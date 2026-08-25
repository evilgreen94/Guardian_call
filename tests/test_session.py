"""Tests for CallSession multi-turn gate accumulation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.session import CallSession, CallSessionStore


class TestCallSession(unittest.TestCase):
    """Test suite for accumulated-transcript gating and the periodic safety net."""

    def test_first_turn_always_escalates(self) -> None:
        session = CallSession(session_id="s1")
        self.assertTrue(session.register_turn("Hola, buenas tardes."))
        self.assertEqual(session.turn_index, 1)

    def test_signal_seen_earlier_keeps_later_keyword_free_turns_escalating(self) -> None:
        """Once a soft signal appears anywhere in the call, later silent turns still escalate."""
        session = CallSession(session_id="s2")
        self.assertTrue(session.register_turn("Le llamamos de su banco."))  # first turn, soft identity claim
        self.assertTrue(
            session.register_turn("Todo va bien por su parte, ¿verdad?")
        )  # no keyword in this turn alone, but "banco" is still in the accumulated transcript

    def test_fully_silent_call_forces_periodic_escalation(self) -> None:
        """A scammer who never says a single recognizable word still gets checked periodically."""
        session = CallSession(session_id="s3")
        benign_turns = [
            "Hola, buenas tardes.",  # turn 1: first turn, always escalates
            "Sigo aquí escuchando.",  # turn 2: silent, skipped
            "De acuerdo, entendido.",  # turn 3: silent, skipped
            "Continuemos con la conversación.",  # turn 4: silent, skipped
            "Todo parece tranquilo.",  # turn 5: silent, skipped
            "Nos vemos pronto.",  # turn 6: 5th silent turn since last escalation -> forced
        ]
        results = [session.register_turn(t) for t in benign_turns]
        self.assertEqual(
            results,
            [True, False, False, False, False, True],
            "expected only the first turn and the periodic-force turn to escalate",
        )

    def test_store_reuses_session_across_calls_and_reset_clears_it(self) -> None:
        store = CallSessionStore()
        first = store.get_or_create("call-1")
        first.register_turn("Hola.")
        same = store.get_or_create("call-1")
        self.assertIs(first, same)
        self.assertEqual(same.turn_index, 1)

        store.reset("call-1")
        fresh = store.get_or_create("call-1")
        self.assertEqual(fresh.turn_index, 0)


if __name__ == "__main__":
    unittest.main()
