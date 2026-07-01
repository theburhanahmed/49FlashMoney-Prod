"""
Wallet service layer for 49FlashMoney.

All wallet mutations MUST go through this service.
Every balance change creates an immutable ledger entry.
Idempotency keys prevent duplicate processing.
"""
import logging
import uuid
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import F

from .models import Wallet, LedgerEntry

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    pass


class WalletFrozenError(Exception):
    pass


class DuplicateTransactionError(Exception):
    """Raised when an idempotency key has already been used."""
    pass


class WalletService:
    """
    Service for all wallet operations.
    All public methods are atomic and create ledger entries.
    """

    @classmethod
    def get_or_create_wallet(cls, user) -> Wallet:
        """Get or create a wallet for a user."""
        wallet, created = Wallet.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created wallet for user {user.id}")
        return wallet

    @classmethod
    def get_balance(cls, user) -> Decimal:
        """Get the cached balance for a user's wallet."""
        wallet = cls.get_or_create_wallet(user)
        return wallet.available_balance

    @classmethod
    def _check_wallet_active(cls, wallet: Wallet) -> None:
        """Raise if wallet is not in ACTIVE state."""
        if wallet.status == Wallet.STATUS_FROZEN:
            raise WalletFrozenError("Wallet is frozen. No transactions allowed.")
        if wallet.status == Wallet.STATUS_RESTRICTED:
            raise WalletFrozenError("Wallet is restricted.")

    @classmethod
    def _check_idempotency(cls, idempotency_key: Optional[str]) -> Optional[LedgerEntry]:
        """
        Check if an idempotency key has already been used.
        Returns the existing entry if found, None otherwise.
        """
        if not idempotency_key:
            return None
        existing = LedgerEntry.objects.filter(idempotency_key=idempotency_key).first()
        return existing

    @classmethod
    @transaction.atomic
    def credit(
        cls,
        user,
        amount: Decimal,
        entry_type: str,
        description: str = '',
        reference_type: str = '',
        reference_id: str = '',
        idempotency_key: Optional[str] = None,
        actor: str = 'system',
        metadata: Optional[dict] = None,
    ) -> LedgerEntry:
        """
        Credit funds to a user's wallet.
        Creates an immutable ledger entry and updates cached balance.

        Args:
            user: The user to credit.
            amount: Amount to credit (must be > 0).
            entry_type: Type of ledger entry (DEPOSIT, WINNING, BONUS, etc.)
            description: Human-readable description.
            reference_type: Type of originating entity.
            reference_id: ID of originating entity.
            idempotency_key: Unique key to prevent duplicate credits.
            actor: Who/what initiated this credit.
            metadata: Additional JSON metadata.

        Returns:
            The created LedgerEntry.

        Raises:
            DuplicateTransactionError: If idempotency_key was already used.
            WalletFrozenError: If wallet is not active.
            ValueError: If amount <= 0.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")

        # Idempotency check
        existing = cls._check_idempotency(idempotency_key)
        if existing:
            logger.info(f"Duplicate credit request: idempotency_key={idempotency_key}")
            raise DuplicateTransactionError(
                f"Transaction with idempotency_key={idempotency_key} already exists."
            )

        wallet = cls.get_or_create_wallet(user)
        cls._check_wallet_active(wallet)

        # Lock the wallet row for update
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        balance_before = wallet.balance
        balance_after = balance_before + amount

        # Create immutable ledger entry
        entry = LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=entry_type,
            direction=LedgerEntry.CREDIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description,
            metadata=metadata or {},
            actor=actor,
        )

        # Update cached balance
        wallet.balance = balance_after
        wallet.save(update_fields=['balance', 'updated_at'])

        logger.info(
            f"Credited {amount} to user {user.id} "
            f"(type={entry_type}, key={idempotency_key})"
        )
        return entry

    @classmethod
    @transaction.atomic
    def debit(
        cls,
        user,
        amount: Decimal,
        entry_type: str,
        description: str = '',
        reference_type: str = '',
        reference_id: str = '',
        idempotency_key: Optional[str] = None,
        actor: str = 'system',
        metadata: Optional[dict] = None,
    ) -> LedgerEntry:
        """
        Debit funds from a user's wallet.
        Creates an immutable ledger entry and updates cached balance.

        Raises:
            InsufficientBalanceError: If balance < amount.
            DuplicateTransactionError: If idempotency_key was already used.
            WalletFrozenError: If wallet is not active.
            ValueError: If amount <= 0.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")

        # Idempotency check
        existing = cls._check_idempotency(idempotency_key)
        if existing:
            logger.info(f"Duplicate debit request: idempotency_key={idempotency_key}")
            raise DuplicateTransactionError(
                f"Transaction with idempotency_key={idempotency_key} already exists."
            )

        wallet = cls.get_or_create_wallet(user)
        cls._check_wallet_active(wallet)

        # Lock the wallet row for update
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.available_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Available: {wallet.available_balance}, "
                f"Requested: {amount}"
            )

        balance_before = wallet.balance
        balance_after = balance_before - amount

        # Create immutable ledger entry
        entry = LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=entry_type,
            direction=LedgerEntry.DEBIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description,
            metadata=metadata or {},
            actor=actor,
        )

        # Update cached balance
        wallet.balance = balance_after
        wallet.save(update_fields=['balance', 'updated_at'])

        logger.info(
            f"Debited {amount} from user {user.id} "
            f"(type={entry_type}, key={idempotency_key})"
        )
        return entry

    @classmethod
    @transaction.atomic
    def reserve(
        cls,
        user,
        amount: Decimal,
        reference_type: str = '',
        reference_id: str = '',
        idempotency_key: Optional[str] = None,
        actor: str = 'system',
        description: str = '',
    ) -> LedgerEntry:
        """
        Reserve funds for a pending operation (bet, withdrawal).
        Funds are moved from available to reserved.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Reserve amount must be positive.")

        existing = cls._check_idempotency(idempotency_key)
        if existing:
            raise DuplicateTransactionError(
                f"Reservation with idempotency_key={idempotency_key} already exists."
            )

        wallet = cls.get_or_create_wallet(user)
        cls._check_wallet_active(wallet)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.available_balance < amount:
            raise InsufficientBalanceError(
                f"Insufficient available balance for reservation. "
                f"Available: {wallet.available_balance}, Requested: {amount}"
            )

        balance_before = wallet.balance

        # Create ledger entry for reservation (debit from available)
        entry = LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=LedgerEntry.RESERVATION,
            direction=LedgerEntry.DEBIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_before - amount,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description or f'Reserved {amount} for {reference_type}',
            actor=actor,
        )

        # Update wallet: decrease balance, increase reserved
        wallet.balance = balance_before - amount
        wallet.reserved_balance = wallet.reserved_balance + amount
        wallet.save(update_fields=['balance', 'reserved_balance', 'updated_at'])

        logger.info(f"Reserved {amount} for user {user.id} (ref={reference_id})")
        return entry

    @classmethod
    @transaction.atomic
    def release_reservation(
        cls,
        user,
        amount: Decimal,
        reference_type: str = '',
        reference_id: str = '',
        idempotency_key: Optional[str] = None,
        actor: str = 'system',
        description: str = '',
    ) -> LedgerEntry:
        """
        Release previously reserved funds back to available balance.
        Used when a bet is cancelled or a withdrawal is rejected.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Release amount must be positive.")

        existing = cls._check_idempotency(idempotency_key)
        if existing:
            raise DuplicateTransactionError(
                f"Release with idempotency_key={idempotency_key} already exists."
            )

        wallet = cls.get_or_create_wallet(user)
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.reserved_balance < amount:
            raise ValueError(
                f"Cannot release more than reserved. "
                f"Reserved: {wallet.reserved_balance}, Requested: {amount}"
            )

        balance_before = wallet.balance

        entry = LedgerEntry.objects.create(
            wallet=wallet,
            entry_type=LedgerEntry.RESERVATION_RELEASE,
            direction=LedgerEntry.CREDIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_before + amount,
            currency=wallet.currency,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            description=description or f'Released reservation of {amount}',
            actor=actor,
        )

        wallet.balance = balance_before + amount
        wallet.reserved_balance = wallet.reserved_balance - amount
        wallet.save(update_fields=['balance', 'reserved_balance', 'updated_at'])

        logger.info(f"Released reservation of {amount} for user {user.id}")
        return entry

    @classmethod
    def reconcile(cls, user) -> dict:
        """
        Reconcile cached balance against ledger-derived balance.
        Returns a dict with derived_balance, cached_balance, and match status.
        """
        wallet = cls.get_or_create_wallet(user)
        derived = wallet.derive_balance_from_ledger().quantize(Decimal('0.01'))
        cached = wallet.balance.quantize(Decimal('0.01'))
        match = derived == cached

        if not match:
            logger.warning(
                f"Balance mismatch for user {user.id}: "
                f"derived={derived}, cached={cached}"
            )

        return {
            'user_id': str(user.id),
            'derived_balance': str(derived),
            'cached_balance': str(cached),
            'match': match,
            'difference': str((derived - cached).quantize(Decimal('0.01'))),
        }

    @classmethod
    def get_ledger_history(cls, user, limit: int = 50, offset: int = 0):
        """Get ledger entries for a user with pagination."""
        wallet = cls.get_or_create_wallet(user)
        return wallet.ledger_entries.all()[offset:offset + limit]

    @classmethod
    @transaction.atomic
    def admin_adjustment(
        cls,
        user,
        amount: Decimal,
        direction: str,
        reason: str,
        admin_user,
        idempotency_key: Optional[str] = None,
    ) -> LedgerEntry:
        """
        Admin manual adjustment (credit or debit).
        Requires elevated permissions and reason code.
        """
        if direction == LedgerEntry.CREDIT:
            return cls.credit(
                user=user,
                amount=amount,
                entry_type=LedgerEntry.ADJUSTMENT,
                description=f'Admin adjustment: {reason}',
                reference_type='admin_adjustment',
                reference_id=str(admin_user.id),
                idempotency_key=idempotency_key,
                actor=f'admin:{admin_user.username}',
                metadata={'reason': reason, 'admin_id': str(admin_user.id)},
            )
        elif direction == LedgerEntry.DEBIT:
            return cls.debit(
                user=user,
                amount=amount,
                entry_type=LedgerEntry.ADJUSTMENT,
                description=f'Admin adjustment: {reason}',
                reference_type='admin_adjustment',
                reference_id=str(admin_user.id),
                idempotency_key=idempotency_key,
                actor=f'admin:{admin_user.username}',
                metadata={'reason': reason, 'admin_id': str(admin_user.id)},
            )
        else:
            raise ValueError(f"Invalid direction: {direction}")
