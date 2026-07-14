# ADR 0001: Greenfield rebuild

- Status: Accepted
- Date: 2026-07-13

## Context

v1 accumulated prompt scaffolding, coupled workflows, repository-specific
assumptions, and a slow monolithic regression harness. Stronger coding models
reduce the value of behavioral prompt scaffolding but do not eliminate the need
for independent evidence, deterministic execution, receipts, or durable state.

## Decision

Build v2 in an independent repository without importing v1 implementation
artifacts.

v1 is used only as:

- a frozen black-box comparison baseline;
- a rollback target;
- evidence of successful concepts and historical failure classes.

Every v2 contract and expectation is re-derived in this repository. Production
implementation remains blocked behind the readiness gate.

## Consequences

- There is no source-level compatibility requirement with v1.
- Migration is coexistence followed by evidence-based promotion, not an in-place
  upgrade.
- Early work may look slower because contracts and empirical spikes precede the
  engine.
- Shared-oracle errors cannot be excused by legacy tests passing.

## Rejected alternatives

- Forking v1 and deleting pieces: rejected because inherited coupling would
  remain the default architecture.
- Copying the previous experimental runner: rejected because its expectations
  and implementation were co-designed.
- Starting the production engine immediately: rejected until readiness evidence
  exists.

