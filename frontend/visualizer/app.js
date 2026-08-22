/**
 * Guardian Call — Minimal Observability & Telemetry Visualizer App
 * Connects frontend UI to FastAPI backend endpoints and real-time SSE stream.
 */

document.addEventListener('DOMContentLoaded', () => {
  const sysClock = document.getElementById('sys-clock');
  const streamStatus = document.getElementById('stream-status');
  const inputText = document.getElementById('input-text');
  
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  
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

  let scenarios = {};

  // 1. Live UTC Clock
  function updateClock() {
    const now = new Date();
    const timeStr = now.toISOString().split('T')[1].substring(0, 8);
    if (sysClock) sysClock.textContent = `${timeStr} UTC`;
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Load Scenarios from Backend
  async function loadScenarios() {
    try {
      const res = await fetch('/api/v1/scenarios');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      scenarios = {};
      scenarioSelect.innerHTML = '<option value="">[ SELECCIONA UN ESCENARIO... ]</option>';
      
      (data.scenarios || []).forEach(sc => {
        scenarios[sc.id] = sc;
        const opt = document.createElement('option');
        opt.value = sc.id;
        opt.textContent = sc.title;
        scenarioSelect.appendChild(opt);
      });
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

    inputText.value = (sc.dialogue || []).join(' ');
    if (sc.expected_final_risk) {
      scenarioRiskBadge.textContent = `RIESGO ESPERADO: ${sc.expected_final_risk}`;
      scenarioRiskBadge.className = `scenario-risk-badge visible risk-${sc.expected_final_risk.toLowerCase()}`;
    }
  });

  // 3. Clear / Reset Terminal
  btnClear?.addEventListener('click', () => {
    inputText.value = '';
    if (scenarioSelect) scenarioSelect.value = '';
    if (scenarioRiskBadge) {
      scenarioRiskBadge.textContent = '';
      scenarioRiskBadge.className = 'scenario-risk-badge';
    }
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
        <span class="evt-payload">Awaiting conversational input to stream pipeline domain events...</span>
      </div>
    `;
  }

  // 4. Render Extracted Results
  function renderResults(data) {
    const { signals, risk_assessment, canary_decision, warning, error } = data;

    if (error) {
      valRiskLevel.textContent = 'ERROR';
      valRiskLevel.className = 'card-value val-critical';
      listRiskReasons.innerHTML = `<li style="color: var(--color-red);">${error}</li>`;
      return;
    }

    // Render Risk Level
    const level = (risk_assessment && risk_assessment.level) || 'NORMAL';
    valRiskLevel.textContent = level;
    valRiskLevel.className = `card-value val-${level.toLowerCase()}`;

    // Render Canary Decision
    const decision = (canary_decision && canary_decision.decision) || 'DENY';
    valCanaryDecision.textContent = decision;
    valCanaryDecision.className = `card-value val-${decision.toLowerCase()}`;

    // Render Explainable Reasons
    listRiskReasons.innerHTML = '';
    const reasons = (risk_assessment && risk_assessment.reasons) || [];
    if (reasons.length > 0) {
      reasons.forEach(reason => {
        const li = document.createElement('li');
        li.textContent = reason;
        listRiskReasons.appendChild(li);
      });
    } else {
      listRiskReasons.innerHTML = '<li class="empty-state">No malicious manipulation signals detected.</li>';
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

    // Render Scam Signals Matrix
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
  }

  // 5. Append Real SSE Domain Event to Event Stream Trail
  function appendDomainEvent(evt) {
    if (!evt || !evt.event_type) return;
    if (evt.event_type === 'STREAM_CONNECTED') return;

    // Remove empty placeholder on first event
    const emptyPlaceholder = eventStream.querySelector('.event-empty');
    if (emptyPlaceholder) {
      emptyPlaceholder.remove();
    }

    const item = document.createElement('div');
    let evtClass = '';
    
    if (evt.event_type === 'USER_WARNING') evtClass = 'evt-warning';
    else if (evt.event_type === 'ACTION_ALLOWED') evtClass = 'evt-allowed';
    else if (evt.event_type === 'ACTION_DENIED') evtClass = 'evt-denied';
    else if (evt.event_type === 'EXTRACTION_FAILED') evtClass = 'evt-failed';
    else if (evt.event_type === 'RISK_UPDATED') evtClass = 'evt-risk';
    else if (evt.event_type === 'SIGNAL_DETECTED') evtClass = 'evt-signal';

    item.className = `event-item ${evtClass}`;

    const rawTime = evt.timestamp || new Date().toISOString();
    const timeStr = rawTime.includes('T') ? rawTime.split('T')[1].split('.')[0] : '00:00:00';

    item.innerHTML = `
      <span class="evt-time">[${timeStr}]</span>
      <span class="evt-type">${evt.event_type}</span>
      <span class="evt-payload">${JSON.stringify(evt.payload || {})}</span>
    `;

    eventStream.appendChild(item);
    eventStream.scrollTop = eventStream.scrollHeight;
  }

  // 6. Connect to SSE Stream
  function initSSE() {
    try {
      const evtSource = new EventSource('/api/v1/events/stream');

      evtSource.onopen = () => {
        if (streamStatus) {
          streamStatus.textContent = 'LIVE';
          streamStatus.className = 'val val-ok';
        }
      };

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          appendDomainEvent(data);
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      };

      evtSource.onerror = () => {
        if (streamStatus) {
          streamStatus.textContent = 'DISCONNECTED';
          streamStatus.className = 'val val-deny';
        }
      };
    } catch (err) {
      console.warn('SSE stream connection failed:', err);
      if (streamStatus) {
        streamStatus.textContent = 'FAILED';
        streamStatus.className = 'val val-deny';
      }
    }
  }
  initSSE();

  // 7. Run Analysis Handler
  btnAnalyze?.addEventListener('click', async () => {
    const text = inputText.value.trim();
    if (!text) {
      alert('Por favor introduzca una transcripción conversacional o seleccione un escenario.');
      return;
    }

    btnAnalyze.disabled = true;
    btnAnalyze.textContent = '[ RUNNING PIPELINE... ]';

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
      renderResults(data);
    } catch (err) {
      console.error('Analysis execution failed:', err);
      alert(`Pipeline error: ${err.message}`);
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = '[ RUN ANALYSIS ]';
    }
  });

});
