"""
Reports App Admin
Read-only admin interfaces for report periods and summaries.
All reports are immutable (bank ledger policy).
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ReportPeriod, 
    ReportProductSummary, 
    ReportSalespersonSummary,
    ReportInventorySummary,
    EmailLog
)


class ReportProductSummaryInline(admin.TabularInline):
    """Inline view of product summaries within a report."""
    model = ReportProductSummary
    extra = 0
    readonly_fields = [
        'product', 'units_produced', 'production_cost', 'batches_count',
        'units_dispatched', 'units_sold', 'units_returned', 'revenue',
        'gross_profit_display', 'gross_margin_display'
    ]
    can_delete = False
    
    def gross_profit_display(self, obj):
        if obj.pk:
            color = 'green' if obj.gross_profit > 0 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">KES {:,.2f}</span>',
                color, obj.gross_profit
            )
        return '-'
    gross_profit_display.short_description = 'Gross Profit'
    
    def gross_margin_display(self, obj):
        if obj.pk:
            color = 'green' if obj.gross_margin > 20 else 'orange'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.gross_margin
            )
        return '-'
    gross_margin_display.short_description = 'Margin'
    
    def has_add_permission(self, request, obj=None):
        return False


class ReportSalespersonSummaryInline(admin.TabularInline):
    """Inline view of salesperson summaries within a report."""
    model = ReportSalespersonSummary
    extra = 0
    readonly_fields = [
        'salesperson', 'dispatch_count', 'total_units_sold', 
        'total_revenue', 'total_commission', 'crates_lost',
        'return_rate_display', 'crate_loss_rate_display'
    ]
    can_delete = False
    
    def return_rate_display(self, obj):
        if obj.pk:
            color = 'green' if obj.return_rate < 10 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.return_rate
            )
        return '-'
    return_rate_display.short_description = 'Return Rate'
    
    def crate_loss_rate_display(self, obj):
        if obj.pk:
            color = 'green' if obj.crate_loss_rate == 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.crate_loss_rate
            )
        return '-'
    crate_loss_rate_display.short_description = 'Crate Loss'
    
    def has_add_permission(self, request, obj=None):
        return False


class ReportInventorySummaryInline(admin.TabularInline):
    """Inline view of inventory summaries within a report."""
    model = ReportInventorySummary
    extra = 0
    readonly_fields = [
        'inventory_item_id', 'item_name', 'opening_stock', 'closing_stock',
        'total_purchased', 'purchase_cost', 'total_consumed', 'stock_movement_display'
    ]
    can_delete = False
    
    def stock_movement_display(self, obj):
        if obj.pk:
            movement = obj.stock_movement
            color = 'green' if movement >= 0 else 'red'
            sign = '+' if movement > 0 else ''
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}{:.2f}</span>',
                color, sign, movement
            )
        return '-'
    stock_movement_display.short_description = 'Movement'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReportPeriod)
class ReportPeriodAdmin(admin.ModelAdmin):
    """
    Report Period Admin - Read-only overview of generated reports.
    """
    list_display = [
        'period_label',
        'period_type_badge',
        'date_range',
        'revenue_display',
        'profit_display',
        'margin_display',
        'email_status',
        'generated_at'
    ]
    list_filter = ['period_type', 'is_locked', 'email_sent']
    search_fields = ['period_label']
    readonly_fields = [
        'period_type', 'start_date', 'end_date', 'period_label',
        'total_revenue', 'total_units_sold', 'total_dispatches', 'total_returns',
        'total_commissions', 'total_units_produced', 'total_batches',
        'total_production_cost', 'average_yield_variance',
        'total_purchase_cost', 'total_purchases_count', 'low_stock_alerts',
        'total_crates_dispatched', 'total_crates_returned',
        'total_crates_lost', 'total_crates_damaged',
        'gross_profit', 'gross_margin_percentage',
        'generated_at', 'generated_by', 'is_locked',
        'email_sent', 'email_sent_at', 'email_recipients'
    ]
    inlines = [
        ReportProductSummaryInline, 
        ReportSalespersonSummaryInline,
        ReportInventorySummaryInline
    ]
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Period Information', {
            'fields': ('period_type', 'start_date', 'end_date', 'period_label', 'is_locked')
        }),
        ('Sales Summary', {
            'fields': (
                'total_revenue', 'total_units_sold', 'total_dispatches',
                'total_returns', 'total_commissions'
            )
        }),
        ('Production Summary', {
            'fields': (
                'total_units_produced', 'total_batches', 
                'total_production_cost', 'average_yield_variance'
            )
        }),
        ('Inventory Summary', {
            'fields': (
                'total_purchase_cost', 'total_purchases_count', 'low_stock_alerts'
            )
        }),
        ('Crate Tracking', {
            'fields': (
                'total_crates_dispatched', 'total_crates_returned',
                'total_crates_lost', 'total_crates_damaged'
            )
        }),
        ('Financial Summary', {
            'fields': ('gross_profit', 'gross_margin_percentage')
        }),
        ('Generation Metadata', {
            'fields': ('generated_at', 'generated_by'),
            'classes': ('collapse',)
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_sent_at', 'email_recipients'),
            'classes': ('collapse',)
        }),
    )
    
    def period_type_badge(self, obj):
        colors = {
            'DAILY': '#3b82f6',    # Blue
            'WEEKLY': '#8b5cf6',   # Purple
            'MONTHLY': '#059669',  # Green
            'ANNUAL': '#dc2626',   # Red
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            colors.get(obj.period_type, '#6b7280'),
            obj.get_period_type_display()
        )
    period_type_badge.short_description = 'Type'
    
    def date_range(self, obj):
        if obj.start_date == obj.end_date:
            return obj.start_date.strftime('%d %b %Y')
        return f"{obj.start_date.strftime('%d %b')} - {obj.end_date.strftime('%d %b %Y')}"
    date_range.short_description = 'Date Range'
    
    def revenue_display(self, obj):
        return format_html(
            '<strong style="color: #059669;">KES {:,.0f}</strong>',
            obj.total_revenue
        )
    revenue_display.short_description = 'Revenue'
    
    def profit_display(self, obj):
        color = '#059669' if obj.gross_profit > 0 else '#dc2626'
        return format_html(
            '<strong style="color: {};">KES {:,.0f}</strong>',
            color, obj.gross_profit
        )
    profit_display.short_description = 'Profit'
    
    def margin_display(self, obj):
        color = '#059669' if obj.gross_margin_percentage > 20 else '#f59e0b'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, obj.gross_margin_percentage
        )
    margin_display.short_description = 'Margin'
    
    def email_status(self, obj):
        if obj.email_sent:
            return format_html(
                '<span style="color: #059669;">✅ Sent</span>'
            )
        return format_html(
            '<span style="color: #6b7280;">⏳ Not sent</span>'
        )
    email_status.short_description = 'Email'
    
    def has_add_permission(self, request):
        """Reports are generated via service, not manually added."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Reports cannot be deleted (bank ledger policy)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Reports are immutable."""
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """
    Email Log Admin - Audit trail of sent emails.
    """
    list_display = [
        'subject_truncated',
        'email_type_badge',
        'recipients_truncated',
        'sent_by',
        'sent_at',
        'status_badge'
    ]
    list_filter = ['email_type', 'is_success', 'sent_at']
    search_fields = ['subject', 'recipients']
    readonly_fields = [
        'email_type', 'report_period', 'subject', 'recipients',
        'sent_by', 'sent_at', 'is_success', 'error_message'
    ]
    date_hierarchy = 'sent_at'
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Subject'
    
    def email_type_badge(self, obj):
        colors = {'REPORT': '#3b82f6', 'ALERT': '#f59e0b'}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.email_type, '#6b7280'),
            obj.get_email_type_display()
        )
    email_type_badge.short_description = 'Type'
    
    def recipients_truncated(self, obj):
        return obj.recipients[:40] + '...' if len(obj.recipients) > 40 else obj.recipients
    recipients_truncated.short_description = 'Recipients'
    
    def status_badge(self, obj):
        if obj.is_success:
            return format_html('<span style="color: #059669;">✅ Success</span>')
        return format_html('<span style="color: #dc2626;">❌ Failed</span>')
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
