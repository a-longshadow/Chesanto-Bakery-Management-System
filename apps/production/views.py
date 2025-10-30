"""
Production Views for Chesanto Bakery Management System
Implements daily production tracking, batch recording, indirect costs, and book closing
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q
from datetime import datetime, timedelta
from datetime import date as date_class
from decimal import Decimal

from .models import DailyProduction, ProductionBatch, IndirectCost
from apps.products.models import Product, Mix
from apps.accounts.models import User


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def can_edit_production(user, daily_production):
    """
    Check if user can edit production data
    Rules:
    - Before 9PM: All authorized users can edit
    - After 9PM (books closed): Only Admin/CEO/Manager can edit
    - BASIC_USER: Cannot edit at all
    """
    if user.role == 'BASIC_USER':
        return False
    
    if not daily_production.is_closed:
        return True
    
    # Books closed - only Admin/CEO/Manager can edit
    return user.role in ['SUPERADMIN', 'CEO', 'MANAGER']


def get_or_create_daily_production(date_obj, user):
    """Get or create DailyProduction for a specific date"""
    daily_production, created = DailyProduction.objects.get_or_create(
        date=date_obj,
        defaults={
            'created_by': user,
            'updated_by': user
        }
    )
    
    # If newly created, set opening stock from previous day's closing
    if created:
        try:
            previous_day = date_obj - timedelta(days=1)
            previous_production = DailyProduction.objects.get(date=previous_day)
            
            daily_production.opening_bread_stock = previous_production.closing_bread_stock
            daily_production.opening_kdf_stock = previous_production.closing_kdf_stock
            daily_production.opening_scones_stock = previous_production.closing_scones_stock
            daily_production.save()
        except DailyProduction.DoesNotExist:
            # No previous day - opening stock stays at 0
            pass
    
    return daily_production


# ============================================================================
# MAIN VIEWS
# ============================================================================

@login_required
def daily_production_today(request):
    """
    Redirect to today's production dashboard
    Main entry point for production app
    """
    today = date_class.today()
    return redirect('production:daily_production_date', date=today.strftime('%Y-%m-%d'))


@login_required
def daily_production_view(request, date):
    """
    Display daily production dashboard for a specific date
    Shows:
    - Stock summary (opening, produced, dispatched, returned, closing)
    - All batches for the day with P&L
    - Indirect costs summary
    - Book closing status
    """
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date format.')
        return redirect('production:daily_production')
    
    # Get or create daily production record
    daily_production = get_or_create_daily_production(date_obj, request.user)
    
    # Get all batches for this day
    batches = daily_production.batches.select_related('mix__product').order_by('batch_number')
    
    # Check if user can edit
    can_edit = can_edit_production(request.user, daily_production)
    
    # Calculate time until 9PM (for countdown timer)
    now = timezone.now()
    today_9pm = now.replace(hour=21, minute=0, second=0, microsecond=0)
    if date_obj == date_class.today() and now < today_9pm:
        time_until_closing = today_9pm - now
        hours_left = int(time_until_closing.total_seconds() // 3600)
        minutes_left = int((time_until_closing.total_seconds() % 3600) // 60)
        show_countdown = True
    else:
        hours_left = 0
        minutes_left = 0
        show_countdown = False
    
    # Calculate totals for display
    total_batches = batches.count()
    total_ingredient_cost = batches.aggregate(total=Sum('ingredient_cost'))['total'] or Decimal('0')
    total_packaging_cost = batches.aggregate(total=Sum('packaging_cost'))['total'] or Decimal('0')
    total_allocated_indirect = batches.aggregate(total=Sum('allocated_indirect_cost'))['total'] or Decimal('0')
    total_cost = batches.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
    total_revenue = batches.aggregate(total=Sum('expected_revenue'))['total'] or Decimal('0')
    total_profit = batches.aggregate(total=Sum('gross_profit'))['total'] or Decimal('0')
    
    # Calculate average margin
    if total_revenue > 0:
        avg_margin = (total_profit / total_revenue * 100)
    else:
        avg_margin = Decimal('0')
    
    context = {
        'date': date_obj,
        'daily_production': daily_production,
        'batches': batches,
        'can_edit': can_edit,
        'show_countdown': show_countdown,
        'hours_left': hours_left,
        'minutes_left': minutes_left,
        'total_batches': total_batches,
        'total_ingredient_cost': total_ingredient_cost,
        'total_packaging_cost': total_packaging_cost,
        'total_allocated_indirect': total_allocated_indirect,
        'total_cost': total_cost,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'avg_margin': avg_margin,
    }
    
    return render(request, 'production/daily_production.html', context)


@login_required
def batch_create(request, date=None):
    """
    Create new production batch
    - Select mix
    - Enter actual output
    - Auto-calculate costs and P&L
    """
    # Get date from URL parameter or default to today
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            date_obj = date_class.today()
    else:
        date_param = request.GET.get('date', date_class.today().strftime('%Y-%m-%d'))
        try:
            date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            date_obj = date_class.today()
    
    # Get or create daily production
    daily_production = get_or_create_daily_production(date_obj, request.user)
    
    # Check permissions
    if not can_edit_production(request.user, daily_production):
        messages.error(request, 'You do not have permission to add batches to closed books.')
        return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
    
    if request.method == 'POST':
        # Get form data
        mix_id = request.POST.get('mix')
        batch_number = request.POST.get('batch_number')
        actual_packets = request.POST.get('actual_packets')
        rejects_produced = request.POST.get('rejects_produced', '0')  # Default to string '0'
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        quality_notes = request.POST.get('quality_notes', '')
        
        # Debug logging
        print(f"📝 Form data received:")
        print(f"   mix_id: '{mix_id}' (type: {type(mix_id).__name__})")
        print(f"   batch_number: '{batch_number}' (type: {type(batch_number).__name__})")
        print(f"   actual_packets: '{actual_packets}' (type: {type(actual_packets).__name__})")
        print(f"   rejects_produced: '{rejects_produced}' (type: {type(rejects_produced).__name__})")
        
        # Validation
        if not all([mix_id, batch_number, actual_packets]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'production/production_batch_form.html', {
                'daily_production': daily_production,
                'mixes': Mix.objects.filter(is_active=True),
                'date': date_obj,
            })
        
        try:
            mix = Mix.objects.get(id=mix_id)
            batch_number = int(batch_number)
            actual_packets = int(actual_packets)
            # Handle empty string for rejects (convert empty to 0)
            rejects_value = str(rejects_produced).strip()
            rejects_produced = int(rejects_value) if rejects_value and rejects_value != '' else 0
            print(f"✅ Converted values: batch_number={batch_number}, actual_packets={actual_packets}, rejects_produced={rejects_produced}")
            
            # Check if batch number already exists for this date
            existing_batch = ProductionBatch.objects.filter(
                daily_production=daily_production,
                batch_number=batch_number
            ).first()
            
            if existing_batch:
                messages.error(
                    request, 
                    f'❌ Batch #{batch_number} already exists for today. Please use a different batch number.'
                )
                return render(request, 'production/production_batch_form.html', {
                    'daily_production': daily_production,
                    'mixes': Mix.objects.filter(is_active=True),
                    'date': date_obj,
                    'suggested_batch_number': batch_number + 1,
                })
            
            # Validate rejects only for Bread
            if rejects_produced > 0 and mix.product.name != 'Bread':
                messages.error(request, '❌ Only Bread can have rejects. Please set rejects to 0 for other products.')
                return render(request, 'production/production_batch_form.html', {
                    'daily_production': daily_production,
                    'mixes': Mix.objects.filter(is_active=True),
                    'date': date_obj,
                    'suggested_batch_number': batch_number,
                })
            
            # Check if we have enough ingredients before creating batch
            mix_ingredients = mix.mixingredient_set.all()
            low_stock_items = []
            
            for mix_ingredient in mix_ingredients:
                if mix_ingredient.ingredient.inventory_item:
                    inventory_item = mix_ingredient.ingredient.inventory_item
                    quantity_needed = mix_ingredient.quantity
                    
                    # Convert units if necessary
                    if mix_ingredient.unit != inventory_item.recipe_unit:
                        if mix_ingredient.unit == 'kg' and inventory_item.recipe_unit == 'g':
                            quantity_needed = quantity_needed * 1000
                        elif mix_ingredient.unit == 'g' and inventory_item.recipe_unit == 'kg':
                            quantity_needed = quantity_needed / 1000
                        elif mix_ingredient.unit == 'l' and inventory_item.recipe_unit == 'ml':
                            quantity_needed = quantity_needed * 1000
                        elif mix_ingredient.unit == 'ml' and inventory_item.recipe_unit == 'l':
                            quantity_needed = quantity_needed / 1000
                    
                    if inventory_item.current_stock < quantity_needed:
                        low_stock_items.append(
                            f"{inventory_item.name}: Need {quantity_needed:.1f} {inventory_item.recipe_unit}, "
                            f"but only {inventory_item.current_stock:.1f} {inventory_item.recipe_unit} available"
                        )
            
            if low_stock_items:
                messages.error(
                    request,
                    f'❌ Insufficient stock to create this batch. Please restock the following items:'
                )
                for item in low_stock_items:
                    messages.warning(request, f'⚠️ {item}')
                return render(request, 'production/production_batch_form.html', {
                    'daily_production': daily_production,
                    'mixes': Mix.objects.filter(is_active=True),
                    'date': date_obj,
                    'suggested_batch_number': batch_number,
                })
            
            # Create batch
            batch = ProductionBatch.objects.create(
                daily_production=daily_production,
                mix=mix,
                batch_number=batch_number,
                actual_packets=actual_packets,
                rejects_produced=rejects_produced,
                start_time=start_time if start_time else None,
                end_time=end_time if end_time else None,
                quality_notes=quality_notes,
                created_by=request.user,
                updated_by=request.user
            )
            
            # Allocate indirect costs to all batches
            allocate_all_indirect_costs(daily_production)
            
            messages.success(request, f'✅ Batch #{batch_number} for {mix.product.name} created successfully!')
            return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
            
        except Mix.DoesNotExist:
            messages.error(request, '❌ Invalid mix selected. Please select a valid mix from the list.')
        except ValueError as e:
            error_msg = str(e).lower()
            if 'invalid literal' in error_msg:
                messages.error(request, '❌ Please enter valid numbers for batch number, packets, and rejects.')
            else:
                messages.error(request, f'❌ Invalid number format: Please check your entries and try again.')
        except Exception as e:
            error_msg = str(e).lower()
            error_class = type(e).__name__
            
            # Handle specific error types with user-friendly messages
            if 'constraint' in error_msg or 'unique' in error_msg:
                messages.error(
                    request,
                    f'❌ This batch number is already in use. Please use batch #{batch_number + 1} instead.'
                )
            elif 'foreign' in error_msg or 'does not exist' in error_msg:
                messages.error(
                    request,
                    f'❌ Invalid data reference. Please ensure all products and mixes are properly configured.'
                )
            elif 'cannot be null' in error_msg or 'required' in error_msg:
                messages.error(
                    request,
                    f'❌ Missing required information. Please fill in all required fields.'
                )
            elif error_class == 'InvalidOperation' or 'invalidoperation' in error_msg:
                messages.error(
                    request,
                    f'❌ Invalid number format detected. Error: {str(e)}. Please check all numeric fields.'
                )
                print(f"🔍 InvalidOperation debug:")
                print(f"   Form values: batch={batch_number if 'batch_number' in locals() else 'N/A'}, "
                      f"packets={actual_packets if 'actual_packets' in locals() else 'N/A'}, "
                      f"rejects={rejects_produced if 'rejects_produced' in locals() else 'N/A'}")
                print(f"   Error: {type(e).__name__} - {str(e)}")
            else:
                # Show technical error for debugging
                messages.error(
                    request,
                    f'❌ Error creating batch: {str(e)}. Please contact your administrator if this persists.'
                )
                # Log the technical error for debugging
                print(f"⚠️ Technical error creating batch (Batch #{batch_number if 'batch_number' in locals() else 'N/A'}, Mix: {mix.name if 'mix' in locals() else 'N/A'}): {error_class} - {str(e)}")
        
        # If we get here, there was an error - re-render the form
        return render(request, 'production/production_batch_form.html', {
            'daily_production': daily_production,
            'mixes': Mix.objects.filter(is_active=True),
            'date': date_obj,
            'suggested_batch_number': batch_number if 'batch_number' in locals() else 1,
        })
    
    # GET request - show form
    mixes = Mix.objects.filter(is_active=True).select_related('product')
    
    # Suggest next batch number
    last_batch = daily_production.batches.order_by('-batch_number').first()
    suggested_batch_number = (last_batch.batch_number + 1) if last_batch else 1
    
    context = {
        'daily_production': daily_production,
        'mixes': mixes,
        'date': date_obj,
        'suggested_batch_number': suggested_batch_number,
    }
    
    return render(request, 'production/production_batch_form.html', context)


@login_required
def batch_detail(request, pk):
    """
    Display detailed view of a production batch
    Shows all fields including P&L breakdown
    """
    batch = get_object_or_404(ProductionBatch.objects.select_related(
        'mix__product',
        'daily_production',
        'created_by',
        'updated_by'
    ), pk=pk)
    
    can_edit = can_edit_production(request.user, batch.daily_production)
    
    context = {
        'batch': batch,
        'can_edit': can_edit,
    }
    
    return render(request, 'production/batch_detail.html', context)


@login_required
def batch_edit(request, pk):
    """
    Edit existing production batch
    Only Admin/CEO/Manager can edit finalized batches
    """
    batch = get_object_or_404(ProductionBatch, pk=pk)
    daily_production = batch.daily_production
    
    # Check permissions
    if not can_edit_production(request.user, daily_production):
        messages.error(request, 'You do not have permission to edit this batch.')
        return redirect('production:batch_detail', pk=pk)
    
    if request.method == 'POST':
        # Update fields
        try:
            batch.actual_packets = int(request.POST.get('actual_packets'))
            # Handle empty string for rejects
            rejects_value = request.POST.get('rejects_produced', '0')
            batch.rejects_produced = int(rejects_value) if rejects_value and rejects_value.strip() else 0
            batch.start_time = request.POST.get('start_time') or None
            batch.end_time = request.POST.get('end_time') or None
            batch.quality_notes = request.POST.get('quality_notes', '')
            batch.updated_by = request.user
            
            # Validate rejects
            if batch.rejects_produced > 0 and batch.mix.product.name != 'Bread':
                messages.error(request, 'Only Bread can have rejects.')
                raise ValueError('Invalid rejects')
            
            batch.save()
            
            # Reallocate indirect costs
            allocate_all_indirect_costs(daily_production)
            
            messages.success(request, 'Batch updated successfully.')
            return redirect('production:batch_detail', pk=pk)
            
        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating batch: {str(e)}')
    
    # GET request - show form with existing data
    mixes = Mix.objects.filter(is_active=True).select_related('product')
    
    context = {
        'batch': batch,
        'daily_production': daily_production,
        'mixes': mixes,
        'date': daily_production.date,
        'is_edit': True,
    }
    
    return render(request, 'production/production_batch_form.html', context)


@login_required
def indirect_costs_form(request, date):
    """
    Enter or update daily indirect costs
    - Diesel, firewood, electricity, fuel distribution, other
    - Auto-calculates total
    - Triggers reallocation to all batches
    """
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date format.')
        return redirect('production:daily_production')
    
    # Get or create daily production
    daily_production = get_or_create_daily_production(date_obj, request.user)
    
    # Check permissions
    if not can_edit_production(request.user, daily_production):
        messages.error(request, 'You do not have permission to edit closed books.')
        return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
    
    if request.method == 'POST':
        try:
            # Update indirect costs - handle empty strings
            def get_decimal_value(field_name, default='0'):
                """Helper to safely convert form value to Decimal"""
                value = request.POST.get(field_name, default)
                # Handle empty string or None
                if not value or not str(value).strip():
                    return Decimal('0')
                return Decimal(str(value).strip())
            
            daily_production.diesel_cost = get_decimal_value('diesel_cost')
            daily_production.firewood_cost = get_decimal_value('firewood_cost')
            daily_production.electricity_cost = get_decimal_value('electricity_cost')
            daily_production.fuel_distribution_cost = get_decimal_value('fuel_distribution_cost')
            daily_production.other_indirect_costs = get_decimal_value('other_indirect_costs')
            daily_production.reconciliation_notes = request.POST.get('reconciliation_notes', '')
            daily_production.updated_by = request.user
            daily_production.save()
            
            # Reallocate costs to all batches
            allocate_all_indirect_costs(daily_production)
            
            messages.success(request, 'Indirect costs updated successfully.')
            return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
            
        except ValueError as e:
            messages.error(request, f'Invalid cost value: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating costs: {str(e)}')
    
    context = {
        'daily_production': daily_production,
        'date': date_obj,
    }
    
    return render(request, 'production/indirect_costs_form.html', context)


@login_required
def close_books(request, date):
    """
    Manual book closing for a specific date
    - Locks all edits (except Admin/CEO/Manager)
    - Calculates final closing stock
    - Checks for reconciliation variance > 5%
    - Sets opening stock for next day
    """
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date format.')
        return redirect('production:daily_production')
    
    # Get daily production
    try:
        daily_production = DailyProduction.objects.get(date=date_obj)
    except DailyProduction.DoesNotExist:
        messages.error(request, 'No production record found for this date.')
        return redirect('production:daily_production')
    
    # Check if already closed
    if daily_production.is_closed:
        messages.info(request, 'Books are already closed for this date.')
        return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
    
    # Check permissions (staff only)
    if not request.user.is_staff:
        messages.error(request, 'Only staff members can close books.')
        return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
    
    if request.method == 'POST':
        # User confirmed - close books
        daily_production.close_books(request.user)
        
        # Finalize all batches
        daily_production.batches.update(is_finalized=True)
        
        # Check for variance warning
        if daily_production.has_variance:
            messages.warning(
                request,
                f'Books closed with {daily_production.variance_percentage:.1f}% variance (threshold: 5%). '
                f'Please review reconciliation notes.'
            )
        else:
            messages.success(request, 'Books closed successfully for this date.')
        
        # Set opening stock for next day
        next_day = date_obj + timedelta(days=1)
        next_daily_production, created = DailyProduction.objects.get_or_create(
            date=next_day,
            defaults={
                'opening_bread_stock': daily_production.closing_bread_stock,
                'opening_kdf_stock': daily_production.closing_kdf_stock,
                'opening_scones_stock': daily_production.closing_scones_stock,
                'created_by': request.user,
                'updated_by': request.user,
            }
        )
        
        if not created:
            # Update opening stock if next day already exists
            next_daily_production.opening_bread_stock = daily_production.closing_bread_stock
            next_daily_production.opening_kdf_stock = daily_production.closing_kdf_stock
            next_daily_production.opening_scones_stock = daily_production.closing_scones_stock
            next_daily_production.save()
        
        return redirect('production:daily_production_date', date=date_obj.strftime('%Y-%m-%d'))
    
    # GET request - show confirmation page
    batches = daily_production.batches.all()
    total_batches = batches.count()
    
    context = {
        'daily_production': daily_production,
        'date': date_obj,
        'total_batches': total_batches,
    }
    
    return render(request, 'production/book_closing_view.html', context)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def allocate_all_indirect_costs(daily_production):
    """
    Reallocate indirect costs to all batches proportionally
    Called after batch changes or indirect cost updates
    """
    batches = daily_production.batches.all()
    
    if not batches.exists():
        return
    
    # Calculate total ingredient cost across all batches
    total_ingredient_cost = sum(batch.ingredient_cost for batch in batches)
    
    if total_ingredient_cost == 0:
        return
    
    # Allocate proportionally to each batch
    for batch in batches:
        proportion = batch.ingredient_cost / total_ingredient_cost
        batch.allocated_indirect_cost = proportion * daily_production.total_indirect_costs
        batch.calculate_costs()
        batch.calculate_pl()
        batch.save()
