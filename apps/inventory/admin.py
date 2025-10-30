"""
Inventory App Admin Configuration
Django Admin interface for inventory management
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ExpenseCategory, InventoryItem, Supplier, Purchase, PurchaseItem,
    StockMovement, WastageRecord, RestockAlert, UnitConversion, InventorySnapshot
)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """
    Expense category management (5 categories)
    """
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'code']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """
    37 inventory items with smart alerts
    """
    list_display = [
        'name', 
        'category', 
        'current_stock_display',
        'stock_status',
        'days_remaining',
        'cost_per_recipe_unit',
        'is_active'
    ]
    list_filter = ['category', 'low_stock_alert', 'is_active', 'purchase_unit', 'recipe_unit']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'is_active')
        }),
        ('Units & Conversion', {
            'fields': ('purchase_unit', 'recipe_unit', 'conversion_factor')
        }),
        ('Stock Tracking', {
            'fields': ('current_stock', 'reorder_level')
        }),
        ('Costing', {
            'fields': ('cost_per_purchase_unit', 'cost_per_recipe_unit'),
            'description': '🤖 cost_per_recipe_unit is auto-calculated'
        }),
        ('Alerts (Auto-calculated)', {
            'fields': ('low_stock_alert', 'days_remaining'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['cost_per_recipe_unit', 'low_stock_alert', 'days_remaining', 'created_at', 'created_by', 'updated_at', 'updated_by']
    
    def current_stock_display(self, obj):
        return f"{obj.current_stock} {obj.recipe_unit}"
    current_stock_display.short_description = "Current Stock"
    
    def stock_status(self, obj):
        if obj.low_stock_alert:
            color = 'red' if obj.days_remaining < 3 else 'orange'
            return format_html(
                '<span style="color: {}; font-weight: bold;">⚠️ LOW STOCK</span>',
                color
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    stock_status.short_description = "Status"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Supplier management
    """
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'phone', 'email', 'address')
        }),
        ('Payment Terms', {
            'fields': ('payment_terms',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class PurchaseItemInline(admin.TabularInline):
    """
    Inline editing of purchase items
    """
    model = PurchaseItem
    extra = 1
    fields = ['item', 'quantity', 'unit_cost', 'total_cost']
    readonly_fields = ['total_cost']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """
    Purchase order management
    """
    list_display = [
        'purchase_number',
        'supplier',
        'purchase_date',
        'status',
        'total_amount',
        'created_at'
    ]
    list_filter = ['status', 'purchase_date', 'supplier']
    search_fields = ['purchase_number', 'supplier__name', 'notes']
    
    inlines = [PurchaseItemInline]
    
    fieldsets = (
        ('Purchase Information', {
            'fields': ('purchase_number', 'supplier', 'purchase_date', 'status'),
            'description': '🤖 Purchase number is auto-generated: PUR-YYYYMMDD-XXX'
        }),
        ('Delivery Tracking', {
            'fields': ('expected_delivery_date', 'actual_delivery_date')
        }),
        ('Total (Auto-calculated)', {
            'fields': ('total_amount',),
            'description': '🤖 Automatically calculated from purchase items'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['purchase_number', 'total_amount', 'created_at', 'created_by', 'updated_at', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    """
    Purchase item management (backup to inline)
    """
    list_display = ['purchase', 'item', 'quantity', 'unit_cost', 'total_cost']
    list_filter = ['purchase__status', 'item__category']
    search_fields = ['item__name', 'purchase__purchase_number']
    
    fieldsets = (
        ('Purchase & Item', {
            'fields': ('purchase', 'item')
        }),
        ('Quantity & Cost', {
            'fields': ('quantity', 'unit_cost', 'total_cost'),
            'description': '🤖 total_cost is auto-calculated'
        }),
        ('Metadata', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_cost', 'added_at']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """
    Stock movement audit trail
    """
    list_display = [
        'item',
        'movement_type',
        'quantity',
        'unit',
        'stock_before',
        'stock_after',
        'created_at'
    ]
    list_filter = ['movement_type', 'created_at', 'item__category']
    search_fields = ['item__name', 'notes', 'reference_type']
    
    fieldsets = (
        ('Movement Details', {
            'fields': ('item', 'movement_type', 'quantity', 'unit')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'notes')
        }),
        ('Stock Levels', {
            'fields': ('stock_before', 'stock_after')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WastageRecord)
class WastageRecordAdmin(admin.ModelAdmin):
    """
    Damage/wastage tracking with CEO approval
    """
    list_display = [
        'item',
        'damage_type',
        'quantity',
        'cost',
        'damage_date',
        'approval_status_display',
        'requires_approval'
    ]
    list_filter = ['approval_status', 'requires_approval', 'damage_type', 'damage_date']
    search_fields = ['item__name', 'description']
    
    fieldsets = (
        ('Damage Details', {
            'fields': ('item', 'damage_type', 'quantity', 'cost', 'damage_date', 'description')
        }),
        ('Approval (Required if cost > KES 500)', {
            'fields': (
                'requires_approval',
                'approval_status',
                'approved_by',
                'approved_at',
                'approval_notes'
            ),
            'description': '🤖 requires_approval and cost are auto-calculated'
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['cost', 'requires_approval', 'approved_at', 'created_at', 'created_by']
    
    def approval_status_display(self, obj):
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.approval_status, 'gray'),
            obj.get_approval_status_display()
        )
    approval_status_display.short_description = "Approval Status"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RestockAlert)
class RestockAlertAdmin(admin.ModelAdmin):
    """
    Restock alert management
    """
    list_display = [
        'item',
        'alert_level_display',
        'days_remaining',
        'is_acknowledged',
        'created_at'
    ]
    list_filter = ['alert_level', 'is_acknowledged', 'created_at']
    search_fields = ['item__name', 'message']
    
    fieldsets = (
        ('Alert Details', {
            'fields': ('item', 'alert_level', 'days_remaining', 'message')
        }),
        ('Acknowledgment', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['acknowledged_at', 'created_at']
    
    def alert_level_display(self, obj):
        colors = {
            'LOW': 'orange',
            'CRITICAL': 'red',
            'OUT': 'darkred',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.alert_level, 'gray'),
            obj.get_alert_level_display()
        )
    alert_level_display.short_description = "Alert Level"


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    """
    Unit conversion rules
    """
    list_display = ['from_unit', 'to_unit', 'factor', 'notes']
    search_fields = ['from_unit', 'to_unit', 'notes']
    
    fieldsets = (
        ('Conversion', {
            'fields': ('from_unit', 'to_unit', 'factor', 'notes')
        }),
    )


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(admin.ModelAdmin):
    """
    Daily inventory snapshots
    """
    list_display = [
        'snapshot_date',
        'total_items',
        'total_value',
        'low_stock_items_count',
        'created_at'
    ]
    list_filter = ['snapshot_date', 'created_at']
    search_fields = ['snapshot_date']
    
    fieldsets = (
        ('Snapshot Date', {
            'fields': ('snapshot_date',)
        }),
        ('Aggregated Data', {
            'fields': ('total_items', 'total_value', 'low_stock_items_count')
        }),
        ('Snapshot Data (JSON)', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
