# Guardian Call Threat Model

## Purpose and scope

This document defines the adversarial surface that Guardian Call must eventually
understand. It is a diagnostic model for evaluating the current M0 pipeline; it
does not change `ScamSignals`, `RiskEngine`, Canary policy, or product behavior.

Guardian Call protects people during social-engineering conversations. The
threat is not limited to a caller pretending to be a bank. The same manipulation
patterns appear in telecom, social media, ecommerce, government impersonation,
technical support, family impersonation, cryptocurrency, and account recovery.

## Canary constitution

> **KNOWLEDGE IS NOT AUTHENTICATION.**

> **TRUST DOES NOT CANCEL DANGEROUS BEHAVIOR.**

> **SENSITIVE REQUESTS OUTWEIGH APPARENT LEGITIMACY.**

These principles are architectural constraints, not model hints. A caller's
knowledge, confidence, institutional language, or accurate account context must
never be treated as independent proof of identity. Apparent credibility must not
neutralize evidence of a dangerous requested action.

## Threat dimensions

### 1. Identity / pretext

An identity claim is the role, organization, or relationship a caller claims.
Examples include bank fraud staff, telecom support, police, tax authorities,
Microsoft support, ecommerce support, a family member, or a social-network
employee.

Pretexts establish a plausible reason for contact. Common pretexts include a
fraudulent charge, expiring subscription, infected computer, detained relative,
account lockout, refund, delivery problem, or compromised crypto wallet.

Conversational details are evidence of a claim, not authentication. Names,
addresses, customer numbers, account history, employee IDs, and institution
names may be stolen, purchased, guessed, or socially engineered. M0 has no
independent identity-verification channel.

### 2. Manipulation tactics

Manipulation tactics shape the user's decision environment. The principal
families are:

- urgency and artificial deadlines;
- fear, threats, penalties, or loss;
- secrecy and isolation from trusted people;
- pressure to remain on the call;
- authority pressure;
- scarcity or expiring opportunity;
- emotional emergency and family impersonation;
- protective pretexts such as a "safe account";
- intimidation;
- rewards, refunds, or exceptional offers.

Tactics matter independently and in combination. They describe how influence is
applied; they are not substitutes for identifying the requested action.

### 3. Sensitive assets

Sensitive assets are information, money, or control whose disclosure or transfer
can enable harm:

- one-time passcodes and verification codes;
- passwords, PINs, security answers, and recovery codes;
- login approvals, reset links, authentication tokens, and 2FA settings;
- payment-card number, expiry date, and CVV/CVC;
- bank funds, payment-app balances, gift cards, and cryptocurrency;
- seed phrases, private keys, and wallet access;
- account recovery email or phone settings;
- device control, remote desktop access, and screen contents;
- identity and account data.

Mentioning a sensitive asset is not the same as requesting it. Semantic subject,
object, direction, tense, negation, and modality must all be considered.

### 4. Requested actions

Requested actions describe what the caller wants the protected person to do.
Dangerous examples include revealing a code or password, approving a login,
changing recovery settings, disabling 2FA, sharing card data, transferring money,
buying gift cards or crypto, installing remote-control software, sharing a screen,
or moving funds to a purported safe account.

Safe actions may use the same vocabulary: entering a code privately in an
official app, changing a password independently in account settings, refusing a
transfer, ending the call, or contacting an organization through a verified
channel. Direction and destination are therefore essential.

### 5. Target context

Target context identifies the system or relationship under attack. It is not a
risk score. Relevant contexts include:

- banking and payment apps;
- telecom subscriptions and SIM/account control;
- social-media accounts;
- email and account recovery;
- ecommerce orders and refunds;
- government, police, and tax impersonation;
- technical support and device administration;
- family and trusted-relationship impersonation;
- cryptocurrency wallets and exchanges.

Dangerous requests remain dangerous across domains. An OTP requested by fake
social-media support can enable account takeover just as an OTP requested by a
fake bank can enable financial theft. Financial context is neither necessary nor
sufficient for serious risk.

## Semantic direction

The evaluator must distinguish an active request from nearby language:

- **Positive request:** the caller asks the user to perform an action.
- **Negation:** the caller says not to perform it.
- **Question:** the caller asks whether someone else requested or performed it.
- **Hypothetical:** the action is conditional or educational.
- **Historical:** the action occurred in the past.
- **Third-party description:** another person is the subject or object.

Keyword presence alone cannot make this distinction. Contrastive cases must keep
vocabulary similar while changing semantic direction.

## Privacy constraints

- Use only fictional or synthetic conversations and identifiers.
- Never store or log real OTPs, passwords, PINs, card data, recovery codes,
  private keys, seed phrases, access tokens, or API keys.
- Do not retain full private transcripts as diagnostic metadata.
- Record the minimum evidence needed to reproduce a synthetic evaluation.
- Do not share transcripts or notify third parties without explicit Canary
  authority and product policy.
- Treat model and extraction failures as observable outcomes; never replace them
  with fabricated signals.

## M0 evaluation boundary

M0 evaluates one text input at a time through the existing pipeline:

```text
Text -> GeminiSignalExtractor -> ScamSignals -> RiskEngine -> Canary -> events
```

This threat model intentionally reaches beyond the current M0 schema so that
unsupported concepts become measurable findings. It does not imply session
memory, caller authentication, audio processing, or a revised risk policy.
