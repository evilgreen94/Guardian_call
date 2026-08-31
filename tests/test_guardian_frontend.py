"""Static and contract tests for the human-facing Guardian frontend."""

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend import server


GUARDIAN_DIR = ROOT / "frontend" / "guardian"
PROVENANCE_DOC = ROOT / "docs" / "threat-model" / "GUARDIAN_BIDIRECTIONAL_SPEAKER_PROVENANCE.md"


class TestGuardianFrontend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)

    def test_guardian_serves_separately_from_frozen_canary_visualizer(self):
        guardian = self.client.get("/guardian/")
        guardian_index = self.client.get("/guardian/index.html")
        canary = self.client.get("/visualizer/")

        self.assertEqual(guardian.status_code, 200)
        self.assertEqual(guardian_index.status_code, 200)
        self.assertEqual(canary.status_code, 200)
        self.assertIn("Guardian Call", guardian.text)
        self.assertIn("Guardian Call", guardian_index.text)
        self.assertIn("Protected by CANARY", guardian.text)
        self.assertIn("CANARY", canary.text)
        self.assertNotEqual(guardian.text, canary.text)

    def test_root_routes_to_guardian_primary_surface(self):
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/guardian/")

    def test_guardian_links_to_canary_with_current_page(self):
        guardian = self.client.get("/guardian/")

        self.assertEqual(guardian.status_code, 200)
        self.assertIn('href="/guardian/" aria-current="page"', guardian.text)
        self.assertIn('href="/visualizer/"', guardian.text)

    def test_canary_links_to_guardian_with_current_page(self):
        canary = self.client.get("/visualizer/")

        self.assertEqual(canary.status_code, 200)
        self.assertIn('href="/guardian/"', canary.text)
        self.assertIn('href="/visualizer/" aria-current="page"', canary.text)

    def test_canary_navigation_has_explicit_hit_area(self):
        css = (ROOT / "frontend" / "visualizer" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("grid-template-columns: minmax(156px, max-content)", css)
        self.assertIn(".surface-switch a", css)
        self.assertIn("display: inline-flex", css)
        self.assertIn("min-height: 24px", css)
        self.assertIn(".surface-switch a:focus-visible", css)

    def test_guardian_uses_only_existing_stt_and_v2_turn_contracts(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("/api/v1/experimental/stt", source)
        self.assertIn("/api/v1/experimental/v2/turn", source)
        self.assertIn("session_id: liveSessionId", source)
        self.assertIn("source_turn_number: sourceTurnNumber", source)
        self.assertNotIn("/api/v1/analyze", source)

    def test_manual_and_stt_text_converge_to_one_submit_function(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("async function submitCanonicalText", source)
        self.assertIn("await submitCanonicalText(manualText.value, 'TEXT')", source)
        self.assertIn("await submitCanonicalText(data.transcript, 'VOICE')", source)
        self.assertEqual(source.count("fetch('/api/v1/experimental/v2/turn'"), 1)

    def test_not_requested_cannot_create_intervention(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("status === 'ALLOW' && canary.action === 'warn_user'", source)
        self.assertIn("const intervention = !failed && isCanaryIntervention(turn)", source)
        self.assertNotIn("canary_status === 'NOT_REQUESTED' &&", source)

    def test_allow_warn_user_creates_intervention_and_entry_cues(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("state = UX_STATES.INTERVENTION", source)
        self.assertIn("playInterventionCueOnce(vm)", source)
        self.assertIn("requestHapticCueOnce(vm)", source)
        self.assertIn("lastInterventionKey", source)
        self.assertIn("lastHapticKey", source)
        self.assertIn("navigator.vibrate([90, 40, 90])", source)

    def test_deterministic_warning_mapping_copy(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("function warningFromEvidence", source)
        self.assertIn("Do not share that code.", source)
        self.assertIn("It's private. It's only for you.", source)
        self.assertIn("Do not make the transfer yet.", source)
        self.assertIn("Do not allow remote access.", source)
        self.assertIn("Do not share your credentials.", source)
        self.assertNotIn("scam_score", source)
        self.assertNotIn("scamScore", source)

    def test_analysis_failure_is_not_rendered_as_safe(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("state = UX_STATES.ANALYSIS_UNAVAILABLE", source)
        self.assertIn("No hemos podido escuchar esta parte de la llamada.", source)
        self.assertIn("No hemos podido comprobar esta parte de la llamada.", source)
        self.assertIn("Esto no significa que sea segura.", source)
        self.assertNotIn("analysis failure is safe", source.lower())

    def test_guardian_primary_html_avoids_engine_internals(self):
        html = (GUARDIAN_DIR / "index.html").read_text(encoding="utf-8")

        forbidden = (
            "CRITICAL",
            "HIGH",
            "SUSPICIOUS",
            "ESCALATE",
            "ALLOW",
            "DENY",
            "M2",
            "Gemini",
            "representational",
            "fingerprint",
            "STATUS",
            "LAST CHECK",
            "typed input",
            "turn.",
        )
        for token in forbidden:
            self.assertNotIn(token, html)
        self.assertIn("Guardian stays with you while you talk.", html)
        self.assertIn("Demo controls", html)

    def test_living_element_uses_amplitude_without_extra_audio_transport(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")
        html = (GUARDIAN_DIR / "index.html").read_text(encoding="utf-8")
        css = (GUARDIAN_DIR / "styles.css").read_text(encoding="utf-8")

        self.assertFalse((GUARDIAN_DIR / "presence.js").exists())
        self.assertIn("class=\"presence-mark\"", html)
        self.assertIn("class=\"presence-mark-core\"", html)
        self.assertNotIn("presence-field", html)
        self.assertNotIn("presence-atmosphere", html)
        self.assertNotIn("presence-fallback", html)
        self.assertNotIn("presence-asset", html)
        self.assertNotIn("decoding=\"async\"", html)
        self.assertNotIn("presence-canvas", html)
        self.assertNotIn("<canvas", html)
        self.assertNotIn("<svg", html)
        self.assertNotIn("<feTurbulence", html)
        self.assertNotIn("<feDisplacementMap", html)
        self.assertNotIn("<feGaussianBlur", html)
        self.assertNotIn("/guardian/presence.js", html)
        self.assertIn("createAnalyser", source)
        self.assertIn("function setPresenceState", source)
        self.assertIn("function setPresenceAmplitude", source)
        self.assertIn("function triggerPresenceIntervention", source)
        self.assertNotIn("PRESENCE_ASSET", source)
        self.assertNotIn("showPresenceAsset", source)
        self.assertNotIn("preloadPresenceAssets", source)
        self.assertNotIn("new Image()", source)
        self.assertIn("setPresenceState(nextState)", source)
        self.assertIn("setPresenceAmplitude(targetAmplitude)", source)
        self.assertIn("triggerPresenceIntervention()", source)
        self.assertIn("--presence-energy", source)
        self.assertIn("targetAmplitude += (bounded - targetAmplitude) * 0.22", source)
        self.assertNotIn("GuardianPresence", source)
        self.assertNotIn("WebGLRenderer", source)
        self.assertNotIn("three", source.lower())
        self.assertIn(".presence-mark", css)
        self.assertIn(".presence-mark::before", css)
        self.assertIn(".presence-mark::after", css)
        self.assertIn(".presence-mark-core", css)
        self.assertIn("@keyframes presenceMarkDrift", css)
        self.assertNotIn(".presence-field", css)
        self.assertNotIn(".presence-asset", css)
        self.assertNotIn(".presence-fallback", css)
        self.assertNotIn(".presence-atmosphere", css)
        self.assertNotIn("--presence-field", css)
        self.assertNotIn("object-fit: contain", css)
        self.assertNotIn("data-asset-status", css)
        self.assertNotIn("presence-canvas", css)
        self.assertNotIn("living-signal", css)
        self.assertNotIn("filter=\"url", html)
        self.assertNotIn("WebGLRenderer", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertEqual(source.count("audio_base64:"), 1)

    def test_conversation_mode_reduces_branding_and_avoids_duplicate_warning(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")
        html = (GUARDIAN_DIR / "index.html").read_text(encoding="utf-8")
        css = (GUARDIAN_DIR / "styles.css").read_text(encoding="utf-8")

        self.assertIn("let conversationActive = false", source)
        self.assertIn("function setConversationActive", source)
        self.assertIn("setConversationActive(true)", source)
        self.assertIn("setConversationActive(false)", source)
        self.assertIn("[data-mode=\"conversation\"] h1", css)
        self.assertIn("opacity: 0.32", css)
        self.assertNotIn("Guardian needs your attention.", source)
        self.assertNotIn("warning-primary", html)
        self.assertEqual(html.count("Do not share that code."), 0)

    def test_primary_recording_action_is_single_visible_control(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")
        html = (GUARDIAN_DIR / "index.html").read_text(encoding="utf-8")

        self.assertIn("function showRecordingAction", source)
        self.assertIn("showRecordingAction('stop')", source)
        self.assertIn("showRecordingAction('start')", source)
        self.assertIn('id="btn-record-stop" disabled hidden', html)
        self.assertNotIn("status-strip", html)

    def test_visual_preview_controls_are_demo_only_and_local(self):
        source = (GUARDIAN_DIR / "app.js").read_text(encoding="utf-8")
        html = (GUARDIAN_DIR / "index.html").read_text(encoding="utf-8")

        self.assertIn("Visual/demo preview only", html)
        self.assertIn("DEMO PREVIEW", html)
        self.assertIn("data-preview-state=\"PROTECTED_NO_INTERVENTION\"", html)
        self.assertIn("data-preview-state=\"INTERVENTION\"", html)
        self.assertIn("id=\"btn-preview-mic\"", html)
        self.assertIn("function renderPreviewState", source)
        self.assertIn("function startPreviewMicResponse", source)
        self.assertIn("previewMicStream = await navigator.mediaDevices.getUserMedia({ audio: true })", source)
        self.assertIn("startAmplitudeAnalysis(previewMicStream)", source)
        self.assertIn("stopTracks(previewMicStream)", source)
        self.assertIn("turn_status: 'VISUAL_PREVIEW'", source)
        self.assertIn("secondary: \"It's private. It's only for you.\"", source)
        self.assertNotIn("Demo preview only. No real Canary authorization was created.", source)
        preview_section = source[source.index("function renderPreviewState"):source.index("async function submitCanonicalText")]
        self.assertNotIn("fetch(", preview_section)
        self.assertNotIn("sourceTurnNumber += 1", preview_section)
        self.assertNotIn("MediaRecorder", preview_section)

    def test_bidirectional_speaker_provenance_requirement_is_recorded(self):
        doc = PROVENANCE_DOC.read_text(encoding="utf-8")

        self.assertIn("VOICE INPUT != SPEAKER IDENTITY", doc)
        self.assertIn("USER", doc)
        self.assertIn("CALLER", doc)
        self.assertIn("THIRD_PARTY_OR_UNKNOWN", doc)
        self.assertIn("telephony provider or call gateway", doc)
        self.assertIn("separated inbound and outbound audio channels or tracks", doc)
        self.assertIn("must not be inferred from transcript language", doc)
        self.assertIn("mixed audio", doc)
        self.assertIn("LLM guesses speaker", doc)
        self.assertIn("one utterance", doc)
        self.assertIn("one canonical submission", doc)


if __name__ == "__main__":
    unittest.main()
