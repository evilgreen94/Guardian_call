"""Contract and unit tests for the Gemini signal extractor (100% mocked, zero network calls)."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.extractor import (
    DEFAULT_GEMINI_MODEL,
    EXTRACTION_SYSTEM_INSTRUCTION,
    ExtractionError,
    GeminiSignalExtractor,
    MockSignalExtractor,
    SCAM_SIGNALS_JSON_SCHEMA,
)
from guardian.models import ScamSignals


class TestGeminiSignalExtractor(unittest.TestCase):
    """Test suite for GeminiSignalExtractor contracts and error boundaries."""

    def test_system_instruction_boundary(self) -> None:
        """Prompt constraint: System instruction must be factual extraction only without risk logic."""
        instruction_lower = EXTRACTION_SYSTEM_INSTRUCTION.lower()
        self.assertIn("factual", instruction_lower)
        self.assertIn("do not determine risk", instruction_lower)
        self.assertIn("do not calculate scam probabilities", instruction_lower)
        self.assertIn("do not advise actions", instruction_lower)

    def test_default_model_is_gemini_3_6_flash(self) -> None:
        """Verify the canonical default model is gemini-3.6-flash."""
        self.assertEqual(DEFAULT_GEMINI_MODEL, "gemini-3.6-flash")

    def test_m0_schema_uses_standard_json_schema_contract(self) -> None:
        """Verify the provider request uses the current JSON Schema contract."""
        self.assertEqual(SCAM_SIGNALS_JSON_SCHEMA["type"], "object")
        self.assertFalse(SCAM_SIGNALS_JSON_SCHEMA["additionalProperties"])
        self.assertEqual(
            SCAM_SIGNALS_JSON_SCHEMA["properties"]["identity_claim"]["type"],
            ["string", "null"],
        )
        self.assertEqual(
            SCAM_SIGNALS_JSON_SCHEMA["properties"]["requested_action"]["type"],
            ["string", "null"],
        )
        self.assertIn("identity_claim", SCAM_SIGNALS_JSON_SCHEMA["required"])
        self.assertIn("requested_action", SCAM_SIGNALS_JSON_SCHEMA["required"])

    def test_missing_api_key_raises_typed_extraction_error(self) -> None:
        """Verify instantiating without API key raises typed ExtractionError."""
        # Clear env vars temporarily
        orig_gemini_key = os.environ.pop("GEMINI_API_KEY", None)
        orig_google_key = os.environ.pop("GOOGLE_API_KEY", None)

        try:
            with self.assertRaises(ExtractionError) as ctx:
                GeminiSignalExtractor(api_key=None, client=None)
            self.assertEqual(ctx.exception.error_type, "API_KEY_MISSING")
            self.assertIn("No Gemini API key", str(ctx.exception))
        finally:
            if orig_gemini_key:
                os.environ["GEMINI_API_KEY"] = orig_gemini_key
            if orig_google_key:
                os.environ["GOOGLE_API_KEY"] = orig_google_key

    def test_model_override_via_env_var_and_param(self) -> None:
        """Verify model selection can be overridden via constructor param or GEMINI_MODEL env var."""
        mock_client = MagicMock()

        # Override via constructor
        extractor_param = GeminiSignalExtractor(model="gemini-test-param", client=mock_client)
        self.assertEqual(extractor_param.model, "gemini-test-param")

        # Override via environment variable
        os.environ["GEMINI_MODEL"] = "gemini-test-env"
        try:
            extractor_env = GeminiSignalExtractor(client=mock_client)
            self.assertEqual(extractor_env.model, "gemini-test-env")
        finally:
            del os.environ["GEMINI_MODEL"]

    def test_canonical_m0_otp_extraction_success(self) -> None:
        """Verify valid Gemini JSON response parses into ScamSignals."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            '{\n'
            '  "identity_claim": "bank",\n'
            '  "identity_verified": false,\n'
            '  "financial_context": true,\n'
            '  "urgency": true,\n'
            '  "secrecy_request": false,\n'
            '  "otp_request": true,\n'
            '  "password_request": false,\n'
            '  "transfer_request": false,\n'
            '  "remote_access_request": false,\n'
            '  "requested_action": "share_otp"\n'
            '}'
        )
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiSignalExtractor(client=mock_client)
        signals = extractor.extract_signals("Tell me the six-digit code you just received.")

        self.assertTrue(signals.otp_request)
        self.assertEqual(signals.requested_action, "share_otp")
        self.assertEqual(signals.identity_claim, "bank")
        self.assertFalse(signals.identity_verified)
        self.assertTrue(signals.urgency)
        self.assertTrue(signals.financial_context)

        # Verify SDK client call arguments
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], DEFAULT_GEMINI_MODEL)
        self.assertIn("Tell me the six-digit code", call_kwargs["contents"])
        config = call_kwargs["config"]
        self.assertEqual(config.response_json_schema, SCAM_SIGNALS_JSON_SCHEMA)

    def test_legitimate_otp_extraction_success(self) -> None:
        """Verify extraction of legitimate in-app OTP guidance."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            '{\n'
            '  "identity_claim": "bank",\n'
            '  "identity_verified": true,\n'
            '  "financial_context": true,\n'
            '  "urgency": false,\n'
            '  "secrecy_request": false,\n'
            '  "otp_request": true,\n'
            '  "password_request": false,\n'
            '  "transfer_request": false,\n'
            '  "remote_access_request": false,\n'
            '  "requested_action": "enter_in_app"\n'
            '}'
        )
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiSignalExtractor(client=mock_client)
        signals = extractor.extract_signals("We sent a verification code to your app. Please enter it in the app.")

        self.assertTrue(signals.otp_request)
        self.assertEqual(signals.requested_action, "enter_in_app")
        self.assertTrue(signals.identity_verified)

    def test_malformed_json_raises_schema_error(self) -> None:
        """Verify malformed JSON from Gemini raises ExtractionError and NEVER returns empty ScamSignals."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "{ malformed json: not valid ... "
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiSignalExtractor(client=mock_client)

        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract_signals("Some text")

        self.assertEqual(ctx.exception.error_type, "SCHEMA_ERROR")
        self.assertIsNotNone(ctx.exception.raw_response)

    def test_empty_response_raises_empty_response_error(self) -> None:
        """Verify empty text response from model raises ExtractionError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "   "
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiSignalExtractor(client=mock_client)

        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract_signals("Some text")

        self.assertEqual(ctx.exception.error_type, "EMPTY_RESPONSE")

    def test_network_failure_raises_network_error(self) -> None:
        """Verify network or SDK exception raises typed ExtractionError(error_type='NETWORK_ERROR')."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = ConnectionError("Network unreachable")

        extractor = GeminiSignalExtractor(client=mock_client)

        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract_signals("Some text")

        self.assertEqual(ctx.exception.error_type, "NETWORK_ERROR")
        self.assertIn("Network unreachable", str(ctx.exception))

    def test_empty_input_text_raises_invalid_input_error(self) -> None:
        """Verify passing blank input raises ExtractionError."""
        mock_client = MagicMock()
        extractor = GeminiSignalExtractor(client=mock_client)

        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract_signals("   ")

        self.assertEqual(ctx.exception.error_type, "INVALID_INPUT")


class TestMockSignalExtractor(unittest.TestCase):
    """Test suite for MockSignalExtractor helper."""

    def test_mock_returns_configured_signals(self) -> None:
        preset = ScamSignals(otp_request=True, requested_action="share_otp")
        mock_ext = MockSignalExtractor(signals=preset)
        self.assertEqual(mock_ext.extract_signals("Any text"), preset)

    def test_mock_raises_configured_error(self) -> None:
        mock_err = ExtractionError("Simulated failure", error_type="SIMULATED")
        mock_ext = MockSignalExtractor(error=mock_err)
        with self.assertRaises(ExtractionError) as ctx:
            mock_ext.extract_signals("Any text")
        self.assertEqual(ctx.exception.error_type, "SIMULATED")


if __name__ == "__main__":
    unittest.main()
