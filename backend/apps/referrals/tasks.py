"""
Celery tasks for referral system.
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Q
import logging

from apps.referrals.models import Referral, ReferralBonus, ReferralProgram

logger = logging.getLogger(__name__)


@shared_task
def check_referral_bonus_expiry():
    """Check and expire old referral bonuses."""
    logger.info('Running task: check_referral_bonus_expiry')
    
    now = timezone.now()
    expired_count = 0
    
    # Find bonuses that are pending and past expiry
    # Note: ReferralBonus doesn't have expiry date directly,
    # but we can check via the referral's expires_at
    expired_bonuses = ReferralBonus.objects.filter(
        status='PENDING'
    ).filter(
        referral__expires_at__lt=now,
        referral__status='PENDING'
    )
    
    for bonus in expired_bonuses:
        bonus.status = 'EXPIRED'
        bonus.save()
        expired_count += 1
        logger.info(f'Expired referral bonus {bonus.id}')
    
    logger.info(f'Expired {expired_count} referral bonuses')
    return f'Expired {expired_count} referral bonuses'


@shared_task
def process_pending_referrals():
    """Process pending referrals and award bonuses if requirements are met."""
    logger.info('Running task: process_pending_referrals')
    
    program = ReferralProgram.get_program()
    
    if program.status != 'ACTIVE':
        logger.info('Referral program is not active, skipping processing')
        return 'Referral program is not active'
    
    # Find pending referrals where requirements might be met
    pending_referrals = Referral.objects.filter(status='PENDING')
    processed_count = 0
    
    for referral in pending_referrals:
        try:
            # Check if referred user has made required deposit
            from apps.transactions.models import Transaction
            
            total_deposits = Transaction.objects.filter(
                user=referral.referred_user,
                type='DEPOSIT',
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if float(total_deposits) >= float(program.minimum_referral_deposit):
                # Requirements met, qualify the referral
                referral.status = 'QUALIFIED'
                referral.referred_user_deposit = total_deposits
                referral.deposit_date = timezone.now()
                referral.save()
                
                # Award bonuses
                from django.utils import timezone as tz
                
                # Referrer bonus
                referrer_bonus = ReferralBonus.objects.create(
                    user=referral.referrer,
                    referral=referral,
                    bonus_type='REFERRER',
                    amount=program.referral_bonus_amount,
                    status='CREDITED',
                    credited_at=tz.now()
                )
                
                # Credit to referrer's referral balance
                referral.referrer.add_balance(program.referral_bonus_amount)
                
                # Referred user bonus
                referred_bonus = ReferralBonus.objects.create(
                    user=referral.referred_user,
                    referral=referral,
                    bonus_type='REFERRED',
                    amount=program.referred_user_bonus,
                    status='CREDITED',
                    credited_at=tz.now()
                )
                
                # Credit to referred user's wallet
                referral.referred_user.add_balance(program.referred_user_bonus)
                
                referral.status = 'BONUS_AWARDED'
                referral.bonus_awarded_at = tz.now()
                referral.save()
                
                processed_count += 1
                logger.info(f'Processed referral {referral.id}, bonuses awarded')
                
        except Exception as e:
            logger.error(f'Error processing referral {referral.id}: {str(e)}', exc_info=True)
    
    logger.info(f'Processed {processed_count} referrals')
    return f'Processed {processed_count} referrals'

