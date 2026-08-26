from django.contrib import admin
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from .models import Order, OrderItem
from .services import OrderService
from payments.models import Payment

# Inline configuration for order line items in Order Admin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False

# Inline configuration for order payment records in Order Admin
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('transaction_id', 'method', 'amount', 'currency', 'status', 'created_at')
    can_delete = False

# Admin configuration for managing orders, lifecycle actions, and status progression
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'full_name',
        'phone',
        'total_amount',
        'payment_method',
        'status',
        'step_action',
        'created_at'
    )
    list_filter = ('status', 'payment_method', 'is_paid', 'created_at')
    search_fields = ('order_number', 'full_name', 'email', 'phone', 'street_address')
    readonly_fields = ('order_number', 'subtotal', 'shipping_fee', 'total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline, PaymentInline]
    date_hierarchy = 'created_at'
    actions = [
        'mark_as_confirmed',
        'mark_as_packaging',
        'mark_as_shipped',
        'mark_as_delivered',
        'approve_selected_cancellations'
    ]

    def step_action(self, obj: Order) -> str:
        if obj.status == 'PENDING':
            url = reverse('admin:orders_order_advance', args=[obj.pk, 'CONFIRMED'])
            return format_html(
                '<a class="button" style="background:#22c55e;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">1. Confirm Order</a>',
                url
            )
        elif obj.status == 'CONFIRMED':
            url = reverse('admin:orders_order_advance', args=[obj.pk, 'PACKAGING'])
            return format_html(
                '<a class="button" style="background:#0ea5e9;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">2. Start Packaging</a>',
                url
            )
        elif obj.status == 'PACKAGING':
            url = reverse('admin:orders_order_advance', args=[obj.pk, 'SHIPPED'])
            return format_html(
                '<a class="button" style="background:#f59e0b;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">3. Mark In Transit</a>',
                url
            )
        elif obj.status == 'SHIPPED':
            url = reverse('admin:orders_order_advance', args=[obj.pk, 'DELIVERED'])
            return format_html(
                '<a class="button" style="background:#10b981;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">4. Mark Delivered</a>',
                url
            )
        elif obj.status == 'CANCEL_REQUESTED':
            url = reverse('admin:orders_order_approve_cancel', args=[obj.pk])
            return format_html(
                '<a class="button" style="background:#ef4444;color:#fff;font-weight:700;padding:4px 10px;border-radius:4px;text-decoration:none;" href="{}">Approve Cancellation</a>',
                url
            )
        elif obj.status == 'DELIVERED':
            return format_html('<span style="color:#10b981;font-weight:700;">{}</span>', 'Delivered')
        elif obj.status == 'CANCELLED':
            return format_html('<span style="color:#ef4444;font-weight:700;">{}</span>', 'Cancelled')
        return obj.get_status_display()
    step_action.short_description = 'Next Step Action'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:order_id>/advance/<str:next_status>/',
                self.admin_site.admin_view(self.advance_order_view),
                name='orders_order_advance'
            ),
            path(
                '<int:order_id>/approve-cancel/',
                self.admin_site.admin_view(self.approve_cancel_view),
                name='orders_order_approve_cancel'
            ),
        ]
        return custom_urls + urls

    def advance_order_view(self, request, order_id: int, next_status: str):
        order = get_object_or_404(Order, pk=order_id)
        valid_statuses = dict(Order.STATUS_CHOICES)
        if next_status in valid_statuses:
            OrderService.advance_order_status(order, next_status)
            messages.success(
                request,
                f"Order #{order.order_number} advanced to '{valid_statuses[next_status]}'. User notification and email dispatched."
            )
        else:
            messages.error(request, 'Invalid status transition.')
        return redirect('admin:orders_order_changelist')

    def approve_cancel_view(self, request, order_id: int):
        order = get_object_or_404(Order, pk=order_id)
        OrderService.approve_order_cancellation(order)
        messages.success(
            request,
            f"Order #{order.order_number} cancellation approved. Inventory restored, user notification and confirmation email dispatched."
        )
        return redirect('admin:orders_order_changelist')

    def mark_as_confirmed(self, request, queryset):
        count = 0
        for order in queryset:
            OrderService.advance_order_status(order, 'CONFIRMED')
            count += 1
        self.message_user(request, f"{count} orders updated to Confirmed.")
    mark_as_confirmed.short_description = 'Advance selected orders to Confirmed'

    def mark_as_packaging(self, request, queryset):
        count = 0
        for order in queryset:
            OrderService.advance_order_status(order, 'PACKAGING')
            count += 1
        self.message_user(request, f"{count} orders updated to Bench Packaging.")
    mark_as_packaging.short_description = 'Advance selected orders to Bench Packaging'

    def mark_as_shipped(self, request, queryset):
        count = 0
        for order in queryset:
            OrderService.advance_order_status(order, 'SHIPPED')
            count += 1
        self.message_user(request, f"{count} orders updated to In Transit.")
    mark_as_shipped.short_description = 'Advance selected orders to In Transit'

    def mark_as_delivered(self, request, queryset):
        count = 0
        for order in queryset:
            OrderService.advance_order_status(order, 'DELIVERED')
            count += 1
        self.message_user(request, f"{count} orders updated to Delivered.")
    mark_as_delivered.short_description = 'Advance selected orders to Delivered'

    def approve_selected_cancellations(self, request, queryset):
        count = 0
        for order in queryset:
            if order.status == 'CANCEL_REQUESTED':
                OrderService.approve_order_cancellation(order)
                count += 1
        self.message_user(request, f"{count} cancellations approved and inventory restored.")
    approve_selected_cancellations.short_description = 'Approve selected cancellation requests'

# Admin configuration for OrderItem
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'unit_price', 'quantity', 'line_total')
    search_fields = ('order__order_number', 'product_name')
