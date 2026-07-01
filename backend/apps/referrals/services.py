"""
Services for referral operations.

All money movements go through WalletService with idempotency keys
to guarantee ledger correctness and prevent duplicate processing.
"""
import logging
from django.utils import timezone
from django.db import transaction
from apps.referrals.models import (
    ReferralProgram, ReferralLink, Referral,
    ReferralBonus, ReferralWithdrawal
)
from apps.transactions.models import Transaction
from apps.users.models import UserProfile
from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry
from apps.notifications.tasks import send_referral_bonus_credited_task
from apps.common.exceptions import ReferralError

logger = logging.getLogger(__name__)


class ReferralService:
    """Service for referral operations."""
    
    @staticmethod
    @transaction.atomic
    def track_referral(referred_user, referral_code=None):
        """
        Track a referral when a new user registers with a referral code.
        
        Args:
            referred_user: Newly registered user
            referral_code: Referral code used during registration
        
        Returns:
            Referral instance if created, None otherwise
        """
        if not referral_code:
            return None
        
        try:
            # Find referrer by referral code
            referrer_link = ReferralLink.objects.get(referral_code=referral_code)
            referrer = referrer_link.user
            
            # Don't allow self-referral
            if referrer.id == referred_user.id:
                return None
            
            # Check if referral already exists
            if Referral.objects.filter(referred_user=referred_user).exists():
                return None
            
            # Get program settings
            program = ReferralProgram.get_program()
            
            if program.status != 'ACTIVE':
                logger.warning(f"Referral program is not active. Status: {program.status}")
                return None
            
            # Create referral record
            referral = Referral.objects.create(
                referrer=referrer,
                referred_user=referred_user,
                status='PENDING',
                referrer_bonus=program.referral_bonus_amount,
                referred_user_bonus=program.referred_user_bonus
            )
            
            logger.info(f"Referral tracked: {referrer.username} referred {referred_user.username}")
            
            return referral
            
        except ReferralLink.DoesNotExist:
            logger.warning(f"Invalid referral code: {referral_code}")
            return None
        except Exception as e:
            logger.error(f"Error tracking referral: {str(e)}")
            return None
    
    @staticmethod
    @transaction.atomic
    def check_and_approve_referral(referral):
        """
        Check if referral meets requirements and approve if so.
        
        Args:
            referral: Referral instance
        
        Returns:
            True if approved, False otherwise
        """
        program = ReferralProgram.get_program()
        
        if program.status != 'ACTIVE':
            return False
        
        # Check if referral is already processed
        if referral.status != 'PENDING':
            return False
        
        # Check if minimum deposit requirement is met
        if referral.referred_user_deposit < program.minimum_referral_deposit:
            return False
        
        # Approve referral
        referral.status = 'QUALIFIED'
        referral.deposit_date = timezone.now()
        referral.save()
        
        # Award bonuses
        ReferralService.award_referral_bonuses(referral)
        
        return True
    
    @staticmethod
    @transaction.atomic
    def award_referral_bonuses(referral):
        """
        Award bonuses to referrer and referred user.
        
        Args:
            referral: Referral instance
        """
        program = ReferralProgram.get_program()
        
        # Create bonus records
        referrer_bonus = ReferralBonus.objects.create(
            user=referral.referrer,
            referral=referral,
            bonus_type='REFERRER',
            amount=program.referral_bonus_amount,
            status='CREDITED',
            credited_at=timezone.now()
        )
        
        referred_bonus = ReferralBonus.objects.create(
            user=referral.referred_user,
            referral=referral,
            bonus_type='REFERRED',
            amount=program.referred_user_bonus,
            status='CREDITED',
            credited_at=timezone.now()
        )
        
        # Credit bonuses via WalletService (creates ledger entries with idempotency)
        referrer_idem = f'referral_bonus_{referral.id}_referrer'
        referred_idem = f'referral_bonus_{referral.id}_referred'

        WalletService.credit(
            user=referral.referrer,
            amount=program.referral_bonus_amount,
            entry_type=LedgerEntry.BONUS,
            description=f'Referral bonus for referring {referral.referred_user.username}',
            reference_type='REFERRAL',
            reference_id=str(referral.id),
            idempotency_key=referrer_idem,
            actor='referral_service',
        )
        WalletService.credit(
            user=referral.referred_user,
            amount=program.referred_user_bonus,
            entry_type=LedgerEntry.BONUS,
            description=f'Welcome bonus for being referred by {referral.referrer.username}',
            reference_type='REFERRAL',
            reference_id=str(referral.id),
            idempotency_key=referred_idem,
            actor='referral_service',
        )
        logger.info(
            f"Referral bonuses credited via ledger: referrer={referral.referrer.id} "
            f"referred={referral.referred_user.id}"
        )

        # Create transaction records for analytics/reporting
        Transaction.objects.create(
            user=referral.referrer,
            type='REFERRAL_BONUS',
            amount=program.referral_bonus_amount,
            status='COMPLETED',
            description=f'Referral bonus for referring {referral.referred_user.username}',
            reference_id=referrer_idem,
        )
        Transaction.objects.create(
            user=referral.referred_user,
            type='REFERRAL_BONUS',
            amount=program.referred_user_bonus,
            status='COMPLETED',
            description=f'Welcome bonus for being referred by {referral.referrer.username}',
            reference_id=referred_idem,
        )
        
        # Update referral link stats
        referral.referrer.referral_link.total_referred += 1
        referral.referrer.referral_link.total_bonus_earned += program.referral_bonus_amount
        referral.referrer.referral_link.save()
        
        # Update user profiles
        referrer_profile, _ = UserProfile.objects.get_or_create(user=referral.referrer)
        referrer_profile.total_referrals += 1
        referrer_profile.total_referral_earnings += float(program.referral_bonus_amount)
        referrer_profile.save()
        
        # Update referral status
        referral.status = 'BONUS_AWARDED'
        referral.bonus_awarded_at = timezone.now()
        referral.save()
        
        # Send notification emails
        send_referral_bonus_credited_task.delay(
            str(referral.referrer.id),
            float(program.referral_bonus_amount),
            str(referral.id)
        )
        
        send_referral_bonus_credited_task.delay(
            str(referral.referred_user.id),
            float(program.referred_user_bonus),
            str(referral.id)
        )
        
        logger.info(f"Bonuses awarded for referral {referral.id}")
    
    @staticmethod
    def update_referral_deposit(referred_user, deposit_amount):
        """
        Update referral deposit tracking when referred user makes a deposit.
        
        Args:
            referred_user: User who made the deposit
            deposit_amount: Amount deposited
        """
        try:
            referral = Referral.objects.get(
                referred_user=referred_user,
                status='PENDING'
            )
            
            referral.referred_user_deposit += deposit_amount
            referral.save()
            
            # Check if referral should be approved
            ReferralService.check_and_approve_referral(referral)
            
        except Referral.DoesNotExist:
            # No pending referral for this user
            pass
        except Exception as e:
            logger.error(f"Error updating referral deposit: {str(e)}")

