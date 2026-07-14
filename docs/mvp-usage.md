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

Do not pre-create ADT state for a standalone cold review. The reviewer performs
the independence preflight, resolves the review scope, and starts its own task.
The invocation is the neutral review brief. When known owner supersessions
exist, include the authoritative owner, the exact old and new requirement or
value, the superseded source or decision, and any remaining open decision. Do
not call an older source authoritative by itself. Then invoke the reviewer with
an explicit full feature range:

```text
$ai-dev-team:review Review <BASE>..<HEAD> against the current accepted requirements. Owner decision: <old requirement> was superseded by <new requirement>.
```

Use `HEAD^..HEAD` only when the accepted scope is explicitly one commit. Before
reporting focused tests as unavailable, the reviewer checks already-ready local
repo runtimes, including an existing image or container; it does not install,
build, pull, or widen the run to broad or live-network smoke for that purpose.

## Start in Claude Code

Start Claude Code in the target repository and invoke the namespaced skill:

```text
/ai-dev-team:develop Implement the requested account export feature.
```

Claude remains free to use its native workflows and subagents. For review:

```text
/ai-dev-team:review Review <BASE>..<HEAD> against its stated goal.
```

## Hand off between hosts

Handoff is deliberately manual in the MVP. Ask the current host to create a
checkpoint and hand the task to the other host. For example:

```text
Checkpoint the current increment and hand it to Claude for an independent review.
```

When an owner changed a requirement, the checkpoint identifies the
authoritative owner, the exact old and new requirement or value when known, the
superseded source or decision, and any remaining open owner decisions. The
final value alone is insufficient continuity.

Then close or leave the current session, open a fresh Claude Code session in
the same repository, and run:

```text
/ai-dev-team:review Review the handed-off implementation independently.
```

The reverse direction works the same way: ask Claude to hand off to Codex,
then open a fresh Codex task and invoke `$ai-dev-team:develop` or
`$ai-dev-team:review`.

The plugin never launches the other provider automatically. This keeps quota,
permissions, native UX, and the point of human control visible. A handoff moves
durable task context, not hidden reasoning or a provider transcript.

## Run a two-model cold review

The MVP can exercise the project's central review idea, but result isolation is
manual:

1. Ask reviewer A to inspect the authoritative intent, snapshot, and diff.
2. Keep A's findings in that native session. Before handoff, write only a
   neutral checkpoint containing the intent, exact scope and snapshot,
   acceptance criteria, known owner supersessions, and permitted checks. Do not
   include findings, suspected files, severities, or fixes.
3. Hand off and open a fresh session in provider B. Before inspecting the
   artifact, check the context already supplied by the host for prior findings,
   suspected locations, severities, fixes, or expected conclusions. For Codex,
   use the same one-off CLI launch above so both memory settings are disabled
   before the session starts. The skill performs the same check on any existing
   ADT context before resume. Do not paste A's output into the session.
4. Let B state and checkpoint its own conclusions.
5. Only after B's report is fixed, compare the two reports and adjudicate
   disagreements from repository evidence.

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
an explicit decision after inspection.

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
