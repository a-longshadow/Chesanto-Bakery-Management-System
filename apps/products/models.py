"""
Products App - Models
Master catalog of bakery products and their recipes (mixes).

Models:
- Product: Master catalog of bakery products
- Mix: Recipe definition for a product
- MixIngredient: Through-table linking Mix → Inventory items

Key Design Decisions:
- Standard Django models (not per-item tables like Inventory)
- IntegerField for inventory_item_id (routes to Inventory app)
- Soft-delete pattern (is_active flag, no hard deletes)
- One active mix per product constraint
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Product(models.Model):
    """
    Master catalog of bakery products.
    
    Supports sub-products via self-referential FK for quality tiers.
    Example: Bread (parent) → Bread Leftovers (child)
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Product name (e.g., 'Bread', 'Scones', 'KDF')"
    )
    
    parent_product = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sub_products',
        help_text="Parent product for quality tiers (e.g., Bread Leftovers → Bread)"
    )
    
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Current selling price per packet/unit (KES)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional product description"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False = archived, not available for new production"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='products_created'
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='products_updated'
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_active else "✗ archived"
        return f"{self.name} (KES {self.selling_price}) [{status}]"
    
    def archive(self, user):
        """Soft delete - set is_active=False"""
        self.is_active = False
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def restore(self, user):
        """Restore archived product"""
        self.is_active = True
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def get_active_mix(self):
        """Get the active mix for this product, or None"""
        return self.mixes.filter(is_active=True).first()
    
    @property
    def has_active_mix(self):
        """Check if product has an active recipe"""
        return self.mixes.filter(is_active=True).exists()
    
    @property
    def is_sub_product(self):
        """Check if this is a sub-product (has parent)"""
        return self.parent_product is not None


class Mix(models.Model):
    """
    Recipe for producing a product.
    
    Each product has ONE active mix at a time.
    Mixes can be edited in place (no versioning).
    Production app SNAPSHOTS mix data at batch creation time.
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='mixes',
        help_text="Which product this recipe produces"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Recipe name (e.g., 'Bread Mix Standard')"
    )
    
    expected_yield = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1'))],
        help_text="Expected packets/units produced per mix"
    )
    
    is_fixed_yield = models.BooleanField(
        default=True,
        help_text="True = machine-weighed (exact), False = hand-cut (variable)"
    )
    
    yield_variance_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('1'))],
        help_text="Minimum expected yield (for variable yield products)"
    )
    
    yield_variance_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('1'))],
        help_text="Maximum expected yield (for variable yield products)"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Only ONE active mix per product"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Recipe notes, special instructions"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='mixes_created'
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mixes_updated'
    )
    
    class Meta:
        verbose_name_plural = "Mixes"
        ordering = ['product__name', 'name']
        constraints = [
            # Only one active mix per product
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_active=True),
                name='unique_active_mix_per_product'
            ),
        ]
    
    def __str__(self):
        status = "✓ Active" if self.is_active else "✗ Archived"
        yield_info = f"{self.expected_yield} units"
        if not self.is_fixed_yield:
            yield_info = f"{self.yield_variance_min}-{self.yield_variance_max} units (variable)"
        return f"{self.name} [{status}] → {yield_info}"
    
    def archive(self, user):
        """Soft delete - set is_active=False"""
        self.is_active = False
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def restore(self, user):
        """
        Restore archived mix.
        Note: Will fail if product already has another active mix.
        """
        self.is_active = True
        self.updated_by = user
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def get_snapshot_data(self):
        """
        Get mix data for snapshot at batch creation time.
        Returns dict (not model instance) for loose coupling with Production app.
        """
        return {
            'mix_id': self.id,
            'mix_name': self.name,
            'expected_yield': str(self.expected_yield),
            'is_fixed_yield': self.is_fixed_yield,
            'yield_variance_min': str(self.yield_variance_min) if self.yield_variance_min else None,
            'yield_variance_max': str(self.yield_variance_max) if self.yield_variance_max else None,
            'ingredients': [
                {
                    'inventory_item_id': ing.inventory_item_id,
                    'quantity_required': str(ing.quantity_required),
                    'unit_of_measure': ing.unit_of_measure,
                    'item_name': ing.get_inventory_item_name(),
                }
                for ing in self.ingredients.all()
            ]
        }
    
    @property
    def total_ingredients_count(self):
        """Count of ingredients in this mix"""
        return self.ingredients.count()
    
    def clean(self):
        """Validate mix data"""
        from django.core.exceptions import ValidationError
        
        # Variable yield products must have variance range
        if not self.is_fixed_yield:
            if not self.yield_variance_min or not self.yield_variance_max:
                raise ValidationError(
                    "Variable yield products must have min and max variance values."
                )
            if self.yield_variance_min >= self.yield_variance_max:
                raise ValidationError(
                    "Minimum variance must be less than maximum variance."
                )


class MixIngredient(models.Model):
    """
    Links a Mix to Inventory items with required quantities.
    
    Uses IntegerField for inventory_item_id (1-23) which routes
    to the appropriate per-item inventory table at runtime.
    
    Example: inventory_item_id=1 → Flour Type 1 table
             inventory_item_id=17 → Packaging table
    
    Category (ingredient vs indirect cost) is DERIVED from ID:
    - Items 1-15 = Ingredients (deducted by Production)
    - Items 16-23 = Indirect Costs (manual tracking)
    """
    
    mix = models.ForeignKey(
        Mix,
        on_delete=models.CASCADE,  # Delete ingredients if mix deleted
        related_name='ingredients',
        help_text="Which recipe this ingredient belongs to"
    )
    
    # ROUTING FIELD - maps to Inventory per-item tables
    inventory_item_id = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(23)
        ],
        help_text="ID mapping to inventory item (1-23). See inventory routing."
    )
    
    quantity_required = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Amount needed per mix in base units"
    )
    
    unit_of_measure = models.CharField(
        max_length=20,
        help_text="Base unit (kg, L, units) - must match inventory item"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Special instructions (e.g., 'sifted flour')"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['inventory_item_id']
        constraints = [
            # Each ingredient appears once per mix
            models.UniqueConstraint(
                fields=['mix', 'inventory_item_id'],
                name='unique_ingredient_per_mix'
            ),
        ]
    
    def __str__(self):
        return f"{self.get_inventory_item_name()} ({self.quantity_required} {self.unit_of_measure})"
    
    def get_inventory_item_name(self):
        """Get human-readable name from Inventory routing"""
        try:
            from apps.inventory.routing import get_item_name
            return get_item_name(self.inventory_item_id)
        except (ImportError, ValueError):
            return f"Item #{self.inventory_item_id}"
    
    def get_inventory_item_unit(self):
        """Get standard unit from Inventory routing"""
        try:
            from apps.inventory.routing import get_item_unit
            return get_item_unit(self.inventory_item_id)
        except (ImportError, ValueError):
            return self.unit_of_measure
    
    def is_ingredient(self):
        """Check if this is a direct ingredient (items 1-15)"""
        try:
            from apps.inventory.routing import is_ingredient
            return is_ingredient(self.inventory_item_id)
        except ImportError:
            return 1 <= self.inventory_item_id <= 15
    
    def is_indirect_cost(self):
        """Check if this is an indirect cost (items 16-23)"""
        try:
            from apps.inventory.routing import is_indirect_cost
            return is_indirect_cost(self.inventory_item_id)
        except ImportError:
            return 16 <= self.inventory_item_id <= 23
    
    @property
    def category(self):
        """Get derived category: INGREDIENT or INDIRECT_COST"""
        return 'INGREDIENT' if self.is_ingredient() else 'INDIRECT_COST'
