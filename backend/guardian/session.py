"""In-memory multi-turn call session state for Guardian Call.

A CallSession accumulates the raw turns of a single call so the local keyword
gate (guardian.signals.should_escalate_to_gemini) can be evaluated against
everything said so far in the call, not an isolated turn in a vacuum. See
should_escalate_to_gemini's docstring for why single-turn gating alone lets a
scammer who spreads signals thin across turns slip past every individual gate
check.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .signals import should_escalate_to_gemini

# ponytail: fixed cadence, no per-session tuning. Make it a constructor param
# if a scenario ever needs a different "check in at least every N turns" rate.
FORCE_ESCALATE_EVERY_N_TURNS = 5


@dataclass
class CallSession:
    """Accumulated state for one call, kept in memory for the life of the process."""

    session_id: str
    turns: List[str] = field(default_factory=list)
    turns_since_last_escalation: int = 0

    @property
    def turn_index(self) -> int:
        """0-based index the *next* turn will receive."""
        return len(self.turns)

    def register_turn(self, text: str) -> bool:
        """Record a new turn and decide whether it should escalate to Gemini.

        Escalates when:
        - it's the session's first turn (mandatory baseline read), or
        - the transcript accumulated so far (every turn said in the call, not
          just this one) contains risk vocabulary -- so once a signal has
          appeared anywhere in the call, later keyword-free turns keep
          escalating instead of going dark again, or
        - FORCE_ESCALATE_EVERY_N_TURNS turns have passed since the last
          escalation (periodic safety net for a scammer who never says a
          single recognizable word).
        """
        is_first_turn = self.turn_index == 0
        self.turns.append(text)

        accumulated_transcript = " ".join(self.turns)
        escalate = should_escalate_to_gemini(accumulated_transcript, is_first_turn=is_first_turn)

        if not escalate and self.turns_since_last_escalation + 1 >= FORCE_ESCALATE_EVERY_N_TURNS:
            escalate = True

        self.turns_since_last_escalation = 0 if escalate else self.turns_since_last_escalation + 1
        return escalate


class CallSessionStore:
    """Process-local registry of active CallSessions, keyed by session_id.

    ponytail: plain dict, no eviction/expiry/persistence -- fine for a
    hackathon-scale single-process demo. Add TTL cleanup or a real store if
    sessions ever need to survive a process restart or outlive a demo call.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, CallSession] = {}

    def get_or_create(self, session_id: str) -> CallSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = CallSession(session_id=session_id)
        return self._sessions[session_id]

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


if __name__ == "__main__":
    # ponytail: smallest runnable self-check for the accumulation + periodic-force logic.
    s = CallSession(session_id="demo")
    assert s.register_turn("Buenas tardes.") is True  # first turn always escalates
    assert s.register_turn("Todo en orden por su parte.") is False  # no keywords, not forced yet
    assert s.register_turn("Le llamamos de su banco.") is True  # soft identity claim
    assert s.register_turn("Confírmenos que sigue ahí.") is True  # accumulated transcript still has "banco"
    print("session.py self-check OK")
