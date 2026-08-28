# M1.2B Live V2 Extraction Benchmark

## Status

**EXPERIMENTAL:** the Gemini V2 adapter, formal benchmark runner, provenance
manifest, and offline tests exist under `guardian.experimental`.

**PLANNED:** no live Gemini V2 result has been executed or recorded yet. This
document defines the frozen baseline protocol; it does not report accuracy.

## Constitutional principles

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These principles constrain architecture and reporting. They do not change the
semantic comparator or create fraud rules.

## Experimental boundary

```text
synthetic corpus text
        -> frozen experimental Gemini V2 extractor
        -> observed ScamSignalsV2
        -> existing M1.2A compare_signals()
        <- expected ScamSignalsV2 mapping
```

M1.2B measures semantic extraction. It does not run RiskEngine, Canary, the
production pipeline, the server, or the frontend. Identity assurance is absent
from the provider schema. The runner attaches external `UNVERIFIED` context
with an explicit source label; it is not model output or an extraction metric.

## Frozen prompt representation

Prompt revision: `m2.5-family-manipulation-prompt-v1`

Prompt contract SHA-256:

```text
9b43516799d62627b3a6198262ac120d16bc139cb0d2f721bc4abd19e7b6c83f
```

The provider receives exactly two Python strings:

1. `system_instruction`: the `SYSTEM_INSTRUCTION` constant.
2. `contents`: `USER_PROMPT_PREFIX + conversation_text + USER_PROMPT_SUFFIX`.

The conversation string is not stripped, Unicode-normalized, case-folded, or
line-ending-normalized by the extractor. Runtime Python strings contain the LF
characters written in the constants. Those exact strings are passed to the
SDK.

The stable prompt-contract fingerprint replaces the conversation with the
literal marker `{conversation_text_exact_bytes_as_utf8}` and constructs:

```json
{
  "contents": "<exact prefix>{conversation_text_exact_bytes_as_utf8}<exact suffix>",
  "system_instruction": "<exact frozen system instruction>"
}
```

That object is serialized with the canonical JSON policy below and hashed as
SHA-256. Every actual request also records `request_prompt_sha256`, calculated
from the same object with the exact conversation string in place of the marker.
The transcript itself is not stored in the formal manifest.

## Frozen schema representation

Schema revision: `m1.2b-schema-v1`

Schema SHA-256:

```text
5dab085e5088fc7a5e8aed421a39cdf45d23ccf5c5935f7aecef676aba93254c
```

The hash input is the complete `SCAM_SIGNALS_V2_JSON_SCHEMA` object. Enum arrays
are generated in Python enum declaration order. The schema includes required
fields, enum values, descriptions, nullable asset representation, and
`additionalProperties` constraints. It excludes identity assurance.

## Canonical JSON bytes

Prompt frames, schema, and run fingerprints use one explicit serializer:

```text
json.dumps(
    value,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

Therefore keys are lexicographically ordered, insignificant whitespace is
absent, non-ASCII characters are encoded directly as UTF-8, and non-finite
numbers are rejected. No platform newline, locale, dictionary insertion order,
or pretty-printing affects the bytes.

## Structured output and parsing

The request uses `application/json`, the frozen JSON schema, and temperature
`0.0`. Structured output constrains response shape but does not establish
semantic correctness. The adapter parses JSON and then calls strict
`ScamSignalsV2.from_dict()`. Empty, malformed, extra-field, unknown-enum, and
invalid asset/category outputs become `PARSE_SCHEMA_FAILURE`; they never become
empty neutral signals.

Raw response content is discarded. A successful response records its SHA-256,
byte length, structured signals, response ID, and returned model version when
the SDK exposes them. A parse failure records only fixed diagnostics, hash, and
byte length.

## Formal result states

- `EXACT_MATCH`
- `SEMANTIC_DIFFERENCES`
- `AMBIGUOUS_REFERENCE`
- `PROVIDER_API_FAILURE`
- `PARSE_SCHEMA_FAILURE`
- `QUOTA_EXHAUSTED`
- `NOT_ATTEMPTED`

Provider and schema failures are excluded from semantic metrics. A 429 or
`RESOURCE_EXHAUSTED` stops further requests and leaves the remaining selection
explicitly unattempted.

## Retry and resume policy

The frozen baseline permits exactly one provider attempt per scenario and sets
no SDK retry options. There is no synthetic fallback. Resume validates the run
fingerprint and skips every result already recorded, including failures. It
continues only unattempted cases. Re-running a failed case requires a separate
run, preserving the first attempt instead of selecting a better result.

An optional operator-selected minimum request interval defaults to zero and is
recorded. It spaces requests but does not retry or alter model output.

## Provenance and privacy

Formal manifests under `logs/m1.2b-formal/` contain scenario IDs, expected and
observed structured signals, comparisons, statuses, actual timestamps, Git
commit, SDK version, requested/returned model identifiers, response IDs,
prompt/schema revisions and hashes, corpus hash, mapping source, selection,
and run fingerprint.

They do not contain transcripts, raw Gemini responses, API keys, authorization
headers, environment secrets, raw sensitive values, fabricated token counts,
cost, latency, seed, or provider metadata. The current corpus text is sent to
Gemini during a live run; processing is not local or fully private.

## Reporting

Successful extractions reuse the M1.2A comparator and metrics unchanged.
Execution failure counts are reported separately. Family and constitutional
slices overlap and are diagnostic. Results must be called semantic extraction
results, never fraud-detection accuracy.

The prompt and schema must not be tuned after observing baseline failures.
Future prompt changes require a new revision, hash, and separately named run.
