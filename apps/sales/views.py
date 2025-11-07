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
        dispatches = Dispatch.objects.filter(base_filters).select_related(
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
                'total_deficits': returns.aggregate(Sum('revenue_deficit'))['revenue_deficit__sum'] or 0,
            }
        })
    
    elif active_tab == 'deficits':
        # Include ALL returns (even with no deficit) to show complete picture
        deficits = SalesReturn.objects.filter(
            return_date__gte=start_date_obj,
            return_date__lte=end_date_obj
        ).select_related('dispatch__salesperson')
        
        if selected_salesperson:
            deficits = deficits.filter(dispatch__salesperson_id=selected_salesperson)
        
        # Order by severity: revenue deficit first, then crate deficit
        deficits = deficits.order_by('-revenue_deficit', '-crates_deficit', '-return_date')
        
        paginator = Paginator(deficits, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calculate aggregates
        revenue_deficit_total = deficits.aggregate(Sum('revenue_deficit'))['revenue_deficit__sum'] or 0
        crate_deficit_total = deficits.aggregate(Sum('crates_deficit'))['crates_deficit__sum'] or 0
        critical_count = deficits.filter(
            Q(revenue_deficit__gt=500) | Q(crates_deficit__gt=5)
        ).count()
        
        context.update({
            'deficits': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'deficit_total': revenue_deficit_total,
            'crate_deficit_total': crate_deficit_total,
            'critical_count': critical_count,
            'resolved_count': deficits.filter(deficit_resolved=True).count(),
            'stats': {
                'total_deficits': revenue_deficit_total,
                'total_crate_deficits': crate_deficit_total,
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
    Validates against production stock levels
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
        dispatch_date = request.POST.get('date')
        crates_dispatched = request.POST.get('crates_dispatched', 0)
        
        # Validation
        if not salesperson_id:
            messages.error(request, 'Please select a salesperson.')
            return render_dispatch_form(request, date_obj)
        
        try:
            salesperson = Salesperson.objects.get(id=salesperson_id, is_active=True)
            crates_dispatched = int(crates_dispatched) if crates_dispatched else 0
            
            # Parse date
            if dispatch_date:
                date_obj = datetime.strptime(dispatch_date, '%Y-%m-%d').date()
            
            # Check for duplicate dispatch
            if Dispatch.objects.filter(date=date_obj, salesperson=salesperson).exists():
                messages.error(request, f'Dispatch for {salesperson.name} on {date_obj} already exists.')
                return render_dispatch_form(request, date_obj)
            
            # Collect product quantities from form (format: product_{id}_quantity)
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
            
            # ✅ PRODUCTION INTEGRATION: Check stock availability
            from apps.production.models import DailyProduction, ProductionBatch
            
            # Get or create today's production record
            daily_production, created = DailyProduction.objects.get_or_create(date=date_obj)
            
            # If created today, auto-populate opening stock from yesterday's closing stock
            if created:
                yesterday = date_obj - timedelta(days=1)
                try:
                    yesterday_production = DailyProduction.objects.get(date=yesterday)
                    daily_production.opening_bread_stock = yesterday_production.closing_bread_stock
                    daily_production.opening_kdf_stock = yesterday_production.closing_kdf_stock
                    daily_production.opening_scones_stock = yesterday_production.closing_scones_stock
                    daily_production.created_by = request.user
                    daily_production.save()
                    messages.info(request, f'ℹ️ Created production record for {date_obj} with opening stock from {yesterday}')
                except DailyProduction.DoesNotExist:
                    # No previous day record - starting fresh
                    messages.warning(request, f'⚠️ No previous day stock found. Starting with zero opening stock for {date_obj}.')
            
            # Validate each product against available stock (DAILY, not cumulative)
            stock_errors = []
            for item_data in products_data:
                product = Product.objects.get(id=item_data['id'], is_active=True)
                
                # Get daily stock from DailyProduction
                if product.name == 'Bread':
                    opening_stock = daily_production.opening_bread_stock
                    produced_today = daily_production.bread_produced
                    already_dispatched = daily_production.bread_dispatched
                elif product.name == 'KDF':
                    opening_stock = daily_production.opening_kdf_stock
                    produced_today = daily_production.kdf_produced
                    already_dispatched = daily_production.kdf_dispatched
                elif product.name == 'Scones':
                    opening_stock = daily_production.opening_scones_stock
                    produced_today = daily_production.scones_produced
                    already_dispatched = daily_production.scones_dispatched
                else:
                    opening_stock = 0
                    produced_today = 0
                    already_dispatched = 0
                
                available = opening_stock + produced_today - already_dispatched
                requested = item_data['quantity']
                
                if requested > available:
                    stock_errors.append(
                        f"{product.name}: Requested {requested}, but only {available} available "
                        f"(Opening: {opening_stock}, Produced: {produced_today}, Already Dispatched: {already_dispatched})"
                    )
            
            if stock_errors:
                for error in stock_errors:
                    messages.error(request, error)
                messages.warning(request, '⚠️ Cannot dispatch more than available stock. Please adjust quantities.')
                return render_dispatch_form(request, date_obj)
            
            # ✅ CRATE INTEGRATION: Check crate availability
            if crates_dispatched > 0:
                from apps.inventory.models import CrateStock, CrateMovement
                try:
                    crate_stock = CrateStock.objects.first()
                    if not crate_stock:
                        messages.error(request, '⚠️ Crate inventory not initialized. Please set up crate stock in admin.')
                        return render_dispatch_form(request, date_obj)
                    
                    if crate_stock.available_crates < crates_dispatched:
                        messages.error(
                            request,
                            f'⚠️ Insufficient crates: Requested {crates_dispatched}, Available {crate_stock.available_crates}'
                        )
                        return render_dispatch_form(request, date_obj)
                except Exception as e:
                    messages.error(request, f'⚠️ Crate check failed: {str(e)}')
                    return render_dispatch_form(request, date_obj)
            
            # Create dispatch
            dispatch = Dispatch.objects.create(
                date=date_obj,
                salesperson=salesperson,
                crates_dispatched=crates_dispatched,
                created_by=request.user
            )
            
            # Create dispatch items AND update DailyProduction explicitly
            from django.db import transaction
            with transaction.atomic():
                for item_data in products_data:
                    product = Product.objects.get(id=item_data['id'], is_active=True)
                    quantity = item_data['quantity']
                    
                    # Create dispatch item
                    DispatchItem.objects.create(
                        dispatch=dispatch,
                        product=product,
                        quantity=quantity,
                        selling_price=product.price_per_packet,
                        expected_revenue=quantity * product.price_per_packet
                    )
                    
                    # Update DailyProduction dispatched field
                    if product.name == 'Bread':
                        daily_production.bread_dispatched += quantity
                    elif product.name == 'KDF':
                        daily_production.kdf_dispatched += quantity
                    elif product.name == 'Scones':
                        daily_production.scones_dispatched += quantity
                
                # Save DailyProduction once
                daily_production.save(update_fields=['bread_dispatched', 'kdf_dispatched', 'scones_dispatched'])
            
            # Note: Crate tracking handled automatically by inventory signals
            
            # Refresh to get calculated expected_revenue
            dispatch.refresh_from_db()
            
            messages.success(request, f'✅ Dispatch to {salesperson.name} created successfully! Expected revenue: KES {dispatch.expected_revenue:,.2f}')
            return redirect('sales:dispatch_list')
            
        except Salesperson.DoesNotExist:
            messages.error(request, '❌ Invalid salesperson selected.')
        except Product.DoesNotExist:
            messages.error(request, '❌ Invalid product selected.')
        except ValueError as e:
            messages.error(request, f'❌ Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'❌ Error creating dispatch: {str(e)}')
    
    # GET request - show form
    return render_dispatch_form(request, date_obj)


def render_dispatch_form(request, date_obj):
    """Helper to render dispatch form with context and stock levels"""
    from apps.production.models import DailyProduction, ProductionBatch
    from django.db.models import Sum
    
    salespeople = Salesperson.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    # Get or create today's production record (with opening stock from yesterday)
    daily_production, created = DailyProduction.objects.get_or_create(date=date_obj)
    
    if created:
        # Auto-populate opening stock from yesterday's closing stock
        yesterday = date_obj - timedelta(days=1)
        try:
            yesterday_production = DailyProduction.objects.get(date=yesterday)
            daily_production.opening_bread_stock = yesterday_production.closing_bread_stock
            daily_production.opening_kdf_stock = yesterday_production.closing_kdf_stock
            daily_production.opening_scones_stock = yesterday_production.closing_scones_stock
            daily_production.created_by = request.user
            daily_production.save()
            messages.info(request, f'ℹ️ Using opening stock from {yesterday}: Bread={yesterday_production.closing_bread_stock}, KDF={yesterday_production.closing_kdf_stock}, Scones={yesterday_production.closing_scones_stock}')
        except DailyProduction.DoesNotExist:
            messages.info(request, f'ℹ️ No previous stock found. Starting with zero opening stock.')
    
    # Calculate available stock for each product (DAILY, not cumulative)
    already_dispatched_today = {}
    for product in products:
        dispatched = DispatchItem.objects.filter(
            dispatch__date=date_obj,
            product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0
        already_dispatched_today[product.id] = dispatched
    
    products_with_stock = []
    for product in products:
        # Get daily stock from DailyProduction
        if product.name == 'Bread':
            opening = daily_production.opening_bread_stock
            produced = daily_production.bread_produced
        elif product.name == 'KDF':
            opening = daily_production.opening_kdf_stock
            produced = daily_production.kdf_produced
        elif product.name == 'Scones':
            opening = daily_production.opening_scones_stock
            produced = daily_production.scones_produced
        else:
            opening = 0
            produced = 0
        
        dispatched = already_dispatched_today.get(product.id, 0)
        available = opening + produced - dispatched
        
        products_with_stock.append({
            'product': product,
            'available': available,
            'opening': opening,
            'produced': produced,
            'dispatched': dispatched
        })
    
    # ✅ CRATE INTEGRATION: Get available crates
    from apps.inventory.models import CrateStock
    crate_stock = CrateStock.objects.first()
    available_crates = crate_stock.available_crates if crate_stock else 0
    
    context = {
        'selected_date': date_obj,
        'salespeople': salespeople,
        'products': products,
        'products_with_stock': products_with_stock,
        'has_production': True,
        'daily_production': daily_production,
        'available_crates': available_crates
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
    Edit existing dispatch (only if not returned)
    Updates dispatch items and validates against production stock
    """
    dispatch = get_object_or_404(Dispatch, pk=pk)
    
    # Prevent editing if already returned
    if dispatch.is_returned:
        messages.error(request, '❌ Cannot edit a dispatch that has already been returned.')
        return redirect('sales:dispatch_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Get form data
            salesperson_id = request.POST.get('salesperson')
            crates_dispatched = request.POST.get('crates_dispatched', 0)
            
            # Update salesperson and crates
            # Note: Crate stock updates handled by signal in apps/inventory/signals.py
            if salesperson_id:
                salesperson = Salesperson.objects.get(id=salesperson_id, is_active=True)
                dispatch.salesperson = salesperson
            dispatch.crates_dispatched = int(crates_dispatched) if crates_dispatched else 0
            
            # Collect product quantities from form
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
            
            # Production integration: Check stock availability
            from apps.production.models import DailyProduction, ProductionBatch
            from django.db.models import Sum
            
            try:
                daily_production = DailyProduction.objects.get(date=dispatch.date)
                
                # Validate each product against available stock (excluding current dispatch)
                stock_errors = []
                for item_data in products_data:
                    product = Product.objects.get(id=item_data['id'], is_active=True)
                    
                    # Calculate available stock (excluding THIS dispatch's items)
                    already_dispatched = DispatchItem.objects.filter(
                        dispatch__date=dispatch.date,
                        product=product
                    ).exclude(dispatch=dispatch).aggregate(total=Sum('quantity'))['total'] or 0
                    
                    # Get daily stock from DailyProduction (correct field names)
                    if product.name == 'Bread':
                        opening_stock = daily_production.opening_bread_stock
                        produced_today = daily_production.bread_produced
                    elif product.name == 'KDF':
                        opening_stock = daily_production.opening_kdf_stock
                        produced_today = daily_production.kdf_produced
                    elif product.name == 'Scones':
                        opening_stock = daily_production.opening_scones_stock
                        produced_today = daily_production.scones_produced
                    else:
                        opening_stock = 0
                        produced_today = 0
                    
                    available = opening_stock + produced_today - already_dispatched
                    requested = item_data['quantity']
                    
                    if requested > available:
                        stock_errors.append(
                            f"{product.name}: Requested {requested}, but only {available} available"
                        )
                
                if stock_errors:
                    for error in stock_errors:
                        messages.error(request, error)
                    return render_edit_dispatch_form(request, dispatch)
                    
            except DailyProduction.DoesNotExist:
                messages.error(request, f'⚠️ No production record found for {dispatch.date}.')
                return render_edit_dispatch_form(request, dispatch)
            
            # ========== EXPLICIT STOCK UPDATES (NO SIGNALS) ==========
            # Step 1: Capture OLD quantities before deleting
            old_quantities = {}
            for item in dispatch.dispatchitem_set.all():
                old_quantities[item.product.id] = item.quantity
            
            # Step 2: Calculate differences for each product
            from django.db import transaction
            with transaction.atomic():
                # Delete old items
                dispatch.dispatchitem_set.all().delete()
                
                # Create new items and update DailyProduction
                for item_data in products_data:
                    product = Product.objects.get(id=item_data['id'], is_active=True)
                    new_quantity = item_data['quantity']
                    old_quantity = old_quantities.get(product.id, 0)
                    difference = new_quantity - old_quantity
                    
                    # Create new dispatch item (signals disabled via bulk_create later)
                    DispatchItem.objects.create(
                        dispatch=dispatch,
                        product=product,
                        quantity=new_quantity,
                        selling_price=product.price_per_packet,
                        expected_revenue=new_quantity * product.price_per_packet
                    )
                    
                    # Update DailyProduction.dispatched ONLY if difference != 0
                    if difference != 0:
                        if product.name == 'Bread':
                            daily_production.bread_dispatched += difference
                        elif product.name == 'KDF':
                            daily_production.kdf_dispatched += difference
                        elif product.name == 'Scones':
                            daily_production.scones_dispatched += difference
                
                # Save DailyProduction once
                daily_production.save(update_fields=['bread_dispatched', 'kdf_dispatched', 'scones_dispatched'])
                
                # Update dispatch expected_revenue
                dispatch.calculate_expected_revenue()
                dispatch.save(update_fields=['expected_revenue'])
            
            messages.success(request, f'✅ Dispatch updated successfully! New expected revenue: KES {dispatch.expected_revenue:,.2f}')
            return redirect('sales:dispatch_detail', pk=pk)
            
        except Salesperson.DoesNotExist:
            messages.error(request, '❌ Invalid salesperson selected.')
        except Product.DoesNotExist:
            messages.error(request, '❌ Invalid product selected.')
        except Exception as e:
            messages.error(request, f'❌ Error updating dispatch: {str(e)}')
    
    # GET request - show form with existing data
    return render_edit_dispatch_form(request, dispatch)


def render_edit_dispatch_form(request, dispatch):
    """Helper to render edit form with existing dispatch data"""
    from apps.production.models import DailyProduction, ProductionBatch
    from django.db.models import Sum
    
    salespeople = Salesperson.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    
    # Get existing dispatch items
    existing_items = {}
    for item in dispatch.dispatchitem_set.all():
        existing_items[item.product.id] = item.quantity
    
    # Get stock levels (excluding current dispatch)
    try:
        daily_production = DailyProduction.objects.get(date=dispatch.date)
        
        products_with_stock = []
        for product in products:
            # Get daily stock from DailyProduction (correct field names)
            if product.name == 'Bread':
                opening_stock = daily_production.opening_bread_stock
                produced_today = daily_production.bread_produced
            elif product.name == 'KDF':
                opening_stock = daily_production.opening_kdf_stock
                produced_today = daily_production.kdf_produced
            elif product.name == 'Scones':
                opening_stock = daily_production.opening_scones_stock
                produced_today = daily_production.scones_produced
            else:
                opening_stock = 0
                produced_today = 0
            
            # Exclude current dispatch from "already dispatched"
            already_dispatched = DispatchItem.objects.filter(
                dispatch__date=dispatch.date,
                product=product
            ).exclude(dispatch=dispatch).aggregate(total=Sum('quantity'))['total'] or 0
            
            available = opening_stock + produced_today - already_dispatched
            
            products_with_stock.append({
                'product': product,
                'available': available,
                'opening': opening_stock,
                'produced': produced_today,
                'dispatched': already_dispatched,
                'current_quantity': existing_items.get(product.id, 0)
            })
        
        # ✅ CRATE INTEGRATION: Get available crates
        from apps.inventory.models import CrateStock
        crate_stock = CrateStock.objects.first()
        available_crates = crate_stock.available_crates if crate_stock else 0
        
        context = {
            'dispatch': dispatch,
            'selected_date': dispatch.date,
            'salespeople': salespeople,
            'products': products,
            'products_with_stock': products_with_stock,
            'existing_items': existing_items,
            'has_production': True,
            'is_edit': True,
            'available_crates': available_crates
        }
    except DailyProduction.DoesNotExist:
        # ✅ CRATE INTEGRATION: Get available crates
        from apps.inventory.models import CrateStock
        crate_stock = CrateStock.objects.first()
        available_crates = crate_stock.available_crates if crate_stock else 0
        
        context = {
            'dispatch': dispatch,
            'selected_date': dispatch.date,
            'salespeople': salespeople,
            'products': products,
            'products_with_stock': [],
            'existing_items': existing_items,
            'has_production': False,
            'is_edit': True,
            'available_crates': available_crates
        }
    
    return render(request, 'sales/dispatch_form.html', context)


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
    from .models import CommissionSettings
    
    dispatch = get_object_or_404(
        Dispatch.objects.select_related('salesperson').prefetch_related(
            'dispatchitem_set__product'
        ),
        pk=dispatch_id
    )
    
    # Get active commission settings
    commission_settings = CommissionSettings.get_active()
    
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
            
            # Note: Crate tracking now handled automatically by inventory signals
            # No manual CrateStock/CrateMovement updates needed
            
            # Check for crate deficit
            if sales_return.crates_deficit > 0:
                messages.warning(
                    request,
                    f'⚠️ Crate deficit: {sales_return.crates_deficit} crates missing. '
                    f'Accountant has been notified.'
                )
            
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
        'commission_settings': commission_settings,
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


# ============================================================================
# DISPATCH DELETE (SINGLE & BULK)
# ============================================================================

@login_required
def dispatch_delete(request, pk):
    """
    Delete a single dispatch with safeguards:
    - Only today's dispatches (before 9PM book closing)
    - Cannot delete if sales return exists
    - Restores stock to DailyProduction
    - Restores crates to CrateStock
    - Logs deletion in audit trail
    """
    dispatch = get_object_or_404(Dispatch, pk=pk)
    
    # SAFEGUARD 1: Check if dispatch has a sales return
    if hasattr(dispatch, 'sales_return'):
        messages.error(request, '❌ Cannot delete dispatch - Sales return already recorded!')
        return redirect('sales:dispatch_detail', pk=pk)
    
    # SAFEGUARD 2: Check if dispatch is from today and before 9PM
    today = date.today()
    current_time = timezone.now().time()
    book_closing_time = timezone.datetime.strptime('21:00', '%H:%M').time()
    
    if dispatch.date != today:
        # Only Accountant+ can delete past dispatches
        if request.user.role not in ['ACCOUNTANT', 'MANAGER', 'CEO', 'SUPERADMIN']:
            messages.error(request, f'❌ Cannot delete dispatch from {dispatch.date} - Only today\'s dispatches can be deleted.')
            return redirect('sales:dispatch_detail', pk=pk)
        
        # Check if that day's books are closed
        from apps.production.models import DailyProduction
        try:
            daily_prod = DailyProduction.objects.get(date=dispatch.date)
            if daily_prod.is_closed:
                messages.error(request, f'❌ Cannot delete dispatch - Books already closed for {dispatch.date}!')
                return redirect('sales:dispatch_detail', pk=pk)
        except DailyProduction.DoesNotExist:
            pass
    
    elif dispatch.date == today and current_time >= book_closing_time:
        # Today but after 9PM - only Accountant+ can delete
        if request.user.role not in ['ACCOUNTANT', 'MANAGER', 'CEO', 'SUPERADMIN']:
            messages.error(request, '❌ Cannot delete dispatch after 9PM - Books are closing!')
            return redirect('sales:dispatch_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            from apps.production.models import DailyProduction
            from apps.inventory.models import CrateStock
            from django.db import transaction
            
            with transaction.atomic():
                # Get daily production record
                daily_production = DailyProduction.objects.get(date=dispatch.date)
                
                # STEP 1: Restore products to stock
                for item in dispatch.dispatchitem_set.all():
                    if item.product.name == 'Bread':
                        daily_production.bread_dispatched -= item.quantity
                    elif item.product.name == 'KDF':
                        daily_production.kdf_dispatched -= item.quantity
                    elif item.product.name == 'Scones':
                        daily_production.scones_dispatched -= item.quantity
                
                daily_production.save(update_fields=['bread_dispatched', 'kdf_dispatched', 'scones_dispatched'])
                
                # STEP 2: Restore crates
                if dispatch.crates_dispatched > 0:
                    crate_stock = CrateStock.get_instance()
                    crate_stock.dispatched_crates -= dispatch.crates_dispatched
                    crate_stock.available_crates += dispatch.crates_dispatched
                    crate_stock.save(update_fields=['dispatched_crates', 'available_crates'])
                
                # STEP 3: Log deletion in audit trail (optional - can add to communications app)
                salesperson_name = dispatch.salesperson.name
                expected_revenue = dispatch.expected_revenue
                
                # STEP 4: Delete dispatch (cascade deletes DispatchItems)
                dispatch.delete()
            
            messages.success(request, f'✅ Dispatch to {salesperson_name} deleted successfully. Stock and crates restored. Expected revenue: KES {expected_revenue:,.2f}')
            return redirect('sales:dispatch_list')
            
        except DailyProduction.DoesNotExist:
            messages.error(request, f'❌ Cannot delete - No production record found for {dispatch.date}')
            return redirect('sales:dispatch_detail', pk=pk)
        except Exception as e:
            messages.error(request, f'❌ Error deleting dispatch: {str(e)}')
            return redirect('sales:dispatch_detail', pk=pk)
    
    # GET request - show confirmation page
    context = {
        'dispatch': dispatch,
        'can_delete': True,
        'warning_message': 'This will restore products and crates back to stock.',
    }
    return render(request, 'sales/dispatch_confirm_delete.html', context)


@login_required
def dispatch_bulk_delete(request):
    """
    Bulk delete multiple dispatches
    POST only - expects 'dispatch_ids[]' in request
    Same safeguards as single delete
    """
    if request.method != 'POST':
        messages.error(request, '❌ Invalid request method')
        return redirect('sales:dispatch_list')
    
    dispatch_ids = request.POST.getlist('dispatch_ids[]')
    
    if not dispatch_ids:
        messages.error(request, '❌ No dispatches selected for deletion')
        return redirect('sales:dispatch_list')
    
    # Validate and collect dispatches
    dispatches = Dispatch.objects.filter(id__in=dispatch_ids)
    
    # Check safeguards
    today = date.today()
    current_time = timezone.now().time()
    book_closing_time = timezone.datetime.strptime('21:00', '%H:%M').time()
    
    errors = []
    skipped = []
    deleted_count = 0
    
    from apps.production.models import DailyProduction
    from apps.inventory.models import CrateStock
    from django.db import transaction
    
    for dispatch in dispatches:
        # Check for sales return
        if hasattr(dispatch, 'sales_return'):
            errors.append(f'Dispatch #{dispatch.id} to {dispatch.salesperson.name} - Has sales return')
            continue
        
        # Check date/time restrictions
        if dispatch.date != today:
            if request.user.role not in ['ACCOUNTANT', 'MANAGER', 'CEO', 'SUPERADMIN']:
                errors.append(f'Dispatch #{dispatch.id} - From {dispatch.date}, only today allowed')
                continue
            
            # Check if books closed
            try:
                daily_prod = DailyProduction.objects.get(date=dispatch.date)
                if daily_prod.is_closed:
                    errors.append(f'Dispatch #{dispatch.id} - Books closed for {dispatch.date}')
                    continue
            except DailyProduction.DoesNotExist:
                pass
        
        elif dispatch.date == today and current_time >= book_closing_time:
            if request.user.role not in ['ACCOUNTANT', 'MANAGER', 'CEO', 'SUPERADMIN']:
                errors.append(f'Dispatch #{dispatch.id} - After 9PM, requires elevated permissions')
                continue
        
        # All checks passed - delete this dispatch
        try:
            with transaction.atomic():
                daily_production = DailyProduction.objects.get(date=dispatch.date)
                
                # Restore products
                for item in dispatch.dispatchitem_set.all():
                    if item.product.name == 'Bread':
                        daily_production.bread_dispatched -= item.quantity
                    elif item.product.name == 'KDF':
                        daily_production.kdf_dispatched -= item.quantity
                    elif item.product.name == 'Scones':
                        daily_production.scones_dispatched -= item.quantity
                
                daily_production.save(update_fields=['bread_dispatched', 'kdf_dispatched', 'scones_dispatched'])
                
                # Restore crates
                if dispatch.crates_dispatched > 0:
                    crate_stock = CrateStock.get_instance()
                    crate_stock.dispatched_crates -= dispatch.crates_dispatched
                    crate_stock.available_crates += dispatch.crates_dispatched
                    crate_stock.save(update_fields=['dispatched_crates', 'available_crates'])
                
                # Delete
                dispatch.delete()
                deleted_count += 1
                
        except Exception as e:
            errors.append(f'Dispatch #{dispatch.id} - Error: {str(e)}')
            continue
    
    # Show results
    if deleted_count > 0:
        messages.success(request, f'✅ Successfully deleted {deleted_count} dispatch(es). Stock and crates restored.')
    
    if errors:
        for error in errors[:5]:  # Show first 5 errors
            messages.warning(request, f'⚠️ {error}')
        
        if len(errors) > 5:
            messages.warning(request, f'⚠️ ...and {len(errors) - 5} more errors')
    
    return redirect('sales:dispatch_list')

