"""
Analytics service for referrals.
"""
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from apps.referrals.models import (
    ReferralProgram, ReferralLink, Referral,
    ReferralBonus, ReferralWithdrawal
)


class ReferralAnalytics:
    """Analytics service for referral system."""
    
    @staticmethod
    def get_user_stats(user):
        """
        Get referral statistics for a user.
        
        Args:
            user: User instance
        
        Returns:
            Dictionary with statistics
        """
        try:
            link = user.referral_link
        except ReferralLink.DoesNotExist:
            return {
                'total_referred': 0,
                'total_bonus_earned': 0,
                'pending_referrals': 0,
                'qualified_referrals': 0,
                'available_balance': 0,
                'pending_withdrawals': 0,
                'total_withdrawn': 0,
            }
        
        referrals = Referral.objects.filter(referrer=user)
        pending = referrals.filter(status='PENDING').count()
        qualified = referrals.filter(status='QUALIFIED').count()
        bonus_awarded = referrals.filter(status='BONUS_AWARDED').count()
        
        bonuses = ReferralBonus.objects.filter(
            user=user,
            status='CREDITED'
        )
        available_balance = bonuses.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        pending_withdrawals = ReferralWithdrawal.objects.filter(
            user=user,
            status__in=['PENDING', 'APPROVED', 'PROCESSING']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_withdrawn = ReferralWithdrawal.objects.filter(
            user=user,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'total_referred': link.total_referred,
            'total_bonus_earned': float(link.total_bonus_earned),
            'pending_referrals': pending,
            'qualified_referrals': qualified,
            'bonus_awarded_referrals': bonus_awarded,
            'available_balance': float(available_balance),
            'pending_withdrawals': float(pending_withdrawals),
            'total_withdrawn': float(total_withdrawn),
            'referral_code': link.referral_code,
            'referral_url': f'/register?ref={link.referral_code}',
        }
    
    @staticmethod
    def get_top_referrers(limit=10):
        """
        Get top referrers by total bonus earned.
        
        Args:
            limit: Number of top referrers to return
        
        Returns:
            List of dictionaries with referrer stats
        """
        links = ReferralLink.objects.order_by('-total_bonus_earned')[:limit]
        
        return [
            {
                'user': link.user.username,
                'total_referred': link.total_referred,
                'total_bonus_earned': float(link.total_bonus_earned),
                'referral_code': link.referral_code,
            }
            for link in links
        ]
    
    @staticmethod
    def get_conversion_rate(days=30):
        """
        Calculate referral conversion rate.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Conversion rate percentage
        """
        start_date = timezone.now() - timedelta(days=days)
        
        total_referrals = Referral.objects.filter(
            created_at__gte=start_date
        ).count()
        
        successful_referrals = Referral.objects.filter(
            created_at__gte=start_date,
            status='BONUS_AWARDED'
        ).count()
        
        if total_referrals == 0:
            return 0.0
        
        return (successful_referrals / total_referrals) * 100
    
    @staticmethod
    def get_program_stats():
        """
        Get overall referral program statistics.
        
        Returns:
            Dictionary with program stats
        """
        program = ReferralProgram.get_program()
        
        total_referrals = Referral.objects.count()
        successful_referrals = Referral.objects.filter(
            status='BONUS_AWARDED'
        ).count()
        
        total_bonuses_awarded = ReferralBonus.objects.filter(
            status='CREDITED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_withdrawals = ReferralWithdrawal.objects.filter(
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'program_status': program.status,
            'total_referrals': total_referrals,
            'successful_referrals': successful_referrals,
            'conversion_rate': (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0,
            'total_bonuses_awarded': float(total_bonuses_awarded),
            'total_withdrawals': float(total_withdrawals),
            'referral_bonus_amount': float(program.referral_bonus_amount),
            'referred_user_bonus': float(program.referred_user_bonus),
        }

