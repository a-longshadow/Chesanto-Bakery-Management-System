from django.urls import path
from . import views

app_name = 'production'

urlpatterns = [
    # Daily Production Dashboard
    path('', views.daily_production_today, name='daily_production'),
    path('<str:date>/', views.daily_production_view, name='daily_production_date'),
    
    # Production Batches
    path('batch/create/', views.batch_create, name='batch_create'),
    path('batch/create/<str:date>/', views.batch_create, name='batch_create_date'),
    path('batch/<int:pk>/', views.batch_detail, name='batch_detail'),
    path('batch/<int:pk>/edit/', views.batch_edit, name='batch_edit'),
    
    # Indirect Costs
    path('costs/<str:date>/', views.indirect_costs_form, name='indirect_costs'),
    
    # Book Closing
    path('close/<str:date>/', views.close_books, name='close_books'),
]
