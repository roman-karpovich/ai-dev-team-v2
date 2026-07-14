# Mission and product direction

- Status: Working mission
- Last reviewed: 2026-07-13
- Scope: Product direction, not an implementation specification

This document defines why AI Dev Team v2 should exist, the result it must
control, and the development cycle it should support. Repository contracts,
ADRs, and the readiness gate remain authoritative for implementation.

## Mission

AI Dev Team v2 turns probabilistic coding models into a controlled,
inspectable, and revisable engineering process.

It collaborates with the owner to turn an incomplete request into a strong
task contract, develops a solution that fits the existing system and the
owner's quality standards, and independently tries to disprove that the result
is ready. It records workflow completion separately from the release
recommendation: a completed run may still recommend `HOLD`. It stops honestly,
identifies the missing confidence, and asks for a decision only where human
judgment is genuinely required.

The system cannot promise that a model will always produce good code on its
first attempt. It must promise not to present undeclared or policy-exceeding
uncertainty as an acceptable result.

## The problem

Frontier models can already plan, write code, run tools, create tests, review
diffs, and delegate work. Rebuilding those abilities is not a product.

The unsolved personal problem is variance without control: the same request can
produce an excellent result once and a plausible but weak result the next
time. Green tests can be self-confirming, reviewers can share the author's blind
spots, and a locally reasonable implementation can still be the wrong
architectural direction.

Controlled does not mean byte-for-byte identical output. It means that:

- the goal, constraints, assumptions, and accepted trade-offs are explicit;
- unacceptable results are not silently promoted to `PROCEED`;
- important claims have inspectable evidence;
- model agreement is not mistaken for proof;
- new information can invalidate old decisions and evidence;
- pauses, replanning, partial discard, and rollback are normal outcomes;
- equivalent risk should produce a stable release decision under the same
  policy, even when implementations differ.

## Product promise

AI Dev Team v2 has two entry modes backed by the same assurance contract:

### Review

Given a diff, commit, branch, or implementation artifact, determine whether it
achieves its intent, fits the current system, meets the applicable quality
policy, and has enough evidence to recommend acceptance under the stated risk
tolerance.

A trusted review must support at least two epistemically independent judgment
paths. Cross-provider and cross-model diversity are strong hypotheses for
reducing correlated misses, not proof of independence by themselves. The paths
and models that qualify for a high-assurance profile are selected by evaluation
and policy; a run that omits a required path is explicitly degraded. Each path
must form its conclusions before seeing another path's findings. Disagreement
triggers investigation; agreement is metadata, not proof.

Qualification requires isolated inference context, expectations derived from
the authoritative contract rather than another agent's output, attributable
model and input identity, and measured complementary defect detection. Merely
changing a model name while sharing the same mistaken oracle is not
independence.

### Delegated development

Given a rough goal, collaborate with the owner to establish a strong task
contract, implement the solution in bounded increments, and pass the result
through the same independent assurance gate used for review.

The builder, reviewer, and native executive are replaceable. The assurance and
acceptance protocol is the durable product.

## Trust contract

The product must preserve these invariants:

1. **Intent is not a literal prompt.** The agent separates the desired outcome
   from the implementation initially suggested by the owner.
2. **The owner is not a factual oracle.** Owner statements about the system are
   hypotheses when they can be checked. Owner authority applies to goals,
   priorities, and explicit trade-offs.
3. **The agent must challenge weak input.** It inspects available evidence,
   identifies ambiguity and contradictions, proposes alternatives, and argues
   against a weak architectural direction.
4. **Questions are reserved for real decisions.** The agent investigates what
   it can discover itself and asks only when an answer materially changes the
   solution or accepts risk.
5. **Authorship and acceptance are separated.** The author of a change is not
   its only reviewer, and a reviewer is not primed with the author's desired
   conclusion.
6. **Evidence outranks confidence and consensus.** Claims are tied to code,
   behavior, commands, measurements, or other admissible observations.
7. **Tests are evidence under review.** A green suite is not sufficient when
   the tests restate the implementation, miss negative behavior, or cannot
   fail under a relevant defect.
8. **System fit is part of correctness.** Local requirement compliance does not
   excuse a serious architectural flaw, an incoherent boundary, or damage to
   the surrounding system.
9. **Serious trade-offs require an explicit waiver.** A waiver is narrow,
   reasoned, attributable, and attached to the affected risk. Silence and
   underspecification are not waivers.
10. **The gate fails closed.** Missing evidence, unresolved serious findings,
    stale assumptions, or material reviewer disagreement cannot become
    `PROCEED` by default.

## Authority and quality policy

Decision authority and factual authority are intentionally different:

| Question | Authority |
| --- | --- |
| Desired outcome and business priority | Owner |
| Facts about the repository or runtime | Reproducible evidence |
| Engineering quality standards | Accepted quality policy |
| Architecture | Owner-agent dialogue, informed by evidence and alternatives |
| Exceptional technical debt | Explicit owner waiver |
| Whether release criteria passed the declared gate | Assurance protocol |

Quality is defined in three layers:

1. **Engineering constitution:** the owner's durable criteria for code,
   architecture, tests, evidence, and acceptable shortcuts.
2. **Repository contract:** the current system's boundaries, conventions,
   compatibility requirements, and verification commands.
3. **Task contract:** the goal, success criteria, non-goals, assumptions,
   selected approach, risks, and any task-specific waivers.

These layers may come from existing repository instructions, architecture
documents, project constitutions, or task artifacts. v2 should normalize and
enforce the accepted policy; it should not require another competing policy
file taxonomy. Its added value is claim-specific evidence, calibrated
enforcement, and explicit waiver handling.

Useful lessons from the predecessor should be re-derived as principles and
evaluation cases. Old prompts, workflows, fixtures, and expected outputs are
not product requirements and are not copied into v2.

## The development cycle

The process is a revisable control loop, not a linear pipeline:

```text
ORIENT -> CHALLENGE -> CONTRACT -> PLAN -> BUILD A BOUNDED INCREMENT
   ^                                              |
   |                                              v
   +-- REPLAN / PAUSE / DISCARD <- REASSESS <- VERIFY
```

### Orient

Inspect the repository, current behavior, relevant decisions, and recent
change context before asking the owner to explain facts that are already
available.

### Challenge

Interrogate the goal, constraints, success criteria, assumptions, and proposed
solution. Present materially different approaches with trade-offs and a
recommendation. The purpose is not to maximize questions; it is to avoid
implementing an accidental interpretation.

### Contract

Record a versioned task contract. It must distinguish confirmed facts,
assumptions, owner decisions, and unresolved questions. A plan is not allowed
to silently decide an architectural fork that belongs here.

### Plan

Choose the smallest useful increments and the evidence each increment needs.
The plan is a current hypothesis, not an obligation to continue after its
premises fail.

### Build

Implement one bounded increment, preserve reversibility, and run the smallest
relevant checks. More code and more test executions are not progress unless
they reduce uncertainty or move the result toward the task contract.

### Verify

Check behavior, test quality, architecture, integration with the existing
system, and load-bearing claims. Use independent reviewers where correlated
error matters. Resolve findings through evidence or a fix-and-re-review loop,
not majority vote.

### Reassess

Ask whether the goal, assumptions, plan, and architecture still deserve to be
continued. The key counterfactual is:

> If the current implementation disappeared, would we choose this design again
> with what we know now?

A reassessment may return `CONTINUE`, `REPLAN`, `SPIKE`, `PAUSE`,
`PARTIAL_DISCARD`, `ROLLBACK`, `NEEDS_DECISION`, or `ABANDON`.

Reassessment is mandatory when evidence indicates architectural drift, such
as repeated failed fixes, growing exception count, expanding scope, tests being
reshaped to fit the implementation, recurring reviewer disagreement, or
complexity growing faster than delivered value.

## Pause, resume, and change

`PAUSED` is a first-class state, not a failure. Work may pause for measurements,
external decisions, another agent's report, a changed requirement, or a shift
in priority.

A durable pause record contains:

- the task-contract version and repository snapshot;
- completed and in-progress increments;
- decisions, rejected alternatives, and their rationale;
- assumptions and the evidence on which they depend;
- open findings, risks, and disagreements;
- awaited information and the decisions it may affect;
- focused resume and verification instructions.

Resume never means blindly executing the next plan item. The agent first checks
repository drift, ingests the new information, identifies affected decisions,
and marks dependent plans, code, tests, and evidence stale. Unaffected evidence
is reused; invalidated evidence is rerun selectively. A slow full suite is a
release or risk decision, not a ritual repeated after every pause.

The minimum dependency model connects assumptions, decisions, plan increments,
implementation areas, and evidence with explicit `depends_on` relationships.
For example, if a design assumes that an external write is idempotent, retry
logic and duplicate-write tests depend on that assumption. Evidence that the
write is not idempotent must stale those decisions, code areas, and tests while
leaving unrelated presentation evidence valid. Before continuing, the system
must expose that invalidation set for inspection.

Discarded code is disposable, but the knowledge gained from rejecting it is
retained so the same failed approach is not rediscovered without cause.

## Completion status and release recommendation

Workflow status answers whether the process ran, not whether the artifact is
safe:

- `IN_PROGRESS`: the current increment is still active.
- `PAUSED`: state is durable and waiting for new information or an intentional
  resume.
- `COMPLETED`: the bounded workflow reached a terminal receipt. This is not a
  safety claim.
- `ABANDONED`: the current approach was rejected; retained evidence explains
  why.

The separate release recommendation answers what may happen to the artifact:

- `PROCEED`: evidence supports acceptance under the declared policy and risk
  tolerance.
- `HOLD`: the artifact must not be accepted while identified risk remains.
- `NEEDS_DECISION`: acceptance requires an owner choice or explicit waiver.
- `REPORT_ONLY`: useful analysis exists, but the run did not earn a release
  recommendation.

## Comparison with public development cycles

This comparison uses public primary sources reviewed on 2026-07-13. A missing
property means it is not part of the documented mandatory core, not that a
user could never add it with prompts or extensions.

| System | Strongest contribution | Boundary relative to this mission | v2 decision |
| --- | --- | --- | --- |
| Claude Code UltraCode | Executable large-scale orchestration | Verification and architectural challenge are workflow choices, not universal gates | Use it as a candidate native backend; do not compete on fan-out |
| obra/superpowers | Disciplined design, TDD, task review, and evidence before completion | Optimizes execution of an approved route more than repeated validation of the route itself | Re-derive its successful engineering disciplines and add first-class reassessment |
| Native OpenAI Codex | Goal steering, subagents, review, worktrees, permissions, and resumable task UX | Provides composable primitives rather than this assurance contract | Use it as a candidate native backend instead of rebuilding the runtime |
| GitHub Spec Kit | Living specification artifacts, constitution, consistency analysis, convergence, and resumable workflows | Convergence primarily asks whether code matches accepted artifacts, not whether the chosen intent and architecture remain right | Reuse artifact traceability concepts and add independent solution validation |

### Claude Code UltraCode

The documented UltraCode cycle is roughly `request -> generated workflow
script -> subagents and scripted loops -> result`, with Claude optionally
launching separate workflows to understand, change, and verify. Dynamic
workflows make orchestration inspectable and repeatable, keep intermediate
results out of the main context, expose cost and progress, and can encode
adversarial cross-checks.

The important limit is that a workflow has no ordinary mid-run user input;
sign-off between stages requires separate workflows. Resume reuses completed
results only within the same Claude Code session. A verification workflow is a
capability, not a mandatory software acceptance contract, and cached results do
not carry documented semantic invalidation when an earlier assumption changes.

The lesson is to keep orchestration inspectable, bounded, and observable while
making quality gates, evidence validity, and human steering part of the product
contract rather than optional prompt content. See the official
[dynamic workflows and UltraCode documentation](https://code.claude.com/docs/en/workflows).

### obra/superpowers

Superpowers uses a strong staged cycle: collaborative brainstorming, design
approval, isolated worktree, detailed plan, task-level TDD, fresh implementers,
per-task review and repair, whole-branch review, fresh final verification, then
merge, keep, or discard. Its current subagent-driven flow also persists a
progress ledger so execution can recover after context compaction.

This is the closest source for several successful v1 concepts: challenge before
code, alternatives before commitment, behavior-focused TDD, evidence before
claims, separate implementer and reviewer contexts, and explicit blocked or
concerned states.

Its default execution path deliberately continues through an approved plan
without routine human check-ins. It stops on blockers, ambiguity, or an
explicitly wrong plan, but it has no general `REASSESS` gate between meaningful
increments. Review primarily asks whether a task matches the accepted spec and
is well built. The progress ledger restores execution position, not the full
dependency structure among goals, assumptions, decisions, and evidence.

The project also removed an expensive mandatory independent review of every
spec and plan after its own evaluation found added latency without measured
quality improvement. That is a useful warning for v2: independence must target
real correlated-risk boundaries and prove its value, not become an expensive
ritual.

Sources: [repository overview](https://github.com/obra/superpowers),
[brainstorming](https://github.com/obra/superpowers/blob/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/brainstorming/SKILL.md),
[subagent-driven development](https://github.com/obra/superpowers/blob/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/subagent-driven-development/SKILL.md),
[verification before completion](https://github.com/obra/superpowers/blob/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/verification-before-completion/SKILL.md),
and [release notes](https://github.com/obra/superpowers/blob/d884ae04edebef577e82ff7c4e143debd0bbec99/RELEASE-NOTES.md).

### Native OpenAI Codex

Codex already supplies the platform primitives v2 would otherwise have to
rebuild. Plan mode can interview the user; Goal mode records outcome,
constraints, and verification criteria and supports pause, resume, editing, and
steering. Subagents isolate parallel work, `/review` launches a dedicated
reviewer that reports findings without changing the working tree, worktrees and
handoff isolate task state, and sandbox and approval policies bound actions.
ExecPlans add a living record of progress, discoveries, decisions, and
validation.

These are composable capabilities, not a mandatory adaptive engineering
protocol. Native review does not by itself establish provider-diverse
independence, challenge whether the task contract is still correct, or
invalidate dependent evidence after an assumption changes.

Therefore v2 should be a policy and assurance layer around replaceable native
execution backends. Codex tasks, subagents, worktrees, reviews, and permissions
are one current backend's useful primitives, not permanent architectural
dependencies. v2 should not build another task UI, worktree manager, generic
subagent runtime, or conversation store.

Sources: [long-running work](https://developers.openai.com/codex/long-running-work),
[subagents](https://developers.openai.com/codex/agent-configuration/subagents),
[code review](https://developers.openai.com/codex/code-review),
[worktrees](https://developers.openai.com/codex/environments/git-worktrees),
and [ExecPlans](https://developers.openai.com/cookbook/articles/codex_exec_plans).

### GitHub Spec Kit

Spec Kit's recommended cycle is approximately `constitution -> specify ->
clarify -> plan -> checklist -> tasks -> analyze -> implement -> converge`,
with `implement` and `converge` repeating until the implementation matches the
artifacts. It treats specifications as durable inputs, checks consistency among
specification, plan, and tasks, and documents living-spec and flow-back modes
for propagating implementation discoveries upward.

Its workflow runtime adds gates, branches, loops, fan-out/fan-in, persisted
state, and exact-step resume with updated inputs. These are valuable evidence
that resumable artifact-driven development is practical.

The remaining gap is the distinction between consistency and validity. The
same agent can author the artifacts, implement them, and run analysis or
convergence. Convergence can demonstrate that code matches accepted intent
while the intent or architecture is still weak. Updating a paused workflow's
inputs reruns the blocked step, but dependency-aware invalidation of already
completed decisions and evidence remains an external discipline. Its workflow
shell steps also intentionally have no capability sandbox.

The lesson is to adopt living contracts, traceability, consistency analysis,
and convergence without copying Spec Kit's file taxonomy or building another
general workflow engine.

Sources: [Spec Kit overview](https://github.github.com/spec-kit/index.html),
[recommended flow](https://github.github.com/spec-kit/quickstart.html),
[workflows and resume](https://github.github.com/spec-kit/reference/workflows.html),
and [evolving specifications](https://github.github.com/spec-kit/guides/evolving-specs.html).

## Strategic conclusion

The direction is valuable only if v2 owns the gap left by these systems.

The ecosystem already offers:

- runtime, steering, worktrees, permissions, and review in Codex;
- scalable scripted orchestration in UltraCode;
- disciplined spec-to-code execution in Superpowers;
- artifact-driven specification and convergence in Spec Kit.

AI Dev Team v2 should own:

- calibrated epistemic independence in review of implementation and
  architecture, using provider or model diversity where it proves useful;
- normalization of existing personal and repository policy into enforceable
  evidence and waiver rules;
- strong challenge of weak requests and unverified owner assumptions;
- explicit distinction between artifact consistency and solution validity;
- anti-swamp architectural reassessment during development;
- dependency-aware invalidation after new information;
- controlled outcome states and explicit waivers;
- calibration against real defects, false greens, false blocks, time, and cost.

## Runtime strategy

The mission must survive the competitive cycle in which different coding
products temporarily become the strongest orchestrator, builder, or reviewer.
No provider is the permanent lead and no model is the best choice for every
role.

v2 therefore keeps assurance portable and execution native. Its stable layer
owns contracts, checkpoints, evidence, invalidation, controlled outcomes, and
release policy. A selected Codex, Claude, or future backend receives a bounded
execution lease and may use its strongest native planning, subagents, review,
steering, or workflow facilities. Selection is role-specific and based on
evaluation rather than reputation.

This is not a lowest-common-denominator workflow. The common contract describes
the required result and evidence, while a capability-aware backend decides how
to produce them. Switching providers happens at a durable checkpoint; hidden
reasoning and provider transcripts are not portable state.

Instructions follow the same boundary. The project and role contracts are
provider-neutral, backend profiles contain only execution mechanics, and a
model-specific delta exists only while measured evaluation evidence justifies
it. Host instruction files and plugins remain thin entry points rather than
copies of the lifecycle.

The proposed boundary and its staged validation are recorded in
[ADR 0002](adr/0002-portable-assurance-native-execution.md).

If v2 becomes another `spec -> plan -> tasks -> code` wrapper, another subagent
fan-out tool, or another prompt library, it should be stopped. Those products
already exist and can be used directly.

## Priorities

These are product-roadmap priorities. Trusted review remains the first
user-facing capability, while the narrower VERIFY evidence kernel remains the
first implementation slice under the existing readiness gate.

### P0: Prove the trust contract

- Normalize the owner's existing quality criteria and predecessor failure
  classes into enforceable policy and blinded evaluation cases without adding
  another policy-file taxonomy.
- Pre-register and test the hypothesis that current top models from different
  providers reduce correlated misses enough to qualify as independent paths.
- Compare against the real baseline: native frontier-agent review, existing
  project checks, and one cold independent review.
- Measure critical and high-severity misses, false-green rate, false blocks,
  human minutes, wall time, cost, and verdict stability.
- Pre-register promotion and kill criteria before tuning the workflow.

### P1: VERIFY evidence kernel

- Complete the currently authorized readiness evidence before production code.
- Separate workflow completion from the release recommendation.
- Validate claim-specific evidence admissibility, degradation, findings, and
  residual gaps.
- Prove fail-closed outcomes before adding development orchestration.

### P2: Trusted review vertical slice

- Review a real diff, commit, or branch against its intent and repository
  contract.
- Run policy-qualified independent judgment paths without cross-contamination.
- Adjudicate disagreement with targeted evidence and focused probes.
- Return findings, evidence gaps, residual risk, and a controlled outcome.
- Demonstrate value on historical and current changes before adding broad
  orchestration.

### P3: Challenge and task contract

- Re-derive the successful `grill me` behavior as a model-agnostic contract.
- Inspect the system before questioning the owner.
- Separate goal, proposed solution, assumptions, constraints, and waivers.
- Require alternatives and architectural challenge where the decision has a
  large or irreversible blast radius.

### P4: Resumable reassessment

- Persist the minimum viable task contract, decisions, assumptions, evidence,
  and repository identity.
- Support pause, drift detection, new-information impact analysis, and
  selective evidence invalidation.
- Demonstrate the assumption-change acceptance example above before expanding
  the dependency model.
- Add risk-based anti-swamp triggers and cold architecture challenge.
- Prove this with a narrow lifecycle before designing a general state or
  workflow framework.

### P5: Bounded delegated development

- Use native platform primitives to implement small, real tasks.
- Require every builder result to pass the same trusted review gate.
- Add repair, re-review, partial discard, and explicit-waiver paths.
- Expand task size only when evaluation shows stable confidence.

### P6: Scale and optimize

- Select native backend, executive, model, and effort per role from capabilities
  and evaluation rather than hard-coded reputation.
- Add providers only when they reduce measured correlated misses.
- Cache only evidence whose dependencies and freshness are known.
- Optimize latency and cost after the false-green gate is credible.

The schema, snapshot, sandbox, ledger, and adapter work described elsewhere in
the repository are enabling mechanisms, not product value by themselves. Each
must justify itself against one of these priorities. A mechanism is admitted
only for an observed recurring failure or committed near-term requirement and
a named consumer such as a decision, gate, enforcement action, or repeated
operation. A one-off evaluation need stays manual or in notes; "possibly useful
later" is insufficient unless delay would make required evidence irrecoverable
or create costly irreversible coupling. This mission does not authorize
production implementation or remove the existing readiness gate; it provides
the standard by which that gate should be reviewed.
