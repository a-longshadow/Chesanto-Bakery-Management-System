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
from apps.sales.models import Dispatch, SalesReturn, DailySales, Salesperson
from apps.inventory.models import InventoryItem, StockMovement
from apps.products.models import Product


@login_required
def dashboard_view(request):
    """
    Real-time analytics dashboard
    8 charts with live data aggregation
    """
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # Financial Analytics (3 charts)
    # 1. P&L Waterfall (Today)
    daily_sales = DailySales.objects.filter(date=today).first()
    pl_waterfall = {
        'revenue': daily_sales.total_actual_revenue if daily_sales else 0,
        'direct_costs': 0,  # Will calculate from production
        'indirect_costs': 0,
        'profit': 0,
    }
    
    # Get today's production costs
    today_production = DailyProduction.objects.filter(date=today).first()
    if today_production:
        pl_waterfall['indirect_costs'] = (
            today_production.diesel_cost +
            today_production.firewood_cost +
            today_production.electricity_cost +
            today_production.fuel_distribution_cost +
            today_production.other_costs
        )
    
    # Get today's batch costs (direct costs)
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
    deficit_data = DailySales.objects.filter(
        date__gte=thirty_days_ago
    ).aggregate(
        total_revenue_deficits=Sum('total_revenue_deficit'),
        deficit_count=Count('id', filter=Q(total_revenue_deficit__gt=0))
    )
    # Add crates deficit as 0 since we removed that field
    deficit_data['total_crate_deficits'] = 0
    
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
    Live data from SalesReturn
    """
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days)
    
    # Daily sales trend
    daily_sales = DailySales.objects.filter(
        date__gte=start_date
    ).order_by('date')
    
    # Salesperson performance
    salesperson_performance = SalesReturn.objects.filter(
        return_date__gte=start_date
    ).values(
        'dispatch__salesperson__name'
    ).annotate(
        total_sales=Sum('cash_returned'),
        total_commission=Sum('total_commission'),
        return_count=Count('id')
    ).order_by('-total_sales')
    
    # Get deficit data from DailySales
    deficit_data = DailySales.objects.filter(
        date__gte=start_date
    ).aggregate(
        total_deficits=Sum('total_revenue_deficit')
    )['total_deficits'] or 0
    
    context = {
        'daily_sales': daily_sales,
        'salesperson_performance': list(salesperson_performance),
        'total_deficits': deficit_data,
        'days': days,
        'start_date': start_date,
    }
    
    return render(request, 'analytics/sales_trends.html', context)


@login_required
def deficit_analysis_view(request):
    """
    Deficit patterns and problem salespeople
    Live data from SalesReturn
    """
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days)
    
    # All deficits in period
    deficits = DailySales.objects.filter(
        date__gte=start_date,
        total_revenue_deficit__gt=0
    ).order_by('-total_revenue_deficit')
    
    # Salesperson deficit patterns - need to aggregate from SalesReturn with calculated deficits
    salesperson_deficits = SalesReturn.objects.filter(
        return_date__gte=start_date
    ).values(
        'dispatch__salesperson__name'
    ).annotate(
        return_count=Count('id'),
        total_sales=Sum('cash_returned')
    ).order_by('-return_count')
    
    # Calculate deficits for each salesperson by getting their daily sales
    for sp in salesperson_deficits:
        salesperson_name = sp['dispatch__salesperson__name']
        # Get all dispatches for this salesperson in the period
        dispatches = Dispatch.objects.filter(
            salesperson__name=salesperson_name,
            date__gte=start_date
        )
        expected_revenue = sum(d.expected_revenue for d in dispatches)
        
        # Get returns for this salesperson
        returns = SalesReturn.objects.filter(
            dispatch__salesperson__name=salesperson_name,
            return_date__gte=start_date
        )
        actual_revenue = sum(r.cash_returned for r in returns)
        
        sp['total_deficits'] = expected_revenue - actual_revenue
        sp['deficit_count'] = 1 if sp['total_deficits'] > 0 else 0
        sp['total_crate_deficits'] = 0  # Removed field, set to 0
    
    # Filter to only those with deficits
    salesperson_deficits = [sp for sp in salesperson_deficits if sp['total_deficits'] > 0]
    
    # Problem salespeople (those with deficits)
    problem_salespeople = [sp for sp in salesperson_deficits if sp['total_deficits'] > 0]
    
    context = {
        'deficits': deficits,
        'salesperson_deficits': list(salesperson_deficits),
        'problem_salespeople': problem_salespeople,
        'days': days,
        'start_date': start_date,
    }
    
    return render(request, 'analytics/deficit_analysis.html', context)
