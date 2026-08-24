"""Interactive manual Gemini V2 exploration; never formal benchmark evidence."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.extractor_v2 import (  # noqa: E402
    GeminiV2Extractor,
    V2ExtractionError,
)
from guardian.experimental.manual_session_v2 import (  # noqa: E402
    MANUAL_LABEL,
    VERDICTS,
    ManualPersistenceRefused,
    ManualSessionPaths,
    ManualSessionRecorder,
)


MANUAL_OUTPUT_ROOT = ROOT / "logs" / "manual-live"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("GEMINI_V2_MODEL"))
    parser.add_argument("--record-session", action="store_true")
    parser.add_argument("--text-log", action="store_true")
    parser.add_argument(
        "--confirm-synthetic-only",
        action="store_true",
        help="Required acknowledgement when persistence is enabled.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    print(MANUAL_LABEL)
    print("SYNTHETIC INPUT ONLY")
    print("LOGGING DISABLED" if not args.record_session else "OPT-IN LOGGING ENABLED")
    if not args.model:
        print("SESSION_CONFIGURATION_ERROR // --model is required", file=sys.stderr)
        return 2
    if args.text_log and not args.record_session:
        print("SESSION_CONFIGURATION_ERROR // --text-log requires --record-session", file=sys.stderr)
        return 2
    if args.record_session and not args.confirm_synthetic_only:
        print(
            "SESSION_CONFIGURATION_ERROR // --confirm-synthetic-only is required",
            file=sys.stderr,
        )
        return 2

    try:
        extractor = GeminiV2Extractor(model=args.model)
    except V2ExtractionError as error:
        print(f"SESSION_INITIALIZATION_FAILED // {error.kind.value}", file=sys.stderr)
        return 2

    session_id = _session_id()
    recorder: Optional[ManualSessionRecorder] = None
    if args.record_session:
        jsonl = MANUAL_OUTPUT_ROOT / f"{session_id}.jsonl"
        text_path = MANUAL_OUTPUT_ROOT / f"{session_id}.txt" if args.text_log else None
        recorder = ManualSessionRecorder(
            paths=ManualSessionPaths(jsonl=jsonl, text=text_path),
            allowed_root=MANUAL_OUTPUT_ROOT,
            session_id=session_id,
            git_commit=_git_commit(),
            requested_model=args.model,
        )
        recorder.start()
        print(f"JSONL // {jsonl.relative_to(ROOT)}")
        if text_path:
            print(f"TEXT // {text_path.relative_to(ROOT)}")

    turn = 0
    last_turn: Optional[int] = None
    while True:
        try:
            raw = input("SYNTHETIC CALLER > ")
        except (EOFError, KeyboardInterrupt):
            print("\nSESSION TERMINATED")
            break
        text = raw.strip()
        if not text:
            continue
        command, _, argument = text.partition(" ")
        if command.lower() in {"/end", "/quit"}:
            break
        if command.lower() == "/mark":
            verdict = argument.strip().lower()
            if verdict not in VERDICTS:
                print("INVALID VERDICT // pass, false_positive, false_negative, ambiguous")
            elif last_turn is None:
                print("NO TURN AVAILABLE TO MARK")
            else:
                print(f"OPERATOR VERDICT // TURN {last_turn:03d} // {verdict}")
                if recorder:
                    recorder.record_verdict(turn=last_turn, verdict=verdict)
            continue
        if command.startswith("/"):
            print("UNKNOWN COMMAND // /mark VERDICT, /end, /quit")
            continue

        turn += 1
        last_turn = turn
        try:
            observation = extractor.extract(raw)
            print(f"TURN {turn:03d} // EXTRACTION_SUCCEEDED")
            for key, value in observation.signals.to_dict().items():
                print(f"{key:<22}{value}")
            if recorder:
                try:
                    recorder.record_turn(turn=turn, text=raw, observation=observation)
                except ManualPersistenceRefused:
                    print("TURN NOT PERSISTED // SENSITIVE-VALUE SAFEGUARD")
        except V2ExtractionError as error:
            print(f"TURN {turn:03d} // {error.kind.value}")
            if recorder:
                try:
                    recorder.record_turn(turn=turn, text=raw, error=error)
                except ManualPersistenceRefused:
                    print("TURN NOT PERSISTED // SENSITIVE-VALUE SAFEGUARD")
        print("VERDICT // /mark pass|false_positive|false_negative|ambiguous")

    if recorder:
        recorder.end(turns=turn)
    print(f"SESSION END // TURNS {turn}")
    return 0


def _session_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"manual-v2-{timestamp}-{uuid.uuid4().hex[:8]}"


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


if __name__ == "__main__":
    raise SystemExit(main())
