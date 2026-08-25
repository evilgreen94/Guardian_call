"""Immutable bounded state and pure reduction for normalized turn evidence."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar

from .evidence import (
    BehavioralAct,
    ContextEvidence,
    IdentityClaimEvidence,
    ManipulationEvidence,
    NormalizedTurnEvidence,
    ProtectedAsset,
    TemporalScope,
    canonical_json,
)


RETRACTABLE_TARGET_SCOPES = frozenset({TemporalScope.CURRENT})


class ReplayStatus(str, Enum):
    APPLIED = "APPLIED"
    EXACT_REPLAY = "EXACT_REPLAY"


class TurnConflictError(ValueError):
    """Raised when a turn identity or ordinal conflicts with accepted evidence."""


@dataclass(frozen=True)
class StateLimits:
    processed_turns: int = 32
    act_ledger: int = 64
    occurrence_count: int = 255

    def __post_init__(self) -> None:
        for name, value in (
            ("processed_turns", self.processed_turns),
            ("act_ledger", self.act_ledger),
            ("occurrence_count", self.occurrence_count),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if value < 1:
                raise ValueError(f"{name} must be positive")

    def to_dict(self) -> Dict[str, int]:
        return {
            "processed_turns": self.processed_turns,
            "act_ledger": self.act_ledger,
            "occurrence_count": self.occurrence_count,
        }


@dataclass(frozen=True)
class ProcessedTurn:
    turn_id: str
    turn_number: int
    evidence_fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "turn_number": self.turn_number,
            "evidence_fingerprint": self.evidence_fingerprint,
        }


@dataclass(frozen=True)
class Occurrence:
    first_seen: int
    last_seen: int
    count: int = 1
    count_saturated: bool = False

    def observe(self, turn_number: int, maximum: int) -> "Occurrence":
        return Occurrence(
            first_seen=self.first_seen,
            last_seen=turn_number,
            count=min(self.count + 1, maximum),
            count_saturated=self.count_saturated or self.count >= maximum,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "count": self.count,
            "count_saturated": self.count_saturated,
        }


EvidenceType = TypeVar("EvidenceType")


@dataclass(frozen=True)
class EvidenceAggregate(Generic[EvidenceType]):
    evidence: EvidenceType
    occurrence: Occurrence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence": self.evidence.to_dict(),  # type: ignore[union-attr]
            "occurrence": self.occurrence.to_dict(),
        }


@dataclass(frozen=True)
class ActAggregate:
    act: BehavioralAct
    occurrence: Occurrence
    retraction_count: int = 0
    last_retracted_at: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "act": self.act.to_dict(),
            "fingerprint": self.act.fingerprint,
            "semantic_fingerprint": self.act.semantic_fingerprint,
            "occurrence": self.occurrence.to_dict(),
            "retraction_count": self.retraction_count,
            "last_retracted_at": self.last_retracted_at,
        }


@dataclass(frozen=True)
class RetractionRelationship:
    target_act_fingerprint: str
    negated_act_fingerprint: str
    turn_number: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_act_fingerprint": self.target_act_fingerprint,
            "negated_act_fingerprint": self.negated_act_fingerprint,
            "turn_number": self.turn_number,
        }


@dataclass(frozen=True)
class ConversationState:
    session_id: str
    limits: StateLimits = field(default_factory=StateLimits)
    revision: int = 0
    turn_count: int = 0
    processed_turns: Tuple[ProcessedTurn, ...] = ()
    contexts: Tuple[EvidenceAggregate[ContextEvidence], ...] = ()
    identity_claims: Tuple[EvidenceAggregate[IdentityClaimEvidence], ...] = ()
    manipulations: Tuple[EvidenceAggregate[ManipulationEvidence], ...] = ()
    acts: Tuple[ActAggregate, ...] = ()
    compacted_acts: Tuple[ActAggregate, ...] = ()

    def __post_init__(self) -> None:
        # Session IDs share the same privacy-safe syntax as turn IDs.
        NormalizedTurnEvidence(turn_id=self.session_id, turn_number=1)

    @classmethod
    def initial(
        cls, session_id: str, limits: Optional[StateLimits] = None
    ) -> "ConversationState":
        return cls(session_id=session_id, limits=limits or StateLimits())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "limits": self.limits.to_dict(),
            "revision": self.revision,
            "turn_count": self.turn_count,
            "processed_turns": [item.to_dict() for item in self.processed_turns],
            "contexts": [item.to_dict() for item in self.contexts],
            "identity_claims": [item.to_dict() for item in self.identity_claims],
            "manipulations": [item.to_dict() for item in self.manipulations],
            "acts": [item.to_dict() for item in self.acts],
            "compacted_acts": [item.to_dict() for item in self.compacted_acts],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True)
class StateTransition:
    status: ReplayStatus
    previous_revision: int
    next_state: ConversationState
    turn_id: str
    turn_number: int
    added_contexts: Tuple[str, ...] = ()
    added_identity_claims: Tuple[str, ...] = ()
    added_manipulations: Tuple[str, ...] = ()
    added_acts: Tuple[str, ...] = ()
    retractions: Tuple[RetractionRelationship, ...] = ()
    evicted_turn_ids: Tuple[str, ...] = ()
    evicted_act_fingerprints: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "previous_revision": self.previous_revision,
            "turn_id": self.turn_id,
            "turn_number": self.turn_number,
            "added_contexts": list(self.added_contexts),
            "added_identity_claims": list(self.added_identity_claims),
            "added_manipulations": list(self.added_manipulations),
            "added_acts": list(self.added_acts),
            "retractions": [item.to_dict() for item in self.retractions],
            "evicted_turn_ids": list(self.evicted_turn_ids),
            "evicted_act_fingerprints": list(self.evicted_act_fingerprints),
            "next_state": self.next_state.to_dict(),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


def apply_turn(
    state: ConversationState, evidence: NormalizedTurnEvidence
) -> StateTransition:
    """Apply one normalized turn without I/O, extraction, risk, or policy work."""
    replay = next(
        (item for item in state.processed_turns if item.turn_id == evidence.turn_id),
        None,
    )
    if replay:
        if (
            replay.turn_number == evidence.turn_number
            and replay.evidence_fingerprint == evidence.evidence_fingerprint
        ):
            return StateTransition(
                status=ReplayStatus.EXACT_REPLAY,
                previous_revision=state.revision,
                next_state=state,
                turn_id=evidence.turn_id,
                turn_number=evidence.turn_number,
            )
        raise TurnConflictError(
            f"turn_id {evidence.turn_id!r} conflicts with accepted evidence"
        )

    expected_number = state.turn_count + 1
    if evidence.turn_number != expected_number:
        if evidence.turn_number <= state.turn_count:
            raise TurnConflictError(
                "turn is outside the bounded replay window or conflicts with an "
                "accepted ordinal"
            )
        raise TurnConflictError(
            f"turn_number must be {expected_number}, got {evidence.turn_number}"
        )

    contexts, new_contexts = _merge_evidence(
        state.contexts, evidence.contexts, evidence.turn_number, state.limits
    )
    claims, new_claims = _merge_evidence(
        state.identity_claims,
        evidence.identity_claims,
        evidence.turn_number,
        state.limits,
    )
    manipulations, new_manipulations = _merge_evidence(
        state.manipulations,
        evidence.manipulations,
        evidence.turn_number,
        state.limits,
    )
    acts, compacted_acts, new_acts, retractions = _merge_acts(
        state.acts,
        state.compacted_acts,
        evidence.acts,
        evidence.turn_number,
        state.limits,
    )
    acts, compacted_acts, evicted_acts = _compact_acts(
        acts, compacted_acts, state.limits
    )

    accepted = ProcessedTurn(
        evidence.turn_id, evidence.turn_number, evidence.evidence_fingerprint
    )
    all_processed = state.processed_turns + (accepted,)
    evicted_turns = all_processed[: -state.limits.processed_turns]
    processed = all_processed[-state.limits.processed_turns :]
    next_state = ConversationState(
        session_id=state.session_id,
        limits=state.limits,
        revision=state.revision + 1,
        turn_count=evidence.turn_number,
        processed_turns=processed,
        contexts=contexts,
        identity_claims=claims,
        manipulations=manipulations,
        acts=acts,
        compacted_acts=compacted_acts,
    )
    return StateTransition(
        status=ReplayStatus.APPLIED,
        previous_revision=state.revision,
        next_state=next_state,
        turn_id=evidence.turn_id,
        turn_number=evidence.turn_number,
        added_contexts=new_contexts,
        added_identity_claims=new_claims,
        added_manipulations=new_manipulations,
        added_acts=new_acts,
        retractions=retractions,
        evicted_turn_ids=tuple(item.turn_id for item in evicted_turns),
        evicted_act_fingerprints=evicted_acts,
    )


def _merge_evidence(
    existing: Tuple[EvidenceAggregate[Any], ...],
    incoming: frozenset,
    turn_number: int,
    limits: StateLimits,
) -> Tuple[Tuple[EvidenceAggregate[Any], ...], Tuple[str, ...]]:
    merged = {canonical_json(item.evidence.to_dict()): item for item in existing}
    added = []
    for item in sorted(incoming):
        key = canonical_json(item.to_dict())
        current = merged.get(key)
        if current:
            merged[key] = replace(
                current,
                occurrence=current.occurrence.observe(
                    turn_number, limits.occurrence_count
                ),
            )
        else:
            merged[key] = EvidenceAggregate(item, Occurrence(turn_number, turn_number))
            added.append(key)
    return tuple(merged[key] for key in sorted(merged)), tuple(sorted(added))


def _merge_acts(
    existing: Tuple[ActAggregate, ...],
    existing_compacted: Tuple[ActAggregate, ...],
    incoming: Tuple[BehavioralAct, ...],
    turn_number: int,
    limits: StateLimits,
) -> Tuple[
    Tuple[ActAggregate, ...],
    Tuple[ActAggregate, ...],
    Tuple[str, ...],
    Tuple[RetractionRelationship, ...],
]:
    merged = {item.act.fingerprint: item for item in existing}
    compacted = {item.act.fingerprint: item for item in existing_compacted}
    added = []
    for act in sorted(incoming, key=lambda item: item.fingerprint):
        current = merged.get(act.fingerprint)
        if current:
            merged[act.fingerprint] = replace(
                current,
                occurrence=current.occurrence.observe(
                    turn_number, limits.occurrence_count
                ),
            )
        elif act.fingerprint in compacted:
            current = compacted[act.fingerprint]
            compacted[act.fingerprint] = replace(
                current,
                occurrence=current.occurrence.observe(
                    turn_number, limits.occurrence_count
                ),
            )
        else:
            merged[act.fingerprint] = ActAggregate(
                act, Occurrence(turn_number, turn_number)
            )
            added.append(act.fingerprint)

    relationships = []
    for negated in sorted(
        (item for item in incoming if item.scope == TemporalScope.NEGATED),
        key=lambda item: item.fingerprint,
    ):
        for ledger in (merged, compacted):
            for fingerprint, aggregate in tuple(ledger.items()):
                if aggregate.act.scope not in RETRACTABLE_TARGET_SCOPES:
                    continue
                if aggregate.act.semantic_fingerprint != negated.semantic_fingerprint:
                    continue
                ledger[fingerprint] = replace(
                    aggregate,
                    retraction_count=min(
                        aggregate.retraction_count + 1, limits.occurrence_count
                    ),
                    last_retracted_at=turn_number,
                )
                relationships.append(
                    RetractionRelationship(
                        target_act_fingerprint=fingerprint,
                        negated_act_fingerprint=negated.fingerprint,
                        turn_number=turn_number,
                    )
                )
    ordered = tuple(merged[key] for key in sorted(merged))
    ordered_compacted = tuple(compacted[key] for key in sorted(compacted))
    return (
        ordered,
        ordered_compacted,
        tuple(sorted(added)),
        tuple(relationships),
    )


def _compact_acts(
    acts: Tuple[ActAggregate, ...],
    compacted_acts: Tuple[ActAggregate, ...],
    limits: StateLimits,
) -> Tuple[
    Tuple[ActAggregate, ...], Tuple[ActAggregate, ...], Tuple[str, ...]
]:
    if len(acts) <= limits.act_ledger:
        return acts, compacted_acts, ()
    eviction_count = len(acts) - limits.act_ledger
    eviction_order = sorted(
        acts,
        key=lambda item: (
            item.occurrence.last_seen,
            item.occurrence.first_seen,
            item.act.fingerprint,
        ),
    )
    evicted = tuple(eviction_order[:eviction_count])
    evicted_fingerprints = {item.act.fingerprint for item in evicted}
    compacted = {item.act.fingerprint: item for item in compacted_acts}
    for item in evicted:
        previous = compacted.get(item.act.fingerprint)
        if previous is None:
            compacted[item.act.fingerprint] = item
            continue
        compacted[item.act.fingerprint] = _combine_act_aggregates(
            previous, item, limits.occurrence_count
        )
    retained = tuple(
        item for item in acts if item.act.fingerprint not in evicted_fingerprints
    )
    return (
        retained,
        tuple(compacted[key] for key in sorted(compacted)),
        tuple(item.act.fingerprint for item in evicted),
    )


def _combine_act_aggregates(
    first: ActAggregate, second: ActAggregate, maximum: int
) -> ActAggregate:
    if first.act != second.act:
        raise ValueError("cannot combine different semantic acts")
    combined_count = first.occurrence.count + second.occurrence.count
    combined_retractions = first.retraction_count + second.retraction_count
    return ActAggregate(
        act=first.act,
        occurrence=Occurrence(
            first_seen=min(first.occurrence.first_seen, second.occurrence.first_seen),
            last_seen=max(first.occurrence.last_seen, second.occurrence.last_seen),
            count=min(combined_count, maximum),
            count_saturated=(
                first.occurrence.count_saturated
                or second.occurrence.count_saturated
                or combined_count > maximum
            ),
        ),
        retraction_count=min(combined_retractions, maximum),
        last_retracted_at=max(
            value
            for value in (first.last_retracted_at, second.last_retracted_at)
            if value is not None
        )
        if first.last_retracted_at is not None or second.last_retracted_at is not None
        else None,
    )
