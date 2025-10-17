"""
Management command to designate the Primary SUPERADMIN
Run this command to set the first/primary SUPERADMIN who cannot be edited by others
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Designate a user as the Primary SUPERADMIN (CEO/System Owner)'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address of the user to designate as Primary SUPERADMIN'
        )

    def handle(self, *args, **options):
        email = options['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User with email "{email}" does not exist.'))
            return

        # Check if user is a SUPERADMIN
        if user.role != 'SUPERADMIN':
            self.stdout.write(self.style.ERROR(f'❌ User "{email}" is not a SUPERADMIN. Current role: {user.get_role_display()}'))
            self.stdout.write(self.style.WARNING('Only SUPERADMIN users can be designated as Primary SUPERADMIN.'))
            return

        # Check if there's already a Primary SUPERADMIN
        existing_primary = User.objects.filter(is_primary_superadmin=True).first()
        if existing_primary and existing_primary.id != user.id:
            self.stdout.write(self.style.WARNING(f'⚠️  A Primary SUPERADMIN already exists: {existing_primary.email}'))
            
            # Ask for confirmation
            confirm = input('Do you want to replace them? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return
            
            # Remove primary status from existing
            existing_primary.is_primary_superadmin = False
            existing_primary.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Removed Primary SUPERADMIN status from {existing_primary.email}'))

        # Set as Primary SUPERADMIN
        user.is_primary_superadmin = True
        user.save()

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully designated {user.email} as Primary SUPERADMIN'))
        self.stdout.write(self.style.SUCCESS(f'  Name: {user.get_full_name()}'))
        self.stdout.write(self.style.SUCCESS(f'  Role: {user.get_role_display()}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.WARNING('\nProtections Applied:'))
        self.stdout.write('  • Cannot be edited by other SUPERADMINs')
        self.stdout.write('  • Cannot be deleted by anyone')
        self.stdout.write('  • Can only be modified by themselves')
        self.stdout.write(self.style.WARNING('\nNote: These protections ensure system security and data integrity.'))
