# Guardian Call — Agent Instructions

These instructions apply to all coding agents working in this repository.

Read `PROJECT_CONTEXT.md` before making architectural or product decisions.

## Primary goal

Build Guardian Call incrementally, beginning with M0:

```text
Text → Gemini → Signal → Risk Engine → Canary → USER_WARNING
```

Do not broaden scope until the current milestone works and is tested.

---

## Working rules

### 1. Preserve architectural boundaries

Do not merge the responsibilities of Gemini, Risk Engine and Canary.

- Gemini extracts meaning and structured signals.
- Risk Engine calculates explainable risk.
- Canary authorizes consequential actions.

No component may directly perform a consequential action unless the action has passed through Canary.

### 2. Prefer a modular monolith

Do not introduce:
- microservices;
- queues;
- distributed systems;
- multiple autonomous agents;
- extra databases;

unless the current implementation has a concrete requirement for them.

Explain the need before adding infrastructure.

### 3. Make changes small and reviewable

For each task:
1. inspect the relevant files;
2. state the implementation plan;
3. make the smallest coherent change;
4. run relevant tests;
5. report what changed;
6. report any assumptions or unresolved issues.

Avoid large unrelated refactors.

### 4. Never silently change product policy

If implementation requires changing:
- risk semantics;
- Canary authority;
- privacy behavior;
- Trusted Circle escalation;
- canonical event names;
- user-facing safety behavior;

stop and surface the decision instead of silently choosing a new policy.

### 5. Treat privacy as a core requirement

Never log secrets, OTP values, passwords, or full private transcripts unless a test explicitly uses synthetic data.

Default to minimum necessary information.

### 6. Use synthetic test data

All fraud scenarios and phone conversations used in development must be fictional or synthetic.

Do not put real personal data, credentials, phone numbers, tokens or financial information into the repository.

### 7. Explainable risk only

Do not implement opaque output such as:

```text
scam_probability = 0.87
```

as the sole decision mechanism.

Risk decisions must include explicit reasons/signals.

### 8. Observability is required

Important state transitions should emit structured events.

Do not add UI behavior that cannot be traced back to a real backend event.

### 9. Test both fraud and legitimate conversations

Every material scam-detection change should consider:
- true positives;
- false positives;
- benign financial conversation;
- ambiguous language;
- adversarial phrasing.

### 10. Avoid fake completeness

If a component is mocked or simulated, label it clearly.

Do not present:
- simulated telephony as live carrier integration;
- hardcoded events as agent reasoning;
- prerecorded visualizer sequences as live observability.

---

## Coding conventions

Until the repository defines stricter conventions:

- Python: type hints for public functions.
- Prefer small pure functions for risk and policy logic.
- Keep model/API integration isolated from deterministic logic.
- Use explicit domain models for signals, risk, events and Canary decisions.
- Avoid hidden global state.
- Use environment variables for secrets.
- Never commit `.env` files or credentials.
- Add tests with every non-trivial behavior change.

---

## Expected initial structure

A reasonable starting point is:

```text
backend/
  guardian/
    agent.py
    models.py
    signals.py
    risk.py
    canary.py
    events.py
    actions.py
  tests/

frontend/
  guardian/
  visualizer/

scenarios/
```

This is guidance, not a reason to create empty complexity. Create files when they have real responsibilities.

---

## M0 Definition of Done

Input:

```text
Tell me the six-digit code you just received.
```

Expected behavior:

1. input accepted;
2. Gemini returns a structured `otp_request` signal;
3. Risk Engine produces `CRITICAL` with explicit reasons;
4. Canary authorizes `warn_user`;
5. backend emits `USER_WARNING`;
6. automated test passes reliably.

Do not begin M1 audio work until M0 is green.
