# Manual Live Session Evidence

## Evidence class

Every persisted record is labelled exactly:

```text
MANUAL EXPLORATORY SESSION // NOT FORMAL BENCHMARK EVIDENCE
```

Manual exploration is **EXPERIMENTAL** qualitative evidence. It is never merged
into M1.2B benchmark denominators or described as model accuracy.

## Constitutional principles

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

## Separation from formal evaluation

The manual tool shares the frozen experimental Gemini adapter so its prompt and
schema are identifiable. It does not import `compare_signals()`, benchmark
summaries, expected corpus mappings, RiskEngine, or Canary. Operator verdicts
are annotations, not computed results.

The existing M0 `conversation_simulator.py` remains unchanged. PowerShell
`Tee-Object` captures may remain local historical artifacts, but repository-
native manual sessions use structured append-only records.

## Opt-in persistence

The default manual session persists nothing. Recording requires both
`--record-session` and `--confirm-synthetic-only`. Optional TXT output requires
the additional `--text-log` flag.

```text
logs/manual-live/<session-id>.jsonl
logs/manual-live/<session-id>.txt
```

JSONL record types are `session_start`, `turn`, `operator_verdict`, and
`session_end`. The TXT file is a human-readable rendering of the same manual
session. Both carry the mandatory non-benchmark label.

## Recorded provenance

Where available, records include actual UTC timestamps, session and turn IDs,
Git commit, provider, requested model, returned model version, response ID, SDK
version, prompt/schema revision and hash, request/response hashes, simulator
mode, structured observed signals, normalized failures, and operator verdicts.

Allowed verdicts are `pass`, `false_positive`, `false_negative`, and
`ambiguous`. They express the operator's judgment and have no automatic
benchmark meaning.

## Sensitive-data policy

Only synthetic input is allowed. The recorder never reads API keys or headers
into evidence and never persists raw Gemini responses or exception dumps.
Before writing a turn it rejects obvious OTP-like digits, card-number-like
sequences, explicit secret assignments, authorization headers, API-key forms,
and private-key markers.

Automated pattern matching cannot prove that arbitrary text is synthetic or
detect every possible secret. The explicit operator acknowledgement is
therefore mandatory, and the filter is defense in depth rather than a privacy
guarantee. A rejected turn may be inspected interactively but is not written.

## Repository policy

The repository already ignores `logs/`, covering both formal and manual local
artifacts. JSONL sessions, TXT transcripts, terminal captures, and operator-
entered text must not be committed.

After explicit review, a separate approved documentation change may preserve a
sanitized summary under `docs/hackathon/evidence/`. Appropriate committed
evidence is limited to IDs, aggregate counts, structured difference categories,
model/prompt/schema/corpus identifiers, hashes, and redacted lessons. There is
no automatic export into documentation.

Manual observations must not tune the frozen M1.2B baseline prompt before the
formal run. Failures remain evidence; later prompt experiments require a new
revision and separate results.
