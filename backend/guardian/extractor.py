"""Signal extraction layer for Guardian Call, backed by Google Gen AI SDK."""

import json
import os
from typing import Any, Dict, Optional, Protocol
from .models import ScamSignals
from .signals import signals_from_dict

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

EXTRACTION_SYSTEM_INSTRUCTION = (
    "You are a factual conversational signal extraction engine. "
    "Analyze the provided conversation text and extract factual caller claims and requests according to the JSON schema. "
    "Do NOT determine risk, do NOT calculate scam probabilities, do NOT make safety decisions, and do NOT advise actions. "
    "Extract only the objective signals defined in the schema."
)

SCAM_SIGNALS_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "identity_claim": {
            "type": ["string", "null"],
            "description": "Factual entity the caller claims to represent (e.g. 'bank', 'police', 'tech_support', 'government') or null if none.",
        },
        "identity_verified": {
            "type": "boolean",
            "description": "Whether the caller's identity was proven or verified through official means during the call.",
        },
        "financial_context": {
            "type": "boolean",
            "description": "Whether the conversation relates to bank accounts, transfers, debts, refunds, or financial assets.",
        },
        "urgency": {
            "type": "boolean",
            "description": "Whether the caller uses time pressure, threats of imminent penalty, or demands immediate action.",
        },
        "secrecy_request": {
            "type": "boolean",
            "description": "Whether the caller asks the user not to tell family, bank staff, or authorities.",
        },
        "otp_request": {
            "type": "boolean",
            "description": "Whether a one-time passcode (OTP), verification code, or 2FA code is mentioned or involved.",
        },
        "password_request": {
            "type": "boolean",
            "description": "Whether an account password, PIN, or credential is requested.",
        },
        "transfer_request": {
            "type": "boolean",
            "description": "Whether the caller asks the user to send money, wire funds, or make a payment.",
        },
        "remote_access_request": {
            "type": "boolean",
            "description": "Whether the caller asks the user to install remote desktop software (e.g. AnyDesk, TeamViewer) or grant device control.",
        },
        "requested_action": {
            "type": ["string", "null"],
            "description": "The specific action the caller asks the user to take (e.g. 'share_otp', 'enter_in_app', 'share_password', 'wire_funds', 'install_software') or null if none.",
        },
    },
    "required": [
        "identity_claim",
        "identity_verified",
        "financial_context",
        "urgency",
        "secrecy_request",
        "otp_request",
        "password_request",
        "transfer_request",
        "remote_access_request",
        "requested_action",
    ],
}


class ExtractionError(Exception):
    """Raised when conversational signal extraction fails."""

    def __init__(
        self,
        message: str,
        error_type: str = "EXTRACTION_ERROR",
        raw_response: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.raw_response = raw_response

    def __str__(self) -> str:
        return f"[{self.error_type}] {self.message}"


class SignalExtractor(Protocol):
    """Protocol for pluggable conversational signal extractors."""

    def extract_signals(self, text: str) -> ScamSignals:
        """Extract structured scam signals from conversation text.

        Raises:
            ExtractionError: If extraction fails due to network, schema, or model errors.
        """
        ...


class GeminiSignalExtractor:
    """Extracts structured ScamSignals using the official Google Gen AI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if client is not None:
            self._client = client
        else:
            if not self.api_key:
                raise ExtractionError(
                    "No Gemini API key provided. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
                    error_type="API_KEY_MISSING",
                )
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError as err:
                raise ExtractionError(
                    f"google-genai SDK is not installed. Install via `pip install google-genai`: {err}",
                    error_type="SDK_MISSING",
                ) from err

    def extract_signals(self, text: str) -> ScamSignals:
        """Invoke Gemini to extract structured ScamSignals from text."""
        if not text or not text.strip():
            raise ExtractionError("Input conversation text is empty.", error_type="INVALID_INPUT")

        prompt = (
            f"Analyze the following conversation snippet and extract factual signals as JSON:\n\n"
            f'"""\n{text}\n"""'
        )

        try:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_json_schema=SCAM_SIGNALS_JSON_SCHEMA,
                    temperature=0.0,
                )
            except (ImportError, AttributeError):
                config = {
                    "system_instruction": EXTRACTION_SYSTEM_INSTRUCTION,
                    "response_mime_type": "application/json",
                    "response_json_schema": SCAM_SIGNALS_JSON_SCHEMA,
                    "temperature": 0.0,
                }

            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as err:
            raise ExtractionError(
                f"Gemini API request failed: {err}",
                error_type="NETWORK_ERROR",
            ) from err

        raw_text: Optional[str] = getattr(response, "text", None)
        if not raw_text or not raw_text.strip():
            raise ExtractionError(
                "Gemini returned an empty response.",
                error_type="EMPTY_RESPONSE",
                raw_response=raw_text,
            )

        try:
            parsed_data = json.loads(raw_text)
        except json.JSONDecodeError as err:
            raise ExtractionError(
                f"Failed to parse Gemini JSON output: {err}",
                error_type="SCHEMA_ERROR",
                raw_response=raw_text,
            ) from err

        if not isinstance(parsed_data, dict):
            raise ExtractionError(
                f"Expected JSON object from Gemini, got {type(parsed_data).__name__}",
                error_type="SCHEMA_ERROR",
                raw_response=raw_text,
            )

        try:
            return signals_from_dict(parsed_data)
        except Exception as err:
            raise ExtractionError(
                f"Failed to construct ScamSignals from model output: {err}",
                error_type="SCHEMA_ERROR",
                raw_response=raw_text,
            ) from err


class MockSignalExtractor:
    """Deterministic mock extractor for unit tests and offline workflows."""

    def __init__(
        self,
        signals: Optional[ScamSignals] = None,
        error: Optional[ExtractionError] = None,
    ) -> None:
        self.signals = signals
        self.error = error

    def extract_signals(self, text: str) -> ScamSignals:
        """Return preset signals or raise preset error."""
        if self.error is not None:
            raise self.error
        if self.signals is not None:
            return self.signals
        # Default behavior: basic neutral signals
        return ScamSignals()
