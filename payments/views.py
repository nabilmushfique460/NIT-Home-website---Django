import logging
from typing import Optional
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpRequest, HttpResponseBadRequest, HttpResponseNotFound
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from orders.models import Order
from orders.services import OrderService
from .models import Payment
from .services import PaymentGatewayFactory, SSLCommerzGatewayService

logger = logging.getLogger(__name__)


def _get_user_order_or_404(request: HttpRequest, order_number: str) -> Order:
    """
    Ensure customer can only access their own order, while staff can inspect any order.
    """
    if request.user.is_staff:
        return get_object_or_404(Order, order_number=order_number)
    return get_object_or_404(Order, order_number=order_number, user=request.user)


# View rendering payment gateway selection screen
class PaymentSelectView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)

        # Guard: If order is already paid, redirect to invoice
        if order.is_paid:
            messages.info(request, f"Order #{order.order_number} has already been paid.")
            return redirect('orders:order_detail', order_number=order.order_number)

        # Guard: If order is cancelled, do not allow payment
        if order.status == 'CANCELLED':
            messages.error(request, f"Order #{order.order_number} has been cancelled.")
            return redirect('orders:order_detail', order_number=order.order_number)

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

        if order.is_paid:
            messages.info(request, f"Order #{order.order_number} is already paid.")
            return redirect('orders:order_detail', order_number=order.order_number)

        if order.status == 'CANCELLED':
            messages.error(request, f"Order #{order.order_number} has been cancelled.")
            return redirect('orders:order_detail', order_number=order.order_number)

        raw_method = request.POST.get('payment_method', 'COD').upper().strip()
        # Sanitize payment method to either COD or SSLCOMMERZ
        if raw_method in ('SSLCOMMERZ', 'ONLINE', 'BKASH', 'NAGAD'):
            method = 'SSLCOMMERZ'
        else:
            method = 'COD'

        order.payment_method = method
        order.save(update_fields=['payment_method', 'updated_at'])

        gateway = PaymentGatewayFactory.get_gateway(method)
        redirect_url = gateway.initiate_payment(order, request)

        return redirect(redirect_url)


# Dedicated SSLCommerz initiate endpoint
class SSLCommerzInitiateView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = _get_user_order_or_404(request, order_number)

        if order.is_paid:
            messages.info(request, f"Order #{order.order_number} is already paid.")
            return redirect('orders:order_detail', order_number=order.order_number)

        if order.status == 'CANCELLED':
            messages.error(request, f"Order #{order.order_number} has been cancelled.")
            return redirect('orders:order_detail', order_number=order.order_number)

        order.payment_method = 'SSLCOMMERZ'
        order.save(update_fields=['payment_method', 'updated_at'])

        gateway_url, payment = SSLCommerzGatewayService.initiate_payment(order, method_hint='SSLCOMMERZ')
        if gateway_url:
            return redirect(gateway_url)

        messages.error(
            request,
            'Unable to initiate secure checkout session with SSLCommerz. Please try again or select Cash on Delivery.'
        )
        return redirect('payments:payment_select', order_number=order.order_number)


# Server-to-server IPN listener from SSLCommerz
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzIPNView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        val_id = request.POST.get('val_id', '').strip()
        tran_id = request.POST.get('tran_id', '').strip()

        if not val_id or not tran_id:
            logger.warning("SSLCommerz IPN received without required val_id or tran_id: %s", request.POST)
            return HttpResponseBadRequest('Missing IPN validation parameters (val_id, tran_id)')

        # Step 1: Verify IPN signature locally if signature fields are present
        sig_ok, sig_msg = SSLCommerzGatewayService.verify_ipn_signature(request.POST.dict())
        if not sig_ok:
            logger.error("SSLCommerz IPN signature rejected: %s", sig_msg)
            return HttpResponse('Invalid IPN signature', status=400)

        # Step 2: Query SSLCOMMERZ validation API server-side
        is_valid, validation_data = SSLCommerzGatewayService.validate_transaction_with_gateway(val_id)
        if not is_valid:
            logger.warning("SSLCommerz IPN gateway validation failed for val_id %s: %s", val_id, validation_data)
            # Find payment and mark failed
            Payment.objects.filter(transaction_id=tran_id, status='PENDING').update(
                status='FAILED',
                val_id=val_id,
                raw_response=str(validation_data.get('error', 'Gateway validation failed'))
            )
            return HttpResponse('Gateway validation failed', status=400)

        # Step 3: Centralized atomic & idempotent settlement
        settled, message, order = SSLCommerzGatewayService.settle_payment_success(
            tran_id=tran_id,
            val_id=val_id,
            validation_data=validation_data
        )

        if not settled:
            logger.warning("SSLCommerz IPN settlement did not succeed: %s (tran_id=%s)", message, tran_id)
            return HttpResponse(f"Settlement failed: {message}", status=400)

        logger.info("SSLCommerz IPN verified and processed successfully for %s", tran_id)
        return HttpResponse('IPN Verified and Settled', status=200)


# Browser redirect after payment completion on SSLCommerz
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzSuccessView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_callback(request, order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_callback(request, order_number)

    def _handle_callback(self, request: HttpRequest, order_number: str) -> HttpResponse:
        # Check authentication if session available
        if request.user.is_authenticated:
            order = _get_user_order_or_404(request, order_number)
        else:
            order = get_object_or_404(Order, order_number=order_number)

        # 1. If order is already settled as paid (e.g. by fast IPN webhook):
        if order.is_paid:
            messages.success(request, f"Payment verified successfully for Order #{order.order_number}!")
            return redirect('orders:order_success', order_number=order.order_number)

        # 2. If not yet marked paid, attempt server-side verification using callback POST data:
        val_id = request.POST.get('val_id', '').strip()
        tran_id = request.POST.get('tran_id', '').strip()

        if val_id and tran_id:
            logger.info("Attempting browser callback validation for Order #%s (val_id=%s)", order.order_number, val_id)
            is_valid, val_data = SSLCommerzGatewayService.validate_transaction_with_gateway(val_id)
            if is_valid:
                settled, msg, settled_order = SSLCommerzGatewayService.settle_payment_success(
                    tran_id=tran_id,
                    val_id=val_id,
                    validation_data=val_data
                )
                if settled:
                    messages.success(request, f"Payment received and verified for Order #{order.order_number}!")
                    return redirect('orders:order_success', order_number=order.order_number)
                else:
                    logger.warning("Browser return settlement check failed: %s", msg)

        # 3. If validation could not be confirmed immediately:
        messages.warning(
            request,
            f"Your payment session was received. Order #{order.order_number} will update automatically once verified by our payment gateway."
        )
        return redirect('orders:order_detail', order_number=order.order_number)


# Browser redirect on payment failure
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzFailView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_fail(request, order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_fail(request, order_number)

    def _handle_fail(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = get_object_or_404(Order, order_number=order_number)
        tran_id = request.POST.get('tran_id', '').strip()
        error_msg = request.POST.get('error', 'Payment declined by issuer')

        if tran_id:
            Payment.objects.filter(transaction_id=tran_id, order=order, status='PENDING').update(
                status='FAILED',
                raw_response=f"Gateway Failure: {error_msg}"
            )
        else:
            Payment.objects.filter(order=order, status='PENDING').update(
                status='FAILED',
                raw_response=f"Gateway Failure: {error_msg}"
            )

        messages.error(request, 'Payment was declined or failed. Please select an alternative payment method or retry.')
        return redirect('payments:payment_select', order_number=order.order_number)


# Browser redirect on user payment cancellation
@method_decorator(csrf_exempt, name='dispatch')
class SSLCommerzCancelView(View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_cancel(request, order_number)

    def get(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        return self._handle_cancel(request, order_number)

    def _handle_cancel(self, request: HttpRequest, order_number: str) -> HttpResponse:
        order = get_object_or_404(Order, order_number=order_number)
        tran_id = request.POST.get('tran_id', '').strip()

        if tran_id:
            Payment.objects.filter(transaction_id=tran_id, order=order, status='PENDING').update(
                status='CANCELLED',
                raw_response='Payment session cancelled by user on gateway'
            )
        else:
            Payment.objects.filter(order=order, status='PENDING').update(
                status='CANCELLED',
                raw_response='Payment session cancelled by user on gateway'
            )

        messages.info(request, 'Payment session was cancelled. You can retry with SSLCommerz or choose Cash on Delivery.')
        return redirect('payments:payment_select', order_number=order.order_number)
