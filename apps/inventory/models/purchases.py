"""
Inventory App - Concrete ItemXXPurchases Models
23 item-specific Purchases models (immutable ledger per inventory item).

Generated from abstract BaseItemPurchases.
Each table stores the purchase history for ONE specific inventory item.

BANK LEDGER MODEL:
- CREATE ONLY - no updates, no deletes
- Each purchase record is permanent
- Forms complete audit trail of all purchases
"""
from .base import BaseItemPurchases


# ============================================================================
# INGREDIENTS (Items 1-15)
# ============================================================================

class Item01FlourType1Purchases(BaseItemPurchases):
    """Flour Type 1 purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_01_flour_type_1_purchases'
        verbose_name = 'Flour Type 1 Purchase'
        verbose_name_plural = 'Flour Type 1 Purchases'


class Item02FlourType2Purchases(BaseItemPurchases):
    """Flour Type 2 purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_02_flour_type_2_purchases'
        verbose_name = 'Flour Type 2 Purchase'
        verbose_name_plural = 'Flour Type 2 Purchases'


class Item03SugarPurchases(BaseItemPurchases):
    """Sugar purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_03_sugar_purchases'
        verbose_name = 'Sugar Purchase'
        verbose_name_plural = 'Sugar Purchases'


class Item04BreadImproverPurchases(BaseItemPurchases):
    """Bread Improver purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_04_bread_improver_purchases'
        verbose_name = 'Bread Improver Purchase'
        verbose_name_plural = 'Bread Improver Purchases'


class Item05SaltPurchases(BaseItemPurchases):
    """Salt purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_05_salt_purchases'
        verbose_name = 'Salt Purchase'
        verbose_name_plural = 'Salt Purchases'


class Item06CalciumPurchases(BaseItemPurchases):
    """Calcium purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_06_calcium_purchases'
        verbose_name = 'Calcium Purchase'
        verbose_name_plural = 'Calcium Purchases'


class Item07YeastPurchases(BaseItemPurchases):
    """Yeast purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_07_yeast_purchases'
        verbose_name = 'Yeast Purchase'
        verbose_name_plural = 'Yeast Purchases'


class Item08Yeast2In1Purchases(BaseItemPurchases):
    """Yeast 2-in-1 purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_08_yeast_2_in_1_purchases'
        verbose_name = 'Yeast 2-in-1 Purchase'
        verbose_name_plural = 'Yeast 2-in-1 Purchases'


class Item09BakingPowderPurchases(BaseItemPurchases):
    """Baking Powder purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_09_baking_powder_purchases'
        verbose_name = 'Baking Powder Purchase'
        verbose_name_plural = 'Baking Powder Purchases'


class Item10MargarinePurchases(BaseItemPurchases):
    """Margarine purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_10_margarine_purchases'
        verbose_name = 'Margarine Purchase'
        verbose_name_plural = 'Margarine Purchases'


class Item11MilkPurchases(BaseItemPurchases):
    """Milk purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_11_milk_purchases'
        verbose_name = 'Milk Purchase'
        verbose_name_plural = 'Milk Purchases'


class Item12EggsPurchases(BaseItemPurchases):
    """Eggs purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_12_eggs_purchases'
        verbose_name = 'Eggs Purchase'
        verbose_name_plural = 'Eggs Purchases'


class Item13CookingFatPurchases(BaseItemPurchases):
    """Cooking Fat purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_13_cooking_fat_purchases'
        verbose_name = 'Cooking Fat Purchase'
        verbose_name_plural = 'Cooking Fat Purchases'


class Item14CookingOilPurchases(BaseItemPurchases):
    """Cooking Oil purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_14_cooking_oil_purchases'
        verbose_name = 'Cooking Oil Purchase'
        verbose_name_plural = 'Cooking Oil Purchases'


class Item15FoodColourPurchases(BaseItemPurchases):
    """Food Colour purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_15_food_colour_purchases'
        verbose_name = 'Food Colour Purchase'
        verbose_name_plural = 'Food Colour Purchases'


# ============================================================================
# INDIRECT COSTS (Items 16-23)
# ============================================================================

class Item16CratesPurchases(BaseItemPurchases):
    """Crates purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_16_crates_purchases'
        verbose_name = 'Crates Purchase'
        verbose_name_plural = 'Crates Purchases'


class Item17PackagingPurchases(BaseItemPurchases):
    """Packaging purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_17_packaging_purchases'
        verbose_name = 'Packaging Purchase'
        verbose_name_plural = 'Packaging Purchases'


class Item18DieselPurchases(BaseItemPurchases):
    """Diesel purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_18_diesel_purchases'
        verbose_name = 'Diesel Purchase'
        verbose_name_plural = 'Diesel Purchases'


class Item19FirewoodPurchases(BaseItemPurchases):
    """Firewood purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_19_firewood_purchases'
        verbose_name = 'Firewood Purchase'
        verbose_name_plural = 'Firewood Purchases'


class Item20FuelBoleroPurchases(BaseItemPurchases):
    """Fuel Bolero purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_20_fuel_bolero_purchases'
        verbose_name = 'Fuel Bolero Purchase'
        verbose_name_plural = 'Fuel Bolero Purchases'


class Item21ElectricityPurchases(BaseItemPurchases):
    """Electricity purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_21_electricity_purchases'
        verbose_name = 'Electricity Purchase'
        verbose_name_plural = 'Electricity Purchases'


class Item22FuelTransportTrucksPurchases(BaseItemPurchases):
    """Fuel for Transport Trucks purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_22_fuel_transport_trucks_purchases'
        verbose_name = 'Fuel for Transport Trucks Purchase'
        verbose_name_plural = 'Fuel for Transport Trucks Purchases'


class Item23HairNetsPurchases(BaseItemPurchases):
    """Hair Nets purchase records (immutable)"""
    class Meta:
        db_table = 'inventory_item_23_hair_nets_purchases'
        verbose_name = 'Hair Nets Purchase'
        verbose_name_plural = 'Hair Nets Purchases'
