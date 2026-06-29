# 10_Game_Engine

## Purpose
This document defines the shared game engine for 49FlashMoney. It establishes the common lifecycle, rules, and interfaces that all games must use so the platform can support multiple game products without duplicating core logic.

## Scope
This specification covers the game lifecycle, common state transitions, player interaction model, wallet integration, result persistence, event publishing, admin controls, and the requirements that every game must satisfy.

## Goals
- Provide a reusable foundation for all games.
- Prevent games from reimplementing shared platform behavior.
- Standardize wallet, result, and history integration.
- Make every game auditable and testable.
- Support both real-time and turn-based game patterns.

## Engine Principles
- All games must extend the shared engine contract.
- Game-specific logic must remain isolated from platform services.
- The engine must integrate with wallet, ledger, notifications, analytics, and admin control.
- Every game result must be persisted.
- Every game action must be traceable.

## Engine Responsibilities
The shared engine must handle:
- Game registration and configuration.
- Round or session creation.
- Player bet validation.
- Wallet reservation or debit coordination.
- Outcome resolution.
- Payout calculation.
- Ledger posting.
- Event publishing.
- Game history storage.
- Admin visibility and controls.

## Common Game Lifecycle
### Draft
The game configuration exists but is not available to players.

### Enabled
The game is available for eligible users and active configuration.

### Maintenance
The game is temporarily unavailable for operational reasons.

### Paused
The game is disabled without deletion, often due to risk or business action.

### Archived
The game is no longer active but remains available for history and reporting.

## Round Lifecycle
A game round or session must support the following conceptual states:
- Created.
- Accepting bets.
- Locked.
- Resolving.
- Resolved.
- Paid out where applicable.
- Closed.

## Engine Inputs
The engine must accept:
- Game type.
- User identity.
- Wager amount.
- Configuration values.
- Player selections where applicable.
- Idempotency reference.
- Timing and eligibility context.

## Engine Outputs
The engine must produce:
- Validation result.
- Bet acceptance or rejection.
- Round or session record.
- Outcome data.
- Payout or loss result.
- Ledger references.
- Event stream updates.

## Bet Processing Rules
- Bets must be validated before acceptance.
- Bets must respect configured limits and user eligibility.
- Funds must be reserved or debited according to the game model.
- Duplicate submissions must be blocked by idempotency rules.

## Outcome Rules
- Outcomes must be deterministically generated or securely random depending on game design.
- The system must persist the outcome and any supporting data needed for audit.
- Payouts must be calculated from game rules and configuration.
- Outcome history must remain queryable.

## Wallet Integration Rules
- Every accepted bet must connect to the wallet and ledger.
- Winnings must create ledger credits.
- Losses must be represented through the bet debit or reservation settlement path.
- Reversals must use compensating entries where needed.

## Event Publishing
The engine must publish events for:
- Game creation.
- Bet accepted.
- Round started.
- Round closed.
- Outcome resolved.
- Payout completed.
- Game paused or resumed.

## Admin Requirements
The admin portal must support:
- Enabling or disabling games.
- Updating configuration values.
- Inspecting round history.
- Reviewing anomalies or disputes.
- Monitoring live or near-live game health.

## Analytics Requirements
The engine must expose data for:
- Bet counts.
- Win/loss ratios.
- RTP and payout performance.
- Participation by game type.
- Round timing and completion rates.

## Business Rules
- No game may bypass wallet or ledger integration.
- No game may be deployed without tests.
- No game may operate without auditability.
- Game-specific logic must not become a second platform layer.
- Every game must comply with the shared engine contract.

## Error Handling
- Invalid configuration must prevent activation.
- Invalid wagers must be rejected before processing.
- Game resolution failures must be recoverable or reviewable.
- Unfinished rounds must be visible to operations.

## Acceptance Criteria
- A shared engine contract is defined for all games.
- Game lifecycle and round lifecycle are explicit.
- Wallet, ledger, and event integration are standardized.
- Admin and analytics requirements are included.
- The engine can support both current and future games.

## Summary
The game engine is the reusable foundation of the platform’s entertainment layer. It ensures that new games can be launched consistently while preserving financial integrity, auditability, and operational control.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
