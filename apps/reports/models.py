"""
Reports App Models
==================
Flexible, product-agnostic report models.
Pre-computed aggregates for fast report retrieval.
All reports follow bank ledger policy (immutable after creation).

Report Types:
- DAILY: Daily summaries
- WEEKLY: Week-ending reports
- MONTHLY: Monthly summaries  
- ANNUAL: Year-end reports

Access: ACCOUNTANT role or higher
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class ReportPeriod(models.Model):
    """
    Container for aggregated report data.
    Generated via management command or scheduled task.
    Immutable after creation (bank ledger policy).
    """
    
    class PeriodType(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        ANNUAL = 'ANNUAL', 'Annual'
    
    # Period identification
    period_type = models.CharField(
        max_length=10, 
        choices=PeriodType.choices,
        help_text="Type of report period"
    )
    start_date = models.DateField(help_text="First day of period")
    end_date = models.DateField(help_text="Last day of period")
    period_label = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Human-readable label (e.g., 'December 2025')"
    )
    
    # ═══════════════════════════════════════════════════════════
    # SALES SUMMARY
    # ═══════════════════════════════════════════════════════════
    total_revenue = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total revenue from sales returns"
    )
    total_units_sold = models.PositiveIntegerField(
        default=0,
        help_text="Total product units sold"
    )
    total_dispatches = models.PositiveIntegerField(
        default=0,
        help_text="Number of sales dispatches"
    )
    total_returns = models.PositiveIntegerField(
        default=0,
        help_text="Total product units returned unsold"
    )
    total_commissions = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total commission payments"
    )
    
    # ═══════════════════════════════════════════════════════════
    # PRODUCTION SUMMARY
    # ═══════════════════════════════════════════════════════════
    total_units_produced = models.PositiveIntegerField(
        default=0,
        help_text="Total units produced"
    )
    total_batches = models.PositiveIntegerField(
        default=0,
        help_text="Number of production batches"
    )
    total_production_cost = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total ingredient cost for production"
    )
    average_yield_variance = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Average yield variance percentage"
    )
    
    # ═══════════════════════════════════════════════════════════
    # INVENTORY SUMMARY
    # ═══════════════════════════════════════════════════════════
    total_purchase_cost = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total cost of inventory purchases"
    )
    total_purchases_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of purchase transactions"
    )
    low_stock_alerts = models.PositiveIntegerField(
        default=0,
        help_text="Number of low stock alerts"
    )
    
    # ═══════════════════════════════════════════════════════════
    # CRATE TRACKING
    # ═══════════════════════════════════════════════════════════
    total_crates_dispatched = models.PositiveIntegerField(
        default=0,
        help_text="Total crates sent out"
    )
    total_crates_returned = models.PositiveIntegerField(
        default=0,
        help_text="Total crates returned"
    )
    total_crates_lost = models.PositiveIntegerField(
        default=0,
        help_text="Total crates lost"
    )
    total_crates_damaged = models.PositiveIntegerField(
        default=0,
        help_text="Total crates damaged"
    )
    
    # ═══════════════════════════════════════════════════════════
    # FINANCIAL SUMMARY (P&L)
    # ═══════════════════════════════════════════════════════════
    gross_profit = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Revenue - Production Cost"
    )
    gross_margin_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="(Gross Profit / Revenue) × 100"
    )
    
    # ═══════════════════════════════════════════════════════════
    # GENERATION METADATA
    # ═══════════════════════════════════════════════════════════
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_generated'
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked reports cannot be regenerated"
    )
    
    # Email tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_recipients = models.TextField(
        blank=True,
        help_text="Comma-separated list of email recipients"
    )
    
    class Meta:
        ordering = ['-start_date', 'period_type']
        unique_together = ['period_type', 'start_date', 'end_date']
        verbose_name = 'Report Period'
        verbose_name_plural = 'Report Periods'
        indexes = [
            models.Index(fields=['period_type', 'start_date']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.get_period_type_display()} Report: {self.period_label or self.start_date}"
    
    def save(self, *args, **kwargs):
        """Generate period label if not provided."""
        if not self.period_label:
            self.period_label = self._generate_label()
        
        # Calculate derived fields
        if self.total_revenue > 0:
            self.gross_profit = self.total_revenue - self.total_production_cost
            self.gross_margin_percentage = (self.gross_profit / self.total_revenue * 100).quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)
    
    def _generate_label(self) -> str:
        """Generate human-readable period label."""
        from calendar import month_name
        
        if self.period_type == self.PeriodType.DAILY:
            return self.start_date.strftime('%d %B %Y')
        elif self.period_type == self.PeriodType.WEEKLY:
            return f"Week of {self.start_date.strftime('%d %b')} - {self.end_date.strftime('%d %b %Y')}"
        elif self.period_type == self.PeriodType.MONTHLY:
            return f"{month_name[self.start_date.month]} {self.start_date.year}"
        elif self.period_type == self.PeriodType.ANNUAL:
            return f"Year {self.start_date.year}"
        return str(self.start_date)
    
    @property
    def return_rate(self) -> Decimal:
        """Calculate product return rate percentage."""
        total_dispatched = self.total_units_sold + self.total_returns
        if total_dispatched == 0:
            return Decimal('0.00')
        return (Decimal(self.total_returns) / Decimal(total_dispatched) * 100).quantize(Decimal('0.01'))
    
    @property
    def crate_loss_rate(self) -> Decimal:
        """Calculate crate loss rate percentage."""
        if self.total_crates_dispatched == 0:
            return Decimal('0.00')
        return (Decimal(self.total_crates_lost) / Decimal(self.total_crates_dispatched) * 100).quantize(Decimal('0.01'))
    
    @property
    def average_revenue_per_dispatch(self) -> Decimal:
        """Calculate average revenue per dispatch."""
        if self.total_dispatches == 0:
            return Decimal('0.00')
        return (self.total_revenue / self.total_dispatches).quantize(Decimal('0.01'))


class ReportProductSummary(models.Model):
    """
    Per-product breakdown within a report period.
    Flexible - works with any products in the system.
    """
    report_period = models.ForeignKey(
        ReportPeriod, 
        on_delete=models.CASCADE,
        related_name='product_summaries'
    )
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.PROTECT,
        related_name='report_summaries'
    )
    
    # Production metrics
    units_produced = models.PositiveIntegerField(default=0)
    production_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    batches_count = models.PositiveIntegerField(default=0)
    average_yield_variance = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Sales metrics
    units_dispatched = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    units_returned = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    class Meta:
        ordering = ['product__name']
        unique_together = ['report_period', 'product']
        verbose_name = 'Product Summary'
        verbose_name_plural = 'Product Summaries'
    
    def __str__(self):
        return f"{self.product.name} - {self.report_period.period_label}"
    
    @property
    def average_selling_price(self) -> Decimal:
        """Average price per unit sold."""
        if self.units_sold == 0:
            return Decimal('0.00')
        return (self.revenue / self.units_sold).quantize(Decimal('0.01'))
    
    @property
    def return_rate(self) -> Decimal:
        """Percentage of dispatched units returned."""
        if self.units_dispatched == 0:
            return Decimal('0.00')
        return (Decimal(self.units_returned) / Decimal(self.units_dispatched) * 100).quantize(Decimal('0.01'))
    
    @property
    def cost_per_unit(self) -> Decimal:
        """Production cost per unit."""
        if self.units_produced == 0:
            return Decimal('0.00')
        return (self.production_cost / self.units_produced).quantize(Decimal('0.01'))
    
    @property
    def gross_profit(self) -> Decimal:
        """Revenue minus production cost."""
        return self.revenue - self.production_cost
    
    @property
    def gross_margin(self) -> Decimal:
        """Gross margin percentage."""
        if self.revenue == 0:
            return Decimal('0.00')
        return (self.gross_profit / self.revenue * 100).quantize(Decimal('0.01'))


class ReportSalespersonSummary(models.Model):
    """
    Per-salesperson performance within a report period.
    """
    report_period = models.ForeignKey(
        ReportPeriod, 
        on_delete=models.CASCADE,
        related_name='salesperson_summaries'
    )
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='sales_summaries'
    )
    
    # Sales metrics
    dispatch_count = models.PositiveIntegerField(default=0)
    total_units_dispatched = models.PositiveIntegerField(default=0)
    total_units_sold = models.PositiveIntegerField(default=0)
    total_units_returned = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    total_commission = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Crate accountability
    crates_dispatched = models.PositiveIntegerField(default=0)
    crates_returned = models.PositiveIntegerField(default=0)
    crates_lost = models.PositiveIntegerField(default=0)
    crates_damaged = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-total_revenue']
        unique_together = ['report_period', 'salesperson']
        verbose_name = 'Salesperson Summary'
        verbose_name_plural = 'Salesperson Summaries'
    
    def __str__(self):
        return f"{self.salesperson.get_full_name()} - {self.report_period.period_label}"
    
    @property
    def return_rate(self) -> Decimal:
        """Percentage of dispatched units returned."""
        if self.total_units_dispatched == 0:
            return Decimal('0.00')
        return (Decimal(self.total_units_returned) / Decimal(self.total_units_dispatched) * 100).quantize(Decimal('0.01'))
    
    @property
    def crate_loss_rate(self) -> Decimal:
        """Percentage of crates lost."""
        if self.crates_dispatched == 0:
            return Decimal('0.00')
        return (Decimal(self.crates_lost) / Decimal(self.crates_dispatched) * 100).quantize(Decimal('0.01'))
    
    @property
    def average_revenue_per_dispatch(self) -> Decimal:
        """Average revenue per dispatch."""
        if self.dispatch_count == 0:
            return Decimal('0.00')
        return (self.total_revenue / self.dispatch_count).quantize(Decimal('0.01'))


class ReportInventorySummary(models.Model):
    """
    Per-inventory-item breakdown within a report period.
    Tracks stock movements and costs.
    """
    report_period = models.ForeignKey(
        ReportPeriod, 
        on_delete=models.CASCADE,
        related_name='inventory_summaries'
    )
    inventory_item_id = models.PositiveIntegerField(
        help_text="Reference to inventory item (1-23)"
    )
    item_name = models.CharField(
        max_length=100,
        help_text="Snapshot of item name at report generation"
    )
    
    # Stock levels
    opening_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    closing_stock = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Movements
    total_purchased = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    purchase_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    purchase_count = models.PositiveIntegerField(default=0)
    
    total_consumed = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    # Pricing
    avg_purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    
    class Meta:
        ordering = ['inventory_item_id']
        unique_together = ['report_period', 'inventory_item_id']
        verbose_name = 'Inventory Summary'
        verbose_name_plural = 'Inventory Summaries'
    
    def __str__(self):
        return f"{self.item_name} - {self.report_period.period_label}"
    
    @property
    def stock_movement(self) -> Decimal:
        """Net change in stock level."""
        return self.closing_stock - self.opening_stock
    
    @property
    def is_low_stock(self) -> bool:
        """Check if closing stock is below minimum."""
        # This would need to fetch from Details model
        # For now, return False - will be calculated in service
        return False


class EmailLog(models.Model):
    """
    Audit trail of report emails sent.
    """
    
    class EmailType(models.TextChoices):
        REPORT = 'REPORT', 'Report Email'
        ALERT = 'ALERT', 'Alert Email'
    
    email_type = models.CharField(
        max_length=20, 
        choices=EmailType.choices,
        default=EmailType.REPORT
    )
    report_period = models.ForeignKey(
        ReportPeriod, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs'
    )
    
    # Email details
    subject = models.CharField(max_length=255)
    recipients = models.TextField(help_text="Comma-separated email addresses")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_emails_sent'
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
