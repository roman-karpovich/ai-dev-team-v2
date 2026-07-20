from __future__ import annotations

import ast
import json
import re
import shlex
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins/ai-dev-team-v2"
SKILLS = PLUGIN / "skills"
LIFECYCLE = PLUGIN / "references/task-lifecycle.md"
EXPECTED_REFERENCES = {
    "develop": {
        "claude-runtime.md",
        "convergence-control.md",
        "incident-observability.md",
        "publication-boundary.md",
        "semantic-boundaries.md",
        "task-lifecycle.md",
        "verification-environments.md",
    },
    "review": {
        "claude-runtime.md",
        "cold-independent-review.md",
        "convergence-control.md",
        "incident-observability.md",
        "publication-boundary.md",
        "semantic-boundaries.md",
        "task-lifecycle.md",
        "verification-environments.md",
    },
}
REPOSITORY_BLOB_ROOT = (
    "https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/"
)
CANDIDATE_BINDING_ROUTE = (
    "check:executes-source|artifact|runtime",
    "references/verification-environments.md",
    "before:check-execution|result-interpretation",
)
DIALOGUE_REFINEMENT_ROUTE = (
    "dialogue:owner-correction|design-hypothesis|scope-challenge",
    "references/convergence-control.md",
    "before:task-action|candidate-edit|review-launch|worker-dispatch|publish",
)
PUBLICATION_GATE_ROUTE = (
    "publication:commit-metadata|tag-metadata|branch-name|github-metadata|public-prose|ci-summary",
    "references/publication-boundary.md",
    "immediately-before:persistent-write",
)
EXPECTED_TASK_STATE_COMMANDS = {
    tuple(shlex.split(command))
    for command in (
        'adt --workspace "$WORKSPACE" status',
        'adt --workspace "$WORKSPACE" list',
        'adt --workspace "$WORKSPACE" report',
        'adt --workspace "$WORKSPACE" report --task "$TASK_ID"',
        'adt --workspace "$WORKSPACE" report --task "$TASK_ID" --output "$FILE"',
        'adt --workspace "$WORKSPACE" start --host "$HOST" --kind develop --goal "$GOAL"',
        'adt --workspace "$WORKSPACE" start --host "$HOST" --kind review --goal "$GOAL"',
        'adt --workspace "$WORKSPACE" resume --host "$HOST"',
        'adt --workspace "$WORKSPACE" resume --host "$HOST" --accept-drift',
        'adt --workspace "$WORKSPACE" takeover --host "$HOST" --reason "$REASON"',
        'adt --workspace "$WORKSPACE" context',
        'adt --workspace "$WORKSPACE" checkpoint --host "$HOST" --lease "$LEASE" --note "$NOTE"',
        'adt --workspace "$WORKSPACE" pause --host "$HOST" --lease "$LEASE" --reason "$REASON"',
        'adt --workspace "$WORKSPACE" handoff --host "$HOST" --lease "$LEASE" --to "$TARGET" --note "$NOTE"',
        'adt --workspace "$WORKSPACE" complete --host "$HOST" --lease "$LEASE" --summary "$SUMMARY"',
    )
}
EXPECTED_SKILL_ROUTES = {
    "develop": [
        (
            "host:claude",
            "references/claude-runtime.md",
            "before:repository-exposure|adt-state|editing",
        ),
        (
            "always",
            "references/task-lifecycle.md",
            "after:claude-if-triggered;before:adt-state|mutation",
        ),
        PUBLICATION_GATE_ROUTE,
        DIALOGUE_REFINEMENT_ROUTE,
        (
            "depends-on:auto-reporting|framework-lifecycle|process-lifecycle|termination|propagation|bootstrap|event-cardinality",
            "references/incident-observability.md",
            "before:task-contract|candidate-edit",
        ),
        (
            "acceptance:input-domain|upstream-replacement:removed,deprecated,unavailable->local-derivation",
            "references/semantic-boundaries.md",
            "before:task-contract",
        ),
        (
            "risk:stateful-ingestion|replay-cursor|transactions-concurrency|migrations-mixed-versions|retention-rebuild-rollback|malformed-failure|production-query-bounds|operational-prerequisites|repair:material-hold|plugin-card-interleave",
            "references/convergence-control.md",
            "before:candidate-edit|repair-restart|plugin-install",
        ),
        CANDIDATE_BINDING_ROUTE,
        (
            "verification:unavailable-dependency|runtime|production-bootstrap|environment-equivalence",
            "references/verification-environments.md",
            "before:verification-selection",
        ),
    ],
    "review": [
        (
            "request:cold|independent|two-model",
            "references/cold-independent-review.md",
            "before:artifact-inspection|repository-context|adt-state",
        ),
        (
            "request:cold|independent|two-model|repair:material-hold|evidence:reuse",
            "references/convergence-control.md",
            "after:cold-preflight-if-triggered;before:review-key|check-selection|counted-cold-launch",
        ),
        (
            "host:claude",
            "references/claude-runtime.md",
            "after:cold-if-triggered;before:repository-exposure|adt-state|artifact-inspection",
        ),
        (
            "always",
            "references/task-lifecycle.md",
            "after:prior-preflights;before:adt-state|mutation",
        ),
        PUBLICATION_GATE_ROUTE,
        DIALOGUE_REFINEMENT_ROUTE,
        (
            "depends-on:auto-reporting|framework-lifecycle|process-lifecycle|termination|propagation|bootstrap|event-cardinality",
            "references/incident-observability.md",
            "before:claim-artifact-inspection",
        ),
        (
            "acceptance:input-domain|upstream-replacement:removed,deprecated,unavailable->local-derivation",
            "references/semantic-boundaries.md",
            "before:claim-judgment",
        ),
        CANDIDATE_BINDING_ROUTE,
        (
            "verification:unavailable-dependency|runtime|production-bootstrap|environment-equivalence",
            "references/verification-environments.md",
            "before:verification-selection",
        ),
    ],
}
REQUIRED_SPECIALIST_BOUNDARIES = {
    "incident-observability.md": {
        (
            "causal-reproduction",
            "probe:adds-unverified-causal-precondition;safe-probe:unavailable-or-negative",
            "establish-precondition-from:repository,deployment,incident-evidence",
            "causality:unverified;develop:pause-unless-owner-revises-goal;review:withhold-affected-claim",
        ),
        (
            "final-observer-evidence",
            "claim:incident-outcome",
            "compare:baseline,candidate@same-final-observer;measure:reachability,ordering,propagation-or-exit,exact-event-cardinality",
            "claim:withhold",
        ),
    },
    "verification-environments.md": {
        (
            "candidate-binding",
            "check:executes-source|artifact|runtime",
            "prove:executed-candidate->intended-worktree|commit|snapshot;cached|baked|generated:rebuild|refresh|fingerprint",
            "candidate-binding:unverified;affected-claim:withhold",
        ),
        (
            "discriminating-seam",
            "check:selected",
            "record:proves,cannot-prove;claim:within-seam-only",
            "outside-seam:unverified",
        ),
        (
            "secret-safe-setup",
            "required-environment:unavailable",
            "forbid:secret-files,credentials,tokens,mutable-runtime-state@workspace,tool-output,logs,checkpoints,review-evidence;allow:checked-in-fixtures,dummy-values,secret-free-config",
            "verification:blocked-if-no-safe-setup",
        ),
    },
}
QUIESCENT_COLD_BOUNDARIES = {
    (
        "quiescent-counted-path",
        "before:counted-cold-launch",
        "other-child-agents:terminal;counted-reviewers:one-at-a-time;reviewer-handle:hidden-from-other-agents",
        "launch:defer",
    ),
    (
        "sealed-artifact-output-isolation",
        "before:counted-cold-launch",
        "sealed-artifact:reviewer-owned;destinations:absolute;launcher-output-if-present:distinct-canonical-target",
        "launch:defer",
    ),
    (
        "sealed-conclusion-embargo",
        "from:launch;until:conclusion-sealed",
        "forbid:spawn-agent,send-message,follow-up,interrupt;wait:terminal-result",
        "path:independence-compromised;conclusion:do-not-count",
    ),
    (
        "unsolicited-cross-agent-contact",
        "message:cross-agent-unsolicited",
        "stop:review",
        "path:independence-compromised;conclusion:do-not-count",
    ),
    (
        "outbound-cross-agent-contact",
        "action:cross-agent-question-or-message",
        "stop:review;reply:do-not-wait-or-read;state:complete-if-owned;return:terminal",
        "path:independence-compromised;conclusion:do-not-count",
    ),
}
MODEL_FIELD = r"model(?:_name|_id)?"
MODEL_KEY = rf"(?:(?:default|preferred|selected|fallback)_)?{MODEL_FIELD}"
MODEL_PLACEHOLDERS = frozenset({"unknown", "string", "null", "none"})
MODEL_POLICY_SIGNAL = re.compile(
    r"""
    (?<![\w-])--model(?![\w-])
    |\bmodel(?:[-_ ]+(?:policy|selection|choice|routing))\b
    |\b(?:choose|prefer|select|route|dispatch|fallback|switch|upgrade|downgrade)\w*
       \s+(?:(?:a|an|the|default|preferred|selected|specific|configured)\s+){0,2}models?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
MODEL_CONTROL = re.compile(
    rf"""
    (?:(?<![\w-]){MODEL_KEY}(?![\w-])|["']{MODEL_KEY}["']\s*\]?)
    \s*=(?![ \t]*["']?(?:unknown|string|null|none)["']?[ \t]*(?:[,;)}}\]]|$))
    [ \t]*\S
    |(?<![\w-])(?:["']{MODEL_KEY}["']|{MODEL_KEY})(?![\w-])\s*:
    (?![ \t]*["']?(?:unknown|string|null|none)["']?[ \t]*(?:[,}}\]#]|$))
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", read(path), re.DOTALL)
    if match is None:
        raise AssertionError(f"missing or malformed frontmatter: {path}")

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise AssertionError(f"unsupported frontmatter line in {path}: {line!r}")
        values[key.strip()] = value.strip()
    return values, match.group(2)


def markdown_links(text: str) -> list[str]:
    return re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text)


def plugin_resource_locators(text: str) -> list[str]:
    return re.findall(r"`(references/[a-z0-9-]+\.md)`", text)


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:text|bash|sh)?\n(.*?)```", text, re.DOTALL)


def fenced_adt_commands(text: str) -> set[tuple[str, ...]]:
    return {
        tuple(shlex.split(line))
        for block in fenced_blocks(text)
        for raw_line in block.splitlines()
        if (line := raw_line.strip()).startswith("adt ")
    }


def markdown_row(line: str) -> tuple[str, ...]:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    normalized: list[str] = []
    for cell in cells:
        value = cell.strip().replace(r"\|", "|")
        if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
            value = value[1:-1]
        normalized.append(value)
    return tuple(normalized)


def markdown_table_rows(text: str, header: str) -> list[tuple[str, ...]]:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.strip() == header]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one table: {header}")

    index = matches[0]
    width = len(markdown_row(header))
    if index + 1 >= len(lines) or markdown_row(lines[index + 1]) != ("---",) * width:
        raise AssertionError(f"malformed table separator: {header}")

    rows: list[tuple[str, ...]] = []
    for line in lines[index + 2 :]:
        if not line.strip().startswith("|"):
            break
        row = markdown_row(line)
        if len(row) != width:
            raise AssertionError(f"malformed table row: {line!r}")
        rows.append(row)
    return rows


def skill_route_rows(text: str) -> list[tuple[str, ...]]:
    return markdown_table_rows(text, "| Trigger | Resource | Boundary |")


def policy_boundary_rows(text: str) -> set[tuple[str, ...]]:
    rows = markdown_table_rows(text, "| Boundary | Trigger | Required | On unmet |")
    if not all(all(row) for row in rows):
        raise AssertionError("empty policy boundary cell")
    if len({row[0] for row in rows}) != len(rows):
        raise AssertionError("duplicate policy boundary id")
    return set(rows)


def model_key(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(
        MODEL_KEY, value.replace("-", "_"), re.IGNORECASE
    ) is not None


def ast_target_keys(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.Subscript):
        key = node.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            return [key.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [key for item in node.elts for key in ast_target_keys(item)]
    return []


def ast_value_selects_model(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        if node.value is None:
            return False
        if isinstance(node.value, str):
            return node.value.strip().casefold() not in MODEL_PLACEHOLDERS
    if isinstance(node, ast.Name):
        return node.id.casefold() not in MODEL_PLACEHOLDERS
    return True


def python_has_model_selector(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return bool(MODEL_POLICY_SIGNAL.search(text) or MODEL_CONTROL.search(text))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if MODEL_POLICY_SIGNAL.search(node.value):
                return True
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is not None and ast_value_selects_model(value):
                if any(
                    model_key(key)
                    for target in targets
                    for key in ast_target_keys(target)
                ):
                    return True
        elif isinstance(node, ast.AugAssign):
            if any(model_key(key) for key in ast_target_keys(node.target)):
                return True
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            positional = [*node.args.posonlyargs, *node.args.args]
            defaults = zip(positional[-len(node.args.defaults) :], node.args.defaults)
            keyword_defaults = zip(node.args.kwonlyargs, node.args.kw_defaults)
            if any(
                model_key(argument.arg)
                and default is not None
                and ast_value_selects_model(default)
                for argument, default in (*defaults, *keyword_defaults)
            ):
                return True
        elif isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and any(
                    keyword.arg == "dest"
                    and isinstance(keyword.value, ast.Constant)
                    and model_key(keyword.value.value)
                    for keyword in node.keywords
                )
            ):
                return True
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "setdefault"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and model_key(node.args[0].value)
                and ast_value_selects_model(node.args[1])
            ):
                return True
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) >= 3
                and isinstance(node.args[1], ast.Constant)
                and model_key(node.args[1].value)
                and ast_value_selects_model(node.args[2])
            ):
                return True
            if any(
                model_key(keyword.arg) and ast_value_selects_model(keyword.value)
                for keyword in node.keywords
                if keyword.arg is not None
            ):
                return True
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and model_key(key.value)
                    and ast_value_selects_model(value)
                ):
                    return True
    return False


def installed_source_files(root: Path = PLUGIN) -> list[Path]:
    sources: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = read(path)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            sources.append(path)
    return sources


def has_model_selector(path: Path, text: str) -> bool:
    if path.suffix == ".py":
        return python_has_model_selector(text)
    if path.suffix == ".json":
        try:
            text = json.dumps(json.loads(text), separators=(",", ":"))
        except json.JSONDecodeError:
            pass
    return bool(MODEL_POLICY_SIGNAL.search(text) or MODEL_CONTROL.search(text))


def model_selector_sources(root: Path = PLUGIN) -> set[Path]:
    return {
        path.resolve()
        for path in installed_source_files(root)
        if has_model_selector(path, read(path))
    }


def repository_link_target(base: Path, target: str) -> Path | None:
    if target.startswith(REPOSITORY_BLOB_ROOT):
        return (ROOT / unquote(target.removeprefix(REPOSITORY_BLOB_ROOT))).resolve()
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None
    return (base / unquote(parsed.path)).resolve()


class SkillContractTest(unittest.TestCase):
    def test_installed_payload_has_exactly_two_explicit_skills(self) -> None:
        self.assertEqual(
            set(EXPECTED_REFERENCES),
            {path.name for path in SKILLS.iterdir() if path.is_dir()},
        )
        for name in EXPECTED_REFERENCES:
            skill = SKILLS / name
            metadata, _ = frontmatter(skill / "SKILL.md")
            self.assertEqual({"name", "description"}, set(metadata))
            self.assertEqual(name, metadata["name"])
            self.assertIn("explicit", metadata["description"].lower())
            self.assertIn(
                "allow_implicit_invocation: false",
                read(skill / "agents/openai.yaml"),
            )

    def test_each_skill_has_its_exact_resolved_resource_set(self) -> None:
        for name, expected in EXPECTED_REFERENCES.items():
            _, body = frontmatter(SKILLS / name / "SKILL.md")
            locators = plugin_resource_locators(body)
            self.assertEqual(expected, {Path(locator).name for locator in locators})
            for locator in locators:
                resolved = (PLUGIN / locator).resolve()
                self.assertTrue(resolved.is_relative_to(PLUGIN.resolve()), locator)
                self.assertTrue(resolved.is_file(), locator)

    def test_skill_route_tables_are_exact_and_ordered(self) -> None:
        for name, expected in EXPECTED_SKILL_ROUTES.items():
            _, body = frontmatter(SKILLS / name / "SKILL.md")
            with self.subTest(skill=name):
                self.assertEqual(expected, skill_route_rows(body))

    def test_candidate_binding_is_reachable_before_every_executed_check(self) -> None:
        for name in EXPECTED_SKILL_ROUTES:
            _, body = frontmatter(SKILLS / name / "SKILL.md")
            with self.subTest(skill=name):
                self.assertIn(CANDIDATE_BINDING_ROUTE, skill_route_rows(body))

        reference = read(PLUGIN / "references/verification-environments.md")
        preface = reference.split("## Required outcomes", 1)[0]
        self.assertIn("any check executes source, artifact, or runtime", preface)

    def test_convergence_control_is_conditional_and_identity_bound(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )

        self.assertLessEqual(len(reference.split()), 1200)
        self.assertIn(
            "Use one compact pre-build risk synthesis only when the change "
            "touches stateful ingestion, replay or cursor behavior, "
            "transactions or concurrency, migrations or mixed versions, "
            "retention, rebuild or rollback, malformed or failure behavior, "
            "production query bounds, or operational prerequisites.",
            reference,
        )
        self.assertIn(
            "Do not require a durable ledger or this synthesis for every small task.",
            reference,
        )
        self.assertIn(
            "`ArtifactKey` is repository identity + immutable `BASE` + "
            "immutable `HEAD` + the ADT snapshot digest including dirty state.",
            reference,
        )
        self.assertIn(
            "`ReviewKey` is `ArtifactKey` + task-contract or work-order digest "
            "+ assurance profile.",
            reference,
        )
        self.assertIn(
            "One review generation is every counted cold path for one `ReviewKey`; "
            "several reviewers on that candidate still consume one generation.",
            reference,
        )

    def test_material_dialogue_refines_contract_without_expanding_authority(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )

        self.assertIn(
            "Classify new material owner dialogue as an `authoritative owner "
            "correction`, `tentative design hypothesis`, or `scope challenge or "
            "question`.",
            reference,
        )
        self.assertIn(
            "An authoritative owner correction supersedes the affected contract "
            "term immediately after verifying discoverable facts.",
            reference,
        )
        self.assertIn(
            "A tentative design hypothesis permits only bounded read-only analysis "
            "until the owner accepts it; do not encode it as a decision.",
            reference,
        )
        self.assertIn(
            "A scope challenge or question audits the existing claim and is not "
            "authorization for code, branch, pull-request, or external mutation.",
            reference,
        )
        self.assertIn(
            "Contract authority and mutation authority are distinct.", reference
        )
        self.assertIn(
            "An authoritative correction changes acceptance but neither grants "
            "new mutation authority nor erases mutation authority already explicit "
            "in the active task.",
            reference,
        )
        self.assertIn(
            "Before replacement or publication, re-check that the action remains "
            "within that existing authorized scope.",
            reference,
        )
        self.assertIn(
            "Before task action, freeze incompatible code, review, worker, and "
            "publish lanes.",
            reference,
        )

    def test_material_dialogue_updates_one_effective_contract_and_pauses_on_forks(
        self,
    ) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )
        _, develop = frontmatter(SKILLS / "develop" / "SKILL.md")
        develop = " ".join(develop.split())

        self.assertIn(
            "For a material refinement, write one compact self-contained effective "
            "contract in the working plan: accepted outcome and domain; constraints "
            "and non-goals; repository policy; resolved `BASE_REF` and immutable "
            "`BASE_SHA`; verification obligations; open design choices; invalidated "
            "candidate, evidence, and reviews; and next permitted work.",
            reference,
        )
        self.assertIn(
            "Only when the change is durable and material to ADT state, checkpoint "
            "that complete effective contract once; do not emit a chain of "
            "correction notes.",
            reference,
        )
        self.assertIn(
            "Pause when an architecture decision remains open.", reference
        )
        self.assertIn(
            "Ordinary clarification needs neither a checkpoint nor a pause.",
            reference,
        )
        self.assertIn(
            "Checkpoint only a durable, material refinement as one complete "
            "effective contract; ordinary clarification needs no checkpoint.",
            develop,
        )
        self.assertNotIn("Checkpoint later owner changes", develop)

    def test_develop_grill_is_bounded_material_and_conversational(self) -> None:
        _, develop = frontmatter(SKILLS / "develop" / "SKILL.md")
        develop = " ".join(develop.split())

        for requirement in (
            "For every nontrivial task, ensure a bounded `grill me` dialogue has "
            "occurred before candidate edits.",
            "Count material questions and decisions already resolved in the current "
            "conversation; do not repeat them.",
            "Investigate repository context before asking questions.",
            "State the task's essence, surface contentious assumptions, risks, and "
            "genuine forks, then ask one coherent bounded batch of remaining material "
            "questions.",
            "Do not ask investigable or routine questions.",
            "If the owner explicitly says `grill me`, deepen the pass even when the "
            "task initially appears specified.",
            "Skip the grill for an explicit small, reversible task unless the owner "
            "requests it.",
            "Treat `да`, `го`, `так`, or equivalent plain-language agreement as "
            "confirmation.",
            "`task.md` is your synthesis and decision log, not an approval form.",
            "After confirmation, build, verify, and perform bounded repair "
            "autonomously.",
            "Reopen dialogue only for a newly discovered genuine fork.",
        ):
            self.assertIn(requirement, develop)

    def test_minimal_artifacts_and_private_report_are_one_shared_policy(self) -> None:
        lifecycle = " ".join(read(LIFECYCLE).split())
        operations = " ".join(
            read(ROOT / "docs/mvp-operations.md").split()
        )

        for requirement in (
            "During normal skill use, the agent runs lifecycle commands; do not ask "
            "the owner to operate the CLI.",
            "Treat plain-text replies in the same task as answers, corrections, or "
            "confirmation without requiring another skill invocation.",
            "`task.md` contains the current effective specification and an append-only "
            "log of material decisions.",
            "`closeout.md` records outcome, exact artifact references, regression "
            "coverage and evidence, independent-review state, risks and rollout, "
            "links, and one next action.",
            "Do not archive raw red and green logs by default.",
            "Create ADRs, runbooks, migration notes, review notes, or reproduction "
            "notes only when the knowledge is independently durable; link them "
            "instead of duplicating them.",
            "Never invent a cross-repository write.",
            "provide a copy-ready `task.md` and `closeout.md` bundle and ask one "
            "focused routing question before a tracked write",
            "A counted cold work order must provide its sealed artifact destination; "
            "if it does not, return a terminal gap or `HOLD` without contact or a "
            "tracked write.",
        ):
            self.assertIn(requirement, lifecycle)

        _, review = frontmatter(SKILLS / "review" / "SKILL.md")
        review = " ".join(review.split())
        self.assertIn(
            "Require the fixed work order to name the sealed artifact destination. "
            "If it does not, return a terminal gap or `HOLD` without contact or a "
            "tracked write.",
            review,
        )

        self.assertIn(
            "The report is a privacy-minimized projection of persisted task state, "
            "not a live worktree observation.",
            operations,
        )
        self.assertIn(
            "Writing an output file after a terminal snapshot can itself dirty the "
            "worktree; the report still describes the persisted latest snapshot.",
            operations,
        )
        self.assertIn("There is no `--include-text` mode.", operations)

    def test_publication_gate_blocks_unauthorized_cross_repo_provenance(self) -> None:
        boundary = " ".join(
            read(PLUGIN / "references/publication-boundary.md").split()
        )
        convergence = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )
        readme = " ".join(read(ROOT / "README.md").split())
        usage = " ".join(read(ROOT / "docs/mvp-usage.md").split())

        for name in EXPECTED_SKILL_ROUTES:
            _, body = frontmatter(SKILLS / name / "SKILL.md")
            with self.subTest(skill=name):
                self.assertIn(PUBLICATION_GATE_ROUTE, skill_route_rows(body))

        for requirement in (
            "Load this reference only immediately before a persistent publication "
            "write. Private drafting and discussion do not trigger it.",
            "The GitHub owner of the actual destination is the default trust domain.",
            "references to another owner do not.",
            "Put every known cross-domain identity from the task, plus any sensitive "
            "same-owner sibling identity, in a temporary patterns file, one case-"
            "insensitive literal per line.",
            "Resolve `DESTINATION_REPO` from the actual GitHub write target or "
            "canonical remote, never from the outbound text.",
            "`HOLD` means rewrite or generalize. There is no autonomous cross-owner "
            "bypass.",
            "On success, require contract `adt.publication-gate.v1`, the actual "
            "destination, and the unchanged byte count and SHA-256.",
            "The receipt attests only the supplied bytes. It does not inspect or "
            "attest a Git object graph, branch contents, refspec, or completed write.",
            "Patterns and receipts are transient private control data, not KB, CI, "
            "or closeout artifacts.",
        ):
            self.assertIn(requirement, boundary)

        self.assertLessEqual(len(boundary.split()), 450)

        self.assertIn(
            "Interleave plugin and card execution, not provenance. Public plugin "
            "artifacts describe the reusable failure class, not the originating card "
            "or repository.",
            convergence,
        )
        for public_doc in (readme, usage):
            self.assertIn(
                "default trust domain",
                public_doc,
            )
            self.assertIn(
                "adt publication-gate --destination-repo", public_doc
            )
            self.assertIn(
                "no autonomous cross-owner bypass", public_doc
            )
            self.assertIn(
                "patterns", public_doc
            )

    def test_quickstart_documents_compact_input_and_autonomous_protocol(self) -> None:
        usage = " ".join(read(ROOT / "docs/mvp-usage.md").split())

        for field in (
            "`Outcome`",
            "`Constraints`",
            "`Done`",
            "`Artifact target`",
            "`Publication authority`",
        ):
            self.assertIn(field, usage)
        self.assertIn(
            "ORIENT -> discuss material decisions -> conversational confirmation -> "
            "autonomous BUILD / VERIFY / bounded REPAIR -> CLOSEOUT + KB",
            usage,
        )
        self.assertIn(
            "The owner does not need to line-review `task.md` as an approval form.",
            usage,
        )
        self.assertIn(
            "Ask again only when new evidence reveals a genuine fork in product, "
            "architecture, scope, release authority, or another hard-to-reverse choice.",
            usage,
        )

    def test_refined_contract_rebinds_review_and_repository_base(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )

        self.assertIn(
            "Changing any accepted outcome, domain, constraint, non-goal, repository "
            "policy, base, or verification obligation changes the contract digest "
            "and therefore the `ReviewKey`.",
            reference,
        )
        self.assertIn(
            "Before creating a branch, worktree, or pull request, resolve `BASE_REF` "
            "and immutable `BASE_SHA` from an explicit authoritative owner decision, "
            "otherwise repository policy, and only then the remote default branch "
            "as fallback when neither selects a base.",
            reference,
        )
        self.assertIn(
            "Never infer the merge target from the current checkout.", reference
        )
        self.assertIn(
            "If a candidate branch is incompatible with the resolved base, "
            "invalidate it; do not repair the mismatch by retargeting the pull "
            "request.",
            reference,
        )
        self.assertIn(
            "The latest effective contract drives both development and review.",
            reference,
        )

    def test_convergence_control_bounds_cold_launches_and_repairs(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )

        for purpose in (
            "`adversarial-integration`",
            "`known-finding-validation`",
            "`diagnostic-cold`",
            "`final-cold`",
            "`complementary-final-cold`",
        ):
            self.assertIn(purpose, reference)
        self.assertIn(
            "A final-acceptance cold path is eligible ex ante only when its "
            "artifact is immutable and clean, contract and accepted domain are "
            "fixed, focused checks are current for its `ArtifactKey`, "
            "adversarial integration is done, known blockers, evidence gaps, "
            "and owner decisions are closed, and no edit lane is active or planned.",
            reference,
        )
        self.assertIn(
            "An explicit `diagnostic-cold` path may reduce uncertainty but never "
            "counts as final acceptance.",
            reference,
        )
        self.assertIn(
            "Do not launch cold review on a candidate with a known-open blocker "
            "or planned edit.",
            reference,
        )
        self.assertIn(
            "The first material `HOLD` generation permits one consolidated repair "
            "and focused validation by the finding-owning lineage.",
            reference,
        )
        self.assertIn(
            "A second distinct repaired `ReviewKey` with a material `HOLD` "
            "requires `REASSESS` before more edits",
            reference,
        )
        self.assertIn(
            "A third material `HOLD` requires a scope split, architecture change, "
            "explicit owner decision, or documented rationale that continuing is "
            "cheaper and safer.",
            reference,
        )
        self.assertIn(
            "Infrastructure failure, not launched, interrupted, no usable result, "
            "independence compromised, and capability-only gaps stay fail-closed "
            "but do not consume a material repair cycle.",
            reference,
        )

    def test_convergence_control_reuses_only_exact_observed_evidence(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )
        verification = " ".join(
            read(PLUGIN / "references/verification-environments.md").split()
        )
        cold = " ".join(
            read(PLUGIN / "references/cold-independent-review.md").split()
        )

        self.assertIn(
            "An exact receipt matches `ArtifactKey`, canonical command, working "
            "directory and selection, toolchain, dependency and build digests, "
            "fixtures, migrations, schema and database reset, plus relevant "
            "environment, database and container identity.",
            reference,
        )
        self.assertIn("Never rerun a successful exact identity.", reference)
        self.assertIn(
            "After a candidate change, run the smallest affected check and one "
            "proportionate final full gate.",
            reference,
        )
        self.assertIn(
            "Do not reuse evidence across SHAs automatically until dependency-aware "
            "invalidation exists.",
            reference,
        )
        self.assertIn("Unknown or unavailable is not zero.", reference)
        self.assertIn(
            "Evidence reuse follows `references/convergence-control.md`", verification
        )
        self.assertIn(
            "Declare the path purpose and `ReviewKey` under "
            "`references/convergence-control.md` before launch.",
            cold,
        )

    def test_convergence_control_separates_plugin_work_and_observed_metrics(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/convergence-control.md").split()
        )

        self.assertIn(
            "Checkpoint the card, batch compatible plugin surgery, install one "
            "payload, then resume the card.",
            reference,
        )
        self.assertIn(
            "Do not cachebust for documentation or test-only adjustments that "
            "cannot affect installed behavior.",
            reference,
        )
        self.assertIn(
            "Identity, start, end, terminal state, tokens, and cost are metrics "
            "only when a launcher or backend actually observes them; never ask a "
            "model to attest them.",
            reference,
        )
        self.assertIn(
            "Prefer premature-cold rate over penalizing an eligible final cold "
            "path that finds a material defect.",
            reference,
        )

    def test_cold_review_preflight_forbids_shared_coordination_registries(self) -> None:
        reference = read(PLUGIN / "references/cold-independent-review.md")
        preflight = reference.split("## Isolate the path", 1)[0]
        normalized_preflight = " ".join(preflight.split())

        self.assertIn(
            "Before and during a counted cold path, do not inspect agent, task, "
            "or thread registries, teammate status feeds, messages, transcripts, "
            "summaries, or another path's progress.",
            normalized_preflight,
        )
        self.assertIn("independence-compromised", preflight)

    def test_counted_cold_review_requires_a_quiescent_launcher_lane(self) -> None:
        reference = read(PLUGIN / "references/cold-independent-review.md")

        self.assertEqual(QUIESCENT_COLD_BOUNDARIES, policy_boundary_rows(reference))

    def test_counted_reviewer_uses_standalone_lifecycle_without_portable_gate(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/cold-independent-review.md").split()
        )
        _, review_skill = frontmatter(SKILLS / "review" / "SKILL.md")
        review_skill = " ".join(review_skill.split())
        lifecycle = " ".join(read(LIFECYCLE).split())
        semantic = " ".join(
            read(PLUGIN / "references/semantic-boundaries.md").split()
        )

        self.assertIn(
            "A counted reviewer uses the normal standalone `kind=review` task "
            "lifecycle.",
            reference,
        )
        self.assertIn(
            "Never run `adt review-gate` inside an individual review path",
            reference,
        )
        self.assertIn(
            "Do not run `adt review-gate` inside a counted path.",
            review_skill,
        )
        self.assertIn(
            "A counted reviewer owns exactly one path and returns one sealed "
            "findings-first report.",
            review_skill,
        )
        self.assertIn(
            "Do not create `bundle.json` or ask for its schema.",
            review_skill,
        )
        self.assertIn(
            "In a counted cold path, record a missing normative input as a "
            "terminal gap or `HOLD`; never ask the launcher, root, owner, or "
            "another agent for it.",
            review_skill,
        )
        self.assertIn(
            "Outside a counted cold path, follow the ordinary owner-decision "
            "route.",
            review_skill,
        )
        self.assertIn(
            "`review-gate` is a launcher/composer command used only after at "
            "least two paths are sealed.",
            lifecycle,
        )
        self.assertIn(
            "For a counted cold path, the cold-review contact boundary "
            "overrides this owner-decision route.",
            semantic,
        )
        self.assertIn(
            "Record unresolved domain membership as a terminal gap or `HOLD` "
            "without contacting the owner or launcher.",
            semantic,
        )

    def test_counted_reviewer_separates_sealed_report_from_launcher_output(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/cold-independent-review.md").split()
        )

        self.assertIn(
            "Before launch, require it and every launcher-owned final-message or "
            "transcript destination to be absolute.",
            reference,
        )
        self.assertIn(
            "Resolve each destination to its canonical target.",
            reference,
        )
        self.assertIn(
            "If a destination such as Codex `-o` names the sealed artifact target, "
            "or any target identity cannot be established, defer the launch.",
            reference,
        )
        self.assertIn(
            "Never route launcher output to the sealed artifact destination.",
            reference,
        )

    def test_outbound_contact_self_aborts_without_waiting_for_a_reply(self) -> None:
        reference = " ".join(
            read(PLUGIN / "references/cold-independent-review.md").split()
        )

        self.assertIn(
            "If outbound contact is sent or attempted, do not wait for, read, "
            "or use a reply.",
            reference,
        )
        self.assertIn(
            "complete it with summary `independence-compromised: "
            "outbound-cross-agent-contact`",
            reference,
        )
        self.assertIn(
            "do not create state only to record the abort",
            reference,
        )
        self.assertIn("The launcher must not answer.", reference)

    def test_specialist_references_retain_fail_closed_boundaries(self) -> None:
        references = PLUGIN / "references"
        for name, required in REQUIRED_SPECIALIST_BOUNDARIES.items():
            with self.subTest(reference=name):
                self.assertTrue(
                    required.issubset(policy_boundary_rows(read(references / name)))
                )

    def test_lifecycle_reference_owns_exact_canonical_task_state_forms(self) -> None:
        command_owners = {
            path.resolve()
            for path in PLUGIN.rglob("*.md")
            if fenced_adt_commands(read(path))
        }
        self.assertEqual({LIFECYCLE.resolve()}, command_owners)
        self.assertEqual(
            EXPECTED_TASK_STATE_COMMANDS,
            fenced_adt_commands(read(LIFECYCLE)),
        )

    def test_homepage_and_all_repository_targets_exist(self) -> None:
        homepages = {
            json.loads(read(PLUGIN / manifest))["homepage"]
            for manifest in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json")
        }
        self.assertEqual(1, len(homepages))
        homepage = repository_link_target(ROOT, next(iter(homepages)))
        self.assertIsNotNone(homepage)
        assert homepage is not None
        self.assertTrue(homepage.is_file())

        resolved = {
            target
            for link in markdown_links(read(homepage))
            if (target := repository_link_target(homepage.parent, link)) is not None
        }
        for target in resolved:
            self.assertTrue(target.is_relative_to(ROOT.resolve()), target)
            self.assertTrue(target.is_file(), target)
        self.assertTrue(
            {
                (ROOT / "docs/mvp-operations.md").resolve(),
                (ROOT / "conformance/portable-cold-review.md").resolve(),
                (ROOT / "conformance/portable-cold-review-contract-v0.md").resolve(),
            }.issubset(resolved)
        )

    def test_model_selection_is_isolated_to_claude_runtime_reference(self) -> None:
        allowed = (PLUGIN / "references/claude-runtime.md").resolve()
        self.assertEqual({allowed}, model_selector_sources())

    def test_installed_source_discovery_covers_every_utf8_text_type(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            shell = root / "policy.sh"
            toml = root / "config.toml"
            binary = root / "asset.bin"
            invalid_utf8 = root / "invalid.bin"
            shell.write_text('MODEL="nebula"', encoding="utf-8")
            toml.write_text('model = "nebula"', encoding="utf-8")
            binary.write_bytes(b"\x00MODEL=nebula\x00")
            invalid_utf8.write_bytes(b"\xff\x00\xfe")

            self.assertEqual({shell, toml}, set(installed_source_files(root)))
            self.assertEqual(
                {shell.resolve(), toml.resolve()}, model_selector_sources(root)
            )

    def test_model_selector_sinks_are_family_agnostic_and_fail_closed(self) -> None:
        for path, policy in (
            (Path("policy.md"), "claude --model nebula"),
            (Path("policy.md"), "Runtime model policy: prefer nebula."),
            (Path("policy.md"), "Choose a model."),
            (Path("policy.md"), "Prefer the configured model."),
            (Path("policy.md"), "Route models by task."),
            (Path("policy.md"), "Select model."),
            (Path("runtime.py"), 'MODEL = "nebula"'),
            (Path("runtime.py"), 'MODEL_ID = "nebula"'),
            (Path("runtime.py"), 'DEFAULT_MODEL = "nebula"'),
            (Path("runtime.py"), 'runner(model="nebula")'),
            (Path("runtime.py"), 'runner(model_id="nebula")'),
            (Path("runtime.py"), "runner(model=resolve_model())"),
            (Path("runtime.py"), 'model: Literal["nebula"] = "nebula"'),
            (Path("runtime.py"), 'identity = dict(model="nebula")'),
            (Path("runtime.py"), 'def launch(model="nebula"): pass'),
            (Path("runtime.py"), 'def launch(*, model="nebula"): pass'),
            (Path("runtime.py"), 'launch = lambda model="nebula": None'),
            (Path("runtime.py"), 'setattr(config, "model", "nebula")'),
            (Path("runtime.py"), 'config.setdefault("model", "nebula")'),
            (
                Path("runtime.py"),
                'parser.add_argument("-m", dest="model", default="nebula")',
            ),
            (Path("runtime.py"), 'parser.add_argument("-m", dest="model")'),
            (Path("runtime.py"), "model, runtime = resolve_identity()"),
            (Path("runtime.py"), 'model += "-fallback"'),
            (Path("agent.yaml"), "model: nebula"),
            (Path("agent.yaml"), "model_id: nebula"),
            (Path("agent.yaml"), "model:\n  id: nebula"),
            (Path("config.json"), '{"model":"nebula"}'),
            (Path("config.json"), '{"model_id":"nebula"}'),
            (Path("config.json"), '{"model":{"id":"nebula"}}'),
            (Path("receipt.json"), '{"identity":{"model":"nebula"}}'),
            (Path("runtime.py"), 'config["model"]="nebula"'),
            (Path("bin/nested/launcher"), "args=(--model nebula)"),
        ):
            with self.subTest(policy=policy):
                self.assertTrue(has_model_selector(path, policy))

    def test_existing_identity_schema_reads_are_not_model_selectors(self) -> None:
        for path, evidence in (
            (Path("review.md"), "two-model review"),
            (Path("review.md"), "model evidence"),
            (Path("review.md"), "model diversity"),
            (Path("receipt.py"), 'receipt["identity"]["model"]'),
            (Path("notes.md"), "claude-code-2 migration notes"),
            (Path("schema.json"), '{"model":"string"}'),
            (Path("receipt.py"), 'identity_model = "unknown"'),
            (Path("receipt.py"), "def record(model: str) -> None: pass"),
            (
                Path("receipt.py"),
                'fields = {"provider", "runtime", "model"}',
            ),
            (
                Path("receipt.py"),
                'receipt["identity"]["model"]',
            ),
            (
                Path("receipt.py"),
                'for field in ("provider", "runtime", "model"): pass',
            ),
            (Path("runtime.py"), 'def launch(model="unknown"): pass'),
            (Path("runtime.py"), "def launch(*, model_id=None): pass"),
            (Path("runtime.py"), 'setattr(config, "model", "unknown")'),
            (Path("runtime.py"), 'config.setdefault("model", "unknown")'),
            (Path("runtime.py"), 'parser.add_argument("--model-cache")'),
        ):
            with self.subTest(evidence=evidence):
                self.assertFalse(has_model_selector(path, evidence))


if __name__ == "__main__":
    unittest.main()
