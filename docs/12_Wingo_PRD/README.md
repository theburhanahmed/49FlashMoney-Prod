# 12_Wingo_PRD

## Purpose
This document defines the Wingo game specification for 49FlashMoney. It describes the time-based prediction model, round scheduling, player choices, resolution behavior, and administrative control requirements.

## Scope
This specification covers Wingo rounds, betting windows, outcome selection, history persistence, payout logic, admin configuration, and integration with the shared game engine.

## Game Overview
Wingo is a round-based prediction game where players place bets on predefined outcomes before a round closes. Once the betting window ends, the round resolves and payouts are calculated according to the configured rules.

## Goals
- Deliver a simple and repeatable prediction game.
- Support configurable round timing and payout tables.
- Ensure outcomes are auditable and persisted.
- Integrate cleanly with the shared game engine and wallet ledger.

## Game Principles
- Wingo must use the shared engine contract.
- Round timing must be explicit and consistent.
- Bets and payouts must be recorded in the ledger.
- Outcome history must be available for players and admins.
- Game configuration must be managed centrally.

## Game Lifecycle
### Draft
Configuration is present but not active.

### Enabled
The game is available for eligible users.

### Maintenance
The game is temporarily unavailable.

### Paused
The game is disabled without deletion.

### Archived
The game remains visible only for history and reporting.

## Round Lifecycle
- Created.
- Accepting bets.
- Locked.
- Resolving.
- Resolved.
- Payout completed where applicable.
- Closed.

## Player Actions
- Select an outcome or bet option.
- Place a wager during the betting window.
- View round status and countdown.
- Inspect round history and results.

## Game Rules
- Bets must be placed before round lock.
- Each round must resolve to a valid outcome.
- Payouts must follow the configured payout table.
- Invalid or late bets must be rejected.
- Duplicate submissions must be prevented by idempotency.

## Outcome Rules
- Outcome generation must follow the configured game model.
- The outcome must be stored with the round record.
- The result must be available for reporting and dispute review.
- Any special resolution mode must be explicitly configured and auditable.

## Wallet and Ledger Rules
- Accepted bets must debit or reserve funds.
- Winning results must create ledger credits.
- Losing bets must be settled according to wallet policy.
- Reversals and corrections must use compensating entries.

## Configurable Parameters
The admin portal must support:
- Round duration.
- Betting window length.
- Available outcome options.
- Payout table.
- RTP or return configuration.
- Enable/disable and maintenance mode.

## Admin Requirements
The admin portal must support:
- Configuring rounds and payout settings.
- Monitoring live and historical rounds.
- Reviewing round outcomes.
- Adjusting status and maintenance settings.
- Viewing audit history of configuration changes.

## Analytics Requirements
The system must track:
- Bets per round.
- Outcome distribution.
- Win rate and payout ratio.
- Participation by time period.
- Round completion latency.
- Revenue and RTP performance.

## Business Rules
- Wingo must never bypass the shared engine.
- Every round must be traceable.
- Every bet and payout must map to ledger entries.
- Timing and outcome rules must be deterministic and auditable.
- Game changes must be logged.

## Error Handling
- Late or invalid bets must be rejected with a clear response.
- Round failures must be visible to operations.
- Outcome generation errors must not create partial financial effects.
- Recovery paths must preserve data integrity.

## Acceptance Criteria
- Wingo supports round-based prediction gameplay.
- Round lifecycle and payout behavior are explicit.
- Wallet and ledger integration is correct.
- Admin configuration and analytics are present.
- The game conforms to the shared engine contract.

## Summary
Wingo is a structured prediction game that depends on clean round management, transparent outcomes, and reliable ledger integration. It should behave predictably for players while remaining configurable for operations.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
