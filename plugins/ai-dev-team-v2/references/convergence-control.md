# Convergence control

Load this reference for the routed risk classes, cold-review planning, repair
cycles, evidence reuse, or interleaved plugin and card work. It is a compact
decision policy, not a new workflow engine, mandatory artifact, or state
schema. Do not add telemetry fields or ask a model to self-report launcher
facts merely to satisfy it.

## Synthesize risk before candidate edits

Use one compact pre-build risk synthesis only when the change touches stateful
ingestion, replay or cursor behavior, transactions or concurrency, migrations
or mixed versions, retention, rebuild or rollback, malformed or failure
behavior, production query bounds, or operational prerequisites. Cover only
the applicable invariants, writers and ordering, failure windows, recovery
path, read bound, rollout precondition, and smallest discriminating seam. Turn
a credible risk into a test, explicit design constraint, owner decision, or
declared non-goal before editing.

Keep the synthesis in the working plan unless a durable decision already
belongs in normal repository documentation or a checkpoint. Do not require a
durable ledger or this synthesis for every small task.

## Bind candidates, purposes, and generations

`ArtifactKey` is repository identity + immutable `BASE` + immutable `HEAD` +
the ADT snapshot digest including dirty state. `ReviewKey` is `ArtifactKey` +
task-contract or work-order digest + assurance profile. One review generation
is every counted cold path for one `ReviewKey`; several reviewers on that
candidate still consume one generation.

Declare one purpose before each path:

- `adversarial-integration` challenges the design before final freeze.
- `known-finding-validation` checks a repaired finding in its informed
  lineage; it is not a fresh cold oracle.
- `diagnostic-cold` explicitly spends independence to reduce uncertainty on a
  non-final candidate.
- `final-cold` is the final acceptance oracle for the declared profile.
- `complementary-final-cold` adds a separately required final path, such as an
  owner-selected two-model profile; it is not a default restart.

A final-acceptance cold path is eligible ex ante only when its artifact is
immutable and clean, contract and accepted domain are fixed, focused checks
are current for its `ArtifactKey`, adversarial integration is done, known
blockers, evidence gaps, and owner decisions are closed, and no edit lane is
active or planned. An explicit `diagnostic-cold` path may reduce uncertainty
but never counts as final acceptance. Do not launch cold review on a candidate
with a known-open blocker or planned edit.

For one generation, declare all required cold-path purposes, run them one at a
time under the sealed independence boundary, then consolidate their findings
and repair once. Multiple sealed paths do not create multiple repair cycles.

## Bound repair cycles

A material `HOLD` generation reports a reachable accepted-scope defect or a
missing required assurance fact that demands a candidate, contract, scope, or
architecture decision. Count the generation once after its sealed paths are
consolidated.

- The first material `HOLD` generation permits one consolidated repair and
  focused validation by the finding-owning lineage.
- A second distinct repaired `ReviewKey` with a material `HOLD` requires
  `REASSESS` before more edits: consolidate recurring causes, challenged
  assumptions, scope growth, and viable alternatives.
- A third material `HOLD` requires a scope split, architecture change,
  explicit owner decision, or documented rationale that continuing is cheaper
  and safer.

Infrastructure failure, not launched, interrupted, no usable result,
independence compromised, and capability-only gaps stay fail-closed but do not
consume a material repair cycle. They may require a valid replacement path;
they never become a pass.

## Reuse exact evidence, not mutable confidence

Treat reusable verification as an immutable content-addressed receipt concept,
not a mutable cache. An exact receipt matches `ArtifactKey`, canonical command,
working directory and selection, toolchain, dependency and build digests,
fixtures, migrations, schema and database reset, plus relevant environment,
database and container identity. Never rerun a successful exact identity.

After a candidate change, run the smallest affected check and one proportionate
final full gate. Do not reuse evidence across SHAs automatically until
dependency-aware invalidation exists. Unknown or unavailable is not zero. Until
a launcher or backend emits receipts from observed execution, preserve ordinary
command and environment evidence without inventing equivalence.

## Separate experiments and observe only what is observable

When a card exposes a compatible plugin-process defect, separate the two work
streams. Checkpoint the card, batch compatible plugin surgery, install one
payload, then resume the card. Do not cachebust for documentation or test-only
adjustments that cannot affect installed behavior.

Identity, start, end, terminal state, tokens, and cost are metrics only when a
launcher or backend actually observes them; never ask a model to attest them.
Until then they are policy targets, not required fields. Prefer premature-cold
rate over penalizing an eligible final cold path that finds a material defect.
Compute same-identity rerun rate, generation counts, duration, tokens, and cost
only from observed data; keep unknown or unavailable values explicit.
