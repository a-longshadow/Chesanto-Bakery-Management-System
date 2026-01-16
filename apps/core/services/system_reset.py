"""
System Reset Service

Full system reset for Primary Superadmin only.
Wipes all transaction data while preserving configuration.

This is the nuclear option - use only when individual record
deletion is impractical due to extensive erroneous data.

Author: Chesanto Bakery Management System
Created: January 2026
"""

from decimal import Decimal
from django.db import transaction
import logging

from .data_management import DataManagementError

logger = logging.getLogger(__name__)


@transaction.atomic
def execute_full_reset(user, reason: str = '') -> dict:
    """
    Wipe all transaction data from Inventory, Production, and Sales.
    
    CRITICAL: Uses QuerySet._raw_delete() to bypass model delete() guards.
    All models have immutability guards that raise ValueError on delete().
    
    Args:
        user: Must be Primary Superadmin (is_primary_superadmin=True)
        reason: Required explanation for audit log
    
    Returns:
        dict with counts of deleted records
    
    Raises:
        PermissionError: If user is not Primary Superadmin
        ValueError: If reason is not provided
        DataManagementError: On any deletion failure
    
    Order matters - delete in reverse dependency order:
    1. Sales movements (no FK protection)
    2. SalesReturn (PROTECTS SalesDispatch)
    3. SalesDispatch (CASCADE deletes SalesDispatchItem)
    4. Production movements (no FK protection)
    5. BatchIngredientDeduction (PROTECTS ProductionBatch)
    6. ProductionBatch
    7. WasteLog
    8. Inventory purchases & outputs
    9. StockAlert
    10. Reset balances (UPDATE, not DELETE)
    
    What is PRESERVED:
    - User accounts
    - Products & Mixes (recipes)
    - Inventory item definitions
    - Report schedules & recipients
    - System configuration
    """
    # Lazy imports to avoid circular dependencies
    from apps.sales.models import SalesReturn, SalesDispatch
    from apps.production.models import (
        ProductionBatch, BatchIngredientDeduction,
        ProductStock, ProductStockMovement, WasteLog
    )
    from apps.inventory.models import StockAlert
    from apps.inventory.routing import (
        ITEM_PURCHASES_MODELS, ITEM_OUTPUTS_MODELS, ITEM_DETAILS_MODELS
    )
    from apps.audit.models import AuditLog
    
    # ==========================================================================
    # PERMISSION CHECK
    # ==========================================================================
    
    if not getattr(user, 'is_primary_superadmin', False):
        raise PermissionError(
            "Only Primary Superadmin can perform full reset. "
            "Contact the system administrator."
        )
    
    if not reason or not reason.strip():
        raise ValueError("Reason is required for audit trail")
    
    reason = reason.strip()
    
    logger.warning(
        f"FULL SYSTEM RESET initiated by {user.email}. Reason: {reason}"
    )
    
    # ==========================================================================
    # COUNT RECORDS BEFORE DELETION (for audit and UI display)
    # ==========================================================================
    
    counts = {
        'sales_returns': SalesReturn.objects.count(),
        'sales_dispatches': SalesDispatch.objects.count(),
        'sales_movements': ProductStockMovement.objects.filter(
            movement_type__in=['DISPATCH', 'RETURN']
        ).count(),
        'production_batches': ProductionBatch.objects.count(),
        'batch_ingredient_deductions': BatchIngredientDeduction.objects.count(),
        'waste_logs': WasteLog.objects.count(),
        'production_movements': ProductStockMovement.objects.filter(
            movement_type='PRODUCTION'
        ).count(),
        'stock_alerts': StockAlert.objects.count(),
        # Sum across all purchase tables
        'purchases': sum(
            Model.objects.count()
            for Model in ITEM_PURCHASES_MODELS.values()
        ),
        # Sum across all output tables
        'outputs': sum(
            Model.objects.count()
            for Model in ITEM_OUTPUTS_MODELS.values()
        ),
    }
    
    total_records = sum(counts.values())
    
    try:
        # ======================================================================
        # SALES - Delete movements first, then returns, then dispatches
        # ======================================================================
        
        # ProductStockMovement for sales (DISPATCH, RETURN types)
        # Uses _raw_delete() to bypass model's save/delete guards
        ProductStockMovement.objects.filter(
            movement_type__in=['DISPATCH', 'RETURN']
        )._raw_delete(using='default')
        
        # SalesReturn - must delete BEFORE SalesDispatch (PROTECT relationship)
        # Cascades to SalesReturnItem
        SalesReturn.objects.all()._raw_delete(using='default')
        
        # SalesDispatch - Cascades to SalesDispatchItem
        SalesDispatch.objects.all()._raw_delete(using='default')
        
        # ======================================================================
        # PRODUCTION - Delete movements, then deductions, then batches
        # ======================================================================
        
        # ProductStockMovement for production (PRODUCTION type)
        ProductStockMovement.objects.filter(
            movement_type='PRODUCTION'
        )._raw_delete(using='default')
        
        # BatchIngredientDeduction - must delete BEFORE ProductionBatch (PROTECT)
        BatchIngredientDeduction.objects.all()._raw_delete(using='default')
        
        # ProductionBatch
        ProductionBatch.objects.all()._raw_delete(using='default')
        
        # WasteLog
        WasteLog.objects.all()._raw_delete(using='default')
        
        # ======================================================================
        # INVENTORY - All 23 purchase tables + 8 output tables
        # ======================================================================
        
        # Purchases (all 23 tables)
        for item_id, PurchaseModel in ITEM_PURCHASES_MODELS.items():
            PurchaseModel.objects.all()._raw_delete(using='default')
        
        # Outputs (items 16-23 only, 8 tables)
        for item_id, OutputModel in ITEM_OUTPUTS_MODELS.items():
            OutputModel.objects.all()._raw_delete(using='default')
        
        # StockAlert
        StockAlert.objects.all()._raw_delete(using='default')
        
        # ======================================================================
        # RESET BALANCES TO ZERO (UPDATE, not DELETE)
        # ======================================================================
        
        # Inventory item balances (all 23 Details tables)
        for item_id, DetailsModel in ITEM_DETAILS_MODELS.items():
            DetailsModel.objects.all().update(
                current_stock=Decimal('0'),
                last_purchase_unit_price=Decimal('0'),
                last_purchase_date=None
            )
        
        # Product stock balances
        product_stock_count = ProductStock.objects.count()
        ProductStock.objects.all().update(
            current_stock=0,
            last_production_date=None,
            last_production_batch=None
        )
        
        # ======================================================================
        # AUDIT LOG - Record the reset action
        # ======================================================================
        
        AuditLog.objects.create(
            action='DELETE',
            user=user,
            app_label='core',
            model_name='FULL_SYSTEM_RESET',
            object_pk='ALL',
            changes={
                'records_deleted': counts,
                'total_records_deleted': total_records,
                'inventory_items_reset': len(ITEM_DETAILS_MODELS),
                'product_stocks_reset': product_stock_count,
            },
            message=f"FULL_SYSTEM_RESET: {reason}"
        )
        
        logger.warning(
            f"FULL SYSTEM RESET completed by {user.email}. "
            f"Deleted {total_records} records."
        )
        
        return {
            'success': True,
            'counts': counts,
            'total_deleted': total_records,
            'inventory_items_reset': len(ITEM_DETAILS_MODELS),
            'product_stocks_reset': product_stock_count,
        }
        
    except Exception as e:
        logger.error(f"FULL SYSTEM RESET failed: {str(e)}")
        raise DataManagementError(f"Reset failed: {str(e)}")


def get_reset_preview() -> dict:
    """
    Get counts of all records that would be deleted in a full reset.
    
    Used for the confirmation page to show users exactly what will be affected.
    
    Returns:
        dict with counts by category
    """
    from apps.sales.models import SalesReturn, SalesDispatch
    from apps.production.models import (
        ProductionBatch, BatchIngredientDeduction,
        ProductStock, ProductStockMovement, WasteLog
    )
    from apps.inventory.models import StockAlert
    from apps.inventory.routing import (
        ITEM_PURCHASES_MODELS, ITEM_OUTPUTS_MODELS, ITEM_DETAILS_MODELS
    )
    
    return {
        'sales': {
            'dispatches': SalesDispatch.objects.count(),
            'returns': SalesReturn.objects.count(),
            'movements': ProductStockMovement.objects.filter(
                movement_type__in=['DISPATCH', 'RETURN']
            ).count(),
        },
        'production': {
            'batches': ProductionBatch.objects.count(),
            'ingredient_deductions': BatchIngredientDeduction.objects.count(),
            'waste_logs': WasteLog.objects.count(),
            'movements': ProductStockMovement.objects.filter(
                movement_type='PRODUCTION'
            ).count(),
        },
        'inventory': {
            'purchases': sum(
                Model.objects.count()
                for Model in ITEM_PURCHASES_MODELS.values()
            ),
            'outputs': sum(
                Model.objects.count()
                for Model in ITEM_OUTPUTS_MODELS.values()
            ),
            'alerts': StockAlert.objects.count(),
        },
        'totals': {
            'inventory_items': len(ITEM_DETAILS_MODELS),
            'product_stocks': ProductStock.objects.count(),
        },
    }
