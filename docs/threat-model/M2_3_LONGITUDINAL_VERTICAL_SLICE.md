# M2.3 Longitudinal Vertical Slice

Status: **EXPERIMENTAL** deterministic end-to-end harness over already
normalized evidence.

M2.3 composes frozen components:

```text
NormalizedTurnEvidence
    -> M2.0 ConversationState
    -> M2.1 LongitudinalRiskState
    -> M2.2 Coordinator / PolicyState
    -> existing CanaryPolicy
    -> controlled authorization projection
```

It does not call extractors or model providers. It does not integrate speech,
image recognition, the production pipeline, server, frontend, Trusted Circle,
or real notification delivery.

## Session State

`LongitudinalSessionState` contains:

- `ConversationState`
- `LongitudinalRiskState`
- `PolicyState`

The three states must share a session id. M2.3 does not add raw transcript,
provider response, wall-clock, UUID, or side-effect state.

## Turn Result

`process_normalized_turn()` returns a `LongitudinalTurnResult` containing:

- M2.0 transition details;
- M2.1 risk transition projection, except exact replay no-ops;
- M2.2 policy event;
- a deterministic Canary authorization projection;
- previous and next immutable session state.

Canary timestamps are excluded from M2.3 serialized output. This preserves
deterministic replay while retaining the controlled policy meaning:
`ALLOW`, `DENY`, `ASK_USER`, or `NOT_REQUESTED`.

## Canary Boundary

M2.2 `WARN` and `ESCALATE` are Canary-facing signals, not authority. M2.3
records whether the existing Canary policy authorized `warn_user`; it does not
execute the action. A Canary authorization is evidence of policy permission,
not a side effect.

## Replay

Exact M2.0 replay is a session-level no-op. It does not add risk history, policy
history, Canary authorization, or session evolution. Conflicting replay is
surfaced through the existing M2.0 conflict behavior.

## Canonical Six-Turn Fixture

1. Bank pretext only: no active danger, no policy event, no Canary request.
2. Benign account discussion: no dangerous intervention.
3. Current OTP disclosure request to caller: risk becomes `CRITICAL`, M2.2
   emits `ESCALATE`, Canary authorizes `warn_user`.
4. Same OTP request repeated: danger remains represented, duplicate warning is
   suppressed, no new Canary authorization is requested.
5. Precise OTP retraction: matching factor is retracted, current risk decreases,
   peak risk remains, no new warning.
6. New remote-access request: immediate re-escalation, materially new semantic
   factor, M2.2 emits `ESCALATE`, Canary authorizes `warn_user` again.

## Constitutional Invariants

**KNOWLEDGE IS NOT AUTHENTICATION.**

**TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

**SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

**MODEL OUTPUT IS EVIDENCE, NOT AUTHORITY.**

Context, identity claims, model output, accumulated trust, and benign history do
not directly authorize side effects.

## Privacy

Persistent/session/result structures contain controlled typed evidence,
fingerprints, risk state, policy state, and controlled decisions only. They do
not contain transcript text, raw model output, provider responses, API keys,
authorization headers, authentication tokens, or secret values.
