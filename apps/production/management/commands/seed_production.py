"""
Seed sample production data for testing
Creates DailyProduction, ProductionBatch, and IndirectCost records
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from apps.production.models import DailyProduction, ProductionBatch, IndirectCost
from apps.products.models import Product, Mix
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed sample production data (idempotent - safe to run multiple times)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🌱 Seeding Production Data...\n'))
        
        # Get or create system user for created_by fields
        system_user, _ = User.objects.get_or_create(
            email='system@chesanto.com',
            defaults={
                'username': 'system',
                'role': 'SUPERADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Get products and mixes
        try:
            bread = Product.objects.get(name='Bread')
            kdf = Product.objects.get(name='KDF')
            scones = Product.objects.get(name='Scones')
            
            bread_mix = Mix.objects.filter(product=bread, is_active=True).first()
            kdf_mix = Mix.objects.filter(product=kdf, is_active=True).first()
            scones_mix = Mix.objects.filter(product=scones, is_active=True).first()
            
            if not all([bread_mix, kdf_mix, scones_mix]):
                self.stdout.write(self.style.ERROR(
                    '❌ Missing mixes. Run seed_products first.'
                ))
                return
        
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                '❌ Products not found. Run seed_products first.'
            ))
            return
        
        # Create production data for today
        today = date.today()
        
        # 1. Create or get DailyProduction for today
        daily_production, created = DailyProduction.objects.get_or_create(
            date=today,
            defaults={
                'bread_opening_stock': 20,  # Leftover from yesterday
                'kdf_opening_stock': 15,
                'scones_opening_stock': 10,
                'created_by': system_user,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Created DailyProduction for {today}'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'⚠️  DailyProduction for {today} already exists'
            ))
        
        # 2. Create Production Batches
        batches_data = [
            {
                'mix': bread_mix,
                'product': bread,
                'expected_packets': 132,
                'actual_packets': 130,  # 2 loaves variance (-1.5%)
                'rejects_produced': 5,  # 5 rejects (Bread only)
                'batch_number': 'BREAD-001',
            },
            {
                'mix': bread_mix,
                'product': bread,
                'expected_packets': 132,
                'actual_packets': 135,  # 3 loaves over (+2.3%)
                'rejects_produced': 3,
                'batch_number': 'BREAD-002',
            },
            {
                'mix': kdf_mix,
                'product': kdf,
                'expected_packets': 107,
                'actual_packets': 105,  # 2 packets under (-1.9%)
                'rejects_produced': 0,  # KDF doesn't have rejects
                'batch_number': 'KDF-001',
            },
            {
                'mix': kdf_mix,
                'product': kdf,
                'expected_packets': 107,
                'actual_packets': 108,  # 1 packet over (+0.9%)
                'rejects_produced': 0,
                'batch_number': 'KDF-002',
            },
            {
                'mix': scones_mix,
                'product': scones,
                'expected_packets': 102,
                'actual_packets': 100,  # 2 packets under (-2.0%)
                'rejects_produced': 0,  # Scones don't have rejects
                'batch_number': 'SCONES-001',
            },
            {
                'mix': scones_mix,
                'product': scones,
                'expected_packets': 102,
                'actual_packets': 102,  # Perfect match (0%)
                'rejects_produced': 0,
                'batch_number': 'SCONES-002',
            },
        ]
        
        batches_created = 0
        for batch_data in batches_data:
            batch, created = ProductionBatch.objects.get_or_create(
                daily_production=daily_production,
                batch_number=batch_data['batch_number'],
                defaults={
                    'mix': batch_data['mix'],
                    'product': batch_data['product'],
                    'expected_packets': batch_data['expected_packets'],
                    'actual_packets': batch_data['actual_packets'],
                    'rejects_produced': batch_data['rejects_produced'],
                    'created_by': system_user,
                }
            )
            
            if created:
                batches_created += 1
                variance_pct = batch.variance_percentage
                variance_color = '🟢' if abs(variance_pct) < 5 else '🟡'
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ {batch.batch_number}: {batch.actual_packets} packets '
                    f'(variance: {variance_color} {variance_pct:+.1f}%)'
                ))
        
        if batches_created > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Created {batches_created} production batches'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  All batches already exist'
            ))
        
        # 3. Add Indirect Costs
        indirect_costs_data = [
            {
                'cost_type': 'DIESEL',
                'description': 'Diesel for production (generator)',
                'amount': Decimal('1500.00'),
                'receipt_number': 'FUEL-2025-001',
                'vendor': 'Kisumu Petrol Station',
            },
            {
                'cost_type': 'FIREWOOD',
                'description': 'Firewood for ovens',
                'amount': Decimal('800.00'),
                'receipt_number': 'WOOD-2025-001',
                'vendor': 'Local Supplier',
            },
            {
                'cost_type': 'ELECTRICITY',
                'description': 'KPLC electricity bill (production)',
                'amount': Decimal('450.00'),
                'receipt_number': 'KPLC-OCT-2025',
                'vendor': 'KPLC',
            },
            {
                'cost_type': 'FUEL_DISTRIBUTION',
                'description': 'Fuel for distribution vehicles',
                'amount': Decimal('600.00'),
                'receipt_number': 'FUEL-2025-002',
                'vendor': 'Kisumu Petrol Station',
            },
        ]
        
        costs_created = 0
        total_indirect_costs = Decimal('0')
        
        for cost_data in indirect_costs_data:
            cost, created = IndirectCost.objects.get_or_create(
                daily_production=daily_production,
                receipt_number=cost_data['receipt_number'],
                defaults={
                    'cost_type': cost_data['cost_type'],
                    'description': cost_data['description'],
                    'amount': cost_data['amount'],
                    'vendor': cost_data['vendor'],
                }
            )
            
            if created:
                costs_created += 1
                total_indirect_costs += cost.amount
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ {cost.get_cost_type_display()}: KES {cost.amount:,.2f}'
                ))
        
        if costs_created > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Created {costs_created} indirect costs (Total: KES {total_indirect_costs:,.2f})'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  All indirect costs already exist'
            ))
        
        # 4. Update DailyProduction totals
        daily_production.diesel_cost = Decimal('1500.00')
        daily_production.firewood_cost = Decimal('800.00')
        daily_production.electricity_cost = Decimal('450.00')
        daily_production.fuel_distribution_cost = Decimal('600.00')
        daily_production.save()
        
        # 5. Display Production Summary
        self.stdout.write(self.style.WARNING('\n📊 Production Summary:'))
        self.stdout.write(f'  Date: {daily_production.date}')
        self.stdout.write(f'  Opening Stock: Bread {daily_production.bread_opening_stock} | '
                         f'KDF {daily_production.kdf_opening_stock} | '
                         f'Scones {daily_production.scones_opening_stock}')
        
        # Calculate totals
        total_bread = ProductionBatch.objects.filter(
            daily_production=daily_production,
            product=bread
        ).aggregate(total=models.Sum('actual_packets'))['total'] or 0
        
        total_kdf = ProductionBatch.objects.filter(
            daily_production=daily_production,
            product=kdf
        ).aggregate(total=models.Sum('actual_packets'))['total'] or 0
        
        total_scones = ProductionBatch.objects.filter(
            daily_production=daily_production,
            product=scones
        ).aggregate(total=models.Sum('actual_packets'))['total'] or 0
        
        from django.db import models
        
        self.stdout.write(f'  Produced: Bread {total_bread} | KDF {total_kdf} | Scones {total_scones}')
        self.stdout.write(f'  Indirect Costs: KES {total_indirect_costs:,.2f}')
        
        # Calculate P&L
        batches = ProductionBatch.objects.filter(daily_production=daily_production)
        total_cost = sum(b.total_cost for b in batches)
        total_revenue = sum(b.expected_revenue for b in batches)
        total_profit = sum(b.gross_profit for b in batches)
        
        if total_revenue > 0:
            margin = (total_profit / total_revenue) * 100
            self.stdout.write(f'  Total Cost: KES {total_cost:,.2f}')
            self.stdout.write(f'  Expected Revenue: KES {total_revenue:,.2f}')
            self.stdout.write(f'  Gross Profit: KES {total_profit:,.2f} ({margin:.1f}%)')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Production seeding complete!\n'))
