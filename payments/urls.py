from django.urls import path
from .views import (
    BkashGatewaySimulateView,
    NagadGatewaySimulateView,
    BkashCallbackView,
    NagadCallbackView
)

app_name = 'payments'

urlpatterns = [
    path('bkash/<str:order_number>/', BkashGatewaySimulateView.as_view(), name='bkash_gateway'),
    path('nagad/<str:order_number>/', NagadGatewaySimulateView.as_view(), name='nagad_gateway'),
    path('bkash/callback/<str:transaction_id>/', BkashCallbackView.as_view(), name='bkash_callback'),
    path('nagad/callback/<str:transaction_id>/', NagadCallbackView.as_view(), name='nagad_callback'),
]

