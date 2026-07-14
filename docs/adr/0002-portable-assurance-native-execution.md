# ADR 0002: Portable assurance, native execution

- Status: Proposed
- Date: 2026-07-13

## Context

Frontier coding products improve independently and unevenly. The best current
orchestrator, builder, or reviewer may change as Codex, Claude Code, and future
runtimes add stronger native planning, subagents, workflows, review, steering,
and isolation.

v2 must be able to replace a provider or model without replacing its trust
contract. It must also preserve each runtime's strongest native execution
features. Treating every provider as a one-shot text model would discard those
features; duplicating the complete development protocol in every host would
create semantic drift and an instruction-maintenance matrix.

The durable product is therefore not a particular model's orchestration. It is
the controlled relationship among intent, repository state, decisions,
evidence, findings, and release policy.

## Decision

Adopt a two-layer architecture summarized as **portable assurance, native
execution**:

1. A provider-neutral assurance kernel owns deterministic lifecycle semantics,
   durable state, evidence validity, and release gates.
2. Replaceable native execution backends use the strongest available runtime
   mechanisms to perform bounded work.

The kernel is not a model and does not design the solution. A selected model
may act as the current lead, builder, reviewer, or adjudicator, but it receives
authority only for a bounded execution lease. Model selection is role-specific
and evaluation-driven; no provider is the permanent orchestrator.

### Assurance-kernel responsibilities

The kernel owns:

- task-contract identity and version;
- repository snapshot and execution-scope identity;
- workflow state, checkpoints, budgets, and terminal derivation;
- confirmed facts, assumptions, decisions, waivers, and dependency-aware
  invalidation;
- backend capability requirements and selection policy;
- evidence and finding receipts;
- pause, cancellation, reassessment, and fail-closed release behavior.

These responsibilities must remain inspectable and deterministic. A model may
propose a transition or decision, but it does not silently make a policy-owned
transition true.

### Native-backend responsibilities

Within one execution lease, a backend may natively choose:

- decomposition and internal control flow;
- subagents, dynamic workflows, skills, tools, and local worktrees;
- focused repair and verification loops;
- model and effort routing allowed by the work order;
- provider-specific progress, steering, and continuation mechanisms.

The portable contract does not standardize the backend's internal agent graph.
For example, Claude may use an UltraCode workflow while Codex uses native
subagents and review. Both are required to return a portable receipt, not to
execute the same topology.

### Portable boundary

Every backend consumes a canonical `WorkOrder` and returns a canonical
`ResultEnvelope` plus an invocation receipt.

A `WorkOrder` identifies at least:

- the operation, semantic role, goal, scope, and non-goals;
- task-contract version and repository snapshot;
- applicable policy, permissions, isolation, and budget;
- required evidence, independence constraints, and exit criteria;
- expected artifact and structured-result contract;
- whether continuation, steering, or native parallelism is required.

A result identifies at least:

- terminal status and produced artifact, patch, or snapshot;
- claims and their evidence references;
- findings, disagreements, open questions, and residual gaps;
- actual provider, runtime, model, native strategy, and permissions;
- input and snapshot binding;
- usage, elapsed time, cancellation, and degradation information.

The concrete schemas remain readiness work. This ADR fixes their semantic
boundary, not their final field layout.

### Capability negotiation

Backends advertise versioned, probed capabilities rather than pretending to be
identical. Examples include structured output, live steering, durable session
resume, native parallelism, detached review, filesystem isolation, model
routing, and usage events.

Selection policy requests semantic capabilities. A backend profile maps those
requests to current native mechanisms. An unavailable required capability must
produce an explicit unsupported or degraded result; it must not be silently
approximated from a provider name or version string.

### Checkpoints and host switching

Provider switching occurs at a neutral checkpoint containing the repository
snapshot, contract version, accepted decisions, valid evidence, open findings,
invalidation set, and next work order.

Provider session identifiers, transcripts, workflow scripts, and hidden model
state are optional backend-local caches. They are not project state and are not
required by the next provider. v2 does not promise to transfer hidden reasoning
or reproduce one host's UI inside another host.

An interactive Codex or Claude integration is a thin host facade over the same
kernel. A headless CLI, SDK, App Server, or MCP invocation is an adapter
mechanism, not a separate product contract. One provider may technically invoke
another through MCP, but direct provider-to-provider coupling is not the
architectural source of truth.

### Instruction composition

Instructions are composed from independent layers:

1. one provider-neutral project and assurance contract;
2. provider-neutral semantic role contracts;
3. the task-specific work order;
4. a small backend execution profile containing only runtime mechanics;
5. an optional model-specific delta retained only when evaluation demonstrates
   a material benefit.

Host instruction files, skills, and plugins are thin entry facades. They do not
copy the mission or lifecycle. A model-specific delta is scoped, versioned,
attributable to evaluation evidence, and periodically reconsidered.

### Independence in trusted review

Native fan-out inside one provider is one judgment path unless evaluation
demonstrates otherwise. A policy-required independent path receives the
authoritative task contract and artifact without seeing the author's or first
reviewer's conclusions. Results remain sealed until adjudication.

Provider diversity is a selection input, not proof of independence.

## Consequences

- Codex, Claude, and future runtimes can replace one another by role without
  changing the assurance contract.
- v2 can adopt new native orchestration features without copying their
  implementation or reducing them to a lowest common denominator.
- Switching providers is reliable only at explicit checkpoints; an in-flight
  native workflow may need to finish or be cancelled first.
- Backend conformance must validate identity, snapshot binding, permissions,
  cancellation, capability claims, structured results, and degradation.
- The adapter boundary is broader than a CLI wrapper and narrower than a
  portable workflow engine.
- Backend profiles and model deltas add maintenance cost, so unsupported or
  unmeasured specialization is deleted rather than accumulated.

## Rejected alternatives

- **Make Codex the permanent orchestrator:** rejected because current product
  leadership is not a durable architectural invariant.
- **Make Claude or UltraCode the permanent orchestrator:** rejected for the
  same reason.
- **Build a lowest-common-denominator external orchestrator:** rejected because
  it would recreate improving vendor runtimes while suppressing their strongest
  native features.
- **Duplicate the full protocol in host-specific instructions:** rejected
  because copies would drift and compliance would depend on prompt obedience.
- **Make direct Codex-to-Claude invocation the core boundary:** rejected because
  the active host would still own state, policy, and failure semantics.

## Staged adoption

This decision does not authorize production orchestration.

1. During readiness, define the portable work-order, result, capability, and
   invocation-receipt contracts and collect adapter conformance evidence.
2. Run one bounded cold-review conformance exercise through a Codex-native and
   a Claude-native path. Use one real invocation per backend; repeated
   statistical evaluation remains a separate opt-in tier.
3. Use the trusted-review slice to evaluate role qualification, complementary
   defect detection, false greens, latency, and cost.
4. Add durable cross-host checkpoints with reassessment work.
5. Add bounded development leases only after VERIFY and trusted review earn
   promotion under their declared gates.

## Acceptance criteria

The decision is validated when:

- the same canonical cold-review work order can be executed by two native
  backends without embedding provider-specific workflow steps in the order;
- both results validate against one portable result contract and bind to the
  same input snapshot;
- each receipt reports actual identity, capabilities, permissions, native
  strategy, usage, and degradation;
- cancellation, malformed output, identity mismatch, missing capability, and
  stale snapshot have explicit fail-closed outcomes;
- a checkpoint produced by either backend can seed a fresh execution by the
  other without its transcript;
- the default offline suite remains fast and real-backend checks remain
  explicit opt-in operations.

## Public capability references

- [Codex App Server](https://developers.openai.com/codex/app-server)
- [Codex SDK](https://developers.openai.com/codex/sdk)
- [Codex as an MCP server](https://developers.openai.com/codex/mcp-server)
- [Claude Code programmatic usage](https://code.claude.com/docs/en/headless)
- [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)
- [Claude Code dynamic workflows and UltraCode](https://code.claude.com/docs/en/workflows)
