# AI Dev Team v2

AI Dev Team v2 is a greenfield, verification-first rebuild for frontier coding
models. Its runtime strategy is portable assurance over replaceable native
execution backends, so the strongest current Codex, Claude, or future runtime
can be used without becoming the source of truth.

Its long-term direction is defined in the
[product mission and development-cycle comparison](docs/mission.md).

## Status

This repository is in the **pre-implementation readiness phase**. It contains
an opt-in native-handoff MVP for dogfooding, but no production plugin or
production VERIFY engine yet.

The predecessor is retained as a
[frozen v1 baseline](https://github.com/roman-karpovich/ai-dev-team). v1 is a
historical comparison target, not a source dependency or a plugin expected to
coexist with v2. Concepts may be re-derived from observed results; v1 source
files, prompts, tests, fixtures, and expected outputs are not copied into v2.

## First slice

The first product slice is VERIFY: determine whether load-bearing claims have
admissible evidence and emit a separate release recommendation. VERIFY does not
claim that an artifact is bug-free.

Current authorized work:

- schema-validation, snapshot, and sandbox spikes;
- execution-backend conformance evidence, including capability negotiation and
  portable work-order and result boundaries;
- versioned evaluation corpus, aligned baseline, and release-gate evidence;
- self-contained public contracts and fast deterministic tests.

Production orchestration begins only after the readiness gate is satisfied.

## Dogfood MVP

The experimental `ai-dev-team` plugin lets Codex and Claude share a local
run, checkpoint it, and hand control to the other native host without copying a
conversation transcript. It intentionally uses manual handoff before automatic
cross-provider dispatch.

See [MVP usage](docs/mvp-usage.md) for installation and the first walkthrough.

## Development

Run the default local check:

```bash
make test
```

The default suite is offline, deterministic, and targeted to finish in under
30 seconds on a normal developer machine. Slower adapter, integration, and
evaluation tiers remain explicit opt-in commands; no test tier may recursively
launch another tier.

See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/architecture.md](docs/architecture.md),
and [docs/readiness-gate.md](docs/readiness-gate.md).
