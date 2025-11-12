"""
Analytics App Views
Real-time data aggregation and analysis views
NO models - queries live data from Production, Sales, Inventory apps
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal

from apps.production.models import DailyProduction, ProductionBatch
# from apps.sales.models import Dispatch, SalesReturn, DailySales, Salesperson  # ❌ REMOVED - Sales app deleted
from apps.inventory.models import InventoryItem, StockMovement
from apps.products.models import Product


@login_required
def dashboard_view(request):
    """
    Real-time analytics dashboard
    8 charts with live data aggregation
    
    NOTE: Sales analytics disabled - sales app removed for rebuild
    """
    from django.http import HttpResponse
    return HttpResponse(
        "<h1>Analytics Dashboard Temporarily Disabled</h1>"
        "<p>Sales app has been removed for rebuild. Analytics will be restored after sales app redesign.</p>"
        "<p><a href='/'>Return to Home</a></p>"
    )
    today_batches = ProductionBatch.objects.filter(
        daily_production__date=today
    ).aggregate(
        total_ingredient_cost=Sum('ingredient_cost'),
        total_packaging_cost=Sum('packaging_cost')
    )
    
    pl_waterfall['direct_costs'] = (
        (today_batches['total_ingredient_cost'] or 0) +
        (today_batches['total_packaging_cost'] or 0)
    )
    pl_waterfall['profit'] = (
        pl_waterfall['revenue'] -
        pl_waterfall['direct_costs'] -
        pl_waterfall['indirect_costs']
    )
    
    # 2. Product Comparison (Past 30 days)
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    product_performance = []
    
    for product in products:
        # Get batches for this product in last 30 days
        batches = ProductionBatch.objects.filter(
            product=product,
            daily_production__date__gte=thirty_days_ago
        ).aggregate(
            total_revenue=Sum('expected_revenue'),
            total_cost=Sum('total_cost'),
            total_profit=Sum('gross_profit'),
            avg_margin=Avg('gross_margin_percentage')
        )
        
        product_performance.append({
            'name': product.name,
            'revenue': batches['total_revenue'] or 0,
            'cost': batches['total_cost'] or 0,
            'profit': batches['total_profit'] or 0,
            'margin': batches['avg_margin'] or 0,
        })
    
    # 3. Profit Margins Trend (Past 7 days)
    margin_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_batches = ProductionBatch.objects.filter(
            daily_production__date=day
        ).aggregate(avg_margin=Avg('gross_margin_percentage'))
        
        margin_trend.append({
            'date': day.strftime('%a'),
            'margin': float(day_batches['avg_margin'] or 0)
        })
    
    # Operational Analytics (5 charts)
    # 4. Inventory Levels (Current)
    inventory_status = InventoryItem.objects.filter(
        is_active=True
    ).values('category__name').annotate(
        total_value=Sum(F('current_stock') * F('cost_per_recipe_unit')),
        low_stock_count=Count('id', filter=Q(low_stock_alert=True))
    )
    
    # 5. Production Trends (Past 7 days)
    production_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_production = DailyProduction.objects.filter(date=day).first()
        
        if day_production:
            total_produced = (
                (day_production.bread_produced or 0) +
                (day_production.kdf_produced or 0) +
                (day_production.scones_produced or 0)
            )
        else:
            total_produced = 0
        
        production_trend.append({
            'date': day.strftime('%a'),
            'units': total_produced
        })
    
    # 6. Sales vs Expected (Past 7 days)
    sales_vs_expected = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_sales = DailySales.objects.filter(date=day).first()
        
        sales_vs_expected.append({
            'date': day.strftime('%a'),
            'expected': float(day_sales.total_expected_revenue if day_sales else 0),
            'actual': float(day_sales.total_actual_revenue if day_sales else 0),
        })
    
    # 7. Deficit Analysis (Past 30 days)
    deficit_data = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).aggregate(
        total_revenue_deficits=Sum('revenue_deficit'),
        total_crate_deficits=Sum('crates_deficit'),
        deficit_count=Count('id', filter=Q(revenue_deficit__gt=0))
    )
    
    # 8. Top Performers (Past 30 days by commission)
    top_performers = SalesReturn.objects.filter(
        return_date__gte=thirty_days_ago
    ).values(
        'dispatch__salesperson__name'
    ).annotate(
        total_sales=Sum('cash_returned'),
        total_commission=Sum('total_commission')
    ).order_by('-total_commission')[:5]
    
    context = {
        'pl_waterfall': pl_waterfall,
        'product_performance': product_performance,
        'margin_trend': margin_trend,
        'inventory_status': list(inventory_status),
        'production_trend': production_trend,
        'sales_vs_expected': sales_vs_expected,
        'deficit_data': deficit_data,
        'top_performers': list(top_performers),
        'today': today,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
def product_performance_view(request):
    """
    Detailed product-level P&L analysis
    Live data from ProductionBatch
    """
    # Date range filter (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days)
    
    products = Product.objects.filter(is_active=True, parent_product__isnull=True)
    product_data = []
    
    for product in products:
        batches = ProductionBatch.objects.filter(
            product=product,
            daily_production__date__gte=start_date
        ).aggregate(
            total_produced=Sum('actual_packets'),
            total_revenue=Sum('expected_revenue'),
            total_cost=Sum('total_cost'),
            total_profit=Sum('gross_profit'),
            avg_margin=Avg('gross_margin_percentage'),
            batch_count=Count('id')
        )
        
        product_data.append({
            'product': product,
            'produced': batches['total_produced'] or 0,
            'revenue': batches['total_revenue'] or 0,
            'cost': batches['total_cost'] or 0,
            'profit': batches['total_profit'] or 0,
            'margin': batches['avg_margin'] or 0,
            'batches': batches['batch_count'] or 0,
        })
    
    context = {
        'product_data': product_data,
        'days': days,
        'start_date': start_date,
    }
    
    return render(request, 'analytics/product_performance.html', context)


@login_required
def inventory_status_view(request):
    """
    Current inventory levels and alerts
    Live data from InventoryItem
    """
    # Get all active inventory items
    items = InventoryItem.objects.filter(is_active=True).select_related('category')
    
    # Categorize by status
    low_stock = items.filter(low_stock_alert=True)
    adequate_stock = items.filter(low_stock_alert=False)
    
    # Calculate total inventory value
    total_value = items.aggregate(
        value=Sum(F('current_stock') * F('cost_per_recipe_unit'))
    )['value'] or 0
    
    context = {
        'items': items,
        'low_stock_items': low_stock,
        'adequate_stock_items': adequate_stock,
        'total_value': total_value,
        'low_stock_count': low_stock.count(),
    }
    
    return render(request, 'analytics/inventory_status.html', context)


@login_required
def sales_trends_view(request):
    """
    Sales trends and patterns
    
    NOTE: Disabled - sales app removed for rebuild
    """
    from django.http import HttpResponse
    return HttpResponse(
        "<h1>Sales Trends Temporarily Disabled</h1>"
        "<p>Sales app has been removed for rebuild.</p>"
        "<p><a href='/'>Return to Home</a></p>"
    )


@login_required
def deficit_analysis_view(request):
    """
    Deficit patterns and problem salespeople
    
    NOTE: Disabled - sales app removed for rebuild
    """
    from django.http import HttpResponse
    return HttpResponse(
        "<h1>Deficit Analysis Temporarily Disabled</h1>"
        "<p>Sales app has been removed for rebuild.</p>"
        "<p><a href='/'>Return to Home</a></p>"
    )
