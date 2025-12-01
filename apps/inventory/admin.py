"""
Inventory App - Django Admin Configuration
Registers all 54 item tables + StockAlert for admin interface.

IMPORTANT: Purchases and Outputs are READ-ONLY in admin to enforce immutability.
Only ItemXXDetails tables allow editing (name, minimum_stock_level).
"""
from django.contrib import admin
from django.utils.html import format_html
from decimal import Decimal

from .models import (
    StockAlert,
    # Details models
    Item01FlourType1Details, Item02FlourType2Details, Item03SugarDetails,
    Item04BreadImproverDetails, Item05SaltDetails, Item06CalciumDetails,
    Item07YeastDetails, Item08Yeast2In1Details, Item09BakingPowderDetails,
    Item10MargarineDetails, Item11MilkDetails, Item12EggsDetails,
    Item13CookingFatDetails, Item14CookingOilDetails, Item15FoodColourDetails,
    Item16CratesDetails, Item17PackagingDetails, Item18DieselDetails,
    Item19FirewoodDetails, Item20FuelBoleroDetails, Item21ElectricityDetails,
    Item22FuelTransportTrucksDetails, Item23HairNetsDetails,
    # Purchases models
    Item01FlourType1Purchases, Item02FlourType2Purchases, Item03SugarPurchases,
    Item04BreadImproverPurchases, Item05SaltPurchases, Item06CalciumPurchases,
    Item07YeastPurchases, Item08Yeast2In1Purchases, Item09BakingPowderPurchases,
    Item10MargarinePurchases, Item11MilkPurchases, Item12EggsPurchases,
    Item13CookingFatPurchases, Item14CookingOilPurchases, Item15FoodColourPurchases,
    Item16CratesPurchases, Item17PackagingPurchases, Item18DieselPurchases,
    Item19FirewoodPurchases, Item20FuelBoleroPurchases, Item21ElectricityPurchases,
    Item22FuelTransportTrucksPurchases, Item23HairNetsPurchases,
    # Outputs models (indirect costs only)
    Item16CratesOutputs, Item17PackagingOutputs, Item18DieselOutputs,
    Item19FirewoodOutputs, Item20FuelBoleroOutputs, Item21ElectricityOutputs,
    Item22FuelTransportTrucksOutputs, Item23HairNetsOutputs,
)


# ============================================================================
# BASE ADMIN CLASSES
# ============================================================================

class BaseItemDetailsAdmin(admin.ModelAdmin):
    """
    Base admin for ItemXXDetails models.
    Allows editing name and minimum_stock_level only.
    """
    list_display = [
        'name', 'current_stock_display', 'unit_of_measure',
        'minimum_stock_level', 'last_purchase_unit_price', 'stock_status'
    ]
    list_filter = ['unit_of_measure']
    search_fields = ['name']
    readonly_fields = [
        'current_stock', 'last_purchase_unit_price', 'last_purchase_date',
        'current_value', 'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    fieldsets = [
        ('Item Information', {
            'fields': ['name', 'unit_of_measure']
        }),
        ('Stock Settings', {
            'fields': ['minimum_stock_level']
        }),
        ('Current State (Read-Only)', {
            'fields': [
                'current_stock', 'current_value',
                'last_purchase_unit_price', 'last_purchase_date'
            ],
            'classes': ['collapse']
        }),
        ('Audit (Read-Only)', {
            'fields': ['created_at', 'created_by', 'updated_at', 'updated_by'],
            'classes': ['collapse']
        }),
    ]
    
    def current_stock_display(self, obj):
        return f"{obj.current_stock} {obj.unit_of_measure}"
    current_stock_display.short_description = 'Current Stock'
    
    def stock_status(self, obj):
        if obj.is_out_of_stock:
            return format_html('<span style="color: red; font-weight: bold;">❌ OUT OF STOCK</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange; font-weight: bold;">⚠️ LOW</span>')
        return format_html('<span style="color: green;">✅ OK</span>')
    stock_status.short_description = 'Status'
    
    def has_delete_permission(self, request, obj=None):
        # Cannot delete item details (singleton per item)
        return False
    
    def has_add_permission(self, request):
        # Items are pre-seeded, cannot add new ones
        return False


class BaseItemPurchasesAdmin(admin.ModelAdmin):
    """
    Base admin for ItemXXPurchases models.
    READ-ONLY - purchases are immutable.
    """
    list_display = [
        'purchase_number', 'purchase_date', 'supplier_name',
        'quantity_purchased', 'unit_price', 'total_cost', 'purchased_by'
    ]
    list_filter = ['purchase_date', 'purchased_by']
    search_fields = ['purchase_number', 'supplier_name']
    date_hierarchy = 'purchase_date'
    ordering = ['-purchase_date', '-created_at']
    
    readonly_fields = [
        'purchase_number', 'supplier_name', 'purchase_date',
        'quantity_purchased', 'unit_price', 'total_cost',
        'notes', 'purchased_by', 'created_at'
    ]
    
    def has_add_permission(self, request):
        # Purchases created via utility function, not admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Immutable - no edits
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Immutable - no deletes
        return False


class BaseItemOutputsAdmin(admin.ModelAdmin):
    """
    Base admin for ItemXXOutputs models (indirect costs only).
    READ-ONLY - outputs are immutable.
    """
    list_display = [
        'output_number', 'consumption_date', 'quantity_consumed',
        'date_range_display', 'consumed_by'
    ]
    list_filter = ['consumption_date', 'consumed_by']
    search_fields = ['output_number', 'description']
    date_hierarchy = 'consumption_date'
    ordering = ['-consumption_date', '-created_at']
    
    readonly_fields = [
        'output_number', 'consumption_date', 'quantity_consumed',
        'date_range_start', 'date_range_end', 'description',
        'consumed_by', 'created_at'
    ]
    
    def date_range_display(self, obj):
        if obj.date_range_start and obj.date_range_end:
            return f"{obj.date_range_start} → {obj.date_range_end}"
        return '-'
    date_range_display.short_description = 'Period'
    
    def has_add_permission(self, request):
        # Outputs created via utility function, not admin
        return False
    
    def has_change_permission(self, request, obj=None):
        # Immutable - no edits
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Immutable - no deletes
        return False


# ============================================================================
# STOCK ALERT ADMIN
# ============================================================================

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    """Admin for StockAlert model (shared table, read-only)."""
    list_display = [
        'triggered_at', 'item_name', 'alert_level_display',
        'current_stock', 'minimum_stock', 'triggered_by', 'email_sent'
    ]
    list_filter = ['alert_level', 'triggered_by', 'email_sent', 'triggered_at']
    search_fields = ['item_name', 'message']
    date_hierarchy = 'triggered_at'
    ordering = ['-triggered_at']
    
    readonly_fields = [
        'inventory_item_id', 'item_name', 'alert_level', 'message',
        'current_stock', 'minimum_stock', 'triggered_by', 'triggered_by_user',
        'email_sent', 'email_sent_at', 'triggered_at', 'created_at'
    ]
    
    def alert_level_display(self, obj):
        if obj.alert_level == 'CRITICAL':
            return format_html('<span style="color: red; font-weight: bold;">🔴 CRITICAL</span>')
        return format_html('<span style="color: orange; font-weight: bold;">🟡 WARNING</span>')
    alert_level_display.short_description = 'Level'
    
    def has_add_permission(self, request):
        # Alerts created automatically by utilities
        return False
    
    def has_change_permission(self, request, obj=None):
        # Immutable (except email_sent which is set programmatically)
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Immutable audit trail
        return False


# ============================================================================
# REGISTER DETAILS MODELS (23 items)
# ============================================================================

@admin.register(Item01FlourType1Details)
class Item01FlourType1DetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item02FlourType2Details)
class Item02FlourType2DetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item03SugarDetails)
class Item03SugarDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item04BreadImproverDetails)
class Item04BreadImproverDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item05SaltDetails)
class Item05SaltDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item06CalciumDetails)
class Item06CalciumDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item07YeastDetails)
class Item07YeastDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item08Yeast2In1Details)
class Item08Yeast2In1DetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item09BakingPowderDetails)
class Item09BakingPowderDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item10MargarineDetails)
class Item10MargarineDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item11MilkDetails)
class Item11MilkDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item12EggsDetails)
class Item12EggsDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item13CookingFatDetails)
class Item13CookingFatDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item14CookingOilDetails)
class Item14CookingOilDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item15FoodColourDetails)
class Item15FoodColourDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item16CratesDetails)
class Item16CratesDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item17PackagingDetails)
class Item17PackagingDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item18DieselDetails)
class Item18DieselDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item19FirewoodDetails)
class Item19FirewoodDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item20FuelBoleroDetails)
class Item20FuelBoleroDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item21ElectricityDetails)
class Item21ElectricityDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item22FuelTransportTrucksDetails)
class Item22FuelTransportTrucksDetailsAdmin(BaseItemDetailsAdmin):
    pass

@admin.register(Item23HairNetsDetails)
class Item23HairNetsDetailsAdmin(BaseItemDetailsAdmin):
    pass


# ============================================================================
# REGISTER PURCHASES MODELS (23 items)
# ============================================================================

@admin.register(Item01FlourType1Purchases)
class Item01FlourType1PurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item02FlourType2Purchases)
class Item02FlourType2PurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item03SugarPurchases)
class Item03SugarPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item04BreadImproverPurchases)
class Item04BreadImproverPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item05SaltPurchases)
class Item05SaltPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item06CalciumPurchases)
class Item06CalciumPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item07YeastPurchases)
class Item07YeastPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item08Yeast2In1Purchases)
class Item08Yeast2In1PurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item09BakingPowderPurchases)
class Item09BakingPowderPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item10MargarinePurchases)
class Item10MargarinePurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item11MilkPurchases)
class Item11MilkPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item12EggsPurchases)
class Item12EggsPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item13CookingFatPurchases)
class Item13CookingFatPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item14CookingOilPurchases)
class Item14CookingOilPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item15FoodColourPurchases)
class Item15FoodColourPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item16CratesPurchases)
class Item16CratesPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item17PackagingPurchases)
class Item17PackagingPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item18DieselPurchases)
class Item18DieselPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item19FirewoodPurchases)
class Item19FirewoodPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item20FuelBoleroPurchases)
class Item20FuelBoleroPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item21ElectricityPurchases)
class Item21ElectricityPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item22FuelTransportTrucksPurchases)
class Item22FuelTransportTrucksPurchasesAdmin(BaseItemPurchasesAdmin):
    pass

@admin.register(Item23HairNetsPurchases)
class Item23HairNetsPurchasesAdmin(BaseItemPurchasesAdmin):
    pass


# ============================================================================
# REGISTER OUTPUTS MODELS (8 indirect cost items only)
# ============================================================================

@admin.register(Item16CratesOutputs)
class Item16CratesOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item17PackagingOutputs)
class Item17PackagingOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item18DieselOutputs)
class Item18DieselOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item19FirewoodOutputs)
class Item19FirewoodOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item20FuelBoleroOutputs)
class Item20FuelBoleroOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item21ElectricityOutputs)
class Item21ElectricityOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item22FuelTransportTrucksOutputs)
class Item22FuelTransportTrucksOutputsAdmin(BaseItemOutputsAdmin):
    pass

@admin.register(Item23HairNetsOutputs)
class Item23HairNetsOutputsAdmin(BaseItemOutputsAdmin):
    pass
