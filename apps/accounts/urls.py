"""
URL Configuration for Authentication and Profile Views
"""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/confirmation/<int:user_id>/', views.account_confirmation_view, name='account_confirmation'),
    path('auth/otp-verify/', views.otp_verify_view, name='otp_verify'),
    path('auth/password/change/', views.password_change_view, name='password_change'),
    path('auth/password/reset/', views.password_reset_request_view, name='password_reset_request'),
    path('auth/password/reset/verify/', views.password_reset_verify_view, name='password_reset_verify'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),  # Staff dashboard
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/edit/<int:user_id>/', views.profile_edit_view, name='profile_edit_other'),  # Admin editing other users
    path('profile/history/', views.profile_changes_view, name='profile_changes'),
    
    # User-specific profile (for BASIC_USER and superadmin access)
    path('auth/<int:user_id>/profile/', views.user_profile_view, name='user_profile'),
]
