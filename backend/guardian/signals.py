"""Signal helpers and validation for Guardian Call."""

from typing import Any, Dict, Optional
from .models import ScamSignals


def create_signals(
    identity_claim: Optional[str] = None,
    identity_verified: bool = False,
    financial_context: bool = False,
    urgency: bool = False,
    secrecy_request: bool = False,
    otp_request: bool = False,
    password_request: bool = False,
    transfer_request: bool = False,
    remote_access_request: bool = False,
    service_cancellation_threat: bool = False,
    subscription_fee_claim: bool = False,
    unverified_link_prompt: bool = False,
    sender_email: Optional[str] = None,
    suspicious_domain: bool = False,
    special_offer_hook: bool = False,
    countdown_timer: bool = False,
    requested_action: Optional[str] = None,
) -> ScamSignals:
    """Create a validated ScamSignals instance."""
    # Normalize string inputs to lowercase and strip whitespace if present
    normalized_identity_claim = (
        identity_claim.strip().lower() if isinstance(identity_claim, str) and identity_claim.strip() else None
    )
    normalized_sender_email = (
        sender_email.strip().lower() if isinstance(sender_email, str) and sender_email.strip() else None
    )
    normalized_requested_action = (
        requested_action.strip().lower() if isinstance(requested_action, str) and requested_action.strip() else None
    )

    return ScamSignals(
        identity_claim=normalized_identity_claim,
        identity_verified=bool(identity_verified),
        financial_context=bool(financial_context),
        urgency=bool(urgency),
        secrecy_request=bool(secrecy_request),
        otp_request=bool(otp_request),
        password_request=bool(password_request),
        transfer_request=bool(transfer_request),
        remote_access_request=bool(remote_access_request),
        service_cancellation_threat=bool(service_cancellation_threat),
        subscription_fee_claim=bool(subscription_fee_claim),
        unverified_link_prompt=bool(unverified_link_prompt),
        sender_email=normalized_sender_email,
        suspicious_domain=bool(suspicious_domain),
        special_offer_hook=bool(special_offer_hook),
        countdown_timer=bool(countdown_timer),
        requested_action=normalized_requested_action,
    )


_URGENCY_KEYWORDS = ("urgente", "urgent", "blocked", "bloquead", "deleted", "eliminad", "expire", "expirad", "immediately", "inmediatamen", "don't wait")
_FINANCIAL_KEYWORDS = ("payment declined", "pago rechazado", "subscription fee", "cuota de suscripci", "bank account", "tarjeta", "wire transfer", "transferencia")
_SERVICE_THREAT_KEYWORDS = ("storage full", "almacenamiento lleno", "photos will be removed", "account blocked", "cuenta bloqueada", "cuenta suspendida", "lost photos")
_SUBSCRIPTION_KEYWORDS = ("payment declined", "pago rechazado", "renovacion obligatoria", "unpaid invoice", "factura impagada")
_LINK_KEYWORDS = ("bit.ly", "tinyurl", "click here", "haga clic", "actualizar pago", "update payment", "verify-account")
_DOMAIN_KEYWORDS = ("importican", "neuralgrid", "verify-bank", "security-alert-update", "temp-mail", "fake-domain")
_OFFER_KEYWORDS = ("extra 50 gb", "50gb bonus", "descuento del 90%", "bonus storage", "free 100gb")
_COUNTDOWN_KEYWORDS = ("expires in", "expira en", "24 hours left", "4 minutes")
_TRIGGER_KEYWORDS = ("storage full", "photos will be removed", "payment declined", "account blocked", "cuenta bloqueada", "otp", "password", "clave", "transferencia", "giftcard")


def text_keyword_flags(text: str) -> Dict[str, bool]:
    """Best-effort keyword flags for scam-adjacent language, used when structured
    signal extraction is unavailable (Gemini failure) or incomplete (OCR merge).
    Single source of truth for the heuristic keyword lists.
    """
    lower_t = text.lower()
    return {
        "urgency": any(k in lower_t for k in _URGENCY_KEYWORDS),
        "financial_context": any(k in lower_t for k in _FINANCIAL_KEYWORDS),
        "service_cancellation_threat": any(k in lower_t for k in _SERVICE_THREAT_KEYWORDS),
        "subscription_fee_claim": any(k in lower_t for k in _SUBSCRIPTION_KEYWORDS),
        "unverified_link_prompt": any(k in lower_t for k in _LINK_KEYWORDS),
        "suspicious_domain": any(k in lower_t for k in _DOMAIN_KEYWORDS),
        "special_offer_hook": any(k in lower_t for k in _OFFER_KEYWORDS),
        "countdown_timer": any(k in lower_t for k in _COUNTDOWN_KEYWORDS),
    }


def heuristic_signals_from_text(text: str) -> Optional[ScamSignals]:
    """Guess ScamSignals from keywords alone. Returns None if nothing scam-adjacent matched."""
    lower_t = text.lower()
    if not any(k in lower_t for k in _TRIGGER_KEYWORDS):
        return None

    flags = text_keyword_flags(text)
    
    identity = None
    if any(k in lower_t for k in ["cloud", "storage", "google", "icloud", "photos", "drive"]):
        identity = "cloud_service_or_bank"
    elif any(k in lower_t for k in ["banco", "bank", "bbva", "santander", "caixabank"]):
        identity = "banco"
    elif any(k in lower_t for k in ["policia", "police", "guardia civil"]):
        identity = "policia"

    action = None
    if flags.get("unverified_link_prompt") or "click" in lower_t or "update" in lower_t:
        action = "click_link"

    return create_signals(
        identity_claim=identity,
        requested_action=action,
        **flags,
    )


def signals_from_dict(data: Dict[str, Any]) -> ScamSignals:
    """Construct a ScamSignals instance from a dictionary."""
    return create_signals(
        identity_claim=data.get("identity_claim"),
        identity_verified=data.get("identity_verified", False),
        financial_context=data.get("financial_context", False),
        urgency=data.get("urgency", False),
        secrecy_request=data.get("secrecy_request", False),
        otp_request=data.get("otp_request", False),
        password_request=data.get("password_request", False),
        transfer_request=data.get("transfer_request", False),
        remote_access_request=data.get("remote_access_request", False),
        service_cancellation_threat=data.get("service_cancellation_threat", False),
        subscription_fee_claim=data.get("subscription_fee_claim", False),
        unverified_link_prompt=data.get("unverified_link_prompt", False),
        sender_email=data.get("sender_email"),
        suspicious_domain=data.get("suspicious_domain", False),
        special_offer_hook=data.get("special_offer_hook", False),
        countdown_timer=data.get("countdown_timer", False),
        requested_action=data.get("requested_action"),
    )
