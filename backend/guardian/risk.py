"""Deterministic Risk Engine for Guardian Call."""

from typing import List, Tuple
from .models import RiskAssessment, RiskLevel, ScamSignals


class RiskEngine:
    """Evaluates structured scam signals into explainable risk assessments."""

    def evaluate(self, signals: ScamSignals) -> RiskAssessment:
        """Deterministically assess risk from conversation signals."""
        reasons: List[str] = []
        contributing: List[str] = []

        # 1. Evaluate primary credential theft vectors
        is_otp_theft = signals.otp_request and (signals.requested_action == "share_otp")
        is_password_theft = signals.password_request and (
            signals.requested_action in ("share_password", "reveal_password", "share_credentials")
        )
        is_remote_access = signals.remote_access_request
        is_transfer_request = signals.transfer_request

        # 2. Gather contextual risk indicators
        has_unverified_claim = bool(signals.identity_claim) and not signals.identity_verified
        if has_unverified_claim:
            reasons.append(f"Unverified identity claim: '{signals.identity_claim}'")
            contributing.append("unverified_identity_claim")

        if signals.financial_context:
            reasons.append("Financial context present")
            contributing.append("financial_context")

        if signals.urgency:
            reasons.append("Urgency or pressure tactics detected")
            contributing.append("urgency")

        if signals.secrecy_request:
            reasons.append("Caller requested secrecy or isolation")
            contributing.append("secrecy_request")

        # 3. Determine Risk Level based on explicit deterministic rules
        level: RiskLevel

        if is_otp_theft:
            level = RiskLevel.CRITICAL
            reasons.insert(0, "Caller explicitly requested user to reveal/share one-time passcode (OTP)")
            contributing.extend(["otp_request", "requested_action:share_otp"])

        elif is_password_theft:
            level = RiskLevel.CRITICAL
            reasons.insert(0, "Caller explicitly requested user to reveal account password/credentials")
            contributing.extend(["password_request", f"requested_action:{signals.requested_action}"])

        elif is_remote_access:
            if has_unverified_claim or signals.urgency or signals.financial_context:
                level = RiskLevel.CRITICAL
                reasons.insert(0, "Remote access requested under unverified or high-urgency context")
            else:
                level = RiskLevel.HIGH
                reasons.insert(0, "Caller requested remote device access")
            contributing.append("remote_access_request")

        elif is_transfer_request:
            if has_unverified_claim and (signals.urgency or signals.secrecy_request):
                level = RiskLevel.CRITICAL
                reasons.insert(0, "Urgent money transfer requested by unverified caller")
            elif has_unverified_claim or signals.urgency:
                level = RiskLevel.HIGH
                reasons.insert(0, "Money transfer requested in suspicious context")
            else:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "Money transfer requested")
            contributing.append("transfer_request")

        elif signals.otp_request and signals.requested_action != "share_otp":
            # Legitimate OTP flow (e.g. entering in official app, or general mention without sharing)
            if has_unverified_claim and signals.urgency:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "OTP mentioned with unverified caller and urgency (no sharing requested)")
            else:
                level = RiskLevel.NORMAL
                reasons.insert(0, "Legitimate OTP flow detected (user not asked to reveal code)")
            contributing.append("otp_request")
            if signals.requested_action:
                contributing.append(f"requested_action:{signals.requested_action}")

        elif has_unverified_claim and (signals.urgency or signals.financial_context):
            level = RiskLevel.SUSPICIOUS
            reasons.insert(0, "Suspicious combination of unverified identity and pressure/financial context")

        elif has_unverified_claim or signals.urgency or signals.financial_context or signals.secrecy_request:
            level = RiskLevel.SUSPICIOUS
            reasons.insert(0, "Isolated suspicious conversational indicators detected")

        else:
            level = RiskLevel.NORMAL
            reasons = ["No malicious manipulation signals detected"]
            contributing = ["benign"]

        # Deduplicate contributing signals while preserving order
        unique_contributing: List[str] = list(dict.fromkeys(contributing))

        return RiskAssessment(
            level=level,
            reasons=reasons,
            contributing_signals=unique_contributing,
        )
