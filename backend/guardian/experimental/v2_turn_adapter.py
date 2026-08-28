"""Experimental ScamSignalsV2 to M2 normalized-turn adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional, Tuple

from guardian.longitudinal.evidence import (
    Action,
    Actor as M2Actor,
    BehavioralAct,
    Context,
    ContextEvidence,
    Destination as M2Destination,
    IdentityClaim,
    IdentityClaimEvidence,
    Manipulation,
    ManipulationEvidence,
    NormalizedTurnEvidence,
    ProtectedAsset,
    TemporalScope,
)

from .signals_v2 import (
    ActionTypeV2,
    Actor as V2Actor,
    AssetSubtype,
    ClaimedEntityType,
    ContextType,
    Destination as V2Destination,
    InteractionAct,
    KnowledgeCategory,
    ManipulationType,
    ScamSignalsV2,
    SemanticDirection,
)


class MappingClassification(str, Enum):
    EXACT_MAPPING = "EXACT_MAPPING"
    LOSSLESS_NORMALIZATION = "LOSSLESS_NORMALIZATION"
    PARTIAL_MAPPING = "PARTIAL_MAPPING"
    NO_SAFE_MAPPING = "NO_SAFE_MAPPING"


class RepresentationalLossDisposition(str, Enum):
    DROPPED_NEUTRAL_CONTEXT = "DROPPED_NEUTRAL_CONTEXT"


@dataclass(frozen=True)
class V2MappingRecord:
    source_enum: str
    source_value: str
    target_value: Optional[str]
    classification: MappingClassification
    rationale: str

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "source_enum": self.source_enum,
            "source_value": self.source_value,
            "target_value": self.target_value,
            "classification": self.classification.value,
            "rationale": self.rationale,
        }


class UnsupportedV2MappingError(ValueError):
    """Raised when V2 evidence cannot be safely represented by M2 evidence."""


@dataclass(frozen=True)
class V2RepresentationalLoss:
    source_enum: str
    source_value: str
    classification: MappingClassification
    disposition: RepresentationalLossDisposition
    rationale: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "source_enum": self.source_enum,
            "source_value": self.source_value,
            "classification": self.classification.value,
            "disposition": self.disposition.value,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class AdaptedV2Turn:
    normalized_turn: NormalizedTurnEvidence
    representational_losses: Tuple[V2RepresentationalLoss, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "normalized_turn": self.normalized_turn.to_dict(),
            "representational_losses": [
                item.to_dict() for item in self.representational_losses
            ],
        }


CLAIM_MAPPING: Mapping[ClaimedEntityType, V2MappingRecord] = {
    ClaimedEntityType.BANK: V2MappingRecord(
        "ClaimedEntityType",
        "BANK",
        IdentityClaim.FINANCIAL_INSTITUTION.value,
        MappingClassification.EXACT_MAPPING,
        "Bank pretext is a financial-institution identity claim.",
    ),
    ClaimedEntityType.TELECOM: V2MappingRecord(
        "ClaimedEntityType",
        "TELECOM",
        IdentityClaim.TELECOM_PROVIDER.value,
        MappingClassification.EXACT_MAPPING,
        "Telecom pretext is a telecom-provider identity claim.",
    ),
    ClaimedEntityType.TECH_SUPPORT: V2MappingRecord(
        "ClaimedEntityType",
        "TECH_SUPPORT",
        IdentityClaim.TECH_SUPPORT.value,
        MappingClassification.EXACT_MAPPING,
        "Technical-support pretext is represented directly.",
    ),
    ClaimedEntityType.SOCIAL_PLATFORM: V2MappingRecord(
        "ClaimedEntityType",
        "SOCIAL_PLATFORM",
        IdentityClaim.ONLINE_SERVICE.value,
        MappingClassification.LOSSLESS_NORMALIZATION,
        "M2 represents social platforms under online-service claims.",
    ),
    ClaimedEntityType.ECOMMERCE: V2MappingRecord(
        "ClaimedEntityType",
        "ECOMMERCE",
        IdentityClaim.MERCHANT.value,
        MappingClassification.EXACT_MAPPING,
        "Ecommerce pretext is a merchant identity claim.",
    ),
    ClaimedEntityType.GOVERNMENT_AUTHORITY: V2MappingRecord(
        "ClaimedEntityType",
        "GOVERNMENT_AUTHORITY",
        IdentityClaim.GOVERNMENT_AUTHORITY.value,
        MappingClassification.EXACT_MAPPING,
        "Government-authority pretext is represented directly.",
    ),
    ClaimedEntityType.POLICE: V2MappingRecord(
        "ClaimedEntityType",
        "POLICE",
        IdentityClaim.LAW_ENFORCEMENT.value,
        MappingClassification.EXACT_MAPPING,
        "Police pretext maps to law-enforcement identity claim.",
    ),
    ClaimedEntityType.FAMILY_MEMBER: V2MappingRecord(
        "ClaimedEntityType",
        "FAMILY_MEMBER",
        IdentityClaim.FAMILY_OR_ACQUAINTANCE.value,
        MappingClassification.EXACT_MAPPING,
        "Family-member pretext is represented directly by M2's broader label.",
    ),
    ClaimedEntityType.ACCOUNT_SUPPORT: V2MappingRecord(
        "ClaimedEntityType",
        "ACCOUNT_SUPPORT",
        IdentityClaim.ONLINE_SERVICE.value,
        MappingClassification.PARTIAL_MAPPING,
        "M2 lacks generic account-support identity; online service is closest.",
    ),
    ClaimedEntityType.CRYPTO_SUPPORT: V2MappingRecord(
        "ClaimedEntityType",
        "CRYPTO_SUPPORT",
        IdentityClaim.CRYPTO_SERVICE.value,
        MappingClassification.EXACT_MAPPING,
        "Crypto-support pretext is represented directly.",
    ),
    ClaimedEntityType.EMAIL_CLOUD_SUPPORT: V2MappingRecord(
        "ClaimedEntityType",
        "EMAIL_CLOUD_SUPPORT",
        IdentityClaim.ONLINE_SERVICE.value,
        MappingClassification.PARTIAL_MAPPING,
        "M2 lacks email/cloud-support identity distinct from online service.",
    ),
}


KNOWLEDGE_MAPPING: Mapping[KnowledgeCategory, V2MappingRecord] = {
    item: V2MappingRecord(
        "KnowledgeCategory",
        item.value,
        None,
        MappingClassification.NO_SAFE_MAPPING,
        "M2 has no neutral identity-knowledge evidence slot; mapping it to authentication or context would invent semantics.",
    )
    for item in KnowledgeCategory
}


CONTEXT_MAPPING: Mapping[ContextType, V2MappingRecord] = {
    ContextType.BANKING: V2MappingRecord(
        "ContextType",
        "BANKING",
        Context.BANKING.value,
        MappingClassification.EXACT_MAPPING,
        "Banking context is represented directly.",
    ),
    ContextType.TELECOM: V2MappingRecord(
        "ContextType",
        "TELECOM",
        Context.TELECOM.value,
        MappingClassification.EXACT_MAPPING,
        "Telecom context is represented directly.",
    ),
    ContextType.SOCIAL_MEDIA: V2MappingRecord(
        "ContextType",
        "SOCIAL_MEDIA",
        Context.SOCIAL_PLATFORM.value,
        MappingClassification.LOSSLESS_NORMALIZATION,
        "M2 names the same domain social platform.",
    ),
    ContextType.ECOMMERCE: V2MappingRecord(
        "ContextType",
        "ECOMMERCE",
        Context.ECOMMERCE.value,
        MappingClassification.EXACT_MAPPING,
        "Ecommerce context is represented directly.",
    ),
    ContextType.GOVERNMENT: V2MappingRecord(
        "ContextType",
        "GOVERNMENT",
        Context.GOVERNMENT.value,
        MappingClassification.EXACT_MAPPING,
        "Government context is represented directly.",
    ),
    ContextType.TECH_SUPPORT: V2MappingRecord(
        "ContextType",
        "TECH_SUPPORT",
        Context.TECH_SUPPORT.value,
        MappingClassification.EXACT_MAPPING,
        "Technical-support context is represented directly.",
    ),
    ContextType.FAMILY: V2MappingRecord(
        "ContextType",
        "FAMILY",
        None,
        MappingClassification.NO_SAFE_MAPPING,
        "M2 has no neutral generic family context; mapping to family emergency would invent emergency semantics.",
    ),
    ContextType.PAYMENT_APP: V2MappingRecord(
        "ContextType",
        "PAYMENT_APP",
        Context.PAYMENT_APP.value,
        MappingClassification.EXACT_MAPPING,
        "Payment-app context is represented directly.",
    ),
    ContextType.ACCOUNT_RECOVERY: V2MappingRecord(
        "ContextType",
        "ACCOUNT_RECOVERY",
        Context.ACCOUNT_RECOVERY.value,
        MappingClassification.EXACT_MAPPING,
        "Account-recovery context is represented directly.",
    ),
    ContextType.CRYPTO: V2MappingRecord(
        "ContextType",
        "CRYPTO",
        Context.CRYPTO.value,
        MappingClassification.EXACT_MAPPING,
        "Crypto context is represented directly.",
    ),
    ContextType.EMAIL_CLOUD: V2MappingRecord(
        "ContextType",
        "EMAIL_CLOUD",
        Context.EMAIL_CLOUD.value,
        MappingClassification.EXACT_MAPPING,
        "Email/cloud context is represented directly.",
    ),
}


ACTION_MAPPING: Mapping[ActionTypeV2, V2MappingRecord] = {
    item: V2MappingRecord(
        "ActionTypeV2",
        item.value,
        Action(item.value).value,
        MappingClassification.EXACT_MAPPING,
        "V2 and M2 use the same controlled action value.",
    )
    for item in ActionTypeV2
}


ASSET_MAPPING: Mapping[AssetSubtype, V2MappingRecord] = {
    AssetSubtype.OTP: V2MappingRecord(
        "AssetSubtype", "OTP", ProtectedAsset.OTP.value, MappingClassification.EXACT_MAPPING, "OTP is represented directly."
    ),
    AssetSubtype.PASSWORD: V2MappingRecord(
        "AssetSubtype", "PASSWORD", ProtectedAsset.PASSWORD.value, MappingClassification.EXACT_MAPPING, "Password is represented directly."
    ),
    AssetSubtype.RECOVERY_CODE: V2MappingRecord(
        "AssetSubtype", "RECOVERY_CODE", ProtectedAsset.RECOVERY_CODE.value, MappingClassification.EXACT_MAPPING, "Recovery code is represented directly."
    ),
    AssetSubtype.CARD_SECURITY_CODE: V2MappingRecord(
        "AssetSubtype", "CARD_SECURITY_CODE", ProtectedAsset.CARD_SECURITY_CODE.value, MappingClassification.EXACT_MAPPING, "Card security code is represented directly."
    ),
    AssetSubtype.GIFT_CARD_REDEMPTION_CODE: V2MappingRecord(
        "AssetSubtype", "GIFT_CARD_REDEMPTION_CODE", ProtectedAsset.GIFT_CARD.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves gift-card sensitivity but not redemption-code subtype."
    ),
    AssetSubtype.SEED_PHRASE: V2MappingRecord(
        "AssetSubtype", "SEED_PHRASE", ProtectedAsset.SEED_PHRASE.value, MappingClassification.EXACT_MAPPING, "Seed phrase is represented directly."
    ),
    AssetSubtype.PRIVATE_KEY: V2MappingRecord(
        "AssetSubtype", "PRIVATE_KEY", ProtectedAsset.PRIVATE_KEY.value, MappingClassification.EXACT_MAPPING, "Private key is represented directly."
    ),
    AssetSubtype.UNSPECIFIED_SECURITY_CODE: V2MappingRecord(
        "AssetSubtype", "UNSPECIFIED_SECURITY_CODE", None, MappingClassification.NO_SAFE_MAPPING, "M2 cannot distinguish an unspecified security code without guessing OTP, PIN, or CVV."
    ),
    AssetSubtype.CARD_NUMBER: V2MappingRecord(
        "AssetSubtype", "CARD_NUMBER", ProtectedAsset.CARD_DATA.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves card-data sensitivity but not card-number subtype."
    ),
    AssetSubtype.CARD_EXPIRY: V2MappingRecord(
        "AssetSubtype", "CARD_EXPIRY", ProtectedAsset.CARD_DATA.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves card-data sensitivity but not expiry subtype."
    ),
    AssetSubtype.FIAT_FUNDS: V2MappingRecord(
        "AssetSubtype", "FIAT_FUNDS", ProtectedAsset.BANK_FUNDS.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves money-movement sensitivity but represents fiat funds as bank funds."
    ),
    AssetSubtype.PAYMENT_APP_PAYMENT: V2MappingRecord(
        "AssetSubtype", "PAYMENT_APP_PAYMENT", ProtectedAsset.PAYMENT_APP_FUNDS.value, MappingClassification.LOSSLESS_NORMALIZATION, "M2 names the same payment-app value as funds."
    ),
    AssetSubtype.GIFT_CARD: V2MappingRecord(
        "AssetSubtype", "GIFT_CARD", ProtectedAsset.GIFT_CARD.value, MappingClassification.EXACT_MAPPING, "Gift card is represented directly."
    ),
    AssetSubtype.CASH: V2MappingRecord(
        "AssetSubtype", "CASH", ProtectedAsset.CASH.value, MappingClassification.EXACT_MAPPING, "Cash is represented directly."
    ),
    AssetSubtype.CRYPTO_ASSET: V2MappingRecord(
        "AssetSubtype", "CRYPTO_ASSET", ProtectedAsset.CRYPTO_ASSET.value, MappingClassification.EXACT_MAPPING, "Crypto asset is represented directly."
    ),
    AssetSubtype.LOGIN_APPROVAL: V2MappingRecord(
        "AssetSubtype", "LOGIN_APPROVAL", ProtectedAsset.LOGIN_APPROVAL.value, MappingClassification.EXACT_MAPPING, "Login approval is represented directly."
    ),
    AssetSubtype.RECOVERY_EMAIL: V2MappingRecord(
        "AssetSubtype", "RECOVERY_EMAIL", ProtectedAsset.ACCOUNT_RECOVERY.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves account-recovery sensitivity but not recovery-email subtype."
    ),
    AssetSubtype.RECOVERY_PHONE: V2MappingRecord(
        "AssetSubtype", "RECOVERY_PHONE", ProtectedAsset.ACCOUNT_RECOVERY.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves account-recovery sensitivity but not recovery-phone subtype."
    ),
    AssetSubtype.TWO_FACTOR_SETTING: V2MappingRecord(
        "AssetSubtype", "TWO_FACTOR_SETTING", ProtectedAsset.SECURITY_SETTINGS.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves security-settings sensitivity but not 2FA-setting subtype."
    ),
    AssetSubtype.PASSWORD_RESET_LINK: V2MappingRecord(
        "AssetSubtype", "PASSWORD_RESET_LINK", ProtectedAsset.ACCOUNT_RECOVERY.value, MappingClassification.PARTIAL_MAPPING, "M2 preserves account-recovery sensitivity but not reset-link subtype."
    ),
    AssetSubtype.REMOTE_SOFTWARE: V2MappingRecord(
        "AssetSubtype", "REMOTE_SOFTWARE", ProtectedAsset.REMOTE_SOFTWARE.value, MappingClassification.EXACT_MAPPING, "Remote software is represented directly."
    ),
    AssetSubtype.REMOTE_CONTROL: V2MappingRecord(
        "AssetSubtype", "REMOTE_CONTROL", ProtectedAsset.REMOTE_CONTROL.value, MappingClassification.EXACT_MAPPING, "Remote control is represented directly."
    ),
    AssetSubtype.SCREEN_CONTENT: V2MappingRecord(
        "AssetSubtype", "SCREEN_CONTENT", ProtectedAsset.SCREEN_CONTENT.value, MappingClassification.EXACT_MAPPING, "Screen content is represented directly."
    ),
}


DIRECTION_MAPPING: Mapping[SemanticDirection, V2MappingRecord] = {
    SemanticDirection.DIRECT_REQUEST: V2MappingRecord(
        "SemanticDirection", "DIRECT_REQUEST", TemporalScope.CURRENT.value, MappingClassification.EXACT_MAPPING, "Direct requests are current actionable evidence."
    ),
    SemanticDirection.INDIRECT_REQUEST: V2MappingRecord(
        "SemanticDirection", "INDIRECT_REQUEST", TemporalScope.CURRENT.value, MappingClassification.LOSSLESS_NORMALIZATION, "Indirect requests are current actionable evidence without preserving phrasing style."
    ),
    SemanticDirection.PARTIAL_REQUEST: V2MappingRecord(
        "SemanticDirection", "PARTIAL_REQUEST", TemporalScope.CURRENT.value, MappingClassification.LOSSLESS_NORMALIZATION, "Partial requests are current actionable evidence without preserving completeness style."
    ),
    SemanticDirection.NEGATION: V2MappingRecord(
        "SemanticDirection", "NEGATION", TemporalScope.NEGATED.value, MappingClassification.EXACT_MAPPING, "Negation maps to M2 precise retraction semantics."
    ),
    SemanticDirection.WARNING: V2MappingRecord(
        "SemanticDirection", "WARNING", TemporalScope.HYPOTHETICAL.value, MappingClassification.PARTIAL_MAPPING, "M2 lacks warning scope; hypothetical preserves non-actionability without retracting prior current evidence."
    ),
    SemanticDirection.QUESTION: V2MappingRecord(
        "SemanticDirection", "QUESTION", TemporalScope.HYPOTHETICAL.value, MappingClassification.PARTIAL_MAPPING, "M2 lacks question scope; hypothetical preserves non-actionability."
    ),
    SemanticDirection.HYPOTHETICAL: V2MappingRecord(
        "SemanticDirection", "HYPOTHETICAL", TemporalScope.HYPOTHETICAL.value, MappingClassification.EXACT_MAPPING, "Hypothetical references are represented directly."
    ),
    SemanticDirection.HISTORICAL: V2MappingRecord(
        "SemanticDirection", "HISTORICAL", TemporalScope.HISTORICAL.value, MappingClassification.EXACT_MAPPING, "Historical references are represented directly."
    ),
    SemanticDirection.THIRD_PARTY: V2MappingRecord(
        "SemanticDirection", "THIRD_PARTY", TemporalScope.HISTORICAL.value, MappingClassification.PARTIAL_MAPPING, "M2 lacks a third-party report scope; historical preserves non-actionability and the described evidence without fabricating user-directed current action."
    ),
    SemanticDirection.SELF_SERVICE: V2MappingRecord(
        "SemanticDirection", "SELF_SERVICE", TemporalScope.CURRENT.value, MappingClassification.LOSSLESS_NORMALIZATION, "Self-service remains current only with its destination control boundary preserved."
    ),
    SemanticDirection.DISCUSSION: V2MappingRecord(
        "SemanticDirection", "DISCUSSION", TemporalScope.HYPOTHETICAL.value, MappingClassification.PARTIAL_MAPPING, "M2 lacks discussion scope; hypothetical preserves non-actionability."
    ),
}


ACTOR_MAPPING: Mapping[V2Actor, V2MappingRecord] = {
    V2Actor.USER: V2MappingRecord(
        "Actor", "USER", M2Actor.USER.value, MappingClassification.EXACT_MAPPING, "User actor is represented directly."
    ),
    V2Actor.THIRD_PARTY: V2MappingRecord(
        "Actor", "THIRD_PARTY", M2Actor.THIRD_PARTY.value, MappingClassification.EXACT_MAPPING, "Third-party actor is represented directly."
    ),
    V2Actor.UNKNOWN: V2MappingRecord(
        "Actor", "UNKNOWN", M2Actor.UNKNOWN.value, MappingClassification.EXACT_MAPPING, "Unknown actor is represented directly."
    ),
}


DESTINATION_MAPPING: Mapping[V2Destination, V2MappingRecord] = {
    V2Destination.CALLER: V2MappingRecord(
        "Destination", "CALLER", M2Destination.OTHER_PARTY.value, MappingClassification.LOSSLESS_NORMALIZATION, "M2 names the caller as other party."
    ),
    V2Destination.THIRD_PARTY: V2MappingRecord(
        "Destination", "THIRD_PARTY", M2Destination.THIRD_PARTY.value, MappingClassification.EXACT_MAPPING, "Third-party destination is represented directly."
    ),
    V2Destination.OFFICIAL_SELF_SERVICE: V2MappingRecord(
        "Destination", "OFFICIAL_SELF_SERVICE", M2Destination.OFFICIAL_SELF_SERVICE.value, MappingClassification.EXACT_MAPPING, "Official self-service destination is represented directly."
    ),
    V2Destination.USER_CONTROLLED: V2MappingRecord(
        "Destination", "USER_CONTROLLED", M2Destination.USER_CONTROLLED.value, MappingClassification.EXACT_MAPPING, "User-controlled destination is represented directly."
    ),
    V2Destination.EXTERNAL_ACCOUNT: V2MappingRecord(
        "Destination", "EXTERNAL_ACCOUNT", M2Destination.EXTERNAL_ACCOUNT.value, MappingClassification.EXACT_MAPPING, "External-account destination is represented directly."
    ),
    V2Destination.UNKNOWN: V2MappingRecord(
        "Destination", "UNKNOWN", M2Destination.UNKNOWN.value, MappingClassification.EXACT_MAPPING, "Unknown destination is represented directly."
    ),
}


MANIPULATION_MAPPING: Mapping[ManipulationType, V2MappingRecord] = {
    ManipulationType.URGENCY: V2MappingRecord(
        "ManipulationType", "URGENCY", Manipulation.URGENCY.value, MappingClassification.EXACT_MAPPING, "Urgency is represented directly."
    ),
    ManipulationType.FEAR_THREAT: V2MappingRecord(
        "ManipulationType", "FEAR_THREAT", Manipulation.FEAR_OR_THREAT.value, MappingClassification.LOSSLESS_NORMALIZATION, "M2 names the same tactic fear or threat."
    ),
    ManipulationType.AUTHORITY_PRESSURE: V2MappingRecord(
        "ManipulationType", "AUTHORITY_PRESSURE", Manipulation.AUTHORITY_PRESSURE.value, MappingClassification.EXACT_MAPPING, "Authority pressure is represented directly."
    ),
    ManipulationType.SECRECY: V2MappingRecord(
        "ManipulationType", "SECRECY", Manipulation.SECRECY.value, MappingClassification.EXACT_MAPPING, "Secrecy is represented directly."
    ),
    ManipulationType.ISOLATION: V2MappingRecord(
        "ManipulationType", "ISOLATION", Manipulation.ISOLATION.value, MappingClassification.EXACT_MAPPING, "Isolation is represented directly."
    ),
    ManipulationType.KEEP_ON_CALL: V2MappingRecord(
        "ManipulationType", "KEEP_ON_CALL", Manipulation.KEEP_ENGAGED.value, MappingClassification.LOSSLESS_NORMALIZATION, "M2 names the same tactic keep engaged."
    ),
    ManipulationType.PROTECTIVE_PRETEXT: V2MappingRecord(
        "ManipulationType", "PROTECTIVE_PRETEXT", Manipulation.PROTECTIVE_PRETEXT.value, MappingClassification.EXACT_MAPPING, "Protective pretext is represented directly."
    ),
    ManipulationType.EMOTIONAL_EMERGENCY: V2MappingRecord(
        "ManipulationType", "EMOTIONAL_EMERGENCY", Manipulation.EMOTIONAL_PRESSURE.value, MappingClassification.LOSSLESS_NORMALIZATION, "M2 names the same pressure family emotional pressure."
    ),
    ManipulationType.REWARD: V2MappingRecord(
        "ManipulationType", "REWARD", Manipulation.REWARD.value, MappingClassification.EXACT_MAPPING, "Reward is represented directly."
    ),
    ManipulationType.SCARCITY: V2MappingRecord(
        "ManipulationType", "SCARCITY", Manipulation.SCARCITY.value, MappingClassification.EXACT_MAPPING, "Scarcity is represented directly."
    ),
}


def adapt_v2_turn(
    *,
    session_id: str,
    turn_id: str,
    ordinal: int,
    signals: ScamSignalsV2,
) -> NormalizedTurnEvidence:
    """Translate already-validated ScamSignalsV2 into neutral M2 evidence."""
    del session_id  # The conversation state owns session identity in M2.
    if signals.identity_pretext.knowledge_categories:
        unsupported = sorted(
            item.value for item in signals.identity_pretext.knowledge_categories
        )
        raise UnsupportedV2MappingError(
            "M2 cannot safely represent identity knowledge categories: "
            + ", ".join(unsupported)
        )
    return NormalizedTurnEvidence(
        turn_id=turn_id,
        turn_number=ordinal,
        contexts=frozenset(
            ContextEvidence(Context(record.target_value))
            for record in _records_for(signals.contexts, CONTEXT_MAPPING)
        ),
        identity_claims=frozenset(
            IdentityClaimEvidence(IdentityClaim(record.target_value))
            for record in _records_for(signals.identity_pretext.claims, CLAIM_MAPPING)
        ),
        manipulations=frozenset(
            ManipulationEvidence(Manipulation(record.target_value))
            for record in _records_for(signals.manipulation, MANIPULATION_MAPPING)
        ),
        acts=tuple(_adapt_act(item) for item in signals.interaction_acts),
    )


def adapt_v2_turn_with_neutral_losses(
    *,
    session_id: str,
    turn_id: str,
    ordinal: int,
    signals: ScamSignalsV2,
) -> AdaptedV2Turn:
    """Adapt V2 evidence while explicitly recording allowlisted neutral loss."""
    del session_id  # The conversation state owns session identity in M2.
    if signals.identity_pretext.knowledge_categories:
        unsupported = sorted(
            item.value for item in signals.identity_pretext.knowledge_categories
        )
        raise UnsupportedV2MappingError(
            "M2 cannot safely represent identity knowledge categories: "
            + ", ".join(unsupported)
        )
    contexts, losses = _adapt_contexts_with_neutral_losses(signals.contexts)
    return AdaptedV2Turn(
        normalized_turn=NormalizedTurnEvidence(
            turn_id=turn_id,
            turn_number=ordinal,
            contexts=contexts,
            identity_claims=frozenset(
                IdentityClaimEvidence(IdentityClaim(record.target_value))
                for record in _records_for(
                    signals.identity_pretext.claims, CLAIM_MAPPING
                )
            ),
            manipulations=frozenset(
                ManipulationEvidence(Manipulation(record.target_value))
                for record in _records_for(signals.manipulation, MANIPULATION_MAPPING)
            ),
            acts=tuple(_adapt_act(item) for item in signals.interaction_acts),
        ),
        representational_losses=losses,
    )


def mapping_coverage_report() -> Tuple[V2MappingRecord, ...]:
    tables = (
        CLAIM_MAPPING,
        KNOWLEDGE_MAPPING,
        CONTEXT_MAPPING,
        ACTION_MAPPING,
        ASSET_MAPPING,
        DIRECTION_MAPPING,
        ACTOR_MAPPING,
        DESTINATION_MAPPING,
        MANIPULATION_MAPPING,
    )
    return tuple(
        record
        for table in tables
        for record in sorted(
            table.values(), key=lambda item: (item.source_enum, item.source_value)
        )
    )


def _adapt_act(act: InteractionAct) -> BehavioralAct:
    action = Action(_record_for(act.action, ACTION_MAPPING).target_value)
    scope = TemporalScope(_record_for(act.semantic_direction, DIRECTION_MAPPING).target_value)
    actor = M2Actor(_record_for(act.actor, ACTOR_MAPPING).target_value)
    destination = M2Destination(_record_for(act.destination, DESTINATION_MAPPING).target_value)
    asset = None
    if act.asset is not None:
        asset_record = _record_for(act.asset.subtype, ASSET_MAPPING)
        if asset_record.classification == MappingClassification.NO_SAFE_MAPPING:
            raise UnsupportedV2MappingError(
                f"Unsupported V2 asset subtype: {act.asset.subtype.value}"
            )
        asset = ProtectedAsset(asset_record.target_value)
    return BehavioralAct(scope, action, asset, actor, destination)


def _adapt_contexts_with_neutral_losses(
    contexts: object,
) -> Tuple[frozenset[ContextEvidence], Tuple[V2RepresentationalLoss, ...]]:
    mapped = []
    losses = []
    for item in sorted(contexts, key=lambda value: value.value):
        record = CONTEXT_MAPPING[item]
        if record.classification == MappingClassification.NO_SAFE_MAPPING:
            if item == ContextType.FAMILY:
                losses.append(
                    V2RepresentationalLoss(
                        source_enum=record.source_enum,
                        source_value=record.source_value,
                        classification=record.classification,
                        disposition=RepresentationalLossDisposition.DROPPED_NEUTRAL_CONTEXT,
                        rationale=record.rationale,
                    )
                )
                continue
            raise UnsupportedV2MappingError(
                f"Unsupported V2 mapping for {record.source_enum}.{record.source_value}"
            )
        if record.target_value is None:
            raise UnsupportedV2MappingError(
                f"Missing M2 target for {record.source_enum}.{record.source_value}"
            )
        mapped.append(ContextEvidence(Context(record.target_value)))
    return frozenset(mapped), tuple(losses)


def _records_for(values: object, table: Mapping[object, V2MappingRecord]) -> Tuple[V2MappingRecord, ...]:
    return tuple(_record_for(item, table) for item in sorted(values, key=lambda item: item.value))


def _record_for(value: object, table: Mapping[object, V2MappingRecord]) -> V2MappingRecord:
    record = table[value]
    if record.classification == MappingClassification.NO_SAFE_MAPPING:
        raise UnsupportedV2MappingError(
            f"Unsupported V2 mapping for {record.source_enum}.{record.source_value}"
        )
    if record.target_value is None:
        raise UnsupportedV2MappingError(
            f"Missing M2 target for {record.source_enum}.{record.source_value}"
        )
    return record
