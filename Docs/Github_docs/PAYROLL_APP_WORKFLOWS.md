# Payroll App Workflows

## Overview

The Payroll app manages employee compensation, statutory deductions (Kenya 2024 rates), and casual labor tracking. **SUPERADMIN-only access** ensures payroll data confidentiality.

---

## Data Models

### 1. Employee
Links User accounts to payroll system.

| Field | Type | Purpose |
|-------|------|---------|
| `user` | OneToOneField | Links to accounts.User |
| `employee_id` | CharField | Unique ID (EMP0001) |
| `employee_type` | Choice | PERMANENT / CONTRACT |
| `status` | Choice | ACTIVE / SUSPENDED / TERMINATED |
| `basic_salary` | Decimal | Monthly base (KES) |
| `housing_allowance` | Decimal | Monthly housing (KES) |
| `transport_allowance` | Decimal | Monthly transport (KES) |
| `other_allowances` | Decimal | Monthly other (KES) |
| `kra_pin` | CharField | For PAYE |
| `nssf_number` | CharField | NSSF membership |
| `nhif_number` | CharField | NHIF membership |
| `employer_remits_paye` | Boolean | Who submits to KRA |
| `employer_remits_nhif` | Boolean | Who submits to NHIF |
| `employer_remits_nssf` | Boolean | Who submits to NSSF |
| `pension_contribution_rate` | Decimal | % of basic salary |
| `bank_name` | CharField | Payment bank |
| `bank_account_number` | CharField | Account number |

**Key Property:**
```python
@property
def gross_salary(self):
    return self.basic_salary + self.housing_allowance + self.transport_allowance + self.other_allowances
```

---

### 2. MonthlyPayroll
Container for a payroll period with 5-step workflow.

| Field | Type | Purpose |
|-------|------|---------|
| `month` | Integer | 1-12 |
| `year` | Integer | e.g., 2025 |
| `status` | Choice | Workflow state |
| `total_gross` | Decimal | Sum of all gross |
| `total_paye` | Decimal | Sum of all PAYE |
| `total_nhif` | Decimal | Sum of all NHIF |
| `total_nssf` | Decimal | Sum of all NSSF |
| `total_pension` | Decimal | Sum of all pension |
| `total_other_deductions` | Decimal | Loans + Advances + Other |
| `total_net` | Decimal | Sum of all net pay |
| `processed_by` | CharField | Who processed |
| `approved_by` | CharField | Who approved |

**Status Workflow:**
```
DRAFT → PROCESSING → APPROVED → PAID → FINALIZED
```

---

### 3. PayrollItem
Individual employee payroll entry for a month.

| Field | Type | Purpose |
|-------|------|---------|
| `payroll` | ForeignKey | Parent MonthlyPayroll |
| `employee` | ForeignKey | Employee record |
| `basic_salary` | Decimal | From employee |
| `housing_allowance` | Decimal | From employee |
| `transport_allowance` | Decimal | From employee |
| `other_allowances` | Decimal | From employee |
| `overtime_pay` | Decimal | Extra hours pay |
| `bonus` | Decimal | Performance bonus |
| `days_worked` | Integer | For pro-rata (default 30) |
| `paye` | Decimal | Calculated tax |
| `nhif` | Decimal | Calculated NHIF |
| `nssf` | Decimal | Calculated NSSF |
| `pension` | Decimal | Calculated pension |
| `loan_deduction` | Decimal | Loan repayment |
| `advance_deduction` | Decimal | Advance repayment |
| `other_deductions` | Decimal | Misc deductions |

**Key Properties:**
```python
@property
def gross_salary(self):
    return (basic + housing + transport + other + overtime + bonus)

@property  
def total_statutory_deductions(self):
    return self.paye + self.nhif + self.nssf + self.pension

@property
def total_other_deductions_calc(self):
    return self.loan_deduction + self.advance_deduction + self.other_deductions

@property
def net_salary(self):
    return self.gross_salary - self.total_deductions
```

---

### 4. CasualLabor
Track daily/casual workers.

| Field | Type | Purpose |
|-------|------|---------|
| `date` | DateField | Work date |
| `worker_name` | CharField | Name or group |
| `number_of_workers` | Integer | How many |
| `task_description` | CharField | Work done |
| `daily_rate` | Decimal | Per worker rate |
| `total_amount` | Decimal | Auto-calculated |
| `payment_status` | Choice | PENDING / PAID |

---

## Statutory Deductions (Kenya 2024)

### PAYE Calculation
```python
# Tax bands (monthly)
if taxable <= 24000:
    paye = taxable * 0.10
elif taxable <= 32333:
    paye = 2400 + (taxable - 24000) * 0.25
elif taxable <= 500000:
    paye = 4483.25 + (taxable - 32333) * 0.30
elif taxable <= 800000:
    paye = 144783.35 + (taxable - 500000) * 0.325
else:
    paye = 242283.35 + (taxable - 800000) * 0.35

# Personal relief (KES 2,400/month)
paye = max(paye - 2400, 0)
```

### NHIF Calculation
Bracket-based rates from KES 150 to KES 1,700 based on gross salary.

### NSSF Calculation
```python
# 6% of gross, capped at KES 2,160
nssf = min(gross * Decimal('0.06'), Decimal('2160.00'))
```

---

## URL Structure

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/payroll/` | dashboard | Overview metrics |
| `/payroll/employees/` | employee_list | List all employees |
| `/payroll/employees/create/` | employee_create | Add user to payroll |
| `/payroll/employees/<pk>/` | employee_detail | View employee + YTD |
| `/payroll/employees/<pk>/edit/` | employee_edit | Edit employee |
| `/payroll/payroll/` | payroll_list | List payroll periods |
| `/payroll/payroll/create/` | payroll_create | New payroll period |
| `/payroll/payroll/<pk>/` | payroll_detail | View payroll items |
| `/payroll/payroll/<pk>/process/` | payroll_process | Workflow actions |
| `/payroll/payroll/<pk>/item/<item_pk>/edit/` | payroll_item_edit | Edit item (DRAFT only) |
| `/payroll/casual/` | casual_labor_list | List casual entries |
| `/payroll/casual/create/` | casual_labor_create | Record casual work |
| `/payroll/casual/<pk>/mark-paid/` | casual_labor_mark_paid | Mark as paid |

---

## Templates (11)

| Template | Purpose |
|----------|---------|
| `base_payroll.html` | Extends core/base.html, adds payroll nav |
| `dashboard.html` | Metrics cards, current payroll status |
| `employee_list.html` | Paginated, filterable employee table |
| `employee_form.html` | Create/Edit with user selection |
| `employee_detail.html` | Profile, YTD breakdown, history |
| `payroll_list.html` | All payroll periods |
| `payroll_form.html` | Create new payroll period |
| `payroll_detail.html` | Items table, workflow buttons |
| `payroll_item_form.html` | Edit deductions (DRAFT only) |
| `casual_labor_list.html` | Casual entries with totals |
| `casual_labor_form.html` | Record casual labor |

---

## Workflows

### Workflow 1: Add Employee to Payroll
```
1. SUPERADMIN navigates to /payroll/employees/create/
2. System shows available users (not in payroll, not other SUPERADMINs)
3. SUPERADMIN selects user → form pre-populates from User profile
4. SUPERADMIN enters: position, salary, allowances, statutory info
5. System generates employee_id (EMP0001, EMP0002...)
6. Employee linked to User via OneToOneField
```

**Business Rules:**
- Only approved, active users shown
- Other SUPERADMINs excluded (protection)
- Name/email synced from User (read-only for linked employees)

---

### Workflow 2: Monthly Payroll Processing
```
1. SUPERADMIN creates payroll: /payroll/payroll/create/
   - Select month/year
   - System auto-generates PayrollItem for each ACTIVE employee
   - Copies salary/allowances from Employee record
   - Calculates statutory deductions
   - Status = DRAFT

2. Review/Edit in DRAFT status: /payroll/payroll/<pk>/
   - Edit any PayrollItem (overtime, bonus, deductions)
   - Edit button visible only in DRAFT

3. Process (DRAFT → PROCESSING):
   - Recalculates ALL statutory deductions
   - Updates payroll totals
   - Sets processed_by, processed_at

4. Approve (PROCESSING → APPROVED):
   - Sets approved_by, approved_at

5. Pay (APPROVED → PAID):
   - Sets paid_at

6. Finalize (PAID → FINALIZED):
   - Sets finalized_at
   - Locks payroll (is_locked = True)
   - No further edits allowed
```

**5-Step Workflow Status:**
```
┌───────┐    ┌────────────┐    ┌──────────┐    ┌──────┐    ┌───────────┐
│ DRAFT │ →  │ PROCESSING │ →  │ APPROVED │ →  │ PAID │ →  │ FINALIZED │
└───────┘    └────────────┘    └──────────┘    └──────┘    └───────────┘
   │              │                                              │
   └── Editable ──┘                                              └── Locked
```

---

### Workflow 3: YTD Calculations
```
1. Navigate to employee detail: /payroll/employees/<pk>/
2. System queries PayrollItem for current year
3. Calculates on-the-fly (not stored):
   - ytd_gross = sum(item.gross_salary)
   - ytd_paye = sum(item.paye)
   - ytd_nhif = sum(item.nhif)
   - etc.
4. Display in YTD breakdown section
```

**Why On-the-fly:**
- ACID compliant (always accurate)
- No sync issues
- Recalculates if PayrollItem edited

---

### Workflow 4: Casual Labor
```
1. Record work: /payroll/casual/create/
   - Date, worker name, count, task, daily rate
   - total_amount = number_of_workers × daily_rate
   - Status = PENDING or PAID

2. Mark as paid: /payroll/casual/<pk>/mark-paid/
   - Changes status to PAID
   - Sets paid_at timestamp
```

---

## Access Control

**ALL views protected by `@superadmin_required` decorator.**

```python
@superadmin_required
def dashboard(request):
    ...
```

**SUPERADMIN Protection Rules:**
1. Cannot add other SUPERADMINs to payroll (only yourself)
2. Cannot edit another SUPERADMIN's employee record
3. Can view but not modify other SUPERADMIN payroll data

---

## Admin Interface

### EmployeeAdmin
- List: employee_id, name, position, status, salary
- Fieldsets: Basic Info, Employment, Salary, Statutory, Remittance, Bank
- Status color badges (green/orange/red)

### MonthlyPayrollAdmin
- List: period, status, totals, lock status
- Inline: PayrollItemInline (tabular)
- Workflow timestamps auto-set on status change
- Finalized payrolls cannot be deleted

### PayrollItemAdmin
- List: employee, period, gross, deductions, net
- Bulk action: "Calculate statutory deductions"

### CasualLaborAdmin
- Date hierarchy
- Bulk action: "Mark selected as paid"

---

## Key Implementation Patterns

### Employee ID Generation
```python
last_employee = Employee.objects.order_by('-id').first()
next_id = (last_employee.id + 1) if last_employee else 1
employee_id = f"EMP{next_id:04d}"  # EMP0001, EMP0002...
```

### User Selection Filter
```python
# Exclude users already in payroll + other SUPERADMINs
available_users = User.objects.filter(
    is_active=True, is_approved=True
).exclude(
    id__in=existing_employee_user_ids
).exclude(
    Q(role='SUPERADMIN') & ~Q(id=request.user.id)
)
```

### Payroll Totals Calculation
```python
def calculate_totals(self):
    items = self.payroll_items.all()
    self.total_gross = sum(item.gross_salary for item in items)
    self.total_paye = sum(item.paye for item in items)
    # ... other totals
    self.total_other_deductions = sum(
        item.loan_deduction + item.advance_deduction + item.other_deductions 
        for item in items
    )
    self.total_net = sum(item.net_salary for item in items)
    self.save()
```

### Remittance Preferences
Displayed in PayrollItem edit form as badges:
```html
<span class="remit-badge remit-badge--employer">Employer remits</span>
<span class="remit-badge remit-badge--employee">Employee remits</span>
```

Used for reporting - identifies who submits statutory deductions to government.

---

## Dashboard Metrics

| Metric | Source |
|--------|--------|
| Total Employees | `Employee.objects.filter(status='ACTIVE').count()` |
| Permanent Count | `filter(employee_type='PERMANENT')` |
| Contract Count | `filter(employee_type='CONTRACT')` |
| Salary Obligation | `sum(emp.gross_salary for emp in active)` |
| Current Payroll Status | `MonthlyPayroll` for current month/year |
| Casual This Month | `CasualLabor` aggregates |
| Pending Casual | `filter(payment_status='PENDING')` |

---

## File Structure

```
apps/payroll/
├── __init__.py
├── admin.py          # 4 ModelAdmin classes
├── apps.py
├── models.py         # Employee, MonthlyPayroll, PayrollItem, CasualLabor
├── urls.py           # 13 URL patterns
├── views.py          # 12 views (all @superadmin_required)
├── migrations/
│   ├── 0001_initial.py
│   ├── 0002_employee_user.py
│   └── 0003_employee_remittance_fields.py
└── templates/payroll/
    ├── base_payroll.html
    ├── dashboard.html
    ├── employee_list.html
    ├── employee_form.html
    ├── employee_detail.html
    ├── payroll_list.html
    ├── payroll_form.html
    ├── payroll_detail.html
    ├── payroll_item_form.html
    ├── casual_labor_list.html
    └── casual_labor_form.html
```

---

## Summary

| Component | Count |
|-----------|-------|
| Models | 4 |
| Views | 12 |
| URLs | 13 |
| Templates | 11 |
| Admin Classes | 4 |
| Migrations | 3 |
