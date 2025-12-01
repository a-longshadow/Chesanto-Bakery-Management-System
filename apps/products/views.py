"""
Products App - Views
Views for product catalog and recipe management.
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_GET

from .models import Product, Mix, MixIngredient
from .services import ProductService, MixService


# ============================================================================
# DASHBOARD
# ============================================================================

@login_required
def dashboard(request):
    """
    Products dashboard - overview of all products and their recipes.
    """
    products = Product.objects.filter(
        is_active=True
    ).select_related(
        'parent_product'
    ).prefetch_related(
        'mixes', 'mixes__ingredients'
    ).order_by('name')
    
    # Separate main products and sub-products
    main_products = [p for p in products if not p.is_sub_product]
    sub_products = [p for p in products if p.is_sub_product]
    
    # Count statistics
    total_products = products.count()
    products_with_recipes = sum(1 for p in products if p.has_active_mix)
    products_without_recipes = total_products - products_with_recipes
    
    # Archived counts
    archived_products = Product.objects.filter(is_active=False).count()
    archived_mixes = Mix.objects.filter(is_active=False).count()
    
    context = {
        'main_products': main_products,
        'sub_products': sub_products,
        'total_products': total_products,
        'products_with_recipes': products_with_recipes,
        'products_without_recipes': products_without_recipes,
        'archived_products': archived_products,
        'archived_mixes': archived_mixes,
    }
    return render(request, 'products/dashboard.html', context)


# ============================================================================
# PRODUCT VIEWS
# ============================================================================

@login_required
def product_list(request):
    """
    List all products (active and archived based on filter).
    """
    show_archived = request.GET.get('archived', 'false').lower() == 'true'
    
    if show_archived:
        products = Product.objects.filter(is_active=False)
    else:
        products = Product.objects.filter(is_active=True)
    
    products = products.select_related('parent_product').prefetch_related('mixes').order_by('name')
    
    context = {
        'products': products,
        'show_archived': show_archived,
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, product_id):
    """
    View product details with active mix and ingredients.
    """
    product = get_object_or_404(Product, id=product_id)
    active_mix = product.get_active_mix()
    
    # Get sub-products if this is a main product
    sub_products = product.sub_products.filter(is_active=True) if not product.is_sub_product else None
    
    # Get all mixes (active and archived)
    all_mixes = product.mixes.all().order_by('-is_active', '-updated_at')
    
    context = {
        'product': product,
        'active_mix': active_mix,
        'ingredients': active_mix.ingredients.all() if active_mix else [],
        'sub_products': sub_products,
        'all_mixes': all_mixes,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def product_create(request):
    """
    Create a new product.
    Admin only.
    """
    # Get parent product options (only main products)
    parent_options = Product.objects.filter(
        is_active=True,
        parent_product__isnull=True
    ).order_by('name')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            selling_price = Decimal(request.POST.get('selling_price', '0'))
            description = request.POST.get('description', '').strip()
            parent_id = request.POST.get('parent_product')
            parent_id = int(parent_id) if parent_id else None
            
            product = ProductService.create_product(
                name=name,
                selling_price=selling_price,
                created_by=request.user,
                parent_product_id=parent_id,
                description=description
            )
            
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('products:detail', product_id=product.id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, str(e))
    
    context = {
        'parent_options': parent_options,
    }
    return render(request, 'products/product_form.html', context)


@login_required
def product_edit(request, product_id):
    """
    Edit an existing product.
    Admin only.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Get parent product options (exclude self and its children)
    parent_options = Product.objects.filter(
        is_active=True,
        parent_product__isnull=True
    ).exclude(id=product_id).order_by('name')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            selling_price = Decimal(request.POST.get('selling_price', '0'))
            description = request.POST.get('description', '').strip()
            parent_id = request.POST.get('parent_product')
            parent_id = int(parent_id) if parent_id else -1  # -1 to remove parent
            
            ProductService.update_product(
                product_id=product.id,
                updated_by=request.user,
                name=name if name != product.name else None,
                selling_price=selling_price,
                description=description,
                parent_product_id=parent_id
            )
            
            messages.success(request, f"Product '{name}' updated successfully!")
            return redirect('products:detail', product_id=product.id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, str(e))
    
    context = {
        'product': product,
        'parent_options': parent_options,
        'is_edit': True,
    }
    return render(request, 'products/product_form.html', context)


@login_required
def product_price_update(request, product_id):
    """
    Quick price update form.
    Admin and Accountant only.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    if request.method == 'POST':
        try:
            new_price = Decimal(request.POST.get('selling_price', '0'))
            old_price = product.selling_price
            
            ProductService.update_price(
                product_id=product.id,
                new_price=new_price,
                updated_by=request.user
            )
            
            messages.success(
                request, 
                f"Price updated: KES {old_price} → KES {new_price}"
            )
            return redirect('products:detail', product_id=product.id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, str(e))
    
    context = {
        'product': product,
    }
    return render(request, 'products/price_update.html', context)


@login_required
@require_POST
def product_archive(request, product_id):
    """
    Archive (soft delete) a product.
    Admin only.
    """
    try:
        product = ProductService.archive_product(product_id, request.user)
        messages.success(request, f"Product '{product.name}' archived.")
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('products:dashboard')


@login_required
@require_POST
def product_restore(request, product_id):
    """
    Restore an archived product.
    Admin only.
    """
    try:
        product = ProductService.restore_product(product_id, request.user)
        messages.success(request, f"Product '{product.name}' restored.")
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('products:detail', product_id=product_id)


# ============================================================================
# MIX (RECIPE) VIEWS
# ============================================================================

@login_required
def mix_create(request, product_id):
    """
    Create a new mix/recipe for a product.
    Admin only.
    """
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check if product already has active mix
    if product.has_active_mix:
        messages.warning(
            request, 
            f"'{product.name}' already has an active recipe. Archive it first to create a new one."
        )
        return redirect('products:detail', product_id=product_id)
    
    # Get inventory items for dropdown
    try:
        from apps.inventory.routing import get_items_for_dropdown
        inventory_items = get_items_for_dropdown()
    except ImportError:
        inventory_items = [(i, f"Item {i}") for i in range(1, 24)]
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            expected_yield = Decimal(request.POST.get('expected_yield', '0'))
            is_fixed_yield = request.POST.get('is_fixed_yield') == 'on'
            yield_variance_min = request.POST.get('yield_variance_min')
            yield_variance_max = request.POST.get('yield_variance_max')
            notes = request.POST.get('notes', '').strip()
            
            # Parse ingredients from form
            ingredients = []
            item_ids = request.POST.getlist('ingredient_item_id')
            quantities = request.POST.getlist('ingredient_quantity')
            units = request.POST.getlist('ingredient_unit')
            ing_notes = request.POST.getlist('ingredient_notes')
            
            for i, item_id in enumerate(item_ids):
                if item_id:
                    ingredients.append({
                        'inventory_item_id': int(item_id),
                        'quantity_required': Decimal(quantities[i] if i < len(quantities) else '0'),
                        'unit_of_measure': units[i] if i < len(units) else '',
                        'notes': ing_notes[i] if i < len(ing_notes) else '',
                    })
            
            mix = MixService.create_mix_with_ingredients(
                product_id=product.id,
                name=name,
                expected_yield=expected_yield,
                is_fixed_yield=is_fixed_yield,
                ingredients=ingredients,
                created_by=request.user,
                yield_variance_min=Decimal(yield_variance_min) if yield_variance_min else None,
                yield_variance_max=Decimal(yield_variance_max) if yield_variance_max else None,
                notes=notes
            )
            
            messages.success(request, f"Recipe '{mix.name}' created with {len(ingredients)} ingredients!")
            return redirect('products:detail', product_id=product.id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, str(e))
    
    context = {
        'product': product,
        'inventory_items': inventory_items,
    }
    return render(request, 'products/mix_form.html', context)


@login_required
def mix_detail(request, mix_id):
    """
    View mix/recipe details with all ingredients.
    """
    mix = get_object_or_404(
        Mix.objects.select_related('product').prefetch_related('ingredients'),
        id=mix_id
    )
    
    # Separate ingredients and indirect costs
    ingredients = [ing for ing in mix.ingredients.all() if ing.is_ingredient()]
    indirect_costs = [ing for ing in mix.ingredients.all() if ing.is_indirect_cost()]
    
    context = {
        'mix': mix,
        'product': mix.product,
        'ingredients': ingredients,
        'indirect_costs': indirect_costs,
    }
    return render(request, 'products/mix_detail.html', context)


@login_required
def mix_edit(request, mix_id):
    """
    Edit an existing mix/recipe.
    Admin only.
    """
    mix = get_object_or_404(
        Mix.objects.select_related('product').prefetch_related('ingredients'),
        id=mix_id
    )
    
    # Get inventory items for dropdown
    try:
        from apps.inventory.routing import get_items_for_dropdown
        inventory_items = get_items_for_dropdown()
    except ImportError:
        inventory_items = [(i, f"Item {i}") for i in range(1, 24)]
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            expected_yield = Decimal(request.POST.get('expected_yield', '0'))
            is_fixed_yield = request.POST.get('is_fixed_yield') == 'on'
            yield_variance_min = request.POST.get('yield_variance_min')
            yield_variance_max = request.POST.get('yield_variance_max')
            notes = request.POST.get('notes', '').strip()
            
            # Update mix settings
            MixService.update_mix(
                mix_id=mix.id,
                updated_by=request.user,
                name=name,
                expected_yield=expected_yield,
                is_fixed_yield=is_fixed_yield,
                yield_variance_min=Decimal(yield_variance_min) if yield_variance_min else None,
                yield_variance_max=Decimal(yield_variance_max) if yield_variance_max else None,
                notes=notes
            )
            
            # Parse and update ingredients
            ingredients = []
            item_ids = request.POST.getlist('ingredient_item_id')
            quantities = request.POST.getlist('ingredient_quantity')
            units = request.POST.getlist('ingredient_unit')
            ing_notes = request.POST.getlist('ingredient_notes')
            
            for i, item_id in enumerate(item_ids):
                if item_id:
                    ingredients.append({
                        'inventory_item_id': int(item_id),
                        'quantity_required': Decimal(quantities[i] if i < len(quantities) else '0'),
                        'unit_of_measure': units[i] if i < len(units) else '',
                        'notes': ing_notes[i] if i < len(ing_notes) else '',
                    })
            
            if ingredients:
                MixService.update_mix_ingredients(
                    mix_id=mix.id,
                    ingredients=ingredients,
                    updated_by=request.user
                )
            
            messages.success(request, f"Recipe '{mix.name}' updated successfully!")
            return redirect('products:detail', product_id=mix.product.id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, str(e))
    
    context = {
        'mix': mix,
        'product': mix.product,
        'inventory_items': inventory_items,
        'is_edit': True,
    }
    return render(request, 'products/mix_form.html', context)


@login_required
@require_POST
def mix_archive(request, mix_id):
    """
    Archive (soft delete) a mix.
    Admin only.
    """
    mix = get_object_or_404(Mix, id=mix_id)
    product_id = mix.product.id
    
    try:
        MixService.archive_mix(mix_id, request.user)
        messages.success(request, f"Recipe '{mix.name}' archived.")
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('products:detail', product_id=product_id)


@login_required
@require_POST
def mix_restore(request, mix_id):
    """
    Restore an archived mix.
    Admin only.
    """
    mix = get_object_or_404(Mix, id=mix_id)
    product_id = mix.product.id
    
    try:
        MixService.restore_mix(mix_id, request.user)
        messages.success(request, f"Recipe '{mix.name}' restored.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('products:detail', product_id=product_id)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@login_required
@require_GET
def api_products_list(request):
    """
    Get list of active products (for AJAX dropdowns).
    
    Returns:
        JSON: {products: [{id, name, price}, ...]}
    """
    products = Product.objects.filter(is_active=True).values('id', 'name', 'selling_price')
    return JsonResponse({
        'products': [
            {
                'id': p['id'],
                'name': p['name'],
                'price': str(p['selling_price'])
            }
            for p in products
        ]
    })


@login_required
@require_GET
def api_product_detail(request, product_id):
    """
    Get product details for AJAX.
    
    Returns:
        JSON: {product: {id, name, price, has_mix}, mix: {...} or null}
    """
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        active_mix = product.get_active_mix()
        
        return JsonResponse({
            'product': {
                'id': product.id,
                'name': product.name,
                'price': str(product.selling_price),
                'has_mix': active_mix is not None,
            },
            'mix': active_mix.get_snapshot_data() if active_mix else None
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_GET
def api_product_mix(request, product_id):
    """
    Get active mix data for a product (for Production app integration).
    
    Returns:
        JSON: Mix snapshot data or error
    """
    result = MixService.get_active_mix_for_product(product_id)
    
    if result['success']:
        return JsonResponse(result['data'])
    else:
        return JsonResponse({'error': result['error']}, status=404)
