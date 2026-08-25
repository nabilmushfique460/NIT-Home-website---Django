import uuid
from abc import ABC, abstractmethod
from django.urls import reverse
from .models import Payment
from orders.models import Order

class PaymentGateway(ABC):

    @abstractmethod
    def initiate_payment(self, order: Order, request) -> str:
        pass

    @abstractmethod
    def verify_payment(self, request_data: dict) -> bool:
        pass

class CODPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request) -> str:
        Payment.objects.create(
            order=order,
            method='COD',
            transaction_id=f'COD-{uuid.uuid4().hex[:8].upper()}',
            amount=order.total_amount,
            status='PENDING',
            gateway_reference='Cash on Delivery order placed'
        )
        return reverse('orders:order_success', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        return True

class BkashPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request) -> str:
        Payment.objects.create(
            order=order,
            method='BKASH',
            transaction_id=f'BKASH-{uuid.uuid4().hex[:10].upper()}',
            amount=order.total_amount,
            status='PENDING',
            gateway_reference=f'bKash pending #{order.order_number}'
        )
        return reverse('payments:bkash_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        return False

class NagadPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request) -> str:
        Payment.objects.create(
            order=order,
            method='NAGAD',
            transaction_id=f'NAGAD-{uuid.uuid4().hex[:10].upper()}',
            amount=order.total_amount,
            status='PENDING',
            gateway_reference=f'Nagad pending #{order.order_number}'
        )
        return reverse('payments:nagad_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        return False

class PaymentGatewayFactory:
    _gateways = {'COD': CODPayment, 'BKASH': BkashPayment, 'NAGAD': NagadPayment}

    @classmethod
    def get_gateway(cls, method_code: str) -> PaymentGateway:
        gateway_class = cls._gateways.get(method_code.upper(), CODPayment)
        return gateway_class()
