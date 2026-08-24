"""M1.2A offline benchmark for expected versus synthetic observed V2 signals."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.evaluation_v2 import (  # noqa: E402
    BenchmarkSummary,
    ScenarioEvaluation,
    compare_signals,
    summarize_benchmark,
)
from guardian.experimental.signals_v2 import (  # noqa: E402
    ActionTypeV2,
    Actor,
    AssetCategory,
    AssetSubtype,
    ClaimedEntityType,
    Destination,
    IdentityPretext,
    InteractionAct,
    ManipulationType,
    ScamSignalsV2,
    SemanticDirection,
    SensitiveAsset,
)


CORPUS_PATH = ROOT / "scenarios" / "m1_adversarial_scenarios.json"
BANNER = (
    "M1.2A OFFLINE EXTRACTOR EVALUATION",
    "NO GEMINI",
    "NO NETWORK",
    "SYNTHETIC OBSERVED SIGNALS",
)


@dataclass(frozen=True)
class ReplayFixture:
    name: str
    group: str
    scenario_id: str
    description: str
    transform: Callable[[ScamSignalsV2], ScamSignalsV2]


@dataclass(frozen=True)
class ReplayResult:
    fixture: ReplayFixture
    expected: ScamSignalsV2
    observed: ScamSignalsV2
    evaluation: ScenarioEvaluation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixture": self.fixture.name,
            "group": self.fixture.group,
            "case": self.fixture.scenario_id,
            "description": self.fixture.description,
            "expected": self.expected.to_dict(),
            "observed": self.observed.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }


def load_corpus() -> Dict[str, Any]:
    with CORPUS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _identity_without_claims(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(
        signals,
        identity_pretext=IdentityPretext(
            claims=frozenset(),
            knowledge_categories=signals.identity_pretext.knowledge_categories,
        ),
    )


def _identity_with_bank(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(
        signals,
        identity_pretext=IdentityPretext(
            claims=signals.identity_pretext.claims | {ClaimedEntityType.BANK},
            knowledge_categories=signals.identity_pretext.knowledge_categories,
        ),
    )


def _replace_first_act(
    signals: ScamSignalsV2,
    predicate: Callable[[InteractionAct], bool],
    **changes: Any,
) -> ScamSignalsV2:
    acts = list(signals.interaction_acts)
    for index, act in enumerate(acts):
        if predicate(act):
            acts[index] = replace(act, **changes)
            return replace(signals, interaction_acts=tuple(acts))
    raise ValueError("Replay fixture could not find its target interaction act")


def _remove_first_act(
    signals: ScamSignalsV2,
    predicate: Callable[[InteractionAct], bool],
) -> ScamSignalsV2:
    acts = list(signals.interaction_acts)
    for index, act in enumerate(acts):
        if predicate(act):
            del acts[index]
            return replace(signals, interaction_acts=tuple(acts))
    raise ValueError("Replay fixture could not find its target interaction act")


def _otp_act(direction: SemanticDirection = SemanticDirection.DIRECT_REQUEST) -> InteractionAct:
    return InteractionAct(
        action=ActionTypeV2.DISCLOSE,
        asset=SensitiveAsset(AssetCategory.SECRET, AssetSubtype.OTP),
        semantic_direction=direction,
        actor=Actor.USER,
        destination=Destination.CALLER,
    )


def _exact(signals: ScamSignalsV2) -> ScamSignalsV2:
    return ScamSignalsV2.from_dict(signals.to_dict())


def _missing_otp(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _remove_first_act(
        signals, lambda act: bool(act.asset and act.asset.subtype == AssetSubtype.OTP)
    )


def _spurious_otp(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(signals, interaction_acts=signals.interaction_acts + (_otp_act(),))


def _warning_to_request(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _replace_first_act(
        signals,
        lambda act: act.semantic_direction == SemanticDirection.WARNING,
        semantic_direction=SemanticDirection.DIRECT_REQUEST,
    )


def _request_to_warning(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _replace_first_act(
        signals,
        lambda act: act.semantic_direction == SemanticDirection.DIRECT_REQUEST,
        semantic_direction=SemanticDirection.WARNING,
    )


def _self_service_to_request(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _replace_first_act(
        signals,
        lambda act: act.semantic_direction == SemanticDirection.SELF_SERVICE
        and act.asset is not None,
        semantic_direction=SemanticDirection.DIRECT_REQUEST,
    )


def _otp_to_password(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _replace_first_act(
        signals,
        lambda act: bool(act.asset and act.asset.subtype == AssetSubtype.OTP),
        asset=SensitiveAsset(AssetCategory.SECRET, AssetSubtype.PASSWORD),
    )


def _caller_to_official(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _replace_first_act(
        signals,
        lambda act: act.destination == Destination.CALLER and act.asset is not None,
        destination=Destination.OFFICIAL_SELF_SERVICE,
    )


def _missing_manipulation(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(
        signals,
        manipulation=signals.manipulation - {ManipulationType.URGENCY},
    )


def _spurious_manipulation(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(
        signals,
        manipulation=signals.manipulation | {ManipulationType.SECRECY},
    )


def _missing_mixed_act(signals: ScamSignalsV2) -> ScamSignalsV2:
    return _remove_first_act(
        signals,
        lambda act: act.semantic_direction == SemanticDirection.DIRECT_REQUEST,
    )


def _reverse_acts(signals: ScamSignalsV2) -> ScamSignalsV2:
    return replace(signals, interaction_acts=tuple(reversed(signals.interaction_acts)))


def _multiple_similar_acts(signals: ScamSignalsV2) -> ScamSignalsV2:
    acts = []
    for act in reversed(signals.interaction_acts):
        if act.asset and act.asset.subtype == AssetSubtype.CARD_NUMBER:
            act = replace(act, destination=Destination.OFFICIAL_SELF_SERVICE)
        elif act.asset and act.asset.subtype == AssetSubtype.CARD_EXPIRY:
            act = replace(act, semantic_direction=SemanticDirection.WARNING)
        elif act.asset and act.asset.subtype == AssetSubtype.CARD_SECURITY_CODE:
            act = replace(act, actor=Actor.THIRD_PARTY)
        acts.append(act)
    return replace(signals, interaction_acts=tuple(acts))


REPLAY_FIXTURES: Tuple[ReplayFixture, ...] = (
    ReplayFixture(
        "exact",
        "exact",
        "bank_otp_sophisticated",
        "Perfect structural replay.",
        _exact,
    ),
    ReplayFixture(
        "missing-otp-act",
        "acts",
        "bank_otp_sophisticated",
        "Expected OTP act is absent.",
        _missing_otp,
    ),
    ReplayFixture(
        "spurious-otp-request",
        "acts",
        "legitimate_bank_notification",
        "An active OTP disclosure act is invented.",
        _spurious_otp,
    ),
    ReplayFixture(
        "warning-to-direct-request",
        "semantic-direction",
        "social_network_legitimate_warning",
        "WARNING is observed as DIRECT_REQUEST.",
        _warning_to_request,
    ),
    ReplayFixture(
        "direct-request-to-warning",
        "semantic-direction",
        "transfer_explicit_bank_request_es",
        "DIRECT_REQUEST is observed as WARNING.",
        _request_to_warning,
    ),
    ReplayFixture(
        "self-service-to-direct-request",
        "semantic-direction",
        "otp_self_entry_official_app_es",
        "SELF_SERVICE is observed as DIRECT_REQUEST.",
        _self_service_to_request,
    ),
    ReplayFixture(
        "otp-to-password",
        "assets",
        "bank_otp_sophisticated",
        "OTP is observed as PASSWORD.",
        _otp_to_password,
    ),
    ReplayFixture(
        "caller-to-official-self-service",
        "destinations",
        "bank_otp_sophisticated",
        "CALLER destination is observed as OFFICIAL_SELF_SERVICE.",
        _caller_to_official,
    ),
    ReplayFixture(
        "missing-manipulation",
        "sets",
        "bank_otp_sophisticated",
        "Expected URGENCY is omitted.",
        _missing_manipulation,
    ),
    ReplayFixture(
        "spurious-manipulation",
        "sets",
        "legitimate_bank_notification",
        "SECRECY is spuriously observed.",
        _spurious_manipulation,
    ),
    ReplayFixture(
        "missing-identity-claim",
        "sets",
        "bank_otp_sophisticated",
        "Expected bank identity claim is omitted.",
        _identity_without_claims,
    ),
    ReplayFixture(
        "spurious-claimed-entity",
        "sets",
        "never_share_secrets_control",
        "A bank identity claim is spuriously observed.",
        _identity_with_bank,
    ),
    ReplayFixture(
        "mixed-intent-missing-act",
        "acts",
        "otp_password_negation_mixed_es",
        "One act is correct while the active request is missing.",
        _missing_mixed_act,
    ),
    ReplayFixture(
        "reordered-acts",
        "matching",
        "recovery_code_takeover",
        "Identical acts arrive in a different order.",
        _reverse_acts,
    ),
    ReplayFixture(
        "multiple-similar-acts",
        "matching",
        "isp_card_cvv",
        "Several similar acts require stable semantic pairing.",
        _multiple_similar_acts,
    ),
    ReplayFixture(
        "ambiguous-reference",
        "ambiguity",
        "ambiguous_security_digits",
        "Ambiguous ground truth remains visible and excluded from strict accuracy.",
        _exact,
    ),
)


def fixture_registry() -> Dict[str, ReplayFixture]:
    return {fixture.name: fixture for fixture in REPLAY_FIXTURES}


def select_fixtures(selector: str) -> Tuple[ReplayFixture, ...]:
    if selector == "all":
        return REPLAY_FIXTURES
    named = fixture_registry().get(selector)
    if named:
        return (named,)
    grouped = tuple(fixture for fixture in REPLAY_FIXTURES if fixture.group == selector)
    if grouped:
        return grouped
    raise ValueError(f"Unknown replay fixture or group: {selector}")


def run_replays(
    fixtures: Iterable[ReplayFixture],
    library: Mapping[str, Any],
) -> Tuple[ReplayResult, ...]:
    scenarios = {item["id"]: item for item in library["scenarios"]}
    mappings = library["v2_mappings"]
    results: List[ReplayResult] = []
    for fixture in fixtures:
        mapping = mappings[fixture.scenario_id]
        expected = ScamSignalsV2.from_dict(mapping["signals"])
        observed = fixture.transform(expected)
        evaluation = compare_signals(
            fixture.scenario_id,
            expected,
            observed,
            ambiguity=mapping.get("ambiguity"),
        )
        if fixture.scenario_id not in scenarios:
            raise ValueError(f"Unknown scenario: {fixture.scenario_id}")
        results.append(ReplayResult(fixture, expected, observed, evaluation))
    return tuple(results)


def constitutional_memberships(library: Mapping[str, Any]) -> Dict[str, Tuple[str, ...]]:
    return {
        scenario["id"]: tuple(scenario["constitutional_principles"])
        for scenario in library["scenarios"]
    }


def _fixture_for_case(case_id: str) -> ReplayFixture:
    return ReplayFixture(
        "exact",
        "exact",
        case_id,
        "Perfect structural replay for the selected case.",
        _exact,
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", default="all")
    parser.add_argument("--case")
    parser.add_argument("--list-fixtures", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Include existing synthetic scenario text in text output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        library = load_corpus()
        if args.list_fixtures:
            return _print_fixture_list(args.format)
        if args.case:
            if args.replay != "exact":
                raise ValueError("--case currently supports only --replay exact")
            fixtures = (_fixture_for_case(args.case),)
        else:
            fixtures = select_fixtures(args.replay)
        results = run_replays(fixtures, library)
    except (KeyError, OSError, ValueError) as error:
        print(f"BENCHMARK_INPUT_ERROR // {error}", file=sys.stderr)
        return 2

    summary = summarize_benchmark(
        (item.evaluation for item in results),
        constitutional_memberships(library),
    )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "benchmark": BANNER[0],
                    "constraints": list(BANNER[1:]),
                    "replays": [item.to_dict() for item in results],
                    "summary": summary.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print_text(results, summary, library, args.show_text)
    return 0


def _print_fixture_list(output_format: str) -> int:
    fixtures = [
        {
            "name": item.name,
            "group": item.group,
            "case": item.scenario_id,
            "description": item.description,
        }
        for item in REPLAY_FIXTURES
    ]
    if output_format == "json":
        print(json.dumps({"fixtures": fixtures}, indent=2, sort_keys=True))
    else:
        for line in BANNER:
            print(line)
        print()
        for fixture in fixtures:
            print(
                f"{fixture['name']:<36} {fixture['group']:<20} "
                f"{fixture['case']}"
            )
    return 0


def _print_text(
    results: Tuple[ReplayResult, ...],
    summary: BenchmarkSummary,
    library: Mapping[str, Any],
    show_text: bool,
) -> None:
    for line in BANNER:
        print(line)
    scenarios = {item["id"]: item for item in library["scenarios"]}
    for result in results:
        print("\n" + "=" * 72)
        print(f"FIXTURE // {result.fixture.name}")
        print(f"CASE // {result.fixture.scenario_id}")
        if show_text:
            print("TEXT // EXISTING SYNTHETIC CORPUS")
            print(scenarios[result.fixture.scenario_id]["input"])
        print("\nEXPECTED")
        print(json.dumps(result.expected.to_dict(), indent=2, sort_keys=True))
        print("\nOBSERVED // REPLAY FIXTURE")
        print(json.dumps(result.observed.to_dict(), indent=2, sort_keys=True))
        print("\nDIFFERENCES")
        if result.evaluation.differences:
            for difference in result.evaluation.differences:
                print(
                    f"{difference.difference_type.value} // {difference.path} // "
                    f"expected={difference.expected} // observed={difference.observed} "
                    f"// impact={difference.impact.value}"
                )
        else:
            print("EXACT_MATCH")
        print("\nSUMMARY")
        print(f"status={result.evaluation.status}")
        print(f"exact={str(result.evaluation.structural_exact).lower()}")
        print(f"differences={len(result.evaluation.differences)}")
        print(
            "critical="
            f"{result.evaluation.to_dict()['difference_counts']['critical']}"
        )

    global_summary = summary.to_dict()["global"]
    print("\n" + "=" * 72)
    print("BENCHMARK SUMMARY")
    for key, value in global_summary.items():
        print(f"{key.upper():<32}{value}")


if __name__ == "__main__":
    raise SystemExit(main())
