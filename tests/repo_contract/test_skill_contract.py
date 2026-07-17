from __future__ import annotations

import json
import re
import shlex
import unittest
from pathlib import Path
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
MODEL_NAME = re.compile(
    r"\b(?:opus|fable)\s+\d|\bclaude-(?:opus|fable)-[a-z0-9.-]+",
    re.IGNORECASE,
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


def skill_route_rows(text: str) -> list[tuple[str, ...]]:
    lines = text.splitlines()
    header = "| Trigger | Resource | Boundary |"
    matches = [index for index, line in enumerate(lines) if line.strip() == header]
    if len(matches) != 1:
        raise AssertionError("expected exactly one skill route table")

    index = matches[0]
    if index + 1 >= len(lines) or markdown_row(lines[index + 1]) != (
        "---",
        "---",
        "---",
    ):
        raise AssertionError("malformed skill route table separator")

    rows: list[tuple[str, ...]] = []
    for line in lines[index + 2 :]:
        if not line.strip().startswith("|"):
            break
        row = markdown_row(line)
        if len(row) != 3:
            raise AssertionError(f"malformed skill route row: {line!r}")
        rows.append(row)
    return rows


def installed_source_files() -> list[Path]:
    return [
        path
        for path in PLUGIN.rglob("*")
        if path.is_file()
        and (
            path.suffix in {".md", ".yaml", ".json", ".py"}
            or path.parent == PLUGIN / "bin"
        )
    ]


def model_name_sources() -> set[Path]:
    return {
        path.resolve()
        for path in installed_source_files()
        if MODEL_NAME.search(read(path))
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

    def test_model_names_are_isolated_to_claude_runtime_reference(self) -> None:
        allowed = (PLUGIN / "references/claude-runtime.md").resolve()
        self.assertEqual({allowed}, model_name_sources())


if __name__ == "__main__":
    unittest.main()
