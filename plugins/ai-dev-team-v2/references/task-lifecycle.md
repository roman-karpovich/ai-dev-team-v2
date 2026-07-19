# ADT task lifecycle

Read this provider-neutral reference before any ADT state read or mutation,
after any required cold-review and host-runtime preflight.

## Bind state truthfully

- Require `adt` on `PATH`; otherwise stop, request MVP installation, and use a
  fresh host session. Never simulate state.
- During normal skill use, the agent runs lifecycle commands; do not ask the
  owner to operate the CLI.
- Treat plain-text replies in the same task as answers, corrections, or
  confirmation without requiring another skill invocation.
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

## Keep durable artifacts minimal

Maintain two baseline human artifacts at an owner-selected destination or an
existing in-worktree KB/docs convention:

- `task.md` contains the current effective specification and an append-only log
  of material decisions. Synthesize and maintain it from dialogue; it is not an
  approval form. Record routine investigation only when it changes the spec.
- `closeout.md` records outcome, exact artifact references, regression coverage
  and evidence, independent-review state, risks and rollout, links, and one next
  action. State terminal workflow status separately from release recommendation
  and publication authority.

Record the failing behavior and regression-test identity plus the final gate.
Do not archive raw red and green logs by default. Keep raw logs only when they
are necessary evidence. Create ADRs, runbooks, migration notes, review notes,
or reproduction notes only when the knowledge is independently durable; link
them instead of duplicating them.

Never invent a cross-repository write. Outside a counted cold path, if neither
the owner nor an existing in-worktree convention authorizes a durable
destination, provide a copy-ready `task.md` and `closeout.md` bundle and ask one
focused routing question before a tracked write. A counted cold work order must
provide its sealed artifact destination; if it does not, return a terminal gap
or `HOLD` without contact or a tracked write. Generate the privacy-minimized
machine report only on demand; do not auto-write it or add prose to it.

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
adt --workspace "$WORKSPACE" report
adt --workspace "$WORKSPACE" report --task "$TASK_ID"
adt --workspace "$WORKSPACE" report --task "$TASK_ID" --output "$FILE"
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
