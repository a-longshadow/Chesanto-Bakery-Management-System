"""
Inventory App URLs
"""
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Inventory Items
    path('', views.inventory_list, name='item_list'),
    path('create/', views.inventory_create, name='item_create'),
    path('<int:pk>/', views.inventory_detail, name='item_detail'),
    path('<int:pk>/edit/', views.inventory_update, name='item_update'),
    
    # Purchases
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/create/', views.purchase_create, name='purchase_create'),
    path('purchases/<int:pk>/', views.purchase_detail, name='purchase_detail'),
    
    # Wastage
    path('wastage/', views.wastage_list, name='wastage_list'),
    path('wastage/create/', views.wastage_create, name='wastage_create'),
    path('wastage/<int:pk>/approve/', views.wastage_approve, name='wastage_approve'),
    
    # Stock Movements
    path('movements/', views.movement_list, name='movement_list'),
]
