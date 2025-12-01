from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Debug toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
]

# Email backend for development - SMTP enabled (real emails with new app password)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Prints to terminal
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Sends real emails via Gmail

# Local domain for development
SITE_DOMAIN = 'localhost:8000'