"""
Service for withdrawal operations and validation.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
import logging

from apps.transactions.models import WithdrawalRequest, Transaction

logger = logging.getLogger(__name__)


class WithdrawalService:
    """Service for handling withdrawal requests and validations."""
    
    # Default withdrawal limits (can be overridden in settings)
    MIN_WITHDRAWAL_AMOUNT = getattr(settings, 'WITHDRAWAL_MIN_AMOUNT', Decimal('10.00'))
    MAX_WITHDRAWAL_AMOUNT = getattr(settings, 'WITHDRAWAL_MAX_AMOUNT', Decimal('10000.00'))
    DAILY_WITHDRAWAL_LIMIT = getattr(settings, 'WITHDRAWAL_DAILY_LIMIT', Decimal('1000.00'))
    MONTHLY_WITHDRAWAL_LIMIT = getattr(settings, 'WITHDRAWAL_MONTHLY_LIMIT', Decimal('5000.00'))
    
    @classmethod
    def get_referral_bonus_balance(cls, user):
        """
        Calculate the total referral bonus balance for a user.
        This amount is NOT withdrawable.
        """
        from apps.referrals.models import ReferralBonus
        
        try:
            bonuses = ReferralBonus.objects.filter(
                user=user,
                status='CREDITED'
            ).aggregate(total=Sum('amount'))
            return bonuses['total'] or Decimal('0.00')
        except Exception as e:
            logger.error(f"Error calculating referral bonus balance: {e}")
            return Decimal('0.00')
    
    @classmethod
    def get_withdrawable_balance(cls, user):
        """
        Calculate the withdrawable balance for a user.
        This excludes referral bonus amounts which cannot be withdrawn.
        """
        referral_balance = cls.get_referral_bonus_balance(user)
        withdrawable = user.wallet_balance - referral_balance
        return max(withdrawable, Decimal('0.00'))
    
    @classmethod
    def validate_withdrawal_request(cls, user, amount):
        """
        Validate a withdrawal request against all limits and rules.
        
        Args:
            user: User requesting withdrawal
            amount: Withdrawal amount
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        amount = Decimal(str(amount))
        
        # Check minimum withdrawal amount
        if amount < cls.MIN_WITHDRAWAL_AMOUNT:
            return False, f'Minimum withdrawal amount is ${cls.MIN_WITHDRAWAL_AMOUNT}'
        
        # Check maximum withdrawal amount
        if amount > cls.MAX_WITHDRAWAL_AMOUNT:
            return False, f'Maximum withdrawal amount is ${cls.MAX_WITHDRAWAL_AMOUNT}'
        
        # Check wallet balance
        if user.wallet_balance < amount:
            return False, 'Insufficient wallet balance'
        
        # Check withdrawable balance (excluding referral bonuses)
        withdrawable_balance = cls.get_withdrawable_balance(user)
        if amount > withdrawable_balance:
            referral_balance = cls.get_referral_bonus_balance(user)
            return False, f'Insufficient withdrawable balance. Your referral bonus of ${referral_balance} cannot be withdrawn. Available for withdrawal: ${withdrawable_balance}'
        
        # Check daily limit
        daily_total = cls.calculate_daily_withdrawals(user, timezone.now().date())
        if daily_total + amount > cls.DAILY_WITHDRAWAL_LIMIT:
            remaining = cls.DAILY_WITHDRAWAL_LIMIT - daily_total
            return False, f'Daily withdrawal limit exceeded. Remaining: ${remaining}'
        
        # Check monthly limit
        monthly_total = cls.calculate_monthly_withdrawals(user, timezone.now().date())
        if monthly_total + amount > cls.MONTHLY_WITHDRAWAL_LIMIT:
            remaining = cls.MONTHLY_WITHDRAWAL_LIMIT - monthly_total
            return False, f'Monthly withdrawal limit exceeded. Remaining: ${remaining}'
        
        return True, None
    
    @classmethod
    def calculate_daily_withdrawals(cls, user, target_date=None):
        """
        Calculate total withdrawals for a user on a specific date.
        
        Args:
            user: User to calculate for
            target_date: Date to calculate for (defaults to today)
            
        Returns:
            Decimal: Total withdrawal amount for the date
        """
        if target_date is None:
            target_date = timezone.now().date()
        
        # Get start and end of day in user's timezone
        start_datetime = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        withdrawals = WithdrawalRequest.objects.filter(
            user=user,
            status__in=['APPROVED', 'PROCESSING', 'COMPLETED'],
            requested_at__gte=start_datetime,
            requested_at__lte=end_datetime
        ).aggregate(total=Sum('amount'))
        
        return withdrawals['total'] or Decimal('0.00')
    
    @classmethod
    def calculate_monthly_withdrawals(cls, user, target_date=None):
        """
        Calculate total withdrawals for a user in a specific month.
        
        Args:
            user: User to calculate for
            target_date: Date within the target month (defaults to today)
            
        Returns:
            Decimal: Total withdrawal amount for the month
        """
        if target_date is None:
            target_date = timezone.now().date()
        
        # Get start and end of month
        start_datetime = timezone.make_aware(
            datetime(target_date.year, target_date.month, 1)
        )
        # Get first day of next month, then subtract one day
        if target_date.month == 12:
            next_month = datetime(target_date.year + 1, 1, 1)
        else:
            next_month = datetime(target_date.year, target_date.month + 1, 1)
        
        end_datetime = timezone.make_aware(next_month) - timedelta(seconds=1)
        
        withdrawals = WithdrawalRequest.objects.filter(
            user=user,
            status__in=['APPROVED', 'PROCESSING', 'COMPLETED'],
            requested_at__gte=start_datetime,
            requested_at__lte=end_datetime
        ).aggregate(total=Sum('amount'))
        
        return withdrawals['total'] or Decimal('0.00')
    
    @classmethod
    def check_withdrawal_limits(cls, user, amount):
        """
        Check if withdrawal amount is within all limits.
        Shorthand method that combines all checks.
        
        Args:
            user: User requesting withdrawal
            amount: Withdrawal amount
            
        Returns:
            dict: {
                'valid': bool,
                'errors': list of error messages,
                'limits': dict with limit information
            }
        """
        errors = []
        amount = Decimal(str(amount))
        
        is_valid, error = cls.validate_withdrawal_request(user, amount)
        if not is_valid:
            errors.append(error)
        
        daily_total = cls.calculate_daily_withdrawals(user)
        monthly_total = cls.calculate_monthly_withdrawals(user)
        referral_balance = cls.get_referral_bonus_balance(user)
        withdrawable_balance = cls.get_withdrawable_balance(user)
        
        limits_info = {
            'min_amount': str(cls.MIN_WITHDRAWAL_AMOUNT),
            'max_amount': str(cls.MAX_WITHDRAWAL_AMOUNT),
            'daily_limit': str(cls.DAILY_WITHDRAWAL_LIMIT),
            'daily_used': str(daily_total),
            'daily_remaining': str(cls.DAILY_WITHDRAWAL_LIMIT - daily_total),
            'monthly_limit': str(cls.MONTHLY_WITHDRAWAL_LIMIT),
            'monthly_used': str(monthly_total),
            'monthly_remaining': str(cls.MONTHLY_WITHDRAWAL_LIMIT - monthly_total),
            'wallet_balance': str(user.wallet_balance),
            'referral_balance': str(referral_balance),
            'withdrawable_balance': str(withdrawable_balance),
        }
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'limits': limits_info
        }

