"""
Promotions service layer for 49FlashMoney.

All business logic lives here. Views are intentionally thin wrappers.
All money movements go through WalletService with idempotency keys.
All admin actions are audited via AuditService.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry
from apps.users.audit_service import AuditService
from apps.transactions.models import Transaction

from .models import Promotion, PromotionClaim

logger = logging.getLogger(__name__)


# ── Custom exceptions ──────────────────────────────────────────────────────────

class PromotionNotFoundError(Exception):
    pass


class PromotionNotActiveError(Exception):
    pass


class PromotionExpiredError(Exception):
    pass


class PromotionMaxClaimsReachedError(Exception):
    pass


class PromotionAlreadyClaimedError(Exception):
    pass


class PromotionIneligibleError(Exception):
    pass


# ── Service ────────────────────────────────────────────────────────────────────

class PromotionService:
    """
    Service for all promotion operations.

    Public API
    ----------
    claim_promotion       – user claims a promotion
    get_available_promotions – list claimable active promotions for a user
    get_user_claims       – list a user's own claim history
    create_promotion      – admin creates a new promotion
    update_promotion      – admin updates an existing promotion
    cancel_promotion      – admin cancels a promotion
    """

    # ── User-facing ───────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def claim_promotion(
        cls,
        user,
        promotion_id: str,
        deposit_amount: Optional[Decimal] = None,
    ) -> PromotionClaim:
        """
        Claim a promotion on behalf of *user*.

        Steps
        -----
        1. Load & validate the promotion (active, within dates, max_claims).
        2. Ensure the user hasn't already claimed it.
        3. Calculate bonus amount (type-specific logic).
        4. Credit bonus via WalletService (LedgerEntry.BONUS).
        5. Create a Transaction record.
        6. Increment promotion.total_claims.
        7. Create PromotionClaim with status CREDITED.
        8. Write audit log.

        Returns
        -------
        PromotionClaim instance.

        Raises
        ------
        PromotionNotFoundError          – promotion_id doesn't exist
        PromotionNotActiveError         – status != ACTIVE
        PromotionExpiredError           – outside start_date / end_date window
        PromotionMaxClaimsReachedError  – max_claims reached (when > 0)
        PromotionAlreadyClaimedError    – user already has a claim
        PromotionIneligibleError        – eligibility criteria not met
        """
        # 1. Load promotion
        try:
            promotion = Promotion.objects.select_for_update().get(pk=promotion_id)
        except Promotion.DoesNotExist:
            raise PromotionNotFoundError(f"Promotion {promotion_id} not found.")

        # 2a. Status check
        if promotion.status != 'ACTIVE':
            raise PromotionNotActiveError(
                f"Promotion '{promotion.name}' is not active (status={promotion.status})."
            )

        # 2b. Date range check
        now = timezone.now()
        if now < promotion.start_date:
            raise PromotionNotActiveError(
                f"Promotion '{promotion.name}' has not started yet."
            )
        if now > promotion.end_date:
            raise PromotionExpiredError(
                f"Promotion '{promotion.name}' has expired."
            )

        # 2c. Max-claims check (0 = unlimited)
        if promotion.max_claims > 0 and promotion.total_claims >= promotion.max_claims:
            raise PromotionMaxClaimsReachedError(
                f"Promotion '{promotion.name}' has reached its maximum number of claims."
            )

        # 3. Duplicate-claim check
        already_claimed = PromotionClaim.objects.filter(
            user=user, promotion=promotion
        ).exists()
        if already_claimed:
            raise PromotionAlreadyClaimedError(
                f"User {user.id} has already claimed promotion '{promotion.name}'."
            )

        # 4. Calculate bonus
        deposit_amount = Decimal(str(deposit_amount)) if deposit_amount is not None else None
        bonus_amount = cls._calculate_bonus(promotion, deposit_amount)

        if bonus_amount <= Decimal('0.00'):
            raise PromotionIneligibleError(
                "Calculated bonus amount is zero. Eligibility criteria may not be met."
            )

        # 5. Credit bonus via WalletService
        idempotency_key = f"promotion-claim-{user.id}-{promotion.id}"
        WalletService.credit(
            user=user,
            amount=bonus_amount,
            entry_type=LedgerEntry.BONUS,
            description=f"Promotion bonus: {promotion.name}",
            reference_type='promotion',
            reference_id=str(promotion.id),
            idempotency_key=idempotency_key,
            actor=f"user:{user.id}",
        )

        # 6. Create Transaction record
        Transaction.objects.create(
            user=user,
            type='REFERRAL_BONUS',  # closest generic bonus type
            amount=bonus_amount,
            status='COMPLETED',
            description=f"Promotion bonus credited: {promotion.name}",
            reference_id=str(promotion.id),
        )

        # 7. Increment total_claims atomically
        Promotion.objects.filter(pk=promotion.pk).update(
            total_claims=promotion.total_claims + 1
        )
        promotion.refresh_from_db()

        # 8. Compute wagering requirement
        wagering_remaining = bonus_amount * promotion.wagering_requirement

        # 9. Create PromotionClaim
        claim = PromotionClaim.objects.create(
            user=user,
            promotion=promotion,
            bonus_amount=bonus_amount,
            deposit_amount=deposit_amount,
            wagering_remaining=wagering_remaining,
            status='CREDITED',
        )

        # 10. Audit log
        AuditService.log(
            action='DEPOSIT',  # financial credit event
            description=(
                f"User {user.username} claimed promotion '{promotion.name}' "
                f"(id={promotion.id}). Bonus credited: {bonus_amount}."
            ),
            user=user,
            resource_type='TRANSACTION',
            resource_id=str(claim.id),
            changes={
                'promotion_id': str(promotion.id),
                'promotion_name': promotion.name,
                'bonus_amount': str(bonus_amount),
                'deposit_amount': str(deposit_amount) if deposit_amount else None,
                'wagering_remaining': str(wagering_remaining),
            },
        )

        logger.info(
            f"Promotion claimed: user={user.id} promotion={promotion.id} "
            f"bonus={bonus_amount} claim={claim.id}"
        )
        return claim

    # ── Bonus calculation helpers ─────────────────────────────────────────────

    @classmethod
    def _calculate_bonus(
        cls,
        promotion: Promotion,
        deposit_amount: Optional[Decimal],
    ) -> Decimal:
        """
        Dispatch to the appropriate bonus formula based on promotion_type.

        DEPOSIT_BONUS : percentage of deposit, capped at max_bonus_amount.
        CASHBACK      : same formula as DEPOSIT_BONUS.
        FREE_BET      : flat bonus equal to max_bonus_amount (no deposit needed).
        REFERRAL      : flat bonus equal to max_bonus_amount (no deposit needed).
        """
        ptype = promotion.promotion_type

        if ptype in ('DEPOSIT_BONUS', 'CASHBACK'):
            if deposit_amount is None or deposit_amount <= Decimal('0.00'):
                raise PromotionIneligibleError(
                    f"A positive deposit_amount is required for {ptype} promotions."
                )
            if deposit_amount < promotion.min_deposit:
                raise PromotionIneligibleError(
                    f"Deposit {deposit_amount} is below the minimum required "
                    f"deposit of {promotion.min_deposit} for this promotion."
                )
            raw_bonus = deposit_amount * (promotion.bonus_percentage / Decimal('100'))
            if promotion.max_bonus_amount > Decimal('0.00'):
                return min(raw_bonus, promotion.max_bonus_amount)
            return raw_bonus

        if ptype in ('FREE_BET', 'REFERRAL'):
            # Flat bonus — no deposit required.
            return promotion.max_bonus_amount if promotion.max_bonus_amount > Decimal('0.00') else Decimal('0.00')

        # Fallback: treat as flat bonus
        logger.warning(f"Unknown promotion_type '{ptype}' – applying flat max_bonus_amount.")
        return promotion.max_bonus_amount if promotion.max_bonus_amount > Decimal('0.00') else Decimal('0.00')

    # ── Queries ───────────────────────────────────────────────────────────────

    @classmethod
    def get_available_promotions(cls, user):
        """
        Return active promotions that:
          - have status ACTIVE
          - are within the start_date / end_date window
          - have not been claimed by this user yet
          - have not exhausted max_claims (0 = unlimited)
        """
        now = timezone.now()
        claimed_ids = PromotionClaim.objects.filter(user=user).values_list(
            'promotion_id', flat=True
        )
        qs = Promotion.objects.filter(
            status='ACTIVE',
            start_date__lte=now,
            end_date__gte=now,
        ).exclude(id__in=claimed_ids)

        # Exclude promotions that have exhausted max_claims
        # max_claims == 0 means unlimited – keep those
        available = [p for p in qs if p.max_claims == 0 or p.total_claims < p.max_claims]
        return available

    @classmethod
    def get_user_claims(cls, user):
        """Return all PromotionClaim records for *user*, most recent first."""
        return (
            PromotionClaim.objects.filter(user=user)
            .select_related('promotion')
            .order_by('-claimed_at')
        )

    # ── Admin operations ──────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def create_promotion(cls, admin_user, data: dict) -> Promotion:
        """
        Admin creates a new promotion.

        Parameters
        ----------
        admin_user : User – must be an admin
        data       : dict of promotion field values

        Returns
        -------
        Newly created Promotion.
        """
        promotion = Promotion.objects.create(**data)

        AuditService.log_admin_action(
            admin_user=admin_user,
            action='DEPOSIT',
            target_type='TRANSACTION',
            target_id=str(promotion.id),
            description=(
                f"Admin {admin_user.username} created promotion '{promotion.name}' "
                f"(type={promotion.promotion_type}, status={promotion.status})."
            ),
            after={
                'id': str(promotion.id),
                'name': promotion.name,
                'promotion_type': promotion.promotion_type,
                'status': promotion.status,
                'bonus_percentage': str(promotion.bonus_percentage),
                'max_bonus_amount': str(promotion.max_bonus_amount),
                'start_date': promotion.start_date.isoformat(),
                'end_date': promotion.end_date.isoformat(),
            },
        )

        logger.info(
            f"Promotion created: id={promotion.id} name='{promotion.name}' "
            f"by admin={admin_user.id}"
        )
        return promotion

    @classmethod
    @transaction.atomic
    def update_promotion(cls, admin_user, promotion_id: str, data: dict) -> Promotion:
        """
        Admin updates an existing promotion.

        Only non-cancelled, non-expired promotions may be freely updated.
        Fields not included in *data* are left unchanged.

        Returns
        -------
        Updated Promotion.

        Raises
        ------
        PromotionNotFoundError – if promotion_id doesn't exist.
        """
        try:
            promotion = Promotion.objects.select_for_update().get(pk=promotion_id)
        except Promotion.DoesNotExist:
            raise PromotionNotFoundError(f"Promotion {promotion_id} not found.")

        # Snapshot before-state for audit
        before = {
            'name': promotion.name,
            'status': promotion.status,
            'promotion_type': promotion.promotion_type,
            'bonus_percentage': str(promotion.bonus_percentage),
            'max_bonus_amount': str(promotion.max_bonus_amount),
            'min_deposit': str(promotion.min_deposit),
            'wagering_requirement': str(promotion.wagering_requirement),
            'start_date': promotion.start_date.isoformat(),
            'end_date': promotion.end_date.isoformat(),
            'max_claims': promotion.max_claims,
        }

        for field, value in data.items():
            setattr(promotion, field, value)
        promotion.save()

        after = {
            'name': promotion.name,
            'status': promotion.status,
            'promotion_type': promotion.promotion_type,
            'bonus_percentage': str(promotion.bonus_percentage),
            'max_bonus_amount': str(promotion.max_bonus_amount),
            'min_deposit': str(promotion.min_deposit),
            'wagering_requirement': str(promotion.wagering_requirement),
            'start_date': promotion.start_date.isoformat(),
            'end_date': promotion.end_date.isoformat(),
            'max_claims': promotion.max_claims,
        }

        AuditService.log_admin_action(
            admin_user=admin_user,
            action='CHANGE_ROLE',  # generic admin-update action available in AuditLog
            target_type='TRANSACTION',
            target_id=str(promotion.id),
            description=(
                f"Admin {admin_user.username} updated promotion '{promotion.name}' "
                f"(id={promotion.id})."
            ),
            before=before,
            after=after,
        )

        logger.info(
            f"Promotion updated: id={promotion.id} by admin={admin_user.id}"
        )
        return promotion

    @classmethod
    @transaction.atomic
    def cancel_promotion(cls, admin_user, promotion_id: str) -> Promotion:
        """
        Admin cancels a promotion (sets status to CANCELLED).

        Returns
        -------
        Cancelled Promotion.

        Raises
        ------
        PromotionNotFoundError   – if promotion_id doesn't exist.
        PromotionNotActiveError  – if promotion is already cancelled/expired.
        """
        try:
            promotion = Promotion.objects.select_for_update().get(pk=promotion_id)
        except Promotion.DoesNotExist:
            raise PromotionNotFoundError(f"Promotion {promotion_id} not found.")

        if promotion.status in ('CANCELLED', 'EXPIRED'):
            raise PromotionNotActiveError(
                f"Promotion '{promotion.name}' is already {promotion.status}."
            )

        before_status = promotion.status
        promotion.status = 'CANCELLED'
        promotion.save(update_fields=['status', 'updated_at'])

        AuditService.log_admin_action(
            admin_user=admin_user,
            action='TOGGLE_USER_STATUS',
            target_type='TRANSACTION',
            target_id=str(promotion.id),
            description=(
                f"Admin {admin_user.username} cancelled promotion '{promotion.name}' "
                f"(id={promotion.id}). Previous status: {before_status}."
            ),
            before={'status': before_status},
            after={'status': 'CANCELLED'},
        )

        logger.info(
            f"Promotion cancelled: id={promotion.id} by admin={admin_user.id}"
        )
        return promotion
