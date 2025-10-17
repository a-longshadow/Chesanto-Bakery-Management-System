import os
import random
import string
import secrets
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta


def is_superadmin_email(email):
    """
    Check if email is in SUPERADMIN_EMAILS environment variable
    Returns True if email should get auto-approved superadmin access
    """
    superadmin_emails = os.getenv('SUPERADMIN_EMAILS', '').split(',')
    normalized_email = email.strip().lower()
    
    for admin_email in superadmin_emails:
        if admin_email.strip().lower() == normalized_email:
            return True
    
    return False


def generate_temp_password(length=8):
    """
    Generate random temporary password for invited users
    
    Format: 8 characters with uppercase, lowercase, digits (e.g., "Kx9mP2vL")
    Note: Random, not predictable like "Temp1234!"
    
    Returns:
        str: Random temporary password
    """
    # Ensure at least one of each type
    password_chars = [
        random.choice(string.ascii_uppercase),  # At least 1 uppercase
        random.choice(string.ascii_lowercase),  # At least 1 lowercase
        random.choice(string.digits),           # At least 1 digit
    ]
    
    # Fill the rest with random mix
    remaining_length = length - len(password_chars)
    all_chars = string.ascii_letters + string.digits
    password_chars.extend(random.choices(all_chars, k=remaining_length))
    
    # Shuffle to avoid predictable pattern
    random.shuffle(password_chars)
    
    return ''.join(password_chars)


def generate_otp(user, purpose='LOGIN'):
    """
    Generate 6-digit OTP code and save to database
    
    Args:
        user: User object
        purpose: 'LOGIN' or 'PASSWORD_RESET'
    
    Returns:
        str: 6-digit OTP code (plaintext)
    """
    from .models import EmailOTP
    
    # Generate 6-digit code
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Determine validity period
    if purpose == EmailOTP.Purpose.LOGIN:
        validity_seconds = int(os.getenv('OTP_CODE_VALIDITY', 600))  # Default: 10 minutes
    else:  # PASSWORD_RESET
        validity_seconds = int(os.getenv('PASSWORD_RESET_CODE_VALIDITY', 900))  # Default: 15 minutes
    
    # Create OTP record
    otp = EmailOTP.objects.create(
        user=user,
        code_hash=make_password(code),  # Hash the code for security
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=validity_seconds)
    )
    
    return code  # Return plaintext code to send via email


def validate_otp(user, code, purpose='LOGIN'):
    """
    Validate OTP code against database
    
    Args:
        user: User object
        code: 6-digit OTP code to validate
        purpose: 'LOGIN' or 'PASSWORD_RESET'
    
    Returns:
        bool: True if valid, False if invalid/expired/too many attempts
    """
    from .models import EmailOTP
    
    # Find most recent valid OTP for this user and purpose
    otp = EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
        expires_at__gt=timezone.now()
    ).order_by('-created_at').first()
    
    if not otp:
        return False
    
    # Check attempt limit (max 3 attempts)
    if otp.attempts >= 3:
        return False
    
    # Increment attempt counter
    otp.attempts += 1
    otp.save()
    
    # Validate code
    if check_password(code, otp.code_hash):
        # Mark as used
        otp.used_at = timezone.now()
        otp.save()
        return True
    
    return False


def requires_reauth(user):
    """
    Check if user needs to re-authenticate (24-hour rule)
    
    Args:
        user: User object
    
    Returns:
        bool: True if re-auth needed, False otherwise
    """
    if not user.last_password_login:
        return True
    
    re_auth_interval = int(os.getenv('RE_AUTH_INTERVAL', 86400))  # Default: 24 hours
    elapsed = timezone.now() - user.last_password_login
    
    return elapsed.total_seconds() >= re_auth_interval


def generate_email_verification_token(user, email):
    """
    Generate email verification token
    
    Args:
        user: User object
        email: Email to verify
    
    Returns:
        EmailVerificationToken: Token object
    """
    from .models import EmailVerificationToken
    
    # Generate secure random token
    token = secrets.token_urlsafe(32)
    
    # Create token record (valid for 24 hours)
    verification = EmailVerificationToken.objects.create(
        user=user,
        email=email,
        token=token,
        expires_at=timezone.now() + timedelta(hours=24)
    )
    
    return verification


def verify_email_token(token):
    """
    Verify email verification token
    
    Args:
        token: Token string
    
    Returns:
        tuple: (success: bool, user: User or None, error_message: str or None)
    """
    from .models import EmailVerificationToken
    
    try:
        verification = EmailVerificationToken.objects.get(token=token)
        
        # Check if already verified
        if verification.verified_at:
            return False, None, 'This verification link has already been used'
        
        # Check if expired
        if timezone.now() > verification.expires_at:
            return False, None, 'This verification link has expired'
        
        # Mark as verified
        verification.verified_at = timezone.now()
        verification.save()
        
        # Update user
        user = verification.user
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save()
        
        return True, user, None
        
    except EmailVerificationToken.DoesNotExist:
        return False, None, 'Invalid verification link'


def get_role_permissions(role):
    """
    Get permission level for a role (for display purposes)
    
    Args:
        role: Role string (from User.Role choices)
    
    Returns:
        dict: Permission info
    """
    permissions = {
        'SUPERADMIN': {
            'level': 100,
            'title': 'CEO / Developer',
            'description': 'Full system access',
            'can_manage_users': True,
            'can_view_all_logs': True,
        },
        'ADMIN': {
            'level': 90,
            'title': 'Accountant',
            'description': 'Financial data, reports, user management',
            'can_manage_users': True,
            'can_view_all_logs': True,
        },
        'PRODUCT_MANAGER': {
            'level': 70,
            'title': 'Production Manager',
            'description': 'Production, inventory, recipes, reports',
            'can_manage_users': False,
            'can_view_all_logs': False,
        },
        'DEPT_HEAD': {
            'level': 60,
            'title': 'Department Head',
            'description': 'Team data, department reports',
            'can_manage_users': False,
            'can_view_all_logs': False,
        },
        'DISPATCH': {
            'level': 40,
            'title': 'Dispatch Officer',
            'description': 'Crate tracking, deliveries, dispatch reports',
            'can_manage_users': False,
            'can_view_all_logs': False,
        },
        'SALESMAN': {
            'level': 30,
            'title': 'Sales Representative',
            'description': 'Sales entry, customer data, own reports',
            'can_manage_users': False,
            'can_view_all_logs': False,
        },
        'SECURITY': {
            'level': 20,
            'title': 'Gate Man / Security',
            'description': 'Entry/exit logs, visitor records',
            'can_manage_users': False,
            'can_view_all_logs': False,
        },
    }
    
    return permissions.get(role, {})


def can_user_manage_role(user_role, target_role):
    """
    Check if a user with user_role can manage/modify users with target_role
    
    Rules:
    - SUPERADMIN can manage all roles except other SUPERADMIN
    - ADMIN can manage all roles except SUPERADMIN and other ADMIN
    - Others cannot manage users
    
    Args:
        user_role: Role of the user trying to manage
        target_role: Role of the target user
    
    Returns:
        bool: True if allowed, False otherwise
    """
    if user_role == 'SUPERADMIN':
        # Superadmin can manage all roles except other superadmins
        return target_role != 'SUPERADMIN'
    
    if user_role == 'ADMIN':
        # Admin can manage all except superadmin and other admins
        return target_role not in ['SUPERADMIN', 'ADMIN']
    
    # Other roles cannot manage users
    return False
