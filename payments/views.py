import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpRequest
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from orders.models import Order
from orders.services import OrderService
from courier.services import SteadfastService
from .models import Payment
from .services import PaymentGatewayFactory, SSLCommerzGatewayService

logger = logging.getLogger(__name__)


def _get_user_order_or_404(request: HttpRequest, order_number: str) -> Order:
    if request.user.is_staff:
        return get_object_or_404(Order, order_number=order_number)
    return get_object_or_404(Order, order_number=order_number, user=request.user)


# View rendering payment gateway selection screen
class PaymentSelectView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)
        return render(
            request,
            'payments/payment_select.html',
            {
                'order': order,
                'title': f"Select Payment Method - #{order.order_number}"
            }
        )


# View processing chosen payment method and dispatching to respective gateway
class ChoosePaymentView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)
        method = request.POST.get('payment_method', 'COD').upper()
        order.payment_method = method
        order.save(update_fields=['payment_method'])

        # Instantiate strategy through gateway factory
        gateway = PaymentGatewayFactory.get_gateway(method)
        redirect_url = gateway.initiate_payment(order, request)

        # If Cash on Delivery, notify admin
        if method == 'COD':
            OrderService.send_admin_new_order_email(order)

        return redirect(redirect_url)


# Dedicated SSLCommerz initiate endpoint
class SSLCommerzInitiateView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)
        method_hint = request.POST.get('payment_method', 'SSLCOMMERZ').upper()
        order.payment_method = method_hint
        order.save(update_fields=['payment_method'])

        gateway_url, _ = SSLCommerzGatewayService.initiate_payment(order, method_hint=method_hint)
        if gateway_url:
            return redirect(gateway_url)

        messages.error(request, 'Unable to initiate payment session with SSLCommerz. Please try again or choose COD.')
        return redirect('payments:payment_select', order_number=order.order_number)


# Server-to-server IPN listener from SSLCommerz
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzIPNView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        val_id = request.POST.get('val_id')
        tran_id = request.POST.get('tran_id')

        if not val_id or not tran_id:
            logger.warning("SSLCommerz IPN received without val_id or tran_id: %s", request.POST)
            return HttpResponse('Missing IPN validation parameters', status=400)

        is_valid, validation_data = SSLCommerzGatewayService.validate_ipn(val_id)
        payment = Payment.objects.filter(transaction_id=tran_id).select_related('order').first()

        if not payment:
            logger.error("SSLCommerz IPN transaction_id not found: %s", tran_id)
            return HttpResponse('Transaction not found', status=404)

        if is_valid:
            payment.status = 'SUCCESS'
            payment.val_id = val_id
            payment.bank_tran_id = validation_data.get('bank_tran_id', '')
            payment.card_type = validation_data.get('card_type', '')
            payment.raw_response = str(validation_data)
            payment.save(update_fields=['status', 'val_id', 'bank_tran_id', 'card_type', 'raw_response'])

            order = payment.order
            order.is_paid = True
            order.save(update_fields=['is_paid'])

            # Automatically advance order status to CONFIRMED and notify buyer
            OrderService.advance_order_status(order, 'CONFIRMED')

            # Automatically book shipment with Steadfast Courier
            try:
                SteadfastService.create_order(order)
            except Exception:
                logger.exception("Failed to auto-book Steadfast shipment for order #%s", order.order_number)

            return HttpResponse('IPN Verified')

        payment.status = 'FAILED'
        payment.raw_response = str(validation_data)
        payment.save(update_fields=['status', 'raw_response'])
        return HttpResponse('Payment validation failed', status=400)


# Browser redirect after payment completion on SSLCommerz
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzSuccessView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = get_object_or_404(Order, order_number=order_number)
        messages.success(request, f"Payment received successfully for Order #{order.order_number}!")
        return redirect('orders:order_success', order_number=order.order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return redirect('orders:order_success', order_number=order_number)


# Browser redirect on payment failure
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzFailView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        messages.error(request, 'Payment was declined or failed. Please select an alternative payment method.')
        return redirect('payments:payment_select', order_number=order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return redirect('payments:payment_select', order_number=order_number)


# Browser redirect on user payment cancellation
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzCancelView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        messages.info(request, 'Payment session was cancelled. You can retry at your convenience.')
        return redirect('payments:payment_select', order_number=order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return redirect('payments:payment_select', order_number=order_number)


# View simulating bKash payment processing gateway (kept for standalone testing if needed)
class BkashGatewaySimulateView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)
        payment = Payment.objects.filter(order=order, method='BKASH').order_by('-created_at').first()
        return render(
            request,
            'payments/bkash_gateway.html',
            {
                'order': order,
                'payment': payment,
                'title': f"bKash Payment - #{order.order_number}"
            }
        )


# View simulating Nagad payment processing gateway (kept for standalone testing if needed)
class NagadGatewaySimulateView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)
        payment = Payment.objects.filter(order=order, method='NAGAD').order_by('-created_at').first()
        return render(
            request,
            'payments/nagad_gateway.html',
            {
                'order': order,
                'payment': payment,
                'title': f"Nagad Payment - #{order.order_number}"
            }
        )
