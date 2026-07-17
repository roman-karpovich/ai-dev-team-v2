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

## Inspect and control a task

Commands return JSON. Keep the lease returned by `start`, `resume`,
`checkpoint`, or `takeover`; every checkpoint rotates it.

```bash
adt --workspace "$WORKSPACE" status
adt --workspace "$WORKSPACE" context
adt --workspace "$WORKSPACE" list
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
