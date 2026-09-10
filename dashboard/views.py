from datetime import timedelta
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from orders.models import Order
from products.models import Product


class OwnerDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/overview.html'

    def test_func(self) -> bool:
        return bool(self.request.user.is_authenticated and self.request.user.is_staff)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        valid_orders = Order.objects.exclude(status='CANCELLED')

        # KPI Metrics
        monthly_rev = valid_orders.filter(
            created_at__gte=month_start
        ).aggregate(total=Sum('total_amount'))['total']
        context['monthly_revenue'] = monthly_rev or 0

        context['orders_today'] = Order.objects.filter(created_at__date=now.date()).count()
        context['orders_delivered'] = Order.objects.filter(status='DELIVERED').count()
        context['orders_pending'] = Order.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'PACKAGING', 'SHIPPED']
        ).count()
        context['orders_cancelled'] = Order.objects.filter(status='CANCELLED').count()

        # 12-Month Revenue & Order Volume Chart Data
        twelve_months_ago = month_start - timedelta(days=365)
        monthly_qs = (
            valid_orders.filter(created_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('total_amount'), count=Count('id'))
            .order_by('month')
        )
        context['monthly_labels'] = [m['month'].strftime('%b %Y') for m in monthly_qs]
        context['monthly_totals'] = [float(m['total'] or 0) for m in monthly_qs]
        context['monthly_counts'] = [int(m['count'] or 0) for m in monthly_qs]

        # Inventory Alerts: Products with stock_qty <= 5
        context['low_stock_products'] = Product.objects.filter(
            stock_qty__lte=5
        ).select_related('category').order_by('stock_qty')[:10]

        # Recent Orders Table
        context['recent_orders'] = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:15]
        context['title'] = 'Business Analytics & Store Dashboard'
        return context
