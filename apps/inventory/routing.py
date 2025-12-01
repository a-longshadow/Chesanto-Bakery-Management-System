"""
Inventory App - Model Routing System
Central registry for per-item model lookup.

This module provides:
- INVENTORY_ITEMS: Master list of all 23 inventory items with metadata
- ITEM_DETAILS_MODELS: Mapping inventory_item_id → Details model class
- ITEM_PURCHASES_MODELS: Mapping inventory_item_id → Purchases model class
- ITEM_OUTPUTS_MODELS: Mapping inventory_item_id → Outputs model class (indirect costs only)
- Helper functions for model lookup and item classification

USAGE:
    from apps.inventory.routing import get_details_model, get_purchases_model, is_ingredient
    
    # Get the correct model for item ID 1 (Flour Type 1)
    FlourDetails = get_details_model(1)
    flour = FlourDetails.objects.get(id=1)
    
    # Check if item is ingredient or indirect cost
    if is_ingredient(1):
        print("This is deducted by Production app")
"""
from .models.items import (
    Item01FlourType1Details,
    Item02FlourType2Details,
    Item03SugarDetails,
    Item04BreadImproverDetails,
    Item05SaltDetails,
    Item06CalciumDetails,
    Item07YeastDetails,
    Item08Yeast2In1Details,
    Item09BakingPowderDetails,
    Item10MargarineDetails,
    Item11MilkDetails,
    Item12EggsDetails,
    Item13CookingFatDetails,
    Item14CookingOilDetails,
    Item15FoodColourDetails,
    Item16CratesDetails,
    Item17PackagingDetails,
    Item18DieselDetails,
    Item19FirewoodDetails,
    Item20FuelBoleroDetails,
    Item21ElectricityDetails,
    Item22FuelTransportTrucksDetails,
    Item23HairNetsDetails,
)

from .models.purchases import (
    Item01FlourType1Purchases,
    Item02FlourType2Purchases,
    Item03SugarPurchases,
    Item04BreadImproverPurchases,
    Item05SaltPurchases,
    Item06CalciumPurchases,
    Item07YeastPurchases,
    Item08Yeast2In1Purchases,
    Item09BakingPowderPurchases,
    Item10MargarinePurchases,
    Item11MilkPurchases,
    Item12EggsPurchases,
    Item13CookingFatPurchases,
    Item14CookingOilPurchases,
    Item15FoodColourPurchases,
    Item16CratesPurchases,
    Item17PackagingPurchases,
    Item18DieselPurchases,
    Item19FirewoodPurchases,
    Item20FuelBoleroPurchases,
    Item21ElectricityPurchases,
    Item22FuelTransportTrucksPurchases,
    Item23HairNetsPurchases,
)

from .models.outputs import (
    Item16CratesOutputs,
    Item17PackagingOutputs,
    Item18DieselOutputs,
    Item19FirewoodOutputs,
    Item20FuelBoleroOutputs,
    Item21ElectricityOutputs,
    Item22FuelTransportTrucksOutputs,
    Item23HairNetsOutputs,
)


# ============================================================================
# MASTER ITEM LIST
# (inventory_item_id, name, is_ingredient, unit_of_measure)
# ============================================================================

INVENTORY_ITEMS = [
    # INGREDIENTS (1-15) - Deducted by Production app, NO outputs table
    (1, 'Flour Type 1', True, 'kg'),
    (2, 'Flour Type 2', True, 'kg'),
    (3, 'Sugar', True, 'kg'),
    (4, 'Bread Improver', True, 'kg'),
    (5, 'Salt', True, 'kg'),
    (6, 'Calcium', True, 'kg'),
    (7, 'Yeast', True, 'kg'),
    (8, 'Yeast 2-in-1', True, 'kg'),
    (9, 'Baking Powder', True, 'kg'),
    (10, 'Margarine', True, 'kg'),
    (11, 'Milk', True, 'L'),
    (12, 'Eggs', True, 'units'),
    (13, 'Cooking Fat', True, 'kg'),
    (14, 'Cooking Oil', True, 'L'),
    (15, 'Food Colour', True, 'kg'),
    # INDIRECT COSTS (16-23) - Manual consumption tracking, HAS outputs table
    (16, 'Crates', False, 'units'),
    (17, 'Packaging', False, 'units'),
    (18, 'Diesel', False, 'L'),
    (19, 'Firewood', False, 'units'),
    (20, 'Fuel Bolero', False, 'units'),
    (21, 'Electricity', False, 'tokens'),
    (22, 'Fuel for Transport Trucks', False, 'L'),
    (23, 'Hair Nets', False, 'units'),
]


# ============================================================================
# MODEL ROUTING DICTIONARIES
# ============================================================================

ITEM_DETAILS_MODELS = {
    1: Item01FlourType1Details,
    2: Item02FlourType2Details,
    3: Item03SugarDetails,
    4: Item04BreadImproverDetails,
    5: Item05SaltDetails,
    6: Item06CalciumDetails,
    7: Item07YeastDetails,
    8: Item08Yeast2In1Details,
    9: Item09BakingPowderDetails,
    10: Item10MargarineDetails,
    11: Item11MilkDetails,
    12: Item12EggsDetails,
    13: Item13CookingFatDetails,
    14: Item14CookingOilDetails,
    15: Item15FoodColourDetails,
    16: Item16CratesDetails,
    17: Item17PackagingDetails,
    18: Item18DieselDetails,
    19: Item19FirewoodDetails,
    20: Item20FuelBoleroDetails,
    21: Item21ElectricityDetails,
    22: Item22FuelTransportTrucksDetails,
    23: Item23HairNetsDetails,
}

ITEM_PURCHASES_MODELS = {
    1: Item01FlourType1Purchases,
    2: Item02FlourType2Purchases,
    3: Item03SugarPurchases,
    4: Item04BreadImproverPurchases,
    5: Item05SaltPurchases,
    6: Item06CalciumPurchases,
    7: Item07YeastPurchases,
    8: Item08Yeast2In1Purchases,
    9: Item09BakingPowderPurchases,
    10: Item10MargarinePurchases,
    11: Item11MilkPurchases,
    12: Item12EggsPurchases,
    13: Item13CookingFatPurchases,
    14: Item14CookingOilPurchases,
    15: Item15FoodColourPurchases,
    16: Item16CratesPurchases,
    17: Item17PackagingPurchases,
    18: Item18DieselPurchases,
    19: Item19FirewoodPurchases,
    20: Item20FuelBoleroPurchases,
    21: Item21ElectricityPurchases,
    22: Item22FuelTransportTrucksPurchases,
    23: Item23HairNetsPurchases,
}

# Only indirect costs (items 16-23) have outputs tables
ITEM_OUTPUTS_MODELS = {
    16: Item16CratesOutputs,
    17: Item17PackagingOutputs,
    18: Item18DieselOutputs,
    19: Item19FirewoodOutputs,
    20: Item20FuelBoleroOutputs,
    21: Item21ElectricityOutputs,
    22: Item22FuelTransportTrucksOutputs,
    23: Item23HairNetsOutputs,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_details_model(inventory_item_id: int):
    """
    Get the Details model class for an inventory item.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        Model class (e.g., Item01FlourType1Details)
        
    Raises:
        ValueError: If inventory_item_id is not valid
    """
    if inventory_item_id not in ITEM_DETAILS_MODELS:
        raise ValueError(f"Unknown inventory item ID: {inventory_item_id}. "
                        f"Valid IDs are 1-23.")
    return ITEM_DETAILS_MODELS[inventory_item_id]


def get_purchases_model(inventory_item_id: int):
    """
    Get the Purchases model class for an inventory item.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        Model class (e.g., Item01FlourType1Purchases)
        
    Raises:
        ValueError: If inventory_item_id is not valid
    """
    if inventory_item_id not in ITEM_PURCHASES_MODELS:
        raise ValueError(f"Unknown inventory item ID: {inventory_item_id}. "
                        f"Valid IDs are 1-23.")
    return ITEM_PURCHASES_MODELS[inventory_item_id]


def get_outputs_model(inventory_item_id: int):
    """
    Get the Outputs model class for an indirect cost item.
    
    Args:
        inventory_item_id: Integer 16-23 (indirect costs only)
        
    Returns:
        Model class (e.g., Item16CratesOutputs)
        
    Raises:
        ValueError: If inventory_item_id is not an indirect cost item
    """
    if inventory_item_id not in ITEM_OUTPUTS_MODELS:
        raise ValueError(f"Item {inventory_item_id} is not an indirect cost item. "
                        f"Only items 16-23 have outputs tables.")
    return ITEM_OUTPUTS_MODELS[inventory_item_id]


def is_indirect_cost(inventory_item_id: int) -> bool:
    """
    Check if item is an indirect cost (has outputs table).
    
    Indirect costs (items 16-23) require manual consumption tracking.
    They have outputs tables for recording usage.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        True if item is indirect cost (16-23), False otherwise
    """
    return inventory_item_id in ITEM_OUTPUTS_MODELS


def is_ingredient(inventory_item_id: int) -> bool:
    """
    Check if item is an ingredient (NO outputs table).
    
    Ingredients (items 1-15) are deducted automatically by Production app.
    They do NOT have outputs tables.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        True if item is ingredient (1-15), False otherwise
    """
    return inventory_item_id not in ITEM_OUTPUTS_MODELS


def get_item_info(inventory_item_id: int) -> tuple:
    """
    Get item metadata (id, name, is_ingredient, unit).
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        Tuple: (id, name, is_ingredient, unit)
        
    Raises:
        ValueError: If inventory_item_id is not valid
    """
    for item in INVENTORY_ITEMS:
        if item[0] == inventory_item_id:
            return item
    raise ValueError(f"Unknown inventory item ID: {inventory_item_id}. "
                    f"Valid IDs are 1-23.")


def get_item_name(inventory_item_id: int) -> str:
    """
    Get item display name by ID.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        String: Item name (e.g., "Flour Type 1")
    """
    return get_item_info(inventory_item_id)[1]


def get_item_unit(inventory_item_id: int) -> str:
    """
    Get item unit of measure by ID.
    
    Args:
        inventory_item_id: Integer 1-23
        
    Returns:
        String: Unit (e.g., "kg", "L", "units")
    """
    return get_item_info(inventory_item_id)[3]


def get_all_ingredient_ids() -> list:
    """
    Get list of all ingredient item IDs (1-15).
    
    Returns:
        List of integers: [1, 2, 3, ..., 15]
    """
    return [item[0] for item in INVENTORY_ITEMS if item[2]]  # item[2] = is_ingredient


def get_all_indirect_cost_ids() -> list:
    """
    Get list of all indirect cost item IDs (16-23).
    
    Returns:
        List of integers: [16, 17, 18, ..., 23]
    """
    return [item[0] for item in INVENTORY_ITEMS if not item[2]]  # item[2] = is_ingredient


def get_items_for_dropdown(include_ingredients=True, include_indirect_costs=True) -> list:
    """
    Get items formatted for dropdown selection.
    
    Args:
        include_ingredients: Include items 1-15
        include_indirect_costs: Include items 16-23
        
    Returns:
        List of tuples: [(id, "Name (unit)"), ...]
    """
    items = []
    for item_id, name, is_ing, unit in INVENTORY_ITEMS:
        if is_ing and not include_ingredients:
            continue
        if not is_ing and not include_indirect_costs:
            continue
        items.append((item_id, f"{name} ({unit})"))
    return items
