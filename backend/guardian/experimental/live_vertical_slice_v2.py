"""Experimental live V2 extraction to M2 longitudinal session orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol, Tuple

from guardian.longitudinal.evidence import NormalizedTurnEvidence, canonical_json
from guardian.longitudinal.session import (
    LongitudinalSessionState,
    LongitudinalTurnResult,
    process_normalized_turn,
)

from .extractor_v2 import GeminiV2Observation, V2ExtractionError
from .signals_v2 import ScamSignalsV2
from .v2_turn_adapter import UnsupportedV2MappingError, adapt_v2_turn


class V2VerticalSliceStatus(str, Enum):
    PROCESSED = "PROCESSED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    UNSUPPORTED_MAPPING = "UNSUPPORTED_MAPPING"


class V2Extractor(Protocol):
    def extract(self, text: str) -> GeminiV2Observation:
        """Return a sanitized V2 observation for one text turn."""


@dataclass(frozen=True)
class V2VerticalSliceTurn:
    session_id: str
    turn_id: str
    turn_number: int
    status: V2VerticalSliceStatus
    extracted_v2_summary: Optional[Dict[str, Any]]
    normalized_m2_summary: Optional[Dict[str, Any]]
    current_risk: Optional[str]
    peak_risk: Optional[str]
    policy_event: Optional[Dict[str, Any]]
    canary_authorization: Optional[Dict[str, Any]]
    extractor_error: Optional[Dict[str, Any]] = None
    mapping_error: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "turn_number": self.turn_number,
            "status": self.status.value,
            "extracted_v2_summary": self.extracted_v2_summary,
            "normalized_m2_summary": self.normalized_m2_summary,
            "current_risk": self.current_risk,
            "peak_risk": self.peak_risk,
            "policy_event": self.policy_event,
            "canary_authorization": self.canary_authorization,
            "extractor_error": self.extractor_error,
            "mapping_error": self.mapping_error,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class V2VerticalSliceState:
    session: LongitudinalSessionState
    turns: Tuple[V2VerticalSliceTurn, ...] = ()

    @classmethod
    def initial(cls, session_id: str) -> "V2VerticalSliceState":
        return cls(session=LongitudinalSessionState.initial(session_id))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session": self.session.to_dict(),
            "turns": [item.to_dict() for item in self.turns],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def process_text_turn(
    state: V2VerticalSliceState,
    *,
    extractor: V2Extractor,
    text: str,
    turn_id: str,
    turn_number: int,
) -> V2VerticalSliceState:
    """Extract one text turn, adapt it to M2 evidence, and process M2.3 policy."""
    try:
        observation = extractor.extract(text)
    except V2ExtractionError as error:
        turn = V2VerticalSliceTurn(
            session_id=state.session.session_id,
            turn_id=turn_id,
            turn_number=turn_number,
            status=V2VerticalSliceStatus.EXTRACTION_FAILED,
            extracted_v2_summary=None,
            normalized_m2_summary=None,
            current_risk=state.session.risk_state.current_risk.value,
            peak_risk=state.session.risk_state.peak_risk.value,
            policy_event=None,
            canary_authorization=None,
            extractor_error=error.to_dict(),
        )
        return _append_turn(state, turn)

    extracted = summarize_observation(observation)
    try:
        evidence = adapt_v2_turn(
            session_id=state.session.session_id,
            turn_id=turn_id,
            ordinal=turn_number,
            signals=observation.signals,
        )
    except UnsupportedV2MappingError as error:
        turn = V2VerticalSliceTurn(
            session_id=state.session.session_id,
            turn_id=turn_id,
            turn_number=turn_number,
            status=V2VerticalSliceStatus.UNSUPPORTED_MAPPING,
            extracted_v2_summary=extracted,
            normalized_m2_summary=None,
            current_risk=state.session.risk_state.current_risk.value,
            peak_risk=state.session.risk_state.peak_risk.value,
            policy_event=None,
            canary_authorization=None,
            mapping_error={
                "type": type(error).__name__,
                "message": str(error),
            },
        )
        return _append_turn(state, turn)

    result = process_normalized_turn(state.session, evidence)
    turn = V2VerticalSliceTurn(
        session_id=state.session.session_id,
        turn_id=turn_id,
        turn_number=turn_number,
        status=V2VerticalSliceStatus.PROCESSED,
        extracted_v2_summary=extracted,
        normalized_m2_summary=summarize_evidence(evidence),
        current_risk=result.canary_authorization.risk_level.value,
        peak_risk=result.policy_event.peak_risk.value,
        policy_event=summarize_policy_event(result),
        canary_authorization=result.canary_authorization.to_dict(),
    )
    return V2VerticalSliceState(
        session=result.next_state,
        turns=state.turns + (turn,),
    )


def summarize_observation(observation: GeminiV2Observation) -> Dict[str, Any]:
    return {
        "provenance": observation.provenance_dict(),
        "signals": summarize_signals(observation.signals),
    }


def summarize_signals(signals: ScamSignalsV2) -> Dict[str, Any]:
    return {
        "identity_claims": sorted(
            item.value for item in signals.identity_pretext.claims
        ),
        "knowledge_categories": sorted(
            item.value for item in signals.identity_pretext.knowledge_categories
        ),
        "contexts": sorted(item.value for item in signals.contexts),
        "manipulation": sorted(item.value for item in signals.manipulation),
        "interaction_acts": [
            {
                "action": item.action.value,
                "asset": item.asset.to_dict() if item.asset else None,
                "semantic_direction": item.semantic_direction.value,
                "actor": item.actor.value,
                "destination": item.destination.value,
            }
            for item in signals.interaction_acts
        ],
    }


def summarize_evidence(evidence: NormalizedTurnEvidence) -> Dict[str, Any]:
    return {
        "turn_id": evidence.turn_id,
        "turn_number": evidence.turn_number,
        "evidence_fingerprint": evidence.evidence_fingerprint,
        "contexts": [item.to_dict() for item in sorted(evidence.contexts)],
        "identity_claims": [
            item.to_dict() for item in sorted(evidence.identity_claims)
        ],
        "manipulations": [
            item.to_dict() for item in sorted(evidence.manipulations)
        ],
        "acts": [item.to_dict() for item in evidence.acts],
    }


def summarize_policy_event(result: LongitudinalTurnResult) -> Dict[str, Any]:
    event = result.policy_event
    return {
        "event_type": event.event_type.value,
        "current_risk": event.current_risk.value,
        "peak_risk": event.peak_risk.value,
        "active_factor_count": len(event.active_factors),
        "new_factor_count": len(event.new_factors),
        "risk_increased": event.risk_increased,
        "duplicate_suppressed": event.duplicate_suppressed,
        "suppression_reason": event.suppression_reason.value,
        "reasons": list(event.reasons),
        "canary_action": event.canary_action,
        "canary_decision": event.canary_decision,
        "canary_reason": event.canary_reason,
    }


def _append_turn(
    state: V2VerticalSliceState,
    turn: V2VerticalSliceTurn,
) -> V2VerticalSliceState:
    return V2VerticalSliceState(
        session=state.session,
        turns=state.turns + (turn,),
    )
