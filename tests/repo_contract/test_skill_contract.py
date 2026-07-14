from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return " ".join((ROOT / relative_path).read_text().lower().split())


class SkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.develop = read("plugins/ai-dev-team-v2/skills/develop/SKILL.md")
        cls.review = read("plugins/ai-dev-team-v2/skills/review/SKILL.md")
        cls.usage = read("docs/mvp-usage.md")

    def test_develop_checkpoint_preserves_requirement_supersession(self) -> None:
        for required in (
            "authoritative owner",
            "exact old and new",
            "superseded source or decision",
            "remaining open owner decisions",
            "final value alone is insufficient",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

    def test_independence_preflight_precedes_review_connection(self) -> None:
        preflight = self.review.index("## independence preflight")
        connect = self.review.index("## connect to the task")
        self.assertLess(preflight, connect)

        for required in (
            "before inspecting the artifact or mutating adt state",
            "cross-session or cross-host memory",
            "imported summaries",
            "transcripts",
            "prior findings",
            "suspected locations",
            "severities",
            "proposed fixes",
            "expected conclusions",
            "independence-compromised",
            "/memories",
            "use of existing memories",
            "future memory generation",
            "telling the model to ignore",
            "status` is metadata-only",
            "completion summary",
            "re-apply the independence preflight",
            "before resume, takeover, or artifact inspection",
            "repair validation, not a cold review",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

    def test_review_preserves_task_kind_and_repair_boundary(self) -> None:
        for required in (
            "task_kind",
            "task_kind=develop",
            "do not call `complete`",
            "explicit repair or handoff direction",
            "task_kind=review",
            "standalone review report",
            "no repair-blocking findings or open owner decisions remain",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

        self.assertNotIn("when the review itself is complete, run", self.review)

    def test_usage_documents_cold_review_and_repair_lifecycle(self) -> None:
        for required in (
            "/memories",
            "use of existing memories",
            "future memory generation",
            "exact old and new",
            "superseded source or decision",
            "leave the development task active",
            "explicit repair or handoff",
            "repair validation, not a cold review",
            "omits the goal, checkpoint notes, and completion summary",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.usage)


if __name__ == "__main__":
    unittest.main()
