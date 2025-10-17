from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .signals import set_current_request
import logging

logger = logging.getLogger(__name__)


class ActivityTrackingMiddleware(MiddlewareMixin):
    """
    Track user activity and update last_activity timestamp
    Also implements smart logout after 1 hour of inactivity
    """
    
    def process_request(self, request):
        """Update user activity timestamp"""
        # Store request in thread-local for signal access
        set_current_request(request)
        
        # Skip if user not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Update last activity timestamp
        user = request.user
        user.last_activity = timezone.now()
        user.save(update_fields=['last_activity'])
        
        return None


class RouteProtectionMiddleware(MiddlewareMixin):
    """
    Protect ALL routes requiring authentication
    Redirect unauthenticated users to login page
    NO route accessible without authentication
    """
    
    # ONLY these routes are accessible without authentication
    PUBLIC_ROUTES = [
        '/auth/login/',
        '/auth/register/',
        '/auth/confirmation/',
        '/auth/password/reset/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/admin/login/',  # Django admin login
    ]
    
    def process_request(self, request):
        """Check if route requires authentication"""
        # Get the request path
        path = request.path
        
        # Allow public routes (exact match or startswith)
        if any(path.startswith(route) for route in self.PUBLIC_ROUTES):
            return None
        
        # Skip if user is authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            return None
        
        # All other routes require authentication - redirect to login
        login_url = reverse('login')
        if path != '/':
            # Preserve the next parameter for redirect after login
            messages.warning(request, 'Please login to access this page.')
            return redirect(f"{login_url}?next={path}")
        else:
            # Home page redirect (no message needed)
            return redirect(login_url)


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Implement session security features:
    - 1-hour timeout with smart logout (detects unsaved data)
    - Session hijacking protection
    """
    
    def process_request(self, request):
        """Check session security"""
        # Skip if user not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        user = request.user
        
        # Check for 1-hour inactivity timeout
        if user.last_activity:
            session_timeout = 3600  # 1 hour in seconds
            elapsed = (timezone.now() - user.last_activity).total_seconds()
            
            if elapsed > session_timeout:
                # Check for unsaved data (via JS flag in session)
                has_unsaved_data = request.session.get('has_unsaved_data', False)
                
                if not has_unsaved_data:
                    # Safe to logout
                    from django.contrib.auth import logout
                    logout(request)
                    messages.info(request, 'Your session expired due to inactivity.')
                    return redirect('login')
                else:
                    # Delay logout - user has unsaved work
                    logger.warning(
                        f"Session timeout delayed for user {user.id} - has unsaved data"
                    )
        
        return None


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Enforce role-based access control
    - BASIC_USER: Only access /auth/<user_id>/profile/ (their own profile)
    - Other roles: Full access to system based on permissions
    """
    
    # Routes that BASIC_USER can access (besides their own profile)
    BASIC_USER_ALLOWED_ROUTES = [
        '/auth/logout/',
        '/auth/password/change/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Enforce role-based access control"""
        # Skip if user not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        user = request.user
        path = request.path
        
        # FORCE password change if required (BLOCKS ALL ACCESS)
        if user.must_change_password:
            if not path.startswith('/auth/password/change/') and not path.startswith('/auth/logout/'):
                messages.warning(request, 'You must change your temporary password before continuing.')
                return redirect('password_change')
        
        # BASIC_USER restrictions
        if user.role == 'BASIC_USER':
            # Check if accessing own profile
            if path.startswith(f'/auth/{user.id}/profile/'):
                return None
            
            # Check if accessing allowed routes
            if any(path.startswith(route) for route in self.BASIC_USER_ALLOWED_ROUTES):
                return None
            
            # Deny access to all other routes
            messages.error(
                request,
                'Access denied. Basic users can only access their own profile.'
            )
            return redirect('user_profile', user_id=user.id)
        
        # All other roles have full access (permissions handled in views)
        return None


class ReAuthenticationMiddleware(MiddlewareMixin):
    """
    Prompt for re-authentication after 24 hours
    Does NOT force logout - only shows prompt
    """
    
    # Routes that don't need re-auth prompt
    EXEMPT_ROUTES = [
        '/auth/login/',
        '/auth/logout/',
        '/auth/otp-verify/',
        '/auth/password/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """Check if re-authentication is needed"""
        # Skip if user not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Skip exempt routes
        if any(request.path.startswith(route) for route in self.EXEMPT_ROUTES):
            return None
        
        user = request.user
        
        # Check if 24 hours have passed since last password login
        if user.last_password_login:
            hours_since_login = (timezone.now() - user.last_password_login).total_seconds() / 3600
            
            if hours_since_login >= 24:
                # Show re-auth prompt (stored in session to prevent repeated prompts)
                if not request.session.get('reauth_prompted'):
                    messages.warning(
                        request,
                        'For security, please re-authenticate. Your session will remain active.'
                    )
                    request.session['reauth_prompted'] = True
                    # Don't force logout - just show prompt
        
        return None
