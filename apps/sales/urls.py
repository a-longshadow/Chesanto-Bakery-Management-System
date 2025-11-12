from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales Dashboard (Unified View)
    path('', views.sales_dashboard, name='sales_dashboard'),
    path('dashboard/', views.sales_dashboard, name='dashboard'),  # Alias
    
    # Dispatch Management
    path('dispatches/', views.dispatch_list, name='dispatch_list'),  # Redirects to dashboard
    path('dispatch/create/', views.dispatch_create, name='dispatch_create'),
    path('dispatch/<int:pk>/assign-crates/', views.dispatch_assign_crates, name='dispatch_assign_crates'),
    path('dispatch/<int:pk>/', views.dispatch_detail, name='dispatch_detail'),
    path('dispatch/<int:pk>/edit/', views.dispatch_edit, name='dispatch_edit'),
    path('dispatch/<int:pk>/delete/', views.dispatch_delete, name='dispatch_delete'),
    path('dispatch/bulk-delete/', views.dispatch_bulk_delete, name='dispatch_bulk_delete'),
    
    # Sales Returns
    path('returns/', views.sales_return_list, name='return_list'),
    path('return/<int:dispatch_id>/', views.sales_return, name='sales_return'),
    path('returns/<int:pk>/', views.sales_return_detail, name='return_detail'),
    
    # Deficits
    path('deficits/', views.deficit_list, name='deficit_list'),
    
    # Commissions
    path('commissions/', views.commission_report, name='commission_report'),
]
