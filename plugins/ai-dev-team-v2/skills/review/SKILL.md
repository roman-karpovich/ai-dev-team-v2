---
name: review
description: Run a controlled evidence-based review with durable state and an explicit cold-review boundary. Use only when the user explicitly invokes $ai-dev-team:review in Codex or /ai-dev-team:review in Claude Code; never activate for an ordinary review request.
---

# Review

Use the active host's native review judgment and tools. Review against accepted
intent, repository constraints, immutable scope, and observable behavior. Do
not launch another provider automatically or repair findings unless the user
explicitly changes the task.

Resolve every `references/...` locator below from the installed plugin root —
the directory containing this plugin's manifest — not from this skill
directory.

## Route references

The first four rows are ordered preflights; later rows load on demand when
their condition holds. A condition holds when any of its listed cases
applies.

| When | Resource | Read it |
| --- | --- | --- |
| The review is explicitly requested as cold, independent, or two-model. | `references/cold-independent-review.md` | First — before artifact inspection, repository context, or ADT state. |
| The review is cold, independent, or two-model; a repair follows a material `HOLD`; or verification evidence may be reused. | `references/convergence-control.md` | After the cold preflight when that applied; before fixing the `ReviewKey`, selecting checks, or launching a counted cold path. |
| The active host is Claude Code. | `references/claude-runtime.md` | After the cold preflight when that applied; before repository or artifact exposure or ADT state. |
| Always. | `references/task-lifecycle.md` | After the applicable preflights above; before any ADT state read or mutation. |
| The write publishes commit metadata, tag metadata, a branch name, GitHub metadata, public prose, or a CI summary. | `references/publication-boundary.md` | Immediately before the persistent write. |
| New material owner dialogue arrives: an authoritative correction, a tentative design hypothesis, or a scope challenge or question. | `references/convergence-control.md` | Before further task action, candidate edits, review launch, worker dispatch, or publication. |
| The requested outcome or a reported or discovered symptom may depend on automatic reporting, framework or process lifecycle, termination or propagation, bootstrap, or event cardinality. | `references/incident-observability.md` | Before inspecting the artifact for an affected claim. |
| Acceptance turns on an input-domain boundary, or a removed, deprecated, or unavailable upstream value is replaced by a local derivation. | `references/semantic-boundaries.md` | Before judging the affected claim. |
| Any check executes source, an artifact, or a runtime. | `references/verification-environments.md` | Before executing the check and before interpreting its result. |
| A required check needs an unavailable dependency, runtime, production bootstrap, or load-bearing environment equivalence. | `references/verification-environments.md` | Before selecting the verification approach. |

When the dialogue route fires, stop incompatible work and refine the working
plan under the convergence reference before resuming task action.

## Define the review without priming it

1. Identify the single Git worktree that owns the artifact. Split a
   cross-repository claim into bounded reviews and state the combined claim
   that remains outside this MVP.
2. Resolve committed `BASE` and `HEAD` to immutable SHAs. Use the full accepted
   range; never substitute `HEAD^..HEAD` unless the user explicitly selected a
   single-commit scope. Verify that `BASE` is an ancestor of `HEAD`; otherwise
   proceed only on an explicitly owner-selected endpoint comparison and record
   that choice.
3. Form a neutral `GOAL` with review intent, acceptance criteria, accepted
   input domain and non-goals, authoritative owner decisions, and the exact
   `$BASE..$HEAD` scope. For a fresh, uninformed review, exclude prior
   findings, suspected locations, severities, proposed fixes, and expected
   conclusions. Informed repair validation within an existing lineage instead
   includes the specific finding under validation; it is never a fresh cold
   path.
   When the review carries a material security or data-assurance obligation,
   state the applicable properties as invariants in the acceptance criteria
   and put evidence-generation limits in the constraints; do not frame the
   goal as attacking the artifact.
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
- Assess security and data risk by verifying accepted invariants: when
  applicable, authorization and input-validation boundaries are enforced,
  secrets and sensitive values stay out of logs, artifacts, and evidence, and
  failure paths preserve the accepted policy. Establish reachability from
  source, configuration, or data-flow evidence, existing safe tests, or the
  smallest safe bounded check within the accepted input or threat domain,
  including inputs a boundary is required to reject. Do not create new
  operational exploit artifacts or reusable attack tooling. These limits
  constrain evidence generation, not analysis or reporting: report every
  credible in-scope security concern under the ordinary taxonomy, and do not
  omit or downgrade an evidence-backed reachable violation merely because no
  exploit artifact was created. If stronger validation would require
  operational attack material, stop at the strongest safe evidence and record
  the smallest safe resolving check or the required-evidence gap. If the
  accepted contract explicitly requires active exploit construction, record a
  required-evidence or capability gap rather than silently substituting
  weaker analysis.
- Run focused, read-only, discriminating checks when the environment is ready.
  Record commands, outcomes, and environment limits; do not turn an unavailable
  broad suite into a finding unless an accepted claim requires that evidence.
- Report artifact-grounded review concerns first, ordered by materiality.
  Classify each as a blocking finding, a non-blocking observation, or an open
  question; do not omit a credible concern solely because reachability,
  impact, or contract status remains unresolved. Each blocking finding must
  cite precise artifact evidence, the violated accepted claim or repository
  constraint, and the reachable in-domain consequence. For an open question,
  name the unresolved fact and the smallest discriminating check. If there
  are no blocking findings, say so and state observations, open questions,
  and residual gaps.
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
