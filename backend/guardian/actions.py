"""Action handlers for authorized Guardian Call interventions."""

from typing import List, Optional
from .events import EventType, GuardianEvent, InMemoryEventSink
from .models import ActionType, CanaryDecision, PolicyDecision, RiskAssessment, RiskLevel


def format_warning_directives(risk_assessment: RiskAssessment) -> List[str]:
    """Generate concise, actionable warning directives tailored to the risk assessment."""
    directives: List[str] = []

    signals = set(risk_assessment.contributing_signals)

    if "otp_request" in signals or any("otp" in r.lower() for r in risk_assessment.reasons):
        directives.append("NO DIGA ESE CÓDIGO")
    if "password_request" in signals or any("password" in r.lower() for r in risk_assessment.reasons):
        directives.append("NO COMPARTA SU CONTRASEÑA")
    if "transfer_request" in signals or any("transfer" in r.lower() for r in risk_assessment.reasons):
        directives.append("NO REALICE TRANSFERENCIAS")
    if "remote_access_request" in signals or any("remote" in r.lower() for r in risk_assessment.reasons):
        directives.append("NO PERMITA ACCESO REMOTO A SU DISPOSITIVO")

    if not directives:
        directives.append("VERIFIQUE LA IDENTIDAD POR OTRO MEDIO")

    return directives


def execute_warning_action(
    canary_decision: CanaryDecision,
    risk_assessment: RiskAssessment,
    event_sink: InMemoryEventSink,
) -> Optional[GuardianEvent]:
    """Execute the warn_user action if explicitly authorized by Canary."""
    # Strict Canary check: Consequential action must not bypass Canary authorization
    if canary_decision.action != ActionType.WARN_USER:
        raise ValueError(f"Expected action WARN_USER, received {canary_decision.action}")

    if canary_decision.decision != PolicyDecision.ALLOW:
        raise PermissionError(
            f"Cannot execute warn_user: Canary decision is {canary_decision.decision.value} ({canary_decision.reason})"
        )

    headline = "POSIBLE ESTAFA" if risk_assessment.level in (RiskLevel.CRITICAL, RiskLevel.HIGH) else "AVISO DE SEGURIDAD"
    directives = format_warning_directives(risk_assessment)

    warning_payload = {
        "headline": headline,
        "directives": directives,
        "severity": risk_assessment.level.value,
        "reasons": list(risk_assessment.reasons),
        "authorized_by": canary_decision.to_dict(),
    }

    warning_event = GuardianEvent(
        event_type=EventType.USER_WARNING,
        payload=warning_payload,
    )

    event_sink.emit(warning_event)
    return warning_event
