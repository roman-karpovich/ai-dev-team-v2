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
            "memories.use_memories=false",
            "memories.generate_memories=false",
            "before the session starts",
            "one-off",
            "global config",
            "telling the model to ignore",
            "status` is metadata-only",
            "completion summary",
            "re-apply the independence preflight",
            "before resume, takeover, or artifact inspection",
            "repair validation, not a cold review",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

        self.assertNotIn("/memories", self.review)

    def test_reviewer_owns_state_start_after_preflight(self) -> None:
        for required in (
            "must not pre-create",
            "reviewer starts",
            "after the independence preflight",
            "retains the returned lease",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

        preflight = self.review.index("## independence preflight")
        start = self.review.index('adt --workspace "$workspace" start')
        self.assertLess(preflight, start)

    def test_review_requires_an_explicit_immutable_commit_range(self) -> None:
        for required in (
            "resolve `base` and `head` to immutable commit shas",
            'git diff "$base..$head"',
            "never silently use `head^`",
            "explicitly accepts a single-commit scope",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

    def test_review_brief_preserves_requirement_supersession(self) -> None:
        for required in (
            "known owner supersessions",
            "authoritative owner",
            "exact old and new requirement or value",
            "superseded source or decision",
            "do not infer authority from a builder commit message",
            "do not invent precedence",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

        for required in (
            "known owner supersessions",
            "exact old and new requirement or value",
            "superseded source or decision",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.usage)

    def test_review_reuses_only_ready_focused_test_runtimes(self) -> None:
        for required in (
            "existing local image or container",
            "exact focused offline selector",
            "do not install dependencies, build, or pull",
            "broad suite or live-network smoke",
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
            "memories.use_memories=false",
            "memories.generate_memories=false",
            "one-off",
            "before the session starts",
            "do not pre-create adt state",
            "<base>..<head>",
            "exact old and new",
            "superseded source or decision",
            "leave the development task active",
            "explicit repair or handoff",
            "repair validation, not a cold review",
            "omits the goal, checkpoint notes, and completion summary",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.usage)

        self.assertNotIn("/memories", self.usage)


if __name__ == "__main__":
    unittest.main()
