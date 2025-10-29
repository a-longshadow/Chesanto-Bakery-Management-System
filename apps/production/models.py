"""
Production App Models
Manages daily production batches, costs, P&L per mix, and book closing
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError


class DailyProduction(models.Model):
    """
    Daily production summary with opening/closing stock
    Books close at 9PM daily
    """
    date = models.DateField(unique=True, help_text="Production date")
    
    # Book Closing
    is_closed = models.BooleanField(
        default=False,
        help_text="🤖 AUTO: Set to True at 9PM by cron job"
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when books were closed"
    )
    
    # Opening Product Stock (finished goods from previous day)
    opening_bread_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: From previous day's closing_bread_stock"
    )
    opening_kdf_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: From previous day's closing_kdf_stock"
    )
    opening_scones_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: From previous day's closing_scones_stock"
    )
    
    # Production (calculated from batches)
    bread_produced = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Sum of Bread batches"
    )
    kdf_produced = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Sum of KDF batches"
    )
    scones_produced = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Sum of Scones batches"
    )
    
    # Dispatched (from Sales app)
    bread_dispatched = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From dispatch records (Sales app)"
    )
    kdf_dispatched = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From dispatch records"
    )
    scones_dispatched = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From dispatch records"
    )
    
    # Returns (from Sales app)
    bread_returned = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From sales returns (Sales app)"
    )
    kdf_returned = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From sales returns"
    )
    scones_returned = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: From sales returns"
    )
    
    # Closing Product Stock (calculated)
    closing_bread_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Opening + Produced - Dispatched + Returned"
    )
    closing_kdf_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Opening + Produced - Dispatched + Returned"
    )
    closing_scones_stock = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Opening + Produced - Dispatched + Returned"
    )
    
    # Indirect Costs (daily operational costs)
    diesel_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Daily diesel consumption (KES)"
    )
    firewood_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Daily firewood cost (KES)"
    )
    electricity_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Daily electricity (estimated, KES)"
    )
    fuel_distribution_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Fuel for trucks/Bolero (KES)"
    )
    other_indirect_costs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="✏️ MANUAL: Miscellaneous costs (KES)"
    )
    total_indirect_costs = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all indirect costs"
    )
    
    # Reconciliation
    reconciliation_notes = models.TextField(
        blank=True,
        help_text="Notes on stock reconciliation, variances, issues"
    )
    has_variance = models.BooleanField(
        default=False,
        help_text="🤖 AUTO: True if variance > 5% detected"
    )
    variance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Variance % if detected"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='daily_production_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='daily_production_updated'
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Production"
        verbose_name_plural = "Daily Productions"
    
    def __str__(self):
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"Production {self.date} ({status})"
    
    def calculate_closing_stock(self):
        """
        Calculate closing stock for all products
        Formula: Opening + Produced - Dispatched + Returned
        """
        self.closing_bread_stock = (
            self.opening_bread_stock + 
            self.bread_produced - 
            self.bread_dispatched + 
            self.bread_returned
        )
        self.closing_kdf_stock = (
            self.opening_kdf_stock + 
            self.kdf_produced - 
            self.kdf_dispatched + 
            self.kdf_returned
        )
        self.closing_scones_stock = (
            self.opening_scones_stock + 
            self.scones_produced - 
            self.scones_dispatched + 
            self.scones_returned
        )
    
    def calculate_total_indirect_costs(self):
        """Calculate sum of all indirect costs"""
        self.total_indirect_costs = (
            self.diesel_cost +
            self.firewood_cost +
            self.electricity_cost +
            self.fuel_distribution_cost +
            self.other_indirect_costs
        )
    
    def check_reconciliation_variance(self):
        """
        Check for stock reconciliation variances > 5%
        Compare expected vs actual closing stock
        """
        total_expected = self.opening_bread_stock + self.bread_produced
        total_actual = self.bread_dispatched - self.bread_returned + self.closing_bread_stock
        
        if total_expected > 0:
            variance = abs(total_expected - total_actual) / total_expected * 100
            if variance > 5:
                self.has_variance = True
                self.variance_percentage = Decimal(str(variance))
            else:
                self.has_variance = False
                self.variance_percentage = Decimal('0')
    
    def close_books(self, user):
        """
        Close daily books (run at 9PM by cron)
        Locks all edits except Admin/CEO
        """
        if not self.is_closed:
            self.calculate_closing_stock()
            self.calculate_total_indirect_costs()
            self.check_reconciliation_variance()
            self.is_closed = True
            self.closed_at = timezone.now()
            self.updated_by = user
            self.save()
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate values"""
        self.calculate_closing_stock()
        self.calculate_total_indirect_costs()
        self.check_reconciliation_variance()
        super().save(*args, **kwargs)


class ProductionBatch(models.Model):
    """
    Individual production batch (one mix)
    Auto-deducts ingredients from inventory via Django signal
    """
    daily_production = models.ForeignKey(
        DailyProduction,
        on_delete=models.CASCADE,
        related_name='batches',
        help_text="Parent daily production record"
    )
    
    # Mix Selection
    mix = models.ForeignKey(
        'products.Mix',
        on_delete=models.PROTECT,
        help_text="✏️ MANUAL: Select mix (Bread Mix 1, KDF Mix 1, etc.)"
    )
    
    # Production Details
    batch_number = models.IntegerField(
        help_text="✏️ MANUAL: Batch number for the day (1, 2, 3...)"
    )
    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="✏️ MANUAL: When production started"
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="✏️ MANUAL: When production finished"
    )
    
    # Output (actual vs expected)
    actual_packets = models.IntegerField(
        help_text="✏️ MANUAL: Actual units/packets produced"
    )
    expected_packets = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: From Mix.expected_packets"
    )
    variance_packets = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Actual - Expected"
    )
    variance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: (Variance / Expected) × 100"
    )
    
    # Sub-products (Bread Rejects)
    rejects_produced = models.IntegerField(
        default=0,
        help_text="✏️ MANUAL: Bread rejects (if applicable)"
    )
    
    # Costs
    ingredient_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: From Mix.total_cost"
    )
    packaging_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: actual_packets × KES 3.3"
    )
    allocated_indirect_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Proportional share of daily indirect costs"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Ingredient + Packaging + Indirect"
    )
    cost_per_packet = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: total_cost / actual_packets"
    )
    
    # P&L (CEO requirement)
    selling_price_per_packet = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: From Product.price_per_packet"
    )
    expected_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: actual_packets × selling_price_per_packet"
    )
    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: expected_revenue - total_cost"
    )
    gross_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: (gross_profit / expected_revenue) × 100"
    )
    
    # Quality Control
    quality_notes = models.TextField(
        blank=True,
        help_text="✏️ MANUAL: Notes on quality, issues, observations"
    )
    is_finalized = models.BooleanField(
        default=False,
        help_text="Locked after book closing (9PM)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='production_batches_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='production_batches_updated'
    )
    
    class Meta:
        ordering = ['daily_production__date', 'batch_number']
        verbose_name = "Production Batch"
        verbose_name_plural = "Production Batches"
        unique_together = ['daily_production', 'batch_number']
    
    def __str__(self):
        return f"{self.mix.product.name} Batch #{self.batch_number} ({self.daily_production.date})"
    
    def calculate_variance(self):
        """Calculate production variance (actual vs expected)"""
        self.expected_packets = self.mix.expected_packets
        self.variance_packets = self.actual_packets - self.expected_packets
        
        if self.expected_packets > 0:
            self.variance_percentage = Decimal(
                str((self.variance_packets / self.expected_packets) * 100)
            )
        else:
            self.variance_percentage = Decimal('0')
    
    def calculate_packaging_cost(self):
        """
        Calculate packaging cost
        Bread: 1 bag per loaf (KES 3.3)
        KDF/Scones: 1 bag per packet (KES 3.3)
        """
        PACKAGING_COST_PER_UNIT = Decimal('3.30')
        total_units = self.actual_packets + self.rejects_produced
        self.packaging_cost = total_units * PACKAGING_COST_PER_UNIT
    
    def calculate_costs(self):
        """Calculate all costs for this batch"""
        # Ingredient cost from mix
        self.ingredient_cost = self.mix.total_cost
        
        # Packaging cost
        self.calculate_packaging_cost()
        
        # Total cost (indirect allocated later by DailyProduction)
        self.total_cost = (
            self.ingredient_cost + 
            self.packaging_cost + 
            self.allocated_indirect_cost
        )
        
        # Cost per packet
        if self.actual_packets > 0:
            self.cost_per_packet = self.total_cost / self.actual_packets
        else:
            self.cost_per_packet = Decimal('0')
    
    def calculate_pl(self):
        """Calculate P&L for this batch"""
        self.selling_price_per_packet = self.mix.product.price_per_packet
        self.expected_revenue = self.actual_packets * self.selling_price_per_packet
        self.gross_profit = self.expected_revenue - self.total_cost
        
        if self.expected_revenue > 0:
            self.gross_margin_percentage = (
                self.gross_profit / self.expected_revenue * 100
            )
        else:
            self.gross_margin_percentage = Decimal('0')
    
    def allocate_indirect_costs(self):
        """
        Allocate daily indirect costs proportionally
        Called by DailyProduction after all batches created
        """
        daily_prod = self.daily_production
        total_ingredient_cost = sum(
            batch.ingredient_cost 
            for batch in daily_prod.batches.all()
        )
        
        if total_ingredient_cost > 0:
            proportion = self.ingredient_cost / total_ingredient_cost
            self.allocated_indirect_cost = proportion * daily_prod.total_indirect_costs
        else:
            self.allocated_indirect_cost = Decimal('0')
        
        # Recalculate total cost and P&L
        self.calculate_costs()
        self.calculate_pl()
    
    def clean(self):
        """Validate batch data"""
        # Can't edit finalized batches
        if self.pk and self.is_finalized:
            raise ValidationError("Cannot edit finalized batch (books closed)")
        
        # Actual packets should be positive
        if self.actual_packets < 0:
            raise ValidationError("Actual packets cannot be negative")
        
        # Rejects only for Bread
        if self.rejects_produced > 0 and self.mix.product.name != "Bread":
            raise ValidationError("Only Bread can have rejects")
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate all values"""
        self.calculate_variance()
        self.calculate_costs()
        self.calculate_pl()
        super().save(*args, **kwargs)
        
        # Update parent DailyProduction totals
        self.update_daily_production_totals()
    
    def update_daily_production_totals(self):
        """Update DailyProduction totals after batch changes"""
        daily_prod = self.daily_production
        
        # Recalculate production totals
        bread_total = sum(
            batch.actual_packets + batch.rejects_produced
            for batch in daily_prod.batches.filter(mix__product__name="Bread")
        )
        kdf_total = sum(
            batch.actual_packets
            for batch in daily_prod.batches.filter(mix__product__name="KDF")
        )
        scones_total = sum(
            batch.actual_packets
            for batch in daily_prod.batches.filter(mix__product__name="Scones")
        )
        
        daily_prod.bread_produced = bread_total
        daily_prod.kdf_produced = kdf_total
        daily_prod.scones_produced = scones_total
        daily_prod.save()


class IndirectCost(models.Model):
    """
    Track individual indirect cost transactions
    Optional detail model for audit trail
    """
    COST_TYPE_CHOICES = [
        ('DIESEL', 'Diesel (Production)'),
        ('FIREWOOD', 'Firewood'),
        ('ELECTRICITY', 'Electricity'),
        ('FUEL_DISTRIBUTION', 'Fuel (Distribution)'),
        ('OTHER', 'Other'),
    ]
    
    daily_production = models.ForeignKey(
        DailyProduction,
        on_delete=models.CASCADE,
        related_name='indirect_cost_details'
    )
    
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        help_text="Type of indirect cost"
    )
    description = models.CharField(
        max_length=200,
        help_text="Description of cost (e.g., '20L diesel from Ikapolok')"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cost amount in KES"
    )
    
    # Receipt tracking
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Receipt/invoice number"
    )
    vendor = models.CharField(
        max_length=200,
        blank=True,
        help_text="Vendor/supplier name"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        ordering = ['daily_production__date', 'created_at']
        verbose_name = "Indirect Cost Detail"
        verbose_name_plural = "Indirect Cost Details"
    
    def __str__(self):
        return f"{self.get_cost_type_display()}: KES {self.amount} ({self.daily_production.date})"
