from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'method', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('transaction_id', 'order__order_number', 'gateway_reference')
    list_editable = ('status',)
    readonly_fields = ('transaction_id', 'created_at', 'updated_at')
    actions = ['mark_success', 'mark_failed', 'mark_cancelled']

    def mark_success(self, request, queryset):
        queryset.update(status='SUCCESS')
        for payment in queryset:
            payment.order.is_paid = True
            payment.order.save()
        self.message_user(request, 'Selected payments marked as SUCCESS and corresponding orders updated to Paid.')
    mark_success.short_description = 'Mark selected payments as SUCCESS'

    def mark_failed(self, request, queryset):
        queryset.update(status='FAILED')
        self.message_user(request, 'Selected payments marked as FAILED.')
    mark_failed.short_description = 'Mark selected payments as FAILED'

    def mark_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
        self.message_user(request, 'Selected payments marked as CANCELLED.')
    mark_cancelled.short_description = 'Mark selected payments as CANCELLED'
