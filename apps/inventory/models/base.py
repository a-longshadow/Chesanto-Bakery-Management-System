"""
Inventory App - Abstract Base Models
Bank-ledger approach: ACID-compliant, immutable purchase/output records

These abstract classes define all fields completely.
Concrete models inherit from these and only add Meta configuration.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP


class BaseItemDetails(models.Model):
    """
    Abstract base for all Item Details models (singleton per item).
    
    Stores current stock state and last purchase price.
    This is the ONLY mutable table for each item - updated by purchases/outputs.
    
    Note: No 'category' field - ingredient vs indirect cost is determined by
    presence in ITEM_OUTPUTS_MODELS routing dictionary (items 16-23 have outputs)
    """
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('L', 'Liters'),
        ('units', 'Units'),
        ('tokens', 'Tokens'),
    ]
    
    name = models.CharField(
        max_length=200,
        help_text="Display name for this inventory item (can be updated)"
    )
    unit_of_measure = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        help_text="Standard unit for measuring this item"
    )
    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000'))],
        help_text="Current stock level in standard units"
    )
    last_purchase_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Unit price from most recent purchase (used for Production costing)"
    )
    last_purchase_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When last purchase was recorded"
    )
    minimum_stock_level = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        validators=[MinValueValidator(Decimal('0.0000'))],
        help_text="Threshold for low stock alerts"
    )
    current_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text="Auto-calculated: current_stock × last_purchase_unit_price"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="User who created this item record"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
        help_text="User who last updated this item"
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Auto-calculate current_value before saving"""
        raw_value = self.current_stock * self.last_purchase_unit_price
        self.current_value = raw_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate stock cannot be negative"""
        if self.current_stock < Decimal('0.0000'):
            raise ValidationError({'current_stock': "Stock cannot be negative"})
    
    def __str__(self):
        return f"{self.name}: {self.current_stock} {self.unit_of_measure}"
    
    @property
    def is_low_stock(self):
        """Check if current stock is below minimum level"""
        return self.current_stock < self.minimum_stock_level
    
    @property
    def is_out_of_stock(self):
        """Check if current stock is zero or negative"""
        return self.current_stock <= Decimal('0.0000')


class BaseItemPurchases(models.Model):
    """
    Abstract base for all Item Purchases models (immutable ledger).
    
    Bank-ledger model: CREATE ONLY - no updates, no deletes after creation.
    Each purchase record is permanent and forms the audit trail.
    """
    purchase_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique identifier"
    )
    supplier_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional vendor/supplier name"
    )
    purchase_date = models.DateField(
        help_text="Date of purchase (not future, max 1 month backdating)"
    )
    quantity_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Amount purchased in standard units (must be > 0)"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Price per unit at purchase time (must be > 0)"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
        help_text="Auto-calculated: quantity × unit_price"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional purchase notes"
    )
    
    # Audit fields (immutable)
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="User who created this purchase record"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Immutable timestamp of record creation"
    )
    
    class Meta:
        abstract = True
        ordering = ['-purchase_date', '-created_at']
    
    def save(self, *args, **kwargs):
        """
        Enforce immutability and auto-calculate total_cost.
        
        IMPORTANT: This method raises ValidationError if called on existing record.
        Purchases are CREATE ONLY - no modifications allowed.
        """
        # Enforce immutability - no updates allowed
        if self.pk:
            raise ValidationError("Purchases cannot be modified after creation. "
                                "This is a bank-ledger model - CREATE ONLY.")
        
        # Auto-calculate total_cost with proper rounding
        self.total_cost = (self.quantity_purchased * self.unit_price).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - immutable ledger"""
        raise ValidationError("Purchases cannot be deleted. "
                            "This is a bank-ledger model - audit trail must be preserved.")
    
    def __str__(self):
        return f"{self.purchase_number}: {self.quantity_purchased} @ {self.unit_price}"


class BaseItemOutputs(models.Model):
    """
    Abstract base for Item Outputs models (indirect costs only, immutable).
    
    Used ONLY for indirect cost items (16-23): Crates, Packaging, Diesel, 
    Firewood, Fuel Bolero, Electricity, Fuel for Transport Trucks, Hair Nets.
    
    Ingredients (1-15) are tracked via Production app, not via outputs table.
    
    Bank-ledger model: CREATE ONLY - no updates, no deletes.
    """
    output_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique identifier"
    )
    consumption_date = models.DateField(
        help_text="Date of consumption entry (not future, max 1 month backdating)"
    )
    quantity_consumed = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Amount consumed in standard units (must be > 0)"
    )
    date_range_start = models.DateField(
        null=True,
        blank=True,
        help_text="Optional: Period start for consumption reporting"
    )
    date_range_end = models.DateField(
        null=True,
        blank=True,
        help_text="Optional: Period end for consumption reporting"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional memo (e.g., 'Fuel for bread production week 1')"
    )
    
    # Audit fields (immutable)
    consumed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
        help_text="User who created this output record"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Immutable timestamp of record creation"
    )
    
    class Meta:
        abstract = True
        ordering = ['-consumption_date', '-created_at']
    
    def save(self, *args, **kwargs):
        """
        Enforce immutability.
        
        IMPORTANT: This method raises ValidationError if called on existing record.
        Outputs are CREATE ONLY - no modifications allowed.
        """
        # Enforce immutability - no updates allowed
        if self.pk:
            raise ValidationError("Outputs cannot be modified after creation. "
                                "This is a bank-ledger model - CREATE ONLY.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - immutable ledger"""
        raise ValidationError("Outputs cannot be deleted. "
                            "This is a bank-ledger model - audit trail must be preserved.")
    
    def __str__(self):
        return f"{self.output_number}: {self.quantity_consumed} consumed"
