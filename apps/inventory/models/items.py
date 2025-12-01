"""
Inventory App - Concrete ItemXXDetails Models
23 item-specific Details models (one singleton table per inventory item).

Generated from abstract BaseItemDetails.
Each table stores the current stock state for ONE specific inventory item.

INGREDIENTS (Items 1-15): NO outputs table - tracked via Production app
INDIRECT COSTS (Items 16-23): HAS outputs table - manual consumption tracking
"""
from .base import BaseItemDetails


# ============================================================================
# INGREDIENTS (Items 1-15) - Tracked via Production app, no outputs table
# ============================================================================

class Item01FlourType1Details(BaseItemDetails):
    """Flour Type 1 (Bakers Flour) - Primary bread flour"""
    class Meta:
        db_table = 'inventory_item_01_flour_type_1_details'
        verbose_name = 'Flour Type 1'
        verbose_name_plural = 'Flour Type 1'


class Item02FlourType2Details(BaseItemDetails):
    """Flour Type 2 (Alternative Flour) - Secondary flour"""
    class Meta:
        db_table = 'inventory_item_02_flour_type_2_details'
        verbose_name = 'Flour Type 2'
        verbose_name_plural = 'Flour Type 2'


class Item03SugarDetails(BaseItemDetails):
    """Sugar - Sweetener for baked goods"""
    class Meta:
        db_table = 'inventory_item_03_sugar_details'
        verbose_name = 'Sugar'
        verbose_name_plural = 'Sugar'


class Item04BreadImproverDetails(BaseItemDetails):
    """Bread Improver - Enhances bread texture and rise"""
    class Meta:
        db_table = 'inventory_item_04_bread_improver_details'
        verbose_name = 'Bread Improver'
        verbose_name_plural = 'Bread Improver'


class Item05SaltDetails(BaseItemDetails):
    """Salt - Flavor enhancer and dough strengthener"""
    class Meta:
        db_table = 'inventory_item_05_salt_details'
        verbose_name = 'Salt'
        verbose_name_plural = 'Salt'


class Item06CalciumDetails(BaseItemDetails):
    """Calcium - Nutritional additive"""
    class Meta:
        db_table = 'inventory_item_06_calcium_details'
        verbose_name = 'Calcium'
        verbose_name_plural = 'Calcium'


class Item07YeastDetails(BaseItemDetails):
    """Yeast - Primary leavening agent"""
    class Meta:
        db_table = 'inventory_item_07_yeast_details'
        verbose_name = 'Yeast'
        verbose_name_plural = 'Yeast'


class Item08Yeast2In1Details(BaseItemDetails):
    """Yeast 2-in-1 - Combined yeast product"""
    class Meta:
        db_table = 'inventory_item_08_yeast_2_in_1_details'
        verbose_name = 'Yeast 2-in-1'
        verbose_name_plural = 'Yeast 2-in-1'


class Item09BakingPowderDetails(BaseItemDetails):
    """Baking Powder - Chemical leavening agent"""
    class Meta:
        db_table = 'inventory_item_09_baking_powder_details'
        verbose_name = 'Baking Powder'
        verbose_name_plural = 'Baking Powder'


class Item10MargarineDetails(BaseItemDetails):
    """Margarine - Fat for enriched doughs"""
    class Meta:
        db_table = 'inventory_item_10_margarine_details'
        verbose_name = 'Margarine'
        verbose_name_plural = 'Margarine'


class Item11MilkDetails(BaseItemDetails):
    """Milk - Liquid enrichment"""
    class Meta:
        db_table = 'inventory_item_11_milk_details'
        verbose_name = 'Milk'
        verbose_name_plural = 'Milk'


class Item12EggsDetails(BaseItemDetails):
    """Eggs - Binding and enrichment"""
    class Meta:
        db_table = 'inventory_item_12_eggs_details'
        verbose_name = 'Eggs'
        verbose_name_plural = 'Eggs'


class Item13CookingFatDetails(BaseItemDetails):
    """Cooking Fat - Solid fat for frying"""
    class Meta:
        db_table = 'inventory_item_13_cooking_fat_details'
        verbose_name = 'Cooking Fat'
        verbose_name_plural = 'Cooking Fat'


class Item14CookingOilDetails(BaseItemDetails):
    """Cooking Oil - Liquid fat for frying"""
    class Meta:
        db_table = 'inventory_item_14_cooking_oil_details'
        verbose_name = 'Cooking Oil'
        verbose_name_plural = 'Cooking Oil'


class Item15FoodColourDetails(BaseItemDetails):
    """Food Colour - Coloring for specialty products"""
    class Meta:
        db_table = 'inventory_item_15_food_colour_details'
        verbose_name = 'Food Colour'
        verbose_name_plural = 'Food Colour'


# ============================================================================
# INDIRECT COSTS (Items 16-23) - Has outputs table for manual consumption
# ============================================================================

class Item16CratesDetails(BaseItemDetails):
    """Crates - Delivery containers (tracked via Sales)"""
    class Meta:
        db_table = 'inventory_item_16_crates_details'
        verbose_name = 'Crates'
        verbose_name_plural = 'Crates'


class Item17PackagingDetails(BaseItemDetails):
    """Packaging - Bags, wrappers, labels"""
    class Meta:
        db_table = 'inventory_item_17_packaging_details'
        verbose_name = 'Packaging'
        verbose_name_plural = 'Packaging'


class Item18DieselDetails(BaseItemDetails):
    """Diesel - Generator/equipment fuel"""
    class Meta:
        db_table = 'inventory_item_18_diesel_details'
        verbose_name = 'Diesel'
        verbose_name_plural = 'Diesel'


class Item19FirewoodDetails(BaseItemDetails):
    """Firewood - Traditional oven fuel"""
    class Meta:
        db_table = 'inventory_item_19_firewood_details'
        verbose_name = 'Firewood'
        verbose_name_plural = 'Firewood'


class Item20FuelBoleroDetails(BaseItemDetails):
    """Fuel Bolero - Delivery vehicle fuel"""
    class Meta:
        db_table = 'inventory_item_20_fuel_bolero_details'
        verbose_name = 'Fuel Bolero'
        verbose_name_plural = 'Fuel Bolero'


class Item21ElectricityDetails(BaseItemDetails):
    """Electricity - Power tokens/units"""
    class Meta:
        db_table = 'inventory_item_21_electricity_details'
        verbose_name = 'Electricity'
        verbose_name_plural = 'Electricity'


class Item22FuelTransportTrucksDetails(BaseItemDetails):
    """Fuel for Transport Trucks - Fleet fuel"""
    class Meta:
        db_table = 'inventory_item_22_fuel_transport_trucks_details'
        verbose_name = 'Fuel for Transport Trucks'
        verbose_name_plural = 'Fuel for Transport Trucks'


class Item23HairNetsDetails(BaseItemDetails):
    """Hair Nets - Hygiene supplies"""
    class Meta:
        db_table = 'inventory_item_23_hair_nets_details'
        verbose_name = 'Hair Nets'
        verbose_name_plural = 'Hair Nets'
