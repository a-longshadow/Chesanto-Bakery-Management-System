# Deployment Checklist

## ✅ Files Created/Fixed for Railway Compatibility

### Core Configuration Files:
- [x] `requirements.txt` - Root level requirements file
- [x] `Procfile` - Web server startup command
- [x] `railway.json` - Railway deployment configuration
- [x] `.env.example` - Environment variables template

### Django Settings:
- [x] Database configuration with `dj-database-url`
- [x] Automatic Railway environment detection
- [x] Conditional DEBUG settings
- [x] Proper ALLOWED_HOSTS configuration
- [x] WhiteNoise static files configuration
- [x] Environment-aware middleware and apps

## 🚀 Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements/local.txt
   ```

2. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Start development server:**
   ```bash
   python manage.py runserver
   ```

## 🚀 Railway Deployment Setup

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Configure Railway deployment"
   git push origin main
   ```

2. **Railway Dashboard:**
   - Create new project
   - Deploy from GitHub repo
   - Add PostgreSQL service
   - Environment variables will be auto-configured

3. **Required Environment Variables (Auto-set by Railway):**
   - `DATABASE_URL` - Automatically set by PostgreSQL service
   - `RAILWAY_ENVIRONMENT` - Automatically set to "production"
   - `PORT` - Automatically set by Railway

## 🔍 Key Compatibility Features

### Database:
- **Local**: SQLite (automatic)
- **Railway**: PostgreSQL (automatic via DATABASE_URL)
- **Migration**: Same commands work in both environments

### Static Files:
- **Local**: Django development server
- **Railway**: WhiteNoise with compression

### Debug Mode:
- **Local**: DEBUG=True (unless RAILWAY_ENVIRONMENT exists)
- **Railway**: DEBUG=False (automatic)

### Dependencies:
- **Local**: Includes debug toolbar, extensions
- **Railway**: Production-only dependencies

## 🚨 Pre-Deployment Checklist

- [ ] All migrations applied locally
- [ ] Static files work locally
- [ ] No environment-specific hardcoded values
- [ ] All sensitive data in environment variables
- [ ] Requirements files are complete
- [ ] Database queries are PostgreSQL compatible

## 🔧 Troubleshooting

### Common Issues:
1. **"No module named 'dj_database_url'"**
   - Solution: Ensure `dj-database-url>=2.1.0` in base.txt

2. **Static files not loading on Railway**
   - Solution: Run `python manage.py collectstatic` after deployment

3. **Database connection errors**
   - Solution: Ensure PostgreSQL service is added to Railway project

### Environment Detection:
```python
# Check current environment
import os
if os.getenv('RAILWAY_ENVIRONMENT'):
    print("Running on Railway")
else:
    print("Running locally")
```

This configuration ensures **zero-hassle deployment** - the same codebase works seamlessly in both environments without any manual intervention.
