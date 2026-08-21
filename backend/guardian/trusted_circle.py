"""Trusted Circle Notification module for Guardian Call (Phase M1).

Sends privacy-preserving alerts to pre-authorized contacts/family members
when CanaryPolicy authorizes NOTIFY_TRUSTED_CIRCLE under CRITICAL risk.
"""

import json
import os
import urllib.request
from typing import Any, Dict, Optional

from .events import EventType, GuardianEvent, InMemoryEventSink
from .models import ActionType, CanaryDecision, PolicyDecision, RiskAssessment


class TrustedCircleNotificationError(Exception):
    """Raised when notification delivery to the trusted circle fails."""
    pass


class TrustedCircleNotifier:
    """Client for dispatching trusted circle notifications via Webhook/SMS."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url or os.getenv("TRUSTED_CIRCLE_WEBHOOK_URL")

    def build_payload(
        self,
        risk_assessment: RiskAssessment,
        recipient_phone: str = "+34600000000",
    ) -> Dict[str, Any]:
        """Construct privacy-preserving notification payload.

        Privacy rule: Raw conversational transcripts or images are NEVER included.
        Only risk level, explainable reasons, and contributing signal identifiers are transmitted.
        """
        return {
            "recipient_phone": recipient_phone,
            "risk_level": risk_assessment.level.value,
            "reasons": risk_assessment.reasons,
            "contributing_signals": risk_assessment.contributing_signals,
            "system_message": (
                f"GUARDIAN CALL ALERT: Potential scam detected for your protected contact. "
                f"Risk Level: {risk_assessment.level.value}. Reasons: {', '.join(risk_assessment.reasons)}"
            ),
        }

    def notify(
        self,
        risk_assessment: RiskAssessment,
        recipient_phone: str = "+34600000000",
    ) -> Dict[str, Any]:
        """Dispatch notification to the configured webhook endpoint."""
        payload = self.build_payload(risk_assessment, recipient_phone=recipient_phone)

        if not self.webhook_url:
            # If no webhook URL is configured, log local simulated delivery
            return {
                "status": "simulated",
                "message": "Notification logged locally (no webhook URL configured).",
                "payload": payload,
            }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status_code = getattr(resp, "status", 200)
                return {
                    "status": "success",
                    "status_code": status_code,
                    "webhook_url": self.webhook_url,
                    "payload": payload,
                }
        except Exception as exc:
            raise TrustedCircleNotificationError(
                f"Failed to deliver trusted circle notification: {str(exc)}"
            ) from exc


def execute_trusted_circle_notification(
    canary_decision: CanaryDecision,
    risk_assessment: RiskAssessment,
    event_sink: InMemoryEventSink,
    recipient_phone: str = "+34600000000",
    notifier: Optional[TrustedCircleNotifier] = None,
) -> Optional[GuardianEvent]:
    """Execute authorized trusted circle notification action and emit TRUSTED_CONTACT_NOTIFIED event.

    Args:
        canary_decision: The CanaryPolicy decision for NOTIFY_TRUSTED_CIRCLE.
        risk_assessment: Current risk state.
        event_sink: Event sink to emit the domain event.
        recipient_phone: Phone number of the trusted contact.
        notifier: Optional TrustedCircleNotifier instance.

    Returns:
        GuardianEvent if action was executed, None if DENIED.
    """
    if canary_decision.decision != PolicyDecision.ALLOW:
        return None

    client = notifier or TrustedCircleNotifier()

    try:
        delivery_result = client.notify(risk_assessment, recipient_phone=recipient_phone)
    except TrustedCircleNotificationError as exc:
        delivery_result = {"status": "failed", "error": str(exc)}

    event = GuardianEvent(
        event_type=EventType.TRUSTED_CONTACT_NOTIFIED,
        payload={
            "action": ActionType.NOTIFY_TRUSTED_CIRCLE.value,
            "recipient_phone": recipient_phone,
            "risk_level": risk_assessment.level.value,
            "delivery_result": delivery_result,
        },
    )
    event_sink.emit(event)
    return event
