# Multimodal Scam Detection & Microphone Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance Guardian 360 to accurately identify English and Spanish email phishing screenshots (e.g. cloud storage deletion threats with spoofed DGA domains) and render interactive WebSpeech API microphone diagnostic feedback in the visualizer UI.

**Architecture:** 
Extend the Google ADK Multimodal Vision Agent (`vision_ocr_agent` in `vision_agent.py`) prompt instructions for spoofed domains, spam banners, and cloud threats. Expand the signal extraction keyword dictionaries in `signals.py` with bilingual (Spanish + English) phishing vocabulary. Update `RiskEngine` in `risk.py` with explicit rules for cloud cancellation threats. Strengthen `vision_agent.py` exception handling so vision API timeouts trigger fail-safe `HIGH` risk. Enhance `app.js` with interactive microphone permission error banners.

**Tech Stack:** Python 3.14, FastAPI, Google ADK (`google-adk`), Google GenAI (`google-genai`), Pytest, WebSpeech API, Vanilla JavaScript, HTML5/CSS3.

**Spec:** [`docs/superpowers/specs/2026-08-25-multimodal-scam-detection-design.md`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/superpowers/specs/2026-08-25-multimodal-scam-detection-design.md)

## Global Constraints

- **Language Support:** Bilingual support for Spanish (`es-ES`) and English (`en-US`).
- **Google ADK Compatibility:** Use `LlmAgent` and `types.Part.from_bytes` for multimodal vision.
- **Fail-Safe Privacy & Security:** Vision exceptions must trigger fail-safe `HIGH` risk instead of silent `NORMAL` pass.
- **Test Coverage:** All unit and integration tests must pass cleanly (`pytest`).

---

### Task 1: Bilingual Keyword Vocabulary & Risk Engine Rules

**Files:**
- Modify: `backend/guardian/signals.py`
- Modify: `backend/guardian/risk.py`
- Test: `tests/test_signals.py`
- Test: `tests/test_risk_engine.py`

**Interfaces:**
- Consumes: Raw extracted OCR text string.
- Produces: `ScamSignals` with `service_cancellation_threat`, `suspicious_domain`, `urgency`, `unverified_link_prompt`, and `RiskAssessment(level=CRITICAL)`.

- [ ] **Step 1: Write failing test in `tests/test_signals.py` and `tests/test_risk_engine.py`**

```python
def test_bilingual_cloud_storage_phishing_keywords():
    from guardian.signals import text_keyword_flags
    text = "ALERTA: Your Account Has Been Blocked! Your Photos and Videos will be Removed. 50 GB bonus storage. Expires in 4 minutes."
    flags = text_keyword_flags(text)
    assert flags["service_cancellation_threat"] is True
    assert flags["urgency"] is True
    assert flags["special_offer_hook"] is True

def test_cloud_storage_threat_with_spoofed_domain_triggers_critical_risk():
    from guardian.signals import create_signals
    from guardian.risk import RiskEngine
    from guardian.models import RiskLevel
    
    signals = create_signals(
        identity_claim="cloud_storage",
        service_cancellation_threat=True,
        suspicious_domain=True,
        urgency=True,
    )
    engine = RiskEngine()
    assessment = engine.evaluate(signals)
    assert assessment.level == RiskLevel.CRITICAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signals.py tests/test_risk_engine.py -k "bilingual or cloud_storage_threat"`
Expected: FAIL due to missing keywords / risk engine rules.

- [ ] **Step 3: Update `backend/guardian/signals.py` and `backend/guardian/risk.py`**

In `backend/guardian/signals.py`, add English keywords to `_URGENCY_KEYWORDS`, `_FINANCIAL_KEYWORDS`, `_SERVICE_THREAT_KEYWORDS`, `_SUBSCRIPTION_KEYWORDS`, `_LINK_KEYWORDS`, `_DOMAIN_KEYWORDS`, `_OFFER_KEYWORDS`, `_TRIGGER_KEYWORDS`.

In `backend/guardian/risk.py`, add explicit rule in `RiskEngine.evaluate()`:
```python
elif signals.service_cancellation_threat and (signals.suspicious_domain or signals.urgency or signals.unverified_link_prompt):
    level = RiskLevel.CRITICAL
    reasons.insert(0, "Amenaza de cancelación de servicio o pérdida de almacenamiento con dominio sospechoso o temporizador de urgencia")
    contributing.extend(["service_cancellation_threat", "suspicious_domain", "urgency"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signals.py tests/test_risk_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guardian/signals.py backend/guardian/risk.py tests/test_signals.py tests/test_risk_engine.py
git commit -m "feat(signals): add bilingual phishing vocabulary and cloud cancellation threat risk rules"
```

---

### Task 2: Google ADK Vision Agent Instruction & Fallback Hardening

**Files:**
- Modify: `backend/guardian/vision_agent.py`
- Modify: `backend/guardian/pipeline.py`
- Test: `tests/test_vision_agent.py`

**Interfaces:**
- Consumes: Image bytes (`image/png`, `image/jpeg`).
- Produces: `VisionOcrResult` with `extracted_text`, `suspicious_domain_detected`, `channel_detected`, and fail-safe handling in `pipeline.py`.

- [ ] **Step 1: Write failing test in `tests/test_vision_agent.py`**

```python
def test_vision_agent_spoofed_domain_and_spam_banner_instruction():
    from guardian.vision_agent import VisionOcrResultSchema
    data = {
        "extracted_text": "Your Account Has Been Blocked! Photos and Videos will be Removed. jg4kqzs3v@emqh1r9s5u.us.a.travis.de.vectorization.importican.de",
        "sender_email": "jg4kqzs3v@emqh1r9s5u.us",
        "sender_domain": "importican.de",
        "suspicious_domain_detected": True,
        "special_offer_detected": True,
        "countdown_timer_detected": True,
        "visual_manipulation_suspected": True,
        "channel_detected": "email_screenshot",
        "key_visual_elements": ["spam_warning_banner", "storage_full_alert", "spoofed_sender_address"],
    }
    schema = VisionOcrResultSchema(**data)
    assert schema.suspicious_domain_detected is True
    assert schema.channel_detected == "email_screenshot"
    assert "spam_warning_banner" in schema.key_visual_elements
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vision_agent.py -k test_vision_agent_spoofed_domain`
Expected: PASS/FAIL depending on schema fields.

- [ ] **Step 3: Update `backend/guardian/vision_agent.py` & `backend/guardian/pipeline.py`**

In `backend/guardian/vision_agent.py`:
Update `_VISION_AGENT_INSTRUCTION` to explicitly guide Gemini 3.5 on inspecting email sender addresses for multi-subdomain DGA patterns, email client spam warning banners, data loss threats, and urgency expiration timers.

In `process_image()` in `vision_agent.py`:
In the exception block, if an error occurs, extract any readable ASCII/UTF-8 strings from raw bytes or set `visual_manipulation_suspected=True` so `pipeline.py` marks fail-safe `HIGH` risk.

In `backend/guardian/pipeline.py`:
Ensure `process_image()` merges `ocr_result` flags (including `sender_email`, `suspicious_domain_detected`, `special_offer_detected`, `countdown_timer_detected`) into `merged_signals` even if text keyword matching didn't trigger escalate.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vision_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guardian/vision_agent.py backend/guardian/pipeline.py tests/test_vision_agent.py
git commit -m "feat(vision): enhance vision agent instruction for spoofed domains and cloud threats with fail-safe error handling"
```

---

### Task 3: Visualizer WebSpeech Microphone Error Diagnostics

**Files:**
- Modify: `frontend/visualizer/app.js`
- Modify: `frontend/visualizer/styles.css`
- Modify: `frontend/visualizer/index.html`

**Interfaces:**
- Consumes: Browser WebSpeech API error events (`onerror`).
- Produces: Visual warning banner in CRT live stream box when microphone access is blocked.

- [ ] **Step 1: Add mic diagnostic alert styles in `frontend/visualizer/styles.css`**

Add CSS for `.mic-error-banner`:
```css
.mic-error-banner {
  background-color: rgba(255, 0, 85, 0.2);
  border: 1px solid var(--hazard-red);
  color: #ffffff;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 700;
  margin-top: 8px;
}
```

- [ ] **Step 2: Update `frontend/visualizer/app.js` microphone error handler**

In `app.js`:
In `recognition.onerror`, handle `not-allowed`, `permission-denied`, and `audio-capture`:
```javascript
recognition.onerror = (evt) => {
  console.warn('Speech Recognition Error:', evt.error);
  if (evt.error === 'not-allowed' || evt.error === 'service-not-allowed') {
    if (micStatus) {
      micStatus.textContent = 'MIC: PERMISO DENEGADO EN NAVEGADOR';
      micStatus.style.color = 'var(--hazard-red)';
    }
    const liveBox = document.getElementById('live-transcription-box');
    const liveContent = document.getElementById('live-transcription-content');
    if (liveBox && liveContent) {
      liveBox.style.display = 'block';
      liveContent.innerHTML = `<div class="mic-error-banner">⚠️ ACCESO AL MICRÓFONO DENEGADO EN EL NAVEGADOR.<br>Haz clic en el icono del candado 🔒 en la barra de direcciones de tu navegador y selecciona "Permitir" para el micrófono.</div>`;
    }
  }
};
```

- [ ] **Step 3: Test full suite and static files**

Run: `pytest -v`
Expected: 73+ PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/visualizer/app.js frontend/visualizer/styles.css frontend/visualizer/index.html
git commit -m "feat(visualizer): add WebSpeech microphone permission diagnostics and UI warning banner"
```
