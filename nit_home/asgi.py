"""
ASGI config for N-IT Home project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nit_home.settings')

application = get_asgi_application()
