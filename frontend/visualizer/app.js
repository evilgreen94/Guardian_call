/**
 * Guardian Call — Tactical Telemetry & Event Visualizer App Script
 * Connects frontend UI to FastAPI backend endpoints (/api/v1/analyze).
 */

document.addEventListener('DOMContentLoaded', () => {
  const sysClock = document.getElementById('sys-clock');
  const inputText = document.getElementById('input-text');
  
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  
  const btnPresetFailsafe = document.getElementById('btn-preset-failsafe');
  const scenarioSelect = document.getElementById('scenario-select');
  const scenarioRiskBadge = document.getElementById('scenario-risk-badge');
  
  const valRiskLevel = document.getElementById('val-risk-level');
  const valCanaryDecision = document.getElementById('val-canary-decision');
  const listRiskReasons = document.getElementById('list-risk-reasons');
  
  const userWarningBanner = document.getElementById('user-warning-banner');
  const warningHeadline = document.getElementById('warning-headline');
  const warningDirectives = document.getElementById('warning-directives');
  
  const signalsGrid = document.getElementById('signals-grid');
  const eventStream = document.getElementById('event-stream');

  // Fail-safe preset: not a real scenario, just triggers the extraction-failure code path
  const FAILSAFE_TEXT = "FAILSAFE_TEST_TRIGGER_API_SIMULATION";

  // Full scenario dataset (id -> scenario object), populated from /api/v1/scenarios
  let scenarios = {};

  async function loadScenarios() {
    try {
      const res = await fetch('/api/v1/scenarios');
      const data = await res.json();
      scenarios = {};
      scenarioSelect.innerHTML = '<option value="">[ SELECCIONA UN ESCENARIO... ]</option>';
      
      if (data.synthetic && data.synthetic.length > 0) {
        const groupSynth = document.createElement('optgroup');
        groupSynth.label = `── ESCENARIOS SINTÉTICOS DÍA 1 (${data.synthetic_count}) ──`;
        data.synthetic.forEach(sc => {
          scenarios[sc.id] = sc;
          const opt = document.createElement('option');
          opt.value = sc.id;
          opt.textContent = `${sc.title}`;
          groupSynth.appendChild(opt);
        });
        scenarioSelect.appendChild(groupSynth);
      }

      if (data.adversarial && data.adversarial.length > 0) {
        const groupAdv = document.createElement('optgroup');
        groupAdv.label = `── BENCHMARK ADVERSARIAL M1 (${data.adversarial_count}) ──`;
        data.adversarial.forEach(sc => {
          scenarios[sc.id] = sc;
          const opt = document.createElement('option');
          opt.value = sc.id;
          opt.textContent = `[M1] ${sc.title}`;
          groupAdv.appendChild(opt);
        });
        scenarioSelect.appendChild(groupAdv);
      }
    } catch (err) {
      console.error('Failed to load scenarios:', err);
      scenarioSelect.innerHTML = '<option value="">[ NO SE PUDIERON CARGAR ESCENARIOS ]</option>';
    }
  }
  loadScenarios();

  scenarioSelect?.addEventListener('change', () => {
    const sc = scenarios[scenarioSelect.value];
    scenarioRiskBadge.textContent = '';
    scenarioRiskBadge.className = 'scenario-risk-badge';
    if (!sc) return;

    inputText.value = sc.text || (sc.dialogue ? sc.dialogue.join(' ') : '');
    
    const expRisk = sc.expected_final_risk || (sc.expected ? sc.expected.risk_level : null);
    if (expRisk) {
      scenarioRiskBadge.textContent = `RIESGO ESPERADO: ${expRisk}`;
      scenarioRiskBadge.classList.add(`risk-${expRisk.toLowerCase()}`);
    }
  });

  // 1. Clock Update
  function updateClock() {
    const now = new Date();
    sysClock.textContent = now.toUTCString().split(' ')[4] + ' UTC';
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Fail-safe Preset (triggers the extraction-failure code path, not a real scenario)
  btnPresetFailsafe?.addEventListener('click', () => {
    inputText.value = FAILSAFE_TEXT;
    scenarioSelect.value = '';
    scenarioRiskBadge.textContent = '';
    scenarioRiskBadge.className = 'scenario-risk-badge';
  });

  let selectedFile = null;
  const dropZone = document.getElementById('drop-zone');
  const imageInput = document.getElementById('image-input');
  const fileNameDisplay = document.getElementById('file-name');

  // File Dropzone handlers
  dropZone?.addEventListener('click', () => imageInput?.click());

  imageInput?.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      selectedFile = e.target.files[0];
      fileNameDisplay.textContent = `SELECTED FILE: ${selectedFile.name} (${Math.round(selectedFile.size / 1024)} KB)`;
    }
  });

  dropZone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone?.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone?.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectedFile = e.dataTransfer.files[0];
      fileNameDisplay.textContent = `SELECTED FILE: ${selectedFile.name} (${Math.round(selectedFile.size / 1024)} KB)`;
    }
  });

  // 3. Clear Terminal
  btnClear?.addEventListener('click', () => {
    inputText.value = '';
    selectedFile = null;
    if (imageInput) imageInput.value = '';
    if (fileNameDisplay) fileNameDisplay.textContent = '';
    if (scenarioSelect) scenarioSelect.value = '';
    if (scenarioRiskBadge) {
      scenarioRiskBadge.textContent = '';
      scenarioRiskBadge.className = 'scenario-risk-badge';
    }
    if (micActive) recognition.stop();
    micSessionId = null;
    resetStatusDisplay();
  });

  function resetStatusDisplay() {
    valRiskLevel.textContent = 'NORMAL';
    valRiskLevel.className = 'card-value val-normal';

    valCanaryDecision.textContent = 'DENY';
    valCanaryDecision.className = 'card-value val-deny';

    listRiskReasons.innerHTML = '<li class="empty-state">No active risk signals evaluated yet.</li>';
    userWarningBanner.style.display = 'none';

    signalsGrid.innerHTML = '';
    eventStream.innerHTML = `
      <div class="event-item event-empty">
        <span class="evt-time">[00:00:00]</span>
        <span class="evt-type">SYSTEM_READY</span>
        <span class="evt-payload">Awaiting input submission to emit backend domain events...</span>
      </div>
    `;
  }

  // 4. Run Analysis
  btnAnalyze?.addEventListener('click', async () => {
    const text = inputText.value.trim();

    if (!selectedFile && !text) {
      alert('Please enter conversational text or attach/drop a screenshot file.');
      return;
    }

    btnAnalyze.disabled = true;
    btnAnalyze.textContent = selectedFile ? '[ ANALYZING MULTIMODAL SCREENSHOT... ]' : '[ ANALYZING AGENT SIGNALS... ]';

    try {
      let response;

      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        response = await fetch('/api/v1/analyze-image', {
          method: 'POST',
          body: formData
        });
      } else {
        response = await fetch('/api/v1/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
      }

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      const data = await response.json();
      renderResults(data);

    } catch (err) {
      console.error('Analysis failed:', err);
      alert(`Backend Analysis Error: ${err.message}`);
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = '[ RUN GOOGLE ADK ANALYSIS ]';
    }
  });

  // 4b. Live Mic Bridge (Web Speech API -> /api/v1/analyze, zero-cost browser STT)
  // ponytail: Chrome/Edge only (webkitSpeechRecognition), no server-side transcription
  // dependency added. Add a server-side STT fallback if cross-browser support matters later.
  const btnMicToggle = document.getElementById('btn-mic-toggle');
  const micStatusEl = document.getElementById('mic-status');
  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;

  let recognition = null;
  let micActive = false;
  let micSessionId = null;

  async function submitMicTurn(text) {
    if (!text || !text.trim()) return;
    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_id: micSessionId })
      });
      if (!response.ok) throw new Error(`HTTP error ${response.status}`);
      const data = await response.json();
      renderResults(data, { appendEvents: true });
    } catch (err) {
      console.error('Mic turn analysis failed:', err);
    }
  }

  if (!SpeechRecognitionImpl) {
    if (btnMicToggle) {
      btnMicToggle.disabled = true;
      btnMicToggle.textContent = '[ 🎤 MIC NO DISPONIBLE (usa Chrome/Edge) ]';
    }
  } else if (btnMicToggle) {
    btnMicToggle.addEventListener('click', () => {
      if (micActive) {
        recognition.stop();
        return;
      }

      micSessionId = window.crypto?.randomUUID ? window.crypto.randomUUID() : `mic-${Date.now()}`;
      recognition = new SpeechRecognitionImpl();
      recognition.lang = 'es-ES';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onstart = () => {
        micActive = true;
        btnMicToggle.textContent = '[ ⏹ DETENER MIC ]';
        if (micStatusEl) {
          micStatusEl.textContent = 'MIC: ESCUCHANDO...';
          micStatusEl.className = 'mic-status mic-live';
        }
      };

      recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript.trim()) {
          inputText.value += (inputText.value ? '\n' : '') + finalTranscript.trim();
          submitMicTurn(finalTranscript.trim());
        }

        if (micStatusEl) {
          micStatusEl.textContent = interimTranscript
            ? `MIC: "${interimTranscript}"`
            : 'MIC: ESCUCHANDO...';
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (micStatusEl) {
          micStatusEl.textContent = `MIC: ERROR (${event.error})`;
          micStatusEl.className = 'mic-status mic-error';
        }
      };

      recognition.onend = () => {
        micActive = false;
        btnMicToggle.textContent = '[ 🎤 INICIAR MIC EN VIVO ]';
        if (micStatusEl) {
          micStatusEl.textContent = 'MIC: INACTIVO';
          micStatusEl.className = 'mic-status';
        }
      };

      recognition.start();
    });
  }

  const btnScanInbox = document.getElementById('btn-scan-inbox');

  btnScanInbox?.addEventListener('click', async () => {
    btnScanInbox.disabled = true;
    btnScanInbox.textContent = '[ ESCANEANDO GMAIL (IMAP)... ]';

    try {
      const response = await fetch('/api/v1/scan-inbox?limit=5', {
        method: 'POST'
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP error ${response.status}`);
      }

      const data = await response.json();
      if (data.scanned_emails && data.scanned_emails.length > 0) {
        data.scanned_emails.forEach(email => handleLiveEvent(email));
      } else {
        alert(`[ESCÁNER IMAP COMPLETADO] Se analizaron ${data.count} correo(s) de tu bandeja de entrada.`);
      }

    } catch (err) {
      console.error('Inbox scan failed:', err);
      alert(`Error de escaneo IMAP: ${err.message}`);
    } finally {
      btnScanInbox.disabled = false;
      btnScanInbox.textContent = '[ 📩 ESCANEAR BANDEJA DE ENTRADA (IMAP) ]';
    }
  });

  const btnViewAuditLog = document.getElementById('btn-view-audit-log');
  const btnRefreshHistory = document.getElementById('btn-refresh-history');
  const btnExportHistory = document.getElementById('btn-export-history');
  const auditHistoryStream = document.getElementById('audit-history-stream');
  let currentAuditHistory = [];

  async function loadAuditHistory() {
    if (!auditHistoryStream) return;
    try {
      const res = await fetch('/api/v1/events/history?limit=100');
      if (!res.ok) return;
      const data = await res.json();
      currentAuditHistory = data.events || [];

      if (currentAuditHistory.length === 0) {
        auditHistoryStream.innerHTML = `
          <div class="event-item event-empty">
            <span class="evt-time">[LOGS]</span>
            <span class="evt-type">NO_LOGS</span>
            <span class="evt-payload">No persistent audit log records found on disk.</span>
          </div>`;
        return;
      }

      auditHistoryStream.innerHTML = '';
      currentAuditHistory.slice().reverse().forEach(evt => {
        const item = document.createElement('div');
        item.className = 'event-item';
        const timeStr = evt.timestamp ? (evt.timestamp.split('T')[1]?.substring(0, 8) || '00:00:00') : '00:00:00';
        const eventType = evt.event_type || 'EVENT';
        const payloadStr = JSON.stringify(evt.payload || evt.signals || evt.reasons || evt);
        item.innerHTML = `
          <span class="evt-time">[${timeStr}]</span>
          <span class="evt-type" style="color: #38bdf8;">${eventType}</span>
          <span class="evt-payload">${payloadStr}</span>
        `;
        auditHistoryStream.appendChild(item);
      });

      document.getElementById('audit-log-section')?.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
      console.error('Failed to load audit history:', err);
    }
  }

  btnViewAuditLog?.addEventListener('click', loadAuditHistory);
  btnRefreshHistory?.addEventListener('click', loadAuditHistory);

  btnExportHistory?.addEventListener('click', () => {
    if (currentAuditHistory.length === 0) {
      alert('No hay registros de auditoría para exportar.');
      return;
    }
    const blob = new Blob([JSON.stringify(currentAuditHistory, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `guardian_audit_logs_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // 5. Render Analysis Results
  function renderResults(data, { appendEvents = false } = {}) {
    const { signals, risk_assessment, canary_decision, warning, events } = data;

    // Render Risk Level
    const level = risk_assessment.level || 'NORMAL';
    valRiskLevel.textContent = level;
    valRiskLevel.className = `card-value val-${level.toLowerCase()}`;

    // Render Canary Decision
    const decision = canary_decision.decision || 'DENY';
    valCanaryDecision.textContent = decision;
    valCanaryDecision.className = `card-value val-${decision.toLowerCase()}`;

    // Render Reasons
    listRiskReasons.innerHTML = '';
    if (risk_assessment.reasons && risk_assessment.reasons.length > 0) {
      risk_assessment.reasons.forEach(reason => {
        const li = document.createElement('li');
        li.textContent = reason;
        listRiskReasons.appendChild(li);
      });
    } else {
      listRiskReasons.innerHTML = '<li class="empty-state">No malicious signals detected.</li>';
    }

    // Render Protected User Warning Banner
    if (warning && warning.payload) {
      userWarningBanner.style.display = 'flex';
      warningHeadline.textContent = warning.payload.headline || 'POSIBLE ESTAFA';
      warningDirectives.innerHTML = '';
      
      const directives = warning.payload.directives || [];
      directives.forEach(dir => {
        const item = document.createElement('div');
        item.className = 'warning-directive-item';
        item.textContent = dir;
        warningDirectives.appendChild(item);
      });
    } else {
      userWarningBanner.style.display = 'none';
    }

    // Render Extracted Signals Grid
    signalsGrid.innerHTML = '';
    if (signals) {
      Object.entries(signals).forEach(([key, val]) => {
        const cell = document.createElement('div');
        cell.className = 'signal-cell';

        let valClass = 'str';
        let displayVal = String(val);

        if (typeof val === 'boolean') {
          valClass = val ? 'true' : 'false';
          displayVal = val ? '[ TRUE ]' : '[ FALSE ]';
        } else if (val === null || val === undefined) {
          valClass = 'false';
          displayVal = '[ NONE ]';
        }

        cell.innerHTML = `
          <span class="signal-name">${key}</span>
          <span class="signal-val ${valClass}">${displayVal}</span>
        `;
        signalsGrid.appendChild(cell);
      });
    }

    // Render Event Stream Trail: single-shot analysis (manual paste, screenshots) replaces the
    // trail each run; a mic session appends so the multi-turn escalation stays visible as a log.
    if (appendEvents) {
      appendEventStream(events);
    } else {
      eventStream.innerHTML = '';
      appendEventStream(events);
    }
  }

  function appendEventStream(events) {
    if (!events || events.length === 0) return;
    if (eventStream.querySelector('.event-empty')) {
      eventStream.innerHTML = '';
    }
    events.forEach(evt => {
      const item = document.createElement('div');
      let evtClass = '';
      if (evt.event_type === 'USER_WARNING') evtClass = 'evt-warning';
      else if (evt.event_type === 'ACTION_ALLOWED') evtClass = 'evt-allowed';
      else if (evt.event_type === 'ACTION_DENIED') evtClass = 'evt-denied';
      else if (evt.event_type === 'SIGNAL_EXTRACTION_FAILED') evtClass = 'evt-failed';
      else if (evt.event_type === 'GATE_SKIPPED') evtClass = 'evt-gate-skipped';
      else if (evt.event_type === 'GATE_ESCALATED') evtClass = 'evt-gate-escalated';

      item.className = `event-item ${evtClass}`;

      const timeStr = evt.timestamp ? evt.timestamp.split('T')[1].split('.')[0] : '00:00:00';

      item.innerHTML = `
        <span class="evt-time">[${timeStr}]</span>
        <span class="evt-type">${evt.event_type}</span>
        <span class="evt-payload">${JSON.stringify(evt.payload)}</span>
      `;
      eventStream.appendChild(item);
    });
  }

  // 6. Real-Time Server-Sent Events (SSE) Stream Listener
  const streamStatus = document.getElementById('stream-status');
  const realtimeEmailCard = document.getElementById('realtime-email-card');
  const realtimeSender = document.getElementById('realtime-sender');
  const realtimeSubject = document.getElementById('realtime-subject');

  function initRealtimeStream() {
    try {
      const evtSource = new EventSource('/api/v1/events/stream');

      evtSource.onopen = () => {
        if (streamStatus) {
          streamStatus.textContent = 'CONNECTED';
          streamStatus.className = 'val val-ok';
        }
      };

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event_type === 'STREAM_CONNECTED') return;

          handleLiveEvent(data);
        } catch (e) {
          console.error('Failed to parse SSE event data:', e);
        }
      };

      evtSource.onerror = () => {
        if (streamStatus) {
          streamStatus.textContent = 'DISCONNECTED';
          streamStatus.className = 'val val-deny';
        }
      };
    } catch (err) {
      console.warn('SSE not supported or failed to connect:', err);
    }
  }

  function handleLiveEvent(data) {
    if (data.event_type === 'REALTIME_EMAIL_ANALYSIS') {
      if (realtimeEmailCard) {
        realtimeEmailCard.style.display = 'flex';
        if (realtimeSender) realtimeSender.textContent = data.sender || 'DESCONOCIDO';
        if (realtimeSubject) realtimeSubject.textContent = data.subject || 'SIN ASUNTO';
      }

      // Automatically hydrate risk assessment UI
      renderResults({
        signals: data.signals || {},
        risk_assessment: {
          level: data.risk_level || 'NORMAL',
          reasons: data.reasons || []
        },
        canary_decision: {
          decision: data.decision || 'DENY'
        },
        warning: data.headline ? { payload: { headline: data.headline, directives: ["SOLICITUD DE ALMACENAMIENTO FALSO", "NO HACER CLIC EN NINGÚN ENLACE", "BLOQUEAR REMITENTE"] } } : null,
        events: data.events || []
      });

      // Prepend event item into stream log
      const item = document.createElement('div');
      item.className = 'event-item evt-warning';
      const now = new Date().toTimeString().split(' ')[0];
      item.innerHTML = `
        <span class="evt-time">[${now}]</span>
        <span class="evt-type">REALTIME_EMAIL_PHISHING</span>
        <span class="evt-payload">From: ${data.sender} | Subject: ${data.subject} | Risk: ${data.risk_level}</span>
      `;
      if (eventStream.querySelector('.event-empty')) {
        eventStream.innerHTML = '';
      }
      eventStream.prepend(item);
    }
  }

  // Hydrate initial recent events if any
  fetch('/api/v1/events/recent')
    .then(res => res.json())
    .then(data => {
      if (data.events && data.events.length > 0) {
        const lastEvt = data.events[data.events.length - 1];
        handleLiveEvent(lastEvt);
      }
    })
    .catch(() => {});

  initRealtimeStream();
});
