"""
Inventory app signals for automated stock updates
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Purchase, PurchaseItem, StockMovement, CrateStock, CrateMovement


@receiver(pre_save, sender=Purchase)
def capture_previous_status(sender, instance, **kwargs):
    """
    Capture the previous status before saving
    """
    if instance.pk:
        try:
            instance._previous_status = Purchase.objects.get(pk=instance.pk).status
        except Purchase.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Purchase)
def update_inventory_on_receipt(sender, instance, created, **kwargs):
    """
    When a purchase is marked as RECEIVED, update inventory stock
    """
    # Only process if status changed to RECEIVED
    previous_status = getattr(instance, '_previous_status', None)
    
    if instance.status == 'RECEIVED' and previous_status != 'RECEIVED':
        print(f"\n🔄 Processing purchase receipt: {instance.purchase_number}")
        
        # Update stock for all purchase items
        for purchase_item in instance.purchaseitem_set.all():
            item = purchase_item.item
            
            # Calculate converted quantity (purchase unit → recipe unit)
            converted_quantity = purchase_item.quantity * item.conversion_factor
            
            # Capture stock levels for audit trail
            stock_before = item.current_stock
            
            # Update inventory item stock
            item.current_stock += converted_quantity
            item.cost_per_purchase_unit = purchase_item.unit_cost
            item.save()
            
            stock_after = item.current_stock
            
            # Create stock movement record for audit trail
            StockMovement.objects.create(
                item=item,
                movement_type='PURCHASE',
                quantity=converted_quantity,
                unit=item.recipe_unit,
                stock_before=stock_before,
                stock_after=stock_after,
                reference_type='Purchase',
                reference_id=instance.id,
                notes=f"Purchase {instance.purchase_number} from {instance.supplier.name}",
                created_by=instance.updated_by or instance.created_by
            )
            
            print(f"  ✅ Updated {item.name}: {stock_before:.2f} → {stock_after:.2f} {item.recipe_unit}")
        
        print(f"✅ Purchase {instance.purchase_number} received and inventory updated\n")


# ============================================================================
# CRATE TRACKING SIGNALS (Closed Chain for Crates)
# ============================================================================

@receiver(post_save, sender='sales.Dispatch')
def track_crate_dispatch(sender, instance, created, **kwargs):
    """
    Automatically update CrateStock when a Dispatch is created or edited
    Creates CrateMovement audit trail
    """
    # Skip if only expected_revenue is being updated (triggered by DispatchItem saves)
    update_fields = kwargs.get('update_fields')
    if update_fields and set(update_fields) == {'expected_revenue'}:
        return
    
    if not instance.crates_dispatched:
        return
    
    # Get or create CrateStock
    crate_stock = CrateStock.get_instance()
    
    if created:
        # New dispatch - deduct crates
        if instance.crates_dispatched > crate_stock.available_crates:
            # This shouldn't happen due to view validation, but handle it
            print(f"⚠️ Warning: Dispatch #{instance.id} tried to dispatch {instance.crates_dispatched} crates but only {crate_stock.available_crates} available")
            return
        
        crate_stock.available_crates -= instance.crates_dispatched
        crate_stock.dispatched_crates += instance.crates_dispatched
        crate_stock.save()
        
        # Create movement record
        CrateMovement.objects.create(
            movement_type='DISPATCH_OUT',
            quantity=instance.crates_dispatched,
            salesperson_name=instance.salesperson.name,
            dispatch_id=instance.id,
            notes=f"Dispatch to {instance.salesperson.name} on {instance.date}",
            created_by=instance.created_by
        )
        
        print(f"✅ Crate dispatch tracked: {instance.crates_dispatched} crates to {instance.salesperson.name}")
    else:
        # Existing dispatch edited - check if crates changed
        # Get previous crate count from database
        try:
            from apps.sales.models import Dispatch
            old_dispatch = Dispatch.objects.get(pk=instance.pk)
            previous_crates = getattr(instance, '_previous_crates', old_dispatch.crates_dispatched)
            
            if previous_crates != instance.crates_dispatched:
                # Crates changed - adjust stock
                crate_difference = instance.crates_dispatched - previous_crates
                
                if crate_difference > 0:
                    # More crates dispatched
                    if crate_difference > crate_stock.available_crates:
                        print(f"⚠️ Warning: Cannot add {crate_difference} more crates to dispatch #{instance.id}")
                        return
                    
                    crate_stock.available_crates -= crate_difference
                    crate_stock.dispatched_crates += crate_difference
                else:
                    # Fewer crates dispatched (returned to available)
                    crate_stock.available_crates += abs(crate_difference)
                    crate_stock.dispatched_crates -= abs(crate_difference)
                
                crate_stock.save()
                
                # Log adjustment
                CrateMovement.objects.create(
                    movement_type='COUNT',
                    quantity=crate_difference,
                    salesperson_name=instance.salesperson.name,
                    dispatch_id=instance.id,
                    notes=f"Dispatch #{instance.id} crates adjusted from {previous_crates} to {instance.crates_dispatched}",
                    created_by=instance.created_by
                )
                
                print(f"✅ Crate dispatch adjusted: {previous_crates} → {instance.crates_dispatched} for {instance.salesperson.name}")
        except Exception as e:
            print(f"⚠️ Error adjusting crate dispatch: {e}")


@receiver(pre_save, sender='sales.Dispatch')
def capture_previous_crates(sender, instance, **kwargs):
    """
    Capture previous crate count before saving
    Used for edit detection in post_save signal
    """
    if instance.pk:
        try:
            from apps.sales.models import Dispatch
            old_dispatch = Dispatch.objects.get(pk=instance.pk)
            instance._previous_crates = old_dispatch.crates_dispatched
        except:
            instance._previous_crates = 0
    else:
        instance._previous_crates = 0


@receiver(post_save, sender='sales.SalesReturn')
def track_crate_return(sender, instance, created, **kwargs):
    """
    Automatically update CrateStock when a SalesReturn is created
    Returns crates from dispatched back to available
    Creates CrateMovement audit trail
    """
    if not instance.crates_returned:
        return
    
    # Get or create CrateStock
    crate_stock = CrateStock.get_instance()
    
    if created:
        # New return - return crates to available
        if instance.crates_returned > crate_stock.dispatched_crates:
            # This shouldn't happen but handle it
            print(f"⚠️ Warning: Return #{instance.id} tried to return {instance.crates_returned} crates but only {crate_stock.dispatched_crates} dispatched")
            # Still process it but log warning
        
        crate_stock.available_crates += instance.crates_returned
        crate_stock.dispatched_crates -= instance.crates_returned
        crate_stock.save()
        
        # Create movement record
        CrateMovement.objects.create(
            movement_type='RETURN_IN',
            quantity=instance.crates_returned,
            salesperson_name=instance.dispatch.salesperson.name,
            dispatch_id=instance.dispatch.id,
            notes=f"Return from {instance.dispatch.salesperson.name} on {instance.return_date}. Deficit: {instance.crates_deficit} crates",
            created_by=instance.created_by
        )
        
        print(f"✅ Crate return tracked: {instance.crates_returned} crates from {instance.dispatch.salesperson.name} (Deficit: {instance.crates_deficit})")
    else:
        # Existing return edited - check if crates changed
        try:
            from apps.sales.models import SalesReturn
            old_return = SalesReturn.objects.get(pk=instance.pk)
            previous_crates = getattr(instance, '_previous_crates_returned', old_return.crates_returned)
            
            if previous_crates != instance.crates_returned:
                # Crates changed - adjust stock
                crate_difference = instance.crates_returned - previous_crates
                
                if crate_difference > 0:
                    # More crates returned
                    crate_stock.available_crates += crate_difference
                    crate_stock.dispatched_crates -= crate_difference
                else:
                    # Fewer crates returned
                    crate_stock.available_crates -= abs(crate_difference)
                    crate_stock.dispatched_crates += abs(crate_difference)
                
                crate_stock.save()
                
                # Log adjustment
                CrateMovement.objects.create(
                    movement_type='COUNT',
                    quantity=crate_difference,
                    salesperson_name=instance.dispatch.salesperson.name,
                    dispatch_id=instance.dispatch.id,
                    notes=f"Return #{instance.id} crates adjusted from {previous_crates} to {instance.crates_returned}",
                    created_by=instance.updated_by
                )
                
                print(f"✅ Crate return adjusted: {previous_crates} → {instance.crates_returned} for {instance.dispatch.salesperson.name}")
        except Exception as e:
            print(f"⚠️ Error adjusting crate return: {e}")


@receiver(pre_save, sender='sales.SalesReturn')
def capture_previous_crates_returned(sender, instance, **kwargs):
    """
    Capture previous crate return count before saving
    Used for edit detection in post_save signal
    """
    if instance.pk:
        try:
            from apps.sales.models import SalesReturn
            old_return = SalesReturn.objects.get(pk=instance.pk)
            instance._previous_crates_returned = old_return.crates_returned
        except:
            instance._previous_crates_returned = 0
    else:
        instance._previous_crates_returned = 0
