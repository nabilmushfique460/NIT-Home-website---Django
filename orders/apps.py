import os
from django.apps import AppConfig

# Configuration for orders application
class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    path = os.path.dirname(os.path.abspath(__file__))
