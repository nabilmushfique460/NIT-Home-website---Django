from django.contrib import admin
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from .models import Order, OrderItem
from .services import OrderService
from payments.models import Payment

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('transaction_id', 'method', 'amount', 'currency', 'status', 'created_at')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'phone', 'total_amount', 'payment_method', 'status', 'approval_action', 'created_at')
    list_filter = ('status', 'payment_method', 'is_paid', 'created_at')
    search_fields = ('order_number', 'full_name', 'email', 'phone', 'street_address')
    readonly_fields = ('order_number', 'subtotal', 'shipping_fee', 'total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline, PaymentInline]
    date_hierarchy = 'created_at'
    actions = ['approve_selected_orders', 'mark_shipped', 'mark_delivered', 'mark_cancelled']

    def approval_action(self, obj):
        if obj.status == 'PENDING':
            url = reverse('admin:orders_order_approve', args=[obj.pk])
            return format_html('<a class="button" style="background:#22c55e;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">1-Click Approve</a>', url)
        return format_html('<span style="color:#22c55e;font-weight:600;">Confirmed</span>' if obj.status == 'CONFIRMED' else obj.get_status_display())
    approval_action.short_description = 'Order Approval'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/approve/', self.admin_site.admin_view(self.approve_order_view), name='orders_order_approve'),
        ]
        return custom_urls + urls

    def approve_order_view(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        if order.status != 'CONFIRMED':
            order.status = 'CONFIRMED'
            order.save(update_fields=['status'])
            OrderService.send_order_approved_email(order)
            messages.success(request, f"Order #{order.order_number} approved successfully. Confirmation email dispatched to {order.email}.")
        else:
            messages.info(request, f"Order #{order.order_number} is already confirmed.")
        return redirect('admin:orders_order_changelist')

    def approve_selected_orders(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status != 'CONFIRMED':
                order.status = 'CONFIRMED'
                order.save(update_fields=['status'])
                OrderService.send_order_approved_email(order)
                count += 1
        self.message_user(request, f"{count} orders approved and confirmation emails sent.")
    approve_selected_orders.short_description = 'Approve & confirm selected orders'

    def mark_shipped(self, request, queryset):
        queryset.update(status='SHIPPED')
    mark_shipped.short_description = 'Mark selected orders as Shipped'

    def mark_delivered(self, request, queryset):
        queryset.update(status='DELIVERED')
    mark_delivered.short_description = 'Mark selected orders as Delivered'

    def mark_cancelled(self, request, queryset):
        queryset.update(status='CANCELLED')
    mark_cancelled.short_description = 'Mark selected orders as Cancelled'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'unit_price', 'quantity', 'line_total')
    search_fields = ('order__order_number', 'product_name')
