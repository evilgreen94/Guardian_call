# Guardian Call: Project Overview

## The problem

Modern conversational scams often mix correct personal context with urgency, authority, secrecy, or a dangerous request. Knowing a person's provider, address, or recent activity does not authenticate a caller. Guardian Call focuses on the decision window in which a person is asked to disclose a secret, transfer money, install software, or approve an account action.

## The product

Guardian Call has two browser surfaces:

- `/guardian/` is the calm protected-user experience.
- `/visualizer/` is the KERN-3 technical observability workstation.

The Guardian UI accepts typed text through `/api/v1/analyze`. Its bounded browser voice path transcribes through `/api/v1/experimental/stt`, then sends the transcript through `/api/v1/analyze`. The primary UI is single-turn and does not call the experimental V2 turn endpoint.

## Responsibility boundaries

```text
Text -> GeminiSignalExtractor -> ScamSignals M0
     -> deterministic RiskEngine -> KERN-3 -> authorized action
```

Gemini extracts structured facts. It does not calculate risk, decide whether a conversation is a scam, or authorize an action.

The deterministic `RiskEngine` produces a qualitative level, explicit reasons, and contributing signals.

KERN-3 is the policy authority boundary. It is internally implemented as `CanaryPolicy`; existing fields and canonical events such as `canary_decision` and `CANARY_EVALUATION` remain stable contracts. A warning cannot execute when policy denies it.

## Current implementation

- FastAPI modular monolith hosted on Google Cloud Run.
- Schema-constrained Gemini M0 extraction using `gemini-3.6-flash` by default.
- Deterministic risk and authorization logic.
- REST responses plus canonical Server-Sent Events.
- Canvas 2D Guardian presence with responsive and reduced-motion behavior.
- Technical V2/STT demo path isolated from the primary Guardian text flow.
- Process-local in-memory experimental session state.

## Evaluation

The synthetic adversarial corpus contains 57 scenarios: 37 scam cases, 19 legitimate controls, and 1 ambiguous case. The frozen M0 oracle baseline records 24 passes, 10 risk mismatches, 22 model gaps, and 1 ambiguous case. It bypasses Gemini and therefore is not model accuracy.

The final local freeze gate passes 331 software regression tests. That count measures code and contract coverage, not detection accuracy or production reliability.

## Safety principles

> KNOWLEDGE IS NOT AUTHENTICATION.

> TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.

> SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.

Extraction failure is terminal for that analysis. Guardian does not fabricate empty signals or convert provider failure into a safe verdict.

## Current limitations

- No independent caller authentication or reliable speaker provenance.
- No direct phone-call interception or carrier integration.
- Browser microphone input is a controlled demo path.
- Provider-backed text and audio are processed through Gemini cloud APIs.
- Primary Guardian analysis is single-turn.
- Experimental V2 sessions are not durable or multi-instance safe.
- No production persistence or Trusted Circle delivery.

## Status vocabulary

- **IMPLEMENTED:** present and reachable in the current codebase.
- **TESTED:** covered by software regression tests or a recorded deterministic evaluation.
- **EXPERIMENTAL:** implemented for research/demo use without a production claim.
- **PLANNED:** proposed work with no claim of implementation.

Detailed research evidence remains under [`docs/threat-model/`](../threat-model/).
