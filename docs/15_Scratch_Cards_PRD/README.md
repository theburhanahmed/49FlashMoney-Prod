# 15_Scratch_Cards_PRD

## Purpose
This document defines the Scratch Cards game specification for 49FlashMoney. It describes the instant-win card model, reveal behavior, prize logic, and administrative controls.

## Scope
This specification covers card purchase, reveal flow, prize tiers, outcome storage, payout behavior, and integration with the shared game engine.

## Game Overview
Scratch Cards is an instant outcome game where a player purchases a card and reveals it to discover a prize or no-win result. The outcome must be determined and persisted according to the game rules and configuration.

## Goals
- Deliver a simple instant-win experience.
- Support configurable prize tiers and odds.
- Ensure every result is auditable.
- Integrate with the shared game engine and wallet ledger.

## Game Principles
- Scratch Cards must use the shared engine contract.
- Outcome determination must be stored and traceable.
- Wallet and ledger integration must be correct.
- The game must remain configurable and testable.
- Player reveal actions must be idempotent or state-safe.

## Game Lifecycle
### Draft
Configuration exists but the game is not available.

### Enabled
The game is available to eligible users.

### Maintenance
The game is temporarily unavailable.

### Paused
The game is disabled without deletion.

### Archived
Historical activity remains available for reporting.

## Card Lifecycle
- Created.
- Purchased.
- Locked.
- Reveal available.
- Revealed.
- Settled.
- Closed.

## Player Actions
- Buy a scratch card.
- Reveal the card.
- View prize result immediately.
- Review past card outcomes.

## Game Rules
- A card must be purchased before reveal.
- The outcome must be determined by the configured game rules.
- Reveal must not produce a different result after storage.
- Duplicate reveal attempts must not create duplicate payouts.
- Unavailable or expired cards must not be revealable.

## Outcome Rules
- The result must be persisted when the card is issued or revealed, depending on implementation model.
- Prize tier logic must be stored and auditable.
- Winning results must reference the relevant payout tier.
- Losing results must also be stored for completeness.

## Wallet and Ledger Rules
- Card purchase must debit the wallet or reserve funds according to the payment model.
- Winning reveals must create ledger credits.
- Non-winning reveals must settle according to wallet policy.
- Any correction must use compensating entries.

## Configurable Parameters
The admin portal must support:
- Card price.
- Prize tiers.
- Outcome odds or distribution.
- Availability windows.
- Enable/disable status.
- Maintenance mode.

## Admin Requirements
The admin portal must support:
- Configuring prize tables and odds.
- Enabling and disabling card batches or campaigns.
- Reviewing card issuance and reveal history.
- Monitoring payout totals.
- Auditing configuration changes.

## Analytics Requirements
The system must track:
- Card purchases.
- Reveal completion rate.
- Prize distribution.
- Payout totals.
- Revenue and RTP performance.
- Campaign engagement.

## Business Rules
- Scratch Cards must never bypass the shared engine.
- Every purchase and payout must map to ledger entries.
- Outcome generation and reveal behavior must be auditable.
- Game configuration changes must be logged.
- Cards must be recoverable in history and support review.

## Error Handling
- Invalid or expired reveals must be rejected.
- Duplicate reveal requests must not duplicate payouts.
- Outcome generation failures must not create partial financial effects.
- Operations must be able to inspect unresolved cards.

## Acceptance Criteria
- Scratch Cards supports instant reveal gameplay.
- Card lifecycle and payout rules are explicit.
- Wallet and ledger integration is correct.
- Admin controls and analytics are available.
- The game conforms to the shared engine contract.

## Summary
Scratch Cards is an instant outcome product designed for fast engagement and simple rewards. It must be auditable, configurable, and fully integrated with the platform ledger and game engine.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
