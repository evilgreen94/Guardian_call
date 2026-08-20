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
