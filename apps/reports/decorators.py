"""
Reports App Decorators
Access control decorators for report views.
All report routes require ACCOUNTANT role or higher.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


# Roles with access to reports (hierarchy order)
REPORT_ACCESS_ROLES = ['SUPERADMIN', 'ADMIN', 'ACCOUNTANT']


def report_access_required(view_func):
    """
    Decorator to restrict access to ACCOUNTANT role or higher.
    Must be used after @login_required.
    
    Usage:
        @login_required
        @report_access_required
        def my_report_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access reports.")
            return redirect('accounts:login')
        
        if request.user.role not in REPORT_ACCESS_ROLES:
            messages.error(
                request, 
                "Reports require Accountant access or higher. "
                f"Your role: {request.user.get_role_display()}"
            )
            return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def report_access_required_roles(allowed_roles):
    """
    Decorator factory for custom role requirements.
    
    Usage:
        @login_required
        @report_access_required_roles(['SUPERADMIN', 'ADMIN'])
        def sensitive_report_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in to access this page.")
                return redirect('accounts:login')
            
            if request.user.role not in allowed_roles:
                messages.error(
                    request, 
                    f"Access denied. Required roles: {', '.join(allowed_roles)}. "
                    f"Your role: {request.user.get_role_display()}"
                )
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
