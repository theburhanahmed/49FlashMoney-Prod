"""
Celery tasks for async email sending.
"""
from celery import shared_task
from django.conf import settings
from apps.notifications.services import EmailService
from apps.notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email_task(user_id):
    """Send welcome email asynchronously."""
    try:
        from apps.users.models import User
        user = User.objects.get(id=user_id)
        EmailService.send_welcome_email(user)
    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
        raise


@shared_task
def send_email_verification_task(user_id):
    """Send email verification asynchronously."""
    try:
        from apps.users.models import User
        user = User.objects.get(id=user_id)
        EmailService.send_email_verification(user)
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        raise


@shared_task
def send_password_reset_task(user_id, token):
    """Send password reset email asynchronously."""
    try:
        from apps.users.models import User
        user = User.objects.get(id=user_id)
        EmailService.send_password_reset(user, token)
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}")
        raise


@shared_task
def send_ticket_purchase_confirmation_task(user_id, ticket_id, lottery_id):
    """Send ticket purchase confirmation asynchronously."""
    try:
        from apps.users.models import User
        from apps.lotteries.models import Ticket, Lottery
        
        user = User.objects.get(id=user_id)
        ticket = Ticket.objects.get(id=ticket_id)
        lottery = Lottery.objects.get(id=lottery_id)
        
        EmailService.send_ticket_purchase_confirmation(user, ticket, lottery)
    except Exception as e:
        logger.error(f"Error sending ticket purchase confirmation: {str(e)}")
        raise


@shared_task
def send_draw_result_win_task(user_id, winner_id, lottery_id):
    """Send draw result email for winner asynchronously."""
    try:
        from apps.users.models import User
        from apps.lotteries.models import Winner, Lottery
        
        user = User.objects.get(id=user_id)
        winner = Winner.objects.get(id=winner_id)
        lottery = Lottery.objects.get(id=lottery_id)
        
        EmailService.send_draw_result_win(user, winner, lottery)
    except Exception as e:
        logger.error(f"Error sending draw result win email: {str(e)}")
        raise


@shared_task
def send_draw_result_loss_task(user_id, lottery_id):
    """Send draw result email for non-winner asynchronously."""
    try:
        from apps.users.models import User
        from apps.lotteries.models import Lottery
        
        user = User.objects.get(id=user_id)
        lottery = Lottery.objects.get(id=lottery_id)
        
        EmailService.send_draw_result_loss(user, lottery)
    except Exception as e:
        logger.error(f"Error sending draw result loss email: {str(e)}")
        raise


@shared_task
def send_withdrawal_status_task(user_id, withdrawal_id, status_message):
    """Send withdrawal status update asynchronously."""
    try:
        from apps.users.models import User
        from apps.transactions.models import WithdrawalRequest
        
        user = User.objects.get(id=user_id)
        withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id)
        
        EmailService.send_withdrawal_status(user, withdrawal, status_message)
    except Exception as e:
        logger.error(f"Error sending withdrawal status email: {str(e)}")
        raise


@shared_task
def send_referral_bonus_credited_task(user_id, bonus_amount, referral_id):
    """Send referral bonus credited email asynchronously."""
    try:
        from apps.users.models import User
        from apps.referrals.models import Referral
        
        user = User.objects.get(id=user_id)
        referral = Referral.objects.get(id=referral_id)
        
        EmailService.send_referral_bonus_credited(user, bonus_amount, referral)
    except Exception as e:
        logger.error(f"Error sending referral bonus email: {str(e)}")
        raise


@shared_task
def send_lottery_ending_soon_task(user_id, lottery_id, hours_remaining):
    """Send lottery ending soon reminder asynchronously."""
    try:
        from apps.users.models import User
        from apps.lotteries.models import Lottery
        
        user = User.objects.get(id=user_id)
        lottery = Lottery.objects.get(id=lottery_id)
        
        EmailService.send_lottery_ending_soon(user, lottery, hours_remaining)
    except Exception as e:
        logger.error(f"Error sending lottery ending soon email: {str(e)}")
        raise


@shared_task
def send_deposit_confirmation_email(user_id, transaction_id=None):
    """Send deposit confirmation email asynchronously."""
    try:
        from apps.users.models import User
        from apps.transactions.models import Transaction
        
        user = User.objects.get(id=user_id)
        
        # Get transaction if provided
        transaction = None
        if transaction_id:
            try:
                transaction = Transaction.objects.get(id=transaction_id)
            except Transaction.DoesNotExist:
                pass
        
        # Send email via EmailService (you may need to add this method)
        # For now, we'll use a generic confirmation
        EmailService.send_deposit_confirmation(user, transaction)
    except Exception as e:
        logger.error(f"Error sending deposit confirmation email: {str(e)}")
        raise


@shared_task
def create_notification_task(user_id, notification_type, title, message, action_url=None, metadata=None):
    """Create in-app notification asynchronously."""
    try:
        from apps.users.models import User
        
        user = User.objects.get(id=user_id)
        
        Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            action_url=action_url or '',
            metadata=metadata or {}
        )
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise
