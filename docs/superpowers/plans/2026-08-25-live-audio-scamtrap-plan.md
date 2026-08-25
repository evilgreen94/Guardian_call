# Live Audio Protection & ScamTrap Counter-Deception Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement real-time live audio speech capture with a live CRT transcription stream box, and build the ScamTrap autonomous counter-deception honey-agent with threat intelligence extraction.

**Architecture:** Extend Google ADK with a new `scamtrap_counter_agent` (`LlmAgent` using `gemini-3.5-flash`), add `ActionType.ACTIVATE_SCAMTRAP` and domain events (`SCAMTRAP_ACTIVATED`, `INTELLIGENCE_EXTRACTED`) in the backend, and add `webkitSpeechRecognition` continuous audio listener with a real-time transcription box and ScamTrap threat matrix in the Guardian Visualizer UI.

**Tech Stack:** Python 3.14, Google ADK (`google-adk`), Gemini 3.5 Flash (`google-genai`), FastAPI, Pytest, Vanilla JS / HTML5 WebSpeech API / CSS CRT.

**Spec:** [`docs/superpowers/specs/2026-08-25-live-audio-scamtrap-design.md`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/docs/superpowers/specs/2026-08-25-live-audio-scamtrap-design.md)

## Global Constraints

- **Python Version:** Python 3.14+ compatible
- **Framework:** `google-adk` (`LlmAgent`, `Runner`, `InMemorySessionService`)
- **Model:** `gemini-3.5-flash`
- **Testing:** `pytest` test suite must remain 100% green at all times
- **UI Theme:** Industrial CRT Brutalism (`#0A0A0A`, `JetBrains Mono`, `Space Grotesk`)

---

### Task 1: ScamTrap Models, Events, and Canary Policy Extensions

**Files:**
- Modify: [`backend/guardian/models.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/models.py)
- Modify: [`backend/guardian/events.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/events.py)
- Modify: [`backend/guardian/canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/backend/guardian/canary.py)
- Test: [`tests/test_canary.py`](file:///d:/SYNJI%20ARCHIVOS/PROYECTOS/CANARY/Guardian_call-main/tests/test_canary.py)

**Interfaces:**
- Consumes: Existing `ActionType`, `EventType`, `CanaryPolicy`
- Produces: `ActionType.ACTIVATE_SCAMTRAP`, `EventType.SCAMTRAP_ACTIVATED`, `EventType.INTELLIGENCE_EXTRACTED`, `CanaryPolicy.evaluate_action` support for `ACTIVATE_SCAMTRAP`.

- [ ] **Step 1: Write the failing test for Canary Policy ACTIVATE_SCAMTRAP**

Add to `tests/test_canary.py`:
```python
def test_activate_scamtrap_policy_requires_high_or_critical_risk(self) -> None:
    from guardian.models import ActionType, PolicyDecision, RiskAssessment, RiskLevel
    from guardian.canary import CanaryPolicy

    policy = CanaryPolicy()
    normal_risk = RiskAssessment(level=RiskLevel.NORMAL, score=0.0)
    high_risk = RiskAssessment(level=RiskLevel.HIGH, score=0.8)
    critical_risk = RiskAssessment(level=RiskLevel.CRITICAL, score=0.95)

    assert policy.evaluate_action(normal_risk, ActionType.ACTIVATE_SCAMTRAP).decision == PolicyDecision.DENY
    assert policy.evaluate_action(high_risk, ActionType.ACTIVATE_SCAMTRAP).decision == PolicyDecision.ALLOW
    assert policy.evaluate_action(critical_risk, ActionType.ACTIVATE_SCAMTRAP).decision == PolicyDecision.ALLOW
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_canary.py -k test_activate_scamtrap_policy_requires_high_or_critical_risk`  
Expected: FAIL with `AttributeError: 'ActionType' has no attribute 'ACTIVATE_SCAMTRAP'`

- [ ] **Step 3: Update `models.py`, `events.py`, and `canary.py`**

In `backend/guardian/models.py`:
```python
class ActionType(str, Enum):
    WARN_USER = "warn_user"
    RECOMMEND_END_CALL = "recommend_end_call"
    NOTIFY_TRUSTED_CIRCLE = "notify_trusted_circle"
    SHARE_TRANSCRIPT = "share_transcript"
    ACTIVATE_SCAMTRAP = "activate_scamtrap"
```

In `backend/guardian/events.py`:
```python
class EventType(str, Enum):
    ...
    SCAMTRAP_ACTIVATED = "scamtrap_activated"
    INTELLIGENCE_EXTRACTED = "intelligence_extracted"
```

In `backend/guardian/canary.py`:
Add rule for `ActionType.ACTIVATE_SCAMTRAP`:
```python
if action == ActionType.ACTIVATE_SCAMTRAP:
    if risk_assessment.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        return CanaryDecision(
            decision=PolicyDecision.ALLOW,
            action=action,
            reason=f"ScamTrap counter-deception authorized under {risk_assessment.level.value} risk.",
        )
    return CanaryDecision(
        decision=PolicyDecision.DENY,
        action=action,
        reason=f"ScamTrap counter-deception requires HIGH or CRITICAL risk (current: {risk_assessment.level.value}).",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_canary.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guardian/models.py backend/guardian/events.py backend/guardian/canary.py tests/test_canary.py
git commit -m "feat(scamtrap): add ACTIVATE_SCAMTRAP action, events, and Canary policy rules"
```

---

### Task 2: Google ADK ScamTrap Counter-Deception Agent (`scamtrap.py`)

**Files:**
- Create: `backend/guardian/scamtrap.py`
- Test: `tests/test_scamtrap.py`

**Interfaces:**
- Consumes: `google.adk.agents.LlmAgent`, `google.adk.runners.Runner`, `pydantic.BaseModel`
- Produces: `ScamTrapIntelligenceSchema`, `scamtrap_counter_agent`, `run_scamtrap_agent(text) -> ScamTrapIntelligence`

- [ ] **Step 1: Write failing unit test for `scamtrap.py`**

Create `tests/test_scamtrap.py`:
```python
import pytest
from backend.guardian.scamtrap import ScamTrapIntelligenceSchema, run_scamtrap_agent

def test_scamtrap_intelligence_schema_validation():
    data = {
        "stalling_response": "Espere un momento, estoy buscando las gafas...",
        "extracted_phishing_urls": ["http://banco-fake-verify.com"],
        "extracted_ibans": ["ES9121000418450200051234"],
        "extracted_phone_numbers": ["+34600112233"],
        "scammer_tactics_summary": "Pretends to be bank tech support asking for urgent IBAN verification.",
    }
    schema = ScamTrapIntelligenceSchema(**data)
    assert schema.stalling_response.startswith("Espere")
    assert "http://banco-fake-verify.com" in schema.extracted_phishing_urls
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_scamtrap.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.guardian.scamtrap'`

- [ ] **Step 3: Implement `backend/guardian/scamtrap.py`**

Create `backend/guardian/scamtrap.py`:
```python
"""ScamTrap Counter-Deception Honey-Agent powered by Google ADK and Gemini."""

from typing import List, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

class ScamTrapIntelligenceSchema(BaseModel):
    """Pydantic schema for extracted threat intelligence and stalling counter-response."""
    stalling_response: str = Field(
        ...,
        description="Tactical stalling phrase to keep scammer occupied without revealing real personal data."
    )
    extracted_phishing_urls: List[str] = Field(
        default_factory=list,
        description="Extracted phishing URLs, domain links, or websites mentioned by scammer."
    )
    extracted_ibans: List[str] = Field(
        default_factory=list,
        description="Extracted IBANs, bank account numbers, or wire destinations requested."
    )
    extracted_phone_numbers: List[str] = Field(
        default_factory=list,
        description="Extracted callback phone numbers provided by scammer."
    )
    scammer_tactics_summary: str = Field(
        default="",
        description="Brief summary of psychological tactics and persona claimed by caller."
    )

SCAMTRAP_INSTRUCTION = (
    "You are ScamTrap, an autonomous counter-deception honey-agent for Guardian Call.\n"
    "Your objective is to neutralize phone and messaging scams by:\n"
    "1. Generating a believable, innocent stalling response that keeps the scammer waiting without revealing real sensitive data (e.g. pretend to search for glasses, complain about slow app loading, ask them to repeat their agent ID).\n"
    "2. Extracting tactical threat intelligence from the transcript: phishing URLs, IBANs, bank accounts, and callback numbers.\n"
    "Respond strictly adhering to the JSON schema."
)

scamtrap_counter_agent = LlmAgent(
    name="scamtrap_counter_agent",
    model="gemini-3.5-flash",
    instruction=SCAMTRAP_INSTRUCTION,
    output_schema=ScamTrapIntelligenceSchema,
)

def run_scamtrap_agent(text: str) -> ScamTrapIntelligenceSchema:
    """Run ScamTrap agent on text and return structured intelligence."""
    import json
    from .signals import heuristic_signals_from_text

    # Heuristic fallback if API fails
    fallback_response = "Espere un momento por favor, se me ha congelado la pantalla del teléfono..."
    urls = []
    if "http" in text.lower() or ".com" in text.lower() or ".es" in text.lower():
        import re
        urls = re.findall(r'https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*', text)

    try:
        session_service = InMemorySessionService()
        session_service.create_session_sync(app_name="guardian_scamtrap", user_id="user", session_id="scamtrap_sess")
        runner = Runner(agent=scamtrap_counter_agent, session_service=session_service, app_name="guardian_scamtrap")

        new_message = types.Content(parts=[types.Part.from_text(text=text)], role="user")
        events = list(runner.run(user_id="user", session_id="scamtrap_sess", new_message=new_message))

        extracted_text = None
        for event in reversed(events):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        extracted_text = part.text
                        break
            if extracted_text:
                break

        if extracted_text:
            clean = extracted_text.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            data = json.loads(clean.strip())
            return ScamTrapIntelligenceSchema(**data)
    except Exception:
        pass

    return ScamTrapIntelligenceSchema(
        stalling_response=fallback_response,
        extracted_phishing_urls=urls,
        extracted_ibans=[],
        extracted_phone_numbers=[],
        scammer_tactics_summary="Detected high-risk scam manipulation.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scamtrap.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guardian/scamtrap.py tests/test_scamtrap.py
git commit -m "feat(scamtrap): implement Google ADK ScamTrap Counter-Deception agent"
```

---

### Task 3: Pipeline Integration & Event Emitting (`pipeline.py`)

**Files:**
- Modify: `backend/guardian/pipeline.py`
- Modify: `tests/test_events_and_pipeline.py`

**Interfaces:**
- Consumes: `scamtrap.run_scamtrap_agent`, `CanaryPolicy.evaluate_action(ActionType.ACTIVATE_SCAMTRAP)`
- Produces: Emits `SCAMTRAP_ACTIVATED` and `INTELLIGENCE_EXTRACTED` events in `GuardianPipeline._act_on_risk_assessment`.

- [ ] **Step 1: Write test for ScamTrap pipeline integration**

Add to `tests/test_events_and_pipeline.py`:
```python
def test_scamtrap_executed_under_critical_risk(self) -> None:
    from guardian.pipeline import GuardianPipeline
    from guardian.models import ScamSignals, RiskLevel, ActionType
    from guardian.events import EventType

    pipeline = GuardianPipeline()
    critical_signals = ScamSignals(
        otp_request=True,
        urgency=True,
        financial_context=True,
    )
    res = pipeline.process_signals(critical_signals)
    event_types = [e.event_type for e in res.events]
    assert EventType.SCAMTRAP_ACTIVATED in event_types
    assert EventType.INTELLIGENCE_EXTRACTED in event_types
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_events_and_pipeline.py -k test_scamtrap_executed_under_critical_risk`  
Expected: FAIL (`SCAMTRAP_ACTIVATED` not in event_types)

- [ ] **Step 3: Update `GuardianPipeline._act_on_risk_assessment` in `pipeline.py`**

In `backend/guardian/pipeline.py`:
```python
        # Evaluate and execute ACTIVATE_SCAMTRAP under Canary policy
        scamtrap_decision = self.canary_policy.evaluate_action(
            risk_assessment=risk_assessment,
            action=ActionType.ACTIVATE_SCAMTRAP,
        )
        if scamtrap_decision.decision == PolicyDecision.ALLOW:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.SCAMTRAP_ACTIVATED,
                    payload={"action": ActionType.ACTIVATE_SCAMTRAP.value, "reason": scamtrap_decision.reason},
                )
            )
            from .scamtrap import run_scamtrap_agent
            intel = run_scamtrap_agent(getattr(signals, "raw_text", "") or "High risk threat detected")
            sink.emit(
                GuardianEvent(
                    event_type=EventType.INTELLIGENCE_EXTRACTED,
                    payload=intel.model_dump(),
                )
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_events_and_pipeline.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/guardian/pipeline.py tests/test_events_and_pipeline.py
git commit -m "feat(pipeline): integrate ScamTrap counter-deception activation into GuardianPipeline"
```

---

### Task 4: Guardian Visualizer UI — Live Audio Stream Box & ScamTrap Widget (`index.html`, `styles.css`, `app.js`)

**Files:**
- Modify: `frontend/visualizer/index.html`
- Modify: `frontend/visualizer/styles.css`
- Modify: `frontend/visualizer/app.js`

**Interfaces:**
- Consumes: Browser `webkitSpeechRecognition` API, `SCAMTRAP_ACTIVATED`, `INTELLIGENCE_EXTRACTED` SSE events.
- Produces: Live transcription CRT box, audio status indicator, ScamTrap Honey-Agent Threat Countermeasure panel.

- [ ] **Step 1: Add Real-Time Live Audio Transcription Box & ScamTrap Panel to `index.html`**

In `frontend/visualizer/index.html`:
1. In `panel-input` body (under textarea), add:
```html
<div class="live-transcription-box" id="live-transcription-box" style="display: none;">
  <div class="live-transcription-header">> 🎙️ STREAM DE TRANSCRIPCIÓN DE AUDIO EN VIVO:</div>
  <div class="live-transcription-content" id="live-transcription-content">
    <span class="transcript-placeholder">[ ESPERANDO ENTRADA DE VOZ... HABLA AL MICRÓFONO ]</span>
  </div>
</div>
```

2. In right column (under status-grid), add:
```html
<div class="scamtrap-panel" id="scamtrap-panel" style="display: none;">
  <div class="scamtrap-header">[ 🍯 SCAMTRAP HONEY-AGENT // THREAT COUNTERMEASURE ]</div>
  <div class="scamtrap-body">
    <div class="stalling-box">
      <span class="stalling-label">RESPUESTA TÁCTICA SUGERIDA:</span>
      <p class="stalling-text" id="stalling-text">"Espere un momento por favor, se me ha congelado la pantalla..."</p>
      <button type="button" class="btn btn-preset" id="btn-copy-stalling">[ 📋 COPIAR RESPUESTA TÁCTICA ]</button>
    </div>
    <div class="intel-matrix">
      <span class="intel-label">INTELIGENCIA EXTRAÍDA:</span>
      <div id="intel-urls" class="intel-item">URLs: Ninguna</div>
      <div id="intel-ibans" class="intel-item">IBANs: Ninguno</div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add CSS styling to `styles.css`**

Add CRT style definitions for `.live-transcription-box` and `.scamtrap-panel` matching dark brutalist substrate (`#0A0A0A`, neon green `#22c55e`, amber `#f59e0b`).

- [ ] **Step 3: Update Speech Recognition & Event Handling in `app.js`**

In `frontend/visualizer/app.js`:
- Bind `btn-mic-toggle` to initialize `SpeechRecognition`.
- On `result` event:
  - Render live text into `live-transcription-content` with timestamp `[HH:MM:SS - VOICE STREAM]`.
  - Update `inputText.value`.
  - Auto-scroll to bottom.
- Listen for `SCAMTRAP_ACTIVATED` and `INTELLIGENCE_EXTRACTED` events in SSE stream to show `scamtrap-panel` and populate `stalling-text`, `intel-urls`, and `intel-ibans`.

- [ ] **Step 4: Verify UI locally with server**

Run: `pytest -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/visualizer/index.html frontend/visualizer/styles.css frontend/visualizer/app.js
git commit -m "feat(ui): add live audio transcription stream box and ScamTrap CRT panel"
```

---

### Task 5: Final Integrated Test Suite & Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`  
Expected: 100% green test suite (70+ tests passing)

- [ ] **Step 2: Commit & Handoff**

```bash
git add .
git commit -m "feat(scamtrap): complete Live Audio Protection & ScamTrap Counter-Deception feature"
```
