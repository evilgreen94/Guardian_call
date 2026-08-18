"""Tests for domain events, warning actions, and the M0 deterministic pipeline."""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.actions import execute_warning_action
from guardian.events import EventType, InMemoryEventSink
from guardian.models import (
    ActionType,
    CanaryDecision,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
    ScamSignals,
)
from guardian.pipeline import GuardianPipeline
from guardian.signals import create_signals


class TestEventsAndPipeline(unittest.TestCase):
    """Test suite for event lifecycle and pipeline coordination."""

    def test_canonical_m0_event_lifecycle_allowed(self) -> None:
        """Verify strict sequential lifecycle for authorized warning:

        SIGNAL_DETECTED -> RISK_UPDATED -> CANARY_EVALUATION -> ACTION_ALLOWED -> USER_WARNING
        """
        pipeline = GuardianPipeline()
        sink = InMemoryEventSink()

        signals = create_signals(
            otp_request=True,
            requested_action="share_otp",
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
            financial_context=True,
        )

        result = pipeline.process_signals(signals, event_sink=sink)

        self.assertEqual(result.risk_assessment.level, RiskLevel.CRITICAL)
        self.assertEqual(result.canary_decision.decision, PolicyDecision.ALLOW)
        self.assertIsNotNone(result.warning_event)

        events = sink.get_events()
        event_types = [e.event_type for e in events]

        expected_sequence = [
            EventType.SIGNAL_DETECTED,
            EventType.RISK_UPDATED,
            EventType.CANARY_EVALUATION,
            EventType.ACTION_ALLOWED,
            EventType.USER_WARNING,
        ]
        self.assertEqual(event_types, expected_sequence)

        # Check payload content of USER_WARNING
        warning_event = sink.get_events_by_type(EventType.USER_WARNING)[0]
        self.assertEqual(warning_event.payload["headline"], "POSIBLE ESTAFA")
        self.assertEqual(warning_event.payload["severity"], "CRITICAL")
        self.assertIn("NO DIGA ESE CÓDIGO", warning_event.payload["directives"])

    def test_event_lifecycle_denied_for_normal_input(self) -> None:
        """Verify lifecycle for benign input emits ACTION_DENIED and never emits USER_WARNING:

        SIGNAL_DETECTED -> RISK_UPDATED -> CANARY_EVALUATION -> ACTION_DENIED
        """
        pipeline = GuardianPipeline()
        sink = InMemoryEventSink()

        signals = ScamSignals()
        result = pipeline.process_signals(signals, event_sink=sink)

        self.assertEqual(result.risk_assessment.level, RiskLevel.NORMAL)
        self.assertEqual(result.canary_decision.decision, PolicyDecision.DENY)
        self.assertIsNone(result.warning_event)

        events = sink.get_events()
        event_types = [e.event_type for e in events]

        expected_sequence = [
            EventType.SIGNAL_DETECTED,
            EventType.RISK_UPDATED,
            EventType.CANARY_EVALUATION,
            EventType.ACTION_DENIED,
        ]
        self.assertEqual(event_types, expected_sequence)
        self.assertEqual(len(sink.get_events_by_type(EventType.USER_WARNING)), 0)

    def test_event_lifecycle_denied_for_suspicious_input(self) -> None:
        """Verify SUSPICIOUS risk emits ACTION_DENIED under M0 policy."""
        pipeline = GuardianPipeline()
        sink = InMemoryEventSink()

        signals = create_signals(
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
        )
        result = pipeline.process_signals(signals, event_sink=sink)

        self.assertEqual(result.risk_assessment.level, RiskLevel.SUSPICIOUS)
        self.assertEqual(result.canary_decision.decision, PolicyDecision.DENY)

        event_types = [e.event_type for e in sink.get_events()]
        self.assertIn(EventType.ACTION_DENIED, event_types)
        self.assertNotIn(EventType.USER_WARNING, event_types)

    def test_action_execution_bypassing_canary_raises_permission_error(self) -> None:
        """Architectural boundary: execute_warning_action must fail if Canary did not ALLOW."""
        sink = InMemoryEventSink()
        assessment = RiskAssessment(
            level=RiskLevel.NORMAL,
            reasons=["Normal conversation"],
            contributing_signals=["benign"],
        )
        denied_decision = CanaryDecision(
            action=ActionType.WARN_USER,
            decision=PolicyDecision.DENY,
            reason="Denied by policy",
            risk_level=RiskLevel.NORMAL,
        )

        with self.assertRaises(PermissionError):
            execute_warning_action(
                canary_decision=denied_decision,
                risk_assessment=assessment,
                event_sink=sink,
            )

        self.assertEqual(len(sink.get_events()), 0)

    def test_privacy_no_secret_values_in_emitted_event_payloads(self) -> None:
        """Privacy constraint: Emitted events must contain only structured signals and no secret OTP values."""
        pipeline = GuardianPipeline()
        sink = InMemoryEventSink()

        signals = create_signals(
            otp_request=True,
            requested_action="share_otp",
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
        )

        pipeline.process_signals(signals, event_sink=sink)

        for event in sink.get_events():
            payload_str = str(event.payload).lower()
            # Ensure no mock 6-digit codes or secret credentials exist
            self.assertNotIn("123456", payload_str)
            self.assertNotIn("secret_code", payload_str)


if __name__ == "__main__":
    unittest.main()
