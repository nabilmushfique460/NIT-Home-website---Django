from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from products.models import Product
from .cart import Cart

class CartDetailView(TemplateView):
    template_name = 'cart/cart_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Shopping Cart'
        return context

class CartAddView(View):

    def post(self, request, product_id, *args, **kwargs):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
        quantity = max(1, min(quantity, min(4, product.stock_qty)))
        if product.stock_qty <= 0:
            messages.error(request, f'Sorry, {product.name} is currently out of stock.')
            return redirect(product.get_absolute_url())
        cart.add(product=product, quantity=quantity, override_quantity=False)
        messages.success(request, f'Added {quantity}× {product.name} to your cart!')
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'cart:cart_detail'
        return redirect(next_url)

class CartUpdateView(View):

    def post(self, request, product_id, *args, **kwargs):
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
            messages.info(request, f'Removed {product.name} from your cart.')
        else:
            clamped_qty = max(1, min(new_qty, min(4, product.stock_qty)))
            cart.add(product=product, quantity=clamped_qty, override_quantity=True)
            if new_qty > min(4, product.stock_qty):
                messages.warning(request, f'Maximum allowed quantity is {min(4, product.stock_qty)} for {product.name}.')
            else:
                messages.success(request, f'Updated quantity for {product.name}.')
        return redirect('cart:cart_detail')

class CartRemoveView(View):

    def post(self, request, product_id, *args, **kwargs):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        cart.remove(product)
        messages.info(request, f'Removed {product.name} from your cart.')
        return redirect('cart:cart_detail')

class CartClearView(View):

    def post(self, request, *args, **kwargs):
        cart = Cart(request)
        cart.clear()
        messages.info(request, 'Your shopping cart has been cleared.')
        return redirect('cart:cart_detail')

class BuyNowView(View):

    def post(self, request, product_id, *args, **kwargs):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
        quantity = max(1, min(quantity, min(4, product.stock_qty)))
        if product.stock_qty <= 0:
            messages.error(request, f'Sorry, {product.name} is currently out of stock.')
            return redirect(product.get_absolute_url())
        cart.add(product=product, quantity=quantity, override_quantity=False)
        return redirect('orders:checkout')
