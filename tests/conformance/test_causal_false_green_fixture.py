from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "conformance/fixtures/causal_false_green.py"
ORACLE = ROOT / "conformance/fixtures/causal_false_green-oracle.md"


class CausalFalseGreenFixtureTest(unittest.TestCase):
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
        self.head = refs["head"]
        self.environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def probe(self, revision: str) -> tuple[int, dict[str, object]]:
        self.git("checkout", "--quiet", revision)
        completed = subprocess.run(
            [sys.executable, "runtime.py"],
            cwd=self.repository,
            env=self.environment,
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_materializes_a_two_commit_blinded_review_repository(self) -> None:
        self.assertEqual("2", self.git("rev-list", "--count", "--all"))
        self.assertEqual(self.base, self.git("rev-parse", f"{self.head}^"))
        self.assertEqual(
            ["snapshot: candidate", "snapshot: baseline"],
            self.git("log", "--format=%s", "--all").splitlines(),
        )
        self.assertEqual(
            ["REVIEW.md", "listener.py", "runtime.py", "test_listener.py"],
            self.git("ls-tree", "-r", "--name-only", self.head).splitlines(),
        )
        self.assertTrue(ORACLE.is_file())
        self.assertFalse(
            any(
                "oracle" in path.name.lower()
                for path in self.repository.rglob("*")
            )
        )

        review_brief = (self.repository / "REVIEW.md").read_text()
        self.assertIn("observable through terminal reporting", review_brief)
        self.assertNotIn("exactly one terminal report", review_brief)

        oracle = " ".join(ORACLE.read_text().split())
        self.assertIn("not causal evidence", oracle)
        self.assertIn("already satisfies", oracle)

    def test_green_candidate_test_hides_the_production_regression(self) -> None:
        self.git("checkout", "--quiet", self.head)
        supplied_tests = subprocess.run(
            [sys.executable, "-m", "unittest", "-q"],
            cwd=self.repository,
            env=self.environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(0, supplied_tests.returncode, supplied_tests.stderr)

        baseline_exit, baseline = self.probe(self.base)
        candidate_exit, candidate = self.probe(self.head)

        self.assertEqual(1, baseline_exit)
        self.assertEqual(1, candidate_exit)
        self.assertEqual(1, baseline["terminal_reports"])
        self.assertEqual(2, candidate["terminal_reports"])
        self.assertEqual("cursor-7", baseline["cursor"])
        self.assertEqual("cursor-7", candidate["cursor"])


if __name__ == "__main__":
    unittest.main()
