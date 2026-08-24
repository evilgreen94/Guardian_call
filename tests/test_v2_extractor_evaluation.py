"""Offline tests for the M1.2A V2 extraction evaluator."""

import io
import json
import os
import socket
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.experimental.evaluation_v2 import (
    DifferenceType,
    ExtractionImpact,
    compare_signals,
    match_interaction_acts,
    summarize_benchmark,
)
from guardian.experimental.signals_v2 import (
    ActionTypeV2,
    Actor,
    AssetCategory,
    AssetSubtype,
    ClaimedEntityType,
    ContextType,
    Destination,
    IdentityAssurance,
    IdentityAssuranceContext,
    IdentityPretext,
    InteractionAct,
    KnowledgeCategory,
    ManipulationType,
    ScamSignalsV2,
    SemanticDirection,
    SensitiveAsset,
)
from scripts import v2_extractor_benchmark as benchmark


def act(
    subtype: AssetSubtype = AssetSubtype.OTP,
    *,
    action: ActionTypeV2 = ActionTypeV2.DISCLOSE,
    category: AssetCategory = AssetCategory.SECRET,
    direction: SemanticDirection = SemanticDirection.DIRECT_REQUEST,
    actor: Actor = Actor.USER,
    destination: Destination = Destination.CALLER,
) -> InteractionAct:
    return InteractionAct(
        action=action,
        asset=SensitiveAsset(category, subtype),
        semantic_direction=direction,
        actor=actor,
        destination=destination,
    )


def signals(*acts: InteractionAct) -> ScamSignalsV2:
    return ScamSignalsV2(interaction_acts=tuple(acts))


class TestV2Comparator(unittest.TestCase):
    def test_exact_signals_produce_exact_result(self) -> None:
        expected = signals(act())
        evaluation = compare_signals("exact", expected, expected)
        self.assertEqual(evaluation.status, "EXACT_MATCH")
        self.assertTrue(evaluation.structural_exact)
        self.assertFalse(evaluation.differences)

    def test_reordered_sets_are_exact(self) -> None:
        expected = ScamSignalsV2.from_dict(
            {
                "identity_pretext": {
                    "claims": ["BANK", "TELECOM"],
                    "knowledge_categories": ["NAME", "ADDRESS"],
                },
                "contexts": ["BANKING", "TELECOM"],
                "interaction_acts": [],
                "manipulation": ["URGENCY", "SECRECY"],
            }
        )
        observed = ScamSignalsV2.from_dict(
            {
                "identity_pretext": {
                    "claims": ["TELECOM", "BANK"],
                    "knowledge_categories": ["ADDRESS", "NAME"],
                },
                "contexts": ["TELECOM", "BANKING"],
                "interaction_acts": [],
                "manipulation": ["SECRECY", "URGENCY"],
            }
        )
        self.assertTrue(compare_signals("sets", expected, observed).structural_exact)

    def test_reordered_acts_are_exact(self) -> None:
        first = act(AssetSubtype.OTP)
        second = act(AssetSubtype.PASSWORD)
        evaluation = compare_signals(
            "acts", signals(first, second), signals(second, first)
        )
        self.assertTrue(evaluation.structural_exact)
        self.assertEqual(
            [item.status for item in evaluation.act_comparisons],
            ["EXACT_MATCH", "EXACT_MATCH"],
        )

    def test_missing_and_spurious_acts_are_distinct(self) -> None:
        missing = compare_signals("missing", signals(act()), signals())
        spurious = compare_signals("spurious", signals(), signals(act()))
        self.assertEqual(
            missing.differences[0].difference_type, DifferenceType.MISSING_ACT
        )
        self.assertEqual(
            spurious.differences[0].difference_type, DifferenceType.SPURIOUS_ACT
        )
        self.assertEqual(missing.differences[0].impact, ExtractionImpact.CRITICAL)
        self.assertEqual(spurious.differences[0].impact, ExtractionImpact.CRITICAL)

    def test_one_field_mismatch_is_paired_not_split_into_two_acts(self) -> None:
        expected = signals(act())
        observed = signals(act(direction=SemanticDirection.WARNING))
        evaluation = compare_signals("direction", expected, observed)
        self.assertEqual(len(evaluation.act_comparisons), 1)
        self.assertEqual(evaluation.act_comparisons[0].status, "PARTIAL_MATCH")
        self.assertEqual(
            [item.difference_type for item in evaluation.differences],
            [DifferenceType.SEMANTIC_DIRECTION_MISMATCH],
        )

    def test_direction_flips_are_first_class_and_critical_in_both_directions(self) -> None:
        for expected_direction, observed_direction in (
            (SemanticDirection.DIRECT_REQUEST, SemanticDirection.WARNING),
            (SemanticDirection.WARNING, SemanticDirection.DIRECT_REQUEST),
            (SemanticDirection.DIRECT_REQUEST, SemanticDirection.NEGATION),
            (SemanticDirection.SELF_SERVICE, SemanticDirection.DIRECT_REQUEST),
            (SemanticDirection.DIRECT_REQUEST, SemanticDirection.DISCUSSION),
            (SemanticDirection.HYPOTHETICAL, SemanticDirection.DIRECT_REQUEST),
            (SemanticDirection.DIRECT_REQUEST, SemanticDirection.HISTORICAL),
            (SemanticDirection.THIRD_PARTY, SemanticDirection.DIRECT_REQUEST),
            (SemanticDirection.DIRECT_REQUEST, SemanticDirection.QUESTION),
        ):
            with self.subTest(expected=expected_direction, observed=observed_direction):
                evaluation = compare_signals(
                    "flip",
                    signals(act(direction=expected_direction)),
                    signals(act(direction=observed_direction)),
                )
                difference = evaluation.differences[0]
                self.assertEqual(
                    difference.difference_type,
                    DifferenceType.SEMANTIC_DIRECTION_MISMATCH,
                )
                self.assertEqual(difference.impact, ExtractionImpact.CRITICAL)

    def test_asset_subtype_and_destination_mismatches_are_detected(self) -> None:
        subtype = compare_signals(
            "subtype", signals(act()), signals(act(AssetSubtype.PASSWORD))
        )
        destination = compare_signals(
            "destination",
            signals(act(destination=Destination.CALLER)),
            signals(act(destination=Destination.OFFICIAL_SELF_SERVICE)),
        )
        self.assertEqual(
            subtype.differences[0].difference_type,
            DifferenceType.ASSET_SUBTYPE_MISMATCH,
        )
        self.assertEqual(subtype.differences[0].impact, ExtractionImpact.HIGH)
        self.assertEqual(
            destination.differences[0].difference_type,
            DifferenceType.DESTINATION_MISMATCH,
        )
        self.assertEqual(destination.differences[0].impact, ExtractionImpact.CRITICAL)

    def test_missing_and_spurious_manipulation_preserve_set_diagnostics(self) -> None:
        expected = ScamSignalsV2(
            manipulation=frozenset({ManipulationType.URGENCY})
        )
        observed = ScamSignalsV2(
            manipulation=frozenset({ManipulationType.SECRECY})
        )
        comparison = compare_signals("manipulation", expected, observed)
        set_result = next(
            item for item in comparison.set_comparisons if item.dimension == "manipulation"
        )
        self.assertEqual(set_result.true_positives, ())
        self.assertEqual(set_result.false_negatives, ("URGENCY",))
        self.assertEqual(set_result.false_positives, ("SECRECY",))
        self.assertEqual(set_result.to_dict()["precision"], 0.0)
        self.assertEqual(set_result.to_dict()["recall"], 0.0)
        self.assertEqual(set_result.to_dict()["f1"], 0.0)
        self.assertTrue(
            all(item.impact == ExtractionImpact.MEDIUM for item in set_result.differences)
        )

    def test_identity_knowledge_and_context_differences_are_separate(self) -> None:
        expected = ScamSignalsV2(
            identity_pretext=IdentityPretext(
                claims=frozenset({ClaimedEntityType.BANK}),
                knowledge_categories=frozenset({KnowledgeCategory.NAME}),
            ),
            contexts=frozenset({ContextType.BANKING}),
        )
        observed = ScamSignalsV2(
            identity_pretext=IdentityPretext(
                claims=frozenset({ClaimedEntityType.TELECOM}),
                knowledge_categories=frozenset({KnowledgeCategory.ADDRESS}),
            ),
            contexts=frozenset({ContextType.TELECOM}),
        )
        kinds = {
            item.difference_type
            for item in compare_signals("sets", expected, observed).differences
        }
        self.assertTrue(
            {
                DifferenceType.IDENTITY_CLAIM_MISS,
                DifferenceType.IDENTITY_CLAIM_SPURIOUS,
                DifferenceType.KNOWLEDGE_CATEGORY_MISS,
                DifferenceType.KNOWLEDGE_CATEGORY_SPURIOUS,
                DifferenceType.CONTEXT_MISS,
                DifferenceType.CONTEXT_SPURIOUS,
            }.issubset(kinds)
        )

    def test_identity_assurance_is_compared_only_when_supplied(self) -> None:
        baseline = compare_signals("assurance", ScamSignalsV2(), ScamSignalsV2())
        self.assertIsNone(baseline.assurance_comparison)
        compared = compare_signals(
            "assurance",
            ScamSignalsV2(),
            ScamSignalsV2(),
            expected_assurance=IdentityAssuranceContext(
                IdentityAssurance.VERIFIED_EXTERNALLY
            ),
            observed_assurance=IdentityAssuranceContext(
                IdentityAssurance.UNVERIFIED
            ),
        )
        self.assertFalse(compared.assurance_comparison.exact)
        self.assertTrue(compared.structural_exact)
        self.assertFalse(compared.differences)
        self.assertEqual(
            compared.assurance_comparison.differences[0].impact,
            ExtractionImpact.INFO,
        )

    def test_ambiguity_remains_visible_and_excluded_from_strict_accuracy(self) -> None:
        evaluation = compare_signals(
            "ambiguous", ScamSignalsV2(), ScamSignalsV2(), ambiguity={"present": True}
        )
        self.assertEqual(evaluation.status, "AMBIGUOUS_REFERENCE")
        self.assertTrue(evaluation.structural_exact)
        self.assertTrue(evaluation.excluded_from_strict_accuracy)
        summary = summarize_benchmark((evaluation,)).to_dict()["global"]
        self.assertEqual(summary["scenarios_evaluated"], 1)
        self.assertEqual(summary["strict_scenarios"], 0)
        self.assertEqual(summary["ambiguous_references"], 1)

    def test_serialization_is_deterministic(self) -> None:
        evaluation = compare_signals(
            "stable", signals(act()), signals(act(direction=SemanticDirection.WARNING))
        )
        first = json.dumps(evaluation.to_dict(), sort_keys=True)
        second = json.dumps(evaluation.to_dict(), sort_keys=True)
        self.assertEqual(first, second)


class TestDeterministicMultiActMatching(unittest.TestCase):
    def test_near_equal_candidates_are_order_independent_and_repeatable(self) -> None:
        expected = (
            act(AssetSubtype.OTP),
            act(AssetSubtype.PASSWORD),
            act(AssetSubtype.RECOVERY_CODE),
        )
        observed = (
            act(AssetSubtype.RECOVERY_CODE, actor=Actor.THIRD_PARTY),
            act(AssetSubtype.PASSWORD, direction=SemanticDirection.WARNING),
            act(AssetSubtype.OTP, destination=Destination.OFFICIAL_SELF_SERVICE),
        )
        baseline = [item.to_dict() for item in match_interaction_acts(expected, observed)]
        for expected_order in (expected, tuple(reversed(expected))):
            for observed_order in (observed, tuple(reversed(observed))):
                for _ in range(10):
                    self.assertEqual(
                        [
                            item.to_dict()
                            for item in match_interaction_acts(
                                expected_order, observed_order
                            )
                        ],
                        baseline,
                    )

    def test_exact_matches_are_consumed_before_closer_partial_candidates(self) -> None:
        direct = act(AssetSubtype.OTP)
        warning = act(AssetSubtype.OTP, direction=SemanticDirection.WARNING)
        question = act(AssetSubtype.OTP, direction=SemanticDirection.QUESTION)
        comparisons = match_interaction_acts(
            (warning, direct),
            (question, direct),
        )
        exact = [item for item in comparisons if item.status == "EXACT_MATCH"]
        partial = [item for item in comparisons if item.status == "PARTIAL_MATCH"]
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0].expected, direct)
        self.assertEqual(exact[0].observed, direct)
        self.assertEqual(partial[0].expected, warning)
        self.assertEqual(partial[0].observed, question)

    def test_canonical_tie_breaking_is_stable_for_equal_distances(self) -> None:
        expected = (
            act(AssetSubtype.OTP, direction=SemanticDirection.WARNING),
            act(AssetSubtype.OTP, direction=SemanticDirection.DIRECT_REQUEST),
        )
        observed = (
            act(AssetSubtype.OTP, direction=SemanticDirection.QUESTION),
            act(AssetSubtype.OTP, direction=SemanticDirection.HISTORICAL),
        )
        results = []
        for expected_order in (expected, tuple(reversed(expected))):
            for observed_order in (observed, tuple(reversed(observed))):
                results.append(
                    [item.to_dict() for item in match_interaction_acts(expected_order, observed_order)]
                )
        self.assertTrue(all(result == results[0] for result in results))
        pairs = [
            (
                item["expected"]["semantic_direction"],
                item["observed"]["semantic_direction"],
            )
            for item in results[0]
        ]
        self.assertEqual(
            pairs,
            [
                ("DIRECT_REQUEST", "HISTORICAL"),
                ("WARNING", "QUESTION"),
            ],
        )

    def test_public_contract_contains_semantics_not_matcher_internals(self) -> None:
        evaluation = compare_signals(
            "contract",
            signals(act()),
            signals(act(direction=SemanticDirection.WARNING)),
        ).to_dict()
        serialized = json.dumps(evaluation, sort_keys=True)
        self.assertIn("act_comparisons", evaluation)
        self.assertIn("expected", evaluation["act_comparisons"][0])
        self.assertIn("observed", evaluation["act_comparisons"][0])
        self.assertNotIn("hamming", serialized.lower())
        self.assertNotIn("candidate_index", serialized)
        self.assertNotIn("greedy", serialized.lower())


class TestReplayHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = benchmark.load_corpus()

    def test_all_57_ground_truth_mappings_parse(self) -> None:
        mappings = self.library["v2_mappings"]
        scenarios = {item["id"] for item in self.library["scenarios"]}
        self.assertEqual(len(mappings), 57)
        self.assertEqual(set(mappings), scenarios)
        for mapping in mappings.values():
            ScamSignalsV2.from_dict(mapping["signals"])

    def test_all_16_replay_fixtures_execute(self) -> None:
        self.assertEqual(len(benchmark.REPLAY_FIXTURES), 16)
        results = benchmark.run_replays(benchmark.REPLAY_FIXTURES, self.library)
        self.assertEqual(len(results), 16)
        by_name = {item.fixture.name: item.evaluation for item in results}
        self.assertTrue(by_name["exact"].structural_exact)
        self.assertTrue(by_name["reordered-acts"].structural_exact)
        self.assertEqual(
            by_name["ambiguous-reference"].status, "AMBIGUOUS_REFERENCE"
        )
        self.assertFalse(by_name["multiple-similar-acts"].structural_exact)

    def test_replay_direction_group_contains_both_critical_flip_directions(self) -> None:
        results = benchmark.run_replays(
            benchmark.select_fixtures("semantic-direction"), self.library
        )
        self.assertEqual(len(results), 3)
        for result in results:
            direction_differences = [
                item
                for item in result.evaluation.differences
                if item.difference_type == DifferenceType.SEMANTIC_DIRECTION_MISMATCH
            ]
            self.assertEqual(len(direction_differences), 1)
            self.assertEqual(
                direction_differences[0].impact, ExtractionImpact.CRITICAL
            )

    def test_summary_has_denominators_direction_flips_and_constitutional_groups(self) -> None:
        results = benchmark.run_replays(benchmark.REPLAY_FIXTURES, self.library)
        summary = summarize_benchmark(
            (item.evaluation for item in results),
            benchmark.constitutional_memberships(self.library),
        ).to_dict()
        self.assertEqual(summary["global"]["scenarios_evaluated"], 16)
        self.assertIn("precision_denominator", summary["by_dimension"]["identity"])
        self.assertEqual(
            summary["by_dimension"]["interaction_actions"]["missing_acts"], 2
        )
        self.assertEqual(
            summary["by_dimension"]["interaction_actions"]["spurious_acts"], 1
        )
        self.assertGreater(summary["semantic_direction"]["mismatch"], 0)
        self.assertIn("DIRECT_REQUEST -> WARNING", summary["semantic_direction"]["direction_flips"])
        self.assertTrue({"C1", "C2", "C3"}.issubset(summary["constitutional"]))

    def test_cli_requires_no_key_network_or_gemini_initialization(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(
            socket, "socket", side_effect=AssertionError("network forbidden")
        ), patch.object(guardian, "GeminiSignalExtractor") as gemini, redirect_stdout(output):
            exit_code = benchmark.main(["--replay", "exact"])
        self.assertEqual(exit_code, 0)
        gemini.assert_not_called()
        rendered = output.getvalue()
        self.assertIn("NO GEMINI", rendered)
        self.assertIn("NO NETWORK", rendered)
        self.assertIn("SYNTHETIC OBSERVED SIGNALS", rendered)

    def test_json_cli_output_is_machine_readable_and_deterministic(self) -> None:
        outputs = []
        for _ in range(2):
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(
                    benchmark.main(["--replay", "semantic-direction", "--format", "json"]),
                    0,
                )
            outputs.append(stream.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        payload = json.loads(outputs[0])
        self.assertEqual(payload["benchmark"], benchmark.BANNER[0])
        self.assertEqual(len(payload["replays"]), 3)

    def test_default_output_does_not_include_scenario_text(self) -> None:
        stream = io.StringIO()
        with redirect_stdout(stream):
            benchmark.main(["--replay", "exact"])
        scenario = next(
            item
            for item in self.library["scenarios"]
            if item["id"] == "bank_otp_sophisticated"
        )
        self.assertNotIn(scenario["input"], stream.getvalue())

    def test_experiment_is_not_exported_or_connected_to_production(self) -> None:
        self.assertNotIn("compare_signals", guardian.__all__)
        self.assertFalse(hasattr(guardian, "compare_signals"))
        production_files = (
            "models.py",
            "extractor.py",
            "risk.py",
            "pipeline.py",
            "actions.py",
            "events.py",
            "canary.py",
        )
        for filename in production_files:
            text = (ROOT / "backend" / "guardian" / filename).read_text(encoding="utf-8")
            self.assertNotIn("evaluation_v2", text)


if __name__ == "__main__":
    unittest.main()
