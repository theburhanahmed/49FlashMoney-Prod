"""
Services for lottery operations.

All money movements go through WalletService with idempotency keys
to guarantee ledger correctness and prevent duplicate processing.
"""
import secrets
import logging
import uuid
from django.utils import timezone
from django.db import transaction
from apps.lotteries.models import Lottery, Ticket, Winner, LotteryDrawLog
from apps.transactions.models import Transaction
from apps.users.models import UserProfile, AuditLog
from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry
from apps.common.exceptions import DrawError, LotteryError

logger = logging.getLogger(__name__)


class DrawService:
    """Service for conducting lottery draws."""
    
    @staticmethod
    @transaction.atomic
    def conduct_draw(lottery, conducted_by=None):
        """
        Conduct a lottery draw using cryptographically secure random selection.
        
        Args:
            lottery: Lottery instance
            conducted_by: User who conducted the draw (optional)
        
        Returns:
            Winner instance
        
        Raises:
            DrawError if draw cannot be conducted
        """
        # Validate lottery can be drawn
        if lottery.status != 'CLOSED':
            raise DrawError('Lottery must be closed before draw can be conducted')
        
        if lottery.draw_date > timezone.now():
            raise DrawError('Draw date has not been reached yet')
        
        # Get all tickets
        tickets = list(Ticket.objects.filter(lottery=lottery))
        if not tickets:
            raise DrawError('No tickets purchased for this lottery')
        
        # Use cryptographically secure random selection
        random_seed = secrets.token_hex(32)
        random_index = secrets.randbelow(len(tickets))
        winning_ticket = tickets[random_index]
        
        # Create winner record
        winner = Winner.objects.create(
            user=winning_ticket.user,
            lottery=lottery,
            ticket=winning_ticket,
            prize_amount=lottery.prize_amount
        )
        
        # Mark ticket as winner
        winning_ticket.is_winner = True
        winning_ticket.save()
        
        # Create draw log
        LotteryDrawLog.objects.create(
            lottery=lottery,
            conducted_by=conducted_by,
            total_participants=lottery.get_total_participants(),
            total_tickets_sold=lottery.get_total_tickets_sold(),
            revenue=lottery.get_revenue(),
            random_seed=random_seed
        )
        
        # Update lottery status
        lottery.status = 'DRAWN'
        lottery.save()
        
        # Credit prize to winner's wallet via WalletService (creates ledger entry)
        idempotency_key = f'lottery_prize_{lottery.id}_{winner.id}'
        WalletService.credit(
            user=winner.user,
            amount=lottery.prize_amount,
            entry_type=LedgerEntry.WINNING,
            description=f'Prize awarded for winning {lottery.name}',
            reference_type='LOTTERY',
            reference_id=str(lottery.id),
            idempotency_key=idempotency_key,
            actor='draw_service',
        )
        logger.info(
            f"Prize credited via ledger: user={winner.user.id} "
            f"amount={lottery.prize_amount} key={idempotency_key}"
        )
        
        # Create transaction record for analytics/reporting
        Transaction.objects.create(
            user=winner.user,
            type='PRIZE_AWARD',
            amount=lottery.prize_amount,
            status='COMPLETED',
            lottery=lottery,
            description=f'Prize awarded for winning {lottery.name}',
            reference_id=idempotency_key,
        )
        
        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(user=winner.user)
        profile.total_won += float(lottery.prize_amount)
        profile.total_wins += 1
        profile.save()
        
        # Log action
        AuditLog.objects.create(
            user=conducted_by,
            action='WIN',
            description=f'Lottery draw conducted for {lottery.name}. Winner: {winner.user.username}'
        )
        
        logger.info(f"Draw conducted for lottery {lottery.id}. Winner: {winner.user.username}")
        
        # Send email notifications
        try:
            from apps.notifications.tasks import (
                send_draw_result_win_task,
                send_draw_result_loss_task
            )
            
            # Send email to winner
            send_draw_result_win_task.delay(
                str(winner.user.id),
                str(winner.id),
                str(lottery.id)
            )
            
            # Send emails to all participants who didn't win
            participant_ids = list(
                Ticket.objects.filter(lottery=lottery)
                .exclude(user=winner.user)
                .values_list('user_id', flat=True)
                .distinct()
            )
            
            for user_id in participant_ids:
                send_draw_result_loss_task.delay(str(user_id), str(lottery.id))
                
        except Exception as e:
            logger.error(f"Error sending draw result emails: {e}")
        
        return winner


class TicketPurchaseService:
    """Service for ticket purchase operations."""
    
    @staticmethod
    @transaction.atomic
    def purchase_ticket(user, lottery, quantity=1):
        """
        Purchase ticket(s) for a lottery.
        
        Args:
            user: User instance
            lottery: Lottery instance
            quantity: Number of tickets to purchase (default: 1)
        
        Returns:
            List of Ticket instances
        
        Raises:
            LotteryError if purchase cannot be completed
        """
        # Validate lottery is active
        if lottery.status != 'ACTIVE':
            raise LotteryError('Lottery is not active')
        
        # Check if lottery is within sale period
        if not lottery.is_within_sale_period():
            raise LotteryError('Lottery is not currently accepting ticket purchases')
        
        # Check available tickets
        if lottery.available_tickets < quantity:
            raise LotteryError(f'Only {lottery.available_tickets} tickets available')
        
        # Calculate total cost
        total_cost = lottery.ticket_price * quantity
        
        # Check max tickets per user
        user_ticket_count = lottery.get_user_ticket_count(user)
        if user_ticket_count + quantity > lottery.max_tickets_per_user:
            raise LotteryError(f'Maximum {lottery.max_tickets_per_user} tickets per user allowed')
        
        # Debit from wallet via WalletService (balance check + ledger entry, under row lock)
        idempotency_key = f'ticket_purchase_{lottery.id}_{user.id}_{uuid.uuid4().hex[:8]}'
        try:
            WalletService.debit(
                user=user,
                amount=total_cost,
                entry_type=LedgerEntry.BET,
                description=f'Purchased {quantity} ticket(s) for {lottery.name}',
                reference_type='LOTTERY',
                reference_id=str(lottery.id),
                idempotency_key=idempotency_key,
                actor='ticket_purchase_service',
            )
        except Exception as e:
            # Re-raise wallet errors as LotteryError for consistent error handling
            from apps.wallet.services import InsufficientBalanceError, WalletFrozenError
            if isinstance(e, InsufficientBalanceError):
                raise LotteryError('Insufficient balance')
            if isinstance(e, WalletFrozenError):
                raise LotteryError('Wallet is frozen')
            raise
        
        # Generate ticket numbers
        last_ticket = Ticket.objects.filter(lottery=lottery).order_by('ticket_number').last()
        start_number = (last_ticket.ticket_number + 1) if last_ticket else 1
        
        tickets = []
        for i in range(quantity):
            ticket = Ticket.objects.create(
                user=user,
                lottery=lottery,
                ticket_number=start_number + i
            )
            tickets.append(ticket)
        
        # Update lottery available count
        lottery.available_tickets -= quantity
        lottery.save()
        
        # Create transaction record for analytics/reporting
        Transaction.objects.create(
            user=user,
            type='TICKET_PURCHASE',
            amount=total_cost,
            status='COMPLETED',
            lottery=lottery,
            description=f'Purchased {quantity} ticket(s) for {lottery.name}',
            reference_id=idempotency_key,
        )
        
        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.total_spent += float(total_cost)
        profile.total_tickets_bought += quantity
        if profile.total_lotteries_participated == 0 or lottery.id not in [t.lottery.id for t in user.tickets.all()]:
            profile.total_lotteries_participated += 1
        profile.save()
        
        # Log action
        AuditLog.objects.create(
            user=user,
            action='BUY_TICKET',
            description=f'Purchased {quantity} ticket(s) for lottery: {lottery.name}'
        )
        
        logger.info(f"User {user.username} purchased {quantity} ticket(s) for lottery {lottery.id}")
        
        return tickets
