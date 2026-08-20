/**
 * Guardian Call — Tactical Telemetry & Event Visualizer App Script
 * Connects frontend UI to FastAPI backend endpoints (/api/v1/analyze).
 */

document.addEventListener('DOMContentLoaded', () => {
  const sysClock = document.getElementById('sys-clock');
  const inputText = document.getElementById('input-text');
  
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  
  const btnPresetOtp = document.getElementById('btn-preset-otp');
  const btnPresetLegit = document.getElementById('btn-preset-legit');
  const btnPresetFailsafe = document.getElementById('btn-preset-failsafe');
  
  const valRiskLevel = document.getElementById('val-risk-level');
  const valCanaryDecision = document.getElementById('val-canary-decision');
  const listRiskReasons = document.getElementById('list-risk-reasons');
  
  const userWarningBanner = document.getElementById('user-warning-banner');
  const warningHeadline = document.getElementById('warning-headline');
  const warningDirectives = document.getElementById('warning-directives');
  
  const signalsGrid = document.getElementById('signals-grid');
  const eventStream = document.getElementById('event-stream');

  // Preset Scenario Strings
  const PRESETS = {
    otp: "Hola, le llamamos del departamento de seguridad del banco. Detectamos un intento de transferencia sospechoso de 450 euros. Para cancelarlo inmediatamente, dígame el código de verificación de 6 dígitos que le acabamos de enviar por SMS.",
    legit: "Buenos días, le llamamos de Centro Médico Sanitas para confirmar su cita de mañana a las 10:00 AM con el Dr. García. Recuerde traer su documento de identidad y tarjeta sanitaria.",
    failsafe: "FAILSAFE_TEST_TRIGGER_API_SIMULATION"
  };

  // 1. Clock Update
  function updateClock() {
    const now = new Date();
    sysClock.textContent = now.toUTCString().split(' ')[4] + ' UTC';
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Scenario Presets
  btnPresetOtp?.addEventListener('click', () => {
    inputText.value = PRESETS.otp;
  });

  btnPresetLegit?.addEventListener('click', () => {
    inputText.value = PRESETS.legit;
  });

  btnPresetFailsafe?.addEventListener('click', () => {
    inputText.value = PRESETS.failsafe;
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
      alert(`[ESCÁNER IMAP COMPLETADO] Se analizaron ${data.count} correo(s) de tu bandeja de entrada.`);

    } catch (err) {
      console.error('Inbox scan failed:', err);
      alert(`Error de escaneo IMAP: ${err.message}`);
    } finally {
      btnScanInbox.disabled = false;
      btnScanInbox.textContent = '[ 📩 ESCANEAR BANDEJA DE ENTRADA (IMAP) ]';
    }
  });

  // 5. Render Analysis Results
  function renderResults(data) {
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

    // Render Event Stream Trail
    eventStream.innerHTML = '';
    if (events && events.length > 0) {
      events.forEach(evt => {
        const item = document.createElement('div');
        let evtClass = '';
        if (evt.event_type === 'USER_WARNING') evtClass = 'evt-warning';
        else if (evt.event_type === 'ACTION_ALLOWED') evtClass = 'evt-allowed';
        else if (evt.event_type === 'ACTION_DENIED') evtClass = 'evt-denied';
        else if (evt.event_type === 'SIGNAL_EXTRACTION_FAILED') evtClass = 'evt-failed';

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
