"""Run the formal M1.2B Gemini-to-ScamSignalsV2 benchmark."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.extractor_v2 import (  # noqa: E402
    GeminiV2Extractor,
    V2ExtractionError,
)
from guardian.experimental.live_benchmark_v2 import (  # noqa: E402
    CORPUS_RELATIVE_PATH,
    FORMAL_LABEL,
    load_corpus,
    load_manifest,
    repository_commit,
    run_formal_benchmark,
    select_scenario_ids,
)


FORMAL_OUTPUT_ROOT = ROOT / "logs" / "m1.2b-formal"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case", action="append", dest="case_ids")
    selection.add_argument("--family")
    selection.add_argument("--principle")
    selection.add_argument("--all", action="store_true", dest="all_cases")
    parser.add_argument("--model", default=os.environ.get("GEMINI_V2_MODEL"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--min-request-interval", type=float, default=0.0)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    print(FORMAL_LABEL)
    print("RAW TRANSCRIPTS NOT PERSISTED")
    print("ONE PROVIDER ATTEMPT PER SCENARIO")
    if not args.model:
        print("BENCHMARK_CONFIGURATION_ERROR // --model is required", file=sys.stderr)
        return 2
    if args.resume and args.output:
        print("BENCHMARK_CONFIGURATION_ERROR // use --resume without --output", file=sys.stderr)
        return 2
    if args.resume:
        output_path = _repository_path(args.resume)
        try:
            existing = load_manifest(output_path)
            scenario_ids = tuple(existing["selection"])
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            print("BENCHMARK_INPUT_ERROR // invalid resume manifest", file=sys.stderr)
            return 2
        if any((args.case_ids, args.family, args.principle, args.all_cases)):
            print("BENCHMARK_CONFIGURATION_ERROR // resume already defines selection", file=sys.stderr)
            return 2
    else:
        if args.output is None:
            print("BENCHMARK_CONFIGURATION_ERROR // --output is required", file=sys.stderr)
            return 2
        output_path = _repository_path(args.output)
        existing = None
        if not any((args.case_ids, args.family, args.principle, args.all_cases)):
            print("BENCHMARK_CONFIGURATION_ERROR // scenario selection is required", file=sys.stderr)
            return 2

    try:
        corpus_path = ROOT / CORPUS_RELATIVE_PATH
        library = load_corpus(corpus_path)
        if not args.resume:
            scenario_ids = select_scenario_ids(
                library,
                case_ids=tuple(args.case_ids or ()),
                family=args.family,
                principle=args.principle,
                all_cases=args.all_cases,
            )
        extractor = GeminiV2Extractor(model=args.model)
        manifest = run_formal_benchmark(
            extractor=extractor,
            library=library,
            corpus_path=corpus_path,
            scenario_ids=scenario_ids,
            output_path=output_path,
            allowed_output_root=FORMAL_OUTPUT_ROOT,
            git_commit=repository_commit(ROOT),
            existing_manifest=existing,
            min_request_interval=args.min_request_interval,
        )
    except V2ExtractionError as error:
        print(f"BENCHMARK_INITIALIZATION_FAILED // {error.kind.value}", file=sys.stderr)
        return 2
    except (KeyError, OSError, ValueError) as error:
        print(f"BENCHMARK_INPUT_ERROR // {type(error).__name__}", file=sys.stderr)
        return 2

    counts = manifest["summary"]["execution"]["status_counts"]
    print(f"RUN_ID // {manifest['run']['run_id']}")
    print(f"OUTPUT // {output_path.relative_to(ROOT)}")
    for status, count in counts.items():
        print(f"{status:<28}{count}")
    print(f"UNATTEMPTED{'':<17}{len(manifest['unattempted'])}")
    return 0


def _repository_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
