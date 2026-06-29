# 20_Database_Design

## Purpose
This document defines the database design requirements for 49FlashMoney. It establishes the structure, integrity, and operational rules for the relational data model that supports the platform.

## Scope
This specification covers schema design, relational integrity, indexes, audit fields, transaction handling, and the storage model for wallets, payments, games, admin actions, and analytics-supporting entities.

## Goals
- Keep data consistent and auditable.
- Support high-integrity financial operations.
- Make reporting and reconciliation possible.
- Preserve historical game and admin records.
- Keep the database aligned with application services.

## Database Principles
- Use PostgreSQL as the primary system of record.
- Model financial history with an immutable ledger.
- Avoid direct edits to derived balances.
- Use foreign keys and constraints to preserve integrity.
- Store audit metadata on important entities.

## Core Data Domains
### Identity and Access
Users, roles, permissions, verification status, account status, and audit fields.

### Wallet and Ledger
Wallet views, ledger entries, reservations, reversals, and balance state references.

### Payments
Deposits, withdrawals, provider references, state transitions, and settlement history.

### Games
Game configurations, rounds, outcomes, tickets, bets, and game-specific histories.

### Promotions and Referrals
Campaigns, referral links, reward issuance, VIP tiers, and eligibility records.

### Admin and Audit
Admin accounts, actions, notes, support cases, and system logs.

### Analytics Support
Event tables or reporting-friendly records that can support aggregation without violating source-of-truth rules.

## Design Rules
- Use normalized tables for core business entities.
- Use denormalized or cached fields only where necessary for performance.
- Store timestamps in a consistent format.
- Use explicit status fields for workflow state.
- Use stable identifiers for all externally referenced objects.

## Ledger Design Requirements
The ledger must be modeled as append-only records. The schema must support:
- Entry type.
- Debit or credit direction.
- Amount.
- Currency.
- Source reference.
- Idempotency key.
- Actor or system reference.
- Created timestamp.
- Audit context.

## Transaction Integrity Requirements
- Money movement rows must be written atomically.
- Related state changes must be committed together.
- Reversal or adjustment data must preserve original history.
- Concurrent updates must not corrupt balance state.

## Indexing Requirements
The database must include indexes for:
- User lookup.
- Ledger and payment history.
- Game round and ticket history.
- Status fields for workflow queues.
- Time-based reporting queries.

## Constraint Requirements
- Unique constraints for idempotency-sensitive records.
- Foreign keys for all relationship integrity.
- Check constraints for valid enumerated states or amounts where appropriate.
- Not-null constraints for critical audit and ownership fields.

## Audit Field Requirements
Important tables should include:
- Created at.
- Updated at.
- Created by or source.
- Updated by or source.
- Audit reason where required.

## Reconciliation Requirements
The schema must support comparing ledger totals, payment statuses, and admin actions against external records. Historical states must be retained long enough to support investigation and finance review.

## Data Retention Requirements
- Keep financial and audit data according to policy.
- Retain records needed for compliance and dispute handling.
- Archive or partition data only when it does not compromise traceability.

## Business Rules
- No business process may rely on an untracked database write for money movement.
- Derived balances must be recalculable from ledger history.
- Admin changes must be identifiable in the data model.
- Game history must remain queryable for reporting and disputes.

## Acceptance Criteria
- The schema supports the wallet-ledger model.
- The schema preserves financial and operational history.
- Constraints and indexes are defined to protect integrity and performance.
- The database design can support payments, games, admin, and analytics.

## Summary
The database design is the structural foundation of the platform. It must preserve integrity, support auditing and reconciliation, and provide a reliable base for all application services.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
