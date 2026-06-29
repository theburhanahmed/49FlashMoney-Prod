"""
Ludo game engine (simplified).

State structure:
- players: list of { user_id (str), position (int), finished (bool) }
  - position == -1 => token is still in base and not yet on the board
  - position >= 0  => position along the track
- current_turn_index: index into players list
- last_dice: last rolled dice value (int or None)
- winner_id: user_id (str) of winner, or None
- phase: 'rolling' or 'finished'
- extra_turn: bool indicating whether current player gets another turn

Rules (MVP):
- Up to 4 players.
- Each player has a single token.
- To leave base (position == -1), player must roll a 6. The token then moves to position 0.
- On subsequent rolls, the token advances by the dice value.
- If the token's position reaches or passes PATH_LENGTH - 1, the player wins.
- Rolling a 6 grants an extra turn (unless the game is already finished).
"""

import random
from typing import Dict, Any


PATH_LENGTH = 52  # Simplified single-loop track length


def _build_players(room) -> list:
    """
    Build initial players list from GameRoomPlayer instances.
    Each player starts with a single token in base (position = -1).
    """
    user_ids = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )
    return [
        {
            'user_id': str(uid),
            'position': -1,  # -1 means in base
            'finished': False,
        }
        for uid in user_ids
    ]


def initial_state(room, config: Dict[str, Any]) -> dict:
    """
    Build initial game state for Ludo.
    """
    players = _build_players(room)
    return {
        'players': players,
        'current_turn_index': 0,
        'last_dice': None,
        'winner_id': None,
        'phase': 'rolling',
        'extra_turn': False,
    }


def _roll_dice(room_id: str, version: int) -> int:
    """
    Deterministic dice roll based on room_id and version.
    Mirrors the approach used in the Snakes & Ladders engine.
    """
    rng = random.Random(f'{room_id}-ludo-{version}')
    return rng.randint(1, 6)


def apply_action(state: dict, user_id: str, action: dict, room_id: str, version: int) -> dict:
    """
    Apply one Ludo action (currently only 'roll_dice') and return new state.
    Raises ValueError if invalid move.
    """
    import copy

    state = copy.deepcopy(state)
    user_id = str(user_id)
    players = state.get('players', [])
    current_turn_index = state.get('current_turn_index', 0)
    phase = state.get('phase', 'rolling')
    winner_id = state.get('winner_id')

    if winner_id:
        raise ValueError('Game already finished')

    if phase != 'rolling':
        raise ValueError('Invalid phase')

    if current_turn_index >= len(players):
        raise ValueError('No current player')

    current_player = players[current_turn_index]
    if current_player.get('user_id') != user_id:
        raise ValueError('Not your turn')

    action_type = action.get('action')
    if action_type != 'roll_dice':
        raise ValueError('Unknown action')

    dice = _roll_dice(room_id, version)

    position = current_player.get('position', -1)
    finished = current_player.get('finished', False)

    # If already finished, nothing should move, but treat as completed game
    if finished:
        raise ValueError('Player already finished')

    # Movement rules
    if position == -1:
        # In base; need a 6 to enter
        if dice == 6:
            new_position = 0
        else:
            new_position = -1
    else:
        new_position = position + dice

    current_player['position'] = new_position

    extra_turn = dice == 6
    if new_position >= PATH_LENGTH - 1:
        # Player wins
        state['last_dice'] = dice
        state['winner_id'] = user_id
        current_player['finished'] = True
        state['phase'] = 'finished'
        state['extra_turn'] = False
        return state

    next_turn_index = current_turn_index
    if not extra_turn:
        next_turn_index = (current_turn_index + 1) % len(players)

    state['current_turn_index'] = next_turn_index
    state['last_dice'] = dice
    state['phase'] = 'rolling'
    state['extra_turn'] = extra_turn
    return state

