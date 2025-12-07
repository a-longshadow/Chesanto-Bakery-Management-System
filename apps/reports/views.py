"""
Reports App Views
=================
All views require ACCOUNTANT role or higher.
Built incrementally - start with dashboard, then add report views.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .decorators import report_access_required
from .services import SalesReportService, ProductionReportService, InventoryReportService, FinancialReportService


@login_required
@report_access_required
def dashboard(request):
    """Reports hub with KPIs and quick links."""
    today = timezone.now().date()
    
    context = {
        'today': today,
        'page_title': 'Reports Dashboard',
    }
    return render(request, 'reports/dashboard.html', context)


# ═══════════════════════════════════════════════════════════════
# INDEX PAGES (Stubs - to be expanded)
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def sales_index(request):
    """Sales reports landing page."""
    return render(request, 'reports/sales/index.html', {
        'page_title': 'Sales Reports',
        'today': timezone.now().date(),
    })


@login_required
@report_access_required
def inventory_index(request):
    """Inventory reports landing page."""
    return render(request, 'reports/inventory/index.html', {
        'page_title': 'Inventory Reports',
        'today': timezone.now().date(),
    })


@login_required
@report_access_required
def production_index(request):
    """Production reports landing page."""
    return render(request, 'reports/production/index.html', {
        'page_title': 'Production Reports',
        'today': timezone.now().date(),
    })


@login_required
@report_access_required
def payroll_index(request):
    """Payroll reports landing page."""
    return render(request, 'reports/payroll/index.html', {
        'page_title': 'Payroll Reports',
        'today': timezone.now().date(),
    })


@login_required
@report_access_required
def financial_index(request):
    """Financial/P&L reports landing page."""
    return render(request, 'reports/financial/index.html', {
        'page_title': 'Financial Reports',
        'today': timezone.now().date(),
    })


# ═══════════════════════════════════════════════════════════════
# SALES REPORTS (Stubs)
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def sales_daily(request):
    """Daily Sales Report - Fully implemented."""
    from datetime import datetime
    
    # Get date from query param or default to today
    date_str = request.GET.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    # Get report data from service
    summary = SalesReportService.get_daily_summary(report_date)
    
    # Navigation dates
    prev_date = report_date - timedelta(days=1)
    next_date = report_date + timedelta(days=1)
    can_go_next = next_date <= timezone.now().date()
    
    context = {
        'page_title': 'Daily Sales Report',
        'today': timezone.now().date(),
        'report_date': report_date,
        'prev_date': prev_date,
        'next_date': next_date if can_go_next else None,
        **summary,  # Unpack all summary data
    }
    return render(request, 'reports/sales/daily.html', context)


@login_required
@report_access_required
def sales_weekly(request):
    """Weekly Sales Report - Fully implemented."""
    from datetime import datetime
    
    # Get week start from query param or default to current week
    date_str = request.GET.get('week_start')
    if date_str:
        try:
            week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    else:
        week_start = None
    
    # Get report data from service
    summary = SalesReportService.get_weekly_summary(week_start)
    
    # Navigation weeks
    prev_week = summary['start_date'] - timedelta(days=7)
    next_week = summary['start_date'] + timedelta(days=7)
    can_go_next = next_week <= timezone.now().date()
    
    context = {
        'page_title': 'Weekly Sales Report',
        'today': timezone.now().date(),
        'prev_week': prev_week,
        'next_week': next_week if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/sales/weekly.html', context)


@login_required
@report_access_required
def sales_monthly(request):
    """Monthly Sales Report - Fully implemented."""
    # Get year/month from query params or default to current
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    # Get report data from service
    summary = SalesReportService.get_monthly_summary(year, month)
    
    # Navigation months
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Monthly Sales Report',
        'today': today,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/sales/monthly.html', context)


@login_required
@report_access_required
def sales_annual(request):
    """Annual Sales Report - Fully implemented."""
    # Get year from query param or default to current
    year_str = request.GET.get('year')
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None
    else:
        year = None
    
    # Get report data from service
    summary = SalesReportService.get_annual_summary(year)
    
    # Navigation years
    prev_year = summary['year'] - 1
    next_year = summary['year'] + 1
    can_go_next = next_year <= timezone.now().year
    
    context = {
        'page_title': 'Annual Sales Report',
        'today': timezone.now().date(),
        'prev_year': prev_year,
        'next_year': next_year if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/sales/annual.html', context)


@login_required
@report_access_required
def salesperson_performance(request):
    """Salesperson Performance Report - Fully implemented."""
    from datetime import datetime
    from calendar import monthrange
    
    # Get year/month from query params or default to current
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    # Get report data
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Salesperson Performance',
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **data,
    }
    return render(request, 'reports/sales/salesperson_performance.html', context)


@login_required
@report_access_required
def commission_report(request):
    """Commission Report - Fully implemented."""
    # Get year/month from query params or default to current
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    
    # Get report data
    data = SalesReportService.get_commission_report(year, month)
    
    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Commission Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **data,
    }
    return render(request, 'reports/sales/commission_report.html', context)


# ═══════════════════════════════════════════════════════════════
# INVENTORY REPORTS
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def inventory_daily(request):
    """Daily Inventory Report - Fully implemented."""
    from datetime import datetime
    
    date_str = request.GET.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    summary = InventoryReportService.get_daily_summary(report_date)
    
    prev_date = report_date - timedelta(days=1)
    next_date = report_date + timedelta(days=1)
    can_go_next = next_date <= timezone.now().date()
    
    context = {
        'page_title': 'Daily Inventory Report',
        'today': timezone.now().date(),
        'report_date': report_date,
        'prev_date': prev_date,
        'next_date': next_date if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/inventory/daily.html', context)


@login_required
@report_access_required
def inventory_weekly(request):
    """Weekly Inventory Report - Fully implemented."""
    from datetime import datetime
    
    date_str = request.GET.get('week_start')
    if date_str:
        try:
            week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    else:
        week_start = None
    
    summary = InventoryReportService.get_weekly_summary(week_start)
    
    prev_week = summary['start_date'] - timedelta(days=7)
    next_week = summary['start_date'] + timedelta(days=7)
    can_go_next = next_week <= timezone.now().date()
    
    context = {
        'page_title': 'Weekly Inventory Report',
        'prev_week': prev_week,
        'next_week': next_week if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/inventory/weekly.html', context)


@login_required
@report_access_required
def inventory_monthly(request):
    """Monthly Inventory Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = InventoryReportService.get_monthly_summary(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Monthly Inventory Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/inventory/monthly.html', context)


@login_required
@report_access_required
def inventory_annual(request):
    """Annual Inventory Report - Fully implemented."""
    year_str = request.GET.get('year')
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None
    else:
        year = None
    
    summary = InventoryReportService.get_annual_summary(year)
    
    prev_year = summary['year'] - 1
    next_year = summary['year'] + 1
    can_go_next = next_year <= timezone.now().year
    
    context = {
        'page_title': 'Annual Inventory Report',
        'prev_year': prev_year,
        'next_year': next_year if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/inventory/annual.html', context)


@login_required
@report_access_required
def inventory_valuation(request):
    """Current inventory valuation report - shows stock levels and values."""
    stock_levels = InventoryReportService.get_current_stock_levels()
    
    # Calculate totals
    total_value = sum(item.get('value', 0) for item in stock_levels)
    low_stock_items = [item for item in stock_levels if item.get('is_low', False)]
    
    context = {
        'page_title': 'Inventory Valuation',
        'today': timezone.now().date(),
        'stock_levels': stock_levels,
        'total_value': total_value,
        'total_items': len(stock_levels),
        'low_stock_count': len(low_stock_items),
        'low_stock_items': low_stock_items,
    }
    return render(request, 'reports/inventory/valuation.html', context)


@login_required
@report_access_required
def purchase_history(request):
    """Purchase history report for a date range."""
    from datetime import datetime
    
    # Get date range from query params
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    today = timezone.now().date()
    
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    purchases = InventoryReportService.get_purchase_summary(start_date, end_date)
    
    # Calculate totals
    total_spent = sum(p.get('total_cost', 0) for p in purchases)
    total_orders = sum(p.get('purchase_count', 0) for p in purchases)
    
    context = {
        'page_title': 'Purchase History',
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        'purchases': purchases,
        'total_spent': total_spent,
        'total_orders': total_orders,
        'items_purchased': len(purchases),
    }
    return render(request, 'reports/inventory/purchase_history.html', context)


# ═══════════════════════════════════════════════════════════════
# PRODUCTION REPORTS (Stubs)
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def production_daily(request):
    """Daily Production Report - Fully implemented."""
    from datetime import datetime
    
    # Get date from query param or default to today
    date_str = request.GET.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    # Get report data from service
    summary = ProductionReportService.get_daily_summary(report_date)
    
    # Navigation dates
    prev_date = report_date - timedelta(days=1)
    next_date = report_date + timedelta(days=1)
    can_go_next = next_date <= timezone.now().date()
    
    context = {
        'page_title': 'Daily Production Report',
        'today': timezone.now().date(),
        'report_date': report_date,
        'prev_date': prev_date,
        'next_date': next_date if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/production/daily.html', context)


@login_required
@report_access_required
def production_weekly(request):
    """Weekly Production Report - Fully implemented."""
    from datetime import datetime
    
    date_str = request.GET.get('week_start')
    if date_str:
        try:
            week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    else:
        week_start = None
    
    summary = ProductionReportService.get_weekly_summary(week_start)
    
    prev_week = summary['start_date'] - timedelta(days=7)
    next_week = summary['start_date'] + timedelta(days=7)
    can_go_next = next_week <= timezone.now().date()
    
    context = {
        'page_title': 'Weekly Production Report',
        'prev_week': prev_week,
        'next_week': next_week if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/production/weekly.html', context)


@login_required
@report_access_required
def production_monthly(request):
    """Monthly Production Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = ProductionReportService.get_monthly_summary(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Monthly Production Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/production/monthly.html', context)


@login_required
@report_access_required
def production_annual(request):
    """Annual Production Report - Fully implemented."""
    year_str = request.GET.get('year')
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None
    else:
        year = None
    
    summary = ProductionReportService.get_annual_summary(year)
    
    prev_year = summary['year'] - 1
    next_year = summary['year'] + 1
    can_go_next = next_year <= timezone.now().year
    
    context = {
        'page_title': 'Annual Production Report',
        'prev_year': prev_year,
        'next_year': next_year if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/production/annual.html', context)


@login_required
@report_access_required
def production_efficiency(request):
    """Production efficiency report - yield variance analysis."""
    from datetime import datetime
    from calendar import monthrange
    
    # Get date range from query params
    year_str = request.GET.get('year')
    month_str = request.GET.get('month')
    
    today = timezone.now().date()
    
    if year_str and month_str:
        try:
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    
    summary = ProductionReportService.get_monthly_summary(year, month)
    
    # Calculate efficiency metrics
    total_units = summary.get('total_units', 0)
    expected_total = summary.get('totals', {}).get('expected_total', 0)
    yield_variance = summary.get('yield_variance', 0)
    
    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Production Efficiency',
        'today': today,
        'year': year,
        'month': month,
        'total_units': total_units,
        'expected_total': expected_total,
        'yield_variance': yield_variance,
        'batch_count': summary.get('batch_count', 0),
        'total_cost': summary.get('total_cost', 0),
        'products': summary.get('products', []),
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
    }
    return render(request, 'reports/production/efficiency.html', context)


@login_required
@report_access_required
def stock_movement(request):
    """Stock movement report - tracks purchases and usage."""
    from datetime import datetime
    
    # Get date range from query params
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    today = timezone.now().date()
    
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    # Get stock levels and purchases
    stock_levels = InventoryReportService.get_current_stock_levels()
    purchases = InventoryReportService.get_purchase_summary(start_date, end_date)
    
    # Create a combined view
    purchase_dict = {p['item_id']: p for p in purchases}
    
    movement_data = []
    for stock in stock_levels:
        item_id = stock['item_id']
        purchase_info = purchase_dict.get(item_id, {})
        movement_data.append({
            **stock,
            'qty_purchased': purchase_info.get('total_qty', 0),
            'purchase_cost': purchase_info.get('total_cost', 0),
            'purchase_count': purchase_info.get('purchase_count', 0),
        })
    
    # Calculate totals
    total_value = sum(item.get('value', 0) for item in stock_levels)
    total_purchased = sum(p.get('total_cost', 0) for p in purchases)
    
    context = {
        'page_title': 'Stock Movement',
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        'movement_data': movement_data,
        'total_value': total_value,
        'total_purchased': total_purchased,
        'item_count': len(movement_data),
    }
    return render(request, 'reports/inventory/stock_movement.html', context)


# ═══════════════════════════════════════════════════════════════
# PAYROLL REPORTS
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def payroll_monthly(request):
    """Monthly Payroll Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = FinancialReportService.get_payroll_monthly(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Monthly Payroll Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/payroll/monthly.html', context)


@login_required
@report_access_required
def payroll_annual(request):
    """Annual Payroll Report - Fully implemented."""
    year_str = request.GET.get('year')
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None
    else:
        year = None
    
    summary = FinancialReportService.get_payroll_annual(year)
    
    prev_year = summary['year'] - 1
    next_year = summary['year'] + 1
    can_go_next = next_year <= timezone.now().year
    
    context = {
        'page_title': 'Annual Payroll Report',
        'prev_year': prev_year,
        'next_year': next_year if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/payroll/annual.html', context)


@login_required
@report_access_required
def casual_labor_report(request):
    """Casual Labor Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = FinancialReportService.get_casual_labor_report(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Casual Labor Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/payroll/casual_labor.html', context)


@login_required
@report_access_required
def misc_expense_report(request):
    """Misc Expense Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = FinancialReportService.get_misc_expense_report(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Misc Expense Report',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/payroll/misc_expense.html', context)


# ═══════════════════════════════════════════════════════════════
# FINANCIAL REPORTS (P&L)
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def profit_loss_daily(request):
    """Daily P&L Report - Fully implemented."""
    from datetime import datetime
    
    date_str = request.GET.get('date')
    if date_str:
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()
    
    summary = FinancialReportService.get_daily_pnl(report_date)
    
    prev_date = report_date - timedelta(days=1)
    next_date = report_date + timedelta(days=1)
    can_go_next = next_date <= timezone.now().date()
    
    context = {
        'page_title': 'Daily Profit & Loss',
        'report_date': report_date,
        'prev_date': prev_date,
        'next_date': next_date if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/financial/daily_pnl.html', context)


@login_required
@report_access_required
def profit_loss_weekly(request):
    """Weekly P&L Report - Fully implemented."""
    from datetime import datetime
    
    date_str = request.GET.get('week_start')
    if date_str:
        try:
            week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    else:
        week_start = None
    
    summary = FinancialReportService.get_weekly_pnl(week_start)
    
    prev_week = summary['start_date'] - timedelta(days=7)
    next_week = summary['start_date'] + timedelta(days=7)
    can_go_next = next_week <= timezone.now().date()
    
    context = {
        'page_title': 'Weekly Profit & Loss',
        'prev_week': prev_week,
        'next_week': next_week if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/financial/weekly_pnl.html', context)


@login_required
@report_access_required
def profit_loss_monthly(request):
    """Monthly P&L Report - Fully implemented."""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = None
            month = None
    else:
        year = None
        month = None
    
    summary = FinancialReportService.get_monthly_pnl(year, month)
    
    if summary['month'] == 1:
        prev_year, prev_month = summary['year'] - 1, 12
    else:
        prev_year, prev_month = summary['year'], summary['month'] - 1
    
    if summary['month'] == 12:
        next_year, next_month = summary['year'] + 1, 1
    else:
        next_year, next_month = summary['year'], summary['month'] + 1
    
    today = timezone.now().date()
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Monthly Profit & Loss',
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/financial/monthly_pnl.html', context)


@login_required
@report_access_required
def profit_loss_annual(request):
    """Annual P&L Report - Fully implemented."""
    year_str = request.GET.get('year')
    if year_str:
        try:
            year = int(year_str)
        except ValueError:
            year = None
    else:
        year = None
    
    summary = FinancialReportService.get_annual_pnl(year)
    
    prev_year = summary['year'] - 1
    next_year = summary['year'] + 1
    can_go_next = next_year <= timezone.now().year
    
    context = {
        'page_title': 'Annual Profit & Loss',
        'prev_year': prev_year,
        'next_year': next_year if can_go_next else None,
        **summary,
    }
    return render(request, 'reports/financial/annual_pnl.html', context)


@login_required
@report_access_required
def product_performance(request):
    """Product Performance Report - Fully implemented."""
    from datetime import datetime
    from calendar import monthrange
    
    # Get year/month from query params or default to current
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    
    # Calculate date range
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    # Get report data
    data = FinancialReportService.get_product_performance(start_date, end_date)
    
    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Product Performance',
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **data,
    }
    return render(request, 'reports/financial/product_performance.html', context)


@login_required
@report_access_required
def expense_summary(request):
    """Expense Summary Report - Fully implemented."""
    from datetime import datetime
    from calendar import monthrange
    
    # Get year/month from query params or default to current
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            year = today.year
            month = today.month
    else:
        year = today.year
        month = today.month
    
    # Calculate date range
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    # Get report data
    data = FinancialReportService.get_expense_summary(start_date, end_date)
    
    # Navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    can_go_next = (next_year < today.year) or (next_year == today.year and next_month <= today.month)
    
    context = {
        'page_title': 'Expense Summary',
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year if can_go_next else None,
        'next_month': next_month if can_go_next else None,
        **data,
    }
    return render(request, 'reports/financial/expense_summary.html', context)


# ═══════════════════════════════════════════════════════════════
# EXPORT/EMAIL
# ═══════════════════════════════════════════════════════════════

@login_required
@report_access_required
def export_csv(request):
    """Export report data as CSV."""
    import csv
    from datetime import datetime, date, timedelta
    from calendar import monthrange
    from django.http import HttpResponse
    
    report_type = request.GET.get('type', '')
    
    # Create the HttpResponse with CSV content type
    response = HttpResponse(content_type='text/csv')
    
    # Generate filename based on report type and date
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{timestamp}.csv"'
    
    writer = csv.writer(response)
    
    # Route to appropriate export based on type
    if report_type == 'sales_daily':
        date_str = request.GET.get('date')
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                report_date = timezone.now().date()
        else:
            report_date = timezone.now().date()
        
        summary = SalesReportService.get_daily_summary(report_date)
        totals = summary['totals']
        crates = summary['crates']
        
        # Write header info
        writer.writerow(['Daily Sales Report'])
        writer.writerow(['Date:', report_date.strftime('%Y-%m-%d')])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Revenue', totals['total_revenue']])
        writer.writerow(['Total Units Sold', totals['total_units_sold']])
        writer.writerow(['Total Commissions', totals['total_commission']])
        writer.writerow(['Dispatch Count', totals['dispatch_count']])
        writer.writerow([])
        
        # Crate tracking
        writer.writerow(['Crate Accountability'])
        writer.writerow(['Crates Dispatched', crates.get('crates_dispatched', 0)])
        writer.writerow(['Crates Returned', crates.get('crates_returned', 0)])
        writer.writerow(['Crates Lost', crates.get('crates_lost', 0)])
        writer.writerow(['Crates Damaged', crates.get('crates_damaged', 0)])
        writer.writerow([])
        
        # Product breakdown
        writer.writerow(['Product Breakdown'])
        writer.writerow(['Product', 'Qty Dispatched', 'Qty Sold', 'Qty Returned', 'Revenue'])
        for item in summary.get('products', []):
            writer.writerow([
                item['product__name'],
                item['units_dispatched'],
                item['units_sold'],
                item['units_returned'],
                item['revenue']
            ])
    
    elif report_type == 'sales_weekly':
        date_str = request.GET.get('week_start')
        if date_str:
            try:
                week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                week_start = None
        else:
            week_start = None
        
        summary = SalesReportService.get_weekly_summary(week_start)
        totals = summary['totals']
        crates = summary.get('crates', {})
        
        writer.writerow(['Weekly Sales Report'])
        writer.writerow(['Period:', f"{summary['start_date']} to {summary['end_date']}"])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Revenue', totals['total_revenue']])
        writer.writerow(['Total Units Sold', totals['total_units_sold']])
        writer.writerow(['Total Commissions', totals['total_commission']])
        writer.writerow(['Dispatch Count', totals['dispatch_count']])
        writer.writerow([])
        
        # Daily breakdown
        writer.writerow(['Daily Breakdown'])
        writer.writerow(['Date', 'Revenue', 'Units Sold'])
        for day in summary.get('daily_data', []):
            writer.writerow([
                day['return_date'],
                day['revenue'],
                day['units_sold'],
            ])
        writer.writerow([])
        
        # Product breakdown
        writer.writerow(['Product Breakdown'])
        writer.writerow(['Product', 'Qty Dispatched', 'Qty Sold', 'Qty Returned', 'Revenue'])
        for item in summary.get('products', []):
            writer.writerow([
                item['product__name'],
                item['units_dispatched'],
                item['units_sold'],
                item['units_returned'],
                item['revenue']
            ])
    
    elif report_type == 'sales_monthly':
        year = request.GET.get('year')
        month = request.GET.get('month')
        if year and month:
            try:
                year, month = int(year), int(month)
            except ValueError:
                year, month = None, None
        else:
            year, month = None, None
        
        summary = SalesReportService.get_monthly_summary(year, month)
        totals = summary['totals']
        
        writer.writerow(['Monthly Sales Report'])
        writer.writerow(['Period:', summary['start_date'].strftime('%B %Y')])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Revenue', totals['total_revenue']])
        writer.writerow(['Total Units Sold', totals['total_units_sold']])
        writer.writerow(['Total Commissions', totals['total_commission']])
        writer.writerow(['Dispatch Count', totals['dispatch_count']])
        writer.writerow([])
        
        # Product breakdown
        writer.writerow(['Product Breakdown'])
        writer.writerow(['Product', 'Qty Dispatched', 'Qty Sold', 'Qty Returned', 'Revenue'])
        for item in summary.get('products', []):
            writer.writerow([
                item['product__name'],
                item['units_dispatched'],
                item['units_sold'],
                item['units_returned'],
                item['revenue']
            ])
    
    elif report_type == 'sales_annual':
        year = request.GET.get('year')
        if year:
            try:
                year = int(year)
            except ValueError:
                year = None
        else:
            year = None
        
        summary = SalesReportService.get_annual_summary(year)
        totals = summary['totals']
        
        writer.writerow(['Annual Sales Report'])
        writer.writerow(['Year:', summary['year']])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Total Revenue', totals['total_revenue']])
        writer.writerow(['Total Units Sold', totals['total_units_sold']])
        writer.writerow(['Total Commissions', totals['total_commission']])
        writer.writerow(['Dispatch Count', totals['dispatch_count']])
        writer.writerow([])
        
        # Monthly breakdown
        writer.writerow(['Monthly Breakdown'])
        writer.writerow(['Month', 'Revenue', 'Units Sold', 'Commission'])
        for m in summary.get('monthly_data', []):
            writer.writerow([
                m['month'],
                m['revenue'],
                m['units_sold'],
                m['commission'],
            ])
    
    elif report_type.startswith('pnl_'):
        # P&L exports
        period = report_type.replace('pnl_', '')
        
        if period == 'daily':
            date_str = request.GET.get('date')
            if date_str:
                try:
                    report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    report_date = timezone.now().date()
            else:
                report_date = timezone.now().date()
            summary = FinancialReportService.get_daily_pnl(report_date)
            writer.writerow(['Daily Profit & Loss'])
            writer.writerow(['Date:', report_date.strftime('%Y-%m-%d')])
        
        elif period == 'weekly':
            date_str = request.GET.get('week_start')
            if date_str:
                try:
                    week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    week_start = None
            else:
                week_start = None
            
            if week_start is None:
                today = timezone.now().date()
                week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            summary = FinancialReportService.get_period_pnl(week_start, week_end)
            writer.writerow(['Weekly Profit & Loss'])
            writer.writerow(['Period:', f"{week_start} to {week_end}"])
        
        elif period == 'monthly':
            year = request.GET.get('year')
            month = request.GET.get('month')
            if year and month:
                try:
                    year, month = int(year), int(month)
                except ValueError:
                    year, month = None, None
            else:
                year, month = None, None
            
            if year is None or month is None:
                today = timezone.now().date()
                year, month = today.year, today.month
            
            from calendar import monthrange
            start_date = date(year, month, 1)
            end_date = date(year, month, monthrange(year, month)[1])
            
            summary = FinancialReportService.get_period_pnl(start_date, end_date)
            writer.writerow(['Monthly Profit & Loss'])
            writer.writerow(['Period:', start_date.strftime('%B %Y')])
        
        elif period == 'annual':
            year = request.GET.get('year')
            if year:
                try:
                    year = int(year)
                except ValueError:
                    year = None
            else:
                year = None
            
            if year is None:
                year = timezone.now().year
            
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            summary = FinancialReportService.get_period_pnl(start_date, end_date)
            writer.writerow(['Annual Profit & Loss'])
            writer.writerow(['Year:', year])
        
        else:
            writer.writerow(['Report type not fully implemented'])
            return response
        
        writer.writerow([])
        writer.writerow(['PROFIT & LOSS STATEMENT'])
        writer.writerow([])
        writer.writerow(['REVENUE'])
        writer.writerow(['Sales Revenue', summary.get('revenue', 0)])
        writer.writerow([])
        writer.writerow(['COST OF GOODS SOLD'])
        writer.writerow(['Production Costs', summary.get('cogs', 0)])
        writer.writerow([])
        writer.writerow(['GROSS PROFIT', summary.get('gross_profit', 0)])
        writer.writerow(['Gross Margin %', f"{summary.get('gross_margin', 0):.1f}%"])
        writer.writerow([])
        writer.writerow(['OPERATING EXPENSES'])
        writer.writerow(['Sales Commissions', summary.get('commissions', 0)])
        writer.writerow([])
        writer.writerow(['NET PROFIT/(LOSS)', summary.get('net_profit', 0)])
    
    else:
        # Default/unsupported
        writer.writerow(['Export not available for this report type'])
        writer.writerow(['Report Type:', report_type])
    
    return response


@login_required
@report_access_required
def email_report(request):
    """Send report via email - Fully implemented."""
    import json
    from django.http import JsonResponse
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    from io import StringIO
    import csv
    from datetime import datetime
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    
    report_type = data.get('report_type', '')
    recipient_email = data.get('email', '')
    include_csv = data.get('include_csv', True)
    
    if not recipient_email:
        return JsonResponse({'status': 'error', 'message': 'Email address required'}, status=400)
    
    if not report_type:
        return JsonResponse({'status': 'error', 'message': 'Report type required'}, status=400)
    
    # Generate report content based on type
    today = timezone.now().date()
    report_title = ''
    report_data = {}
    csv_content = None
    
    try:
        if report_type == 'sales_daily':
            date_str = data.get('date')
            if date_str:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                report_date = today
            report_data = SalesReportService.get_daily_summary(report_date)
            report_title = f'Daily Sales Report - {report_date.strftime("%B %d, %Y")}'
            
        elif report_type == 'sales_monthly':
            year = data.get('year', today.year)
            month = data.get('month', today.month)
            report_data = SalesReportService.get_monthly_summary(int(year), int(month))
            report_title = f'Monthly Sales Report - {report_data["start_date"].strftime("%B %Y")}'
            
        elif report_type == 'pnl_daily':
            date_str = data.get('date')
            if date_str:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                report_date = today
            report_data = FinancialReportService.get_daily_pnl(report_date)
            report_title = f'Daily P&L Report - {report_date.strftime("%B %d, %Y")}'
            
        elif report_type == 'pnl_monthly':
            year = data.get('year', today.year)
            month = data.get('month', today.month)
            report_data = FinancialReportService.get_monthly_pnl(int(year), int(month))
            report_title = f'Monthly P&L Report - {report_data["start_date"].strftime("%B %Y")}'
            
        elif report_type == 'commission':
            year = data.get('year', today.year)
            month = data.get('month', today.month)
            report_data = SalesReportService.get_commission_report(int(year), int(month))
            report_title = f'Commission Report - {report_data["start_date"].strftime("%B %Y")}'
            
        else:
            return JsonResponse({'status': 'error', 'message': f'Report type "{report_type}" not supported for email'}, status=400)
        
        # Build email body
        email_body = f"""
Chesanto Bakery - {report_title}
{'=' * 50}

Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
Requested by: {request.user.get_full_name()}

"""
        
        # Add summary based on report type
        if 'totals' in report_data:
            email_body += "Summary:\n"
            for key, value in report_data['totals'].items():
                email_body += f"  {key.replace('_', ' ').title()}: {value}\n"
        elif 'summary' in report_data:
            email_body += "Summary:\n"
            for key, value in report_data['summary'].items():
                email_body += f"  {key.replace('_', ' ').title()}: {value}\n"
        
        # Generate CSV attachment if requested
        if include_csv:
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            
            writer.writerow([report_title])
            writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            if 'products' in report_data:
                writer.writerow(['Product', 'Qty Sold', 'Revenue'])
                for product in report_data['products']:
                    writer.writerow([
                        product.get('product__name', product.get('product_name', '')),
                        product.get('units_sold', product.get('qty_sold', 0)),
                        product.get('revenue', 0),
                    ])
            elif 'commissions' in report_data:
                writer.writerow(['Salesperson', 'Total Revenue', 'Commission Earned', 'Target Achievement'])
                for c in report_data['commissions']:
                    writer.writerow([
                        c['full_name'],
                        c['total_revenue'],
                        c['commission_earned'],
                        f"{c['target_achievement']:.1f}%",
                    ])
            
            csv_content = csv_buffer.getvalue()
        
        # Send email
        email = EmailMessage(
            subject=f'[Chesanto Bakery] {report_title}',
            body=email_body,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            to=[recipient_email],
        )
        
        if csv_content:
            email.attach(
                f'report_{report_type}_{today.strftime("%Y%m%d")}.csv',
                csv_content,
                'text/csv'
            )
        
        email.send(fail_silently=False)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Report sent to {recipient_email}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to send email: {str(e)}'
        }, status=500)
