import uuid
from abc import ABC, abstractmethod
from typing import Any
from django.urls import reverse
from django.http import HttpRequest
from .models import Payment
from orders.models import Order

# Abstract base class defining the payment gateway strategy interface
class PaymentGateway(ABC):

    @abstractmethod
    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        # Initiate payment workflow and return destination redirect URL
        pass

    @abstractmethod
    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        # Verify payment transaction outcome from gateway callback
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
        Payment.objects.create(
            order=order,
            method='BKASH',
            transaction_id=f"BKASH-{uuid.uuid4().hex[:10].upper()}",
            amount=order.total_amount,
            status='PENDING',
            gateway_reference=f"bKash pending #{order.order_number}"
        )
        return reverse('payments:bkash_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False

# Strategy implementation for Nagad mobile financial service
class NagadPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request: HttpRequest) -> str:
        Payment.objects.create(
            order=order,
            method='NAGAD',
            transaction_id=f"NAGAD-{uuid.uuid4().hex[:10].upper()}",
            amount=order.total_amount,
            status='PENDING',
            gateway_reference=f"Nagad pending #{order.order_number}"
        )
        return reverse('payments:nagad_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict[str, Any]) -> bool:
        return False

# Factory class instantiating payment gateways according to selected payment method
class PaymentGatewayFactory:
    _gateways: dict[str, type[PaymentGateway]] = {
        'COD': CODPayment,
        'BKASH': BkashPayment,
        'NAGAD': NagadPayment,
    }

    @classmethod
    def get_gateway(cls, method_code: str) -> PaymentGateway:
        gateway_class = cls._gateways.get(method_code.upper(), CODPayment)
        return gateway_class()
