#!/usr/bin/env python3
"""Reject non-portable locators from publishable files and Git messages."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    rule: str


_POSIX_USER_ROOT = b"/" + b"Users" + b"/"
_POSIX_HOME_ROOT = b"/" + b"home" + b"/"
_WINDOWS_USER_ROOT = b"Users" + b"\\"
_LOCAL_FILE_SCHEME = b"file" + b"://"
_PARENT_LOCATOR = b".." + b"/"

_LINE_RULES = (
    (
        "absolute-home",
        re.compile(
            b"(?:"
            + re.escape(_POSIX_USER_ROOT)
            + b"[^/\\s]+/"
            + b"|"
            + re.escape(_POSIX_HOME_ROOT)
            + b"[^/\\s]+/"
            + b"|[A-Za-z]:\\\\"
            + re.escape(_WINDOWS_USER_ROOT)
            + rb"[^\s\\]+\\"
            + b")"
        ),
    ),
    ("local-file-uri", re.compile(re.escape(_LOCAL_FILE_SCHEME), re.IGNORECASE)),
    ("parent-locator", re.compile(re.escape(_PARENT_LOCATOR))),
)


def find_line_violations(
    path: str, data: bytes, external_patterns: Sequence[bytes] = ()
) -> list[Violation]:
    violations: list[Violation] = []
    for line_number, line in enumerate(data.splitlines(), start=1):
        for rule, pattern in _LINE_RULES:
            if pattern.search(line):
                violations.append(Violation(path, line_number, rule))
        if any(pattern and pattern in line for pattern in external_patterns):
            violations.append(Violation(path, line_number, "external-pattern"))
    return violations


def publishable_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return sorted(
        Path(os.fsdecode(raw_path))
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    )


def _escapes_root(root: Path, target: Path) -> bool:
    try:
        return os.path.commonpath((str(root), str(target))) != str(root)
    except ValueError:
        return True


def scan_repo(
    root: Path, external_patterns: Sequence[bytes] = ()
) -> list[Violation]:
    root = root.resolve()
    violations: list[Violation] = []
    for relative_path in publishable_paths(root):
        full_path = root / relative_path
        if full_path.is_symlink():
            if _escapes_root(root, full_path.resolve(strict=False)):
                violations.append(
                    Violation(str(relative_path), 0, "escaping-symlink")
                )
                continue
        if not full_path.is_file():
            continue
        violations.extend(
            find_line_violations(
                str(relative_path), full_path.read_bytes(), external_patterns
            )
        )
    return violations


def scan_history(
    root: Path, external_patterns: Sequence[bytes] = (), ref: str = "HEAD"
) -> list[Violation]:
    root = root.resolve()
    result = subprocess.run(
        ["git", "rev-list", "--objects", ref],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    object_paths: dict[bytes, str] = {}
    for record in result.stdout.splitlines():
        object_id, separator, raw_path = record.partition(b" ")
        if separator and raw_path:
            object_paths.setdefault(object_id, os.fsdecode(raw_path))

    if not object_paths:
        return []

    type_result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        cwd=root,
        check=True,
        input=b"\n".join(object_paths) + b"\n",
        stdout=subprocess.PIPE,
    )
    blob_ids = [
        object_id
        for object_id, object_type in (
            line.split(b" ", 1) for line in type_result.stdout.splitlines()
        )
        if object_type == b"blob"
    ]

    violations: list[Violation] = []
    for object_id in blob_ids:
        blob = subprocess.run(
            ["git", "cat-file", "blob", os.fsdecode(object_id)],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        path = object_paths[object_id]
        historical_path = f"{path}@{os.fsdecode(object_id[:12])}"
        violations.extend(
            find_line_violations(historical_path, blob, external_patterns)
        )
    return violations


def scan_commit_messages(
    root: Path, external_patterns: Sequence[bytes] = (), ref: str = "HEAD"
) -> list[Violation]:
    root = root.resolve()
    result = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x00", ref],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    fields = result.stdout.split(b"\0")
    violations: list[Violation] = []
    for index in range(0, len(fields) - 1, 2):
        object_id = fields[index].strip()
        message = fields[index + 1]
        if not object_id:
            continue
        violations.extend(
            find_line_violations(
                f"commit@{os.fsdecode(object_id[:12])}",
                message,
                external_patterns,
            )
        )
    return violations


def scan_annotated_tag_messages(
    root: Path, external_patterns: Sequence[bytes] = ()
) -> list[Violation]:
    root = root.resolve()
    result = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname) %(objecttype) %(objectname)",
            "refs/tags",
        ],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    violations: list[Violation] = []
    for record in result.stdout.splitlines():
        _raw_ref, object_type, object_id = record.split(b" ", 2)
        if object_type != b"tag":
            continue
        tag = subprocess.run(
            ["git", "cat-file", "tag", os.fsdecode(object_id)],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        _, separator, message = tag.partition(b"\n\n")
        if not separator:
            message = b""
        violations.extend(
            find_line_violations(
                f"tag@{os.fsdecode(object_id[:12])}", message, external_patterns
            )
        )
    return violations


def load_external_patterns() -> tuple[bytes, ...]:
    pattern_file = os.environ.get("PUBLIC_SOURCE_PATTERNS_FILE")
    if not pattern_file:
        return ()
    return tuple(
        line
        for line in Path(pattern_file).read_bytes().splitlines()
        if line and not line.startswith(b"#")
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    external_patterns = load_external_patterns()
    violations = scan_repo(root, external_patterns)
    violations.extend(scan_history(root, external_patterns))
    violations.extend(scan_commit_messages(root, external_patterns))
    violations.extend(scan_annotated_tag_messages(root, external_patterns))
    for violation in violations:
        print(f"{violation.path}:{violation.line}: {violation.rule}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
