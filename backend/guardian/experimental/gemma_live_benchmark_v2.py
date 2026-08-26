"""Local Gemma/Ollama benchmark orchestration for M1.4A."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from .evaluation_v2 import ScenarioEvaluation, compare_signals, summarize_benchmark
from .gemma_extractor_v2 import (
    GENERATION_OPTIONS,
    GENERATION_SCHEMA_REVISION,
    GENERATION_SCHEMA_SHA256,
    MODEL_TAG,
    PROMPT_REVISION,
    PROMPT_SHA256,
    PROVIDER,
    SCHEMA_REVISION,
    SCHEMA_SHA256,
    GemmaExtractionStatus,
    GemmaV2ExtractionError,
    GemmaV2Extractor,
    canonical_json_bytes,
    sha256_hex,
)
from .signals_v2 import IdentityAssuranceContext, ScamSignalsV2


FORMAL_LABEL = "M1.4A LOCAL GEMMA V2 EXTRACTION BENCHMARK"
BENCHMARK_MODE = "LOCAL_GEMMA_V2_EXTRACTION"
CORPUS_RELATIVE_PATH = "scenarios/m1_adversarial_scenarios.json"
SUCCESS_STATUSES = {"EXACT_MATCH", "SEMANTIC_DIFFERENCES", "AMBIGUOUS_REFERENCE"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def repository_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def load_corpus(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def select_scenario_ids(
    library: Mapping[str, Any],
    *,
    case_ids: Sequence[str] = (),
    all_cases: bool = False,
) -> Tuple[str, ...]:
    if bool(case_ids) == all_cases:
        raise ValueError("select exactly one of cases or all")
    scenarios = tuple(library["scenarios"])
    known = {item["id"] for item in scenarios}
    if all_cases:
        return tuple(item["id"] for item in scenarios)
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("duplicate scenario selection")
    unknown = sorted(set(case_ids) - known)
    if unknown:
        raise ValueError(f"unknown scenarios: {unknown}")
    return tuple(case_ids)


def run_fingerprint(
    *,
    scenario_ids: Sequence[str],
    corpus_sha256: str,
    requested_model: str,
    git_commit: str,
) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "benchmark_mode": BENCHMARK_MODE,
                "corpus_sha256": corpus_sha256,
                "generation_options": GENERATION_OPTIONS,
                "git_commit": git_commit,
                "prompt_revision": PROMPT_REVISION,
                "prompt_sha256": PROMPT_SHA256,
                "requested_model": requested_model,
                "scenario_ids": list(scenario_ids),
                "schema_revision": SCHEMA_REVISION,
                "schema_sha256": SCHEMA_SHA256,
            }
        )
    )


def run_local_benchmark(
    *,
    extractor: GemmaV2Extractor,
    library: Mapping[str, Any],
    corpus_path: Path,
    scenario_ids: Sequence[str],
    output_path: Path,
    allowed_output_root: Path,
    git_commit: str,
    ollama_version: Optional[str] = None,
    ollama_model_digest: Optional[str] = None,
    existing_manifest: Optional[Mapping[str, Any]] = None,
    run_id: Optional[str] = None,
    clock: Callable[[], datetime] = utc_now,
) -> Dict[str, Any]:
    """Run local extraction and persist a sanitized manifest after each case."""
    _require_output_path(output_path, allowed_output_root)
    corpus_hash = sha256_hex(corpus_path.read_bytes())
    fingerprint = run_fingerprint(
        scenario_ids=scenario_ids,
        corpus_sha256=corpus_hash,
        requested_model=extractor.model,
        git_commit=git_commit,
    )
    scenarios = {item["id"]: item for item in library["scenarios"]}
    mappings = library["v2_mappings"]

    if existing_manifest is None:
        manifest: Dict[str, Any] = {
            "label": FORMAL_LABEL,
            "run": {
                "run_id": run_id or str(uuid.uuid4()),
                "benchmark_mode": BENCHMARK_MODE,
                "started_at_utc": iso_utc(clock()),
                "completed_at_utc": None,
                "complete": False,
                "provider": PROVIDER,
                "requested_model": extractor.model,
                "benchmark_model_tag": MODEL_TAG,
                "ollama_version": ollama_version,
                "ollama_model_digest": ollama_model_digest,
                "generation_options": GENERATION_OPTIONS,
                "git_commit": git_commit,
                "prompt_revision": PROMPT_REVISION,
                "prompt_sha256": PROMPT_SHA256,
                "schema_revision": SCHEMA_REVISION,
                "schema_sha256": SCHEMA_SHA256,
                "generation_schema_revision": GENERATION_SCHEMA_REVISION,
                "generation_schema_sha256": GENERATION_SCHEMA_SHA256,
                "corpus_path": CORPUS_RELATIVE_PATH,
                "corpus_sha256": corpus_hash,
                "run_fingerprint": fingerprint,
                "maximum_attempts_per_scenario": 1,
                "raw_transcripts_persisted": False,
                "raw_model_responses_persisted": False,
            },
            "selection": list(scenario_ids),
            "results": [],
            "unattempted": list(scenario_ids),
            "summary": {},
        }
    else:
        manifest = json.loads(json.dumps(existing_manifest))
        if manifest.get("label") != FORMAL_LABEL:
            raise ValueError("resume artifact is not an M1.4A Gemma manifest")
        if manifest.get("run", {}).get("run_fingerprint") != fingerprint:
            raise ValueError("resume fingerprint does not match current run contract")
        if manifest.get("selection") != list(scenario_ids):
            raise ValueError("resume selection does not match")

    completed = {item["scenario_id"] for item in manifest["results"]}
    _refresh_manifest(manifest, library)
    _write_manifest(output_path, manifest)

    for scenario_id in scenario_ids:
        if scenario_id in completed:
            continue
        scenario = scenarios[scenario_id]
        mapping = mappings[scenario_id]
        expected = ScamSignalsV2.from_dict(mapping["signals"])
        result: Dict[str, Any] = {
            "scenario_id": scenario_id,
            "language": scenario["language"],
            "families": list(scenario["families"]),
            "constitutional_principles": list(scenario["constitutional_principles"]),
            "expected_mapping_source": f"{CORPUS_RELATIVE_PATH}#v2_mappings/{scenario_id}",
            "expected_signals": expected.to_dict(),
            "expected_ambiguity": mapping.get("ambiguity"),
            "identity_assurance_context": {
                **IdentityAssuranceContext().to_dict(),
                "source": "benchmark_external_default_no_independent_verification",
            },
            "attempt": 1,
            "attempted_at_utc": iso_utc(clock()),
        }
        try:
            observation = extractor.extract(scenario["input"])
            evaluation = compare_signals(
                scenario_id,
                expected,
                observation.signals,
                ambiguity=mapping.get("ambiguity"),
            )
            status = (
                "AMBIGUOUS_REFERENCE"
                if evaluation.ambiguous_reference
                else "EXACT_MATCH" if evaluation.structural_exact else "SEMANTIC_DIFFERENCES"
            )
            result.update(
                {
                    "status": status,
                    "extraction_status": GemmaExtractionStatus.EXTRACTION_SUCCEEDED.value,
                    "observed_signals": observation.signals.to_dict(),
                    "provider_provenance": observation.provenance_dict(),
                    "comparison": evaluation.to_dict(),
                    "failure": None,
                }
            )
        except GemmaV2ExtractionError as error:
            result.update(
                {
                    "status": error.status.value,
                    "extraction_status": error.status.value,
                    "observed_signals": None,
                    "provider_provenance": {
                        "provider": PROVIDER,
                        "requested_model": extractor.model,
                    },
                    "comparison": None,
                    "failure": error.to_dict(),
                }
            )
        manifest["results"].append(result)
        completed.add(scenario_id)
        _refresh_manifest(manifest, library)
        _write_manifest(output_path, manifest)

    manifest["run"]["completed_at_utc"] = iso_utc(clock())
    _refresh_manifest(manifest, library)
    manifest["run"]["complete"] = not manifest["unattempted"]
    _write_manifest(output_path, manifest)
    return manifest


def load_manifest(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("manifest root must be an object")
    return value


def summarize_local_results(
    results: Sequence[Mapping[str, Any]], library: Mapping[str, Any]
) -> Dict[str, Any]:
    evaluations = tuple(
        _evaluation_from_result(item)
        for item in results
        if item["status"] in SUCCESS_STATUSES
    )
    memberships = {
        item["id"]: tuple(item["constitutional_principles"])
        for item in library["scenarios"]
    }
    return {
        "execution": _execution_counts(results),
        "semantic": summarize_benchmark(evaluations, memberships).to_dict(),
    }


def deterministic_manifest_json(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _refresh_manifest(manifest: Dict[str, Any], library: Mapping[str, Any]) -> None:
    completed = {item["scenario_id"] for item in manifest["results"]}
    manifest["unattempted"] = [
        scenario_id for scenario_id in manifest["selection"] if scenario_id not in completed
    ]
    manifest["summary"] = summarize_local_results(manifest["results"], library)
    manifest["summary"]["execution"]["unattempted"] = len(manifest["unattempted"])


def _execution_counts(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    statuses: Dict[str, int] = {}
    for result in results:
        statuses[result["status"]] = statuses.get(result["status"], 0) + 1
    return {
        "results_recorded": len(results),
        "status_counts": dict(sorted(statuses.items())),
        "semantic_evaluations": sum(
            result["status"] in SUCCESS_STATUSES for result in results
        ),
    }


def _evaluation_from_result(result: Mapping[str, Any]) -> ScenarioEvaluation:
    return compare_signals(
        result["scenario_id"],
        ScamSignalsV2.from_dict(result["expected_signals"]),
        ScamSignalsV2.from_dict(result["observed_signals"]),
        ambiguity=result.get("expected_ambiguity"),
    )


def _require_output_path(path: Path, allowed_root: Path) -> None:
    resolved = path.resolve()
    root = allowed_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"output must be a file under {root}")


def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(deterministic_manifest_json(manifest), encoding="utf-8", newline="\n")
    os.replace(temporary, path)
