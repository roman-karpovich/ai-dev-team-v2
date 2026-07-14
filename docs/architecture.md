# Architecture

## Decision

v2 is a greenfield rebuild. It does not depend on the v1 implementation and
does not preserve v1's prompt workflow or repository shape.

The architecture retains only concepts that remain valuable with stronger
models:

- independent judgment paths where correlated error matters;
- deterministic control-plane decisions;
- typed evidence with claim-specific admissibility;
- receipts for identity, inputs, execution policy, and cost;
- durable, corruption-evident state;
- bounded LIGHT and HEAVY risk profiles;
- explicit human decisions only at genuine forks.

## Execution strategy

v2 follows **portable assurance, native execution**. A provider-neutral kernel
owns deterministic state, evidence validity, checkpoints, budgets, and release
gates. A replaceable native backend receives a bounded work order and remains
free to use its strongest runtime mechanisms, such as native subagents, review,
skills, or dynamic workflows.

The portable boundary standardizes work orders, results, capability claims,
and receipts. It does not standardize internal agent topology or reduce every
runtime to a one-shot model call. Provider sessions and transcripts are
optional execution caches rather than canonical project state. Provider or
model selection is role-specific and evaluation-driven.

See
[ADR 0002](adr/0002-portable-assurance-native-execution.md) for the proposed
responsibility boundary and staged validation.

## First vertical slice

VERIFY is the first slice. It evaluates evidence for load-bearing claims and
produces:

- workflow completion status;
- canonical confirmed findings;
- noncanonical candidate dispositions;
- coverage and degradation records;
- a separate release recommendation.

Completion is not a safety claim, and agreement between models is metadata
rather than proof.

## Planned production boundaries

These boundaries become implementation packages only after readiness GO:

- core: state machine, dispatch, and terminal derivation;
- contracts: schemas, policy, and validation;
- platform: snapshot and sandbox;
- adapters: native execution backends with capability negotiation and portable
  work-order, result, and invocation-receipt boundaries;
- evidence: claims and adjudication validation;
- ledger: journal, seal, and lifecycle.

Do not split them further before implementation pressure justifies it.

## Current phase

The repository currently owns readiness evidence, not a production engine:

1. Re-author self-contained public contracts.
2. Complete schema, snapshot, and sandbox spikes.
3. Collect adapter conformance evidence.
4. Materialize evaluation prerequisites and an aligned frozen-v1 baseline.
5. Run the readiness gate.
