# M2.4 V2 Turn Adapter

Status: **EXPERIMENTAL** deterministic adapter from already-validated
`ScamSignalsV2` into extractor-independent M2 `NormalizedTurnEvidence`.

M2.4 does not call Gemini, Gemma, Ollama, speech-to-text, the production
pipeline, server, frontend, network services, or external side effects.

## Dependency Direction

The dependency direction is:

```text
guardian.experimental.signals_v2
    -> guardian.experimental.v2_turn_adapter
    -> guardian.longitudinal.evidence
    -> M2.3 longitudinal session stack
```

The longitudinal core does not import `guardian.experimental`. Production M0
does not import the M2.4 adapter.

## Adapter Interface

`adapt_v2_turn(session_id, turn_id, ordinal, signals)` returns one
`NormalizedTurnEvidence` object. The caller supplies session identity, turn
identity, and ordinal. The adapter creates no UUIDs, timestamps, provider
metadata, or wall-clock state.

`session_id` is accepted to keep the call boundary explicit, but M2 conversation
state owns session identity; `NormalizedTurnEvidence` itself stores only the
opaque turn id and ordinal.

Unsupported mappings raise `UnsupportedV2MappingError`. The adapter does not
retry, repair, guess aliases, fuzzy-match values, or translate evidence into
risk directly.

## Constitutional Invariants

**KNOWLEDGE IS NOT AUTHENTICATION.**

**TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

**SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

**MODEL OUTPUT IS EVIDENCE, NOT AUTHORITY.**

Identity claims remain neutral claims. Context remains background evidence.
Manipulation remains evidence. Canary remains the authority boundary for any
later consequential action.

## Mapping Coverage

The deterministic mapping report covers all 97 current V2 enum values:

| Classification | Count | Meaning |
| --- | ---: | --- |
| `EXACT_MAPPING` | 62 | Same security meaning is available in M2. |
| `LOSSLESS_NORMALIZATION` | 10 | M2 uses a different name or grouping without relevant loss. |
| `PARTIAL_MAPPING` | 14 | M2 preserves the safety-relevant meaning but loses a subtype or distinction. |
| `NO_SAFE_MAPPING` | 11 | M2 has no neutral representation; adapter fails safely if encountered. |

## Identity And Knowledge

| V2 value | M2 value | Classification |
| --- | --- | --- |
| `BANK` | `FINANCIAL_INSTITUTION` | `EXACT_MAPPING` |
| `TELECOM` | `TELECOM_PROVIDER` | `EXACT_MAPPING` |
| `TECH_SUPPORT` | `TECH_SUPPORT` | `EXACT_MAPPING` |
| `SOCIAL_PLATFORM` | `ONLINE_SERVICE` | `LOSSLESS_NORMALIZATION` |
| `ECOMMERCE` | `MERCHANT` | `EXACT_MAPPING` |
| `GOVERNMENT_AUTHORITY` | `GOVERNMENT_AUTHORITY` | `EXACT_MAPPING` |
| `POLICE` | `LAW_ENFORCEMENT` | `EXACT_MAPPING` |
| `FAMILY_MEMBER` | `FAMILY_OR_ACQUAINTANCE` | `EXACT_MAPPING` |
| `ACCOUNT_SUPPORT` | `ONLINE_SERVICE` | `PARTIAL_MAPPING` |
| `CRYPTO_SUPPORT` | `CRYPTO_SERVICE` | `EXACT_MAPPING` |
| `EMAIL_CLOUD_SUPPORT` | `ONLINE_SERVICE` | `PARTIAL_MAPPING` |

All V2 `KnowledgeCategory` values are `NO_SAFE_MAPPING`. M2 has no neutral
identity-knowledge evidence slot. Mapping knowledge to authentication would
violate the contract; mapping it to context would invent domain evidence.

## Context

All V2 contexts map exactly except:

| V2 value | M2 value | Classification |
| --- | --- | --- |
| `SOCIAL_MEDIA` | `SOCIAL_PLATFORM` | `LOSSLESS_NORMALIZATION` |
| `FAMILY` | none | `NO_SAFE_MAPPING` |

The family mapping fails safely because M2 currently has family-emergency
context, not generic family context. Mapping generic family context to
`FAMILY_EMERGENCY` would invent emergency semantics.

## Temporal Direction

| V2 direction | M2 scope | Classification |
| --- | --- | --- |
| `DIRECT_REQUEST` | `CURRENT` | `EXACT_MAPPING` |
| `INDIRECT_REQUEST` | `CURRENT` | `LOSSLESS_NORMALIZATION` |
| `PARTIAL_REQUEST` | `CURRENT` | `LOSSLESS_NORMALIZATION` |
| `NEGATION` | `NEGATED` | `EXACT_MAPPING` |
| `WARNING` | `HYPOTHETICAL` | `PARTIAL_MAPPING` |
| `QUESTION` | `HYPOTHETICAL` | `PARTIAL_MAPPING` |
| `HYPOTHETICAL` | `HYPOTHETICAL` | `EXACT_MAPPING` |
| `HISTORICAL` | `HISTORICAL` | `EXACT_MAPPING` |
| `THIRD_PARTY` | `HISTORICAL` | `PARTIAL_MAPPING` |
| `SELF_SERVICE` | `CURRENT` | `LOSSLESS_NORMALIZATION` |
| `DISCUSSION` | `HYPOTHETICAL` | `PARTIAL_MAPPING` |

`WARNING`, `QUESTION`, and `DISCUSSION` intentionally do not become current
external danger. They map to non-actionable M2 scope because M2 has no distinct
warning, question, or discussion scope. `WARNING` is not mapped to `NEGATED`
because that could incorrectly retract a prior current factor.

`THIRD_PARTY` intentionally does not become current user-directed danger. M2
lacks a dedicated third-party-report temporal scope, so the adapter maps it to
`HISTORICAL` as a partial conservative normalization while preserving actor,
asset, and destination evidence.

`SELF_SERVICE` remains current, but its destination control boundary is
preserved. M2.1 does not treat official self-service or user-controlled
destinations as active external danger.

## Actions

All V2 `ActionTypeV2` values map exactly by name to M2 `Action`:
`DISCLOSE`, `TRANSFER`, `AUTHORIZE`, `INSTALL`, `GRANT_ACCESS`,
`CHANGE_SECURITY`, `PURCHASE`, `WITHDRAW`, `NAVIGATE`, `ENTER`, `CONTACT`,
`REVIEW`, and `REJECT`.

The adapter does not make an action active by itself. Temporal direction and
destination remain attached to each act.

## Assets

Exact asset mappings:

`OTP`, `PASSWORD`, `RECOVERY_CODE`, `CARD_SECURITY_CODE`, `SEED_PHRASE`,
`PRIVATE_KEY`, `GIFT_CARD`, `CASH`, `CRYPTO_ASSET`, `LOGIN_APPROVAL`,
`REMOTE_SOFTWARE`, `REMOTE_CONTROL`, and `SCREEN_CONTENT`.

Lossless normalization:

| V2 asset | M2 asset |
| --- | --- |
| `PAYMENT_APP_PAYMENT` | `PAYMENT_APP_FUNDS` |

Partial mappings:

| V2 asset | M2 asset | Loss |
| --- | --- | --- |
| `GIFT_CARD_REDEMPTION_CODE` | `GIFT_CARD` | redemption-code subtype |
| `CARD_NUMBER` | `CARD_DATA` | card-number subtype |
| `CARD_EXPIRY` | `CARD_DATA` | expiry subtype |
| `FIAT_FUNDS` | `BANK_FUNDS` | fiat-funds generality |
| `RECOVERY_EMAIL` | `ACCOUNT_RECOVERY` | recovery-email subtype |
| `RECOVERY_PHONE` | `ACCOUNT_RECOVERY` | recovery-phone subtype |
| `TWO_FACTOR_SETTING` | `SECURITY_SETTINGS` | 2FA-setting subtype |
| `PASSWORD_RESET_LINK` | `ACCOUNT_RECOVERY` | reset-link subtype |

No-safe mapping:

| V2 asset | Rationale |
| --- | --- |
| `UNSPECIFIED_SECURITY_CODE` | M2 cannot distinguish OTP, PIN, CVV, or another security code without guessing. |

The adapter never stores secret values, OTP digits, passwords, card numbers, or
account numbers.

## Actor And Destination

Actors map exactly: `USER`, `THIRD_PARTY`, and `UNKNOWN`.

Destinations map exactly except `CALLER`, which maps losslessly to M2
`OTHER_PARTY`. External control boundaries are preserved:
`THIRD_PARTY`, `EXTERNAL_ACCOUNT`, `OFFICIAL_SELF_SERVICE`, `USER_CONTROLLED`,
and `UNKNOWN` are not swapped across trust boundaries.

## Manipulation

Exact mappings: `URGENCY`, `AUTHORITY_PRESSURE`, `SECRECY`, `ISOLATION`,
`PROTECTIVE_PRETEXT`, `REWARD`, and `SCARCITY`.

Lossless normalizations:

| V2 value | M2 value |
| --- | --- |
| `FEAR_THREAT` | `FEAR_OR_THREAT` |
| `KEEP_ON_CALL` | `KEEP_ENGAGED` |
| `EMOTIONAL_EMERGENCY` | `EMOTIONAL_PRESSURE` |

The adapter does not convert manipulation directly into risk. M2.1 evaluates
manipulation as an amplifier after adaptation.

## Offline Proof

Tests exercise direct and indirect OTP requests, warning/historical/hypothetical
OTP references, precise negation, official self-service OTP entry, transfer to
external account, remote software/control requests, identity-only evidence,
trust context followed by sensitive request, and multi-act preservation through
the M2.3 session stack.
