"""
Production App - Batch Recording and Finished Goods Stock Management

This app handles:
- Recording production batches (immutable, CREATE-ONLY)
- Deducting ingredients from inventory (via Inventory utilities)
- Tracking finished product stock (available for Sales)
- Calculating batch costs (snapshotting ingredient prices at production time)

CRITICAL: ProductionBatch records are IMMUTABLE (bank ledger philosophy).
"""

default_app_config = 'apps.production.apps.ProductionConfig'
