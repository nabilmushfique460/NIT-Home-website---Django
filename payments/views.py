from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from orders.models import Order
from orders.services import OrderService
from .models import Payment
from .services import PaymentGatewayFactory

class PaymentSelectView(View):

    def get(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        return render(request, 'payments/payment_select.html', {
            'order': order,
            'title': f'Select Payment Method - #{order.order_number}'
        })

class ChoosePaymentView(View):

    def post(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        method = request.POST.get('payment_method', 'COD').upper()
        order.payment_method = method
        order.save(update_fields=['payment_method'])

        gateway = PaymentGatewayFactory.get_gateway(method)
        redirect_url = gateway.initiate_payment(order, request)
        if method == 'COD':
            OrderService.send_admin_new_order_email(order)
        return redirect(redirect_url)

class BkashGatewaySimulateView(View):

    def get(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        payment = Payment.objects.filter(order=order, method='BKASH').order_by('-created_at').first()
        return render(request, 'payments/bkash_gateway.html', {'order': order, 'payment': payment, 'title': f'bKash Payment - #{order.order_number}'})

class NagadGatewaySimulateView(View):

    def get(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number)
        payment = Payment.objects.filter(order=order, method='NAGAD').order_by('-created_at').first()
        return render(request, 'payments/nagad_gateway.html', {'order': order, 'payment': payment, 'title': f'Nagad Payment - #{order.order_number}'})
