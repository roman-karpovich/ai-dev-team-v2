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
   - An owner-supplied claim of an observed failure triggers the incident path
     regardless of the builder's terminology, requested implementation, or
     attempt to restate the work as observability hardening or adding a call.
     Only an explicit owner decision may revise the desired outcome from
     incident repair to hardening.
   - In an incident or bug fix, preserve the existing failure policy unless
     the owner explicitly changes it. A choice that changes exit or restart,
     retry or skip, cursor or checkpoint advancement, transaction boundaries,
     or partial-success behavior is normative and never a reversible
     assumption. Re-derive the baseline failure mechanism through its final
     production-relevant observer, including whether and when that observer is
     reachable under relevant concurrency, shutdown, buffering, and framework
     behavior. Name that observer in the verified facts before implementation.
     This is a lifecycle-wide qualification gate for new, resumed, taken-over,
     and handed-off tasks. It must pass before the first or any further
     candidate edit.

     The gate blocks candidate edits, not ADT state creation. When investigation
     may outlive the current turn, form a neutral investigation goal in step 7
     with the owner-reported outcome and the causal mechanism as unverified;
     start or resume state and checkpoint the probe plan, evidence gap,
     provenance, and results. State creation never satisfies or bypasses the
     gate.

     Run a safe focused baseline probe through the final observer when the
     claimed outcome depends on runtime reporting, propagation, lifecycle, or
     cardinality. Use the identified immutable pre-candidate snapshot and the
     same terminal-boundary validity rules required under verification below:
     exercise the production entry point when the outcome depends on process or
     framework hooks, retain every enabled automatic reporting route, and
     measure exact aggregate cardinality when reporting is load-bearing. Naming
     an observer or reasoning from source is not a substitute for an available
     probe. A copied or handwritten harness that directly installs process or
     framework hooks or initializes the downstream observer is not the
     production entry point. It can support exploration, but cannot qualify the
     incident gate when the real initialization path is load-bearing or
     unverified. Identify the observer as the exact runtime route and measurable
     outcome, not merely a destination, vendor, or subsystem.

     Calling the real library function from a harness does not make the harness
     the production initialization path. When initialization is load-bearing,
     the actual repository bootstrap must execute it; copying its arguments or
     configuration into probe code is still a reimplementation and cannot
     qualify the incident gate. A fake terminal transport is acceptable only
     when the actual repository bootstrap reaches a supported replacement seam
     without the probe recreating the bootstrap itself.

     Matching the reported outward symptoms is not incident reproduction when
     the probe introduced an added causal precondition. Each added causal
     precondition must be independently established as applicable to the
     reported incident from inspected repository, deployment, or incident
     evidence. An injected fault may stand in for an established trigger, but a
     synthetic hang, timeout, signal, kill, or supervisor action introduced only
     to force the outcome remains exploratory evidence. It cannot qualify the
     incident gate or promote that hypothesized mechanism to a verified cause.

     After resume, takeover, or handoff, reuse prior qualifying checkpoint
     evidence only when it identifies the immutable snapshot, final observer,
     exercised route, measured outcome, result, and evidence provenance.
     Otherwise run or repeat the focused probe before any further candidate
     edit. If candidate edits already exist without qualifying evidence, freeze
     those edits, recover the immutable pre-candidate snapshot, and probe that
     snapshot; never treat the dirty candidate as the baseline.

     If no safe probe can run, or the probe does not reproduce the incident,
     mark the causal mechanism unverified, state the evidence gap, and ask one
     focused owner decision between further incident investigation and an
     explicitly revised hardening goal before source or test edits.
     An answer to an operational fact question is not authorization; the owner
     must explicitly revise the task goal before edits pursue a different
     outcome. If the decision remains missing input when the session ends,
     checkpoint the evidence and then pause the task. Never leave an active
     lease awaiting an owner reply.
     A worker, callback, future, command, or framework boundary is not final
     when production has a later automatic observer; catching there changes the
     path. An explicit reporting call is not the final observer when the same
     exception is re-raised into an automatic framework or process reporter;
     every later automatic reporting route remains part of the final observer
     path. Inspect targeted history plus runtime and supervisor configuration
     before changing that boundary. Do not infer a timing or
     termination SLA from `fail-fast` or `restart`. New evidence may invalidate
     the plan, but it does not authorize strengthening the owner's contract. A
     fix that bypasses normal stack unwinding or cleanup, or changes the fate of
     sibling work, is a normative failure-policy change and requires an
     explicit owner decision. If multiple viable contracts remain, present the
     evidence and ask one focused owner decision before candidate edits.
7. For the new-task path in step 6, before any edit, form a compact neutral
   task contract from the preserved owner intent, corrected factual premises,
   and repository evidence. Use the contract as the existing `--goal` value;
   it is no new artifact or taxonomy. Challenge may distinguish an
   owner-proposed solution from the desired outcome, but the durable `GOAL`
   must contain only this compact, neutral, outcome-level contract:
   - desired outcome and observable success;
   - constraints and non-goals, including the accepted input domain and
     explicitly unsupported inputs when they affect acceptance;
   - verified repository facts distinguished from explicit assumptions; and
   - authoritative owner decisions, waivers, and unresolved decisions.

   Use `verified` only for facts directly observed in the selected snapshot or
   demonstrated by concrete inspected repository and applicable runtime
   evidence. Counterfactual claims about concurrency, shutdown, buffering,
   reporting loss, or sibling fate remain explicit assumptions until exercised;
   they must not be promoted to verified facts, justify source edits, or expand
   observable success.

   When the contract depends on a domain boundary, carry both any verified
   domain invariant and any owner-approved explicitly unsupported inputs.
   Verify discoverable invariants from repository or applicable platform
   evidence; owner authority defines product scope but does not prove a fact.
   An out-of-domain counterexample must not enlarge the accepted contract. If
   its domain membership is material and unresolved, inspect the available
   evidence or ask one focused owner decision before adding defensive behavior.

   When a removed, deprecated, or unavailable upstream value is replaced by a
   local derivation, treat semantic equivalence as a load-bearing factual
   invariant. Ordinary local calculations and refactors are outside this check
   unless they replace such an upstream value. Establish what the upstream value
   included and excluded from authoritative upstream specification, source, or
   targeted history independently of the candidate formula and tests. Tests that
   mirror the derivation do not establish equivalence. If equivalence cannot be
   established or the semantics differ, pause before candidate edits unless the
   owner explicitly approves the semantic change.

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
- Treat a review finding as evidence about the candidate, not authority to
  enlarge the accepted task contract. Before repairing it, trace it to the
  accepted outcome or a repository constraint, and establish that its trigger
  is inside the accepted input domain. A constructible out-of-domain
  counterexample must not enlarge the accepted contract. Do not implement an
  adjacent guarantee without an owner decision. If an in-scope repair
  materially adds state, concurrency coordination, or dependence of
  correctness or proof on non-public dependency behavior, reopen the plan and
  compare simpler contract-preserving alternatives. Keep that complexity only
  when repository evidence shows it is load-bearing for the accepted outcome;
  otherwise reshape or discard it.
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
  Model-authored self-report is not execution evidence. After conclusions are
  fixed, prefer launcher-owned execution evidence such as a CLI header or
  invocation receipt. If the reviewer cannot see it, keep the reviewer-authored
  value `unknown` and attach the launcher evidence separately.

- For behavior-changing code, prefer a focused failing test first. Reproduce
  the defect at the narrowest deterministic seam that still includes every
  load-bearing automatic downstream observer. For an incident or bug fix,
  compare baseline and candidate at the same final observer and preserve the
  complete downstream disposition, reachability, timing, and signal
  cardinality. Assert the observable outcome plus relevant persistence,
  propagation, or process lifecycle. When signal classification or handled
  state affects operational behavior, assert it as well as cardinality. A new
  mock or log call alone is insufficient evidence when those semantics matter.
  When a candidate adds a reporting action while the same failure still reaches
  automatic reporting, enumerate every enabled reporting route, including
  direct SDK calls, logging integrations, framework hooks, and process hooks.
  A test that patches capture or flush and asserts only those calls is
  non-discriminating for final delivery, aggregate event cardinality, and
  handled classification. A real client exercised only around a directly
  invoked handler in the test process is not terminal-boundary evidence.
  Use the lowest-cost seam that remains discriminating. Exercise the
  production entry point when framework bootstrap or process lifecycle is
  load-bearing, or when a narrower seam's equivalence to every final observer
  cannot be demonstrated. A narrower harness may drive final observers
  directly only when repository or runtime evidence shows that it preserves
  production initialization, automatic hooks, ordering, classification, exact
  aggregate cardinality, and propagation or exit. A fake or in-memory
  transport is acceptable. Assert the exact aggregate event cardinality from
  all enabled routes plus the propagation or exit outcome; `>= 1`, non-empty,
  and per-route call assertions prove only partial observability.
  A test that replaces the mechanism that performs the claimed outcome proves
  only the local call unless production-equivalent behavior is independently
  demonstrated. A real dependency client remains non-discriminating when its
  load-bearing hooks or integrations are disabled, replaced, or bypassed.
  Before freezing a candidate, when its proof harness depends on a load-bearing
  observer, run a safe test-only negative-control mutation that disables,
  replaces, or bypasses that observer while the trigger still executes. The
  control qualifies only when the claimed measurable outcome itself fails;
  failure only at an assertion that the observer is installed, active, or
  reached does not qualify.
  When one-time process-global initialization installs a load-bearing observer,
  prove at the measurement point that the observer is active and that the
  trigger reaches it; a successful initialization call or initialized registry
  alone is insufficient. Isolate baseline, candidate, and repeated cases from
  one another: restoring an outward hook while retaining process-global
  initialization or integration registry state is not a consistent reset.
  Prefer a fresh process when public teardown cannot restore both consistently;
  do not mutate non-public dependency internals to simulate teardown.
  Treat test scaffolding as part of the design: dependency of the harness does
  not make a production seam load-bearing. Do not add production configuration,
  public interfaces, or dependencies solely for verification when a test-only
  equivalent exists. If no such equivalent preserves the accepted
  proof boundary, record why the production seam is necessary and keep it
  minimal.
- Before declaring focused verification blocked or settling for syntax-only
  checks, inspect already-ready repo-native runtimes: repository instructions
  and test targets, an existing environment associated with another checkout
  of the same repository, and an existing local image or container. Use one
  only if it runs the exact focused offline selector against the selected
  worktree's source without copying secrets or mutable runtime state.
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
- Before asking to commit or open a PR, reconsider the whole candidate against
  the accepted outcome, including its proof scaffolding and reliance on
  non-public dependency interfaces. Green, discriminating checks establish
  behavior, not the necessity of incidental machinery. When a simpler
  contract-preserving candidate reaches the same accepted proof boundary,
  reshape to it before freezing. Then always state whether independent review
  ran. Missing review blocks completion only when the selected assurance
  profile, accepted task contract, or owner requires it. In that case call the
  result an implementation checkpoint and keep the task active. Freeze the
  candidate as an immutable range and give the exact invocation for a fresh
  memory-clean session in a separate review checkout that exposes the same
  immutable range. There the reviewer starts a standalone `kind=review` task
  with a neutral `GOAL`; do not hand off or resume the open development task as
  cold-review context. Ordinary handoff remains available for continuity or
  non-cold validation. Otherwise completion may proceed after proportionate
  verification while disclosing that review did not run. Green tests or a
  builder checkpoint must not imply independent acceptance.
- When the accepted task contract or owner requires a trusted, full-cycle, or
  two-model result, one reviewer is insufficient. The required independent
  paths must form conclusions before disclosure, and any material disagreement
  must be adjudicated from evidence before acceptance.
- Builder-spawned subagents and repeated review passes inside the builder's
  active session may advise the implementation, but they do not count as
  independent judgment paths. A counted path starts in a fresh preflighted
  session, receives only neutral context, and fixes its conclusion under the
  review embargo. A two-model claim additionally requires evidence of distinct
  actual models.
- Do not claim full production assurance. This MVP proves resumable control
  boundaries; stronger evidence and release gates remain separate work.
