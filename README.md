# Guardian Call — Agentic Phone-Scam & Omnichannel Protection System

> **"Detect the manipulation. Break the isolation. Protect the person before fraud becomes loss."**

Guardian Call is an agentic protection system built for the **All Things Agentic Hackathon 2026** (Google Agentics). It analyzes conversational text, audio, and screenshots in real time, detects scam manipulation tactics using a multi-agent **Google ADK** pipeline powered by **Gemini 3.5**, evaluates explainable risk, and executes interventions strictly governed by **Canary Policy Guardrails**.

---

## Current Status (Version 0.6.0 — Full M1 & Guardian 360 Multimodal Completed)

Branch: **`lab/splurtch-dev-antigravity`**  
Test Suite: **37 / 37 tests passing (`python -m pytest`)**

```text
                                USER INPUT STREAM
                     (Text / Chat / Screenshot / Bank Receipt)
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                     ▼
              [Text Input]                        [Image / Screenshot]
                     │                                     │
                     │                            Google ADK Agent #1
                     │                         (vision_ocr_agent)
                     │                            model: gemini-3.5-flash
                     │                                     │
                     │                           Emits IMAGE_PROCESSED_OCR
                     │                                     │
                     └──────────────────┬──────────────────┘
                                        ▼
                               Google ADK Agent #2
                           (signal_extraction_agent)
                              model: gemini-3.5-flash
                                        │
                              Emits SIGNAL_DETECTED
                                        │
                                        ▼
                             DETERMINISTIC RISK ENGINE
                                        │
                              Emits RISK_UPDATED
                                        │
                                        ▼
                             CANARY POLICY GUARDRAIL
                                        │
                      Emits CANARY_EVALUATION / USER_WARNING
                                        │
                             [If Risk is CRITICAL]
                                        ▼
                           TRUSTED CIRCLE NOTIFICATION
                      (Emits TRUSTED_CONTACT_NOTIFIED Event)
```

---

## Key Implemented Components

### 1. Google ADK Multi-Agent Pipeline (`google-adk`)
- **Signal Extraction Agent:** [`backend/guardian/agent.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/agent.py) — `LlmAgent` using `gemini-3.5-flash` with Pydantic output schema (`ScamSignalsSchema`). Extracted 10 signals: `identity_claim`, `identity_verified`, `financial_context`, `urgency`, `secrecy_request`, `otp_request`, `password_request`, `transfer_request`, `remote_access_request`, `requested_action`.
- **Multimodal Vision/OCR Agent (Guardian 360):** [`backend/guardian/vision_agent.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/vision_agent.py) — `LlmAgent` using `gemini-3.5-flash` Multimodal. Extracts OCR transcripts, detects visual forgery/manipulation in fake receipts, and classifies input channels (`chat_screenshot`, `bank_receipt`, `sms_screenshot`, etc.).

### 2. Deterministic Risk Engine & Canary Policy Guardrails
- **Risk Engine:** [`backend/guardian/risk.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/risk.py) — Computes transparent, explainable risk levels (`NORMAL`, `SUSPICIOUS`, `HIGH`, `CRITICAL`) from contributing signals.
- **Canary Policy Engine:** [`backend/guardian/canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/canary.py) — Authority layer enforcing user autonomy and strict privacy rules (`share_transcript` -> `DENY`, `end_call` -> `ASK_USER`, `warn_user` -> `ALLOW` on `HIGH`/`CRITICAL`, `notify_trusted_circle` -> `ALLOW` on `CRITICAL`).
- **Trusted Circle Notifier:** [`backend/guardian/trusted_circle.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/trusted_circle.py) — Dispatches privacy-preserving notifications (webhook/SMS) under `CRITICAL` risk without transmitting raw transcripts.
- **Fail-safe Posture (ADR-002):** [`backend/guardian/pipeline.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/pipeline.py) — Preserves privacy and defaults to a cautious `HIGH` risk state if Gemini extraction encounters network or API errors.

### 3. Google Cloud Run Backend Server
- **File:** [`backend/server.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/server.py)
- **Containerization:** [`Dockerfile`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/Dockerfile) & [`.dockerignore`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/.dockerignore) optimized for **Google Cloud Run** (`gcloud run deploy`).
- **Endpoints:**
  - `POST /api/v1/analyze`: Analyzes text input and returns structured risk, Canary decision, and live event stream.
  - `POST /api/v1/analyze-image`: Analyzes image/screenshot upload via `UploadFile` multipart form-data.
  - `GET /health` / `GET /api/v1/health`: Health check probes for Cloud Run.
  - `GET /`: Serves the Guardian Visualizer UI.

### 4. Guardian Visualizer UI (Industrial Brutalism & Emil Design Engineering)
- **Location:** [`frontend/visualizer/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/frontend/visualizer/)
- **Design System:** Industrial Brutalist CRT terminal (`#0A0A0A` substrate, sharp 90° corners, `JetBrains Mono` typography) combined with Emil Kowalski's micro-interactions (`scale(0.97)` press feedback, `@starting-style` smooth enter transitions).
- **Features:** Drag & Drop image upload zone for screenshots, live event stream log, signals telemetry matrix, risk reasons, preset scenario buttons, and protected user warning overlay (`POSIBLE ESTAFA`).

### 5. Synthetic Scenarios & Testing Suite
- **Scenarios:** [`scenarios/bank_otp_scam.json`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/bank_otp_scam.json) & [`scenarios/legitimate_call.json`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/legitimate_call.json)
- **CLI Runner:** [`scenarios/runner.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/runner.py)
- **Test Suite:** [`tests/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/tests/) — **37 unit & integration tests passing** covering signals, vision agent, risk engine, canary policy, trusted circle, ADK agent, fail-safe pipeline, and FastAPI HTTP endpoints.

### 6. Guardian 360 Architectural Spec (Omnichannel Expansion)
- **Specification:** [`docs/specs/2026-08-20-guardian-360-design.md`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/specs/2026-08-20-guardian-360-design.md)
- **Roadmap:** Omnichannel multi-agent expansion covering screenshots, fake receipts, phishing emails, and malicious URLs.

---

## Quickstart Guide

### 1. Installation & Setup
```bash
# Clone repository and navigate to folder
git clone https://github.com/evilgreen94/Guardian_call.git
cd Guardian_call
git checkout lab/splurtch-dev-antigravity

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
TRUSTED_CIRCLE_WEBHOOK_URL=https://api.example.com/trusted-circle-webhook
```

### 3. Run Automated Tests
```bash
python -m pytest
```

### 4. Run Local Backend & Guardian Visualizer UI
```bash
python backend/server.py
```
Open **[http://localhost:8080/](http://localhost:8080/)** in your web browser.

### 5. Run Synthetic Scenario CLI Evaluation
```bash
python scenarios/runner.py
```

---

## Repository Structure

```text
Guardian_call/
├── backend/
│   ├── guardian/
│   │   ├── actions.py          # Authorized intervention execution
│   │   ├── agent.py            # Google ADK LlmAgent for text signals (gemini-3.5-flash)
│   │   ├── canary.py           # Canary Policy Engine & authority guardrails
│   │   ├── events.py           # Domain event definitions & InMemoryEventSink
│   │   ├── models.py           # Domain data models (ScamSignals, RiskAssessment, etc.)
│   │   ├── pipeline.py         # GuardianPipeline coordinator (process_text & process_image)
│   │   ├── risk.py             # Deterministic explainable Risk Engine
│   │   ├── signals.py          # ScamSignals constructor & helper functions
│   │   ├── trusted_circle.py   # Trusted Circle notification client (SMS/Webhook)
│   │   └── vision_agent.py     # Google ADK Multimodal Vision/OCR LlmAgent (gemini-3.5-flash)
│   └── server.py               # FastAPI server for Google Cloud Run (POST /api/v1/analyze & analyze-image)
├── frontend/
│   └── visualizer/             # Industrial Brutalist Visualizer UI (Drag & Drop, HTML, CSS, JS)
├── scenarios/
│   ├── bank_otp_scam.json      # Synthetic bank OTP scam transcript
│   ├── legitimate_call.json    # Synthetic benign appointment transcript
│   └── runner.py               # CLI scenario evaluator
├── tests/                      # 37 unit & integration tests (pytest)
├── docs/
│   ├── ADR-001-gemini-signal-agent-adk.md
│   ├── ADR-002-text-pipeline-failsafe.md
│   └── specs/
│       └── 2026-08-20-guardian-360-design.md
├── Dockerfile                  # Google Cloud Run container recipe
├── .dockerignore
└── requirements.txt            # Project dependencies (google-adk, fastapi, uvicorn, pytest)
```

---

## Architecture Decision Records (ADRs) & Specs

- [ADR-001: Use Google ADK for the Gemini Signal-Extraction Agent](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/ADR-001-gemini-signal-agent-adk.md)
- [ADR-002: Fail-Safe Risk Handling when Gemini Signal Extraction Fails](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/ADR-002-text-pipeline-failsafe.md)
- [Guardian 360 Multi-Agent Architecture Specification](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/specs/2026-08-20-guardian-360-design.md)
