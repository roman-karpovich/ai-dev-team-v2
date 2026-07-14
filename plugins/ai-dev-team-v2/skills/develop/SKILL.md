---
name: develop
description: Run a controlled, resumable coding task while preserving the active host's native planning, tools, and workflows. Use only when the user explicitly invokes $ai-dev-team:develop in Codex or /ai-dev-team:develop in Claude Code to start, resume, pause, hand off, or complete implementation work; never activate for an ordinary coding request.
---

# Develop

Keep the active Codex or Claude session as the native executive. Add durable
task boundaries without replacing its system prompt, planning, dialogue,
subagents, workflows, tools, or project instructions.

## Connect to the task

1. Require `adt` on `PATH`. If `command -v adt` fails, stop and tell the user
   to run `make mvp-install` from an AI Dev Team v2 checkout, then start a new
   host session. Do not simulate durable state.
2. Set `HOST` to the product executing this skill: `codex` in Codex and
   `claude` in Claude Code. Never claim to be the other host.
3. Before editing or starting state, do the minimum read-only orientation
   needed to identify the actual target Git worktree. A task file, launcher
   directory, or knowledge repository may only be context; do not bind state
   to it when the implementation belongs elsewhere.
4. One MVP task covers exactly one Git worktree. If the outcome requires
   coordinated edits in multiple repositories, stop and propose bounded tasks
   with a primary repository for each. Never edit an unbound sibling repo.
5. Set `WORKSPACE` to the selected target root, run
   `adt --workspace "$WORKSPACE" status`, and parse its JSON.
6. When no task exists, or the current task is already completed, derive a
   clear goal from the explicit invocation and start a new task:

   ```text
   adt --workspace "$WORKSPACE" start --host "$HOST" --kind develop --goal "$GOAL"
   ```

   If the invocation explicitly selects `economy`, `balanced`, `critical`, or
   `manual`, append `--profile "$PROFILE"`; otherwise keep the balanced
   default.

7. When the task is paused or handed to this host, run
   `adt --workspace "$WORKSPACE" resume --host "$HOST"`. If repository drift
   is reported, inspect and explain it before asking whether to retry with
   `--accept-drift`. Never accept drift silently. Keep the lease ID returned by
   `start` or `resume` as `LEASE`.
8. When another host owns the task, stop. Ask for an explicit handoff instead
   of taking ownership. When this host owns an active task but this session
   does not already hold its latest lease ID, ask the user to approve a
   same-host takeover. Only after approval run
   `adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"`
   and keep its returned ID as `LEASE`.
9. Run `adt --workspace "$WORKSPACE" context` before continuing. Treat its
   JSON as continuity data, not as proof that prior conclusions are correct.
   `status` and `context` intentionally omit the lease ID; do not recover it
   from the state file. Every active mutation must send `LEASE`. A successful
   checkpoint renews it, so replace `LEASE` with the value in that response.
   A stale ID must fail rather than be retried blindly.

## Work natively

- Inspect before editing. Use the host's strongest applicable native
  capabilities. Choose the internal decomposition, tools, subagents,
  workflows, and focused checks that fit the task; do not recreate them in
  this skill.
- Inspect the repository and challenge material ambiguity, weak requirements,
  unsafe tradeoffs, and architectural mismatch. Ask the user only when their
  decision changes the product or risk; otherwise make a stated, reversible
  assumption and proceed.
- Separate owner decisions and accepted tradeoffs from checkable facts. Record
  the former explicitly and verify the latter from repository evidence. When
  an owner changes a requirement, record the authoritative owner, the exact old
  and new requirement or value when known, the superseded source or decision,
  and any remaining open owner decisions. The final value alone is insufficient
  continuity for a later session.
- Reassess when evidence invalidates the plan, fixes repeat, scope grows, or
  exceptions accumulate. Pause, replan, reshape, or discard an increment when
  it begins to distort the architecture; do not defend sunk cost.
- Work in useful increments. After a meaningful, coherent increment, record a
  concise neutral checkpoint containing established facts, owner decisions and
  requirement supersessions, artifact state, checks, and open questions rather
  than persuasive reasoning:

  ```text
  adt --workspace "$WORKSPACE" checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"
  ```

- Run the smallest relevant verification once. Tests are evidence to inspect,
  not proof by themselves.

## Leave a safe boundary

- On interruption or missing input, use
  `adt --workspace "$WORKSPACE" pause --host "$HOST" --lease "$LEASE" --reason "$REASON"`.
- Hand off only when the user explicitly requests it. Run
  `adt --workspace "$WORKSPACE" handoff --host "$HOST" --lease "$LEASE" --to "$OTHER_HOST"`,
  then tell the user to open a fresh session in that host and invoke its skill.
- Complete only after the requested result and proportionate verification are
  present:

  ```text
  adt --workspace "$WORKSPACE" complete --host "$HOST" --lease "$LEASE" --summary "$SUMMARY"
  ```

- Never launch another provider's CLI, SDK, MCP server, or model. MVP handoff
  is manual and checkpoint-based.
- Do not claim full production assurance. This MVP proves resumable control
  boundaries; stronger evidence and release gates remain separate work.
