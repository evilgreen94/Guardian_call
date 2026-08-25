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
        is_service_threat = signals.service_cancellation_threat
        is_subscription_claim = signals.subscription_fee_claim
        is_unverified_link = signals.unverified_link_prompt
        is_suspicious_domain = signals.suspicious_domain
        is_countdown_timer = signals.countdown_timer
        is_special_offer = signals.special_offer_hook

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

        if signals.prompt_injection_attempt:
            level = RiskLevel.CRITICAL
            reasons.insert(0, f"Intento de inyección de prompt o sobreescritura de instrucciones de seguridad detectado (Tipo: {signals.injection_type or 'direct_override'})")
            contributing.append("prompt_injection_attempt")

        elif is_otp_theft:
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

        elif is_suspicious_domain and (is_service_threat or is_subscription_claim or is_unverified_link or signals.urgency or is_countdown_timer or is_special_offer):
            level = RiskLevel.CRITICAL
            contributing.append("suspicious_domain")
            if is_service_threat:
                contributing.append("service_cancellation_threat")
            if is_subscription_claim:
                contributing.append("subscription_fee_claim")
            if is_unverified_link:
                contributing.append("unverified_link_prompt")
            if is_countdown_timer:
                contributing.append("countdown_timer")
            if is_special_offer:
                contributing.append("special_offer_hook")
            reasons.insert(0, f"Correo electrónico o dominio de remitente falsificado/sospechoso ({signals.sender_email or 'desconocido'}) combinado con táctica de phishing")

        elif is_service_threat:
            contributing.append("service_cancellation_threat")
            if is_unverified_link or is_transfer_request or signals.financial_context or is_otp_theft or is_countdown_timer or is_special_offer or is_suspicious_domain:
                level = RiskLevel.CRITICAL
                if is_unverified_link:
                    contributing.append("unverified_link_prompt")
                if is_countdown_timer:
                    contributing.append("countdown_timer")
                if is_special_offer:
                    contributing.append("special_offer_hook")
                reasons.insert(0, "Intento de estafa/phishing de almacenamiento o servicio exigiendo pago o datos de acceso bajo amenaza de pérdida de información")
            elif signals.urgency or has_unverified_claim:
                level = RiskLevel.HIGH
                reasons.insert(0, "Amenaza de suspensión de servicio o pérdida de almacenamiento en la nube detectada con tácticas de urgencia")
            else:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "Notificación sospechosa de cancelación de servicio o espacio de almacenamiento lleno")

        elif is_subscription_claim:
            contributing.append("subscription_fee_claim")
            if is_unverified_link or is_transfer_request or is_otp_theft or is_countdown_timer or is_suspicious_domain:
                level = RiskLevel.CRITICAL
                if is_unverified_link:
                    contributing.append("unverified_link_prompt")
                if is_countdown_timer:
                    contributing.append("countdown_timer")
                reasons.insert(0, "Cobro o renovación de suscripción imprevista redirigiendo a enlace o pago sospechoso")
            elif signals.urgency or has_unverified_claim:
                level = RiskLevel.HIGH
                reasons.insert(0, "Notificación sospechosa de cobro o renovación de suscripción imprevista con urgencia")
            else:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "Reclamo de cobro o suscripción no reconocida")

        elif is_unverified_link:
            contributing.append("unverified_link_prompt")
            if signals.urgency or has_unverified_claim or signals.financial_context:
                level = RiskLevel.HIGH
                reasons.insert(0, "Enlace externo no verificado en contexto urgente o financiero sospechoso")
            else:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "Solicitud de clic en enlace externo no verificado")

        elif signals.otp_request and signals.requested_action != "share_otp":
            # Legitimate OTP flow (e.g. entering in official app, or general mention without sharing)
            if has_unverified_claim and signals.urgency:
                level = RiskLevel.SUSPICIOUS
                reasons.insert(0, "OTP mentioned with unverified caller and urgency (no sharing requested)")
            else:
                level = RiskLevel.NORMAL
                reasons.insert(0, "Legitimate OTP flow detected (user not asked to reveal code)")
            contributing.append("otp_request")

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

        # Explainability guarantee: a NORMAL verdict must not carry unrelated
        # contextual reasons/signals gathered before a branch overrode them
        # (e.g. "Financial context present" surviving a legitimate OTP flow).
        if level == RiskLevel.NORMAL:
            reasons = [reasons[0]] if reasons else ["No malicious manipulation signals detected"]
            contextual = {"unverified_identity_claim", "financial_context", "urgency", "secrecy_request"}
            contributing = [c for c in contributing if c not in contextual] or ["benign"]

        # Deduplicate contributing signals while preserving order
        unique_contributing: List[str] = list(dict.fromkeys(contributing))

        return RiskAssessment(
            level=level,
            reasons=reasons,
            contributing_signals=unique_contributing,
        )
