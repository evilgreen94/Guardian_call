"""Unit tests for Gemini signal-extraction agent using mocked ADK Runner."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from google.adk.events import Event
from google.genai import types

from guardian.agent import SignalExtractionError, extract_signals
from guardian.models import ScamSignals


def test_extract_signals_success() -> None:
    """Verify successful signal extraction from mocked ADK Runner response."""
    mock_runner = MagicMock()

    payload = {
        "identity_claim": "bank",
        "identity_verified": False,
        "financial_context": True,
        "urgency": True,
        "secrecy_request": False,
        "otp_request": True,
        "password_request": False,
        "transfer_request": False,
        "remote_access_request": False,
        "requested_action": "share_otp",
    }
    json_text = json.dumps(payload)

    mock_event = Event(
        author="signal_extraction_agent",
        content=types.Content(
            parts=[types.Part.from_text(text=json_text)],
            role="model",
        ),
        turn_complete=True,
    )
    mock_runner.run.return_value = [mock_event]

    sample_text = "Tell me the six-digit code you just received from your bank."
    signals = extract_signals(sample_text, runner=mock_runner)

    assert isinstance(signals, ScamSignals)
    assert signals.identity_claim == "bank"
    assert signals.identity_verified is False
    assert signals.financial_context is True
    assert signals.urgency is True
    assert signals.otp_request is True
    assert signals.requested_action == "share_otp"


def test_extract_signals_invalid_output() -> None:
    """Verify SignalExtractionError is raised when model output is invalid JSON."""
    mock_runner = MagicMock()

    mock_event = Event(
        author="signal_extraction_agent",
        content=types.Content(
            parts=[types.Part.from_text(text="NOT_VALID_JSON_TEXT")],
            role="model",
        ),
        turn_complete=True,
    )
    mock_runner.run.return_value = [mock_event]

    with pytest.raises(SignalExtractionError, match="Failed to extract signals"):
        extract_signals("Some text", runner=mock_runner)


def test_extract_signals_api_exception() -> None:
    """Verify SignalExtractionError is raised when Runner encounters an API exception."""
    mock_runner = MagicMock()
    mock_runner.run.side_effect = RuntimeError("Gemini API connection timeout")

    with pytest.raises(SignalExtractionError, match="Failed to extract signals"):
        extract_signals("Some text", runner=mock_runner)
