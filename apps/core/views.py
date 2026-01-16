"""
Core App - Views
Data management views for Primary Superadmin only.

These views are part of the Data Management feature (FEATURE_DATA_MANAGEMENT.md).
Full System Reset provides a way to wipe all transaction data when
individual record deletion is impractical.

WARNING: These views are extremely dangerous and can cause data loss.
Only Primary Superadmin can access these endpoints.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from functools import wraps

from .services import (
    execute_full_reset,
    get_reset_preview,
    DataManagementError,
)


def primary_superadmin_required(view_func):
    """
    Only Primary Superadmin can access.
    
    Use for: Full system reset and other dangerous operations.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not getattr(request.user, 'is_primary_superadmin', False):
            messages.error(
                request,
                'Access denied. This area is restricted to Primary Superadmin only.'
            )
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@primary_superadmin_required
@require_http_methods(["GET", "POST"])
def full_reset(request):
    """
    Full system reset page.
    
    URL: /admin/data-management/full-reset/
    
    GET: Show confirmation page with record counts
    POST: Execute reset if checkboxes confirmed and reason provided
    
    Template: core/full_reset.html
    
    Context:
        - preview: Dict with record counts by category
        - total_records: Total count of records to delete
    """
    # Get preview of what will be deleted
    preview = get_reset_preview()
    
    # Calculate totals
    total_records = (
        preview['sales']['dispatches'] +
        preview['sales']['returns'] +
        preview['sales']['movements'] +
        preview['production']['batches'] +
        preview['production']['ingredient_deductions'] +
        preview['production']['waste_logs'] +
        preview['production']['movements'] +
        preview['inventory']['purchases'] +
        preview['inventory']['outputs'] +
        preview['inventory']['alerts']
    )
    
    if request.method == 'POST':
        # Validate checkboxes
        confirm_delete = request.POST.get('confirm_delete') == 'on'
        confirm_balances = request.POST.get('confirm_balances') == 'on'
        reason = request.POST.get('reason', '').strip()
        
        errors = []
        if not confirm_delete:
            errors.append("You must confirm that ALL transaction data will be deleted.")
        if not confirm_balances:
            errors.append("You must confirm that you are prepared to enter inventory opening balances.")
        if not reason:
            errors.append("Please provide a reason for the reset.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'core/full_reset.html', {
                'preview': preview,
                'total_records': total_records,
                'submitted_reason': reason,
                'confirm_delete_checked': confirm_delete,
                'confirm_balances_checked': confirm_balances,
            })
        
        try:
            result = execute_full_reset(request.user, reason)
            messages.success(
                request,
                f"✓ System reset complete. Deleted {result['total_deleted']} records. "
                f"Reset {result['inventory_items_reset']} inventory items and "
                f"{result['product_stocks_reset']} product stocks to zero."
            )
            return redirect('core:reset_complete')
            
        except PermissionError as e:
            messages.error(request, str(e))
            return redirect('home')
            
        except (ValueError, DataManagementError) as e:
            messages.error(request, f"Reset failed: {str(e)}")
            return render(request, 'core/full_reset.html', {
                'preview': preview,
                'total_records': total_records,
                'submitted_reason': reason,
                'confirm_delete_checked': confirm_delete,
                'confirm_balances_checked': confirm_balances,
            })
    
    # GET request - show confirmation page
    return render(request, 'core/full_reset.html', {
        'preview': preview,
        'total_records': total_records,
    })


@primary_superadmin_required
def reset_complete(request):
    """
    Post-reset page with next steps.
    
    URL: /admin/data-management/reset-complete/
    
    Template: core/reset_complete.html
    """
    return render(request, 'core/reset_complete.html')
