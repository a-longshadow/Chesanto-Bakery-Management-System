"""
Management command to fix Production→Sales chain
Backfill DailyProduction.dispatched and returned quantities from existing sales data
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.production.models import DailyProduction
from apps.sales.models import DispatchItem, SalesReturnItem
from apps.products.models import Product


class Command(BaseCommand):
    help = 'Fix DailyProduction by backfilling dispatch/return quantities from sales data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔧 Starting Production→Sales Chain Fix\n'))
        
        # Get all products
        try:
            bread = Product.objects.get(name='Bread')
            kdf = Product.objects.get(name='KDF')
            scones = Product.objects.get(name='Scones')
        except Product.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'❌ Product not found: {e}'))
            return
        
        # Get all DailyProduction records
        daily_productions = DailyProduction.objects.all().order_by('date')
        
        fixed_count = 0
        error_count = 0
        
        for dp in daily_productions:
            try:
                # Calculate dispatched quantities from DispatchItem
                bread_dispatched = DispatchItem.objects.filter(
                    dispatch__date=dp.date,
                    product=bread
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                kdf_dispatched = DispatchItem.objects.filter(
                    dispatch__date=dp.date,
                    product=kdf
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                scones_dispatched = DispatchItem.objects.filter(
                    dispatch__date=dp.date,
                    product=scones
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # Calculate returned quantities from SalesReturnItem
                # Returns are linked to dispatch date (where products came from)
                bread_returned = SalesReturnItem.objects.filter(
                    sales_return__dispatch__date=dp.date,
                    product=bread
                ).aggregate(total=Sum('units_returned'))['total'] or 0
                
                kdf_returned = SalesReturnItem.objects.filter(
                    sales_return__dispatch__date=dp.date,
                    product=kdf
                ).aggregate(total=Sum('units_returned'))['total'] or 0
                
                scones_returned = SalesReturnItem.objects.filter(
                    sales_return__dispatch__date=dp.date,
                    product=scones
                ).aggregate(total=Sum('units_returned'))['total'] or 0
                
                # Check if update needed
                needs_update = (
                    dp.bread_dispatched != bread_dispatched or
                    dp.kdf_dispatched != kdf_dispatched or
                    dp.scones_dispatched != scones_dispatched or
                    dp.bread_returned != bread_returned or
                    dp.kdf_returned != kdf_returned or
                    dp.scones_returned != scones_returned
                )
                
                if needs_update:
                    # Store old values for comparison
                    old_values = (
                        f"Bread: {dp.bread_dispatched}/{dp.bread_returned}, "
                        f"KDF: {dp.kdf_dispatched}/{dp.kdf_returned}, "
                        f"Scones: {dp.scones_dispatched}/{dp.scones_returned}"
                    )
                    
                    # Update fields
                    dp.bread_dispatched = bread_dispatched
                    dp.kdf_dispatched = kdf_dispatched
                    dp.scones_dispatched = scones_dispatched
                    dp.bread_returned = bread_returned
                    dp.kdf_returned = kdf_returned
                    dp.scones_returned = scones_returned
                    
                    # Save (this will recalculate closing stock)
                    dp.save(update_fields=[
                        'bread_dispatched', 'kdf_dispatched', 'scones_dispatched',
                        'bread_returned', 'kdf_returned', 'scones_returned',
                        'closing_bread_stock', 'closing_kdf_stock', 'closing_scones_stock',
                        'updated_at'
                    ])
                    
                    new_values = (
                        f"Bread: {dp.bread_dispatched}/{dp.bread_returned}, "
                        f"KDF: {dp.kdf_dispatched}/{dp.kdf_returned}, "
                        f"Scones: {dp.scones_dispatched}/{dp.scones_returned}"
                    )
                    
                    self.stdout.write(
                        self.style.WARNING(f'\n📅 {dp.date}:') +
                        f'\n   Old (dispatched/returned): {old_values}' +
                        f'\n   New (dispatched/returned): {new_values}' +
                        self.style.SUCCESS(f'\n   Closing Stock: Bread={dp.closing_bread_stock}, KDF={dp.closing_kdf_stock}, Scones={dp.closing_scones_stock}')
                    )
                    
                    fixed_count += 1
                else:
                    self.stdout.write(self.style.SUCCESS(f'✅ {dp.date}: Already correct'))
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {dp.date}: Error - {e}'))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n\n📊 Summary:'))
        self.stdout.write(f'   Total records: {daily_productions.count()}')
        self.stdout.write(self.style.SUCCESS(f'   Fixed: {fixed_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'   Errors: {error_count}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Production→Sales chain fix complete!\n'))
