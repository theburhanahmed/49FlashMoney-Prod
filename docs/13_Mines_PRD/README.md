# 13_Mines_PRD

## Purpose
This document defines the Mines game specification for 49FlashMoney. It describes the grid-based play model, mine placement, progression rules, cash-out behavior, and administrative configuration requirements.

## Scope
This specification covers game setup, tile selection, mine resolution, multiplier progression, payout behavior, history persistence, and shared engine integration.

## Game Overview
Mines is a grid game where a player opens safe tiles to increase winnings while avoiding hidden mines. The player may cash out at any point before hitting a mine, locking in the current multiplier or payout amount.

## Goals
- Deliver a simple but strategic game loop.
- Support configurable board size and mine count.
- Ensure each action is auditable and persisted.
- Integrate with the shared game engine and wallet ledger.

## Game Principles
- Mines must use the shared engine contract.
- Each player action must update game state explicitly.
- Tile outcomes must be stored and auditable.
- Cash-out behavior must be clear and idempotent.
- Wallet and ledger integration must be reliable.

## Game Lifecycle
### Draft
The game is configured but not available.

### Enabled
The game is active for eligible users.

### Maintenance
The game is temporarily disabled.

### Paused
The game is suspended without removal.

### Archived
The game is inactive but retained for reporting.

## Round Lifecycle
- Created.
- Bet accepted.
- Board initialized.
- Tile selection in progress.
- Cash-out available.
- Mine hit or cash-out executed.
- Round resolved.
- Payout completed where applicable.
- Closed.

## Player Actions
- Start a round with a wager.
- Select tiles one by one.
- View increasing multiplier or reward progression.
- Cash out at any safe point.
- Review past rounds.

## Game Rules
- A wager must be accepted before board play begins.
- Each tile selection must resolve to safe or mine.
- Safe selections increase the multiplier or payout path.
- Hitting a mine ends the round immediately.
- Cash-out must be available before a mine is hit.

## Outcome Rules
- Mine placement must be stored for audit and round integrity.
- Safe tile selections and mine hits must be persisted.
- The final payout must reflect the number of successful selections and any configured multiplier table.
- Duplicate actions must be rejected by idempotency or state checks.

## Wallet and Ledger Rules
- The wager must be reserved or debited when the round starts.
- Cash-out must create a winnings ledger credit.
- Mine loss settlement must follow wallet policy.
- Reversals must use compensating entries only.

## Configurable Parameters
The admin portal must support:
- Board size.
- Mine count.
- Wager limits.
- Multiplier table or payout curve.
- Enable/disable status.
- Maintenance mode.

## Admin Requirements
The admin portal must support:
- Configuring board and payout parameters.
- Monitoring active rounds.
- Viewing tile history and round outcomes.
- Adjusting game state.
- Reviewing audit logs for configuration changes.

## Analytics Requirements
The system must track:
- Round starts.
- Tile selection depth.
- Cash-out frequency.
- Mine hit rate.
- Average multiplier achieved.
- Revenue and RTP performance.

## Business Rules
- Mines must never bypass the shared engine.
- Every tile action must be traceable.
- Every wager and payout must map to ledger entries.
- Game state must remain consistent across retries and reconnects.
- Configuration changes must be logged.

## Error Handling
- Invalid tile selections must be rejected.
- Actions after round end must fail cleanly.
- Resolution errors must not create duplicate payouts.
- Unresolved rounds must be visible to operations.

## Acceptance Criteria
- Mines supports wagered board-based play.
- Tile selection and cash-out flow are explicit.
- Wallet and ledger integration is correct.
- Admin controls and analytics are available.
- The game conforms to the shared engine contract.

## Summary
Mines is a compact strategic game built on safe tile progression and optional cash-out. It must remain auditable, configurable, and fully integrated with the shared platform engine.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
