import logging
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.urls import reverse
from django.http import HttpRequest
from sslcommerz_python_api import SSLCommerzService
from sslcommerz_python_api.models import PaymentRequest, CustomerInfo, ShippingInfo

from .models import Payment
from orders.models import Order

logger = logging.getLogger(__name__)


class SSLCommerzGatewayService:

    @classmethod
    def get_service_client(cls) -> SSLCommerzService:
        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'testbox')
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', 'qwerty')
        is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)
        return SSLCommerzService.create(
            store_id=store_id,
            store_pass=store_pass,
            is_sandbox=is_sandbox,
        )

    @classmethod
    def initiate_payment(cls, order: Order, method_hint: str = 'SSLCOMMERZ') -> tuple[Optional[str], Payment]:
        tran_id = f"NIT-{order.order_number}-{uuid.uuid4().hex[:6].upper()}"

        payment = Payment.objects.create(
            order=order,
            method=method_hint,
            transaction_id=tran_id,
            amount=order.total_amount,
            currency='BDT',
            status='PENDING',
            gateway_reference=f"Initiated via SSLCommerz ({method_hint})",
        )

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
        success_url = f"{site_url}{reverse('payments:sslcommerz_success', kwargs={'order_number': order.order_number})}"
        fail_url = f"{site_url}{reverse('payments:sslcommerz_fail', kwargs={'order_number': order.order_number})}"
        cancel_url = f"{site_url}{reverse('payments:sslcommerz_cancel', kwargs={'order_number': order.order_number})}"
        ipn_url = f"{site_url}{reverse('payments:sslcommerz_ipn')}"

        full_address = f"{order.street_address}, {order.state_or_division}".strip(', ')
        customer = CustomerInfo(
            name=order.full_name,
            email=order.email,
            phone=order.phone,
            address1=full_address or 'Dhaka',
            city=order.city or 'Dhaka',
            postcode=order.postal_code or '1200',
            country=order.country or 'Bangladesh',
        )

        shipping = ShippingInfo(
            shipping_to=order.full_name,
            address=full_address or 'Dhaka',
            city=order.city or 'Dhaka',
            postcode=order.postal_code or '1200',
            country=order.country or 'Bangladesh',
        )

        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', 'testbox')
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', 'qwerty')

        payment_request = PaymentRequest(
            store_id=store_id,
            store_pass=store_pass,
            total_amount=Decimal(str(order.total_amount)),
            currency='BDT',
            tran_id=tran_id,
            success_url=success_url,
            fail_url=fail_url,
            cancel_url=cancel_url,
            ipn_url=ipn_url,
            product_name=f"NIT Order #{order.order_number}",
            product_category='Computer Hardware',
            product_profile='general',
            num_of_item=order.items.count() or 1,
            shipping_method='YES',
            customer=customer,
            shipping=shipping,
            value_a=order.order_number,
            value_b=method_hint,
        )

        try:
            client = cls.get_service_client()
            response = client.initiate_payment(payment_request)
            if response.status == 'SUCCESS':
                payment.gateway_session_key = response.session_key
                payment.save(update_fields=['gateway_session_key'])
                return response.gateway_url, payment

            payment.status = 'FAILED'
            payment.raw_response = str(response.__dict__)
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment
        except Exception as e:
            logger.exception("SSLCommerz initiation failed for order #%s", order.order_number)
            payment.status = 'FAILED'
            payment.raw_response = str(e)
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment

    @classmethod
    def validate_ipn(cls, val_id: str) -> tuple[bool, dict[str, Any]]:
        try:
            client = cls.get_service_client()
            resp = client.validate_transaction(val_id)
            is_valid = resp.status in ('VALID', 'VALIDATED')
            return is_valid, resp.data if hasattr(resp, 'data') else {}
        except Exception as e:
            logger.exception("SSLCommerz IPN validation failed for val_id %s", val_id)
            return False, {'error': str(e)}


# Abstract base class defining the payment gateway strategy interface
class PaymentGateway(ABC):

    @abstractmethod
    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        pass

    @abstractmethod
    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        pass


# Strategy implementation for Cash on Delivery orders
class CODPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        Payment.objects.create(
            order=order,
            method='COD',
            transaction_id=f"COD-{uuid.uuid4().hex[:8].upper()}",
            amount=order.total_amount,
            status='PENDING',
            gateway_reference='Cash on Delivery order placed'
        )
        return reverse('orders:order_success', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return True


# Strategy implementation for bKash mobile financial service
class BkashPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        gateway_url, _ = SSLCommerzGatewayService.initiate_payment(order, method_hint='BKASH')
        if gateway_url:
            return gateway_url
        return reverse('payments:payment_select', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False


# Strategy implementation for Nagad mobile financial service
class NagadPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        gateway_url, _ = SSLCommerzGatewayService.initiate_payment(order, method_hint='NAGAD')
        if gateway_url:
            return gateway_url
        return reverse('payments:payment_select', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False


# Strategy implementation for SSLCommerz Card & Net Banking
class SSLCommerzPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        gateway_url, _ = SSLCommerzGatewayService.initiate_payment(order, method_hint='SSLCOMMERZ')
        if gateway_url:
            return gateway_url
        return reverse('payments:payment_select', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False


# Factory class instantiating payment gateways according to selected payment method
class PaymentGatewayFactory:
    _gateways: dict[str, type[PaymentGateway]] = {
        'COD': CODPayment,
        'BKASH': BkashPayment,
        'NAGAD': NagadPayment,
        'SSLCOMMERZ': SSLCommerzPayment,
    }

    @classmethod
    def get_gateway(cls, method_code: str) -> PaymentGateway:
        gateway_class = cls._gateways.get(method_code.upper(), CODPayment)
        return gateway_class()
