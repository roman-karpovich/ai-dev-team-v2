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

    def test_develop_preserves_incident_failure_policy_before_start(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        self.assertLess(
            self.develop.index("in an incident or bug fix"),
            self.develop.index('adt --workspace "$workspace" start'),
        )
        self.assertIn(
            "preserve the existing failure policy unless the owner explicitly changes it",
            incident,
        )
        self.assertIn("is normative and never a reversible assumption", incident)
        self.assertIn(
            "inspect targeted history plus runtime and supervisor configuration before changing that boundary",
            incident,
        )

    def test_develop_rederives_incident_causality_without_expanding_failure_policy(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "re-derive the baseline failure mechanism",
            "final production-relevant observer",
            "whether and when that observer is reachable",
            "name that observer",
            "worker, callback, future, command, or framework boundary",
            "production has a later automatic observer",
            "explicit reporting call is not the final observer",
            "every later automatic reporting route",
            "do not infer a timing or termination sla from `fail-fast` or `restart`",
            "normal stack unwinding or cleanup",
            "fate of sibling work",
            "explicit owner decision",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_develop_requires_observed_baseline_before_incident_edits(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "run a safe focused baseline probe",
            "before the first or any further candidate edit",
            "naming an observer or reasoning from source is not a substitute",
            "exact runtime route and measurable outcome",
            "not merely a destination, vendor, or subsystem",
            "mark the causal mechanism unverified",
            "explicitly revised hardening goal",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_develop_incident_gate_is_lifecycle_wide_and_cannot_be_relabelled(self) -> None:
        incident = self.develop[
            self.develop.index("owner-supplied claim of an observed failure") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "owner-supplied claim of an observed failure",
            "regardless of the builder's terminology",
            "only an explicit owner decision may revise",
            "lifecycle-wide",
            "new, resumed, taken-over, and handed-off tasks",
            "before the first or any further candidate edit",
            "qualifying checkpoint evidence",
            "freeze those edits",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_develop_incident_state_persists_investigation_without_authorizing_edits(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "blocks candidate edits, not adt state creation",
            "neutral investigation goal",
            "causal mechanism as unverified",
            "checkpoint the probe plan",
            "state creation never satisfies or bypasses",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_develop_preedit_probe_uses_immutable_terminal_observer_rules(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "identified immutable pre-candidate snapshot",
            "same terminal-boundary validity rules",
            "production entry point",
            "every enabled automatic reporting route",
            "exact aggregate cardinality",
            "copied or handwritten harness",
            "directly installs process or framework hooks",
            "cannot qualify the incident gate",
            "real initialization path",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_incident_gate_rejects_reimplemented_bootstrap_as_production_entry(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "calling the real library function from a harness does not "
                "make the harness the production initialization path",
                "actual repository bootstrap",
                "copying its arguments or configuration",
                "fake terminal transport",
                "supported replacement seam",
                "cannot qualify the incident gate",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_incident_gate_rejects_synthetic_causal_premises(self) -> None:
        for surface in (self.develop, self.usage):
            for required in (
                "matching the reported outward symptoms is not incident reproduction",
                "added causal precondition",
                "independently established as applicable to the reported incident",
                "synthetic hang, timeout, signal, kill, or supervisor action",
                "injected fault may stand in for an established trigger",
                "remains exploratory evidence",
                "cannot qualify the incident gate",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_develop_incident_owner_wait_pauses_without_implicit_goal_revision(self) -> None:
        incident = self.develop[
            self.develop.index("in an incident or bug fix") :
            self.develop.index("for the new-task path")
        ]
        for required in (
            "an answer to an operational fact question is not authorization",
            "explicitly revise the task goal",
            "checkpoint the evidence and then pause the task",
            "never leave an active lease awaiting an owner reply",
        ):
            with self.subTest(required=required):
                self.assertIn(required, incident)

    def test_develop_goal_does_not_promote_counterfactuals_to_facts(self) -> None:
        goal = self.develop[
            self.develop.index("the durable `goal` must contain only") :
            self.develop.index("set `goal` to this contract")
        ]
        for required in (
            "use `verified` only for facts directly observed",
            "concrete inspected repository and applicable runtime evidence",
            "counterfactual claims about concurrency, shutdown, buffering, reporting loss, or sibling fate",
            "remain explicit assumptions until exercised",
            "must not be promoted to verified facts",
            "justify source edits",
            "expand observable success",
        ):
            with self.subTest(required=required):
                self.assertIn(required, goal)

    def test_develop_verification_guardrails_cover_behavior_and_secrets(self) -> None:
        verification = self.develop[
            self.develop.index("for behavior-changing code") :
            self.develop.index("run the smallest relevant verification once")
        ]
        for required in (
            "focused failing test first",
            "narrowest deterministic seam that still includes every load-bearing automatic downstream observer",
            "compare baseline and candidate at the same final observer",
            "complete downstream disposition, reachability, timing, and signal cardinality",
            "signal classification or handled state",
            "persistence, propagation, or process lifecycle",
            "a new mock or log call alone is insufficient evidence",
            "patches capture or flush",
            "aggregate event cardinality",
            "enumerate every enabled reporting route",
            "direct sdk calls, logging integrations, framework hooks, and process hooks",
            "directly invoked handler in the test process is not terminal-boundary evidence",
            "lowest-cost seam that remains discriminating",
            "production entry point when framework bootstrap or process lifecycle is load-bearing",
            "narrower seam's equivalence to every final observer",
            "dependency of the harness does not make a production seam load-bearing",
            "production configuration, public interfaces, or dependencies solely for verification",
            "fake or in-memory transport is acceptable",
            "exact aggregate event cardinality from all enabled routes",
            "`>= 1`, non-empty, and per-route call assertions",
            "partial observability",
            "replaces the mechanism that performs the claimed outcome",
            "real dependency client",
            "hooks or integrations are disabled",
            "never copy a secret-bearing `.env`",
            "minimal dummy non-secret values",
        ):
            self.assertIn(required, verification)
        self.assertNotIn(
            "exercise the production entry point through the terminal process boundary",
            verification,
        )
        self.assertNotIn("aggregate events from both routes", verification)
        self.assertIn("never copy a secret-bearing `.env`", self.review)

    def test_process_global_observer_initialization_is_isolated(self) -> None:
        for surface_name, surface in (
            ("develop", self.develop),
            ("review", self.review),
            ("usage", self.usage),
        ):
            for required in (
                "prove at the measurement point that the observer is active and that the trigger reaches it; "
                "a successful initialization call or initialized registry alone is insufficient",
                "isolate baseline, candidate, and repeated cases from one another: restoring an outward hook "
                "while retaining process-global initialization or integration registry state is not a consistent reset",
                "prefer a fresh process when public teardown cannot restore both consistently; "
                "do not mutate non-public dependency internals to simulate teardown",
            ):
                with self.subTest(surface=surface_name, required=required):
                    self.assertIn(required, surface)

    def test_develop_and_review_search_ready_runtime_before_syntax_only_fallback(self) -> None:
        for surface in (self.develop, self.review):
            for required in (
                "environment associated with another checkout of the same repository",
                "exact focused offline selector",
                "selected worktree's source",
                "syntax-only",
            ):
                with self.subTest(surface=surface[:20], required=required):
                    self.assertIn(required, surface)

    def test_develop_reconsiders_candidate_complexity_before_freeze(self) -> None:
        boundary = self.develop[self.develop.index("## leave a safe boundary") :]
        reconsider = boundary.index("reconsider the whole candidate")
        freeze = boundary.index("freeze the candidate as an immutable range")
        self.assertLess(reconsider, freeze)

        reconsideration = boundary[reconsider:freeze]
        for required in (
            "proof scaffolding and reliance on non-public dependency interfaces",
            "green, discriminating checks establish behavior, not the necessity of incidental machinery",
            "simpler contract-preserving candidate",
            "same accepted proof boundary",
            "reshape to it before freezing",
        ):
            with self.subTest(required=required):
                self.assertIn(required, reconsideration)

    def test_develop_review_gate_is_explicitly_conditional(self) -> None:
        boundary = self.develop[self.develop.index("before asking to commit") :]
        for required in (
            "always state whether independent review ran",
            "missing review blocks completion only when the selected assurance profile, "
            "accepted task contract, or owner requires it",
            "implementation checkpoint",
            "otherwise completion may proceed after proportionate verification",
            "must not imply independent acceptance",
            "trusted, full-cycle, or two-model result",
            "one reviewer is insufficient",
            "material disagreement must be adjudicated",
        ):
            self.assertIn(required, boundary)

    def test_implementation_checkpoint_uses_standalone_cold_review_state(self) -> None:
        develop_boundary = self.develop[self.develop.index("before asking to commit") :]
        for required in (
            "implementation checkpoint",
            "separate review checkout",
            "same immutable range",
            "standalone `kind=review`",
            "neutral `goal`",
        ):
            with self.subTest(surface="develop", required=required):
                self.assertIn(required, develop_boundary)

        review_connection = self.review[
            self.review.index("## connect to the task") :
            self.review.index("## review independently")
        ]
        for required in (
            "open `kind=develop`",
            "stop before reading `context`",
            "separate review checkout",
            "same immutable range",
            "standalone `kind=review`",
            "neutral `goal`",
            "existing open `kind=review`",
            "reviewer-to-reviewer",
        ):
            with self.subTest(surface="review", required=required):
                self.assertIn(required, review_connection)

        for required in (
            "implementation checkpoint",
            "stop before reading `context`",
            "separate review checkout",
            "same immutable range",
            "standalone `kind=review`",
            "neutral `goal`",
        ):
            with self.subTest(surface="usage", required=required):
                self.assertIn(required, self.usage)

    def test_builder_subagents_are_advisory_not_independent_paths(self) -> None:
        boundary = self.develop[self.develop.index("before asking to commit") :]
        for surface_name, surface in (
            ("develop", boundary),
            ("review", self.review),
            ("usage", self.usage),
        ):
            for required in (
                "builder-spawned subagents",
                "active session",
                "may advise",
                "do not count as independent judgment paths",
                "fresh preflighted session",
                "only neutral context",
                "distinct actual models",
            ):
                with self.subTest(surface=surface_name, required=required):
                    self.assertIn(required, surface)

    def test_review_findings_cannot_expand_contract_or_complexity(self) -> None:
        develop_work = self.develop[
            self.develop.index("## work natively") :
            self.develop.index("## leave a safe boundary")
        ]
        for surface_name, surface in (
            ("develop", develop_work),
            ("review", self.review),
            ("usage", self.usage),
        ):
            for required in (
                "evidence about the candidate, not authority",
                "accepted outcome or a repository constraint",
                "adjacent guarantee",
                "owner decision",
                "state",
                "concurrency coordination",
                "non-public dependency behavior",
                "load-bearing for the accepted outcome",
                "discard",
            ):
                with self.subTest(surface=surface_name, required=required):
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

    def test_claude_model_choice_is_manual_and_orthogonal(self) -> None:
        for required in (
            "claude --model claude-opus-4-8",
            "claude --model claude-fable-5",
            "bounded, well-specified, or routine work",
            "highest-complexity, long-horizon, architecture-wide, or high-ambiguity work",
            "host, model, task complexity, and assurance profile are independent",
            "owner's explicit choice overrides",
            "no automatic model router",
            "profiles never route models",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.usage)

        for surface_name, surface in (
            ("usage", self.usage),
            ("develop", self.develop),
            ("review", self.review),
        ):
            with self.subTest(surface=surface_name):
                self.assertIn("if the selected claude model is unavailable", surface)
                self.assertIn("return control to the owner", surface)

    def test_develop_resolves_claude_model_before_repository_work(self) -> None:
        host = self.develop.index("set `host`")
        model = self.develop.index("resolve the claude model boundary")
        orientation = self.develop.index("minimum read-only orientation")
        self.assertLess(host, model)
        self.assertLess(model, orientation)

        for required in (
            "host is not the model",
            "do not infer the model from `--profile`",
            "do not restart merely to downgrade",
            "fresh fable session before adt state",
            "visible opus continuation",
            "actual model",
            "otherwise record `unknown`",
            "execution evidence, not part of `goal`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.develop)

    def test_review_model_boundary_preserves_coldness_and_evidence(self) -> None:
        preflight = self.review.index("## independence preflight")
        model = self.review.index("## resolve the claude model boundary")
        connect = self.review.index("## connect to the task")
        self.assertLess(preflight, model)
        self.assertLess(model, connect)

        for required in (
            "before artifact inspection",
            "switching models after contamination does not restore independence",
            "fresh neutral session",
            "actual model",
            "otherwise record `unknown`",
            "intended model identity or a silent fallback",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.review)

    def test_second_review_keeps_model_evidence_out_of_neutral_handoff(self) -> None:
        for surface_name, surface in (
            ("usage", self.usage),
            ("review", self.review),
        ):
            for required in (
                "reviewer a's model or fallback evidence",
                "until b has fixed its conclusions",
                "disclose and merge a's model or fallback evidence during adjudication",
            ):
                with self.subTest(surface=surface_name, required=required):
                    self.assertIn(required, surface)

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
            "claude_code_disable_auto_memory=1",
            "--no-session-persistence",
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
        self.assertIn("claude_code_disable_auto_memory=1", self.usage)
        self.assertIn("--no-session-persistence", self.usage)

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

    def test_review_rederives_bug_fix_at_the_production_seam(self) -> None:
        review_work = self.review[
            self.review.index("## review independently") :
            self.review.index("## preserve a cold second review")
        ]
        self.assertIn(
            "tests could pass while the requirement remains broken",
            review_work,
        )
        for required in (
            "independently re-derive the failure mechanism from the baseline",
            "compare baseline and candidate at the same production-relevant seam",
            "framework or runtime behavior outside the diff",
            "complete downstream disposition",
            "whether and when the final observer is reachable",
            "concurrency, shutdown, buffering, and framework lifecycle",
            "catches the failure before a terminal observer",
            "all downstream observers and the signal cardinality",
            "signal classification or handled state",
            "baseline already satisfies the claimed outcome",
            "does not reproduce the reported incident",
            "do not invent a historical or configuration explanation",
            "silently reclassify the change as hardening",
            "withhold acceptance",
            "owner explicitly accepts the revised hardening goal and trade-off",
            "disables, replaces, or bypasses a load-bearing mechanism",
            "real dependency client",
            "hooks or integrations are disabled",
            "non-discriminating",
            "unless equivalence is demonstrated",
            "patches capture or flush",
            "aggregate event cardinality",
            "source-only conjecture cannot establish whether the incident reproduces",
            "exact runtime route and measurable outcome",
            "enumerate every enabled reporting route",
            "direct sdk calls, logging integrations, framework hooks, and process hooks",
            "directly invoked handler in the review process is not terminal-boundary evidence",
            "either uses the production entry point",
            "reviewer independently demonstrates equivalence",
            "production-equivalent automatic hooks",
            "dependency of the current harness is not evidence that a production seam is load-bearing",
            "simpler equally discriminating test-only seam",
            "fake or in-memory transport is acceptable",
            "exact aggregate event cardinality from all enabled routes",
            "`>= 1`, non-empty, and per-route call assertions",
            "do not establish absence of duplication or loss",
        ):
            with self.subTest(required=required):
                self.assertIn(required, review_work)
        self.assertNotIn(
            "unless a production-entry-point terminal check",
            review_work,
        )

    def test_single_review_accept_is_not_a_trusted_result(self) -> None:
        boundary = self.review[self.review.index("## record the boundary") :]
        for required in (
            "one judgment path",
            "not a trusted or final acceptance",
            "required independent paths",
            "material disagreement",
            "adjudicated",
            "a verdict must follow its evidence",
            "explicit acceptance criterion is violated",
            "must not downgrade that violation to a follow-up",
            "owner explicitly waives or supersedes the criterion",
            "severity wording or a qualified-pass label",
        ):
            with self.subTest(required=required):
                self.assertIn(required, boundary)

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
