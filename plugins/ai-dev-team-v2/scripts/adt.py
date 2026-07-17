#!/usr/bin/env python3
"""Durable, provider-neutral task checkpoints for the AI Dev Team MVP."""

from __future__ import annotations

import argparse
import copy
import contextlib
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, NoReturn, Sequence


SCHEMA_VERSION = 2
SNAPSHOT_FORMAT_VERSION = 2
STATE_NAMESPACE = "ai-dev-team"
OPEN_STATUSES = frozenset({"active", "paused"})
REVIEW_HOLD_EXIT_CODE = 5
STATE_UNAVAILABLE_MESSAGE = (
    "ADT needs read/write access to its state directory under the common Git "
    "directory."
)
TASK_KINDS = frozenset({"develop", "review"})
TASK_PROFILES = frozenset({"economy", "balanced", "critical", "manual"})
TASK_STATUSES = frozenset({"active", "paused", "completed"})
CHECKPOINT_KINDS = frozenset(
    {"manual", "pause", "handoff", "drift-accepted", "complete"}
)
LOWER_HEX = frozenset("0123456789abcdef")
OCTAL_DIGITS = frozenset("01234567")
FINGERPRINT_KINDS = frozenset({"file", "symlink", "special"})
UNMERGED_STATUSES = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})
INDEX_STATUSES = frozenset({"M", "T", "A", "R", "C"})
WORKTREE_STATUSES = frozenset({"M", "T", "D", "R", "C"})
INDEXED_WORKTREE_STATUSES = frozenset({" ", "M", "T", "D"})


class CliError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        exit_code: int = 3,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.exit_code = exit_code


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliError("usage", message, exit_code=2)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized_nonblank(value: Any) -> bool:
    return _nonblank(value) and value == value.strip()


def _string(value: Any) -> bool:
    return isinstance(value, str)


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _choice(value: Any, choices: frozenset[str]) -> bool:
    return isinstance(value, str) and value in choices


def _fixed_hex(value: Any, *, prefix: str = "", length: int) -> bool:
    if not isinstance(value, str) or not value.startswith(prefix):
        return False
    suffix = value[len(prefix) :]
    return len(suffix) == length and all(
        character in LOWER_HEX for character in suffix
    )


def _valid_index_item(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split(" ")
    if len(parts) != 3:
        return False
    mode, object_id, stage = parts
    return (
        len(mode) == 6
        and all(character in OCTAL_DIGITS for character in mode)
        and (
            _fixed_hex(object_id, length=40)
            or _fixed_hex(object_id, length=64)
        )
        and stage in {"0", "1", "2", "3"}
    )


def _valid_index(value: Any) -> bool:
    return isinstance(value, list) and all(_valid_index_item(item) for item in value)


def _valid_fingerprint(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, dict):
        return False
    mode = value.get("mode")
    size = value.get("size")
    return (
        isinstance(mode, str)
        and mode.startswith("0o")
        and len(mode) > 2
        and all(character in OCTAL_DIGITS for character in mode[2:])
        and _integer(size)
        and size >= 0
        and _choice(value.get("kind"), FINGERPRINT_KINDS)
        and _fixed_hex(value.get("sha256"), length=64)
    )


def _valid_porcelain_v1_status(status: Any) -> bool:
    """Validate XY pairs from the documented porcelain-v1 short-status table."""
    if not isinstance(status, str) or len(status) != 2:
        return False
    if status in UNMERGED_STATUSES or status in {"??", "!!"}:
        return True
    index_status, worktree_status = status
    if index_status == " ":
        return worktree_status in WORKTREE_STATUSES | {"A"}
    if index_status == "D":
        return worktree_status in {" ", "A", "R", "C"}
    return (
        index_status in INDEX_STATUSES
        and worktree_status in INDEXED_WORKTREE_STATUSES
    )


def _valid_change_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if not {"status", "path", "index", "worktree"}.issubset(entry):
        return False
    status = entry.get("status")
    if (
        not _valid_porcelain_v1_status(status)
        or not isinstance(entry.get("path"), str)
        or not entry["path"]
        or not _valid_index(entry.get("index"))
        or not _valid_fingerprint(entry.get("worktree"))
    ):
        return False
    original_fields = {"original_path", "original_index", "original_worktree"}
    expects_original = "R" in status or "C" in status
    present_original_fields = original_fields.intersection(entry)
    if (
        expects_original and present_original_fields != original_fields
    ) or (not expects_original and present_original_fields):
        return False
    return not expects_original or (
        isinstance(entry.get("original_path"), str)
        and bool(entry["original_path"])
        and _valid_index(entry.get("original_index"))
        and _valid_fingerprint(entry.get("original_worktree"))
    )


def _valid_snapshot(snapshot: Any) -> bool:
    if not isinstance(snapshot, dict):
        return False
    head = snapshot.get("head")
    changes = snapshot.get("changes")
    if not isinstance(changes, dict):
        return False
    total = changes.get("total")
    entries = changes.get("entries")
    truncated = changes.get("truncated")
    return (
        "head" in snapshot
        and _integer(snapshot.get("format_version"))
        and snapshot["format_version"] == SNAPSHOT_FORMAT_VERSION
        and snapshot.get("algorithm") == "sha256"
        and _fixed_hex(snapshot.get("digest"), prefix="sha256:", length=64)
        and (
            head is None
            or _fixed_hex(head, length=40)
            or _fixed_hex(head, length=64)
        )
        and isinstance(snapshot.get("dirty"), bool)
        and _integer(total)
        and total >= 0
        and isinstance(entries, list)
        and all(_valid_change_entry(entry) for entry in entries)
        and _integer(truncated)
        and truncated >= 0
        and total == len(entries) + truncated
        and snapshot["dirty"] == bool(total)
    )


def _fingerprint_contract(value: dict[str, Any] | None) -> tuple[Any, ...] | None:
    if value is None:
        return None
    return tuple(value[field] for field in ("mode", "size", "kind", "sha256"))


def _change_entry_contract(entry: dict[str, Any]) -> tuple[Any, ...]:
    return (
        entry["status"],
        entry["path"],
        tuple(entry["index"]),
        _fingerprint_contract(entry["worktree"]),
        entry.get("original_path"),
        tuple(entry["original_index"]) if "original_index" in entry else None,
        _fingerprint_contract(entry.get("original_worktree")),
    )


def _snapshot_contract(snapshot: dict[str, Any]) -> tuple[Any, ...]:
    changes = snapshot["changes"]
    return (
        snapshot["format_version"],
        snapshot["algorithm"],
        snapshot["digest"],
        snapshot["head"],
        snapshot["dirty"],
        changes["total"],
        tuple(_change_entry_contract(entry) for entry in changes["entries"]),
        changes["truncated"],
    )


def _valid_lease(lease: Any) -> bool:
    return (
        isinstance(lease, dict)
        and _fixed_hex(lease.get("id"), prefix="lease_", length=32)
        and _string(lease.get("host"))
        and _string(lease.get("acquired_at"))
    )


def _valid_optional_string(value: dict[str, Any], key: str) -> bool:
    return key not in value or _string(value[key])


def _valid_checkpoint_kind_fields(checkpoint: dict[str, Any]) -> bool:
    kind = checkpoint["kind"]
    has_target = "target_host" in checkpoint
    has_previous = "previous_digest" in checkpoint
    if kind == "handoff":
        return (
            has_target
            and _normalized_nonblank(checkpoint["target_host"])
            and not has_previous
        )
    if kind == "drift-accepted":
        return (
            not has_target
            and has_previous
            and _fixed_hex(
                checkpoint["previous_digest"],
                prefix="sha256:",
                length=64,
            )
        )
    return not has_target and not has_previous


def _valid_checkpoints(checkpoints: Any) -> bool:
    if not isinstance(checkpoints, list):
        return False
    for expected_sequence, checkpoint in enumerate(checkpoints, start=1):
        if not isinstance(checkpoint, dict):
            return False
        sequence = checkpoint.get("sequence")
        if (
            not _fixed_hex(checkpoint.get("id"), prefix="checkpoint_", length=32)
            or not _integer(sequence)
            or sequence != expected_sequence
            or not _choice(checkpoint.get("kind"), CHECKPOINT_KINDS)
            or not _string(checkpoint.get("host"))
            or not _string(checkpoint.get("created_at"))
            or not _valid_snapshot(checkpoint.get("snapshot"))
            or not _valid_optional_string(checkpoint, "note")
            or not _valid_checkpoint_kind_fields(checkpoint)
        ):
            return False
    return True


def _valid_takeovers(takeovers: Any) -> bool:
    if not isinstance(takeovers, list):
        return False
    return all(
        isinstance(takeover, dict)
        and _string(takeover.get("host"))
        and _string(takeover.get("created_at"))
        and _string(takeover.get("reason"))
        for takeover in takeovers
    )


def _valid_task(task: Any) -> bool:
    if not isinstance(task, dict):
        return False
    required_fields = {
        "id",
        "kind",
        "profile",
        "goal",
        "status",
        "lease",
        "resume_host",
        "snapshot",
        "checkpoints",
        "created_at",
        "updated_at",
    }
    if not required_fields.issubset(task):
        return False
    status = task.get("status")
    lease = task.get("lease")
    resume_host = task.get("resume_host")
    checkpoints = task.get("checkpoints")
    if status == "active":
        lifecycle_valid = _valid_lease(lease) and resume_host is None
    elif status == "paused":
        lifecycle_valid = lease is None and _string(resume_host)
    elif status == "completed":
        lifecycle_valid = (
            lease is None
            and resume_host is None
            and _string(task.get("completed_at"))
        )
    else:
        lifecycle_valid = False
    shape_valid = (
        _fixed_hex(task.get("id"), prefix="task_", length=32)
        and _choice(task.get("kind"), TASK_KINDS)
        and _choice(task.get("profile"), TASK_PROFILES)
        and _nonblank(task.get("goal"))
        and _choice(status, TASK_STATUSES)
        and lifecycle_valid
        and _valid_snapshot(task.get("snapshot"))
        and _valid_checkpoints(checkpoints)
        and _valid_takeovers(task.get("takeovers", []))
        and _string(task.get("created_at"))
        and _string(task.get("updated_at"))
        and _valid_optional_string(task, "completed_at")
        and _valid_optional_string(task, "summary")
    )
    if not shape_valid:
        return False
    if checkpoints and _snapshot_contract(task["snapshot"]) != _snapshot_contract(
        checkpoints[-1]["snapshot"]
    ):
        return False
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint["kind"] != "drift-accepted":
            continue
        if index == 0:
            return False
        predecessor = checkpoints[index - 1]
        if predecessor["kind"] not in {"pause", "handoff"}:
            return False
        expected_host = (
            predecessor["host"]
            if predecessor["kind"] == "pause"
            else predecessor["target_host"]
        )
        if (
            checkpoint["host"] != expected_host
            or checkpoint["previous_digest"] != predecessor["snapshot"]["digest"]
            or checkpoint["snapshot"]["digest"] == predecessor["snapshot"]["digest"]
        ):
            return False
    if status == "paused":
        if not checkpoints or checkpoints[-1]["kind"] not in {"pause", "handoff"}:
            return False
        terminal = checkpoints[-1]
        expected_resume_host = (
            terminal["host"]
            if terminal["kind"] == "pause"
            else terminal["target_host"]
        )
        if task["resume_host"] != expected_resume_host:
            return False
    completion_checkpoints = [
        checkpoint for checkpoint in checkpoints if checkpoint["kind"] == "complete"
    ]
    if status != "completed":
        return (
            "completed_at" not in task
            and "summary" not in task
            and not completion_checkpoints
        )
    if len(completion_checkpoints) != 1 or checkpoints[-1]["kind"] != "complete":
        return False
    terminal = checkpoints[-1]
    if task["completed_at"] != task["updated_at"] or task["completed_at"] != terminal[
        "created_at"
    ]:
        return False
    has_summary = "summary" in task
    has_terminal_note = "note" in terminal
    return has_summary == has_terminal_note and (
        not has_summary or task["summary"] == terminal["note"]
    )


def _inferred_resume_count(task: dict[str, Any]) -> int:
    checkpoints = task["checkpoints"]
    count = 0
    for index, checkpoint in enumerate(checkpoints):
        if checkpoint["kind"] not in {"pause", "handoff"}:
            continue
        has_successor = index + 1 < len(checkpoints)
        was_resumed = has_successor or task["status"] != "paused"
        successor_is_drift = (
            has_successor and checkpoints[index + 1]["kind"] == "drift-accepted"
        )
        if was_resumed and not successor_is_drift:
            count += 1
    return count


def _validate_state(value: dict[str, Any], workspace_id: str) -> None:
    workspace_value = value.get("workspace")
    if (
        not isinstance(workspace_value, dict)
        or not _fixed_hex(workspace_value.get("id"), length=24)
        or not _string(workspace_value.get("root"))
    ):
        raise CliError(
            "state_corrupt",
            "The workspace state has no valid workspace identity.",
            exit_code=4,
        )
    if workspace_value["id"] != workspace_id:
        raise CliError(
            "workspace_mismatch",
            "The stored state belongs to a different workspace.",
            exit_code=4,
        )

    tasks = value.get("tasks")
    revision = value.get("revision")
    current_id = value.get("current_task_id")
    if (
        not isinstance(tasks, list)
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 0
        or "current_task_id" not in value
        or not _string(value.get("created_at"))
        or not _string(value.get("updated_at"))
    ):
        raise CliError(
            "state_corrupt",
            "The workspace state has invalid task metadata.",
            exit_code=4,
        )
    if not tasks:
        if current_id is None and revision == 0:
            return
        raise CliError(
            "state_corrupt",
            "The workspace state has no valid current task.",
            exit_code=4,
        )

    if not all(_valid_task(task) for task in tasks):
        raise CliError(
            "state_corrupt",
            "The workspace state has invalid persisted task data.",
            exit_code=4,
        )
    task_ids = [task["id"] for task in tasks]
    minimum_revision = len(tasks) + sum(
        len(task["checkpoints"])
        + len(task.get("takeovers", []))
        + _inferred_resume_count(task)
        for task in tasks
    )
    if (
        len(task_ids) != len(set(task_ids))
        or revision < minimum_revision
        or not _fixed_hex(current_id, prefix="task_", length=32)
        or current_id != task_ids[-1]
        or any(task["status"] != "completed" for task in tasks[:-1])
    ):
        raise CliError(
            "state_corrupt",
            "The workspace state has no valid current task.",
            exit_code=4,
        )


@dataclass(frozen=True)
class GitWorkspace:
    root: Path
    common_dir: Path
    workspace_id: str

    @classmethod
    def discover(cls, start: Path) -> "GitWorkspace":
        requested = start.expanduser().resolve()
        root_text = _git_text(requested, "rev-parse", "--show-toplevel")
        root = Path(root_text).resolve()
        common_text = _git_text(root, "rev-parse", "--git-common-dir")
        common_path = Path(common_text)
        if not common_path.is_absolute():
            common_path = root / common_path
        common_dir = common_path.resolve()
        workspace_id = hashlib.sha256(os.fsencode(root)).hexdigest()[:24]
        return cls(root=root, common_dir=common_dir, workspace_id=workspace_id)

    def description(self) -> dict[str, str]:
        return {"id": self.workspace_id, "root": str(self.root)}


class StateStore:
    def __init__(self, workspace: GitWorkspace) -> None:
        self.workspace = workspace
        self.directory = (
            workspace.common_dir
            / STATE_NAMESPACE
            / "workspaces"
            / workspace.workspace_id
        )
        self.state_path = self.directory / "state.json"
        self.lock_path = self.directory / "state.lock"

    def exists(self) -> bool:
        try:
            self.state_path.stat()
        except FileNotFoundError:
            return False
        except OSError as error:
            raise CliError(
                "state_unavailable",
                STATE_UNAVAILABLE_MESSAGE,
                exit_code=4,
            ) from error
        return True

    @contextlib.contextmanager
    def lock(self, *, shared: bool = False) -> Iterator[None]:
        lock_file = None
        try:
            if not shared:
                self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            lock_file = self.lock_path.open("rb" if shared else "a+b")
            if not shared:
                os.chmod(self.lock_path, 0o600)
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_SH if shared else fcntl.LOCK_EX,
            )
        except OSError as error:
            if lock_file is not None:
                with contextlib.suppress(OSError):
                    lock_file.close()
            raise CliError(
                "state_unavailable",
                STATE_UNAVAILABLE_MESSAGE,
                exit_code=4,
            ) from error
        assert lock_file is not None
        body_failed = False
        try:
            yield
        except BaseException:
            body_failed = True
            raise
        finally:
            cleanup_error = None
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError as error:
                cleanup_error = error
            try:
                lock_file.close()
            except OSError as error:
                if cleanup_error is None:
                    cleanup_error = error
            if cleanup_error is not None and not body_failed:
                raise CliError(
                    "state_unavailable",
                    STATE_UNAVAILABLE_MESSAGE,
                    exit_code=4,
                ) from cleanup_error

    def load(self) -> dict[str, Any] | None:
        if not self.exists():
            return None
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise CliError(
                "state_unavailable",
                STATE_UNAVAILABLE_MESSAGE,
                exit_code=4,
            ) from error
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            RecursionError,
        ) as error:
            raise CliError(
                "state_corrupt",
                "The workspace state cannot be read as valid JSON.",
                exit_code=4,
            ) from error
        schema_version = (
            value.get("schema_version") if isinstance(value, dict) else None
        )
        if (
            not isinstance(value, dict)
            or not _integer(schema_version)
            or schema_version != SCHEMA_VERSION
        ):
            raise CliError(
                "state_version_unsupported",
                "The workspace state schema is not supported by this CLI.",
                details={"supported_schema_version": SCHEMA_VERSION},
                exit_code=4,
            )
        _validate_state(value, self.workspace.workspace_id)
        return value

    def save(self, state_value: dict[str, Any]) -> None:
        encoded = (
            json.dumps(
                state_value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        descriptor = -1
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix="state.", suffix=".tmp", dir=self.directory
            )
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as temporary_file:
                descriptor = -1
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, self.state_path)
            directory_descriptor = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError as error:
            raise CliError(
                "state_unavailable",
                STATE_UNAVAILABLE_MESSAGE,
                exit_code=4,
            ) from error
        finally:
            if descriptor >= 0:
                with contextlib.suppress(OSError):
                    os.close(descriptor)
            if temporary_name is not None:
                with contextlib.suppress(OSError):
                    os.unlink(temporary_name)


def _git_bytes(workspace: Path, *arguments: str, allow_failure: bool = False) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=workspace,
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise CliError(
            "git_unavailable",
            "Git could not be executed.",
            exit_code=4,
        ) from error
    if result.returncode != 0 and not allow_failure:
        raise CliError(
            "not_a_git_workspace",
            "The command must run inside a Git worktree.",
            details={"git_exit_code": result.returncode},
            exit_code=4,
        )
    return result.stdout if result.returncode == 0 else b""


def _git_text(workspace: Path, *arguments: str) -> str:
    raw = _git_bytes(workspace, *arguments)
    try:
        return raw.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise CliError(
            "git_output_invalid",
            "Git returned a path that is not valid UTF-8.",
            exit_code=4,
        ) from error


def _hash_field(digest: Any, label: bytes, value: bytes) -> None:
    digest.update(len(label).to_bytes(4, "big"))
    digest.update(label)
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _hash_untracked_file(digest: Any, workspace: Path, relative_raw: bytes) -> None:
    relative = os.fsdecode(relative_raw)
    candidate = workspace / relative
    try:
        metadata = candidate.lstat()
    except FileNotFoundError as error:
        raise CliError(
            "snapshot_unstable",
            "The worktree changed while its snapshot was captured.",
        ) from error

    _hash_field(digest, b"untracked-path", relative_raw)
    _hash_field(digest, b"untracked-mode", str(stat.S_IFMT(metadata.st_mode)).encode())
    if stat.S_ISLNK(metadata.st_mode):
        _hash_field(digest, b"untracked-symlink", os.fsencode(os.readlink(candidate)))
        return
    if not stat.S_ISREG(metadata.st_mode):
        _hash_field(digest, b"untracked-special", str(metadata.st_size).encode())
        return

    digest.update(b"untracked-content\0")
    try:
        with candidate.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except FileNotFoundError as error:
        raise CliError(
            "snapshot_unstable",
            "The worktree changed while its snapshot was captured.",
        ) from error


def _display_git_path(raw_path: bytes) -> str:
    return raw_path.decode("utf-8", errors="backslashreplace")


def _parse_status_records(
    status_raw: bytes,
) -> list[tuple[str, bytes, bytes | None]]:
    raw_entries = [entry for entry in status_raw.split(b"\0") if entry]
    records: list[tuple[str, bytes, bytes | None]] = []
    index = 0
    while index < len(raw_entries):
        raw_entry = raw_entries[index]
        if len(raw_entry) < 4 or raw_entry[2:3] != b" ":
            raise CliError(
                "git_output_invalid",
                "Git returned an invalid porcelain status record.",
                exit_code=4,
            )
        status = raw_entry[:2].decode("ascii")
        path_raw = raw_entry[3:]
        original_path_raw = None
        if "R" in status or "C" in status:
            index += 1
            if index >= len(raw_entries):
                raise CliError(
                    "git_output_invalid",
                    "Git returned an incomplete rename status record.",
                    exit_code=4,
                )
            original_path_raw = raw_entries[index]
        records.append((status, path_raw, original_path_raw))
        index += 1
    return records


def _index_entries(workspace: Path) -> dict[bytes, list[str]]:
    raw_index = _git_bytes(workspace, "ls-files", "--stage", "-z")
    result: dict[bytes, list[str]] = {}
    for raw_entry in (entry for entry in raw_index.split(b"\0") if entry):
        try:
            metadata, path_raw = raw_entry.split(b"\t", 1)
            metadata_text = metadata.decode("ascii")
        except (ValueError, UnicodeDecodeError) as error:
            raise CliError(
                "git_output_invalid",
                "Git returned an invalid index record.",
                exit_code=4,
            ) from error
        result.setdefault(path_raw, []).append(metadata_text)
    return result


def _worktree_fingerprint(
    workspace: Path, relative_raw: bytes
) -> dict[str, Any] | None:
    candidate = workspace / os.fsdecode(relative_raw)
    try:
        before = candidate.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise CliError(
            "snapshot_unreadable",
            "A changed worktree path could not be inspected.",
            details={"path": _display_git_path(relative_raw)},
            exit_code=4,
        ) from error

    fingerprint: dict[str, Any] = {
        "mode": oct(stat.S_IFMT(before.st_mode) | stat.S_IMODE(before.st_mode)),
        "size": before.st_size,
    }
    content_digest = hashlib.sha256()
    try:
        if stat.S_ISLNK(before.st_mode):
            fingerprint["kind"] = "symlink"
            content_digest.update(os.fsencode(os.readlink(candidate)))
        elif stat.S_ISREG(before.st_mode):
            fingerprint["kind"] = "file"
            with candidate.open("rb") as source:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    content_digest.update(chunk)
        else:
            fingerprint["kind"] = "special"
            content_digest.update(str(before.st_rdev).encode("ascii"))
        after = candidate.lstat()
    except FileNotFoundError as error:
        raise CliError(
            "snapshot_unstable",
            "The worktree changed while its snapshot was captured.",
        ) from error
    except OSError as error:
        raise CliError(
            "snapshot_unreadable",
            "A changed worktree path could not be fingerprinted.",
            details={"path": _display_git_path(relative_raw)},
            exit_code=4,
        ) from error

    stability_fields = ("st_mode", "st_size", "st_mtime_ns", "st_ino")
    if any(getattr(before, field) != getattr(after, field) for field in stability_fields):
        raise CliError(
            "snapshot_unstable",
            "The worktree changed while its snapshot was captured.",
        )
    fingerprint["sha256"] = content_digest.hexdigest()
    return fingerprint


def _build_change_manifest(workspace: Path, status_raw: bytes) -> dict[str, Any]:
    records = _parse_status_records(status_raw)
    index_by_path = _index_entries(workspace) if records else {}
    entries: list[dict[str, Any]] = []
    for status, path_raw, original_path_raw in records:
        entry: dict[str, Any] = {
            "status": status,
            "path": _display_git_path(path_raw),
            "index": index_by_path.get(path_raw, []),
            "worktree": _worktree_fingerprint(workspace, path_raw),
        }
        if original_path_raw is not None:
            entry["original_path"] = _display_git_path(original_path_raw)
            entry["original_index"] = index_by_path.get(original_path_raw, [])
            entry["original_worktree"] = _worktree_fingerprint(
                workspace, original_path_raw
            )
        entries.append(entry)

    return {
        "total": len(entries),
        "entries": entries,
        "truncated": 0,
    }


def capture_snapshot(workspace: GitWorkspace) -> dict[str, Any]:
    head_raw = _git_bytes(
        workspace.root, "rev-parse", "--verify", "HEAD", allow_failure=True
    ).strip()
    status_raw = _git_bytes(
        workspace.root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    index_diff_raw = _git_bytes(
        workspace.root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--binary",
        "--full-index",
        "--cached",
        "--",
    )
    worktree_diff_raw = _git_bytes(
        workspace.root,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--binary",
        "--full-index",
        "--",
    )
    untracked_raw = _git_bytes(
        workspace.root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )

    digest = hashlib.sha256()
    _hash_field(digest, b"head", head_raw)
    _hash_field(digest, b"status", status_raw)
    _hash_field(digest, b"index-diff", index_diff_raw)
    _hash_field(digest, b"worktree-diff", worktree_diff_raw)
    for relative_raw in sorted(item for item in untracked_raw.split(b"\0") if item):
        _hash_untracked_file(digest, workspace.root, relative_raw)

    return {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "algorithm": "sha256",
        "digest": f"sha256:{digest.hexdigest()}",
        "head": head_raw.decode("ascii") if head_raw else None,
        "dirty": bool(status_raw),
        "changes": _build_change_manifest(workspace.root, status_raw),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _new_state(workspace: GitWorkspace, timestamp: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "workspace": workspace.description(),
        "current_task_id": None,
        "tasks": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _current_task(state_value: dict[str, Any]) -> dict[str, Any]:
    current_id = state_value.get("current_task_id")
    if current_id is None:
        raise CliError("no_task", "No current task exists in this workspace.")
    for task in state_value["tasks"]:
        if isinstance(task, dict) and task.get("id") == current_id:
            return task
    raise CliError("no_task", "No current task exists in this workspace.")


def _require_active_lease(
    task: dict[str, Any], host: str, lease_id: str
) -> None:
    if task.get("status") != "active":
        raise CliError(
            "task_not_active",
            "The current task is not active.",
            details={"status": task.get("status")},
        )
    lease = task.get("lease")
    owner = lease.get("host") if isinstance(lease, dict) else None
    current_lease_id = lease.get("id") if isinstance(lease, dict) else None
    if owner != host or current_lease_id != lease_id:
        raise CliError(
            "lease_conflict",
            "The current execution lease does not match this host and lease ID.",
            details={
                "lease_host": owner,
                "requested_host": host,
                "lease_id_match": current_lease_id == lease_id,
            },
        )


def _new_lease(host: str, timestamp: str) -> dict[str, str]:
    return {
        "id": f"lease_{uuid.uuid4().hex}",
        "host": host,
        "acquired_at": timestamp,
    }


def _append_checkpoint(
    task: dict[str, Any],
    *,
    kind: str,
    host: str,
    timestamp: str,
    snapshot: dict[str, Any],
    note: str | None = None,
    target_host: str | None = None,
    previous_digest: str | None = None,
) -> dict[str, Any]:
    checkpoint: dict[str, Any] = {
        "id": f"checkpoint_{uuid.uuid4().hex}",
        "sequence": len(task["checkpoints"]) + 1,
        "kind": kind,
        "host": host,
        "created_at": timestamp,
        "snapshot": snapshot,
    }
    if note:
        checkpoint["note"] = note
    if target_host:
        checkpoint["target_host"] = target_host
    if previous_digest:
        checkpoint["previous_digest"] = previous_digest
    task["checkpoints"].append(checkpoint)
    task["snapshot"] = snapshot
    task["updated_at"] = timestamp
    return checkpoint


def _commit_state(store: StateStore, state_value: dict[str, Any], timestamp: str) -> None:
    state_value["revision"] += 1
    state_value["updated_at"] = timestamp
    store.save(state_value)


def _success(
    command: str,
    workspace: GitWorkspace,
    **values: Any,
) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "workspace": workspace.description(),
        **values,
    }


def _task_view(task: dict[str, Any], *, include_lease_id: bool) -> dict[str, Any]:
    view = copy.deepcopy(task)
    lease = view.get("lease")
    if isinstance(lease, dict) and not include_lease_id:
        lease.pop("id", None)
    return view


def command_start(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    goal = arguments.goal.strip()
    if not goal:
        raise CliError(
            "goal_invalid",
            "Goal must contain non-whitespace text.",
        )

    with store.lock():
        timestamp = _now()
        state_value = store.load() or _new_state(workspace, timestamp)
        if state_value["current_task_id"] is not None:
            current = _current_task(state_value)
            if current.get("status") in OPEN_STATUSES:
                raise CliError(
                    "task_open",
                    "Complete the current task before starting another one.",
                    details={
                        "task_id": current.get("id"),
                        "status": current.get("status"),
                    },
                )

        snapshot = capture_snapshot(workspace)
        task = {
            "id": f"task_{uuid.uuid4().hex}",
            "kind": arguments.kind,
            "profile": arguments.profile,
            "goal": goal,
            "status": "active",
            "lease": _new_lease(arguments.host, timestamp),
            "resume_host": None,
            "snapshot": snapshot,
            "checkpoints": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        state_value["tasks"].append(task)
        state_value["current_task_id"] = task["id"]
        _commit_state(store, state_value, timestamp)
        return _success("start", workspace, revision=state_value["revision"], task=task)


def _load_existing(store: StateStore) -> dict[str, Any]:
    state_value = store.load()
    if state_value is None:
        raise CliError("no_task", "No task state exists in this workspace.")
    return state_value


def command_status(
    command: str, workspace: GitWorkspace, store: StateStore
) -> dict[str, Any]:
    if not store.exists():
        raise CliError("no_task", "No task state exists in this workspace.")
    with store.lock(shared=True):
        state_value = _load_existing(store)
        task = _current_task(state_value)
        live_snapshot = capture_snapshot(workspace)
        drift = live_snapshot["digest"] != task["snapshot"]["digest"]
        task_view = _task_view(task, include_lease_id=False)
        if command == "status":
            task_view.pop("goal", None)
            task_view.pop("checkpoints", None)
            task_view.pop("summary", None)
        return _success(
            command,
            workspace,
            revision=state_value["revision"],
            task=task_view,
            live_snapshot=live_snapshot,
            drift=drift,
        )


def command_list(workspace: GitWorkspace, store: StateStore) -> dict[str, Any]:
    if not store.exists():
        return _success("list", workspace, revision=0, current_task_id=None, tasks=[])
    with store.lock(shared=True):
        state_value = _load_existing(store)
        summaries = [
            {
                "id": task.get("id"),
                "kind": task.get("kind"),
                "profile": task.get("profile"),
                "goal": task.get("goal"),
                "status": task.get("status"),
                "lease_host": (
                    task["lease"].get("host")
                    if isinstance(task.get("lease"), dict)
                    else None
                ),
                "resume_host": task.get("resume_host"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
            }
            for task in state_value["tasks"]
            if isinstance(task, dict)
        ]
        return _success(
            "list",
            workspace,
            revision=state_value["revision"],
            current_task_id=state_value["current_task_id"],
            tasks=summaries,
        )


def command_checkpoint(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        _require_active_lease(task, arguments.host, arguments.lease)
        timestamp = _now()
        snapshot = capture_snapshot(workspace)
        checkpoint = _append_checkpoint(
            task,
            kind="manual",
            host=arguments.host,
            timestamp=timestamp,
            snapshot=snapshot,
            note=arguments.note,
        )
        task["lease"] = _new_lease(arguments.host, timestamp)
        _commit_state(store, state_value, timestamp)
        return _success(
            "checkpoint",
            workspace,
            revision=state_value["revision"],
            task=task,
            checkpoint=checkpoint,
        )


def command_takeover(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        if task.get("status") != "active":
            raise CliError(
                "task_not_active",
                "Only an active task can be taken over.",
                details={"status": task.get("status")},
            )
        lease = task.get("lease")
        owner = lease.get("host") if isinstance(lease, dict) else None
        if owner != arguments.host:
            raise CliError(
                "host_mismatch",
                "Only the host that owns the active task may take it over.",
                details={"lease_host": owner, "requested_host": arguments.host},
            )

        timestamp = _now()
        live_snapshot = capture_snapshot(workspace)
        drift = live_snapshot["digest"] != task["snapshot"]["digest"]
        task.setdefault("takeovers", []).append(
            {
                "host": arguments.host,
                "created_at": timestamp,
                "reason": arguments.reason,
            }
        )
        task["lease"] = _new_lease(arguments.host, timestamp)
        task["updated_at"] = timestamp
        _commit_state(store, state_value, timestamp)
        return _success(
            "takeover",
            workspace,
            revision=state_value["revision"],
            task=task,
            live_snapshot=live_snapshot,
            drift=drift,
        )


def command_pause(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        _require_active_lease(task, arguments.host, arguments.lease)
        timestamp = _now()
        snapshot = capture_snapshot(workspace)
        checkpoint = _append_checkpoint(
            task,
            kind="pause",
            host=arguments.host,
            timestamp=timestamp,
            snapshot=snapshot,
            note=arguments.reason,
        )
        task["status"] = "paused"
        task["lease"] = None
        task["resume_host"] = arguments.host
        _commit_state(store, state_value, timestamp)
        return _success(
            "pause",
            workspace,
            revision=state_value["revision"],
            task=task,
            checkpoint=checkpoint,
        )


def command_handoff(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    target_host = arguments.to.strip()
    if not target_host:
        raise CliError(
            "target_host_invalid",
            "Target host must contain non-whitespace text.",
        )
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        _require_active_lease(task, arguments.host, arguments.lease)
        timestamp = _now()
        snapshot = capture_snapshot(workspace)
        checkpoint = _append_checkpoint(
            task,
            kind="handoff",
            host=arguments.host,
            timestamp=timestamp,
            snapshot=snapshot,
            note=arguments.note,
            target_host=target_host,
        )
        task["status"] = "paused"
        task["lease"] = None
        task["resume_host"] = target_host
        _commit_state(store, state_value, timestamp)
        return _success(
            "handoff",
            workspace,
            revision=state_value["revision"],
            task=task,
            checkpoint=checkpoint,
        )


def command_resume(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        if task.get("status") != "paused":
            raise CliError(
                "task_not_paused",
                "Only a paused task can be resumed.",
                details={"status": task.get("status")},
            )
        expected_host = task.get("resume_host")
        if expected_host is not None and expected_host != arguments.host:
            raise CliError(
                "host_mismatch",
                "The task is reserved for a different resume host.",
                details={
                    "expected_host": expected_host,
                    "requested_host": arguments.host,
                },
            )

        live_snapshot = capture_snapshot(workspace)
        expected_digest = task["snapshot"]["digest"]
        actual_digest = live_snapshot["digest"]
        drift = expected_digest != actual_digest
        if drift and not arguments.accept_drift:
            raise CliError(
                "snapshot_drift",
                "The worktree changed after the last checkpoint; inspect it and retry with --accept-drift.",
                details={
                    "expected_digest": expected_digest,
                    "actual_digest": actual_digest,
                    "expected_changes": task["snapshot"].get("changes"),
                    "actual_changes": live_snapshot.get("changes"),
                },
            )

        timestamp = _now()
        checkpoint = None
        if drift:
            checkpoint = _append_checkpoint(
                task,
                kind="drift-accepted",
                host=arguments.host,
                timestamp=timestamp,
                snapshot=live_snapshot,
                previous_digest=expected_digest,
            )
        task["status"] = "active"
        task["lease"] = _new_lease(arguments.host, timestamp)
        task["resume_host"] = None
        task["updated_at"] = timestamp
        _commit_state(store, state_value, timestamp)
        result = _success(
            "resume",
            workspace,
            revision=state_value["revision"],
            task=task,
            live_snapshot=live_snapshot,
            accepted_drift=drift,
        )
        if checkpoint is not None:
            result["checkpoint"] = checkpoint
        return result


def command_complete(
    workspace: GitWorkspace, store: StateStore, arguments: argparse.Namespace
) -> dict[str, Any]:
    with store.lock():
        state_value = _load_existing(store)
        task = _current_task(state_value)
        _require_active_lease(task, arguments.host, arguments.lease)
        timestamp = _now()
        snapshot = capture_snapshot(workspace)
        checkpoint = _append_checkpoint(
            task,
            kind="complete",
            host=arguments.host,
            timestamp=timestamp,
            snapshot=snapshot,
            note=arguments.summary,
        )
        task["status"] = "completed"
        task["lease"] = None
        task["resume_host"] = None
        task["completed_at"] = timestamp
        if arguments.summary:
            task["summary"] = arguments.summary
        _commit_state(store, state_value, timestamp)
        return _success(
            "complete",
            workspace,
            revision=state_value["revision"],
            task=task,
            checkpoint=checkpoint,
        )


def command_review_gate(arguments: argparse.Namespace) -> dict[str, Any]:
    # Imported lazily so the task-state CLI remains usable as a standalone
    # module and review-gate stays independent of Git workspace discovery.
    import review_gate

    try:
        result = review_gate.evaluate_bundle(Path(arguments.bundle))
    except review_gate.ReviewGateError as error:
        raise CliError(error.code, error.message) from error
    return {"ok": result["verdict"] == "REPORT_ONLY", "command": "review-gate", **result}


def build_parser() -> JsonArgumentParser:
    parser = JsonArgumentParser(prog="adt")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("ADT_WORKSPACE", "."),
        help="Git worktree to operate on (defaults to the current directory).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start")
    start.add_argument("--host", required=True)
    start.add_argument("--goal", required=True)
    start.add_argument("--kind", choices=("develop", "review"), default="develop")
    start.add_argument(
        "--profile",
        choices=("economy", "balanced", "critical", "manual"),
        default="balanced",
    )

    subparsers.add_parser("status")
    subparsers.add_parser("context")
    subparsers.add_parser("list")

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--host", required=True)
    checkpoint.add_argument("--lease", required=True)
    checkpoint.add_argument("--note")

    takeover = subparsers.add_parser("takeover")
    takeover.add_argument("--host", required=True)
    takeover.add_argument("--reason", required=True)

    pause = subparsers.add_parser("pause")
    pause.add_argument("--host", required=True)
    pause.add_argument("--lease", required=True)
    pause.add_argument("--reason")

    handoff = subparsers.add_parser("handoff")
    handoff.add_argument("--host", required=True)
    handoff.add_argument("--lease", required=True)
    handoff.add_argument("--to", required=True)
    handoff.add_argument("--note")

    resume = subparsers.add_parser("resume")
    resume.add_argument("--host", required=True)
    resume.add_argument("--accept-drift", action="store_true")

    complete = subparsers.add_parser("complete")
    complete.add_argument("--host", required=True)
    complete.add_argument("--lease", required=True)
    complete.add_argument("--summary")

    review_gate = subparsers.add_parser("review-gate")
    review_gate.add_argument("--bundle", required=True)
    return parser


def dispatch(arguments: argparse.Namespace) -> dict[str, Any]:
    if arguments.command == "review-gate":
        return command_review_gate(arguments)
    workspace = GitWorkspace.discover(Path(arguments.workspace))
    store = StateStore(workspace)
    if arguments.command == "start":
        return command_start(workspace, store, arguments)
    if arguments.command in {"status", "context"}:
        return command_status(arguments.command, workspace, store)
    if arguments.command == "list":
        return command_list(workspace, store)
    if arguments.command == "checkpoint":
        return command_checkpoint(workspace, store, arguments)
    if arguments.command == "takeover":
        return command_takeover(workspace, store, arguments)
    if arguments.command == "pause":
        return command_pause(workspace, store, arguments)
    if arguments.command == "handoff":
        return command_handoff(workspace, store, arguments)
    if arguments.command == "resume":
        return command_resume(workspace, store, arguments)
    if arguments.command == "complete":
        return command_complete(workspace, store, arguments)
    raise CliError("usage", "Unknown command.", exit_code=2)


def _emit(value: dict[str, Any], stream: Any) -> None:
    json.dump(value, stream, ensure_ascii=False, sort_keys=True)
    stream.write("\n")
    stream.flush()


def main(argv: Sequence[str] | None = None) -> int:
    arguments: argparse.Namespace | None = None
    try:
        arguments = build_parser().parse_args(argv)
        result = dispatch(arguments)
        _emit(result, sys.stdout)
        if arguments.command == "review-gate" and result["verdict"] == "HOLD":
            return REVIEW_HOLD_EXIT_CODE
        return 0
    except CliError as error:
        _emit(
            {
                "ok": False,
                "error": {
                    "code": error.code,
                    "message": error.message,
                    **({"details": error.details} if error.details else {}),
                },
            },
            sys.stderr,
        )
        return error.exit_code
    except KeyboardInterrupt:
        _emit(
            {
                "ok": False,
                "error": {"code": "interrupted", "message": "Command interrupted."},
            },
            sys.stderr,
        )
        return 130
    except Exception:
        message = (
            "The review gate failed before it could produce a verdict."
            if arguments is not None and arguments.command == "review-gate"
            else "The command failed before it could update task state."
        )
        _emit(
            {
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": message,
                },
            },
            sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
