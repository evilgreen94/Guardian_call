"""Tests for Canary policy engine and authority layer."""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.canary import CanaryPolicy
from guardian.models import (
    ActionType,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
)


class TestCanaryPolicy(unittest.TestCase):
    """Test suite for Canary policy authorization."""

    def setUp(self) -> None:
        self.canary = CanaryPolicy()

    def _make_assessment(self, level: RiskLevel) -> RiskAssessment:
        return RiskAssessment(
            level=level,
            reasons=[f"Test reason for {level.value}"],
            contributing_signals=["test_signal"],
        )

    def test_warn_user_policy_for_all_risk_levels(self) -> None:
        """Verify WARN_USER decisions match explicit M0 policy:

        NORMAL -> DENY
        SUSPICIOUS -> DENY
        HIGH -> ALLOW
        CRITICAL -> ALLOW
        """
        # NORMAL -> DENY
        dec_normal = self.canary.evaluate_action(
            self._make_assessment(RiskLevel.NORMAL), ActionType.WARN_USER
        )
        self.assertEqual(dec_normal.decision, PolicyDecision.DENY)
        self.assertEqual(dec_normal.action, ActionType.WARN_USER)

        # SUSPICIOUS -> DENY
        dec_suspicious = self.canary.evaluate_action(
            self._make_assessment(RiskLevel.SUSPICIOUS), ActionType.WARN_USER
        )
        self.assertEqual(dec_suspicious.decision, PolicyDecision.DENY)
        self.assertEqual(dec_suspicious.action, ActionType.WARN_USER)

        # HIGH -> ALLOW
        dec_high = self.canary.evaluate_action(
            self._make_assessment(RiskLevel.HIGH), ActionType.WARN_USER
        )
        self.assertEqual(dec_high.decision, PolicyDecision.ALLOW)
        self.assertEqual(dec_high.action, ActionType.WARN_USER)

        # CRITICAL -> ALLOW
        dec_critical = self.canary.evaluate_action(
            self._make_assessment(RiskLevel.CRITICAL), ActionType.WARN_USER
        )
        self.assertEqual(dec_critical.decision, PolicyDecision.ALLOW)
        self.assertEqual(dec_critical.action, ActionType.WARN_USER)

    def test_share_transcript_strictly_denied_by_privacy_policy(self) -> None:
        """Privacy constraint: Transcripts must never be shared by default."""
        for level in RiskLevel:
            decision = self.canary.evaluate_action(
                self._make_assessment(level), ActionType.SHARE_TRANSCRIPT
            )
            self.assertEqual(
                decision.decision,
                PolicyDecision.DENY,
                f"Transcript sharing must be DENIED at level {level.value}",
            )

    def test_trusted_circle_escalation_requires_critical_risk(self) -> None:
        """Trusted circle escalation is only authorized for CRITICAL risk."""
        dec_crit = self.canary.evaluate_action(
            self._make_assessment(RiskLevel.CRITICAL), ActionType.NOTIFY_TRUSTED_CIRCLE
        )
        self.assertEqual(dec_crit.decision, PolicyDecision.ALLOW)

        for level in (RiskLevel.HIGH, RiskLevel.SUSPICIOUS, RiskLevel.NORMAL):
            decision = self.canary.evaluate_action(
                self._make_assessment(level), ActionType.NOTIFY_TRUSTED_CIRCLE
            )
            self.assertEqual(decision.decision, PolicyDecision.DENY)

    def test_end_call_preserves_user_autonomy(self) -> None:
        """Autonomy constraint: Autonomous unilateral termination is disallowed; must ask user."""
        for level in RiskLevel:
            decision = self.canary.evaluate_action(
                self._make_assessment(level), ActionType.END_CALL
            )
            self.assertEqual(
                decision.decision,
                PolicyDecision.ASK_USER,
                f"End call must return ASK_USER at level {level.value}",
            )

    def test_recommend_end_call_allowed_for_severe_risk(self) -> None:
        """Recommending end call is allowed for HIGH and CRITICAL."""
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.CRITICAL), ActionType.RECOMMEND_END_CALL
            ).decision,
            PolicyDecision.ALLOW,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.HIGH), ActionType.RECOMMEND_END_CALL
            ).decision,
            PolicyDecision.ALLOW,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.SUSPICIOUS), ActionType.RECOMMEND_END_CALL
            ).decision,
            PolicyDecision.DENY,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.NORMAL), ActionType.RECOMMEND_END_CALL
            ).decision,
            PolicyDecision.DENY,
        )


    def test_activate_scamtrap_policy_requires_high_or_critical_risk(self) -> None:
        """ScamTrap activation is authorized for HIGH and CRITICAL risk levels."""
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.CRITICAL), ActionType.ACTIVATE_SCAMTRAP
            ).decision,
            PolicyDecision.ALLOW,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.HIGH), ActionType.ACTIVATE_SCAMTRAP
            ).decision,
            PolicyDecision.ALLOW,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.SUSPICIOUS), ActionType.ACTIVATE_SCAMTRAP
            ).decision,
            PolicyDecision.DENY,
        )
        self.assertEqual(
            self.canary.evaluate_action(
                self._make_assessment(RiskLevel.NORMAL), ActionType.ACTIVATE_SCAMTRAP
            ).decision,
            PolicyDecision.DENY,
        )


if __name__ == "__main__":
    unittest.main()
