#!/usr/bin/env python3
"""Deterministic, local-only checks for exact outbound publication text."""

from __future__ import annotations

import hashlib
import html
import os
import re
import stat
import string
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import unquote, urlsplit


MAX_INPUT_BYTES = 1024 * 1024
MAX_PATTERNS_BYTES = 64 * 1024
MAX_PATTERNS = 1024
MAX_PATTERN_CHARACTERS = 4096
PUBLICATION_GATE_CONTRACT_VERSION = "adt.publication-gate.v1"

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_REPOSITORY = r"[A-Za-z0-9._-]{1,100}"
_REPOSITORY_ID = re.compile(rf"^(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})$")
_GITHUB_HOST = (
    r"(?:github\.com|www\.github\.com|api\.github\.com|gist\.github\.com|"
    r"uploads\.github\.com|codeload\.github\.com|github\.dev|"
    r"githubusercontent\.com|[A-Za-z0-9.-]+\.githubusercontent\.com|"
    r"[A-Za-z0-9-]+\.github\.io)"
)
_URL_CANDIDATE = re.compile(
    rf"(?i)(?:"
    rf"(?:https?:)?//[^\s<>\[\]()`\"']+"
    rf"|(?<![A-Za-z0-9.-]){_GITHUB_HOST}(?::[0-9]+)?/[^\s<>\[\]()`\"']+"
    rf")"
)
_ROOT_RELATIVE_MARKDOWN_TARGET = re.compile(
    r"\]\(\s*(?P<target>/[^)\s]+)"
)
_ROOT_RELATIVE_REFERENCE_TARGET = re.compile(
    r"^ {0,3}\[[^]\n]+\]:[ \t]*<?(?P<target>/[^>\s]+)>?"
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
_MARKDOWN_ESCAPE = re.compile(r"\\([" + re.escape(string.punctuation) + r"])")
_MARKDOWN_FENCE = re.compile(r"^ {0,3}(?:> ?)?(?P<fence>`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(?P<ticks>`+).*?(?P=ticks)")
_GITHUB_RESERVED_ROOTS = frozenset(
    {
        "about",
        "account",
        "apps",
        "codespaces",
        "collections",
        "contact",
        "customer-stories",
        "enterprise",
        "events",
        "explore",
        "features",
        "issues",
        "login",
        "marketplace",
        "new",
        "notifications",
        "organizations",
        "orgs",
        "pricing",
        "pulls",
        "readme",
        "search",
        "security",
        "settings",
        "site",
        "sponsors",
        "topics",
        "trending",
        "users",
    }
)
_GITHUB_OWNER_ROUTES = frozenset(
    {"organizations", "orgs", "sponsors", "users"}
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
    normalized = _MARKDOWN_ESCAPE.sub(r"\1", normalized)
    return normalized.replace("\\", "/")


def _path_segments(path: str) -> list[str]:
    segments: list[str] = []
    for segment in path.split("/"):
        if not segment or segment == ".":
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    return segments


def _github_owner_from_url(candidate: str) -> str | None:
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif candidate.startswith("/"):
        candidate = "https://github.com" + candidate
    elif "://" not in candidate:
        candidate = "https://" + candidate
    try:
        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    segments = _path_segments(parsed.path)

    if host in {"github.com", "www.github.com"}:
        if not segments:
            return None
        route = segments[0].casefold()
        if route in _GITHUB_OWNER_ROUTES and len(segments) >= 2:
            return segments[1]
        if route in _GITHUB_RESERVED_ROOTS:
            return None
        return segments[0]

    if host in {"api.github.com", "uploads.github.com"}:
        if len(segments) >= 2 and segments[0].casefold() in {
            "orgs",
            "organizations",
            "repos",
            "users",
        }:
            return segments[1]
        return None

    if host in {
        "codeload.github.com",
        "gist.github.com",
        "gist.githubusercontent.com",
        "github.dev",
        "raw.githubusercontent.com",
    }:
        return segments[0] if segments else ""

    if host == "githubusercontent.com" or host.endswith(
        ".githubusercontent.com"
    ):
        return ""

    if host.endswith(".github.io"):
        owner = host[: -len(".github.io")]
        return owner if owner and "." not in owner and owner != "www" else ""

    return None


def _is_external_owner(owner: str, destination_owner: str) -> bool:
    normalized = owner.casefold()
    return normalized != destination_owner and normalized not in _GITHUB_RESERVED_ROOTS


def _has_external_github_owner(line: str, destination_owner: str) -> bool:
    for match in _URL_CANDIDATE.finditer(line):
        owner = _github_owner_from_url(match.group(0))
        if owner is not None and _is_external_owner(owner, destination_owner):
            return True
    for matcher in (
        _ROOT_RELATIVE_MARKDOWN_TARGET,
        _ROOT_RELATIVE_REFERENCE_TARGET,
    ):
        for match in matcher.finditer(line):
            owner = _github_owner_from_url(match.group("target"))
            if owner is not None and _is_external_owner(owner, destination_owner):
                return True
    for matcher in (_GITHUB_SCP_URL, _OWNER_REPOSITORY_ISSUE, _OWNER_REPOSITORY_COMMIT):
        for match in matcher.finditer(line):
            if _is_external_owner(match.group("owner"), destination_owner):
                return True
    return False


def _visible_markdown_for_mentions(
    line: str, fence: str | None
) -> tuple[str, str | None]:
    match = _MARKDOWN_FENCE.match(line)
    if fence is not None:
        if (
            match is not None
            and match.group("fence")[0] == fence[0]
            and len(match.group("fence")) >= len(fence)
        ):
            return "", None
        return "", fence
    if match is not None:
        return "", match.group("fence")
    if line.startswith("    ") or line.startswith("\t"):
        return "", None
    return _INLINE_CODE.sub("", line), None


def _has_external_github_mention(line: str, destination_owner: str) -> bool:
    return any(
        _is_external_owner(match.group("owner"), destination_owner)
        for match in _GITHUB_MENTION.finditer(line)
    )


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
    markdown_fence: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        normalized = _normalized_line(line)
        visible, markdown_fence = _visible_markdown_for_mentions(
            normalized, markdown_fence
        )
        if _has_external_github_owner(
            normalized, destination_owner
        ) or _has_external_github_mention(visible, destination_owner):
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
