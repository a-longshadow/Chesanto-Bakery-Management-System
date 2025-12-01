"""
Products App - Admin Configuration
Django Admin interface for Product, Mix, and MixIngredient management.
"""
from django.contrib import admin
from .models import Product, Mix, MixIngredient


class MixIngredientInline(admin.TabularInline):
    """Inline editor for mix ingredients"""
    model = MixIngredient
    extra = 1
    fields = ['inventory_item_id', 'quantity_required', 'unit_of_measure', 'notes']
    readonly_fields = ['created_at']
    
    def get_formfield_overrides(self):
        """Custom field overrides for better UX"""
        from django.db import models
        from django.forms import NumberInput, Select
        return {
            models.DecimalField: {'widget': NumberInput(attrs={'step': '0.0001', 'min': '0.0001'})},
        }


class MixInline(admin.TabularInline):
    """Inline editor for product mixes"""
    model = Mix
    extra = 0
    fields = ['name', 'expected_yield', 'is_fixed_yield', 'is_active']
    readonly_fields = []
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'selling_price', 'parent_product', 'is_active', 'has_active_mix_display', 'updated_at']
    list_filter = ['is_active', 'parent_product']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [MixInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'selling_price', 'description')
        }),
        ('Hierarchy', {
            'fields': ('parent_product',),
            'description': 'Set parent for sub-products (e.g., Bread Leftovers → Bread)'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_active_mix_display(self, obj):
        """Display whether product has an active mix"""
        return "✓ Yes" if obj.has_active_mix else "✗ No"
    has_active_mix_display.short_description = "Has Recipe"
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['archive_products', 'restore_products']
    
    @admin.action(description="Archive selected products")
    def archive_products(self, request, queryset):
        from .services import ProductService
        count = 0
        for product in queryset.filter(is_active=True):
            ProductService.archive_product(product.id, request.user)
            count += 1
        self.message_user(request, f"Archived {count} products.")
    
    @admin.action(description="Restore selected products")
    def restore_products(self, request, queryset):
        from .services import ProductService
        count = 0
        for product in queryset.filter(is_active=False):
            ProductService.restore_product(product.id, request.user)
            count += 1
        self.message_user(request, f"Restored {count} products.")


@admin.register(Mix)
class MixAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'expected_yield', 'is_fixed_yield', 'is_active', 'ingredients_count', 'updated_at']
    list_filter = ['is_active', 'is_fixed_yield', 'product']
    search_fields = ['name', 'product__name']
    inlines = [MixIngredientInline]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        (None, {
            'fields': ('product', 'name')
        }),
        ('Yield Configuration', {
            'fields': ('expected_yield', 'is_fixed_yield', 'yield_variance_min', 'yield_variance_max'),
            'description': 'For variable yield products (hand-cut), set min/max variance.'
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def ingredients_count(self, obj):
        """Display count of ingredients"""
        return obj.total_ingredients_count
    ingredients_count.short_description = "# Ingredients"
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['archive_mixes', 'restore_mixes']
    
    @admin.action(description="Archive selected mixes")
    def archive_mixes(self, request, queryset):
        from .services import MixService
        count = 0
        for mix in queryset.filter(is_active=True):
            MixService.archive_mix(mix.id, request.user)
            count += 1
        self.message_user(request, f"Archived {count} mixes.")
    
    @admin.action(description="Restore selected mixes")
    def restore_mixes(self, request, queryset):
        from django.contrib import messages
        from .services import MixService
        from django.core.exceptions import ValidationError
        count = 0
        errors = []
        for mix in queryset.filter(is_active=False):
            try:
                MixService.restore_mix(mix.id, request.user)
                count += 1
            except ValidationError as e:
                errors.append(f"{mix.name}: {e.message}")
        
        if count:
            self.message_user(request, f"Restored {count} mixes.")
        if errors:
            self.message_user(request, f"Could not restore: {'; '.join(errors)}", level=messages.WARNING)


@admin.register(MixIngredient)
class MixIngredientAdmin(admin.ModelAdmin):
    """Standalone admin for mix ingredients (optional - mainly managed via inline)"""
    list_display = ['mix', 'inventory_item_id', 'get_item_name', 'quantity_required', 'unit_of_measure', 'category']
    list_filter = ['mix__product', 'inventory_item_id']
    search_fields = ['mix__name', 'mix__product__name']
    readonly_fields = ['created_at']
    
    def get_item_name(self, obj):
        return obj.get_inventory_item_name()
    get_item_name.short_description = "Item Name"
    
    def category(self, obj):
        return obj.category
    category.short_description = "Type"
