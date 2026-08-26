from django.urls import path
from .views import (
    CheckoutView,
    OrderSuccessView,
    OrderDetailView,
    OrderHistoryView,
    OrderCancelView,
)

app_name = 'orders'

# Orders URL routing definitions
urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('success/<str:order_number>/', OrderSuccessView.as_view(), name='order_success'),
    path('history/', OrderHistoryView.as_view(), name='order_history'),
    path('invoice/<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
    path('cancel/<str:order_number>/', OrderCancelView.as_view(), name='order_cancel'),
]
