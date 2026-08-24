"""Offline tests for the frozen experimental Gemini V2 adapter."""

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.experimental.extractor_v2 import (
    PROMPT_CANONICAL_BYTES,
    PROMPT_REVISION,
    PROMPT_SHA256,
    SCAM_SIGNALS_V2_JSON_SCHEMA,
    SCHEMA_CANONICAL_BYTES,
    SCHEMA_REVISION,
    SCHEMA_SHA256,
    SYSTEM_INSTRUCTION,
    GeminiV2Extractor,
    V2ExtractionError,
    V2ExtractionFailureKind,
    canonical_json_bytes,
    render_user_prompt,
    request_prompt_sha256,
)


VALID_SIGNALS = {
    "identity_pretext": {"claims": ["BANK"], "knowledge_categories": []},
    "contexts": ["BANKING"],
    "interaction_acts": [
        {
            "action": "DISCLOSE",
            "asset": {"category": "SECRET", "subtype": "OTP"},
            "semantic_direction": "DIRECT_REQUEST",
            "actor": "USER",
            "destination": "CALLER",
        }
    ],
    "manipulation": [],
}


class FakeResponse:
    def __init__(self, value, *, model_version="model-version-1", response_id="response-1"):
        self.text = value
        self.model_version = model_version
        self.response_id = response_id


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.models = FakeModels(response=response, error=error)


class QuotaError(Exception):
    code = 429
    status = "RESOURCE_EXHAUSTED"


class TestCanonicalFingerprints(unittest.TestCase):
    def test_frozen_revisions_and_hashes(self) -> None:
        self.assertEqual(PROMPT_REVISION, "m1.2b-prompt-v1")
        self.assertEqual(SCHEMA_REVISION, "m1.2b-schema-v1")
        self.assertEqual(
            PROMPT_SHA256,
            "f2b4c476add079b6f082d9c38c64700817683c5f9668c48d8e555e3d833e08d4",
        )
        self.assertEqual(
            SCHEMA_SHA256,
            "5dab085e5088fc7a5e8aed421a39cdf45d23ccf5c5935f7aecef676aba93254c",
        )
        self.assertNotIn(b"\r", PROMPT_CANONICAL_BYTES)
        self.assertNotIn(b"\r", SCHEMA_CANONICAL_BYTES)

    def test_canonical_json_is_order_and_platform_independent(self) -> None:
        first = canonical_json_bytes({"b": "á", "a": [2, 1]})
        second = canonical_json_bytes({"a": [2, 1], "b": "á"})
        self.assertEqual(first, second)
        self.assertEqual(first, b'{"a":[2,1],"b":"\xc3\xa1"}')

    def test_request_hash_uses_exact_unnormalized_provider_strings(self) -> None:
        composed = "código"
        decomposed = "co\u0301digo"
        self.assertNotEqual(request_prompt_sha256(composed), request_prompt_sha256(decomposed))
        self.assertEqual(render_user_prompt(" a "), render_user_prompt(" a "))
        self.assertIn("\n a \n", render_user_prompt(" a "))


class TestGeminiV2Extractor(unittest.TestCase):
    def test_valid_structured_response_parses_and_preserves_real_metadata(self) -> None:
        response = FakeResponse(json.dumps(VALID_SIGNALS))
        client = FakeClient(response=response)
        extractor = GeminiV2Extractor(model="gemini-test", client=client)
        observation = extractor.extract("Léame el código.")
        self.assertEqual(observation.signals.to_dict(), VALID_SIGNALS)
        self.assertEqual(observation.requested_model, "gemini-test")
        self.assertEqual(observation.returned_model_version, "model-version-1")
        self.assertEqual(observation.response_id, "response-1")
        call = client.models.calls[0]
        self.assertEqual(call["model"], "gemini-test")
        self.assertEqual(call["contents"], render_user_prompt("Léame el código."))
        config = call["config"]
        self.assertEqual(config.system_instruction, SYSTEM_INSTRUCTION)
        self.assertEqual(config.response_json_schema, SCAM_SIGNALS_V2_JSON_SCHEMA)
        self.assertEqual(config.temperature, 0.0)

    def test_identity_assurance_is_absent_from_provider_contract(self) -> None:
        serialized_schema = json.dumps(SCAM_SIGNALS_V2_JSON_SCHEMA, sort_keys=True)
        self.assertNotIn("identity_assurance", serialized_schema.lower())
        self.assertNotIn("verified_externally", serialized_schema.lower())
        self.assertNotIn("verification_failed", serialized_schema.lower())
        self.assertIn("Identity assurance is external", SYSTEM_INSTRUCTION)

    def test_multiple_acts_and_ambiguity_values_survive_strict_parse(self) -> None:
        value = json.loads(json.dumps(VALID_SIGNALS))
        value["interaction_acts"].append(
            {
                "action": "DISCLOSE",
                "asset": {"category": "SECRET", "subtype": "UNSPECIFIED_SECURITY_CODE"},
                "semantic_direction": "QUESTION",
                "actor": "UNKNOWN",
                "destination": "UNKNOWN",
            }
        )
        observation = GeminiV2Extractor(
            model="gemini-test", client=FakeClient(response=FakeResponse(json.dumps(value)))
        ).extract("Synthetic mixed input")
        self.assertEqual(len(observation.signals.interaction_acts), 2)

    def test_malformed_or_schema_invalid_response_never_becomes_empty_signals(self) -> None:
        for raw in ("not json", json.dumps({**VALID_SIGNALS, "raw_secret": "123456"})):
            with self.subTest(raw=raw):
                extractor = GeminiV2Extractor(
                    model="gemini-test", client=FakeClient(response=FakeResponse(raw))
                )
                with self.assertRaises(V2ExtractionError) as context:
                    extractor.extract("Synthetic text")
                error = context.exception
                self.assertEqual(error.kind, V2ExtractionFailureKind.PARSE_SCHEMA_FAILURE)
                self.assertIsNotNone(error.response_sha256)
                self.assertNotIn(raw, json.dumps(error.to_dict()))

    def test_quota_and_other_provider_failures_are_distinct(self) -> None:
        quota = GeminiV2Extractor(
            model="gemini-test", client=FakeClient(error=QuotaError("quota"))
        )
        with self.assertRaises(V2ExtractionError) as quota_context:
            quota.extract("Synthetic text")
        self.assertEqual(quota_context.exception.kind, V2ExtractionFailureKind.QUOTA_EXHAUSTED)
        self.assertEqual(quota_context.exception.http_status, 429)

        provider = GeminiV2Extractor(
            model="gemini-test", client=FakeClient(error=RuntimeError("offline"))
        )
        with self.assertRaises(V2ExtractionError) as provider_context:
            provider.extract("Synthetic text")
        self.assertEqual(
            provider_context.exception.kind,
            V2ExtractionFailureKind.PROVIDER_API_FAILURE,
        )

    def test_experimental_extractor_is_not_exported_from_guardian(self) -> None:
        self.assertNotIn("GeminiV2Extractor", guardian.__all__)
        self.assertFalse(hasattr(guardian, "GeminiV2Extractor"))


if __name__ == "__main__":
    unittest.main()
