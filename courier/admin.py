from django.contrib import admin, messages
from .models import Shipment
from .services import SteadfastService


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'consignment_id', 'tracking_code', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'consignment_id', 'tracking_code', 'order__full_name')
    readonly_fields = ('created_at', 'updated_at', 'raw_last_webhook')
    actions = ['book_with_steadfast']

    @admin.action(description='Book selected orders with Steadfast Courier')
    def book_with_steadfast(self, request, queryset):
        success = 0
        for shipment in queryset:
            res = SteadfastService.create_order(shipment.order)
            if res.get('status') == 200 or res.get('consignment'):
                success += 1
        messages.success(request, f"Successfully dispatched {success} shipment(s) with Steadfast.")
