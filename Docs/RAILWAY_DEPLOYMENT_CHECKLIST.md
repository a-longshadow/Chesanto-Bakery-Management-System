# 🚀 Railway Deployment Checklist

> **Version:** 1.0 | **Last Updated:** December 22, 2025

Complete guide for deploying Chesanto Bakery Management System to a fresh Railway instance.

---

## 📋 Pre-Deployment Checklist

Before you start, ensure you have:

- [ ] GitHub account with access to the repository
- [ ] Railway account (https://railway.app)
- [ ] Email credentials for system emails (Gmail recommended)
- [ ] Domain name (optional, Railway provides free subdomain)

---

## 🔧 Step 1: Create Railway Project

1. **Login to Railway**
   - Go to https://railway.app
   - Sign in with GitHub

2. **Create New Project**
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Choose: `a-longshadow/Chesanto-Bakery-Management-System`
   - Select branch: `foundation-rebuild`

3. **Add PostgreSQL Database**
   - In your project, click **"+ New"**
   - Select **"Database"** → **"PostgreSQL"**
   - Railway auto-creates `DATABASE_URL` variable

---

## 🔐 Step 2: Configure Environment Variables

Click on the web service → **Variables** tab → Add the following:

### Required Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | `your-secret-key-here` | Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | Must be False in production |
| `ALLOWED_HOSTS` | `*.railway.app,*.up.railway.app` | Add custom domain if using |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Production settings |

### Database (Auto-configured)

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | (auto-set by Railway) | PostgreSQL connection string |

### Email Configuration (Gmail)

| Variable | Value | Notes |
|----------|-------|-------|
| `EMAIL_HOST` | `smtp.gmail.com` | Gmail SMTP |
| `EMAIL_PORT` | `587` | TLS port |
| `EMAIL_USE_TLS` | `True` | Enable TLS |
| `EMAIL_HOST_USER` | `chesantobakery@gmail.com` | Your Gmail address |
| `EMAIL_HOST_PASSWORD` | `your-app-password` | Gmail App Password (not regular password) |
| `DEFAULT_FROM_EMAIL` | `Chesanto Bakery <chesantobakery@gmail.com>` | From address |

#### Getting Gmail App Password:
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for "Mail" on "Other (Custom name)"
5. Use this 16-character password

### Superadmin (Initial User from ENV)

| Variable | Value | Notes |
|----------|-------|-------|
| `DJANGO_SUPERUSER_EMAIL` | `admin@chesanto.co.ke` | Initial superadmin email |
| `DJANGO_SUPERUSER_PASSWORD` | `SecurePassword123!` | Initial superadmin password |
| `DJANGO_SUPERUSER_FIRST_NAME` | `Admin` | First name |
| `DJANGO_SUPERUSER_LAST_NAME` | `User` | Last name |

### Optional Variables

| Variable | Value | Notes |
|----------|-------|-------|
| `CSRF_TRUSTED_ORIGINS` | `https://*.railway.app,https://*.up.railway.app` | For form submissions |
| `SERVER_URL` | `https://your-app.up.railway.app` | Auto-detected, but can override |

---

## 🏗️ Step 3: Deploy

1. **Trigger Deployment**
   - Railway auto-deploys on push to connected branch
   - Or click **"Deploy"** button manually

2. **Monitor Build Logs**
   - Click on deployment → **Build Logs**
   - Should see Docker build completing

3. **Monitor Deploy Logs**
   - Click on deployment → **Deploy Logs**
   - Look for:
   ```
   ========================================
   CHESANTO BAKERY - DEPLOYMENT STARTUP
   ========================================
   
   Step 1: Running database migrations...
   Step 2: Running seed_all (all seed commands)...
   ```

---

## ✅ Step 4: Verify Deployment

### Check Deploy Logs for Success

You should see output for each seed command:

```
▶️  Seeding Superadmin from ENV (Phase 1)...
✅ Superadmin from ENV seeded successfully

▶️  Seeding Superadmin Accounts (Phase 1)...
👑 Joe Maina (joe@coophive.network) - CREATED
👑 Joe Maina (mainajoe21@gmail.com) - CREATED
...
✅ Superadmin Accounts seeded successfully

▶️  Seeding Inventory Items (Phase 2)...
✅ Inventory Items seeded successfully

▶️  Seeding Employees & Salesmen (Phase 3)...
✅ Employees & Salesmen seeded successfully

▶️  Seeding Expense Categories (Phase 4)...
✅ Expense Categories seeded successfully

▶️  Seeding Report Schedules (Phase 5)...
✅ Report Schedules seeded successfully
```

### Test the Application

1. **Get your app URL**
   - In Railway, click **Settings** → **Domains**
   - Copy the URL (e.g., `https://chesanto-xyz.up.railway.app`)

2. **Test login**
   - Go to: `https://your-app.up.railway.app/auth/login/`
   - Login with a superadmin account:
     - Email: `joe@coophive.network` (or any from seed_superadmins)
     - Password: `Chesanto2025!`

3. **Verify data in Django Admin**
   - Go to: `https://your-app.up.railway.app/admin/`
   - Check:
     - [ ] Users exist (Accounts → Users)
     - [ ] Products exist (Products → Products)
     - [ ] Inventory items exist (check via shell or production module)

---

## 🔄 Step 5: Post-Deployment Tasks

### Change Default Passwords

All seeded users have password `Chesanto2025!`. Users should change on first login.

### Add Report Recipients

Reports won't send until recipients are added:

1. Go to Django Admin → Reports → Report Recipients
2. Add email addresses for each report schedule

Or run via Railway shell:
```bash
railway run python manage.py setup_report_schedules --add-recipient "Joe Maina <joe@coophive.network>"
```

### Configure Custom Domain (Optional)

1. In Railway → Settings → Domains
2. Click **"+ Custom Domain"**
3. Add your domain (e.g., `bakery.chesanto.co.ke`)
4. Update DNS records as shown
5. Add domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

---

## 🛠️ Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Invalid credentials" on login | Check seeding ran; try password `Chesanto2025!` |
| 500 errors | Check `DEBUG=False` and `ALLOWED_HOSTS` includes your domain |
| Static files not loading | Verify `collectstatic` ran in build logs |
| Emails not sending | Check Gmail App Password; verify EMAIL_* variables |
| "CSRF verification failed" | Add domain to `CSRF_TRUSTED_ORIGINS` |

### Checking Logs

```bash
# View deploy logs in Railway dashboard
# Or use Railway CLI:
railway logs
```

### Running Commands Manually

If seeding didn't run:
```bash
# Via Railway CLI
railway run python manage.py seed_all

# Or individual commands
railway run python manage.py seed_superadmins
railway run python manage.py seed_employees
railway run python manage.py seed_inventory
```

### Database Reset (Nuclear Option)

If you need to start fresh:
```bash
railway run python manage.py flush --noinput
railway run python manage.py migrate
railway run python manage.py seed_all
```

---

## 📊 Monitoring

### Health Check

The app responds to:
- `/` - Dashboard (redirects to login if not authenticated)
- `/auth/login/` - Login page
- `/admin/` - Django Admin

### Django-Q Cluster

The supervisor runs both gunicorn and qcluster:
- **gunicorn**: Web server
- **qcluster**: Background task processor (for scheduled reports)

Check logs for:
```
Q Cluster xxx-xxx-xxx running.
```

---

## 🔒 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is unique and not committed to git
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] Using HTTPS (Railway provides by default)
- [ ] Gmail App Password used (not regular password)
- [ ] Default passwords changed after first login

---

## 📁 Environment Variables Template

Copy this template and fill in values:

```env
# Required
SECRET_KEY=your-50-character-secret-key-here
DEBUG=False
ALLOWED_HOSTS=*.railway.app,*.up.railway.app
DJANGO_SETTINGS_MODULE=config.settings.production

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=chesantobakery@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=Chesanto Bakery <chesantobakery@gmail.com>

# Initial Superadmin (optional - seed_superadmins handles main users)
DJANGO_SUPERUSER_EMAIL=admin@chesanto.co.ke
DJANGO_SUPERUSER_PASSWORD=ChangeThisPassword123!
DJANGO_SUPERUSER_FIRST_NAME=Admin
DJANGO_SUPERUSER_LAST_NAME=User

# CSRF (add custom domains here)
CSRF_TRUSTED_ORIGINS=https://*.railway.app,https://*.up.railway.app
```

---

## 🎉 Done!

Your Chesanto Bakery Management System is now live on Railway!

**Default Login:**
- URL: `https://your-app.up.railway.app`
- Email: `joe@coophive.network` (or other superadmin)
- Password: `Chesanto2025!` (change immediately)

---

*Document Version: 1.0 | Created: December 22, 2025*
