"""
Wingo game engine for 49FlashMoney.

Round-based prediction game. Players bet on a predicted outcome (number or color)
during a betting window. When the window closes, an outcome is generated and
players who predicted correctly receive payouts per the payout table.

State shape:
{
  "phase": "betting" | "locked" | "resolving" | "resolved" | "finished",
  "round_number": int,
  "outcome": int|null,          # 0-9 for number-based game
  "outcome_color": str|null,    # "RED", "GREEN", "VIOLET"
  "bets": [
    {"user_id": str, "amount": str, "prediction_type": str,
     "prediction_value": str, "won": bool|null, "payout": str|null}
  ],
  "players": [str],
  "round_id": str,
  "winner_id": null,
  "config": {...},
}

Engine interface:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict

Actions:
- {"action": "place_bet", "amount": "10.00", "prediction_type": "number"|"color"|"big_small",
   "prediction_value": "5"|"RED"|"BIG"}
- {"action": "lock"}     (server-driven: close betting window)
- {"action": "resolve"}  (server-driven: generate outcome and settle)
"""
import copy
import hashlib
from decimal import Decimal


# Number to color mapping (standard Wingo layout)
# 0 = VIOLET+RED, 5 = VIOLET+GREEN
# 1,3,7,9 = GREEN
# 2,4,6,8 = RED
NUMBER_COLORS = {
    0: ['RED', 'VIOLET'],
    1: ['GREEN'],
    2: ['RED'],
    3: ['GREEN'],
    4: ['RED'],
    5: ['GREEN', 'VIOLET'],
    6: ['RED'],
    7: ['GREEN'],
    8: ['RED'],
    9: ['GREEN'],
}

# Default payout table
DEFAULT_PAYOUTS = {
    'number': Decimal('9.00'),      # Exact number: 9x
    'color_red': Decimal('2.00'),   # Red: 2x
    'color_green': Decimal('2.00'), # Green: 2x
    'color_violet': Decimal('4.50'),# Violet: 4.5x
    'big': Decimal('2.00'),         # Big (5-9): 2x
    'small': Decimal('2.00'),       # Small (0-4): 2x
}

DEFAULT_MIN_BET = Decimal('1.00')
DEFAULT_MAX_BET = Decimal('500.00')


def _generate_outcome(room_id: str, version: int) -> int:
    """
    Generate a provably fair outcome (0-9) using hash of room_id + version.
    """
    seed = f"{room_id}:{version}:wingo_outcome"
    hash_hex = hashlib.sha256(seed.encode()).hexdigest()
    # Use first 4 hex chars for outcome
    h = int(hash_hex[:4], 16)
    return h % 10


def _get_payout_multiplier(prediction_type: str, prediction_value: str, outcome: int, config: dict) -> Decimal:
    """
    Calculate payout multiplier for a bet given the outcome.
    Returns 0 if bet lost, multiplier if won.
    """
    payouts = config.get('payouts', DEFAULT_PAYOUTS)
    outcome_colors = NUMBER_COLORS.get(outcome, [])

    if prediction_type == 'number':
        if int(prediction_value) == outcome:
            return Decimal(str(payouts.get('number', DEFAULT_PAYOUTS['number'])))
        return Decimal('0')

    elif prediction_type == 'color':
        color = prediction_value.upper()
        if color in outcome_colors:
            key = f'color_{color.lower()}'
            return Decimal(str(payouts.get(key, Decimal('2.00'))))
        return Decimal('0')

    elif prediction_type == 'big_small':
        value = prediction_value.upper()
        if value == 'BIG' and outcome >= 5:
            return Decimal(str(payouts.get('big', DEFAULT_PAYOUTS['big'])))
        elif value == 'SMALL' and outcome < 5:
            return Decimal(str(payouts.get('small', DEFAULT_PAYOUTS['small'])))
        return Decimal('0')

    return Decimal('0')


def initial_state(room, config: dict) -> dict:
    """
    Build initial Wingo game state. Starts in 'betting' phase.
    """
    players = list(
        room.players.order_by('position').values_list('user_id', flat=True)
    )

    return {
        'phase': 'betting',
        'round_number': 1,
        'outcome': None,
        'outcome_color': None,
        'bets': [],
        'players': [str(uid) for uid in players],
        'round_id': str(room.id),
        'winner_id': None,
        'config': {
            'min_bet': str(config.get('min_bet', DEFAULT_MIN_BET)),
            'max_bet': str(config.get('max_bet', DEFAULT_MAX_BET)),
            'payouts': {k: str(v) for k, v in (config.get('payouts') or DEFAULT_PAYOUTS).items()},
            'round_duration_seconds': config.get('round_duration_seconds', 60),
        },
    }


def apply_action(state: dict, user_id: str, action: dict, room_id: str, version: int) -> dict:
    """
    Apply an action to the Wingo game state.

    Actions:
    - place_bet: Player places a prediction bet.
    - lock: Server locks the betting window.
    - resolve: Server generates outcome and settles bets.
    """
    state = copy.deepcopy(state)
    user_id = str(user_id)
    action_type = action.get('action')
    phase = state.get('phase', 'betting')

    if phase == 'finished' or phase == 'resolved':
        raise ValueError('Round is already finished')

    if action_type == 'place_bet':
        return _handle_place_bet(state, user_id, action)
    elif action_type == 'lock':
        return _handle_lock(state)
    elif action_type == 'resolve':
        return _handle_resolve(state, room_id, version)
    else:
        raise ValueError(f'Unknown action: {action_type}')


def _handle_place_bet(state: dict, user_id: str, action: dict) -> dict:
    """Place a prediction bet during the betting phase."""
    if state['phase'] != 'betting':
        raise ValueError('Bets can only be placed during betting phase')

    prediction_type = action.get('prediction_type')
    prediction_value = action.get('prediction_value')
    amount_str = action.get('amount')

    if not prediction_type or not prediction_value or not amount_str:
        raise ValueError('prediction_type, prediction_value, and amount are required')

    # Validate prediction type
    valid_types = ['number', 'color', 'big_small']
    if prediction_type not in valid_types:
        raise ValueError(f'prediction_type must be one of: {valid_types}')

    # Validate prediction value
    if prediction_type == 'number':
        try:
            num = int(prediction_value)
            if num < 0 or num > 9:
                raise ValueError('Number must be 0-9')
        except (ValueError, TypeError):
            raise ValueError('prediction_value must be a number 0-9')
    elif prediction_type == 'color':
        if prediction_value.upper() not in ['RED', 'GREEN', 'VIOLET']:
            raise ValueError('Color must be RED, GREEN, or VIOLET')
    elif prediction_type == 'big_small':
        if prediction_value.upper() not in ['BIG', 'SMALL']:
            raise ValueError('Value must be BIG or SMALL')

    # Validate amount
    amount = Decimal(str(amount_str))
    min_bet = Decimal(state['config']['min_bet'])
    max_bet = Decimal(state['config']['max_bet'])
    if amount < min_bet or amount > max_bet:
        raise ValueError(f'Bet must be between {min_bet} and {max_bet}')

    # Check duplicate bet from same user with same prediction
    for bet in state['bets']:
        if (bet['user_id'] == user_id and
                bet['prediction_type'] == prediction_type and
                bet['prediction_value'] == str(prediction_value)):
            raise ValueError('Duplicate bet on same prediction')

    state['bets'].append({
        'user_id': user_id,
        'amount': str(amount),
        'prediction_type': prediction_type,
        'prediction_value': str(prediction_value),
        'won': None,
        'payout': None,
    })

    return state


def _handle_lock(state: dict) -> dict:
    """Lock the betting window (server-driven)."""
    if state['phase'] != 'betting':
        raise ValueError('Can only lock from betting phase')

    state['phase'] = 'locked'
    return state


def _handle_resolve(state: dict, room_id: str, version: int) -> dict:
    """Generate outcome and settle all bets (server-driven)."""
    if state['phase'] not in ('locked', 'betting'):
        raise ValueError('Can only resolve from locked or betting phase')

    # Generate outcome
    outcome = _generate_outcome(room_id, version)
    outcome_colors = NUMBER_COLORS.get(outcome, [])

    state['outcome'] = outcome
    state['outcome_color'] = outcome_colors[0] if outcome_colors else None
    state['phase'] = 'resolved'

    # Settle bets
    config = state.get('config', {})
    for bet in state['bets']:
        multiplier = _get_payout_multiplier(
            bet['prediction_type'],
            bet['prediction_value'],
            outcome,
            config,
        )
        amount = Decimal(bet['amount'])
        if multiplier > 0:
            payout = (amount * multiplier).quantize(Decimal('0.01'))
            bet['won'] = True
            bet['payout'] = str(payout)
        else:
            bet['won'] = False
            bet['payout'] = '0.00'

    # Mark round as finished
    state['winner_id'] = 'WINGO_RESOLVED'
    state['phase'] = 'finished'
    return state


def game_kind() -> str:
    return 'WINGO'


def default_config() -> dict:
    return {
        'min_bet': str(DEFAULT_MIN_BET),
        'max_bet': str(DEFAULT_MAX_BET),
        'payouts': {k: str(v) for k, v in DEFAULT_PAYOUTS.items()},
        'round_duration_seconds': 60,
    }


def is_finished(state: dict) -> bool:
    return state.get('phase') == 'finished'


def get_winners(state: dict) -> list:
    """Return list of winner dicts for players who won bets."""
    if not is_finished(state):
        return []
    winners = []
    for bet in state.get('bets', []):
        if bet.get('won') and bet.get('payout') and Decimal(bet['payout']) > 0:
            winners.append({
                'user_id': bet['user_id'],
                'result': 'WON',
                'payout': Decimal(bet['payout']),
            })
    return winners


def get_public_state(state: dict) -> dict:
    """Wingo has no secrets to hide; return full state."""
    import copy
    return copy.deepcopy(state)


def validate_config(config: dict) -> list:
    errors = []
    if 'min_bet' in config and 'max_bet' in config:
        if Decimal(str(config['min_bet'])) >= Decimal(str(config['max_bet'])):
            errors.append('min_bet must be less than max_bet')
    dur = config.get('round_duration_seconds', 60)
    if dur < 5 or dur > 600:
        errors.append('round_duration_seconds must be between 5 and 600')
    return errors


def validate_bet(state: dict, user_id: str, amount: Decimal, action: dict):
    if state.get('phase') != 'betting':
        return 'Bets can only be placed during betting phase'
    min_bet = Decimal(state.get('config', {}).get('min_bet', '1.00'))
    max_bet = Decimal(state.get('config', {}).get('max_bet', '500.00'))
    if amount < min_bet or amount > max_bet:
        return f'Bet must be between {min_bet} and {max_bet}'
    return None
