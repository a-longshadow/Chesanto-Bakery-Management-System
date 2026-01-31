"""
Sales App - Data Models

Bank Ledger Philosophy: CREATE-ONLY, IMMUTABLE records.
- NO DELETE - Dispatches and Returns are permanent records
- NO EDIT - Once created, records cannot be modified
- NO ADJUSTMENTS - No "correction" or "reversal" records

Models:
- SalesDispatch: Daily dispatch record per salesperson (FK to accounts.User)
- SalesDispatchItem: Line items (product quantities) per dispatch
- SalesReturn: End-of-day return/settlement record
- SalesReturnItem: Line items with sold/returned breakdown
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class SalesDispatch(models.Model):
    """
    Daily dispatch record per salesperson.
    
    IMMUTABLE except:
    - is_returned, returned_at, status (set ONCE when return processed)
    
    Bank Ledger: Cannot be edited or deleted after creation.
    """
    
    class Status(models.TextChoices):
        DISPATCHED = 'DISPATCHED', 'Dispatched'
        RETURNED = 'RETURNED', 'Returned'
    
    # Dispatch ID - Auto-generated: DSP-YYYYMMDD-XXX
    dispatch_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False
    )
    
    # Salesperson - FK to User with role=SALESMAN
    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales_dispatches',
        limit_choices_to={'role': 'SALESMAN'},
        help_text="User with role=SALESMAN"
    )
    
    # Dispatch date
    dispatch_date = models.DateField(db_index=True)
    
    # Status - only 2 states: DISPATCHED or RETURNED
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DISPATCHED,
        db_index=True
    )
    
    # Crates dispatched
    crates_dispatched = models.PositiveIntegerField(default=0)
    
    # Return tracking (set when return processed)
    is_returned = models.BooleanField(default=False, db_index=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='dispatches_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_dispatch'
        ordering = ['-dispatch_date', '-created_at']
        # One dispatch per salesperson per day
        unique_together = ['salesperson', 'dispatch_date']
        indexes = [
            models.Index(fields=['dispatch_number']),
            models.Index(fields=['dispatch_date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_returned']),
            models.Index(fields=['salesperson', 'dispatch_date']),
        ]
    
    def __str__(self):
        return f"{self.dispatch_number} - {self.salesperson.get_display_name()}"
    
    def save(self, *args, **kwargs):
        """
        Enforce immutability and auto-generate dispatch_number.
        """
        if not self.dispatch_number:
            # Generate dispatch number on first save
            self.dispatch_number = self._generate_dispatch_number()
        
        if self.pk:
            # Existing record - enforce immutability
            original = SalesDispatch.objects.get(pk=self.pk)
            allowed_changes = {'is_returned', 'returned_at', 'status'}
            
            for field in self._meta.fields:
                if field.name in allowed_changes:
                    continue  # These are allowed to change once
                if field.name in ('id', 'created_at'):
                    continue  # Skip auto fields
                
                orig_val = getattr(original, field.name)
                new_val = getattr(self, field.name)
                
                # Handle FK comparisons
                if hasattr(orig_val, 'pk') and hasattr(new_val, 'pk'):
                    if orig_val.pk != new_val.pk:
                        raise ValueError(
                            f"SalesDispatch.{field.name} is immutable. Bank ledger policy."
                        )
                elif orig_val != new_val:
                    raise ValueError(
                        f"SalesDispatch.{field.name} is immutable. Bank ledger policy."
                    )
            
            # is_returned can only go False → True (never reversed)
            if original.is_returned and not self.is_returned:
                raise ValueError("Cannot un-return a dispatch. Bank ledger policy.")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bank ledger policy."""
        raise ValueError("SalesDispatch records cannot be deleted. Bank ledger policy.")
    
    def _generate_dispatch_number(self):
        """Generate unique dispatch number: DSP-YYYYMMDD-XXX"""
        date_str = self.dispatch_date.strftime('%Y%m%d')
        prefix = f"DSP-{date_str}-"
        
        last_dispatch = SalesDispatch.objects.filter(
            dispatch_number__startswith=prefix
        ).order_by('-dispatch_number').first()
        
        if last_dispatch:
            last_seq = int(last_dispatch.dispatch_number.split('-')[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        
        return f"{prefix}{next_seq:03d}"
    
    @property
    def total_units(self):
        """Total units across all dispatch items."""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_items(self):
        """Alias for total_units - total items dispatched."""
        return self.total_units
    
    @property
    def crates_out(self):
        """Alias for crates_dispatched - crates sent out."""
        return self.crates_dispatched
    
    @property
    def expected_revenue(self):
        """Expected revenue if all items sold at full price."""
        return sum(item.line_total for item in self.items.all())


class SalesDispatchItem(models.Model):
    """
    Line item for a dispatch - product and quantity.
    
    IMMUTABLE - no edits, no deletes (bank ledger).
    """
    
    dispatch = models.ForeignKey(
        SalesDispatch,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='dispatch_items'
    )
    
    quantity = models.PositiveIntegerField()
    
    # Price snapshot at dispatch time
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price at time of dispatch"
    )
    
    class Meta:
        db_table = 'sales_dispatch_item'
        unique_together = ['dispatch', 'product']
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.product.name}: {self.quantity} @ {self.unit_price}"
    
    @property
    def quantity_dispatched(self):
        """Alias for quantity - quantity dispatched."""
        return self.quantity
    
    @property
    def potential_value(self):
        """Alias for line_total - potential value if all sold."""
        return self.line_total
    
    @property
    def line_total(self):
        """Calculate line total: quantity × unit_price"""
        return Decimal(str(self.quantity)) * self.unit_price
    
    def save(self, *args, **kwargs):
        """Enforce immutability for existing records."""
        if self.pk:
            raise ValueError("SalesDispatchItem cannot be modified. Bank ledger policy.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bank ledger policy."""
        raise ValueError("SalesDispatchItem cannot be deleted. Bank ledger policy.")


class SalesReturn(models.Model):
    """
    End-of-day return/settlement record.
    
    IMMUTABLE except:
    - crates_marked_lost, crates_marked_damaged (resolution status flags)
    
    Bank Ledger: Cannot be edited or deleted after creation.
    Commission is manually entered by Accountant.
    """
    
    dispatch = models.OneToOneField(
        SalesDispatch,
        on_delete=models.PROTECT,
        related_name='sales_return'
    )
    
    return_date = models.DateField(db_index=True)
    
    # Calculated totals (stored for performance/auditing)
    total_units_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Auto-calculated: sum(qty_sold × unit_price)"
    )
    
    # Crate accountability
    crates_returned = models.PositiveIntegerField(default=0)
    crates_lost = models.PositiveIntegerField(default=0)
    crates_damaged = models.PositiveIntegerField(default=0)
    
    # Crate resolution status (ONLY mutable fields)
    crates_marked_lost = models.BooleanField(
        default=False,
        help_text="True when lost crates issue is resolved"
    )
    crates_marked_damaged = models.BooleanField(
        default=False,
        help_text="True when damaged crates issue is resolved"
    )
    
    # Commission (manual entry by Accountant)
    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Manually entered by Accountant. NULL if commission disabled."
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='returns_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales_return'
        ordering = ['-return_date', '-created_at']
        indexes = [
            models.Index(fields=['return_date']),
            models.Index(fields=['crates_marked_lost']),
            models.Index(fields=['crates_marked_damaged']),
        ]
    
    def __str__(self):
        return f"Return for {self.dispatch.dispatch_number}"
    
    @property
    def returned_at(self):
        """Alias for created_at - when the return was processed."""
        return self.created_at
    
    @property
    def processed_by(self):
        """Alias for created_by - who processed the return."""
        return self.created_by
    
    @property
    def crate_deficit(self):
        """Calculate crate deficit: dispatched - returned."""
        return self.dispatch.crates_dispatched - self.crates_returned
    
    @property
    def crates_reconciled(self):
        """True if all crate issues are resolved."""
        # If no deficit, consider reconciled
        if self.crate_deficit <= 0:
            return True
        # If deficit exists, check if lost/damaged are marked resolved
        return self.crates_marked_lost and self.crates_marked_damaged
    
    def clean(self):
        """Validate crate accountability."""
        if self.dispatch_id:
            crates_total = self.crates_returned + self.crates_lost + self.crates_damaged
            if crates_total != self.dispatch.crates_dispatched:
                raise ValidationError({
                    'crates_returned': (
                        f"Crate accountability error: "
                        f"returned ({self.crates_returned}) + "
                        f"lost ({self.crates_lost}) + "
                        f"damaged ({self.crates_damaged}) = {crates_total} "
                        f"≠ dispatched ({self.dispatch.crates_dispatched})"
                    )
                })
    
    def save(self, *args, **kwargs):
        """Enforce immutability except for crate status fields."""
        if self.pk:
            original = SalesReturn.objects.get(pk=self.pk)
            allowed_changes = {'crates_marked_lost', 'crates_marked_damaged'}
            
            for field in self._meta.fields:
                if field.name in allowed_changes:
                    continue
                if field.name in ('id', 'created_at'):
                    continue
                
                orig_val = getattr(original, field.name)
                new_val = getattr(self, field.name)
                
                # Handle FK comparisons
                if hasattr(orig_val, 'pk') and hasattr(new_val, 'pk'):
                    if orig_val.pk != new_val.pk:
                        raise ValueError(
                            f"SalesReturn.{field.name} is immutable. Bank ledger policy."
                        )
                elif orig_val != new_val:
                    raise ValueError(
                        f"SalesReturn.{field.name} is immutable. Bank ledger policy."
                    )
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bank ledger policy."""
        raise ValueError("SalesReturn records cannot be deleted. Bank ledger policy.")


class SalesReturnItem(models.Model):
    """
    Line item for a return - sold and returned quantities.
    
    IMMUTABLE - no edits, no deletes (bank ledger).
    Enforces: qty_sold + qty_returned == qty_dispatched
    """
    
    sales_return = models.ForeignKey(
        SalesReturn,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='return_items'
    )
    
    # Snapshot from dispatch for accountability
    qty_dispatched = models.PositiveIntegerField(
        help_text="Quantity originally dispatched"
    )
    
    # Accountant-entered values
    qty_sold = models.PositiveIntegerField()
    qty_returned = models.PositiveIntegerField()
    
    # Price from dispatch
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price from dispatch"
    )
    
    # Discount given for this product line (lump sum, not per-unit)
    line_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total discount given for this product line (e.g., 360 for bulk customer deals)"
    )
    
    # Auto-calculated: (qty_sold × unit_price) - line_discount
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Auto-calculated: (qty_sold × unit_price) - line_discount"
    )
    
    class Meta:
        db_table = 'sales_return_item'
        unique_together = ['sales_return', 'product']
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.product.name}: sold {self.qty_sold}, returned {self.qty_returned}"
    
    @property
    def quantity_sold(self):
        """Alias for qty_sold."""
        return self.qty_sold
    
    @property
    def quantity_returned(self):
        """Alias for qty_returned."""
        return self.qty_returned
    
    @property
    def quantity_dispatched(self):
        """Alias for qty_dispatched."""
        return self.qty_dispatched
    
    @property
    def line_total(self):
        """Alias for revenue - line total for this item."""
        return self.revenue
    
    @property
    def dispatch_item(self):
        """Get the corresponding dispatch item for this return item."""
        try:
            return SalesDispatchItem.objects.get(
                dispatch=self.sales_return.dispatch,
                product=self.product
            )
        except SalesDispatchItem.DoesNotExist:
            return None
    
    def clean(self):
        """Validate accountability and line discount."""
        # Validate accountability: sold + returned == dispatched
        total = self.qty_sold + self.qty_returned
        if total != self.qty_dispatched:
            raise ValidationError({
                'qty_sold': (
                    f"Accountability error: "
                    f"sold ({self.qty_sold}) + returned ({self.qty_returned}) = {total} "
                    f"≠ dispatched ({self.qty_dispatched})"
                )
            })
        
        # Validate line discount is not negative
        if self.line_discount and self.line_discount < 0:
            raise ValidationError({
                'line_discount': "Line discount cannot be negative."
            })
        
        # Validate line discount doesn't exceed gross revenue
        gross = Decimal(str(self.qty_sold)) * self.unit_price
        discount = self.line_discount or Decimal('0.00')
        if discount > gross:
            raise ValidationError({
                'line_discount': (
                    f"Line discount ({discount}) cannot exceed "
                    f"gross revenue ({gross})."
                )
            })
    
    def save(self, *args, **kwargs):
        """Calculate revenue and enforce immutability."""
        # Auto-calculate revenue: (qty_sold × unit_price) - line_discount
        gross = Decimal(str(self.qty_sold)) * self.unit_price
        self.revenue = gross - (self.line_discount or Decimal('0.00'))
        
        if self.pk:
            raise ValueError("SalesReturnItem cannot be modified. Bank ledger policy.")
        
        # Validate before save
        self.clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - bank ledger policy."""
        raise ValueError("SalesReturnItem cannot be deleted. Bank ledger policy.")
