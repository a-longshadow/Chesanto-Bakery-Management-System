"""
Transaction-safe utility functions for Inventory app.
These functions provide the interface layer for Sales and other apps.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@transaction.atomic
def receive_purchase_atomic(purchase, user=None):
    """
    Mark purchase as received and update inventory stock.
    
    This replaces the signal-driven stock update.
    Either ALL items are received OR nothing happens (rollback).
    
    Args:
        purchase: Purchase instance
        user: User performing the receipt
    
    Returns:
        (success: bool, error_message: str or None)
    """
    from .models import InventoryItem, StockMovement
    
    if purchase.status == 'RECEIVED':
        return False, "❌ Purchase already received"
    
    # Lock all affected inventory items
    purchase_items = purchase.purchaseitem_set.select_related('item').all()
    
    if not purchase_items.exists():
        return False, "❌ No items in this purchase"
    
    # Update each inventory item with locking
    for purchase_item in purchase_items:
        # Lock inventory item to prevent race conditions
        inventory_item = InventoryItem.objects.select_for_update().get(
            id=purchase_item.item.id
        )
        
        # Convert to recipe unit if needed
        quantity = purchase_item.quantity
        
        # purchase_item.quantity is in purchase_unit
        # Need to convert to recipe_unit using conversion_factor
        converted_qty = quantity * inventory_item.conversion_factor
        
        # Record stock before
        stock_before = inventory_item.current_stock
        
        # Update stock
        inventory_item.current_stock += converted_qty
        
        # ✅ SAFETY CHECK (should never be negative)
        if inventory_item.current_stock < 0:
            raise ValidationError(
                f"❌ INTEGRITY ERROR: {inventory_item.name} would go negative!\n"
                f"   This should never happen. Rolling back entire transaction."
            )
        
        inventory_item.save()
        
        # Create audit trail
        StockMovement.objects.create(
            item=inventory_item,
            movement_type='PURCHASE',
            quantity=converted_qty,
            unit=inventory_item.recipe_unit,
            reference_type='Purchase',
            reference_id=purchase.id,
            notes=f"Purchase {purchase.purchase_number} received",
            stock_before=stock_before,
            stock_after=inventory_item.current_stock,
            created_by=user
        )
        
        logger.info(
            f"Received {purchase_item.quantity} {inventory_item.purchase_unit} "
            f"({converted_qty} {inventory_item.recipe_unit}) of {inventory_item.name} "
            f"from purchase {purchase.purchase_number}"
        )
    
    # Update purchase status
    from django.utils import timezone
    purchase.status = 'RECEIVED'
    purchase.actual_delivery_date = timezone.now().date()
    purchase.updated_by = user
    purchase.save()
    
    logger.info(f"Purchase {purchase.purchase_number} marked as RECEIVED")
    
    return True, None


@transaction.atomic
def dispatch_crates_atomic(quantity, dispatch_id=None, user=None):
    """
    Dispatch crates for Sales.
    Atomic operation with row locking.
    
    Args:
        quantity: Number of crates to dispatch
        dispatch_id: Related dispatch ID (optional)
        user: User performing the dispatch
    
    Returns:
        (crate_stock, error_message)
        - crate_stock: CrateStock instance if successful, None if error
        - error_message: str if error, None if successful
    """
    from .models import CrateStock, CrateMovement
    
    if quantity <= 0:
        return None, "❌ Quantity must be positive"
    
    # Get and lock the single CrateStock record
    try:
        crate_stock = CrateStock.objects.select_for_update().get(pk=1)
    except CrateStock.DoesNotExist:
        # Create if doesn't exist
        crate_stock = CrateStock.objects.create(
            pk=1,
            total_crates=0,
            available_crates=0,
            dispatched_crates=0,
            damaged_crates=0
        )
    
    # ❌ BLOCK if insufficient crates (negative stock prevention)
    if quantity > crate_stock.available_crates:
        return None, (
            f"❌ INSUFFICIENT CRATES\n"
            f"   Requested: {quantity} crates\n"
            f"   Available: {crate_stock.available_crates} crates\n"
            f"   Deficit: {quantity - crate_stock.available_crates} crates\n"
            f"   🛑 CANNOT DISPATCH - Add crates first or reduce dispatch quantity"
        )
    
    # Update crate stock
    crate_stock.available_crates -= quantity
    crate_stock.dispatched_crates += quantity
    
    # ✅ SAFETY CHECK (should never be negative)
    if crate_stock.available_crates < 0:
        raise ValidationError(
            "❌ INTEGRITY ERROR: Available crates would go negative!\n"
            "   This should never happen. Rolling back entire transaction."
        )
    
    crate_stock.save()
    
    # Create audit trail
    CrateMovement.objects.create(
        movement_type='DISPATCH_OUT',
        quantity=quantity,
        dispatch_id=dispatch_id,
        notes=f"Dispatched {quantity} crates" + (f" for dispatch #{dispatch_id}" if dispatch_id else ""),
        created_by=user
    )
    
    logger.info(
        f"Dispatched {quantity} crates. "
        f"Available: {crate_stock.available_crates}, "
        f"Dispatched: {crate_stock.dispatched_crates}"
    )
    
    return crate_stock, None


@transaction.atomic
def return_crates_atomic(quantity, dispatch_id=None, user=None):
    """
    Return crates from Sales.
    Atomic operation with row locking.
    
    Args:
        quantity: Number of crates to return
        dispatch_id: Related dispatch ID (optional)
        user: User performing the return
    
    Returns:
        (crate_stock, error_message)
    """
    from .models import CrateStock, CrateMovement
    
    if quantity <= 0:
        return None, "❌ Quantity must be positive"
    
    # Get and lock the single CrateStock record
    try:
        crate_stock = CrateStock.objects.select_for_update().get(pk=1)
    except CrateStock.DoesNotExist:
        return None, "❌ Crate stock record not found. Please contact administrator."
    
    # ❌ BLOCK if trying to return more than dispatched
    if quantity > crate_stock.dispatched_crates:
        return None, (
            f"❌ INVALID RETURN\n"
            f"   Trying to return: {quantity} crates\n"
            f"   Currently dispatched: {crate_stock.dispatched_crates} crates\n"
            f"   Overage: {quantity - crate_stock.dispatched_crates} crates\n"
            f"   🛑 CANNOT RETURN - Check dispatch records"
        )
    
    # Update crate stock
    crate_stock.dispatched_crates -= quantity
    crate_stock.available_crates += quantity
    
    # ✅ SAFETY CHECK (should never be negative)
    if crate_stock.dispatched_crates < 0:
        raise ValidationError(
            "❌ INTEGRITY ERROR: Dispatched crates would go negative!\n"
            "   This should never happen. Rolling back entire transaction."
        )
    
    crate_stock.save()
    
    # Create audit trail
    CrateMovement.objects.create(
        movement_type='RETURN_IN',
        quantity=quantity,
        dispatch_id=dispatch_id,
        notes=f"Returned {quantity} crates" + (f" from dispatch #{dispatch_id}" if dispatch_id else ""),
        created_by=user
    )
    
    logger.info(
        f"Returned {quantity} crates. "
        f"Available: {crate_stock.available_crates}, "
        f"Dispatched: {crate_stock.dispatched_crates}"
    )
    
    return crate_stock, None


def get_available_crates():
    """
    Read-only query for available crates.
    Safe for Sales to call.
    
    Returns:
        int: Number of available crates
    """
    from .models import CrateStock
    
    try:
        crate_stock = CrateStock.objects.get(pk=1)
        return crate_stock.available_crates
    except CrateStock.DoesNotExist:
        return 0


def convert_quantity(quantity, from_unit, to_unit):
    """
    Convert quantity from one unit to another using UnitConversion table.
    
    Args:
        quantity: Decimal quantity to convert
        from_unit: Source unit (e.g., 'bag')
        to_unit: Target unit (e.g., 'kg')
    
    Returns:
        Decimal: Converted quantity
    """
    from .models import UnitConversion
    
    if from_unit == to_unit:
        return quantity
    
    try:
        conversion = UnitConversion.objects.get(
            from_unit=from_unit,
            to_unit=to_unit
        )
        return quantity * conversion.factor
    except UnitConversion.DoesNotExist:
        # Try reverse conversion
        try:
            conversion = UnitConversion.objects.get(
                from_unit=to_unit,
                to_unit=from_unit
            )
            return quantity / conversion.factor
        except UnitConversion.DoesNotExist:
            # No conversion rule - log warning and return as is
            logger.warning(
                f"No conversion from {from_unit} to {to_unit}. "
                f"Returning original quantity."
            )
            return quantity
