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
from guardian.experimental.extractor_v2 import GeminiV2Observation
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
        return observation(self.items.pop(0))


class TestExperimentalV2VerticalSlice(unittest.TestCase):
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
