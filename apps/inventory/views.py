"""
Inventory App - Views
Dashboard views, purchase/output recording, and API endpoints.

All views use the atomic utilities from utils.py for data integrity.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator

from .routing import (
    INVENTORY_ITEMS,
    get_details_model,
    get_purchases_model,
    get_outputs_model,
    is_indirect_cost,
    is_ingredient,
    get_items_for_dropdown,
    get_all_ingredient_ids,
    get_all_indirect_cost_ids,
)
from .utils import (
    create_purchase_atomic,
    create_output_atomic,
    get_all_stock_levels,
    get_item_stock,
)
from .models import StockAlert
from apps.accounts.decorators import (
    admin_required,
    management_required,
)
from apps.core.services import can_delete_purchase


# ============================================================================
# PAGINATION HELPERS
# ============================================================================

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


# ============================================================================
# DASHBOARDS
# ============================================================================

@management_required
def dashboard(request):
    """Main inventory dashboard showing all items with stock status"""
    all_items = get_all_stock_levels()
    
    # Separate by category
    ingredients = [i for i in all_items if i.get('is_ingredient', True)]
    indirect_costs = [i for i in all_items if not i.get('is_ingredient', True)]
    
    # Count alerts
    low_stock_count = sum(1 for i in all_items if i.get('is_low_stock'))
    out_of_stock_count = sum(1 for i in all_items if i.get('is_out_of_stock'))
    
    # Recent alerts
    recent_alerts = StockAlert.objects.order_by('-triggered_at')[:5]
    
    context = {
        'ingredients': ingredients,
        'indirect_costs': indirect_costs,
        'total_items': len(all_items),
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'recent_alerts': recent_alerts,
    }
    return render(request, 'inventory/dashboard.html', context)


@management_required
def ingredients_dashboard(request):
    """Dashboard for ingredients (items 1-15)"""
    items = get_all_stock_levels(include_ingredients=True, include_indirect_costs=False)
    
    low_stock = [i for i in items if i.get('is_low_stock')]
    out_of_stock = [i for i in items if i.get('is_out_of_stock')]
    
    context = {
        'items': items,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'category': 'Ingredients',
    }
    return render(request, 'inventory/ingredients_dashboard.html', context)


@management_required
def indirect_costs_dashboard(request):
    """Dashboard for indirect costs (items 16-23)"""
    items = get_all_stock_levels(include_ingredients=False, include_indirect_costs=True)
    
    low_stock = [i for i in items if i.get('is_low_stock')]
    out_of_stock = [i for i in items if i.get('is_out_of_stock')]
    
    context = {
        'items': items,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'category': 'Indirect Costs',
    }
    return render(request, 'inventory/indirect_costs_dashboard.html', context)


# ============================================================================
# ITEM DETAIL
# ============================================================================

@management_required
def item_detail(request, inventory_item_id):
    """Detailed view of a specific inventory item"""
    # Get item stock info
    stock_result = get_item_stock(inventory_item_id)
    if not stock_result['success']:
        messages.error(request, stock_result['error'])
        return redirect('inventory:dashboard')
    
    item = stock_result['data']
    
    # Get purchase history
    PurchasesModel = get_purchases_model(inventory_item_id)
    recent_purchases = PurchasesModel.objects.all()[:10]
    
    # Get output history if indirect cost
    recent_outputs = []
    if is_indirect_cost(inventory_item_id):
        OutputsModel = get_outputs_model(inventory_item_id)
        recent_outputs = OutputsModel.objects.all()[:10]
    
    # Get alerts for this item
    alerts = StockAlert.objects.filter(
        inventory_item_id=inventory_item_id
    ).order_by('-triggered_at')[:10]
    
    context = {
        'item': item,
        'recent_purchases': recent_purchases,
        'recent_outputs': recent_outputs,
        'alerts': alerts,
        'is_indirect_cost': is_indirect_cost(inventory_item_id),
    }
    return render(request, 'inventory/item_detail.html', context)


# ============================================================================
# PURCHASE RECORDING
# ============================================================================

@admin_required
def create_purchase(request):
    """Record a new purchase for any inventory item"""
    # Get items for dropdown
    items = get_items_for_dropdown(include_ingredients=True, include_indirect_costs=True)
    
    # Initialize form data with defaults
    form_data = {
        'inventory_item_id': request.GET.get('item', ''),
        'supplier_name': '',
        'quantity_purchased': '',
        'unit_price': '',
        'purchase_date': date.today().isoformat(),
        'notes': '',
    }
    
    if request.method == 'POST':
        # Preserve form data for re-display on error
        form_data = {
            'inventory_item_id': request.POST.get('inventory_item_id', ''),
            'supplier_name': request.POST.get('supplier_name', ''),
            'quantity_purchased': request.POST.get('quantity_purchased', ''),
            'unit_price': request.POST.get('unit_price', ''),
            'purchase_date': request.POST.get('purchase_date', date.today().isoformat()),
            'notes': request.POST.get('notes', ''),
        }
        
        try:
            inventory_item_id = int(request.POST.get('inventory_item_id'))
            supplier_name = request.POST.get('supplier_name', '').strip()
            quantity = Decimal(request.POST.get('quantity_purchased', '0'))
            unit_price = Decimal(request.POST.get('unit_price', '0'))
            
            # Parse date
            date_str = request.POST.get('purchase_date', '')
            if date_str:
                purchase_date = date.fromisoformat(date_str)
            else:
                purchase_date = date.today()
            
            notes = request.POST.get('notes', '').strip()
            
            # Call atomic utility
            result = create_purchase_atomic(
                inventory_item_id=inventory_item_id,
                supplier_name=supplier_name,
                quantity_purchased=quantity,
                unit_price=unit_price,
                purchase_date=purchase_date,
                requested_by_user=request.user,
                notes=notes
            )
            
            if result['success']:
                messages.success(
                    request, 
                    f"✅ Purchase recorded: {result['data']['purchase_number']}"
                )
                return redirect('inventory:item_detail', inventory_item_id=inventory_item_id)
            else:
                messages.error(request, result['error'])
                
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Invalid input: Please check your values and try again.")
    
    # GET request or POST with errors - show form with preserved data
    today = date.today()
    min_date = today - timedelta(days=30)
    context = {
        'items': items,
        'today': today.isoformat(),
        'min_date': min_date.isoformat(),
        'form_data': form_data,
    }
    return render(request, 'inventory/create_purchase.html', context)


@management_required
def purchase_history(request, inventory_item_id):
    """View purchase history for a specific item with full pagination"""
    stock_result = get_item_stock(inventory_item_id)
    if not stock_result['success']:
        messages.error(request, stock_result['error'])
        return redirect('inventory:dashboard')
    
    # Get item info from INVENTORY_ITEMS for unit
    item_info = next((i for i in INVENTORY_ITEMS if i[0] == inventory_item_id), None)
    unit = item_info[3] if item_info else ''
    
    PurchasesModel = get_purchases_model(inventory_item_id)
    purchases_list = PurchasesModel.objects.select_related('purchased_by').order_by('-purchase_date', '-created_at')
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(purchases_list, per_page)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    
    # Enhance item data with unit
    item_data = stock_result['data']
    item_data['unit'] = unit
    
    # Check delete capability for each purchase (only for SUPERADMIN)
    is_superadmin = request.user.role == 'SUPERADMIN'
    if is_superadmin:
        for purchase in purchases:
            purchase.can_delete = can_delete_purchase(inventory_item_id, purchase)
    
    context = {
        'item': item_data,
        'purchases': purchases,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': paginator.count,
        'is_superadmin': is_superadmin,
    }
    return render(request, 'inventory/purchase_history.html', context)


@management_required
def purchase_list(request):
    """View all purchases across all items"""
    # Collect purchases from all 23 items
    all_purchases = []
    for item_id, name, is_ing, unit in INVENTORY_ITEMS:
        try:
            PurchasesModel = get_purchases_model(item_id)
            purchases = PurchasesModel.objects.all().order_by('-purchase_date', '-created_at')[:1000]
            for p in purchases:
                all_purchases.append({
                    'inventory_item_id': item_id,
                    'item_name': name,
                    'unit': unit,
                    'purchase_number': p.purchase_number,
                    'supplier_name': p.supplier_name,
                    'purchase_date': p.purchase_date,
                    'quantity_purchased': p.quantity_purchased,
                    'unit_price': p.unit_price,
                    'total_cost': p.total_cost,
                    'purchased_by': p.purchased_by,
                    'created_at': p.created_at,
                })
        except Exception:
            pass
    
    # Sort by date
    all_purchases.sort(key=lambda x: (x['purchase_date'], x['created_at']), reverse=True)
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(all_purchases, per_page)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    
    context = {
        'purchases': purchases,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': len(all_purchases),
    }
    return render(request, 'inventory/purchase_list.html', context)


# ============================================================================
# OUTPUT RECORDING (INDIRECT COSTS ONLY)
# ============================================================================

@admin_required
def create_output(request):
    """Record consumption output for indirect cost items"""
    # Get items for dropdown (only indirect costs)
    items = get_items_for_dropdown(include_ingredients=False, include_indirect_costs=True)
    
    # Initialize form data with defaults
    form_data = {
        'inventory_item_id': request.GET.get('item', ''),
        'quantity_consumed': '',
        'consumption_date': date.today().isoformat(),
        'date_range_start': '',
        'date_range_end': '',
        'description': '',
    }
    
    if request.method == 'POST':
        # Preserve form data for re-display on error
        form_data = {
            'inventory_item_id': request.POST.get('inventory_item_id', ''),
            'quantity_consumed': request.POST.get('quantity_consumed', ''),
            'consumption_date': request.POST.get('consumption_date', date.today().isoformat()),
            'date_range_start': request.POST.get('date_range_start', ''),
            'date_range_end': request.POST.get('date_range_end', ''),
            'description': request.POST.get('description', ''),
        }
        
        try:
            inventory_item_id = int(request.POST.get('inventory_item_id'))
            quantity = Decimal(request.POST.get('quantity_consumed', '0'))
            
            # Parse dates
            date_str = request.POST.get('consumption_date', '')
            consumption_date = date.fromisoformat(date_str) if date_str else date.today()
            
            range_start_str = request.POST.get('date_range_start', '')
            range_end_str = request.POST.get('date_range_end', '')
            date_range_start = date.fromisoformat(range_start_str) if range_start_str else None
            date_range_end = date.fromisoformat(range_end_str) if range_end_str else None
            
            description = request.POST.get('description', '').strip()
            
            # Call atomic utility
            result = create_output_atomic(
                inventory_item_id=inventory_item_id,
                quantity_consumed=quantity,
                consumption_date=consumption_date,
                requested_by_user=request.user,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                description=description
            )
            
            if result['success']:
                messages.success(
                    request,
                    f"✅ Output recorded: {result['data']['output_number']}"
                )
                
                # Show alerts if any
                for alert in result.get('alerts', []):
                    messages.warning(
                        request,
                        f"⚠️ Low Stock Alert: {alert['item_name']} - "
                        f"{alert['current_stock']} (min: {alert['minimum_stock']})"
                    )
                
                return redirect('inventory:item_detail', inventory_item_id=inventory_item_id)
            else:
                messages.error(request, result['error'])
                
        except (ValueError, InvalidOperation) as e:
            messages.error(request, "Invalid input: Please check your values and try again.")
    
    # GET request or POST with errors - show form with preserved data
    today = date.today()
    min_date = today - timedelta(days=30)
    context = {
        'items': items,
        'today': today.isoformat(),
        'min_date': min_date.isoformat(),
        'form_data': form_data,
    }
    return render(request, 'inventory/create_output.html', context)


@management_required
def output_history(request, inventory_item_id):
    """View output history for an indirect cost item with full pagination"""
    if not is_indirect_cost(inventory_item_id):
        messages.error(request, "This item does not have an outputs table.")
        return redirect('inventory:dashboard')
    
    stock_result = get_item_stock(inventory_item_id)
    if not stock_result['success']:
        messages.error(request, stock_result['error'])
        return redirect('inventory:dashboard')
    
    # Get item info from INVENTORY_ITEMS for unit
    item_info = next((i for i in INVENTORY_ITEMS if i[0] == inventory_item_id), None)
    unit = item_info[3] if item_info else ''
    
    OutputsModel = get_outputs_model(inventory_item_id)
    outputs_list = OutputsModel.objects.select_related('consumed_by').order_by('-consumption_date', '-created_at')
    
    # Get last purchase price as Decimal for cost calculation
    try:
        last_price = Decimal(stock_result['data'].get('last_purchase_unit_price', '0') or '0')
    except (InvalidOperation, TypeError):
        last_price = Decimal('0')
    
    # Annotate each output with cost at last purchase price
    outputs_with_cost = []
    for output in outputs_list:
        output.cost_at_lpp = round(output.quantity_consumed * last_price, 2) if last_price > 0 else None
        outputs_with_cost.append(output)
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(outputs_with_cost, per_page)
    page_number = request.GET.get('page')
    outputs = paginator.get_page(page_number)
    
    # Enhance item data with unit
    item_data = stock_result['data']
    item_data['unit'] = unit
    
    context = {
        'item': item_data,
        'outputs': outputs,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': paginator.count,
    }
    return render(request, 'inventory/output_history.html', context)


@management_required
def output_list(request):
    """View all outputs across all indirect cost items"""
    # Collect outputs from indirect cost items (16-23)
    all_outputs = []
    indirect_cost_ids = get_all_indirect_cost_ids()
    
    for item_id in indirect_cost_ids:
        try:
            item_info = next((i for i in INVENTORY_ITEMS if i[0] == item_id), None)
            if not item_info:
                continue
            name, unit = item_info[1], item_info[3]
            
            OutputsModel = get_outputs_model(item_id)
            outputs = OutputsModel.objects.all().order_by('-consumption_date', '-created_at')[:1000]
            for o in outputs:
                all_outputs.append({
                    'inventory_item_id': item_id,
                    'item_name': name,
                    'unit': unit,
                    'output_number': o.output_number,
                    'consumption_date': o.consumption_date,
                    'quantity_consumed': o.quantity_consumed,
                    'date_range_start': o.date_range_start,
                    'date_range_end': o.date_range_end,
                    'description': o.description,
                    'consumed_by': o.consumed_by,
                    'created_at': o.created_at,
                })
        except Exception:
            pass
    
    # Sort by date
    all_outputs.sort(key=lambda x: (x['consumption_date'], x['created_at']), reverse=True)
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(all_outputs, per_page)
    page_number = request.GET.get('page')
    outputs = paginator.get_page(page_number)
    
    context = {
        'outputs': outputs,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': len(all_outputs),
    }
    return render(request, 'inventory/output_list.html', context)


# ============================================================================
# STOCK ALERTS
# ============================================================================

@management_required
def alerts_list(request):
    """View all stock alerts"""
    all_alerts = StockAlert.objects.all()
    alerts_queryset = all_alerts.order_by('-triggered_at')
    
    # Get counts by level (before filtering)
    warning_count = all_alerts.filter(alert_level='WARNING').count()
    critical_count = all_alerts.filter(alert_level='CRITICAL').count()
    
    # Filter by level
    level = request.GET.get('level')
    if level in ['WARNING', 'CRITICAL']:
        alerts_queryset = alerts_queryset.filter(alert_level=level)
    
    # Filter by inventory item
    item_id = request.GET.get('item_id')
    if item_id:
        try:
            alerts_queryset = alerts_queryset.filter(inventory_item_id=int(item_id))
        except (ValueError, TypeError):
            pass
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        alerts_queryset = alerts_queryset.filter(triggered_at__date__gte=date_from)
    if date_to:
        alerts_queryset = alerts_queryset.filter(triggered_at__date__lte=date_to)
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(alerts_queryset, per_page)
    page_number = request.GET.get('page')
    alerts = paginator.get_page(page_number)
    
    # Preserve filter params across pagination
    preserve_params = {}
    if level:
        preserve_params['level'] = level
    if item_id:
        preserve_params['item_id'] = item_id
    if date_from:
        preserve_params['date_from'] = date_from
    if date_to:
        preserve_params['date_to'] = date_to
    
    # Build inventory items list for dropdown
    inventory_items_choices = [(item[0], item[1]) for item in INVENTORY_ITEMS]
    
    context = {
        'alerts': alerts,
        'current_level': level,
        'current_item_id': item_id,
        'date_from': date_from,
        'date_to': date_to,
        'inventory_items_choices': inventory_items_choices,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': alerts_queryset.count(),
        'warning_count': warning_count,
        'critical_count': critical_count,
        'preserve_params': preserve_params,
    }
    return render(request, 'inventory/alerts_list.html', context)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@management_required
@require_GET
def api_stock_levels(request):
    """API endpoint returning all stock levels as JSON"""
    include_ingredients = request.GET.get('ingredients', 'true').lower() == 'true'
    include_indirect = request.GET.get('indirect_costs', 'true').lower() == 'true'
    
    items = get_all_stock_levels(
        include_ingredients=include_ingredients,
        include_indirect_costs=include_indirect
    )
    
    return JsonResponse({
        'success': True,
        'data': items,
        'count': len(items),
    })


@management_required
@require_GET
def api_item_stock(request, inventory_item_id):
    """API endpoint returning stock level for specific item"""
    result = get_item_stock(inventory_item_id)
    return JsonResponse(result)
