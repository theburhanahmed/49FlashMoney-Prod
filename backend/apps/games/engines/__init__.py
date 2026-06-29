"""
Game engines: Snakes & Ladders, future Ludo, Carrom, etc.

This module exposes a simple dispatcher so the rest of the codebase can
select the appropriate engine implementation based on GameKind.
"""
from apps.games.models import GameKind
from . import snakes_ladders, ludo, carrom


ENGINE_REGISTRY = {
    GameKind.SNAKES_LADDERS: snakes_ladders,
    GameKind.LUDO: ludo,
    GameKind.CARROM: carrom,
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


__all__ = ['snakes_ladders', 'ludo', 'carrom', 'get_engine_for_game_kind']
