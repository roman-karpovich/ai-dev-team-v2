from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import os
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

    def _assert_persisted_status_round_trips(
        self,
        expected_status: str,
        expected_path: str,
        *,
        expected_original_path: str | None = None,
    ) -> None:
        started = self._start()
        _, state_value = self._stored_state()
        persisted_snapshot = state_value["tasks"][0]["snapshot"]
        self.assertEqual(started["task"]["snapshot"], persisted_snapshot)
        runtime = self._load_runtime()
        self.assertTrue(runtime._valid_snapshot(persisted_snapshot))
        emitted_entry = next(
            entry
            for entry in persisted_snapshot["changes"]["entries"]
            if entry["status"] == expected_status
        )
        self.assertEqual(expected_path, emitted_entry["path"])
        if expected_original_path is None:
            self.assertNotIn("original_path", emitted_entry)
        else:
            self.assertEqual(
                expected_original_path,
                emitted_entry["original_path"],
            )

        for command in ("status", "context", "list"):
            with self.subTest(status=expected_status, command=command):
                payload, _ = self._adt(command)
                self.assertTrue(payload["ok"])

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

    def test_review_gate_help_routes_individual_reviewers_to_task_lifecycle(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ADT), "review-gate", "--help"],
            check=False,
            text=True,
            capture_output=True,
            env={**os.environ, "COLUMNS": "60"},
        )

        self.assertEqual(0, result.returncode, result.stderr)
        help_text = " ".join(result.stdout.lower().split())
        self.assertIn("launcher-only", help_text)
        self.assertIn("not an individual review path", help_text)
        self.assertIn("at least two paths are sealed", help_text)
        self.assertIn("does not launch a reviewer", help_text)
        self.assertIn("adt.portable-cold-review-bundle.v0", help_text)
        self.assertIn("bundle.json", help_text)
        self.assertIn(
            "bundle.json exact top-level fields: contract_version work_order paths",
            help_text,
        )
        self.assertIn("--bundle directory", help_text)
        self.assertLessEqual(max(map(len, result.stdout.splitlines())), 60)

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

    def test_lock_cleanup_failure_after_success_reports_state_unavailable(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="successful-body-cleanup-failure",
        )
        store = runtime.StateStore(workspace)

        with self.subTest(operation="unlock"):
            with mock.patch.object(
                runtime.fcntl,
                "flock",
                side_effect=[None, OSError("unlock failed")],
            ):
                with self.assertRaises(runtime.CliError) as raised:
                    with store.lock():
                        pass
            self.assertEqual("state_unavailable", raised.exception.code)
            self.assertEqual(4, raised.exception.exit_code)
            self.assertEqual(
                runtime.STATE_UNAVAILABLE_MESSAGE,
                raised.exception.message,
            )

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
                        pass
            self.assertEqual("state_unavailable", raised.exception.code)
            self.assertEqual(4, raised.exception.exit_code)
            self.assertEqual(
                runtime.STATE_UNAVAILABLE_MESSAGE,
                raised.exception.message,
            )

    def test_state_exists_metadata_failure_reports_state_unavailable(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="metadata-unavailable",
        )
        store = runtime.StateStore(workspace)

        with mock.patch.object(
            runtime.Path,
            "stat",
            side_effect=PermissionError("private machine path"),
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.exists()

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(4, raised.exception.exit_code)
        self.assertEqual(runtime.STATE_UNAVAILABLE_MESSAGE, raised.exception.message)
        self.assertNotIn("private machine path", raised.exception.message)

    def test_absent_state_has_no_task_status_and_empty_list(self) -> None:
        for command in ("status", "context"):
            with self.subTest(command=command):
                error, _ = self._adt(command, expected_code=3)
                self.assertEqual("no_task", error["error"]["code"])

        listed, _ = self._adt("list")
        self.assertEqual(0, listed["revision"])
        self.assertIsNone(listed["current_task_id"])
        self.assertEqual([], listed["tasks"])

    def test_state_load_rejects_malformed_unsupported_and_invalid_shapes(self) -> None:
        self._start()
        state_path, baseline = self._stored_state()
        duplicate_tasks = copy.deepcopy(baseline["tasks"])
        duplicate_tasks.append(copy.deepcopy(duplicate_tasks[0]))
        cases = (
            ("malformed-json", "{", "state_corrupt"),
            ("non-object", json.dumps([]), "state_version_unsupported"),
            (
                "unsupported-version",
                json.dumps({**baseline, "schema_version": 999}),
                "state_version_unsupported",
            ),
            (
                "invalid-workspace-shape",
                json.dumps({**baseline, "workspace": []}),
                "state_corrupt",
            ),
            (
                "empty-workspace",
                json.dumps({**baseline, "workspace": {}}),
                "state_corrupt",
            ),
            (
                "invalid-workspace-id",
                json.dumps(
                    {
                        **baseline,
                        "workspace": {**baseline["workspace"], "id": "bad"},
                    }
                ),
                "state_corrupt",
            ),
            (
                "valid-different-workspace-id",
                json.dumps(
                    {
                        **baseline,
                        "workspace": {**baseline["workspace"], "id": "0" * 24},
                    }
                ),
                "workspace_mismatch",
            ),
            (
                "invalid-workspace-root",
                json.dumps(
                    {
                        **baseline,
                        "workspace": {**baseline["workspace"], "root": []},
                    }
                ),
                "state_corrupt",
            ),
            (
                "invalid-tasks-shape",
                json.dumps({**baseline, "tasks": {}}),
                "state_corrupt",
            ),
            (
                "duplicate-task-ids",
                json.dumps({**baseline, "tasks": duplicate_tasks}),
                "state_corrupt",
            ),
        )

        for label, encoded, expected_code in cases:
            with self.subTest(case=label):
                state_path.write_text(encoded)
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual(expected_code, error["error"]["code"])

    def test_state_load_normalizes_json_parser_limits_to_state_corrupt(self) -> None:
        self._start()
        state_path, _ = self._stored_state()
        malformed_values = (
            '{"schema_version":' + "9" * 5000 + "}",
            "[" * 10000 + "0" + "]" * 10000,
        )

        for encoded in malformed_values:
            with self.subTest(prefix=encoded[:20]):
                state_path.write_text(encoded)
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])
                self.assertEqual(
                    "The workspace state cannot be read as valid JSON.",
                    error["error"]["message"],
                )
                self.assertNotIn(str(state_path), error["error"]["message"])

    def test_persisted_numeric_schema_fields_require_true_integers(self) -> None:
        started = self._start()
        (self.repo / "app.txt").write_text("changed before checkpoint\n")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, baseline = self._stored_state()

        for invalid_schema in (True, 2.0):
            with self.subTest(field="schema-version", value=invalid_schema):
                state_value = copy.deepcopy(baseline)
                state_value["schema_version"] = invalid_schema
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_version_unsupported", error["error"]["code"])

        float_revision = copy.deepcopy(baseline)
        float_revision["revision"] = float(float_revision["revision"])
        state_path.write_text(json.dumps(float_revision))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

        for label, invalid_value in (
            ("snapshot-format-version", True),
            ("snapshot-format-version", 2.0),
            ("snapshot-format-version", 99),
            ("checkpoint-sequence", True),
            ("checkpoint-sequence", 1.0),
            ("snapshot-total", 1.0),
            ("snapshot-truncated", 0.0),
            ("fingerprint-size", 1.0),
        ):
            with self.subTest(field=label, value=invalid_value):
                state_value = copy.deepcopy(baseline)
                task = state_value["tasks"][0]
                if label == "snapshot-format-version":
                    for snapshot in (
                        task["snapshot"],
                        task["checkpoints"][0]["snapshot"],
                    ):
                        snapshot["format_version"] = invalid_value
                elif label == "checkpoint-sequence":
                    task["checkpoints"][0]["sequence"] = invalid_value
                else:
                    for snapshot in (
                        task["snapshot"],
                        task["checkpoints"][0]["snapshot"],
                    ):
                        if label == "snapshot-total":
                            snapshot["changes"]["total"] = invalid_value
                        elif label == "snapshot-truncated":
                            snapshot["changes"]["truncated"] = invalid_value
                        else:
                            snapshot["changes"]["entries"][0]["worktree"][
                                "size"
                            ] = invalid_value
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_revision_boolean_is_rejected_at_the_minimum_revision_floor(
        self,
    ) -> None:
        self._start()
        state_path, state_value = self._stored_state()
        self.assertEqual(1, state_value["revision"])
        state_value["revision"] = True
        state_path.write_text(json.dumps(state_value))

        error, _ = self._adt("status", expected_code=4)

        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_snapshot_coherence_ignores_unknown_nested_object_keys(self) -> None:
        started = self._start()
        (self.repo / "app.txt").write_text("changed before checkpoint\n")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, baseline = self._stored_state()

        for level in ("snapshot", "changes", "entry", "fingerprint"):
            with self.subTest(level=level):
                state_value = copy.deepcopy(baseline)
                task = state_value["tasks"][0]
                task_target = task["snapshot"]
                checkpoint_target = task["checkpoints"][-1]["snapshot"]
                if level in {"changes", "entry", "fingerprint"}:
                    task_target = task_target["changes"]
                    checkpoint_target = checkpoint_target["changes"]
                if level in {"entry", "fingerprint"}:
                    task_target = task_target["entries"][0]
                    checkpoint_target = checkpoint_target["entries"][0]
                if level == "fingerprint":
                    task_target = task_target["worktree"]
                    checkpoint_target = checkpoint_target["worktree"]
                task_target["future_extension"] = {"source": "task"}
                checkpoint_target["future_extension"] = {"source": "checkpoint"}
                state_path.write_text(json.dumps(state_value))
                status, _ = self._adt("status")
                self.assertEqual(task["id"], status["task"]["id"])

        state_value = copy.deepcopy(baseline)
        task = state_value["tasks"][0]
        task["snapshot"].pop("head")
        task["checkpoints"][-1]["snapshot"].pop("head")
        state_path.write_text(json.dumps(state_value))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_snapshot_coherence_ignores_original_fingerprint_extensions(
        self,
    ) -> None:
        (self.repo / "rename-me.txt").write_text("rename this file\n")
        self._git("add", "rename-me.txt")
        self._git("commit", "-qm", "add rename candidate")
        started = self._start()
        self._git("mv", "rename-me.txt", "renamed.txt")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, state_value = self._stored_state()
        task = state_value["tasks"][0]
        task_entry = next(
            entry
            for entry in task["snapshot"]["changes"]["entries"]
            if "R" in entry["status"]
        )
        checkpoint_entry = next(
            entry
            for entry in task["checkpoints"][-1]["snapshot"]["changes"][
                "entries"
            ]
            if "R" in entry["status"]
        )
        task_entry["original_worktree"] = copy.deepcopy(task_entry["worktree"])
        checkpoint_entry["original_worktree"] = copy.deepcopy(
            checkpoint_entry["worktree"]
        )
        task_entry["original_worktree"]["future_extension"] = {"source": "task"}
        checkpoint_entry["original_worktree"]["future_extension"] = {
            "source": "checkpoint"
        }
        state_path.write_text(json.dumps(state_value))

        status, _ = self._adt("status")

        self.assertEqual(task["id"], status["task"]["id"])

    def test_snapshot_coherence_still_compares_all_declared_nested_fields(
        self,
    ) -> None:
        (self.repo / "rename-me.txt").write_text("rename this file\n")
        self._git("add", "rename-me.txt")
        self._git("commit", "-qm", "add rename candidate")
        started = self._start()
        (self.repo / "app.txt").write_text("changed before checkpoint\n")
        self._git("mv", "rename-me.txt", "renamed.txt")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, baseline = self._stored_state()

        def entry(snapshot, path):
            return next(
                value
                for value in snapshot["changes"]["entries"]
                if value["path"] == path
            )

        def renamed_entry(snapshot):
            return next(
                value
                for value in snapshot["changes"]["entries"]
                if "R" in value["status"]
            )

        cases = []
        changed_digest = copy.deepcopy(baseline)
        changed_digest["tasks"][0]["snapshot"]["digest"] = (
            "sha256:" + "0" * 64
        )
        cases.append(("snapshot", changed_digest))

        changed_entries = copy.deepcopy(baseline)
        changes = changed_entries["tasks"][0]["snapshot"]["changes"]
        changes["entries"].append(copy.deepcopy(changes["entries"][0]))
        changes["total"] += 1
        cases.append(("changes", changed_entries))

        changed_path = copy.deepcopy(baseline)
        changed_path["tasks"][0]["snapshot"]["changes"]["entries"][0][
            "path"
        ] = "other.txt"
        cases.append(("entry", changed_path))

        changed_size = copy.deepcopy(baseline)
        changed_size["tasks"][0]["snapshot"]["changes"]["entries"][0][
            "worktree"
        ]["size"] += 1
        cases.append(("fingerprint", changed_size))

        changed_head = copy.deepcopy(baseline)
        changed_head["tasks"][0]["snapshot"]["head"] = None
        cases.append(("head", changed_head))

        changed_status = copy.deepcopy(baseline)
        entry(changed_status["tasks"][0]["snapshot"], "app.txt")[
            "status"
        ] = "A "
        cases.append(("entry-status", changed_status))

        changed_index_value = copy.deepcopy(baseline)
        indexed_entry = entry(
            changed_index_value["tasks"][0]["snapshot"], "app.txt"
        )
        mode, object_id, stage = indexed_entry["index"][0].split(" ")
        indexed_entry["index"][0] = f"{mode} {'0' * len(object_id)} {stage}"
        cases.append(("index-value", changed_index_value))

        for label, field, alternative in (
            ("fingerprint-mode", "mode", "0o777"),
            ("fingerprint-kind", "kind", "special"),
            ("fingerprint-sha256", "sha256", "0" * 64),
        ):
            state_value = copy.deepcopy(baseline)
            fingerprint = entry(
                state_value["tasks"][0]["snapshot"], "app.txt"
            )["worktree"]
            if fingerprint[field] == alternative:
                alternative = {
                    "mode": "0o666",
                    "kind": "file",
                    "sha256": "1" * 64,
                }[field]
            fingerprint[field] = alternative
            cases.append((label, state_value))

        missing_worktree = copy.deepcopy(baseline)
        entry(missing_worktree["tasks"][0]["snapshot"], "app.txt")[
            "worktree"
        ] = None
        cases.append(("worktree-none", missing_worktree))

        changed_accounting = copy.deepcopy(baseline)
        changes = changed_accounting["tasks"][0]["snapshot"]["changes"]
        changes["total"] += 1
        changes["truncated"] += 1
        cases.append(("total-truncated", changed_accounting))

        changed_entry_order = copy.deepcopy(baseline)
        changed_entry_order["tasks"][0]["snapshot"]["changes"][
            "entries"
        ].reverse()
        cases.append(("entry-order", changed_entry_order))

        changed_index_order = copy.deepcopy(baseline)
        task = changed_index_order["tasks"][0]
        task_entry = entry(task["snapshot"], "app.txt")
        checkpoint_entry = entry(task["checkpoints"][-1]["snapshot"], "app.txt")
        first_item = task_entry["index"][0]
        mode, object_id, stage = first_item.split(" ")
        second_stage = "1" if stage != "1" else "2"
        second_item = f"{mode} {object_id} {second_stage}"
        task_entry["index"] = [first_item, second_item]
        checkpoint_entry["index"] = [second_item, first_item]
        cases.append(("index-order", changed_index_order))

        changed_original_path = copy.deepcopy(baseline)
        renamed_entry(changed_original_path["tasks"][0]["snapshot"])[
            "original_path"
        ] = "different-original.txt"
        cases.append(("original-path", changed_original_path))

        changed_original_index = copy.deepcopy(baseline)
        original_entry = renamed_entry(
            changed_original_index["tasks"][0]["snapshot"]
        )
        original_entry["original_index"].append(original_entry["index"][0])
        cases.append(("original-index", changed_original_index))

        changed_original_index_order = copy.deepcopy(baseline)
        task = changed_original_index_order["tasks"][0]
        task_entry = renamed_entry(task["snapshot"])
        checkpoint_entry = renamed_entry(task["checkpoints"][-1]["snapshot"])
        mode, object_id, _ = task_entry["index"][0].split(" ")
        first_item = f"{mode} {object_id} 1"
        second_item = f"{mode} {object_id} 2"
        task_entry["original_index"] = [first_item, second_item]
        checkpoint_entry["original_index"] = [second_item, first_item]
        cases.append(("original-index-order", changed_original_index_order))

        changed_original_worktree = copy.deepcopy(baseline)
        original_entry = renamed_entry(
            changed_original_worktree["tasks"][0]["snapshot"]
        )
        original_entry["original_worktree"] = copy.deepcopy(
            original_entry["worktree"]
        )
        cases.append(("original-worktree", changed_original_worktree))

        runtime = self._load_runtime()
        for level, state_value in cases:
            with self.subTest(level=level):
                task = state_value["tasks"][0]
                self.assertTrue(
                    runtime._valid_snapshot(task["snapshot"]),
                    msg=f"task snapshot invalid for {level}",
                )
                self.assertTrue(
                    runtime._valid_snapshot(
                        task["checkpoints"][-1]["snapshot"]
                    ),
                    msg=f"checkpoint snapshot invalid for {level}",
                )
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_state_load_rejects_malformed_persisted_task_shapes(self) -> None:
        started = self._start()
        (self.repo / "app.txt").write_text("changed before checkpoint\n")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            "--note",
            "Keep this note",
        )
        self._adt(
            "takeover",
            "--host",
            "codex",
            "--reason",
            "Fresh local session",
        )
        state_path, baseline = self._stored_state()
        private_marker = "/private/machine/state.json"

        def changed(path: tuple[object, ...], value: object) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            target = state_value
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            return state_value

        def added(
            path: tuple[object, ...], key: str, value: object
        ) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            target = state_value
            for part in path:
                target = target[part]
            target[key] = value
            return state_value

        def task_changed(**values: object) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            state_value["tasks"][0].update(values)
            return state_value

        def checkpoint_changed(**values: object) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            state_value["tasks"][0]["checkpoints"][0].update(values)
            return state_value

        def removed(path: tuple[object, ...]) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            target = state_value
            for part in path[:-1]:
                target = target[part]
            del target[path[-1]]
            return state_value

        task_path = ("tasks", 0)
        checkpoint_path = (*task_path, "checkpoints", 0)
        takeover_path = (*task_path, "takeovers", 0)
        snapshot_entry_path = (*task_path, "snapshot", "changes", "entries", 0)
        checkpoint_entry_path = (
            *checkpoint_path,
            "snapshot",
            "changes",
            "entries",
            0,
        )
        fingerprint_path = (*snapshot_entry_path, "worktree")
        cases = (
            ("revision-bool", changed(("revision",), True)),
            ("revision-negative", changed(("revision",), -1)),
            ("revision-too-small", changed(("revision",), 2)),
            ("state-created-at", changed(("created_at",), [])),
            ("state-updated-at", changed(("updated_at",), None)),
            ("missing-current-task-id", removed(("current_task_id",))),
            ("current-task-id", changed(("current_task_id",), [])),
            ("null-current-with-history", changed(("current_task_id",), None)),
            ("task-entry", changed(task_path, [])),
            ("task-id", changed((*task_path, "id"), private_marker)),
            ("missing-resume-host", removed((*task_path, "resume_host"))),
            ("task-kind", changed((*task_path, "kind"), [])),
            ("task-profile", changed((*task_path, "profile"), "unknown")),
            ("task-goal", changed((*task_path, "goal"), "")),
            ("task-status", changed((*task_path, "status"), "unknown")),
            ("task-created-at", changed((*task_path, "created_at"), None)),
            ("task-updated-at", changed((*task_path, "updated_at"), [])),
            ("active-lease", changed((*task_path, "lease"), None)),
            ("paused-with-lease", task_changed(status="paused")),
            (
                "paused-without-resume-host",
                task_changed(status="paused", lease=None, resume_host=None),
            ),
            (
                "completed-without-completed-at",
                task_changed(status="completed", lease=None, resume_host=None),
            ),
            ("lease-id", changed((*task_path, "lease", "id"), "bad")),
            ("lease-host", changed((*task_path, "lease", "host"), [])),
            (
                "lease-acquired-at",
                changed((*task_path, "lease", "acquired_at"), []),
            ),
            ("active-resume-host", changed((*task_path, "resume_host"), "claude")),
            ("snapshot-shape", changed((*task_path, "snapshot"), [])),
            (
                "snapshot-version",
                changed((*task_path, "snapshot", "format_version"), True),
            ),
            (
                "snapshot-digest",
                changed((*task_path, "snapshot", "digest"), private_marker),
            ),
            ("snapshot-head", changed((*task_path, "snapshot", "head"), [])),
            ("snapshot-dirty", changed((*task_path, "snapshot", "dirty"), 1)),
            ("snapshot-changes", changed((*task_path, "snapshot", "changes"), [])),
            (
                "snapshot-change-count",
                changed((*task_path, "snapshot", "changes", "total"), 2),
            ),
            ("snapshot-entry", changed(snapshot_entry_path, [])),
            ("snapshot-entry-status", changed((*snapshot_entry_path, "status"), [])),
            (
                "snapshot-entry-impossible-clean-status",
                changed((*snapshot_entry_path, "status"), "  "),
            ),
            (
                "snapshot-entry-invalid-status-combination",
                changed((*snapshot_entry_path, "status"), "MA"),
            ),
            ("snapshot-entry-path", changed((*snapshot_entry_path, "path"), [])),
            ("snapshot-entry-index", changed((*snapshot_entry_path, "index"), {})),
            (
                "snapshot-entry-index-item",
                changed((*snapshot_entry_path, "index", 0), []),
            ),
            (
                "snapshot-entry-worktree",
                changed((*snapshot_entry_path, "worktree"), []),
            ),
            ("fingerprint-mode", changed((*fingerprint_path, "mode"), [])),
            ("fingerprint-size", changed((*fingerprint_path, "size"), True)),
            ("fingerprint-kind", changed((*fingerprint_path, "kind"), "unknown")),
            ("fingerprint-digest", changed((*fingerprint_path, "sha256"), "bad")),
            (
                "incomplete-original-entry",
                added(snapshot_entry_path, "original_path", "old-app.txt"),
            ),
            (
                "rename-without-original-fields",
                changed((*snapshot_entry_path, "status"), "R "),
            ),
            ("checkpoints", changed((*task_path, "checkpoints"), private_marker)),
            ("checkpoint-shape", changed(checkpoint_path, [])),
            ("checkpoint-id", changed((*checkpoint_path, "id"), "bad")),
            ("checkpoint-sequence", changed((*checkpoint_path, "sequence"), 2)),
            ("checkpoint-kind", changed((*checkpoint_path, "kind"), [])),
            ("checkpoint-host", changed((*checkpoint_path, "host"), [])),
            (
                "checkpoint-created-at",
                changed((*checkpoint_path, "created_at"), None),
            ),
            ("checkpoint-snapshot", changed((*checkpoint_path, "snapshot"), [])),
            (
                "checkpoint-snapshot-entry",
                changed((*checkpoint_entry_path, "status"), []),
            ),
            ("checkpoint-note", changed((*checkpoint_path, "note"), [])),
            (
                "checkpoint-target-host",
                added(checkpoint_path, "target_host", []),
            ),
            (
                "manual-target-host",
                added(checkpoint_path, "target_host", "claude"),
            ),
            (
                "checkpoint-previous-digest",
                added(checkpoint_path, "previous_digest", []),
            ),
            (
                "manual-previous-digest",
                added(
                    checkpoint_path,
                    "previous_digest",
                    "sha256:" + "0" * 64,
                ),
            ),
            (
                "handoff-missing-target-host",
                changed((*checkpoint_path, "kind"), "handoff"),
            ),
            (
                "drift-missing-previous-digest",
                changed((*checkpoint_path, "kind"), "drift-accepted"),
            ),
            (
                "drift-invalid-previous-digest",
                checkpoint_changed(
                    kind="drift-accepted",
                    previous_digest=private_marker,
                ),
            ),
            (
                "drift-target-host",
                checkpoint_changed(
                    kind="drift-accepted",
                    previous_digest="sha256:" + "0" * 64,
                    target_host="claude",
                ),
            ),
            ("takeovers", changed((*task_path, "takeovers"), private_marker)),
            ("takeover-shape", changed(takeover_path, [])),
            ("takeover-host", changed((*takeover_path, "host"), [])),
            (
                "takeover-created-at",
                changed((*takeover_path, "created_at"), None),
            ),
            ("takeover-reason", changed((*takeover_path, "reason"), [])),
            ("optional-summary", changed((*task_path, "summary"), [])),
            ("optional-completed-at", added(task_path, "completed_at", [])),
            (
                "active-stale-completed-at",
                added(task_path, "completed_at", "2026-07-17T00:00:00Z"),
            ),
            ("active-stale-summary", added(task_path, "summary", "stale")),
            (
                "paused-stale-summary",
                task_changed(
                    status="paused",
                    lease=None,
                    resume_host="codex",
                    summary="stale",
                ),
            ),
            (
                "active-complete-terminal-checkpoint",
                changed((*checkpoint_path, "kind"), "complete"),
            ),
            (
                "task-checkpoint-snapshot-mismatch",
                changed(
                    (*task_path, "snapshot", "digest"),
                    "sha256:" + "0" * 64,
                ),
            ),
        )

        for label, state_value in cases:
            with self.subTest(case=label):
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])
                self.assertNotIn(private_marker, error["error"]["message"])

    def test_takeover_rejects_malformed_takeover_history(self) -> None:
        self._start()
        state_path, baseline = self._stored_state()
        task = baseline["tasks"][0]
        state_path.write_text(
            json.dumps({**baseline, "tasks": [{**task, "takeovers": "corrupt"}]})
        )

        error, _ = self._adt(
            "takeover",
            "--host",
            "codex",
            "--reason",
            "Recover the task",
            expected_code=4,
        )

        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_start_rejects_corrupt_retained_history_without_mutating_it(self) -> None:
        started = self._start()
        (self.repo / "app.txt").write_text("changed before completion\n")
        self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, state_value = self._stored_state()
        task = state_value["tasks"][0]
        task["snapshot"]["changes"]["entries"][0]["status"] = []
        task["checkpoints"][-1]["snapshot"]["changes"]["entries"][0][
            "status"
        ] = []
        state_path.write_text(json.dumps(state_value))
        corrupt_bytes = state_path.read_bytes()

        error, _ = self._adt(
            "start",
            "--host",
            "claude",
            "--goal",
            "Do not append over corrupt history",
            expected_code=4,
        )

        self.assertEqual("state_corrupt", error["error"]["code"])
        self.assertEqual(corrupt_bytes, state_path.read_bytes())

    def test_completed_task_relations_are_validated(self) -> None:
        started = self._start()
        self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            "--summary",
            "Delivered",
        )
        state_path, baseline = self._stored_state()

        def changed(path: tuple[object, ...], value: object) -> dict[str, object]:
            state_value = copy.deepcopy(baseline)
            target = state_value
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            return state_value

        task_path = ("tasks", 0)
        checkpoint_path = (*task_path, "checkpoints", 0)
        cases = (
            ("terminal-kind", changed((*checkpoint_path, "kind"), "manual")),
            (
                "completed-at",
                changed((*task_path, "completed_at"), "2026-07-17T00:00:00Z"),
            ),
            (
                "updated-at",
                changed((*task_path, "updated_at"), "2026-07-17T00:00:00Z"),
            ),
            ("summary", changed((*task_path, "summary"), "Different")),
            (
                "snapshot",
                changed(
                    (*task_path, "snapshot", "digest"),
                    "sha256:" + "0" * 64,
                ),
            ),
        )

        for label, state_value in cases:
            with self.subTest(case=label):
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_snapshot_validator_accepts_rename_and_missing_worktree_shapes(
        self,
    ) -> None:
        removed = self.repo / "removed.txt"
        removed.write_text("remove after task starts\n")
        self._git("add", "removed.txt")
        self._git("commit", "-qm", "add removal candidate")
        started = self._start()
        self._git("mv", "app.txt", "renamed.txt")
        removed.unlink()

        checkpoint, _ = self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        context, _ = self._adt("context")

        entries = checkpoint["checkpoint"]["snapshot"]["changes"]["entries"]
        renamed = next(entry for entry in entries if "R" in entry["status"])
        deleted = next(entry for entry in entries if entry["path"] == "removed.txt")
        self.assertIsNone(renamed["original_worktree"])
        self.assertIsNone(deleted["worktree"])
        self.assertEqual(
            checkpoint["checkpoint"]["snapshot"], context["task"]["snapshot"]
        )

        state_path, state_value = self._stored_state()
        task = state_value["tasks"][0]
        snapshots = (task["snapshot"], task["checkpoints"][-1]["snapshot"])
        for snapshot in snapshots:
            renamed_entry = next(
                entry
                for entry in snapshot["changes"]["entries"]
                if "R" in entry["status"]
            )
            renamed_entry["status"] = renamed_entry["status"].replace("R", "C")
        state_path.write_text(json.dumps(state_value))
        copied, _ = self._adt("context")
        self.assertTrue(
            any(
                "C" in entry["status"]
                for entry in copied["task"]["snapshot"]["changes"]["entries"]
            )
        )

        invalid_cases = ("original_worktree", "original_index")
        for field in invalid_cases:
            with self.subTest(copy_field=field):
                malformed = copy.deepcopy(state_value)
                task = malformed["tasks"][0]
                for snapshot in (
                    task["snapshot"],
                    task["checkpoints"][-1]["snapshot"],
                ):
                    copied_entry = next(
                        entry
                        for entry in snapshot["changes"]["entries"]
                        if "C" in entry["status"]
                    )
                    if field == "original_worktree":
                        copied_entry[field] = []
                    else:
                        del copied_entry[field]
                state_path.write_text(json.dumps(malformed))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_original_fields_are_symmetric_for_rename_and_plain_entries(
        self,
    ) -> None:
        (self.repo / "rename-me.txt").write_text("rename this file\n")
        self._git("add", "rename-me.txt")
        self._git("commit", "-qm", "add rename candidate")
        started = self._start()
        (self.repo / "app.txt").write_text("changed before checkpoint\n")
        self._git("mv", "rename-me.txt", "renamed.txt")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, baseline = self._stored_state()

        def snapshots(state_value):
            task = state_value["tasks"][0]
            return (task["snapshot"], task["checkpoints"][-1]["snapshot"])

        def rename_entry(snapshot):
            return next(
                entry
                for entry in snapshot["changes"]["entries"]
                if "R" in entry["status"]
            )

        def plain_entry(snapshot):
            return next(
                entry
                for entry in snapshot["changes"]["entries"]
                if entry["path"] == "app.txt"
            )

        missing_original_worktree = copy.deepcopy(baseline)
        for snapshot in snapshots(missing_original_worktree):
            del rename_entry(snapshot)["original_worktree"]

        stray_plain_originals = copy.deepcopy(baseline)
        for snapshot in snapshots(stray_plain_originals):
            plain = plain_entry(snapshot)
            plain["original_path"] = "old-app.txt"
            plain["original_index"] = copy.deepcopy(plain["index"])
            plain["original_worktree"] = copy.deepcopy(plain["worktree"])

        for label, state_value in (
            ("rename-missing-original-worktree", missing_original_worktree),
            ("plain-entry-with-original-fields", stray_plain_originals),
        ):
            with self.subTest(case=label):
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_paused_task_terminal_checkpoint_relations_are_validated(self) -> None:
        started = self._start()
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        state_path, paused = self._stored_state()

        pause_cases = (
            ("terminal-kind", {"kind": "manual"}, {}),
            ("resume-host", {}, {"resume_host": "claude"}),
            ("pause-target-host", {"target_host": "codex"}, {}),
        )
        for label, checkpoint_values, task_values in pause_cases:
            with self.subTest(kind="pause", case=label):
                state_value = copy.deepcopy(paused)
                task = state_value["tasks"][0]
                task["checkpoints"][-1].update(checkpoint_values)
                task.update(task_values)
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

        state_path.write_text(json.dumps(paused))
        resumed, _ = self._adt("resume", "--host", "codex")
        self._adt(
            "handoff",
            "--host",
            "codex",
            "--lease",
            self._lease(resumed),
            "--to",
            "claude",
        )
        state_path, handed_off = self._stored_state()
        handoff_cases = (
            ("terminal-kind", {"kind": "manual"}, {}),
            ("missing-target-host", {"target_host": None}, {}),
            ("resume-host", {}, {"resume_host": "codex"}),
            ("handoff-previous-digest", {"previous_digest": "sha256:" + "0" * 64}, {}),
            (
                "whitespace-hosts",
                {"target_host": " \t"},
                {"resume_host": " \t"},
            ),
            (
                "unnormalized-hosts",
                {"target_host": " claude "},
                {"resume_host": " claude "},
            ),
        )
        for label, checkpoint_values, task_values in handoff_cases:
            with self.subTest(kind="handoff", case=label):
                state_value = copy.deepcopy(handed_off)
                task = state_value["tasks"][0]
                task["checkpoints"][-1].update(checkpoint_values)
                task.update(task_values)
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_active_resume_accepts_pause_and_handoff_terminal_history(self) -> None:
        started = self._start()
        paused, _ = self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        resumed, _ = self._adt("resume", "--host", "codex")
        status, _ = self._adt("status")
        self.assertEqual("pause", paused["checkpoint"]["kind"])
        self.assertEqual("active", status["task"]["status"])

        handed_off, _ = self._adt(
            "handoff",
            "--host",
            "codex",
            "--lease",
            self._lease(resumed),
            "--to",
            "claude",
        )
        self._adt("resume", "--host", "claude")
        status, _ = self._adt("status")
        self.assertEqual("handoff", handed_off["checkpoint"]["kind"])
        self.assertEqual("active", status["task"]["status"])

    def test_pause_retains_legacy_raw_host_values(self) -> None:
        for host in ("", " \n\t", "  codex  "):
            with self.subTest(host=host):
                started = self._start(host=host)
                paused, _ = self._adt(
                    "pause",
                    "--host",
                    host,
                    "--lease",
                    self._lease(started),
                )
                status, _ = self._adt("status")
                self.assertEqual(host, paused["checkpoint"]["host"])
                self.assertEqual(host, status["task"]["resume_host"])

                resumed, _ = self._adt("resume", "--host", host)
                self._adt(
                    "complete",
                    "--host",
                    host,
                    "--lease",
                    self._lease(resumed),
                )

    def test_drift_accepted_checkpoint_relations_are_validated(self) -> None:
        started = self._start()
        paused, _ = self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        (self.repo / "app.txt").write_text("drifted while paused\n")
        resumed, _ = self._adt("resume", "--host", "codex", "--accept-drift")
        state_path, baseline = self._stored_state()

        self.assertEqual(3, resumed["revision"])
        self.assertEqual("pause", paused["checkpoint"]["kind"])
        self.assertEqual("drift-accepted", resumed["checkpoint"]["kind"])
        self.assertEqual(
            paused["checkpoint"]["snapshot"]["digest"],
            resumed["checkpoint"]["previous_digest"],
        )
        self._adt("status")

        invalid_states = []
        wrong_digest = copy.deepcopy(baseline)
        wrong_digest["tasks"][0]["checkpoints"][1]["previous_digest"] = (
            "sha256:" + "0" * 64
        )
        invalid_states.append(("predecessor-digest", wrong_digest))

        wrong_predecessor = copy.deepcopy(baseline)
        wrong_predecessor["tasks"][0]["checkpoints"][0]["kind"] = "manual"
        invalid_states.append(("predecessor-kind", wrong_predecessor))

        wrong_host = copy.deepcopy(baseline)
        wrong_host["tasks"][0]["checkpoints"][1]["host"] = "claude"
        invalid_states.append(("resume-host", wrong_host))

        unchanged_drift = copy.deepcopy(baseline)
        task = unchanged_drift["tasks"][0]
        task["checkpoints"][0]["snapshot"] = copy.deepcopy(
            task["checkpoints"][1]["snapshot"]
        )
        task["checkpoints"][1]["previous_digest"] = task["checkpoints"][0]["snapshot"][
            "digest"
        ]
        invalid_states.append(("unchanged-digest", unchanged_drift))

        for label, state_value in invalid_states:
            with self.subTest(relation=label):
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_handoff_drift_acceptance_uses_the_target_host(self) -> None:
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
        (self.repo / "app.txt").write_text("drifted after handoff\n")
        resumed, _ = self._adt("resume", "--host", "claude", "--accept-drift")
        state_path, baseline = self._stored_state()

        self.assertEqual("claude", resumed["checkpoint"]["host"])
        self.assertEqual(
            handed_off["checkpoint"]["snapshot"]["digest"],
            resumed["checkpoint"]["previous_digest"],
        )
        self._adt("status")

        baseline["tasks"][0]["checkpoints"][-1]["host"] = "codex"
        state_path.write_text(json.dumps(baseline))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_drift_accepted_at_index_zero_cannot_wrap_to_trailing_pause(
        self,
    ) -> None:
        started = self._start()
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        (self.repo / "app.txt").write_text("first drift\n")
        resumed, _ = self._adt("resume", "--host", "codex", "--accept-drift")
        (self.repo / "app.txt").write_text("second drift\n")
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(resumed),
        )
        state_path, state_value = self._stored_state()
        task = state_value["tasks"][0]
        drift, trailing_pause = task["checkpoints"][1:]
        drift["sequence"] = 1
        trailing_pause["sequence"] = 2
        drift["previous_digest"] = trailing_pause["snapshot"]["digest"]
        task["checkpoints"] = [drift, trailing_pause]
        state_path.write_text(json.dumps(state_value))

        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_revision_lower_bound_includes_unretained_no_drift_resumes(self) -> None:
        started = self._start()
        self._adt(
            "pause",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
        )
        resumed, _ = self._adt("resume", "--host", "codex")
        state_path, active = self._stored_state()

        self.assertEqual(3, active["revision"])
        self._adt("status")
        rolled_back = copy.deepcopy(active)
        rolled_back["revision"] = 2
        state_path.write_text(json.dumps(rolled_back))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

        state_path.write_text(json.dumps(active))
        completed, _ = self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(resumed),
        )
        state_path, terminal = self._stored_state()
        self.assertEqual(4, completed["revision"])
        self._adt("status")

        rolled_back = copy.deepcopy(terminal)
        rolled_back["revision"] = 3
        state_path.write_text(json.dumps(rolled_back))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

        future_revision = copy.deepcopy(terminal)
        future_revision["revision"] = 99
        state_path.write_text(json.dumps(future_revision))
        status, _ = self._adt("status")
        self.assertEqual(99, status["revision"])

    def test_revision_lower_bound_includes_handoff_no_drift_resume(self) -> None:
        started = self._start()
        self._adt(
            "handoff",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            "--to",
            "claude",
        )
        self._adt("resume", "--host", "claude")
        state_path, active = self._stored_state()

        self.assertEqual(3, active["revision"])
        rolled_back = copy.deepcopy(active)
        rolled_back["revision"] = 2
        state_path.write_text(json.dumps(rolled_back))
        error, _ = self._adt("status", expected_code=4)
        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_state_relations_and_snapshot_rules_have_isolated_mutations(self) -> None:
        first = self._start()
        self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(first),
        )
        (self.repo / "rename-me.txt").write_text("rename this file\n")
        self._git("add", "rename-me.txt")
        self._git("commit", "-qm", "add rename candidate")
        second = self._start()
        (self.repo / "app.txt").write_text("staged current task change\n")
        self._git("add", "app.txt")
        self._git("mv", "rename-me.txt", "renamed.txt")
        self._adt(
            "checkpoint",
            "--host",
            "codex",
            "--lease",
            self._lease(second),
        )
        state_path, baseline = self._stored_state()

        def current_snapshots(state_value):
            task = state_value["tasks"][-1]
            return (task["snapshot"], task["checkpoints"][-1]["snapshot"])

        def current_entry(snapshot):
            return next(
                entry
                for entry in snapshot["changes"]["entries"]
                if entry["path"] == "app.txt"
            )

        def rename_entry(snapshot):
            return next(
                entry
                for entry in snapshot["changes"]["entries"]
                if "R" in entry["status"]
            )

        cases = []

        float_revision = copy.deepcopy(baseline)
        float_revision["revision"] = float(float_revision["revision"])
        cases.append(("revision-float", float_revision))

        wrong_current = copy.deepcopy(baseline)
        wrong_current["current_task_id"] = wrong_current["tasks"][0]["id"]
        cases.append(("current-is-last", wrong_current))

        open_history = copy.deepcopy(baseline)
        prior_id = open_history["tasks"][0]["id"]
        open_history["tasks"][0] = copy.deepcopy(open_history["tasks"][-1])
        open_history["tasks"][0]["id"] = prior_id
        cases.append(("previous-task-completed", open_history))

        duplicate_ids = copy.deepcopy(baseline)
        duplicate_ids["tasks"][0]["id"] = duplicate_ids["tasks"][-1]["id"]
        cases.append(("unique-task-ids", duplicate_ids))

        for label, field, invalid in (
            ("fingerprint-mode", "mode", "0o"),
            ("fingerprint-sha256", "sha256", "0" * 63),
            ("fingerprint-kind", "kind", "unknown"),
            ("fingerprint-size-negative", "size", -1),
            ("fingerprint-size-float", "size", 1.0),
        ):
            state_value = copy.deepcopy(baseline)
            for snapshot in current_snapshots(state_value):
                current_entry(snapshot)["worktree"][field] = invalid
            cases.append((label, state_value))

        for label, field, invalid in (
            ("snapshot-algorithm", "algorithm", "sha512"),
            ("snapshot-digest", "digest", "sha256:" + "0" * 63),
            ("snapshot-head", "head", "g" * 40),
        ):
            state_value = copy.deepcopy(baseline)
            for snapshot in current_snapshots(state_value):
                snapshot[field] = invalid
            cases.append((label, state_value))

        for label, field, invalid in (
            ("snapshot-total-float", "total", 2.0),
            ("snapshot-truncated-float", "truncated", 0.0),
        ):
            state_value = copy.deepcopy(baseline)
            for snapshot in current_snapshots(state_value):
                snapshot["changes"][field] = invalid
            cases.append((label, state_value))

        negative_truncation = copy.deepcopy(baseline)
        for snapshot in current_snapshots(negative_truncation):
            changes = snapshot["changes"]
            changes["truncated"] = -1
            changes["total"] = len(changes["entries"]) - 1
        cases.append(("snapshot-truncated-negative", negative_truncation))

        invalid_path = copy.deepcopy(baseline)
        for snapshot in current_snapshots(invalid_path):
            current_entry(snapshot)["path"] = ""
        cases.append(("change-path", invalid_path))

        incomplete_original = copy.deepcopy(baseline)
        for snapshot in current_snapshots(incomplete_original):
            del rename_entry(snapshot)["original_index"]
        cases.append(("original-field-symmetry", incomplete_original))

        invalid_index_mode = copy.deepcopy(baseline)
        for snapshot in current_snapshots(invalid_index_mode):
            index_item = current_entry(snapshot)["index"][0]
            _, object_id, stage = index_item.split(" ")
            current_entry(snapshot)["index"][0] = f"999999 {object_id} {stage}"
        cases.append(("index-mode", invalid_index_mode))

        invalid_object_id = copy.deepcopy(baseline)
        for snapshot in current_snapshots(invalid_object_id):
            index_item = current_entry(snapshot)["index"][0]
            mode, object_id, stage = index_item.split(" ")
            current_entry(snapshot)["index"][0] = (
                f"{mode} {'g' * len(object_id)} {stage}"
            )
        cases.append(("index-object-id", invalid_object_id))

        dirty_mismatch = copy.deepcopy(baseline)
        for snapshot in current_snapshots(dirty_mismatch):
            snapshot["dirty"] = False
        cases.append(("dirty-total-coherence", dirty_mismatch))

        total_mismatch = copy.deepcopy(baseline)
        for snapshot in current_snapshots(total_mismatch):
            snapshot["changes"]["total"] += 1
        cases.append(("total-entry-truncation-coherence", total_mismatch))

        invalid_stage = copy.deepcopy(baseline)
        for snapshot in current_snapshots(invalid_stage):
            index_item = current_entry(snapshot)["index"][0]
            current_entry(snapshot)["index"][0] = index_item[:-1] + "4"
        cases.append(("index-stage", invalid_stage))

        for label, state_value in cases:
            with self.subTest(rule=label):
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("status", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_state_load_accepts_only_legal_porcelain_v1_status_pairs(self) -> None:
        (self.repo / "app.txt").write_text("dirty before task start\n")
        self._start()
        state_path, baseline = self._stored_state()
        legal_statuses = (
            " M",
            "M ",
            " T",
            "T ",
            " A",
            "A ",
            " D",
            "D ",
            "DR",
            "DC",
            "DA",
            " R",
            "R ",
            " C",
            "C ",
            "DD",
            "AU",
            "UD",
            "UA",
            "DU",
            "AA",
            "UU",
            "??",
            "!!",
        )
        for status in legal_statuses:
            with self.subTest(legal=status):
                state_value = copy.deepcopy(baseline)
                entry = state_value["tasks"][0]["snapshot"]["changes"]["entries"][0]
                entry["status"] = status
                if "R" in status or "C" in status:
                    entry["original_path"] = "old-app.txt"
                    entry["original_index"] = copy.deepcopy(entry["index"])
                    entry["original_worktree"] = copy.deepcopy(entry["worktree"])
                state_path.write_text(json.dumps(state_value))
                listed, _ = self._adt("list")
                self.assertEqual(1, len(listed["tasks"]))

        for status in (
            "  ",
            "MA",
            "MR",
            "MC",
            "U ",
            "DM",
            "DT",
            "D?",
            "D!",
            "!?",
        ):
            with self.subTest(invalid=status):
                state_value = copy.deepcopy(baseline)
                state_value["tasks"][0]["snapshot"]["changes"]["entries"][0][
                    "status"
                ] = status
                state_path.write_text(json.dumps(state_value))
                error, _ = self._adt("list", expected_code=4)
                self.assertEqual("state_corrupt", error["error"]["code"])

    def test_real_worktree_rename_from_deleted_index_row_round_trips(
        self,
    ) -> None:
        (self.repo / "a.txt").write_text("same content\n")
        (self.repo / "b.txt").write_text("old destination\n")
        self._git("add", "a.txt", "b.txt")
        self._git("commit", "-qm", "add rename pair")
        self._git("rm", "--cached", "b.txt")
        (self.repo / "b.txt").write_text((self.repo / "a.txt").read_text())
        self._git("add", "-N", "b.txt")
        (self.repo / "a.txt").unlink()
        porcelain = self._git("status", "--porcelain=v1", "-z")
        self.assertEqual("DR b.txt\0a.txt\0", porcelain.stdout)

        self._assert_persisted_status_round_trips(
            "DR",
            "b.txt",
            expected_original_path="a.txt",
        )

    def test_real_intent_to_add_from_deleted_index_row_round_trips(self) -> None:
        destination = self.repo / "b.txt"
        destination.write_text("tracked destination\n")
        self._git("add", "b.txt")
        self._git("commit", "-qm", "add destination")
        self._git("rm", "--cached", "b.txt")
        destination.unlink()
        destination.write_text("tracked destination\n")
        self._git("add", "-N", "b.txt")
        porcelain = self._git("status", "--porcelain=v1", "-z")
        self.assertEqual("DA b.txt\0", porcelain.stdout)

        self._assert_persisted_status_round_trips("DA", "b.txt")

    def test_real_worktree_copy_from_deleted_index_row_round_trips(self) -> None:
        self._git("config", "status.renames", "copies")
        source = self.repo / "source.txt"
        destination = self.repo / "destination.txt"
        source.write_text("committed source\n")
        destination.write_text("old destination\n")
        self._git("add", "source.txt", "destination.txt")
        self._git("commit", "-qm", "add copy candidates")
        committed_source = source.read_text()
        self._git("rm", "--cached", "destination.txt")
        destination.write_text(committed_source)
        self._git("add", "-N", "destination.txt")
        source.write_text("modified source\n")
        porcelain = self._git("status", "--porcelain=v1", "-z")
        self.assertEqual(
            "DC destination.txt\0source.txt\0 M source.txt\0",
            porcelain.stdout,
        )

        self._assert_persisted_status_round_trips(
            "DC",
            "destination.txt",
            expected_original_path="source.txt",
        )

    def test_state_load_validates_non_current_history(self) -> None:
        first = self._start()
        self._adt(
            "complete",
            "--host",
            "codex",
            "--lease",
            self._lease(first),
        )
        self._start(host="claude")
        state_path, state_value = self._stored_state()
        state_value["tasks"][0]["snapshot"] = []
        state_path.write_text(json.dumps(state_value))

        error, _ = self._adt("list", expected_code=4)

        self.assertEqual("state_corrupt", error["error"]["code"])

    def test_empty_schema_v2_state_requires_a_null_current_task(self) -> None:
        self._start()
        state_path, state_value = self._stored_state()
        state_value["revision"] = 0
        state_value["tasks"] = []
        state_value["current_task_id"] = None
        state_path.write_text(json.dumps(state_value))

        listed, _ = self._adt("list")

        self.assertEqual([], listed["tasks"])
        self.assertIsNone(listed["current_task_id"])

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

    def test_state_save_fsyncs_closed_temp_before_replace_and_directory_after(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="durable-save-order",
        )
        store = runtime.StateStore(workspace)
        temporary_name = str(store.directory / "state.owned.tmp")
        events: list[tuple[object, ...]] = []

        class TemporaryFile:
            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                events.append(("close-temp",))

            def write(self, _payload: bytes) -> None:
                events.append(("write",))

            def flush(self) -> None:
                events.append(("flush",))

            def fileno(self) -> int:
                return 31

        def record(event: str, *values: object, result: object = None):
            events.append((event, *values))
            return result

        with (
            mock.patch.object(
                runtime.tempfile,
                "mkstemp",
                side_effect=lambda **_kwargs: record(
                    "mkstemp", result=(31, temporary_name)
                ),
            ),
            mock.patch.object(
                runtime.os,
                "fchmod",
                side_effect=lambda descriptor, mode: record(
                    "fchmod", descriptor, mode
                ),
            ),
            mock.patch.object(
                runtime.os,
                "fdopen",
                side_effect=lambda descriptor, mode: record(
                    "fdopen", descriptor, mode, result=TemporaryFile()
                ),
            ),
            mock.patch.object(
                runtime.os,
                "fsync",
                side_effect=lambda descriptor: record("fsync", descriptor),
            ),
            mock.patch.object(
                runtime.os,
                "replace",
                side_effect=lambda source, destination: record(
                    "replace", source, destination
                ),
            ),
            mock.patch.object(
                runtime.os,
                "open",
                side_effect=lambda path, flags: record(
                    "open-dir", path, flags, result=41
                ),
            ),
            mock.patch.object(
                runtime.os,
                "close",
                side_effect=lambda descriptor: record("close-dir", descriptor),
            ),
            mock.patch.object(runtime.os, "unlink"),
        ):
            store.save({"schema_version": runtime.SCHEMA_VERSION})

        self.assertEqual(
            [
                ("mkstemp",),
                ("fchmod", 31, 0o600),
                ("fdopen", 31, "wb"),
                ("write",),
                ("flush",),
                ("fsync", 31),
                ("close-temp",),
                ("replace", temporary_name, store.state_path),
                ("open-dir", store.directory, runtime.os.O_RDONLY),
                ("fsync", 41),
                ("close-dir", 41),
            ],
            events,
        )

    def test_state_save_cleans_temp_when_temp_fsync_fails(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="temp-fsync-failure",
        )
        store = runtime.StateStore(workspace)
        store.directory.mkdir(parents=True)
        original = b"existing state\n"
        store.state_path.write_bytes(original)

        with (
            mock.patch.object(
                runtime.os,
                "fsync",
                side_effect=OSError("temp fsync failed"),
            ),
            mock.patch.object(runtime.os, "replace") as replace,
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.save({"schema_version": runtime.SCHEMA_VERSION})

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(4, raised.exception.exit_code)
        replace.assert_not_called()
        self.assertEqual(original, store.state_path.read_bytes())
        self.assertEqual([], list(store.directory.glob("state.*.tmp")))

    def test_state_save_fchmod_failure_cleans_owned_temp(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="fchmod-failure",
        )
        store = runtime.StateStore(workspace)
        store.directory.mkdir(parents=True)
        original = b"existing state\n"
        store.state_path.write_bytes(original)

        with (
            mock.patch.object(
                runtime.os,
                "fchmod",
                side_effect=OSError("fchmod failed"),
            ),
            mock.patch.object(runtime.os, "replace") as replace,
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.save({"schema_version": runtime.SCHEMA_VERSION})

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(4, raised.exception.exit_code)
        replace.assert_not_called()
        self.assertEqual(original, store.state_path.read_bytes())
        self.assertEqual([], list(store.directory.glob("state.*.tmp")))

    def test_state_save_write_flush_and_temp_close_failures_clean_temp(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="temp-file-failure",
        )
        store = runtime.StateStore(workspace)
        temporary_name = str(store.directory / "state.owned.tmp")

        class TemporaryFile:
            def __init__(self, failed_operation: str) -> None:
                self.failed_operation = failed_operation
                self.close_attempted = False

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                self.close_attempted = True
                if self.failed_operation == "close":
                    raise OSError("temp close failed")

            def write(self, _payload: bytes) -> None:
                if self.failed_operation == "write":
                    raise OSError("write failed")

            def flush(self) -> None:
                if self.failed_operation == "flush":
                    raise OSError("flush failed")

            def fileno(self) -> int:
                return 31

        for operation in ("write", "flush", "close"):
            with self.subTest(operation=operation):
                temporary_file = TemporaryFile(operation)
                with (
                    mock.patch.object(
                        runtime.tempfile,
                        "mkstemp",
                        return_value=(31, temporary_name),
                    ),
                    mock.patch.object(runtime.os, "fchmod"),
                    mock.patch.object(
                        runtime.os,
                        "fdopen",
                        return_value=temporary_file,
                    ),
                    mock.patch.object(runtime.os, "fsync"),
                    mock.patch.object(runtime.os, "replace") as replace,
                    mock.patch.object(runtime.os, "unlink") as unlink,
                ):
                    with self.assertRaises(runtime.CliError) as raised:
                        store.save({"schema_version": runtime.SCHEMA_VERSION})

                self.assertEqual("state_unavailable", raised.exception.code)
                self.assertEqual(4, raised.exception.exit_code)
                self.assertTrue(temporary_file.close_attempted)
                replace.assert_not_called()
                unlink.assert_called_once_with(temporary_name)

    def test_state_save_reports_directory_fsync_failure_after_replace_lands(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="directory-fsync-failure",
        )
        store = runtime.StateStore(workspace)
        store.directory.mkdir(parents=True)
        original_fsync = runtime.os.fsync
        fsync_calls = 0

        def fail_directory_fsync(descriptor: int) -> None:
            nonlocal fsync_calls
            fsync_calls += 1
            if fsync_calls == 2:
                raise OSError("directory fsync failed")
            original_fsync(descriptor)

        replacement = {"schema_version": runtime.SCHEMA_VERSION, "landed": True}
        with mock.patch.object(
            runtime.os,
            "fsync",
            side_effect=fail_directory_fsync,
        ):
            with self.assertRaises(runtime.CliError) as raised:
                store.save(replacement)

        self.assertEqual("state_unavailable", raised.exception.code)
        self.assertEqual(4, raised.exception.exit_code)
        self.assertEqual(replacement, json.loads(store.state_path.read_text()))
        self.assertEqual([], list(store.directory.glob("state.*.tmp")))

    def test_state_save_directory_open_and_close_failures_report_landed_state(self) -> None:
        runtime = self._load_runtime()
        workspace = runtime.GitWorkspace(
            root=self.repo,
            common_dir=self.repo / ".git",
            workspace_id="directory-handle-failure",
        )
        store = runtime.StateStore(workspace)
        store.directory.mkdir(parents=True)
        original_open = runtime.os.open
        original_close = runtime.os.close

        for operation in ("open", "close"):
            with self.subTest(operation=operation):
                directory_descriptor = None

                def controlled_open(path, flags, *args, **kwargs):
                    nonlocal directory_descriptor
                    if Path(path) == store.directory and operation == "open":
                        raise OSError("directory open failed")
                    descriptor = original_open(path, flags, *args, **kwargs)
                    if Path(path) == store.directory:
                        directory_descriptor = descriptor
                    return descriptor

                def controlled_close(descriptor):
                    if descriptor == directory_descriptor and operation == "close":
                        original_close(descriptor)
                        raise OSError("directory close failed")
                    return original_close(descriptor)

                replacement = {
                    "schema_version": runtime.SCHEMA_VERSION,
                    "operation": operation,
                }
                with (
                    mock.patch.object(runtime.os, "open", side_effect=controlled_open),
                    mock.patch.object(
                        runtime.os,
                        "close",
                        side_effect=controlled_close,
                    ),
                ):
                    with self.assertRaises(runtime.CliError) as raised:
                        store.save(replacement)

                self.assertEqual("state_unavailable", raised.exception.code)
                self.assertEqual(4, raised.exception.exit_code)
                self.assertEqual(replacement, json.loads(store.state_path.read_text()))
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

    def test_handoff_rejects_blank_target_without_mutating_state(self) -> None:
        started = self._start()
        state_path, state_value = self._stored_state()
        state_before = state_path.read_bytes()

        for target in ("", " \n\t"):
            with self.subTest(target=target):
                error, _ = self._adt(
                    "handoff",
                    "--host",
                    "codex",
                    "--lease",
                    self._lease(started),
                    "--to",
                    target,
                    expected_code=3,
                )
                self.assertEqual("target_host_invalid", error["error"]["code"])
                self.assertEqual(state_before, state_path.read_bytes())
                self.assertEqual(
                    state_value["revision"], self._stored_state()[1]["revision"]
                )

        handed_off, _ = self._adt(
            "handoff",
            "--host",
            "codex",
            "--lease",
            self._lease(started),
            "--to",
            "  claude  ",
        )
        self.assertEqual("claude", handed_off["task"]["resume_host"])
        self.assertEqual("claude", handed_off["checkpoint"]["target_host"])

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
