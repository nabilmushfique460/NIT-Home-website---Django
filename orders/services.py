from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, OrderItem
from products.models import Product
from accounts.models import Notification, User
from cart.cart import Cart

# Service class handling order creation, status workflows, cancellations, and notifications
class OrderService:

    @classmethod
    @transaction.atomic
    def create_order_from_cart(cls, cart: Cart, cleaned_data: dict, user: Optional[User] = None) -> Order:
        if cart.is_empty():
            raise ValidationError('Cannot create an order with an empty cart.')

        # Lock and validate inventory availability before creating order
        cart_items_data = list(cart)
        for item in cart_items_data:
            product = Product.objects.select_for_update().get(id=item['product'].id)
            if product.stock_qty < item['quantity']:
                raise ValidationError(
                    f"Insufficient stock for '{product.name}'. Available: {product.stock_qty}, Requested: {item['quantity']}."
                )

        # Create order record
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
            payment_method=cleaned_data.get('payment_method', 'COD') or 'COD',
            status='PENDING',
            is_paid=False
        )

        # Deduct stock and persist individual order line items
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

        # Create in-app notification for authenticated buyers
        if order.user:
            Notification.objects.create(
                user=order.user,
                title=f"Order #{order.order_number} Placed",
                message=f"Your order #{order.order_number} for ৳{order.total_amount} has been placed successfully.",
                link=f"/orders/invoice/{order.order_number}/"
            )

        return order

    @classmethod
    def send_admin_new_order_email(cls, order: Order) -> None:
        items_summary = "\n".join([f"- {item.quantity}x {item.product_name} (৳{item.line_total})" for item in order.items.all()])
        subject = f"[N-IT HOME] New Cash on Delivery Order #{order.order_number} - Review Required"
        message = (
            f"A new Cash on Delivery order has been placed on N-IT HOME:\n\n"
            f"Order Number: {order.order_number}\n"
            f"Customer Name: {order.full_name}\n"
            f"Customer Email: {order.email}\n"
            f"Phone: {order.phone}\n"
            f"Delivery Address: {order.street_address}, {order.city} {order.postal_code}\n"
            f"Total Amount: ৳{order.total_amount}\n\n"
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
    @transaction.atomic
    def advance_order_status(cls, order: Order, new_status: str) -> None:
        order.status = new_status
        if new_status == 'DELIVERED':
            order.is_paid = True
            order.save(update_fields=['status', 'is_paid'])
        else:
            order.save(update_fields=['status'])

        items_summary = "\n".join([f"- {item.quantity}x {item.product_name}" for item in order.items.all()])
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')

        # Status: Confirmed
        if new_status == 'CONFIRMED':
            if order.user:
                Notification.objects.create(
                    user=order.user,
                    title=f"Order #{order.order_number} Confirmed",
                    message=f"Your order #{order.order_number} has been confirmed by our team.",
                    link=f"/orders/invoice/{order.order_number}/"
                )
            subject = f"[N-IT HOME] Order #{order.order_number} Confirmed"
            message = (
                f"Dear {order.full_name},\n\n"
                f"Your order #{order.order_number} has been confirmed, you will get more update soon.\n\n"
                f"Order Summary:\n"
                f"- Order Number: {order.order_number}\n"
                f"- Total Amount: ৳{order.total_amount}\n"
                f"- Payment Method: {order.get_payment_method_display()}\n"
                f"- Delivery Address: {order.street_address}, {order.city} {order.postal_code}\n\n"
                f"Items:\n{items_summary}\n\n"
                f"Thank you for shopping with N-IT HOME!\n\n"
                f"Best regards,\n"
                f"N-IT HOME Team"
            )
            try:
                send_mail(subject=subject, message=message, from_email=from_email, recipient_list=[order.email], fail_silently=False)
            except Exception:
                pass

        # Status: Packaging
        elif new_status == 'PACKAGING':
            if order.user:
                Notification.objects.create(
                    user=order.user,
                    title=f"Order #{order.order_number} in Bench Packaging",
                    message=f"Your components for order #{order.order_number} are being verified and packaged on our test bench.",
                    link=f"/orders/invoice/{order.order_number}/"
                )
            subject = f"[N-IT HOME] Order #{order.order_number} - Bench Packaging Started"
            message = (
                f"Dear {order.full_name},\n\n"
                f"Your order #{order.order_number} is now in Bench Packaging.\n\n"
                f"Our hardware engineers are verifying serial numbers, testing clearances, and carefully packaging your components for dispatch.\n\n"
                f"Track live progress on your order page:\n"
                f"http://127.0.0.1:8000/orders/invoice/{order.order_number}/\n\n"
                f"Best regards,\n"
                f"N-IT HOME Team"
            )
            try:
                send_mail(subject=subject, message=message, from_email=from_email, recipient_list=[order.email], fail_silently=False)
            except Exception:
                pass

        # Status: Shipped
        elif new_status == 'SHIPPED':
            if order.user:
                Notification.objects.create(
                    user=order.user,
                    title=f"Order #{order.order_number} In Transit",
                    message=f"Your order #{order.order_number} has been dispatched and is on the way!",
                    link=f"/orders/invoice/{order.order_number}/"
                )
            subject = f"[N-IT HOME] Order #{order.order_number} is In Transit"
            message = (
                f"Dear {order.full_name},\n\n"
                f"Your order #{order.order_number} has been dispatched from our lab and is now In Transit!\n\n"
                f"Delivery Destination: {order.street_address}, {order.city} {order.postal_code}\n"
                f"Recipient Phone: {order.phone}\n\n"
                f"Our delivery personnel will contact you upon arrival.\n\n"
                f"Best regards,\n"
                f"N-IT HOME Team"
            )
            try:
                send_mail(subject=subject, message=message, from_email=from_email, recipient_list=[order.email], fail_silently=False)
            except Exception:
                pass

        # Status: Delivered
        elif new_status == 'DELIVERED':
            if order.user:
                Notification.objects.create(
                    user=order.user,
                    title=f"Order #{order.order_number} Delivered",
                    message=f"Your order #{order.order_number} has been delivered! Please share your review.",
                    link=f"/orders/invoice/{order.order_number}/"
                )
            subject = f"[N-IT HOME] Order #{order.order_number} Delivered - Please Leave a Review"
            message = (
                f"Dear {order.full_name},\n\n"
                f"Your order #{order.order_number} has been successfully delivered!\n\n"
                f"We hope you enjoy your new hardware. Please take a moment to share your review and feedback:\n"
                f"http://127.0.0.1:8000/orders/invoice/{order.order_number}/\n\n"
                f"Thank you for choosing N-IT HOME!\n\n"
                f"Best regards,\n"
                f"N-IT HOME Team"
            )
            try:
                send_mail(subject=subject, message=message, from_email=from_email, recipient_list=[order.email], fail_silently=False)
            except Exception:
                pass

    @classmethod
    def request_order_cancellation(cls, order: Order, user: Optional[User] = None) -> None:
        if not order.can_be_cancelled:
            raise ValidationError(
                f"Order #{order.order_number} cannot be cancelled because it is already '{order.get_status_display()}'."
            )
        order.status = 'CANCEL_REQUESTED'
        order.save(update_fields=['status'])

        if order.user:
            Notification.objects.create(
                user=order.user,
                title=f"Cancellation Requested for Order #{order.order_number}",
                message=f"Your cancellation request for order #{order.order_number} has been submitted for admin review.",
                link=f"/orders/invoice/{order.order_number}/"
            )

        subject = f"[N-IT HOME Cancellation Request] Order #{order.order_number}"
        message = (
            f"A customer has requested cancellation for Order #{order.order_number}:\n\n"
            f"Customer Name: {order.full_name}\n"
            f"Customer Email: {order.email}\n"
            f"Phone: {order.phone}\n"
            f"Total Amount: ৳{order.total_amount}\n\n"
            f"Please review and approve the cancellation in Django Admin:\n"
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
    @transaction.atomic
    def approve_order_cancellation(cls, order: Order) -> None:
        if order.status == 'CANCELLED':
            return
        # Restore reserved product inventory back to stock
        for item in order.items.all():
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_qty += item.quantity
            product.save(update_fields=['stock_qty'])

        order.status = 'CANCELLED'
        order.save(update_fields=['status'])

        if order.user:
            Notification.objects.create(
                user=order.user,
                title=f"Order #{order.order_number} Cancelled",
                message=f"Your cancellation request for order #{order.order_number} has been approved.",
                link=f"/orders/invoice/{order.order_number}/"
            )

        subject = f"[N-IT HOME] Order #{order.order_number} Cancellation Confirmed"
        message = (
            f"Dear {order.full_name},\n\n"
            f"Your cancellation request for order #{order.order_number} has been approved and the order is now cancelled.\n\n"
            f"If you have any questions, please feel free to reach out.\n\n"
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
