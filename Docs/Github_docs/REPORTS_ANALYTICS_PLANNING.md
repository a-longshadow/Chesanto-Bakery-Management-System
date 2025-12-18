# REPORTS & ANALYTICS PLANNING

> **Status:** Planning Phase  
> **Tech Specs:** See `REPORTS_ANALYTICS_WORKFLOWS.MD` (line 805+ for Cross-App Data Relationships)

---

## CLARIFIED REQUIREMENTS

### 1. Each Report View Must Have:
- ✅ **Print to PDF** - Browser print dialog (works reliably)
- ✅ **CSV Export** - Direct download
- ✅ **Email Report** - Auto-selects current user email + option to add recipients

### 2. Audit Logging:
- ✅ All report generation logged
- ✅ All user actions logged
- Uses existing `apps/audit/` (AuditLog, RequestLog models)

### 3. Centralized Storage Requirement:
- ❌ Railway = read-only filesystem (no local storage)
- ✅ **Django-Q2** for scheduled tasks (uses existing PostgreSQL)
- ✅ Email as archive (Gmail 15GB)

---

## SCHEDULING DECISION: Django-Q2 ✅

### Why Django-Q2:
- Uses existing PostgreSQL as broker (no Redis/RabbitMQ)
- Admin UI for task visibility (what ran, what failed)
- Automatic retries on failure
- Task history stored in DB (built-in audit trail)
- Free, one pip install

### Management Philosophy:
| Responsibility | Owner |
|----------------|-------|
| **Define functions** | Developer (in code) |
| **Schedule timing** | SUPERADMIN (via Django Admin) |
| **Pause/Resume** | SUPERADMIN (via Django Admin) |
| **View history/failures** | SUPERADMIN (via Django Admin) |

**All schedulable functions pre-defined in `apps/reports/tasks.py`. SUPERADMIN cannot create new functions, only manage when existing ones run.**

### Fallback Alternatives:
| Option | When to Use |
|--------|-------------|
| **APScheduler** | If Django-Q2 causes issues on Railway (same features, no admin UI) |
| **Background Thread** | Last resort / debugging only (DIY, no retry logic) |

### Railway Deployment:
```
# Procfile
web: gunicorn config.wsgi
worker: python manage.py qcluster
```

### Configuration:
```python
# settings.py
Q_CLUSTER = {
    'name': 'chesanto',
    'orm': 'default',      # Uses PostgreSQL
    'timeout': 300,        # 5 min max per task
    'retry': 600,          # Retry after 10 min
    'save_limit': 500,     # Keep last 500 task results
    'ack_failures': True,  # Log failed tasks
}
```

---

## TASK FUNCTIONS (Developer-Defined)

All functions live in `apps/reports/tasks.py`. SUPERADMIN schedules via Admin.

### Daily Tasks
| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `daily_sales_summary` | Yesterday's sales totals, by product, by salesperson | SUPERADMIN |
| `daily_production_summary` | Batches produced, ingredients used | SUPERADMIN |
| `daily_inventory_summary` | Stock levels, purchases, usage | SUPERADMIN |
| `daily_profit_loss` | Daily P&L statement | SUPERADMIN |
| `daily_low_stock_alerts` | Items below reorder level | SUPERADMIN |
| `daily_dispatch_summary` | Dispatches sent, crates out | SUPERADMIN |

### Weekly Tasks
| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `weekly_sales_summary` | This week's sales + comparison to last week | SUPERADMIN |
| `weekly_production_summary` | Batches, yields, efficiency | SUPERADMIN |
| `weekly_inventory_summary` | Purchases, usage, current levels | SUPERADMIN |
| `weekly_profit_loss` | Weekly P&L statement | SUPERADMIN |
| `weekly_salesperson_performance` | Revenue, commission, crate accountability | SUPERADMIN |

### Monthly Tasks
| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `monthly_sales_summary` | Full month sales breakdown | SUPERADMIN |
| `monthly_production_summary` | Production metrics for the month | SUPERADMIN |
| `monthly_inventory_summary` | Stock value, movement, valuation | SUPERADMIN |
| `monthly_profit_loss` | Monthly P&L statement | SUPERADMIN |
| `monthly_payroll_summary` | Total payroll, statutory deductions | SUPERADMIN |
| `monthly_casual_labor_summary` | Casual payments for the month | SUPERADMIN |
| `monthly_expense_summary` | Indirect costs + miscellaneous | SUPERADMIN |

### Annual Tasks
| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `annual_sales_summary` | Full year sales breakdown | SUPERADMIN |
| `annual_production_summary` | Yearly production metrics | SUPERADMIN |
| `annual_inventory_summary` | Yearly stock movement + valuation | SUPERADMIN |
| `annual_profit_loss` | Annual P&L statement | SUPERADMIN |
| `annual_payroll_summary` | Yearly payroll + YTD per employee | SUPERADMIN |

### On-Demand Tasks (Callable from Admin or Code)
| Function Name | Purpose | Triggered By |
|---------------|---------|--------------|
| `send_payroll_report` | Email specific payroll period | Payroll FINALIZED |
| `send_custom_date_range_report` | Flexible date range for any report | Manual from Admin |
| `archive_report` | Send report to archive email | Any report generation |

**Total: ~25 pre-defined task functions**

---

## SCHEDULED REPORTS (Admin-Configured Defaults)

### Daily (Suggested: 6:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `daily_sales_summary` | `0 6 * * *` | ✅ |
| `daily_production_summary` | `0 6 * * *` | ✅ |
| `daily_inventory_summary` | `0 6 * * *` | ✅ |
| `daily_profit_loss` | `0 6 * * *` | ✅ |
| `daily_low_stock_alerts` | `0 6 * * *` | ✅ |

### Weekly (Suggested: Monday 7:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `weekly_sales_summary` | `0 7 * * 1` | ✅ |
| `weekly_production_summary` | `0 7 * * 1` | ✅ |
| `weekly_inventory_summary` | `0 7 * * 1` | ✅ |
| `weekly_profit_loss` | `0 7 * * 1` | ✅ |
| `weekly_salesperson_performance` | `0 7 * * 1` | ✅ |

### Monthly (Suggested: 1st of month, 8:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `monthly_sales_summary` | `0 8 1 * *` | ✅ |
| `monthly_production_summary` | `0 8 1 * *` | ✅ |
| `monthly_inventory_summary` | `0 8 1 * *` | ✅ |
| `monthly_profit_loss` | `0 8 1 * *` | ✅ |
| `monthly_payroll_summary` | `0 8 1 * *` | ✅ |

### Annual (Suggested: January 2nd, 9:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `annual_sales_summary` | `0 9 2 1 *` | ✅ |
| `annual_production_summary` | `0 9 2 1 *` | ✅ |
| `annual_inventory_summary` | `0 9 2 1 *` | ✅ |
| `annual_profit_loss` | `0 9 2 1 *` | ✅ |
| `annual_payroll_summary` | `0 9 2 1 *` | ✅ |

**Note:** These are suggested defaults. SUPERADMIN can adjust timing, pause, or disable via Django Admin.

---

## ARCHIVE STRATEGY: Email

### Primary Archive Email:
```
chesanto.reports@gmail.com (or dedicated address) - OR read from .env
```

### Gmail Organization:
- Labels: `payroll`, `sales`, `inventory`, `production`
- Filters: Auto-label by subject prefix `[PAYROLL]`, `[SALES]`, etc.
- Search: Full-text search across all historical reports

### Archive Email Format:
```
To: chesanto.reports@gmail.com
Subject: [PAYROLL] Monthly Summary - December 2025
Body: HTML rendered report
Attachments: payroll_december_2025.csv
```

---

## Current Data Sources (What We Can Draw From)

### From Accounts App
| Data | Insights | Value |
|------|----------|-------|
| User registrations over time | Staff growth trends | HR planning |
| Role distribution | Team composition | Org structure |
| Login activity (last_login) | Active vs inactive users | Security/audit |
| Approval queue | Onboarding bottleneck | Process efficiency |

### From Payroll App
| Data | Insights | Value |
|------|----------|-------|
| Monthly payroll totals | Labor cost trends | Budgeting |
| YTD per employee | Compensation analysis | Tax planning |
| Statutory deductions | PAYE/NHIF/NSSF remittance totals | Compliance |
| Casual labor trends | Seasonal labor needs | Workforce planning |
| Department breakdown | Cost per department | Resource allocation |

### From Inventory App
| Data | Insights | Value |
|------|----------|-------|
| Purchase history | Spending patterns, supplier analysis | Procurement |
| Stock levels | Inventory turnover, dead stock | Cash flow |
| Low stock alerts | Stockout risk | Operations |
| Material usage | Production efficiency | Cost control |

### From Sales App
| Data | Insights | Value |
|------|----------|-------|
| Daily/weekly/monthly sales | Revenue trends | Business health |
| Product performance | Best/worst sellers | Menu optimization |
| Salesperson performance | Commission, crate accountability | Staff management |

### From Production App
| Data | Insights | Value |
|------|----------|-------|
| Batch yields | Production efficiency | Quality control |
| Wastage | Loss analysis | Cost reduction |
| Material consumption vs output | Variance analysis | Recipe costing |

---

## Architecture Decision: Centralized Reports App ✅

```
apps/reports/
├── admin.py              # Django-Q task visibility
├── apps.py               # Register scheduled tasks on ready()
├── views.py              # Report generation views
├── tasks.py              # Django-Q scheduled tasks
├── services/             # Report logic per domain
│   ├── payroll.py
│   ├── inventory.py
│   ├── sales.py
│   ├── production.py
│   └── cross_app.py      # COGS, margins, etc.
├── templates/reports/
│   ├── base_report.html  # Print-friendly base
│   ├── email/            # Email templates
│   ├── dashboard.html
│   └── [report templates]
└── utils/
    ├── export.py         # CSV export
    ├── email.py          # Email with attachments
    └── audit.py          # Report action logging
```

---

## Report Delivery Matrix

| Action | Implementation | Available On |
|--------|---------------|--------------|
| **View** | HTML table, filterable | All reports |
| **Print** | CSS `@media print` + browser dialog | All reports |
| **CSV** | `HttpResponse` with `text/csv` | All reports |
| **Email** | Django EmailMessage + CSV attachment | **All reports (from frontend)** |
| **Scheduled** | Django-Q2 task → Email + Archive | Configured reports |

### Email from Frontend: Universal Feature ✅

Every report view will have an "Email Report" button that:
1. Pre-fills current user's email
2. Allows adding additional recipients
3. Sends HTML report body + CSV attachment
4. Logs action to audit trail

```
┌─────────────────────────────────────────────────────────────┐
│  ANY REPORT VIEW                                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [Export CSV]  [Print]  [📧 Email Report]              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Report Data (table)                                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Audit Requirements

### Report Actions to Log:
```python
# In apps/reports/utils/audit.py
def log_report_action(user, report_type, action, details=None):
    AuditLog.objects.create(
        user=user,
        app_label='reports',
        model_name=report_type,
        action=action,  # 'CREATE' for generate, 'INFO' for email sent
        message=f'{action}: {report_type}',
        changes=details  # JSON with filters used, recipients, etc.
    )
```

### Actions to Track:
- Report viewed (manual)
- Report exported CSV (manual)
- Report printed (via JS callback)
- Report emailed (manual, with recipient list)
- Scheduled report generated (Django-Q2)
- Scheduled report emailed (Django-Q2)
- Task failures (Django-Q2 built-in)

---

## Implementation Phases

### Phase 0: New Model (MiscExpense in Payroll)
1. ⬜ Add `MiscExpenseCategory` and `MiscExpenseRecord` to `apps/payroll/models.py`
2. ⬜ Create migration
3. ⬜ Add admin registration
4. ⬜ Create views for CRUD (similar to CasualLabor)
5. ⬜ Seed default categories

### Phase 1: Foundation
1. ⬜ Install Django-Q2, configure settings
2. ⬜ Create `apps/reports/` structure
3. ⬜ Implement utility functions (export, email, audit)
4. ⬜ Create base_report.html (print-friendly)

### Phase 2: Manual Reports
1. ⬜ Payroll Monthly Summary (view + CSV + email)
2. ⬜ Sales Daily Summary (with aggregate totals)
3. ⬜ Product Performance (per-product + aggregate row)
4. ⬜ Inventory Stock Levels (per-item + aggregate)
5. ⬜ Add report links to existing app templates

### Phase 3: Scheduled Reports
1. ⬜ Configure Django-Q2 schedules
2. ⬜ Daily reports task (6 AM)
3. ⬜ Weekly reports task (Monday 7 AM)
4. ⬜ Monthly reports task (1st, 8 AM)
5. ⬜ Event-triggered tasks (Payroll FINALIZED, etc.)

### Phase 4: Cross-App Analytics
1. ⬜ COGS calculations
2. ⬜ Margin analysis
3. ⬜ Dashboard with KPIs

---

## FRONTEND VIEWS & ROUTES

### Architecture: DRY Approach ✅

**Principle:** Reports app is the **central hub** that links to app-level analytics. Each domain app can have its own lightweight "analytics" tab, but complex/cross-app reports live in the Reports app.

```
┌────────────────────────────────────────────────────────────────┐
│                    REPORTS HUB (/reports/)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Dashboard: KPI Cards + Quick Links to All Reports        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│    ┌─────────────┬───────────┼───────────┬─────────────┐       │
│    ▼             ▼           ▼           ▼             ▼       │
│ /reports/    /reports/   /reports/   /reports/    /reports/    │
│   sales/     inventory/  production/  payroll/     financial/  │
│                                                                 │
│  (Each section has: Daily / Weekly / Monthly / Custom Range)   │
└────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   App Dashboards        App Dashboards        App Dashboards
   have "View Reports"   have "View Reports"   have "View Reports"
   button → redirects    button → redirects    button → redirects
   to /reports/sales/    to /reports/inventory/ etc.
```

---

### URL Structure

```python
# config/urls.py (add to existing)
path('reports/', include('apps.reports.urls')),
path('analytics/', include('apps.analytics.urls')),  # Keep for real-time dashboards
```

```python
# apps/reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # DASHBOARD (Entry Point)
    # ═══════════════════════════════════════════════════════════════
    path('', views.dashboard, name='dashboard'),
    
    # ═══════════════════════════════════════════════════════════════
    # SALES REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('sales/', views.sales_index, name='sales_index'),
    path('sales/daily/', views.sales_daily, name='sales_daily'),
    path('sales/weekly/', views.sales_weekly, name='sales_weekly'),
    path('sales/monthly/', views.sales_monthly, name='sales_monthly'),
    path('sales/annual/', views.sales_annual, name='sales_annual'),
    path('sales/salesperson/', views.salesperson_performance, name='salesperson_performance'),
    path('sales/commissions/', views.commission_report, name='commission_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # INVENTORY REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('inventory/', views.inventory_index, name='inventory_index'),
    path('inventory/daily/', views.inventory_daily, name='inventory_daily'),
    path('inventory/weekly/', views.inventory_weekly, name='inventory_weekly'),
    path('inventory/monthly/', views.inventory_monthly, name='inventory_monthly'),
    path('inventory/annual/', views.inventory_annual, name='inventory_annual'),
    path('inventory/valuation/', views.inventory_valuation, name='inventory_valuation'),
    path('inventory/purchases/', views.purchase_history, name='purchase_history'),
    
    # ═══════════════════════════════════════════════════════════════
    # PRODUCTION REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('production/', views.production_index, name='production_index'),
    path('production/daily/', views.production_daily, name='production_daily'),
    path('production/weekly/', views.production_weekly, name='production_weekly'),
    path('production/monthly/', views.production_monthly, name='production_monthly'),
    path('production/annual/', views.production_annual, name='production_annual'),
    path('production/efficiency/', views.production_efficiency, name='production_efficiency'),
    path('production/stock-movement/', views.stock_movement, name='stock_movement'),
    
    # ═══════════════════════════════════════════════════════════════
    # PAYROLL REPORTS (Monthly / Annual only)
    # ═══════════════════════════════════════════════════════════════
    path('payroll/', views.payroll_index, name='payroll_index'),
    path('payroll/monthly/', views.payroll_monthly, name='payroll_monthly'),
    path('payroll/annual/', views.payroll_annual, name='payroll_annual'),
    path('payroll/casual-labor/', views.casual_labor_report, name='casual_labor_report'),
    path('payroll/misc-expenses/', views.misc_expense_report, name='misc_expense_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # PROFIT & LOSS REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('financial/', views.financial_index, name='financial_index'),
    path('financial/pnl/daily/', views.profit_loss_daily, name='profit_loss_daily'),
    path('financial/pnl/weekly/', views.profit_loss_weekly, name='profit_loss_weekly'),
    path('financial/pnl/monthly/', views.profit_loss_monthly, name='profit_loss_monthly'),
    path('financial/pnl/annual/', views.profit_loss_annual, name='profit_loss_annual'),
    path('financial/product-performance/', views.product_performance, name='product_performance'),
    path('financial/expense-summary/', views.expense_summary, name='expense_summary'),
    
    # ═══════════════════════════════════════════════════════════════
    # EXPORT/EMAIL ENDPOINTS (AJAX) - Available for ALL reports
    # ═══════════════════════════════════════════════════════════════
    path('export/csv/', views.export_csv, name='export_csv'),
    path('email/send/', views.email_report, name='email_report'),
]
```

---

### View Functions (Reusable Pattern)

```python
# apps/reports/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .services import sales, inventory, production, payroll, cross_app
from .utils.export import generate_csv
from .utils.email import send_report_email
from .utils.audit import log_report_action

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED CONTEXT (DRY)
# ═══════════════════════════════════════════════════════════════════════════════

def get_report_context(request, report_type, data):
    """
    Adds common elements to every report view:
    - Export/Print/Email action bar
    - User's email pre-filled
    - Date range info
    """
    return {
        'report_type': report_type,
        'data': data,
        'user_email': request.user.email,
        'can_export': True,  # All reports exportable
        'can_email': True,   # All reports emailable
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    """
    Reports hub - KPI cards + navigation to all report sections
    """
    context = {
        'sections': [
            {'name': 'Sales', 'url': 'reports:sales_index', 'icon': 'cash', 'count': 6},
            {'name': 'Inventory', 'url': 'reports:inventory_index', 'icon': 'boxes', 'count': 4},
            {'name': 'Production', 'url': 'reports:production_index', 'icon': 'industry', 'count': 3},
            {'name': 'Payroll', 'url': 'reports:payroll_index', 'icon': 'users', 'count': 4},
            {'name': 'Financial', 'url': 'reports:financial_index', 'icon': 'chart-line', 'count': 5},
        ],
        # Quick stats (today/this week/this month)
        'quick_stats': cross_app.get_quick_stats(),
    }
    return render(request, 'reports/dashboard.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# SALES REPORTS (Example of section pattern)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def sales_index(request):
    """Sales reports section - list of available reports"""
    reports = [
        {'name': 'Daily Sales Summary', 'url': 'reports:sales_daily', 'desc': 'Revenue by product, salesperson'},
        {'name': 'Weekly Comparison', 'url': 'reports:sales_weekly', 'desc': 'This week vs last week'},
        {'name': 'Monthly Summary', 'url': 'reports:sales_monthly', 'desc': 'Full month breakdown'},
        {'name': 'Salesperson Performance', 'url': 'reports:salesperson_performance', 'desc': 'Commission, targets, crates'},
        {'name': 'Commission Report', 'url': 'reports:commission_report', 'desc': 'Commission earned by salesperson'},
    ]
    return render(request, 'reports/section_index.html', {'section': 'Sales', 'reports': reports})


@login_required
def sales_daily(request):
    """
    Daily Sales Summary
    - Date picker (default: yesterday)
    - Per-product breakdown + aggregate total
    - Per-salesperson breakdown
    """
    selected_date = request.GET.get('date')  # Parse or default to yesterday
    data = sales.get_daily_summary(selected_date)
    
    log_report_action(request.user, 'sales_daily', 'VIEW', {'date': selected_date})
    
    context = get_report_context(request, 'sales_daily', data)
    context['selected_date'] = selected_date
    return render(request, 'reports/sales/daily.html', context)


# ... Similar pattern for all other report views ...


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT & EMAIL (Shared Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def export_csv(request):
    """
    Generic CSV export endpoint
    POST: { report_type: 'sales_daily', filters: {...} }
    """
    report_type = request.POST.get('report_type')
    filters = request.POST.get('filters', {})
    
    # Get data based on report type (dispatch to correct service)
    data = get_report_data(report_type, filters)
    
    # Generate CSV
    csv_content = generate_csv(report_type, data)
    
    log_report_action(request.user, report_type, 'EXPORT_CSV', filters)
    
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_{filters.get("date", "report")}.csv"'
    return response


@login_required
def email_report(request):
    """
    Generic email endpoint
    POST: { report_type, filters, recipients: ['email1', 'email2'] }
    """
    report_type = request.POST.get('report_type')
    filters = request.POST.get('filters', {})
    recipients = request.POST.getlist('recipients', [request.user.email])
    
    # Get data and generate report
    data = get_report_data(report_type, filters)
    
    # Send email with CSV attachment
    send_report_email(report_type, data, recipients)
    
    log_report_action(request.user, report_type, 'EMAIL_SENT', {'recipients': recipients})
    
    return JsonResponse({'success': True, 'sent_to': recipients})
```

---

### Template Structure (DRY)

```
apps/reports/templates/reports/
├── base_report.html          # Print-friendly base (all reports extend this)
├── dashboard.html            # Reports hub with KPI cards
├── section_index.html        # Reusable index for each section (Sales, Inventory, etc.)
├── components/
│   ├── action_bar.html       # Export CSV | Print | Email (included in every report)
│   ├── date_filter.html      # Date range picker component
│   ├── email_modal.html      # Modal for email recipients
│   └── aggregate_row.html    # Total/Summary row styling
├── sales/
│   ├── daily.html
│   ├── weekly.html
│   ├── monthly.html
│   ├── salesperson.html
│   └── commissions.html
├── inventory/
│   ├── valuation.html
│   ├── movement.html
│   ├── purchases.html
│   └── usage.html
├── production/
│   ├── daily.html
│   ├── efficiency.html
│   └── stock_movement.html
├── payroll/
│   ├── monthly.html
│   ├── ytd.html
│   ├── casual_labor.html
│   └── misc_expenses.html
└── financial/
    ├── pnl.html              # P&L Statement
    ├── product_performance.html
    └── expense_summary.html
```

---

### Action Bar Component (Every Report)

```html
<!-- apps/reports/templates/reports/components/action_bar.html -->

<div class="report-actions no-print">
    <div class="btn-group">
        <!-- CSV Export -->
        <button type="button" class="btn btn-outline-primary" 
                onclick="exportCSV('{{ report_type }}')">
            <i class="fas fa-file-csv"></i> Export CSV
        </button>
        
        <!-- Print -->
        <button type="button" class="btn btn-outline-secondary" 
                onclick="window.print()">
            <i class="fas fa-print"></i> Print
        </button>
        
        <!-- Email -->
        <button type="button" class="btn btn-outline-success" 
                data-bs-toggle="modal" data-bs-target="#emailModal">
            <i class="fas fa-envelope"></i> Email Report
        </button>
    </div>
</div>

<!-- Email Modal -->
<div class="modal fade" id="emailModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Email Report</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="emailForm">
                    <input type="hidden" name="report_type" value="{{ report_type }}">
                    
                    <!-- Pre-filled with current user -->
                    <div class="mb-3">
                        <label class="form-label">Send to:</label>
                        <input type="email" name="recipients" value="{{ user_email }}" 
                               class="form-control" required>
                    </div>
                    
                    <!-- Additional recipients -->
                    <div class="mb-3">
                        <label class="form-label">Additional Recipients (optional):</label>
                        <input type="text" name="additional_recipients" 
                               class="form-control" 
                               placeholder="email1@example.com, email2@example.com">
                        <small class="text-muted">Separate multiple emails with commas</small>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="sendEmail()">
                    <i class="fas fa-paper-plane"></i> Send
                </button>
            </div>
        </div>
    </div>
</div>
```

---

### Linking from App Dashboards

Each app dashboard should have a "Reports" link that goes to the relevant reports section:

```html
<!-- Example: apps/sales/templates/sales/dashboard.html -->

<div class="dashboard-header">
    <h1>Sales Dashboard</h1>
    <div class="dashboard-actions">
        <!-- Quick action to full reports -->
        <a href="{% url 'reports:sales_index' %}" class="btn btn-outline-primary">
            <i class="fas fa-chart-bar"></i> View All Reports
        </a>
    </div>
</div>

<!-- Or as sidebar link -->
<nav class="sidebar">
    <a href="{% url 'sales:dashboard' %}">Dashboard</a>
    <a href="{% url 'sales:dispatch_list' %}">Dispatches</a>
    <a href="{% url 'reports:sales_index' %}" class="reports-link">
        <i class="fas fa-file-alt"></i> Sales Reports
    </a>
</nav>
```

---

### Analytics vs Reports: Clear Separation

| Feature | Analytics (`/analytics/`) | Reports (`/reports/`) |
|---------|---------------------------|------------------------|
| **Purpose** | Real-time monitoring | Historical analysis |
| **Data** | Live aggregations | Date-range filtered |
| **Charts** | Yes (Chart.js) | Optional (mostly tables) |
| **Export** | No | Yes (CSV, Email) |
| **Print** | No | Yes |
| **Scheduled** | No | Yes (Django-Q2) |
| **Audit Log** | No | Yes |


- `apps/analytics/` - Real-time dashboards (charts, live KPIs)
- `apps/reports/` - Historical reports (exportable, schedulable, audited)

---

### Role-Based Access

```python
# apps/reports/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def report_access_required(allowed_roles=None):
    """
    Decorator to control report access by role
    Default: SUPERADMIN, ADMIN, ACCOUNTANT can access all reports
    """
    if allowed_roles is None:
        allowed_roles = ['SUPERADMIN', 'ADMIN', 'ACCOUNTANT']
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                messages.error(request, "You don't have permission to view this report.")
                return redirect('reports:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Usage:
@login_required
@report_access_required(['SUPERADMIN', 'ADMIN'])
def payroll_monthly(request):
    # Only SUPERADMIN and ADMIN can view payroll reports
    ...
```

---

### Navigation Summary

| From | Link Text | Goes To |
|------|-----------|---------|
| Main Nav | Reports | `/reports/` (dashboard) |
| Sales Dashboard | View All Reports | `/reports/sales/` |
| Inventory Dashboard | View All Reports | `/reports/inventory/` |
| Production Dashboard | View All Reports | `/reports/production/` |
| Payroll Dashboard | View All Reports | `/reports/payroll/` |
| Reports Dashboard | Sales Reports | `/reports/sales/` |
| Reports Dashboard | Financial Reports | `/reports/financial/` |
| Any Report | ← Back to Section | `/reports/{section}/` |
| Any Report | ← All Reports | `/reports/` |

---

## Next Steps

1. ✅ Planning complete (this document)
2. ⬜ Create `apps/reports/` structure
3. ⬜ Install and configure Django-Q2
4. ⬜ Build first report: Payroll Monthly Summary
5. ⬜ Test scheduled task execution
6. ⬜ Expand to other domains

---

## COMPLETE URL REFERENCE

### Reports App Routes (`/reports/`)

| URL | View Name | Purpose | Access | Email |
|-----|-----------|---------|--------|-------|
| `/reports/` | `dashboard` | Reports hub with KPIs | All | - |
| **SALES** |||||
| `/reports/sales/` | `sales_index` | Sales reports list | All | - |
| `/reports/sales/daily/` | `sales_daily` | Daily sales summary | All | ✅ |
| `/reports/sales/weekly/` | `sales_weekly` | Weekly sales summary | All | ✅ |
| `/reports/sales/monthly/` | `sales_monthly` | Monthly sales summary | All | ✅ |
| `/reports/sales/annual/` | `sales_annual` | Annual sales summary | All | ✅ |
| `/reports/sales/salesperson/` | `salesperson_performance` | Per-salesperson metrics | All | ✅ |
| `/reports/sales/commissions/` | `commission_report` | Commission breakdown | All | ✅ |
| **INVENTORY** |||||
| `/reports/inventory/` | `inventory_index` | Inventory reports list | All | - |
| `/reports/inventory/daily/` | `inventory_daily` | Daily inventory summary | All | ✅ |
| `/reports/inventory/weekly/` | `inventory_weekly` | Weekly inventory summary | All | ✅ |
| `/reports/inventory/monthly/` | `inventory_monthly` | Monthly inventory summary | All | ✅ |
| `/reports/inventory/annual/` | `inventory_annual` | Annual inventory summary | All | ✅ |
| `/reports/inventory/valuation/` | `inventory_valuation` | Stock values | All | ✅ |
| `/reports/inventory/purchases/` | `purchase_history` | Purchase log | All | ✅ |
| **PRODUCTION** |||||
| `/reports/production/` | `production_index` | Production reports list | All | - |
| `/reports/production/daily/` | `production_daily` | Daily production summary | All | ✅ |
| `/reports/production/weekly/` | `production_weekly` | Weekly production summary | All | ✅ |
| `/reports/production/monthly/` | `production_monthly` | Monthly production summary | All | ✅ |
| `/reports/production/annual/` | `production_annual` | Annual production summary | All | ✅ |
| `/reports/production/efficiency/` | `production_efficiency` | Yield analysis | All | ✅ |
| `/reports/production/stock-movement/` | `stock_movement` | Product stock flow | All | ✅ |
| **PAYROLL** (Monthly & Annual only) |||||
| `/reports/payroll/` | `payroll_index` | Payroll reports list | Admin+ | - |
| `/reports/payroll/monthly/` | `payroll_monthly` | Monthly payroll summary | Admin+ | ✅ |
| `/reports/payroll/annual/` | `payroll_annual` | Annual payroll + YTD | Admin+ | ✅ |
| `/reports/payroll/casual-labor/` | `casual_labor_report` | Casual payments | Admin+ | ✅ |
| `/reports/payroll/misc-expenses/` | `misc_expense_report` | Miscellaneous expenses | Admin+ | ✅ |
| **FINANCIAL / P&L** |||||
| `/reports/financial/` | `financial_index` | Financial reports list | Admin+ | - |
| `/reports/financial/pnl/daily/` | `profit_loss_daily` | Daily P&L | Admin+ | ✅ |
| `/reports/financial/pnl/weekly/` | `profit_loss_weekly` | Weekly P&L | Admin+ | ✅ |
| `/reports/financial/pnl/monthly/` | `profit_loss_monthly` | Monthly P&L | Admin+ | ✅ |
| `/reports/financial/pnl/annual/` | `profit_loss_annual` | Annual P&L | Admin+ | ✅ |
| `/reports/financial/product-performance/` | `product_performance` | Product profitability | Admin+ | ✅ |
| `/reports/financial/expense-summary/` | `expense_summary` | All expenses | Admin+ | ✅ |
| **ACTIONS** |||||
| `/reports/export/csv/` | `export_csv` | CSV download (POST) | All | - |
| `/reports/email/send/` | `email_report` | Send any report (POST) | All | - |

### Analytics App Routes (`/analytics/`) - Existing

| URL | View Name | Purpose | Email |
|-----|-----------|---------|-------|
| `/analytics/dashboard/` | `dashboard_view` | Real-time KPIs (8 charts) | ✅ |
| `/analytics/products/` | `product_performance_view` | Live product metrics | ✅ |
| `/analytics/inventory/` | `inventory_status_view` | Current stock levels | ✅ |
| `/analytics/sales/` | `sales_trends_view` | Sales trends (disabled) | ✅ |
| `/analytics/payroll/` | `payroll_analysis_view` | Payroll patterns (disabled) | ✅ |

**Total Reports Routes: 35**
**Total Analytics Routes: 5**
**Email-capable Views: 35+ (all report & analytics views)**


--------------------
Summarized conversation historyExcellent! This is very helpful. Looking at your Excel screenshots, I can see the full picture of what you're currently tracking. Let me analyze and categorize:

## Analysis of Current Excel Reports

### From Screenshots:

**1. Product Performance (per product: Bread, KDF, Scones)**
- Total Net Sales
- Total Production Cost
- Gross Profit/Loss
- Less: Packaging Materials
- Less: Commission
- **Net Profit per Product**

**2. Closing Stock Reports**
- Product Stock Value (Bread, KDF, Scones units × cost)
- Inventory Stock Value (Unga, Sugar, Cooking Fat, etc. × unit price)

**3. Monthly P&L / Financial Summary**
- Revenue by product (Bread, KDF, Scones)
- Cost of Sales:
  - Direct Expenses (Flour, Cooking Fat, Oil, Sugar, Yeast, etc.)
  - Indirect Costs (Diesel, Firewood, Fuel, Electricity)
  - Direct Salaries (Production, Sales, Casuals)
  - Commissions (per product)
- Gross Profit/Loss

**4. Daily Stock Movement**
- Opening Stock → Mixes → Available → Dispatches by Salesperson → Returns → Closing Stock
- Error tracking (discrepancies)

**5. Daily Inventory Movement**
- Opening → Additional (purchases) → Daily Usage → Closing Stock

**6. Daily Expenditure Log**
- Date, Description, Quantity, Unit Cost, Total

**7. Sales Commission Tracking**
- Date, Salesman, Sales Type, Expected Banking, Total Sales
- Sales Target, Sales Above Target, Commission %, Commission Earned

---

## Proposed Report Structure

### DAILY REPORTS (Operational)

| Report | What It Shows | Data Source | Priority |
|--------|---------------|-------------|----------|
| **Daily Sales Summary** | Revenue by product, by salesperson + total | SalesReturn | ✅ Essential |
| **Daily Stock Movement** | Opening → Production → Dispatch → Returns → Closing | ProductStock, Dispatch, Return | ✅ Essential |
| **Daily Inventory Usage** | Opening → Purchases → Usage → Closing per ingredient | Inventory Details/Output | ✅ Essential |
| **Daily Expenditure** | All costs logged for the day | Inventory Indirect Outputs (items 16-23) + MiscExpenseRecord | ✅ Essential |
| **Daily Dispatch Summary** | Crates out by salesperson | SalesDispatch | ✅ Essential |
| **Daily Discrepancy/Error** | Stock variances (expected vs actual) | Calculated | ⚠️ Important |

### WEEKLY REPORTS (Trend Analysis)

| Report | What It Shows | Data Source | Priority |
|--------|---------------|-------------|----------|
| **Weekly Sales Comparison** | This week vs last week by product | SalesReturn | ✅ Essential |
| **Weekly Salesperson Performance** | Revenue, commission, targets, crates | SalesReturn, Dispatch | ✅ Essential |
| **Weekly Inventory Movement** | Purchases, usage, trends | Inventory | ⚠️ Important |
| **Weekly Production Summary** | Batches, yields, efficiency | ProductionBatch | ⚠️ Important |

### MONTHLY REPORTS (Financial/Management)

| Report | What It Shows | Data Source | Priority |
|--------|---------------|-------------|----------|
| **Monthly P&L Statement** | Full Income Statement (aggregate) | Cross-app | ✅ Essential |
| **Product Performance** | Revenue, COGS, Gross Profit, Net Profit per product + aggregate total | Cross-app | ✅ Essential |
| **Salesperson Performance** | Monthly totals, commission (uses User.sales_target) | SalesReturn, User | ✅ Essential |
| **Inventory Valuation** | Closing stock value (products + ingredients) per-item + total | All stock tables | ✅ Essential |
| **Payroll Summary** | Salaries, deductions, net pay | Payroll | ✅ Essential |
| **Casual Labor Summary** | Total casual payments | CasualLabor | ✅ Essential |
| **Expense Summary** | Indirect costs + miscellaneous by category | Inventory Outputs + MiscExpenseRecord | ⚠️ Important |

### YEARLY REPORTS

| Report | What It Shows | Priority |
|--------|---------------|----------|
| **Annual P&L** | 12-month summary | ✅ Essential |
| **Annual Sales Trend** | Month-by-month comparison | ⚠️ Important |
| **YTD Employee Earnings** | For tax purposes | ✅ Essential |

---

## Gap Analysis: RESOLVED ✅

### Indirect Costs: Already in Inventory ✅

Most indirect costs are already tracked in Inventory App (items 16-23):
- ✅ Diesel (L) - has purchases + outputs tables
- ✅ Firewood (units) - has purchases + outputs tables
- ✅ Fuel Bolero (units) - has purchases + outputs tables
- ✅ Electricity (tokens) - has purchases + outputs tables
- ✅ Fuel for Transport Trucks (L) - has purchases + outputs tables
- ✅ Crates (units) - has purchases + outputs tables
- ✅ Packaging (units) - has purchases + outputs tables
- ✅ Hair Nets (units) - has purchases + outputs tables

**Data Source:** `INVENTORY_APP_WORKFLOWS.md` line 190+

### Need New Model: Miscellaneous Expenses (in Payroll) ✅

For items NOT tracked in Inventory (similar to CasualLabor pattern):
- Petty Cash disbursements
- CCTV Repairs
- Transaction Costs (bank fees, M-Pesa costs)
- Tyres/Vehicle maintenance
- Other operational expenses

**Decision:** Create `MiscExpenseDetails` + `MiscExpenseRecord` in `apps/payroll/` 
(follows same 2-table pattern as CasualLabor)

### Commission Calculation: Already Configured ✅

User model already has:
- `sales_target` - stored per salesperson
- `commission_percentage` - stored per salesperson
- Commission rules handled in Sales app

**No new models needed for commission.**

---

## Proposed Consolidation

### Merge These:
| Excel Sheets | → Merged Report |
|--------------|-----------------|
| Bread Performance + KDF Performance + Scones Performance | **Product Performance Report** (all products in one table + aggregate total row) |
| Closing Stock Product + Closing Stock Inventory | **Inventory Valuation Report** (products + ingredients) |
| Daily stock movement (3 sheets) | **Daily Stock Report** (all products in one) |

### Report View Modes:
| Report | Breakdown View | Aggregated View |
|--------|---------------|-----------------|
| **Product Performance** | Per-product P&L (Bread, KDF, Scones rows) | Total row summing all products |
| **Sales Summary** | Per-salesperson revenue | Total sales for period |
| **Inventory Valuation** | Per-item stock value | Total stock value |

### Keep Separate:
- Daily Expenditure (Inventory indirect costs + new MiscExpense model)
- Sales Commissions (already modeled in User)
- Staff Salaries (Payroll app)
- P&L Statement (cross-app calculation)

---

## Updated Task Functions

```python
# apps/reports/tasks.py

# ═══════════════════════════════════════════════════════════════════════════════
# DAILY (6 functions) - Run 6:00 AM EAT
# ═══════════════════════════════════════════════════════════════════════════════
daily_sales_summary()           # Revenue by product, by salesperson + aggregate total
daily_production_summary()      # Batches produced, yields, ingredients used
daily_inventory_summary()       # Stock levels, purchases, usage for the day
daily_profit_loss()             # Daily P&L statement
daily_low_stock_alerts()        # Items below reorder level
daily_dispatch_summary()        # Crates out by salesperson

# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY (5 functions) - Run Monday 7:00 AM EAT
# ═══════════════════════════════════════════════════════════════════════════════
weekly_sales_summary()          # This week's sales + comparison to last week
weekly_production_summary()     # Batches, yields, efficiency
weekly_inventory_summary()      # Purchases, usage, trends
weekly_profit_loss()            # Weekly P&L statement
weekly_salesperson_performance()# Revenue, commission, crates

# ═══════════════════════════════════════════════════════════════════════════════
# MONTHLY (7 functions) - Run 1st of month 8:00 AM EAT
# ═══════════════════════════════════════════════════════════════════════════════
monthly_sales_summary()         # Full month sales breakdown
monthly_production_summary()    # Production metrics for the month
monthly_inventory_summary()     # Stock value, movement, valuation
monthly_profit_loss()           # Monthly P&L statement
monthly_payroll_summary()       # Total payroll, statutory deductions
monthly_casual_labor_summary()  # Casual payments for the month
monthly_expense_summary()       # Indirect costs + MiscExpenseRecord

# ═══════════════════════════════════════════════════════════════════════════════
# ANNUAL (5 functions) - Run January 2nd 9:00 AM EAT
# ═══════════════════════════════════════════════════════════════════════════════
annual_sales_summary()          # Full year sales breakdown
annual_production_summary()     # Yearly production metrics
annual_inventory_summary()      # Yearly stock movement + valuation
annual_profit_loss()            # Annual P&L statement
annual_payroll_summary()        # Yearly payroll + YTD per employee

# ═══════════════════════════════════════════════════════════════════════════════
# ON-DEMAND (3 functions) - Triggered manually or by events
# ═══════════════════════════════════════════════════════════════════════════════
send_report_email()             # Generic: send any report to recipients
send_payroll_report()           # Triggered when Payroll FINALIZED
archive_report()                # Send report to archive email
```

**Total: 26 task functions**

---

## NEW MODEL: MiscExpenseRecord (in Payroll App)

Follows same pattern as CasualLabor (2 tables: Details + Records):

```python
# apps/payroll/models.py

class MiscExpenseCategory(models.Model):
    """Categories for miscellaneous expenses not tracked in Inventory"""
    name = models.CharField(max_length=100, unique=True)
    # Examples: 'Vehicle Maintenance', 'Bank Fees', 'Repairs', 'Petty Cash'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Misc Expense Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class MiscExpenseRecord(models.Model):
    """Individual expense records (like CasualLaborRecord)"""
    category = models.ForeignKey(MiscExpenseCategory, on_delete=models.PROTECT)
    date = models.DateField()
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    receipt_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='+'
    )
    
    class Meta:
        ordering = ['-date', '-created_at']
    
    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.date} - {self.category.name}: {self.description}"
```

### Default Categories to Seed:
| Category | Example Expenses |
|----------|-----------------|
| Vehicle Maintenance | Tyres, repairs, servicing |
| Bank/Transaction Fees | M-Pesa costs, bank charges |
| Equipment Repairs | CCTV, machinery, electrical |
| Petty Cash | Small operational expenses |
| Licenses & Permits | Business permits, renewals |
| Other | Miscellaneous |

---
