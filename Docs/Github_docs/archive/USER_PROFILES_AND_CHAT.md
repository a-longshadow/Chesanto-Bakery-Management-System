# User Profiles & In-App Chat - Complete Specification
**Project:** Chesanto Bakery Management System  
**Date:** October 16, 2025  
**Status:** ✅ APPROVED ENHANCEMENT  
**Priority:** Part of Authentication System (Phase 1)

---

# PART 1: USER PROFILES WITH PAYROLL INTEGRATION

## Executive Summary

Comprehensive user profile system that integrates with payroll tracking, supports detailed employee information, multiple contact methods, profile photo management, and tracks all profile changes for accountability.

## Why Enhanced User Profiles?

**Business Problem:**
- Payroll **tracking** requires detailed employee information (Staff No, ID Number, Position, Salary)
- Need to track commission calculations (5 KES per bread for salesmen)
- Multiple contact methods needed for emergency communication
- Profile photos help identify staff in audit logs and reports
- All profile changes must be tracked (who changed what, when)

**Important Clarification:**
- **We track payroll numbers, NOT process payroll payments**
- Just like daily petty cash expenses tracked by accountant
- Payroll data used for monthly income calculations → affects profit/loss statements
- Actual payment processing happens outside the app

**Solution:**
- Detailed employee profiles with payroll **tracking** fields
- Up to 3 mobile numbers per user
- Profile photo with drag-to-center positioning
- Full audit trail of all profile modifications
- Admin/superadmin can edit, but changes are logged

---

# PART 2: TECHNICAL SPECIFICATIONS

## Enhanced User Model

### Database Schema
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE,
    
    -- Email (verified, required)
    email VARCHAR(254) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    
    -- Password & Auth
    password VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    last_password_login TIMESTAMP,
    last_activity TIMESTAMP,
    
    -- Name Fields (Enhanced)
    first_name VARCHAR(100) NOT NULL,
    middle_names VARCHAR(200),  -- Optional, space-separated multiple middle names
    last_name VARCHAR(100) NOT NULL,
    
    -- Contact Information (Up to 3 mobile numbers)
    mobile_primary VARCHAR(15) NOT NULL,
    mobile_secondary VARCHAR(15),
    mobile_tertiary VARCHAR(15),
    
    -- Profile Photo (Max 5MB)
    profile_photo VARCHAR(255),  -- Path to uploaded photo
    photo_uploaded_at TIMESTAMP,
    photo_uploaded_by INTEGER REFERENCES users(id),
    photo_center_x DECIMAL(5,2) DEFAULT 50.00,  -- Drag position X (0-100%)
    photo_center_y DECIMAL(5,2) DEFAULT 50.00,  -- Drag position Y (0-100%)
    
    -- Employee/Payroll TRACKING Information (for profit/loss calculations)
    employee_id VARCHAR(20) UNIQUE,  -- e.g., CHE001, CHE028 (from Excel)
    national_id VARCHAR(20) UNIQUE,  -- ID Number for official records
    position VARCHAR(100),  -- Job title/position
    department VARCHAR(100),  -- Production, Sales, Dispatch, etc.
    basic_salary DECIMAL(10,2),  -- Monthly basic salary (KES) - TRACKED, not paid from app
    pay_per_day DECIMAL(10,2),  -- Calculated: basic_salary / 30 - for expense tracking
    overtime_rate DECIMAL(10,2),  -- Per mix for production staff - for cost tracking
    commission_rate DECIMAL(5,2) DEFAULT 7.00,  -- % above target (for salesmen) - for commission tracking
    sales_target DECIMAL(10,2) DEFAULT 35000.00,  -- Monthly target (KES)
    date_hired DATE,
    date_terminated DATE,
    employment_status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, INACTIVE, TERMINATED
    
    -- Loan/Advance TRACKING (Links to Finance Module for expense tracking)
    current_loan_balance DECIMAL(10,2) DEFAULT 0.00,  -- Tracked for monthly expenses
    current_advance_balance DECIMAL(10,2) DEFAULT 0.00,  -- Tracked for monthly expenses
    
    -- Audit Fields
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    
    -- Custom Permissions (for superadmin modifications)
    custom_permissions JSONB DEFAULT '{}',
    
    -- Indexes for performance
    INDEX idx_email (email),
    INDEX idx_employee_id (employee_id),
    INDEX idx_role (role),
    INDEX idx_employment_status (employment_status),
    INDEX idx_is_active_approved (is_active, is_approved)
);
```

### Profile Change History
```sql
CREATE TABLE user_profile_changes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    changed_by INTEGER REFERENCES users(id),
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason TEXT,  -- Optional reason for change
    changed_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    
    INDEX idx_user_changes (user_id, changed_at),
    INDEX idx_changed_by (changed_by),
    INDEX idx_field_name (field_name)
);
```

### Email Verification Tokens
```sql
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(254) NOT NULL,
    token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    
    INDEX idx_token (token),
    INDEX idx_user_email (user_id, email)
);
```

---

## Django Models

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'CEO / Developer'
        ADMIN = 'ADMIN', 'Accountant'
        PRODUCT_MANAGER = 'PRODUCT_MANAGER', 'Production Manager'
        DEPT_HEAD = 'DEPT_HEAD', 'Department Head'
        DISPATCH = 'DISPATCH', 'Dispatch Officer'
        SALESMAN = 'SALESMAN', 'Sales Representative'
        SECURITY = 'SECURITY', 'Gate Man / Security'
    
    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        TERMINATED = 'TERMINATED', 'Terminated'
    
    # ========== NAME FIELDS ==========
    first_name = models.CharField(max_length=100, help_text="Required")
    middle_names = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Optional. Enter multiple middle names separated by spaces"
    )
    last_name = models.CharField(max_length=100, help_text="Required")
    
    # ========== EMAIL (VERIFIED) ==========
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # ========== MOBILE NUMBERS (UP TO 3) ==========
    mobile_primary = models.CharField(
        max_length=15,
        help_text="Primary contact number (required)"
    )
    mobile_secondary = models.CharField(
        max_length=15,
        blank=True,
        help_text="Secondary contact number (optional)"
    )
    mobile_tertiary = models.CharField(
        max_length=15,
        blank=True,
        help_text="Tertiary contact number (optional)"
    )
    
    # ========== PROFILE PHOTO (MAX 5MB, CIRCULAR DISPLAY) ==========
    profile_photo = models.ImageField(
        upload_to='profiles/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
        ],
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
        validators=[MaxValueValidator(100)],
        help_text="Horizontal center position (0-100%)"
    )
    photo_center_y = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MaxValueValidator(100)],
        help_text="Vertical center position (0-100%)"
    )
    
    # ========== EMPLOYEE/PAYROLL TRACKING (NOT PAYMENT PROCESSING) ==========
    # These fields track payroll data for monthly expense calculations
    # Actual payments processed outside the app
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="e.g., CHE001, CHE028"
    )
    national_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="National ID Number for official records"
    )
    position = models.CharField(max_length=100, blank=True, help_text="Job title")
    department = models.CharField(
        max_length=100,
        blank=True,
        help_text="Production, Sales, Dispatch, etc."
    )
    
    # Salary TRACKING (for expense calculations, not payment processing)
    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly basic salary (KES) - tracked for monthly income/expense calculations"
    )
    pay_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated: basic_salary / 30 - for daily expense tracking"
    )
    overtime_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Per mix for production staff (KES) - tracked for cost calculations"
    )
    
    # Commission TRACKING (for Salesmen - used in monthly expense calculations)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('7.00'),
        help_text="Percentage above sales target (default: 7%) - tracked for commission calculations"
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
        default=EmploymentStatus.ACTIVE
    )
    
    # Loan/Advance TRACKING (tracked like petty cash expenses)
    current_loan_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current outstanding loan amount (KES) - tracked for monthly expenses"
    )
    current_advance_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current advance payment balance (KES) - tracked for monthly expenses"
    )
    
    # ========== ROLE & PERMISSIONS ==========
    role = models.CharField(max_length=20, choices=Role.choices)
    is_approved = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    last_password_login = models.DateTimeField(null=True)
    last_activity = models.DateTimeField(null=True)
    custom_permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom permissions set by superadmin"
    )
    
    # ========== AUDIT FIELDS ==========
    created_by = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.SET_NULL,
        related_name='users_created'
    )
    updated_by = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.SET_NULL,
        related_name='users_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========== METHODS ==========
    def get_full_name(self):
        """Return full name including middle names"""
        parts = [self.first_name]
        if self.middle_names:
            parts.append(self.middle_names)
        parts.append(self.last_name)
        return ' '.join(parts)
    
    def get_display_name(self):
        """Return first and last name only (no middle names)"""
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
    
    def clean(self):
        """Validate model before saving"""
        from django.core.exceptions import ValidationError
        
        # Validate photo size (max 5MB)
        if self.profile_photo and self.profile_photo.size > 5 * 1024 * 1024:
            raise ValidationError({'profile_photo': 'Photo size cannot exceed 5MB'})
        
        # Auto-calculate pay_per_day if basic_salary changed
        if self.basic_salary and not self.pay_per_day:
            self.calculate_pay_per_day()
    
    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
            models.Index(fields=['employment_status']),
            models.Index(fields=['is_active', 'is_approved']),
        ]


class UserProfileChange(models.Model):
    """Track all changes to user profiles"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='profile_changes'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='profile_changes_made'
    )
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    change_reason = models.TextField(
        blank=True,
        help_text="Optional reason for the change"
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    
    class Meta:
        db_table = 'accounts_user_profile_change'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['user', '-changed_at']),
            models.Index(fields=['changed_by']),
            models.Index(fields=['field_name']),
        ]
    
    def __str__(self):
        return f"{self.user.get_display_name()} - {self.field_name} changed by {self.changed_by.get_display_name() if self.changed_by else 'System'}"


class EmailVerificationToken(models.Model):
    """Email verification tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    def is_valid(self):
        """Check if token is still valid"""
        return not self.verified_at and timezone.now() < self.expires_at
    
    class Meta:
        db_table = 'accounts_email_verification_token'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'email']),
        ]
```

---

## Profile Change Tracking Signals

```python
# apps/accounts/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import User, UserProfileChange

# Fields to track changes
TRACKED_FIELDS = [
    'first_name', 'middle_names', 'last_name',
    'email', 'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
    'employee_id', 'national_id', 'position', 'department',
    'basic_salary', 'pay_per_day', 'overtime_rate',
    'commission_rate', 'sales_target',
    'employment_status', 'role',
    'current_loan_balance', 'current_advance_balance'
]

@receiver(pre_save, sender=User)
def track_profile_changes(sender, instance, **kwargs):
    """Track changes to user profile fields"""
    if not instance.pk:
        return  # New user, no changes to track
    
    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return
    
    # Get request from thread local storage (set in middleware)
    from .middleware import get_current_request
    request = get_current_request()
    changed_by = request.user if request and request.user.is_authenticated else None
    ip_address = request.META.get('REMOTE_ADDR') if request else None
    
    # Track changes to monitored fields
    for field in TRACKED_FIELDS:
        old_value = getattr(old_instance, field)
        new_value = getattr(instance, field)
        
        if old_value != new_value:
            UserProfileChange.objects.create(
                user=instance,
                changed_by=changed_by,
                field_name=field,
                old_value=str(old_value) if old_value is not None else '',
                new_value=str(new_value) if new_value is not None else '',
                ip_address=ip_address
            )
```

---

## Profile Photo Upload Form

```python
# apps/accounts/forms.py
from django import forms
from .models import User

class ProfilePhotoForm(forms.ModelForm):
    """Form for uploading profile photo with drag-to-center"""
    
    class Meta:
        model = User
        fields = ['profile_photo', 'photo_center_x', 'photo_center_y']
        widgets = {
            'profile_photo': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/png',
                'class': 'form-control',
                'id': 'profile-photo-input'
            }),
            'photo_center_x': forms.HiddenInput(),
            'photo_center_y': forms.HiddenInput(),
        }
    
    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            # Check file size (max 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Photo size cannot exceed 5MB')
            
            # Check file type
            if not photo.content_type in ['image/jpeg', 'image/png']:
                raise forms.ValidationError('Only JPG and PNG images are supported')
        
        return photo


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile (admin/user editable)"""
    
    change_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Optional: Reason for changes...'
        }),
        help_text='Optional reason for profile changes (logged in audit trail)'
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'middle_names', 'last_name',
            'email', 'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
            'employee_id', 'national_id', 'position', 'department',
            'basic_salary', 'overtime_rate', 'commission_rate', 'sales_target',
            'date_hired', 'employment_status'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'middle_names': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'mobile_primary': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'mobile_secondary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'mobile_tertiary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'date_hired': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Only superadmin/admin can edit payroll fields
        if self.request and self.request.user.role not in ['SUPERADMIN', 'ADMIN']:
            for field in ['basic_salary', 'overtime_rate', 'commission_rate', 'employee_id', 'national_id']:
                self.fields[field].disabled = True
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-calculate pay_per_day
        if instance.basic_salary:
            instance.calculate_pay_per_day()
        
        # Set updated_by
        if self.request:
            instance.updated_by = self.request.user
        
        if commit:
            instance.save()
            
            # Log change reason if provided
            change_reason = self.cleaned_data.get('change_reason')
            if change_reason:
                UserProfileChange.objects.create(
                    user=instance,
                    changed_by=self.request.user if self.request else None,
                    field_name='__reason__',
                    new_value=change_reason,
                    ip_address=self.request.META.get('REMOTE_ADDR') if self.request else None
                )
        
        return instance
```

---

# PART 3: IN-APP CHAT SYSTEM (PLANNING)

## Executive Summary

**Simplified** Django-only in-app chat system for direct user-to-user text messaging with message history and reply functionality. No Redis required - uses Django ORM for real-time updates via polling.

## Why Simplified Chat?

**Business Benefits:**
- **Cost Savings**: Reduce SMS costs for internal communication
- **Audit Trail**: All conversations logged for accountability
- **Simple Communication**: Text messages between users
- **Message History**: View past conversations
- **Reply Feature**: Reply to specific messages for context
- **No Complex Setup**: Django-only, no Redis/WebSockets

**Simplified Requirements:**
- ✅ User-to-user direct messaging (text only)
- ✅ Message history (view past conversations)
- ✅ Reply to specific messages (threading)
- ✅ Read receipts (seen/unseen)
- ✅ Django ORM polling (no WebSockets)
- ❌ Group chats (not needed for now)
- ❌ File attachments (not needed for now)
- ❌ Typing indicators (not needed for now)
- ❌ Redis/WebSockets (keeping it simple)

**Use Cases:**
- Salesman reports daily stock issues to admin/dispatch
- Admin sends payment confirmations to salesmen
- Production manager coordinates with accountant on inventory
- CEO receives alerts and can respond instantly
- Quick questions and answers between staff

---

## Simplified Architecture (Django-Only, No Redis)

### Simplified Chat Implementation
```
apps/communications/
├── models.py
│   ├── ChatConversation  # Direct user-to-user chats only
│   └── ChatMessage       # Text messages with reply support
│
├── services/
│   └── chat.py           # ChatService class (simple CRUD)
│
├── views.py              # Django views (no WebSockets)
│
├── urls.py               # Chat routes
│
└── templates/
    └── chat/
        ├── inbox.html           # Chat inbox (all conversations)
        ├── conversation.html     # Chat thread (message history)
        └── components/
            └── message.html      # Single message display with reply
```

### Simplified Database Schema
```sql
-- Direct User-to-User Conversations
CREATE TABLE chat_conversations (
    id SERIAL PRIMARY KEY,
    user1_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    user2_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP,
    last_message_text TEXT,  -- Cache for inbox preview
    
    -- Ensure one conversation per user pair
    CONSTRAINT unique_user_pair UNIQUE (LEAST(user1_id, user2_id), GREATEST(user1_id, user2_id)),
    INDEX idx_user1 (user1_id),
    INDEX idx_user2 (user2_id),
    INDEX idx_last_message (last_message_at)
);

-- Simple Text Messages
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES chat_conversations(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    recipient_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    reply_to_id INTEGER REFERENCES chat_messages(id),  -- Reply to specific message
    sent_at TIMESTAMP DEFAULT NOW(),
    read_at TIMESTAMP,  -- Simple read receipt (NULL = unread)
    
    INDEX idx_conversation_sent (conversation_id, sent_at),
    INDEX idx_sender (sender_id),
    INDEX idx_reply_to (reply_to_id)
);
```

### Technology Stack (Simplified)
- **Django ORM**: All database operations
- **Django Views**: Standard request/response (no WebSockets)
- **JavaScript**: AJAX polling for new messages (every 3-5 seconds)
- **HTML/CSS**: Simple chat UI with scroll, reply button
- **No Redis**: No caching layer needed
- **No Channels**: No WebSocket complexity

### Simplified Chat Service
```python
# apps/communications/services/chat.py
from django.db.models import Q
from django.utils import timezone
from ..models import ChatConversation, ChatMessage

class ChatService:
    """
    Simplified chat service - Django ORM only, no Redis.
    
    Features:
    - Send direct text messages
    - Get conversation history
    - Reply to messages
    - Simple read receipts
    - Email notification (if configured)
    """
    
    @staticmethod
    def get_or_create_conversation(user1, user2):
        """Get existing conversation or create new one"""
        # Ensure consistent ordering to avoid duplicates
        u1_id = min(user1.id, user2.id)
        u2_id = max(user1.id, user2.id)
        
        conversation, created = ChatConversation.objects.get_or_create(
            user1_id=u1_id,
            user2_id=u2_id
        )
        return conversation
    
    @staticmethod
    def send_message(sender, recipient, message, reply_to=None):
        """Send simple text message"""
        conversation = ChatService.get_or_create_conversation(sender, recipient)
        
        # Create message
        msg = ChatMessage.objects.create(
            conversation=conversation,
            sender=sender,
            recipient=recipient,
            message=message,
            reply_to=reply_to
        )
        
        # Update conversation
        conversation.last_message_at = timezone.now()
        conversation.last_message_text = message[:100]  # Preview
        conversation.save()
        
        return msg
    
    @staticmethod
    def get_messages(conversation, limit=50):
        """Get message history"""
        return ChatMessage.objects.filter(
            conversation=conversation
        ).select_related('sender', 'recipient', 'reply_to').order_by('-sent_at')[:limit]
    
    @staticmethod
    def mark_as_read(message, user):
        """Mark message as read"""
        if message.recipient == user and not message.read_at:
            message.read_at = timezone.now()
            message.save()
    
    @staticmethod
    def get_unread_count(user):
        """Get total unread message count"""
        return ChatMessage.objects.filter(
            recipient=user,
            read_at__isnull=True
        ).count()
    
    @staticmethod
    def get_user_conversations(user):
        """Get all conversations for user"""
        return ChatConversation.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).order_by('-last_message_at')
```

### Simplified Features Roadmap

**Phase 1: Simplified Chat (Post-Auth) - CORE**
- [ ] Direct user-to-user text messages
- [ ] Message history (view past conversations)
- [ ] Reply to specific messages (threading)
- [ ] Simple read receipts (read_at timestamp)
- [ ] Inbox with all conversations
- [ ] AJAX polling for new messages (every 3-5 seconds)
- [ ] Basic emoji support (native emoji picker)
- [ ] Message timestamps

**Phase 2: Enhancements (Future - If Needed)**
- [ ] Message search within conversation
- [ ] Delete own messages
- [ ] Edit sent messages (within 5 min)
- [ ] Email notification for unread messages (daily digest)
- [ ] Conversation archiving

**Phase 3: Advanced Features (Future - If Really Needed)**
- [ ] Group conversations (if business requires)
- [ ] File attachments (if business requires)
- [ ] Upgrade to WebSockets for true real-time (if polling too slow)

**NOT PLANNED:**
- ❌ Voice messages (not needed)
- ❌ Video calls (not needed)
- ❌ Complex reactions (not needed)
- ❌ Message pinning (not needed)
- ❌ Chat bots (not needed)
- ❌ Mobile app integration (not needed initially)

---

## Simplified Permission Model

| Role | Chat Permissions |
|------|------------------|
| **SUPERADMIN** | Can message anyone, view all conversations (audit) |
| **ADMIN** | Can message anyone, view all conversations (audit) |
| **PRODUCT_MANAGER** | Can message admin, salesmen, dispatch, production staff |
| **DEPT_HEAD** | Can message admin, own department staff |
| **DISPATCH** | Can message admin, salesmen, other dispatch |
| **SALESMAN** | Can message admin, dispatch, other salesmen |
| **SECURITY** | Can message admin only |

**Simplified Rules:**
- All users can send/receive direct messages
- Superadmin/Admin can view any conversation (audit trail)
- Users can only see conversations they're part of
- No complex group permissions (keep it simple)

---

**Document Version:** 1.0  
**Last Updated:** October 16, 2025  
**Next Review:** When implementing chat system (post-authentication phase)
