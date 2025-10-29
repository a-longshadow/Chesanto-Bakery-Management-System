from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Employee, MonthlyPayroll, PayrollItem, CasualLabor


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    Employee Admin - CRUD interface for managing employees
    Features: Inline editing, status filtering, search
    """
    list_display = [
        'employee_id', 
        'full_name_display', 
        'position', 
        'status_badge',
        'basic_salary_display',
        'gross_salary_display',
        'hire_date'
    ]
    list_filter = ['status', 'employee_type', 'department', 'hire_date']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email', 'kra_pin']
    readonly_fields = ['created_at', 'updated_at', 'gross_salary_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Employment Details', {
            'fields': ('employee_type', 'status', 'position', 'department', 'hire_date', 'termination_date')
        }),
        ('Salary & Allowances', {
            'fields': (
                'basic_salary', 
                'housing_allowance', 
                'transport_allowance', 
                'other_allowances',
                'gross_salary_display'
            )
        }),
        ('Statutory Information', {
            'fields': ('kra_pin', 'nssf_number', 'nhif_number', 'pension_contribution_rate')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_branch')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name_display(self, obj):
        return obj.full_name
    full_name_display.short_description = 'Full Name'
    
    def status_badge(self, obj):
        colors = {
            'ACTIVE': 'green',
            'SUSPENDED': 'orange',
            'TERMINATED': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def basic_salary_display(self, obj):
        return format_html('KES {:,.2f}', obj.basic_salary)
    basic_salary_display.short_description = 'Basic Salary'
    
    def gross_salary_display(self, obj):
        return format_html('KES {:,.2f}', obj.gross_salary)
    gross_salary_display.short_description = 'Gross Salary'


class PayrollItemInline(admin.TabularInline):
    """
    Inline for PayrollItems within MonthlyPayroll
    """
    model = PayrollItem
    extra = 0
    fields = [
        'employee', 
        'basic_salary', 
        'gross_salary_display',
        'paye', 
        'nhif', 
        'nssf',
        'pension',
        'total_deductions_display',
        'net_salary_display'
    ]
    readonly_fields = ['gross_salary_display', 'total_deductions_display', 'net_salary_display']
    
    def gross_salary_display(self, obj):
        if obj.id:
            return format_html('KES {:,.2f}', obj.gross_salary)
        return '-'
    gross_salary_display.short_description = 'Gross'
    
    def total_deductions_display(self, obj):
        if obj.id:
            return format_html('KES {:,.2f}', obj.total_deductions)
        return '-'
    total_deductions_display.short_description = 'Total Deductions'
    
    def net_salary_display(self, obj):
        if obj.id:
            return format_html('KES {:,.2f}', obj.net_salary)
        return '-'
    net_salary_display.short_description = 'Net Salary'


@admin.register(MonthlyPayroll)
class MonthlyPayrollAdmin(admin.ModelAdmin):
    """
    Monthly Payroll Admin - 5-step workflow
    Steps: Draft → Processing → Approved → Paid → Finalized
    """
    list_display = [
        'period_display_admin',
        'status_badge',
        'total_gross_display',
        'total_deductions_display',
        'total_net_display',
        'processed_at',
        'lock_status'
    ]
    list_filter = ['status', 'year', 'month']
    search_fields = ['month', 'year']
    readonly_fields = [
        'total_gross_display',
        'total_paye_display',
        'total_nhif_display',
        'total_nssf_display',
        'total_pension_display',
        'total_other_deductions_display',
        'total_net_display',
        'created_at',
        'updated_at'
    ]
    inlines = [PayrollItemInline]
    
    fieldsets = (
        ('Period Information', {
            'fields': ('month', 'year', 'status')
        }),
        ('Totals (Auto-calculated)', {
            'fields': (
                'total_gross_display',
                'total_paye_display',
                'total_nhif_display',
                'total_nssf_display',
                'total_pension_display',
                'total_other_deductions_display',
                'total_net_display'
            )
        }),
        ('Processing Information', {
            'fields': (
                'processed_by', 'processed_at',
                'approved_by', 'approved_at',
                'paid_at', 'finalized_at'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def period_display_admin(self, obj):
        return obj.period_display
    period_display_admin.short_description = 'Payroll Period'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'PROCESSING': 'blue',
            'APPROVED': 'green',
            'PAID': 'teal',
            'FINALIZED': 'purple'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_gross_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_gross)
    total_gross_display.short_description = 'Total Gross'
    
    def total_deductions_display(self, obj):
        total_deductions = obj.total_paye + obj.total_nhif + obj.total_nssf + obj.total_pension + obj.total_other_deductions
        return format_html('KES {:,.2f}', total_deductions)
    total_deductions_display.short_description = 'Total Deductions'
    
    def total_net_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.total_net)
    total_net_display.short_description = 'Total Net Pay'
    
    def total_paye_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_paye)
    total_paye_display.short_description = 'Total PAYE'
    
    def total_nhif_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_nhif)
    total_nhif_display.short_description = 'Total NHIF'
    
    def total_nssf_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_nssf)
    total_nssf_display.short_description = 'Total NSSF'
    
    def total_pension_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_pension)
    total_pension_display.short_description = 'Total Pension'
    
    def total_other_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_other_deductions)
    total_other_deductions_display.short_description = 'Total Other Deductions'
    
    def lock_status(self, obj):
        if obj.is_locked:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: green;">✏️ Editable</span>')
    lock_status.short_description = 'Lock Status'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of finalized payrolls
        if obj and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        # Auto-set processing timestamps based on status changes
        if obj.status == 'PROCESSING' and not obj.processed_at:
            obj.processed_at = timezone.now()
            obj.processed_by = request.user.get_full_name() or request.user.username
        
        if obj.status == 'APPROVED' and not obj.approved_at:
            obj.approved_at = timezone.now()
            obj.approved_by = request.user.get_full_name() or request.user.username
        
        if obj.status == 'PAID' and not obj.paid_at:
            obj.paid_at = timezone.now()
        
        if obj.status == 'FINALIZED' and not obj.finalized_at:
            obj.finalized_at = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Recalculate totals after saving
        obj.calculate_totals()


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    """
    Individual Payroll Item Admin - Detailed view of employee payroll
    """
    list_display = [
        'employee_name',
        'payroll_period',
        'gross_salary_display',
        'statutory_deductions_display',
        'other_deductions_display',
        'net_salary_display'
    ]
    list_filter = ['payroll__year', 'payroll__month']
    search_fields = ['employee__employee_id', 'employee__first_name', 'employee__last_name']
    readonly_fields = [
        'gross_salary_display',
        'total_statutory_deductions_display',
        'total_other_deductions_display',
        'total_deductions_display',
        'net_salary_display',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Employee & Period', {
            'fields': ('payroll', 'employee', 'days_worked')
        }),
        ('Earnings', {
            'fields': (
                'basic_salary',
                'housing_allowance',
                'transport_allowance',
                'other_allowances',
                'overtime_pay',
                'bonus',
                'gross_salary_display'
            )
        }),
        ('Statutory Deductions', {
            'fields': (
                'paye',
                'nhif',
                'nssf',
                'pension',
                'total_statutory_deductions_display'
            )
        }),
        ('Other Deductions', {
            'fields': (
                'loan_deduction',
                'advance_deduction',
                'other_deductions',
                'total_other_deductions_display'
            )
        }),
        ('Summary', {
            'fields': (
                'total_deductions_display',
                'net_salary_display'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_name(self, obj):
        return obj.employee.full_name
    employee_name.short_description = 'Employee'
    
    def payroll_period(self, obj):
        return obj.payroll.period_display
    payroll_period.short_description = 'Period'
    
    def gross_salary_display(self, obj):
        return format_html('KES {:,.2f}', obj.gross_salary)
    gross_salary_display.short_description = 'Gross Salary'
    
    def statutory_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_statutory_deductions)
    statutory_deductions_display.short_description = 'Statutory Deductions'
    
    def other_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_other_deductions_calc)
    other_deductions_display.short_description = 'Other Deductions'
    
    def net_salary_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.net_salary)
    net_salary_display.short_description = 'Net Salary'
    
    def total_statutory_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_statutory_deductions)
    total_statutory_deductions_display.short_description = 'Total Statutory Deductions'
    
    def total_other_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_other_deductions_calc)
    total_other_deductions_display.short_description = 'Total Other Deductions'
    
    def total_deductions_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_deductions)
    total_deductions_display.short_description = 'Total Deductions'
    
    actions = ['calculate_statutory_deductions_action']
    
    def calculate_statutory_deductions_action(self, request, queryset):
        """Bulk action to calculate statutory deductions for selected items"""
        count = 0
        for item in queryset:
            item.calculate_statutory_deductions()
            count += 1
        self.message_user(request, f'Successfully calculated statutory deductions for {count} payroll item(s).')
    calculate_statutory_deductions_action.short_description = 'Calculate statutory deductions'


@admin.register(CasualLabor)
class CasualLaborAdmin(admin.ModelAdmin):
    """
    Casual Labor Admin - Track daily/weekly casual workers
    """
    list_display = [
        'date',
        'worker_name',
        'number_of_workers',
        'daily_rate_display',
        'total_amount_display',
        'payment_status_badge'
    ]
    list_filter = ['payment_status', 'date']
    search_fields = ['worker_name', 'task_description']
    readonly_fields = ['total_amount_display', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Work Details', {
            'fields': ('date', 'worker_name', 'number_of_workers', 'task_description')
        }),
        ('Payment Information', {
            'fields': (
                'daily_rate',
                'total_amount_display',
                'payment_status',
                'paid_at'
            )
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def daily_rate_display(self, obj):
        return format_html('KES {:,.2f}', obj.daily_rate)
    daily_rate_display.short_description = 'Daily Rate'
    
    def total_amount_display(self, obj):
        return format_html('<strong>KES {:,.2f}</strong>', obj.total_amount)
    total_amount_display.short_description = 'Total Amount'
    
    def payment_status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PAID': 'green'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.payment_status, 'gray'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment Status'
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        """Bulk action to mark casual labor entries as paid"""
        updated = queryset.filter(payment_status='PENDING').update(
            payment_status='PAID',
            paid_at=timezone.now()
        )
        self.message_user(request, f'Successfully marked {updated} casual labor entry/entries as paid.')
    mark_as_paid.short_description = 'Mark selected as paid'

