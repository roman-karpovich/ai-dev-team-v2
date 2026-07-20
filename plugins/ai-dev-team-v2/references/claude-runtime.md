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
- Use `xhigh` effort for both models.
- Treat a review as security-focused only when security assurance is its
  primary accepted goal, not merely one proportional dimension of an ordinary
  review. For security-focused analysis, prefer Opus 4.8 unless the owner
  visibly chooses another available, eligible model; when this rule and the
  complexity preference above both apply, this rule wins.
- Treat host, model, task complexity, and ADT assurance profile as independent.
  Profiles never route models.
- Model eligibility depends on the organization's data policy and retention
  configuration. An invalid-request response can indicate ineligibility, so
  check eligibility before treating the invocation as malformed.
- Do not build an automatic router, silently fall back, or automatically
  repeat or replace the selected model through a CLI, SDK, or API. Ordinary
  transport retries of the same request are not a model change. If the
  selected model is unavailable, ineligible, or refuses the work, return
  control to the owner for a visible choice; inside a counted cold path, a
  refusal is terminal — record it in the sealed output and return only the
  opaque terminal marker, without contact, fallback, or automatic retry.
- Do not restart simple work already running in Fable merely to downgrade. If
  Opus is materially underpowered, recommend a fresh Fable session before
  repository exposure; continue only when the owner visibly accepts the
  tradeoff.

Manual examples:

```text
claude --model claude-opus-4-8 --effort xhigh
claude --model claude-fable-5 --effort xhigh
```

## Communicate deliberately

Do not narrate routine tool use. Outside a counted cold path, communicate
material decisions, blockers, status the owner requested, and the final
owner-facing summary. Inside a counted cold path, keep conclusions in the
sealed output and return only the opaque terminal marker.

## Record identity honestly

After conclusions are fixed, record the actual model and any visible switch or
fallback only when the host or launcher exposes reliable evidence. Otherwise
record `unknown`. Model-authored self-report is not execution evidence. Keep
launcher-owned identity evidence separate from neutral review input so it does
not prime another path.
