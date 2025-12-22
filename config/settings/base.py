import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file (only if exists - Railway uses direct env vars)
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
# Note: No warning for missing .env - Railway injects env vars directly

# Check if we're on Railway
RAILWAY_ENVIRONMENT = os.getenv('RAILWAY_ENVIRONMENT')

# Only show debug info in development
if not RAILWAY_ENVIRONMENT:
    print(f"🔍 DEBUG: Running in local development mode")
    print(f"🔍 DEBUG: SERVER_URL = {os.getenv('SERVER_URL', 'NOT SET')}")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-key-for-local-development-only')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

# Railway deployment compatibility - RAILWAY_ENVIRONMENT already set above
if RAILWAY_ENVIRONMENT:
    # Production settings for Railway
    DEBUG = False
    ALLOWED_HOSTS = ['*']  # Railway handles the domain routing
    # CSRF trusted origins for Railway deployment
    CSRF_TRUSTED_ORIGINS = [
        'https://*.railway.app',
        'https://*.up.railway.app',
    ]
    # Also support custom domain if configured
    server_url = os.getenv('SERVER_URL')
    if server_url:
        CSRF_TRUSTED_ORIGINS.append(server_url)
else:
    # Local development
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
    CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For number formatting (intcomma, etc.)
]

THIRD_PARTY_APPS = [
    'django_q',  # Django-Q2 for async tasks and scheduled jobs
]

LOCAL_APPS = [
    'apps.accounts.apps.AccountsConfig',
    'apps.audit.apps.AuditConfig',
    'apps.communications.apps.CommunicationsConfig',
    'apps.core.apps.CoreConfig',
    # 🏗️ FOUNDATION APPS (Rebuilt with ACID compliance)
    'apps.inventory.apps.InventoryConfig',  # ✅ REBUILT - Per-item table architecture
    'apps.products.apps.ProductsConfig',    # ✅ REBUILT - Product catalog & recipes
    'apps.production.apps.ProductionConfig', # ✅ REBUILT - Production batches & stock
    'apps.sales.apps.SalesConfig',          # ✅ REBUILT - Bank ledger dispatches & returns
    'apps.reports.apps.ReportsConfig',
    'apps.analytics.apps.AnalyticsConfig',
    'apps.payroll.apps.PayrollConfig',
    'apps.accounting.apps.AccountingConfig',  # ⚠️ NEEDS REFACTOR - Will use new inventory/production
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Add development apps only in local environment
if DEBUG and not RAILWAY_ENVIRONMENT:
    # Debug toolbar can be added later if needed
    # THIRD_PARTY_APPS.extend(['debug_toolbar'])
    # INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Must be after SecurityMiddleware - for serving static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for authentication
    'apps.accounts.middleware.ActivityTrackingMiddleware',
    'apps.accounts.middleware.RouteProtectionMiddleware',  # ✅ ENABLED - Protect all routes
    'apps.accounts.middleware.RoleBasedAccessMiddleware',  # ✅ ENABLED - BASIC_USER restrictions
    'apps.accounts.middleware.SessionSecurityMiddleware',  # ✅ ENABLED - 1hr timeout
    # 'apps.accounts.middleware.ReAuthenticationMiddleware',  # ❌ DISABLED - needs proper UI (redirects to password reset)
]

# Add debug toolbar middleware only in development
if DEBUG and not RAILWAY_ENVIRONMENT:
    # MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration with Railway compatibility
# Default to SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Railway automatically sets DATABASE_URL in production
if 'DATABASE_URL' in os.environ:
    # For production, install dj-database-url: pip install dj-database-url
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.parse(os.environ.get('DATABASE_URL'))
        DATABASES['default']['CONN_MAX_AGE'] = 600
        DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    except ImportError:
        pass  # Fall back to SQLite if dj-database-url not installed

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization - East Africa settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'  # East Africa timezone
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# WhiteNoise configuration for production
if RAILWAY_ENVIRONMENT:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Authentication Configuration
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Session Configuration (1 hour timeout for smart logout)
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Media files configuration (for profile photos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration - Gmail SMTP
# Use console backend for development (prints to terminal)
# Use SMTP backend for production (sends real emails)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'  # Default to console for safety
)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'joe@coophive.network')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'Chesanto Bakery <joe@coophive.network>'
SERVER_EMAIL = 'Chesanto Bakery <joe@coophive.network>'

# Stock Alert Email - where to send low stock notifications
STOCK_ALERT_EMAIL = os.getenv('STOCK_ALERT_EMAIL', 'joe@coophive.network')

# Server URL (for emails and redirects) - strip trailing slash to prevent double slashes
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8000').rstrip('/')

# Debug: Print SERVER_URL during startup (remove after debugging)
print(f"🔗 SERVER_URL configured as: {SERVER_URL}")

# Authentication & Security Settings
SUPERADMIN_EMAILS = os.getenv('SUPERADMIN_EMAILS', 'madame@chesanto.com,joe@coophive.network')
OTP_CODE_LENGTH = int(os.getenv('OTP_CODE_LENGTH', '6'))
OTP_CODE_VALIDITY = int(os.getenv('OTP_CODE_VALIDITY', '600'))  # 10 minutes
PASSWORD_RESET_CODE_VALIDITY = int(os.getenv('PASSWORD_RESET_CODE_VALIDITY', '900'))  # 15 minutes
RE_AUTH_INTERVAL = int(os.getenv('RE_AUTH_INTERVAL', '86400'))  # 24 hours

# Audit Settings
AUDIT_LOG_RETENTION_DAYS = int(os.getenv('AUDIT_LOG_RETENTION_DAYS', '365'))

# Rate Limiting Settings (for future implementation)
LOGIN_RATE_LIMIT = os.getenv('LOGIN_RATE_LIMIT', '10/m')
PASSWORD_RESET_RATE_LIMIT = os.getenv('PASSWORD_RESET_RATE_LIMIT', '3/h')

# Site Configuration
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'chesanto.com')
SITE_NAME = 'Chesanto Bakery Management System'

# Debug toolbar settings
INTERNAL_IPS = ['127.0.0.1']

# ═══════════════════════════════════════════════════════════════════════════════
# DJANGO-Q2 CONFIGURATION
# Async task queue and scheduled job management
# ═══════════════════════════════════════════════════════════════════════════════

Q_CLUSTER = {
    'name': 'chesanto_bakery',
    'workers': int(os.getenv('Q_WORKERS', '2')),
    'recycle': 500,  # Recycle workers after 500 tasks
    'timeout': 300,  # Task timeout in seconds (5 minutes)
    'retry': 360,  # Retry failed tasks after 6 minutes
    'compress': True,  # Compress task data
    'save_limit': 250,  # Keep last 250 tasks in database
    'queue_limit': 500,  # Max tasks in queue
    'cpu_affinity': 1,  # Workers per CPU
    'label': 'Chesanto Task Queue',
    'orm': 'default',  # Use Django ORM as broker (no Redis needed)
    'catch_up': False,  # Don't run missed scheduled tasks on startup
    'sync': os.getenv('Q_SYNC', 'False').lower() == 'true',  # Run tasks synchronously (for testing)
    'ack_failures': True,  # Acknowledge failed tasks
    'poll': 5,  # Check for new tasks every 5 seconds
}

# Report Scheduling Configuration
REPORT_EMAIL_RECIPIENTS = os.getenv(
    'REPORT_EMAIL_RECIPIENTS',
    'madame@chesanto.com,joe@coophive.network'
).split(',')

# Schedule times (in Africa/Nairobi timezone)
DAILY_REPORT_HOUR = int(os.getenv('DAILY_REPORT_HOUR', '7'))  # 7 AM
WEEKLY_REPORT_DAY = os.getenv('WEEKLY_REPORT_DAY', 'monday').lower()  # Monday
MONTHLY_REPORT_DAY = int(os.getenv('MONTHLY_REPORT_DAY', '1'))  # 1st of month