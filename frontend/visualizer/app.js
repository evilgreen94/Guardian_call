/**
 * Guardian Call GC-80 workstation client.
 * Dynamic values are rendered only from REST responses or SSE domain events.
 */

document.addEventListener('DOMContentLoaded', () => {
  const SIGNAL_FIELDS = [
    'identity_claim',
    'identity_verified',
    'financial_context',
    'urgency',
    'secrecy_request',
    'otp_request',
    'password_request',
    'transfer_request',
    'remote_access_request',
    'requested_action',
  ];

  const sysClock = document.getElementById('sys-clock');
  const streamStatus = document.getElementById('stream-status');
  const inputText = document.getElementById('input-text');
  const inputState = document.getElementById('input-state');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  const scenarioSelect = document.getElementById('scenario-select');
  const expectedRiskTag = document.getElementById('expected-risk-tag');

  const pipeCallState = document.getElementById('pipe-call-state');
  const pipeGeminiState = document.getElementById('pipe-gemini-state');
  const pipeRiskState = document.getElementById('pipe-risk-state');
  const pipeCanaryState = document.getElementById('pipe-canary-state');
  const pipeActionState = document.getElementById('pipe-action-state');
  const pipeActionLabel = document.getElementById('pipe-action-label');
  const pipeCallTime = document.getElementById('pipe-call-time');
  const pipeGeminiTime = document.getElementById('pipe-gemini-time');
  const pipeRiskTime = document.getElementById('pipe-risk-time');
  const pipeCanaryTime = document.getElementById('pipe-canary-time');
  const pipeActionTime = document.getElementById('pipe-action-time');

  const reasonsTelemetry = document.getElementById('reasons-telemetry');
  const signalRegisterBody = document.getElementById('signal-register-body');

  const canaryAction = document.getElementById('canary-action');
  const canaryDecision = document.getElementById('canary-decision');
  const canaryRiskLevel = document.getElementById('canary-risk-level');
  const canaryReason = document.getElementById('canary-reason');
  const canaryIntervention = document.getElementById('canary-intervention');
  const canaryTime = document.getElementById('canary-time');
  const crtMode = document.getElementById('crt-mode');
  const crtOutput = document.getElementById('crt-output');

  const warningInterrupt = document.getElementById('warning-interrupt');
  const userPreview = document.getElementById('user-preview');
  const placardHeadline = document.getElementById('placard-headline');
  const placardDirectives = document.getElementById('placard-directives');
  const eventStreamTerminal = document.getElementById('event-stream-terminal');
  const eventLineCount = document.getElementById('event-line-count');

  let scenarios = {};
  let printedLines = 0;

  function setText(element, text) {
    if (element) element.textContent = text;
  }

  function setStateClass(element, baseClass, stateClass) {
    if (element) element.className = `${baseClass} ${stateClass}`.trim();
  }

  function classForRisk(level) {
    const normalized = String(level || '').toUpperCase();
    if (normalized === 'CRITICAL') return 'state-critical';
    if (normalized === 'HIGH') return 'state-high';
    if (normalized === 'SUSPICIOUS') return 'state-suspicious';
    if (normalized === 'NORMAL') return 'state-ok';
    return 'state-muted';
  }

  function classForDecision(decision) {
    const normalized = String(decision || '').toUpperCase();
    if (normalized === 'ALLOW') return 'state-allow';
    if (normalized === 'ASK_USER') return 'state-ask_user';
    if (normalized === 'DENY') return 'state-deny';
    return 'state-muted';
  }

  function isAsserted(value) {
    return value === true || (typeof value === 'string' && value.trim().length > 0);
  }

  function formatValue(value) {
    if (value === true) return 'true';
    if (value === false) return 'false';
    if (value === null || value === undefined || value === '') return '-';
    return String(value);
  }

  function eventTime(timestamp) {
    const raw = timestamp || new Date().toISOString();
    if (!raw.includes('T')) return '00:00:00';
    return raw.split('T')[1].split('.')[0].replace('Z', '');
  }

  function updateClock() {
    const now = new Date();
    setText(sysClock, `${now.toISOString().split('T')[1].substring(0, 8)} UTC`);
  }

  setInterval(updateClock, 1000);
  updateClock();

  function resetPipeline() {
    setText(pipeCallState, '-');
    setStateClass(pipeCallState, 'seq-state', 'state-muted');
    setText(pipeGeminiState, '-');
    setStateClass(pipeGeminiState, 'seq-state', 'state-muted');
    setText(pipeRiskState, 'NORMAL');
    setStateClass(pipeRiskState, 'seq-state', 'state-ok');
    setText(pipeCanaryState, 'DENY');
    setStateClass(pipeCanaryState, 'seq-state', 'state-deny');
    setText(pipeActionState, '-');
    setStateClass(pipeActionState, 'seq-state', 'state-muted');
    setText(pipeActionLabel, 'NO ACTION');
    [pipeCallTime, pipeGeminiTime, pipeRiskTime, pipeCanaryTime, pipeActionTime].forEach((node) => {
      setText(node, '--:--:--');
    });
  }

  function resetRegister() {
    signalRegisterBody.textContent = '';
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.className = 'empty';
    cell.textContent = 'Awaiting ScamSignals output.';
    row.appendChild(cell);
    signalRegisterBody.appendChild(row);
  }

  function resetReasons() {
    reasonsTelemetry.textContent = '';
    const item = document.createElement('li');
    item.className = 'empty';
    item.textContent = 'No risk assessment recorded.';
    reasonsTelemetry.appendChild(item);
  }

  function resetCanary() {
    setText(canaryAction, '-');
    setText(canaryDecision, 'DENY');
    setStateClass(canaryDecision, 'state', 'state-deny');
    setText(canaryRiskLevel, '-');
    setText(canaryReason, 'No Canary evaluation recorded.');
    setText(canaryIntervention, 'NONE');
    setText(canaryTime, '--:--:-- UTC');
    setText(crtMode, 'SAFE');
    setText(crtOutput, 'NONE');
  }

  function resetUserWarning() {
    warningInterrupt?.classList.remove('warning-interrupt-active');
    warningInterrupt?.setAttribute('aria-hidden', 'true');
    userPreview.className = 'user-preview';
    setText(placardHeadline, 'NO USER_WARNING EVENT');
    placardDirectives.textContent = '';
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'No authorized user-warning directives emitted.';
    placardDirectives.appendChild(empty);
  }

  function resetAuditLog() {
    printedLines = 0;
    eventStreamTerminal.textContent = '';
    appendLogRow('00:00:00', 'SYSTEM_READY', 'Awaiting backend domain events.');
    eventStreamTerminal.querySelector('.log-entry')?.classList.add('log-empty');
  }

  function resetWorkstation({ clearInput = true, clearScenario = true } = {}) {
    if (clearInput) inputText.value = '';
    if (clearScenario) scenarioSelect.value = '';
    if (clearScenario) {
      setText(expectedRiskTag, '');
      expectedRiskTag.className = 'scenario-target';
    }
    setText(inputState, 'IDLE');
    resetPipeline();
    resetRegister();
    resetReasons();
    resetCanary();
    resetUserWarning();
    resetAuditLog();
  }

  async function loadScenarios() {
    try {
      const res = await fetch('/api/v1/scenarios');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      scenarios = {};
      scenarioSelect.textContent = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '[ LOAD TEST TAPE ]';
      scenarioSelect.appendChild(placeholder);

      (data.scenarios || []).forEach((scenario) => {
        scenarios[scenario.id] = scenario;
        const option = document.createElement('option');
        option.value = scenario.id;
        option.textContent = `${scenario.title} [${scenario.expected_final_risk}]`;
        scenarioSelect.appendChild(option);
      });
    } catch (err) {
      console.error('Failed to load scenarios:', err);
      scenarioSelect.textContent = '';
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '[ TEST TAPE CATALOG UNAVAILABLE ]';
      scenarioSelect.appendChild(option);
    }
  }

  scenarioSelect?.addEventListener('change', () => {
    const scenario = scenarios[scenarioSelect.value];
    setText(expectedRiskTag, '');
    expectedRiskTag.className = 'scenario-target';

    if (!scenario) return;

    inputText.value = (scenario.dialogue || []).join(' ');
    if (scenario.expected_final_risk) {
      setText(expectedRiskTag, `EXPECTED: ${scenario.expected_final_risk}`);
      expectedRiskTag.className = `scenario-target ${classForRisk(scenario.expected_final_risk)}`;
    }
  });

  btnClear?.addEventListener('click', () => resetWorkstation());

  function createMeter(asserted) {
    const meter = document.createElement('span');
    meter.className = 'level-meter';
    for (let i = 0; i < 6; i += 1) {
      const block = document.createElement('i');
      if (asserted && i < 2) block.className = 'on';
      meter.appendChild(block);
    }
    return meter;
  }

  function renderSignals(signals) {
    signalRegisterBody.textContent = '';
    if (!signals) {
      resetRegister();
      return;
    }

    SIGNAL_FIELDS.forEach((field, index) => {
      const value = signals[field];
      const asserted = isAsserted(value);
      const row = document.createElement('tr');

      const idCell = document.createElement('td');
      idCell.textContent = String(index + 1).padStart(2, '0');

      const fieldCell = document.createElement('td');
      fieldCell.textContent = field;

      const stateCell = document.createElement('td');
      stateCell.textContent = asserted ? 'ASSERTED' : 'CLEARED';
      stateCell.className = asserted ? 'state-asserted' : 'state-cleared';

      const valueCell = document.createElement('td');
      valueCell.textContent = formatValue(value);

      const meterCell = document.createElement('td');
      meterCell.appendChild(createMeter(asserted));

      row.append(idCell, fieldCell, stateCell, valueCell, meterCell);
      signalRegisterBody.appendChild(row);
    });
  }

  function renderReasons(reasons) {
    reasonsTelemetry.textContent = '';
    if (!Array.isArray(reasons) || reasons.length === 0) {
      const item = document.createElement('li');
      item.className = 'empty';
      item.textContent = 'No risk reasons emitted.';
      reasonsTelemetry.appendChild(item);
      return;
    }

    reasons.forEach((reason) => {
      const item = document.createElement('li');
      item.textContent = reason;
      reasonsTelemetry.appendChild(item);
    });
  }

  function renderRisk(riskAssessment) {
    if (!riskAssessment) return;
    const level = riskAssessment.level || 'NORMAL';
    setText(pipeRiskState, level);
    setStateClass(pipeRiskState, 'seq-state', classForRisk(level));
    renderReasons(riskAssessment.reasons || []);
  }

  function renderCanary(decision) {
    if (!decision) return;
    const policyDecision = decision.decision || 'DENY';
    setText(pipeCanaryState, policyDecision);
    setStateClass(pipeCanaryState, 'seq-state', classForDecision(policyDecision));

    setText(canaryAction, decision.action || '-');
    setText(canaryDecision, policyDecision);
    setStateClass(canaryDecision, 'state', classForDecision(policyDecision));
    setText(canaryRiskLevel, decision.risk_level || '-');
    setText(canaryReason, decision.reason || '-');
    setText(canaryTime, `${eventTime(decision.timestamp)} UTC`);
  }

  function renderWarning(warning) {
    const payload = warning && warning.payload ? warning.payload : null;
    if (!payload) {
      resetUserWarning();
      return;
    }

    warningInterrupt?.classList.add('warning-interrupt-active');
    warningInterrupt?.setAttribute('aria-hidden', 'false');
    userPreview.className = 'user-preview warning-active';
    setText(placardHeadline, payload.headline || 'USER_WARNING');
    setText(crtMode, payload.severity || 'WARNING');
    setText(crtOutput, 'USER_WARNING');
    setText(canaryIntervention, 'USER_WARNING');
    placardDirectives.textContent = '';

    const directives = Array.isArray(payload.directives) ? payload.directives : [];
    if (directives.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty';
      empty.textContent = 'USER_WARNING event contained no directives.';
      placardDirectives.appendChild(empty);
      return;
    }

    directives.forEach((directive) => {
      const line = document.createElement('output');
      line.className = 'directive-line';
      line.textContent = directive;
      placardDirectives.appendChild(line);
    });
  }

  function renderAnalysisData(data) {
    if (data.error) {
      setText(inputState, 'ERROR');
      setText(pipeCallState, 'RX');
      setStateClass(pipeCallState, 'seq-state', 'state-eval');
      setText(pipeGeminiState, 'FAIL');
      setStateClass(pipeGeminiState, 'seq-state', 'state-error');
      setText(pipeRiskState, 'HALT');
      setStateClass(pipeRiskState, 'seq-state', 'state-muted');
      setText(pipeCanaryState, '-');
      setStateClass(pipeCanaryState, 'seq-state', 'state-muted');
      setText(pipeActionState, '-');
      setStateClass(pipeActionState, 'seq-state', 'state-muted');
      renderReasons([data.error]);
      resetCanary();
      resetUserWarning();
      return;
    }

    setText(inputState, 'COMPLETE');
    setText(pipeCallState, 'RX');
    setStateClass(pipeCallState, 'seq-state', 'state-eval');
    setText(pipeGeminiState, 'OK');
    setStateClass(pipeGeminiState, 'seq-state', 'state-ok');
    renderSignals(data.signals);
    renderRisk(data.risk_assessment);
    renderCanary(data.canary_decision);

    if (data.warning) {
      setText(pipeActionState, 'USER');
      setText(pipeActionLabel, 'USER_WARNING');
      setStateClass(pipeActionState, 'seq-state', 'state-critical');
      renderWarning(data.warning);
    } else {
      const decision = data.canary_decision && data.canary_decision.decision;
      setText(pipeActionState, '-');
      setText(pipeActionLabel, decision === 'ALLOW' ? 'AUTHORIZED' : 'NO ACTION');
      setStateClass(pipeActionState, 'seq-state', decision === 'ALLOW' ? 'state-allow' : 'state-muted');
      resetUserWarning();
    }
  }

  function summarizeEvent(evt) {
    const payload = evt.payload || {};

    if (evt.event_type === 'INPUT_RECEIVED') {
      return `Conversation input acquired len=${payload.input_length || 0} type=${payload.input_type || 'text'}`;
    }
    if (evt.event_type === 'SIGNAL_DETECTED') {
      const sigs = payload.signals || {};
      const active = SIGNAL_FIELDS
        .filter((field) => isAsserted(sigs[field]))
        .map((field) => `${field}=${formatValue(sigs[field])}`);
      return active.length > 0 ? active.join(' ') : 'active=0';
    }
    if (evt.event_type === 'RISK_UPDATED') {
      return `Risk level: ${payload.level || '-'} reasons=${Array.isArray(payload.reasons) ? payload.reasons.length : 0}`;
    }
    if (evt.event_type === 'CANARY_EVALUATION') {
      return `Decision: ${payload.decision || '-'} action=${payload.action || '-'}`;
    }
    if (evt.event_type === 'ACTION_ALLOWED' || evt.event_type === 'ACTION_DENIED') {
      return `Action: ${payload.action || '-'} reason=${payload.reason || '-'}`;
    }
    if (evt.event_type === 'USER_WARNING') {
      return `headline=${payload.headline || '-'} directives=${Array.isArray(payload.directives) ? payload.directives.length : 0}`;
    }
    if (evt.event_type === 'EXTRACTION_FAILED') {
      return `error_type=${payload.error_type || '-'} message=${payload.message || '-'}`;
    }
    if (evt.event_type === 'STREAM_CONNECTED') {
      return 'SSE channel established';
    }
    return Object.keys(payload).length > 0 ? 'payload=present' : 'payload=empty';
  }

  function appendLogRow(time, eventType, summary) {
    printedLines += 1;
    setText(eventLineCount, `LINES ${String(printedLines).padStart(3, '0')}`);

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const timeCell = document.createElement('span');
    timeCell.className = 'log-time';
    timeCell.textContent = time;

    const eventCell = document.createElement('span');
    eventCell.className = `log-event event-${String(eventType).toLowerCase()}`;
    eventCell.textContent = eventType;

    const payloadCell = document.createElement('span');
    payloadCell.className = 'log-payload';
    payloadCell.textContent = summary;

    entry.append(timeCell, eventCell, payloadCell);
    eventStreamTerminal.appendChild(entry);
    eventStreamTerminal.scrollTop = eventStreamTerminal.scrollHeight;
  }

  function appendRealDomainEvent(evt) {
    if (!evt || !evt.event_type || evt.event_type === 'STREAM_CONNECTED') return;
    eventStreamTerminal.querySelector('.log-empty')?.remove();
    appendLogRow(eventTime(evt.timestamp), evt.event_type, summarizeEvent(evt));
  }

  function applyEventToWorkstation(evt) {
    if (!evt || !evt.event_type) return;
    const payload = evt.payload || {};
    const time = eventTime(evt.timestamp);

    if (evt.event_type === 'INPUT_RECEIVED') {
      setText(inputState, 'RUNNING');
      setText(pipeCallState, 'RX');
      setStateClass(pipeCallState, 'seq-state', 'state-eval');
      setText(pipeCallTime, time);
    } else if (evt.event_type === 'SIGNAL_DETECTED') {
      setText(pipeGeminiState, 'OK');
      setStateClass(pipeGeminiState, 'seq-state', 'state-ok');
      setText(pipeGeminiTime, time);
      renderSignals(payload.signals);
    } else if (evt.event_type === 'RISK_UPDATED') {
      setText(pipeRiskTime, time);
      renderRisk(payload);
    } else if (evt.event_type === 'CANARY_EVALUATION') {
      setText(pipeCanaryTime, time);
      renderCanary(payload);
    } else if (evt.event_type === 'ACTION_ALLOWED') {
      setText(pipeActionState, 'USER');
      setText(pipeActionLabel, 'AUTHORIZED');
      setStateClass(pipeActionState, 'seq-state', 'state-allow');
      setText(pipeActionTime, time);
      setText(canaryIntervention, payload.action || 'warn_user');
    } else if (evt.event_type === 'ACTION_DENIED') {
      setText(pipeActionState, '-');
      setText(pipeActionLabel, 'NO ACTION');
      setStateClass(pipeActionState, 'seq-state', 'state-muted');
      setText(pipeActionTime, time);
      setText(canaryIntervention, 'NONE');
    } else if (evt.event_type === 'USER_WARNING') {
      setText(pipeActionState, 'USER');
      setText(pipeActionLabel, 'USER_WARNING');
      setStateClass(pipeActionState, 'seq-state', 'state-critical');
      setText(pipeActionTime, time);
      renderWarning(evt);
    } else if (evt.event_type === 'EXTRACTION_FAILED') {
      setText(inputState, 'ERROR');
      setText(pipeGeminiState, 'FAIL');
      setStateClass(pipeGeminiState, 'seq-state', 'state-error');
      setText(pipeRiskState, 'HALT');
      setStateClass(pipeRiskState, 'seq-state', 'state-muted');
      renderReasons([payload.message || payload.error_type || 'Extraction failed.']);
    }
  }

  function initSSE() {
    try {
      const evtSource = new EventSource('/api/v1/events/stream');

      evtSource.onopen = () => {
        setText(streamStatus, 'LIVE');
        setStateClass(streamStatus, 'state', 'state-ok');
      };

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          appendRealDomainEvent(data);
          applyEventToWorkstation(data);
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      evtSource.onerror = () => {
        setText(streamStatus, 'OFFLINE');
        setStateClass(streamStatus, 'state', 'state-deny');
      };
    } catch (err) {
      console.warn('SSE stream connection failed:', err);
      setText(streamStatus, 'OFFLINE');
      setStateClass(streamStatus, 'state', 'state-deny');
    }
  }

  btnAnalyze?.addEventListener('click', async () => {
    const text = inputText.value.trim();
    if (!text) {
      alert('Please enter call text or load a test tape.');
      return;
    }

    resetWorkstation({ clearInput: false, clearScenario: false });
    setText(inputState, 'RUNNING');
    btnAnalyze.disabled = true;
    btnAnalyze.textContent = 'RUNNING';

    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      renderAnalysisData(data);
    } catch (err) {
      console.error('Pipeline execution error:', err);
      alert(`Pipeline error: ${err.message}`);
      setText(inputState, 'ERROR');
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = 'EXECUTE ANALYSIS';
    }
  });

  resetWorkstation();
  loadScenarios();
  initSSE();
});
