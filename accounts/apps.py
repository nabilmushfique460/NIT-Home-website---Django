from django.apps import AppConfig

# Configuration for accounts application
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        pass
