# 25_Roadmap

## Purpose
This document defines the high-level roadmap for 49FlashMoney. It outlines the major delivery phases needed to evolve the platform from its current foundation into a modular real-money gaming platform.

## Scope
This roadmap covers foundational platform work, core financial systems, initial game delivery, operational tooling, growth systems, and later expansion phases.

## Roadmap Principles
- Build the platform foundation before scaling games.
- Prioritize financial integrity and operational control.
- Deliver reusable systems before game-specific features.
- Sequence work to reduce dependency risk.
- Keep the roadmap flexible enough to adapt to business and regulatory needs.

## Phase 1: Platform Foundation
Focus areas:
- Authentication and KYC.
- Wallet and ledger.
- Payments.
- Admin portal basics.
- Core analytics and audit logging.
- API and database standards.
- Security and DevOps foundations.

## Phase 2: Lottery-First Delivery
Focus areas:
- Lottery product implementation.
- Ticket purchase and draw flow.
- Winner selection and prize settlement.
- Lottery admin controls.
- Reporting and reconciliation.

## Phase 3: Shared Game Engine
Focus areas:
- Generalize game lifecycle rules.
- Standardize bet, resolution, and payout handling.
- Add real-time event support.
- Make new games plug into the shared engine.

## Phase 4: Live and Instant Games
Focus areas:
- Aviator.
- Wingo.
- Mines.
- Scratch Cards.
- Slots.
- Additional games as approved.

## Phase 5: Loyalty and Growth
Focus areas:
- Referral optimization.
- Promotion engine.
- VIP tiers and benefits.
- Retention campaigns.
- Campaign analytics.

## Phase 6: Operational Maturity
Focus areas:
- Advanced dashboards.
- Fraud and risk controls.
- Support workflows.
- Better reconciliation tools.
- Release automation and observability improvements.

## Phase 7: Scale and Expansion
Focus areas:
- More games and game variants.
- Performance scaling.
- Expanded reporting.
- Jurisdiction-specific configuration where permitted.
- Ongoing product refinement.

## Delivery Priorities
The earliest priorities should be:
1. Financial integrity.
2. KYC and access control.
3. Payment reliability.
4. Ledger and reconciliation.
5. Admin oversight.
6. Lottery delivery.
7. Game engine reuse.

## Dependencies
The roadmap depends on:
- Product vision.
- Business requirements.
- Wallet and payment architecture.
- Game engine contract.
- Security, DevOps, and testing foundations.

## Business Rules
- Platform foundations must be completed before expansion.
- New games must use the shared engine.
- Money movement features must not ship without ledger coverage.
- Operational tooling must keep pace with product growth.

## Acceptance Criteria
- The roadmap is organized into phased delivery blocks.
- Foundational work is prioritized ahead of game expansion.
- The roadmap reflects the platform’s architecture and product direction.
- The plan supports both near-term implementation and longer-term growth.

## Summary
The roadmap turns the PRD suite into a delivery sequence. It helps align teams on what must be built first, what can be reused, and how the platform should evolve over time.

## Related Artifacts
- api/api_contract.yaml
- db/db_schema.md
- diagrams/state_machine.md
- diagrams/sequence_diagram.md
- tests/test_plan.md
