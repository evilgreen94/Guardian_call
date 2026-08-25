# Multimodal Scam Detection & Microphone Diagnostic Suite — Design Specification

**Date:** 2026-08-25  
**System:** Guardian Call M0.5  
**Author:** Antigravity AI & Engineering Team  
**Status:** Approved  

---

## 1. Executive Summary

Guardian 360 includes multimodal image inspection (screenshots of chat, email, bank receipts) and real-time live microphone speech-to-text telemetry.  
In real-world testing with phishing email screenshots containing storage deletion threats in English (*"Your Account Has Been Blocked! Your Photos and Videos will be Removed"*, spoofed domain `jg4kqzs3v@emqh1r9s5u.us...importican.de`), the system evaluated the input as `RISK LEVEL: NORMAL` (`PASS // CLEAN`). Furthermore, WebSpeech API microphone capture silently failed when browser permissions were blocked without user feedback.

This specification details the architecture for:
1. Enhancing the Google ADK Vision Agent (`vision_agent.py`) with spoofed domain detection, spam banner recognition, and cloud deletion threat parsing.
2. Expanding the signal extraction vocabulary (`signals.py`) with bilingual (Spanish + English) phishing keywords.
3. Adding explicit deterministic risk rules in `RiskEngine` (`risk.py`) for cloud cancellation and payment decline threats.
4. Adding robust fallback logic in `vision_agent.py` to prevent silent `NORMAL` evaluation on vision/OCR API exceptions.
5. Implementing interactive WebSpeech API permission diagnostics and error indicators in `app.js`.

---

## 2. Component Design & Specification

### 2.1 Google ADK Multimodal Vision Agent (`backend/guardian/vision_agent.py`)

#### Prompt & Instruction Enhancements
The system prompt `_VISION_AGENT_INSTRUCTION` for `vision_ocr_agent` (`gemini-3.5-flash`) is updated to inspect:
- **Spoofed & DGA Domains:** Flag sender email addresses or headers with multiple subdomains, random hash strings, or non-standard TLD stacks (e.g. `.neuralgrid.org.importican.de`).
- **Email Client Spam Banners:** Detect native email client banners (e.g. Gmail's *"Why is this message in Spam?"* or *"¿Por qué está en Spam este mensaje?"*).
- **Cloud Account & Data Loss Threats:** Extract text such as *"Photos and Videos will be Removed"*, *"Account Has Been Blocked"*, *"Storage Full (99.9%)"*, *"Payment-Declined"*.
- **Urgency & Bonus Hooks:** Extract timer phrases (*"expires in 4 minutes et 39 seconds"*) and bonus space claims (*"extra 50 GB bonus storage"*).

#### Robust Exception Fallback
`process_image()` currently catches `Exception` and returns an empty `VisionOcrResult()`.  
*New Behavior:* If an exception occurs during ADK execution (e.g., rate limits, API timeout), `process_image()` attempts regex-based text extraction over the raw bytes or flags `visual_manipulation_suspected=True` so `pipeline.py` marks `extraction_failed` / `HIGH` fail-safe risk instead of silent `NORMAL`.

---

### 2.2 Bilingual Signal Extraction & Risk Engine (`backend/guardian/signals.py` & `backend/guardian/risk.py`)

#### Bilingual Keyword Lists (`signals.py`)
Extend existing tuples with English phishing patterns:
- `_URGENCY_KEYWORDS`: Add `"photos and videos will be removed"`, `"account has been blocked"`, `"your account has been blocked"`, `"account blocked"`, `"take action"`, `"don't wait"`, `"expires in"`, `"urgent"`.
- `_FINANCIAL_KEYWORDS`: Add `"payment-declined"`, `"payment declined"`, `"50 gb bonus"`, `"extra 50 gb"`, `"bonus storage"`, `"subscription fee"`.
- `_SERVICE_THREAT_KEYWORDS`: Add `"photos and videos will be removed"`, `"storage full"`, `"account blocked"`, `"lost photos"`, `"data loss"`, `"will be removed"`.
- `_SUBSCRIPTION_KEYWORDS`: Add `"payment-declined"`, `"payment declined"`, `"unpaid invoice"`.
- `_LINK_KEYWORDS`: Add `"update now"`, `"click to update"`, `"upgrade now"`.
- `_DOMAIN_KEYWORDS`: Add `"importican"`, `"neuralgrid"`, `"vectorization"`, `"travis.de"`.
- `_OFFER_KEYWORDS`: Add `"50 gb bonus"`, `"extra 50 gb"`, `"bonus storage"`.
- `_TRIGGER_KEYWORDS`: Add `"photos and videos will be removed"`, `"payment-declined"`, `"account has been blocked"`, `"storage full"`.

#### Deterministic Risk Engine Rule (`risk.py`)
In `RiskEngine.evaluate()`:
- When `signals.service_cancellation_threat` or `signals.subscription_fee_claim` is combined with `signals.suspicious_domain`, `signals.urgency`, or `signals.unverified_link_prompt`, the level evaluates to **`RiskLevel.CRITICAL`** (or `HIGH` if no urgency).
- Reason added: *"Amenaza de cancelación de cuenta/almacenamiento con dominio sospechoso o temporizador de urgencia detectado"*.

---

### 2.3 Visualizer WebSpeech Microphone Diagnostics (`frontend/visualizer/app.js`)

#### Interactive Error Diagnostics
In `app.js`:
- Catch `recognition.onerror` events:
  - `not-allowed` / `permission-denied`: Update `#mic-status` to `"MIC: PERMISO DENEGADO EN NAVEGADOR"` (red text) and render alert bar asking the user to click the browser lock icon to enable microphone access.
  - `no-speech`: Keep listening without resetting state.
  - `audio-capture`: Update `#mic-status` to `"MIC: DISPOSITIVO DE AUDIO NO ENCONTRADO"`.
- Add auto-reconnect attempt on `recognition.onend` while `isListening === true`.

---

## 3. Verification & Testing Plan

### Automated Unit & Integration Tests
1. **`tests/test_vision_agent.py`:** Test that a synthetic phishing email screenshot payload correctly extracts `sender_email`, `suspicious_domain_detected=True`, `special_offer_detected=True`, and `service_cancellation_threat`.
2. **`tests/test_risk_engine.py`:** Verify that bilingual cloud storage threats with spoofed domains evaluate to `RiskLevel.CRITICAL`.
3. **`tests/test_server.py`:** Verify `POST /api/v1/analyze-image` returns `CRITICAL` risk and authorized Canary warning for the phishing email screenshot.

### Manual Verification
- Upload the user's phishing email screenshot (`media_1787673939649.jpg`) to the visualizer UI and confirm that the dashboard renders `RISK LEVEL: CRITICAL` / `WARN USER` / `SCAMTRAP ACTIVE`.
- Test microphone activation in Chrome/Edge, verify permission error banner rendering if blocked.
