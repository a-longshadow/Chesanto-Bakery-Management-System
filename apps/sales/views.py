"""
Sales App Views - Bank Ledger Philosophy
IMMUTABLE RECORDS: No edit/delete for dispatches and returns
"""
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import SalesDispatch, SalesDispatchItem, SalesReturn, SalesReturnItem
from .services import DispatchService, ReturnService, SalesReportService, CommissionService
from apps.accounts.models import User
from apps.core.services import can_delete_dispatch
from apps.accounts.decorators import (
    admin_required, 
    dispatch_required, 
    sales_view_required, 
    gate_log_required,
    salesman_access_required,
    salesman_own_data_only,
    role_required,
    SALES_VIEW_ROLES,
    GATE_LOG_ROLES,
)


PAGINATION_CHOICES = [10, 50, 100, 500, 1000]
DEFAULT_PAGE_SIZE = 50


def get_page_size(request):
    """Get page size from request, with validation"""
    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PAGE_SIZE))
        if per_page in PAGINATION_CHOICES:
            return per_page
    except (ValueError, TypeError):
        pass
    return DEFAULT_PAGE_SIZE


@sales_view_required
def dashboard(request):
    """Sales dashboard with summary stats"""
    today = timezone.now().date()
    
    # All pending returns (not just today - dispatches that haven't been returned)
    pending_returns = SalesDispatch.objects.filter(
        is_returned=False
    ).select_related('salesperson').order_by('-dispatch_date', '-created_at')
    
    # Today's dispatches count
    today_dispatches = SalesDispatch.objects.filter(dispatch_date=today).count()
    
    # Returns processed today
    returned_today = SalesReturn.objects.filter(
        return_date=today
    ).select_related('dispatch', 'dispatch__salesperson')
    
    # Calculate totals
    total_sold_today = returned_today.aggregate(
        total=Sum('total_revenue')
    )['total'] or Decimal('0')
    
    units_sold_today = SalesReturnItem.objects.filter(
        sales_return__return_date=today
    ).aggregate(
        total=Sum('qty_sold')
    )['total'] or 0
    
    # Recent activity
    recent_dispatches = SalesDispatch.objects.select_related(
        'salesperson'
    ).order_by('-created_at')[:10]
    
    context = {
        'today': today,
        'pending_returns': pending_returns,
        'pending_count': pending_returns.count(),
        'today_dispatches': today_dispatches,
        'returned_count': returned_today.count(),
        'total_sold_today': total_sold_today,
        'units_sold_today': units_sold_today,
        'recent_dispatches': recent_dispatches,
    }
    
    return render(request, 'sales/dashboard.html', context)


@sales_view_required
def dispatch_list(request):
    """List all dispatches with filters"""
    # Pagination settings
    PAGINATION_CHOICES = [10, 25, 50, 100, 500]
    DEFAULT_PAGE_SIZE = 25
    
    # Get page size from request
    try:
        per_page = int(request.GET.get('per_page', DEFAULT_PAGE_SIZE))
        if per_page not in PAGINATION_CHOICES:
            per_page = DEFAULT_PAGE_SIZE
    except (ValueError, TypeError):
        per_page = DEFAULT_PAGE_SIZE
    
    # Get filters
    salesperson_id = request.GET.get('salesperson')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    
    # Base queryset
    dispatches = SalesDispatch.objects.select_related(
        'salesperson'
    ).prefetch_related('items').order_by('-dispatch_date', '-created_at')
    
    # Apply filters
    if salesperson_id:
        dispatches = dispatches.filter(salesperson_id=salesperson_id)
    
    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)
    
    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)
    
    # Get IDs of dispatches that have returns
    returned_dispatch_ids = SalesReturn.objects.values_list('dispatch_id', flat=True)
    
    if status == 'pending':
        dispatches = dispatches.exclude(pk__in=returned_dispatch_ids)
    elif status == 'returned':
        dispatches = dispatches.filter(pk__in=returned_dispatch_ids)
    
    # Annotate with return status
    for dispatch in dispatches:
        dispatch.has_return = dispatch.pk in returned_dispatch_ids
    
    # Pagination with configurable page size
    paginator = Paginator(dispatches, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get salespeople for filter dropdown
    salespeople = User.objects.filter(role=User.Role.SALESMAN, is_active=True).order_by('first_name')
    
    context = {
        'dispatches': page_obj,
        'page_obj': page_obj,
        'salespeople': salespeople,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': paginator.count,
        'filters': {
            'salesperson': salesperson_id,
            'date_from': date_from,
            'date_to': date_to,
            'status': status,
        }
    }
    
    return render(request, 'sales/dispatch_list.html', context)


@dispatch_required
@transaction.atomic
def dispatch_create(request):
    """Create a new dispatch - IMMUTABLE once created"""
    # Prepare context data (needed for both GET and POST with errors)
    salespeople = User.objects.filter(role=User.Role.SALESMAN, is_active=True).order_by('first_name')
    available_products = DispatchService.get_available_products()
    
    # Get available crates from inventory using service method
    crates_info = DispatchService.get_available_crates()
    
    # Form data for preserving values on error
    form_data = {
        'salesperson': '',
        'dispatch_date': timezone.now().date().isoformat(),
        'crates_out': 0,
        'notes': '',
        'product_quantities': {},  # {product_id: quantity}
    }
    
    if request.method == 'POST':
        # Extract and preserve form data
        form_data['salesperson'] = request.POST.get('salesperson', '')
        form_data['dispatch_date'] = request.POST.get('dispatch_date', timezone.now().date().isoformat())
        form_data['crates_out'] = int(request.POST.get('crates_out', 0) or 0)
        form_data['notes'] = request.POST.get('notes', '')
        
        # Extract product quantities as list of dicts
        items = []
        for key, value in request.POST.items():
            if key.startswith('product_') and value:
                product_id = int(key.replace('product_', ''))
                qty = int(value)
                form_data['product_quantities'][product_id] = qty
                if qty > 0:
                    items.append({'product_id': product_id, 'quantity': qty})
        
        if not items:
            messages.error(request, "Please select at least one product to dispatch.")
        else:
            try:
                dispatch, result = DispatchService.create_dispatch(
                    salesperson_id=int(form_data['salesperson']),
                    dispatch_date=form_data['dispatch_date'],
                    items=items,
                    crates=form_data['crates_out'],
                    user=request.user
                )
                
                if result['success']:
                    # Show warnings if any
                    for warning in result.get('warnings', []):
                        messages.warning(request, warning)
                    messages.success(request, f"Dispatch {dispatch.dispatch_number} created successfully!")
                    return redirect('sales:dispatch_detail', pk=dispatch.pk)
                else:
                    for error in result.get('errors', []):
                        messages.error(request, error)
            except ValueError as e:
                messages.error(request, str(e))
        
        # On error, re-render form with preserved data (don't redirect)
        context = {
            'salespeople': salespeople,
            'available_products': available_products,
            'crates_info': crates_info,
            'today': form_data['dispatch_date'],
            'form_data': form_data,
            'product_quantities_json': json.dumps(form_data['product_quantities']),
        }
        return render(request, 'sales/dispatch_form.html', context)
    
    # GET: Show form
    context = {
        'salespeople': salespeople,
        'available_products': available_products,
        'crates_info': crates_info,
        'today': timezone.now().date().isoformat(),
        'form_data': form_data,
        'product_quantities_json': json.dumps(form_data['product_quantities']),
    }
    
    return render(request, 'sales/dispatch_form.html', context)


@login_required
def dispatch_detail(request, pk):
    """
    View dispatch details.
    
    Access:
    - SUPERADMIN, ADMIN, PRODUCT_MANAGER, DEPT_HEAD, DISPATCH: Can view any dispatch
    - SALESMAN: Can only view their OWN dispatches
    - Others: Access denied
    """
    from apps.accounts.decorators import SALES_VIEW_ROLES
    
    dispatch = get_object_or_404(
        SalesDispatch.objects.select_related('salesperson', 'created_by')
        .prefetch_related('items__product'),
        pk=pk
    )
    
    # Check access permissions
    user_role = request.user.role
    
    # Higher roles can view any dispatch
    if user_role not in SALES_VIEW_ROLES:
        # SALESMAN can only view their own dispatches
        if user_role == 'SALESMAN':
            if dispatch.salesperson != request.user:
                messages.error(request, 'You can only view your own dispatches.')
                return redirect('sales:my_dispatches')
        else:
            # Other roles (SECURITY, BASIC_USER) cannot access dispatch details
            messages.error(
                request,
                f'Access denied. Your role ({request.user.get_role_display()}) '
                f'does not have permission to access this page.'
            )
            return redirect('home')
    
    # Check if has return
    try:
        sales_return = dispatch.sales_return
        dispatch.has_return = True
    except SalesReturn.DoesNotExist:
        dispatch.has_return = False
    
    # Check if SUPERADMIN can delete this dispatch
    can_delete = False
    blocking_reason = ''
    if user_role == 'SUPERADMIN':
        can_delete, blocking_reason = can_delete_dispatch(dispatch)
    
    context = {
        'dispatch': dispatch,
        'can_delete': can_delete,
        'blocking_reason': blocking_reason,
        'is_superadmin': user_role == 'SUPERADMIN',
    }
    
    return render(request, 'sales/dispatch_detail.html', context)


@dispatch_required
@transaction.atomic
def dispatch_return(request, pk):
    """Process a return for a dispatch - IMMUTABLE once created"""
    dispatch = get_object_or_404(
        SalesDispatch.objects.select_related('salesperson')
        .prefetch_related('items__product'),
        pk=pk
    )
    
    # Check if already returned
    try:
        existing_return = dispatch.sales_return
        if existing_return:
            messages.error(request, "This dispatch has already been returned.")
            return redirect('sales:dispatch_detail', pk=pk)
    except SalesReturn.DoesNotExist:
        pass
    
    dispatch_items = list(dispatch.items.all())
    
    if request.method == 'POST':
        crates_returned = int(request.POST.get('crates_returned', 0))
        notes = request.POST.get('notes', '')
        
        # Calculate crate deficit - any missing crates are lost
        crates_lost = max(0, dispatch.crates_dispatched - crates_returned)
        crates_damaged = 0  # We don't track damaged crates separately in this simple form
        
        # Build items data for the service (now includes line_discount)
        items = []
        for item in dispatch_items:
            returned_qty = int(request.POST.get(f'returned_{item.id}', 0))
            sold_qty = item.quantity - returned_qty
            # Get line discount (default 0 if not provided)
            line_discount = Decimal(request.POST.get(f'discount_{item.id}', '0') or '0')
            items.append({
                'product_id': item.product_id,
                'qty_sold': sold_qty,
                'qty_returned': returned_qty,
                'line_discount': line_discount,
            })
        
        # Calculate commission based on salesperson's rate (after discounts)
        total_revenue = sum(
            (Decimal(str(i['qty_sold'])) * dispatch_items[idx].unit_price) - i['line_discount']
            for idx, i in enumerate(items)
        )
        commission_amount = None
        if dispatch.salesperson.commission_rate:
            commission_rate = Decimal(str(dispatch.salesperson.commission_rate)) / 100
            commission_amount = total_revenue * commission_rate
        
        try:
            sales_return, result = ReturnService.process_return(
                dispatch_id=dispatch.pk,
                items=items,
                crates_returned=crates_returned,
                crates_lost=crates_lost,
                crates_damaged=crates_damaged,
                notes=notes,
                commission_amount=commission_amount,
                user=request.user
            )
            
            if result['success']:
                messages.success(
                    request, 
                    f"Return processed successfully! Revenue: KES {sales_return.total_revenue:,.2f}"
                )
                return redirect('sales:dispatch_detail', pk=dispatch.pk)
            else:
                for error in result.get('errors', []):
                    messages.error(request, error)
        except ValueError as e:
            messages.error(request, str(e))
    
    context = {
        'dispatch': dispatch,
        'dispatch_items': dispatch_items,
    }
    
    return render(request, 'sales/return_form.html', context)


@dispatch_required
@transaction.atomic
def update_crate_status(request, pk):
    """Update crate reconciliation status"""
    sales_return = get_object_or_404(
        SalesReturn.objects.select_related('dispatch'),
        pk=pk
    )
    
    if request.method == 'POST':
        # The model has crates_marked_lost and crates_marked_damaged as the mutable fields
        # When both are True, crates_reconciled property returns True
        mark_reconciled = 'crates_reconciled' in request.POST
        notes = request.POST.get('crate_notes', '')
        
        # Update the mutable crate status fields
        # Setting both to True marks as reconciled
        SalesReturn.objects.filter(pk=pk).update(
            crates_marked_lost=mark_reconciled,
            crates_marked_damaged=mark_reconciled,
            notes=notes
        )
        
        messages.success(request, "Crate status updated successfully!")
        return redirect('sales:dispatch_detail', pk=sales_return.dispatch.pk)
    
    context = {
        'return': sales_return,
    }
    
    return render(request, 'sales/crate_status_form.html', context)


@admin_required
def sales_report(request):
    """Sales performance report"""
    # Get filters
    salesperson_id = request.GET.get('salesperson')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build base queryset
    returns = SalesReturn.objects.select_related('dispatch', 'dispatch__salesperson')
    
    if salesperson_id:
        returns = returns.filter(dispatch__salesperson_id=salesperson_id)
    
    if date_from:
        returns = returns.filter(return_date__gte=date_from)
    
    if date_to:
        returns = returns.filter(return_date__lte=date_to)
    
    # Summary stats
    summary = returns.aggregate(
        total_revenue=Sum('total_revenue'),
        total_dispatches=Count('dispatch', distinct=True),
        total_returns=Count('id'),
    )
    
    # Units sold
    items = SalesReturnItem.objects.filter(sales_return__in=returns)
    units_sold = items.aggregate(total=Sum('qty_sold'))['total'] or 0
    summary['total_units_sold'] = units_sold
    
    # Get salespeople for filter
    salespeople = User.objects.filter(role=User.Role.SALESMAN, is_active=True).order_by('first_name')
    
    # Sales by salesperson
    salesperson_summary = returns.values(
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ).annotate(
        dispatches=Count('dispatch', distinct=True),
        revenue=Sum('total_revenue'),
        commission=Sum('commission_amount'),
    ).order_by('-revenue')
    
    # Add units sold per salesperson
    for item in salesperson_summary:
        item['units_sold'] = SalesReturnItem.objects.filter(
            sales_return__dispatch__salesperson__first_name=item['dispatch__salesperson__first_name'],
            sales_return__dispatch__salesperson__last_name=item['dispatch__salesperson__last_name'],
            sales_return__in=returns
        ).aggregate(total=Sum('qty_sold'))['total'] or 0
    
    # Paginate the salesperson summary
    per_page = get_page_size(request)
    salesperson_list = list(salesperson_summary)
    paginator = Paginator(salesperson_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'summary': summary,
        'salespeople': salespeople,
        'salesperson_summary': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': len(salesperson_list),
        'filters': {
            'salesperson': salesperson_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'sales/sales_report.html', context)


@admin_required
def commission_report(request):
    """Commission tracking report with pagination"""
    # Get pagination settings
    per_page = get_page_size(request)
    
    # Get filters
    salesperson_id = request.GET.get('salesperson')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build base queryset
    returns = SalesReturn.objects.select_related('dispatch', 'dispatch__salesperson')
    
    if salesperson_id:
        returns = returns.filter(dispatch__salesperson_id=salesperson_id)
    
    if date_from:
        returns = returns.filter(return_date__gte=date_from)
    
    if date_to:
        returns = returns.filter(return_date__lte=date_to)
    
    # Summary
    summary = returns.aggregate(
        total_commission=Sum('commission_amount'),
        total_revenue=Sum('total_revenue'),
        total_returns=Count('id'),
    )
    
    # Calculate effective rate
    if summary['total_revenue'] and summary['total_commission']:
        summary['effective_rate'] = (summary['total_commission'] / summary['total_revenue']) * 100
    else:
        summary['effective_rate'] = 0
    
    # Commission by salesperson
    salespeople = User.objects.filter(role=User.Role.SALESMAN, is_active=True).order_by('first_name')
    commission_data = []
    
    for salesperson in salespeople:
        sp_returns = returns.filter(dispatch__salesperson=salesperson)
        if sp_returns.exists():
            totals = sp_returns.aggregate(
                total_revenue=Sum('total_revenue'),
                total_commission=Sum('commission_amount'),
                return_count=Count('id'),
            )
            commission_data.append({
                'salesperson': salesperson,
                'total_revenue': totals['total_revenue'] or Decimal('0'),
                'total_commission': totals['total_commission'] or Decimal('0'),
                'return_count': totals['return_count'],
            })
    
    # Paginate recent returns
    all_returns = returns.order_by('-return_date', '-created_at')
    total_count = all_returns.count()
    paginator = Paginator(all_returns, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'summary': summary,
        'salespeople': salespeople,
        'commission_data': commission_data,
        'recent_returns': page_obj,
        'page_obj': page_obj,
        'total_count': total_count,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'filters': {
            'salesperson': salesperson_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'sales/commission_report.html', context)


# API Endpoints

@sales_view_required
def api_stock_levels(request):
    """API: Get current stock levels for dispatch form"""
    products = DispatchService.get_available_products()
    
    data = [
        {
            'id': p.id,
            'name': p.name,
            'available_stock': p.available_stock,
            'unit_price': str(p.unit_price),
        }
        for p in products
    ]
    
    return JsonResponse({'products': data})


@dispatch_required
def api_commission_preview(request):
    """API: Preview commission calculation"""
    total_revenue = Decimal(request.GET.get('revenue', '0'))
    salesperson_id = request.GET.get('salesperson_id')
    
    if salesperson_id:
        try:
            salesperson = User.objects.get(pk=salesperson_id)
            commission = CommissionService.calculate_commission(
                salesperson=salesperson,
                total_revenue=total_revenue
            )
            return JsonResponse({
                'commission': str(commission),
                'rate': str(salesperson.commission_rate or 0),
            })
        except User.DoesNotExist:
            pass
    
    return JsonResponse({'commission': '0', 'rate': '0'})


# ============================================================================
# SALESMAN-SPECIFIC VIEWS (Own data only)
# ============================================================================

@salesman_own_data_only
def my_dispatches(request):
    """
    SALESMAN view: See only their own dispatches.
    Filtered automatically to current user's dispatches.
    """
    dispatches = SalesDispatch.objects.filter(
        salesperson=request.user
    ).select_related('salesperson').order_by('-dispatch_date', '-created_at')
    
    # Filters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if status:
        dispatches = dispatches.filter(status=status)
    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)
    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)
    
    # Pagination
    per_page = get_page_size(request)
    paginator = Paginator(dispatches, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'dispatches': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': dispatches.count(),
        'status_choices': SalesDispatch.Status.choices,
        'filters': {
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'sales/my_dispatches.html', context)


@salesman_own_data_only
def my_commissions(request):
    """
    SALESMAN view: See only their own commission data.
    Shows completed returns with commission amounts for current user only.
    """
    # Get returns for this salesperson only
    returns = SalesReturn.objects.filter(
        dispatch__salesperson=request.user
    ).select_related('dispatch').order_by('-return_date', '-created_at')
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        returns = returns.filter(return_date__gte=date_from)
    if date_to:
        returns = returns.filter(return_date__lte=date_to)
    
    # Summary for this salesperson
    summary = returns.aggregate(
        total_revenue=Sum('total_revenue'),
        total_commission=Sum('commission_amount'),
        total_returns=Count('id'),
    )
    
    # Calculate effective rate
    if summary['total_revenue'] and summary['total_commission']:
        summary['effective_rate'] = (summary['total_commission'] / summary['total_revenue']) * 100
    else:
        summary['effective_rate'] = 0
    
    # Pagination
    per_page = get_page_size(request)
    paginator = Paginator(returns, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'returns': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': returns.count(),
        'summary': summary,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'sales/my_commissions.html', context)


# ============================================================================
# SECURITY VIEWS (Gate log - NO financial data)
# ============================================================================

@gate_log_required
def gate_log(request):
    """
    SECURITY view: Track dispatches leaving/returning.
    Shows dispatch status, salesperson, date/time - NO financial data.
    """
    dispatches = SalesDispatch.objects.select_related(
        'salesperson'
    ).order_by('-dispatch_date', '-created_at')
    
    # Filters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    salesperson_id = request.GET.get('salesperson')
    
    if status:
        dispatches = dispatches.filter(status=status)
    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)
    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)
    if salesperson_id:
        dispatches = dispatches.filter(salesperson_id=salesperson_id)
    
    # Get salespeople for filter dropdown
    salespeople = User.objects.filter(
        role=User.Role.SALESMAN, 
        is_active=True
    ).order_by('first_name')
    
    # Pagination
    per_page = get_page_size(request)
    paginator = Paginator(dispatches, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary stats (counts only, no financials) - use fresh queryset, not filtered
    today = timezone.now().date()
    today_stats = {
        # Total dispatches that LEFT today (regardless of whether they've returned)
        'dispatched_out': SalesDispatch.objects.filter(
            dispatch_date=today
        ).count(),
        # Dispatches that RETURNED today (regardless of when they went out)
        'returned': SalesDispatch.objects.filter(
            returned_at__date=today,
            status=SalesDispatch.Status.RETURNED
        ).count(),
        # ALL dispatches currently out (not yet returned)
        'pending': SalesDispatch.objects.filter(
            status=SalesDispatch.Status.DISPATCHED
        ).count(),
    }
    
    context = {
        'dispatches': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': dispatches.count(),
        'status_choices': SalesDispatch.Status.choices,
        'salespeople': salespeople,
        'today_stats': today_stats,
        'filters': {
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'salesperson': salesperson_id,
        }
    }
    
    return render(request, 'sales/gate_log.html', context)
