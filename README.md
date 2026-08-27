# Guardian Call — Agentic Phone-Scam & Omnichannel Protection System

> **"Detect the manipulation. Break the isolation. Protect the person before fraud becomes loss."**

Guardian Call is an agentic protection system built for the **All Things Agentic Hackathon 2026** (Google Agentics). It analyzes conversational text, audio, screenshots, and real-time emails in real time, detects scam manipulation tactics using a multi-agent **Google ADK** pipeline powered by **Gemini 3.5** and **ShieldGemma / Gemma Guardrail**, evaluates explainable risk, and executes interventions strictly governed by **Canary Policy Guardrails**.

---

## Current Status (Version 1.1.0 — Guardian 360, Multi-Turn Memory & ScamTrap)

Branch: **`lab/splurtch-dev-antigravity`**  
Test Suite: **78 / 78 tests passing (`pytest`)**

```text
                                INCOMING USER INPUT STREAM
                  (Text / Screenshot / Real-Time IMAP Inbox Polling)
                                        │
           ┌────────────────────────────┼───────────────────────────┐
           ▼                            ▼                           ▼
     [Text Input]             [Image / Screenshot]         [Real-Time IMAP Inbox]
           │                            │                 (email_listener.py)
           │                   Google ADK Agent #1                  │
           │                (vision_ocr_agent)                  Parses MIME
           │                   model: gemini-3.5-flash        Headers, Sender & Body
           │                            │                           │
           └────────────────────┬───────┴───────────────────────────┘
                                ▼
                     MULTI-TURN SESSION MEMORY
                         (session.py)
                 [Accumulated Transcript Retention]
                                │
                                ▼
                     GEMMA / SHIELDGEMMA GUARDRAIL
                        (gemma_guardrail.py)
                [Pre-execution Prompt Injection Defense]
                                │
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
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
[If Risk is CRITICAL]                       [If Risk is HIGH/CRITICAL]
TRUSTED CIRCLE NOTIFICATION                   SCAMTRAP COUNTER-DECEPTION
 (trusted_circle.py)                              (scamtrap.py)
Emits TRUSTED_CONTACT_NOTIFIED               Generates Stalling Response
```

---

## Key Implemented Components

### 1. Multi-Turn Session Memory (`session.py`)
- **Module:** [`backend/guardian/session.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/session.py)
- **Features:** Retains full call transcript state across turns per `session_id`. Preserves conversational context for Gemini signal extraction while enforcing a periodic 5-turn forced escalation safety net.

### 2. Gemma / ShieldGemma Guardrail (`gemma_guardrail.py`)
- **Module:** [`backend/guardian/gemma_guardrail.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/gemma_guardrail.py)
- **Features:** Edge / on-device safety layer evaluating incoming text before executing model calls. Detects direct prompt injections, fake security mode triggers, persona hijacking, indirect injections, special token forgery, payload obfuscation, and credential exfiltration.

### 3. Google ADK Multi-Agent Pipeline (`google-adk`)
- **Signal Extraction Agent:** [`backend/guardian/agent.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/agent.py) — `LlmAgent` using `gemini-3.5-flash` with Pydantic output schema (`ScamSignalsSchema`). Extracted signals: `identity_claim`, `financial_context`, `urgency`, `service_cancellation_threat`, `subscription_fee_claim`, `unverified_link_prompt`, `sender_email`, `suspicious_domain`, `special_offer_hook`, `countdown_timer`, etc.
- **Multimodal Vision/OCR Agent (Guardian 360):** [`backend/guardian/vision_agent.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/vision_agent.py) — `LlmAgent` using `gemini-3.5-flash` Multimodal. Performs multilingual OCR, detects visual forgery, cloud storage threats, sender email headers, countdown timers, and discount offer hooks with single-pass SSE event deduplication.

### 4. Deterministic Risk Engine & Canary Policy Guardrails
- **Risk Engine:** [`backend/guardian/risk.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/risk.py) — Computes transparent, explainable risk levels (`NORMAL`, `SUSPICIOUS`, `HIGH`, `CRITICAL`) from contributing signals. Features expanded OTP action variants (`share_otp`, `share_code`, `reveal_otp`, `provide_code`, `dar_codigo`, `share_credentials`) while classifying legitimate in-app entry as normal.
- **Canary Policy Engine:** [`backend/guardian/canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/canary.py) — Authority layer enforcing user autonomy and strict privacy rules (`warn_user` -> `ALLOW` on `HIGH`/`CRITICAL`, `notify_trusted_circle` -> `ALLOW` on `CRITICAL`, `activate_scamtrap` -> `ALLOW` on `HIGH`/`CRITICAL`).
- **Trusted Circle Notifier:** [`backend/guardian/trusted_circle.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/trusted_circle.py) — Dispatches privacy-preserving notifications (webhook/SMS) under `CRITICAL` risk without transmitting raw conversation transcripts.

### 5. ScamTrap Counter-Deception Honey Agent (`scamtrap.py`)
- **Module:** [`backend/guardian/scamtrap.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/scamtrap.py)
- **Features:** Autonomous counter-deception module activated under `HIGH`/`CRITICAL` risk. Generates tactical stalling responses to waste scammer time while parsing threat intelligence (phishing URLs, IBANs, phone numbers) with resilient JSON extraction.

### 6. Real-Time IMAP Email Protection (`email_listener.py`)
- **Module:** [`backend/guardian/email_listener.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/email_listener.py)
- **Features:** Connects via SSL IMAP to Gmail, Outlook, or custom mail servers (`IMAP_SERVER`, `IMAP_USER`, `IMAP_PASSWORD`). Polls unseen emails, parses MIME structures (headers, spoofed sender domains, subject, plain/HTML text), formats full email context, and runs it through `GuardianPipeline`.

### 7. Google Cloud Run Backend Server & Real-Time Telemetry Stream
- **File:** [`backend/server.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/server.py)
- **Containerization:** [`Dockerfile`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/Dockerfile) & [`.dockerignore`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/.dockerignore) optimized for **Google Cloud Run**.
- **Performance & Security:** Async disk I/O for audit logs (`data/audit_log.jsonl`), W3C compliant CORS configuration, and real-time Server-Sent Events (SSE) stream (`GET /api/v1/events/stream`).
- **Endpoints:** `POST /api/v1/analyze`, `POST /api/v1/events/publish`, `GET /api/v1/events/recent`, `GET /api/v1/events/stream`, `POST /api/v1/guardrail/evaluate`, `POST /api/v1/scan-inbox`, `GET /api/v1/scenarios`, `GET /health`, `GET /`.

### 8. Guardian Visualizer UI (Industrial Brutalism & Emil Design Engineering)
- **Location:** [`frontend/visualizer/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/frontend/visualizer/)
- **Design:** Industrial CRT layout (`#0A0A0A` substrate, `JetBrains Mono` font), Drag & Drop upload zone, live SSE telemetry matrix, scenario loader (57+ adversarial benchmarks), and warning overlay.

### 9. Test Suite & Scenarios
- **Test Suite:** [`tests/`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/tests/) — **78 unit & integration tests passing** (`pytest`).

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

# Real-Time Email Protection Credentials (IMAP)
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your_email@gmail.com
IMAP_PASSWORD=your_app_password
```

### 3. Run Automated Tests
```bash
pytest
```

### 4. Run Real-Time IMAP Email Protection Listener
```bash
python backend/guardian/email_listener.py
```

### 5. Run Local Backend & Guardian Visualizer UI
```bash
python backend/server.py
```
Open **[http://localhost:8080/](http://localhost:8080/)** in your web browser.

---

## Repository Structure

```text
Guardian_call/
├── backend/
│   ├── guardian/
│   │   ├── actions.py          # Authorized intervention execution
│   │   ├── agent.py            # Google ADK LlmAgent for text signals (gemini-3.5-flash)
│   │   ├── canary.py           # Canary Policy Engine & authority guardrails
│   │   ├── email_listener.py   # Real-Time IMAP Email Protection Connector
│   │   ├── events.py           # Domain event definitions & InMemoryEventSink
│   │   ├── gemma_guardrail.py  # Gemma / ShieldGemma edge safety & prompt injection defense
│   │   ├── models.py           # Domain data models (ScamSignals, RiskAssessment, etc.)
│   │   ├── pipeline.py         # GuardianPipeline coordinator
│   │   ├── risk.py             # Deterministic explainable Risk Engine
│   │   ├── scamtrap.py         # ScamTrap counter-deception honey agent & threat extraction
│   │   ├── session.py          # Multi-turn call session transcript memory store
   │   ├── signals.py          # ScamSignals constructor & heuristic keyword gate
│   │   ├── trusted_circle.py   # Trusted Circle notification client (SMS/Webhook)
│   │   └── vision_agent.py     # Google ADK Multimodal Vision/OCR LlmAgent (gemini-3.5-flash)
│   └── server.py               # FastAPI server for Google Cloud Run
├── frontend/
│   └── visualizer/             # Industrial Brutalist Visualizer UI
├── scenarios/                  # Synthetic scenarios & 57 adversarial benchmarks
├── tests/                      # 78 unit & integration tests (pytest)
├── Dockerfile                  # Google Cloud Run container recipe
└── requirements.txt            # Project dependencies
```
