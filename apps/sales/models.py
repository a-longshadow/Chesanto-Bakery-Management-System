"""
Sales App Models
Manages dispatch, returns, deficits, and commission calculations
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError


class CommissionSettings(models.Model):
    """
    System-wide commission configuration (singleton pattern)
    Controls how salesperson commissions are calculated
    """
    per_unit_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Commission earned per unit sold (KES)"
    )
    bonus_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('35000.00'),
        help_text="Revenue threshold for bonus commission (KES)"
    )
    bonus_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('7.00'),
        help_text="Bonus percentage above threshold (e.g., 7 for 7%)"
    )
    effective_from = models.DateField(
        default=timezone.now,
        help_text="Date when these settings become effective"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one settings record can be active at a time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who last updated these settings"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this configuration"
    )

    class Meta:
        verbose_name = "Commission Settings"
        verbose_name_plural = "Commission Settings"
        ordering = ['-effective_from']

    def __str__(self):
        return f"Commission Settings (Effective: {self.effective_from})"

    def save(self, *args, **kwargs):
        """Ensure only one active record exists"""
        if self.is_active:
            # Deactivate all other records
            CommissionSettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """Get the currently active commission settings"""
        settings = cls.objects.filter(is_active=True).first()
        if not settings:
            # Create default settings if none exist
            settings = cls.objects.create(
                per_unit_commission=Decimal('5.00'),
                bonus_threshold=Decimal('35000.00'),
                bonus_percentage=Decimal('7.00'),
                is_active=True
            )
        return settings


class Salesperson(models.Model):
    """
    Sales team members (salespeople, school contacts, depot managers)
    """
    RECIPIENT_TYPE_CHOICES = [
        ('SALESMAN', 'Salesman'),
        ('SCHOOL', 'School'),
        ('DEPOT', 'Depot'),
        ('OTHER', 'Other'),
    ]
    
    # User account (optional - some may not have login)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salesperson_profile',
        help_text="Linked user account (if applicable)"
    )
    
    # Basic Information
    name = models.CharField(
        max_length=200,
        help_text="Full name (e.g., 'John Doe', 'Okiya Depot', 'St. Mary School')"
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=RECIPIENT_TYPE_CHOICES,
        default='SALESMAN',
        help_text="Type of recipient"
    )
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Area/location/route"
    )
    
    # Commission Structure (for salespeople)
    commission_per_bread = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Commission per bread loaf (KES)"
    )
    commission_per_kdf = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Commission per KDF packet (KES)"
    )
    commission_per_scones = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Commission per scones packet (KES)"
    )
    
    # Bonus Commission (7% of sales above target)
    sales_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('35000.00'),
        help_text="Monthly sales target (KES) for bonus eligibility"
    )
    bonus_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('7.00'),
        help_text="Bonus commission % for sales above target"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Soft delete")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salespeople_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salespeople_updated'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Salesperson"
        verbose_name_plural = "Salespeople"
    
    def __str__(self):
        return f"{self.name} ({self.get_recipient_type_display()})"


class Dispatch(models.Model):
    """
    Daily product dispatch to salespeople/schools/depots
    Mixed products (Bread + KDF + Scones in one dispatch)
    """
    date = models.DateField(help_text="Dispatch date")
    salesperson = models.ForeignKey(
        Salesperson,
        on_delete=models.PROTECT,
        related_name='dispatches',
        help_text="Recipient (salesperson/school/depot)"
    )
    
    # Crates
    crates_dispatched = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: Number of crates dispatched"
    )
    
    # Expected Revenue (auto-calculated from items)
    expected_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all DispatchItem.expected_revenue"
    )
    
    # Status
    is_returned = models.BooleanField(
        default=False,
        help_text="True when salesperson returns with sales data"
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dispatches_created'
    )
    
    class Meta:
        ordering = ['-date', 'salesperson__name']
        verbose_name = "Dispatch"
        verbose_name_plural = "Dispatches"
        unique_together = ['date', 'salesperson']  # One dispatch per person per day
    
    def __str__(self):
        return f"Dispatch to {self.salesperson.name} on {self.date}"
    
    def calculate_expected_revenue(self):
        """Calculate total expected revenue from all dispatch items"""
        self.expected_revenue = sum(
            item.expected_revenue
            for item in self.dispatchitem_set.all()
        )
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate expected revenue"""
        super().save(*args, **kwargs)
        self.calculate_expected_revenue()
        if self.expected_revenue != self._state.fields_cache.get('expected_revenue', 0):
            super().save(update_fields=['expected_revenue'])


class DispatchItem(models.Model):
    """
    Individual products in a dispatch
    Multiple products per dispatch (Bread + KDF + Scones)
    """
    dispatch = models.ForeignKey(
        Dispatch,
        on_delete=models.CASCADE,
        related_name='dispatchitem_set'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        help_text="Product dispatched (Bread/KDF/Scones)"
    )
    
    # Quantity
    quantity = models.IntegerField(
        help_text="✏️ MANUAL: Units/packets dispatched"
    )
    
    # Costs & Revenue
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: From ProductionBatch.cost_per_packet (latest)"
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: From Product.price_per_packet"
    )
    expected_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: quantity × selling_price"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product__name']
        verbose_name = "Dispatch Item"
        verbose_name_plural = "Dispatch Items"
        unique_together = ['dispatch', 'product']
    
    def __str__(self):
        return f"{self.quantity} {self.product.name} @ KES {self.selling_price}"
    
    def calculate_values(self):
        """Calculate cost and expected revenue"""
        # Get selling price from product
        self.selling_price = self.product.price_per_packet
        
        # Calculate expected revenue
        self.expected_revenue = self.quantity * self.selling_price
        
        # Get cost from latest production batch (simplified - uses product cost)
        # In production, would fetch from actual ProductionBatch
        try:
            from apps.products.models import Mix
            mix = Mix.objects.filter(product=self.product, is_active=True).first()
            if mix:
                self.cost_per_unit = mix.cost_per_packet
        except Exception:
            self.cost_per_unit = Decimal('0')
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate values"""
        self.calculate_values()
        super().save(*args, **kwargs)
        
        # Update parent dispatch expected revenue
        self.dispatch.calculate_expected_revenue()
        # Save the dispatch to persist the updated expected_revenue
        self.dispatch.save(update_fields=['expected_revenue'])


class SalesReturn(models.Model):
    """
    Sales return from salesperson
    Strong 1-to-1 FK with Dispatch
    Tracks actual sales, returns, deficits, and commissions
    """
    dispatch = models.OneToOneField(
        Dispatch,
        on_delete=models.CASCADE,
        related_name='sales_return',
        help_text="Linked dispatch record"
    )
    
    # Return Date
    return_date = models.DateField(
        help_text="✏️ MANUAL: Date when salesperson returned"
    )
    return_time = models.TimeField(
        null=True,
        blank=True,
        help_text="✏️ MANUAL: Time of return"
    )
    
    # Crates
    crates_returned = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: Crates returned"
    )
    crates_deficit = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: crates_dispatched - crates_returned"
    )
    
    # Cash/Banking
    cash_returned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Cash/M-Pesa amount returned (KES)"
    )
    revenue_deficit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: expected_revenue - cash_returned"
    )
    
    # Commission (auto-calculated)
    per_unit_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of (units_sold × commission_per_unit)"
    )
    bonus_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: 7% of sales above KES 35,000 target"
    )
    total_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: per_unit_commission + bonus_commission"
    )
    
    # Deficit Handling
    deficit_reason = models.TextField(
        blank=True,
        help_text="✏️ MANUAL: Reason for deficit (expired stock, damage, etc.)"
    )
    deficit_resolved = models.BooleanField(
        default=False,
        help_text="True when deficit issue resolved"
    )
    
    # Alert Status
    deficit_alert_sent = models.BooleanField(
        default=False,
        help_text="🤖 AUTO: True if alert sent to Accountant/CEO"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_returns_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_returns_updated'
    )
    
    class Meta:
        ordering = ['-return_date']
        verbose_name = "Sales Return"
        verbose_name_plural = "Sales Returns"
    
    def __str__(self):
        return f"Return from {self.dispatch.salesperson.name} on {self.return_date}"
    
    def calculate_crate_deficit(self):
        """Calculate crate deficit"""
        self.crates_deficit = self.dispatch.crates_dispatched - self.crates_returned
    
    def calculate_revenue_deficit(self):
        """Calculate revenue deficit"""
        self.revenue_deficit = self.dispatch.expected_revenue - self.cash_returned
    
    def calculate_commission(self):
        """
        Calculate total commission using system-wide CommissionSettings
        - Per-unit commission: units_sold × commission_per_unit (from settings or salesperson override)
        - Bonus commission: bonus_percentage of sales above bonus_threshold
        """
        salesperson = self.dispatch.salesperson
        settings = CommissionSettings.get_active()
        
        # Calculate per-unit commission from sales return items
        per_unit_total = Decimal('0')
        for item in self.salesreturnitem_set.all():
            units_sold = item.units_sold
            
            # Get commission rate for this product (from salesperson or settings)
            if item.product.name == "Bread":
                commission_rate = salesperson.commission_per_bread
            elif item.product.name == "KDF":
                commission_rate = salesperson.commission_per_kdf
            elif item.product.name == "Scones":
                commission_rate = salesperson.commission_per_scones
            else:
                # Use system-wide default from settings
                commission_rate = settings.per_unit_commission
            
            per_unit_total += units_sold * commission_rate
        
        self.per_unit_commission = per_unit_total
        
        # Calculate bonus commission using settings
        total_sales = self.cash_returned + self.revenue_deficit  # Total sales before deficit
        if total_sales > settings.bonus_threshold:
            excess = total_sales - settings.bonus_threshold
            self.bonus_commission = excess * (settings.bonus_percentage / 100)
        else:
            self.bonus_commission = Decimal('0')
        
        # Total commission
        self.total_commission = self.per_unit_commission + self.bonus_commission
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate deficits and commissions"""
        self.calculate_crate_deficit()
        self.calculate_revenue_deficit()
        
        # Only calculate commission if we have a PK (i.e., already saved once)
        # or if we're not creating a new record
        if self.pk or not kwargs.get('force_insert'):
            try:
                self.calculate_commission()
            except ValueError:
                # Can't calculate commission yet (no items), set to zero
                self.per_unit_commission = Decimal('0')
                self.bonus_commission = Decimal('0')
                self.total_commission = Decimal('0')
        else:
            # New record without items yet
            self.per_unit_commission = Decimal('0')
            self.bonus_commission = Decimal('0')
            self.total_commission = Decimal('0')
        
        super().save(*args, **kwargs)
        
        # Mark dispatch as returned
        self.dispatch.is_returned = True
        self.dispatch.returned_at = timezone.now()
        self.dispatch.save()


class SalesReturnItem(models.Model):
    """
    Product-level sales tracking in a return
    Tracks units sold, returned, and damaged
    """
    sales_return = models.ForeignKey(
        SalesReturn,
        on_delete=models.CASCADE,
        related_name='salesreturnitem_set'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        help_text="Product (Bread/KDF/Scones)"
    )
    
    # Quantities
    units_dispatched = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: From DispatchItem.quantity"
    )
    units_returned = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: Units returned unsold"
    )
    units_damaged = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: Units damaged (not sellable)"
    )
    units_sold = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: dispatched - returned - damaged"
    )
    
    # Revenue
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: From Product.price_per_packet"
    )
    gross_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: units_sold × selling_price"
    )
    damaged_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: units_damaged × selling_price"
    )
    net_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: gross_sales - damaged_value"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product__name']
        verbose_name = "Sales Return Item"
        verbose_name_plural = "Sales Return Items"
        unique_together = ['sales_return', 'product']
    
    def __str__(self):
        return f"{self.product.name}: {self.units_sold} sold, {self.units_returned} returned"
    
    def calculate_values(self):
        """Calculate units sold and revenue"""
        # Units sold = dispatched - returned - damaged
        self.units_sold = self.units_dispatched - self.units_returned - self.units_damaged
        
        # Get selling price
        self.selling_price = self.product.price_per_packet
        
        # Calculate revenue
        self.gross_sales = self.units_sold * self.selling_price
        self.damaged_value = self.units_damaged * self.selling_price
        self.net_sales = self.gross_sales - self.damaged_value
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate values"""
        self.calculate_values()
        super().save(*args, **kwargs)
        
        # Update parent SalesReturn commissions
        self.sales_return.calculate_commission()
        self.sales_return.save()


class DailySales(models.Model):
    """
    Daily sales summary
    Aggregates all dispatches and returns for a day
    """
    date = models.DateField(unique=True, help_text="Sales date")
    
    # Totals (auto-calculated)
    total_dispatched = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Total units dispatched today"
    )
    total_expected_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all dispatch expected revenues"
    )
    total_actual_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all cash returned"
    )
    total_revenue_deficit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: expected - actual"
    )
    total_commissions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all commissions earned"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='daily_sales_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='daily_sales_updated'
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Sales"
        verbose_name_plural = "Daily Sales"
    
    def __str__(self):
        return f"Sales Summary {self.date}"
    
    def calculate_totals(self):
        """Calculate daily totals from dispatches and returns"""
        # Get all dispatches for this date
        dispatches = Dispatch.objects.filter(date=self.date)
        
        self.total_expected_revenue = sum(d.expected_revenue for d in dispatches)
        
        # Get all returns for this date
        returns = SalesReturn.objects.filter(return_date=self.date)
        
        self.total_actual_revenue = sum(r.cash_returned for r in returns)
        self.total_revenue_deficit = sum(r.revenue_deficit for r in returns)
        self.total_commissions = sum(r.total_commission for r in returns)
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate totals"""
        self.calculate_totals()
        super().save(*args, **kwargs)

