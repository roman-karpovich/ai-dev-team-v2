from __future__ import annotations

import fcntl
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
        self,
        *args: str,
        expected_code: int = 0,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
        result = subprocess.run(
            [sys.executable, str(ADT), *args],
            cwd=cwd or self.repo,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
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

    def _load_runtime(self):
        spec = importlib.util.spec_from_file_location("adt_under_test", ADT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        runtime = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = runtime
        self.addCleanup(sys.modules.pop, spec.name, None)
        previous_dont_write_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(runtime)
        finally:
            sys.dont_write_bytecode = previous_dont_write_bytecode
        return runtime

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

    def test_start_rejects_blank_goal_without_creating_state(self) -> None:
        for goal in ("", " \n\t"):
            with self.subTest(goal=goal):
                error, _ = self._adt(
                    "start",
                    "--host",
                    "codex",
                    "--goal",
                    goal,
                    expected_code=3,
                )
                self.assertEqual("goal_invalid", error["error"]["code"])
                self.assertEqual(
                    [],
                    list(
                        (self.repo / ".git" / "ai-dev-team").glob(
                            "workspaces/*/state.json"
                        )
                    ),
                )

    def test_status_context_and_list_use_read_only_shared_lock(self) -> None:
        self._start()
        state_path, state = self._stored_state()
        lock_path = state_path.with_name("state.lock")
        state_before = state_path.read_bytes()

        lock_path.chmod(0o400)
        lock_mode_before = stat.S_IMODE(lock_path.stat().st_mode)
        lock_mtime_before = lock_path.stat().st_mtime_ns
        lock_mode_after = None
        lock_mtime_after = None
        try:
            with lock_path.open("rb") as held_lock:
                fcntl.flock(held_lock.fileno(), fcntl.LOCK_SH)
                try:
                    for command in ("status", "context", "list"):
                        with self.subTest(command=command):
                            payload, _ = self._adt(command, timeout=2)
                            self.assertTrue(payload["ok"])
                finally:
                    fcntl.flock(held_lock.fileno(), fcntl.LOCK_UN)
            lock_mode_after = stat.S_IMODE(lock_path.stat().st_mode)
            lock_mtime_after = lock_path.stat().st_mtime_ns
        finally:
            lock_path.chmod(0o600)

        self.assertEqual(state_before, state_path.read_bytes())
        self.assertEqual(state["revision"], self._stored_state()[1]["revision"])
        self.assertEqual(lock_mode_before, lock_mode_after)
        self.assertEqual(lock_mtime_before, lock_mtime_after)

    def test_mutation_lock_remains_exclusive(self) -> None:
        runtime = self._load_runtime()

        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="lock-contract",
        )
        store = runtime.StateStore(workspace)

        with mock.patch.object(runtime.fcntl, "flock") as flock:
            with store.lock():
                pass
            self.assertEqual(fcntl.LOCK_EX, flock.call_args_list[0].args[1])

        with mock.patch.object(runtime.fcntl, "flock") as flock:
            with store.lock(shared=True):
                pass
            self.assertEqual(fcntl.LOCK_SH, flock.call_args_list[0].args[1])

    def test_linked_worktree_lock_failure_reports_state_unavailable(self) -> None:
        runtime = self._load_runtime()
        linked_worktree = Path(self.temp_dir.name) / "linked"
        self._git("worktree", "add", "-q", "-b", "diagnostic", str(linked_worktree))
        workspace = runtime.GitWorkspace.discover(linked_worktree)
        self.assertEqual((self.repo / ".git").resolve(), workspace.common_dir)
        store = runtime.StateStore(workspace)

        with mock.patch.object(
            runtime.Path,
            "mkdir",
            side_effect=PermissionError("private machine path"),
        ):
            with self.assertRaises(runtime.CliError) as raised:
                with store.lock():
                    self.fail("lock must not be acquired")

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(
            "ADT needs read/write access to its state directory under the "
            "common Git directory.",
            raised.exception.message,
        )
        self.assertNotIn("private machine path", raised.exception.message)

    def test_lock_cleanup_does_not_overwrite_body_cli_error(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="cleanup-failure",
        )
        store = runtime.StateStore(workspace)

        original = runtime.CliError("body_error", "Preserve this error.")
        with self.subTest(operation="unlock"):
            with mock.patch.object(
                runtime.fcntl,
                "flock",
                side_effect=[None, OSError("unlock failed")],
            ):
                with self.assertRaises(runtime.CliError) as raised:
                    with store.lock():
                        raise original
            self.assertIs(original, raised.exception)

        lock_file = mock.Mock()
        lock_file.fileno.return_value = 42
        lock_file.close.side_effect = OSError("close failed")
        with self.subTest(operation="close"):
            with (
                mock.patch.object(runtime.Path, "open", return_value=lock_file),
                mock.patch.object(runtime.os, "chmod"),
                mock.patch.object(runtime.fcntl, "flock"),
            ):
                with self.assertRaises(runtime.CliError) as raised:
                    with store.lock():
                        raise original
            self.assertIs(original, raised.exception)

    def test_state_save_failure_reports_state_unavailable_without_path(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="save-unavailable",
        )
        store = runtime.StateStore(workspace)

        with mock.patch.object(
            runtime.tempfile,
            "mkstemp",
            side_effect=PermissionError("private machine path"),
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.save({"schema_version": runtime.SCHEMA_VERSION})

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(
            "ADT needs read/write access to its state directory under the "
            "common Git directory.",
            raised.exception.message,
        )
        self.assertNotIn("private machine path", raised.exception.message)

    def test_state_save_cleans_temp_and_preserves_state_when_replace_fails(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="atomic-save-failure",
        )
        store = runtime.StateStore(workspace)
        store.directory.mkdir(parents=True)
        original = b"existing state\n"
        store.state_path.write_bytes(original)

        with mock.patch.object(
            runtime.os,
            "replace",
            side_effect=OSError("replace failed"),
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.save({"schema_version": runtime.SCHEMA_VERSION})

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(original, store.state_path.read_bytes())
        self.assertEqual([], list(store.directory.glob("state.*.tmp")))

    def test_state_read_failure_is_unavailable_not_corrupt(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="read-unavailable",
        )
        store = runtime.StateStore(workspace)

        with (
            mock.patch.object(runtime.Path, "stat", return_value=mock.Mock()),
            mock.patch.object(
                runtime.Path,
                "read_text",
                side_effect=PermissionError("private machine path"),
            ),
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.load()

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertNotEqual("state_corrupt", raised.exception.code)
        self.assertNotIn("private machine path", raised.exception.message)

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
