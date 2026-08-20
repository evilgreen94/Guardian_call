import json
import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_publish_and_recent_events():
    payload = {
        "event_type": "REALTIME_EMAIL_ANALYSIS",
        "source": "IMAP_LISTENER",
        "sender": "Security Alert <shinjimulatiere@gmail.com>",
        "subject": "URGENT: Cloud Storage Blocked",
        "risk_level": "CRITICAL",
        "decision": "ALLOW",
        "reasons": ["Urgency or pressure tactics detected"],
        "headline": "POSIBLE ESTAFA",
        "signals": {"identity_claim": "cloud_service_or_bank", "urgency": True},
        "events": [{"event_type": "USER_WARNING", "payload": {"headline": "POSIBLE ESTAFA"}}]
    }

    pub_res = client.post("/api/v1/events/publish", json=payload)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    rec_res = client.get("/api/v1/events/recent")
    assert rec_res.status_code == 200
    events = rec_res.json()["events"]
    assert len(events) >= 1
    assert events[-1]["event_type"] == "REALTIME_EMAIL_ANALYSIS"
    assert events[-1]["sender"] == "Security Alert <shinjimulatiere@gmail.com>"


def test_scan_inbox_endpoint(monkeypatch):
    from backend.guardian.models import RiskAssessment, RiskLevel, CanaryDecision, PolicyDecision, ActionType
    from backend.guardian.signals import ScamSignals

    class DummyResult:
        risk_assessment = RiskAssessment(level=RiskLevel.CRITICAL, reasons=["Test scam reason"])
        canary_decision = CanaryDecision(action=ActionType.WARN_USER, decision=PolicyDecision.ALLOW, reason="Test warning authorized", risk_level=RiskLevel.CRITICAL)
        warning_event = None
        signals = ScamSignals()
        events = []

    def mock_scan(self, limit=5):
        return [("123", DummyResult()), ("124", DummyResult())]

    from backend.guardian.email_listener import EmailListener
    monkeypatch.setattr(EmailListener, "scan_recent_emails", mock_scan)

    res = client.post("/api/v1/scan-inbox?limit=2")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["count"] == 2
    assert data["scanned_emails"][0]["risk_level"] == "CRITICAL"

