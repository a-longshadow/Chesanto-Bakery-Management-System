"""
Inventory App - ACID-Compliant Atomic Utilities
Bank-ledger approach: All stock changes via atomic transactions with row locking.

This module provides:
- create_purchase_atomic(): Record purchase, update stock, update last price
- create_output_atomic(): Record consumption, deduct stock (indirect costs only)
- deduct_ingredients_atomic(): Bulk deduction for Production app
- deduct_crates_atomic(): Crate deduction for Sales dispatch
- return_crates_atomic(): Crate return for Sales returns

All functions:
- Use @transaction.atomic for ACID compliance
- Use select_for_update() for row locking
- Validate positive values only
- Create StockAlerts when minimum_stock_level is breached
- Return structured dicts (not model instances) for cross-app safety

USAGE:
    from apps.inventory.utils import create_purchase_atomic
    
    result = create_purchase_atomic(
        inventory_item_id=1,
        supplier_name='Supplier ABC',
        quantity_purchased=Decimal('50.0000'),
        unit_price=Decimal('85.0000'),
        purchase_date=date.today(),
        requested_by_user=request.user
    )
    
    if result['success']:
        print(f"Purchase created: {result['data']['purchase_number']}")
    else:
        print(f"Error: {result['error']}")
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .routing import (
    get_details_model,
    get_purchases_model,
    get_outputs_model,
    is_indirect_cost,
    is_ingredient,
    get_item_name,
    get_item_unit,
    INVENTORY_ITEMS,
)
from .models.alerts import StockAlert


# ============================================================================
# CONSTANTS
# ============================================================================

MAX_BACKDATE_DAYS = 30  # Maximum days in past for purchase/output dates


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _generate_purchase_number(item_name: str, purchase_date: date, sequence: int) -> str:
    """Generate unique purchase number: PUR-ITEMNAME-YYYY-MM-DD-NNN"""
    clean_name = item_name.upper().replace(' ', '_').replace('-', '_')[:15]
    date_str = purchase_date.strftime('%Y-%m-%d')
    return f"PUR-{clean_name}-{date_str}-{sequence:03d}"


def _generate_output_number(item_name: str, consumption_date: date, sequence: int) -> str:
    """Generate unique output number: OUT-ITEMNAME-YYYY-MM-DD-NNN"""
    clean_name = item_name.upper().replace(' ', '_').replace('-', '_')[:15]
    date_str = consumption_date.strftime('%Y-%m-%d')
    return f"OUT-{clean_name}-{date_str}-{sequence:03d}"


def _validate_date(input_date: date, field_name: str) -> None:
    """
    Validate date is not future and within backdate limit.
    
    Raises:
        ValidationError: If date is invalid
    """
    today = date.today()
    
    if input_date > today:
        raise ValidationError({field_name: f"{field_name} cannot be in the future"})
    
    min_date = today - timedelta(days=MAX_BACKDATE_DAYS)
    if input_date < min_date:
        raise ValidationError({field_name: f"{field_name} cannot be more than {MAX_BACKDATE_DAYS} days in the past"})


def _check_and_create_alert(item_details, inventory_item_id: int, triggered_by: str, 
                            triggered_by_user) -> Optional[Dict]:
    """
    Check if stock is below minimum and create StockAlert if needed.
    
    Args:
        item_details: ItemXXDetails instance (already locked)
        inventory_item_id: Integer 1-23
        triggered_by: String ('production', 'manual_output', 'sales')
        triggered_by_user: User instance
        
    Returns:
        Dict with alert info if created, None otherwise
    """
    if item_details.current_stock < item_details.minimum_stock_level:
        alert = StockAlert.create_alert(
            inventory_item_id=inventory_item_id,
            item_name=item_details.name,
            current_stock=item_details.current_stock,
            minimum_stock=item_details.minimum_stock_level,
            triggered_by=triggered_by,
            triggered_by_user=triggered_by_user
        )
        return {
            'inventory_item_id': inventory_item_id,
            'item_name': item_details.name,
            'alert_level': alert.alert_level,
            'current_stock': str(item_details.current_stock),
            'minimum_stock': str(item_details.minimum_stock_level),
        }
    return None


# ============================================================================
# PUBLIC UTILITIES
# ============================================================================

@transaction.atomic
def create_purchase_atomic(
    inventory_item_id: int,
    supplier_name: str,
    quantity_purchased: Decimal,
    unit_price: Decimal,
    purchase_date: date,
    requested_by_user,
    notes: str = ''
) -> Dict[str, Any]:
    """
    Create purchase for specific inventory item atomically.
    
    Routes to correct per-item table based on inventory_item_id.
    Updates ItemXXDetails: current_stock, last_purchase_unit_price, last_purchase_date.
    
    Args:
        inventory_item_id: Integer 1-23 (which item)
        supplier_name: String (supplier/vendor name, optional)
        quantity_purchased: Decimal (amount purchased, must be > 0)
        unit_price: Decimal (price per unit, must be > 0)
        purchase_date: Date (when purchased, not future, max 30 days backdate)
        requested_by_user: User instance (who created purchase)
        notes: String (optional purchase notes)
    
    Returns:
        {'success': True, 'data': {'purchase_number': str, 'new_stock': str}}
        OR
        {'success': False, 'error': str}
    
    Raises:
        ValidationError: If validation fails (propagated to caller)
    """
    try:
        # Validate inputs
        if quantity_purchased <= Decimal('0'):
            raise ValidationError({'quantity_purchased': "Quantity must be greater than 0"})
        
        if unit_price <= Decimal('0'):
            raise ValidationError({'unit_price': "Unit price must be greater than 0"})
        
        _validate_date(purchase_date, 'purchase_date')
        
        # Get model classes via routing
        ItemDetailsModel = get_details_model(inventory_item_id)
        ItemPurchasesModel = get_purchases_model(inventory_item_id)
        
        # Lock item details row (singleton - pk=1)
        # Each ItemXXDetails table has exactly one row with pk=1
        item = ItemDetailsModel.objects.select_for_update().get(pk=1)
        
        # Calculate total cost with rounding
        total_cost = (quantity_purchased * unit_price).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
        
        # Generate purchase number
        today_count = ItemPurchasesModel.objects.filter(
            purchase_date=purchase_date
        ).count()
        purchase_number = _generate_purchase_number(
            item.name, purchase_date, today_count + 1
        )
        
        # Create purchase record (immutable)
        purchase = ItemPurchasesModel.objects.create(
            purchase_number=purchase_number,
            supplier_name=supplier_name or '',
            purchase_date=purchase_date,
            quantity_purchased=quantity_purchased,
            unit_price=unit_price,
            total_cost=total_cost,
            purchased_by=requested_by_user,
            notes=notes or ''
        )
        
        # Update stock and price
        item.current_stock += quantity_purchased
        item.last_purchase_unit_price = unit_price
        item.last_purchase_date = timezone.now()
        item.updated_by = requested_by_user
        item.save()  # current_value auto-calculated in save()
        
        return {
            'success': True,
            'data': {
                'purchase_number': purchase_number,
                'purchase_id': purchase.id,
                'new_stock': str(item.current_stock),
                'new_value': str(item.current_value),
                'total_cost': str(total_cost),
            }
        }
        
    except ItemDetailsModel.DoesNotExist:
        return {
            'success': False,
            'error': f"Item {inventory_item_id} has not been initialized. "
                    f"Run 'python manage.py seed_inventory' first."
        }
    except ValidationError as e:
        return {
            'success': False,
            'error': str(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


@transaction.atomic
def create_output_atomic(
    inventory_item_id: int,
    quantity_consumed: Decimal,
    consumption_date: date,
    requested_by_user,
    date_range_start: Optional[date] = None,
    date_range_end: Optional[date] = None,
    description: str = ''
) -> Dict[str, Any]:
    """
    Record manual consumption for indirect cost item atomically.
    
    ONLY for indirect costs (items 16-23). Ingredients (1-15) are tracked
    via Production app, not via outputs table.
    
    Args:
        inventory_item_id: Integer 16-23 (indirect costs only)
        quantity_consumed: Decimal (must be > 0 and ≤ current_stock)
        consumption_date: Date (not future, max 30 days backdate)
        requested_by_user: User instance
        date_range_start: Optional Date (period start for reporting)
        date_range_end: Optional Date (period end for reporting)
        description: Optional String (memo)
    
    Returns:
        {'success': True, 'data': {...}, 'alerts': [...]}
        OR
        {'success': False, 'error': str}
    """
    try:
        # Validate item is indirect cost
        if not is_indirect_cost(inventory_item_id):
            raise ValidationError({
                'inventory_item_id': f"Item {inventory_item_id} is not an indirect cost. "
                                    f"Only items 16-23 have outputs tables."
            })
        
        # Validate inputs
        if quantity_consumed <= Decimal('0'):
            raise ValidationError({'quantity_consumed': "Quantity must be greater than 0"})
        
        _validate_date(consumption_date, 'consumption_date')
        
        # Get model classes via routing
        ItemDetailsModel = get_details_model(inventory_item_id)
        ItemOutputsModel = get_outputs_model(inventory_item_id)
        
        # Lock item details row
        item = ItemDetailsModel.objects.select_for_update().get(pk=1)
        
        # Validate sufficient stock
        if quantity_consumed > item.current_stock:
            raise ValidationError({
                'quantity_consumed': f"Cannot consume {quantity_consumed} - "
                                    f"only {item.current_stock} available"
            })
        
        # Generate output number
        today_count = ItemOutputsModel.objects.filter(
            consumption_date=consumption_date
        ).count()
        output_number = _generate_output_number(
            item.name, consumption_date, today_count + 1
        )
        
        # Create output record (immutable)
        output = ItemOutputsModel.objects.create(
            output_number=output_number,
            consumption_date=consumption_date,
            quantity_consumed=quantity_consumed,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            description=description or '',
            consumed_by=requested_by_user
        )
        
        # Deduct from stock
        item.current_stock -= quantity_consumed
        item.updated_by = requested_by_user
        item.save()  # current_value auto-calculated
        
        # Check for stock alerts
        alerts = []
        alert = _check_and_create_alert(
            item, inventory_item_id, 'manual_output', requested_by_user
        )
        if alert:
            alerts.append(alert)
        
        return {
            'success': True,
            'data': {
                'output_number': output_number,
                'output_id': output.id,
                'new_stock': str(item.current_stock),
                'new_value': str(item.current_value),
            },
            'alerts': alerts
        }
        
    except ItemDetailsModel.DoesNotExist:
        return {
            'success': False,
            'error': f"Item {inventory_item_id} has not been initialized."
        }
    except ValidationError as e:
        return {
            'success': False,
            'error': str(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


@transaction.atomic
def deduct_ingredients_atomic(
    ingredients_list: List[Dict[str, Any]],
    requested_by_app: str = 'production',
    requested_by_user = None
) -> Dict[str, Any]:
    """
    Deduct multiple ingredients atomically (for Production app).
    
    All-or-nothing: If ANY ingredient has insufficient stock, 
    the entire transaction rolls back.
    
    Args:
        ingredients_list: List of dicts with 'inventory_item_id' and 'quantity'
            Example: [{'inventory_item_id': 1, 'quantity': Decimal('5.0')}, ...]
        requested_by_app: String ('production', etc.) for alert tracking
        requested_by_user: User instance
    
    Returns:
        {
            'success': True,
            'data': {'deducted_items': int, 'items': [...]},
            'alerts': [...]
        }
        OR
        {'success': False, 'error': str}
    
    Example:
        result = deduct_ingredients_atomic(
            [
                {'inventory_item_id': 1, 'quantity': Decimal('5.0')},  # Flour
                {'inventory_item_id': 3, 'quantity': Decimal('0.5')},  # Sugar
                {'inventory_item_id': 7, 'quantity': Decimal('0.05')}, # Yeast
            ],
            requested_by_app='production',
            requested_by_user=request.user
        )
    """
    try:
        if not ingredients_list:
            raise ValidationError("No ingredients provided")
        
        deducted_items = []
        alerts = []
        
        for ingredient in ingredients_list:
            inventory_item_id = ingredient.get('inventory_item_id')
            quantity = Decimal(str(ingredient.get('quantity', 0)))
            
            # Validate ingredient is actually an ingredient (not indirect cost)
            if not is_ingredient(inventory_item_id):
                raise ValidationError(
                    f"Item {inventory_item_id} is not an ingredient. "
                    f"Use create_output_atomic() for indirect costs."
                )
            
            if quantity <= Decimal('0'):
                raise ValidationError(
                    f"Quantity for item {inventory_item_id} must be > 0"
                )
            
            # Get model and lock row
            ItemDetailsModel = get_details_model(inventory_item_id)
            item = ItemDetailsModel.objects.select_for_update().get(pk=1)
            
            # Validate sufficient stock
            if quantity > item.current_stock:
                item_name = get_item_name(inventory_item_id)
                raise ValidationError(
                    f"Insufficient stock for {item_name}: "
                    f"need {quantity}, have {item.current_stock}"
                )
            
            # Deduct stock
            item.current_stock -= quantity
            item.updated_by = requested_by_user
            item.save()
            
            deducted_items.append({
                'inventory_item_id': inventory_item_id,
                'item_name': item.name,
                'quantity_deducted': str(quantity),
                'new_stock': str(item.current_stock),
            })
            
            # Check for alerts
            alert = _check_and_create_alert(
                item, inventory_item_id, requested_by_app, requested_by_user
            )
            if alert:
                alerts.append(alert)
        
        return {
            'success': True,
            'data': {
                'deducted_items': len(deducted_items),
                'items': deducted_items,
            },
            'alerts': alerts
        }
        
    except ValidationError as e:
        return {
            'success': False,
            'error': str(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


@transaction.atomic
def deduct_crates_atomic(
    quantity: Decimal,
    requested_by_app: str = 'sales',
    requested_by_user = None
) -> Dict[str, Any]:
    """
    Deduct crates from inventory atomically (for Sales dispatch).
    
    Crates are Item ID 16 in the inventory system.
    
    Args:
        quantity: Decimal (number of crates to deduct, must be > 0)
        requested_by_app: String ('sales', etc.) for alert tracking
        requested_by_user: User instance
    
    Returns:
        {'success': True, 'data': {'new_stock': str}, 'alerts': [...]}
        OR
        {'success': False, 'error': str}
    """
    CRATES_ITEM_ID = 16
    
    try:
        if quantity <= Decimal('0'):
            raise ValidationError("Quantity must be greater than 0")
        
        # Get crates model and lock row
        ItemDetailsModel = get_details_model(CRATES_ITEM_ID)
        item = ItemDetailsModel.objects.select_for_update().get(pk=1)
        
        # Validate sufficient crates
        if quantity > item.current_stock:
            raise ValidationError(
                f"Insufficient crates: need {quantity}, have {item.current_stock}"
            )
        
        # Deduct crates
        item.current_stock -= quantity
        item.updated_by = requested_by_user
        item.save()
        
        # Check for alerts
        alerts = []
        alert = _check_and_create_alert(
            item, CRATES_ITEM_ID, requested_by_app, requested_by_user
        )
        if alert:
            alerts.append(alert)
        
        return {
            'success': True,
            'data': {
                'quantity_deducted': str(quantity),
                'new_stock': str(item.current_stock),
            },
            'alerts': alerts
        }
        
    except ItemDetailsModel.DoesNotExist:
        return {
            'success': False,
            'error': "Crates (Item 16) has not been initialized."
        }
    except ValidationError as e:
        return {
            'success': False,
            'error': str(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


@transaction.atomic
def return_crates_atomic(
    quantity: Decimal,
    requested_by_app: str = 'sales',
    requested_by_user = None
) -> Dict[str, Any]:
    """
    Return crates to inventory atomically (for Sales returns).
    
    Crates are Item ID 16 in the inventory system.
    
    Args:
        quantity: Decimal (number of crates to return, must be > 0)
        requested_by_app: String ('sales', etc.) for tracking
        requested_by_user: User instance
    
    Returns:
        {'success': True, 'data': {'new_stock': str}}
        OR
        {'success': False, 'error': str}
    """
    CRATES_ITEM_ID = 16
    
    try:
        if quantity <= Decimal('0'):
            raise ValidationError("Quantity must be greater than 0")
        
        # Get crates model and lock row
        ItemDetailsModel = get_details_model(CRATES_ITEM_ID)
        item = ItemDetailsModel.objects.select_for_update().get(pk=1)
        
        # Add back crates
        item.current_stock += quantity
        item.updated_by = requested_by_user
        item.save()
        
        return {
            'success': True,
            'data': {
                'quantity_returned': str(quantity),
                'new_stock': str(item.current_stock),
            }
        }
        
    except ItemDetailsModel.DoesNotExist:
        return {
            'success': False,
            'error': "Crates (Item 16) has not been initialized."
        }
    except ValidationError as e:
        return {
            'success': False,
            'error': str(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


# ============================================================================
# READ-ONLY UTILITIES (No transactions needed)
# ============================================================================

def get_all_stock_levels(include_ingredients=True, include_indirect_costs=True) -> List[Dict]:
    """
    Get current stock levels for all items.
    
    Args:
        include_ingredients: Include items 1-15
        include_indirect_costs: Include items 16-23
        
    Returns:
        List of dicts with item info and stock levels
    """
    results = []
    
    for item_id, name, is_ing, unit in INVENTORY_ITEMS:
        if is_ing and not include_ingredients:
            continue
        if not is_ing and not include_indirect_costs:
            continue
        
        try:
            ItemDetailsModel = get_details_model(item_id)
            item = ItemDetailsModel.objects.get(pk=1)
            results.append({
                'inventory_item_id': item_id,
                'name': item.name,
                'unit': unit,
                'is_ingredient': is_ing,
                'current_stock': str(item.current_stock),
                'minimum_stock_level': str(item.minimum_stock_level),
                'last_purchase_unit_price': str(item.last_purchase_unit_price),
                'current_value': str(item.current_value),
                'is_low_stock': item.is_low_stock,
                'is_out_of_stock': item.is_out_of_stock,
            })
        except ItemDetailsModel.DoesNotExist:
            results.append({
                'inventory_item_id': item_id,
                'name': name,
                'unit': unit,
                'is_ingredient': is_ing,
                'error': 'Not initialized',
            })
    
    return results


def get_item_stock(inventory_item_id: int) -> Dict[str, Any]:
    """
    Get current stock level for a specific item.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        Dict with item info and stock level
    """
    try:
        ItemDetailsModel = get_details_model(inventory_item_id)
        item = ItemDetailsModel.objects.get(pk=1)
        
        return {
            'success': True,
            'data': {
                'inventory_item_id': inventory_item_id,
                'name': item.name,
                'current_stock': str(item.current_stock),
                'minimum_stock_level': str(item.minimum_stock_level),
                'last_purchase_unit_price': str(item.last_purchase_unit_price),
                'last_purchase_date': item.last_purchase_date,
                'current_value': str(item.current_value),
                'is_low_stock': item.is_low_stock,
                'is_out_of_stock': item.is_out_of_stock,
            }
        }
    except ItemDetailsModel.DoesNotExist:
        return {
            'success': False,
            'error': f"Item {inventory_item_id} has not been initialized."
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }
