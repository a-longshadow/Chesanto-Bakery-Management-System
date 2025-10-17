from django.contrib import admin
from .models import EmailLog, SMSLog, MessageTemplate


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'template', 'status', 'sent_at', 'sent_by']
    list_filter = ['status', 'template', 'sent_at']
    search_fields = ['recipient', 'subject', 'error_message']
    readonly_fields = ['sent_at', 'delivered_at', 'opened_at', 'clicked_at']
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Message Details', {
            'fields': ('recipient', 'cc', 'bcc', 'subject', 'template')
        }),
        ('Tracking', {
            'fields': ('sent_by', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at')
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'retry_count')
        }),
        ('Metadata', {
            'fields': ('provider', 'provider_message_id', 'context_data'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'template', 'status', 'cost', 'sent_at', 'sent_by']
    list_filter = ['status', 'provider', 'sent_at']
    search_fields = ['phone_number', 'message', 'error_message']
    readonly_fields = ['sent_at', 'delivered_at']
    date_hierarchy = 'sent_at'


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'version', 'is_active', 'updated_at']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
