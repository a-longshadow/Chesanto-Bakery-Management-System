"""
Reports App Admin
Read-only admin interfaces for report periods and summaries.
All reports are immutable (bank ledger policy).
"""
from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    ReportPeriod, 
    ReportProductSummary, 
    ReportSalespersonSummary,
    ReportInventorySummary,
    EmailLog,
    # Scheduling models
    ReportSchedule,
    ReportType,
    ScheduleReport,
    ReportRecipient,
    ScheduledReportLog,
)


class ReportProductSummaryInline(admin.TabularInline):
    """Inline view of product summaries within a report."""
    model = ReportProductSummary
    extra = 0
    readonly_fields = [
        'product', 'units_produced', 'production_cost', 'batches_count',
        'units_dispatched', 'units_sold', 'units_returned', 'revenue',
        'gross_profit_display', 'gross_margin_display'
    ]
    can_delete = False
    
    def gross_profit_display(self, obj):
        if obj.pk:
            color = 'green' if obj.gross_profit > 0 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">KES {:,.2f}</span>',
                color, obj.gross_profit
            )
        return '-'
    gross_profit_display.short_description = 'Gross Profit'
    
    def gross_margin_display(self, obj):
        if obj.pk:
            color = 'green' if obj.gross_margin > 20 else 'orange'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.gross_margin
            )
        return '-'
    gross_margin_display.short_description = 'Margin'
    
    def has_add_permission(self, request, obj=None):
        return False


class ReportSalespersonSummaryInline(admin.TabularInline):
    """Inline view of salesperson summaries within a report."""
    model = ReportSalespersonSummary
    extra = 0
    readonly_fields = [
        'salesperson', 'dispatch_count', 'total_units_sold', 
        'total_revenue', 'total_commission', 'crates_lost',
        'return_rate_display', 'crate_loss_rate_display'
    ]
    can_delete = False
    
    def return_rate_display(self, obj):
        if obj.pk:
            color = 'green' if obj.return_rate < 10 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.return_rate
            )
        return '-'
    return_rate_display.short_description = 'Return Rate'
    
    def crate_loss_rate_display(self, obj):
        if obj.pk:
            color = 'green' if obj.crate_loss_rate == 0 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.crate_loss_rate
            )
        return '-'
    crate_loss_rate_display.short_description = 'Crate Loss'
    
    def has_add_permission(self, request, obj=None):
        return False


class ReportInventorySummaryInline(admin.TabularInline):
    """Inline view of inventory summaries within a report."""
    model = ReportInventorySummary
    extra = 0
    readonly_fields = [
        'inventory_item_id', 'item_name', 'opening_stock', 'closing_stock',
        'total_purchased', 'purchase_cost', 'total_consumed', 'stock_movement_display'
    ]
    can_delete = False
    
    def stock_movement_display(self, obj):
        if obj.pk:
            movement = obj.stock_movement
            color = 'green' if movement >= 0 else 'red'
            sign = '+' if movement > 0 else ''
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}{:.2f}</span>',
                color, sign, movement
            )
        return '-'
    stock_movement_display.short_description = 'Movement'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReportPeriod)
class ReportPeriodAdmin(admin.ModelAdmin):
    """
    Report Period Admin - Read-only overview of generated reports.
    """
    list_display = [
        'period_label',
        'period_type_badge',
        'date_range',
        'revenue_display',
        'profit_display',
        'margin_display',
        'email_status',
        'generated_at'
    ]
    list_filter = ['period_type', 'is_locked', 'email_sent']
    search_fields = ['period_label']
    readonly_fields = [
        'period_type', 'start_date', 'end_date', 'period_label',
        'total_revenue', 'total_units_sold', 'total_dispatches', 'total_returns',
        'total_commissions', 'total_units_produced', 'total_batches',
        'total_production_cost', 'average_yield_variance',
        'total_purchase_cost', 'total_purchases_count', 'low_stock_alerts',
        'total_crates_dispatched', 'total_crates_returned',
        'total_crates_lost', 'total_crates_damaged',
        'gross_profit', 'gross_margin_percentage',
        'generated_at', 'generated_by', 'is_locked',
        'email_sent', 'email_sent_at', 'email_recipients'
    ]
    inlines = [
        ReportProductSummaryInline, 
        ReportSalespersonSummaryInline,
        ReportInventorySummaryInline
    ]
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Period Information', {
            'fields': ('period_type', 'start_date', 'end_date', 'period_label', 'is_locked')
        }),
        ('Sales Summary', {
            'fields': (
                'total_revenue', 'total_units_sold', 'total_dispatches',
                'total_returns', 'total_commissions'
            )
        }),
        ('Production Summary', {
            'fields': (
                'total_units_produced', 'total_batches', 
                'total_production_cost', 'average_yield_variance'
            )
        }),
        ('Inventory Summary', {
            'fields': (
                'total_purchase_cost', 'total_purchases_count', 'low_stock_alerts'
            )
        }),
        ('Crate Tracking', {
            'fields': (
                'total_crates_dispatched', 'total_crates_returned',
                'total_crates_lost', 'total_crates_damaged'
            )
        }),
        ('Financial Summary', {
            'fields': ('gross_profit', 'gross_margin_percentage')
        }),
        ('Generation Metadata', {
            'fields': ('generated_at', 'generated_by'),
            'classes': ('collapse',)
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_sent_at', 'email_recipients'),
            'classes': ('collapse',)
        }),
    )
    
    def period_type_badge(self, obj):
        colors = {
            'DAILY': '#3b82f6',    # Blue
            'WEEKLY': '#8b5cf6',   # Purple
            'MONTHLY': '#059669',  # Green
            'ANNUAL': '#dc2626',   # Red
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            colors.get(obj.period_type, '#6b7280'),
            obj.get_period_type_display()
        )
    period_type_badge.short_description = 'Type'
    
    def date_range(self, obj):
        if obj.start_date == obj.end_date:
            return obj.start_date.strftime('%d %b %Y')
        return f"{obj.start_date.strftime('%d %b')} - {obj.end_date.strftime('%d %b %Y')}"
    date_range.short_description = 'Date Range'
    
    def revenue_display(self, obj):
        return format_html(
            '<strong style="color: #059669;">KES {:,.0f}</strong>',
            obj.total_revenue
        )
    revenue_display.short_description = 'Revenue'
    
    def profit_display(self, obj):
        color = '#059669' if obj.gross_profit > 0 else '#dc2626'
        return format_html(
            '<strong style="color: {};">KES {:,.0f}</strong>',
            color, obj.gross_profit
        )
    profit_display.short_description = 'Profit'
    
    def margin_display(self, obj):
        color = '#059669' if obj.gross_margin_percentage > 20 else '#f59e0b'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, obj.gross_margin_percentage
        )
    margin_display.short_description = 'Margin'
    
    def email_status(self, obj):
        if obj.email_sent:
            return format_html(
                '<span style="color: #059669;">✅ Sent</span>'
            )
        return format_html(
            '<span style="color: #6b7280;">⏳ Not sent</span>'
        )
    email_status.short_description = 'Email'
    
    def has_add_permission(self, request):
        """Reports are generated via service, not manually added."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Reports cannot be deleted (bank ledger policy)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Reports are immutable."""
        return False


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """
    Email Log Admin - Audit trail of sent emails.
    """
    list_display = [
        'subject_truncated',
        'email_type_badge',
        'recipients_truncated',
        'sent_by',
        'sent_at',
        'status_badge'
    ]
    list_filter = ['email_type', 'is_success', 'sent_at']
    search_fields = ['subject', 'recipients']
    readonly_fields = [
        'email_type', 'report_period', 'subject', 'recipients',
        'sent_by', 'sent_at', 'is_success', 'error_message'
    ]
    date_hierarchy = 'sent_at'
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Subject'
    
    def email_type_badge(self, obj):
        colors = {'REPORT': '#3b82f6', 'ALERT': '#f59e0b'}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.email_type, '#6b7280'),
            obj.get_email_type_display()
        )
    email_type_badge.short_description = 'Type'
    
    def recipients_truncated(self, obj):
        return obj.recipients[:40] + '...' if len(obj.recipients) > 40 else obj.recipients
    recipients_truncated.short_description = 'Recipients'
    
    def status_badge(self, obj):
        if obj.is_success:
            return format_html('<span style="color: #059669;">✅ Success</span>')
        return format_html('<span style="color: #dc2626;">❌ Failed</span>')
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    @admin.action(description="🔄 Retry failed/selected reports NOW")
    def retry_failed_reports(self, request, queryset):
        """Retry sending the selected report logs by re-triggering their schedules."""
        from .tasks import send_scheduled_reports
        
        schedule_types = set()
        for log in queryset:
            if log.schedule:
                schedule_types.add(log.schedule.schedule_type)
        
        for schedule_type in schedule_types:
            try:
                result = send_scheduled_reports(schedule_type)
                status = result.get('status', '')
                if status in ['sent', 'success']:
                    self.message_user(
                        request,
                        f"✅ {schedule_type}: Sent to {result.get('recipients_count', 0)} recipients",
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request,
                        f"⚠️ {schedule_type}: {', '.join(result.get('errors', ['Check logs']))}",
                        messages.WARNING
                    )
            except Exception as e:
                self.message_user(request, f"❌ {schedule_type}: {str(e)}", messages.ERROR)
        
        if not schedule_types:
            self.message_user(request, "No schedules found in selected logs", messages.WARNING)
    
    @admin.action(description="🗑️ Clear logs older than 30 days")
    def clear_old_logs(self, request, queryset):
        """Delete logs older than 30 days."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        old_logs = ScheduledReportLog.objects.filter(started_at__lt=cutoff)
        count = old_logs.count()
        old_logs.delete()
        self.message_user(request, f"🗑️ Deleted {count} logs older than 30 days", messages.SUCCESS)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED REPORTS ADMIN
# Manage report schedules, recipients, and assignments
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduleReportInline(admin.TabularInline):
    """Inline for managing reports assigned to a schedule."""
    model = ScheduleReport
    extra = 1
    autocomplete_fields = ['report_type']
    ordering = ['sort_order']


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """Admin for managing report schedules."""
    list_display = ['name', 'schedule_type', 'time_display_admin', 'is_active', 'recipients_count', 'reports_count']
    list_filter = ['schedule_type', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']
    inlines = [ScheduleReportInline]
    actions = ['send_reports_now', 'activate_schedules', 'deactivate_schedules']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'schedule_type', 'is_active')
        }),
        ('Timing', {
            'fields': ('hour', 'minute'),
            'description': 'Time in Africa/Nairobi timezone (EAT)'
        }),
        ('Email Settings', {
            'fields': ('subject_template',),
            'description': 'Use {schedule_name}, {date}, {day_of_week} as placeholders'
        }),
    )
    
    def time_display_admin(self, obj):
        return obj.time_display
    time_display_admin.short_description = 'Time'
    
    def recipients_count(self, obj):
        count = obj.recipients.filter(is_active=True).count()
        return format_html('<span style="color: {};">{}</span>', 
                          '#059669' if count > 0 else '#dc2626', count)
    recipients_count.short_description = 'Recipients'
    
    def reports_count(self, obj):
        return obj.schedule_reports.filter(is_active=True).count()
    reports_count.short_description = 'Reports'
    
    @admin.action(description="📧 Send reports NOW to all recipients")
    def send_reports_now(self, request, queryset):
        """Immediately trigger the selected schedules to send reports."""
        from .tasks import (
            send_morning_report, send_evening_report, 
            send_weekly_report, send_monthly_report, send_annual_report
        )
        
        task_map = {
            'MORNING': send_morning_report,
            'EVENING': send_evening_report,
            'WEEKLY': send_weekly_report,
            'MONTHLY': send_monthly_report,
            'ANNUAL': send_annual_report,
        }
        
        sent_count = 0
        errors = []
        
        for schedule in queryset:
            task_func = task_map.get(schedule.schedule_type)
            if task_func:
                try:
                    result = task_func()
                    sent_count += 1
                    self.message_user(
                        request, 
                        f"✅ {schedule.name}: Sent to {result.get('recipients_count', 0)} recipients",
                        messages.SUCCESS
                    )
                except Exception as e:
                    errors.append(f"{schedule.name}: {str(e)}")
            else:
                errors.append(f"{schedule.name}: Unknown schedule type")
        
        if errors:
            self.message_user(request, f"⚠️ Errors: {'; '.join(errors)}", messages.WARNING)
    
    @admin.action(description="✅ Activate selected schedules")
    def activate_schedules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} schedule(s)", messages.SUCCESS)
    
    @admin.action(description="❌ Deactivate selected schedules")
    def deactivate_schedules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} schedule(s)", messages.SUCCESS)


@admin.register(ReportType)
class ReportTypeAdmin(admin.ModelAdmin):
    """Admin for managing available report types."""
    list_display = ['name', 'code', 'category', 'period_type', 'is_active', 'sort_order']
    list_filter = ['category', 'period_type', 'is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'code', 'description']
    ordering = ['category', 'sort_order']
    actions = ['activate_report_types', 'deactivate_report_types']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'category', 'period_type', 'is_active')
        }),
        ('PDF Configuration', {
            'fields': ('pdf_view_name', 'description'),
        }),
        ('Display', {
            'fields': ('sort_order',),
        }),
    )


    @admin.action(description="✅ Activate selected report types")
    def activate_report_types(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"✅ Activated {updated} report type(s)", messages.SUCCESS)
    
    @admin.action(description="❌ Deactivate selected report types")
    def deactivate_report_types(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"❌ Deactivated {updated} report type(s)", messages.SUCCESS)


@admin.register(ReportRecipient)
class ReportRecipientAdmin(admin.ModelAdmin):
    """Admin for managing report recipients."""
    list_display = ['name', 'email', 'user_link', 'is_active', 'schedules_list', 'created_at']
    list_filter = ['is_active', 'schedules']
    list_editable = ['is_active']
    search_fields = ['name', 'email', 'user__email']
    filter_horizontal = ['schedules']
    autocomplete_fields = ['user']
    actions = ['send_test_email', 'activate_recipients', 'deactivate_recipients', 
               'subscribe_to_all', 'unsubscribe_from_all']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'is_active')
        }),
        ('User Account', {
            'fields': ('user',),
            'description': 'Optionally link to a user account',
            'classes': ('collapse',),
        }),
        ('Subscriptions', {
            'fields': ('schedules',),
            'description': 'Select which reports this recipient should receive'
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            return format_html('<a href="/admin/accounts/user/{}/change/">{}</a>', 
                             obj.user.id, obj.user.email)
        return '-'
    user_link.short_description = 'User Account'
    
    def schedules_list(self, obj):
        schedules = obj.schedules.all()
        if schedules:
            return ', '.join([s.name for s in schedules])
        return format_html('<span style="color: #dc2626;">None</span>')
    schedules_list.short_description = 'Schedules'


@admin.register(ScheduledReportLog)
class ScheduledReportLogAdmin(admin.ModelAdmin):
    """Admin for viewing scheduled report execution logs."""
    list_display = ['schedule', 'status_badge', 'started_at', 'completed_at', 
                   'recipients_count', 'reports_summary', 'duration']
    list_filter = ['status', 'schedule', ('started_at', admin.DateFieldListFilter)]
    search_fields = ['schedule__name', 'recipients_list', 'reports_included']
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    readonly_fields = ['schedule', 'status', 'started_at', 'completed_at', 
                      'recipients_count', 'recipients_list', 'reports_included',
                      'error_message', 'task_id']
    actions = ['retry_failed_reports', 'clear_old_logs']
    
    def status_badge(self, obj):
        colors = {
            'PENDING': '#f59e0b',
            'GENERATING': '#3b82f6',
            'SENDING': '#8b5cf6',
            'SENT': '#059669',
            'FAILED': '#dc2626',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def reports_summary(self, obj):
        if obj.reports_included:
            reports = obj.reports_included.split(', ')
            return f"{len(reports)} reports"
        return '-'
    reports_summary.short_description = 'Reports'
    
    def duration(self, obj):
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            return f"{delta.total_seconds():.1f}s"
        return '-'
    duration.short_description = 'Duration'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deleting old logs
        return True
    
    def has_change_permission(self, request, obj=None):
        return False
    
    @admin.action(description="🔄 Retry failed/selected reports NOW")
    def retry_failed_reports(self, request, queryset):
        """Retry sending the selected report logs by re-triggering their schedules."""
        from .tasks import send_scheduled_reports
        
        schedule_types = set()
        for log in queryset:
            if log.schedule:
                schedule_types.add(log.schedule.schedule_type)
        
        for schedule_type in schedule_types:
            try:
                result = send_scheduled_reports(schedule_type)
                status = result.get('status', '')
                if status in ['sent', 'success']:
                    self.message_user(
                        request,
                        f"✅ {schedule_type}: Sent to {result.get('recipients_count', 0)} recipients",
                        messages.SUCCESS
                    )
                else:
                    self.message_user(
                        request,
                        f"⚠️ {schedule_type}: {', '.join(result.get('errors', ['Check logs']))}",
                        messages.WARNING
                    )
            except Exception as e:
                self.message_user(request, f"❌ {schedule_type}: {str(e)}", messages.ERROR)
        
        if not schedule_types:
            self.message_user(request, "No schedules found in selected logs", messages.WARNING)
    
    @admin.action(description="🗑️ Clear logs older than 30 days")
    def clear_old_logs(self, request, queryset):
        """Delete logs older than 30 days."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=30)
        old_logs = ScheduledReportLog.objects.filter(started_at__lt=cutoff)
        count = old_logs.count()
        old_logs.delete()
        self.message_user(request, f"🗑️ Deleted {count} logs older than 30 days", messages.SUCCESS)
