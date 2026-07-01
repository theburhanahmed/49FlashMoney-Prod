"""
Aviator game engine for 49FlashMoney.

Real-time multiplier crash game. A round starts at 1.00x and increases
until a randomly determined crash point. Players can cash out at any time
before the crash to lock in (bet * multiplier) as winnings.

State shape:
{
  "phase": "betting" | "flying" | "crashed" | "finished",
  "crash_point": float,         # secret until crash
  "current_multiplier": float,  # increases during flying
  "tick": int,                  # discrete time step
  "bets": [
    {"user_id": str, "amount": str, "cashed_out": bool,
     "cashout_multiplier": float|null, "payout": str|null}
  ],
  "round_id": str,
  "winner_id": null,            # not used for aviator (multi-player payout)
}

Engine interface:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict

Actions:
- {"action": "place_bet", "amount": "10.00"}
- {"action": "cash_out"}
- {"action": "tick"}  (server-driven: advance multiplier)
- {"action": "crash"} (server-driven: resolve round)
"""
import copy
import hashlib
import math
from decimal import Decimal


# Multiplier growth per tick (configurable via room config)
DEFAULT_TICK_INCREMENT = 0.05  # +0.05x per tick
DEFAULT_MIN_BET = Decimal('1.00')
DEFAULT_MAX_BET = Decimal('1000.00')


def _generate_crash_point(room_id: str, version: int, house_edge: float = 0.03) -> float:
    """
    Generate a provably fair crash point using room_id and version as seed.
    Uses a hash-based approach with configurable house edge.
    Minimum crash point is 1.00 (instant crash).
    """
    seed = f"{room_id}:{version}:aviator_crash"
    hash_hex = hashlib.sha256(seed.encode()).hexdigest()
    # Use first 8 hex chars -> 32-bit int
    h = int(hash_hex[:8], 16)
    # Map to crash point with house edge
    # E(crash_point) = 1 / house_edge when house_edge > 0
    e = 2 ** 32
    if h % 33 == 0:
        # ~3% chance of instant crash (house edge)
        return 1.00
    # Crash point formula: result = (e / (e - h)) with house edge applied
    result = (1 - house_edge) * e / (e - h)
    return max(1.00, round(result, 2))


def initial_state(room, config: dict) -> dict:
    """
    Build initial Aviator game state.
    Phase starts as 'betting' - players place bets before round starts flying.
    """
    room_id = str(room.id)
    house_edge = config.get('house_edge', 0.03)
    crash_point = _generate_crash_point(room_id, 0, house_edge)

    players = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )

    return {
        'phase': 'betting',
        'crash_point': crash_point,  # Hidden from clients during play
        'current_multiplier': 1.00,
        'tick': 0,
        'bets': [],
        'players': [str(uid) for uid in players],
        'round_id': room_id,
        'winner_id': None,  # Aviator doesn't use single winner
        'config': {
            'tick_increment': config.get('tick_increment', DEFAULT_TICK_INCREMENT),
            'min_bet': str(config.get('min_bet', DEFAULT_MIN_BET)),
            'max_bet': str(config.get('max_bet', DEFAULT_MAX_BET)),
        },
    }


def apply_action(state: dict, user_id: str, action: dict, room_id: str, version: int) -> dict:
    """
    Apply an action to the Aviator game state.

    Actions:
    - place_bet: Player places a bet during betting phase.
    - cash_out: Player cashes out during flying phase.
    - start_flight: Server action to transition from betting to flying.
    - tick: Server action to advance the multiplier.
    - crash: Server action to resolve the round.
    """
    state = copy.deepcopy(state)
    user_id = str(user_id)
    action_type = action.get('action')
    phase = state.get('phase', 'betting')

    if phase == 'finished' or phase == 'crashed':
        raise ValueError('Round is already finished')

    if action_type == 'place_bet':
        return _handle_place_bet(state, user_id, action)
    elif action_type == 'cash_out':
        return _handle_cash_out(state, user_id)
    elif action_type == 'start_flight':
        return _handle_start_flight(state)
    elif action_type == 'tick':
        return _handle_tick(state)
    elif action_type == 'crash':
        return _handle_crash(state)
    else:
        raise ValueError(f'Unknown action: {action_type}')


def _handle_place_bet(state: dict, user_id: str, action: dict) -> dict:
    """Place a bet during the betting phase."""
    if state['phase'] != 'betting':
        raise ValueError('Bets can only be placed during betting phase')

    # Check if user already has a bet
    for bet in state['bets']:
        if bet['user_id'] == user_id:
            raise ValueError('Already placed a bet this round')

    amount_str = action.get('amount')
    if not amount_str:
        raise ValueError('Bet amount is required')

    amount = Decimal(str(amount_str))
    min_bet = Decimal(state['config']['min_bet'])
    max_bet = Decimal(state['config']['max_bet'])

    if amount < min_bet or amount > max_bet:
        raise ValueError(f'Bet must be between {min_bet} and {max_bet}')

    state['bets'].append({
        'user_id': user_id,
        'amount': str(amount),
        'cashed_out': False,
        'cashout_multiplier': None,
        'payout': None,
    })

    return state


def _handle_cash_out(state: dict, user_id: str) -> dict:
    """Cash out during the flying phase."""
    if state['phase'] != 'flying':
        raise ValueError('Can only cash out during flying phase')

    for bet in state['bets']:
        if bet['user_id'] == user_id:
            if bet['cashed_out']:
                raise ValueError('Already cashed out')

            multiplier = state['current_multiplier']
            amount = Decimal(bet['amount'])
            payout = (amount * Decimal(str(multiplier))).quantize(Decimal('0.01'))

            bet['cashed_out'] = True
            bet['cashout_multiplier'] = multiplier
            bet['payout'] = str(payout)
            return state

    raise ValueError('No bet found for this user')


def _handle_start_flight(state: dict) -> dict:
    """Transition from betting to flying phase (server-driven)."""
    if state['phase'] != 'betting':
        raise ValueError('Can only start flight from betting phase')

    if len(state['bets']) == 0:
        raise ValueError('No bets placed - cannot start flight')

    state['phase'] = 'flying'
    state['current_multiplier'] = 1.00
    state['tick'] = 0
    return state


def _handle_tick(state: dict) -> dict:
    """Advance multiplier by one tick (server-driven)."""
    if state['phase'] != 'flying':
        raise ValueError('Can only tick during flying phase')

    tick_increment = state['config'].get('tick_increment', DEFAULT_TICK_INCREMENT)
    state['tick'] += 1

    # Exponential-ish growth: multiplier increases faster over time
    new_multiplier = 1.00 + (state['tick'] * tick_increment)
    # Add slight exponential curve
    new_multiplier = round(new_multiplier * (1 + state['tick'] * 0.001), 2)
    state['current_multiplier'] = new_multiplier

    # Check if crash point reached
    if new_multiplier >= state['crash_point']:
        return _handle_crash(state)

    return state


def _handle_crash(state: dict) -> dict:
    """Resolve the round - players who didn't cash out lose."""
    state['phase'] = 'crashed'

    # Mark non-cashed-out bets as lost
    for bet in state['bets']:
        if not bet['cashed_out']:
            bet['payout'] = '0.00'
            bet['cashout_multiplier'] = 0.0

    # Set winner_id to signal game completion (use 'CRASH' marker)
    # The game room end_game logic uses winner_id to detect completion
    state['winner_id'] = 'CRASH_RESOLVED'
    state['phase'] = 'finished'
    return state


def get_public_state(state: dict) -> dict:
    """
    Return a sanitized state safe for clients (hide crash_point during flight).
    """
    public = copy.deepcopy(state)
    if public['phase'] == 'flying' or public['phase'] == 'betting':
        public.pop('crash_point', None)
    return public


def game_kind() -> str:
    return 'AVIATOR'


def default_config() -> dict:
    return {
        'tick_increment': DEFAULT_TICK_INCREMENT,
        'min_bet': str(DEFAULT_MIN_BET),
        'max_bet': str(DEFAULT_MAX_BET),
        'house_edge': 0.03,
    }


def is_finished(state: dict) -> bool:
    return state.get('phase') == 'finished'


def get_winners(state: dict) -> list:
    """Return list of winner dicts for players who cashed out."""
    if not is_finished(state):
        return []
    winners = []
    for bet in state.get('bets', []):
        if bet.get('cashed_out') and bet.get('payout') and Decimal(bet['payout']) > 0:
            winners.append({
                'user_id': bet['user_id'],
                'result': 'WON',
                'payout': Decimal(bet['payout']),
            })
    return winners


def validate_config(config: dict) -> list:
    errors = []
    if 'min_bet' in config and 'max_bet' in config:
        if Decimal(str(config['min_bet'])) >= Decimal(str(config['max_bet'])):
            errors.append('min_bet must be less than max_bet')
    he = config.get('house_edge', 0.03)
    if not (0 < he < 1):
        errors.append('house_edge must be between 0 and 1')
    return errors


def validate_bet(state: dict, user_id: str, amount: Decimal, action: dict):
    if state.get('phase') != 'betting':
        return 'Bets can only be placed during betting phase'
    for bet in state.get('bets', []):
        if bet['user_id'] == str(user_id):
            return 'Already placed a bet this round'
    min_bet = Decimal(state.get('config', {}).get('min_bet', '1.00'))
    max_bet = Decimal(state.get('config', {}).get('max_bet', '1000.00'))
    if amount < min_bet or amount > max_bet:
        return f'Bet must be between {min_bet} and {max_bet}'
    return None
