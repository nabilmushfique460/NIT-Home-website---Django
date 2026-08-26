import uuid
from django.db import models
from django.conf import settings
from products.models import Product

# Model representing customer hardware orders and delivery status
class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Placed'),
        ('CONFIRMED', 'Confirmed'),
        ('PACKAGING', 'Bench Packaging'),
        ('SHIPPED', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCEL_REQUESTED', 'Cancellation Requested'),
        ('CANCELLED', 'Cancelled'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('COD', 'Cash on Delivery (COD)'),
        ('BKASH', 'bKash Mobile Financial Service'),
        ('NAGAD', 'Nagad Mobile Financial Service'),
    )

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state_or_division = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='Bangladesh')
    order_notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='COD')
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Automatically generate unique alphanumeric order reference
        if not self.order_number:
            self.order_number = f"NIT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def payment_status(self) -> str:
        return 'PAID' if self.is_paid else 'PENDING'

    @property
    def status_step_index(self) -> int:
        steps = {
            'PENDING': 1,
            'CONFIRMED': 2,
            'PACKAGING': 3,
            'SHIPPED': 4,
            'DELIVERED': 5,
            'CANCEL_REQUESTED': 0,
            'CANCELLED': 0,
        }
        return steps.get(self.status, 1)

    @property
    def progress_percentage(self) -> int:
        percentages = {
            'PENDING': 0,
            'CONFIRMED': 25,
            'PACKAGING': 50,
            'SHIPPED': 75,
            'DELIVERED': 100,
            'CANCEL_REQUESTED': 0,
            'CANCELLED': 0,
        }
        return percentages.get(self.status, 0)

    @property
    def can_be_cancelled(self) -> bool:
        return self.status in ['PENDING', 'CONFIRMED', 'PACKAGING']

    def __str__(self) -> str:
        return f"Order #{self.order_number} - {self.full_name} (${self.total_amount})"

# Model representing individual line items within an order
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.name
        if not self.unit_price and self.product:
            self.unit_price = self.product.price
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product_name} in #{self.order.order_number}"
