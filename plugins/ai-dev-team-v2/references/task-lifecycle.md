# ADT task lifecycle

Read this provider-neutral reference before any ADT state read or mutation,
after any required cold-review and host-runtime preflight.

## Bind state truthfully

- Require `adt` on `PATH`; otherwise stop, request MVP installation, and use a
  fresh host session. Never simulate state.
- Set `HOST=codex` in Codex or `HOST=claude` in Claude Code. Bind `WORKSPACE` to
  the one Git worktree that owns the task; split cross-repository work.
- Inspect `status` before starting or reconnecting. Start only when no open task
  exists. Keep `kind=develop` for implementation and `kind=review` for a
  standalone review.

## Fence every mutation

Keep the lease returned by `start`, `resume`, or `takeover`. Send it on every
active mutation. A successful checkpoint rotates the lease, so immediately
replace `LEASE` with the returned value. `status` and `context` omit lease IDs;
never recover one from the state file or retry a stale lease blindly.

Resume only a paused task reserved for this host. If drift is reported, inspect
and explain the changed snapshot; use `--accept-drift` only after explicit
approval. Read `context` after resume, takeover, or handoff and treat it as
continuity, not proof.

Use handoff to pause and reserve a task for another host in the same task
lineage. If this host still owns an active task but its session and lease were
lost, obtain explicit approval for same-host takeover and record the reason.
Takeover cannot seize another host's task.

Checkpoint a coherent increment before pausing or handing off. Pause rather
than retain an active lease while waiting. Complete only when that task's
closeout rules are satisfied. Completion closes workflow state; it is never a
release recommendation or authorization.

## Canonical task-state command forms

These are the canonical task-state forms used by the skills, not exhaustive CLI
help. An optional `start --profile "$PROFILE"` records a durable label when the
user selects one. `review-gate` is a launcher/composer command used only after
at least two paths are sealed. It is outside the task lifecycle and deliberately
omitted here; a standalone reviewer never invokes it or requests its bundle.

Use JSON responses as the source of task and lease values:

```text
adt --workspace "$WORKSPACE" status
adt --workspace "$WORKSPACE" list
adt --workspace "$WORKSPACE" start --host "$HOST" --kind develop --goal "$GOAL"
adt --workspace "$WORKSPACE" start --host "$HOST" --kind review --goal "$GOAL"
adt --workspace "$WORKSPACE" resume --host "$HOST"
adt --workspace "$WORKSPACE" resume --host "$HOST" --accept-drift
adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"
adt --workspace "$WORKSPACE" context
adt --workspace "$WORKSPACE" checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"
adt --workspace "$WORKSPACE" pause --host "$HOST" --lease "$LEASE" --reason "$REASON"
adt --workspace "$WORKSPACE" handoff --host "$HOST" --lease "$LEASE" --to "$TARGET" --note "$NOTE"
adt --workspace "$WORKSPACE" complete --host "$HOST" --lease "$LEASE" --summary "$SUMMARY"
```
