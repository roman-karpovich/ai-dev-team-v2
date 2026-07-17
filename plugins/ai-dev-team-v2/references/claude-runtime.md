# Claude runtime boundary

Load this reference only when the active host is Claude Code, and do so before
repository or artifact exposure, ADT state, or editing. For a cold review,
complete the independence preflight before applying this runtime choice.

## Select visibly

- Follow the owner's explicit model choice when it is available and permitted
  by the applicable data policy.
- Without an explicit choice, prefer Opus 4.8 for bounded, well-specified, or
  routine work. Prefer Fable 5 for highest-complexity, long-horizon,
  architecture-wide, or high-ambiguity work.
- Treat host, model, task complexity, and ADT assurance profile as independent.
  Profiles never route models.
- Do not build an automatic router, silently fall back, or retry through a CLI,
  SDK, or API. If the selected model is unavailable, ineligible, or refuses
  the work, return control to the owner for a visible choice.
- Do not restart simple work already running in Fable merely to downgrade. If
  Opus is materially underpowered, recommend a fresh Fable session before
  repository exposure; continue only when the owner visibly accepts the
  tradeoff.

Manual examples:

```text
claude --model claude-opus-4-8
claude --model claude-fable-5
```

## Record identity honestly

After conclusions are fixed, record the actual model and any visible switch or
fallback only when the host or launcher exposes reliable evidence. Otherwise
record `unknown`. Model-authored self-report is not execution evidence. Keep
launcher-owned identity evidence separate from neutral review input so it does
not prime another path.
