from decimal import Decimal
from django.conf import settings
from products.models import Product

class Cart:
    """Session-backed Cart management class."""

    FREE_SHIPPING_THRESHOLD = Decimal('500.00')
    STANDARD_SHIPPING_FEE = Decimal('15.00')

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product: Product, quantity: int = 1, override_quantity: bool = False) -> None:
        """Add a product to the cart or update its quantity."""
        product_id = str(product.id)
        
        # Enforce stock limits
        if product.stock_qty <= 0:
            return

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price),
            }

        if override_quantity:
            new_qty = quantity
        else:
            new_qty = self.cart[product_id]['quantity'] + quantity

        # Clamp between 1 and product stock
        self.cart[product_id]['quantity'] = max(1, min(new_qty, product.stock_qty))
        self.save()

    def save(self) -> None:
        """Mark the session as modified to ensure it gets saved."""
        self.session.modified = True

    def remove(self, product: Product) -> None:
        """Remove a product from the cart."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self) -> None:
        """Empty the cart session."""
        self.session[settings.CART_SESSION_ID] = {}
        self.save()

    def __iter__(self):
        """Iterate over the items in the cart and fetch the products from the database."""
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            # If a product was deleted from DB while in cart
            if 'product' not in item:
                continue
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self) -> int:
        """Count all items in the cart."""
        return sum(item['quantity'] for item in self.cart.values())

    def get_subtotal(self) -> Decimal:
        """Calculate the sum of all item prices."""
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def get_shipping_fee(self) -> Decimal:
        """Free shipping if subtotal >= threshold, else standard fee."""
        subtotal = self.get_subtotal()
        if subtotal == Decimal('0.00') or subtotal >= self.FREE_SHIPPING_THRESHOLD:
            return Decimal('0.00')
        return self.STANDARD_SHIPPING_FEE

    def get_grand_total(self) -> Decimal:
        """Subtotal + Shipping fee."""
        return self.get_subtotal() + self.get_shipping_fee()

    def is_empty(self) -> bool:
        return len(self.cart) == 0
