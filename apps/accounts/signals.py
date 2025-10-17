from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from contextvars import ContextVar
from .models import User, UserProfileChange

# Context variable for request context (async-safe)
_current_request = ContextVar('current_request', default=None)


def set_current_request(request):
    """Store current request in context variable (async-safe)"""
    _current_request.set(request)


def get_current_request():
    """Retrieve current request from context variable"""
    return _current_request.get()


# Fields to track changes (excluding passwords and internal fields)
TRACKED_FIELDS = [
    'first_name', 'middle_names', 'last_name',
    'email', 'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
    'employee_id', 'national_id', 'position', 'department',
    'basic_salary', 'pay_per_day', 'overtime_rate',
    'commission_rate', 'sales_target',
    'employment_status', 'role',
    'current_loan_balance', 'current_advance_balance',
    'date_hired', 'date_terminated',
    'is_active', 'is_approved',
]


@receiver(pre_save, sender=User)
def track_user_profile_changes(sender, instance, **kwargs):
    """
    Track changes to user profile fields
    Creates UserProfileChange records for audit trail
    """
    # Skip tracking for new users
    if not instance.pk:
        return
    
    try:
        # Get old instance from database
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return
    
    # Get current request from thread-local storage
    request = get_current_request()
    changed_by = request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    
    # Track changes to monitored fields
    for field in TRACKED_FIELDS:
        old_value = getattr(old_instance, field)
        new_value = getattr(instance, field)
        
        # Only log if value changed
        if old_value != new_value:
            UserProfileChange.objects.create(
                user=instance,
                changed_by=changed_by or instance,  # Default to self if no request context
                field_name=field,
                old_value=str(old_value) if old_value is not None else '',
                new_value=str(new_value) if new_value is not None else '',
                ip_address=ip_address
            )
    
    # Send activation email when account is activated
    if not old_instance.is_active and instance.is_active:
        from apps.communications.services.email import EmailService
        login_url = request.build_absolute_uri('/auth/login/') if request else 'https://chesanto.com/auth/login/'
        EmailService.send_account_activated(
            email=instance.email,
            name=instance.get_full_name(),
            login_url=login_url,
            user=changed_by
        )


@receiver(pre_save, sender=User)
def auto_calculate_pay_per_day(sender, instance, **kwargs):
    """
    Auto-calculate pay_per_day when basic_salary changes
    Only for employees with payroll tracking (superadmins may not have payroll)
    """
    if instance.basic_salary and instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            # Only recalculate if basic_salary changed
            if old_instance.basic_salary != instance.basic_salary:
                instance.calculate_pay_per_day()
        except User.DoesNotExist:
            # New user - calculate on first save
            instance.calculate_pay_per_day()
    elif instance.basic_salary and not instance.pk:
        # New user with basic_salary
        instance.calculate_pay_per_day()


@receiver(post_save, sender='accounts.UserInvitation')
def create_user_from_invitation(sender, instance, created, **kwargs):
    """
    Auto-create user account when invitation is created
    - Creates ACTIVE user with temporary password
    - Sets must_change_password=True to force password change
    - Sends invitation email automatically
    - Works for invitations created via admin or invite view
    """
    if created and not instance.used_at:
        # Check if user already exists
        if User.objects.filter(email=instance.email).exists():
            return
        
        # Parse full name into first/last
        name_parts = instance.full_name.split(None, 1)
        first_name = name_parts[0] if name_parts else instance.full_name
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create user account
        User.objects.create_user(
            username=instance.email,
            email=instance.email,
            password=instance.temp_password,
            first_name=first_name,
            last_name=last_name,
            role=instance.role,
            is_active=True,
            is_approved=True,
            must_change_password=True
        )
        
        # Send invitation email automatically
        from apps.communications.services.email import EmailService
        from django.conf import settings
        login_url = f"{getattr(settings, 'SERVER_URL', 'http://localhost:8000')}/auth/login/"
        EmailService.send_invitation(
            email=instance.email,
            name=instance.full_name,
            role=instance.role,
            temp_password=instance.temp_password,
            login_url=login_url,
            invited_by=instance.invited_by
        )
