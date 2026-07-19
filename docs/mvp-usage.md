# AI Dev Team v2 MVP quickstart

This experimental plugin keeps Codex or Claude Code as the native executive
while `adt` records durable task state. It is explicit opt-in: ordinary coding
and review requests do not activate it.

## Install

From this repository checkout, install both hosts or one host:

```bash
make mvp-install
make mvp-install-codex
make mvp-install-claude
```

Ensure `~/.local/bin` is on `PATH`, then start a fresh host session so it loads
the installed plugin.

## Develop

In Codex:

```text
$ai-dev-team:develop Implement replay-safe ingestion for this repository.
```

In Claude Code:

```text
/ai-dev-team:develop Implement replay-safe ingestion for this repository.
```

The skill identifies one target Git worktree, creates or resumes a neutral
task contract, uses the host's native workflow, and checkpoints useful
increments. It does not automatically call the other provider.

A short natural-language invocation is enough. When useful, add any of these
optional fields: `Outcome`, `Constraints`, `Done`, `Artifact target`, and
`Publication authority`. Omitted routine detail is investigated by the agent,
not returned as a form to fill out.

## Review

State an immutable review scope and whether the review must be cold or
independent. In Codex:

```text
$ai-dev-team:review Cold-review commits <base>..<head> against the accepted task contract.
```

In Claude Code:

```text
/ai-dev-team:review Cold-review commits <base>..<head> against the accepted task contract.
```

A cold path must begin in a fresh neutral session and separate review checkout.
The skill does not dispatch a second model. One clean review path is still not
trusted release acceptance.

## Dialogue and autonomous execution

For a nontrivial development task, the normal protocol is:

ORIENT -> discuss material decisions -> conversational confirmation ->
autonomous BUILD / VERIFY / bounded REPAIR -> CLOSEOUT + KB

The agent investigates repository context first, states its understanding of
the task's essence, and ensures the dialogue includes one bounded `grill me`
pass over material assumptions, risks, nuances, and genuine forks. Questions
and decisions already resolved in the current conversation count; the agent
does not repeat them. Say `grill me` explicitly to force a full pass even when
the request initially looks specified. Explicit small, reversible work skips
this ceremony unless requested.

After the dialogue, the agent synthesizes the resolved design and material
decision log in `task.md`, presents a compact decision brief, and accepts an
ordinary reply such as `да`, `го`, or `так`. The owner does not need to
line-review `task.md` as an approval form. The agent then implements, verifies,
and performs bounded repair within the confirmed authority. Ask again only when
new evidence reveals a genuine fork in product, architecture, scope, release
authority, or another hard-to-reverse choice. Investigable uncertainty is
resolved directly or handled with a stated reversible assumption.

Plain-text replies in the same task are answers or corrections; do not repeat
the skill invocation. The agent runs lifecycle commands during normal skill
use.

## Minimal durable artifacts

The baseline human bundle has two files: `task.md` holds the current effective
specification plus an append-only material decision log; `closeout.md` holds the
outcome, exact artifact references, regression evidence, independent-review
state, risks and rollout, links, and one next action. Terminal workflow status
is separate from release recommendation and publication authority.

Generate the privacy-minimized `adt report` JSON only when process analysis
needs it. Do not archive raw red/green logs by default. Add an ADR, runbook,
migration, review, or reproduction note only when that knowledge deserves an
independent durable home, then link it rather than duplicating it.

Write artifacts only to an explicit owner target or an existing in-worktree
KB/docs convention. Never invent a cross-repository write. If neither exists,
the agent supplies a copy-ready bundle and asks one focused routing question
before making a tracked write.

## Optional operator inspection

The agent owns these commands in normal skill use. For manual inspection or
recovery, commands return JSON. Keep the lease returned by `start`, `resume`,
`checkpoint`, or `takeover`; every checkpoint rotates it.

```bash
adt --workspace "$WORKSPACE" status
adt --workspace "$WORKSPACE" context
adt --workspace "$WORKSPACE" list
adt --workspace "$WORKSPACE" report
adt --workspace "$WORKSPACE" report --task "$TASK_ID" --output "$FILE"
adt --workspace "$WORKSPACE" checkpoint --host codex --lease "$LEASE" --note "$NOTE"
adt --workspace "$WORKSPACE" pause --host codex --lease "$LEASE" --reason "$REASON"
adt --workspace "$WORKSPACE" resume --host codex
adt --workspace "$WORKSPACE" takeover --host codex --reason "$REASON"
adt --workspace "$WORKSPACE" handoff --host codex --lease "$LEASE" --to claude --note "$NOTE"
adt --workspace "$WORKSPACE" complete --host codex --lease "$LEASE" --summary "$SUMMARY"
```

Use `--accept-drift` on `resume` only after inspecting and explicitly accepting
the reported worktree change. Use `claude` instead of `codex` when Claude Code
owns the current lease.

After a handoff, open a fresh session on the target host and invoke the same
skill explicitly:

```text
/ai-dev-team:develop Continue the handed-off task from its checkpoint.
$ai-dev-team:review Continue the handed-off review from its checkpoint.
```

## Portable review evidence

Validate a manually assembled experimental bundle with:

```bash
adt review-gate --bundle ./review-bundle
```

Read the canonical [conformance exercise](https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/conformance/portable-cold-review.md)
and [bundle contract](https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/conformance/portable-cold-review-contract-v0.md)
before producing evidence. `REPORT_ONLY` is not acceptance; `HOLD` exits 5.
The gate validates supplied evidence but does not launch reviewers, attest the
launcher, adjudicate findings, or authorize release.

## MVP limits

- State is cooperative fencing, not security against a local process that
  deliberately reads Git-private files.
- `kind` and `profile` are durable labels; they do not route models or enforce
  assurance automatically.
- Cross-provider handoff, cold-review isolation, and bundle composition remain
  manual.
- Completion records workflow state separately from release recommendation.
- This dogfood MVP is not the production VERIFY engine or a general workflow
  orchestrator.

For the full command lifecycle, state layout, and troubleshooting, read
[MVP operations](mvp-operations.md).
