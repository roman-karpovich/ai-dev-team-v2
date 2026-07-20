#!/usr/bin/env python3
"""Deterministic, local-only checks for exact outbound publication text."""

from __future__ import annotations

import hashlib
import html
import os
import re
import stat
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import unquote


MAX_INPUT_BYTES = 1024 * 1024
MAX_PATTERNS_BYTES = 64 * 1024
MAX_PATTERNS = 1024
MAX_PATTERN_CHARACTERS = 4096
PUBLICATION_GATE_CONTRACT_VERSION = "adt.publication-gate.v1"

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_REPOSITORY = r"[A-Za-z0-9._-]{1,100}"
_REPOSITORY_ID = re.compile(rf"^(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})$")
_GITHUB_WEB_REFERENCE = re.compile(
    rf"(?i)(?<![A-Za-z0-9.-])(?:www\.)?github\.com/"
    rf"(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})"
)
_GITHUB_API_URL = re.compile(
    rf"(?i)https?://api\.github\.com/repos/"
    rf"(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})"
)
_GITHUB_WEB_ACCOUNT = re.compile(
    rf"(?i)(?<![A-Za-z0-9.-])(?:www\.)?github\.com/"
    rf"(?P<owner>{_OWNER})(?=$|[^A-Za-z0-9-])"
)
_GITHUB_API_ACCOUNT = re.compile(
    rf"(?i)https?://api\.github\.com/users/(?P<owner>{_OWNER})"
)
_GITHUB_GIST_ACCOUNT = re.compile(
    rf"(?i)https?://gist\.github\.com/(?P<owner>{_OWNER})"
)
_GITHUB_CONTENT_REFERENCE = re.compile(
    rf"(?i)https?://(?:raw\.githubusercontent\.com|codeload\.github\.com|github\.dev)/"
    rf"(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})"
)
_GITHUB_SCP_URL = re.compile(
    rf"(?i)(?<![A-Za-z0-9])git@github\.com:"
    rf"(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})"
)
_OWNER_REPOSITORY_ISSUE = re.compile(
    rf"(?<![A-Za-z0-9_.-])(?P<owner>{_OWNER})/"
    rf"(?P<repo>{_REPOSITORY})#[0-9]+(?![0-9])"
)
_OWNER_REPOSITORY_COMMIT = re.compile(
    rf"(?i)(?<![A-Za-z0-9_.-])(?P<owner>{_OWNER})/"
    rf"(?P<repo>{_REPOSITORY})@[0-9a-f]{{7,64}}(?![0-9a-f])"
)
_GITHUB_MENTION = re.compile(
    rf"(?i)(?<![A-Za-z0-9_])@(?P<owner>{_OWNER})(?![A-Za-z0-9-])"
)


class PublicationGateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise PublicationGateError(code, message)


def _repository_id(value: Any) -> str:
    if not isinstance(value, str):
        _fail(
            "publication_repository_invalid",
            "A repository argument is not a valid OWNER/REPO identifier.",
        )
    match = _REPOSITORY_ID.fullmatch(value)
    if match is None or match.group("repo") in {".", ".."}:
        _fail(
            "publication_repository_invalid",
            "A repository argument is not a valid OWNER/REPO identifier.",
        )
    return f"{match.group('owner')}/{match.group('repo')}".lower()


def _read_regular_file(
    path: Path,
    *,
    maximum_bytes: int,
    error_code: str,
    error_message: str,
) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            _fail(error_code, error_message)

        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(raw) > maximum_bytes
            or not stat.S_ISREG(after.st_mode)
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or after.st_size != len(raw)
        ):
            _fail(error_code, error_message)
        return raw
    except PublicationGateError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise PublicationGateError(error_code, error_message) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _decode_utf8(raw: bytes, *, code: str, message: str) -> str:
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise PublicationGateError(code, message) from error


def _patterns(path: Path | None) -> tuple[str, ...]:
    if path is None:
        return ()
    message = "The sensitive-patterns file must be a bounded UTF-8 regular file."
    raw = _read_regular_file(
        path,
        maximum_bytes=MAX_PATTERNS_BYTES,
        error_code="publication_patterns_invalid",
        error_message=message,
    )
    text = _decode_utf8(
        raw,
        code="publication_patterns_invalid",
        message=message,
    )
    patterns = tuple(line for line in text.splitlines() if line)
    if (
        len(patterns) > MAX_PATTERNS
        or any(len(pattern) > MAX_PATTERN_CHARACTERS for pattern in patterns)
    ):
        _fail("publication_patterns_invalid", message)
    effective = tuple(sorted({pattern.casefold() for pattern in patterns}))
    if any(len(pattern) > MAX_PATTERN_CHARACTERS for pattern in effective):
        _fail("publication_patterns_invalid", message)
    return effective


def _normalized_line(line: str) -> str:
    normalized = line
    for _ in range(2):
        decoded = unquote(html.unescape(normalized))
        if decoded == normalized:
            break
        normalized = decoded
    return normalized


def _has_external_github_owner(line: str, destination_owner: str) -> bool:
    for matcher in (
        _GITHUB_WEB_REFERENCE,
        _GITHUB_API_URL,
        _GITHUB_WEB_ACCOUNT,
        _GITHUB_API_ACCOUNT,
        _GITHUB_GIST_ACCOUNT,
        _GITHUB_CONTENT_REFERENCE,
        _GITHUB_SCP_URL,
        _OWNER_REPOSITORY_ISSUE,
        _OWNER_REPOSITORY_COMMIT,
        _GITHUB_MENTION,
    ):
        for match in matcher.finditer(line):
            if match.group("owner").casefold() != destination_owner:
                return True
    return False


def _sensitive_patterns_sha256(patterns: tuple[str, ...]) -> str:
    canonical = "" if not patterns else "\n".join(patterns) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_publication(
    *,
    destination_repository: str,
    input_path: Path,
    patterns_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate exact bytes without network access or durable state changes."""
    destination = _repository_id(destination_repository)
    destination_owner = destination.partition("/")[0]
    sensitive_patterns = _patterns(patterns_path)

    input_message = "The publication input must be a bounded UTF-8 regular file."
    raw = _read_regular_file(
        input_path,
        maximum_bytes=MAX_INPUT_BYTES,
        error_code="publication_input_invalid",
        error_message=input_message,
    )
    text = _decode_utf8(
        raw,
        code="publication_input_invalid",
        message=input_message,
    )

    violations: set[tuple[int, str]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        normalized = _normalized_line(line)
        if _has_external_github_owner(normalized, destination_owner):
            violations.add((line_number, "external_github_owner"))
        if any(pattern in normalized.casefold() for pattern in sensitive_patterns):
            violations.add((line_number, "sensitive_literal"))

    if violations:
        return {
            "ok": False,
            "verdict": "HOLD",
            "violations": [
                {"line": line, "rule": rule}
                for line, rule in sorted(violations)
            ],
        }
    return {
        "ok": True,
        "receipt": {
            "contract_version": PUBLICATION_GATE_CONTRACT_VERSION,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_count": len(raw),
            "destination_repo": destination,
            "sensitive_patterns_sha256": _sensitive_patterns_sha256(
                sensitive_patterns
            ),
        },
    }
