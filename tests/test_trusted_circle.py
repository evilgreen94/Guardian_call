"""Unit and integration tests for Trusted Circle Notifications (US6)."""

import pytest
from unittest.mock import MagicMock, patch

from backend.guardian.canary import CanaryPolicy
from backend.guardian.events import EventType, InMemoryEventSink
from backend.guardian.models import (
    ActionType,
    CanaryDecision,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
)
from backend.guardian.trusted_circle import (
    TrustedCircleNotificationError,
    TrustedCircleNotifier,
    execute_trusted_circle_notification,
)


def test_trusted_circle_notifier_format_payload():
    """Verify notification payload contains risk level and reasons without raw text."""
    notifier = TrustedCircleNotifier(webhook_url="https://api.example.com/trusted-circle-webhook")

    risk = RiskAssessment(
        level=RiskLevel.CRITICAL,
        reasons=["Demanda urgente de código SMS/OTP", "Solicitud de transferencia bancaria"],
        contributing_signals=["otp_request", "transfer_request"],
    )

    payload = notifier.build_payload(risk, recipient_phone="+34600112233")

    assert payload["recipient_phone"] == "+34600112233"
    assert payload["risk_level"] == "CRITICAL"
    assert len(payload["reasons"]) == 2
    assert "transcript" not in payload  # Privacy rule: raw transcript is never included


@patch("urllib.request.urlopen")
def test_trusted_circle_notifier_send_success(mock_urlopen):
    """Verify HTTP POST notification request to webhook endpoint."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value = mock_response

    notifier = TrustedCircleNotifier(webhook_url="https://api.example.com/trusted-circle-webhook")

    risk = RiskAssessment(
        level=RiskLevel.CRITICAL,
        reasons=["Demanda urgente de código SMS/OTP"],
        contributing_signals=["otp_request"],
    )

    result = notifier.notify(risk, recipient_phone="+34600112233")

    assert result["status"] == "success"
    assert result["webhook_url"] == "https://api.example.com/trusted-circle-webhook"
    assert mock_urlopen.called


@patch("backend.guardian.trusted_circle.TrustedCircleNotifier.notify")
def test_execute_trusted_circle_notification_action(mock_notify):
    """Verify execute_trusted_circle_notification emits TRUSTED_CONTACT_NOTIFIED event."""
    mock_notify.return_value = {"status": "success", "webhook_url": "https://api.example.com/webhook"}

    sink = InMemoryEventSink()
    canary = CanaryPolicy()
    risk = RiskAssessment(
        level=RiskLevel.CRITICAL,
        reasons=["Demanda urgente de código SMS/OTP"],
        contributing_signals=["otp_request"],
    )

    decision = canary.evaluate_action(risk_assessment=risk, action=ActionType.NOTIFY_TRUSTED_CIRCLE)
    assert decision.decision == PolicyDecision.ALLOW

    event = execute_trusted_circle_notification(
        canary_decision=decision,
        risk_assessment=risk,
        event_sink=sink,
        recipient_phone="+34600112233",
    )

    assert event is not None
    assert event.event_type == EventType.TRUSTED_CONTACT_NOTIFIED
    assert event.payload["action"] == ActionType.NOTIFY_TRUSTED_CIRCLE.value
    assert event.payload["recipient_phone"] == "+34600112233"
    assert event.payload["risk_level"] == "CRITICAL"
