from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'quantity', 'line_total')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'full_name', 'phone', 'total_amount', 
        'payment_method', 'is_paid', 'status', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'is_paid', 'created_at')
    search_fields = ('order_number', 'full_name', 'email', 'phone', 'street_address')
    list_editable = ('status', 'is_paid')
    readonly_fields = ('order_number', 'subtotal', 'shipping_fee', 'total_amount', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['mark_confirmed', 'mark_shipped', 'mark_delivered', 'mark_paid']

    def mark_confirmed(self, request, queryset):
        queryset.update(status='CONFIRMED')
    mark_confirmed.short_description = "Mark selected orders as Confirmed"

    def mark_shipped(self, request, queryset):
        queryset.update(status='SHIPPED')
    mark_shipped.short_description = "Mark selected orders as Shipped"

    def mark_delivered(self, request, queryset):
        queryset.update(status='DELIVERED')
    mark_delivered.short_description = "Mark selected orders as Delivered"

    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True)
    mark_paid.short_description = "Mark selected orders as Paid"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'unit_price', 'quantity', 'line_total')
    search_fields = ('order__order_number', 'product_name')
