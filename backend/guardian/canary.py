"""Deterministic Canary Policy Engine for Guardian Call."""

from .models import (
    ActionType,
    CanaryDecision,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
)


class CanaryPolicy:
    """Policy and authority layer governing consequential actions."""

    def evaluate_action(
        self,
        risk_assessment: RiskAssessment,
        action: ActionType,
    ) -> CanaryDecision:
        """Evaluate whether a proposed action is allowed under the current risk assessment."""
        risk_level = risk_assessment.level

        if action == ActionType.WARN_USER:
            # Explicit M0 Policy for WARN_USER:
            # NORMAL -> DENY
            # SUSPICIOUS -> DENY
            # HIGH -> ALLOW
            # CRITICAL -> ALLOW
            if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.ALLOW,
                    reason=f"{risk_level.value} scam risk detected; user warning authorized.",
                    risk_level=risk_level,
                )
            elif risk_level == RiskLevel.SUSPICIOUS:
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.DENY,
                    reason="Suspicious risk does not authorize intrusive user warning in M0 policy.",
                    risk_level=risk_level,
                )
            else:  # NORMAL
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.DENY,
                    reason="Normal risk level; user warning denied.",
                    risk_level=risk_level,
                )

        elif action == ActionType.SHARE_TRANSCRIPT:
            # Privacy constraint: Transcripts are never shared by default
            return CanaryDecision(
                action=action,
                decision=PolicyDecision.DENY,
                reason="Transcript sharing denied by default privacy policy.",
                risk_level=risk_level,
            )

        elif action == ActionType.NOTIFY_TRUSTED_CIRCLE:
            # Trusted Circle escalation is restricted to CRITICAL emergencies
            if risk_level == RiskLevel.CRITICAL:
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.ALLOW,
                    reason="Critical scam risk detected; trusted circle notification authorized.",
                    risk_level=risk_level,
                )
            return CanaryDecision(
                action=action,
                decision=PolicyDecision.DENY,
                reason="Trusted circle notification requires CRITICAL risk.",
                risk_level=risk_level,
            )

        elif action == ActionType.RECOMMEND_END_CALL:
            if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.ALLOW,
                    reason="High or Critical scam risk detected; call termination recommendation authorized.",
                    risk_level=risk_level,
                )
            return CanaryDecision(
                action=action,
                decision=PolicyDecision.DENY,
                reason="Call termination recommendation denied for low-risk interaction.",
                risk_level=risk_level,
            )

        elif action == ActionType.END_CALL:
            # Autonomy constraint: Autonomous unilateral termination is disallowed; must ask user
            return CanaryDecision(
                action=action,
                decision=PolicyDecision.ASK_USER,
                reason="User autonomy policy requires asking user before terminating call.",
                risk_level=risk_level,
            )

        elif action == ActionType.ACTIVATE_SCAMTRAP:
            # ScamTrap counter-deception authorized under HIGH or CRITICAL risk
            if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                return CanaryDecision(
                    action=action,
                    decision=PolicyDecision.ALLOW,
                    reason=f"ScamTrap counter-deception authorized under {risk_level.value} risk.",
                    risk_level=risk_level,
                )
            return CanaryDecision(
                action=action,
                decision=PolicyDecision.DENY,
                reason=f"ScamTrap counter-deception requires HIGH or CRITICAL risk (current: {risk_level.value}).",
                risk_level=risk_level,
            )

        # Fallback default: Deny any unhandled action type
        return CanaryDecision(
            action=action,
            decision=PolicyDecision.DENY,
            reason=f"Action '{action.value}' not authorized by default policy.",
            risk_level=risk_level,
        )
