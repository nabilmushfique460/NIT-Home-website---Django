from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'method', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('transaction_id', 'order__order_number', 'gateway_reference')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at')
