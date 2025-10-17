# Communication System - Complete Specification
**Project:** Chesanto Bakery Management System  
**Date:** October 16, 2025  
**Status:** ✅ CORE INFRASTRUCTURE  
**Purpose:** Centralized email/SMS communication for all modules

---

# PART 1: HIGH-LEVEL OVERVIEW (FOR HUMANS)

## Executive Summary

Centralized communication system that handles ALL email and SMS notifications across the entire Chesanto Bakery system. Single source of truth for message templates, delivery tracking, and notification logs.

## Why Separate Communications App?

**Problems with Scattered Communication:**
- Each module implements its own email logic (duplication)
- Inconsistent message templates (unprofessional)
- No centralized delivery tracking (failures go unnoticed)
- Hard to update branding (change in 10 places)
- Cannot switch providers easily (locked in)

**Solution - Centralized Communications:**
- **One app handles all messages** (email, SMS, future: push, WhatsApp)
- **Reusable templates** (update once, apply everywhere)
- **Delivery tracking** (see which emails failed/succeeded)
- **Easy provider switching** (change Gmail to SendGrid in one place)
- **Audit trail** (who sent what, when, to whom)

## Who Uses Communications App?

| Module | Usage Examples |
|--------|----------------|
| **Authentication** | Invitations, OTP codes, password resets, approval notifications |
| **Sales** | Order confirmations, invoice emails, payment receipts, commission reports |
| **Production** | Production schedules, recipe updates, inventory alerts |
| **Inventory** | Low stock alerts, reorder notifications, delivery confirmations |
| **Finance** | Expense approvals, petty cash alerts, monthly reports |
| **Reports** | Scheduled report delivery, export notifications |
| **Dispatch** | Delivery assignments, crate return reminders, vehicle logs |

## Message Types Supported

### 1. Transactional Emails (High Priority)
- OTP codes (authentication)
- Password resets
- Order confirmations
- Payment receipts
- System alerts

### 2. Notification Emails (Medium Priority)
- Daily entry reminders
- Low stock alerts
- Approval requests
- Status updates

### 3. Scheduled Emails (Lower Priority)
- Weekly reports
- Monthly summaries
- Bulk announcements

### 4. SMS (Future - Phase 2)
- OTP codes (backup for email)
- Critical alerts
- Delivery notifications

### 5. In-App Chat (Future - Phase 3)
- Real-time messaging between staff
- Group chats for departments
- File sharing (images, PDFs)
- Read receipts and typing indicators
- **Architecture**: Django Channels + WebSockets + Redis
- **Cost Savings**: Reduces SMS costs for internal communication
- **Audit Trail**: All conversations logged for accountability
- **See**: USER_PROFILES_AND_CHAT.md for complete chat specifications

---

# PART 2: TECHNICAL SPECIFICATIONS (FOR DEVELOPERS)

## App Architecture

```
apps/communications/
├── __init__.py
├── models.py              # EmailLog, SMSLog, MessageTemplate
├── services/
│   ├── __init__.py
│   ├── email.py          # EmailService class
│   ├── sms.py            # SMSService class (future)
│   └── base.py           # BaseMessageService (shared logic)
├── templates/
│   └── emails/
│       ├── base.html            # Base email template
│       ├── components/
│       │   ├── header.html      # Email header
│       │   ├── footer.html      # Email footer
│       │   └── button.html      # CTA button
│       │
│       ├── auth/                # Authentication emails
│       │   ├── invitation.html
│       │   ├── otp.html
│       │   ├── password_reset.html
│       │   ├── password_changed.html
│       │   ├── account_approved.html
│       │   └── security_alert.html
│       │
│       ├── sales/               # Sales emails (future)
│       │   ├── order_confirmation.html
│       │   ├── invoice.html
│       │   └── payment_receipt.html
│       │
│       ├── production/          # Production emails (future)
│       │   └── schedule_notification.html
│       │
│       ├── inventory/           # Inventory emails (future)
│       │   └── low_stock_alert.html
│       │
│       └── reports/             # Report emails (future)
│           └── scheduled_report.html
├── tests/
│   ├── test_email_service.py
│   ├── test_sms_service.py
│   └── test_models.py
├── admin.py               # Django admin for logs
├── apps.py
└── urls.py                # Future: webhook endpoints
```

## Database Models

### EmailLog
```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailLog(models.Model):
    """Track all outgoing emails for audit and debugging"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'
        BOUNCED = 'BOUNCED', 'Bounced'
        REJECTED = 'REJECTED', 'Rejected'
    
    # Message details
    recipient = models.EmailField(db_index=True)
    cc = models.JSONField(null=True, blank=True)  # CC recipients
    bcc = models.JSONField(null=True, blank=True)  # BCC recipients
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=100, db_index=True)
    
    # Tracking
    sent_by = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='sent_emails'
    )
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Context (for debugging)
    context_data = models.JSONField(null=True, blank=True)
    
    # Provider metadata
    provider = models.CharField(max_length=50, default='gmail')  # gmail, sendgrid, etc
    provider_message_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'communications_email_log'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['recipient', '-sent_at']),
            models.Index(fields=['status', '-sent_at']),
            models.Index(fields=['template', '-sent_at']),
        ]
    
    def __str__(self):
        return f"{self.template} to {self.recipient} - {self.status}"


class SMSLog(models.Model):
    """Track all outgoing SMS for audit and debugging (future)"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        UNDELIVERED = 'UNDELIVERED', 'Undelivered'
    
    # Message details
    phone_number = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    template = models.CharField(max_length=100, db_index=True)
    
    # Tracking
    sent_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_sms'
    )
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Provider metadata
    provider = models.CharField(max_length=50)  # twilio, africastalking, etc
    provider_message_id = models.CharField(max_length=255, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # SMS cost
    
    class Meta:
        db_table = 'communications_sms_log'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['phone_number', '-sent_at']),
            models.Index(fields=['status', '-sent_at']),
        ]
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status}"


class MessageTemplate(models.Model):
    """Store reusable message templates (future enhancement)"""
    
    class Type(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        SMS = 'SMS', 'SMS'
    
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=Type.choices)
    subject = models.CharField(max_length=255, blank=True)  # For emails
    template_path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Versioning
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    required_context = models.JSONField(default=list)  # Required template variables
    
    class Meta:
        db_table = 'communications_message_template'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
```

## Email Service Implementation

### services/email.py
```python
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from ..models import EmailLog
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Centralized email service for all modules.
    
    Usage from any app:
        from apps.communications.services.email import EmailService
        EmailService.send_invitation(email, name, password, url)
    """
    
    @staticmethod
    def _send_email(
        recipient,
        subject,
        template_path,
        context,
        cc=None,
        bcc=None,
        sent_by=None,
        template_name=None
    ):
        """
        Internal method to send email and log result.
        
        Args:
            recipient (str): Recipient email
            subject (str): Email subject
            template_path (str): Path to HTML template
            context (dict): Template context variables
            cc (list): CC recipients
            bcc (list): BCC recipients
            sent_by (User): User who triggered email
            template_name (str): Template identifier for logging
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Create log entry
        log = EmailLog.objects.create(
            recipient=recipient,
            cc=cc,
            bcc=bcc,
            subject=subject,
            template=template_name or template_path,
            sent_by=sent_by,
            context_data=context,
            provider='gmail',
            status=EmailLog.Status.PENDING
        )
        
        try:
            # Render HTML email
            html_content = render_to_string(template_path, context)
            
            # Create plain text fallback (strip HTML)
            from django.utils.html import strip_tags
            text_content = strip_tags(html_content)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                cc=cc or [],
                bcc=bcc or []
            )
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send(fail_silently=False)
            
            # Update log on success
            log.status = EmailLog.Status.SENT
            log.delivered_at = timezone.now()
            log.save(update_fields=['status', 'delivered_at'])
            
            logger.info(f"Email sent successfully: {template_name} to {recipient}")
            return True
            
        except Exception as e:
            # Update log on failure
            log.status = EmailLog.Status.FAILED
            log.error_message = str(e)
            log.retry_count += 1
            log.save(update_fields=['status', 'error_message', 'retry_count'])
            
            logger.error(f"Email failed: {template_name} to {recipient} - {str(e)}")
            return False
    
    # ========== AUTHENTICATION EMAILS ==========
    
    @staticmethod
    def send_invitation(email, name, role, temp_password, login_url, sent_by=None):
        """Send user invitation with temporary password"""
        context = {
            'name': name,
            'email': email,
            'role': role,
            'password': temp_password,
            'login_url': login_url,
            'year': timezone.now().year
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Welcome to Chesanto Bakery Management System',
            template_path='emails/auth/invitation.html',
            context=context,
            sent_by=sent_by,
            template_name='auth_invitation'
        )
    
    @staticmethod
    def send_otp(email, name, code, purpose='login', expiry_minutes=10, sent_by=None):
        """Send OTP code for login or password reset"""
        context = {
            'name': name,
            'email': email,
            'otp_code': code,
            'purpose': 'login verification' if purpose == 'login' else 'password reset',
            'expiry_minutes': expiry_minutes,
            'year': timezone.now().year
        }
        
        return EmailService._send_email(
            recipient=email,
            subject=f'Your Verification Code - Chesanto Bakery',
            template_path='emails/auth/otp.html',
            context=context,
            sent_by=sent_by,
            template_name='auth_otp'
        )
    
    @staticmethod
    def send_password_reset(email, name, code, sent_by=None):
        """Send password reset code"""
        return EmailService.send_otp(
            email=email,
            name=name,
            code=code,
            purpose='password_reset',
            expiry_minutes=15,
            sent_by=sent_by
        )
    
    @staticmethod
    def send_password_changed(email, name, timestamp, ip_address, user_agent, sent_by=None):
        """Send password change confirmation"""
        context = {
            'name': name,
            'email': email,
            'timestamp': timestamp,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'year': timezone.now().year
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Password Changed - Chesanto Bakery',
            template_path='emails/auth/password_changed.html',
            context=context,
            sent_by=sent_by,
            template_name='auth_password_changed'
        )
    
    @staticmethod
    def send_account_approved(email, name, role, login_url, approved_by, sent_by=None):
        """Send account approval notification"""
        context = {
            'name': name,
            'email': email,
            'role': role,
            'login_url': login_url,
            'approved_by': approved_by,
            'year': timezone.now().year
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='🎉 Your Chesanto Account Has Been Approved',
            template_path='emails/auth/account_approved.html',
            context=context,
            sent_by=sent_by,
            template_name='auth_account_approved'
        )
    
    @staticmethod
    def send_daily_entry_reminder(email, name, date, entry_type, dashboard_url, sent_by=None):
        """Send daily entry reminder to salesmen/dispatch"""
        context = {
            'name': name,
            'email': email,
            'date': date,
            'entry_type': entry_type,  # 'sales' or 'dispatch'
            'dashboard_url': dashboard_url,
            'year': timezone.now().year
        }
        
        return EmailService._send_email(
            recipient=email,
            subject=f'⏰ Daily Entry Reminder - {date}',
            template_path='emails/auth/daily_reminder.html',
            context=context,
            sent_by=sent_by,
            template_name='auth_daily_reminder'
        )
    
    # ========== FUTURE: SALES EMAILS ==========
    
    @staticmethod
    def send_order_confirmation(email, order_id, items, total, sent_by=None):
        """Send order confirmation (future implementation)"""
        # TODO: Implement when Sales module is ready
        pass
    
    # ========== FUTURE: INVENTORY EMAILS ==========
    
    @staticmethod
    def send_low_stock_alert(email, product_name, current_stock, threshold, sent_by=None):
        """Send low stock alert (future implementation)"""
        # TODO: Implement when Inventory module is ready
        pass
    
    # ========== FUTURE: REPORTS EMAILS ==========
    
    @staticmethod
    def send_scheduled_report(email, report_name, attachment_path, sent_by=None):
        """Send scheduled report with attachment (future implementation)"""
        # TODO: Implement when Reports module is ready
        pass
```

## Environment Variables

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL="Chesanto Bakery <your@gmail.com>"

# Email Settings
EMAIL_TIMEOUT=30
EMAIL_MAX_RETRIES=3
EMAIL_RETRY_DELAY=60  # seconds

# Future: SMS Configuration
# SMS_PROVIDER=africastalking  # or twilio
# SMS_API_KEY=your-api-key
# SMS_USERNAME=your-username
# SMS_SENDER_ID=CHESANTO
```

## Integration Examples

### From Authentication App
```python
# apps/accounts/views.py
from apps.communications.services.email import EmailService

def invite_user(request):
    # ... create user ...
    
    # Send invitation via Communications app
    EmailService.send_invitation(
        email=user.email,
        name=user.get_full_name(),
        role=user.get_role_display(),
        temp_password=temp_password,
        login_url=f"{settings.SERVER_URL}/login",
        sent_by=request.user
    )
    
    return JsonResponse({'success': True})
```

### From Sales App (Future)
```python
# apps/sales/views.py
from apps.communications.services.email import EmailService

def create_order(request):
    # ... create order ...
    
    # Send order confirmation via Communications app
    EmailService.send_order_confirmation(
        email=order.customer.email,
        order_id=order.id,
        items=order.items.all(),
        total=order.total,
        sent_by=request.user
    )
    
    return JsonResponse({'success': True})
```

### From Inventory App (Future)
```python
# apps/inventory/tasks.py (Celery task)
from apps.communications.services.email import EmailService

def check_low_stock():
    low_stock_products = Product.objects.filter(stock__lt=F('threshold'))
    
    for product in low_stock_products:
        # Send alert via Communications app
        EmailService.send_low_stock_alert(
            email='admin@chesanto.com',
            product_name=product.name,
            current_stock=product.stock,
            threshold=product.threshold
        )
```

## Testing

### Unit Tests
```python
# apps/communications/tests/test_email_service.py
from django.test import TestCase
from apps.communications.services.email import EmailService
from apps.communications.models import EmailLog
from django.core import mail

class EmailServiceTest(TestCase):
    def test_send_invitation(self):
        """Test invitation email sends successfully"""
        result = EmailService.send_invitation(
            email='test@example.com',
            name='John Doe',
            role='Salesman',
            temp_password='Abc123xyz',
            login_url='http://test.com/login'
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('Welcome', mail.outbox[0].subject)
        
        # Check log created
        log = EmailLog.objects.latest('sent_at')
        self.assertEqual(log.recipient, 'test@example.com')
        self.assertEqual(log.status, EmailLog.Status.SENT)
    
    def test_email_failure_logged(self):
        """Test email failures are logged correctly"""
        # Temporarily break email settings
        from django.conf import settings
        old_host = settings.EMAIL_HOST
        settings.EMAIL_HOST = 'invalid'
        
        result = EmailService.send_invitation(
            email='test@example.com',
            name='John Doe',
            role='Salesman',
            temp_password='Abc123xyz',
            login_url='http://test.com/login'
        )
        
        self.assertFalse(result)
        
        # Check log shows failure
        log = EmailLog.objects.latest('sent_at')
        self.assertEqual(log.status, EmailLog.Status.FAILED)
        self.assertIn('error', log.error_message.lower())
        
        # Restore settings
        settings.EMAIL_HOST = old_host
```

## Django Admin

```python
# apps/communications/admin.py
from django.contrib import admin
from .models import EmailLog, SMSLog, MessageTemplate

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'template', 'status', 'sent_at', 'sent_by']
    list_filter = ['status', 'template', 'sent_at', 'provider']
    search_fields = ['recipient', 'subject', 'error_message']
    readonly_fields = ['sent_at', 'delivered_at', 'opened_at', 'clicked_at']
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        return False  # Logs created by system only
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superadmin can delete logs


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'template', 'status', 'cost', 'sent_at', 'sent_by']
    list_filter = ['status', 'template', 'sent_at', 'provider']
    search_fields = ['phone_number', 'message', 'error_message']
    readonly_fields = ['sent_at', 'delivered_at']
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'version', 'is_active', 'updated_at']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
```

## Future Enhancements

### Phase 2: SMS Integration
```python
# apps/communications/services/sms.py
class SMSService:
    """SMS service using Africa's Talking or Twilio"""
    
    @staticmethod
    def send_otp(phone_number, code):
        """Send OTP via SMS"""
        pass
    
    @staticmethod
    def send_delivery_notification(phone_number, order_id, eta):
        """Send delivery notification"""
        pass
```

### Phase 3: Push Notifications
```python
# apps/communications/services/push.py
class PushService:
    """Push notifications using Firebase Cloud Messaging"""
    
    @staticmethod
    def send_notification(user, title, body, data=None):
        """Send push notification to mobile app"""
        pass
```

### Phase 4: WhatsApp Integration
```python
# apps/communications/services/whatsapp.py
class WhatsAppService:
    """WhatsApp Business API integration"""
    
    @staticmethod
    def send_message(phone_number, message):
        """Send WhatsApp message"""
        pass
```

## Installation & Setup

```bash
# 1. App is already in project structure
INSTALLED_APPS = [
    # ...
    'apps.communications',
]

# 2. Run migrations
python manage.py makemigrations communications
python manage.py migrate

# 3. Set environment variables
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL="Chesanto Bakery <your@gmail.com>"

# 4. Test email delivery
python manage.py shell
>>> from apps.communications.services.email import EmailService
>>> EmailService.send_invitation('test@example.com', 'Test User', 'Admin', 'Pass123', 'http://localhost:8000/login')
```

## Monitoring & Maintenance

### Email Delivery Monitoring
```sql
-- Check failed emails in last 24 hours
SELECT recipient, template, error_message, sent_at
FROM communications_email_log
WHERE status = 'FAILED'
  AND sent_at >= NOW() - INTERVAL '24 hours'
ORDER BY sent_at DESC;

-- Email success rate by template
SELECT 
    template,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent,
    ROUND(100.0 * SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM communications_email_log
WHERE sent_at >= NOW() - INTERVAL '7 days'
GROUP BY template
ORDER BY total DESC;
```

### Cleanup Old Logs
```python
# management/commands/cleanup_email_logs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.communications.models import EmailLog

class Command(BaseCommand):
    help = 'Clean up email logs older than 1 year'
    
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=365)
        deleted = EmailLog.objects.filter(sent_at__lt=cutoff_date).delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {deleted[0]} old email logs')
        )
```

---

**Document Version:** 1.0  
**Last Updated:** October 16, 2025  
**Next Review:** When adding new message types from other modules
