# Demo Script - Archived Draft

> Historical draft. Superseded by `docs/hackathon/DEMO_SCRIPT.md`. Public
> branding is now KERN-3; historical Canary wording below is retained as an
> implementation-era record and must not be used for the final recording.

## Opening

A call begins.

The user sees almost nothing: Guardian is quietly observing.

The technical visualizer shows:

`CALL → GEMINI → RISK → CANARY → ACTION`

## Turn 1 — Identity claim

Caller:
> "Buenas tardes, le llamamos de su banco."

Guardian extracts:
- identity claim: bank;
- identity not independently verified.

No aggressive intervention.

## Turn 2 — Financial concern

Caller:
> "Hemos detectado una operación sospechosa en su cuenta."

Guardian:
- financial context;
- evidence accumulates;
- risk moves upward.

## Turn 3 — Pressure

Caller:
> "Necesitamos solucionarlo inmediatamente. No cuelgue."

Guardian:
- urgency;
- isolation/pressure;
- risk becomes HIGH.

## Turn 4 — Credential theft

Caller:
> "Le hemos enviado un código de seis cifras. Dígamelo ahora."

Guardian:
- OTP request;
- requested action = share OTP;
- risk becomes CRITICAL.

Visualizer:
- Canary boundary activates;
- `WARN_USER → ALLOW`;
- `NOTIFY_TRUSTED_CIRCLE → ALLOW`.

Protected-user UI:

**POSIBLE ESTAFA**

**NO DIGA ESE CÓDIGO**

Trusted Circle panel reacts.

## Close

Explain:

Gemini did not decide the intervention.

Gemini understood the conversation.

The deterministic Risk Engine evaluated the signals.

Canary controlled what the system was allowed to do.

Then show the legitimate-bank scenario briefly to demonstrate restraint.
