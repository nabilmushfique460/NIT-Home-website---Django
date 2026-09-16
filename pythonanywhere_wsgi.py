# +-----------------------------------------------------------------------------+
# | PythonAnywhere WSGI Configuration for NIT Store                             |
# | Copy and paste this content into your PythonAnywhere WSGI file:             |
# | e.g. /var/www/nit_pythonanywhere_com_wsgi.py or                             |
# |      /var/www/nabil371_pythonanywhere_com_wsgi.py                          |
# +-----------------------------------------------------------------------------+

import os
import sys

# Auto-detect project directory path for 'nithome', 'nit', or 'Nabil371'
possible_paths = [
    '/home/nithome/NIT-Home-website---Django',
    '/home/nit/NIT-Home-website---Django',
    '/home/Nabil371/NIT-Home-website---Django',
]

for p in possible_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)
        break
else:
    # Fallback if custom home path
    username = os.environ.get('USER', 'Nabil371')
    custom_path = f'/home/{username}/NIT-Home-website---Django'
    if custom_path not in sys.path:
        sys.path.insert(0, custom_path)

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'nit_home.settings'

# Import and expose WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
