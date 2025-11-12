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
# CRATE TRACKING SIGNALS - DISABLED
# Sales app removed for rebuild
# ============================================================================

# All sales-related signals have been removed
# They will be reimplemented when sales app is rebuilt with proper architecture

