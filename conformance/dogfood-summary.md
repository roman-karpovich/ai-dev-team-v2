# Development and review dogfood summary

- Date: 2026-07-15
- Status: Manual evidence from real tasks; not statistical model qualification
- Scope: AI Dev Team contract behavior, not production rollout approval

## What was exercised

The MVP was used on three different task shapes:

1. a bounded operational-health change with concrete numeric requirements;
2. an incident report whose observable outcome crossed worker, process, and
   error-reporting boundaries; and
3. a supply-metric refresh whose upstream schema no longer exposed all state
   required by the requested product meaning.

Builders and reviewers ran through native Codex and Claude Code workflows.
Durable task state, pause and resume, cross-host handoff, immutable review
boundaries, focused tests, causal controls, and independent cold review were
exercised where applicable.

## Material results

- Owner-provided requirement changes survived handoff, including later
  supersession of an earlier numeric value.
- A builder initially converted a weak incident report into a different
  failure policy. Repository and deployment evidence exposed the mismatch;
  the candidate was rejected instead of treating green tests as acceptance.
- Repeated review passes found tests that observed locally inserted calls while
  missing downstream process behavior. The accepted proof required a safe
  negative control to make the claimed measurable outcome fail, not merely an
  implementation sentinel.
- Fresh Codex and Claude reviews could disagree materially. Their labels were
  treated as evidence to adjudicate, not as votes or automatic approval.
- A later clean task correctly stopped before edits when upstream fields had
  disappeared and the product meaning of both current and compatibility totals
  was unresolved. The owner then established that archived contract balances
  had left the supported protocol and selected the replacement formulas; the
  pause prevented the builder from inventing either decision.
- After the owner narrowed that supply contract, an over-broad cold-review
  brief omitted the accepted network-value domain. The reviewer then generated
  out-of-domain monetary counterexamples and a defensive-validation detour.
  Reissuing the same immutable candidate with the verified domain invariant and
  explicitly unsupported inputs restored a relevant review boundary and the
  minimal candidate was accepted.
- The launcher exposed an exact model identifier while model-authored records
  could only report `unknown`. Runtime/model provenance therefore belongs to
  launcher-owned execution evidence after conclusions are fixed, not model
  self-report or the requested model name.
- An execution's failure to follow an already explicit contract was repaired
  under the same release. It did not automatically create another rule or
  workflow artifact.

## Boundaries retained by the MVP

- Corrected facts may challenge a proposed solution, but may not silently
  replace the owner's desired outcome.
- Decisions that materially change product meaning, failure policy, or risk
  require a focused owner choice before candidate edits.
- Tests are inspected as evidence. Exact downstream outcome, propagation,
  persistence, cardinality, and lifecycle matter when they are load-bearing.
- Independent review starts from a neutral contract and immutable candidate;
  same-session helpers remain advisory.
- Neutral review context carries the accepted input domain and explicitly
  unsupported inputs, while factual domain invariants remain independently
  checkable.
- Code-green and rollout-ready remain separate conclusions.
- A safe no-code pause is a valid result when required normative input or a
  production-relevant oracle is missing.

## Limitations

These runs cover a small number of task classes and model executions. They do
not establish comparative model rankings, backend interchangeability, live
deployment behavior, or plugin stability. A clean implementation-to-publication
cycle on additional tasks is still required.
