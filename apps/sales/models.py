"""
Sales App Models
Manages dispatches and returns for Chesanto Bakery
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class Salesperson(models.Model):
    """
    Represents a salesperson, depot, or school.
    Used for searchable dropdown (handles 50+ entries).
    """
    SALESPERSON_TYPE_CHOICES = [
        ('PERSON', 'Individual Salesperson'),
        ('DEPOT', 'Depot'),
        ('SCHOOL', 'School'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Salesperson/Depot/School name"
    )
    salesperson_type = models.CharField(
        max_length=20,
        choices=SALESPERSON_TYPE_CHOICES,
        default='PERSON',
        help_text="Type of sales entity"
    )
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='salespeople_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='salespeople_updated'
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = "Salesperson"
        verbose_name_plural = "Salespeople"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.name}"


class Dispatch(models.Model):
    """
    UNIFIED model: Records dispatch AND return in ONE place.
    Lifecycle: Created → Crates Assigned → Returned (locked)
    """
    # ============ DISPATCH PHASE ============
    dispatch_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Auto-generated: DSP-YYYYMMDD-NAME-001"
    )
    
    salesperson = models.ForeignKey(
        Salesperson,
        on_delete=models.PROTECT,
        related_name='dispatches'
    )
    dispatch_date = models.DateField(help_text="Date of dispatch")
    
    # Product quantities dispatched
    bread_qty = models.PositiveIntegerField(
        default=0,
        help_text="Loaves of bread dispatched"
    )
    kdf_qty = models.PositiveIntegerField(
        default=0,
        help_text="KDF packets dispatched"
    )
    scones_qty = models.PositiveIntegerField(
        default=0,
        help_text="Scones packets dispatched"
    )
    
    # Crates dispatched
    crates_dispatched = models.PositiveIntegerField(
        default=0,
        help_text="Number of crates dispatched"
    )
    
    # ============ RETURN PHASE (NULL until returned) ============
    # Products sold & returned
    bread_sold = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Bread loaves sold"
    )
    bread_returned = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Bread loaves returned unsold"
    )
    kdf_sold = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="KDF packets sold"
    )
    kdf_returned = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="KDF packets returned unsold"
    )
    scones_sold = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Scones packets sold"
    )
    scones_returned = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Scones packets returned unsold"
    )
    
    # Revenue (calculated from sold × Product.price_per_packet)
    bread_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Revenue from bread sales (KES)"
    )
    kdf_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Revenue from KDF sales (KES)"
    )
    scones_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Revenue from scones sales (KES)"
    )
    total_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total revenue (KES)"
    )
    
    # Crates returned
    crates_returned = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of crates returned"
    )
    crate_deficit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Crate deficit (dispatched - returned)"
    )
    
    # ============ STATUS TRACKING ============
    is_returned = models.BooleanField(
        default=False,
        help_text="Locks entire record after return"
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    
    # Soft delete (only if NOT returned)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='deleted_dispatches'
    )
    
    # ============ AUDIT ============
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_dispatches'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='updated_dispatches'
    )
    
    class Meta:
        ordering = ['-dispatch_date', '-created_at']
        verbose_name = "Dispatch"
        verbose_name_plural = "Dispatches"
        unique_together = [['salesperson', 'dispatch_date']]
        indexes = [
            models.Index(fields=['dispatch_number']),
            models.Index(fields=['dispatch_date']),
            models.Index(fields=['salesperson', 'dispatch_date']),
            models.Index(fields=['is_returned']),
            models.Index(fields=['deleted_at']),
        ]
    
    def __str__(self):
        return f"{self.dispatch_number} - {self.salesperson.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate dispatch_number on creation"""
        if not self.dispatch_number:
            from django.db import transaction
            
            with transaction.atomic():
                # Lock to prevent race conditions
                existing = Dispatch.objects.filter(
                    salesperson=self.salesperson,
                    dispatch_date=self.dispatch_date
                ).select_for_update().count()
                
                # Generate components
                date_str = self.dispatch_date.strftime('%Y%m%d')
                name_abbr = self.salesperson.name[:4].upper().replace(' ', '')
                sequence = str(existing + 1).zfill(3)
                
                self.dispatch_number = f"DSP-{date_str}-{name_abbr}-{sequence}"
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate dispatch data"""
        # At least one product must be dispatched
        if self.bread_qty == 0 and self.kdf_qty == 0 and self.scones_qty == 0:
            raise ValidationError("At least one product quantity must be greater than 0")
        
        # Cannot edit/delete if returned
        if self.pk and self.is_returned:
            original = Dispatch.objects.get(pk=self.pk)
            if original.is_returned and not self.is_returned:
                raise ValidationError("Cannot unlock returned dispatch")
        
        # Validate return accountability (if returned)
        if self.is_returned:
            # Bread
            if self.bread_qty > 0:
                bread_total = (self.bread_sold or 0) + (self.bread_returned or 0)
                if bread_total != self.bread_qty:
                    raise ValidationError(
                        f"Bread accountability error: "
                        f"sold ({self.bread_sold}) + returned ({self.bread_returned}) "
                        f"!= dispatched ({self.bread_qty})"
                    )
            
            # KDF
            if self.kdf_qty > 0:
                kdf_total = (self.kdf_sold or 0) + (self.kdf_returned or 0)
                if kdf_total != self.kdf_qty:
                    raise ValidationError(
                        f"KDF accountability error: "
                        f"sold ({self.kdf_sold}) + returned ({self.kdf_returned}) "
                        f"!= dispatched ({self.kdf_qty})"
                    )
            
            # Scones
            if self.scones_qty > 0:
                scones_total = (self.scones_sold or 0) + (self.scones_returned or 0)
                if scones_total != self.scones_qty:
                    raise ValidationError(
                        f"Scones accountability error: "
                        f"sold ({self.scones_sold}) + returned ({self.scones_returned}) "
                        f"!= dispatched ({self.scones_qty})"
                    )
