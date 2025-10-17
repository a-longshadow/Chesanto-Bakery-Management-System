from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.conf import settings
import logging
from .models import User, UserInvitation, EmailOTP, UserProfileChange, EmailVerificationToken

logger = logging.getLogger(__name__)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'employment_status', 'is_active', 'is_approved', 'date_joined']
    list_filter = ['role', 'employment_status', 'is_active', 'is_approved', 'email_verified']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id', 'national_id']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password', 'email_verified', 'email_verified_at')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'middle_names', 'last_name', 'profile_photo', 'photo_center_x', 'photo_center_y')
        }),
        ('Contact Info', {
            'fields': ('mobile_primary', 'mobile_secondary', 'mobile_tertiary')
        }),
        ('Employee Info (Optional - for employees with payroll)', {
            'fields': ('employee_id', 'national_id', 'position', 'department', 'date_hired', 'date_terminated', 'employment_status'),
            'description': 'Payroll fields are optional - only for actual employees (superadmins may not have these)'
        }),
        ('Payroll Tracking (Optional)', {
            'fields': ('basic_salary', 'pay_per_day', 'overtime_rate', 'commission_rate', 'sales_target'),
            'classes': ('collapse',)
        }),
        ('Loans & Advances (Tracking)', {
            'fields': ('current_loan_balance', 'current_advance_balance'),
            'classes': ('collapse',)
        }),
        ('Permissions & Role', {
            'fields': ('role', 'is_active', 'is_approved', 'is_staff', 'is_superuser', 'is_primary_superadmin', 'custom_permissions')
        }),
        ('Security', {
            'fields': ('must_change_password', 'last_login', 'last_password_login', 'last_activity')
        }),
        ('Audit', {
            'fields': ('created_by', 'updated_by', 'updated_at', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password1', 'password2')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'middle_names', 'last_name')
        }),
        ('Contact', {
            'fields': ('mobile_primary',)
        }),
        ('Role', {
            'fields': ('role', 'is_active', 'is_approved')
        }),
    )
    
    readonly_fields = ['email_verified_at', 'last_login', 'last_password_login', 'last_activity', 
                       'date_joined', 'updated_at', 'pay_per_day']
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    def get_readonly_fields(self, request, obj=None):
        """
        Make certain fields read-only based on SUPERADMIN protections
        """
        readonly = list(self.readonly_fields)
        
        if obj:
            # Protect Primary SUPERADMIN from modifications
            if obj.is_primary_superadmin and obj.id != request.user.id:
                # Make almost all fields read-only for Primary SUPERADMIN
                readonly.extend([
                    'email', 'first_name', 'last_name', 'middle_names',
                    'role', 'is_active', 'is_approved', 'is_staff', 'is_superuser',
                    'is_primary_superadmin', 'mobile_primary'
                ])
            
            # Protect other SUPERADMINs from modification
            if obj.role == 'SUPERADMIN' and obj.id != request.user.id:
                readonly.extend(['role', 'is_superuser', 'is_primary_superadmin'])
        
        return readonly
    
    def has_delete_permission(self, request, obj=None):
        """
        Enforce SUPERADMIN deletion protections
        """
        if not request.user.is_superuser:
            return False
        
        if obj:
            # Use the model's can_delete_user method
            return request.user.can_delete_user(obj)
        
        return True


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'role', 'invited_by', 'created_at', 'is_used', 'is_expired']
    list_filter = ['role', 'created_at']
    search_fields = ['email', 'full_name']
    readonly_fields = ['temp_password', 'created_at', 'used_at', 'expires_at']
    actions = ['send_invitation_emails']
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('email', 'full_name', 'role', 'invited_by')
        }),
        ('Auto-Generated Security', {
            'fields': ('temp_password',),
            'description': 'Temporary password is automatically generated when you save.'
        }),
        ('Tracking', {
            'fields': ('created_at', 'used_at', 'expires_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set invited_by to current user if not set"""
        if not change:  # Only on creation
            if not obj.invited_by:
                obj.invited_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.action(description="✉️ Send invitation email to selected invitations")
    def send_invitation_emails(self, request, queryset):
        """Send email invitations to selected users"""
        from apps.communications.services.email import EmailService
        
        sent = 0
        failed = 0
        skipped = 0
        
        for invitation in queryset:
            # Skip already used or expired invitations
            if not invitation.is_valid():
                skipped += 1
                continue
                
            try:
                # Generate login URL
                login_url = f"{settings.SERVER_URL}/auth/login/"
                
                # Send invitation email with temp password
                success = EmailService.send_invitation(
                    email=invitation.email,
                    name=invitation.full_name,
                    role=invitation.role,
                    temp_password=invitation.temp_password,
                    login_url=login_url,
                    invited_by=invitation.invited_by
                )
                
                if success:
                    sent += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send invitation to {invitation.email}: {str(e)}")
        
        # Show success message
        if sent > 0:
            self.message_user(
                request,
                f"✅ Successfully sent {sent} invitation(s). {failed} failed. {skipped} skipped (already used/expired).",
                level='success' if failed == 0 else 'warning'
            )
        else:
            self.message_user(
                request,
                f"⚠️ No invitations sent. {failed} failed. {skipped} skipped (already used/expired).",
                level='error'
            )
    
    def is_used(self, obj):
        if obj.used_at:
            return format_html('<span style="color: green;">✓ Used</span>')
        return format_html('<span style="color: gray;">Pending</span>')
    is_used.short_description = 'Status'
    
    def is_expired(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Expired</span>')
    is_expired.short_description = 'Validity'


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'created_at', 'expires_at', 'attempts', 'is_valid_status', 'is_used']
    list_filter = ['purpose', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['code_hash', 'created_at', 'expires_at', 'used_at', 'attempts', 'ip_address']
    
    fieldsets = (
        ('OTP Details', {
            'fields': ('user', 'purpose', 'code_hash')
        }),
        ('Tracking', {
            'fields': ('created_at', 'expires_at', 'used_at', 'attempts', 'ip_address')
        }),
    )
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Invalid/Expired</span>')
    is_valid_status.short_description = 'Valid'
    
    def is_used(self, obj):
        if obj.used_at:
            return format_html('<span style="color: green;">✓ Used</span>')
        return format_html('<span style="color: gray;">Unused</span>')
    is_used.short_description = 'Used'
    
    def has_add_permission(self, request):
        # OTP codes should be generated programmatically
        return False


@admin.register(UserProfileChange)
class UserProfileChangeAdmin(admin.ModelAdmin):
    list_display = ['user', 'field_name', 'changed_by', 'changed_at', 'old_value_short', 'new_value_short']
    list_filter = ['field_name', 'changed_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'field_name']
    readonly_fields = ['user', 'changed_by', 'field_name', 'old_value', 'new_value', 'change_reason', 'changed_at', 'ip_address']
    date_hierarchy = 'changed_at'
    
    fieldsets = (
        ('Change Details', {
            'fields': ('user', 'changed_by', 'field_name')
        }),
        ('Values', {
            'fields': ('old_value', 'new_value', 'change_reason')
        }),
        ('Metadata', {
            'fields': ('changed_at', 'ip_address')
        }),
    )
    
    def old_value_short(self, obj):
        if len(obj.old_value) > 50:
            return obj.old_value[:50] + '...'
        return obj.old_value
    old_value_short.short_description = 'Old Value'
    
    def new_value_short(self, obj):
        if len(obj.new_value) > 50:
            return obj.new_value[:50] + '...'
        return obj.new_value
    new_value_short.short_description = 'New Value'
    
    def has_add_permission(self, request):
        # Profile changes are tracked automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Cannot modify audit trail
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superadmin can delete
        return request.user.is_superuser


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'created_at', 'expires_at', 'is_verified', 'is_valid_status']
    list_filter = ['created_at', 'verified_at']
    search_fields = ['user__email', 'email', 'token']
    readonly_fields = ['user', 'email', 'token', 'created_at', 'expires_at', 'verified_at']
    
    fieldsets = (
        ('Verification Details', {
            'fields': ('user', 'email', 'token')
        }),
        ('Tracking', {
            'fields': ('created_at', 'expires_at', 'verified_at')
        }),
    )
    
    def is_verified(self, obj):
        if obj.verified_at:
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: gray;">Pending</span>')
    is_verified.short_description = 'Verified'
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Invalid/Expired</span>')
    is_valid_status.short_description = 'Valid'
    
    def has_add_permission(self, request):
        # Tokens should be generated programmatically
        return False
