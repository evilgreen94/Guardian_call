# ADR-002 — Fail-safe risk handling when Gemini signal extraction fails

## Status
Accepted

## Context

ADR-001 added `extract_signals(text) -> ScamSignals`, which raises `SignalExtractionError` on API failure or unparseable model output. M0 still needs a single text-in entrypoint (`Text → Gemini → Signal → Risk Engine → Canary → USER_WARNING`) that calls it and continues the pipeline.

Two situations are not covered by the existing deterministic `RiskEngine`/`CanaryPolicy`, which only ever operate on a real `ScamSignals` object:

- no text yet (a call that has just started, nothing said);
- Gemini/ADK genuinely fails (network/API error, or the model returns invalid/unparseable output).

Per AGENTS.md rule 4 ("never silently change risk semantics"), this was raised with the team and decided explicitly rather than assumed.

## Decision

- **Empty/whitespace-only input** is treated as "no signals yet": the existing deterministic pipeline runs with an empty `ScamSignals()`, which already yields `NORMAL` risk and no warning. No Gemini call, no special-casing.
- **A genuine `SignalExtractionError`** is treated as fail-safe: bypass `RiskEngine.evaluate` and construct a synthetic assessment —
  `RiskAssessment(level=HIGH, reasons=["Unable to analyze conversation content; defaulting to cautious posture"], contributing_signals=["extraction_failed"])` —
  with `PipelineResult.signals = ScamSignals()` (no reliable signals were available). A new event, `SIGNAL_EXTRACTION_FAILED`, is emitted (a short, generic reason only — never the raw exception text or transcript, per AGENTS.md's privacy rule) before `RISK_UPDATED`. From there, the pipeline continues exactly as normal: Canary evaluates `warn_user` against this assessment, and `HIGH` already authorizes it under the existing M0 policy — no Canary code changes needed.
- `pipeline.py` is refactored to extract the "act on a risk assessment" tail (Canary evaluation → action execution, currently the second half of `process_signals`) into a private helper, reused by both `process_signals` and the new fail-safe branch of `process_text`, instead of duplicating that logic.

New public entrypoint: `GuardianPipeline.process_text(text: str, event_sink: Optional[EventSink] = None) -> PipelineResult`.

## Why

- Keeps `RiskEngine` pure and deterministic (AGENTS.md: risk must be explainable from contributing signals) — the fail-safe path is a distinctly labeled reason (`extraction_failed`), never presented as a real scam signal.
- Fails toward user safety (a warning) rather than fails silent, matching the earlier team decision that extraction failure should elevate risk, not suppress it.
- Separates "nothing said yet" from "we tried and failed," so a call's opening silence doesn't trigger a false HIGH-risk warning.

## Alternatives considered

- **Fail-loud** (raise, no automatic warning) — considered and rejected earlier in favor of fail-safe, to protect the user even when analysis is impossible.
- **Treating empty text the same as extraction failure** — rejected: would fire a HIGH-risk warning at the very start of every call, before anything was said.

## Consequences

- New event type `SIGNAL_EXTRACTION_FAILED` in `events.py`.
- New `GuardianPipeline.process_text()` entrypoint; `process_signals()` keeps its current public behavior, with its Canary/action tail extracted into a shared private helper.
- Any event-sink consumer (the future visualizer) needs to handle this new event type — it's the first "the system failed, not the caller" event in the taxonomy.

## Revisit when

- If `RiskEngine` ever gains a level for "insufficient evidence" distinct from `NORMAL`/`HIGH`, this fail-safe mapping should be reconsidered.
