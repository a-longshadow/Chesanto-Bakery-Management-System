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
from .models import ProductionBatch, ProductStock, ProductStockMovement
from .services import ProductionService


@login_required
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


@login_required
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
    
    # Paginate
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    batches = paginator.get_page(page_number)
    
    # Get products for filter dropdown
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    
    context = {
        'batches': batches,
        'products': products,
        'current_product': product_id,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    
    return render(request, 'production/batch_list.html', context)


@login_required
def batch_create(request):
    """Create a new production batch."""
    if request.method == 'POST':
        mix_id = request.POST.get('mix')
        quantity_produced = request.POST.get('quantity_produced')
        production_date = request.POST.get('production_date')
        production_time = request.POST.get('production_time') or None
        notes = request.POST.get('notes', '')
        
        # Validate
        if not all([mix_id, quantity_produced, production_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('production:batch_create')
        
        try:
            from datetime import datetime
            prod_date = datetime.strptime(production_date, '%Y-%m-%d').date()
            prod_time = None
            if production_time:
                prod_time = datetime.strptime(production_time, '%H:%M').time()
            
            result = ProductionService.create_production_batch(
                mix_id=int(mix_id),
                quantity_produced=int(quantity_produced),
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
        
        return redirect('production:batch_create')
    
    # GET request - show form
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    today = timezone.now().date()
    
    context = {
        'products': products,
        'today': today,
    }
    
    return render(request, 'production/batch_form.html', context)


@login_required
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


@login_required
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


@login_required
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

@login_required
def api_get_mixes(request):
    """Get active mixes for a product (for dynamic dropdown)."""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'mixes': []})
    
    mixes = Mix.objects.filter(
        product_id=product_id,
        is_active=True
    ).values('id', 'name', 'expected_yield')
    
    return JsonResponse({'mixes': list(mixes)})


@login_required
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
