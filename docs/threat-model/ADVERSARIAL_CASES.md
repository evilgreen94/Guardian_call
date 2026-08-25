# Guardian Call Adversarial Cases

## Evaluation method

These contrastive groups test semantic direction, not keyword recognition. Each
group holds the sensitive concept relatively constant while changing whether a
current caller is actually asking the protected person to do something.

The expected interpretation labels below describe language semantics. They do
not prescribe an M0 risk level or Canary decision.

## Evaluation modes

The red-team harness has two explicitly different paths:

```text
LIVE EXTRACTOR
raw synthetic text -> GeminiSignalExtractor -> GuardianPipeline.process_text()

OFFLINE ORACLE
predefined ScamSignals M0 -> GuardianPipeline.process_signals()
```

Live mode evaluates Gemini, RiskEngine, and Canary together. Oracle mode does
not initialize Gemini, requires no API key or network, and evaluates only the
existing deterministic RiskEngine and CanaryPolicy. Oracle signals are manually
declared ground truth for the current M0 schema; they are never presented as
model output.

The scenario expectation is an assertion, not an alternative scoring system.
Risk and Canary always execute through the production M0 pipeline. The harness
only compares their returned values with the declared security expectation.

Oracle outcomes are mutually exclusive:

- `PASS`: representable signals produced the expected risk and Canary decision.
- `RISK MISMATCH`: correct representable signals reached RiskEngine, but its
  deterministic assessment differed from the expected security outcome.
- `CANARY MISMATCH`: risk matched, but Canary authorization differed.
- `MODEL GAP`: ScamSignals M0 cannot represent evidence needed by the scenario.
- `AMBIGUOUS`: the case intentionally has no forced pass/fail assertion.

`MODEL GAP` takes precedence over engine comparisons. Unsupported concepts such
as CVV, recovery codes, seed phrases, login approvals, payment-app approvals,
and gift-card payments are recorded in diagnostic metadata and never forced into
unrelated M0 fields. The metadata never enters RiskEngine or CanaryPolicy.

Future expected-versus-observed extraction evaluation will compare Gemini output
field by field with the same oracle signals. Extraction mismatches must remain
separate from model gaps, RiskEngine mismatches, and Canary mismatches.

The architecture and evaluations remain governed by:

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

## Contrastive expansion methodology

The expanded corpus preserves the original `baseline_20` cohort and adds a
`contrastive_expansion_v1` cohort. Historical text, oracle signals, expected
outcomes, model gaps, and result classifications in the original cohort are not
rewritten. New cases are organized as small semantic variations rather than as
unrelated scam stories.

Each scenario declares one or more diagnostic families, a contrast-group ID,
and its role inside that group. Family membership may overlap: an OTP request
from social-network support can simultaneously exercise authentication,
cross-domain masking, manipulation, and a constitutional principle. Global
counts operate on unique scenarios; family counts operate on memberships and
therefore do not sum to the global total.

The principal contrastive families are:

- OTP and authentication codes;
- payment cards and CVV/CVC;
- money movement;
- remote device control;
- account takeover and recovery;
- cryptographic and wallet assets;
- apparent credibility and private knowledge;
- manipulation and social engineering;
- cross-domain masking.

Semantic-direction roles distinguish direct and indirect requests, partial
requests, negation, questions, hypotheticals, historical and third-party reports,
self-service actions, ordinary discussion, and mixed intent. Ground-truth
signals describe who is asking whom to do what using only fields that exist in
M0.

## Expected outcomes are diagnostic

Expected risk and Canary values are manually reviewed assertions used to expose
the current M0 baseline. They are not automatic scores, do not enter the
production pipeline, and are not an implicit specification for ScamSignals v2
or RiskEngine v2. Future production policy must be designed only after reviewing
the empirical findings and tradeoffs, including false positives.

When M0 cannot represent evidence needed by a case, the scenario is classified
as `MODEL GAP` before risk or Canary differences are considered. Unsupported
concepts remain diagnostic metadata. Conversely, a representable signal set
that produces an unexpected risk is a `RISK MISMATCH`; it must not be hidden
behind a model-gap label.

## Apparent credibility matrix

Credibility cases use six levels of entirely synthetic knowledge:

0. organization claim only;
1. synthetic name;
2. name and fictional address;
3. name, address, and synthetic customer reference;
4. account or subscription details;
5. all prior context plus a synthetic employee ID and plausible incident.

Every level has a safe branch with no dangerous request and a dangerous branch
with a sensitive request. This tests both sides of the constitutional boundary:
knowledge cannot authenticate a caller, but knowledge alone must not become a
proxy for fraud.

## Language and realism

The expansion is Spanish-first and uses natural Spanish social-engineering
phrasing, with a smaller English set retained for cross-language robustness. All
names, identifiers, addresses, accounts, incidents, and amounts are synthetic.
The corpus never contains actual credentials, OTP values, payment-card data, or
personal information.

## False-positive controls and mixed intent

Every sensitive family includes nearby legitimate controls: negated requests,
self-service official-channel actions, questions, warnings, historical reports,
or ordinary discussion. Mixed-intent cases deliberately combine reassuring
language with a subsequent dangerous request. This prevents a keyword-only
interpretation of words such as "never", "secure", "official", or "support".

## Constitutional coverage

Scenarios may carry `C1`, `C2`, and `C3` metadata. These labels are used only to
aggregate oracle outcomes and never enter extraction, risk, or Canary policy.
The `/all` report shows case, pass, model-gap, risk-mismatch,
Canary-mismatch, and ambiguous counts for each constitutional principle.

## OTP / verification code

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Tell me the one-time code from the message." | Active request to disclose an OTP. |
| Negation | "Never tell me or anyone else your one-time code." | Explicit prohibition; no disclosure request. |
| Question | "Did anyone ask you for your one-time code?" | Inquiry about another request. |
| Hypothetical | "If somebody asks for your code, end the call." | Conditional safety guidance. |
| Historical | "Yesterday somebody asked me for my one-time code." | Past report, not a current request. |
| Third-party | "The scammer asked him for his verification code." | Description involving another person. |

## Password

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Give me the password for the account." | Active credential-disclosure request. |
| Negation | "Do not give me your password." | Explicit prohibition. |
| Question | "Has support asked you for your password?" | Inquiry about another request. |
| Hypothetical | "If a caller asks for a password, refuse." | Conditional safety guidance. |
| Historical | "Last week a caller requested my password." | Past report. |
| Third-party | "She said the attacker asked her colleague for a password." | Third-party description. |

## CVV / CVC

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Read the three security digits on the back of the card." | Active CVV/CVC disclosure request. |
| Negation | "We will never ask for the security digits on your card." | Explicit prohibition. |
| Question | "Did the seller request your CVV?" | Inquiry about another request. |
| Hypothetical | "If anyone asks for the CVV, do not continue." | Conditional safety guidance. |
| Historical | "The fake agent requested my CVV yesterday." | Past report. |
| Third-party | "The investigator said the scammer took his CVV." | Third-party description. |

## Payment card

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Tell me the full card number and expiry date." | Active card-data disclosure request. |
| Negation | "Do not provide your card number over this call." | Explicit prohibition. |
| Question | "Were you asked to provide a card number?" | Inquiry about another request. |
| Hypothetical | "If a merchant asks by phone, use another verified channel." | Conditional safety guidance. |
| Historical | "I previously gave the caller an expired card number." | Past report. |
| Third-party | "My colleague reported that a caller requested her card details." | Third-party description. |

## Money transfer

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Move your savings to this protected account now." | Active transfer request under protective pretext. |
| Negation | "Do not make any transfer; contact your bank yourself." | Explicit prohibition and safe redirection. |
| Question | "Have you already transferred money to the caller?" | Inquiry about a possible past action. |
| Hypothetical | "If someone asks you to move funds, call the bank." | Conditional safety guidance. |
| Historical | "Yesterday I transferred money after a fake call." | Past report. |
| Third-party | "The police said victims had transferred funds to criminals." | Third-party description. |

## Remote access

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Install the remote-support tool and accept my connection." | Active remote-control request. |
| Negation | "Do not install remote-access software for callers." | Explicit prohibition. |
| Question | "Did support ask you to install AnyDesk?" | Inquiry about another request. |
| Hypothetical | "If a popup asks for remote control, close it." | Conditional safety guidance. |
| Historical | "A fake technician controlled my old computer last month." | Past report. |
| Third-party | "The trainer explained how scammers ask victims to share screens." | Third-party description. |

## Recovery code

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Send me one of your account recovery codes." | Active account-takeover request. |
| Negation | "Never send a recovery code to support." | Explicit prohibition. |
| Question | "Did anyone request a recovery code?" | Inquiry about another request. |
| Hypothetical | "If you are asked for a recovery code, stop responding." | Conditional safety guidance. |
| Historical | "The attacker asked me for a recovery code yesterday." | Past report. |
| Third-party | "She reported that her friend shared a recovery code." | Third-party description. |

## Login approval

| Form | Synthetic input | Semantic interpretation |
| --- | --- | --- |
| Positive request | "Approve the login notification on your phone now." | Active authorization request. |
| Negation | "Do not approve login notifications you did not initiate." | Explicit prohibition. |
| Question | "Did you approve an unexpected login notification?" | Inquiry about a possible action. |
| Hypothetical | "If an unexpected approval prompt appears, reject it." | Conditional safety guidance. |
| Historical | "Yesterday I approved a prompt before realizing it was fake." | Past report. |
| Third-party | "The administrator said another user approved the attacker's login." | Third-party description. |

## Cross-cutting attacks

The structured scenario library also probes:

- apparent credibility without independent authentication;
- credible context followed by a dangerous request;
- safe versus unsafe action destinations;
- indirect and euphemistic requests;
- non-financial account takeover;
- emotional manipulation and isolation;
- safe-account and protective pretexts;
- unsupported assets such as card security codes and seed phrases;
- long-confidence framing compressed into one M0 input;
- ambiguity where conservative interpretation may be appropriate.

Failures should be classified as extraction failure, negation failure,
semantic-direction failure, unsupported sensitive asset, unsupported requested
action, false positive, false negative, contextual over-weighting, identity
over-trust, or insufficient manipulation modeling. Findings are evidence for a
future schema and policy design; they are not permission to alter M0.
