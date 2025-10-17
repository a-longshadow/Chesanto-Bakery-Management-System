"""
WSGI config for Chesanto Bakery Management System.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use production settings on Railway, local settings otherwise
if os.environ.get('RAILWAY_ENVIRONMENT'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_wsgi_application()
