# Project Structure
**Project:** Chesanto Bakery Management System  
**Last Updated:** October 16, 2025  
**Architecture:** Django 5.2.7, Multi-App Monolith

---

## PART 1: HIGH-LEVEL ARCHITECTURE

### System Overview
```
┌─────────────────────────────────────────────────────────┐
│                     USERS                                │
│  (Superadmin, Admin, Managers, Salesmen, Dispatch)     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │   NGINX / Railway   │  (Production)
         │   Django Dev Server │  (Local)
         └──────────┬──────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│            DJANGO APPLICATION (Port 8000)                 │
│                                                           │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │accounts │  │   audit   │  │   comms  │  │  core   │ │
│  │(auth)   │  │(logging)  │  │ (email)  │  │(shared) │ │
│  └─────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │          FUTURE APPS (Not Started)                │  │
│  │  production | sales | inventory | dispatch        │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────┬────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │   PostgreSQL         │  (Production)
         │   SQLite             │  (Local)
         └─────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │   Gmail SMTP         │
         │   (Email Delivery)   │
         └─────────────────────┘
```

---

## PART 2: DIRECTORY STRUCTURE

```
Chesanto-Bakery-Management-System/
│
├── manage.py                           # Django management commands
├── db.sqlite3                          # Local database
├── Procfile                            # Railway deployment config
├── railway.json                        # Railway settings
├── requirements.txt                    # Python dependencies
├── requirements_frozen.txt             # Locked versions
├── .env                                # Environment variables (not in git)
├── .gitignore                          # Git ignore rules
│
├── config/                             # Project settings
│   ├── __init__.py
│   ├── asgi.py                         # ASGI config (async)
│   ├── wsgi.py                         # WSGI config (production)
│   ├── urls.py                         # Root URL routing
│   └── settings/
│       ├── __init__.py                 # Auto-load based on env
│       ├── base.py                     # Shared settings
│       ├── local.py                    # Development settings
│       └── prod.py                     # Production settings
│
├── apps/                               # All Django apps
│   ├── __init__.py
│   │
│   ├── accounts/                       # 🟢 70% Complete
│   │   ├── __init__.py
│   │   ├── admin.py                    # User admin interface
│   │   ├── apps.py                     # App config
│   │   ├── forms.py                    # RegisterForm, InviteForm, UserProfileForm
│   │   ├── middleware.py               # Session timeout, re-auth
│   │   ├── models.py                   # User, EmailOTP, UserInvitation, UserProfileChange
│   │   ├── signals.py                  # Auto-create profile on user save
│   │   ├── urls.py                     # 11 auth routes
│   │   ├── utils.py                    # generate_otp, validate_otp, generate_temp_password
│   │   ├── views.py                    # 🔴 BROKEN - 8 auth views (710 lines)
│   │   ├── views.py.backup             # 🔴 SUSPECT - Old corrupted version
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── init_deployment.py  # Create superadmin, test email
│   │   │       └── test_env.py         # Verify environment variables
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_alter_userinvitation_expires_at.py
│   │   │   └── 0003_alter_userinvitation_temp_password.py
│   │   └── templates/accounts/
│   │       ├── base.html               # Master template
│   │       ├── login.html              # ✅ Working
│   │       ├── register.html           # ✅ Fixed (role removed)
│   │       ├── otp_verify.html         # ✅ Working
│   │       ├── password_reset_request.html  # 🔴 Backend broken
│   │       ├── password_reset_verify.html   # Not tested
│   │       ├── password_change.html    # Not tested
│   │       ├── invite_user.html        # 🔴 Backend broken
│   │       ├── profile.html            # ✅ Working
│   │       ├── profile_edit.html       # ✅ Working
│   │       └── profile_changes.html    # ✅ Working
│   │
│   ├── audit/                          # 🟡 50% Complete (Refactored Today)
│   │   ├── __init__.py
│   │   ├── admin.py                    # Audit log admin
│   │   ├── apps.py
│   │   ├── middleware.py               # Auto-log page views
│   │   ├── models.py                   # AuditLog (20+ action types)
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   └── services/
│   │       ├── __init__.py             # Export ActivityLogger, AuditTrail, AuditLogger (deprecated)
│   │       ├── activity_logger.py      # ✅ NEW - Fire-and-forget activity logging
│   │       ├── audit_trail.py          # ✅ NEW - Transactional audit records
│   │       ├── archiver.py             # Archive old activity logs
│   │       └── logger.py               # 🔴 DEPRECATED - Old AuditLogger (causes errors)
│   │
│   ├── communications/                 # ✅ 100% Complete
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                   # EmailLog, SMSLog (future)
│   │   ├── migrations/
│   │   │   └── 0001_initial.py
│   │   ├── services/
│   │   │   └── email.py                # EmailService (Gmail SMTP)
│   │   └── templates/communications/
│   │       ├── invitation.html         # User invitation email
│   │       ├── password_reset.html     # Password reset email
│   │       └── otp.html                # OTP code email
│   │
│   ├── core/                           # ✅ 100% Complete
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                   # BaseModel (created_at, updated_at)
│   │   ├── validators.py               # Phone, email, ID validators
│   │   └── migrations/
│   │       └── 0001_initial.py
│   │
│   ├── production/                     # ⚪ 0% Complete (Not Started)
│   │   └── (empty)
│   │
│   ├── sales/                          # ⚪ 0% Complete (Not Started)
│   │   └── (empty)
│   │
│   ├── inventory/                      # ⚪ 0% Complete (Not Started)
│   │   └── (empty)
│   │
│   └── dispatch/                       # ⚪ 0% Complete (Not Started)
│       └── (empty)
│
├── static/                             # Static assets (CSS, JS, images)
│   ├── css/
│   │   ├── base.css                    # Global styles (Apple-inspired)
│   │   ├── components.css              # Reusable components
│   │   └── main.css                    # App-specific styles
│   ├── js/
│   │   ├── base.js                     # Global JavaScript
│   │   └── main.js                     # App-specific JavaScript
│   └── images/
│       └── favicon.svg                 # Site icon
│
├── media/                              # User uploads (profile photos)
│   └── profile_photos/                 # (Created on first upload)
│
├── Docs/                               # Documentation (CONSOLIDATED)
│   ├── 1_ACCOUNTS_APP.md               # ✅ NEW - Accounts app complete docs
│   ├── 2_IMPLEMENTATION_STATUS.md      # ✅ NEW - Overall progress, blockers
│   ├── 3_PROJECT_STRUCTURE.md          # ✅ NEW - This file
│   ├── 4_TEMPLATES_DESIGN.md           # 🔄 TODO - Design system, components
│   │
│   ├── Github_docs/                    # 🔴 OLD - To be replaced by 4 master docs above
│   │   ├── AUTHENTICATION_SYSTEM.md    # → Merged into 1_ACCOUNTS_APP.md
│   │   ├── USER_PROFILES_AND_CHAT.md   # → Merged into 1_ACCOUNTS_APP.md
│   │   ├── AUDIT_ARCHITECTURE.md       # → Keep separate (architectural decision)
│   │   ├── IMPLEMENTATION_STATUS.md    # → Replaced by 2_IMPLEMENTATION_STATUS.md
│   │   ├── project_structure.md        # → Replaced by 3_PROJECT_STRUCTURE.md
│   │   ├── template_schema.md          # → Will merge into 4_TEMPLATES_DESIGN.md
│   │   └── (14 other files)            # → Archive or delete
│   │
│   └── Local_working_docs/             # Business requirements (keep)
│       ├── SPECS.MD
│       ├── system_design_specification.md
│       └── Chesantto Books_September 2025_.xlsx
│
├── venv/                               # Python virtual environment (not in git)
│
└── __pycache__/                        # 🔴 PROBLEM - Bytecode cache (causes errors)
    └── (delete frequently)
```

---

## PART 3: KEY FILES EXPLAINED

### manage.py
```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

# Usage:
# python manage.py runserver         # Start dev server
# python manage.py migrate            # Run database migrations
# python manage.py createsuperuser    # Create admin user
# python manage.py init_deployment    # Custom: Setup production
# python manage.py test_env           # Custom: Test environment vars
```

---

### config/settings/base.py
**Core Django settings (shared across all environments)**

```python
# Key Settings:
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Our apps
    'apps.core',
    'apps.accounts',
    'apps.audit',
    'apps.communications',
    # production, sales, inventory, dispatch (not added yet)
]

AUTH_USER_MODEL = 'accounts.User'  # Custom user model

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'apps.accounts.middleware.SessionTimeoutMiddleware',  # TODO: Enable
    # 'apps.accounts.middleware.ReAuthMiddleware',          # TODO: Enable
    # 'apps.audit.middleware.PageViewMiddleware',           # TODO: Enable
]

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],  # Each app has own templates/
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# Session Config
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_SECURE = True  # TODO: Enable in production (HTTPS)

# Timezone
TIME_ZONE = 'Africa/Nairobi'  # EAT (UTC+3)
USE_TZ = True

# Static Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media Files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

### config/settings/local.py
**Development-specific settings**

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email (Gmail SMTP for testing)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# Superadmin emails (auto-approval)
SUPERADMIN_EMAILS = os.getenv('SUPERADMIN_EMAILS', '').split(',')
```

---

### config/settings/prod.py
**Production settings (Railway.app)**

```python
from .base import *

DEBUG = False
ALLOWED_HOSTS = ['.railway.app', 'chesanto.com']  # TODO: Add custom domain

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT', 5432),
    }
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Static files (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

---

### config/urls.py
**Root URL routing**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.accounts.urls')),  # All auth routes
    # path('production/', include('apps.production.urls')),  # TODO: Add
    # path('sales/', include('apps.sales.urls')),            # TODO: Add
    # path('inventory/', include('apps.inventory.urls')),    # TODO: Add
    # path('dispatch/', include('apps.dispatch.urls')),      # TODO: Add
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

### .env (Example - Not in Git)
```bash
# Django
SECRET_KEY="your-secret-key-here"
DJANGO_SETTINGS_MODULE="config.settings.local"

# Database (Production)
PGDATABASE="chesanto_db"
PGUSER="postgres"
PGPASSWORD="your-db-password"
PGHOST="your-db-host.railway.app"
PGPORT="5432"

# Email (Gmail SMTP)
EMAIL_HOST_USER="your-email@gmail.com"
EMAIL_HOST_PASSWORD="your-app-password"  # Not regular password!

# Superadmin Auto-Approval
SUPERADMIN_EMAILS="madame@chesanto.com,joe@coophive.network"

# Railway
PORT="8000"
```

---

### requirements.txt
```
Django==5.2.7
Pillow==10.0.0                # Image processing (profile photos)
python-decouple==3.8          # .env file loading
psycopg2-binary==2.9.7        # PostgreSQL driver
gunicorn==21.2.0              # WSGI server (production)
whitenoise==6.5.0             # Static file serving
```

---

### Procfile (Railway.app Deployment)
```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

---

### railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## PART 4: DATA FLOW

### Authentication Flow
```
User Browser
    ↓
1. GET /auth/login/
    ↓
Django URL Router (config/urls.py)
    ↓
apps.accounts.urls (auth/)
    ↓
apps.accounts.views.login_view()
    ↓
Check @anonymous_required decorator
    ↓
Render templates/accounts/login.html
    ↓
User submits form (POST)
    ↓
Validate credentials (authenticate())
    ↓
Check last_password_login < 24hrs?
    ├─ YES → login(request, user) → Redirect to profile
    └─ NO → generate_otp() → Send email → Redirect to OTP verify
    ↓
ActivityLogger.log_login() (fire-and-forget)
    ↓
Save to audit.AuditLog table (async, non-blocking)
```

---

### Password Reset Flow (🔴 CURRENTLY BROKEN)
```
User Browser
    ↓
1. GET /auth/password/reset/
    ↓
Render password_reset_request.html
    ↓
User enters email (POST)
    ↓
apps.accounts.views.password_reset_request_view()
    ↓
User.objects.get(email=email)
    ↓
generate_otp(user, purpose='PASSWORD_RESET') → 6-digit code
    ↓
EmailService.send_password_reset(email, code, user)
    ↓
🔴 ActivityLogger.log_password_reset_requested()  ← ERROR HERE
    ↓ (Should be fire-and-forget, but throws NameError)
Store user_id in session
    ↓
Redirect to /auth/password/reset/verify/
    ↓
User enters code + new password (POST)
    ↓
validate_otp(user, code, purpose='PASSWORD_RESET')
    ↓
user.set_password(new_password)
    ↓
user.save()
    ↓
ActivityLogger.log_password_changed()
    ↓
Redirect to /auth/login/
```

---

### Invitation Flow (🔴 BACKEND BROKEN)
```
Admin Browser
    ↓
1. GET /auth/invite/ (requires @staff_required)
    ↓
Render invite_user.html (form with email, name, role)
    ↓
Admin submits form (POST)
    ↓
apps.accounts.views.invite_user_view()
    ↓
Check existing invitation:
🔴 UserInvitation.objects.filter(email=email, is_accepted=False, ...)
    ↓ (Field error: is_accepted doesn't exist, should be used_at__isnull=True)
generate_temp_password() → Random password (e.g., 'Kx9mP2vL')
    ↓
User.objects.create_user(email, temp_password, role=role, must_change_password=True)
    ↓
UserInvitation.objects.create(email, temp_password, invited_by=admin, expires_at=+7days)
    ↓
EmailService.send_invitation(email, name, role, temp_password, login_url, invited_by)
    ↓
ActivityLogger.log_user_invited(email, admin, request)
    ↓
Success message + redirect
```

---

## PART 5: DATABASE SCHEMA

### Entity Relationship Diagram
```
┌─────────────────────────────────────────┐
│ User (AbstractUser)                     │
│ ─────────────────────────────────────── │
│ PK: id (int)                            │
│ UK: email (varchar)                     │
│ UK: national_id (varchar)               │
│     username (nullable)                 │
│     first_name, middle_names, last_name │
│     mobile_primary/secondary/tertiary   │
│     employee_id, basic_salary, ...      │
│     role (TextChoices)                  │
│     is_approved, must_change_password   │
│     last_password_login                 │
│     profile_photo (ImageField)          │
└──────────────┬──────────────────────────┘
               │
               │ 1:N
               ├──────────────────────────────┐
               │                              │
               ▼                              ▼
┌──────────────────────────────┐  ┌────────────────────────────┐
│ EmailOTP                     │  │ UserInvitation             │
│ ──────────────────────────── │  │ ────────────────────────── │
│ PK: id                       │  │ PK: id                     │
│ FK: user_id                  │  │     email                  │
│     code (6 digits)          │  │     full_name              │
│     purpose (LOGIN/RESET)    │  │     role                   │
│     expires_at (10-15 min)   │  │     temp_password          │
│     is_used                  │  │ FK: invited_by (User)      │
│     attempt_count (max 3)    │  │     expires_at (+7 days)   │
│     created_at               │  │     used_at (nullable)     │
└──────────────────────────────┘  └────────────────────────────┘
               │
               │ 1:N
               ▼
┌──────────────────────────────┐
│ UserProfileChange            │
│ ──────────────────────────── │
│ PK: id                       │
│ FK: user_id                  │
│ FK: changed_by_id            │
│     field_name               │
│     old_value, new_value     │
│     timestamp                │
└──────────────────────────────┘

┌──────────────────────────────┐
│ AuditLog                     │
│ ──────────────────────────── │
│ PK: id                       │
│ FK: user_id (nullable)       │
│     action (20+ types)       │
│     description              │
│     url, ip_address          │
│     user_agent, session_id   │
│     model_name, object_id    │
│     changes (JSONField)      │
│     metadata (JSONField)     │
│     success, error_message   │
│     timestamp                │
└──────────────────────────────┘
```

### Table Sizes (Current - Local DB)
| Table | Rows | Size | Notes |
|-------|------|------|-------|
| accounts_user | 2 | ~5 KB | Superadmin + test user |
| accounts_emailotp | 5 | ~2 KB | Test OTP codes |
| accounts_userinvitation | 0 | 0 KB | No invitations yet |
| accounts_userprofilechange | 3 | ~1 KB | Profile edits |
| audit_auditlog | 20 | ~10 KB | Login/logout activity |
| communications_emaillog | 5 | ~5 KB | Sent emails |

**Total:** ~25 KB (tiny, will grow to GB in production)

---

## PART 6: DEPLOYMENT ARCHITECTURE

### Local Development
```
Developer Machine
    ↓
PyCharm / VS Code
    ↓
source venv/bin/activate
    ↓
python manage.py runserver
    ↓
Django Dev Server (http://127.0.0.1:8000/)
    ↓
SQLite Database (db.sqlite3)
    ↓
Gmail SMTP (for email testing)
```

---

### Production (Railway.app - Planned)
```
Internet
    ↓
Railway Load Balancer
    ↓
Gunicorn WSGI Server (Python)
    ↓
Django Application
    ├─ Static Files → WhiteNoise (served from memory)
    ├─ Media Files → Railway Volume (persistent storage)
    └─ Database → Railway PostgreSQL (managed)
    ↓
Gmail SMTP (for production emails)
```

---

## PART 7: NAMING CONVENTIONS

### Models
- **PascalCase** - `User`, `EmailOTP`, `UserInvitation`
- **Singular nouns** - `User` (not `Users`)

### Views
- **snake_case** - `login_view`, `password_reset_request_view`
- **Suffix `_view`** - Distinguishes from utility functions

### URLs
- **kebab-case** - `/auth/password/reset/`, `/profile/edit/`
- **No trailing slashes** in path() - Django adds them

### Templates
- **snake_case** - `login.html`, `password_reset_request.html`
- **Match view name** - `login_view` → `login.html`

### Static Files
- **kebab-case** - `base.css`, `main.js`
- **Prefix app name** if global - `accounts-login.css`

### Database Tables
- **app_model** - `accounts_user`, `audit_auditlog`
- **Auto-generated by Django** from model names

### Environment Variables
- **UPPERCASE_SNAKE** - `EMAIL_HOST_USER`, `SUPERADMIN_EMAILS`

---

## PART 8: FILE PERMISSIONS

### Production Security
```bash
# Django project files (read-only for web server)
chmod 644 manage.py
chmod 644 requirements.txt
chmod -R 644 apps/
chmod -R 755 apps/  # Directories executable

# .env file (sensitive, owner-only)
chmod 600 .env

# Media uploads (read-write for web server)
chmod -R 755 media/
chmod -R 775 media/profile_photos/

# Static files (read-only)
chmod -R 644 static/
chmod -R 755 static/  # Directories

# Database (owner-only)
chmod 600 db.sqlite3  # Local only (production uses PostgreSQL)
```

---

## PART 9: GIT STRUCTURE

### Branches (Planned)
- `main` - Production-ready code
- `development` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Emergency production fixes

### .gitignore
```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
venv/
.Python

# Django
db.sqlite3
/static/
/media/

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

## PART 10: TESTING STRUCTURE (Planned)

```
apps/accounts/
├── tests/
│   ├── __init__.py
│   ├── test_models.py           # User, EmailOTP, etc.
│   ├── test_views.py            # login_view, register_view, etc.
│   ├── test_forms.py            # RegisterForm, InviteForm, etc.
│   ├── test_utils.py            # generate_otp, validate_otp, etc.
│   ├── test_decorators.py       # @anonymous_required, @staff_required
│   └── test_middleware.py       # SessionTimeout, ReAuth
```

**Current Status:** ❌ No tests written (critical gap)

---

**End of Project Structure Documentation**  
**Token Count:** ~7,000 words ≈ 10,500 tokens  
**Next:** Create 4_TEMPLATES_DESIGN.md
