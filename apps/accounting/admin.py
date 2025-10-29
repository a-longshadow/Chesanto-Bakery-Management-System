from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    AccountingPeriod, 
    JournalEntry, 
    JournalEntryLine,
    LedgerAccount, 
    TrialBalance
)


class JournalEntryLineInline(admin.TabularInline):
    """
    Inline for Journal Entry Lines
    Shows debits and credits for each entry
    """
    model = JournalEntryLine
    extra = 2
    fields = ['account', 'line_type', 'amount', 'description']
    
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "line_type":
            kwargs['widget'] = admin.widgets.AdminRadioSelect()
        return super().formfield_for_choice_field(db_field, request, **kwargs)


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    """
    Accounting Period Admin - Monthly accounting cycles
    """
    list_display = [
        'period_display_admin',
        'status_badge',
        'total_revenue_display',
        'total_costs_display',
        'net_profit_display',
        'profit_margin_display',
        'reconciliation_status'
    ]
    list_filter = ['status', 'year', 'month']
    search_fields = ['month', 'year']
    readonly_fields = [
        'total_revenue_display',
        'total_direct_costs_display',
        'total_indirect_costs_display',
        'total_payroll_costs_display',
        'total_other_expenses_display',
        'gross_profit_display',
        'net_profit_display',
        'profit_margin_display',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Period Information', {
            'fields': ('month', 'year', 'status')
        }),
        ('Revenue & Costs', {
            'fields': (
                'total_revenue_display',
                'total_direct_costs_display',
                'total_indirect_costs_display',
                'total_payroll_costs_display',
                'total_other_expenses_display'
            )
        }),
        ('Profitability', {
            'fields': (
                'gross_profit_display',
                'net_profit_display',
                'profit_margin_display'
            )
        }),
        ('Reconciliation', {
            'fields': ('closed_at', 'reconciled_at', 'reconciled_by')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['calculate_period_totals', 'close_period', 'reconcile_period']
    
    def period_display_admin(self, obj):
        return obj.period_display
    period_display_admin.short_description = 'Period'
    
    def status_badge(self, obj):
        colors = {
            'OPEN': 'green',
            'CLOSED': 'orange',
            'RECONCILED': 'blue'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_revenue_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_revenue)
    total_revenue_display.short_description = 'Total Revenue'
    
    def total_costs_display(self, obj):
        total_costs = (
            obj.total_direct_costs + 
            obj.total_indirect_costs + 
            obj.total_payroll_costs + 
            obj.total_other_expenses
        )
        return format_html('KES {:,.2f}', total_costs)
    total_costs_display.short_description = 'Total Costs'
    
    def net_profit_display(self, obj):
        color = 'green' if obj.net_profit >= 0 else 'red'
        return format_html(
            '<strong style="color: {};">KES {:,.2f}</strong>',
            color,
            obj.net_profit
        )
    net_profit_display.short_description = 'Net Profit'
    
    def profit_margin_display(self, obj):
        color = 'green' if obj.profit_margin >= 0 else 'red'
        return format_html(
            '<strong style="color: {};">{:.2f}%</strong>',
            color,
            obj.profit_margin
        )
    profit_margin_display.short_description = 'Profit Margin'
    
    def total_direct_costs_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_direct_costs)
    total_direct_costs_display.short_description = 'Direct Costs'
    
    def total_indirect_costs_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_indirect_costs)
    total_indirect_costs_display.short_description = 'Indirect Costs'
    
    def total_payroll_costs_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_payroll_costs)
    total_payroll_costs_display.short_description = 'Payroll Costs'
    
    def total_other_expenses_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_other_expenses)
    total_other_expenses_display.short_description = 'Other Expenses'
    
    def gross_profit_display(self, obj):
        color = 'green' if obj.gross_profit >= 0 else 'red'
        return format_html(
            '<strong style="color: {};">KES {:,.2f}</strong>',
            color,
            obj.gross_profit
        )
    gross_profit_display.short_description = 'Gross Profit'
    
    def reconciliation_status(self, obj):
        if obj.status == 'RECONCILED':
            return format_html('<span style="color: blue;">✓ Reconciled</span>')
        elif obj.status == 'CLOSED':
            return format_html('<span style="color: orange;">⏳ Closed</span>')
        return format_html('<span style="color: green;">✏️ Open</span>')
    reconciliation_status.short_description = 'Reconciliation'
    
    def calculate_period_totals(self, request, queryset):
        """Bulk action to recalculate totals for selected periods"""
        count = 0
        for period in queryset:
            period.calculate_totals()
            count += 1
        self.message_user(request, f'Successfully calculated totals for {count} accounting period(s).')
    calculate_period_totals.short_description = 'Recalculate period totals'
    
    def close_period(self, request, queryset):
        """Bulk action to close selected periods"""
        updated = queryset.filter(status='OPEN').update(
            status='CLOSED',
            closed_at=timezone.now()
        )
        self.message_user(request, f'Successfully closed {updated} accounting period(s).')
    close_period.short_description = 'Close selected periods'
    
    def reconcile_period(self, request, queryset):
        """Bulk action to reconcile selected periods"""
        updated = queryset.filter(status='CLOSED').update(
            status='RECONCILED',
            reconciled_at=timezone.now(),
            reconciled_by=request.user.get_full_name() or request.user.username
        )
        self.message_user(request, f'Successfully reconciled {updated} accounting period(s).')
    reconcile_period.short_description = 'Reconcile selected periods'


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """
    Journal Entry Admin - Double-entry bookkeeping
    """
    list_display = [
        'reference_number',
        'date',
        'entry_type_badge',
        'total_debit_display',
        'total_credit_display',
        'balance_status',
        'posted_status'
    ]
    list_filter = ['entry_type', 'is_posted', 'date', 'accounting_period']
    search_fields = ['reference_number', 'description']
    readonly_fields = [
        'total_debit',
        'total_credit',
        'posted_at',
        'created_at',
        'updated_at'
    ]
    inlines = [JournalEntryLineInline]
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('entry_type', 'date', 'reference_number', 'accounting_period')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Totals (Auto-calculated)', {
            'fields': ('total_debit', 'total_credit')
        }),
        ('Posting Status', {
            'fields': ('is_posted', 'posted_at')
        }),
        ('Source Reference', {
            'fields': ('source_app', 'source_model', 'source_id'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['post_entries']
    
    def entry_type_badge(self, obj):
        colors = {
            'SALE': 'green',
            'PURCHASE': 'blue',
            'PRODUCTION': 'purple',
            'PAYROLL': 'orange',
            'ADJUSTMENT': 'gray',
            'OPENING_BALANCE': 'teal'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.entry_type, 'gray'),
            obj.get_entry_type_display()
        )
    entry_type_badge.short_description = 'Entry Type'
    
    def total_debit_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_debit)
    total_debit_display.short_description = 'Total Debit'
    
    def total_credit_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_credit)
    total_credit_display.short_description = 'Total Credit'
    
    def balance_status(self, obj):
        if obj.total_debit == obj.total_credit:
            return format_html('<span style="color: green;">✓ Balanced</span>')
        return format_html(
            '<span style="color: red;">✗ Unbalanced (Diff: KES {:,.2f})</span>',
            abs(obj.total_debit - obj.total_credit)
        )
    balance_status.short_description = 'Balance'
    
    def posted_status(self, obj):
        if obj.is_posted:
            return format_html('<span style="color: green;">✓ Posted</span>')
        return format_html('<span style="color: orange;">⏳ Not Posted</span>')
    posted_status.short_description = 'Posted'
    
    def post_entries(self, request, queryset):
        """Bulk action to post selected journal entries"""
        count = 0
        for entry in queryset.filter(is_posted=False):
            if entry.total_debit == entry.total_credit:
                entry.post()
                count += 1
        self.message_user(request, f'Successfully posted {count} journal entry/entries.')
    post_entries.short_description = 'Post selected entries'


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    """
    Ledger Account Admin - Chart of Accounts
    """
    list_display = [
        'account_code',
        'account_name',
        'account_type_badge',
        'current_balance_display',
        'parent_account',
        'active_status'
    ]
    list_filter = ['account_type', 'is_active']
    search_fields = ['account_code', 'account_name']
    readonly_fields = ['current_balance_display', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('account_code', 'account_name', 'account_type')
        }),
        ('Account Hierarchy', {
            'fields': ('parent_account',)
        }),
        ('Balance', {
            'fields': ('current_balance_display',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Additional Information', {
            'fields': ('description', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def account_type_badge(self, obj):
        colors = {
            'ASSET': 'blue',
            'LIABILITY': 'orange',
            'EQUITY': 'purple',
            'REVENUE': 'green',
            'EXPENSE': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.account_type, 'gray'),
            obj.get_account_type_display()
        )
    account_type_badge.short_description = 'Account Type'
    
    def current_balance_display(self, obj):
        color = 'green' if obj.current_balance >= 0 else 'red'
        return format_html(
            '<strong style="color: {};">KES {:,.2f}</strong>',
            color,
            obj.current_balance
        )
    current_balance_display.short_description = 'Current Balance'
    
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    active_status.short_description = 'Status'


@admin.register(TrialBalance)
class TrialBalanceAdmin(admin.ModelAdmin):
    """
    Trial Balance Admin - Verify debits = credits
    """
    list_display = [
        'accounting_period',
        'generated_at',
        'total_debits_display',
        'total_credits_display',
        'variance_display',
        'balance_status'
    ]
    list_filter = ['is_balanced', 'generated_at', 'accounting_period']
    readonly_fields = [
        'total_debits',
        'total_credits',
        'is_balanced',
        'variance',
        'generated_at'
    ]
    
    fieldsets = (
        ('Period', {
            'fields': ('accounting_period',)
        }),
        ('Balances', {
            'fields': ('total_debits', 'total_credits', 'variance', 'is_balanced')
        }),
        ('Generation Information', {
            'fields': ('generated_at', 'generated_by', 'notes')
        }),
    )
    
    actions = ['regenerate_trial_balance']
    
    def total_debits_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_debits)
    total_debits_display.short_description = 'Total Debits'
    
    def total_credits_display(self, obj):
        return format_html('KES {:,.2f}', obj.total_credits)
    total_credits_display.short_description = 'Total Credits'
    
    def variance_display(self, obj):
        color = 'green' if abs(obj.variance) < 0.01 else 'red'
        return format_html(
            '<strong style="color: {};">KES {:,.2f}</strong>',
            color,
            obj.variance
        )
    variance_display.short_description = 'Variance'
    
    def balance_status(self, obj):
        if obj.is_balanced:
            return format_html('<span style="color: green;">✓ Balanced</span>')
        return format_html('<span style="color: red;">✗ Unbalanced</span>')
    balance_status.short_description = 'Status'
    
    def regenerate_trial_balance(self, request, queryset):
        """Bulk action to regenerate trial balance"""
        count = 0
        for trial_balance in queryset:
            trial_balance.generate()
            count += 1
        self.message_user(request, f'Successfully regenerated {count} trial balance(s).')
    regenerate_trial_balance.short_description = 'Regenerate trial balance'
    
    def has_add_permission(self, request):
        # Trial balances should only be generated, not manually added
        return True
    
    def save_model(self, request, obj, form, change):
        obj.generated_by = request.user.get_full_name() or request.user.username
        super().save_model(request, obj, form, change)
        # Auto-generate trial balance on save
        obj.generate()

