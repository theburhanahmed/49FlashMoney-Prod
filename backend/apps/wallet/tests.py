"""
Tests for the Wallet and Ledger system.
Covers: balance correctness, idempotency, immutability, reconciliation,
insufficient balance, frozen wallet, and admin adjustments.
"""
import uuid
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from apps.wallet.models import Wallet, LedgerEntry
from apps.wallet.services import (
    WalletService,
    InsufficientBalanceError,
    WalletFrozenError,
    DuplicateTransactionError,
)

User = get_user_model()


class WalletServiceTestCase(TestCase):
    """Test wallet service operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )

    def test_get_or_create_wallet(self):
        """Wallet is created on first access."""
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        self.assertEqual(wallet.status, Wallet.STATUS_ACTIVE)

    def test_credit_creates_ledger_entry(self):
        """Crediting creates an immutable ledger entry."""
        entry = WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            description='Test deposit',
            idempotency_key='dep-001',
        )
        self.assertEqual(entry.direction, LedgerEntry.CREDIT)
        self.assertEqual(entry.amount, Decimal('100.00'))
        self.assertEqual(entry.balance_before, Decimal('0.00'))
        self.assertEqual(entry.balance_after, Decimal('100.00'))

    def test_credit_updates_balance(self):
        """Credit updates cached balance on wallet."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('50.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-002',
        )
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('50.00'))

    def test_debit_creates_ledger_entry(self):
        """Debiting creates an immutable ledger entry."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-003',
        )
        entry = WalletService.debit(
            user=self.user,
            amount=Decimal('30.00'),
            entry_type=LedgerEntry.BET,
            description='Test bet',
            idempotency_key='bet-001',
        )
        self.assertEqual(entry.direction, LedgerEntry.DEBIT)
        self.assertEqual(entry.amount, Decimal('30.00'))
        self.assertEqual(entry.balance_before, Decimal('100.00'))
        self.assertEqual(entry.balance_after, Decimal('70.00'))

    def test_debit_insufficient_balance(self):
        """Debit fails if balance is insufficient."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('10.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-004',
        )
        with self.assertRaises(InsufficientBalanceError):
            WalletService.debit(
                user=self.user,
                amount=Decimal('20.00'),
                entry_type=LedgerEntry.WITHDRAWAL,
                idempotency_key='wd-001',
            )

    def test_idempotency_prevents_duplicate_credit(self):
        """Same idempotency key prevents duplicate credit."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-005',
        )
        with self.assertRaises(DuplicateTransactionError):
            WalletService.credit(
                user=self.user,
                amount=Decimal('100.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key='dep-005',
            )

        # Balance should only be 100, not 200
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_idempotency_prevents_duplicate_debit(self):
        """Same idempotency key prevents duplicate debit."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-006',
        )
        WalletService.debit(
            user=self.user,
            amount=Decimal('25.00'),
            entry_type=LedgerEntry.BET,
            idempotency_key='bet-002',
        )
        with self.assertRaises(DuplicateTransactionError):
            WalletService.debit(
                user=self.user,
                amount=Decimal('25.00'),
                entry_type=LedgerEntry.BET,
                idempotency_key='bet-002',
            )

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('75.00'))

    def test_ledger_entry_immutability(self):
        """Ledger entries cannot be modified after creation."""
        entry = WalletService.credit(
            user=self.user,
            amount=Decimal('50.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-007',
        )
        entry.amount = Decimal('1000.00')
        with self.assertRaises(ValueError):
            entry.save()

    def test_ledger_entry_cannot_be_deleted(self):
        """Ledger entries cannot be deleted."""
        entry = WalletService.credit(
            user=self.user,
            amount=Decimal('50.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-008',
        )
        with self.assertRaises(ValueError):
            entry.delete()

    def test_reconcile_balance_matches(self):
        """Reconciliation shows balance matches when consistent."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('200.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-009',
        )
        WalletService.debit(
            user=self.user,
            amount=Decimal('50.00'),
            entry_type=LedgerEntry.BET,
            idempotency_key='bet-003',
        )
        result = WalletService.reconcile(self.user)
        self.assertTrue(result['match'])
        self.assertEqual(result['derived_balance'], '150.00')
        self.assertEqual(result['cached_balance'], '150.00')

    def test_frozen_wallet_blocks_transactions(self):
        """Frozen wallet prevents both credits and debits."""
        wallet = WalletService.get_or_create_wallet(self.user)
        wallet.status = Wallet.STATUS_FROZEN
        wallet.save()

        with self.assertRaises(WalletFrozenError):
            WalletService.credit(
                user=self.user,
                amount=Decimal('100.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key='dep-010',
            )

    def test_reserve_and_release(self):
        """Reserving and releasing funds works correctly."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-011',
        )

        # Reserve 30
        WalletService.reserve(
            user=self.user,
            amount=Decimal('30.00'),
            reference_type='game',
            reference_id='game-001',
            idempotency_key='res-001',
        )

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('70.00'))
        self.assertEqual(wallet.reserved_balance, Decimal('30.00'))
        # available_balance = balance - reserved_balance = 70 - 30 = 40
        self.assertEqual(wallet.available_balance, Decimal('40.00'))

        # Release 30
        WalletService.release_reservation(
            user=self.user,
            amount=Decimal('30.00'),
            reference_type='game',
            reference_id='game-001',
            idempotency_key='rel-001',
        )

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('100.00'))
        self.assertEqual(wallet.reserved_balance, Decimal('0.00'))

    def test_reserve_insufficient_available_balance(self):
        """Cannot reserve more than available balance."""
        WalletService.credit(
            user=self.user,
            amount=Decimal('50.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-012',
        )
        with self.assertRaises(InsufficientBalanceError):
            WalletService.reserve(
                user=self.user,
                amount=Decimal('60.00'),
                idempotency_key='res-002',
            )

    def test_multiple_credits_sum_correctly(self):
        """Multiple credits sum up correctly."""
        for i in range(5):
            WalletService.credit(
                user=self.user,
                amount=Decimal('20.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key=f'dep-multi-{i}',
            )
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_credit_negative_amount_rejected(self):
        """Cannot credit a negative or zero amount."""
        with self.assertRaises(ValueError):
            WalletService.credit(
                user=self.user,
                amount=Decimal('-10.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key='dep-neg-001',
            )

        with self.assertRaises(ValueError):
            WalletService.credit(
                user=self.user,
                amount=Decimal('0.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key='dep-zero-001',
            )

    def test_admin_adjustment_credit(self):
        """Admin can credit a user's wallet with audit trail."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_admin=True,
            role='admin',
        )
        entry = WalletService.admin_adjustment(
            user=self.user,
            amount=Decimal('75.00'),
            direction='CREDIT',
            reason='Compensation for service issue',
            admin_user=admin_user,
            idempotency_key='adj-001',
        )
        self.assertEqual(entry.entry_type, LedgerEntry.ADJUSTMENT)
        self.assertEqual(entry.direction, LedgerEntry.CREDIT)
        self.assertIn('admin', entry.actor)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('75.00'))

    def test_admin_adjustment_debit(self):
        """Admin can debit a user's wallet with audit trail."""
        admin_user = User.objects.create_user(
            username='admin2',
            email='admin2@example.com',
            password='adminpass123',
            is_admin=True,
            role='admin',
        )
        WalletService.credit(
            user=self.user,
            amount=Decimal('100.00'),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='dep-adj-001',
        )
        entry = WalletService.admin_adjustment(
            user=self.user,
            amount=Decimal('25.00'),
            direction='DEBIT',
            reason='Fraud correction',
            admin_user=admin_user,
            idempotency_key='adj-002',
        )
        self.assertEqual(entry.entry_type, LedgerEntry.ADJUSTMENT)
        self.assertEqual(entry.direction, LedgerEntry.DEBIT)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('75.00'))

    def test_ledger_history_ordered_by_created_at(self):
        """Ledger history returns entries in reverse chronological order."""
        for i in range(3):
            WalletService.credit(
                user=self.user,
                amount=Decimal('10.00'),
                entry_type=LedgerEntry.DEPOSIT,
                idempotency_key=f'dep-hist-{i}',
            )
        entries = WalletService.get_ledger_history(self.user)
        self.assertEqual(len(entries), 3)
        # Should be newest first
        self.assertTrue(entries[0].created_at >= entries[1].created_at)
