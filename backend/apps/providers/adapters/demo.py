"""
Demo provider adapter for 49FlashMoney.

This adapter simulates a casino game provider entirely in-process — no
external HTTP calls are made.  It is designed to:

  1. Exercise the full provider abstraction stack during local development.
  2. Serve as a reference implementation when integrating a real provider.
  3. Power integration tests without mocking network calls.

The DemoProvider uses the transfer-wallet model: all money movements are
delegated to WalletService, and the adapter returns synthetic game results.

Game catalogue (all simulated):
  - demo_slots_classic     Slots (3-reel classic)
  - demo_blackjack_std     Blackjack (standard rules)
  - demo_roulette_euro     European Roulette
  - demo_crash_game        Crash / multiplier game
"""
from __future__ import annotations

import hashlib
import logging
import random
import time
import uuid
from decimal import Decimal
from typing import Optional

from ..base import (
    BaseProviderAdapter,
    BetResult,
    HealthStatus,
    ProviderGame,
    ProviderSession,
    SettlementResult,
)
from ..exceptions import (
    ProviderAuthError,
    ProviderBetError,
    ProviderGameNotFoundError,
    ProviderSessionError,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Simulated game catalogue                                                      #
# --------------------------------------------------------------------------- #

_DEMO_GAMES: list[dict] = [
    {
        'game_id': 'demo_slots_classic',
        'name': 'Classic Slots',
        'category': 'slots',
        'thumbnail_url': '',
        'min_bet': Decimal('0.10'),
        'max_bet': Decimal('500.00'),
        'rtp': Decimal('96.00'),
        'tags': ['slots', 'classic', 'demo'],
    },
    {
        'game_id': 'demo_blackjack_std',
        'name': 'Blackjack Standard',
        'category': 'table',
        'thumbnail_url': '',
        'min_bet': Decimal('1.00'),
        'max_bet': Decimal('2000.00'),
        'rtp': Decimal('99.50'),
        'tags': ['table', 'cards', 'demo'],
    },
    {
        'game_id': 'demo_roulette_euro',
        'name': 'European Roulette',
        'category': 'table',
        'thumbnail_url': '',
        'min_bet': Decimal('0.50'),
        'max_bet': Decimal('5000.00'),
        'rtp': Decimal('97.30'),
        'tags': ['table', 'roulette', 'demo'],
    },
    {
        'game_id': 'demo_crash_game',
        'name': 'Crash',
        'category': 'instant_win',
        'thumbnail_url': '',
        'min_bet': Decimal('0.10'),
        'max_bet': Decimal('1000.00'),
        'rtp': Decimal('97.00'),
        'tags': ['crash', 'multiplier', 'demo'],
    },
]

_GAME_MAP: dict[str, dict] = {g['game_id']: g for g in _DEMO_GAMES}


# --------------------------------------------------------------------------- #
# RNG helpers                                                                   #
# --------------------------------------------------------------------------- #

def _deterministic_float(seed: str) -> float:
    """Return a float in [0, 1) deterministically from a seed string."""
    digest = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return (digest % (10 ** 15)) / (10 ** 15)


def _simulate_payout(game_id: str, bet: Decimal, seed: str) -> tuple[Decimal, str]:
    """
    Simulate a bet outcome.

    Returns:
        (payout, status_str)  where status_str is one of 'won', 'lost', 'push'.
    """
    rng = _deterministic_float(seed)

    if game_id == 'demo_slots_classic':
        # ~96% RTP — house edge 4%
        if rng < 0.02:       # jackpot (2%)
            return (bet * Decimal('50')).quantize(Decimal('0.01')), 'won'
        elif rng < 0.10:     # big win (8%)
            return (bet * Decimal('5')).quantize(Decimal('0.01')), 'won'
        elif rng < 0.30:     # small win (20%)
            return (bet * Decimal('2')).quantize(Decimal('0.01')), 'won'
        else:
            return Decimal('0.00'), 'lost'

    elif game_id == 'demo_blackjack_std':
        # Simple: win / push / lose with approximate 99.5% RTP
        if rng < 0.47:
            return (bet * Decimal('2')).quantize(Decimal('0.01')), 'won'
        elif rng < 0.52:
            return bet.quantize(Decimal('0.01')), 'push'  # push — refund stake
        else:
            return Decimal('0.00'), 'lost'

    elif game_id == 'demo_roulette_euro':
        # Simulate a straight-up bet (35:1) with 1/37 win probability
        if rng < (1 / 37):
            return (bet * Decimal('36')).quantize(Decimal('0.01')), 'won'
        else:
            return Decimal('0.00'), 'lost'

    elif game_id == 'demo_crash_game':
        # Crash: random multiplier between 1.0x and 10.0x; cash-out at 1.5x
        multiplier = 1.0 + rng * 9.0
        if multiplier >= 1.5:
            return (bet * Decimal(str(round(1.5, 2)))).quantize(Decimal('0.01')), 'won'
        else:
            return Decimal('0.00'), 'lost'

    # Unknown game — refund
    return bet, 'push'


# --------------------------------------------------------------------------- #
# Adapter                                                                       #
# --------------------------------------------------------------------------- #

class DemoProviderAdapter(BaseProviderAdapter):
    """
    Fully in-process demo provider.

    No network calls; all state lives in local dicts within the process.
    Suitable for local development and integration tests only.
    """

    SLUG = 'demo'

    @property
    def provider_slug(self) -> str:
        return self.SLUG

    @property
    def display_name(self) -> str:
        return 'Demo Casino'

    # ------------------------------------------------------------------ #
    # Authentication                                                       #
    # ------------------------------------------------------------------ #

    def authenticate(self, config: dict) -> bool:
        """
        Demo accepts any config that contains the key 'demo_api_key'
        with value 'demo-secret'.
        """
        api_key = config.get('api_key', '')
        if api_key not in ('', 'demo-secret'):
            raise ProviderAuthError(
                "Invalid API key for Demo provider.",
                provider=self.SLUG,
                code='AUTH_FAILED',
            )
        logger.debug("DemoProvider: authentication succeeded")
        return True

    # ------------------------------------------------------------------ #
    # Catalogue                                                            #
    # ------------------------------------------------------------------ #

    def list_games(self, page: int = 1, page_size: int = 100) -> list[ProviderGame]:
        start = (page - 1) * page_size
        end = start + page_size
        return [
            ProviderGame(
                game_id=g['game_id'],
                name=g['name'],
                category=g['category'],
                provider=self.SLUG,
                thumbnail_url=g['thumbnail_url'],
                is_active=True,
                min_bet=g['min_bet'],
                max_bet=g['max_bet'],
                rtp=g['rtp'],
                tags=g['tags'],
            )
            for g in _DEMO_GAMES[start:end]
        ]

    def get_game(self, game_id: str) -> ProviderGame:
        g = _GAME_MAP.get(game_id)
        if not g:
            raise ProviderGameNotFoundError(
                f"Game '{game_id}' not found in Demo catalogue.",
                provider=self.SLUG,
                code='GAME_NOT_FOUND',
            )
        return ProviderGame(
            game_id=g['game_id'],
            name=g['name'],
            category=g['category'],
            provider=self.SLUG,
            thumbnail_url=g['thumbnail_url'],
            is_active=True,
            min_bet=g['min_bet'],
            max_bet=g['max_bet'],
            rtp=g['rtp'],
            tags=g['tags'],
        )

    # ------------------------------------------------------------------ #
    # Sessions                                                             #
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        game_id: str,
        user_id: str,
        currency: str,
        language: str = 'en',
        extra: Optional[dict] = None,
    ) -> ProviderSession:
        if game_id not in _GAME_MAP:
            raise ProviderSessionError(
                f"Cannot create session for unknown game '{game_id}'.",
                provider=self.SLUG,
                code='GAME_NOT_FOUND',
            )
        token = f"demo-session-{uuid.uuid4().hex}"
        launch_url = (
            f"https://demo.49flashmoney.internal/play"
            f"?game={game_id}&token={token}&lang={language}&currency={currency}"
        )
        logger.debug(
            "DemoProvider.create_session: game=%s user=%s token=%s",
            game_id, user_id, token,
        )
        return ProviderSession(
            session_token=token,
            launch_url=launch_url,
            game_id=game_id,
            user_id=user_id,
            provider=self.SLUG,
            extra={'currency': currency, 'language': language},
        )

    def launch_game(
        self,
        session_token: str,
        return_url: str = '',
        mode: str = 'real',
    ) -> str:
        url = (
            f"https://demo.49flashmoney.internal/play"
            f"?token={session_token}&mode={mode}"
        )
        if return_url:
            url += f"&return={return_url}"
        return url

    # ------------------------------------------------------------------ #
    # Betting                                                              #
    # ------------------------------------------------------------------ #

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
        if game_id not in _GAME_MAP:
            raise ProviderBetError(
                f"Game '{game_id}' not found.",
                provider=self.SLUG,
                code='GAME_NOT_FOUND',
            )
        game_meta = _GAME_MAP[game_id]
        if amount < game_meta['min_bet']:
            raise ProviderBetError(
                f"Bet {amount} is below minimum {game_meta['min_bet']}.",
                provider=self.SLUG,
                code='BET_TOO_SMALL',
            )
        if amount > game_meta['max_bet']:
            raise ProviderBetError(
                f"Bet {amount} exceeds maximum {game_meta['max_bet']}.",
                provider=self.SLUG,
                code='BET_TOO_LARGE',
            )

        provider_round_id = f"demo-round-{uuid.uuid4().hex}"
        seed = f"{round_id}:{user_id}:{game_id}:{provider_round_id}"
        payout, status = _simulate_payout(game_id, amount, seed)

        logger.info(
            "DemoProvider.place_bet: game=%s user=%s round=%s "
            "bet=%s payout=%s status=%s",
            game_id, user_id, round_id, amount, payout, status,
        )
        return BetResult(
            round_id=round_id,
            provider_round_id=provider_round_id,
            game_id=game_id,
            bet_amount=amount,
            payout=payout,
            currency=currency,
            status=status,
            state={'seed': seed},
        )

    # ------------------------------------------------------------------ #
    # Settlement                                                           #
    # ------------------------------------------------------------------ #

    def settle_round(
        self,
        round_id: str,
        provider_round_id: str,
        payout: Decimal,
        currency: str,
        extra: Optional[dict] = None,
    ) -> SettlementResult:
        logger.info(
            "DemoProvider.settle_round: round=%s provider_round=%s payout=%s",
            round_id, provider_round_id, payout,
        )
        return SettlementResult(
            round_id=round_id,
            provider_round_id=provider_round_id,
            payout=payout,
            currency=currency,
            status='settled',
        )

    # ------------------------------------------------------------------ #
    # Refunds                                                              #
    # ------------------------------------------------------------------ #

    def refund(
        self,
        round_id: str,
        provider_round_id: str,
        amount: Decimal,
        currency: str,
        reason: str = '',
        extra: Optional[dict] = None,
    ) -> SettlementResult:
        logger.info(
            "DemoProvider.refund: round=%s amount=%s reason=%s",
            round_id, amount, reason,
        )
        return SettlementResult(
            round_id=round_id,
            provider_round_id=provider_round_id,
            payout=amount,
            currency=currency,
            status='refunded',
            extra={'reason': reason},
        )

    # ------------------------------------------------------------------ #
    # Balance                                                              #
    # ------------------------------------------------------------------ #

    def get_balance(self, user_id: str, currency: str) -> Decimal:
        """
        Demo uses the transfer-wallet model so the provider doesn't hold
        a real balance.  We return 0 to signal "provider has no sub-wallet".
        In production transfer-wallet adapters this would query the platform
        ledger via WalletService.
        """
        return Decimal('0.00')

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #

    def health_check(self) -> HealthStatus:
        start = time.monotonic()
        # Simulate a fast local check
        ok = True
        latency_ms = (time.monotonic() - start) * 1000
        return HealthStatus(
            provider=self.SLUG,
            healthy=ok,
            latency_ms=round(latency_ms, 2),
            message='Demo provider is always healthy.',
        )

    # ------------------------------------------------------------------ #
    # Optional overrides                                                   #
    # ------------------------------------------------------------------ #

    def supports_demo_mode(self) -> bool:
        return True

    def supported_currencies(self) -> list[str]:
        return ['INR', 'USD', 'EUR', 'GBP']

    def validate_config(self, config: dict) -> list[str]:
        errors = []
        if 'api_key' not in config:
            errors.append("'api_key' is required in Demo provider config.")
        return errors
