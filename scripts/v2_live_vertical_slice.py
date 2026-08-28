"""Run an experimental Gemini V2 to M2.3 longitudinal text vertical slice."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.extractor_v2 import (  # noqa: E402
    GeminiV2Extractor,
    V2ExtractionError,
    sdk_version,
)
from guardian.experimental.live_vertical_slice_v2 import (  # noqa: E402
    V2VerticalSliceState,
    process_text_turn,
)


DEFAULT_SESSION_ID = "m2-5-live-v2"
DEFAULT_TURNS: Tuple[str, ...] = (
    "This is a courtesy call from synthetic Northbridge Bank about your account. No action is required on this call.",
    "Your savings account ending in a synthetic reference has normal activity. You can review it later in the official app.",
    "To block the pending transfer, read me the six-digit verification code that just arrived.",
    "I still need that same six-digit verification code now so I can cancel the transfer.",
    "Do not read that code to me or to anyone else; enter it only in the official app if you initiated the action.",
    "Your computer may also be compromised. Install the remote support app and approve my remote-control request now.",
)
SMOKE_TURNS: Tuple[str, ...] = DEFAULT_TURNS[:4]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("GEMINI_V2_MODEL"))
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the first four controlled turns only.",
    )
    parser.add_argument(
        "--turn",
        action="append",
        dest="turns",
        help="Synthetic text turn. Repeat to override the default script.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    print("EXPERIMENTAL M2.5 LIVE V2 LONGITUDINAL VERTICAL SLICE")
    print("RAW TRANSCRIPTS NOT PERSISTED")
    print("RAW PROVIDER RESPONSES NOT PERSISTED")
    print("MODEL OUTPUT IS EVIDENCE, NOT AUTHORITY")
    print("CANARY AUTHORIZATION ONLY AFTER M2.3 POLICY")

    if not args.model:
        print("VERTICAL_SLICE_CONFIGURATION_ERROR // --model is required", file=sys.stderr)
        return 2

    try:
        extractor = GeminiV2Extractor(model=args.model)
    except V2ExtractionError as error:
        print(
            "VERTICAL_SLICE_INITIALIZATION_FAILED // "
            f"{json.dumps(error.to_dict(), sort_keys=True)}",
            file=sys.stderr,
        )
        return 2

    print(f"PROVIDER // Gemini")
    print(f"MODEL // {args.model}")
    print(f"SDK // {sdk_version() or 'unknown'}")

    state = run_vertical_slice(
        extractor=extractor,
        session_id=args.session_id,
        turns=tuple(args.turns) if args.turns else (SMOKE_TURNS if args.smoke else DEFAULT_TURNS),
    )
    print(f"SESSION_END // turns={len(state.turns)}")
    return 0


def run_vertical_slice(
    *,
    extractor: GeminiV2Extractor,
    session_id: str,
    turns: Iterable[str],
) -> V2VerticalSliceState:
    state = V2VerticalSliceState.initial(session_id)
    for index, text in enumerate(turns, 1):
        turn_id = f"turn-{index}"
        state = process_text_turn(
            state,
            extractor=extractor,
            text=text,
            turn_id=turn_id,
            turn_number=index,
        )
        print_turn_summary(state.turns[-1].to_dict())
    return state


def print_turn_summary(turn: dict) -> None:
    print(f"TURN {turn['turn_number']:03d} // {turn['status']}")
    print(json.dumps(turn, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
