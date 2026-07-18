---
name: develop
description: Run a controlled, resumable native coding task with durable checkpoints and explicit handoff. Use only when the user explicitly invokes $ai-dev-team:develop in Codex or /ai-dev-team:develop in Claude Code; never activate for an ordinary coding request.
---

# Develop

Keep the active Codex or Claude session as the native executive. Add durable
task boundaries without replacing its planning, tools, dialogue, subagents, or
repository instructions. Do not launch another provider automatically.

All `references/...` locators below resolve from the installed plugin root.

## Route references

| Trigger | Resource | Boundary |
| --- | --- | --- |
| `host:claude` | `references/claude-runtime.md` | `before:repository-exposure\|adt-state\|editing` |
| `always` | `references/task-lifecycle.md` | `after:claude-if-triggered;before:adt-state\|mutation` |
| `depends-on:auto-reporting\|framework-lifecycle\|process-lifecycle\|termination\|propagation\|bootstrap\|event-cardinality` | `references/incident-observability.md` | `before:task-contract\|candidate-edit` |
| `acceptance:input-domain\|upstream-replacement:removed,deprecated,unavailable->local-derivation` | `references/semantic-boundaries.md` | `before:task-contract` |
| `check:executes-source\|artifact\|runtime` | `references/verification-environments.md` | `before:check-execution\|result-interpretation` |
| `verification:unavailable-dependency\|runtime\|production-bootstrap\|environment-equivalence` | `references/verification-environments.md` | `before:verification-selection` |

`|` joins alternatives or boundary members; `;` sequences boundaries from
left to right.

## Establish the task

1. Perform the minimum read-only orientation needed to identify the target
   worktree, then follow the lifecycle reference and inspect `status`.
2. If no open task exists, inspect enough repository evidence to resolve
   discoverable facts before asking the owner questions.
3. Form `GOAL` as a compact neutral contract: desired outcome and observable
   success, constraints and non-goals, verified facts separated from
   assumptions, and authoritative owner decisions or unresolved choices.
   Exclude proposed fixes, persuasive reasoning, prior findings, and expected
   conclusions. Preserve the owner's outcome when evidence corrects a premise.
4. Challenge only a material product, architecture, or risk fork. Investigate
   ordinary uncertainty and proceed with a stated reversible assumption. Ask
   one focused question for missing normative input; present alternatives only
   when the answer selects a hard-to-reverse fork.
5. Skip state only when observable success is already satisfied and no
   repository work remains. Otherwise start `kind=develop`; append an explicit
   `--profile` only when the user selected one.

On resume, takeover, or same-lineage handoff, use `context` for orientation but
re-check load-bearing conclusions. Do not re-form the durable contract unless
drift or new evidence invalidates it. Checkpoint later owner changes with the
authoritative owner, superseded decision, old and new values when known, and
remaining open decisions.

## Work natively

- Inspect before editing. Use the host's native planning, tools, delegation,
  and repository workflows rather than recreating them here.
- Prefer a focused failing test before behavior-changing code. Choose the
  smallest verification seam that can distinguish the required behavior from
  the relevant defect; a self-confirming mock or irrelevant green suite is not
  proof.
- Work in coherent increments. Reassess when evidence invalidates the plan,
  fixes repeat, scope grows, or exceptions accumulate. Replan, pause, reshape,
  or discard instead of defending sunk cost.
- Checkpoint established facts, artifact state, checks, owner decisions, and
  open questions. Keep notes neutral and concise.

## Close the task honestly

- Before pausing or same-lineage handoff, checkpoint enough evidence for a
  fresh session to continue without a transcript.
- Before completion, disclose whether independent review ran. When the owner,
  repository policy, or task contract requires it, freeze an immutable commit
  range and keep the development task active while fresh standalone cold paths
  run in separate checkouts; provide only neutral scope and acceptance input,
  never builder findings or transcript.
- Complete only after the requested outcome and focused discriminating checks
  are satisfied and no blocking owner decision remains. Completion records
  workflow state, not release authorization or trusted review.
- Report outcome, evidence, remaining risks, and next action. If blocked,
  checkpoint and pause instead of retaining an active lease while waiting.
