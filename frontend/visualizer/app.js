/**
 * Guardian Call GC-80 signal instrument client.
 * The moving point advances only from real REST/SSE domain events.
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
  const guardrailStatus = document.getElementById('guardrail-status');
  const inputText = document.getElementById('input-text');
  const inputState = document.getElementById('input-state');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  const scenarioSelect = document.getElementById('scenario-select');
  const expectedRiskTag = document.getElementById('expected-risk-tag');

  // Tactical Controls & Expansion Elements
  const btnMicToggle = document.getElementById('btn-mic-toggle');
  const btnScanImap = document.getElementById('btn-scan-imap');
  const fileImageUpload = document.getElementById('file-image-upload');
  const liveAudioBox = document.getElementById('live-audio-box');
  const liveAudioTranscript = document.getElementById('live-audio-transcript');
  const micDiagnosticBanner = document.getElementById('mic-diagnostic-banner');
  
  const imagePreviewZone = document.getElementById('image-preview-zone');
  const imagePreviewImg = document.getElementById('image-preview-img');
  const btnAnalyzeImage = document.getElementById('btn-analyze-image');
  const btnClearImage = document.getElementById('btn-clear-image');
  
  const scamtrapBlock = document.getElementById('scamtrap-block');
  const scamtrapStallingText = document.getElementById('scamtrap-stalling-text');
  const btnCopyStalling = document.getElementById('btn-copy-stalling');
  const scamtrapIntelMatrix = document.getElementById('scamtrap-intel-matrix');
  
  const emailAlertBanner = document.getElementById('email-alert-banner');
  const emailSender = document.getElementById('email-sender');
  const emailSubject = document.getElementById('email-subject');

  const btnModeTelemetry = document.getElementById('btn-mode-telemetry');
  const btnModeProtected = document.getElementById('btn-mode-protected');
  const btnPhoneBack = document.getElementById('btn-phone-back');
  const btnPhoneEnd = document.getElementById('btn-phone-end');
  const instrumentSurface = document.getElementById('instrument-surface');
  const protectedUserView = document.getElementById('protected-user-view');
  const phoneHeadline = document.getElementById('phone-headline');
  const phoneSubheadline = document.getElementById('phone-subheadline');
  const phoneDirectives = document.getElementById('phone-directives');

  const btnTtyEvents = document.getElementById('btn-tty-events');
  const btnTtyAudit = document.getElementById('btn-tty-audit');
  const btnRefreshAudit = document.getElementById('btn-refresh-audit');
  const btnExportAudit = document.getElementById('btn-export-audit');
  const eventStreamContainer = document.getElementById('event-stream-container');
  const auditLogContainer = document.getElementById('audit-log-container');
  const auditHistoryTerminal = document.getElementById('audit-history-terminal');

  const rail = document.getElementById('pipeline-rail');
  const railState = document.getElementById('rail-state');
  const pipeCallState = document.getElementById('pipe-call-state');
  const pipeGeminiState = document.getElementById('pipe-gemini-state');
  const pipeRiskState = document.getElementById('pipe-risk-state');
  const pipeCanaryState = document.getElementById('pipe-canary-state');
  const pipeActionState = document.getElementById('pipe-action-state');

  const riskLevelReadout = document.getElementById('risk-level-readout');
  const reasonsTelemetry = document.getElementById('reasons-telemetry');
  const contributingSignals = document.getElementById('contributing-signals');
  const signalRegisterBody = document.getElementById('signal-register-body');

  const canaryAction = document.getElementById('canary-action');
  const canaryDecision = document.getElementById('canary-decision');
  const canaryRiskLevel = document.getElementById('canary-risk-level');
  const canaryReason = document.getElementById('canary-reason');

  const warningInterrupt = document.getElementById('warning-interrupt');
  const warningClose = document.getElementById('warning-close');
  const placardHeadline = document.getElementById('placard-headline');
  const placardDirectives = document.getElementById('placard-directives');

  const eventStreamTerminal = document.getElementById('event-stream-terminal');
  const eventLineCount = document.getElementById('event-line-count');

  let scenarios = {};
  let printedLines = 0;
  let visualQueue = [];
  let visualProcessing = false;
  let visualRunId = 0;
  let sseLive = false;
  let selectedImageFile = null;
  let speechRecognition = null;
  let isMicActive = false;
  let auditLogsData = [];
  const VISUAL_STEP_MS = 450;
  const RAIL_POINTS = {
    idle: { x: '6%', color: 'var(--text-dim)' },
    call: { x: '6%', color: 'var(--amber)' },
    'gemini-pending': { x: '18%', color: 'var(--amber)' },
    gemini: { x: '26%', color: 'var(--green)' },
    risk: { x: '51%', color: 'var(--amber)' },
    canary: { x: '75.5%', color: 'var(--amber)' },
    crossed: { x: '84%', color: 'var(--green)' },
    action: { x: '94%', color: 'var(--red)' },
    denied: { x: '75.5%', color: 'var(--red)' },
  };

  function setText(element, text) {
    if (element) element.textContent = text;
  }

  function setClass(element, baseClass, stateClass) {
    if (element) element.className = `${baseClass} ${stateClass}`.trim();
  }

  function setRailPoint(position) {
    if (!rail) return;
    const point = RAIL_POINTS[position] || RAIL_POINTS.idle;
    rail.className = `pipeline-rail point-${position}`;
    rail.style.setProperty('--point-x', point.x);
    rail.style.setProperty('--point-color', point.color);
  }

  function setPendingExtractionState() {
    setText(inputState, 'RUNNING');
    setText(railState, 'GEMINI PROCESSING');
    setText(pipeCallState, 'RX');
    setText(pipeGeminiState, 'PROCESSING');
    setClass(pipeGeminiState, 'state', 'state-eval');
    setRailPoint('gemini-pending');
  }

  function enqueueVisualEvent(evt) {
    if (!evt || !evt.event_type || evt.event_type === 'STREAM_CONNECTED') return;
    visualQueue.push({ evt, runId: visualRunId });
    processVisualQueue();
  }

  async function processVisualQueue() {
    if (visualProcessing) return;
    visualProcessing = true;
    while (visualQueue.length > 0) {
      const { evt, runId } = visualQueue.shift();
      if (runId !== visualRunId) continue;
      applyEventToInstrument(evt);
      await new Promise((resolve) => setTimeout(resolve, VISUAL_STEP_MS));
    }
    visualProcessing = false;
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
    setRailPoint('idle');
    setText(railState, 'AWAITING INPUT');
    setText(pipeCallState, '-');
    setText(pipeGeminiState, '-');
    setText(pipeRiskState, 'NORMAL');
    setClass(pipeRiskState, 'state', 'state-ok');
    setText(pipeCanaryState, 'DENY');
    setClass(pipeCanaryState, 'state', 'state-deny');
    setText(pipeActionState, '-');
  }

  function resetRegister() {
    signalRegisterBody.textContent = '';
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'Awaiting ScamSignals output.';
    signalRegisterBody.appendChild(empty);
  }

  function resetReasons() {
    reasonsTelemetry.textContent = '';
    const item = document.createElement('li');
    item.className = 'empty';
    item.textContent = 'No risk assessment recorded.';
    reasonsTelemetry.appendChild(item);
    setText(contributingSignals, '-');
  }

  function resetCanary() {
    setText(canaryAction, '-');
    setText(canaryDecision, 'DENY');
    setClass(canaryDecision, 'state', 'state-deny');
    setText(canaryRiskLevel, '-');
    setText(canaryReason, 'No Canary evaluation recorded.');
  }

  function resetWarning() {
    warningInterrupt?.classList.remove('warning-interrupt-active');
    warningInterrupt?.setAttribute('aria-hidden', 'true');
    setText(placardHeadline, 'NO USER_WARNING EVENT');
    placardDirectives.textContent = '';
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = 'No authorized user-warning directives emitted.';
    placardDirectives.appendChild(empty);
  }

  function closeWarningInterrupt() {
    warningInterrupt?.classList.remove('warning-interrupt-active');
    warningInterrupt?.setAttribute('aria-hidden', 'true');
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
      expectedRiskTag.className = '';
    }
    visualRunId += 1;
    visualQueue = [];
    setText(inputState, 'IDLE');
    resetPipeline();
    resetRegister();
    resetReasons();
    resetCanary();
    resetWarning();
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
    expectedRiskTag.className = '';
    if (!scenario) return;

    inputText.value = (scenario.dialogue || []).join(' ');
    if (scenario.expected_final_risk) {
      setText(expectedRiskTag, `EXPECTED: ${scenario.expected_final_risk}`);
      expectedRiskTag.className = classForRisk(scenario.expected_final_risk);
    }
  });

  btnClear?.addEventListener('click', () => resetWorkstation());

  function renderSignals(signals) {
    signalRegisterBody.textContent = '';
    if (!signals) {
      resetRegister();
      return;
    }

    SIGNAL_FIELDS.forEach((field) => {
      const value = signals[field];
      const asserted = isAsserted(value);
      const row = document.createElement('div');
      row.className = 'signal-row';

      const mark = document.createElement('span');
      mark.className = `signal-mark ${asserted ? 'state-asserted' : 'state-cleared'}`;
      mark.textContent = asserted ? '\u25a0' : '.';

      const key = document.createElement('span');
      key.textContent = field;

      const val = document.createElement('span');
      val.textContent = formatValue(value);

      row.append(mark, key, val);
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
    setClass(pipeRiskState, 'state', classForRisk(level));
    setText(riskLevelReadout, level);
    setClass(riskLevelReadout, 'state', classForRisk(level));
    renderReasons(riskAssessment.reasons || []);
    setText(contributingSignals, (riskAssessment.contributing_signals || []).join('  ') || '-');
  }

  function renderCanary(decision) {
    if (!decision) return;
    const policyDecision = decision.decision || 'DENY';
    setText(pipeCanaryState, policyDecision);
    setClass(pipeCanaryState, 'state', classForDecision(policyDecision));
    setText(canaryAction, decision.action || '-');
    setText(canaryDecision, policyDecision);
    setClass(canaryDecision, 'state', classForDecision(policyDecision));
    setText(canaryRiskLevel, decision.risk_level || '-');
    setText(canaryReason, decision.reason || '-');
  }

  function renderWarning(warning) {
    const payload = warning && warning.payload ? warning.payload : null;
    if (!payload) {
      resetWarning();
      return;
    }

    warningInterrupt?.classList.add('warning-interrupt-active');
    warningInterrupt?.setAttribute('aria-hidden', 'false');
    setText(placardHeadline, payload.headline || 'USER_WARNING');
    placardDirectives.textContent = '';

    const directives = Array.isArray(payload.directives) ? payload.directives : [];
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
      setRailPoint('gemini');
      setText(pipeCallState, 'RX');
      setText(pipeGeminiState, 'FAIL');
      setClass(pipeGeminiState, 'state', 'state-error');
      renderReasons([data.error]);
      resetCanary();
      resetWarning();
      return;
    }

    setText(inputState, 'COMPLETE');
    setText(pipeCallState, 'RX');
    setText(pipeGeminiState, 'EXTRACTED');
    setClass(pipeGeminiState, 'state', 'state-ok');
    renderSignals(data.signals);
    renderRisk(data.risk_assessment);
    renderCanary(data.canary_decision);

    if (data.warning) {
      setText(pipeActionState, 'USER_WARNING');
      setRailPoint('action');
      renderWarning(data.warning);
    } else {
      const decision = data.canary_decision && data.canary_decision.decision;
      setText(pipeActionState, '-');
      setRailPoint(decision === 'ALLOW' ? 'crossed' : 'denied');
      resetWarning();
    }
  }

  function summarizeEvent(evt) {
    const payload = evt.payload || {};
    if (evt.event_type === 'INPUT_RECEIVED') {
      return `len=${payload.input_length || 0} type=${payload.input_type || 'text'}`;
    }
    if (evt.event_type === 'SIGNAL_DETECTED') {
      const sigs = payload.signals || {};
      const active = SIGNAL_FIELDS
        .filter((field) => isAsserted(sigs[field]))
        .map((field) => `${field}=${formatValue(sigs[field])}`);
      return active.length > 0 ? active.join(' ') : 'active=0';
    }
    if (evt.event_type === 'RISK_UPDATED') {
      return `${payload.level || '-'} reasons=${Array.isArray(payload.reasons) ? payload.reasons.length : 0}`;
    }
    if (evt.event_type === 'CANARY_EVALUATION') {
      return `${payload.decision || '-'} action=${payload.action || '-'}`;
    }
    if (evt.event_type === 'ACTION_ALLOWED' || evt.event_type === 'ACTION_DENIED') {
      return `action=${payload.action || '-'} reason=${payload.reason || '-'}`;
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

  function applyEventToInstrument(evt) {
    if (!evt || !evt.event_type) return;
    const payload = evt.payload || {};

    if (evt.event_type === 'INPUT_RECEIVED') {
      setText(inputState, 'RUNNING');
      setText(railState, 'CALL INPUT RECEIVED');
      setText(pipeCallState, 'RX');
      if (pipeGeminiState?.textContent !== 'PROCESSING') {
        setRailPoint('call');
      }
    } else if (evt.event_type === 'SIGNAL_DETECTED') {
      setText(railState, 'GEMINI SIGNALS EXTRACTED');
      setText(pipeGeminiState, 'EXTRACTED');
      setClass(pipeGeminiState, 'state', 'state-ok');
      setRailPoint('gemini');
      renderSignals(payload.signals);
    } else if (evt.event_type === 'RISK_UPDATED') {
      setText(railState, 'RISK UPDATED');
      setRailPoint('risk');
      renderRisk(payload);
    } else if (evt.event_type === 'CANARY_EVALUATION') {
      setText(railState, 'CANARY EVALUATION');
      setRailPoint('canary');
      renderCanary(payload);
    } else if (evt.event_type === 'ACTION_ALLOWED') {
      setText(railState, 'CANARY ALLOW - BOUNDARY CROSSED');
      setRailPoint('crossed');
    } else if (evt.event_type === 'ACTION_DENIED') {
      setText(railState, 'CANARY DENY - BOUNDARY STOP');
      setRailPoint('denied');
      setText(pipeActionState, '-');
    } else if (evt.event_type === 'USER_WARNING') {
      setText(railState, 'USER WARNING EMITTED');
      setRailPoint('action');
      setText(pipeActionState, 'USER_WARNING');
      renderWarning(evt);
    } else if (evt.event_type === 'EXTRACTION_FAILED') {
      setText(inputState, 'ERROR');
      setText(railState, 'EXTRACTION FAILED');
      setText(pipeGeminiState, 'FAIL');
      setClass(pipeGeminiState, 'state', 'state-error');
      renderReasons([payload.message || payload.error_type || 'Extraction failed.']);
    } else if (evt.event_type === 'SCAMTRAP_ACTIVATED') {
      handleScamTrapActivation(payload);
    } else if (evt.event_type === 'REALTIME_EMAIL_ANALYSIS') {
      if (emailAlertBanner) {
        emailAlertBanner.style.display = 'block';
        setText(emailSender, evt.sender || payload.sender || '-');
        setText(emailSubject, evt.subject || payload.subject || '-');
      }
    } else if (evt.event_type === 'GEMMA_GUARDRAIL_EVALUATION') {
      const isBlocked = payload.guardrail_passed === false || payload.verdict === 'BLOCKED';
      setText(guardrailStatus, isBlocked ? 'INJECTION DETECTED' : 'CLEAN');
      setClass(guardrailStatus, 'state', isBlocked ? 'state-critical' : 'state-ok');
    }
  }

  function initSSE() {
    try {
      const evtSource = new EventSource('/api/v1/events/stream');
      evtSource.onopen = () => {
        sseLive = true;
        setText(streamStatus, 'LIVE');
        setClass(streamStatus, 'state', 'state-ok');
      };
      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          appendRealDomainEvent(data);
          enqueueVisualEvent(data);
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };
      evtSource.onerror = () => {
        sseLive = false;
        setText(streamStatus, 'OFFLINE');
        setClass(streamStatus, 'state', 'state-deny');
      };
    } catch (err) {
      console.warn('SSE stream connection failed:', err);
      sseLive = false;
      setText(streamStatus, 'OFFLINE');
      setClass(streamStatus, 'state', 'state-deny');
    }
  }

  warningClose?.addEventListener('click', closeWarningInterrupt);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeWarningInterrupt();
  });

  btnAnalyze?.addEventListener('click', async () => {
    const text = inputText.value.trim();
    if (!text) {
      alert('Please enter call text or load a test tape.');
      return;
    }

    resetWorkstation({ clearInput: false, clearScenario: false });
    setPendingExtractionState();
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
      if (!sseLive && Array.isArray(data.events)) {
        data.events.forEach((evt) => {
          appendRealDomainEvent(evt);
          enqueueVisualEvent(evt);
        });
      }
    } catch (err) {
      console.error('Pipeline execution error:', err);
      alert(`Pipeline error: ${err.message}`);
      setText(inputState, 'ERROR');
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = 'EXECUTE ANALYSIS';
    }
  });

  /* -------------------------------------------------------------
   * 1. MULTIMODAL VISION AGENT (IMAGE UPLOAD & ANALYSIS)
   * ------------------------------------------------------------- */
  fileImageUpload?.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    selectedImageFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
      if (imagePreviewImg) imagePreviewImg.src = event.target.result;
      if (imagePreviewZone) imagePreviewZone.style.display = 'block';
    };
    reader.readAsDataURL(file);
  });

  btnClearImage?.addEventListener('click', () => {
    selectedImageFile = null;
    if (fileImageUpload) fileImageUpload.value = '';
    if (imagePreviewZone) imagePreviewZone.style.display = 'none';
  });

  btnAnalyzeImage?.addEventListener('click', async () => {
    if (!selectedImageFile) {
      alert('Seleccione una imagen primero.');
      return;
    }
    resetWorkstation({ clearInput: false, clearScenario: false });
    setPendingExtractionState();
    if (btnAnalyzeImage) {
      btnAnalyzeImage.disabled = true;
      btnAnalyzeImage.textContent = 'ANALIZANDO IMAGEN...';
    }

    try {
      const formData = new FormData();
      formData.append('file', selectedImageFile);

      const response = await fetch('/api/v1/analyze-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      renderAnalysisData(data);
    } catch (err) {
      console.error('Error procesando imagen vision:', err);
      alert(`Error en análisis de imagen: ${err.message}`);
      setText(inputState, 'ERROR');
    } finally {
      if (btnAnalyzeImage) {
        btnAnalyzeImage.disabled = false;
        btnAnalyzeImage.textContent = '[ EXECUTE VISION ANALYSIS ]';
      }
    }
  });

  /* -------------------------------------------------------------
   * 2. LIVE AUDIO WEBSPEECH MICROPHONE BRIDGE
   * ------------------------------------------------------------- */
  btnMicToggle?.addEventListener('click', () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (micDiagnosticBanner) {
        micDiagnosticBanner.style.display = 'block';
        micDiagnosticBanner.textContent = '⚠️ WebSpeech API no soportada en este navegador. Pruebe Chrome, Edge o Safari.';
      }
      return;
    }

    if (isMicActive && speechRecognition) {
      speechRecognition.stop();
      isMicActive = false;
      btnMicToggle.textContent = '[ 🎙️ MIC EN VIVO ]';
      btnMicToggle.classList.remove('active');
      return;
    }

    try {
      speechRecognition = new SpeechRecognition();
      speechRecognition.continuous = true;
      speechRecognition.interimResults = true;
      speechRecognition.lang = 'es-ES';

      speechRecognition.onstart = () => {
        isMicActive = true;
        btnMicToggle.textContent = '[ 🛑 DETENER MIC ]';
        btnMicToggle.classList.add('active');
        if (liveAudioBox) liveAudioBox.style.display = 'block';
        if (micDiagnosticBanner) micDiagnosticBanner.style.display = 'none';
        if (liveAudioTranscript) liveAudioTranscript.textContent = 'Escuchando micrófono...';
      };

      speechRecognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (liveAudioTranscript) liveAudioTranscript.textContent = transcript;
        if (inputText) inputText.value = transcript;
      };

      speechRecognition.onerror = (event) => {
        console.error('Error de micrófono WebSpeech:', event.error);
        if (micDiagnosticBanner) {
          micDiagnosticBanner.style.display = 'block';
          micDiagnosticBanner.textContent = `⚠️ Error de micrófono: ${event.error}. Verifique los permisos del navegador.`;
        }
      };

      speechRecognition.onend = () => {
        isMicActive = false;
        btnMicToggle.textContent = '[ 🎙️ MIC EN VIVO ]';
        btnMicToggle.classList.remove('active');
      };

      speechRecognition.start();
    } catch (err) {
      console.error('No se pudo iniciar el micrófono:', err);
      if (micDiagnosticBanner) {
        micDiagnosticBanner.style.display = 'block';
        micDiagnosticBanner.textContent = `⚠️ Error al iniciar micrófono: ${err.message}`;
      }
    }
  });

  /* -------------------------------------------------------------
   * 3. IMAP GMAIL INBOX MANUAL SCAN
   * ------------------------------------------------------------- */
  btnScanImap?.addEventListener('click', async () => {
    btnScanImap.disabled = true;
    btnScanImap.textContent = '[ ⏳ ESCANANDO... ]';
    try {
      const response = await fetch('/api/v1/scan-inbox?limit=3', { method: 'POST' });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      alert(`Escaneo IMAP completado. ${data.count || 0} correos analizados.`);
    } catch (err) {
      console.error('Error en escaneo IMAP:', err);
      alert(`Error en escaneo IMAP: ${err.message}`);
    } finally {
      btnScanImap.disabled = false;
      btnScanImap.textContent = '[ 📧 SCAN GMAIL ]';
    }
  });

  /* -------------------------------------------------------------
   * 4. COPY SCAMTRAP STALLING RESPONSE
   * ------------------------------------------------------------- */
  btnCopyStalling?.addEventListener('click', () => {
    const text = scamtrapStallingText?.textContent.replace(/^"|"$/g, '');
    if (text) {
      navigator.clipboard.writeText(text);
      btnCopyStalling.textContent = '[ ✓ COPIADO AL PORTAPAPELES ]';
      setTimeout(() => {
        btnCopyStalling.textContent = '[ 📋 COPIAR RESPUESTA ]';
      }, 2000);
    }
  });

  /* -------------------------------------------------------------
   * 5. PERSISTENT DISK AUDIT LOGS TRAIL (/api/v1/audit-history)
   * ------------------------------------------------------------- */
  async function fetchAuditHistory() {
    if (!auditHistoryTerminal) return;
    auditHistoryTerminal.textContent = '';
    const loadingRow = document.createElement('div');
    loadingRow.className = 'log-entry';
    loadingRow.innerHTML = '<span class="log-time">...</span><span class="log-event">LOADING</span><span class="log-payload">Cargando registros desde data/audit_log.jsonl...</span>';
    auditHistoryTerminal.appendChild(loadingRow);

    try {
      const response = await fetch('/api/v1/audit-history?limit=50');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      auditLogsData = data.history || [];

      auditHistoryTerminal.textContent = '';
      if (auditLogsData.length === 0) {
        auditHistoryTerminal.innerHTML = '<div class="log-entry log-empty"><span class="log-time">00:00:00</span><span class="log-event">NO_LOGS</span><span class="log-payload">No hay registros guardados aún.</span></div>';
        return;
      }

      auditLogsData.forEach((rec) => {
        const row = document.createElement('div');
        row.className = 'log-entry';
        const timeStr = eventTime(rec.timestamp);
        const eventStr = rec.event_type || rec.action || 'AUDIT_RECORD';
        const payloadStr = JSON.stringify(rec.payload || rec.signals || rec.risk_assessment || rec);
        
        row.innerHTML = `
          <span class="log-time">${timeStr}</span>
          <span class="log-event event-${eventStr.toLowerCase()}">${eventStr}</span>
          <span class="log-payload">${payloadStr}</span>
        `;
        auditHistoryTerminal.appendChild(row);
      });
    } catch (err) {
      console.error('Error al cargar historial de auditoría:', err);
      auditHistoryTerminal.innerHTML = `<div class="log-entry log-empty"><span class="log-time">ERR</span><span class="log-event">FAIL</span><span class="log-payload">Error cargando registros: ${err.message}</span></div>`;
    }
  }

  btnTtyEvents?.addEventListener('click', () => {
    btnTtyEvents.classList.add('active');
    btnTtyAudit?.classList.remove('active');
    if (eventStreamContainer) eventStreamContainer.style.display = 'block';
    if (auditLogContainer) auditLogContainer.style.display = 'none';
    if (btnRefreshAudit) btnRefreshAudit.style.display = 'none';
    if (btnExportAudit) btnExportAudit.style.display = 'none';
  });

  btnTtyAudit?.addEventListener('click', () => {
    btnTtyAudit.classList.add('active');
    btnTtyEvents?.classList.remove('active');
    if (eventStreamContainer) eventStreamContainer.style.display = 'none';
    if (auditLogContainer) auditLogContainer.style.display = 'block';
    if (btnRefreshAudit) btnRefreshAudit.style.display = 'inline-block';
    if (btnExportAudit) btnExportAudit.style.display = 'inline-block';
    fetchAuditHistory();
  });

  btnRefreshAudit?.addEventListener('click', fetchAuditHistory);

  btnExportAudit?.addEventListener('click', () => {
    if (auditLogsData.length === 0) {
      alert('No hay registros de auditoría cargados.');
      return;
    }
    const blob = new Blob([JSON.stringify(auditLogsData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `guardian_audit_logs_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  /* -------------------------------------------------------------
   * 6. VIEW MODE SWITCHER (TELEMETRY WORKSTATION vs PROTECTED MODE)
   * ------------------------------------------------------------- */
  function setViewMode(mode) {
    if (mode === 'protected') {
      if (instrumentSurface) instrumentSurface.style.display = 'none';
      if (protectedUserView) protectedUserView.style.display = 'flex';
      btnModeProtected?.classList.add('active');
      btnModeTelemetry?.classList.remove('active');
    } else {
      if (instrumentSurface) instrumentSurface.style.display = 'grid';
      if (protectedUserView) protectedUserView.style.display = 'none';
      btnModeTelemetry?.classList.add('active');
      btnModeProtected?.classList.remove('active');
    }
  }

  btnModeTelemetry?.addEventListener('click', () => setViewMode('telemetry'));
  btnModeProtected?.addEventListener('click', () => setViewMode('protected'));
  btnPhoneBack?.addEventListener('click', () => setViewMode('telemetry'));

  btnPhoneEnd?.addEventListener('click', () => {
    alert('Llamada finalizada por el usuario siguiendo la recomendación de Canary.');
    setViewMode('telemetry');
  });

  resetWorkstation();
  loadScenarios();
  initSSE();
});
