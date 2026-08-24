from django.urls import path
from .views import (
    CartDetailView, CartAddView, CartUpdateView, 
    CartRemoveView, CartClearView, BuyNowView
)

app_name = 'cart'

urlpatterns = [
    path('', CartDetailView.as_view(), name='cart_detail'),
    path('add/<int:product_id>/', CartAddView.as_view(), name='cart_add'),
    path('update/<int:product_id>/', CartUpdateView.as_view(), name='cart_update'),
    path('remove/<int:product_id>/', CartRemoveView.as_view(), name='cart_remove'),
    path('clear/', CartClearView.as_view(), name='cart_clear'),
    path('buy-now/<int:product_id>/', BuyNowView.as_view(), name='buy_now'),
]
