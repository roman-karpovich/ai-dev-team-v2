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
EXPECTED_ADT_COMMANDS = {
    tuple(shlex.split(command))
    for command in (
        'adt --workspace "$WORKSPACE" status',
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

    def test_review_preflight_resource_order_is_fail_closed(self) -> None:
        _, review = frontmatter(SKILLS / "review/SKILL.md")
        cold = review.index("`references/cold-independent-review.md`")
        claude = review.index("`references/claude-runtime.md`")
        lifecycle = review.index("`references/task-lifecycle.md`")
        self.assertLess(cold, claude)
        self.assertLess(claude, lifecycle)

    def test_lifecycle_reference_owns_exact_executable_command_surface(self) -> None:
        command_owners = {
            path.resolve()
            for path in PLUGIN.rglob("*.md")
            if fenced_adt_commands(read(path))
        }
        self.assertEqual({LIFECYCLE.resolve()}, command_owners)
        self.assertEqual(EXPECTED_ADT_COMMANDS, fenced_adt_commands(read(LIFECYCLE)))

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
        self.assertLessEqual(len(read(homepage).splitlines()), 140)

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
        model_name = re.compile(
            r"\b(?:opus|fable)\s+\d|\bclaude-(?:opus|fable)-[a-z0-9.-]+",
            re.IGNORECASE,
        )
        containing = {
            path.resolve()
            for path in PLUGIN.rglob("*.md")
            if model_name.search(read(path))
        }
        self.assertEqual({allowed}, containing)


if __name__ == "__main__":
    unittest.main()
