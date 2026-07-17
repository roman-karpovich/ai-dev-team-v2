# Verification environments

Load this reference only when a required check needs an unavailable dependency,
runtime, production bootstrap, or load-bearing environment equivalence.

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
