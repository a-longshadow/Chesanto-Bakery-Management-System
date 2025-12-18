"""
Role-Based Access Control Decorators
=====================================
Centralized decorator system for view-level access control.

Usage:
    from apps.accounts.decorators import admin_required, management_required
    
    @admin_required
    def sensitive_view(request):
        ...

Role Groups:
    ADMIN_ROLES: SUPERADMIN, ADMIN
    MANAGEMENT_ROLES: SUPERADMIN, ADMIN, PRODUCT_MANAGER, DEPT_HEAD
    DISPATCH_ROLES: SUPERADMIN, ADMIN, DISPATCH
    SALES_VIEW_ROLES: SUPERADMIN, ADMIN, PRODUCT_MANAGER, DEPT_HEAD, DISPATCH
    GATE_LOG_ROLES: SUPERADMIN, ADMIN, PRODUCT_MANAGER, DEPT_HEAD, DISPATCH, SECURITY
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


# ============================================================================
# ROLE GROUPS (for easier management)
# ============================================================================

# Full administrative access
ADMIN_ROLES = ['SUPERADMIN', 'ADMIN']

# Management level - production, inventory, products (view)
MANAGEMENT_ROLES = ['SUPERADMIN', 'ADMIN', 'PRODUCT_MANAGER', 'DEPT_HEAD']

# Dispatch operations - create/process dispatches and returns
DISPATCH_ROLES = ['SUPERADMIN', 'ADMIN', 'DISPATCH']

# Sales view access - can see all dispatches, dashboard, stock
SALES_VIEW_ROLES = ['SUPERADMIN', 'ADMIN', 'PRODUCT_MANAGER', 'DEPT_HEAD', 'DISPATCH']

# Gate log access - includes SECURITY (no financial data)
GATE_LOG_ROLES = ['SUPERADMIN', 'ADMIN', 'PRODUCT_MANAGER', 'DEPT_HEAD', 'DISPATCH', 'SECURITY']

# Salesman data access - own data + higher roles
SALESMAN_ACCESS_ROLES = ['SUPERADMIN', 'ADMIN', 'SALESMAN']


# ============================================================================
# CORE DECORATOR
# ============================================================================

def role_required(allowed_roles):
    """
    Restrict view access to specific roles.
    
    Args:
        allowed_roles: List of role strings that can access the view
        
    Usage:
        @role_required(['SUPERADMIN', 'ADMIN', 'PRODUCT_MANAGER'])
        def batch_create(request):
            ...
    
    Returns:
        Decorator function that checks user role before allowing access.
        Redirects to home with error message if access denied.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user_role = getattr(request.user, 'role', None)
            
            if user_role not in allowed_roles:
                # Get user-friendly role names for message
                role_display = request.user.get_role_display() if hasattr(request.user, 'get_role_display') else user_role
                messages.error(
                    request, 
                    f'Access denied. Your role ({role_display}) does not have permission to access this page.'
                )
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# SHORTCUT DECORATORS
# ============================================================================

def admin_required(view_func):
    """
    Restrict to SUPERADMIN and ADMIN only.
    
    Use for: Financial transactions, user management, sensitive reports.
    
    Usage:
        @admin_required
        def create_purchase(request):
            ...
    """
    return role_required(ADMIN_ROLES)(view_func)


def management_required(view_func):
    """
    Restrict to SUPERADMIN, ADMIN, PRODUCT_MANAGER, DEPT_HEAD.
    
    Use for: Production, inventory view, products view.
    
    Usage:
        @management_required
        def batch_create(request):
            ...
    """
    return role_required(MANAGEMENT_ROLES)(view_func)


def dispatch_required(view_func):
    """
    Restrict to SUPERADMIN, ADMIN, DISPATCH.
    
    Use for: Creating dispatches, processing returns.
    
    Usage:
        @dispatch_required
        def dispatch_create(request):
            ...
    """
    return role_required(DISPATCH_ROLES)(view_func)


def sales_view_required(view_func):
    """
    Restrict to roles that can view all sales data.
    
    Use for: Sales dashboard, dispatch list, dispatch detail.
    
    Usage:
        @sales_view_required
        def dashboard(request):
            ...
    """
    return role_required(SALES_VIEW_ROLES)(view_func)


def gate_log_required(view_func):
    """
    Restrict to roles that can view gate log (includes SECURITY).
    
    Use for: Gate log view (no financial data).
    
    Usage:
        @gate_log_required
        def gate_log(request):
            ...
    """
    return role_required(GATE_LOG_ROLES)(view_func)


def salesman_access_required(view_func):
    """
    Allow SALESMAN to access their own data, plus higher roles.
    
    Use for: My dispatches, my commissions views.
    
    Usage:
        @salesman_access_required
        def my_dispatches(request):
            # View should filter by request.user for SALESMAN
            ...
    """
    return role_required(SALESMAN_ACCESS_ROLES)(view_func)


# ============================================================================
# SPECIAL DECORATORS
# ============================================================================

def salesman_own_data_only(view_func):
    """
    Allow SALESMAN to access ONLY their own data.
    Higher roles (ADMIN+) get full access to all data.
    
    The view is responsible for filtering data based on request.user.role.
    
    Usage:
        @salesman_own_data_only
        def my_dispatches(request):
            if request.user.role == 'SALESMAN':
                dispatches = SalesDispatch.objects.filter(salesperson=request.user)
            else:
                dispatches = SalesDispatch.objects.all()
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user_role = getattr(request.user, 'role', None)
        
        # Higher roles get full access
        if user_role in SALES_VIEW_ROLES:
            return view_func(request, *args, **kwargs)
        
        # SALESMAN can access (view filters by request.user)
        if user_role == 'SALESMAN':
            return view_func(request, *args, **kwargs)
        
        # All others denied
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    return wrapper


# ============================================================================
# EXISTING DECORATORS (moved from views.py for centralization)
# ============================================================================
# Note: These are duplicated here for import convenience.
# The originals in views.py should be updated to import from here.

def anonymous_required(view_func):
    """
    Redirect authenticated users away from login/register pages.
    
    Usage:
        @anonymous_required
        def login_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You are already logged in.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """
    Only staff/superusers can access.
    
    Note: Consider using admin_required instead for role-based control.
    
    Usage:
        @staff_required
        def admin_view(request):
            ...
    """
    from django.core.exceptions import PermissionDenied
    
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    """
    Only SUPERADMIN role can access.
    
    Use for: Payroll, system configuration, sensitive admin areas.
    
    Usage:
        @superadmin_required
        def payroll_dashboard(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or request.user.role != 'SUPERADMIN':
            messages.error(request, 'Access denied. This area is restricted to administrators only.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
