"""
Email service for sending emails.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with templates."""
    
    @staticmethod
    def send_email(subject, template_name, context, recipient_list, from_email=None):
        """
        Send email using template.
        
        Args:
            subject: Email subject
            template_name: Template name (without .html extension)
            context: Template context dictionary
            recipient_list: List of recipient email addresses
            from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            from_email = from_email or settings.DEFAULT_FROM_EMAIL
            
            # Render HTML template
            html_content = render_to_string(f'emails/{template_name}.html', context)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=html_content,  # Fallback plain text
                from_email=from_email,
                to=recipient_list
            )
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            
            logger.info(f"Email sent successfully to {recipient_list}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user."""
        context = {
            'user': user,
            'frontend_url': settings.FRONTEND_URL,
            'verification_url': f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}" if user.email_verification_token else None,
        }
        return EmailService.send_email(
            subject='Welcome to Lottery System!',
            template_name='welcome',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_email_verification(user):
        """Send email verification email."""
        token = user.generate_verification_token()
        context = {
            'user': user,
            'verification_url': f"{settings.FRONTEND_URL}/verify-email/{token}",
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject='Verify Your Email Address',
            template_name='email_verification',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_password_reset(user, token):
        """Send password reset email."""
        context = {
            'user': user,
            'reset_url': f"{settings.FRONTEND_URL}/reset-password/{token}",
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject='Password Reset Request',
            template_name='password_reset',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_ticket_purchase_confirmation(user, ticket, lottery):
        """Send ticket purchase confirmation email."""
        context = {
            'user': user,
            'ticket': ticket,
            'lottery': lottery,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject=f'Ticket Purchase Confirmation - {lottery.name}',
            template_name='ticket_purchase_confirmation',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_draw_result_win(user, winner, lottery):
        """Send draw result email for winner."""
        context = {
            'user': user,
            'winner': winner,
            'lottery': lottery,
            'prize_amount': winner.prize_amount,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject=f'Congratulations! You Won {lottery.name}',
            template_name='draw_result_win',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_draw_result_loss(user, lottery):
        """Send draw result email for non-winner."""
        context = {
            'user': user,
            'lottery': lottery,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject=f'Draw Results - {lottery.name}',
            template_name='draw_result_loss',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_withdrawal_status(user, withdrawal_request, status_message):
        """Send withdrawal status update email."""
        context = {
            'user': user,
            'withdrawal': withdrawal_request,
            'status_message': status_message,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject=f'Withdrawal Request {withdrawal_request.get_status_display()}',
            template_name='withdrawal_status',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_referral_bonus_credited(user, bonus_amount, referral):
        """Send referral bonus credited email."""
        context = {
            'user': user,
            'bonus_amount': bonus_amount,
            'referral': referral,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject='Referral Bonus Credited!',
            template_name='referral_bonus_credited',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_lottery_ending_soon(user, lottery, hours_remaining):
        """Send lottery ending soon reminder email."""
        context = {
            'user': user,
            'lottery': lottery,
            'hours_remaining': hours_remaining,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject=f'{lottery.name} Ending Soon!',
            template_name='lottery_ending_soon',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_deposit_confirmation(user, transaction=None):
        """Send deposit confirmation email."""
        context = {
            'user': user,
            'transaction': transaction,
            'amount': transaction.amount if transaction else None,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject='Deposit Confirmation',
            template_name='deposit_confirmation',
            context=context,
            recipient_list=[user.email]
        )
    
    @staticmethod
    def send_deposit_confirmation(user, transaction=None):
        """Send deposit confirmation email."""
        context = {
            'user': user,
            'transaction': transaction,
            'amount': transaction.amount if transaction else None,
            'frontend_url': settings.FRONTEND_URL,
        }
        return EmailService.send_email(
            subject='Deposit Confirmation',
            template_name='deposit_confirmation',
            context=context,
            recipient_list=[user.email]
        )

