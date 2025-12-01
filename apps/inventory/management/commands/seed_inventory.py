"""
Seed Inventory Management Command
Creates singleton records for all 23 inventory items.

This must be run ONCE after migrations to initialize all ItemXXDetails tables.
Each item table gets exactly one row (pk=1) representing that item's state.

Usage:
    python manage.py seed_inventory
    python manage.py seed_inventory --reset  # WARNING: Clears existing data

After running:
    - All 23 ItemXXDetails tables have exactly 1 row each
    - current_stock = 0, last_purchase_unit_price = 0
    - Ready to accept purchases via create_purchase_atomic()
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from apps.inventory.routing import INVENTORY_ITEMS, get_details_model


class Command(BaseCommand):
    help = 'Seed inventory with all 23 pre-defined items'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all items to initial state (WARNING: Clears stock data)',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=1,
            help='User ID for created_by field (default: 1)',
        )
    
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        reset = options['reset']
        user_id = options['user_id']
        
        # Get the user for created_by field
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f'User with ID {user_id} not found. '
                               f'Create a user first or specify --user-id.')
            )
            return
        
        if reset:
            self.stdout.write(
                self.style.WARNING('⚠️  RESET mode: Existing stock data will be cleared!')
            )
        
        self.stdout.write('Seeding inventory items...\n')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for item_id, name, is_ingredient, unit in INVENTORY_ITEMS:
            try:
                with transaction.atomic():
                    ItemDetailsModel = get_details_model(item_id)
                    
                    # Check if item already exists
                    try:
                        existing = ItemDetailsModel.objects.get(pk=1)
                        
                        if reset:
                            # Reset to initial state
                            existing.name = name
                            existing.unit_of_measure = unit
                            existing.current_stock = Decimal('0.0000')
                            existing.last_purchase_unit_price = Decimal('0.0000')
                            existing.last_purchase_date = None
                            existing.minimum_stock_level = Decimal('0.0000')
                            existing.updated_by = user
                            existing.save()
                            updated_count += 1
                            status = self.style.WARNING('RESET')
                        else:
                            skipped_count += 1
                            status = self.style.SUCCESS('EXISTS')
                    
                    except ItemDetailsModel.DoesNotExist:
                        # Create new item
                        ItemDetailsModel.objects.create(
                            id=1,  # Force pk=1 for singleton
                            name=name,
                            unit_of_measure=unit,
                            current_stock=Decimal('0.0000'),
                            last_purchase_unit_price=Decimal('0.0000'),
                            last_purchase_date=None,
                            minimum_stock_level=Decimal('0.0000'),
                            created_by=user,
                        )
                        created_count += 1
                        status = self.style.SUCCESS('CREATED')
                    
                    item_type = 'Ingredient' if is_ingredient else 'Indirect Cost'
                    self.stdout.write(f'  [{item_id:02d}] {name} ({unit}) - {item_type} - {status}')
                    
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'  [{item_id:02d}] {name} - ERROR: {str(e)}')
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Seeding complete!'))
        self.stdout.write(f'   Created: {created_count}')
        self.stdout.write(f'   Reset: {updated_count}')
        self.stdout.write(f'   Skipped (already exists): {skipped_count}')
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Set minimum_stock_level for each item via admin')
        self.stdout.write('  2. Record initial purchases via the web interface')
        self.stdout.write('  3. Or use create_purchase_atomic() in code/shell')
