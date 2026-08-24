# Guardian Call Architecture

## Reading this document

The diagrams below describe three different systems. Only the first is the
current production path. The second is isolated experimental research. The
third is planned work.

## 1. Current M0 production architecture

**IMPLEMENTED / TESTED**

```text
Synthetic or operator-provided text
                 |
                 v
        GeminiSignalExtractor
        factual M0 extraction
                 |
                 v
          ScamSignals M0
                 |
                 v
     deterministic RiskEngine
      level + explicit reasons
                 |
                 v
            CanaryPolicy
       authorize warn_user?
          /              \
         v                v
 ACTION_ALLOWED      ACTION_DENIED
         |                |
         v                +--> no warning action
 authorized warning
         |
         v
    USER_WARNING event
```

### Responsibility boundaries

**GeminiSignalExtractor** extracts factual fields into the fixed M0 schema. Its
system instruction explicitly forbids risk scoring and safety decisions.

**RiskEngine** is deterministic. It maps M0 signals to `NORMAL`, `SUSPICIOUS`,
`HIGH`, or `CRITICAL`, with reasons and contributing signals.

**CanaryPolicy** is the authorization boundary. Current pipeline execution asks
whether `warn_user` is allowed. High and critical risk authorize that action;
normal and suspicious risk deny it under M0 policy.

**Actions** execute only after an `ALLOW` decision. Direct warning execution
without Canary authorization raises an error.

### API and observability

```text
Browser POST /api/v1/analyze
             |
             v
      GuardianPipeline.process_text()
             |
             +--> REST response
             |
             +--> canonical events
                       |
                       v
            /api/v1/events/stream (SSE)
                       |
                       v
              GC-80 workstation
```

The workstation displays conversation input, the live signal rail, risk
reasons, the M0 signal register, Canary authority, and the domain-event TTY.
Its 450 ms visual queue is presentation persistence only. The TTY receives real
events immediately, and no synthetic UI states are written into domain history.

`ACTION_ALLOWED` moves the visual point across the Canary boundary.
`ACTION_DENIED` leaves it stopped at the boundary. A `USER_WARNING` event moves
the point to action and opens the interrupt. Acknowledging the interrupt is
local UI state and does not alter backend history or policy.

### M0 event contract

Successful extraction and allowed warning:

```text
INPUT_RECEIVED -> SIGNAL_DETECTED -> RISK_UPDATED
-> CANARY_EVALUATION -> ACTION_ALLOWED -> USER_WARNING
```

Successful extraction and denied warning:

```text
INPUT_RECEIVED -> SIGNAL_DETECTED -> RISK_UPDATED
-> CANARY_EVALUATION -> ACTION_DENIED
```

Extraction failure:

```text
INPUT_RECEIVED -> EXTRACTION_FAILED
```

Risk and Canary do not run after extraction failure.

## 2. Experimental research architecture

**EXPERIMENTAL / TESTED / ISOLATED FROM PRODUCTION**

```text
57-case adversarial corpus
            |
            v
human-curated semantic ground truth
            |
            v
      ScamSignalsV2
            |
            v
 M1.2A semantic comparator <--- synthetic observed V2 replay
            |
            v
 structured extraction differences
 + extraction-impact diagnostics
 + aggregate metrics
```

The 57 V2 mappings are expected semantic representations. They are not model
output, a fraud-rule database, or a RiskEngineV2 specification.

`ScamSignalsV2` has four top-level semantic dimensions:

- identity pretext: claimed entity types and knowledge categories;
- contexts: affected domain or relationship;
- interaction acts: action, protected asset, semantic direction, actor, and
  destination;
- manipulation: pressure tactics that can amplify behavior but are not a
  prerequisite for representing it.

Identity assurance is external to conversational extraction and defaults to
`UNVERIFIED` in M1.1 mappings. Conversation cannot set independent verification.

The M1.2A comparator is provider-independent. It compares two already-parsed V2
objects, matches exact acts first, then deterministically pairs remaining acts
by field-equality distance. Its extraction-impact labels describe the possible
consequence of a semantic extraction mistake. They are not fraud risk levels.

The research package is not imported by production M0. No experimental field
enters RiskEngine, Canary, server responses, SSE, or the frontend.

## 3. Future M1.2B

**PLANNED / NOT YET IMPLEMENTED**

```text
conversation
     |
     v
Gemini V2 extractor
     |
     v
observed ScamSignalsV2
     |
     +--------------------------+
                                v
expected ground truth <-> frozen M1.2A comparator
                                |
                                v
                   live extraction benchmark report
```

There is currently no Gemini V2 extractor, provider adapter, live V2 benchmark,
or production V2 path. The planned extractor would feed the existing pure
comparator; it would not change comparator semantics.

## What is intentionally absent

- **PLANNED** RiskEngineV2: no design or implementation exists.
- **PLANNED** session semantics: experimental M2 work is paused outside `main`.
- **PLANNED** audio/telephony: no current audio processing path exists.
- **PLANNED** identity verification: no independent assurance channel exists.
- **PLANNED** Trusted Circle integration: M0 defines policy types but does not
  execute trusted-contact delivery in the current pipeline.
- **PLANNED** production persistence: current event sinks and benchmark outputs
  are in-memory or operator-visible and are not a production audit store.

## Privacy boundary

M0 domain events use structured payloads and record input length instead of raw
input in `INPUT_RECEIVED`. V2 mappings and evaluator outputs store semantic
categories rather than sensitive values. However, current production text is
sent to Gemini for extraction. Guardian Call therefore must not be described as
fully local or as providing proven end-to-end transcript privacy.

See [Privacy and Safety](PRIVACY_AND_SAFETY.md) for the precise current claims.
