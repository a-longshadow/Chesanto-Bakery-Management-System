"""
Analytics App URLs
Routes for real-time analytics views
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('products/', views.product_performance_view, name='product_performance'),
    path('inventory/', views.inventory_status_view, name='inventory_status'),
    path('sales/', views.sales_trends_view, name='sales_trends'),
    path('deficits/', views.deficit_analysis_view, name='deficit_analysis'),
]
