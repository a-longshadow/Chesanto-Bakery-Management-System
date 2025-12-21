"""
Production App - Data Models

This module defines:
- ProductionBatch: Immutable production batch record
- BatchIngredientDeduction: Audit trail of ingredient deductions
- ProductStock: Current finished goods stock levels
- ProductStockMovement: Audit trail of stock changes

CRITICAL: ProductionBatch and BatchIngredientDeduction are CREATE-ONLY.
They follow the bank ledger philosophy - no updates, no deletes.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


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
        'products.Product',
        on_delete=models.PROTECT,
        related_name='production_batches',
        help_text="The product being produced"
    )
    
    # === MIX REFERENCE (for lookup only) ===
    mix = models.ForeignKey(
        'products.Mix',
        on_delete=models.PROTECT,
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
    
    expected_yield = models.PositiveIntegerField(
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
        if 'KDF' in self.product.name.upper():
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
        'products.Product',
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
        related_name='+',
        help_text="Reference to most recent batch"
    )
    
    class Meta:
        db_table = 'product_stock'
        verbose_name = 'Product Stock'
        verbose_name_plural = 'Product Stocks'
    
    def __str__(self):
        return f"{self.product.name}: {self.current_stock} units"


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
        WASTE = 'WASTE', 'Waste disposal'
    
    product = models.ForeignKey(
        'products.Product',
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


class WasteLog(TimeStampedModel):
    """
    Immutable record of product waste for P&L tracking.
    
    CREATE-ONLY - follows bank ledger philosophy.
    Records all disposed products with valuation for loss reporting.
    """
    
    class Source(models.TextChoices):
        SALES_RETURN = 'SALES_RETURN', 'Stale Leftovers'
        BAKERY_STOCK = 'BAKERY_STOCK', 'Expired in Bakery'
    
    waste_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Format: WST-YYYYMMDD-XXX"
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='waste_records',
        help_text="Product that was disposed"
    )
    
    quantity = models.PositiveIntegerField(
        help_text="Number of units disposed"
    )
    
    unit_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Product selling price at disposal time"
    )
    
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity × unit_value (P&L expense)"
    )
    
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        db_index=True,
        help_text="Where the waste originated"
    )
    
    reason = models.CharField(
        max_length=100,
        help_text="Reason for disposal (e.g., Stale, Mold, Damaged)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )
    
    disposal_date = models.DateField(
        db_index=True,
        help_text="Date when waste was disposed"
    )
    
    disposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='waste_disposed',
        help_text="User who recorded the disposal"
    )
    
    class Meta:
        db_table = 'waste_log'
        ordering = ['-disposal_date', '-created_at']
        indexes = [
            models.Index(fields=['disposal_date', 'product']),
            models.Index(fields=['source', 'disposal_date']),
        ]
        verbose_name = 'Waste Log'
        verbose_name_plural = 'Waste Logs'
    
    def __str__(self):
        return f"{self.waste_number} - {self.product.name} ({self.quantity} units)"
    
    def save(self, *args, **kwargs):
        """Enforce CREATE-ONLY behavior."""
        if self.pk:
            raise ValueError("WasteLog records are immutable.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bank ledger policy."""
        raise ValueError("WasteLog records cannot be deleted.")
