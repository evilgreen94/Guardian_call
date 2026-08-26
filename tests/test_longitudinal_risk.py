"""Tests for deterministic M2.1 longitudinal risk transitions."""

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import guardian
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
    evaluate_risk_transition,
)
from guardian.longitudinal.state import (
    ConversationState,
    ReplayStatus,
    StateLimits,
    apply_turn,
)


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


def step(
    conversation: ConversationState,
    risk: LongitudinalRiskState,
    evidence: NormalizedTurnEvidence,
) -> tuple[ConversationState, LongitudinalRiskState, object]:
    state_transition = apply_turn(conversation, evidence)
    risk_transition = evaluate_risk_transition(risk, state_transition)
    return state_transition.next_state, risk_transition.next_state, risk_transition


class TestLongitudinalRiskTransitions(unittest.TestCase):
    def test_repeated_current_occurrence_remains_one_active_factor(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        conversation, risk, first = step(conversation, risk, turn(1, acts=(otp,)))
        self.assertEqual(first.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(risk.unresolved_factors, (otp.fingerprint,))

        conversation, risk, second = step(conversation, risk, turn(2, acts=(otp,)))
        self.assertEqual(second.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(risk.unresolved_factors, (otp.fingerprint,))

        aggregate = next(item for item in conversation.acts if item.act == otp)
        self.assertEqual(aggregate.occurrence.first_seen, 1)
        self.assertEqual(aggregate.occurrence.last_seen, 2)
        self.assertEqual(aggregate.occurrence.count, 2)
        self.assertEqual(aggregate.retraction_count, 0)

    def test_repeated_occurrence_persistence_is_bounded_by_m2_0_limits(self) -> None:
        conversation = ConversationState.initial(
            "session-a", limits=StateLimits(occurrence_count=2)
        )
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        conversation, risk, _ = step(conversation, risk, turn(1, acts=(otp,)))
        conversation, risk, _ = step(conversation, risk, turn(2, acts=(otp,)))
        conversation, risk, _ = step(conversation, risk, turn(3, acts=(otp,)))

        aggregate = next(item for item in conversation.acts if item.act == otp)
        self.assertEqual(aggregate.occurrence.count, 2)
        self.assertTrue(aggregate.occurrence.count_saturated)
        self.assertEqual(risk.unresolved_factors, (otp.fingerprint,))

    def test_all_benign_sequence_remains_normal(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        for evidence in (
            turn(1, contexts=frozenset({ContextEvidence(Context.BANKING)})),
            turn(
                2,
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            ),
            turn(
                3,
                acts=(
                    act(
                        asset=None,
                        action=Action.REVIEW,
                        destination=Destination.OFFICIAL_SELF_SERVICE,
                    ),
                ),
            ),
        ):
            conversation, risk, transition = step(conversation, risk, evidence)
            self.assertEqual(transition.current_risk, LongitudinalRiskLevel.NORMAL)
        self.assertEqual(risk.peak_risk, LongitudinalRiskLevel.NORMAL)

    def test_delayed_otp_disclosure_escalates(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation,
            risk,
            turn(1, contexts=frozenset({ContextEvidence(Context.BANKING)})),
        )
        conversation, risk, transition = step(
            conversation, risk, turn(2, acts=(act(asset=ProtectedAsset.OTP),))
        )
        self.assertEqual(transition.previous_risk, LongitudinalRiskLevel.NORMAL)
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertIn("CURRENT_ACTIONABLE_SENSITIVE_ACT", [r.code for r in transition.reasons])

    def test_delayed_remote_access_request_escalates(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation,
            risk,
            turn(
                1,
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.TECH_SUPPORT)}
                ),
            ),
        )
        conversation, risk, transition = step(
            conversation,
            risk,
            turn(
                2,
                acts=(
                    act(
                        asset=ProtectedAsset.REMOTE_CONTROL,
                        action=Action.GRANT_ACCESS,
                    ),
                ),
            ),
        )
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.CRITICAL)

    def test_trust_or_legitimacy_prefix_does_not_suppress_later_danger(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation,
            risk,
            turn(
                1,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            ),
        )
        conversation, risk, transition = step(
            conversation,
            risk,
            turn(2, acts=(act(asset=ProtectedAsset.PASSWORD),)),
        )
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.CRITICAL)

    def test_historical_and_hypothetical_danger_do_not_behave_as_current(self) -> None:
        for scope in (TemporalScope.HISTORICAL, TemporalScope.HYPOTHETICAL):
            with self.subTest(scope=scope):
                conversation = ConversationState.initial("session-a")
                risk = LongitudinalRiskState.initial("session-a")
                _, _, transition = step(
                    conversation, risk, turn(1, acts=(act(scope=scope),))
                )
                self.assertEqual(transition.current_risk, LongitudinalRiskLevel.NORMAL)

    def test_negated_retracted_act_reduces_only_matching_active_factor(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        conversation, risk, first = step(conversation, risk, turn(1, acts=(otp,)))
        self.assertEqual(first.current_risk, LongitudinalRiskLevel.CRITICAL)
        conversation, risk, second = step(
            conversation,
            risk,
            turn(2, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )
        self.assertEqual(second.current_risk, LongitudinalRiskLevel.HIGH)
        self.assertEqual(second.peak_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertIn("BOUNDED_RESIDUAL_RISK", [r.code for r in second.reasons])

    def test_one_precise_negation_resolves_repeated_equivalent_current_factor(
        self,
    ) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        conversation, risk, _ = step(conversation, risk, turn(1, acts=(otp,)))
        conversation, risk, _ = step(conversation, risk, turn(2, acts=(otp,)))
        conversation, risk, transition = step(
            conversation,
            risk,
            turn(3, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )

        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.HIGH)
        self.assertEqual(transition.peak_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(risk.unresolved_factors, ())

        aggregate = next(item for item in conversation.acts if item.act == otp)
        self.assertEqual(aggregate.occurrence.first_seen, 1)
        self.assertEqual(aggregate.occurrence.last_seen, 2)
        self.assertEqual(aggregate.occurrence.count, 2)
        self.assertEqual(aggregate.retraction_count, 1)
        self.assertEqual(aggregate.last_retracted_at, 3)
        self.assertIn(
            "RETRACTED_PERSISTENT_DANGER_HISTORY",
            [reason.code for reason in transition.reasons],
        )

        conversation, risk, decayed = step(conversation, risk, turn(4))
        self.assertNotIn(
            "RETRACTED_PERSISTENT_DANGER_HISTORY",
            [reason.code for reason in decayed.reasons],
        )

    def test_same_turn_current_and_matching_negated_factor_is_not_active(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        negated_otp = act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP)
        conversation, risk, transition = step(
            conversation, risk, turn(1, acts=(otp, negated_otp))
        )

        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.NORMAL)
        self.assertEqual(risk.unresolved_factors, ())

        aggregate = next(item for item in conversation.acts if item.act == otp)
        self.assertEqual(aggregate.occurrence.last_seen, 1)
        self.assertEqual(aggregate.retraction_count, 1)
        self.assertEqual(aggregate.last_retracted_at, 1)

    def test_unrelated_negation_does_not_clear_another_factor(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation, risk, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        conversation, risk, transition = step(
            conversation,
            risk,
            turn(
                2,
                acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.PASSWORD),),
            ),
        )
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.CRITICAL)

    def test_historical_hypothetical_occurrences_are_not_retraction_targets_for_risk(
        self,
    ) -> None:
        for scope in (TemporalScope.HISTORICAL, TemporalScope.HYPOTHETICAL):
            with self.subTest(scope=scope):
                conversation = ConversationState.initial("session-a")
                risk = LongitudinalRiskState.initial("session-a")
                conversation, risk, _ = step(
                    conversation, risk, turn(1, acts=(act(scope=scope),))
                )
                conversation, risk, transition = step(
                    conversation,
                    risk,
                    turn(2, acts=(act(scope=TemporalScope.NEGATED),)),
                )
                self.assertEqual(transition.current_risk, LongitudinalRiskLevel.NORMAL)
                aggregate = next(
                    item for item in conversation.acts if item.act.scope == scope
                )
                self.assertEqual(aggregate.retraction_count, 0)
                self.assertIsNone(aggregate.last_retracted_at)

    def test_benign_turns_decay_unresolved_risk(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation, risk, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        conversation, risk, decayed = step(
            conversation,
            risk,
            turn(2, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )
        self.assertEqual(decayed.current_risk, LongitudinalRiskLevel.HIGH)
        conversation, risk, normal = step(conversation, risk, turn(3))
        self.assertEqual(normal.current_risk, LongitudinalRiskLevel.SUSPICIOUS)
        conversation, risk, cleared = step(conversation, risk, turn(4))
        self.assertEqual(cleared.current_risk, LongitudinalRiskLevel.NORMAL)

    def test_new_dangerous_act_reescalates_immediately_after_decay(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        conversation, risk, _ = step(
            conversation, risk, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        conversation, risk, _ = step(
            conversation,
            risk,
            turn(2, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )
        conversation, risk, _ = step(conversation, risk, turn(3))
        conversation, risk, _ = step(conversation, risk, turn(4))
        self.assertEqual(risk.current_risk, LongitudinalRiskLevel.NORMAL)
        conversation, risk, transition = step(
            conversation, risk, turn(5, acts=(act(asset=ProtectedAsset.PASSWORD),))
        )
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.CRITICAL)

    def test_same_factor_reactivates_after_precise_retraction(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        otp = act(asset=ProtectedAsset.OTP)
        conversation, risk, _ = step(conversation, risk, turn(1, acts=(otp,)))
        conversation, risk, retracted = step(
            conversation,
            risk,
            turn(2, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
        )
        self.assertEqual(retracted.current_risk, LongitudinalRiskLevel.HIGH)
        self.assertEqual(risk.unresolved_factors, ())

        conversation, risk, returned = step(conversation, risk, turn(3, acts=(otp,)))
        self.assertEqual(returned.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(risk.unresolved_factors, (otp.fingerprint,))

        aggregate = next(item for item in conversation.acts if item.act == otp)
        self.assertEqual(aggregate.occurrence.count, 2)
        self.assertEqual(aggregate.occurrence.last_seen, 3)
        self.assertEqual(aggregate.retraction_count, 1)
        self.assertEqual(aggregate.last_retracted_at, 2)

    def test_independent_sessions_do_not_contaminate_each_other(self) -> None:
        first_conv = ConversationState.initial("session-a")
        first_risk = LongitudinalRiskState.initial("session-a")
        second_conv = ConversationState.initial("session-b")
        second_risk = LongitudinalRiskState.initial("session-b")
        _, first_risk, _ = step(
            first_conv, first_risk, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        _, second_risk, transition = step(second_conv, second_risk, turn(1))
        self.assertEqual(first_risk.current_risk, LongitudinalRiskLevel.CRITICAL)
        self.assertEqual(second_risk.current_risk, LongitudinalRiskLevel.NORMAL)
        self.assertEqual(transition.current_risk, LongitudinalRiskLevel.NORMAL)

    def test_deterministic_replay_gives_identical_transitions(self) -> None:
        evidence = (
            turn(1, contexts=frozenset({ContextEvidence(Context.BANKING)})),
            turn(2, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(3, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
            turn(4),
        )

        def replay() -> list[str]:
            conversation = ConversationState.initial("session-a")
            risk = LongitudinalRiskState.initial("session-a")
            serialized = []
            for item in evidence:
                conversation, risk, transition = step(conversation, risk, item)
                serialized.append(transition.to_json())
            return serialized

        self.assertEqual(replay(), replay())

    def test_duplicate_replay_semantics_remain_noop(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        evidence = turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        state_transition = apply_turn(conversation, evidence)
        risk_transition = evaluate_risk_transition(risk, state_transition)
        replay_state_transition = apply_turn(state_transition.next_state, evidence)
        replay_risk_transition = evaluate_risk_transition(
            risk_transition.next_state, replay_state_transition
        )
        self.assertEqual(replay_state_transition.status, ReplayStatus.EXACT_REPLAY)
        self.assertIs(replay_risk_transition.next_state, risk_transition.next_state)
        self.assertEqual(
            replay_risk_transition.current_risk, LongitudinalRiskLevel.CRITICAL
        )

    def test_no_raw_text_or_secrets_appear_in_risk_state(self) -> None:
        conversation = ConversationState.initial("session-a")
        risk = LongitudinalRiskState.initial("session-a")
        _, risk, _ = step(
            conversation, risk, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        serialized = risk.to_json()
        for forbidden in ("transcript", "raw_text", "483921", "password", "secret"):
            self.assertNotIn(forbidden, serialized.lower())

    def test_no_canary_or_model_dependency_enters_m2_1(self) -> None:
        self.assertNotIn("LongitudinalRiskState", guardian.__all__)
        self.assertFalse(hasattr(guardian, "LongitudinalRiskState"))
        source = (ROOT / "backend" / "guardian" / "longitudinal" / "risk.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("Gemini", "Gemma", "Ollama", "Canary", "server"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
