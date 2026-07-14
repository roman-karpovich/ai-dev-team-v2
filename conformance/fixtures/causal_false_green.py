#!/usr/bin/env python3
"""Materialize the small causal false-green cold-review fixture."""

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

        Review the candidate commit against this behavior contract:

        - a failed item produces exactly one terminal report;
        - the same failure reaches the process boundary and exits non-zero;
        - failed processing does not advance the persisted cursor.

        The repository is self-contained. Permitted focused checks are
        `python3 -m unittest -q` and `python3 runtime.py`.
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
    "runtime.py": dedent(
        """\
        import json

        from listener import listen_once


        def production_main() -> int:
            state = {"cursor": "cursor-7"}
            terminal_reports: list[str] = []

            def report(error: BaseException) -> None:
                terminal_reports.append(str(error))

            try:
                listen_once(state, report)
            except Exception as error:
                report(error)
                print(
                    json.dumps(
                        {
                            "cursor": state["cursor"],
                            "terminal_reports": len(terminal_reports),
                        },
                        sort_keys=True,
                    )
                )
                return 1
            return 0


        if __name__ == "__main__":
            raise SystemExit(production_main())
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


def materialize(repository: Path) -> tuple[str, str]:
    if repository.exists():
        raise ValueError(f"destination already exists: {repository}")
    repository.mkdir(parents=True)
    git(repository, "init", "--quiet", "--initial-branch=main")
    git(repository, "config", "user.name", "Fixture Author")
    git(repository, "config", "user.email", "fixture@example.invalid")
    git(repository, "config", "commit.gpgsign", "false")

    write_files(repository, BASE_FILES)
    base = commit(
        repository,
        "base: existing terminal reporting",
        "2000-01-01T00:00:00Z",
    )

    write_files(repository, CANDIDATE_FILES)
    head = commit(repository, "fix: report handler failures", "2000-01-01T00:01:00Z")
    return base, head


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        print(f"usage: {Path(arguments[0]).name} DESTINATION", file=sys.stderr)
        return 2
    base, head = materialize(Path(arguments[1]))
    print(json.dumps({"base": base, "head": head}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
