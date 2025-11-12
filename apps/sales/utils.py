"""
Sales App Atomic Utilities
Handles dispatches and returns using Production/Inventory utilities
NEVER writes directly to Production/Inventory models
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import Dict, Tuple, Optional

from .models import Dispatch, Salesperson
from apps.production.utils import get_available_stock, add_returned_products
from apps.inventory.utils import dispatch_crates_atomic, return_crates_atomic, get_available_crates
from apps.products.models import Product


def validate_dispatch_stock(bread_qty: int, kdf_qty: int, scones_qty: int, up_to_date=None) -> Dict[str, any]:
    """
    Validate product availability before dispatch.
    Returns availability dict with warnings/errors.
    """
    if up_to_date is None:
        up_to_date = timezone.now().date()
    
    # Get available stock
    available = get_available_stock(
        product_field=['bread', 'kdf', 'scones'],
        up_to_date=up_to_date
    )
    
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'available': available
    }
    
    # Check bread
    if bread_qty > 0:
        if available['bread'] < bread_qty:
            if available['bread'] == 0:
                result['valid'] = False
                result['errors'].append(f"No bread available (requested: {bread_qty})")
            else:
                result['valid'] = False
                result['errors'].append(
                    f"Insufficient bread: {available['bread']} available, {bread_qty} requested"
                )
    
    # Check KDF
    if kdf_qty > 0:
        if available['kdf'] < kdf_qty:
            if available['kdf'] == 0:
                result['valid'] = False
                result['errors'].append(f"No KDF available (requested: {kdf_qty})")
            else:
                result['valid'] = False
                result['errors'].append(
                    f"Insufficient KDF: {available['kdf']} available, {kdf_qty} requested"
                )
    
    # Check scones
    if scones_qty > 0:
        if available['scones'] < scones_qty:
            if available['scones'] == 0:
                result['valid'] = False
                result['errors'].append(f"No scones available (requested: {scones_qty})")
            else:
                result['valid'] = False
                result['errors'].append(
                    f"Insufficient scones: {available['scones']} available, {scones_qty} requested"
                )
    
    # Warning for low stock
    for product, qty in [('bread', bread_qty), ('kdf', kdf_qty), ('scones', scones_qty)]:
        if qty > 0 and available[product] > 0:
            remaining = available[product] - qty
            if remaining < 50:  # Low stock threshold
                result['warnings'].append(
                    f"Low {product} stock after dispatch: {remaining} remaining"
                )
    
    return result


@transaction.atomic
def create_dispatch_atomic(
    salesperson_id: int,
    dispatch_date,
    bread_qty: int,
    kdf_qty: int,
    scones_qty: int,
    crates_qty: int,
    user
) -> Tuple[Optional[Dispatch], Dict[str, any]]:
    """
    Atomically create a dispatch:
    1. Validate stock availability
    2. Create Dispatch record
    3. Dispatch crates (if > 0)
    
    Returns: (dispatch, result_dict)
    result_dict contains: {'success': bool, 'errors': [], 'warnings': []}
    """
    result = {'success': False, 'errors': [], 'warnings': []}
    
    # 1. Validate stock BEFORE any writes
    validation = validate_dispatch_stock(bread_qty, kdf_qty, scones_qty, dispatch_date)
    
    if not validation['valid']:
        result['errors'] = validation['errors']
        return None, result
    
    result['warnings'] = validation['warnings']
    
    # 2. Lock salesperson to prevent duplicate dispatch on same date
    try:
        salesperson = Salesperson.objects.select_for_update().get(
            id=salesperson_id,
            is_active=True
        )
    except Salesperson.DoesNotExist:
        result['errors'].append("Salesperson not found or inactive")
        return None, result
    
    # Check for existing dispatch on same date
    existing = Dispatch.objects.filter(
        salesperson=salesperson,
        dispatch_date=dispatch_date,
        deleted_at__isnull=True
    ).exists()
    
    if existing:
        result['errors'].append(
            f"Dispatch already exists for {salesperson.name} on {dispatch_date}"
        )
        return None, result
    
    # 3. Validate crates availability
    if crates_qty > 0:
        available_crates = get_available_crates()
        if available_crates < crates_qty:
            result['errors'].append(
                f"Insufficient crates: {available_crates} available, {crates_qty} requested"
            )
            return None, result
    
    # 4. Create dispatch record
    dispatch = Dispatch.objects.create(
        salesperson=salesperson,
        dispatch_date=dispatch_date,
        bread_qty=bread_qty,
        kdf_qty=kdf_qty,
        scones_qty=scones_qty,
        crates_dispatched=crates_qty,
        created_by=user,
        updated_by=user
    )
    
    # 5. Dispatch crates (if any)
    if crates_qty > 0:
        crate_result = dispatch_crates_atomic(
            quantity=crates_qty,
            dispatch_id=dispatch.dispatch_number,
            user=user
        )
        
        if not crate_result['success']:
            # Rollback will happen automatically
            result['errors'].append(f"Crate dispatch failed: {crate_result.get('error', 'Unknown error')}")
            return None, result
    
    result['success'] = True
    return dispatch, result


@transaction.atomic
def return_dispatch_atomic(
    dispatch_id: int,
    bread_sold: int,
    bread_returned: int,
    kdf_sold: int,
    kdf_returned: int,
    scones_sold: int,
    scones_returned: int,
    crates_returned: int,
    user
) -> Tuple[Optional[Dispatch], Dict[str, any]]:
    """
    Atomically process dispatch return:
    1. Lock dispatch record
    2. Validate accountability (sold + returned = dispatched)
    3. Calculate revenue
    4. Update dispatch record (mark returned)
    5. Add returned products to production
    6. Return crates to inventory
    
    Returns: (dispatch, result_dict)
    """
    result = {'success': False, 'errors': [], 'warnings': []}
    
    # 1. Lock dispatch record
    try:
        dispatch = Dispatch.objects.select_for_update().get(
            id=dispatch_id,
            deleted_at__isnull=True
        )
    except Dispatch.DoesNotExist:
        result['errors'].append("Dispatch not found or deleted")
        return None, result
    
    # 2. Validate not already returned
    if dispatch.is_returned:
        result['errors'].append("Dispatch already returned")
        return None, result
    
    # 3. Validate accountability
    accountability_errors = []
    
    # Bread
    if dispatch.bread_qty > 0:
        bread_total = bread_sold + bread_returned
        if bread_total != dispatch.bread_qty:
            accountability_errors.append(
                f"Bread: sold ({bread_sold}) + returned ({bread_returned}) = {bread_total} "
                f"!= dispatched ({dispatch.bread_qty})"
            )
    
    # KDF
    if dispatch.kdf_qty > 0:
        kdf_total = kdf_sold + kdf_returned
        if kdf_total != dispatch.kdf_qty:
            accountability_errors.append(
                f"KDF: sold ({kdf_sold}) + returned ({kdf_returned}) = {kdf_total} "
                f"!= dispatched ({dispatch.kdf_qty})"
            )
    
    # Scones
    if dispatch.scones_qty > 0:
        scones_total = scones_sold + scones_returned
        if scones_total != dispatch.scones_qty:
            accountability_errors.append(
                f"Scones: sold ({scones_sold}) + returned ({scones_returned}) = {scones_total} "
                f"!= dispatched ({dispatch.scones_qty})"
            )
    
    if accountability_errors:
        result['errors'] = accountability_errors
        return None, result
    
    # 4. Calculate revenue (from Product model prices)
    try:
        bread_product = Product.objects.get(name__iexact='bread')
        kdf_product = Product.objects.get(name__iexact='kdf')
        scones_product = Product.objects.get(name__iexact='scones')
    except Product.DoesNotExist as e:
        result['errors'].append(f"Product not found: {str(e)}")
        return None, result
    
    bread_revenue = Decimal(bread_sold) * bread_product.price_per_packet
    kdf_revenue = Decimal(kdf_sold) * kdf_product.price_per_packet
    scones_revenue = Decimal(scones_sold) * scones_product.price_per_packet
    total_revenue = bread_revenue + kdf_revenue + scones_revenue
    
    # 5. Update dispatch record
    dispatch.bread_sold = bread_sold
    dispatch.bread_returned = bread_returned
    dispatch.kdf_sold = kdf_sold
    dispatch.kdf_returned = kdf_returned
    dispatch.scones_sold = scones_sold
    dispatch.scones_returned = scones_returned
    
    dispatch.bread_revenue = bread_revenue
    dispatch.kdf_revenue = kdf_revenue
    dispatch.scones_revenue = scones_revenue
    dispatch.total_revenue = total_revenue
    
    dispatch.crates_returned = crates_returned
    dispatch.crate_deficit = dispatch.crates_dispatched - crates_returned
    
    dispatch.is_returned = True
    dispatch.returned_at = timezone.now()
    dispatch.updated_by = user
    
    dispatch.save()
    
    # 6. Add returned products to Production (via utility)
    if bread_returned > 0 or kdf_returned > 0 or scones_returned > 0:
        production_result = add_returned_products(
            return_date=dispatch.dispatch_date,
            bread=bread_returned,
            kdf=kdf_returned,
            scones=scones_returned,
            user=user
        )
        
        if not production_result['success']:
            result['errors'].append(
                f"Failed to add returned products: {production_result.get('error', 'Unknown error')}"
            )
            return None, result
    
    # 7. Return crates to Inventory (via utility)
    if crates_returned > 0:
        crate_result = return_crates_atomic(
            quantity=crates_returned,
            dispatch_id=dispatch.dispatch_number,
            user=user
        )
        
        if not crate_result['success']:
            result['errors'].append(
                f"Failed to return crates: {crate_result.get('error', 'Unknown error')}"
            )
            return None, result
        
        # Warning for crate deficit
        if dispatch.crate_deficit > 0:
            result['warnings'].append(
                f"Crate deficit: {dispatch.crate_deficit} crates not returned"
            )
    
    result['success'] = True
    return dispatch, result
