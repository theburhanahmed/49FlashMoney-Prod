"""
Abstract base adapter for casino game providers.

Every third-party provider integration MUST subclass BaseProviderAdapter and
implement all abstract methods. Optional hooks can be overridden to add
provider-specific behaviour without breaking the contract.

Wallet model:
    This layer uses the *transfer-wallet* model: the platform maintains the
    authoritative balance in the ledger, and the provider receives a token
    representing the session.  If the provider uses a seamless-wallet model,
    the adapter should proxy balance queries back to WalletService.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderGame:
    """Normalised game descriptor returned by list_games / get_game."""
    game_id: str             # Provider's internal game identifier
    name: str
    category: str            # e.g. 'slots', 'table', 'live', 'instant_win'
    provider: str            # Provider slug (e.g. 'demo', 'pragmatic')
    thumbnail_url: str = ''
    is_active: bool = True
    min_bet: Decimal = Decimal('0.10')
    max_bet: Decimal = Decimal('10000.00')
    rtp: Decimal = Decimal('96.00')
    tags: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class ProviderSession:
    """Active game session returned by create_session / launch_game."""
    session_token: str
    launch_url: str
    game_id: str
    user_id: str
    provider: str
    expires_at: Optional[str] = None   # ISO-8601 or None for no expiry
    extra: dict = field(default_factory=dict)


@dataclass
class BetResult:
    """Result of a place_bet call."""
    round_id: str
    provider_round_id: str
    game_id: str
    bet_amount: Decimal
    payout: Decimal
    currency: str
    status: str              # 'pending', 'won', 'lost', 'push'
    state: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@dataclass
class SettlementResult:
    """Result of a settle_round call."""
    round_id: str
    provider_round_id: str
    payout: Decimal
    currency: str
    status: str              # 'settled', 'refunded', 'voided'
    extra: dict = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Result of a health_check call."""
    provider: str
    healthy: bool
    latency_ms: Optional[float] = None
    message: str = ''
    details: dict = field(default_factory=dict)


class BaseProviderAdapter(abc.ABC):
    """
    Abstract base class for all casino provider adapters.

    Subclasses MUST implement every abstract method.
    Subclasses MAY override the optional hooks.
    """

    # ---------- Identity -------------------------------------------------- #

    @property
    @abc.abstractmethod
    def provider_slug(self) -> str:
        """Unique identifier for this provider, e.g. 'demo', 'pragmatic'."""

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name, e.g. 'Demo Casino'."""

    # ---------- Authentication -------------------------------------------- #

    @abc.abstractmethod
    def authenticate(self, config: dict) -> bool:
        """
        Validate provider credentials / API keys.

        Args:
            config: Provider-specific configuration dict (api_key, secret, etc.)

        Returns:
            True if authentication succeeded.

        Raises:
            ProviderAuthError on failure.
        """

    # ---------- Catalogue ------------------------------------------------- #

    @abc.abstractmethod
    def list_games(self, page: int = 1, page_size: int = 100) -> list[ProviderGame]:
        """
        Fetch the provider's game catalogue.

        Args:
            page: 1-based page number.
            page_size: Number of games per page.

        Returns:
            List of ProviderGame objects.
        """

    @abc.abstractmethod
    def get_game(self, game_id: str) -> ProviderGame:
        """
        Fetch metadata for a single game.

        Raises:
            ProviderGameNotFoundError if the game does not exist.
        """

    # ---------- Sessions -------------------------------------------------- #

    @abc.abstractmethod
    def create_session(
        self,
        game_id: str,
        user_id: str,
        currency: str,
        language: str = 'en',
        extra: Optional[dict] = None,
    ) -> ProviderSession:
        """
        Create a new game session for a user.

        Args:
            game_id: Provider game ID.
            user_id: Platform user ID (passed as external reference).
            currency: ISO 4217 currency code, e.g. 'INR'.
            language: ISO 639-1 language code.
            extra: Additional provider-specific parameters.

        Returns:
            ProviderSession with launch URL.

        Raises:
            ProviderSessionError on failure.
        """

    @abc.abstractmethod
    def launch_game(
        self,
        session_token: str,
        return_url: str = '',
        mode: str = 'real',
    ) -> str:
        """
        Resolve the final launch URL for an existing session.

        Args:
            session_token: Token returned by create_session.
            return_url: URL to redirect to when the player closes the game.
            mode: 'real' or 'demo'.

        Returns:
            Absolute launch URL string.
        """

    # ---------- Betting --------------------------------------------------- #

    @abc.abstractmethod
    def place_bet(
        self,
        session_token: str,
        game_id: str,
        user_id: str,
        amount: Decimal,
        currency: str,
        round_id: str,
        extra: Optional[dict] = None,
    ) -> BetResult:
        """
        Place a bet on behalf of a user.

        Args:
            session_token: Active session token.
            game_id: Provider game ID.
            user_id: Platform user ID.
            amount: Wager amount.
            currency: ISO 4217 currency code.
            round_id: Platform-side idempotency key for this round.
            extra: Additional provider-specific data.

        Returns:
            BetResult describing the outcome.

        Raises:
            ProviderBetError if the bet was rejected.
        """

    # ---------- Settlement ------------------------------------------------ #

    @abc.abstractmethod
    def settle_round(
        self,
        round_id: str,
        provider_round_id: str,
        payout: Decimal,
        currency: str,
        extra: Optional[dict] = None,
    ) -> SettlementResult:
        """
        Settle a completed game round and credit / void the payout.

        Args:
            round_id: Platform round ID.
            provider_round_id: Provider's own round reference.
            payout: Amount to credit to the user (0 for a loss).
            currency: ISO 4217 currency code.
            extra: Additional provider-specific data.

        Returns:
            SettlementResult.

        Raises:
            ProviderSettlementError if settlement fails.
        """

    # ---------- Refunds --------------------------------------------------- #

    @abc.abstractmethod
    def refund(
        self,
        round_id: str,
        provider_round_id: str,
        amount: Decimal,
        currency: str,
        reason: str = '',
        extra: Optional[dict] = None,
    ) -> SettlementResult:
        """
        Refund a cancelled or errored round.

        Returns:
            SettlementResult with status='refunded'.

        Raises:
            ProviderRefundError if the refund cannot be processed.
        """

    # ---------- Balance --------------------------------------------------- #

    @abc.abstractmethod
    def get_balance(self, user_id: str, currency: str) -> Decimal:
        """
        Query the provider's record of a user's balance.

        For seamless-wallet providers this always equals the platform balance.
        For transfer-wallet providers this is the balance inside the provider's
        sub-wallet.

        Returns:
            Balance as Decimal.
        """

    # ---------- Health ---------------------------------------------------- #

    @abc.abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Probe the provider's API endpoint.

        Returns:
            HealthStatus with healthy=True/False and optional latency.
        """

    # ---------- Optional hooks -------------------------------------------- #

    def validate_config(self, config: dict) -> list[str]:
        """
        Validate a configuration dict before saving to DB.

        Returns:
            List of validation error strings (empty = valid).
        """
        return []

    def on_session_expired(self, session_token: str) -> None:
        """Called when a session token has expired. Override for cleanup."""

    def supports_demo_mode(self) -> bool:
        """Return True if the provider supports free-play / demo rounds."""
        return False

    def supported_currencies(self) -> list[str]:
        """Return list of ISO 4217 currency codes supported by this provider."""
        return ['INR', 'USD', 'EUR']

    def __repr__(self) -> str:
        return f"<ProviderAdapter: {self.provider_slug}>"
