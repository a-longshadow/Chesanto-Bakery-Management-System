"""
Products App - URL Configuration
Routes for product catalog, recipe management, and price updates.
"""
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Products
    path('list/', views.product_list, name='list'),
    path('create/', views.product_create, name='create'),
    path('<int:product_id>/', views.product_detail, name='detail'),
    path('<int:product_id>/edit/', views.product_edit, name='edit'),
    path('<int:product_id>/price/', views.product_price_update, name='price_update'),
    path('<int:product_id>/archive/', views.product_archive, name='archive'),
    path('<int:product_id>/restore/', views.product_restore, name='restore'),
    
    # Mixes (Recipes)
    path('<int:product_id>/mix/create/', views.mix_create, name='mix_create'),
    path('mix/<int:mix_id>/', views.mix_detail, name='mix_detail'),
    path('mix/<int:mix_id>/edit/', views.mix_edit, name='mix_edit'),
    path('mix/<int:mix_id>/archive/', views.mix_archive, name='mix_archive'),
    path('mix/<int:mix_id>/restore/', views.mix_restore, name='mix_restore'),
    
    # API endpoints (for AJAX)
    path('api/products/', views.api_products_list, name='api_products'),
    path('api/product/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/product/<int:product_id>/mix/', views.api_product_mix, name='api_product_mix'),
]
