# Design Document: Live Audio Protection & ScamTrap Counter-Deception Engine

**System:** Guardian Call — Omnichannel Protection System  
**Date:** 2026-08-25  
**Version:** 1.1.0  
**Branch:** `lab/splurtch-dev-antigravity`  
**Authors:** Antigravity AI & Guardian Call Team  

---

## 1. Overview & Purpose

This specification defines two major strategic enhancements for Guardian Call:
1. **Live Audio Telemetry & Real-Time Speech Capture (Option A):** Captures live voice streams from the browser via WebSpeech API / MediaRecorder, processes text and audio turns through `CallSession`, and routes them seamlessly into the Google ADK Gemini 3.5 signal extraction pipeline.
2. **ScamTrap Counter-Deception Agent & Intelligence Extraction Engine (Option B):** An autonomous Google ADK `LlmAgent` activated upon `HIGH` or `CRITICAL` risk to generate tactical stalling responses ("honey-agent" time-waster), extract scammer threat intelligence (fake URLs, IBANs, phone numbers), and present actionable defense scripts in the Guardian Visualizer CRT UI.

---

## 2. System Architecture & Component Interaction

```text
               LIVE BROWSER VOICE INPUT (WebSpeech / MediaRecorder)
                                       │
                                       ▼
                       POST /api/v1/analyze (session_id)
                                       │
                         GUARDIAN PIPELINE (pipeline.py)
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
    GEMMA GUARDRAIL                                      CALL SESSION STORE
 (gemma_guardrail.py)                                     (session.py)
            │                                                     │
            └──────────────────────────┬──────────────────────────┘
                                       ▼
                             GOOGLE ADK AGENT #1
                         (signal_extraction_agent)
                            model: gemini-3.5-flash
                                       │
                             DETERMINISTIC RISK ENGINE
                                    (risk.py)
                                       │
                          CANARY POLICY GUARDRAILS
                                   (canary.py)
                                       │
              ┌────────────────────────┴────────────────────────┐
              ▼                                                 ▼
    [If Risk >= HIGH / CRITICAL]                      [Normal Execution]
   CANARY POLICY AUTHORIZES:                             WARN_USER
   ActionType.ACTIVATE_SCAMTRAP                      USER_WARNING Event
              │
              ▼
      GOOGLE ADK AGENT #3
   (scamtrap_counter_agent)
     model: gemini-3.5-flash
              │
    Emits Domain Events:
    • SCAMTRAP_ACTIVATED
    • INTELLIGENCE_EXTRACTED
              │
              ▼
   REAL-TIME SSE TELEMETRY STREAM -> GUARDIAN VISUALIZER CRT UI
```

---

## 3. Detailed Component Specifications

### 3.1 Live Audio Telemetry (`frontend/visualizer/app.js` & `index.html`)

- **Browser Audio Listener:** Implements continuous recognition using `webkitSpeechRecognition` / `SpeechRecognition` when `[ 🎤 INICIAR MIC EN VIVO ]` is toggled.
- **Session Continuity:** Maintains a stable `session_id` in `localStorage` across speech bursts so multi-turn context accumulates correctly in `CallSessionStore`.
- **UI State Indicators:** Updates mic status indicator: `MIC: INACTIVO` -> `[ 🔴 ESCUCHANDO EN VIVO... ]` with live transcript preview and status pulse.

### 3.2 ScamTrap Counter-Deception Agent (`backend/guardian/scamtrap.py`)

- **Agent Name:** `scamtrap_counter_agent`
- **Framework:** `google-adk` (`LlmAgent`) using `gemini-3.5-flash`.
- **Pydantic Output Schema (`ScamTrapIntelligenceSchema`):**
  - `stalling_response` (`str`): Tactical stalling phrase to keep the scammer occupied without revealing real personal data (e.g., "Espere un momento, estoy buscando las gafas...", "Me sale un mensaje de error en la app del banco, ¿me repite su código de empleado?").
  - `extracted_phishing_urls` (`List[str]`): Extracted malicious domains or URLs mentioned.
  - `extracted_ibans` (`List[str]`): Extracted IBANs, bank accounts, or crypto wallet addresses.
  - `extracted_phone_numbers` (`List[str]`): Phone numbers provided by caller for out-of-band callbacks.
  - `scammer_tactics_summary` (`str`): Brief tactical breakdown of scammer tactics.

### 3.3 Domain Model Extensions

- **New Action Type ([`backend/guardian/models.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/models.py)):**
  - `ActionType.ACTIVATE_SCAMTRAP = "activate_scamtrap"`
- **New Event Types ([`backend/guardian/events.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/events.py)):**
  - `EventType.SCAMTRAP_ACTIVATED = "scamtrap_activated"`
  - `EventType.INTELLIGENCE_EXTRACTED = "intelligence_extracted"`
- **Canary Policy Rules ([`backend/guardian/canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/canary.py)):**
  - `ACTIVATE_SCAMTRAP` authorized when `RiskLevel` is `HIGH` or `CRITICAL`.

### 3.4 Guardian Visualizer CRT UI Enhancements

- **ScamTrap Widget ([`frontend/visualizer/index.html`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/frontend/visualizer/index.html)):**
  - Dedicated tactical panel: `[ 🍯 SCAMTRAP HONEY-AGENT // THREAT COUNTERMEASURE ]`.
  - Stalling response generator card with 1-click "Copiar Respuesta Táctica" button.
  - Extracted Threat Intelligence matrix table (URLs, IBANs, Caller Identity).

---

## 4. Verification & Testing Strategy

1. **Unit Tests (`tests/test_scamtrap.py`):**
   - Verify `scamtrap_counter_agent` initialization and Pydantic schema validation.
   - Test ScamTrap activation logic under `HIGH` and `CRITICAL` risk states.
   - Verify non-activation under `NORMAL` and `SUSPICIOUS` risk states.
2. **Pipeline Integration Tests (`tests/test_events_and_pipeline.py`):**
   - Verify `SCAMTRAP_ACTIVATED` and `INTELLIGENCE_EXTRACTED` events emitted into `InMemoryEventSink`.
3. **Full Pytest Execution:**
   - Ensure 100% pass rate across the full test suite.
