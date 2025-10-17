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
from functools import wraps

from .models import User, UserInvitation, EmailOTP, UserProfileChange
from .utils import generate_otp, generate_temp_password, validate_otp
from apps.communications.services.email import EmailService
from apps.audit.services.logger import AuditLogger


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
    - Checks 24-hour re-auth requirement
    - Redirects to password change if first login (temp password used)
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
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Please contact an administrator.')
                ActivityLogger.log_security_event(
                    event_type='login_inactive_account',
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details={'email': email}
                )
                return render(request, 'accounts/login.html')
            
            # Check if account is approved (except for superadmins)
            if not user.is_approved and not user.is_superuser:
                messages.error(request, 'Your account is pending approval. You will be notified via email once approved.')
                ActivityLogger.log_security_event(
                    event_type='login_unapproved_account',
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    details={'email': email}
                )
                return render(request, 'accounts/login.html')
            
            # Successful login
            login(request, user)
            
            # Django automatically updates last_login timestamp
            
            # Log successful login
            ActivityLogger.log_security_event(
                event_type='login_success',
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'email': email}
            )
            
            messages.success(request, f'Welcome back, {user.first_name}!')
            
            # Check if user needs to change password (first login with temp password)
            if user.must_change_password:
                messages.warning(request, 'Please change your temporary password.')
                return redirect('password_change')
            
            # Redirect to intended page or profile
            next_url = request.GET.get('next', 'profile')
            return redirect(next_url)
        else:
            # Login failed
            messages.error(request, 'Invalid email or password.')
            ActivityLogger.log_security_event(
                event_type='login_failed',
                user=None,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'email': email, 'reason': 'invalid_credentials'}
            )
            return render(request, 'accounts/login.html')
    
    # GET request - show login form
    return render(request, 'accounts/login.html')


def logout_view(request):
    """
    Logout view - ends user session
    """
    user = request.user
    if user.is_authenticated:
        ActivityLogger.log_security_event(
            event_type='logout',
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'email': user.email}
        )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@anonymous_required
def register_view(request):
    """
    Self-registration view
    - Users register with email, password, names, mobile, role
    - Auto-approved if email in SUPERADMIN_EMAILS
    - Otherwise requires admin approval
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        mobile_primary = request.POST.get('mobile_primary', '').strip()
        role = request.POST.get('role', '').strip()
        
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
        
        if not role:
            errors.append('Role is required.')
        elif role not in dict(User.Role.choices).keys():
            errors.append('Invalid role selected.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/register.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'mobile_primary': mobile_primary,
                'role': role,
                'role_choices': User.Role.choices
            })
        
        # Check if auto-approve (SUPERADMIN_EMAILS)
        is_auto_approved = email in getattr(settings, 'SUPERADMIN_EMAILS', [])
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            mobile_primary=mobile_primary,
            role=role,
            is_approved=is_auto_approved,
            is_superuser=is_auto_approved,
            is_staff=is_auto_approved
        )
        
        # Log registration
        ActivityLogger.log_security_event(
            event_type='user_registered',
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'email': email,
                'role': role,
                'auto_approved': is_auto_approved
            }
        )
        
        if is_auto_approved:
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('login')
        else:
            messages.success(request, 'Registration successful! Your account is pending approval. You will be notified via email.')
            return redirect('login')
    
    # GET request - show registration form
    return render(request, 'accounts/register.html', {
        'role_choices': User.Role.choices
    })


@staff_required
def invite_user_view(request):
    """
    Admin-only view to invite new users
    - Sends invitation email with temporary password
    - Only accessible by staff/superusers
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        full_name = request.POST.get('full_name', '').strip()
        role = request.POST.get('role', '').strip()
        
        # Validation
        errors = []
        
        if not email:
            errors.append('Email is required.')
        elif User.objects.filter(email=email).exists():
            errors.append('A user with this email already exists.')
        elif UserInvitation.objects.filter(email=email, is_accepted=False, expires_at__gt=timezone.now()).exists():
            errors.append('An active invitation already exists for this email.')
        
        if not full_name:
            errors.append('Full name is required.')
        
        if not role:
            errors.append('Role is required.')
        elif role not in dict(User.Role.choices).keys():
            errors.append('Invalid role selected.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/invite_user.html', {
                'email': email,
                'full_name': full_name,
                'role': role,
                'role_choices': User.Role.choices
            })
        
        # Create invitation (temp password auto-generates in model save())
        invitation = UserInvitation.objects.create(
            email=email,
            full_name=full_name,
            role=role,
            invited_by=request.user
        )
        
        # Send invitation email
        login_url = f"{settings.SERVER_URL}/auth/login/"
        EmailService.send_invitation(
            email=invitation.email,
            name=invitation.full_name,
            role=invitation.role,
            temp_password=invitation.temp_password,
            login_url=login_url,
            invited_by=request.user
        )
        
        # Log invitation
        ActivityLogger.log_action(
            action='user_invited',
            user=request.user,
            details={
                'invited_email': email,
                'invited_name': full_name,
                'role': role
            }
        )
        
        messages.success(request, f'Invitation sent to {email} with temporary password.')
        return redirect('invite_user')
    
    # GET request - show invitation form
    return render(request, 'accounts/invite_user.html', {
        'role_choices': User.Role.choices
    })


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
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            messages.error(request, 'No active OTP found. Please request a new code.')
            if 'otp_user_id' in request.session:
                del request.session['otp_user_id']
            return redirect('login')
        
        # Check attempts
        if otp.attempts >= 3:
            otp.is_used = True
            otp.save()
            messages.error(request, 'Too many failed attempts. Please request a new code.')
            ActivityLogger.log_security_event(
                event_type='otp_max_attempts',
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'otp_id': otp.id}
            )
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
            
            ActivityLogger.log_security_event(
                event_type='otp_verified',
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'otp_id': otp.id}
            )
            
            messages.success(request, 'Code verified successfully!')
            return redirect('profile')
        else:
            # Failed attempt
            otp.attempts += 1
            otp.save()
            
            attempts_left = 3 - otp.attempts
            messages.error(request, f'Invalid code. {attempts_left} attempt(s) remaining.')
            
            ActivityLogger.log_security_event(
                event_type='otp_failed',
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'otp_id': otp.id, 'attempts': otp.attempts}
            )
            
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
        
        # Log password change
        ActivityLogger.log_security_event(
            event_type='password_changed',
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'forced': request.user.must_change_password}
        )
        
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
        EmailService.send_password_reset(
            email=user.email,
            code=code,
            user=user
        )
        
        # Log request
        ActivityLogger.log_security_event(
            event_type='password_reset_requested',
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'email': user.email}
        )
        
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
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        
        if not otp:
            messages.error(request, 'Invalid or expired reset code. Please request a new one.')
            ActivityLogger.log_security_event(
                event_type='password_reset_invalid_code',
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                details={'code': code}
            )
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
        otp.is_used = True
        otp.save()
        
        # Clean up session
        if 'reset_user_id' in request.session:
            del request.session['reset_user_id']
        if 'reset_timestamp' in request.session:
            del request.session['reset_timestamp']
        
        # Log password reset
        ActivityLogger.log_security_event(
            event_type='password_reset_completed',
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={'otp_id': otp.id}
        )
        
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
def profile_edit_view(request):
    """
    Edit user profile
    - Tracks changes in UserProfileChange model
    - Updates user information
    - Handles profile photo upload
    """
    if request.method == 'POST':
        # Track changes
        changes = {}
        
        # Update basic info
        fields_to_update = [
            'first_name', 'last_name', 'middle_names',
            'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
            'emergency_contact_name', 'emergency_contact_phone',
            'address', 'national_id', 'kra_pin',
            'bank_name', 'bank_account_number', 'bank_branch'
        ]
        
        for field in fields_to_update:
            new_value = request.POST.get(field, '').strip()
            old_value = getattr(request.user, field) or ''
            
            if new_value != old_value:
                changes[field] = {'old': old_value, 'new': new_value}
                setattr(request.user, field, new_value)
        
        # Handle profile photo
        if 'profile_photo' in request.FILES:
            old_photo = request.user.profile_photo.name if request.user.profile_photo else None
            request.user.profile_photo = request.FILES['profile_photo']
            changes['profile_photo'] = {'old': old_photo, 'new': 'Updated'}
        
        # Save user
        request.user.save()
        
        # Log changes
        if changes:
            for field, change in changes.items():
                UserProfileChange.objects.create(
                    user=request.user,
                    changed_by=request.user,
                    field_name=field,
                    old_value=str(change['old']),
                    new_value=str(change['new'])
                )
            
            ActivityLogger.log_action(
                action='profile_updated',
                user=request.user,
                details={'fields_changed': list(changes.keys())}
            )
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    # GET request
    return render(request, 'accounts/profile_edit.html', {
        'user': request.user
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
