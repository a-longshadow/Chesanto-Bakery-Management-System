"""
Inventory App Models
Per-item physical table architecture for financial-grade data integrity.

This module exports:
- Abstract base classes for model definitions
- All 23 item-specific Details models
- All 23 item-specific Purchases models  
- All 8 item-specific Outputs models (indirect costs only)
- StockAlert shared model
- Routing utilities for model lookup
"""

# Abstract base classes
from .base import BaseItemDetails, BaseItemPurchases, BaseItemOutputs

# Shared model
from .alerts import StockAlert

# Concrete Details models (23 items)
from .items import (
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

# Concrete Purchases models (23 items)
from .purchases import (
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

# Concrete Outputs models (8 indirect cost items only)
from .outputs import (
    Item16CratesOutputs,
    Item17PackagingOutputs,
    Item18DieselOutputs,
    Item19FirewoodOutputs,
    Item20FuelBoleroOutputs,
    Item21ElectricityOutputs,
    Item22FuelTransportTrucksOutputs,
    Item23HairNetsOutputs,
)

# All models list for Django registration
__all__ = [
    # Base classes
    'BaseItemDetails',
    'BaseItemPurchases', 
    'BaseItemOutputs',
    # Shared
    'StockAlert',
    # Details (23)
    'Item01FlourType1Details',
    'Item02FlourType2Details',
    'Item03SugarDetails',
    'Item04BreadImproverDetails',
    'Item05SaltDetails',
    'Item06CalciumDetails',
    'Item07YeastDetails',
    'Item08Yeast2In1Details',
    'Item09BakingPowderDetails',
    'Item10MargarineDetails',
    'Item11MilkDetails',
    'Item12EggsDetails',
    'Item13CookingFatDetails',
    'Item14CookingOilDetails',
    'Item15FoodColourDetails',
    'Item16CratesDetails',
    'Item17PackagingDetails',
    'Item18DieselDetails',
    'Item19FirewoodDetails',
    'Item20FuelBoleroDetails',
    'Item21ElectricityDetails',
    'Item22FuelTransportTrucksDetails',
    'Item23HairNetsDetails',
    # Purchases (23)
    'Item01FlourType1Purchases',
    'Item02FlourType2Purchases',
    'Item03SugarPurchases',
    'Item04BreadImproverPurchases',
    'Item05SaltPurchases',
    'Item06CalciumPurchases',
    'Item07YeastPurchases',
    'Item08Yeast2In1Purchases',
    'Item09BakingPowderPurchases',
    'Item10MargarinePurchases',
    'Item11MilkPurchases',
    'Item12EggsPurchases',
    'Item13CookingFatPurchases',
    'Item14CookingOilPurchases',
    'Item15FoodColourPurchases',
    'Item16CratesPurchases',
    'Item17PackagingPurchases',
    'Item18DieselPurchases',
    'Item19FirewoodPurchases',
    'Item20FuelBoleroPurchases',
    'Item21ElectricityPurchases',
    'Item22FuelTransportTrucksPurchases',
    'Item23HairNetsPurchases',
    # Outputs (8 indirect costs only)
    'Item16CratesOutputs',
    'Item17PackagingOutputs',
    'Item18DieselOutputs',
    'Item19FirewoodOutputs',
    'Item20FuelBoleroOutputs',
    'Item21ElectricityOutputs',
    'Item22FuelTransportTrucksOutputs',
    'Item23HairNetsOutputs',
]
