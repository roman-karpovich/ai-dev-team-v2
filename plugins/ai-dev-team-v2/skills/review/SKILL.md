---
name: review
description: Run a controlled evidence-based review with durable state and an explicit cold-review boundary. Use only when the user explicitly invokes $ai-dev-team:review in Codex or /ai-dev-team:review in Claude Code; never activate for an ordinary review request.
---

# Review

Use the active host's native review judgment and tools. Review against accepted
intent, repository constraints, immutable scope, and observable behavior. Do
not launch another provider automatically or repair findings unless the user
explicitly changes the task.

All `references/...` locators below resolve from the installed plugin root.

## Load preflights before state

| Trigger | Resource | Boundary |
| --- | --- | --- |
| `request:cold\|independent\|two-model` | `references/cold-independent-review.md` | `before:artifact-inspection\|repository-context\|adt-state` |
| `host:claude` | `references/claude-runtime.md` | `after:cold-if-triggered;before:repository-exposure\|adt-state\|artifact-inspection` |
| `always` | `references/task-lifecycle.md` | `after:prior-preflights;before:adt-state\|mutation` |

`|` joins alternatives or boundary members; `;` sequences boundaries from
left to right.

Load optional specialist routes only when their trigger applies:

- When a reviewed claim actually depends on automatic reporting, framework or
  process lifecycle, termination or propagation, bootstrap, or event
  cardinality, read `references/incident-observability.md` before inspecting
  the artifact for that claim.
- When acceptance turns on an input-domain boundary or on replacing a removed,
  deprecated, or unavailable upstream value with a local derivation, read
  `references/semantic-boundaries.md` before judging that claim.
- When a required check needs an unavailable dependency, runtime, production
  bootstrap, or load-bearing environment equivalence, read
  `references/verification-environments.md` before selecting verification.

## Define the review without priming it

1. Identify the single Git worktree that owns the artifact. Split a
   cross-repository claim into bounded reviews and state the combined claim
   that remains outside this MVP.
2. Resolve committed `BASE` and `HEAD` to immutable SHAs. Use the full accepted
   range; never substitute `HEAD^..HEAD` unless the user explicitly selected a
   single-commit scope.
3. Form a neutral `GOAL` with review intent, acceptance criteria, accepted
   input domain and non-goals, authoritative owner decisions, and the exact
   `$BASE..$HEAD` scope. Exclude prior findings, suspected locations,
   severities, proposed fixes, and expected conclusions.
4. For each counted cold path, use a distinct checkout, fresh inference
   context, standalone path-specific `kind=review` state, and sealed output.
   Never hand off between cold paths, resume another path's state, or read its
   context. Keep every path's findings hidden until all counted paths have
   fixed their results; adjudicate only then.

Use lifecycle `context`, resume, and handoff only inside one existing review
lineage or for explicitly non-cold continuation. Once findings enter a lineage,
later work there is repair validation, never a fresh cold path. Preserve
`kind=develop` only when validating a handed-off development repair.

## Review independently

- Inspect the accepted commit list and `git diff "$BASE..$HEAD"`. Re-derive
  requirements and relevant failure behavior from authoritative sources and
  the baseline, not from builder confidence or tests alone.
- Review correctness, failure behavior, security and data risk, compatibility,
  architectural fit, and maintainability in proportion to the change. Check
  whether tests could pass while the requirement remains broken.
- Run focused, read-only, discriminating checks when the environment is ready.
  Record commands, outcomes, and environment limits; do not turn an unavailable
  broad suite into a finding unless an accepted claim requires that evidence.
- Report findings first, ordered by materiality, with precise artifact
  evidence, the violated accepted claim or repository constraint, and the
  reachable in-domain consequence. Distinguish blockers, non-blocking
  observations, and open questions. If none survive, state residual gaps.
- Checkpoint neutral evidence and conclusions only within the current lineage.
  Keep a cold path's output sealed until the cross-path embargo ends.

## Preserve the assurance boundary

- One reviewer is one judgment path, not trusted acceptance. Missing required
  evidence, independence failure, unresolved material disagreement, or an
  unwaived blocking finding yields `HOLD`; never soften it into a qualified
  pass. Silence is not a waiver.
- A two-model request requires distinct fresh paths and post-embargo
  adjudication. This skill does not dispatch another path, and model diversity
  alone does not prove epistemic independence.
- For a handed-off development task with a repair-blocking finding, checkpoint
  it and pause or hand it back; do not complete the development task. A
  standalone review task may complete after its sealed report is fixed,
  including a `HOLD` report. Completion is not release authorization.
