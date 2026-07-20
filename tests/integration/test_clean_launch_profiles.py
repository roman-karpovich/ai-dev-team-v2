from __future__ import annotations

import os
import shutil
import subprocess
import unittest


def cli_output(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), capture_output=True, text=True, timeout=60, check=False
    )


@unittest.skipUnless(
    os.environ.get("ADT_INTEGRATION_CLI") == "1",
    "opt-in: set ADT_INTEGRATION_CLI=1 to validate documented launch profiles "
    "against the installed CLIs",
)
class CleanLaunchProfilesTest(unittest.TestCase):
    """Validate the dated launch profiles in docs/mvp-operations.md.

    These checks exercise installed CLI help and configuration validation
    only; they never start a model session.
    """

    def require(self, executable: str) -> None:
        if shutil.which(executable) is None:
            self.skipTest(f"{executable} is not installed")

    def test_claude_profile_flags_exist_with_print_dependency(self) -> None:
        self.require("claude")
        help_text = cli_output("claude", "--help").stdout
        for flag in ("--bare", "--print", "--no-session-persistence", "--plugin-dir"):
            self.assertIn(flag, help_text)
        persistence = help_text.split("--no-session-persistence", 1)[1][:220]
        self.assertIn("only works with --print", persistence)

    def test_codex_profile_flags_exist(self) -> None:
        self.require("codex")
        exec_help = cli_output("codex", "exec", "--help").stdout
        for flag in ("--ephemeral", "--strict-config", "--sandbox"):
            self.assertIn(flag, exec_help)
        # Strict-config rejection of unknown `-c` keys happens at session
        # launch; `--version` and `doctor` do not reach config validation, so
        # that behavior cannot be probed here without starting a session.
        # Confirm it manually on the installed version before counting a path.


if __name__ == "__main__":
    unittest.main()
