"""
Celery tasks for lottery operations.
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from apps.lotteries.models import Lottery
from apps.lotteries.services import DrawService
from apps.notifications.tasks import send_lottery_ending_soon_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_and_close_lotteries():
    """Check and close lotteries that have reached their end date."""
    try:
        now = timezone.now()
        lotteries = Lottery.objects.filter(
            status='ACTIVE',
            end_date__lte=now
        )
        
        count = 0
        for lottery in lotteries:
            lottery.status = 'CLOSED'
            lottery.save()
            count += 1
            logger.info(f"Closed lottery {lottery.id}: {lottery.name}")
        
        return f"Closed {count} lotteries"
    except Exception as e:
        logger.error(f"Error closing lotteries: {str(e)}")
        raise


@shared_task
def conduct_scheduled_draws():
    """Conduct draws for lotteries that have reached their draw date and have auto_draw enabled."""
    try:
        now = timezone.now()
        lotteries = Lottery.objects.filter(
            status='CLOSED',
            draw_date__lte=now,
            auto_draw=True
        )
        
        count = 0
        for lottery in lotteries:
            try:
                DrawService.conduct_draw(lottery)
                count += 1
                logger.info(f"Auto-drew lottery {lottery.id}: {lottery.name}")
            except Exception as e:
                logger.error(f"Error conducting draw for lottery {lottery.id}: {str(e)}")
        
        return f"Conducted {count} draws"
    except Exception as e:
        logger.error(f"Error conducting scheduled draws: {str(e)}")
        raise


@shared_task
def send_draw_reminders():
    """Send reminders for lotteries ending soon."""
    try:
        from apps.lotteries.models import Ticket
        from datetime import timedelta
        
        # Find lotteries ending in the next 24 hours
        now = timezone.now()
        next_24h = now + timedelta(hours=24)
        
        lotteries = Lottery.objects.filter(
            status='ACTIVE',
            end_date__gte=now,
            end_date__lte=next_24h
        )
        
        count = 0
        for lottery in lotteries:
            # Get all users who have tickets for this lottery
            ticket_users = Ticket.objects.filter(
                lottery=lottery
            ).values_list('user', flat=True).distinct()
            
            hours_remaining = (lottery.end_date - now).total_seconds() / 3600
            
            for user_id in ticket_users:
                try:
                    send_lottery_ending_soon_task.delay(
                        str(user_id),
                        str(lottery.id),
                        int(hours_remaining)
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Error sending reminder to user {user_id}: {str(e)}")
        
        return f"Sent {count} reminders"
    except Exception as e:
        logger.error(f"Error sending draw reminders: {str(e)}")
        raise


@shared_task
def update_lottery_statuses():
    """Update lottery statuses based on dates."""
    try:
        now = timezone.now()
        
        # Update lotteries that should be active
        Lottery.objects.filter(
            status='DRAFT',
            start_date__lte=now,
            end_date__gte=now
        ).update(status='ACTIVE')
        
        # Update lotteries that should be closed
        Lottery.objects.filter(
            status='ACTIVE',
            end_date__lt=now
        ).update(status='CLOSED')
        
        return "Updated lottery statuses"
    except Exception as e:
        logger.error(f"Error updating lottery statuses: {str(e)}")
        raise
