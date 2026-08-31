"""Offline tests for the experimental STT vertical slice."""

import base64
import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend import server
from backend.guardian.experimental.extractor_v2 import GeminiV2Observation
from backend.guardian.experimental.signals_v2 import (
    ActionTypeV2,
    Actor,
    AssetCategory,
    AssetSubtype,
    IdentityPretext,
    InteractionAct,
    ScamSignalsV2,
    SemanticDirection,
    SensitiveAsset,
    Destination,
)
from backend.guardian.experimental.stt import (
    GoogleGenAISpeechToTextProvider,
    STTError,
    STTFailureKind,
    STTTranscript,
    decode_audio_base64,
)


class FakeSTTProvider:
    calls = 0

    def __init__(self, transcript="Tell me the six-digit code.", error=None):
        self.transcript = transcript
        self.error = error

    def transcribe(self, *, audio, mime_type, language_hint=None):
        type(self).calls += 1
        if self.error:
            raise self.error
        return STTTranscript(
            transcript=self.transcript,
            provider="FakeSTT",
            requested_model="fake-stt",
            language_hint=language_hint,
            audio_bytes=len(audio),
        )


class FakeV2Extractor:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    def extract(self, text):
        type(self).calls.append(text)
        return GeminiV2Observation(
            signals=ScamSignalsV2(
                identity_pretext=IdentityPretext(),
                contexts=frozenset(),
                interaction_acts=(
                    InteractionAct(
                        ActionTypeV2.DISCLOSE,
                        SensitiveAsset(AssetCategory.SECRET, AssetSubtype.OTP),
                        SemanticDirection.DIRECT_REQUEST,
                        Actor.USER,
                        Destination.CALLER,
                    ),
                ),
                manipulation=frozenset(),
            ),
            provider="FakeGemini",
            requested_model="fake-v2",
            returned_model_version="fake-version",
            response_id="fake-response",
            request_prompt_sha256="1" * 64,
            response_sha256="2" * 64,
            response_bytes=10,
        )


class FakeGenAIResponse:
    text = "Hola mundo"


class FakeGenAIModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return FakeGenAIResponse()


class FakeGenAIClient:
    def __init__(self):
        self.models = FakeGenAIModels()


class TestExperimentalSTT(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        server.experimental_v2_sessions.clear()
        FakeSTTProvider.calls = 0
        FakeV2Extractor.calls = []
        self.previous_stt_factory = server.experimental_stt_provider_factory
        self.previous_extractor_factory = server.experimental_v2_extractor_factory
        server.experimental_stt_provider_factory = lambda: FakeSTTProvider()
        server.experimental_v2_extractor_factory = FakeV2Extractor

    def tearDown(self):
        server.experimental_v2_sessions.clear()
        server.experimental_stt_provider_factory = self.previous_stt_factory
        server.experimental_v2_extractor_factory = self.previous_extractor_factory

    def test_successful_stt_returns_sanitized_transcript(self):
        payload = {
            "audio_base64": base64.b64encode(b"fake audio").decode("ascii"),
            "mime_type": "audio/webm",
            "language_hint": "es",
        }

        response = self.client.post("/api/v1/experimental/stt", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "TRANSCRIBED")
        self.assertEqual(body["transcript"], "Tell me the six-digit code.")
        self.assertEqual(body["language_hint"], "es")
        self.assertEqual(body["provider"], "FakeSTT")
        self.assertEqual(body["audio_bytes"], len(b"fake audio"))
        serialized = json.dumps(body)
        self.assertNotIn(payload["audio_base64"], serialized)
        self.assertNotIn("raw_audio", serialized)
        self.assertNotIn("provider_response", serialized)

    def test_stt_failure_does_not_enter_m2_5_or_retry(self):
        server.experimental_stt_provider_factory = lambda: FakeSTTProvider(
            error=STTError(STTFailureKind.PROVIDER_FAILURE, http_status=503)
        )
        payload = {
            "audio_base64": base64.b64encode(b"fake audio").decode("ascii"),
            "mime_type": "audio/webm",
            "language_hint": "auto",
        }

        response = self.client.post("/api/v1/experimental/stt", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "FAILED")
        self.assertEqual(body["error"]["kind"], "PROVIDER_FAILURE")
        self.assertEqual(body["error"]["http_status"], 503)
        self.assertEqual(FakeSTTProvider.calls, 1)
        self.assertEqual(FakeV2Extractor.calls, [])
        self.assertEqual(server.experimental_v2_sessions, {})

    def test_transcript_and_typed_text_share_canonical_turn_endpoint(self):
        stt_response = self.client.post(
            "/api/v1/experimental/stt",
            json={
                "audio_base64": base64.b64encode(b"fake audio").decode("ascii"),
                "mime_type": "audio/webm",
                "language_hint": "en",
            },
        )
        transcript = stt_response.json()["transcript"]

        typed = self.client.post(
            "/api/v1/experimental/v2/turn",
            json={
                "session_id": "canonical-session",
                "source_turn_number": 1,
                "text": "Typed text",
            },
        )
        voice = self.client.post(
            "/api/v1/experimental/v2/turn",
            json={
                "session_id": "canonical-session",
                "source_turn_number": 2,
                "text": transcript,
            },
        )

        self.assertEqual(typed.json()["turn"]["source_turn_number"], 1)
        self.assertEqual(voice.json()["turn"]["source_turn_number"], 2)
        self.assertEqual(typed.json()["turn"]["applied_m2_turn_number"], 1)
        self.assertEqual(voice.json()["turn"]["applied_m2_turn_number"], 2)
        self.assertEqual(FakeV2Extractor.calls, ["Typed text", transcript])

    def test_invalid_stt_input_is_sanitized_and_does_not_retry(self):
        response = self.client.post(
            "/api/v1/experimental/stt",
            json={
                "audio_base64": "not-base64",
                "mime_type": "audio/webm",
                "language_hint": "es",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "FAILED")
        self.assertEqual(response.json()["error"]["kind"], "INVALID_INPUT")
        self.assertEqual(FakeSTTProvider.calls, 0)
        self.assertEqual(FakeV2Extractor.calls, [])

    def test_google_genai_stt_provider_uses_audio_part_once(self):
        client = FakeGenAIClient()
        provider = GoogleGenAISpeechToTextProvider(
            model="gemini-test",
            api_key="synthetic-key",
            client=client,
        )

        result = provider.transcribe(
            audio=b"fake audio",
            mime_type="audio/webm",
            language_hint="es",
        )

        self.assertEqual(result.transcript, "Hola mundo")
        self.assertEqual(result.requested_model, "gemini-test")
        self.assertEqual(result.language_hint, "es")
        self.assertEqual(len(client.models.calls), 1)
        call = client.models.calls[0]
        self.assertEqual(call["model"], "gemini-test")
        self.assertEqual(len(call["contents"]), 2)

    def test_decode_audio_base64_rejects_empty_or_oversized_audio(self):
        with self.assertRaises(STTError):
            decode_audio_base64("")
        with self.assertRaises(STTError):
            decode_audio_base64(base64.b64encode(b"1234").decode("ascii"), max_audio_bytes=3)

    def test_browser_routes_successful_stt_through_submit_turn_text(self):
        source = (ROOT / "frontend" / "visualizer" / "app.js").read_text(encoding="utf-8")
        self.assertIn("async function submitTurnText", source)
        self.assertIn("await submitTurnText(data.transcript, 'VOICE')", source)
        self.assertIn("await submitTurnText(text, 'TEXT')", source)
        self.assertIn("/api/v1/experimental/v2/turn", source)
        self.assertIn("/api/v1/experimental/stt", source)
        self.assertNotIn("/api/v1/analyze',", source)

    def test_canary_view_model_uses_real_rest_fields_without_scores(self):
        source = (ROOT / "frontend" / "visualizer" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "frontend" / "visualizer" / "index.html").read_text(encoding="utf-8")

        self.assertIn("function buildCanaryViewModel", source)
        self.assertIn("renderCanaryViewModel(vm)", source)
        self.assertIn("RISK != KERN-3 AUTHORITY", html)
        for field in (
            "source_turn_number",
            "applied_m2_turn_number",
            "representational_losses",
            "normalized_m2_summary",
            "policy_event",
            "canary_authorization",
        ):
            self.assertIn(field, source)
        self.assertNotIn("scamScore", source)
        self.assertNotIn("scam_score", source)
        self.assertNotIn("0-100", html)

    def test_canary_redesign_renders_failure_as_not_new_safety_verdict(self):
        source = (ROOT / "frontend" / "visualizer" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "frontend" / "visualizer" / "index.html").read_text(encoding="utf-8")

        self.assertIn("NO ASSESSMENT", source)
        self.assertIn("PRESERVED STATE", source)
        self.assertIn("ANALYSIS UNAVAILABLE", html)
        self.assertIn("STATE UNCHANGED/PRESERVED", html)
        self.assertIn("NOT A NEW SAFETY VERDICT", html)
        self.assertIn("buildSTTFailureViewModel", source)
        self.assertIn("renderCanaryViewModel(buildSTTFailureViewModel", source)
        self.assertIn("failureBanner?.classList.toggle", source)
        self.assertIn("updateRiskRail(vm.failure ? null : currentRisk)", source)

    def test_canary_redesign_final_polish_keeps_real_state_boundaries(self):
        source = (ROOT / "frontend" / "visualizer" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "frontend" / "visualizer" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("setText(riskDominant, 'NO ASSESSMENT')", source)
        self.assertIn("const dominantRiskLabel = hasPreservedRisk", source)
        self.assertIn("'PRESERVED STATE'", source)
        self.assertIn("setText(canaryAction, vm.canary.evaluated ? valueOrDash(vm.canary.action) : '-')", source)
        self.assertIn("[loss.source_value, loss.disposition, loss.source_enum]", source)
        self.assertIn("grid-template-columns: 72px minmax(112px, 0.9fr) 62px minmax(150px, 1fr) 68px 142px", css)


if __name__ == "__main__":
    unittest.main()
