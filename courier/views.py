import json
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Shipment
from accounts.models import Notification
from orders.services import OrderService

logger = logging.getLogger(__name__)

STATUS_MESSAGES = {
    'pending': "Your order has been booked with our courier partner.",
    'in_review': "Your parcel is under review by the courier.",
    'in_transit': "Your parcel is in transit and on its way to you.",
    'picked_up': "Your package has been picked up from our hardware lab.",
    'out_for_delivery': "Your order is out for delivery today! Keep your phone reachable.",
    'delivered': "Your order has been successfully delivered! Thank you for shopping with N-IT HOME.",
    'partial_delivered': "Part of your order has been delivered.",
    'cancelled': "Your delivery was cancelled by the courier.",
    'hold': "Your delivery is on hold. Our team will contact you shortly.",
    'returned': "Your parcel was returned to the sender.",
}


@method_decorator(csrf_exempt, name='dispatch')
class SteadfastWebhookView(View):
    def post(self, request, token: str, *args, **kwargs):
        expected_token = getattr(settings, 'STEADFAST_WEBHOOK_TOKEN', '')
        if not expected_token or token != expected_token:
            logger.warning("Steadfast webhook unauthorized access attempt with token: %s", token)
            return HttpResponse('Forbidden', status=403)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return HttpResponse('Invalid JSON payload', status=400)

        consignment_id = str(payload.get('consignment_id', ''))
        new_status = payload.get('delivery_status') or payload.get('status')
        if not consignment_id or not new_status:
            return HttpResponse('Missing consignment_id or delivery_status', status=400)

        shipment = Shipment.objects.filter(
            consignment_id=consignment_id
        ).select_related('order', 'order__user').first()

        if not shipment:
            logger.warning("Steadfast webhook received for unknown consignment_id: %s", consignment_id)
            return HttpResponse('Shipment record not found', status=404)

        shipment.status = str(new_status)
        shipment.raw_last_webhook = payload
        shipment.save(update_fields=['status', 'raw_last_webhook', 'updated_at'])

        order = shipment.order
        normalized = str(new_status).lower()
        friendly_msg = STATUS_MESSAGES.get(normalized, f"Delivery status update: {new_status}")

        # Update order status based on courier milestones
        if normalized in ('in_transit', 'picked_up', 'out_for_delivery'):
            if order.status not in ('SHIPPED', 'DELIVERED', 'CANCELLED'):
                OrderService.advance_order_status(order, 'SHIPPED')
        elif normalized == 'delivered':
            if order.status != 'DELIVERED':
                OrderService.advance_order_status(order, 'DELIVERED')
        elif normalized in ('cancelled', 'returned'):
            if order.status != 'CANCELLED':
                OrderService.approve_order_cancellation(order)

        # In-app notification for authenticated buyer
        if order.user:
            Notification.objects.create(
                user=order.user,
                title=f"Order #{order.order_number} Delivery Update",
                message=friendly_msg,
                link=f"/orders/invoice/{order.order_number}/",
            )

        # Email update to customer
        try:
            send_mail(
                subject=f"[N-IT HOME] Order #{order.order_number}: {friendly_msg}",
                message=(
                    f"Hello {order.full_name},\n\n"
                    f"{friendly_msg}\n\n"
                    f"Consignment ID: {shipment.consignment_id}\n"
                    f"Tracking Code: {shipment.tracking_code or 'N/A'}\n"
                    f"Invoice Reference: {order.order_number}\n\n"
                    f"View live status anytime on your invoice:\n"
                    f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/orders/invoice/{order.order_number}/\n\n"
                    f"Best regards,\n"
                    f"N-IT HOME Team"
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com'),
                recipient_list=[order.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Failed to send customer delivery email for order #%s", order.order_number)

        # Admin alert on critical conditions (cancelled, hold, returned)
        if normalized in ('cancelled', 'hold', 'returned'):
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'nabil29089@gmail.com')
            try:
                send_mail(
                    subject=f"[N-IT HOME ALERT] Delivery Issue for Order #{order.order_number}: {new_status}",
                    message=(
                        f"Consignment ID: {consignment_id}\n"
                        f"New Status: {new_status}\n"
                        f"Customer: {order.full_name} (Phone: {order.phone})\n"
                        f"Order Total: ৳{order.total_amount}\n"
                        f"Shipping Address: {order.street_address}, {order.city}\n"
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com'),
                    recipient_list=[admin_email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send admin delivery alert for order #%s", order.order_number)

        return JsonResponse({'received': True, 'consignment_id': consignment_id, 'status': new_status})
