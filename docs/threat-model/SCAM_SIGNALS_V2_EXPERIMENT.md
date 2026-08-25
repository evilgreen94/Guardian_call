# ScamSignalsV2 Experimental Schema

## Status and boundary

`ScamSignalsV2` is an M1.1 schema experiment. It is parallel to the canonical
M0 `ScamSignals` model and is not connected to Gemini, `GuardianPipeline`,
`RiskEngine`, Canary, the server API, or the frontend. It does not define
RiskEngine v2 policy. The 57 mappings are diagnostic representations, not
future risk rules.

## Constitutional constraints

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

Conversational identity claims and knowledge belong only to
`IdentityPretext`. They cannot set `IdentityAssurance`. M1.1 defaults external
assurance to `UNVERIFIED` because Guardian has no independent identity channel.

## Central behavioral representation

Behavioral evidence is represented compositionally as:

```text
semantic direction + action + protected asset + destination
```

`identity_pretext` and `contexts` add context, not proof or standalone
suspicion. `manipulation` records pressure tactics as amplifiers; dangerous
behavior remains representable without them. Mixed utterances use multiple
`InteractionAct` values so a safety statement cannot erase a simultaneous
dangerous request.

## Destination semantics

`Destination` has one meaning: **the ownership or control boundary that receives
the result of the represented act**. Depending on the act, that result can be
information, economic value, a capability, or a security-state effect.

- `CALLER`: the result passes under the caller's control.
- `THIRD_PARTY`: it passes to another non-caller external party.
- `OFFICIAL_SELF_SERVICE`: it remains in an official user-operated channel.
- `USER_CONTROLLED`: it remains within the user's own control boundary.
- `EXTERNAL_ACCOUNT`: economic value reaches an externally controlled account
  or wallet.
- `UNKNOWN`: the utterance does not establish the receiving boundary.

Installation location is not a second meaning of `Destination`. For example,
installing remote software has `USER_CONTROLLED` as its immediate result
boundary, while granting the resulting remote-control capability is a separate
act whose destination is `CALLER`. M1.1 intentionally has no independent
installation-location field.

## Asset compatibility

Every sensitive asset has one category and subtype. The explicit compatibility
table in `signals_v2.py` is exhaustive: secrets, payment-card data, economic
value, account control, and device access each admit only their listed
subtypes. Construction and parsing reject crossed combinations rather than
coercing them.

No model field stores transcript text, OTPs, passwords, card values, recovery
codes, private keys, seed phrases, or other raw sensitive values.

## Evidence-bounded vocabulary

The taxonomy is bounded by the current 57-case corpus. Automated coverage tests
require every enum value to occur in at least one mapping, with only two
documented exceptions:

- `IdentityAssurance.VERIFIED_EXTERNALLY` is necessary to represent a future
  positive result from an independent verification channel.
- `IdentityAssurance.VERIFICATION_FAILED` is necessary to distinguish an
  explicit failed external check from no check (`UNVERIFIED`).

Neither exception is inferred from conversation or used by production M0.
Adding any other unused value fails vocabulary coverage until corpus evidence
or an explicit architectural justification is supplied.

## Corpus mapping

The existing scenario document contains a `v2_mappings` object keyed by the
same 57 scenario IDs. It does not duplicate raw conversation text. Each entry
contains `signals`, external `identity_assurance`, and explicit ambiguity
metadata. `ambiguous_security_digits` uses an unspecified security-code subtype
and unknown actor/destination, preserving uncertainty instead of forcing a
request classification.

