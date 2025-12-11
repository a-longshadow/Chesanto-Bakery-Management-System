"""
Analytics App Views
Real-time data aggregation and analysis views
NO models - queries live data from Production, Sales, Inventory apps

Chart.js Integration:
- All chart data is passed as JSON-safe context variables
- Templates use Chart.js 4.4.1 via CDN
- DecimalEncoder handles Decimal to float conversion for JSON
"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from apps.production.models import ProductionBatch, ProductStock
from apps.sales.models import SalesDispatch, SalesDispatchItem, SalesReturn, SalesReturnItem
from apps.products.models import Product
from apps.inventory.models import StockAlert
from apps.inventory.routing import ITEM_DETAILS_MODELS


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@login_required
def dashboard_view(request):
    """Real-time analytics dashboard - Executive Overview"""
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    
    # ============================================
    # TODAY'S SNAPSHOT
    # ============================================
    today_revenue = SalesReturn.objects.filter(
        return_date=today
    ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
    
    today_sold = SalesReturnItem.objects.filter(
        sales_return__return_date=today
    ).aggregate(total=Sum('qty_sold'))['total'] or 0
    
    today_dispatched = SalesDispatch.objects.filter(
        dispatch_date=today
    ).count()
    
    today_production = ProductionBatch.objects.filter(
        production_date=today
    ).aggregate(
        total_units=Sum('quantity_produced'),
        total_batches=Count('id')
    )
    
    # ============================================
    # MONTHLY METRICS
    # ============================================
    monthly_revenue = SalesReturn.objects.filter(
        return_date__gte=month_start,
        return_date__lte=today
    ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
    
    monthly_returns = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=month_start,
        sales_return__return_date__lte=today
    ).aggregate(total=Sum('qty_returned'))['total'] or 0
    
    monthly_sold = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=month_start,
        sales_return__return_date__lte=today
    ).aggregate(total=Sum('qty_sold'))['total'] or 0
    
    monthly_production = ProductionBatch.objects.filter(
        production_date__gte=month_start,
        production_date__lte=today
    ).aggregate(
        total_batches=Count('id'),
        total_units=Sum('quantity_produced')
    )
    
    # Stock alerts count (recent alerts in last 7 days)
    low_stock_count = StockAlert.objects.filter(
        triggered_at__gte=seven_days_ago
    ).count()
    
    # Total inventory value (sum across all 23 item details tables)
    total_inventory_value = Decimal('0')
    for item_id, model_class in ITEM_DETAILS_MODELS.items():
        try:
            item = model_class.objects.first()
            if item and item.current_stock and item.last_purchase_unit_price:
                total_inventory_value += Decimal(str(item.current_stock)) * item.last_purchase_unit_price
        except Exception:
            pass
    
    # ============================================
    # CHART DATA: 7-Day Revenue Trend
    # ============================================
    sales_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_revenue = SalesReturn.objects.filter(return_date=day).aggregate(
            total=Sum('total_revenue')
        )['total'] or Decimal('0')
        sales_trend.append({'date': day.strftime('%a'), 'revenue': float(day_revenue)})
    
    # ============================================
    # CHART DATA: 7-Day Production Trend
    # ============================================
    production_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_production = ProductionBatch.objects.filter(production_date=day).aggregate(
            total=Sum('quantity_produced')
        )['total'] or 0
        production_trend.append({'date': day.strftime('%a'), 'units': day_production})
    
    # ============================================
    # CHART DATA: Top 5 Products (Revenue - for Table and Doughnut)
    # ============================================
    top_products = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=thirty_days_ago
    ).values('product__name').annotate(
        revenue=Sum('revenue'),
        units_sold=Sum('qty_sold')
    ).order_by('-revenue')[:5]
    
    # Prepare for doughnut chart
    product_chart_labels = [p['product__name'] for p in top_products]
    product_chart_values = [float(p['revenue']) for p in top_products]
    
    # ============================================
    # CHART DATA: Salesperson Leaderboard (30-day)
    # ============================================
    salesperson_stats = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).values(
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ).annotate(
        total_revenue=Sum('total_revenue'),
        total_dispatches=Count('id')
    ).order_by('-total_revenue')[:5]
    
    salesperson_chart_labels = [
        f"{s['dispatch__salesperson__first_name']} {s['dispatch__salesperson__last_name']}"
        for s in salesperson_stats
    ]
    salesperson_chart_values = [float(s['total_revenue']) for s in salesperson_stats]
    
    # ============================================
    # CRATE ACCOUNTABILITY SUMMARY
    # ============================================
    crate_stats = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).aggregate(
        total_lost=Sum('crates_lost'),
        total_damaged=Sum('crates_damaged'),
    )
    
    context = {
        # Today's snapshot
        'today_revenue': today_revenue,
        'today_sold': today_sold,
        'today_dispatched': today_dispatched,
        'today_produced': today_production['total_units'] or 0,
        'today_batches': today_production['total_batches'] or 0,
        
        # Monthly metrics
        'monthly_revenue': monthly_revenue,
        'monthly_returns': monthly_returns,
        'monthly_sold': monthly_sold,
        'monthly_batches': monthly_production['total_batches'] or 0,
        'monthly_units': monthly_production['total_units'] or 0,
        'low_stock_count': low_stock_count,
        'inventory_value': total_inventory_value,
        
        # Chart data (JSON-safe)
        'sales_trend': json.dumps(sales_trend, cls=DecimalEncoder),
        'production_trend': json.dumps(production_trend, cls=DecimalEncoder),
        'product_chart_labels': json.dumps(product_chart_labels),
        'product_chart_values': json.dumps(product_chart_values),
        'salesperson_chart_labels': json.dumps(salesperson_chart_labels),
        'salesperson_chart_values': json.dumps(salesperson_chart_values),
        
        # Tables
        'top_products': list(top_products),
        'salesperson_stats': list(salesperson_stats),
        
        # Crate stats
        'total_crates_lost': crate_stats['total_lost'] or 0,
        'total_crates_damaged': crate_stats['total_damaged'] or 0,
        
        # Meta
        'today': today,
        'month_name': today.strftime('%B %Y'),
    }
    return render(request, 'analytics/dashboard.html', context)


@login_required
def product_performance_view(request):
    """Product-level performance analysis"""
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days)
    
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    product_data = []
    
    for product in products:
        # Sales from return items (actual sold quantities)
        sales = SalesReturnItem.objects.filter(
            product=product,
            sales_return__return_date__gte=start_date
        ).aggregate(
            qty_sold=Sum('qty_sold'),
            revenue=Sum('revenue')
        )
        
        # Production batches
        production = ProductionBatch.objects.filter(
            product=product,
            production_date__gte=start_date
        ).aggregate(
            qty_produced=Sum('quantity_produced'),
            batch_count=Count('id')
        )
        
        product_data.append({
            'product': product,
            'produced': production['qty_produced'] or 0,
            'sold': sales['qty_sold'] or 0,
            'revenue': sales['revenue'] or Decimal('0'),
            'batches': production['batch_count'] or 0,
        })
    
    product_data.sort(key=lambda x: x['revenue'], reverse=True)
    
    context = {
        'product_data': product_data,
        'days': days,
        'start_date': start_date,
    }
    return render(request, 'analytics/product_performance.html', context)


@login_required
def inventory_status_view(request):
    """Inventory Analytics Dashboard - Stock levels and alerts"""
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    
    # Collect data from all 23 item details tables
    items = []
    low_stock_items = []
    total_value = Decimal('0')
    
    # For chart data
    stock_levels = []
    min_levels = []
    item_names = []
    
    for item_id, model_class in ITEM_DETAILS_MODELS.items():
        try:
            item = model_class.objects.first()
            if item:
                item_value = Decimal('0')
                if item.current_stock and item.last_purchase_unit_price:
                    item_value = Decimal(str(item.current_stock)) * item.last_purchase_unit_price
                
                current = float(item.current_stock or 0)
                minimum = float(item.minimum_stock_level or 0)
                
                is_low = current < minimum
                deficit = round(minimum - current, 1) if is_low else 0
                
                item_data = {
                    'id': item_id,
                    'name': item.name,
                    'current_stock': item.current_stock or 0,
                    'unit_of_measure': item.unit_of_measure,
                    'minimum_stock_level': item.minimum_stock_level or 0,
                    'last_purchase_unit_price': item.last_purchase_unit_price,
                    'value': item_value,
                    'is_low_stock': is_low,
                    'deficit': deficit,
                    'stock_percent': round((current / minimum * 100), 0) if minimum > 0 else 100,
                }
                items.append(item_data)
                total_value += item_value
                
                # Chart data
                item_names.append(item.name[:15])  # Truncate for chart
                stock_levels.append(current)
                min_levels.append(minimum)
                
                if is_low:
                    low_stock_items.append(item_data)
        except Exception:
            pass
    
    # Sort by item_id
    items.sort(key=lambda x: x['id'])
    
    # Recent stock alerts
    recent_alerts = StockAlert.objects.filter(
        triggered_at__gte=seven_days_ago
    ).order_by('-triggered_at')[:10]
    
    context = {
        # Chart data (JSON-safe)
        'item_names_json': json.dumps(item_names),
        'stock_levels_json': json.dumps(stock_levels),
        'min_levels_json': json.dumps(min_levels),
        
        # Table data
        'items': items,
        'low_stock_items': low_stock_items,
        'recent_alerts': recent_alerts,
        
        # Summary stats
        'total_value': total_value,
        'low_stock_count': len(low_stock_items),
        'healthy_stock_count': len(items) - len(low_stock_items),
        'total_items': len(items),
    }
    return render(request, 'analytics/inventory_status.html', context)


@login_required
def sales_trends_view(request):
    """Sales Analytics Dashboard - Comprehensive sales analysis"""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # ============================================
    # DAILY SALES (30 days) - For Bar Chart
    # ============================================
    daily_sales = []
    for i in range(30):
        day = today - timedelta(days=29-i)
        day_data = SalesReturn.objects.filter(return_date=day).aggregate(
            total_revenue=Sum('total_revenue'),
            total_sold=Sum('total_units_sold')
        )
        daily_sales.append({
            'date': day.strftime('%m/%d'),
            'revenue': float(day_data['total_revenue'] or 0),
            'units': day_data['total_sold'] or 0
        })
    
    # ============================================
    # WEEKLY SUMMARY - For Trend Analysis
    # ============================================
    weekly_totals = []
    for week in range(4):
        week_start = today - timedelta(days=(3-week)*7 + 6)
        week_end = today - timedelta(days=(3-week)*7)
        week_data = SalesReturn.objects.filter(
            return_date__gte=week_start,
            return_date__lte=week_end
        ).aggregate(
            total=Sum('total_revenue'),
            total_units=Sum('total_units_sold')
        )
        weekly_totals.append({
            'week': f"Week {week+1}",
            'start': week_start.strftime('%m/%d'),
            'end': week_end.strftime('%m/%d'),
            'revenue': week_data['total'] or Decimal('0'),
            'units': week_data['total_units'] or 0,
        })
    
    # ============================================
    # SALESPERSON LEADERBOARD - Horizontal Bar
    # ============================================
    salesperson_stats = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).values(
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ).annotate(
        total_revenue=Sum('total_revenue'),
        total_dispatches=Count('id'),
        total_units=Sum('total_units_sold')
    ).order_by('-total_revenue')[:10]
    
    salesperson_labels = [
        f"{s['dispatch__salesperson__first_name']} {s['dispatch__salesperson__last_name']}"
        for s in salesperson_stats
    ]
    salesperson_values = [float(s['total_revenue']) for s in salesperson_stats]
    
    # ============================================
    # PRODUCT BREAKDOWN - Doughnut Chart
    # ============================================
    product_sales = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=thirty_days_ago
    ).values('product__name').annotate(
        revenue=Sum('revenue'),
        qty_sold=Sum('qty_sold')
    ).order_by('-revenue')[:8]
    
    product_labels = [p['product__name'] for p in product_sales]
    product_revenue_values = [float(p['revenue']) for p in product_sales]
    product_qty_values = [p['qty_sold'] for p in product_sales]
    
    # ============================================
    # RETURN RATE ANALYSIS
    # ============================================
    return_analysis = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=thirty_days_ago
    ).aggregate(
        total_dispatched=Sum('qty_dispatched'),
        total_sold=Sum('qty_sold'),
        total_returned=Sum('qty_returned')
    )
    
    dispatched = return_analysis['total_dispatched'] or 0
    sold = return_analysis['total_sold'] or 0
    returned = return_analysis['total_returned'] or 0
    return_rate = (returned / dispatched * 100) if dispatched > 0 else 0
    
    # ============================================
    # CRATE ACCOUNTABILITY
    # ============================================
    crate_stats = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).aggregate(
        total_dispatched=Sum('dispatch__crates_dispatched'),
        total_returned=Sum('crates_returned'),
        total_lost=Sum('crates_lost'),
        total_damaged=Sum('crates_damaged'),
    )
    
    context = {
        # Chart data (JSON-safe)
        'daily_sales_json': json.dumps(daily_sales, cls=DecimalEncoder),
        'salesperson_labels_json': json.dumps(salesperson_labels),
        'salesperson_values_json': json.dumps(salesperson_values),
        'product_labels_json': json.dumps(product_labels),
        'product_revenue_json': json.dumps(product_revenue_values),
        'product_qty_json': json.dumps(product_qty_values),
        
        # Table data
        'weekly_totals': weekly_totals,
        'salesperson_stats': list(salesperson_stats),
        'product_sales': list(product_sales),
        
        # Summary stats
        'total_revenue': sum(d['revenue'] for d in daily_sales),
        'total_units_sold': sold,
        'total_units_returned': returned,
        'return_rate': round(return_rate, 1),
        
        # Crate stats
        'crates_dispatched': crate_stats['total_dispatched'] or 0,
        'crates_returned': crate_stats['total_returned'] or 0,
        'crates_lost': crate_stats['total_lost'] or 0,
        'crates_damaged': crate_stats['total_damaged'] or 0,
        
        'today': today,
    }
    return render(request, 'analytics/sales_trends.html', context)


@login_required
def production_analytics_view(request):
    """Production Analytics Dashboard - Production performance analysis"""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # ============================================
    # DAILY PRODUCTION (30 days) - For Bar Chart
    # ============================================
    daily_production = []
    for i in range(30):
        day = today - timedelta(days=29-i)
        day_data = ProductionBatch.objects.filter(production_date=day).aggregate(
            total_units=Sum('quantity_produced'),
            total_batches=Count('id'),
            total_cost=Sum('total_ingredient_cost')
        )
        daily_production.append({
            'date': day.strftime('%m/%d'),
            'units': day_data['total_units'] or 0,
            'batches': day_data['total_batches'] or 0,
            'cost': float(day_data['total_cost'] or 0)
        })
    
    # ============================================
    # YIELD VARIANCE ANALYSIS
    # ============================================
    batches = ProductionBatch.objects.filter(
        production_date__gte=thirty_days_ago
    ).select_related('product')
    
    variance_data = []
    total_expected = 0
    total_actual = 0
    for batch in batches:
        total_expected += batch.expected_yield
        total_actual += batch.quantity_produced
        
    overall_variance = total_actual - total_expected
    variance_percent = (overall_variance / total_expected * 100) if total_expected > 0 else 0
    
    # Per-product variance
    product_variance = ProductionBatch.objects.filter(
        production_date__gte=thirty_days_ago
    ).values('product__name').annotate(
        total_expected=Sum('expected_yield'),
        total_actual=Sum('quantity_produced'),
        batch_count=Count('id')
    ).order_by('-total_actual')
    
    for pv in product_variance:
        pv['variance'] = pv['total_actual'] - pv['total_expected']
        pv['variance_pct'] = round((pv['variance'] / pv['total_expected'] * 100), 1) if pv['total_expected'] > 0 else 0
    
    # ============================================
    # PRODUCT MIX - Doughnut Chart
    # ============================================
    product_mix = ProductionBatch.objects.filter(
        production_date__gte=thirty_days_ago
    ).values('product__name').annotate(
        total_units=Sum('quantity_produced')
    ).order_by('-total_units')
    
    product_labels = [p['product__name'] for p in product_mix]
    product_values = [p['total_units'] for p in product_mix]
    
    # ============================================
    # PRODUCTION VS SALES COMPARISON
    # ============================================
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    prod_vs_sales = []
    for product in products:
        produced = ProductionBatch.objects.filter(
            product=product,
            production_date__gte=thirty_days_ago
        ).aggregate(total=Sum('quantity_produced'))['total'] or 0
        
        sold = SalesReturnItem.objects.filter(
            product=product,
            sales_return__return_date__gte=thirty_days_ago
        ).aggregate(total=Sum('qty_sold'))['total'] or 0
        
        if produced > 0 or sold > 0:
            prod_vs_sales.append({
                'product': product.name,
                'produced': produced,
                'sold': sold,
                'difference': produced - sold
            })
    
    prod_vs_sales.sort(key=lambda x: x['produced'], reverse=True)
    
    # Prepare chart data
    pvs_labels = [p['product'] for p in prod_vs_sales[:6]]
    pvs_produced = [p['produced'] for p in prod_vs_sales[:6]]
    pvs_sold = [p['sold'] for p in prod_vs_sales[:6]]
    
    context = {
        # Chart data (JSON-safe)
        'daily_production_json': json.dumps(daily_production, cls=DecimalEncoder),
        'product_labels_json': json.dumps(product_labels),
        'product_values_json': json.dumps(product_values),
        'pvs_labels_json': json.dumps(pvs_labels),
        'pvs_produced_json': json.dumps(pvs_produced),
        'pvs_sold_json': json.dumps(pvs_sold),
        
        # Table data
        'product_variance': list(product_variance),
        'prod_vs_sales': prod_vs_sales,
        
        # Summary stats
        'total_batches': len(batches),
        'total_units_produced': total_actual,
        'total_expected': total_expected,
        'overall_variance': overall_variance,
        'variance_percent': round(variance_percent, 1),
        
        'today': today,
    }
    return render(request, 'analytics/production_analytics.html', context)


@login_required
def deficit_analysis_view(request):
    """Crate deficit analysis (no cash deficits - system enforces sold+returned=dispatched)"""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Find returns with crate deficits (crates_lost + crates_damaged > 0)
    returns_with_crate_issues = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).filter(
        Q(crates_lost__gt=0) | Q(crates_damaged__gt=0)
    ).select_related('dispatch__salesperson').order_by('-return_date')[:20]
    
    # Totals
    crate_stats = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).aggregate(
        total_lost=Sum('crates_lost'),
        total_damaged=Sum('crates_damaged'),
        total_dispatched=Sum('dispatch__crates_dispatched'),
        total_returned=Sum('crates_returned'),
    )
    
    context = {
        'returns_with_issues': returns_with_crate_issues,
        'total_crates_lost': crate_stats['total_lost'] or 0,
        'total_crates_damaged': crate_stats['total_damaged'] or 0,
        'total_crates_dispatched': crate_stats['total_dispatched'] or 0,
        'total_crates_returned': crate_stats['total_returned'] or 0,
        'today': today,
    }
    return render(request, 'analytics/deficit_analysis.html', context)
