"""
Production App Signals
Auto-deduct ingredients and packaging from inventory when ProductionBatch is created/updated
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from decimal import Decimal
from .models import ProductionBatch, DailyProduction
from apps.inventory.models import InventoryItem, StockMovement


@receiver(post_save, sender=ProductionBatch)
def deduct_ingredients_from_inventory(sender, instance, created, **kwargs):
    """
    Auto-deduct ingredients from inventory when production batch is saved
    Creates StockMovement records for audit trail
    """
    # Skip if batch is being updated with finalized flag (no re-deduction)
    if not created and instance.is_finalized:
        return
    
    # Skip if this is an update and not first save (prevent double deduction)
    if not created:
        # Check if we already deducted (has stock movements)
        existing_movements = StockMovement.objects.filter(
            reference_type='PRODUCTION',
            reference_id=instance.id
        )
        if existing_movements.exists():
            return
    
    # Get all mix ingredients
    mix_ingredients = instance.mix.mixingredient_set.all()
    
    for mix_ingredient in mix_ingredients:
        ingredient = mix_ingredient.ingredient
        
        # Skip if ingredient not linked to inventory
        if not ingredient.inventory_item:
            continue
        
        inventory_item = ingredient.inventory_item
        
        # Calculate quantity to deduct (from recipe units)
        quantity_to_deduct = mix_ingredient.quantity
        
        # Convert units if necessary (match inventory recipe_unit)
        if mix_ingredient.unit != inventory_item.recipe_unit:
            # Handle conversions (kg↔g, L↔mL)
            if mix_ingredient.unit == 'kg' and inventory_item.recipe_unit == 'g':
                quantity_to_deduct = quantity_to_deduct * 1000
            elif mix_ingredient.unit == 'g' and inventory_item.recipe_unit == 'kg':
                quantity_to_deduct = quantity_to_deduct / 1000
            elif mix_ingredient.unit == 'l' and inventory_item.recipe_unit == 'ml':
                quantity_to_deduct = quantity_to_deduct * 1000
            elif mix_ingredient.unit == 'ml' and inventory_item.recipe_unit == 'l':
                quantity_to_deduct = quantity_to_deduct / 1000
        
        # Get stock before deduction
        stock_before = inventory_item.current_stock
        
        # Deduct from inventory
        inventory_item.current_stock -= Decimal(str(quantity_to_deduct))
        inventory_item.save()
        
        # Get stock after deduction
        stock_after = inventory_item.current_stock
        
        # Create stock movement for audit trail
        StockMovement.objects.create(
            item=inventory_item,
            movement_type='PRODUCTION',
            quantity=-Decimal(str(quantity_to_deduct)),  # Negative for deduction
            unit=inventory_item.recipe_unit,
            reference_type='PRODUCTION',
            reference_id=instance.id,
            notes=f"Deducted for {instance.mix.product.name} Batch #{instance.batch_number}",
            stock_before=stock_before,
            stock_after=stock_after,
            created_by=instance.created_by
        )
    
    # Deduct packaging bags
    deduct_packaging_bags(instance)


def deduct_packaging_bags(batch):
    """
    Auto-deduct packaging bags from inventory
    Bread/KDF/Scones: 1 bag per unit
    """
    try:
        # Find packaging bags in inventory
        packaging_item = None
        
        # Try to find product-specific packaging
        product_name = batch.mix.product.name
        try:
            packaging_item = InventoryItem.objects.get(
                name=f"Packaging Bags ({product_name})"
            )
        except InventoryItem.DoesNotExist:
            # Try generic packaging
            try:
                packaging_item = InventoryItem.objects.get(
                    name__icontains="packaging bag"
                )
            except InventoryItem.DoesNotExist:
                # No packaging item found - skip
                return
        
        if packaging_item:
            # Calculate total units (including rejects)
            total_units = batch.actual_packets + batch.rejects_produced
            
            # Get stock before deduction
            stock_before = packaging_item.current_stock
            
            # Deduct bags (1 bag per unit)
            packaging_item.current_stock -= Decimal(str(total_units))
            packaging_item.save()
            
            # Get stock after deduction
            stock_after = packaging_item.current_stock
            
            # Create stock movement
            StockMovement.objects.create(
                item=packaging_item,
                movement_type='PRODUCTION',
                quantity=-Decimal(str(total_units)),
                unit=packaging_item.recipe_unit,
                reference_type='PRODUCTION',
                reference_id=batch.id,
                notes=f"Packaging for {batch.mix.product.name} Batch #{batch.batch_number} ({total_units} bags)",
                stock_before=stock_before,
                stock_after=stock_after,
                created_by=batch.created_by
            )
    except Exception as e:
        # Log error but don't fail the batch save
        print(f"Warning: Could not deduct packaging bags: {str(e)}")


@receiver(post_save, sender=ProductionBatch)
def check_low_stock_alerts(sender, instance, created, **kwargs):
    """
    Check for low stock after production deduction
    Trigger alerts if any ingredient < reorder_level
    """
    if not created:
        return
    
    # Get all ingredients used in this batch
    mix_ingredients = instance.mix.mixingredient_set.all()
    
    for mix_ingredient in mix_ingredients:
        if mix_ingredient.ingredient.inventory_item:
            inventory_item = mix_ingredient.ingredient.inventory_item
            
            # Check if below reorder level
            if inventory_item.current_stock < inventory_item.reorder_level:
                inventory_item.low_stock_alert = True
                inventory_item.save()
                
                # TODO: Send email/SMS alert
                # This will be implemented in Phase 3 (Communications)
                print(f"🚨 LOW STOCK ALERT: {inventory_item.name} ({inventory_item.current_stock} {inventory_item.recipe_unit} remaining)")


@receiver(post_save, sender=DailyProduction)
def allocate_indirect_costs_to_batches(sender, instance, created, **kwargs):
    """
    When DailyProduction indirect costs are updated,
    reallocate to all batches proportionally
    """
    if created:
        return
    
    # Only run if update_fields is not specified (prevents recursion)
    update_fields = kwargs.get('update_fields')
    if update_fields is not None:
        return
    
    # Recalculate for all batches today
    for batch in instance.batches.all():
        batch.allocate_indirect_costs()
        # Use update_fields to prevent recursion
        batch.save(update_fields=[
            'allocated_indirect_cost', 
            'total_cost', 
            'cost_per_packet',
            'expected_revenue',
            'gross_profit',
            'gross_margin_percentage'
        ])


@receiver(pre_save, sender=DailyProduction)
def set_next_day_opening_stock(sender, instance, **kwargs):
    """
    When books close (is_closed=True),
    set next day's opening stock to this day's closing stock
    """
    if not instance.is_closed:
        return
    
    # Check if next day exists
    from datetime import timedelta
    next_date = instance.date + timedelta(days=1)
    
    try:
        next_day = DailyProduction.objects.get(date=next_date)
        
        # Update next day's opening stock
        next_day.opening_bread_stock = instance.closing_bread_stock
        next_day.opening_kdf_stock = instance.closing_kdf_stock
        next_day.opening_scones_stock = instance.closing_scones_stock
        next_day.save()
    except DailyProduction.DoesNotExist:
        # Next day not created yet - will be set when created
        pass
