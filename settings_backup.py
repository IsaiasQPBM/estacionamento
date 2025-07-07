"""
Django settings for parking_system project - Production.
"""

from .settings import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # Temporariamente TRUE para diagnóstico

# Substitua 'seu-username' pelo seu username do PythonAnywhere
USERNAME = 'sysparkingcbmepi'  # ALTERE AQUI!
ALLOWED_HOSTS = [f'{USERNAME}.pythonanywhere.com', f'www.{USERNAME}.pythonanywhere.com']

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Email settings (configure according to your needs)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For development on PythonAnywhere 