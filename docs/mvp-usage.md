# MVP usage

This MVP makes one development task resumable across Codex and Claude Code
without replacing either product's native system prompt, tools, planning,
subagents, review facilities, or workflows. The host you open is the current
executive; AI Dev Team records deterministic task boundaries around its work.

The MVP is intended for dogfooding on real repositories. It is not yet the
full VERIFY product, an automatic model router, or a release-safety claim.
Each task is bound to exactly one Git worktree. The skill performs read-only
orientation before creating state, so a launcher or knowledge repository is
not mistaken for the implementation repository. Multi-repository outcomes
must be split into bounded tasks; sibling repositories are never silently
edited outside the recorded snapshot.

During contract dogfooding, feature throughput is not a success metric. A
small immutable task or defect may be rerun after a contract change while it
still distinguishes a trustworthy result from a plausible false green. Each
run starts from a fresh inference context and the prior result remains hidden
until the new conclusion is fixed. Seek another task when the existing
fixtures no longer exercise the uncertainty being reduced, not merely to
produce novel code.

## Install

Clone this repository, enter its root, and install both host plugins and the
`adt` command:

```bash
make mvp-install
```

v2 owns the canonical `ai-dev-team` plugin name and is not installed alongside
v1. If the v1 plugin is still present, the normal target stops without
replacing it. Use the explicit migration target to uninstall the known v1
plugin and marketplace only after the selected v2 installs succeed:

```bash
make mvp-replace-v1
```

Install only one host when preferred:

```bash
make mvp-install-codex
make mvp-install-claude
```

Ensure the user-local executable directory used by the installer is on
`PATH`, then start a new Codex task or Claude Code session. Re-run the same
target after updating the checkout. The installer refuses to overwrite an
unrelated `adt` executable.

The marketplace is named `ai-dev-team-v2-local`; the product and command
namespace are `ai-dev-team`.

## Start in Codex

Open the target repository in Codex Desktop or start Codex CLI there. Invoke
the skill explicitly:

```text
$ai-dev-team:develop Implement the requested account export feature.
```

The skill starts or resumes the workspace task and then lets Codex use its
normal dialogue, planning, subagents, tools, and focused verification. Ordinary
coding requests do not opt into AI Dev Team state.

For a new or completed development task, the skill first performs read-only
worktree orientation, checks ADT status, and inspects the repository facts
needed to resolve the request without asking the owner for discoverable facts.
If repository work remains, it forms a compact neutral task contract and uses
it as the existing `--goal`. The durable contract contains only the desired
outcome and observable success, constraints and non-goals, verified repository
facts distinguished from explicit assumptions, and authoritative owner
decisions, waivers, or unresolved decisions. The host may challenge or
distinguish an owner-proposed solution, but it does not persist rejected
suggestions, model-selected implementation details, suspected locations,
proposed fixes, persuasive reasoning, prior findings, severities, or expected
conclusions. An approach enters the contract only when the owner explicitly
approves it as an authoritative decision. Empty parts are omitted; native
plan/build consumes this cold-review-safe continuity, and later neutral review
or handoff receives only that safe portion. This is not a new artifact or
taxonomy.

When acceptance depends on a domain boundary, the neutral contract includes the
accepted input domain, any verified domain invariant, and owner-approved
explicitly unsupported inputs. Discoverable invariants are verified from the
repository or applicable platform evidence; owner authority defines product
scope but does not prove a fact. A constructible out-of-domain counterexample
must not enlarge the accepted contract. If its domain membership is material
and unresolved, inspect the evidence or ask one focused owner decision before
adding defensive behavior.

Clear, bounded work proceeds in the same turn without a questionnaire,
approval ritual, or invented alternatives. Skip state only when observable
success is already satisfied and no repository work remains; report the
evidence. Repository evidence may correct a factual premise, but it must never
silently replace the owner's desired outcome. If corrected facts make that
outcome ambiguous or infeasible, present the evidence and ask the focused owner
decision. Missing required normative input requires one focused question before
starting state or editing; so does a case where a real owner decision materially
changes the product or risk. Only when that question resolves a material or
hard-to-reverse architectural fork does the host first present two genuinely
different viable approaches, concrete tradeoffs, and a recommendation.

An owner-supplied claim of an observed failure enters the incident path
regardless of whether the builder calls the work a bug fix, observability
hardening, or an added reporting call. Only the owner may revise the desired
outcome from incident repair to hardening. Preserve the existing failure policy
unless the owner explicitly changes it. A choice that changes exit or restart,
retry or skip, cursor or checkpoint advancement, transaction boundaries, or
partial-success behavior is normative and never a reversible assumption.

Re-derive the baseline through the final production-relevant observer,
including whether and when it is reachable under relevant concurrency,
shutdown, buffering, and framework behavior, and name that observer in the
verified facts before implementation. When the outcome depends on runtime
reporting, propagation, lifecycle, or cardinality, run a safe focused baseline
probe on the immutable pre-candidate snapshot before the first or any further
candidate edit. The probe uses the same terminal-boundary rules as candidate
verification: exercise the production entry point when hooks are load-bearing,
retain every enabled automatic reporting route, and measure exact aggregate
cardinality. A copied or handwritten harness that directly installs hooks or
initializes the downstream observer can support exploration, but it is not the
production entry point and cannot qualify this gate while the real
initialization path is load-bearing or unverified. Naming a destination or
reasoning from source is not a substitute for an available probe.

Calling the real library function from a harness does not make the harness the
production initialization path. When initialization is load-bearing, the
actual repository bootstrap must execute it; copying its arguments or
configuration into probe code is still a reimplementation and cannot qualify
the incident gate. A fake terminal transport remains acceptable only when the
actual repository bootstrap reaches a supported replacement seam without the
probe recreating that bootstrap.

Matching the reported outward symptoms is not incident reproduction when a
probe introduced an added causal precondition. Each added causal precondition
must be independently established as applicable to the reported incident from
inspected repository, deployment, or incident evidence. An injected fault may
stand in for an established trigger, but a synthetic hang, timeout, signal,
kill, or supervisor action introduced only to force the outcome remains
exploratory evidence and cannot qualify the incident gate or verify that
hypothesized cause.

This gate applies to new, resumed, taken-over, and handed-off work. It blocks
candidate edits, not durable state: a longer investigation may start under a
neutral goal that marks causality unverified, then checkpoint its probe plan,
evidence gap, provenance, and results. On resume, reuse qualifying checkpoint
evidence only when it identifies the immutable snapshot, observer, exercised
route, measured result, and provenance. Otherwise probe before further edits;
freeze any existing candidate while recovering its pre-candidate baseline.

If the probe is unavailable or does not reproduce the incident, mark the causal
mechanism unverified and ask the owner to choose between further investigation
and an explicitly revised hardening goal before source or test edits. An answer
to an operational fact question does not authorize a different goal; the owner
must explicitly revise the desired outcome. If the session ends awaiting that
decision, checkpoint the evidence and pause the task instead of retaining an
active lease. A worker, callback, future, command, or framework boundary is not
final when production has a later automatic observer; catching there changes
the path. Inspect targeted history plus runtime and supervisor configuration
first. `Fail-fast` or `restart` does not silently define a timing or termination
SLA. A fix that bypasses normal stack unwinding or cleanup, or changes the fate
of sibling work, requires an explicit owner decision. If multiple viable
contracts remain, present the evidence and ask one focused owner decision before
candidate edits.

Evidence from a sibling repository, ignored symlink target, deployment
snapshot, or runtime configuration outside the selected worktree is external
operational evidence. Record its provenance and freshness; it is not a
verified repository fact from the task snapshot.

Use `verified` only for facts directly observed in the selected snapshot or
demonstrated by concrete inspected repository and applicable runtime evidence.
Counterfactual claims about concurrency, shutdown, buffering, reporting loss,
or sibling fate remain assumptions until exercised; they cannot justify source
edits or expand observable success.

For behavior-changing code, prefer a focused failing test first. Reproduce the
defect at the narrowest deterministic seam that still includes every
load-bearing automatic downstream observer. For an incident fix, compare
baseline and candidate at the same final observer, including complete
downstream disposition, reachability, timing, and signal cardinality. Assert
the observable outcome plus relevant persistence, propagation, or process
lifecycle. When signal classification or handled state affects operational
behavior, assert it as well as cardinality. A new mock or log call alone is
insufficient evidence when those semantics matter; replacing the mechanism
that performs the claimed outcome proves only the local call unless
production-equivalent behavior is separately demonstrated. A real dependency
client remains non-discriminating when its load-bearing hooks or integrations
are disabled, replaced, or bypassed.

When one-time process-global initialization installs a load-bearing observer,
prove at the measurement point that the observer is active and that the
trigger reaches it; a successful initialization call or initialized registry
alone is insufficient. Isolate baseline, candidate, and repeated cases from
one another: restoring an outward hook while retaining process-global
initialization or integration registry state is not a consistent reset.
Prefer a fresh process when public teardown cannot restore both consistently;
do not mutate non-public dependency internals to simulate teardown.

When a candidate adds reporting while the same failure still reaches automatic
reporting, enumerate every enabled route, including direct SDK calls, logging
integrations, framework hooks, and process hooks. Use the lowest-cost seam that
remains discriminating. Drive the production entry point when framework
bootstrap or process lifecycle is load-bearing, or when equivalence of a
narrower final-observer harness cannot be demonstrated. The narrower harness
must preserve production initialization, automatic hooks, ordering,
classification, exact aggregate cardinality, and propagation or exit; a fake
or in-memory transport is sufficient. A real client around a directly invoked
handler, `>= 1`, non-empty, and per-route call assertions prove only partial
observability.

Review proof scaffolding separately from the outcome it measures. Dependence of
the current harness does not make a production seam load-bearing. Do not add
production configuration, public interfaces, or dependencies solely for
verification when a simpler equally discriminating test-only seam exists. When
no such equivalent preserves the proof boundary, record why the production
seam is necessary and keep it minimal.

A review finding is evidence about the candidate, not authority to enlarge the
accepted task contract. Before repair, trace it to the accepted outcome or a
repository constraint. An adjacent guarantee requires an owner decision. If an
in-scope repair materially adds state, concurrency coordination, or dependence
of correctness or proof on non-public dependency behavior, compare simpler
contract-preserving alternatives and keep the complexity only when repository
evidence shows it is load-bearing for the accepted outcome; otherwise reshape
or discard it.

Never copy a secret-bearing `.env` or credential-bearing runtime config into a
worktree to run a check. Use project fixtures or minimal dummy non-secret
values, keep secrets out of tool output, and report the check as blocked when
no safe focused setup exists.

Before reporting focused verification as blocked or settling for syntax-only
checks, inspect already-ready repo-native runtimes: documented test targets, an
existing environment associated with another checkout of the same repository,
or an existing local image or container. Use one only when it runs the exact
focused offline selector against the selected worktree's source without
copying secrets or mutable runtime state.

Before asking to commit or open a PR, the builder always states whether
independent review ran. Missing review blocks completion only when the selected
assurance profile, accepted task contract, or owner requires it. In that case
the result is an implementation checkpoint and the development task remains
active. Freeze the candidate as an immutable range and supply an invocation for
a fresh memory-clean session in a separate review checkout that exposes the
same immutable range. The cold reviewer must stop before reading `context` from
the open development task and instead start a standalone `kind=review` task
with a neutral `GOAL`. Otherwise completion may proceed after proportionate
verification while disclosing that review did not run. Green tests or a
builder checkpoint must not imply independent acceptance.

When the accepted task contract or owner requires a trusted, full-cycle, or
two-model result, one reviewer is insufficient. Required independent paths
form conclusions before disclosure, and material disagreement is adjudicated
from evidence before acceptance.

Builder-spawned subagents and repeated review passes inside the builder's
active session may advise the implementation, but they do not count as
independent judgment paths. A counted path starts in a fresh preflighted
session, receives only neutral context, and fixes its conclusion under the
review embargo. A two-model claim additionally requires evidence of distinct
actual models.

For a standalone cold review, use a one-off Codex CLI launch that disables both
memory directions before the session starts. It does not edit global config.
For a linked worktree, the narrow additional writable root lets ADT update its
own ledger without granting the whole common Git directory:

```bash
WORKSPACE=/path/to/worktree
ADT_STATE_ROOT="$(git -C "$WORKSPACE" rev-parse --path-format=absolute --git-common-dir)/ai-dev-team"
codex -C "$WORKSPACE" \
  --add-dir "$ADT_STATE_ROOT" \
  -c 'memories.use_memories=false' \
  -c 'memories.generate_memories=false'
```

For a one-off Claude Code CLI cold review, disable auto-memory only for that
process and avoid session persistence; this does not change global memory
configuration:

```bash
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \
  claude -p --model claude-opus-4-8 --no-session-persistence \
  "$(cat REVIEW_PROMPT.md)"
```

Do not pre-create ADT state for a standalone cold review. The reviewer performs
the independence preflight, resolves the review scope, and starts its own task.
The invocation is the neutral review brief. When known owner supersessions
exist, include the authoritative owner, the exact old and new requirement or
value, the superseded source or decision, and any remaining open decision. Do
not call an older source authoritative by itself. Also carry the accepted input
domain, every verified domain invariant, and explicitly unsupported inputs that
affect acceptance. The reviewer verifies a material domain claim from available
evidence, but an out-of-domain counterexample must not enlarge the accepted
contract. Then invoke the reviewer with an explicit full feature range:

```text
$ai-dev-team:review Review <BASE>..<HEAD> against the current accepted requirements. Owner decision: <old requirement> was superseded by <new requirement>.
```

Use `HEAD^..HEAD` only when the accepted scope is explicitly one commit. Before
reporting focused tests as unavailable, the reviewer checks already-ready local
repo runtimes, including an existing image or container; it does not install,
build, pull, or widen the run to broad or live-network smoke for that purpose.

## Start in Claude Code

### Choose a Claude model

Choose the model before exposing repository material when possible, then start
Claude Code in the target repository. Use the full pinned ID so later evidence
is attributable; short aliases are only interactive conveniences:

```bash
claude --model claude-opus-4-8
claude --model claude-fable-5
```

The current manual starting guidance is Opus 4.8 for bounded, well-specified,
or routine work, and Fable 5 for highest-complexity, long-horizon,
architecture-wide, or high-ambiguity work. The owner's explicit choice
overrides this guidance, subject to host availability and the applicable data
policy. Host, model, task complexity, and assurance profile are independent;
`critical` expresses the required assurance, not a Fable selection. AI Dev
Team has no automatic model router or silent/API fallback, and profiles never
route models.

Check Fable availability and data-policy eligibility before repository
exposure. If the selected Claude model is unavailable, ineligible under the
applicable policy, or refuses the work, stop and return control to the owner
for a visible manual choice. Do not restart a simple task already running in
Fable merely to downgrade. If Opus is materially underpowered for a frontier
task, recommend a fresh Fable session before ADT state or artifact exposure;
the owner may instead accept a visible Opus continuation as a degraded
tradeoff. Record the actual model and any visible fallback or switch only when
the host reliably exposes them; otherwise record `unknown`. This is execution
evidence in existing checkpoints and reports, not a new CLI option, state
field, or `GOAL` field.
Model-authored self-report is not execution evidence. After conclusions are
fixed, prefer launcher-owned execution evidence such as a CLI header or
invocation receipt. If the reviewer cannot see it, keep the reviewer-authored
value `unknown` and attach the launcher evidence separately.

Invoke the namespaced skill:

```text
/ai-dev-team:develop Implement the requested account export feature.
```

Claude remains free to use its native workflows and subagents. For review:

```text
/ai-dev-team:review Review <BASE>..<HEAD> against its stated goal.
```

## Hand off between hosts

Handoff is deliberately manual in the MVP. Use it to transfer task continuity
or request non-cold validation. It is not the path from an implementation
checkpoint to a cold review; that path uses the separate standalone review
checkout described above. Ask the current host to create a checkpoint and hand
the task to the other host. For example:

```text
Checkpoint the current increment and hand it to Claude to continue the task.
```

When an owner changed a requirement, the checkpoint identifies the
authoritative owner, the exact old and new requirement or value when known, the
superseded source or decision, and any remaining open owner decisions. The
final value alone is insufficient continuity.

Then close or leave the current session, open a fresh Claude Code session in
the same repository, and run:

```text
/ai-dev-team:develop Continue the handed-off task from its checkpoint.
```

The reverse direction works the same way: ask Claude to hand off to Codex,
then open a fresh Codex task and invoke `$ai-dev-team:develop` or
`$ai-dev-team:review`.

The plugin never launches the other provider automatically. This keeps quota,
permissions, native UX, and the point of human control visible. A handoff moves
durable task context, not hidden reasoning or a provider transcript.
Reviewer-to-reviewer handoff of an existing open `kind=review` remains valid
under the cold-review embargo below.

## Run a two-model cold review

The MVP can exercise the project's central review idea, but result isolation is
manual:

1. Ask reviewer A to inspect the authoritative intent, snapshot, and diff.
2. Keep A's findings in that native session. Before handoff, write only a
   neutral checkpoint containing the intent, exact scope and snapshot,
   acceptance criteria, known owner supersessions, the accepted input domain,
   verified domain invariants, explicitly unsupported inputs, and permitted
   checks. Do not include findings, suspected files, severities, fixes, or
   reviewer A's model or fallback evidence until B has fixed its conclusions.
3. Hand off and open a fresh session in provider B. Before inspecting the
   artifact, check the context already supplied by the host for prior findings,
   suspected locations, severities, fixes, or expected conclusions. For Codex,
   use the same one-off CLI launch above so both memory settings are disabled
   before the session starts. The skill performs the same check on any existing
   ADT context before resume. Do not paste A's output into the session.
4. Let B state and checkpoint its own conclusions.
5. Only after B's report is fixed, disclose and merge A's model or fallback
   evidence during adjudication, compare the two reports, and resolve
   disagreements from repository evidence.

A standalone `ACCEPT` remains one judgment path, not a trusted or final
acceptance. A trusted result exists only after every declared independent path
has completed and material disagreement has been adjudicated.

If reviewer B sees A's conclusions before forming its own, label the run
independence-compromised and restart from neutral context. This MVP has no
sealed-results store, so it cannot enforce the embargo mechanically. The result
is manually independent only when this discipline is followed. Telling B to
ignore conclusions it has already seen does not restore independence.

## Return a review to repair

When a reviewer receives a handed-off `kind=develop` task and finds an
unresolved material issue that requires repair or withholds acceptance, it
checkpoints the finding and must leave the development task active. It asks the
user for explicit repair or handoff direction instead of completing the task.
The development task completes only after its requested goal and acceptance
criteria are satisfied and no repair-blocking findings or open owner decisions
remain. A standalone `kind=review` task may complete when its report is done,
even when the report concludes HOLD.

Once findings have been recorded in a development task, a later review of that
same task is repair validation, not a cold review. For a cold oracle after the
known repairs are finished, complete the bounded repair task, then open a fresh
memory-clean session and invoke a standalone review with a neutral goal. That
task completion records the repair phase, not release approval. If the cold
review concludes HOLD, start the next bounded development task from its
adjudicated findings.

## Pause and resume

Tell the active host to pause at a safe boundary when work is interrupted:

```text
Checkpoint what is established and pause this task because the API contract is pending.
```

After new information arrives, open either the owning host or the host named by
a handoff and invoke the relevant skill again. The skill inspects status and
context before continuing. Repository drift is reported; accepting it requires
an explicit decision after inspection. Do not re-form or re-approve the task
contract on resume by default; reassess it only when drift or new information
invalidates it. Later owner changes use the existing exact supersession
checkpoint convention.

## Inspect state directly

The skills normally run these commands, but they are also useful in a terminal:

```bash
adt --workspace . status
adt --workspace . context
adt --workspace . list
```

State lives under Git's common directory, keyed by worktree. A snapshot keeps
the HEAD, staged and unstaged digest, untracked-file digest, and a bounded
status/path summary; it does not copy repository file bodies or patches into
the task ledger. Drift errors include the checkpoint and live summaries so the
host can identify the affected paths before asking to accept the new snapshot.
`status` returns neutral control metadata and omits the goal, checkpoint notes,
and completion summary; `context` adds that continuity text. This lets a cold reviewer decide
whether to start a standalone review without first ingesting conclusions from a
completed task.

The complete MVP command surface is:

```text
adt --workspace PATH start --host HOST --kind KIND --profile PROFILE --goal TEXT
adt --workspace PATH status
adt --workspace PATH context
adt --workspace PATH list
adt --workspace PATH checkpoint --host codex --lease LEASE_ID --note TEXT
adt --workspace PATH takeover --host codex --reason TEXT
adt --workspace PATH pause --host codex --lease LEASE_ID --reason TEXT
adt --workspace PATH handoff --host codex --lease LEASE_ID --to claude
adt --workspace PATH resume --host claude
adt --workspace PATH resume --host claude --accept-drift
adt --workspace PATH complete --host claude --lease LEASE_ID --summary TEXT
adt review-gate --bundle BUNDLE_DIRECTORY
```

Use `codex` or `claude` for host-valued arguments. Commands return JSON on
success and failure so the host can reason from explicit state. `--kind` is
`develop` or `review`; `--profile` is `economy`, `balanced`, `critical`, or
`manual`. Both are optional, with development and balanced defaults.
`start`, `resume`, `checkpoint`, and `takeover` return the current lease ID.
Supply it on active mutations; every successful checkpoint renews it. Status
and context omit the ID so another same-host session cannot silently join the
task. If a session was lost, approve an explicit `takeover`; it rotates the ID
and records the reason, fencing the abandoned session before work continues.
This is cooperative concurrency fencing, not an authentication boundary
against a local process that deliberately reads Git's private state.

In this MVP, `kind` and `profile` are durable intent labels only. They do not
yet auto-route models, spend quota, or mechanically enforce different review
gates.

## Validate a cold-review evidence bundle

The experimental conformance slice can validate a manually assembled bundle
without a Git worktree or ADT task state:

```bash
adt review-gate --bundle ./review-bundle
```

The checked-in contract is
`conformance/portable-cold-review-contract-v0.md`. The command verifies every
referenced exact-byte digest before parsing model results, validates closed
work-order, result, and launcher-receipt shapes, checks cross-object bindings,
and emits only `REPORT_ONLY` or `HOLD`. `REPORT_ONLY` is not acceptance or
release approval. The command does not launch reviewers, prove the launcher's
attestations, adjudicate findings, or authorize release. The bundle manifest
provides integrity after composition, not authenticity against an actor able
to reseal it.

## What to evaluate

Use the MVP on bounded, existing tasks and note:

- whether the host challenged weak requirements without adding ceremony;
- whether checkpoints were sufficient after interruption or host switching;
- whether native Codex and Claude workflows remained useful;
- whether review found issues not encoded by the builder's tests;
- where the state model was confusing or too restrictive;
- latency, quota use, and verification cost.

Do not treat a successful handoff or green tests as trusted-review evidence by
itself. Cold-review isolation, typed evidence, backend qualification,
adjudication, and release gates remain later product slices.

## Troubleshooting

- If `adt` is unavailable, run the appropriate `make mvp-install` target from
  the checkout and start a new host session.
- If the task belongs to the other host, return there and request a handoff;
  do not force ownership through local file edits.
- If resume reports drift, inspect the repository change before explicitly
  accepting it.
- If updated skills are not visible, reinstall and start a new task or session
  so the host reloads plugin content.
