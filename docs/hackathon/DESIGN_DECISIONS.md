# Guardian Call Design Decisions

## Status vocabulary

- **IMPLEMENTED**: active on production M0 `main`.
- **TESTED**: supported by automated regression or deterministic evaluation.
- **EXPERIMENTAL**: implemented in the isolated research layer.
- **PLANNED**: not implemented.

These concise records summarize decisions evidenced by code, tests, Git history,
and [`docs/threat-model/`](../threat-model/).

## DD-01 - Deterministic risk instead of LLM risk decisions

**CONTEXT:** Conversational understanding benefits from an LLM, but opaque risk
decisions would be difficult to explain and reproduce.
**DECISION:** Gemini extracts M0 signals; deterministic `RiskEngine` calculates
risk and explicit reasons.
**RATIONALE:** Identical structured evidence follows reviewable rules, and the
model cannot directly choose intervention severity.
**TRADE-OFF:** M0 can reason only about concepts its schema and rules represent.
**STATUS:** IMPLEMENTED / TESTED.

## DD-02 - Canary is the action-authorization boundary

**CONTEXT:** Detecting risk and performing an intervention are different
authorities.
**DECISION:** Consequential actions require a `CanaryPolicy` decision; the
current pipeline evaluates `warn_user`.
**RATIONALE:** Policy, privacy, and autonomy remain explicit and testable.
**TRADE-OFF:** A correct risk assessment cannot execute an action absent an
applicable Canary rule.
**STATUS:** IMPLEMENTED / TESTED.

## DD-03 - Extraction is separate from deterministic reasoning

**CONTEXT:** Language interpretation is probabilistic; risk and authorization
must remain reproducible.
**DECISION:** `GeminiSignalExtractor` returns structured facts and is instructed
not to score risk, determine fraud, advise, or authorize.
**RATIONALE:** Extraction errors can be measured separately from downstream
logic.
**TRADE-OFF:** Schema quality becomes a hard capability boundary.
**STATUS:** IMPLEMENTED / TESTED for M0; EXPERIMENTAL for V2 evaluation.

## DD-04 - Identity claims are context, not authentication

**CONTEXT:** A caller can claim to represent a bank, platform, authority, or
family member.
**DECISION:** A conversational claim records pretext but does not establish
identity.
**RATIONALE:** Self-asserted affiliation is not independent evidence.
**TRADE-OFF:** Guardian currently cannot confirm legitimate callers.
**STATUS:** IMPLEMENTED in M0 semantics; EXPERIMENTAL in V2 pretext modeling.

## DD-05 - Personal knowledge does not verify identity

**CONTEXT:** Attackers may know names, addresses, identifiers, subscriptions,
transactions, or incident details.
**DECISION:** V2 stores only knowledge categories under identity pretext;
`IdentityAssurance` remains external and defaults to `UNVERIFIED`.
**RATIONALE:** Knowledge can be stolen or socially engineered and is not proof
of control over an official identity channel.
**TRADE-OFF:** Independent identity verification remains unimplemented.
**STATUS:** EXPERIMENTAL / TESTED.

## DD-06 - Trust does not cancel dangerous behavior

**CONTEXT:** Convincing details and institutional language can coexist with an
OTP, transfer, account-control, or remote-access request.
**DECISION:** Identity pretext and behavioral acts remain separate dimensions.
**RATIONALE:** Apparent legitimacy must not erase what the user is being asked
to do.
**TRADE-OFF:** Future policy must still calibrate benign context without using
trust as a safety override.
**STATUS:** EXPERIMENTAL / TESTED in the V2 mappings and contrastive corpus.

## DD-07 - Sensitive requests are independent of caller credibility

**CONTEXT:** The same sensitive action can appear in banking, telecom, social
media, government, family, support, ecommerce, payment, or crypto pretexts.
**DECISION:** V2 represents action, asset, and destination with domain-agnostic
vocabularies.
**RATIONALE:** The requested capability matters across domains.
**TRADE-OFF:** This schema does not itself determine risk or policy.
**STATUS:** EXPERIMENTAL / TESTED.

## DD-08 - Semantic direction is first-class

**CONTEXT:** "Tell me the code" and "never tell anyone the code" share keywords
but have opposite meanings.
**DECISION:** V2 explicitly models direct, indirect, and partial requests;
warning, negation, question, hypothetical, historical, third-party,
self-service, and discussion directions. Mixed intent uses multiple acts.
**RATIONALE:** Mention detection cannot distinguish active behavior from safety
guidance or reports.
**TRADE-OFF:** Extraction and act matching become structurally richer.
**STATUS:** EXPERIMENTAL / TESTED.

## DD-09 - Sensitive values are absent from V2 signals

**CONTEXT:** Evaluation needs to identify protected asset types without
retaining their contents.
**DECISION:** V2 stores categories and subtypes, never OTP contents, passwords,
card values, recovery-code contents, seed phrases, private keys, addresses, or
government-ID values. Strict parsing rejects extra value fields.
**RATIONALE:** Semantic evaluation does not require secrets or personal data.
**TRADE-OFF:** V2 cannot reproduce or inspect a sensitive value, by design.
**STATUS:** EXPERIMENTAL / TESTED.

## DD-10 - Adversarial evaluation precedes V2 production integration

**CONTEXT:** M0 gaps became visible only after broad contrastive testing.
**DECISION:** Map and evaluate the 57-case corpus before connecting V2 to a
provider, risk engine, API, or UI.
**RATIONALE:** Empirical semantic evidence should precede production policy.
**TRADE-OFF:** V2 produces no user-facing protection today.
**STATUS:** EXPERIMENTAL / TESTED; production integration is PLANNED.

## DD-11 - Pause M2 rather than build on inadequate semantics

**CONTEXT:** Session accumulation raised unresolved identity and requested-action
persistence questions while M0's cross-domain gaps were becoming clear.
**DECISION:** Preserve M2 on `wip/m2-paused-session` and return `main` to the
canonical workstation baseline.
**RATIONALE:** Session memory should retain evidence, not conceal policy or
amplify an inadequate representation.
**TRADE-OFF:** Current production remains single-turn.
**STATUS:** EXPERIMENTAL work paused outside `main`; continuation is PLANNED.

## DD-12 - Keep experimental V2 isolated from M0

**CONTEXT:** M0 is a working, tested production path while V2 is research.
**DECISION:** Place V2 under `guardian.experimental`, do not export it through
`guardian.__init__`, and do not connect it to pipeline, risk, Canary, API, or
frontend.
**RATIONALE:** Research can evolve without silently changing product behavior.
**TRADE-OFF:** Two representations coexist temporarily.
**STATUS:** EXPERIMENTAL / TESTED isolation.

## DD-13 - Ground truth and replay data are not fraud rules

**CONTEXT:** Scenario expectations and V2 mappings could be mistaken for a new
scoring engine or model output.
**DECISION:** Treat expected values as human-curated diagnostic assertions;
replay observations are deliberately synthetic evaluator fixtures.
**RATIONALE:** Evaluation evidence must not silently become product policy.
**TRADE-OFF:** Human review and provenance remain essential.
**STATUS:** IMPLEMENTED / TESTED in the diagnostic harnesses.

## DD-14 - Extraction impact is not fraud risk

**CONTEXT:** Some extraction errors could seriously distort later reasoning,
but no RiskEngineV2 exists.
**DECISION:** M1.2A labels the possible downstream impact of semantic mistakes
independently from conversation risk.
**RATIONALE:** Direction and destination reversals deserve visibility without
pretending to assess fraud.
**TRADE-OFF:** Impact labels must never be presented as scam severity or model
accuracy.
**STATUS:** EXPERIMENTAL / TESTED.

## DD-15 - The M1.2A comparator is provider-independent

**CONTEXT:** Gemini quota was unavailable, but evaluator correctness could be
developed offline.
**DECISION:** Compare expected and observed `ScamSignalsV2` objects without
Gemini, network, RiskEngine, or Canary dependencies.
**RATIONALE:** Comparator behavior can be frozen and tested before live model
benchmarking.
**TRADE-OFF:** Current replay results measure the harness only.
**STATUS:** EXPERIMENTAL / TESTED. M1.2B provider integration is PLANNED.

## Constitutional summary

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These principles govern design review. They are not unsupported claims about
Guardian Call's accuracy.
