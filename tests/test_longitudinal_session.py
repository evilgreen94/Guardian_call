"""Tests for the M2.3 deterministic longitudinal session harness."""

import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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
    NormalizedTurnEvidence,
    ProtectedAsset,
    TemporalScope,
)
from guardian.longitudinal.session import (
    CanaryAuthorizationStatus,
    LongitudinalSessionState,
    process_normalized_turn,
)
from guardian.longitudinal.coordinator import PolicyEventType, PolicySuppressionReason
from guardian.longitudinal.risk import LongitudinalRiskLevel
from guardian.longitudinal.state import ReplayStatus, TurnConflictError


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


def process_sequence(evidence: tuple[NormalizedTurnEvidence, ...]) -> list[object]:
    state = LongitudinalSessionState.initial("session-a")
    results = []
    for item in evidence:
        result = process_normalized_turn(state, item)
        results.append(result)
        state = result.next_state
    return results


class TestM23CanonicalVerticalSlice(unittest.TestCase):
    def test_canonical_six_turn_vertical_slice(self) -> None:
        session = LongitudinalSessionState.initial("session-a")
        evidence = (
            turn(
                1,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            ),
            turn(2, contexts=frozenset({ContextEvidence(Context.BANKING)})),
            turn(3, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(4, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(5, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
            turn(
                6,
                acts=(
                    act(
                        asset=ProtectedAsset.REMOTE_CONTROL,
                        action=Action.GRANT_ACCESS,
                    ),
                ),
            ),
        )
        results = []
        for item in evidence:
            result = process_normalized_turn(session, item)
            results.append(result)
            session = result.next_state

        self.assertEqual(results[0].policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(
            results[0].canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )
        self.assertEqual(results[1].policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(results[2].risk_transition["previous_risk"], "NORMAL")
        self.assertEqual(results[2].risk_transition["current_risk"], "CRITICAL")
        self.assertEqual(results[2].policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(results[2].canary_authorization.status, CanaryAuthorizationStatus.ALLOW)
        self.assertEqual(results[2].canary_authorization.action, "warn_user")
        self.assertEqual(results[3].policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertTrue(results[3].policy_event.duplicate_suppressed)
        self.assertEqual(
            results[3].canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )
        self.assertEqual(results[4].risk_transition["current_risk"], "HIGH")
        self.assertEqual(results[4].risk_transition["peak_risk"], "CRITICAL")
        self.assertEqual(results[4].policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(results[5].risk_transition["current_risk"], "CRITICAL")
        self.assertEqual(results[5].policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(len(results[5].policy_event.new_factors), 1)
        self.assertEqual(results[5].canary_authorization.status, CanaryAuthorizationStatus.ALLOW)


class TestM23RequiredSequences(unittest.TestCase):
    def test_all_benign_never_authorizes_warn_user(self) -> None:
        results = process_sequence(
            (
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
            )
        )
        self.assertTrue(
            all(
                item.canary_authorization.status
                == CanaryAuthorizationStatus.NOT_REQUESTED
                for item in results
            )
        )

    def test_trust_poisoning_does_not_suppress_sensitive_request(self) -> None:
        evidence = tuple(
            turn(
                number,
                contexts=frozenset({ContextEvidence(Context.BANKING)}),
                identity_claims=frozenset(
                    {IdentityClaimEvidence(IdentityClaim.FINANCIAL_INSTITUTION)}
                ),
            )
            for number in range(1, 4)
        ) + (turn(4, acts=(act(asset=ProtectedAsset.OTP),)),)
        result = process_sequence(evidence)[-1]
        self.assertEqual(result.policy_event.event_type, PolicyEventType.ESCALATE)
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)

    def test_temporal_contrast_only_current_authorizes_warning(self) -> None:
        for scope, expected in (
            (TemporalScope.CURRENT, CanaryAuthorizationStatus.ALLOW),
            (TemporalScope.HISTORICAL, CanaryAuthorizationStatus.NOT_REQUESTED),
            (TemporalScope.HYPOTHETICAL, CanaryAuthorizationStatus.NOT_REQUESTED),
            (TemporalScope.NEGATED, CanaryAuthorizationStatus.NOT_REQUESTED),
        ):
            with self.subTest(scope=scope):
                result = process_sequence((turn(1, acts=(act(scope=scope),)),))[0]
                self.assertEqual(result.canary_authorization.status, expected)

    def test_self_service_is_not_transformed_into_caller_directed_danger(self) -> None:
        result = process_sequence(
            (
                turn(
                    1,
                    acts=(
                        act(
                            asset=ProtectedAsset.OTP,
                            action=Action.ENTER,
                            destination=Destination.OFFICIAL_SELF_SERVICE,
                        ),
                    ),
                ),
            )
        )[0]
        self.assertEqual(result.policy_event.event_type, PolicyEventType.NO_ACTION)
        self.assertEqual(result.policy_event.active_factors, ())
        self.assertEqual(
            result.canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )

    def test_danger_returns_canary_may_authorize_again(self) -> None:
        results = process_sequence(
            (
                turn(1, acts=(act(asset=ProtectedAsset.PASSWORD),)),
                turn(
                    2,
                    acts=(
                        act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.PASSWORD),
                    ),
                ),
                turn(3),
                turn(4),
                turn(5, acts=(act(asset=ProtectedAsset.PASSWORD),)),
            )
        )
        self.assertEqual(results[0].canary_authorization.status, CanaryAuthorizationStatus.ALLOW)
        self.assertEqual(results[4].canary_authorization.status, CanaryAuthorizationStatus.ALLOW)
        self.assertEqual(results[4].policy_event.event_type, PolicyEventType.ESCALATE)

    def test_independent_sessions_do_not_contaminate(self) -> None:
        first = LongitudinalSessionState.initial("session-a")
        second = LongitudinalSessionState.initial("session-b")
        first_result = process_normalized_turn(
            first, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        second_result = process_normalized_turn(second, turn(1))
        self.assertEqual(
            first_result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW
        )
        self.assertEqual(
            second_result.canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )


class TestM23ReplayDeterminismAndPrivacy(unittest.TestCase):
    def test_exact_replay_is_idempotent_without_policy_or_canary_growth(self) -> None:
        state = LongitudinalSessionState.initial("session-a")
        evidence = turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        first = process_normalized_turn(state, evidence)
        replay = process_normalized_turn(first.next_state, evidence)
        self.assertEqual(replay.replay_status, ReplayStatus.EXACT_REPLAY)
        self.assertIsNone(replay.risk_transition)
        self.assertIs(replay.next_state, first.next_state)
        self.assertEqual(
            len(replay.next_state.policy_state.history),
            len(first.next_state.policy_state.history),
        )
        self.assertEqual(
            replay.canary_authorization.status,
            CanaryAuthorizationStatus.NOT_REQUESTED,
        )
        self.assertEqual(
            replay.policy_event.suppression_reason,
            PolicySuppressionReason.EXACT_REPLAY,
        )

    def test_conflicting_replay_raises_m2_0_error(self) -> None:
        state = LongitudinalSessionState.initial("session-a")
        first = process_normalized_turn(
            state, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
        )
        conflict = NormalizedTurnEvidence(
            "turn-1", 1, acts=(act(asset=ProtectedAsset.PASSWORD),)
        )
        with self.assertRaises(TurnConflictError):
            process_normalized_turn(first.next_state, conflict)

    def test_deterministic_repeated_execution(self) -> None:
        evidence = (
            turn(1, contexts=frozenset({ContextEvidence(Context.BANKING)})),
            turn(2, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(3, acts=(act(asset=ProtectedAsset.OTP),)),
            turn(4, acts=(act(scope=TemporalScope.NEGATED, asset=ProtectedAsset.OTP),)),
            turn(5),
        )

        def replay() -> list[str]:
            state = LongitudinalSessionState.initial("session-a")
            serialized = []
            for item in evidence:
                result = process_normalized_turn(state, item)
                serialized.append(result.to_json())
                state = result.next_state
            return serialized

        self.assertEqual(replay(), replay())

    def test_no_action_execution_or_event_sink_required(self) -> None:
        result = process_sequence((turn(1, acts=(act(asset=ProtectedAsset.OTP),)),))[0]
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)
        serialized = result.to_json()
        self.assertNotIn("USER_WARNING", serialized)
        self.assertNotIn("TRUSTED_CONTACT_NOTIFIED", serialized)
        self.assertNotIn("CALL_ENDED", serialized)

    def test_privacy_invariants(self) -> None:
        result = process_sequence((turn(1, acts=(act(asset=ProtectedAsset.OTP),)),))[0]
        serialized = json.dumps(result.to_dict(), sort_keys=True).lower()
        for forbidden in (
            "transcript",
            "raw_text",
            "raw model",
            "provider response",
            "api_key",
            "authorization_header",
            "authentication token",
            "483921",
            "synthetic-secret",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_no_network_or_model_dependency(self) -> None:
        state = LongitudinalSessionState.initial("session-a")
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            result = process_normalized_turn(
                state, turn(1, acts=(act(asset=ProtectedAsset.OTP),))
            )
        self.assertEqual(result.canary_authorization.status, CanaryAuthorizationStatus.ALLOW)
        self.assertNotIn("LongitudinalSessionState", guardian.__all__)
        source = (ROOT / "backend" / "guardian" / "longitudinal" / "session.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("Gemini", "Gemma", "Ollama", "requests", "urllib"):
            self.assertNotIn(forbidden, source)

    def test_prior_component_files_are_unchanged_by_m2_3(self) -> None:
        self.assertEqual(
            [],
            [
                path
                for path in (
                    "backend/guardian/longitudinal/state.py",
                    "backend/guardian/longitudinal/evidence.py",
                    "backend/guardian/longitudinal/risk.py",
                    "backend/guardian/longitudinal/coordinator.py",
                    "backend/guardian/canary.py",
                    "backend/guardian/risk.py",
                    "backend/guardian/pipeline.py",
                    "backend/server.py",
                )
                if "M2.3" in (ROOT / path).read_text(encoding="utf-8")
            ],
        )


if __name__ == "__main__":
    unittest.main()
