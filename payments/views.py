from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpRequest
from orders.models import Order
from orders.services import OrderService
from .models import Payment
from .services import PaymentGatewayFactory

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

        # Notify administrator if Cash on Delivery order is placed
        if method == 'COD':
            OrderService.send_admin_new_order_email(order)

        return redirect(redirect_url)

# View simulating bKash payment processing gateway
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

# View simulating Nagad payment processing gateway
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
