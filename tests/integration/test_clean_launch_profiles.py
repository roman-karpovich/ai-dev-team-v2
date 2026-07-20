from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPERATIONS = ROOT / "docs/mvp-operations.md"


def cli_output(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), capture_output=True, text=True, timeout=60, check=False
    )


def documented_version(pattern: str) -> str:
    match = re.search(pattern, OPERATIONS.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"documented version not found: {pattern}")
    return match.group(1)


def installed_version(*command: str) -> str:
    match = re.search(r"\d+\.\d+\.\d+", cli_output(*command).stdout)
    if match is None:
        raise AssertionError(f"no version in output of: {' '.join(command)}")
    return match.group(0)


@unittest.skipUnless(
    os.environ.get("ADT_INTEGRATION_CLI") == "1",
    "opt-in: set ADT_INTEGRATION_CLI=1 to validate documented launch profiles "
    "against the installed CLIs",
)
class CleanLaunchProfilesTest(unittest.TestCase):
    """Validate the dated launch profiles in docs/mvp-operations.md.

    These checks bind the documented dated profiles to the installed CLIs:
    a version mismatch means the profile is unverified for this machine and
    must be re-validated and re-dated, so the test fails rather than passing
    on unexamined newer runtimes. Only CLI help and version output is
    exercised; no model session is ever started.
    """

    def require(self, executable: str) -> None:
        if shutil.which(executable) is None:
            self.skipTest(f"{executable} is not installed")

    def test_claude_profile_matches_installed_cli(self) -> None:
        self.require("claude")
        documented = documented_version(r"Claude Code (\d+\.\d+\.\d+)")
        installed = installed_version("claude", "--version")
        self.assertEqual(
            documented,
            installed,
            "installed Claude Code differs from the dated profile; re-verify "
            "the documented launch form and update its version in "
            "docs/mvp-operations.md",
        )
        help_text = cli_output("claude", "--help").stdout
        for flag in ("--bare", "--print", "--no-session-persistence", "--plugin-dir"):
            self.assertIn(flag, help_text)
        persistence = help_text.split("--no-session-persistence", 1)[1][:400]
        self.assertIn("only works with --print", persistence)

    def test_codex_profile_matches_installed_cli(self) -> None:
        self.require("codex")
        documented = documented_version(r"Codex (\d+\.\d+\.\d+)")
        installed = installed_version("codex", "--version")
        self.assertEqual(
            documented,
            installed,
            "installed Codex differs from the dated profile; re-verify the "
            "documented launch form and update its version in "
            "docs/mvp-operations.md",
        )
        exec_help = cli_output("codex", "exec", "--help").stdout
        for flag in ("--ephemeral", "--strict-config", "--sandbox"):
            self.assertIn(flag, exec_help)
        # Strict-config rejection of unknown `-c` keys happens at session
        # launch; `--version` and `doctor` do not reach config validation, so
        # that behavior cannot be probed here without starting a session.
        # Confirm it manually on the installed version before counting a path.


if __name__ == "__main__":
    unittest.main()
