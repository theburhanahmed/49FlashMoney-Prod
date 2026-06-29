"""
Analytics service for calculating dashboard metrics.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.contrib.auth import get_user_model

from apps.lotteries.models import Lottery, Ticket, Winner
from apps.transactions.models import Transaction, WithdrawalRequest
from apps.users.models import User

User = get_user_model()


class AnalyticsService:
    """Service for analytics calculations."""
    
    @staticmethod
    def get_financial_metrics(start_date=None, end_date=None):
        """
        Get financial metrics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            dict: Financial metrics
        """
        if start_date is None:
            start_date = timezone.now() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now()
        
        # Revenue from ticket purchases
        ticket_purchases = Transaction.objects.filter(
            type='TICKET_PURCHASE',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total deposits
        deposits = Transaction.objects.filter(
            type='DEPOSIT',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total withdrawals
        withdrawals = WithdrawalRequest.objects.filter(
            status__in=['APPROVED', 'COMPLETED'],
            requested_at__gte=start_date,
            requested_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total prizes awarded
        prizes = Transaction.objects.filter(
            type='PRIZE_AWARD',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Net revenue = revenue - prizes
        net_revenue = ticket_purchases - prizes
        
        return {
            'revenue': str(ticket_purchases),
            'deposits': str(deposits),
            'withdrawals': str(withdrawals),
            'prizes_awarded': str(prizes),
            'net_revenue': str(net_revenue),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }
        }
    
    @staticmethod
    def get_user_metrics(start_date=None, end_date=None):
        """
        Get user metrics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            dict: User metrics
        """
        if start_date is None:
            start_date = timezone.now() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now()
        
        # Total users
        total_users = User.objects.count()
        
        # Active users (logged in within last 30 days)
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # New registrations
        new_registrations = User.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Users with tickets
        users_with_tickets = User.objects.filter(
            tickets__isnull=False
        ).distinct().count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_registrations': new_registrations,
            'users_with_tickets': users_with_tickets,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }
        }
    
    @staticmethod
    def get_lottery_metrics(start_date=None, end_date=None):
        """
        Get lottery metrics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            dict: Lottery metrics
        """
        if start_date is None:
            start_date = timezone.now() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now()
        
        # Active lotteries
        active_lotteries = Lottery.objects.filter(status='ACTIVE').count()
        
        # Completed lotteries
        completed_lotteries = Lottery.objects.filter(
            status='DRAWN',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Total tickets sold
        tickets_sold = Ticket.objects.filter(
            purchased_at__gte=start_date,
            purchased_at__lte=end_date
        ).count()
        
        # Revenue from lotteries
        lottery_revenue = Transaction.objects.filter(
            type='TICKET_PURCHASE',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return {
            'active_lotteries': active_lotteries,
            'completed_lotteries': completed_lotteries,
            'tickets_sold': tickets_sold,
            'revenue': str(lottery_revenue),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            }
        }
    
    @staticmethod
    def get_chart_data(metric_type, period='days', days=30):
        """
        Get time-series chart data.
        
        Args:
            metric_type: Type of metric ('revenue', 'users', 'tickets')
            period: Aggregation period ('days', 'weeks', 'months')
            days: Number of days to look back
            
        Returns:
            list: List of data points with labels and values
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        data_points = []
        current_date = start_date
        
        if metric_type == 'revenue':
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                revenue = Transaction.objects.filter(
                    type='TICKET_PURCHASE',
                    status='COMPLETED',
                    created_at__gte=current_date,
                    created_at__lt=next_date
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                data_points.append({
                    'label': current_date.strftime('%Y-%m-%d'),
                    'value': str(revenue)
                })
                current_date = next_date
        
        elif metric_type == 'users':
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                new_users = User.objects.filter(
                    created_at__gte=current_date,
                    created_at__lt=next_date
                ).count()
                
                data_points.append({
                    'label': current_date.strftime('%Y-%m-%d'),
                    'value': new_users
                })
                current_date = next_date
        
        elif metric_type == 'tickets':
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                tickets = Ticket.objects.filter(
                    purchased_at__gte=current_date,
                    purchased_at__lt=next_date
                ).count()
                
                data_points.append({
                    'label': current_date.strftime('%Y-%m-%d'),
                    'value': tickets
                })
                current_date = next_date
        
        return data_points

