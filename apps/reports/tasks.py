"""
Reports App Tasks
=================
Django-Q2 async tasks for scheduled report generation and emailing.

Tasks:
- send_morning_report: 6 AM daily briefing
- send_evening_report: 10 PM daily wrap-up
- generate_and_email_reports: Core function for PDF generation and emailing

Uses the same PDF views as the frontend to ensure consistency.
"""

import io
import logging
from datetime import date, timedelta
from typing import List, Tuple, Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)


def get_report_dates() -> dict:
    """
    Calculate all relevant dates for report generation.
    Returns dict with yesterday, today, week_start, month_start, year info.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    
    # Week calculation (Monday = 0)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    
    # Month calculation
    month_start = today.replace(day=1)
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
    last_month_end = month_start - timedelta(days=1)
    
    return {
        'today': today,
        'yesterday': yesterday,
        'is_monday': today.weekday() == 0,
        'is_first_of_month': today.day == 1,
        'is_first_of_year': today.day == 1 and today.month == 1,
        'week_start': week_start,
        'last_week_start': last_week_start,
        'last_week_end': last_week_end,
        'month_start': month_start,
        'last_month_start': last_month_start,
        'last_month_end': last_month_end,
        'year': today.year,
        'month': today.month,
        'last_year': today.year - 1,
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
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_pnl_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily P&L report for yesterday."""
    from apps.reports.services import FinancialReportService
    
    report_date = dates['yesterday']
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
    """Generate weekly P&L report for last week."""
    from apps.reports.services import FinancialReportService
    
    week_start = dates['last_week_start']
    data = FinancialReportService.get_weekly_pnl(week_start)
    
    html = render_to_string('reports/pdf/pnl_weekly.html', {
        'start_date': data['start_date'],
        'end_date': data['end_date'],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_weekly_{data['start_date'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_pnl_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly P&L report for last month."""
    from apps.reports.services import FinancialReportService
    import calendar
    
    year = dates['last_month_start'].year
    month = dates['last_month_start'].month
    data = FinancialReportService.get_monthly_pnl(year, month)
    
    html = render_to_string('reports/pdf/pnl_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_pnl_annual(dates: dict) -> Tuple[bytes, str]:
    """Generate annual P&L report for last year."""
    from apps.reports.services import FinancialReportService
    
    year = dates['last_year']
    data = FinancialReportService.get_annual_pnl(year)
    
    html = render_to_string('reports/pdf/pnl_annual.html', {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"pnl_annual_{year}.pdf"
    return pdf_bytes, filename


def _generate_sales_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily sales summary for yesterday."""
    from apps.reports.services import SalesReportService
    
    report_date = dates['yesterday']
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
    """Generate weekly sales summary for last week."""
    from apps.reports.services import SalesReportService
    
    week_start = dates['last_week_start']
    week_end = dates['last_week_end']
    data = SalesReportService.get_weekly_summary(week_start)
    
    html = render_to_string('reports/pdf/sales_weekly.html', {
        'start_date': week_start,
        'end_date': week_end,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"sales_weekly_{week_start.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_sales_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly sales summary for last month."""
    from apps.reports.services import SalesReportService
    import calendar
    
    year = dates['last_month_start'].year
    month = dates['last_month_start'].month
    data = SalesReportService.get_monthly_summary(year, month)
    
    html = render_to_string('reports/pdf/sales_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"sales_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_salesperson_performance(dates: dict) -> Tuple[bytes, str]:
    """Generate salesperson performance for current/last month."""
    from apps.reports.services import SalesReportService
    import calendar
    from calendar import monthrange
    
    # Use last month if it's the first of the month, otherwise current month
    if dates['is_first_of_month']:
        year = dates['last_month_start'].year
        month = dates['last_month_start'].month
        start_date = dates['last_month_start']
        end_date = dates['last_month_end']
    else:
        year = dates['year']
        month = dates['month']
        start_date = dates['month_start']
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Calculate additional metrics for PDF
    for sp in data['salespeople']:
        sp['avg_per_dispatch'] = sp.get('avg_revenue_per_dispatch', 0)
        sp['percentage'] = sp.get('revenue_share', 0)
    
    html = render_to_string('reports/pdf/salesperson_performance.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
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
    
    # Format data to match inventory_daily template expectations
    data = {
        'total_items': len(low_stock_items),
        'total_value': sum(item.get('value', Decimal('0')) for item in low_stock_items),
        'low_stock_count': len(low_stock_items),
        'total_purchased': Decimal('0'),  # Not relevant for this report
        'stock_levels': low_stock_items,
        'purchases': [],
        'low_stock_items': low_stock_items,
    }
    
    html = render_to_string('reports/pdf/inventory_daily.html', {
        'report_date': dates['today'],
        'data': data,
        'is_low_stock_report': True,
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
    from calendar import monthrange
    import calendar
    
    # Get current month's salesperson data which includes crate info
    year = dates['year']
    month = dates['month']
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Use salesperson_performance template which has crate data
    html = render_to_string('reports/pdf/salesperson_performance.html', {
        'salespeople': data['salespeople'],
        'total_dispatches': data['summary']['total_dispatches'],
        'total_revenue': data['summary']['total_revenue'],
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"crate_accountability_{dates['today'].strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_production_daily(dates: dict) -> Tuple[bytes, str]:
    """Generate daily production summary for yesterday."""
    from apps.reports.services import ProductionReportService
    
    report_date = dates['yesterday']
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
    
    week_start = dates['last_week_start']
    week_end = dates['last_week_end']
    data = ProductionReportService.get_weekly_summary(week_start)
    
    html = render_to_string('reports/pdf/production_weekly.html', {
        'start_date': week_start,
        'end_date': week_end,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"production_weekly_{week_start.strftime('%Y%m%d')}.pdf"
    return pdf_bytes, filename


def _generate_production_monthly(dates: dict) -> Tuple[bytes, str]:
    """Generate monthly production summary."""
    from apps.reports.services import ProductionReportService
    import calendar
    
    year = dates['last_month_start'].year
    month = dates['last_month_start'].month
    data = ProductionReportService.get_monthly_summary(year, month)
    
    html = render_to_string('reports/pdf/production_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"production_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_efficiency_report(dates: dict) -> Tuple[bytes, str]:
    """Generate efficiency report for last 7 days."""
    from apps.production.models import ProductionBatch
    from django.db.models import Sum, Count
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    end_date = dates['yesterday']
    start_date = end_date - timedelta(days=6)
    
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
    
    year = dates['last_month_start'].year
    month = dates['last_month_start'].month
    data = FinancialReportService.get_payroll_monthly(year, month)
    
    html = render_to_string('reports/pdf/payroll_monthly.html', {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"payroll_monthly_{year}{month:02d}.pdf"
    return pdf_bytes, filename


def _generate_payroll_annual(dates: dict) -> Tuple[bytes, str]:
    """Generate annual payroll summary."""
    from apps.reports.services import FinancialReportService
    
    year = dates['last_year']
    data = FinancialReportService.get_payroll_annual(year)
    
    html = render_to_string('reports/pdf/payroll_annual.html', {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    })
    
    pdf_bytes = generate_pdf_from_html(html)
    filename = f"payroll_annual_{year}.pdf"
    return pdf_bytes, filename


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════════════════════

def send_scheduled_reports(schedule_type: str) -> dict:
    """
    Main task for sending scheduled reports.
    
    Args:
        schedule_type: 'MORNING' or 'EVENING'
    
    Returns:
        dict with status, reports_sent, recipients_count, errors
    """
    from apps.reports.models import ReportSchedule, ScheduleReport, ReportRecipient, ScheduledReportLog
    
    result = {
        'status': 'success',
        'schedule_type': schedule_type,
        'reports_generated': [],
        'reports_failed': [],
        'recipients_count': 0,
        'errors': [],
    }
    
    try:
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
        
        # Get date context
        dates = get_report_dates()
        
        # Get reports to include (check period type)
        schedule_reports = ScheduleReport.objects.filter(
            schedule=schedule,
            is_active=True,
            report_type__is_active=True
        ).select_related('report_type').order_by('sort_order')
        
        # Filter reports based on schedule type and period type
        # For dedicated periodic schedules (WEEKLY, MONTHLY, ANNUAL), include all assigned reports
        # For daily schedules (MORNING, EVENING), filter by current date
        reports_to_generate = []
        for sr in schedule_reports:
            rt = sr.report_type
            
            # For dedicated periodic schedules, include all assigned reports
            if schedule_type in ['WEEKLY', 'MONTHLY', 'ANNUAL']:
                reports_to_generate.append(rt.code)
            
            # For daily schedules (MORNING, EVENING), filter by period type
            else:
                # Always include DAILY and SNAPSHOT reports
                if rt.period_type in ['DAILY', 'SNAPSHOT']:
                    reports_to_generate.append(rt.code)
                
                # Include WEEKLY reports only on Mondays
                elif rt.period_type == 'WEEKLY' and dates['is_monday']:
                    reports_to_generate.append(rt.code)
                
                # Include MONTHLY reports only on 1st of month
                elif rt.period_type == 'MONTHLY' and dates['is_first_of_month']:
                    reports_to_generate.append(rt.code)
                
                # Include ANNUAL reports only on Jan 1st
                elif rt.period_type == 'ANNUAL' and dates['is_first_of_year']:
                    reports_to_generate.append(rt.code)
        
        if not reports_to_generate:
            log.status = ScheduledReportLog.Status.SENT
            log.reports_included = "No reports applicable for today"
            log.completed_at = timezone.now()
            log.save()
            result['status'] = 'skipped'
            result['errors'].append("No reports applicable for today's date")
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
        subject = schedule.subject_template.format(
            schedule_name=schedule.name,
            date=today.strftime('%B %d, %Y'),
            day_of_week=today.strftime('%A'),
        )
        
        # Generate email body
        email_html = render_to_string('reports/email/scheduled_report.html', {
            'schedule': schedule,
            'date': today,
            'reports_generated': result['reports_generated'],
            'reports_failed': result['reports_failed'],
            'is_monday': dates['is_monday'],
            'is_first_of_month': dates['is_first_of_month'],
            'is_first_of_year': dates['is_first_of_year'],
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
        
        logger.info(f"Sent {schedule_type} report to {len(recipients)} recipients with {len(attachments)} attachments")
        
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


def send_morning_report() -> dict:
    """
    Morning report task (6 AM).
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('MORNING')


def send_evening_report() -> dict:
    """
    Evening report task (10 PM).
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('EVENING')


def send_weekly_report() -> dict:
    """
    Weekly report task (Monday 7 AM).
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('WEEKLY')


def send_monthly_report() -> dict:
    """
    Monthly report task (1st of month, 7 AM).
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('MONTHLY')


def send_annual_report() -> dict:
    """
    Annual report task (Jan 1, 8 AM).
    Called by Django-Q scheduler.
    """
    return send_scheduled_reports('ANNUAL')


def test_report_email(recipient_email: str, schedule_type: str = 'MORNING') -> dict:
    """
    Test function to send a report to a single recipient.
    Useful for testing the email configuration.
    
    Usage in Django shell:
        from apps.reports.tasks import test_report_email
        test_report_email('test@example.com', 'MORNING')
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
    
    result = send_scheduled_reports(schedule_type)
    
    # Clean up test recipient if we created it
    if created:
        recipient.delete()
    
    return result
