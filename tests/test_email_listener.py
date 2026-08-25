"""Unit and integration tests for Real-Time Email Listener Module (IMAP Connector)."""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch
import pytest

from backend.guardian.email_listener import EmailMessageData, EmailListener, parse_mime_email
from backend.guardian.events import EventType, InMemoryEventSink
from backend.guardian.models import RiskLevel


def create_synthetic_phishing_mime() -> bytes:
    """Construct a raw MIME email message simulating a cloud storage phishing scam."""
    msg = MIMEMultipart()
    msg["From"] = "Payment-Declined <jg4kqzs3v@emqh1r9s5u.us.a.travis.de.vectorization.importican.de>"
    msg["To"] = "target_user@example.com"
    msg["Subject"] = "shinjimulatiere, Your Account Has Been Blocked! Your Photos and Videos will be Removed"
    
    body_text = (
        "ALERTA URGENTE: Su almacenamiento en la nube está lleno (99.9%). "
        "Don't risk losing your photos, videos, contacts and personal private data. "
        "Upgrade now and get an extra 50 GB bonus storage. Don't wait! "
        "This special offer expires in 4 minutes. Click to update: http://fake-storage-domain.com/pay"
    )
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    return msg.as_bytes()


def test_parse_mime_email():
    """Verify MIME email parsing extracts sender, subject, and body text cleanly."""
    raw_bytes = create_synthetic_phishing_mime()
    parsed = parse_mime_email(raw_bytes)

    assert isinstance(parsed, EmailMessageData)
    assert "jg4kqzs3v@emqh1r9s5u.us" in parsed.sender
    assert "Account Has Been Blocked" in parsed.subject
    assert "almacenamiento" in parsed.body_text.lower()
    assert "50 GB bonus storage" in parsed.body_text


@patch("backend.guardian.email_listener.EmailListener._publish_to_server")
@patch("backend.guardian.pipeline.extract_signals")
def test_email_listener_process_single_email(mock_extract_signals, mock_publish):
    """Test EmailListener.process_email passes message through GuardianPipeline and triggers warning."""
    from backend.guardian.signals import create_signals

    mock_extract_signals.return_value = create_signals(
        identity_claim="icloud",
        service_cancellation_threat=True,
        subscription_fee_claim=True,
        unverified_link_prompt=True,
        sender_email="jg4kqzs3v@emqh1r9s5u.us",
        suspicious_domain=True,
        special_offer_hook=True,
        countdown_timer=True,
        urgency=True,
        financial_context=True,
    )

    sink = InMemoryEventSink()
    listener = EmailListener(event_sink=sink)

    raw_mime = create_synthetic_phishing_mime()
    result = listener.process_raw_email(raw_mime)

    assert result.risk_assessment.level == RiskLevel.CRITICAL
    assert result.canary_decision.decision.value == "ALLOW"
    assert result.warning_event is not None
    assert result.warning_event.payload["headline"] == "POSIBLE ESTAFA"

    event_types = [e.event_type for e in result.events]
    assert EventType.INPUT_RECEIVED in event_types
    assert EventType.SIGNAL_DETECTED in event_types
    assert EventType.RISK_UPDATED in event_types
    assert EventType.CANARY_EVALUATION in event_types
    assert EventType.USER_WARNING in event_types
    assert EventType.TRUSTED_CONTACT_NOTIFIED in event_types
