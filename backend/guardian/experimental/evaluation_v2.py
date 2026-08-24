"""Pure, offline comparison infrastructure for experimental ScamSignalsV2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .signals_v2 import (
    Actor,
    AssetCategory,
    Destination,
    IdentityAssuranceContext,
    InteractionAct,
    ScamSignalsV2,
    SemanticDirection,
)


class DifferenceType(str, Enum):
    MISSING_VALUE = "MISSING_VALUE"
    SPURIOUS_VALUE = "SPURIOUS_VALUE"
    VALUE_MISMATCH = "VALUE_MISMATCH"
    MISSING_ACT = "MISSING_ACT"
    SPURIOUS_ACT = "SPURIOUS_ACT"
    ACTION_MISMATCH = "ACTION_MISMATCH"
    ASSET_CATEGORY_MISMATCH = "ASSET_CATEGORY_MISMATCH"
    ASSET_SUBTYPE_MISMATCH = "ASSET_SUBTYPE_MISMATCH"
    SEMANTIC_DIRECTION_MISMATCH = "SEMANTIC_DIRECTION_MISMATCH"
    ACTOR_MISMATCH = "ACTOR_MISMATCH"
    DESTINATION_MISMATCH = "DESTINATION_MISMATCH"
    IDENTITY_CLAIM_MISS = "IDENTITY_CLAIM_MISS"
    IDENTITY_CLAIM_SPURIOUS = "IDENTITY_CLAIM_SPURIOUS"
    KNOWLEDGE_CATEGORY_MISS = "KNOWLEDGE_CATEGORY_MISS"
    KNOWLEDGE_CATEGORY_SPURIOUS = "KNOWLEDGE_CATEGORY_SPURIOUS"
    CONTEXT_MISS = "CONTEXT_MISS"
    CONTEXT_SPURIOUS = "CONTEXT_SPURIOUS"
    MANIPULATION_MISS = "MANIPULATION_MISS"
    MANIPULATION_SPURIOUS = "MANIPULATION_SPURIOUS"


class ExtractionImpact(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


IMPACT_RANK: Mapping[ExtractionImpact, int] = {
    ExtractionImpact.INFO: 0,
    ExtractionImpact.LOW: 1,
    ExtractionImpact.MEDIUM: 2,
    ExtractionImpact.HIGH: 3,
    ExtractionImpact.CRITICAL: 4,
}

ACTIVE_REQUEST_DIRECTIONS = frozenset(
    {
        SemanticDirection.DIRECT_REQUEST,
        SemanticDirection.INDIRECT_REQUEST,
        SemanticDirection.PARTIAL_REQUEST,
    }
)

REFERENCE_OR_CONTROL_DIRECTIONS = frozenset(
    {
        SemanticDirection.WARNING,
        SemanticDirection.NEGATION,
        SemanticDirection.SELF_SERVICE,
        SemanticDirection.DISCUSSION,
        SemanticDirection.HYPOTHETICAL,
        SemanticDirection.HISTORICAL,
        SemanticDirection.THIRD_PARTY,
        SemanticDirection.QUESTION,
    }
)

EXTERNAL_DESTINATIONS = frozenset(
    {Destination.CALLER, Destination.THIRD_PARTY, Destination.EXTERNAL_ACCOUNT}
)
CONTROL_PRESERVING_DESTINATIONS = frozenset(
    {Destination.OFFICIAL_SELF_SERVICE, Destination.USER_CONTROLLED}
)


@dataclass(frozen=True)
class FieldDifference:
    difference_type: DifferenceType
    dimension: str
    path: str
    expected: Any
    observed: Any
    impact: ExtractionImpact

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.difference_type.value,
            "dimension": self.dimension,
            "path": self.path,
            "expected": self.expected,
            "observed": self.observed,
            "impact": self.impact.value,
        }


@dataclass(frozen=True)
class SetComparison:
    dimension: str
    expected: Tuple[str, ...]
    observed: Tuple[str, ...]
    true_positives: Tuple[str, ...]
    false_positives: Tuple[str, ...]
    false_negatives: Tuple[str, ...]
    differences: Tuple[FieldDifference, ...]

    @property
    def exact(self) -> bool:
        return not self.false_positives and not self.false_negatives

    def to_dict(self) -> Dict[str, Any]:
        precision_denominator = len(self.true_positives) + len(self.false_positives)
        recall_denominator = len(self.true_positives) + len(self.false_negatives)
        precision = (
            len(self.true_positives) / precision_denominator
            if precision_denominator
            else None
        )
        recall = (
            len(self.true_positives) / recall_denominator
            if recall_denominator
            else None
        )
        f1_denominator = (
            2 * len(self.true_positives)
            + len(self.false_positives)
            + len(self.false_negatives)
        )
        f1 = (
            2 * len(self.true_positives) / f1_denominator
            if f1_denominator
            else None
        )
        return {
            "dimension": self.dimension,
            "expected": list(self.expected),
            "observed": list(self.observed),
            "true_positives": list(self.true_positives),
            "false_positives": list(self.false_positives),
            "false_negatives": list(self.false_negatives),
            "counts": {
                "expected": len(self.expected),
                "observed": len(self.observed),
                "true_positives": len(self.true_positives),
                "false_positives": len(self.false_positives),
                "false_negatives": len(self.false_negatives),
            },
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "exact": self.exact,
            "differences": [item.to_dict() for item in self.differences],
        }


@dataclass(frozen=True)
class ActComparison:
    expected: Optional[InteractionAct]
    observed: Optional[InteractionAct]
    differences: Tuple[FieldDifference, ...]

    @property
    def status(self) -> str:
        if self.expected is None:
            return "SPURIOUS_ACT"
        if self.observed is None:
            return "MISSING_ACT"
        if not self.differences:
            return "EXACT_MATCH"
        return "PARTIAL_MATCH"

    @property
    def exact(self) -> bool:
        return self.status == "EXACT_MATCH"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "expected": self.expected.to_dict() if self.expected else None,
            "observed": self.observed.to_dict() if self.observed else None,
            "differences": [item.to_dict() for item in self.differences],
        }


@dataclass(frozen=True)
class AssuranceComparison:
    expected: Optional[str]
    observed: Optional[str]
    differences: Tuple[FieldDifference, ...]

    @property
    def exact(self) -> bool:
        return not self.differences

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected": self.expected,
            "observed": self.observed,
            "exact": self.exact,
            "differences": [item.to_dict() for item in self.differences],
        }


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario_id: str
    status: str
    structural_exact: bool
    ambiguous_reference: bool
    excluded_from_strict_accuracy: bool
    set_comparisons: Tuple[SetComparison, ...]
    act_comparisons: Tuple[ActComparison, ...]
    assurance_comparison: Optional[AssuranceComparison]
    differences: Tuple[FieldDifference, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "status": self.status,
            "structural_exact": self.structural_exact,
            "ambiguous_reference": self.ambiguous_reference,
            "excluded_from_strict_accuracy": self.excluded_from_strict_accuracy,
            "set_comparisons": {
                item.dimension: item.to_dict() for item in self.set_comparisons
            },
            "act_comparisons": [item.to_dict() for item in self.act_comparisons],
            "assurance_comparison": (
                self.assurance_comparison.to_dict()
                if self.assurance_comparison
                else None
            ),
            "differences": [item.to_dict() for item in self.differences],
            "difference_counts": {
                "total": len(self.differences),
                "critical": _count_impact(self.differences, ExtractionImpact.CRITICAL),
                "high": _count_impact(self.differences, ExtractionImpact.HIGH),
            },
        }


@dataclass(frozen=True)
class BenchmarkSummary:
    evaluations: Tuple[ScenarioEvaluation, ...]
    constitutional_memberships: Mapping[str, Tuple[str, ...]]

    def to_dict(self) -> Dict[str, Any]:
        strict = [
            item
            for item in self.evaluations
            if not item.excluded_from_strict_accuracy
        ]
        all_differences = [
            difference
            for evaluation in self.evaluations
            for difference in evaluation.differences
        ]
        return {
            "global": {
                "scenarios_evaluated": len(self.evaluations),
                "strict_scenarios": len(strict),
                "ambiguous_references": sum(
                    item.ambiguous_reference for item in self.evaluations
                ),
                "exact_scenario_matches": sum(
                    item.structural_exact for item in strict
                ),
                "scenarios_with_any_mismatch": sum(
                    not item.structural_exact for item in strict
                ),
                "total_differences": len(all_differences),
                "critical_differences": _count_impact(
                    all_differences, ExtractionImpact.CRITICAL
                ),
                "high_differences": _count_impact(
                    all_differences, ExtractionImpact.HIGH
                ),
            },
            "by_dimension": _summarize_dimensions(self.evaluations),
            "interaction_acts": _summarize_acts(self.evaluations),
            "semantic_direction": _summarize_directions(self.evaluations),
            "constitutional": _summarize_constitutional(
                self.evaluations, self.constitutional_memberships
            ),
        }


def compare_signals(
    scenario_id: str,
    expected: ScamSignalsV2,
    observed: ScamSignalsV2,
    *,
    ambiguity: Optional[Mapping[str, Any]] = None,
    expected_assurance: Optional[IdentityAssuranceContext] = None,
    observed_assurance: Optional[IdentityAssuranceContext] = None,
) -> ScenarioEvaluation:
    """Compare expected and observed semantic extraction without risk evaluation."""
    set_comparisons = (
        _compare_set(
            "identity",
            expected.identity_pretext.claims,
            observed.identity_pretext.claims,
            DifferenceType.IDENTITY_CLAIM_MISS,
            DifferenceType.IDENTITY_CLAIM_SPURIOUS,
            ExtractionImpact.LOW,
        ),
        _compare_set(
            "knowledge",
            expected.identity_pretext.knowledge_categories,
            observed.identity_pretext.knowledge_categories,
            DifferenceType.KNOWLEDGE_CATEGORY_MISS,
            DifferenceType.KNOWLEDGE_CATEGORY_SPURIOUS,
            ExtractionImpact.LOW,
        ),
        _compare_set(
            "contexts",
            expected.contexts,
            observed.contexts,
            DifferenceType.CONTEXT_MISS,
            DifferenceType.CONTEXT_SPURIOUS,
            ExtractionImpact.LOW,
        ),
        _compare_set(
            "manipulation",
            expected.manipulation,
            observed.manipulation,
            DifferenceType.MANIPULATION_MISS,
            DifferenceType.MANIPULATION_SPURIOUS,
            ExtractionImpact.MEDIUM,
        ),
    )
    act_comparisons = match_interaction_acts(
        expected.interaction_acts, observed.interaction_acts
    )
    assurance = _compare_assurance(expected_assurance, observed_assurance)
    differences = tuple(
        difference
        for comparison in set_comparisons
        for difference in comparison.differences
    ) + tuple(
        difference
        for comparison in act_comparisons
        for difference in comparison.differences
    )
    ambiguous_reference = bool(ambiguity and ambiguity.get("present"))
    structural_exact = not differences
    status = (
        "AMBIGUOUS_REFERENCE"
        if ambiguous_reference
        else "EXACT_MATCH" if structural_exact else "MISMATCH"
    )
    return ScenarioEvaluation(
        scenario_id=scenario_id,
        status=status,
        structural_exact=structural_exact,
        ambiguous_reference=ambiguous_reference,
        excluded_from_strict_accuracy=ambiguous_reference,
        set_comparisons=set_comparisons,
        act_comparisons=act_comparisons,
        assurance_comparison=assurance,
        differences=differences,
    )


def match_interaction_acts(
    expected: Sequence[InteractionAct], observed: Sequence[InteractionAct]
) -> Tuple[ActComparison, ...]:
    """Pair acts exact-first, then by stable greedy Hamming distance."""
    expected_remaining = sorted(expected, key=_act_key)
    observed_remaining = sorted(observed, key=_act_key)
    exact: list[ActComparison] = []

    for expected_act in tuple(expected_remaining):
        try:
            observed_index = observed_remaining.index(expected_act)
        except ValueError:
            continue
        expected_remaining.remove(expected_act)
        observed_act = observed_remaining.pop(observed_index)
        exact.append(ActComparison(expected_act, observed_act, ()))

    candidates = sorted(
        (
            _act_distance(expected_act, observed_act),
            _act_key(expected_act),
            _act_key(observed_act),
            expected_index,
            observed_index,
        )
        for expected_index, expected_act in enumerate(expected_remaining)
        for observed_index, observed_act in enumerate(observed_remaining)
    )
    paired_expected: set[int] = set()
    paired_observed: set[int] = set()
    partial: list[ActComparison] = []
    for _, _, _, expected_index, observed_index in candidates:
        if expected_index in paired_expected or observed_index in paired_observed:
            continue
        expected_act = expected_remaining[expected_index]
        observed_act = observed_remaining[observed_index]
        paired_expected.add(expected_index)
        paired_observed.add(observed_index)
        partial.append(
            ActComparison(
                expected_act,
                observed_act,
                _compare_act_fields(expected_act, observed_act),
            )
        )

    missing = [
        ActComparison(
            expected_act,
            None,
            (
                FieldDifference(
                    DifferenceType.MISSING_ACT,
                    "interaction_actions",
                    "interaction_acts",
                    expected_act.to_dict(),
                    None,
                    _missing_or_spurious_act_impact(expected_act),
                ),
            ),
        )
        for index, expected_act in enumerate(expected_remaining)
        if index not in paired_expected
    ]
    spurious = [
        ActComparison(
            None,
            observed_act,
            (
                FieldDifference(
                    DifferenceType.SPURIOUS_ACT,
                    "interaction_actions",
                    "interaction_acts",
                    None,
                    observed_act.to_dict(),
                    _missing_or_spurious_act_impact(observed_act),
                ),
            ),
        )
        for index, observed_act in enumerate(observed_remaining)
        if index not in paired_observed
    ]
    return tuple(
        sorted(exact, key=_comparison_key)
        + sorted(partial, key=_comparison_key)
        + missing
        + spurious
    )


def summarize_benchmark(
    evaluations: Iterable[ScenarioEvaluation],
    constitutional_memberships: Optional[Mapping[str, Iterable[str]]] = None,
) -> BenchmarkSummary:
    memberships = {
        key: tuple(sorted(values))
        for key, values in (constitutional_memberships or {}).items()
    }
    return BenchmarkSummary(tuple(evaluations), memberships)


def _compare_set(
    dimension: str,
    expected: Iterable[Enum],
    observed: Iterable[Enum],
    missing_type: DifferenceType,
    spurious_type: DifferenceType,
    impact: ExtractionImpact,
) -> SetComparison:
    expected_values = {item.value for item in expected}
    observed_values = {item.value for item in observed}
    true_positives = tuple(sorted(expected_values & observed_values))
    false_positives = tuple(sorted(observed_values - expected_values))
    false_negatives = tuple(sorted(expected_values - observed_values))
    differences = tuple(
        FieldDifference(
            missing_type,
            dimension,
            dimension,
            value,
            None,
            impact,
        )
        for value in false_negatives
    ) + tuple(
        FieldDifference(
            spurious_type,
            dimension,
            dimension,
            None,
            value,
            impact,
        )
        for value in false_positives
    )
    return SetComparison(
        dimension,
        tuple(sorted(expected_values)),
        tuple(sorted(observed_values)),
        true_positives,
        false_positives,
        false_negatives,
        differences,
    )


def _compare_act_fields(
    expected: InteractionAct, observed: InteractionAct
) -> Tuple[FieldDifference, ...]:
    differences: list[FieldDifference] = []
    if expected.action != observed.action:
        differences.append(
            _act_field_difference(
                DifferenceType.ACTION_MISMATCH,
                "interaction_actions",
                "action",
                expected.action.value,
                observed.action.value,
                expected,
                observed,
            )
        )

    expected_category = expected.asset.category.value if expected.asset else None
    observed_category = observed.asset.category.value if observed.asset else None
    expected_subtype = expected.asset.subtype.value if expected.asset else None
    observed_subtype = observed.asset.subtype.value if observed.asset else None
    if (expected.asset is None) != (observed.asset is None):
        difference_type = (
            DifferenceType.MISSING_VALUE
            if expected.asset is not None
            else DifferenceType.SPURIOUS_VALUE
        )
        differences.append(
            _act_field_difference(
                difference_type,
                "assets",
                "asset",
                expected.asset.to_dict() if expected.asset else None,
                observed.asset.to_dict() if observed.asset else None,
                expected,
                observed,
            )
        )
    elif expected_category != observed_category:
        differences.append(
            _act_field_difference(
                DifferenceType.ASSET_CATEGORY_MISMATCH,
                "assets",
                "asset.category",
                expected_category,
                observed_category,
                expected,
                observed,
            )
        )
    if expected_subtype != observed_subtype and expected.asset and observed.asset:
        differences.append(
            _act_field_difference(
                DifferenceType.ASSET_SUBTYPE_MISMATCH,
                "assets",
                "asset.subtype",
                expected_subtype,
                observed_subtype,
                expected,
                observed,
            )
        )
    if expected.semantic_direction != observed.semantic_direction:
        differences.append(
            _act_field_difference(
                DifferenceType.SEMANTIC_DIRECTION_MISMATCH,
                "semantic_direction",
                "semantic_direction",
                expected.semantic_direction.value,
                observed.semantic_direction.value,
                expected,
                observed,
            )
        )
    if expected.actor != observed.actor:
        differences.append(
            _act_field_difference(
                DifferenceType.ACTOR_MISMATCH,
                "actors",
                "actor",
                expected.actor.value,
                observed.actor.value,
                expected,
                observed,
            )
        )
    if expected.destination != observed.destination:
        differences.append(
            _act_field_difference(
                DifferenceType.DESTINATION_MISMATCH,
                "destinations",
                "destination",
                expected.destination.value,
                observed.destination.value,
                expected,
                observed,
            )
        )
    return tuple(differences)


def _act_field_difference(
    difference_type: DifferenceType,
    dimension: str,
    path: str,
    expected_value: Any,
    observed_value: Any,
    expected_act: InteractionAct,
    observed_act: InteractionAct,
) -> FieldDifference:
    return FieldDifference(
        difference_type,
        dimension,
        f"interaction_acts[].{path}",
        expected_value,
        observed_value,
        classify_extraction_impact(difference_type, expected_act, observed_act),
    )


def classify_extraction_impact(
    difference_type: DifferenceType,
    expected_act: Optional[InteractionAct],
    observed_act: Optional[InteractionAct],
) -> ExtractionImpact:
    """Classify extraction-error impact independently from fraud risk policy."""
    if difference_type in {
        DifferenceType.IDENTITY_CLAIM_MISS,
        DifferenceType.IDENTITY_CLAIM_SPURIOUS,
        DifferenceType.KNOWLEDGE_CATEGORY_MISS,
        DifferenceType.KNOWLEDGE_CATEGORY_SPURIOUS,
        DifferenceType.CONTEXT_MISS,
        DifferenceType.CONTEXT_SPURIOUS,
    }:
        return ExtractionImpact.LOW
    if difference_type in {
        DifferenceType.MANIPULATION_MISS,
        DifferenceType.MANIPULATION_SPURIOUS,
    }:
        return ExtractionImpact.MEDIUM
    if difference_type in {DifferenceType.MISSING_ACT, DifferenceType.SPURIOUS_ACT}:
        act = expected_act or observed_act
        return _missing_or_spurious_act_impact(act) if act else ExtractionImpact.MEDIUM
    if difference_type == DifferenceType.SEMANTIC_DIRECTION_MISMATCH:
        if _is_direction_flip(expected_act, observed_act) and _has_asset(
            expected_act, observed_act
        ):
            return ExtractionImpact.CRITICAL
        return ExtractionImpact.HIGH
    if difference_type == DifferenceType.DESTINATION_MISMATCH:
        if _is_control_boundary_flip(expected_act, observed_act) and _has_asset(
            expected_act, observed_act
        ):
            return ExtractionImpact.CRITICAL
        return ExtractionImpact.HIGH
    if difference_type in {
        DifferenceType.ACTION_MISMATCH,
        DifferenceType.ASSET_CATEGORY_MISMATCH,
        DifferenceType.ASSET_SUBTYPE_MISMATCH,
        DifferenceType.ACTOR_MISMATCH,
        DifferenceType.MISSING_VALUE,
        DifferenceType.SPURIOUS_VALUE,
    }:
        return ExtractionImpact.HIGH
    return ExtractionImpact.INFO


def _missing_or_spurious_act_impact(act: InteractionAct) -> ExtractionImpact:
    if act.asset and act.semantic_direction in ACTIVE_REQUEST_DIRECTIONS:
        return ExtractionImpact.CRITICAL
    return ExtractionImpact.MEDIUM


def _is_direction_flip(
    expected: Optional[InteractionAct], observed: Optional[InteractionAct]
) -> bool:
    if not expected or not observed:
        return False
    directions = {expected.semantic_direction, observed.semantic_direction}
    return bool(
        directions & ACTIVE_REQUEST_DIRECTIONS
        and directions & REFERENCE_OR_CONTROL_DIRECTIONS
    )


def _is_control_boundary_flip(
    expected: Optional[InteractionAct], observed: Optional[InteractionAct]
) -> bool:
    if not expected or not observed:
        return False
    destinations = {expected.destination, observed.destination}
    return bool(
        destinations & EXTERNAL_DESTINATIONS
        and destinations & CONTROL_PRESERVING_DESTINATIONS
    )


def _has_asset(
    expected: Optional[InteractionAct], observed: Optional[InteractionAct]
) -> bool:
    return bool(
        (expected and expected.asset is not None)
        or (observed and observed.asset is not None)
    )


def _compare_assurance(
    expected: Optional[IdentityAssuranceContext],
    observed: Optional[IdentityAssuranceContext],
) -> Optional[AssuranceComparison]:
    if expected is None and observed is None:
        return None
    expected_value = expected.identity_assurance.value if expected else None
    observed_value = observed.identity_assurance.value if observed else None
    if expected_value == observed_value:
        differences: Tuple[FieldDifference, ...] = ()
    else:
        difference_type = (
            DifferenceType.MISSING_VALUE
            if expected is not None and observed is None
            else DifferenceType.SPURIOUS_VALUE
            if expected is None and observed is not None
            else DifferenceType.VALUE_MISMATCH
        )
        differences = (
            FieldDifference(
                difference_type,
                "identity_assurance",
                "identity_assurance",
                expected_value,
                observed_value,
                ExtractionImpact.INFO,
            ),
        )
    return AssuranceComparison(expected_value, observed_value, differences)


def _act_distance(expected: InteractionAct, observed: InteractionAct) -> int:
    return sum(
        expected_value != observed_value
        for expected_value, observed_value in zip(
            _act_key(expected), _act_key(observed)
        )
    )


def _act_key(act: InteractionAct) -> Tuple[str, ...]:
    return (
        act.action.value,
        act.asset.category.value if act.asset else "",
        act.asset.subtype.value if act.asset else "",
        act.semantic_direction.value,
        act.actor.value,
        act.destination.value,
    )


def _comparison_key(comparison: ActComparison) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    return (
        _act_key(comparison.expected) if comparison.expected else ("",) * 6,
        _act_key(comparison.observed) if comparison.observed else ("",) * 6,
    )


def _count_impact(
    differences: Iterable[FieldDifference], impact: ExtractionImpact
) -> int:
    return sum(item.impact == impact for item in differences)


def _summarize_dimensions(
    evaluations: Sequence[ScenarioEvaluation],
) -> Dict[str, Any]:
    set_dimensions = ("identity", "knowledge", "contexts", "manipulation")
    result: Dict[str, Any] = {}
    for dimension in set_dimensions:
        comparisons = [
            comparison
            for evaluation in evaluations
            for comparison in evaluation.set_comparisons
            if comparison.dimension == dimension
        ]
        tp = sum(len(item.true_positives) for item in comparisons)
        fp = sum(len(item.false_positives) for item in comparisons)
        fn = sum(len(item.false_negatives) for item in comparisons)
        result[dimension] = _metric_counts(tp, fp, fn)

    paired = [
        comparison
        for evaluation in evaluations
        for comparison in evaluation.act_comparisons
        if comparison.expected is not None and comparison.observed is not None
    ]
    field_dimensions = {
        "interaction_actions": DifferenceType.ACTION_MISMATCH,
        "semantic_direction": DifferenceType.SEMANTIC_DIRECTION_MISMATCH,
        "actors": DifferenceType.ACTOR_MISMATCH,
        "destinations": DifferenceType.DESTINATION_MISMATCH,
    }
    for dimension, difference_type in field_dimensions.items():
        mismatches = sum(
            any(item.difference_type == difference_type for item in comparison.differences)
            for comparison in paired
        )
        result[dimension] = {
            "exact": len(paired) - mismatches,
            "mismatch": mismatches,
            "compared": len(paired),
        }
    all_act_comparisons = [
        comparison
        for evaluation in evaluations
        for comparison in evaluation.act_comparisons
    ]
    result["interaction_actions"].update(
        {
            "missing_acts": sum(
                item.status == "MISSING_ACT" for item in all_act_comparisons
            ),
            "spurious_acts": sum(
                item.status == "SPURIOUS_ACT" for item in all_act_comparisons
            ),
        }
    )
    asset_mismatches = sum(
        any(item.dimension == "assets" for item in comparison.differences)
        for comparison in paired
    )
    result["assets"] = {
        "exact": len(paired) - asset_mismatches,
        "mismatch": asset_mismatches,
        "compared": len(paired),
    }
    return result


def _metric_counts(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision_denominator = tp + fp
    recall_denominator = tp + fn
    precision = tp / precision_denominator if precision_denominator else None
    recall = tp / recall_denominator if recall_denominator else None
    f1_denominator = 2 * tp + fp + fn
    f1 = 2 * tp / f1_denominator if f1_denominator else None
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision_denominator": precision_denominator,
        "recall_denominator": recall_denominator,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _summarize_acts(evaluations: Sequence[ScenarioEvaluation]) -> Dict[str, int]:
    comparisons = [
        comparison
        for evaluation in evaluations
        for comparison in evaluation.act_comparisons
    ]
    return {
        "exact_acts": sum(item.status == "EXACT_MATCH" for item in comparisons),
        "partially_matched_acts": sum(
            item.status == "PARTIAL_MATCH" for item in comparisons
        ),
        "missing_acts": sum(item.status == "MISSING_ACT" for item in comparisons),
        "spurious_acts": sum(item.status == "SPURIOUS_ACT" for item in comparisons),
    }


def _summarize_directions(
    evaluations: Sequence[ScenarioEvaluation],
) -> Dict[str, Any]:
    exact = 0
    mismatch = 0
    flips: Dict[str, int] = {}
    for evaluation in evaluations:
        for comparison in evaluation.act_comparisons:
            if comparison.expected is None or comparison.observed is None:
                continue
            expected = comparison.expected.semantic_direction.value
            observed = comparison.observed.semantic_direction.value
            if expected == observed:
                exact += 1
            else:
                mismatch += 1
                key = f"{expected} -> {observed}"
                flips[key] = flips.get(key, 0) + 1
    return {
        "exact": exact,
        "mismatch": mismatch,
        "compared": exact + mismatch,
        "direction_flips": dict(sorted(flips.items())),
    }


def _summarize_constitutional(
    evaluations: Sequence[ScenarioEvaluation],
    memberships: Mapping[str, Tuple[str, ...]],
) -> Dict[str, Any]:
    principles = sorted(
        {
            principle
            for scenario_principles in memberships.values()
            for principle in scenario_principles
        }
    )
    result: Dict[str, Any] = {}
    for principle in principles:
        members = [
            item
            for item in evaluations
            if principle in memberships.get(item.scenario_id, ())
        ]
        strict = [item for item in members if not item.excluded_from_strict_accuracy]
        differences = [item for member in members for item in member.differences]
        result[principle] = {
            "cases": len(members),
            "strict_cases": len(strict),
            "exact": sum(item.structural_exact for item in strict),
            "mismatch": sum(not item.structural_exact for item in strict),
            "ambiguous": sum(item.ambiguous_reference for item in members),
            "critical_differences": _count_impact(
                differences, ExtractionImpact.CRITICAL
            ),
        }
    return result
