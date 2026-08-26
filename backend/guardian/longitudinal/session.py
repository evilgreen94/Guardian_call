"""M2.3 deterministic end-to-end longitudinal integration harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .coordinator import (
    CanaryPolicyEvent,
    PolicyEventType,
    PolicyState,
    PolicySuppressionReason,
    evaluate_longitudinal_turn,
)
from .evidence import NormalizedTurnEvidence, canonical_json
from .risk import LongitudinalRiskLevel, LongitudinalRiskState
from .state import ConversationState, ReplayStatus, StateTransition, apply_turn


class CanaryAuthorizationStatus(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ASK_USER = "ASK_USER"
    NOT_REQUESTED = "NOT_REQUESTED"


@dataclass(frozen=True)
class LongitudinalSessionState:
    conversation_state: ConversationState
    risk_state: LongitudinalRiskState
    policy_state: PolicyState

    def __post_init__(self) -> None:
        if not (
            self.conversation_state.session_id
            == self.risk_state.session_id
            == self.policy_state.session_id
        ):
            raise ValueError("longitudinal session components must share a session_id")

    @classmethod
    def initial(cls, session_id: str) -> "LongitudinalSessionState":
        return cls(
            conversation_state=ConversationState.initial(session_id),
            risk_state=LongitudinalRiskState.initial(session_id),
            policy_state=PolicyState.initial(session_id),
        )

    @property
    def session_id(self) -> str:
        return self.conversation_state.session_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_state": self.conversation_state.to_dict(),
            "risk_state": self.risk_state.to_dict(),
            "policy_state": self.policy_state.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class CanaryAuthorizationProjection:
    action: str
    status: CanaryAuthorizationStatus
    reason: str
    risk_level: LongitudinalRiskLevel

    def to_dict(self) -> Dict[str, str]:
        return {
            "action": self.action,
            "status": self.status.value,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
        }


@dataclass(frozen=True)
class LongitudinalTurnResult:
    turn_id: str
    turn_number: int
    replay_status: ReplayStatus
    conversation_transition: StateTransition
    risk_transition: Optional[Dict[str, Any]]
    policy_event: CanaryPolicyEvent
    canary_authorization: CanaryAuthorizationProjection
    previous_state: LongitudinalSessionState
    next_state: LongitudinalSessionState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "turn_number": self.turn_number,
            "replay_status": self.replay_status.value,
            "conversation_transition": self.conversation_transition.to_dict(),
            "risk_transition": self.risk_transition,
            "policy_event": self.policy_event.to_dict(),
            "canary_authorization": self.canary_authorization.to_dict(),
            "previous_state": self.previous_state.to_dict(),
            "next_state": self.next_state.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def process_normalized_turn(
    session_state: LongitudinalSessionState,
    evidence: NormalizedTurnEvidence,
) -> LongitudinalTurnResult:
    """Process one normalized turn through the deterministic longitudinal stack."""
    replay_transition = apply_turn(session_state.conversation_state, evidence)
    if replay_transition.status == ReplayStatus.EXACT_REPLAY:
        policy_event = _exact_replay_policy_event(session_state, evidence)
        return LongitudinalTurnResult(
            turn_id=evidence.turn_id,
            turn_number=evidence.turn_number,
            replay_status=ReplayStatus.EXACT_REPLAY,
            conversation_transition=replay_transition,
            risk_transition=None,
            policy_event=policy_event,
            canary_authorization=_not_requested(
                policy_event.current_risk,
                "Exact replay did not request Canary authorization.",
            ),
            previous_state=session_state,
            next_state=session_state,
        )

    coordinated = evaluate_longitudinal_turn(
        session_state.conversation_state,
        session_state.risk_state,
        session_state.policy_state,
        evidence,
    )
    next_state = LongitudinalSessionState(
        conversation_state=coordinated.next_conversation_state,
        risk_state=coordinated.next_risk_state,
        policy_state=coordinated.next_policy_state,
    )
    return LongitudinalTurnResult(
        turn_id=evidence.turn_id,
        turn_number=evidence.turn_number,
        replay_status=ReplayStatus.APPLIED,
        conversation_transition=coordinated.conversation_transition,
        risk_transition=coordinated.risk_transition.to_dict(),
        policy_event=coordinated.policy_event,
        canary_authorization=_project_canary(coordinated.policy_event),
        previous_state=session_state,
        next_state=next_state,
    )


def _project_canary(event: CanaryPolicyEvent) -> CanaryAuthorizationProjection:
    if event.canary_decision is None:
        return _not_requested(
            event.current_risk,
            "M2.2 did not propose a Canary-controlled action.",
        )
    return CanaryAuthorizationProjection(
        action=event.canary_action or "warn_user",
        status=CanaryAuthorizationStatus(event.canary_decision),
        reason=event.canary_reason or "Canary decision recorded.",
        risk_level=event.current_risk,
    )


def _not_requested(
    risk_level: LongitudinalRiskLevel, reason: str
) -> CanaryAuthorizationProjection:
    return CanaryAuthorizationProjection(
        action="warn_user",
        status=CanaryAuthorizationStatus.NOT_REQUESTED,
        reason=reason,
        risk_level=risk_level,
    )


def _exact_replay_policy_event(
    session_state: LongitudinalSessionState,
    evidence: NormalizedTurnEvidence,
) -> CanaryPolicyEvent:
    return CanaryPolicyEvent(
        event_type=PolicyEventType.NO_ACTION,
        current_risk=session_state.risk_state.current_risk,
        peak_risk=session_state.risk_state.peak_risk,
        active_factors=session_state.risk_state.unresolved_factors,
        new_factors=(),
        risk_increased=False,
        duplicate_suppressed=True,
        suppression_reason=PolicySuppressionReason.EXACT_REPLAY,
        reasons=("EXACT_REPLAY_NO_SESSION_EVOLUTION",),
        canary_action=None,
        canary_decision=None,
        canary_reason=None,
    )
