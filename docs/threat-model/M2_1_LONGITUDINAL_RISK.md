# M2.1 Longitudinal Risk Transitions

Status: **EXPERIMENTAL** deterministic risk layer over the frozen M2.0
`ConversationState` and `NormalizedTurnEvidence` foundation.

M2.1 is not connected to the production extractor, server, frontend, Gemini,
Gemma, RiskEngine, or Canary.

## State

`LongitudinalRiskState` is immutable and records:

- `previous_risk`
- `current_risk`
- `peak_risk`
- bounded unresolved factor fingerprints
- bounded transition history
- explicit reasons for each transition

It stores controlled enums, fingerprints, counters, and turn-relative ordinals
only. It stores no raw transcript text, secrets, provider responses, or policy
authorization.

## Transition Semantics

Risk is recalculated after each M2.0 `StateTransition`. It is not monotonically
increasing:

- current actionable sensitive acts can raise active risk;
- precise retractions can remove only matching current unresolved factors;
- benign turns can move unresolved risk through a bounded residual window;
- `peak_risk` remains as audit memory after `current_risk` decreases;
- a new current dangerous act immediately re-escalates.

## Constitutional Invariants

**KNOWLEDGE IS NOT AUTHENTICATION.**

**TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

**SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

Context and identity claims can corroborate later evidence but never
authenticate a caller, prove safety, or independently create critical risk.

## Temporal Handling

Only `CURRENT` actionable sensitive acts drive active risk. `HISTORICAL`,
`HYPOTHETICAL`, and `NEGATED` acts remain auditable but are not treated as
current requests. `ACCUMULATED_CONTEXT` may corroborate a later current act but
is not independently actionable.

## Retraction

Retraction uses M2.0 semantic fingerprints: action, asset, actor, and
destination must match exactly. Retraction does not delete audit history and
does not prove safety by itself. Unrelated negations do not clear active
factors.

## Residual Policy

The default residual policy is turn-relative and bounded. After an active
dangerous factor is no longer unresolved, the prior risk decays by one level per
benign transition and then clears. Wall-clock time is not used.

This one-risk-level-per-benign-transition rule is an experimental deterministic
engineering policy for repeatable evaluation. It is not an empirical claim about
real-world scam persistence or time-to-safety.

## Deferred

M2.1 does not implement warning cooldown, Canary policy, production event
emission, model routing, extractor integration, or user-facing interventions.
