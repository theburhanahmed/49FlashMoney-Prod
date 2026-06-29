# 14_Lottery_PRD

## Purpose
This document defines the Lottery game specification for 49FlashMoney. It describes ticket purchase, draw scheduling, winner selection, prize handling, and administrative controls for the lottery product.

## Scope
This specification covers draw lifecycle, ticket lifecycle, participant management, result publication, prize settlement, admin draw operations, and shared engine integration.

## Game Overview
Lottery is a scheduled draw-based game where players purchase tickets for a given draw window and winners are selected according to the configured draw rules. Tickets, draw outcomes, and prize settlements must be stored and auditable.

## Goals
- Support scheduled draw gameplay.
- Make ticket and winner handling transparent.
- Ensure every purchase and payout is recorded in the ledger.
- Provide strong admin control over draw execution.
- Preserve historical draw data for reporting and dispute resolution.

## Game Principles
- Lottery must use the shared engine contract.
- Ticket purchase and draw settlement must be traceable.
- Draw results must be persisted and auditable.
- Wallet and ledger rules must be enforced.
- Administrative draw actions must be controlled and logged.

## Game Lifecycle
### Draft
The lottery is configured but not yet available.

### Enabled
Users can buy tickets for active draws.

### Closed
Ticket sales are no longer accepted for the draw.

### In Draw
The draw is being executed or verified.

### Settled
Winning results have been confirmed and prizes handled.

### Archived
Historical draws remain available for review.

## Draw Lifecycle
- Created.
- Open for tickets.
- Ticket sales locked.
- Draw initiated.
- Winner selection completed.
- Prize allocation recorded.
- Draw published.
- Closed.

## Player Actions
- View active lottery draws.
- Buy one or more tickets.
- Review ticket history.
- Check draw results and winnings.

## Game Rules
- Ticket sales must stop at the configured cutoff time.
- Each ticket must be uniquely identifiable.
- Draw execution must follow the configured rules.
- Winner selection must be auditable.
- Duplicate ticket purchases must be prevented by idempotency and business checks.

## Outcome Rules
- The draw outcome must be persisted with the draw record.
- Winner records must reference the relevant tickets.
- Prize allocations must be represented in the ledger.
- Unclaimed or rolled-over prize logic must be explicitly configured if supported.

## Wallet and Ledger Rules
- Ticket purchases must debit the wallet or reserve funds according to the payment model.
- Prize payouts must create ledger credits.
- Refunds, cancellations, or adjustments must be represented by compensating entries.
- Balance changes must always be auditable.

## Configurable Parameters
The admin portal must support:
- Ticket price.
- Draw schedule.
- Prize pool rules.
- Winner count or selection logic.
- Ticket cutoff time.
- Enable/disable status.

## Admin Requirements
The admin portal must support:
- Creating and editing draws.
- Opening and closing ticket sales.
- Initiating and verifying draws.
- Reviewing participants and winners.
- Publishing results and audit logs.

## Analytics Requirements
The system must track:
- Ticket sales volume.
- Participation by draw.
- Prize payout totals.
- Draw completion timing.
- Revenue and retention effects.
- Historical winner analysis.

## Business Rules
- Lottery must never bypass the shared engine.
- Every ticket purchase and prize payout must map to ledger entries.
- Draw results must be reproducible from stored records.
- Admin actions must be logged.
- Canceled or failed draws must be recoverable or clearly marked.

## Error Handling
- Invalid or late ticket purchases must be rejected.
- Draw failures must not produce partial payouts.
- Winner selection disputes must be traceable.
- Settlement issues must be visible to operations and finance.

## Acceptance Criteria
- Lottery supports scheduled draw play.
- Ticket lifecycle and draw lifecycle are explicit.
- Wallet and ledger integration is correct.
- Admin draw controls and analytics are available.
- The game conforms to the shared engine contract.

## Summary
Lottery is the platform’s scheduled draw product and requires precise ticket management, transparent draw execution, and complete financial traceability. It must fit cleanly into the shared platform engine and ledger model.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
