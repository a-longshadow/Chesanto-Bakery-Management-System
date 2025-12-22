"""
Seed Superadmin Users
Creates the core superadmin accounts for Chesanto Bakery.

Usage:
    python manage.py seed_superadmins
    python manage.py seed_superadmins --password "CustomPassword123!"
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed superadmin users for Chesanto Bakery'

    # Superadmin accounts
    # Format: (email, first_name, last_name)
    SUPERADMINS = [
        ('joe@coophive.network', 'Joe', 'Maina'),
        ('mainajoe21@gmail.com', 'Joe', 'Maina'),
        ('emma.oradu@gmail.com', 'Emma', 'Oradu'),
        ('reinnyetyang@gmail.com', 'Oita', 'Etyang'),
        ('doreenongoro@gmail.com', 'Doreen', 'Ongoro'),
        ('chesantobakery@gmail.com', 'Chesanto', 'Bakery'),
    ]

    # Default password (must change on first login)
    DEFAULT_PASSWORD = 'Chesanto2025!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default=self.DEFAULT_PASSWORD,
            help=f'Password for superadmins (default: {self.DEFAULT_PASSWORD})',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing superadmins (update password, reactivate)',
        )

    def handle(self, *args, **options):
        password = options['password']
        reset = options['reset']

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('👑 SEEDING SUPERADMINS: Chesanto Bakery'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        if reset:
            self.stdout.write(self.style.WARNING('⚠️  RESET mode: Will update passwords and reactivate\n'))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for email, first_name, last_name in self.SUPERADMINS:
                try:
                    existing = User.objects.filter(email=email).first()

                    if existing:
                        if reset:
                            # Reset/update existing superadmin
                            existing.first_name = first_name
                            existing.last_name = last_name
                            existing.role = 'SUPERADMIN'
                            existing.is_superuser = True
                            existing.is_staff = True
                            existing.is_active = True
                            existing.is_approved = True
                            existing.must_change_password = True
                            existing.set_password(password)
                            existing.save()
                            updated_count += 1
                            status = self.style.WARNING('RESET')
                        else:
                            skipped_count += 1
                            status = self.style.SUCCESS('EXISTS')
                    else:
                        # Create new superadmin
                        User.objects.create_superuser(
                            email=email,
                            password=password,
                            first_name=first_name,
                            last_name=last_name,
                            role='SUPERADMIN',
                            is_approved=True,
                            must_change_password=True,
                            email_verified=True,
                            email_verified_at=timezone.now(),
                        )
                        created_count += 1
                        status = self.style.SUCCESS('CREATED')

                    self.stdout.write(f'  👑 {first_name} {last_name} ({email}) - {status}')

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ {first_name} {last_name} ({email}) - ERROR: {str(e)}')
                    )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Superadmin seeding complete!'))
        self.stdout.write(f'   Created: {created_count}')
        self.stdout.write(f'   Reset: {updated_count}')
        self.stdout.write(f'   Skipped (already exists): {skipped_count}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🔐 Login Credentials:'))
        self.stdout.write(f'   Password: {password}')
        self.stdout.write('   (All superadmins must change password on first login)')
        self.stdout.write('')
        
        # Show superadmin count
        total = User.objects.filter(role='SUPERADMIN', is_active=True).count()
        self.stdout.write(f'📊 Total active superadmins: {total}')
        self.stdout.write('')
