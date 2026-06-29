"""
Signals for transaction app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.transactions.models import Transaction
from apps.referrals.services import ReferralService


@receiver(post_save, sender=Transaction)
def track_referral_deposit(sender, instance, created, **kwargs):
    """
    Track deposits by referred users for referral qualification.
    """
    if not created:
        return
    
    # Only track successful deposits
    if instance.type == 'DEPOSIT' and instance.status == 'COMPLETED':
        ReferralService.update_referral_deposit(instance.user, instance.amount)

