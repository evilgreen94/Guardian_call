"""Tests for RiskEngine deterministic risk evaluation."""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.models import RiskLevel, ScamSignals
from guardian.risk import RiskEngine
from guardian.signals import create_signals


class TestRiskEngine(unittest.TestCase):
    """Test suite for deterministic, explainable risk assessment."""

    def setUp(self) -> None:
        self.engine = RiskEngine()

    def test_canonical_m0_otp_fraud_scenario(self) -> None:
        """Verify M0 canonical synthetic signal triggers CRITICAL risk with explainable reasons."""
        signals = create_signals(
            otp_request=True,
            requested_action="share_otp",
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
            financial_context=True,
        )
        assessment = self.engine.evaluate(signals)

        self.assertEqual(assessment.level, RiskLevel.CRITICAL)
        self.assertIn("otp_request", assessment.contributing_signals)
        self.assertIn("requested_action:share_otp", assessment.contributing_signals)
        self.assertIn("unverified_identity_claim", assessment.contributing_signals)
        self.assertIn("urgency", assessment.contributing_signals)
        self.assertIn("financial_context", assessment.contributing_signals)

        # Verify explicit explainability in reasons
        reasons_text = " ".join(assessment.reasons).lower()
        self.assertIn("otp", reasons_text)
        self.assertIn("bank", reasons_text)
        self.assertIn("urgency", reasons_text)

    def test_legitimate_otp_flow_does_not_trigger_critical(self) -> None:
        """Verify legitimate OTP guidance (e.g. enter in official app) is NOT marked CRITICAL."""
        # Case A: Benign guidance to enter OTP in app
        signals_legit = create_signals(
            otp_request=True,
            requested_action="enter_in_app",
            identity_claim="bank",
            identity_verified=True,
            financial_context=True,
        )
        assessment_legit = self.engine.evaluate(signals_legit)
        self.assertNotEqual(assessment_legit.level, RiskLevel.CRITICAL)
        self.assertEqual(assessment_legit.level, RiskLevel.NORMAL)

        # Case B: Unverified caller mentions OTP but doesn't ask user to share it
        signals_mention = create_signals(
            otp_request=True,
            requested_action="enter_in_app",
            identity_claim="bank",
            identity_verified=False,
            urgency=True,
        )
        assessment_mention = self.engine.evaluate(signals_mention)
        self.assertNotEqual(assessment_mention.level, RiskLevel.CRITICAL)
        self.assertEqual(assessment_mention.level, RiskLevel.SUSPICIOUS)

    def test_password_theft_triggers_critical(self) -> None:
        """Verify requesting password revelation triggers CRITICAL."""
        signals = create_signals(
            password_request=True,
            requested_action="share_password",
            identity_claim="tech_support",
            identity_verified=False,
            urgency=True,
        )
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.CRITICAL)
        self.assertTrue(any("password" in r.lower() for r in assessment.reasons))

    def test_remote_access_with_urgency_triggers_critical(self) -> None:
        """Verify remote access under pressure triggers CRITICAL."""
        signals = create_signals(
            remote_access_request=True,
            identity_claim="tech_support",
            identity_verified=False,
            urgency=True,
        )
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.CRITICAL)

    def test_urgent_unverified_transfer_triggers_critical(self) -> None:
        """Verify urgent money transfer requested by unverified caller triggers CRITICAL."""
        signals = create_signals(
            transfer_request=True,
            identity_claim="police",
            identity_verified=False,
            urgency=True,
            secrecy_request=True,
        )
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.CRITICAL)

    def test_benign_conversation_returns_normal_risk(self) -> None:
        """Verify benign conversation with no attack vectors returns NORMAL."""
        signals = ScamSignals()
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.NORMAL)
        self.assertTrue(len(assessment.reasons) > 0)
        self.assertIn("No malicious manipulation signals detected", assessment.reasons[0])

    def test_all_assessments_have_explicit_reasons(self) -> None:
        """Explainability constraint: All risk assessments must provide non-empty explicit reasons."""
        test_cases = [
            ScamSignals(),
            create_signals(urgency=True),
            create_signals(financial_context=True, identity_claim="bank", identity_verified=False),
            create_signals(otp_request=True, requested_action="share_otp"),
            create_signals(remote_access_request=True),
        ]
        for signals in test_cases:
            assessment = self.engine.evaluate(signals)
            self.assertIsInstance(assessment.reasons, list)
            self.assertGreater(len(assessment.reasons), 0, "Reasons list must not be empty")
            for reason in assessment.reasons:
                self.assertIsInstance(reason, str)
                self.assertGreater(len(reason.strip()), 0, "Reason string must not be blank")


    def test_cloud_storage_deletion_threat_triggers_high_or_critical(self) -> None:
        """Verify cloud storage full / data deletion threat triggers HIGH or CRITICAL risk."""
        # Case A: Urgent storage deletion threat -> HIGH
        signals_high = create_signals(
            service_cancellation_threat=True,
            urgency=True,
            identity_claim="cloud_storage",
        )
        assessment_high = self.engine.evaluate(signals_high)
        self.assertIn(assessment_high.level, (RiskLevel.HIGH, RiskLevel.CRITICAL))
        self.assertTrue(any("almacenamiento" in r.lower() or "storage" in r.lower() or "cancelaci" in r.lower() for r in assessment_high.reasons))

        # Case B: Storage deletion threat with payment link or transfer request -> CRITICAL
        signals_critical = create_signals(
            service_cancellation_threat=True,
            urgency=True,
            unverified_link_prompt=True,
            financial_context=True,
            identity_claim="cloud_storage",
        )
        assessment_critical = self.engine.evaluate(signals_critical)
        self.assertEqual(assessment_critical.level, RiskLevel.CRITICAL)
        self.assertIn("service_cancellation_threat", assessment_critical.contributing_signals)

    def test_fake_subscription_fee_claim_triggers_high_or_critical(self) -> None:
        """Verify fake subscription fee or unexpected charge claim triggers HIGH or CRITICAL risk."""
        signals = create_signals(
            subscription_fee_claim=True,
            urgency=True,
            unverified_link_prompt=True,
        )
        assessment = self.engine.evaluate(signals)
        self.assertIn(assessment.level, (RiskLevel.HIGH, RiskLevel.CRITICAL))
        self.assertIn("subscription_fee_claim", assessment.contributing_signals)

    def test_suspicious_domain_phishing_records_contributing_signal(self) -> None:
        """Verify the suspicious-domain phishing branch names its own deciding signal."""
        signals = create_signals(
            suspicious_domain=True,
            unverified_link_prompt=True,
            sender_email="alert@importican.de",
        )
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.CRITICAL)
        self.assertIn("suspicious_domain", assessment.contributing_signals)
        self.assertIn("unverified_link_prompt", assessment.contributing_signals)

    def test_legitimate_verified_otp_flow_does_not_leak_unrelated_reasons(self) -> None:
        """Explainability: a NORMAL verdict must not carry contextual reasons that didn't drive it."""
        signals = create_signals(
            otp_request=True,
            requested_action="enter_in_app",
            identity_claim="bank",
            identity_verified=True,
            financial_context=True,
        )
        assessment = self.engine.evaluate(signals)
        self.assertEqual(assessment.level, RiskLevel.NORMAL)
        reasons_text = " ".join(assessment.reasons).lower()
        self.assertNotIn("financial context present", reasons_text)
        self.assertNotIn("financial_context", assessment.contributing_signals)


if __name__ == "__main__":
    unittest.main()
