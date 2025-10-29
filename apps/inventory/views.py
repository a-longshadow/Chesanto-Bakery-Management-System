"""
Inventory App Views
Function-based views for inventory management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from decimal import Decimal
from datetime import date

from .models import (
    InventoryItem, ExpenseCategory, Purchase, PurchaseItem,
    WastageRecord, StockMovement, Supplier
)


@login_required
def inventory_list(request):
    """
    Display all inventory items with filters and stock alerts
    """
    items = InventoryItem.objects.filter(is_active=True).select_related('category')
    
    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(category_id=category_id)
    
    stock_level = request.GET.get('stock_level')
    if stock_level == 'critical':
        items = items.filter(days_remaining__lt=3)
    elif stock_level == 'low':
        items = items.filter(low_stock_alert=True, days_remaining__gte=3)
    elif stock_level == 'adequate':
        items = items.filter(low_stock_alert=False)
    
    search = request.GET.get('search')
    if search:
        items = items.filter(name__icontains=search)
    
    # Calculate stock value for each item
    items_with_value = []
    for item in items:
        item.stock_value = item.current_stock * item.cost_per_recipe_unit
        items_with_value.append(item)
    
    # Calculate stats
    total_value = sum(item.stock_value for item in items_with_value)
    low_stock_count = items.filter(low_stock_alert=True).count()
    critical_stock_count = items.filter(days_remaining__lt=3).count()
    
    context = {
        'items': items_with_value,
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'stats': {
            'total_items': items.count(),
            'total_value': total_value,
            'low_stock_count': low_stock_count,
            'critical_stock_count': critical_stock_count,
        }
    }
    
    return render(request, 'inventory/inventory_list.html', context)


@login_required
def inventory_detail(request, pk):
    """
    Display detailed information for a single inventory item
    """
    item = get_object_or_404(InventoryItem, pk=pk)
    
    # Get recent stock movements
    movements = item.movements.all()[:20]
    
    # Get recent purchases
    purchases = item.purchase_items.select_related('purchase').order_by('-purchase__purchase_date')[:10]
    
    # Get recent wastage
    wastage = item.wastage_records.all()[:10]
    
    # Calculate stock value
    stock_value = item.current_stock * item.cost_per_recipe_unit
    
    context = {
        'item': item,
        'movements': movements,
        'purchases': purchases,
        'wastage': wastage,
        'stock_value': stock_value,
    }
    
    return render(request, 'inventory/inventory_detail.html', context)


@login_required
def inventory_create(request):
    """
    Create new inventory item
    Permission: SUPERADMIN, CEO, MANAGER
    """
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER']:
        messages.error(request, 'You do not have permission to add inventory items.')
        return redirect('inventory:item_list')
    
    if request.method == 'POST':
        try:
            # Create inventory item with correct field names
            item = InventoryItem.objects.create(
                name=request.POST.get('name'),
                category_id=request.POST.get('category'),
                description=request.POST.get('description', ''),
                purchase_unit=request.POST.get('purchase_unit'),
                recipe_unit=request.POST.get('recipe_unit'),
                conversion_factor=Decimal(request.POST.get('conversion_factor', '1')),
                current_stock=Decimal(request.POST.get('current_stock', '0')),
                reorder_level=Decimal(request.POST.get('reorder_level')),
                cost_per_purchase_unit=Decimal(request.POST.get('cost_per_purchase_unit')),
                created_by=request.user,
                updated_by=request.user,
            )
            
            messages.success(request, f'Inventory item "{item.name}" created successfully!')
            return redirect('inventory:item_detail', pk=item.pk)
        
        except Exception as e:
            messages.error(request, f'Error creating item: {str(e)}')
    
    context = {
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'form': {},  # Empty dict for template compatibility
    }
    
    return render(request, 'inventory/inventory_form.html', context)


@login_required
def inventory_update(request, pk):
    """
    Update existing inventory item
    Permission: SUPERADMIN, CEO, MANAGER
    """
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER']:
        messages.error(request, 'You do not have permission to edit inventory items.')
        return redirect('inventory:item_list')
    
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        try:
            # Update with correct field names
            item.name = request.POST.get('name')
            item.category_id = request.POST.get('category')
            item.description = request.POST.get('description', '')
            item.purchase_unit = request.POST.get('purchase_unit')
            item.recipe_unit = request.POST.get('recipe_unit')
            item.conversion_factor = Decimal(request.POST.get('conversion_factor', '1'))
            item.current_stock = Decimal(request.POST.get('current_stock', '0'))
            item.reorder_level = Decimal(request.POST.get('reorder_level'))
            item.cost_per_purchase_unit = Decimal(request.POST.get('cost_per_purchase_unit'))
            item.updated_by = request.user
            item.save()
            
            messages.success(request, f'Inventory item "{item.name}" updated successfully!')
            return redirect('inventory:item_detail', pk=item.pk)
        
        except Exception as e:
            messages.error(request, f'Error updating item: {str(e)}')
    
    context = {
        'item': item,
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'form': {},  # Empty dict for template compatibility
    }
    
    return render(request, 'inventory/inventory_form.html', context)


# Purchase Views

@login_required
def purchase_list(request):
    """
    Display all purchases with filters
    """
    purchases = Purchase.objects.select_related('supplier').order_by('-purchase_date')
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        purchases = purchases.filter(status=status)
    
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        purchases = purchases.filter(supplier_id=supplier_id)
    
    search = request.GET.get('search')
    if search:
        purchases = purchases.filter(
            Q(purchase_number__icontains=search) |
            Q(supplier__name__icontains=search)
        )
    
    context = {
        'purchases': purchases,
        'suppliers': Supplier.objects.filter(is_active=True),
    }
    
    return render(request, 'inventory/purchase_list.html', context)


@login_required
def purchase_create(request):
    """
    Create new purchase order
    Permission: SUPERADMIN, CEO, MANAGER, ACCOUNTANT
    """
    if request.user.role not in ['SUPERADMIN', 'CEO', 'MANAGER', 'ACCOUNTANT']:
        messages.error(request, 'You do not have permission to create purchases.')
        return redirect('inventory:purchase_list')
    
    if request.method == 'POST':
        try:
            # Generate purchase number
            today = date.today()
            count = Purchase.objects.filter(purchase_date=today).count() + 1
            purchase_number = f"PUR-{today.strftime('%Y%m%d')}-{count:03d}"
            
            # Create purchase with correct field names
            purchase = Purchase.objects.create(
                purchase_number=purchase_number,
                supplier_id=request.POST.get('supplier'),
                purchase_date=request.POST.get('purchase_date'),
                expected_delivery_date=request.POST.get('expected_delivery_date') or None,
                status=request.POST.get('status', 'DRAFT'),
                notes=request.POST.get('notes', ''),
                created_by=request.user,
                updated_by=request.user,
            )
            
            messages.success(request, f'Purchase {purchase.purchase_number} created successfully!')
            return redirect('inventory:purchase_detail', pk=purchase.pk)
        
        except Exception as e:
            messages.error(request, f'Error creating purchase: {str(e)}')
    
    context = {
        'suppliers': Supplier.objects.filter(is_active=True),
        'items': InventoryItem.objects.filter(is_active=True).select_related('category'),
        'form': {},
        'today': date.today(),
    }
    
    return render(request, 'inventory/purchase_form.html', context)


@login_required
def purchase_detail(request, pk):
    """
    Display purchase details with items
    """
    purchase = get_object_or_404(Purchase, pk=pk)
    items = purchase.purchaseitem_set.select_related('item').all()
    
    context = {
        'purchase': purchase,
        'items': items,
    }
    
    return render(request, 'inventory/purchase_detail.html', context)


# Wastage Views

@login_required
def wastage_list(request):
    """
    Display all wastage records with filters
    """
    wastage = WastageRecord.objects.select_related('item', 'created_by').order_by('-damage_date')
    
    # Apply filters
    approval_status = request.GET.get('approval_status')
    if approval_status:
        wastage = wastage.filter(approval_status=approval_status)
    
    damage_type = request.GET.get('damage_type')
    if damage_type:
        wastage = wastage.filter(damage_type=damage_type)
    
    search = request.GET.get('search')
    if search:
        wastage = wastage.filter(item__name__icontains=search)
    
    context = {
        'wastage_records': wastage,
    }
    
    return render(request, 'inventory/wastage_list.html', context)


@login_required
def wastage_create(request):
    """
    Create new wastage record
    """
    if request.method == 'POST':
        try:
            # Create wastage record with correct field names
            wastage = WastageRecord.objects.create(
                item_id=request.POST.get('item'),
                damage_type=request.POST.get('damage_type'),
                quantity=Decimal(request.POST.get('quantity')),
                damage_date=request.POST.get('damage_date'),
                description=request.POST.get('description', ''),
                created_by=request.user,
            )
            
            # Deduct from stock
            item = wastage.item
            item.current_stock -= wastage.quantity
            item.save()
            
            # Create stock movement
            StockMovement.objects.create(
                item=item,
                movement_type='DAMAGE',
                quantity=-wastage.quantity,
                unit=item.recipe_unit,
                reference_type='WastageRecord',
                reference_id=wastage.id,
                stock_before=item.current_stock + wastage.quantity,
                stock_after=item.current_stock,
                notes=f"Damage: {wastage.get_damage_type_display()}",
                created_by=request.user,
            )
            
            if wastage.requires_approval:
                messages.warning(
                    request, 
                    f'Wastage record created (KES {wastage.cost}). CEO approval required (> KES 500).'
                )
            else:
                messages.success(request, f'Wastage record created successfully!')
            
            return redirect('inventory:wastage_list')
        
        except Exception as e:
            messages.error(request, f'Error creating wastage record: {str(e)}')
    
    context = {
        'items': InventoryItem.objects.filter(is_active=True).select_related('category'),
        'form': {},
        'today': date.today(),
    }
    
    return render(request, 'inventory/wastage_form.html', context)


@login_required
def wastage_approve(request, pk):
    """
    Approve wastage record (CEO only)
    """
    if request.user.role not in ['SUPERADMIN', 'CEO']:
        messages.error(request, 'Only CEO can approve wastage records.')
        return redirect('inventory:wastage_list')
    
    wastage = get_object_or_404(WastageRecord, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            wastage.approval_status = 'APPROVED'
            wastage.approved_by = request.user
            wastage.approved_at = date.today()
            wastage.approval_notes = request.POST.get('approval_notes', '')
            wastage.save()
            
            messages.success(request, f'Wastage record approved (KES {wastage.cost}).')
        
        elif action == 'reject':
            wastage.approval_status = 'REJECTED'
            wastage.approved_by = request.user
            wastage.approved_at = date.today()
            wastage.approval_notes = request.POST.get('approval_notes', '')
            wastage.save()
            
            # Restore stock if rejected
            item = wastage.item
            item.current_stock += wastage.quantity
            item.save()
            
            messages.info(request, f'Wastage record rejected. Stock restored.')
        
        return redirect('inventory:wastage_list')
    
    context = {
        'wastage': wastage,
    }
    
    return render(request, 'inventory/wastage_approve.html', context)


# Stock Movement Views

@login_required
def movement_list(request):
    """
    Display stock movement audit trail
    """
    movements = StockMovement.objects.select_related(
        'item', 'created_by'
    ).order_by('-created_at')
    
    # Apply filters
    item_id = request.GET.get('item')
    if item_id:
        movements = movements.filter(item_id=item_id)
    
    movement_type = request.GET.get('movement_type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    
    # Limit to recent 100 movements
    movements = movements[:100]
    
    context = {
        'movements': movements,
        'items': InventoryItem.objects.filter(is_active=True),
    }
    
    return render(request, 'inventory/movement_list.html', context)
