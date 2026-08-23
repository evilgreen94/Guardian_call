"""Offline tests for the M1 red-team harness; no Gemini or network calls."""

import copy
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from scripts import conversation_simulator as simulator


BASELINE_20_STATUSES = {
    "bank_otp_sophisticated": "PASS",
    "safe_account_transfer": "RISK_MISMATCH",
    "legitimate_bank_notification": "RISK_MISMATCH",
    "isp_card_cvv": "MODEL_GAP",
    "legitimate_isp_sale": "RISK_MISMATCH",
    "microsoft_remote_access": "PASS",
    "legitimate_technical_support": "PASS",
    "social_network_otp_takeover": "MODEL_GAP",
    "social_network_legitimate_warning": "PASS",
    "government_urgent_payment": "PASS",
    "family_emergency_money": "PASS",
    "ecommerce_fake_cancellation": "MODEL_GAP",
    "bizum_payment_app": "MODEL_GAP",
    "crypto_seed_phrase": "MODEL_GAP",
    "gift_card_payment": "MODEL_GAP",
    "recovery_code_takeover": "MODEL_GAP",
    "long_confidence_scam": "MODEL_GAP",
    "private_data_no_dangerous_request": "RISK_MISMATCH",
    "never_share_secrets_control": "PASS",
    "ambiguous_security_digits": "AMBIGUOUS",
}

SEMANTIC_DIRECTIONS = {
    "request",
    "indirect_request",
    "partial_request",
    "negation",
    "question",
    "hypothetical",
    "historical",
    "third_party",
    "self_service",
    "mixed_intent",
    "discussion",
}


class TestAdversarialCorpus(unittest.TestCase):
    """Validate the deterministic oracle contract in the synthetic corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = simulator.load_library()
        cls.scenarios = cls.library["scenarios"]

    def test_library_preserves_baseline_and_expands_to_target_range(self) -> None:
        self.assertGreaterEqual(len(self.scenarios), 50)
        self.assertLessEqual(len(self.scenarios), 60)
        self.assertEqual(len({item["id"] for item in self.scenarios}), len(self.scenarios))
        baseline_ids = {
            item["id"] for item in self.scenarios if item["cohort"] == "baseline_20"
        }
        self.assertEqual(baseline_ids, set(BASELINE_20_STATUSES))

    def test_scenario_classifications_are_explicit(self) -> None:
        for scenario in self.scenarios:
            self.assertIn(scenario["classification"], simulator.CLASSIFICATIONS)

    def test_oracle_signals_use_exact_m0_schema(self) -> None:
        for scenario in self.scenarios:
            simulator.validate_oracle_signals(scenario["expected"]["signals"])

    def test_conversation_never_asserts_identity_verification(self) -> None:
        for scenario in self.scenarios:
            self.assertFalse(scenario["expected"]["signals"]["identity_verified"])

    def test_model_gaps_name_missing_concepts(self) -> None:
        for scenario in self.scenarios:
            gap = scenario["model_gap"]
            self.assertEqual(gap["present"], bool(gap["missing_concepts"]))
            signal_fields = set(scenario["expected"]["signals"])
            self.assertTrue(set(gap["missing_concepts"]).isdisjoint(signal_fields))

    def test_family_and_contrast_metadata_is_valid(self) -> None:
        covered_families = set()
        for scenario in self.scenarios:
            self.assertTrue(scenario["families"])
            self.assertTrue(set(scenario["families"]).issubset(simulator.FAMILIES))
            covered_families.update(scenario["families"])
            self.assertTrue(scenario["contrast"]["group_id"])
            self.assertTrue(scenario["contrast"]["role"])
            self.assertIn(scenario["semantic_direction"], SEMANTIC_DIRECTIONS)
        self.assertEqual(covered_families, set(simulator.FAMILIES))

    def test_constitutional_metadata_is_diagnostic_only_and_valid(self) -> None:
        covered = set()
        for scenario in self.scenarios:
            principles = set(scenario["constitutional_principles"])
            self.assertTrue(principles.issubset(simulator.CONSTITUTIONAL_PRINCIPLES))
            covered.update(principles)
        self.assertEqual(covered, set(simulator.CONSTITUTIONAL_PRINCIPLES))

    def test_ambiguous_cases_do_not_force_expected_outcomes(self) -> None:
        for scenario in self.scenarios:
            if scenario["classification"] == "ambiguous":
                self.assertIsNone(scenario["expected"]["risk_level"])
                self.assertIsNone(scenario["expected"]["canary_decision"])

    def test_credibility_matrix_has_safe_and_dangerous_levels_zero_to_five(self) -> None:
        observed = {
            (item["credibility"]["level"], item["credibility"]["branch"])
            for item in self.scenarios
            if item["credibility"]["level"] is not None
        }
        expected = {
            (level, branch)
            for level in range(6)
            for branch in ("safe", "dangerous")
        }
        self.assertTrue(expected.issubset(observed))

    def test_expansion_is_spanish_first(self) -> None:
        expansion = [
            item for item in self.scenarios if item["cohort"] == "contrastive_expansion_v1"
        ]
        spanish = [item for item in expansion if item["language"] == "es"]
        self.assertGreaterEqual(len(spanish) / len(expansion), 0.75)


class TestOracleEvaluation(unittest.TestCase):
    """Verify oracle classification over the real deterministic M0 pipeline."""

    @classmethod
    def setUpClass(cls) -> None:
        library = simulator.load_library()
        cls.scenarios = {item["id"]: item for item in library["scenarios"]}

    def setUp(self) -> None:
        self.pipeline = simulator.create_pipeline("oracle")

    def test_oracle_pipeline_does_not_initialize_gemini(self) -> None:
        with patch.object(simulator, "GeminiSignalExtractor") as gemini:
            pipeline = simulator.create_pipeline("oracle")
        gemini.assert_not_called()
        self.assertIsNone(pipeline.extractor)

    def test_oracle_main_requires_no_api_key(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(
            simulator, "GeminiSignalExtractor"
        ) as gemini, patch("builtins.input", return_value="/quit"), redirect_stdout(output):
            exit_code = simulator.main(["--mode", "oracle"])
        self.assertEqual(exit_code, 0)
        gemini.assert_not_called()
        self.assertIn("GEMINI NOT INVOKED", output.getvalue())

    def test_otp_oracle_uses_process_signals_event_lifecycle(self) -> None:
        evaluation = simulator.evaluate_oracle_scenario(
            self.pipeline,
            self.scenarios["bank_otp_sophisticated"],
        )
        self.assertEqual(evaluation.status, "PASS")
        self.assertEqual(evaluation.risk_level, "CRITICAL")
        self.assertEqual(evaluation.canary_decision, "ALLOW")
        self.assertEqual(
            evaluation.event_sequence,
            [
                "SIGNAL_DETECTED",
                "RISK_UPDATED",
                "CANARY_EVALUATION",
                "ACTION_ALLOWED",
                "USER_WARNING",
            ],
        )
        self.assertNotIn("INPUT_RECEIVED", evaluation.event_sequence)

    def test_known_cvv_limitation_is_model_gap(self) -> None:
        evaluation = simulator.evaluate_oracle_scenario(
            self.pipeline,
            self.scenarios["isp_card_cvv"],
        )
        self.assertEqual(evaluation.status, "MODEL_GAP")
        self.assertIn("card_security_code_request", evaluation.reason)

    def test_representable_safe_account_case_exposes_risk_mismatch(self) -> None:
        evaluation = simulator.evaluate_oracle_scenario(
            self.pipeline,
            self.scenarios["safe_account_transfer"],
        )
        self.assertEqual(evaluation.status, "RISK_MISMATCH")
        self.assertEqual(evaluation.risk_level, "HIGH")

    def test_ambiguous_case_is_not_forced_to_pass_or_fail(self) -> None:
        evaluation = simulator.evaluate_oracle_scenario(
            self.pipeline,
            self.scenarios["ambiguous_security_digits"],
        )
        self.assertEqual(evaluation.status, "AMBIGUOUS")

    def test_canary_mismatch_is_separate_from_risk_mismatch(self) -> None:
        scenario = copy.deepcopy(self.scenarios["legitimate_technical_support"])
        scenario["expected"]["canary_decision"] = "ALLOW"
        evaluation = simulator.evaluate_oracle_scenario(self.pipeline, scenario)
        self.assertEqual(evaluation.status, "CANARY_MISMATCH")

    def test_full_oracle_baseline_has_stable_diagnostic_counts(self) -> None:
        evaluations = [
            simulator.evaluate_oracle_scenario(self.pipeline, scenario)
            for scenario in self.scenarios.values()
        ]
        self.assertEqual(
            simulator.summarize_oracle(evaluations),
            {
                "PASS": 24,
                "RISK_MISMATCH": 10,
                "CANARY_MISMATCH": 0,
                "MODEL_GAP": 22,
                "AMBIGUOUS": 1,
            },
        )

    def test_original_twenty_oracle_statuses_are_unchanged(self) -> None:
        observed = {}
        for scenario_id in BASELINE_20_STATUSES:
            evaluation = simulator.evaluate_oracle_scenario(
                self.pipeline,
                self.scenarios[scenario_id],
            )
            observed[scenario_id] = evaluation.status
        self.assertEqual(observed, BASELINE_20_STATUSES)

    def test_family_and_constitutional_summaries_reconcile(self) -> None:
        evaluations = [
            simulator.evaluate_oracle_scenario(self.pipeline, scenario)
            for scenario in self.scenarios.values()
        ]
        family_counts = simulator.summarize_memberships(
            evaluations,
            self.scenarios,
            "families",
            simulator.FAMILIES,
        )
        constitutional_counts = simulator.summarize_memberships(
            evaluations,
            self.scenarios,
            "constitutional_principles",
            simulator.CONSTITUTIONAL_PRINCIPLES,
        )
        for summary in (family_counts, constitutional_counts):
            for counts in summary.values():
                status_total = sum(counts[status] for status in simulator.ORACLE_STATUSES)
                self.assertEqual(status_total, counts["CASES"])


class TestExtractionErrorPresentation(unittest.TestCase):
    """Keep provider failures compact without changing production errors."""

    def test_quota_failure_is_classified_for_simulator_display(self) -> None:
        error = simulator.ExtractionError(
            "429 RESOURCE_EXHAUSTED: free tier quota exceeded; verbose SDK detail",
            error_type="NETWORK_ERROR",
        )
        lines = simulator.format_extraction_failure(error)
        self.assertEqual(
            lines,
            [
                "EXTRACTION_FAILED",
                "type: QUOTA_EXHAUSTED",
                "provider: Gemini",
                "risk: NOT_EVALUATED",
                "canary: NOT_EVALUATED",
            ],
        )
        self.assertNotIn("verbose SDK detail", "\n".join(lines))
        self.assertEqual(error.error_type, "NETWORK_ERROR")

    def test_non_quota_error_retains_production_error_type(self) -> None:
        error = simulator.ExtractionError(
            "Connection refused with verbose transport details",
            error_type="NETWORK_ERROR",
        )
        lines = simulator.format_extraction_failure(error)
        self.assertIn("type: NETWORK_ERROR", lines)
        self.assertNotIn("verbose transport details", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
