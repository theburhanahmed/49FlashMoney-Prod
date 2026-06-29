# 17_Admin_Portal

## Purpose
This document defines the admin portal requirements for 49FlashMoney. It covers the operational surface used by internal teams to manage users, financial flows, games, promotions, support cases, analytics, and configuration.

## Scope
This specification includes roles, permissions, modules, workflows, audit logging, and the administrative controls required to safely operate the platform.

## Goals
- Provide full operational control without direct database access.
- Make sensitive actions explicit, auditable, and permissioned.
- Support finance, operations, support, compliance, and product workflows.
- Surface platform health and business data clearly.
- Keep high-risk actions protected and reviewable.

## Portal Principles
- Admin actions must be role-based.
- Every admin action must be logged.
- High-risk actions must require stricter permissions.
- Operational workflows must be fast and searchable.
- The portal must reflect actual system state, not inferred state alone.

## Roles
The portal should support at minimum:
- Super admin.
- Operations admin.
- Finance admin.
- Support agent.
- Compliance reviewer.
- Read-only analyst.

## Core Modules
### User Management
Search, view, restrict, block, verify, and annotate user accounts.

### Wallet and Ledger
Inspect balances, entries, adjustments, and reconciliation data.

### Payments
Review deposits, withdrawals, payment providers, and exception queues.

### Games
Manage enabled state, configurations, and round or outcome history.

### Promotions and VIP
Create and manage campaigns, tiers, eligibility, and reward logic.

### Referrals
Inspect referral relationships, rewards, and abuse signals.

### Analytics
View KPIs, cohorts, revenue, retention, and operational metrics.

### Audit Logs
Inspect admin actions and system events.

### Feature Flags and Configuration
Toggle operational settings safely and with traceability.

### Support Cases
Review account issues, disputes, and escalation workflows.

## Permission Rules
- Permissions must be scoped by role.
- Sensitive financial and compliance actions must require elevated access.
- Read-only users must not perform destructive actions.
- Action visibility must match permission level.
- Permission failures must be explicit and logged.

## Workflow Requirements
The portal must support:
- Search and filter across users, payments, tickets, draws, and ledgers.
- Detail views for accounts and financial records.
- Review queues for withdrawals, disputes, and suspicious activity.
- Controlled approval and rejection flows.
- Audit trails for every decision.

## Financial Controls
The portal must support:
- Ledger browsing and filtering.
- Manual adjustments with reason codes.
- Withdrawal approval or rejection where policy allows.
- Reconciliation review.
- Payment exception handling.

## Game Controls
The portal must support:
- Enabling and disabling games.
- Adjusting configuration values.
- Starting or closing draws or sessions where appropriate.
- Monitoring live game status.
- Reviewing game history and anomalies.

## Compliance Controls
The portal must support:
- KYC review.
- Account restriction or blocking.
- Audit history review.
- Risk flag management.
- Record retention consistent with policy.

## Audit Logging Requirements
Each administrative event must store:
- Actor.
- Action.
- Target entity.
- Timestamp.
- Before and after values where relevant.
- Reason or comment where required.

## Error Handling
- Unauthorized actions must fail clearly.
- Invalid state transitions must be blocked.
- Conflicting edits must be visible to the operator.
- High-risk actions must require confirmation and logging.

## UI Requirements
- Tables and filters for operational review.
- Detail panels for user, payment, and game records.
- Confirmation dialogs for destructive actions.
- Clear state indicators and timestamps.
- Fast navigation between linked records.

## Metrics and Monitoring
The portal must surface:
- Active users.
- Payment completion rates.
- Withdrawal queues.
- Game performance.
- Revenue and RTP.
- Support and compliance case volume.

## Acceptance Criteria
- The portal provides role-based operational control.
- Every admin action is auditable.
- Financial, game, and compliance workflows are supported.
- The portal can be used without direct database access.
- The interface reflects the platform’s actual state and permissions.

## Summary
The admin portal is the platform’s operational command center. It must make day-to-day management efficient while preserving strict controls, auditability, and safety for high-risk actions.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
