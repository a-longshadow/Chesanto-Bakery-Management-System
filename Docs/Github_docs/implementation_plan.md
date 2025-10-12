# Chesanto App Implementation Plan

## 1. Development Environment & Strategy

### Environment Configuration & Deployment

1. **Project Dependencies**
   ```text
   # requirements.txt
   django>=4.2.0
   gunicorn  # Production server
   whitenoise  # Static file serving
   psycopg[binary,pool]  # PostgreSQL adapter
   ```

2. **Environment Settings**
   ```python
   # config/settings/base.py
   import os
   from pathlib import Path

   # Build paths
   BASE_DIR = Path(__file__).resolve().parent.parent.parent

   # SECURITY WARNING: keep the secret key used in production secret!
   SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-key-for-local')

   # SECURITY WARNING: don't run with debug turned on in production!
   DEBUG = os.getenv('DJANGO_ENV') != 'production'

   # Allow all hosts in development, configure properly in production
   ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

   # Database configuration based on environment
   if os.getenv('DJANGO_ENV') == 'production':
       DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.postgresql',
               'NAME': os.getenv('PGDATABASE'),
               'USER': os.getenv('PGUSER'),
               'PASSWORD': os.getenv('PGPASSWORD'),
               'HOST': os.getenv('PGHOST'),
               'PORT': os.getenv('PGPORT'),
           }
       }
   else:
       DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.sqlite3',
               'NAME': BASE_DIR / 'db.sqlite3',
           }
       }

   # Static files configuration
   STATIC_URL = 'static/'
   STATIC_ROOT = BASE_DIR / 'staticfiles'
   STATICFILES_DIRS = [BASE_DIR / 'static']
   
   # Whitenoise for static files in production
   if os.getenv('DJANGO_ENV') == 'production':
       MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
       STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'whitenoise.middleware.WhiteNoiseMiddleware',
       # ... other middleware
   ]
   ```

2. **Railway Deployment Configuration**

   a. **Nixpacks Auto-Detection**
   - Railway uses Nixpacks to automatically detect and build Django projects
   - Create `requirements.txt` in project root:
     ```
     django>=4.2.0
     gunicorn
     whitenoise
     psycopg[binary,pool]
     ```
   - Create `Procfile` in project root (optional, Nixpacks will create one if not present):
     ```
     web: gunicorn config.wsgi:application
     ```

   b. **Railway Project Setup**
   - Push code to GitHub repository
   - In Railway dashboard:
     - Create new project
     - Select "Deploy from GitHub repo"
     - Add PostgreSQL service
     - Add environment variables:
       ```
       DJANGO_ENV=production
       DJANGO_SECRET_KEY=your-secure-key
       PYTHON_VERSION=3.11
       PGDATABASE=${{Postgres.PGDATABASE}}
       PGUSER=${{Postgres.PGUSER}}
       PGPASSWORD=${{Postgres.PGPASSWORD}}
       PGHOST=${{Postgres.PGHOST}}
       PGPORT=${{Postgres.PGPORT}}
       ```

   c. **Automatic Deployment Process**
   Railway's Nixpacks will automatically:
   - Detect Python/Django project
   - Install system dependencies
   - Install Python requirements
   - Set up virtual environment
   - Run Django migrations
   - Collect static files
   - Start Gunicorn server

   d. **Build and Start Commands** (automatically handled by Nixpacks)
   ```
   # Build command (automatic)
   python manage.py collectstatic --noinput

   # Start command (automatic)
   gunicorn config.wsgi:application --workers 2 --threads 2 --timeout 60
   ```

   e. **Security Headers** (add to settings/prod.py)
   ```python
   # Security settings
   SECURE_SSL_REDIRECT = True
   SECURE_HSTS_SECONDS = 31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   ```

3. **Project Backup Command**
   ```python
   # apps/core/management/commands/backup_project.py
   from django.core.management.base import BaseCommand
   import shutil, os
   from datetime import datetime
   
   class Command(BaseCommand):
       help = 'Creates a complete backup of project including database'
       
       def handle(self, *args, **options):
           timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
           backup_name = f"chesanto_backup_{timestamp}"
           backup_dir = os.path.expanduser("~/ChesantoBackups")
           
           if not os.path.exists(backup_dir):
               os.makedirs(backup_dir)
           
           # Keep only 10 recent backups
           backups = sorted([d for d in os.listdir(backup_dir) if d.startswith('chesanto_backup_')])
           while len(backups) > 9:  # Remove oldest if more than 9 exist
               shutil.rmtree(os.path.join(backup_dir, backups[0]))
               backups.pop(0)
           
           # Create new backup
           project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
           backup_path = os.path.join(backup_dir, backup_name)
           
           # Copy project files
           shutil.copytree(project_dir, backup_path)
           
           # Backup database
           self.stdout.write('Creating database backup...')
           os.system(f'python manage.py dumpdata --indent 2 > "{backup_path}/db.json"')
           
           self.stdout.write(self.style.SUCCESS(f'Backup created at {backup_path}'))

3. **Development Environment**

### Action Logging
- **Model Changes**
  ```python
  # Using django-simple-history
  class Transaction(models.Model):
      amount = models.DecimalField()
      description = models.CharField()
      history = HistoricalRecords()  # Tracks all changes
  ```

- **User Actions**
  ```python
  # Using django-auditlog
  from auditlog.registry import auditlog
  
  @auditlog.register()
  class FinancialEntry(models.Model):
      # Fields automatically tracked with who/what/when
  ```

- **System Events**
  ```python
  # Custom logging
  class SystemLog(models.Model):
      timestamp = models.DateTimeField(auto_now_add=True)
      event_type = models.CharField()
      description = models.TextField()
      metadata = models.JSONField()
  ```

### Reporting System

1. **Automated Reports**
   ```python
   # Using django-q for scheduling
   async_task(
       'reports.tasks.generate_daily_statement',
       schedule_type='D',  # Daily
       repeats=-1  # Forever
   )
   ```

2. **On-Demand Reports**
   ```python
   # PDF Generation
   class FinancialReportView(View):
       def get(self, request, *args, **kwargs):
           template = get_template('reports/financial_statement.html')
           html = template.render(context)
           return generate_pdf(html)
   ```

3. **Email Integration**
   ```python
   # Using django-templated-email
   send_templated_mail(
       template_name='daily_report',
       from_email='reports@chesanto.com',
       recipient_list=['management@chesanto.com'],
       context={'report_data': data}
   )
   ```

### 5. Testing Strategy

### Unit Testing
- One test file per module
- 90% code coverage minimum
- Mock external services
- Test all model methodsate Python virtual environment
2. Install development dependencies
3. Configure pre-commit hooks
4. Set up pytest with coverage

### Railway.app Setup
1. Configure Railway project
2. Set up PostgreSQL database
3. Configure environment variables
4. Set up GitHub integration

## 2. Project Implementation Phases

### Phase 1: Foundation (2 weeks)
1. **Project Structure**
   - Set up project with domain-driven design
   - Configure settings for all environments
   - Set up testing framework
   - Implement base templates and styling

2. **Audit System**
   - Model history tracking
   - User action logging
   - System event recording
   - Audit trail views

3. **Reporting Framework**
   - PDF report generation
   - Excel export capability
   - Automated report scheduling
   - Email delivery system

4. **Notification System**
   - Email integration
   - In-app notifications
   - SMS gateway setup
   - Template management

2. **Core Features**
   - Custom user model
   - Authentication system
   - Permission framework
   - Base model mixins

3. **Testing Foundation**
   - Unit test setup
   - Integration test framework
   - Factory Boy fixtures
   - CI pipeline setup

### Phase 2: Domain Apps (4 weeks)
1. **Production Module**
   - Product models and migrations
   - Production tracking
   - Quality control
   - Unit tests

2. **Sales Module**
   - Order processing
   - Territory management
   - Commission calculation
   - Integration tests

3. **Inventory Module**
   - Stock management
   - Movement tracking
   - Automated alerts
   - End-to-end tests

4. **Finance Module**
   - Banking integration
   - Expense tracking
   - Report generation
   - System tests

### Phase 3: API & Integration (2 weeks)
1. **API Development**
   - REST framework setup
   - Endpoint implementation
   - API documentation
   - Authentication/Authorization

2. **Railway Deployment**
   - Production configuration
   - Database migration strategy
   - Static file serving
   - SSL setup

## 3. Testing Strategy

### Unit Testing
- One test file per module
- 90% code coverage minimum
- Mock external services
- Test all model methods

### Integration Testing
- End-to-end workflows
- API endpoint testing
- Database interactions
- Cross-module functionality

### Performance Testing
- Load testing
- Database query optimization
- Caching implementation
- Response time benchmarks

## 4. Deployment Pipeline

### GitHub Actions Workflow
1. Run tests on pull requests
2. Check code quality
3. Build Docker image
4. Deploy to Railway

### Railway Deployment Process
1. **GitHub Integration**
   - Push code to GitHub
   - Railway automatically detects changes
   - Builds and deploys automatically

2. **Environment Variables on Railway**
   ```
   DJANGO_SECRET_KEY=your_production_secret_key
   DJANGO_SETTINGS_MODULE=config.settings.prod
   DATABASE_URL=postgres://...  # Auto-provided by Railway
   RAILWAY_ENVIRONMENT=production
   ALLOWED_HOSTS=.railway.app
   ```

3. **Database Management**
   - PostgreSQL auto-provisioned by Railway
   - Automatic database URL configuration
   - Migrations run on deploy

4. **Static Files**
   - Collected during deployment
   - Served via whitenoise

## 5. Quality Assurance

### Code Quality
- Black for formatting
- Flake8 for linting
- isort for imports
- MyPy for type checking

### Documentation
- API documentation (drf-yasg)
- Code documentation
- Deployment guides
- User manuals

## 6. Monitoring & Maintenance

### Production Monitoring
- Error tracking
- Performance monitoring
- Database monitoring
- Security updates

### Backup Strategy
- Automated database backups
- File storage backups
- Disaster recovery plan
- Backup testing schedule