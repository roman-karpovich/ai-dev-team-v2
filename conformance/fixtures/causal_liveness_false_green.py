#!/usr/bin/env python3
"""Materialize the causal-liveness false-green cold-review fixture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


BASE_FILES = {
    "REVIEW.md": dedent(
        """\
        # Cold review brief

        Review the proposed change against this accepted behavior intent:

        - a handler failure becomes observable through the configured reporting path;
        - the process reaches a non-zero, supervisor-facing failure outcome;
        - failed processing preserves the persisted cursor;
        - existing sibling-worker lifecycle and cleanup semantics are preserved.

        The repository is self-contained. Permitted focused checks are
        `python3 -m unittest -q` and `python3 probe.py`.
        """
    ),
    "listener.py": dedent(
        """\
        from collections.abc import Callable


        Reporter = Callable[[BaseException], None]


        def handle_item() -> None:
            raise RuntimeError("handler failed")


        def listen_once(state: dict[str, str], report: Reporter) -> None:
            next_cursor = "cursor-8"
            handle_item()
            state["cursor"] = next_cursor
        """
    ),
    "reporting.py": dedent(
        """\
        import json
        import os
        from pathlib import Path


        class RecordingTransport:
            def __init__(self, destination: Path) -> None:
                self.destination = destination

            def capture(self, error: BaseException) -> None:
                record = {
                    "message": str(error),
                    "type": type(error).__name__,
                }
                with self.destination.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, sort_keys=True) + "\\n")
                    stream.flush()
                    os.fsync(stream.fileno())
        """
    ),
    "runtime.py": dedent(
        """\
        import sys
        import time
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path

        from listener import listen_once
        from reporting import RecordingTransport


        POLL_SECONDS = 0.005
        STARTUP_TIMEOUT_SECONDS = 2.0


        def wait_for(path: Path) -> None:
            deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
            while not path.exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for {path.name}")
                time.sleep(POLL_SECONDS)


        def run_sibling(run_directory: Path) -> None:
            (run_directory / "sibling-ready").write_text("ready")
            try:
                release = run_directory / "release-sibling"
                while not release.exists():
                    time.sleep(POLL_SECONDS)
            finally:
                (run_directory / "sibling-cleanup").write_text("clean")


        def production_main(run_directory: Path) -> int:
            run_directory.mkdir(parents=True, exist_ok=True)
            state = {"cursor": "cursor-7"}
            cursor_path = run_directory / "cursor"
            cursor_path.write_text(state["cursor"])
            transport = RecordingTransport(run_directory / "reports.jsonl")

            def run_listener() -> None:
                (run_directory / "listener-started").write_text("started")
                try:
                    listen_once(state, transport.capture)
                finally:
                    (run_directory / "listener-finished").write_text("finished")

            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    executor.submit(run_sibling, run_directory)
                    wait_for(run_directory / "sibling-ready")
                    failed = executor.submit(run_listener)
                    failed.result()
            except Exception as error:
                transport.capture(error)
                cursor_path.write_text(state["cursor"])
                return 31
            return 0


        if __name__ == "__main__":
            if len(sys.argv) != 2:
                raise SystemExit("usage: runtime.py RUN_DIRECTORY")
            raise SystemExit(production_main(Path(sys.argv[1])))
        """
    ),
    "probe.py": dedent(
        """\
        import json
        import subprocess
        import sys
        import tempfile
        import time
        from collections.abc import Callable
        from pathlib import Path


        POLL_SECONDS = 0.005
        PROBE_TIMEOUT_SECONDS = 3.0
        ROOT = Path(__file__).resolve().parent


        def wait_until(predicate: Callable[[], bool], description: str) -> None:
            deadline = time.monotonic() + PROBE_TIMEOUT_SECONDS
            while not predicate():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for {description}")
                time.sleep(POLL_SECONDS)


        def report_count(path: Path) -> int:
            if not path.exists():
                return 0
            return len(path.read_text().splitlines())


        def snapshot(process: subprocess.Popen[bytes], run_directory: Path) -> dict[str, object]:
            exit_code = process.poll()
            return {
                "cursor": (run_directory / "cursor").read_text(),
                "exit_code": exit_code,
                "process_alive": exit_code is None,
                "reports": report_count(run_directory / "reports.jsonl"),
                "sibling_cleanup": (run_directory / "sibling-cleanup").exists(),
            }


        def probe() -> dict[str, object]:
            with tempfile.TemporaryDirectory() as temporary_directory:
                run_directory = Path(temporary_directory)
                process = subprocess.Popen(
                    [sys.executable, "runtime.py", str(run_directory)],
                    cwd=ROOT,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                try:
                    wait_until(
                        lambda: (run_directory / "sibling-ready").exists(),
                        "the sibling worker",
                    )
                    wait_until(
                        lambda: (run_directory / "listener-finished").exists()
                        or process.poll() is not None,
                        "the listener outcome",
                    )
                    while_blocked = snapshot(process, run_directory)

                    (run_directory / "release-sibling").write_text("release")
                    wait_until(lambda: process.poll() is not None, "process exit")
                    process.wait()
                    after_release = snapshot(process, run_directory)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()

                return {
                    "after_release": after_release,
                    "while_blocked": while_blocked,
                }


        if __name__ == "__main__":
            print(json.dumps(probe(), sort_keys=True))
        """
    ),
}

CANDIDATE_FILES = {
    "listener.py": dedent(
        """\
        from collections.abc import Callable


        Reporter = Callable[[BaseException], None]


        def handle_item() -> None:
            raise RuntimeError("handler failed")


        def listen_once(state: dict[str, str], report: Reporter) -> None:
            next_cursor = "cursor-8"
            try:
                handle_item()
            except Exception as error:
                report(error)
                raise
            state["cursor"] = next_cursor
        """
    ),
    "test_listener.py": dedent(
        """\
        import unittest

        from listener import listen_once


        class ListenerTest(unittest.TestCase):
            def test_failure_is_reported_without_advancing_cursor(self) -> None:
                state = {"cursor": "cursor-7"}
                reports: list[BaseException] = []

                with self.assertRaisesRegex(RuntimeError, "handler failed"):
                    listen_once(state, reports.append)

                self.assertEqual(1, len(reports))
                self.assertEqual("cursor-7", state["cursor"])


        if __name__ == "__main__":
            unittest.main()
        """
    ),
}

REPAIR_FILES = {
    "listener.py": dedent(
        """\
        import os
        from collections.abc import Callable
        from typing import NoReturn


        Reporter = Callable[[BaseException], None]
        ExitProcess = Callable[[int], NoReturn]


        def handle_item() -> None:
            raise RuntimeError("handler failed")


        def listen_once(
            state: dict[str, str],
            report: Reporter,
            exit_process: ExitProcess = os._exit,
        ) -> None:
            next_cursor = "cursor-8"
            try:
                handle_item()
            except Exception as error:
                report(error)
                exit_process(47)
            state["cursor"] = next_cursor
        """
    ),
    "test_listener.py": dedent(
        """\
        import unittest

        from listener import listen_once


        class ForcedExit(Exception):
            pass


        class ListenerTest(unittest.TestCase):
            def test_failure_is_reported_and_forces_nonzero_exit(self) -> None:
                state = {"cursor": "cursor-7"}
                reports: list[BaseException] = []
                exit_codes: list[int] = []

                def record_exit(code: int) -> None:
                    exit_codes.append(code)
                    raise ForcedExit

                with self.assertRaises(ForcedExit):
                    listen_once(state, reports.append, record_exit)

                self.assertEqual(1, len(reports))
                self.assertEqual([47], exit_codes)
                self.assertEqual("cursor-7", state["cursor"])


        if __name__ == "__main__":
            unittest.main()
        """
    ),
}


def git(
    repository: Path,
    *arguments: str,
    environment: dict[str, str] | None = None,
) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def write_files(repository: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (repository / relative_path).write_text(content)


def commit(repository: Path, message: str, timestamp: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": timestamp,
        "GIT_COMMITTER_DATE": timestamp,
    }
    git(repository, "add", "--all", environment=environment)
    git(repository, "commit", "--quiet", "--message", message, environment=environment)
    return git(repository, "rev-parse", "HEAD")


def materialize(repository: Path) -> tuple[str, str, str]:
    if repository.exists():
        raise ValueError(f"destination already exists: {repository}")
    repository.mkdir(parents=True)
    git(repository, "init", "--quiet", "--initial-branch=main")
    git(repository, "config", "user.name", "Fixture Author")
    git(repository, "config", "user.email", "fixture@example.invalid")
    git(repository, "config", "commit.gpgsign", "false")

    write_files(repository, BASE_FILES)
    base = commit(repository, "snapshot: baseline", "2000-01-01T00:00:00Z")

    write_files(repository, CANDIDATE_FILES)
    candidate = commit(
        repository,
        "snapshot: candidate",
        "2000-01-01T00:01:00Z",
    )

    write_files(repository, REPAIR_FILES)
    repair = commit(repository, "snapshot: repaired", "2000-01-01T00:02:00Z")
    return base, candidate, repair


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(f"usage: {Path(arguments[0]).name} DESTINATION", file=sys.stderr)
        return 2
    base, candidate, repair = materialize(Path(arguments[1]))
    print(
        json.dumps(
            {"base": base, "candidate": candidate, "head": repair, "repair": repair},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
