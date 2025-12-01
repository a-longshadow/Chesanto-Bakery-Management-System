"""
Inventory App - Concrete ItemXXOutputs Models
8 item-specific Outputs models (INDIRECT COSTS ONLY - items 16-23).

Generated from abstract BaseItemOutputs.
Each table stores the manual consumption history for ONE specific indirect cost item.

BANK LEDGER MODEL:
- CREATE ONLY - no updates, no deletes
- Each output record is permanent
- Forms complete audit trail of all consumption

NOTE: Ingredients (items 1-15) do NOT have outputs tables.
Ingredient consumption is tracked via Production app batches.
"""
from .base import BaseItemOutputs


# ============================================================================
# INDIRECT COSTS ONLY (Items 16-23)
# These are the ONLY items with outputs tables
# ============================================================================

class Item16CratesOutputs(BaseItemOutputs):
    """Crates consumption records (immutable)
    
    Typically auto-deducted via Sales dispatch, but can also be
    manually recorded for losses, damages, etc.
    """
    class Meta:
        db_table = 'inventory_item_16_crates_outputs'
        verbose_name = 'Crates Output'
        verbose_name_plural = 'Crates Outputs'


class Item17PackagingOutputs(BaseItemOutputs):
    """Packaging consumption records (immutable)
    
    Bags, wrappers, labels used in production.
    """
    class Meta:
        db_table = 'inventory_item_17_packaging_outputs'
        verbose_name = 'Packaging Output'
        verbose_name_plural = 'Packaging Outputs'


class Item18DieselOutputs(BaseItemOutputs):
    """Diesel consumption records (immutable)
    
    Generator and equipment fuel usage.
    """
    class Meta:
        db_table = 'inventory_item_18_diesel_outputs'
        verbose_name = 'Diesel Output'
        verbose_name_plural = 'Diesel Outputs'


class Item19FirewoodOutputs(BaseItemOutputs):
    """Firewood consumption records (immutable)
    
    Traditional oven fuel usage.
    """
    class Meta:
        db_table = 'inventory_item_19_firewood_outputs'
        verbose_name = 'Firewood Output'
        verbose_name_plural = 'Firewood Outputs'


class Item20FuelBoleroOutputs(BaseItemOutputs):
    """Fuel Bolero consumption records (immutable)
    
    Delivery vehicle (Bolero) fuel usage.
    """
    class Meta:
        db_table = 'inventory_item_20_fuel_bolero_outputs'
        verbose_name = 'Fuel Bolero Output'
        verbose_name_plural = 'Fuel Bolero Outputs'


class Item21ElectricityOutputs(BaseItemOutputs):
    """Electricity consumption records (immutable)
    
    Power tokens/units usage tracking.
    """
    class Meta:
        db_table = 'inventory_item_21_electricity_outputs'
        verbose_name = 'Electricity Output'
        verbose_name_plural = 'Electricity Outputs'


class Item22FuelTransportTrucksOutputs(BaseItemOutputs):
    """Fuel for Transport Trucks consumption records (immutable)
    
    Fleet/delivery trucks fuel usage.
    """
    class Meta:
        db_table = 'inventory_item_22_fuel_transport_trucks_outputs'
        verbose_name = 'Fuel for Transport Trucks Output'
        verbose_name_plural = 'Fuel for Transport Trucks Outputs'


class Item23HairNetsOutputs(BaseItemOutputs):
    """Hair Nets consumption records (immutable)
    
    Hygiene supplies usage tracking.
    """
    class Meta:
        db_table = 'inventory_item_23_hair_nets_outputs'
        verbose_name = 'Hair Nets Output'
        verbose_name_plural = 'Hair Nets Outputs'
