"""
Production App - Views

Handles all HTTP requests for production management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Sum, Count

from apps.products.models import Product, Mix
from apps.accounts.decorators import management_required, sales_view_required, SALES_VIEW_ROLES
from .models import ProductionBatch, ProductStock, ProductStockMovement
from .services import ProductionService


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


@management_required
def dashboard(request):
    """Production dashboard with today's summary."""
    today = timezone.now().date()
    
    # Get today's production summary
    summary = ProductionService.get_production_summary(date_filter=today)
    
    # Get current stock levels
    stocks = ProductStock.objects.select_related('product').filter(
        product__is_active=True,
        product__parent_product__isnull=True  # Main products only
    ).order_by('product__name')
    
    # Get recent batches
    recent_batches = ProductionBatch.objects.select_related(
        'product', 'produced_by'
    ).order_by('-created_at')[:10]
    
    # Get recent stock movements
    recent_movements = ProductStockMovement.objects.select_related(
        'product', 'recorded_by'
    ).order_by('-created_at')[:10]
    
    context = {
        'summary': summary,
        'stocks': stocks,
        'recent_batches': recent_batches,
        'recent_movements': recent_movements,
        'today': today,
    }
    
    return render(request, 'production/dashboard.html', context)


@management_required
def batch_list(request):
    """List all production batches with filtering."""
    queryset = ProductionBatch.objects.select_related(
        'product', 'produced_by'
    ).order_by('-production_date', '-created_at')
    
    # Apply filters
    product_id = request.GET.get('product')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    search = request.GET.get('search')
    
    if product_id:
        queryset = queryset.filter(product_id=product_id)
    if date_from:
        queryset = queryset.filter(production_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(production_date__lte=date_to)
    if search:
        queryset = queryset.filter(batch_number__icontains=search)
    
    # Paginate with configurable page size
    per_page = get_page_size(request)
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    batches = paginator.get_page(page_number)
    
    # Preserve filter params for pagination
    preserve_params = {}
    if product_id:
        preserve_params['product'] = product_id
    if date_from:
        preserve_params['from'] = date_from
    if date_to:
        preserve_params['to'] = date_to
    if search:
        preserve_params['search'] = search
    
    # Get products for filter dropdown
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    
    context = {
        'batches': batches,
        'products': products,
        'current_product': product_id,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        # Pagination context
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_count': queryset.count(),
        'preserve_params': preserve_params,
    }
    
    return render(request, 'production/batch_list.html', context)


@management_required
def batch_create(request):
    """Create a new production batch."""
    # Prepare products for dropdown
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    today = timezone.now().date()
    now_time = timezone.now().strftime('%H:%M')
    
    # Initialize form_data for template (preserves values on error)
    form_data = {
        'product': '',
        'mix': '',
        'quantity_produced': '',
        'production_date': str(today),
        'production_time': now_time,
        'notes': '',
    }
    
    if request.method == 'POST':
        # Capture form data for preservation on error
        form_data['product'] = request.POST.get('product', '')
        form_data['mix'] = request.POST.get('mix', '')
        form_data['quantity_produced'] = request.POST.get('quantity_produced', '')
        form_data['production_date'] = request.POST.get('production_date', str(today))
        form_data['production_time'] = request.POST.get('production_time', '')
        form_data['notes'] = request.POST.get('notes', '')
        
        mix_id = form_data['mix']
        quantity_produced = form_data['quantity_produced']
        production_date = form_data['production_date']
        production_time = form_data['production_time'] or None
        notes = form_data['notes']
        
        # Validate required fields
        if not all([mix_id, quantity_produced, production_date]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'production/batch_form.html', {
                'products': products,
                'today': today,
                'form_data': form_data,
            })
        
        try:
            from datetime import datetime
            from decimal import Decimal, InvalidOperation
            
            prod_date = datetime.strptime(production_date, '%Y-%m-%d').date()
            prod_time = None
            if production_time:
                prod_time = datetime.strptime(production_time, '%H:%M').time()
            
            # Parse quantity - handle Decimal strings properly
            try:
                qty_decimal = Decimal(str(quantity_produced))
                qty_int = int(qty_decimal)
            except (InvalidOperation, ValueError):
                messages.error(request, f"Invalid quantity: '{quantity_produced}'. Please enter a whole number.")
                return render(request, 'production/batch_form.html', {
                    'products': products,
                    'today': today,
                    'form_data': form_data,
                })
            
            result = ProductionService.create_production_batch(
                mix_id=int(mix_id),
                quantity_produced=qty_int,
                production_date=prod_date,
                user=request.user,
                production_time=prod_time,
                notes=notes
            )
            
            if result['success']:
                messages.success(
                    request,
                    f"✅ Production batch {result['data']['batch_number']} recorded successfully! "
                    f"Produced {result['data']['quantity_produced']} units. "
                    f"Stock: {result['data']['stock_after']} units."
                )
                
                # Show stock alerts if any
                for alert in result['data'].get('stock_alerts', []):
                    messages.warning(
                        request,
                        f"⚠️ Low stock alert: {alert['item_name']} - {alert['current_stock']} remaining"
                    )
                
                return redirect('production:batch_detail', batch_id=result['data']['batch'].id)
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'shortages' in result:
                    shortage_details = ', '.join(
                        f"{s['item_name']}: need {s['required']}, have {s['available']}"
                        for s in result['shortages']
                    )
                    error_msg = f"Insufficient ingredients: {shortage_details}"
                messages.error(request, error_msg)
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating batch: {str(e)}")
        
        # On error, re-render with preserved form data
        return render(request, 'production/batch_form.html', {
            'products': products,
            'today': today,
            'form_data': form_data,
        })
    
    # GET request - show form with defaults
    context = {
        'products': products,
        'today': today,
        'form_data': form_data,
    }
    
    return render(request, 'production/batch_form.html', context)


@management_required
def batch_detail(request, batch_id):
    """View production batch details."""
    batch = get_object_or_404(
        ProductionBatch.objects.select_related('product', 'mix', 'produced_by'),
        id=batch_id
    )
    
    deductions = batch.ingredient_deductions.all().order_by('inventory_item_id')
    
    context = {
        'batch': batch,
        'deductions': deductions,
    }
    
    return render(request, 'production/batch_detail.html', context)


@sales_view_required
def stock_dashboard(request):
    """View current product stock levels."""
    # Get all product stocks
    stocks = ProductStock.objects.select_related('product').filter(
        product__is_active=True
    ).order_by('product__name')
    
    # Get recent movements
    movements = ProductStockMovement.objects.select_related(
        'product', 'recorded_by'
    ).order_by('-created_at')[:20]
    
    # Calculate totals
    total_stock = stocks.aggregate(total=Sum('current_stock'))['total'] or 0
    
    context = {
        'stocks': stocks,
        'movements': movements,
        'total_stock': total_stock,
    }
    
    return render(request, 'production/stock_dashboard.html', context)


@sales_view_required
def stock_detail(request, product_id):
    """View stock movements for a specific product."""
    product = get_object_or_404(Product, id=product_id)
    
    try:
        stock = ProductStock.objects.get(product=product)
    except ProductStock.DoesNotExist:
        stock = None
    
    movements = ProductStockMovement.objects.filter(
        product=product
    ).select_related('recorded_by').order_by('-created_at')[:50]
    
    context = {
        'product': product,
        'stock': stock,
        'movements': movements,
    }
    
    return render(request, 'production/stock_detail.html', context)


# ============================================================================
# API VIEWS (for AJAX/HTMX)
# ============================================================================

@management_required
def api_get_mixes(request):
    """Get active mixes for a product (for dynamic dropdown)."""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'mixes': []})
    
    mixes = Mix.objects.filter(
        product_id=product_id,
        is_active=True
    ).values('id', 'name', 'expected_yield')
    
    # Convert expected_yield to int for clean display
    mixes_list = []
    for mix in mixes:
        mixes_list.append({
            'id': mix['id'],
            'name': mix['name'],
            'expected_yield': int(mix['expected_yield'])
        })
    
    return JsonResponse({'mixes': mixes_list})


@management_required
def api_mix_preview(request, mix_id):
    """Get ingredient availability preview for a mix."""
    try:
        mix = Mix.objects.prefetch_related('ingredients').get(id=mix_id, is_active=True)
        availability = ProductionService.check_ingredient_availability(mix)
        
        return JsonResponse({
            'success': True,
            'mix_name': mix.name,
            'expected_yield': int(mix.expected_yield),
            **availability
        })
    except Mix.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mix not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# WASTE MANAGEMENT VIEWS
# ============================================================================

@management_required
def waste_list(request):
    """List all waste disposal records with filtering."""
    from .models import WasteLog
    
    # Get filter parameters
    source_filter = request.GET.get('source', '')
    product_filter = request.GET.get('product', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    waste_logs = WasteLog.objects.select_related(
        'product', 'disposed_by'
    ).order_by('-disposal_date', '-created_at')
    
    # Apply filters
    if source_filter:
        waste_logs = waste_logs.filter(source=source_filter)
    
    if product_filter:
        waste_logs = waste_logs.filter(product_id=product_filter)
    
    if date_from:
        waste_logs = waste_logs.filter(disposal_date__gte=date_from)
    
    if date_to:
        waste_logs = waste_logs.filter(disposal_date__lte=date_to)
    
    # Pagination
    per_page = get_page_size(request)
    paginator = Paginator(waste_logs, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get products for filter dropdown (only Leftovers products)
    leftovers_products = Product.objects.filter(
        parent_product__isnull=False,
        is_active=True
    ).order_by('name')
    
    # Calculate totals for filtered results
    totals = waste_logs.aggregate(
        total_quantity=Sum('quantity'),
        total_value=Sum('total_value')
    )
    
    context = {
        'page_obj': page_obj,
        'waste_logs': page_obj,
        'source_choices': WasteLog.Source.choices,
        'products': leftovers_products,
        'current_source': source_filter,
        'current_product': product_filter,
        'date_from': date_from,
        'date_to': date_to,
        'per_page': per_page,
        'pagination_choices': PAGINATION_CHOICES,
        'total_quantity': totals['total_quantity'] or 0,
        'total_value': totals['total_value'] or 0,
    }
    
    return render(request, 'production/waste_list.html', context)


@management_required
def waste_dispose(request):
    """Create a new waste disposal record."""
    from .models import WasteLog
    from datetime import date
    
    if request.method == 'POST':
        try:
            # Parse form data
            product_id = int(request.POST.get('product'))
            quantity = int(request.POST.get('quantity'))
            source = request.POST.get('source')
            reason = request.POST.get('reason', '').strip()
            notes = request.POST.get('notes', '').strip()
            
            # Validate reason
            if not reason:
                raise ValueError("Reason is required")
            
            # Call service
            result = ProductionService.dispose_waste(
                product_id=product_id,
                quantity=quantity,
                source=source,
                reason=reason,
                disposal_date=date.today(),
                user=request.user,
                notes=notes
            )
            
            if result.get('success'):
                messages.success(
                    request,
                    f"Waste disposal recorded: {result['waste_number']} - "
                    f"{result['quantity']} units of {result['product_name']} "
                    f"(Value: KES {result['total_value']})"
                )
                return redirect('production:waste_list')
            else:
                messages.error(request, result.get('error', 'Disposal failed'))
                
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    # GET request - show form
    # Get Leftovers products with stock for disposal
    leftovers_with_stock = ProductStock.objects.select_related('product').filter(
        product__parent_product__isnull=False,
        product__is_active=True,
        current_stock__gt=0
    ).order_by('product__name')
    
    context = {
        'products_with_stock': leftovers_with_stock,
        'source_choices': WasteLog.Source.choices,
        'today': date.today(),
    }
    
    return render(request, 'production/waste_dispose.html', context)
