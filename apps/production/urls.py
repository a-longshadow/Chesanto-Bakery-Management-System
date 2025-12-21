"""
Production App - URL Configuration
"""

from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Production Batches
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/create/', views.batch_create, name='batch_create'),
    path('batches/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    
    # Product Stock
    path('stock/', views.stock_dashboard, name='stock_dashboard'),
    path('stock/<int:product_id>/', views.stock_detail, name='stock_detail'),
    
    # Waste Management
    path('waste/', views.waste_list, name='waste_list'),
    path('waste/dispose/', views.waste_dispose, name='waste_dispose'),
    
    # API endpoints (for AJAX/HTMX)
    path('api/mixes/', views.api_get_mixes, name='api_get_mixes'),
    path('api/mix-preview/<int:mix_id>/', views.api_mix_preview, name='api_mix_preview'),
]
