"""
Authentication Views for Chesanto Bakery Management System
Implements 8 core views for user authentication and profile management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import PermissionDenied
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from .models import User, UserInvitation, EmailOTP, UserProfileChange
from .utils import generate_otp, generate_temp_password, validate_otp
from apps.communications.services.email import EmailService


# ============================================================================
# CUSTOM DECORATORS
# ============================================================================

def anonymous_required(view_func):
    """Redirect authenticated users away from login/register"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You are already logged in.')
            return redirect('profile')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Only staff/superusers can access"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

@anonymous_required
def login_view(request):
    """
    Login view with email + password authentication
    - BASIC_USER can only access own profile: /auth/<user_id>/profile/
    - Other roles redirect to /profile/ (staff dashboard)
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'accounts/login.html')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Check if account is active
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Please contact an administrator.')
                return render(request, 'accounts/login.html')
            
            # Check if account is approved
            if not user.is_approved:
                messages.warning(request, 'Your account is still pending approval. Please wait for admin confirmation.')
                return redirect('account_confirmation', user_id=user.id)
            
            # Successful login
            login(request, user)
            
            messages.success(request, f'Welcome back, {user.first_name}!')
            
            # Check if user needs to change password (first login with temp password)
            if user.must_change_password:
                messages.warning(request, 'Please change your temporary password.')
                return redirect('password_change')
            
            # Role-based redirect
            if user.role == 'BASIC_USER':
                # Basic users go to their own profile
                return redirect('user_profile', user_id=user.id)
            else:
                # Staff/admin users go to next_url or profile dashboard
                next_url = request.GET.get('next', 'profile')
                return redirect(next_url)
        else:
            # Login failed
            messages.error(request, 'Invalid email or password.')
            return render(request, 'accounts/login.html')
    
    # GET request - show login form
    return render(request, 'accounts/login.html')


def logout_view(request):
    """
    Logout view - ends user session
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@anonymous_required
def register_view(request):
    """
    Self-registration view for BASIC_USER accounts
    - Auto-assigns role='BASIC_USER' (no role selection shown)
    - Account created INACTIVE, awaiting admin approval
    - Admin can approve as BASIC_USER or change role during approval
    - BASIC_USER permissions: View/modify own profile only
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        mobile_primary = request.POST.get('mobile_primary', '').strip()
        
        # Validation
        errors = []
        
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')
        
        if not password:
            errors.append('Password is required.')
        elif len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if not first_name or not last_name:
            errors.append('First and last name are required.')
        
        if not mobile_primary:
            errors.append('Primary mobile number is required.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/register.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'mobile_primary': mobile_primary
            })
        
        try:
            # Create BASIC_USER account (INACTIVE, awaiting admin approval)
            user = User.objects.create_user(
                username=email,  # Use email as username
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                mobile_primary=mobile_primary,
                role='BASIC_USER',  # Default role (admin can change during approval)
                is_approved=False,  # REQUIRES ADMIN APPROVAL
                is_active=False,    # INACTIVE until approved
                is_superuser=False,
                is_staff=False
            )
            
            # Send welcome email
            from apps.communications.services.email import EmailService
            EmailService.send_account_created(
                email=user.email,
                name=user.get_full_name(),
                user=user
            )
            
            # Redirect to confirmation check page (not login)
            messages.success(request, 'Registration successful! Your account is awaiting admin approval.')
            return redirect('account_confirmation', user_id=user.id)
                
        except Exception as e:
            # Handle any database errors gracefully
            messages.error(request, f'Registration failed: {str(e)}. Please try again or contact support.')
            return render(request, 'accounts/register.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'mobile_primary': mobile_primary
            })
    
    # GET request - show registration form
    return render(request, 'accounts/register.html')


def otp_verify_view(request):
    """
    OTP verification view
    - Verifies 6-digit OTP code
    - Max 3 attempts before code expires
    - 10-minute expiry
    """
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        
        if not code:
            messages.error(request, 'Please enter the 6-digit code.')
            return render(request, 'accounts/otp_verify.html')
        
        if len(code) != 6 or not code.isdigit():
            messages.error(request, 'Code must be exactly 6 digits.')
            return render(request, 'accounts/otp_verify.html')
        
        # Get user from session (set by previous view)
        user_id = request.session.get('otp_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please try again.')
            return redirect('login')
        
        user = get_object_or_404(User, id=user_id)
        
        # Get active OTP
        otp = EmailOTP.objects.filter(
            user=user,
            purpose='LOGIN',
            used_at__isnull=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            messages.error(request, 'No active OTP found. Please request a new code.')
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            return redirect('login')
        
        # Check attempts
        if otp.attempts >= 3:
            otp.used_at = timezone.now()
            otp.save()
            messages.error(request, 'Too many failed attempts. Please request a new code.')
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            return redirect('login')
        
        # Verify code using utility function
        if validate_otp(user, code, purpose='LOGIN'):
            # Success
            login(request, user)
            
            # Clean up session
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            
            messages.success(request, 'Code verified successfully!')
            return redirect('profile')
        else:
            # Failed attempt
            otp.attempts += 1
            otp.save()
            
            attempts_left = 3 - otp.attempts
            messages.error(request, f'Invalid code. {attempts_left} attempt(s) remaining.')
            
            return render(request, 'accounts/otp_verify.html')
    
    # GET request
    return render(request, 'accounts/otp_verify.html')


@login_required
def password_change_view(request):
    """
    Password change view
    - Forces change on first login (temp password)
    - Validates old password
    - Requires password confirmation
    """
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not old_password:
            errors.append('Current password is required.')
        elif not request.user.check_password(old_password):
            errors.append('Current password is incorrect.')
        
        if not new_password:
            errors.append('New password is required.')
        elif len(new_password) < 8:
            errors.append('New password must be at least 8 characters long.')
        
        if new_password != confirm_password:
            errors.append('New passwords do not match.')
        
        if old_password and new_password and old_password == new_password:
            errors.append('New password must be different from current password.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/password_change.html')
        
        # Change password
        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save()
        
        # Mark invitation as used (if exists)
        try:
            invitation = UserInvitation.objects.filter(
                email=request.user.email,
                used_at__isnull=True
            ).first()
            if invitation:
                invitation.used_at = timezone.now()
                invitation.save()
        except Exception:
            pass  # Silently fail if invitation tracking fails
        
        # Re-authenticate to maintain session
        login(request, request.user)
        
        messages.success(request, 'Password changed successfully!')
        return redirect('profile')
    
    # GET request
    return render(request, 'accounts/password_change.html')


@anonymous_required
def password_reset_request_view(request):
    """
    Password reset request view
    - User enters email
    - Generates 6-digit code
    - Sends code via email
    - 15-minute expiry
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if user exists (security)
            messages.success(request, 'If an account exists with this email, you will receive a password reset code.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Generate reset code using OTP system
        code = generate_otp(user, purpose='PASSWORD_RESET')
        
        # Send email
        try:
            EmailService.send_password_reset(
                email=user.email,
                code=code,
                user=user
            )
        except Exception as e:
            messages.error(request, 'Failed to send reset code. Please try again.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Store user_id in session for verify step
        request.session['reset_user_id'] = user.id
        request.session['reset_timestamp'] = timezone.now().isoformat()
        
        messages.success(request, 'A password reset code has been sent to your email.')
        return redirect('password_reset_verify')
    
    # GET request
    return render(request, 'accounts/password_reset_request.html')


@anonymous_required
def password_reset_verify_view(request):
    """
    Password reset verification view
    - User enters 6-digit code + new password
    - Validates code
    - Sets new password
    """
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not code:
            errors.append('Reset code is required.')
        elif len(code) != 6 or not code.isdigit():
            errors.append('Code must be exactly 6 digits.')
        
        if not new_password:
            errors.append('New password is required.')
        elif len(new_password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if new_password != confirm_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/password_reset_verify.html')
        
        # Get user from session
        user_id = request.session.get('reset_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please request a new reset code.')
            return redirect('password_reset_request')
        
        # Check session timeout (15 minutes)
        reset_timestamp = request.session.get('reset_timestamp')
        if reset_timestamp:
            from django.utils.dateparse import parse_datetime
            reset_time = parse_datetime(reset_timestamp)
            if reset_time and (timezone.now() - reset_time).seconds > 900:  # 15 minutes
                messages.error(request, 'Session expired. Please request a new reset code.')
                if 'reset_user_id' in request.session:
                    del request.session['reset_user_id']
                if 'reset_timestamp' in request.session:
                    del request.session['reset_timestamp']
                return redirect('password_reset_request')
        
        user = get_object_or_404(User, id=user_id)
        
        # Find valid OTP
        otp = EmailOTP.objects.filter(
            user=user,
            purpose='PASSWORD_RESET',
            used_at__isnull=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            messages.error(request, 'Invalid or expired reset code. Please request a new one.')
            # Don't log failed attempts - user might just be confused
            return render(request, 'accounts/password_reset_verify.html')
        
        # Validate OTP code
        if not validate_otp(user, code, purpose='PASSWORD_RESET'):
            messages.error(request, 'Invalid or expired reset code. Please request a new one.')
            return render(request, 'accounts/password_reset_verify.html')
        
        # Reset password
        user.set_password(new_password)
        user.must_change_password = False
        user.save()
        
        # Mark OTP as used
        otp.used_at = timezone.now()
        otp.save()
        
        # Clean up session
        if 'reset_user_id' in request.session:
            del request.session['reset_user_id']
        if 'reset_timestamp' in request.session:
            del request.session['reset_timestamp']
        
        messages.success(request, 'Password reset successfully! You can now log in.')
        return redirect('login')
    
    # GET request
    return render(request, 'accounts/password_reset_verify.html')


# ============================================================================
# PROFILE VIEWS
# ============================================================================

@login_required
def profile_view(request):
    """
    View user profile
    - Displays all user information
    - Shows profile photo
    - Link to edit profile
    """
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })


@login_required
def profile_edit_view(request, user_id=None):
    """
    Edit user profile
    - Tracks changes in UserProfileChange model
    - Updates user information
    - Handles profile photo upload with focal point
    - Enforces SUPERADMIN protection rules
    
    Safeguards:
    - Primary SUPERADMIN cannot be edited by anyone except themselves
    - SUPERADMINs can only edit themselves, not other SUPERADMINs
    - Regular users can only edit their own profiles (limited fields)
    """
    # Determine which user to edit
    if user_id:
        # Editing another user's profile (admin function)
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('profile')
        
        # Check permission to edit this user
        if not request.user.can_edit_user(target_user):
            messages.error(request, 'You do not have permission to edit this user.')
            return redirect('profile')
    else:
        # Editing own profile
        target_user = request.user
    
    if request.method == 'POST':
        # Track changes
        changes = {}
        
        # Determine which fields can be updated based on permissions
        if request.user.role == 'SUPERADMIN' and target_user.id == request.user.id:
            # SUPERADMIN editing their own profile - all fields
            fields_to_update = [
                'first_name', 'last_name', 'middle_names',
                'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
                'national_id', 'employee_id',
                'position', 'department'
            ]
        elif request.user.role == 'SUPERADMIN' and target_user.id != request.user.id:
            # SUPERADMIN editing another non-SUPERADMIN user - all fields
            fields_to_update = [
                'first_name', 'last_name', 'middle_names',
                'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
                'national_id', 'employee_id',
                'position', 'department'
            ]
        else:
            # Regular user editing their own profile - limited fields only
            fields_to_update = ['mobile_secondary', 'mobile_tertiary']
        
        for field in fields_to_update:
            new_value = request.POST.get(field, '').strip()
            old_value = str(getattr(target_user, field, '') or '')
            
            if new_value != old_value:
                changes[field] = {'old': old_value, 'new': new_value}
                setattr(target_user, field, new_value if new_value else None)
        
        # Handle profile photo (users can always update their own photo)
        if 'profile_photo' in request.FILES:
            old_photo = target_user.profile_photo.name if target_user.profile_photo else None
            target_user.profile_photo = request.FILES['profile_photo']
            target_user.photo_uploaded_at = timezone.now()
            target_user.photo_uploaded_by = request.user
            changes['profile_photo'] = {'old': old_photo, 'new': 'Updated'}
        
        # Handle photo focal point (for drag-to-fit feature)
        if 'photo_center_x' in request.POST and 'photo_center_y' in request.POST:
            try:
                new_x = Decimal(request.POST.get('photo_center_x', '50.00'))
                new_y = Decimal(request.POST.get('photo_center_y', '50.00'))
                target_user.photo_center_x = new_x
                target_user.photo_center_y = new_y
            except (ValueError, TypeError):
                pass  # Keep default values
        
        # Save user
        target_user.save()
        
        # Log changes
        if changes:
            for field, change in changes.items():
                UserProfileChange.objects.create(
                    user=target_user,
                    changed_by=request.user,
                    field_name=field,
                    old_value=str(change['old']),
                    new_value=str(change['new'])
                )
        
        messages.success(request, 'Profile updated successfully!')
        if target_user.id == request.user.id:
            return redirect('profile')
        else:
            return redirect('user_profile', user_id=target_user.id)
    
    # GET request
    return render(request, 'accounts/profile_edit.html', {
        'user': target_user,
        'is_editing_self': target_user.id == request.user.id
    })


@login_required
def profile_changes_view(request):
    """
    View profile change history
    - Shows all changes made to user profile
    - Displays old and new values
    """
    changes = UserProfileChange.objects.filter(
        user=request.user
    ).order_by('-changed_at')[:50]  # Last 50 changes
    
    return render(request, 'accounts/profile_changes.html', {
        'changes': changes
    })


@login_required
def user_profile_view(request, user_id):
    """
    User-specific profile view
    - BASIC_USER can only access their own profile (user_id must match request.user.id)
    - SUPERADMIN can access any user's profile
    - Other roles are denied access
    """
    try:
        profile_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')
    
    # Access control
    if request.user.role == 'BASIC_USER':
        # Basic users can only view their own profile
        if request.user.id != user_id:
            messages.error(request, 'Access denied. You can only view your own profile.')
            return redirect('user_profile', user_id=request.user.id)
    elif request.user.role == 'SUPERADMIN':
        # Superadmin can view any profile
        pass
    else:
        # Other roles cannot access user-specific profiles
        messages.error(request, 'Access denied. Please use the staff dashboard.')
        return redirect('profile')
    
    # Render profile
    return render(request, 'accounts/user_profile.html', {
        'profile_user': profile_user,
        'is_own_profile': request.user.id == user_id,
        'can_edit': request.user.id == user_id or request.user.role == 'SUPERADMIN'
    })


@anonymous_required
def account_confirmation_view(request, user_id):
    """
    Account confirmation check page
    - Shows pending approval status
    - Auto-checks if account is approved
    - If approved, redirects to login
    - If still pending, shows waiting message with refresh option
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('register')
    
    # Check if account is approved
    if user.is_active and user.is_approved:
        messages.success(request, f'Your account has been approved! You can now log in as {user.get_role_display()}.')
        return redirect('login')
    
    # Still pending
    return render(request, 'accounts/account_confirmation.html', {
        'user': user,
        'email': user.email,
        'registered_at': user.date_joined
    })
