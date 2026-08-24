"""Offline tests for formal M1.2B orchestration and provenance."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.extractor_v2 import (
    GeminiV2Observation,
    V2ExtractionError,
    V2ExtractionFailureKind,
)
from guardian.experimental.live_benchmark_v2 import (
    FORMAL_LABEL,
    load_corpus,
    load_manifest,
    run_formal_benchmark,
    select_scenario_ids,
)
from guardian.experimental.signals_v2 import ScamSignalsV2


CORPUS_PATH = ROOT / "scenarios" / "m1_adversarial_scenarios.json"
FIXED_TIME = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def observation(signals: ScamSignalsV2, model: str = "gemini-test") -> GeminiV2Observation:
    return GeminiV2Observation(
        signals=signals,
        provider="Gemini",
        requested_model=model,
        returned_model_version="returned-test-version",
        response_id="response-test",
        request_prompt_sha256="1" * 64,
        response_sha256="2" * 64,
        response_bytes=42,
    )


class ExpectedMappingExtractor:
    def __init__(self, library, model="gemini-test"):
        self.model = model
        self.by_text = {
            scenario["input"]: ScamSignalsV2.from_dict(
                library["v2_mappings"][scenario["id"]]["signals"]
            )
            for scenario in library["scenarios"]
        }
        self.calls = []

    def extract(self, text):
        self.calls.append(text)
        return observation(self.by_text[text], self.model)


class SequenceExtractor:
    def __init__(self, values, model="gemini-test"):
        self.model = model
        self.values = list(values)
        self.calls = 0

    def extract(self, text):
        self.calls += 1
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class TestFormalLiveBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_corpus(CORPUS_PATH)
        cls.ids = [item["id"] for item in cls.library["scenarios"]]

    def run_manifest(self, extractor, scenario_ids, directory, existing=None):
        output_root = Path(directory) / "formal"
        output = output_root / "run.json"
        return run_formal_benchmark(
            extractor=extractor,
            library=self.library,
            corpus_path=CORPUS_PATH,
            scenario_ids=scenario_ids,
            output_path=output,
            allowed_output_root=output_root,
            git_commit="a" * 40,
            existing_manifest=existing,
            run_id="run-test",
            clock=lambda: FIXED_TIME,
            sleeper=lambda _: None,
        )

    def test_single_subset_family_principle_and_all_selection(self):
        self.assertEqual(
            select_scenario_ids(self.library, case_ids=(self.ids[0],)),
            (self.ids[0],),
        )
        self.assertEqual(
            select_scenario_ids(self.library, case_ids=(self.ids[1], self.ids[0])),
            (self.ids[1], self.ids[0]),
        )
        self.assertEqual(len(select_scenario_ids(self.library, family="otp_authentication")), 14)
        self.assertEqual(len(select_scenario_ids(self.library, principle="C1")), 15)
        self.assertEqual(len(select_scenario_ids(self.library, all_cases=True)), 57)

    def test_exact_run_persists_structured_evidence_without_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            extractor = ExpectedMappingExtractor(self.library)
            manifest = self.run_manifest(extractor, (self.ids[0],), directory)
            persisted = load_manifest(Path(directory) / "formal" / "run.json")
        self.assertEqual(manifest, persisted)
        self.assertEqual(manifest["label"], FORMAL_LABEL)
        self.assertEqual(manifest["results"][0]["status"], "EXACT_MATCH")
        self.assertEqual(manifest["results"][0]["attempt"], 1)
        self.assertTrue(manifest["run"]["complete"])
        serialized = json.dumps(manifest, ensure_ascii=False)
        scenario = next(item for item in self.library["scenarios"] if item["id"] == self.ids[0])
        self.assertNotIn(scenario["input"], serialized)
        self.assertNotIn("GEMINI_API_KEY", serialized)
        self.assertIn("expected_signals", manifest["results"][0])
        self.assertIn("observed_signals", manifest["results"][0])
        self.assertIn("comparison", manifest["results"][0])

    def test_quota_is_not_compared_and_stops_remaining_cases(self):
        expected_first = ScamSignalsV2.from_dict(
            self.library["v2_mappings"][self.ids[0]]["signals"]
        )
        quota = V2ExtractionError(
            V2ExtractionFailureKind.QUOTA_EXHAUSTED,
            http_status=429,
            provider_code="RESOURCE_EXHAUSTED",
        )
        extractor = SequenceExtractor([observation(expected_first), quota])
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(extractor, tuple(self.ids[:3]), directory)
        self.assertEqual(extractor.calls, 2)
        self.assertEqual([item["status"] for item in manifest["results"]], ["EXACT_MATCH", "QUOTA_EXHAUSTED"])
        self.assertEqual(manifest["unattempted"], [self.ids[2]])
        self.assertEqual(manifest["summary"]["execution"]["semantic_evaluations"], 1)
        self.assertIsNone(manifest["results"][1]["comparison"])

    def test_resume_skips_recorded_results_and_continues_only_unattempted(self):
        quota = V2ExtractionError(V2ExtractionFailureKind.QUOTA_EXHAUSTED, http_status=429)
        with tempfile.TemporaryDirectory() as directory:
            first = self.run_manifest(SequenceExtractor([quota]), tuple(self.ids[:2]), directory)
            expected_second = ScamSignalsV2.from_dict(
                self.library["v2_mappings"][self.ids[1]]["signals"]
            )
            resumed_extractor = SequenceExtractor([observation(expected_second)])
            resumed = self.run_manifest(
                resumed_extractor,
                tuple(self.ids[:2]),
                directory,
                existing=first,
            )
        self.assertEqual(resumed_extractor.calls, 1)
        self.assertEqual(len(resumed["results"]), 2)
        self.assertEqual(resumed["results"][0]["status"], "QUOTA_EXHAUSTED")
        self.assertEqual(resumed["results"][1]["status"], "EXACT_MATCH")
        self.assertTrue(resumed["run"]["complete"])

    def test_resume_rejects_model_or_contract_fingerprint_change(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.run_manifest(
                ExpectedMappingExtractor(self.library), (self.ids[0],), directory
            )
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                self.run_manifest(
                    ExpectedMappingExtractor(self.library, model="different-model"),
                    (self.ids[0],),
                    directory,
                    existing=first,
                )

    def test_output_is_restricted_to_allowed_ignored_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "formal"
            with self.assertRaisesRegex(ValueError, "output must be"):
                run_formal_benchmark(
                    extractor=ExpectedMappingExtractor(self.library),
                    library=self.library,
                    corpus_path=CORPUS_PATH,
                    scenario_ids=(self.ids[0],),
                    output_path=Path(directory) / "outside.json",
                    allowed_output_root=root,
                    git_commit="a" * 40,
                    clock=lambda: FIXED_TIME,
                )

    def test_family_and_constitutional_metrics_reuse_m1_2a_summary(self):
        selected = tuple(self.ids[:4])
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(
                ExpectedMappingExtractor(self.library), selected, directory
            )
        semantic = manifest["summary"]["semantic"]
        self.assertEqual(semantic["global"]["scenarios_evaluated"], 4)
        self.assertIn("constitutional", semantic)
        self.assertIn("otp_authentication", manifest["summary"]["by_family"])
        family = manifest["summary"]["by_family"]["otp_authentication"]
        self.assertIn("by_dimension", family["semantic"])
        self.assertIn("execution", family)
        self.assertIn("C1", manifest["summary"]["by_constitutional_principle"])

    def test_all_57_execute_offline_with_exact_mocked_observations(self):
        extractor = ExpectedMappingExtractor(self.library)
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(extractor, tuple(self.ids), directory)
        self.assertEqual(extractor.calls, [item["input"] for item in self.library["scenarios"]])
        self.assertEqual(len(manifest["results"]), 57)
        self.assertEqual(len(manifest["unattempted"]), 0)
        self.assertTrue(manifest["run"]["complete"])
        self.assertEqual(
            manifest["summary"]["execution"]["status_counts"],
            {"AMBIGUOUS_REFERENCE": 1, "EXACT_MATCH": 56},
        )
        self.assertEqual(
            manifest["summary"]["semantic"]["global"]["strict_scenarios"],
            56,
        )

    def test_production_modules_do_not_import_live_experiment(self):
        for filename in (
            "__init__.py",
            "models.py",
            "extractor.py",
            "risk.py",
            "canary.py",
            "pipeline.py",
            "events.py",
        ):
            text = (ROOT / "backend" / "guardian" / filename).read_text(encoding="utf-8")
            self.assertNotIn("extractor_v2", text)
            self.assertNotIn("live_benchmark_v2", text)


if __name__ == "__main__":
    unittest.main()
