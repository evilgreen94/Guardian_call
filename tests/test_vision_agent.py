"""Tests for Google ADK Multimodal Vision/OCR Agent (Guardian 360)."""

import json
import pytest
from unittest.mock import MagicMock, patch
from google.genai import types

from backend.guardian.vision_agent import (
    VisionOcrResult,
    VisionOcrResultSchema,
    process_image,
)


def test_vision_ocr_result_conversion():
    """Verify VisionOcrResult dataclass serialization."""
    res = VisionOcrResult(
        extracted_text="Su código de 6 dígitos es 492012. No lo comparta.",
        visual_manipulation_suspected=True,
        channel_detected="chat_screenshot",
        key_visual_elements=["whatsapp_header", "bank_logo"],
    )
    d = res.to_dict()
    assert d["extracted_text"] == "Su código de 6 dígitos es 492012. No lo comparta."
    assert d["visual_manipulation_suspected"] is True
    assert d["channel_detected"] == "chat_screenshot"
    assert d["key_visual_elements"] == ["whatsapp_header", "bank_logo"]


@patch("backend.guardian.vision_agent.Runner")
def test_process_image_mocked(mock_runner_cls):
    """Test process_image executes ADK runner with image bytes."""
    mock_runner = MagicMock()
    mock_runner_cls.return_value = mock_runner

    mock_event = MagicMock()
    mock_event.output = VisionOcrResultSchema(
        extracted_text="Transferencia confirmada de 500 EUR",
        visual_manipulation_suspected=False,
        channel_detected="bank_receipt",
        key_visual_elements=["bbva_logo"],
    )
    mock_runner.run.return_value = [mock_event]

    dummy_bytes = b"fake_png_data"
    result = process_image(dummy_bytes, mime_type="image/png", runner=mock_runner)

    assert result.extracted_text == "Transferencia confirmada de 500 EUR"
    assert result.visual_manipulation_suspected is False
    assert result.channel_detected == "bank_receipt"
    assert "bbva_logo" in result.key_visual_elements


@patch("backend.guardian.vision_agent.Runner")
@patch("backend.guardian.agent.Runner")
def test_pipeline_process_image_flow(mock_agent_runner_cls, mock_vision_runner_cls):
    """Test full pipeline execution with image input."""
    from backend.guardian.agent import ScamSignalsSchema
    from backend.guardian.events import EventType, InMemoryEventSink
    from backend.guardian.pipeline import GuardianPipeline

    # Mock Vision Agent Runner
    mock_vision_runner = MagicMock()
    mock_vision_runner_cls.return_value = mock_vision_runner
    mock_vision_event = MagicMock()
    mock_vision_event.output = VisionOcrResultSchema(
        extracted_text="Dime tu código de SMS de 6 dígitos urgentemente",
        visual_manipulation_suspected=True,
        channel_detected="chat_screenshot",
        key_visual_elements=["whatsapp_header"],
    )
    mock_vision_runner.run.return_value = [mock_vision_event]

    # Mock Signal Extraction Agent Runner
    mock_agent_runner = MagicMock()
    mock_agent_runner_cls.return_value = mock_agent_runner
    signal_json = json.dumps({
        "identity_claim": "banco",
        "otp_request": True,
        "urgency": True,
        "financial_context": True,
        "transfer_request": True,
    })
    mock_agent_event = MagicMock()
    mock_agent_event.content.parts = [types.Part.from_text(text=signal_json)]
    mock_agent_runner.run.return_value = [mock_agent_event]

    pipeline = GuardianPipeline()
    sink = InMemoryEventSink()
    res = pipeline.process_image(b"fake_image_bytes", mime_type="image/png", event_sink=sink)

    assert res.signals.otp_request is True
    assert res.risk_assessment.level.value == "CRITICAL"

    event_types = [e.event_type for e in res.events]
    assert EventType.IMAGE_RECEIVED in event_types
    assert EventType.IMAGE_PROCESSED_OCR in event_types
    assert EventType.SIGNAL_DETECTED in event_types
    assert EventType.RISK_UPDATED in event_types
    assert EventType.CANARY_EVALUATION in event_types
    assert EventType.USER_WARNING in event_types

