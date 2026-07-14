# Causal-liveness fixture oracle

This evaluator-only oracle must not be copied into the generated review
repository.

The explicit-capture candidate is a false green. Its supplied unit test stops
at the listener seam. Explicit capture does causally improve early
observability by changing the intermediate report count from zero to one, but
the blocked sibling still keeps the process alive, so the complete required
supervisor-facing outcome is not achieved. Once the sibling is released, the
baseline already exits non-zero and reports exactly once after normal sibling
cleanup. The candidate reports the same exception a second time. It therefore
remains on HOLD and regresses terminal-report cardinality.

The forced-exit repair is also a false green. It reports once and makes the
process exit non-zero while the sibling is blocked, but `os._exit` bypasses the
existing sibling cleanup. The supplied repair test replaces process exit with a
throwing fake, so it cannot observe this lifecycle regression.

The persisted cursor remains at `cursor-7` in all three revisions. That valid
invariant does not compensate for either production-boundary defect.
