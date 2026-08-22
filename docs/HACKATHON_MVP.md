# Guardian Call — Hackathon MVP

## Product story

A vulnerable user receives a suspicious call.

Guardian Call listens to the conversation, extracts manipulation signals, shows how risk evolves, and intervenes only when Canary policy authorizes it.

The demo must communicate this story without requiring the audience to understand the code.

## MVP end-to-end target

```text
CONTROLLED AUDIO / CONVERSATION
           ↓
         GEMINI
           ↓
      ScamSignals
           ↓
      CallSession
           ↓
       Risk Engine
           ↓
         Canary
       ┌────┴────┐
       ↓         ↓
   User Warn   Trusted Circle
       │
       └────┬────┘
            ↓
       Event Stream
            ↓
        Visualizer
```

## Demo risk evolution

The canonical demo should show gradual escalation:

```text
TURN 1
"Buenas tardes, llamamos de su banco."
→ NORMAL / low evidence

TURN 2
"Hemos detectado una operación sospechosa."
→ SUSPICIOUS

TURN 3
"Necesitamos resolverlo inmediatamente."
→ HIGH

TURN 4
"Le llegará un código. Dígamelo."
→ CRITICAL

CANARY
→ WARN_USER ALLOW
→ NOTIFY_TRUSTED_CIRCLE ALLOW

USER
→ NO DIGA ESE CÓDIGO
```

Exact thresholds are implementation decisions and must remain explainable.

## Four demo scenarios

### 1. Legitimate bank call
Purpose: demonstrate restraint / false-positive control.

### 2. Bank OTP theft
Purpose: canonical CRITICAL path.

### 3. Safe-account transfer scam
Purpose: demonstrate another financial manipulation tactic.

### 4. Fake technical support
Purpose: demonstrate remote-access manipulation.

Do not expand the scenario catalogue until these four are stable.

## Trusted Circle prototype

Hackathon requirement:

- CRITICAL state may authorize a `NOTIFY_TRUSTED_CIRCLE` action.
- The action must emit a real domain event.
- The demo visualizes a trusted contact receiving the event.

Not required for MVP:

- SMS;
- WhatsApp;
- push notification;
- real phone-number delivery.

## Audio prototype

Preferred implementation order:

1. browser/text pipeline works;
2. controlled audio file or microphone;
3. real-time/streaming if time permits;
4. mobile/VoIP only as bonus.

Direct cellular-call capture is not a blocker for hackathon MVP.

## Definition of finished

Guardian is ready for hackathon submission when:

- [ ] M0 remains green.
- [ ] Browser can submit conversational input.
- [ ] Backend produces real events.
- [ ] Visualizer displays those events.
- [ ] Multi-turn risk evolution works.
- [ ] Controlled audio reaches the same pipeline.
- [ ] Critical state triggers user warning.
- [ ] Critical state can trigger Trusted Circle event.
- [ ] Four demo scenarios work reliably.
- [ ] Cloud Run deployment is reproducible.
- [ ] Demo can be performed in < 4 minutes.
