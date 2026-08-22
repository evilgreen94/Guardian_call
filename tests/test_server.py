"""Unit and integration tests for Guardian Call FastAPI server and SSE streaming."""

import asyncio
import json
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from backend.guardian.extractor import ExtractionError
from backend.guardian.models import RiskLevel
from backend.guardian.signals import ScamSignals, create_signals
from backend.server import (
    LazyGeminiExtractor,
    app,
    broadcast_event,
    event_subscribers,
    stream_events,
)


class TestServerEndpoints(unittest.TestCase):
    """Tests for FastAPI endpoints and SSE streaming."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoints(self) -> None:
        """Verify /health and /api/v1/health return 200 and healthy metadata."""
        for path in ("/health", "/api/v1/health"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["service"], "guardian-call-backend")
            self.assertIn("model", data)
            self.assertIn("has_api_key", data)

    def test_scenarios_endpoint(self) -> None:
        """Verify /api/v1/scenarios returns the 4 approved canonical scenarios."""
        response = self.client.get("/api/v1/scenarios")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["count"], 4)

        scenario_ids = [s["id"] for s in data["scenarios"]]
        self.assertIn("legitimate_bank_notification_01", scenario_ids)
        self.assertIn("bank_otp_scam_01", scenario_ids)
        self.assertIn("bank_secure_vault_01", scenario_ids)
        self.assertIn("tech_support_anydesk_01", scenario_ids)

        for sc in data["scenarios"]:
            self.assertTrue(sc["title"])
            self.assertIsInstance(sc["dialogue"], list)
            self.assertGreater(len(sc["dialogue"]), 0)

    @patch.object(LazyGeminiExtractor, "extract_signals")
    def test_analyze_endpoint_critical_otp_theft(self, mock_extract) -> None:
        """Verify POST /api/v1/analyze with OTP scam produces CRITICAL risk and USER_WARNING."""
        mock_extract.return_value = create_signals(
            identity_claim="bank",
            identity_verified=False,
            financial_context=True,
            urgency=True,
            otp_request=True,
            requested_action="share_otp",
        )

        payload = {"text": "Tell me the six-digit code you just received from your bank."}
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsNotNone(data["signals"])
        self.assertEqual(data["signals"]["otp_request"], True)
        self.assertEqual(data["signals"]["requested_action"], "share_otp")

        self.assertIsNotNone(data["risk_assessment"])
        self.assertEqual(data["risk_assessment"]["level"], "CRITICAL")

        self.assertIsNotNone(data["canary_decision"])
        self.assertEqual(data["canary_decision"]["decision"], "ALLOW")

        self.assertIsNotNone(data["warning"])
        self.assertEqual(data["warning"]["payload"]["headline"], "POSIBLE ESTAFA")
        self.assertIn("NO DIGA ESE CÓDIGO", data["warning"]["payload"]["directives"])

        event_types = [e["event_type"] for e in data["events"]]
        expected_sequence = [
            "INPUT_RECEIVED",
            "SIGNAL_DETECTED",
            "RISK_UPDATED",
            "CANARY_EVALUATION",
            "ACTION_ALLOWED",
            "USER_WARNING",
        ]
        self.assertEqual(event_types, expected_sequence)

    @patch.object(LazyGeminiExtractor, "extract_signals")
    def test_analyze_endpoint_legitimate_call(self, mock_extract) -> None:
        """Verify POST /api/v1/analyze with benign neutral text produces NORMAL risk and DENY decision."""
        mock_extract.return_value = ScamSignals()

        payload = {"text": "Hola, le llamo de su oficina para desearle un buen día."}
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["risk_assessment"]["level"], "NORMAL")
        self.assertEqual(data["canary_decision"]["decision"], "DENY")
        self.assertIsNone(data["warning"])

        event_types = [e["event_type"] for e in data["events"]]
        expected_sequence = [
            "INPUT_RECEIVED",
            "SIGNAL_DETECTED",
            "RISK_UPDATED",
            "CANARY_EVALUATION",
            "ACTION_DENIED",
        ]
        self.assertEqual(event_types, expected_sequence)

    @patch.object(LazyGeminiExtractor, "extract_signals")
    def test_analyze_endpoint_extraction_failure_is_explicit(self, mock_extract) -> None:
        """Verify extraction failure halts cleanly and does NOT fabricate HIGH or NORMAL risk."""
        mock_extract.side_effect = ExtractionError("Simulated Gemini error", error_type="NETWORK_ERROR")

        payload = {"text": "Random text causing extraction error."}
        response = self.client.post("/api/v1/analyze", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsNone(data["signals"])
        self.assertIsNone(data["risk_assessment"])
        self.assertIsNone(data["canary_decision"])
        self.assertIsNone(data["warning"])
        self.assertIsNotNone(data["error"])

        event_types = [e["event_type"] for e in data["events"]]
        self.assertEqual(event_types, ["INPUT_RECEIVED", "EXTRACTION_FAILED"])

    def test_events_stream_sse_generator(self) -> None:
        """Verify SSE stream generator yields STREAM_CONNECTED and broadcasts real domain events."""
        async def run_sse_test():
            response = await stream_events()
            gen = response.body_iterator

            # Read first event: initial connection ping
            first_chunk = await anext(gen)
            self.assertTrue(first_chunk.startswith("data:"))
            init_data = json.loads(first_chunk[len("data:"):].strip())
            self.assertEqual(init_data["event_type"], "STREAM_CONNECTED")

            # Broadcast a real test domain event and verify receipt
            test_event = {
                "event_type": "SIGNAL_DETECTED",
                "payload": {"signals": {"otp_request": True}},
                "timestamp": "2026-08-23T00:00:00Z",
            }
            await broadcast_event(test_event)

            second_chunk = await anext(gen)
            self.assertTrue(second_chunk.startswith("data:"))
            broadcasted_data = json.loads(second_chunk[len("data:"):].strip())
            self.assertEqual(broadcasted_data["event_type"], "SIGNAL_DETECTED")
            self.assertEqual(broadcasted_data["payload"]["signals"]["otp_request"], True)

            # Cleanup generator
            await gen.aclose()

        asyncio.run(run_sse_test())


if __name__ == "__main__":
    unittest.main()
