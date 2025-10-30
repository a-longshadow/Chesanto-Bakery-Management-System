"""
Sales Views for Chesanto Bakery Management System
Implements dispatch, sales returns, deficit tracking, and commission reports
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q, Count
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import (
    Salesperson, Dispatch, DispatchItem,
    SalesReturn, SalesReturnItem, DailySales
)
from apps.products.models import Product
from apps.accounts.models import User


# ============================================================================
# DISPATCH VIEWS
# ============================================================================

@login_required
def dispatch_list(request):
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
        date=date_obj
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
    Create new multi-product dispatch
    Dynamic form with product rows
    """
    # Default to today
    date_param = request.GET.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
    except ValueError:
        date_obj = date.today()
    
    if request.method == 'POST':
        # Get form data
        salesperson_id = request.POST.get('salesperson')
        crates_dispatched = request.POST.get('crates_dispatched', 0)
        
        # Get product quantities (multiple products)
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        
        # Validation
        if not salesperson_id:
            messages.error(request, 'Please select a salesperson.')
            return render_dispatch_form(request, date_obj)
        
        if not product_ids or not any(quantities):
            messages.error(request, 'Please add at least one product.')
            return render_dispatch_form(request, date_obj)
        
        try:
            salesperson = Salesperson.objects.get(id=salesperson_id, is_active=True)
            crates_dispatched = int(crates_dispatched) if crates_dispatched else 0
            
            # Check for duplicate dispatch
            if Dispatch.objects.filter(date=date_obj, salesperson=salesperson).exists():
                messages.error(request, f'Dispatch for {salesperson.name} on {date_obj} already exists.')
                return render_dispatch_form(request, date_obj)
            
            # Create dispatch
            dispatch = Dispatch.objects.create(
                date=date_obj,
                salesperson=salesperson,
                crates_dispatched=crates_dispatched,
                created_by=request.user
            )
            
            # Create dispatch items
            for product_id, quantity in zip(product_ids, quantities):
                if not quantity or int(quantity) <= 0:
                    continue
                
                product = Product.objects.get(id=product_id, is_active=True)
                DispatchItem.objects.create(
                    dispatch=dispatch,
                    product=product,
                    quantity=int(quantity)
                )
            
            messages.success(request, f'Dispatch to {salesperson.name} created successfully.')
            return redirect('sales:dispatch_list')
            
        except Salesperson.DoesNotExist:
            messages.error(request, 'Invalid salesperson selected.')
        except Product.DoesNotExist:
            messages.error(request, 'Invalid product selected.')
        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating dispatch: {str(e)}')
    
    # GET request - show form
    return render_dispatch_form(request, date_obj)


def render_dispatch_form(request, date_obj):
    """Helper to render dispatch form with context"""
    salespeople = Salesperson.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    context = {
        'date': date_obj,
        'salespeople': salespeople,
        'products': products,
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


# ============================================================================
# SALES RETURN VIEWS
# ============================================================================

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
    
    # Filter by deficit status
    deficit_filter = request.GET.get('deficit')
    if deficit_filter == 'with':
        returns = returns.filter(revenue_deficit__gt=0)
    elif deficit_filter == 'without':
        returns = returns.filter(revenue_deficit=0)
    
    # Calculate totals
    total_returns = returns.count()
    total_cash = returns.aggregate(total=Sum('cash_returned'))['total'] or Decimal('0')
    total_deficit = returns.aggregate(total=Sum('revenue_deficit'))['total'] or Decimal('0')
    total_commission = returns.aggregate(total=Sum('total_commission'))['total'] or Decimal('0')
    
    context = {
        'date': date_obj,
        'returns': returns,
        'total_returns': total_returns,
        'total_cash': total_cash,
        'total_deficit': total_deficit,
        'total_commission': total_commission,
        'deficit_filter': deficit_filter,
    }
    
    return render(request, 'sales/sales_return_list.html', context)


@login_required
def sales_return_create(request, dispatch_id):
    """
    Create sales return for a dispatch
    - Enter sold, returned, damaged quantities
    - Auto-calculate commission
    - Detect deficits
    """
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('salesperson').prefetch_related(
            'dispatchitem_set__product'
        ),
        pk=dispatch_id
    )
    
    # Check if return already exists
    if hasattr(dispatch, 'sales_return'):
        messages.warning(request, 'Sales return already exists for this dispatch.')
        return redirect('sales:return_detail', pk=dispatch.sales_return.pk)
    
    if request.method == 'POST':
        try:
            # Get form data
            return_date = request.POST.get('return_date', date.today())
            return_time = request.POST.get('return_time')
            crates_returned = int(request.POST.get('crates_returned', 0))
            cash_returned = Decimal(request.POST.get('cash_returned', 0))
            deficit_reason = request.POST.get('deficit_reason', '')
            
            # Convert date string to date object
            if isinstance(return_date, str):
                return_date = datetime.strptime(return_date, '%Y-%m-%d').date()
            
            # Create sales return
            sales_return = SalesReturn.objects.create(
                dispatch=dispatch,
                return_date=return_date,
                return_time=return_time if return_time else None,
                crates_returned=crates_returned,
                cash_returned=cash_returned,
                deficit_reason=deficit_reason,
                created_by=request.user,
                updated_by=request.user
            )
            
            # Create sales return items for each dispatched product
            dispatch_items = dispatch.dispatchitem_set.all()
            
            for item in dispatch_items:
                product_id = str(item.product.id)
                units_returned = int(request.POST.get(f'units_returned_{product_id}', 0))
                units_damaged = int(request.POST.get(f'units_damaged_{product_id}', 0))
                
                SalesReturnItem.objects.create(
                    sales_return=sales_return,
                    product=item.product,
                    units_dispatched=item.quantity,
                    units_returned=units_returned,
                    units_damaged=units_damaged
                )
            
            # Recalculate to get final commission
            sales_return.calculate_commission()
            sales_return.save()
            
            # Check for deficit alerts
            if sales_return.revenue_deficit > 500:
                messages.warning(
                    request,
                    f'Revenue deficit of KES {sales_return.revenue_deficit:,.2f} detected. '
                    f'CEO has been notified.'
                )
            elif sales_return.revenue_deficit > 0:
                messages.info(
                    request,
                    f'Revenue deficit of KES {sales_return.revenue_deficit:,.2f} recorded.'
                )
            
            messages.success(request, 'Sales return recorded successfully.')
            return redirect('sales:return_detail', pk=sales_return.pk)
            
        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating sales return: {str(e)}')
    
    # GET request - show form
    items = dispatch.dispatchitem_set.all()
    
    context = {
        'dispatch': dispatch,
        'items': items,
        'today': date.today(),
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
    List all deficits with filtering
    Color-coded alerts (>KES 500 red, >KES 0 orange)
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
    
    # Query returns with deficits
    deficits = SalesReturn.objects.filter(
        return_date__range=[start_date_obj, end_date_obj],
        revenue_deficit__gt=0
    ).select_related('dispatch__salesperson').order_by('-revenue_deficit')
    
    # Filter by salesperson
    salesperson_id = request.GET.get('salesperson')
    if salesperson_id:
        deficits = deficits.filter(dispatch__salesperson_id=salesperson_id)
    
    # Calculate totals
    total_deficit = deficits.aggregate(total=Sum('revenue_deficit'))['total'] or Decimal('0')
    high_deficits = deficits.filter(revenue_deficit__gt=500).count()
    
    # Get salespeople for filter
    salespeople = Salesperson.objects.filter(is_active=True)
    
    context = {
        'deficits': deficits,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'total_deficit': total_deficit,
        'high_deficits': high_deficits,
        'salespeople': salespeople,
        'selected_salesperson': salesperson_id,
    }
    
    return render(request, 'sales/deficit_list.html', context)


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
        data['total_sales'] += ret.cash_returned + ret.revenue_deficit
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

