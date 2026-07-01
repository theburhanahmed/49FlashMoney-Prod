"""
PaymentService – orchestrates deposit and withdrawal flows with
idempotent ledger integration.

Responsibilities:
- Deposit confirmation → wallet credit via immutable ledger
- Withdrawal request → eligibility check → reservation → processing
- Withdrawal approval/rejection with ledger settlement
- Reconciliation between provider records and ledger
- Audit logging for every financial state transition

The existing StripeService/RazorpayService handle provider API calls.
This service handles the *platform-side* money movement.
"""
import logging
import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import models as db_models, transaction
from django.utils import timezone

from apps.users.models import User, AuditLog
from apps.wallet.services import (
    WalletService,
    InsufficientBalanceError,
    WalletFrozenError,
    DuplicateTransactionError,
)
from apps.wallet.models import LedgerEntry
from apps.transactions.models import Transaction, WithdrawalRequest
from apps.payments.models import PaymentIntent, RazorpayOrder

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Central service for deposit and withdrawal orchestration.
    Every method is idempotent via idempotency keys.
    """

    # ── Deposits ──────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def confirm_deposit(
        cls,
        user: User,
        amount: Decimal,
        provider: str,
        provider_reference: str,
        idempotency_key: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> LedgerEntry:
        """
        Called when a payment provider confirms a successful deposit.
        Creates a ledger credit and a Transaction record.

        This is idempotent: if the idempotency_key was already used,
        a DuplicateTransactionError is raised (no double-credit).

        Args:
            user: The depositing user.
            amount: Confirmed deposit amount.
            provider: 'stripe' or 'razorpay'.
            provider_reference: Provider's reference ID.
            idempotency_key: Unique key (e.g. payment_intent_id).
            metadata: Extra data for audit.

        Returns:
            The LedgerEntry created.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        idem_key = idempotency_key or f'deposit:{provider}:{provider_reference}'

        # Credit wallet via ledger
        entry = WalletService.credit(
            user=user,
            amount=amount,
            entry_type=LedgerEntry.DEPOSIT,
            description=f'Deposit via {provider}',
            reference_type=f'payment_{provider}',
            reference_id=provider_reference,
            idempotency_key=idem_key,
            actor=f'payment_service:{provider}',
            metadata=metadata or {'provider': provider, 'reference': provider_reference},
        )

        # Create Transaction record
        Transaction.objects.create(
            user=user,
            type='DEPOSIT',
            amount=amount,
            status='COMPLETED',
            description=f'Deposit confirmed via {provider}',
            reference_id=provider_reference,
            completed_at=timezone.now(),
        )

        # Audit log
        AuditLog.objects.create(
            user=user,
            action='DEPOSIT',
            description=f'Deposit of {amount} confirmed via {provider}',
            resource_type='PAYMENT',
            resource_id=provider_reference,
            changes={'amount': str(amount), 'provider': provider},
        )

        logger.info(
            f"Deposit confirmed: user={user.id} amount={amount} "
            f"provider={provider} ref={provider_reference}"
        )
        return entry

    @classmethod
    @transaction.atomic
    def handle_stripe_success(cls, payment_intent_id: str) -> LedgerEntry:
        """
        Handle a successful Stripe payment (webhook or confirm flow).
        Idempotent: safe to call multiple times for the same intent.
        """
        try:
            pi = PaymentIntent.objects.select_for_update().get(
                stripe_payment_intent_id=payment_intent_id
            )
        except PaymentIntent.DoesNotExist:
            raise ValueError(f"PaymentIntent not found: {payment_intent_id}")

        if pi.status == 'succeeded' and pi.completed_at:
            # Already processed - check if ledger entry exists
            raise DuplicateTransactionError(
                f"Payment {payment_intent_id} already processed"
            )

        pi.status = 'succeeded'
        pi.completed_at = timezone.now()
        pi.save(update_fields=['status', 'completed_at', 'updated_at'])

        return cls.confirm_deposit(
            user=pi.user,
            amount=pi.amount,
            provider='stripe',
            provider_reference=payment_intent_id,
            idempotency_key=f'stripe_deposit:{payment_intent_id}',
        )

    @classmethod
    @transaction.atomic
    def handle_razorpay_success(
        cls, razorpay_order_id: str, razorpay_payment_id: str
    ) -> LedgerEntry:
        """
        Handle a verified Razorpay payment.
        Idempotent: safe to call multiple times.
        """
        try:
            order = RazorpayOrder.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except RazorpayOrder.DoesNotExist:
            raise ValueError(f"RazorpayOrder not found: {razorpay_order_id}")

        if order.status == 'paid' and order.completed_at:
            raise DuplicateTransactionError(
                f"Razorpay order {razorpay_order_id} already processed"
            )

        order.status = 'paid'
        order.completed_at = timezone.now()
        order.metadata['razorpay_payment_id'] = razorpay_payment_id
        order.save(update_fields=['status', 'completed_at', 'metadata', 'updated_at'])

        return cls.confirm_deposit(
            user=order.user,
            amount=order.amount,
            provider='razorpay',
            provider_reference=razorpay_order_id,
            idempotency_key=f'razorpay_deposit:{razorpay_order_id}',
            metadata={
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
            },
        )

    # ── Withdrawals ───────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def request_withdrawal(
        cls,
        user: User,
        amount: Decimal,
        bank_details: dict = None,
        idempotency_key: Optional[str] = None,
    ) -> WithdrawalRequest:
        """
        Create a withdrawal request. Reserves funds in the wallet
        so they cannot be spent while the withdrawal is under review.

        Returns:
            WithdrawalRequest instance.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")

        # Check limits
        min_wd = Decimal(str(getattr(settings, 'WITHDRAWAL_MIN_AMOUNT', 10)))
        max_wd = Decimal(str(getattr(settings, 'WITHDRAWAL_MAX_AMOUNT', 10000)))
        if amount < min_wd or amount > max_wd:
            raise ValueError(f'Withdrawal must be between {min_wd} and {max_wd}')

        # Check daily limits
        daily_limit = Decimal(str(getattr(settings, 'WITHDRAWAL_DAILY_LIMIT', 1000)))
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_total = WithdrawalRequest.objects.filter(
            user=user,
            status__in=['REQUESTED', 'APPROVED', 'PROCESSING', 'COMPLETED'],
            requested_at__gte=today_start,
        ).aggregate(total=db_models.Sum('amount'))['total'] or Decimal('0')

        if today_total + amount > daily_limit:
            raise ValueError(
                f'Daily withdrawal limit exceeded. '
                f'Used: {today_total}, Requested: {amount}, Limit: {daily_limit}'
            )

        # Reserve funds in wallet
        idem_key = idempotency_key or f'wd_reserve:{uuid.uuid4()}'
        WalletService.reserve(
            user=user,
            amount=amount,
            reference_type='withdrawal',
            reference_id=idem_key,
            idempotency_key=idem_key,
            actor='payment_service',
            description=f'Withdrawal reservation of {amount}',
        )

        # Create WithdrawalRequest
        wd = WithdrawalRequest.objects.create(
            user=user,
            amount=amount,
            status='REQUESTED',
            bank_details=bank_details or {},
            remarks=f'idempotency_key={idem_key}',
        )

        # Create pending transaction
        txn = Transaction.objects.create(
            user=user,
            type='WITHDRAWAL',
            amount=amount,
            status='PENDING',
            description='Withdrawal requested',
            reference_id=str(wd.id),
        )
        wd.transaction = txn
        wd.save(update_fields=['transaction'])

        AuditLog.objects.create(
            user=user,
            action='WITHDRAWAL',
            description=f'Withdrawal of {amount} requested',
            resource_type='WITHDRAWAL',
            resource_id=str(wd.id),
            changes={'amount': str(amount), 'status': 'REQUESTED'},
        )

        logger.info(f"Withdrawal requested: user={user.id} amount={amount} wd={wd.id}")
        return wd

    @classmethod
    @transaction.atomic
    def approve_withdrawal(
        cls,
        withdrawal_id: str,
        admin_user: User,
        remarks: str = '',
    ) -> WithdrawalRequest:
        """
        Approve a withdrawal request. Debits the reserved funds from the
        wallet and marks the withdrawal as APPROVED.
        """
        wd = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_id)
        if wd.status != 'REQUESTED':
            raise ValueError(f'Cannot approve withdrawal in {wd.status} status')

        user = wd.user

        # Debit the reserved amount from wallet (release reservation + debit)
        idem_key = f'wd_approve:{wd.id}'

        # Release the reservation first
        WalletService.release_reservation(
            user=user,
            amount=wd.amount,
            reference_type='withdrawal',
            reference_id=str(wd.id),
            idempotency_key=f'wd_release:{wd.id}',
            actor=f'admin:{admin_user.username}',
            description=f'Release reservation for approved withdrawal',
        )

        # Then debit the actual funds
        WalletService.debit(
            user=user,
            amount=wd.amount,
            entry_type=LedgerEntry.WITHDRAWAL,
            description=f'Withdrawal approved by {admin_user.username}',
            reference_type='withdrawal',
            reference_id=str(wd.id),
            idempotency_key=idem_key,
            actor=f'admin:{admin_user.username}',
            metadata={'remarks': remarks, 'admin_id': str(admin_user.id)},
        )

        wd.status = 'APPROVED'
        wd.processed_at = timezone.now()
        wd.remarks = remarks or wd.remarks
        wd.save(update_fields=['status', 'processed_at', 'remarks'])

        if wd.transaction:
            wd.transaction.mark_completed()

        AuditLog.objects.create(
            user=admin_user,
            action='WITHDRAWAL',
            description=f'Withdrawal {wd.id} approved for user {user.username}',
            resource_type='WITHDRAWAL',
            resource_id=str(wd.id),
            changes={
                'status_before': 'REQUESTED',
                'status_after': 'APPROVED',
                'amount': str(wd.amount),
                'remarks': remarks,
            },
        )

        logger.info(f"Withdrawal approved: wd={wd.id} by admin={admin_user.id}")
        return wd

    @classmethod
    @transaction.atomic
    def reject_withdrawal(
        cls,
        withdrawal_id: str,
        admin_user: User,
        reason: str = '',
    ) -> WithdrawalRequest:
        """
        Reject a withdrawal request. Releases reserved funds back to
        the user's available balance.
        """
        wd = WithdrawalRequest.objects.select_for_update().get(id=withdrawal_id)
        if wd.status != 'REQUESTED':
            raise ValueError(f'Cannot reject withdrawal in {wd.status} status')

        user = wd.user

        # Release reserved funds
        WalletService.release_reservation(
            user=user,
            amount=wd.amount,
            reference_type='withdrawal_rejection',
            reference_id=str(wd.id),
            idempotency_key=f'wd_reject_release:{wd.id}',
            actor=f'admin:{admin_user.username}',
            description=f'Withdrawal rejected: {reason}',
        )

        wd.status = 'REJECTED'
        wd.processed_at = timezone.now()
        wd.remarks = reason or wd.remarks
        wd.save(update_fields=['status', 'processed_at', 'remarks'])

        if wd.transaction:
            wd.transaction.mark_failed()

        AuditLog.objects.create(
            user=admin_user,
            action='WITHDRAWAL',
            description=f'Withdrawal {wd.id} rejected for user {user.username}',
            resource_type='WITHDRAWAL',
            resource_id=str(wd.id),
            changes={
                'status_before': 'REQUESTED',
                'status_after': 'REJECTED',
                'reason': reason,
            },
        )

        logger.info(f"Withdrawal rejected: wd={wd.id} by admin={admin_user.id}")
        return wd

    # ── Reconciliation ────────────────────────────────────────────────

    @classmethod
    def reconcile_deposits(cls, provider: str = 'all') -> dict:
        """
        Compare internal deposit records against ledger entries.
        Returns summary of matched/mismatched/missing records.
        """
        results = {'matched': 0, 'mismatched': 0, 'missing_ledger': 0, 'records': []}

        if provider in ('stripe', 'all'):
            for pi in PaymentIntent.objects.filter(status='succeeded'):
                ledger = LedgerEntry.objects.filter(
                    idempotency_key=f'stripe_deposit:{pi.stripe_payment_intent_id}'
                ).first()
                if ledger:
                    if ledger.amount == pi.amount:
                        results['matched'] += 1
                    else:
                        results['mismatched'] += 1
                        results['records'].append({
                            'type': 'mismatch',
                            'provider': 'stripe',
                            'reference': pi.stripe_payment_intent_id,
                            'provider_amount': str(pi.amount),
                            'ledger_amount': str(ledger.amount),
                        })
                else:
                    results['missing_ledger'] += 1
                    results['records'].append({
                        'type': 'missing_ledger',
                        'provider': 'stripe',
                        'reference': pi.stripe_payment_intent_id,
                        'amount': str(pi.amount),
                    })

        if provider in ('razorpay', 'all'):
            for order in RazorpayOrder.objects.filter(status='paid'):
                ledger = LedgerEntry.objects.filter(
                    idempotency_key=f'razorpay_deposit:{order.razorpay_order_id}'
                ).first()
                if ledger:
                    if ledger.amount == order.amount:
                        results['matched'] += 1
                    else:
                        results['mismatched'] += 1
                        results['records'].append({
                            'type': 'mismatch',
                            'provider': 'razorpay',
                            'reference': order.razorpay_order_id,
                            'provider_amount': str(order.amount),
                            'ledger_amount': str(ledger.amount),
                        })
                else:
                    results['missing_ledger'] += 1
                    results['records'].append({
                        'type': 'missing_ledger',
                        'provider': 'razorpay',
                        'reference': order.razorpay_order_id,
                        'amount': str(order.amount),
                    })

        return results
