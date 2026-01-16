"""
Dependency Checker Service

Provides functions to check if a record can be safely deleted based on
temporal ordering and FK relationships.

Dependency Rules:
- Purchase → Batch: TEMPORAL (any batch created AFTER purchase blocks it)
- Batch → Dispatch: TEMPORAL (any dispatch created AFTER batch blocks it)
- Dispatch → Return: FK (return has foreign key to dispatch)

Author: Chesanto Bakery Management System
Created: January 2026
"""

from django.utils import timezone
from typing import Tuple, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def can_delete_purchase(purchase) -> Tuple[bool, str]:
    """
    Check if a purchase record can be safely deleted.
    
    A purchase can be deleted if NO ProductionBatch exists with
    created_at > purchase.created_at (temporal dependency).
    
    This is intentionally conservative - we don't track which specific
    purchase was consumed by which batch, so if ANY batch happened after,
    we assume it MIGHT have used this purchase.
    
    Args:
        purchase: ItemXXPurchases instance
    
    Returns:
        Tuple of (can_delete: bool, reason: str)
        - If can_delete is True, reason is empty
        - If can_delete is False, reason explains why
    
    Example:
        can_delete, reason = can_delete_purchase(purchase)
        if not can_delete:
            messages.error(request, reason)
            return redirect(...)
    """
    from apps.production.models import ProductionBatch
    
    # Find any batch created after this purchase
    blocking_batch = ProductionBatch.objects.filter(
        created_at__gt=purchase.created_at
    ).order_by('created_at').first()
    
    if blocking_batch:
        return (
            False,
            f"Cannot delete: Production batch {blocking_batch.batch_number} "
            f"was created after this purchase ({blocking_batch.created_at.strftime('%Y-%m-%d %H:%M')}). "
            f"Delete all batches created after {purchase.created_at.strftime('%Y-%m-%d %H:%M')} first."
        )
    
    # Also check if deletion would cause negative stock
    # Get the Details model for this item
    from apps.inventory.routing import get_details_model
    
    try:
        DetailsModel = get_details_model(purchase.inventory_item_id)
        item = DetailsModel.objects.get(pk=1)
        
        if item.current_stock < purchase.quantity_purchased:
            return (
                False,
                f"Cannot delete: Would result in negative stock. "
                f"Current stock: {item.current_stock}, "
                f"Purchase quantity: {purchase.quantity_purchased}"
            )
    except Exception as e:
        logger.warning(f"Could not check stock for purchase deletion: {e}")
        # Don't block on stock check failure - temporal check is primary
    
    return (True, "")


def can_delete_batch(batch) -> Tuple[bool, str]:
    """
    Check if a production batch can be safely deleted.
    
    A batch can be deleted if NO SalesDispatch exists with
    created_at > batch.created_at (temporal dependency).
    
    This is intentionally conservative - if ANY dispatch happened after,
    we assume it MIGHT have dispatched products from this batch.
    
    Args:
        batch: ProductionBatch instance
    
    Returns:
        Tuple of (can_delete: bool, reason: str)
    
    Example:
        can_delete, reason = can_delete_batch(batch)
        if not can_delete:
            raise DataManagementError(reason)
    """
    from apps.sales.models import SalesDispatch
    
    # Find any dispatch created after this batch
    blocking_dispatch = SalesDispatch.objects.filter(
        created_at__gt=batch.created_at
    ).order_by('created_at').first()
    
    if blocking_dispatch:
        return (
            False,
            f"Cannot delete: Sales dispatch {blocking_dispatch.dispatch_number} "
            f"was created after this batch ({blocking_dispatch.created_at.strftime('%Y-%m-%d %H:%M')}). "
            f"Delete all dispatches created after {batch.created_at.strftime('%Y-%m-%d %H:%M')} first."
        )
    
    return (True, "")


def can_delete_dispatch(dispatch) -> Tuple[bool, str]:
    """
    Check if a sales dispatch can be safely deleted.
    
    A dispatch can be deleted if NO SalesReturn exists with
    dispatch_id = dispatch.id (FK relationship, not temporal).
    
    Unlike purchases and batches, this is a direct FK check because
    SalesReturn has a foreign key to SalesDispatch.
    
    Args:
        dispatch: SalesDispatch instance
    
    Returns:
        Tuple of (can_delete: bool, reason: str)
    
    Example:
        can_delete, reason = can_delete_dispatch(dispatch)
        if not can_delete:
            raise DataManagementError(reason)
    """
    from apps.sales.models import SalesReturn
    
    # Check for existing return (FK relationship)
    try:
        existing_return = SalesReturn.objects.get(dispatch=dispatch)
        return (
            False,
            f"Cannot delete: A return exists for this dispatch (processed {existing_return.return_date}). "
            f"Returns are immutable financial records and cannot be deleted. "
            f"Use Full System Reset if data correction is needed."
        )
    except SalesReturn.DoesNotExist:
        pass  # No return exists, can proceed
    
    return (True, "")


def get_blocking_records(record_type: str, record_id: int) -> List[Dict[str, Any]]:
    """
    Get a list of records that block deletion of the specified record.
    
    Used for UI display to show users exactly what's blocking their delete.
    
    Args:
        record_type: One of 'purchase', 'batch', 'dispatch'
        record_id: Primary key of the record
    
    Returns:
        List of dicts with blocking record info:
        [
            {
                'type': 'ProductionBatch',
                'identifier': 'PRD-20260115-001',
                'created_at': datetime,
                'url': '/production/batch/123/'
            },
            ...
        ]
    
    Example:
        blocking = get_blocking_records('purchase', 47)
        if blocking:
            context['blocking_records'] = blocking
    """
    blocking_records = []
    
    if record_type == 'purchase':
        from apps.production.models import ProductionBatch
        from apps.inventory.routing import get_purchases_model
        
        # Get the purchase to find its created_at
        # We need to check all 23 purchase tables - caller should provide the right model
        # For now, return empty - this is for UI display only
        # The actual blocking check is in can_delete_purchase()
        
        # This function is mainly for Option B UX (showing blocking records in template)
        # For Phase 1, we're using Option A (simple Django messages)
        pass
        
    elif record_type == 'batch':
        from apps.production.models import ProductionBatch
        from apps.sales.models import SalesDispatch
        
        try:
            batch = ProductionBatch.objects.get(pk=record_id)
            dispatches = SalesDispatch.objects.filter(
                created_at__gt=batch.created_at
            ).order_by('created_at')[:10]  # Limit to 10 for UI
            
            for d in dispatches:
                blocking_records.append({
                    'type': 'SalesDispatch',
                    'identifier': d.dispatch_number,
                    'created_at': d.created_at,
                    'url': f'/sales/dispatch/{d.pk}/'
                })
        except ProductionBatch.DoesNotExist:
            pass
            
    elif record_type == 'dispatch':
        from apps.sales.models import SalesDispatch, SalesReturn
        
        try:
            dispatch = SalesDispatch.objects.get(pk=record_id)
            try:
                ret = SalesReturn.objects.get(dispatch=dispatch)
                blocking_records.append({
                    'type': 'SalesReturn',
                    'identifier': ret.return_number,
                    'created_at': ret.created_at,
                    'url': f'/sales/dispatch/{dispatch.pk}/'  # Returns are viewed via dispatch
                })
            except SalesReturn.DoesNotExist:
                pass
        except SalesDispatch.DoesNotExist:
            pass
    
    return blocking_records


def get_all_downstream_counts() -> Dict[str, int]:
    """
    Get counts of all records in the dependency chain.
    
    Used for Full Reset UI to show what will be deleted.
    
    Returns:
        Dict with counts for each model type
    
    Example:
        counts = get_all_downstream_counts()
        # {'sales_dispatches': 47, 'sales_returns': 12, ...}
    """
    from apps.sales.models import SalesDispatch, SalesReturn
    from apps.production.models import (
        ProductionBatch, BatchIngredientDeduction,
        ProductStock, ProductStockMovement
    )
    try:
        from apps.production.models import WasteLog
        waste_count = WasteLog.objects.count()
    except ImportError:
        waste_count = 0
    
    from apps.inventory.models import StockAlert
    from apps.inventory.routing import (
        ITEM_PURCHASES_MODELS, ITEM_OUTPUTS_MODELS
    )
    
    # Count purchases across all 23 tables
    purchase_count = sum(
        Model.objects.count() 
        for Model in ITEM_PURCHASES_MODELS.values()
    )
    
    # Count outputs across all 8 tables
    output_count = sum(
        Model.objects.count() 
        for Model in ITEM_OUTPUTS_MODELS.values()
    )
    
    return {
        'sales_dispatches': SalesDispatch.objects.count(),
        'sales_returns': SalesReturn.objects.count(),
        'sales_movements': ProductStockMovement.objects.filter(
            movement_type__in=['DISPATCH', 'RETURN']
        ).count(),
        'production_batches': ProductionBatch.objects.count(),
        'batch_ingredient_deductions': BatchIngredientDeduction.objects.count(),
        'waste_logs': waste_count,
        'production_movements': ProductStockMovement.objects.filter(
            movement_type='PRODUCTION'
        ).count(),
        'purchases': purchase_count,
        'outputs': output_count,
        'stock_alerts': StockAlert.objects.count(),
        'product_stocks': ProductStock.objects.count(),
    }
