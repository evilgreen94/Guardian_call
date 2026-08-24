# Guardian Call Development Log

## Evidence and status

This record follows the first-parent history of `main`. Dates, commits, and tags
come from Git. Capability claims come from source and tests at checkpoint
`guardian-m1.2a`.

Status terms have fixed meanings: **IMPLEMENTED**, **TESTED**, **EXPERIMENTAL**,
and **PLANNED**. The 105-test count is software regression coverage, not Gemini
or fraud-detection accuracy.

## M0.1 - Deterministic core

**Commit:** `e2a4faf` - `feat: implement Guardian Call M0 deterministic core`
**Date:** 2026-08-18
**Status:** IMPLEMENTED / TESTED

### OBJECTIVE

Create the smallest explainable protection pipeline around structured signals.

### HYPOTHESIS

Separating deterministic risk and policy authorization would make decisions
reviewable and prevent an LLM from directly performing consequential actions.

### IMPLEMENTATION

The repository introduced `ScamSignals`, `RiskEngine`, `CanaryPolicy`, action
types, domain events, and `GuardianPipeline.process_signals()`.

### EVALUATION

Unit tests exercised canonical OTP theft, benign input, risk reasons, Canary's
authorization table, privacy denial for transcript sharing, and enforcement
against bypassing Canary.

### FINDINGS

The architecture could produce a critical, explainable OTP assessment and an
authorized warning while keeping extraction outside deterministic policy.

### LIMITATIONS

Input was already-structured M0 signals. There was no live language extraction,
HTTP API, SSE visualizer, session memory, or audio.

### DECISION

Keep a modular monolith and preserve separate extraction, risk, policy, and
action responsibilities.

### NEXT STEP

Add a real structured language-extraction boundary.

## M0.2 - Gemini signal extraction

**Commit:** `e7b4ce1` - `feat: complete M0 Gemini signal extraction`
**Date:** 2026-08-18
**Status:** IMPLEMENTED / TESTED

### OBJECTIVE

Accept raw text and extract the existing M0 schema with Gemini.

### HYPOTHESIS

An LLM is useful for language understanding when constrained to factual
structured extraction and denied authority over risk or intervention.

### IMPLEMENTATION

`GeminiSignalExtractor` uses a JSON schema and a system instruction that
explicitly forbids risk scoring, scam probabilities, advice, and safety
decisions. `process_text()` emits input and extraction events, then delegates
successful signals to the deterministic pipeline.

### EVALUATION

Tests use controlled provider responses and cover valid extraction, legitimate
OTP flow, malformed JSON, empty output, missing API key, network error, and the
canonical end-to-end warning lifecycle.

### FINDINGS

The system gained an end-to-end text path while preserving deterministic risk
and Canary authority.

### LIMITATIONS

Production text is sent to Gemini. The path is not fully local/private, and M0
remains single-turn with a narrow schema.

### DECISION

Treat extraction failure as an explicit terminal event; do not fabricate empty
signals or continue into risk and policy.

### NEXT STEP

Expose the pipeline and its real events to a browser-based operator view.

## M0.3 - FastAPI, SSE, and initial visualizer

**Commit:** `86fcaa4` - `feat: add FastAPI SSE visualizer for Day 1 MVP`
**Date:** 2026-08-23
**Status:** IMPLEMENTED / TESTED

### OBJECTIVE

Make the canonical M0 path executable and observable from a browser.

### HYPOTHESIS

Judges and engineers could understand the agentic boundary more clearly by
seeing real domain events instead of a prerecorded animation.

### IMPLEMENTATION

FastAPI added health, scenario, text-analysis, and SSE endpoints. The browser
visualizer submitted synthetic text and consumed backend events.

### EVALUATION

Endpoint tests cover critical OTP analysis, legitimate denial, extraction
failure, scenario listing, health, and SSE generation.

### FINDINGS

REST and SSE could expose the same domain lifecycle used by tests. Backend
events became the source of truth for operator visualization.

### LIMITATIONS

The interface was an early technical view. Historical planning documents added
in this commit described CallSession, audio, and Trusted Circle aspirations;
those plans were not implementations.

### DECISION

Keep UI motion traceable to real REST/SSE/domain state.

### NEXT STEP

Turn the visualizer into a coherent Canary operator instrument.

## M0.4 - Canary workstation visual identity

**Commit:** `7bca552` - `feat: redesign Canary operator workstation`
**Date:** 2026-08-23
**Tag:** `canary-workstation-v1`
**Status:** IMPLEMENTED

### OBJECTIVE

Present Guardian Call as one specialized industrial workstation instead of a
generic web dashboard.

### HYPOTHESIS

A dense, legible instrument could communicate extraction, risk, authority, and
intervention as one system without inventing telemetry.

### IMPLEMENTATION

The frontend was restructured around conversation, protection sequence, signal
register, Canary authority, event output, and a real-event warning interrupt.

### EVALUATION

The design was reviewed iteratively against desktop composition, CRT/industrial
identity, event mapping, and the requirement that `USER_WARNING` remain a real
event.

### FINDINGS

Visual naming alone was insufficient; the application needed fixed workstation
geometry and a semantic Canary boundary.

### LIMITATIONS

Interaction timing and the distinction between authorization and executed
action still needed refinement.

### DECISION

Preserve the workstation identity while refining observable execution rather
than adding dashboard modules.

### NEXT STEP

Finalize event progression, boundary crossing, and interrupt behavior.

## M0.5 - Final workstation interaction flow

**Commit:** `a5478bd` - `feat: finalize Canary workstation interaction and visual flow`
**Date:** 2026-08-23
**Tag:** `canary-workstation-v2`
**Status:** IMPLEMENTED / TESTED

### OBJECTIVE

Make fast real execution perceptible while preserving canonical event order and
separating Canary authorization from action execution.

### HYPOTHESIS

Frontend presentation persistence could improve legibility without slowing the
API, fabricating events, or changing timestamps.

### IMPLEMENTATION

One persistent point moves along the live rail. Real SSE events enter a 450 ms
visual queue. `CANARY_EVALUATION` reaches the boundary, `ACTION_ALLOWED` crosses
it, `ACTION_DENIED` stops there, and only `USER_WARNING` reaches action and opens
the interrupt. `[ ACK ]` is local UI state.

### EVALUATION

The critical allow/warning path and deny path were checked against real event
semantics. The domain-event TTY excludes transient `RX` and `PROCESSING` UI
states.

### FINDINGS

Backend speed and human-readable visualization can coexist when presentation
history is explicitly separate from domain history.

### LIMITATIONS

The workstation visualizes M0 single-turn analysis only. It does not prove
telephony, session memory, or production deployment.

### DECISION

Freeze the visual direction and use the workstation as the current demo surface.

### NEXT STEP

Challenge the semantic and risk model with broader modern scam behavior.

## Paused M2 session experiment

**Commit:** `ccaa036` on `wip/m2-paused-session`
**Status:** EXPERIMENTAL

### OBJECTIVE

Explore multi-turn evidence retention and session-oriented API behavior.

### HYPOTHESIS

Accumulated evidence might represent gradual social engineering better than
independent M0 turns.

### IMPLEMENTATION

Experimental work was preserved on a dedicated branch outside `main`.

### EVALUATION

The work was deliberately isolated before it could become the new baseline.
Its tests and implementation are not part of the 105-test `main` checkpoint.

### FINDINGS

Session semantics depend on a sound representation of identity, requested
actions, and cross-domain sensitive behavior. Extending M0 first risked
accumulating inadequate semantics.

### LIMITATIONS

The branch is not production, not merged, and not evidence of current Guardian
functionality.

### DECISION

Pause M2 and reassess the threat model before continuing session work.

### NEXT STEP

Build a diagnostic adversarial baseline without changing production M0.

## M1 - Adversarial threat-model baseline

**Commit:** `275d394` - `test: establish M1 adversarial threat-model baseline`
**Date:** 2026-08-24
**Tag:** `m1-adversarial-baseline-v1`
**Status:** IMPLEMENTED / TESTED diagnostic infrastructure

### OBJECTIVE

Measure what M0 can represent and reason about across modern cross-domain scam
behavior and nearby legitimate language.

### HYPOTHESIS

Contrastive, adversarial cases would expose schema gaps and false-positive
calibration problems that a few canonical demos could not reveal.

### IMPLEMENTATION

The corpus expanded to 57 synthetic Spanish/English scenarios with scam,
legitimate-control, and ambiguous classifications; semantic-direction,
credibility, family, and constitutional metadata; and an offline oracle path
through the unchanged M0 RiskEngine and CanaryPolicy.

### EVALUATION

```text
PASS 24 | RISK MISMATCH 10 | CANARY MISMATCH 0
MODEL GAP 22 | AMBIGUOUS 1
```

### FINDINGS

M0 represented OTP, password, transfer, and remote-access behavior best. It
lacked many card, account-control, payment, screen, and wallet concepts. Nine
risk mismatches were benign contextual over-classification; one safe-account
case was under-classified relative to expected critical risk.

### LIMITATIONS

Oracle signals bypass Gemini and evaluate deterministic M0 behavior only.
Expected outcomes are diagnostic assertions, not future policy rules.

### DECISION

Freeze the empirical baseline and design a parallel semantic model before any
production policy change.

### NEXT STEP

Represent all 57 cases compositionally without scam-specific top-level fields.

## M1.1 - ScamSignalsV2 schema experiment

**Commit:** `8537a43` - `feat: add experimental ScamSignals v2 semantic model`
**Date:** 2026-08-24
**Tag:** `m1-signals-v2-experiment`
**Status:** EXPERIMENTAL / TESTED

### OBJECTIVE

Create a domain-agnostic semantic representation for all observed adversarial
concepts while preserving M0 unchanged.

### HYPOTHESIS

`direction + action + asset + destination` could distinguish dangerous requests
from warnings, self-service actions, history, and discussion across domains.

### IMPLEMENTATION

Immutable V2 enums and dataclasses model identity pretext, knowledge, contexts,
interaction acts, protected assets, semantic direction, actor, destination,
manipulation, and external identity assurance. All 57 cases were manually
remapped. Parsers reject unknown fields, raw sensitive values, and invalid
asset category/subtype combinations.

### EVALUATION

Tests prove 57/57 representability, vocabulary evidence, deterministic
serialization, explicit ambiguity, and isolation from production M0.

### FINDINGS

The corpus can be represented without bank-specific top-level scam categories.
Identity knowledge remains context, while dangerous behavior remains explicit.

### LIMITATIONS

There is no Gemini V2 extractor, RiskEngineV2, Canary integration, API path, or
frontend path.

### DECISION

Keep V2 under `guardian.experimental` and do not export it through production.

### NEXT STEP

Build provider-independent extraction comparison before live extraction.

## M1.2A - Offline semantic extraction evaluator

**Commit:** `f058fa6` - `feat: complete M1.2A semantic extraction evaluation`
**Date:** 2026-08-24
**Tag:** `guardian-m1.2a`
**Status:** EXPERIMENTAL / TESTED

### OBJECTIVE

Compare expected and observed V2 semantics deterministically without Gemini,
network access, risk calculation, or Canary.

### HYPOTHESIS

A frozen pure comparator could validate extraction semantics independently and
later accept observed output from any provenance-aware provider adapter.

### IMPLEMENTATION

M1.2A compares set fields and interaction acts, reports structured differences,
classifies extraction-error impact separately from risk, aggregates metrics,
preserves ambiguity, and supports deterministic JSON/text output.

### EVALUATION

```text
SYNTHETIC OFFLINE REPLAY // NOT GEMINI ACCURACY
16 fixtures | 15 strict | 1 ambiguous
15 differences | 9 critical-impact | 2 high-impact
```

The checkpoint contains 105 passing software regression tests.

### FINDINGS

The evaluator detects missing, spurious, reordered, and partially matched acts;
direction and destination flips; set errors; and explicit ambiguity. Exact-first
greedy matching is deterministic across tested ordering and tie cases.

### LIMITATIONS

Replay fixtures deliberately inject errors and say nothing about Gemini
performance. Greedy matching is stable but not globally optimal.

### DECISION

Freeze the comparator before adding a live provider path.

### NEXT STEP

**PLANNED:** M1.2B may produce observed V2 signals with Gemini and feed the
unchanged comparator. No live V2 benchmark results currently exist.
