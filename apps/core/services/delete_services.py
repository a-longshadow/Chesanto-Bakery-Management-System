"""
Delete Services

High-level delete operations for Purchase, Batch, and Dispatch records.
Composes dependency checking with force delete to provide complete
reversal of CREATE operations.

Usage:
    from apps.core.services import delete_purchase, delete_batch, delete_dispatch
    
    result = delete_purchase(purchase, user, reason="Wrong quantity")
    result = delete_batch(batch, user, reason="Test batch")
    result = delete_dispatch(dispatch, user, reason="Duplicate entry")

All operations:
- Check temporal/FK dependencies
- Reverse stock changes atomically
- Create AuditLog snapshot before deletion
- Cascade delete related records

Author: Chesanto Bakery Management System
Created: January 2026
"""

from decimal import Decimal
from django.db import transaction
import logging

from .data_management import _force_delete, DataManagementError
from .dependency_checker import can_delete_purchase, can_delete_batch, can_delete_dispatch

logger = logging.getLogger(__name__)


# =============================================================================
# DELETE PURCHASE
# =============================================================================

@transaction.atomic
def delete_purchase(purchase, user, reason: str = '', inventory_item_id: int = None) -> dict:
    """
    Delete an inventory purchase and reverse its stock effects.
    
    This is the INVERSE of purchase creation (via PurchaseFormView).
    
    On creation, a purchase:
    1. Created ItemXXPurchases record
    2. Increased ItemXXDetails.current_stock by quantity_purchased
    3. Updated ItemXXDetails.last_purchase_unit_price
    4. Recalculated ItemXXDetails.current_value
    
    On deletion (this function):
    1. Decreases ItemXXDetails.current_stock by quantity_purchased
    2. Does NOT change last_purchase_unit_price (kept as stale reference)
    3. Recalculates current_value (automatic on save)
    4. Deletes the ItemXXPurchases record via _force_delete
    
    Args:
        purchase: ItemXXPurchases instance to delete
        user: User performing the deletion (must be SUPERADMIN)
        reason: Optional reason for audit log
        inventory_item_id: The item ID (1-23) - REQUIRED
        reason: Optional reason for audit log
    
    Returns:
        dict with keys:
            - success: True
            - data: {item_name, quantity_reversed, stock_before, stock_after}
    
    Raises:
        DataManagementError: If purchase cannot be deleted (batch exists after it)
    
    Example:
        try:
            result = delete_purchase(purchase, request.user, "Duplicate entry")
            messages.success(request, f"Purchase deleted. Stock: {result['data']['stock_after']}")
        except DataManagementError as e:
            messages.error(request, str(e))
    """
    from apps.inventory.routing import get_details_model
    
    # Validate inventory_item_id is provided
    if inventory_item_id is None:
        raise DataManagementError("inventory_item_id is required for delete_purchase")
    
    # Step 1: Validate dependencies
    can_delete, blocking_reason = can_delete_purchase(purchase)
    if not can_delete:
        raise DataManagementError(blocking_reason)
    
    # Step 2: Get and lock the item details row
    item_id = inventory_item_id
    DetailsModel = get_details_model(item_id)
    item = DetailsModel.objects.select_for_update().get(pk=1)
    
    # Record state before modification
    stock_before = item.current_stock
    item_name = item.name
    purchase_number = purchase.purchase_number
    quantity = purchase.quantity_purchased
    
    # Step 3: Reduce stock (reverse of purchase)
    item.current_stock -= quantity
    
    # Step 4: DO NOT touch last_purchase_unit_price or last_purchase_date
    # The existing values are fine - no production depended on this purchase
    
    # Step 5: Save (current_value auto-calculated by model)
    item.updated_by = user
    item.save()
    
    # Step 6: Delete purchase with audit trail
    _force_delete(purchase, user, 'DELETE_PURCHASE', reason)
    
    logger.info(
        f"Purchase {purchase_number} deleted by {user.email}. "
        f"Stock: {stock_before} → {item.current_stock}"
    )
    
    return {
        'success': True,
        'data': {
            'purchase_number': purchase_number,
            'item_name': item_name,
            'quantity_reversed': str(quantity),
            'stock_before': str(stock_before),
            'stock_after': str(item.current_stock),
        }
    }


# =============================================================================
# DELETE BATCH
# =============================================================================

@transaction.atomic
def delete_batch(batch, user, reason: str = '') -> dict:
    """
    Delete a production batch and reverse all its effects.
    
    This is the INVERSE of ProductionService.create_production_batch().
    
    On creation, a batch:
    1. Deducted ingredients from inventory (BatchIngredientDeduction records)
    2. Increased ProductStock.current_stock for the product
    3. Created ProductStockMovement(PRODUCTION, +qty)
    4. Updated ProductStock.last_production_date/batch
    5. Created the ProductionBatch record
    
    On deletion (this function):
    1. Restores ALL ingredients to inventory from BatchIngredientDeduction
    2. Decreases ProductStock.current_stock by quantity_produced
    3. Deletes the ProductStockMovement(PRODUCTION) record
    4. Updates ProductStock tracking to previous batch
    5. Deletes ProductionBatch (CASCADE deletes BatchIngredientDeduction)
    
    Args:
        batch: ProductionBatch instance to delete
        user: User performing the deletion (must be SUPERADMIN)
        reason: Optional reason for audit log
    
    Returns:
        dict with keys:
            - success: True
            - data: {batch_number, product_name, ingredients_restored, ...}
    
    Raises:
        DataManagementError: If batch cannot be deleted (dispatch exists after it)
    
    Example:
        try:
            result = delete_batch(batch, request.user, "Test batch - not real production")
            messages.success(request, f"Batch {result['data']['batch_number']} deleted")
        except DataManagementError as e:
            messages.error(request, str(e))
    """
    from apps.inventory.routing import get_details_model
    from apps.production.models import ProductionBatch, ProductStock, ProductStockMovement
    
    # Step 1: Validate dependencies
    can_delete, blocking_reason = can_delete_batch(batch)
    if not can_delete:
        raise DataManagementError(blocking_reason)
    
    # Record batch info before deletion
    batch_number = batch.batch_number
    product_name = batch.product.name
    quantity_produced = batch.quantity_produced
    
    # Step 2: Lock ProductStock row first (prevents dispatch racing us)
    stock = ProductStock.objects.select_for_update().get(product=batch.product)
    stock_before = stock.current_stock
    
    # Step 3: Restore ALL ingredients to inventory
    # BatchIngredientDeduction contains everything we need - no Mix lookup required
    restored_ingredients = []
    for deduction in batch.ingredient_deductions.select_for_update().all():
        DetailsModel = get_details_model(deduction.inventory_item_id)
        item = DetailsModel.objects.select_for_update().get(pk=1)
        
        # Record state for response
        item_stock_before = item.current_stock
        
        # Restore the exact quantity that was deducted
        item.current_stock += deduction.quantity_deducted
        item.updated_by = user
        item.save()  # current_value auto-calculated
        
        restored_ingredients.append({
            'inventory_item_id': deduction.inventory_item_id,
            'item_name': item.name,
            'quantity_restored': str(deduction.quantity_deducted),
            'stock_before': str(item_stock_before),
            'stock_after': str(item.current_stock),
        })
    
    # Step 4: Reduce finished goods stock
    stock.current_stock -= quantity_produced
    
    # Step 5: Update tracking references
    if stock.last_production_batch == batch:
        prev_batch = ProductionBatch.objects.filter(
            product=batch.product,
            created_at__lt=batch.created_at
        ).order_by('-created_at').first()
        stock.last_production_batch = prev_batch
        stock.last_production_date = prev_batch.production_date if prev_batch else None
    stock.save()
    
    # Step 6: Delete related stock movements
    deleted_movements = ProductStockMovement.objects.filter(
        reference_type='ProductionBatch',
        reference_id=batch.id
    ).delete()[0]  # Returns (count, {model: count})
    
    # Step 7: Delete BatchIngredientDeduction records FIRST (uses PROTECT, not CASCADE)
    # We've already restored stock from them, now we can safely delete
    from apps.production.models import BatchIngredientDeduction
    BatchIngredientDeduction.objects.filter(batch=batch)._raw_delete(using='default')
    
    # Step 8: Delete batch with audit trail
    _force_delete(batch, user, 'DELETE_BATCH', reason)
    
    logger.info(
        f"Batch {batch_number} deleted by {user.email}. "
        f"ProductStock: {stock_before} → {stock.current_stock}. "
        f"Restored {len(restored_ingredients)} ingredients."
    )
    
    return {
        'success': True,
        'data': {
            'batch_number': batch_number,
            'product_name': product_name,
            'quantity_produced': str(quantity_produced),
            'ingredients_restored': restored_ingredients,
            'product_stock_before': str(stock_before),
            'product_stock_after': str(stock.current_stock),
            'movements_deleted': deleted_movements,
        }
    }


# =============================================================================
# DELETE DISPATCH
# =============================================================================

def _restore_crates_on_delete(dispatch, user) -> dict:
    """
    Restore crates to inventory when deleting a dispatch.
    
    INTEGRITY GUARANTEES:
    1. Finds the EXACT output record via unique dispatch_number
    2. Validates quantity matches before proceeding
    3. Uses OUTPUT's quantity for restoration (not dispatch's) for ledger accuracy
    4. Raises DataManagementError on ANY inconsistency
    5. Handles edge case where crates weren't deducted on creation
    
    Unlike return_crates_atomic(), this DELETES the output record (no new purchase).
    
    Args:
        dispatch: SalesDispatch instance being deleted
        user: User performing the deletion
    
    Returns:
        dict with keys: success, restored (Decimal), output_deleted or warning
    
    Raises:
        DataManagementError: On data integrity issues
    """
    from apps.inventory.routing import get_details_model, get_outputs_model
    
    CRATES_ITEM_ID = 16
    CratesDetails = get_details_model(CRATES_ITEM_ID)
    CratesOutputs = get_outputs_model(CRATES_ITEM_ID)
    
    # Find the EXACT output record using unique dispatch_number
    search_ref = f"Ref: {dispatch.dispatch_number}"
    
    try:
        output = CratesOutputs.objects.get(description__contains=search_ref)
    except CratesOutputs.DoesNotExist:
        # No output exists - dispatch was created before crates were initialized
        logger.warning(
            f"No crate output found for dispatch {dispatch.dispatch_number}. "
            f"Crates were likely not deducted on creation."
        )
        return {'success': True, 'restored': Decimal('0'), 'warning': 'No output record found'}
    except CratesOutputs.MultipleObjectsReturned:
        # Should NEVER happen - dispatch_number is unique
        raise DataManagementError(
            f"Data integrity error: Multiple crate outputs found for {dispatch.dispatch_number}. "
            f"Manual intervention required."
        )
    
    # INTEGRITY CHECK: Quantity MUST match
    if output.quantity_consumed != Decimal(str(dispatch.crates_dispatched)):
        raise DataManagementError(
            f"Data integrity error: Output quantity ({output.quantity_consumed}) "
            f"does not match dispatch crates ({dispatch.crates_dispatched}). "
            f"Manual intervention required."
        )
    
    # Restore stock (use OUTPUT's quantity for ledger accuracy)
    crates = CratesDetails.objects.select_for_update().get(pk=1)
    crates.current_stock += output.quantity_consumed
    crates.updated_by = user
    crates.save()
    
    # Delete the output record (QuerySet.delete() bypasses model guard)
    deleted_output_number = output.output_number
    CratesOutputs.objects.filter(pk=output.pk).delete()
    
    return {
        'success': True,
        'restored': output.quantity_consumed,
        'output_deleted': deleted_output_number
    }


@transaction.atomic
def delete_dispatch(dispatch, user, reason: str = '') -> dict:
    """
    Delete a sales dispatch and reverse all its effects.
    
    This is the INVERSE of dispatch creation (via SalesDispatchView).
    
    On creation, a dispatch:
    1. Created SalesDispatch record
    2. Created SalesDispatchItem records (one per product)
    3. Decreased ProductStock.current_stock for each product
    4. Created ProductStockMovement(DISPATCH, -qty) for each product
    5. Decreased Item16CratesDetails.current_stock (crates sent out)
    6. Created Item16CratesOutputs record
    
    On deletion (this function):
    1. Restores ProductStock.current_stock for each SalesDispatchItem
    2. Deletes ProductStockMovement(DISPATCH) records
    3. Restores Item16CratesDetails.current_stock (crates returned to inventory)
    4. Deletes Item16CratesOutputs record
    5. Deletes SalesDispatch (CASCADE deletes SalesDispatchItem)
    
    Note: Does NOT affect ProductionBatch records - production is independent.
    
    Args:
        dispatch: SalesDispatch instance to delete
        user: User performing the deletion (must be SUPERADMIN)
        reason: Optional reason for audit log
    
    Returns:
        dict with keys:
            - success: True
            - data: {dispatch_number, products_restored, crates_restored, ...}
    
    Raises:
        DataManagementError: If dispatch cannot be deleted (return exists)
    
    Example:
        try:
            result = delete_dispatch(dispatch, request.user, "Duplicate dispatch")
            messages.success(request, f"Dispatch {result['data']['dispatch_number']} deleted")
        except DataManagementError as e:
            messages.error(request, str(e))
    """
    from apps.production.models import ProductStock, ProductStockMovement
    
    # Step 1: Validate dependencies
    can_delete, blocking_reason = can_delete_dispatch(dispatch)
    if not can_delete:
        raise DataManagementError(blocking_reason)
    
    # Record dispatch info before deletion
    dispatch_number = dispatch.dispatch_number
    
    # Step 2: Restore product stock for each item
    products_restored = []
    for item in dispatch.items.select_for_update().all():
        stock = ProductStock.objects.select_for_update().get(product=item.product)
        stock_before = stock.current_stock
        
        stock.current_stock += item.quantity
        stock.save()
        
        products_restored.append({
            'product_name': item.product.name,
            'quantity_restored': str(item.quantity),
            'stock_before': str(stock_before),
            'stock_after': str(stock.current_stock),
        })
    
    # Step 3: Delete the stock movements that were created on dispatch
    deleted_movements = ProductStockMovement.objects.filter(
        reference_type='SalesDispatch',
        reference_id=dispatch.id
    ).delete()[0]
    
    # Step 4: Restore crates to inventory (if any were dispatched)
    crates_result = {'restored': Decimal('0')}
    if dispatch.crates_dispatched > 0:
        crates_result = _restore_crates_on_delete(dispatch, user)
        if not crates_result.get('success'):
            raise DataManagementError(f"Crate restoration failed: {crates_result.get('error')}")
    
    # Step 5: Delete dispatch with audit trail (CASCADE deletes SalesDispatchItem)
    _force_delete(dispatch, user, 'DELETE_DISPATCH', reason)
    
    logger.info(
        f"Dispatch {dispatch_number} deleted by {user.email}. "
        f"Restored {len(products_restored)} products, {crates_result['restored']} crates."
    )
    
    return {
        'success': True,
        'data': {
            'dispatch_number': dispatch_number,
            'products_restored': products_restored,
            'movements_deleted': deleted_movements,
            'crates_restored': str(crates_result['restored']),
            'crates_output_deleted': crates_result.get('output_deleted'),
        }
    }
