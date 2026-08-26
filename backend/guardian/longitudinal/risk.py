"""Deterministic M2.1 longitudinal risk transitions over M2.0 state."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Iterable, Optional, Tuple

from .evidence import (
    Action,
    BehavioralAct,
    ContextEvidence,
    Destination,
    IdentityClaimEvidence,
    Manipulation,
    ManipulationEvidence,
    ProtectedAsset,
    TemporalScope,
    canonical_json,
)
from .state import ActAggregate, ConversationState, ReplayStatus, StateTransition


class LongitudinalRiskLevel(str, Enum):
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


RISK_RANK = {
    LongitudinalRiskLevel.NORMAL: 0,
    LongitudinalRiskLevel.SUSPICIOUS: 1,
    LongitudinalRiskLevel.HIGH: 2,
    LongitudinalRiskLevel.CRITICAL: 3,
}

RISK_FROM_RANK = {value: key for key, value in RISK_RANK.items()}

HISTORY_LIMIT = 16
RESIDUAL_DECAY_TURNS = 2

EXTERNAL_DESTINATIONS = frozenset(
    {
        Destination.OTHER_PARTY,
        Destination.THIRD_PARTY,
        Destination.EXTERNAL_ACCOUNT,
        Destination.UNKNOWN,
    }
)

CONTROL_PRESERVING_DESTINATIONS = frozenset(
    {Destination.OFFICIAL_SELF_SERVICE, Destination.USER_CONTROLLED}
)

SECRET_OR_ACCOUNT_ASSETS = frozenset(
    {
        ProtectedAsset.OTP,
        ProtectedAsset.PASSWORD,
        ProtectedAsset.PIN,
        ProtectedAsset.RECOVERY_CODE,
        ProtectedAsset.CARD_SECURITY_CODE,
        ProtectedAsset.SEED_PHRASE,
        ProtectedAsset.PRIVATE_KEY,
        ProtectedAsset.LOGIN_APPROVAL,
        ProtectedAsset.ACCOUNT_RECOVERY,
        ProtectedAsset.SECURITY_SETTINGS,
    }
)

REMOTE_ACCESS_ASSETS = frozenset(
    {
        ProtectedAsset.REMOTE_SOFTWARE,
        ProtectedAsset.REMOTE_CONTROL,
        ProtectedAsset.SCREEN_CONTENT,
    }
)

MONEY_ASSETS = frozenset(
    {
        ProtectedAsset.BANK_FUNDS,
        ProtectedAsset.PAYMENT_APP_FUNDS,
        ProtectedAsset.CASH,
        ProtectedAsset.GIFT_CARD,
        ProtectedAsset.CRYPTO_ASSET,
    }
)

HIGH_SIGNAL_MANIPULATIONS = frozenset(
    {
        Manipulation.URGENCY,
        Manipulation.FEAR_OR_THREAT,
        Manipulation.AUTHORITY_PRESSURE,
        Manipulation.SECRECY,
        Manipulation.ISOLATION,
        Manipulation.KEEP_ENGAGED,
        Manipulation.PROTECTIVE_PRETEXT,
        Manipulation.EMOTIONAL_PRESSURE,
    }
)


@dataclass(frozen=True)
class RiskReason:
    code: str
    detail: str
    level: LongitudinalRiskLevel
    act_fingerprint: Optional[str] = None
    turn_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "level": self.level.value,
            "act_fingerprint": self.act_fingerprint,
            "turn_number": self.turn_number,
        }


@dataclass(frozen=True)
class RiskHistoryEntry:
    turn_number: int
    previous_risk: LongitudinalRiskLevel
    current_risk: LongitudinalRiskLevel
    peak_risk: LongitudinalRiskLevel
    reasons: Tuple[RiskReason, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "previous_risk": self.previous_risk.value,
            "current_risk": self.current_risk.value,
            "peak_risk": self.peak_risk.value,
            "reasons": [item.to_dict() for item in self.reasons],
        }


@dataclass(frozen=True)
class LongitudinalRiskState:
    session_id: str
    previous_risk: LongitudinalRiskLevel = LongitudinalRiskLevel.NORMAL
    current_risk: LongitudinalRiskLevel = LongitudinalRiskLevel.NORMAL
    peak_risk: LongitudinalRiskLevel = LongitudinalRiskLevel.NORMAL
    unresolved_factors: Tuple[str, ...] = ()
    history: Tuple[RiskHistoryEntry, ...] = ()
    history_limit: int = HISTORY_LIMIT
    residual_decay_turns: int = RESIDUAL_DECAY_TURNS

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id is required")
        for name in ("previous_risk", "current_risk", "peak_risk"):
            if not isinstance(getattr(self, name), LongitudinalRiskLevel):
                raise TypeError(f"{name} must be a LongitudinalRiskLevel")
        if self.history_limit < 1:
            raise ValueError("history_limit must be positive")
        if self.residual_decay_turns < 1:
            raise ValueError("residual_decay_turns must be positive")

    @classmethod
    def initial(
        cls,
        session_id: str,
        *,
        history_limit: int = HISTORY_LIMIT,
        residual_decay_turns: int = RESIDUAL_DECAY_TURNS,
    ) -> "LongitudinalRiskState":
        return cls(
            session_id=session_id,
            history_limit=history_limit,
            residual_decay_turns=residual_decay_turns,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "previous_risk": self.previous_risk.value,
            "current_risk": self.current_risk.value,
            "peak_risk": self.peak_risk.value,
            "unresolved_factors": list(self.unresolved_factors),
            "history": [item.to_dict() for item in self.history],
            "history_limit": self.history_limit,
            "residual_decay_turns": self.residual_decay_turns,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class RiskTransition:
    turn_id: str
    turn_number: int
    previous_risk: LongitudinalRiskLevel
    current_risk: LongitudinalRiskLevel
    peak_risk: LongitudinalRiskLevel
    reasons: Tuple[RiskReason, ...]
    next_state: LongitudinalRiskState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "turn_number": self.turn_number,
            "previous_risk": self.previous_risk.value,
            "current_risk": self.current_risk.value,
            "peak_risk": self.peak_risk.value,
            "reasons": [item.to_dict() for item in self.reasons],
            "next_state": self.next_state.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def evaluate_risk_transition(
    risk_state: LongitudinalRiskState,
    state_transition: StateTransition,
) -> RiskTransition:
    """Evaluate risk from an already-applied M2.0 state transition."""
    conversation_state = state_transition.next_state
    if risk_state.session_id != conversation_state.session_id:
        raise ValueError("risk state and conversation state sessions differ")
    if state_transition.status == ReplayStatus.EXACT_REPLAY:
        return RiskTransition(
            turn_id=state_transition.turn_id,
            turn_number=state_transition.turn_number,
            previous_risk=risk_state.current_risk,
            current_risk=risk_state.current_risk,
            peak_risk=risk_state.peak_risk,
            reasons=(
                RiskReason(
                    "EXACT_REPLAY_NO_CHANGE",
                    "Duplicate normalized turn did not change longitudinal risk.",
                    risk_state.current_risk,
                    turn_number=state_transition.turn_number,
                ),
            ),
            next_state=risk_state,
        )

    active = tuple(_active_actionable_factors(conversation_state.acts))
    current_reasons = tuple(_current_reasons(active, conversation_state))
    residual_reasons = tuple(
        _residual_reasons(risk_state, active, state_transition.turn_number)
    )
    persistence_reasons = tuple(
        _persistence_reasons(conversation_state.acts, active, state_transition.turn_number)
    )
    contradiction_reasons = tuple(
        _contradiction_reasons(active, conversation_state.acts)
    )
    reasons = (
        current_reasons
        + residual_reasons
        + persistence_reasons
        + contradiction_reasons
    )
    current_risk = _max_reason_level(reasons)
    peak_risk = _max_level(risk_state.peak_risk, current_risk)
    unresolved = tuple(sorted(item.act.fingerprint for item in active))
    entry = RiskHistoryEntry(
        turn_number=state_transition.turn_number,
        previous_risk=risk_state.current_risk,
        current_risk=current_risk,
        peak_risk=peak_risk,
        reasons=reasons,
    )
    history = (risk_state.history + (entry,))[-risk_state.history_limit :]
    next_state = replace(
        risk_state,
        previous_risk=risk_state.current_risk,
        current_risk=current_risk,
        peak_risk=peak_risk,
        unresolved_factors=unresolved,
        history=history,
    )
    return RiskTransition(
        turn_id=state_transition.turn_id,
        turn_number=state_transition.turn_number,
        previous_risk=risk_state.current_risk,
        current_risk=current_risk,
        peak_risk=peak_risk,
        reasons=reasons,
        next_state=next_state,
    )


def _active_actionable_factors(
    aggregates: Iterable[ActAggregate],
) -> Tuple[ActAggregate, ...]:
    return tuple(
        sorted(
            (
                item
                for item in aggregates
                if item.act.scope == TemporalScope.CURRENT
                and item.act.asset is not None
                and item.act.destination in EXTERNAL_DESTINATIONS
                and _is_current_factor_unresolved(item)
            ),
            key=lambda item: item.act.fingerprint,
        )
    )


def _is_current_factor_unresolved(item: ActAggregate) -> bool:
    if item.last_retracted_at is None:
        return True
    return item.occurrence.last_seen > item.last_retracted_at


def _current_reasons(
    active: Tuple[ActAggregate, ...],
    state: ConversationState,
) -> Tuple[RiskReason, ...]:
    reasons = []
    has_manipulation = _has_current_manipulation(state.manipulations)
    has_corroboration = _has_compatible_context_or_claim(state)
    for item in active:
        level = _base_risk_for_act(item.act)
        if has_manipulation and level == LongitudinalRiskLevel.HIGH:
            level = LongitudinalRiskLevel.CRITICAL
        if has_corroboration and level == LongitudinalRiskLevel.SUSPICIOUS:
            level = LongitudinalRiskLevel.HIGH
        reasons.append(
            RiskReason(
                "CURRENT_ACTIONABLE_SENSITIVE_ACT",
                _act_detail(item.act, has_corroboration, has_manipulation),
                level,
                act_fingerprint=item.act.fingerprint,
                turn_number=item.occurrence.last_seen,
            )
        )
    if not active and _has_context_or_claim_only(state):
        reasons.append(
            RiskReason(
                "CONTEXT_OR_IDENTITY_ONLY_NOT_AUTHENTICATION",
                "Context and identity claims are retained as evidence but do not authenticate or create critical risk.",
                LongitudinalRiskLevel.NORMAL,
                turn_number=state.turn_count,
            )
        )
    return tuple(reasons)


def _residual_reasons(
    risk_state: LongitudinalRiskState,
    active: Tuple[ActAggregate, ...],
    turn_number: int,
) -> Tuple[RiskReason, ...]:
    if active or risk_state.current_risk == LongitudinalRiskLevel.NORMAL:
        return ()
    remaining = max(risk_state.residual_decay_turns - 1, 0)
    if remaining <= 0:
        return (
            RiskReason(
                "RESIDUAL_RISK_DECAYED",
                "No current unresolved dangerous factor remains after the bounded residual window.",
                LongitudinalRiskLevel.NORMAL,
                turn_number=turn_number,
            ),
        )
    decayed_level = _decay_one_step(risk_state.current_risk)
    return (
        RiskReason(
            "BOUNDED_RESIDUAL_RISK",
            "Previously active risk remains unresolved for a bounded turn-relative window.",
            decayed_level,
            turn_number=turn_number,
        ),
    )


def _persistence_reasons(
    aggregates: Iterable[ActAggregate],
    active: Tuple[ActAggregate, ...],
    turn_number: int,
) -> Tuple[RiskReason, ...]:
    if active:
        return ()
    persistent = tuple(
        item
        for item in aggregates
        if item.act.scope == TemporalScope.CURRENT
        and item.act.asset is not None
        and item.act.destination in EXTERNAL_DESTINATIONS
        and item.occurrence.count > 1
        and item.last_retracted_at == turn_number
        and item.last_retracted_at >= item.occurrence.last_seen
    )
    if not persistent:
        return ()
    return tuple(
        RiskReason(
            "RETRACTED_PERSISTENT_DANGER_HISTORY",
            "Repeated equivalent dangerous evidence remains audit history after precise retraction.",
            LongitudinalRiskLevel.SUSPICIOUS,
            act_fingerprint=item.act.fingerprint,
            turn_number=turn_number,
        )
        for item in sorted(persistent, key=lambda item: item.act.fingerprint)
    )


def _contradiction_reasons(
    active: Tuple[ActAggregate, ...],
    aggregates: Iterable[ActAggregate],
) -> Tuple[RiskReason, ...]:
    active_semantics = {item.act.semantic_fingerprint for item in active}
    if not active_semantics:
        return ()
    has_related_negation = any(
        item.act.scope == TemporalScope.NEGATED
        and item.act.semantic_fingerprint in active_semantics
        for item in aggregates
    )
    if not has_related_negation:
        return ()
    return (
        RiskReason(
            "CONTRADICTORY_CURRENT_AND_NEGATED_EVIDENCE",
            "A matching negation exists, but unresolved current occurrences still remain.",
            LongitudinalRiskLevel.SUSPICIOUS,
        ),
    )


def _base_risk_for_act(act: BehavioralAct) -> LongitudinalRiskLevel:
    if act.asset in SECRET_OR_ACCOUNT_ASSETS | REMOTE_ACCESS_ASSETS:
        return LongitudinalRiskLevel.CRITICAL
    if act.asset in MONEY_ASSETS:
        return LongitudinalRiskLevel.HIGH
    return LongitudinalRiskLevel.SUSPICIOUS


def _has_current_manipulation(
    manipulations: Iterable[Any],
) -> bool:
    return any(
        item.evidence.scope == TemporalScope.CURRENT
        and item.evidence.manipulation in HIGH_SIGNAL_MANIPULATIONS
        for item in manipulations
    )


def _has_compatible_context_or_claim(state: ConversationState) -> bool:
    return any(
        item.evidence.scope in {TemporalScope.CURRENT, TemporalScope.ACCUMULATED_CONTEXT}
        for item in state.contexts + state.identity_claims
    )


def _has_context_or_claim_only(state: ConversationState) -> bool:
    return bool(state.contexts or state.identity_claims)


def _max_reason_level(reasons: Tuple[RiskReason, ...]) -> LongitudinalRiskLevel:
    if not reasons:
        return LongitudinalRiskLevel.NORMAL
    return RISK_FROM_RANK[max(RISK_RANK[item.level] for item in reasons)]


def _max_level(
    first: LongitudinalRiskLevel, second: LongitudinalRiskLevel
) -> LongitudinalRiskLevel:
    return RISK_FROM_RANK[max(RISK_RANK[first], RISK_RANK[second])]


def _decay_one_step(level: LongitudinalRiskLevel) -> LongitudinalRiskLevel:
    return RISK_FROM_RANK[max(RISK_RANK[level] - 1, 0)]


def _act_detail(
    act: BehavioralAct, has_corroboration: bool, has_manipulation: bool
) -> str:
    parts = [
        f"{act.scope.value} {act.action.value}",
        f"asset={act.asset.value if act.asset else 'NONE'}",
        f"destination={act.destination.value}",
    ]
    if has_corroboration:
        parts.append("compatible_context_or_identity_present")
    if has_manipulation:
        parts.append("manipulation_amplifier_present")
    return "; ".join(parts)
