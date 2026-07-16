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
  snapshot details, acceptance criteria, the accepted input domain, explicitly
  unsupported inputs, and permitted checks are safe inputs.
  Prior findings, suspected locations, severities, proposed fixes, or expected
  conclusions contaminate a cold review.
- If contaminating context is present, stop and label the attempt
  `independence-compromised`. In Codex, launch a replacement as a one-off
  memory-clean process before the session starts, with
  `-c 'memories.use_memories=false'` and
  `-c 'memories.generate_memories=false'`, then invoke this skill. Do not edit
  global config for a cold review. An in-session setting cannot restore
  independence after memory has already entered the context. For a one-off
  Claude Code CLI review, set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` before the
  process starts and use `--no-session-persistence`; this does not change
  global memory configuration. On another host, establish the equivalent
  memory-clean session. If that is impossible, continue only when the user
  accepts a non-independent validation. Telling the model to ignore
  contaminated context is insufficient because it has already primed the
  review.
- Builder-spawned subagents and repeated review passes inside the builder's
  active session may advise the implementation, but they do not count as
  independent judgment paths. A counted path starts in a fresh preflighted
  session, receives only neutral context, and fixes its conclusion under the
  review embargo. A two-model claim additionally requires evidence of distinct
  actual models.

## Resolve the Claude model boundary

After the Independence preflight and before artifact inspection, ADT state, or
repository orientation, resolve the model boundary when the current host is
Claude Code. Host, model, task complexity, and assurance profile are
independent. Follow the owner's explicit choice, subject to host availability
and the applicable data policy; otherwise prefer Opus 4.8 for bounded,
well-specified, or routine work and Fable 5 for highest-complexity,
long-horizon, architecture-wide, or high-ambiguity work. Do not infer a model
from `--profile`, automatically route one, or silently fall back through a CLI,
SDK, or API.

If the selected Claude model is unavailable, ineligible under the applicable
policy, or refuses the review, stop and return control to the owner for a
visible manual choice. Do not restart a simple review already running in Fable
merely to downgrade. If Opus is materially underpowered for a frontier review,
recommend a fresh Fable session before ADT state or artifact exposure; the
owner may explicitly accept a visible Opus continuation as a degraded
tradeoff. Switching models after contamination does not restore independence.
A fallback or switch after artifact inspection or prior findings requires a
fresh neutral session and another preflight.

After the reviewer has fixed its conclusions, record the actual model and any
visible fallback or switch only when the host reliably exposes them; otherwise
record `unknown`. Do not claim provider or model diversity from an intended
model identity or a silent fallback.
Model-authored self-report is not execution evidence. After conclusions are
fixed, prefer launcher-owned execution evidence such as a CLI header or
invocation receipt. If the reviewer cannot see it, keep the reviewer-authored
value `unknown` and attach the launcher evidence separately.

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
   any remaining open owner decision, the accepted input domain, any verified
   domain invariant, and explicitly unsupported inputs that affect acceptance.
   Owner authority defines product scope but does not prove a factual domain
   invariant. Do not infer authority from a builder commit message. If supplied
   requirement sources conflict and no authoritative owner decision resolves
   them, stop and ask the user; do not invent precedence. For a committed
   review, resolve `BASE` and `HEAD` to immutable commit SHAs before creating
   state, state both values, and put the resolved `$BASE..$HEAD` range in the
   neutral `GOAL`. If the full-change boundaries are ambiguous, ask the user.
   Never silently use `HEAD^`; use `HEAD^..HEAD` only when the user explicitly
   accepts a single-commit scope.
4. The launcher or user must not pre-create a standalone ADT review task. After
   the Independence preflight and read-only workspace orientation, the
   reviewer starts or connects to state itself. Set `WORKSPACE` to the selected
   target root and run
   `adt --workspace "$WORKSPACE" status`. Save the active task's durable kind
   as `TASK_KIND`. For a cold review, if `status` reports an open
   `kind=develop`, stop before reading `context`; do not resume or hand off that
   task as cold-review context. Require a separate review checkout that exposes
   the same immutable range, then use a fresh memory-clean session whose
   reviewer starts a standalone `kind=review` task with a neutral `GOAL`. An
   existing open `kind=review` may still use reviewer-to-reviewer handoff under
   the review embargo. Preserve `TASK_KIND=develop` only for explicitly
   non-cold review or repair validation of a handed-off development task.
   `status` is metadata-only: it must omit the goal, checkpoint notes, and
   completion summary. If a cold review receives any of them from `status`,
   stop as `independence-compromised`. If no task exists, or the current task is
   already completed, start a new one with
   `adt --workspace "$WORKSPACE" start --host "$HOST" --kind review --goal "$GOAL"`,
   set `TASK_KIND` to `review`; the reviewer retains the returned lease as
   `LEASE`. The reviewer starts only after the preflight and lets `GOAL`
   identify the artifact, resolved range, and review intent. If the invocation
   explicitly selects `economy`, `balanced`, `critical`, or `manual`, append
   `--profile "$PROFILE"`; otherwise keep the balanced default.
5. For a cold or independent review of an existing open `kind=review` task, run
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
- Establish that a proposed trigger belongs to the accepted input domain before
  treating it as a defect. Verify a claimed verified domain invariant against
  available repository or applicable platform evidence. A constructible
  out-of-domain counterexample must not enlarge the accepted contract; report a
  material unsupported or contradicted domain boundary instead of silently
  adding defensive requirements.
- When a removed, deprecated, or unavailable upstream value is replaced by a
  local derivation, treat semantic equivalence as a load-bearing factual
  invariant. Ordinary local calculations and refactors are outside this check
  unless they replace such an upstream value. Establish what the upstream value
  included and excluded from authoritative upstream specification, source, or
  targeted history independently of the candidate formula and tests. Tests that
  mirror the derivation do not establish equivalence. If equivalence cannot be
  established or the semantics differ, withhold acceptance unless the owner
  explicitly approves the semantic change.
- Inspect correctness, failure behavior, security and data risks,
  architectural fit, compatibility, and maintainability in proportion to the
  change. Check whether tests could pass while the requirement remains broken.
  For a bug-fix claim, independently re-derive the failure mechanism from the
  baseline and compare baseline and candidate at the same production-relevant
  seam, including framework or runtime behavior outside the diff. Preserve the
  failure's complete downstream disposition through its final framework or
  process boundary. Establish whether and when the final observer is reachable
  under relevant concurrency, shutdown, buffering, and framework lifecycle;
  eventual behavior after blocked work is released is not equivalent to prompt
  failure handling. A harness that catches the failure before a terminal
  observer changes an unhandled path and is not an equivalent counterfactual;
  account for all downstream observers and the signal cardinality. Compare the
  signal classification or handled state when it can change alerting or other
  operational meaning. When a safe focused baseline probe is available, run it
  at the final observer; source-only conjecture cannot establish whether the
  incident reproduces. Identify the observer as the exact runtime route and
  measurable outcome, not merely a destination, vendor, or subsystem. Treat a
  test that disables, replaces, or bypasses a
  load-bearing mechanism in that path as non-discriminating for the affected
  claim unless equivalence is demonstrated. A real dependency client does not
  establish equivalence when its load-bearing hooks or integrations are
  disabled, replaced, or bypassed; report the gap instead of accepting green.
  When one-time process-global initialization installs a load-bearing observer,
  prove at the measurement point that the observer is active and that the
  trigger reaches it; a successful initialization call or initialized registry
  alone is insufficient. Isolate baseline, candidate, and repeated cases from
  one another: restoring an outward hook while retaining process-global
  initialization or integration registry state is not a consistent reset.
  Prefer a fresh process when public teardown cannot restore both consistently;
  do not mutate non-public dependency internals to simulate teardown.
  If a candidate adds a reporting action while the same failure propagates to
  automatic reporting, enumerate every enabled reporting route, including
  direct SDK calls, logging integrations, framework hooks, and process hooks.
  A test that patches capture or flush and asserts only those calls is
  non-discriminating for final delivery, aggregate event cardinality, and
  handled classification. A real client exercised only around a directly
  invoked handler in the review process is not terminal-boundary evidence.
  Withhold acceptance unless a final-observer check either uses the production
  entry point with production-equivalent automatic hooks or the reviewer
  independently demonstrates equivalence of a narrower check across
  initialization, every automatic route, ordering, classification, and
  propagation or exit, while measuring exact aggregate event cardinality from
  all enabled routes. A fake or in-memory transport is acceptable. `>= 1`,
  non-empty, and per-route call assertions do not establish absence of
  duplication or loss. Review proof scaffolding as part of the candidate:
  dependency of the current harness is not evidence that a production seam is
  load-bearing. Compare a simpler equally discriminating test-only seam before
  accepting production configuration, public interfaces, or dependencies added
  only for verification.
- If the reproduced baseline already satisfies the claimed outcome or does not
  reproduce the reported incident, the candidate is not causal evidence for
  that bug-fix claim. Do not invent a historical or configuration explanation
  or silently reclassify the change as hardening to make it acceptable.
  Withhold acceptance until authoritative evidence establishes the failure
  mechanism, or the owner explicitly accepts the revised hardening goal and
  trade-off.
- Use native review tools and focused verification. Before declaring focused
  tests unavailable or settling for syntax-only checks, inspect already-ready
  repo-native runtimes: repository instructions and test targets, an existing
  environment associated with another checkout of the same repository, and an
  existing local image or container. Use one only if it runs the exact focused
  offline selector against the selected worktree's source without copying
  secrets or mutable runtime state. Do not install dependencies, build, or pull
  merely to fill a review gap. This bounded discovery does not authorize a
  broad suite or live-network smoke; report the exact residual coverage gap if
  no ready runtime works.
- Never copy a secret-bearing `.env` or credential-bearing runtime config into
  the review worktree. Use existing test fixtures or minimal dummy non-secret
  values, keep secrets out of tool output, and report the check as blocked when
  no safe focused setup exists.
- Do not modify code unless the user explicitly requests review-and-repair.
  Keep findings independent before beginning any repair.
- When review-and-repair is authorized, treat each finding as evidence about
  the candidate, not authority to enlarge the accepted task contract. Trace a
  repair to the accepted outcome or a repository constraint; an adjacent
  guarantee requires an owner decision. If the repair materially adds state,
  concurrency coordination, or dependence of correctness or proof on
  non-public dependency behavior, keep that complexity only when repository
  evidence shows it is load-bearing for the accepted outcome; otherwise use a
  simpler contract-preserving repair or discard it.
- Report actionable findings first, ordered by severity. Give a precise
  location, impact, triggering conditions, and supporting evidence. If there
  are no findings, state residual coverage gaps and uncertainty explicitly.

## Preserve a cold second review

When the user requests two-model or independent review, use this manual MVP
protocol:

1. Reviewer A forms its findings in its native session. Keep those findings out
   of `adt` state and do not pass them, suspected locations, severities, or
   proposed fixes to reviewer B. Keep reviewer A's model or fallback evidence
   out of the neutral handoff until B has fixed its conclusions.
2. Before handoff, record only a neutral note containing authoritative intent,
   known owner supersessions, exact scope and snapshot, accepted criteria, the
   accepted input domain, any verified domain invariant, explicitly unsupported
   inputs, and permitted checks. Then use
   `handoff --host "$HOST" --lease "$LEASE" --to "$OTHER_HOST"`. Tell the user
   not to copy A's findings into the next session.
3. Start a fresh session in host B and run the Independence preflight before
   invoking this skill. B reads the neutral context and commits its own findings
   before seeing A's conclusions. If A's findings leaked into context, stop and
   label the attempt `independence-compromised`.
4. After B has stated its conclusions, record B's reviewed scope, checks, and
   findings with `checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"`.
5. Only then reveal A's report, disclose and merge A's model or fallback
   evidence during adjudication, and compare agreements, unique findings, and
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

A standalone `ACCEPT` is one judgment path, not a trusted or final acceptance.
When the accepted contract or owner requires a trusted or multi-path result,
all required independent paths must fix their conclusions before disclosure,
and any material disagreement must be adjudicated from evidence. A standalone
review report may still complete without making that stronger claim.

A verdict must follow its evidence. If a review establishes that an explicit
acceptance criterion is violated, the verdict must withhold acceptance; it
must not downgrade that violation to a follow-up unless the owner explicitly
waives or supersedes the criterion. Severity wording or a qualified-pass label
does not change that boundary.

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
