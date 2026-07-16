"""Replayable structured-result projections for two observed native surfaces.

This spike does not launch a backend or produce assurance receipts. It only
projects the portable result shape and mechanically normalizes retained native
output through the existing review-gate validator.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REVIEW_GATE = ROOT / "plugins" / "ai-dev-team-v2" / "scripts" / "review_gate.py"


def _load_review_gate() -> Any:
    specification = importlib.util.spec_from_file_location(
        "adt_schema_spike_review_gate", REVIEW_GATE
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("The review-gate validator cannot be loaded.")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


review_gate = _load_review_gate()


CODEX_SURFACE = "codex-exec-v0"
CLAUDE_SURFACE = "claude-print-v0"
SURFACES = frozenset({CODEX_SURFACE, CLAUDE_SURFACE})


class NativeResultAdapterError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _encoded(value: object) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise NativeResultAdapterError(
            "native_output_invalid",
            "Normalized JSON contains an unpaired Unicode surrogate.",
        ) from error


def _surface(value: str) -> str:
    if value not in SURFACES:
        raise NativeResultAdapterError(
            "native_surface_unsupported", "The native result surface is unsupported."
        )
    return value


def _work_order(raw: bytes) -> dict[str, Any]:
    try:
        value = review_gate._strict_json_loads(raw, "work_order")
        return review_gate._validate_work_order(value)
    except review_gate.ReviewGateError as error:
        raise NativeResultAdapterError(error.code, error.message) from error


def _context(work_order_raw: bytes, path_id: str) -> tuple[dict[str, Any], str]:
    work_order = _work_order(work_order_raw)
    if path_id not in work_order["review_paths"]:
        raise NativeResultAdapterError(
            "review_path_unknown", "The path ID is absent from the work order."
        )
    return work_order, hashlib.sha256(work_order_raw).hexdigest()


def _constant(value: str) -> dict[str, str]:
    # Codex rejected a const without its sibling type. Keeping the redundant
    # type is the candidate common projection; Claude acceptance remains a probe.
    return {"const": value, "type": "string"}


def _result_schema(
    work_order: dict[str, Any], work_order_sha256: str, path_id: str
) -> dict[str, Any]:
    text = {"type": "string"}
    evidence = {
        "additionalProperties": False,
        "properties": {
            "id": text,
            "observation": text,
            "requirement": text,
        },
        "required": ["id", "requirement", "observation"],
        "type": "object",
    }
    finding = {
        "additionalProperties": False,
        "properties": {
            "evidence_refs": {
                "items": text,
                "type": "array",
            },
            "id": text,
            "severity": {
                "enum": sorted(review_gate.SEVERITIES),
                "type": "string",
            },
            "summary": text,
        },
        "required": ["id", "severity", "summary", "evidence_refs"],
        "type": "object",
    }
    return {
        "additionalProperties": False,
        "properties": {
            "artifact_snapshot_sha256": _constant(
                work_order["artifact"]["snapshot_sha256"]
            ),
            "contract_version": _constant(review_gate.RESULT_VERSION),
            "degradations": {"items": text, "type": "array"},
            "evidence": {"items": evidence, "type": "array"},
            "findings": {"items": finding, "type": "array"},
            "gaps": {"items": text, "type": "array"},
            "path_id": _constant(path_id),
            "release_recommendation": _constant("REPORT_ONLY"),
            "terminal_status": {
                "enum": sorted(review_gate.TERMINAL_STATUSES),
                "type": "string",
            },
            "work_order_id": _constant(work_order["id"]),
            "work_order_sha256": _constant(work_order_sha256),
        },
        "required": [
            "contract_version",
            "work_order_id",
            "path_id",
            "work_order_sha256",
            "artifact_snapshot_sha256",
            "terminal_status",
            "release_recommendation",
            "evidence",
            "findings",
            "gaps",
            "degradations",
        ],
        "type": "object",
    }


def project_result_schema(work_order_raw: bytes, path_id: str) -> bytes:
    """Return the candidate common emission schema for one declared path."""
    work_order, work_order_sha256 = _context(work_order_raw, path_id)
    return _encoded(_result_schema(work_order, work_order_sha256, path_id))


def _native_result(surface: str, raw: bytes) -> Any:
    location = "codex_native_result" if surface == CODEX_SURFACE else "claude_wrapper"
    try:
        value = review_gate._strict_json_loads(raw, location)
    except review_gate.ReviewGateError as error:
        raise NativeResultAdapterError(error.code, error.message) from error
    if surface == CLAUDE_SURFACE:
        if (
            not isinstance(value, dict)
            or value.get("type") != "result"
            or value.get("subtype") != "success"
            or value.get("is_error") is not False
        ):
            raise NativeResultAdapterError(
                "native_output_invalid",
                "Claude native output is not a successful result wrapper.",
            )
        if "permission_denials" not in value or not isinstance(
            value["permission_denials"], list
        ):
            raise NativeResultAdapterError(
                "native_output_invalid",
                "Claude native output has invalid permission-denial status.",
            )
        if value["permission_denials"]:
            raise NativeResultAdapterError(
                "native_output_degraded",
                "Claude native output reports permission denials.",
            )
        if "structured_output" not in value:
            raise NativeResultAdapterError(
                "native_output_invalid",
                "Claude native output lacks structured_output.",
            )
        value = value["structured_output"]
    if not isinstance(value, dict):
        raise NativeResultAdapterError(
            "native_output_invalid", "The native result must be a JSON object."
        )
    return value


def normalize_result(
    surface: str,
    work_order_raw: bytes,
    path_id: str,
    native_output_raw: bytes,
) -> bytes:
    """Validate and deterministically encode one retained native result."""
    selected_surface = _surface(surface)
    work_order, work_order_sha256 = _context(work_order_raw, path_id)
    value = _native_result(selected_surface, native_output_raw)
    try:
        result = review_gate._validate_result(value, "native_result")
    except review_gate.ReviewGateError as error:
        raise NativeResultAdapterError(error.code, error.message) from error

    if (
        result["work_order_id"] != work_order["id"]
        or result["path_id"] != path_id
        or result["work_order_sha256"] != work_order_sha256
        or result["artifact_snapshot_sha256"]
        != work_order["artifact"]["snapshot_sha256"]
    ):
        raise NativeResultAdapterError(
            "native_result_binding_mismatch",
            "The native result is bound to different review inputs.",
        )
    return _encoded(result)
