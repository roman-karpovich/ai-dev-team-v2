from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RepositoryContractTest(unittest.TestCase):
    def test_required_bootstrap_files_exist(self) -> None:
        for relative_path in (
            "README.md",
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


if __name__ == "__main__":
    unittest.main()
