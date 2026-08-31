# Guardian Call Hackathon Demo Script

## Demo contract

This is a concise preparation script, not evidence that every future feature is
implemented. Every segment is labelled:

- **IMPLEMENTED**: available on current `main`.
- **TESTED**: covered by automated regression or deterministic evaluation.
- **EXPERIMENTAL**: available only in the isolated research layer.
- **PLANNED**: not implemented.

Before recording, verify the current checkpoint, test suite, Gemini credentials
and quota, FastAPI server, SSE connection, and selected synthetic scenario. Do
not substitute prerecorded or fabricated events for a failed live path.

## 1. Problem

**NARRATION**

"Phone scams are no longer just obvious requests from unknown callers. A caller
may know your provider, address, account context, or recent activity. Then they
create urgency and ask for a code, transfer, approval, card detail, or remote
access. Guardian Call focuses on that decision window."

**ON SCREEN**

Show `/guardian/` as the protected-user surface and `/visualizer/` as the
technical Canary/observability surface. Do not show unsupported phone-carrier
integration.

## 2. Sophisticated scam example

**IMPLEMENTED demo text path, subject to live Gemini availability**

Use a synthetic OTP scenario such as:

> "I am Elena from the synthetic Northbridge Bank fraud desk. A transfer is
> pending. Read me the six digits from the verification message now so I can
> cancel it."

**NARRATION**

"The protective story sounds plausible, but the requested action would disclose
an authentication secret to the caller."

No real OTP, account, name, phone number, or personal information may be used.

## 3. Guardian analysis

**IMPLEMENTED / TESTED**

Execute the text through the Guardian UI, which submits to
`/api/v1/experimental/v2/turn`. The older `/api/v1/analyze` M0 endpoint remains
useful for core regression, but it is not the primary protected-user demo
surface. Point out the Canary boundary in the technical visualizer:

```text
CALL -> GEMINI -> RISK -> CANARY -> ACTION
```

**NARRATION**

"Gemini extracts structured evidence. It does not authorize an intervention.
Canary remains the authority boundary for user-facing warning behavior."

Call out `identity_verified=false`, OTP involvement, requested action, urgency,
and the resulting explainable risk only if those values are present in the real
response. Do not narrate expected values over a failed extraction.

## 4. Canary intervention

**IMPLEMENTED / TESTED**

Let the real event sequence remain visible:

```text
INPUT_RECEIVED
SIGNAL_DETECTED
RISK_UPDATED
CANARY_EVALUATION
ACTION_ALLOWED
USER_WARNING
```

**NARRATION**

"Guardian identifies and reasons. Canary controls authority. The point reaches
the Canary boundary during evaluation, crosses only after `ACTION_ALLOWED`, and
reaches action only when the real `USER_WARNING` event is emitted."

Show the interrupt headline and only its backend-provided directives. Use
`[ ACK ]` to hide it, then note that acknowledgement changes local UI only; the
domain-event TTY and policy decision remain intact.

Optionally run a legitimate scenario to show `ACTION_DENIED` stopping at Canary
without a warning. This second run is important evidence of restraint.

## 5. Why keyword detection is insufficient

**IMPLEMENTED corpus / EXPERIMENTAL V2 research**

Show a small contrast set without claiming live V2 extraction:

```text
"Tell me your OTP."
"Never tell anyone your OTP."
"Did someone ask for your OTP?"
"If somebody asks for your OTP, hang up."
"Yesterday somebody asked me for my OTP."
```

**NARRATION**

"The sensitive words are nearly identical. What changes is semantic direction:
request, warning, question, hypothetical, or history. Keyword presence alone
cannot represent that distinction."

## 6. Apparent credibility problem

Display the constitutional principles prominently:

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

**NARRATION**

"The corpus varies synthetic knowledge from an organization claim through
names, addresses, customer details, employee IDs, and incident context. Every
credibility level has both safe and dangerous behavior. Knowledge is context;
Guardian currently has no independent identity-verification channel."

These principles are architecture constraints, not claims of measured
accuracy.

## 7. Adversarial evaluation

**IMPLEMENTED / TESTED diagnostic harness**

Show the frozen M0 baseline:

```text
CASES                   57
PASS                    24
RISK MISMATCH           10
CANARY MISMATCH          0
MODEL GAP               22
AMBIGUOUS                1
```

**NARRATION**

"We did not change production to make the test set look better. Twenty-two
cases expose concepts M0 cannot represent, ten expose deterministic risk
mismatches, and one stays intentionally ambiguous. Zero Canary mismatches means
Canary applied the current M0 table consistently; it does not mean perfect
end-to-end detection."

Mention that the 105 passing tests are software regression coverage, not model
accuracy.

## 8. ScamSignalsV2 semantic model

**EXPERIMENTAL / TESTED / NOT CONNECTED TO PRODUCTION**

Show this research model:

```text
identity pretext + knowledge categories + contexts

semantic direction + action + protected asset + destination

actor + manipulation
```

**NARRATION**

"V2 represents all 57 cases without adding one scam-specific field for every
new trick. It stores semantic categories, not secret values. But it is isolated
research: there is no Gemini V2 extractor, RiskEngineV2, production API path, or
Canary integration."

Then show the comparator boundary:

```text
expected ScamSignalsV2
          <->
observed ScamSignalsV2
          |
          v
pure semantic comparator
```

Run or show the offline replay report only with this label:

```text
SYNTHETIC OFFLINE REPLAY // NOT GEMINI ACCURACY
```

Explain that the 16 fixtures deliberately inject errors to prove the evaluator
can detect missing acts, false acts, direction flips, destination flips, and
ambiguity.

## 9. Privacy and safety

**IMPLEMENTED / TESTED boundaries with documented limitations**

**NARRATION**

"V2 semantic mappings omit OTP contents, passwords, card numbers, CVVs,
recovery-code contents, seed phrases, private keys, and raw personal knowledge.
Canary separates risk from action authority, and ambiguity remains explicit."

Then state the current limitation without qualification:

"Current production text is sent to Gemini for extraction. This prototype does
not provide fully local or proven end-to-end private transcript processing."

Do not claim compliance, on-device processing, hardened API authorization, or a
production retention policy.

## 10. Future work

**PLANNED / NOT YET IMPLEMENTED**

```text
M1.2B:
conversation -> Gemini V2 extractor -> observed ScamSignalsV2
                                   -> frozen M1.2A comparator
expected human-curated ground truth ->
```

**NARRATION**

"The next research step is to benchmark live Gemini V2 extraction against the
frozen comparator. Only after reviewing that evidence should the project design
future risk policy or revisit multi-turn sessions."

Mention separately as planned or limited: direct telephony integration,
independent identity assurance, Trusted Circle delivery, production
persistence, and deployment hardening. Browser microphone STT is a controlled
hackathon demo path, not phone-call interception.

M2 work is preserved outside `main` on `wip/m2-paused-session` and is not part
of the demo's implemented path.

## Closing line

"Guardian Call is not asking an AI to make an opaque safety decision. It
separates understanding, explainable reasoning, policy authority, and action,
then red-teams the semantic foundation before expanding the product."
