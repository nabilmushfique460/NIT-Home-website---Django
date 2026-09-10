import logging
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.http import HttpRequest
from sslcommerz_python_api import SSLCommerzService
from sslcommerz_python_api.models import PaymentRequest, CustomerInfo, ShippingInfo
from sslcommerz_python_api.exceptions import SSLCommerzValidationError, SSLCommerzAPIError

from .models import Payment
from orders.models import Order
from orders.services import OrderService

logger = logging.getLogger(__name__)


def generate_ssl_tran_id(order: Order) -> str:
    """
    Generate a deterministic, unique transaction ID safe for SSLCOMMERZ (max 30 characters).
    Format: NIT<order_id>X<random_hex_10> (e.g. NIT42X7F8A1B2C3D -> 16-20 characters).
    """
    random_part = uuid.uuid4().hex[:10].upper()
    tran_id = f"NIT{order.id}X{random_part}"
    return tran_id[:30]


class SSLCommerzGatewayService:

    @classmethod
    def get_service_client(cls) -> SSLCommerzService:
        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', '')
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', '')
        is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)

        if not store_id or not store_pass:
            logger.warning(
                "SSLCOMMERZ credentials are not configured. SSLCOMMERZ_STORE_ID or SSLCOMMERZ_STORE_PASS is missing."
            )

        return SSLCommerzService.create(
            store_id=store_id,
            store_pass=store_pass,
            is_sandbox=is_sandbox,
        )

    @classmethod
    def initiate_payment(cls, order: Order, method_hint: str = 'SSLCOMMERZ') -> tuple[Optional[str], Optional[Payment]]:
        # Guard: Check order status and payment state before initiation
        if order.is_paid:
            logger.warning("Attempted to initiate payment for already-paid order #%s", order.order_number)
            return None, None

        if order.status == 'CANCELLED':
            logger.warning("Attempted to initiate payment for cancelled order #%s", order.order_number)
            return None, None

        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', '')
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', '')

        tran_id = generate_ssl_tran_id(order)

        # Reuse an existing pending payment record or create a new one
        payment = Payment.objects.filter(order=order, status='PENDING').first()
        if payment:
            payment.transaction_id = tran_id
            payment.amount = order.total_amount
            payment.currency = 'BDT'
            payment.method = 'SSLCOMMERZ'
            payment.gateway_reference = 'Initiated via SSLCommerz Hosted Checkout'
            payment.save(update_fields=['transaction_id', 'amount', 'currency', 'method', 'gateway_reference', 'updated_at'])
        else:
            payment = Payment.objects.create(
                order=order,
                method='SSLCOMMERZ',
                transaction_id=tran_id,
                amount=order.total_amount,
                currency='BDT',
                status='PENDING',
                gateway_reference='Initiated via SSLCommerz Hosted Checkout',
            )

        if not store_id or not store_pass:
            logger.error("Cannot initiate SSLCommerz payment: Store ID or Store Password missing in environment.")
            payment.status = 'FAILED'
            payment.raw_response = 'Gateway misconfiguration: Store credentials missing'
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment

        is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)
        if not is_sandbox and store_id.lower() in ('testbox', 'test', 'sandbox'):
            logger.error("Cannot use sandbox test credentials when SSLCOMMERZ_IS_SANDBOX=False (production mode).")
            payment.status = 'FAILED'
            payment.raw_response = 'Gateway misconfiguration: Sandbox credentials used in production mode'
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment

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
            ship_name=order.full_name,
            address=full_address or 'Dhaka',
            city=order.city or 'Dhaka',
            postcode=order.postal_code or '1200',
            country=order.country or 'Bangladesh',
        )

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
            value_b='SSLCOMMERZ',
        )

        try:
            client = cls.get_service_client()
            response = client.initiate_payment(payment_request)
            if response.status == 'SUCCESS':
                payment.gateway_session_key = response.session_key
                payment.save(update_fields=['gateway_session_key'])
                return response.gateway_url, payment

            payment.status = 'FAILED'
            payment.raw_response = 'Gateway initiation returned unsuccessful status'
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment
        except (SSLCommerzAPIError, Exception) as e:
            logger.exception("SSLCommerz initiation failed for order #%s", order.order_number)
            payment.status = 'FAILED'
            payment.raw_response = f"Initiation error: {type(e).__name__}"
            payment.save(update_fields=['status', 'raw_response'])
            return None, payment

    @classmethod
    def verify_ipn_signature(cls, post_data: dict[str, Any]) -> tuple[bool, str]:
        """
        Verify the IPN hash signature locally using store_passwd.
        """
        if 'verify_sign' not in post_data or 'verify_key' not in post_data:
            return True, "No signature parameters provided"

        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', '')
        if not store_pass:
            return False, "Store password not configured for IPN signature verification"

        try:
            client = cls.get_service_client()
            client.verify_ipn(post_data)
            return True, "IPN signature verified"
        except SSLCommerzValidationError as e:
            logger.warning("SSLCommerz IPN signature verification failed: %s", str(e))
            return False, str(e)
        except Exception as e:
            logger.error("Unexpected error during IPN signature verification: %s", str(e))
            return False, str(e)

    @classmethod
    def validate_transaction_with_gateway(cls, val_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Query SSLCOMMERZ validation server directly to confirm payment authenticity.
        """
        if not val_id:
            return False, {'error': 'Missing val_id'}

        try:
            client = cls.get_service_client()
            resp = client.validate_transaction(val_id)
            is_valid = resp.status in ('VALID', 'VALIDATED')
            data = resp.data if hasattr(resp, 'data') else {}
            return is_valid, data
        except (SSLCommerzValidationError, SSLCommerzAPIError, Exception) as e:
            logger.exception("SSLCommerz server-side validation error for val_id %s", val_id)
            return False, {'error': str(e)}

    @classmethod
    @transaction.atomic
    def settle_payment_success(
        cls,
        tran_id: str,
        val_id: str,
        validation_data: dict[str, Any]
    ) -> tuple[bool, str, Optional[Order]]:
        """
        Centralized, atomic, idempotent payment settlement.
        Verifies:
          1. Existence of payment and order
          2. Idempotency (already SUCCESS / paid)
          3. Status is VALID or VALIDATED
          4. tran_id matches
          5. Amount matches Decimal equality
          6. Currency matches BDT
          7. Risk level assessment (risk_level == '0')
        """
        payment = Payment.objects.select_for_update().filter(
            transaction_id=tran_id
        ).select_related('order').first()

        if not payment:
            logger.error("Settlement rejected: Transaction ID not found: %s", tran_id)
            return False, "Transaction not found", None

        order = Order.objects.select_for_update().get(id=payment.order_id)

        # Idempotency check: If already successfully settled, exit early without duplicating side effects
        if payment.status == 'SUCCESS' and order.is_paid:
            logger.info("Payment %s for Order #%s is already settled. Skipping duplicate settlement.", tran_id, order.order_number)
            return True, "Payment already settled", order

        # 1. Verify Gateway Status
        gateway_status = validation_data.get('status', '').upper()
        if gateway_status not in ('VALID', 'VALIDATED'):
            payment.status = 'FAILED'
            payment.raw_response = f"Invalid gateway status: {gateway_status}"
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            return False, f"Invalid gateway status: {gateway_status}", order

        # 2. Verify Transaction ID
        val_tran_id = str(validation_data.get('tran_id', '')).strip()
        if val_tran_id != payment.transaction_id:
            logger.error(
                "Settlement rejected: tran_id mismatch! Gateway tran_id=%s, DB tran_id=%s",
                val_tran_id, payment.transaction_id
            )
            payment.status = 'FAILED'
            payment.raw_response = f"tran_id mismatch: gateway={val_tran_id} vs db={payment.transaction_id}"
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            return False, "Transaction ID mismatch", order

        # 3. Verify Amount with safe Decimal comparison
        try:
            gateway_amount = Decimal(str(validation_data.get('amount', '0'))).quantize(Decimal('0.01'))
            expected_amount = Decimal(str(order.total_amount)).quantize(Decimal('0.01'))
            payment_amount = Decimal(str(payment.amount)).quantize(Decimal('0.01'))
        except Exception:
            return False, "Invalid amount format in validation response", order

        if gateway_amount != expected_amount or gateway_amount != payment_amount:
            logger.error(
                "Settlement rejected: Amount mismatch! Gateway amount=%s, Order total=%s, Payment amount=%s",
                gateway_amount, expected_amount, payment_amount
            )
            payment.status = 'FAILED'
            payment.raw_response = f"Amount mismatch: gateway={gateway_amount}, order={expected_amount}"
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            return False, "Amount mismatch", order

        # 4. Verify Currency
        gateway_currency = str(validation_data.get('currency', '')).upper().strip()
        if gateway_currency != 'BDT' or gateway_currency != payment.currency.upper():
            logger.error(
                "Settlement rejected: Currency mismatch! Gateway currency=%s, Expected BDT",
                gateway_currency
            )
            payment.status = 'FAILED'
            payment.raw_response = f"Currency mismatch: gateway={gateway_currency}, expected=BDT"
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            return False, "Currency mismatch", order

        # 5. Risk Assessment Policy
        risk_level = str(validation_data.get('risk_level', '0')).strip()
        risk_title = str(validation_data.get('risk_title', '')).strip()
        if risk_level != '0':
            logger.warning(
                "Settlement held: Risky transaction flagged by SSLCOMMERZ for Order #%s! Risk level=%s (%s)",
                order.order_number, risk_level, risk_title
            )
            payment.status = 'PENDING'
            payment.gateway_reference = f"Risk Level {risk_level} ({risk_title}) - Pending Owner Review"
            payment.val_id = val_id
            payment.bank_tran_id = validation_data.get('bank_tran_id', '')
            payment.card_type = validation_data.get('card_type', '')
            payment.raw_response = f"Risk Flagged: {risk_title} (Level {risk_level})"
            payment.save(update_fields=['status', 'gateway_reference', 'val_id', 'bank_tran_id', 'card_type', 'raw_response', 'updated_at'])
            return False, f"Transaction held for security review: {risk_title}", order

        # Authoritative Settlement
        card_type = validation_data.get('card_type', 'Online')
        bank_tran_id = validation_data.get('bank_tran_id', '')

        payment.status = 'SUCCESS'
        payment.val_id = val_id
        payment.bank_tran_id = bank_tran_id
        payment.card_type = card_type
        payment.gateway_reference = f"SSLCommerz Paid via {card_type}"
        payment.raw_response = f"Status: {gateway_status}, Card: {card_type}, BankTranID: {bank_tran_id}"
        payment.save(update_fields=['status', 'val_id', 'bank_tran_id', 'card_type', 'gateway_reference', 'raw_response', 'updated_at'])

        order.is_paid = True
        order.payment_method = 'SSLCOMMERZ'
        order.save(update_fields=['is_paid', 'payment_method', 'updated_at'])

        # Advance order status to CONFIRMED (centralized notifications and courier booking)
        OrderService.advance_order_status(order, 'CONFIRMED')

        logger.info("Order #%s successfully verified and settled via SSLCOMMERZ (%s)", order.order_number, tran_id)
        return True, "Payment settled successfully", order


# Abstract base class defining payment gateway strategy interface
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
        if order.is_paid:
            return reverse('orders:order_detail', kwargs={'order_number': order.order_number})

        Payment.objects.create(
            order=order,
            method='COD',
            transaction_id=f"COD-{order.id}-{uuid.uuid4().hex[:8].upper()}",
            amount=order.total_amount,
            status='PENDING',
            gateway_reference='Cash on Delivery order placed'
        )
        return reverse('orders:order_success', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return True


# Strategy implementation for SSLCommerz Hosted Checkout (bKash, Nagad, Cards, Internet Banking)
class SSLCommerzPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        if order.is_paid:
            return reverse('orders:order_detail', kwargs={'order_number': order.order_number})

        gateway_url, _ = SSLCommerzGatewayService.initiate_payment(order, method_hint='SSLCOMMERZ')
        if gateway_url:
            return gateway_url
        return reverse('payments:payment_select', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False


# Factory class instantiating payment gateways
class PaymentGatewayFactory:
    _gateways: dict[str, type[PaymentGateway]] = {
        'COD': CODPayment,
        'SSLCOMMERZ': SSLCommerzPayment,
        # Backwards-compatible aliases routing directly to SSLCOMMERZ Hosted Checkout
        'BKASH': SSLCommerzPayment,
        'NAGAD': SSLCommerzPayment,
    }

    @classmethod
    def get_gateway(cls, method_code: str) -> PaymentGateway:
        gateway_class = cls._gateways.get(method_code.upper(), CODPayment)
        return gateway_class()
