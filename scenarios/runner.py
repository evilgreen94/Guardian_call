"""Scenario runner for testing and demonstrating Guardian Call M0.

Executes synthetic call scenarios through GuardianPipeline and prints a clean,
industrial terminal event log.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend package directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.events import InMemoryEventSink
from guardian.pipeline import GuardianPipeline


def run_scenario(scenario_path: Path) -> None:
    """Load and execute a single synthetic scenario file."""
    if not scenario_path.exists():
        print(f"[ERROR] Scenario file not found: {scenario_path}")
        return

    with open(scenario_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", scenario_path.stem)
    description = data.get("description", "")
    dialogue = data.get("dialogue", [])
    full_text = " ".join(dialogue)

    print("=" * 70)
    print(f"GUARDIAN CALL — SCENARIO EVALUATION")
    print(f"Title: {title}")
    print(f"Description: {description}")
    print("=" * 70)

    sink = InMemoryEventSink()
    pipeline = GuardianPipeline()

    result = pipeline.process_text(full_text, event_sink=sink)

    print("\n--- EMITTED BACKEND EVENT TRAIL ---")
    for idx, event in enumerate(result.events, 1):
        print(f"[{idx:02d}] EVENT: {event.event_type}")
        print(f"     Payload: {event.payload}")

    print("\n--- FINAL EVALUATION SUMMARY ---")
    print(f"Risk Level:       {result.risk_assessment.level.value}")
    print(f"Reasons:          {', '.join(result.risk_assessment.reasons)}")
    print(f"Canary Action:    {result.canary_decision.action.value} -> {result.canary_decision.decision.value}")
    
    if result.warning_event:
        warning_payload = result.warning_event.payload
        print("\n" + "!" * 50)
        print(f"WARNING HEADLINE: {warning_payload.get('headline')}")
        print(f"DIRECTIVES:       {', '.join(warning_payload.get('directives', []))}")
        print("!" * 50)
    else:
        print("\n[OK] No user warning issued.")

    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Guardian Call Scenario Runner")
    parser.add_argument(
        "--scenario",
        type=str,
        help="Path to a scenario JSON file. If omitted, runs all scenarios in scenarios/ directory.",
    )
    args = parser.parse_args()

    scenarios_dir = Path(__file__).resolve().parent

    if args.scenario:
        run_scenario(Path(args.scenario))
    else:
        scenario_files = list(scenarios_dir.glob("*.json"))
        if not scenario_files:
            print("[INFO] No JSON scenarios found in scenarios/ directory.")
            return
        for file in scenario_files:
            run_scenario(file)


if __name__ == "__main__":
    main()
