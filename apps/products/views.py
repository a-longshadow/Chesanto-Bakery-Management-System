from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
import json
from .models import Product, Mix, Ingredient, MixIngredient


@login_required
def product_list(request):
    """
    Display all active products
    Filter by active status
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    
    context = {
        'products': products,
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, pk):
    """
    Display product details including all mixes
    """
    product = get_object_or_404(Product, pk=pk)
    mixes = product.mixes.all().prefetch_related('mixingredient_set__ingredient')
    
    context = {
        'product': product,
        'mixes': mixes,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def product_create(request):
    """
    Create new product (Super Admin, CEO, Manager only)
    """
    # Permission check
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER']:
        messages.error(request, "You don't have permission to create products.")
        return redirect('products:product_list')
    
    if request.method == 'POST':
        # Extract form data
        name = request.POST.get('name')
        alias = request.POST.get('alias', '')
        price_per_packet = request.POST.get('price_per_packet')
        packet_label = request.POST.get('packet_label', 'packet')
        baseline_output = request.POST.get('baseline_output')
        has_variable_output = request.POST.get('has_variable_output') == 'on'
        has_sub_product = request.POST.get('has_sub_product') == 'on'
        sub_product_name = request.POST.get('sub_product_name', '')
        sub_product_price = request.POST.get('sub_product_price')
        description = request.POST.get('description', '')
        
        # Validation
        if not all([name, price_per_packet, baseline_output]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('products:product_create')
        
        try:
            # Create product
            product = Product.objects.create(
                name=name,
                alias=alias if alias else None,
                price_per_packet=price_per_packet,
                packet_label=packet_label,
                baseline_output=baseline_output,
                has_variable_output=has_variable_output,
                has_sub_product=has_sub_product,
                sub_product_name=sub_product_name if has_sub_product else '',
                sub_product_price=sub_product_price if has_sub_product and sub_product_price else None,
                description=description,
                created_by=request.user
            )
            
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('products:product_detail', pk=product.id)
            
        except Exception as e:
            messages.error(request, f"Error creating product: {str(e)}")
            return redirect('products:product_create')
    
    # GET request - show form
    parent_products = Product.objects.filter(is_active=True, has_sub_product=False)
    
    context = {
        'parent_products': parent_products,
        'form': {'instance': Product()},  # Empty form for template compatibility
    }
    return render(request, 'products/product_form.html', context)


@login_required
def product_update(request, pk):
    """
    Update existing product (Super Admin, CEO, Manager only)
    """
    # Permission check
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER']:
        messages.error(request, "You don't have permission to update products.")
        return redirect('products:product_list')
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # Extract form data
        product.name = request.POST.get('name')
        product.alias = request.POST.get('alias', '') or None
        product.price_per_packet = request.POST.get('price_per_packet')
        product.packet_label = request.POST.get('packet_label', 'packet')
        product.baseline_output = request.POST.get('baseline_output')
        product.has_variable_output = request.POST.get('has_variable_output') == 'on'
        product.has_sub_product = request.POST.get('has_sub_product') == 'on'
        product.sub_product_name = request.POST.get('sub_product_name', '') if product.has_sub_product else ''
        sub_product_price = request.POST.get('sub_product_price')
        product.sub_product_price = sub_product_price if product.has_sub_product and sub_product_price else None
        product.description = request.POST.get('description', '')
        product.is_active = request.POST.get('is_active', 'on') == 'on'
        product.updated_by = request.user
        
        try:
            product.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('products:product_detail', pk=product.id)
        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
    
    # GET request - show form
    parent_products = Product.objects.filter(is_active=True, has_sub_product=False).exclude(pk=pk)
    
    # Create a simple form-like dict for template compatibility
    form = {
        'instance': product,
        'name': {'value': product.name},
        'alias': {'value': product.alias or ''},
        'price_per_packet': {'value': product.price_per_packet},
        'packet_label': {'value': product.packet_label},
        'baseline_output': {'value': product.baseline_output},
        'has_variable_output': {'value': product.has_variable_output},
        'has_sub_product': {'value': product.has_sub_product},
        'sub_product_name': {'value': product.sub_product_name or ''},
        'sub_product_price': {'value': product.sub_product_price if product.sub_product_price else ''},
        'description': {'value': product.description or ''},
    }
    
    context = {
        'form': form,
        'parent_products': parent_products,
        'is_update': True,
    }
    return render(request, 'products/product_form.html', context)


@login_required
def mix_detail(request, pk):
    """
    Display mix details with ingredient breakdown and cost calculation
    """
    mix = get_object_or_404(Mix, pk=pk)
    mix_ingredients = mix.mixingredient_set.select_related('ingredient', 'ingredient__inventory_item').all()
    
    # Calculate profit metrics
    profit_per_unit = Decimal(str(mix.product.price_per_packet)) - mix.cost_per_packet
    if mix.product.price_per_packet > 0:
        profit_margin = (profit_per_unit / Decimal(str(mix.product.price_per_packet))) * 100
    else:
        profit_margin = 0
    
    context = {
        'mix': mix,
        'mix_ingredients': mix_ingredients,
        'profit_per_unit': profit_per_unit,
        'profit_margin': profit_margin,
    }
    return render(request, 'products/mix_detail.html', context)


@login_required
def mix_create(request, product_id):
    """
    Create new mix for a product
    """
    # Permission check
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER']:
        messages.error(request, "You don't have permission to create mixes.")
        return redirect('products:product_list')
    
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        # Extract form data
        name = request.POST.get('name')
        expected_packets = request.POST.get('expected_packets', product.baseline_output)
        
        if not all([name, expected_packets]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('products:mix_create', product_id=product_id)
        
        try:
            # Determine version number (auto-increment)
            existing_mixes = Mix.objects.filter(product=product).count()
            version = existing_mixes + 1
            
            # Create mix
            mix = Mix.objects.create(
                product=product,
                name=name,
                version=version,
                expected_packets=expected_packets,
                created_by=request.user
            )
            
            # Process ingredients
            total_cost = Decimal('0.00')
            ingredient_counter = 1
            
            while f'ingredient_{ingredient_counter}' in request.POST:
                ingredient_id = request.POST.get(f'ingredient_{ingredient_counter}')
                quantity_str = request.POST.get(f'quantity_{ingredient_counter}')
                
                if ingredient_id and quantity_str:
                    try:
                        ingredient = Ingredient.objects.get(pk=ingredient_id)
                        quantity = Decimal(quantity_str)
                        
                        # Create MixIngredient (cost auto-calculates via save method)
                        MixIngredient.objects.create(
                            mix=mix,
                            ingredient=ingredient,
                            quantity=quantity,
                            unit=ingredient.default_unit,
                            added_by=request.user
                        )
                        
                    except (Ingredient.DoesNotExist, ValueError) as e:
                        pass  # Skip invalid ingredients
                
                ingredient_counter += 1
            
            # Recalculate mix costs (will be done automatically via signals)
            mix.calculate_costs()
            
            messages.success(request, f"Mix '{mix.name}' created successfully with {ingredient_counter - 1} ingredients!")
            return redirect('products:mix_detail', pk=mix.id)
            
        except Exception as e:
            messages.error(request, f"Error creating mix: {str(e)}")
            return redirect('products:mix_create', product_id=product_id)
    
    # GET request - show form
    ingredients = Ingredient.objects.filter(is_active=True).select_related('inventory_item').order_by('name')
    
    # Prepare ingredients JSON for JavaScript
    ingredients_json = json.dumps([
        {
            'id': ing.id,
            'name': ing.name,
            'cost_per_unit': float(ing.inventory_item.cost_per_recipe_unit) if ing.inventory_item else 0.0,
            'unit': ing.get_default_unit_display(),
        }
        for ing in ingredients
    ])
    
    context = {
        'product': product,
        'ingredients': ingredients,
        'ingredients_json': ingredients_json,
    }
    return render(request, 'products/mix_form.html', context)


@login_required
def get_ingredient_cost(request, ingredient_id):
    """
    AJAX endpoint to get ingredient cost per recipe unit
    Used for real-time cost calculation in mix forms
    """
    try:
        ingredient = Ingredient.objects.select_related('inventory_item').get(pk=ingredient_id)
        
        # Get cost from linked inventory item
        if ingredient.inventory_item:
            cost_per_unit = float(ingredient.inventory_item.cost_per_recipe_unit)
            unit = ingredient.inventory_item.recipe_unit
        else:
            cost_per_unit = 0.0
            unit = ingredient.default_unit
        
        return JsonResponse({
            'success': True,
            'cost_per_unit': cost_per_unit,
            'unit': unit,
            'ingredient_name': ingredient.name,
        })
    except Ingredient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ingredient not found'
        }, status=404)
