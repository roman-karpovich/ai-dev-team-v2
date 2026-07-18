# Cold independent review

Load this reference only for a review explicitly requested as cold,
independent, or two-model. Complete the preflight before artifact inspection,
repository context, or ADT state.

## Preflight

Inspect all context already present in the session. Safe input is limited to
authoritative intent, owner decisions, neutral scope and immutable snapshot,
acceptance criteria, accepted input domain, explicit non-goals, and permitted
checks. Prior findings, suspected locations, severities, proposed fixes,
expected conclusions, builder transcripts, imported summaries, and
finding-bearing memory contaminate a cold path.

Inference-visible context includes shared coordination surfaces, even when the
session itself started empty. Before and during a counted cold path, do not
inspect agent, task, or thread registries, teammate status feeds, messages,
transcripts, summaries, or another path's progress. A read-only registry can
still disclose prior findings or suspected locations. The launcher should
withhold those tools where possible and otherwise state this prohibition in
the neutral work order.

If contaminated, stop as `independence-compromised`. Telling the model to
ignore known findings cannot restore independence. Start a fresh one-off
memory-clean session before any artifact or state exposure:

```text
codex -c 'memories.use_memories=false' -c 'memories.generate_memories=false'
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude --no-session-persistence
```

Do not change global memory configuration for a one-off review. If an
equivalent clean session is impossible, continue only after the user accepts
that the result is non-independent.

## Isolate the path

- Give every counted cold path a distinct review checkout exposing the accepted
  immutable `BASE..HEAD`, a fresh inference context, standalone path-specific
  `kind=review` state, and its own sealed output.
- Give the reviewer only the neutral contract and repository instructions.
  Do not pre-create review state or pass a development task's context.
- Let the reviewer start standalone `kind=review` state after preflight and
  read-only worktree orientation. `status` is safe only while it omits goals,
  checkpoints, and completion summaries.
- Never hand off between cold paths, resume or share another path's ADT state,
  or read its context. Handoff and context are only for the same review lineage
  or explicitly non-cold continuation; they cannot create a fresh cold path.
- Keep every other path's result, model evidence, transcript, and findings
  hidden until all counted paths have fixed and sealed their conclusions.
  Adjudicate only after that embargo ends.
- Count only a fresh preflighted inference context. Builder subagents, repeated
  passes in the builder session, and a model-name change inside contaminated
  context are not independent paths.

## Conclude fail-closed

One path cannot establish trusted acceptance. A two-model request requires two
separate sealed paths plus post-embargo adjudication, but the skill never
launches the other provider automatically. Missing required evidence, contaminated context,
unresolved material disagreement, or a blocking accepted-contract violation
remains `HOLD` unless the owner explicitly waives or supersedes it.

Attach reliable launcher evidence for actual model, immutable inputs,
permissions, and timing after conclusions are fixed. Do not ask a reviewer to
attest facts it cannot observe. A later review that knows a repaired finding is
repair validation; use another neutral preflighted session for a new cold
oracle.
