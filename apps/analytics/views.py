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

from apps.production.models import ProductionBatch, ProductStock
from apps.sales.models import SalesDispatch, SalesDispatchItem, SalesReturn, SalesReturnItem
from apps.products.models import Product
from apps.inventory.models import StockAlert
from apps.inventory.routing import ITEM_DETAILS_MODELS


@login_required
def dashboard_view(request):
    """Real-time analytics dashboard"""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    month_start = today.replace(day=1)
    
    # Revenue this month (from SalesReturn.total_revenue which stores actual sales)
    monthly_revenue = SalesReturn.objects.filter(
        return_date__gte=month_start,
        return_date__lte=today
    ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
    
    # Units returned this month
    monthly_returns = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=month_start,
        sales_return__return_date__lte=today
    ).aggregate(total=Sum('qty_returned'))['total'] or 0
    
    # Units sold this month
    monthly_sold = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=month_start,
        sales_return__return_date__lte=today
    ).aggregate(total=Sum('qty_sold'))['total'] or 0
    
    # Production this month
    monthly_production = ProductionBatch.objects.filter(
        production_date__gte=month_start,
        production_date__lte=today
    ).aggregate(
        total_batches=Count('id'),
        total_units=Sum('quantity_produced')
    )
    
    # Stock alerts count (recent alerts in last 7 days)
    seven_days_ago = today - timedelta(days=7)
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
    
    # 7-day sales trend (from actual returns/sales)
    sales_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_revenue = SalesReturn.objects.filter(return_date=day).aggregate(
            total=Sum('total_revenue')
        )['total'] or Decimal('0')
        sales_trend.append({'date': day.strftime('%a'), 'revenue': float(day_revenue)})
    
    # 7-day production trend
    production_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_production = ProductionBatch.objects.filter(production_date=day).aggregate(
            total=Sum('quantity_produced')
        )['total'] or 0
        production_trend.append({'date': day.strftime('%a'), 'units': day_production})
    
    # Top 5 products by revenue (from return items)
    top_products = SalesReturnItem.objects.filter(
        sales_return__return_date__gte=thirty_days_ago
    ).values('product__name').annotate(
        revenue=Sum('revenue')
    ).order_by('-revenue')[:5]
    
    context = {
        'monthly_revenue': monthly_revenue,
        'monthly_returns': monthly_returns,
        'monthly_sold': monthly_sold,
        'monthly_batches': monthly_production['total_batches'] or 0,
        'monthly_units': monthly_production['total_units'] or 0,
        'low_stock_count': low_stock_count,
        'inventory_value': total_inventory_value,
        'sales_trend': sales_trend,
        'production_trend': production_trend,
        'top_products': list(top_products),
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
    """Current inventory levels and alerts across all 23 items"""
    
    # Collect data from all 23 item details tables
    items = []
    low_stock_items = []
    total_value = Decimal('0')
    
    for item_id, model_class in ITEM_DETAILS_MODELS.items():
        try:
            item = model_class.objects.first()
            if item:
                item_value = Decimal('0')
                if item.current_stock and item.last_purchase_unit_price:
                    item_value = Decimal(str(item.current_stock)) * item.last_purchase_unit_price
                
                item_data = {
                    'id': item_id,
                    'name': item.name,
                    'current_stock': item.current_stock or 0,
                    'unit_of_measure': item.unit_of_measure,
                    'minimum_stock_level': item.minimum_stock_level or 0,
                    'last_purchase_unit_price': item.last_purchase_unit_price,
                    'value': item_value,
                    'is_low_stock': (item.current_stock or 0) < (item.minimum_stock_level or 0),
                }
                items.append(item_data)
                total_value += item_value
                
                if item_data['is_low_stock']:
                    low_stock_items.append(item_data)
        except Exception:
            pass
    
    # Sort by item_id
    items.sort(key=lambda x: x['id'])
    
    context = {
        'items': items,
        'low_stock_items': low_stock_items,
        'total_value': total_value,
        'low_stock_count': len(low_stock_items),
    }
    return render(request, 'analytics/inventory_status.html', context)


@login_required
def sales_trends_view(request):
    """Sales trends and patterns over 30 days"""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Daily sales from SalesReturn (actual revenue)
    daily_sales = []
    for i in range(30):
        day = today - timedelta(days=29-i)
        day_revenue = SalesReturn.objects.filter(return_date=day).aggregate(
            total=Sum('total_revenue')
        )['total'] or Decimal('0')
        daily_sales.append({'date': day.strftime('%m/%d'), 'revenue': float(day_revenue)})
    
    # Weekly summary
    weekly_totals = []
    for week in range(4):
        week_start = today - timedelta(days=(3-week)*7 + 6)
        week_end = today - timedelta(days=(3-week)*7)
        week_revenue = SalesReturn.objects.filter(
            return_date__gte=week_start,
            return_date__lte=week_end
        ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
        weekly_totals.append({
            'week': f"Week {week+1}",
            'start': week_start.strftime('%m/%d'),
            'end': week_end.strftime('%m/%d'),
            'revenue': week_revenue,
        })
    
    context = {
        'daily_sales': daily_sales,
        'weekly_totals': weekly_totals,
        'today': today,
    }
    return render(request, 'analytics/sales_trends.html', context)


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
