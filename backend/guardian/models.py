"""Domain models for Guardian Call."""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    """Explainable risk levels for evaluated conversation state."""
    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    """Consequential actions subject to Canary policy authorization."""
    WARN_USER = "warn_user"
    NOTIFY_TRUSTED_CIRCLE = "notify_trusted_circle"
    SHARE_TRANSCRIPT = "share_transcript"
    RECOMMEND_END_CALL = "recommend_end_call"
    END_CALL = "end_call"


class PolicyDecision(str, Enum):
    """Authorization outcomes from Canary policy evaluation."""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ASK_USER = "ASK_USER"


@dataclass(frozen=True)
class ScamSignals:
    """Structured scam signals extracted from conversational input."""
    identity_claim: Optional[str] = None
    identity_verified: bool = False
    financial_context: bool = False
    urgency: bool = False
    secrecy_request: bool = False
    otp_request: bool = False
    password_request: bool = False
    transfer_request: bool = False
    remote_access_request: bool = False
    service_cancellation_threat: bool = False
    subscription_fee_claim: bool = False
    unverified_link_prompt: bool = False
    sender_email: Optional[str] = None
    suspicious_domain: bool = False
    special_offer_hook: bool = False
    countdown_timer: bool = False
    requested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert signals to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class RiskAssessment:
    """Explainable risk evaluation produced by the Risk Engine."""
    level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    contributing_signals: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert risk assessment to dictionary."""
        return {
            "level": self.level.value,
            "reasons": list(self.reasons),
            "contributing_signals": list(self.contributing_signals),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class CanaryDecision:
    """Policy authorization decision produced by Canary."""
    action: ActionType
    decision: PolicyDecision
    reason: str
    risk_level: RiskLevel
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert Canary decision to dictionary."""
        return {
            "action": self.action.value,
            "decision": self.decision.value,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
            "timestamp": self.timestamp,
        }
