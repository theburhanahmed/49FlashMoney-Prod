from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.users.models import User, UserProfile, AuditLog
from apps.notifications.services import EmailService
from apps.notifications.tasks import send_welcome_email_task
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create UserProfile automatically when User is created
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
        # Send welcome email asynchronously
        try:
            send_welcome_email_task.delay(str(instance.id))
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            # Fallback to synchronous sending if Celery is not available
            try:
                EmailService.send_welcome_email(instance)
            except Exception as e2:
                logger.error(f"Error sending welcome email synchronously: {e2}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save UserProfile when User is saved
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(pre_save, sender=User)
def log_user_changes(sender, instance, **kwargs):
    """
    Signal to log user changes
    """
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.wallet_balance != instance.wallet_balance:
            # Wallet balance changed - this will be logged in the transaction
            pass
    except sender.DoesNotExist:
        # New user being created
        pass
