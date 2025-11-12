"""
Sales App URLs
"""
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dispatch CRUD
    path('dispatch/create/', views.dispatch_create, name='dispatch_create'),
    path('dispatch/<int:pk>/', views.dispatch_detail, name='dispatch_detail'),
    path('dispatch/<int:pk>/return/', views.dispatch_return, name='dispatch_return'),
    path('dispatches/', views.dispatch_list, name='dispatch_list'),
    
    # Salesperson management
    path('salespeople/', views.salesperson_list, name='salesperson_list'),
    path('salesperson/create/', views.salesperson_create, name='salesperson_create'),
]
