from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, OrderItem
from products.models import Product
from cart.cart import Cart

class OrderService:
    """Service layer for atomic order processing and stock management."""

    @classmethod
    @transaction.atomic
    def create_order_from_cart(cls, cart: Cart, cleaned_data: dict, user=None) -> Order:
        """Atomically create order, create line items, and deduct stock."""
        if cart.is_empty():
            raise ValidationError("Cannot create an order with an empty cart.")

        # 1. Lock and verify stock for all items
        cart_items_data = list(cart)
        for item in cart_items_data:
            product = Product.objects.select_for_update().get(id=item['product'].id)
            if product.stock_qty < item['quantity']:
                raise ValidationError(
                    f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, Requested: {item['quantity']}."
                )

        # 2. Instantiate Order
        order = Order.objects.create(
            user=user if user and user.is_authenticated else None,
            full_name=cleaned_data['full_name'],
            email=cleaned_data['email'],
            phone=cleaned_data['phone'],
            street_address=cleaned_data['street_address'],
            city=cleaned_data['city'],
            state_or_division=cleaned_data.get('state_or_division', ''),
            postal_code=cleaned_data['postal_code'],
            country=cleaned_data.get('country', 'Bangladesh'),
            order_notes=cleaned_data.get('order_notes', ''),
            subtotal=cart.get_subtotal(),
            shipping_fee=cart.get_shipping_fee(),
            total_amount=cart.get_grand_total(),
            payment_method=cleaned_data['payment_method'],
            status='PENDING' if cleaned_data['payment_method'] != 'COD' else 'CONFIRMED',
            is_paid=False,
        )

        # 3. Create items and reduce stock
        for item in cart_items_data:
            product = Product.objects.select_for_update().get(id=item['product'].id)
            product.stock_qty -= item['quantity']
            product.save(update_fields=['stock_qty'])

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                unit_price=item['price'],
                quantity=item['quantity'],
                line_total=item['total_price']
            )

        # 4. Notify customer via email
        cls.send_order_confirmation_email(order)

        return order

    @classmethod
    def send_order_confirmation_email(cls, order: Order) -> None:
        """Sends order placement confirmation receipt."""
        subject = f"Order #{order.order_number} Confirmation - N-IT Home"
        message = (
            f"Dear {order.full_name},\n\n"
            f"Thank you for your order at N-IT Home!\n"
            f"Order Number: {order.order_number}\n"
            f"Payment Method: {order.get_payment_method_display()}\n"
            f"Total Amount: ${order.total_amount}\n"
            f"Delivery Address: {order.street_address}, {order.city} - {order.postal_code}\n\n"
            f"We are preparing your PC hardware components for fast dispatch.\n\n"
            f"Best regards,\nN-IT Home Customer Support"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'orders@nithome.com'),
                recipient_list=[order.email],
                fail_silently=True
            )
        except Exception:
            pass

    @classmethod
    @transaction.atomic
    def cancel_order(cls, order: Order) -> None:
        """Restores stock and marks order as cancelled."""
        if order.status in ['SHIPPED', 'DELIVERED', 'CANCELLED']:
            raise ValidationError(f"Cannot cancel order with status '{order.get_status_display()}'.")

        for item in order.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_qty += item.quantity
            product.save(update_fields=['stock_qty'])

        order.status = 'CANCELLED'
        order.save(update_fields=['status'])
