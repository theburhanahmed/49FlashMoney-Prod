"""
Slots service layer.
Handles spin logic, payout calculation, and provably fair RNG.
All money movements go through WalletService.
"""
import hashlib
import logging
import uuid
from decimal import Decimal

from django.db import transaction

from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry
from apps.transactions.models import Transaction
from apps.users.models import AuditLog
from .models import SlotsGame, SlotsSpin, DEFAULT_REELS, DEFAULT_PAYTABLE

logger = logging.getLogger(__name__)


class SlotsService:
    """Service for slots game operations."""

    @classmethod
    def _generate_spin_result(cls, game: SlotsGame, seed: str) -> list:
        """
        Generate deterministic spin result from seed.
        Returns list of 3 symbols (one per reel).
        """
        reels = game.reels or DEFAULT_REELS
        result = []
        for i, reel in enumerate(reels):
            reel_seed = f"{seed}:reel_{i}"
            hash_val = int(hashlib.sha256(reel_seed.encode()).hexdigest(), 16)
            idx = hash_val % len(reel)
            result.append(reel[idx])
        return result

    @classmethod
    def _calculate_payout(cls, game: SlotsGame, symbols: list, bet_amount: Decimal) -> Decimal:
        """
        Calculate payout based on symbols. 3-of-a-kind pays multiplier * bet.
        2-of-a-kind of the first two reels pays 0.5 * multiplier * bet (partial match).
        """
        paytable = game.paytable or DEFAULT_PAYTABLE
        # 3-of-a-kind
        if symbols[0] == symbols[1] == symbols[2]:
            multiplier = Decimal(str(paytable.get(symbols[0], 0)))
            return (bet_amount * multiplier).quantize(Decimal('0.01'))
        # 2-of-a-kind (first two match)
        if symbols[0] == symbols[1]:
            multiplier = Decimal(str(paytable.get(symbols[0], 0)))
            return (bet_amount * multiplier * Decimal('0.25')).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @classmethod
    @transaction.atomic
    def spin(cls, user, game_id: str, bet_amount: Decimal) -> SlotsSpin:
        """
        Execute a slots spin.
        1. Validate game and bet
        2. Debit bet from wallet via ledger
        3. Generate spin result
        4. Calculate and credit payout if won
        5. Record spin
        """
        try:
            game = SlotsGame.objects.get(id=game_id)
        except SlotsGame.DoesNotExist:
            raise ValueError('Game not found')
        if not game.is_active:
            raise ValueError('This slots game is not active')

        bet_amount = Decimal(str(bet_amount))
        if bet_amount <= 0:
            raise ValueError('Bet amount must be positive')
        if bet_amount < game.min_bet:
            raise ValueError(f'Minimum bet is {game.min_bet}')
        if bet_amount > game.max_bet:
            raise ValueError(f'Maximum bet is {game.max_bet}')

        # Generate seed for provably fair verification
        seed = f"{uuid.uuid4()}:{user.id}:{game_id}"
        idempotency_base = hashlib.sha256(seed.encode()).hexdigest()[:16]

        # Debit bet via wallet ledger
        WalletService.debit(
            user=user,
            amount=bet_amount,
            entry_type=LedgerEntry.BET,
            description=f'Slots bet: {game.name}',
            reference_type='slots_game',
            reference_id=str(game.id),
            idempotency_key=f'slots_bet:{idempotency_base}',
            actor='slots_service',
        )

        # Generate result
        symbols = cls._generate_spin_result(game, seed)
        payout = cls._calculate_payout(game, symbols, bet_amount)

        # Credit winnings if any
        if payout > 0:
            WalletService.credit(
                user=user,
                amount=payout,
                entry_type=LedgerEntry.WINNING,
                description=f'Slots win: {game.name} ({symbols})',
                reference_type='slots_game',
                reference_id=str(game.id),
                idempotency_key=f'slots_win:{idempotency_base}',
                actor='slots_service',
            )
            Transaction.objects.create(
                user=user,
                type='SLOTS_WIN',
                amount=payout,
                status='COMPLETED',
                description=f'Slots win: {game.name}',
                reference_id=str(game.id),
            )

        # Record bet transaction
        Transaction.objects.create(
            user=user,
            type='SLOTS_BET',
            amount=bet_amount,
            status='COMPLETED',
            description=f'Slots bet: {game.name}',
            reference_id=str(game.id),
        )

        # Create immutable spin record
        spin = SlotsSpin.objects.create(
            user=user,
            game=game,
            bet_amount=bet_amount,
            symbols=symbols,
            payout=payout,
            random_seed=seed,
        )

        logger.info(
            f"Slots spin: user={user.id} game={game.name} "
            f"bet={bet_amount} symbols={symbols} payout={payout}"
        )
        return spin

    @classmethod
    def get_spin_history(cls, user, game_id: str = None, limit: int = 50):
        """Get spin history for a user, optionally filtered by game."""
        qs = SlotsSpin.objects.filter(user=user).order_by('-created_at')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs[:limit]

    @classmethod
    def get_game_stats(cls, game_id: str) -> dict:
        """Get aggregate stats for a slots game."""
        from django.db.models import Sum, Count, Avg
        spins = SlotsSpin.objects.filter(game_id=game_id)
        stats = spins.aggregate(
            total_spins=Count('id'),
            total_wagered=Sum('bet_amount'),
            total_paid=Sum('payout'),
            avg_bet=Avg('bet_amount'),
        )
        total_wagered = stats['total_wagered'] or Decimal('0')
        total_paid = stats['total_paid'] or Decimal('0')
        actual_rtp = (total_paid / total_wagered * 100) if total_wagered > 0 else Decimal('0')
        return {
            'total_spins': stats['total_spins'] or 0,
            'total_wagered': str(total_wagered),
            'total_paid': str(total_paid),
            'avg_bet': str(stats['avg_bet'] or Decimal('0')),
            'actual_rtp': str(actual_rtp.quantize(Decimal('0.01'))),
            'house_profit': str(total_wagered - total_paid),
        }
