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
   `claude` in Claude Code. Never claim to be the other host. Host is not the
   model. For `HOST=claude`, resolve the Claude model boundary before
   repository orientation, ADT state, or editing when possible:
   - Follow the owner's explicit model choice, subject to host availability and
     the applicable data policy. Otherwise use the current manual guidance:
     Opus 4.8 for bounded, well-specified, or routine work; Fable 5 for
     highest-complexity, long-horizon, architecture-wide, or high-ambiguity
     work.
   - Model, task complexity, and assurance profile are independent. Do not
     infer the model from `--profile`; profiles never route models. Do not
     create an automatic router or silently fall back through a CLI, SDK, or
     API.
   - If the selected Claude model is unavailable, ineligible under the
     applicable policy, or refuses the work, stop and return control to the
     owner for a visible manual choice. If a simple task already runs in Fable,
     do not restart merely to downgrade. If Opus is materially underpowered for
     a frontier task, recommend a fresh Fable session before ADT state or
     repository exposure. The owner may explicitly accept a visible Opus
     continuation; record that degraded tradeoff.
3. Before editing or starting state, do the minimum read-only orientation
   needed to identify the actual target Git worktree. A task file, launcher
   directory, or knowledge repository may only be context; do not bind state
   to it when the implementation belongs elsewhere.
4. One MVP task covers exactly one Git worktree. If the outcome requires
   coordinated edits in multiple repositories, stop and propose bounded tasks
   with a primary repository for each. Never edit an unbound sibling repo.
5. Set `WORKSPACE` to the selected target root, run
   `adt --workspace "$WORKSPACE" status`, and parse its JSON.
6. When no task exists, or the current task is already completed, use the
   orientation and status evidence above, then perform the focused read-only
   inspection needed to verify load-bearing repository facts. Do not ask the
   owner for facts that can be discovered from the repository. Resolve the
   decision boundary before starting state:
   - Skip state only when observable success is already satisfied and no
     repository work remains. Report that evidence and do not start a task.
   - Repository evidence may correct a factual premise, but it must never
     silently replace the owner's desired outcome. If corrected facts make
     that outcome ambiguous or infeasible, present the evidence and ask the
     focused owner decision.
   - Clear, bounded work proceeds in the same turn without a
     questionnaire, approval ritual, or invented alternatives.
   - For missing required normative input, or when a real owner decision
     materially changes the product or risk, ask one focused question before
     starting state or editing.
   - If that question resolves a material or hard-to-reverse architectural
     fork, first present two genuinely different viable approaches with
     concrete tradeoffs and a recommendation, then ask it. Only this case
     requires the alternatives ceremony.
   - In an incident or bug fix, preserve the existing failure policy unless
     the owner explicitly changes it. A choice that changes exit or restart,
     retry or skip, cursor or checkpoint advancement, transaction boundaries,
     or partial-success behavior is normative and never a reversible
     assumption. Inspect targeted history plus runtime and supervisor
     configuration before changing that boundary. If multiple viable contracts
     remain, present the evidence and ask one focused owner decision before
     starting state or editing.
7. For the new-task path in step 6, before any edit, form a compact neutral
   task contract from the preserved owner intent, corrected factual premises,
   and repository evidence. Use the contract as the existing `--goal` value;
   it is no new artifact or taxonomy. Challenge may distinguish an
   owner-proposed solution from the desired outcome, but the durable `GOAL`
   must contain only this compact, neutral, outcome-level contract:
   - desired outcome and observable success;
   - constraints and non-goals;
   - verified repository facts distinguished from explicit assumptions; and
   - authoritative owner decisions, waivers, and unresolved decisions.

   Treat a sibling repository, ignored symlink target, deployment snapshot, or
   runtime configuration outside the selected worktree as external operational
   evidence. Record its provenance and freshness; it is not a verified
   repository fact from the task snapshot.

   Omit empty parts. The contract must exclude rejected suggestions,
   model-selected implementation details, suspected locations, proposed fixes,
   persuasive reasoning, prior findings, severities, and expected conclusions.
   Only when the owner explicitly approves an approach may it be recorded as
   an authoritative owner decision. Native plan/build consumes this neutral
   contract; later neutral review or handoff receives only this cold-review-safe
   portion. Do not create a separate challenge skill, task kind, CLI field,
   schema, workflow, file taxonomy, routing, or release gate. Set `GOAL` to this
   contract and start the task:

   ```text
   adt --workspace "$WORKSPACE" start --host "$HOST" --kind develop --goal "$GOAL"
   ```

   If the invocation explicitly selects `economy`, `balanced`, `critical`, or
   `manual`, append `--profile "$PROFILE"`; otherwise keep the balanced
   default.

8. When the task is paused or handed to this host, run
   `adt --workspace "$WORKSPACE" resume --host "$HOST"`. If repository drift
   is reported, inspect and explain it before asking whether to retry with
   `--accept-drift`. Never accept drift silently. Keep the lease ID returned by
   `start` or `resume` as `LEASE`.
9. When another host owns the task, stop. Ask for an explicit handoff instead
   of taking ownership. When this host owns an active task but this session
   does not already hold its latest lease ID, ask the user to approve a
   same-host takeover. Only after approval run
   `adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"`
   and keep its returned ID as `LEASE`.
10. After resume, takeover, or handoff, run
   `adt --workspace "$WORKSPACE" context` before continuing. A fresh `start`
   already returns the new task and does not need an immediate duplicate
   context read. Treat context JSON as continuity data, not as proof that prior
   conclusions are correct.
   `status` and `context` intentionally omit the lease ID; do not recover it
   from the state file. Every active mutation must send `LEASE`. A successful
   checkpoint renews it, so replace `LEASE` with the value in that response.
   A stale ID must fail rather than be retried blindly. For a resumed task, do
   not re-form or re-approve its contract by default. Reassess only when drift
   or new information invalidates it. Record later owner changes through the
   existing exact supersession checkpoint convention below.

## Work natively

- Inspect before editing. Use the host's strongest applicable native
  capabilities. Choose the internal decomposition, tools, subagents,
  workflows, and focused checks that fit the task; do not recreate them in
  this skill.
- Inspect the repository and challenge material ambiguity, weak requirements,
  unsafe tradeoffs, and architectural mismatch. Ask the user only when their
  decision changes the product or risk; otherwise make a stated, reversible
  assumption and proceed. The normative failure-policy boundaries above are
  never reversible assumptions.
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

  When the host reliably exposes the actual model, include it and any visible
  fallback or switch in the factual checkpoint or completion summary;
  otherwise record `unknown`. Never infer it from the requested model. This is
  execution evidence, not part of `GOAL`, and requires no new state field.

- For behavior-changing code, prefer a focused failing test first. Reproduce
  the defect at the closest deterministic production seam and assert the
  observable outcome plus relevant persistence, propagation, or process
  lifecycle. A new mock or log call alone is insufficient evidence when those
  semantics matter.
- Never copy a secret-bearing `.env` or credential-bearing runtime config into
  another worktree to run a check. Prefer project test fixtures or minimal
  dummy non-secret values, and keep secrets out of tool output and checkpoints.
  If no safe focused setup exists, report the check as blocked. On accidental
  exposure, stop, remove the copy, notify the owner, and redact local artifacts
  when authorized.
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
- Before asking to commit or open a PR, always state whether independent review
  ran. Missing review blocks completion only when the selected assurance
  profile, accepted task contract, or owner requires it. In that case call the
  result an implementation checkpoint, keep the task active, and, when the
  owner requests the manual review, use the handoff flow above and give the
  exact fresh review invocation. Otherwise completion may proceed after
  proportionate verification while disclosing that review did not run. Green
  tests or a builder checkpoint must not imply independent acceptance.
- Do not claim full production assurance. This MVP proves resumable control
  boundaries; stronger evidence and release gates remain separate work.
