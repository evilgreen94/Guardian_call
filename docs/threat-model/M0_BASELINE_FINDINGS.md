# M0 Baseline Findings

## Method

This report records live evaluations through the unchanged M0
`GeminiSignalExtractor` and `GuardianPipeline.process_text()`. Each input is a
separate turn with no session memory. Model output is empirical and may vary
between runs; timestamps are omitted because they are not relevant to semantic
comparison.

The baseline was prepared with six synthetic probes:

1. obvious OTP disclosure request;
2. explicit "never share OTP" negative control;
3. card/CVV disclosure request;
4. remote-access request;
5. credible caller with synthetic personal context but no dangerous request;
6. legitimate bank warning.

Measurements were captured on 2026-08-24 using the configured live Gemini model.
All successful turns emitted canonical M0 events only. An initial sandboxed run
failed with `NETWORK_ERROR`; it was repeated with network access and is not used
as semantic evidence below.

## A. Obvious OTP scam

**INPUT**

> I am Elena from the synthetic Northbridge Bank fraud desk. Read me the six
> digits from the verification message now so I can cancel a pending transfer.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": "bank",
  "identity_verified": false,
  "financial_context": true,
  "urgency": true,
  "secrecy_request": false,
  "otp_request": true,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": "share_otp"
}
```

**RISK**

`CRITICAL` -- explicit OTP disclosure request, unverified bank claim, financial
context, and urgency.

**CANARY**

`warn_user -> ALLOW`; events ended in `ACTION_ALLOWED -> USER_WARNING`.

**EXPECTED SEMANTIC BEHAVIOR**

Recognize a current request to disclose an OTP despite the protective banking
pretext and authorize a warning.

**MATCH / MISMATCH**

`MATCH`

**OBSERVATION**

M0 recognized both the sensitive asset and action direction. The pending
transfer was correctly treated as context, not as a user transfer request.

## B. "Never share OTP" negative control

**INPUT**

> Never share your OTP with me or any caller.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": null,
  "identity_verified": false,
  "financial_context": false,
  "urgency": false,
  "secrecy_request": false,
  "otp_request": true,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": null
}
```

**RISK**

`NORMAL` -- M0 described this as a legitimate OTP flow because no sharing action
was extracted.

**CANARY**

`warn_user -> DENY`; events ended in `ACTION_DENIED`.

**EXPECTED SEMANTIC BEHAVIOR**

Recognize the negation and avoid treating the sentence as an active disclosure
request.

**MATCH / MISMATCH**

`MATCH`

**OBSERVATION**

The extractor preserved action direction through `requested_action=null`, but
`otp_request=true` still conflates an OTP mention with a request. M0 happens to
resolve this case safely through the requested-action check.

## C. Card and CVV request

**INPUT**

> I am Marta from fictional Telestar. To keep the discount, tell me the card
> number and the three security digits on the back.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": "telestar",
  "identity_verified": false,
  "financial_context": true,
  "urgency": true,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": true,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": "share_card_details"
}
```

**RISK**

`SUSPICIOUS` -- unverified identity plus financial context and urgency.

**CANARY**

`warn_user -> DENY`; events ended in `ACTION_DENIED`.

**EXPECTED SEMANTIC BEHAVIOR**

Recognize a current request for payment-card data and CVV as a dangerous
sensitive-data disclosure request capable of authorizing protection.

**MATCH / MISMATCH**

`MISMATCH -- FALSE NEGATIVE`

**OBSERVATION**

M0 has no payment-card or CVV signal. Gemini mapped the request to
`password_request=true` and `requested_action=share_card_details`, but the current
RiskEngine recognizes password theft only for its existing password-action
strings. The dangerous request therefore remained below the warning threshold.

## D. Remote-access request

**INPUT**

> This is Microsoft security support. Install AnyDesk now and accept my
> remote-control request.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": "tech_support",
  "identity_verified": false,
  "financial_context": false,
  "urgency": true,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": true,
  "requested_action": "install_software"
}
```

**RISK**

`CRITICAL` -- remote access under an unverified, urgent support pretext.

**CANARY**

`warn_user -> ALLOW`; events ended in `ACTION_ALLOWED -> USER_WARNING`.

**EXPECTED SEMANTIC BEHAVIOR**

Recognize the active remote-control request and authorize a warning.

**MATCH / MISMATCH**

`MATCH`

**OBSERVATION**

M0 handled both explicit software installation and remote-control acceptance
through the existing `remote_access_request` signal.

## E. Credible caller with no dangerous request

**INPUT**

> I am Marta from fictional Telestar, employee TS-204. I know your synthetic
> customer reference CUST-0042 and see three lines. No action is required; review
> the notice in your official portal.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": "telestar",
  "identity_verified": false,
  "financial_context": false,
  "urgency": false,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": "review_portal_notice"
}
```

**RISK**

`SUSPICIOUS` -- isolated unverified identity claim.

**CANARY**

`warn_user -> DENY`; events ended in `ACTION_DENIED`.

**EXPECTED SEMANTIC BEHAVIOR**

Do not infer independent identity verification from private-data knowledge, and
do not infer a dangerous action where none is requested.

**MATCH / MISMATCH**

`MATCH WITH CALIBRATION NOTE`

**OBSERVATION**

Gemini correctly kept `identity_verified=false`; knowledge did not become
authentication. M0 still assigns `SUSPICIOUS` to any unverified identity claim,
showing contextual over-weighting, but Canary correctly denied an intrusive
warning.

## F. Legitimate bank warning

**INPUT**

> This is a courtesy security warning from synthetic Northbridge Bank. Never
> share a verification code. Do not transfer money; contact the bank through its
> official app.

**EXTRACTED SIGNALS**

```json
{
  "identity_claim": "bank",
  "identity_verified": false,
  "financial_context": true,
  "urgency": false,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": null
}
```

**RISK**

`SUSPICIOUS` -- unverified identity claim combined with financial context.

**CANARY**

`warn_user -> DENY`; events ended in `ACTION_DENIED`.

**EXPECTED SEMANTIC BEHAVIOR**

Recognize safety guidance and negation rather than an OTP disclosure or transfer
request; do not issue a user warning.

**MATCH / MISMATCH**

`MATCH WITH CALIBRATION NOTE`

**OBSERVATION**

The extractor correctly avoided active OTP and transfer signals. M0 nevertheless
elevated the benign message to `SUSPICIOUS` solely from claimed identity and
financial context, another example of contextual over-weighting that does not
cross the current Canary warning boundary.

## Baseline conclusion

The six-case sample exposes both working boundaries and a concrete schema gap.
M0 distinguishes the tested OTP negation, catches explicit OTP theft and remote
access, and refuses to treat synthetic private knowledge as verification. It
does not represent payment-card/CVV requests directly, producing a false
negative at the Canary boundary. It also tends to classify benign institutional
claims as `SUSPICIOUS`, even when no dangerous action is requested.

These are diagnostic findings only. No M0 signals, risk rules, or Canary policy
were changed in response.
