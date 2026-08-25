"""Structured domain events and event sink for Guardian Call."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


class EventType:
    """Canonical domain event types."""
    INPUT_RECEIVED = "INPUT_RECEIVED"
    GEMMA_GUARDRAIL_EVALUATED = "GEMMA_GUARDRAIL_EVALUATED"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    GATE_ESCALATED = "GATE_ESCALATED"
    GATE_SKIPPED = "GATE_SKIPPED"
    IMAGE_RECEIVED = "IMAGE_RECEIVED"
    IMAGE_PROCESSED_OCR = "IMAGE_PROCESSED_OCR"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    SIGNAL_EXTRACTION_FAILED = "SIGNAL_EXTRACTION_FAILED"
    RISK_UPDATED = "RISK_UPDATED"
    CANARY_EVALUATION = "CANARY_EVALUATION"
    ACTION_ALLOWED = "ACTION_ALLOWED"
    ACTION_DENIED = "ACTION_DENIED"
    USER_WARNING = "USER_WARNING"
    TRUSTED_CONTACT_NOTIFIED = "TRUSTED_CONTACT_NOTIFIED"
    SCAMTRAP_ACTIVATED = "SCAMTRAP_ACTIVATED"
    INTELLIGENCE_EXTRACTED = "INTELLIGENCE_EXTRACTED"
    CALL_ENDED = "CALL_ENDED"


@dataclass(frozen=True)
class GuardianEvent:
    """Immutable domain event capturing backend state transitions."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)


class InMemoryEventSink:
    """In-memory event sink for testing, debugging, and local visualizer feeds."""

    def __init__(self) -> None:
        self._events: List[GuardianEvent] = []

    def emit(self, event: GuardianEvent) -> None:
        """Append an event to the in-memory stream."""
        self._events.append(event)

    def get_events(self) -> List[GuardianEvent]:
        """Retrieve all emitted events in chronological order."""
        return list(self._events)

    def get_events_by_type(self, event_type: str) -> List[GuardianEvent]:
        """Filter events by event type."""
        return [e for e in self._events if e.event_type == event_type]

    def clear(self) -> None:
        """Clear all stored events."""
        self._events.clear()


class JsonFileEventSink:
    """Persistent JSON lines file sink for auditing all domain events to disk."""

    def __init__(self, file_path: str = "data/audit_log.jsonl") -> None:
        import os
        from pathlib import Path
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._in_memory = InMemoryEventSink()

    def emit(self, event: GuardianEvent) -> None:
        """Emit event to memory and append to persistent JSONL file."""
        import json
        self._in_memory.emit(event)
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception:
            pass

    def get_events(self) -> List[GuardianEvent]:
        return self._in_memory.get_events()


def get_audit_history(file_path: str = "data/audit_log.jsonl", limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve persistent audit log history from disk."""
    import json
    from pathlib import Path

    p = Path(file_path)
    if not p.exists():
        return []

    events = []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        events.append(json.loads(line_str))
                    except Exception:
                        pass
    except Exception:
        return []

    return events[-limit:] if len(events) >= limit else events
