# ADR-001 — Use Google ADK for the Gemini signal-extraction agent

## Status
Accepted

## Context

M0 requires: `Text → Gemini → Signal → Risk Engine → Canary → USER_WARNING`. The Gemini step (`agent.py`) was not yet implemented; `ScamSignals` were only ever built by hand in tests.

The hackathon rules require every project to use:
- Gemini 3.5 or newer, via the Gemini API or Vertex AI;
- at least one Google Agent Framework (Google ADK, GenAI SDK, Antigravity SDK, or GenKit);
- at least one Google Cloud infrastructure service (deferred to the deployment phase, 27–28 Aug).

An initial design using the raw `google-genai` SDK (a single structured-output call) was drafted and would have satisfied the framework requirement as "GenAI SDK." Before implementation, the team confirmed the intent to build the signal extractor as an actual Google ADK agent instead, to more directly demonstrate agent architecture for judging in an "agentics" hackathon.

## Decision

Implement the signal-extraction step as a single Google ADK `LlmAgent`, model `gemini-3.5-flash`, with `output_schema` set to a Pydantic model that mirrors `ScamSignals` (same 10 fields, same types/defaults) from `backend/guardian/models.py`.

Public interface, unchanged from the original design:

```python
def extract_signals(text: str, runner: Optional[Runner] = None) -> ScamSignals
```

This keeps `agent.py` behind the same boundary already used by `pipeline.py`: Gemini/ADK only understands text and emits structured signals. It never touches `risk.py` or `canary.py`, and it never authorizes actions directly (AGENTS.md: "Gemini understands; Canary authorizes").

On API failure or invalid/unparseable model output, `extract_signals` raises a new `SignalExtractionError` rather than silently returning empty signals. Handling that failure (a fail-safe HIGH-risk fallback so the user is still warned when analysis is impossible) is orchestration logic that belongs in `pipeline.py`, not in `agent.py` — tracked as a separate, smaller implementation task.

## Why

- Satisfies the hackathon's Google Agent Framework requirement in its most demonstrable form — an actual agent, not a single API call.
- ADK's `output_schema` gives the same structured-output guarantee the simpler design already relied on, so there is no loss of reliability.
- Preserves the existing architectural boundary (AGENTS.md §1): Gemini extracts meaning; Risk Engine computes explainable risk; Canary authorizes. Only the internals of the extraction step change.

## Alternatives considered

- **Raw `google-genai` SDK, single call.** Simpler, fewer moving parts, already satisfies the minimum framework requirement ("GenAI SDK" is explicitly accepted). Rejected in favor of a clearer, more literal agent for a hackathon centered on agentic architecture.
- **Multi-agent ADK pipeline** (separate agents for extraction, risk reasoning, notification). Rejected: AGENTS.md explicitly forbids "multi-agent architecture for its own sake," and Risk Engine/Canary must remain deterministic and explainable, not LLM-driven.

## Consequences

- New dependency: `google-adk` (pulls in `google-genai` transitively). Needs a `requirements.txt` (did not previously exist).
- New env vars in `.env` (already gitignored): `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.
- Tests for `agent.py` must mock ADK's `Runner`/session objects, not a plain HTTP/client mock.
- Per `docs/ANTIGRAVITY_WORKFLOW.md`, implementation is delegated to Antigravity via a scoped prompt; Claude's role is authoring this ADR and reviewing the resulting code against `AGENTS.md` (architectural boundaries, unnecessary complexity, privacy, opaque risk logic, test coverage, fake observability, scope creep).

## Revisit when

- Moving to Vertex AI for the Google Cloud deployment requirement (27–28 Aug) — will likely need `GOOGLE_GENAI_USE_VERTEXAI=TRUE` + `GOOGLE_CLOUD_PROJECT` instead of a direct API key.
- If a second LLM-driven step is ever proposed (e.g., risk-reasoning assistance) — needs its own ADR, since AGENTS.md currently requires deterministic, explainable risk logic.
