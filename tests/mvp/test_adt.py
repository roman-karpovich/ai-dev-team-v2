from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADT = ROOT / "plugins" / "ai-dev-team-v2" / "scripts" / "adt.py"
ADT_BIN = ROOT / "plugins" / "ai-dev-team-v2" / "bin" / "adt"


class AdtCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name) / "repo"
        self.repo.mkdir()
        self._git("init", "-q")
        self._git("config", "user.name", "Test User")
        self._git("config", "user.email", "test@example.invalid")
        (self.repo / "app.txt").write_text("initial\n")
        self._git("add", "app.txt")
        self._git("commit", "-qm", "initial")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )

    def _adt(
        self, *args: str, expected_code: int = 0, cwd: Path | None = None
    ) -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
        result = subprocess.run(
            [sys.executable, str(ADT), *args],
            cwd=cwd or self.repo,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            expected_code,
            result.returncode,
            msg=f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
        )
        raw = result.stdout if expected_code == 0 else result.stderr
        return json.loads(raw), result

    def _start(self, host: str = "codex") -> dict[str, object]:
        payload, _ = self._adt(
            "start",
            "--host",
            host,
            "--goal",
            "Add a focused behavior",
        )
        return payload

    def _lease(self, payload: dict[str, object]) -> str:
        return payload["task"]["lease"]["id"]

    def _stored_state(self) -> tuple[Path, dict[str, object]]:
        matches = list((self.repo / ".git" / "ai-dev-team").glob(
            "workspaces/*/state.json"
        ))
        self.assertEqual(1, len(matches))
        return matches[0], json.loads(matches[0].read_text())

    def test_start_and_context_create_common_git_state(self) -> None:
        started = self._start()

        self.assertTrue(started["ok"])
        self.assertEqual("start", started["command"])
        task = started["task"]
        self.assertEqual("develop", task["kind"])
        self.assertEqual("balanced", task["profile"])
        self.assertEqual("active", task["status"])
        self.assertEqual("codex", task["lease"]["host"])
        self.assertEqual(2, task["snapshot"]["format_version"])

        context, _ = self._adt("context")
        self.assertEqual(task["id"], context["task"]["id"])
        self.assertEqual("Add a focused behavior", context["task"]["goal"])
        self.assertEqual([], context["task"]["checkpoints"])
        self.assertNotIn("id", context["task"]["lease"])
        self.assertFalse(context["drift"])

        installed_bin = Path(self.temp_dir.name) / "local" / "bin"
        installed_bin.mkdir(parents=True)
        installed_adt = installed_bin / "adt"
        installed_adt.symlink_to(ADT_BIN)
        installed_result = subprocess.run(
            [str(installed_adt), "--help"],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, installed_result.returncode, installed_result.stderr)
        self.assertIn("usage: adt", installed_result.stdout)

        state_path, state = self._stored_state()
        self.assertTrue(state_path.is_relative_to(self.repo / ".git"))
        self.assertEqual(task["id"], state["current_task_id"])
        self.assertFalse((self.repo / ".adt").exists())

        error, _ = self._adt(
            "start",
            "--host",
            "claude",
            "--goal",
            "Competing task",
            expected_code=3,
        )
        self.assertEqual("task_open", error["error"]["code"])

    def test_start_records_explicit_kind_and_profile_without_routing(self) -> None:
        payload, _ = self._adt(
            "start",
            "--host",
            "claude",
            "--kind",
            "review",
            "--profile",
            "economy",
            "--goal",
            "Review the candidate patch",
        )

        self.assertEqual("review", payload["task"]["kind"])
        self.assertEqual("economy", payload["task"]["profile"])
        self.assertEqual("claude", payload["task"]["lease"]["host"])

    def test_lease_guards_checkpoint_pause_and_resume(self) -> None:
        started = self._start()
        lease = self._lease(started)

        error, _ = self._adt(
            "checkpoint",
            "--host",
            "claude",
            "--lease",
            lease,
            expected_code=3,
        )
        self.assertEqual("lease_conflict", error["error"]["code"])

        checkpoint, _ = self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            lease,
            "--note",
            "Tests focused",
        )
        self.assertEqual("active", checkpoint["task"]["status"])
        self.assertEqual("Tests focused", checkpoint["checkpoint"]["note"])
        renewed_lease = self._lease(checkpoint)
        self.assertNotEqual(lease, renewed_lease)

        error, _ = self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            lease,
            expected_code=3,
        )
        self.assertEqual("lease_conflict", error["error"]["code"])

        taken_over, _ = self._adt(
            "takeover",
            "--host",
            "codex",
            "--reason",
            "Owner approved a fresh same-host session",
        )
        takeover_lease = self._lease(taken_over)
        self.assertNotEqual(renewed_lease, takeover_lease)

        error, _ = self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            renewed_lease,
            expected_code=3,
        )
        self.assertEqual("lease_conflict", error["error"]["code"])

        paused, _ = self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            takeover_lease,
            "--reason",
            "Need product input",
        )
        self.assertEqual("paused", paused["task"]["status"])
        self.assertIsNone(paused["task"]["lease"])
        self.assertEqual("codex", paused["task"]["resume_host"])

        resumed, _ = self._adt("resume", "--host", "codex")
        self.assertEqual("active", resumed["task"]["status"])
        self.assertEqual("codex", resumed["task"]["lease"]["host"])

    def test_handoff_requires_the_target_host_to_resume(self) -> None:
        started = self._start()

        handed_off, _ = self._adt(
            "handoff",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            "--to",
            "claude",
        )
        self.assertEqual("paused", handed_off["task"]["status"])
        self.assertEqual("claude", handed_off["task"]["resume_host"])

        error, _ = self._adt(
            "resume", "--host", "codex", expected_code=3
        )
        self.assertEqual("host_mismatch", error["error"]["code"])

        resumed, _ = self._adt("resume", "--host", "claude")
        self.assertEqual("claude", resumed["task"]["lease"]["host"])

    def test_resume_fails_closed_on_drift_until_explicitly_accepted(self) -> None:
        started = self._start()
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        (self.repo / "app.txt").write_text("changed while paused\n")

        error, _ = self._adt(
            "resume", "--host", "codex", expected_code=3
        )
        self.assertEqual("snapshot_drift", error["error"]["code"])
        self.assertNotEqual(
            error["error"]["details"]["expected_digest"],
            error["error"]["details"]["actual_digest"],
        )
        self.assertEqual(
            {"total": 0, "entries": [], "truncated": 0},
            error["error"]["details"]["expected_changes"],
        )
        self.assertEqual(
            "app.txt",
            error["error"]["details"]["actual_changes"]["entries"][0][
                "path"
            ],
        )

        resumed, _ = self._adt(
            "resume", "--host", "codex", "--accept-drift"
        )
        self.assertEqual("active", resumed["task"]["status"])
        self.assertTrue(resumed["accepted_drift"])
        self.assertEqual(
            resumed["live_snapshot"]["digest"],
            resumed["task"]["snapshot"]["digest"],
        )

    def test_unborn_staged_file_worktree_drift_is_detected(self) -> None:
        repo = Path(self.temp_dir.name) / "unborn"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-q"], cwd=repo, check=True, capture_output=True
        )
        candidate = repo / "candidate.txt"
        candidate.write_text("staged\n")
        subprocess.run(
            ["git", "add", "candidate.txt"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        candidate.write_text("baseline worktree\n")

        started, _ = self._adt(
            "start",
            "--host",
            "codex",
            "--goal",
            "Exercise an unborn repository",
            cwd=repo,
        )
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            cwd=repo,
        )
        candidate.write_text("drifted worktree\n")

        error, _ = self._adt(
            "resume", "--host", "codex", expected_code=3, cwd=repo
        )
        self.assertEqual("snapshot_drift", error["error"]["code"])
        expected_entry = error["error"]["details"]["expected_changes"][
            "entries"
        ][0]
        actual_entry = error["error"]["details"]["actual_changes"][
            "entries"
        ][0]
        self.assertEqual("candidate.txt", expected_entry["path"])
        self.assertEqual("candidate.txt", actual_entry["path"])
        self.assertNotEqual(
            expected_entry["worktree"]["sha256"],
            actual_entry["worktree"]["sha256"],
        )

    def test_state_keeps_digests_but_not_repository_file_contents(self) -> None:
        started = self._start()
        marker = "repository-content-must-not-be-persisted-784312"
        (self.repo / "app.txt").write_text(marker + "\n")

        checkpoint, _ = self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, _ = self._stored_state()
        raw_state = state_path.read_text()

        self.assertNotIn(marker, raw_state)
        self.assertRegex(checkpoint["checkpoint"]["snapshot"]["digest"], r"^sha256:")

    def test_complete_releases_lease_and_list_retains_task_history(self) -> None:
        first = self._start()
        completed, _ = self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(first),
            "--summary",
            "Delivered",
        )
        self.assertEqual("completed", completed["task"]["status"])
        self.assertIsNone(completed["task"]["lease"])

        status, _ = self._adt("status")
        self.assertEqual("develop", status["task"]["kind"])
        self.assertEqual("completed", status["task"]["status"])
        self.assertNotIn("goal", status["task"])
        self.assertNotIn("checkpoints", status["task"])
        self.assertNotIn("summary", status["task"])
        self.assertNotIn("Add a focused behavior", json.dumps(status))
        self.assertNotIn("Delivered", json.dumps(status))

        second = self._start(host="claude")
        listed, _ = self._adt("list")
        ids = [item["id"] for item in listed["tasks"]]
        self.assertEqual([first["task"]["id"], second["task"]["id"]], ids)
        self.assertEqual(second["task"]["id"], listed["current_task_id"])

if __name__ == "__main__":
    unittest.main()
