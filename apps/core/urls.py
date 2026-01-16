"""
Core App - URL Configuration
Data management endpoints for Primary Superadmin only.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Full System Reset (Primary Superadmin only)
    path('data-management/full-reset/', views.full_reset, name='full_reset'),
    path('data-management/reset-complete/', views.reset_complete, name='reset_complete'),
]
