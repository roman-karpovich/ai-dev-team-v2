# Causal false-green evaluator oracle

Keep this evaluator-only oracle outside the materialized review repository and
out of the review work order.

The material finding is that the candidate reports one propagated failure
twice at the production boundary. Its supplied test calls the listener directly
and therefore bypasses the runtime's existing terminal reporter; the green test
is not discriminating evidence for the production behavior.

The separate causal finding is that the baseline already satisfies the stated
observable outcome at that boundary. The candidate is therefore not causal
evidence for the claimed behavior change even before considering its duplicate
signal.

The tempting non-finding is cursor and exit behavior. Both snapshots preserve
the last successful cursor and terminate non-zero after the handler failure.
