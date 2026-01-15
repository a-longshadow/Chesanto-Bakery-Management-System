"""
Sales App URLs

Bank Ledger: NO edit URLs exist. Delete only available via Data Management feature.
"""
from django.urls import path
from . import views
from . import delete_views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Dispatch (NO EDIT - bank ledger)
    path('dispatches/', views.dispatch_list, name='dispatch_list'),
    path('dispatch/create/', views.dispatch_create, name='dispatch_create'),
    path('dispatch/<int:pk>/', views.dispatch_detail, name='dispatch_detail'),
    path('dispatch/<int:pk>/return/', views.dispatch_return, name='dispatch_return'),
    
    # Dispatch Delete (SUPERADMIN only - Data Management feature)
    path('dispatch/<int:pk>/delete/', delete_views.dispatch_delete, name='dispatch_delete'),
    
    # Crate Status Update (only mutable action)
    path('return/<int:pk>/crates/', views.update_crate_status, name='update_crate_status'),
    
    # Reports
    path('reports/', views.sales_report, name='sales_report'),
    path('commissions/', views.commission_report, name='commission_report'),
    
    # SALESMAN-specific views (own data only)
    path('my-dispatches/', views.my_dispatches, name='my_dispatches'),
    path('my-commissions/', views.my_commissions, name='my_commissions'),
    
    # SECURITY gate log (no financial data)
    path('gate-log/', views.gate_log, name='gate_log'),
    
    # API (for JavaScript)
    path('api/stock-levels/', views.api_stock_levels, name='api_stock_levels'),
    path('api/commission-preview/', views.api_commission_preview, name='api_commission_preview'),
]
