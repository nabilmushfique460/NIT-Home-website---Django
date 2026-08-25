import uuid
import json
from abc import ABC, abstractmethod
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
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
        Payment.objects.create(order=order, method='COD', transaction_id=f'COD-{uuid.uuid4().hex[:8].upper()}', amount=order.total_amount, status='PENDING', gateway_reference='Cash on Delivery collection on dispatch')
        return reverse('orders:order_success', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        return True

class BkashPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request) -> str:
        trx_id = f'BKASH-{uuid.uuid4().hex[:10].upper()}'
        payment = Payment.objects.create(order=order, method='BKASH', transaction_id=trx_id, amount=order.total_amount, status='PENDING', gateway_reference=f'bKash Checkout Session for #{order.order_number}')
        return reverse('payments:bkash_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        order_number = request_data.get('order_number')
        wallet_number = request_data.get('wallet_number', '')
        pin = request_data.get('pin', '')
        if not order_number or not wallet_number:
            return False
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            return False
        payment = Payment.objects.filter(order=order, method='BKASH').order_by('-created_at').first()
        if payment:
            payment.status = 'SUCCESS'
            payment.gateway_reference = f"bKash Wallet: {wallet_number[-4:].rjust(len(wallet_number), '*')}"
            payment.raw_response = json.dumps({'status': '0000', 'message': 'Successful bKash transaction', 'wallet': wallet_number})
            payment.save()
            order.is_paid = True
            order.status = 'CONFIRMED'
            order.save(update_fields=['is_paid', 'status'])
            return True
        return False

class NagadPayment(PaymentGateway):

    def initiate_payment(self, order: Order, request) -> str:
        trx_id = f'NAGAD-{uuid.uuid4().hex[:10].upper()}'
        payment = Payment.objects.create(order=order, method='NAGAD', transaction_id=trx_id, amount=order.total_amount, status='PENDING', gateway_reference=f'Nagad Checkout Session for #{order.order_number}')
        return reverse('payments:nagad_gateway', kwargs={'order_number': order.order_number})

    def verify_payment(self, request_data: dict) -> bool:
        order_number = request_data.get('order_number')
        wallet_number = request_data.get('wallet_number', '')
        otp = request_data.get('otp', '')
        if not order_number or not wallet_number:
            return False
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            return False
        payment = Payment.objects.filter(order=order, method='NAGAD').order_by('-created_at').first()
        if payment:
            payment.status = 'SUCCESS'
            payment.gateway_reference = f"Nagad Account: {wallet_number[-4:].rjust(len(wallet_number), '*')}"
            payment.raw_response = json.dumps({'status': 'Success', 'message': 'Nagad payment verified', 'account': wallet_number})
            payment.save()
            order.is_paid = True
            order.status = 'CONFIRMED'
            order.save(update_fields=['is_paid', 'status'])
            return True
        return False

class PaymentGatewayFactory:
    _gateways = {'COD': CODPayment, 'BKASH': BkashPayment, 'NAGAD': NagadPayment}

    @classmethod
    def get_gateway(cls, method_code: str) -> PaymentGateway:
        gateway_class = cls._gateways.get(method_code.upper(), CODPayment)
        return gateway_class()
