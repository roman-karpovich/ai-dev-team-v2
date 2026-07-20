---
name: develop
description: Run a controlled, resumable native coding task with durable checkpoints and explicit handoff. Use only when the user explicitly invokes $ai-dev-team:develop in Codex or /ai-dev-team:develop in Claude Code; never activate for an ordinary coding request.
---

# Develop

Keep the active Codex or Claude session as the native executive. Add durable
task boundaries without replacing its planning, tools, dialogue, subagents, or
repository instructions. Do not launch another provider automatically.

Resolve every `references/...` locator below from the installed plugin root —
the installed plugin directory that contains `skills/` and `references/` —
not from this skill directory.

## Route references

Read a routed reference when its condition holds, at the stated moment. A
condition holds when any of its listed cases applies.

| When | Resource | Read it |
| --- | --- | --- |
| The active host is Claude Code. | `references/claude-runtime.md` | Before repository or artifact exposure, ADT state, or editing. |
| Always. | `references/task-lifecycle.md` | After the Claude runtime reference when that applied; before any ADT state read or mutation. |
| The write publishes commit metadata, tag metadata, a branch name, GitHub metadata, public prose, or a CI summary. | `references/publication-boundary.md` | Immediately before the persistent write. |
| New material owner dialogue arrives: an authoritative correction, a tentative design hypothesis, or a scope challenge or question. | `references/convergence-control.md` | Before further task action, candidate edits, review launch, worker dispatch, or publication. |
| The requested outcome or a reported or discovered symptom may depend on automatic reporting, framework or process lifecycle, termination or propagation, bootstrap, or event cardinality. | `references/incident-observability.md` | Before forming the task contract or editing a candidate. |
| Acceptance turns on an input-domain boundary, or a removed, deprecated, or unavailable upstream value is replaced by a local derivation. | `references/semantic-boundaries.md` | Before forming the task contract. |
| The change touches stateful ingestion, replay or cursor behavior, transactions or concurrency, migrations or mixed versions, retention, rebuild or rollback, malformed or failure behavior, production query bounds, or operational prerequisites, or carries comparable state-integrity, ordering, recovery, boundedness, or rollout risk; a repair follows a material `HOLD`; or plugin and card work interleave. | `references/convergence-control.md` | Before candidate edits, a repair restart, or a plugin install. |
| Any check executes source, an artifact, or a runtime. | `references/verification-environments.md` | Before executing the check and before interpreting its result. |
| A required check needs an unavailable dependency, runtime, production bootstrap, or load-bearing environment equivalence. | `references/verification-environments.md` | Before selecting the verification approach. |

When the dialogue route fires, stop incompatible work and refine the working
plan under the convergence reference before resuming task action.

## Establish the task

1. Perform the minimum read-only orientation needed to identify the target
   worktree, then follow the lifecycle reference and inspect `status`.
2. If no open task exists, continue with this preflight. Investigate repository
   context before asking questions. Resolve discoverable facts and routine
   uncertainty yourself; use a stated reversible assumption when it stays
   within authorized scope.
3. Form `GOAL` as a compact neutral contract: desired outcome and observable
   success, constraints and non-goals, verified facts separated from
   assumptions, and authoritative owner decisions or unresolved choices.
   Exclude proposed fixes, persuasive reasoning, prior findings, and expected
   conclusions. Preserve the owner's outcome when evidence corrects a premise.
4. For every nontrivial task, ensure a bounded `grill me` dialogue has occurred
   before candidate edits. Count material questions and decisions already
   resolved in the current conversation; do not repeat them. State the task's
   essence, surface contentious assumptions, risks, and genuine forks, then ask
   one coherent bounded batch of remaining material questions. Challenge
   answers when concrete tradeoffs warrant it. Do not ask investigable or
   routine questions. If the owner explicitly says `grill me`, deepen the pass
   even when the task initially appears specified. Skip the grill for an
   explicit small, reversible task unless the owner requests it.
5. Synthesize the resolved design as `task.md` content with its append-only
   material decision log, then present one compact decision brief. Treat `да`,
   `го`, `так`, or equivalent plain-language agreement as confirmation.
   `task.md` is your synthesis and decision log, not an approval form. The owner
   need not line-review it.
6. Skip state only when observable success is already satisfied and no
   repository work remains. Otherwise start `kind=develop`; append an explicit
   `--profile` only when the user selected one.

On resume, takeover, or same-lineage handoff, use `context` for orientation but
re-check load-bearing conclusions. Do not re-form the durable contract unless
drift or new evidence invalidates it. Checkpoint only a durable, material
refinement as one complete effective contract; ordinary clarification needs no
checkpoint.

## Work natively

- After confirmation, build, verify, and perform bounded repair autonomously.
  Reopen dialogue only for a newly discovered genuine fork. Ask when its answer
  changes product, architecture, scope, release authority, or another
  hard-to-reverse choice; otherwise investigate or use a stated reversible
  assumption.
- Inspect before editing. Use the host's native planning, tools, delegation,
  and repository workflows rather than recreating them here.
- When two or more independent bounded seams can proceed without shared
  mutation and coordination is cheaper than serial work, use native parallel
  delegation; keep tightly coupled edits with one integrator. Do not treat
  fan-out as independent review.
- When the convergence route fires, synthesize the applicable failure seams
  before candidate edits. Keep that compact model in the working plan unless a
  normal repository decision or checkpoint must outlive the session.
- Prefer a focused failing test before behavior-changing code. Choose the
  smallest verification seam that can distinguish the required behavior from
  the relevant defect; a self-confirming mock or irrelevant green suite is not
  proof.
- Work in coherent increments. Reassess when evidence invalidates the plan,
  fixes repeat, scope grows, or exceptions accumulate. Replan, pause, reshape,
  or discard instead of defending sunk cost.
- Checkpoint established facts, artifact state, checks, owner decisions, and
  open questions. Keep notes neutral and concise.

## Close the task honestly

- Before pausing or same-lineage handoff, checkpoint enough evidence for a
  fresh session to continue without a transcript.
- Before completion, disclose whether independent review ran. When the owner,
  repository policy, or task contract requires it, freeze an immutable commit
  range and keep the development task open but paused while fresh standalone
  cold paths run in separate checkouts under
  `references/cold-independent-review.md`; do not complete it before
  post-embargo adjudication. Provide only neutral scope and acceptance input,
  never builder findings or transcript.
- Complete only after the requested outcome and focused discriminating checks
  are satisfied and no blocking owner decision remains. Completion records
  workflow state, not release authorization or trusted review.
- Maintain `task.md` and produce `closeout.md` under the lifecycle artifact
  policy. Generate `adt report` only on demand. If blocked, checkpoint and pause
  instead of retaining an active lease while waiting.
