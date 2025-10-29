"""
Products App Models
Manages product catalog, mixes, and recipes for Chesanto Bakery
"""
from django.db import models
from django.conf import settings


class Product(models.Model):
    """
    Main product catalog (Bread, KDF, Scones, etc.)
    Super Admin can add/edit products dynamically
    """
    # Basic Information
    name = models.CharField(max_length=100, help_text="Product name (e.g., Bread, KDF, Scones)")
    alias = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Unit alias (e.g., 'Loaves' for Bread, 'Pieces' for KDF)"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Soft delete - preserves historical data")
    
    # Output Characteristics
    has_variable_output = models.BooleanField(
        default=False, 
        help_text="True for KDF (hand-cut, variable), False for machine-weighed products"
    )
    baseline_output = models.IntegerField(
        help_text="Expected units per mix (e.g., 132 for Bread, 107 for KDF)"
    )
    min_expected_output = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Minimum output for variable products (e.g., 98 for KDF)"
    )
    max_expected_output = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Maximum output for variable products (e.g., 107 for KDF)"
    )
    
    # Packaging
    units_per_packet = models.IntegerField(
        default=1, 
        help_text="Units per packet (Bread=1, KDF=12, Scones=12)"
    )
    packet_label = models.CharField(
        max_length=50, 
        default="packet", 
        help_text="Label for packet (e.g., 'dozen', 'loaf', 'packet')"
    )
    
    # Pricing (KES - Kenyan Shillings)
    price_per_packet = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Selling price per packet in KES"
    )
    
    # Sub-Product Support (e.g., Bread Rejects)
    has_sub_product = models.BooleanField(
        default=False, 
        help_text="True if this product has rejects/sub-products"
    )
    sub_product_name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Name of sub-product (e.g., 'Bread Rejects')"
    )
    sub_product_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Selling price for sub-product in KES (e.g., KES 50 for Bread Rejects)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products_updated'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return f"{self.name} ({self.alias or 'packet'})"


class Ingredient(models.Model):
    """
    Master ingredients table - links to InventoryItem
    Used in mix recipes
    """
    name = models.CharField(max_length=200, help_text="Ingredient name (e.g., Wheat Flour, Yeast)")
    description = models.TextField(blank=True)
    
    default_unit = models.CharField(
        max_length=20,
        choices=[
            ('g', 'Grams'),
            ('kg', 'Kilograms'),
            ('ml', 'Milliliters'),
            ('l', 'Liters'),
            ('pcs', 'Pieces'),
        ],
        help_text="Default unit for recipes"
    )
    
    # Link to inventory for cost tracking
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem', 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Linked inventory item for cost tracking"
    )
    
    is_active = models.BooleanField(default=True, help_text="Soft delete")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ingredients_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ingredients_updated'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Ingredient"
        verbose_name_plural = "Ingredients"
    
    def __str__(self):
        return f"{self.name} ({self.get_default_unit_display()})"


class Mix(models.Model):
    """
    Recipe for each product with ingredient list
    Supports versioning for recipe changes
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='mixes',
        help_text="Product this mix produces"
    )
    name = models.CharField(
        max_length=200, 
        help_text="Mix name (e.g., 'Standard Bread Mix', 'Mix 1')"
    )
    version = models.IntegerField(
        default=1, 
        help_text="Track recipe changes (increment on modifications)"
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Only one active mix per product recommended"
    )
    
    # Expected Yield
    expected_packets = models.IntegerField(
        help_text="How many packets this mix produces (e.g., 132 for Bread Mix 1)"
    )
    
    # Costs (auto-calculated from ingredients)
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="🤖 AUTO: Sum of all MixIngredients costs"
    )
    cost_per_packet = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="🤖 AUTO: total_cost / expected_packets"
    )
    
    notes = models.TextField(blank=True, help_text="Preparation notes or special instructions")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='mixes_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='mixes_updated'
    )
    
    class Meta:
        ordering = ['product__name', '-version']
        verbose_name = "Mix (Recipe)"
        verbose_name_plural = "Mixes (Recipes)"
        unique_together = ['product', 'name', 'version']
    
    def __str__(self):
        return f"{self.product.name} - {self.name} (v{self.version})"
    
    def calculate_costs(self):
        """
        Calculate total_cost and cost_per_packet from ingredients
        Called after MixIngredient changes
        """
        self.total_cost = sum(
            mix_ingredient.ingredient_cost 
            for mix_ingredient in self.mixingredient_set.all()
        )
        if self.expected_packets > 0:
            self.cost_per_packet = self.total_cost / self.expected_packets
        else:
            self.cost_per_packet = 0
        self.save()


class MixIngredient(models.Model):
    """
    Individual ingredients in a mix with quantities
    Costs auto-calculated from Inventory
    """
    mix = models.ForeignKey(
        Mix, 
        on_delete=models.CASCADE, 
        related_name='mixingredient_set',
        help_text="Parent mix"
    )
    ingredient = models.ForeignKey(
        Ingredient, 
        on_delete=models.PROTECT,
        help_text="Ingredient from master list"
    )
    
    # Quantity (manual entry)
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3,
        help_text="✏️ MANUAL: Amount needed (e.g., 36.000 for Bread flour)"
    )
    unit = models.CharField(
        max_length=20,
        choices=[
            ('g', 'Grams'),
            ('kg', 'Kilograms'),
            ('ml', 'Milliliters'),
            ('l', 'Liters'),
            ('pcs', 'Pieces'),
        ],
        help_text="✏️ MANUAL: Unit for this ingredient"
    )
    
    # Cost (auto-calculated from Inventory)
    ingredient_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="🤖 AUTO: quantity × Inventory cost_per_recipe_unit"
    )
    
    # Metadata
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="User who added this ingredient to the mix"
    )
    
    class Meta:
        ordering = ['ingredient__name']
        verbose_name = "Mix Ingredient"
        verbose_name_plural = "Mix Ingredients"
        unique_together = ['mix', 'ingredient']
    
    def __str__(self):
        return f"{self.ingredient.name}: {self.quantity} {self.unit}"
    
    def calculate_cost(self):
        """
        Calculate ingredient_cost from linked InventoryItem
        Auto-pulls cost_per_recipe_unit from Inventory
        """
        if self.ingredient.inventory_item:
            inventory = self.ingredient.inventory_item
            
            # Convert units if necessary
            if self.unit == inventory.recipe_unit:
                # Direct match - no conversion needed
                cost_per_unit = inventory.cost_per_recipe_unit
            elif self.unit == 'kg' and inventory.recipe_unit == 'g':
                # Convert kg to g (1kg = 1000g)
                cost_per_unit = inventory.cost_per_recipe_unit * 1000
            elif self.unit == 'g' and inventory.recipe_unit == 'kg':
                # Convert g to kg (1g = 0.001kg)
                cost_per_unit = inventory.cost_per_recipe_unit / 1000
            elif self.unit == 'l' and inventory.recipe_unit == 'ml':
                # Convert L to mL (1L = 1000mL)
                cost_per_unit = inventory.cost_per_recipe_unit * 1000
            elif self.unit == 'ml' and inventory.recipe_unit == 'l':
                # Convert mL to L (1mL = 0.001L)
                cost_per_unit = inventory.cost_per_recipe_unit / 1000
            else:
                # Units match or no conversion rule - use as is
                cost_per_unit = inventory.cost_per_recipe_unit
            
            # Calculate total cost for this ingredient
            self.ingredient_cost = self.quantity * cost_per_unit
        else:
            # No inventory link - keep cost at 0
            self.ingredient_cost = 0
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate cost"""
        self.calculate_cost()
        super().save(*args, **kwargs)
        # Update parent Mix costs
        self.mix.calculate_costs()
