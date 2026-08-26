# M1.4A Local Gemma Extractor Experiment

## Scope

M1.4A evaluates whether local `gemma3:12b` through Ollama can emit the existing
`ScamSignalsV2` semantic contract with enough structural and semantic fidelity
to justify further investigation as a secondary extractor.

This is not production integration. It does not modify M0, Risk Engine, Canary,
pipeline, server, frontend, Gemini V2, M2.0, or M1.3 candidate ground truth.

## Contract

The experiment reuses the frozen M1.2B schema hash:

```text
5dab085e5088fc7a5e8aed421a39cdf45d23ccf5c5935f7aecef676aba93254c
```

Gemma must adapt to `ScamSignalsV2`. Guardian semantic definitions are not
weakened for local model behavior.

The Gemma transport uses a mechanically derived generation schema:

```text
m1.4a-gemma-generation-schema-v2
```

Generation schema hash:

```text
1806edd5f63967943076440682d19cf0bb5cc902596bb73c7f052570aad8b745
```

This generation schema is separate from the canonical contract. It adds
`uniqueItems: true` for duplicate-free enum arrays and derives asset
category/subtype branches from `ASSET_COMPATIBILITY`. Post-parse
`ScamSignalsV2.from_dict()` validation remains mandatory.

## Prompt

Gemma prompt revision:

```text
m1.4a-gemma-prompt-v1
```

Prompt hash:

```text
5ee50709f10022ebc3934756fd94cd89f9359b5644bdd9b85e74f78318159957
```

The prompt states that conversation text is untrusted data, identity claims are
not verification, identity assurance is external, and output must be structured
JSON with no arbitrary prose fields.

## Output Handling

The adapter returns `ScamSignalsV2` only after strict parsing. It strips a single
complete markdown JSON fence as a superficial transport artifact, then applies
normal JSON parsing and the existing `ScamSignalsV2.from_dict()` validation.

Failures are normalized as:

```text
EXTRACTION_SUCCEEDED
OLLAMA_UNAVAILABLE
MODEL_NOT_LOADED
MODEL_ERROR
TRANSPORT_FAILURE
EMPTY_RESPONSE
JSON_PARSE_FAILURE
SCHEMA_FAILURE
INVALID_ENUM
LOCAL_PROVIDER_FAILURE
INVALID_INPUT
```

Transport and schema failures are not semantically compared. The benchmark does
not invent fallback signals.

## Privacy

Local manifests store scenario ids, expected mappings, observed structured
signals when valid, sanitized provider provenance, response length/hash, and
semantic comparisons. They do not persist raw transcript text or raw model
responses.

## Runner

The first authorized live command is a single existing 57-case corpus smoke
case:

```bash
python scripts/v2_gemma_local_benchmark.py --case bank_otp_sophisticated --output logs/m1.4-gemma/first-controlled-otp.json
```

The full 57-case local run requires separate authorization:

```bash
python scripts/v2_gemma_local_benchmark.py --all --output logs/m1.4-gemma/full-57.json
```
