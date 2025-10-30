from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dispatch Management
    path('', views.dispatch_list, name='dispatch_list'),
    path('dispatch/create/', views.dispatch_create, name='dispatch_create'),
    path('dispatch/<int:pk>/', views.dispatch_detail, name='dispatch_detail'),
    
    # Sales Returns
    path('returns/', views.sales_return_list, name='return_list'),
    path('returns/create/<int:dispatch_id>/', views.sales_return_create, name='return_create'),
    path('returns/<int:pk>/', views.sales_return_detail, name='return_detail'),
    
    # Deficits
    path('deficits/', views.deficit_list, name='deficit_list'),
    
    # Commissions
    path('commissions/', views.commission_report, name='commission_report'),
]
