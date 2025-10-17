"""
Authentication Forms for Chesanto Bakery Management System
Django forms for user authentication and profile management
"""
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(forms.Form):
    """Login form with email and password"""
    
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
            'autofocus': True
        }),
        label='Email Address'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        }),
        label='Password'
    )


class RegisterForm(forms.Form):
    """User registration form"""
    
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        label='Email Address'
    )
    
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        }),
        label='First Name'
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        }),
        label='Last Name'
    )
    
    mobile_primary = forms.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^(\+254|0)[17]\d{8}$',
                message='Enter a valid Kenyan mobile number (e.g., +254712345678 or 0712345678)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+254712345678 or 0712345678'
        }),
        label='Mobile Number'
    )
    
    # Role field removed - BASIC_USER assigned automatically in view
    
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 characters'
        }),
        label='Password',
        help_text='Must be at least 8 characters long'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter password'
        }),
        label='Confirm Password'
    )
    
    def clean_email(self):
        """Validate email is unique"""
        email = self.cleaned_data.get('email', '').lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email
    
    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data


class InviteForm(forms.Form):
    """Admin form to invite new users"""
    
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'user@example.com'
        }),
        label='Email Address'
    )
    
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name of the invitee'
        }),
        label='Full Name'
    )
    
    role = forms.ChoiceField(
        choices=lambda: User.Role.choices,  # Lazy evaluation
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Role'
    )


class OTPForm(forms.Form):
    """OTP verification form"""
    
    code = forms.CharField(
        min_length=6,
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='Code must be exactly 6 digits'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '\d{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code'
        }),
        label='Verification Code'
    )


class PasswordChangeForm(forms.Form):
    """Password change form for authenticated users"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password'
        }),
        label='Current Password'
    )
    
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 characters'
        }),
        label='New Password',
        help_text='Must be at least 8 characters long'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter new password'
        }),
        label='Confirm New Password'
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    
    def clean_old_password(self):
        """Validate old password is correct"""
        old_password = self.cleaned_data.get('old_password')
        if self.user and not self.user.check_password(old_password):
            raise ValidationError('Current password is incorrect.')
        return old_password
    
    def clean(self):
        """Validate passwords match and new password is different"""
        cleaned_data = super().clean()
        old_password = cleaned_data.get('old_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('New passwords do not match.')
        
        if old_password and new_password and old_password == new_password:
            raise ValidationError('New password must be different from current password.')
        
        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""
    
    email = forms.EmailField(
        max_length=255,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        label='Email Address',
        help_text='Enter the email associated with your account'
    )


class PasswordResetVerifyForm(forms.Form):
    """Password reset verification form"""
    
    code = forms.CharField(
        min_length=6,
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='Code must be exactly 6 digits'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '\d{6}',
            'inputmode': 'numeric'
        }),
        label='Reset Code'
    )
    
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 characters'
        }),
        label='New Password',
        help_text='Must be at least 8 characters long'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter new password'
        }),
        label='Confirm New Password'
    )
    
    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'middle_names',
            'mobile_primary', 'mobile_secondary', 'mobile_tertiary',
            'emergency_contact_name', 'emergency_contact_phone',
            'address', 'national_id', 'kra_pin',
            'bank_name', 'bank_account_number', 'bank_branch',
            'profile_photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_names': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_primary': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_secondary': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_tertiary': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'kra_pin': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
