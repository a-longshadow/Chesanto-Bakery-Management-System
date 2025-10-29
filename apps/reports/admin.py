"""
Reports App Admin
Read-only admin interfaces for immutable reports
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import DailyReport, WeeklyReport, MonthlyReport


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    """Read-only admin for daily reports"""
    list_display = [
        'date',
        'display_revenue',
        'display_profit',
        'display_margin',
        'display_deficits',
        'email_sent',
    ]
    list_filter = ['date', 'email_sent']
    search_fields = ['date']
    readonly_fields = [
        'date', 'bread_produced', 'kdf_produced', 'scones_produced', 'total_batches',
        'bread_dispatched', 'kdf_dispatched', 'scones_dispatched',
        'bread_returned', 'kdf_returned', 'scones_returned',
        'bread_sold', 'kdf_sold', 'scones_sold',
        'total_revenue', 'total_direct_costs', 'total_indirect_costs', 'total_costs',
        'gross_profit', 'gross_margin_percentage',
        'revenue_deficits', 'crate_deficits', 'total_commissions',
        'bread_revenue', 'bread_cost', 'bread_profit', 'bread_margin',
        'kdf_revenue', 'kdf_cost', 'kdf_profit', 'kdf_margin',
        'scones_revenue', 'scones_cost', 'scones_profit', 'scones_margin',
        'is_locked', 'generated_at', 'generated_by', 'email_sent', 'email_sent_at',
    ]
    
    fieldsets = (
        ('Report Date', {
            'fields': ('date', 'is_locked', 'generated_at', 'generated_by')
        }),
        ('Production Summary', {
            'fields': (
                'bread_produced', 'kdf_produced', 'scones_produced', 'total_batches'
            )
        }),
        ('Sales Summary', {
            'fields': (
                ('bread_dispatched', 'bread_returned', 'bread_sold'),
                ('kdf_dispatched', 'kdf_returned', 'kdf_sold'),
                ('scones_dispatched', 'scones_returned', 'scones_sold'),
            )
        }),
        ('Financial Summary', {
            'fields': (
                'total_revenue',
                'total_direct_costs',
                'total_indirect_costs',
                'total_costs',
                'gross_profit',
                'gross_margin_percentage',
            )
        }),
        ('Product P&L - Bread', {
            'fields': ('bread_revenue', 'bread_cost', 'bread_profit', 'bread_margin'),
            'classes': ('collapse',)
        }),
        ('Product P&L - KDF', {
            'fields': ('kdf_revenue', 'kdf_cost', 'kdf_profit', 'kdf_margin'),
            'classes': ('collapse',)
        }),
        ('Product P&L - Scones', {
            'fields': ('scones_revenue', 'scones_cost', 'scones_profit', 'scones_margin'),
            'classes': ('collapse',)
        }),
        ('Deficits & Commissions', {
            'fields': ('revenue_deficits', 'crate_deficits', 'total_commissions')
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Cannot manually add reports"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Cannot delete reports"""
        return False
    
    def display_revenue(self, obj):
        """Display total revenue"""
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,}</span>',
            obj.total_revenue
        )
    display_revenue.short_description = "Revenue"
    
    def display_profit(self, obj):
        """Display gross profit"""
        color = 'green' if obj.gross_profit > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">KES {:,}</span>',
            color,
            obj.gross_profit
        )
    display_profit.short_description = "Profit"
    
    def display_margin(self, obj):
        """Display margin percentage"""
        color = 'green' if obj.gross_margin_percentage > 30 else 'orange'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            obj.gross_margin_percentage
        )
    display_margin.short_description = "Margin"
    
    def display_deficits(self, obj):
        """Display deficits"""
        if obj.revenue_deficits == 0:
            return format_html('<span style="color: green;">✅ No deficits</span>')
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ KES {:,}</span>',
                obj.revenue_deficits
            )
    display_deficits.short_description = "Deficits"


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    """Read-only admin for weekly reports"""
    list_display = [
        'week_starting',
        'week_ending',
        'display_revenue',
        'display_profit',
        'display_margin',
        'email_sent',
    ]
    list_filter = ['week_ending', 'email_sent']
    readonly_fields = [
        'week_ending', 'week_starting',
        'total_bread_produced', 'total_kdf_produced', 'total_scones_produced', 'total_batches',
        'total_bread_sold', 'total_kdf_sold', 'total_scones_sold',
        'total_revenue', 'total_costs', 'total_profit', 'average_margin',
        'total_revenue_deficits', 'total_crate_deficits', 'total_commissions',
        'is_locked', 'generated_at', 'generated_by', 'email_sent', 'email_sent_at',
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def display_revenue(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,}</span>',
            obj.total_revenue
        )
    display_revenue.short_description = "Revenue"
    
    def display_profit(self, obj):
        color = 'green' if obj.total_profit > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">KES {:,}</span>',
            color,
            obj.total_profit
        )
    display_profit.short_description = "Profit"
    
    def display_margin(self, obj):
        color = 'green' if obj.average_margin > 30 else 'orange'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            obj.average_margin
        )
    display_margin.short_description = "Avg Margin"


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    """Read-only admin for monthly reports"""
    list_display = [
        'month_name',
        'display_revenue',
        'display_profit',
        'display_margin',
        'display_deficits',
        'email_sent',
    ]
    list_filter = ['month', 'email_sent']
    readonly_fields = [
        'month', 'month_name',
        'total_bread_produced', 'total_kdf_produced', 'total_scones_produced', 'total_batches',
        'total_bread_sold', 'total_kdf_sold', 'total_scones_sold',
        'total_revenue', 'total_direct_costs', 'total_indirect_costs', 'total_costs',
        'total_profit', 'average_margin',
        'total_revenue_deficits', 'total_crate_deficits', 'deficit_incidents',
        'total_commissions', 'total_per_unit_commissions', 'total_bonus_commissions',
        'bread_revenue', 'bread_cost', 'bread_profit', 'bread_margin',
        'kdf_revenue', 'kdf_cost', 'kdf_profit', 'kdf_margin',
        'scones_revenue', 'scones_cost', 'scones_profit', 'scones_margin',
        'is_locked', 'generated_at', 'generated_by', 'email_sent', 'email_sent_at',
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def display_revenue(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,}</span>',
            obj.total_revenue
        )
    display_revenue.short_description = "Revenue"
    
    def display_profit(self, obj):
        color = 'green' if obj.total_profit > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">KES {:,}</span>',
            color,
            obj.total_profit
        )
    display_profit.short_description = "Profit"
    
    def display_margin(self, obj):
        color = 'green' if obj.average_margin > 30 else 'orange'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            obj.average_margin
        )
    display_margin.short_description = "Avg Margin"
    
    def display_deficits(self, obj):
        if obj.total_revenue_deficits == 0:
            return format_html('<span style="color: green;">✅ No deficits</span>')
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {} incidents (KES {:,})</span>',
                obj.deficit_incidents,
                obj.total_revenue_deficits
            )
    display_deficits.short_description = "Deficits"
