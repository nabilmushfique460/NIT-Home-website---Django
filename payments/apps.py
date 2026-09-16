import os
from django.apps import AppConfig

# Configuration for payments application
class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    path = os.path.dirname(os.path.abspath(__file__))
