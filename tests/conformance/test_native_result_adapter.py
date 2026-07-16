from __future__ import annotations

import copy
import hashlib
import json
import unittest

from spikes.schema import native_result_adapter


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


class NativeResultAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work_order = {
            "contract_version": "adt.portable-cold-review-work-order.v0",
            "id": "work-order-001",
            "operation": "COLD_REVIEW",
            "role": "REVIEWER",
            "goal": "Independently review the immutable candidate.",
            "acceptance_criteria": [
                {"id": "criterion-1", "text": "Report evidence-backed defects."}
            ],
            "constraints": ["Do not modify the candidate."],
            "non_goals": ["Do not implement fixes."],
            "artifact": {
                "repository_id": "example/repository",
                "base_revision": "a" * 40,
                "candidate_revision": "b" * 40,
                "snapshot_sha256": "c" * 64,
                "paths": ["src", "tests"],
            },
            "permissions": {"filesystem": "READ_ONLY", "network": "DENY"},
            "budget": {"wall_seconds": 120},
            "required_capabilities": ["SOURCE_INSPECTION", "TEST_EXECUTION"],
            "required_evidence": ["candidate-inspection"],
            "independence": {
                "fresh_context": True,
                "prior_results_visible": False,
            },
            "review_paths": ["codex-native", "claude-native"],
            "result_contract": "ADT_PORTABLE_COLD_REVIEW_RESULT_V0",
        }
        self.work_order_raw = encoded(self.work_order)
        self.work_order_sha256 = hashlib.sha256(self.work_order_raw).hexdigest()
        self.result = {
            "contract_version": "adt.portable-cold-review-result.v0",
            "work_order_id": "work-order-001",
            "path_id": "codex-native",
            "work_order_sha256": self.work_order_sha256,
            "artifact_snapshot_sha256": "c" * 64,
            "terminal_status": "COMPLETED",
            "release_recommendation": "REPORT_ONLY",
            "evidence": [
                {
                    "id": "evidence-1",
                    "requirement": "candidate-inspection",
                    "observation": "Inspected the complete candidate diff.",
                }
            ],
            "findings": [],
            "gaps": [],
            "degradations": [],
        }

    def result_for(self, path_id: str) -> dict[str, object]:
        result = copy.deepcopy(self.result)
        result["path_id"] = path_id
        return result

    def test_projects_the_common_observed_schema_subset(self) -> None:
        schema = json.loads(
            native_result_adapter.project_result_schema(
                self.work_order_raw, "codex-native"
            )
        )

        self.assertNotIn("$schema", schema)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(self.result), set(schema["properties"]))
        self.assertEqual(set(self.result), set(schema["required"]))
        self.assertFalse(
            schema["properties"]["evidence"]["items"]["additionalProperties"]
        )
        self.assertFalse(
            schema["properties"]["findings"]["items"]["additionalProperties"]
        )

        constants: list[dict[str, object]] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                if "const" in value:
                    constants.append(value)
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(schema)
        self.assertGreater(len(constants), 0)
        self.assertTrue(all(constant.get("type") == "string" for constant in constants))

    def test_normalizes_both_native_surfaces_to_identical_bytes(self) -> None:
        result = self.result_for("codex-native")
        result["evidence"][0]["observation"] = "Inspected π, naïve — exact text."
        codex_raw = json.dumps(
            result, ensure_ascii=False, separators=(",", ":")
        ).encode()
        claude_raw = json.dumps(
            {
                "ignored": "😀",
                "is_error": False,
                "modelUsage": {"claude-opus-4-8": {"outputTokens": 100}},
                "permission_denials": [],
                "structured_output": result,
                "subtype": "success",
                "type": "result",
            },
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode()

        normalized_codex = native_result_adapter.normalize_result(
            "codex-exec-v0", self.work_order_raw, "codex-native", codex_raw
        )
        normalized_claude = native_result_adapter.normalize_result(
            "claude-print-v0", self.work_order_raw, "codex-native", claude_raw
        )

        self.assertEqual(encoded(result), normalized_codex)
        self.assertEqual(normalized_codex, normalized_claude)
        self.assertEqual(
            normalized_codex,
            native_result_adapter.normalize_result(
                "codex-exec-v0",
                self.work_order_raw,
                "codex-native",
                codex_raw,
            ),
        )

    def test_rejects_malformed_native_envelopes_and_unknown_surfaces(self) -> None:
        cases = [
            (
                "claude-print-v0",
                b'{"structured_output":{},"structured_output":{}}',
            ),
            ("claude-print-v0", b'{"type":"result"}'),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": False,
                        "structured_output": self.result,
                        "subtype": "success",
                        "type": "result",
                    }
                ).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": False,
                        "permission_denials": {},
                        "structured_output": self.result,
                        "subtype": "success",
                        "type": "result",
                    }
                ).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": False,
                        "structured_output": [],
                        "subtype": "success",
                        "type": "result",
                    }
                ).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": True,
                        "structured_output": self.result,
                        "subtype": "error_max_turns",
                        "type": "result",
                    }
                ).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": False,
                        "structured_output": self.result,
                        "subtype": "success",
                        "type": "not-a-result",
                    }
                ).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(
                    {
                        "is_error": False,
                        "permission_denials": [{"tool": "Bash"}],
                        "structured_output": self.result,
                        "subtype": "success",
                        "type": "result",
                    }
                ).encode(),
            ),
            ("future-surface", encoded(self.result)),
        ]

        for surface, native_raw in cases:
            with self.subTest(surface=surface, native_raw=native_raw):
                with self.assertRaises(native_result_adapter.NativeResultAdapterError):
                    native_result_adapter.normalize_result(
                        surface,
                        self.work_order_raw,
                        "codex-native",
                        native_raw,
                    )

    def test_rejects_each_unsuccessful_claude_terminal_status(self) -> None:
        valid = {
            "is_error": False,
            "permission_denials": [],
            "structured_output": self.result,
            "subtype": "success",
            "type": "result",
        }
        mutations = [
            ("type", None),
            ("type", "not-a-result"),
            ("subtype", None),
            ("subtype", "error_max_turns"),
            ("is_error", None),
            ("is_error", True),
            ("is_error", 0),
        ]

        for field, value in mutations:
            wrapper = copy.deepcopy(valid)
            if value is None:
                del wrapper[field]
            else:
                wrapper[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(
                    native_result_adapter.NativeResultAdapterError
                ) as raised:
                    native_result_adapter.normalize_result(
                        "claude-print-v0",
                        self.work_order_raw,
                        "codex-native",
                        json.dumps(wrapper).encode(),
                    )
                self.assertEqual("native_output_invalid", raised.exception.code)

    def test_rejects_nonstandard_json_anywhere_in_native_input(self) -> None:
        result = self.result_for("codex-native")
        text = json.dumps(result)
        surrogate = self.result_for("codex-native")
        surrogate["evidence"][0]["observation"] = "Invalid \ud800 scalar."
        wrapper = {
            "is_error": False,
            "permission_denials": [],
            "structured_output": result,
            "subtype": "success",
            "type": "result",
        }
        ignored_nan = {**wrapper, "ignored": float("nan")}
        ignored_infinity = {**wrapper, "ignored": float("inf")}
        ignored_surrogate_value = {**wrapper, "ignored": "\ud800"}
        ignored_surrogate_key = {**wrapper, "\ud800": "ignored"}
        overflow = json.dumps({**wrapper, "ignored": 0}).replace(
            '"ignored": 0', '"ignored": 1e9999'
        )
        oversized_integer = json.dumps({**wrapper, "ignored": 0}).replace(
            '"ignored": 0', f'"ignored": {"9" * 5000}'
        )
        cases = [
            ("codex-exec-v0", text.encode("utf-16")),
            ("codex-exec-v0", text.encode("utf-32")),
            (
                "codex-exec-v0",
                json.dumps(surrogate, ensure_ascii=True).encode(),
            ),
            ("claude-print-v0", json.dumps(ignored_nan).encode()),
            ("claude-print-v0", json.dumps(ignored_infinity).encode()),
            (
                "claude-print-v0",
                json.dumps(ignored_surrogate_value, ensure_ascii=True).encode(),
            ),
            (
                "claude-print-v0",
                json.dumps(ignored_surrogate_key, ensure_ascii=True).encode(),
            ),
            ("claude-print-v0", overflow.encode()),
            ("claude-print-v0", oversized_integer.encode()),
        ]

        for surface, native_raw in cases:
            with self.subTest(surface=surface, prefix=native_raw[:8]):
                with self.assertRaises(
                    native_result_adapter.NativeResultAdapterError
                ) as raised:
                    native_result_adapter.normalize_result(
                        surface,
                        self.work_order_raw,
                        "codex-native",
                        native_raw,
                    )
                self.assertEqual("review_json_invalid", raised.exception.code)

    def test_rejects_invalid_work_order_before_projection_or_normalization(
        self,
    ) -> None:
        invalid = copy.deepcopy(self.work_order)
        invalid["permissions"]["filesystem"] = "WRITE"
        invalid_raw = encoded(invalid)

        with self.assertRaises(
            native_result_adapter.NativeResultAdapterError
        ) as projected:
            native_result_adapter.project_result_schema(invalid_raw, "codex-native")
        with self.assertRaises(
            native_result_adapter.NativeResultAdapterError
        ) as normalized:
            native_result_adapter.normalize_result(
                "codex-exec-v0",
                invalid_raw,
                "codex-native",
                encoded(self.result),
            )

        self.assertEqual("review_contract_invalid", projected.exception.code)
        self.assertEqual("review_contract_invalid", normalized.exception.code)

    def test_rejects_review_path_absent_from_work_order(self) -> None:
        with self.assertRaises(
            native_result_adapter.NativeResultAdapterError
        ) as raised:
            native_result_adapter.project_result_schema(
                self.work_order_raw, "undeclared-path"
            )

        self.assertEqual("review_path_unknown", raised.exception.code)

    def test_rejects_invalid_results_and_binding_mismatches(self) -> None:
        dangling = self.result_for("codex-native")
        dangling["findings"] = [
            {
                "id": "finding-1",
                "severity": "HIGH",
                "summary": "A defect.",
                "evidence_refs": ["missing-evidence"],
            }
        ]
        unknown = self.result_for("codex-native")
        unknown["invented"] = "value"
        missing = self.result_for("codex-native")
        del missing["terminal_status"]

        for result in (dangling, unknown, missing):
            with self.subTest(result=result):
                native_raw = encoded(result)
                with self.assertRaises(native_result_adapter.NativeResultAdapterError):
                    native_result_adapter.normalize_result(
                        "codex-exec-v0",
                        self.work_order_raw,
                        "codex-native",
                        native_raw,
                    )

    def test_rejects_each_result_binding_mismatch(self) -> None:
        cases = {
            "work_order_id": "different-order",
            "path_id": "claude-native",
            "work_order_sha256": "d" * 64,
            "artifact_snapshot_sha256": "e" * 64,
        }

        for field, value in cases.items():
            result = self.result_for("codex-native")
            result[field] = value
            with self.subTest(field=field):
                with self.assertRaises(
                    native_result_adapter.NativeResultAdapterError
                ) as raised:
                    native_result_adapter.normalize_result(
                        "codex-exec-v0",
                        self.work_order_raw,
                        "codex-native",
                        encoded(result),
                    )
                self.assertEqual(
                    "native_result_binding_mismatch", raised.exception.code
                )


if __name__ == "__main__":
    unittest.main()
