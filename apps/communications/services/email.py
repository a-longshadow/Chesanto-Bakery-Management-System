from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from ..models import EmailLog
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Centralized email service for all modules
    Handles email delivery with Gmail SMTP and logging
    """
    
    @staticmethod
    def _send_email(recipient, subject, template_name, context, sent_by=None, log_context=None):
        """
        Internal method to send email with template rendering and logging
        
        Args:
            recipient: Email address
            subject: Email subject
            template_name: Template path (e.g., 'emails/auth/invitation.html')
            context: Template context dict
            sent_by: User object who triggered the email
            log_context: Sanitized context for logging (optional, defaults to context)
        
        Returns:
            bool: Success status
        """
        # Use sanitized context for logging if provided
        log = EmailLog.objects.create(
            recipient=recipient,
            subject=subject,
            template=template_name,
            sent_by=sent_by,
            context_data=log_context or context,
            status=EmailLog.Status.PENDING
        )
        
        try:
            # Render HTML email from template
            html_message = render_to_string(f'communications/{template_name}', context)
            plain_message = strip_tags(html_message)
            
            # Create email with HTML alternative
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient]
            )
            email.attach_alternative(html_message, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            # Update log
            log.status = EmailLog.Status.SENT
            log.delivered_at = timezone.now()
            log.save()
            
            logger.info(f"Email sent successfully: {template_name} to {recipient}")
            return True
            
        except Exception as e:
            log.status = EmailLog.Status.FAILED
            log.error_message = str(e)
            log.retry_count += 1
            log.save()
            
            logger.error(f"Email send failed: {template_name} to {recipient}. Error: {str(e)}")
            return False
    
    @staticmethod
    def send_invitation(email, name, role, temp_password, login_url, invited_by=None):
        """
        Send invitation email with temporary password
        
        Args:
            email: Recipient email
            name: Full name
            role: User role
            temp_password: Temporary password
            login_url: Login page URL
            invited_by: User who sent invitation
        """
        context = {
            'name': name,
            'email': email,
            'role': role,
            'temp_password': temp_password,
            'login_url': login_url,
        }
        
        # Sanitize context for logging (exclude password)
        log_context = {k: v for k, v in context.items() if k != 'temp_password'}
        log_context['temp_password'] = '[REDACTED]'
        
        return EmailService._send_email(
            recipient=email,
            subject='Welcome to Chesanto Bakery',
            template_name='emails/auth/invitation.html',
            context=context,
            sent_by=invited_by,
            log_context=log_context
        )
    
    @staticmethod
    def send_otp(email, code, purpose='login', user=None):
        """
        Send OTP verification code
        
        Args:
            email: Recipient email
            code: 6-digit OTP code
            purpose: 'login' or 'password_reset'
            user: User object (optional)
        """
        context = {
            'code': code,
            'purpose': purpose,
            'validity_minutes': 10 if purpose == 'login' else 15,
        }
        
        subject = 'Your Login Code' if purpose == 'login' else 'Password Reset Code'
        
        return EmailService._send_email(
            recipient=email,
            subject=subject,
            template_name='emails/auth/otp.html',
            context=context,
            sent_by=user
        )
    
    @staticmethod
    def send_password_reset(email, code, user=None):
        """
        Send password reset email with verification code
        
        Args:
            email: Recipient email
            code: 6-digit reset code
            user: User object (optional)
        """
        context = {
            'code': code,
            'validity_minutes': 15,
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Password Reset Request',
            template_name='emails/auth/password_reset.html',
            context=context,
            sent_by=user
        )
    
    @staticmethod
    def send_password_changed(email, user=None):
        """
        Send confirmation email after password change
        
        Args:
            email: Recipient email
            user: User object (optional)
        """
        context = {
            'changed_at': timezone.now(),
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Password Changed Successfully',
            template_name='emails/auth/password_changed.html',
            context=context,
            sent_by=user
        )
    
    @staticmethod
    def send_account_approved(email, name, login_url, approved_by=None):
        """
        Send account approval notification
        
        Args:
            email: Recipient email
            name: User full name
            login_url: Login page URL
            approved_by: Admin who approved
        """
        context = {
            'name': name,
            'login_url': login_url,
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Account Approved - Chesanto Bakery',
            template_name='emails/auth/account_approved.html',
            context=context,
            sent_by=approved_by
        )
    
    @staticmethod
    def send_account_created(email, name, user=None):
        """
        Send welcome email after account registration (pending approval)
        
        Args:
            email: Recipient email
            name: User full name
            user: User object (optional)
        """
        context = {
            'name': name,
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Welcome to Chesanto Bakery - Account Pending Approval',
            template_name='emails/auth/account_created.html',
            context=context,
            sent_by=user
        )
    
    @staticmethod
    def send_account_activated(email, name, login_url, user=None):
        """
        Send notification when account is activated by admin
        
        Args:
            email: Recipient email
            name: User full name
            login_url: Login page URL
            user: User object (optional)
        """
        context = {
            'name': name,
            'login_url': login_url,
        }
        
        return EmailService._send_email(
            recipient=email,
            subject='Account Activated - Chesanto Bakery',
            template_name='emails/auth/account_activated.html',
            context=context,
            sent_by=user
        )
    
    @staticmethod
    def send_security_alert(email, alert_type, details, user=None):
        """
        Send security alert email
        
        Args:
            email: Recipient email
            alert_type: Type of alert (e.g., 'Failed Login', 'Password Change')
            details: Alert details dict
            user: User object (optional)
        """
        context = {
            'alert_type': alert_type,
            'details': details,
            'timestamp': timezone.now(),
        }
        
        return EmailService._send_email(
            recipient=email,
            subject=f'Security Alert: {alert_type}',
            template_name='emails/auth/security_alert.html',
            context=context,
            sent_by=user
        )
