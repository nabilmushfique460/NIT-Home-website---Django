import logging
import requests
from django.conf import settings
from orders.models import Order
from .models import Shipment

logger = logging.getLogger(__name__)


class SteadfastService:
    BASE_URL = 'https://portal.packzy.com/api/v1'

    @classmethod
    def _headers(cls) -> dict:
        return {
            'Api-Key': getattr(settings, 'STEADFAST_API_KEY', ''),
            'Secret-Key': getattr(settings, 'STEADFAST_SECRET_KEY', ''),
            'Content-Type': 'application/json',
        }

    @classmethod
    def create_order(cls, order: Order) -> dict:
        # Idempotency guard: If a real consignment is already booked for this order, never call Steadfast API again
        existing_shipment = Shipment.objects.filter(order=order).first()
        if existing_shipment and existing_shipment.consignment_id and not existing_shipment.consignment_id.startswith('LOCAL-'):
            logger.info(
                "Order #%s already has booked consignment %s. Skipping duplicate Steadfast API call.",
                order.order_number, existing_shipment.consignment_id
            )
            return {
                'status': 200,
                'message': 'Shipment already booked',
                'consignment': {
                    'consignment_id': existing_shipment.consignment_id,
                    'tracking_code': existing_shipment.tracking_code,
                    'status': existing_shipment.status,
                }
            }

        api_key = getattr(settings, 'STEADFAST_API_KEY', '')
        secret_key = getattr(settings, 'STEADFAST_SECRET_KEY', '')

        if not api_key or not secret_key:
            if existing_shipment:
                return {'status': 200, 'message': 'Steadfast mock order already exists'}
            logger.warning(
                "Steadfast credentials not configured in settings. Order #%s shipment booking skipped.",
                order.order_number
            )
            # Create a mock/pending shipment record so the order still displays a shipment object
            shipment, _ = Shipment.objects.update_or_create(
                order=order,
                defaults={
                    'consignment_id': f"LOCAL-{order.order_number}",
                    'tracking_code': f"TRK-{order.order_number}",
                    'status': 'pending',
                }
            )
            return {'status': 200, 'message': 'Steadfast mock order recorded (no API keys configured)'}

        cod_amount = float(order.total_amount) if order.payment_method == 'COD' and not order.is_paid else 0.0
        full_address = f"{order.street_address}, {order.state_or_division}, {order.city} {order.postal_code}".strip(', ')

        payload = {
            'invoice': order.order_number,
            'recipient_name': order.full_name,
            'recipient_phone': order.phone,
            'recipient_address': full_address or order.city or 'Dhaka',
            'cod_amount': cod_amount,
            'note': f"N-IT HOME Order #{order.order_number} | {order.order_notes or 'Fragile Hardware'}",
        }

        try:
            resp = requests.post(
                f"{cls.BASE_URL}/create_order",
                json=payload,
                headers=cls._headers(),
                timeout=15
            )
            data = resp.json()
            consignment = data.get('consignment', {})
            if consignment:
                Shipment.objects.update_or_create(
                    order=order,
                    defaults={
                        'consignment_id': str(consignment.get('consignment_id', '')),
                        'tracking_code': consignment.get('tracking_code', ''),
                        'status': consignment.get('status', 'pending'),
                        'raw_last_webhook': data,
                    }
                )
            return data
        except requests.RequestException as e:
            logger.error("Steadfast API request failed for Order #%s: %s", order.order_number, str(e))
            return {'status': 500, 'error': str(e)}

    @classmethod
    def get_status(cls, consignment_id: str) -> dict:
        api_key = getattr(settings, 'STEADFAST_API_KEY', '')
        secret_key = getattr(settings, 'STEADFAST_SECRET_KEY', '')
        if not api_key or not secret_key:
            return {}

        try:
            resp = requests.get(
                f"{cls.BASE_URL}/status_by_cid/{consignment_id}",
                headers=cls._headers(),
                timeout=10
            )
            return resp.json()
        except requests.RequestException as e:
            logger.error("Steadfast status check failed for CID %s: %s", consignment_id, str(e))
            return {}
