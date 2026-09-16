import os
from django.apps import AppConfig


class CourierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courier'
    path = os.path.dirname(os.path.abspath(__file__))
