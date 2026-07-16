# Schema-validation spike

- Status: Active
- Production dependency decision: Not yet made

## Question

Which validation substrate covers every required structured-output contract
with the smallest security and maintenance burden?

## Candidates

1. A small pinned validation dependency, subject to supply-chain review.
2. A deliberately narrow standard-library subset implementing only the
   preregistered feature matrix.

A general self-written schema framework is out of scope.

## Observed native compatibility

The first two-provider cold-review run disproved the assumption that one JSON
Schema document could be handed unchanged to both native structured-output
surfaces:

| Construct | Codex-native observation | Claude-native observation | Portable decision |
| --- | --- | --- | --- |
| `const` without sibling `type` | Rejected | Not isolated from the initial failure | Emit `type` with `const` for Codex |
| Root `$schema` meta-schema URI | Not isolated from the initial failure | Rejected | Omit unsupported metadata from the Claude emission schema |
| Closed objects, required fields, arrays, and enums | Accepted by the successful projection | Accepted by the successful projection | Retain their canonical semantics |

These observations justify small backend projections, not a general schema
compiler. Provider and runtime versions belong in the invocation evidence for
each future probe because the accepted subsets may change.

## Required evidence

- representative valid and invalid envelopes;
- required-feature matrix across every public contract;
- exact rejection paths for missing fields, unknown fields, enums, nested
  objects, arrays, and composition actually used by the contracts;
- dependency provenance and security review for candidate 1;
- implementation LOC, test LOC, review surface, and measured runtime;
- identical accept/reject results across candidates for the preregistered
  fixtures.
- retained native schemas and raw outputs that replay through each adapter to
  the exact canonical result bytes, including negative cases where
  normalization cannot preserve required semantics.

## Exit criteria

Record one selected substrate and the reason. Do not add it to production
dependencies until the spike decision is accepted.
