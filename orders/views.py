from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Order
from .forms import CheckoutForm
from .services import OrderService
from cart.cart import Cart
from accounts.models import Address
from payments.services import PaymentGatewayFactory

class CheckoutView(FormView):
    template_name = 'orders/checkout.html'
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        cart = Cart(request)
        if cart.is_empty():
            messages.warning(request, 'Your cart is empty. Please add items before checkout.')
            return redirect('products:product_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.request.user.is_authenticated:
            user = self.request.user
            initial['full_name'] = f'{user.first_name} {user.last_name}'.strip() or user.email
            initial['email'] = user.email
            if hasattr(user, 'profile') and user.profile.phone:
                initial['phone'] = user.profile.phone
            default_address = Address.objects.filter(user=user, is_default=True).first()
            if not default_address:
                default_address = Address.objects.filter(user=user).first()
            if default_address:
                initial['street_address'] = default_address.street_address
                initial['city'] = default_address.city
                initial['state_or_division'] = default_address.state_or_division
                initial['postal_code'] = default_address.postal_code
                initial['country'] = default_address.country
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Secure Checkout'
        if self.request.user.is_authenticated:
            context['saved_addresses'] = Address.objects.filter(user=self.request.user)
        return context

    def form_valid(self, form):
        cart = Cart(self.request)
        user = self.request.user if self.request.user.is_authenticated else None
        try:
            order = OrderService.create_order_from_cart(cart, form.cleaned_data, user=user)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        if user and form.cleaned_data.get('save_address_to_profile'):
            Address.objects.get_or_create(user=user, street_address=form.cleaned_data['street_address'], city=form.cleaned_data['city'], postal_code=form.cleaned_data['postal_code'], defaults={'full_name': form.cleaned_data['full_name'], 'phone': form.cleaned_data['phone'], 'state_or_division': form.cleaned_data.get('state_or_division', ''), 'country': form.cleaned_data.get('country', 'Bangladesh')})
        cart.clear()
        payment_method = form.cleaned_data['payment_method']
        gateway = PaymentGatewayFactory.get_gateway(payment_method)
        redirect_url = gateway.initiate_payment(order, self.request)
        return redirect(redirect_url)

class OrderSuccessView(DetailView):
    model = Order
    template_name = 'orders/order_success.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Order #{self.object.order_number} Confirmed'
        return context

class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Invoice #{self.object.order_number}'
        return context

class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Orders'
        return context

class OrderCancelView(LoginRequiredMixin, View):

    def post(self, request, order_number, *args, **kwargs):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        try:
            OrderService.cancel_order(order)
            messages.success(request, f'Order #{order.order_number} has been cancelled successfully.')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('orders:order_detail', order_number=order.order_number)
