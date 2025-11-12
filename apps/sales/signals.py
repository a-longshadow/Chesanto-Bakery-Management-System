"""
Sales App Signals
Handles deficit alerts, commission calculations, and production updates
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
from .models import SalesReturn, Dispatch, DispatchItem, SalesReturnItem


@receiver(post_save, sender=SalesReturn)
def send_deficit_alerts(sender, instance, created, **kwargs):
    """
    DEFICIT ALERTS DISABLED: Fields removed in sales returns overhaul
    The new two-phase workflow handles deficits differently
    """
    # Deficit alerts disabled - new workflow doesn't use deficit fields
    return


@receiver(post_save, sender=SalesReturn)
def detect_deficit_patterns(sender, instance, **kwargs):
    """
    DEFICIT PATTERN DETECTION DISABLED: Fields removed in sales returns overhaul
    The new two-phase workflow handles deficits differently
    """
    # Deficit pattern detection disabled - new workflow doesn't use deficit fields
    return


@receiver(post_save, sender=DispatchItem)
def update_daily_production_on_dispatch(sender, instance, **kwargs):
    """
    DISABLED: Explicit updates now handled in dispatch_create/dispatch_edit views
    This signal was causing duplicate/incorrect stock calculations during edits
    
    When DispatchItem is created/updated, update DailyProduction.dispatched quantities
    This ensures Production → Sales chain is complete
    """
    # Signal disabled - updates now explicit in views to prevent edit bugs
    return
    
    from apps.production.models import DailyProduction
    from django.db.models import Sum
    
    dispatch = instance.dispatch
    product = instance.product
    
    try:
        daily_production, created = DailyProduction.objects.get_or_create(
            date=dispatch.date
        )
        
        # Aggregate ALL dispatch quantities for this product on this date
        total_dispatched = DispatchItem.objects.filter(
            dispatch__date=dispatch.date,
            product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Update the corresponding field
        if product.name == 'Bread':
            daily_production.bread_dispatched = total_dispatched
        elif product.name == 'KDF':
            daily_production.kdf_dispatched = total_dispatched
        elif product.name == 'Scones':
            daily_production.scones_dispatched = total_dispatched
        
        daily_production.save(update_fields=[
            'bread_dispatched', 'kdf_dispatched', 'scones_dispatched',
            'closing_bread_stock', 'closing_kdf_stock', 'closing_scones_stock',
            'updated_at'
        ])
        
        print(f"✅ Updated DailyProduction {dispatch.date}: {product.name} dispatched = {total_dispatched}")
        
    except Exception as e:
        print(f"❌ Failed to update DailyProduction on dispatch: {e}")


@receiver(post_save, sender=SalesReturnItem)
def update_daily_production_on_return(sender, instance, **kwargs):
    """
    DISABLED: Explicit updates now handled in sales_return_create view
    This signal was causing duplicate/incorrect stock calculations
    
    When SalesReturnItem is created/updated, update DailyProduction.returned quantities
    This closes the loop: Production → Dispatch → Return → Closing Stock
    """
    # Signal disabled - updates now explicit in views to prevent edit bugs
    return


@receiver(post_save, sender=SalesReturn)


@receiver(pre_save, sender=DispatchItem)
def populate_dispatch_item_from_dispatch(sender, instance, **kwargs):
    """
    Auto-populate units_dispatched in SalesReturnItem when dispatch created
    """
    # This runs when DispatchItem is saved
    # We'll create or update the corresponding SalesReturnItem if return exists
    pass  # Handled in SalesReturnItem creation


@receiver(post_save, sender=DispatchItem)
def auto_create_sales_return_item(sender, instance, created, **kwargs):
    """
    When SalesReturn is created, auto-create SalesReturnItem for each DispatchItem
    This ensures all dispatched products are tracked in returns
    """
    try:
        sales_return = instance.dispatch.sales_return
        
        # Create or update SalesReturnItem
        sales_return_item, created_item = SalesReturnItem.objects.get_or_create(
            sales_return=sales_return,
            product=instance.product,
            defaults={
                'units_dispatched': instance.quantity,
                'selling_price': instance.selling_price,
            }
        )
        
        if not created_item:
            # Update units_dispatched if dispatch quantity changed
            sales_return_item.units_dispatched = instance.quantity
            sales_return_item.save()
    
    except SalesReturn.DoesNotExist:
        # Sales return not yet created - that's okay
        pass


@receiver(post_save, sender=Dispatch)
def create_daily_sales_summary(sender, instance, **kwargs):
    """
    Create or update DailySales summary when dispatch created/updated
    """
    from .models import DailySales
    
    try:
        daily_sales, created = DailySales.objects.get_or_create(
            date=instance.date
        )
        
        # Recalculate will happen in DailySales.save()
        daily_sales.save()
        
        if created:
            print(f"✅ Created DailySales for {instance.date}")
        else:
            print(f"✅ Updated DailySales for {instance.date}")
    
    except Exception as e:
        print(f"❌ Failed to update DailySales: {e}")
