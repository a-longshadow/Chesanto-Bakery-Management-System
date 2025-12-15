"""
Reports App Views
=================
All views require ACCOUNTANT role or higher.
Built incrementally - start with dashboard, then add report views.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from datetime import timedelta, date
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
    healthy_stock_items = [item for item in stock_levels if not item.get('is_low', False)]
    
    # Enhance stock levels with additional fields for template
    for item in stock_levels:
        item['quantity'] = item['current_stock']
        item['min_level'] = item['minimum_stock']
        item['unit_cost'] = item['last_price']
        item['total_value'] = item['value']
    
    context = {
        'page_title': 'Inventory Valuation',
        'today': timezone.now().date(),
        'stock_levels': stock_levels,
        'total_value': total_value,
        'total_items': len(stock_levels),
        'low_stock_count': len(low_stock_items),
        'healthy_stock_count': len(healthy_stock_items),
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
    
    # Get aggregated summary by item
    purchases = InventoryReportService.get_purchase_summary(start_date, end_date)
    
    # Get individual purchase records with dates
    individual_purchases = InventoryReportService.get_individual_purchases(start_date, end_date)
    
    # Calculate totals
    total_spent = sum(p.get('total_cost', 0) for p in purchases)
    total_orders = sum(p.get('purchase_count', 0) for p in purchases)
    
    context = {
        'page_title': 'Purchase History',
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        'purchases': purchases,
        'individual_purchases': individual_purchases,
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
    from decimal import Decimal
    
    # Get date range from query params (supports both start/end and year/month)
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    year_str = request.GET.get('year')
    month_str = request.GET.get('month')
    
    today = timezone.now().date()
    
    # Determine date range
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    elif year_str and month_str:
        try:
            year = int(year_str)
            month = int(month_str)
            start_date = date(year, month, 1)
            end_date = date(year, month, monthrange(year, month)[1])
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        # Default to current month
        start_date = today.replace(day=1)
        end_date = today
    
    # Get production batches for the period
    from apps.production.models import ProductionBatch
    batches = ProductionBatch.objects.filter(
        production_date__gte=start_date,
        production_date__lte=end_date
    )
    
    # Aggregate totals
    from django.db.models import Sum, Count
    totals = batches.aggregate(
        total_batches=Count('id'),
        total_units=Coalesce(Sum('quantity_produced'), 0),
        total_planned=Coalesce(Sum('expected_yield'), 0),
    )
    
    total_batches = totals['total_batches']
    total_units = totals['total_units']
    total_planned = totals['total_planned']
    
    # Calculate overall efficiency and waste
    if total_planned > 0:
        avg_efficiency = (Decimal(total_units) / Decimal(total_planned)) * 100
        waste_rate = max(Decimal('0'), ((Decimal(total_planned) - Decimal(total_units)) / Decimal(total_planned)) * 100)
    else:
        avg_efficiency = Decimal('0')
        waste_rate = Decimal('0')
    
    # Product breakdown with efficiency metrics
    product_data = batches.values(
        'product__id',
        'product__name'
    ).annotate(
        batch_count=Count('id'),
        actual_qty=Coalesce(Sum('quantity_produced'), 0),
        planned_qty=Coalesce(Sum('expected_yield'), 0),
    ).order_by('-actual_qty')
    
    products = []
    for p in product_data:
        planned = p['planned_qty']
        actual = p['actual_qty']
        if planned > 0:
            efficiency = (Decimal(actual) / Decimal(planned)) * 100
            product_waste = max(Decimal('0'), ((Decimal(planned) - Decimal(actual)) / Decimal(planned)) * 100)
        else:
            efficiency = Decimal('0')
            product_waste = Decimal('0')
        
        products.append({
            'name': p['product__name'],
            'batch_count': p['batch_count'],
            'planned_qty': planned,
            'actual_qty': actual,
            'efficiency': efficiency,
            'waste_rate': product_waste,
        })
    
    context = {
        'page_title': 'Production Efficiency',
        'start_date': start_date,
        'end_date': end_date,
        'total_batches': total_batches,
        'total_units': total_units,
        'total_planned': total_planned,
        'avg_efficiency': avg_efficiency,
        'waste_rate': waste_rate,
        'products': products,
    }
    return render(request, 'reports/production/efficiency.html', context)


@login_required
@report_access_required
def stock_movement(request):
    """
    Product Stock Movement Report - tracks FINISHED GOODS movements.
    Shows production additions, dispatch deductions, returns, and adjustments.
    """
    from datetime import datetime
    from apps.production.models import ProductStock, ProductStockMovement
    from apps.products.models import Product
    
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
    
    # Get all movements in date range
    movements = ProductStockMovement.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('product', 'recorded_by').order_by('-created_at')
    
    # Calculate totals by movement type
    total_production = movements.filter(movement_type='PRODUCTION').aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']
    total_dispatched = abs(movements.filter(movement_type='DISPATCH').aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total'])
    total_returns = movements.filter(movement_type='RETURN').aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']
    total_adjustments = movements.filter(movement_type='ADJUSTMENT').aggregate(
        total=Coalesce(Sum('quantity'), 0)
    )['total']
    
    # Net change (production + returns - dispatches + adjustments)
    total_in = total_production + total_returns
    total_out = total_dispatched
    net_change = total_in - total_out + total_adjustments
    
    # Current stock levels for all products
    stocks = ProductStock.objects.select_related('product').filter(
        product__is_active=True
    ).order_by('product__name')
    
    total_current_stock = stocks.aggregate(total=Coalesce(Sum('current_stock'), 0))['total']
    
    context = {
        'page_title': 'Product Stock Movement',
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        # Movements list for table
        'movements': movements[:100],  # Limit to last 100 movements
        # Stock levels
        'stocks': stocks,
        'total_current_stock': total_current_stock,
        # Summary totals
        'total_production': total_production,
        'total_dispatched': total_dispatched,
        'total_returns': total_returns,
        'total_adjustments': total_adjustments,
        'total_in': total_in,
        'total_out': total_out,
        'net_change': net_change,
        'total_transactions': movements.count(),
    }
    return render(request, 'reports/production/stock_movement.html', context)


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
# EMAIL
# ═══════════════════════════════════════════════════════════════

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
