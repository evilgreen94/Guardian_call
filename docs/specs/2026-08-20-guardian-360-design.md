# Guardian 360 — Multi-Agent & Multimodal Architecture Design

**Document ID:** `2026-08-20-guardian-360-design`  
**Status:** Approved by Human Partner  
**Target Milestone:** Guardian 360 (Phase M1.5 - Multi-Channel Expansion)

---

## 1. Overview & Vision

Guardian 360 expands the Guardian Call system from a single-channel conversation protector into an **omnichannel agentic protection ecosystem**. It safeguards users against phone scams, chat manipulation, fake bank receipts, phishing emails, and malicious URLs.

### Architectural Principle
> **"Gemini understands (multimodal & text agents); Risk Engine evaluates; Canary authorizes."**

Security and authority remain strictly deterministic and un-hackable via Canary Policy Guardrails, while perception and intelligence are powered by specialized **Google ADK LLM Agents**.

---

## 2. Multi-Channel Priority Hierarchy

1. **Priority 1 (Immediate): Screenshots & Images / OCR**
   - Analysis of chat screenshots, SMS message captures, fake wire transfer receipts, and technical support popups using Gemini 3.5 Multimodal capabilities.
2. **Priority 2: Email & Phishing / BEC**
   - Detection of Business Email Compromise (BEC), corporate impersonation, and fraudulent email bodies/headers.
3. **Priority 3: Web URLs & Phishing Domain Analyzer**
   - Inspection of malicious links and credential harvesting landing pages.

---

## 3. Google ADK Multi-Agent Architecture (Option B)

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
```

### Specialized Agents

#### Agent 1: `vision_ocr_agent` (`backend/guardian/vision_agent.py`)
- **Framework:** `google.adk.agents.LlmAgent`
- **Model:** `gemini-3.5-flash` (Multimodal)
- **Output Schema (`VisionOcrResult` Pydantic model):**
  - `extracted_text: str`: Full OCR text transcript extracted from image.
  - `visual_manipulation_suspected: bool`: Flag indicating font misalignment, photo editing, or fake receipt layout anomalies.
  - `channel_detected: str`: `chat_screenshot` | `bank_receipt` | `sms_screenshot` | `email_screenshot` | `document`.
  - `key_visual_elements: List[str]`: List of recognized logos, account numbers, or badges.

#### Agent 2: `signal_extraction_agent` (`backend/guardian/agent.py`)
- **Framework:** `google.adk.agents.LlmAgent`
- **Model:** `gemini-3.5-flash`
- **Output Schema (`ScamSignalsSchema` Pydantic model):**
  - 10 core fields (`identity_claim`, `identity_verified`, `financial_context`, `urgency`, `secrecy_request`, `otp_request`, `password_request`, `transfer_request`, `remote_access_request`, `requested_action`).

---

## 4. Domain Events & Privacy Standards

### Privacy Rules
- **Rule 1:** `IMAGE_RECEIVED` payload contains only `image_size_bytes` and `mime_type`. Raw image bytes or base64 data are **never logged or stored** in the event trail.
- **Rule 2:** `INPUT_RECEIVED` payload contains only `text_length`. Raw conversational transcript is **never logged** in the event trail.

### Canonical Event Sequence for Multimodal Input
1. `IMAGE_RECEIVED` -> `{"image_size_bytes": 45120, "mime_type": "image/png"}`
2. `IMAGE_PROCESSED_OCR` -> `{"extracted_text_length": 210, "visual_manipulation_suspected": false, "channel_detected": "bank_receipt"}`
3. `SIGNAL_DETECTED` -> `{"signals": {...}}`
4. `RISK_UPDATED` -> `{"level": "CRITICAL", "reasons": [...]}`
5. `CANARY_EVALUATION` -> `{"action": "warn_user", "decision": "ALLOW"}`
6. `ACTION_ALLOWED` -> `{"action": "warn_user"}`
7. `USER_WARNING` -> `{"headline": "POSIBLE ESTAFA", "directives": [...]}`

---

## 5. Security & Authority: Canary Policy Guardrail

Canary remains a **deterministic Python policy engine** (`canary.py`) and is **never** implemented as an LLM agent:
- Prevents **Prompt Injection** attacks (a scammer cannot override policies by telling the system to ignore safety rules).
- Guarantees 100% explainability and non-negotiable privacy boundaries (`share_transcript` -> `DENY`, `end_call` -> `ASK_USER`).
