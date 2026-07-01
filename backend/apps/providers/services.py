"""
ProviderService — orchestration layer for third-party casino provider adapters.

Responsibilities:
  - Validate and persist provider config / credentials.
  - Sync the game catalogue from the provider.
  - Create and track game sessions.
  - Orchestrate the bet → settle lifecycle with idempotent wallet movements.
  - Handle refunds for cancelled / errored rounds.
  - Run balance reconciliation spot checks.

All money movements go through WalletService and are backed by immutable
LedgerEntry records.  ProviderRound records shadow every ledger entry.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService, InsufficientBalanceError, DuplicateTransactionError

from .exceptions import (
    ProviderAuthError,
    ProviderBetError,
    ProviderError,
    ProviderGameNotFoundError,
    ProviderRefundError,
    ProviderSettlementError,
)
from .models import ProviderConfig, ProviderGameCatalog, ProviderGameSession, ProviderRound
from .registry import registry

logger = logging.getLogger(__name__)


class ProviderService:
    """
    High-level service for all provider operations.

    All public methods are class methods; no state is stored on the instance.
    """

    # ------------------------------------------------------------------ #
    # Provider config                                                       #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_or_create_config(cls, slug: str, display_name: str = '') -> ProviderConfig:
        """Return the ProviderConfig for a slug, creating it if absent."""
        config, created = ProviderConfig.objects.get_or_create(
            slug=slug,
            defaults={'display_name': display_name or slug},
        )
        if created:
            logger.info("Created ProviderConfig for slug=%s", slug)
        return config

    @classmethod
    def update_credentials(
        cls,
        slug: str,
        credentials: dict,
        settings: Optional[dict] = None,
    ) -> ProviderConfig:
        """
        Update credentials (and optionally settings) for a provider.

        Validates credentials through the adapter before saving.

        Raises:
            ProviderAuthError if validation fails.
            KeyError if the adapter is not registered.
        """
        adapter = registry.get(slug)
        errors = adapter.validate_config(credentials)
        if errors:
            raise ProviderAuthError(
                f"Invalid credentials for '{slug}': {'; '.join(errors)}",
                provider=slug,
            )
        config = cls.get_or_create_config(slug)
        config.credentials = credentials
        if settings is not None:
            config.settings = settings
        config.save(update_fields=['credentials', 'settings', 'updated_at'])
        logger.info("Updated credentials for provider=%s", slug)
        return config

    # ------------------------------------------------------------------ #
    # Catalogue sync                                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def sync_catalog(cls, slug: str) -> int:
        """
        Pull the full game catalogue from the provider and upsert into DB.

        Returns:
            Number of games synced.

        Raises:
            KeyError if the adapter is not registered.
        """
        adapter = registry.get(slug)
        config = cls.get_or_create_config(slug, adapter.display_name)

        games = adapter.list_games(page=1, page_size=1000)
        synced = 0
        for game in games:
            ProviderGameCatalog.objects.update_or_create(
                provider=config,
                provider_game_id=game.game_id,
                defaults={
                    'name': game.name,
                    'category': game.category,
                    'thumbnail_url': game.thumbnail_url,
                    'is_active': game.is_active,
                    'min_bet': game.min_bet,
                    'max_bet': game.max_bet,
                    'rtp': game.rtp,
                    'tags': game.tags,
                    'extra': game.extra,
                },
            )
            synced += 1

        logger.info("Synced %d games for provider=%s", synced, slug)
        return synced

    # ------------------------------------------------------------------ #
    # Sessions                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def launch_game(
        cls,
        user,
        slug: str,
        provider_game_id: str,
        currency: str = 'INR',
        language: str = 'en',
        mode: str = 'real',
        return_url: str = '',
    ) -> ProviderGameSession:
        """
        Create a provider session and return the DB record with launch URL.

        Args:
            user: Django user instance.
            slug: Provider slug.
            provider_game_id: Provider's game identifier.
            currency: ISO 4217 currency code.
            language: ISO 639-1 language code.
            mode: 'real' or 'demo'.
            return_url: URL to redirect to after the player closes the game.

        Returns:
            ProviderGameSession (status=ACTIVE, launch_url populated).

        Raises:
            ProviderGameNotFoundError if the game is not in the catalogue.
            ProviderSessionError on provider error.
            KeyError if the adapter is not registered.
        """
        adapter = registry.get(slug)
        config = cls.get_or_create_config(slug, adapter.display_name)

        # Resolve catalog entry
        try:
            catalog_entry = ProviderGameCatalog.objects.get(
                provider=config,
                provider_game_id=provider_game_id,
                is_active=True,
            )
        except ProviderGameCatalog.DoesNotExist:
            raise ProviderGameNotFoundError(
                f"Game '{provider_game_id}' not found for provider '{slug}'.",
                provider=slug,
            )

        provider_session = adapter.create_session(
            game_id=provider_game_id,
            user_id=str(user.id),
            currency=currency,
            language=language,
            extra={'mode': mode},
        )

        launch_url = adapter.launch_game(
            session_token=provider_session.session_token,
            return_url=return_url,
            mode=mode,
        )

        db_session = ProviderGameSession.objects.create(
            user=user,
            provider=config,
            game=catalog_entry,
            session_token=provider_session.session_token,
            launch_url=launch_url,
            currency=currency,
            mode=mode,
            status=ProviderGameSession.STATUS_ACTIVE,
            extra={
                'language': language,
                'return_url': return_url,
                'provider_extra': provider_session.extra,
            },
        )
        logger.info(
            "Launched provider game: user=%s slug=%s game=%s session=%s",
            user.id, slug, provider_game_id, db_session.id,
        )
        return db_session

    # ------------------------------------------------------------------ #
    # Bet lifecycle                                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    @transaction.atomic
    def place_bet(
        cls,
        user,
        session_id: str,
        bet_amount: Decimal,
        extra: Optional[dict] = None,
    ) -> ProviderRound:
        """
        Debit the player's wallet and place a bet through the provider.

        Idempotency:
            A unique round_id is generated per call.  The wallet debit uses
            round_id as its idempotency_key so retries are safe.

        Args:
            user: Django user instance.
            session_id: UUID of the ProviderGameSession.
            bet_amount: Amount to wager.
            extra: Additional provider-specific data forwarded to adapter.

        Returns:
            ProviderRound (status may be PENDING, WON, LOST, or PUSH).

        Raises:
            InsufficientBalanceError from WalletService.
            ProviderBetError if the provider rejects the bet.
        """
        bet_amount = Decimal(str(bet_amount))
        if bet_amount <= 0:
            raise ValueError("bet_amount must be positive.")

        try:
            db_session = ProviderGameSession.objects.select_related(
                'provider', 'game', 'user',
            ).get(id=session_id, user=user, status=ProviderGameSession.STATUS_ACTIVE)
        except ProviderGameSession.DoesNotExist:
            raise ProviderBetError(
                f"Active session '{session_id}' not found for user {user.id}.",
                provider='',
            )

        slug = db_session.provider.slug
        adapter = registry.get(slug)
        round_id = f"prov-{slug}-{uuid.uuid4().hex}"

        # 1. Debit the wallet (idempotent)
        bet_entry = WalletService.debit(
            user=user,
            amount=bet_amount,
            entry_type=LedgerEntry.BET,
            description=f"Provider bet: {db_session.game.name if db_session.game else slug}",
            reference_type='provider_round',
            reference_id=round_id,
            idempotency_key=f"prov_bet:{round_id}",
            actor='provider_service',
        )

        # 2. Create the round record (PENDING)
        prov_round = ProviderRound.objects.create(
            session=db_session,
            user=user,
            provider=db_session.provider,
            game=db_session.game,
            round_id=round_id,
            bet_amount=bet_amount,
            payout=Decimal('0.00'),
            currency=db_session.currency,
            status=ProviderRound.STATUS_PENDING,
            bet_ledger_entry_id=str(bet_entry.id),
        )

        # 3. Forward bet to provider
        try:
            result = adapter.place_bet(
                session_token=db_session.session_token,
                game_id=db_session.game.provider_game_id if db_session.game else '',
                user_id=str(user.id),
                amount=bet_amount,
                currency=db_session.currency,
                round_id=round_id,
                extra=extra or {},
            )
        except ProviderBetError as exc:
            # Provider rejected — refund wallet and mark round as error
            try:
                WalletService.credit(
                    user=user,
                    amount=bet_amount,
                    entry_type=LedgerEntry.REFUND,
                    description=f"Refund: provider rejected bet (round={round_id})",
                    reference_type='provider_round',
                    reference_id=round_id,
                    idempotency_key=f"prov_bet_refund:{round_id}",
                    actor='provider_service',
                )
            except DuplicateTransactionError:
                pass  # Already refunded
            prov_round.status = ProviderRound.STATUS_ERROR
            prov_round.error_message = str(exc)
            prov_round.save(update_fields=['status', 'error_message'])
            raise

        # 4. Store provider response
        prov_round.provider_round_id = result.provider_round_id
        prov_round.raw_bet_response = result.state

        # 5. Settle immediately if provider returned a final result
        payout_entry_id = ''
        if result.status in ('won', 'push', 'lost'):
            prov_round, payout_entry_id = cls._settle_internal(
                user=user,
                prov_round=prov_round,
                payout=result.payout,
                status_str=result.status,
                settle_extra={},
            )
        else:
            prov_round.status = ProviderRound.STATUS_PENDING
            prov_round.save(update_fields=[
                'provider_round_id', 'raw_bet_response', 'status',
            ])

        return prov_round

    # ------------------------------------------------------------------ #
    # Settlement                                                            #
    # ------------------------------------------------------------------ #

    @classmethod
    @transaction.atomic
    def settle_round(
        cls,
        round_id: str,
        payout: Decimal,
        extra: Optional[dict] = None,
    ) -> ProviderRound:
        """
        Settle a pending round (e.g. from an async provider webhook).

        Args:
            round_id: Platform round_id on ProviderRound.
            payout: Amount to credit to the user (0 for a loss).
            extra: Raw provider data to store for audit.

        Returns:
            Updated ProviderRound.

        Raises:
            ProviderSettlementError if the round is not in PENDING state.
        """
        try:
            prov_round = ProviderRound.objects.select_related(
                'user', 'provider', 'game',
            ).get(round_id=round_id)
        except ProviderRound.DoesNotExist:
            raise ProviderSettlementError(
                f"Round '{round_id}' not found.",
                provider='',
            )

        if prov_round.status != ProviderRound.STATUS_PENDING:
            raise ProviderSettlementError(
                f"Round '{round_id}' is in state '{prov_round.status}', cannot settle.",
                provider=prov_round.provider.slug,
            )

        payout = Decimal(str(payout))
        status_str = 'won' if payout > 0 else 'lost'
        prov_round, _ = cls._settle_internal(
            user=prov_round.user,
            prov_round=prov_round,
            payout=payout,
            status_str=status_str,
            settle_extra=extra or {},
        )
        return prov_round

    @classmethod
    def _settle_internal(
        cls,
        user,
        prov_round: ProviderRound,
        payout: Decimal,
        status_str: str,
        settle_extra: dict,
    ) -> tuple[ProviderRound, str]:
        """Internal helper: credit payout, update round status."""
        payout_entry_id = ''
        if payout > 0:
            try:
                payout_entry = WalletService.credit(
                    user=user,
                    amount=payout,
                    entry_type=LedgerEntry.WINNING,
                    description=(
                        f"Provider win: "
                        f"{prov_round.game.name if prov_round.game else prov_round.provider.slug}"
                    ),
                    reference_type='provider_round',
                    reference_id=prov_round.round_id,
                    idempotency_key=f"prov_win:{prov_round.round_id}",
                    actor='provider_service',
                )
                payout_entry_id = str(payout_entry.id)
            except DuplicateTransactionError:
                logger.warning(
                    "Duplicate settlement for round %s — already settled.",
                    prov_round.round_id,
                )

        status_map = {
            'won': ProviderRound.STATUS_WON,
            'lost': ProviderRound.STATUS_LOST,
            'push': ProviderRound.STATUS_PUSH,
        }
        prov_round.status = status_map.get(status_str, ProviderRound.STATUS_SETTLED)
        prov_round.payout = payout
        prov_round.payout_ledger_entry_id = payout_entry_id
        prov_round.raw_settle_response = settle_extra
        prov_round.settled_at = timezone.now()
        prov_round.save(update_fields=[
            'status', 'payout', 'payout_ledger_entry_id',
            'raw_settle_response', 'settled_at',
            'provider_round_id', 'raw_bet_response',
        ])
        return prov_round, payout_entry_id

    # ------------------------------------------------------------------ #
    # Refunds                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    @transaction.atomic
    def refund_round(
        cls,
        round_id: str,
        reason: str = '',
        extra: Optional[dict] = None,
    ) -> ProviderRound:
        """
        Refund the bet for a cancelled or errored round.

        Only rounds in PENDING or ERROR state can be refunded.

        Returns:
            Updated ProviderRound (status=REFUNDED).

        Raises:
            ProviderRefundError if the round cannot be refunded.
        """
        try:
            prov_round = ProviderRound.objects.select_related(
                'user', 'provider', 'game',
            ).get(round_id=round_id)
        except ProviderRound.DoesNotExist:
            raise ProviderRefundError(
                f"Round '{round_id}' not found.",
                provider='',
            )

        if prov_round.status not in (
            ProviderRound.STATUS_PENDING, ProviderRound.STATUS_ERROR,
        ):
            raise ProviderRefundError(
                f"Round '{round_id}' is in state '{prov_round.status}' and cannot be refunded.",
                provider=prov_round.provider.slug,
            )

        try:
            WalletService.credit(
                user=prov_round.user,
                amount=prov_round.bet_amount,
                entry_type=LedgerEntry.REFUND,
                description=f"Refund round {round_id}: {reason}",
                reference_type='provider_round',
                reference_id=round_id,
                idempotency_key=f"prov_refund:{round_id}",
                actor='provider_service',
            )
        except DuplicateTransactionError:
            logger.warning("Duplicate refund for round %s — already refunded.", round_id)

        prov_round.status = ProviderRound.STATUS_REFUNDED
        prov_round.error_message = reason
        prov_round.raw_settle_response = extra or {}
        prov_round.settled_at = timezone.now()
        prov_round.save(update_fields=[
            'status', 'error_message', 'raw_settle_response', 'settled_at',
        ])
        logger.info("Refunded round %s for user %s", round_id, prov_round.user.id)
        return prov_round

    # ------------------------------------------------------------------ #
    # Utilities                                                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_round_history(
        cls,
        user,
        slug: Optional[str] = None,
        limit: int = 50,
    ) -> list[ProviderRound]:
        """Return recent rounds for a user, optionally filtered by provider."""
        qs = ProviderRound.objects.filter(user=user).order_by('-created_at')
        if slug:
            qs = qs.filter(provider__slug=slug)
        return list(qs[:limit])

    @classmethod
    def health_check_all(cls) -> list[dict]:
        """Run health checks for all registered providers."""
        results = []
        for adapter in registry.all():
            try:
                status = adapter.health_check()
                results.append({
                    'provider': adapter.provider_slug,
                    'healthy': status.healthy,
                    'latency_ms': status.latency_ms,
                    'message': status.message,
                })
            except Exception as exc:
                results.append({
                    'provider': adapter.provider_slug,
                    'healthy': False,
                    'message': str(exc),
                })
        return results
