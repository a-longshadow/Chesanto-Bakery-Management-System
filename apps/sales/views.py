"""
Sales Views for Chesanto Bakery Management System
Implements dispatch, sales returns, deficit tracking, and commission reports
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q, Count
from datetime import date, datetime, timedelta, time
from decimal import Decimal

from .models import (
    Salesperson, Dispatch, DispatchItem,
    SalesReturn, SalesReturnItem, DailySales
)
from .forms import (
    SalesReconciliationForm, SalesReturnItemForm,
    CrateReturnForm, CrateReturnItemForm
)
from apps.products.models import Product
from apps.accounts.models import User


# ============================================================================
# SALES DASHBOARD (UNIFIED VIEW)
# ============================================================================

@login_required
def sales_dashboard(request):
    """
    Unified sales dashboard with tabs for:
    - Dispatches
    - Sales Returns
    - Deficits
    - Commissions
    
    Features:
    - Date range filtering
    - Salesperson filtering
    - Permission-based historical access (Accountant+)
    - Quick stats
    """
    from django.core.paginator import Paginator
    from django.db.models import Sum, Count, Q
    
    # Get active tab (default: dispatches)
    active_tab = request.GET.get('tab', 'dispatches')
    
    # Permission check for historical access
    user_can_view_history = request.user.role in ['ACCOUNTANT', 'MANAGER', 'CEO', 'SUPERADMIN']
    
    # Date filtering
    today = date.today()
    if user_can_view_history:
        # Accountant+ can view any date range (default: last 30 days)
        default_start = today - timedelta(days=30)
        start_date = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
        end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    else:
        # Other roles: today only
        start_date = today.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    # Parse dates
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = today
        end_date_obj = today
    
    # Salesperson filter
    selected_salesperson = request.GET.get('salesperson', '')
    salespeople = Salesperson.objects.filter(is_active=True).order_by('name')
    
    # Base query filters
    base_filters = Q(date__gte=start_date_obj, date__lte=end_date_obj)
    if selected_salesperson:
        base_filters &= Q(salesperson_id=selected_salesperson)
    
    # Get data based on active tab
    context = {
        'active_tab': active_tab,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'selected_salesperson': selected_salesperson,
        'salespeople': salespeople,
        'today': today,
        'user_can_view_history': user_can_view_history,
    }
    
    if active_tab == 'dispatches':
        dispatches = Dispatch.objects.filter(
            base_filters,
            deleted_at__isnull=True  # Exclude soft-deleted dispatches
        ).select_related(
            'salesperson'
        ).prefetch_related('dispatchitem_set__product').order_by('-date', 'salesperson__name')
        
        paginator = Paginator(dispatches, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'dispatches': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'stats': {
                'total_dispatches': dispatches.count(),
                'total_revenue': dispatches.aggregate(Sum('expected_revenue'))['expected_revenue__sum'] or 0,
                'pending_returns': dispatches.filter(is_returned=False).count(),
            }
        })
    
    elif active_tab == 'returns':
        returns = SalesReturn.objects.filter(
            return_date__gte=start_date_obj,
            return_date__lte=end_date_obj
        ).select_related('dispatch__salesperson')
        
        if selected_salesperson:
            returns = returns.filter(dispatch__salesperson_id=selected_salesperson)
        
        returns = returns.order_by('-return_date')
        
        paginator = Paginator(returns, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'returns': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'stats': {
                'total_returns': returns.count(),
                'total_revenue': returns.aggregate(Sum('cash_returned'))['cash_returned__sum'] or 0,
                'total_commission': returns.aggregate(Sum('total_commission'))['total_commission__sum'] or 0,
            }
        })
    
    elif active_tab == 'commissions':
        # Commission aggregation by salesperson
        commission_data = SalesReturn.objects.filter(
            return_date__gte=start_date_obj,
            return_date__lte=end_date_obj
        ).values(
            'dispatch__salesperson__id',
            'dispatch__salesperson__name'
        ).annotate(
            dispatch_count=Count('id'),
            total_sales=Sum('cash_returned'),
            total_per_unit_commission=Sum('per_unit_commission'),
            total_bonus_commission=Sum('bonus_commission'),
            total_commission=Sum('total_commission')
        ).order_by('-total_commission')
        
        if selected_salesperson:
            commission_data = commission_data.filter(dispatch__salesperson__id=selected_salesperson)
        
        # Calculate totals
        commission_totals = {
            'total_sales': sum(d['total_sales'] or 0 for d in commission_data),
            'total_per_unit': sum(d['total_per_unit_commission'] or 0 for d in commission_data),
            'total_bonus': sum(d['total_bonus_commission'] or 0 for d in commission_data),
            'grand_total': sum(d['total_commission'] or 0 for d in commission_data),
        }
        
        context.update({
            'commission_data': commission_data,
            'commission_totals': commission_totals,
            'stats': {
                'total_revenue': commission_totals['total_sales'],
            }
        })
    
    return render(request, 'sales/sales_dashboard.html', context)


# ============================================================================
# DISPATCH VIEWS (Legacy - keeping for backward compatibility)
# ============================================================================

@login_required
def dispatch_list(request):
    """
    DEPRECATED: Redirect to unified sales dashboard
    Keeping for backward compatibility with old links
    """
    return redirect('sales:sales_dashboard')


@login_required
def dispatch_list_old(request):
    """
    List today's dispatches
    Filter by date and salesperson
    """
    # Get date filter (default to today)
    date_param = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
    except ValueError:
        date_obj = date.today()
    
    # Get salesperson filter (optional)
    salesperson_id = request.GET.get('salesperson')
    
    # Query dispatches
    dispatches = Dispatch.objects.filter(
        date=date_obj,
        deleted_at__isnull=True  # Exclude soft-deleted
    ).select_related('salesperson').prefetch_related('dispatchitem_set__product')
    
    if salesperson_id:
        dispatches = dispatches.filter(salesperson_id=salesperson_id)
    
    # Get all salespeople for filter dropdown
    salespeople = Salesperson.objects.filter(is_active=True)
    
    # Calculate totals
    total_dispatches = dispatches.count()
    total_expected_revenue = dispatches.aggregate(
        total=Sum('expected_revenue')
    )['total'] or Decimal('0')
    
    # Count returns
    returned_count = dispatches.filter(is_returned=True).count()
    pending_count = total_dispatches - returned_count
    
    context = {
        'date': date_obj,
        'dispatches': dispatches,
        'salespeople': salespeople,
        'selected_salesperson': salesperson_id,
        'total_dispatches': total_dispatches,
        'total_expected_revenue': total_expected_revenue,
        'returned_count': returned_count,
        'pending_count': pending_count,
    }
    
    return render(request, 'sales/dispatch_list.html', context)


@login_required
def dispatch_create(request):
    """
    Create new dispatch with real-time stock validation
    Deducts from global product and crate stock immediately
    """
    # Default to today
    date_param = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
    except ValueError:
        date_obj = date.today()
    
    if request.method == 'POST':
        salesperson_id = request.POST.get('salesperson')
        
        if not salesperson_id:
            messages.error(request, 'Please select a salesperson.')
            return render_dispatch_form(request, date_obj)
        
        try:
            salesperson = Salesperson.objects.get(id=salesperson_id, is_active=True)
            
            # Check for duplicate dispatch
            if Dispatch.objects.filter(date=date_obj, salesperson=salesperson, deleted_at__isnull=True).exists():
                messages.error(request, f'Dispatch for {salesperson.name} on {date_obj} already exists.')
                return render_dispatch_form(request, date_obj)
            
            # Collect product quantities
            products_data = []
            for key, value in request.POST.items():
                if key.startswith('product_') and key.endswith('_quantity'):
                    product_id = key.split('_')[1]
                    quantity = int(value) if value else 0
                    if quantity > 0:
                        products_data.append({'id': product_id, 'quantity': quantity})
            
            if not products_data:
                messages.error(request, 'Please enter quantities for at least one product.')
                return render_dispatch_form(request, date_obj)
            
            # Real-time stock validation and deduction
            from django.db import transaction
            with transaction.atomic():
                # Validate and deduct products one by one
                for item_data in products_data:
                    product = Product.objects.select_for_update().get(id=item_data['id'], is_active=True)
                    requested = item_data['quantity']
                    
                    if requested > product.available_stock:
                        messages.error(request, f'Insufficient stock for {product.name}: requested {requested}, available {product.available_stock}')
                        return render_dispatch_form(request, date_obj)
                    
                    # Deduct stock
                    product.available_stock -= requested
                    product.save(update_fields=['available_stock'])
                
                # Create dispatch
                dispatch = Dispatch.objects.create(
                    date=date_obj,
                    salesperson=salesperson,
                    created_by=request.user
                )
                
                # Create dispatch items
                for item_data in products_data:
                    product = Product.objects.get(id=item_data['id'])
                    DispatchItem.objects.create(
                        dispatch=dispatch,
                        product=product,
                        quantity=item_data['quantity'],
                        selling_price=product.price_per_packet,
                        expected_revenue=item_data['quantity'] * product.price_per_packet
                    )
                
                messages.success(request, f'✅ Dispatch to {salesperson.name} created successfully!')
                return redirect('sales:dispatch_assign_crates', pk=dispatch.pk)
                
        except Salesperson.DoesNotExist:
            messages.error(request, '❌ Invalid salesperson selected.')
        except Product.DoesNotExist:
            messages.error(request, '❌ Invalid product selected.')
        except Exception as e:
            messages.error(request, f'❌ Error creating dispatch: {str(e)}')
    
    return render_dispatch_form(request, date_obj)


def render_dispatch_form(request, date_obj):
    """Helper to render dispatch form with real-time stock levels"""
    salespeople = Salesperson.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    # Real-time stock from database
    products_with_stock = []
    for product in products:
        products_with_stock.append({
            'product': product,
            'available': product.available_stock,
        })
    
    context = {
        'selected_date': date_obj,
        'salespeople': salespeople,
        'products': products,
        'products_with_stock': products_with_stock,
    }
    
    return render(request, 'sales/dispatch_form.html', context)


@login_required
def dispatch_detail(request, pk):
    """
    Display dispatch details
    Shows all products dispatched and return status
    """
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('salesperson').prefetch_related(
            'dispatchitem_set__product'
        ),
        pk=pk
    )
    
    # Get items
    items = dispatch.dispatchitem_set.all()
    
    # Check if return exists
    try:
        sales_return = dispatch.sales_return
    except SalesReturn.DoesNotExist:
        sales_return = None
    
    context = {
        'dispatch': dispatch,
        'items': items,
        'sales_return': sales_return,
    }
    
    return render(request, 'sales/dispatch_detail.html', context)


@login_required
def dispatch_edit(request, pk):
    """
    Edit existing dispatch with real-time stock validation
    Adjusts global stock: adds back old quantities, deducts new ones
    """
    dispatch = get_object_or_404(Dispatch, pk=pk)
    
    # Prevent editing if already returned
    if dispatch.is_returned:
        messages.error(request, '❌ Cannot edit a dispatch that has already been returned.')
        return redirect('sales:dispatch_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Update salesperson if changed
            salesperson_id = request.POST.get('salesperson')
            if salesperson_id:
                salesperson = Salesperson.objects.get(id=salesperson_id, is_active=True)
                dispatch.salesperson = salesperson
            
            # Collect new product quantities
            products_data = []
            for key, value in request.POST.items():
                if key.startswith('product_') and key.endswith('_quantity'):
                    product_id = key.split('_')[1]
                    quantity = int(value) if value else 0
                    if quantity > 0:
                        products_data.append({'id': product_id, 'quantity': quantity})
            
            if not products_data:
                messages.error(request, 'Please enter quantities for at least one product.')
                return render_edit_dispatch_form(request, dispatch)
            
            # Get old quantities
            old_quantities = {}
            for item in dispatch.dispatchitem_set.all():
                old_quantities[item.product.id] = item.quantity
            
            # Real-time stock validation and adjustment
            from django.db import transaction
            with transaction.atomic():
                # Validate and adjust stock for each product
                for item_data in products_data:
                    product = Product.objects.select_for_update().get(id=item_data['id'], is_active=True)
                    new_quantity = item_data['quantity']
                    old_quantity = old_quantities.get(product.id, 0)
                    difference = new_quantity - old_quantity
                    
                    # Check if we have enough stock for the increase
                    if difference > 0 and difference > product.available_stock:
                        messages.error(request, f'Insufficient stock for {product.name}: need {difference} more, available {product.available_stock}')
                        return render_edit_dispatch_form(request, dispatch)
                    
                    # Adjust stock: add back old, deduct new
                    product.available_stock += old_quantity  # Add back old
                    product.available_stock -= new_quantity  # Deduct new
                    product.save(update_fields=['available_stock'])
                
                # Handle products that were removed (add back to stock)
                for product_id, old_quantity in old_quantities.items():
                    if not any(p['id'] == str(product_id) for p in products_data):
                        product = Product.objects.select_for_update().get(id=product_id)
                        product.available_stock += old_quantity
                        product.save(update_fields=['available_stock'])
                
                # Delete old dispatch items
                dispatch.dispatchitem_set.all().delete()
                
                # Create new dispatch items
                for item_data in products_data:
                    product = Product.objects.get(id=item_data['id'])
                    DispatchItem.objects.create(
                        dispatch=dispatch,
                        product=product,
                        quantity=item_data['quantity'],
                        selling_price=product.price_per_packet,
                        expected_revenue=item_data['quantity'] * product.price_per_packet
                    )
                
                # Update dispatch expected_revenue
                dispatch.calculate_expected_revenue()
                dispatch.save(update_fields=['expected_revenue', 'salesperson'])
            
            messages.success(request, f'✅ Dispatch updated successfully! New expected revenue: KES {dispatch.expected_revenue:,.2f}')
            return redirect('sales:dispatch_detail', pk=pk)
            
        except Salesperson.DoesNotExist:
            messages.error(request, '❌ Invalid salesperson selected.')
        except Product.DoesNotExist:
            messages.error(request, '❌ Invalid product selected.')
        except Exception as e:
            messages.error(request, f'❌ Error updating dispatch: {str(e)}')
    
    return render_edit_dispatch_form(request, dispatch)
def render_edit_dispatch_form(request, dispatch):
    """Helper to render edit form with existing dispatch data and real-time stock"""
    salespeople = Salesperson.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    # Get existing dispatch items
    existing_items = {}
    for item in dispatch.dispatchitem_set.all():
        existing_items[item.product.id] = item.quantity
    
    # Real-time stock from database
    products_with_stock = []
    for product in products:
        current_quantity = existing_items.get(product.id, 0)
        # Available stock includes the current dispatch quantities (since they'll be added back)
        effective_available = product.available_stock + current_quantity
        
        products_with_stock.append({
            'product': product,
            'available': effective_available,
            'current_quantity': current_quantity
        })
    
    context = {
        'dispatch': dispatch,
        'selected_date': dispatch.date,
        'salespeople': salespeople,
        'products': products,
        'products_with_stock': products_with_stock,
        'existing_items': existing_items,
        'is_edit': True,
    }
    
    return render(request, 'sales/dispatch_form.html', context)


@login_required
def dispatch_assign_crates(request, pk):
    """
    Assign crates to a newly created dispatch
    Shows a modal popup for crate assignment with validation
    """
    dispatch = get_object_or_404(Dispatch, pk=pk)
    
    # Security check: Only allow assignment for dispatches without crates assigned
    if dispatch.crates_dispatched > 0:
        messages.warning(request, 'Crates have already been assigned to this dispatch.')
        return redirect('sales:dispatch_detail', pk=pk)
    
    # Get available crates
    from apps.inventory.models import CrateStock
    crate_stock = CrateStock.get_instance()
    available_crates = crate_stock.available_crates if crate_stock else 0
    
    if request.method == 'POST':
        try:
            crates_to_assign = int(request.POST.get('crates_dispatched', 0))
            
            # Validation
            if crates_to_assign < 0:
                messages.error(request, '❌ Number of crates cannot be negative.')
                return render_crate_assignment_form(request, dispatch, available_crates)
            
            if crates_to_assign > available_crates:
                messages.error(request, f'❌ Only {available_crates} crates available. Cannot assign {crates_to_assign}.')
                return render_crate_assignment_form(request, dispatch, available_crates)
            
            # Assign crates
            from django.db import transaction
            with transaction.atomic():
                # Update dispatch
                dispatch.crates_dispatched = crates_to_assign
                dispatch.save(update_fields=['crates_dispatched'])
                
                # Update crate stock
                if crates_to_assign > 0:
                    crate_stock.dispatched_crates += crates_to_assign
                    crate_stock.available_crates -= crates_to_assign
                    crate_stock.save(update_fields=['dispatched_crates', 'available_crates'])
            
            messages.success(request, f'✅ Successfully assigned {crates_to_assign} crates to dispatch!')
            return redirect('sales:dispatch_detail', pk=pk)
            
        except ValueError:
            messages.error(request, '❌ Invalid number of crates.')
        except Exception as e:
            messages.error(request, f'❌ Error assigning crates: {str(e)}')
    
    # GET request - show crate assignment form
    return render_crate_assignment_form(request, dispatch, available_crates)


def render_crate_assignment_form(request, dispatch, available_crates):
    """Helper to render crate assignment modal"""
    context = {
        'dispatch': dispatch,
        'available_crates': available_crates,
    }
    return render(request, 'sales/dispatch_assign_crates.html', context)

@login_required
def sales_return_list(request):
    """
    List all sales returns
    Filter by date, salesperson, deficit status
    """
    # Get date filter
    date_param = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
    except ValueError:
        date_obj = date.today()
    
    # Query returns
    returns = SalesReturn.objects.filter(
        return_date=date_obj
    ).select_related('dispatch__salesperson').prefetch_related(
        'salesreturnitem_set__product'
    )
    
    # Calculate totals
    total_returns = returns.count()
    total_cash = returns.aggregate(total=Sum('cash_returned'))['total'] or Decimal('0')
    total_commission = returns.aggregate(total=Sum('total_commission'))['total'] or Decimal('0')
    
    context = {
        'date': date_obj,
        'returns': returns,
        'total_returns': total_returns,
        'total_cash': total_cash,
        'total_commission': total_commission,
    }
    
    return render(request, 'sales/sales_return_list.html', context)


@login_required
def sales_return(request, dispatch_id):
    """
    Return products from dispatch, calculate sales figures, update production
    Transfer returned units back to production, sold units become sales revenue
    """
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('salesperson').prefetch_related(
            'dispatchitem_set__product'
        ),
        pk=dispatch_id
    )
    
    # Check if already returned
    if dispatch.is_returned:
        messages.warning(request, 'This dispatch has already been returned.')
        return redirect('sales:dispatch_detail', pk=dispatch_id)
    
    if request.method == 'POST':
        try:
            from django.db import transaction
            with transaction.atomic():
                # Process returns for each product
                total_sales_revenue = Decimal('0')
                total_returned_units = 0
                
                for dispatch_item in dispatch.dispatchitem_set.all():
                    product_id = str(dispatch_item.product.id)
                    units_returned = int(request.POST.get(f'units_returned_{product_id}', 0))
                    units_damaged = int(request.POST.get(f'units_damaged_{product_id}', 0))
                    
                    # Validate
                    if units_returned + units_damaged > dispatch_item.quantity:
                        messages.error(request, f'Invalid quantities for {dispatch_item.product.name}')
                        return redirect('sales:sales_return', dispatch_id=dispatch_id)
                    
                    units_sold = dispatch_item.quantity - units_returned - units_damaged
                    
                    # Calculate sales revenue for sold units
                    sales_revenue = units_sold * dispatch_item.selling_price
                    total_sales_revenue += sales_revenue
                    
                    # Add returned units back to global product stock
                    if units_returned > 0:
                        product = Product.objects.select_for_update().get(id=dispatch_item.product.id)
                        product.available_stock += units_returned
                        product.save(update_fields=['available_stock'])
                        total_returned_units += units_returned
                    
                    # Update production: add returned units back to DailyProduction
                    from apps.production.models import DailyProduction
                    daily_production, created = DailyProduction.objects.get_or_create(
                        date=dispatch.date,
                        defaults={'created_by': request.user}
                    )
                    
                    if dispatch_item.product.name == 'Bread':
                        daily_production.bread_returned += units_returned
                    elif dispatch_item.product.name == 'KDF':
                        daily_production.kdf_returned += units_returned
                    elif dispatch_item.product.name == 'Scones':
                        daily_production.scones_returned += units_returned
                    
                    daily_production.save(update_fields=[
                        'bread_returned', 'kdf_returned', 'scones_returned',
                        'closing_bread_stock', 'closing_kdf_stock', 'closing_scones_stock'
                    ])
                
                # Handle crates
                crates_returned = int(request.POST.get('crates_returned', 0))
                if crates_returned > dispatch.crates_dispatched:
                    messages.error(request, 'Invalid crate return quantity')
                    return redirect('sales:sales_return', dispatch_id=dispatch_id)
                
                # Add back crates to CrateStock
                if crates_returned > 0:
                    from apps.inventory.models import CrateStock
                    crate_stock = CrateStock.objects.select_for_update().first()
                    if crate_stock:
                        crate_stock.available_crates += crates_returned
                        crate_stock.dispatched_crates -= crates_returned
                        crate_stock.save(update_fields=['available_crates', 'dispatched_crates'])
                
                # Create SalesReturn record
                sales_return = SalesReturn.objects.create(
                    dispatch=dispatch,
                    return_date=date.today(),
                    cash_returned=total_sales_revenue,  # Actual sales revenue
                    sales_reconciled=True,
                    crates_returned=True,
                    created_by=request.user,
                    updated_by=request.user
                )
                
                # Create SalesReturnItem records
                for dispatch_item in dispatch.dispatchitem_set.all():
                    product_id = str(dispatch_item.product.id)
                    units_returned = int(request.POST.get(f'units_returned_{product_id}', 0))
                    units_damaged = int(request.POST.get(f'units_damaged_{product_id}', 0))
                    units_sold = dispatch_item.quantity - units_returned - units_damaged
                    
                    SalesReturnItem.objects.create(
                        sales_return=sales_return,
                        product=dispatch_item.product,
                        units_dispatched=dispatch_item.quantity,
                        units_returned=units_returned,
                        units_damaged=units_damaged,
                        units_sold=units_sold,
                        selling_price=dispatch_item.selling_price,
                        gross_sales=units_sold * dispatch_item.selling_price,
                        damaged_value=units_damaged * dispatch_item.selling_price,
                        net_sales=units_sold * dispatch_item.selling_price,
                        crates_returned=0  # Simplified
                    )
                
                # Mark dispatch as returned
                dispatch.is_returned = True
                dispatch.returned_at = timezone.now()
                dispatch.save(update_fields=['is_returned', 'returned_at'])
                
                messages.success(request, f'✅ Return processed successfully. Sales revenue: KES {total_sales_revenue:,.2f}, {total_returned_units} units returned to stock.')
                return redirect('sales:dispatch_detail', pk=dispatch_id)
                
        except Exception as e:
            messages.error(request, f'❌ Error processing return: {str(e)}')
    
    # Prepare items for display
    items = []
    for dispatch_item in dispatch.dispatchitem_set.all():
        items.append({
            'dispatch_item': dispatch_item,
            'product_id': dispatch_item.product.id,
            'product_name': dispatch_item.product.name,
            'dispatched': dispatch_item.quantity,
        })
    
    context = {
        'dispatch': dispatch,
        'items': items,
    }
    
    return render(request, 'sales/sales_return_form.html', context)





@login_required
def sales_return_detail(request, pk):
    """
    Display sales return details
    Shows sold/returned/damaged breakdown and commission
    """
    sales_return = get_object_or_404(
        SalesReturn.objects.select_related(
            'dispatch__salesperson'
        ).prefetch_related(
            'salesreturnitem_set__product'
        ),
        pk=pk
    )
    
    items = sales_return.salesreturnitem_set.all()
    
    context = {
        'sales_return': sales_return,
        'items': items,
    }
    
    return render(request, 'sales/sales_return_detail.html', context)


# ============================================================================
# DEFICIT & COMMISSION REPORTS
# ============================================================================

@login_required
def deficit_list(request):
    """
    List returns with damaged items
    Shows returns that had product damage or issues
    """
    # Get date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = date.today() - timedelta(days=30)
        end_date_obj = date.today()
    
    # Query returns with damaged items
    returns_with_damage = SalesReturn.objects.filter(
        return_date__range=[start_date_obj, end_date_obj],
        salesreturnitem__units_damaged__gt=0
    ).select_related('dispatch__salesperson').distinct()
    
    # Filter by salesperson
    salesperson_id = request.GET.get('salesperson')
    if salesperson_id:
        returns_with_damage = returns_with_damage.filter(dispatch__salesperson_id=salesperson_id)
    
    # Calculate totals
    total_returns_with_damage = returns_with_damage.count()
    total_damaged_units = SalesReturnItem.objects.filter(
        sales_return__return_date__range=[start_date_obj, end_date_obj],
        units_damaged__gt=0
    ).aggregate(total=Sum('units_damaged'))['total'] or 0
    
    # Get salespeople for filter
    salespeople = Salesperson.objects.filter(is_active=True)
    
    context = {
        'returns_with_damage': returns_with_damage,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'total_returns_with_damage': total_returns_with_damage,
        'total_damaged_units': total_damaged_units,
        'salespeople': salespeople,
        'selected_salesperson': salesperson_id,
    }
    
    return render(request, 'sales/damaged_items_report.html', context)


@login_required
def commission_report(request):
    """
    Monthly commission report for all salespeople
    Shows per-unit + bonus commissions
    Exportable to CSV
    """
    # Get month filter (default to current month)
    month_param = request.GET.get('month')
    if month_param:
        try:
            year, month = month_param.split('-')
            month_obj = date(int(year), int(month), 1)
        except (ValueError, TypeError):
            month_obj = date.today().replace(day=1)
    else:
        month_obj = date.today().replace(day=1)
    
    # Calculate month range
    if month_obj.month == 12:
        next_month = month_obj.replace(year=month_obj.year + 1, month=1)
    else:
        next_month = month_obj.replace(month=month_obj.month + 1)
    
    # Query sales returns for the month
    returns = SalesReturn.objects.filter(
        return_date__gte=month_obj,
        return_date__lt=next_month
    ).select_related('dispatch__salesperson')
    
    # Group by salesperson
    commission_data = {}
    for ret in returns:
        salesperson = ret.dispatch.salesperson
        
        if salesperson.id not in commission_data:
            commission_data[salesperson.id] = {
                'salesperson': salesperson,
                'total_sales': Decimal('0'),
                'per_unit_commission': Decimal('0'),
                'bonus_commission': Decimal('0'),
                'total_commission': Decimal('0'),
                'dispatch_count': 0,
            }
        
        data = commission_data[salesperson.id]
        data['total_sales'] += ret.cash_returned
        data['per_unit_commission'] += ret.per_unit_commission
        data['bonus_commission'] += ret.bonus_commission
        data['total_commission'] += ret.total_commission
        data['dispatch_count'] += 1
    
    # Convert to list for template
    commission_list = sorted(
        commission_data.values(),
        key=lambda x: x['total_commission'],
        reverse=True
    )
    
    # Calculate grand totals
    grand_total_sales = sum(d['total_sales'] for d in commission_list)
    grand_total_commission = sum(d['total_commission'] for d in commission_list)
    
    context = {
        'month': month_obj,
        'commission_list': commission_list,
        'grand_total_sales': grand_total_sales,
        'grand_total_commission': grand_total_commission,
    }
    
    return render(request, 'sales/commission_report.html', context)


# ============================================================================
# DISPATCH DELETE (SINGLE & BULK)
# ============================================================================

@login_required
def dispatch_delete(request, pk):
    """
    Soft delete dispatch and restore stock to global inventory
    Cannot delete if already returned
    """
    dispatch = get_object_or_404(Dispatch, pk=pk)
    
    # Prevent deleting already soft-deleted dispatches
    if dispatch.deleted_at:
        messages.error(request, '❌ This dispatch has already been deleted.')
        return redirect('sales:dispatch_list')
    
    # Prevent deleting already returned dispatches
    if dispatch.is_returned:
        messages.error(request, '❌ Cannot delete a dispatch that has already been returned.')
        return redirect('sales:dispatch_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            from django.db import transaction
            with transaction.atomic():
                # Add back products to global stock
                for item in dispatch.dispatchitem_set.all():
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    product.available_stock += item.quantity
                    product.save(update_fields=['available_stock'])
                
                # Add back crates to CrateStock
                if dispatch.crates_dispatched > 0:
                    from apps.inventory.models import CrateStock
                    crate_stock = CrateStock.objects.select_for_update().first()
                    if crate_stock:
                        crate_stock.available_crates += dispatch.crates_dispatched
                        crate_stock.dispatched_crates -= dispatch.crates_dispatched
                        crate_stock.save(update_fields=['available_crates', 'dispatched_crates'])
                
                # Soft delete
                dispatch.soft_delete(request.user, "Manual deletion")
                
                salesperson_name = dispatch.salesperson.name
                expected_revenue = dispatch.expected_revenue
                messages.success(request, f'✅ Dispatch to {salesperson_name} deleted successfully. Stock and crates restored. Expected revenue: KES {expected_revenue:,.2f}')
                
                return redirect('sales:dispatch_list')
                
        except Exception as e:
            messages.error(request, f'❌ Error deleting dispatch: {str(e)}')
            return redirect('sales:dispatch_detail', pk=pk)
    
    context = {
        'dispatch': dispatch,
        'warning_message': 'This will restore products and crates back to stock and mark the dispatch as deleted.',
    }
    return render(request, 'sales/dispatch_confirm_delete.html', context)


@login_required
def dispatch_bulk_delete(request):
    """
    Bulk delete multiple dispatches with fail-fast approach
    - Stops on first error for security
    - Uses same safeguards as single delete
    - Soft deletes with full audit trail
    """
    if request.method != 'POST':
        messages.error(request, '❌ Invalid request method')
        return redirect('sales:dispatch_list')
    
    dispatch_ids = request.POST.getlist('dispatch_ids[]')
    
    if not dispatch_ids:
        messages.error(request, '❌ No dispatches selected for deletion')
        return redirect('sales:dispatch_list')
    
    # Validate and collect dispatches (exclude already deleted ones)
    dispatches = Dispatch.objects.filter(
        id__in=dispatch_ids,
        deleted_at__isnull=True  # Only not already deleted
    )
    
    if not dispatches:
        messages.error(request, '❌ No valid dispatches found for deletion')
        return redirect('sales:dispatch_list')
    
    # Check ALL safeguards BEFORE processing any deletions
    today = date.today()
    current_time = timezone.now().time()
    book_closing_time = time(21, 0)  # 9 PM
    
    validation_errors = []
    
    for dispatch in dispatches:
        # SAFEGUARD 1: Check if dispatch has a sales return
        if hasattr(dispatch, 'sales_return'):
            validation_errors.append(f'Dispatch #{dispatch.id} to {dispatch.salesperson.name} - Has sales return')
            continue
        
        # SAFEGUARD 2: Check date and time restrictions
        can_delete = False
        if request.user.role == 'SUPERADMIN':
            can_delete = True
        elif request.user.role in ['ACCOUNTANT', 'MANAGER', 'CEO']:
            if dispatch.date != today:
                try:
                    from apps.production.models import DailyProduction
                    daily_prod = DailyProduction.objects.get(date=dispatch.date)
                    can_delete = not daily_prod.is_closed
                except DailyProduction.DoesNotExist:
                    can_delete = True
            else:
                can_delete = current_time < book_closing_time
        else:
            can_delete = (dispatch.date == today and current_time < book_closing_time)
        
        if not can_delete:
            validation_errors.append(f'Dispatch #{dispatch.id} - Permission denied or books closed')
            continue
        
        # SAFEGUARD 3: Future date validation
        if dispatch.date > today:
            validation_errors.append(f'Dispatch #{dispatch.id} - Future dated dispatch')
            continue
    
    # If any validation errors, stop immediately (fail-fast)
    if validation_errors:
        for error in validation_errors[:3]:  # Show first 3 errors
            messages.error(request, f'❌ {error}')
        if len(validation_errors) > 3:
            messages.error(request, f'❌ ...and {len(validation_errors) - 3} more validation errors')
        messages.error(request, '❌ Bulk delete cancelled due to validation errors')
        return redirect('sales:dispatch_list')
    
    # All validations passed - proceed with deletions
    deleted_count = 0
    processing_errors = []
    
    from apps.production.models import DailyProduction
    from apps.inventory.models import CrateStock
    from django.db import transaction
    
    for dispatch in dispatches:
        try:
            with transaction.atomic():
                # STEP 1: Create audit snapshot
                dispatch.create_audit_snapshot(request.user, "Bulk deletion")
                
                # STEP 2: Restore products to DailyProduction
                daily_production, created = DailyProduction.objects.get_or_create(
                    date=dispatch.date,
                    defaults={'created_by': request.user}
                )
                
                for item in dispatch.dispatchitem_set.all():
                    if item.product.name == 'Bread':
                        daily_production.bread_dispatched -= item.quantity
                    elif item.product.name == 'KDF':
                        daily_production.kdf_dispatched -= item.quantity
                    elif item.product.name == 'Scones':
                        daily_production.scones_dispatched -= item.quantity
                
                daily_production.save(update_fields=['bread_dispatched', 'kdf_dispatched', 'scones_dispatched'])
                
                # STEP 3: Restore crates to CrateStock
                if dispatch.crates_dispatched > 0:
                    crate_stock = CrateStock.objects.first()
                    if crate_stock:
                        crate_stock.dispatched_crates -= dispatch.crates_dispatched
                        crate_stock.available_crates += dispatch.crates_dispatched
                        crate_stock.save(update_fields=['dispatched_crates', 'available_crates'])
                    else:
                        processing_errors.append(f'Dispatch #{dispatch.id} - CrateStock not found')
                        continue
                
                # STEP 4: Soft delete
                dispatch.soft_delete(request.user, "Bulk deletion")
                deleted_count += 1
                
        except Exception as e:
            processing_errors.append(f'Dispatch #{dispatch.id} - Error: {str(e)}')
            # Fail-fast: stop on first processing error
            break
    
    # Report results
    if deleted_count > 0:
        messages.success(request, f'✅ Successfully deleted {deleted_count} dispatch(es). Stock and crates restored.')
    
    if processing_errors:
        for error in processing_errors:
            messages.error(request, f'❌ {error}')
        messages.error(request, '❌ Bulk delete stopped due to processing errors')
    
    return redirect('sales:dispatch_list')

