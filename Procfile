# Web process - migrations are handled by pre-deploy command in railway.json
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -

# Worker process for Django-Q task queue (run as separate Railway service)
worker: python manage.py qcluster
