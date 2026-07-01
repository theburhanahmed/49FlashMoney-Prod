"""
Abstract base class for 49FlashMoney game engines.

Every game engine MUST implement this contract. The platform dispatches
to engines through the registry and relies on these methods for:
- Round/session initialisation
- Action processing (bets, moves, cash-outs, ticks)
- Outcome resolution and payout calculation
- Public state sanitisation (hide secrets from clients)

The orchestration layer (GameService) handles wallet debits/credits,
ledger entries, event publishing, and persistence. Engines are pure
game-logic units and MUST NOT import wallet or payment modules.
"""
from __future__ import annotations

import abc
import copy
from decimal import Decimal
from typing import Any, Dict, List, Optional


class GameEngine(abc.ABC):
    """
    Shared contract for all 49FlashMoney game engines.

    Subclasses implement class-level methods so the registry can call
    them without instantiation (matching the existing module-function API).
    """

    # ── Identity ──────────────────────────────────────────────────────

    @staticmethod
    @abc.abstractmethod
    def game_kind() -> str:
        """Return the GameKind constant this engine handles."""
        ...

    @staticmethod
    @abc.abstractmethod
    def default_config() -> Dict[str, Any]:
        """
        Return the default configuration dict for this game.
        Used when admin creates a new game without explicit config.
        """
        ...

    # ── Lifecycle ─────────────────────────────────────────────────────

    @staticmethod
    @abc.abstractmethod
    def initial_state(room: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the initial game state when a round/session starts.

        Args:
            room: GameRoom model instance (with .players queryset).
            config: Merged game configuration dict.

        Returns:
            A JSON-serialisable dict representing the full game state.
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def apply_action(
        state: Dict[str, Any],
        user_id: str,
        action: Dict[str, Any],
        room_id: str,
        version: int,
    ) -> Dict[str, Any]:
        """
        Apply a single action to the game state and return the new state.

        The returned state MUST be a new dict (deep-copied). The caller
        persists the new state and increments the version.

        Args:
            state: Current game state dict (deep-copy before mutating).
            user_id: The acting user's UUID string.
            action: Action payload, must contain at least ``{"action": "<type>"}``.
            room_id: The game room's UUID string (for deterministic RNG seeding).
            version: Current state version (for deterministic RNG seeding).

        Returns:
            New game state dict.

        Raises:
            ValueError: For invalid moves, out-of-turn actions, etc.
        """
        ...

    # ── Query helpers ─────────────────────────────────────────────────

    @staticmethod
    def get_public_state(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a sanitised copy of the state safe for client broadcast.
        Override to strip secrets (e.g. crash point, mine positions).
        Default implementation returns a full deep-copy.
        """
        return copy.deepcopy(state)

    @staticmethod
    def is_finished(state: Dict[str, Any]) -> bool:
        """Return True when the round/session is complete."""
        return state.get('phase') == 'finished'

    @staticmethod
    def get_winners(state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Return list of winner dicts after the round is finished.

        Each dict: {"user_id": str, "payout": Decimal, "result": str}
        Default derives from ``winner_id`` for simple 1-winner games.
        Multi-winner games (Aviator, Wingo) MUST override.
        """
        winner_id = state.get('winner_id')
        if not winner_id or winner_id in ('CRASH_RESOLVED', 'WINGO_RESOLVED'):
            return []
        return [{'user_id': winner_id, 'result': 'WON', 'payout': Decimal('0')}]

    # ── Validation helpers ────────────────────────────────────────────

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration dict. Return list of error strings.
        Empty list means valid. Override for game-specific checks.
        """
        return []

    @staticmethod
    def validate_bet(
        state: Dict[str, Any],
        user_id: str,
        amount: Decimal,
        action: Dict[str, Any],
    ) -> Optional[str]:
        """
        Pre-validate a bet before wallet debit.
        Return None if valid, or an error message string.
        Default: check phase == 'betting'.
        """
        phase = state.get('phase', '')
        if phase != 'betting':
            return f'Cannot place bet during {phase} phase'
        return None
