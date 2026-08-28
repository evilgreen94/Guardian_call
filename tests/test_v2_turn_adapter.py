"""Tests for the M2.4 ScamSignalsV2 to NormalizedTurnEvidence adapter."""

import json
import socket
import sys
import unittest
import ast
from collections import Counter
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.signals_v2 import (
    ActionTypeV2,
    Actor,
    AssetSubtype,
    ClaimedEntityType,
    ContextType,
    Destination,
    IdentityPretext,
    InteractionAct,
    KnowledgeCategory,
    ManipulationType,
    ScamSignalsV2,
    SemanticDirection,
    SensitiveAsset,
)
from guardian.experimental.v2_turn_adapter import (
    ACTION_MAPPING,
    ACTOR_MAPPING,
    ASSET_MAPPING,
    CLAIM_MAPPING,
    CONTEXT_MAPPING,
    DESTINATION_MAPPING,
    DIRECTION_MAPPING,
    KNOWLEDGE_MAPPING,
    MANIPULATION_MAPPING,
    MappingClassification,
    UnsupportedV2MappingError,
    adapt_v2_turn,
    mapping_coverage_report,
)
from guardian.longitudinal.evidence import (
    Action,
    Actor as M2Actor,
    Context,
    Destination as M2Destination,
    IdentityClaim,
    Manipulation,
    ProtectedAsset,
    TemporalScope,
)
from guardian.longitudinal.session import (
    CanaryAuthorizationStatus,
    LongitudinalSessionState,
    process_normalized_turn,
)
from guardian.longitudinal.coordinator import PolicyEventType
from guardian.longitudinal.risk import LongitudinalRiskLevel


CORPUS_PATH = ROOT / "scenarios" / "m1_adversarial_scenarios.json"
LONGITUDINAL_DIR = ROOT / "backend" / "guardian" / "longitudinal"
PRODUCTION_FILES = (
    ROOT / "backend" / "guardian" / "agent.py",
    ROOT / "backend" / "guardian" / "extractor.py",
    ROOT / "backend" / "guardian" / "pipeline.py",
    ROOT / "backend" / "guardian" / "risk.py",
    ROOT / "backend" / "guardian" / "canary.py",
    ROOT / "backend" / "server.py",
)


def asset(subtype: AssetSubtype) -> SensitiveAsset:
    for category, subtypes in __import__(
        "guardian.experimental.signals_v2", fromlist=["ASSET_COMPATIBILITY"]
    ).ASSET_COMPATIBILITY.items():
        if subtype in subtypes:
            return SensitiveAsset(category, subtype)
    raise AssertionError(f"unmapped subtype {subtype}")


def signals(
    *,
    claims: frozenset[ClaimedEntityType] = frozenset(),
    knowledge: frozenset[KnowledgeCategory] = frozenset(),
    contexts: frozenset[ContextType] = frozenset(),
    acts: tuple[InteractionAct, ...] = (),
    manipulation: frozenset[ManipulationType] = frozenset(),
) -> ScamSignalsV2:
    return ScamSignalsV2(
        identity_pretext=IdentityPretext(claims, knowledge),
        contexts=contexts,
        interaction_acts=acts,
        manipulation=manipulation,
    )


def interaction(
    direction: SemanticDirection = SemanticDirection.DIRECT_REQUEST,
    subtype: AssetSubtype = AssetSubtype.OTP,
    *,
    action: ActionTypeV2 = ActionTypeV2.DISCLOSE,
    actor: Actor = Actor.USER,
    destination: Destination = Destination.CALLER,
) -> InteractionAct:
    return InteractionAct(action, asset(subtype), direction, actor, destination)


def adapt(item: ScamSignalsV2):
    return adapt_v2_turn(
        session_id="session-a",
        turn_id="turn-1",
        ordinal=1,
        signals=item,
    )


def corpus_signals(scenario_id: str) -> ScamSignalsV2:
    library = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return ScamSignalsV2.from_dict(library["v2_mappings"][scenario_id]["signals"])


class TestV2MappingTables(unittest.TestCase):
    def test_mapping_tables_cover_every_v2_enum_value(self) -> None:
        self.assertEqual(set(CLAIM_MAPPING), set(ClaimedEntityType))
        self.assertEqual(set(KNOWLEDGE_MAPPING), set(KnowledgeCategory))
        self.assertEqual(set(CONTEXT_MAPPING), set(ContextType))
        self.assertEqual(set(ACTION_MAPPING), set(ActionTypeV2))
        self.assertEqual(set(ASSET_MAPPING), set(AssetSubtype))
        self.assertEqual(set(DIRECTION_MAPPING), set(SemanticDirection))
        self.assertEqual(set(ACTOR_MAPPING), set(Actor))
        self.assertEqual(set(DESTINATION_MAPPING), set(Destination))
        self.assertEqual(set(MANIPULATION_MAPPING), set(ManipulationType))

    def test_mapping_report_is_deterministic_and_classifies_every_value(self) -> None:
        first = [item.to_dict() for item in mapping_coverage_report()]
        second = [item.to_dict() for item in mapping_coverage_report()]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 97)
        classifications = {item["classification"] for item in first}
        self.assertEqual(
            classifications,
            {
                MappingClassification.EXACT_MAPPING.value,
                MappingClassification.LOSSLESS_NORMALIZATION.value,
                MappingClassification.PARTIAL_MAPPING.value,
                MappingClassification.NO_SAFE_MAPPING.value,
            },
        )
        self.assertEqual(
            Counter(item["classification"] for item in first),
            {
                MappingClassification.EXACT_MAPPING.value: 62,
                MappingClassification.LOSSLESS_NORMALIZATION.value: 10,
                MappingClassification.PARTIAL_MAPPING.value: 14,
                MappingClassification.NO_SAFE_MAPPING.value: 11,
            },
        )

    def test_temporal_direction_mapping_is_conservative(self) -> None:
        expected = {
            SemanticDirection.DIRECT_REQUEST: TemporalScope.CURRENT,
            SemanticDirection.INDIRECT_REQUEST: TemporalScope.CURRENT,
            SemanticDirection.PARTIAL_REQUEST: TemporalScope.CURRENT,
            SemanticDirection.THIRD_PARTY: TemporalScope.HISTORICAL,
            SemanticDirection.NEGATION: TemporalScope.NEGATED,
            SemanticDirection.HISTORICAL: TemporalScope.HISTORICAL,
            SemanticDirection.HYPOTHETICAL: TemporalScope.HYPOTHETICAL,
            SemanticDirection.WARNING: TemporalScope.HYPOTHETICAL,
            SemanticDirection.QUESTION: TemporalScope.HYPOTHETICAL,
            SemanticDirection.DISCUSSION: TemporalScope.HYPOTHETICAL,
            SemanticDirection.SELF_SERVICE: TemporalScope.CURRENT,
        }
        for source, target in expected.items():
            with self.subTest(source=source):
                evidence = adapt(signals(acts=(interaction(source),)))
                self.assertEqual(evidence.acts[0].scope, target)

    def test_action_mapping_preserves_equivalent_values(self) -> None:
        for source in ActionTypeV2:
            with self.subTest(source=source):
                evidence = adapt(signals(acts=(interaction(action=source),)))
                self.assertEqual(evidence.acts[0].action, Action(source.value))

    def test_asset_mapping_preserves_supported_sensitive_assets(self) -> None:
        expected = {
            AssetSubtype.OTP: ProtectedAsset.OTP,
            AssetSubtype.PASSWORD: ProtectedAsset.PASSWORD,
            AssetSubtype.RECOVERY_CODE: ProtectedAsset.RECOVERY_CODE,
            AssetSubtype.CARD_SECURITY_CODE: ProtectedAsset.CARD_SECURITY_CODE,
            AssetSubtype.GIFT_CARD_REDEMPTION_CODE: ProtectedAsset.GIFT_CARD,
            AssetSubtype.SEED_PHRASE: ProtectedAsset.SEED_PHRASE,
            AssetSubtype.PRIVATE_KEY: ProtectedAsset.PRIVATE_KEY,
            AssetSubtype.CARD_NUMBER: ProtectedAsset.CARD_DATA,
            AssetSubtype.CARD_EXPIRY: ProtectedAsset.CARD_DATA,
            AssetSubtype.FIAT_FUNDS: ProtectedAsset.BANK_FUNDS,
            AssetSubtype.PAYMENT_APP_PAYMENT: ProtectedAsset.PAYMENT_APP_FUNDS,
            AssetSubtype.GIFT_CARD: ProtectedAsset.GIFT_CARD,
            AssetSubtype.CASH: ProtectedAsset.CASH,
            AssetSubtype.CRYPTO_ASSET: ProtectedAsset.CRYPTO_ASSET,
            AssetSubtype.LOGIN_APPROVAL: ProtectedAsset.LOGIN_APPROVAL,
            AssetSubtype.RECOVERY_EMAIL: ProtectedAsset.ACCOUNT_RECOVERY,
            AssetSubtype.RECOVERY_PHONE: ProtectedAsset.ACCOUNT_RECOVERY,
            AssetSubtype.TWO_FACTOR_SETTING: ProtectedAsset.SECURITY_SETTINGS,
            AssetSubtype.PASSWORD_RESET_LINK: ProtectedAsset.ACCOUNT_RECOVERY,
            AssetSubtype.REMOTE_SOFTWARE: ProtectedAsset.REMOTE_SOFTWARE,
            AssetSubtype.REMOTE_CONTROL: ProtectedAsset.REMOTE_CONTROL,
            AssetSubtype.SCREEN_CONTENT: ProtectedAsset.SCREEN_CONTENT,
        }
        for source, target in expected.items():
            with self.subTest(source=source):
                evidence = adapt(signals(acts=(interaction(subtype=source),)))
                self.assertEqual(evidence.acts[0].asset, target)

    def test_unsupported_asset_mapping_fails_safely(self) -> None:
        with self.assertRaisesRegex(UnsupportedV2MappingError, "UNSPECIFIED"):
            adapt(signals(acts=(interaction(subtype=AssetSubtype.UNSPECIFIED_SECURITY_CODE),)))

    def test_all_no_safe_mapping_values_fail_explicitly(self) -> None:
        records = [
            item
            for item in mapping_coverage_report()
            if item.classification == MappingClassification.NO_SAFE_MAPPING
        ]
        self.assertEqual(len(records), 11)
        for record in records:
            with self.subTest(source=record.source_enum, value=record.source_value):
                if record.source_enum == "KnowledgeCategory":
                    item = signals(
                        knowledge=frozenset(
                            {KnowledgeCategory(record.source_value)}
                        )
                    )
                elif record.source_enum == "AssetSubtype":
                    item = signals(
                        acts=(
                            interaction(
                                subtype=AssetSubtype(record.source_value)
                            ),
                        )
                    )
                elif record.source_enum == "ContextType":
                    item = signals(
                        contexts=frozenset({ContextType(record.source_value)})
                    )
                else:
                    self.fail(f"Unhandled NO_SAFE_MAPPING source {record.source_enum}")
                with self.assertRaises(UnsupportedV2MappingError):
                    adapt(item)

    def test_generic_family_context_fails_without_inventing_emergency(self) -> None:
        with self.assertRaisesRegex(UnsupportedV2MappingError, "FAMILY"):
            adapt(signals(contexts=frozenset({ContextType.FAMILY})))

    def test_actor_destination_identity_context_and_manipulation_mappings(self) -> None:
        evidence = adapt(
            signals(
                claims=frozenset(
                    {
                        ClaimedEntityType.BANK,
                        ClaimedEntityType.SOCIAL_PLATFORM,
                    }
                ),
                contexts=frozenset({ContextType.BANKING, ContextType.SOCIAL_MEDIA}),
                manipulation=frozenset(
                    {ManipulationType.FEAR_THREAT, ManipulationType.KEEP_ON_CALL}
                ),
                acts=(
                    interaction(
                        actor=Actor.THIRD_PARTY,
                        destination=Destination.EXTERNAL_ACCOUNT,
                    ),
                ),
            )
        )
        self.assertEqual(
            {item.claim for item in evidence.identity_claims},
            {IdentityClaim.FINANCIAL_INSTITUTION, IdentityClaim.ONLINE_SERVICE},
        )
        self.assertEqual(
            {item.context for item in evidence.contexts},
            {Context.BANKING, Context.SOCIAL_PLATFORM},
        )
        self.assertEqual(
            {item.manipulation for item in evidence.manipulations},
            {Manipulation.FEAR_OR_THREAT, Manipulation.KEEP_ENGAGED},
        )
        self.assertEqual(evidence.acts[0].actor, M2Actor.THIRD_PARTY)
        self.assertEqual(evidence.acts[0].destination, M2Destination.EXTERNAL_ACCOUNT)

    def test_identity_knowledge_categories_fail_without_authenticating(self) -> None:
        with self.assertRaisesRegex(UnsupportedV2MappingError, "knowledge"):
            adapt(
                signals(
                    claims=frozenset({ClaimedEntityType.BANK}),
                    knowledge=frozenset({KnowledgeCategory.NAME}),
                )
            )


class TestV2AdapterEndToEnd(unittest.TestCase):
    def test_otp_direct_request_to_caller_intervenes(self) -> None:
        evidence = adapt(corpus_signals("social_network_otp_takeover"))
        session = LongitudinalSessionState.initial("session-a")
        result = process_normalized_turn(session, evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_otp_indirect_request_to_caller_intervenes(self) -> None:
        evidence = adapt(signals(acts=(interaction(SemanticDirection.INDIRECT_REQUEST),)))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_otp_warning_is_not_active_caller_directed_danger(self) -> None:
        evidence = adapt(corpus_signals("social_network_legitimate_warning"))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.NOT_REQUESTED)

    def test_otp_historical_and_hypothetical_reports_do_not_intervene(self) -> None:
        for scenario_id in ("otp_historical_report_es", "otp_hypothetical_warning_es"):
            with self.subTest(scenario=scenario_id):
                evidence = adapt(corpus_signals(scenario_id))
                result = process_normalized_turn(
                    LongitudinalSessionState.initial("session-a"), evidence
                )
                self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)
                self.assertEqual(
                    result.canary_authorization.status,
                    CanaryAuthorizationStatus.NOT_REQUESTED,
                )

    def test_otp_third_party_report_preserves_evidence_without_intervention(self) -> None:
        evidence = adapt(corpus_signals("otp_third_party_report_es"))
        self.assertEqual(len(evidence.acts), 1)
        act = evidence.acts[0]
        self.assertEqual(act.scope, TemporalScope.HISTORICAL)
        self.assertEqual(act.actor, M2Actor.THIRD_PARTY)
        self.assertEqual(act.asset, ProtectedAsset.OTP)
        self.assertEqual(act.destination, M2Destination.OTHER_PARTY)
        self.assertFalse(evidence.identity_claims)

        result = process_normalized_turn(
            LongitudinalSessionState.initial("session-a"), evidence
        )
        self.assertEqual(result.risk_transition["current_risk"], "NORMAL")
        self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(result.policy_event.active_factors, ())
        self.assertEqual(
            result.canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )

    def test_third_party_report_does_not_retract_existing_current_factor(self) -> None:
        session = LongitudinalSessionState.initial("session-a")
        first = process_normalized_turn(
            session,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-1",
                ordinal=1,
                signals=signals(acts=(interaction(),)),
            ),
        )
        second = process_normalized_turn(
            first.next_state,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-2",
                ordinal=2,
                signals=corpus_signals("otp_third_party_report_es"),
            ),
        )
        self.assertEqual(second.risk_transition["current_risk"], "CRITICAL")
        self.assertEqual(second.conversation_transition.retractions, ())
        self.assertEqual(len(second.policy_event.active_factors), 1)

    def test_current_otp_request_after_third_party_report_still_intervenes(self) -> None:
        first = process_normalized_turn(
            LongitudinalSessionState.initial("session-a"),
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-1",
                ordinal=1,
                signals=corpus_signals("otp_third_party_report_es"),
            ),
        )
        second = process_normalized_turn(
            first.next_state,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-2",
                ordinal=2,
                signals=signals(acts=(interaction(),)),
            ),
        )
        self.assertEqual(second.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(
            second.canary_authorization.status,
            CanaryAuthorizationStatus.ALLOW,
        )

    def test_otp_negation_drives_matching_retraction_semantics(self) -> None:
        session = LongitudinalSessionState.initial("session-a")
        first = process_normalized_turn(
            session,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-1",
                ordinal=1,
                signals=signals(acts=(interaction(),)),
            ),
        )
        second = process_normalized_turn(
            first.next_state,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-2",
                ordinal=2,
                signals=corpus_signals("otp_self_entry_official_app_es"),
            ),
        )
        self.assertEqual(second.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(second.risk_transition["current_risk"], "HIGH")

    def test_official_self_service_otp_entry_does_not_intervene(self) -> None:
        evidence = adapt(corpus_signals("otp_self_entry_official_app_es"))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.NOT_REQUESTED)

    def test_transfer_to_external_account_warns(self) -> None:
        evidence = adapt(corpus_signals("safe_account_transfer"))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_remote_software_installation_request_intervenes(self) -> None:
        evidence = adapt(corpus_signals("remote_generic_support_es"))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_identity_only_v2_does_not_authenticate_or_create_critical_act(self) -> None:
        evidence = adapt(signals(claims=frozenset({ClaimedEntityType.BANK})))
        result = process_normalized_turn(LongitudinalSessionState.initial("session-a"), evidence)
        self.assertEqual(result.risk_transition["current_risk"], "NORMAL")
        self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)

    def test_trust_context_does_not_suppress_later_sensitive_request(self) -> None:
        session = LongitudinalSessionState.initial("session-a")
        first = process_normalized_turn(
            session,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-1",
                ordinal=1,
                signals=signals(
                    claims=frozenset({ClaimedEntityType.BANK}),
                    contexts=frozenset({ContextType.BANKING}),
                ),
            ),
        )
        second = process_normalized_turn(
            first.next_state,
            adapt_v2_turn(
                session_id="session-a",
                turn_id="turn-2",
                ordinal=2,
                signals=signals(acts=(interaction(),)),
            ),
        )
        self.assertEqual(second.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(second.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_multi_act_v2_turn_preserves_all_safe_acts(self) -> None:
        evidence = adapt(corpus_signals("remote_mixed_emergency_es"))
        self.assertEqual(len(evidence.acts), 3)
        self.assertEqual(
            [item.action for item in evidence.acts],
            [Action.GRANT_ACCESS, Action.INSTALL, Action.GRANT_ACCESS],
        )


class TestV2AdapterStrictnessPrivacyAndDependencies(unittest.TestCase):
    def test_mapping_is_deterministic_and_uses_supplied_ids(self) -> None:
        item = corpus_signals("safe_account_transfer")
        first = adapt_v2_turn(
            session_id="session-a", turn_id="external-turn", ordinal=7, signals=item
        )
        second = adapt_v2_turn(
            session_id="session-a", turn_id="external-turn", ordinal=7, signals=item
        )
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.turn_id, "external-turn")
        self.assertEqual(first.turn_number, 7)

    def test_adapter_result_contains_no_raw_text_or_provider_material(self) -> None:
        evidence = adapt(corpus_signals("safe_account_transfer"))
        serialized = evidence.to_json().lower()
        for forbidden in (
            "transcript",
            "raw_text",
            "model_response",
            "api_key",
            "auth_token",
            "authorization_header",
            "483921",
            "synthetic-secret",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_no_network_or_model_dependency(self) -> None:
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            evidence = adapt(corpus_signals("safe_account_transfer"))
        self.assertEqual(evidence.turn_id, "turn-1")
        source = (ROOT / "backend" / "guardian" / "experimental" / "v2_turn_adapter.py").read_text(
            encoding="utf-8"
        )
        parsed = ast.parse(source)
        imported_modules = {
            alias.name
            for node in ast.walk(parsed)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            node.module
            for node in ast.walk(parsed)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        for forbidden in ("requests", "urllib"):
            self.assertNotIn(forbidden, imported_modules)
        for forbidden in ("Gemini", "Gemma", "Ollama"):
            self.assertNotIn(forbidden, source)

    def test_longitudinal_core_does_not_import_experimental(self) -> None:
        offenders = []
        for path in LONGITUDINAL_DIR.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "guardian.experimental" in source:
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_production_m0_does_not_depend_on_m2_4_adapter(self) -> None:
        offenders = []
        for path in PRODUCTION_FILES:
            if path.exists() and "v2_turn_adapter" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
