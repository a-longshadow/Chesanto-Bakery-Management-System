"""
Sales App Views
Handles dispatch creation and returns
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Dispatch, Salesperson
# 🔴 FOUNDATION REBUILD - Temporarily commented out (apps deleted)
# from .utils import create_dispatch_atomic, return_dispatch_atomic, validate_dispatch_stock
# from apps.inventory.utils import get_available_crates


@login_required
@transaction.atomic
def dispatch_create(request):
    """Create new dispatch"""
    if request.method == 'POST':
        # Extract form data
        salesperson_id = request.POST.get('salesperson')
        dispatch_date = request.POST.get('dispatch_date')
        bread_qty = int(request.POST.get('bread_qty', 0))
        kdf_qty = int(request.POST.get('kdf_qty', 0))
        scones_qty = int(request.POST.get('scones_qty', 0))
        crates_qty = int(request.POST.get('crates_qty', 0))
        
        # Create dispatch atomically
        dispatch, result = create_dispatch_atomic(
            salesperson_id=salesperson_id,
            dispatch_date=dispatch_date,
            bread_qty=bread_qty,
            kdf_qty=kdf_qty,
            scones_qty=scones_qty,
            crates_qty=crates_qty,
            user=request.user
        )
        
        if result['success']:
            # Show warnings (if any)
            for warning in result.get('warnings', []):
                messages.warning(request, warning)
            
            messages.success(request, f"Dispatch {dispatch.dispatch_number} created successfully")
            return redirect('sales:dispatch_detail', pk=dispatch.pk)
        else:
            # Show errors
            for error in result['errors']:
                messages.error(request, error)
    
    # GET request: show form
    salespeople = Salesperson.objects.filter(is_active=True).order_by('name')
    available_crates = get_available_crates()
    
    context = {
        'salespeople': salespeople,
        'available_crates': available_crates,
        'today': timezone.now().date(),
    }
    
    return render(request, 'sales/dispatch_create.html', context)


@login_required
def dispatch_detail(request, pk):
    """View dispatch details"""
    dispatch = get_object_or_404(Dispatch, pk=pk, deleted_at__isnull=True)
    
    context = {
        'dispatch': dispatch,
    }
    
    return render(request, 'sales/dispatch_detail.html', context)


@login_required
@transaction.atomic
def dispatch_return(request, pk):
    """Process dispatch return"""
    dispatch = get_object_or_404(Dispatch, pk=pk, deleted_at__isnull=True)
    
    # Prevent returning already returned dispatch
    if dispatch.is_returned:
        messages.error(request, "This dispatch has already been returned")
        return redirect('sales:dispatch_detail', pk=pk)
    
    if request.method == 'POST':
        # Extract return data
        bread_sold = int(request.POST.get('bread_sold', 0))
        bread_returned = int(request.POST.get('bread_returned', 0))
        kdf_sold = int(request.POST.get('kdf_sold', 0))
        kdf_returned = int(request.POST.get('kdf_returned', 0))
        scones_sold = int(request.POST.get('scones_sold', 0))
        scones_returned = int(request.POST.get('scones_returned', 0))
        crates_returned = int(request.POST.get('crates_returned', 0))
        
        # Process return atomically
        returned_dispatch, result = return_dispatch_atomic(
            dispatch_id=dispatch.id,
            bread_sold=bread_sold,
            bread_returned=bread_returned,
            kdf_sold=kdf_sold,
            kdf_returned=kdf_returned,
            scones_sold=scones_sold,
            scones_returned=scones_returned,
            crates_returned=crates_returned,
            user=request.user
        )
        
        if result['success']:
            # Show warnings (if any)
            for warning in result.get('warnings', []):
                messages.warning(request, warning)
            
            messages.success(
                request,
                f"Dispatch {dispatch.dispatch_number} returned successfully. "
                f"Total revenue: KES {returned_dispatch.total_revenue:,.2f}"
            )
            return redirect('sales:dispatch_detail', pk=dispatch.pk)
        else:
            # Show errors
            for error in result['errors']:
                messages.error(request, error)
    
    # GET request: show return form
    context = {
        'dispatch': dispatch,
    }
    
    return render(request, 'sales/dispatch_return.html', context)


@login_required
def dispatch_list(request):
    """List all dispatches with filters"""
    # Get filters from query params
    salesperson_id = request.GET.get('salesperson')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_returned = request.GET.get('is_returned')
    
    # Base queryset
    dispatches = Dispatch.objects.filter(deleted_at__isnull=True).select_related('salesperson')
    
    # Apply filters
    if salesperson_id:
        dispatches = dispatches.filter(salesperson_id=salesperson_id)
    
    if date_from:
        dispatches = dispatches.filter(dispatch_date__gte=date_from)
    
    if date_to:
        dispatches = dispatches.filter(dispatch_date__lte=date_to)
    
    if is_returned == 'yes':
        dispatches = dispatches.filter(is_returned=True)
    elif is_returned == 'no':
        dispatches = dispatches.filter(is_returned=False)
    
    # Pagination
    paginator = Paginator(dispatches, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Context
    salespeople = Salesperson.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'salespeople': salespeople,
        'filters': {
            'salesperson': salesperson_id,
            'date_from': date_from,
            'date_to': date_to,
            'is_returned': is_returned,
        }
    }
    
    return render(request, 'sales/dispatch_list.html', context)


@login_required
def salesperson_list(request):
    """List all salespeople"""
    salespeople = Salesperson.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(salespeople, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'sales/salesperson_list.html', context)


@login_required
@transaction.atomic
def salesperson_create(request):
    """Create new salesperson"""
    if request.method == 'POST':
        name = request.POST.get('name')
        salesperson_type = request.POST.get('salesperson_type')
        phone = request.POST.get('phone', '')
        
        try:
            salesperson = Salesperson.objects.create(
                name=name,
                salesperson_type=salesperson_type,
                phone=phone,
                created_by=request.user
            )
            messages.success(request, f"Salesperson '{name}' created successfully")
            return redirect('sales:salesperson_list')
        except Exception as e:
            messages.error(request, f"Error creating salesperson: {str(e)}")
    
    context = {
        'salesperson_types': Salesperson.SALESPERSON_TYPE_CHOICES,
    }
    
    return render(request, 'sales/salesperson_create.html', context)
