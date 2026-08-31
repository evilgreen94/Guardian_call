# Guardian Call Privacy and Safety

## Scope of these claims

This document originally described checkpoint `guardian-m1.2a`. The current
hackathon demo now includes a protected-user Guardian UI, a Canary diagnostic
visualizer, an experimental V2 turn endpoint, and controlled browser STT. It
does not claim certified security, regulatory compliance, production-grade
privacy, or protection against every scam.

## Constitutional principles

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These principles constrain architecture and evaluation. They do not establish
system accuracy or authenticate any caller.

## Current M0 privacy boundary

**IMPLEMENTED / TESTED**

`INPUT_RECEIVED` events store input length and input type rather than the raw
text. Downstream domain events use structured signals, risk reasons, policy
decisions, and warning directives. Tests check that synthetic secret contents
do not appear in emitted event payloads.

**Important current limitation:** production input text is sent to Gemini for
semantic extraction. Current production processing is therefore not fully
local and must not be described as private on-device transcript processing.
Provider handling, transport, retention, deployment configuration, and user
consent require separate production review beyond this repository.

The FastAPI response can include structured signals, risk reasons, Canary
decisions, warnings, and event payloads. Extraction failures include an error
type and message. These surfaces must be reviewed before any real-user or
production deployment.

## Data minimization in experimental V2

**EXPERIMENTAL / TESTED**

`ScamSignalsV2` stores controlled semantic categories. It does not store:

- OTP or verification-code contents;
- passwords or PIN contents;
- payment-card numbers;
- CVV/CVC values;
- recovery-code contents;
- seed phrases;
- private keys;
- raw addresses;
- government-ID values;
- raw personal-knowledge values;
- transcript text.

Identity pretext records claimed entity types and categories of knowledge, such
as `ADDRESS` or `TRANSACTION_DETAILS`, without storing the value. Interaction
acts record action, asset category/subtype, direction, actor, and destination.
Strict parsing rejects unknown and raw-value fields.

The 57-case corpus does contain synthetic conversation text for repeatable
research. M1.2A output hides that text by default and displays it only through
an explicit CLI option. The corpus must never be populated with real secrets,
credentials, accounts, identifiers, or personal data.

## Identity and apparent credibility

Current Guardian Call has no independent identity-verification channel.
Conversational claims, employee IDs, customer references, account details, and
incident knowledge are evidence of pretext, not authentication.

M1.1 defines external `IdentityAssurance` states so a future independent source
could be represented without inferring verification from conversation. All
current mappings use `UNVERIFIED`. `VERIFIED_EXTERNALLY` and
`VERIFICATION_FAILED` exist as experimental vocabulary only; no current system
produces those outcomes.

## Deterministic safety boundaries

**IMPLEMENTED / TESTED in M0**

Gemini extracts M0 signals but is instructed not to calculate risk, determine
fraud, advise the user, or authorize action. RiskEngine applies explicit rules
and returns reasons. CanaryPolicy separately decides whether `warn_user` may
execute.

Tests enforce that:

- a denied warning action cannot execute;
- normal and suspicious M0 states do not authorize `warn_user`;
- high and critical M0 states do authorize `warn_user`;
- transcript sharing is denied by default policy;
- autonomous call termination requires user involvement in the policy model;
- extraction failure stops before risk, Canary, and warning execution;
- `USER_WARNING` follows an allowed Canary decision.

Defining a policy type is not the same as integrating a feature. Trusted Circle
delivery, autonomous telephony control, and production notification channels are
not implemented in the current M0 pipeline.

## Ambiguity and extraction errors

**EXPERIMENTAL / TESTED**

The corpus preserves `ambiguous_security_digits` rather than forcing a single
semantic truth. M1.2A marks ambiguous references and excludes them from strict
accuracy while retaining their structural comparison.

M1.2A reports missing, spurious, and mismatched semantic evidence explicitly.
Extraction-error impact is separate from fraud risk. A critical-impact
direction flip means the representation error could seriously distort future
reasoning; it does not mean the underlying conversation received a critical
risk assessment.

Production M0 also makes extraction failure explicit through
`EXTRACTION_FAILED`. It does not fabricate replacement signals or continue to
RiskEngine and Canary.

## Current demo surfaces and experimental isolation

The current browser demo serves:

- `/guardian/` as the protected-user Guardian UI;
- `/visualizer/` as the technical Canary/observability visualizer;
- `/api/v1/experimental/v2/turn` for the experimental V2 turn path;
- `/api/v1/experimental/stt` for controlled browser-audio transcription.

The STT route receives browser-recorded audio blobs in the demo. It is not a
phone-carrier integration, not direct cellular-call capture, and not a
production telephony privacy model.

V2 and M1.2A live under `guardian.experimental` and are not exported through
the production package. The hackathon demo intentionally exposes an
experimental V2 turn route and adapts supported V2 acts into the demo
longitudinal/Canary path. This should be described as experimental demo
integration, not as a hardened production API or RiskEngineV2.

M2 session work remains outside `main` on `wip/m2-paused-session`. It must not be
used as evidence of current privacy, retention, or session behavior.

## Known limitations

- Production input text leaves the local process for Gemini extraction.
- There is no independent caller-identity verification.
- There is no implemented consent, account, deletion, or retention product
  workflow.
- There is no production persistent audit design on `main`.
- The local SSE broadcast uses in-memory subscriber queues and is not a
  hardened authorization boundary.
- CORS is permissive for local development.
- M0's schema omits several sensitive asset and action categories.
- V2 privacy properties apply to V2 structured mappings and evaluator output,
  not automatically to future provider prompts or production logs.
- No live V2 extraction benchmark exists.
- Browser microphone STT exists for the controlled demo, but no direct
  telephony privacy model exists because phone/carrier integration is not
  implemented.

## Requirements before broader deployment

**PLANNED**

A production path would require explicit consent and disclosure; provider data
handling review; transport and access controls; retention and deletion policy;
authentication and authorization for APIs/SSE; threat modeling for logs and
operator access; redaction and bounded error reporting; abuse monitoring; and
validation with representative users. None is implied by the current
hackathon prototype.
