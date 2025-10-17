from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta
from apps.core.validators import phone_validator, validate_kenyan_national_id, validate_file_size


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('role', 'SUPERADMIN')
        extra_fields.setdefault('must_change_password', False)  # Superusers choose their own password
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Enhanced User model with payroll tracking integration
    Extends Django's AbstractUser with Chesanto-specific fields
    """
    
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'CEO / Developer'
        ADMIN = 'ADMIN', 'Accountant'
        PRODUCT_MANAGER = 'PRODUCT_MANAGER', 'Production Manager'
        DEPT_HEAD = 'DEPT_HEAD', 'Department Head'
        DISPATCH = 'DISPATCH', 'Dispatch Officer'
        SALESMAN = 'SALESMAN', 'Sales Representative'
        SECURITY = 'SECURITY', 'Gate Man / Security'
        BASIC_USER = 'BASIC_USER', 'Basic User (Self-Registered)'
    
    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        TERMINATED = 'TERMINATED', 'Terminated'
    
    # Override username (make it optional, use email as primary identifier)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    
    # ========== EMAIL (VERIFIED, REQUIRED) ==========
    email = models.EmailField(unique=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # ========== NAME FIELDS (ENHANCED) ==========
    first_name = models.CharField(max_length=100, help_text="Required")
    middle_names = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional. Multiple middle names separated by spaces"
    )
    last_name = models.CharField(max_length=100, help_text="Required")
    
    # ========== MOBILE NUMBERS (UP TO 3) ==========
    mobile_primary = models.CharField(
        max_length=15,
        validators=[phone_validator],
        help_text="Primary contact (+254XXXXXXXXX or 07XXXXXXXX)"
    )
    mobile_secondary = models.CharField(
        max_length=15,
        blank=True,
        validators=[phone_validator],
        help_text="Secondary contact (optional)"
    )
    mobile_tertiary = models.CharField(
        max_length=15,
        blank=True,
        validators=[phone_validator],
        help_text="Tertiary contact (optional)"
    )
    
    # ========== PROFILE PHOTO (MAX 5MB) ==========
    profile_photo = models.ImageField(
        upload_to='profiles/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Max 5MB. Supported: JPG, PNG"
    )
    photo_uploaded_at = models.DateTimeField(null=True, blank=True)
    photo_uploaded_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='photos_uploaded'
    )
    photo_center_x = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Horizontal center (0-100%)"
    )
    photo_center_y = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Vertical center (0-100%)"
    )
    
    # ========== EMPLOYEE/PAYROLL TRACKING ==========
    # Note: Payroll fields are OPTIONAL - only for actual employees with payroll tracking
    # Superadmins (CEO/Developer) may not have these fields filled
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="e.g., CHE001, CHE028 (optional - only for employees with payroll)"
    )
    national_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_kenyan_national_id],
        help_text="National ID (7-8 digits) - optional for superadmins"
    )
    position = models.CharField(max_length=100, blank=True, help_text="Job title")
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Production, Sales, Dispatch, etc."
    )
    
    # Salary TRACKING (for expense calculations, NOT payment processing)
    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly basic salary (KES) - tracked for expense calculations"
    )
    pay_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Auto-calculated: basic_salary / 30"
    )
    overtime_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Per mix for production staff (KES)"
    )
    
    # Commission TRACKING (for Salesmen)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('7.00'),
        help_text="% above target (default: 7%)"
    )
    sales_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('35000.00'),
        help_text="Monthly sales target (KES)"
    )
    
    # Employment Dates
    date_hired = models.DateField(null=True, blank=True)
    date_terminated = models.DateField(null=True, blank=True)
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
        db_index=True
    )
    
    # Loan/Advance TRACKING (like petty cash)
    current_loan_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Outstanding loan (KES) - tracked for monthly expenses"
    )
    current_advance_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Advance payment balance (KES)"
    )
    
    # ========== ROLE & PERMISSIONS ==========
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    is_primary_superadmin = models.BooleanField(
        default=False,
        help_text="Reserved for the first/primary SUPERADMIN (CEO/System Owner). Cannot be modified by other admins."
    )
    must_change_password = models.BooleanField(default=False)
    last_password_login = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    custom_permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom permissions set by superadmin"
    )
    
    # ========== AUDIT FIELDS ==========
    created_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_created'
    )
    updated_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'mobile_primary']
    
    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
            models.Index(fields=['employment_status']),
            models.Index(fields=['is_active', 'is_approved']),
        ]
    
    def __str__(self):
        return self.get_full_name()
    
    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username:
            self.username = self.email.split('@')[0]
        
        # Auto-calculate pay_per_day
        if self.basic_salary and not self.pay_per_day:
            self.calculate_pay_per_day()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate model before saving"""
        # Validate photo size (max 5MB)
        if self.profile_photo:
            try:
                validate_file_size(self.profile_photo)
            except ValidationError as e:
                raise ValidationError({'profile_photo': e.message})
    
    def get_full_name(self):
        """Return full name including middle names"""
        parts = [self.first_name]
        if self.middle_names:
            parts.append(self.middle_names)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    def get_display_name(self):
        """Return first and last name only"""
        return f"{self.first_name} {self.last_name}"
    
    def get_all_mobile_numbers(self):
        """Return list of all mobile numbers"""
        numbers = [self.mobile_primary]
        if self.mobile_secondary:
            numbers.append(self.mobile_secondary)
        if self.mobile_tertiary:
            numbers.append(self.mobile_tertiary)
        return numbers
    
    def calculate_pay_per_day(self):
        """Calculate daily pay from basic salary (30 days/month)"""
        if self.basic_salary:
            self.pay_per_day = self.basic_salary / Decimal('30')
            return self.pay_per_day
        return None
    
    def get_profile_photo_url(self):
        """Return profile photo URL or default avatar"""
        if self.profile_photo:
            return self.profile_photo.url
        return '/static/images/default-avatar.png'
    
    def requires_reauth(self):
        """Check if 24-hour re-authentication is needed"""
        if not self.last_password_login:
            return True
        elapsed = timezone.now() - self.last_password_login
        return elapsed.total_seconds() >= 86400  # 24 hours
    
    def can_edit_user(self, target_user):
        """
        Check if this user can edit the target user's profile
        
        Safeguards:
        1. Primary SUPERADMIN cannot be edited by anyone except themselves
        2. SUPERADMINs can only edit themselves, not other SUPERADMINs
        3. Regular users can only edit their own profiles
        
        Args:
            target_user: User object to be edited
            
        Returns:
            bool: True if allowed, False otherwise
        """
        # Users can always edit their own profiles
        if self.id == target_user.id:
            return True
        
        # Primary SUPERADMIN cannot be edited by anyone else
        if target_user.is_primary_superadmin:
            return False
        
        # SUPERADMINs cannot edit other SUPERADMINs
        if self.role == 'SUPERADMIN' and target_user.role == 'SUPERADMIN':
            return False
        
        # SUPERADMIN can edit non-SUPERADMIN users
        if self.role == 'SUPERADMIN':
            return True
        
        # Regular users cannot edit other users
        return False
    
    def can_delete_user(self, target_user):
        """
        Check if this user can delete the target user
        
        Safeguards:
        1. No one can delete a Primary SUPERADMIN
        2. SUPERADMINs cannot delete other SUPERADMINs
        3. Users cannot delete themselves
        4. Only SUPERADMINs can delete users
        
        Args:
            target_user: User object to be deleted
            
        Returns:
            bool: True if allowed, False otherwise
        """
        # Cannot delete yourself
        if self.id == target_user.id:
            return False
        
        # Cannot delete Primary SUPERADMIN
        if target_user.is_primary_superadmin:
            return False
        
        # SUPERADMINs cannot delete other SUPERADMINs
        if self.role == 'SUPERADMIN' and target_user.role == 'SUPERADMIN':
            return False
        
        # Only SUPERADMINs can delete users
        return self.role == 'SUPERADMIN'


class UserInvitation(models.Model):
    """Track user invitations sent by admin"""
    email = models.EmailField(db_index=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=User.Role.choices)
    temp_password = models.CharField(max_length=128, blank=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invitations_sent'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        help_text="Invitation expiry (default: 7 days from creation)"
    )
    
    def save(self, *args, **kwargs):
        """Auto-set expires_at and temp_password if not provided"""
        from apps.accounts.utils import generate_temp_password
        
        # Auto-generate temp password if not provided
        if not self.temp_password:
            self.temp_password = generate_temp_password(length=12)
        
        # Auto-set expiry to 7 days from now if not provided
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
            
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'accounts_user_invitation'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Invitation to {self.email}"
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return not self.used_at and timezone.now() < self.expires_at


class EmailOTP(models.Model):
    """Email-based OTP codes for authentication and password reset"""
    
    class Purpose(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'accounts_email_otp'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'purpose', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (
            not self.used_at and 
            self.attempts < 3 and 
            timezone.now() < self.expires_at
        )


class UserProfileChange(models.Model):
    """Track all changes to user profiles"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_changes')
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='profile_changes_made'
    )
    field_name = models.CharField(max_length=100, db_index=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    change_reason = models.TextField(blank=True, help_text="Optional reason")
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'accounts_user_profile_change'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['user', '-changed_at']),
            models.Index(fields=['changed_by']),
            models.Index(fields=['field_name']),
        ]
    
    def __str__(self):
        changed_by_name = self.changed_by.get_display_name() if self.changed_by else 'System'
        return f"{self.user.get_display_name()} - {self.field_name} changed by {changed_by_name}"


class EmailVerificationToken(models.Model):
    """Email verification tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'accounts_email_verification_token'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'email']),
        ]
    
    def __str__(self):
        return f"Email verification for {self.email}"
    
    def is_valid(self):
        """Check if token is still valid"""
        return not self.verified_at and timezone.now() < self.expires_at
