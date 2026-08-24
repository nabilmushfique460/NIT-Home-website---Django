from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from orders.models import Order
from .models import Payment
from .services import BkashPayment, NagadPayment

class BkashGatewaySimulateView(View):
    """bKash Payment Gateway Interface (Server-side rendered, zero-JS)."""

    def get(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        payment = Payment.objects.filter(order=order, method='BKASH').order_by('-created_at').first()

        return render(request, 'payments/bkash_gateway.html', {
            'order': order,
            'payment': payment,
            'title': f"bKash Payment Gateway - #{order.order_number}"
        })

    def post(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        wallet_number = request.POST.get('wallet_number', '').strip()
        pin = request.POST.get('pin', '').strip()

        if not wallet_number or len(wallet_number) < 11:
            messages.error(request, "Please provide a valid 11-digit bKash account number.")
            return redirect('payments:bkash_gateway', order_number=order.order_number)

        gateway = BkashPayment()
        success = gateway.verify_payment({
            'order_number': order_number,
            'wallet_number': wallet_number,
            'pin': pin
        })

        if success:
            messages.success(request, f"bKash payment of ${order.total_amount} verified successfully!")
            return redirect('orders:order_success', order_number=order.order_number)
        else:
            messages.error(request, "bKash verification failed. Please try again.")
            return redirect('payments:bkash_gateway', order_number=order.order_number)

class NagadGatewaySimulateView(View):
    """Nagad Payment Gateway Interface (Server-side rendered, zero-JS)."""

    def get(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        payment = Payment.objects.filter(order=order, method='NAGAD').order_by('-created_at').first()

        return render(request, 'payments/nagad_gateway.html', {
            'order': order,
            'payment': payment,
            'title': f"Nagad Payment Gateway - #{order.order_number}"
        })

    def post(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        wallet_number = request.POST.get('wallet_number', '').strip()
        otp = request.POST.get('otp', '').strip()

        if not wallet_number or len(wallet_number) < 11:
            messages.error(request, "Please provide a valid 11-digit Nagad account number.")
            return redirect('payments:nagad_gateway', order_number=order.order_number)

        gateway = NagadPayment()
        success = gateway.verify_payment({
            'order_number': order_number,
            'wallet_number': wallet_number,
            'otp': otp
        })

        if success:
            messages.success(request, f"Nagad payment of ${order.total_amount} verified successfully!")
            return redirect('orders:order_success', order_number=order.order_number)
        else:
            messages.error(request, "Nagad verification failed. Please try again.")
            return redirect('payments:nagad_gateway', order_number=order.order_number)


class BkashCallbackView(View):
    """bKash Callback/Webhook simulation view."""

    def post(self, request, transaction_id, *args, **kwargs):
        payment = get_object_or_404(Payment, transaction_id=transaction_id)
        order = payment.order
        wallet_number = request.POST.get('wallet_number', '').strip()
        pin = request.POST.get('pin', '').strip()

        gateway = BkashPayment()
        success = gateway.verify_payment({
            'order_number': order.order_number,
            'wallet_number': wallet_number,
            'pin': pin
        })

        if success:
            messages.success(request, f"bKash payment of ${order.total_amount} verified successfully!")
            return redirect('orders:order_success', order_number=order.order_number)
        else:
            messages.error(request, "bKash verification failed.")
            return redirect('payments:bkash_gateway', order_number=order.order_number)


class NagadCallbackView(View):
    """Nagad Callback/Webhook simulation view."""

    def post(self, request, transaction_id, *args, **kwargs):
        payment = get_object_or_404(Payment, transaction_id=transaction_id)
        order = payment.order
        wallet_number = request.POST.get('wallet_number', '').strip()
        otp = request.POST.get('otp', '').strip()

        gateway = NagadPayment()
        success = gateway.verify_payment({
            'order_number': order.order_number,
            'wallet_number': wallet_number,
            'otp': otp
        })

        if success:
            messages.success(request, f"Nagad payment of ${order.total_amount} verified successfully!")
            return redirect('orders:order_success', order_number=order.order_number)
        else:
            messages.error(request, "Nagad verification failed.")
            return redirect('payments:nagad_gateway', order_number=order.order_number)

