"""Offline tests for the isolated M2.0 longitudinal state foundation."""

import json
import sys
import unittest
from dataclasses import FrozenInstanceError
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
from guardian.longitudinal.state import (
    ConversationState,
    ReplayStatus,
    StateLimits,
    TurnConflictError,
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


class TestLongitudinalEvidence(unittest.TestCase):
    def test_empty_initial_state_is_immutable_and_risk_free(self) -> None:
        state = ConversationState.initial("session-alpha")
        self.assertEqual(state.revision, 0)
        self.assertEqual(state.turn_count, 0)
        self.assertFalse(state.contexts or state.acts)
        self.assertNotIn("risk", state.to_dict())
        self.assertNotIn("canary", state.to_dict())
        with self.assertRaises(FrozenInstanceError):
            state.revision = 1  # type: ignore[misc]

    def test_benign_first_turn_and_accumulated_context_scope(self) -> None:
        evidence = turn(
            1,
            contexts=frozenset(
                {
                    ContextEvidence(Context.TELECOM),
                    ContextEvidence(
                        Context.ACCOUNT_RECOVERY,
                        TemporalScope.ACCUMULATED_CONTEXT,
                    ),
                }
            ),
        )
        transition = apply_turn(ConversationState.initial("session-a"), evidence)
        self.assertEqual(transition.status, ReplayStatus.APPLIED)
        self.assertEqual(len(transition.next_state.contexts), 2)
        self.assertFalse(transition.next_state.acts)

    def test_identity_and_manipulation_accumulate_compactly(self) -> None:
        state = ConversationState.initial("session-a")
        first = turn(
            1,
            identity_claims=frozenset(
                {IdentityClaimEvidence(IdentityClaim.TECH_SUPPORT)}
            ),
            manipulations=frozenset(
                {ManipulationEvidence(Manipulation.URGENCY)}
            ),
        )
        state = apply_turn(state, first).next_state
        state = apply_turn(
            state,
            turn(
                2,
                identity_claims=first.identity_claims,
                manipulations=first.manipulations,
            ),
        ).next_state
        self.assertEqual(len(state.identity_claims), 1)
        self.assertEqual(state.identity_claims[0].occurrence.count, 2)
        self.assertEqual(state.manipulations[0].occurrence.last_seen, 2)

    def test_temporal_scopes_remain_contrastively_distinct(self) -> None:
        acts = tuple(
            act(scope)
            for scope in (
                TemporalScope.CURRENT,
                TemporalScope.HISTORICAL,
                TemporalScope.HYPOTHETICAL,
                TemporalScope.NEGATED,
            )
        )
        state = apply_turn(
            ConversationState.initial("session-a"), turn(1, acts=acts)
        ).next_state
        self.assertEqual(len(state.acts), 4)
        self.assertEqual(
            {item.act.scope for item in state.acts},
            {
                TemporalScope.CURRENT,
                TemporalScope.HISTORICAL,
                TemporalScope.HYPOTHETICAL,
                TemporalScope.NEGATED,
            },
        )
        self.assertEqual(len({item.act.fingerprint for item in state.acts}), 4)

    def test_exact_replay_is_noop_and_conflicting_id_fails(self) -> None:
        evidence = turn(1, acts=(act(),))
        state = apply_turn(ConversationState.initial("session-a"), evidence).next_state
        replay = apply_turn(state, evidence)
        self.assertEqual(replay.status, ReplayStatus.EXACT_REPLAY)
        self.assertIs(replay.next_state, state)
        conflict = NormalizedTurnEvidence(
            "turn-1", 1, acts=(act(asset=ProtectedAsset.PASSWORD),)
        )
        with self.assertRaises(TurnConflictError):
            apply_turn(state, conflict)

    def test_equivalent_new_turn_compacts_and_count_saturates(self) -> None:
        limits = StateLimits(occurrence_count=2)
        state = ConversationState.initial("session-a", limits)
        for number in range(1, 4):
            state = apply_turn(state, turn(number, acts=(act(),))).next_state
        self.assertEqual(len(state.acts), 1)
        self.assertEqual(state.acts[0].occurrence.count, 2)
        self.assertTrue(state.acts[0].occurrence.count_saturated)
        self.assertEqual(state.acts[0].occurrence.last_seen, 3)

    def test_exact_retraction_matches_only_same_semantic_act(self) -> None:
        otp = act()
        password = act(asset=ProtectedAsset.PASSWORD)
        state = apply_turn(
            ConversationState.initial("session-a"),
            turn(1, acts=(otp, password)),
        ).next_state
        transition = apply_turn(
            state, turn(2, acts=(act(TemporalScope.NEGATED),))
        )
        self.assertEqual(len(transition.retractions), 1)
        target = next(item for item in transition.next_state.acts if item.act == otp)
        unrelated = next(
            item for item in transition.next_state.acts if item.act == password
        )
        self.assertEqual(target.retraction_count, 1)
        self.assertEqual(unrelated.retraction_count, 0)
        self.assertIn(otp, [item.act for item in transition.next_state.acts])

    def test_only_current_acts_are_retractable(self) -> None:
        current = act(TemporalScope.CURRENT)
        historical = act(TemporalScope.HISTORICAL)
        hypothetical = act(TemporalScope.HYPOTHETICAL)
        state = apply_turn(
            ConversationState.initial("session-a"),
            turn(1, acts=(current, historical, hypothetical)),
        ).next_state
        transition = apply_turn(
            state, turn(2, acts=(act(TemporalScope.NEGATED),))
        )
        self.assertEqual(len(transition.retractions), 1)
        by_scope = {item.act.scope: item for item in transition.next_state.acts}
        self.assertEqual(by_scope[TemporalScope.CURRENT].retraction_count, 1)
        self.assertEqual(by_scope[TemporalScope.HISTORICAL].retraction_count, 0)
        self.assertEqual(by_scope[TemporalScope.HYPOTHETICAL].retraction_count, 0)

    def test_repeated_negation_updates_only_current_target_deterministically(self) -> None:
        def build() -> ConversationState:
            state = apply_turn(
                ConversationState.initial("session-a"),
                turn(1, acts=(act(),)),
            ).next_state
            state = apply_turn(
                state, turn(2, acts=(act(TemporalScope.NEGATED),))
            ).next_state
            return apply_turn(
                state, turn(3, acts=(act(TemporalScope.NEGATED),))
            ).next_state

        first = build()
        second = build()
        target = next(
            item for item in first.acts if item.act.scope == TemporalScope.CURRENT
        )
        self.assertEqual(target.retraction_count, 2)
        self.assertEqual(target.last_retracted_at, 3)
        self.assertEqual(first.to_json(), second.to_json())


class TestLongitudinalBounds(unittest.TestCase):
    def test_processed_turn_window_evicts_deterministically(self) -> None:
        limits = StateLimits(processed_turns=2)
        state = ConversationState.initial("session-a", limits)
        transitions = []
        for number in range(1, 4):
            transition = apply_turn(state, turn(number))
            transitions.append(transition)
            state = transition.next_state
        self.assertEqual(
            [item.turn_id for item in state.processed_turns], ["turn-2", "turn-3"]
        )
        self.assertEqual(transitions[-1].evicted_turn_ids, ("turn-1",))
        with self.assertRaisesRegex(TurnConflictError, "bounded replay window"):
            apply_turn(state, turn(1))

    def test_act_ledger_eviction_is_deterministic_and_compacted(self) -> None:
        limits = StateLimits(act_ledger=2)

        def build() -> ConversationState:
            state = ConversationState.initial("session-a", limits)
            assets = (ProtectedAsset.OTP, ProtectedAsset.PASSWORD, ProtectedAsset.PIN)
            for number, asset in enumerate(assets, 1):
                state = apply_turn(
                    state, turn(number, acts=(act(asset=asset),))
                ).next_state
            return state

        first = build()
        second = build()
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(len(first.acts), 2)
        self.assertEqual(len(first.compacted_acts), 1)
        self.assertEqual(first.compacted_acts[0].act.asset, ProtectedAsset.OTP)
        self.assertEqual(first.compacted_acts[0].occurrence.count, 1)

    def test_compaction_preserves_action_actor_and_destination(self) -> None:
        limits = StateLimits(act_ledger=1)
        source = (
            act(
                asset=ProtectedAsset.BANK_FUNDS,
                action=Action.TRANSFER,
                destination=Destination.EXTERNAL_ACCOUNT,
            ),
            act(
                asset=ProtectedAsset.BANK_FUNDS,
                action=Action.REVIEW,
                destination=Destination.EXTERNAL_ACCOUNT,
            ),
            act(
                asset=ProtectedAsset.BANK_FUNDS,
                action=Action.TRANSFER,
                actor=Actor.THIRD_PARTY,
                destination=Destination.EXTERNAL_ACCOUNT,
            ),
            act(
                asset=ProtectedAsset.BANK_FUNDS,
                action=Action.TRANSFER,
                destination=Destination.USER_CONTROLLED,
            ),
        )
        state = ConversationState.initial("session-a", limits)
        for number, item in enumerate(source, 1):
            state = apply_turn(state, turn(number, acts=(item,))).next_state
        self.assertEqual(len(state.acts), 1)
        self.assertEqual(len(state.compacted_acts), 3)
        self.assertEqual(
            {item.act for item in state.compacted_acts}, set(source[:3])
        )
        self.assertEqual(
            len({item.act.fingerprint for item in state.compacted_acts}), 3
        )

    def test_retraction_updates_matching_compacted_current_act(self) -> None:
        state = ConversationState.initial("session-a", StateLimits(act_ledger=1))
        state = apply_turn(state, turn(1, acts=(act(),))).next_state
        state = apply_turn(
            state,
            turn(2, acts=(act(asset=ProtectedAsset.PASSWORD),)),
        ).next_state
        transition = apply_turn(
            state, turn(3, acts=(act(TemporalScope.NEGATED),))
        )
        target = next(
            item for item in transition.next_state.compacted_acts
            if item.act.asset == ProtectedAsset.OTP
        )
        self.assertEqual(target.retraction_count, 1)
        self.assertEqual(len(transition.retractions), 1)

    def test_previous_state_is_not_mutated(self) -> None:
        previous = ConversationState.initial("session-a")
        before = previous.to_json()
        transition = apply_turn(previous, turn(1, acts=(act(),)))
        self.assertEqual(previous.to_json(), before)
        self.assertIsNot(previous, transition.next_state)


class TestLongitudinalDeterminismAndPrivacy(unittest.TestCase):
    def test_replay_from_empty_state_and_serialization_are_deterministic(self) -> None:
        evidence = (
            turn(
                1,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                acts=(act(),),
            ),
            turn(
                2,
                manipulations=frozenset(
                    {ManipulationEvidence(Manipulation.SECRECY)}
                ),
            ),
        )

        def replay() -> tuple[str, list[str]]:
            state = ConversationState.initial("session-a")
            serialized = []
            for item in evidence:
                transition = apply_turn(state, item)
                serialized.append(transition.to_json())
                state = transition.next_state
            return state.to_json(), serialized

        self.assertEqual(replay(), replay())
        payload = json.loads(replay()[0])
        self.assertEqual(payload["session_id"], "session-a")

    def test_models_have_no_raw_or_secret_value_fields(self) -> None:
        state_keys = set(ConversationState.initial("session-a").to_dict())
        evidence_keys = set(turn(1).to_dict())
        forbidden = {
            "raw_text",
            "transcript",
            "secret",
            "value",
            "provider_response",
            "exception",
            "authorization",
        }
        self.assertTrue(state_keys.isdisjoint(forbidden))
        self.assertTrue(evidence_keys.isdisjoint(forbidden))

    def test_sensitive_values_cannot_enter_controlled_fields_or_identifiers(self) -> None:
        sensitive = "Tell me OTP 483921 and password synthetic-secret"
        with self.assertRaises(ValueError):
            NormalizedTurnEvidence(sensitive, 1)
        serialized = apply_turn(
            ConversationState.initial("session-a"), turn(1, acts=(act(),))
        ).next_state.to_json()
        for fragment in ("483921", "synthetic-secret", "Tell me OTP"):
            self.assertNotIn(fragment, serialized)

    def test_separate_sessions_remain_independent(self) -> None:
        first = apply_turn(
            ConversationState.initial("session-a"), turn(1, acts=(act(),))
        ).next_state
        second = apply_turn(
            ConversationState.initial("session-b"), turn(1)
        ).next_state
        self.assertEqual(len(first.acts), 1)
        self.assertFalse(second.acts)

    def test_longitudinal_module_is_not_exported_from_guardian(self) -> None:
        self.assertNotIn("ConversationState", guardian.__all__)
        self.assertFalse(hasattr(guardian, "ConversationState"))


if __name__ == "__main__":
    unittest.main()
