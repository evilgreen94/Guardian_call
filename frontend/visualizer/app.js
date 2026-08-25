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
        groupAdv.label = `── BENCHMARK ADVERSARIAL & PROMPT INJECTION (${data.adversarial_count}) ──`;
        data.adversarial.forEach(sc => {
          scenarios[sc.id] = sc;
          const opt = document.createElement('option');
          opt.value = sc.id;
          opt.textContent = `[BENCHMARK] ${sc.title}`;
          groupAdv.appendChild(opt);
        });
        scenarioSelect.appendChild(groupAdv);
      }

      if (Object.keys(scenarios).length === 0 && data.scenarios && data.scenarios.length > 0) {
        const groupAll = document.createElement('optgroup');
        groupAll.label = `── TODOS LOS ESCENARIOS (${data.scenarios.length}) ──`;
        data.scenarios.forEach(sc => {
          scenarios[sc.id] = sc;
          const opt = document.createElement('option');
          opt.value = sc.id;
          opt.textContent = `${sc.title}`;
          groupAll.appendChild(opt);
        });
        scenarioSelect.appendChild(groupAll);
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

  // View Mode Toggles
  const btnViewTactical = document.getElementById('btn-view-tactical');
  const btnViewProtected = document.getElementById('btn-view-protected');
  const mainTacticalGrid = document.getElementById('main-tactical-grid');
  const protectedUserView = document.getElementById('protected-user-view');

  btnViewTactical?.addEventListener('click', () => {
    btnViewTactical.classList.add('active');
    btnViewProtected.classList.remove('active');
    mainTacticalGrid.style.display = 'grid';
    protectedUserView.style.display = 'none';
  });

  btnViewProtected?.addEventListener('click', () => {
    btnViewProtected.classList.add('active');
    btnViewTactical.classList.remove('active');
    mainTacticalGrid.style.display = 'none';
    protectedUserView.style.display = 'flex';
  });

  let selectedFile = null;
  const dropZone = document.getElementById('drop-zone');
  const imageInput = document.getElementById('image-input');
  const fileNameDisplay = document.getElementById('file-name');
  const imagePreviewBox = document.getElementById('image-preview-box');
  const previewImg = document.getElementById('preview-img');

  function updateImagePreview(file) {
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (previewImg) previewImg.src = e.target.result;
        if (imagePreviewBox) imagePreviewBox.style.display = 'block';
      };
      reader.readAsDataURL(file);
    } else if (imagePreviewBox) {
      imagePreviewBox.style.display = 'none';
    }
  }

  // File Dropzone handlers
  dropZone?.addEventListener('click', () => imageInput?.click());

  imageInput?.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      selectedFile = e.target.files[0];
      fileNameDisplay.textContent = `SELECTED FILE: ${selectedFile.name} (${Math.round(selectedFile.size / 1024)} KB)`;
      updateImagePreview(selectedFile);
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
      updateImagePreview(selectedFile);
    }
  });

  // 3. Clear Terminal
  btnClear?.addEventListener('click', () => {
    inputText.value = '';
    selectedFile = null;
    if (imageInput) imageInput.value = '';
    if (fileNameDisplay) fileNameDisplay.textContent = '';
    if (imagePreviewBox) imagePreviewBox.style.display = 'none';
    if (scenarioSelect) scenarioSelect.value = '';
    if (scenarioRiskBadge) {
      scenarioRiskBadge.textContent = '';
      scenarioRiskBadge.className = 'scenario-risk-badge';
    }
    if (typeof micActive !== 'undefined' && micActive && typeof recognition !== 'undefined') {
      try { recognition.stop(); } catch(e) {}
    }
    resetStatusDisplay();
  });

  // Stepper Execution Animation
  async function animateAgentStepper() {
    const stepper = document.getElementById('agent-stepper');
    if (!stepper) return;
    stepper.style.display = 'block';

    const steps = ['gemma', 'gemini', 'risk', 'canary'];
    for (const step of steps) {
      const el = document.getElementById(`step-${step}`);
      const st = document.getElementById(`status-${step}`);
      if (el && st) {
        el.className = 'step-item active';
        st.textContent = 'RUNNING...';
        await new Promise(r => setTimeout(r, 180));
        el.className = 'step-item done';
        st.textContent = 'OK';
      }
    }
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
      await animateAgentStepper();
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

    // Render Gemma Guardrail State
    const valGemmaGuardrail = document.getElementById('val-gemma-guardrail');
    if (valGemmaGuardrail) {
      const isInjection = signals ? Boolean(signals.prompt_injection_attempt) : false;
      const gemmaEvt = events ? events.find(e => e.event_type === 'GEMMA_GUARDRAIL_EVALUATED') : null;
      
      if (isInjection) {
        valGemmaGuardrail.textContent = 'ATTACK // BLOCKED';
        valGemmaGuardrail.className = 'card-value val-critical';
      } else if (gemmaEvt && gemmaEvt.payload && gemmaEvt.payload.passed === false) {
        valGemmaGuardrail.textContent = 'ATTACK // BLOCKED';
        valGemmaGuardrail.className = 'card-value val-critical';
      } else {
        valGemmaGuardrail.textContent = 'PASS // CLEAN';
        valGemmaGuardrail.className = 'card-value val-normal';
      }
    }

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

    // Render Protected User Warning Banner & Phone Mockup Mode
    const phoneWarningCard = document.getElementById('phone-warning-card');
    const phoneHeadline = document.getElementById('phone-headline');
    const phoneSubheadline = document.getElementById('phone-subheadline');
    const phoneDirectives = document.getElementById('phone-directives');

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

      if (phoneWarningCard) {
        phoneWarningCard.className = 'phone-warning-card';
        if (phoneHeadline) phoneHeadline.textContent = warning.payload.headline || 'POSIBLE ESTAFA';
        if (phoneSubheadline) phoneSubheadline.textContent = 'Guardian ha detectado un intento de estafa en tiempo real. Siga las instrucciones:';
        if (phoneDirectives) {
          phoneDirectives.innerHTML = '';
          directives.forEach(dir => {
            const div = document.createElement('div');
            div.className = 'directive-box';
            div.textContent = `🛑 ${dir}`;
            phoneDirectives.appendChild(div);
          });
        }
      }
    } else {
      userWarningBanner.style.display = 'none';
      if (phoneWarningCard) {
        phoneWarningCard.className = 'phone-warning-card safe';
        if (phoneHeadline) phoneHeadline.textContent = 'LLAMADA SEGURA';
        if (phoneSubheadline) phoneSubheadline.textContent = 'No se han detectado tácticas de ingeniería social ni señales de estafa.';
        if (phoneDirectives) {
          phoneDirectives.innerHTML = `
            <div class="directive-box ok">✓ Conversación limpia</div>
            <div class="directive-box ok">✓ Canal protegido</div>
          `;
        }
      }
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

  // 3. Live Audio WebSpeech Recognition & Real-Time Transcription
  const btnMicToggle = document.getElementById('btn-mic-toggle');
  const micStatus = document.getElementById('mic-status');
  const liveTranscriptionBox = document.getElementById('live-transcription-box');
  const liveTranscriptionContent = document.getElementById('live-transcription-content');
  
  let recognition = null;
  let isListening = false;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'es-ES';

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (liveTranscriptionBox) liveTranscriptionBox.style.display = 'block';
      const now = new Date().toTimeString().split(' ')[0];
      
      const fullText = (inputText.value + ' ' + finalTranscript).trim();
      if (finalTranscript) {
        inputText.value = fullText;
        const line = document.createElement('div');
        line.textContent = `[${now} - VOICE STREAM]: ${finalTranscript}`;
        if (liveTranscriptionContent.querySelector('.transcript-placeholder')) {
          liveTranscriptionContent.innerHTML = '';
        }
        liveTranscriptionContent.appendChild(line);
        liveTranscriptionContent.scrollTop = liveTranscriptionContent.scrollHeight;
      }
    };

    recognition.onerror = (evt) => {
      console.warn('Speech Recognition Error:', evt.error);
    };

    recognition.onend = () => {
      if (isListening) {
        try { recognition.start(); } catch (e) {}
      }
    };
  }

  btnMicToggle?.addEventListener('click', () => {
    if (!recognition) {
      alert('Tu navegador no soporta WebSpeech API. Por favor usa Chrome, Edge o Safari.');
      return;
    }

    if (!isListening) {
      isListening = true;
      try { recognition.start(); } catch (e) {}
      btnMicToggle.textContent = '[ 🔴 DETENER MIC ]';
      btnMicToggle.style.borderColor = 'var(--hazard-red)';
      btnMicToggle.style.color = 'var(--hazard-red)';
      micStatus.textContent = 'MIC: ESCUCHANDO Y TRANSCRIBIENDO';
      micStatus.style.color = 'var(--status-green)';
      if (liveTranscriptionBox) liveTranscriptionBox.style.display = 'block';
    } else {
      isListening = false;
      try { recognition.stop(); } catch (e) {}
      btnMicToggle.textContent = '[ 🎤 INICIAR MIC EN VIVO ]';
      btnMicToggle.style.borderColor = 'var(--panel-border)';
      btnMicToggle.style.color = 'var(--text-muted)';
      micStatus.textContent = 'MIC: INACTIVO';
      micStatus.style.color = 'var(--text-muted)';
    }
  });

  // 4. ScamTrap Panel & Event Hydration
  const scamtrapPanel = document.getElementById('scamtrap-panel');
  const stallingText = document.getElementById('stalling-text');
  const intelUrls = document.getElementById('intel-urls');
  const intelIbans = document.getElementById('intel-ibans');
  const btnCopyStalling = document.getElementById('btn-copy-stalling');

  btnCopyStalling?.addEventListener('click', () => {
    if (stallingText) {
      navigator.clipboard.writeText(stallingText.textContent);
      btnCopyStalling.textContent = '[ ¡COPIADO AL PORTAPAPELES! ]';
      setTimeout(() => {
        btnCopyStalling.textContent = '[ 📋 COPIAR RESPUESTA TÁCTICA ]';
      }, 2000);
    }
  });

  // Process ScamTrap events inside renderResults
  const origRenderResults = window.renderResults;
  window.renderResults = function(data) {
    if (typeof origRenderResults === 'function') {
      origRenderResults(data);
    }
    if (data && data.events) {
      const scamtrapEvt = data.events.find(e => e.event_type === 'SCAMTRAP_ACTIVATED');
      const intelEvt = data.events.find(e => e.event_type === 'INTELLIGENCE_EXTRACTED');
      if (scamtrapEvt && scamtrapPanel) {
        scamtrapPanel.style.display = 'block';
        if (intelEvt && intelEvt.payload) {
          if (stallingText && intelEvt.payload.stalling_response) {
            stallingText.textContent = `"${intelEvt.payload.stalling_response}"`;
          }
          if (intelUrls) {
            const urls = intelEvt.payload.extracted_phishing_urls || [];
            intelUrls.textContent = `URLs: ${urls.length > 0 ? urls.join(', ') : 'Ninguna'}`;
          }
          if (intelIbans) {
            const ibans = intelEvt.payload.extracted_ibans || [];
            intelIbans.textContent = `IBANs: ${ibans.length > 0 ? ibans.join(', ') : 'Ninguno'}`;
          }
        }
      }
    }
  };

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
