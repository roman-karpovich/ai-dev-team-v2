# Portable cold-review bundle contract v0

- Status: Experimental conformance contract
- Consumer: `adt review-gate --bundle DIRECTORY`
- Scope: Read-only, manually launched cold-review evidence

This contract defines the smallest provider-neutral evidence bundle accepted by
the experimental review gate. It does not launch a model, choose a provider,
write task state, adjudicate findings, or authorize release. The only normal
verdicts are `REPORT_ONLY` and `HOLD`.

All JSON objects are closed: every listed field is required and unlisted fields
are invalid. Duplicate object fields are invalid JSON for this contract. All
strings described as text are non-blank. IDs and other string arrays contain
unique non-blank strings. Integer counts are non-negative and booleans are JSON
booleans, not integer substitutes. Every SHA-256 value is 64 lowercase
hexadecimal characters and covers the exact referenced file bytes.

## Bundle layout and integrity

The bundle directory contains `bundle.json` and the files it references.
`bundle.json` has exactly:

```json
{
  "contract_version": "adt.portable-cold-review-bundle.v0",
  "work_order": {"path": "work-order.json", "sha256": "..."},
  "paths": [
    {
      "id": "path-alpha",
      "launcher_identity": {
        "provider": "...",
        "runtime": "...",
        "model": "..."
      },
      "result": {"path": "results/path-alpha.json", "sha256": "..."},
      "receipt": {"path": "receipts/path-alpha.json", "sha256": "..."}
    },
    {
      "id": "path-beta",
      "launcher_identity": {
        "provider": "...",
        "runtime": "...",
        "model": "..."
      },
      "result": {"path": "results/path-beta.json", "sha256": "..."},
      "receipt": {"path": "receipts/path-beta.json", "sha256": "..."}
    }
  ]
}
```

At least two path declarations are required. Path IDs and invocation IDs are
unique. Referenced paths are canonical, unique relative names that use forward
slashes, contain no empty, current-directory, or parent segments, and resolve
to unique regular files inside the bundle directory.

The gate reads and verifies the exact-byte digest of every reference before it
parses any result or receipt. A missing, escaping, duplicated, or digest-invalid
reference is a fail-closed input error, not a `HOLD` result.

The manifest is an integrity envelope after bundle composition, not an
authenticity mechanism. Anyone who can replace both a file and `bundle.json`
can reseal the bundle. v0 has no signatures, trusted timestamp, transparency
log, or protection against a malicious local launcher.

## Work order

The referenced work order is provider-neutral and has exactly these fields:

| Field | Contract |
| --- | --- |
| `contract_version` | `adt.portable-cold-review-work-order.v0` |
| `id` | Work-order ID |
| `operation` | `COLD_REVIEW` |
| `role` | `REVIEWER` |
| `goal` | Neutral review goal |
| `acceptance_criteria` | One or more `{id, text}` objects with unique IDs |
| `constraints` | String array; may be empty |
| `non_goals` | String array; may be empty |
| `artifact` | Artifact object below |
| `permissions` | Permission object below |
| `budget` | `{"wall_seconds": positive integer}` |
| `required_capabilities` | String array; may be empty |
| `required_evidence` | Requirement-name array; may be empty |
| `independence` | Independence object below |
| `review_paths` | At least two path IDs, exactly matching the manifest set |
| `result_contract` | `ADT_PORTABLE_COLD_REVIEW_RESULT_V0` |

`artifact` has exactly:

- `repository_id`, `base_revision`, and `candidate_revision` as non-blank
  identifiers;
- `snapshot_sha256`, binding every result and receipt to the declared immutable
  input;
- `paths`, a possibly empty string array. Empty means the whole artifact is in
  scope.

`permissions` has exactly `filesystem: READ_ONLY` and `network: DENY` or
`ALLOW`.

`independence` has exactly `fresh_context: true` and
`prior_results_visible: false`. A v0 work order cannot weaken this policy.
Provider, runtime, model, provider-specific flags, expected findings, and
provider-specific workflow topology do not belong in the work order.

## Result

Each path has one result object with exactly:

| Field | Contract |
| --- | --- |
| `contract_version` | `adt.portable-cold-review-result.v0` |
| `work_order_id` | Exact work-order ID |
| `path_id` | Exact manifest path ID |
| `work_order_sha256` | Exact work-order file digest |
| `artifact_snapshot_sha256` | Exact work-order artifact snapshot digest |
| `terminal_status` | `COMPLETED`, `CANCELLED`, `TIMED_OUT`, `FAILED`, or `UNSUPPORTED` |
| `release_recommendation` | Always `REPORT_ONLY` |
| `evidence` | Evidence objects below |
| `findings` | Finding objects below |
| `gaps` | String array |
| `degradations` | String array |

An evidence object has exactly `id`, `requirement`, and `observation`. Evidence
IDs are unique within the result. Every name in the work order's
`required_evidence` must be covered by at least one evidence object's
`requirement` for the path to avoid `HOLD`.

A finding has exactly `id`, `severity`, `summary`, and `evidence_refs`.
Severities are `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`. Finding IDs are unique;
`evidence_refs` is non-empty, unique, and resolves only to evidence in the same
result. Any finding severity produces `HOLD` in v0.

The result is model-authored data. Its identity and bindings are cross-checked
against launcher-authored manifest and receipt data; the model's claims
alone are not invocation evidence. An `evidence.observation` is declarative
model output in manual v0: the gate checks shape and coverage, not whether the
observation is true.

## Invocation receipt

Each path has one launcher-authored receipt object with exactly:

| Field | Contract |
| --- | --- |
| `contract_version` | `adt.portable-cold-review-receipt.v0` |
| `invocation_id` | Unique invocation ID across the bundle |
| `work_order_id` | Exact work-order ID |
| `path_id` | Exact manifest path ID |
| `identity` | Identity object below |
| `native_strategy` | Non-blank launcher-observed strategy description |
| `capabilities_observed` | Unique string array |
| `permissions_observed` | Same closed shape as work-order permissions |
| `independence_observed` | Same closed shape as work-order independence |
| `bindings` | Binding object below |
| `terminal_status` | Same enum and exact value as the result |
| `timing` | Timing object below |
| `usage` | Usage object below |
| `degradations` | String array |

`identity` has exactly `provider`, `runtime`, `model`, and
`observed_by: LAUNCHER`. The first three values exactly match
`launcher_identity` in the manifest. A syntactically valid identity using
`UNKNOWN`, `UNSPECIFIED`, or `UNAVAILABLE`, case-insensitively, produces
`HOLD`.

`bindings` has exactly `work_order_sha256`, `artifact_snapshot_sha256`, and
`result_sha256`; all must match the verified files and work order. `timing` has
exactly a non-blank `started_at` and non-negative `elapsed_ms`. `usage` has
exactly `input_tokens` and `output_tokens`, each a non-negative integer or
`null`.

Observed permissions must exactly match requested permissions. Missing required
capabilities produce `HOLD`. Identity, permission, terminal-status, object-ID,
path-ID, or digest disagreement is an invalid cross-object binding and exits
nonzero.

Receipt identity, capabilities, permissions, timing, usage, and independence
are launcher-reported in manual v0. The gate checks internal consistency; it
does not independently prove those claims or that one reviewer could not see
the other's output.

## Gate semantics

For a structurally valid, consistently bound bundle, the deterministic output
has exactly these result fields plus the CLI success envelope:

```json
{
  "ok": true,
  "command": "review-gate",
  "verdict": "REPORT_ONLY",
  "reason_codes": [],
  "path_ids": ["path-alpha", "path-beta"]
}
```

`path_ids` and `reason_codes` are sorted; no timestamp or generated ID is
added. Path declaration order therefore cannot change the output.

`REPORT_ONLY` requires every path to be `COMPLETED`, within its declared wall
budget, fully identified, capability-complete, evidence-complete, independent
as requested, and free of findings, gaps, or degradations. Otherwise the
verdict is `HOLD`, with one or more path-qualified reason codes.

`REPORT_ONLY` means only that this manual evidence bundle is internally
consistent and contains no declared blocker. It is never a green result,
acceptance decision, or release approval.

Malformed JSON, duplicate JSON fields, closed-shape violations, unsafe or
duplicate paths, digest mismatch, missing or duplicate review declarations,
dangling evidence references, and cross-object binding mismatch exit nonzero
with JSON on stderr. They never become normal success. The gate never emits
`PROCEED`, `ACCEPT`, or `NEEDS_DECISION`.

## Deferred boundaries

v0 deliberately does not:

- launch or cancel a native backend;
- prove that launcher identity or independence observations are truthful;
- verify that declared evidence observations correspond to repository facts;
- hide one result from another by itself;
- sign or durably store the bundle;
- compare reviewer conclusions or adjudicate findings;
- turn a clean report into a release authorization;
- support filesystems that cannot provide stable local file identities for
  duplicate-reference detection;
- provide a general schema engine or workflow format.

Those capabilities require backend adapters, sandbox and snapshot evidence,
or an explicit later product decision. They are not implied by a green v0
gate.
