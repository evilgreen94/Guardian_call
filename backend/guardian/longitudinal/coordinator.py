"""Pure M2.2 coordinator from longitudinal evidence to policy events."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from guardian.canary import CanaryPolicy
from guardian.models import (
    ActionType,
    CanaryDecision,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
)

from .evidence import NormalizedTurnEvidence, canonical_json
from .risk import (
    LongitudinalRiskLevel,
    LongitudinalRiskState,
    RiskTransition,
    RISK_RANK,
    evaluate_risk_transition,
)
from .state import ConversationState, StateTransition, apply_turn


class PolicyEventType(str, Enum):
    NO_ACTION = "NO_ACTION"
    WARN = "WARN"
    ESCALATE = "ESCALATE"


class PolicySuppressionReason(str, Enum):
    NONE = "NONE"
    RISK_BELOW_WARNING_THRESHOLD = "RISK_BELOW_WARNING_THRESHOLD"
    NO_CURRENT_ACTIVE_DANGER = "NO_CURRENT_ACTIVE_DANGER"
    SAME_ACTIVE_DANGER = "SAME_ACTIVE_DANGER"
    CANARY_DENIED = "CANARY_DENIED"
    EXACT_REPLAY = "EXACT_REPLAY"


@dataclass(frozen=True)
class PolicyHistoryEntry:
    turn_number: int
    event_type: PolicyEventType
    current_risk: LongitudinalRiskLevel
    active_factors: Tuple[str, ...]
    duplicate_suppressed: bool
    reasons: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "event_type": self.event_type.value,
            "current_risk": self.current_risk.value,
            "active_factors": list(self.active_factors),
            "duplicate_suppressed": self.duplicate_suppressed,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class PolicyState:
    session_id: str
    warned_active_factors: Tuple[str, ...] = ()
    last_intervention_risk: Optional[LongitudinalRiskLevel] = None
    history: Tuple[PolicyHistoryEntry, ...] = ()
    history_limit: int = 16

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id is required")
        if self.last_intervention_risk is not None and not isinstance(
            self.last_intervention_risk, LongitudinalRiskLevel
        ):
            raise TypeError("last_intervention_risk must be a LongitudinalRiskLevel")
        if self.history_limit < 1:
            raise ValueError("history_limit must be positive")

    @classmethod
    def initial(cls, session_id: str, *, history_limit: int = 16) -> "PolicyState":
        return cls(session_id=session_id, history_limit=history_limit)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "warned_active_factors": list(self.warned_active_factors),
            "last_intervention_risk": (
                self.last_intervention_risk.value
                if self.last_intervention_risk
                else None
            ),
            "history": [item.to_dict() for item in self.history],
            "history_limit": self.history_limit,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class CanaryPolicyEvent:
    event_type: PolicyEventType
    current_risk: LongitudinalRiskLevel
    peak_risk: LongitudinalRiskLevel
    active_factors: Tuple[str, ...]
    new_factors: Tuple[str, ...]
    risk_increased: bool
    duplicate_suppressed: bool
    suppression_reason: PolicySuppressionReason
    reasons: Tuple[str, ...]
    canary_action: Optional[str] = None
    canary_decision: Optional[str] = None
    canary_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "current_risk": self.current_risk.value,
            "peak_risk": self.peak_risk.value,
            "active_factors": list(self.active_factors),
            "new_factors": list(self.new_factors),
            "risk_increased": self.risk_increased,
            "duplicate_suppressed": self.duplicate_suppressed,
            "suppression_reason": self.suppression_reason.value,
            "reasons": list(self.reasons),
            "canary_action": self.canary_action,
            "canary_decision": self.canary_decision,
            "canary_reason": self.canary_reason,
        }


@dataclass(frozen=True)
class LongitudinalDecision:
    conversation_transition: StateTransition
    risk_transition: RiskTransition
    policy_event: CanaryPolicyEvent
    next_conversation_state: ConversationState
    next_risk_state: LongitudinalRiskState
    next_policy_state: PolicyState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_transition": self.conversation_transition.to_dict(),
            "risk_transition": self.risk_transition.to_dict(),
            "policy_event": self.policy_event.to_dict(),
            "next_conversation_state": self.next_conversation_state.to_dict(),
            "next_risk_state": self.next_risk_state.to_dict(),
            "next_policy_state": self.next_policy_state.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def evaluate_longitudinal_turn(
    conversation_state: ConversationState,
    risk_state: LongitudinalRiskState,
    policy_state: PolicyState,
    normalized_evidence: NormalizedTurnEvidence,
    *,
    canary: Optional[CanaryPolicy] = None,
) -> LongitudinalDecision:
    """Apply evidence, risk transition, and Canary-facing policy decision."""
    if not (
        conversation_state.session_id
        == risk_state.session_id
        == policy_state.session_id
    ):
        raise ValueError("conversation, risk, and policy sessions differ")

    conversation_transition = apply_turn(conversation_state, normalized_evidence)
    risk_transition = evaluate_risk_transition(risk_state, conversation_transition)
    policy_event = derive_policy_event(
        policy_state,
        risk_transition,
        canary=canary or CanaryPolicy(),
    )
    next_policy_state = _apply_policy_event(policy_state, policy_event, risk_transition)
    return LongitudinalDecision(
        conversation_transition=conversation_transition,
        risk_transition=risk_transition,
        policy_event=policy_event,
        next_conversation_state=conversation_transition.next_state,
        next_risk_state=risk_transition.next_state,
        next_policy_state=next_policy_state,
    )


def derive_policy_event(
    policy_state: PolicyState,
    risk_transition: RiskTransition,
    *,
    canary: CanaryPolicy,
) -> CanaryPolicyEvent:
    if policy_state.session_id != risk_transition.next_state.session_id:
        raise ValueError("policy state and risk state sessions differ")

    active_factors = tuple(sorted(risk_transition.next_state.unresolved_factors))
    previous_factors = set(policy_state.warned_active_factors)
    new_factors = tuple(item for item in active_factors if item not in previous_factors)
    risk_increased = _risk_increased(policy_state, risk_transition.current_risk)
    base_reasons = tuple(reason.code for reason in risk_transition.reasons)

    if risk_transition.next_state is policy_state:
        raise TypeError("risk and policy states must remain separate")

    if not active_factors:
        reason = (
            PolicySuppressionReason.RISK_BELOW_WARNING_THRESHOLD
            if risk_transition.current_risk
            in (LongitudinalRiskLevel.NORMAL, LongitudinalRiskLevel.SUSPICIOUS)
            else PolicySuppressionReason.NO_CURRENT_ACTIVE_DANGER
        )
        return _no_action(
            risk_transition,
            active_factors,
            new_factors,
            risk_increased,
            reason,
            base_reasons,
        )

    if risk_transition.current_risk in (
        LongitudinalRiskLevel.NORMAL,
        LongitudinalRiskLevel.SUSPICIOUS,
    ):
        return _no_action(
            risk_transition,
            active_factors,
            new_factors,
            risk_increased,
            PolicySuppressionReason.RISK_BELOW_WARNING_THRESHOLD,
            base_reasons,
        )

    if not new_factors and not risk_increased:
        return _no_action(
            risk_transition,
            active_factors,
            new_factors,
            risk_increased,
            PolicySuppressionReason.SAME_ACTIVE_DANGER,
            base_reasons,
            duplicate=True,
        )

    assessment = _risk_assessment(risk_transition)
    decision = canary.evaluate_action(assessment, ActionType.WARN_USER)
    if decision.decision != PolicyDecision.ALLOW:
        return _no_action(
            risk_transition,
            active_factors,
            new_factors,
            risk_increased,
            PolicySuppressionReason.CANARY_DENIED,
            base_reasons + (decision.reason,),
            decision=decision,
        )
    event_type = (
        PolicyEventType.ESCALATE
        if risk_transition.current_risk == LongitudinalRiskLevel.CRITICAL
        else PolicyEventType.WARN
    )
    return CanaryPolicyEvent(
        event_type=event_type,
        current_risk=risk_transition.current_risk,
        peak_risk=risk_transition.peak_risk,
        active_factors=active_factors,
        new_factors=new_factors,
        risk_increased=risk_increased,
        duplicate_suppressed=False,
        suppression_reason=PolicySuppressionReason.NONE,
        reasons=base_reasons + (decision.reason,),
        canary_action=decision.action.value,
        canary_decision=decision.decision.value,
        canary_reason=decision.reason,
    )


def _apply_policy_event(
    policy_state: PolicyState,
    event: CanaryPolicyEvent,
    risk_transition: RiskTransition,
) -> PolicyState:
    if event.event_type in (PolicyEventType.WARN, PolicyEventType.ESCALATE):
        warned = event.active_factors
        last_risk: Optional[LongitudinalRiskLevel] = event.current_risk
    elif not event.active_factors:
        warned = ()
        last_risk = None
    else:
        warned = policy_state.warned_active_factors
        last_risk = policy_state.last_intervention_risk
    entry = PolicyHistoryEntry(
        turn_number=risk_transition.turn_number,
        event_type=event.event_type,
        current_risk=event.current_risk,
        active_factors=event.active_factors,
        duplicate_suppressed=event.duplicate_suppressed,
        reasons=event.reasons,
    )
    return replace(
        policy_state,
        warned_active_factors=warned,
        last_intervention_risk=last_risk,
        history=(policy_state.history + (entry,))[-policy_state.history_limit :],
    )


def _risk_assessment(risk_transition: RiskTransition) -> RiskAssessment:
    return RiskAssessment(
        level=RiskLevel(risk_transition.current_risk.value),
        reasons=[reason.detail for reason in risk_transition.reasons],
        contributing_signals=[reason.code for reason in risk_transition.reasons],
        timestamp=f"turn:{risk_transition.turn_number}",
    )


def _risk_increased(
    policy_state: PolicyState, current_risk: LongitudinalRiskLevel
) -> bool:
    if policy_state.last_intervention_risk is None:
        return current_risk in (
            LongitudinalRiskLevel.HIGH,
            LongitudinalRiskLevel.CRITICAL,
        )
    return RISK_RANK[current_risk] > RISK_RANK[policy_state.last_intervention_risk]


def _no_action(
    risk_transition: RiskTransition,
    active_factors: Tuple[str, ...],
    new_factors: Tuple[str, ...],
    risk_increased: bool,
    reason: PolicySuppressionReason,
    reasons: Tuple[str, ...],
    *,
    duplicate: bool = False,
    decision: Optional[CanaryDecision] = None,
) -> CanaryPolicyEvent:
    return CanaryPolicyEvent(
        event_type=PolicyEventType.NO_ACTION,
        current_risk=risk_transition.current_risk,
        peak_risk=risk_transition.peak_risk,
        active_factors=active_factors,
        new_factors=new_factors,
        risk_increased=risk_increased,
        duplicate_suppressed=duplicate,
        suppression_reason=reason,
        reasons=reasons,
        canary_action=decision.action.value if decision else None,
        canary_decision=decision.decision.value if decision else None,
        canary_reason=decision.reason if decision else None,
    )
