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

    # ── Game-specific metrics ────────────────────────────────────────

    @staticmethod
    def get_game_metrics(start_date=None, end_date=None):
        """
        Get game platform KPIs: GGR, NGR, RTP, and per-game breakdown.

        GGR (Gross Gaming Revenue) = total bets - total payouts
        NGR (Net Gaming Revenue) = GGR - bonuses
        RTP (Return to Player %) = (total payouts / total bets) * 100
        """
        from apps.games.models import GameRoom, GameRoomPlayer
        from apps.slots.models import SlotsSpin

        if start_date is None:
            start_date = timezone.now() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now()

        # Game room bets and payouts
        room_bets = Transaction.objects.filter(
            type__in=['BET', 'GAME_BET'],
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        room_payouts = Transaction.objects.filter(
            type__in=['WINNING', 'GAME_WIN'],
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Slots bets and payouts
        slots_bets = Transaction.objects.filter(
            type='SLOTS_BET',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        slots_payouts = Transaction.objects.filter(
            type='SLOTS_WIN',
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Bonuses paid
        bonuses = Transaction.objects.filter(
            type__in=['CASHBACK', 'BONUS'],
            status='COMPLETED',
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_bets = room_bets + slots_bets
        total_payouts = room_payouts + slots_payouts
        ggr = total_bets - total_payouts
        ngr = ggr - bonuses
        rtp = (total_payouts / total_bets * 100) if total_bets > 0 else Decimal('0')

        # Per-game-kind breakdown
        game_breakdown = {}
        rooms = GameRoom.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).values('game_kind').annotate(
            room_count=Count('id'),
            player_count=Count('players'),
        )
        for row in rooms:
            game_breakdown[row['game_kind']] = {
                'rooms': row['room_count'],
                'players': row['player_count'],
            }

        # Slots breakdown
        slot_stats = SlotsSpin.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).aggregate(
            spin_count=Count('id'),
            total_wagered=Sum('bet_amount'),
            total_paid=Sum('payout'),
        )
        slot_wagered = slot_stats['total_wagered'] or Decimal('0')
        slot_paid = slot_stats['total_paid'] or Decimal('0')
        slot_rtp = (slot_paid / slot_wagered * 100) if slot_wagered > 0 else Decimal('0')

        return {
            'total_bets': str(total_bets),
            'total_payouts': str(total_payouts),
            'ggr': str(ggr),
            'ngr': str(ngr),
            'rtp': str(rtp.quantize(Decimal('0.01'))),
            'bonuses_paid': str(bonuses),
            'game_breakdown': game_breakdown,
            'slots': {
                'total_spins': slot_stats['spin_count'] or 0,
                'total_wagered': str(slot_wagered),
                'total_paid': str(slot_paid),
                'rtp': str(slot_rtp.quantize(Decimal('0.01'))),
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
        }

