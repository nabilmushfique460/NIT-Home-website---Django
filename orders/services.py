from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, OrderItem
from products.models import Product
from cart.cart import Cart

class OrderService:

    @classmethod
    @transaction.atomic
    def create_order_from_cart(cls, cart: Cart, cleaned_data: dict, user=None) -> Order:
        if cart.is_empty():
            raise ValidationError('Cannot create an order with an empty cart.')
        cart_items_data = list(cart)
        for item in cart_items_data:
            product = Product.objects.select_for_update().get(id=item['product'].id)
            if product.stock_qty < item['quantity']:
                raise ValidationError(f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, Requested: {item['quantity']}.")
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
            status='PENDING',
            is_paid=False
        )
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
        if cleaned_data['payment_method'] == 'COD':
            cls.send_admin_new_order_email(order)
        return order

    @classmethod
    def send_admin_new_order_email(cls, order: Order) -> None:
        items_summary = "\n".join([f"- {item.quantity}x {item.product_name} (${item.line_total})" for item in order.items.all()])
        subject = f"[N-IT HOME] New Cash on Delivery Order #{order.order_number} - Review Required"
        message = (
            f"A new Cash on Delivery order has been placed on N-IT HOME:\n\n"
            f"Order Number: {order.order_number}\n"
            f"Customer Name: {order.full_name}\n"
            f"Customer Email: {order.email}\n"
            f"Phone: {order.phone}\n"
            f"Delivery Address: {order.street_address}, {order.city} {order.postal_code}\n"
            f"Total Amount: ${order.total_amount}\n\n"
            f"Items Ordered:\n{items_summary}\n\n"
            f"Please review and approve this order from the Django Admin:\n"
            f"http://127.0.0.1:8000/admin/orders/order/{order.id}/change/"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com'),
                recipient_list=['nabil29089@gmail.com'],
                fail_silently=False
            )
        except Exception:
            pass

    @classmethod
    def send_order_approved_email(cls, order: Order) -> None:
        items_summary = "\n".join([f"- {item.quantity}x {item.product_name} (${item.line_total})" for item in order.items.all()])
        subject = f"[N-IT HOME] Order #{order.order_number} Confirmed"
        message = (
            f"Dear {order.full_name},\n\n"
            f"Your order has been confirmed, you will get more update soon.\n\n"
            f"Order Number: {order.order_number}\n"
            f"Total Amount: ${order.total_amount}\n"
            f"Payment Method: {order.get_payment_method_display()}\n"
            f"Delivery Address: {order.street_address}, {order.city} {order.postal_code}\n\n"
            f"Items Summary:\n{items_summary}\n\n"
            f"Thank you for choosing N-IT HOME!\n\n"
            f"Best regards,\n"
            f"N-IT HOME Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com'),
                recipient_list=[order.email],
                fail_silently=False
            )
        except Exception:
            pass

    @classmethod
    @transaction.atomic
    def cancel_order(cls, order: Order) -> None:
        if order.status in ['SHIPPED', 'DELIVERED', 'CANCELLED']:
            raise ValidationError(f"Cannot cancel order with status '{order.get_status_display()}'.")
        for item in order.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_qty += item.quantity
            product.save(update_fields=['stock_qty'])
        order.status = 'CANCELLED'
        order.save(update_fields=['status'])
