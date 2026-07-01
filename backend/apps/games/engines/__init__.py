"""
Game engines registry.

Every engine module or class MUST provide at minimum:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict

Engines may also provide (optional, with defaults in GameEngine ABC):
- get_public_state(state) -> dict  (strip secrets before broadcast)
- is_finished(state) -> bool
- get_winners(state) -> list[dict]
- validate_config(config) -> list[str]
- validate_bet(state, user_id, amount, action) -> str | None
- default_config() -> dict
"""
from apps.games.models import GameKind
from . import snakes_ladders, ludo, carrom, aviator, wingo, mines, scratch_card
from .base import GameEngine  # noqa: F401 – re-export for consumers


ENGINE_REGISTRY = {
    GameKind.SNAKES_LADDERS: snakes_ladders,
    GameKind.LUDO: ludo,
    GameKind.CARROM: carrom,
    GameKind.AVIATOR: aviator,
    GameKind.WINGO: wingo,
    GameKind.MINES: mines,
    GameKind.SCRATCH_CARD: scratch_card,
}


def get_engine_for_game_kind(game_kind: str):
    """
    Return the engine module/class for the given game kind.

    The returned object is guaranteed to provide:
    - initial_state(room, config)
    - apply_action(state, user_id, action, room_id, version)
    """
    try:
        return ENGINE_REGISTRY[game_kind]
    except KeyError:
        raise ValueError(f'No engine for game kind: {game_kind}')


def list_registered_engines() -> list:
    """Return a list of registered game kinds and their metadata."""
    result = []
    for kind, engine in ENGINE_REGISTRY.items():
        info = {
            'game_kind': kind,
            'module': engine.__name__,
        }
        if hasattr(engine, 'default_config'):
            info['has_default_config'] = True
        if hasattr(engine, 'get_public_state'):
            info['has_public_state'] = True
        if hasattr(engine, 'get_winners'):
            info['has_get_winners'] = True
        result.append(info)
    return result


__all__ = [
    'GameEngine',
    'snakes_ladders', 'ludo', 'carrom', 'aviator', 'wingo', 'mines', 'scratch_card',
    'get_engine_for_game_kind', 'list_registered_engines',
]
