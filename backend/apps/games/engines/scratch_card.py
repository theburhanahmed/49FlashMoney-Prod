"""
Scratch Card game engine for 49FlashMoney.

Single-player grid game. The player places a bet, then reveals cells one by
one. Cells hide fixed prize multipliers (2x, 5x, 10x), a single "bust" cell
that ends the round with zero payout, and blank cells that award nothing but
keep the round alive.

Prizes are accumulated into ``total_prize`` (net of the configured house edge).
The player may collect winnings at any time after revealing at least one safe
cell, or the round auto-collects once all non-bust cells are revealed.

State shape:
{
  "phase": "betting" | "scratching" | "finished",
  "grid_size": int,
  "cells": [
    {"value": "2x" | "5x" | "10x" | "bust" | "blank", "revealed": false},
    ...
  ],
  "revealed_indices": [int],
  "bet_amount": str,
  "total_prize": str,
  "user_id": str,
  "round_id": str,
  "winner_id": str | null,
  "config": {...},
}

Engine interface:
- initial_state(room, config) -> dict
- apply_action(state, user_id, action, room_id, version) -> dict

Actions:
- {"action": "place_bet", "amount": "10.00"}
- {"action": "scratch", "cell": 3}
- {"action": "collect"}
"""
import copy
import hashlib
from decimal import Decimal


DEFAULT_GRID_SIZE = 9
DEFAULT_CELL_VALUES = [
    "10x", "5x", "2x", "2x", "bust", "blank", "blank", "blank", "blank"
]
DEFAULT_MIN_BET = Decimal("1.00")
DEFAULT_MAX_BET = Decimal("500.00")
DEFAULT_HOUSE_EDGE = Decimal("0.05")

_VALID_CELL_VALUES = {"2x", "5x", "10x", "bust", "blank"}


def _generate_grid(room_id: str, version: int, cell_values: list) -> list:
    """
    Generate a deterministically shuffled scratch-card grid.

    The seed is ``room_id + version`` (same provably-fair pattern as the
    Mines engine). The returned list contains dicts with ``value`` and
    ``revealed`` keys.
    """
    seed = f"{room_id}:{version}:scratch_card_grid"
    values = list(cell_values)
    hash_bytes = hashlib.sha256(seed.encode()).digest()
    extended_seed = seed
    idx = 0

    for i in range(len(values) - 1, 0, -1):
        if idx + 4 > len(hash_bytes):
            extended_seed = extended_seed + ":ext"
            hash_bytes = hashlib.sha256(extended_seed.encode()).digest()
            idx = 0
        j = int.from_bytes(hash_bytes[idx:idx + 4], "big") % (i + 1)
        idx += 4
        values[i], values[j] = values[j], values[i]

    return [{"value": value, "revealed": False} for value in values]


def _parse_multiplier(cell_value: str):
    """Return the numeric multiplier for a prize cell, or None otherwise."""
    if cell_value.endswith("x"):
        return Decimal(cell_value[:-1])
    return None


def _all_non_bust_cells_revealed(state: dict) -> bool:
    """Return True if every non-bust cell has been revealed."""
    non_bust_indices = [
        i for i, cell in enumerate(state["cells"]) if cell["value"] != "bust"
    ]
    return len(non_bust_indices) > 0 and all(
        state["cells"][i]["revealed"] for i in non_bust_indices
    )


def _finish_with_collection(state: dict, user_id: str) -> dict:
    """Mark the round as finished with the player collecting total_prize."""
    state["phase"] = "finished"
    state["winner_id"] = user_id
    return state


def _finish_with_bust(state: dict) -> dict:
    """Mark the round as finished with zero payout after hitting a bust."""
    state["phase"] = "finished"
    state["total_prize"] = "0.00"
    state["winner_id"] = None
    return state


# ── Engine interface ──────────────────────────────────────────────────


def initial_state(room, config: dict) -> dict:
    """Build the initial Scratch Card game state. Starts in 'betting' phase."""
    players = list(
        room.players.order_by("position").values_list("user_id", flat=True)
    )
    user_id = str(players[0]) if players else ""
    grid_size = int(config.get("grid_size", DEFAULT_GRID_SIZE))
    cell_values = list(config.get("cell_values", DEFAULT_CELL_VALUES))

    return {
        "phase": "betting",
        "grid_size": grid_size,
        "cells": [],
        "revealed_indices": [],
        "bet_amount": "0.00",
        "total_prize": "0.00",
        "user_id": user_id,
        "players": [user_id],
        "round_id": str(room.id),
        "winner_id": None,
        "config": {
            "grid_size": grid_size,
            "cell_values": cell_values,
            "min_bet": str(config.get("min_bet", DEFAULT_MIN_BET)),
            "max_bet": str(config.get("max_bet", DEFAULT_MAX_BET)),
            "house_edge": str(config.get("house_edge", DEFAULT_HOUSE_EDGE)),
        },
    }


def apply_action(
    state: dict, user_id: str, action: dict, room_id: str, version: int
) -> dict:
    """Apply an action to the Scratch Card game state."""
    state = copy.deepcopy(state)
    user_id = str(user_id)
    action_type = action.get("action")
    phase = state.get("phase", "betting")

    if phase == "finished":
        raise ValueError("Round is already finished")

    if action_type == "place_bet":
        return _handle_place_bet(state, user_id, action, room_id, version)
    if action_type == "scratch":
        return _handle_scratch(state, user_id, action)
    if action_type == "collect":
        return _handle_collect(state, user_id)

    raise ValueError(f"Unknown action: {action_type}")


def _handle_place_bet(
    state: dict, user_id: str, action: dict, room_id: str, version: int
) -> dict:
    """Place a bet and generate the hidden scratch-card grid."""
    if state["phase"] != "betting":
        raise ValueError("Bet can only be placed during betting phase")

    if user_id != state.get("user_id", ""):
        raise ValueError("Not the player in this room")

    amount_str = action.get("amount")
    if not amount_str:
        raise ValueError("amount is required")

    amount = Decimal(str(amount_str))
    min_bet = Decimal(state["config"]["min_bet"])
    max_bet = Decimal(state["config"]["max_bet"])
    if amount < min_bet or amount > max_bet:
        raise ValueError(f"Bet must be between {min_bet} and {max_bet}")

    grid_size = state["grid_size"]
    cell_values = state["config"]["cell_values"]
    if len(cell_values) != grid_size:
        raise ValueError("Configured cell_values length does not match grid_size")

    cells = _generate_grid(room_id, version, cell_values)

    state["bet_amount"] = str(amount)
    state["cells"] = cells
    state["phase"] = "scratching"
    state["revealed_indices"] = []
    state["total_prize"] = "0.00"
    return state


def _handle_scratch(state: dict, user_id: str, action: dict) -> dict:
    """Reveal a cell. Bust ends the round; prizes accumulate; blanks continue."""
    if state["phase"] != "scratching":
        raise ValueError("Can only scratch during scratching phase")

    if user_id != state.get("user_id", ""):
        raise ValueError("Not the player in this room")

    cell = action.get("cell")
    if cell is None:
        raise ValueError("cell index is required")
    cell = int(cell)

    grid_size = state["grid_size"]
    if cell < 0 or cell >= grid_size:
        raise ValueError(f"cell must be between 0 and {grid_size - 1}")
    if cell in state["revealed_indices"]:
        raise ValueError("Cell already revealed")

    state["cells"][cell]["revealed"] = True
    state["revealed_indices"].append(cell)

    value = state["cells"][cell]["value"]

    if value == "bust":
        return _finish_with_bust(state)

    if value == "blank":
        if _all_non_bust_cells_revealed(state):
            return _finish_with_collection(state, user_id)
        return state

    # Prize cell
    multiplier = _parse_multiplier(value)
    if multiplier is None:
        raise ValueError(f"Invalid cell value: {value}")

    bet_amount = Decimal(state["bet_amount"])
    house_edge = Decimal(state["config"]["house_edge"])
    prize = (
        bet_amount * multiplier * (Decimal("1") - house_edge)
    ).quantize(Decimal("0.01"))

    total_prize = Decimal(state["total_prize"]) + prize
    state["total_prize"] = str(total_prize.quantize(Decimal("0.01")))

    if _all_non_bust_cells_revealed(state):
        return _finish_with_collection(state, user_id)

    return state


def _handle_collect(state: dict, user_id: str) -> dict:
    """Collect the current total_prize and end the round."""
    if state["phase"] != "scratching":
        raise ValueError("Can only collect during scratching phase")

    if user_id != state.get("user_id", ""):
        raise ValueError("Not the player in this room")

    if len(state["revealed_indices"]) == 0:
        raise ValueError("Must reveal at least one safe cell before collecting")

    return _finish_with_collection(state, user_id)


# ── ABC-compatible helpers ────────────────────────────────────────────


def game_kind() -> str:
    """Return the GameKind constant for this engine."""
    return "SCRATCH_CARD"


def default_config() -> dict:
    """Return the default configuration for a Scratch Card room."""
    return {
        "grid_size": DEFAULT_GRID_SIZE,
        "cell_values": list(DEFAULT_CELL_VALUES),
        "min_bet": str(DEFAULT_MIN_BET),
        "max_bet": str(DEFAULT_MAX_BET),
        "house_edge": str(DEFAULT_HOUSE_EDGE),
    }


def is_finished(state: dict) -> bool:
    """Return True when the round has been resolved."""
    return state.get("phase") == "finished"


def get_winners(state: dict) -> list:
    """Return the winner record(s) for a finished round, if any."""
    if not is_finished(state):
        return []

    winner_id = state.get("winner_id")
    if not winner_id:
        return []

    payout = Decimal(state.get("total_prize", "0.00"))
    if payout <= 0:
        return []

    return [{"user_id": winner_id, "result": "WON", "payout": payout}]


def get_public_state(state: dict) -> dict:
    """Return a client-safe copy of the state with unrevealed cell values hidden."""
    public = copy.deepcopy(state)
    cells = public.get("cells")
    if cells:
        public["cells"] = [
            {"value": cell["value"] if cell["revealed"] else None, "revealed": cell["revealed"]}
            for cell in cells
        ]
    return public


def validate_config(config: dict) -> list:
    """Validate a Scratch Card configuration. Returns a list of error strings."""
    errors = []

    grid_size = config.get("grid_size", DEFAULT_GRID_SIZE)
    if not isinstance(grid_size, int) or grid_size < 2:
        errors.append("grid_size must be an integer >= 2")

    cell_values = config.get("cell_values", DEFAULT_CELL_VALUES)
    if not isinstance(cell_values, list) or len(cell_values) != grid_size:
        errors.append("cell_values must be a list whose length equals grid_size")
    else:
        invalid = [v for v in cell_values if v not in _VALID_CELL_VALUES]
        if invalid:
            errors.append(
                f"cell_values contains invalid tokens: {sorted(set(invalid))}"
            )
        if not any(v.endswith("x") for v in cell_values):
            errors.append("cell_values must contain at least one prize cell")
        if not any(v != "bust" for v in cell_values):
            errors.append("cell_values must contain at least one non-bust cell")

    if "min_bet" in config and "max_bet" in config:
        min_bet = Decimal(str(config["min_bet"]))
        max_bet = Decimal(str(config["max_bet"]))
        if min_bet <= 0:
            errors.append("min_bet must be greater than 0")
        if max_bet <= 0:
            errors.append("max_bet must be greater than 0")
        if min_bet >= max_bet:
            errors.append("min_bet must be less than max_bet")

    try:
        house_edge = Decimal(str(config.get("house_edge", DEFAULT_HOUSE_EDGE)))
    except Exception:
        errors.append("house_edge must be a valid decimal")
    else:
        if not (Decimal("0") <= house_edge < Decimal("1")):
            errors.append("house_edge must be between 0 and 1")

    return errors


def validate_bet(state: dict, user_id: str, amount: Decimal, action: dict):
    """Pre-validate a bet before wallet debit."""

    if state.get("phase") != "betting":
        return f"Cannot place bet during {state.get('phase')} phase"

    if str(user_id) != state.get("user_id", ""):
        return "Not the player in this room"

    min_bet = Decimal(state.get("config", {}).get("min_bet", "1.00"))
    max_bet = Decimal(state.get("config", {}).get("max_bet", "500.00"))
    if amount < min_bet or amount > max_bet:
        return f"Bet must be between {min_bet} and {max_bet}"

    return None
