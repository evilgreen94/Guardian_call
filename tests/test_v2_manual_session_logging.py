"""Offline tests for opt-in manual V2 session evidence."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.extractor_v2 import (
    GeminiV2Observation,
    V2ExtractionError,
    V2ExtractionFailureKind,
)
from guardian.experimental.manual_session_v2 import (
    MANUAL_LABEL,
    ManualPersistenceRefused,
    ManualSessionPaths,
    ManualSessionRecorder,
    assert_safe_for_manual_persistence,
    read_jsonl,
)
from guardian.experimental.signals_v2 import ScamSignalsV2
from scripts import v2_manual_exploration as manual_cli


def observation() -> GeminiV2Observation:
    return GeminiV2Observation(
        signals=ScamSignalsV2(),
        provider="Gemini",
        requested_model="gemini-test",
        returned_model_version="returned-test",
        response_id="response-test",
        request_prompt_sha256="1" * 64,
        response_sha256="2" * 64,
        response_bytes=10,
    )


class TestManualSessionRecorder(unittest.TestCase):
    def recorder(self, directory, *, text_log=False):
        root = Path(directory) / "manual-live"
        return ManualSessionRecorder(
            paths=ManualSessionPaths(
                jsonl=root / "session.jsonl",
                text=root / "session.txt" if text_log else None,
            ),
            allowed_root=root,
            session_id="manual-test",
            git_commit="a" * 40,
            requested_model="gemini-test",
            clock=lambda: "2026-08-25T12:00:00Z",
        )

    def test_jsonl_is_opt_in_append_only_and_every_record_is_labelled(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            recorder.start()
            recorder.record_turn(
                turn=1,
                text="Léame los seis números que acaba de recibir.",
                observation=observation(),
            )
            recorder.record_verdict(turn=1, verdict="false_negative")
            recorder.end(turns=1)
            records = read_jsonl(recorder.paths.jsonl)
        self.assertEqual(
            [item["record_type"] for item in records],
            ["session_start", "turn", "operator_verdict", "session_end"],
        )
        self.assertTrue(all(item["label"] == MANUAL_LABEL for item in records))
        self.assertEqual(records[2]["verdict"], "false_negative")
        self.assertEqual(records[2]["evidence_class"], "manual_operator_annotation")

    def test_optional_text_log_has_mandatory_non_benchmark_label(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory, text_log=True)
            recorder.start()
            recorder.record_turn(turn=1, text="Synthetic warning without digits.", observation=observation())
            recorder.end(turns=1)
            rendered = recorder.paths.text.read_text(encoding="utf-8")
        self.assertIn(MANUAL_LABEL, rendered)
        self.assertIn("SYNTHETIC INPUT", rendered)

    def test_provider_failure_is_normalized_without_raw_exception_or_response(self):
        error = V2ExtractionError(
            V2ExtractionFailureKind.PARSE_SCHEMA_FAILURE,
            exception_type="ValueError",
            response_sha256="3" * 64,
            response_bytes=99,
        )
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            recorder.start()
            recorder.record_turn(turn=1, text="Synthetic malformed output case.", error=error)
            record = read_jsonl(recorder.paths.jsonl)[1]
        self.assertEqual(record["status"], "PARSE_SCHEMA_FAILURE")
        self.assertIsNone(record["observed_signals"])
        self.assertNotIn("raw_response", json.dumps(record))

    def test_obvious_sensitive_values_are_refused_before_persistence(self):
        prohibited = (
            "Mi código es 123456",
            "password: hunter2",
            "Authorization: Bearer secret-token",
            "4111 1111 1111 1111",
            "-----BEGIN PRIVATE KEY-----",
        )
        for value in prohibited:
            with self.subTest(value=value):
                with self.assertRaises(ManualPersistenceRefused):
                    assert_safe_for_manual_persistence(value)

        with tempfile.TemporaryDirectory() as directory:
            recorder = self.recorder(directory)
            recorder.start()
            with self.assertRaises(ManualPersistenceRefused):
                recorder.record_turn(turn=1, text="OTP=123456", observation=observation())
            records = read_jsonl(recorder.paths.jsonl)
        self.assertEqual(len(records), 1)

    def test_environment_secrets_are_never_read_into_records(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"GEMINI_API_KEY": "AIza-test-secret-value-should-not-appear"}
        ):
            recorder = self.recorder(directory)
            recorder.start()
            recorder.end(turns=0)
            rendered = recorder.paths.jsonl.read_text(encoding="utf-8")
        self.assertNotIn("AIza-test-secret", rendered)
        self.assertNotIn("GEMINI_API_KEY", rendered)

    def test_paths_cannot_escape_ignored_manual_log_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "manual-live"
            with self.assertRaisesRegex(ValueError, "manual evidence path"):
                ManualSessionRecorder(
                    paths=ManualSessionPaths(Path(directory) / "outside.jsonl"),
                    allowed_root=root,
                    session_id="manual-test",
                    git_commit="a" * 40,
                    requested_model="gemini-test",
                )

    def test_cli_logging_flags_are_explicit_and_separate(self):
        default = manual_cli.parse_args(["--model", "gemini-test"])
        self.assertFalse(default.record_session)
        self.assertFalse(default.text_log)
        recorded = manual_cli.parse_args(
            [
                "--model",
                "gemini-test",
                "--record-session",
                "--text-log",
                "--confirm-synthetic-only",
            ]
        )
        self.assertTrue(recorded.record_session)
        self.assertTrue(recorded.confirm_synthetic_only)

    def test_manual_module_has_no_comparator_or_benchmark_dependency(self):
        source = (
            ROOT / "backend" / "guardian" / "experimental" / "manual_session_v2.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("compare_signals", source)
        self.assertNotIn("summarize_benchmark", source)
        self.assertNotIn("live_benchmark_v2", source)


if __name__ == "__main__":
    unittest.main()
