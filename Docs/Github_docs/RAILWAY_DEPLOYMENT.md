# Railway Deployment Guide
**Project:** Chesanto Bakery Management System  
**Date:** December 17, 2025  
**Platform:** Railway.app (Pro Plan)  
**Deployment:** Dockerfile with Supervisor

---

## Prerequisites

✅ GitHub repository: `https://github.com/a-longshadow/Chesanto-Bakery-Management-System`  
✅ Railway account connected to GitHub  
✅ PostgreSQL database service created in Railway

---

## Deployment Steps

### 1. Create Railway Project
1. Login to Railway: https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose: `a-longshadow/Chesanto-Bakery-Management-System`
5. Railway will auto-detect Django and use Nixpacks

### 2. Add PostgreSQL Database
1. In your project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a `DATABASE_URL` variable
4. Link the database to your Django service

### 3. Configure Environment Variables
Go to your Django service → Variables tab and add these:

#### Core Django Settings (REQUIRED)
```env
DJANGO_SECRET_KEY=_&96_2g&qtkohtxd()sfv!gl6gigm)q-4o3qwd-%mb5wr%05r+
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.prod
```

#### Initial Superuser (REQUIRED - First deployment only)
```env
INITIAL_SUPERUSER_EMAIL=joe@coophive.network
INITIAL_SUPERUSER_PASSWORD=YourSecurePassword123!
INITIAL_SUPERUSER_FIRST_NAME=Joe
INITIAL_SUPERUSER_LAST_NAME=Maina
INITIAL_SUPERUSER_MOBILE=+254712345678
```

#### Authentication & Security
```env
SUPERADMIN_EMAILS=joe@coophive.network
SERVER_URL=https://your-app-name.up.railway.app
```

#### Email Configuration (Gmail SMTP)
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=joe@coophive.network
EMAIL_HOST_PASSWORD=opno whxi ztta soyt
DEFAULT_FROM_EMAIL=Chesanto Bakery <joe@coophive.network>
```

#### Session & OTP Configuration (Optional - has defaults)
```env
SESSION_COOKIE_AGE=3600
OTP_CODE_LENGTH=6
OTP_CODE_VALIDITY=600
PASSWORD_RESET_CODE_VALIDITY=900
```

#### Audit Configuration (Optional)
```env
AUDIT_LOG_RETENTION_DAYS=365
```

---

## Automatic Deployment Process

When you push to GitHub, Railway will automatically:

### 1. Build Phase
```bash
# Install Python packages
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput
```

### 2. Start Phase (Runs on every deployment)
```bash
# Run database migrations
python manage.py migrate --noinput

# Initialize deployment (creates superuser on first run)
python manage.py init_deployment

# Setup report schedules
python manage.py setup_report_schedules

# Start Gunicorn server
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

**Note:** The `init_deployment` command is **idempotent** - it's safe to run multiple times. It will:
- ✅ Create superuser on first deployment
- ✅ Skip if user already exists (unless --force flag)
- ✅ Verify email is in SUPERADMIN_EMAILS list

---

## Scheduled Report Emails (Automatic)

The system sends automated report emails on a schedule using Django-Q2.

### How It Works

Django-Q2 runs **automatically** via Supervisor when the container starts. Both Gunicorn (web server) and qcluster (background worker) run in the same container, managed by Supervisor.

**Architecture:**
```
Container Start
    └── supervisord
        ├── gunicorn (web server on $PORT)
        └── qcluster (background worker)
```

The qcluster process:
- Monitors the PostgreSQL-backed task queue
- Executes scheduled tasks at their configured times
- Retries failed tasks automatically
- Logs all task history to the database

### Schedule Summary

| Schedule | When (EAT) | Reports |
|----------|------------|---------|
| **Morning** | Daily 6:00 AM | Daily P&L, Sales, Production, Stock Levels, Low Stock Alerts, Crates |
| **Evening** | Daily 10:00 PM | Salesperson Performance, Stock Movement, Efficiency, Valuation |
| **Weekly** | Monday 7:00 AM | Weekly P&L, Sales, Production, Stock Movement |
| **Monthly** | 1st of month 7:00 AM | Monthly P&L, Sales, Production, Commission, Payroll, Valuation |
| **Annual** | Jan 1st 8:00 AM | Annual P&L, Annual Payroll |

### Managing Schedules via Admin

**Django-Q Schedule Admin:** `/admin/django_q/schedule/`
- ✅ View all scheduled tasks
- ✅ Pause/resume individual schedules
- ✅ Adjust timing (cron expressions)
- ✅ View task history and failures

**Report Management Admin:** `/admin/reports/`
- **ReportSchedule** - Enable/disable schedules, adjust timing
- **ReportRecipient** - Manage who receives which reports
- **ReportType** - Configure available report types
- **ScheduledReportLog** - View send history and retry failed sends

### Admin Actions Available

| Admin Section | Available Actions |
|--------------|-------------------|
| Report Schedules | Send Reports Now, Activate, Deactivate |
| Report Recipients | Send Test Email, Activate, Deactivate, Subscribe/Unsubscribe All |
| Report Types | Activate, Deactivate |
| Scheduled Report Logs | Retry Failed Reports, Clear Old Logs |

### Disable Background Scheduler

If needed, you can modify `supervisord.conf` to disable qcluster:
```ini
[program:qcluster]
autostart=false
```

### Test Locally
```bash
# Dry run (see what would be sent)
python manage.py send_scheduled_report MORNING --dry-run

# Actually send
python manage.py send_scheduled_report MORNING
```

---

## Post-Deployment Steps

### 1. Verify Deployment
Check Railway logs for:
```
✅ Superuser created successfully!
📊 User Details:
   Email: joe@coophive.network
   Name: Joe Maina
   Role: SUPERADMIN
```

Also look for:
```
🚀 Starting Django-Q cluster in background thread...
✅ Django-Q cluster thread started
```

### 2. Access Your App
- **Frontend:** `https://your-app-name.up.railway.app/`
- **Admin Panel:** `https://your-app-name.up.railway.app/admin/`
- **Login:** `https://your-app-name.up.railway.app/auth/login/`

### 3. First Login Security
1. Login with `INITIAL_SUPERUSER_EMAIL` and `INITIAL_SUPERUSER_PASSWORD`
2. **IMMEDIATELY change your password** at `/auth/password/change/`
3. Remove or update `INITIAL_SUPERUSER_PASSWORD` in Railway variables

### 4. Set Primary SUPERADMIN
Run this command locally (connected to production DB) or via Railway CLI:
```bash
python manage.py set_primary_superadmin joe@coophive.network
```

---

## Environment Variable Reference

### Critical Variables (Must Set)

| Variable | Example | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | `_&96_2g&qt...` | **NEW SECRET KEY** (see above) |
| `DJANGO_DEBUG` | `False` | **MUST be False in production** |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Uses production settings |
| `DATABASE_URL` | `postgres://...` | Auto-set by Railway Postgres |
| `INITIAL_SUPERUSER_EMAIL` | `joe@coophive.network` | First admin email |
| `INITIAL_SUPERUSER_PASSWORD` | `Secure123!` | **Change after first login** |
| `SUPERADMIN_EMAILS` | `joe@coophive.network` | Comma-separated list |

### Email Variables (Required for notifications)

| Variable | Value |
|----------|-------|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `465` |
| `EMAIL_USE_SSL` | `True` |
| `EMAIL_HOST_USER` | Your Gmail address |
| `EMAIL_HOST_PASSWORD` | Gmail app password |
| `DEFAULT_FROM_EMAIL` | `Chesanto Bakery <email@domain.com>` |

### Optional Variables (Have defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_COOKIE_AGE` | `3600` | 1 hour session timeout |
| `OTP_CODE_LENGTH` | `6` | OTP digit length |
| `OTP_CODE_VALIDITY` | `600` | 10 minutes |
| `AUDIT_LOG_RETENTION_DAYS` | `365` | 1 year |

---

## Railway-Specific Files

### `Dockerfile` (Build Configuration)
Custom Dockerfile for Railway deployment with WeasyPrint PDF support and Supervisor process management:

```dockerfile
FROM python:3.12-slim-bookworm

# Install system dependencies for WeasyPrint and Supervisor
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN python manage.py collectstatic --noinput

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
CMD ["/entrypoint.sh"]
```

### `supervisord.conf` (Process Manager)
Runs both Gunicorn (web server) and Django-Q2 (background worker) in a single container:

```ini
[supervisord]
nodaemon=true
logfile=/dev/null
pidfile=/tmp/supervisord.pid

[program:gunicorn]
command=gunicorn config.wsgi:application --bind 0.0.0.0:%(ENV_PORT)s --workers 2
autostart=true
autorestart=true
stdout_logfile=/dev/fd/1
stderr_logfile=/dev/fd/2

[program:qcluster]
command=python manage.py qcluster
autostart=true
autorestart=true
stdout_logfile=/dev/fd/1
stderr_logfile=/dev/fd/2
```

### `entrypoint.sh` (Startup Script)
```bash
#!/bin/bash
set -e
python manage.py migrate --noinput
python manage.py init_deployment
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
```

### `railway.json` (Deployment Config)
```json
{
  "build": { "builder": "DOCKERFILE" },
  "deploy": { "numReplicas": 1 }
}
```

### `Procfile` & `nixpacks.toml` (Legacy - Not Used)
These files are ignored when using Dockerfile deployment.

---

## Troubleshooting

### "gunicorn: command not found"
✅ **FIXED** - Added `gunicorn==23.0.0` to requirements.txt

### Database Connection Error
- Verify PostgreSQL service is linked to Django service
- Check `DATABASE_URL` variable exists
- Ensure `dj-database-url` is in requirements.txt

### "Missing required environment variables"
- Check all variables in Railway dashboard
- Verify spelling (case-sensitive)
- Use Railway's "Raw Editor" to paste all at once

### Static Files Not Loading
- Ensure `whitenoise` is installed
- Check `STATICFILES_STORAGE` in prod.py
- Verify `collectstatic` ran in build logs

### Email Not Sending
- Verify Gmail App Password (not regular password)
- Check EMAIL_* variables are set correctly
- Test with `python manage.py test_env` locally first

### Superuser Not Created
- Check deployment logs for errors
- Verify `INITIAL_SUPERUSER_*` variables are set
- Email must be in `SUPERADMIN_EMAILS` list
- Run `python manage.py init_deployment --force` to retry

### Background Worker (qcluster) Not Running
- Check Railway logs for supervisor status messages
- Look for: `INFO success: qcluster entered RUNNING state`
- If missing, verify `supervisord.conf` is copied in Dockerfile
- Check entrypoint.sh is executable (`chmod +x`)

### Scheduled Reports Not Sending
- Verify qcluster is running (check logs for heartbeat messages)
- Check `/admin/django_q/schedule/` for schedule status
- View `/admin/reports/scheduledreportlog/` for error logs
- Use admin action "Send Reports Now" to test manually
- Verify recipients exist and are active at `/admin/reports/reportrecipient/`

### PDF Reports Failing (WeasyPrint)
- Ensure Dockerfile includes WeasyPrint system dependencies:
  `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
- Check Railway logs for WeasyPrint-specific errors

---

## Security Checklist

- [ ] `DJANGO_DEBUG=False` in production
- [ ] Secure `DJANGO_SECRET_KEY` generated and set
- [ ] Initial superuser password changed after first login
- [ ] `SUPERADMIN_EMAILS` list is restricted
- [ ] SSL/HTTPS enabled (Railway provides by default)
- [ ] Session timeout configured (default 1 hour)
- [ ] Email credentials secured (use app passwords, not account passwords)
- [ ] Database backups enabled in Railway
- [ ] Environment variables never committed to Git

---

## Monitoring & Maintenance

### Railway Dashboard
- **Deployments:** View build and deploy logs
- **Metrics:** CPU, Memory, Network usage
- **Logs:** Real-time application logs
- **Database:** Query console, backups

### Django Admin
- Monitor user activity at `/admin/accounts/user/`
- View email logs at `/admin/communications/emaillog/`
- Check audit trail at `/admin/accounts/userprofilechange/`
- Monitor scheduled reports at `/admin/reports/scheduledreportlog/`
- Manage report recipients at `/admin/reports/reportrecipient/`
- Monitor scheduled reports at `/admin/reports/scheduledreportlog/`
- Manage report recipients at `/admin/reports/reportrecipient/`

### Health Check
Railway auto-monitors: `https://your-app.up.railway.app/health/`

---

## Commands Reference

### Local Testing (Production-like)
```bash
# Use production settings locally
export DJANGO_SETTINGS_MODULE=config.settings.prod
export DATABASE_URL=postgres://localhost/chesanto_test

# Test initialization
python manage.py init_deployment

# Test with production server
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Railway CLI Commands
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Run migrations
railway run python manage.py migrate

# Create superuser
railway run python manage.py createsuperuser

# Shell access
railway run python manage.py shell
```

---

## Your New Secure Secret Key

**Copy this to Railway's `DJANGO_SECRET_KEY` variable:**
```
_&96_2g&qtkohtxd()sfv!gl6gigm)q-4o3qwd-%mb5wr%05r+
```

⚠️ **NEVER commit this to Git or share publicly!**

---

## Success Criteria

After deployment, you should be able to:
- ✅ Access the homepage at your Railway URL
- ✅ Login to admin panel at `/admin/`
- ✅ Login to frontend at `/auth/login/`
- ✅ Receive email notifications (invitations, OTP, password reset)
- ✅ Create new users via admin
- ✅ Upload profile photos
- ✅ All authentication flows working
- ✅ Both gunicorn and qcluster running (check supervisor logs)
- ✅ Scheduled reports sending at configured times
- ✅ Admin actions available in Reports section (Send, Retry, Activate/Deactivate)

---

**Questions or Issues?**
- Check Railway logs first (look for both gunicorn and qcluster output)
- Review Django logs in Railway dashboard
- Verify all environment variables are set correctly
- Check scheduled report logs at `/admin/reports/scheduledreportlog/`
- Test locally with `DJANGO_SETTINGS_MODULE=config.settings.prod`

**Ready to deploy! 🚀**
