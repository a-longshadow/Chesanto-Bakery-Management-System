# Railway Deployment Guide
**Project:** Chesanto Bakery Management System  
**Date:** October 18, 2025  
**Platform:** Railway.app

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

# Start Gunicorn server
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

**Note:** The `init_deployment` command is **idempotent** - it's safe to run multiple times. It will:
- ✅ Create superuser on first deployment
- ✅ Skip if user already exists (unless --force flag)
- ✅ Verify email is in SUPERADMIN_EMAILS list

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

### `nixpacks.toml` (Build Configuration)
Defines how Railway builds and starts your app:
- Installs Python packages
- Collects static files
- Runs migrations on startup
- Runs init_deployment on startup
- Starts Gunicorn

### `Procfile` (Legacy, still used)
```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
```

### `railway.json` (Deployment Config)
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": { "numReplicas": 1 }
}
```

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

---

**Questions or Issues?**
- Check Railway logs first
- Review Django logs in Railway dashboard
- Verify all environment variables are set correctly
- Test locally with `DJANGO_SETTINGS_MODULE=config.settings.prod`

**Ready to deploy! 🚀**
