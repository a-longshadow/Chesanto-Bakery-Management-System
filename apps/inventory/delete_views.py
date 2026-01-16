"""
Inventory App - Delete Views
SUPERADMIN-only views for dependency-aware purchase deletion.

These views are part of the Data Management feature (FEATURE_DATA_MANAGEMENT.md).
They allow correction of erroneous data entries while maintaining audit trail.

WARNING: These views bypass normal immutability guards.
Only SUPERADMIN role can access these endpoints.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import superadmin_required
from apps.core.services import (
    delete_purchase,
    can_delete_purchase,
    DataManagementError,
)
from .routing import get_purchases_model, get_details_model, ITEM_DETAILS_MODELS, INVENTORY_ITEMS


def _get_purchase_or_404(inventory_item_id: int, purchase_id: int):
    """
    Get a purchase instance from the correct per-item table.
    
    Args:
        inventory_item_id: Item ID (1-23)
        purchase_id: Primary key of the purchase record
    
    Returns:
        Purchase instance
    
    Raises:
        Http404: If item ID invalid or purchase not found
    """
    if inventory_item_id not in ITEM_DETAILS_MODELS:
        raise Http404(f"Invalid inventory item ID: {inventory_item_id}")
    
    PurchasesModel = get_purchases_model(inventory_item_id)
    return get_object_or_404(PurchasesModel, pk=purchase_id)


@superadmin_required
@require_http_methods(["GET", "POST"])
def purchase_delete(request, inventory_item_id: int, purchase_id: int):
    """
    Delete an inventory purchase with dependency checking.
    
    URL: /inventory/item/<item_id>/purchase/<purchase_id>/delete/
    
    GET: Show confirmation page with dependency info
    POST: Execute deletion if confirmed and no dependencies
    
    Template: inventory/purchase_delete.html
    
    Context:
        - purchase: The purchase record
        - item: The inventory item details
        - inventory_item_id: The item ID for URL routing
        - can_delete: Boolean - whether deletion is allowed
        - blocking_reason: String explaining why blocked (if any)
    """
    purchase = _get_purchase_or_404(inventory_item_id, purchase_id)
    DetailsModel = get_details_model(inventory_item_id)
    item = DetailsModel.objects.get(pk=1)
    
    # Get unit from INVENTORY_ITEMS tuple (id, name, is_ingredient, unit)
    item_info = next((i for i in INVENTORY_ITEMS if i[0] == inventory_item_id), None)
    unit = item_info[3] if item_info else ''
    
    # Check if deletion is allowed
    can_delete, blocking_reason = can_delete_purchase(purchase)
    
    if request.method == 'POST':
        if not can_delete:
            messages.error(request, f"Cannot delete: {blocking_reason}")
            return redirect('inventory:purchase_history', inventory_item_id=inventory_item_id)
        
        # Get reason from form
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for deletion.")
            return render(request, 'inventory/purchase_delete.html', {
                'purchase': purchase,
                'item': item,
                'inventory_item_id': inventory_item_id,
                'can_delete': can_delete,
                'blocking_reason': blocking_reason,
                'reason_required': True,
            })
        
        try:
            result = delete_purchase(purchase, request.user, reason, inventory_item_id=inventory_item_id)
            messages.success(
                request,
                f"✓ Purchase {result['data']['purchase_number']} deleted. "
                f"Stock adjusted: {result['data']['stock_before']} → {result['data']['stock_after']} {unit}"
            )
            return redirect('inventory:purchase_history', inventory_item_id=inventory_item_id)
            
        except DataManagementError as e:
            messages.error(request, f"Delete failed: {str(e)}")
            return redirect('inventory:item_detail', inventory_item_id=inventory_item_id)
    
    # Calculate stock after deletion for display
    stock_after_delete = item.current_stock - purchase.quantity_purchased
    
    # GET request - show confirmation page
    return render(request, 'inventory/purchase_delete.html', {
        'purchase': purchase,
        'item': item,
        'unit': unit,
        'inventory_item_id': inventory_item_id,
        'can_delete': can_delete,
        'blocking_reason': blocking_reason,
        'stock_after_delete': stock_after_delete,
    })
