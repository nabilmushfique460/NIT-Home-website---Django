from django.urls import path
from .views import SteadfastWebhookView

app_name = 'courier'

urlpatterns = [
    path('webhook/steadfast/<str:token>/', SteadfastWebhookView.as_view(), name='steadfast_webhook'),
]
