from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SOURCE = ROOT / "plugins/ai-dev-team-v2"
PLUGIN_VERSION = json.loads(
    (PLUGIN_SOURCE / ".codex-plugin/plugin.json").read_text()
)["version"]


class InstallMvpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.install_root = self.root / "installed-plugin"
        self.state = self.root / "state"
        self.home.mkdir()
        self.bin.mkdir()
        self.state.mkdir()

        fake_codex = self.bin / "codex"
        fake_codex.write_text(
            """#!/usr/bin/env bash
set -euo pipefail

case "$*" in
  "plugin marketplace list")
    printf 'MARKETPLACE ROOT\\n'
    printf 'ai-dev-team-v2-local  %s\\n' "$FAKE_CODEX_MARKETPLACE_ROOT"
    ;;
  "plugin marketplace list --json")
    python3 - <<'PY'
import json
import os

print(json.dumps({
    "marketplaces": [{
        "name": "ai-dev-team-v2-local",
        "root": os.environ["FAKE_CODEX_MARKETPLACE_ROOT"],
        "marketplaceSource": {
            "sourceType": os.environ["FAKE_CODEX_MARKETPLACE_TYPE"],
            "source": os.environ["FAKE_CODEX_MARKETPLACE_ROOT"],
        },
    }]
}))
PY
    ;;
  "plugin marketplace upgrade ai-dev-team-v2-local")
    touch "$FAKE_CODEX_STATE/upgraded"
    ;;
  "plugin list --json")
    python3 - <<'PY'
import json
import os

print(json.dumps({
    "installed": [{
        "pluginId": "ai-dev-team@ai-dev-team-v2-local",
        "version": os.environ["FAKE_CODEX_VERSION"],
    }]
}))
PY
    ;;
  "plugin add ai-dev-team@ai-dev-team-v2-local --json")
    if [[ "$FAKE_CODEX_REQUIRE_UPGRADE" == "1" && ! -f "$FAKE_CODEX_STATE/upgraded" ]]; then
      echo "marketplace was not refreshed" >&2
      exit 9
    fi
    rm -rf "$FAKE_CODEX_INSTALL_ROOT"
    if [[ "$FAKE_CODEX_MODE" != "missing" ]]; then
      cp -R "$FAKE_CODEX_SOURCE" "$FAKE_CODEX_INSTALL_ROOT"
    fi
    if [[ "$FAKE_CODEX_MODE" == "stale" ]]; then
      printf '\\nstale cache\\n' >> "$FAKE_CODEX_INSTALL_ROOT/skills/develop/SKILL.md"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-manifest" ]]; then
      printf '\\n' >> "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "native-manifest" ]]; then
      printf '\\n' >> "$FAKE_CODEX_INSTALL_ROOT/.codex-plugin/plugin.json"
    fi
    python3 - <<'PY'
import json
import os

version = os.environ["FAKE_CODEX_VERSION"]
if os.environ["FAKE_CODEX_MODE"] == "wrong-version":
    version = version.split("+", 1)[0] + "+codex.stale"
print(json.dumps({
    "pluginId": "ai-dev-team@ai-dev-team-v2-local",
    "name": "ai-dev-team",
    "marketplaceName": "ai-dev-team-v2-local",
    "version": version,
    "installedPath": os.environ["FAKE_CODEX_INSTALL_ROOT"],
    "authPolicy": "ON_INSTALL",
}))
PY
    ;;
  *)
    echo "unexpected fake Codex invocation: $*" >&2
    exit 8
    ;;
esac
"""
        )
        fake_codex.chmod(0o755)

        fake_claude = self.bin / "claude"
        fake_claude.write_text(
            """#!/usr/bin/env bash
set -euo pipefail

case "$*" in
  "plugin marketplace list --json")
    printf '[{"name":"ai-dev-team-v2-local"}]\\n'
    ;;
  "plugin list --json")
    python3 - <<'PY'
import json
import os

print(json.dumps([{
    "id": "ai-dev-team@ai-dev-team-v2-local",
    "version": "0.1.29",
    "installPath": os.environ["FAKE_CLAUDE_INSTALL_ROOT"],
}]))
PY
    ;;
  "plugin update ai-dev-team@ai-dev-team-v2-local")
    ;;
  *)
    echo "unexpected fake Claude invocation: $*" >&2
    exit 8
    ;;
esac
"""
        )
        fake_claude.chmod(0o755)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_installer(
        self,
        *,
        mode: str,
        marketplace_root: Path = ROOT,
        marketplace_type: str = "local",
        require_upgrade: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.bin}:{environment['PATH']}",
                "FAKE_CODEX_INSTALL_ROOT": str(self.install_root),
                "FAKE_CODEX_MARKETPLACE_ROOT": str(marketplace_root),
                "FAKE_CODEX_MARKETPLACE_TYPE": marketplace_type,
                "FAKE_CODEX_MODE": mode,
                "FAKE_CODEX_REQUIRE_UPGRADE": "1" if require_upgrade else "0",
                "FAKE_CODEX_SOURCE": str(PLUGIN_SOURCE),
                "FAKE_CODEX_STATE": str(self.state),
                "FAKE_CODEX_VERSION": PLUGIN_VERSION,
            }
        )
        return subprocess.run(
            [str(ROOT / "scripts/install-mvp"), "--codex"],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def run_claude_installer(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.bin}:{environment['PATH']}",
                "FAKE_CLAUDE_INSTALL_ROOT": str(self.install_root),
            }
        )
        return subprocess.run(
            [str(ROOT / "scripts/install-mvp"), "--claude"],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_codex_install_is_verified_after_plugin_add(self) -> None:
        result = self.run_installer(mode="foreign-manifest")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.install_root.is_dir())

    def test_claude_ignores_codex_manifest_but_verifies_native_content(self) -> None:
        shutil.copytree(PLUGIN_SOURCE, self.install_root)
        with (self.install_root / ".codex-plugin/plugin.json").open("a") as manifest:
            manifest.write("\n")

        foreign_manifest_result = self.run_claude_installer()

        self.assertEqual(
            foreign_manifest_result.returncode,
            0,
            foreign_manifest_result.stderr,
        )

        for relative_path in (
            ".claude-plugin/plugin.json",
            "skills/develop/SKILL.md",
        ):
            with self.subTest(relative_path=relative_path):
                shutil.rmtree(self.install_root)
                shutil.copytree(PLUGIN_SOURCE, self.install_root)
                with (self.install_root / relative_path).open("a") as native_content:
                    native_content.write("\nstale native content\n")

                stale_result = self.run_claude_installer()

                self.assertNotEqual(stale_result.returncode, 0)
                self.assertIn(
                    "Claude's cached plugin does not match the local source",
                    stale_result.stderr,
                )

    def test_git_marketplace_snapshot_is_refreshed_before_plugin_add(self) -> None:
        snapshot = self.root / "marketplace-snapshot"
        snapshot.mkdir()

        result = self.run_installer(
            mode="matching",
            marketplace_root=snapshot,
            marketplace_type="git",
            require_upgrade=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.state / "upgraded").is_file())

    def test_different_local_marketplace_is_not_reconfigured_implicitly(self) -> None:
        other_checkout = self.root / "other-checkout"
        other_checkout.mkdir()

        result = self.run_installer(
            mode="matching",
            marketplace_root=other_checkout,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not point to this checkout", result.stderr)
        self.assertFalse((self.state / "upgraded").exists())

    def test_codex_install_rejects_missing_or_stale_cache(self) -> None:
        expectations = {
            "missing": "Codex reported an invalid install path",
            "native-manifest": "Codex's cached plugin does not match the local source",
            "stale": "Codex's cached plugin does not match the local source",
            "wrong-version": "Codex installed version",
        }

        for mode, message in expectations.items():
            with self.subTest(mode=mode):
                if mode == "stale":
                    snapshot = self.root / "stale-marketplace-snapshot"
                    snapshot.mkdir(exist_ok=True)
                    result = self.run_installer(
                        mode=mode,
                        marketplace_root=snapshot,
                        marketplace_type="git",
                        require_upgrade=True,
                    )
                else:
                    result = self.run_installer(mode=mode)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
