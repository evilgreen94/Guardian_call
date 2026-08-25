"""Neutral, immutable evidence accepted by the M2 longitudinal reducer."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional, Tuple


class TemporalScope(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"
    NEGATED = "NEGATED"
    ACCUMULATED_CONTEXT = "ACCUMULATED_CONTEXT"


class Context(str, Enum):
    BANKING = "BANKING"
    TELECOM = "TELECOM"
    TECH_SUPPORT = "TECH_SUPPORT"
    ACCOUNT_RECOVERY = "ACCOUNT_RECOVERY"
    SOCIAL_PLATFORM = "SOCIAL_PLATFORM"
    ECOMMERCE = "ECOMMERCE"
    GOVERNMENT = "GOVERNMENT"
    FAMILY_EMERGENCY = "FAMILY_EMERGENCY"
    PAYMENT_APP = "PAYMENT_APP"
    CRYPTO = "CRYPTO"
    EMAIL_CLOUD = "EMAIL_CLOUD"


class IdentityClaim(str, Enum):
    FINANCIAL_INSTITUTION = "FINANCIAL_INSTITUTION"
    TELECOM_PROVIDER = "TELECOM_PROVIDER"
    TECH_SUPPORT = "TECH_SUPPORT"
    ONLINE_SERVICE = "ONLINE_SERVICE"
    GOVERNMENT_AUTHORITY = "GOVERNMENT_AUTHORITY"
    LAW_ENFORCEMENT = "LAW_ENFORCEMENT"
    FAMILY_OR_ACQUAINTANCE = "FAMILY_OR_ACQUAINTANCE"
    MERCHANT = "MERCHANT"
    CRYPTO_SERVICE = "CRYPTO_SERVICE"


class Manipulation(str, Enum):
    URGENCY = "URGENCY"
    FEAR_OR_THREAT = "FEAR_OR_THREAT"
    AUTHORITY_PRESSURE = "AUTHORITY_PRESSURE"
    SECRECY = "SECRECY"
    ISOLATION = "ISOLATION"
    KEEP_ENGAGED = "KEEP_ENGAGED"
    PROTECTIVE_PRETEXT = "PROTECTIVE_PRETEXT"
    EMOTIONAL_PRESSURE = "EMOTIONAL_PRESSURE"
    REWARD = "REWARD"
    SCARCITY = "SCARCITY"


class Action(str, Enum):
    DISCLOSE = "DISCLOSE"
    TRANSFER = "TRANSFER"
    AUTHORIZE = "AUTHORIZE"
    INSTALL = "INSTALL"
    GRANT_ACCESS = "GRANT_ACCESS"
    CHANGE_SECURITY = "CHANGE_SECURITY"
    PURCHASE = "PURCHASE"
    WITHDRAW = "WITHDRAW"
    NAVIGATE = "NAVIGATE"
    ENTER = "ENTER"
    CONTACT = "CONTACT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class ProtectedAsset(str, Enum):
    OTP = "OTP"
    PASSWORD = "PASSWORD"
    PIN = "PIN"
    RECOVERY_CODE = "RECOVERY_CODE"
    CARD_SECURITY_CODE = "CARD_SECURITY_CODE"
    CARD_DATA = "CARD_DATA"
    BANK_FUNDS = "BANK_FUNDS"
    PAYMENT_APP_FUNDS = "PAYMENT_APP_FUNDS"
    CASH = "CASH"
    GIFT_CARD = "GIFT_CARD"
    CRYPTO_ASSET = "CRYPTO_ASSET"
    SEED_PHRASE = "SEED_PHRASE"
    PRIVATE_KEY = "PRIVATE_KEY"
    LOGIN_APPROVAL = "LOGIN_APPROVAL"
    ACCOUNT_RECOVERY = "ACCOUNT_RECOVERY"
    SECURITY_SETTINGS = "SECURITY_SETTINGS"
    REMOTE_SOFTWARE = "REMOTE_SOFTWARE"
    REMOTE_CONTROL = "REMOTE_CONTROL"
    SCREEN_CONTENT = "SCREEN_CONTENT"


class Actor(str, Enum):
    USER = "USER"
    OTHER_PARTY = "OTHER_PARTY"
    THIRD_PARTY = "THIRD_PARTY"
    UNKNOWN = "UNKNOWN"


class Destination(str, Enum):
    """Control boundary receiving the asset, capability, or action effect."""

    OTHER_PARTY = "OTHER_PARTY"
    THIRD_PARTY = "THIRD_PARTY"
    OFFICIAL_SELF_SERVICE = "OFFICIAL_SELF_SERVICE"
    USER_CONTROLLED = "USER_CONTROLLED"
    EXTERNAL_ACCOUNT = "EXTERNAL_ACCOUNT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, order=True)
class ContextEvidence:
    context: Context
    scope: TemporalScope = TemporalScope.CURRENT

    def __post_init__(self) -> None:
        _require_enum(self.context, Context, "context")
        _require_enum(self.scope, TemporalScope, "scope")

    def to_dict(self) -> Dict[str, str]:
        return {"context": self.context.value, "scope": self.scope.value}


@dataclass(frozen=True, order=True)
class IdentityClaimEvidence:
    claim: IdentityClaim
    scope: TemporalScope = TemporalScope.CURRENT

    def __post_init__(self) -> None:
        _require_enum(self.claim, IdentityClaim, "claim")
        _require_enum(self.scope, TemporalScope, "scope")

    def to_dict(self) -> Dict[str, str]:
        return {"claim": self.claim.value, "scope": self.scope.value}


@dataclass(frozen=True, order=True)
class ManipulationEvidence:
    manipulation: Manipulation
    scope: TemporalScope = TemporalScope.CURRENT

    def __post_init__(self) -> None:
        _require_enum(self.manipulation, Manipulation, "manipulation")
        _require_enum(self.scope, TemporalScope, "scope")

    def to_dict(self) -> Dict[str, str]:
        return {"manipulation": self.manipulation.value, "scope": self.scope.value}


@dataclass(frozen=True)
class BehavioralAct:
    scope: TemporalScope
    action: Action
    asset: Optional[ProtectedAsset]
    actor: Actor
    destination: Destination

    def __post_init__(self) -> None:
        _require_enum(self.scope, TemporalScope, "scope")
        _require_enum(self.action, Action, "action")
        if self.asset is not None:
            _require_enum(self.asset, ProtectedAsset, "asset")
        _require_enum(self.actor, Actor, "actor")
        _require_enum(self.destination, Destination, "destination")

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "scope": self.scope.value,
            "action": self.action.value,
            "asset": self.asset.value if self.asset else None,
            "actor": self.actor.value,
            "destination": self.destination.value,
        }

    def semantic_dict(self) -> Dict[str, Optional[str]]:
        """Return the scope-independent identity used for precise retraction."""
        return {
            "action": self.action.value,
            "asset": self.asset.value if self.asset else None,
            "actor": self.actor.value,
            "destination": self.destination.value,
        }

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())

    @property
    def semantic_fingerprint(self) -> str:
        return _fingerprint(self.semantic_dict())


@dataclass(frozen=True)
class NormalizedTurnEvidence:
    turn_id: str
    turn_number: int
    contexts: FrozenSet[ContextEvidence] = field(default_factory=frozenset)
    identity_claims: FrozenSet[IdentityClaimEvidence] = field(
        default_factory=frozenset
    )
    manipulations: FrozenSet[ManipulationEvidence] = field(default_factory=frozenset)
    acts: Tuple[BehavioralAct, ...] = ()

    def __post_init__(self) -> None:
        _require_identifier(self.turn_id, "turn_id")
        if not isinstance(self.turn_number, int) or isinstance(self.turn_number, bool):
            raise TypeError("turn_number must be an integer")
        if self.turn_number < 1:
            raise ValueError("turn_number must be positive")
        _require_frozen_set(self.contexts, ContextEvidence, "contexts")
        _require_frozen_set(
            self.identity_claims, IdentityClaimEvidence, "identity_claims"
        )
        _require_frozen_set(
            self.manipulations, ManipulationEvidence, "manipulations"
        )
        if not isinstance(self.acts, tuple) or not all(
            isinstance(item, BehavioralAct) for item in self.acts
        ):
            raise TypeError("acts must be a tuple of BehavioralAct")
        if len(set(self.acts)) != len(self.acts):
            raise ValueError("acts must not contain duplicates within a turn")

    def semantic_dict(self) -> Dict[str, Any]:
        return {
            "turn_number": self.turn_number,
            "contexts": [item.to_dict() for item in sorted(self.contexts)],
            "identity_claims": [
                item.to_dict() for item in sorted(self.identity_claims)
            ],
            "manipulations": [
                item.to_dict() for item in sorted(self.manipulations)
            ],
            "acts": [item.to_dict() for item in sorted(self.acts, key=_act_key)],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"turn_id": self.turn_id, **self.semantic_dict()}

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @property
    def evidence_fingerprint(self) -> str:
        return _fingerprint(self.semantic_dict())


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,63}$")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fingerprint(value: Any) -> str:
    payload = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _act_key(act: BehavioralAct) -> Tuple[str, str, str, str, str]:
    return (
        act.scope.value,
        act.action.value,
        act.asset.value if act.asset else "",
        act.actor.value,
        act.destination.value,
    )


def _require_identifier(value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{path} must be a string")
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"{path} must be an externally supplied opaque identifier of 1-64 "
            "ASCII characters, starting with a letter"
        )


def _require_enum(value: Any, enum_type: type[Enum], path: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{path} must be a {enum_type.__name__}")


def _require_frozen_set(value: Any, item_type: type, path: str) -> None:
    if not isinstance(value, frozenset) or not all(
        isinstance(item, item_type) for item in value
    ):
        raise TypeError(f"{path} must be a frozenset of {item_type.__name__}")
