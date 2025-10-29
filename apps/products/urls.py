from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Product URLs
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_update, name='product_update'),
    
    # Mix URLs
    path('mixes/<int:pk>/', views.mix_detail, name='mix_detail'),
    path('<int:product_id>/mixes/create/', views.mix_create, name='mix_create'),
    
    # AJAX API
    path('api/ingredients/<int:ingredient_id>/cost/', views.get_ingredient_cost, name='get_ingredient_cost'),
]
