# M2.2 Longitudinal Coordinator

Status: **EXPERIMENTAL** deterministic coordinator between M2.0 state, M2.1
risk transitions, and Canary-facing policy events.

M2.2 is not production integration. It does not connect to the server,
frontend, model providers, external messaging, identity verification, or real
notifications.

## Architecture

```text
NormalizedTurnEvidence
    -> ConversationState / apply_turn
    -> LongitudinalRiskState / evaluate_risk_transition
    -> PolicyState / deduplication
    -> Canary-facing policy event
```

`ConversationState` remains semantic memory. `LongitudinalRiskState` remains
risk memory. `PolicyState` stores only intervention memory. No layer is
overloaded with another layer's responsibility.

## Policy Events

M2.2 emits a small controlled vocabulary:

- `NO_ACTION`
- `WARN`
- `ESCALATE`

`WARN` and `ESCALATE` are policy events only. They do not send notifications,
display UI, contact anyone, or perform external side effects.

## Canary Compatibility

Existing Canary can be reused unchanged for the current milestone. The
coordinator adapts longitudinal risk into a deterministic `RiskAssessment` and
uses Canary's existing `WARN_USER` authorization semantics. Canary timestamps
are not persisted in M2.2 state, preserving deterministic replay.

## Deduplication

Deduplication is based on semantic fingerprints from normalized evidence, never
transcript strings.

- Same active danger: duplicate warning is suppressed.
- Risk increase: a new policy event is allowed.
- New dangerous factor: a new policy event is allowed even if risk remains
  `CRITICAL`.
- Resolved/retracted danger: warning memory clears when no active factor
  remains.
- Danger returns: a later matching current danger can emit again.

## Constitutional Invariants

**KNOWLEDGE IS NOT AUTHENTICATION.**

**TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

**SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

**MODEL OUTPUT IS EVIDENCE, NOT AUTHORITY.**

Identity claims, context, accumulated legitimacy, and prior benign behavior do
not authorize side effects and do not suppress a later current sensitive
request.

## Temporal Handling

Historical, hypothetical, negated, warning, and self-service evidence do not
produce the same intervention behavior as a current external sensitive request.
Retraction can reduce active risk and clear warning memory, but it does not
delete prior evidence, prior peak risk, or audit history.

## Privacy

M2.2 state contains controlled enum values, risk levels, reasons, bounded
history, and semantic fingerprints. It contains no transcript text, raw model
output, secret values, API credentials, authentication tokens, authorization
headers, or notification payloads.

## Deferred

Production events, visualizer integration, server wiring, warning cooldown
presentation, Trusted Circle delivery, and Canary escalation side effects remain
deferred to later milestones.
