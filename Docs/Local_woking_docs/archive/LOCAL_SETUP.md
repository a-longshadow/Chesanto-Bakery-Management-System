# Local Development Setup

## Quick Start

1. **Clone and navigate to the project:**
   ```bash
   cd /Users/joe/Documents/Chesanto-Bakery-Management-System
   ```

2. **Set up Python virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements/local.txt
   ```

4. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server:**
   ```bash
   python manage.py runserver
   ```

8. **Visit:** http://127.0.0.1:8000

## Project Structure
- `config/` - Django project settings and configuration
- `apps/` - Domain-specific Django applications
- `static/` - Static files (CSS, JS, images)
- `templates/` - HTML templates
- `requirements/` - Environment-specific requirements

## Environment Variables
- `DJANGO_DEBUG` - Set to True for development
- `DJANGO_SECRET_KEY` - Secret key for Django
- `DJANGO_SETTINGS_MODULE` - Settings module to use

## Database
- **Local:** SQLite (automatic)
- **Production:** PostgreSQL via Railway (automatic)

## Commands
- `python manage.py check` - Check for issues
- `python manage.py test` - Run tests
- `python manage.py collectstatic` - Collect static files
