"""
Carrom game engine (simplified scoring model).

State structure:
- players: list of { user_id (str), score (int) }
- current_turn_index: index into players list
- last_points: last points scored in a shot (int or None)
- winner_id: user_id (str) of winner, or None
- phase: 'playing' or 'finished'
- extra_turn: bool indicating whether current player gets another turn

Rules (MVP):
- Turn-based scoring.
- Client sends an action with the number of points scored in a shot.
- If a player reaches or exceeds WINNING_SCORE, they win.
- Scoring a non-zero number of points grants an extra turn.
"""

from typing import Dict, Any


WINNING_SCORE = 29


def _build_players(room) -> list:
    """
    Build initial players list from GameRoomPlayer instances.
    Each player starts with score 0.
    """
    user_ids = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )
    return [
        {
            'user_id': str(uid),
            'score': 0,
        }
        for uid in user_ids
    ]


def initial_state(room, config: Dict[str, Any]) -> dict:
    """
    Build initial game state for Carrom.
    """
    players = _build_players(room)
    return {
        'players': players,
        'current_turn_index': 0,
        'last_points': None,
        'winner_id': None,
        'phase': 'playing',
        'extra_turn': False,
    }


def apply_action(state: dict, user_id: str, action: dict, room_id: str, version: int) -> dict:
    """
    Apply one Carrom action (currently only 'record_shot') and return new state.
    Raises ValueError if invalid move.
    """
    import copy

    state = copy.deepcopy(state)
    user_id = str(user_id)
    players = state.get('players', [])
    current_turn_index = state.get('current_turn_index', 0)
    phase = state.get('phase', 'playing')
    winner_id = state.get('winner_id')

    if winner_id:
        raise ValueError('Game already finished')

    if phase != 'playing':
        raise ValueError('Invalid phase')

    if current_turn_index >= len(players):
        raise ValueError('No current player')

    current_player = players[current_turn_index]
    if current_player.get('user_id') != user_id:
        raise ValueError('Not your turn')

    action_type = action.get('action')
    if action_type != 'record_shot':
        raise ValueError('Unknown action')

    try:
        points = int(action.get('points', 0))
    except (TypeError, ValueError):
        raise ValueError('Invalid points value')

    if points < 0:
        raise ValueError('Points cannot be negative')

    current_score = int(current_player.get('score', 0))
    new_score = current_score + points
    current_player['score'] = new_score

    if new_score >= WINNING_SCORE:
        state['last_points'] = points
        state['winner_id'] = user_id
        state['phase'] = 'finished'
        state['extra_turn'] = False
        return state

    extra_turn = points > 0

    next_turn_index = current_turn_index
    if not extra_turn:
        next_turn_index = (current_turn_index + 1) % len(players)

    state['current_turn_index'] = next_turn_index
    state['last_points'] = points
    state['extra_turn'] = extra_turn
    return state

