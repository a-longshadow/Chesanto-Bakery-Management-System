from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """Generic audit record for model changes and important system events."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('INFO', 'Info'),
        ('ERROR', 'Error'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    app_label = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_pk = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    changes = models.JSONField(blank=True, null=True, help_text='Optional structured diff or payload')
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.timestamp.isoformat()} {self.app_label}.{self.model_name} {self.action} {self.object_pk}"


class RequestLog(models.Model):
    """Log of incoming HTTP requests for troubleshooting and traceability."""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=1024)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    remote_addr = models.CharField(max_length=100, blank=True)
    host = models.CharField(max_length=255, blank=True)
    query_params = models.TextField(blank=True)
    request_body = models.TextField(blank=True)
    response_body_snippet = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'

    def __str__(self):
        return f"{self.timestamp.isoformat()} {self.method} {self.path} {self.status_code or ''}"
