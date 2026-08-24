"""Formal M1.2B live benchmark orchestration and provenance."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .evaluation_v2 import ScenarioEvaluation, compare_signals, summarize_benchmark
from .extractor_v2 import (
    PROMPT_REVISION,
    PROMPT_SHA256,
    SCHEMA_REVISION,
    SCHEMA_SHA256,
    GeminiV2Extractor,
    V2ExtractionError,
    V2ExtractionFailureKind,
    canonical_json_bytes,
    sdk_version,
    sha256_hex,
)
from .signals_v2 import IdentityAssuranceContext, ScamSignalsV2


FORMAL_LABEL = "FORMAL M1.2B LIVE V2 EXTRACTION BENCHMARK"
BENCHMARK_MODE = "LIVE_V2_EXTRACTION"
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
    family: Optional[str] = None,
    principle: Optional[str] = None,
    all_cases: bool = False,
) -> Tuple[str, ...]:
    modes = sum((bool(case_ids), family is not None, principle is not None, all_cases))
    if modes != 1:
        raise ValueError("select exactly one of cases, family, principle, or all")
    scenarios = tuple(library["scenarios"])
    known = {item["id"] for item in scenarios}
    if case_ids:
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("duplicate scenario selection")
        unknown = sorted(set(case_ids) - known)
        if unknown:
            raise ValueError(f"unknown scenarios: {unknown}")
        return tuple(case_ids)
    if family is not None:
        selected = tuple(item["id"] for item in scenarios if family in item["families"])
    elif principle is not None:
        selected = tuple(
            item["id"]
            for item in scenarios
            if principle in item["constitutional_principles"]
        )
    else:
        selected = tuple(item["id"] for item in scenarios)
    if not selected:
        raise ValueError("selection contains no scenarios")
    return selected


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
                "corpus_sha256": corpus_sha256,
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


def run_formal_benchmark(
    *,
    extractor: GeminiV2Extractor,
    library: Mapping[str, Any],
    corpus_path: Path,
    scenario_ids: Sequence[str],
    output_path: Path,
    allowed_output_root: Path,
    git_commit: str,
    existing_manifest: Optional[Mapping[str, Any]] = None,
    run_id: Optional[str] = None,
    clock: Callable[[], datetime] = utc_now,
    sleeper: Callable[[float], None] = time.sleep,
    min_request_interval: float = 0.0,
) -> Dict[str, Any]:
    """Run one-attempt live extraction and persist after every completed case."""
    if min_request_interval < 0:
        raise ValueError("min_request_interval must be non-negative")
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
                "provider": "Gemini",
                "requested_model": extractor.model,
                "sdk_version": sdk_version(),
                "git_commit": git_commit,
                "prompt_revision": PROMPT_REVISION,
                "prompt_sha256": PROMPT_SHA256,
                "schema_revision": SCHEMA_REVISION,
                "schema_sha256": SCHEMA_SHA256,
                "corpus_path": CORPUS_RELATIVE_PATH,
                "corpus_sha256": corpus_hash,
                "run_fingerprint": fingerprint,
                "maximum_attempts_per_scenario": 1,
                "min_request_interval_seconds": min_request_interval,
            },
            "selection": list(scenario_ids),
            "results": [],
            "unattempted": list(scenario_ids),
            "summary": {},
        }
    else:
        manifest = json.loads(json.dumps(existing_manifest))
        if manifest.get("label") != FORMAL_LABEL:
            raise ValueError("resume artifact is not a formal M1.2B manifest")
        if manifest.get("run", {}).get("run_fingerprint") != fingerprint:
            raise ValueError("resume fingerprint does not match current run contract")
        if manifest.get("selection") != list(scenario_ids):
            raise ValueError("resume selection does not match")

    completed = {item["scenario_id"] for item in manifest["results"]}
    _refresh_manifest(manifest, library)
    _write_manifest(output_path, manifest)
    attempted_this_invocation = 0
    quota_exhausted = False

    for scenario_id in scenario_ids:
        if scenario_id in completed:
            continue
        if quota_exhausted:
            break
        if attempted_this_invocation and min_request_interval:
            sleeper(min_request_interval)
        attempted_this_invocation += 1
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
                    "observed_signals": observation.signals.to_dict(),
                    "provider_provenance": observation.provenance_dict(),
                    "comparison": evaluation.to_dict(),
                    "failure": None,
                }
            )
        except V2ExtractionError as error:
            result.update(
                {
                    "status": error.kind.value,
                    "observed_signals": None,
                    "provider_provenance": {
                        "provider": "Gemini",
                        "requested_model": extractor.model,
                    },
                    "comparison": None,
                    "failure": error.to_dict(),
                }
            )
            quota_exhausted = error.kind == V2ExtractionFailureKind.QUOTA_EXHAUSTED
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


def _refresh_manifest(manifest: Dict[str, Any], library: Mapping[str, Any]) -> None:
    completed = {item["scenario_id"] for item in manifest["results"]}
    manifest["unattempted"] = [
        scenario_id for scenario_id in manifest["selection"] if scenario_id not in completed
    ]
    manifest["summary"] = summarize_live_results(manifest["results"], library)
    manifest["summary"]["execution"]["unattempted"] = len(manifest["unattempted"])


def summarize_live_results(
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
    families = sorted(
        {family for item in library["scenarios"] for family in item["families"]}
    )
    family_summary: Dict[str, Any] = {}
    scenario_families = {
        item["id"]: set(item["families"]) for item in library["scenarios"]
    }
    for family in families:
        members = tuple(
            item
            for item in evaluations
            if family in scenario_families[item.scenario_id]
        )
        member_results = tuple(
            item for item in results if family in scenario_families[item["scenario_id"]]
        )
        family_summary[family] = {
            "execution": _execution_counts(member_results),
            "semantic": summarize_benchmark(members, memberships).to_dict(),
        }
    principles = sorted(
        {
            principle
            for item in library["scenarios"]
            for principle in item["constitutional_principles"]
        }
    )
    scenario_principles = {
        item["id"]: set(item["constitutional_principles"])
        for item in library["scenarios"]
    }
    constitutional_summary: Dict[str, Any] = {}
    for principle in principles:
        members = tuple(
            item for item in evaluations if principle in scenario_principles[item.scenario_id]
        )
        member_results = tuple(
            item for item in results if principle in scenario_principles[item["scenario_id"]]
        )
        constitutional_summary[principle] = {
            "execution": _execution_counts(member_results),
            "semantic": summarize_benchmark(members, memberships).to_dict(),
        }
    return {
        "execution": _execution_counts(results),
        "semantic": summarize_benchmark(evaluations, memberships).to_dict(),
        "by_family": family_summary,
        "by_constitutional_principle": constitutional_summary,
    }


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
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
