"""
Production App - Django Admin Configuration

Provides read-only admin for immutable records and limited editing for ProductStock.
"""

from django.contrib import admin
from django.utils.html import format_html
import json

from .models import (
    ProductionBatch,
    BatchIngredientDeduction,
    ProductStock,
    ProductStockMovement
)


class BatchIngredientDeductionInline(admin.TabularInline):
    """Inline display of ingredient deductions for a batch."""
    model = BatchIngredientDeduction
    extra = 0
    can_delete = False
    readonly_fields = [
        'inventory_item_id', 'item_name', 'quantity_deducted', 'unit',
        'unit_price_at_deduction', 'line_cost', 'stock_before', 'stock_after'
    ]
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    """
    Read-only admin for ProductionBatch (immutable records).
    """
    list_display = [
        'batch_number',
        'product',
        'quantity_produced',
        'production_date',
        'total_ingredient_cost_display',
        'cost_per_unit_display',
        'yield_variance_display',
        'produced_by'
    ]
    list_filter = ['product', 'production_date', 'produced_by']
    search_fields = ['batch_number', 'product__name']
    date_hierarchy = 'production_date'
    ordering = ['-production_date', '-created_at']
    
    inlines = [BatchIngredientDeductionInline]
    
    readonly_fields = [
        'batch_number',
        'product',
        'mix',
        'mix_snapshot_display',
        'quantity_produced',
        'expected_yield',
        'yield_variance_display',
        'total_ingredient_cost',
        'cost_per_unit',
        'production_date',
        'production_time',
        'produced_by',
        'notes',
        'created_at',
    ]
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'product', 'mix', 'production_date', 'production_time')
        }),
        ('Yield', {
            'fields': ('quantity_produced', 'expected_yield', 'yield_variance_display')
        }),
        ('Costs', {
            'fields': ('total_ingredient_cost', 'cost_per_unit')
        }),
        ('Recipe Snapshot', {
            'fields': ('mix_snapshot_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('produced_by', 'notes', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Batches are created via service, not admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Batches are immutable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Batches cannot be deleted."""
        return False
    
    @admin.display(description='Total Cost')
    def total_ingredient_cost_display(self, obj):
        return f"KES {obj.total_ingredient_cost:,.2f}"
    
    @admin.display(description='Cost/Unit')
    def cost_per_unit_display(self, obj):
        return f"KES {obj.cost_per_unit:,.4f}"
    
    @admin.display(description='Yield Variance')
    def yield_variance_display(self, obj):
        variance = obj.yield_variance
        pct = obj.yield_variance_percentage
        color = 'green' if obj.is_within_acceptable_variance else 'red'
        sign = '+' if variance > 0 else ''
        return format_html(
            '<span style="color: {}">{}{} ({:.1f}%)</span>',
            color, sign, variance, pct
        )
    
    @admin.display(description='Mix Snapshot')
    def mix_snapshot_display(self, obj):
        return format_html(
            '<pre style="max-width: 600px; overflow: auto; background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
            json.dumps(obj.mix_snapshot, indent=2)
        )


@admin.register(BatchIngredientDeduction)
class BatchIngredientDeductionAdmin(admin.ModelAdmin):
    """
    Read-only admin for ingredient deductions (immutable).
    """
    list_display = [
        'batch',
        'item_name',
        'quantity_deducted',
        'unit',
        'unit_price_display',
        'line_cost_display'
    ]
    list_filter = ['inventory_item_id', 'batch__production_date']
    search_fields = ['batch__batch_number', 'item_name']
    
    readonly_fields = [
        'batch',
        'inventory_item_id',
        'item_name',
        'quantity_deducted',
        'unit',
        'unit_price_at_deduction',
        'line_cost',
        'stock_before',
        'stock_after',
        'created_at'
    ]
    
    @admin.display(description='Unit Price')
    def unit_price_display(self, obj):
        return f"KES {obj.unit_price_at_deduction:,.2f}"
    
    @admin.display(description='Line Cost')
    def line_cost_display(self, obj):
        return f"KES {obj.line_cost:,.2f}"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    """
    Admin for ProductStock - primarily read, limited edits for corrections.
    """
    list_display = [
        'product',
        'current_stock',
        'last_production_date',
        'updated_at'
    ]
    list_filter = ['product']
    
    readonly_fields = [
        'product',
        'last_production_batch',
        'last_production_date',
        'created_at',
        'updated_at'
    ]
    
    fields = [
        'product',
        'current_stock',
        'last_production_date',
        'last_production_batch',
        'updated_at'
    ]
    
    def has_add_permission(self, request):
        """Stock records created via seeding or production."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductStockMovement)
class ProductStockMovementAdmin(admin.ModelAdmin):
    """
    Read-only admin for stock movements (immutable audit trail).
    """
    list_display = [
        'product',
        'movement_type',
        'quantity_display',
        'stock_before',
        'stock_after',
        'recorded_by',
        'created_at'
    ]
    list_filter = ['product', 'movement_type', 'created_at']
    search_fields = ['product__name', 'reference_type']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = [
        'product',
        'movement_type',
        'quantity',
        'stock_before',
        'stock_after',
        'reference_type',
        'reference_id',
        'recorded_by',
        'notes',
        'created_at'
    ]
    
    @admin.display(description='Quantity')
    def quantity_display(self, obj):
        if obj.quantity > 0:
            return format_html('<span style="color: green;">+{}</span>', obj.quantity)
        else:
            return format_html('<span style="color: red;">{}</span>', obj.quantity)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
