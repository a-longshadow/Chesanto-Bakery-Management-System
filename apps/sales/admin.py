"""
Sales App Admin
Admin interfaces for dispatch, returns, and commission tracking
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    CommissionSettings,
    Salesperson,
    Dispatch,
    DispatchItem,
    SalesReturn,
    SalesReturnItem,
    DailySales,
)


@admin.register(CommissionSettings)
class CommissionSettingsAdmin(admin.ModelAdmin):
    """Admin for commission configuration (Superuser only)"""
    list_display = [
        'effective_from',
        'display_per_unit_commission',
        'display_bonus_structure',
        'is_active',
        'updated_at',
        'updated_by',
    ]
    list_filter = ['is_active', 'effective_from']
    readonly_fields = ['created_at', 'updated_at', 'updated_by']
    
    fieldsets = (
        ('Commission Rates', {
            'fields': ('per_unit_commission', 'bonus_threshold', 'bonus_percentage')
        }),
        ('Effective Period', {
            'fields': ('effective_from', 'is_active')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def display_per_unit_commission(self, obj):
        """Display per-unit commission"""
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {}</span>',
            obj.per_unit_commission
        )
    display_per_unit_commission.short_description = "Per Unit"
    
    def display_bonus_structure(self, obj):
        """Display bonus structure"""
        return format_html(
            '<strong>{}%</strong> above KES {:,}',
            obj.bonus_percentage,
            obj.bonus_threshold
        )
    display_bonus_structure.short_description = "Bonus Structure"
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of active settings"""
        if obj and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Auto-populate updated_by"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class DispatchItemInline(admin.TabularInline):
    """Inline for multiple products in one dispatch"""
    model = DispatchItem
    extra = 3  # Default 3 products (Bread, KDF, Scones)
    readonly_fields = ['cost_per_unit', 'selling_price', 'expected_revenue']
    fields = ['product', 'quantity', 'cost_per_unit', 'selling_price', 'expected_revenue']


@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):
    """Admin for salespeople/schools/depots"""
    list_display = [
        'name',
        'recipient_type',
        'phone',
        'location',
        'display_commission_structure',
        'is_active',
    ]
    list_filter = ['recipient_type', 'is_active']
    search_fields = ['name', 'phone', 'email', 'location']
    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'recipient_type', 'phone', 'email', 'location')
        }),
        ('Commission Structure', {
            'fields': (
                'commission_per_bread',
                'commission_per_kdf',
                'commission_per_scones',
                'sales_target',
                'bonus_commission_rate',
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def display_commission_structure(self, obj):
        """Display commission rates"""
        return format_html(
            "Bread: KES {}<br>KDF: KES {}<br>Scones: KES {}<br>Target: KES {:,}",
            obj.commission_per_bread,
            obj.commission_per_kdf,
            obj.commission_per_scones,
            obj.sales_target,
        )
    display_commission_structure.short_description = "Commission Structure"
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by/updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    """Admin for daily dispatches"""
    list_display = [
        'date',
        'salesperson',
        'display_products',
        'display_expected_revenue',
        'crates_dispatched',
        'display_return_status',
    ]
    list_filter = ['date', 'is_returned']
    search_fields = ['salesperson__name']
    readonly_fields = ['expected_revenue', 'is_returned', 'returned_at', 'created_at']
    inlines = [DispatchItemInline]
    
    fieldsets = (
        ('Dispatch Information', {
            'fields': ('date', 'salesperson', 'crates_dispatched')
        }),
        ('Revenue', {
            'fields': ('expected_revenue',)
        }),
        ('Return Status', {
            'fields': ('is_returned', 'returned_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def display_products(self, obj):
        """Display all dispatched products"""
        items = obj.dispatchitem_set.all()
        return format_html(
            "<br>".join([f"{item.product.name}: {item.quantity}" for item in items])
        )
    display_products.short_description = "Products Dispatched"
    
    def display_expected_revenue(self, obj):
        """Display expected revenue with color"""
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,}</span>',
            obj.expected_revenue
        )
    display_expected_revenue.short_description = "Expected Revenue"
    
    def display_return_status(self, obj):
        """Display return status with icon"""
        if obj.is_returned:
            return format_html(
                '<span style="color: green;">✅ Returned</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⏳ Pending</span>'
            )
    display_return_status.short_description = "Return Status"
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class SalesReturnItemInline(admin.TabularInline):
    """Inline for product-level sales tracking"""
    model = SalesReturnItem
    extra = 0
    readonly_fields = ['units_dispatched', 'units_sold', 'selling_price', 'gross_sales', 'damaged_value', 'net_sales']
    fields = [
        'product',
        'units_dispatched',
        'units_returned',
        'units_damaged',
        'units_sold',
        'selling_price',
        'gross_sales',
        'damaged_value',
        'net_sales',
    ]


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    """Admin for sales returns with deficit tracking"""
    list_display = [
        'dispatch',
        'return_date',
        'display_cash_returned',
        'display_revenue_deficit',
        'display_crate_deficit',
        'display_commission',
        'deficit_resolved',
    ]
    list_filter = ['return_date', 'deficit_resolved', 'deficit_alert_sent']
    search_fields = ['dispatch__salesperson__name']
    readonly_fields = [
        'crates_deficit',
        'revenue_deficit',
        'per_unit_commission',
        'bonus_commission',
        'total_commission',
        'deficit_alert_sent',
        'created_at',
        'updated_at',
    ]
    inlines = [SalesReturnItemInline]
    
    fieldsets = (
        ('Return Information', {
            'fields': ('dispatch', 'return_date', 'return_time')
        }),
        ('Crates', {
            'fields': ('crates_returned', 'crates_deficit')
        }),
        ('Revenue', {
            'fields': ('cash_returned', 'revenue_deficit')
        }),
        ('Commission', {
            'fields': ('per_unit_commission', 'bonus_commission', 'total_commission')
        }),
        ('Deficit Management', {
            'fields': ('deficit_reason', 'deficit_resolved', 'deficit_alert_sent')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def display_cash_returned(self, obj):
        """Display cash with color"""
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,}</span>',
            obj.cash_returned
        )
    display_cash_returned.short_description = "Cash Returned"
    
    def display_revenue_deficit(self, obj):
        """Display revenue deficit with color-coding"""
        if obj.revenue_deficit == 0:
            color = 'green'
            icon = '✅'
        elif obj.revenue_deficit <= 500:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'red'
            icon = '🚨'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} KES {:,}</span>',
            color,
            icon,
            obj.revenue_deficit
        )
    display_revenue_deficit.short_description = "Revenue Deficit"
    
    def display_crate_deficit(self, obj):
        """Display crate deficit"""
        if obj.crates_deficit == 0:
            return format_html('<span style="color: green;">✅ No deficit</span>')
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {} crates</span>',
                obj.crates_deficit
            )
    display_crate_deficit.short_description = "Crate Deficit"
    
    def display_commission(self, obj):
        """Display total commission"""
        return format_html(
            '<span style="color: blue; font-weight: bold;">KES {:,}</span><br>'
            '<small>Per-unit: KES {:,}<br>Bonus: KES {:,}</small>',
            obj.total_commission,
            obj.per_unit_commission,
            obj.bonus_commission,
        )
    display_commission.short_description = "Commission"
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by/updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    """Admin for daily sales summary"""
    list_display = [
        'date',
        'total_dispatched',
        'display_expected_revenue',
        'display_actual_revenue',
        'display_deficit',
        'display_commissions',
    ]
    list_filter = ['date']
    readonly_fields = [
        'total_dispatched',
        'total_expected_revenue',
        'total_actual_revenue',
        'total_revenue_deficit',
        'total_commissions',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Summary', {
            'fields': (
                'total_dispatched',
                'total_expected_revenue',
                'total_actual_revenue',
                'total_revenue_deficit',
                'total_commissions',
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def display_expected_revenue(self, obj):
        """Display expected revenue"""
        return format_html(
            '<span style="color: green;">KES {:,}</span>',
            obj.total_expected_revenue
        )
    display_expected_revenue.short_description = "Expected Revenue"
    
    def display_actual_revenue(self, obj):
        """Display actual revenue"""
        return format_html(
            '<span style="color: blue; font-weight: bold;">KES {:,}</span>',
            obj.total_actual_revenue
        )
    display_actual_revenue.short_description = "Actual Revenue"
    
    def display_deficit(self, obj):
        """Display deficit with color-coding"""
        if obj.total_revenue_deficit == 0:
            color = 'green'
            icon = '✅'
        elif obj.total_revenue_deficit <= 1000:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'red'
            icon = '🚨'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} KES {:,}</span>',
            color,
            icon,
            obj.total_revenue_deficit
        )
    display_deficit.short_description = "Revenue Deficit"
    
    def display_commissions(self, obj):
        """Display total commissions"""
        return format_html(
            '<span style="color: purple; font-weight: bold;">KES {:,}</span>',
            obj.total_commissions
        )
    display_commissions.short_description = "Total Commissions"
    
    def save_model(self, request, obj, form, change):
        """Auto-populate created_by/updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

