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

    def test_develop_goal_follows_orientation_and_status_before_start(self) -> None:
        orientation = self.develop.index("minimum read-only orientation")
        status = self.develop.index('adt --workspace "$workspace" status')
        contract = self.develop.index("form a compact neutral task contract")
        start = self.develop.index('adt --workspace "$workspace" start')

        self.assertLess(orientation, status)
        self.assertLess(status, contract)
        self.assertLess(contract, start)

        for required in (
            "before any edit",
            "focused read-only inspection",
            "do not ask the owner for facts that can be discovered",
            "for the new-task path",
            "preserved owner intent, corrected factual premises",
            "existing `--goal` value",
            "desired outcome and observable success",
            "constraints and non-goals",
            "verified repository facts",
            "explicit assumptions",
            "authoritative owner decisions, waivers, and unresolved decisions",
            "omit empty parts",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

    def test_develop_goal_excludes_cold_review_contamination(self) -> None:
        goal_contract = self.develop[
            self.develop.index("the durable `goal` must contain only") :
            self.develop.index("set `goal` to this contract")
        ]
        allowed_fields = goal_contract[: goal_contract.index("omit empty parts")]
        exclusions = goal_contract[goal_contract.index("must exclude") :]

        for allowed in (
            "desired outcome and observable success",
            "constraints and non-goals",
            "verified repository facts distinguished from explicit assumptions",
            "authoritative owner decisions, waivers, and unresolved decisions",
        ):
            with self.subTest(allowed=allowed):
                self.assertIn(allowed, allowed_fields)

        for contamination in (
            "prior findings",
            "suspected locations",
            "severities",
            "proposed fixes",
            "expected conclusions",
        ):
            with self.subTest(contamination=contamination):
                self.assertIn(contamination, self.review)
                self.assertIn(contamination, exclusions)

        for excluded in (
            "rejected suggestions",
            "model-selected implementation details",
            "persuasive reasoning",
        ):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, exclusions)

        for required in (
            "may distinguish an owner-proposed solution from the desired outcome",
            "only when the owner explicitly approves an approach",
            "authoritative owner decision",
            "native plan/build consumes this neutral contract",
            "later neutral review or handoff receives only this cold-review-safe portion",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

    def test_develop_contract_keeps_clear_work_low_ceremony(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "same turn",
                "without a questionnaire",
                "approval ritual",
                "invented alternatives",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_develop_contract_preserves_required_owner_input(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "missing required normative input",
                "owner decision materially changes the product or risk",
                "one focused question",
                "before starting state or editing",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_develop_contract_gives_architectural_forks_extra_ceremony(self) -> None:
        for required in (
            "material or hard-to-reverse architectural fork",
            "two genuinely different viable approaches",
            "concrete tradeoffs",
            "recommendation",
            "only this case requires the alternatives ceremony",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

        decision_gate = self.develop.index("material or hard-to-reverse architectural fork")
        start = self.develop.index('adt --workspace "$workspace" start')
        self.assertLess(decision_gate, start)

    def test_develop_contract_separates_facts_from_owner_authority(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "repository evidence may correct a factual premise",
                "never silently replace the owner's desired outcome",
                "ambiguous or infeasible",
                "present the evidence",
                "focused owner decision",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_develop_skips_state_only_when_no_repository_work_remains(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "observable success is already satisfied",
                "no repository work remains",
                "skip state only",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)
            self.assertNotIn("no implementation is needed", surface)

    def test_develop_contract_is_reused_on_resume_and_preserves_exclusions(self) -> None:
        for required in (
            "do not re-form or re-approve",
            "drift or new information invalidates",
            "existing exact supersession checkpoint convention",
            "no new artifact or taxonomy",
            "separate challenge skill, task kind, cli field, schema, workflow, file taxonomy, routing, or release gate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

        for required in (
            "compact neutral task contract",
            "existing `--goal`",
            "do not re-form or re-approve",
            "drift or new information invalidates",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.usage)

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
