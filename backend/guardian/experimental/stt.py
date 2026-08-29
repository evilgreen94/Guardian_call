"""Experimental bounded speech-to-text adapter for demo voice input."""

from __future__ import annotations

import base64
import binascii
import importlib.metadata
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol


DEFAULT_STT_MODEL = "gemini-3.6-flash"
DEFAULT_MAX_AUDIO_BYTES = 6 * 1024 * 1024
SUPPORTED_LANGUAGE_HINTS = frozenset({"en", "es", "auto"})


class STTFailureKind(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    API_KEY_MISSING = "API_KEY_MISSING"
    SDK_MISSING = "SDK_MISSING"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    EMPTY_TRANSCRIPT = "EMPTY_TRANSCRIPT"


class STTError(Exception):
    """Sanitized STT failure; never contains raw audio or provider response."""

    def __init__(
        self,
        kind: STTFailureKind,
        *,
        exception_type: Optional[str] = None,
        http_status: Optional[int] = None,
        provider_code: Optional[str] = None,
    ) -> None:
        super().__init__(kind.value)
        self.kind = kind
        self.exception_type = exception_type
        self.http_status = http_status
        self.provider_code = provider_code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "exception_type": self.exception_type,
            "http_status": self.http_status,
            "provider_code": self.provider_code,
        }


@dataclass(frozen=True)
class STTTranscript:
    transcript: str
    provider: str
    requested_model: str
    language_hint: Optional[str]
    audio_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript": self.transcript,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "language_hint": self.language_hint,
            "audio_bytes": self.audio_bytes,
        }


class SpeechToTextProvider(Protocol):
    def transcribe(
        self,
        *,
        audio: bytes,
        mime_type: str,
        language_hint: Optional[str] = None,
    ) -> STTTranscript:
        """Return a transcript for one bounded audio sample."""


class GoogleGenAISpeechToTextProvider:
    """Small replaceable STT provider using the installed google-genai SDK."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        self.model = (
            model
            or os.environ.get("GEMINI_STT_MODEL")
            or os.environ.get("GEMINI_V2_MODEL")
            or DEFAULT_STT_MODEL
        )
        if client is not None:
            self._client = client
            return
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise STTError(STTFailureKind.API_KEY_MISSING)
        try:
            from google import genai
        except ImportError as error:
            raise STTError(
                STTFailureKind.SDK_MISSING,
                exception_type=type(error).__name__,
            ) from error
        self._client = genai.Client(api_key=key)

    def transcribe(
        self,
        *,
        audio: bytes,
        mime_type: str,
        language_hint: Optional[str] = None,
    ) -> STTTranscript:
        validate_stt_input(audio, mime_type, language_hint)
        try:
            from google.genai import types
        except ImportError as error:
            raise STTError(
                STTFailureKind.SDK_MISSING,
                exception_type=type(error).__name__,
            ) from error
        prompt = _transcription_prompt(language_hint)
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio, mime_type=mime_type),
                ],
            )
        except Exception as error:
            raise _provider_error(error) from error
        transcript = getattr(response, "text", None)
        if not isinstance(transcript, str) or not transcript.strip():
            raise STTError(STTFailureKind.EMPTY_TRANSCRIPT)
        return STTTranscript(
            transcript=transcript.strip(),
            provider="Gemini",
            requested_model=self.model,
            language_hint=language_hint,
            audio_bytes=len(audio),
        )


def decode_audio_base64(
    value: str,
    *,
    max_audio_bytes: int = DEFAULT_MAX_AUDIO_BYTES,
) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise STTError(STTFailureKind.INVALID_INPUT)
    try:
        audio = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise STTError(
            STTFailureKind.INVALID_INPUT,
            exception_type=type(error).__name__,
        ) from error
    if not audio or len(audio) > max_audio_bytes:
        raise STTError(STTFailureKind.INVALID_INPUT)
    return audio


def validate_stt_input(
    audio: bytes,
    mime_type: str,
    language_hint: Optional[str],
) -> None:
    if not isinstance(audio, bytes) or not audio:
        raise STTError(STTFailureKind.INVALID_INPUT)
    if len(audio) > DEFAULT_MAX_AUDIO_BYTES:
        raise STTError(STTFailureKind.INVALID_INPUT)
    if not isinstance(mime_type, str) or not mime_type.startswith("audio/"):
        raise STTError(STTFailureKind.INVALID_INPUT)
    if language_hint is not None and language_hint not in SUPPORTED_LANGUAGE_HINTS:
        raise STTError(STTFailureKind.INVALID_INPUT)


def sdk_version() -> Optional[str]:
    try:
        return importlib.metadata.version("google-genai")
    except importlib.metadata.PackageNotFoundError:
        return None


def _transcription_prompt(language_hint: Optional[str]) -> str:
    language = language_hint or "auto"
    return (
        "Transcribe the speech in this bounded synthetic Guardian Call demo "
        f"audio. Language hint: {language}. Return only the spoken transcript, "
        "with no commentary, no labels, and no safety analysis."
    )


def _provider_error(error: Exception) -> STTError:
    status = getattr(error, "code", None) or getattr(error, "status_code", None)
    try:
        http_status = int(status) if status is not None else None
    except (TypeError, ValueError):
        http_status = None
    provider_code = getattr(error, "status", None)
    provider_code = provider_code if isinstance(provider_code, str) else None
    return STTError(
        STTFailureKind.PROVIDER_FAILURE,
        exception_type=type(error).__name__,
        http_status=http_status,
        provider_code=provider_code,
    )
