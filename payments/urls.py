from django.urls import path
from .views import (
    PaymentSelectView,
    ChoosePaymentView,
    BkashGatewaySimulateView,
    NagadGatewaySimulateView,
    SSLCommerzInitiateView,
    SSLCommerzIPNView,
    SSLCommerzSuccessView,
    SSLCommerzFailView,
    SSLCommerzCancelView,
)

app_name = 'payments'

urlpatterns = [
    path('select/<str:order_number>/', PaymentSelectView.as_view(), name='payment_select'),
    path('choose/<str:order_number>/', ChoosePaymentView.as_view(), name='choose_payment'),
    path('sslcommerz/initiate/<str:order_number>/', SSLCommerzInitiateView.as_view(), name='sslcommerz_initiate'),
    path('sslcommerz/ipn/', SSLCommerzIPNView.as_view(), name='sslcommerz_ipn'),
    path('sslcommerz/success/<str:order_number>/', SSLCommerzSuccessView.as_view(), name='sslcommerz_success'),
    path('sslcommerz/fail/<str:order_number>/', SSLCommerzFailView.as_view(), name='sslcommerz_fail'),
    path('sslcommerz/cancel/<str:order_number>/', SSLCommerzCancelView.as_view(), name='sslcommerz_cancel'),
    path('bkash/<str:order_number>/', BkashGatewaySimulateView.as_view(), name='bkash_gateway'),
    path('nagad/<str:order_number>/', NagadGatewaySimulateView.as_view(), name='nagad_gateway'),
]
