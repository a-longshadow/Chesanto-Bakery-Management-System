#!/bin/bash
# Deployment Seeding Script for Railway
# Runs migrations and seeds initial data
# Safe for production (idempotent commands)

set -e  # Exit on error

echo "======================================================================"
echo "🚀 Chesanto Bakery Deployment: Migrations & Data Seeding"
echo "======================================================================"
echo ""

# Step 1: Run migrations
echo "📦 Step 1: Running database migrations..."
python manage.py migrate --noinput
echo "✅ Migrations complete"
echo ""

# Step 2: Collect static files (production)
if [ "$DJANGO_DEBUG" = "False" ]; then
    echo "📁 Step 2: Collecting static files..."
    python manage.py collectstatic --noinput
    echo "✅ Static files collected"
    echo ""
fi

# Step 3: Seed data (skip if exists in production)
echo "🌱 Step 3: Seeding initial data..."
if [ "$DJANGO_DEBUG" = "False" ]; then
    # Production: skip if data exists
    python manage.py seed_all --skip-existing
else
    # Development: always seed (idempotent)
    python manage.py seed_all
fi
echo "✅ Data seeding complete"
echo ""

# Step 4: Create superuser if needed (production only)
if [ "$DJANGO_DEBUG" = "False" ]; then
    echo "👤 Step 4: Checking for superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(is_superuser=True).exists():
    print('⚠️  No superuser found. Create one manually with: python manage.py createsuperuser')
else:
    print('✅ Superuser exists')
" || echo "⚠️  Superuser check skipped"
    echo ""
fi

echo "======================================================================"
echo "✅ Deployment complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Visit your app URL to verify deployment"
echo "  2. Login to /admin/ with superuser credentials"
echo "  3. Verify seeded data is present"
echo ""
