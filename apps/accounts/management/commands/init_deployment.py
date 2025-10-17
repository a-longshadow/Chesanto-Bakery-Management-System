"""
Management command to initialize the system on first deployment.

This command:
1. Creates the initial superuser from environment variables
2. Verifies the superuser email is in SUPERADMIN_EMAILS
3. Is idempotent (safe to run multiple times)

Usage:
    python manage.py init_deployment

Environment Variables Required:
    INITIAL_SUPERUSER_EMAIL - Email for the first superuser
    INITIAL_SUPERUSER_PASSWORD - Password (should be changed after first login)
    INITIAL_SUPERUSER_FIRST_NAME - First name
    INITIAL_SUPERUSER_LAST_NAME - Last name
    INITIAL_SUPERUSER_MOBILE - Primary mobile number
    SUPERADMIN_EMAILS - Comma-separated list of superadmin emails
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.accounts.models import User
from apps.accounts.utils import is_superadmin_email


class Command(BaseCommand):
    help = 'Initialize system for first deployment (creates initial superuser from environment variables)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user exists (will update password)',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('🚀 CHESANTO BAKERY - DEPLOYMENT INITIALIZATION'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        # Get environment variables
        email = os.getenv('INITIAL_SUPERUSER_EMAIL')
        password = os.getenv('INITIAL_SUPERUSER_PASSWORD')
        first_name = os.getenv('INITIAL_SUPERUSER_FIRST_NAME')
        last_name = os.getenv('INITIAL_SUPERUSER_LAST_NAME')
        mobile = os.getenv('INITIAL_SUPERUSER_MOBILE')
        superadmin_emails = os.getenv('SUPERADMIN_EMAILS', '')

        # Validate required environment variables
        missing = []
        if not email:
            missing.append('INITIAL_SUPERUSER_EMAIL')
        if not password:
            missing.append('INITIAL_SUPERUSER_PASSWORD')
        if not first_name:
            missing.append('INITIAL_SUPERUSER_FIRST_NAME')
        if not last_name:
            missing.append('INITIAL_SUPERUSER_LAST_NAME')
        if not mobile:
            missing.append('INITIAL_SUPERUSER_MOBILE')

        if missing:
            self.stdout.write(self.style.ERROR('❌ Missing required environment variables:'))
            for var in missing:
                self.stdout.write(self.style.ERROR(f'   - {var}'))
            self.stdout.write('')
            self.stdout.write('Please set these in your .env file or Railway environment variables.')
            raise CommandError('Missing required environment variables')

        # Display configuration
        self.stdout.write(self.style.WARNING('📋 Configuration:'))
        self.stdout.write(f'   Email: {email}')
        self.stdout.write(f'   Name: {first_name} {last_name}')
        self.stdout.write(f'   Mobile: {mobile}')
        self.stdout.write(f'   Password: {"*" * len(password)}')
        self.stdout.write('')

        # Verify email is in SUPERADMIN_EMAILS
        self.stdout.write(self.style.WARNING('🔒 Security Check:'))
        self.stdout.write(f'   SUPERADMIN_EMAILS: {superadmin_emails}')
        
        if not is_superadmin_email(email):
            self.stdout.write(self.style.ERROR(f'❌ Email {email} is NOT in SUPERADMIN_EMAILS list!'))
            self.stdout.write('')
            self.stdout.write('Add this email to SUPERADMIN_EMAILS environment variable:')
            self.stdout.write(f'   SUPERADMIN_EMAILS={superadmin_emails},{email}')
            raise CommandError('Superuser email must be in SUPERADMIN_EMAILS list')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Email {email} is verified as superadmin'))
        self.stdout.write('')

        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            if not options['force']:
                self.stdout.write(self.style.WARNING(f'⚠️  User with email {email} already exists!'))
                self.stdout.write('')
                self.stdout.write('User details:')
                self.stdout.write(f'   Name: {user.get_full_name()}')
                self.stdout.write(f'   Role: {user.role}')
                self.stdout.write(f'   Active: {user.is_active}')
                self.stdout.write(f'   Superuser: {user.is_superuser}')
                self.stdout.write('')
                self.stdout.write('Run with --force to update password.')
                return
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Updating existing user: {email}'))
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.is_approved = True
                user.role = 'SUPERADMIN'
                user.save()
                self.stdout.write(self.style.SUCCESS('✅ Password updated successfully!'))
                self.stdout.write('')
                return

        except User.DoesNotExist:
            pass

        # Create superuser
        self.stdout.write(self.style.WARNING('👤 Creating superuser...'))
        
        try:
            user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                mobile_primary=mobile,
            )
            
            # Ensure role is SUPERADMIN (should be set by create_superuser)
            user.role = 'SUPERADMIN'
            user.email_verified = True  # Auto-verify for initial setup
            from django.utils import timezone
            user.email_verified_at = timezone.now()
            user.is_approved = True
            user.save()

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ Superuser created successfully!'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('📊 User Details:'))
            self.stdout.write(f'   ID: {user.id}')
            self.stdout.write(f'   Email: {user.email}')
            self.stdout.write(f'   Name: {user.get_full_name()}')
            self.stdout.write(f'   Mobile: {user.mobile_primary}')
            self.stdout.write(f'   Role: {user.role}')
            self.stdout.write(f'   Superuser: {user.is_superuser}')
            self.stdout.write(f'   Active: {user.is_active}')
            self.stdout.write(f'   Approved: {user.is_approved}')
            self.stdout.write(f'   Email Verified: {user.email_verified}')
            self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('🎉 Deployment initialization complete!'))
            self.stdout.write('')
            self.stdout.write('Next steps:')
            self.stdout.write('1. Login at /admin/ with the credentials')
            self.stdout.write('2. Change password after first login (IMPORTANT!)')
            self.stdout.write('3. Create additional users through admin interface')
            self.stdout.write('')
            self.stdout.write('=' * 70)

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'❌ Error creating superuser: {str(e)}'))
            raise CommandError(f'Failed to create superuser: {str(e)}')
