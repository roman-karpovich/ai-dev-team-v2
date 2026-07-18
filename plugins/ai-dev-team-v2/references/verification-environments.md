# Verification environments

Load this reference whenever any check executes source, artifact, or runtime.
Also load it when a required check needs an unavailable dependency, runtime,
production bootstrap, or load-bearing environment equivalence.

## Required outcomes

| Boundary | Trigger | Required | On unmet |
| --- | --- | --- | --- |
| `candidate-binding` | `check:executes-source\|artifact\|runtime` | `prove:executed-candidate->intended-worktree\|commit\|snapshot;cached\|baked\|generated:rebuild\|refresh\|fingerprint` | `candidate-binding:unverified;affected-claim:withhold` |
| `discriminating-seam` | `check:selected` | `record:proves,cannot-prove;claim:within-seam-only` | `outside-seam:unverified` |
| `secret-safe-setup` | `required-environment:unavailable` | `forbid:secret-files,credentials,tokens,mutable-runtime-state@workspace,tool-output,logs,checkpoints,review-evidence;allow:checked-in-fixtures,dummy-values,secret-free-config` | `verification:blocked-if-no-safe-setup` |

## Bind the executed candidate

Before interpreting a check, prove that the source, artifact, or runtime actually
executed corresponds to the intended worktree, commit, or snapshot. A command
selected by repository documentation is not proof of that binding. Treat a
cached, baked, or generated artifact as unverified until it is rebuilt or
refreshed from the intended candidate, or its fingerprint is matched to that
candidate. Withhold only claims that rely on an unbound candidate.

## Select a discriminating seam

Start with the smallest ready offline check that can distinguish the accepted
behavior from the relevant defect. State what it proves and what it cannot
prove. A green command is not evidence for behavior outside its seam.

When environment equivalence is load-bearing, identify the concrete property:
dependency version, service behavior, framework bootstrap, database
transaction semantics, process lifecycle, network, or platform configuration.
Do not substitute a convenient harness without demonstrating that property.
A fake or in-memory dependency is acceptable when the affected semantics are
preserved.

## Handle unavailable checks

- Never copy secret-bearing environment files, credentials, tokens, or mutable
  runtime state into a test workspace. Use checked-in fixtures, dummy values,
  or a purpose-built secret-free configuration. Keep secrets out of tool
  output, logs, checkpoint notes, and review evidence. If no safe setup exists,
  report the verification as blocked instead of weakening this boundary.
- During independent review, reuse only an already-ready local environment and
  focused offline selector. Do not install dependencies, build or pull images,
  or start a broad live-network suite merely to erase an evidence gap.
- During development, add or prepare dependencies only when that mutation is
  authorized and belongs to the task. Keep live or destructive checks
  explicit and proportionate to risk.
- Record the command, environment identity that matters, outcome, and gap.
  Treat a missing check as blocking only when the accepted contract or current
  assurance profile requires its evidence.
- Prefer a narrower equivalent seam when repository evidence demonstrates the
  relevant semantics. Otherwise report the limitation honestly rather than
  manufacturing confidence.
