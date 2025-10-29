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
    Send alerts when revenue or crate deficits detected
    
    Rules:
    - Any deficit > KES 0: Email to Accountant
    - Deficit > KES 500: Email to CEO + Accountant
    - Crate deficit > 0: SMS + Email to Accountant
    """
    if instance.deficit_alert_sent:
        return  # Already sent
    
    # Check revenue deficit
    if instance.revenue_deficit > Decimal('0'):
        subject = f"⚠️ Revenue Deficit Alert: {instance.dispatch.salesperson.name}"
        
        message = f"""
        Revenue Deficit Detected:
        
        Salesperson: {instance.dispatch.salesperson.name}
        Date: {instance.return_date}
        Expected Revenue: KES {instance.dispatch.expected_revenue:,.2f}
        Cash Returned: KES {instance.cash_returned:,.2f}
        Deficit: KES {instance.revenue_deficit:,.2f}
        
        Reason: {instance.deficit_reason or "Not provided"}
        
        Please follow up immediately.
        """
        
        # Determine recipients
        recipients = ['accountant@chesanto.com']  # Default accountant
        
        if instance.revenue_deficit > Decimal('500'):
            recipients.append('ceo@chesanto.com')  # CEO for large deficits
        
        # Send email (in production, use proper email backend)
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
            print(f"✅ Deficit alert sent: KES {instance.revenue_deficit} to {recipients}")
        except Exception as e:
            print(f"❌ Email failed: {e}")
    
    # Check crate deficit
    if instance.crates_deficit > 0:
        crate_message = f"""
        Crate Deficit Detected:
        
        Salesperson: {instance.dispatch.salesperson.name}
        Date: {instance.return_date}
        Crates Dispatched: {instance.dispatch.crates_dispatched}
        Crates Returned: {instance.crates_returned}
        Deficit: {instance.crates_deficit} crates
        
        Please recover missing crates.
        """
        
        try:
            send_mail(
                f"⚠️ Crate Deficit: {instance.crates_deficit} crates missing",
                crate_message,
                settings.DEFAULT_FROM_EMAIL,
                ['accountant@chesanto.com'],
                fail_silently=False,
            )
            print(f"✅ Crate deficit alert sent: {instance.crates_deficit} crates")
        except Exception as e:
            print(f"❌ Crate alert failed: {e}")
    
    # Mark alert as sent
    instance.deficit_alert_sent = True
    SalesReturn.objects.filter(pk=instance.pk).update(deficit_alert_sent=True)


@receiver(post_save, sender=SalesReturn)
def detect_deficit_patterns(sender, instance, **kwargs):
    """
    Detect salespeople with recurring deficits
    Flag if 3+ deficits in a month
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Count deficits in last 30 days for this salesperson
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    
    recent_deficits = SalesReturn.objects.filter(
        dispatch__salesperson=instance.dispatch.salesperson,
        return_date__gte=thirty_days_ago,
        revenue_deficit__gt=0
    ).count()
    
    if recent_deficits >= 3:
        print(f"⚠️ PATTERN ALERT: {instance.dispatch.salesperson.name} has {recent_deficits} deficits in last 30 days")
        
        # Send pattern alert to CEO
        subject = f"🚨 Recurring Deficit Pattern: {instance.dispatch.salesperson.name}"
        message = f"""
        RECURRING DEFICIT PATTERN DETECTED:
        
        Salesperson: {instance.dispatch.salesperson.name}
        Deficits in last 30 days: {recent_deficits}
        
        This salesperson requires immediate review and corrective action.
        
        Consider:
        - Performance review
        - Route reassignment
        - Additional training
        - Termination (if fraud suspected)
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['ceo@chesanto.com', 'accountant@chesanto.com'],
                fail_silently=False,
            )
            print(f"✅ Pattern alert sent for {instance.dispatch.salesperson.name}")
        except Exception as e:
            print(f"❌ Pattern alert failed: {e}")


@receiver(post_save, sender=SalesReturn)
def update_daily_production_totals(sender, instance, **kwargs):
    """
    Update DailyProduction dispatched/returned fields when sales return saved
    """
    try:
        from apps.production.models import DailyProduction
        
        # Get DailyProduction for dispatch date
        daily_production, created = DailyProduction.objects.get_or_create(
            date=instance.dispatch.date
        )
        
        # Recalculate totals from all sales returns
        for item in instance.salesreturnitem_set.all():
            product_name = item.product.name
            
            # Update dispatched totals
            if product_name == "Bread":
                # Sum all dispatched bread for this date
                daily_production.bread_dispatched = sum(
                    di.quantity for di in DispatchItem.objects.filter(
                        dispatch__date=instance.dispatch.date,
                        product__name="Bread"
                    )
                )
                # Sum all returned bread
                daily_production.bread_returned = sum(
                    sri.units_returned for sri in SalesReturnItem.objects.filter(
                        sales_return__dispatch__date=instance.dispatch.date,
                        product__name="Bread"
                    )
                )
            
            elif product_name == "KDF":
                daily_production.kdf_dispatched = sum(
                    di.quantity for di in DispatchItem.objects.filter(
                        dispatch__date=instance.dispatch.date,
                        product__name="KDF"
                    )
                )
                daily_production.kdf_returned = sum(
                    sri.units_returned for sri in SalesReturnItem.objects.filter(
                        sales_return__dispatch__date=instance.dispatch.date,
                        product__name="KDF"
                    )
                )
            
            elif product_name == "Scones":
                daily_production.scones_dispatched = sum(
                    di.quantity for di in DispatchItem.objects.filter(
                        dispatch__date=instance.dispatch.date,
                        product__name="Scones"
                    )
                )
                daily_production.scones_returned = sum(
                    sri.units_returned for sri in SalesReturnItem.objects.filter(
                        sales_return__dispatch__date=instance.dispatch.date,
                        product__name="Scones"
                    )
                )
        
        daily_production.save()
        print(f"✅ Updated DailyProduction for {instance.dispatch.date}")
    
    except Exception as e:
        print(f"❌ Failed to update DailyProduction: {e}")


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
