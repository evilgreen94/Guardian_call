"""Structured domain events and event sink for Guardian Call."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Protocol


class EventType:
    """Canonical domain event types."""
    INPUT_RECEIVED = "INPUT_RECEIVED"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"
    SIGNAL_EXTRACTION_FAILED = "SIGNAL_EXTRACTION_FAILED"
    RISK_UPDATED = "RISK_UPDATED"
    CANARY_EVALUATION = "CANARY_EVALUATION"
    ACTION_ALLOWED = "ACTION_ALLOWED"
    ACTION_DENIED = "ACTION_DENIED"
    USER_WARNING = "USER_WARNING"
    TRUSTED_CONTACT_NOTIFIED = "TRUSTED_CONTACT_NOTIFIED"
    CALL_ENDED = "CALL_ENDED"


@dataclass(frozen=True)
class GuardianEvent:
    """Immutable domain event capturing backend state transitions."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


class EventSink(Protocol):
    """Protocol for event consumers and stream processors."""

    def emit(self, event: GuardianEvent) -> None:
        """Publish a domain event."""
        ...


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
