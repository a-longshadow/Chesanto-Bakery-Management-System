"""
Management command to seed 2 weeks of production data
Usage: python manage.py seed_production_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from apps.products.models import Product, Mix
from apps.production.models import DailyProduction, ProductionBatch
from apps.inventory.models import InventoryItem


class Command(BaseCommand):
    help = 'Seed 2 weeks of production data (5 mixes daily per product)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of days to seed (default: 14)'
        )
        parser.add_argument(
            '--batches-per-day',
            type=int,
            default=5,
            help='Number of batches per product per day (default: 5)'
        )
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get system user
        system_user = User.objects.filter(role='SUPERADMIN').first()
        if not system_user:
            system_user = User.objects.filter(is_staff=True).first()
        
        if not system_user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create one first.'))
            return
        
        days = options['days']
        batches_per_day = options['batches_per_day']
        
        # Get all active products
        products = Product.objects.filter(is_active=True)
        if not products.exists():
            self.stdout.write(self.style.ERROR('No products found. Please seed products first.'))
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'🏭 Seeding {days} days of production data'))
        self.stdout.write(self.style.SUCCESS(f'📦 {batches_per_day} batches per product per day'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Ensure adequate inventory for production
        self._ensure_inventory()
        
        # Start date (X days ago)
        start_date = datetime.now().date() - timedelta(days=days - 1)
        
        total_batches = 0
        total_days = 0
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            # Skip future dates
            if current_date > datetime.now().date():
                continue
            
            self.stdout.write(f'\n📅 {current_date.strftime("%A, %B %d, %Y")}')
            self.stdout.write('-' * 70)
            
            # Get or create DailyProduction for this date
            daily_production, created = DailyProduction.objects.get_or_create(
                date=current_date,
                defaults={
                    'is_closed': current_date < datetime.now().date(),  # Close past dates
                    'created_by': system_user,
                    'updated_by': system_user,
                }
            )
            
            if created:
                self.stdout.write(f'  ✅ Created DailyProduction for {current_date}')
            else:
                self.stdout.write(f'  ℹ️  DailyProduction already exists for {current_date}')
            
            # Set opening stock (first day or from previous day's closing)
            if day_offset == 0:
                daily_production.opening_bread_stock = 50
                daily_production.opening_kdf_stock = 30
                daily_production.opening_scones_stock = 40
            else:
                prev_date = current_date - timedelta(days=1)
                prev_daily = DailyProduction.objects.filter(date=prev_date).first()
                if prev_daily:
                    daily_production.opening_bread_stock = prev_daily.closing_bread_stock or 0
                    daily_production.opening_kdf_stock = prev_daily.closing_kdf_stock or 0
                    daily_production.opening_scones_stock = prev_daily.closing_scones_stock or 0
            
            # Add indirect costs (realistic daily costs)
            daily_production.diesel_cost = Decimal(random.randint(2500, 4000))
            daily_production.firewood_cost = Decimal(random.randint(1000, 2000))
            daily_production.electricity_cost = Decimal(random.randint(800, 1500))
            daily_production.fuel_distribution_cost = Decimal(random.randint(1500, 3000))
            daily_production.other_indirect_costs = Decimal(random.randint(500, 1500))
            
            daily_production.save()
            
            # Create production batches for each product
            day_batches = 0
            
            for product in products:
                # Get active mixes for this product
                mixes = Mix.objects.filter(product=product, is_active=True)
                
                if not mixes.exists():
                    self.stdout.write(f'  ⚠️  No mixes found for {product.name}. Skipping.')
                    continue
                
                # Use first mix (or rotate through mixes)
                for batch_num in range(batches_per_day):
                    mix = mixes[batch_num % mixes.count()]
                    
                    # Calculate batch number (sequential for the day)
                    existing_batches = ProductionBatch.objects.filter(
                        daily_production=daily_production
                    ).count()
                    batch_number = existing_batches + 1
                    
                    # Generate realistic output (90-110% of expected)
                    variance_factor = random.uniform(0.90, 1.10)
                    actual_packets = int(mix.expected_packets * variance_factor)
                    
                    # Rejects only for Bread (1-5%)
                    rejects = 0
                    if product.name == 'Bread':
                        rejects = random.randint(0, int(actual_packets * 0.05))
                    
                    # Random start/end times (6 AM - 4 PM production window)
                    start_hour = random.randint(6, 15)
                    start_minute = random.choice([0, 15, 30, 45])
                    end_hour = start_hour + random.randint(1, 3)
                    end_minute = random.choice([0, 15, 30, 45])
                    
                    # Check if batch already exists
                    if ProductionBatch.objects.filter(
                        daily_production=daily_production,
                        batch_number=batch_number
                    ).exists():
                        continue
                    
                    try:
                        # Create batch
                        batch = ProductionBatch.objects.create(
                            daily_production=daily_production,
                            mix=mix,
                            batch_number=batch_number,
                            actual_packets=actual_packets,
                            rejects_produced=rejects,
                            start_time=f'{start_hour:02d}:{start_minute:02d}',
                            end_time=f'{end_hour:02d}:{end_minute:02d}',
                            quality_notes=random.choice([
                                'Good quality',
                                'Excellent batch',
                                'Standard quality',
                                'Slightly darker crust',
                                'Perfect texture',
                            ]),
                            created_by=system_user,
                            updated_by=system_user
                        )
                        
                        self.stdout.write(
                            f'  ✅ Batch #{batch_number}: {mix.product.name} - '
                            f'{actual_packets} packets (expected: {mix.expected_packets})'
                        )
                        day_batches += 1
                        total_batches += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠️  Failed to create batch #{batch_number} for {product.name}: {str(e)}'
                            )
                        )
            
            # Update daily production totals
            daily_production.refresh_from_db()
            
            # Set dispatched amounts (80-95% of produced)
            dispatch_factor = random.uniform(0.80, 0.95)
            daily_production.bread_dispatched = int(daily_production.bread_produced * dispatch_factor)
            daily_production.kdf_dispatched = int(daily_production.kdf_produced * dispatch_factor)
            daily_production.scones_dispatched = int(daily_production.scones_produced * dispatch_factor)
            
            # Set returned amounts (1-5% of dispatched)
            return_factor = random.uniform(0.01, 0.05)
            daily_production.bread_returned = int(daily_production.bread_dispatched * return_factor)
            daily_production.kdf_returned = int(daily_production.kdf_dispatched * return_factor)
            daily_production.scones_returned = int(daily_production.scones_dispatched * return_factor)
            
            daily_production.save()
            
            self.stdout.write(f'  📊 Created {day_batches} batches for this day')
            total_days += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ Production data seeding complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'📅 Days seeded: {total_days}')
        self.stdout.write(f'📦 Total batches created: {total_batches}')
        self.stdout.write(f'💰 Average batches per day: {total_batches / total_days if total_days > 0 else 0:.1f}')
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Check Production dashboard: /production/')
        self.stdout.write('  2. View batch details for any day')
        self.stdout.write('  3. Check inventory deductions in admin')
        self.stdout.write('')
    
    def _ensure_inventory(self):
        """Ensure adequate inventory for production runs"""
        self.stdout.write('')
        self.stdout.write('📦 Checking inventory levels...')
        
        inventory_items = InventoryItem.objects.all()
        restocked_count = 0
        
        for item in inventory_items:
            # Ensure minimum stock for production
            min_stock = item.reorder_level * 3  # 3x reorder level for 2 weeks
            
            if item.current_stock < min_stock:
                old_stock = item.current_stock
                item.current_stock = min_stock
                item.save()
                
                self.stdout.write(
                    f'  ✅ Restocked {item.name}: {old_stock} → {min_stock} {item.recipe_unit}'
                )
                restocked_count += 1
        
        if restocked_count > 0:
            self.stdout.write(f'  📊 Restocked {restocked_count} items')
        else:
            self.stdout.write('  ✅ All inventory levels adequate')
        
        self.stdout.write('')
