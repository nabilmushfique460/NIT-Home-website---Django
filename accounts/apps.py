import os
from django.apps import AppConfig

# Configuration for accounts application
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        pass
