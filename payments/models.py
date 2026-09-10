import uuid
from django.db import models
from orders.models import Order

def generate_transaction_id() -> str:
    return f"NIT{uuid.uuid4().hex[:18].upper()}"


# Model representing financial transactions and gateway logs for customer orders
class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Successful / Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled by User'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=64, unique=True, default=generate_transaction_id)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    gateway_session_key = models.CharField(max_length=100, blank=True, null=True)
    val_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    bank_tran_id = models.CharField(max_length=100, blank=True, null=True)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    raw_response = models.TextField(blank=True, null=True, help_text='Server-side gateway audit log')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['val_id']),
        ]

    def __str__(self) -> str:
        return f"{self.method} Payment ({self.transaction_id}) - ৳{self.amount} [{self.status}]"
