# Guardian Call: Project Overview

## Status vocabulary

- **IMPLEMENTED**: present on `main` and reachable in the current codebase.
- **TESTED**: covered by automated software tests or a recorded deterministic evaluation.
- **EXPERIMENTAL**: implemented for research but isolated from production.
- **PLANNED**: proposed direction with no claim of current implementation.

## Reconciliation note

This document originally described checkpoint `guardian-m1.2a` at commit
`f058fa6`. The current hackathon demo has since advanced to a protected-user
Guardian UI at `/guardian/`, a technical Canary visualizer at `/visualizer/`,
an experimental V2 turn endpoint, and controlled browser STT. The historical
105-test count below remains evidence for the older checkpoint only; it is not
the current regression count and is not model accuracy.

This document describes checkpoint `guardian-m1.2a` at commit `f058fa6`.
The complete software regression suite at that checkpoint contains 105 passing
tests. That number measures engineering coverage, not model accuracy.

## The problem

Modern phone scams are difficult because they rarely look like a single bad
keyword. A caller can know a person's name, address, provider, subscription, or
recent transaction. They can combine accurate details with urgency, authority,
secrecy, emotional pressure, or a supposedly protective action. The dangerous
part is often what the person is being asked to disclose, authorize, install,
or transfer, and where the result will go.

Guardian Call explores protection during that decision window: understand the
conversation, identify structured evidence, assess it explainably, and permit
an intervention only through an explicit policy boundary.

## Intended users

The intended protected user is someone handling a suspicious or confusing
call, including people who may be vulnerable to pressure, isolation, or a
convincing impersonation. A second interface serves technical operators,
evaluators, and hackathon judges who need to see why the system moved from
input to signal, risk, policy, and action.

Guardian Call is not a caller-authentication service. The current system has no
independent identity-verification channel.

## Constitutional design principles

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These are design constraints, not accuracy claims and not automatic scoring
rules. Caller knowledge is conversational context. It cannot prove identity or
neutralize evidence of a dangerous requested action.

## Guardian and Canary

**Guardian** is the protective system as a whole: extraction, deterministic
reasoning, observability, and authorized intervention.

**Canary** is the authority boundary inside Guardian. It does not extract
meaning and does not calculate risk. It decides whether a proposed
consequential action is allowed under policy. Current M0 processing asks Canary
whether `warn_user` is authorized. A warning action cannot execute when Canary
denies it.

The current demo presents Guardian and Canary as two browser surfaces:
`/guardian/` is the intended protected-user UI and `/visualizer/` is the
technical/diagnostic visualizer. The root route `/` redirects to `/guardian/`.

## Current production architecture

**IMPLEMENTED / TESTED**

```text
Text
  -> GeminiSignalExtractor
  -> ScamSignals M0
  -> deterministic RiskEngine
  -> CanaryPolicy
  -> ACTION_ALLOWED or ACTION_DENIED
  -> USER_WARNING only when authorized
```

The FastAPI application accepts a text snippet, runs this single-turn pipeline,
returns structured results, and broadcasts canonical domain events over SSE.
The GC-80 operator workstation renders the real event sequence. A presentation
queue makes rapid events legible without delaying backend execution or
fabricating domain timestamps.

The canonical successful intervention sequence is:

```text
INPUT_RECEIVED
SIGNAL_DETECTED
RISK_UPDATED
CANARY_EVALUATION
ACTION_ALLOWED
USER_WARNING
```

Denied actions stop at `ACTION_DENIED`. Extraction failures stop before risk
and Canary evaluation.

The Guardian UI uses the experimental demo endpoints
`/api/v1/experimental/v2/turn` and `/api/v1/experimental/stt`. Browser STT is a
controlled hackathon input path, not direct cellular call capture or production
telephony integration.

## What M0 demonstrates

M0 demonstrates a complete architectural boundary: Gemini extracts factual
signals; deterministic code produces explainable risk; Canary authorizes the
intervention; and real events make the transition observable. Automated tests
cover the critical OTP-warning path, benign restraint, extraction failure,
policy denial, and prevention of action execution without Canary authority.

M0 is intentionally narrow. Its flat signal model directly represents OTP and
password requests, transfer requests, remote access, urgency, secrecy,
financial context, and a claimed identity. It does not represent the full
modern scam surface.

## Adversarial reassessment

**IMPLEMENTED / TESTED diagnostic infrastructure**

The M1 corpus contains 57 synthetic scenarios across banking, telecom, social
media, ecommerce, government impersonation, family emergencies, payment apps,
technical support, account recovery, email/cloud, and crypto. It includes 37
scam cases, 19 legitimate controls, and one explicitly ambiguous case. Cases
contrast active requests with warnings, negation, questions, hypothetical and
historical language, third-party reports, self-service behavior, and ordinary
discussion.

The frozen M0 oracle baseline is:

```text
CASES                   57
PASS                    24
RISK MISMATCH           10
CANARY MISMATCH          0
MODEL GAP               22
AMBIGUOUS                1
```

This exposed schema gaps around payment-card data, recovery codes, login
approval, account-security changes, screen sharing, payment-app authorization,
gift cards, cash withdrawal, and wallet secrets. It also exposed benign cases
that M0 elevates to `SUSPICIOUS` because broad context can outweigh action
direction. Production rules were not changed to improve the baseline.

## Experimental semantic model

**EXPERIMENTAL / TESTED / NOT CONNECTED TO PRODUCTION**

`ScamSignalsV2` represents behavioral evidence compositionally:

```text
semantic direction + action + protected asset + destination
```

It also records identity pretext, knowledge categories, contexts, actor, and
manipulation. All 57 cases have human-curated V2 mappings. V2 stores categories,
not OTPs, passwords, card values, recovery codes, seed phrases, private keys,
addresses, government identifiers, or transcript text.

V2 is not exported through the public production package. The current
hackathon demo does expose an experimental Gemini V2 turn endpoint and adapts
supported V2 acts into the longitudinal demo path for Canary authorization.
There is still no production RiskEngineV2.

## Offline extraction evaluator

**EXPERIMENTAL / TESTED**

M1.2A compares expected and observed V2 structures with a pure semantic
comparator. It reports set differences, matched and unmatched interaction acts,
semantic-direction flips, and extraction-error impact. It does not call Gemini,
use the network, calculate fraud risk, or invoke Canary.

The 16 replay fixtures deliberately inject semantic errors to validate the
evaluator:

```text
SYNTHETIC OFFLINE REPLAY // NOT GEMINI ACCURACY
```

They are not observed model failures.

## Current limitations

- Production accepts one text input at a time and has no session memory.
- Production input text is sent to Gemini for extraction; processing is not
  fully local or private.
- M0's signal vocabulary is narrower than the documented threat model.
- Caller identity is not independently verified.
- V2 extraction by Gemini is implemented only as an experimental demo path.
- Live V2 benchmark results are separate evidence and must not be presented as
  production accuracy.
- Browser microphone STT is implemented for the demo; direct phone-call
  integration is not implemented.
- Trusted Circle delivery is not integrated into the current M0 pipeline.
- RiskEngineV2 does not exist.

## Paused and future work

**EXPERIMENTAL / PAUSED OUTSIDE `main`**

Multi-turn session work is preserved on `wip/m2-paused-session`. It was paused
so the threat model and semantic representation could be reconsidered first.
It is not evidence of current Guardian functionality.

**PLANNED / NOT YET IMPLEMENTED**

M1.2B is intended to connect a future Gemini V2 extractor to the frozen M1.2A
comparator, producing live expected-versus-observed extraction measurements.
Any production V2 risk policy, session model, audio path, independent identity
assurance, or trusted-contact delivery requires separate design and evidence.

## Evidence layer

Detailed research evidence remains in [`docs/threat-model/`](../threat-model/).
This hackathon layer summarizes the product and engineering record without
replacing the underlying threat model, corpus, baselines, or evaluator design.
