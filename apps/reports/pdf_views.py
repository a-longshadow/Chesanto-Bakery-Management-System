"""
PDF Report Views
================
WeasyPrint-based PDF generation for all reports.
Each report has a corresponding PDF endpoint.
"""
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from datetime import timedelta, date
from decimal import Decimal
import calendar

from .decorators import report_access_required
from .services import (
    SalesReportService,
    InventoryReportService,
    ProductionReportService,
    FinancialReportService,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PDF CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_pdf_css():
    """
    Returns CSS for professional PDF output with:
    - Page numbers
    - Headers/footers
    - Watermark support
    - Proper page breaks
    """
    return CSS(string='''
        @page {
            size: A4;
            margin: 2cm 1.5cm 2.5cm 1.5cm;
            
            @top-left {
                content: "Chesanto Bakery";
                font-size: 9pt;
                color: #666;
                font-family: sans-serif;
            }
            
            @top-right {
                content: string(report-title);
                font-size: 9pt;
                color: #666;
                font-family: sans-serif;
            }
            
            @bottom-center {
                content: "Confidential - Internal Use Only";
                font-size: 8pt;
                color: #999;
                font-family: sans-serif;
            }
            
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
                font-family: sans-serif;
            }
        }
        
        @page :first {
            @top-left { content: ""; }
            @top-right { content: ""; }
        }
        
        /* Base styles */
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        /* Report title - captured by string() */
        .pdf-title {
            string-set: report-title content();
        }
        
        /* Header section */
        .pdf-header {
            text-align: center;
            margin-bottom: 20pt;
            padding-bottom: 15pt;
            border-bottom: 2pt solid #2563eb;
        }
        
        .pdf-header h1 {
            font-size: 18pt;
            color: #1e40af;
            margin: 0 0 5pt 0;
        }
        
        .pdf-header .subtitle {
            font-size: 11pt;
            color: #666;
            margin: 0;
        }
        
        .pdf-header .date-range {
            font-size: 10pt;
            color: #888;
            margin-top: 5pt;
        }
        
        /* Generated timestamp */
        .pdf-generated {
            font-size: 8pt;
            color: #999;
            text-align: right;
            margin-bottom: 15pt;
        }
        
        /* KPI Cards */
        .kpi-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10pt;
            margin-bottom: 20pt;
        }
        
        .kpi-card {
            flex: 1 1 calc(25% - 10pt);
            min-width: 120pt;
            background: #f8fafc;
            border: 1pt solid #e2e8f0;
            border-radius: 6pt;
            padding: 12pt;
            text-align: center;
        }
        
        .kpi-card.success { border-left: 3pt solid #10b981; }
        .kpi-card.warning { border-left: 3pt solid #f59e0b; }
        .kpi-card.danger { border-left: 3pt solid #ef4444; }
        .kpi-card.info { border-left: 3pt solid #3b82f6; }
        
        .kpi-label {
            font-size: 8pt;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5pt;
            margin-bottom: 4pt;
        }
        
        .kpi-value {
            font-size: 16pt;
            font-weight: bold;
            color: #1e293b;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15pt;
            font-size: 9pt;
        }
        
        th, td {
            padding: 8pt 6pt;
            text-align: left;
            border-bottom: 1pt solid #e2e8f0;
        }
        
        th {
            background: #f1f5f9;
            font-weight: 600;
            color: #475569;
            font-size: 8pt;
            text-transform: uppercase;
            letter-spacing: 0.3pt;
        }
        
        tr:nth-child(even) {
            background: #fafafa;
        }
        
        tfoot td {
            background: #f1f5f9;
            font-weight: bold;
            border-top: 2pt solid #cbd5e1;
        }
        
        .text-end { text-align: right; }
        .text-center { text-align: center; }
        .text-success { color: #10b981; }
        .text-danger { color: #ef4444; }
        .text-muted { color: #94a3b8; }
        .fw-bold { font-weight: bold; }
        
        /* Section headers */
        .section-header {
            font-size: 12pt;
            font-weight: 600;
            color: #1e40af;
            margin: 20pt 0 10pt 0;
            padding-bottom: 5pt;
            border-bottom: 1pt solid #cbd5e1;
            page-break-after: avoid;
        }
        
        /* Status badges */
        .badge {
            display: inline-block;
            padding: 2pt 6pt;
            border-radius: 3pt;
            font-size: 8pt;
            font-weight: 500;
        }
        
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-info { background: #dbeafe; color: #1e40af; }
        
        /* Page break controls */
        .page-break-before { page-break-before: always; }
        .page-break-after { page-break-after: always; }
        .avoid-break { page-break-inside: avoid; }
        
        table { page-break-inside: auto; }
        tr { page-break-inside: avoid; page-break-after: auto; }
        thead { display: table-header-group; }
        tfoot { display: table-footer-group; }
        
        /* Summary box */
        .summary-box {
            background: #eff6ff;
            border: 1pt solid #bfdbfe;
            border-radius: 6pt;
            padding: 12pt;
            margin: 15pt 0;
        }
        
        .summary-box h4 {
            margin: 0 0 8pt 0;
            color: #1e40af;
            font-size: 11pt;
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 30pt;
            color: #94a3b8;
        }
        
        /* Watermark (optional - applied via background) */
        .watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 72pt;
            color: rgba(0, 0, 0, 0.03);
            white-space: nowrap;
            z-index: -1;
            pointer-events: none;
        }
    ''')


def generate_pdf_response(html_content, filename):
    """
    Generate PDF from HTML content and return as HTTP response.
    """
    font_config = FontConfiguration()
    html = HTML(string=html_content, base_url='/')
    pdf = html.write_pdf(
        stylesheets=[get_pdf_css()],
        font_config=font_config,
    )
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# SALES REPORT PDFs
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@report_access_required
def sales_daily_pdf(request):
    """Daily Sales Report PDF"""
    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.localdate()
    
    data = SalesReportService.get_daily_summary(report_date)
    
    context = {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/sales_daily.html', context)
    filename = f"sales_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def sales_weekly_pdf(request):
    """Weekly Sales Report PDF"""
    # Accept either 'week_start' or 'date' parameter
    date_str = request.GET.get('week_start') or request.GET.get('date')
    if date_str:
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.localdate()
    
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    data = SalesReportService.get_weekly_summary(start_of_week)
    
    context = {
        'start_date': start_of_week,
        'end_date': end_of_week,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/sales_weekly.html', context)
    filename = f"sales_weekly_{start_of_week.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def sales_monthly_pdf(request):
    """Monthly Sales Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    data = SalesReportService.get_monthly_summary(year, month)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/sales_monthly.html', context)
    filename = f"sales_monthly_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def sales_annual_pdf(request):
    """Annual Sales Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    
    data = SalesReportService.get_annual_summary(year)
    
    context = {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/sales_annual.html', context)
    filename = f"sales_annual_{year}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def salesperson_performance_pdf(request):
    """Salesperson Performance Report PDF"""
    from calendar import monthrange
    
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Calculate date range for the month
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)
    
    data = SalesReportService.get_salesperson_performance(start_date, end_date)
    
    # Calculate additional metrics for PDF
    total_revenue = data['summary']['total_revenue']
    for sp in data['salespeople']:
        sp['avg_per_dispatch'] = sp.get('avg_revenue_per_dispatch', 0)
        sp['percentage'] = sp.get('revenue_share', 0)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'salespeople': data['salespeople'],
        'total_dispatches': data['summary']['total_dispatches'],
        'total_revenue': total_revenue,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/salesperson_performance.html', context)
    filename = f"salesperson_performance_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def commission_report_pdf(request):
    """Commission Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    data = SalesReportService.get_commission_report(year, month)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'commissions': data.get('commissions', []),
        'summary': data.get('summary', {}),
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/commission_report.html', context)
    filename = f"commission_report_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY REPORT PDFs
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@report_access_required
def inventory_daily_pdf(request):
    """Daily Inventory Report PDF"""
    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.localdate()
    
    data = InventoryReportService.get_daily_summary(report_date)
    
    context = {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/inventory_daily.html', context)
    filename = f"inventory_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def inventory_weekly_pdf(request):
    """Weekly Inventory Report PDF"""
    date_str = request.GET.get('week_start') or request.GET.get('date')
    if date_str:
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.localdate()
    
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    data = InventoryReportService.get_weekly_summary(start_of_week)
    
    context = {
        'start_date': start_of_week,
        'end_date': end_of_week,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/inventory_weekly.html', context)
    filename = f"inventory_weekly_{start_of_week.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def inventory_monthly_pdf(request):
    """Monthly Inventory Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    data = InventoryReportService.get_monthly_summary(year, month)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/inventory_monthly.html', context)
    filename = f"inventory_monthly_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def inventory_annual_pdf(request):
    """Annual Inventory Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    
    data = InventoryReportService.get_annual_summary(year)
    
    context = {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/inventory_annual.html', context)
    filename = f"inventory_annual_{year}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def inventory_valuation_pdf(request):
    """Inventory Valuation Report PDF"""
    data = InventoryReportService.get_valuation_report()
    
    context = {
        'report_date': timezone.localdate(),
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/inventory_valuation.html', context)
    filename = f"inventory_valuation_{timezone.localdate().strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def purchase_history_pdf(request):
    """Purchase History Report PDF"""
    date_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    today = timezone.localdate()
    if date_str and end_str:
        from datetime import datetime
        start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    data = InventoryReportService.get_purchase_history(start_date, end_date)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/purchase_history.html', context)
    filename = f"purchase_history_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTION REPORT PDFs
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@report_access_required
def production_daily_pdf(request):
    """Daily Production Report PDF"""
    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.localdate()
    
    data = ProductionReportService.get_daily_summary(report_date)
    
    context = {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/production_daily.html', context)
    filename = f"production_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def production_weekly_pdf(request):
    """Weekly Production Report PDF"""
    # Accept either 'week_start' or 'date' parameter
    date_str = request.GET.get('week_start') or request.GET.get('date')
    if date_str:
        from datetime import datetime
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.localdate()
    
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Note: get_weekly_summary only takes week_start, it calculates end internally
    data = ProductionReportService.get_weekly_summary(start_of_week)
    
    context = {
        'start_date': start_of_week,
        'end_date': end_of_week,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/production_weekly.html', context)
    filename = f"production_weekly_{start_of_week.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def production_monthly_pdf(request):
    """Monthly Production Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    data = ProductionReportService.get_monthly_summary(year, month)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/production_monthly.html', context)
    filename = f"production_monthly_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def production_annual_pdf(request):
    """Annual Production Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    
    data = ProductionReportService.get_annual_summary(year)
    
    context = {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/production_annual.html', context)
    filename = f"production_annual_{year}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def production_efficiency_pdf(request):
    """Production Efficiency Report PDF"""
    from datetime import datetime
    from apps.production.models import ProductionBatch
    from django.db.models import Sum, Count
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    today = timezone.localdate()
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today
    
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
    
    context = {
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
    }
    
    html = render_to_string('reports/pdf/production_efficiency.html', context)
    filename = f"production_efficiency_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def stock_movement_pdf(request):
    """Product Stock Movement Report PDF - tracks finished goods movements."""
    from datetime import datetime
    from apps.production.models import ProductStock, ProductStockMovement
    from django.db.models.functions import Coalesce
    
    today = timezone.localdate()
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today
    
    # Get all movements in date range
    movements = ProductStockMovement.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).select_related('product', 'recorded_by').order_by('-created_at')
    
    # Calculate totals by movement type
    from django.db.models import Sum
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
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'movements': movements[:100],
        'stocks': stocks,
        'total_current_stock': total_current_stock,
        'total_production': total_production,
        'total_dispatched': total_dispatched,
        'total_returns': total_returns,
        'total_adjustments': total_adjustments,
        'total_in': total_in,
        'total_out': total_out,
        'net_change': net_change,
        'total_transactions': movements.count(),
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/stock_movement.html', context)
    filename = f"stock_movement_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


# ═══════════════════════════════════════════════════════════════════════════════
# PAYROLL REPORT PDFs
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@report_access_required
def payroll_monthly_pdf(request):
    """Monthly Payroll Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    summary = FinancialReportService.get_payroll_monthly(year, month)
    
    context = {
        'year': summary.get('year', year),
        'month': summary.get('month', month),
        'month_name': calendar.month_name[summary.get('month', month)],
        'data': summary,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/payroll_monthly.html', context)
    filename = f"payroll_monthly_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def payroll_annual_pdf(request):
    """Annual Payroll Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    
    summary = FinancialReportService.get_payroll_annual(year)
    
    context = {
        'year': summary.get('year', year),
        'data': summary,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/payroll_annual.html', context)
    filename = f"payroll_annual_{year}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def casual_labor_pdf(request):
    """Casual Labor Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    summary = FinancialReportService.get_casual_labor_report(year, month)
    
    context = {
        'year': summary.get('year', year),
        'month': summary.get('month', month),
        'month_name': calendar.month_name[summary.get('month', month)],
        'data': summary,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/casual_labor.html', context)
    filename = f"casual_labor_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def misc_expense_pdf(request):
    """Miscellaneous Expense Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    summary = FinancialReportService.get_misc_expense_report(year, month)
    
    context = {
        'year': summary.get('year', year),
        'month': summary.get('month', month),
        'month_name': calendar.month_name[summary.get('month', month)],
        'data': summary,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/misc_expense.html', context)
    filename = f"misc_expense_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCIAL REPORT PDFs
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
@report_access_required
def pnl_daily_pdf(request):
    """Daily P&L Report PDF"""
    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        report_date = timezone.localdate()
    
    data = FinancialReportService.get_daily_pnl(report_date)
    
    context = {
        'report_date': report_date,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/pnl_daily.html', context)
    filename = f"pnl_daily_{report_date.strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def pnl_weekly_pdf(request):
    """Weekly P&L Report PDF"""
    # Match the HTML view's parameter name
    date_str = request.GET.get('week_start') or request.GET.get('date')
    if date_str:
        from datetime import datetime
        try:
            week_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = None
    else:
        week_start = None
    
    # get_weekly_pnl only takes week_start (or None for current week)
    data = FinancialReportService.get_weekly_pnl(week_start)
    
    context = {
        'start_date': data['start_date'],
        'end_date': data['end_date'],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/pnl_weekly.html', context)
    filename = f"pnl_weekly_{data['start_date'].strftime('%Y%m%d')}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def pnl_monthly_pdf(request):
    """Monthly P&L Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    data = FinancialReportService.get_monthly_pnl(year, month)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/pnl_monthly.html', context)
    filename = f"pnl_monthly_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def pnl_annual_pdf(request):
    """Annual P&L Report PDF"""
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    
    data = FinancialReportService.get_annual_pnl(year)
    
    context = {
        'year': year,
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/pnl_annual.html', context)
    filename = f"pnl_annual_{year}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def product_performance_pdf(request):
    """Product Performance Report PDF"""
    from datetime import datetime as dt
    from calendar import monthrange
    
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Calculate date range for the method
    start_date = dt(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = dt(year, month, last_day).date()
    
    data = FinancialReportService.get_product_performance(start_date, end_date)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/product_performance.html', context)
    filename = f"product_performance_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)


@login_required
@report_access_required
def expense_summary_pdf(request):
    """Expense Summary Report PDF"""
    from datetime import datetime as dt
    from calendar import monthrange
    
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Calculate date range for the method
    start_date = dt(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = dt(year, month, last_day).date()
    
    data = FinancialReportService.get_expense_summary(start_date, end_date)
    
    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'data': data,
        'generated_at': timezone.now(),
    }
    
    html = render_to_string('reports/pdf/expense_summary.html', context)
    filename = f"expense_summary_{year}{month:02d}.pdf"
    return generate_pdf_response(html, filename)
