import os
from django.apps import AppConfig

# Configuration for cart application
class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cart'
    path = os.path.dirname(os.path.abspath(__file__))
