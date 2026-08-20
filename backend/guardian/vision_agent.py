"""Google ADK Multimodal Vision/OCR Agent for Guardian 360 (Phase M1.5).

Extracts full text transcripts and analyzes visual manipulation anomalies from
chat screenshots, fake bank transfer receipts, SMS captures, and documents.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class VisionOcrError(Exception):
    """Raised when the vision/OCR agent fails to process an image."""
    pass


class VisionOcrResultSchema(BaseModel):
    """Pydantic schema for structured output from the Google ADK vision agent."""

    extracted_text: str = Field(
        default="",
        description="Full text transcript extracted from the image/screenshot via OCR.",
    )
    visual_manipulation_suspected: bool = Field(
        default=False,
        description="True if font misalignment, digital editing, or fake receipt layout anomalies are detected.",
    )
    channel_detected: str = Field(
        default="unknown",
        description="Detected image category: chat_screenshot, bank_receipt, sms_screenshot, email_screenshot, document, or unknown.",
    )
    key_visual_elements: List[str] = Field(
        default_factory=list,
        description="List of recognized visual elements (e.g. whatsapp_header, bank_logo, verify_button).",
    )


@dataclass
class VisionOcrResult:
    """Dataclass representing the OCR and visual analysis result."""

    extracted_text: str = ""
    visual_manipulation_suspected: bool = False
    channel_detected: str = "unknown"
    key_visual_elements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        return asdict(self)


_VISION_AGENT_INSTRUCTION = (
    "You are a specialized Multimodal Vision & OCR Forensic Agent for Guardian 360.\n"
    "Your objective is to inspect the provided image or screenshot carefully:\n"
    "1. Extract the complete, exact text transcript visible in the image into 'extracted_text'.\n"
    "2. Inspect for visual forgery or manipulation (e.g. misaligned fonts, fake transfer receipt artifacts, altered account numbers) and set 'visual_manipulation_suspected'.\n"
    "3. Classify the channel ('chat_screenshot', 'bank_receipt', 'sms_screenshot', 'email_screenshot', 'document').\n"
    "4. List key recognized visual markers in 'key_visual_elements'.\n"
    "Do not invent facts not present in the image."
)

vision_ocr_agent = LlmAgent(
    name="vision_ocr_agent",
    model="gemini-3.5-flash",
    output_schema=VisionOcrResultSchema,
    instruction=_VISION_AGENT_INSTRUCTION,
)


def process_image(
    image_bytes: bytes,
    mime_type: str = "image/png",
    runner: Optional[Runner] = None,
) -> VisionOcrResult:
    """Analyze image bytes with Gemini 3.5 Multimodal via Google ADK.

    Args:
        image_bytes: Raw binary content of the image.
        mime_type: Image MIME type (default 'image/png').
        runner: Optional pre-configured ADK Runner.

    Returns:
        VisionOcrResult with extracted text and visual indicators.
    """
    if not image_bytes:
        return VisionOcrResult()

    if runner is None:
        session_service = InMemorySessionService()
        runner = Runner(
            agent=vision_ocr_agent,
            session_service=session_service,
        )

    try:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        events = runner.run(user_input=part)

        for event in reversed(events):
            if hasattr(event, "output") and event.output is not None:
                out = event.output
                if isinstance(out, VisionOcrResultSchema):
                    return VisionOcrResult(
                        extracted_text=out.extracted_text,
                        visual_manipulation_suspected=out.visual_manipulation_suspected,
                        channel_detected=out.channel_detected,
                        key_visual_elements=out.key_visual_elements or [],
                    )
                elif isinstance(out, dict):
                    return VisionOcrResult(
                        extracted_text=out.get("extracted_text", ""),
                        visual_manipulation_suspected=bool(out.get("visual_manipulation_suspected", False)),
                        channel_detected=out.get("channel_detected", "unknown"),
                        key_visual_elements=out.get("key_visual_elements", []),
                    )

        return VisionOcrResult()

    except Exception as exc:
        raise VisionOcrError(f"Failed to process image: {str(exc)}") from exc
