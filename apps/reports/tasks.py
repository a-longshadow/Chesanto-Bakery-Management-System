"""
Reports App Tasks
=================
Django-Q2 async tasks for scheduled report generation and emailing.

Schedule Types:
- DAILY: 9 PM every day - sends today's complete data
- WEEKLY: 9 PM Sunday - sends Mon-Sun complete week  
- MONTHLY: 9 PM last day of month - sends complete month
- ANNUAL: 9 PM Dec 31 - sends complete year

Manual triggers use "current period" mode (period start → today).

Uses the same PDF views as the frontend to ensure consistency.
"""

import io
import logging
from calendar import monthrange
from datetime import date, timedelta
from typing import List, Tuple, Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)


def is_last_day_of_month(check_date: date) -> bool:
    """Check if the given date is the last day of its month."""
    _, last_day = monthrange(check_date.year, check_date.month)
    return check_date.day == last_day


def get_report_dates(mode: str = 'scheduled') -> dict:
    """
    Calculate all relevant dates for report generation.
    
    Args:
        mode: 'scheduled' for automated runs (complete periods)
              'manual' for manual triggers (current period: start → today)
    
    Returns dict with date ranges for each period type.
    
    Scheduled mode (complete periods):
    - DAILY: today (day is complete at 9 PM)
    - WEEKLY: Mon-Sun of current week (runs Sunday night)
    - MONTHLY: 1st-last of current month (runs last day)
    - ANNUAL: Jan 1-Dec 31 of current year (runs Dec 31)
    
    Manual mode (current period to date):
    - DAILY: today
    - WEEKLY: Mon-today (week to date)
    - MONTHLY: 1st-today (month to date)
    - ANNUAL: Jan 1-today (year to date)
    """
    today = timezone.localdate()
    
    # Week calculation (Monday = start of week)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end_sunday = week_start + timedelta(days=6)
    
    # Month calculation
    month_start = today.replace(day=1)
    _, last_day_of_month = monthrange(today.year, today.month)
    month_end = today.replace(day=last_day_of_month)
    
    # Year calculation
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    
    if mode == 'manual':
        # Manual trigger: current period (start → today)
        return {
            'mode': 'manual',
            'today': today,
            # Daily
            'daily_date': today,
            # Weekly: week to date
            'week_start': week_start,
            'week_end': today,  # Up to today
            'week_label': f"Week to Date ({week_start.strftime('%b %d')} - {today.strftime('%b %d')})",
            # Monthly: month to date
            'month_start': month_start,
            'month_end': today,  # Up to today
            'month': today.month,
            'month_label': f"{today.strftime('%B')} to Date (1st - {today.day})",
            # Annual: year to date  
            'year_start': year_start,
            'year_end': today,  # Up to today
            'year': today.year,
            'year_label': f"{today.year} Year to Date",
            # Flags
            'is_sunday': today.weekday() == 6,
            'is_last_day_of_month': is_last_day_of_month(today),
            'is_dec_31': today.month == 12 and today.day == 31,
        }
    else:
        # Scheduled: complete periods (runs at end of period)
        return {
            'mode': 'scheduled',
            'today': today,
            # Daily: today (complete at 9 PM)
            'daily_date': today,
            # Weekly: full week Mon-Sun (runs Sunday night)
            'week_start': week_start,
            'week_end': week_end_sunday,
            'week_label': f"Week of {week_start.strftime('%b %d')} - {week_end_sunday.strftime('%b %d, %Y')}",
            # Monthly: full month (runs last day)
            'month_start': month_start,
            'month_end': month_end,
            'month': today.month,
            'month_label': today.strftime('%B %Y'),
            # Annual: full year (runs Dec 31)
            'year_start': year_start,
            'year_end': year_end,
            'year': today.year,
            'year_label': str(today.year),
            # Flags for schedule eligibility
            'is_sunday': today.weekday() == 6,
            'is_last_day_of_month': is_last_day_of_month(today),
            'is_dec_31': today.month == 12 and today.day == 31,
        }


def generate_pdf_from_html(html_content: str, base_url: str = None) -> bytes:
    """
    Generate PDF bytes from HTML content using WeasyPrint.
    """
    from django.templatetags.static import static
    
    # Base CSS for PDF reports
    css = CSS(string='''
        @page {
            size: A4;
            margin: 1.5cm;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 6px 8px;
            text-align: left;
        }
        th {
            background-color: #f5f5f5;
            font-weight: 600;
        }
        .text-end { text-align: right; }
        .text-center { text-align: center; }
        .fw-bold { font-weight: bold; }
        .text-success { color: #28a745; }
        .text-danger { color: #dc3545; }
    ''')
    
    html = HTML(string=html_content, base_url=base_url or settings.SERVER_URL)
    pdf_bytes = html.write_pdf(stylesheets=[css])
    return pdf_bytes


def generate_report_pdf(report_code: str, dates: dict) -> Tuple[Optional[bytes], str]:
    """
    Generate a PDF for a specific report type.
    
    Returns tuple of (pdf_bytes, filename) or (None, error_message) on failure.
    """
    from apps.reports.services import (
        FinancialReportService,
        SalesReportService,
        InventoryReportService,
        ProductionReportService,
    )
    
    try:
        # Map report codes to their generation logic
        report_generators = {
            # Financial Reports
            'pnl_daily': lambda: _generate_pnl_daily(dates),
            'pnl_weekly': lambda: _generate_pnl_weekly(dates),
            'pnl_monthly': lambda: _generate_pnl_monthly(dates),
            'pnl_annual': lambda: _generate_pnl_annual(dates),
            
            # Sales Reports
            'sales_daily': lambda: _generate_sales_daily(dates),
            'sales_weekly': lambda: _generate_sales_weekly(dates),
            'sales_monthly': lambda: _generate_sales_monthly(dates),
            'salesperson_performance': lambda: _generate_salesperson_performance(dates),
            'commission_report': lambda: _generate_commission_report(dates),
            
            # Inventory Reports
            'stock_levels': lambda: _generate_stock_levels(dates),
            'low_stock_alerts': lambda: _generate_low_stock_alerts(dates),
            'stock_movement': lambda: _generate_stock_movement(dates),
            'inventory_valuation': lambda: _generate_inventory_valuation(dates),
            'crate_accountability': lambda: _generate_crate_accountability(dates),
            
            # Production Reports
            'production_daily': lambda: _generate_production_daily(dates),
            'production_weekly': lambda: _generate_production_weekly(dates),
            'production_monthly': lambda: _generate_production_monthly(dates),
            'efficiency_report': lambda: _generate_efficiency_report(dates),
            
            # Payroll Reports
            'payroll_monthly': lambda: _generate_payroll_monthly(dates),
            'payroll_annual': lambda: _generate_payroll_annual(dates),
        }
        
        if report_code not in report_generators:
            return None, f"Unknown report code: {report_code}"
        
        pdf_bytes, filename = report_generators[report_code]()
        return pdf_bytes, filename
        
    except Exception as e:
        logger.exception(f"Error generating report {report_code}: {e}")
        return None, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATION FUNCTIONS
# Each function generates HTML and converts to PDF
# Uses dates from get_report_dates() - works for both scheduled and manual modes
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_pnl_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily P&L report for today."""
    from apps.reports.services import FinancialReportService
    
    report_date = dates['daily_date']  # Today (complete at 9 PM)
    data = FinancialReportService.get_daily_pnl(report_date)
    
    html = render_to_string('reports/pdf/pnl_daily.html', {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_pnl_weekly(dates: dict) -> Tuple[bytes, str]:
    """Generate weekly P&L report for the week period in dates."""
    from apps.reports.services import FinancialReportService
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    
    # Use period P&L for flexible date ranges
    data = FinancialReportService.get_period_pnl(start_date, end_date)
    data['start_date'] = start_date
    data['end_date'] = end_date
    
    # Add daily breakdown for the period
    data['daily_breakdown'] = []
    current = start_date
    while current <= end_date:
        day_data = FinancialReportService.get_daily_pnl(current)
        data['daily_breakdown'].append({
            'date': current,
            'revenue': day_data['revenue'],
            'expenses': day_data['total_expenses'],
            'profit': day_data['net_profit'],
            'margin': day_data['profit_margin'],
        })
        current += timedelta(days=1)
    
    # Determine label based on mode
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    html = render_to_string('reports/pdf/pnl_weekly.html', {
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_weekly_{start_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_pnl_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly P&L report for the month period in dates."""
    from apps.reports.services import FinancialReportService
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    year = start_date.year
    month = start_date.month
    
    # Use period P&L for flexible date ranges (handles month-to-date)
    data = FinancialReportService.get_period_pnl(start_date, end_date)
    data['start_date'] = start_date
    data['end_date'] = end_date
    
    # Determine label based on mode
    period_label = dates.get('month_label', calendar.month_name[month] + ' ' + str(year))
    
    html = render_to_string('reports/pdf/pnl_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_pnl_annual(dates: dict) -> Tuple[bytes, str]:
    """Generate annual P&L report for the year period in dates."""
    from apps.reports.services import FinancialReportService
    
    start_date = dates['year_start']
    end_date = dates['year_end']
    year = dates['year']
    
    # Use period P&L for flexible date ranges (handles year-to-date)
    data = FinancialReportService.get_period_pnl(start_date, end_date)
    data['start_date'] = start_date
    data['end_date'] = end_date
    
    # Determine label based on mode
    period_label = dates.get('year_label', str(year))
    
    html = render_to_string('reports/pdf/pnl_annual.html', {
        'year': year,
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_annual_{year}.pdf"
    return pdf_bytes, filename


def _generate_sales_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily sales summary for today."""
    from apps.reports.services import SalesReportService
    
    report_date = dates['daily_date']  # Today
    data = SalesReportService.get_daily_summary(report_date)
    
    html = render_to_string('reports/pdf/sales_daily.html', {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"sales_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_sales_weekly(dates: dict) -> Tuple[bytes, str]:
    """Generate weekly sales summary for the week period in dates."""
    from apps.reports.services import SalesReportService
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    
    # Get period summary (handles both full week and week-to-date)
    data = SalesReportService.get_period_summary(start_date, end_date)
    
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    html = render_to_string('reports/pdf/sales_weekly.html', {
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"sales_weekly_{start_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_sales_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly sales summary for the month period in dates."""
    from apps.reports.services import SalesReportService
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    year = start_date.year
    month = start_date.month
    
    # Get period summary (handles both full month and month-to-date)
    data = SalesReportService.get_period_summary(start_date, end_date)
    
    period_label = dates.get('month_label', calendar.month_name[month] + ' ' + str(year))
    
    html = render_to_string('reports/pdf/sales_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"sales_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_salesperson_performance(dates: dict) -> Tuple[bytes, str]:
    """Generate salesperson performance for the month period in dates."""
    from apps.reports.services import SalesReportService
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    year = start_date.year
    month = start_date.month
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Calculate additional metrics for PDF
    for sp in data['salespeople']:
        sp['avg_per_dispatch'] = sp.get('avg_revenue_per_dispatch', 0)
        sp['percentage'] = sp.get('revenue_share', 0)
    
    period_label = dates.get('month_label', calendar.month_name[month] + ' ' + str(year))
    
    html = render_to_string('reports/pdf/salesperson_performance.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'period_label': period_label,
        'salespeople': data['salespeople'],
        'total_dispatches': data['summary']['total_dispatches'],
        'total_revenue': data['summary']['total_revenue'],
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"salesperson_performance_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_commission_report(dates: dict) -> Tuple[bytes, str]:
    """Generate commission report for last month."""
    from apps.reports.services import SalesReportService
    import calendar
    
    year = dates['last_month_start'].year
    month = dates['last_month_start'].month
    data = SalesReportService.get_commission_report(year, month)
    
    html = render_to_string('reports/pdf/commission_report.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'commissions': data.get('commissions', []),
        'summary': data.get('summary', {}),
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"commission_report_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_stock_levels(dates: dict) -> Tuple[bytes, str]:
    """Generate current stock levels report."""
    from apps.reports.services import InventoryReportService
    
    data = InventoryReportService.get_daily_summary(dates['today'])
    
    html = render_to_string('reports/pdf/inventory_daily.html', {
        'report_date': dates['today'],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"stock_levels_{dates['today'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_low_stock_alerts(dates: dict) -> Tuple[bytes, str]:
    """Generate low stock alerts report."""
    from apps.reports.services import InventoryReportService
    from decimal import Decimal
    
    # Get all stock and filter to low stock items
    all_stock = InventoryReportService.get_current_stock_levels()
    low_stock_items = [item for item in all_stock if item.get('is_low', False)]
    
    data = {
        'total_items': len(all_stock),
        'total_value': sum(item.get('value', Decimal('0')) for item in all_stock),
        'low_stock_count': len(low_stock_items),
        'low_stock_items': low_stock_items,
    }
    
    html = render_to_string('reports/pdf/low_stock_alerts.html', {
        'report_date': dates['today'],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"low_stock_alerts_{dates['today'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_stock_movement(dates: dict) -> Tuple[bytes, str]:
    """Generate stock movement report for last 7 days."""
    from apps.production.models import ProductStock, ProductStockMovement
    from django.db.models import Sum
    from django.db.models.functions import Coalesce
    
    end_date = dates['yesterday']
    start_date = end_date - timedelta(days=6)  # Last 7 days
    
    # Get all movements in date range (same logic as pdf_views.stock_movement_pdf)
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
    
    total_in = total_production + total_returns
    total_out = total_dispatched
    net_change = total_in - total_out + total_adjustments
    
    # Current stock levels
    stocks = ProductStock.objects.select_related('product').filter(
        product__is_active=True
    ).order_by('product__name')
    
    total_current_stock = stocks.aggregate(total=Coalesce(Sum('current_stock'), 0))['total']
    
    # Calculate Opening Stock (stock at start of period)
    opening_stock = total_current_stock - net_change
    
    html = render_to_string('reports/pdf/stock_movement.html', {
        'start_date': start_date,
        'end_date': end_date,
        'movements': movements[:100],
        'stocks': stocks,
        'total_current_stock': total_current_stock,
        'opening_stock': opening_stock,
        'total_production': total_production,
        'total_dispatched': total_dispatched,
        'total_returns': total_returns,
        'total_adjustments': total_adjustments,
        'total_in': total_in,
        'total_out': total_out,
        'net_change': net_change,
        'total_transactions': movements.count(),
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"stock_movement_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_inventory_valuation(dates: dict) -> Tuple[bytes, str]:
    """Generate inventory valuation report."""
    from apps.reports.services import InventoryReportService
    
    # Use get_valuation_report() which returns properly structured data
    data = InventoryReportService.get_valuation_report()
    
    html = render_to_string('reports/pdf/inventory_valuation.html', {
        'report_date': dates['today'],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"inventory_valuation_{dates['today'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_crate_accountability(dates: dict) -> Tuple[bytes, str]:
    """Generate crate accountability report."""
    from apps.reports.services import SalesReportService
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Calculate crate totals
    salespeople = data['salespeople']
    total_dispatched = sum(sp.get('crates_dispatched', 0) or 0 for sp in salespeople)
    total_returned = sum(sp.get('crates_returned', 0) or 0 for sp in salespeople)
    total_lost = sum(sp.get('crates_lost', 0) or 0 for sp in salespeople)
    total_damaged = sum(sp.get('crates_damaged', 0) or 0 for sp in salespeople)
    total_outstanding = total_dispatched - total_returned - total_lost - total_damaged
    
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    html = render_to_string('reports/pdf/crate_accountability.html', {
        'salespeople': salespeople,
        'total_dispatched': total_dispatched,
        'total_returned': total_returned,
        'total_lost': total_lost,
        'total_damaged': total_damaged,
        'total_lost_damaged': total_lost + total_damaged,
        'total_outstanding': total_outstanding,
        'period_label': period_label,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"crate_accountability_{dates['today'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_production_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily production summary for today."""
    from apps.reports.services import ProductionReportService
    
    report_date = dates['daily_date']  # Today
    data = ProductionReportService.get_daily_summary(report_date)
    
    html = render_to_string('reports/pdf/production_daily.html', {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"production_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_production_weekly(dates: dict) -> Tuple[bytes, str]:
    """Generate weekly production summary."""
    from apps.reports.services import ProductionReportService
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    
    # Get period summary (handles both full week and week-to-date)
    data = ProductionReportService.get_period_summary(start_date, end_date)
    
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    html = render_to_string('reports/pdf/production_weekly.html', {
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"production_weekly_{start_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_production_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly production summary."""
    from apps.reports.services import ProductionReportService
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    year = start_date.year
    month = start_date.month
    
    # Get period summary (handles both full month and month-to-date)
    data = ProductionReportService.get_period_summary(start_date, end_date)
    
    period_label = dates.get('month_label', calendar.month_name[month] + ' ' + str(year))
    
    html = render_to_string('reports/pdf/production_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"production_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_efficiency_report(dates: dict) -> Tuple[bytes, str]:
    """Generate efficiency report for the week period."""
    from apps.production.models import ProductionBatch
    from django.db.models import Sum, Count
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    
    # Get production batches for the period
    batches = ProductionBatch.objects.filter(
        production_date__gte=start_date,
        production_date__lte=end_date
    )
    
    # Aggregate totals
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
        units_wasted = max(0, total_planned - total_units)
    else:
        avg_efficiency = Decimal('0')
        waste_rate = Decimal('0')
        units_wasted = 0
    
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
    
    html = render_to_string('reports/pdf/production_efficiency.html', {
        'start_date': start_date,
        'end_date': end_date,
        'data': {
            'total_batches': total_batches,
            'total_actual': total_units,
            'total_planned': total_planned,
            'avg_efficiency': avg_efficiency,
            'waste_rate': waste_rate,
            'units_wasted': units_wasted,
            'products': products,
        },
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"efficiency_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_payroll_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly payroll summary."""
    from apps.reports.services import FinancialReportService
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    year = start_date.year
    month = start_date.month
    
    data = FinancialReportService.get_payroll_monthly(year, month)
    
    period_label = dates.get('month_label', calendar.month_name[month] + ' ' + str(year))
    
    html = render_to_string('reports/pdf/payroll_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"payroll_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_payroll_annual(dates: dict) -> Tuple[bytes, str]:
    """Generate annual payroll summary."""
    from apps.reports.services import FinancialReportService
    
    year = dates['year']
    data = FinancialReportService.get_payroll_annual(year)
    
    period_label = dates.get('year_label', str(year))
    
    html = render_to_string('reports/pdf/payroll_annual.html', {
        'year': year,
        'period_label': period_label,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"payroll_annual_{year}.pdf"
    return pdf_bytes, filename


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════════════════════

def send_scheduled_reports(schedule_type: str, mode: str = 'scheduled') -> dict:
    """
    Main task for sending scheduled reports.
    
    Args:
        schedule_type: 'DAILY', 'WEEKLY', 'MONTHLY', or 'ANNUAL'
        mode: 'scheduled' for automated runs (complete periods)
              'manual' for manual triggers (current period: start → today)
    
    Schedule Eligibility (for automated runs):
    - DAILY: Runs every day at 9 PM
    - WEEKLY: Runs only on Sunday (is_sunday check)
    - MONTHLY: Runs only on last day of month (is_last_day_of_month check)
    - ANNUAL: Runs only on Dec 31 (is_dec_31 check)
    
    Returns:
        dict with status, reports_sent, recipients_count, errors
    """
    from apps.reports.models import ReportSchedule, ScheduleReport, ReportRecipient, ScheduledReportLog
    
    result = {
        'status': 'success',
        'schedule_type': schedule_type,
        'mode': mode,
        'reports_generated': [],
        'reports_failed': [],
        'recipients_count': 0,
        'errors': [],
    }
    
    try:
        # Get date context based on mode
        dates = get_report_dates(mode)
        
        # For scheduled mode, check if today is the right day for this schedule
        if mode == 'scheduled':
            if schedule_type == 'WEEKLY' and not dates['is_sunday']:
                result['status'] = 'skipped'
                result['errors'].append("Weekly report only runs on Sunday")
                return result
            
            if schedule_type == 'MONTHLY' and not dates['is_last_day_of_month']:
                result['status'] = 'skipped'
                result['errors'].append("Monthly report only runs on last day of month")
                return result
            
            if schedule_type == 'ANNUAL' and not dates['is_dec_31']:
                result['status'] = 'skipped'
                result['errors'].append("Annual report only runs on December 31")
                return result
        
        # Get the schedule configuration
        schedule = ReportSchedule.objects.filter(
            schedule_type=schedule_type,
            is_active=True
        ).first()
        
        if not schedule:
            result['status'] = 'skipped'
            result['errors'].append(f"No active schedule found for {schedule_type}")
            return result
        
        # Create log entry
        log = ScheduledReportLog.objects.create(
            schedule=schedule,
            status=ScheduledReportLog.Status.GENERATING,
        )
        
        # Get recipients
        recipients = ReportRecipient.objects.filter(
            schedules=schedule,
            is_active=True
        ).values_list('email', flat=True)
        
        if not recipients:
            log.status = ScheduledReportLog.Status.FAILED
            log.error_message = "No active recipients for this schedule"
            log.completed_at = timezone.now()
            log.save()
            result['status'] = 'skipped'
            result['errors'].append("No active recipients")
            return result
        
        result['recipients_count'] = len(recipients)
        log.recipients_count = len(recipients)
        log.recipients_list = ', '.join(recipients)
        log.save()
        
        # Get reports to include based on schedule type
        schedule_reports = ScheduleReport.objects.filter(
            schedule=schedule,
            is_active=True,
            report_type__is_active=True
        ).select_related('report_type').order_by('sort_order')
        
        # Collect all report codes for this schedule
        reports_to_generate = [sr.report_type.code for sr in schedule_reports]
        
        if not reports_to_generate:
            log.status = ScheduledReportLog.Status.SENT
            log.reports_included = "No reports configured for this schedule"
            log.completed_at = timezone.now()
            log.save()
            result['status'] = 'skipped'
            result['errors'].append("No reports configured")
            return result
        
        log.reports_included = ', '.join(reports_to_generate)
        log.save()
        
        # Generate PDFs
        attachments = []
        for report_code in reports_to_generate:
            pdf_bytes, filename_or_error = generate_report_pdf(report_code, dates)
            if pdf_bytes:
                attachments.append((filename_or_error, pdf_bytes, 'application/pdf'))
                result['reports_generated'].append(report_code)
            else:
                result['reports_failed'].append(f"{report_code}: {filename_or_error}")
        
        if not attachments:
            log.status = ScheduledReportLog.Status.FAILED
            log.error_message = "All report generations failed"
            log.completed_at = timezone.now()
            log.save()
            result['status'] = 'failed'
            return result
        
        # Send email
        log.status = ScheduledReportLog.Status.SENDING
        log.save()
        
        today = dates['today']
        
        # Build period description for email subject
        period_desc = ""
        if schedule_type == 'DAILY':
            period_desc = today.strftime('%B %d, %Y')
        elif schedule_type == 'WEEKLY':
            period_desc = dates.get('week_label', f"Week of {dates['week_start'].strftime('%b %d')}")
        elif schedule_type == 'MONTHLY':
            period_desc = dates.get('month_label', today.strftime('%B %Y'))
        elif schedule_type == 'ANNUAL':
            period_desc = dates.get('year_label', str(today.year))
        
        subject = schedule.subject_template.format(
            schedule_name=schedule.name,
            date=period_desc,
            day_of_week=today.strftime('%A'),
        )
        
        # Generate email body
        email_html = render_to_string('reports/email/scheduled_report.html', {
            'schedule': schedule,
            'schedule_type': schedule_type,
            'mode': mode,
            'date': today,
            'period_label': period_desc,
            'dates': dates,
            'reports_generated': result['reports_generated'],
            'reports_failed': result['reports_failed'],
            'is_sunday': dates['is_sunday'],
            'is_last_day_of_month': dates['is_last_day_of_month'],
            'is_dec_31': dates['is_dec_31'],
        })
        
        email = EmailMessage(
            subject=subject,
            body=email_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=list(recipients),
        )
        email.content_subtype = 'html'
        
        for filename, content, mimetype in attachments:
            email.attach(filename, content, mimetype)
        
        email.send()
        
        # Update log
        log.status = ScheduledReportLog.Status.SENT
        log.completed_at = timezone.now()
        log.save()
        
        logger.info(f"Sent {schedule_type} report ({mode} mode) to {len(recipients)} recipients with {len(attachments)} attachments")
        
    except Exception as e:
        logger.exception(f"Error sending {schedule_type} reports: {e}")
        result['status'] = 'failed'
        result['errors'].append(str(e))
        
        # Update log if it exists
        try:
            if 'log' in locals():
                log.status = ScheduledReportLog.Status.FAILED
                log.error_message = str(e)
                log.completed_at = timezone.now()
                log.save()
        except:
            pass
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DJANGO-Q TASK ENTRY POINTS
# These are called by the scheduler at the configured times
# ═══════════════════════════════════════════════════════════════════════════════

def send_daily_report() -> dict:
    """
    Daily report task (9 PM every day).
    Sends today's complete data.
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('DAILY', mode='scheduled')


def send_weekly_report() -> dict:
    """
    Weekly report task (9 PM Sunday).
    Sends Mon-Sun complete week data.
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('WEEKLY', mode='scheduled')


def send_monthly_report() -> dict:
    """
    Monthly report task (9 PM last day of month).
    Sends complete month data.
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('MONTHLY', mode='scheduled')


def send_annual_report() -> dict:
    """
    Annual report task (9 PM Dec 31).
    Sends complete year data.
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('ANNUAL', mode='scheduled')


# ═══════════════════════════════════════════════════════════════════════════════
# MANUAL TRIGGER FUNCTIONS
# These use "current period" mode (period start → today)
# ═══════════════════════════════════════════════════════════════════════════════

def trigger_daily_report() -> dict:
    """Manually trigger daily report for today."""
    return send_scheduled_reports('DAILY', mode='manual')


def trigger_weekly_report() -> dict:
    """Manually trigger weekly report for week-to-date (Mon → today)."""
    return send_scheduled_reports('WEEKLY', mode='manual')


def trigger_monthly_report() -> dict:
    """Manually trigger monthly report for month-to-date (1st → today)."""
    return send_scheduled_reports('MONTHLY', mode='manual')


def trigger_annual_report() -> dict:
    """Manually trigger annual report for year-to-date (Jan 1 → today)."""
    return send_scheduled_reports('ANNUAL', mode='manual')


def test_report_email(recipient_email: str, schedule_type: str = 'DAILY', mode: str = 'manual') -> dict:
    """
    Test function to send a report to a single recipient.
    Useful for testing the email configuration.
    
    Usage in Django shell:
        from apps.reports.tasks import test_report_email
        test_report_email('test@example.com', 'DAILY')
        test_report_email('test@example.com', 'WEEKLY', mode='manual')  # Week to date
    """
    from apps.reports.models import ReportRecipient, ReportSchedule
    
    # Temporarily create/update recipient for testing
    schedule = ReportSchedule.objects.filter(schedule_type=schedule_type).first()
    if not schedule:
        return {'error': f'No {schedule_type} schedule found'}
    
    recipient, created = ReportRecipient.objects.get_or_create(
        email=recipient_email,
        defaults={'name': 'Test Recipient', 'is_active': True}
    )
    recipient.schedules.add(schedule)
    
    result = send_scheduled_reports(schedule_type, mode=mode)
    
    # Clean up test recipient if we created it
    if created:
        recipient.delete()
    
    return result
