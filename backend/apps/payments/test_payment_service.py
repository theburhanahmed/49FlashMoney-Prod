"""
Tests for PaymentService – deposit/withdrawal flows with ledger integration.
Covers: deposit confirmation, idempotency, withdrawal lifecycle,
approval, rejection, and reconciliation.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from apps.wallet.models import Wallet, LedgerEntry
from apps.wallet.services import WalletService, DuplicateTransactionError
from apps.transactions.models import Transaction, WithdrawalRequest
from apps.payments.models import PaymentIntent, RazorpayOrder
from apps.payments.payment_service import PaymentService

User = get_user_model()


@override_settings(
    WITHDRAWAL_MIN_AMOUNT=1,
    WITHDRAWAL_MAX_AMOUNT=10000,
    WITHDRAWAL_DAILY_LIMIT=5000,
)
class DepositTestCase(TestCase):
    """Test deposit confirmation with ledger integration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='depositor',
            email='depositor@test.com',
            password='Pass123!',
        )

    def test_confirm_deposit_creates_ledger_entry(self):
        entry = PaymentService.confirm_deposit(
            user=self.user,
            amount=Decimal('100.00'),
            provider='stripe',
            provider_reference='pi_test_001',
        )
        self.assertEqual(entry.direction, LedgerEntry.CREDIT)
        self.assertEqual(entry.amount, Decimal('100.00'))
        self.assertEqual(entry.entry_type, LedgerEntry.DEPOSIT)

    def test_confirm_deposit_credits_wallet(self):
        PaymentService.confirm_deposit(
            user=self.user,
            amount=Decimal('100.00'),
            provider='stripe',
            provider_reference='pi_test_002',
        )
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_confirm_deposit_creates_transaction(self):
        PaymentService.confirm_deposit(
            user=self.user,
            amount=Decimal('50.00'),
            provider='razorpay',
            provider_reference='order_test_001',
        )
        txn = Transaction.objects.filter(user=self.user, type='DEPOSIT').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, Decimal('50.00'))
        self.assertEqual(txn.status, 'COMPLETED')

    def test_confirm_deposit_idempotency(self):
        PaymentService.confirm_deposit(
            user=self.user,
            amount=Decimal('100.00'),
            provider='stripe',
            provider_reference='pi_idem_001',
            idempotency_key='unique-deposit-key',
        )
        with self.assertRaises(DuplicateTransactionError):
            PaymentService.confirm_deposit(
                user=self.user,
                amount=Decimal('100.00'),
                provider='stripe',
                provider_reference='pi_idem_001',
                idempotency_key='unique-deposit-key',
            )
        # Balance should only reflect one deposit
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_confirm_deposit_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            PaymentService.confirm_deposit(
                user=self.user,
                amount=Decimal('-50.00'),
                provider='stripe',
                provider_reference='pi_negative',
            )

    def test_confirm_deposit_zero_amount_rejected(self):
        with self.assertRaises(ValueError):
            PaymentService.confirm_deposit(
                user=self.user,
                amount=Decimal('0.00'),
                provider='stripe',
                provider_reference='pi_zero',
            )


@override_settings(
    WITHDRAWAL_MIN_AMOUNT=10,
    WITHDRAWAL_MAX_AMOUNT=10000,
    WITHDRAWAL_DAILY_LIMIT=5000,
)
class WithdrawalTestCase(TestCase):
    """Test withdrawal lifecycle with ledger integration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='withdrawer',
            email='withdrawer@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
        )
        # Give user some funds
        WalletService.credit(
            user=self.user,
            amount=Decimal('500.00'),
            entry_type=LedgerEntry.DEPOSIT,
            description='Test funding',
            idempotency_key='wd-test-fund',
        )

    def test_request_withdrawal_reserves_funds(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        self.assertEqual(wd.status, 'REQUESTED')
        self.assertEqual(wd.amount, Decimal('100.00'))
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertEqual(wallet.reserved_balance, Decimal('100.00'))
        self.assertEqual(wallet.available_balance, Decimal('300.00'))

    def test_request_withdrawal_creates_pending_transaction(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        txn = wd.transaction
        self.assertIsNotNone(txn)
        self.assertEqual(txn.type, 'WITHDRAWAL')
        self.assertEqual(txn.status, 'PENDING')

    def test_request_withdrawal_insufficient_balance(self):
        from apps.wallet.services import InsufficientBalanceError
        with self.assertRaises(InsufficientBalanceError):
            PaymentService.request_withdrawal(
                user=self.user,
                amount=Decimal('600.00'),
            )

    def test_request_withdrawal_below_minimum(self):
        with self.assertRaises(ValueError):
            PaymentService.request_withdrawal(
                user=self.user,
                amount=Decimal('5.00'),
            )

    def test_approve_withdrawal_debits_wallet(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        PaymentService.approve_withdrawal(
            withdrawal_id=str(wd.id),
            admin_user=self.admin,
            remarks='Approved for payout',
        )
        wd.refresh_from_db()
        self.assertEqual(wd.status, 'APPROVED')
        wallet = WalletService.get_or_create_wallet(self.user)
        # 500 - 100 reserved + released - 100 debited = 400
        # But reserve deducts from balance, so after reserve: balance=400, reserved=100
        # After release: balance=500, reserved=0
        # After debit: balance=400
        self.assertEqual(wallet.balance, Decimal('400.00'))
        self.assertEqual(wallet.reserved_balance, Decimal('0.00'))

    def test_reject_withdrawal_releases_funds(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        PaymentService.reject_withdrawal(
            withdrawal_id=str(wd.id),
            admin_user=self.admin,
            reason='KYC not verified',
        )
        wd.refresh_from_db()
        self.assertEqual(wd.status, 'REJECTED')
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal('500.00'))
        self.assertEqual(wallet.reserved_balance, Decimal('0.00'))

    def test_approve_already_approved_fails(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        PaymentService.approve_withdrawal(str(wd.id), self.admin)
        with self.assertRaises(ValueError):
            PaymentService.approve_withdrawal(str(wd.id), self.admin)

    def test_reject_already_rejected_fails(self):
        wd = PaymentService.request_withdrawal(
            user=self.user,
            amount=Decimal('100.00'),
        )
        PaymentService.reject_withdrawal(str(wd.id), self.admin, 'Reason')
        with self.assertRaises(ValueError):
            PaymentService.reject_withdrawal(str(wd.id), self.admin, 'Another reason')


@override_settings(
    WITHDRAWAL_MIN_AMOUNT=1,
    WITHDRAWAL_MAX_AMOUNT=10000,
    WITHDRAWAL_DAILY_LIMIT=5000,
)
class StripeIntegrationTestCase(TestCase):
    """Test Stripe payment flow with ledger (mocked Stripe calls)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='stripe_user',
            email='stripe@test.com',
            password='Pass123!',
        )

    def test_handle_stripe_success_creates_ledger_entry(self):
        # Create a pending PaymentIntent record
        pi = PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_test_success_001',
            amount=Decimal('200.00'),
            currency='usd',
            status='requires_payment_method',
        )
        entry = PaymentService.handle_stripe_success('pi_test_success_001')
        self.assertEqual(entry.amount, Decimal('200.00'))
        self.assertEqual(entry.entry_type, LedgerEntry.DEPOSIT)
        pi.refresh_from_db()
        self.assertEqual(pi.status, 'succeeded')
        self.assertIsNotNone(pi.completed_at)

    def test_handle_stripe_success_idempotent(self):
        PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_test_idem_001',
            amount=Decimal('150.00'),
            currency='usd',
            status='requires_payment_method',
        )
        PaymentService.handle_stripe_success('pi_test_idem_001')
        with self.assertRaises(DuplicateTransactionError):
            PaymentService.handle_stripe_success('pi_test_idem_001')

    def test_handle_stripe_success_nonexistent_fails(self):
        with self.assertRaises(ValueError):
            PaymentService.handle_stripe_success('pi_nonexistent')


class RazorpayIntegrationTestCase(TestCase):
    """Test Razorpay payment flow with ledger."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='razorpay_user',
            email='razorpay@test.com',
            password='Pass123!',
        )

    def test_handle_razorpay_success(self):
        order = RazorpayOrder.objects.create(
            user=self.user,
            razorpay_order_id='order_test_001',
            amount=Decimal('300.00'),
            currency='INR',
            status='created',
        )
        entry = PaymentService.handle_razorpay_success(
            'order_test_001', 'pay_test_001'
        )
        self.assertEqual(entry.amount, Decimal('300.00'))
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.metadata['razorpay_payment_id'], 'pay_test_001')

    def test_handle_razorpay_success_idempotent(self):
        RazorpayOrder.objects.create(
            user=self.user,
            razorpay_order_id='order_idem_001',
            amount=Decimal('200.00'),
            currency='INR',
            status='created',
        )
        PaymentService.handle_razorpay_success('order_idem_001', 'pay_idem_001')
        with self.assertRaises(DuplicateTransactionError):
            PaymentService.handle_razorpay_success('order_idem_001', 'pay_idem_002')


class ReconciliationTestCase(TestCase):
    """Test deposit reconciliation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='recon_user',
            email='recon@test.com',
            password='Pass123!',
        )

    def test_reconcile_matched_deposits(self):
        pi = PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_recon_001',
            amount=Decimal('100.00'),
            currency='usd',
            status='requires_payment_method',
        )
        PaymentService.handle_stripe_success('pi_recon_001')

        results = PaymentService.reconcile_deposits(provider='stripe')
        self.assertEqual(results['matched'], 1)
        self.assertEqual(results['mismatched'], 0)
        self.assertEqual(results['missing_ledger'], 0)

    def test_reconcile_missing_ledger(self):
        # Create a "succeeded" PaymentIntent but no ledger entry
        PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_recon_missing',
            amount=Decimal('100.00'),
            currency='usd',
            status='succeeded',
        )
        results = PaymentService.reconcile_deposits(provider='stripe')
        self.assertEqual(results['missing_ledger'], 1)
