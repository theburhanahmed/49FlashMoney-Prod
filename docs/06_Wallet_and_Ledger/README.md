# 06_Wallet_and_Ledger

## Purpose
This document defines the wallet and ledger system for 49FlashMoney. It establishes the financial source of truth for all user balances, money movements, and reconciliation workflows.

## Scope
This specification covers wallet balance rules, immutable ledger entries, transaction types, ledger posting, reversals, adjustments, reconciliation support, and admin visibility. It also defines the foundational financial constraints that all payment and game systems must obey.

## Goals
- Maintain a trustworthy, auditable financial record.
- Prevent direct balance editing outside ledger logic.
- Support deposits, withdrawals, bets, winnings, bonuses, refunds, and adjustments.
- Make financial history easy to reconcile and inspect.
- Ensure every financial event is traceable end to end.

## Wallet Principles
- The wallet is derived from the ledger.
- The ledger is immutable.
- No balance change occurs without a ledger entry.
- All financial actions must be atomic and auditable.
- Ledger entries must be stored with enough detail for reconciliation and investigation.

## Financial Model
The platform must use a ledger-based wallet model where the current balance is calculated from recorded transactions rather than stored as a manually editable value. Operational tables may cache derived values for performance, but the ledger remains the authoritative source.

## Ledger Entry Types
The ledger must support at minimum the following entry types:
- Deposit credit.
- Withdrawal debit.
- Bet debit.
- Winnings credit.
- Bonus credit.
- Refund credit.
- Referral reward credit.
- Manual adjustment debit or credit.
- Reversal entry.

## Ledger Entry Requirements
Each ledger entry must include:
- Unique transaction identifier.
- User identifier.
- Entry type.
- Debit or credit direction.
- Amount.
- Currency.
- Before and after balance context where applicable.
- Reference to the originating business event.
- Idempotency key where relevant.
- Timestamp.
- Actor or source system.
- Audit metadata.

## Balance Rules
- Available balance must reflect settled, spendable funds.
- Pending or reserved funds must not be treated as spendable.
- Ledger entries must explain all deltas.
- Negative balances are not allowed unless explicitly modeled by policy and configuration, which should be avoided by default.

## Wallet States
### Active
The wallet can receive credits and process debits according to policy.

### Pending
Funds are awaiting final settlement or confirmation.

### Reserved
Funds are held for an active play or withdrawal flow.

### Restricted
Wallet actions are limited due to risk, compliance, or support status.

### Frozen
Wallet movements are blocked.

## Transaction Flow Rules
- A deposit becomes available only after the payment flow confirms it.
- A withdrawal must verify eligibility before funds are reserved or debited.
- A game bet must reserve or debit funds before play is resolved.
- A winnings payout must create a credit ledger entry.
- Refunds, bonuses, and manual adjustments must be explicitly categorized.

## Reconciliation Requirements
The wallet system must support:
- Daily or scheduled reconciliation.
- Cross-checking ledger totals against payment-provider records.
- Identifying mismatched or missing events.
- Investigating balance discrepancies.
- Generating operational reports for finance review.

## Immutability Rules
- Existing ledger entries must not be edited to change financial history.
- Correction must happen via compensating entries.
- Any reversal or adjustment must preserve the original source record.

## Reservation Rules
Where the platform requires temporary holds, the system must explicitly track reserved amounts separate from available balance. Reservation state must be reversible and auditable.

## Idempotency Rules
- Repeated financial requests with the same idempotency key must not create duplicate ledger effects.
- Idempotency must be enforced for payment-driven wallet changes and sensitive admin actions where appropriate.

## Admin Requirements
The admin portal must provide:
- Wallet history by user.
- Ledger entry search and filters.
- Balance visibility by derived and operational views.
- Adjustment tools with permission controls.
- Reconciliation and mismatch review capabilities.

## Business Rules
- No direct database update may bypass the ledger layer.
- Every financial movement must create an auditable record.
- Balance calculations must be deterministic.
- Adjustments require elevated permissions and explicit reason codes.
- Ledger entries must be queryable by time, type, user, and source reference.

## Error Handling
- Duplicate financial requests must resolve safely.
- Missing references must be rejected or placed in review depending on transaction type.
- Balance mismatches must be detectable by reconciliation jobs.
- Restricted wallet states must prevent spend or withdrawal actions.

## Dependencies
- Authentication and KYC.
- Payments.
- Game engine.
- Admin portal.
- Analytics and reporting.

## Acceptance Criteria
- Every money movement creates a ledger entry.
- Wallet balance can be derived from ledger history.
- Adjustments and reversals are auditable and controlled.
- The system supports reconciliation and discrepancy review.
- The wallet model can support all future payment and game flows.

## Summary
The wallet and ledger are the financial backbone of the platform. They enforce integrity, traceability, and accountability for every money movement, and they must remain the source of truth for all balance-related behavior.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
