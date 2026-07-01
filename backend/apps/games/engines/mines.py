"""
Mines game engine for 49FlashMoney.

Single-player grid game. The player places a bet, then reveals tiles
on a hidden grid. Some tiles are "gems" (safe), others are "mines"
(instant loss). The player can cash out at any time after revealing
at least one safe tile, locking in a payout that increases with each
successive safe reveal.

State shape:
{
  "phase": "betting" | "playing" | "cashed_out" | "exploded" | "finished",
  "grid_size": int,           # e.g. 25 (5x5)
  "mine_count": int,
  "mine_positions": [int],    # hidden from client until game ends
  "revealed": [int],          # indices of revealed tiles
  "bet_amount": str,
  "current_multiplier": str,
  "payout": str | null,
  "user_id": str,
  "round_id": str,
  "winner_id": str | null,
  "config": {...},
}

Engine interface:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict

Actions:
- {"action": "place_bet", "amount": "10.00", "mine_count": 5}
- {"action": "reveal", "tile": 12}
- {"action": "cash_out"}
"""
import copy
import hashlib
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional


DEFAULT_GRID_SIZE = 25  # 5x5
DEFAULT_MIN_MINES = 1
DEFAULT_MAX_MINES = 24
DEFAULT_MIN_BET = Decimal('1.00')
DEFAULT_MAX_BET = Decimal('500.00')
DEFAULT_HOUSE_EDGE = Decimal('0.02')  # 2%


def _generate_mine_positions(
    room_id: str, version: int, grid_size: int, mine_count: int
) -> list:
    """
    Generate deterministic mine positions using room_id + version as seed.
    Returns sorted list of mine indices.
    """
    seed = f"{room_id}:{version}:mines_positions"
    hash_bytes = hashlib.sha256(seed.encode()).digest()

    # Fisher-Yates-like selection using hash bytes
    positions = list(range(grid_size))
    # Use chunks of the hash to shuffle
    extended_seed = seed
    idx = 0
    for i in range(grid_size - 1, 0, -1):
        if idx + 4 > len(hash_bytes):
            extended_seed = extended_seed + ':ext'
            hash_bytes = hashlib.sha256(extended_seed.encode()).digest()
            idx = 0
        j = int.from_bytes(hash_bytes[idx:idx + 4], 'big') % (i + 1)
        idx += 4
        positions[i], positions[j] = positions[j], positions[i]

    return sorted(positions[:mine_count])


def _calculate_multiplier(
    grid_size: int, mine_count: int, reveals: int, house_edge: Decimal = DEFAULT_HOUSE_EDGE
) -> Decimal:
    """
    Calculate the current multiplier based on how many safe tiles revealed.
    Uses the combinatorial fair odds minus house edge.

    Fair multiplier for k reveals with m mines on n tiles:
      product_{i=0}^{k-1} (n - i) / (n - m - i)
    Then apply (1 - house_edge).
    """
    if reveals <= 0:
        return Decimal('1.00')

    safe_tiles = grid_size - mine_count
    if reveals > safe_tiles:
        return Decimal('0.00')  # impossible

    multiplier = Decimal('1.0')
    for i in range(reveals):
        numerator = Decimal(grid_size - i)
        denominator = Decimal(safe_tiles - i)
        if denominator <= 0:
            return Decimal('0.00')
        multiplier *= numerator / denominator

    # Apply house edge
    multiplier *= (Decimal('1') - house_edge)
    return multiplier.quantize(Decimal('0.01'), rounding=ROUND_DOWN)


# ── Engine interface ──────────────────────────────────────────────────


def initial_state(room, config: dict) -> dict:
    """
    Build initial Mines game state. Starts in 'betting' phase.
    Mines is a single-player game; room should have exactly 1 player.
    """
    players = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )
    user_id = str(players[0]) if players else ''

    grid_size = config.get('grid_size', DEFAULT_GRID_SIZE)

    return {
        'phase': 'betting',
        'grid_size': grid_size,
        'mine_count': 0,
        'mine_positions': [],
        'revealed': [],
        'bet_amount': '0.00',
        'current_multiplier': '1.00',
        'payout': None,
        'user_id': user_id,
        'players': [user_id],
        'round_id': str(room.id),
        'winner_id': None,
        'config': {
            'grid_size': grid_size,
            'min_mines': config.get('min_mines', DEFAULT_MIN_MINES),
            'max_mines': config.get('max_mines', DEFAULT_MAX_MINES),
            'min_bet': str(config.get('min_bet', DEFAULT_MIN_BET)),
            'max_bet': str(config.get('max_bet', DEFAULT_MAX_BET)),
            'house_edge': str(config.get('house_edge', DEFAULT_HOUSE_EDGE)),
        },
    }


def apply_action(
    state: dict, user_id: str, action: dict, room_id: str, version: int
) -> dict:
    """Apply an action to the Mines game state."""
    state = copy.deepcopy(state)
    user_id = str(user_id)
    action_type = action.get('action')
    phase = state.get('phase', 'betting')

    if phase in ('cashed_out', 'exploded', 'finished'):
        raise ValueError('Round is already finished')

    if action_type == 'place_bet':
        return _handle_place_bet(state, user_id, action, room_id, version)
    elif action_type == 'reveal':
        return _handle_reveal(state, user_id, action)
    elif action_type == 'cash_out':
        return _handle_cash_out(state, user_id)
    else:
        raise ValueError(f'Unknown action: {action_type}')


def _handle_place_bet(
    state: dict, user_id: str, action: dict, room_id: str, version: int
) -> dict:
    """Place a bet and initialise the mine grid."""
    if state['phase'] != 'betting':
        raise ValueError('Bet can only be placed during betting phase')

    if user_id != state.get('user_id', ''):
        raise ValueError('Not the player in this room')

    amount_str = action.get('amount')
    mine_count = action.get('mine_count')
    if not amount_str or mine_count is None:
        raise ValueError('amount and mine_count are required')

    amount = Decimal(str(amount_str))
    mine_count = int(mine_count)
    grid_size = state['grid_size']
    min_bet = Decimal(state['config']['min_bet'])
    max_bet = Decimal(state['config']['max_bet'])
    min_mines = state['config']['min_mines']
    max_mines = state['config']['max_mines']

    if amount < min_bet or amount > max_bet:
        raise ValueError(f'Bet must be between {min_bet} and {max_bet}')
    if mine_count < min_mines or mine_count > max_mines:
        raise ValueError(f'Mine count must be between {min_mines} and {max_mines}')
    if mine_count >= grid_size:
        raise ValueError('Mine count must be less than grid size')

    # Generate mine positions deterministically
    mine_positions = _generate_mine_positions(room_id, version, grid_size, mine_count)

    state['mine_count'] = mine_count
    state['mine_positions'] = mine_positions
    state['bet_amount'] = str(amount)
    state['phase'] = 'playing'
    state['revealed'] = []
    state['current_multiplier'] = '1.00'

    return state


def _handle_reveal(state: dict, user_id: str, action: dict) -> dict:
    """Reveal a tile. If mine → explode. If safe → update multiplier."""
    if state['phase'] != 'playing':
        raise ValueError('Can only reveal tiles during playing phase')

    if user_id != state.get('user_id', ''):
        raise ValueError('Not the player in this room')

    tile = action.get('tile')
    if tile is None:
        raise ValueError('tile index is required')
    tile = int(tile)

    grid_size = state['grid_size']
    if tile < 0 or tile >= grid_size:
        raise ValueError(f'tile must be 0-{grid_size - 1}')
    if tile in state['revealed']:
        raise ValueError('Tile already revealed')

    mine_positions = state['mine_positions']

    if tile in mine_positions:
        # BOOM - mine hit
        state['phase'] = 'exploded'
        state['payout'] = '0.00'
        state['current_multiplier'] = '0.00'
        state['winner_id'] = 'MINES_EXPLODED'
        state['phase'] = 'finished'
        return state

    # Safe tile
    state['revealed'].append(tile)
    reveals = len(state['revealed'])
    house_edge = Decimal(state['config'].get('house_edge', str(DEFAULT_HOUSE_EDGE)))
    multiplier = _calculate_multiplier(grid_size, state['mine_count'], reveals, house_edge)
    state['current_multiplier'] = str(multiplier)

    # Check if all safe tiles revealed (auto cash-out)
    safe_tiles = grid_size - state['mine_count']
    if reveals >= safe_tiles:
        return _handle_cash_out(state, user_id)

    return state


def _handle_cash_out(state: dict, user_id: str) -> dict:
    """Cash out at current multiplier."""
    if state['phase'] != 'playing':
        raise ValueError('Can only cash out during playing phase')

    if user_id != state.get('user_id', ''):
        raise ValueError('Not the player in this room')

    if len(state['revealed']) == 0:
        raise ValueError('Must reveal at least one tile before cashing out')

    amount = Decimal(state['bet_amount'])
    multiplier = Decimal(state['current_multiplier'])
    payout = (amount * multiplier).quantize(Decimal('0.01'))

    state['phase'] = 'finished'
    state['payout'] = str(payout)
    state['winner_id'] = user_id  # player wins
    return state


# ── ABC-compatible helpers ────────────────────────────────────────────


def game_kind() -> str:
    return 'MINES'


def default_config() -> dict:
    return {
        'grid_size': DEFAULT_GRID_SIZE,
        'min_mines': DEFAULT_MIN_MINES,
        'max_mines': DEFAULT_MAX_MINES,
        'min_bet': str(DEFAULT_MIN_BET),
        'max_bet': str(DEFAULT_MAX_BET),
        'house_edge': str(DEFAULT_HOUSE_EDGE),
    }


def is_finished(state: dict) -> bool:
    return state.get('phase') == 'finished'


def get_winners(state: dict) -> list:
    """Return list of winner dicts."""
    if not is_finished(state):
        return []
    payout = state.get('payout')
    winner_id = state.get('winner_id')
    if not payout or not winner_id or winner_id == 'MINES_EXPLODED':
        return []
    payout_dec = Decimal(payout)
    if payout_dec <= 0:
        return []
    return [{'user_id': winner_id, 'result': 'WON', 'payout': payout_dec}]


def get_public_state(state: dict) -> dict:
    """Strip mine_positions during play."""
    public = copy.deepcopy(state)
    if public.get('phase') == 'playing':
        public.pop('mine_positions', None)
    return public


def validate_config(config: dict) -> list:
    errors = []
    grid = config.get('grid_size', DEFAULT_GRID_SIZE)
    if grid < 4 or grid > 49:
        errors.append('grid_size must be between 4 and 49')
    if 'min_bet' in config and 'max_bet' in config:
        if Decimal(str(config['min_bet'])) >= Decimal(str(config['max_bet'])):
            errors.append('min_bet must be less than max_bet')
    he = Decimal(str(config.get('house_edge', DEFAULT_HOUSE_EDGE)))
    if not (Decimal('0') < he < Decimal('0.5')):
        errors.append('house_edge must be between 0 and 0.5')
    return errors


def validate_bet(state: dict, user_id: str, amount: Decimal, action: dict):
    if state.get('phase') != 'betting':
        return 'Bet can only be placed during betting phase'
    min_bet = Decimal(state.get('config', {}).get('min_bet', '1.00'))
    max_bet = Decimal(state.get('config', {}).get('max_bet', '500.00'))
    if amount < min_bet or amount > max_bet:
        return f'Bet must be between {min_bet} and {max_bet}'
    return None
