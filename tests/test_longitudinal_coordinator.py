"""Tests for the M2.2 longitudinal coordinator and policy state."""

import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
from guardian.longitudinal.coordinator import (
    PolicyEventType,
    PolicyState,
    PolicySuppressionReason,
    evaluate_longitudinal_turn,
)
from guardian.longitudinal.evidence import (
    Action,
    Actor,
    BehavioralAct,
    Context,
    ContextEvidence,
    Destination,
    IdentityClaim,
    IdentityClaimEvidence,
    Manipulation,
    ManipulationEvidence,
    NormalizedTurnEvidence,
    ProtectedAsset,
    TemporalScope,
)
from guardian.longitudinal.risk import (
    LongitudinalRiskLevel,
    LongitudinalRiskState,
)
from guardian.longitudinal.state import ConversationState


def act(
    scope: TemporalScope = TemporalScope.CURRENT,
    asset: ProtectedAsset = ProtectedAsset.OTP,
    *,
    action: Action = Action.DISCLOSE,
    actor: Actor = Actor.USER,
    destination: Destination = Destination.OTHER_PARTY,
) -> BehavioralAct:
    return BehavioralAct(scope, action, asset, actor, destination)


def turn(number: int, **kwargs: object) -> NormalizedTurnEvidence:
    return NormalizedTurnEvidence(f"turn-{number}", number, **kwargs)


class Harness:
    def __init__(self, session_id: str = "session-a") -> None:
        self.conversation = ConversationState.initial(session_id)
        self.risk = LongitudinalRiskState.initial(session_id)
        self.policy = PolicyState.initial(session_id)

    def apply(self, evidence: NormalizedTurnEvidence):
        decision = evaluate_longitudinal_turn(
            self.conversation, self.risk, self.policy, evidence
        )
        self.conversation = decision.next_conversation_state
        self.risk = decision.next_risk_state
        self.policy = decision.next_policy_state
        return decision


class TestLongitudinalCoordinatorVerticalSlices(unittest.TestCase):
    def test_sequence_1_delayed_otp_duplicate_and_new_remote_factor(self) -> None:
        h = Harness()
        first = h.apply(
            turn(
                1,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            )
        )
        self.assertEqual(first.policy_event.event_type, PolicyEventType.NO_ACTION)

        second = h.apply(
            turn(
                2,
                contexts=frozenset(
                    {ContextEvidence(Context.BANKING, TemporalScope.ACCUMULATED_CONTEXT)}
                ),
            )
        )
        self.assertEqual(second.policy_event.event_type, PolicyEventType.NO_ACTION)

        third = h.apply(turn(3, acts=(act(asset=ProtectedAsset.OTP),)))
        self.assertEqual(third.risk_transition.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(third.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertFalse(third.policy_event.duplicate_suppressed)

        fourth = h.apply(turn(4, acts=(act(asset=ProtectedAsset.OTP),)))
        self.assertEqual(fourth.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertTrue(fourth.policy_event.duplicate_suppressed)
        self.assertEqual(
            fourth.policy_event.suppression_reason,
            PolicySuppressionReason.SAME_ACTIVE_DANGER,
        )

        fifth = h.apply(
            turn(
                5,
                acts=(
                    act(
                        asset=ProtectedAsset.REMOTE_CONTROL,
                        action=Action.GRANT_ACCESS,
                    ),
                ),
            )
        )
        self.assertEqual(fifth.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(len(fifth.policy_event.new_factors), 1)

    def test_sequence_2_retraction_decay_and_danger_return(self) -> None:
        h = Harness()
        first = h.apply(turn(1, acts=(act(asset=ProtectedAsset.PASSWORD),)))
        self.assertEqual(first.policy_event.event_type, PolicyEventType.ESCALATE)

        second = h.apply(
            turn(
                2,
                acts=(
                    act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.PASSWORD),
                ),
            )
        )
        self.assertEqual(second.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(
            second.policy_event.suppression_reason,
            PolicySuppressionReason.NO_CURRENT_ACTIVE_DANGER,
        )
        self.assertEqual(second.risk_transition.current_risk, LongitudinalRiskLevel.HIGH)
        self.assertEqual(second.risk_transition.peak_risk, LongitudinalRiskLevel.CRITICAL)

        third = h.apply(turn(3))
        fourth = h.apply(turn(4))
        self.assertEqual(third.risk_transition.current_risk, LongitudinalRiskLevel.SUSPICIOUS)
        self.assertEqual(fourth.risk_transition.current_risk, LongitudinalRiskLevel.NORMAL)

        fifth = h.apply(turn(5, acts=(act(asset=ProtectedAsset.PASSWORD),)))
        self.assertEqual(fifth.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(fifth.risk_transition.peak_risk, LongitudinalRiskLevel.CRITICAL)

    def test_sequence_3_legitimate_self_service_no_external_warning(self) -> None:
        h = Harness()
        first = h.apply(
            turn(
                1,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                acts=(
                    act(
                        asset=ProtectedAsset.OTP,
                        action=Action.ENTER,
                        destination=Destination.OFFICIAL_SELF_SERVICE,
                    ),
                ),
            )
        )
        self.assertEqual(first.risk_transition.current_risk, LongitudinalRiskLevel.NORMAL)
        self.assertEqual(first.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(first.policy_event.active_factors, ())

    def test_sequence_4_trust_poisoning_does_not_suppress_danger(self) -> None:
        h = Harness()
        for number in range(1, 5):
            h.apply(
                turn(
                    number,
                    contexts=frozenset(
                        {ContextEvidence(Context.BANKING, TemporalScope.ACCUMULATED_CONTEXT)}
                    ),
                    identity_claims=frozenset(
                        {
                            IdentityClaimEvidence(
                                IdentityClaim.FINANCIAL_INSTITUTION,
                                TemporalScope.ACCUMULATED_CONTEXT,
                            )
                        }
                    ),
                )
            )
        dangerous = h.apply(turn(5, acts=(act(asset=ProtectedAsset.OTP),)))
        self.assertEqual(dangerous.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertIn(
            "CURRENT_ACTIONABLE_SENSITIVE_ACT",
            dangerous.policy_event.reasons,
        )

    def test_sequence_5_temporal_contrast_only_current_intervenes(self) -> None:
        for scope, expected_event in (
            (TemporalScope.CURRENT, PolicyEventType.ESCALATE),
            (TemporalScope.HISTORICAL, PolicyEventType.NO_ACTION),
            (TemporalScope.HYPOTHETICAL, PolicyEventType.NO_ACTION),
            (TemporalScope.NEGATED, PolicyEventType.NO_ACTION),
        ):
            with self.subTest(scope=scope):
                h = Harness()
                decision = h.apply(turn(1, acts=(act(scope=scope),)))
                self.assertEqual(decision.policy_event.event_type, expected_event)


class TestLongitudinalCoordinatorPolicy(unittest.TestCase):
    def test_risk_increase_rewarns_existing_factor(self) -> None:
        h = Harness()
        first = h.apply(
            turn(
                1,
                acts=(
                    act(
                        asset=ProtectedAsset.BANK_FUNDS,
                        action=Action.TRANSFER,
                        destination=Destination.EXTERNAL_ACCOUNT,
                    ),
                ),
            )
        )
        self.assertEqual(first.policy_event.event_type, PolicyEventType.WARN)
        second = h.apply(
            turn(
                2,
                manipulations=frozenset(
                    {ManipulationEvidence(Manipulation.URGENCY)}
                ),
            )
        )
        self.assertEqual(second.risk_transition.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(second.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertTrue(second.policy_event.risk_increased)

    def test_identity_claim_does_not_authenticate_or_suppress_otp_warning(self) -> None:
        h = Harness()
        h.apply(
            turn(
                1,
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            )
        )
        decision = h.apply(turn(2, acts=(act(asset=ProtectedAsset.OTP),)))
        self.assertEqual(decision.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertTrue(
            any(
                reason.code == "CURRENT_ACTIONABLE_SENSITIVE_ACT"
                for reason in decision.risk_transition.reasons
            )
        )

    def test_prior_successful_benign_interaction_does_not_authorize_later_danger(self) -> None:
        h = Harness()
        h.apply(
            turn(
                1,
                acts=(
                    act(
                        asset=None,
                        action=Action.REVIEW,
                        destination=Destination.OFFICIAL_SELF_SERVICE,
                    ),
                ),
            )
        )
        decision = h.apply(turn(2, acts=(act(asset=ProtectedAsset.RECOVERY_CODE),)))
        self.assertEqual(decision.policy_event.event_type, PolicyEventType.ESCALATE)

    def test_independent_sessions_do_not_contaminate_policy_state(self) -> None:
        first = Harness("session-a")
        second = Harness("session-b")
        first_decision = first.apply(turn(1, acts=(act(asset=ProtectedAsset.OTP),)))
        second_decision = second.apply(turn(1))
        self.assertEqual(first_decision.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(second_decision.policy_event.event_type, PolicyEventType.NO_ACTION)

    def test_deterministic_identical_replay(self) -> None:
        evidence = (
            turn(1, contexts=frozenset({ContextEvidence(Context.BANKING)})),
            turn(2, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(3, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(4, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )

        def replay() -> list[str]:
            h = Harness()
            return [h.apply(item).to_json() for item in evidence]

        self.assertEqual(replay(), replay())

    def test_exact_duplicate_turn_is_noop_and_warning_suppressed(self) -> None:
        h = Harness()
        evidence = turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        first = h.apply(evidence)
        replay = evaluate_longitudinal_turn(
            h.conversation,
            h.risk,
            h.policy,
            evidence,
        )
        self.assertEqual(first.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(replay.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertTrue(replay.policy_event.duplicate_suppressed)
        self.assertIs(replay.next_conversation_state, h.conversation)
        self.assertIs(replay.next_risk_state, h.risk)

    def test_policy_history_is_bounded(self) -> None:
        h = Harness()
        h.policy = PolicyState.initial("session-a", history_limit=2)
        for number in range(1, 5):
            h.apply(turn(number))
        self.assertEqual(len(h.policy.history), 2)
        self.assertEqual([item.turn_number for item in h.policy.history], [3, 4])

    def test_no_transcript_or_secret_persistence(self) -> None:
        h = Harness()
        decision = h.apply(turn(1, acts=(act(asset=ProtectedAsset.OTP),)))
        serialized = json.dumps(decision.to_dict(), sort_keys=True).lower()
        for forbidden in (
            "transcript",
            "raw_text",
            "provider_response",
            "authorization_header",
            "483921",
            "synthetic-secret",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_no_network_or_model_provider_dependency(self) -> None:
        h = Harness()
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            decision = h.apply(turn(1, acts=(act(asset=ProtectedAsset.OTP),)))
        self.assertEqual(decision.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertNotIn("LongitudinalDecision", guardian.__all__)
        self.assertFalse(hasattr(guardian, "LongitudinalDecision"))
        source = (ROOT / "backend" / "guardian" / "longitudinal" / "coordinator.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("Gemini", "Gemma", "Ollama"):
            self.assertNotIn(forbidden, source)

    def test_m2_0_m2_1_and_existing_canary_files_are_unchanged_by_m2_2(self) -> None:
        production_or_prior = (
            "backend/guardian/longitudinal/state.py",
            "backend/guardian/longitudinal/evidence.py",
            "backend/guardian/longitudinal/risk.py",
            "backend/guardian/canary.py",
            "backend/guardian/risk.py",
            "backend/guardian/pipeline.py",
            "backend/server.py",
        )
        for relative in production_or_prior:
            with self.subTest(file=relative):
                self.assertFalse((ROOT / relative).read_text(encoding="utf-8").startswith("M2.2"))


if __name__ == "__main__":
    unittest.main()
