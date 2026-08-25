# M2.0 Longitudinal Evidence Architecture

Status: **EXPERIMENTAL** M2.0 state infrastructure. It is not connected to the
production extractor, RiskEngine, CanaryPolicy, server, or frontend.

## Constitutional boundary

**KNOWLEDGE IS NOT AUTHENTICATION.**

**TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

**SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

M2.0 records normalized evidence. It assigns no fraud likelihood, risk score,
authorization, or intervention consequence.

## Flow and isolation

```text
raw turn -> extractor -> NormalizedTurnEvidence -> pure reducer
                          raw turn discarded       |
                                                   v
                                           ConversationState
```

The longitudinal package has no extractor dependency and does not import
`guardian.experimental`. Evidence may originate from any future adapter or from
an offline fixture. M2.0 does not adapt M0 or ScamSignalsV2.

## Neutral evidence contract

`NormalizedTurnEvidence` is immutable and contains only:

- an externally supplied opaque `turn_id` and monotonic `turn_number`;
- controlled context observations;
- controlled identity/pretext claims;
- controlled manipulation observations;
- typed behavioral acts.

A behavioral act is represented by:

```text
temporal scope + action + protected asset + actor + destination
```

`Destination` always means the control boundary receiving the asset,
capability, or effect. It does not represent software installation location.
An optional protected asset is a semantic category such as `OTP`, not a raw
value. `UNKNOWN` actor/destination means the normalized evidence did not
establish that dimension; it does not imply safety or danger.

Identity claims are conversational pretexts only. The state has no identity
assurance field and cannot convert a claim into authentication.

## Temporal semantics

- `CURRENT`: the act or observation applies in the present turn.
- `HISTORICAL`: a report of past activity.
- `HYPOTHETICAL`: conditional, illustrative, or training content.
- `NEGATED`: explicit negation or retraction of the same semantic act.
- `ACCUMULATED_CONTEXT`: retained background context, not a current act.

Scope is structural evidence only. M2.1 will determine risk consequences.
Historical, hypothetical, negated, and current OTP acts have different stable
fingerprints and remain separately auditable.

## State and reduction

`ConversationState` is a frozen value. `apply_turn(state, evidence)` performs no
I/O and returns a frozen `StateTransition` containing the next state and compact
change metadata. Inputs are never mutated. Session IDs, turn IDs, and turn
ordinals are supplied externally; the reducer generates no UUIDs or timestamps.

Equivalent observations under different turn IDs are compacted into occurrence
records with `first_seen`, `last_seen`, a capped count, and a saturation flag.
This records repetition without assigning it risk significance.

## Replay contract

The default replay index retains 32 accepted turns. Inside that window:

- identical `turn_id`, ordinal, and normalized evidence is an exact no-op;
- the same ID with different evidence raises `TurnConflictError`.

Turns use consecutive externally supplied ordinals. Once an ID leaves the
bounded replay index, an old ordinal is rejected as outside the replay window;
it is never silently applied again. Future ordinals with gaps are also rejected.
This provides bounded exact idempotency without an unbounded ID set.

## Bounds and compaction

Defaults are engineering limits, not scientific or policy thresholds:

- processed replay records: 32;
- detailed unique act aggregates: 64;
- occurrence/retraction count: 255.

All are configurable through immutable `StateLimits`. Context, identity claim,
and manipulation aggregates are bounded by their finite controlled vocabularies.
Act eviction is deterministic: least recently seen, then first seen, then stable
fingerprint. Evicted detail moves into a compact aggregate keyed by the complete
act fingerprint. It therefore preserves temporal scope, action, protected asset,
actor, and destination together with bounded first-seen, last-seen, occurrence,
and retraction metadata. Repeated observations update the same compact entry;
raw turn snapshots do not accumulate.

The compact ledger has a hard structural ceiling because every fingerprint is a
combination of finite controlled enums and an optional controlled asset. It
cannot grow through arbitrary text or identifiers. M2.1 must assess practical
memory limits before any vocabulary expansion or production integration.

## Negation and retraction

An act fingerprint includes its temporal scope. A separate semantic fingerprint
contains only action, protected asset, actor, and destination. Explicit
`RETRACTABLE_TARGET_SCOPES` currently contains only `CURRENT`. A `NEGATED` act
therefore links only to prior current acts with the exact semantic fingerprint;
historical, hypothetical, accumulated-context, and already-negated evidence are
not eligible targets. The target and negation remain in the detailed or compact
ledger; no evidence is deleted. Thus a password negation cannot retract an
unrelated OTP request. Repeated real negations deterministically update the
current target's capped retraction count and last-retracted ordinal. M2.0 records
these relationships but assigns no resolution or risk consequence.

## Privacy invariants

Persistent state contains controlled enums, normalized semantic fingerprints,
counters, external opaque identifiers, and turn-relative ordinals only. It has
no field for raw text, transcript fragments, secret values, provider responses,
or exceptions. Fingerprints are computed only from normalized enum fields;
raw text and secrets must never be hashed or passed to the reducer.

Identifiers accept at most 64 restricted ASCII characters and must start with a
letter. The caller remains responsible for generating opaque identifiers rather
than embedding PII or secrets. Extraction adapters must discard raw input before
constructing persistent state.

## Deterministic serialization

`to_json()` uses UTF-8-compatible ASCII JSON with sorted object keys, compact
separators, enum values as uppercase strings, and canonically sorted controlled
collections. Semantic fingerprints are SHA-256 over exactly those canonical JSON
bytes. No time, random value, object address, or platform newline enters the
serialized representation.

## Deferred to M2.1 and later

M2.0 intentionally leaves these questions unresolved:

- escalation, decrease, decay, and resolution policy;
- current and peak longitudinal risk;
- contradiction consequences;
- Canary evaluation and warning deduplication;
- production extractor and server integration;
- an experimental ScamSignalsV2 adapter.
