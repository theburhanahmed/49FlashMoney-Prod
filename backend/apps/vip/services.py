"""
VIP service layer.
Handles tier progression, cashback calculation, and admin tier management.
All money movements go through WalletService.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.transactions.models import Transaction
from apps.users.models import AuditLog
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

from .models import VIPTier, UserVIPStatus

logger = logging.getLogger(__name__)


class VIPService:
    """Service for VIP tier operations."""

    # ── User-facing ──────────────────────────────────────────────────

    @classmethod
    def get_or_create_status(cls, user) -> UserVIPStatus:
        """Get or create the VIP status for a user, assigning the lowest tier."""
        try:
            return user.vip_status
        except UserVIPStatus.DoesNotExist:
            lowest = VIPTier.objects.order_by('level').first()
            if not lowest:
                lowest = VIPTier.objects.create(
                    name='Bronze', level=0, min_wagered=Decimal('0'),
                    cashback_percentage=Decimal('0'),
                )
            return UserVIPStatus.objects.create(user=user, tier=lowest)

    @classmethod
    @transaction.atomic
    def update_wagered(cls, user, amount: Decimal):
        """
        Add wagered amount and check for tier promotion.
        Called after every game bet.
        """
        vip = cls.get_or_create_status(user)
        vip.total_wagered += Decimal(str(amount))
        vip.save(update_fields=['total_wagered', 'updated_at'])
        cls.check_and_promote(user)

    @classmethod
    @transaction.atomic
    def check_and_promote(cls, user):
        """Auto-promote user if they qualify for a higher tier."""
        vip = cls.get_or_create_status(user)
        current_level = vip.tier.level
        next_tier = (
            VIPTier.objects
            .filter(level__gt=current_level, min_wagered__lte=vip.total_wagered)
            .order_by('-level')
            .first()
        )
        if next_tier and next_tier.level > current_level:
            old_tier = vip.tier
            vip.tier = next_tier
            vip.promoted_at = timezone.now()
            vip.save(update_fields=['tier', 'promoted_at', 'updated_at'])
            AuditLog.objects.create(
                user=user,
                action='VIP_PROMOTION',
                description=f'Auto-promoted from {old_tier.name} to {next_tier.name}',
                resource_type='VIP',
                resource_id=str(next_tier.id),
                changes={
                    'old_tier': old_tier.name,
                    'new_tier': next_tier.name,
                    'total_wagered': str(vip.total_wagered),
                },
            )
            logger.info(
                f"VIP promotion: user={user.id} "
                f"{old_tier.name}→{next_tier.name}"
            )

    @classmethod
    @transaction.atomic
    def calculate_cashback(cls, user, period_days: int = 7) -> Decimal:
        """
        Calculate and credit weekly cashback based on net losses.
        Returns the cashback amount credited (0 if no losses).
        """
        vip = cls.get_or_create_status(user)
        if vip.tier.cashback_percentage <= 0:
            return Decimal('0')

        period_start = timezone.now() - timedelta(days=period_days)
        period_key = period_start.strftime('%Y-%W')

        # Net losses = total bets - total winnings in period
        bets = Transaction.objects.filter(
            user=user,
            type__in=['BET', 'SLOTS_BET', 'TICKET_PURCHASE'],
            status='COMPLETED',
            created_at__gte=period_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        winnings = Transaction.objects.filter(
            user=user,
            type__in=['WINNING', 'SLOTS_WIN', 'PRIZE_AWARD'],
            status='COMPLETED',
            created_at__gte=period_start,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        net_loss = bets - winnings
        if net_loss <= 0:
            return Decimal('0')

        cashback = (
            net_loss * vip.tier.cashback_percentage / Decimal('100')
        ).quantize(Decimal('0.01'))

        if cashback <= 0:
            return Decimal('0')

        idempotency_key = f'cashback:{user.id}:{period_key}'

        try:
            WalletService.credit(
                user=user,
                amount=cashback,
                entry_type=LedgerEntry.BONUS,
                description=f'VIP cashback ({vip.tier.name} – {vip.tier.cashback_percentage}%)',
                idempotency_key=idempotency_key,
                actor='vip_service',
            )
        except Exception:
            # DuplicateTransactionError – already claimed this period
            logger.info(f"Cashback already claimed: user={user.id} period={period_key}")
            return Decimal('0')

        Transaction.objects.create(
            user=user,
            type='CASHBACK',
            amount=cashback,
            status='COMPLETED',
            description=f'VIP {vip.tier.name} cashback',
            reference_id=str(vip.id),
        )
        AuditLog.objects.create(
            user=user,
            action='VIP_CASHBACK',
            description=f'Cashback of {cashback} credited for period {period_key}',
            resource_type='VIP',
            resource_id=str(vip.id),
            changes={
                'net_loss': str(net_loss),
                'cashback_percentage': str(vip.tier.cashback_percentage),
                'cashback_amount': str(cashback),
                'period': period_key,
            },
        )
        return cashback

    @classmethod
    def get_tier_benefits(cls, user) -> dict:
        """Return the user's current VIP tier info and benefits."""
        vip = cls.get_or_create_status(user)
        return {
            'tier': {
                'id': str(vip.tier.id),
                'name': vip.tier.name,
                'level': vip.tier.level,
                'cashback_percentage': str(vip.tier.cashback_percentage),
                'withdrawal_limit_multiplier': str(vip.tier.withdrawal_limit_multiplier),
                'benefits': vip.tier.benefits,
            },
            'total_wagered': str(vip.total_wagered),
            'promoted_at': vip.promoted_at.isoformat() if vip.promoted_at else None,
            'next_tier': cls._next_tier_info(vip),
        }

    @classmethod
    def _next_tier_info(cls, vip: UserVIPStatus) -> dict | None:
        nxt = VIPTier.objects.filter(level__gt=vip.tier.level).order_by('level').first()
        if not nxt:
            return None
        remaining = max(Decimal('0'), nxt.min_wagered - vip.total_wagered)
        return {
            'name': nxt.name,
            'level': nxt.level,
            'min_wagered': str(nxt.min_wagered),
            'remaining': str(remaining),
        }

    # ── Admin ────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def admin_set_tier(cls, admin_user, user, tier_id: str):
        """Admin manually sets a user's VIP tier."""
        tier = VIPTier.objects.get(id=tier_id)
        vip = cls.get_or_create_status(user)
        old_tier = vip.tier
        vip.tier = tier
        vip.promoted_at = timezone.now()
        vip.save(update_fields=['tier', 'promoted_at', 'updated_at'])
        AuditLog.objects.create(
            user=admin_user,
            action='VIP_MANUAL_SET',
            description=f'Set {user.username} tier from {old_tier.name} to {tier.name}',
            resource_type='VIP',
            resource_id=str(tier.id),
            changes={
                'target_user': str(user.id),
                'old_tier': old_tier.name,
                'new_tier': tier.name,
            },
        )

    @classmethod
    @transaction.atomic
    def admin_create_tier(cls, admin_user, data: dict) -> VIPTier:
        """Create a new VIP tier."""
        tier = VIPTier.objects.create(
            name=data['name'],
            level=data['level'],
            min_wagered=Decimal(str(data.get('min_wagered', 0))),
            cashback_percentage=Decimal(str(data.get('cashback_percentage', 0))),
            withdrawal_limit_multiplier=Decimal(str(data.get('withdrawal_limit_multiplier', 1))),
            benefits=data.get('benefits', {}),
        )
        AuditLog.objects.create(
            user=admin_user,
            action='VIP_TIER_CREATE',
            description=f'Created VIP tier {tier.name}',
            resource_type='VIP_TIER',
            resource_id=str(tier.id),
            changes=data,
        )
        return tier

    @classmethod
    @transaction.atomic
    def admin_update_tier(cls, admin_user, tier_id: str, data: dict) -> VIPTier:
        """Update a VIP tier's settings."""
        tier = VIPTier.objects.get(id=tier_id)
        old = {
            'name': tier.name, 'cashback_percentage': str(tier.cashback_percentage),
            'min_wagered': str(tier.min_wagered),
        }
        for field in ('name', 'level', 'min_wagered', 'cashback_percentage',
                      'withdrawal_limit_multiplier', 'benefits'):
            if field in data:
                val = data[field]
                if field in ('min_wagered', 'cashback_percentage', 'withdrawal_limit_multiplier'):
                    val = Decimal(str(val))
                setattr(tier, field, val)
        tier.save()
        AuditLog.objects.create(
            user=admin_user,
            action='VIP_TIER_UPDATE',
            description=f'Updated VIP tier {tier.name}',
            resource_type='VIP_TIER',
            resource_id=str(tier.id),
            changes={'old': old, 'new': data},
        )
        return tier
