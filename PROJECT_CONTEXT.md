# Guardian Call — Project Context

## Project

**Guardian Call** is an agentic protection system designed to detect phone-scam tactics during a conversation, assess how risk evolves over time, and trigger only the interventions explicitly allowed by policy.

The product thesis is:

> **Detect the manipulation. Break the isolation. Protect the person before fraud becomes loss.**

Guardian Call is being built for the **All Things Agentic Hackathon 2026**.

---

## Core architecture

The canonical execution path is:

```text
INPUT / CALL
    │
    ▼
GEMINI
conversation understanding
    │
    ▼
RISK ENGINE
signals + state
    │
    ▼
CANARY
policy + authority
    │
    ├── WARN USER
    ├── TRUSTED CIRCLE
    └── LOG / MEMORY
```

### Responsibility boundaries

**Gemini**
- Understands the conversation.
- Extracts structured scam signals.
- Does not directly authorize consequential actions.

**Risk Engine**
- Converts detected signals into an explainable risk state.
- Initial states: `NORMAL`, `SUSPICIOUS`, `HIGH`, `CRITICAL`.
- Risk must always be explainable from contributing signals.

**Canary**
- Is the policy and authority layer.
- Decides which actions Guardian is allowed to perform.
- Consequential actions must not bypass Canary.

**Actions**
Initial action types:
- `warn_user`
- `notify_trusted_circle`
- `share_transcript`
- `recommend_end_call`

---

## MVP

The first milestone is deliberately narrow.

```text
TEXT INPUT
    ↓
GEMINI
    ↓
STRUCTURED SIGNAL
    ↓
RISK ENGINE
    ↓
CANARY
    ↓
USER WARNING
```

Canonical M0 test input:

> Tell me the six-digit code you just received.

Expected result:

```text
otp_request = true
risk = CRITICAL
warn_user = ALLOW
event = USER_WARNING
```

Do not introduce audio, VoIP, mobile integration, persistence, microservices, or multiple agents until M0 works reliably.

---

## Initial scam signals

The first signal taxonomy includes:

- `identity_claim`
- `identity_verified`
- `financial_context`
- `urgency`
- `secrecy_request`
- `otp_request`
- `password_request`
- `transfer_request`
- `remote_access_request`
- `requested_action`

Candidate signal object:

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

---

## Initial Canary policy model

Example:

```text
RISK: CRITICAL

warn_user()             ALLOW
notify_trusted_circle() ALLOW
share_transcript()      DENY
recommend_end_call()    ALLOW
end_call()              ASK_USER
```

User privacy and autonomy take priority over feature breadth.

---

## Trusted Circle

Trusted Circle is a pre-authorized group of family members, caregivers, or trusted contacts.

Principles:
- opt-in;
- minimum necessary information;
- explicit escalation policy;
- no transcript sharing by default;
- no automatic disclosure beyond configured policy.

---

## Observability

Every meaningful backend transition should emit an event.

Initial events:

- `INPUT_RECEIVED`
- `SIGNAL_DETECTED`
- `RISK_UPDATED`
- `CANARY_EVALUATION`
- `ACTION_ALLOWED`
- `ACTION_DENIED`
- `USER_WARNING`
- `TRUSTED_CONTACT_NOTIFIED`
- `CALL_ENDED`

The technical visualizer must consume **real backend events**. It must not be a fake demo animation.

---

## Product design

There are two interfaces.

### Guardian UI
For the protected user.

It must be extremely simple during a risky interaction.

Example:

```text
POSIBLE ESTAFA

NO DIGA ESE CÓDIGO

NO REALICE TRANSFERENCIAS
```

### Guardian Visualizer
For observability, testing, judges and technical operators.

Visual direction:
- graphic brutalism;
- classic computer / industrial-terminal influence;
- minimal framing;
- monospaced typography;
- black / off-white base;
- sparse functional colors;
- strong lines, nodes and barriers;
- motion driven by backend events.

Avoid generic "AI startup" styling and decorative sci-fi chrome.

---

## Non-goals for v0.1

Do not build these until the core pipeline is stable:

- unrestricted cellular-call audio capture;
- full Android telephony product;
- multi-agent architecture for its own sake;
- microservices;
- sophisticated long-term memory;
- autonomous call termination;
- unnecessary authentication flows;
- production-grade payments/accounts;
- broad generic fraud detection unrelated to the demo.

---

## Architectural principles

1. **Monolith first.**
2. **One component = one distinct responsibility.**
3. **Gemini understands; Canary authorizes.**
4. **Risk must be explainable.**
5. **Consequential actions must be policy-controlled.**
6. **Events are first-class architecture.**
7. **Do not add a feature unless it helps prove the Guardian Call thesis.**
8. **Prefer the simplest implementation that preserves the architecture.**
