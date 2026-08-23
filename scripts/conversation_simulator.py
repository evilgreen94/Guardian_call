"""Red-team harness for live extraction or deterministic M0 oracle evaluation."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian import (  # noqa: E402
    ExtractionError,
    GeminiSignalExtractor,
    GuardianPipeline,
    InMemoryEventSink,
    ScamSignals,
)
from guardian.signals import signals_from_dict  # noqa: E402


SCENARIO_LIBRARY = ROOT / "scenarios" / "m1_adversarial_scenarios.json"
MARKS = {"pass", "false_positive", "false_negative", "ambiguous"}
ORACLE_STATUSES = (
    "PASS",
    "RISK_MISMATCH",
    "CANARY_MISMATCH",
    "MODEL_GAP",
    "AMBIGUOUS",
)
CLASSIFICATIONS = {"scam", "legitimate_control", "ambiguous"}
FAMILIES = (
    "otp_authentication",
    "payment_card_cvv",
    "money_movement",
    "remote_device_control",
    "account_takeover_recovery",
    "crypto_wallet_assets",
    "apparent_credibility",
    "manipulation_social_engineering",
    "cross_domain_masking",
)
CONSTITUTIONAL_PRINCIPLES = ("C1", "C2", "C3")
PRESETS = {
    "/obvious": "bank_otp_sophisticated",
    "/negation": "never_share_secrets_control",
    "/ambiguous": "ambiguous_security_digits",
    "/credible": "private_data_no_dangerous_request",
    "/social": "social_network_otp_takeover",
    "/financial": "safe_account_transfer",
    "/remote": "microsoft_remote_access",
    "/recovery": "recovery_code_takeover",
}


@dataclass
class TurnRecord:
    """Minimum local metadata retained for operator classification."""

    turn: int
    scenario_id: Optional[str]
    risk_level: Optional[str]
    canary_decision: Optional[str]
    event_sequence: List[str]
    extraction_error: Optional[str]
    verdict: str = "unmarked"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn": self.turn,
            "scenario_id": self.scenario_id,
            "risk_level": self.risk_level,
            "canary_decision": self.canary_decision,
            "event_sequence": list(self.event_sequence),
            "extraction_error": self.extraction_error,
            "verdict": self.verdict,
        }


@dataclass(frozen=True)
class PresentedExtractionError:
    """Compact simulator-only view of a production extraction error."""

    error_type: str
    provider: str = "Gemini"


@dataclass(frozen=True)
class OracleCaseEvaluation:
    """Deterministic assertion result for one predefined M0 signal set."""

    scenario_id: str
    status: str
    reason: str
    risk_level: str
    canary_decision: str
    event_sequence: List[str]
    result: Any


def load_library() -> Dict[str, Any]:
    """Load the synthetic adversarial prompt library."""
    with SCENARIO_LIBRARY.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def classify_extraction_error(error: ExtractionError) -> PresentedExtractionError:
    """Classify quota failures for display without changing domain errors."""
    message = str(error).lower()
    quota_markers = ("429", "resource_exhausted", "resource exhausted", "quota")
    if any(marker in message for marker in quota_markers):
        return PresentedExtractionError(error_type="QUOTA_EXHAUSTED")
    return PresentedExtractionError(error_type=error.error_type)


def format_extraction_failure(error: ExtractionError) -> List[str]:
    """Return the compact normal operator view for extraction failures."""
    presented = classify_extraction_error(error)
    return [
        "EXTRACTION_FAILED",
        f"type: {presented.error_type}",
        f"provider: {presented.provider}",
        "risk: NOT_EVALUATED",
        "canary: NOT_EVALUATED",
    ]


def validate_oracle_signals(data: Dict[str, Any]) -> None:
    """Require a complete, exact M0 ScamSignals projection in every oracle."""
    expected_fields = set(ScamSignals().to_dict())
    actual_fields = set(data)
    if actual_fields != expected_fields:
        missing = sorted(expected_fields - actual_fields)
        extra = sorted(actual_fields - expected_fields)
        raise ValueError(f"Invalid oracle signals; missing={missing}, extra={extra}")


def evaluate_oracle_scenario(
    pipeline: GuardianPipeline,
    scenario: Dict[str, Any],
) -> OracleCaseEvaluation:
    """Run predefined signals through the real deterministic M0 pipeline."""
    expected = scenario["expected"]
    signal_data = expected["signals"]
    validate_oracle_signals(signal_data)
    signals = signals_from_dict(signal_data)
    sink = InMemoryEventSink()
    result = pipeline.process_signals(signals, event_sink=sink)

    actual_risk = result.risk_assessment.level.value
    actual_canary = result.canary_decision.decision.value
    events = [event.event_type for event in sink.get_events()]
    classification = scenario["classification"]
    model_gap = scenario["model_gap"]

    if classification == "ambiguous":
        status = "AMBIGUOUS"
        reason = "Scenario is explicitly ambiguous; no pass/fail assertion applied."
    elif model_gap["present"]:
        status = "MODEL_GAP"
        concepts = ", ".join(model_gap["missing_concepts"])
        reason = f"ScamSignals M0 cannot represent: {concepts}."
    elif actual_risk != expected["risk_level"]:
        status = "RISK_MISMATCH"
        reason = f"Expected risk {expected['risk_level']}; M0 produced {actual_risk}."
    elif actual_canary != expected["canary_decision"]:
        status = "CANARY_MISMATCH"
        reason = (
            f"Expected Canary {expected['canary_decision']}; "
            f"M0 produced {actual_canary}."
        )
    else:
        status = "PASS"
        reason = "Risk and Canary match the declared security expectation."

    return OracleCaseEvaluation(
        scenario_id=scenario["id"],
        status=status,
        reason=reason,
        risk_level=actual_risk,
        canary_decision=actual_canary,
        event_sequence=events,
        result=result,
    )


def summarize_oracle(evaluations: List[OracleCaseEvaluation]) -> Dict[str, int]:
    """Count mutually exclusive oracle outcomes."""
    counts = {status: 0 for status in ORACLE_STATUSES}
    for evaluation in evaluations:
        counts[evaluation.status] += 1
    return counts


def summarize_memberships(
    evaluations: List[OracleCaseEvaluation],
    scenarios: Dict[str, Dict[str, Any]],
    metadata_field: str,
    members: tuple[str, ...],
) -> Dict[str, Dict[str, int]]:
    """Summarize overlapping diagnostic metadata without affecting outcomes."""
    grouped: Dict[str, List[OracleCaseEvaluation]] = {member: [] for member in members}
    for evaluation in evaluations:
        for member in scenarios[evaluation.scenario_id][metadata_field]:
            grouped[member].append(evaluation)
    return {
        member: {"CASES": len(grouped[member]), **summarize_oracle(grouped[member])}
        for member in members
    }


def summarize_languages(
    evaluations: List[OracleCaseEvaluation],
    scenarios: Dict[str, Dict[str, Any]],
) -> Dict[str, int]:
    """Count the declared language of each unique evaluated scenario."""
    counts: Dict[str, int] = {}
    for evaluation in evaluations:
        language = scenarios[evaluation.scenario_id]["language"]
        counts[language] = counts.get(language, 0) + 1
    return dict(sorted(counts.items()))


def print_banner(mode: str) -> None:
    print("=" * 72)
    print("GUARDIAN CALL // RED TEAM SIMULATOR")
    print("M0 SINGLE-TURN MODE // NO SESSION MEMORY")
    if mode == "oracle":
        print("OFFLINE ORACLE MODE // PREDEFINED SIGNALS // GEMINI NOT INVOKED")
    else:
        print("LIVE EXTRACTOR MODE // GEMINI")
    print("AGGRESSIVE DIAGNOSTIC HARNESS // SYNTHETIC INPUT ONLY")
    print("=" * 72)
    print("Do not enter real OTPs, passwords, card data, recovery codes, or PII.")
    print("Type /help for commands.\n")


def print_help(mode: str, variant_names: List[str]) -> None:
    print("\nCOMMANDS")
    print("  /help                         show this command list")
    print("  /reset                        clear local counters and verdict metadata")
    print("  /end                          print local verdict summary and exit")
    print("  /quit                         exit immediately")
    print("  /case <scenario_id>           run one corpus scenario")
    print("  /random                       run one random synthetic scenario")
    if mode == "oracle":
        print("  /all                          evaluate all 20 oracle scenarios")
    else:
        print("  /variants <name>              run each live text variant")
    print("  /mark pass|false_positive|false_negative|ambiguous")
    for command in PRESETS:
        print(f"  {command:<30} run its synthetic preset")
    if mode == "live":
        print(f"\nVARIANT SETS: {', '.join(variant_names)}")
    print()


class RedTeamHarness:
    """Presentation layer over explicit live or deterministic oracle paths."""

    def __init__(
        self,
        pipeline: GuardianPipeline,
        library: Dict[str, Any],
        mode: str,
        debug_errors: bool = False,
    ) -> None:
        self.pipeline = pipeline
        self.mode = mode
        self.debug_errors = debug_errors
        self.scenarios = {item["id"]: item for item in library["scenarios"]}
        self.variants = library.get("variant_sets", {})
        self.turn = 0
        self.records: List[TurnRecord] = []

    def reset(self) -> None:
        self.turn = 0
        self.records.clear()
        print("LOCAL HARNESS STATE CLEARED // M0 HAS NO SESSION MEMORY\n")

    def run_scenario(self, scenario_id: str) -> None:
        scenario = self.scenarios.get(scenario_id)
        if scenario is None:
            print(f"UNKNOWN SCENARIO // {scenario_id}\n")
            return
        print(f"PRESET // {scenario['id']} // {scenario['title']}")
        if self.mode == "oracle":
            self.run_oracle_scenario(scenario, detailed=True)
        else:
            self.run_live_text(scenario["input"], scenario_id=scenario_id)

    def run_random(self) -> None:
        self.run_scenario(random.SystemRandom().choice(list(self.scenarios)))

    def run_variants(self, name: str) -> None:
        if self.mode != "live":
            print("VARIANTS REQUIRE LIVE MODE // no oracle signals are defined\n")
            return
        phrases = self.variants.get(name)
        if phrases is None:
            available = ", ".join(sorted(self.variants))
            print(f"UNKNOWN VARIANT SET // available: {available}\n")
            return
        print(f"VARIANT RUN // {name} // {len(phrases)} ISOLATED M0 TURNS")
        for index, phrase in enumerate(phrases, 1):
            self.run_live_text(phrase, scenario_id=f"variant:{name}:{index}")

    def run_live_text(self, text: str, scenario_id: Optional[str] = None) -> None:
        self.turn += 1
        sink = InMemoryEventSink()
        result = self.pipeline.process_text(text, event_sink=sink)
        events = [event.event_type for event in sink.get_events()]

        print("\n" + "-" * 72)
        print(f"TURN {self.turn:03d} // LIVE EXTRACTOR")
        print("-" * 72)
        print("INPUT // RAW SYNTHETIC INPUT")
        print(json.dumps(text, ensure_ascii=False))

        if result.error is not None:
            print()
            for line in format_extraction_failure(result.error):
                print(line)
            if self.debug_errors:
                print(f"debug: {self._sanitized_debug_error(result.error)}", file=sys.stderr)
        else:
            self._print_pipeline_result(result, "EXTRACTED SIGNALS // GEMINI OBSERVED")

        print("\nEVENTS")
        for event_type in events:
            print(event_type)
        self._record(scenario_id, result, events)
        self._print_verdict_prompt()

    def run_oracle_scenario(
        self,
        scenario: Dict[str, Any],
        detailed: bool,
    ) -> OracleCaseEvaluation:
        self.turn += 1
        evaluation = evaluate_oracle_scenario(self.pipeline, scenario)
        result = evaluation.result
        self._record(scenario["id"], result, evaluation.event_sequence)

        if detailed:
            print("\n" + "-" * 72)
            print(f"TURN {self.turn:03d} // OFFLINE ORACLE")
            print("-" * 72)
            print("INPUT REFERENCE // NOT SENT TO GEMINI")
            print(json.dumps(scenario["input"], ensure_ascii=False))
            self._print_pipeline_result(result, "PREDEFINED ORACLE SIGNALS // NOT GEMINI EXTRACTION")
            print("\nEVENTS")
            for event_type in evaluation.event_sequence:
                print(event_type)
            print("\nBASELINE RESULT")
            print(evaluation.status.replace("_", " "))
            print(evaluation.reason)
            self._print_verdict_prompt()
        return evaluation

    def run_all_oracle(self) -> List[OracleCaseEvaluation]:
        if self.mode != "oracle":
            print("/all REQUIRES OFFLINE ORACLE MODE\n")
            return []

        print("\nM1 ADVERSARIAL BASELINE // M0 ENGINE")
        print("-" * 72)
        evaluations = [
            self.run_oracle_scenario(scenario, detailed=False)
            for scenario in self.scenarios.values()
        ]
        for evaluation in evaluations:
            label = evaluation.status.replace("_", " ")
            print(f"{evaluation.scenario_id:<42}{label}")

        counts = summarize_oracle(evaluations)
        print("\nM1 ADVERSARIAL BASELINE // M0 ENGINE")
        print(f"{'CASES':<24}{len(evaluations)}")
        for status in ORACLE_STATUSES:
            print(f"{status.replace('_', ' '):<24}{counts[status]}")

        family_counts = summarize_memberships(
            evaluations,
            self.scenarios,
            "families",
            FAMILIES,
        )
        print("\nBY FAMILY // MEMBERSHIPS MAY OVERLAP")
        for family in FAMILIES:
            self._print_coverage_row(family, family_counts[family])

        constitutional_counts = summarize_memberships(
            evaluations,
            self.scenarios,
            "constitutional_principles",
            CONSTITUTIONAL_PRINCIPLES,
        )
        print("\nCONSTITUTIONAL COVERAGE")
        for principle in CONSTITUTIONAL_PRINCIPLES:
            self._print_coverage_row(principle, constitutional_counts[principle])

        print("\nLANGUAGE COVERAGE")
        for language, count in summarize_languages(evaluations, self.scenarios).items():
            print(f"{language.upper():<24}{count}")

        non_pass = [item for item in evaluations if item.status != "PASS"]
        if non_pass:
            print("\nNON-PASS CASES")
            for evaluation in non_pass:
                label = evaluation.status.replace("_", " ")
                print(f"[{label}] {evaluation.scenario_id}: {evaluation.reason}")
        print()
        return evaluations

    @staticmethod
    def _print_coverage_row(label: str, counts: Dict[str, int]) -> None:
        display = label.replace("_", " ").upper()
        print(
            f"{display:<34} CASES {counts['CASES']:>2}  "
            f"PASS {counts['PASS']:>2}  GAP {counts['MODEL_GAP']:>2}  "
            f"RISK {counts['RISK_MISMATCH']:>2}  "
            f"CANARY {counts['CANARY_MISMATCH']:>2}  "
            f"AMB {counts['AMBIGUOUS']:>2}"
        )

    def _print_pipeline_result(self, result: Any, signal_heading: str) -> None:
        print(f"\n{signal_heading}")
        for key, value in result.signals.to_dict().items():
            print(f"{key:<24}{json.dumps(value, ensure_ascii=False)}")
        print("\nRISK")
        print(result.risk_assessment.level.value)
        print("\nREASONS")
        for index, reason in enumerate(result.risk_assessment.reasons, 1):
            print(f"{index:02d} {reason}")
        print("\nCONTRIBUTING SIGNALS")
        for signal in result.risk_assessment.contributing_signals:
            print(signal)
        print("\nCANARY")
        decision = result.canary_decision
        print(f"{decision.action.value} -> {decision.decision.value}")
        print(decision.reason)

    def _record(self, scenario_id: Optional[str], result: Any, events: List[str]) -> None:
        self.records.append(
            TurnRecord(
                turn=self.turn,
                scenario_id=scenario_id,
                risk_level=(
                    result.risk_assessment.level.value
                    if result.risk_assessment is not None
                    else None
                ),
                canary_decision=(
                    result.canary_decision.decision.value
                    if result.canary_decision is not None
                    else None
                ),
                event_sequence=events,
                extraction_error=(
                    classify_extraction_error(result.error).error_type
                    if result.error is not None
                    else None
                ),
            )
        )

    def _print_verdict_prompt(self) -> None:
        print("\nOPERATOR VERDICT")
        print("[unmarked]")
        print("Use /mark pass|false_positive|false_negative|ambiguous")
        print("-" * 72 + "\n")

    def _sanitized_debug_error(self, error: ExtractionError) -> str:
        detail = str(error)
        for variable in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            secret = os.environ.get(variable)
            if secret:
                detail = detail.replace(secret, "[REDACTED]")
        return detail[:2000]

    def mark_last(self, verdict: str) -> None:
        if verdict not in MARKS:
            print("INVALID VERDICT // pass, false_positive, false_negative, ambiguous\n")
            return
        if not self.records:
            print("NO TURN AVAILABLE TO MARK\n")
            return
        self.records[-1].verdict = verdict
        print("LOCAL SYNTHETIC RESULT")
        print(json.dumps(self.records[-1].to_dict(), indent=2))
        print()

    def print_summary(self) -> None:
        counts = {mark: 0 for mark in sorted(MARKS)}
        counts["unmarked"] = 0
        for record in self.records:
            counts[record.verdict] += 1
        print("\nLOCAL OPERATOR SUMMARY // NOT PERSISTED")
        print(f"turns {len(self.records)}")
        for verdict, count in counts.items():
            print(f"{verdict:<16}{count}")


def create_pipeline(mode: str) -> GuardianPipeline:
    """Construct an explicitly live or extractor-free M0 pipeline."""
    if mode == "oracle":
        return GuardianPipeline()
    return GuardianPipeline(extractor=GeminiSignalExtractor())


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("live", "oracle"), default="live")
    parser.add_argument(
        "--debug-errors",
        action="store_true",
        help="Print a redacted, bounded provider exception to stderr.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    print_banner(args.mode)

    if args.mode == "live" and not (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    ):
        print("EXTRACTION_FAILED")
        print("type: API_KEY_MISSING")
        print("provider: Gemini")
        print("risk: NOT_EVALUATED")
        print("canary: NOT_EVALUATED")
        return 2

    try:
        library = load_library()
        pipeline = create_pipeline(args.mode)
    except (OSError, ValueError, ExtractionError) as error:
        print(f"HARNESS_INITIALIZATION_FAILED // {type(error).__name__}")
        return 2

    harness = RedTeamHarness(
        pipeline=pipeline,
        library=library,
        mode=args.mode,
        debug_errors=args.debug_errors,
    )

    while True:
        try:
            raw = input("CALLER > ")
        except (EOFError, KeyboardInterrupt):
            print("\nHARNESS TERMINATED")
            return 0

        text = raw.strip()
        if not text:
            continue
        command, _, argument = text.partition(" ")
        command = command.lower()
        argument = argument.strip().lower()

        if command == "/help":
            print_help(args.mode, sorted(harness.variants))
        elif command == "/reset":
            harness.reset()
        elif command == "/end":
            harness.print_summary()
            return 0
        elif command == "/quit":
            return 0
        elif command == "/mark":
            harness.mark_last(argument)
        elif command == "/case":
            harness.run_scenario(argument)
        elif command == "/all":
            harness.run_all_oracle()
        elif command == "/random":
            harness.run_random()
        elif command == "/variants":
            if argument:
                harness.run_variants(argument)
            else:
                print(f"VARIANT SETS // {', '.join(sorted(harness.variants))}\n")
        elif command in PRESETS:
            harness.run_scenario(PRESETS[command])
        elif command.startswith("/"):
            print("UNKNOWN COMMAND // type /help\n")
        elif args.mode == "oracle":
            print("ORACLE MODE REQUIRES A PREDEFINED CASE // use /case, a preset, or /all\n")
        else:
            harness.run_live_text(raw)


if __name__ == "__main__":
    raise SystemExit(main())
