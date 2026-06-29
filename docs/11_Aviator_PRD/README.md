# 11_Aviator_PRD

## Purpose
This document defines the Aviator game specification for 49FlashMoney. It describes the gameplay model, round lifecycle, player actions, payout behavior, admin controls, and integration requirements with the shared game engine.

## Scope
This specification covers Aviator gameplay, cash-out behavior, round timing, multiplier progression, outcome resolution, history persistence, and reporting requirements.

## Game Overview
Aviator is a real-time multiplier game where a round starts at a low multiplier and increases until a crash point is reached. Players may cash out before the crash to lock in winnings; if they do not cash out in time, they lose the wager according to the game rules.

## Goals
- Deliver a fast, understandable live game.
- Provide a real-time event-driven experience.
- Ensure bet, cash-out, and payout actions are auditable.
- Keep the game fully integrated with the shared engine and ledger.

## Game Principles
- The game must use the shared engine contract.
- Round timing and outcome data must be persisted.
- Cash-out actions must be idempotent and traceable.
- Wallet debits and credits must follow ledger rules.
- Live events must be published to connected clients.

## Game Lifecycle
### Draft
Configuration exists but the game is not available.

### Enabled
The game is available to eligible users.

### Maintenance
The game is temporarily unavailable.

### Paused
The game is manually or automatically suspended.

### Archived
Historical rounds remain available, but the game is not active.

## Round Lifecycle
- Created.
- Accepting bets.
- In progress.
- Crash point approaching.
- Locked.
- Resolved.
- Paid out where applicable.
- Closed.

## Player Actions
- Place bet before round lock.
- View live multiplier progression.
- Cash out before crash.
- Review historical rounds and results.

## Game Rules
- Bets must be accepted before the round lock point.
- Cash-out must occur before the crash resolves.
- A successful cash-out must calculate payout from the multiplier at the time of exit.
- Late cash-out attempts must fail cleanly.
- Duplicate cash-out requests must be prevented by idempotency rules.

## Outcome Rules
- Each round must have a recorded crash point.
- The crash point must be stored for audit and history.
- The engine must preserve the relationship between bet amount, cash-out point, and payout.
- Failed or missed cash-outs must be represented clearly in history.

## Wallet and Ledger Rules
- The wager must be debited or reserved when the bet is accepted.
- Successful cash-outs must generate a winnings credit in the ledger.
- Lost wagers must be settled according to the wallet model.
- Any correction or reversal must be a compensating ledger entry.

## Real-Time Requirements
- The game must publish live multiplier updates.
- Cash-out confirmations must be delivered promptly.
- Round start, lock, crash, and resolution events must be emitted.
- Reconnection support should allow players to rejoin ongoing rounds without corrupting state.

## Configurable Parameters
The admin portal must support configuration of:
- Minimum and maximum bet.
- Round duration.
- Multiplier growth profile.
- Crash behavior parameters where policy allows.
- RTP or payout configuration.
- Maintenance and enable/disable status.

## Admin Requirements
The admin portal must support:
- Live round monitoring.
- Round history review.
- Game status management.
- RTP and limits configuration.
- Audit logs for manual changes.

## Analytics Requirements
The system must capture:
- Bets per round.
- Cash-out rates.
- Average cash-out multiplier.
- Round duration metrics.
- Payout and RTP performance.
- Player participation frequency.

## Business Rules
- Aviator must never bypass the shared engine.
- Every round must remain auditable.
- Every bet and payout must map to ledger entries.
- Cash-out timing must be precise and consistent.
- Game configuration changes must be logged.

## Error Handling
- Late cash-outs must fail without side effects.
- Invalid bets must be rejected before acceptance.
- Round resolution failures must be visible to operations.
- Reconnection mismatches must not duplicate state.

## Acceptance Criteria
- Aviator supports live rounds and cash-out behavior.
- Round lifecycle is explicit and auditable.
- Wallet and ledger integration is correct.
- Admin controls and analytics are present.
- The game conforms to the shared engine contract.

## Summary
Aviator is a real-time multiplier game built for fast, event-driven play. Its implementation must remain tightly aligned with the shared engine, ledger, and WebSocket-based live experience.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
