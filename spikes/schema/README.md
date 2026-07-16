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

Together these observations suggest a candidate portable subset: explicit
`type` beside every `const`, with unsupported metadata omitted. They justify
testing one common emission shape plus thin native-output extractors before
adding a general schema compiler or separate provider schema trees. They do
not prove that the identical candidate document was accepted by both surfaces.
Provider and runtime versions belong in the invocation evidence for each probe
because the accepted subset may change.

## Replay prototype

`native_result_adapter.py` preserves the reusable part of that observation as
an intentionally narrow spike:

- `project_result_schema` emits the candidate common closed result shape. Every
  `const` has an explicit sibling `type`, the rejected root `$schema` metadata
  is omitted, and stricter semantic checks stay in the canonical validator.
- `normalize_result` extracts either a Codex final-output object or Claude's
  `structured_output`, then delegates validation to the existing review gate,
  verifies exact work-order/path/snapshot bindings, and emits deterministic
  JSON bytes. A Claude envelope must itself report a successful terminal
  result; error wrappers and permission denials fail closed instead of being
  discarded.
- Normalization never fills, repairs, or interprets model-authored fields.
  JSON Schema does not express all gate invariants, so post-extraction contract
  validation remains mandatory.
- The spike reuses the gate's private validation functions to avoid a second
  semantic implementation. Production promotion requires a supported module
  boundary; the focused parity tests make private-API drift visible meanwhile.

The candidate emission schema intentionally uses only the structured-output
constructs already isolated in the compatibility matrix. Non-blank strings,
minimum array cardinality, uniqueness, and cross-reference validity remain
mandatory in post-extraction canonical validation until their native schema
support is probed. This weakens only the early emission filter, not the accepted
portable result contract.

For this spike, canonical bytes mean UTF-8 JSON with sorted keys, two-space
indentation, one trailing newline, and unescaped non-ASCII characters. Unpaired
Unicode surrogates and non-UTF-8 native input fail closed. This is an adapter
output convention for replay; v0 does not impose it on independently assembled
bundle files.

The prototype does not launch a process, select a model, inspect Git, enforce a
sandbox, probe capabilities, infer runtime identity, or issue a receipt. The
normalizer's surface names describe the two observed native envelope shapes,
not compatibility with every current or future CLI version. Production
adoption remains blocked on the rest of this spike's exit criteria and the
separate snapshot and sandbox decisions.

## Required evidence

- representative valid and invalid envelopes;
- required-feature matrix across every public contract;
- exact rejection paths for missing fields, unknown fields, enums, nested
  objects, arrays, and composition actually used by the contracts;
- dependency provenance and security review for candidate 1;
- implementation LOC, test LOC, review surface, and measured runtime;
- identical accept/reject results across candidates for the preregistered
  fixtures.
- retained native schemas, raw outputs, and adapter-produced canonical bytes
  whose digests reproduce on replay, including negative cases where
  normalization cannot preserve required semantics.

## Exit criteria

Record one selected substrate and the reason. Do not add it to production
dependencies until the spike decision is accepted.
