# Guardian Call Evaluation

## What is being measured

Guardian Call currently has three distinct evaluation layers. Their numbers are
not interchangeable.

1. **TESTED software behavior:** 105 automated regression tests at
   `guardian-m1.2a`. This is not model accuracy.
2. **TESTED M0 deterministic baseline:** human-curated M0 signals run through
   the unchanged RiskEngine and CanaryPolicy. This is not Gemini extraction.
3. **EXPERIMENTAL M1.2A replay:** deliberately altered V2 observations compared
   with expected V2 mappings. This validates the comparator and is not Gemini
   accuracy.

Detailed evidence is maintained in
[`docs/threat-model/`](../threat-model/). This document summarizes it for
hackathon review.

## Corpus

**IMPLEMENTED / TESTED diagnostic asset**

The corpus contains 57 entirely synthetic scenarios:

| Classification | Cases |
| --- | ---: |
| Scam | 37 |
| Legitimate control | 19 |
| Ambiguous | 1 |
| **Total** | **57** |

| Language | Cases |
| --- | ---: |
| Spanish | 35 |
| English | 22 |

It covers active requests, indirect and partial requests, warnings, negation,
questions, hypotheticals, historical reports, third-party reports,
self-service, ordinary discussion, and mixed intent. Apparent-credibility cases
pair synthetic personal knowledge with both safe and dangerous branches.

### Overlapping families

Family memberships overlap and therefore do not sum to 57.

| Family | Cases |
| --- | ---: |
| OTP / authentication | 14 |
| Payment card / CVV | 11 |
| Money movement | 11 |
| Remote device control | 9 |
| Account takeover / recovery | 13 |
| Crypto / wallet assets | 5 |
| Apparent credibility | 15 |
| Manipulation / social engineering | 12 |
| Cross-domain masking | 21 |

### Constitutional coverage

Constitutional memberships also overlap and are reporting metadata only.

| Principle | Cases |
| --- | ---: |
| C1 - Knowledge is not authentication | 15 |
| C2 - Trust does not cancel dangerous behavior | 26 |
| C3 - Sensitive requests outweigh apparent legitimacy | 37 |

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

Membership does not alter extraction, risk, Canary, comparison, or impact
results.

## M0 adversarial baseline

**TESTED OFFLINE ORACLE BASELINE / UNCHANGED M0 ENGINE**

Every predefined M0 `ScamSignals` object was independently processed through
the real `GuardianPipeline.process_signals()`, deterministic RiskEngine, and
CanaryPolicy. Gemini was not initialized. There was no API key or network
requirement and no session memory.

```text
CASES                   57
PASS                    24
RISK MISMATCH           10
CANARY MISMATCH          0
MODEL GAP               22
AMBIGUOUS                1
```

### Outcome definitions

**PASS** means representable M0 signals produced both the expected risk level
and expected Canary decision.

**RISK MISMATCH** means the required evidence was representable and reached the
unchanged deterministic RiskEngine, but its level differed from the manually
reviewed security expectation.

**CANARY MISMATCH** means risk matched the expectation but Canary authorization
did not. The baseline recorded zero such cases; this says Canary consistently
applied its current table, not that the whole system achieved perfect policy or
fraud detection.

**MODEL GAP** means M0 `ScamSignals` could not represent evidence necessary for
the expected outcome. The harness reports the gap before blaming RiskEngine or
Canary.

**AMBIGUOUS** means the case intentionally has no forced pass/fail expectation.
It remains visible instead of being silently assigned a confident label.

### Findings

M0 was strongest where its schema directly represented the requested
capability: OTP disclosure, password disclosure, transfers, and remote device
access.

The 22 model-gap outcomes cover concepts including card number/expiry/CVV,
payment-app approval, login approval, recovery codes, recovery-contact changes,
disabling 2FA, password-reset links, gift cards, cash withdrawal, screen
sharing, seed phrases, and private keys.

Of ten RiskEngine mismatches, nine were benign controls returned as
`SUSPICIOUS`, generally because an unverified identity claim or broad financial
context outweighed the absence or direction of a dangerous action. The
safe-account transfer case was expected `CRITICAL` but returned `HIGH`; Canary
still authorized a warning at that level.

No M0 code or expected signal was changed to improve these results.

## M1.1 representability

**EXPERIMENTAL / TESTED**

All 57 scenarios have exactly one human-curated `ScamSignalsV2` mapping. Tests
validate:

- complete ID coverage and deterministic round trips;
- representation of all M0 gap concepts;
- distinct acts for mixed intent;
- explicit ambiguity for `ambiguous_security_digits`;
- evidence-backed vocabulary;
- exhaustive asset category/subtype compatibility;
- rejection of raw sensitive-value fields;
- external identity assurance fixed to `UNVERIFIED` for current mappings;
- isolation from M0 production.

Representability does not prove that Gemini can extract V2 accurately and does
not specify future risk policy.

## M1.2A evaluator replay

```text
SYNTHETIC OFFLINE REPLAY // NOT GEMINI ACCURACY
```

**EXPERIMENTAL / TESTED**

Sixteen deterministic fixtures start from human-curated expected V2 mappings
and deliberately produce exact, missing, spurious, reordered, or semantically
altered observations. Their purpose is to prove that the comparator detects
known errors.

```text
Scenarios evaluated        16
Strict scenarios           15
Ambiguous references        1
Exact strict scenarios      2
Mismatched strict cases    13
Total differences          15
Critical differences        9
High differences            2
```

Interaction-act matching:

```text
Exact acts                 22
Partial matches             8
Missing acts                2
Spurious acts               1
```

Two exact strict scenarios are expected: the exact fixture and the reordered
acts fixture. Thirteen strict mismatches are also expected because those
fixtures intentionally inject semantic errors. The ambiguous reference is
structurally reported but excluded from strict accuracy.

Critical and high are extraction-error impact labels. They indicate how a
semantic mistake could distort later reasoning; they are not conversation risk
levels and not Canary decisions.

The comparator reports:

- TP, FP, FN, precision, recall, F1, and denominators for set dimensions;
- exact, partial, missing, and spurious acts;
- action, asset, direction, actor, and destination mismatches;
- direction-flip breakdowns;
- extraction-error impact;
- constitutional reporting groups;
- explicit ambiguity;
- deterministic text and JSON output.

The exact-first greedy matcher is deterministic across tested input order,
repetition, near-equal candidates, and canonical tie cases. It is not guaranteed
to find a globally optimal assignment; that limitation is documented and its
implementation can be replaced without changing result types.

## Software regression suite

At checkpoint `guardian-m1.2a`:

```text
105 tests passed
```

The suite covers M0 signals, extraction contracts and failures, deterministic
risk, Canary policy, action authority, domain events, pipeline lifecycles,
FastAPI/SSE behavior, M0 oracle evaluation, V2 schema validation, 57-case V2
mapping, comparator semantics, matching determinism, replay fixtures, privacy
constraints, and experimental isolation.

The suite uses mocks and deterministic fixtures where appropriate. The number
105 must never be presented as Gemini accuracy, scam-detection accuracy, recall,
precision, or production reliability.

## Future live V2 benchmark

**PLANNED / NOT YET IMPLEMENTED**

```text
conversation -> Gemini V2 extractor -> observed ScamSignalsV2
                                      -> frozen M1.2A comparator
expected human-curated V2 ground truth ->
```

No live V2 measurements exist.

Future results must record provider/model provenance, distinguish extraction
failure from semantic mismatch, preserve ambiguous references, report
denominators, and remain separate from future deterministic risk evaluation.

### M1.2B live benchmark results

**PLANNED / NO RESULTS**

This section is intentionally empty until an implemented provider path produces
reviewed evidence.
