from typing import Any
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import HttpResponse, HttpRequest
from products.models import Product
from .cart import Cart

# View rendering the shopping cart overview page
class CartDetailView(TemplateView):
    template_name = 'cart/cart_detail.html'

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shopping Cart'
        return context

# View handling adding items to shopping cart
class CartAddView(View):

    def post(self, request: HttpRequest, product_id: int, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        quantity = max(1, min(quantity, min(4, product.stock_qty)))
        if product.stock_qty <= 0:
            messages.error(request, f"Sorry, {product.name} is currently out of stock.")
            return redirect(product.get_absolute_url())

        cart.add(product=product, quantity=quantity, override_quantity=False)
        messages.success(request, f"Added {quantity}× {product.name} to your cart!")

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cart:cart_detail'
        return redirect(next_url)

# View handling cart item quantity increments, decrements, or manual updates
class CartUpdateView(View):

    def post(self, request: HttpRequest, product_id: int, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        action = request.POST.get('action')
        current_qty = cart.cart.get(str(product_id), {}).get('quantity', 1)

        if action == 'increase':
            new_qty = min(4, current_qty + 1)
        elif action == 'decrease':
            new_qty = current_qty - 1
        else:
            try:
                new_qty = int(request.POST.get('quantity', current_qty))
            except (ValueError, TypeError):
                new_qty = current_qty

        if new_qty <= 0:
            cart.remove(product)
            messages.info(request, f"Removed {product.name} from your cart.")
        else:
            clamped_qty = max(1, min(new_qty, min(4, product.stock_qty)))
            cart.add(product=product, quantity=clamped_qty, override_quantity=True)
            if new_qty > min(4, product.stock_qty):
                messages.warning(request, f"Maximum allowed quantity is {min(4, product.stock_qty)} for {product.name}.")
            else:
                messages.success(request, f"Updated quantity for {product.name}.")

        return redirect('cart:cart_detail')

# View handling item removal from cart
class CartRemoveView(View):

    def post(self, request: HttpRequest, product_id: int, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        cart.remove(product)
        messages.info(request, f"Removed {product.name} from your cart.")
        return redirect('cart:cart_detail')

# View clearing all items from cart
class CartClearView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        cart.clear()
        messages.info(request, 'Your shopping cart has been cleared.')
        return redirect('cart:cart_detail')

# View enabling immediate product purchase and instant checkout redirect
class BuyNowView(View):

    def post(self, request: HttpRequest, product_id: int, *args, **kwargs) -> HttpResponse:
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)

        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        quantity = max(1, min(quantity, min(4, product.stock_qty)))
        if product.stock_qty <= 0:
            messages.error(request, f"Sorry, {product.name} is currently out of stock.")
            return redirect(product.get_absolute_url())

        cart.add(product=product, quantity=quantity, override_quantity=False)
        return redirect('orders:checkout')
