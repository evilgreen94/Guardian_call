"""Experimental compositional signal schema for M1.1 adversarial research."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple, Type, TypeVar


class ClaimedEntityType(str, Enum):
    BANK = "BANK"
    TELECOM = "TELECOM"
    TECH_SUPPORT = "TECH_SUPPORT"
    SOCIAL_PLATFORM = "SOCIAL_PLATFORM"
    ECOMMERCE = "ECOMMERCE"
    GOVERNMENT_AUTHORITY = "GOVERNMENT_AUTHORITY"
    POLICE = "POLICE"
    FAMILY_MEMBER = "FAMILY_MEMBER"
    ACCOUNT_SUPPORT = "ACCOUNT_SUPPORT"
    CRYPTO_SUPPORT = "CRYPTO_SUPPORT"
    EMAIL_CLOUD_SUPPORT = "EMAIL_CLOUD_SUPPORT"


class KnowledgeCategory(str, Enum):
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    CUSTOMER_ID = "CUSTOMER_ID"
    GOVERNMENT_ID = "GOVERNMENT_ID"
    ACCOUNT_DETAILS = "ACCOUNT_DETAILS"
    SUBSCRIPTION_DETAILS = "SUBSCRIPTION_DETAILS"
    TRANSACTION_DETAILS = "TRANSACTION_DETAILS"
    EMPLOYEE_ID = "EMPLOYEE_ID"
    INCIDENT_DETAILS = "INCIDENT_DETAILS"


class ContextType(str, Enum):
    BANKING = "BANKING"
    TELECOM = "TELECOM"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    ECOMMERCE = "ECOMMERCE"
    GOVERNMENT = "GOVERNMENT"
    TECH_SUPPORT = "TECH_SUPPORT"
    FAMILY = "FAMILY"
    PAYMENT_APP = "PAYMENT_APP"
    ACCOUNT_RECOVERY = "ACCOUNT_RECOVERY"
    CRYPTO = "CRYPTO"
    EMAIL_CLOUD = "EMAIL_CLOUD"


class ActionTypeV2(str, Enum):
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


class AssetCategory(str, Enum):
    SECRET = "SECRET"
    PAYMENT_CARD_DATA = "PAYMENT_CARD_DATA"
    ECONOMIC_VALUE = "ECONOMIC_VALUE"
    ACCOUNT_CONTROL = "ACCOUNT_CONTROL"
    DEVICE_ACCESS = "DEVICE_ACCESS"


class AssetSubtype(str, Enum):
    OTP = "OTP"
    PASSWORD = "PASSWORD"
    RECOVERY_CODE = "RECOVERY_CODE"
    CARD_SECURITY_CODE = "CARD_SECURITY_CODE"
    GIFT_CARD_REDEMPTION_CODE = "GIFT_CARD_REDEMPTION_CODE"
    SEED_PHRASE = "SEED_PHRASE"
    PRIVATE_KEY = "PRIVATE_KEY"
    UNSPECIFIED_SECURITY_CODE = "UNSPECIFIED_SECURITY_CODE"
    CARD_NUMBER = "CARD_NUMBER"
    CARD_EXPIRY = "CARD_EXPIRY"
    FIAT_FUNDS = "FIAT_FUNDS"
    PAYMENT_APP_PAYMENT = "PAYMENT_APP_PAYMENT"
    GIFT_CARD = "GIFT_CARD"
    CASH = "CASH"
    CRYPTO_ASSET = "CRYPTO_ASSET"
    LOGIN_APPROVAL = "LOGIN_APPROVAL"
    RECOVERY_EMAIL = "RECOVERY_EMAIL"
    RECOVERY_PHONE = "RECOVERY_PHONE"
    TWO_FACTOR_SETTING = "TWO_FACTOR_SETTING"
    PASSWORD_RESET_LINK = "PASSWORD_RESET_LINK"
    REMOTE_SOFTWARE = "REMOTE_SOFTWARE"
    REMOTE_CONTROL = "REMOTE_CONTROL"
    SCREEN_CONTENT = "SCREEN_CONTENT"


class SemanticDirection(str, Enum):
    DIRECT_REQUEST = "DIRECT_REQUEST"
    INDIRECT_REQUEST = "INDIRECT_REQUEST"
    PARTIAL_REQUEST = "PARTIAL_REQUEST"
    NEGATION = "NEGATION"
    WARNING = "WARNING"
    QUESTION = "QUESTION"
    HYPOTHETICAL = "HYPOTHETICAL"
    HISTORICAL = "HISTORICAL"
    THIRD_PARTY = "THIRD_PARTY"
    SELF_SERVICE = "SELF_SERVICE"
    DISCUSSION = "DISCUSSION"


class Actor(str, Enum):
    USER = "USER"
    THIRD_PARTY = "THIRD_PARTY"
    UNKNOWN = "UNKNOWN"


class Destination(str, Enum):
    """Control boundary receiving the act's asset, capability, or effect."""

    CALLER = "CALLER"
    THIRD_PARTY = "THIRD_PARTY"
    OFFICIAL_SELF_SERVICE = "OFFICIAL_SELF_SERVICE"
    USER_CONTROLLED = "USER_CONTROLLED"
    EXTERNAL_ACCOUNT = "EXTERNAL_ACCOUNT"
    UNKNOWN = "UNKNOWN"


class ManipulationType(str, Enum):
    URGENCY = "URGENCY"
    FEAR_THREAT = "FEAR_THREAT"
    AUTHORITY_PRESSURE = "AUTHORITY_PRESSURE"
    SECRECY = "SECRECY"
    ISOLATION = "ISOLATION"
    KEEP_ON_CALL = "KEEP_ON_CALL"
    PROTECTIVE_PRETEXT = "PROTECTIVE_PRETEXT"
    EMOTIONAL_EMERGENCY = "EMOTIONAL_EMERGENCY"
    REWARD = "REWARD"
    SCARCITY = "SCARCITY"


class IdentityAssurance(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED_EXTERNALLY = "VERIFIED_EXTERNALLY"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


VOCABULARY_JUSTIFICATIONS: Mapping[str, Mapping[str, str]] = {
    "IdentityAssurance": {
        "VERIFIED_EXTERNALLY": (
            "Required to represent a positive result from a future independent "
            "verification channel without deriving it from conversation."
        ),
        "VERIFICATION_FAILED": (
            "Required to distinguish an explicit failed external check from the "
            "absence of verification represented by UNVERIFIED."
        ),
    }
}


ASSET_COMPATIBILITY: Mapping[AssetCategory, FrozenSet[AssetSubtype]] = {
    AssetCategory.SECRET: frozenset(
        {
            AssetSubtype.OTP,
            AssetSubtype.PASSWORD,
            AssetSubtype.RECOVERY_CODE,
            AssetSubtype.CARD_SECURITY_CODE,
            AssetSubtype.GIFT_CARD_REDEMPTION_CODE,
            AssetSubtype.SEED_PHRASE,
            AssetSubtype.PRIVATE_KEY,
            AssetSubtype.UNSPECIFIED_SECURITY_CODE,
        }
    ),
    AssetCategory.PAYMENT_CARD_DATA: frozenset(
        {AssetSubtype.CARD_NUMBER, AssetSubtype.CARD_EXPIRY}
    ),
    AssetCategory.ECONOMIC_VALUE: frozenset(
        {
            AssetSubtype.FIAT_FUNDS,
            AssetSubtype.PAYMENT_APP_PAYMENT,
            AssetSubtype.GIFT_CARD,
            AssetSubtype.CASH,
            AssetSubtype.CRYPTO_ASSET,
        }
    ),
    AssetCategory.ACCOUNT_CONTROL: frozenset(
        {
            AssetSubtype.LOGIN_APPROVAL,
            AssetSubtype.RECOVERY_EMAIL,
            AssetSubtype.RECOVERY_PHONE,
            AssetSubtype.TWO_FACTOR_SETTING,
            AssetSubtype.PASSWORD_RESET_LINK,
        }
    ),
    AssetCategory.DEVICE_ACCESS: frozenset(
        {
            AssetSubtype.REMOTE_SOFTWARE,
            AssetSubtype.REMOTE_CONTROL,
            AssetSubtype.SCREEN_CONTENT,
        }
    ),
}


@dataclass(frozen=True)
class IdentityPretext:
    claims: FrozenSet[ClaimedEntityType] = field(default_factory=frozenset)
    knowledge_categories: FrozenSet[KnowledgeCategory] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        _require_frozen_enum_set(self.claims, ClaimedEntityType, "claims")
        _require_frozen_enum_set(
            self.knowledge_categories, KnowledgeCategory, "knowledge_categories"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claims": sorted(item.value for item in self.claims),
            "knowledge_categories": sorted(
                item.value for item in self.knowledge_categories
            ),
        }


@dataclass(frozen=True)
class SensitiveAsset:
    category: AssetCategory
    subtype: AssetSubtype

    def __post_init__(self) -> None:
        if not isinstance(self.category, AssetCategory):
            raise TypeError("category must be an AssetCategory")
        if not isinstance(self.subtype, AssetSubtype):
            raise TypeError("subtype must be an AssetSubtype")
        if self.subtype not in ASSET_COMPATIBILITY[self.category]:
            raise ValueError(
                f"Asset subtype {self.subtype.value} is incompatible with "
                f"category {self.category.value}"
            )

    def to_dict(self) -> Dict[str, str]:
        return {"category": self.category.value, "subtype": self.subtype.value}


@dataclass(frozen=True)
class InteractionAct:
    action: ActionTypeV2
    asset: Optional[SensitiveAsset]
    semantic_direction: SemanticDirection
    actor: Actor
    destination: Destination

    def __post_init__(self) -> None:
        _require_enum_instance(self.action, ActionTypeV2, "action")
        if self.asset is not None and not isinstance(self.asset, SensitiveAsset):
            raise TypeError("asset must be a SensitiveAsset or None")
        _require_enum_instance(
            self.semantic_direction, SemanticDirection, "semantic_direction"
        )
        _require_enum_instance(self.actor, Actor, "actor")
        _require_enum_instance(self.destination, Destination, "destination")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "asset": self.asset.to_dict() if self.asset else None,
            "semantic_direction": self.semantic_direction.value,
            "actor": self.actor.value,
            "destination": self.destination.value,
        }


@dataclass(frozen=True)
class ScamSignalsV2:
    identity_pretext: IdentityPretext = field(default_factory=IdentityPretext)
    contexts: FrozenSet[ContextType] = field(default_factory=frozenset)
    interaction_acts: Tuple[InteractionAct, ...] = ()
    manipulation: FrozenSet[ManipulationType] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.identity_pretext, IdentityPretext):
            raise TypeError("identity_pretext must be an IdentityPretext")
        _require_frozen_enum_set(self.contexts, ContextType, "contexts")
        if not isinstance(self.interaction_acts, tuple) or not all(
            isinstance(item, InteractionAct) for item in self.interaction_acts
        ):
            raise TypeError("interaction_acts must be a tuple of InteractionAct")
        _require_frozen_enum_set(
            self.manipulation, ManipulationType, "manipulation"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_pretext": self.identity_pretext.to_dict(),
            "contexts": sorted(item.value for item in self.contexts),
            "interaction_acts": [item.to_dict() for item in self.interaction_acts],
            "manipulation": sorted(item.value for item in self.manipulation),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScamSignalsV2":
        _require_exact_keys(
            value,
            {"identity_pretext", "contexts", "interaction_acts", "manipulation"},
            "ScamSignalsV2",
        )
        pretext_value = _require_mapping(value["identity_pretext"], "identity_pretext")
        _require_exact_keys(
            pretext_value, {"claims", "knowledge_categories"}, "IdentityPretext"
        )
        pretext = IdentityPretext(
            claims=_parse_enum_set(
                ClaimedEntityType, pretext_value["claims"], "identity_pretext.claims"
            ),
            knowledge_categories=_parse_enum_set(
                KnowledgeCategory,
                pretext_value["knowledge_categories"],
                "identity_pretext.knowledge_categories",
            ),
        )
        acts = tuple(
            _parse_interaction_act(item, index)
            for index, item in enumerate(
                _require_list(value["interaction_acts"], "interaction_acts")
            )
        )
        return cls(
            identity_pretext=pretext,
            contexts=_parse_enum_set(ContextType, value["contexts"], "contexts"),
            interaction_acts=acts,
            manipulation=_parse_enum_set(
                ManipulationType, value["manipulation"], "manipulation"
            ),
        )


@dataclass(frozen=True)
class IdentityAssuranceContext:
    identity_assurance: IdentityAssurance = IdentityAssurance.UNVERIFIED

    def __post_init__(self) -> None:
        _require_enum_instance(
            self.identity_assurance, IdentityAssurance, "identity_assurance"
        )

    def to_dict(self) -> Dict[str, str]:
        return {"identity_assurance": self.identity_assurance.value}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IdentityAssuranceContext":
        _require_exact_keys(value, {"identity_assurance"}, "IdentityAssuranceContext")
        return cls(
            identity_assurance=_parse_enum(
                IdentityAssurance, value["identity_assurance"], "identity_assurance"
            )
        )


EnumType = TypeVar("EnumType", bound=Enum)


def _parse_interaction_act(value: Any, index: int) -> InteractionAct:
    path = f"interaction_acts[{index}]"
    mapping = _require_mapping(value, path)
    _require_exact_keys(
        mapping,
        {"action", "asset", "semantic_direction", "actor", "destination"},
        path,
    )
    asset_value = mapping["asset"]
    asset = None
    if asset_value is not None:
        asset_mapping = _require_mapping(asset_value, f"{path}.asset")
        _require_exact_keys(asset_mapping, {"category", "subtype"}, f"{path}.asset")
        asset = SensitiveAsset(
            category=_parse_enum(
                AssetCategory, asset_mapping["category"], f"{path}.asset.category"
            ),
            subtype=_parse_enum(
                AssetSubtype, asset_mapping["subtype"], f"{path}.asset.subtype"
            ),
        )
    return InteractionAct(
        action=_parse_enum(ActionTypeV2, mapping["action"], f"{path}.action"),
        asset=asset,
        semantic_direction=_parse_enum(
            SemanticDirection,
            mapping["semantic_direction"],
            f"{path}.semantic_direction",
        ),
        actor=_parse_enum(Actor, mapping["actor"], f"{path}.actor"),
        destination=_parse_enum(
            Destination, mapping["destination"], f"{path}.destination"
        ),
    )


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def _require_exact_keys(
    value: Mapping[str, Any], expected: set, model_name: str
) -> None:
    actual = set(value)
    if actual != expected:
        unexpected = sorted(actual - expected)
        missing = sorted(expected - actual)
        raise ValueError(
            f"{model_name} fields must match schema; "
            f"unexpected={unexpected}, missing={missing}"
        )


def _parse_enum(enum_type: Type[EnumType], value: Any, path: str) -> EnumType:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValueError(f"Unknown {path} value: {value!r}") from error


def _parse_enum_set(
    enum_type: Type[EnumType], value: Any, path: str
) -> FrozenSet[EnumType]:
    items = _require_list(value, path)
    parsed = tuple(_parse_enum(enum_type, item, path) for item in items)
    if len(set(parsed)) != len(parsed):
        raise ValueError(f"{path} must not contain duplicates")
    return frozenset(parsed)


def _require_enum_instance(value: Any, enum_type: Type[EnumType], path: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{path} must be a {enum_type.__name__}")


def _require_frozen_enum_set(
    value: Any, enum_type: Type[EnumType], path: str
) -> None:
    if not isinstance(value, frozenset) or not all(
        isinstance(item, enum_type) for item in value
    ):
        raise TypeError(f"{path} must be a frozenset of {enum_type.__name__}")
