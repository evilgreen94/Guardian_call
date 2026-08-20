"""Gemini signal-extraction agent using Google ADK for Guardian Call M0."""

import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .models import ScamSignals
from .signals import signals_from_dict


class ScamSignalsSchema(BaseModel):
    """Pydantic schema for structured signal output matching ScamSignals exactly."""
    identity_claim: Optional[str] = Field(
        default=None,
        description="The organization, institution, or persona the caller claims to represent.",
    )
    identity_verified: bool = Field(
        default=False,
        description="Whether the caller's identity was verified through a trusted out-of-band process.",
    )
    financial_context: bool = Field(
        default=False,
        description="Whether the conversation touches on money, bank accounts, cards, or assets.",
    )
    urgency: bool = Field(
        default=False,
        description="Whether the caller is creating time pressure, panic, or demanding immediate action.",
    )
    secrecy_request: bool = Field(
        default=False,
        description="Whether the caller asks the user not to tell anyone, hang up, or check with family/bank.",
    )
    otp_request: bool = Field(
        default=False,
        description="Whether the caller asks for or mentions a one-time passcode (OTP/SMS code).",
    )
    password_request: bool = Field(
        default=False,
        description="Whether the caller asks for a password, PIN, or account login credentials.",
    )
    transfer_request: bool = Field(
        default=False,
        description="Whether the caller requests a wire transfer, gift card, Zelle, or payment.",
    )
    remote_access_request: bool = Field(
        default=False,
        description="Whether the caller requests installing remote access software (AnyDesk, TeamViewer, etc.).",
    )
    service_cancellation_threat: bool = Field(
        default=False,
        description="Whether there is a threat of cloud storage full, account deletion, lost photos/files, or service cancellation.",
    )
    subscription_fee_claim: bool = Field(
        default=False,
        description="Whether there is a claim of an unexpected subscription fee, mandatory renewal charge, or unpaid invoice.",
    )
    unverified_link_prompt: bool = Field(
        default=False,
        description="Whether the user is prompted to click an external link, update payment methods, or login outside the official app.",
    )
    requested_action: Optional[str] = Field(
        default=None,
        description="Specific action requested by caller (e.g. 'share_otp', 'click_link', 'upgrade_storage', 'transfer_money').",
    )


class SignalExtractionError(Exception):
    """Raised when signal extraction via Gemini API fails or returns invalid output."""
    pass


from .knowledge import get_knowledge_prompt_context

KNOWLEDGE_CONTEXT = get_knowledge_prompt_context()

INSTRUCTION = (
    "You are Guardian Call's specialized Scam Detection Agent powered by Gemini.\n"
    "Analyze the provided conversational text and extract structured scam signals.\n"
    "Populate the 10 schema fields based strictly on facts explicitly mentioned in the text.\n\n"
    f"{KNOWLEDGE_CONTEXT}\n\n"
    "CRITICAL RULES FOR SIGNAL EXTRACTION:\n"
    "1. Strict Fact Extraction: Only set a boolean field to true if explicitly requested or stated by caller.\n"
    "2. False Positive Suppression: If caller mentions security warnings in a negative context (e.g. 'The bank NEVER asks for passwords'), do NOT flag password_request or otp_request as true.\n"
    "3. Canonical requested_action values: Limit requested_action to one of: 'share_otp', 'share_password', 'install_remote_software', 'transfer_money', 'buy_giftcards', 'confirm_iban', or null.\n"
    "4. Normalized identity_claim: Use standard lower-case terms like 'banco', 'soporte_tecnico', 'policia', 'familiar', 'correos', 'director_general', 'broker', 'compania_electrica'.\n\n"
    "Do not invent or infer unstated facts."
)

signal_agent = LlmAgent(
    name="signal_extraction_agent",
    model="gemini-3.5-flash",
    instruction=INSTRUCTION,
    output_schema=ScamSignalsSchema,
)




def extract_signals(text: str, runner: Optional[Runner] = None) -> ScamSignals:
    """Extract structured ScamSignals from text input using Gemini ADK agent.

    Raises:
        SignalExtractionError: If API execution fails or returns unparseable/invalid output.
    """
    if not isinstance(text, str) or not text.strip():
        raise SignalExtractionError("Input text must be a non-empty string.")

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
            agent=signal_agent,
            session_service=session_service,
            app_name="guardian_call",
        )

    try:
        new_message = types.Content(
            parts=[types.Part.from_text(text=text)],
            role="user",
        )

        events = list(runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ))

        extracted_text: Optional[str] = None
        for event in reversed(events):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        extracted_text = part.text
                        break
            if extracted_text:
                break

        if not extracted_text:
            raise SignalExtractionError("Model returned empty or missing content.")

        # Clean potential markdown block formatting if present
        clean_text = extracted_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        data: Dict[str, Any] = json.loads(clean_text)
        if not isinstance(data, dict):
            raise SignalExtractionError(f"Model output is not a JSON object: {type(data)}")

        # Validate through Pydantic schema to ensure field constraints
        validated_schema = ScamSignalsSchema(**data)
        validated_dict = validated_schema.model_dump()

        return signals_from_dict(validated_dict)

    except Exception as exc:
        if isinstance(exc, SignalExtractionError):
            raise
        raise SignalExtractionError(f"Failed to extract signals from text: {str(exc)}") from exc
