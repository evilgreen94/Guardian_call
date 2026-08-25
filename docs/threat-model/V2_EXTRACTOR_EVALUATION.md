# V2 Extractor Evaluation

## M1.2A status

```text
M1.2A OFFLINE EXTRACTOR EVALUATION
NO GEMINI
NO NETWORK
SYNTHETIC OBSERVED SIGNALS
```

M1.2A evaluates semantic extraction infrastructure. It compares an expected
`ScamSignalsV2` with an observed `ScamSignalsV2` without knowing how the
observed value was produced. The observed values in this milestone are
deterministic replay fixtures created to test the evaluator itself. They are
not Gemini output, model output, simulated provider output, or production
events.

The 57 manually curated V2 mappings are human-authored experimental ground
truth. They are neither a database of fraud rules nor an implicit specification
for RiskEngine v2. This evaluator reports representation differences; it does
not decide whether a conversation is fraudulent and does not calculate risk.

## Constitutional invariants

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These principles are reporting-group metadata and project invariants. Corpus
membership in C1, C2, or C3 never alters comparison or extraction-impact
results.

## Expected and observed

The pure comparator accepts a scenario identifier, expected signals, observed
signals, optional ambiguity metadata, and optional external identity-assurance
contexts. Normal extraction dimensions are:

- claimed entity types;
- knowledge categories;
- contexts;
- interaction acts;
- manipulation signals.

Identity assurance is external to conversational extraction. It is excluded
unless both benchmark inputs explicitly choose to validate it through the
separate assurance comparison.

Set-like dimensions use order-independent TP, FP, and FN comparisons. Precision,
recall, and F1 retain their denominators; undefined values serialize as `null`.

## Interaction-act matching

An act is canonically represented by:

```text
action / asset category / asset subtype / semantic direction / actor / destination
```

Matching proceeds as follows:

1. Sort expected and observed acts by their canonical six-field keys.
2. Consume exact multiset matches first.
3. Calculate Hamming distance for every remaining candidate pair using only
   field equality.
4. Sort candidates by distance, expected canonical key, then observed canonical
   key.
5. Greedily accept the first candidate whose expected and observed acts are
   both still unmatched.
6. Emit remaining expected acts as `MISSING_ACT` and remaining observed acts as
   `SPURIOUS_ACT`.

This is deterministic and independent of tuple order. Exact acts cannot be
captured by partial pairings, and equal-distance ties have a stable canonical
result.

### Matcher limitation

Greedy minimum-distance pairing does not guarantee the globally minimal total
distance across all remaining pairs. A locally closest pair can make a later
pair less intuitive. This is accepted for M1.2A because the current acts are
small, compositional tuples and the adversarial fixtures verify the relevant
equal and near-equal cases.

The public comparator contract exposes expected acts, observed acts, semantic
field differences, and unmatched acts. It does not expose candidate indexes,
Hamming scores, or the greedy algorithm. A future matcher can therefore replace
the implementation without changing result semantics or machine-readable
types. Replacement is warranted only if empirical live-extractor cases show
that greedy pairing obscures diagnostics.

## Difference taxonomy

Set differences:

- `IDENTITY_CLAIM_MISS`, `IDENTITY_CLAIM_SPURIOUS`
- `KNOWLEDGE_CATEGORY_MISS`, `KNOWLEDGE_CATEGORY_SPURIOUS`
- `CONTEXT_MISS`, `CONTEXT_SPURIOUS`
- `MANIPULATION_MISS`, `MANIPULATION_SPURIOUS`

Act differences:

- `MISSING_ACT`, `SPURIOUS_ACT`
- `ACTION_MISMATCH`
- `ASSET_CATEGORY_MISMATCH`, `ASSET_SUBTYPE_MISMATCH`
- `SEMANTIC_DIRECTION_MISMATCH`
- `ACTOR_MISMATCH`, `DESTINATION_MISMATCH`
- `MISSING_VALUE`, `SPURIOUS_VALUE`, `VALUE_MISMATCH`

`EXACT_MATCH` is an evaluation or act-comparison status, not a fabricated
difference.

## Extraction-error impact

Extraction impact estimates how consequential a representation mistake could
be for later reasoning. It is not risk, fraud severity, a probability, or
Canary authorization.

- `CRITICAL`: omission or invention of an active asset-bearing request;
  active-request versus warning/reference/control direction flip; or external
  versus control-preserving destination flip for an asset-bearing act.
- `HIGH`: action, asset, actor, other direction, or unresolved destination
  mismatch.
- `MEDIUM`: non-active missing/spurious acts and manipulation differences.
- `LOW`: identity-claim, knowledge, and context differences.
- `INFO`: separate identity-assurance metadata differences.

Active request directions are `DIRECT_REQUEST`, `INDIRECT_REQUEST`, and
`PARTIAL_REQUEST`. Warning/reference/control directions are `WARNING`,
`NEGATION`, `SELF_SERVICE`, `DISCUSSION`, `HYPOTHETICAL`, `HISTORICAL`,
`THIRD_PARTY`, and `QUESTION`. Destination reversals distinguish caller,
third-party, or external-account control from official self-service or
user-controlled boundaries. `UNKNOWN` is reported as a mismatch but is not
silently assigned to either side.

## Metrics

Reports retain multiple diagnostic views:

- scenarios evaluated, strict scenarios, ambiguous references, exact scenarios,
  mismatched scenarios, and difference counts by impact;
- TP, FP, FN, precision, recall, F1, and denominators for set dimensions;
- exact, partial, missing, and spurious acts;
- exact/mismatch counts for actions, assets, directions, actors, and
  destinations;
- semantic-direction flip breakdowns;
- C1/C2/C3 group counts, strict exact/mismatch counts, ambiguity, and critical
  extraction differences.

Constitutional groups may overlap. Their metrics are diagnostic slices and do
not modify the underlying evaluations.

## Ambiguity

An ambiguous ground-truth reference remains structurally comparable and visible
as `AMBIGUOUS_REFERENCE`. It carries
`excluded_from_strict_accuracy=true`. Its differences remain available, but it
cannot increase either the strict exact or strict mismatch numerator.

## Replay fixtures and CLI

Sixteen named replay fixtures cover exact output, missing and spurious acts,
direction reversals, asset and destination mismatches, set differences, mixed
intent, reordered acts, similar-act pairing, and explicit ambiguity.

```text
python scripts/v2_extractor_benchmark.py --replay all
python scripts/v2_extractor_benchmark.py --replay semantic-direction
python scripts/v2_extractor_benchmark.py --case bank_otp_sophisticated --replay exact
python scripts/v2_extractor_benchmark.py --list-fixtures
python scripts/v2_extractor_benchmark.py --replay all --format json
```

No result is persisted automatically. Text output shows scenario identifiers
and structured categories by default. Existing synthetic scenario text appears
only with `--show-text`.

## Privacy

Evaluator inputs and outputs contain controlled semantic categories, never raw
OTP values, passwords, PINs, card numbers, security codes, recovery codes, seed
phrases, private keys, addresses, government IDs, or personal data. The CLI
does not create new transcript storage.

## Future M1.2B boundary

A future provider adapter may produce:

```text
scenario_id + expected ScamSignalsV2 + observed ScamSignalsV2
```

It can call the same pure comparator without changing matching, differences,
impact, metrics, or report types. M1.2A deliberately defines no provider
protocol because one input tuple is already a sufficient boundary. M1.2B must
separately address prompting, parsing, provider errors, quotas, and provenance;
none are simulated here.

M1.2A does not integrate V2 with `GuardianPipeline`, RiskEngine, Canary,
FastAPI, frontend code, or M2 session work.
