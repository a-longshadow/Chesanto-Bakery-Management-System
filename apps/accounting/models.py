from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class AccountingPeriod(models.Model):
    """
    Accounting Period - Monthly accounting cycles
    Links to all financial transactions for a given month
    """
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('RECONCILED', 'Reconciled'),
    ]
    
    # Period Information
    month = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Month number (1-12)"
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)],
        help_text="Year (e.g., 2024)"
    )
    
    # Period Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Financial Totals (aggregated from all sources)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue from sales"
    )
    total_direct_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total direct costs (ingredients, packaging)"
    )
    total_indirect_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total indirect costs (diesel, firewood, etc.)"
    )
    total_payroll_costs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total payroll (permanent + casual)"
    )
    total_other_expenses = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Other miscellaneous expenses"
    )
    
    # Calculated Fields
    gross_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Revenue - Direct Costs"
    )
    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Gross Profit - Indirect Costs - Payroll - Other Expenses"
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Net Profit / Revenue × 100 (%)"
    )
    
    # Reconciliation
    closed_at = models.DateTimeField(blank=True, null=True)
    reconciled_at = models.DateTimeField(blank=True, null=True)
    reconciled_by = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['month', 'year']
        indexes = [
            models.Index(fields=['month', 'year']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        from calendar import month_name
        return f"{month_name[self.month]} {self.year} - {self.status}"
    
    @property
    def period_display(self):
        from calendar import month_name
        return f"{month_name[self.month]} {self.year}"
    
    @property
    def is_locked(self):
        """Check if period is closed or reconciled"""
        return self.status in ['CLOSED', 'RECONCILED']
    
    def calculate_totals(self):
        """
        Aggregate all financial data for this period from:
        - Sales (revenue)
        - Production (direct costs: ingredients, packaging)
        - Production (indirect costs: diesel, firewood, etc.)
        - Payroll (permanent + casual labor)
        - Inventory (other purchases)
        """
        from apps.sales.models import SalesReturn
        from apps.production.models import ProductionBatch, IndirectCost
        from apps.payroll.models import MonthlyPayroll, CasualLabor
        from apps.inventory.models import Purchase
        from django.db.models import Sum
        from datetime import datetime
        
        # Date range for this period
        start_date = datetime(self.year, self.month, 1).date()
        if self.month == 12:
            end_date = datetime(self.year + 1, 1, 1).date()
        else:
            end_date = datetime(self.year, self.month + 1, 1).date()
        
        # Revenue from Sales
        sales_revenue = SalesReturn.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).aggregate(
            total=Sum('actual_revenue')
        )['total'] or Decimal('0.00')
        self.total_revenue = sales_revenue
        
        # Direct Costs from Production (ingredients + packaging)
        production_costs = ProductionBatch.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0.00')
        self.total_direct_costs = production_costs
        
        # Indirect Costs from Production
        indirect_costs = IndirectCost.objects.filter(
            daily_production__date__gte=start_date,
            daily_production__date__lt=end_date
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        self.total_indirect_costs = indirect_costs
        
        # Payroll Costs (Permanent)
        payroll_costs = MonthlyPayroll.objects.filter(
            month=self.month,
            year=self.year
        ).aggregate(
            total=Sum('total_net')
        )['total'] or Decimal('0.00')
        
        # Casual Labor Costs
        casual_costs = CasualLabor.objects.filter(
            date__gte=start_date,
            date__lt=end_date
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        self.total_payroll_costs = payroll_costs + casual_costs
        
        # Other Expenses (non-production inventory purchases)
        # This would include items not directly used in production
        other_purchases = Purchase.objects.filter(
            date__gte=start_date,
            date__lt=end_date,
            items__inventory_item__category__name__in=['Cleaning Supplies', 'Office Supplies', 'Miscellaneous']
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        self.total_other_expenses = other_purchases
        
        # Calculate Profit Metrics
        self.gross_profit = self.total_revenue - self.total_direct_costs
        self.net_profit = (
            self.gross_profit - 
            self.total_indirect_costs - 
            self.total_payroll_costs - 
            self.total_other_expenses
        )
        
        # Calculate Profit Margin
        if self.total_revenue > 0:
            self.profit_margin = (self.net_profit / self.total_revenue * 100).quantize(Decimal('0.01'))
        else:
            self.profit_margin = Decimal('0.00')
        
        self.save()


class JournalEntry(models.Model):
    """
    Journal Entry - Double-entry bookkeeping for all transactions
    Auto-created by signals from other apps (Production, Sales, Payroll, Inventory)
    """
    ENTRY_TYPE_CHOICES = [
        ('SALE', 'Sale'),
        ('PURCHASE', 'Purchase'),
        ('PRODUCTION', 'Production'),
        ('PAYROLL', 'Payroll'),
        ('ADJUSTMENT', 'Adjustment'),
        ('OPENING_BALANCE', 'Opening Balance'),
    ]
    
    # Entry Information
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    date = models.DateField(help_text="Transaction date")
    reference_number = models.CharField(max_length=50, unique=True, help_text="Unique reference (e.g., SAL-001, PUR-001)")
    
    # Accounting Period Link
    accounting_period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='journal_entries',
        help_text="Accounting period this entry belongs to"
    )
    
    # Description
    description = models.TextField(help_text="Description of the transaction")
    
    # Amounts (Double-entry: Debit = Credit)
    total_debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Status
    is_posted = models.BooleanField(default=False, help_text="Whether entry is posted to ledger")
    posted_at = models.DateTimeField(blank=True, null=True)
    
    # Foreign Key References (to link back to source transactions)
    # Use GenericForeignKey for flexibility
    source_app = models.CharField(max_length=50, blank=True, null=True, help_text="Source app (sales, production, etc.)")
    source_model = models.CharField(max_length=50, blank=True, null=True, help_text="Source model name")
    source_id = models.IntegerField(blank=True, null=True, help_text="Source object ID")
    
    # Metadata
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Journal Entry'
        verbose_name_plural = 'Journal Entries'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['entry_type']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['accounting_period']),
        ]
    
    def __str__(self):
        return f"{self.reference_number} - {self.get_entry_type_display()} ({self.date})"
    
    def clean(self):
        """Validate that debits equal credits"""
        from django.core.exceptions import ValidationError
        if self.total_debit != self.total_credit:
            raise ValidationError(f"Debits (KES {self.total_debit}) must equal Credits (KES {self.total_credit})")
    
    def post(self):
        """Post this journal entry to the ledger"""
        if not self.is_posted:
            self.is_posted = True
            self.posted_at = timezone.now()
            self.save()
            
            # Update accounting period totals
            self.accounting_period.calculate_totals()


class LedgerAccount(models.Model):
    """
    Chart of Accounts - All accounts for double-entry bookkeeping
    """
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    ]
    
    # Account Information
    account_code = models.CharField(max_length=20, unique=True, help_text="Unique account code (e.g., 1000, 2000)")
    account_name = models.CharField(max_length=200, help_text="Account name (e.g., Cash, Sales Revenue)")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    
    # Account Hierarchy (for sub-accounts)
    parent_account = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='sub_accounts',
        help_text="Parent account (for sub-accounts)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Current Balance
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current balance (updated by journal entries)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['account_code']
        indexes = [
            models.Index(fields=['account_code']),
            models.Index(fields=['account_type']),
        ]
    
    def __str__(self):
        return f"{self.account_code} - {self.account_name}"
    
    @property
    def full_account_path(self):
        """Get full account path (for sub-accounts)"""
        if self.parent_account:
            return f"{self.parent_account.full_account_path} > {self.account_name}"
        return self.account_name
    
    def update_balance(self, amount, is_debit=True):
        """
        Update account balance based on transaction
        - Asset/Expense accounts: Debit increases, Credit decreases
        - Liability/Equity/Revenue accounts: Credit increases, Debit decreases
        """
        if self.account_type in ['ASSET', 'EXPENSE']:
            if is_debit:
                self.current_balance += amount
            else:
                self.current_balance -= amount
        else:  # LIABILITY, EQUITY, REVENUE
            if is_debit:
                self.current_balance -= amount
            else:
                self.current_balance += amount
        
        self.save()


class JournalEntryLine(models.Model):
    """
    Journal Entry Line - Individual debit/credit lines for each journal entry
    Implements double-entry bookkeeping
    """
    LINE_TYPE_CHOICES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
    ]
    
    # Relationships
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name='journal_lines'
    )
    
    # Line Details
    line_type = models.CharField(max_length=10, choices=LINE_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.CharField(max_length=500, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['journal_entry', 'line_type', '-amount']
        indexes = [
            models.Index(fields=['journal_entry', 'line_type']),
            models.Index(fields=['account']),
        ]
    
    def __str__(self):
        return f"{self.journal_entry.reference_number} - {self.account.account_code} ({self.line_type}): KES {self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update ledger account balance
        is_debit = (self.line_type == 'DEBIT')
        self.account.update_balance(self.amount, is_debit=is_debit)
        
        # Update journal entry totals
        self.journal_entry.total_debit = self.journal_entry.lines.filter(line_type='DEBIT').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.journal_entry.total_credit = self.journal_entry.lines.filter(line_type='CREDIT').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        self.journal_entry.save()


class TrialBalance(models.Model):
    """
    Trial Balance - Snapshot of all account balances at a point in time
    Generated monthly to verify debits = credits
    """
    # Period Information
    accounting_period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='trial_balances'
    )
    
    # Balance Information
    total_debits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_credits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Validation
    is_balanced = models.BooleanField(default=False, help_text="Whether debits equal credits")
    variance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Difference between debits and credits (should be 0)"
    )
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['accounting_period']),
        ]
    
    def __str__(self):
        return f"Trial Balance - {self.accounting_period.period_display} ({self.generated_at.strftime('%Y-%m-%d')})"
    
    def generate(self):
        """Generate trial balance from all ledger accounts"""
        from django.db.models import Sum
        
        # Get all active accounts
        accounts = LedgerAccount.objects.filter(is_active=True)
        
        # Calculate total debits (Asset + Expense accounts with positive balance)
        asset_expense_balance = accounts.filter(
            account_type__in=['ASSET', 'EXPENSE'],
            current_balance__gt=0
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        
        # Add Liability/Equity/Revenue accounts with negative balance (which means debit side)
        other_debit_balance = accounts.filter(
            account_type__in=['LIABILITY', 'EQUITY', 'REVENUE'],
            current_balance__lt=0
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        
        self.total_debits = asset_expense_balance + abs(other_debit_balance)
        
        # Calculate total credits (Liability + Equity + Revenue accounts with positive balance)
        liability_equity_revenue_balance = accounts.filter(
            account_type__in=['LIABILITY', 'EQUITY', 'REVENUE'],
            current_balance__gt=0
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        
        # Add Asset/Expense accounts with negative balance (which means credit side)
        other_credit_balance = accounts.filter(
            account_type__in=['ASSET', 'EXPENSE'],
            current_balance__lt=0
        ).aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
        
        self.total_credits = liability_equity_revenue_balance + abs(other_credit_balance)
        
        # Check if balanced
        self.variance = self.total_debits - self.total_credits
        self.is_balanced = (abs(self.variance) < Decimal('0.01'))  # Allow for rounding errors
        
        self.save()

