# AI Dev Team v2

AI Dev Team v2 is an experimental plugin for running supervised, autonomous
software-development tasks in Codex or Claude Code. You discuss the task and
material decisions with the agent, confirm the resulting direction in normal
conversation, and let it implement, verify, repair, and close out the work
without asking you to operate the workflow machinery.

The plugin combines native host execution with a small deterministic `adt`
state kernel. It keeps task continuity, worktree snapshots, checkpoints, and
handoffs durable while leaving coding and review judgment to the active host.

## Status

`v0.1.53` is the current experimental supervised-autonomy prerelease. It is ready
for dogfood on real repositories with an owner available for genuine product,
architecture, scope, or release-authority forks.

This release is not a production VERIFY engine, a general workflow
orchestrator, or a guarantee that unattended execution will always produce a
correct result. Cross-provider handoff and independent-review composition are
still explicit and manual. Workflow completion is separate from review verdict,
release recommendation, and publication authority.

## What works today

- dialogue-first development with a bounded `grill me` pass for nontrivial
  tasks;
- conversational owner confirmation followed by autonomous BUILD, VERIFY, and
  bounded REPAIR;
- evidence-based review with immutable scope and findings-first output;
- durable task state, checkpoints, pause/resume, takeover, and manual handoff;
- a compact KB bundle built around `task.md` and `closeout.md`;
- a privacy-minimized `adt report` for process analysis;
- fail-closed local installation and installed-payload verification for Codex
  and Claude Code.

The plugin never chooses or launches another provider automatically.

## Requirements

- macOS, Linux, or another Unix-like environment with Bash and `make`;
- Git and Python 3.10 or newer;
- Codex with plugin marketplace support, Claude Code with plugin support, or
  both;
- `~/.local/bin` on `PATH` after installation.

The installer registers a local marketplace and links `~/.local/bin/adt` to the
selected checkout. Install from a permanent directory: moving or deleting that
checkout breaks the CLI and invalidates the marketplace source.

## Install v0.1.53

Clone the release into a durable location:

```bash
mkdir -p "$HOME/src"
git clone --branch v0.1.53 --depth 1 \
  https://github.com/roman-karpovich/ai-dev-team-v2.git \
  "$HOME/src/ai-dev-team-v2"
cd "$HOME/src/ai-dev-team-v2"
```

Choose exactly one install target:

| Hosts | Command | Requirement |
| --- | --- | --- |
| Codex only | `make mvp-install-codex` | `codex` is installed |
| Claude only | `make mvp-install-claude` | `claude` is installed |
| Both | `make mvp-install` | both CLIs are installed |

The installer fails rather than silently replacing an existing `adt` path,
switching a marketplace to another checkout, or accepting a stale plugin
payload.

Make the CLI visible in the current shell and add the equivalent export to your
shell startup file:

```bash
export PATH="$HOME/.local/bin:$PATH"
adt --help
```

Start a new Codex task or Claude session after every install or update. Existing
sessions may retain the previously loaded skill text.

## Run your first development task

Open the repository you want to change as the active Git worktree. In Codex:

```text
$ai-dev-team:develop Implement replay-safe ingestion without changing the public API. Grill me.
```

In Claude Code:

```text
/ai-dev-team:develop Implement replay-safe ingestion without changing the public API. Grill me.
```

For a nontrivial task the agent follows this protocol:

```text
ORIENT -> discuss material decisions -> conversational confirmation
       -> BUILD -> VERIFY -> bounded REPAIR -> CLOSEOUT + KB
```

The agent first investigates repository facts, explains its understanding of
the task, and raises a bounded set of contentious assumptions, risks, and real
forks. Questions and decisions already resolved in the current conversation
count; the agent must not repeat them as ceremony. An explicit `grill me`
requests a full refinement pass even when the initial request looks complete.

Answer in the same task. An ordinary `go`, `yes`, `да`, or `го` is sufficient
confirmation; you do not need to line-review a generated specification or
invoke the skill again. After confirmation, the agent continues autonomously
within the agreed authority. It asks again only when new evidence exposes a
genuine product, architecture, scope, release-authority, or other
hard-to-reverse fork. Small explicit reversible tasks may skip the grill unless
you request it.

You normally do not run `adt start`, manage leases, or issue checkpoint
commands yourself. The skill owns that lifecycle.

## Durable task artifacts

The normal human-readable bundle is intentionally small:

- `task.md` contains the current effective specification and an append-only log
  of material decisions;
- `closeout.md` contains the outcome, exact commit or PR references, regression
  evidence, independent-review state, remaining risks and rollout notes, and
  one next action.

The agent writes these files only to a destination you selected or to an
existing in-worktree KB/docs convention. If neither exists, it returns a
copy-ready bundle and asks one routing question before making a tracked write.

Raw red/green logs are not archived by default. ADRs, runbooks, migration notes,
review reports, and reproduction notes are added only when they have durable
value of their own, then linked from the closeout instead of duplicated.

## Process report

Ask the agent for an `adt report` when you want to compare task runs or analyze
process efficiency. Manual operator forms are also available:

```bash
adt --workspace "$WORKSPACE" report
adt --workspace "$WORKSPACE" report \
  --output "$BUNDLE_DIR/run-report.json"
```

The report is a deterministic projection of persisted task state. It includes
task kind/status, lifecycle timestamps and counts, plus the persisted snapshot
identity. It omits workspace paths, host values, goals, summaries, notes,
reasons, leases, file paths, and unobserved model, token, cost, or review
metrics. It does not claim to observe the current worktree. Prefer an output
directory outside the worktree so the report itself does not create candidate
drift.

## Review a change

Use an exact committed range and accepted intent. In Codex:

```text
$ai-dev-team:review Review <base-sha>..<head-sha> against the accepted task contract. Findings first; do not edit.
```

In Claude Code:

```text
/ai-dev-team:review Review <base-sha>..<head-sha> against the accepted task contract. Findings first; do not edit.
```

For a cold or independent review, use a fresh neutral session and a separate
checkout. A single clean review is evidence, not trusted release acceptance.
Counted cold reviewers do not contact the owner; missing normative input or a
missing sealed artifact destination produces `HOLD`.

See [MVP usage](docs/mvp-usage.md) and the
[cold-review contract](plugins/ai-dev-team-v2/references/cold-independent-review.md)
for the full boundary.

## Resume and hand off

Task state is stored under the Git common directory and keyed by worktree.
Snapshots bind the commit and the staged, unstaged, and untracked change set;
they do not store file bodies or patches.

The active agent can pause, resume, or hand a task to the other host. Handoff
does not launch that host. Open a fresh session there and invoke the same skill
with a continuation request, for example:

```text
/ai-dev-team:develop Continue the handed-off task from its checkpoint.
```

The lease is cooperative fencing against stale sessions, not a security
boundary against local processes that can read Git-private state.

## Update

Keep using the same permanent checkout:

```bash
cd "$HOME/src/ai-dev-team-v2"
git fetch --tags origin
git checkout --detach <new-release-tag>
```

Run the same host target you selected during installation:

```bash
make mvp-install-codex   # Codex only
make mvp-install-claude  # Claude only
make mvp-install         # both hosts
```

Then open a new host session. If the configured local marketplace points to a
different checkout, the installer stops and asks you to resolve that source
explicitly instead of rewriting it.

## Replace the frozen v1 plugin

v1 and v2 use distinct marketplace identities. If v1 is still configured, the
normal installer stops. To replace v1 explicitly on both hosts:

```bash
make mvp-replace-v1
```

For one host only:

```bash
./scripts/install-mvp --codex --replace-v1
./scripts/install-mvp --claude --replace-v1
```

The frozen [v1 repository](https://github.com/roman-karpovich/ai-dev-team)
remains a historical comparison and rollback baseline; v2 does not copy or
depend on its implementation.

## MVP limits

- no automatic provider/model dispatch;
- no production VERIFY assurance or automatic release authorization;
- no general workflow engine;
- manual cross-provider handoff and cold-review composition;
- local cooperative state, not a hostile-process security boundary;
- an owner is still required for weak requirements and genuine hard-to-reverse
  decisions.

The long-term direction and deferred assurance boundaries live in the
[product mission](docs/mission.md), [architecture](docs/architecture.md), and
[readiness gate](docs/readiness-gate.md).

## Development

Run the offline deterministic suite:

```bash
make test
```

Contributions should start with the smallest behavior-focused failing test and
preserve public-source hygiene. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[MVP operations](docs/mvp-operations.md).

## License

AI Dev Team v2 is available under the [MIT License](LICENSE).
