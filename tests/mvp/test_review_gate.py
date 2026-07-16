from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
ADT = ROOT / "plugins" / "ai-dev-team-v2" / "scripts" / "adt.py"

MANIFEST_VERSION = "adt.portable-cold-review-bundle.v0"
WORK_ORDER_VERSION = "adt.portable-cold-review-work-order.v0"
RESULT_VERSION = "adt.portable-cold-review-result.v0"
RECEIPT_VERSION = "adt.portable-cold-review-receipt.v0"
RESULT_CONTRACT = "ADT_PORTABLE_COLD_REVIEW_RESULT_V0"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class BundleBuilder:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.path_ids = ["path-alpha", "path-beta"]
        self.work_order = {
            "contract_version": WORK_ORDER_VERSION,
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
            "required_evidence": ["candidate-inspection", "focused-tests"],
            "independence": {
                "fresh_context": True,
                "prior_results_visible": False,
            },
            "review_paths": list(self.path_ids),
            "result_contract": RESULT_CONTRACT,
        }
        self.results = {
            path_id: {
                "contract_version": RESULT_VERSION,
                "work_order_id": "work-order-001",
                "path_id": path_id,
                "work_order_sha256": "",
                "artifact_snapshot_sha256": "c" * 64,
                "terminal_status": "COMPLETED",
                "release_recommendation": "REPORT_ONLY",
                "evidence": [
                    {
                        "id": "evidence-inspection",
                        "requirement": "candidate-inspection",
                        "observation": "Inspected the complete candidate diff.",
                    },
                    {
                        "id": "evidence-tests",
                        "requirement": "focused-tests",
                        "observation": "Focused offline tests passed.",
                    },
                ],
                "findings": [],
                "gaps": [],
                "degradations": [],
            }
            for path_id in self.path_ids
        }
        self.receipts = {
            path_id: {
                "contract_version": RECEIPT_VERSION,
                "invocation_id": f"invocation-{path_id}",
                "work_order_id": "work-order-001",
                "path_id": path_id,
                "identity": {
                    "provider": "provider-alpha" if path_id == "path-alpha" else "provider-beta",
                    "runtime": "native-cli",
                    "model": "frontier-model",
                    "observed_by": "LAUNCHER",
                },
                "native_strategy": "native-read-only-review",
                "capabilities_observed": ["SOURCE_INSPECTION", "TEST_EXECUTION"],
                "permissions_observed": {
                    "filesystem": "READ_ONLY",
                    "network": "DENY",
                },
                "independence_observed": {
                    "fresh_context": True,
                    "prior_results_visible": False,
                },
                "bindings": {
                    "work_order_sha256": "",
                    "artifact_snapshot_sha256": "c" * 64,
                    "result_sha256": "",
                },
                "terminal_status": "COMPLETED",
                "timing": {"started_at": "2026-07-16T10:00:00Z", "elapsed_ms": 5000},
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "degradations": [],
            }
            for path_id in self.path_ids
        }

    @staticmethod
    def _encoded(value: object) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def write(self, *, manifest_path_order: list[str] | None = None) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        work_order_raw = self._encoded(self.work_order)
        work_order_sha = _sha256(work_order_raw)
        (self.directory / "work-order.json").write_bytes(work_order_raw)

        declarations = []
        path_order = manifest_path_order or self.path_ids
        for path_id in self.path_ids:
            result = self.results[path_id]
            result["work_order_sha256"] = work_order_sha
            result_raw = self._encoded(result)
            result_sha = _sha256(result_raw)
            result_path = Path("results") / f"{path_id}.json"
            (self.directory / result_path).parent.mkdir(exist_ok=True)
            (self.directory / result_path).write_bytes(result_raw)

            receipt = self.receipts[path_id]
            receipt["bindings"]["work_order_sha256"] = work_order_sha
            receipt["bindings"]["result_sha256"] = result_sha
            receipt_raw = self._encoded(receipt)
            receipt_sha = _sha256(receipt_raw)
            receipt_path = Path("receipts") / f"{path_id}.json"
            (self.directory / receipt_path).parent.mkdir(exist_ok=True)
            (self.directory / receipt_path).write_bytes(receipt_raw)

            declarations.append(
                {
                    "id": path_id,
                    "launcher_identity": {
                        key: receipt["identity"][key]
                        for key in ("provider", "runtime", "model")
                    },
                    "result": {"path": result_path.as_posix(), "sha256": result_sha},
                    "receipt": {"path": receipt_path.as_posix(), "sha256": receipt_sha},
                }
            )

        by_id = {item["id"]: item for item in declarations}
        manifest = {
            "contract_version": MANIFEST_VERSION,
            "work_order": {"path": "work-order.json", "sha256": work_order_sha},
            "paths": [by_id[path_id] for path_id in path_order],
        }
        (self.directory / "bundle.json").write_bytes(self._encoded(manifest))
        return self.directory


class ReviewGateCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "bundle"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _run(
        self,
        bundle: Path | None = None,
        *,
        cwd: Path | None = None,
        expected_code: int = 0,
    ) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(ADT), "review-gate", "--bundle", str(bundle or self.bundle)],
            cwd=cwd or self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            expected_code,
            result.returncode,
            msg=f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
        )
        return json.loads(result.stdout or result.stderr)

    def test_happy_bundle_is_order_independent_and_deterministic(self) -> None:
        first = BundleBuilder(self.bundle)
        first.write(manifest_path_order=["path-beta", "path-alpha"])

        output_one = self._run()
        output_two = self._run()
        self.assertEqual(output_one, output_two)
        self.assertEqual(
            {
                "ok": True,
                "command": "review-gate",
                "verdict": "REPORT_ONLY",
                "reason_codes": [],
                "path_ids": ["path-alpha", "path-beta"],
            },
            output_one,
        )

        second_bundle = self.root / "second-bundle"
        BundleBuilder(second_bundle).write(manifest_path_order=["path-alpha", "path-beta"])
        self.assertEqual(output_one, self._run(second_bundle))

        allowed_network = BundleBuilder(self.root / "allowed-network")
        allowed_network.work_order["permissions"]["network"] = "ALLOW"
        for receipt in allowed_network.receipts.values():
            receipt["permissions_observed"]["network"] = "ALLOW"
        allowed_network.receipts["path-alpha"]["timing"]["elapsed_ms"] = 120000
        allowed_network.write()
        self.assertEqual("REPORT_ONLY", self._run(allowed_network.directory)["verdict"])

    def test_rejects_unknown_fields_at_representative_nesting_levels(self) -> None:
        cases = []

        top = BundleBuilder(self.root / "unknown-manifest")
        top.write()
        manifest_path = top.directory / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["unexpected"] = True
        manifest_path.write_bytes(top._encoded(manifest))
        cases.append(top.directory)

        work_order = BundleBuilder(self.root / "unknown-work-order")
        work_order.work_order["artifact"]["unexpected"] = True
        work_order.write()
        cases.append(work_order.directory)

        result = BundleBuilder(self.root / "unknown-result")
        result.results["path-alpha"]["unexpected"] = True
        result.write()
        cases.append(result.directory)

        receipt = BundleBuilder(self.root / "unknown-receipt")
        receipt.receipts["path-alpha"]["timing"]["unexpected"] = True
        receipt.write()
        cases.append(receipt.directory)

        for bundle in cases:
            with self.subTest(bundle=bundle.name):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_contract_invalid", payload["error"]["code"])

    def test_rejects_missing_fields_wrong_containers_and_invalid_enums(self) -> None:
        missing = BundleBuilder(self.root / "missing-field")
        del missing.work_order["required_evidence"]
        missing.write()

        wrong_container = BundleBuilder(self.root / "wrong-container")
        wrong_container.results["path-alpha"]["evidence"] = {}
        wrong_container.write()

        invalid_enum = BundleBuilder(self.root / "invalid-enum")
        invalid_enum.receipts["path-alpha"]["permissions_observed"]["network"] = "MAYBE"
        invalid_enum.write()

        for bundle in (
            missing.directory,
            wrong_container.directory,
            invalid_enum.directory,
        ):
            with self.subTest(bundle=bundle.name):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_contract_invalid", payload["error"]["code"])

    def test_rejects_unparseable_or_offsetless_receipt_start_time(self) -> None:
        cases = (
            ("unparseable-start", "not-a-timestamp"),
            ("offsetless-start", "2026-07-16T10:00:00"),
        )

        for label, started_at in cases:
            builder = BundleBuilder(self.root / label)
            builder.receipts["path-alpha"]["timing"]["started_at"] = started_at
            builder.write()
            with self.subTest(label=label):
                payload = self._run(builder.directory, expected_code=3)
                self.assertEqual("review_contract_invalid", payload["error"]["code"])

    def test_rejects_policy_weakening_and_invalid_json_substitutes(self) -> None:
        weakened = BundleBuilder(self.root / "weakened-independence")
        weakened.work_order["independence"] = {
            "fresh_context": False,
            "prior_results_visible": True,
        }
        for receipt in weakened.receipts.values():
            receipt["independence_observed"] = copy.deepcopy(
                weakened.work_order["independence"]
            )
        weakened.write()

        integer_boolean = BundleBuilder(self.root / "integer-boolean")
        integer_boolean.work_order["independence"]["fresh_context"] = 1
        integer_boolean.write()

        uppercase_digest = BundleBuilder(self.root / "uppercase-digest")
        uppercase_digest.work_order["artifact"]["snapshot_sha256"] = "C" * 64
        uppercase_digest.write()

        release_upgrade = BundleBuilder(self.root / "release-upgrade")
        release_upgrade.results["path-alpha"]["release_recommendation"] = "PROCEED"
        release_upgrade.write()

        for bundle in (
            weakened.directory,
            integer_boolean.directory,
            uppercase_digest.directory,
            release_upgrade.directory,
        ):
            with self.subTest(bundle=bundle.name):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_contract_invalid", payload["error"]["code"])

    def test_verifies_all_digests_before_parsing_any_result_or_receipt(self) -> None:
        BundleBuilder(self.bundle).write()
        invalid_result = self.bundle / "results" / "path-alpha.json"
        invalid_raw = b"not-json\n"
        invalid_result.write_bytes(invalid_raw)
        manifest_path = self.bundle / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["paths"][0]["result"]["sha256"] = _sha256(invalid_raw)
        manifest_path.write_bytes(BundleBuilder._encoded(manifest))

        # A later reference has a bad seal. The gate must report that integrity
        # error before it attempts to parse the earlier, correctly sealed bytes.
        (self.bundle / "results" / "path-beta.json").write_text("tampered\n")

        payload = self._run(expected_code=3)

        self.assertEqual("review_digest_mismatch", payload["error"]["code"])

    def test_rejects_escaping_absolute_and_duplicate_reference_paths(self) -> None:
        for label, replacement in (
            ("parent", str(PurePosixPath("..") / "outside.json")),
            ("absolute", str(self.root / "outside.json")),
            ("backslash", "..\\outside.json"),
            ("current", "results/./path-alpha.json"),
            ("empty-segment", "results//path-alpha.json"),
        ):
            builder = BundleBuilder(self.root / label)
            builder.write()
            manifest_path = builder.directory / "bundle.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["paths"][0]["result"]["path"] = replacement
            manifest_path.write_bytes(builder._encoded(manifest))
            with self.subTest(label=label):
                payload = self._run(builder.directory, expected_code=3)
                self.assertEqual("review_path_invalid", payload["error"]["code"])

        duplicate = BundleBuilder(self.root / "duplicate")
        duplicate.write()
        manifest_path = duplicate.directory / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["paths"][1]["result"] = copy.deepcopy(manifest["paths"][0]["result"])
        manifest_path.write_bytes(duplicate._encoded(manifest))
        payload = self._run(duplicate.directory, expected_code=3)
        self.assertEqual("review_path_invalid", payload["error"]["code"])

        alias = BundleBuilder(self.root / "resolved-alias")
        alias.write()
        alias_path = alias.directory / "result-alias.json"
        alias_path.symlink_to(Path("results") / "path-alpha.json")
        manifest_path = alias.directory / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["paths"][1]["result"] = {
            "path": "result-alias.json",
            "sha256": manifest["paths"][0]["result"]["sha256"],
        }
        manifest_path.write_bytes(alias._encoded(manifest))
        payload = self._run(alias.directory, expected_code=3)
        self.assertEqual("review_path_invalid", payload["error"]["code"])

        hardlink = BundleBuilder(self.root / "hardlink-alias")
        hardlink.write()
        hardlink_path = hardlink.directory / "result-hardlink.json"
        os.link(
            hardlink.directory / "results" / "path-alpha.json",
            hardlink_path,
        )
        manifest_path = hardlink.directory / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["paths"][1]["result"] = {
            "path": hardlink_path.name,
            "sha256": manifest["paths"][0]["result"]["sha256"],
        }
        manifest_path.write_bytes(hardlink._encoded(manifest))
        payload = self._run(hardlink.directory, expected_code=3)
        self.assertEqual("review_path_invalid", payload["error"]["code"])

    def test_rejects_path_set_and_cross_object_binding_mismatches(self) -> None:
        path_set = BundleBuilder(self.root / "path-set")
        path_set.work_order["review_paths"] = ["path-alpha", "different-path"]
        path_set.write()

        binding = BundleBuilder(self.root / "binding")
        binding.results["path-alpha"]["artifact_snapshot_sha256"] = "d" * 64
        binding.write()

        terminal = BundleBuilder(self.root / "terminal")
        terminal.receipts["path-alpha"]["terminal_status"] = "FAILED"
        terminal.write()

        permission = BundleBuilder(self.root / "permission")
        permission.receipts["path-alpha"]["permissions_observed"]["network"] = "ALLOW"
        permission.write()

        invocation = BundleBuilder(self.root / "invocation")
        invocation.receipts["path-beta"]["invocation_id"] = invocation.receipts[
            "path-alpha"
        ]["invocation_id"]
        invocation.write()

        for bundle in (
            path_set.directory,
            binding.directory,
            terminal.directory,
            permission.directory,
            invocation.directory,
        ):
            with self.subTest(bundle=bundle.name):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_binding_mismatch", payload["error"]["code"])

    def test_launcher_identity_mismatch_is_invalid_but_unknown_identity_holds(self) -> None:
        mismatch = BundleBuilder(self.root / "identity-mismatch")
        mismatch.write()
        manifest_path = mismatch.directory / "bundle.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["paths"][0]["launcher_identity"]["model"] = "different-model"
        manifest_path.write_bytes(mismatch._encoded(manifest))
        payload = self._run(mismatch.directory, expected_code=3)
        self.assertEqual("review_binding_mismatch", payload["error"]["code"])

        unknown = BundleBuilder(self.root / "identity-unknown")
        unknown.receipts["path-alpha"]["identity"]["model"] = "UNKNOWN"
        unknown.write()
        payload = self._run(unknown.directory, expected_code=5)
        self.assertFalse(payload["ok"])
        self.assertEqual("HOLD", payload["verdict"])
        self.assertIn("path-alpha:IDENTITY_UNQUALIFIED", payload["reason_codes"])

    def test_missing_capability_or_evidence_holds_and_dangling_reference_is_invalid(self) -> None:
        capability = BundleBuilder(self.root / "capability")
        capability.receipts["path-alpha"]["capabilities_observed"] = ["SOURCE_INSPECTION"]
        capability.write()

        evidence = BundleBuilder(self.root / "evidence")
        evidence.results["path-alpha"]["evidence"] = [
            evidence.results["path-alpha"]["evidence"][0]
        ]
        evidence.write()

        for bundle, reason in (
            (capability.directory, "path-alpha:REQUIRED_CAPABILITY_MISSING"),
            (evidence.directory, "path-alpha:REQUIRED_EVIDENCE_MISSING"),
        ):
            with self.subTest(bundle=bundle.name):
                payload = self._run(bundle, expected_code=5)
                self.assertFalse(payload["ok"])
                self.assertEqual("HOLD", payload["verdict"])
                self.assertIn(reason, payload["reason_codes"])

        dangling = BundleBuilder(self.root / "dangling")
        dangling.results["path-alpha"]["findings"] = [
            {
                "id": "finding-1",
                "severity": "HIGH",
                "summary": "A defect with a nonexistent evidence reference.",
                "evidence_refs": ["missing-evidence"],
            }
        ]
        dangling.write()
        payload = self._run(dangling.directory, expected_code=3)
        self.assertEqual("review_binding_mismatch", payload["error"]["code"])

    def test_semantic_concerns_hold_instead_of_emitting_a_release_decision(self) -> None:
        def finding(builder: BundleBuilder) -> None:
            builder.results["path-alpha"]["findings"] = [
                {
                    "id": "finding-1",
                    "severity": "LOW",
                    "summary": "Even a low-severity finding holds in v0.",
                    "evidence_refs": ["evidence-inspection"],
                }
            ]

        def gap(builder: BundleBuilder) -> None:
            builder.results["path-alpha"]["gaps"] = ["Could not inspect generated code."]

        def degradation(builder: BundleBuilder) -> None:
            builder.receipts["path-alpha"]["degradations"] = ["Usage was estimated."]

        def incomplete(builder: BundleBuilder) -> None:
            builder.results["path-alpha"]["terminal_status"] = "CANCELLED"
            builder.receipts["path-alpha"]["terminal_status"] = "CANCELLED"

        def budget(builder: BundleBuilder) -> None:
            builder.receipts["path-alpha"]["timing"]["elapsed_ms"] = 120001

        def independence(builder: BundleBuilder) -> None:
            builder.receipts["path-alpha"]["independence_observed"]["fresh_context"] = False

        def prior_result_visible(builder: BundleBuilder) -> None:
            builder.receipts["path-alpha"]["independence_observed"][
                "prior_results_visible"
            ] = True

        cases = (
            ("finding", finding, "path-alpha:FINDINGS_PRESENT"),
            ("gap", gap, "path-alpha:GAPS_PRESENT"),
            ("degradation", degradation, "path-alpha:DEGRADATIONS_PRESENT"),
            ("incomplete", incomplete, "path-alpha:TERMINAL_CANCELLED"),
            ("budget", budget, "path-alpha:BUDGET_EXCEEDED"),
            ("independence", independence, "path-alpha:INDEPENDENCE_NOT_ESTABLISHED"),
            (
                "prior-result-visible",
                prior_result_visible,
                "path-alpha:INDEPENDENCE_NOT_ESTABLISHED",
            ),
        )
        for label, mutate, reason in cases:
            builder = BundleBuilder(self.root / label)
            mutate(builder)
            builder.write()
            with self.subTest(label=label):
                payload = self._run(builder.directory, expected_code=5)
                self.assertFalse(payload["ok"])
                self.assertEqual("HOLD", payload["verdict"])
                self.assertIn(reason, payload["reason_codes"])
                self.assertNotIn("PROCEED", json.dumps(payload))
                self.assertNotIn("ACCEPT", json.dumps(payload))
                self.assertNotIn("NEEDS_DECISION", json.dumps(payload))

    def test_runs_outside_git_without_creating_task_state(self) -> None:
        BundleBuilder(self.bundle).write()
        non_git = self.root / "non-git"
        non_git.mkdir()

        payload = self._run(cwd=non_git)

        self.assertEqual("REPORT_ONLY", payload["verdict"])
        self.assertFalse((non_git / ".git").exists())
        self.assertEqual([], list(self.root.rglob("state.json")))

    def test_internal_review_gate_failure_uses_stateless_diagnostic(self) -> None:
        standalone = self.root / "standalone-adt.py"
        standalone.write_bytes(ADT.read_bytes())

        result = subprocess.run(
            [sys.executable, str(standalone), "review-gate", "--bundle", str(self.bundle)],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(4, result.returncode)
        payload = json.loads(result.stderr)
        self.assertEqual("internal_error", payload["error"]["code"])
        self.assertEqual(
            "The review gate failed before it could produce a verdict.",
            payload["error"]["message"],
        )

    def test_invalid_json_exits_nonzero(self) -> None:
        self.bundle.mkdir()
        (self.bundle / "bundle.json").write_text("not-json\n")

        payload = self._run(expected_code=3)

        self.assertEqual("review_json_invalid", payload["error"]["code"])

    def test_rejects_non_utf8_json(self) -> None:
        for encoding in ("utf-16", "utf-32"):
            bundle = self.root / encoding
            bundle.mkdir()
            (bundle / "bundle.json").write_bytes("{}".encode(encoding))

            with self.subTest(encoding=encoding):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_json_invalid", payload["error"]["code"])

    def test_rejects_nonstandard_json_scalars_before_contract_validation(self) -> None:
        cases = {
            "nan": b'{"ignored":NaN}',
            "infinity": b'{"ignored":Infinity}',
            "negative-infinity": b'{"ignored":-Infinity}',
            "overflow": b'{"ignored":1e9999}',
            "oversized-integer": ('{"ignored":' + "9" * 5000 + "}").encode(),
            "surrogate-value": b'{"ignored":"\\ud800"}',
            "surrogate-key": b'{"\\ud800":null}',
        }

        for name, raw in cases.items():
            bundle = self.root / name
            bundle.mkdir()
            (bundle / "bundle.json").write_bytes(raw)

            with self.subTest(name=name):
                payload = self._run(bundle, expected_code=3)
                self.assertEqual("review_json_invalid", payload["error"]["code"])

    def test_duplicate_json_object_key_is_invalid(self) -> None:
        BundleBuilder(self.bundle).write()
        manifest_path = self.bundle / "bundle.json"
        raw = manifest_path.read_text()
        field = f'  "contract_version": "{MANIFEST_VERSION}",\n'
        self.assertIn(field, raw)
        manifest_path.write_text(raw.replace(field, field + field, 1))

        payload = self._run(expected_code=3)

        self.assertEqual("review_json_invalid", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
