# Native-backend conformance

This area holds versioned, secret-free evidence for replaceable native
execution backends. A backend may use a CLI, SDK, App Server, MCP server, or a
future native integration, but it must accept the same portable work-order
semantics and return the same result and invocation-receipt semantics.

Conformance validates the boundary, not identical internal orchestration.
Required classes include:

- happy path and structured-result validation;
- advertised, missing, forbidden, and misstated capabilities;
- cancellation, timeout, and late output;
- malformed output and identity mismatch;
- personal-configuration and inference-context isolation;
- repository-instruction selection;
- sandbox and network enforcement;
- usage and elapsed-time accounting;
- snapshot, manifest, contract, and output binding;
- explicit degraded and unsupported outcomes.

The first planned exercise is the
[portable cold-review conformance exercise](portable-cold-review.md).

The privacy-safe public conclusions are recorded in the
[development and review dogfood summary](dogfood-summary.md).

Real backend checks are explicit opt-in and never part of the default local
suite. One real invocation per backend is sufficient for the conformance
exercise; repeated promotion evaluation belongs to a separate slow tier.
