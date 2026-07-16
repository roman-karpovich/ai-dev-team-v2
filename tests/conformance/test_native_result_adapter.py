from __future__ import annotations

import copy
import hashlib
import json
import unittest

from spikes.schema import native_result_adapter


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


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
        self.assertEqual(set(self.result), set(schema["properties"]))
        self.assertEqual(set(self.result), set(schema["required"]))

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
        codex_raw = json.dumps(result, separators=(",", ":")).encode()
        claude_raw = json.dumps(
            {
                "is_error": False,
                "modelUsage": {"claude-opus-4-8": {"outputTokens": 100}},
                "permission_denials": [],
                "structured_output": result,
                "subtype": "success",
                "type": "result",
            },
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
        wrong_path = self.result_for("claude-native")
        missing = self.result_for("codex-native")
        del missing["terminal_status"]

        for result in (dangling, unknown, wrong_path, missing):
            with self.subTest(result=result):
                native_raw = encoded(result)
                with self.assertRaises(native_result_adapter.NativeResultAdapterError):
                    native_result_adapter.normalize_result(
                        "codex-exec-v0",
                        self.work_order_raw,
                        "codex-native",
                        native_raw,
                    )


if __name__ == "__main__":
    unittest.main()
