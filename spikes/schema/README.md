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

## Required evidence

- representative valid and invalid envelopes;
- required-feature matrix across every public contract;
- exact rejection paths for missing fields, unknown fields, enums, nested
  objects, arrays, and composition actually used by the contracts;
- dependency provenance and security review for candidate 1;
- implementation LOC, test LOC, review surface, and measured runtime;
- identical accept/reject results across candidates for the preregistered
  fixtures.

## Exit criteria

Record one selected substrate and the reason. Do not add it to production
dependencies until the spike decision is accepted.

