"""
Inventory App - StockAlert Model
Shared table for tracking stock alert events across all inventory items.

This is an EVENT LOG - not transactional data.
Created atomically with stock changes when minimum_stock_level is breached.
"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class StockAlert(models.Model):
    """
    Shared table for all stock alerts (immutable event log).
    
    Created automatically by inventory utilities when stock falls below minimum.
    Forms an audit trail of all alert events across all 23 inventory items.
    
    Why Shared (Not Per-Item):
    - Alerts are event logs, not transactional data
    - Enables cross-item analysis: "How many alerts this week?"
    - Efficient querying across all items
    - inventory_item_id field links to specific item
    """
    ALERT_LEVEL_CHOICES = [
        ('WARNING', 'Low Stock Warning'),
        ('CRITICAL', 'Out of Stock'),
    ]
    
    TRIGGERED_BY_CHOICES = [
        ('production', 'Production Batch'),
        ('manual_output', 'Manual Output Recording'),
        ('sales', 'Sales Dispatch'),
        ('system', 'System Check'),
    ]
    
    # Item identification
    inventory_item_id = models.IntegerField(
        help_text="Inventory item ID (1-23)"
    )
    item_name = models.CharField(
        max_length=200,
        help_text="Snapshot of item name at alert time"
    )
    
    # Alert details
    alert_level = models.CharField(
        max_length=20,
        choices=ALERT_LEVEL_CHOICES,
        help_text="WARNING = low stock, CRITICAL = out of stock"
    )
    message = models.TextField(
        help_text="Full alert message for display/email"
    )
    
    # Stock snapshots at alert time
    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Stock level at alert time"
    )
    minimum_stock = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Minimum threshold at alert time"
    )
    
    # Trigger context
    triggered_by = models.CharField(
        max_length=50,
        choices=TRIGGERED_BY_CHOICES,
        help_text="Source of the deduction that triggered alert"
    )
    triggered_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_alerts_triggered',
        help_text="User who initiated the operation"
    )
    
    # Email tracking
    email_sent = models.BooleanField(
        default=False,
        help_text="Was notification email sent?"
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When notification email was sent"
    )
    
    # Audit fields (immutable)
    triggered_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Immutable timestamp of alert creation"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        db_table = 'inventory_stock_alerts'
        ordering = ['-triggered_at']
        verbose_name = 'Stock Alert'
        verbose_name_plural = 'Stock Alerts'
        indexes = [
            models.Index(fields=['inventory_item_id']),
            models.Index(fields=['alert_level']),
            models.Index(fields=['triggered_at']),
            models.Index(fields=['email_sent']),
        ]
    
    def save(self, *args, **kwargs):
        """
        Enforce immutability for alert records.
        Only exception: email_sent can be updated once.
        """
        if self.pk:
            # Allow only email_sent update
            original = StockAlert.objects.get(pk=self.pk)
            if not original.email_sent and self.email_sent:
                # This is allowed - marking email as sent
                super().save(update_fields=['email_sent', 'email_sent_at'])
                return
            else:
                raise ValueError("Stock alerts cannot be modified after creation. "
                               "Only email_sent can be set to True once.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - immutable event log"""
        raise ValueError("Stock alerts cannot be deleted. "
                        "This is an audit trail - records must be preserved.")
    
    def __str__(self):
        return f"[{self.alert_level}] {self.item_name}: {self.current_stock} (min: {self.minimum_stock})"
    
    @classmethod
    def create_alert(cls, inventory_item_id, item_name, current_stock, 
                     minimum_stock, triggered_by, triggered_by_user=None):
        """
        Factory method to create stock alert with proper level and message.
        
        Args:
            inventory_item_id: Integer (1-23)
            item_name: String - item display name
            current_stock: Decimal - current stock level
            minimum_stock: Decimal - minimum threshold
            triggered_by: String - source ('production', 'manual_output', etc.)
            triggered_by_user: User instance (optional)
        
        Returns:
            StockAlert instance (saved)
        """
        # Determine alert level
        if current_stock <= Decimal('0.0000'):
            alert_level = 'CRITICAL'
            message = f"OUT OF STOCK: {item_name} - {current_stock} (Min: {minimum_stock})"
        else:
            alert_level = 'WARNING'
            message = f"Low Stock: {item_name} - {current_stock} (Min: {minimum_stock})"
        
        return cls.objects.create(
            inventory_item_id=inventory_item_id,
            item_name=item_name,
            alert_level=alert_level,
            message=message,
            current_stock=current_stock,
            minimum_stock=minimum_stock,
            triggered_by=triggered_by,
            triggered_by_user=triggered_by_user,
        )
