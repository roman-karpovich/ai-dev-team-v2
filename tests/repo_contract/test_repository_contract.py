from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RepositoryContractTest(unittest.TestCase):
    def test_required_bootstrap_files_exist(self) -> None:
        for relative_path in (
            "README.md",
            "LICENSE",
            "AGENTS.md",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "docs/architecture.md",
            "docs/mission.md",
            "docs/readiness-gate.md",
            "docs/adr/0001-greenfield-rebuild.md",
            "docs/adr/0002-portable-assurance-native-execution.md",
            "docs/mvp-usage.md",
            "conformance/portable-cold-review.md",
            "plugins/ai-dev-team-v2/.codex-plugin/plugin.json",
            "plugins/ai-dev-team-v2/.claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
            "scripts/install-mvp",
            "spikes/schema/README.md",
            "scripts/check_public_source.py",
            "scripts/test-fast",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_production_source_tree_is_blocked_before_readiness_go(self) -> None:
        self.assertFalse((ROOT / "src").exists())

    def test_fast_entrypoint_does_not_recurse_into_other_tiers(self) -> None:
        entrypoint = (ROOT / "scripts/test-fast").read_text()
        self.assertNotIn("make test", entrypoint)
        self.assertNotIn("test-all", entrypoint)

    def test_troubleshooting_error_codes_exist_in_adt_cli(self) -> None:
        operations = (ROOT / "docs/mvp-operations.md").read_text()
        troubleshooting_codes = {
            token
            for heading in re.findall(r"(?m)^### (.+)$", operations)
            for token in re.findall(r"`([a-z][a-z0-9_]+)`", heading)
            if "_" in token
        }

        source = ROOT / "plugins/ai-dev-team-v2/scripts/adt.py"
        tree = ast.parse(source.read_text(), filename=str(source))
        cli_error_codes = {
            call.args[0].value
            for call in ast.walk(tree)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "CliError"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        }

        self.assertLessEqual(troubleshooting_codes, cli_error_codes)

    def test_host_plugin_versions_share_one_release_base(self) -> None:
        codex = json.loads(
            (ROOT / "plugins/ai-dev-team-v2/.codex-plugin/plugin.json").read_text()
        )
        claude = json.loads(
            (ROOT / "plugins/ai-dev-team-v2/.claude-plugin/plugin.json").read_text()
        )
        marketplace = json.loads(
            (ROOT / ".claude-plugin/marketplace.json").read_text()
        )

        release_version = claude["version"]
        codex_release, separator, codex_cachebuster = codex["version"].partition("+")
        self.assertEqual(release_version, codex_release)
        self.assertEqual("+", separator)
        self.assertRegex(codex_cachebuster, r"^codex\.\d{14}$")
        self.assertEqual(release_version, marketplace["plugins"][0]["version"])

    def test_host_plugin_identity_and_marketplace_sources_are_symmetric(self) -> None:
        codex = json.loads(
            (ROOT / "plugins/ai-dev-team-v2/.codex-plugin/plugin.json").read_text()
        )
        claude = json.loads(
            (ROOT / "plugins/ai-dev-team-v2/.claude-plugin/plugin.json").read_text()
        )
        claude_marketplace = json.loads(
            (ROOT / ".claude-plugin/marketplace.json").read_text()
        )
        codex_marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text()
        )

        plugin_name = claude["name"]
        self.assertEqual(plugin_name, codex["name"])
        self.assertEqual(plugin_name, claude_marketplace["plugins"][0]["name"])
        self.assertEqual(plugin_name, codex_marketplace["plugins"][0]["name"])
        self.assertEqual(claude_marketplace["name"], codex_marketplace["name"])
        self.assertEqual(
            claude_marketplace["plugins"][0]["source"],
            codex_marketplace["plugins"][0]["source"]["path"],
        )
        self.assertEqual(
            "local", codex_marketplace["plugins"][0]["source"]["source"]
        )


if __name__ == "__main__":
    unittest.main()
