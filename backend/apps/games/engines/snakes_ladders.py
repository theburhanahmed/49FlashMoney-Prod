"""
Snakes & Ladders game engine.
Board: 100 cells. Classic snake and ladder positions.
State: players (user_id, position), current_turn_index, last_dice, winner_id, phase.
"""
import random
from decimal import Decimal


# Classic 10x10 board: snakes and ladders (cell -> destination)
# Snakes: head -> tail (go down)
SNAKES = {
    16: 6, 31: 19, 47: 26, 56: 53, 62: 18, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78,
}
LADDERS = {
    1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100,
}


def get_destination(cell: int) -> int:
    """Apply snake or ladder if present, else return cell."""
    if cell in SNAKES:
        return SNAKES[cell]
    if cell in LADDERS:
        return LADDERS[cell]
    return cell


def initial_state(room, config: dict) -> dict:
    """
    Build initial game state for Snakes & Ladders.
    room: GameRoom with players (GameRoomPlayer ordered by position).
    config: optional game config (e.g. board_size).
    """
    players = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )
    # state: list of { user_id (str), position (int) }
    return {
        'players': [{'user_id': str(uid), 'position': 0} for uid in players],
        'current_turn_index': 0,
        'last_dice': None,
        'winner_id': None,
        'phase': 'rolling',
        'extra_turn': False,
    }


def apply_action(state: dict, user_id: str, action: dict, room_id: str, version: int) -> dict:
    """
    Apply one action (roll_dice) and return new state.
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

    # Roll 1-6
    rng = random.Random(f'{room_id}-{version}')
    dice = rng.randint(1, 6)

    # Find current position and move
    position = current_player.get('position', 0)
    new_position = min(100, position + dice)
    new_position = get_destination(new_position)
    current_player['position'] = new_position

    extra_turn = dice == 6
    if new_position >= 100:
        state['last_dice'] = dice
        state['winner_id'] = user_id
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
