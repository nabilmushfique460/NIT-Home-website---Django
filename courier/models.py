from django.db import models


class Shipment(models.Model):
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='shipment')
    consignment_id = models.CharField(max_length=50, blank=True, db_index=True)
    tracking_code = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=40, default='pending')
    raw_last_webhook = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Courier Shipment'
        verbose_name_plural = 'Courier Shipments'

    def __str__(self) -> str:
        return f"Shipment for #{self.order.order_number} ({self.status})"
