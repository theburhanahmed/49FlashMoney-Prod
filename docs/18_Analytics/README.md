# 18_Analytics

## Purpose
This document defines the analytics requirements for 49FlashMoney. It covers the metrics, dimensions, reporting surfaces, and operational insights needed to manage growth, performance, and risk.

## Scope
This specification includes acquisition analytics, engagement analytics, financial analytics, game analytics, VIP analytics, fraud signals, and operational reporting.

## Goals
- Provide accurate business visibility.
- Support decision-making for operations, finance, and product.
- Track platform performance over time.
- Make financial and game activity measurable.
- Surface anomalies and trends quickly.

## Analytics Principles
- Metrics must be consistent and defined centrally.
- Financial reporting must align with the ledger.
- Game reporting must align with the engine and round history.
- Analytics must be actionable, not just descriptive.
- Access to sensitive analytics must be role-based.

## Core KPI Groups
### Acquisition
- Signups.
- Referral conversion.
- First deposit conversion.
- KYC completion rate.

### Engagement
- Daily active users.
- Weekly active users.
- Session frequency.
- Game participation rate.
- Retention by cohort.

### Monetization
- Deposits.
- Withdrawals.
- Gross gaming revenue.
- Net revenue.
- Average deposit value.
- Average wager value.

### Wallet and Ledger
- Ledger volume.
- Balance changes.
- Adjustment counts.
- Reconciliation mismatch rate.

### Game Performance
- Bets per game.
- Win rates.
- RTP or payout rate.
- Round completion rate.
- Cash-out rates where relevant.

### VIP and Promotions
- VIP tier progression.
- Promotion redemptions.
- Cashback issuance.
- Campaign cost and return.

### Support and Compliance
- Case volume.
- Blocked account count.
- KYC review volume.
- Fraud flags.
- Withdrawal review queue size.

## Reporting Requirements
The platform must support:
- Near-real-time operational dashboards.
- Daily business summaries.
- Finance reconciliation views.
- Game-level performance reports.
- Campaign and cohort analysis.
- Drill-down from aggregate to user or event level where permissions allow.

## Dimensions
Analytics should support segmentation by:
- Date and time window.
- User cohort.
- Game type.
- Promotion campaign.
- VIP tier.
- Payment method.
- Geographic or jurisdictional constraints where allowed.
- Account status.

## Data Integrity Rules
- Financial metrics must reconcile to ledger records.
- Game metrics must reconcile to persisted game history.
- Analytics pipelines must not invent or mutate source facts.
- Late-arriving events must be handled consistently.

## Operational Dashboards
The admin portal should provide dashboards for:
- Revenue and deposits.
- Withdrawals and pending queues.
- Game health and participation.
- Promotion performance.
- Risk and fraud alerts.
- Audit and compliance summaries.

## Alerting Requirements
The system should alert on:
- Failed deposit or withdrawal spikes.
- Reconciliation mismatches.
- Unusual win or payout patterns.
- Sudden drops in engagement.
- Game or payment outages.
- Excessive admin overrides.

## Business Rules
- KPI definitions must be stable and documented.
- Sensitive views must require appropriate access.
- Metrics based on money movement must match ledger truth.
- Game metrics must be traceable to stored round data.
- Campaign metrics must align with promotion records.

## Analytics Events
The platform should capture events for:
- Registration.
- KYC completion.
- Deposit initiated and confirmed.
- Withdrawal requested, approved, paid, or failed.
- Game round started and resolved.
- Bet placed.
- Payout credited.
- Promotion issued.
- VIP tier changed.
- Admin action performed.

## Acceptance Criteria
- Core KPIs are defined across acquisition, engagement, monetization, games, and risk.
- Metrics align with ledger and game history.
- The portal supports actionable operational dashboards.
- Analytics are available by key dimensions.
- Alerts are defined for the most important anomalies.

## Summary
Analytics gives the platform the visibility needed to grow responsibly and operate safely. It must be accurate, auditable, and directly tied to the underlying ledger, game, and administrative records.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
