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
