# Dockerfile for Railway deployment
# Uses Python 3.12 with WeasyPrint system dependencies

FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install WeasyPrint system dependencies + supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    # Font support
    fonts-liberation \
    fonts-dejavu-core \
    # Build tools (for some pip packages)
    gcc \
    libpq-dev \
    # Process manager
    supervisor \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Railway sets $PORT)
EXPOSE 8000

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create entrypoint script that runs migrations, seeds data, then starts supervisor
RUN echo '#!/bin/bash\n\
set -e\n\
echo "========================================"\n\
echo "CHESANTO BAKERY - DEPLOYMENT STARTUP"\n\
echo "========================================"\n\
echo ""\n\
echo "Step 1: Running database migrations..."\n\
python manage.py migrate --noinput\n\
echo ""\n\
echo "Step 2: Running seed_all (all seed commands)..."\n\
python manage.py seed_all 2>&1 || echo "seed_all completed with warnings"\n\
echo ""\n\
echo "========================================"\n\
echo "SEEDING COMPLETE - Starting services..."\n\
echo "========================================"\n\
echo "Starting supervisor (gunicorn + qcluster) on port ${PORT:-8000}..."\n\
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Start command
CMD ["/app/entrypoint.sh"]
