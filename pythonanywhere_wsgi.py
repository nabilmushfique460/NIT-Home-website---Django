# +-----------------------------------------------------------------------------+
# | PythonAnywhere WSGI Configuration for NIT Store                             |
# | Copy and paste this content into:                                           |
# | /var/www/nabil371_pythonanywhere_com_wsgi.py                                |
# +-----------------------------------------------------------------------------+

import os
import sys

# Project directory path on PythonAnywhere
path = '/home/Nabil371/NIT-Home-website---Django'
if path not in sys.path:
    sys.path.insert(0, path)

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'nit_home.settings'

# Import and expose WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
