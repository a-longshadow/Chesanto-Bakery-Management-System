from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class Employee(models.Model):
    """
    Employee model - Permanent employees (20+ capacity, unlimited)
    Tracks statutory deductions (NHIF, NSSF, PAYE) and pension contributions
    """
    EMPLOYEE_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent Employee'),
        ('CONTRACT', 'Contract Employee'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
    ]
    
    # Basic Information
    employee_id = models.CharField(max_length=20, unique=True, help_text="Unique employee ID (e.g., EMP001)")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Employment Details
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES, default='PERMANENT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    position = models.CharField(max_length=100, help_text="Job title/position")
    department = models.CharField(max_length=100, blank=True, null=True)
    hire_date = models.DateField(help_text="Date of employment")
    termination_date = models.DateField(blank=True, null=True)
    
    # Salary Information
    basic_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly basic salary (KES)"
    )
    
    # Allowances (optional)
    housing_allowance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly housing allowance (KES)"
    )
    transport_allowance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monthly transport allowance (KES)"
    )
    other_allowances = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Other monthly allowances (KES)"
    )
    
    # Statutory Information
    kra_pin = models.CharField(max_length=20, blank=True, null=True, help_text="KRA PIN for PAYE")
    nssf_number = models.CharField(max_length=20, blank=True, null=True, help_text="NSSF membership number")
    nhif_number = models.CharField(max_length=20, blank=True, null=True, help_text="NHIF membership number")
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    
    # Pension (optional)
    pension_contribution_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Pension contribution rate as percentage of basic salary"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about employee")
    
    class Meta:
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['status']),
            models.Index(fields=['hire_date']),
        ]
    
    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def gross_salary(self):
        """Calculate gross salary (basic + all allowances)"""
        return (
            self.basic_salary + 
            self.housing_allowance + 
            self.transport_allowance + 
            self.other_allowances
        )
    
    @property
    def pension_contribution(self):
        """Calculate monthly pension contribution"""
        return (self.basic_salary * self.pension_contribution_rate / 100).quantize(Decimal('0.01'))


class MonthlyPayroll(models.Model):
    """
    Monthly payroll period - Container for all payroll items for a specific month
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PROCESSING', 'Processing'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('FINALIZED', 'Finalized'),
    ]
    
    # Period Information
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Month number (1-12)"
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)],
        help_text="Year (e.g., 2024)"
    )
    
    # Payroll Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Totals (calculated from PayrollItems)
    total_gross = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total gross salary for all employees"
    )
    total_paye = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total PAYE deductions"
    )
    total_nhif = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total NHIF deductions"
    )
    total_nssf = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total NSSF deductions"
    )
    total_pension = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total pension contributions"
    )
    total_other_deductions = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total other deductions (loans, advances, etc.)"
    )
    total_net = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total net pay for all employees"
    )
    
    # Processing Information
    processed_by = models.CharField(max_length=100, blank=True, null=True, help_text="User who processed payroll")
    processed_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.CharField(max_length=100, blank=True, null=True, help_text="User who approved payroll")
    approved_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True, help_text="Date payroll was paid")
    finalized_at = models.DateTimeField(blank=True, null=True, help_text="Date payroll was finalized (locked)")
    
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
        return f"Payroll - {month_name[self.month]} {self.year} ({self.status})"
    
    @property
    def period_display(self):
        from calendar import month_name
        return f"{month_name[self.month]} {self.year}"
    
    @property
    def is_locked(self):
        """Check if payroll is finalized (immutable)"""
        return self.status == 'FINALIZED'
    
    def calculate_totals(self):
        """Recalculate all totals from PayrollItems"""
        items = self.payroll_items.all()
        self.total_gross = sum(item.gross_salary for item in items)
        self.total_paye = sum(item.paye for item in items)
        self.total_nhif = sum(item.nhif for item in items)
        self.total_nssf = sum(item.nssf for item in items)
        self.total_pension = sum(item.pension for item in items)
        self.total_other_deductions = sum(item.other_deductions for item in items)
        self.total_net = sum(item.net_salary for item in items)
        self.save()


class PayrollItem(models.Model):
    """
    Individual employee payroll entry for a specific month
    Stores all earnings, deductions, and net pay
    """
    # Relationships
    payroll = models.ForeignKey(
        MonthlyPayroll, 
        on_delete=models.CASCADE, 
        related_name='payroll_items',
        help_text="Monthly payroll period"
    )
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.PROTECT, 
        related_name='payroll_items',
        help_text="Employee"
    )
    
    # Earnings
    basic_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Basic salary for this month"
    )
    housing_allowance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    transport_allowance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    other_allowances = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    overtime_pay = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overtime payment for this month"
    )
    bonus = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Bonus payment for this month"
    )
    
    # Statutory Deductions
    paye = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="PAYE (Pay As You Earn) tax"
    )
    nhif = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="NHIF (National Hospital Insurance Fund)"
    )
    nssf = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="NSSF (National Social Security Fund)"
    )
    pension = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Pension contribution"
    )
    
    # Other Deductions
    loan_deduction = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Loan repayment deduction"
    )
    advance_deduction = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Salary advance deduction"
    )
    other_deductions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Other miscellaneous deductions"
    )
    
    # Days Worked (for partial month calculations)
    days_worked = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(31)],
        help_text="Number of days worked this month (for pro-rata calculation)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['employee__employee_id']
        unique_together = ['payroll', 'employee']
        indexes = [
            models.Index(fields=['payroll', 'employee']),
        ]
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.payroll.period_display}"
    
    @property
    def gross_salary(self):
        """Calculate gross salary (all earnings)"""
        return (
            self.basic_salary + 
            self.housing_allowance + 
            self.transport_allowance + 
            self.other_allowances + 
            self.overtime_pay + 
            self.bonus
        )
    
    @property
    def total_statutory_deductions(self):
        """Calculate total statutory deductions"""
        return self.paye + self.nhif + self.nssf + self.pension
    
    @property
    def total_other_deductions_calc(self):
        """Calculate total other deductions"""
        return self.loan_deduction + self.advance_deduction + self.other_deductions
    
    @property
    def total_deductions(self):
        """Calculate all deductions"""
        return self.total_statutory_deductions + self.total_other_deductions_calc
    
    @property
    def net_salary(self):
        """Calculate net salary (gross - all deductions)"""
        return self.gross_salary - self.total_deductions
    
    def calculate_statutory_deductions(self):
        """
        Calculate PAYE, NHIF, NSSF based on gross salary
        Uses Kenya tax brackets (2024 rates)
        """
        gross = self.gross_salary
        
        # NHIF Calculation (Kenya rates 2024)
        if gross <= 5999:
            self.nhif = Decimal('150.00')
        elif gross <= 7999:
            self.nhif = Decimal('300.00')
        elif gross <= 11999:
            self.nhif = Decimal('400.00')
        elif gross <= 14999:
            self.nhif = Decimal('500.00')
        elif gross <= 19999:
            self.nhif = Decimal('600.00')
        elif gross <= 24999:
            self.nhif = Decimal('750.00')
        elif gross <= 29999:
            self.nhif = Decimal('850.00')
        elif gross <= 34999:
            self.nhif = Decimal('900.00')
        elif gross <= 39999:
            self.nhif = Decimal('950.00')
        elif gross <= 44999:
            self.nhif = Decimal('1000.00')
        elif gross <= 49999:
            self.nhif = Decimal('1100.00')
        elif gross <= 59999:
            self.nhif = Decimal('1200.00')
        elif gross <= 69999:
            self.nhif = Decimal('1300.00')
        elif gross <= 79999:
            self.nhif = Decimal('1400.00')
        elif gross <= 89999:
            self.nhif = Decimal('1500.00')
        elif gross <= 99999:
            self.nhif = Decimal('1600.00')
        else:
            self.nhif = Decimal('1700.00')
        
        # NSSF Calculation (6% of gross, capped at KES 2,160)
        nssf_rate = Decimal('0.06')
        nssf_cap = Decimal('2160.00')
        self.nssf = min(gross * nssf_rate, nssf_cap).quantize(Decimal('0.01'))
        
        # Pension Calculation (from employee record)
        if self.employee.pension_contribution_rate > 0:
            self.pension = (self.basic_salary * self.employee.pension_contribution_rate / 100).quantize(Decimal('0.01'))
        
        # PAYE Calculation (Kenya tax brackets 2024)
        # Taxable income = Gross - NHIF - NSSF - Pension
        taxable_income = gross - self.nhif - self.nssf - self.pension
        
        if taxable_income <= 0:
            self.paye = Decimal('0.00')
        else:
            paye = Decimal('0.00')
            
            # 10% on first 24,000
            if taxable_income <= 24000:
                paye = taxable_income * Decimal('0.10')
            else:
                paye += Decimal('24000') * Decimal('0.10')
                
                # 25% on next 8,333 (24,001 - 32,333)
                if taxable_income <= 32333:
                    paye += (taxable_income - Decimal('24000')) * Decimal('0.25')
                else:
                    paye += Decimal('8333') * Decimal('0.25')
                    
                    # 30% on next 467,667 (32,334 - 500,000)
                    if taxable_income <= 500000:
                        paye += (taxable_income - Decimal('32333')) * Decimal('0.30')
                    else:
                        paye += Decimal('467667') * Decimal('0.30')
                        
                        # 32.5% on next 300,000 (500,001 - 800,000)
                        if taxable_income <= 800000:
                            paye += (taxable_income - Decimal('500000')) * Decimal('0.325')
                        else:
                            paye += Decimal('300000') * Decimal('0.325')
                            
                            # 35% on amount above 800,000
                            paye += (taxable_income - Decimal('800000')) * Decimal('0.35')
            
            # Personal relief (KES 2,400 per month)
            personal_relief = Decimal('2400.00')
            self.paye = max(paye - personal_relief, Decimal('0.00')).quantize(Decimal('0.01'))
        
        self.save()


class CasualLabor(models.Model):
    """
    Casual labor tracking - Daily/weekly workers not on permanent payroll
    Example: 12 workers × 13 days in Sept 2024 = 156 days × KES 1,200 = KES 187,200
    """
    # Period Information
    date = models.DateField(help_text="Date of work")
    
    # Worker Information
    worker_name = models.CharField(max_length=200, help_text="Name of casual worker(s)")
    number_of_workers = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        help_text="Number of workers for this entry"
    )
    
    # Work Details
    task_description = models.CharField(max_length=500, help_text="Description of work performed")
    daily_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Daily rate per worker (KES)"
    )
    
    # Payment Information
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount paid (auto-calculated: workers × rate)"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
        ],
        default='PENDING'
    )
    paid_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Casual Labor Entry'
        verbose_name_plural = 'Casual Labor Entries'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"{self.date} - {self.worker_name} ({self.number_of_workers} workers)"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total_amount
        self.total_amount = (Decimal(self.number_of_workers) * self.daily_rate).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
    
    @property
    def month_year(self):
        from calendar import month_name
        return f"{month_name[self.date.month]} {self.date.year}"

