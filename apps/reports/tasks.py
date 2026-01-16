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
Generates both PDF (for viewing) and Excel (for backup/analysis) attachments.
"""

import io
import logging
from calendar import monthrange
from datetime import date, timedelta
from io import BytesIO
from typing import List, Tuple, Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from weasyprint import HTML, CSS
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL STYLE CONSTANTS
# Mirrors: apps/reports/templates/reports/pdf/base_pdf.html
# ═══════════════════════════════════════════════════════════════════════════════

# Chesanto brand color (SaddleBrown) - used for headers in PDF
CHESANTO_BROWN = '8B4513'

EXCEL_STYLES = {
    # Report title - matches .pdf-header h1 (brown text) but inverted for Excel visibility
    'title_font': Font(bold=True, size=18, color='FFFFFF'),
    'title_fill': PatternFill(start_color=CHESANTO_BROWN, end_color=CHESANTO_BROWN, fill_type='solid'),
    
    # Section headers - matches h3.section-header (brown text, border-bottom)
    'section_font': Font(bold=True, size=12, color=CHESANTO_BROWN),
    
    # Table headers - matches th (brown background, white text, uppercase)
    # From base_pdf.html: th { background: #8B4513; color: white; }
    'header_font': Font(bold=True, size=9, color='FFFFFF'),
    'header_fill': PatternFill(start_color=CHESANTO_BROWN, end_color=CHESANTO_BROWN, fill_type='solid'),
    'header_alignment': Alignment(horizontal='center', vertical='center'),
    
    # Alternate row shading - matches tbody tr:nth-child(even) { background: #f9f9f9; }
    'alt_row_fill': PatternFill(start_color='F9F9F9', end_color='F9F9F9', fill_type='solid'),
    
    # Footer/total row - matches tfoot td { background: #f5f5f5; border-top: 2px solid #8B4513; }
    'footer_fill': PatternFill(start_color='F5F5F5', end_color='F5F5F5', fill_type='solid'),
    'footer_font': Font(bold=True),
    
    # Number formats
    'currency_format': '"KES "#,##0',      # Matches KES {{ value|intcomma }} in templates
    'currency_decimal': '"KES "#,##0.00',
    'integer_format': '#,##0',
    'percent_format': '0.0%',
    'date_format': 'YYYY-MM-DD',
    
    # Status colors - from base_pdf.html KPI cards and text classes
    'success_font': Font(color='28A745'),  # .text-success, .kpi-card.success
    'danger_font': Font(color='DC3545'),   # .text-danger, .kpi-card.danger
    'warning_font': Font(color='C58D00'),  # .text-warning (darker for visibility)
    'info_font': Font(color='17A2B8'),     # .text-info, .kpi-card.info
    'muted_font': Font(color='888888', italic=True),  # .text-muted, .pdf-generated
    
    # KPI card backgrounds (for summary cells)
    'success_fill': PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid'),
    'danger_fill': PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid'),
    'warning_fill': PatternFill(start_color='FFF3CD', end_color='FFF3CD', fill_type='solid'),
    'info_fill': PatternFill(start_color='D1ECF1', end_color='D1ECF1', fill_type='solid'),
    
    # Borders - matches th, td { border-bottom: 1px solid #ddd; }
    'border': Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    ),
    'border_bottom_only': Border(
        bottom=Side(style='thin', color='DDDDDD')
    ),
    # Footer border - matches tfoot { border-top: 2px solid #8B4513; }
    'footer_border': Border(
        top=Side(style='medium', color=CHESANTO_BROWN),
        bottom=Side(style='thin', color='DDDDDD')
    ),
}


def _apply_excel_header_style(cell):
    """
    Apply table header styling to a cell.
    Mirrors: th { background: #8B4513; color: white; font-weight: 600; }
    """
    cell.font = EXCEL_STYLES['header_font']
    cell.fill = EXCEL_STYLES['header_fill']
    cell.alignment = EXCEL_STYLES['header_alignment']
    cell.border = EXCEL_STYLES['border']


def _apply_excel_data_style(cell, is_currency=False, is_percent=False, row_num=0):
    """
    Apply standard data cell styling.
    Optionally applies alternate row shading for even rows.
    """
    cell.border = EXCEL_STYLES['border_bottom_only']
    cell.alignment = Alignment(horizontal='right' if is_currency or is_percent else 'left')
    
    if is_currency:
        cell.number_format = EXCEL_STYLES['currency_format']
    elif is_percent:
        cell.number_format = EXCEL_STYLES['percent_format']
    
    # Alternate row shading (even rows)
    if row_num % 2 == 0:
        cell.fill = EXCEL_STYLES['alt_row_fill']


def _apply_excel_footer_style(cell, is_currency=False):
    """
    Apply footer/total row styling.
    Mirrors: tfoot td { background: #f5f5f5; font-weight: bold; border-top: 2px solid #8B4513; }
    """
    cell.font = EXCEL_STYLES['footer_font']
    cell.fill = EXCEL_STYLES['footer_fill']
    cell.border = EXCEL_STYLES['footer_border']
    if is_currency:
        cell.number_format = EXCEL_STYLES['currency_format']


def _add_excel_branding_footer(ws, row):
    """
    Add Chesanto branding footer to worksheet (Excel alternative to PDF watermark).
    Mirrors the PDF running footer: "Confidential" | "CHESANTO BAKERY"
    """
    ws.cell(row=row, column=1, value="Confidential - CHESANTO BAKERY")
    ws.cell(row=row, column=1).font = EXCEL_STYLES['muted_font']


def _add_excel_title(ws, title: str, subtitle: str = None, max_col: int = 6):
    """
    Add title section to worksheet with Chesanto branding.
    Returns the next row number to use.
    """
    # Merge cells for title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    title_cell = ws.cell(row=1, column=1, value=title)
    title_cell.font = EXCEL_STYLES['title_font']
    title_cell.fill = EXCEL_STYLES['title_fill']
    title_cell.alignment = Alignment(horizontal='center')
    ws.row_dimensions[1].height = 28
    
    next_row = 2
    
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
        ws.cell(row=2, column=1, value=subtitle)
        ws.cell(row=2, column=1).font = Font(size=10, color='666666')
        ws.cell(row=2, column=1).alignment = Alignment(horizontal='center')
        next_row = 3
    
    # Generated timestamp
    ws.cell(row=next_row, column=1, value=f"Generated: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}")
    ws.cell(row=next_row, column=1).font = EXCEL_STYLES['muted_font']
    
    return next_row + 2  # Skip a row after timestamp


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
# EXCEL REPORT GENERATION FUNCTIONS
# Each function generates formatted Excel bytes matching PDF styling
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report_excel(report_code: str, dates: dict) -> Tuple[Optional[bytes], str]:
    """
    Generate Excel bytes for a specific report type.
    
    Returns tuple of (excel_bytes, filename) or (None, error_message) on failure.
    Mirrors generate_report_pdf() but outputs formatted Excel instead.
    """
    try:
        excel_generators = {
            # Daily reports
            'pnl_daily': lambda: _generate_pnl_daily_excel(dates),
            'sales_daily': lambda: _generate_sales_daily_excel(dates),
            'production_daily': lambda: _generate_production_daily_excel(dates),
            'stock_levels': lambda: _generate_stock_levels_excel(dates),
            'low_stock_alerts': lambda: _generate_low_stock_alerts_excel(dates),
            
            # Weekly reports
            'pnl_weekly': lambda: _generate_pnl_weekly_excel(dates),
            'sales_weekly': lambda: _generate_sales_weekly_excel(dates),
            'production_weekly': lambda: _generate_production_weekly_excel(dates),
            'efficiency_report': lambda: _generate_efficiency_excel(dates),
            'stock_movement': lambda: _generate_stock_movement_excel(dates),
            'salesperson_performance': lambda: _generate_salesperson_performance_excel(dates),
            'crate_accountability': lambda: _generate_crate_accountability_excel(dates),
            
            # Monthly reports
            'pnl_monthly': lambda: _generate_pnl_monthly_excel(dates),
            'sales_monthly': lambda: _generate_sales_monthly_excel(dates),
            'production_monthly': lambda: _generate_production_monthly_excel(dates),
            'inventory_valuation': lambda: _generate_inventory_valuation_excel(dates),
            'payroll_monthly': lambda: _generate_payroll_monthly_excel(dates),
            'commission_report': lambda: _generate_commission_excel(dates),
            
            # Annual reports
            'pnl_annual': lambda: _generate_pnl_annual_excel(dates),
            'payroll_annual': lambda: _generate_payroll_annual_excel(dates),
        }
        
        if report_code not in excel_generators:
            return None, f"No Excel generator for: {report_code}"
        
        return excel_generators[report_code]()
        
    except Exception as e:
        logger.exception(f"Error generating Excel for {report_code}: {e}")
        return None, str(e)


def _generate_sales_daily_excel(dates: dict) -> Tuple[bytes, str]:
    """
    Generate formatted Excel for daily sales report.
    Mirrors: apps/reports/templates/reports/pdf/sales_daily.html
    """
    from apps.reports.services import SalesReportService
    from decimal import Decimal
    
    report_date = dates['daily_date']
    data = SalesReportService.get_daily_summary(report_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Sales"
    
    # Title section
    row = _add_excel_title(
        ws, 
        f"Daily Sales Report - {report_date.strftime('%A, %B %d, %Y')}", 
        "Sales Summary",
        max_col=6
    )
    
    # KPI Summary Row
    kpi_labels = ['Total Revenue', 'Cash Collected', 'Deficit Amount', 'Returns Value']
    kpi_values = [
        float(data.get('total_revenue', 0)),
        float(data.get('cash_collected', data.get('total_revenue', 0))),  # cash_collected may not exist
        float(data.get('deficit_amount', 0)),
        float(data.get('returns_value', 0))
    ]
    kpi_fills = [
        EXCEL_STYLES['success_fill'],
        EXCEL_STYLES['info_fill'],
        EXCEL_STYLES['danger_fill'] if kpi_values[2] > 0 else EXCEL_STYLES['info_fill'],
        EXCEL_STYLES['warning_fill'] if kpi_values[3] > 0 else EXCEL_STYLES['info_fill']
    ]
    
    for col, (label, value, fill) in enumerate(zip(kpi_labels, kpi_values, kpi_fills), 1):
        ws.cell(row=row, column=col, value=label).font = Font(size=8, color='666666')
        value_cell = ws.cell(row=row+1, column=col, value=value)
        value_cell.font = Font(bold=True, size=12)
        value_cell.number_format = EXCEL_STYLES['currency_format']
        value_cell.fill = fill
    
    row += 3
    
    # Net Sales Box
    ws.cell(row=row, column=1, value="Total Revenue")
    ws.cell(row=row, column=2, value=float(data.get('total_revenue', 0))).number_format = EXCEL_STYLES['currency_format']
    row += 1
    ws.cell(row=row, column=1, value="Less: Returns")
    ws.cell(row=row, column=2, value=-float(data.get('returns_value', 0))).number_format = EXCEL_STYLES['currency_format']
    row += 1
    ws.cell(row=row, column=1, value="Net Sales").font = Font(bold=True)
    net_sales_cell = ws.cell(row=row, column=2, value=float(data.get('net_sales', data.get('total_revenue', 0) - data.get('returns_value', 0))))
    net_sales_cell.font = Font(bold=True)
    net_sales_cell.number_format = EXCEL_STYLES['currency_format']
    _apply_excel_footer_style(ws.cell(row=row, column=1))
    _apply_excel_footer_style(ws.cell(row=row, column=2), is_currency=True)
    
    row += 2
    
    # Sales by Product Table
    ws.cell(row=row, column=1, value="Sales by Product").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Product', 'Qty Dispatched', 'Qty Returned', 'Qty Sold', 'Revenue']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    # Data rows
    products = data.get('product_breakdown', [])
    for idx, product in enumerate(products):
        ws.cell(row=row, column=1, value=product.get('product_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=product.get('qty_dispatched', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=product.get('qty_returned', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=product.get('qty_sold', 0)).alignment = Alignment(horizontal='center')
        revenue_cell = ws.cell(row=row, column=5, value=float(product.get('revenue', 0)))
        revenue_cell.number_format = EXCEL_STYLES['currency_format']
        revenue_cell.alignment = Alignment(horizontal='right')
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Product totals row
    for col in range(1, 6):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="TOTAL")
    ws.cell(row=row, column=2, value=data.get('total_qty_dispatched', sum(p.get('qty_dispatched', 0) or 0 for p in products))).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=3, value=data.get('total_qty_returned', sum(p.get('qty_returned', 0) or 0 for p in products))).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=4, value=data.get('total_qty_sold', sum(p.get('qty_sold', 0) or 0 for p in products))).alignment = Alignment(horizontal='center')
    total_cell = ws.cell(row=row, column=5, value=float(data.get('total_revenue', 0)))
    total_cell.number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    
    # Sales by Salesperson Table
    ws.cell(row=row, column=1, value="Sales by Salesperson").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Salesperson', 'Dispatches', 'Revenue', 'Cash Collected', 'Deficit', 'Returns']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, sp in enumerate(data.get('salesperson_breakdown', [])):
        ws.cell(row=row, column=1, value=sp.get('salesperson_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=sp.get('dispatch_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=float(sp.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=4, value=float(sp.get('cash_collected', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(sp.get('deficit', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=6, value=float(sp.get('returns_value', 0))).number_format = EXCEL_STYLES['currency_format']
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    # Column widths
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 13
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 14
    ws.column_dimensions['F'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"sales_daily_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_sales_weekly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for weekly sales report."""
    from apps.reports.services import SalesReportService
    from decimal import Decimal
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    data = SalesReportService.get_period_summary(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly Sales"
    
    row = _add_excel_title(ws, f"Weekly Sales Report", period_label, max_col=6)
    
    # Daily breakdown table
    ws.cell(row=row, column=1, value="Daily Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Date', 'Dispatches', 'Units Sold', 'Revenue', 'Returns', 'Net Sales']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_revenue = Decimal('0')
    total_returns = Decimal('0')
    
    # Get daily breakdown
    daily_data = data.get('daily_breakdown', [])
    for idx, day in enumerate(daily_data):
        day_date = day.get('date')
        ws.cell(row=row, column=1, value=day_date.strftime('%a %b %d') if day_date else '')
        ws.cell(row=row, column=2, value=day.get('dispatch_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=day.get('units_sold', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=float(day.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(day.get('returns_value', 0))).number_format = EXCEL_STYLES['currency_format']
        net = float(day.get('revenue', 0)) - float(day.get('returns_value', 0))
        ws.cell(row=row, column=6, value=net).number_format = EXCEL_STYLES['currency_format']
        
        total_revenue += Decimal(str(day.get('revenue', 0)))
        total_returns += Decimal(str(day.get('returns_value', 0)))
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Totals row
    for col in range(1, 7):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="WEEK TOTAL")
    ws.cell(row=row, column=4, value=float(total_revenue)).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=5, value=float(total_returns)).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=6, value=float(total_revenue - total_returns)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    # Column widths
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws.column_dimensions[col].width = 14
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"sales_weekly_{start_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_sales_monthly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for monthly sales report."""
    from apps.reports.services import SalesReportService
    from decimal import Decimal
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    period_label = dates.get('month_label', start_date.strftime('%B %Y'))
    
    data = SalesReportService.get_period_summary(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Sales"
    
    row = _add_excel_title(ws, f"Monthly Sales Report", period_label, max_col=5)
    
    # Summary KPIs
    ws.cell(row=row, column=1, value="Total Revenue").font = Font(size=9, color='666666')
    ws.cell(row=row, column=2, value=float(data.get('total_revenue', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=2).fill = EXCEL_STYLES['success_fill']
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)
    row += 2
    
    # Product summary table
    ws.cell(row=row, column=1, value="Sales by Product").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Product', 'Units Sold', 'Revenue', '% of Total']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_revenue = Decimal(str(data.get('total_revenue', 1))) or Decimal('1')  # Avoid division by zero
    
    for idx, product in enumerate(data.get('product_breakdown', [])):
        ws.cell(row=row, column=1, value=product.get('product_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=product.get('qty_sold', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=float(product.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        pct = float(Decimal(str(product.get('revenue', 0))) / total_revenue) if total_revenue else 0
        ws.cell(row=row, column=4, value=pct).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 5):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws.column_dimensions[col].width = 16
    ws.column_dimensions['A'].width = 22
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"sales_monthly_{start_date.strftime('%Y%m')}.xlsx"
    return buffer.getvalue(), filename


def _generate_pnl_daily_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for daily P&L report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    report_date = dates['daily_date']
    data = FinancialReportService.get_daily_pnl(report_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily P&L"
    
    row = _add_excel_title(
        ws, 
        f"Daily Profit & Loss - {report_date.strftime('%A, %B %d, %Y')}", 
        "Financial Summary",
        max_col=4
    )
    
    # Revenue section
    ws.cell(row=row, column=1, value="REVENUE").font = EXCEL_STYLES['section_font']
    row += 1
    
    ws.cell(row=row, column=1, value="Sales Revenue")
    ws.cell(row=row, column=2, value=float(data.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=2).fill = EXCEL_STYLES['success_fill']
    row += 2
    
    # Expenses section
    ws.cell(row=row, column=1, value="EXPENSES").font = EXCEL_STYLES['section_font']
    row += 1
    
    # Use correct field names from FinancialReportService.get_daily_pnl()
    expenses = [
        ('Cost of Goods Sold (COGS)', data.get('cogs', 0)),
        ('Sales Commissions', data.get('commissions', 0)),
        ('Labor Costs', data.get('labor_cost', 0)),
        ('Waste/Loss', data.get('waste_loss', 0)),
        ('Other Expenses', data.get('other_expenses', 0)),
    ]
    
    for idx, (label, value) in enumerate(expenses):
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=float(value)).number_format = EXCEL_STYLES['currency_format']
        _apply_excel_data_style(ws.cell(row=row, column=1), row_num=idx)
        _apply_excel_data_style(ws.cell(row=row, column=2), is_currency=True, row_num=idx)
        row += 1
    
    # Total Expenses
    _apply_excel_footer_style(ws.cell(row=row, column=1, value="Total Expenses"))
    total_expenses_cell = ws.cell(row=row, column=2, value=float(data.get('total_expenses', 0)))
    _apply_excel_footer_style(total_expenses_cell, is_currency=True)
    row += 2
    
    # Net Profit
    ws.cell(row=row, column=1, value="NET PROFIT").font = Font(bold=True, size=14)
    profit_cell = ws.cell(row=row, column=2, value=float(data.get('net_profit', 0)))
    profit_cell.number_format = EXCEL_STYLES['currency_format']
    profit_cell.font = Font(bold=True, size=14)
    profit = data.get('net_profit', 0)
    if profit >= 0:
        profit_cell.fill = EXCEL_STYLES['success_fill']
    else:
        profit_cell.fill = EXCEL_STYLES['danger_fill']
    
    row += 1
    margin = data.get('profit_margin', 0)
    ws.cell(row=row, column=1, value="Profit Margin")
    margin_cell = ws.cell(row=row, column=2, value=float(margin) / 100 if margin else 0)
    margin_cell.number_format = EXCEL_STYLES['percent_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 18
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"pnl_daily_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_pnl_weekly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for weekly P&L report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    data = FinancialReportService.get_period_pnl(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly P&L"
    
    row = _add_excel_title(ws, "Weekly Profit & Loss", period_label, max_col=5)
    
    # Daily breakdown table
    ws.cell(row=row, column=1, value="Daily P&L Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Date', 'Revenue', 'Expenses', 'Net Profit', 'Margin']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    # Get daily data for the period
    current = start_date
    idx = 0
    total_revenue = Decimal('0')
    total_expenses = Decimal('0')
    
    while current <= end_date:
        day_data = FinancialReportService.get_daily_pnl(current)
        
        ws.cell(row=row, column=1, value=current.strftime('%a %b %d'))
        ws.cell(row=row, column=2, value=float(day_data.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=3, value=float(day_data.get('total_expenses', 0))).number_format = EXCEL_STYLES['currency_format']
        profit_cell = ws.cell(row=row, column=4, value=float(day_data.get('net_profit', 0)))
        profit_cell.number_format = EXCEL_STYLES['currency_format']
        if day_data.get('net_profit', 0) < 0:
            profit_cell.font = EXCEL_STYLES['danger_font']
        margin = day_data.get('profit_margin', 0)
        ws.cell(row=row, column=5, value=float(margin) / 100 if margin else 0).number_format = EXCEL_STYLES['percent_format']
        
        total_revenue += Decimal(str(day_data.get('revenue', 0)))
        total_expenses += Decimal(str(day_data.get('total_expenses', 0)))
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
        current += timedelta(days=1)
        idx += 1
    
    # Week totals
    for col in range(1, 6):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="WEEK TOTAL")
    ws.cell(row=row, column=2, value=float(total_revenue)).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=3, value=float(total_expenses)).number_format = EXCEL_STYLES['currency_format']
    net_profit = total_revenue - total_expenses
    ws.cell(row=row, column=4, value=float(net_profit)).number_format = EXCEL_STYLES['currency_format']
    margin = float(net_profit / total_revenue) if total_revenue else 0
    ws.cell(row=row, column=5, value=margin).number_format = EXCEL_STYLES['percent_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws.column_dimensions[col].width = 14
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"pnl_weekly_{start_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_pnl_monthly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for monthly P&L report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    period_label = dates.get('month_label', start_date.strftime('%B %Y'))
    
    data = FinancialReportService.get_period_pnl(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly P&L"
    
    row = _add_excel_title(ws, "Monthly Profit & Loss", period_label, max_col=4)
    
    # Summary section
    summary = [
        ('Total Revenue', data.get('revenue', 0), EXCEL_STYLES['success_fill']),
        ('Total Expenses', data.get('total_expenses', 0), EXCEL_STYLES['warning_fill']),
        ('Net Profit', data.get('net_profit', 0), 
         EXCEL_STYLES['success_fill'] if data.get('net_profit', 0) >= 0 else EXCEL_STYLES['danger_fill']),
    ]
    
    for label, value, fill in summary:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        value_cell = ws.cell(row=row, column=2, value=float(value))
        value_cell.number_format = EXCEL_STYLES['currency_format']
        value_cell.fill = fill
        value_cell.font = Font(bold=True, size=12)
        row += 1
    
    # Profit Margin
    margin = data.get('profit_margin', 0)
    ws.cell(row=row, column=1, value="Profit Margin").font = Font(bold=True)
    margin_cell = ws.cell(row=row, column=2, value=float(margin) / 100 if margin else 0)
    margin_cell.number_format = EXCEL_STYLES['percent_format']
    margin_cell.font = Font(bold=True, size=12)
    
    row += 2
    
    # Expense breakdown
    ws.cell(row=row, column=1, value="Expense Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Category', 'Amount', '% of Total']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_expenses = Decimal(str(data.get('total_expenses', 1))) or Decimal('1')
    # Use correct field names from FinancialReportService.get_period_pnl()
    expense_items = [
        ('Cost of Goods Sold (COGS)', data.get('cogs', 0)),
        ('Sales Commissions', data.get('commissions', 0)),
        ('Labor Costs', data.get('labor_cost', 0)),
        ('Waste/Loss', data.get('waste_loss', 0)),
        ('Other Expenses', data.get('other_expenses', 0)),
    ]
    
    for idx, (label, value) in enumerate(expense_items):
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=float(value)).number_format = EXCEL_STYLES['currency_format']
        pct = float(Decimal(str(value)) / total_expenses) if total_expenses else 0
        ws.cell(row=row, column=3, value=pct).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 4):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 16
    ws.column_dimensions['C'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"pnl_monthly_{start_date.strftime('%Y%m')}.xlsx"
    return buffer.getvalue(), filename


def _generate_stock_levels_excel(dates: dict) -> Tuple[bytes, str]:
    """
    Generate formatted Excel for current stock levels.
    Mirrors: apps/reports/templates/reports/pdf/low_stock_alerts.html
    """
    from apps.reports.services import InventoryReportService
    from decimal import Decimal
    
    report_date = dates['today']
    data = InventoryReportService.get_current_stock_levels()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Levels"
    
    row = _add_excel_title(
        ws, 
        f"Inventory Stock Levels - {report_date.strftime('%A, %B %d, %Y')}", 
        "Raw Materials & Indirect Costs",
        max_col=6
    )
    
    headers = ['Item', 'Category', 'Current Stock', 'Unit', 'Unit Price', 'Total Value']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_value = Decimal('0')
    for idx, item in enumerate(data):
        ws.cell(row=row, column=1, value=item.get('name', ''))
        ws.cell(row=row, column=2, value='Ingredient' if item.get('is_ingredient') else 'Indirect Cost')
        
        stock_cell = ws.cell(row=row, column=3, value=float(item.get('current_stock', 0)))
        stock_cell.number_format = EXCEL_STYLES['integer_format']
        stock_cell.alignment = Alignment(horizontal='right')
        
        # Highlight low stock in red
        if item.get('is_low', False):
            stock_cell.font = EXCEL_STYLES['danger_font']
        
        ws.cell(row=row, column=4, value=item.get('unit', ''))
        
        price_cell = ws.cell(row=row, column=5, value=float(item.get('unit_price', 0)))
        price_cell.number_format = EXCEL_STYLES['currency_format']
        price_cell.alignment = Alignment(horizontal='right')
        
        value = Decimal(str(item.get('value', 0)))
        value_cell = ws.cell(row=row, column=6, value=float(value))
        value_cell.number_format = EXCEL_STYLES['currency_format']
        value_cell.alignment = Alignment(horizontal='right')
        total_value += value
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Total row
    row += 1
    for col in range(1, 7):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=5, value="TOTAL:").alignment = Alignment(horizontal='right')
    ws.cell(row=row, column=6, value=float(total_value)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 14
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"stock_levels_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_inventory_valuation_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for inventory valuation report."""
    from apps.reports.services import InventoryReportService
    from decimal import Decimal
    
    report_date = dates.get('month_end', dates['today'])
    data = InventoryReportService.get_valuation_report()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory Valuation"
    
    row = _add_excel_title(
        ws, 
        f"Inventory Valuation Report", 
        report_date.strftime('%B %d, %Y'),
        max_col=6
    )
    
    # Summary KPIs
    ws.cell(row=row, column=1, value="Total Value").font = Font(bold=True)
    total_val_cell = ws.cell(row=row, column=2, value=float(data.get('total_value', 0)))
    total_val_cell.number_format = EXCEL_STYLES['currency_format']
    total_val_cell.fill = EXCEL_STYLES['success_fill']
    total_val_cell.font = Font(bold=True, size=12)
    
    ws.cell(row=row, column=3, value="Low Stock Items").font = Font(bold=True)
    low_cell = ws.cell(row=row, column=4, value=data.get('low_stock_count', 0))
    low_cell.font = Font(bold=True, size=12)
    if data.get('low_stock_count', 0) > 0:
        low_cell.fill = EXCEL_STYLES['danger_fill']
    else:
        low_cell.fill = EXCEL_STYLES['info_fill']
    row += 2
    
    # Category summary
    ws.cell(row=row, column=1, value="Category Summary").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Category', 'Items', 'Value', '% of Total']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, cat in enumerate(data.get('category_summary', [])):
        ws.cell(row=row, column=1, value=cat.get('name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=cat.get('item_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=float(cat.get('value', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=4, value=float(cat.get('percentage', 0)) / 100).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 5):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    
    # Detailed items table
    ws.cell(row=row, column=1, value="Item Details").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Item', 'Category', 'Quantity', 'Unit', 'Unit Cost', 'Total Value']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_value = Decimal('0')
    items = data.get('items', [])
    for idx, item in enumerate(items):
        ws.cell(row=row, column=1, value=item.get('name', ''))
        ws.cell(row=row, column=2, value=item.get('category', ''))
        
        qty_cell = ws.cell(row=row, column=3, value=float(item.get('quantity', 0)))
        qty_cell.number_format = '#,##0.0'
        qty_cell.alignment = Alignment(horizontal='right')
        # Highlight low stock
        if item.get('is_low_stock', False):
            qty_cell.font = EXCEL_STYLES['danger_font']
        
        ws.cell(row=row, column=4, value=item.get('unit', ''))
        ws.cell(row=row, column=5, value=float(item.get('unit_cost', 0))).number_format = EXCEL_STYLES['currency_format']
        value = Decimal(str(item.get('total_value', 0)))
        ws.cell(row=row, column=6, value=float(value)).number_format = EXCEL_STYLES['currency_format']
        total_value += value
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Total
    for col in range(1, 7):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="TOTAL")
    ws.cell(row=row, column=6, value=float(total_value)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 14
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"inventory_valuation_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_production_daily_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for daily production report."""
    from apps.reports.services import ProductionReportService
    from decimal import Decimal
    
    report_date = dates['daily_date']
    data = ProductionReportService.get_daily_summary(report_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Production"
    
    row = _add_excel_title(
        ws, 
        f"Daily Production Report - {report_date.strftime('%A, %B %d, %Y')}", 
        "Production Summary",
        max_col=5
    )
    
    # Summary KPIs
    ws.cell(row=row, column=1, value="Total Batches").font = Font(size=9, color='666666')
    ws.cell(row=row, column=2, value=data.get('batch_count', 0)).font = Font(bold=True, size=12)
    ws.cell(row=row, column=2).fill = EXCEL_STYLES['info_fill']
    
    ws.cell(row=row, column=3, value="Total Units").font = Font(size=9, color='666666')
    ws.cell(row=row, column=4, value=data.get('total_units', 0)).font = Font(bold=True, size=12)
    ws.cell(row=row, column=4).fill = EXCEL_STYLES['success_fill']
    row += 2
    
    # Batches table
    ws.cell(row=row, column=1, value="Production Batches").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Product', 'Batch #', 'Quantity', 'Status', 'Production Cost']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_cost = Decimal('0')
    batches = data.get('batches', [])
    for idx, batch in enumerate(batches):
        ws.cell(row=row, column=1, value=batch.get('product_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=batch.get('batch_number', ''))
        ws.cell(row=row, column=3, value=batch.get('quantity', 0)).alignment = Alignment(horizontal='center')
        
        status_cell = ws.cell(row=row, column=4, value=batch.get('status', ''))
        status = batch.get('status', '').upper()
        if status == 'COMPLETED':
            status_cell.font = EXCEL_STYLES['success_font']
        elif status in ['CANCELLED', 'FAILED']:
            status_cell.font = EXCEL_STYLES['danger_font']
        
        cost = Decimal(str(batch.get('production_cost', 0)))
        ws.cell(row=row, column=5, value=float(cost)).number_format = EXCEL_STYLES['currency_format']
        total_cost += cost
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Total
    for col in range(1, 6):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="TOTAL")
    ws.cell(row=row, column=3, value=data.get('total_units', 0)).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=5, value=float(total_cost)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 15
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"production_daily_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_production_weekly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for weekly production report."""
    from apps.reports.services import ProductionReportService
    from decimal import Decimal
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    data = ProductionReportService.get_period_summary(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Weekly Production"
    
    row = _add_excel_title(ws, "Weekly Production Report", period_label, max_col=4)
    
    # Daily breakdown
    ws.cell(row=row, column=1, value="Daily Production").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Date', 'Batches', 'Units Produced', 'Cost']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_batches = 0
    total_units = 0
    total_cost = Decimal('0')
    
    daily_data = data.get('daily_breakdown', [])
    for idx, day in enumerate(daily_data):
        day_date = day.get('date')
        ws.cell(row=row, column=1, value=day_date.strftime('%a %b %d') if day_date else '')
        ws.cell(row=row, column=2, value=day.get('batch_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=day.get('units', 0)).alignment = Alignment(horizontal='center')
        cost = Decimal(str(day.get('cost', 0)))
        ws.cell(row=row, column=4, value=float(cost)).number_format = EXCEL_STYLES['currency_format']
        
        total_batches += day.get('batch_count', 0)
        total_units += day.get('units', 0)
        total_cost += cost
        
        for col in range(1, 5):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Totals
    for col in range(1, 5):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="WEEK TOTAL")
    ws.cell(row=row, column=2, value=total_batches).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=3, value=total_units).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=4, value=float(total_cost)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    for col in ['A', 'B', 'C', 'D']:
        ws.column_dimensions[col].width = 16
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"production_weekly_{start_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_production_monthly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for monthly production report."""
    from apps.reports.services import ProductionReportService
    from decimal import Decimal
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    period_label = dates.get('month_label', start_date.strftime('%B %Y'))
    
    data = ProductionReportService.get_period_summary(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Production"
    
    row = _add_excel_title(ws, "Monthly Production Report", period_label, max_col=4)
    
    # Summary - use correct field names from ProductionReportService.get_period_summary()
    ws.cell(row=row, column=1, value="Total Batches").font = Font(bold=True)
    ws.cell(row=row, column=2, value=data.get('batch_count', 0)).fill = EXCEL_STYLES['info_fill']
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Total Units").font = Font(bold=True)
    ws.cell(row=row, column=2, value=data.get('total_units', 0)).fill = EXCEL_STYLES['success_fill']
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Total Cost").font = Font(bold=True)
    cost_cell = ws.cell(row=row, column=2, value=float(data.get('total_cost', 0)))
    cost_cell.number_format = EXCEL_STYLES['currency_format']
    cost_cell.fill = EXCEL_STYLES['warning_fill']
    cost_cell.font = Font(bold=True, size=12)
    row += 2
    
    # Product breakdown
    ws.cell(row=row, column=1, value="Production by Product").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Product', 'Batches', 'Units', 'Cost']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    products = data.get('product_breakdown', [])
    for idx, product in enumerate(products):
        ws.cell(row=row, column=1, value=product.get('product_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=product.get('batch_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=product.get('units', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=float(product.get('cost', 0))).number_format = EXCEL_STYLES['currency_format']
        
        for col in range(1, 5):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"production_monthly_{start_date.strftime('%Y%m')}.xlsx"
    return buffer.getvalue(), filename


def _generate_payroll_monthly_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for monthly payroll report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    month = dates.get('month', dates['today'].month)
    year = dates.get('year', dates['today'].year)
    period_label = dates.get('month_label', f"{month}/{year}")
    
    data = FinancialReportService.get_payroll_monthly(year, month)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Payroll"
    
    row = _add_excel_title(ws, "Monthly Payroll Report", period_label, max_col=6)
    
    # Summary
    ws.cell(row=row, column=1, value="Total Employees").font = Font(bold=True)
    ws.cell(row=row, column=2, value=data.get('employee_count', 0)).fill = EXCEL_STYLES['info_fill']
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Total Payroll").font = Font(bold=True)
    payroll_cell = ws.cell(row=row, column=2, value=float(data.get('total_payroll', 0)))
    payroll_cell.number_format = EXCEL_STYLES['currency_format']
    payroll_cell.fill = EXCEL_STYLES['success_fill']
    payroll_cell.font = Font(bold=True, size=12)
    row += 2
    
    # Employee breakdown
    ws.cell(row=row, column=1, value="Employee Details").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Employee', 'Role', 'Hours', 'Base Pay', 'Deductions', 'Net Pay']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_net = Decimal('0')
    employees = data.get('employees', [])
    for idx, emp in enumerate(employees):
        ws.cell(row=row, column=1, value=emp.get('name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=emp.get('role', ''))
        ws.cell(row=row, column=3, value=emp.get('hours', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=float(emp.get('base_pay', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(emp.get('deductions', 0))).number_format = EXCEL_STYLES['currency_format']
        net = Decimal(str(emp.get('net_pay', 0)))
        ws.cell(row=row, column=6, value=float(net)).number_format = EXCEL_STYLES['currency_format']
        total_net += net
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Total
    for col in range(1, 7):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="TOTAL")
    ws.cell(row=row, column=6, value=float(total_net)).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"payroll_monthly_{year}{month:02d}.xlsx"
    return buffer.getvalue(), filename


def _generate_low_stock_alerts_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for low stock alerts report."""
    from apps.reports.services import InventoryReportService
    from decimal import Decimal
    
    report_date = dates['today']
    all_items = InventoryReportService.get_current_stock_levels()
    
    # Filter to low stock items only
    low_stock_items = [item for item in all_items if item.get('is_low', False)]
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Low Stock Alerts"
    
    row = _add_excel_title(
        ws, 
        f"Low Stock Alerts - {report_date.strftime('%A, %B %d, %Y')}", 
        f"{len(low_stock_items)} items below minimum level",
        max_col=5
    )
    
    if not low_stock_items:
        ws.cell(row=row, column=1, value="No items below minimum stock level").font = Font(italic=True, color='28A745')
        row += 2
    else:
        headers = ['Item', 'Current Stock', 'Minimum Level', 'Shortage', 'Unit']
        for col, header in enumerate(headers, 1):
            _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
        row += 1
        
        for idx, item in enumerate(low_stock_items):
            ws.cell(row=row, column=1, value=item.get('name', '')).font = Font(bold=True)
            
            current = float(item.get('current_stock', 0))
            minimum = float(item.get('minimum_stock', 0))
            shortage = minimum - current
            
            stock_cell = ws.cell(row=row, column=2, value=current)
            stock_cell.number_format = '#,##0.0'
            stock_cell.font = EXCEL_STYLES['danger_font']
            
            ws.cell(row=row, column=3, value=minimum).number_format = '#,##0.0'
            
            shortage_cell = ws.cell(row=row, column=4, value=shortage)
            shortage_cell.number_format = '#,##0.0'
            shortage_cell.font = EXCEL_STYLES['danger_font']
            
            ws.cell(row=row, column=5, value=item.get('unit', ''))
            
            for col in range(1, 6):
                _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
            row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 10
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"low_stock_alerts_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_efficiency_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for production efficiency report."""
    from apps.production.models import ProductionBatch
    from django.db.models import Sum, Count
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    # Get production batches for the period
    batches = ProductionBatch.objects.filter(
        production_date__gte=start_date,
        production_date__lte=end_date
    )
    
    totals = batches.aggregate(
        total_batches=Count('id'),
        total_units=Coalesce(Sum('quantity_produced'), 0),
        total_planned=Coalesce(Sum('expected_yield'), 0),
    )
    
    total_batches = totals['total_batches']
    total_units = totals['total_units']
    total_planned = totals['total_planned']
    
    if total_planned > 0:
        avg_efficiency = (Decimal(total_units) / Decimal(total_planned)) * 100
        waste_rate = max(Decimal('0'), ((Decimal(total_planned) - Decimal(total_units)) / Decimal(total_planned)) * 100)
        units_wasted = max(0, total_planned - total_units)
    else:
        avg_efficiency = Decimal('100')
        waste_rate = Decimal('0')
        units_wasted = 0
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Efficiency Report"
    
    row = _add_excel_title(ws, "Production Efficiency Report", period_label, max_col=5)
    
    # Summary KPIs
    ws.cell(row=row, column=1, value="Overall Efficiency").font = Font(bold=True)
    eff_cell = ws.cell(row=row, column=2, value=float(avg_efficiency) / 100)
    eff_cell.number_format = EXCEL_STYLES['percent_format']
    eff_cell.fill = EXCEL_STYLES['success_fill'] if avg_efficiency >= 95 else EXCEL_STYLES['warning_fill']
    eff_cell.font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Waste Rate").font = Font(bold=True)
    waste_cell = ws.cell(row=row, column=2, value=float(waste_rate) / 100)
    waste_cell.number_format = EXCEL_STYLES['percent_format']
    waste_cell.fill = EXCEL_STYLES['success_fill'] if waste_rate <= 5 else EXCEL_STYLES['danger_fill']
    waste_cell.font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Units Wasted").font = Font(bold=True)
    ws.cell(row=row, column=2, value=units_wasted).font = Font(bold=True, size=12)
    row += 2
    
    # Product breakdown
    ws.cell(row=row, column=1, value="Efficiency by Product").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Product', 'Batches', 'Planned', 'Actual', 'Efficiency']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    product_data = batches.values(
        'product__name'
    ).annotate(
        batch_count=Count('id'),
        actual_qty=Coalesce(Sum('quantity_produced'), 0),
        planned_qty=Coalesce(Sum('expected_yield'), 0),
    ).order_by('-actual_qty')
    
    for idx, p in enumerate(product_data):
        ws.cell(row=row, column=1, value=p['product__name']).font = Font(bold=True)
        ws.cell(row=row, column=2, value=p['batch_count']).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=p['planned_qty']).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=p['actual_qty']).alignment = Alignment(horizontal='center')
        
        if p['planned_qty'] > 0:
            eff = float(p['actual_qty']) / float(p['planned_qty'])
        else:
            eff = 1.0
        eff_cell = ws.cell(row=row, column=5, value=eff)
        eff_cell.number_format = EXCEL_STYLES['percent_format']
        if eff < 0.95:
            eff_cell.font = EXCEL_STYLES['danger_font']
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 22
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"efficiency_report_{start_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_stock_movement_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for stock movement report."""
    from apps.production.models import ProductStock, ProductStockMovement
    from django.db.models import Sum
    from django.db.models.functions import Coalesce
    
    end_date = dates.get('yesterday', dates['today'] - timedelta(days=1))
    start_date = end_date - timedelta(days=6)
    
    movements = ProductStockMovement.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('product').order_by('-created_at')
    
    # Calculate totals
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
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Movement"
    
    period_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    row = _add_excel_title(ws, "Stock Movement Report", period_label, max_col=5)
    
    # Summary
    summary_items = [
        ('Production (In)', total_production, EXCEL_STYLES['success_fill']),
        ('Returns (In)', total_returns, EXCEL_STYLES['info_fill']),
        ('Dispatched (Out)', total_dispatched, EXCEL_STYLES['warning_fill']),
        ('Adjustments', total_adjustments, EXCEL_STYLES['info_fill']),
        ('Net Change', net_change, EXCEL_STYLES['success_fill'] if net_change >= 0 else EXCEL_STYLES['danger_fill']),
    ]
    
    for label, value, fill in summary_items:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        val_cell = ws.cell(row=row, column=2, value=value)
        val_cell.fill = fill
        val_cell.font = Font(bold=True, size=11)
        row += 1
    
    row += 1
    
    # Movement details
    ws.cell(row=row, column=1, value="Recent Movements").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Date', 'Product', 'Type', 'Quantity', 'Recorded By']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, mv in enumerate(movements[:50]):  # Limit to 50 rows
        ws.cell(row=row, column=1, value=mv.created_at.strftime('%Y-%m-%d %H:%M'))
        ws.cell(row=row, column=2, value=mv.product.name if mv.product else '')
        ws.cell(row=row, column=3, value=mv.movement_type)
        
        qty_cell = ws.cell(row=row, column=4, value=mv.quantity)
        if mv.quantity < 0:
            qty_cell.font = EXCEL_STYLES['danger_font']
        
        ws.cell(row=row, column=5, value=mv.recorded_by.get_full_name() if mv.recorded_by else '')
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 16
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"stock_movement_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_salesperson_performance_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for salesperson performance report."""
    from apps.reports.services import SalesReportService
    from decimal import Decimal
    import calendar
    
    start_date = dates['month_start']
    end_date = dates['month_end']
    period_label = dates.get('month_label', start_date.strftime('%B %Y'))
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Salesperson Performance"
    
    row = _add_excel_title(ws, "Salesperson Performance Report", period_label, max_col=6)
    
    # Summary
    summary = data.get('summary', {})
    ws.cell(row=row, column=1, value="Total Revenue").font = Font(bold=True)
    rev_cell = ws.cell(row=row, column=2, value=float(summary.get('total_revenue', 0)))
    rev_cell.number_format = EXCEL_STYLES['currency_format']
    rev_cell.fill = EXCEL_STYLES['success_fill']
    rev_cell.font = Font(bold=True, size=12)
    
    ws.cell(row=row, column=3, value="Total Dispatches").font = Font(bold=True)
    ws.cell(row=row, column=4, value=summary.get('total_dispatches', 0)).font = Font(bold=True, size=12)
    row += 2
    
    # Salesperson breakdown
    ws.cell(row=row, column=1, value="Performance by Salesperson").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Salesperson', 'Dispatches', 'Units Sold', 'Revenue', 'Commission', '% Share']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    salespeople = data.get('salespeople', [])
    for idx, sp in enumerate(salespeople):
        ws.cell(row=row, column=1, value=sp.get('name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=sp.get('dispatch_count', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=sp.get('units_sold', 0)).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=float(sp.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(sp.get('commission', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=6, value=float(sp.get('revenue_share', 0)) / 100).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 10
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"salesperson_performance_{start_date.strftime('%Y%m')}.xlsx"
    return buffer.getvalue(), filename


def _generate_crate_accountability_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for crate accountability report."""
    from apps.reports.services import SalesReportService
    
    start_date = dates['week_start']
    end_date = dates['week_end']
    period_label = dates.get('week_label', f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    salespeople = data.get('salespeople', [])
    
    # Calculate crate totals
    total_dispatched = sum(sp.get('crates_dispatched', 0) or 0 for sp in salespeople)
    total_returned = sum(sp.get('crates_returned', 0) or 0 for sp in salespeople)
    total_lost = sum(sp.get('crates_lost', 0) or 0 for sp in salespeople)
    total_damaged = sum(sp.get('crates_damaged', 0) or 0 for sp in salespeople)
    total_outstanding = total_dispatched - total_returned - total_lost - total_damaged
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Crate Accountability"
    
    row = _add_excel_title(ws, "Crate Accountability Report", period_label, max_col=6)
    
    # Summary
    summary_items = [
        ('Total Dispatched', total_dispatched, EXCEL_STYLES['info_fill']),
        ('Total Returned', total_returned, EXCEL_STYLES['success_fill']),
        ('Lost', total_lost, EXCEL_STYLES['danger_fill']),
        ('Damaged', total_damaged, EXCEL_STYLES['warning_fill']),
        ('Outstanding', total_outstanding, EXCEL_STYLES['danger_fill'] if total_outstanding > 0 else EXCEL_STYLES['success_fill']),
    ]
    
    for col, (label, value, fill) in enumerate(summary_items, 1):
        ws.cell(row=row, column=col, value=label).font = Font(size=9, color='666666')
        val_cell = ws.cell(row=row+1, column=col, value=value)
        val_cell.fill = fill
        val_cell.font = Font(bold=True, size=12)
    row += 3
    
    # Salesperson breakdown
    ws.cell(row=row, column=1, value="By Salesperson").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Salesperson', 'Dispatched', 'Returned', 'Lost', 'Damaged', 'Outstanding']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, sp in enumerate(salespeople):
        dispatched = sp.get('crates_dispatched', 0) or 0
        returned = sp.get('crates_returned', 0) or 0
        lost = sp.get('crates_lost', 0) or 0
        damaged = sp.get('crates_damaged', 0) or 0
        outstanding = dispatched - returned - lost - damaged
        
        ws.cell(row=row, column=1, value=sp.get('name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=dispatched).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=returned).alignment = Alignment(horizontal='center')
        
        lost_cell = ws.cell(row=row, column=4, value=lost)
        lost_cell.alignment = Alignment(horizontal='center')
        if lost > 0:
            lost_cell.font = EXCEL_STYLES['danger_font']
        
        damaged_cell = ws.cell(row=row, column=5, value=damaged)
        damaged_cell.alignment = Alignment(horizontal='center')
        if damaged > 0:
            damaged_cell.font = EXCEL_STYLES['warning_font']
        
        outstanding_cell = ws.cell(row=row, column=6, value=outstanding)
        outstanding_cell.alignment = Alignment(horizontal='center')
        if outstanding > 0:
            outstanding_cell.font = EXCEL_STYLES['danger_font']
        
        for col in range(1, 7):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws.column_dimensions[col].width = 14
    ws.column_dimensions['A'].width = 18
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"crate_accountability_{dates['today'].strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_commission_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for commission report."""
    from apps.reports.services import SalesReportService
    from decimal import Decimal
    import calendar
    
    # Commission report is for last month
    year = dates.get('last_month_start', dates['month_start']).year
    month = dates.get('last_month_start', dates['month_start']).month
    
    data = SalesReportService.get_commission_report(year, month)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Commission Report"
    
    period_label = f"{calendar.month_name[month]} {year}"
    row = _add_excel_title(ws, "Commission Report", period_label, max_col=5)
    
    # Summary
    summary = data.get('summary', {})
    ws.cell(row=row, column=1, value="Total Commission").font = Font(bold=True)
    total_cell = ws.cell(row=row, column=2, value=float(summary.get('total_commission', 0)))
    total_cell.number_format = EXCEL_STYLES['currency_format']
    total_cell.fill = EXCEL_STYLES['success_fill']
    total_cell.font = Font(bold=True, size=12)
    row += 2
    
    # Commission breakdown
    ws.cell(row=row, column=1, value="Commission by Salesperson").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Salesperson', 'Revenue', 'Commission Rate', 'Commission', '% of Total']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    total_commission = Decimal(str(summary.get('total_commission', 1))) or Decimal('1')
    
    for idx, comm in enumerate(data.get('commissions', [])):
        ws.cell(row=row, column=1, value=comm.get('salesperson_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=float(comm.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=3, value=float(comm.get('commission_rate', 0)) / 100).number_format = EXCEL_STYLES['percent_format']
        ws.cell(row=row, column=4, value=float(comm.get('commission', 0))).number_format = EXCEL_STYLES['currency_format']
        
        pct = float(Decimal(str(comm.get('commission', 0))) / total_commission) if total_commission else 0
        ws.cell(row=row, column=5, value=pct).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"commission_report_{year}{month:02d}.xlsx"
    return buffer.getvalue(), filename


def _generate_pnl_annual_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for annual P&L report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    year = dates.get('year', dates['today'].year)
    data = FinancialReportService.get_annual_pnl(year)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Annual P&L"
    
    row = _add_excel_title(ws, f"Annual Profit & Loss Report - {year}", "Financial Summary", max_col=6)
    
    # Summary KPIs
    summary_items = [
        ('Total Revenue', data.get('revenue', 0), EXCEL_STYLES['success_fill']),
        ('Total Expenses', data.get('total_expenses', 0), EXCEL_STYLES['warning_fill']),
        ('Net Profit', data.get('net_profit', 0), 
         EXCEL_STYLES['success_fill'] if data.get('net_profit', 0) >= 0 else EXCEL_STYLES['danger_fill']),
    ]
    
    for label, value, fill in summary_items:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        val_cell = ws.cell(row=row, column=2, value=float(value))
        val_cell.number_format = EXCEL_STYLES['currency_format']
        val_cell.fill = fill
        val_cell.font = Font(bold=True, size=12)
        row += 1
    
    margin = data.get('profit_margin', 0)
    ws.cell(row=row, column=1, value="Profit Margin").font = Font(bold=True)
    margin_cell = ws.cell(row=row, column=2, value=float(margin) / 100 if margin else 0)
    margin_cell.number_format = EXCEL_STYLES['percent_format']
    margin_cell.font = Font(bold=True, size=12)
    row += 2
    
    # Monthly breakdown
    ws.cell(row=row, column=1, value="Monthly Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Month', 'Revenue', 'Expenses', 'Net Profit', 'Margin']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, month_data in enumerate(data.get('monthly_breakdown', [])):
        ws.cell(row=row, column=1, value=month_data.get('month_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=float(month_data.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=3, value=float(month_data.get('expenses', 0))).number_format = EXCEL_STYLES['currency_format']
        
        profit_cell = ws.cell(row=row, column=4, value=float(month_data.get('net_profit', 0)))
        profit_cell.number_format = EXCEL_STYLES['currency_format']
        if month_data.get('net_profit', 0) < 0:
            profit_cell.font = EXCEL_STYLES['danger_font']
        
        margin_val = month_data.get('margin', 0)
        ws.cell(row=row, column=5, value=float(margin_val) / 100 if margin_val else 0).number_format = EXCEL_STYLES['percent_format']
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Totals
    for col in range(1, 6):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="YEAR TOTAL")
    ws.cell(row=row, column=2, value=float(data.get('revenue', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=3, value=float(data.get('total_expenses', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=4, value=float(data.get('net_profit', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=5, value=float(margin) / 100 if margin else 0).number_format = EXCEL_STYLES['percent_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 12
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"pnl_annual_{year}.xlsx"
    return buffer.getvalue(), filename


def _generate_payroll_annual_excel(dates: dict) -> Tuple[bytes, str]:
    """Generate formatted Excel for annual payroll report."""
    from apps.reports.services import FinancialReportService
    from decimal import Decimal
    
    year = dates.get('year', dates['today'].year)
    data = FinancialReportService.get_payroll_annual(year)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Annual Payroll"
    
    row = _add_excel_title(ws, f"Annual Payroll Report - {year}", "Payroll Summary", max_col=6)
    
    # Summary KPIs
    ws.cell(row=row, column=1, value="Total Payroll").font = Font(bold=True)
    total_cell = ws.cell(row=row, column=2, value=float(data.get('grand_total', 0)))
    total_cell.number_format = EXCEL_STYLES['currency_format']
    total_cell.fill = EXCEL_STYLES['success_fill']
    total_cell.font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="Monthly Average").font = Font(bold=True)
    avg_cell = ws.cell(row=row, column=2, value=float(data.get('monthly_avg', 0)))
    avg_cell.number_format = EXCEL_STYLES['currency_format']
    avg_cell.font = Font(bold=True, size=12)
    row += 1
    
    ws.cell(row=row, column=1, value="YoY Change").font = Font(bold=True)
    yoy = data.get('yoy_change', 0)
    yoy_cell = ws.cell(row=row, column=2, value=float(yoy) / 100 if yoy else 0)
    yoy_cell.number_format = EXCEL_STYLES['percent_format']
    yoy_cell.font = Font(bold=True, size=12)
    if yoy > 0:
        yoy_cell.fill = EXCEL_STYLES['danger_fill']
    elif yoy < 0:
        yoy_cell.fill = EXCEL_STYLES['success_fill']
    row += 2
    
    # Category breakdown
    ws.cell(row=row, column=1, value="Category Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    categories = [
        ('Salaries', data.get('salary_total', 0)),
        ('Casual Labor', data.get('casual_total', 0)),
        ('Misc Expenses', data.get('misc_total', 0)),
    ]
    
    for label, value in categories:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=float(value)).number_format = EXCEL_STYLES['currency_format']
        row += 1
    
    row += 1
    
    # Monthly breakdown
    ws.cell(row=row, column=1, value="Monthly Breakdown").font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Month', 'Salary', 'Casual', 'Misc', 'Total']
    for col, header in enumerate(headers, 1):
        _apply_excel_header_style(ws.cell(row=row, column=col, value=header))
    row += 1
    
    for idx, month_data in enumerate(data.get('monthly_breakdown', [])):
        ws.cell(row=row, column=1, value=month_data.get('month_name', '')).font = Font(bold=True)
        ws.cell(row=row, column=2, value=float(month_data.get('salary', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=3, value=float(month_data.get('casual', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=4, value=float(month_data.get('misc', 0))).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(month_data.get('total', 0))).number_format = EXCEL_STYLES['currency_format']
        
        for col in range(1, 6):
            _apply_excel_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Totals
    for col in range(1, 6):
        _apply_excel_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=1, value="YEAR TOTAL")
    ws.cell(row=row, column=2, value=float(data.get('salary_total', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=3, value=float(data.get('casual_total', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=4, value=float(data.get('misc_total', 0))).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=5, value=float(data.get('grand_total', 0))).number_format = EXCEL_STYLES['currency_format']
    
    row += 2
    _add_excel_branding_footer(ws, row)
    
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 14
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"payroll_annual_{year}.xlsx"
    return buffer.getvalue(), filename


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
        
        # Generate PDFs and Excel files
        attachments = []
        excel_generated = []
        
        for report_code in reports_to_generate:
            # Generate PDF (required)
            pdf_bytes, filename_or_error = generate_report_pdf(report_code, dates)
            if pdf_bytes:
                attachments.append((filename_or_error, pdf_bytes, 'application/pdf'))
                result['reports_generated'].append(report_code)
            else:
                result['reports_failed'].append(f"{report_code}: {filename_or_error}")
            
            # Generate Excel (optional backup - failure doesn't block email)
            excel_bytes, excel_filename = generate_report_excel(report_code, dates)
            if excel_bytes:
                attachments.append((
                    excel_filename, 
                    excel_bytes, 
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ))
                excel_generated.append(report_code)
            # Note: Excel failure is not critical, don't add to reports_failed
        
        if excel_generated:
            logger.info(f"Generated Excel backups for: {', '.join(excel_generated)}")
        
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
