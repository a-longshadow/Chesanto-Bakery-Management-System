"""
Products App Admin Configuration
Django Admin interface for products management
"""
from django.contrib import admin
from .models import Product, Ingredient, Mix, MixIngredient


class MixIngredientInline(admin.TabularInline):
    """
    Inline editing of ingredients within Mix admin page
    """
    model = MixIngredient
    extra = 1
    fields = ['ingredient', 'quantity', 'unit', 'ingredient_cost']
    readonly_fields = ['ingredient_cost']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Product catalog management
    """
    list_display = [
        'name', 
        'alias', 
        'price_per_packet', 
        'units_per_packet', 
        'baseline_output',
        'has_sub_product',
        'is_active'
    ]
    list_filter = ['is_active', 'has_variable_output', 'has_sub_product']
    search_fields = ['name', 'alias', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'alias', 'description', 'is_active')
        }),
        ('Output Characteristics', {
            'fields': (
                'has_variable_output',
                'baseline_output',
                'min_expected_output',
                'max_expected_output'
            )
        }),
        ('Packaging', {
            'fields': ('units_per_packet', 'packet_label')
        }),
        ('Pricing', {
            'fields': ('price_per_packet',)
        }),
        ('Sub-Product', {
            'fields': ('has_sub_product', 'sub_product_name', 'sub_product_price'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by and updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """
    Master ingredients management
    """
    list_display = ['name', 'default_unit', 'is_active']
    list_filter = ['is_active', 'default_unit']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'default_unit', 'is_active')
        }),
        # ('Inventory Link', {
        #     'fields': ('inventory_item',)
        # }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by and updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Mix)
class MixAdmin(admin.ModelAdmin):
    """
    Recipe management with inline ingredients
    """
    list_display = [
        'product', 
        'name', 
        'version', 
        'expected_packets',
        'total_cost',
        'cost_per_packet',
        'is_active'
    ]
    list_filter = ['is_active', 'product']
    search_fields = ['name', 'notes', 'product__name']
    
    inlines = [MixIngredientInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'name', 'version', 'is_active')
        }),
        ('Yield', {
            'fields': ('expected_packets',)
        }),
        ('Costs (Auto-calculated)', {
            'fields': ('total_cost', 'cost_per_packet'),
            'description': '🤖 These fields are automatically calculated from ingredients'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['total_cost', 'cost_per_packet', 'created_at', 'created_by', 'updated_at', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by and updated_by"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MixIngredient)
class MixIngredientAdmin(admin.ModelAdmin):
    """
    Individual ingredient management (backup to inline editing)
    """
    list_display = ['mix', 'ingredient', 'quantity', 'unit', 'ingredient_cost']
    list_filter = ['unit', 'mix__product']
    search_fields = ['ingredient__name', 'mix__name']
    
    fieldsets = (
        ('Mix & Ingredient', {
            'fields': ('mix', 'ingredient')
        }),
        ('Quantity (Manual Entry)', {
            'fields': ('quantity', 'unit')
        }),
        ('Cost (Auto-calculated)', {
            'fields': ('ingredient_cost',),
            'description': '🤖 Automatically calculated from Inventory'
        }),
        ('Metadata', {
            'fields': ('added_at', 'added_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['ingredient_cost', 'added_at', 'added_by']
    
    def save_model(self, request, obj, form, change):
        """Auto-set added_by"""
        if not change:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)
