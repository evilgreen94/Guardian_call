# Guardian Call — Agentic Phone-Scam Protection System

> **"Detect the manipulation. Break the isolation. Protect the person before fraud becomes loss."**

Guardian Call is an agentic protection system built for the **All Things Agentic Hackathon 2026** (Google Agentics). It analyzes conversational text and audio in real time, detects scam manipulation tactics using **Google ADK** and **Gemini 3.5**, evaluates explainable risk, and executes interventions strictly governed by **Canary Policy Guardrails**.

---

## Current Status (Version 0.5 — M0 & M0.5 Completed)

Branch: **`lab/splurtch-dev-antigravity`**  
Test Suite: **30 / 30 tests passing (`python -m pytest`)**

### 1. Google ADK Signal Extraction Agent
- **File:** [`backend/guardian/agent.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/agent.py)
- **Framework:** **Google ADK** (`google-adk`) using `LlmAgent`, `Runner`, and `InMemorySessionService`.
- **Model:** `gemini-3.5-flash` with strict Pydantic output schema (`ScamSignalsSchema`).
- **Extracted Taxonomy (10 Signals):** `identity_claim`, `identity_verified`, `financial_context`, `urgency`, `secrecy_request`, `otp_request`, `password_request`, `transfer_request`, `remote_access_request`, `requested_action`.

### 2. Deterministic Risk Engine & Canary Policy Guardrails
- **Risk Engine:** [`backend/guardian/risk.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/risk.py) — Computes transparent, explainable risk levels (`NORMAL`, `SUSPICIOUS`, `HIGH`, `CRITICAL`) from contributing signals.
- **Canary Policy Engine:** [`backend/guardian/canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/canary.py) — Authority layer enforcing user autonomy and strict privacy rules (`share_transcript` -> `DENY`, `end_call` -> `ASK_USER`, `warn_user` -> `ALLOW` on `HIGH`/`CRITICAL`).
- **Fail-safe Posture (ADR-002):** [`backend/guardian/pipeline.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/pipeline.py) — Preserves privacy (only logs text length) and defaults to a cautious `HIGH` risk state if Gemini extraction encounters network or API errors.

### 3. Google Cloud Run Backend Server
- **File:** [`backend/server.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/server.py)
- **Containerization:** [`Dockerfile`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/Dockerfile) & [`.dockerignore`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/.dockerignore) optimized for **Google Cloud Run** (`gcloud run deploy`).
- **Endpoints:**
  - `POST /api/v1/analyze`: Analyzes text and returns structured risk, Canary decision, and live event stream.
  - `GET /health` / `GET /api/v1/health`: Health check probes for Cloud Run.
  - `GET /`: Serves the Guardian Visualizer UI.

### 4. Guardian Visualizer UI (Industrial Brutalism & Emil Design Engineering)
- **Location:** [`frontend/visualizer/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/frontend/visualizer/)
- **Design System:** Industrial Brutalist CRT terminal (`#0A0A0A` substrate, sharp 90° corners, `JetBrains Mono` typography) combined with Emil Kowalski's micro-interactions (`scale(0.97)` press feedback, `@starting-style` smooth enter transitions).
- **Features:** Live event stream log, signals telemetry matrix, risk reasons, preset scenario buttons, and protected user warning overlay (`POSIBLE ESTAFA`).

### 5. Synthetic Scenarios & Testing Suite
- **Scenarios:** [`scenarios/bank_otp_scam.json`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/bank_otp_scam.json) & [`scenarios/legitimate_call.json`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/legitimate_call.json)
- **CLI Runner:** [`scenarios/runner.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/scenarios/runner.py)
- **Test Suite:** [`tests/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/tests/) — 30 unit & integration tests covering signals, risk engine, canary policy, ADK agent, fail-safe pipeline, and FastAPI HTTP endpoints.

### 6. Guardian 360 Architectural Spec (Omnichannel Expansion)
- **Specification:** [`docs/specs/2026-08-20-guardian-360-design.md`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/specs/2026-08-20-guardian-360-design.md)
- **Roadmap:** Multi-agent ADK pipeline introducing `vision_ocr_agent` (`gemini-3.5-flash` multimodal) for OCR & visual forgery analysis of chat screenshots and fake bank receipts.

---

## Canonical Execution Path

```text
INPUT (Text / Screenshot / Call)
    │
    ▼
GOOGLE ADK AGENT (gemini-3.5-flash)
    │  Emits SIGNAL_DETECTED
    ▼
DETERMINISTIC RISK ENGINE
    │  Emits RISK_UPDATED
    ▼
CANARY POLICY GUARDRAIL
    │  Emits CANARY_EVALUATION
    ├── WARN USER (Headline & Directives)
    ├── NOTIFY TRUSTED CIRCLE (Critical Risk)
    └── EVENT STREAM (Visualizer & Logs)
```

---

## Quickstart Guide

### 1. Installation
```bash
# Clone repository and navigate to folder
git clone https://github.com/evilgreen94/Guardian_call.git
cd Guardian_call
git checkout lab/splurtch-dev-antigravity

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
Create a `.env` file in the root directory (documented in `.env.example`):
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
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
│   │   ├── actions.py       # Authorized intervention execution
│   │   ├── agent.py         # Google ADK LlmAgent (gemini-3.5-flash)
│   │   ├── canary.py        # Canary Policy Engine & authority guardrails
│   │   ├── events.py        # Domain event definitions & InMemoryEventSink
│   │   ├── models.py        # Domain data models (ScamSignals, RiskAssessment, etc.)
│   │   ├── pipeline.py      # GuardianPipeline coordinator & process_text() entrypoint
│   │   ├── risk.py          # Deterministic explainable Risk Engine
│   │   └── signals.py       # ScamSignals constructor & helper functions
│   └── server.py            # FastAPI server for Google Cloud Run
├── frontend/
│   └── visualizer/          # Industrial Brutalist Visualizer UI (HTML, CSS, JS)
├── scenarios/
│   ├── bank_otp_scam.json   # Synthetic bank OTP scam transcript
│   ├── legitimate_call.json # Synthetic benign appointment transcript
│   └── runner.py            # CLI scenario evaluator
├── tests/                   # 30 unit & integration tests (pytest)
├── docs/
│   ├── ADR-001-gemini-signal-agent-adk.md
│   ├── ADR-002-text-pipeline-failsafe.md
│   └── specs/
│       └── 2026-08-20-guardian-360-design.md
├── Dockerfile               # Google Cloud Run container recipe
├── .dockerignore
└── requirements.txt         # Project dependencies (google-adk, fastapi, uvicorn, pytest)
```

---

## Architecture Decision Records (ADRs)

- [ADR-001: Use Google ADK for the Gemini Signal-Extraction Agent](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/ADR-001-gemini-signal-agent-adk.md)
- [ADR-002: Fail-Safe Risk Handling when Gemini Signal Extraction Fails](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/ADR-002-text-pipeline-failsafe.md)
