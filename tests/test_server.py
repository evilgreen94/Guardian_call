"""Integration tests for Guardian Call FastAPI server endpoints."""

import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure backend package directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from server import app
from guardian.signals import create_signals


client = TestClient(app)


def test_health_check_endpoints() -> None:
    """Verify /health and /api/v1/health endpoints return 200 and expected service status."""
    for path in ("/health", "/api/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "guardian-call-backend"
        assert data["model"] == "gemini-3.5-flash"
        assert data["framework"] == "google-adk"


def test_list_scenarios_endpoint() -> None:
    """Verify /api/v1/scenarios returns every synthetic demo scenario with the expected fields."""
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]

    assert len(scenarios) == 15
    for scenario in scenarios:
        assert scenario["id"]
        assert scenario["title"]
        assert isinstance(scenario["dialogue"], list) and len(scenario["dialogue"]) > 0

    ids = [s["id"] for s in scenarios]
    assert "mfa_fatigue_it_helpdesk_01" in ids


@patch("guardian.pipeline.extract_signals")
def test_analyze_endpoint_success(mock_extract) -> None:
    """Verify POST /api/v1/analyze processes text input and returns structured response."""
    mock_extract.return_value = create_signals(
        otp_request=True,
        requested_action="share_otp",
        identity_claim="bank",
        identity_verified=False,
        urgency=True,
        financial_context=True,
    )

    payload = {"text": "Tell me the six-digit code you just received from your bank."}
    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "signals" in data
    assert "risk_assessment" in data
    assert "canary_decision" in data
    assert "warning" in data
    assert "events" in data

    assert data["risk_assessment"]["level"] == "CRITICAL"
    assert data["canary_decision"]["decision"] == "ALLOW"
    assert data["warning"]["payload"]["headline"] == "POSIBLE ESTAFA"
    assert "NO DIGA ESE CÓDIGO" in data["warning"]["payload"]["directives"]
    assert len(data["events"]) == 7


def test_analyze_endpoint_empty_text() -> None:
    """Verify POST /api/v1/analyze with empty text yields NORMAL risk and DENY canary decision."""
    payload = {"text": "   "}
    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["risk_assessment"]["level"] == "NORMAL"
    assert data["canary_decision"]["decision"] == "DENY"
    assert data["warning"] is None


@patch("guardian.vision_agent.process_image")
@patch("guardian.pipeline.extract_signals")
def test_analyze_image_endpoint(mock_extract_signals, mock_process_image) -> None:
    """Verify POST /api/v1/analyze-image endpoint processes uploaded image files."""
    from guardian.vision_agent import VisionOcrResult

    mock_process_image.return_value = VisionOcrResult(
        extracted_text="Dime el código de verificación del SMS que te llegó del banco",
        visual_manipulation_suspected=True,
        channel_detected="chat_screenshot",
        key_visual_elements=["whatsapp_header"],
    )
    mock_extract_signals.return_value = create_signals(
        otp_request=True,
        requested_action="share_otp",
        identity_claim="bank",
        urgency=True,
        financial_context=True,
        transfer_request=True,
    )

    files = {"file": ("screenshot.png", b"fake_png_bytes", "image/png")}
    response = client.post("/api/v1/analyze-image", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["risk_assessment"]["level"] == "CRITICAL"
    assert data["canary_decision"]["decision"] == "ALLOW"
    assert data["warning"]["payload"]["headline"] == "POSIBLE ESTAFA"
    event_types = [e["event_type"] for e in data["events"]]
    assert "IMAGE_RECEIVED" in event_types
    assert "IMAGE_PROCESSED_OCR" in event_types
