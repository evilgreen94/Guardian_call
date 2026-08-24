"""Tests for the isolated M1.1 ScamSignalsV2 experiment."""

import json
import sys
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.models import ScamSignals
from guardian.experimental.signals_v2 import (
    ASSET_COMPATIBILITY,
    VOCABULARY_JUSTIFICATIONS,
    ActionTypeV2,
    Actor,
    AssetCategory,
    AssetSubtype,
    ClaimedEntityType,
    ContextType,
    Destination,
    IdentityAssurance,
    IdentityAssuranceContext,
    IdentityPretext,
    InteractionAct,
    KnowledgeCategory,
    ManipulationType,
    ScamSignalsV2,
    SemanticDirection,
    SensitiveAsset,
)


CORPUS_PATH = ROOT / "scenarios" / "m1_adversarial_scenarios.json"


class TestScamSignalsV2(unittest.TestCase):
    """Validate schema isolation, construction, and deterministic I/O."""

    def test_m0_schema_and_exports_are_unchanged(self) -> None:
        self.assertEqual(
            [item.name for item in fields(ScamSignals)],
            [
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
        )
        self.assertNotIn("ScamSignalsV2", guardian.__all__)
        self.assertFalse(hasattr(guardian, "ScamSignalsV2"))

    def test_models_are_deeply_immutable_at_the_container_level(self) -> None:
        signals = ScamSignalsV2(
            identity_pretext=IdentityPretext(
                claims=frozenset({ClaimedEntityType.BANK})
            ),
            contexts=frozenset({ContextType.BANKING}),
            interaction_acts=(),
            manipulation=frozenset(),
        )
        with self.assertRaises(FrozenInstanceError):
            signals.contexts = frozenset()  # type: ignore[misc]
        with self.assertRaises(TypeError):
            ScamSignalsV2(contexts={ContextType.BANKING})  # type: ignore[arg-type]

    def test_serialization_is_deterministic_and_round_trips(self) -> None:
        raw = {
            "identity_pretext": {
                "claims": ["TELECOM", "BANK"],
                "knowledge_categories": ["NAME", "ADDRESS"],
            },
            "contexts": ["TELECOM", "BANKING"],
            "interaction_acts": [
                {
                    "action": "DISCLOSE",
                    "asset": {"category": "SECRET", "subtype": "OTP"},
                    "semantic_direction": "DIRECT_REQUEST",
                    "actor": "USER",
                    "destination": "CALLER",
                }
            ],
            "manipulation": ["URGENCY", "SECRECY"],
        }
        signals = ScamSignalsV2.from_dict(raw)
        serialized = signals.to_dict()
        self.assertEqual(serialized["contexts"], ["BANKING", "TELECOM"])
        self.assertEqual(serialized["identity_pretext"]["claims"], ["BANK", "TELECOM"])
        self.assertEqual(ScamSignalsV2.from_dict(serialized), signals)

    def test_identity_assurance_is_external_and_defaults_unverified(self) -> None:
        context = IdentityAssuranceContext()
        self.assertEqual(context.identity_assurance, IdentityAssurance.UNVERIFIED)
        self.assertNotIn("identity_assurance", ScamSignalsV2().to_dict())

    def test_direct_construction_rejects_invalid_asset_combinations(self) -> None:
        invalid = (
            (AssetCategory.DEVICE_ACCESS, AssetSubtype.OTP),
            (AssetCategory.ECONOMIC_VALUE, AssetSubtype.PASSWORD),
            (AssetCategory.PAYMENT_CARD_DATA, AssetSubtype.SEED_PHRASE),
        )
        for category, subtype in invalid:
            with self.subTest(category=category, subtype=subtype):
                with self.assertRaises(ValueError):
                    SensitiveAsset(category, subtype)

    def test_parser_rejects_invalid_asset_combinations(self) -> None:
        raw = self._minimal_signals()
        raw["interaction_acts"] = [
            {
                "action": "DISCLOSE",
                "asset": {"category": "DEVICE_ACCESS", "subtype": "OTP"},
                "semantic_direction": "DIRECT_REQUEST",
                "actor": "USER",
                "destination": "CALLER",
            }
        ]
        with self.assertRaisesRegex(ValueError, "incompatible"):
            ScamSignalsV2.from_dict(raw)

    def test_asset_compatibility_is_explicit_and_exhaustive(self) -> None:
        self.assertEqual(set(ASSET_COMPATIBILITY), set(AssetCategory))
        mapped = [subtype for values in ASSET_COMPATIBILITY.values() for subtype in values]
        self.assertEqual(set(mapped), set(AssetSubtype))
        self.assertEqual(len(mapped), len(set(mapped)))

    def test_strict_parser_rejects_unknown_and_sensitive_value_fields(self) -> None:
        for forbidden in ("scam_type", "raw_value", "secret", "value", "transcript"):
            raw = self._minimal_signals()
            raw[forbidden] = "synthetic-but-forbidden"
            with self.subTest(field=forbidden):
                with self.assertRaisesRegex(ValueError, "unexpected"):
                    ScamSignalsV2.from_dict(raw)

    @staticmethod
    def _minimal_signals() -> dict:
        return {
            "identity_pretext": {"claims": [], "knowledge_categories": []},
            "contexts": [],
            "interaction_acts": [],
            "manipulation": [],
        }


class TestV2CorpusMapping(unittest.TestCase):
    """Prove complete, evidence-bounded representation of the 57 cases."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.library = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        cls.scenarios = {item["id"]: item for item in cls.library["scenarios"]}
        cls.mappings = cls.library["v2_mappings"]
        cls.parsed = {
            scenario_id: ScamSignalsV2.from_dict(mapping["signals"])
            for scenario_id, mapping in cls.mappings.items()
        }

    def test_all_57_scenario_ids_have_exactly_one_mapping(self) -> None:
        self.assertEqual(len(self.scenarios), 57)
        self.assertEqual(len(self.mappings), 57)
        self.assertEqual(set(self.mappings), set(self.scenarios))

    def test_every_mapping_parses_and_round_trips(self) -> None:
        for scenario_id, signals in self.parsed.items():
            with self.subTest(scenario=scenario_id):
                self.assertEqual(
                    ScamSignalsV2.from_dict(signals.to_dict()),
                    signals,
                )

    def test_all_external_assurance_is_unverified(self) -> None:
        for scenario_id, mapping in self.mappings.items():
            with self.subTest(scenario=scenario_id):
                context = IdentityAssuranceContext.from_dict(
                    {"identity_assurance": mapping["identity_assurance"]}
                )
                self.assertEqual(
                    context.identity_assurance, IdentityAssurance.UNVERIFIED
                )

    def test_all_m0_model_gap_cases_are_representable(self) -> None:
        model_gaps = {
            scenario_id
            for scenario_id, scenario in self.scenarios.items()
            if scenario["model_gap"]["present"]
        }
        self.assertEqual(len(model_gaps), 23)
        classified_model_gaps = {
            scenario_id
            for scenario_id in model_gaps
            if self.scenarios[scenario_id]["classification"] != "ambiguous"
        }
        self.assertEqual(len(classified_model_gaps), 22)
        self.assertTrue(model_gaps.issubset(self.parsed))
        for scenario_id in model_gaps:
            self.assertTrue(self.parsed[scenario_id].interaction_acts)

    def test_mixed_intent_cases_preserve_separate_acts(self) -> None:
        mixed = {
            scenario_id
            for scenario_id, scenario in self.scenarios.items()
            if scenario["semantic_direction"] == "mixed_intent"
        }
        self.assertEqual(len(mixed), 3)
        for scenario_id in mixed:
            directions = {
                act.semantic_direction for act in self.parsed[scenario_id].interaction_acts
            }
            self.assertIn(SemanticDirection.NEGATION, directions)
            self.assertIn(SemanticDirection.DIRECT_REQUEST, directions)

    def test_ambiguous_security_digits_remains_explicitly_ambiguous(self) -> None:
        mapping = self.mappings["ambiguous_security_digits"]
        signals = self.parsed["ambiguous_security_digits"]
        self.assertTrue(mapping["ambiguity"]["present"])
        self.assertTrue(mapping["ambiguity"]["reason"])
        self.assertEqual(len(signals.interaction_acts), 1)
        act = signals.interaction_acts[0]
        self.assertEqual(act.asset.subtype, AssetSubtype.UNSPECIFIED_SECURITY_CODE)
        self.assertEqual(act.actor, Actor.UNKNOWN)
        self.assertEqual(act.destination, Destination.UNKNOWN)
        self.assertEqual(act.semantic_direction, SemanticDirection.QUESTION)

    def test_v2_mapping_stores_no_transcripts_or_raw_sensitive_values(self) -> None:
        forbidden_keys = {
            "input",
            "transcript",
            "raw_text",
            "raw_value",
            "value",
            "otp_value",
            "password_value",
            "secret",
        }

        def visit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.mappings)

    def test_every_vocabulary_value_has_corpus_evidence_or_justification(self) -> None:
        observed = self._observed_vocabulary()
        enum_types = (
            ClaimedEntityType,
            KnowledgeCategory,
            ContextType,
            ActionTypeV2,
            AssetCategory,
            AssetSubtype,
            SemanticDirection,
            Actor,
            Destination,
            ManipulationType,
            IdentityAssurance,
        )
        self.assertEqual(
            set(VOCABULARY_JUSTIFICATIONS),
            {"IdentityAssurance"},
        )
        for enum_type in enum_types:
            justified = set(VOCABULARY_JUSTIFICATIONS.get(enum_type.__name__, {}))
            with self.subTest(vocabulary=enum_type.__name__):
                self.assertEqual(
                    {item.value for item in enum_type},
                    observed[enum_type.__name__] | justified,
                )
                self.assertTrue(observed[enum_type.__name__].isdisjoint(justified))

    def _observed_vocabulary(self) -> dict:
        observed = {
            "ClaimedEntityType": set(),
            "KnowledgeCategory": set(),
            "ContextType": set(),
            "ActionTypeV2": set(),
            "AssetCategory": set(),
            "AssetSubtype": set(),
            "SemanticDirection": set(),
            "Actor": set(),
            "Destination": set(),
            "ManipulationType": set(),
            "IdentityAssurance": set(),
        }
        for scenario_id, signals in self.parsed.items():
            mapping = self.mappings[scenario_id]
            observed["IdentityAssurance"].add(mapping["identity_assurance"])
            observed["ClaimedEntityType"].update(
                item.value for item in signals.identity_pretext.claims
            )
            observed["KnowledgeCategory"].update(
                item.value for item in signals.identity_pretext.knowledge_categories
            )
            observed["ContextType"].update(item.value for item in signals.contexts)
            observed["ManipulationType"].update(
                item.value for item in signals.manipulation
            )
            for act in signals.interaction_acts:
                observed["ActionTypeV2"].add(act.action.value)
                observed["SemanticDirection"].add(act.semantic_direction.value)
                observed["Actor"].add(act.actor.value)
                observed["Destination"].add(act.destination.value)
                if act.asset:
                    observed["AssetCategory"].add(act.asset.category.value)
                    observed["AssetSubtype"].add(act.asset.subtype.value)
        return observed


if __name__ == "__main__":
    unittest.main()
