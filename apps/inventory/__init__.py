"""
Inventory App
Per-item physical table architecture for financial-grade data integrity.

54 tables total:
- 23 ItemXXDetails tables (singleton per item)
- 23 ItemXXPurchases tables (immutable ledger)
- 8 ItemXXOutputs tables (indirect costs only)
- 1 StockAlert shared table

Models: apps.inventory.models
Routing: apps.inventory.routing
Utilities: apps.inventory.utils
"""
default_app_config = 'apps.inventory.apps.InventoryConfig'
