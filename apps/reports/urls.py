"""
Reports App URLs
================
All routes require ACCOUNTANT role or higher.
35 report routes + 5 analytics routes = 40 total.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # DASHBOARD (Entry Point)
    # ═══════════════════════════════════════════════════════════════
    path('', views.dashboard, name='dashboard'),
    
    # ═══════════════════════════════════════════════════════════════
    # SALES REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('sales/', views.sales_index, name='sales_index'),
    path('sales/daily/', views.sales_daily, name='sales_daily'),
    path('sales/weekly/', views.sales_weekly, name='sales_weekly'),
    path('sales/monthly/', views.sales_monthly, name='sales_monthly'),
    path('sales/annual/', views.sales_annual, name='sales_annual'),
    path('sales/salesperson/', views.salesperson_performance, name='salesperson_performance'),
    path('sales/commissions/', views.commission_report, name='commission_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # INVENTORY REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('inventory/', views.inventory_index, name='inventory_index'),
    path('inventory/daily/', views.inventory_daily, name='inventory_daily'),
    path('inventory/weekly/', views.inventory_weekly, name='inventory_weekly'),
    path('inventory/monthly/', views.inventory_monthly, name='inventory_monthly'),
    path('inventory/annual/', views.inventory_annual, name='inventory_annual'),
    path('inventory/valuation/', views.inventory_valuation, name='inventory_valuation'),
    path('inventory/purchases/', views.purchase_history, name='purchase_history'),
    
    # ═══════════════════════════════════════════════════════════════
    # PRODUCTION REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('production/', views.production_index, name='production_index'),
    path('production/daily/', views.production_daily, name='production_daily'),
    path('production/weekly/', views.production_weekly, name='production_weekly'),
    path('production/monthly/', views.production_monthly, name='production_monthly'),
    path('production/annual/', views.production_annual, name='production_annual'),
    path('production/efficiency/', views.production_efficiency, name='production_efficiency'),
    path('production/stock-movement/', views.stock_movement, name='stock_movement'),
    
    # ═══════════════════════════════════════════════════════════════
    # PAYROLL REPORTS (Monthly / Annual only)
    # ═══════════════════════════════════════════════════════════════
    path('payroll/', views.payroll_index, name='payroll_index'),
    path('payroll/monthly/', views.payroll_monthly, name='payroll_monthly'),
    path('payroll/annual/', views.payroll_annual, name='payroll_annual'),
    path('payroll/casual-labor/', views.casual_labor_report, name='casual_labor_report'),
    path('payroll/misc-expenses/', views.misc_expense_report, name='misc_expense_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # PROFIT & LOSS REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('financial/', views.financial_index, name='financial_index'),
    path('financial/pnl/daily/', views.profit_loss_daily, name='profit_loss_daily'),
    path('financial/pnl/weekly/', views.profit_loss_weekly, name='profit_loss_weekly'),
    path('financial/pnl/monthly/', views.profit_loss_monthly, name='profit_loss_monthly'),
    path('financial/pnl/annual/', views.profit_loss_annual, name='profit_loss_annual'),
    path('financial/product-performance/', views.product_performance, name='product_performance'),
    path('financial/expense-summary/', views.expense_summary, name='expense_summary'),
    
    # ═══════════════════════════════════════════════════════════════
    # EXPORT/EMAIL ENDPOINTS (AJAX)
    # ═══════════════════════════════════════════════════════════════
    path('export/csv/', views.export_csv, name='export_csv'),
    path('email/send/', views.email_report, name='email_report'),
]
