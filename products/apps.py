import os
from django.apps import AppConfig

# Configuration for products application
class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    path = os.path.dirname(os.path.abspath(__file__))
