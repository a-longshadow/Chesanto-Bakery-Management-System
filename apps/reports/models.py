"""
Reports App Models
Immutable reports generated after daily book closing
Stores calculated metrics for historical reporting
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class DailyReport(models.Model):
    """
    Daily report generated at book closing (9PM)
    Immutable after creation - stores snapshot of all daily metrics
    """
    date = models.DateField(unique=True, help_text="Report date")
    
    # Production Summary
    bread_produced = models.IntegerField(default=0, help_text="Total bread produced")
    kdf_produced = models.IntegerField(default=0, help_text="Total KDF produced")
    scones_produced = models.IntegerField(default=0, help_text="Total scones produced")
    total_batches = models.IntegerField(default=0, help_text="Number of batches")
    
    # Sales Summary
    bread_dispatched = models.IntegerField(default=0)
    kdf_dispatched = models.IntegerField(default=0)
    scones_dispatched = models.IntegerField(default=0)
    bread_returned = models.IntegerField(default=0)
    kdf_returned = models.IntegerField(default=0)
    scones_returned = models.IntegerField(default=0)
    bread_sold = models.IntegerField(default=0, help_text="dispatched - returned")
    kdf_sold = models.IntegerField(default=0)
    scones_sold = models.IntegerField(default=0)
    
    # Financial Summary
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Cash returned from all sales"
    )
    total_direct_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Ingredients + packaging"
    )
    total_indirect_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Diesel + firewood + electricity + fuel"
    )
    total_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Direct + indirect costs"
    )
    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Revenue - total costs"
    )
    gross_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="(Gross profit / Revenue) × 100"
    )
    
    # Deficits
    revenue_deficits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Sum of all revenue deficits"
    )
    crate_deficits = models.IntegerField(
        default=0,
        help_text="Sum of all crate deficits"
    )
    
    # Commissions
    total_commissions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Sum of all commissions paid"
    )
    
    # Product-Level P&L
    bread_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    kdf_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    scones_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status
    is_locked = models.BooleanField(
        default=True,
        help_text="Always true - reports are immutable"
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When report was generated"
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='daily_reports_generated'
    )
    
    # Email
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
    
    def __str__(self):
        return f"Daily Report - {self.date}"


class WeeklyReport(models.Model):
    """
    Weekly report (7 days aggregation)
    Generated every Sunday at 8AM
    """
    week_ending = models.DateField(
        unique=True,
        help_text="Last day of the week (Sunday)"
    )
    week_starting = models.DateField(help_text="First day of the week (Monday)")
    
    # Production Summary (7 days totals)
    total_bread_produced = models.IntegerField(default=0)
    total_kdf_produced = models.IntegerField(default=0)
    total_scones_produced = models.IntegerField(default=0)
    total_batches = models.IntegerField(default=0)
    
    # Sales Summary (7 days totals)
    total_bread_sold = models.IntegerField(default=0)
    total_kdf_sold = models.IntegerField(default=0)
    total_scones_sold = models.IntegerField(default=0)
    
    # Financial Summary (7 days totals)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Average margin across 7 days"
    )
    
    # Deficits (7 days totals)
    total_revenue_deficits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crate_deficits = models.IntegerField(default=0)
    
    # Commissions (7 days totals)
    total_commissions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_locked = models.BooleanField(default=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='weekly_reports_generated'
    )
    
    # Email
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-week_ending']
        verbose_name = "Weekly Report"
        verbose_name_plural = "Weekly Reports"
    
    def __str__(self):
        return f"Weekly Report - {self.week_starting} to {self.week_ending}"


class MonthlyReport(models.Model):
    """
    Monthly report (30 days aggregation)
    Generated on 1st of each month at 12AM
    """
    month = models.DateField(
        unique=True,
        help_text="First day of the month"
    )
    month_name = models.CharField(
        max_length=20,
        help_text="Month name (e.g., 'October 2025')"
    )
    
    # Production Summary (30 days totals)
    total_bread_produced = models.IntegerField(default=0)
    total_kdf_produced = models.IntegerField(default=0)
    total_scones_produced = models.IntegerField(default=0)
    total_batches = models.IntegerField(default=0)
    
    # Sales Summary (30 days totals)
    total_bread_sold = models.IntegerField(default=0)
    total_kdf_sold = models.IntegerField(default=0)
    total_scones_sold = models.IntegerField(default=0)
    
    # Financial Summary (30 days totals)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_direct_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_indirect_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    average_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Deficits (30 days totals)
    total_revenue_deficits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crate_deficits = models.IntegerField(default=0)
    deficit_incidents = models.IntegerField(
        default=0,
        help_text="Number of sales returns with deficits"
    )
    
    # Commissions (30 days totals)
    total_commissions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_per_unit_commissions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_bonus_commissions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Product-Level P&L (30 days)
    bread_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bread_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    kdf_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kdf_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    scones_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scones_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status
    is_locked = models.BooleanField(default=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='monthly_reports_generated'
    )
    
    # Email
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-month']
        verbose_name = "Monthly Report"
        verbose_name_plural = "Monthly Reports"
    
    def __str__(self):
        return f"Monthly Report - {self.month_name}"
