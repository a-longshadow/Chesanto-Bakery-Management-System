"""
Reports App URLs
================
All routes require ACCOUNTANT role or higher.
35 report routes + 5 analytics routes + 25 PDF routes = 65 total.
"""
from django.urls import path
from . import views
from . import pdf_views

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
    path('sales/daily/pdf/', pdf_views.sales_daily_pdf, name='sales_daily_pdf'),
    path('sales/weekly/', views.sales_weekly, name='sales_weekly'),
    path('sales/weekly/pdf/', pdf_views.sales_weekly_pdf, name='sales_weekly_pdf'),
    path('sales/monthly/', views.sales_monthly, name='sales_monthly'),
    path('sales/monthly/pdf/', pdf_views.sales_monthly_pdf, name='sales_monthly_pdf'),
    path('sales/annual/', views.sales_annual, name='sales_annual'),
    path('sales/annual/pdf/', pdf_views.sales_annual_pdf, name='sales_annual_pdf'),
    path('sales/salesperson/', views.salesperson_performance, name='salesperson_performance'),
    path('sales/salesperson/pdf/', pdf_views.salesperson_performance_pdf, name='salesperson_performance_pdf'),
    path('sales/commissions/', views.commission_report, name='commission_report'),
    path('sales/commissions/pdf/', pdf_views.commission_report_pdf, name='commission_report_pdf'),
    
    # ═══════════════════════════════════════════════════════════════
    # INVENTORY REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('inventory/', views.inventory_index, name='inventory_index'),
    path('inventory/daily/', views.inventory_daily, name='inventory_daily'),
    path('inventory/daily/pdf/', pdf_views.inventory_daily_pdf, name='inventory_daily_pdf'),
    path('inventory/weekly/', views.inventory_weekly, name='inventory_weekly'),
    path('inventory/weekly/pdf/', pdf_views.inventory_weekly_pdf, name='inventory_weekly_pdf'),
    path('inventory/monthly/', views.inventory_monthly, name='inventory_monthly'),
    path('inventory/monthly/pdf/', pdf_views.inventory_monthly_pdf, name='inventory_monthly_pdf'),
    path('inventory/annual/', views.inventory_annual, name='inventory_annual'),
    path('inventory/annual/pdf/', pdf_views.inventory_annual_pdf, name='inventory_annual_pdf'),
    path('inventory/valuation/', views.inventory_valuation, name='inventory_valuation'),
    path('inventory/valuation/pdf/', pdf_views.inventory_valuation_pdf, name='inventory_valuation_pdf'),
    path('inventory/purchases/', views.purchase_history, name='purchase_history'),
    path('inventory/purchases/pdf/', pdf_views.purchase_history_pdf, name='purchase_history_pdf'),
    
    # ═══════════════════════════════════════════════════════════════
    # PRODUCTION REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('production/', views.production_index, name='production_index'),
    path('production/daily/', views.production_daily, name='production_daily'),
    path('production/daily/pdf/', pdf_views.production_daily_pdf, name='production_daily_pdf'),
    path('production/weekly/', views.production_weekly, name='production_weekly'),
    path('production/weekly/pdf/', pdf_views.production_weekly_pdf, name='production_weekly_pdf'),
    path('production/monthly/', views.production_monthly, name='production_monthly'),
    path('production/monthly/pdf/', pdf_views.production_monthly_pdf, name='production_monthly_pdf'),
    path('production/annual/', views.production_annual, name='production_annual'),
    path('production/annual/pdf/', pdf_views.production_annual_pdf, name='production_annual_pdf'),
    path('production/efficiency/', views.production_efficiency, name='production_efficiency'),
    path('production/efficiency/pdf/', pdf_views.production_efficiency_pdf, name='production_efficiency_pdf'),
    path('production/stock-movement/', views.stock_movement, name='stock_movement'),
    path('production/stock-movement/pdf/', pdf_views.stock_movement_pdf, name='stock_movement_pdf'),
    
    # ═══════════════════════════════════════════════════════════════
    # PAYROLL REPORTS (Monthly / Annual only)
    # ═══════════════════════════════════════════════════════════════
    path('payroll/', views.payroll_index, name='payroll_index'),
    path('payroll/monthly/', views.payroll_monthly, name='payroll_monthly'),
    path('payroll/monthly/pdf/', pdf_views.payroll_monthly_pdf, name='payroll_monthly_pdf'),
    path('payroll/annual/', views.payroll_annual, name='payroll_annual'),
    path('payroll/annual/pdf/', pdf_views.payroll_annual_pdf, name='payroll_annual_pdf'),
    path('payroll/casual-labor/', views.casual_labor_report, name='casual_labor_report'),
    path('payroll/casual-labor/pdf/', pdf_views.casual_labor_pdf, name='casual_labor_pdf'),
    path('payroll/misc-expenses/', views.misc_expense_report, name='misc_expense_report'),
    path('payroll/misc-expenses/pdf/', pdf_views.misc_expense_pdf, name='misc_expense_pdf'),
    
    # ═══════════════════════════════════════════════════════════════
    # PROFIT & LOSS REPORTS (Daily / Weekly / Monthly / Annual)
    # ═══════════════════════════════════════════════════════════════
    path('financial/', views.financial_index, name='financial_index'),
    path('financial/pnl/daily/', views.profit_loss_daily, name='profit_loss_daily'),
    path('financial/pnl/daily/pdf/', pdf_views.pnl_daily_pdf, name='pnl_daily_pdf'),
    path('financial/pnl/weekly/', views.profit_loss_weekly, name='profit_loss_weekly'),
    path('financial/pnl/weekly/pdf/', pdf_views.pnl_weekly_pdf, name='pnl_weekly_pdf'),
    path('financial/pnl/monthly/', views.profit_loss_monthly, name='profit_loss_monthly'),
    path('financial/pnl/monthly/pdf/', pdf_views.pnl_monthly_pdf, name='pnl_monthly_pdf'),
    path('financial/pnl/annual/', views.profit_loss_annual, name='profit_loss_annual'),
    path('financial/pnl/annual/pdf/', pdf_views.pnl_annual_pdf, name='pnl_annual_pdf'),
    path('financial/product-performance/', views.product_performance, name='product_performance'),
    path('financial/product-performance/pdf/', pdf_views.product_performance_pdf, name='product_performance_pdf'),
    path('financial/expense-summary/', views.expense_summary, name='expense_summary'),
    path('financial/expense-summary/pdf/', pdf_views.expense_summary_pdf, name='expense_summary_pdf'),
    
    # ═══════════════════════════════════════════════════════════════
    # EMAIL ENDPOINT (AJAX)
    # ═══════════════════════════════════════════════════════════════
    path('email/send/', views.email_report, name='email_report'),
]
