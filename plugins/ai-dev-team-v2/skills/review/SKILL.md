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
| `request:cold\|independent\|two-model\|repair:material-hold\|evidence:reuse` | `references/convergence-control.md` | `after:cold-preflight-if-triggered;before:review-key\|check-selection\|counted-cold-launch` |
| `host:claude` | `references/claude-runtime.md` | `after:cold-if-triggered;before:repository-exposure\|adt-state\|artifact-inspection` |
| `always` | `references/task-lifecycle.md` | `after:prior-preflights;before:adt-state\|mutation` |
| `dialogue:owner-correction\|design-hypothesis\|scope-challenge` | `references/convergence-control.md` | `before:task-action\|candidate-edit\|review-launch\|worker-dispatch\|publish` |
| `depends-on:auto-reporting\|framework-lifecycle\|process-lifecycle\|termination\|propagation\|bootstrap\|event-cardinality` | `references/incident-observability.md` | `before:claim-artifact-inspection` |
| `acceptance:input-domain\|upstream-replacement:removed,deprecated,unavailable->local-derivation` | `references/semantic-boundaries.md` | `before:claim-judgment` |
| `check:executes-source\|artifact\|runtime` | `references/verification-environments.md` | `before:check-execution\|result-interpretation` |
| `verification:unavailable-dependency\|runtime\|production-bootstrap\|environment-equivalence` | `references/verification-environments.md` | `before:verification-selection` |

`|` joins alternatives or boundary members; `;` sequences boundaries from
left to right.

When the dialogue route fires, stop incompatible work and refine the working
plan under the convergence reference before resuming task action.

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
   Outside a counted cold path, investigate routine uncertainty, present a
   compact decision brief for material scope choices, and accept ordinary
   plain-language confirmation. Ask again only for a newly discovered genuine
   product, architecture, scope, release-authority, or hard-to-reverse fork.
   Inside a counted cold path, the fixed work order and contact boundary replace
   owner dialogue.
4. For each counted cold path, use a distinct checkout, fresh inference
   context, standalone path-specific `kind=review` state, and sealed output.
   Require the fixed work order to name the sealed artifact destination. If it
   does not, return a terminal gap or `HOLD` without contact or a tracked write.
   Declare its purpose and `ReviewKey` first; a diagnostic path is not final
   acceptance, and a final path must be eligible before it launches.
   A counted reviewer owns exactly one path and returns one sealed
   findings-first report.
   Quiesce the launcher lane first and run counted paths one at a time as the
   cold-review reference requires.
   Do not run `adt review-gate` inside a counted path. It is a launcher-only
   aggregator for already sealed multi-path evidence, not a review lifecycle
   command. Do not create `bundle.json` or ask for its schema.
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
- In a counted cold path, record a missing normative input as a terminal gap or
  `HOLD`; never ask the launcher, root, owner, or another agent for it. Outside
  a counted cold path, follow the ordinary owner-decision route.
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
- Maintain the neutral effective specification in `task.md` and put the fixed
  findings-first outcome in `closeout.md` under the lifecycle artifact policy.
  Generate `adt report` only on demand; keep terminal status, review verdict,
  release recommendation, and publication authority distinct.
