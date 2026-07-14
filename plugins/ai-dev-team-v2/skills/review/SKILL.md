---
name: review
description: Run an evidence-based code review while preserving the active host's native review tools and judgment. Use only when the user explicitly invokes $ai-dev-team:review in Codex or /ai-dev-team:review in Claude Code to inspect an existing change, continue a handed-off review, or record review completion; never activate for an ordinary coding request.
---

# Review

Review the change independently against its intent, repository constraints,
and observable behavior. Keep the active host's native review facilities and
project instructions; do not replace them with a scripted checklist.

## Independence preflight

Apply this preflight when the invocation requests a cold, independent, or
two-model review. Run it before inspecting the artifact or mutating ADT state.

- Inspect all context already provided to the session, including the current
  prompt, cross-session or cross-host memory, imported summaries, transcripts,
  and handoff context. Authoritative intent, owner decisions, neutral scope and
  snapshot details, acceptance criteria, and permitted checks are safe inputs.
  Prior findings, suspected locations, severities, proposed fixes, or expected
  conclusions contaminate a cold review.
- If contaminating context is present, stop and label the attempt
  `independence-compromised`. In Codex, launch a replacement as a one-off
  memory-clean process before the session starts, with
  `-c 'memories.use_memories=false'` and
  `-c 'memories.generate_memories=false'`, then invoke this skill. Do not edit
  global config for a cold review. An in-session setting cannot restore
  independence after memory has already entered the context. On another host,
  establish the equivalent memory-clean session. If that is impossible,
  continue only when the user accepts a non-independent validation. Telling
  the model to ignore contaminated context is insufficient because it has
  already primed the review.

## Connect to the task

1. Require `adt` on `PATH`. If `command -v adt` fails, stop and tell the user
   to run `make mvp-install` from an AI Dev Team v2 checkout, then start a new
   host session. Do not simulate durable state.
2. Set `HOST` to `codex` in Codex or `claude` in Claude Code. Before starting
   state, use read-only inspection to identify the Git worktree that owns the
   reviewed artifact; the launcher or knowledge repository may only be
   context.
3. One MVP review covers exactly one Git worktree. If the requested artifact
   spans repositories, split it into bounded reviews and state which combined
   claim remains outside this MVP's assurance. Carry all known owner
   supersessions in the neutral `GOAL`: identify the authoritative owner, the
   exact old and new requirement or value, the superseded source or decision,
   and any remaining open owner decision. Do not infer authority from a builder
   commit message. If supplied requirement sources conflict and no
   authoritative owner decision resolves them, stop and ask the user; do not
   invent precedence. For a committed review, resolve `BASE` and `HEAD` to
   immutable commit SHAs before creating state, state both values, and put the
   resolved `$BASE..$HEAD` range in the neutral `GOAL`. If the full-change
   boundaries are ambiguous, ask the user. Never silently use `HEAD^`; use
   `HEAD^..HEAD` only when the user explicitly accepts a single-commit scope.
4. The launcher or user must not pre-create a standalone ADT review task. After
   the Independence preflight and read-only workspace orientation, the
   reviewer starts or connects to state itself. Set `WORKSPACE` to the selected
   target root and run
   `adt --workspace "$WORKSPACE" status`. Save the active task's durable kind
   as `TASK_KIND`; preserve an existing `kind=develop` when review is a handed-
   off phase of that task. `status` is metadata-only: it must omit the goal,
   checkpoint notes, and completion summary. If a cold review receives any of
   them from `status`, stop as
   `independence-compromised`. If no task exists, or the current task is already
   completed, start a new one with
   `adt --workspace "$WORKSPACE" start --host "$HOST" --kind review --goal "$GOAL"`,
   set `TASK_KIND` to `review`; the reviewer retains the returned lease as
   `LEASE`. The reviewer starts only after the preflight and lets `GOAL`
   identify the artifact, resolved range, and review intent. If the invocation
   explicitly selects `economy`, `balanced`, `critical`, or `manual`, append
   `--profile "$PROFILE"`; otherwise keep the balanced default.
5. For a cold or independent review of an existing open task, run
   `adt --workspace "$WORKSPACE" context` read-only before resume, takeover, or
   artifact inspection. Re-apply the Independence preflight to that payload.
   Stop as `independence-compromised` if its goal or checkpoints disclose prior
   findings, locations, severities, fixes, or expected conclusions. A later
   review of the same finding-bearing repair task is repair validation, not a
   cold review.
6. Resume only a task paused or handed to this host. Inspect reported drift
   before asking whether to use `resume --host "$HOST" --accept-drift`. Keep
   the lease ID returned by `start` or `resume` as `LEASE`.
7. If another host owns the task, stop and request an explicit handoff.
   If this host owns an active task but this session lacks its latest lease,
   ask the user to approve a same-host takeover. Only after approval run
   `adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"`
   and keep its returned ID as `LEASE`.
8. Run `adt --workspace "$WORKSPACE" context` unless step 5 already inspected
   the same payload. Treat prior summaries and builder claims as untrusted
   orientation, never as review evidence. Status and context intentionally omit
   the lease ID; do not read it from the state file. Every active mutation must
   send `LEASE`. Replace it with the renewed ID returned by each successful
   checkpoint.

## Review independently

- Use the original goal, accepted requirements, current repository state, and
  actual diff as the review basis. For a committed range, inspect the commit
  list and `git diff "$BASE..$HEAD"`; do not substitute the latest commit for
  the accepted scope. In a cold review, use a fresh host session and do not
  seek the builder's transcript or another reviewer's conclusions.
- Inspect correctness, failure behavior, security and data risks,
  architectural fit, compatibility, and maintainability in proportion to the
  change. Check whether tests could pass while the requirement remains broken.
- Use native review tools and focused verification. Before declaring focused
  tests unavailable, inspect already-ready repo-native runtimes: repository
  instructions and test targets, an existing environment, and an existing
  local image or container. If one can run the exact focused offline selector,
  use it. Do not install dependencies, build, or pull merely to fill a review
  gap. This bounded discovery does not authorize a broad suite or live-network
  smoke; report the exact residual coverage gap if no ready runtime works.
- Do not modify code unless the user explicitly requests review-and-repair.
  Keep findings independent before beginning any repair.
- Report actionable findings first, ordered by severity. Give a precise
  location, impact, triggering conditions, and supporting evidence. If there
  are no findings, state residual coverage gaps and uncertainty explicitly.

## Preserve a cold second review

When the user requests two-model or independent review, use this manual MVP
protocol:

1. Reviewer A forms its findings in its native session. Keep those findings out
   of `adt` state and do not pass them, suspected locations, severities, or
   proposed fixes to reviewer B.
2. Before handoff, record only a neutral note containing authoritative intent,
   known owner supersessions, exact scope and snapshot, accepted criteria, and
   permitted checks. Then use
   `handoff --host "$HOST" --lease "$LEASE" --to "$OTHER_HOST"`. Tell the user
   not to copy A's findings into the next session.
3. Start a fresh session in host B and run the Independence preflight before
   invoking this skill. B reads the neutral context and commits its own findings
   before seeing A's conclusions. If A's findings leaked into context, stop and
   label the attempt `independence-compromised`.
4. After B has stated its conclusions, record B's reviewed scope, checks, and
   findings with `checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"`.
5. Only then reveal A's report and compare agreements, unique findings, and
   disagreements. Resolve disputed claims from repository evidence. Do not
   complete the joint review before this comparison unless the user explicitly
   requests two unadjudicated reports.

The MVP has no sealed-results store. This protocol depends on the user and
reviewer A keeping A's findings in its native session until B commits its
conclusions. Describe the result as manually independent, not cryptographically
or mechanically sealed.

## Record the boundary

For a single-review run, or after an independent reviewer has committed its
conclusions, record the reviewed scope, checks, and unresolved findings as a
factual checkpoint:

```text
adt --workspace "$WORKSPACE" checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"
```

Pause when interrupted. Outside the cold-review protocol, hand off only on the
user's explicit request, then direct the user to invoke the review skill in a
fresh session of the other host. Never call that provider automatically.

If `TASK_KIND=develop` and any unresolved material finding requires
repair or withholds acceptance, do not call `complete`. Leave the development
task active, checkpoint the findings, and request explicit repair or handoff
direction from the user. Complete a handed-off development task only after its
requested goal and acceptance criteria are satisfied, proportionate
verification is present, and no repair-blocking findings or open owner
decisions remain.

If `TASK_KIND=review`, the standalone review report may complete once
the report is finished, even when its conclusion is HOLD. Record that boundary
with:

```text
adt --workspace "$WORKSPACE" complete --host "$HOST" --lease "$LEASE" --summary "$SUMMARY"
```

Review completion records finished work; it is not automatically a release
approval or a claim that the artifact is defect-free.
