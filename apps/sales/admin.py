"""
Sales App - Admin Configuration

Bank Ledger Policy:
- NO delete allowed on any model
- NO edit allowed on SalesDispatch (except via service layer)
- SalesReturn: ONLY crates_marked_lost and crates_marked_damaged are editable
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    SalesDispatch,
    SalesDispatchItem,
    SalesReturn,
    SalesReturnItem
)


# ============================================================================
# INLINE ADMIN
# ============================================================================

class SalesDispatchItemInline(admin.TabularInline):
    """Inline for dispatch items - read-only."""
    model = SalesDispatchItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price', 'line_total_display']
    can_delete = False
    
    def line_total_display(self, obj):
        return f"KES {obj.line_total:,.2f}"
    line_total_display.short_description = 'Line Total'
    
    def has_add_permission(self, request, obj=None):
        return False


class SalesReturnItemInline(admin.TabularInline):
    """Inline for return items - read-only."""
    model = SalesReturnItem
    extra = 0
    readonly_fields = [
        'product', 'qty_dispatched', 'qty_sold', 'qty_returned',
        'unit_price', 'revenue'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# DISPATCH ADMIN
# ============================================================================

@admin.register(SalesDispatch)
class SalesDispatchAdmin(admin.ModelAdmin):
    """
    Admin for SalesDispatch - completely read-only.
    Bank ledger: NO edits, NO deletes.
    """
    
    list_display = [
        'dispatch_number',
        'salesperson_display',
        'dispatch_date',
        'total_units_display',
        'expected_revenue_display',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'is_returned', 'dispatch_date']
    search_fields = ['dispatch_number', 'salesperson__first_name', 'salesperson__last_name']
    date_hierarchy = 'dispatch_date'
    ordering = ['-dispatch_date', '-created_at']
    inlines = [SalesDispatchItemInline]
    
    # ALL fields are readonly
    readonly_fields = [
        'dispatch_number',
        'salesperson',
        'dispatch_date',
        'status',
        'crates_dispatched',
        'is_returned',
        'returned_at',
        'created_by',
        'created_at'
    ]
    
    fieldsets = (
        ('Dispatch Information', {
            'fields': (
                'dispatch_number',
                'salesperson',
                'dispatch_date',
                'status'
            )
        }),
        ('Crates', {
            'fields': ('crates_dispatched',)
        }),
        ('Return Status', {
            'fields': ('is_returned', 'returned_at')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def salesperson_display(self, obj):
        return obj.salesperson.get_display_name()
    salesperson_display.short_description = 'Salesperson'
    
    def total_units_display(self, obj):
        return obj.total_units
    total_units_display.short_description = 'Units'
    
    def expected_revenue_display(self, obj):
        return f"KES {obj.expected_revenue:,.2f}"
    expected_revenue_display.short_description = 'Expected Revenue'
    
    def status_badge(self, obj):
        colors = {
            'DISPATCHED': '#F59E0B',  # Amber
            'RETURNED': '#10B981',    # Green
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Create via views only
    
    def has_change_permission(self, request, obj=None):
        return False  # No editing allowed - bank ledger
    
    def has_delete_permission(self, request, obj=None):
        return False  # No deletion allowed - bank ledger


# ============================================================================
# RETURN ADMIN
# ============================================================================

@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    """
    Admin for SalesReturn.
    Bank ledger: ONLY crate status fields are editable.
    """
    
    list_display = [
        'dispatch_link',
        'return_date',
        'total_units_sold',
        'total_revenue_display',
        'commission_display',
        'crate_status_badge',
        'created_at'
    ]
    list_filter = ['return_date', 'crates_marked_lost', 'crates_marked_damaged']
    search_fields = [
        'dispatch__dispatch_number',
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ]
    date_hierarchy = 'return_date'
    ordering = ['-return_date', '-created_at']
    inlines = [SalesReturnItemInline]
    
    # Only crate status fields are editable
    readonly_fields = [
        'dispatch',
        'return_date',
        'total_units_sold',
        'total_revenue',
        'crates_returned',
        'crates_lost',
        'crates_damaged',
        'commission_amount',
        'notes',
        'created_by',
        'created_at'
    ]
    
    fieldsets = (
        ('Return Information', {
            'fields': ('dispatch', 'return_date')
        }),
        ('Sales Totals', {
            'fields': ('total_units_sold', 'total_revenue')
        }),
        ('Crates', {
            'fields': (
                'crates_returned',
                'crates_lost',
                'crates_damaged',
                'crates_marked_lost',      # ONLY editable field
                'crates_marked_damaged'    # ONLY editable field
            ),
            'description': 'Only the "marked" checkboxes can be changed.'
        }),
        ('Commission', {
            'fields': ('commission_amount',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def dispatch_link(self, obj):
        return format_html(
            '<a href="/admin/sales/salesdispatch/{}/change/">{}</a>',
            obj.dispatch.id, obj.dispatch.dispatch_number
        )
    dispatch_link.short_description = 'Dispatch'
    
    def total_revenue_display(self, obj):
        return f"KES {obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Revenue'
    
    def commission_display(self, obj):
        if obj.commission_amount is None:
            return format_html('<span style="color: #6B7280;">—</span>')
        return format_html(
            '<span style="color: #10B981;">KES {:,.2f}</span>',
            obj.commission_amount
        )
    commission_display.short_description = 'Commission'
    
    def crate_status_badge(self, obj):
        """Badge showing crate accountability status."""
        has_lost = obj.crates_lost > 0
        has_damaged = obj.crates_damaged > 0
        
        if has_lost or has_damaged:
            lost_resolved = not has_lost or obj.crates_marked_lost
            damaged_resolved = not has_damaged or obj.crates_marked_damaged
            
            if lost_resolved and damaged_resolved:
                return format_html(
                    '<span style="color: #F59E0B;">⚠️ Resolved</span>'
                )
            return format_html(
                '<span style="color: #EF4444;">⚠️ {} lost, {} damaged</span>',
                obj.crates_lost, obj.crates_damaged
            )
        return format_html(
            '<span style="color: #10B981;">✓ All returned</span>'
        )
    crate_status_badge.short_description = 'Crates'
    
    def has_add_permission(self, request):
        return False  # Create via views only
    
    def has_delete_permission(self, request, obj=None):
        return False  # No deletion allowed - bank ledger

