#!/usr/bin/env python3
"""Purpose-specific validation and gating for portable cold-review bundles."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn


MANIFEST_VERSION = "adt.portable-cold-review-bundle.v0"
WORK_ORDER_VERSION = "adt.portable-cold-review-work-order.v0"
RESULT_VERSION = "adt.portable-cold-review-result.v0"
RECEIPT_VERSION = "adt.portable-cold-review-receipt.v0"
RESULT_CONTRACT = "ADT_PORTABLE_COLD_REVIEW_RESULT_V0"

TERMINAL_STATUSES = frozenset(
    {"COMPLETED", "CANCELLED", "TIMED_OUT", "FAILED", "UNSUPPORTED"}
)
SEVERITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
UNQUALIFIED_IDENTITIES = frozenset({"unknown", "unspecified", "unavailable"})
MAX_JSON_INTEGER_DIGITS = 512


class ReviewGateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise ReviewGateError(code, message)


def _object(value: Any, fields: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("review_contract_invalid", f"{location} must be an object.")
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        unknown = sorted(actual - fields)
        _fail(
            "review_contract_invalid",
            f"{location} has invalid fields (missing={missing}, unknown={unknown}).",
        )
    return value


def _array(value: Any, location: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(
            "review_contract_invalid",
            f"{location} must be an array with at least {minimum} item(s).",
        )
    return value


def _nonblank(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("review_contract_invalid", f"{location} must be a non-blank string.")
    return value


def _constant(value: Any, expected: str, location: str) -> str:
    text = _nonblank(value, location)
    if text != expected:
        _fail("review_contract_invalid", f"{location} has an unsupported value.")
    return text


def _enum(value: Any, choices: frozenset[str], location: str) -> str:
    text = _nonblank(value, location)
    if text not in choices:
        _fail("review_contract_invalid", f"{location} has an unsupported value.")
    return text


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        _fail("review_contract_invalid", f"{location} must be a boolean.")
    return value


def _integer(value: Any, location: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(
            "review_contract_invalid",
            f"{location} must be an integer greater than or equal to {minimum}.",
        )
    return value


def _nullable_integer(value: Any, location: str) -> int | None:
    if value is None:
        return None
    return _integer(value, location)


def _sha256(value: Any, location: str) -> str:
    text = _nonblank(value, location)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        _fail(
            "review_contract_invalid",
            f"{location} must be a lowercase hexadecimal SHA-256 digest.",
        )
    return text


def _timestamp(value: Any, location: str) -> str:
    text = _nonblank(value, location)
    normalized = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        _fail(
            "review_contract_invalid",
            f"{location} must be an ISO 8601 timestamp with an explicit UTC offset.",
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(
            "review_contract_invalid",
            f"{location} must be an ISO 8601 timestamp with an explicit UTC offset.",
        )
    return text


def _unique_strings(
    value: Any, location: str, *, minimum: int = 0
) -> list[str]:
    values = _array(value, location, minimum=minimum)
    result = [
        _nonblank(item, f"{location}[{index}]")
        for index, item in enumerate(values)
    ]
    if len(set(result)) != len(result):
        _fail("review_contract_invalid", f"{location} must contain unique strings.")
    return result


def _identity(value: Any, location: str, *, receipt: bool) -> dict[str, str]:
    fields = {"provider", "runtime", "model"}
    if receipt:
        fields.add("observed_by")
    identity = _object(value, fields, location)
    result = {
        field: _nonblank(identity[field], f"{location}.{field}")
        for field in ("provider", "runtime", "model")
    }
    if receipt:
        result["observed_by"] = _constant(
            identity["observed_by"], "LAUNCHER", f"{location}.observed_by"
        )
    return result


def _permissions(value: Any, location: str) -> dict[str, str]:
    permissions = _object(value, {"filesystem", "network"}, location)
    return {
        "filesystem": _constant(
            permissions["filesystem"], "READ_ONLY", f"{location}.filesystem"
        ),
        "network": _enum(
            permissions["network"], frozenset({"DENY", "ALLOW"}), f"{location}.network"
        ),
    }


def _independence(value: Any, location: str) -> dict[str, bool]:
    independence = _object(
        value, {"fresh_context", "prior_results_visible"}, location
    )
    return {
        "fresh_context": _boolean(
            independence["fresh_context"], f"{location}.fresh_context"
        ),
        "prior_results_visible": _boolean(
            independence["prior_results_visible"],
            f"{location}.prior_results_visible",
        ),
    }


def _reference(value: Any, location: str) -> dict[str, str]:
    reference = _object(value, {"path", "sha256"}, location)
    return {
        "path": _nonblank(reference["path"], f"{location}.path"),
        "sha256": _sha256(reference["sha256"], f"{location}.sha256"),
    }


def _strict_json_loads(raw: bytes, location: str) -> Any:
    def parse_integer(value: str) -> int:
        digits = value[1:] if value.startswith("-") else value
        if len(digits) > MAX_JSON_INTEGER_DIGITS:
            _fail(
                "review_json_invalid",
                f"{location} contains an oversized integer literal.",
            )
        return int(value)

    def reject_nonstandard_constant(_: str) -> NoReturn:
        _fail(
            "review_json_invalid",
            f"{location} contains a non-standard numeric value.",
        )

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(
                    "review_json_invalid",
                    f"{location} contains a duplicate object field.",
                )
            result[key] = value
        return result

    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_constant,
            parse_int=parse_integer,
        )
    except ReviewGateError:
        raise
    except (RecursionError, ValueError) as error:
        raise ReviewGateError(
            "review_json_invalid", f"{location} is not valid UTF-8 JSON."
        ) from error

    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            try:
                current.encode("utf-8", errors="strict")
            except UnicodeEncodeError as error:
                raise ReviewGateError(
                    "review_json_invalid",
                    f"{location} contains an invalid Unicode scalar.",
                ) from error
        elif isinstance(current, float) and not math.isfinite(current):
            _fail(
                "review_json_invalid",
                f"{location} contains a non-finite numeric value.",
            )
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, dict):
            for key, item in current.items():
                pending.extend((key, item))
    return value


def _load_manifest(bundle_directory: Path) -> dict[str, Any]:
    manifest_path = bundle_directory / "bundle.json"
    try:
        raw = manifest_path.read_bytes()
    except OSError as error:
        raise ReviewGateError(
            "review_bundle_unreadable", "bundle.json could not be read."
        ) from error
    value = _strict_json_loads(raw, "bundle.json")
    manifest = _object(value, {"contract_version", "work_order", "paths"}, "bundle")
    _constant(manifest["contract_version"], MANIFEST_VERSION, "bundle.contract_version")
    manifest["work_order"] = _reference(manifest["work_order"], "bundle.work_order")
    declarations = _array(manifest["paths"], "bundle.paths", minimum=2)
    normalized = []
    ids = []
    for index, raw_declaration in enumerate(declarations):
        location = f"bundle.paths[{index}]"
        declaration = _object(
            raw_declaration,
            {"id", "launcher_identity", "result", "receipt"},
            location,
        )
        path_id = _nonblank(declaration["id"], f"{location}.id")
        ids.append(path_id)
        normalized.append(
            {
                "id": path_id,
                "launcher_identity": _identity(
                    declaration["launcher_identity"],
                    f"{location}.launcher_identity",
                    receipt=False,
                ),
                "result": _reference(declaration["result"], f"{location}.result"),
                "receipt": _reference(declaration["receipt"], f"{location}.receipt"),
            }
        )
    if len(set(ids)) != len(ids):
        _fail("review_contract_invalid", "bundle.paths IDs must be unique.")
    manifest["paths"] = normalized
    return manifest


def _read_references(
    bundle_directory: Path, manifest: dict[str, Any]
) -> dict[str, bytes]:
    references = [manifest["work_order"]]
    for declaration in manifest["paths"]:
        references.extend((declaration["result"], declaration["receipt"]))

    path_values = [reference["path"] for reference in references]
    if len(set(path_values)) != len(path_values):
        _fail("review_path_invalid", "Every bundle reference path must be unique.")

    bundle_root = bundle_directory.resolve()
    raw_by_path: dict[str, bytes] = {}
    file_identities: set[tuple[int, int]] = set()
    mismatches: list[str] = []
    for reference in references:
        relative_text = reference["path"]
        portable = PurePosixPath(relative_text)
        raw_segments = relative_text.split("/")
        if (
            portable.is_absolute()
            or portable.as_posix() != relative_text
            or "\\" in relative_text
            or any(part in {"", ".", ".."} for part in raw_segments)
        ):
            _fail("review_path_invalid", "Bundle references must be safe relative paths.")
        candidate = bundle_root.joinpath(*portable.parts)
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(bundle_root)
        except (OSError, RuntimeError, ValueError) as error:
            raise ReviewGateError(
                "review_path_invalid", "A bundle reference escapes or cannot be read."
            ) from error
        if not resolved.is_file():
            _fail("review_path_invalid", "A bundle reference is not a regular file.")
        try:
            metadata = resolved.stat()
        except OSError as error:
            raise ReviewGateError(
                "review_bundle_unreadable",
                "A referenced bundle file could not be inspected.",
            ) from error
        file_identity = (metadata.st_dev, metadata.st_ino)
        if file_identity in file_identities:
            _fail(
                "review_path_invalid",
                "Bundle references must identify unique regular files.",
            )
        file_identities.add(file_identity)
        try:
            raw = resolved.read_bytes()
        except OSError as error:
            raise ReviewGateError(
                "review_bundle_unreadable", "A referenced bundle file could not be read."
            ) from error
        raw_by_path[relative_text] = raw
        if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            mismatches.append(relative_text)

    # Integrity is checked for every referenced byte string before model-authored
    # result or receipt JSON is parsed.
    if mismatches:
        _fail(
            "review_digest_mismatch",
            f"Referenced file digest mismatch: {', '.join(sorted(mismatches))}.",
        )
    return raw_by_path


def _parse_referenced(raw: bytes, location: str) -> Any:
    return _strict_json_loads(raw, location)


def _validate_work_order(value: Any) -> dict[str, Any]:
    work_order = _object(
        value,
        {
            "contract_version",
            "id",
            "operation",
            "role",
            "goal",
            "acceptance_criteria",
            "constraints",
            "non_goals",
            "artifact",
            "permissions",
            "budget",
            "required_capabilities",
            "required_evidence",
            "independence",
            "review_paths",
            "result_contract",
        },
        "work_order",
    )
    _constant(work_order["contract_version"], WORK_ORDER_VERSION, "work_order.contract_version")
    _nonblank(work_order["id"], "work_order.id")
    _constant(work_order["operation"], "COLD_REVIEW", "work_order.operation")
    _constant(work_order["role"], "REVIEWER", "work_order.role")
    _nonblank(work_order["goal"], "work_order.goal")

    criteria = _array(
        work_order["acceptance_criteria"], "work_order.acceptance_criteria", minimum=1
    )
    criterion_ids = []
    for index, raw_criterion in enumerate(criteria):
        location = f"work_order.acceptance_criteria[{index}]"
        criterion = _object(raw_criterion, {"id", "text"}, location)
        criterion_ids.append(_nonblank(criterion["id"], f"{location}.id"))
        _nonblank(criterion["text"], f"{location}.text")
    if len(set(criterion_ids)) != len(criterion_ids):
        _fail(
            "review_contract_invalid", "work_order acceptance criterion IDs must be unique."
        )

    _unique_strings(work_order["constraints"], "work_order.constraints")
    _unique_strings(work_order["non_goals"], "work_order.non_goals")
    artifact = _object(
        work_order["artifact"],
        {
            "repository_id",
            "base_revision",
            "candidate_revision",
            "snapshot_sha256",
            "paths",
        },
        "work_order.artifact",
    )
    _nonblank(artifact["repository_id"], "work_order.artifact.repository_id")
    _nonblank(artifact["base_revision"], "work_order.artifact.base_revision")
    _nonblank(artifact["candidate_revision"], "work_order.artifact.candidate_revision")
    _sha256(artifact["snapshot_sha256"], "work_order.artifact.snapshot_sha256")
    _unique_strings(artifact["paths"], "work_order.artifact.paths")
    work_order["permissions"] = _permissions(
        work_order["permissions"], "work_order.permissions"
    )
    budget = _object(work_order["budget"], {"wall_seconds"}, "work_order.budget")
    _integer(budget["wall_seconds"], "work_order.budget.wall_seconds", minimum=1)
    work_order["required_capabilities"] = _unique_strings(
        work_order["required_capabilities"], "work_order.required_capabilities"
    )
    work_order["required_evidence"] = _unique_strings(
        work_order["required_evidence"], "work_order.required_evidence"
    )
    work_order["independence"] = _independence(
        work_order["independence"], "work_order.independence"
    )
    if work_order["independence"] != {
        "fresh_context": True,
        "prior_results_visible": False,
    }:
        _fail(
            "review_contract_invalid",
            "The v0 work order must require fresh context and hidden prior results.",
        )
    work_order["review_paths"] = _unique_strings(
        work_order["review_paths"], "work_order.review_paths", minimum=2
    )
    _constant(
        work_order["result_contract"], RESULT_CONTRACT, "work_order.result_contract"
    )
    return work_order


def _validate_result(value: Any, location: str) -> dict[str, Any]:
    result = _object(
        value,
        {
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
        },
        location,
    )
    _constant(result["contract_version"], RESULT_VERSION, f"{location}.contract_version")
    _nonblank(result["work_order_id"], f"{location}.work_order_id")
    _nonblank(result["path_id"], f"{location}.path_id")
    _sha256(result["work_order_sha256"], f"{location}.work_order_sha256")
    _sha256(
        result["artifact_snapshot_sha256"], f"{location}.artifact_snapshot_sha256"
    )
    _enum(result["terminal_status"], TERMINAL_STATUSES, f"{location}.terminal_status")
    _constant(
        result["release_recommendation"],
        "REPORT_ONLY",
        f"{location}.release_recommendation",
    )

    evidence = _array(result["evidence"], f"{location}.evidence")
    evidence_ids = []
    for index, raw_evidence in enumerate(evidence):
        item_location = f"{location}.evidence[{index}]"
        item = _object(raw_evidence, {"id", "requirement", "observation"}, item_location)
        evidence_ids.append(_nonblank(item["id"], f"{item_location}.id"))
        _nonblank(item["requirement"], f"{item_location}.requirement")
        _nonblank(item["observation"], f"{item_location}.observation")
    if len(set(evidence_ids)) != len(evidence_ids):
        _fail("review_contract_invalid", f"{location} evidence IDs must be unique.")

    findings = _array(result["findings"], f"{location}.findings")
    finding_ids = []
    for index, raw_finding in enumerate(findings):
        item_location = f"{location}.findings[{index}]"
        item = _object(
            raw_finding, {"id", "severity", "summary", "evidence_refs"}, item_location
        )
        finding_ids.append(_nonblank(item["id"], f"{item_location}.id"))
        _enum(item["severity"], SEVERITIES, f"{item_location}.severity")
        _nonblank(item["summary"], f"{item_location}.summary")
        references = _unique_strings(
            item["evidence_refs"], f"{item_location}.evidence_refs", minimum=1
        )
        if not set(references).issubset(evidence_ids):
            _fail(
                "review_binding_mismatch",
                f"{item_location} references evidence absent from its result.",
            )
    if len(set(finding_ids)) != len(finding_ids):
        _fail("review_contract_invalid", f"{location} finding IDs must be unique.")
    result["gaps"] = _unique_strings(result["gaps"], f"{location}.gaps")
    result["degradations"] = _unique_strings(
        result["degradations"], f"{location}.degradations"
    )
    return result


def _validate_receipt(value: Any, location: str) -> dict[str, Any]:
    receipt = _object(
        value,
        {
            "contract_version",
            "invocation_id",
            "work_order_id",
            "path_id",
            "identity",
            "native_strategy",
            "capabilities_observed",
            "permissions_observed",
            "independence_observed",
            "bindings",
            "terminal_status",
            "timing",
            "usage",
            "degradations",
        },
        location,
    )
    _constant(receipt["contract_version"], RECEIPT_VERSION, f"{location}.contract_version")
    _nonblank(receipt["invocation_id"], f"{location}.invocation_id")
    _nonblank(receipt["work_order_id"], f"{location}.work_order_id")
    _nonblank(receipt["path_id"], f"{location}.path_id")
    receipt["identity"] = _identity(receipt["identity"], f"{location}.identity", receipt=True)
    _nonblank(receipt["native_strategy"], f"{location}.native_strategy")
    receipt["capabilities_observed"] = _unique_strings(
        receipt["capabilities_observed"], f"{location}.capabilities_observed"
    )
    receipt["permissions_observed"] = _permissions(
        receipt["permissions_observed"], f"{location}.permissions_observed"
    )
    receipt["independence_observed"] = _independence(
        receipt["independence_observed"], f"{location}.independence_observed"
    )
    bindings = _object(
        receipt["bindings"],
        {"work_order_sha256", "artifact_snapshot_sha256", "result_sha256"},
        f"{location}.bindings",
    )
    for key in ("work_order_sha256", "artifact_snapshot_sha256", "result_sha256"):
        _sha256(bindings[key], f"{location}.bindings.{key}")
    _enum(receipt["terminal_status"], TERMINAL_STATUSES, f"{location}.terminal_status")
    timing = _object(receipt["timing"], {"started_at", "elapsed_ms"}, f"{location}.timing")
    _timestamp(timing["started_at"], f"{location}.timing.started_at")
    _integer(timing["elapsed_ms"], f"{location}.timing.elapsed_ms")
    usage = _object(
        receipt["usage"], {"input_tokens", "output_tokens"}, f"{location}.usage"
    )
    _nullable_integer(usage["input_tokens"], f"{location}.usage.input_tokens")
    _nullable_integer(usage["output_tokens"], f"{location}.usage.output_tokens")
    receipt["degradations"] = _unique_strings(
        receipt["degradations"], f"{location}.degradations"
    )
    return receipt


def evaluate_bundle(bundle: Path) -> dict[str, Any]:
    bundle_directory = bundle.expanduser()
    if not bundle_directory.is_dir():
        _fail("review_bundle_unreadable", "The bundle path must be a directory.")
    manifest = _load_manifest(bundle_directory)
    raw_by_path = _read_references(bundle_directory, manifest)

    work_order_ref = manifest["work_order"]
    work_order = _validate_work_order(
        _parse_referenced(raw_by_path[work_order_ref["path"]], "work_order")
    )
    declared_ids = [declaration["id"] for declaration in manifest["paths"]]
    if set(declared_ids) != set(work_order["review_paths"]):
        _fail(
            "review_binding_mismatch",
            "Manifest paths do not match work_order.review_paths.",
        )

    work_order_sha = work_order_ref["sha256"]
    snapshot_sha = work_order["artifact"]["snapshot_sha256"]
    reasons: set[str] = set()
    invocation_ids: set[str] = set()

    for declaration in manifest["paths"]:
        path_id = declaration["id"]
        result_ref = declaration["result"]
        receipt_ref = declaration["receipt"]
        result = _validate_result(
            _parse_referenced(raw_by_path[result_ref["path"]], f"result[{path_id}]"),
            f"result[{path_id}]",
        )
        receipt = _validate_receipt(
            _parse_referenced(raw_by_path[receipt_ref["path"]], f"receipt[{path_id}]"),
            f"receipt[{path_id}]",
        )

        expected_identity = declaration["launcher_identity"]
        observed_identity = {
            key: receipt["identity"][key] for key in ("provider", "runtime", "model")
        }
        binding_values_match = (
            result["work_order_id"] == work_order["id"]
            and receipt["work_order_id"] == work_order["id"]
            and result["path_id"] == path_id
            and receipt["path_id"] == path_id
            and result["work_order_sha256"] == work_order_sha
            and receipt["bindings"]["work_order_sha256"] == work_order_sha
            and result["artifact_snapshot_sha256"] == snapshot_sha
            and receipt["bindings"]["artifact_snapshot_sha256"] == snapshot_sha
            and receipt["bindings"]["result_sha256"] == result_ref["sha256"]
            and receipt["terminal_status"] == result["terminal_status"]
            and receipt["permissions_observed"] == work_order["permissions"]
            and observed_identity == expected_identity
        )
        if not binding_values_match:
            _fail(
                "review_binding_mismatch",
                f"Cross-object binding mismatch for path {path_id}.",
            )
        invocation_id = receipt["invocation_id"]
        if invocation_id in invocation_ids:
            _fail(
                "review_binding_mismatch", "Invocation IDs must be unique across paths."
            )
        invocation_ids.add(invocation_id)

        def hold(reason: str) -> None:
            reasons.add(f"{path_id}:{reason}")

        if result["terminal_status"] != "COMPLETED":
            hold(f"TERMINAL_{result['terminal_status']}")
        if receipt["timing"]["elapsed_ms"] > work_order["budget"]["wall_seconds"] * 1000:
            hold("BUDGET_EXCEEDED")
        if any(
            value.strip().lower() in UNQUALIFIED_IDENTITIES
            for value in observed_identity.values()
        ):
            hold("IDENTITY_UNQUALIFIED")
        if not set(work_order["required_capabilities"]).issubset(
            receipt["capabilities_observed"]
        ):
            hold("REQUIRED_CAPABILITY_MISSING")
        covered_requirements = {item["requirement"] for item in result["evidence"]}
        if not set(work_order["required_evidence"]).issubset(covered_requirements):
            hold("REQUIRED_EVIDENCE_MISSING")
        if receipt["independence_observed"] != work_order["independence"]:
            hold("INDEPENDENCE_NOT_ESTABLISHED")
        if result["findings"]:
            hold("FINDINGS_PRESENT")
        if result["gaps"]:
            hold("GAPS_PRESENT")
        if result["degradations"] or receipt["degradations"]:
            hold("DEGRADATIONS_PRESENT")

    return {
        "verdict": "HOLD" if reasons else "REPORT_ONLY",
        "reason_codes": sorted(reasons),
        "path_ids": sorted(declared_ids),
    }
