import os
from django.core.asgi import get_asgi_application

# Set the default Django settings module for the ASGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nit_home.settings')

# Expose the ASGI callable as a module-level variable named application
application = get_asgi_application()
