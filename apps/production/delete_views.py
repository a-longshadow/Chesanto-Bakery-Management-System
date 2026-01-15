"""
Production App - Delete Views
SUPERADMIN-only views for dependency-aware batch deletion.

These views are part of the Data Management feature (FEATURE_DATA_MANAGEMENT.md).
They allow correction of erroneous data entries while maintaining audit trail.

WARNING: These views bypass normal immutability guards.
Only SUPERADMIN role can access these endpoints.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import superadmin_required
from apps.core.services import (
    delete_batch,
    can_delete_batch,
    DataManagementError,
)
from .models import ProductionBatch


@superadmin_required
@require_http_methods(["GET", "POST"])
def batch_delete(request, batch_id: int):
    """
    Delete a production batch with dependency checking.
    
    URL: /production/batch/<batch_id>/delete/
    
    GET: Show confirmation page with dependency info
    POST: Execute deletion if confirmed and no dependencies
    
    Template: production/batch_delete.html
    
    Context:
        - batch: The ProductionBatch record
        - can_delete: Boolean - whether deletion is allowed
        - blocking_reason: String explaining why blocked (if any)
        - ingredients: List of ingredient deductions that will be restored
    """
    batch = get_object_or_404(ProductionBatch, pk=batch_id)
    
    # Check if deletion is allowed
    can_delete, blocking_reason = can_delete_batch(batch)
    
    # Get ingredient deductions for display
    ingredients = list(batch.ingredient_deductions.select_related().all())
    
    if request.method == 'POST':
        if not can_delete:
            messages.error(request, f"Cannot delete: {blocking_reason}")
            return redirect('production:batch_detail', batch_id=batch_id)
        
        # Get reason from form
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for deletion.")
            return render(request, 'production/batch_delete.html', {
                'batch': batch,
                'can_delete': can_delete,
                'blocking_reason': blocking_reason,
                'ingredients': ingredients,
                'reason_required': True,
            })
        
        try:
            result = delete_batch(batch, request.user, reason)
            
            # Format success message
            msg_parts = [
                f"✓ Batch {result['data']['batch_number']} deleted.",
                f"Product stock: {result['data']['product_stock_before']} → {result['data']['product_stock_after']}",
            ]
            if result['data']['ingredients_restored']:
                msg_parts.append(f"Restored {len(result['data']['ingredients_restored'])} ingredient(s) to inventory.")
            
            messages.success(request, " ".join(msg_parts))
            return redirect('production:batch_list')
            
        except DataManagementError as e:
            messages.error(request, f"Delete failed: {str(e)}")
            return redirect('production:batch_detail', batch_id=batch_id)
    
    # GET request - show confirmation page
    return render(request, 'production/batch_delete.html', {
        'batch': batch,
        'can_delete': can_delete,
        'blocking_reason': blocking_reason,
        'ingredients': ingredients,
    })
