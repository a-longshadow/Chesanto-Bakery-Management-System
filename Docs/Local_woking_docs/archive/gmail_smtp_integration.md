# Gmail SMTP Integration - Implementation Guide
## Chesanto Bakery Management System

### 🎯 **Overview**

This document provides the complete implementation guide for integrating Gmail SMTP into the Chesanto Bakery Management System authentication workflow. The integration uses the provided Gmail credentials to send professional, branded emails for user verification, admin notifications, and approval workflows.

---

### 📧 **Gmail Configuration Details**

#### Credentials & Settings
```python
# Gmail SMTP Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'joe@coophive.network'
EMAIL_HOST_PASSWORD = 'opno whxi ztta soyt'  # App-specific password
EMAIL_PORT = 465  # SSL port for secure connection
EMAIL_USE_SSL = True  # Enable SSL encryption
EMAIL_USE_TLS = False  # Disable TLS (using SSL instead)
DEFAULT_FROM_EMAIL = 'Chesanto Bakery <joe@coophive.network>'
EMAIL_TIMEOUT = 30  # Connection timeout in seconds

# Development Configuration
EMAIL_USE_CONSOLE = True  # DEVELOPMENT ONLY - logs emails to console
```

#### Security Features
- **App-Specific Password**: Using `opno whxi ztta soyt` for secure authentication
- **SSL Encryption**: Port 465 with SSL for maximum security
- **Professional Identity**: "Chesanto Bakery" brand name in sender field
- **Fallback Support**: TLS on port 587 as backup option

---

### 🛠 **Django Settings Implementation**

#### settings/base.py
```python
# Email Configuration - Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_TIMEOUT = 30

# From email settings
DEFAULT_FROM_EMAIL = 'Chesanto Bakery <joe@coophive.network>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = '[Chesanto Bakery] '

# Email credentials (store in environment variables for production)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='joe@coophive.network')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='opno whxi ztta soyt')

# Gmail-specific settings
EMAIL_USE_LOCALTIME = True
EMAIL_USE_THREADING = True
```

#### settings/local.py (Development)
```python
# Development email settings
EMAIL_USE_CONSOLE = True  # Also log emails to console for debugging

# Email backend override for development
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # Uncomment below to test actual Gmail sending in development
    # EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

#### settings/prod.py (Production)
```python
# Production email settings
EMAIL_USE_CONSOLE = False  # Disable console logging in production

# Ensure SSL verification
EMAIL_SSL_KEYFILE = None
EMAIL_SSL_CERTFILE = None

# Production email backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

---

### 📨 **Email Service Implementation**

#### Core Email Service Class
```python
# apps/authentication/services/email_service.py
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from typing import List, Optional
import time

logger = logging.getLogger(__name__)

class GmailEmailService:
    """
    Gmail SMTP email service for authentication workflows
    """
    
    @staticmethod
    def _send_email_with_retry(
        subject: str,
        html_content: str,
        recipient_list: List[str],
        sender: Optional[str] = None,
        retry_attempts: int = 3,
        retry_delay: int = 5
    ) -> bool:
        """
        Send email with retry mechanism for Gmail reliability
        """
        sender = sender or settings.DEFAULT_FROM_EMAIL
        text_content = strip_tags(html_content)
        
        for attempt in range(retry_attempts):
            try:
                msg = EmailMultiAlternatives(
                    subject=f"{settings.EMAIL_SUBJECT_PREFIX}{subject}",
                    body=text_content,
                    from_email=sender,
                    to=recipient_list
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                logger.info(f"Email sent successfully to {recipient_list}")
                return True
                
            except Exception as e:
                logger.warning(f"Email attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to send email after {retry_attempts} attempts: {str(e)}")
                    return False
        
        return False
    
    @classmethod
    def send_verification_code(cls, user, code: str) -> bool:
        """
        Send 4-digit verification code via Gmail
        """
        context = {
            'user': user,
            'code': code,
            'company_name': 'Chesanto Bakery',
            'expires_in': 15,  # minutes
            'base_url': settings.BASE_URL,
        }
        
        html_content = render_to_string(
            'authentication/emails/verification_code.html',
            context
        )
        
        return cls._send_email_with_retry(
            subject="Email Verification Code",
            html_content=html_content,
            recipient_list=[user.email]
        )
    
    @classmethod
    def send_admin_new_user_alert(cls, user) -> bool:
        """
        Send new user registration alert to administrators
        """
        from apps.authentication.models import ChesantoUser
        
        # Get all administrators
        admins = ChesantoUser.objects.filter(
            is_staff=True,
            is_active=True
        ).values_list('email', flat=True)
        
        if not admins:
            logger.warning("No administrators found to notify")
            return False
        
        context = {
            'user': user,
            'company_name': 'Chesanto Bakery',
            'approval_url': f"{settings.BASE_URL}/admin/approvals/",
            'base_url': settings.BASE_URL,
        }
        
        html_content = render_to_string(
            'authentication/emails/admin_new_user_alert.html',
            context
        )
        
        return cls._send_email_with_retry(
            subject=f"New User Registration - {user.get_full_name()}",
            html_content=html_content,
            recipient_list=list(admins)
        )
    
    @classmethod
    def send_user_approved_notification(cls, user) -> bool:
        """
        Send approval confirmation to user
        """
        context = {
            'user': user,
            'company_name': 'Chesanto Bakery',
            'login_url': f"{settings.BASE_URL}/auth/login/",
            'base_url': settings.BASE_URL,
        }
        
        html_content = render_to_string(
            'authentication/emails/user_approved.html',
            context
        )
        
        return cls._send_email_with_retry(
            subject="Welcome to Chesanto Bakery Management System",
            html_content=html_content,
            recipient_list=[user.email]
        )
    
    @classmethod
    def send_user_rejected_notification(cls, user, reason: str) -> bool:
        """
        Send rejection notification to user
        """
        context = {
            'user': user,
            'reason': reason,
            'company_name': 'Chesanto Bakery',
            'contact_email': 'hr@chesanto.com',
            'base_url': settings.BASE_URL,
        }
        
        html_content = render_to_string(
            'authentication/emails/user_rejected.html',
            context
        )
        
        return cls._send_email_with_retry(
            subject="Registration Application Update",
            html_content=html_content,
            recipient_list=[user.email]
        )
    
    @classmethod
    def send_password_reset_email(cls, user, reset_url: str) -> bool:
        """
        Send password reset email
        """
        context = {
            'user': user,
            'reset_url': reset_url,
            'company_name': 'Chesanto Bakery',
            'expires_in': 60,  # minutes
            'base_url': settings.BASE_URL,
        }
        
        html_content = render_to_string(
            'authentication/emails/password_reset.html',
            context
        )
        
        return cls._send_email_with_retry(
            subject="Password Reset Request",
            html_content=html_content,
            recipient_list=[user.email]
        )
```

---

### 📧 **Email Templates with Gmail Branding**

#### Verification Code Template
```html
<!-- apps/authentication/templates/authentication/emails/verification_code.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Verification - Chesanto Bakery</title>
    <style>
        body {
            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333333;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }
        .header h1 {
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }
        .content {
            background: white;
            padding: 40px 30px;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .verification-code {
            background: #f8f9fa;
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 25px;
            text-align: center;
            margin: 25px 0;
        }
        .code {
            font-size: 36px;
            font-weight: 700;
            color: #667eea;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 14px;
        }
        .btn {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .security-note {
            background: #e9ecef;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 4px 4px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ company_name }}</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0;">Email Verification</p>
        </div>
        
        <div class="content">
            <h2>Hello {{ user.first_name }}!</h2>
            <p>Thank you for registering with {{ company_name }}. Please use the verification code below to confirm your email address:</p>
            
            <div class="verification-code">
                <p style="margin: 0 0 10px; font-weight: 600; color: #495057;">Your verification code is:</p>
                <div class="code">{{ code }}</div>
                <p style="margin: 10px 0 0; font-size: 14px; color: #6c757d;">
                    This code expires in {{ expires_in }} minutes
                </p>
            </div>
            
            <p>Enter this code on the verification page to complete your registration.</p>
            
            <div class="security-note">
                <strong>Security Notice:</strong> If you didn't request this verification code, please ignore this email. Your account will remain unverified and inactive.
            </div>
        </div>
        
        <div class="footer">
            <p>{{ company_name }} Management System</p>
            <p>Sent from: {{ DEFAULT_FROM_EMAIL }}</p>
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
```

#### Admin New User Alert Template
```html
<!-- apps/authentication/templates/authentication/emails/admin_new_user_alert.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New User Registration - Admin Alert</title>
    <style>
        body {
            font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333333;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
            padding: 30px;
            border-radius: 8px 8px 0 0;
            text-align: center;
        }
        .header h1 {
            color: white;
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .content {
            background: white;
            padding: 30px;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .user-details {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .detail-row {
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #dee2e6;
        }
        .detail-row:last-child {
            border-bottom: none;
        }
        .detail-label {
            font-weight: 600;
            width: 120px;
            color: #495057;
        }
        .detail-value {
            color: #333;
        }
        .btn {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .urgent-notice {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>New User Registration</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0;">Admin Approval Required</p>
        </div>
        
        <div class="content">
            <h2>Action Required: User Approval</h2>
            <p>A new user has completed email verification and requires admin approval to access the {{ company_name }} Management System.</p>
            
            <div class="user-details">
                <div class="detail-row">
                    <span class="detail-label">Name:</span>
                    <span class="detail-value">{{ user.get_full_name }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Email:</span>
                    <span class="detail-value">{{ user.email }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Department:</span>
                    <span class="detail-value">{{ user.profile.department|default:"Not specified" }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Position:</span>
                    <span class="detail-value">{{ user.profile.position|default:"Not specified" }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Registered:</span>
                    <span class="detail-value">{{ user.date_joined|date:"F j, Y g:i A" }}</span>
                </div>
            </div>
            
            <div style="text-align: center;">
                <a href="{{ approval_url }}" class="btn">Review Application</a>
            </div>
            
            <div class="urgent-notice">
                <strong>Note:</strong> The user cannot access the system until approved. Please review applications promptly to maintain good user experience.
            </div>
        </div>
        
        <div class="footer">
            <p>{{ company_name }} Management System</p>
            <p>Sent from: {{ DEFAULT_FROM_EMAIL }}</p>
            <p>This is an automated admin notification.</p>
        </div>
    </div>
</body>
</html>
```

---

### ⚙️ **Django Management Commands**

#### Test Email Configuration
```python
# apps/authentication/management/commands/test_gmail.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test Gmail SMTP configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email address to send test email to',
            default='admin@chesanto.com'
        )
    
    def handle(self, *args, **options):
        recipient = options['to']
        
        try:
            # Test basic email sending
            send_mail(
                subject='Gmail SMTP Test - Chesanto Bakery',
                message='This is a test email to verify Gmail SMTP configuration.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Gmail SMTP test successful! Email sent to {recipient}'
                )
            )
            
            # Display current configuration
            self.stdout.write('\n📧 Current Email Configuration:')
            self.stdout.write(f'   Host: {settings.EMAIL_HOST}')
            self.stdout.write(f'   Port: {settings.EMAIL_PORT}')
            self.stdout.write(f'   User: {settings.EMAIL_HOST_USER}')
            self.stdout.write(f'   SSL: {settings.EMAIL_USE_SSL}')
            self.stdout.write(f'   TLS: {settings.EMAIL_USE_TLS}')
            self.stdout.write(f'   From: {settings.DEFAULT_FROM_EMAIL}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Gmail SMTP test failed: {str(e)}'
                )
            )
            sys.exit(1)
```

#### Send Test Verification Email
```python
# apps/authentication/management/commands/send_test_verification.py
from django.core.management.base import BaseCommand
from apps.authentication.services.email_service import GmailEmailService
from apps.authentication.models import ChesantoUser

class Command(BaseCommand):
    help = 'Send test verification email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='User email to send verification to',
            required=True
        )
    
    def handle(self, *args, **options):
        email = options['email']
        
        try:
            # Get or create test user
            user, created = ChesantoUser.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': 'Test',
                    'last_name': 'User',
                    'username': f'test_{email.split("@")[0]}'
                }
            )
            
            # Send verification email
            success = GmailEmailService.send_verification_code(user, '1234')
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Test verification email sent to {email}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Failed to send verification email to {email}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )
```

---

### 🚀 **Testing Gmail Integration**

#### Development Testing
```bash
# Test basic Gmail configuration
python manage.py test_gmail --to your-email@example.com

# Send test verification email
python manage.py send_test_verification --email test@example.com

# Check email backend in Django shell
python manage.py shell
>>> from django.core.mail import send_mail
>>> from django.conf import settings
>>> send_mail('Test', 'Message', settings.DEFAULT_FROM_EMAIL, ['test@example.com'])
```

#### Production Verification
```python
# Add to authentication views for monitoring
import logging
logger = logging.getLogger(__name__)

def register_user_view(request):
    # ... registration logic ...
    
    # Send verification email with logging
    try:
        success = GmailEmailService.send_verification_code(user, code)
        if success:
            logger.info(f"Verification email sent successfully to {user.email}")
        else:
            logger.error(f"Failed to send verification email to {user.email}")
    except Exception as e:
        logger.error(f"Email service error: {str(e)}")
```

---

### 📊 **Monitoring & Analytics**

#### Email Delivery Tracking
```python
# apps/authentication/models.py
class EmailDeliveryLog(models.Model):
    user = models.ForeignKey(ChesantoUser, on_delete=models.CASCADE)
    email_type = models.CharField(max_length=50)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=20, default='SENT')
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-sent_at']
```

This comprehensive Gmail SMTP integration provides reliable, professional email delivery for the authentication system with proper error handling, retry mechanisms, and monitoring capabilities.
