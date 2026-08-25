from django.urls import path
from .views import (
    PaymentSelectView,
    ChoosePaymentView,
    BkashGatewaySimulateView,
    NagadGatewaySimulateView
)

app_name = 'payments'

urlpatterns = [
    path('select/<str:order_number>/', PaymentSelectView.as_view(), name='payment_select'),
    path('choose/<str:order_number>/', ChoosePaymentView.as_view(), name='choose_payment'),
    path('bkash/<str:order_number>/', BkashGatewaySimulateView.as_view(), name='bkash_gateway'),
    path('nagad/<str:order_number>/', NagadGatewaySimulateView.as_view(), name='nagad_gateway'),
]
