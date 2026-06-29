from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import ReferralLink, ReferralProgram, Referral
from .services import ReferralService
import string
import random
from django.utils import timezone


@receiver(post_save, sender=User)
def create_referral_link(sender, instance, created, **kwargs):
    """
    Automatically create a referral link when a new user is created.
    Also track referral if user registered with a referral code.
    """
    if created:
        # Check if referral link already exists
        if not hasattr(instance, 'referral_link'):
            # Generate unique referral code
            code = generate_referral_code()
            ReferralLink.objects.create(
                user=instance,
                referral_code=code
            )
        
        # Check if user registered with a referral code
        # This would be set during registration - you may need to adjust based on your registration flow
        referral_code = getattr(instance, '_referral_code', None)
        if referral_code:
            ReferralService.track_referral(instance, referral_code)


@receiver(post_save, sender=ReferralProgram)
def ensure_single_program(sender, instance, **kwargs):
    """
    Ensure only one referral program exists.
    Delete duplicates if somehow created.
    """
    if instance.id != 1:
        # Ensure all operations use id=1
        duplicate = ReferralProgram.objects.exclude(id=1).first()
        if duplicate:
            duplicate.delete()


def generate_referral_code():
    """
    Generate a unique referral code.
    Format: YEAR + 12 random characters
    """
    while True:
        code = f'{timezone.now().year}' + ''.join(
            random.choices(string.ascii_letters + string.digits, k=12)
        )
        if not ReferralLink.objects.filter(referral_code=code).exists():
            return code
