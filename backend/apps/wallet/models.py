"""
Wallet and Ledger models for 49FlashMoney.

The wallet uses an immutable ledger as the source of truth.
Balance is derived from ledger entries. A cached balance on the Wallet
model is maintained for performance but must always be backed by ledger records.
"""
import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Wallet(models.Model):
    """
    User wallet with cached balance. The cached balance MUST always equal
    the sum of all ledger entries for this wallet.
    """
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_RESTRICTED = 'RESTRICTED'
    STATUS_FROZEN = 'FROZEN'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_RESTRICTED, 'Restricted'),
        (STATUS_FROZEN, 'Frozen'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet_account',
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cached balance derived from ledger entries.',
    )
    reserved_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Funds reserved for active bets or pending withdrawals.',
    )
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Wallet({self.user.username}) balance={self.balance}"

    @property
    def available_balance(self) -> Decimal:
        """Available balance = total balance - reserved."""
        return self.balance - self.reserved_balance

    def derive_balance_from_ledger(self) -> Decimal:
        """Recalculate balance from all ledger entries. Used for reconciliation."""
        from django.db.models import Sum, Q
        result = self.ledger_entries.aggregate(
            credits=Sum('amount', filter=Q(direction=LedgerEntry.CREDIT)),
            debits=Sum('amount', filter=Q(direction=LedgerEntry.DEBIT)),
        )
        credits = result['credits'] or Decimal('0.00')
        debits = result['debits'] or Decimal('0.00')
        return credits - debits


class LedgerEntry(models.Model):
    """
    Immutable ledger entry. Once created, entries are NEVER modified or deleted.
    Corrections must be done via compensating entries (reversals/adjustments).
    """
    CREDIT = 'CREDIT'
    DEBIT = 'DEBIT'
    DIRECTION_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    # Entry types matching PRD requirements
    DEPOSIT = 'DEPOSIT'
    WITHDRAWAL = 'WITHDRAWAL'
    BET = 'BET'
    WINNING = 'WINNING'
    BONUS = 'BONUS'
    REFUND = 'REFUND'
    REFERRAL_REWARD = 'REFERRAL_REWARD'
    ADJUSTMENT = 'ADJUSTMENT'
    REVERSAL = 'REVERSAL'
    RESERVATION = 'RESERVATION'
    RESERVATION_RELEASE = 'RESERVATION_RELEASE'

    ENTRY_TYPE_CHOICES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (BET, 'Bet'),
        (WINNING, 'Winning'),
        (BONUS, 'Bonus'),
        (REFUND, 'Refund'),
        (REFERRAL_REWARD, 'Referral Reward'),
        (ADJUSTMENT, 'Adjustment'),
        (REVERSAL, 'Reversal'),
        (RESERVATION, 'Reservation'),
        (RESERVATION_RELEASE, 'Reservation Release'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='ledger_entries',
    )
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES)
    direction = models.CharField(max_length=6, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Type of the originating entity (e.g. payment, game_room, etc.)',
    )
    reference_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='ID of the originating entity.',
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text='Prevents duplicate ledger effects for the same business event.',
    )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.CharField(
        max_length=100,
        blank=True,
        help_text='User or system that initiated this entry.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['entry_type', '-created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return (
            f"Ledger({self.entry_type} {self.direction} {self.amount} "
            f"wallet={self.wallet.user.username})"
        )

    def save(self, *args, **kwargs):
        """Override save to enforce immutability on existing records."""
        if self.pk and LedgerEntry.objects.filter(pk=self.pk).exists():
            raise ValueError("Ledger entries are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Ledger entries cannot be deleted."""
        raise ValueError("Ledger entries are immutable and cannot be deleted.")
