# Guardian Call - Devpost Submission

## Project name

Guardian Call

## Tagline

Agentic protection at the moment a conversation becomes dangerous.

## Problem

Conversational scams exploit pressure, trust, and plausible personal context. A caller may know accurate details and still ask the victim to reveal an authentication code, transfer money, install remote-access software, or approve an account action. Keyword blocking alone misses the requested behavior, while an unconstrained language model should not control a safety intervention.

## Why it matters

The decisive moment is often short: a person must act before they have time to verify the caller independently. Guardian Call explores how an AI system can understand that moment while preserving an explicit, testable authority boundary.

## What it does

Guardian accepts typed conversation text or a bounded browser microphone recording. It extracts structured evidence, calculates explainable qualitative risk, evaluates policy, and presents a warning only when KERN-3 authorizes it. A separate technical visualizer exposes the real pipeline fields and events.

## How it works

Gemini converts language into the fixed `ScamSignals` schema. It is non-authoritative: it does not score risk or choose an action. The deterministic `RiskEngine` calculates a level and reasons. KERN-3, internally implemented as `CanaryPolicy`, authorizes or denies `warn_user`. The action layer rejects execution without that authorization.

## Architecture

```text
Guardian UI -> FastAPI -> Gemini structured extraction
                         [LLM, NON-AUTHORITATIVE]
                    -> deterministic RiskEngine
                    -> KERN-3 authority boundary
                    -> no intervention | user warning
```

## Technologies

Python, FastAPI, Pydantic, Google Gen AI SDK, Gemini, JavaScript, Canvas 2D, HTML/CSS, Server-Sent Events, Docker, and Google Cloud Run.

## Google Cloud usage

Google Cloud Run hosts the API and both frontend surfaces in the `guardian-stable` service in `europe-west1`. The Gemini API credential is injected at runtime from Secret Manager; it is not stored in the repository or frontend.

## Gemini usage

The current M0 extractor uses `gemini-3.6-flash` for schema-constrained factual extraction. Browser audio transcription is an experimental demo input path. Gemini never decides risk and never authorizes a warning.

## Safety model

The design follows three constraints: knowledge is not authentication; trust does not cancel dangerous behavior; and sensitive requests outweigh apparent legitimacy. Extraction errors terminate analysis instead of silently producing a safe result.

## What makes it agentic

Guardian observes an input, builds structured evidence, reasons through deterministic state, proposes a bounded action, passes it through a separate authority policy, and emits observable events. Agency is constrained by architecture rather than delegated wholesale to the model.

## Challenges

The hardest work was separating language understanding from authority, preserving useful behavior across benign and adversarial phrasing, making fast backend events legible without fabricating telemetry, and keeping the protected-user UI calm while retaining a technical evidence surface.

## Learnings

Correct details do not prove caller identity. Direction matters: asking a user to disclose a code differs from warning them not to disclose one. Test counts measure software regression coverage, not model accuracy. A visible authority boundary makes agent behavior easier to explain and audit.

## Limitations

Guardian does not authenticate callers, infer reliable speaker identity, intercept telephone calls, or provide production persistence. Browser audio is a controlled demo path. Provider-backed input is processed in the cloud. The primary Guardian flow is single-turn; experimental V2 session state is in memory.

## Future work

Future work includes independent identity assurance, consent and retention controls, production-grade persistence, broader measured extraction evaluation, representative-user testing, and carefully governed carrier or device integration.

## Links

- Repository: https://github.com/evilgreen94/Guardian_call
- Live project: https://guardian-stable-601044791798.europe-west1.run.app/guardian/
- Technical visualizer: https://guardian-stable-601044791798.europe-west1.run.app/visualizer/
