"""
Seed sample sales data for testing
Creates Salesperson, Dispatch, DispatchItem, SalesReturn, and SalesReturnItem records
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, time

from apps.sales.models import (
    Salesperson,
    Dispatch,
    DispatchItem,
    SalesReturn,
    SalesReturnItem,
    DailySales,
)
from apps.products.models import Product
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed sample sales data (idempotent - safe to run multiple times)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🌱 Seeding Sales Data...\n'))
        
        # Get or create system user
        system_user, _ = User.objects.get_or_create(
            email='system@chesanto.com',
            defaults={
                'username': 'system',
                'role': 'SUPERADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Get products
        try:
            bread = Product.objects.get(name='Bread')
            kdf = Product.objects.get(name='KDF')
            scones = Product.objects.get(name='Scones')
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                '❌ Products not found. Run seed_products first.'
            ))
            return
        
        # 1. Create Salespeople
        salespeople_data = [
            {
                'name': 'John Doe',
                'recipient_type': 'SALESMAN',
                'phone': '+254712345678',
                'email': 'john.doe@chesanto.com',
                'location': 'Kisumu Town',
            },
            {
                'name': 'Mary Okoth',
                'recipient_type': 'SALESMAN',
                'phone': '+254723456789',
                'email': 'mary.okoth@chesanto.com',
                'location': 'Kondele',
            },
            {
                'name': 'St. Mary School',
                'recipient_type': 'SCHOOL',
                'phone': '+254734567890',
                'email': 'procurement@stmary.ac.ke',
                'location': 'Milimani',
            },
            {
                'name': 'Okiya Depot',
                'recipient_type': 'DEPOT',
                'phone': '+254745678901',
                'email': 'okiya.depot@example.com',
                'location': 'Okiya',
            },
        ]
        
        salespeople_created = 0
        salespeople = {}
        
        for sp_data in salespeople_data:
            salesperson, created = Salesperson.objects.get_or_create(
                name=sp_data['name'],
                defaults={
                    'recipient_type': sp_data['recipient_type'],
                    'phone': sp_data['phone'],
                    'email': sp_data['email'],
                    'location': sp_data['location'],
                    'commission_per_bread': Decimal('5.00'),
                    'commission_per_kdf': Decimal('5.00'),
                    'commission_per_scones': Decimal('5.00'),
                    'sales_target': Decimal('35000.00'),
                    'bonus_commission_rate': Decimal('7.00'),
                    'created_by': system_user,
                }
            )
            
            salespeople[sp_data['name']] = salesperson
            
            if created:
                salespeople_created += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ {salesperson.name} ({salesperson.get_recipient_type_display()}) - {salesperson.location}'
                ))
        
        if salespeople_created > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Created {salespeople_created} salespeople'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  All salespeople already exist'
            ))
        
        # 2. Create Dispatches with Items
        today = date.today()
        
        dispatches_data = [
            {
                'salesperson': salespeople['John Doe'],
                'crates': 3,
                'items': [
                    {'product': bread, 'quantity': 50},
                    {'product': kdf, 'quantity': 30},
                    {'product': scones, 'quantity': 20},
                ],
            },
            {
                'salesperson': salespeople['Mary Okoth'],
                'crates': 4,
                'items': [
                    {'product': bread, 'quantity': 60},
                    {'product': kdf, 'quantity': 40},
                    {'product': scones, 'quantity': 30},
                ],
            },
            {
                'salesperson': salespeople['St. Mary School'],
                'crates': 5,
                'items': [
                    {'product': bread, 'quantity': 80},
                    {'product': kdf, 'quantity': 50},
                    {'product': scones, 'quantity': 30},
                ],
            },
            {
                'salesperson': salespeople['Okiya Depot'],
                'crates': 2,
                'items': [
                    {'product': bread, 'quantity': 10},
                    {'product': kdf, 'quantity': 30},
                    {'product': scones, 'quantity': 20},
                ],
            },
        ]
        
        dispatches_created = 0
        dispatches = {}
        
        for dispatch_data in dispatches_data:
            dispatch, created = Dispatch.objects.get_or_create(
                date=today,
                salesperson=dispatch_data['salesperson'],
                defaults={
                    'crates_dispatched': dispatch_data['crates'],
                    'created_by': system_user,
                }
            )
            
            dispatches[dispatch_data['salesperson'].name] = dispatch
            
            if created:
                dispatches_created += 1
                
                # Create dispatch items
                for item_data in dispatch_data['items']:
                    DispatchItem.objects.create(
                        dispatch=dispatch,
                        product=item_data['product'],
                        quantity=item_data['quantity'],
                    )
                
                items_str = ', '.join([
                    f"{item['quantity']} {item['product'].name}"
                    for item in dispatch_data['items']
                ])
                
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Dispatch to {dispatch.salesperson.name}: {items_str} '
                    f'({dispatch.crates_dispatched} crates, KES {dispatch.expected_revenue:,.2f})'
                ))
        
        if dispatches_created > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Created {dispatches_created} dispatches'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  All dispatches already exist'
            ))
        
        # 3. Create Sales Returns (simulate different scenarios)
        returns_data = [
            {
                'dispatch': dispatches['John Doe'],
                'crates_returned': 3,
                'cash_returned': Decimal('9550.00'),  # Full payment
                'returns': [
                    {'product': bread, 'returned': 5, 'damaged': 2},
                    {'product': kdf, 'returned': 3, 'damaged': 1},
                    {'product': scones, 'returned': 2, 'damaged': 0},
                ],
                'deficit_reason': '',
                'scenario': 'Full Payment',
            },
            {
                'dispatch': dispatches['Mary Okoth'],
                'crates_returned': 4,
                'cash_returned': Decimal('12000.00'),  # KES 200 deficit
                'returns': [
                    {'product': bread, 'returned': 8, 'damaged': 1},
                    {'product': kdf, 'returned': 5, 'damaged': 2},
                    {'product': scones, 'returned': 4, 'damaged': 1},
                ],
                'deficit_reason': 'Expired stock (2 loaves past sell-by date)',
                'scenario': 'Small Deficit',
            },
            {
                'dispatch': dispatches['St. Mary School'],
                'crates_returned': 5,
                'cash_returned': Decimal('15600.00'),  # Full payment
                'returns': [
                    {'product': bread, 'returned': 0, 'damaged': 0},
                    {'product': kdf, 'returned': 0, 'damaged': 0},
                    {'product': scones, 'returned': 0, 'damaged': 0},
                ],
                'deficit_reason': '',
                'scenario': 'Full Payment (School)',
            },
            {
                'dispatch': dispatches['Okiya Depot'],
                'crates_returned': 1,  # 1 crate deficit
                'cash_returned': Decimal('2500.00'),  # KES 600 deficit (CEO alert)
                'returns': [
                    {'product': bread, 'returned': 2, 'damaged': 1},
                    {'product': kdf, 'returned': 10, 'damaged': 5},
                    {'product': scones, 'returned': 8, 'damaged': 2},
                ],
                'deficit_reason': 'Damaged goods in transit (poor road conditions)',
                'scenario': 'Large Deficit + Crate Deficit',
            },
        ]
        
        returns_created = 0
        
        for return_data in returns_data:
            # Check if return already exists
            if hasattr(return_data['dispatch'], 'sales_return'):
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Return for {return_data["dispatch"].salesperson.name} already exists'
                ))
                continue
            
            # Create SalesReturn
            sales_return = SalesReturn.objects.create(
                dispatch=return_data['dispatch'],
                return_date=today,
                return_time=time(17, 30),  # 5:30 PM
                cash_returned=return_data['cash_returned'],
                sales_reconciled=True,  # Mark as reconciled since we're seeding complete returns
                crates_returned=True,   # Mark as crates returned since we're seeding complete returns
                created_by=system_user,
            )
            
            # Create SalesReturnItems
            for item_data in return_data['returns']:
                # Get dispatched quantity
                dispatch_item = DispatchItem.objects.get(
                    dispatch=return_data['dispatch'],
                    product=item_data['product']
                )
                
                SalesReturnItem.objects.create(
                    sales_return=sales_return,
                    product=item_data['product'],
                    units_dispatched=dispatch_item.quantity,
                    units_returned=item_data['returned'],
                    units_damaged=item_data['damaged'],
                    crates_returned=0,  # Will be set during crate return phase
                )
            
            returns_created += 1
            
            # Calculate revenue deficit (expected - actual)
            revenue_deficit = sales_return.dispatch.expected_revenue - sales_return.cash_returned
            
            # Calculate crates deficit (dispatched - returned)
            total_crates_returned = sum(item.crates_returned for item in sales_return.salesreturnitem_set.all())
            crates_deficit = sales_return.dispatch.crates_dispatched - total_crates_returned
            
            # Display return summary
            deficit_icon = '✅' if revenue_deficit == 0 else '⚠️'
            if revenue_deficit > 500:
                deficit_icon = '🚨'
            
            crate_deficit_str = ''
            if crates_deficit > 0:
                crate_deficit_str = f', {crates_deficit} crates deficit'
            
            self.stdout.write(self.style.SUCCESS(
                f'  {deficit_icon} Return from {sales_return.dispatch.salesperson.name}: '
                f'KES {sales_return.cash_returned:,.2f} '
                f'(Deficit: KES {revenue_deficit:,.2f}{crate_deficit_str})'
            ))
            
            if sales_return.total_commission > 0:
                self.stdout.write(
                    f'     Commission: KES {sales_return.total_commission:,.2f} '
                    f'(Per-unit: KES {sales_return.per_unit_commission:,.2f}, '
                    f'Bonus: KES {sales_return.bonus_commission:,.2f})'
                )
        
        if returns_created > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Created {returns_created} sales returns'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  All sales returns already exist'
            ))
        
        # 4. Display Daily Sales Summary
        daily_sales, _ = DailySales.objects.get_or_create(date=today)
        
        self.stdout.write(self.style.WARNING('\n📊 Daily Sales Summary:'))
        self.stdout.write(f'  Date: {daily_sales.date}')
        self.stdout.write(f'  Expected Revenue: KES {daily_sales.total_expected_revenue:,.2f}')
        self.stdout.write(f'  Actual Revenue: KES {daily_sales.total_actual_revenue:,.2f}')
        self.stdout.write(f'  Revenue Deficit: KES {daily_sales.total_revenue_deficit:,.2f}')
        self.stdout.write(f'  Total Commissions: KES {daily_sales.total_commissions:,.2f}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sales seeding complete!\n'))
