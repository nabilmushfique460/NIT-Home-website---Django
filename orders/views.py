from typing import Any
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpRequest
from .models import Order
from .forms import CheckoutForm
from .services import OrderService
from cart.cart import Cart
from accounts.models import Address

# View handling checkout form presentation, prefill from profile, and order submission
class CheckoutView(FormView):
    template_name = 'orders/checkout.html'
    form_class = CheckoutForm

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        if cart.is_empty():
            messages.warning(request, 'Your cart is empty. Please add items before checkout.')
            return redirect('products:product_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        # Prefill customer details and default shipping address if authenticated
        if self.request.user.is_authenticated:
            user = self.request.user
            initial['full_name'] = f"{user.first_name} {user.last_name}".strip() or user.email
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

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Secure Checkout'
        if self.request.user.is_authenticated:
            context['saved_addresses'] = Address.objects.filter(user=self.request.user)
        return context

    def form_valid(self, form: CheckoutForm) -> HttpResponse:
        cart = Cart(self.request)
        user = self.request.user if self.request.user.is_authenticated else None

        # Create order through OrderService
        try:
            order = OrderService.create_order_from_cart(cart, form.cleaned_data, user=user)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # Save shipping address to user profile if opted in
        if user and form.cleaned_data.get('save_address_to_profile'):
            Address.objects.get_or_create(
                user=user,
                street_address=form.cleaned_data['street_address'],
                city=form.cleaned_data['city'],
                postal_code=form.cleaned_data['postal_code'],
                defaults={
                    'full_name': form.cleaned_data['full_name'],
                    'phone': form.cleaned_data['phone'],
                    'state_or_division': form.cleaned_data.get('state_or_division', ''),
                    'country': form.cleaned_data.get('country', 'Bangladesh'),
                }
            )

        # Clear shopping cart after successful checkout
        cart.clear()
        return redirect('payments:payment_select', order_number=order.order_number)

# View rendering order placement confirmation page
class OrderSuccessView(DetailView):
    model = Order
    template_name = 'orders/order_success.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = f"Order #{self.object.order_number} Placed"
        return context

# View rendering detailed invoice, item breakdown, and delivery timeline
class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = f"Invoice #{self.object.order_number}"
        context['items'] = self.object.items.select_related('product')
        return context

# View displaying customer's historical orders with pagination
class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Orders'
        return context

# View handling order cancellation requests initiated by customers
class OrderCancelView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, order_number: str, *args, **kwargs) -> HttpResponse:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        try:
            OrderService.request_order_cancellation(order, request.user)
            messages.success(
                request,
                f"Cancellation request for Order #{order.order_number} submitted. Awaiting admin review."
            )
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('orders:order_detail', order_number=order.order_number)
