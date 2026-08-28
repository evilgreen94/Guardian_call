"""Offline tests for the experimental local Gemma V2 extractor."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.experimental import extractor_v2 as gemini_v2
from guardian.experimental.gemma_extractor_v2 import (
    GEMMA_GENERATION_SCHEMA,
    GENERATION_SCHEMA_REVISION,
    GENERATION_SCHEMA_SHA256,
    GENERATION_OPTIONS,
    MODEL_TAG,
    PROMPT_REVISION,
    PROMPT_SHA256,
    SCHEMA_SHA256,
    SYSTEM_INSTRUCTION,
    GemmaExtractionStatus,
    GemmaV2ExtractionError,
    GemmaV2Extractor,
    LocalOllamaClient,
    gemma_generation_schema,
    normalize_response_text,
)
from guardian.experimental.signals_v2 import ASSET_COMPATIBILITY


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
    "manipulation": ["URGENCY"],
}


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeUrlopenResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps({"response": json.dumps(VALID_SIGNALS)}).encode("utf-8")


class TestGemmaExtractor(unittest.TestCase):
    def test_valid_structured_response_parses_and_uses_local_contract(self) -> None:
        client = FakeClient(
            {
                "model": MODEL_TAG,
                "response": json.dumps(VALID_SIGNALS),
                "done_reason": "stop",
                "eval_count": 10,
            }
        )
        observation = GemmaV2Extractor(client=client).extract("Synthetic OTP request")
        self.assertEqual(observation.signals.to_dict(), VALID_SIGNALS)
        self.assertEqual(observation.provider, "Ollama")
        self.assertEqual(observation.requested_model, MODEL_TAG)
        call = client.calls[0]
        self.assertEqual(call["model"], MODEL_TAG)
        self.assertEqual(call["options"], GENERATION_OPTIONS)
        self.assertIn("UNTRUSTED DATA", call["system"])
        self.assertIn("Synthetic OTP request", call["prompt"])

    def test_local_ollama_transport_sends_real_schema_in_format(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeUrlopenResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            response = LocalOllamaClient(timeout=7.0).generate(
                model=MODEL_TAG,
                system=SYSTEM_INSTRUCTION,
                prompt="Synthetic holdout",
                schema=gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA,
                options=GENERATION_OPTIONS,
            )

        self.assertEqual(response["response"], json.dumps(VALID_SIGNALS))
        self.assertEqual(captured["url"], "http://localhost:11434/api/generate")
        self.assertEqual(captured["timeout"], 7.0)
        self.assertEqual(captured["payload"]["format"], gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA)
        self.assertEqual(captured["payload"]["options"]["temperature"], 0.0)
        self.assertFalse(captured["payload"]["stream"])

    def test_extractor_sends_gemma_generation_schema_in_format(self) -> None:
        client = FakeClient({"response": json.dumps(VALID_SIGNALS)})
        GemmaV2Extractor(client=client).extract("Synthetic OTP request")
        self.assertEqual(client.calls[0]["schema"], GEMMA_GENERATION_SCHEMA)
        self.assertNotEqual(
            client.calls[0]["schema"],
            gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA,
        )

    def test_generation_schema_is_mechanically_derived(self) -> None:
        self.assertEqual(GEMMA_GENERATION_SCHEMA, gemma_generation_schema())
        canonical = json.loads(json.dumps(gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA))
        canonical["properties"]["identity_pretext"]["properties"]["claims"][
            "uniqueItems"
        ] = True
        canonical["properties"]["identity_pretext"]["properties"]["knowledge_categories"][
            "uniqueItems"
        ] = True
        canonical["properties"]["contexts"]["uniqueItems"] = True
        canonical["properties"]["manipulation"]["uniqueItems"] = True
        canonical["properties"]["interaction_acts"]["items"]["properties"]["asset"] = (
            GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"]["items"][
                "properties"
            ]["asset"]
        )
        self.assertEqual(GEMMA_GENERATION_SCHEMA, canonical)

    def test_each_asset_category_has_exactly_one_compatible_branch(self) -> None:
        asset_schema = GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"][
            "items"
        ]["properties"]["asset"]
        branches = asset_schema["oneOf"]
        category_branches = [
            branch for branch in branches if branch.get("type") == "object"
        ]
        observed_categories = [
            branch["properties"]["category"]["enum"][0]
            for branch in category_branches
        ]
        self.assertEqual(len(category_branches), len(ASSET_COMPATIBILITY))
        self.assertEqual(len(set(observed_categories)), len(ASSET_COMPATIBILITY))
        self.assertEqual(
            set(observed_categories),
            {category.value for category in ASSET_COMPATIBILITY},
        )

    def test_allowed_subtypes_appear_only_in_compatible_category_branches(self) -> None:
        asset_schema = GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"][
            "items"
        ]["properties"]["asset"]
        branches = [
            branch for branch in asset_schema["oneOf"] if branch.get("type") == "object"
        ]
        for category, subtypes in ASSET_COMPATIBILITY.items():
            branch = next(
                item
                for item in branches
                if item["properties"]["category"]["enum"] == [category.value]
            )
            self.assertEqual(
                set(branch["properties"]["subtype"]["enum"]),
                {subtype.value for subtype in subtypes},
            )
        occurrences = {}
        for branch in branches:
            category = branch["properties"]["category"]["enum"][0]
            for subtype in branch["properties"]["subtype"]["enum"]:
                occurrences.setdefault(subtype, []).append(category)
        for subtype, categories in occurrences.items():
            self.assertEqual(len(categories), 1, subtype)

    def test_invalid_category_subtype_combinations_are_excluded(self) -> None:
        asset_schema = GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"][
            "items"
        ]["properties"]["asset"]
        branches = [
            branch for branch in asset_schema["oneOf"] if branch.get("type") == "object"
        ]
        account_control = next(
            branch
            for branch in branches
            if branch["properties"]["category"]["enum"] == ["ACCOUNT_CONTROL"]
        )
        self.assertNotIn(
            "UNSPECIFIED_SECURITY_CODE",
            account_control["properties"]["subtype"]["enum"],
        )

    def test_null_asset_remains_accepted(self) -> None:
        asset_schema = GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"][
            "items"
        ]["properties"]["asset"]
        self.assertIn({"type": "null"}, asset_schema["oneOf"])

    def test_unique_items_is_applied_to_duplicate_free_enum_sets(self) -> None:
        self.assertTrue(
            GEMMA_GENERATION_SCHEMA["properties"]["identity_pretext"]["properties"][
                "claims"
            ]["uniqueItems"]
        )
        self.assertTrue(
            GEMMA_GENERATION_SCHEMA["properties"]["identity_pretext"]["properties"][
                "knowledge_categories"
            ]["uniqueItems"]
        )
        self.assertTrue(GEMMA_GENERATION_SCHEMA["properties"]["contexts"]["uniqueItems"])
        self.assertTrue(GEMMA_GENERATION_SCHEMA["properties"]["manipulation"]["uniqueItems"])

    def test_no_semantic_action_direction_actor_destination_constraints_added(self) -> None:
        act = GEMMA_GENERATION_SCHEMA["properties"]["interaction_acts"]["items"]
        for field in ("action", "semantic_direction", "actor", "destination"):
            self.assertEqual(
                act["properties"][field],
                gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA["properties"][
                    "interaction_acts"
                ]["items"]["properties"][field],
            )

    def test_valid_multi_act_response_parses(self) -> None:
        value = json.loads(json.dumps(VALID_SIGNALS))
        value["interaction_acts"].append(
            {
                "action": "DISCLOSE",
                "asset": {"category": "SECRET", "subtype": "PASSWORD"},
                "semantic_direction": "NEGATION",
                "actor": "USER",
                "destination": "CALLER",
            }
        )
        observation = GemmaV2Extractor(
            client=FakeClient({"response": json.dumps(value)})
        ).extract("Synthetic mixed input")
        self.assertEqual(len(observation.signals.interaction_acts), 2)

    def test_strict_enum_handling_rejects_unknown_values(self) -> None:
        value = json.loads(json.dumps(VALID_SIGNALS))
        value["interaction_acts"][0]["action"] = "TELL"
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": json.dumps(value)})).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.INVALID_ENUM)

    def test_malformed_json_is_not_repaired(self) -> None:
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": "{bad"})).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.JSON_PARSE_FAILURE)

    def test_markdown_fenced_json_is_allowed_as_transport_artifact(self) -> None:
        raw = "```json\n" + json.dumps(VALID_SIGNALS) + "\n```"
        observation = GemmaV2Extractor(client=FakeClient({"response": raw})).extract("x")
        self.assertEqual(observation.signals.to_dict(), VALID_SIGNALS)
        self.assertEqual(normalize_response_text(raw), json.dumps(VALID_SIGNALS))

    def test_extra_field_rejection_is_schema_failure(self) -> None:
        value = json.loads(json.dumps(VALID_SIGNALS))
        value["raw_response"] = "forbidden"
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": json.dumps(value)})).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.SCHEMA_FAILURE)

    def test_invalid_asset_rejection(self) -> None:
        value = json.loads(json.dumps(VALID_SIGNALS))
        value["interaction_acts"][0]["asset"] = {
            "category": "DEVICE_ACCESS",
            "subtype": "OTP",
        }
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": json.dumps(value)})).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.INVALID_ENUM)

    def test_invalid_actor_destination_rejection(self) -> None:
        for field in ("actor", "destination"):
            value = json.loads(json.dumps(VALID_SIGNALS))
            value["interaction_acts"][0][field] = "BANK"
            with self.subTest(field=field):
                with self.assertRaises(GemmaV2ExtractionError) as context:
                    GemmaV2Extractor(client=FakeClient({"response": json.dumps(value)})).extract("x")
                self.assertEqual(context.exception.status, GemmaExtractionStatus.INVALID_ENUM)

    def test_empty_response_is_distinct(self) -> None:
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": "  "})).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.EMPTY_RESPONSE)

    def test_local_transport_unavailable_is_sanitized(self) -> None:
        error = GemmaV2ExtractionError(GemmaExtractionStatus.OLLAMA_UNAVAILABLE)
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient(error=error)).extract("secret text")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.OLLAMA_UNAVAILABLE)
        self.assertNotIn("secret text", json.dumps(context.exception.to_dict()))

    def test_model_error_is_sanitized(self) -> None:
        error = GemmaV2ExtractionError(
            GemmaExtractionStatus.MODEL_ERROR,
            provider_code="synthetic model error",
        )
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient(error=error)).extract("x")
        self.assertEqual(context.exception.status, GemmaExtractionStatus.MODEL_ERROR)

    def test_no_raw_response_or_transcript_persistence_on_failure(self) -> None:
        raw = json.dumps({**VALID_SIGNALS, "secret": "123456"})
        with self.assertRaises(GemmaV2ExtractionError) as context:
            GemmaV2Extractor(client=FakeClient({"response": raw})).extract("Tell me 123456")
        serialized = json.dumps(context.exception.to_dict(), sort_keys=True)
        self.assertNotIn(raw, serialized)
        self.assertNotIn("123456", serialized)
        self.assertIsNotNone(context.exception.response_sha256)
        self.assertIsNotNone(context.exception.response_bytes)

    def test_identity_assurance_absent_from_model_controlled_schema(self) -> None:
        serialized = json.dumps(gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA, sort_keys=True)
        self.assertNotIn("identity_assurance", serialized.lower())
        self.assertIn("External identity assurance is outside this schema", SYSTEM_INSTRUCTION)

    def test_gemini_extractor_prompt_contract_reference(self) -> None:
        self.assertEqual(
            gemini_v2.PROMPT_REVISION,
            "m2.5-family-manipulation-prompt-v1",
        )
        self.assertEqual(
            gemini_v2.PROMPT_SHA256,
            "9b43516799d62627b3a6198262ac120d16bc139cb0d2f721bc4abd19e7b6c83f",
        )

    def test_production_isolation(self) -> None:
        self.assertNotIn("GemmaV2Extractor", guardian.__all__)
        self.assertFalse(hasattr(guardian, "GemmaV2Extractor"))

    def test_prompt_hash_stability(self) -> None:
        self.assertEqual(PROMPT_REVISION, "m1.4a-gemma-prompt-v1")
        self.assertEqual(len(PROMPT_SHA256), 64)
        self.assertEqual(
            PROMPT_SHA256,
            "5ee50709f10022ebc3934756fd94cd89f9359b5644bdd9b85e74f78318159957",
        )

    def test_schema_hash_stability(self) -> None:
        self.assertEqual(
            SCHEMA_SHA256,
            "5dab085e5088fc7a5e8aed421a39cdf45d23ccf5c5935f7aecef676aba93254c",
        )
        self.assertEqual(
            gemini_v2.SCHEMA_SHA256,
            "5dab085e5088fc7a5e8aed421a39cdf45d23ccf5c5935f7aecef676aba93254c",
        )
        self.assertEqual(
            gemini_v2.SCAM_SIGNALS_V2_JSON_SCHEMA["properties"][
                "interaction_acts"
            ]["items"]["properties"]["asset"],
            {
                "anyOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": [
                                    "SECRET",
                                    "PAYMENT_CARD_DATA",
                                    "ECONOMIC_VALUE",
                                    "ACCOUNT_CONTROL",
                                    "DEVICE_ACCESS",
                                ],
                            },
                            "subtype": {
                                "type": "string",
                                "enum": [
                                    "OTP",
                                    "PASSWORD",
                                    "RECOVERY_CODE",
                                    "CARD_SECURITY_CODE",
                                    "GIFT_CARD_REDEMPTION_CODE",
                                    "SEED_PHRASE",
                                    "PRIVATE_KEY",
                                    "UNSPECIFIED_SECURITY_CODE",
                                    "CARD_NUMBER",
                                    "CARD_EXPIRY",
                                    "FIAT_FUNDS",
                                    "PAYMENT_APP_PAYMENT",
                                    "GIFT_CARD",
                                    "CASH",
                                    "CRYPTO_ASSET",
                                    "LOGIN_APPROVAL",
                                    "RECOVERY_EMAIL",
                                    "RECOVERY_PHONE",
                                    "TWO_FACTOR_SETTING",
                                    "PASSWORD_RESET_LINK",
                                    "REMOTE_SOFTWARE",
                                    "REMOTE_CONTROL",
                                    "SCREEN_CONTENT",
                                ],
                            },
                        },
                        "required": ["category", "subtype"],
                    },
                ]
            },
        )

    def test_generation_schema_hash_stability(self) -> None:
        self.assertEqual(
            GENERATION_SCHEMA_REVISION,
            "m1.4a-gemma-generation-schema-v2",
        )
        self.assertEqual(len(GENERATION_SCHEMA_SHA256), 64)
        self.assertEqual(
            GENERATION_SCHEMA_SHA256,
            "1806edd5f63967943076440682d19cf0bb5cc902596bb73c7f052570aad8b745",
        )

    def test_non_localhost_ollama_endpoint_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "localhost"):
            LocalOllamaClient(base_url="https://example.com")


if __name__ == "__main__":
    unittest.main()
