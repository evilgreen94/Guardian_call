"""Offline tests for local Gemma benchmark manifests."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.gemma_extractor_v2 import (  # noqa: E402
    MODEL_TAG,
    GemmaExtractionStatus,
    GemmaV2ExtractionError,
    GemmaV2Observation,
)
from guardian.experimental.gemma_live_benchmark_v2 import (  # noqa: E402
    FORMAL_LABEL,
    deterministic_manifest_json,
    load_corpus,
    load_manifest,
    run_local_benchmark,
    select_scenario_ids,
)
from guardian.experimental.signals_v2 import ScamSignalsV2  # noqa: E402


CORPUS_PATH = ROOT / "scenarios" / "m1_adversarial_scenarios.json"
FIXED_TIME = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def observation(signals: ScamSignalsV2, model: str = MODEL_TAG) -> GemmaV2Observation:
    return GemmaV2Observation(
        signals=signals,
        provider="Ollama",
        requested_model=model,
        returned_model=model,
        prompt_revision="m1.4a-gemma-prompt-v1",
        prompt_sha256="1" * 64,
        schema_revision="m1.2b-schema-v1",
        schema_sha256="2" * 64,
        generation_schema_revision="m1.4a-gemma-generation-schema-v2",
        generation_schema_sha256="4" * 64,
        generation_options={"temperature": 0.0, "num_ctx": 4096},
        response_sha256="3" * 64,
        response_bytes=42,
        done_reason="stop",
        observed_metadata={"done": True},
    )


class ExpectedMappingExtractor:
    def __init__(self, library, model=MODEL_TAG):
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
    def __init__(self, values, model=MODEL_TAG):
        self.model = model
        self.values = list(values)
        self.calls = 0

    def extract(self, text):
        self.calls += 1
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class TestGemmaLocalBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = load_corpus(CORPUS_PATH)
        cls.ids = [item["id"] for item in cls.library["scenarios"]]

    def run_manifest(self, extractor, scenario_ids, directory, existing=None):
        output_root = Path(directory) / "logs"
        output = output_root / "run.json"
        return run_local_benchmark(
            extractor=extractor,
            library=self.library,
            corpus_path=CORPUS_PATH,
            scenario_ids=scenario_ids,
            output_path=output,
            allowed_output_root=output_root,
            git_commit="a" * 40,
            ollama_version="ollama version is 0.0-test",
            ollama_model_digest="sha256:test",
            existing_manifest=existing,
            run_id="run-test",
            clock=lambda: FIXED_TIME,
        )

    def test_selection_requires_case_or_all(self):
        self.assertEqual(
            select_scenario_ids(self.library, case_ids=(self.ids[0],)),
            (self.ids[0],),
        )
        self.assertEqual(len(select_scenario_ids(self.library, all_cases=True)), 57)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            select_scenario_ids(self.library)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            select_scenario_ids(self.library, case_ids=(self.ids[0], self.ids[0]))

    def test_exact_run_persists_sanitized_manifest_without_transcript_or_raw_response(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(
                ExpectedMappingExtractor(self.library), (self.ids[0],), directory
            )
            persisted = load_manifest(Path(directory) / "logs" / "run.json")
        self.assertEqual(manifest, persisted)
        self.assertEqual(manifest["label"], FORMAL_LABEL)
        self.assertEqual(manifest["results"][0]["status"], "EXACT_MATCH")
        self.assertEqual(manifest["results"][0]["extraction_status"], "EXTRACTION_SUCCEEDED")
        serialized = json.dumps(manifest, ensure_ascii=False)
        scenario = next(item for item in self.library["scenarios"] if item["id"] == self.ids[0])
        self.assertNotIn(scenario["input"], serialized)
        self.assertNotIn("response\":", serialized)
        self.assertFalse(manifest["run"]["raw_transcripts_persisted"])
        self.assertFalse(manifest["run"]["raw_model_responses_persisted"])

    def test_extraction_failure_is_not_semantically_compared(self):
        error = GemmaV2ExtractionError(GemmaExtractionStatus.JSON_PARSE_FAILURE)
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(
                SequenceExtractor([error]),
                (self.ids[0],),
                directory,
            )
        result = manifest["results"][0]
        self.assertEqual(result["status"], "JSON_PARSE_FAILURE")
        self.assertIsNone(result["observed_signals"])
        self.assertIsNone(result["comparison"])
        self.assertEqual(manifest["summary"]["execution"]["semantic_evaluations"], 0)

    def test_deterministic_manifest_serialization(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(
                ExpectedMappingExtractor(self.library), (self.ids[0],), directory
            )
        self.assertEqual(
            deterministic_manifest_json(manifest),
            deterministic_manifest_json(json.loads(json.dumps(manifest))),
        )

    def test_output_is_restricted_to_log_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "logs"
            with self.assertRaisesRegex(ValueError, "output must be"):
                run_local_benchmark(
                    extractor=ExpectedMappingExtractor(self.library),
                    library=self.library,
                    corpus_path=CORPUS_PATH,
                    scenario_ids=(self.ids[0],),
                    output_path=Path(directory) / "outside.json",
                    allowed_output_root=root,
                    git_commit="a" * 40,
                    clock=lambda: FIXED_TIME,
                )

    def test_resume_rejects_contract_fingerprint_change(self):
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

    def test_all_57_execute_offline_with_exact_mocked_observations(self):
        extractor = ExpectedMappingExtractor(self.library)
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_manifest(extractor, tuple(self.ids), directory)
        self.assertEqual(extractor.calls, [item["input"] for item in self.library["scenarios"]])
        self.assertEqual(len(manifest["results"]), 57)
        self.assertEqual(
            manifest["summary"]["execution"]["status_counts"],
            {"AMBIGUOUS_REFERENCE": 1, "EXACT_MATCH": 56},
        )

    def test_production_modules_do_not_import_gemma_experiment(self):
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
            self.assertNotIn("gemma_extractor_v2", text)
            self.assertNotIn("gemma_live_benchmark_v2", text)


if __name__ == "__main__":
    unittest.main()
