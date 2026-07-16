from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_SOURCE = ROOT / "plugins/ai-dev-team-v2"


class InstallMvpTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.install_root = self.root / "installed-plugin"
        self.wrong_install_root = self.root / "wrong-installed-plugin"
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
    if [[ "$FAKE_CODEX_MODE" == "add-failure" ]]; then
      exit 7
    fi
    rm -rf "$FAKE_CODEX_INSTALL_ROOT"
    rm -rf "$FAKE_CODEX_WRONG_INSTALL_ROOT"
    if [[ "$FAKE_CODEX_MODE" != "missing" ]]; then
      cp -R "$FAKE_CODEX_SOURCE" "$FAKE_CODEX_INSTALL_ROOT"
      chmod -R u+w "$FAKE_CODEX_INSTALL_ROOT"
    fi
    if [[ "$FAKE_CODEX_MODE" == "stale" ]]; then
      printf '\\nstale cache\\n' >> "$FAKE_CODEX_INSTALL_ROOT/skills/develop/SKILL.md"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-manifest" ]]; then
      printf '\\n' >> "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-manifest-missing" ]]; then
      rm "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-manifest-symlink" ]]; then
      rm "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/plugin.json"
      ln -s plugin.other.json "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-directory-missing" ]]; then
      rm -rf "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin"
    fi
    if [[ "$FAKE_CODEX_MODE" == "foreign-extra" ]]; then
      mkdir -p "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/extra"
      printf 'unexpected payload\\n' > "$FAKE_CODEX_INSTALL_ROOT/.claude-plugin/extra/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "native-manifest" ]]; then
      printf '\\n' >> "$FAKE_CODEX_INSTALL_ROOT/.codex-plugin/plugin.json"
    fi
    if [[ "$FAKE_CODEX_MODE" == "non-executable" ]]; then
      chmod a-x "$FAKE_CODEX_INSTALL_ROOT/bin/adt"
    fi
    if [[ "$FAKE_CODEX_MODE" == "owner-only-executable" ]]; then
      chmod 700 "$FAKE_CODEX_INSTALL_ROOT/bin/adt"
    fi
    if [[ "$FAKE_CODEX_MODE" == "runtime-cache" ]]; then
      mkdir -p "$FAKE_CODEX_INSTALL_ROOT/scripts/__pycache__"
      printf 'ignored bytecode\\n' > "$FAKE_CODEX_INSTALL_ROOT/scripts/__pycache__/extra.pyc"
    fi
    if [[ "$FAKE_CODEX_MODE" == "orphan-pyc" ]]; then
      printf 'unexpected bytecode\\n' > "$FAKE_CODEX_INSTALL_ROOT/orphan.pyc"
    fi
    if [[ "$FAKE_CODEX_MODE" == "pyc-directory" ]]; then
      mkdir "$FAKE_CODEX_INSTALL_ROOT/unexpected.pyc"
      printf 'unexpected payload\\n' > "$FAKE_CODEX_INSTALL_ROOT/unexpected.pyc/payload.txt"
    fi
    if [[ "$FAKE_CODEX_MODE" == "pycache-symlink" ]]; then
      ln -s develop "$FAKE_CODEX_INSTALL_ROOT/skills/__pycache__"
    fi
    if [[ "$FAKE_CODEX_MODE" == "pycache-payload" ]]; then
      mkdir -p "$FAKE_CODEX_INSTALL_ROOT/scripts/__pycache__"
      printf 'unexpected payload\\n' > "$FAKE_CODEX_INSTALL_ROOT/scripts/__pycache__/unexpected.txt"
    fi
    if [[ "$FAKE_CODEX_MODE" == "type-drift" ]]; then
      rm "$FAKE_CODEX_INSTALL_ROOT/skills/review/SKILL.md"
      mkdir "$FAKE_CODEX_INSTALL_ROOT/skills/review/SKILL.md"
    fi
    if [[ "$FAKE_CODEX_MODE" == "special-entry" ]]; then
      mkfifo "$FAKE_CODEX_INSTALL_ROOT/unexpected.fifo"
    fi
    if [[ "$FAKE_CODEX_MODE" == "unreadable" ]]; then
      chmod 000 "$FAKE_CODEX_INSTALL_ROOT/skills/develop/SKILL.md"
    fi
    if [[ "$FAKE_CODEX_MODE" == "symlink-target" ]]; then
      rm "$FAKE_CODEX_INSTALL_ROOT/scripts/payload-link"
      ln -s review_gate.py "$FAKE_CODEX_INSTALL_ROOT/scripts/payload-link"
    fi
    if [[ "$FAKE_CODEX_MODE" == "symlink-type" ]]; then
      rm "$FAKE_CODEX_INSTALL_ROOT/scripts/payload-link"
      cp "$FAKE_CODEX_INSTALL_ROOT/scripts/adt.py" "$FAKE_CODEX_INSTALL_ROOT/scripts/payload-link"
    fi
    if [[ "$FAKE_CODEX_MODE" == "wrong-installed-path" ]]; then
      mkdir -p "$FAKE_CODEX_WRONG_INSTALL_ROOT"
      printf 'not the plugin payload\\n' > "$FAKE_CODEX_WRONG_INSTALL_ROOT/unexpected.txt"
    fi
    python3 - <<'PY'
import json
import os

mode = os.environ["FAKE_CODEX_MODE"]
version = os.environ["FAKE_CODEX_VERSION"]
if mode == "wrong-version":
    version = version.split("+", 1)[0] + "+codex.stale"
plugin_id = "ai-dev-team@ai-dev-team-v2-local"
if mode == "wrong-plugin-id":
    plugin_id = "other-plugin@ai-dev-team-v2-local"
installed_path = os.environ["FAKE_CODEX_INSTALL_ROOT"]
if mode == "empty-installed-path":
    installed_path = ""
elif mode == "wrong-installed-path":
    installed_path = os.environ["FAKE_CODEX_WRONG_INSTALL_ROOT"]
result = {
    "pluginId": plugin_id,
    "name": "ai-dev-team",
    "marketplaceName": "ai-dev-team-v2-local",
    "version": version,
    "authPolicy": "ON_INSTALL",
}
if mode != "missing-installed-path":
    result["installedPath"] = installed_path
print(json.dumps(result))
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
        self.make_tree_owner_writable(self.root)
        self.temporary.cleanup()

    @staticmethod
    def make_tree_owner_writable(root: Path) -> None:
        if not root.exists() or root.is_symlink():
            return
        for directory, directory_names, file_names in os.walk(root):
            paths = [Path(directory)]
            paths.extend(Path(directory) / name for name in directory_names)
            paths.extend(Path(directory) / name for name in file_names)
            for path in paths:
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)

    @staticmethod
    def make_tree_read_only(root: Path) -> None:
        write_bits = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        for directory, directory_names, file_names in os.walk(root):
            paths = [Path(directory)]
            paths.extend(Path(directory) / name for name in directory_names)
            paths.extend(Path(directory) / name for name in file_names)
            for path in paths:
                if not path.is_symlink():
                    path.chmod(path.stat().st_mode & ~write_bits)

    def copy_writable_plugin(self) -> None:
        if self.install_root.exists():
            self.make_tree_owner_writable(self.install_root)
            shutil.rmtree(self.install_root)
        shutil.copytree(PLUGIN_SOURCE, self.install_root)
        self.make_tree_owner_writable(self.install_root)

    def run_installer(
        self,
        *,
        mode: str,
        marketplace_root: Path | None = None,
        marketplace_type: str = "local",
        repo_root: Path = ROOT,
        require_upgrade: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        marketplace_root = marketplace_root or repo_root
        plugin_source = repo_root / "plugins/ai-dev-team-v2"
        plugin_version = json.loads(
            (plugin_source / ".codex-plugin/plugin.json").read_text()
        )["version"]
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(self.home),
                "PATH": f"{self.bin}:{environment['PATH']}",
                "FAKE_CODEX_INSTALL_ROOT": str(self.install_root),
                "FAKE_CODEX_WRONG_INSTALL_ROOT": str(self.wrong_install_root),
                "FAKE_CODEX_MARKETPLACE_ROOT": str(marketplace_root),
                "FAKE_CODEX_MARKETPLACE_TYPE": marketplace_type,
                "FAKE_CODEX_MODE": mode,
                "FAKE_CODEX_REQUIRE_UPGRADE": "1" if require_upgrade else "0",
                "FAKE_CODEX_SOURCE": str(plugin_source),
                "FAKE_CODEX_STATE": str(self.state),
                "FAKE_CODEX_VERSION": plugin_version,
            }
        )
        return subprocess.run(
            [str(repo_root / "scripts/install-mvp"), "--codex"],
            cwd=repo_root,
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
        for mode in (
            "foreign-manifest",
            "foreign-manifest-missing",
            "foreign-directory-missing",
        ):
            with self.subTest(mode=mode):
                result = self.run_installer(mode=mode)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.install_root.is_dir())

    def test_executable_mode_is_normalized_to_owner_semantics(self) -> None:
        result = self.run_installer(mode="owner-only-executable")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installer_does_not_require_source_write_access(self) -> None:
        read_only_repo = self.root / "read-only-repo"
        (read_only_repo / "scripts").mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/install-mvp", read_only_repo / "scripts")
        shutil.copytree(
            PLUGIN_SOURCE,
            read_only_repo / "plugins/ai-dev-team-v2",
        )
        self.make_tree_read_only(read_only_repo)

        result = self.run_installer(
            mode="matching",
            repo_root=read_only_repo,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_claude_ignores_codex_manifest_but_verifies_native_content(self) -> None:
        self.copy_writable_plugin()
        with (self.install_root / ".codex-plugin/plugin.json").open("a") as manifest:
            manifest.write("\n")

        foreign_manifest_result = self.run_claude_installer()

        self.assertEqual(
            foreign_manifest_result.returncode,
            0,
            foreign_manifest_result.stderr,
        )

        self.copy_writable_plugin()
        shutil.rmtree(self.install_root / ".codex-plugin")
        foreign_directory_result = self.run_claude_installer()

        self.assertEqual(
            foreign_directory_result.returncode,
            0,
            foreign_directory_result.stderr,
        )

        for relative_path in (
            ".claude-plugin/plugin.json",
            "bin/adt",
            "skills/develop/SKILL.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.copy_writable_plugin()
                native_content = self.install_root / relative_path
                if relative_path == "bin/adt":
                    native_content.chmod(native_content.stat().st_mode & ~0o111)
                else:
                    with native_content.open("a") as stream:
                        stream.write("\nstale native content\n")

                stale_result = self.run_claude_installer()

                self.assertNotEqual(stale_result.returncode, 0)
                self.assertIn(
                    "Claude's cached plugin does not match the local source",
                    stale_result.stderr,
                )

    def test_hosts_ignore_only_the_foreign_manifest(self) -> None:
        for mode in (
            "foreign-extra",
            "foreign-manifest-symlink",
        ):
            with self.subTest(host="codex", mode=mode):
                codex_result = self.run_installer(mode=mode)

                self.assertNotEqual(codex_result.returncode, 0)
                self.assertIn(
                    "Codex's cached plugin does not match the local source",
                    codex_result.stderr,
                )

        for mutation in ("extra", "symlink"):
            with self.subTest(host="claude", mutation=mutation):
                self.copy_writable_plugin()
                foreign_manifest = (
                    self.install_root / ".codex-plugin/plugin.json"
                )
                if mutation == "extra":
                    foreign_extra = (
                        self.install_root / ".codex-plugin/extra/plugin.json"
                    )
                    foreign_extra.parent.mkdir()
                    foreign_extra.write_text("unexpected payload\n")
                elif mutation == "symlink":
                    foreign_manifest.unlink()
                    foreign_manifest.symlink_to("plugin.other.json")
                claude_result = self.run_claude_installer()

                self.assertNotEqual(claude_result.returncode, 0)
                self.assertIn(
                    "Claude's cached plugin does not match the local source",
                    claude_result.stderr,
                )

    def test_payload_inventory_rejects_structural_drift(self) -> None:
        result = self.run_installer(mode="type-drift")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Codex's cached plugin does not match the local source",
            result.stderr,
        )

    def test_runtime_cache_exclusions_are_type_scoped(self) -> None:
        runtime_cache_result = self.run_installer(mode="runtime-cache")

        self.assertEqual(
            runtime_cache_result.returncode,
            0,
            runtime_cache_result.stderr,
        )

        for mode in (
            "orphan-pyc",
            "pyc-directory",
            "pycache-symlink",
            "pycache-payload",
        ):
            with self.subTest(mode=mode):
                result = self.run_installer(mode=mode)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "Codex's cached plugin does not match the local source",
                    result.stderr,
                )

    def test_symlink_target_and_type_are_verified(self) -> None:
        symlink_repo = self.root / "symlink-repo"
        (symlink_repo / "scripts").mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/install-mvp", symlink_repo / "scripts")
        shutil.copytree(
            PLUGIN_SOURCE,
            symlink_repo / "plugins/ai-dev-team-v2",
            symlinks=True,
        )
        (
            symlink_repo
            / "plugins/ai-dev-team-v2/scripts/payload-link"
        ).symlink_to("adt.py")

        matching_result = self.run_installer(
            mode="matching",
            repo_root=symlink_repo,
        )
        self.assertEqual(matching_result.returncode, 0, matching_result.stderr)

        for mode in ("symlink-target", "symlink-type"):
            with self.subTest(mode=mode):
                result = self.run_installer(mode=mode, repo_root=symlink_repo)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "Codex's cached plugin does not match the local source",
                    result.stderr,
                )

    def test_unsupported_payload_entry_fails_with_specific_diagnostic(self) -> None:
        result = self.run_installer(mode="special-entry")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "plugin payload verification failed: unsupported plugin entry: "
            "unexpected.fifo",
            result.stderr,
        )
        self.assertIn(
            "Codex's cached plugin could not be verified",
            result.stderr,
        )

    @unittest.skipIf(os.geteuid() == 0, "root can read chmod-000 fixtures")
    def test_unreadable_payload_fails_closed(self) -> None:
        result = self.run_installer(mode="unreadable")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugin payload verification failed:", result.stderr)
        self.assertIn(
            "Codex's cached plugin could not be verified",
            result.stderr,
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
            "non-executable": "Codex's cached plugin does not match the local source",
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

    def test_codex_rejects_untrusted_install_result_fields(self) -> None:
        expectations = {
            "add-failure": (7, None),
            "empty-installed-path": (
                None,
                "Codex reported an invalid install path",
            ),
            "missing-installed-path": (
                None,
                "Codex reported an invalid install path",
            ),
            "wrong-installed-path": (
                None,
                "Codex's cached plugin does not match the local source",
            ),
            "wrong-plugin-id": (None, "Codex installed plugin"),
        }

        for mode, (returncode, message) in expectations.items():
            with self.subTest(mode=mode):
                result = self.run_installer(mode=mode)

                if returncode is None:
                    self.assertNotEqual(result.returncode, 0)
                else:
                    self.assertEqual(result.returncode, returncode)
                if message is not None:
                    self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
