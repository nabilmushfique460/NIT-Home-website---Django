import os
from django.core.wsgi import get_wsgi_application

# Set the default Django settings module for the WSGI application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nit_home.settings')

# Expose the WSGI callable as a module-level variable named application
application = get_wsgi_application()
