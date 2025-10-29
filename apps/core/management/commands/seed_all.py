"""
Master Seeding Command
Seeds all apps with initial data in correct dependency order
Safe for production deployment
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Seed all apps with initial data in correct dependency order'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip seeding if data already exists (production safety)',
        )
        parser.add_argument(
            '--apps',
            nargs='+',
            help='Specific apps to seed (e.g., inventory products)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🌱 MASTER SEEDING: Chesanto Bakery Management System'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
        
        # Check if data exists (production safety)
        if options['skip_existing']:
            if self._data_exists():
                self.stdout.write(self.style.WARNING('⚠️  Data already exists. Skipping seeding.'))
                self.stdout.write('   Use without --skip-existing to re-seed (idempotent).\n')
                return
        
        # Define seeding order (respects dependencies)
        all_commands = [
            ('seed_inventory', 'Inventory', 'Phase 1'),
            ('seed_products', 'Products', 'Phase 1'),
            ('recalculate_costs', 'Mix Costs', 'Phase 1 Integration'),
            # Future commands (add as implemented):
            # ('seed_production', 'Production', 'Phase 2'),
            # ('seed_sales', 'Sales', 'Phase 2'),
            # ('seed_reports', 'Reports', 'Phase 3'),
            # ('seed_payroll', 'Payroll', 'Phase 4'),
        ]
        
        # Filter by specific apps if requested
        if options['apps']:
            commands_to_run = [
                cmd for cmd in all_commands 
                if any(app in cmd[0] for app in options['apps'])
            ]
        else:
            commands_to_run = all_commands
        
        if not commands_to_run:
            self.stdout.write(self.style.ERROR('❌ No valid commands found'))
            return
        
        # Run seeding commands
        success_count = 0
        fail_count = 0
        
        for command, name, phase in commands_to_run:
            self.stdout.write(f'\n▶️  Seeding {name} ({phase})...')
            self.stdout.write('-' * 60)
            
            try:
                call_command(command)
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ {name} seeded successfully\n'))
            except Exception as e:
                fail_count += 1
                self.stdout.write(self.style.ERROR(f'❌ {name} seeding failed: {str(e)}\n'))
                # Continue with other commands (don't exit)
        
        # Summary
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'✅ MASTER SEEDING COMPLETE!'))
        self.stdout.write(f'   Success: {success_count} | Failed: {fail_count}')
        self.stdout.write('=' * 60 + '\n')
        
        # Show next steps
        if fail_count == 0:
            self.stdout.write(self.style.SUCCESS('🎉 All data seeded successfully!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('  1. Visit http://127.0.0.1:8000/admin/ to view data')
            self.stdout.write('  2. Test workflows in Django Admin')
            self.stdout.write('  3. Proceed with frontend development\n')

    def _data_exists(self):
        """Check if data already exists"""
        try:
            from apps.inventory.models import InventoryItem
            from apps.products.models import Product
            
            return InventoryItem.objects.exists() or Product.objects.exists()
        except Exception:
            return False
