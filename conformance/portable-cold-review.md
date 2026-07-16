# Portable cold-review conformance exercise

- Status: Active; bundle validation slice implemented, backend runs pending
- Scope: Readiness evidence, not production orchestration

## Question

Can one provider-neutral cold-review work order be executed by both a
Codex-native and a Claude-native backend without suppressing their native
strengths, while producing comparable, inspectable, snapshot-bound receipts?

This exercise validates the execution boundary proposed by ADR 0002,
`Portable assurance, native execution`. It does not rank model quality or
qualify either path as epistemically independent.

The experimental bundle and gate contract is fixed in
`portable-cold-review-contract-v0.md`. It validates manually assembled evidence
without launching a backend or authorizing release. The remaining exercise is
to produce those artifacts through two qualified native paths.

## Fixed input

Use one small, public, immutable review fixture containing:

- an intent and acceptance contract;
- a base and candidate snapshot or deterministic patch;
- focused repository instructions;
- at least one known behavioral defect and one tempting non-finding;
- no provider-specific workflow instructions or expected prose.

The fixture and label derivation must be reviewed independently from the
backend adapters. Hidden evaluation labels are not included in the work order.

## Portable artifacts

Before a real invocation, define draft schemas or equivalent normative
contracts for:

1. `WorkOrder`: operation, reviewer role, goal, scope, contract and snapshot
   identities, permissions, budget, required evidence, independence policy,
   and result contract.
2. `CapabilityManifest`: probed backend and model identity plus supported
   structured output, isolation, cancellation, resume, steering, native review,
   parallelism, and usage reporting.
3. `ResultEnvelope`: terminal status, findings, evidence references, gaps,
   artifact identity, degradation, and a fixed `REPORT_ONLY` release
   recommendation. A single reviewer cannot earn `PROCEED`.
4. `InvocationReceipt`: actual runtime, provider, model, native strategy,
   inputs, permissions, timing, usage, cancellation, and raw-output digest.

Provider and model selection belong to the backend profile, not the portable
work order. Runtime identity and input digests are observed and recorded by the
adapter rather than trusted from model-authored prose.

The schemas must describe semantic requirements, not command-line flags or a
shared internal agent graph.

## Backend executions

Run the same work order once through each path:

- a Codex-native read-only path using the simplest surface that preserves
  structured output, identity, isolation, events, and cancellation;
- a Claude-native read-only path using the simplest equivalent surface, with a
  native workflow allowed only when the backend selects or requests it through
  declared capabilities.

Backend profiles translate the portable order into native configuration. They
may add execution mechanics but may not add provider-specific acceptance
criteria, defect hints, or expected conclusions.

Each path starts in a fresh inference context. It receives no transcript,
finding, summary, or expected conclusion from the other path. A schema failure
or backend failure is recorded as conformance evidence without an automatic
retry or repair prompt.

Record invocation commands or SDK parameters in secret-free receipts after
redaction. Do not require both backends to use the same number of agents or the
same orchestration topology.

## Focused negative probes

Use mocked process or protocol boundaries for malformed output, identity
mismatch, stale snapshot, absent required capability, cancellation, timeout,
late output, and personal-configuration leakage. These cases belong in the fast
adapter tier and do not require repeated real model calls.

Perform at most one real cancellation probe only if the chosen integration
surface cannot establish cancellation behavior through an existing local
protocol test or authoritative receipt.

## Measurements

Record:

- schema and receipt completeness;
- whether the exact input and snapshot are attributable;
- capability truthfulness and any degraded behavior;
- whether the known defect is reported with admissible evidence;
- false findings against the tempting non-finding;
- human intervention, wall time, and reported usage or cost;
- native features used and native features lost at the boundary.

Quality measurements are diagnostic in this exercise. Statistical promotion
criteria belong to the evaluation tier.

## Exit criteria

The exercise succeeds only when:

- one unchanged portable work order drives both native backends;
- both outputs validate against the portable result contract;
- both receipts bind actual identity, permissions, and output to the same
  immutable input;
- provider-specific mechanics remain confined to backend profiles;
- missing capabilities and malformed or stale results cannot become a normal
  successful result;
- no result from the first path is visible to the second path;
- the default offline suite performs no real backend invocation and remains
  within its runtime budget;
- the evidence is sufficient to accept, revise, or reject the ADR boundary
  before production implementation.

## Explicit non-goals

- building the production kernel or a general workflow DSL;
- reproducing one provider's interactive UI in another provider;
- proving that provider diversity guarantees independence;
- selecting a permanent orchestrator or model;
- repeated smoke runs or statistically meaningful model evaluation;
- tuning model-specific prompts beyond the minimum required to exercise the
  portable contract.
