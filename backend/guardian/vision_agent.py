"""Google ADK Multimodal Vision/OCR Agent for Guardian 360 (Phase M1.5).

Extracts full text transcripts and analyzes visual manipulation anomalies from
chat screenshots, fake bank transfer receipts, SMS captures, email headers, and documents.
"""

import json
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
        description="Full text transcript extracted from the image/screenshot via OCR in any language (English, Spanish, etc.).",
    )
    sender_email: Optional[str] = Field(
        default=None,
        description="Sender email address or email header visible in email screenshots (e.g. jg4kqzs3v@emqh1r9s5u.us).",
    )
    sender_domain: Optional[str] = Field(
        default=None,
        description="Sender domain or server route visible in headers (e.g. neuralgrid.org.importican.de).",
    )
    suspicious_domain_detected: bool = Field(
        default=False,
        description="True if sender email address/domain looks randomized, spoofed, or suspicious.",
    )
    special_offer_detected: bool = Field(
        default=False,
        description="True if special bonus offer or discount hooks are present (e.g. 'extra 50 GB bonus storage', '90% discount').",
    )
    countdown_timer_detected: bool = Field(
        default=False,
        description="True if urgency countdown timer or expiration time is visible (e.g. 'expires in 4 minutes', '24 hours left').",
    )
    visual_manipulation_suspected: bool = Field(
        default=False,
        description="True if font misalignment, digital editing, fake banners, or fake receipt layout anomalies are detected.",
    )
    channel_detected: str = Field(
        default="unknown",
        description="Detected image category: email_screenshot, chat_screenshot, bank_receipt, sms_screenshot, cloud_storage_alert, document, or unknown.",
    )
    key_visual_elements: List[str] = Field(
        default_factory=list,
        description="List of recognized visual elements (e.g. whatsapp_header, bank_logo, verify_button, storage_full_banner, urgency_timer).",
    )


@dataclass
class VisionOcrResult:
    """Dataclass representing the OCR and visual analysis result."""

    extracted_text: str = ""
    sender_email: Optional[str] = None
    sender_domain: Optional[str] = None
    suspicious_domain_detected: bool = False
    special_offer_detected: bool = False
    countdown_timer_detected: bool = False
    visual_manipulation_suspected: bool = False
    channel_detected: str = "unknown"
    key_visual_elements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to serializable dictionary."""
        return asdict(self)


_VISION_AGENT_INSTRUCTION = (
    "You are a specialized Multimodal Vision & OCR Forensic Agent for Guardian 360.\n"
    "Your objective is to inspect the provided image, screenshot, or document carefully:\n"
    "1. Extract the complete, exact text transcript visible in the image into 'extracted_text' in any language (English, Spanish, French, German, etc.). Include sender emails, headers, warnings, body copy, and button text.\n"
    "2. Identify any visible sender email address in 'sender_email' and its domain in 'sender_domain'. Set 'suspicious_domain_detected' to true if the domain looks randomized, spoofed, or suspicious (e.g., long random strings, fake server routes).\n"
    "3. Set 'special_offer_detected' to true if special bonus hooks or free space offers are present (e.g., 'extra 50 GB bonus storage').\n"
    "4. Set 'countdown_timer_detected' to true if urgency expiration timers are present (e.g., 'expires in 4 minutes').\n"
    "5. Inspect for visual forgery or manipulation (e.g., misaligned fonts, fake transfer receipt artifacts, fake cloud alert banners, altered account numbers) and set 'visual_manipulation_suspected'.\n"
    "6. Classify the channel ('email_screenshot', 'chat_screenshot', 'bank_receipt', 'sms_screenshot', 'cloud_storage_alert', 'document').\n"
    "7. List key recognized visual markers in 'key_visual_elements' (e.g., 'spam_warning_banner', 'cloud_icon', 'urgency_timer', 'red_update_button', 'spoofed_sender_address').\n"
    "Do not invent facts not present in the image."
)

vision_ocr_agent = LlmAgent(
    name="vision_ocr_agent",
    model="gemini-3.5-flash",
    output_schema=VisionOcrResultSchema,
    instruction=_VISION_AGENT_INSTRUCTION,
)


def _parse_vision_dict(data: Dict[str, Any]) -> VisionOcrResult:
    """Helper to parse a dictionary into VisionOcrResult."""
    return VisionOcrResult(
        extracted_text=data.get("extracted_text", ""),
        sender_email=data.get("sender_email"),
        sender_domain=data.get("sender_domain"),
        suspicious_domain_detected=bool(data.get("suspicious_domain_detected", False)),
        special_offer_detected=bool(data.get("special_offer_detected", False)),
        countdown_timer_detected=bool(data.get("countdown_timer_detected", False)),
        visual_manipulation_suspected=bool(data.get("visual_manipulation_suspected", False)),
        channel_detected=data.get("channel_detected", "unknown"),
        key_visual_elements=data.get("key_visual_elements", []) or [],
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

    user_id = "guardian_user"
    session_id = "guardian_session"

    if runner is None:
        session_service = InMemorySessionService()
        session_service.create_session_sync(
            app_name="guardian_call",
            user_id=user_id,
            session_id=session_id,
        )
        runner = Runner(
            agent=vision_ocr_agent,
            session_service=session_service,
            app_name="guardian_call",
        )

    try:
        img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        prompt_text = (
            "Perform full OCR transcript extraction in any language (English, Spanish, etc.). "
            "Extract sender email address and domain, detect cloud storage threats, special bonus offers, "
            "countdown timers, and visual manipulation."
        )
        txt_part = types.Part.from_text(text=prompt_text)

        new_message = types.Content(parts=[txt_part, img_part], role="user")

        events = list(runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ))

        for event in reversed(events):
            # Case 1: ADK populated event.output with VisionOcrResultSchema or dict
            if hasattr(event, "output") and event.output is not None:
                out = event.output
                if isinstance(out, VisionOcrResultSchema):
                    return VisionOcrResult(
                        extracted_text=out.extracted_text,
                        sender_email=out.sender_email,
                        sender_domain=out.sender_domain,
                        suspicious_domain_detected=out.suspicious_domain_detected,
                        special_offer_detected=out.special_offer_detected,
                        countdown_timer_detected=out.countdown_timer_detected,
                        visual_manipulation_suspected=out.visual_manipulation_suspected,
                        channel_detected=out.channel_detected,
                        key_visual_elements=out.key_visual_elements or [],
                    )
                elif isinstance(out, dict):
                    return _parse_vision_dict(out)

            # Case 2: Output JSON string present in event.content.parts[0].text
            if hasattr(event, "content") and event.content and getattr(event.content, "parts", None):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text and p.text.strip().startswith("{"):
                        try:
                            parsed_json = json.loads(p.text)
                            if isinstance(parsed_json, dict):
                                return _parse_vision_dict(parsed_json)
                        except Exception:
                            pass

        return VisionOcrResult()

    except Exception as exc:
        raise VisionOcrError(f"Failed to process image: {str(exc)}") from exc
