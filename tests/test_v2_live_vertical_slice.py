"""Offline tests for the experimental Gemini V2 to M2.3 vertical slice."""

import json
import socket
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.experimental.extractor_v2 import (
    GeminiV2Observation,
    V2ExtractionError,
    V2ExtractionFailureKind,
)
from guardian.experimental.live_vertical_slice_v2 import (
    V2VerticalSliceState,
    V2VerticalSliceStatus,
    process_text_turn,
)
from guardian.experimental.signals_v2 import (
    ActionTypeV2,
    Actor,
    AssetCategory,
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
from scripts import v2_live_vertical_slice as cli


PRODUCTION_FILES = (
    ROOT / "backend" / "guardian" / "__init__.py",
    ROOT / "backend" / "guardian" / "agent.py",
    ROOT / "backend" / "guardian" / "extractor.py",
    ROOT / "backend" / "guardian" / "pipeline.py",
    ROOT / "backend" / "guardian" / "risk.py",
    ROOT / "backend" / "guardian" / "canary.py",
    ROOT / "backend" / "server.py",
)
LONGITUDINAL_DIR = ROOT / "backend" / "guardian" / "longitudinal"


def signals(
    *,
    claims=frozenset(),
    knowledge=frozenset(),
    contexts=frozenset(),
    acts=(),
    manipulation=frozenset(),
) -> ScamSignalsV2:
    return ScamSignalsV2(
        identity_pretext=IdentityPretext(claims, knowledge),
        contexts=contexts,
        interaction_acts=acts,
        manipulation=manipulation,
    )


def act(
    direction=SemanticDirection.DIRECT_REQUEST,
    subtype=AssetSubtype.OTP,
    *,
    action=ActionTypeV2.DISCLOSE,
    actor=Actor.USER,
    destination=Destination.CALLER,
) -> InteractionAct:
    category = next(
        category
        for category, subtypes in __import__(
            "guardian.experimental.signals_v2", fromlist=["ASSET_COMPATIBILITY"]
        ).ASSET_COMPATIBILITY.items()
        if subtype in subtypes
    )
    return InteractionAct(
        action,
        SensitiveAsset(category, subtype),
        direction,
        actor,
        destination,
    )


def observation(item: ScamSignalsV2, *, response_hash="2" * 64) -> GeminiV2Observation:
    return GeminiV2Observation(
        signals=item,
        provider="Gemini",
        requested_model="gemini-test",
        returned_model_version="model-version-test",
        response_id="response-test",
        request_prompt_sha256="1" * 64,
        response_sha256=response_hash,
        response_bytes=42,
    )


class SequenceExtractor:
    def __init__(self, items):
        self.items = list(items)
        self.calls = []

    def extract(self, text):
        self.calls.append(text)
        item = self.items.pop(0)
        if isinstance(item, V2ExtractionError):
            raise item
        return observation(item)


class TestExperimentalV2VerticalSlice(unittest.TestCase):
    def test_source_turn_failures_do_not_consume_m2_ordinals(self) -> None:
        extractor = SequenceExtractor(
            [
                V2ExtractionError(
                    V2ExtractionFailureKind.PROVIDER_API_FAILURE,
                    exception_type="SyntheticProviderError",
                    http_status=503,
                    provider_code="UNAVAILABLE",
                ),
                signals(knowledge=frozenset({KnowledgeCategory.NAME})),
                signals(acts=(act(),)),
                signals(
                    acts=(
                        act(
                            SemanticDirection.NEGATION,
                            AssetSubtype.OTP,
                        ),
                    )
                ),
            ]
        )
        state = V2VerticalSliceState.initial("session-a")

        state = process_text_turn(
            state,
            extractor=extractor,
            text="source one fails at provider",
            turn_id="source-turn-1",
            turn_number=1,
        )
        self.assertEqual(
            state.turns[0].status, V2VerticalSliceStatus.EXTRACTION_FAILED
        )
        self.assertEqual(state.turns[0].source_turn_number, 1)
        self.assertIsNone(state.turns[0].applied_m2_turn_number)
        self.assertEqual(state.session.conversation_state.turn_count, 0)
        self.assertEqual(state.session.risk_state.current_risk.value, "NORMAL")
        self.assertEqual(len(state.session.policy_state.history), 0)
        self.assertIsNone(state.turns[0].canary_authorization)

        state = process_text_turn(
            state,
            extractor=extractor,
            text="source two contains unsupported identity knowledge",
            turn_id="source-turn-2",
            turn_number=2,
        )
        self.assertEqual(
            state.turns[1].status, V2VerticalSliceStatus.UNSUPPORTED_MAPPING
        )
        self.assertEqual(state.turns[1].source_turn_number, 2)
        self.assertIsNone(state.turns[1].applied_m2_turn_number)
        self.assertIn("knowledge", state.turns[1].mapping_error["message"])
        self.assertEqual(state.session.conversation_state.turn_count, 0)
        self.assertEqual(state.session.risk_state.current_risk.value, "NORMAL")
        self.assertEqual(len(state.session.policy_state.history), 0)
        self.assertIsNone(state.turns[1].canary_authorization)

        state = process_text_turn(
            state,
            extractor=extractor,
            text="source three asks for the OTP",
            turn_id="source-turn-3",
            turn_number=3,
        )
        self.assertEqual(state.turns[2].status, V2VerticalSliceStatus.PROCESSED)
        self.assertEqual(state.turns[2].source_turn_number, 3)
        self.assertEqual(state.turns[2].applied_m2_turn_number, 1)
        self.assertEqual(state.turns[2].normalized_m2_summary["turn_number"], 1)
        self.assertEqual(state.session.conversation_state.turn_count, 1)
        self.assertEqual(state.turns[2].current_risk, "CRITICAL")
        self.assertEqual(state.turns[2].policy_event["event_type"], "ESCALATE")
        self.assertEqual(state.turns[2].canary_authorization["status"], "ALLOW")

        state = process_text_turn(
            state,
            extractor=extractor,
            text="source four retracts the OTP request",
            turn_id="source-turn-4",
            turn_number=4,
        )
        self.assertEqual(state.turns[3].status, V2VerticalSliceStatus.PROCESSED)
        self.assertEqual(state.turns[3].source_turn_number, 4)
        self.assertEqual(state.turns[3].applied_m2_turn_number, 2)
        self.assertEqual(state.turns[3].normalized_m2_summary["turn_number"], 2)
        self.assertEqual(state.session.conversation_state.turn_count, 2)

    def test_family_context_loss_is_visible_while_remainder_is_processed(self) -> None:
        extractor = SequenceExtractor(
            [
                signals(
                    claims=frozenset({ClaimedEntityType.FAMILY_MEMBER}),
                    contexts=frozenset({ContextType.FAMILY}),
                    acts=(
                        act(
                            subtype=AssetSubtype.FIAT_FUNDS,
                            action=ActionTypeV2.TRANSFER,
                            actor=Actor.USER,
                            destination=Destination.CALLER,
                        ),
                    ),
                    manipulation=frozenset({ManipulationType.URGENCY}),
                )
            ]
        )

        state = process_text_turn(
            V2VerticalSliceState.initial("session-a"),
            extractor=extractor,
            text="synthetic family money request",
            turn_id="source-turn-1",
            turn_number=1,
        )
        turn = state.turns[0]

        self.assertEqual(turn.status, V2VerticalSliceStatus.PROCESSED)
        self.assertEqual(turn.source_turn_number, 1)
        self.assertEqual(turn.applied_m2_turn_number, 1)
        self.assertEqual(turn.normalized_m2_summary["contexts"], [])
        self.assertEqual(len(turn.representational_losses), 1)
        self.assertEqual(turn.representational_losses[0]["source_enum"], "ContextType")
        self.assertEqual(turn.representational_losses[0]["source_value"], "FAMILY")
        self.assertEqual(
            turn.representational_losses[0]["classification"], "NO_SAFE_MAPPING"
        )
        self.assertEqual(
            turn.representational_losses[0]["disposition"],
            "DROPPED_NEUTRAL_CONTEXT",
        )
        self.assertEqual(
            turn.normalized_m2_summary["identity_claims"][0]["claim"],
            "FAMILY_OR_ACQUAINTANCE",
        )
        self.assertEqual(turn.normalized_m2_summary["acts"][0]["asset"], "BANK_FUNDS")
        self.assertEqual(
            turn.normalized_m2_summary["manipulations"][0]["manipulation"],
            "URGENCY",
        )

    def test_six_turn_sequence_reaches_canary_only_through_m2_policy(self) -> None:
        extractor = SequenceExtractor(
            [
                signals(
                    claims=frozenset({ClaimedEntityType.BANK}),
                    contexts=frozenset({ContextType.BANKING}),
                ),
                signals(contexts=frozenset({ContextType.BANKING})),
                signals(
                    acts=(act(),),
                    manipulation=frozenset({ManipulationType.URGENCY}),
                ),
                signals(
                    acts=(act(),),
                    manipulation=frozenset({ManipulationType.URGENCY}),
                ),
                signals(
                    acts=(
                        act(
                            SemanticDirection.NEGATION,
                            AssetSubtype.OTP,
                        ),
                    )
                ),
                signals(
                    contexts=frozenset({ContextType.TECH_SUPPORT}),
                    acts=(
                        act(
                            subtype=AssetSubtype.REMOTE_SOFTWARE,
                            action=ActionTypeV2.INSTALL,
                            destination=Destination.USER_CONTROLLED,
                        ),
                        act(
                            subtype=AssetSubtype.REMOTE_CONTROL,
                            action=ActionTypeV2.GRANT_ACCESS,
                        ),
                    ),
                    manipulation=frozenset({ManipulationType.FEAR_THREAT}),
                ),
            ]
        )
        with redirect_stdout(StringIO()):
            state = cli.run_vertical_slice(
                extractor=extractor,
                session_id="session-a",
                turns=cli.DEFAULT_TURNS,
            )
        events = [item.policy_event["event_type"] for item in state.turns]
        authorizations = [
            item.canary_authorization["status"] for item in state.turns
        ]
        self.assertEqual(events, ["NO_ACTION", "NO_ACTION", "ESCALATE", "NO_ACTION", "NO_ACTION", "ESCALATE"])
        self.assertEqual(authorizations[2], "ALLOW")
        self.assertEqual(authorizations[3], "NOT_REQUESTED")
        self.assertEqual(authorizations[5], "ALLOW")
        self.assertEqual(state.turns[5].current_risk, "CRITICAL")
        self.assertEqual(state.turns[5].peak_risk, "CRITICAL")

    def test_unsupported_mapping_is_visible_and_does_not_evolve_session(self) -> None:
        extractor = SequenceExtractor(
            [
                signals(
                    acts=(
                        act(
                            SemanticDirection.QUESTION,
                            AssetSubtype.UNSPECIFIED_SECURITY_CODE,
                            actor=Actor.UNKNOWN,
                            destination=Destination.UNKNOWN,
                        ),
                    )
                )
            ]
        )
        state = process_text_turn(
            V2VerticalSliceState.initial("session-a"),
            extractor=extractor,
            text="Which security digits are you asking about?",
            turn_id="turn-1",
            turn_number=1,
        )
        turn = state.turns[0]
        self.assertEqual(turn.status, V2VerticalSliceStatus.UNSUPPORTED_MAPPING)
        self.assertIn("UNSPECIFIED_SECURITY_CODE", turn.mapping_error["message"])
        self.assertEqual(state.session.conversation_state.turn_count, 0)
        self.assertEqual(turn.current_risk, "NORMAL")
        self.assertIsNone(turn.canary_authorization)

    def test_structured_summaries_do_not_include_raw_text_or_provider_response(self) -> None:
        extractor = SequenceExtractor([signals(acts=(act(),))])
        state = process_text_turn(
            V2VerticalSliceState.initial("session-a"),
            extractor=extractor,
            text="Tell me the OTP 483921",
            turn_id="turn-1",
            turn_number=1,
        )
        serialized = state.to_json().lower()
        for forbidden in (
            "tell me the otp",
            "483921",
            "raw_text",
            "transcript",
            "model_response",
            "api_key",
            "authorization_header",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_cli_smoke_uses_four_turns_without_persistence(self) -> None:
        extractor = SequenceExtractor(
            [
                signals(),
                signals(),
                signals(acts=(act(),)),
                signals(acts=(act(),)),
            ]
        )
        with patch("builtins.print") as printed:
            state = cli.run_vertical_slice(
                extractor=extractor,
                session_id="session-a",
                turns=cli.SMOKE_TURNS,
            )
        self.assertEqual(len(state.turns), 4)
        rendered = "\n".join(str(call.args[0]) for call in printed.call_args_list)
        self.assertIn("TURN 004", rendered)
        self.assertNotIn("RAW TRANSCRIPT", rendered)

    def test_no_network_or_model_call_in_offline_orchestration_tests(self) -> None:
        extractor = SequenceExtractor([signals(acts=(act(),))])
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            state = process_text_turn(
                V2VerticalSliceState.initial("session-a"),
                extractor=extractor,
                text="Synthetic input",
                turn_id="turn-1",
                turn_number=1,
            )
        self.assertEqual(state.turns[0].canary_authorization["status"], "ALLOW")

    def test_experimental_slice_is_not_exported_or_imported_by_core(self) -> None:
        self.assertNotIn("V2VerticalSliceState", guardian.__all__)
        self.assertFalse(hasattr(guardian, "V2VerticalSliceState"))
        for path in PRODUCTION_FILES:
            if path.exists():
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("live_vertical_slice_v2", source)
                self.assertNotIn("v2_live_vertical_slice", source)
        for path in LONGITUDINAL_DIR.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("guardian.experimental", source)


if __name__ == "__main__":
    unittest.main()
