"""
Slots spin service with provably fair RNG.
"""
import hashlib
import secrets
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.slots.models import SlotsGame, SlotsSpin
from apps.transactions.models import Transaction
from apps.users.models import UserProfile, AuditLog
from apps.users.responsible_gaming import ResponsibleGamingService

logger = logging.getLogger(__name__)


class SlotsSpinService:
    """Service for conducting slots spins with provably fair RNG."""

    @staticmethod
    def _get_symbol_from_seed(seed_bytes: bytes, reel: list, index: int) -> str:
        """
        Deterministically pick a symbol from reel using seed.
        Uses SHA256(seed + index) mod len(reel).
        """
        h = hashlib.sha256(seed_bytes + index.to_bytes(4, 'big')).hexdigest()
        idx = int(h[:8], 16) % len(reel)
        return reel[idx]

    @staticmethod
    def _generate_spin_result(game: SlotsGame, seed: str) -> list:
        """
        Generate spin result [symbol1, symbol2, symbol3] from seed.
        Provably fair: same seed + game config = same result.
        """
        seed_bytes = seed.encode('utf-8')
        reels = game.reels or []
        if len(reels) < 3:
            reels = [["cherry", "lemon", "orange", "plum", "bell", "bar", "seven"]] * 3
        results = []
        for i, reel in enumerate(reels):
            sym = SlotsSpinService._get_symbol_from_seed(seed_bytes, reel, i)
            results.append(sym)
        return results

    @staticmethod
    def _calculate_payout(game: SlotsGame, symbols: list, bet_amount: Decimal) -> Decimal:
        """
        Calculate payout based on paytable.
        3 matching symbols = bet * multiplier.
        """
        if len(symbols) < 3:
            return Decimal('0')
        s1, s2, s3 = symbols[0], symbols[1], symbols[2]
        if s1 == s2 == s3:
            multiplier = game.get_payout(s1)
            return bet_amount * Decimal(str(multiplier))
        return Decimal('0')

    @staticmethod
    @transaction.atomic
    def spin(user, game_id: str, bet_amount: Decimal):
        """
        Execute a slots spin.

        Args:
            user: User making the spin
            game_id: UUID of SlotsGame
            bet_amount: Bet amount (must be within min/max)

        Returns:
            dict with spin result for API response

        Raises:
            ValueError with user-friendly message on validation failure
        """
        game = SlotsGame.objects.get(id=game_id)

        if not game.is_active:
            raise ValueError("This game is not available")

        bet_amount = Decimal(str(bet_amount))

        if bet_amount < game.min_bet:
            raise ValueError(f"Minimum bet is ${game.min_bet}")

        if bet_amount > game.max_bet:
            raise ValueError(f"Maximum bet is ${game.max_bet}")

        # Responsible gaming checks
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(user)
        if is_excluded:
            raise ValueError(exclusion_reason)

        is_valid, error_msg, _ = ResponsibleGamingService.check_session_time(user)
        if not is_valid:
            raise ValueError(error_msg or "Session limit exceeded")

        is_valid, error_msg = ResponsibleGamingService.check_loss_limit(user, bet_amount)
        if not is_valid:
            raise ValueError(error_msg or "Daily loss limit exceeded")

        if user.wallet_balance < bet_amount:
            raise ValueError("Insufficient balance")

        # Update session start if not set
        if not user.last_session_start:
            user.last_session_start = timezone.now()
            user.save(update_fields=['last_session_start'])

        # Generate provably fair seed
        seed = secrets.token_hex(32)

        # Generate result
        symbols = SlotsSpinService._generate_spin_result(game, seed)
        payout = SlotsSpinService._calculate_payout(game, symbols, bet_amount)

        # Deduct bet
        user.deduct_balance(bet_amount)

        # Credit payout if any
        if payout > 0:
            user.add_balance(payout)

        # Create spin record
        spin = SlotsSpin.objects.create(
            user=user,
            game=game,
            bet_amount=bet_amount,
            symbols=symbols,
            payout=payout,
            random_seed=seed,
        )

        # Create transactions
        Transaction.objects.create(
            user=user,
            type='SLOTS_BET',
            amount=bet_amount,
            status='COMPLETED',
            description=f'Slots bet: {game.name} - {symbols}',
            reference_id=str(spin.id),
        )
        if payout > 0:
            Transaction.objects.create(
                user=user,
                type='SLOTS_WIN',
                amount=payout,
                status='COMPLETED',
                description=f'Slots win: {game.name} - {symbols}',
                reference_id=str(spin.id),
            )

        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.total_spent += float(bet_amount)
        if payout > 0:
            profile.total_won += float(payout)
            profile.total_wins += 1
        profile.save()

        # Audit log
        AuditLog.objects.create(
            user=user,
            action='BUY_TICKET',  # Reuse; could add SLOTS_SPIN to choices
            description=f'Slots spin: {game.name} bet ${bet_amount} result {symbols} payout ${payout}',
            resource_type='USER',
            resource_id=str(user.id),
        )

        logger.info(f"Slots spin: user={user.id} game={game_id} bet={bet_amount} result={symbols} payout={payout}")

        return {
            'id': str(spin.id),
            'symbols': symbols,
            'bet_amount': float(bet_amount),
            'payout': float(payout),
            'random_seed': seed,
            'created_at': spin.created_at.isoformat(),
        }
