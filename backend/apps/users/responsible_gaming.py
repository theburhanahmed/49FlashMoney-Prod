"""
Service for responsible gaming checks and limits.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
import logging

from apps.transactions.models import Transaction

logger = logging.getLogger(__name__)


class ResponsibleGamingService:
    """Service for responsible gaming limit checks and self-exclusion."""
    
    @staticmethod
    def check_self_exclusion(user):
        """
        Check if user is self-excluded.
        
        Args:
            user: User to check
            
        Returns:
            tuple: (is_excluded: bool, reason: str or None)
        """
        if not user.self_excluded:
            return False, None
        
        if user.self_exclusion_until:
            if timezone.now() < user.self_exclusion_until:
                return True, f'Self-excluded until {user.self_exclusion_until.strftime("%Y-%m-%d %H:%M")}'
            else:
                # Exclusion period expired, reset
                user.self_excluded = False
                user.self_exclusion_until = None
                user.save()
                return False, None
        
        # Permanent exclusion
        return True, 'Permanently self-excluded'
    
    @staticmethod
    def check_deposit_limit(user, amount):
        """
        Check if deposit amount exceeds user's deposit limits.
        
        Args:
            user: User making deposit
            amount: Deposit amount
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        amount = Decimal(str(amount))
        now = timezone.now()
        
        # Check daily limit
        if user.daily_deposit_limit:
            daily_total = ResponsibleGamingService._calculate_daily_deposits(user, now.date())
            if daily_total + amount > user.daily_deposit_limit:
                remaining = user.daily_deposit_limit - daily_total
                return False, f'Daily deposit limit exceeded. Remaining: ${remaining}'
        
        # Check weekly limit
        if user.weekly_deposit_limit:
            week_start = now - timedelta(days=now.weekday())
            weekly_total = ResponsibleGamingService._calculate_weekly_deposits(user, week_start.date())
            if weekly_total + amount > user.weekly_deposit_limit:
                remaining = user.weekly_deposit_limit - weekly_total
                return False, f'Weekly deposit limit exceeded. Remaining: ${remaining}'
        
        # Check monthly limit
        if user.monthly_deposit_limit:
            month_start = date(now.year, now.month, 1)
            monthly_total = ResponsibleGamingService._calculate_monthly_deposits(user, month_start)
            if monthly_total + amount > user.monthly_deposit_limit:
                remaining = user.monthly_deposit_limit - monthly_total
                return False, f'Monthly deposit limit exceeded. Remaining: ${remaining}'
        
        return True, None
    
    @staticmethod
    def check_loss_limit(user, amount):
        """
        Check if loss amount (from ticket purchases) exceeds user's loss limits.
        
        Args:
            user: User making purchase
            amount: Purchase amount (which becomes a loss if ticket doesn't win)
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not user.daily_loss_limit:
            return True, None
        
        amount = Decimal(str(amount))
        now = timezone.now()
        
        # Calculate today's losses (ticket purchases without wins)
        today_losses = ResponsibleGamingService._calculate_daily_losses(user, now.date())
        
        if today_losses + amount > user.daily_loss_limit:
            remaining = user.daily_loss_limit - today_losses
            return False, f'Daily loss limit exceeded. Remaining: ${remaining}'
        
        return True, None
    
    @staticmethod
    def check_session_time(user):
        """
        Check if user has exceeded session time limit.
        
        Args:
            user: User to check
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None, minutes_remaining: int or None)
        """
        if not user.session_time_limit or not user.last_session_start:
            return True, None, None
        
        now = timezone.now()
        session_duration = (now - user.last_session_start).total_seconds() / 60  # minutes
        
        if session_duration >= user.session_time_limit:
            return False, f'Session time limit of {user.session_time_limit} minutes exceeded. Please take a break.', None
        
        minutes_remaining = int(user.session_time_limit - session_duration)
        return True, None, minutes_remaining
    
    @staticmethod
    def apply_self_exclusion(user, days=None):
        """
        Apply self-exclusion to user.
        
        Args:
            user: User to exclude
            days: Number of days to exclude (None for permanent)
            
        Returns:
            bool: Success status
        """
        user.self_excluded = True
        if days:
            user.self_exclusion_until = timezone.now() + timedelta(days=days)
        else:
            user.self_exclusion_until = None  # Permanent
        user.save()
        
        logger.info(f'Applied self-exclusion to user {user.id} for {days} days' if days else 'permanently')
        return True
    
    @staticmethod
    def _calculate_daily_deposits(user, target_date):
        """Calculate total deposits for a specific date."""
        start_datetime = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        deposits = Transaction.objects.filter(
            user=user,
            type='DEPOSIT',
            status='COMPLETED',
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).aggregate(total=Sum('amount'))
        
        return deposits['total'] or Decimal('0.00')
    
    @staticmethod
    def _calculate_weekly_deposits(user, week_start_date):
        """Calculate total deposits for a week starting from week_start_date."""
        start_datetime = timezone.make_aware(datetime.combine(week_start_date, datetime.min.time()))
        end_datetime = start_datetime + timedelta(days=7)
        
        deposits = Transaction.objects.filter(
            user=user,
            type='DEPOSIT',
            status='COMPLETED',
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        ).aggregate(total=Sum('amount'))
        
        return deposits['total'] or Decimal('0.00')
    
    @staticmethod
    def _calculate_monthly_deposits(user, month_start_date):
        """Calculate total deposits for a month starting from month_start_date."""
        start_datetime = timezone.make_aware(datetime.combine(month_start_date, datetime.min.time()))
        
        # Get first day of next month
        if month_start_date.month == 12:
            next_month = datetime(month_start_date.year + 1, 1, 1)
        else:
            next_month = datetime(month_start_date.year, month_start_date.month + 1, 1)
        
        end_datetime = timezone.make_aware(next_month)
        
        deposits = Transaction.objects.filter(
            user=user,
            type='DEPOSIT',
            status='COMPLETED',
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        ).aggregate(total=Sum('amount'))
        
        return deposits['total'] or Decimal('0.00')
    
    @staticmethod
    def _calculate_daily_losses(user, target_date):
        """Calculate total losses (ticket purchases) for a specific date."""
        start_datetime = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        
        # Get ticket purchases and slots bets (both count as spending)
        purchases = Transaction.objects.filter(
            user=user,
            type__in=['TICKET_PURCHASE', 'SLOTS_BET', 'GAME_ENTRY'],
            status='COMPLETED',
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).aggregate(total=Sum('amount'))
        
        # Get prizes won on this date (to subtract from losses)
        prizes = Transaction.objects.filter(
            user=user,
            type__in=['PRIZE_AWARD', 'SLOTS_WIN', 'GAME_WIN'],
            status='COMPLETED',
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).aggregate(total=Sum('amount'))
        
        total_purchases = purchases['total'] or Decimal('0.00')
        total_prizes = prizes['total'] or Decimal('0.00')
        
        # Loss = purchases - prizes
        return max(Decimal('0.00'), total_purchases - total_prizes)

