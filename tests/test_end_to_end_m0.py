"""End-to-end integration tests for Milestone 0 (M0).

Validates canonical pipeline flow:
Text → Gemini (Mocked) → ScamSignals → Risk Engine → Canary → USER_WARNING

Also validates the extraction failure lifecycle:
INPUT_RECEIVED → EXTRACTION_FAILED
"""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.events import EventType, InMemoryEventSink
from guardian.extractor import ExtractionError, MockSignalExtractor
from guardian.models import PolicyDecision, RiskLevel, ScamSignals
from guardian.pipeline import GuardianPipeline
from guardian.signals import create_signals


class TestEndToEndM0(unittest.TestCase):
    """End-to-end tests for text-driven Guardian Call M0 pipeline."""

    def test_canonical_m0_fraud_pipeline(self) -> None:
        """Canonical M0 DoD Test:

        Input: 'Tell me the six-digit code you just received.'
        Expected Event Lifecycle:
        INPUT_RECEIVED -> SIGNAL_DETECTED -> RISK_UPDATED (CRITICAL) -> CANARY_EVALUATION -> ACTION_ALLOWED -> USER_WARNING
        """
        canonical_signals = create_signals(
            otp_request=True,
            requested_action="share_otp",
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
            financial_context=True,
        )
        mock_extractor = MockSignalExtractor(signals=canonical_signals)
        pipeline = GuardianPipeline(extractor=mock_extractor)
        sink = InMemoryEventSink()

        text_input = "Tell me the six-digit code you just received."
        result = pipeline.process_text(text_input, event_sink=sink)

        # 1. Assert successful result structure
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.signals)
        self.assertIsNotNone(result.risk_assessment)
        self.assertIsNotNone(result.canary_decision)
        self.assertIsNotNone(result.warning_event)

        # 2. Assert risk and canary outcomes
        self.assertEqual(result.risk_assessment.level, RiskLevel.CRITICAL)
        self.assertEqual(result.canary_decision.decision, PolicyDecision.ALLOW)

        # 3. Assert exact sequential event lifecycle
        events = sink.get_events()
        event_types = [e.event_type for e in events]
        expected_sequence = [
            EventType.INPUT_RECEIVED,
            EventType.SIGNAL_DETECTED,
            EventType.RISK_UPDATED,
            EventType.CANARY_EVALUATION,
            EventType.ACTION_ALLOWED,
            EventType.USER_WARNING,
        ]
        self.assertEqual(event_types, expected_sequence)

        # 4. Assert warning directive content
        warning_payload = result.warning_event.payload
        self.assertEqual(warning_payload["headline"], "POSIBLE ESTAFA")
        self.assertEqual(warning_payload["severity"], "CRITICAL")
        self.assertIn("NO DIGA ESE CÓDIGO", warning_payload["directives"])

    def test_extraction_failure_lifecycle(self) -> None:
        """Extraction Failure Test:

        On extraction failure, processing must stop immediately.
        Expected Event Lifecycle:
        INPUT_RECEIVED -> EXTRACTION_FAILED

        Must NOT emit RISK_UPDATED, must NOT evaluate Canary, must NOT emit USER_WARNING.
        """
        extraction_error = ExtractionError(
            "Gemini response could not be parsed as valid ScamSignals schema",
            error_type="SCHEMA_ERROR",
            raw_response="{corrupted_json",
        )
        mock_extractor = MockSignalExtractor(error=extraction_error)
        pipeline = GuardianPipeline(extractor=mock_extractor)
        sink = InMemoryEventSink()

        result = pipeline.process_text("Unintelligible noisy audio transcript", event_sink=sink)

        # 1. Assert result captures error and does not produce false assessments
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.error_type, "SCHEMA_ERROR")
        self.assertIsNone(result.signals)
        self.assertIsNone(result.risk_assessment)
        self.assertIsNone(result.canary_decision)
        self.assertIsNone(result.warning_event)

        # 2. Assert strict event lifecycle: INPUT_RECEIVED -> EXTRACTION_FAILED
        events = sink.get_events()
        event_types = [e.event_type for e in events]
        self.assertEqual(event_types, [EventType.INPUT_RECEIVED, EventType.EXTRACTION_FAILED])

        # 3. Verify no risk or warning events exist
        self.assertEqual(len(sink.get_events_by_type(EventType.RISK_UPDATED)), 0)
        self.assertEqual(len(sink.get_events_by_type(EventType.CANARY_EVALUATION)), 0)
        self.assertEqual(len(sink.get_events_by_type(EventType.USER_WARNING)), 0)

    def test_legitimate_otp_flow_text_pipeline(self) -> None:
        """Legitimate OTP Text Test:

        Input: 'We sent an authentication code. Please enter it inside the mobile banking app.'
        Expected Event Lifecycle:
        INPUT_RECEIVED -> SIGNAL_DETECTED -> RISK_UPDATED (NORMAL) -> CANARY_EVALUATION -> ACTION_DENIED
        """
        legit_signals = create_signals(
            otp_request=True,
            requested_action="enter_in_app",
            identity_claim="bank",
            identity_verified=True,
            financial_context=True,
        )
        mock_extractor = MockSignalExtractor(signals=legit_signals)
        pipeline = GuardianPipeline(extractor=mock_extractor)
        sink = InMemoryEventSink()

        text_input = "We sent an authentication code. Please enter it inside the mobile banking app."
        result = pipeline.process_text(text_input, event_sink=sink)

        self.assertIsNone(result.error)
        self.assertEqual(result.risk_assessment.level, RiskLevel.NORMAL)
        self.assertEqual(result.canary_decision.decision, PolicyDecision.DENY)
        self.assertIsNone(result.warning_event)

        event_types = [e.event_type for e in sink.get_events()]
        expected_sequence = [
            EventType.INPUT_RECEIVED,
            EventType.SIGNAL_DETECTED,
            EventType.RISK_UPDATED,
            EventType.CANARY_EVALUATION,
            EventType.ACTION_DENIED,
        ]
        self.assertEqual(event_types, expected_sequence)
        self.assertEqual(len(sink.get_events_by_type(EventType.USER_WARNING)), 0)

    def test_missing_extractor_raises_runtime_error(self) -> None:
        """Verify pipeline without configured extractor raises error on process_text."""
        pipeline = GuardianPipeline(extractor=None)
        with self.assertRaises(RuntimeError):
            pipeline.process_text("Any text")


if __name__ == "__main__":
    unittest.main()
