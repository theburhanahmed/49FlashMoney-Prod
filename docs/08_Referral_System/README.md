# 08_Referral_System

## Purpose
This document defines the referral system for 49FlashMoney. It covers referral code generation, attribution, reward rules, eligibility, fraud controls, and administrative management of referral campaigns.

## Scope
This specification includes referral links or codes, invite attribution, referral reward creation, campaign configuration, reward restrictions, and analytics related to acquisition and conversion.

## Goals
- Drive new user acquisition through existing users.
- Reward referrers according to configurable business rules.
- Prevent referral abuse and duplicate attribution.
- Support campaign-level control and reporting.
- Record referral rewards through the ledger.

## Referral Principles
- Referral rewards must be auditable.
- Referral logic must be configurable.
- Rewards must obey eligibility and anti-fraud rules.
- Referral attribution must be deterministic.
- Referral payouts must create ledger entries.

## Referral Model
Each eligible user may have a referral code or invite mechanism that can be shared with new users. The system must track the relationship between the referrer and the referred user and apply campaign rules when conditions are met.

## Core Components
- Referrer user.
- Referred user.
- Referral code or invite token.
- Campaign rules.
- Qualification events.
- Reward ledger entry.
- Analytics record.

## Attribution Rules
- Referral attribution must occur using a defined and consistent matching rule.
- Attribution must be tied to the first valid registration or campaign-specific event where applicable.
- A referral should not be reassigned after qualification unless explicitly supported by policy.
- Duplicate or conflicting attribution events must be rejected or resolved by rule.

## Reward Types
- Fixed bonus credit.
- Percentage cashback.
- Tiered reward.
- Milestone reward.
- Campaign-specific incentive.

## Reward Qualification Rules
Referral rewards may require one or more of the following conditions:
- The referred user completes registration.
- The referred user completes KYC.
- The referred user makes a first deposit.
- The referred user reaches a wagering threshold.
- The campaign remains active and the referral is not disqualified.

## Reward Posting Rules
- Referral rewards must only be posted when campaign conditions are satisfied.
- Rewards must be written to the ledger.
- The system must be able to trace each reward to the original campaign and referral relationship.
- Rewards may be credited immediately or after qualification, depending on campaign rules.

## Fraud Controls
- Referral abuse detection must be supported.
- Duplicate account patterns must be reviewable.
- Self-referral prevention must be enforceable.
- Suspicious reward patterns must be flagged for review.
- High-risk campaigns must have limits and monitoring.

## Campaign Configuration
The admin portal must support:
- Creating and editing campaigns.
- Defining reward amounts and conditions.
- Setting campaign start and end dates.
- Enabling or disabling campaigns.
- Viewing campaign performance metrics.

## Analytics Requirements
The system must measure:
- Referral code usage.
- Registration conversion.
- KYC conversion.
- First deposit conversion.
- Reward issuance totals.
- Fraud or rejection counts.

## Business Rules
- A referral reward may not be issued without a qualifying rule being met.
- Referral rewards must be auditable like any other financial event.
- Referral campaigns must have start and end boundaries.
- Campaign logic must be configurable without code changes where possible.
- Referral data must be visible in both user history and admin reporting.

## Admin Requirements
The admin portal must support:
- Referral campaign management.
- Referral user tree or relationship lookup.
- Reward history review.
- Fraud review and override actions.
- Analytics by campaign, cohort, and channel.

## Error Handling
- Invalid referral codes must be rejected gracefully.
- Duplicate attribution attempts must be handled deterministically.
- Disqualified users must not receive rewards.
- Campaign expiration must stop reward issuance.

## Acceptance Criteria
- Referral attribution is tracked reliably.
- Rewards are issued only when campaign rules are satisfied.
- All rewards are recorded in the ledger.
- Referral campaigns are configurable and measurable.
- The system supports abuse review and operational oversight.

## Summary
The referral system is an acquisition and growth mechanism that must remain tightly controlled. It should drive user growth while preserving ledger integrity, campaign flexibility, and anti-fraud protections.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
