"""
Inventory App - URL Configuration
Routes for inventory dashboards, purchase recording, and item management.
"""
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboards
    path('', views.dashboard, name='dashboard'),
    path('ingredients/', views.ingredients_dashboard, name='ingredients_dashboard'),
    path('indirect-costs/', views.indirect_costs_dashboard, name='indirect_costs_dashboard'),
    
    # Item Details
    path('item/<int:inventory_item_id>/', views.item_detail, name='item_detail'),
    
    # Purchases
    path('purchase/create/', views.create_purchase, name='purchase_create'),
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchase/<int:inventory_item_id>/history/', views.purchase_history, name='purchase_history'),
    
    # Outputs (indirect costs only)
    path('output/create/', views.create_output, name='output_create'),
    path('outputs/', views.output_list, name='output_list'),
    path('output/<int:inventory_item_id>/history/', views.output_history, name='output_history'),
    
    # Stock Alerts
    path('alerts/', views.alerts_list, name='alerts_list'),
    
    # API endpoints (for AJAX)
    path('api/stock-levels/', views.api_stock_levels, name='api_stock_levels'),
    path('api/item/<int:inventory_item_id>/stock/', views.api_item_stock, name='api_item_stock'),
]
