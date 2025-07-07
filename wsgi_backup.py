"""
WSGI config for parking_system project - Production.
"""

import os
import sys

# Add the project directory to the Python path
# Substitua 'seu-username' pelo seu username do PythonAnywhere
USERNAME = 'sysparkingcbmepi'  # ALTERE AQUI!
path = f'/home/{USERNAME}/parking'
if path not in sys.path:
    sys.path.append(path)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings_prod')

application = get_wsgi_application() 