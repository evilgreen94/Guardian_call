"""Run the M1.4A local Gemma/Ollama V2 extractor benchmark."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from guardian.experimental.gemma_extractor_v2 import (  # noqa: E402
    MODEL_TAG,
    GemmaV2Extractor,
)
from guardian.experimental.gemma_live_benchmark_v2 import (  # noqa: E402
    CORPUS_RELATIVE_PATH,
    FORMAL_LABEL,
    load_corpus,
    load_manifest,
    repository_commit,
    run_local_benchmark,
    select_scenario_ids,
)


LOG_ROOT = ROOT / "logs" / "m1.4-gemma"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", dest="cases", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--model", default=MODEL_TAG)
    parser.add_argument("--output")
    parser.add_argument("--resume")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        corpus_path = ROOT / CORPUS_RELATIVE_PATH
        library = load_corpus(corpus_path)
        scenario_ids = select_scenario_ids(
            library,
            case_ids=tuple(args.cases),
            all_cases=args.all,
        )
        output = Path(args.output) if args.output else LOG_ROOT / "latest.json"
        if not output.is_absolute():
            output = ROOT / output
        existing = load_manifest(Path(args.resume)) if args.resume else None
        manifest = run_local_benchmark(
            extractor=GemmaV2Extractor(model=args.model),
            library=library,
            corpus_path=corpus_path,
            scenario_ids=scenario_ids,
            output_path=output,
            allowed_output_root=LOG_ROOT,
            git_commit=repository_commit(ROOT),
            ollama_version=ollama_version(),
            ollama_model_digest=ollama_model_digest(args.model),
            existing_manifest=existing,
        )
    except Exception as error:
        print(f"GEMMA_BENCHMARK_ERROR // {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(FORMAL_LABEL)
        print("LOCAL OLLAMA ONLY")
        print(f"output={output.relative_to(ROOT)}")
        print(f"selection={len(manifest['selection'])}")
        print(f"complete={str(manifest['run']['complete']).lower()}")
        print(f"status_counts={manifest['summary']['execution']['status_counts']}")
    return 0


def ollama_version() -> Optional[str]:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    value = (result.stdout or result.stderr).strip()
    return value or None


def ollama_model_digest(model: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["ollama", "show", model, "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        payload: Dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    for key in ("digest", "model_info"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    details = payload.get("details")
    if isinstance(details, dict):
        digest = details.get("digest")
        if isinstance(digest, str) and digest:
            return digest
    return None


if __name__ == "__main__":
    raise SystemExit(main())
