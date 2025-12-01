# 🏭 PRODUCTION APP - WORKFLOWS & INTERACTIONS

> **Complete Technical Specification for Production Batch Management**

**Document Version:** 1.0  
**Last Updated:** November 29, 2025  
**Status:** Technical Specification (Ready for Implementation)

---

## 📋 TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Core Responsibilities](#2-core-responsibilities)
3. [Data Models](#3-data-models)
4. [Architecture Decisions](#4-architecture-decisions)
5. [Workflow Reference](#5-workflow-reference)
6. [Cross-App Integration](#6-cross-app-integration)
7. [Service Layer](#7-service-layer)
8. [User Flows (Frontend)](#8-user-flows-frontend)
9. [Views, Admin & Utilities Summary](#9-views-admin--utilities-summary)
10. [Key Principles](#10-key-principles)
11. [Validation Rules](#11-validation-rules)
12. [Decimal Precision & Rounding](#12-decimal-precision--rounding)
13. [Testing](#13-testing)
14. [Implementation Checklist](#14-implementation-checklist)

---

## 1. OVERVIEW

### What is the Production App?

The **Production App** is the **batch recording and finished goods tracking system** for Chesanto Bakery. It handles:
- **Recording** production batches (what was made, when, by whom)
- **Deducting** ingredients from inventory (via Inventory utilities)
- **Tracking** finished product stock (available for Sales)
- **Calculating** batch costs (snapshotting ingredient prices at production time)

### Why Production App Matters

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDATION APPS LAYER                        │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│   INVENTORY     │    PRODUCTS     │   PRODUCTION    │   SALES   │
│   (23 items)    │  (Catalog/Mix)  │   (Batches)     │  (Orders) │
│                 │                 │                 │           │
│  Raw materials  │  What to make   │  ★ Making it ★  │  Selling  │
│  Ingredients    │  Recipes/yields │  Stock tracking │  Revenue  │
└────────┬────────┴────────┬────────┴────────┬────────┴─────┬─────┘
         │                 │                 │              │
         └─────────────────┴─────────────────┴──────────────┘
                    Data flows LEFT → RIGHT
```

### Core Principle: CREATE-ONLY Immutable Records

Production batches follow **bank ledger philosophy**:
- **CREATE ONLY** - No edits, no deletes (immutable audit trail)
- **Atomic** - Batch either fully succeeds or fully rolls back
- **Snapshot** - Mix data frozen at batch creation time
- **Cost locked** - Uses `last_purchase_unit_price` from Inventory at batch time

### Production Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION BATCH FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ PRODUCTS │───▶│  PRODUCTION  │───▶│     INVENTORY       │   │
│  │   App    │    │     App      │    │       App           │   │
│  │          │    │              │    │                     │   │
│  │ Mix data │    │ Record batch │    │ Deduct ingredients  │   │
│  │ (recipe) │    │ Snapshot mix │    │ Update stock        │   │
│  │          │    │ Calc costs   │    │ Trigger alerts      │   │
│  └──────────┘    └──────┬───────┘    └─────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│                  ┌──────────────┐                               │
│                  │ ProductStock │                               │
│                  │ (Available   │                               │
│                  │  for Sales)  │                               │
│                  └──────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. CORE RESPONSIBILITIES

### Production App DOES:

| Responsibility | Description |
|---------------|-------------|
| **Record Production Batches** | Immutable record of each mix produced |
| **Snapshot Mix Data** | Freeze recipe at batch creation (JSONField) |
| **Deduct Ingredients** | Call Inventory's `deduct_ingredients_atomic()` |
| **Track Actual Yield** | Record actual quantity produced per batch |
| **Calculate Batch Costs** | Sum of (ingredient_qty × last_purchase_unit_price) |
| **Manage Product Stock** | Track finished goods available for dispatch |
| **Record Ingredient Deductions** | Audit trail via BatchIngredientDeduction |

### Production App DOES NOT:

| Not Responsible For | Handled By |
|--------------------|------------|
| Define products/mixes | Products App |
| Track raw material levels | Inventory App |
| Create stock alerts | Inventory App (inside utilities) |
| Handle sales/dispatch | Sales App |
| Track leftovers | Sales App (after dispatch returns) |
| Manage ingredient prices | Inventory App (purchases) |

### Key Distinction: Production vs Sales Leftovers

**Production records quality output:**
- Batch produces 132 units of Bread (quality product)
- This is the actual yield from the mix

**Sales handles leftovers:**
- Dispatch sends 132 Bread to market
- Returns: 10 Bread come back unsold
- Some are repackaged as "Bread Leftovers" (sub-product)
- This is a SALES workflow, not Production

---

## 3. DATA MODELS

### 3.1 ProductionBatch Model

**Purpose:** Immutable record of a single production batch

```python
# apps/production/models.py

from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.products.models import Product, Mix


class ProductionBatch(TimeStampedModel):
    """
    Immutable production batch record.
    
    CRITICAL: CREATE-ONLY - No updates, no deletes.
    Each batch is a permanent audit record.
    
    The mix_snapshot stores the complete recipe at batch creation time,
    ensuring historical accuracy even if the Mix is later modified.
    """
    
    # === BATCH IDENTIFICATION ===
    batch_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Format: PRD-YYYYMMDD-XXX (e.g., PRD-20251129-001)"
    )
    
    # === PRODUCT REFERENCE ===
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # Cannot delete product with batches
        related_name='production_batches',
        help_text="The product being produced"
    )
    
    # === MIX REFERENCE (for lookup only) ===
    mix = models.ForeignKey(
        Mix,
        on_delete=models.PROTECT,  # Cannot delete mix with batches
        related_name='production_batches',
        help_text="Reference to the mix used (recipe frozen in mix_snapshot)"
    )
    
    # === SNAPSHOTTED MIX DATA ===
    mix_snapshot = models.JSONField(
        help_text="""
        Complete mix data frozen at batch creation time.
        Structure:
        {
            "mix_id": 1,
            "mix_name": "Bread Mix 1",
            "expected_yield": 132,
            "ingredients": [
                {
                    "inventory_item_id": 1,
                    "item_name": "Bakers Flour",
                    "quantity_required": "36.000",
                    "unit": "kg",
                    "unit_price_at_batch": "85.50",
                    "line_cost": "3078.00"
                },
                ...
            ],
            "total_mix_cost": "12500.00"
        }
        """
    )
    
    # === PRODUCTION QUANTITIES ===
    quantity_produced = models.PositiveIntegerField(
        help_text="Actual units produced (e.g., 132 loaves)"
    )
    
    expected_yield = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Expected yield from mix (snapshot from mix at batch time)"
    )
    
    # === CALCULATED COSTS (at batch time) ===
    total_ingredient_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Sum of all ingredient costs at batch time"
    )
    
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="total_ingredient_cost / quantity_produced"
    )
    
    # === PRODUCTION METADATA ===
    production_date = models.DateField(
        db_index=True,
        help_text="Date of production"
    )
    
    production_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Approximate time batch was completed"
    )
    
    produced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='produced_batches',
        help_text="User who recorded this batch"
    )
    
    # === NOTES ===
    notes = models.TextField(
        blank=True,
        help_text="Optional production notes (quality observations, issues, etc.)"
    )
    
    class Meta:
        db_table = 'production_batches'
        ordering = ['-production_date', '-created_at']
        indexes = [
            models.Index(fields=['production_date', 'product']),
            models.Index(fields=['batch_number']),
        ]
        verbose_name = 'Production Batch'
        verbose_name_plural = 'Production Batches'
    
    def __str__(self):
        return f"{self.batch_number} - {self.product.name} ({self.quantity_produced} units)"
    
    def save(self, *args, **kwargs):
        """
        Override save to enforce CREATE-ONLY behavior.
        """
        if self.pk:
            raise ValueError(
                "ProductionBatch records are immutable. "
                "Cannot update existing batch. Create a new batch instead."
            )
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        Prevent deletion of production batches.
        """
        raise ValueError(
            "ProductionBatch records cannot be deleted. "
            "They are permanent audit records."
        )
    
    # === COMPUTED PROPERTIES ===
    
    @property
    def yield_variance(self) -> int:
        """
        Difference between actual and expected yield.
        Positive = over-production, Negative = under-production.
        """
        return self.quantity_produced - self.expected_yield
    
    @property
    def yield_variance_percentage(self) -> float:
        """
        Yield variance as a percentage of expected.
        """
        if self.expected_yield == 0:
            return 0.0
        return round((self.yield_variance / self.expected_yield) * 100, 2)
    
    @property
    def is_within_acceptable_variance(self) -> bool:
        """
        Check if yield is within acceptable range.
        
        Per business rules:
        - Bread/Scones: 99-105 units per mix (expected ~102)
        - KDF: 97-107 units per mix (expected ~102, higher variance acceptable)
        """
        # KDF has higher acceptable variance
        if self.product.name.upper() == 'KDF':
            return -5 <= self.yield_variance_percentage <= 5
        # Standard products: ~3% variance
        return -3 <= self.yield_variance_percentage <= 3


class BatchIngredientDeduction(TimeStampedModel):
    """
    Audit record of each ingredient deducted for a production batch.
    
    This provides granular tracking of what was deducted from inventory
    for each batch, enabling:
    - Detailed cost analysis
    - Ingredient usage reporting
    - Audit trail for stock movements
    
    CRITICAL: CREATE-ONLY - Immutable audit records.
    """
    
    batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.PROTECT,
        related_name='ingredient_deductions',
        help_text="The production batch this deduction belongs to"
    )
    
    # === INVENTORY REFERENCE ===
    inventory_item_id = models.PositiveIntegerField(
        db_index=True,
        help_text="ID of the inventory item (1-15 for ingredients)"
    )
    
    item_name = models.CharField(
        max_length=100,
        help_text="Ingredient name at time of deduction (denormalized for audit)"
    )
    
    # === DEDUCTION DETAILS ===
    quantity_deducted = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Amount deducted from inventory"
    )
    
    unit = models.CharField(
        max_length=20,
        help_text="Unit of measurement (kg, L, pieces, etc.)"
    )
    
    # === COST AT DEDUCTION TIME ===
    unit_price_at_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="last_purchase_unit_price from inventory at batch time"
    )
    
    line_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity_deducted × unit_price_at_deduction"
    )
    
    # === STOCK LEVELS (for audit) ===
    stock_before = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Inventory stock level before this deduction"
    )
    
    stock_after = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Inventory stock level after this deduction"
    )
    
    class Meta:
        db_table = 'batch_ingredient_deductions'
        ordering = ['batch', 'inventory_item_id']
        indexes = [
            models.Index(fields=['batch', 'inventory_item_id']),
            models.Index(fields=['inventory_item_id', 'created_at']),
        ]
        verbose_name = 'Batch Ingredient Deduction'
        verbose_name_plural = 'Batch Ingredient Deductions'
    
    def __str__(self):
        return f"{self.batch.batch_number} - {self.item_name}: {self.quantity_deducted} {self.unit}"
    
    def save(self, *args, **kwargs):
        """Enforce CREATE-ONLY behavior."""
        if self.pk:
            raise ValueError("BatchIngredientDeduction records are immutable.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        raise ValueError("BatchIngredientDeduction records cannot be deleted.")


class ProductStock(TimeStampedModel):
    """
    Current stock of finished products available for dispatch.
    
    This is the bridge between Production and Sales:
    - Production ADDS to stock (via batches)
    - Sales DEDUCTS from stock (via dispatch)
    - Sales ADDS back to stock (via returns)
    
    CRITICAL: Uses row locking (select_for_update) for concurrent access.
    """
    
    product = models.OneToOneField(
        Product,
        on_delete=models.PROTECT,
        related_name='stock',
        help_text="The product this stock record tracks"
    )
    
    current_stock = models.PositiveIntegerField(
        default=0,
        help_text="Current available units for dispatch"
    )
    
    # === TRACKING FIELDS ===
    last_production_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of most recent production batch"
    )
    
    last_production_batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',  # No reverse relation needed
        help_text="Reference to most recent batch"
    )
    
    class Meta:
        db_table = 'product_stock'
        verbose_name = 'Product Stock'
        verbose_name_plural = 'Product Stocks'
    
    def __str__(self):
        return f"{self.product.name}: {self.current_stock} units"
    
    # NOTE: ProductStock IS updatable (unlike batches)
    # Updates happen via atomic service functions with row locking


class ProductStockMovement(TimeStampedModel):
    """
    Audit trail of all stock movements for finished products.
    
    Records every addition (production) and deduction (dispatch)
    for complete traceability.
    
    CRITICAL: CREATE-ONLY - Immutable audit records.
    """
    
    class MovementType(models.TextChoices):
        PRODUCTION = 'PRODUCTION', 'Production (batch added)'
        DISPATCH = 'DISPATCH', 'Dispatch (sent to sales)'
        RETURN = 'RETURN', 'Return (unsold from dispatch)'
        ADJUSTMENT = 'ADJUSTMENT', 'Manual adjustment'
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        help_text="The product this movement affects"
    )
    
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        db_index=True
    )
    
    quantity = models.IntegerField(
        help_text="Positive for additions, negative for deductions"
    )
    
    stock_before = models.PositiveIntegerField(
        help_text="Stock level before this movement"
    )
    
    stock_after = models.PositiveIntegerField(
        help_text="Stock level after this movement"
    )
    
    # === REFERENCE TO SOURCE ===
    reference_type = models.CharField(
        max_length=50,
        help_text="Type of source record (e.g., 'ProductionBatch', 'SalesDispatch')"
    )
    
    reference_id = models.PositiveIntegerField(
        help_text="ID of the source record"
    )
    
    # === METADATA ===
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stock_movements_recorded'
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this movement"
    )
    
    class Meta:
        db_table = 'product_stock_movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
        verbose_name = 'Product Stock Movement'
        verbose_name_plural = 'Product Stock Movements'
    
    def __str__(self):
        direction = '+' if self.quantity > 0 else ''
        return f"{self.product.name} {direction}{self.quantity} ({self.movement_type})"
    
    def save(self, *args, **kwargs):
        """Enforce CREATE-ONLY behavior."""
        if self.pk:
            raise ValueError("ProductStockMovement records are immutable.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        raise ValueError("ProductStockMovement records cannot be deleted.")
```

### 3.2 Model Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DATA MODELS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │     Product     │◄────────│      ProductionBatch        │   │
│  │  (Products App) │         │                             │   │
│  │                 │         │  • batch_number (unique)    │   │
│  │  • id           │         │  • product_id (FK)          │   │
│  │  • name         │         │  • mix_id (FK)              │   │
│  │  • is_active    │         │  • mix_snapshot (JSON)      │   │
│  └────────┬────────┘         │  • quantity_produced        │   │
│           │                  │  • expected_yield           │   │
│           │                  │  • total_ingredient_cost    │   │
│           │                  │  • cost_per_unit            │   │
│           │                  │  • production_date          │   │
│           │                  │  • produced_by (FK User)    │   │
│           │                  └──────────────┬──────────────┘   │
│           │                                 │                   │
│           │                                 │ 1:N               │
│           │                                 ▼                   │
│           │                  ┌─────────────────────────────┐   │
│           │                  │  BatchIngredientDeduction   │   │
│           │                  │                             │   │
│           │                  │  • batch_id (FK)            │   │
│           │                  │  • inventory_item_id        │   │
│           │                  │  • item_name                │   │
│           │                  │  • quantity_deducted        │   │
│           │                  │  • unit_price_at_deduction  │   │
│           │                  │  • line_cost                │   │
│           │                  │  • stock_before/after       │   │
│           │                  └─────────────────────────────┘   │
│           │                                                     │
│           │ 1:1                                                 │
│           ▼                                                     │
│  ┌─────────────────────┐     ┌─────────────────────────────┐   │
│  │    ProductStock     │     │   ProductStockMovement      │   │
│  │                     │     │                             │   │
│  │  • product_id (FK)  │◄────│  • product_id (FK)          │   │
│  │  • current_stock    │     │  • movement_type            │   │
│  │  • last_prod_date   │     │  • quantity (+/-)           │   │
│  │  • last_prod_batch  │     │  • stock_before/after       │   │
│  │                     │     │  • reference_type/id        │   │
│  │  [UPDATABLE with    │     │  • recorded_by              │   │
│  │   row locking]      │     │                             │   │
│  └─────────────────────┘     │  [CREATE-ONLY]              │   │
│                              └─────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Inventory Integration (Items 1-15)

**Production only interacts with Items 1-15 (Ingredients):**

| Item ID | Name | Unit | Production Deducts? |
|---------|------|------|---------------------|
| 1 | Bakers Flour | kg | ✅ Yes (via mix) |
| 2 | Sugar | kg | ✅ Yes (via mix) |
| 3 | Bread Improver | kg | ✅ Yes (via mix) |
| 4 | Salt | kg | ✅ Yes (via mix) |
| 5 | Calcium | kg | ✅ Yes (via mix) |
| 6 | Yeast | kg | ✅ Yes (via mix) |
| 7 | Cooking Fat | kg | ✅ Yes (via mix) |
| 8 | Cooking Oil | L | ✅ Yes (via mix) |
| 9-15 | Other ingredients | various | ✅ Yes (via mix) |
| 16-23 | Indirect costs | various | ❌ No (manual tracking) |

**Note:** Items 16-23 (Packaging, Crates, Diesel, etc.) are NOT deducted by Production.
They are tracked via Inventory's `create_output_atomic()` for manual outputs.

---

## 4. ARCHITECTURE DECISIONS

### 4.1 Decision Log

| # | Decision | Rationale | Alternatives Rejected |
|---|----------|-----------|----------------------|
| 1 | **CREATE-ONLY batches** | Immutable audit trail; bank ledger philosophy | Editable batches (corruption risk) |
| 2 | **Snapshot mix data in JSONField** | Historical accuracy; mix may change later | ForeignKey only (loses recipe at batch time) |
| 3 | **Use last_purchase_unit_price** | Simple, current cost; business requirement | Weighted average (too complex) |
| 4 | **One product per batch** | Matches physical reality; simpler tracking | Multi-product batches (complexity) |
| 5 | **Atomic transactions only** | ACID compliance; no partial states | Saga pattern (overkill for this scale) |
| 6 | **BatchIngredientDeduction model** | Granular audit trail; cost analysis | Store only in snapshot (less queryable) |
| 7 | **No batch states (PENDING/COMPLETE)** | Batch exists = completed; atomic creation | State machine (unnecessary complexity) |
| 8 | **ProductStock row locking** | Prevent race conditions in concurrent access | Optimistic locking (less safe) |
| 9 | **Leftovers in Sales, not Production** | Leftovers are post-dispatch; cleaner separation | Production tracks leftovers (wrong domain) |
| 10 | **Stock alerts in Inventory utilities** | DRY; alerts triggered by deduction, not caller | Production creates alerts (duplication) |

### 4.2 Why Snapshot Mix Data?

**Problem:** If a Mix is edited after a batch is recorded, we lose the actual recipe used.

**Solution:** Store complete mix data in `mix_snapshot` JSONField at batch creation.

```python
# Example mix_snapshot structure
{
    "mix_id": 1,
    "mix_name": "Bread Mix 1",
    "expected_yield": 132,
    "ingredients": [
        {
            "inventory_item_id": 1,
            "item_name": "Bakers Flour",
            "quantity_required": "36.000",
            "unit": "kg",
            "unit_price_at_batch": "85.50",
            "line_cost": "3078.00"
        },
        {
            "inventory_item_id": 2,
            "item_name": "Sugar",
            "quantity_required": "4.500",
            "unit": "kg",
            "unit_price_at_batch": "150.00",
            "line_cost": "675.00"
        }
        # ... more ingredients
    ],
    "total_mix_cost": "12500.00",
    "snapshot_timestamp": "2025-11-29T08:30:00Z"
}
```

**Benefits:**
- ✅ Historical accuracy (recipe at exact time of production)
- ✅ Cost audit trail (prices locked at batch time)
- ✅ No need to track mix versions
- ✅ Self-contained batch record

### 4.3 Why Last Purchase Unit Price?

**Business Requirement:** Use the most recent purchase price for cost calculations.

**Implementation:**
```python
# During batch creation, get current price from Inventory
item_details = Item01Details.objects.get(pk=1)  # Bakers Flour
unit_price = item_details.last_purchase_unit_price  # e.g., 85.50

# This price is frozen in mix_snapshot and BatchIngredientDeduction
```

**Why Not Weighted Average?**
- More complex to calculate and maintain
- Requires tracking purchase history with quantities
- Business prefers simpler "current price" approach
- Can be added in V2 if needed

### 4.4 Why No Batch States?

**Traditional approach:** PENDING → IN_PROGRESS → COMPLETE → CANCELLED

**Our approach:** Batch either **exists** (success) or **doesn't exist** (rolled back)

```python
# Atomic batch creation - no intermediate states
@transaction.atomic
def create_production_batch(...):
    # 1. Validate everything
    # 2. Create ProductionBatch
    # 3. Deduct ingredients (via Inventory utility)
    # 4. Create BatchIngredientDeduction records
    # 5. Update ProductStock
    # 6. Create ProductStockMovement
    
    # If ANY step fails → entire transaction rolls back
    # Batch either fully exists or doesn't exist at all
```

**Benefits:**
- ✅ No orphaned/stuck batches
- ✅ No "partial" production states
- ✅ Simpler code (no state machine)
- ✅ Database integrity guaranteed

### 4.5 Atomic Transaction Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              PRODUCTION BATCH ATOMIC TRANSACTION                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  @transaction.atomic                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  1. VALIDATE                                            │   │
│  │     ├── Mix exists and is active                        │   │
│  │     ├── All ingredients available (sufficient stock)    │   │
│  │     └── User has permission                             │   │
│  │                                                         │   │
│  │  2. LOCK & PREPARE                                      │   │
│  │     ├── Lock ProductStock row (select_for_update)       │   │
│  │     ├── Build mix snapshot with current prices          │   │
│  │     └── Generate batch number                           │   │
│  │                                                         │   │
│  │  3. CREATE BATCH                                        │   │
│  │     └── ProductionBatch.objects.create(...)             │   │
│  │                                                         │   │
│  │  4. DEDUCT INGREDIENTS                                  │   │
│  │     ├── Call Inventory's deduct_ingredients_atomic()    │   │
│  │     ├── Create BatchIngredientDeduction records         │   │
│  │     └── (Stock alerts created by Inventory utility)     │   │
│  │                                                         │   │
│  │  5. UPDATE PRODUCT STOCK                                │   │
│  │     ├── Increment ProductStock.current_stock            │   │
│  │     ├── Update last_production_date/batch               │   │
│  │     └── Create ProductStockMovement record              │   │
│  │                                                         │   │
│  │  6. RETURN SUCCESS                                      │   │
│  │     └── Return batch details + any stock alerts         │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  If ANY error occurs → ROLLBACK entire transaction              │
│  - No batch created                                             │
│  - No ingredients deducted                                      │
│  - No stock updated                                             │
│  - Clean state maintained                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6 Row Locking Strategy

**Problem:** Multiple users might record batches simultaneously, causing race conditions.

**Solution:** Use `select_for_update()` for ProductStock:

```python
@transaction.atomic
def add_production_to_stock(product_id: int, quantity: int, batch: ProductionBatch, user):
    """
    Add produced quantity to product stock with row locking.
    """
    # Lock the row for this product - other transactions wait
    stock = ProductStock.objects.select_for_update().get(product_id=product_id)
    
    stock_before = stock.current_stock
    stock.current_stock += quantity
    stock.last_production_date = batch.production_date
    stock.last_production_batch = batch
    stock.save()
    
    # Create audit record
    ProductStockMovement.objects.create(
        product_id=product_id,
        movement_type=ProductStockMovement.MovementType.PRODUCTION,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock.current_stock,
        reference_type='ProductionBatch',
        reference_id=batch.id,
        recorded_by=user
    )
    
    return stock.current_stock
```

**Why Row Locking?**
- Prevents "lost update" problem
- Ensures stock counts are always accurate
- Database-level guarantee (not application-level)
- Works with PostgreSQL and SQLite

---

## 5. WORKFLOW REFERENCE

### 5.1 Workflow Summary Table

| Workflow | Trigger | Owner | Key Operations |
|----------|---------|-------|----------------|
| Record Production Batch | User submits form | Production | Create batch, deduct ingredients, update stock |
| View Production History | User navigates | Production | Read-only batch list with filters |
| View Batch Details | User clicks batch | Production | Display snapshot, costs, yield variance |
| View Product Stock | User navigates | Production | Display current stock levels |
| Generate Batch Number | System (auto) | Production | Format: PRD-YYYYMMDD-XXX |

### 5.2 Workflow 1: Record Production Batch (Primary Workflow)

**Trigger:** User submits production batch form  
**Owner:** Production App  
**Purpose:** Create immutable production record, deduct ingredients, update finished goods stock

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW: RECORD PRODUCTION BATCH                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  USER INPUT                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Select Product (dropdown: Bread, KDF, Scones)         │   │
│  │ • Select Mix (filtered by product)                       │   │
│  │ • Enter Quantity Produced (actual yield)                 │   │
│  │ • Select Production Date (default: today)                │   │
│  │ • Optional: Production Time, Notes                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  VALIDATION (PRE-SUBMIT)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Mix is active                                        │   │
│  │ 2. Quantity > 0                                         │   │
│  │ 3. Production date not in future                        │   │
│  │ 4. User has production permission                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  @transaction.atomic                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  STEP 1: CHECK INGREDIENT AVAILABILITY                  │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ For each ingredient in mix:                     │   │   │
│  │  │   - Get ItemXXDetails from Inventory            │   │   │
│  │  │   - Check: current_stock >= quantity_required   │   │   │
│  │  │   - Collect: last_purchase_unit_price           │   │   │
│  │  │                                                 │   │   │
│  │  │ If ANY insufficient:                            │   │   │
│  │  │   → Return error with shortage details          │   │   │
│  │  │   → ROLLBACK                                    │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 2: BUILD MIX SNAPSHOT                             │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ mix_snapshot = {                                │   │   │
│  │  │   "mix_id": mix.id,                            │   │   │
│  │  │   "mix_name": mix.name,                        │   │   │
│  │  │   "expected_yield": mix.expected_yield,        │   │   │
│  │  │   "ingredients": [                             │   │   │
│  │  │     {                                          │   │   │
│  │  │       "inventory_item_id": 1,                  │   │   │
│  │  │       "item_name": "Bakers Flour",             │   │   │
│  │  │       "quantity_required": "36.000",           │   │   │
│  │  │       "unit": "kg",                            │   │   │
│  │  │       "unit_price_at_batch": "85.50",          │   │   │
│  │  │       "line_cost": "3078.00"                   │   │   │
│  │  │     },                                         │   │   │
│  │  │     ...                                        │   │   │
│  │  │   ],                                           │   │   │
│  │  │   "total_mix_cost": "12500.00"                │   │   │
│  │  │ }                                              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 3: GENERATE BATCH NUMBER                          │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Format: PRD-YYYYMMDD-XXX                        │   │   │
│  │  │ Example: PRD-20251129-001                       │   │   │
│  │  │                                                 │   │   │
│  │  │ XXX = sequential for the day (001, 002, ...)   │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 4: CREATE PRODUCTION BATCH                        │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ ProductionBatch.objects.create(                 │   │   │
│  │  │   batch_number=batch_number,                   │   │   │
│  │  │   product=product,                             │   │   │
│  │  │   mix=mix,                                     │   │   │
│  │  │   mix_snapshot=mix_snapshot,                   │   │   │
│  │  │   quantity_produced=quantity,                  │   │   │
│  │  │   expected_yield=mix.expected_yield,           │   │   │
│  │  │   total_ingredient_cost=total_cost,            │   │   │
│  │  │   cost_per_unit=total_cost / quantity,         │   │   │
│  │  │   production_date=date,                        │   │   │
│  │  │   produced_by=user                             │   │   │
│  │  │ )                                              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 5: DEDUCT INGREDIENTS                             │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Call Inventory's deduct_ingredients_atomic()    │   │   │
│  │  │                                                 │   │   │
│  │  │ deduction_result = deduct_ingredients_atomic(  │   │   │
│  │  │   ingredients_list=[                           │   │   │
│  │  │     {'inventory_item_id': 1, 'quantity': 36},  │   │   │
│  │  │     {'inventory_item_id': 2, 'quantity': 4.5}, │   │   │
│  │  │     ...                                        │   │   │
│  │  │   ],                                           │   │   │
│  │  │   requested_by_app='production',               │   │   │
│  │  │   requested_by_user=user                       │   │   │
│  │  │ )                                              │   │   │
│  │  │                                                 │   │   │
│  │  │ ⚠️ Stock alerts created INSIDE this utility    │   │   │
│  │  │    if any item falls below minimum level       │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 6: CREATE DEDUCTION AUDIT RECORDS                 │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ For each ingredient deducted:                   │   │   │
│  │  │   BatchIngredientDeduction.objects.create(      │   │   │
│  │  │     batch=batch,                               │   │   │
│  │  │     inventory_item_id=item_id,                 │   │   │
│  │  │     item_name=item_name,                       │   │   │
│  │  │     quantity_deducted=qty,                     │   │   │
│  │  │     unit=unit,                                 │   │   │
│  │  │     unit_price_at_deduction=price,             │   │   │
│  │  │     line_cost=qty * price,                     │   │   │
│  │  │     stock_before=before,                       │   │   │
│  │  │     stock_after=after                          │   │   │
│  │  │   )                                            │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 7: UPDATE PRODUCT STOCK                           │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ stock = ProductStock.objects.select_for_update()│   │   │
│  │  │            .get(product=product)                │   │   │
│  │  │                                                 │   │   │
│  │  │ stock_before = stock.current_stock             │   │   │
│  │  │ stock.current_stock += quantity_produced       │   │   │
│  │  │ stock.last_production_date = date              │   │   │
│  │  │ stock.last_production_batch = batch            │   │   │
│  │  │ stock.save()                                   │   │   │
│  │  │                                                 │   │   │
│  │  │ ProductStockMovement.objects.create(           │   │   │
│  │  │   product=product,                             │   │   │
│  │  │   movement_type='PRODUCTION',                  │   │   │
│  │  │   quantity=quantity_produced,                  │   │   │
│  │  │   stock_before=stock_before,                   │   │   │
│  │  │   stock_after=stock.current_stock,             │   │   │
│  │  │   reference_type='ProductionBatch',            │   │   │
│  │  │   reference_id=batch.id,                       │   │   │
│  │  │   recorded_by=user                             │   │   │
│  │  │ )                                              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                         │                               │   │
│  │                         ▼                               │   │
│  │  STEP 8: RETURN SUCCESS                                 │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ return {                                        │   │   │
│  │  │   'success': True,                             │   │   │
│  │  │   'data': {                                    │   │   │
│  │  │     'batch': batch,                            │   │   │
│  │  │     'batch_number': 'PRD-20251129-001',        │   │   │
│  │  │     'quantity_produced': 132,                  │   │   │
│  │  │     'total_cost': Decimal('12500.00'),         │   │   │
│  │  │     'cost_per_unit': Decimal('94.70'),         │   │   │
│  │  │     'stock_alerts': [...],  # From Inventory   │   │   │
│  │  │     'new_product_stock': 264                   │   │   │
│  │  │   }                                            │   │   │
│  │  │ }                                              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TRANSACTION COMPLETE ✓                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Models Affected

| Model | App | Operation |
|-------|-----|-----------|
| Mix | Products | READ (get recipe) |
| MixIngredient | Products | READ (get ingredients) |
| ItemXXDetails | Inventory | READ (check stock, get price) → UPDATE (deduct stock) |
| ItemXXTransactions | Inventory | CREATE (deduction record) |
| StockAlert | Inventory | CREATE (if below minimum) |
| ProductionBatch | Production | CREATE |
| BatchIngredientDeduction | Production | CREATE (one per ingredient) |
| ProductStock | Production | UPDATE (increment stock) |
| ProductStockMovement | Production | CREATE |

### 5.3 Workflow 2: View Production History

**Trigger:** User navigates to production history page  
**Owner:** Production App  
**Purpose:** Display list of production batches with filters and search

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW: VIEW PRODUCTION HISTORY                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  USER NAVIGATES TO: /production/batches/                        │
│                                                                 │
│  FILTERS AVAILABLE                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Date Range (from/to)                                  │   │
│  │ • Product (Bread, KDF, Scones, All)                     │   │
│  │ • Produced By (user dropdown)                           │   │
│  │ • Search (batch number)                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LIST DISPLAY                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Batch #       │ Product │ Qty  │ Date       │ Cost     │   │
│  │───────────────┼─────────┼──────┼────────────┼──────────│   │
│  │ PRD-1129-003  │ Bread   │ 132  │ 2025-11-29 │ 12,500   │   │
│  │ PRD-1129-002  │ Scones  │ 105  │ 2025-11-29 │ 8,200    │   │
│  │ PRD-1129-001  │ KDF     │ 102  │ 2025-11-29 │ 15,800   │   │
│  │ ...           │         │      │            │          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  PAGINATION: 20 batches per page                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Workflow 3: View Batch Details

**Trigger:** User clicks on a batch in the list  
**Owner:** Production App  
**Purpose:** Display complete batch information including snapshot and costs

#### Detail View Contents

```
┌─────────────────────────────────────────────────────────────────┐
│              BATCH DETAILS: PRD-20251129-001                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BATCH INFORMATION                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Batch Number:     PRD-20251129-001                      │   │
│  │ Product:          Bread                                 │   │
│  │ Mix Used:         Bread Mix 1                           │   │
│  │ Production Date:  November 29, 2025                     │   │
│  │ Recorded By:      John Doe (Accountant)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  YIELD INFORMATION                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Quantity Produced:  132 units                           │   │
│  │ Expected Yield:     132 units                           │   │
│  │ Variance:           0 units (0.00%)  ✓ Within range     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  INGREDIENT DEDUCTIONS (from snapshot)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Ingredient      │ Qty      │ Unit │ Price   │ Cost     │   │
│  │─────────────────┼──────────┼──────┼─────────┼──────────│   │
│  │ Bakers Flour    │ 36.000   │ kg   │ 85.50   │ 3,078.00 │   │
│  │ Sugar           │ 4.500    │ kg   │ 150.00  │ 675.00   │   │
│  │ Bread Improver  │ 0.060    │ kg   │ 450.00  │ 27.00    │   │
│  │ Salt            │ 0.280    │ kg   │ 45.00   │ 12.60    │   │
│  │ Calcium         │ 0.070    │ kg   │ 200.00  │ 14.00    │   │
│  │ Yeast           │ 0.200    │ kg   │ 380.00  │ 76.00    │   │
│  │ Cooking Fat     │ 2.800    │ kg   │ 280.00  │ 784.00   │   │
│  │─────────────────┴──────────┴──────┴─────────┴──────────│   │
│  │                              TOTAL COST: KES 4,666.60   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  COST SUMMARY                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Total Ingredient Cost:  KES 4,666.60                    │   │
│  │ Quantity Produced:      132 units                       │   │
│  │ Cost Per Unit:          KES 35.35                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  NOTES                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ (Any production notes entered by user)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.5 Workflow 4: View Product Stock Dashboard

**Trigger:** User navigates to stock dashboard  
**Owner:** Production App  
**Purpose:** Display current finished goods stock levels

#### Dashboard Display

```
┌─────────────────────────────────────────────────────────────────┐
│              PRODUCT STOCK DASHBOARD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CURRENT STOCK LEVELS                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐             │   │
│  │  │  BREAD  │    │   KDF   │    │ SCONES  │             │   │
│  │  │         │    │         │    │         │             │   │
│  │  │   264   │    │   156   │    │   210   │             │   │
│  │  │  units  │    │  units  │    │  units  │             │   │
│  │  │         │    │         │    │         │             │   │
│  │  │ Last:   │    │ Last:   │    │ Last:   │             │   │
│  │  │ Today   │    │ Today   │    │ Yesterday│             │   │
│  │  └─────────┘    └─────────┘    └─────────┘             │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TODAY'S PRODUCTION                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Bread: 2 batches (264 units)                          │   │
│  │ • KDF: 1 batch (102 units)                              │   │
│  │ • Scones: 0 batches                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  RECENT MOVEMENTS                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Time    │ Product │ Type       │ Qty   │ Stock After   │   │
│  │─────────┼─────────┼────────────┼───────┼───────────────│   │
│  │ 08:30   │ Bread   │ Production │ +132  │ 264           │   │
│  │ 07:45   │ Bread   │ Production │ +132  │ 132           │   │
│  │ 07:00   │ KDF     │ Production │ +102  │ 156           │   │
│  │ 06:30   │ Scones  │ Dispatch   │ -50   │ 210           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. CROSS-APP INTEGRATION

### 6.1 Integration Matrix

| Source App | Target App | Interaction | Direction |
|------------|------------|-------------|-----------|
| Production | Products | Read Mix, MixIngredients | → (reads) |
| Production | Inventory | Deduct ingredients, read prices | → (calls utility) |
| Production | Inventory | Receive stock alerts | ← (returned from utility) |
| Sales | Production | Read ProductStock for dispatch | ← (reads) |
| Sales | Production | Update ProductStock (dispatch/return) | → (calls utility) |
| Reports | Production | Read batches, stock movements | ← (reads) |

### 6.2 Products App Integration

**Purpose:** Get recipe data for production batches

#### Read Mix Data

```python
# apps/production/services.py

from apps.products.models import Mix, MixIngredient

def get_mix_with_ingredients(mix_id: int) -> dict:
    """
    Get mix data with all ingredients for batch creation.
    
    Args:
        mix_id: ID of the mix to retrieve
    
    Returns:
        dict with mix info and ingredient list
    
    Raises:
        ValueError: If mix not found or inactive
    """
    try:
        mix = Mix.objects.select_related('product').prefetch_related(
            'ingredients'
        ).get(id=mix_id, is_active=True)
    except Mix.DoesNotExist:
        raise ValueError(f"Mix {mix_id} not found or is inactive")
    
    ingredients = []
    for mi in mix.ingredients.all():
        ingredients.append({
            'inventory_item_id': mi.inventory_item_id,
            'quantity_required': mi.quantity_required,
        })
    
    return {
        'mix_id': mix.id,
        'mix_name': mix.name,
        'product_id': mix.product_id,
        'product_name': mix.product.name,
        'expected_yield': mix.expected_yield,
        'ingredients': ingredients
    }
```

### 6.3 Inventory App Integration

**Purpose:** Deduct ingredients, get prices, trigger stock alerts

#### Calling Inventory Utility

```python
# apps/production/services.py

from apps.inventory.utils import deduct_ingredients_atomic
from apps.inventory.routing import get_item_details_model

def build_mix_snapshot_with_prices(mix_data: dict) -> dict:
    """
    Build complete mix snapshot with current inventory prices.
    
    Args:
        mix_data: Output from get_mix_with_ingredients()
    
    Returns:
        Complete snapshot dict for ProductionBatch.mix_snapshot
    """
    ingredients_with_prices = []
    total_cost = Decimal('0.00')
    
    for ingredient in mix_data['ingredients']:
        item_id = ingredient['inventory_item_id']
        qty = Decimal(str(ingredient['quantity_required']))
        
        # Get current price from Inventory
        DetailsModel = get_item_details_model(item_id)
        details = DetailsModel.objects.get(pk=1)  # Single row per table
        
        unit_price = details.last_purchase_unit_price
        line_cost = (qty * unit_price).quantize(Decimal('0.01'))
        total_cost += line_cost
        
        ingredients_with_prices.append({
            'inventory_item_id': item_id,
            'item_name': details.item_name,
            'quantity_required': str(qty),
            'unit': details.unit,
            'unit_price_at_batch': str(unit_price),
            'line_cost': str(line_cost)
        })
    
    return {
        'mix_id': mix_data['mix_id'],
        'mix_name': mix_data['mix_name'],
        'expected_yield': mix_data['expected_yield'],
        'ingredients': ingredients_with_prices,
        'total_mix_cost': str(total_cost),
        'snapshot_timestamp': timezone.now().isoformat()
    }


def deduct_batch_ingredients(batch: ProductionBatch, user) -> dict:
    """
    Deduct ingredients from inventory for a production batch.
    
    Calls Inventory's deduct_ingredients_atomic() utility.
    Stock alerts are created INSIDE that utility if needed.
    
    Args:
        batch: The ProductionBatch being created
        user: User performing the action
    
    Returns:
        dict with deduction results and any stock alerts
    """
    # Build deduction list from mix snapshot
    deductions = []
    for ingredient in batch.mix_snapshot['ingredients']:
        deductions.append({
            'inventory_item_id': ingredient['inventory_item_id'],
            'quantity': Decimal(ingredient['quantity_required'])
        })
    
    # Call Inventory utility (handles stock alerts internally)
    result = deduct_ingredients_atomic(
        ingredients_list=deductions,
        requested_by_app='production',
        requested_by_user=user
    )
    
    return result
```

### 6.4 Inventory Routing Reference

**Production uses Inventory's routing module to access per-item tables:**

```python
# apps/inventory/routing.py (reference - exists in Inventory app)

ITEM_TABLE_MAPPING = {
    1: ('Item01Details', 'Item01Transactions'),   # Bakers Flour
    2: ('Item02Details', 'Item02Transactions'),   # Sugar
    3: ('Item03Details', 'Item03Transactions'),   # Bread Improver
    4: ('Item04Details', 'Item04Transactions'),   # Salt
    5: ('Item05Details', 'Item05Transactions'),   # Calcium
    6: ('Item06Details', 'Item06Transactions'),   # Yeast
    7: ('Item07Details', 'Item07Transactions'),   # Cooking Fat
    8: ('Item08Details', 'Item08Transactions'),   # Cooking Oil
    # ... items 9-15 (other ingredients)
    # Items 16-23 exist but NOT used by Production
}

def get_item_details_model(item_id: int):
    """Get the Details model class for an inventory item."""
    # Returns Item01Details, Item02Details, etc.
    
def get_item_transactions_model(item_id: int):
    """Get the Transactions model class for an inventory item."""
    # Returns Item01Transactions, Item02Transactions, etc.
```

**Important:** Production only interacts with Items 1-15 (Ingredients).
Items 16-23 (Packaging, Crates, Diesel, etc.) are tracked manually via Inventory's outputs.

### 6.5 Sales App Integration (Outbound)

**Purpose:** Sales reads ProductStock to know what's available for dispatch

#### Sales Reads Production Stock

```python
# In Sales App (for context - implemented in Sales spec)

from apps.production.models import ProductStock

def get_available_stock(product_id: int) -> int:
    """
    Get current available stock for a product.
    Called by Sales before creating dispatch.
    """
    try:
        stock = ProductStock.objects.get(product_id=product_id)
        return stock.current_stock
    except ProductStock.DoesNotExist:
        return 0
```

#### Sales Updates Production Stock

```python
# apps/production/services.py

@transaction.atomic
def deduct_dispatch_from_stock(
    product_id: int,
    quantity: int,
    dispatch_id: int,
    user
) -> dict:
    """
    Deduct dispatched quantity from product stock.
    Called by Sales App when creating a dispatch.
    
    Args:
        product_id: Product being dispatched
        quantity: Units to dispatch
        dispatch_id: ID of the SalesDispatch record
        user: User performing the action
    
    Returns:
        dict with success status and new stock level
    
    Raises:
        ValueError: If insufficient stock
    """
    stock = ProductStock.objects.select_for_update().get(product_id=product_id)
    
    if stock.current_stock < quantity:
        raise ValueError(
            f"Insufficient stock. Available: {stock.current_stock}, "
            f"Requested: {quantity}"
        )
    
    stock_before = stock.current_stock
    stock.current_stock -= quantity
    stock.save()
    
    # Create movement record
    ProductStockMovement.objects.create(
        product_id=product_id,
        movement_type=ProductStockMovement.MovementType.DISPATCH,
        quantity=-quantity,  # Negative for deduction
        stock_before=stock_before,
        stock_after=stock.current_stock,
        reference_type='SalesDispatch',
        reference_id=dispatch_id,
        recorded_by=user
    )
    
    return {
        'success': True,
        'stock_before': stock_before,
        'stock_after': stock.current_stock
    }


@transaction.atomic
def add_return_to_stock(
    product_id: int,
    quantity: int,
    return_id: int,
    user
) -> dict:
    """
    Add returned units back to product stock.
    Called by Sales App when processing returns.
    
    Args:
        product_id: Product being returned
        quantity: Units returned
        return_id: ID of the SalesReturn record
        user: User performing the action
    
    Returns:
        dict with success status and new stock level
    """
    stock = ProductStock.objects.select_for_update().get(product_id=product_id)
    
    stock_before = stock.current_stock
    stock.current_stock += quantity
    stock.save()
    
    ProductStockMovement.objects.create(
        product_id=product_id,
        movement_type=ProductStockMovement.MovementType.RETURN,
        quantity=quantity,  # Positive for addition
        stock_before=stock_before,
        stock_after=stock.current_stock,
        reference_type='SalesReturn',
        reference_id=return_id,
        recorded_by=user
    )
    
    return {
        'success': True,
        'stock_before': stock_before,
        'stock_after': stock.current_stock
    }
```

### 6.6 Stock Alert Flow (Via Inventory)

**Key Clarification:** Production does NOT create stock alerts directly.

```
┌─────────────────────────────────────────────────────────────────┐
│                    STOCK ALERT FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRODUCTION APP                    INVENTORY APP                │
│  ┌──────────────┐                 ┌──────────────────────────┐ │
│  │              │                 │                          │ │
│  │  Create      │   ─────────▶    │  deduct_ingredients_     │ │
│  │  Batch       │   Calls         │  atomic()                │ │
│  │              │                 │                          │ │
│  │              │                 │    ┌──────────────────┐  │ │
│  │              │                 │    │ For each item:   │  │ │
│  │              │                 │    │ 1. Deduct stock  │  │ │
│  │              │                 │    │ 2. Check minimum │  │ │
│  │              │                 │    │ 3. Create alert  │  │ │
│  │              │                 │    │    if needed     │  │ │
│  │              │                 │    └──────────────────┘  │ │
│  │              │                 │                          │ │
│  │              │   ◀─────────    │  Return:                 │ │
│  │  Display     │   Returns       │  {                       │ │
│  │  Alerts      │   alerts        │    'success': True,      │ │
│  │              │                 │    'alerts': [...]       │ │
│  │              │                 │  }                       │ │
│  └──────────────┘                 └──────────────────────────┘ │
│                                                                 │
│  Email notifications sent via transaction.on_commit()           │
│  inside Inventory utility (DRY - not duplicated in Production) │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. SERVICE LAYER

### 7.1 Service Module Structure

```
apps/production/
├── __init__.py
├── models.py              # ProductionBatch, BatchIngredientDeduction, etc.
├── services.py            # Core business logic
├── views.py               # HTTP handlers
├── forms.py               # Django forms
├── urls.py                # URL routing
├── admin.py               # Django admin
├── utils.py               # Helper functions
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

### 7.2 Core Service: Create Production Batch

```python
# apps/production/services.py

from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.products.models import Mix
from apps.inventory.utils import deduct_ingredients_atomic
from apps.inventory.routing import get_item_details_model
from .models import (
    ProductionBatch, 
    BatchIngredientDeduction, 
    ProductStock, 
    ProductStockMovement
)


class ProductionService:
    """
    Core service for production batch operations.
    
    All methods follow ACID principles:
    - Atomic transactions
    - Consistent state
    - Isolated operations
    - Durable records
    """
    
    @staticmethod
    def generate_batch_number(production_date) -> str:
        """
        Generate unique batch number for the given date.
        
        Format: PRD-YYYYMMDD-XXX
        Where XXX is sequential for the day (001, 002, etc.)
        
        Args:
            production_date: Date of production
        
        Returns:
            Unique batch number string
        """
        date_str = production_date.strftime('%Y%m%d')
        prefix = f"PRD-{date_str}-"
        
        # Find highest existing batch number for this date
        last_batch = ProductionBatch.objects.filter(
            batch_number__startswith=prefix
        ).order_by('-batch_number').first()
        
        if last_batch:
            # Extract sequence number and increment
            last_seq = int(last_batch.batch_number.split('-')[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        
        return f"{prefix}{next_seq:03d}"
    
    @staticmethod
    def validate_mix_availability(mix_id: int) -> dict:
        """
        Validate that a mix exists and is active.
        
        Args:
            mix_id: ID of the mix to validate
        
        Returns:
            dict with validation result and mix data
        
        Raises:
            ValueError: If mix not found or inactive
        """
        try:
            mix = Mix.objects.select_related('product').prefetch_related(
                'ingredients'
            ).get(id=mix_id, is_active=True, product__is_active=True)
        except Mix.DoesNotExist:
            raise ValueError(f"Mix {mix_id} not found or is inactive")
        
        return {
            'mix': mix,
            'product': mix.product,
            'expected_yield': mix.expected_yield,
            'ingredient_count': mix.ingredients.count()
        }
    
    @staticmethod
    def check_ingredient_availability(mix: Mix) -> dict:
        """
        Check if all ingredients are available in sufficient quantity.
        
        Args:
            mix: Mix object with prefetched ingredients
        
        Returns:
            dict with:
            - available: bool
            - ingredients: list with availability details
            - shortages: list of ingredients with insufficient stock
        """
        ingredients_status = []
        shortages = []
        
        for mi in mix.ingredients.all():
            DetailsModel = get_item_details_model(mi.inventory_item_id)
            details = DetailsModel.objects.get(pk=1)
            
            available = details.current_stock >= mi.quantity_required
            
            status = {
                'inventory_item_id': mi.inventory_item_id,
                'item_name': details.item_name,
                'required': mi.quantity_required,
                'available': details.current_stock,
                'unit': details.unit,
                'sufficient': available,
                'unit_price': details.last_purchase_unit_price
            }
            ingredients_status.append(status)
            
            if not available:
                shortages.append({
                    'item_name': details.item_name,
                    'required': mi.quantity_required,
                    'available': details.current_stock,
                    'shortage': mi.quantity_required - details.current_stock,
                    'unit': details.unit
                })
        
        return {
            'available': len(shortages) == 0,
            'ingredients': ingredients_status,
            'shortages': shortages
        }
    
    @staticmethod
    def build_mix_snapshot(mix: Mix, ingredients_status: list) -> dict:
        """
        Build complete mix snapshot with current prices.
        
        Args:
            mix: Mix object
            ingredients_status: Output from check_ingredient_availability
        
        Returns:
            Complete snapshot dict for ProductionBatch.mix_snapshot
        """
        ingredients_snapshot = []
        total_cost = Decimal('0.00')
        
        for ing in ingredients_status:
            qty = Decimal(str(ing['required']))
            price = Decimal(str(ing['unit_price']))
            line_cost = (qty * price).quantize(Decimal('0.01'))
            total_cost += line_cost
            
            ingredients_snapshot.append({
                'inventory_item_id': ing['inventory_item_id'],
                'item_name': ing['item_name'],
                'quantity_required': str(qty.quantize(Decimal('0.001'))),
                'unit': ing['unit'],
                'unit_price_at_batch': str(price.quantize(Decimal('0.01'))),
                'line_cost': str(line_cost)
            })
        
        return {
            'mix_id': mix.id,
            'mix_name': mix.name,
            'expected_yield': mix.expected_yield,
            'ingredients': ingredients_snapshot,
            'total_mix_cost': str(total_cost),
            'snapshot_timestamp': timezone.now().isoformat()
        }
    
    @classmethod
    @transaction.atomic
    def create_production_batch(
        cls,
        mix_id: int,
        quantity_produced: int,
        production_date,
        user,
        production_time=None,
        notes: str = ''
    ) -> dict:
        """
        Create a production batch with full ACID compliance.
        
        This is the primary entry point for recording production.
        
        Args:
            mix_id: ID of the mix being produced
            quantity_produced: Actual units produced
            production_date: Date of production
            user: User recording the batch
            production_time: Optional time of production
            notes: Optional production notes
        
        Returns:
            dict with:
            - success: bool
            - data: batch details, alerts, stock info
            - error: error message (if failed)
        """
        try:
            # STEP 1: Validate mix
            mix_validation = cls.validate_mix_availability(mix_id)
            mix = mix_validation['mix']
            product = mix_validation['product']
            
            # STEP 2: Check ingredient availability
            availability = cls.check_ingredient_availability(mix)
            
            if not availability['available']:
                return {
                    'success': False,
                    'error': 'Insufficient ingredients',
                    'shortages': availability['shortages']
                }
            
            # STEP 3: Build mix snapshot with prices
            mix_snapshot = cls.build_mix_snapshot(mix, availability['ingredients'])
            total_cost = Decimal(mix_snapshot['total_mix_cost'])
            
            # STEP 4: Generate batch number
            batch_number = cls.generate_batch_number(production_date)
            
            # STEP 5: Calculate cost per unit
            cost_per_unit = (total_cost / Decimal(quantity_produced)).quantize(
                Decimal('0.0001')
            )
            
            # STEP 6: Create ProductionBatch
            batch = ProductionBatch(
                batch_number=batch_number,
                product=product,
                mix=mix,
                mix_snapshot=mix_snapshot,
                quantity_produced=quantity_produced,
                expected_yield=mix.expected_yield,
                total_ingredient_cost=total_cost,
                cost_per_unit=cost_per_unit,
                production_date=production_date,
                production_time=production_time,
                produced_by=user,
                notes=notes
            )
            # Use Django's Model.save() - our override prevents updates
            batch.save(force_insert=True)
            
            # STEP 7: Deduct ingredients from Inventory
            deductions = []
            for ing in mix_snapshot['ingredients']:
                deductions.append({
                    'inventory_item_id': ing['inventory_item_id'],
                    'quantity': Decimal(ing['quantity_required'])
                })
            
            deduction_result = deduct_ingredients_atomic(
                ingredients_list=deductions,
                requested_by_app='production',
                requested_by_user=user
            )
            
            # STEP 8: Create BatchIngredientDeduction records
            for ing in mix_snapshot['ingredients']:
                # Get before/after from deduction result
                item_deduction = next(
                    d for d in deduction_result['data']['deductions']
                    if d['inventory_item_id'] == ing['inventory_item_id']
                )
                
                BatchIngredientDeduction.objects.create(
                    batch=batch,
                    inventory_item_id=ing['inventory_item_id'],
                    item_name=ing['item_name'],
                    quantity_deducted=Decimal(ing['quantity_required']),
                    unit=ing['unit'],
                    unit_price_at_deduction=Decimal(ing['unit_price_at_batch']),
                    line_cost=Decimal(ing['line_cost']),
                    stock_before=item_deduction['stock_before'],
                    stock_after=item_deduction['stock_after']
                )
            
            # STEP 9: Update ProductStock
            stock, created = ProductStock.objects.select_for_update().get_or_create(
                product=product,
                defaults={'current_stock': 0}
            )
            
            stock_before = stock.current_stock
            stock.current_stock += quantity_produced
            stock.last_production_date = production_date
            stock.last_production_batch = batch
            stock.save()
            
            # STEP 10: Create ProductStockMovement
            ProductStockMovement.objects.create(
                product=product,
                movement_type=ProductStockMovement.MovementType.PRODUCTION,
                quantity=quantity_produced,
                stock_before=stock_before,
                stock_after=stock.current_stock,
                reference_type='ProductionBatch',
                reference_id=batch.id,
                recorded_by=user
            )
            
            # STEP 11: Return success with all details
            return {
                'success': True,
                'data': {
                    'batch': batch,
                    'batch_number': batch_number,
                    'product_name': product.name,
                    'quantity_produced': quantity_produced,
                    'expected_yield': mix.expected_yield,
                    'yield_variance': quantity_produced - mix.expected_yield,
                    'total_cost': total_cost,
                    'cost_per_unit': cost_per_unit,
                    'stock_before': stock_before,
                    'stock_after': stock.current_stock,
                    'stock_alerts': deduction_result['data'].get('alerts', [])
                }
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error creating production batch: {e}")
            
            return {
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }
    
    @staticmethod
    def get_production_summary(date=None, product_id: int = None) -> dict:
        """
        Get production summary for dashboard display.
        
        Args:
            date: Filter by date (default: today)
            product_id: Filter by product (optional)
        
        Returns:
            dict with production statistics
        """
        if date is None:
            date = timezone.now().date()
        
        queryset = ProductionBatch.objects.filter(production_date=date)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        from django.db.models import Sum, Count, Avg
        
        stats = queryset.aggregate(
            total_batches=Count('id'),
            total_units=Sum('quantity_produced'),
            total_cost=Sum('total_ingredient_cost'),
            avg_cost_per_unit=Avg('cost_per_unit')
        )
        
        # Get per-product breakdown
        by_product = queryset.values('product__name').annotate(
            batches=Count('id'),
            units=Sum('quantity_produced'),
            cost=Sum('total_ingredient_cost')
        ).order_by('product__name')
        
        return {
            'date': date,
            'totals': stats,
            'by_product': list(by_product)
        }
    
    @staticmethod
    def get_batch_details(batch_id: int) -> dict:
        """
        Get complete details for a production batch.
        
        Args:
            batch_id: ID of the batch
        
        Returns:
            dict with batch details, deductions, and computed values
        
        Raises:
            ValueError: If batch not found
        """
        try:
            batch = ProductionBatch.objects.select_related(
                'product', 'mix', 'produced_by'
            ).get(id=batch_id)
        except ProductionBatch.DoesNotExist:
            raise ValueError(f"Batch {batch_id} not found")
        
        deductions = BatchIngredientDeduction.objects.filter(
            batch=batch
        ).order_by('inventory_item_id')
        
        return {
            'batch': batch,
            'deductions': list(deductions),
            'yield_variance': batch.yield_variance,
            'yield_variance_percentage': batch.yield_variance_percentage,
            'is_within_acceptable_variance': batch.is_within_acceptable_variance
        }
```

### 7.3 Utility Functions

```python
# apps/production/utils.py

from decimal import Decimal
from typing import List
from django.utils import timezone

from .models import ProductStock, ProductStockMovement


def get_product_stock_levels() -> List[dict]:
    """
    Get current stock levels for all products.
    
    Returns:
        List of dicts with product stock info
    """
    stocks = ProductStock.objects.select_related('product').all()
    
    return [
        {
            'product_id': s.product_id,
            'product_name': s.product.name,
            'current_stock': s.current_stock,
            'last_production_date': s.last_production_date,
        }
        for s in stocks
    ]


def get_recent_stock_movements(
    product_id: int = None,
    limit: int = 20
) -> List[dict]:
    """
    Get recent stock movements for display.
    
    Args:
        product_id: Filter by product (optional)
        limit: Maximum records to return
    
    Returns:
        List of movement dicts
    """
    queryset = ProductStockMovement.objects.select_related(
        'product', 'recorded_by'
    ).order_by('-created_at')
    
    if product_id:
        queryset = queryset.filter(product_id=product_id)
    
    movements = queryset[:limit]
    
    return [
        {
            'id': m.id,
            'product_name': m.product.name,
            'movement_type': m.movement_type,
            'quantity': m.quantity,
            'stock_before': m.stock_before,
            'stock_after': m.stock_after,
            'recorded_by': m.recorded_by.get_full_name(),
            'created_at': m.created_at
        }
        for m in movements
    ]


def validate_quantity_produced(quantity: int, expected_yield: int) -> dict:
    """
    Validate quantity produced against expected yield.
    
    Args:
        quantity: Actual quantity produced
        expected_yield: Expected yield from mix
    
    Returns:
        dict with validation result and warnings
    """
    variance = quantity - expected_yield
    variance_pct = (variance / expected_yield) * 100 if expected_yield > 0 else 0
    
    # Thresholds
    warning_threshold = 5  # 5% variance triggers warning
    error_threshold = 15   # 15% variance is suspicious
    
    result = {
        'valid': True,
        'quantity': quantity,
        'expected': expected_yield,
        'variance': variance,
        'variance_percentage': round(variance_pct, 2),
        'warnings': []
    }
    
    if abs(variance_pct) > error_threshold:
        result['valid'] = False
        result['warnings'].append(
            f"Variance of {variance_pct:.1f}% is unusually high. "
            f"Please verify the quantity."
        )
    elif abs(variance_pct) > warning_threshold:
        result['warnings'].append(
            f"Variance of {variance_pct:.1f}% is higher than usual."
        )
    
    return result
```

---

## 8. USER FLOWS (FRONTEND)

### 8.1 User Flow Summary

| Flow | Entry Point | Steps | Outcome |
|------|-------------|-------|---------|
| Record Batch | Dashboard → "Record Production" | Select product/mix → Enter quantity → Submit | Batch created, stock updated |
| View History | Dashboard → "Production History" | Browse/filter → Click batch | View batch details |
| View Stock | Dashboard → "Stock Levels" | View cards | See current stock |
| View Dashboard | Login → Dashboard | View summary | See today's production |

### 8.2 Flow 1: Record Production Batch

```
┌─────────────────────────────────────────────────────────────────┐
│              USER FLOW: RECORD PRODUCTION BATCH                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: NAVIGATE                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ User clicks "Record Production" on dashboard or nav     │   │
│  │ URL: /production/batches/new/                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  STEP 2: SELECT PRODUCT                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ Product: [Dropdown]                                 │ │   │
│  │ │  ○ Bread                                            │ │   │
│  │ │  ● KDF                                              │ │   │
│  │ │  ○ Scones                                           │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ On selection: Load mixes for selected product           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  STEP 3: SELECT MIX                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ Mix: [Dropdown - filtered by product]               │ │   │
│  │ │  ● KDF Mix 1 (Expected yield: 102)                  │ │   │
│  │ │  ○ KDF Mix 2 (Expected yield: 102)                  │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ On selection: Show ingredient preview                   │   │
│  │                                                         │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ INGREDIENT REQUIREMENTS:                            │ │   │
│  │ │ • Bakers Flour: 50 kg (Available: 150 kg) ✓         │ │   │
│  │ │ • Sugar: 2.5 kg (Available: 45 kg) ✓                │ │   │
│  │ │ • Cooking Oil: 7.5 L (Available: 30 L) ✓            │ │   │
│  │ │ • Salt: 0.3 kg (Available: 5 kg) ✓                  │ │   │
│  │ │ ...                                                 │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  STEP 4: ENTER PRODUCTION DETAILS                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ Quantity Produced: [___102___] units                │ │   │
│  │ │ (Expected: 102)                                     │ │   │
│  │ │                                                     │ │   │
│  │ │ Production Date: [2025-11-29] (default: today)      │ │   │
│  │ │                                                     │ │   │
│  │ │ Production Time: [08:30] (optional)                 │ │   │
│  │ │                                                     │ │   │
│  │ │ Notes: [_________________________________]          │ │   │
│  │ │        (optional)                                   │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  STEP 5: REVIEW COST PREVIEW                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ COST PREVIEW (based on current prices):             │ │   │
│  │ │                                                     │ │   │
│  │ │ Estimated Total Cost: KES 15,800.00                 │ │   │
│  │ │ Estimated Cost/Unit:  KES 154.90                    │ │   │
│  │ │                                                     │ │   │
│  │ │ ⚠️ Costs locked at submission time                  │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ [Cancel]                        [Submit Production]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  STEP 6: CONFIRMATION                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ ✓ PRODUCTION BATCH RECORDED SUCCESSFULLY            │ │   │
│  │ │                                                     │ │   │
│  │ │ Batch Number: PRD-20251129-001                      │ │   │
│  │ │ Product: KDF                                        │ │   │
│  │ │ Quantity: 102 units                                 │ │   │
│  │ │ Total Cost: KES 15,800.00                           │ │   │
│  │ │                                                     │ │   │
│  │ │ Current KDF Stock: 204 units                        │ │   │
│  │ │                                                     │ │   │
│  │ │ ⚠️ STOCK ALERTS:                                    │ │   │
│  │ │ • Cooking Oil: LOW (12.5 L remaining)               │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │                                                         │   │
│  │ [View Batch Details]    [Record Another]    [Dashboard] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Flow 2: View Production History

```
┌─────────────────────────────────────────────────────────────────┐
│              USER FLOW: VIEW PRODUCTION HISTORY                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: NAVIGATE                                               │
│  URL: /production/batches/                                      │
│                                                                 │
│  STEP 2: APPLY FILTERS (Optional)                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ From: [2025-11-01]  To: [2025-11-29]                    │   │
│  │ Product: [All ▼]    Produced By: [All ▼]                │   │
│  │ Search: [batch number...] [🔍]                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  STEP 3: BROWSE LIST                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Batch #       │ Product │ Qty  │ Date     │ Cost    │   │   │
│  │───────────────┼─────────┼──────┼──────────┼─────────┼───│   │
│  │ PRD-1129-003  │ Bread   │ 132  │ Nov 29   │ 4,667   │ → │   │
│  │ PRD-1129-002  │ Scones  │ 105  │ Nov 29   │ 8,200   │ → │   │
│  │ PRD-1129-001  │ KDF     │ 102  │ Nov 29   │ 15,800  │ → │   │
│  │ PRD-1128-005  │ Bread   │ 130  │ Nov 28   │ 4,550   │ → │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  STEP 4: CLICK ROW TO VIEW DETAILS                              │
│  → Navigates to /production/batches/<id>/                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4 Flow 3: View Stock Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│              USER FLOW: VIEW STOCK DASHBOARD                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  URL: /production/stock/                                        │
│                                                                 │
│  DISPLAY: PRODUCT STOCK CARDS                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │   BREAD     │  │    KDF      │  │   SCONES    │     │   │
│  │  │             │  │             │  │             │     │   │
│  │  │    264      │  │    204      │  │    315      │     │   │
│  │  │   units     │  │   units     │  │   units     │     │   │
│  │  │             │  │             │  │             │     │   │
│  │  │ Last: Today │  │ Last: Today │  │ Last: Yday  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  │                                                         │   │
│  │  Click card → View movements for that product           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  DISPLAY: RECENT MOVEMENTS                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Time  │ Product │ Type       │ Qty   │ Stock After     │   │
│  │───────┼─────────┼────────────┼───────┼─────────────────│   │
│  │ 08:30 │ Bread   │ Production │ +132  │ 264             │   │
│  │ 08:00 │ Bread   │ Production │ +132  │ 132             │   │
│  │ 07:30 │ KDF     │ Production │ +102  │ 204             │   │
│  │ 07:00 │ KDF     │ Production │ +102  │ 102             │   │
│  │ 06:30 │ Scones  │ Dispatch   │ -100  │ 315             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. VIEWS, ADMIN & UTILITIES SUMMARY

### 9.1 URL Configuration

```python
# apps/production/urls.py

from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Production Batches
    path('batches/', views.BatchListView.as_view(), name='batch_list'),
    path('batches/new/', views.BatchCreateView.as_view(), name='batch_create'),
    path('batches/<int:pk>/', views.BatchDetailView.as_view(), name='batch_detail'),
    
    # Product Stock
    path('stock/', views.StockDashboardView.as_view(), name='stock_dashboard'),
    path('stock/<int:product_id>/', views.StockDetailView.as_view(), name='stock_detail'),
    
    # API Endpoints (for HTMX/AJAX)
    path('api/mixes/', views.get_mixes_for_product, name='api_get_mixes'),
    path('api/mix-preview/', views.get_mix_preview, name='api_mix_preview'),
]
```

### 9.2 View Classes

| View | Type | URL | Purpose |
|------|------|-----|---------|
| DashboardView | TemplateView | `/production/` | Production summary dashboard |
| BatchListView | ListView | `/production/batches/` | Paginated batch history |
| BatchCreateView | CreateView | `/production/batches/new/` | Record new batch form |
| BatchDetailView | DetailView | `/production/batches/<id>/` | Batch details with snapshot |
| StockDashboardView | TemplateView | `/production/stock/` | Current stock levels |
| StockDetailView | DetailView | `/production/stock/<product>/` | Stock movements for product |

### 9.3 View Implementations

```python
# apps/production/views.py

from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy

from apps.products.models import Product, Mix
from .models import ProductionBatch, ProductStock, ProductStockMovement
from .services import ProductionService
from .forms import ProductionBatchForm


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Production dashboard showing today's summary.
    """
    template_name = 'production/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get today's production summary
        context['summary'] = ProductionService.get_production_summary()
        
        # Get current stock levels
        context['stocks'] = ProductStock.objects.select_related('product').all()
        
        # Get recent batches
        context['recent_batches'] = ProductionBatch.objects.select_related(
            'product', 'produced_by'
        ).order_by('-created_at')[:5]
        
        return context


class BatchListView(LoginRequiredMixin, ListView):
    """
    Paginated list of production batches with filters.
    """
    model = ProductionBatch
    template_name = 'production/batch_list.html'
    context_object_name = 'batches'
    paginate_by = 20
    ordering = ['-production_date', '-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'produced_by')
        
        # Apply filters
        product_id = self.request.GET.get('product')
        date_from = self.request.GET.get('from')
        date_to = self.request.GET.get('to')
        search = self.request.GET.get('search')
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if date_from:
            queryset = queryset.filter(production_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(production_date__lte=date_to)
        if search:
            queryset = queryset.filter(batch_number__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        return context


class BatchCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Create a new production batch.
    """
    template_name = 'production/batch_form.html'
    form_class = ProductionBatchForm
    permission_required = 'production.add_productionbatch'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        # Use service to create batch
        result = ProductionService.create_production_batch(
            mix_id=form.cleaned_data['mix'].id,
            quantity_produced=form.cleaned_data['quantity_produced'],
            production_date=form.cleaned_data['production_date'],
            user=self.request.user,
            production_time=form.cleaned_data.get('production_time'),
            notes=form.cleaned_data.get('notes', '')
        )
        
        if result['success']:
            messages.success(
                self.request,
                f"Production batch {result['data']['batch_number']} recorded successfully!"
            )
            
            # Show stock alerts if any
            for alert in result['data'].get('stock_alerts', []):
                messages.warning(
                    self.request,
                    f"⚠️ Low stock alert: {alert['item_name']} - {alert['current_stock']} remaining"
                )
            
            return redirect('production:batch_detail', pk=result['data']['batch'].id)
        else:
            messages.error(self.request, result['error'])
            return self.form_invalid(form)


class BatchDetailView(LoginRequiredMixin, DetailView):
    """
    View production batch details including ingredient snapshot.
    """
    model = ProductionBatch
    template_name = 'production/batch_detail.html'
    context_object_name = 'batch'
    
    def get_queryset(self):
        return super().get_queryset().select_related('product', 'mix', 'produced_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['deductions'] = self.object.ingredient_deductions.all()
        return context


class StockDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard showing current product stock levels.
    """
    template_name = 'production/stock_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stocks'] = ProductStock.objects.select_related('product').all()
        context['recent_movements'] = ProductStockMovement.objects.select_related(
            'product', 'recorded_by'
        ).order_by('-created_at')[:20]
        return context


# API Views for HTMX/AJAX

def get_mixes_for_product(request):
    """
    Return mixes for a product (for dynamic dropdown).
    """
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'mixes': []})
    
    mixes = Mix.objects.filter(
        product_id=product_id,
        is_active=True
    ).values('id', 'name', 'expected_yield')
    
    return JsonResponse({'mixes': list(mixes)})


def get_mix_preview(request):
    """
    Return ingredient preview for a mix.
    """
    mix_id = request.GET.get('mix_id')
    
    if not mix_id:
        return JsonResponse({'ingredients': []})
    
    try:
        availability = ProductionService.check_ingredient_availability(
            Mix.objects.prefetch_related('ingredients').get(id=mix_id)
        )
        return JsonResponse(availability)
    except Mix.DoesNotExist:
        return JsonResponse({'error': 'Mix not found'}, status=404)
```

### 9.4 Forms

```python
# apps/production/forms.py

from django import forms
from django.utils import timezone

from apps.products.models import Product, Mix
from .models import ProductionBatch


class ProductionBatchForm(forms.Form):
    """
    Form for recording a production batch.
    
    Note: We use a plain Form instead of ModelForm because
    the batch creation involves complex service logic.
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'product-select'})
    )
    
    mix = forms.ModelChoiceField(
        queryset=Mix.objects.none(),  # Populated dynamically
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'mix-select'})
    )
    
    quantity_produced = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    production_date = forms.DateField(
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    production_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If product is in data, filter mixes
        if 'product' in self.data:
            try:
                product_id = int(self.data.get('product'))
                self.fields['mix'].queryset = Mix.objects.filter(
                    product_id=product_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                pass
    
    def clean_production_date(self):
        date = self.cleaned_data['production_date']
        if date > timezone.now().date():
            raise forms.ValidationError("Production date cannot be in the future.")
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        mix = cleaned_data.get('mix')
        
        if product and mix:
            if mix.product_id != product.id:
                raise forms.ValidationError("Selected mix does not belong to selected product.")
        
        return cleaned_data
```

### 9.5 Admin Configuration

```python
# apps/production/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductionBatch, 
    BatchIngredientDeduction, 
    ProductStock, 
    ProductStockMovement
)


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    """
    Read-only admin for ProductionBatch (immutable records).
    """
    list_display = [
        'batch_number', 
        'product', 
        'quantity_produced', 
        'production_date',
        'total_ingredient_cost',
        'cost_per_unit',
        'produced_by'
    ]
    list_filter = ['product', 'production_date', 'produced_by']
    search_fields = ['batch_number', 'product__name']
    date_hierarchy = 'production_date'
    ordering = ['-production_date', '-created_at']
    
    readonly_fields = [
        'batch_number',
        'product',
        'mix',
        'mix_snapshot_display',
        'quantity_produced',
        'expected_yield',
        'yield_variance_display',
        'total_ingredient_cost',
        'cost_per_unit',
        'production_date',
        'production_time',
        'produced_by',
        'notes',
        'created_at',
    ]
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'product', 'mix', 'production_date', 'production_time')
        }),
        ('Yield', {
            'fields': ('quantity_produced', 'expected_yield', 'yield_variance_display')
        }),
        ('Costs', {
            'fields': ('total_ingredient_cost', 'cost_per_unit')
        }),
        ('Recipe Snapshot', {
            'fields': ('mix_snapshot_display',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('produced_by', 'notes', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        """Batches are created via service, not admin."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Batches are immutable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Batches cannot be deleted."""
        return False
    
    @admin.display(description='Yield Variance')
    def yield_variance_display(self, obj):
        variance = obj.yield_variance
        pct = obj.yield_variance_percentage
        color = 'green' if obj.is_within_acceptable_variance else 'red'
        sign = '+' if variance > 0 else ''
        return format_html(
            '<span style="color: {}">{}{} ({:.1f}%)</span>',
            color, sign, variance, pct
        )
    
    @admin.display(description='Mix Snapshot')
    def mix_snapshot_display(self, obj):
        import json
        return format_html(
            '<pre style="max-width: 600px; overflow: auto;">{}</pre>',
            json.dumps(obj.mix_snapshot, indent=2)
        )


@admin.register(BatchIngredientDeduction)
class BatchIngredientDeductionAdmin(admin.ModelAdmin):
    """
    Read-only admin for ingredient deductions (immutable).
    """
    list_display = [
        'batch',
        'item_name',
        'quantity_deducted',
        'unit',
        'unit_price_at_deduction',
        'line_cost'
    ]
    list_filter = ['inventory_item_id', 'batch__production_date']
    search_fields = ['batch__batch_number', 'item_name']
    
    readonly_fields = [
        'batch',
        'inventory_item_id',
        'item_name',
        'quantity_deducted',
        'unit',
        'unit_price_at_deduction',
        'line_cost',
        'stock_before',
        'stock_after',
        'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    """
    Admin for ProductStock - READ primarily, limited edits.
    """
    list_display = [
        'product',
        'current_stock',
        'last_production_date',
        'updated_at'
    ]
    list_filter = ['product']
    
    readonly_fields = [
        'product',
        'last_production_batch',
        'last_production_date',
        'created_at',
        'updated_at'
    ]
    
    # Only allow editing current_stock for corrections
    fields = [
        'product',
        'current_stock',
        'last_production_date',
        'last_production_batch',
        'updated_at'
    ]
    
    def has_add_permission(self, request):
        """Stock records created via seeding, not admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductStockMovement)
class ProductStockMovementAdmin(admin.ModelAdmin):
    """
    Read-only admin for stock movements (immutable audit trail).
    """
    list_display = [
        'product',
        'movement_type',
        'quantity',
        'stock_before',
        'stock_after',
        'recorded_by',
        'created_at'
    ]
    list_filter = ['product', 'movement_type', 'created_at']
    search_fields = ['product__name', 'reference_type']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = [
        'product',
        'movement_type',
        'quantity',
        'stock_before',
        'stock_after',
        'reference_type',
        'reference_id',
        'recorded_by',
        'notes',
        'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

### 9.6 Seeding Strategy

**Purpose:** Initialize ProductStock records for each active product.

```python
# apps/production/management/commands/seed_product_stock.py

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.products.models import Product
from apps.production.models import ProductStock


class Command(BaseCommand):
    help = 'Seed ProductStock records for all active products'
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding ProductStock records...')
        
        products = Product.objects.filter(is_active=True)
        created_count = 0
        existing_count = 0
        
        for product in products:
            stock, created = ProductStock.objects.get_or_create(
                product=product,
                defaults={'current_stock': 0}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Created stock for: {product.name}')
                )
            else:
                existing_count += 1
                self.stdout.write(
                    f'  Already exists: {product.name} ({stock.current_stock} units)'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Created: {created_count}, Already existed: {existing_count}'
            )
        )
```

**Seeding Order:**
```
1. Products App seeds first (creates Product records)
2. Production App seeds second (creates ProductStock for each Product)

Command sequence:
$ python manage.py seed_products      # Creates Bread, KDF, Scones
$ python manage.py seed_product_stock # Creates ProductStock for each
```

**Initial Stock Values:**

| Product | Initial Stock | Notes |
|---------|--------------|-------|
| Bread | 0 | No production yet |
| KDF | 0 | No production yet |
| Scones | 0 | No production yet |
| Bread Leftovers | 0 | Sub-product (created by Sales) |
| Scone Leftovers | 0 | Sub-product (created by Sales) |

---

## 10. KEY PRINCIPLES

### 10.1 Design Principles

| Principle | Application in Production App |
|-----------|-------------------------------|
| **CREATE-ONLY** | ProductionBatch, BatchIngredientDeduction, ProductStockMovement are immutable |
| **Atomic Transactions** | Batch creation is all-or-nothing (no partial batches) |
| **Snapshot Over Reference** | Mix data frozen in JSONField at batch time |
| **Row Locking** | ProductStock uses select_for_update() for concurrent access |
| **Single Responsibility** | Production records batches; Inventory handles stock alerts |
| **DRY** | Use Inventory utilities for deductions; don't duplicate logic |
| **Audit Trail** | Every stock change has a corresponding movement record |

### 10.2 Bank Ledger Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                   BANK LEDGER PHILOSOPHY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Traditional Database:        Bank Ledger (Our Approach):       │
│  ┌─────────────────┐         ┌─────────────────┐               │
│  │ UPDATE product  │         │ CREATE batch    │               │
│  │ SET stock = 100 │         │ quantity = +50  │               │
│  └─────────────────┘         │                 │               │
│                              │ CREATE batch    │               │
│  Problem: Lost history       │ quantity = +50  │               │
│                              └─────────────────┘               │
│                                                                 │
│                              Benefit: Complete                  │
│                              audit trail                        │
│                                                                 │
│  RULE: For transaction data (batches, movements):               │
│  - CREATE only                                                  │
│  - Never UPDATE                                                 │
│  - Never DELETE                                                 │
│  - Current state = SUM of all transactions                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.3 Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                 PRODUCTION APP BOUNDARIES                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ PRODUCTION OWNS:                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • ProductionBatch model and creation                     │   │
│  │ • BatchIngredientDeduction records                       │   │
│  │ • ProductStock current levels                            │   │
│  │ • ProductStockMovement audit trail                       │   │
│  │ • Batch number generation                                │   │
│  │ • Mix snapshot creation                                  │   │
│  │ • Cost calculation at batch time                         │   │
│  │ • Yield variance tracking                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ❌ PRODUCTION DOES NOT OWN:                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Product/Mix definitions (→ Products App)              │   │
│  │ • Raw ingredient stock levels (→ Inventory App)         │   │
│  │ • Stock alert creation (→ Inventory App utilities)      │   │
│  │ • Ingredient prices (→ Inventory App purchases)         │   │
│  │ • Dispatch/Sales (→ Sales App)                          │   │
│  │ • Leftover conversion (→ Sales App)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.4 Data Flow Direction

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA FLOW DIRECTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  READS FROM:                                                    │
│                                                                 │
│  Products ───────────────────────────────────────────▶ Production│
│  (Mix, MixIngredient)                           (get recipe)    │
│                                                                 │
│  Inventory ──────────────────────────────────────────▶ Production│
│  (ItemXXDetails)                          (get price, stock)    │
│                                                                 │
│  WRITES TO:                                                     │
│                                                                 │
│  Production ─────────────────────────────────────────▶ Inventory │
│  (create batch)                     (deduct via utility call)   │
│                                                                 │
│  Production ◀─────────────────────────────────────────── Sales  │
│  (ProductStock)                   (read stock for dispatch)     │
│                                                                 │
│  Production ◀─────────────────────────────────────────── Sales  │
│  (ProductStock)            (update stock via service call)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. VALIDATION RULES

### 11.1 Model-Level Validations

| Model | Field | Validation | Error Message |
|-------|-------|------------|---------------|
| ProductionBatch | batch_number | Unique, format PRD-YYYYMMDD-XXX | "Batch number already exists" |
| ProductionBatch | quantity_produced | > 0 | "Quantity must be positive" |
| ProductionBatch | production_date | Not future | "Production date cannot be in the future" |
| ProductionBatch | mix | is_active=True | "Cannot use inactive mix" |
| ProductionBatch | product | is_active=True | "Cannot produce inactive product" |
| BatchIngredientDeduction | quantity_deducted | > 0 | "Deduction must be positive" |
| ProductStock | current_stock | >= 0 | "Stock cannot be negative" |

### 11.2 Service-Level Validations

```python
# apps/production/validators.py

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_ingredient_availability(mix, raise_exception=True):
    """
    Validate that all ingredients are available.
    
    Args:
        mix: Mix object with prefetched ingredients
        raise_exception: If True, raise ValidationError
    
    Returns:
        dict with validation result
    """
    from apps.inventory.routing import get_item_details_model
    
    shortages = []
    
    for mi in mix.ingredients.all():
        DetailsModel = get_item_details_model(mi.inventory_item_id)
        details = DetailsModel.objects.get(pk=1)
        
        if details.current_stock < mi.quantity_required:
            shortages.append({
                'item': details.item_name,
                'required': mi.quantity_required,
                'available': details.current_stock,
                'shortage': mi.quantity_required - details.current_stock
            })
    
    if shortages and raise_exception:
        raise ValidationError({
            'ingredients': f"Insufficient stock for: {', '.join(s['item'] for s in shortages)}"
        })
    
    return {'valid': len(shortages) == 0, 'shortages': shortages}


def validate_production_date(date, raise_exception=True):
    """
    Validate production date.
    
    Rules:
    - Cannot be in the future
    - Cannot be more than 7 days in the past (optional restriction)
    """
    today = timezone.now().date()
    
    if date > today:
        if raise_exception:
            raise ValidationError("Production date cannot be in the future.")
        return {'valid': False, 'error': 'Future date'}
    
    # Optional: restrict backdating
    max_backdate = 7
    days_ago = (today - date).days
    
    if days_ago > max_backdate:
        if raise_exception:
            raise ValidationError(
                f"Production date cannot be more than {max_backdate} days in the past."
            )
        return {'valid': False, 'error': f'More than {max_backdate} days ago'}
    
    return {'valid': True}


def validate_quantity_produced(quantity, expected_yield, raise_exception=True):
    """
    Validate quantity produced against expected yield.
    
    Rules:
    - Must be positive
    - Warn if variance > 5%
    - Error if variance > 20% (likely data entry error)
    """
    if quantity <= 0:
        if raise_exception:
            raise ValidationError("Quantity produced must be positive.")
        return {'valid': False, 'error': 'Non-positive quantity'}
    
    variance_pct = abs((quantity - expected_yield) / expected_yield * 100)
    
    if variance_pct > 20:
        if raise_exception:
            raise ValidationError(
                f"Quantity variance ({variance_pct:.1f}%) is unusually high. "
                f"Expected around {expected_yield} units. Please verify."
            )
        return {'valid': False, 'error': f'Excessive variance: {variance_pct:.1f}%'}
    
    warnings = []
    if variance_pct > 5:
        warnings.append(f"High variance: {variance_pct:.1f}%")
    
    return {'valid': True, 'warnings': warnings}


def validate_mix_is_active(mix, raise_exception=True):
    """
    Validate that mix and its product are active.
    """
    if not mix.is_active:
        if raise_exception:
            raise ValidationError(f"Mix '{mix.name}' is not active.")
        return {'valid': False, 'error': 'Inactive mix'}
    
    if not mix.product.is_active:
        if raise_exception:
            raise ValidationError(f"Product '{mix.product.name}' is not active.")
        return {'valid': False, 'error': 'Inactive product'}
    
    return {'valid': True}
```

### 11.3 Yield Variance Thresholds

**Per business requirements from initial team meeting:**

| Product | Expected Yield | Acceptable Range | Variance |
|---------|----------------|------------------|----------|
| Bread | 132 units | 129-135 | ±2.3% |
| Scones | 102 units | 99-105 | ±3% |
| KDF | 102 units | 97-107 | ±5% |

**KDF has higher variance due to:**
- Frying process causes more variability
- Size variation more acceptable
- Historical data shows wider range

```python
# apps/production/validators.py

YIELD_VARIANCE_THRESHOLDS = {
    'default': {'warning': 5, 'error': 15},
    'BREAD': {'warning': 3, 'error': 10},
    'SCONES': {'warning': 4, 'error': 12},
    'KDF': {'warning': 6, 'error': 15},  # Higher tolerance
}

def get_variance_threshold(product_name: str) -> dict:
    """Get yield variance thresholds for a product."""
    name_upper = product_name.upper()
    return YIELD_VARIANCE_THRESHOLDS.get(
        name_upper, 
        YIELD_VARIANCE_THRESHOLDS['default']
    )
```

### 11.4 Stock Sufficiency Validation

```python
def validate_dispatch_stock(product_id: int, quantity: int):
    """
    Validate that sufficient stock exists for dispatch.
    Called by Sales app before creating dispatch.
    
    Args:
        product_id: Product to dispatch
        quantity: Quantity to dispatch
    
    Raises:
        ValidationError: If insufficient stock
    """
    from .models import ProductStock
    
    try:
        stock = ProductStock.objects.get(product_id=product_id)
    except ProductStock.DoesNotExist:
        raise ValidationError(f"No stock record for product {product_id}")
    
    if stock.current_stock < quantity:
        raise ValidationError(
            f"Insufficient stock. Available: {stock.current_stock}, "
            f"Requested: {quantity}"
        )
    
    return True
```

---

## 12. DECIMAL PRECISION & ROUNDING

### 12.1 Precision Rules

| Field Type | Precision | Django Field | Example |
|------------|-----------|--------------|---------|
| Quantities (ingredients) | 3 decimal places | `DecimalField(max_digits=10, decimal_places=3)` | 36.000 kg |
| Unit prices | 2 decimal places | `DecimalField(max_digits=10, decimal_places=2)` | 85.50 |
| Line costs | 2 decimal places | `DecimalField(max_digits=12, decimal_places=2)` | 3,078.00 |
| Cost per unit | 4 decimal places | `DecimalField(max_digits=10, decimal_places=4)` | 35.3535 |
| Totals | 2 decimal places | `DecimalField(max_digits=12, decimal_places=2)` | 12,500.00 |

### 12.2 Rounding Strategy

```python
# apps/production/utils.py

from decimal import Decimal, ROUND_HALF_UP

# Rounding constants
QUANTITY_PRECISION = Decimal('0.001')  # 3 decimal places
PRICE_PRECISION = Decimal('0.01')       # 2 decimal places
COST_PER_UNIT_PRECISION = Decimal('0.0001')  # 4 decimal places

def round_quantity(value):
    """Round quantity to 3 decimal places."""
    return Decimal(str(value)).quantize(QUANTITY_PRECISION, rounding=ROUND_HALF_UP)

def round_price(value):
    """Round price/cost to 2 decimal places."""
    return Decimal(str(value)).quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)

def round_cost_per_unit(value):
    """Round cost per unit to 4 decimal places."""
    return Decimal(str(value)).quantize(COST_PER_UNIT_PRECISION, rounding=ROUND_HALF_UP)

def calculate_line_cost(quantity, unit_price):
    """
    Calculate line cost with proper rounding.
    
    Formula: quantity × unit_price, rounded to 2 decimal places
    """
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    return (qty * price).quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)

def calculate_cost_per_unit(total_cost, quantity):
    """
    Calculate cost per unit with proper rounding.
    
    Formula: total_cost ÷ quantity, rounded to 4 decimal places
    """
    total = Decimal(str(total_cost))
    qty = Decimal(str(quantity))
    if qty == 0:
        return Decimal('0.0000')
    return (total / qty).quantize(COST_PER_UNIT_PRECISION, rounding=ROUND_HALF_UP)
```

### 12.3 JSON Serialization

```python
# When storing decimals in mix_snapshot (JSONField), convert to strings

def decimal_to_json(value):
    """Convert Decimal to string for JSON storage."""
    if isinstance(value, Decimal):
        return str(value)
    return value

# Example usage in mix snapshot
ingredient_data = {
    'quantity_required': str(round_quantity(qty)),           # "36.000"
    'unit_price_at_batch': str(round_price(price)),         # "85.50"
    'line_cost': str(round_price(line_cost))                # "3078.00"
}

# When reading from JSON, convert back to Decimal
def json_to_decimal(value):
    """Convert JSON string back to Decimal."""
    if isinstance(value, str):
        return Decimal(value)
    return Decimal(str(value))
```

---

## 13. TESTING

### 13.1 Test Structure

```
apps/production/tests/
├── __init__.py
├── test_models.py          # Model tests (immutability, properties)
├── test_services.py        # Service layer tests
├── test_views.py           # View tests (forms, responses)
├── test_validators.py      # Validation function tests
└── test_integration.py     # Cross-app integration tests
```

### 13.2 Model Tests

```python
# apps/production/tests/test_models.py

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.products.models import Product, Mix, MixIngredient
from apps.production.models import (
    ProductionBatch, 
    BatchIngredientDeduction,
    ProductStock,
    ProductStockMovement
)

User = get_user_model()


class ProductionBatchModelTests(TestCase):
    """Tests for ProductionBatch model."""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cls.product = Product.objects.create(
            name='Bread',
            description='Fresh bread',
            is_active=True
        )
        cls.mix = Mix.objects.create(
            product=cls.product,
            name='Bread Mix 1',
            expected_yield=132,
            is_active=True
        )
    
    def test_batch_creation(self):
        """Test creating a production batch."""
        batch = ProductionBatch(
            batch_number='PRD-20251129-001',
            product=self.product,
            mix=self.mix,
            mix_snapshot={
                'mix_id': self.mix.id,
                'mix_name': 'Bread Mix 1',
                'expected_yield': 132,
                'ingredients': [],
                'total_mix_cost': '0.00'
            },
            quantity_produced=132,
            expected_yield=132,
            total_ingredient_cost=Decimal('4666.60'),
            cost_per_unit=Decimal('35.3530'),
            production_date=timezone.now().date(),
            produced_by=self.user
        )
        batch.save(force_insert=True)
        
        self.assertIsNotNone(batch.id)
        self.assertEqual(batch.batch_number, 'PRD-20251129-001')
    
    def test_batch_immutability_update(self):
        """Test that batches cannot be updated."""
        batch = ProductionBatch.objects.create(
            batch_number='PRD-20251129-002',
            product=self.product,
            mix=self.mix,
            mix_snapshot={'ingredients': []},
            quantity_produced=132,
            expected_yield=132,
            total_ingredient_cost=Decimal('4666.60'),
            cost_per_unit=Decimal('35.3530'),
            production_date=timezone.now().date(),
            produced_by=self.user
        )
        
        # Attempt to update
        batch.quantity_produced = 140
        with self.assertRaises(ValueError) as context:
            batch.save()
        
        self.assertIn('immutable', str(context.exception))
    
    def test_batch_immutability_delete(self):
        """Test that batches cannot be deleted."""
        batch = ProductionBatch.objects.create(
            batch_number='PRD-20251129-003',
            product=self.product,
            mix=self.mix,
            mix_snapshot={'ingredients': []},
            quantity_produced=132,
            expected_yield=132,
            total_ingredient_cost=Decimal('4666.60'),
            cost_per_unit=Decimal('35.3530'),
            production_date=timezone.now().date(),
            produced_by=self.user
        )
        
        with self.assertRaises(ValueError) as context:
            batch.delete()
        
        self.assertIn('cannot be deleted', str(context.exception))
    
    def test_yield_variance_property(self):
        """Test yield variance calculation."""
        batch = ProductionBatch(
            quantity_produced=135,
            expected_yield=132
        )
        
        self.assertEqual(batch.yield_variance, 3)
        self.assertAlmostEqual(batch.yield_variance_percentage, 2.27, places=2)
    
    def test_acceptable_variance_bread(self):
        """Test acceptable variance for bread."""
        batch = ProductionBatch(
            quantity_produced=135,
            expected_yield=132
        )
        batch.product = self.product  # Bread
        
        # 2.27% variance should be within acceptable range
        self.assertTrue(batch.is_within_acceptable_variance)
    
    def test_unacceptable_variance(self):
        """Test unacceptable variance detection."""
        batch = ProductionBatch(
            quantity_produced=150,  # 13.6% over
            expected_yield=132
        )
        batch.product = self.product
        
        self.assertFalse(batch.is_within_acceptable_variance)


class ProductStockTests(TestCase):
    """Tests for ProductStock model."""
    
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name='Bread',
            is_active=True
        )
    
    def test_stock_creation(self):
        """Test creating product stock."""
        stock = ProductStock.objects.create(
            product=self.product,
            current_stock=0
        )
        
        self.assertEqual(stock.current_stock, 0)
    
    def test_stock_update(self):
        """Test that ProductStock CAN be updated (unlike batches)."""
        stock = ProductStock.objects.create(
            product=self.product,
            current_stock=100
        )
        
        stock.current_stock = 200
        stock.save()  # Should succeed
        
        stock.refresh_from_db()
        self.assertEqual(stock.current_stock, 200)


class BatchIngredientDeductionTests(TestCase):
    """Tests for BatchIngredientDeduction model."""
    
    def test_deduction_immutability(self):
        """Test that deduction records are immutable."""
        # Create required objects first
        user = User.objects.create_user(email='test@test.com', password='test')
        product = Product.objects.create(name='Bread', is_active=True)
        mix = Mix.objects.create(
            product=product, name='Mix 1', expected_yield=132, is_active=True
        )
        batch = ProductionBatch.objects.create(
            batch_number='PRD-TEST-001',
            product=product,
            mix=mix,
            mix_snapshot={},
            quantity_produced=132,
            expected_yield=132,
            total_ingredient_cost=Decimal('100.00'),
            cost_per_unit=Decimal('0.7576'),
            production_date=timezone.now().date(),
            produced_by=user
        )
        
        deduction = BatchIngredientDeduction.objects.create(
            batch=batch,
            inventory_item_id=1,
            item_name='Bakers Flour',
            quantity_deducted=Decimal('36.000'),
            unit='kg',
            unit_price_at_deduction=Decimal('85.50'),
            line_cost=Decimal('3078.00'),
            stock_before=Decimal('150.000'),
            stock_after=Decimal('114.000')
        )
        
        deduction.quantity_deducted = Decimal('40.000')
        with self.assertRaises(ValueError):
            deduction.save()
```

### 13.3 Service Tests

```python
# apps/production/tests/test_services.py

from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.products.models import Product, Mix, MixIngredient
from apps.production.services import ProductionService
from apps.production.models import ProductionBatch, ProductStock

User = get_user_model()


class ProductionServiceTests(TransactionTestCase):
    """Tests for ProductionService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.product = Product.objects.create(
            name='Bread',
            is_active=True
        )
        self.mix = Mix.objects.create(
            product=self.product,
            name='Bread Mix 1',
            expected_yield=132,
            is_active=True
        )
        # Add ingredients
        MixIngredient.objects.create(
            mix=self.mix,
            inventory_item_id=1,  # Flour
            quantity_required=Decimal('36.000')
        )
    
    def test_generate_batch_number_first_of_day(self):
        """Test batch number generation for first batch of day."""
        date = timezone.now().date()
        batch_number = ProductionService.generate_batch_number(date)
        
        expected = f"PRD-{date.strftime('%Y%m%d')}-001"
        self.assertEqual(batch_number, expected)
    
    def test_generate_batch_number_sequential(self):
        """Test batch numbers are sequential."""
        date = timezone.now().date()
        
        # Create first batch
        ProductionBatch.objects.create(
            batch_number=f"PRD-{date.strftime('%Y%m%d')}-001",
            product=self.product,
            mix=self.mix,
            mix_snapshot={},
            quantity_produced=132,
            expected_yield=132,
            total_ingredient_cost=Decimal('100'),
            cost_per_unit=Decimal('0.76'),
            production_date=date,
            produced_by=self.user
        )
        
        # Generate next
        batch_number = ProductionService.generate_batch_number(date)
        expected = f"PRD-{date.strftime('%Y%m%d')}-002"
        self.assertEqual(batch_number, expected)
    
    @patch('apps.production.services.deduct_ingredients_atomic')
    @patch('apps.production.services.get_item_details_model')
    def test_create_batch_success(self, mock_get_model, mock_deduct):
        """Test successful batch creation."""
        # Mock inventory interactions
        mock_details = MagicMock()
        mock_details.current_stock = Decimal('150.000')
        mock_details.last_purchase_unit_price = Decimal('85.50')
        mock_details.item_name = 'Bakers Flour'
        mock_details.unit = 'kg'
        
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_details
        mock_get_model.return_value = mock_model
        
        mock_deduct.return_value = {
            'success': True,
            'data': {
                'deductions': [
                    {
                        'item_id': 1,
                        'stock_before': Decimal('150.000'),
                        'stock_after': Decimal('114.000')
                    }
                ],
                'alerts': []
            }
        }
        
        # Create batch
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        self.assertTrue(result['success'])
        self.assertIn('batch', result['data'])
        self.assertEqual(result['data']['quantity_produced'], 132)
    
    @patch('apps.production.services.get_item_details_model')
    def test_create_batch_insufficient_stock(self, mock_get_model):
        """Test batch creation fails with insufficient stock."""
        # Mock insufficient stock
        mock_details = MagicMock()
        mock_details.current_stock = Decimal('10.000')  # Less than 36 needed
        mock_details.last_purchase_unit_price = Decimal('85.50')
        mock_details.item_name = 'Bakers Flour'
        mock_details.unit = 'kg'
        
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_details
        mock_get_model.return_value = mock_model
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        self.assertFalse(result['success'])
        self.assertIn('shortages', result)
    
    def test_create_batch_inactive_mix(self):
        """Test batch creation fails with inactive mix."""
        self.mix.is_active = False
        self.mix.save()
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        self.assertFalse(result['success'])
        self.assertIn('inactive', result['error'].lower())
```

### 13.4 Integration Tests

```python
# apps/production/tests/test_integration.py

from decimal import Decimal
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.products.models import Product, Mix, MixIngredient
from apps.inventory.models import Item01Details, Item01Transactions
from apps.production.services import ProductionService
from apps.production.models import (
    ProductionBatch, 
    BatchIngredientDeduction,
    ProductStock,
    ProductStockMovement
)

User = get_user_model()


class ProductionInventoryIntegrationTests(TransactionTestCase):
    """Integration tests between Production and Inventory apps."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create product and mix
        self.product = Product.objects.create(
            name='Bread',
            is_active=True
        )
        self.mix = Mix.objects.create(
            product=self.product,
            name='Bread Mix 1',
            expected_yield=132,
            is_active=True
        )
        MixIngredient.objects.create(
            mix=self.mix,
            inventory_item_id=1,
            quantity_required=Decimal('36.000')
        )
        
        # Set up inventory
        Item01Details.objects.create(
            item_name='Bakers Flour',
            unit='kg',
            current_stock=Decimal('150.000'),
            minimum_stock_level=Decimal('50.000'),
            last_purchase_unit_price=Decimal('85.50')
        )
    
    def test_batch_deducts_inventory(self):
        """Test that batch creation deducts from inventory."""
        initial_stock = Item01Details.objects.get(pk=1).current_stock
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        self.assertTrue(result['success'])
        
        # Check inventory was deducted
        new_stock = Item01Details.objects.get(pk=1).current_stock
        self.assertEqual(new_stock, initial_stock - Decimal('36.000'))
    
    def test_batch_creates_deduction_records(self):
        """Test that deduction audit records are created."""
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        batch = result['data']['batch']
        deductions = BatchIngredientDeduction.objects.filter(batch=batch)
        
        self.assertEqual(deductions.count(), 1)
        self.assertEqual(deductions[0].inventory_item_id, 1)
        self.assertEqual(deductions[0].quantity_deducted, Decimal('36.000'))
    
    def test_batch_updates_product_stock(self):
        """Test that product stock is updated."""
        # Ensure stock exists
        ProductStock.objects.create(product=self.product, current_stock=0)
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        stock = ProductStock.objects.get(product=self.product)
        self.assertEqual(stock.current_stock, 132)
    
    def test_batch_creates_stock_movement(self):
        """Test that stock movement record is created."""
        ProductStock.objects.create(product=self.product, current_stock=0)
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        movement = ProductStockMovement.objects.filter(
            product=self.product,
            movement_type='PRODUCTION'
        ).first()
        
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, 132)
        self.assertEqual(movement.stock_before, 0)
        self.assertEqual(movement.stock_after, 132)
    
    def test_transaction_rollback_on_failure(self):
        """Test that failed batch rolls back all changes."""
        initial_stock = Item01Details.objects.get(pk=1).current_stock
        initial_batch_count = ProductionBatch.objects.count()
        
        # Set stock to insufficient
        flour = Item01Details.objects.get(pk=1)
        flour.current_stock = Decimal('10.000')
        flour.save()
        
        result = ProductionService.create_production_batch(
            mix_id=self.mix.id,
            quantity_produced=132,
            production_date=timezone.now().date(),
            user=self.user
        )
        
        self.assertFalse(result['success'])
        
        # Verify no batch was created
        self.assertEqual(ProductionBatch.objects.count(), initial_batch_count)
        
        # Verify stock unchanged (was already 10)
        current = Item01Details.objects.get(pk=1).current_stock
        self.assertEqual(current, Decimal('10.000'))
```

---

## 14. IMPLEMENTATION CHECKLIST

### 14.1 Phase 1: Models & Migrations

- [ ] Create `apps/production/` app structure
- [ ] Implement `ProductionBatch` model with immutability enforcement
- [ ] Implement `BatchIngredientDeduction` model
- [ ] Implement `ProductStock` model
- [ ] Implement `ProductStockMovement` model
- [ ] Create and run migrations
- [ ] Configure Django admin (read-only for immutable models)
- [ ] Create `seed_product_stock` management command

### 14.2 Phase 2: Service Layer

- [ ] Implement `ProductionService.generate_batch_number()`
- [ ] Implement `ProductionService.validate_mix_availability()`
- [ ] Implement `ProductionService.check_ingredient_availability()`
- [ ] Implement `ProductionService.build_mix_snapshot()`
- [ ] Implement `ProductionService.create_production_batch()` (atomic)
- [ ] Implement `ProductionService.get_production_summary()`
- [ ] Implement `ProductionService.get_batch_details()`

### 14.3 Phase 3: Validators & Utils

- [ ] Implement `validators.py` with all validation functions
- [ ] Implement `utils.py` with helper functions
- [ ] Implement decimal precision utilities

### 14.4 Phase 4: Views & Forms

- [ ] Implement URL configuration
- [ ] Implement `DashboardView`
- [ ] Implement `BatchListView` with filters
- [ ] Implement `BatchCreateView` with form handling
- [ ] Implement `BatchDetailView`
- [ ] Implement `StockDashboardView`
- [ ] Implement `ProductionBatchForm`
- [ ] Implement API views for dynamic dropdowns

### 14.5 Phase 5: Templates

- [ ] Create `production/dashboard.html`
- [ ] Create `production/batch_list.html`
- [ ] Create `production/batch_form.html`
- [ ] Create `production/batch_detail.html`
- [ ] Create `production/stock_dashboard.html`
- [ ] Add JavaScript for dynamic form behavior (product → mix filtering)

### 14.6 Phase 6: Integration

- [ ] Test integration with Products app (Mix reading)
- [ ] Test integration with Inventory app (deductions)
- [ ] Verify stock alerts are triggered via Inventory utilities
- [ ] Prepare service methods for Sales app integration

### 14.7 Phase 7: Testing

- [ ] Write model tests (immutability, properties)
- [ ] Write service tests (all methods)
- [ ] Write validator tests
- [ ] Write view tests
- [ ] Write integration tests
- [ ] Achieve target test coverage (>80%)

### 14.8 Phase 8: Admin, Seeding & Deployment

- [ ] Test admin interface for all models
- [ ] Run `seed_product_stock` command
- [ ] Update admin documentation
- [ ] Create user guide for production recording
- [ ] Deploy and verify on Railway

---

## DOCUMENT CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial complete specification |

---

**END OF DOCUMENT**
