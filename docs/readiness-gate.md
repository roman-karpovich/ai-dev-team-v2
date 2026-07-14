# VERIFY implementation readiness gate

Production VERIFY implementation remains blocked until all items below are
complete and the owner records GO.

- [ ] State, evidence, risk, adapter, ledger, and evaluation contracts are
      self-contained and accepted.
- [ ] Contract expectations were derived independently from any executable
      mirror.
- [ ] Schema strategy was selected by an evidence-producing spike.
- [ ] Snapshot capture, mutation detection, cleanup, and secret failure behavior
      were demonstrated on real fixtures.
- [ ] Sandbox restrictions were demonstrated with negative fixtures.
- [ ] Every native execution backend admitted to the initial evaluation profile
      accepts the portable work-order and result contracts and has versioned
      capability and invocation receipts.
- [ ] Missing or misstated required backend capabilities have explicit
      fail-closed or degraded outcomes.
- [ ] High-risk unverifiable evidence has a fail-closed outcome.
- [ ] Evaluation corpus and blinded labels are sealed and versioned.
- [ ] The frozen-v1 comparison baseline is aligned.
- [ ] Statistical promotion rules were fixed before evaluation.
- [ ] Complexity and maintenance estimates were recalculated after the spikes.
- [ ] Coexistence and rollback behavior are documented.

Until GO, there is no production `src/` tree.
