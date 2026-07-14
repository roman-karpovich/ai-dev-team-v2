# AGENTS.md

## Mission

Build AI Dev Team v2 as a greenfield, verification-first system for frontier
coding models. Add only capabilities a strong model cannot reliably provide by
itself: deterministic control flow, epistemic independence, typed evidence,
receipts, durable state, bounded execution, and explicit human decisions.

## Sources of truth

Use this precedence order:

1. The current user request and explicit owner decisions.
2. Self-contained contracts and ADRs checked into this repository.
3. Executable schemas, fixtures, and tests, which mirror the contracts but do
   not overrule them.

If required normative input is absent, stop and request it. Never encode a
machine-local or external private-document locator in repository content.

## Greenfield boundary

- Do not copy v1 source, prompts, agents, hooks, tests, fixtures, expected
  outputs, manifests, or directory structure.
- v1 may be exercised only as a black-box comparison baseline or used to
  identify concepts and historical failure classes.
- Re-derive expectations independently from v2's public contracts. A green
  legacy test is not an oracle.
- Keep public artifacts self-contained. Do not mention or link external private
  documentation.

## Current authorization

- The first product slice is VERIFY.
- Current work is limited to public contracts, three technical spikes
  (schema, snapshot, sandbox), execution-backend conformance, evaluation
  prerequisites, readiness evidence, and the owner-authorized experimental
  native-handoff MVP under `plugins/ai-dev-team-v2/`.
- The MVP may contain shared skills and a deterministic local state CLI for
  manual Codex/Claude handoff. It must not add automatic model dispatch, a
  general workflow engine, or claim production assurance.
- Do not create a production `src/` package or production orchestrator until
  every item in `docs/readiness-gate.md` is satisfied and the owner records GO.
- DESIGN/BUILD/SHIP orchestration, trajectory replay, dry rounds, refutation,
  prefix caching, and other full-v2 machinery remain deferred.

## Engineering contract

- Prefer a focused failing test before behavior-changing implementation.
- Keep the default test suite offline and deterministic; target under 30 seconds
  on a normal developer machine.
- Run the smallest relevant tier once; do not repeat identical full-suite runs.
- Admit a new field, label, phase, receipt, abstraction, or workflow only when it
  addresses an observed recurring failure or a committed near-term requirement
  and has a named consumer: a decision, gate, enforcement action, or repeated
  operation. Keep one-off experiment needs in notes or manual procedure; defer
  speculative machinery unless delay would make required evidence
  irrecoverable or create costly irreversible coupling.
- Shell is permitted only for thin entrypoints. Deterministic core tooling uses
  Python 3 standard library unless an approved spike selects a pinned dependency.
- Models perform bounded judgment. Deterministic code owns cross-phase
  lifecycle, validation, durable state transitions, budgets, and receipts. A
  qualified native backend may own bounded intra-phase orchestration under an
  execution lease and must return a portable result and invocation receipt.
- Preserve unrelated work and keep diffs minimal.

## Test tiers

- `make test`: default repository, unit, contract, and public-source checks.
- Backend-adapter tests: mocked process boundaries; added when adapters exist.
- Integration tests: real local CLIs; explicit opt-in.
- Evaluation and promotion gates: manual CI, nightly, or release only.
- No test entrypoint may invoke another complete test tier recursively.

## Definition of done

- The relevant public contract and acceptance criteria are satisfied.
- Focused tests pass without new warnings.
- Public-source checks pass.
- Deferred work is stated honestly.
- Migration, rollback, and evidence consequences are documented when affected.
