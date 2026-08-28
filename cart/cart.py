from decimal import Decimal
from typing import Iterator, Any
from django.conf import settings
from django.http import HttpRequest
from products.models import Product

# OOP shopping cart implementation managing session cart state, quantities, and totals
class Cart:
    FREE_SHIPPING_THRESHOLD = Decimal('60000.00')
    STANDARD_SHIPPING_FEE = Decimal('150.00')

    def __init__(self, request: HttpRequest) -> None:
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart: dict[str, dict[str, Any]] = cart

    def add(self, product: Product, quantity: int = 1, override_quantity: bool = False) -> None:
        product_id = str(product.id)
        if product.stock_qty <= 0:
            return
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        if override_quantity:
            new_qty = quantity
        else:
            new_qty = self.cart[product_id]['quantity'] + quantity
        # Clamp quantity between 1 and available stock
        self.cart[product_id]['quantity'] = max(1, min(new_qty, product.stock_qty))
        self.save()

    def save(self) -> None:
        self.session.modified = True

    def remove(self, product: Product) -> None:
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self) -> None:
        self.session[settings.CART_SESSION_ID] = {}
        self.save()

    def __iter__(self) -> Iterator[dict[str, Any]]:
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart_copy = self.cart.copy()
        for product in products:
            cart_copy[str(product.id)]['product'] = product
        for item in cart_copy.values():
            if 'product' not in item:
                continue
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self) -> int:
        return sum(item['quantity'] for item in self.cart.values())

    def get_subtotal(self) -> Decimal:
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def get_shipping_fee(self) -> Decimal:
        subtotal = self.get_subtotal()
        if subtotal == Decimal('0.00') or subtotal >= self.FREE_SHIPPING_THRESHOLD:
            return Decimal('0.00')
        return self.STANDARD_SHIPPING_FEE

    def get_grand_total(self) -> Decimal:
        return self.get_subtotal() + self.get_shipping_fee()

    def is_empty(self) -> bool:
        return len(self.cart) == 0
