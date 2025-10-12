# Django Project Structure

## Project Organization
```
chesanto/
├── manage.py
├── requirements/
│   ├── base.txt          # Shared requirements
│   ├── local.txt         # Development requirements
│   ├── production.txt    # Production requirements
│   └── test.txt         # Testing requirements
│
├── config/              # Project configuration
│   ├── settings/
│   │   ├── base.py      # Base settings
│   │   ├── local.py     # Development settings
│   │   ├── test.py      # Test settings
│   │   └── prod.py      # Production settings
│   ├── urls.py
│   └── wsgi.py
│
├── apps/               # Domain-specific applications
│   ├── core/          # Core functionality
│   │   ├── models/
│   │   │   ├── user.py        # Custom user model
│   │   │   └── base.py        # Base models
│   │   ├── templates/
│   │   │   └── core/
│   │   ├── tests/
│   │   │   ├── factories.py
│   │   │   └── test_*.py
│   │   └── utils/
│   │
│   ├── production/     # Production management
│   │   ├── models/
│   │   ├── services/
│   │   ├── templates/
│   │   └── tests/
│   │
│   ├── sales/         # Sales and orders
│   │   ├── models/
│   │   ├── services/
│   │   ├── templates/
│   │   └── tests/
│   │
│   ├── inventory/     # Inventory tracking
│   │   ├── models/
│   │   ├── services/
│   │   ├── templates/
│   │   └── tests/
│   │
│   ├── finance/      # Financial operations
│   │   ├── models/
│   │   ├── services/
│   │   ├── templates/
│   │   └── tests/
│   │
│   ├── audit/       # System auditing
│   │   ├── models/
│   │   ├── services/
│   │   └── tests/
│   │
│   └── api/         # API endpoints
│       ├── v1/
│       └── tests/
│
├── templates/        # Global templates
│   ├── base.html    # Base template
│   ├── nav.html     # Navigation
│   └── components/  # Reusable components
│
├── static/          # Static files
│   ├── css/
│   ├── js/
│   └── images/
│
├── tests/           # Integration tests
│   ├── conftest.py
│   └── integration/
│
├── scripts/         # Utility scripts
│   ├── backup.py    # Backup system
│   └── setup.py     # Environment setup
│
└── docs/           # Documentation
    ├── api/        # API documentation
    └── user/       # User manuals

## Domain-Specific Components

### 1. Core App Structure
```python
# core/models/base.py
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# core/models/user.py
class User(AbstractUser, TimestampedModel):
    employee_id = models.CharField(unique=True)
    role = models.CharField(choices=ROLE_CHOICES)
```

### 2. Testing Structure
```python
# tests/conftest.py
@pytest.fixture
def test_user():
    return UserFactory()

@pytest.fixture
def test_product():
    return ProductFactory()

# apps/sales/tests/test_orders.py
class TestOrderCreation:
    def test_order_process(self, test_user, test_product):
        order = create_order(test_user, test_product)
        assert order.status == 'created'
```

### 3. Template Hierarchy
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    {% include 'components/meta.html' %}
    {% include 'components/styles.html' %}
</head>
<body>
    {% include 'nav.html' %}
    {% block content %}{% endblock %}
    {% include 'components/scripts.html' %}
</body>
</html>
```

### 4. Backup System Integration
```python
# scripts/backup.py
class ProjectBackup:
    def __init__(self):
        self.source = settings.BASE_DIR
        self.backup_dir = settings.BACKUP_DIR
        
    def create_backup(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.backup_dir}/backup_{timestamp}"
        
        # Copy files
        shutil.copytree(self.source, backup_path)
        
        # Export database
        self.export_database(backup_path)
        
        # Verify backup
        self.verify_backup(backup_path)
        
        # Cleanup old backups
        self.cleanup_old_backups()
```

## Railway.app Integration

### 1. Database Configuration
```python
# config/settings/base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    } if not os.getenv('RAILWAY_ENVIRONMENT') else {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT'),
    }
}
```

### 2. Deployment Configuration
```python
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "python manage.py collectstatic --noinput"

[deploy]
startCommand = "gunicorn config.wsgi:application"
healthcheckPath = "/health/"
restartPolicyType = "on_failure"
```o Project Structure

## Project Organization
```
chesanto/
├── apps/                      # Domain-specific applications
│   ├── core/                 # Core functionality
│   │   ├── models/
│   │   │   ├── user.py      # Custom user model
│   │   │   └── common.py    # Base models
│   │   ├── tests/
│   │   │   ├── factories.py # Test data factories
│   │   │   ├── test_models.py
│   │   │   └── test_views.py
│   │   └── utils/           # Shared utilities
│   │
│   ├── audit/              # Audit and logging
│   │   ├── models/
│   │   │   ├── audit_log.py    # Audit trail model
│   │   │   ├── system_log.py   # System events
│   │   │   └── user_action.py  # User actions
│   │   ├── services/
│   │   │   ├── audit_service.py  # Audit logging
│   │   │   └── report_service.py # Audit reporting
│   │   └── views/
│   │       └── audit_views.py    # Audit trail views
│   │
│   ├── reports/            # Reporting system
│   │   ├── templates/
│   │   │   ├── pdf/       # PDF report templates
│   │   │   └── excel/     # Excel report templates
│   │   ├── services/
│   │   │   ├── generators/  # Report generators
│   │   │   └── schedulers/  # Report scheduling
│   │   └── views/
│   │       └── report_views.py
│   │
│   ├── notifications/     # Notification system
│   │   ├── templates/
│   │   │   ├── email/    # Email templates
│   │   │   └── sms/      # SMS templates
│   │   ├── services/
│   │   │   ├── email_service.py
│   │   │   └── sms_service.py
│   │   └── views/
│   │
│   ├── production/          # Production management
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/       # Business logic
│   │   └── views/
│   │
│   ├── sales/             # Sales operations
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   ├── inventory/        # Inventory management
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   ├── finance/         # Financial operations
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   └── api/            # API endpoints
│       ├── v1/
│       ├── tests/
│       └── docs/       # API documentation
│
├── config/            # Project configuration
│   ├── settings/
│   │   ├── base.py     # Base settings
│   │   ├── local.py    # Development settings
│   │   ├── test.py     # Test settings
│   │   └── prod.py     # Production settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/         # HTML templates
│   ├── base/
│   │   ├── base.html          # Main template
│   │   ├── nav.html           # Navigation
│   │   └── footer.html        # Footer
│   ├── components/            # Reusable components
│   │   ├── forms/
│   │   └── widgets/
│   └── pages/                 # Page templates
│
├── static/           # Static files
│   ├── css/
│   │   ├── base.css    # Base styles
│   │   └── theme.css   # Theme variables
│   ├── js/
│   └── images/
│
├── tests/            # Integration tests
│   ├── conftest.py   # Test configuration
│   ├── factories.py  # Test data factories
│   └── integration/  # Integration test suites
│
├── scripts/          # Utility scripts
│   ├── setup_dev.sh  # Dev environment setup
│   └── setup_test.sh # Test environment setup
│
└── requirements/     # Dependencies
    ├── base.txt     # Shared requirements
    ├── local.txt    # Development
    ├── test.txt     # Testing
    └── prod.txt     # Production
```

## Key Design Decisions

### 1. Environment Configuration
```python
# config/settings/base.py
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_TESTING = 'test' in sys.argv

# Railway.app specific
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
DATABASE_URL = os.getenv('DATABASE_URL')
```

### 2. Database Configuration
```python
# config/settings/base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    } if not IS_RAILWAY else {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT'),
    }
}
```

### 3. Railway Deployment Setup
```yaml
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "python manage.py collectstatic --noinput"

[deploy]
startCommand = "gunicorn config.wsgi:application"
healthcheckPath = "/health/"
restartPolicyType = "on_failure"

[env]
DJANGO_ENV = "production"
PYTHON_VERSION = "3.11"
```

### 4. Testing Strategy

1. **Unit Tests**
   - One test file per module
   - pytest as test runner
   - Factory Boy for test data
   - Mock external services

2. **Integration Tests**
   - End-to-end workflows
   - API endpoint testing
   - Database interactions
   - External service integration

3. **Test Configuration**
   ```python
   # config/settings/test.py
   from .base import *

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': ':memory:'
       }
   }
   ```

### 5. Template Structure

1. **Base Templates**
   ```html
   <!-- templates/base/base.html -->
   <!DOCTYPE html>
   <html lang="en">
   <head>
       {% include 'base/meta.html' %}
       {% include 'base/styles.html' %}
   </head>
   <body>
       {% include 'base/nav.html' %}
       {% block content %}{% endblock %}
       {% include 'base/footer.html' %}
       {% include 'base/scripts.html' %}
   </body>
   </html>
   ```

2. **Theme Configuration**
   ```css
   /* static/css/theme.css */
   :root {
       --primary-color: #007bff;
       --secondary-color: #6c757d;
       --font-family: 'Roboto', sans-serif;
       --spacing-unit: 1rem;
   }
   ```

### 6. Development Workflow

1. **Local Development**
   ```bash
   python manage.py runserver --settings=config.settings.local
   ```

2. **Testing**
   ```bash
   pytest --ds=config.settings.test
   ```

3. **Railway Deployment**
   - GitHub Actions for CI/CD
   - Automatic deployments on main branch
   - Environment variable management
   - Database migrations