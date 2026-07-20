# Incident observability and lifecycle

Load this reference when the requested outcome or a reported or discovered
symptom may depend on automatic reporting, framework or process lifecycle,
termination or propagation, bootstrap, or event cardinality — including
missing, duplicate, or misordered reports or events. Do not apply it to
every bug.

## Required outcomes

| Boundary | Trigger | Required | On unmet |
| --- | --- | --- | --- |
| `causal-reproduction` | `probe:adds-unverified-causal-precondition;safe-probe:unavailable-or-negative` | `establish-precondition-from:repository,deployment,incident-evidence` | `causality:unverified;develop:pause-unless-owner-revises-goal;review:withhold-affected-claim` |
| `final-observer-evidence` | `claim:incident-outcome` | `compare:baseline,candidate@same-final-observer;measure:reachability,ordering,propagation-or-exit,exact-event-cardinality` | `claim:withhold` |

## Qualify the baseline

Identify the final production-relevant observer and the measurable outcome.
A worker, callback, handler, future, or explicit reporting call is not final
when a later framework or process hook still observes the failure.

Before a candidate edit, inspect the immutable baseline and run the safest
focused probe that reaches the final observer when one is available. Exercise
the actual repository bootstrap or production entry point when initialization,
automatic hooks, shutdown, or process behavior is load-bearing. A copied
harness that installs those hooks itself is exploratory, not equivalent.

Do not claim reproduction when the probe adds an unverified causal
precondition, such as a synthetic hang, signal, timeout, kill, or supervisor
action. Establish added preconditions from repository, deployment, or incident
evidence. If a safe discriminating probe is unavailable or does not reproduce,
mark causality unverified. A builder must pause before changing an incident
into hardening unless the owner explicitly revises the goal; a reviewer must
withhold the affected acceptance claim.

## Preserve disposition

- Preserve the accepted failure policy unless the owner explicitly changes
  exit or restart, retry or skip, cursor or checkpoint advancement,
  transaction boundaries, cleanup, sibling fate, or partial success.
- Compare baseline and candidate at the same final observer. Account for
  reachability, ordering, propagation or exit, handled classification when
  operationally meaningful, and exact aggregate event cardinality.
- Enumerate all enabled automatic routes when a candidate adds reporting while
  the failure still propagates: direct SDK, logging integration, framework
  hook, and process hook.
- Treat `>= 1`, non-empty, per-route call assertions, or a mocked reporting
  call as partial evidence when duplication, loss, or final delivery matters.
- Prove process-global observer activation at the measurement point. Isolate
  baseline, candidate, and repeated cases in fresh processes when public
  teardown cannot reset hooks and integration registries consistently.

Checkpoint the immutable snapshot, observer route, probe entry point, measured
outcome, result, and provenance. Reuse that evidence after resume or handoff
only when all of those bindings remain applicable.
