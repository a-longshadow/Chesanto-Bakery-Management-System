"""
Inventory App Models
Manages ingredients, stock, purchases, and restocking for Chesanto Bakery
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class ExpenseCategory(models.Model):
    """
    5 expense categories for inventory items
    """
    CATEGORY_CHOICES = [
        ('RAW_MATERIALS', 'Raw Materials'),
        ('PACKAGING', 'Packaging'),
        ('FUEL_ENERGY', 'Fuel & Energy'),
        ('CONSUMABLES', 'Consumables'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='expense_categories_created'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
    
    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """
    37 inventory items with smart alerts
    Master item list for purchasing and tracking
    """
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('l', 'Liters'),
        ('ml', 'Milliliters'),
        ('pcs', 'Pieces'),
        ('bag', 'Bag'),
        ('jerycan', 'Jerycan'),
        ('packet', 'Packet'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200, unique=True, help_text="Item name (e.g., Wheat Flour)")
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='items',
        help_text="Expense category"
    )
    description = models.TextField(blank=True)
    
    # Units & Purchasing
    purchase_unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        help_text="Unit for purchasing (e.g., 'bag' for 50kg bag)"
    )
    recipe_unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        help_text="Unit for recipes (e.g., 'kg')"
    )
    conversion_factor = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        help_text="Convert purchase_unit to recipe_unit (e.g., 50 for 50kg bag)"
    )
    
    # Stock Tracking
    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Current stock in recipe_unit"
    )
    reorder_level = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Alert when stock falls below this (7 days supply)"
    )
    
    # Costing
    cost_per_purchase_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Cost per purchase_unit in KES (e.g., KES 3,650 per 50kg bag)"
    )
    cost_per_recipe_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="🤖 AUTO: cost_per_purchase_unit / conversion_factor"
    )
    
    # Alerts
    low_stock_alert = models.BooleanField(
        default=False,
        help_text="🤖 AUTO: True if current_stock < reorder_level"
    )
    days_remaining = models.IntegerField(
        default=0,
        help_text="🤖 AUTO: Calculated from usage rate"
    )
    
    is_active = models.BooleanField(default=True, help_text="Soft delete")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_items_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_items_updated'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
    
    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.recipe_unit})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate cost_per_recipe_unit and low_stock_alert"""
        if self.conversion_factor > 0:
            self.cost_per_recipe_unit = self.cost_per_purchase_unit / self.conversion_factor
        self.low_stock_alert = self.current_stock < self.reorder_level
        super().save(*args, **kwargs)


class Supplier(models.Model):
    """
    Supplier management for purchases
    """
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    # Payment Terms
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., 'Net 30 days', 'Cash on delivery'"
    )
    
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='suppliers_created'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
    
    def __str__(self):
        return self.name


class Purchase(models.Model):
    """
    Purchase orders for inventory items
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Purchase Information
    purchase_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated: PUR-YYYYMMDD-XXX"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases'
    )
    purchase_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # Totals (calculated from PurchaseItems)
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="🤖 AUTO: Sum of all purchase items"
    )
    
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchases_created'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='purchases_updated'
    )
    
    class Meta:
        ordering = ['-purchase_date']
        verbose_name = "Purchase"
        verbose_name_plural = "Purchases"
    
    def __str__(self):
        return f"{self.purchase_number} - {self.supplier.name} (KES {self.total_amount})"
    
    def save(self, *args, **kwargs):
        """Auto-generate purchase_number if not set"""
        if not self.purchase_number:
            from datetime import date
            today = date.today()
            date_str = today.strftime('%Y%m%d')
            
            # Get count of purchases today
            today_count = Purchase.objects.filter(
                purchase_number__startswith=f'PUR-{date_str}'
            ).count()
            
            # Generate purchase number: PUR-YYYYMMDD-001
            self.purchase_number = f'PUR-{date_str}-{(today_count + 1):03d}'
        
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """Calculate total from purchase items"""
        self.total_amount = sum(
            item.total_cost for item in self.purchaseitem_set.all()
        )
        self.save()


class PurchaseItem(models.Model):
    """
    Individual items in a purchase order
    """
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='purchaseitem_set'
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='purchase_items'
    )
    
    # Quantities
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Quantity in purchase_unit"
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Cost per purchase_unit in KES"
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="🤖 AUTO: quantity × unit_cost"
    )
    
    # Metadata
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['item__name']
        verbose_name = "Purchase Item"
        verbose_name_plural = "Purchase Items"
        unique_together = ['purchase', 'item']
    
    def __str__(self):
        return f"{self.item.name}: {self.quantity} {self.item.purchase_unit}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate total_cost"""
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        
        # Note: Stock update is handled by Purchase signal when status = RECEIVED
        # This avoids duplicate updates
        
        # Update parent purchase total
        self.purchase.calculate_total()


class StockMovement(models.Model):
    """
    Audit trail for all stock changes
    """
    MOVEMENT_TYPE_CHOICES = [
        ('PURCHASE', 'Purchase Receipt'),
        ('PRODUCTION', 'Production Usage'),
        ('DAMAGE', 'Damage/Wastage'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('RETURN', 'Supplier Return'),
    ]
    
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Positive for additions, negative for deductions"
    )
    unit = models.CharField(max_length=20)
    
    # Context
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., 'Purchase', 'ProductionBatch', 'Damage'"
    )
    reference_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of related object"
    )
    
    notes = models.TextField(blank=True)
    
    # Stock levels at time of movement
    stock_before = models.DecimalField(max_digits=12, decimal_places=3)
    stock_after = models.DecimalField(max_digits=12, decimal_places=3)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements_created'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
    
    def __str__(self):
        return f"{self.item.name}: {self.quantity:+} {self.unit} ({self.movement_type})"


class WastageRecord(models.Model):
    """
    Damage and wastage tracking with CEO approval for > KES 500
    """
    DAMAGE_TYPE_CHOICES = [
        ('SPILL', 'Spill'),
        ('EXPIRED', 'Expired'),
        ('DAMAGED', 'Damaged in Transit'),
        ('CONTAMINATED', 'Contaminated'),
        ('OTHER', 'Other'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='wastage_records'
    )
    
    # Damage Details
    damage_type = models.CharField(max_length=20, choices=DAMAGE_TYPE_CHOICES)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Quantity damaged (in recipe_unit)"
    )
    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="🤖 AUTO: quantity × cost_per_recipe_unit"
    )
    
    damage_date = models.DateField()
    description = models.TextField(help_text="Detailed description of damage")
    
    # Approval (required if cost > KES 500)
    requires_approval = models.BooleanField(
        default=False,
        help_text="🤖 AUTO: True if cost > KES 500"
    )
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wastage_approvals',
        help_text="CEO approval required for > KES 500"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='wastage_records_created'
    )
    
    class Meta:
        ordering = ['-damage_date']
        verbose_name = "Wastage Record"
        verbose_name_plural = "Wastage Records"
    
    def __str__(self):
        return f"{self.item.name}: {self.quantity} {self.item.recipe_unit} - KES {self.cost}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate cost and approval requirement"""
        self.cost = self.quantity * self.item.cost_per_recipe_unit
        self.requires_approval = self.cost > Decimal('500.00')
        super().save(*args, **kwargs)


class RestockAlert(models.Model):
    """
    Smart restock alerts (7-day supply threshold)
    """
    ALERT_LEVEL_CHOICES = [
        ('LOW', 'Low Stock (< 7 days)'),
        ('CRITICAL', 'Critical Stock (< 3 days)'),
        ('OUT', 'Out of Stock'),
    ]
    
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='restock_alerts'
    )
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVEL_CHOICES)
    days_remaining = models.IntegerField()
    message = models.TextField()
    
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restock_alerts_acknowledged'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Restock Alert"
        verbose_name_plural = "Restock Alerts"
    
    def __str__(self):
        return f"{self.item.name}: {self.alert_level} ({self.days_remaining} days)"


class UnitConversion(models.Model):
    """
    Unit conversion rules for inventory
    """
    from_unit = models.CharField(max_length=20)
    to_unit = models.CharField(max_length=20)
    factor = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Multiply by this to convert from_unit to to_unit"
    )
    
    notes = models.TextField(blank=True, help_text="e.g., '1 bag = 50kg'")
    
    class Meta:
        ordering = ['from_unit', 'to_unit']
        verbose_name = "Unit Conversion"
        verbose_name_plural = "Unit Conversions"
        unique_together = ['from_unit', 'to_unit']
    
    def __str__(self):
        return f"1 {self.from_unit} = {self.factor} {self.to_unit}"


class InventorySnapshot(models.Model):
    """
    Daily inventory snapshot for historical tracking
    Taken at book closing (9PM)
    """
    snapshot_date = models.DateField(unique=True)
    
    # Aggregated Data
    total_items = models.IntegerField(default=0)
    total_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Sum of (current_stock × cost_per_recipe_unit) for all items"
    )
    low_stock_items_count = models.IntegerField(
        default=0,
        help_text="Count of items with low_stock_alert=True"
    )
    
    # Snapshot Data (JSON field for all item details)
    data = models.JSONField(
        default=dict,
        help_text="Complete snapshot of all inventory items"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_snapshots_created'
    )
    
    class Meta:
        ordering = ['-snapshot_date']
        verbose_name = "Inventory Snapshot"
        verbose_name_plural = "Inventory Snapshots"
    
    def __str__(self):
        return f"Snapshot {self.snapshot_date}: {self.total_items} items, KES {self.total_value}"


class CrateStock(models.Model):
    """
    Crate inventory tracking
    Single-row table (only one record exists)
    Tracks total crates, available, dispatched, and damaged
    """
    # Crate Counts
    total_crates = models.IntegerField(
        default=0,
        help_text="Total crates owned by bakery"
    )
    available_crates = models.IntegerField(
        default=0,
        help_text="Crates available at bakery (not dispatched)"
    )
    dispatched_crates = models.IntegerField(
        default=0,
        help_text="Crates currently with salespeople"
    )
    damaged_crates = models.IntegerField(
        default=0,
        help_text="Crates marked as damaged/unusable"
    )
    
    # Physical Count Tracking
    last_counted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last physical count date"
    )
    last_counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crate_counts'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Crate Stock"
        verbose_name_plural = "Crate Stock"
    
    def __str__(self):
        return f"Crates: {self.available_crates} available, {self.dispatched_crates} dispatched, {self.damaged_crates} damaged"
    
    @classmethod
    def get_instance(cls):
        """Get or create the single CrateStock record"""
        stock, created = cls.objects.get_or_create(pk=1)
        return stock
    
    def dispatch_crates(self, quantity):
        """Move crates from available to dispatched"""
        if quantity > self.available_crates:
            raise ValueError(f"Cannot dispatch {quantity} crates - only {self.available_crates} available")
        self.available_crates -= quantity
        self.dispatched_crates += quantity
    
    def return_crates(self, quantity):
        """Move crates from dispatched back to available"""
        if quantity > self.dispatched_crates:
            raise ValueError(f"Cannot return {quantity} crates - only {self.dispatched_crates} dispatched")
        self.dispatched_crates -= quantity
        self.available_crates += quantity
    
    def mark_damaged(self, quantity):
        """Mark crates as damaged (from available or dispatched)"""
        self.damaged_crates += quantity
        self.total_crates -= quantity
    
    def add_crates(self, quantity):
        """Add new crates (purchase or repair)"""
        self.total_crates += quantity
        self.available_crates += quantity


class CrateMovement(models.Model):
    """
    Audit trail for all crate movements
    Tracks dispatch, return, purchase, damage, etc.
    """
    MOVEMENT_CHOICES = [
        ('DISPATCH_OUT', 'Dispatched to Salesperson'),
        ('RETURN_IN', 'Returned from Salesperson'),
        ('PURCHASE', 'New Crates Purchased'),
        ('DAMAGE', 'Crates Damaged'),
        ('REPAIR', 'Crates Repaired'),
        ('COUNT', 'Physical Count Adjustment'),
    ]
    
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_CHOICES,
        help_text="Type of crate movement"
    )
    quantity = models.IntegerField(
        help_text="Number of crates (positive or negative)"
    )
    salesperson_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Salesperson name if dispatch/return"
    )
    dispatch_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Related dispatch ID if applicable"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or reason"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='crate_movements'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Crate Movement"
        verbose_name_plural = "Crate Movements"
    
    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.quantity} crates on {self.created_at.strftime('%Y-%m-%d')}"
