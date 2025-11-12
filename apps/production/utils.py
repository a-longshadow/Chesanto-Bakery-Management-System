"""
Transaction-safe utility functions for Production app.
These functions provide the interface layer for Sales and other apps.
"""
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
import logging

logger = logging.getLogger(__name__)


@transaction.atomic
def create_production_batch_atomic(
    daily_production,
    mix,
    actual_packets,
    rejects_produced=0,
    batch_number=None,
    user=None
):
    """
    Create a production batch with atomic ingredient deduction.
    
    This replaces the signal-driven ingredient deduction.
    Either ALL ingredients are deducted OR nothing happens (rollback).
    
    Args:
        daily_production: DailyProduction instance
        mix: Mix instance
        actual_packets: Number of packets produced
        rejects_produced: Number of rejects (Bread only)
        batch_number: Batch number (auto-calculated if None)
        user: User performing the action
    
    Returns:
        (batch, error_message)
        - batch: ProductionBatch instance if successful, None if error
        - error_message: str if error, None if successful
    """
    from .models import ProductionBatch
    from apps.products.models import MixIngredient
    from apps.inventory.models import InventoryItem, StockMovement
    
    # Step 1: Validate all ingredients BEFORE any changes
    ingredient_requirements = []
    mix_ingredients = MixIngredient.objects.filter(mix=mix).select_related('ingredient')
    
    if not mix_ingredients.exists():
        return None, f"Mix '{mix.name}' has no ingredients configured"
    
    for mix_ingredient in mix_ingredients:
        # Calculate required quantity based on actual output
        # Formula: (ingredient_qty_per_mix / expected_packets) * actual_packets
        qty_per_packet = mix_ingredient.quantity / mix.expected_packets
        required_qty = qty_per_packet * actual_packets
        
        # Get inventory item
        if not mix_ingredient.ingredient.inventory_item:
            return None, f"Ingredient '{mix_ingredient.ingredient.name}' not linked to inventory"
        
        try:
            # Lock inventory item to prevent race conditions
            inventory_item = InventoryItem.objects.select_for_update().get(
                id=mix_ingredient.ingredient.inventory_item.id
            )
        except InventoryItem.DoesNotExist:
            return None, f"Inventory item not found for {mix_ingredient.ingredient.name}"
        
        # ❌ BLOCK if insufficient stock (negative stock prevention)
        if inventory_item.current_stock < required_qty:
            return None, (
                f"❌ INSUFFICIENT STOCK: {mix_ingredient.ingredient.name}\n"
                f"   Required: {required_qty:.3f} {inventory_item.recipe_unit}\n"
                f"   Available: {inventory_item.current_stock:.3f} {inventory_item.recipe_unit}\n"
                f"   Deficit: {required_qty - inventory_item.current_stock:.3f} {inventory_item.recipe_unit}\n"
                f"   🛑 CANNOT PROCEED - Add inventory first"
            )
        
        ingredient_requirements.append({
            'inventory_item': inventory_item,
            'ingredient': mix_ingredient.ingredient,
            'quantity': required_qty,
            'unit': inventory_item.recipe_unit
        })
    
    # Step 2: Auto-calculate batch number if not provided
    if batch_number is None:
        existing_batches = ProductionBatch.objects.filter(
            daily_production=daily_production
        ).count()
        batch_number = existing_batches + 1
    
    # Step 3: Create the batch (validation OK, now commit)
    batch = ProductionBatch(
        daily_production=daily_production,
        mix=mix,
        batch_number=batch_number,
        actual_packets=actual_packets,
        rejects_produced=rejects_produced,
        created_by=user
    )
    
    # Prepare calculated fields
    error = batch.prepare_for_save()
    if error:
        return None, f"Batch calculation error: {error}"
    
    batch.save()
    
    # Step 4: Deduct ingredients (all locked, all in same transaction)
    for req in ingredient_requirements:
        inventory_item = req['inventory_item']
        quantity = req['quantity']
        
        # Deduct from inventory
        inventory_item.current_stock -= quantity
        
        # ✅ SAFETY CHECK (should never happen, but paranoid)
        if inventory_item.current_stock < 0:
            raise ValidationError(
                f"❌ INTEGRITY ERROR: {inventory_item.name} would go negative!\n"
                f"   This should never happen. Rolling back entire transaction."
            )
        
        inventory_item.save()
        
        # Create audit trail
        StockMovement.objects.create(
            inventory_item=inventory_item,
            movement_type='PRODUCTION_USE',
            quantity=quantity,
            reference_id=batch.id,
            reference_type='ProductionBatch',
            notes=f"Used in {mix.name} batch #{batch_number} (Qty: {actual_packets})",
            created_by=user
        )
    
    # Step 5: Update daily production totals
    daily_production.refresh_from_db()
    
    # Map mix product to field name
    product_name = mix.product.name.lower()
    
    if product_name == 'bread':
        # Include rejects in total bread produced
        daily_production.bread_produced = (
            daily_production.bread_produced + actual_packets + rejects_produced
        )
    elif product_name == 'kdf':
        daily_production.kdf_produced = daily_production.kdf_produced + actual_packets
    elif product_name == 'scones':
        daily_production.scones_produced = daily_production.scones_produced + actual_packets
    else:
        logger.warning(f"Unknown product type: {product_name}")
    
    daily_production.updated_by = user
    daily_production.save()
    
    # Step 6: Check for low stock alerts
    check_low_stock_alerts(mix, user)
    
    return batch, None


def get_available_stock(product_field, up_to_date=None):
    """
    SAFE query function for Sales to use.
    Calculate available stock without side effects.
    
    Args:
        product_field: 'bread', 'kdf', or 'scones'
        up_to_date: Calculate up to this date (default: today)
    
    Returns:
        int: Available quantity
    """
    from .models import DailyProduction
    
    if up_to_date is None:
        up_to_date = date.today()
    
    # Total produced up to date
    produced = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_produced')
    )['total'] or 0
    
    # Total damaged up to date (reduces available stock)
    # Note: No damaged field yet, will add when needed
    damaged = 0
    
    # Total dispatched up to date (from Sales app - will implement after Sales is built)
    # For now, read from DailyProduction.{product}_dispatched
    dispatched = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_dispatched')
    )['total'] or 0
    
    # Total returned up to date
    returned = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_returned')
    )['total'] or 0
    
    # Available = Produced - Damaged - Dispatched + Returned
    available = produced - damaged - dispatched + returned
    
    return max(0, available)  # Never return negative


@transaction.atomic
def add_returned_products(return_date, bread=0, kdf=0, scones=0, user=None):
    """
    SAFE write function for Sales returns.
    This is the ONLY place Sales should write to Production.
    
    Args:
        return_date: Date of the return
        bread: Quantity of bread returned
        kdf: Quantity of KDF returned
        scones: Quantity of scones returned
        user: User performing the return
    
    Returns:
        (daily_production, error_message)
    """
    from .models import DailyProduction
    
    # Validate inputs
    if bread < 0 or kdf < 0 or scones < 0:
        return None, "❌ Return quantities cannot be negative"
    
    if bread == 0 and kdf == 0 and scones == 0:
        return None, "❌ At least one product must be returned"
    
    # Get or create DailyProduction for return date
    daily_prod, created = DailyProduction.objects.select_for_update().get_or_create(
        date=return_date,
        defaults={
            'created_by': user,
            'bread_produced': 0,
            'kdf_produced': 0,
            'scones_produced': 0,
            'bread_dispatched': 0,
            'kdf_dispatched': 0,
            'scones_dispatched': 0,
            'bread_returned': 0,
            'kdf_returned': 0,
            'scones_returned': 0
        }
    )
    
    # Update return quantities using F() to prevent race conditions
    if bread > 0:
        daily_prod.bread_returned = F('bread_returned') + bread
    if kdf > 0:
        daily_prod.kdf_returned = F('kdf_returned') + kdf
    if scones > 0:
        daily_prod.scones_returned = F('scones_returned') + scones
    
    daily_prod.updated_by = user
    daily_prod.save()
    
    # Refresh to get actual values (F() expressions need refresh)
    daily_prod.refresh_from_db()
    
    logger.info(
        f"Products returned on {return_date}: "
        f"Bread={bread}, KDF={kdf}, Scones={scones} by {user}"
    )
    
    return daily_prod, None


def check_low_stock_alerts(mix, user=None):
    """
    Check if any ingredients fall below 7-day supply threshold.
    Called explicitly in production batch creation.
    
    Replaces: post_save signal on ProductionBatch
    
    Args:
        mix: Mix instance
        user: User who triggered the check
    """
    from apps.products.models import MixIngredient
    
    # Note: LowStockAlert model doesn't exist yet
    # Will implement when Inventory app alerts are built
    # For now, just log warnings
    
    mix_ingredients = MixIngredient.objects.filter(mix=mix).select_related('ingredient')
    
    for mix_ingredient in mix_ingredients:
        if not mix_ingredient.ingredient.inventory_item:
            continue
        
        inventory_item = mix_ingredient.ingredient.inventory_item
        
        # Calculate 7-day supply
        daily_usage = mix_ingredient.quantity  # Per batch
        seven_day_supply = daily_usage * 7
        
        if inventory_item.current_stock < seven_day_supply:
            days_remaining = int(inventory_item.current_stock / daily_usage) if daily_usage > 0 else 0
            
            logger.warning(
                f"⚠️ LOW STOCK ALERT: {inventory_item.name}\n"
                f"   Current: {inventory_item.current_stock:.2f} {inventory_item.recipe_unit}\n"
                f"   7-day supply: {seven_day_supply:.2f}\n"
                f"   Days remaining: ~{days_remaining} days\n"
                f"   🛑 REORDER NEEDED"
            )
            
            # TODO: Create LowStockAlert record when model is available
            # LowStockAlert.objects.get_or_create(
            #     inventory_item=inventory_item,
            #     defaults={
            #         'threshold': seven_day_supply,
            #         'current_stock': inventory_item.current_stock,
            #         'days_remaining': days_remaining,
            #         'created_by': user
            #     }
            # )
