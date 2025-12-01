"""
Inventory App - Views
Dashboard views, purchase/output recording, and API endpoints.

All views use the atomic utilities from utils.py for data integrity.
"""
from datetime import date
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


# ============================================================================
# DASHBOARDS
# ============================================================================

@login_required
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


@login_required
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


@login_required
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

@login_required
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

@login_required
def create_purchase(request):
    """Record a new purchase for any inventory item"""
    if request.method == 'POST':
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
                    f"Purchase recorded: {result['data']['purchase_number']}"
                )
                return redirect('inventory:item_detail', inventory_item_id=inventory_item_id)
            else:
                messages.error(request, f"Error: {result['error']}")
                
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Invalid input: {str(e)}")
    
    # GET request - show form
    items = get_items_for_dropdown(include_ingredients=True, include_indirect_costs=True)
    context = {
        'items': items,
        'today': date.today().isoformat(),
    }
    return render(request, 'inventory/create_purchase.html', context)


@login_required
def purchase_history(request, inventory_item_id):
    """View purchase history for a specific item"""
    stock_result = get_item_stock(inventory_item_id)
    if not stock_result['success']:
        messages.error(request, stock_result['error'])
        return redirect('inventory:dashboard')
    
    PurchasesModel = get_purchases_model(inventory_item_id)
    purchases_list = PurchasesModel.objects.all().order_by('-purchase_date', '-created_at')
    
    paginator = Paginator(purchases_list, 20)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    
    context = {
        'item': stock_result['data'],
        'purchases': purchases,
    }
    return render(request, 'inventory/purchase_history.html', context)


@login_required
def purchase_list(request):
    """View all purchases across all items"""
    # Collect purchases from all 23 items
    all_purchases = []
    for item_id, name, is_ing, unit in INVENTORY_ITEMS:
        try:
            PurchasesModel = get_purchases_model(item_id)
            purchases = PurchasesModel.objects.all().order_by('-purchase_date', '-created_at')[:100]
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
    
    # Paginate
    paginator = Paginator(all_purchases, 50)
    page_number = request.GET.get('page')
    purchases = paginator.get_page(page_number)
    
    context = {
        'purchases': purchases,
    }
    return render(request, 'inventory/purchase_list.html', context)


# ============================================================================
# OUTPUT RECORDING (INDIRECT COSTS ONLY)
# ============================================================================

@login_required
def create_output(request):
    """Record consumption output for indirect cost items"""
    if request.method == 'POST':
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
                    f"Output recorded: {result['data']['output_number']}"
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
                messages.error(request, f"Error: {result['error']}")
                
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Invalid input: {str(e)}")
    
    # GET request - show form (only indirect cost items)
    items = get_items_for_dropdown(include_ingredients=False, include_indirect_costs=True)
    context = {
        'items': items,
        'today': date.today().isoformat(),
    }
    return render(request, 'inventory/create_output.html', context)


@login_required
def output_history(request, inventory_item_id):
    """View output history for an indirect cost item"""
    if not is_indirect_cost(inventory_item_id):
        messages.error(request, "This item does not have an outputs table.")
        return redirect('inventory:dashboard')
    
    stock_result = get_item_stock(inventory_item_id)
    if not stock_result['success']:
        messages.error(request, stock_result['error'])
        return redirect('inventory:dashboard')
    
    OutputsModel = get_outputs_model(inventory_item_id)
    outputs_list = OutputsModel.objects.all().order_by('-consumption_date', '-created_at')
    
    paginator = Paginator(outputs_list, 20)
    page_number = request.GET.get('page')
    outputs = paginator.get_page(page_number)
    
    context = {
        'item': stock_result['data'],
        'outputs': outputs,
    }
    return render(request, 'inventory/output_history.html', context)


@login_required
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
            outputs = OutputsModel.objects.all().order_by('-consumption_date', '-created_at')[:100]
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
    
    # Paginate
    paginator = Paginator(all_outputs, 50)
    page_number = request.GET.get('page')
    outputs = paginator.get_page(page_number)
    
    context = {
        'outputs': outputs,
    }
    return render(request, 'inventory/output_list.html', context)


# ============================================================================
# STOCK ALERTS
# ============================================================================

@login_required
def alerts_list(request):
    """View all stock alerts"""
    alerts_queryset = StockAlert.objects.all().order_by('-triggered_at')
    
    # Filter by level
    level = request.GET.get('level')
    if level in ['WARNING', 'CRITICAL']:
        alerts_queryset = alerts_queryset.filter(alert_level=level)
    
    paginator = Paginator(alerts_queryset, 50)
    page_number = request.GET.get('page')
    alerts = paginator.get_page(page_number)
    
    context = {
        'alerts': alerts,
        'current_level': level,
    }
    return render(request, 'inventory/alerts_list.html', context)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@login_required
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


@login_required
@require_GET
def api_item_stock(request, inventory_item_id):
    """API endpoint returning stock level for specific item"""
    result = get_item_stock(inventory_item_id)
    return JsonResponse(result)
