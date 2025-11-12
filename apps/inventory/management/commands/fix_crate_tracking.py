"""
Management command to fix crate tracking
Ensures CrateStock matches actual dispatches and returns
Creates missing CrateMovement audit records
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.inventory.models import CrateStock, CrateMovement
from apps.sales.models import Dispatch, SalesReturn


class Command(BaseCommand):
    help = 'Fix crate tracking by recalculating from dispatch/return data'
    
    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("🔧 CRATE TRACKING FIX"))
        self.stdout.write("="*70 + "\n")
        
        # Get or create CrateStock
        crate_stock = CrateStock.get_instance()
        self.stdout.write(f"📦 Current CrateStock:")
        self.stdout.write(f"   Total: {crate_stock.total_crates}")
        self.stdout.write(f"   Available: {crate_stock.available_crates}")
        self.stdout.write(f"   Dispatched: {crate_stock.dispatched_crates}")
        self.stdout.write(f"   Damaged: {crate_stock.damaged_crates}\n")
        
        # Calculate what SHOULD be based on actual dispatches/returns
        total_dispatched = Dispatch.objects.aggregate(
            total=Sum('crates_dispatched')
        )['total'] or 0
        
        total_returned = SalesReturn.objects.aggregate(
            total=Sum('crates_returned')
        )['total'] or 0
        
        # Currently dispatched = total dispatched - total returned
        expected_dispatched = total_dispatched - total_returned
        expected_available = crate_stock.total_crates - expected_dispatched - crate_stock.damaged_crates
        
        self.stdout.write(f"📊 Calculated from Sales Data:")
        self.stdout.write(f"   Total Dispatched: {total_dispatched} crates")
        self.stdout.write(f"   Total Returned: {total_returned} crates")
        self.stdout.write(f"   Expected Currently Dispatched: {expected_dispatched} crates")
        self.stdout.write(f"   Expected Available: {expected_available} crates\n")
        
        # Check if correction needed
        if (crate_stock.dispatched_crates == expected_dispatched and 
            crate_stock.available_crates == expected_available):
            self.stdout.write(self.style.SUCCESS("✅ CrateStock is already correct!\n"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  CrateStock needs correction:"))
            self.stdout.write(f"   Dispatched: {crate_stock.dispatched_crates} → {expected_dispatched}")
            self.stdout.write(f"   Available: {crate_stock.available_crates} → {expected_available}\n")
            
            # Update CrateStock
            crate_stock.dispatched_crates = expected_dispatched
            crate_stock.available_crates = expected_available
            crate_stock.save()
            
            self.stdout.write(self.style.SUCCESS("✅ CrateStock corrected!\n"))
        
        # Check CrateMovement records
        self.stdout.write("🔍 Checking CrateMovement audit trail...\n")
        
        # Get all dispatches and check if they have movement records
        dispatches = Dispatch.objects.all().order_by('date')
        missing_dispatch_movements = 0
        
        for dispatch in dispatches:
            movement = CrateMovement.objects.filter(
                movement_type='DISPATCH_OUT',
                dispatch_id=dispatch.id
            ).first()
            
            if not movement and dispatch.crates_dispatched > 0:
                # Create missing movement record
                CrateMovement.objects.create(
                    movement_type='DISPATCH_OUT',
                    quantity=dispatch.crates_dispatched,
                    salesperson_name=dispatch.salesperson.name,
                    dispatch_id=dispatch.id,
                    notes=f"Backfilled: Dispatch to {dispatch.salesperson.name} on {dispatch.date}",
                    created_by=dispatch.created_by
                )
                missing_dispatch_movements += 1
                self.stdout.write(
                    f"   ✅ Created movement: Dispatch #{dispatch.id} - "
                    f"{dispatch.crates_dispatched} crates to {dispatch.salesperson.name}"
                )
        
        # Get all returns and check if they have movement records
        returns = SalesReturn.objects.all().order_by('return_date')
        missing_return_movements = 0
        
        for sales_return in returns:
            movement = CrateMovement.objects.filter(
                movement_type='RETURN_IN',
                dispatch_id=sales_return.dispatch.id
            ).first()
            
            if not movement and sales_return.crates_returned:
                # Calculate total crates returned from all items
                total_crates_returned = sum(item.crates_returned for item in sales_return.salesreturnitem_set.all())
                crates_deficit = sales_return.dispatch.crates_dispatched - total_crates_returned
                
                # Create missing movement record
                CrateMovement.objects.create(
                    movement_type='RETURN_IN',
                    quantity=total_crates_returned,
                    salesperson_name=sales_return.dispatch.salesperson.name,
                    dispatch_id=sales_return.dispatch.id,
                    notes=f"Backfilled: Return from {sales_return.dispatch.salesperson.name} on {sales_return.return_date}. Deficit: {crates_deficit}",
                    created_by=sales_return.created_by
                )
                missing_return_movements += 1
                self.stdout.write(
                    f"   ✅ Created movement: Return #{sales_return.id} - "
                    f"{total_crates_returned} crates from {sales_return.dispatch.salesperson.name}"
                )
        
        self.stdout.write(f"\n📋 Summary:")
        self.stdout.write(f"   Total Dispatches: {dispatches.count()}")
        self.stdout.write(f"   Missing Dispatch Movements: {missing_dispatch_movements}")
        self.stdout.write(f"   Total Returns: {returns.count()}")
        self.stdout.write(f"   Missing Return Movements: {missing_return_movements}")
        
        total_movements = CrateMovement.objects.count()
        self.stdout.write(f"   Total CrateMovement Records: {total_movements}\n")
        
        if missing_dispatch_movements == 0 and missing_return_movements == 0:
            self.stdout.write(self.style.SUCCESS("✅ All audit records are complete!\n"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Created {missing_dispatch_movements + missing_return_movements} missing audit records!\n"))
        
        # Final verification
        crate_stock.refresh_from_db()
        self.stdout.write("📦 Final CrateStock:")
        self.stdout.write(f"   Total: {crate_stock.total_crates}")
        self.stdout.write(f"   Available: {crate_stock.available_crates}")
        self.stdout.write(f"   Dispatched: {crate_stock.dispatched_crates}")
        self.stdout.write(f"   Damaged: {crate_stock.damaged_crates}\n")
        
        self.stdout.write(self.style.SUCCESS("="*70))
        self.stdout.write(self.style.SUCCESS("🎉 CRATE TRACKING FIX COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("="*70 + "\n"))
