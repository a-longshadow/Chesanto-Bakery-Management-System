"""
Sales App - Delete Views
SUPERADMIN-only views for dependency-aware dispatch deletion.

These views are part of the Data Management feature (FEATURE_DATA_MANAGEMENT.md).
They allow correction of erroneous data entries while maintaining audit trail.

WARNING: These views bypass normal immutability guards.
Only SUPERADMIN role can access these endpoints.

NOTE: Returns (SalesReturn) are NEVER deletable. They are immutable financial
records. The only way to undo a return is via Full System Reset.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import superadmin_required
from apps.core.services import (
    delete_dispatch,
    can_delete_dispatch,
    DataManagementError,
)
from .models import SalesDispatch


@superadmin_required
@require_http_methods(["GET", "POST"])
def dispatch_delete(request, pk: int):
    """
    Delete a sales dispatch with dependency checking.
    
    URL: /sales/dispatch/<pk>/delete/
    
    GET: Show confirmation page with dependency info
    POST: Execute deletion if confirmed and no dependencies
    
    Template: sales/dispatch_delete.html
    
    Context:
        - dispatch: The SalesDispatch record
        - can_delete: Boolean - whether deletion is allowed
        - blocking_reason: String explaining why blocked (if any)
        - items: List of dispatch items that will have stock restored
    """
    dispatch = get_object_or_404(SalesDispatch, pk=pk)
    
    # Check if deletion is allowed
    can_delete, blocking_reason = can_delete_dispatch(dispatch)
    
    # Get dispatch items for display
    items = list(dispatch.items.select_related('product').all())
    
    if request.method == 'POST':
        if not can_delete:
            messages.error(request, f"Cannot delete: {blocking_reason}")
            return redirect('sales:dispatch_detail', pk=pk)
        
        # Get reason from form
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for deletion.")
            return render(request, 'sales/dispatch_delete.html', {
                'dispatch': dispatch,
                'can_delete': can_delete,
                'blocking_reason': blocking_reason,
                'items': items,
                'reason_required': True,
            })
        
        try:
            result = delete_dispatch(dispatch, request.user, reason)
            
            # Format success message
            msg_parts = [
                f"✓ Dispatch {result['data']['dispatch_number']} deleted.",
            ]
            if result['data']['products_restored']:
                msg_parts.append(f"Restored {len(result['data']['products_restored'])} product(s) to stock.")
            if result['data']['crates_restored'] and result['data']['crates_restored'] != '0':
                msg_parts.append(f"Restored {result['data']['crates_restored']} crate(s) to inventory.")
            
            messages.success(request, " ".join(msg_parts))
            return redirect('sales:dispatch_list')
            
        except DataManagementError as e:
            messages.error(request, f"Delete failed: {str(e)}")
            return redirect('sales:dispatch_detail', pk=pk)
    
    # GET request - show confirmation page
    return render(request, 'sales/dispatch_delete.html', {
        'dispatch': dispatch,
        'can_delete': can_delete,
        'blocking_reason': blocking_reason,
        'items': items,
    })
