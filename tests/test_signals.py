"""Tests for ScamSignals models and validation helpers."""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.models import ScamSignals
from guardian.signals import create_signals, signals_from_dict, should_escalate_to_gemini


class TestScamSignals(unittest.TestCase):
    """Test suite for ScamSignals dataclass and signal creation."""

    def test_default_values(self) -> None:
        """Verify default signals are all falsy/None."""
        signals = ScamSignals()
        self.assertIsNone(signals.identity_claim)
        self.assertFalse(signals.identity_verified)
        self.assertFalse(signals.financial_context)
        self.assertFalse(signals.urgency)
        self.assertFalse(signals.secrecy_request)
        self.assertFalse(signals.otp_request)
        self.assertFalse(signals.password_request)
        self.assertFalse(signals.transfer_request)
        self.assertFalse(signals.remote_access_request)
        self.assertIsNone(signals.requested_action)

    def test_create_signals_normalization(self) -> None:
        """Verify strings are normalized (trimmed and lowercased)."""
        signals = create_signals(
            identity_claim="  BANK  ",
            requested_action=" SHARE_OTP  ",
            otp_request=True,
            urgency=True,
        )
        self.assertEqual(signals.identity_claim, "bank")
        self.assertEqual(signals.requested_action, "share_otp")
        self.assertTrue(signals.otp_request)
        self.assertTrue(signals.urgency)
        self.assertFalse(signals.identity_verified)

    def test_signals_from_dict_and_to_dict(self) -> None:
        """Verify round-trip serialization and deserialization."""
        raw_dict = {
            "identity_claim": "tech_support",
            "identity_verified": False,
            "financial_context": True,
            "urgency": True,
            "secrecy_request": False,
            "otp_request": True,
            "password_request": False,
            "transfer_request": False,
            "remote_access_request": True,
            "requested_action": "share_otp",
        }
        signals = signals_from_dict(raw_dict)
        self.assertEqual(signals.identity_claim, "tech_support")
        self.assertTrue(signals.remote_access_request)
        self.assertTrue(signals.otp_request)
        self.assertEqual(signals.requested_action, "share_otp")

        serialized = signals.to_dict()
        self.assertEqual(serialized["identity_claim"], "tech_support")
        self.assertEqual(serialized["remote_access_request"], True)
        self.assertEqual(serialized["requested_action"], "share_otp")

    def test_frozen_immutability(self) -> None:
        """Verify ScamSignals instances cannot be modified after creation."""
        signals = ScamSignals(otp_request=True)
        with self.assertRaises(AttributeError):
            signals.otp_request = False  # type: ignore[misc]


class TestShouldEscalateToGemini(unittest.TestCase):
    """Test suite for the local keyword gate in front of Gemini calls."""

    def test_first_turn_always_escalates(self) -> None:
        """First turn escalates even with zero risk vocabulary (baseline read)."""
        self.assertTrue(should_escalate_to_gemini("Hola, buenas tardes.", is_first_turn=True))

    def test_keyword_free_later_turn_is_skipped(self) -> None:
        """A benign later turn with no risk vocabulary at all does not escalate."""
        self.assertFalse(
            should_escalate_to_gemini("Hola, buenas tardes, ¿qué tal está?", is_first_turn=False)
        )

    def test_soft_identity_claim_escalates_later_turn(self) -> None:
        """A soft identity claim alone ('banco') is enough to open the gate."""
        self.assertTrue(
            should_escalate_to_gemini("Le llamamos de su banco.", is_first_turn=False)
        )

    def test_soft_otp_wording_escalates_later_turn(self) -> None:
        """Spanish 'código' opens the gate even without the English 'otp' keyword."""
        self.assertTrue(
            should_escalate_to_gemini("Dígame el código que le acaba de llegar.", is_first_turn=False)
        )

    def test_empty_later_turn_does_not_escalate(self) -> None:
        """Empty/whitespace-only later turns never escalate."""
        self.assertFalse(should_escalate_to_gemini("   ", is_first_turn=False))


if __name__ == "__main__":
    unittest.main()
