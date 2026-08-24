"""Opt-in local evidence records for manual experimental V2 sessions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .extractor_v2 import (
    PROMPT_REVISION,
    PROMPT_SHA256,
    SCHEMA_REVISION,
    SCHEMA_SHA256,
    GeminiV2Observation,
    V2ExtractionError,
    sdk_version,
)


MANUAL_LABEL = "MANUAL EXPLORATORY SESSION // NOT FORMAL BENCHMARK EVIDENCE"
MANUAL_MODE = "MANUAL_LIVE_V2_EXPLORATION"
VERDICTS = frozenset({"pass", "false_positive", "false_negative", "ambiguous"})

_PROHIBITED_PATTERNS = (
    re.compile(r"(?i)authorization\s*:\s*bearer\s+\S+"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    re.compile(r"(?<!\d)\d{4,8}(?!\d)"),
    re.compile(
        r"(?i)\b(?:password|contrase(?:n|ñ)a|pin|cvv|cvc|otp|recovery code|"
        r"seed phrase|private key|api key)\b\s*(?:is|es|:|=)\s*\S+"
    ),
)


class ManualPersistenceRefused(ValueError):
    """Raised when a turn does not meet synthetic-only persistence controls."""


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def assert_safe_for_manual_persistence(text: str) -> None:
    """Reject obvious secret values; operator synthetic-only policy remains required."""
    if not isinstance(text, str) or not text.strip():
        raise ManualPersistenceRefused("empty text cannot be persisted")
    if any(pattern.search(text) for pattern in _PROHIBITED_PATTERNS):
        raise ManualPersistenceRefused("input resembles prohibited sensitive material")


@dataclass(frozen=True)
class ManualSessionPaths:
    jsonl: Path
    text: Optional[Path] = None


class ManualSessionRecorder:
    """Append-only manual evidence writer with no benchmark dependencies."""

    def __init__(
        self,
        *,
        paths: ManualSessionPaths,
        allowed_root: Path,
        session_id: str,
        git_commit: str,
        requested_model: str,
        clock: Any = utc_timestamp,
    ) -> None:
        _require_under(paths.jsonl, allowed_root)
        if paths.text is not None:
            _require_under(paths.text, allowed_root)
        self.paths = paths
        self.session_id = session_id
        self.git_commit = git_commit
        self.requested_model = requested_model
        self.clock = clock
        self.paths.jsonl.parent.mkdir(parents=True, exist_ok=True)
        if self.paths.text is not None:
            self.paths.text.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        record = {
            "record_type": "session_start",
            "label": MANUAL_LABEL,
            "timestamp_utc": self.clock(),
            "session_id": self.session_id,
            "simulator_mode": MANUAL_MODE,
            "git_commit": self.git_commit,
            "provider": "Gemini",
            "requested_model": self.requested_model,
            "sdk_version": sdk_version(),
            "prompt_revision": PROMPT_REVISION,
            "prompt_sha256": PROMPT_SHA256,
            "schema_revision": SCHEMA_REVISION,
            "schema_sha256": SCHEMA_SHA256,
            "synthetic_input_acknowledged": True,
        }
        self._append(record)
        self._append_text(
            f"{MANUAL_LABEL}\nSESSION {self.session_id}\nMODEL {self.requested_model}\n"
        )

    def record_turn(
        self,
        *,
        turn: int,
        text: str,
        observation: Optional[GeminiV2Observation] = None,
        error: Optional[V2ExtractionError] = None,
    ) -> None:
        assert_safe_for_manual_persistence(text)
        if (observation is None) == (error is None):
            raise ValueError("provide exactly one observation or error")
        record: Dict[str, Any] = {
            "record_type": "turn",
            "label": MANUAL_LABEL,
            "timestamp_utc": self.clock(),
            "session_id": self.session_id,
            "turn": turn,
            "synthetic_input": text,
            "status": "EXTRACTION_SUCCEEDED" if observation else error.kind.value,
            "observed_signals": observation.signals.to_dict() if observation else None,
            "provider_provenance": (
                observation.provenance_dict()
                if observation
                else {"provider": "Gemini", "requested_model": self.requested_model}
            ),
            "failure": error.to_dict() if error else None,
        }
        self._append(record)
        rendered = [f"\nTURN {turn:03d}", "SYNTHETIC INPUT", text, record["status"]]
        if observation:
            rendered.append(json.dumps(observation.signals.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            rendered.append(json.dumps(record["failure"], ensure_ascii=False, sort_keys=True))
        self._append_text("\n".join(rendered) + "\n")

    def record_verdict(self, *, turn: int, verdict: str) -> None:
        if verdict not in VERDICTS:
            raise ValueError(f"unknown operator verdict: {verdict}")
        self._append(
            {
                "record_type": "operator_verdict",
                "label": MANUAL_LABEL,
                "timestamp_utc": self.clock(),
                "session_id": self.session_id,
                "turn": turn,
                "verdict": verdict,
                "evidence_class": "manual_operator_annotation",
            }
        )
        self._append_text(f"VERDICT TURN {turn:03d} // {verdict}\n")

    def end(self, *, turns: int) -> None:
        self._append(
            {
                "record_type": "session_end",
                "label": MANUAL_LABEL,
                "timestamp_utc": self.clock(),
                "session_id": self.session_id,
                "turns": turns,
            }
        )
        self._append_text(f"SESSION END // TURNS {turns}\n")

    def _append(self, record: Mapping[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.paths.jsonl.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(payload + "\n")

    def _append_text(self, value: str) -> None:
        if self.paths.text is None:
            return
        with self.paths.text.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(value)


def read_jsonl(path: Path) -> list[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _require_under(path: Path, allowed_root: Path) -> None:
    resolved = path.resolve()
    root = allowed_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"manual evidence path must be a file under {root}")
