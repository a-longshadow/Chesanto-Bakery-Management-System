from django.db import models
from django.conf import settings
from apps.core.models import TimestampedModel


class EmailLog(models.Model):
    """Track all outgoing emails for audit and debugging"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        REJECTED = 'REJECTED', 'Rejected'
    
    # Message details
    recipient = models.EmailField(db_index=True)
    cc = models.JSONField(null=True, blank=True)  # CC recipients
    bcc = models.JSONField(null=True, blank=True)  # BCC recipients
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=100, db_index=True)
    
    # Tracking
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_emails'
    )
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Context (for debugging)
    context_data = models.JSONField(null=True, blank=True)
    
    # Provider metadata
    provider = models.CharField(max_length=50, default='gmail')
    provider_message_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'communications_email_log'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['template', 'sent_at']),
        ]
    
    def __str__(self):
        return f"{self.template} to {self.recipient} - {self.status}"


class SMSLog(models.Model):
    """Track all outgoing SMS for audit and debugging (future)"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        DELIVERED = 'DELIVERED', 'Delivered'
        UNDELIVERED = 'UNDELIVERED', 'Undelivered'
    
    # Message details
    phone_number = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    template = models.CharField(max_length=100, db_index=True)
    
    # Tracking
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_sms'
    )
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Provider metadata
    provider = models.CharField(max_length=50, blank=True)  # twilio, africastalking, etc
    provider_message_id = models.CharField(max_length=255, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # SMS cost
    
    class Meta:
        db_table = 'communications_sms_log'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
        ]
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status}"


class MessageTemplate(models.Model):
    """Store reusable message templates (future enhancement)"""
    
    class Type(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        SMS = 'SMS', 'SMS'
    
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    subject = models.CharField(max_length=255, blank=True)  # For emails
    template_path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Versioning
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'communications_message_template'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
