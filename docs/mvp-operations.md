# MVP operations

This guide covers the local `adt` command surface and state lifecycle. Use the
[quickstart](mvp-usage.md) for installation and first invocation. Specialized
review and verification policy lives in the plugin references linked by each
skill; it is intentionally not repeated here.

During normal skill use the agent operates this command surface. The owner
uses the CLI directly only for optional inspection or recovery.

## Runtime values

Choose these values before issuing commands:

- `WORKSPACE`: the root of the one Git worktree bound to the task;
- `HOST`: `codex` or `claude`, matching the process executing the skill;
- `GOAL`: a non-empty neutral task contract;
- `LEASE`: the current lease ID from a successful mutating response.

Successful commands emit JSON on stdout; errors emit JSON on stderr. Do not
parse human messages or edit the state file directly.

## Command surface

Start a task:

```bash
adt --workspace "$WORKSPACE" start --host "$HOST" --kind develop --goal "$GOAL"
adt --workspace "$WORKSPACE" start --host "$HOST" --kind review --goal "$GOAL"
```

`--kind` defaults to `develop`. `--profile` accepts `economy`, `balanced`,
`critical`, or `manual` and defaults to `balanced`. These values are durable
labels only in the MVP.

Read state:

```bash
adt --workspace "$WORKSPACE" status
adt --workspace "$WORKSPACE" context
adt --workspace "$WORKSPACE" list
```

`status` omits goal, checkpoint notes, completion summary, and lease ID.
`context` includes continuity text but still omits the lease ID. `list` gives a
workspace task history summary.

Generate a process-analysis report from the current task or retained history:

```bash
adt --workspace "$WORKSPACE" report
adt --workspace "$WORKSPACE" report --task "$TASK_ID"
adt --workspace "$WORKSPACE" report --task "$TASK_ID" --output "$FILE"
```

The canonical `adt.pilot-run-report.v0` report is a closed, byte-deterministic
JSON projection containing only:

- task ID, kind, profile, and status;
- created, updated, and optional completed timestamps;
- counts for each checkpoint kind, inferred resumes, and takeovers;
- persisted latest snapshot HEAD, digest, dirty flag, total changes, and
  truncated changes.

The report is a privacy-minimized projection of persisted task state, not a
live worktree observation. It omits workspace root and ID, change paths, host
values, goal, summary, notes, reasons, lease data, and unobserved token, cost,
model, or review metrics. There is no `--include-text` mode. An unknown task ID
fails rather than falling back to the current task.

The command holds a shared state lock and does not update the ledger or capture
a live snapshot. Without `--output`, it writes no artifact. With `--output`, it
atomically publishes exactly the canonical report plus a final newline; stdout
still returns a success envelope and never echoes the machine-local output
path. Writing an output file after a terminal snapshot can itself dirty the
worktree; the report still describes the persisted latest snapshot.

Record an increment:

```bash
adt --workspace "$WORKSPACE" checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"
```

The response contains a new lease. Replace the previous value immediately.

Pause and resume:

```bash
adt --workspace "$WORKSPACE" pause --host "$HOST" --lease "$LEASE" --reason "$REASON"
adt --workspace "$WORKSPACE" resume --host "$HOST"
adt --workspace "$WORKSPACE" resume --host "$HOST" --accept-drift
```

Pause records a snapshot and releases ownership. Resume is allowed only for
the reserved host. Without `--accept-drift`, a changed worktree fails closed
and reports the expected and actual snapshot summaries.

Transfer ownership:

```bash
adt --workspace "$WORKSPACE" handoff --host "$HOST" --lease "$LEASE" --to "$TARGET" --note "$NOTE"
adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"
```

Handoff pauses and reserves the task for `TARGET`. Takeover is only for a new
session of the same host after explicit approval; it rotates the abandoned
lease and records why. It cannot seize a lease owned by another host.

Complete:

```bash
adt --workspace "$WORKSPACE" complete --host "$HOST" --lease "$LEASE" --summary "$SUMMARY"
```

Completion snapshots the worktree, clears the lease, and closes workflow
state. It does not authorize release. A completed task remains in history; a
later `start` creates a new task.

Validate portable review evidence:

```bash
adt review-gate --bundle "$BUNDLE"
```

This command does not need a Git workspace. Its normative input and output are
defined by the [portable cold-review bundle contract](https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/conformance/portable-cold-review-contract-v0.md).
`REPORT_ONLY` exits successfully but is not acceptance. `HOLD` emits structured
JSON and exits 5.

Validate exact outbound publication bytes:

```bash
adt publication-gate --destination-repo "$DESTINATION_REPO" \
  --input "$OUTBOUND_FILE" --patterns-file "$PATTERNS_FILE"
```

This command is local-only and needs no Git workspace. The destination owner is
the default GitHub trust domain. `--patterns-file` supplies case-insensitive
literals that the built-in link checks cannot infer; omit it only when the task
has no such cross-domain or private identity. `HOLD` exits 5, errors exit 3,
and success returns an ephemeral exact-byte receipt. The command never
publishes. Follow the
[publication boundary](https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/plugins/ai-dev-team-v2/references/publication-boundary.md)
for routing and retention rules.

## State and snapshots

State lives under the Git common directory and is keyed by worktree. This lets
linked worktrees keep separate ledgers while sharing the repository object
database.

A task snapshot binds the current commit and a digest of staged, unstaged, and
untracked changes with a bounded status/path summary. It does not store file
bodies or patches. The CLI validates the full retained state before every read
or mutation and writes updates atomically under its lock.

The lease is cooperative concurrency fencing. It prevents stale sessions from
mutating through the CLI, but it is not an authorization boundary against a
local process deliberately reading Git-private state.

## Typical lifecycle

1. Run `status` after read-only worktree orientation.
2. Resolve material decisions and accept conversational confirmation; let the
   agent maintain `task.md` rather than treating it as an approval form.
3. Start a new task or resume the paused task assigned to this host.
4. Run `context` after resume, takeover, or handoff.
5. Work natively and checkpoint coherent increments, rotating `LEASE` each
   time.
6. Pause when waiting, hand off when another host should continue, or complete
   when the task outcome is satisfied.
7. Produce `closeout.md`, keeping terminal state distinct from review verdict,
   release recommendation, and publication authority. Generate `adt report`
   only on demand.

For a standalone cold review, use a separate checkout and follow the direct
[cold-review reference](https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/plugins/ai-dev-team-v2/references/cold-independent-review.md)
before artifact or state exposure. For environment-specific verification, use
the reference selected conditionally by the active skill rather than adding
operational ceremony here.

## Troubleshooting

### `adt` is not found

Run the relevant install target from this checkout, ensure `~/.local/bin` is on
`PATH`, and start a fresh host session.

### `no_task` or `task_open`

Use `status` and `list` to distinguish an empty workspace from an existing open
task. Complete the open task before starting another; do not delete its state.

### `host_mismatch`

Return to the owning host or request an explicit handoff. Takeover cannot cross
hosts.

### `lease_conflict`

Stop the stale session. Use the renewed lease from the latest checkpoint, or
obtain approval for same-host takeover when the owning session is lost.

### `snapshot_drift`

Inspect the reported expected and actual changes. Resume with
`--accept-drift` only after the user explicitly accepts that new baseline.

### `state_corrupt` or `state_unavailable`

Do not hand-edit, truncate, or recreate the ledger. Preserve the diagnostic and
the state path, stop mutations, and repair the underlying file or filesystem
problem through a separately reviewed recovery action.

### `report_output_unavailable`

The requested report was not safely published, or publication landed but
directory durability could not be confirmed. Inspect the target without
assuming that retry is side-effect free; the error never exposes its path.

### Updated skill is not visible

Reinstall the plugin and open a new host session. Existing sessions may retain
already-loaded skill content.
