"""
Game engines registry.

This module exposes a simple dispatcher so the rest of the codebase can
select the appropriate engine implementation based on GameKind.

Each engine module must provide:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict
"""
from apps.games.models import GameKind
from . import snakes_ladders, ludo, carrom, aviator, wingo


ENGINE_REGISTRY = {
    GameKind.SNAKES_LADDERS: snakes_ladders,
    GameKind.LUDO: ludo,
    GameKind.CARROM: carrom,
    GameKind.AVIATOR: aviator,
    GameKind.WINGO: wingo,
}


def get_engine_for_game_kind(game_kind: str):
    """
    Return the engine module for the given game kind.

    The returned object is expected to provide:
    - initial_state(room, config)
    - apply_action(state, user_id, action, room_id, version)
    """
    try:
        return ENGINE_REGISTRY[game_kind]
    except KeyError:
        raise ValueError(f'No engine for game kind: {game_kind}')


__all__ = [
    'snakes_ladders', 'ludo', 'carrom', 'aviator', 'wingo',
    'get_engine_for_game_kind',
]
