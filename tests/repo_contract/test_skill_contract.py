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
        "incident-observability.md",
        "semantic-boundaries.md",
        "task-lifecycle.md",
        "verification-environments.md",
    },
    "review": {
        "claude-runtime.md",
        "cold-independent-review.md",
        "incident-observability.md",
        "semantic-boundaries.md",
        "task-lifecycle.md",
        "verification-environments.md",
    },
}
REPOSITORY_BLOB_ROOT = (
    "https://github.com/roman-karpovich/ai-dev-team-v2/blob/master/"
)
EXPECTED_TASK_STATE_COMMANDS = {
    tuple(shlex.split(command))
    for command in (
        'adt --workspace "$WORKSPACE" status',
        'adt --workspace "$WORKSPACE" list',
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
            "host:claude",
            "references/claude-runtime.md",
            "after:cold-if-triggered;before:repository-exposure|adt-state|artifact-inspection",
        ),
        (
            "always",
            "references/task-lifecycle.md",
            "after:prior-preflights;before:adt-state|mutation",
        ),
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
