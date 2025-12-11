"""
Reports App Services
====================
Core service functions for generating reports.
All functions are read-only aggregations from foundation apps.

TEMPLATE VARIABLE CONVENTION:
-----------------------------
Templates expect FLAT variables (not nested dicts).
So services should return data like:
    {
        'total_revenue': Decimal('1000'),
        'dispatch_count': 5,
        'products': [...],
    }
NOT:
    {
        'totals': {'total_revenue': Decimal('1000'), 'dispatch_count': 5},
        'products': [...],
    }
"""
from django.db.models import Sum, Avg, Count, F, Q
from django.db.models.functions import Coalesce, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import calendar
from calendar import monthrange

from apps.sales.models import SalesDispatch, SalesReturn, SalesReturnItem
from apps.production.models import ProductionBatch, ProductStock, ProductStockMovement
from apps.products.models import Product
from apps.inventory.models import StockAlert
from apps.inventory.routing import INVENTORY_ITEMS, get_details_model, get_purchases_model
from apps.accounts.models import User


class SalesReportService:
    """
    Service for generating sales report data.
    
    Data Source (per spec):
    - Revenue: SalesReturn.total_revenue (actual sold value)
    - Units: SalesReturn.total_units_sold
    - Commission: SalesReturn.commission_amount (manually entered by Accountant)
    - Products: SalesReturnItem (qty_dispatched, qty_sold, qty_returned, revenue)
    - Crates: SalesDispatch.crates_dispatched → SalesReturn.crates_returned/lost/damaged
    
    Note: "cash_collected" and "deficit" are NOT in current models.
    For now, cash_collected = total_revenue (all sales are assumed collected).
    """
    
    @staticmethod
    def get_daily_summary(target_date: date) -> dict:
        """
        Get sales summary for a specific date.
        Returns FLAT data for template rendering.
        """
        # Get all sales returns for the date
        returns = SalesReturn.objects.filter(return_date=target_date)
        
        # Aggregate totals
        agg = returns.aggregate(
            total_revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            total_units_sold=Coalesce(Sum('total_units_sold'), 0),
            total_commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
            dispatch_count=Count('id'),
            crates_returned=Coalesce(Sum('crates_returned'), 0),
            crates_lost=Coalesce(Sum('crates_lost'), 0),
            crates_damaged=Coalesce(Sum('crates_damaged'), 0),
        )
        
        # Crate tracking from dispatches
        dispatches = SalesDispatch.objects.filter(dispatch_date=target_date)
        dispatch_agg = dispatches.aggregate(
            crates_dispatched=Coalesce(Sum('crates_dispatched'), 0),
        )
        
        # Product breakdown
        products = list(SalesReturnItem.objects.filter(
            sales_return__return_date=target_date
        ).values(
            'product__id',
            'product__name'
        ).annotate(
            qty_dispatched=Sum('qty_dispatched'),
            qty_sold=Sum('qty_sold'),
            qty_returned=Sum('qty_returned'),
            revenue=Sum('revenue'),
        ).order_by('-revenue'))
        
        # Add product_name alias for templates
        for p in products:
            p['product_name'] = p['product__name']
        
        # Salesperson breakdown
        salespeople = list(returns.values(
            salesperson_id=F('dispatch__salesperson__id'),
            salesperson_name=F('dispatch__salesperson__first_name'),
        ).annotate(
            dispatch_count=Count('id'),
            revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            units_sold=Coalesce(Sum('total_units_sold'), 0),
            commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
        ).order_by('-revenue'))
        
        # For templates expecting full name + cash/deficit/returns fields
        for sp in salespeople:
            if sp['salesperson_name']:
                sp['salesperson_name'] = sp['salesperson_name']
            # Add cash_collected = revenue (no separate tracking in current models)
            sp['cash_collected'] = sp['revenue']
            sp['deficit'] = Decimal('0.00')  # Not tracked separately
            sp['returns_value'] = Decimal('0.00')  # Would need per-salesperson returns calc
        
        # Calculate returns value (from returned products)
        returns_value = sum(
            (p['qty_returned'] or 0) * Decimal(str(SalesReturnItem.objects.filter(
                sales_return__return_date=target_date,
                product_id=p['product__id']
            ).first().unit_price if SalesReturnItem.objects.filter(
                sales_return__return_date=target_date,
                product_id=p['product__id']
            ).exists() else 0))
            for p in products
        ) if products else Decimal('0')
        
        # Calculate product quantity totals for template footer
        total_qty_dispatched = sum(p.get('qty_dispatched', 0) or 0 for p in products)
        total_qty_returned = sum(p.get('qty_returned', 0) or 0 for p in products)
        total_qty_sold = sum(p.get('qty_sold', 0) or 0 for p in products)
        
        return {
            'date': target_date,
            # Flattened totals
            'total_revenue': agg['total_revenue'],
            'total_units_sold': agg['total_units_sold'],
            'total_commission': agg['total_commission'],
            'dispatch_count': agg['dispatch_count'],
            # Cash collected = revenue (no separate tracking)
            'cash_collected': agg['total_revenue'],
            'deficit_amount': Decimal('0.00'),  # Not tracked
            'returns_value': returns_value,
            'return_count': len([p for p in products if p.get('qty_returned', 0) > 0]),
            'net_sales': agg['total_revenue'],
            # Product quantity totals for table footer
            'total_qty_dispatched': total_qty_dispatched,
            'total_qty_returned': total_qty_returned,
            'total_qty_sold': total_qty_sold,
            # Crate data
            'crates_dispatched': dispatch_agg['crates_dispatched'],
            'crates_returned': agg['crates_returned'],
            'crates_lost': agg['crates_lost'],
            'crates_damaged': agg['crates_damaged'],
            # Also provide nested for backwards compat
            'totals': agg,
            'crates': {
                'crates_dispatched': dispatch_agg['crates_dispatched'],
                'crates_returned': agg['crates_returned'],
                'crates_lost': agg['crates_lost'],
                'crates_damaged': agg['crates_damaged'],
            },
            # Breakdowns
            'products': products,
            'product_breakdown': products,
            'salespeople': salespeople,
            'salesperson_breakdown': salespeople,
        }
    
    @staticmethod
    def get_period_summary(start_date: date, end_date: date) -> dict:
        """Get sales summary for a date range. Returns FLAT data."""
        returns = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        )
        
        agg = returns.aggregate(
            total_revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            total_units_sold=Coalesce(Sum('total_units_sold'), 0),
            total_commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
            dispatch_count=Count('id'),
            crates_returned=Coalesce(Sum('crates_returned'), 0),
            crates_lost=Coalesce(Sum('crates_lost'), 0),
            crates_damaged=Coalesce(Sum('crates_damaged'), 0),
        )
        
        # Crate tracking from dispatches
        dispatches = SalesDispatch.objects.filter(
            dispatch_date__gte=start_date,
            dispatch_date__lte=end_date
        )
        dispatch_agg = dispatches.aggregate(
            crates_dispatched=Coalesce(Sum('crates_dispatched'), 0),
        )
        
        # Daily breakdown for charts and tables
        daily_data = list(returns.values('return_date').annotate(
            dispatch_count=Count('id'),
            revenue=Sum('total_revenue'),
            units_sold=Sum('total_units_sold'),
        ).order_by('return_date'))
        
        # Add template-friendly field names
        for day in daily_data:
            day['date'] = day['return_date']
            day['cash'] = day['revenue']  # Assume all collected
            day['deficit'] = Decimal('0.00')
            day['returns'] = Decimal('0.00')  # Would need returns calc
        
        # Product breakdown
        products = list(SalesReturnItem.objects.filter(
            sales_return__return_date__gte=start_date,
            sales_return__return_date__lte=end_date
        ).values(
            'product__id',
            'product__name'
        ).annotate(
            qty_dispatched=Sum('qty_dispatched'),
            qty_sold=Sum('qty_sold'),
            qty_returned=Sum('qty_returned'),
            revenue=Sum('revenue'),
        ).order_by('-revenue'))
        
        for p in products:
            p['product_name'] = p['product__name']
        
        # Salesperson breakdown
        salespeople = list(returns.values(
            salesperson_id=F('dispatch__salesperson__id'),
            first_name=F('dispatch__salesperson__first_name'),
            last_name=F('dispatch__salesperson__last_name'),
        ).annotate(
            dispatch_count=Count('id'),
            revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            units_sold=Coalesce(Sum('total_units_sold'), 0),
            commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
            crates_lost=Coalesce(Sum('crates_lost'), 0),
            crates_damaged=Coalesce(Sum('crates_damaged'), 0),
        ).order_by('-revenue'))
        
        for sp in salespeople:
            sp['salesperson_name'] = f"{sp['first_name'] or ''} {sp['last_name'] or ''}".strip()
            sp['cash_collected'] = sp['revenue']  # Assume all collected
            sp['deficit'] = Decimal('0.00')
            sp['returns_value'] = Decimal('0.00')  # Would need more complex calc
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            # Flattened totals
            'total_revenue': agg['total_revenue'],
            'total_units_sold': agg['total_units_sold'],
            'total_commission': agg['total_commission'],
            'dispatch_count': agg['dispatch_count'],
            'cash_collected': agg['total_revenue'],
            'deficit_amount': Decimal('0.00'),
            'returns_value': Decimal('0.00'),
            'return_count': 0,
            'net_sales': agg['total_revenue'],
            # Crate data
            'crates_dispatched': dispatch_agg['crates_dispatched'],
            'crates_returned': agg['crates_returned'],
            'crates_lost': agg['crates_lost'],
            'crates_damaged': agg['crates_damaged'],
            # Nested for backwards compat
            'totals': agg,
            'crates': {
                'crates_dispatched': dispatch_agg['crates_dispatched'],
                **{k: agg[k] for k in ['crates_returned', 'crates_lost', 'crates_damaged']}
            },
            # Breakdowns
            'daily_data': daily_data,
            'daily_breakdown': daily_data,  # Template-friendly alias
            'products': products,
            'product_breakdown': products,
            'salespeople': salespeople,
            'salesperson_breakdown': salespeople,
        }
    
    @staticmethod
    def get_weekly_summary(week_start: date = None) -> dict:
        """
        Get sales summary for a week.
        If week_start is None, uses current week.
        """
        if week_start is None:
            today = date.today()
            # Go back to Monday
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        result = SalesReportService.get_period_summary(week_start, week_end)
        result['week_start'] = week_start
        result['week_end'] = week_end
        return result
    
    @staticmethod
    def get_monthly_summary(year: int = None, month: int = None) -> dict:
        """
        Get sales summary for a month with weekly breakdown.
        If year/month is None, uses current month.
        """
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        result = SalesReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        result['month'] = month
        
        # Weekly breakdown for monthly report
        weekly_breakdown = []
        current_week_start = start_date
        while current_week_start <= end_date:
            # Find end of this week (Sunday) or end of month, whichever is first
            days_to_sunday = 6 - current_week_start.weekday()
            current_week_end = min(current_week_start + timedelta(days=days_to_sunday), end_date)
            
            # Get data for this week
            week_returns = SalesReturn.objects.filter(
                return_date__gte=current_week_start,
                return_date__lte=current_week_end
            )
            week_agg = week_returns.aggregate(
                revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
                dispatch_count=Count('id'),
            )
            
            weekly_breakdown.append({
                'start_date': current_week_start,
                'end_date': current_week_end,
                'dispatch_count': week_agg['dispatch_count'],
                'revenue': week_agg['revenue'],
                'cash': week_agg['revenue'],  # Alias
                'deficit': Decimal('0.00'),
                'returns': Decimal('0.00'),
            })
            
            # Move to next week
            current_week_start = current_week_end + timedelta(days=1)
        
        result['weekly_breakdown'] = weekly_breakdown
        return result
    
    @staticmethod
    def get_annual_summary(year: int = None) -> dict:
        """
        Get sales summary for a year with monthly breakdown.
        If year is None, uses current year.
        """
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        result = SalesReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        
        # Monthly breakdown for annual report using TruncMonth
        monthly_data = list(SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).annotate(
            month_date=TruncMonth('return_date')
        ).values('month_date').annotate(
            revenue=Sum('total_revenue'),
            units_sold=Sum('total_units_sold'),
            dispatch_count=Count('id'),
            commission=Sum('commission_amount'),
        ).order_by('month_date'))
        
        # Add template-friendly fields
        MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        for m in monthly_data:
            m['month'] = m['month_date'].month
            m['month_name'] = MONTH_NAMES[m['month']]
            m['cash'] = m['revenue']  # Assume all collected
            m['deficit'] = Decimal('0.00')
            m['returns'] = Decimal('0.00')
        
        result['monthly_data'] = monthly_data
        result['monthly_breakdown'] = monthly_data  # Alias
        return result
    
    @staticmethod
    def get_salesperson_summary(start_date: date, end_date: date) -> list:
        """Get per-salesperson performance for a date range."""
        return list(
            SalesReturn.objects.filter(
                return_date__gte=start_date,
                return_date__lte=end_date
            ).values(
                'dispatch__salesperson__id',
                'dispatch__salesperson__first_name',
                'dispatch__salesperson__last_name',
            ).annotate(
                dispatch_count=Count('id'),
                total_units_sold=Sum('total_units_sold'),
                total_revenue=Sum('total_revenue'),
                total_commission=Sum('commission_amount'),
                crates_lost=Sum('crates_lost'),
                crates_damaged=Sum('crates_damaged'),
            ).order_by('-total_revenue')
        )
    
    @staticmethod
    def get_salesperson_performance(start_date: date, end_date: date) -> dict:
        """
        Get detailed salesperson performance report.
        Includes rankings, averages, and individual metrics.
        """
        # Get all salespeople from returns in the period
        salesperson_data = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).values(
            salesperson_id=F('dispatch__salesperson__id'),
            first_name=F('dispatch__salesperson__first_name'),
            last_name=F('dispatch__salesperson__last_name'),
            sales_target=F('dispatch__salesperson__sales_target'),
            commission_rate=F('dispatch__salesperson__commission_rate'),
        ).annotate(
            dispatch_count=Count('id'),
            total_units_sold=Coalesce(Sum('total_units_sold'), 0),
            total_revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            total_commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
            crates_dispatched=Coalesce(Sum('dispatch__crates_dispatched'), 0),
            crates_returned=Coalesce(Sum('crates_returned'), 0),
            crates_lost=Coalesce(Sum('crates_lost'), 0),
            crates_damaged=Coalesce(Sum('crates_damaged'), 0),
        ).order_by('-total_revenue')
        
        salespeople = list(salesperson_data)
        
        # Calculate additional metrics
        total_revenue = sum(s['total_revenue'] or Decimal('0') for s in salespeople)
        total_commission = sum(s['total_commission'] or Decimal('0') for s in salespeople)
        total_dispatches = sum(s['dispatch_count'] for s in salespeople)
        
        for idx, sp in enumerate(salespeople, 1):
            sp['rank'] = idx
            sp['full_name'] = f"{sp['first_name']} {sp['last_name']}"
            sp['avg_revenue_per_dispatch'] = (
                sp['total_revenue'] / sp['dispatch_count'] 
                if sp['dispatch_count'] > 0 else Decimal('0')
            )
            # Sell-through rate based on revenue vs what could have been earned
            sp['sell_through_rate'] = 0  # Simplified - could calculate from dispatch items if needed
            sp['crate_deficit'] = (
                (sp.get('crates_dispatched', 0) or 0) - 
                (sp.get('crates_returned', 0) or 0) - 
                (sp.get('crates_lost', 0) or 0) - 
                (sp.get('crates_damaged', 0) or 0)
            )
            sp['revenue_share'] = (
                (sp['total_revenue'] / total_revenue * 100) 
                if total_revenue > 0 else Decimal('0')
            )
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'salespeople': salespeople,
            'summary': {
                'total_salespeople': len(salespeople),
                'total_dispatches': total_dispatches,
                'total_revenue': total_revenue,
                'total_commission': total_commission,
                'avg_revenue_per_salesperson': (
                    total_revenue / len(salespeople) if salespeople else Decimal('0')
                ),
            }
        }
    
    @staticmethod
    def get_commission_report(year: int, month: int) -> dict:
        """
        Get commission report for a specific month.
        Shows actual commission amounts entered by Accountant on SalesReturn records.
        """
        from calendar import monthrange
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        # Get salesperson data with actual commission amounts from database
        commission_data = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).values(
            salesperson_id=F('dispatch__salesperson__id'),
            first_name=F('dispatch__salesperson__first_name'),
            last_name=F('dispatch__salesperson__last_name'),
        ).annotate(
            dispatch_count=Count('id'),
            total_revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            total_commission=Coalesce(Sum('commission_amount'), Decimal('0.00')),
        ).order_by('-total_revenue')
        
        commissions = []
        total_sales = Decimal('0')
        total_commission = Decimal('0')
        
        for sp in commission_data:
            revenue = sp['total_revenue'] or Decimal('0')
            commission = sp['total_commission'] or Decimal('0')
            
            commissions.append({
                'salesperson_id': sp['salesperson_id'],
                'full_name': f"{sp['first_name'] or ''} {sp['last_name'] or ''}".strip(),
                'dispatch_count': sp['dispatch_count'],
                'total_revenue': revenue,
                'commission_earned': commission,
            })
            
            total_sales += revenue
            total_commission += commission
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'commissions': commissions,
            'summary': {
                'total_salespeople': len(commissions),
                'total_sales': total_sales,
                'total_commission': total_commission,
                'salespeople_with_commission': sum(1 for c in commissions if c['commission_earned'] > 0),
            }
        }


class ProductionReportService:
    """
    Service for generating production report data.
    
    Data Source (per spec):
    - Batches: ProductionBatch (batch_number, product, quantity_produced, total_ingredient_cost)
    - Yield: ProductionBatch.quantity_produced vs expected_yield
    - Ingredient Usage: BatchIngredientDeduction (quantity_deducted, line_cost)
    """
    
    @staticmethod
    def get_daily_summary(target_date: date) -> dict:
        """Get production summary for a specific date. Returns FLAT data."""
        batches_qs = ProductionBatch.objects.filter(production_date=target_date).select_related('product')
        
        agg = batches_qs.aggregate(
            total_units=Coalesce(Sum('quantity_produced'), 0),
            total_cost=Coalesce(Sum('total_ingredient_cost'), Decimal('0.00')),
            batch_count=Count('id'),
            expected_total=Coalesce(Sum('expected_yield'), 0),
        )
        
        # Calculate yield variance
        if agg['expected_total'] > 0:
            yield_variance = ((agg['total_units'] - agg['expected_total']) / agg['expected_total']) * 100
        else:
            yield_variance = Decimal('0')
        
        # Product breakdown with aliases
        products = list(batches_qs.values(
            'product__id',
            'product__name'
        ).annotate(
            units_produced=Sum('quantity_produced'),
            batch_count=Count('id'),
            production_cost=Sum('total_ingredient_cost'),
        ).order_by('-units_produced'))
        
        product_breakdown = []
        for p in products:
            product_breakdown.append({
                'product_name': p['product__name'],
                'batch_count': p['batch_count'],
                'quantity': p['units_produced'],
                'cost': p['production_cost'],
                'units_produced': p['units_produced'],
                'production_cost': p['production_cost'],
            })
        
        # Build batches list for template (Batch Details table)
        batches_list = []
        for batch in batches_qs.order_by('-created_at'):
            # Determine status based on yield variance
            variance = batch.quantity_produced - batch.expected_yield
            if variance >= 0:
                status = 'Completed'
                status_color = 'success'
            else:
                status = 'Under-yield'
                status_color = 'warning'
            
            batches_list.append({
                'batch_number': batch.batch_number,
                'product_name': batch.product.name,
                'quantity': batch.quantity_produced,
                'expected_yield': batch.expected_yield,
                'status': status,
                'status_color': status_color,
                'notes': batch.notes or '',
                'cost': batch.total_ingredient_cost,
            })
        
        return {
            'date': target_date,
            # Flattened data
            'total_units': agg['total_units'],
            'total_cost': agg['total_cost'],
            'batch_count': agg['batch_count'],
            'yield_variance': yield_variance,
            # Aliases for templates
            'total_quantity': agg['total_units'],
            'product_count': len(products),
            # Nested for backwards compat
            'totals': agg,
            # Breakdowns
            'products': product_breakdown,
            'product_breakdown': product_breakdown,
            # Batch details list
            'batches': batches_list,
        }
    
    @staticmethod
    def get_period_summary(start_date: date, end_date: date) -> dict:
        """Get production summary for a date range. Returns FLAT data."""
        batches = ProductionBatch.objects.filter(
            production_date__gte=start_date,
            production_date__lte=end_date
        )
        
        agg = batches.aggregate(
            total_units=Coalesce(Sum('quantity_produced'), 0),
            total_cost=Coalesce(Sum('total_ingredient_cost'), Decimal('0.00')),
            batch_count=Count('id'),
            expected_total=Coalesce(Sum('expected_yield'), 0),
        )
        
        if agg['expected_total'] > 0:
            yield_variance = ((agg['total_units'] - agg['expected_total']) / agg['expected_total']) * 100
        else:
            yield_variance = Decimal('0')
        
        # Daily breakdown - with aliases for templates
        daily_data = list(batches.values('production_date').annotate(
            units=Sum('quantity_produced'),
            batches=Count('id'),
            cost=Sum('total_ingredient_cost'),
        ).order_by('production_date'))
        
        # Add aliases for templates (day.date, day.batch_count, day.quantity)
        daily_breakdown = []
        for d in daily_data:
            daily_breakdown.append({
                'date': d['production_date'],
                'batch_count': d['batches'],
                'quantity': d['units'],
                'cost': d['cost'],
            })
        
        # Product breakdown
        products = list(batches.values(
            'product__id',
            'product__name'
        ).annotate(
            units_produced=Sum('quantity_produced'),
            batch_count=Count('id'),
            production_cost=Sum('total_ingredient_cost'),
        ).order_by('-units_produced'))
        
        # Add aliases for templates
        product_breakdown = []
        for p in products:
            product_breakdown.append({
                'product_name': p['product__name'],
                'batch_count': p['batch_count'],
                'quantity': p['units_produced'],
                'cost': p['production_cost'],
                # Original fields for compatibility
                'units_produced': p['units_produced'],
                'production_cost': p['production_cost'],
            })
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            # Flattened
            'total_units': agg['total_units'],
            'total_cost': agg['total_cost'],
            'batch_count': agg['batch_count'],
            'yield_variance': yield_variance,
            # Aliases for templates
            'total_quantity': agg['total_units'],
            'product_count': len(products),
            # Nested
            'totals': agg,
            # Breakdowns
            'daily_data': daily_data,
            'daily_breakdown': daily_breakdown,
            'products': product_breakdown,
            'product_breakdown': product_breakdown,
        }
    
    @staticmethod
    def get_weekly_summary(week_start: date = None) -> dict:
        """Get production summary for a week."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        result = ProductionReportService.get_period_summary(week_start, week_end)
        result['week_start'] = week_start
        result['week_end'] = week_end
        return result
    
    @staticmethod
    def get_monthly_summary(year: int = None, month: int = None) -> dict:
        """Get production summary for a month with weekly breakdown."""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        result = ProductionReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        result['month'] = month
        
        # Add weekly breakdown for templates
        weekly_breakdown = []
        batches = ProductionBatch.objects.filter(
            production_date__gte=start_date,
            production_date__lte=end_date
        )
        
        # Group by week (ISO week)
        week_data = batches.annotate(
            week=TruncWeek('production_date')
        ).values('week').annotate(
            units=Sum('quantity_produced'),
            batches=Count('id'),
            cost=Sum('total_ingredient_cost'),
        ).order_by('week')
        
        for w in week_data:
            week_start = w['week']
            week_end = week_start + timedelta(days=6)
            weekly_breakdown.append({
                'start_date': week_start,
                'end_date': week_end,
                'batch_count': w['batches'],
                'quantity': w['units'],
                'cost': w['cost'],
            })
        
        result['weekly_breakdown'] = weekly_breakdown
        return result
    
    @staticmethod
    def get_annual_summary(year: int = None) -> dict:
        """Get production summary for a year with monthly breakdown."""
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        result = ProductionReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        
        # Monthly breakdown with aliases for templates
        monthly_data = list(ProductionBatch.objects.filter(
            production_date__gte=start_date,
            production_date__lte=end_date
        ).annotate(
            month_trunc=TruncMonth('production_date')
        ).values('month_trunc').annotate(
            units=Sum('quantity_produced'),
            batches=Count('id'),
            cost=Sum('total_ingredient_cost'),
        ).order_by('month_trunc'))
        
        # Format for templates
        monthly_breakdown = []
        for m in monthly_data:
            monthly_breakdown.append({
                'month': m['month_trunc'].month,
                'month_name': m['month_trunc'].strftime('%B'),
                'batch_count': m['batches'],
                'quantity': m['units'],
                'cost': m['cost'],
            })
        
        result['monthly_data'] = monthly_breakdown
        result['monthly_breakdown'] = monthly_breakdown
        
        # Top products for annual view
        total_units = result['total_units'] or 1
        top_products = []
        for p in result['product_breakdown'][:10]:  # Top 10
            top_products.append({
                'product_name': p['product_name'],
                'quantity': p['quantity'],
                'cost': p['cost'],
                'percentage': (p['quantity'] / total_units * 100) if total_units > 0 else 0,
            })
        result['top_products'] = top_products
        
        return result


class InventoryReportService:
    """
    Service for generating inventory report data.
    
    Data Source (per spec):
    - Current Stock: ItemXXDetails.current_stock, minimum_stock_level
    - Purchases: ItemXXPurchases (quantity_purchased, unit_price, total_cost)
    - Usage: BatchIngredientDeduction for items 1-15, ItemXXOutputs for items 16-23
    """
    
    @staticmethod
    def get_current_stock_levels() -> list:
        """Get current stock levels for all 23 items."""
        stock_data = []
        
        # INVENTORY_ITEMS is a list of tuples: (item_id, name, is_active, unit)
        for item_tuple in INVENTORY_ITEMS:
            item_id = item_tuple[0]
            item_name = item_tuple[1]
            item_unit = item_tuple[3] if len(item_tuple) > 3 else 'units'
            DetailsModel = get_details_model(item_id)
            details = DetailsModel.objects.first()
            
            if details:
                # Only mark as low stock if:
                # 1. minimum_stock_level > 0 AND current_stock <= minimum_stock_level, OR
                # 2. current_stock < minimum_stock_level (strictly less than)
                # This prevents items with min=0 and stock=0 from being flagged as low
                is_low = (details.minimum_stock_level > 0 and 
                         details.current_stock <= details.minimum_stock_level)
                
                stock_data.append({
                    'item_id': item_id,
                    'name': item_name,
                    'unit': item_unit,
                    'current_stock': details.current_stock,
                    'minimum_stock': details.minimum_stock_level,
                    'last_price': details.last_purchase_unit_price,
                    'is_low': is_low,
                    'value': details.current_stock * details.last_purchase_unit_price,
                })
        
        return stock_data
    
    @staticmethod
    def get_purchase_summary(start_date: date, end_date: date) -> list:
        """Get purchase summary for all items in date range."""
        purchase_data = []
        
        for item_tuple in INVENTORY_ITEMS:
            item_id = item_tuple[0]
            item_name = item_tuple[1]
            item_unit = item_tuple[3] if len(item_tuple) > 3 else 'units'
            PurchasesModel = get_purchases_model(item_id)
            
            purchases = PurchasesModel.objects.filter(
                purchase_date__gte=start_date,
                purchase_date__lte=end_date
            )
            
            totals = purchases.aggregate(
                total_qty=Coalesce(Sum('quantity_purchased'), Decimal('0.00')),
                total_cost=Coalesce(Sum('total_cost'), Decimal('0.00')),
                purchase_count=Count('id'),
                avg_price=Avg('unit_price'),
            )
            
            if totals['purchase_count'] > 0:
                purchase_data.append({
                    'item_id': item_id,
                    'name': item_name,
                    'unit': item_unit,
                    **totals,
                })
        
        return purchase_data
    
    @staticmethod
    def get_daily_summary(target_date: date) -> dict:
        """Get inventory summary for a specific date."""
        stock_levels = InventoryReportService.get_current_stock_levels()
        purchases = InventoryReportService.get_purchase_summary(target_date, target_date)
        
        # Low stock items
        low_stock = [s for s in stock_levels if s['is_low']]
        
        # Calculate totals
        total_value = sum(s['value'] for s in stock_levels)
        total_items = len(stock_levels)
        total_purchases = sum(p['total_cost'] for p in purchases)
        
        # Format purchases for templates with detailed categories
        formatted_purchases = []
        for p in purchases:
            formatted_purchases.append({
                'item_name': p['name'],
                'category': InventoryReportService.get_item_category(p['item_id']),
                'quantity': p['total_qty'],
                'unit': p['unit'],
                'amount': p['total_cost'],
                # Original fields
                **p
            })
        
        # Use detailed category breakdown
        category_breakdown = InventoryReportService.get_detailed_category_breakdown(purchases)
        
        purchase_count = sum(p['purchase_count'] for p in purchases)
        
        return {
            'date': target_date,
            'total_value': total_value,
            'total_items': total_items,
            'low_stock_count': len(low_stock),
            'total_purchases': total_purchases,
            'stock_levels': stock_levels,
            'purchases': formatted_purchases,
            'low_stock_items': low_stock,
            # Aliases for templates
            'purchase_count': purchase_count,
            'total_purchased': total_purchases,
            'items_received': len([p for p in purchases if p['total_qty'] > 0]),
            'category_count': len(category_breakdown),
            'category_breakdown': category_breakdown,
        }
    
    @staticmethod
    def get_period_summary(start_date: date, end_date: date) -> dict:
        """Get inventory summary for a date range."""
        stock_levels = InventoryReportService.get_current_stock_levels()
        purchases = InventoryReportService.get_purchase_summary(start_date, end_date)
        
        low_stock = [s for s in stock_levels if s['is_low']]
        total_value = sum(s['value'] for s in stock_levels)
        total_purchases = sum(p['total_cost'] for p in purchases)
        
        # Format purchases for templates with detailed categories
        formatted_purchases = []
        for p in purchases:
            formatted_purchases.append({
                'item_name': p['name'],
                'category': InventoryReportService.get_item_category(p['item_id']),
                'quantity': p['total_qty'],
                'unit': p['unit'],
                'amount': p['total_cost'],
                **p
            })
        
        # Use detailed category breakdown
        category_breakdown = InventoryReportService.get_detailed_category_breakdown(purchases)
        
        purchase_count = sum(p['purchase_count'] for p in purchases)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_value': total_value,
            'total_items': len(stock_levels),
            'low_stock_count': len(low_stock),
            'total_purchases': total_purchases,
            'stock_levels': stock_levels,
            'purchases': formatted_purchases,
            'low_stock_items': low_stock,
            # Aliases for templates
            'purchase_count': purchase_count,
            'total_purchased': total_purchases,
            'items_received': len([p for p in purchases if p['total_qty'] > 0]),
            'category_count': len(category_breakdown),
            'category_breakdown': category_breakdown,
        }
    
    @staticmethod
    def get_weekly_summary(week_start: date = None) -> dict:
        """Get inventory summary for a week with daily breakdown."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        result = InventoryReportService.get_period_summary(week_start, week_end)
        result['week_start'] = week_start
        result['week_end'] = week_end
        
        # Generate daily breakdown for the week
        daily_breakdown = []
        current_date = week_start
        while current_date <= week_end:
            day_purchases = InventoryReportService.get_purchase_summary(current_date, current_date)
            day_purchase_count = sum(p['purchase_count'] for p in day_purchases)
            day_amount = sum(p['total_cost'] for p in day_purchases)
            daily_breakdown.append({
                'date': current_date,
                'purchase_count': day_purchase_count,
                'amount': day_amount,
            })
            current_date += timedelta(days=1)
        
        result['daily_breakdown'] = daily_breakdown
        return result
    
    @staticmethod
    def get_monthly_summary(year: int = None, month: int = None) -> dict:
        """Get inventory summary for a month with weekly breakdown."""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        result = InventoryReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        result['month'] = month
        
        # Generate weekly breakdown for the month
        weekly_breakdown = []
        current_week_start = start_date
        
        while current_week_start <= end_date:
            # Week ends on Sunday or end of month, whichever comes first
            current_week_end = current_week_start + timedelta(days=6 - current_week_start.weekday())
            if current_week_end > end_date:
                current_week_end = end_date
            
            week_purchases = InventoryReportService.get_purchase_summary(current_week_start, current_week_end)
            week_purchase_count = sum(p['purchase_count'] for p in week_purchases)
            week_amount = sum(p['total_cost'] for p in week_purchases)
            weekly_breakdown.append({
                'start_date': current_week_start,
                'end_date': current_week_end,
                'purchase_count': week_purchase_count,
                'amount': week_amount,
            })
            
            # Move to next week (Monday after current_week_end)
            current_week_start = current_week_end + timedelta(days=1)
        
        result['weekly_breakdown'] = weekly_breakdown
        return result
    
    @staticmethod
    def get_annual_summary(year: int = None) -> dict:
        """Get inventory summary for a year."""
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        result = InventoryReportService.get_period_summary(start_date, end_date)
        result['year'] = year
        
        # Generate monthly breakdown for the year
        monthly_breakdown = []
        for m in range(1, 13):
            month_start = date(year, m, 1)
            month_end = date(year, m, monthrange(year, m)[1])
            
            # Only include months up to today
            if month_start > date.today():
                break
            
            month_purchases = InventoryReportService.get_purchase_summary(month_start, month_end)
            month_purchase_count = sum(p['purchase_count'] for p in month_purchases)
            month_amount = sum(p['total_cost'] for p in month_purchases)
            monthly_breakdown.append({
                'month': m,
                'month_name': calendar.month_name[m],
                'purchase_count': month_purchase_count,
                'amount': month_amount,
            })
        
        result['monthly_breakdown'] = monthly_breakdown
        return result
    
    @staticmethod
    def get_item_category(item_id: int) -> str:
        """Get detailed category for an inventory item."""
        # Define more specific categories for each item
        ITEM_CATEGORIES = {
            # Baking Flours
            1: 'Baking Flours',
            2: 'Baking Flours',
            # Sweeteners & Additives
            3: 'Sweeteners & Additives',
            4: 'Sweeteners & Additives',
            5: 'Sweeteners & Additives',
            6: 'Sweeteners & Additives',
            # Leavening Agents
            7: 'Leavening Agents',
            8: 'Leavening Agents',
            9: 'Leavening Agents',
            # Fats & Oils
            10: 'Fats & Oils',
            13: 'Fats & Oils',
            14: 'Fats & Oils',
            # Dairy & Eggs
            11: 'Dairy & Eggs',
            12: 'Dairy & Eggs',
            # Food Additives
            15: 'Food Additives',
            # Packaging
            16: 'Packaging',
            17: 'Packaging',
            23: 'Packaging',
            # Energy & Fuel
            18: 'Energy & Fuel',
            19: 'Energy & Fuel',
            20: 'Energy & Fuel',
            21: 'Energy & Fuel',
            22: 'Energy & Fuel',
        }
        return ITEM_CATEGORIES.get(item_id, 'Other')
    
    @staticmethod
    def get_individual_purchases(start_date: date, end_date: date) -> list:
        """Get individual purchase records for all items in date range."""
        purchases = []
        
        for item_tuple in INVENTORY_ITEMS:
            item_id = item_tuple[0]
            item_name = item_tuple[1]
            item_unit = item_tuple[3] if len(item_tuple) > 3 else 'units'
            PurchasesModel = get_purchases_model(item_id)
            
            item_purchases = PurchasesModel.objects.filter(
                purchase_date__gte=start_date,
                purchase_date__lte=end_date
            ).order_by('-purchase_date')
            
            for p in item_purchases:
                purchases.append({
                    'date': p.purchase_date,
                    'item_id': item_id,
                    'item_name': item_name,
                    'category': InventoryReportService.get_item_category(item_id),
                    'quantity': p.quantity_purchased,
                    'unit': item_unit,
                    'unit_cost': p.unit_price,
                    'total': p.total_cost,
                    'supplier': getattr(p, 'supplier_name', None) or '-',
                })
        
        # Sort all purchases by date descending
        purchases.sort(key=lambda x: x['date'], reverse=True)
        return purchases
    
    @staticmethod
    def get_valuation_report() -> dict:
        """Get inventory valuation report data for PDF."""
        stock_levels = InventoryReportService.get_current_stock_levels()
        
        # Format for PDF template (expects 'items' key)
        items = []
        for s in stock_levels:
            items.append({
                'name': s['name'],
                'category': InventoryReportService.get_item_category(s['item_id']),
                'quantity': s['current_stock'],
                'unit': s['unit'],
                'unit_cost': s['last_price'],
                'total_value': s['value'],
                'min_level': s['minimum_stock'],
                'is_low_stock': s['is_low'],
            })
        
        total_value = sum(s['value'] for s in stock_levels)
        low_stock = [s for s in stock_levels if s['is_low']]
        out_of_stock = [s for s in stock_levels if s['current_stock'] <= 0]
        
        # Group by category for summary
        category_totals = {}
        for item in items:
            cat = item['category']
            if cat not in category_totals:
                category_totals[cat] = {'name': cat, 'item_count': 0, 'value': Decimal('0.00')}
            category_totals[cat]['item_count'] += 1
            category_totals[cat]['value'] += item['total_value']
        
        category_summary = []
        for cat_name, cat_data in sorted(category_totals.items()):
            cat_data['percentage'] = (cat_data['value'] / total_value * 100) if total_value > 0 else 0
            category_summary.append(cat_data)
        
        return {
            'items': items,
            'total_value': total_value,
            'total_items': len(stock_levels),
            'low_stock_count': len(low_stock),
            'out_of_stock_count': len(out_of_stock),
            'category_summary': category_summary,
        }
    
    @staticmethod
    def get_purchase_history(start_date: date, end_date: date) -> dict:
        """Get purchase history report data for PDF."""
        # Get individual purchases for detailed table
        purchases = InventoryReportService.get_individual_purchases(start_date, end_date)
        
        # Get aggregate by item
        item_summary = InventoryReportService.get_purchase_summary(start_date, end_date)
        by_item = []
        for p in item_summary:
            by_item.append({
                'name': p['name'],
                'unit': p['unit'],
                'purchase_count': p['purchase_count'],
                'total_quantity': p['total_qty'],
                'total_spent': p['total_cost'],
            })
        
        total_spent = sum(p['total'] for p in purchases)
        total_purchases = len(purchases)
        avg_per_purchase = (total_spent / total_purchases) if total_purchases > 0 else Decimal('0.00')
        unique_items = len(set(p['item_name'] for p in purchases))
        
        return {
            'purchases': purchases,
            'by_item': by_item,
            'total_spent': total_spent,
            'total_purchases': total_purchases,
            'avg_per_purchase': avg_per_purchase,
            'unique_items': unique_items,
        }
    
    @staticmethod
    def get_detailed_category_breakdown(purchases: list) -> list:
        """Get category breakdown with detailed categories."""
        category_totals = {}
        
        for p in purchases:
            item_id = p.get('item_id', 0)
            cat = InventoryReportService.get_item_category(item_id)
            
            if cat not in category_totals:
                category_totals[cat] = {
                    'category_name': cat,
                    'purchase_count': 0,
                    'amount': Decimal('0.00'),
                }
            category_totals[cat]['purchase_count'] += p.get('purchase_count', 1)
            category_totals[cat]['amount'] += p.get('total_cost', p.get('amount', Decimal('0.00')))
        
        # Sort by amount descending
        return sorted(category_totals.values(), key=lambda x: x['amount'], reverse=True)


class FinancialReportService:
    """
    Service for generating P&L and financial reports.
    
    Data Source (per spec):
    - Revenue: SalesReturn.total_revenue
    - COGS: ProductionBatch.total_ingredient_cost
    - Commissions: SalesReturn.commission_amount
    - Payroll: MonthlyPayroll, CasualLabor
    - Other Expenses: MiscExpenseRecord
    """
    
    @staticmethod
    def get_daily_pnl(target_date: date) -> dict:
        """Get daily Profit & Loss summary."""
        # Revenue from sales
        sales_data = SalesReturn.objects.filter(
            return_date=target_date
        ).aggregate(
            revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            commissions=Coalesce(Sum('commission_amount'), Decimal('0.00')),
        )
        
        # COGS from production
        production_data = ProductionBatch.objects.filter(
            production_date=target_date
        ).aggregate(
            production_cost=Coalesce(Sum('total_ingredient_cost'), Decimal('0.00')),
        )
        
        revenue = sales_data['revenue']
        cogs = production_data['production_cost']
        commissions = sales_data['commissions']
        
        gross_profit = revenue - cogs
        net_profit = gross_profit - commissions
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0.00')
        
        # Total expenses = COGS + commissions
        total_expenses = cogs + commissions
        
        # Build breakdowns for templates
        revenue_breakdown = []
        if revenue > 0:
            revenue_breakdown.append({'source': 'Sales Revenue', 'amount': revenue})
        
        expense_breakdown = []
        if cogs > 0:
            expense_breakdown.append({'category': 'Cost of Goods Sold (COGS)', 'amount': cogs})
        if commissions > 0:
            expense_breakdown.append({'category': 'Sales Commissions', 'amount': commissions})
        
        return {
            'date': target_date,
            'revenue': revenue,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'gross_margin': gross_margin,
            'commissions': commissions,
            'net_profit': net_profit,
            # Aliases for templates
            'expenses': total_expenses,
            'profit': net_profit,
            'margin': gross_margin,
            'revenue_breakdown': revenue_breakdown,
            'expense_breakdown': expense_breakdown,
        }
    
    @staticmethod
    def get_period_pnl(start_date: date, end_date: date) -> dict:
        """Get P&L for a date range."""
        # Revenue
        sales_data = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).aggregate(
            revenue=Coalesce(Sum('total_revenue'), Decimal('0.00')),
            commissions=Coalesce(Sum('commission_amount'), Decimal('0.00')),
        )
        
        # COGS
        production_data = ProductionBatch.objects.filter(
            production_date__gte=start_date,
            production_date__lte=end_date
        ).aggregate(
            production_cost=Coalesce(Sum('total_ingredient_cost'), Decimal('0.00')),
        )
        
        revenue = sales_data['revenue']
        cogs = production_data['production_cost']
        commissions = sales_data['commissions']
        
        gross_profit = revenue - cogs
        net_profit = gross_profit - commissions
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0.00')
        
        # Total expenses = COGS + commissions
        total_expenses = cogs + commissions
        
        # Build breakdowns for templates
        revenue_breakdown = []
        if revenue > 0:
            revenue_breakdown.append({'source': 'Sales Revenue', 'amount': revenue})
        
        expense_breakdown = []
        if cogs > 0:
            expense_breakdown.append({'category': 'Cost of Goods Sold (COGS)', 'amount': cogs})
        if commissions > 0:
            expense_breakdown.append({'category': 'Sales Commissions', 'amount': commissions})
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'revenue': revenue,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'gross_margin': gross_margin,
            'commissions': commissions,
            'net_profit': net_profit,
            # Aliases for templates
            'expenses': total_expenses,
            'profit': net_profit,
            'margin': gross_margin,
            'revenue_breakdown': revenue_breakdown,
            'expense_breakdown': expense_breakdown,
        }
    
    @staticmethod
    def get_weekly_pnl(week_start: date = None) -> dict:
        """Get weekly P&L with daily breakdown."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        result = FinancialReportService.get_period_pnl(week_start, week_end)
        result['week_start'] = week_start
        result['week_end'] = week_end
        
        # Generate daily breakdown for the week
        daily_breakdown = []
        current_date = week_start
        while current_date <= week_end:
            day_pnl = FinancialReportService.get_daily_pnl(current_date)
            daily_breakdown.append({
                'date': current_date,
                'revenue': day_pnl['revenue'],
                'expenses': day_pnl['expenses'],
                'profit': day_pnl['profit'],
                'cogs': day_pnl['cogs'],
                'commissions': day_pnl['commissions'],
                'margin': day_pnl['margin'],
            })
            current_date += timedelta(days=1)
        
        result['daily_breakdown'] = daily_breakdown
        result['daily_data'] = daily_breakdown  # Backward compat
        return result
    
    @staticmethod
    def get_monthly_pnl(year: int = None, month: int = None) -> dict:
        """Get monthly P&L with weekly breakdown."""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        result = FinancialReportService.get_period_pnl(start_date, end_date)
        result['year'] = year
        result['month'] = month
        
        # Generate weekly breakdown for the month
        weekly_breakdown = []
        current_week_start = start_date
        
        # Adjust to Monday if needed (or keep start_date if it's the 1st)
        while current_week_start <= end_date:
            # Week ends on Sunday or end of month, whichever comes first
            current_week_end = current_week_start + timedelta(days=6 - current_week_start.weekday())
            if current_week_end > end_date:
                current_week_end = end_date
            
            week_pnl = FinancialReportService.get_period_pnl(current_week_start, current_week_end)
            weekly_breakdown.append({
                'start_date': current_week_start,
                'end_date': current_week_end,
                'revenue': week_pnl['revenue'],
                'expenses': week_pnl['expenses'],
                'profit': week_pnl['profit'],
                'cogs': week_pnl['cogs'],
                'commissions': week_pnl['commissions'],
                'margin': week_pnl['margin'],
            })
            
            # Move to next week (Monday after current_week_end)
            current_week_start = current_week_end + timedelta(days=1)
        
        result['weekly_breakdown'] = weekly_breakdown
        result['weekly_data'] = weekly_breakdown  # Backward compat
        return result
    
    @staticmethod
    def get_annual_pnl(year: int = None) -> dict:
        """Get annual P&L with monthly breakdown."""
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        result = FinancialReportService.get_period_pnl(start_date, end_date)
        result['year'] = year
        
        # Monthly breakdown
        monthly_breakdown = []
        for m in range(1, 13):
            m_start = date(year, m, 1)
            m_end = date(year, m, monthrange(year, m)[1])
            m_pnl = FinancialReportService.get_period_pnl(m_start, m_end)
            monthly_breakdown.append({
                'month': m,
                'month_name': m_start.strftime('%B'),
                'revenue': m_pnl['revenue'],
                'cogs': m_pnl['cogs'],
                'gross_profit': m_pnl['gross_profit'],
                'net_profit': m_pnl['net_profit'],
                # Aliases for templates
                'expenses': m_pnl['expenses'],
                'profit': m_pnl['profit'],
                'margin': m_pnl['margin'],
            })
        
        result['monthly_breakdown'] = monthly_breakdown
        result['monthly_data'] = monthly_breakdown  # Backward compat
        return result
    
    @staticmethod
    def get_payroll_monthly(year: int = None, month: int = None) -> dict:
        """Get monthly payroll summary."""
        from apps.payroll.models import MonthlyPayroll, PayrollItem, CasualLabor, MiscExpenseRecord
        
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        # Monthly payroll - use MonthlyPayroll's stored totals
        try:
            monthly_payroll = MonthlyPayroll.objects.filter(
                year=year,
                month=month
            ).first()
            
            if monthly_payroll:
                # Count employees from PayrollItem
                emp_count = PayrollItem.objects.filter(payroll=monthly_payroll).count()
                payroll = {
                    'total_gross': monthly_payroll.total_gross or Decimal('0.00'),
                    'total_deductions': (monthly_payroll.total_gross or Decimal('0.00')) - (monthly_payroll.total_net or Decimal('0.00')),
                    'total_net': monthly_payroll.total_net or Decimal('0.00'),
                    'employee_count': emp_count,
                }
            else:
                payroll = {
                    'total_gross': Decimal('0.00'),
                    'total_deductions': Decimal('0.00'),
                    'total_net': Decimal('0.00'),
                    'employee_count': 0,
                }
        except Exception:
            payroll = {
                'total_gross': Decimal('0.00'),
                'total_deductions': Decimal('0.00'),
                'total_net': Decimal('0.00'),
                'employee_count': 0,
            }
        
        # Get employee payment details (for both HTML and PDF)
        employee_payments = []
        employees = []  # For PDF template
        total_basic = Decimal('0.00')
        total_allowances = Decimal('0.00')
        total_deductions = Decimal('0.00')
        
        # Aggregate deduction types
        deduction_totals = {
            'paye': Decimal('0'),
            'nhif': Decimal('0'),
            'nssf': Decimal('0'),
            'pension': Decimal('0'),
            'loan': Decimal('0'),
            'advance': Decimal('0'),
            'other': Decimal('0'),
        }
        
        try:
            payroll_items = PayrollItem.objects.filter(
                payroll__year=year,
                payroll__month=month
            ).select_related('employee')
            
            for item in payroll_items:
                # Calculate allowances
                allowances = (
                    (item.housing_allowance or Decimal('0')) +
                    (item.transport_allowance or Decimal('0')) +
                    (item.other_allowances or Decimal('0')) +
                    (item.overtime_pay or Decimal('0')) +
                    (item.bonus or Decimal('0'))
                )
                
                # Calculate deductions and track by type
                item_paye = item.paye or Decimal('0')
                item_nhif = item.nhif or Decimal('0')
                item_nssf = item.nssf or Decimal('0')
                item_pension = item.pension or Decimal('0')
                item_loan = item.loan_deduction or Decimal('0')
                item_advance = item.advance_deduction or Decimal('0')
                item_other = item.other_deductions or Decimal('0')
                
                deductions = item_paye + item_nhif + item_nssf + item_pension + item_loan + item_advance + item_other
                
                # Accumulate deduction totals
                deduction_totals['paye'] += item_paye
                deduction_totals['nhif'] += item_nhif
                deduction_totals['nssf'] += item_nssf
                deduction_totals['pension'] += item_pension
                deduction_totals['loan'] += item_loan
                deduction_totals['advance'] += item_advance
                deduction_totals['other'] += item_other
                
                # HTML template format
                employee_payments.append({
                    'name': f"{item.employee.first_name} {item.employee.last_name}",
                    'role': getattr(item.employee, 'role', 'Staff'),
                    'base_salary': item.basic_salary + allowances,  # gross_salary
                    'deductions': deductions,
                    'net_pay': item.net_salary,
                })
                
                # PDF template format
                employees.append({
                    'name': f"{item.employee.first_name} {item.employee.last_name}",
                    'role': getattr(item.employee, 'role', 'Staff'),
                    'basic_salary': item.basic_salary,
                    'allowances': allowances,
                    'deductions': deductions,
                    'net_pay': item.net_salary,
                })
                
                total_basic += item.basic_salary
                total_allowances += allowances
                total_deductions += deductions
        except Exception:
            pass
        
        # Build deduction breakdown for templates
        deduction_breakdown = []
        deduction_types = [
            ('paye', 'PAYE (Tax)', 'file-earmark-text'),
            ('nhif', 'NHIF', 'hospital'),
            ('nssf', 'NSSF', 'piggy-bank'),
            ('pension', 'Pension', 'hourglass'),
            ('loan', 'Loan Deduction', 'credit-card'),
            ('advance', 'Advance Recovery', 'arrow-left-right'),
            ('other', 'Other Deductions', 'dash-circle'),
        ]
        for key, name, icon in deduction_types:
            if deduction_totals[key] > 0:
                deduction_breakdown.append({
                    'name': name,
                    'icon': icon,
                    'amount': deduction_totals[key],
                    'percentage': (deduction_totals[key] / total_deductions * 100) if total_deductions > 0 else Decimal('0'),
                })
        
        # Casual labor
        casual = CasualLabor.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00')),
            count=Count('id'),
        )
        
        # Misc expenses
        try:
            misc = MiscExpenseRecord.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00')),
            )
            misc_total = misc['total']
        except Exception:
            misc_total = Decimal('0.00')
        
        salary_total = payroll['total_net']
        casual_total = casual['total']
        grand_total = salary_total + casual_total + misc_total
        
        # Calculate average salary
        avg_salary = (salary_total / payroll['employee_count']) if payroll['employee_count'] > 0 else Decimal('0.00')
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'payroll': payroll,
            'casual_labor': casual,
            'total_labor_cost': salary_total + casual_total,
            # HTML template fields
            'employee_count': payroll['employee_count'],
            'total_payroll': salary_total,
            'salary_total': salary_total,
            'casual_total': casual_total,
            'misc_total': misc_total,
            'grand_total': grand_total,
            'base_total': payroll['total_gross'],
            'deductions_total': payroll['total_deductions'],
            'employee_payments': employee_payments,
            'deduction_breakdown': deduction_breakdown,
            # PDF template fields
            'employees': employees,
            'total_basic': total_basic,
            'total_allowances': total_allowances,
            'total_deductions': total_deductions,
            'avg_salary': avg_salary,
        }
    
    @staticmethod
    def get_payroll_annual(year: int = None) -> dict:
        """Get annual payroll summary."""
        from apps.payroll.models import MiscExpenseRecord, PayrollItem
        
        if year is None:
            year = date.today().year
        
        # Aggregate all months
        monthly_breakdown = []
        total_salary = Decimal('0')
        total_casual = Decimal('0')
        total_misc = Decimal('0')
        total_basic = Decimal('0')
        total_allowances = Decimal('0')
        total_deductions = Decimal('0')
        
        for m in range(1, 13):
            m_data = FinancialReportService.get_payroll_monthly(year, m)
            month_total = m_data['salary_total'] + m_data['casual_total'] + m_data['misc_total']
            monthly_breakdown.append({
                'month': m,
                'month_name': date(year, m, 1).strftime('%B'),
                'salary': m_data['salary_total'],
                'casual': m_data['casual_total'],
                'misc': m_data['misc_total'],
                'total': month_total,
                'employee_count': m_data['employee_count'],
                # Original field names
                'gross_pay': m_data['base_total'],
                'net_pay': m_data['salary_total'],
                'casual_labor': m_data['casual_total'],
            })
            total_salary += m_data['salary_total']
            total_casual += m_data['casual_total']
            total_misc += m_data['misc_total']
            total_basic += m_data.get('total_basic', Decimal('0'))
            total_allowances += m_data.get('total_allowances', Decimal('0'))
            total_deductions += m_data.get('total_deductions', Decimal('0'))
        
        # Count unique employees in the year
        employee_count = PayrollItem.objects.filter(
            payroll__year=year
        ).values('employee').distinct().count()
        
        grand_total = total_salary + total_casual + total_misc
        
        # Add percentage of year to each month
        for m in monthly_breakdown:
            m['percentage'] = (m['total'] / grand_total * 100) if grand_total > 0 else Decimal('0')
        
        # Calculate monthly average
        months_with_data = sum(1 for m in monthly_breakdown if m['total'] > 0)
        monthly_avg = (grand_total / months_with_data) if months_with_data > 0 else Decimal('0')
        
        # YoY change (compare to previous year)
        prev_year_data = None
        yoy_change = Decimal('0')
        try:
            prev_salary = Decimal('0')
            prev_casual = Decimal('0')
            prev_misc = Decimal('0')
            for m in range(1, 13):
                m_data = FinancialReportService.get_payroll_monthly(year - 1, m)
                prev_salary += m_data['salary_total']
                prev_casual += m_data['casual_total']
                prev_misc += m_data['misc_total']
            prev_total = prev_salary + prev_casual + prev_misc
            if prev_total > 0:
                yoy_change = ((grand_total - prev_total) / prev_total * 100)
        except Exception:
            pass
        
        return {
            'year': year,
            'start_date': date(year, 1, 1),
            'end_date': date(year, 12, 31),
            'monthly_data': monthly_breakdown,
            'monthly_breakdown': monthly_breakdown,
            'totals': {
                'total_gross': total_salary,
                'total_net': total_salary,
                'total_casual': total_casual,
                'total_labor_cost': total_salary + total_casual,
            },
            # Aliases for templates
            'employee_count': employee_count,
            'total_payroll': total_salary,
            'salary_total': total_salary,
            'casual_total': total_casual,
            'misc_total': total_misc,
            'grand_total': grand_total,
            # PDF template fields
            'monthly_avg': monthly_avg,
            'yoy_change': yoy_change,
            'total_basic': total_basic,
            'total_allowances': total_allowances,
            'total_deductions': total_deductions,
        }
    
    @staticmethod
    def get_casual_labor_report(year: int = None, month: int = None) -> dict:
        """Get casual labor breakdown."""
        from apps.payroll.models import CasualLabor
        
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        records = CasualLabor.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        total = records.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00')),
            count=Count('id'),
            total_workers=Coalesce(Sum('number_of_workers'), 0),
        )
        
        # Group by worker name
        worker_payments = []
        workers = []  # For PDF template
        worker_summary = records.values('worker_name').annotate(
            days=Count('id'),
            total=Sum('total_amount'),
            avg_rate=Avg('daily_rate'),
            total_workers=Sum('number_of_workers'),
        ).order_by('-total')
        
        for w in worker_summary:
            worker_payments.append({
                'name': w['worker_name'],
                'days': w['days'],
                'rate': w['avg_rate'] or 0,
                'total': w['total'],
            })
            workers.append({
                'name': w['worker_name'],
                'days_worked': w['days'],
                'hours': w['days'] * 8,  # Assume 8-hour workdays
                'rate': w['avg_rate'] or 0,
                'total': w['total'],
            })
        
        total_days = records.count()
        total_hours = total_days * 8  # Assume 8-hour workdays
        
        # Calculate average rate
        avg_rate = Decimal('0')
        if total['count'] > 0:
            avg_rate = total['total'] / total['count']
        
        # Group by date for daily breakdown
        by_date = []
        date_summary = records.values('date').annotate(
            worker_count=Sum('number_of_workers'),
            cost=Sum('total_amount'),
        ).order_by('date')
        
        for d in date_summary:
            by_date.append({
                'date': d['date'],
                'worker_count': d['worker_count'],
                'hours': d['worker_count'] * 8,  # Assume 8-hour workdays
                'cost': d['cost'],
            })
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'records': list(records.values()),
            'total_amount': total['total'],
            'record_count': total['count'],
            # HTML template fields
            'worker_count': len(worker_payments),
            'total_paid': total['total'],
            'total_days': total_days,
            'worker_payments': worker_payments,
            # PDF template fields
            'total_cost': total['total'],
            'total_hours': total_hours,
            'avg_rate': avg_rate,
            'workers': workers,
            'by_date': by_date,
        }
    
    @staticmethod
    def get_misc_expense_report(year: int = None, month: int = None) -> dict:
        """Get misc expense breakdown."""
        from apps.payroll.models import MiscExpenseRecord
        
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        records = MiscExpenseRecord.objects.filter(
            expense_date__gte=start_date,
            expense_date__lte=end_date
        ).select_related('category').order_by('expense_date')
        
        # Calculate totals FIRST (needed for percentages)
        total = records.aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00')),
            count=Count('id'),
        )
        
        # By category
        by_category = records.values(
            'category__name'
        ).annotate(
            amount=Sum('amount'),
            count=Count('id'),
        ).order_by('-amount')
        
        # Format category breakdown for templates (with percentage for PDF)
        category_breakdown = []
        by_category_pdf = []  # For PDF template
        for cat in by_category:
            cat_amount = cat['amount'] or Decimal('0')
            percentage = (cat_amount / total['total'] * 100) if total['total'] > 0 else Decimal('0')
            category_breakdown.append({
                'category_name': cat['category__name'] or 'Uncategorized',
                'count': cat['count'],
                'amount': cat_amount,
            })
            by_category_pdf.append({
                'name': cat['category__name'] or 'Uncategorized',
                'count': cat['count'],
                'amount': cat_amount,
                'percentage': percentage,
            })
        
        # Format expenses for templates
        expenses = []
        for r in records:
            expenses.append({
                'date': r.expense_date,
                'description': r.description,
                'category': r.category.name if r.category else 'Uncategorized',
                'amount': r.amount,
            })
        
        # Calculate month-over-month change
        mom_change = Decimal('0')
        try:
            if month == 1:
                prev_year, prev_month = year - 1, 12
            else:
                prev_year, prev_month = year, month - 1
            
            prev_start = date(prev_year, prev_month, 1)
            prev_end = date(prev_year, prev_month, monthrange(prev_year, prev_month)[1])
            
            prev_total = MiscExpenseRecord.objects.filter(
                expense_date__gte=prev_start,
                expense_date__lte=prev_end
            ).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.00'))
            )['total']
            
            if prev_total > 0:
                mom_change = ((total['total'] - prev_total) / prev_total * 100)
        except Exception:
            pass
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'records': list(records.values('expense_date', 'category__name', 'description', 'amount')),
            'by_category': by_category_pdf,
            'total_amount': total['total'],
            'record_count': total['count'],
            # HTML template fields
            'expense_count': total['count'],
            'category_count': len(category_breakdown),
            'category_breakdown': category_breakdown,
            'expenses': expenses,
            # PDF template fields
            'total_expenses': total['total'],
            'transaction_count': total['count'],
            'mom_change': mom_change,
        }
    
    @staticmethod
    def get_product_performance(start_date: date, end_date: date) -> dict:
        """
        Get product performance report for a date range.
        Shows production vs sales, revenue, margins by product.
        """
        # Get products with sales data
        product_sales = SalesReturnItem.objects.filter(
            sales_return__return_date__gte=start_date,
            sales_return__return_date__lte=end_date
        ).values(
            'product__id',
            'product__name',
            'product__selling_price',
        ).annotate(
            qty_dispatched=Coalesce(Sum('qty_dispatched'), 0),
            qty_sold=Coalesce(Sum('qty_sold'), 0),
            qty_returned=Coalesce(Sum('qty_returned'), 0),
            total_revenue=Coalesce(Sum('revenue'), Decimal('0.00')),
        ).order_by('-total_revenue')
        
        # Get production data per product
        product_production = ProductionBatch.objects.filter(
            production_date__gte=start_date,
            production_date__lte=end_date
        ).values(
            'product__id',
        ).annotate(
            qty_produced=Coalesce(Sum('quantity_produced'), 0),
            production_cost=Coalesce(Sum('total_ingredient_cost'), Decimal('0.00')),
            batch_count=Count('id'),
        )
        
        # Create production lookup
        production_lookup = {p['product__id']: p for p in product_production}
        
        products = []
        total_revenue = Decimal('0')
        total_cost = Decimal('0')
        total_profit = Decimal('0')
        
        for sale in product_sales:
            prod_id = sale['product__id']
            prod_data = production_lookup.get(prod_id, {})
            
            revenue = sale['total_revenue']
            cost = prod_data.get('production_cost', Decimal('0'))
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else Decimal('0')
            sell_through = (sale['qty_sold'] / sale['qty_dispatched'] * 100) if sale['qty_dispatched'] > 0 else 0
            
            products.append({
                'product_id': prod_id,
                'product_name': sale['product__name'],
                'unit_price': sale['product__selling_price'],
                'qty_produced': prod_data.get('qty_produced', 0),
                'qty_dispatched': sale['qty_dispatched'],
                'qty_sold': sale['qty_sold'],
                'qty_returned': sale['qty_returned'],
                'production_cost': cost,
                'revenue': revenue,
                'profit': profit,
                'margin': margin,
                'sell_through_rate': sell_through,
                'batch_count': prod_data.get('batch_count', 0),
            })
            
            total_revenue += revenue
            total_cost += cost
            total_profit += profit
        
        # Calculate revenue share for each product
        for p in products:
            p['revenue_share'] = (p['revenue'] / total_revenue * 100) if total_revenue > 0 else Decimal('0')
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'products': products,
            'summary': {
                'total_products': len(products),
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'overall_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0'),
            }
        }
    
    @staticmethod
    def get_expense_summary(start_date: date, end_date: date) -> dict:
        """
        Get expense summary for a date range.
        Combines inventory purchases, payroll, casual labor, and misc expenses.
        """
        from apps.payroll.models import PayrollItem, MonthlyPayroll, CasualLabor, MiscExpenseRecord, MiscExpenseCategory
        
        # Inventory purchases
        inventory_total = Decimal('0')
        inventory_breakdown = []
        # INVENTORY_ITEMS is a list of tuples: (item_id, name, is_active, unit)
        for item_tuple in INVENTORY_ITEMS:
            item_id = item_tuple[0]
            item_name = item_tuple[1]
            PurchasesModel = get_purchases_model(item_id)
            purchases = PurchasesModel.objects.filter(
                purchase_date__gte=start_date,
                purchase_date__lte=end_date
            )
            totals = purchases.aggregate(
                total_cost=Coalesce(Sum('total_cost'), Decimal('0.00')),
                purchase_count=Count('id'),
            )
            if totals['purchase_count'] > 0:
                inventory_breakdown.append({
                    'name': item_name,
                    'amount': totals['total_cost'],
                    'count': totals['purchase_count'],
                })
                inventory_total += totals['total_cost']
        
        # Casual Labor
        casual_labor = CasualLabor.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        casual_total = casual_labor.aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )['total']
        casual_count = casual_labor.count()
        
        # Misc Expenses by category
        misc_expenses = MiscExpenseRecord.objects.filter(
            expense_date__gte=start_date,
            expense_date__lte=end_date
        )
        misc_total = misc_expenses.aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total']
        
        misc_by_category = misc_expenses.values(
            'category__name'
        ).annotate(
            amount=Sum('amount'),
            count=Count('id'),
        ).order_by('-amount')
        
        # Sales Commissions
        commissions = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).aggregate(
            total=Coalesce(Sum('commission_amount'), Decimal('0.00'))
        )['total']
        
        # Total expenses
        total_expenses = inventory_total + casual_total + misc_total + commissions
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'inventory': {
                'total': inventory_total,
                'breakdown': inventory_breakdown,
            },
            'casual_labor': {
                'total': casual_total,
                'count': casual_count,
            },
            'misc_expenses': {
                'total': misc_total,
                'by_category': list(misc_by_category),
            },
            'commissions': {
                'total': commissions,
            },
            'summary': {
                'total_expenses': total_expenses,
                'inventory_percent': (inventory_total / total_expenses * 100) if total_expenses > 0 else Decimal('0'),
                'labor_percent': (casual_total / total_expenses * 100) if total_expenses > 0 else Decimal('0'),
                'misc_percent': (misc_total / total_expenses * 100) if total_expenses > 0 else Decimal('0'),
                'commission_percent': (commissions / total_expenses * 100) if total_expenses > 0 else Decimal('0'),
            }
        }
