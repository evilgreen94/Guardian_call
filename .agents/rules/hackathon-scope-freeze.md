---
description: Always-on hackathon scope guard for Guardian Call.
activation: always
---

# Guardian Call — Hackathon Scope Freeze

The repository is in hackathon delivery mode.

## Canonical product

Guardian Call protects a user during a potentially fraudulent conversation.

Canonical flow:

```text
CONVERSATION / AUDIO
        ↓
      GEMINI
semantic extraction
        ↓
   ScamSignals
        ↓
SESSION RISK STATE
NORMAL → SUSPICIOUS → HIGH → CRITICAL
        ↓
      CANARY
policy authority
        ↓
 ┌──────┴─────────┐
 ↓                ↓
WARN USER     TRUSTED CIRCLE
        │
        ▼
REAL DOMAIN EVENTS
        │
        ▼
   VISUALIZER
```

## Canonical architecture rules

1. Main is canonical. Experimental/lab branches are sources of ideas only.
2. Never merge the experimental branch wholesale.
3. Gemini understands/extracts. It does not calculate final risk or authorize actions.
4. Risk Engine remains deterministic and explainable.
5. Canary controls consequential actions.
6. Extraction failure remains explicit. Never convert extraction failure into false NORMAL or fabricated HIGH risk.
7. UI/visualizer must consume real backend events.
8. Preserve all existing M0 tests.
9. Prefer adapting lab code to main architecture, never replacing main architecture with lab code.
10. Make changes small, reviewable, reversible and milestone-scoped.

## Approved hackathon MVP scope

Only these capabilities are approved:

- existing M0 text → Gemini → ScamSignals → Risk → Canary → action;
- minimal FastAPI server;
- text analysis endpoint using existing core;
- SSE endpoint for real Guardian events;
- minimal browser visualizer;
- multi-turn CallSession / conversation state;
- controlled audio input after browser pipeline works;
- minimal Trusted Circle event for CRITICAL risk;
- synthetic scenarios required for demo;
- Cloud Run deployment after local demo is stable.

## Explicitly frozen / parking lot

Do NOT implement or port without explicit human approval:

- email / IMAP;
- inbox scanning;
- vision / OCR;
- Guardian 360;
- image analysis;
- crypto/email/phishing product channels;
- production mobile app;
- direct SIM-call capture;
- authentication/accounts;
- sophisticated persistence;
- microservices;
- additional autonomous agents;
- production SMS/WhatsApp delivery;
- automatic call termination.

If a requested task would touch frozen scope, stop and report it instead.

## Demo-first rule

Every development day must end with a demonstrable build.

Do not trade a working demo for architectural breadth.
