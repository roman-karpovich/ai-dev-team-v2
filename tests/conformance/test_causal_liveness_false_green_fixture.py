from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "conformance/fixtures/causal_liveness_false_green.py"
ORACLE = ROOT / "conformance/fixtures/causal_liveness_false_green-oracle.md"


class CausalLivenessFalseGreenFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository = Path(self.temporary_directory.name) / "review-fixture"
        completed = subprocess.run(
            [sys.executable, str(MATERIALIZER), str(self.repository)],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        refs = json.loads(completed.stdout)
        self.base = refs["base"]
        self.candidate = refs["candidate"]
        self.repair = refs["repair"]
        self.environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def checkout(self, revision: str) -> None:
        self.git("checkout", "--quiet", revision)

    def supplied_tests(self, revision: str) -> subprocess.CompletedProcess[str]:
        self.checkout(revision)
        return subprocess.run(
            [sys.executable, "-m", "unittest", "-q"],
            cwd=self.repository,
            env=self.environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def probe(self, revision: str) -> dict[str, dict[str, object]]:
        self.checkout(revision)
        completed = subprocess.run(
            [sys.executable, "probe.py"],
            cwd=self.repository,
            env=self.environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_materializes_a_three_commit_blinded_review_repository(self) -> None:
        self.assertEqual("3", self.git("rev-list", "--count", "--all"))
        self.assertEqual(self.base, self.git("rev-parse", f"{self.candidate}^"))
        self.assertEqual(self.candidate, self.git("rev-parse", f"{self.repair}^"))
        self.assertEqual(
            ["snapshot: repaired", "snapshot: candidate", "snapshot: baseline"],
            self.git("log", "--format=%s", "--all").splitlines(),
        )
        self.assertEqual(
            [
                "REVIEW.md",
                "listener.py",
                "probe.py",
                "reporting.py",
                "runtime.py",
                "test_listener.py",
            ],
            self.git("ls-tree", "-r", "--name-only", self.repair).splitlines(),
        )
        self.assertTrue(ORACLE.is_file())
        self.assertFalse(
            any("oracle" in path.name.lower() for path in self.repository.rglob("*"))
        )

        self.checkout(self.repair)
        review_brief = (self.repository / "REVIEW.md").read_text()
        self.assertIn("observable through the configured reporting path", review_brief)
        self.assertIn("non-zero, supervisor-facing failure outcome", review_brief)
        self.assertIn("preserves the persisted cursor", review_brief)
        self.assertIn("sibling-worker lifecycle and cleanup semantics", review_brief)
        self.assertNotIn("HOLD", review_brief)
        self.assertNotIn("exactly once", review_brief)
        self.assertNotIn("forced exit", review_brief)

        oracle = " ".join(ORACLE.read_text().split())
        self.assertIn("explicit-capture candidate is a false green", oracle)
        self.assertIn("forced-exit repair is also a false green", oracle)

    def test_supplied_candidate_and_repair_tests_are_green(self) -> None:
        candidate_tests = self.supplied_tests(self.candidate)
        self.assertEqual(0, candidate_tests.returncode, candidate_tests.stderr)

        repair_tests = self.supplied_tests(self.repair)
        self.assertEqual(0, repair_tests.returncode, repair_tests.stderr)

    def test_parent_probe_exposes_both_production_boundary_defects(self) -> None:
        baseline = self.probe(self.base)
        candidate = self.probe(self.candidate)
        repair = self.probe(self.repair)

        self.assertEqual(
            {
                "cursor": "cursor-7",
                "exit_code": None,
                "process_alive": True,
                "reports": 0,
                "sibling_cleanup": False,
            },
            baseline["while_blocked"],
        )
        self.assertEqual(
            {
                "cursor": "cursor-7",
                "exit_code": None,
                "process_alive": True,
                "reports": 1,
                "sibling_cleanup": False,
            },
            candidate["while_blocked"],
        )
        self.assertEqual(
            {
                "cursor": "cursor-7",
                "exit_code": 47,
                "process_alive": False,
                "reports": 1,
                "sibling_cleanup": False,
            },
            repair["while_blocked"],
        )

        self.assertEqual(
            {
                "cursor": "cursor-7",
                "exit_code": 31,
                "process_alive": False,
                "reports": 1,
                "sibling_cleanup": True,
            },
            baseline["after_release"],
        )
        self.assertEqual(
            {
                "cursor": "cursor-7",
                "exit_code": 31,
                "process_alive": False,
                "reports": 2,
                "sibling_cleanup": True,
            },
            candidate["after_release"],
        )
        self.assertEqual(repair["while_blocked"], repair["after_release"])


if __name__ == "__main__":
    unittest.main()
