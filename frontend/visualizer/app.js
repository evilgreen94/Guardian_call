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
  const inputText = document.getElementById('input-text');
  const inputState = document.getElementById('input-state');
  const headerSession = document.getElementById('header-session');
  const headerInput = document.getElementById('header-input');
  const headerProvider = document.getElementById('header-provider');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnClear = document.getElementById('btn-clear');
  const sttLanguage = document.getElementById('stt-language');
  const sttState = document.getElementById('stt-state');
  const btnRecordStart = document.getElementById('btn-record-start');
  const btnRecordStop = document.getElementById('btn-record-stop');
  const scenarioSelect = document.getElementById('scenario-select');
  const expectedRiskTag = document.getElementById('expected-risk-tag');

  const rail = document.getElementById('pipeline-rail');
  const railState = document.getElementById('rail-state');
  const pipeCallState = document.getElementById('pipe-call-state');
  const pipeGeminiState = document.getElementById('pipe-gemini-state');
  const pipeRiskState = document.getElementById('pipe-risk-state');
  const pipeCanaryState = document.getElementById('pipe-canary-state');
  const pipeActionState = document.getElementById('pipe-action-state');
  const analysisState = document.getElementById('analysis-state');
  const vmSessionId = document.getElementById('vm-session-id');
  const vmInputSource = document.getElementById('vm-input-source');
  const vmSourceTurn = document.getElementById('vm-source-turn');
  const vmAppliedTurn = document.getElementById('vm-applied-turn');
  const vmExtractionStatus = document.getElementById('vm-extraction-status');
  const vmLossStatus = document.getElementById('vm-loss-status');
  const failureBanner = document.getElementById('failure-banner');
  const riskRail = document.getElementById('risk-rail');
  const vmCurrentRisk = document.getElementById('vm-current-risk');
  const vmPeakRisk = document.getElementById('vm-peak-risk');
  const vmRiskMotion = document.getElementById('vm-risk-motion');
  const vmPolicyEvent = document.getElementById('vm-policy-event');
  const policyEventType = document.getElementById('policy-event-type');
  const policyDuplicate = document.getElementById('policy-duplicate');
  const policySuppression = document.getElementById('policy-suppression');
  const canaryEvaluated = document.getElementById('canary-evaluated');

  const riskLevelReadout = document.getElementById('risk-level-readout');
  const riskDominant = document.getElementById('risk-dominant');
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
  const liveSessionId = `m2-5-stt-${Date.now().toString(36)}`;
  let sourceTurnNumber = 0;
  let mediaRecorder = null;
  let recordingStream = null;
  let recordingChunks = [];
  let recordingTimer = null;
  let lastCanaryViewModel = null;
  let lastSTTMeta = null;
  const MAX_RECORDING_MS = 15000;
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

  function setSTTStatus(text) {
    setText(sttState, text);
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

  function valueOrDash(value) {
    return value === null || value === undefined || value === '' ? '-' : String(value);
  }

  function classifyRiskMotion(policy) {
    if (!policy) return '-';
    if (policy.risk_increased === true) return 'INCREASED';
    if (policy.risk_increased === false) return 'STABLE/NO NEW INCREASE';
    return '-';
  }

  function canaryWasEvaluated(canary) {
    return !!canary && canary.status && canary.status !== 'NOT_REQUESTED';
  }

  function buildCanaryViewModel(data, inputSource, transcript) {
    const turn = data && data.turn ? data.turn : null;
    const policy = turn && turn.policy_event ? turn.policy_event : null;
    const canary = turn && turn.canary_authorization ? turn.canary_authorization : null;
    const extracted = turn && turn.extracted_v2_summary ? turn.extracted_v2_summary : null;
    const normalized = turn && turn.normalized_m2_summary ? turn.normalized_m2_summary : null;
    const failed = !turn || turn.status === 'EXTRACTION_FAILED' || turn.status === 'UNSUPPORTED_MAPPING' || !!data.error;
    const unchangedRisk = failed && turn ? {
      current: turn.current_risk,
      peak: turn.peak_risk,
    } : null;

    return {
      input: {
        source: inputSource,
        transcript,
        stt: inputSource === 'VOICE' ? lastSTTMeta : null,
      },
      turn: {
        session_id: turn ? turn.session_id : liveSessionId,
        source_turn_number: turn ? turn.source_turn_number : sourceTurnNumber,
        applied_m2_turn_number: turn ? turn.applied_m2_turn_number : null,
        status: turn ? turn.status : 'FAILED',
      },
      extraction: {
        status: turn ? turn.status : 'FAILED',
        provenance: extracted ? extracted.provenance : null,
        v2_signals: extracted ? extracted.signals : null,
        extractor_error: turn ? turn.extractor_error : data.error,
        mapping_error: turn ? turn.mapping_error : null,
        representational_losses: turn ? turn.representational_losses || [] : [],
      },
      evidence: {
        normalized_m2_summary: normalized,
      },
      risk: {
        current_risk: turn ? turn.current_risk : (lastCanaryViewModel ? lastCanaryViewModel.risk.current_risk : null),
        peak_risk: turn ? turn.peak_risk : (lastCanaryViewModel ? lastCanaryViewModel.risk.peak_risk : null),
        unchanged: unchangedRisk,
        risk_increased: policy ? policy.risk_increased : null,
        reasons: policy ? policy.reasons || [] : [],
      },
      policy: {
        event_type: policy ? policy.event_type : null,
        duplicate_suppressed: policy ? policy.duplicate_suppressed : null,
        suppression_reason: policy ? policy.suppression_reason : null,
        canary_action: policy ? policy.canary_action : null,
        canary_decision: policy ? policy.canary_decision : null,
        canary_reason: policy ? policy.canary_reason : null,
        active_factor_count: policy ? policy.active_factor_count : null,
        new_factor_count: policy ? policy.new_factor_count : null,
      },
      canary: {
        evaluated: canaryWasEvaluated(canary),
        status: canary ? canary.status : null,
        action: canary ? canary.action : null,
        reason: canary ? canary.reason : null,
        risk_level: canary ? canary.risk_level : null,
      },
      failure: failed,
    };
  }

  function buildSTTFailureViewModel(error, languageHint) {
    return {
      input: {
        source: 'VOICE',
        transcript: inputText.value.trim() || null,
        stt: {
          status: 'FAILED',
          language_hint: languageHint,
          error,
        },
      },
      turn: {
        session_id: liveSessionId,
        source_turn_number: null,
        applied_m2_turn_number: null,
        status: 'STT_FAILED',
      },
      extraction: {
        status: 'NOT_RUN',
        provenance: null,
        v2_signals: null,
        extractor_error: null,
        mapping_error: null,
        representational_losses: [],
      },
      evidence: {
        normalized_m2_summary: null,
      },
      risk: {
        current_risk: lastCanaryViewModel ? lastCanaryViewModel.risk.current_risk : null,
        peak_risk: lastCanaryViewModel ? lastCanaryViewModel.risk.peak_risk : null,
        unchanged: lastCanaryViewModel ? {
          current: lastCanaryViewModel.risk.current_risk,
          peak: lastCanaryViewModel.risk.peak_risk,
        } : null,
        risk_increased: null,
        reasons: [],
      },
      policy: {
        event_type: null,
        duplicate_suppressed: null,
        suppression_reason: null,
        canary_action: null,
        canary_decision: null,
        canary_reason: null,
        active_factor_count: null,
        new_factor_count: null,
      },
      canary: {
        evaluated: false,
        status: 'NOT_REQUESTED',
        action: null,
        reason: 'STT failed before canonical text turn submission.',
        risk_level: lastCanaryViewModel ? lastCanaryViewModel.risk.current_risk : null,
      },
      failure: true,
    };
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
    setText(pipeRiskState, '-');
    setClass(pipeRiskState, 'state', 'state-muted');
    setText(pipeCanaryState, 'DENY');
    setClass(pipeCanaryState, 'state', 'state-deny');
    setText(pipeActionState, '-');
    setText(analysisState, 'AWAITING TURN');
    setText(headerSession, liveSessionId);
    setText(headerInput, '-');
    setText(headerProvider, '-');
    setText(vmSessionId, liveSessionId);
    setText(vmInputSource, '-');
    setText(vmSourceTurn, '-');
    setText(vmAppliedTurn, '-');
    setText(vmExtractionStatus, '-');
    setText(vmLossStatus, '-');
    failureBanner?.classList.remove('failure-banner-active');
    setText(vmCurrentRisk, '-');
    setText(vmPeakRisk, '-');
    setText(riskDominant, 'NO ASSESSMENT');
    setClass(riskDominant, 'state risk-dominant-value', 'state-muted');
    setText(vmRiskMotion, '-');
    setText(vmPolicyEvent, '-');
    setText(policyEventType, '-');
    setText(policyDuplicate, '-');
    setText(policySuppression, '-');
    setText(canaryEvaluated, 'NOT EVALUATED');
    updateRiskRail(null);
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
    setText(canaryReason, 'No KERN-3 evaluation recorded.');
  }

  function resetWarning() {
    warningInterrupt?.classList.remove('warning-interrupt-active');
    warningInterrupt?.classList.remove('warning-sync');
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
    appendLogRow('00:00:00', 'SYSTEM_READY', 'Awaiting client-observed REST/STT lifecycle events.');
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
    const currentRisk = riskAssessment.current_risk || riskAssessment.level || 'NORMAL';
    const peakRisk = riskAssessment.peak_risk || currentRisk;
    setText(pipeRiskState, currentRisk);
    setClass(pipeRiskState, 'state', classForRisk(currentRisk));
    setText(riskLevelReadout, currentRisk);
    setClass(riskLevelReadout, 'state', classForRisk(currentRisk));
    setText(riskDominant, currentRisk);
    setClass(riskDominant, 'state risk-dominant-value', classForRisk(currentRisk));
    setText(vmCurrentRisk, currentRisk);
    setText(vmPeakRisk, peakRisk);
    updateRiskRail(currentRisk);
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

  function renderV2Signals(summary) {
    signalRegisterBody.textContent = '';
    if (!summary) {
      resetRegister();
      return;
    }
    const rows = [];
    rows.push(['V2 IDENTITY', (summary.identity_claims || []).join(', ')]);
    rows.push(['V2 CONTEXT', (summary.contexts || []).join(', ')]);
    rows.push(['V2 MANIPULATION', (summary.manipulation || []).join(', ')]);
    (summary.interaction_acts || []).forEach((act, index) => {
      const asset = act.asset ? act.asset.subtype : 'NO_ASSET';
      rows.push([
        `V2 ACT ${String(index + 1).padStart(2, '0')}`,
        `${act.actor} -- ${act.action} / ${asset} --> ${act.destination} [${act.semantic_direction}]`,
      ]);
    });
    rows.forEach(([field, value]) => {
      const asserted = isAsserted(value);
      const row = document.createElement('div');
      row.className = 'signal-row';

      const mark = document.createElement('span');
      mark.className = `signal-mark ${asserted ? 'state-asserted' : 'state-cleared'}`;
      mark.textContent = asserted ? '\u25a0' : '.';

      const key = document.createElement('span');
      key.textContent = field;

      const val = document.createElement('span');
      val.textContent = value || '-';

      row.append(mark, key, val);
      signalRegisterBody.appendChild(row);
    });
  }

  function renderEvidence(vm) {
    const signals = vm.extraction.v2_signals;
    const normalized = vm.evidence.normalized_m2_summary;
    signalRegisterBody.textContent = '';
    if (!signals && !normalized) {
      resetRegister();
      return;
    }

    const appendSection = (title, rows) => {
      const section = document.createElement('section');
      section.className = 'evidence-section';
      const heading = document.createElement('h3');
      heading.textContent = title;
      section.appendChild(heading);
      if (!rows.length) {
        const empty = document.createElement('p');
        empty.className = 'empty';
        empty.textContent = '-';
        section.appendChild(empty);
      }
      rows.forEach(([field, value, className = 'evidence-row']) => {
        const row = document.createElement('div');
        row.className = className;

        const key = document.createElement('span');
        key.textContent = field;

        const val = document.createElement('span');
        val.textContent = value || '-';

        row.append(key, val);
        section.appendChild(row);
      });
      signalRegisterBody.appendChild(section);
    };

    if (signals) {
      appendSection('EXTRACTED V2 SEMANTICS', [
        ['IDENTITY', (signals.identity_claims || []).join(', ')],
        ['CONTEXT', (signals.contexts || []).join(', ')],
      ]);
      appendSection('EXTRACTED INTERACTION ACTS', (signals.interaction_acts || []).map((act, index) => {
        const asset = act.asset ? act.asset.subtype : 'NO_ASSET';
        return [
          `V2 ${String(index + 1).padStart(2, '0')}`,
          `${act.actor} ── ${act.action} / ${asset} ──► ${act.destination} [${act.semantic_direction}]`,
          'semantic-act',
        ];
      }));
      appendSection('PRESSURE / MANIPULATION', [
        ['V2', (signals.manipulation || []).join(', ')],
      ]);
    }
    if (normalized) {
      appendSection('NORMALIZED M2 CONTEXT', [
        ['CLAIMS', (normalized.identity_claims || []).map((claim) => `${claim.claim} [${claim.scope}]`).join(', ')],
        ['CONTEXTS', (normalized.contexts || []).map((context) => `${context.context} [${context.scope}]`).join(', ')],
        ['MANIPULATION', (normalized.manipulations || []).map((item) => `${item.manipulation} [${item.scope}]`).join(', ')],
      ]);
      appendSection('NORMALIZED M2 ACTS', (normalized.acts || []).map((act, index) => [
        `M2 ${String(index + 1).padStart(2, '0')}`,
          `${act.actor} ── ${act.action} / ${act.asset || 'NO_ASSET'} ──► ${act.destination} [${act.scope}]`,
          'semantic-act semantic-act-normalized',
      ]));
    }
    appendSection('REPRESENTATIONAL LOSSES', (vm.extraction.representational_losses || []).map((loss, index) => [
        `LOSS ${String(index + 1).padStart(2, '0')}`,
        [loss.source_value, loss.disposition, loss.source_enum].filter(Boolean).join(' / '),
        'loss-row',
    ]));
  }

  function updateRiskRail(level) {
    if (!riskRail) return;
    const current = String(level || '').toUpperCase();
    riskRail.querySelectorAll('[data-risk]').forEach((item) => {
      item.classList.toggle('risk-active', !!current && item.getAttribute('data-risk') === current);
    });
  }

  function renderCanaryViewModel(vm) {
    const currentRisk = vm.risk.current_risk || '-';
    const peakRisk = vm.risk.peak_risk || '-';
    const policyDecision = vm.canary.status || 'NOT_REQUESTED';
    const lossCount = vm.extraction.representational_losses.length;
    const lossSummary = lossCount > 0
      ? vm.extraction.representational_losses
          .map((loss) => [loss.source_value, loss.disposition].filter(Boolean).join(' / '))
          .join(' | ')
      : 'NONE';
    const hasPreservedRisk = vm.failure && !!vm.risk.unchanged && !!vm.risk.unchanged.current;
    const dominantRiskLabel = hasPreservedRisk
      ? 'PRESERVED STATE'
      : vm.failure
        ? 'NO ASSESSMENT'
        : currentRisk;
    const dominantRiskClass = hasPreservedRisk
      ? 'state-eval'
      : vm.failure
        ? 'state-muted'
        : classForRisk(currentRisk);
    const provider = vm.input.stt
      ? `${vm.input.stt.provider}/${vm.input.stt.requested_model}`
      : vm.extraction.provenance
        ? `${vm.extraction.provenance.provider}/${vm.extraction.provenance.requested_model}`
        : '-';

    setText(inputState, vm.failure ? 'ANALYSIS UNAVAILABLE' : vm.turn.status);
    setText(analysisState, vm.failure ? 'STATE PRESERVED' : 'ANALYSIS RETURNED');
    setText(headerSession, valueOrDash(vm.turn.session_id));
    setText(headerInput, valueOrDash(vm.input.source));
    setText(headerProvider, provider);
    setText(vmSessionId, valueOrDash(vm.turn.session_id));
    setText(vmInputSource, valueOrDash(vm.input.source));
    setText(vmSourceTurn, valueOrDash(vm.turn.source_turn_number));
    setText(vmAppliedTurn, valueOrDash(vm.turn.applied_m2_turn_number));
    setText(vmExtractionStatus, valueOrDash(vm.extraction.status));
    setText(vmLossStatus, lossSummary);

    failureBanner?.classList.toggle('failure-banner-active', vm.failure);

    setText(pipeCallState, vm.turn.source_turn_number ? `S${vm.turn.source_turn_number}` : '-');
    setText(pipeGeminiState, vm.failure ? 'FAIL' : 'EXTRACTED');
    setClass(pipeGeminiState, 'state', vm.failure ? 'state-error' : 'state-ok');
    setText(pipeRiskState, currentRisk);
    setClass(pipeRiskState, 'state', classForRisk(currentRisk));
    setText(pipeCanaryState, policyDecision);
    setClass(pipeCanaryState, 'state', classForDecision(policyDecision));

    setText(riskLevelReadout, currentRisk);
    setClass(riskLevelReadout, 'state', classForRisk(currentRisk));
    setText(riskDominant, dominantRiskLabel);
    setClass(riskDominant, 'state risk-dominant-value', dominantRiskClass);
    setText(vmCurrentRisk, currentRisk);
    setText(vmPeakRisk, peakRisk);
    setText(vmRiskMotion, classifyRiskMotion(vm.policy));
    updateRiskRail(vm.failure ? null : currentRisk);
    renderReasons(vm.failure ? ['NOT A NEW SAFETY VERDICT'] : vm.risk.reasons);

    const factorSummary = [
      `active_factors=${valueOrDash(vm.policy.active_factor_count)}`,
      `new_factors=${valueOrDash(vm.policy.new_factor_count)}`,
      `losses=${lossCount}`,
      `canary=${policyDecision}`,
    ];
    if (vm.risk.unchanged) {
      factorSummary.push(`preserved_current=${valueOrDash(vm.risk.unchanged.current)}`);
      factorSummary.push(`preserved_peak=${valueOrDash(vm.risk.unchanged.peak)}`);
    }
    setText(contributingSignals, factorSummary.join('  '));

    renderEvidence(vm);

    setText(vmPolicyEvent, valueOrDash(vm.policy.event_type));
    setText(policyEventType, valueOrDash(vm.policy.event_type));
    setText(policyDuplicate, vm.policy.duplicate_suppressed === null ? '-' : String(vm.policy.duplicate_suppressed).toUpperCase());
    setText(policySuppression, valueOrDash(vm.policy.suppression_reason));

    setText(canaryEvaluated, vm.canary.evaluated ? 'EVALUATED' : 'NOT REQUESTED');
    setText(canaryAction, vm.canary.evaluated ? valueOrDash(vm.canary.action) : '-');
    setText(canaryDecision, policyDecision);
    setClass(canaryDecision, 'state', classForDecision(policyDecision));
    setText(canaryRiskLevel, valueOrDash(vm.canary.risk_level || currentRisk));
    setText(canaryReason, valueOrDash(vm.canary.reason));

    if (vm.canary.evaluated && policyDecision === 'ALLOW' && vm.canary.action === 'warn_user') {
      setText(pipeActionState, 'USER_WARNING');
      setRailPoint('action');
      warningInterrupt?.classList.add('warning-interrupt-active');
      warningInterrupt?.classList.add('warning-sync');
      warningInterrupt?.setAttribute('aria-hidden', 'false');
      setText(placardHeadline, `AUTHORIZATION: ${policyDecision}`);
      placardDirectives.textContent = '';
      [
        `ACTION  ${vm.canary.action}`,
        `RISK    ${valueOrDash(vm.canary.risk_level || currentRisk)}`,
        `REASON  ${valueOrDash(vm.canary.reason)}`,
      ].forEach((directive) => {
        const line = document.createElement('output');
        line.className = 'directive-line';
        line.textContent = directive;
        placardDirectives.appendChild(line);
      });
      setTimeout(() => warningInterrupt?.classList.remove('warning-sync'), 520);
    } else {
      setText(pipeActionState, '-');
      setRailPoint(vm.failure ? 'denied' : 'crossed');
      resetWarning();
    }
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
    while (eventStreamTerminal.children.length > 40) {
      eventStreamTerminal.removeChild(eventStreamTerminal.firstElementChild);
    }
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
      setText(railState, 'KERN-3 EVALUATION');
      setRailPoint('canary');
      renderCanary(payload);
    } else if (evt.event_type === 'ACTION_ALLOWED') {
      setText(railState, 'KERN-3 ALLOW - BOUNDARY CROSSED');
      setRailPoint('crossed');
    } else if (evt.event_type === 'ACTION_DENIED') {
      setText(railState, 'KERN-3 DENY - BOUNDARY STOP');
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

  async function submitTurnText(text, inputSource = 'TEXT') {
    const trimmed = String(text || '').trim();
    if (!trimmed) {
      alert('Please enter call text or load a test tape.');
      return;
    }

    sourceTurnNumber += 1;
    resetWorkstation({ clearInput: false, clearScenario: false });
    setPendingExtractionState();
    appendLogRow(eventTime(), 'TURN_TEXT_SUBMITTED', `source=${inputSource} source_turn=${sourceTurnNumber}`);
    btnAnalyze.disabled = true;
    btnAnalyze.textContent = 'RUNNING';

    try {
      const response = await fetch('/api/v1/experimental/v2/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: trimmed,
          session_id: liveSessionId,
          source_turn_number: sourceTurnNumber,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      const vm = buildCanaryViewModel(data, inputSource, trimmed);
      renderCanaryViewModel(vm);
      if (!vm.failure) {
        lastCanaryViewModel = vm;
      }
      appendLogRow(eventTime(), 'V2_TURN_RESULT', `status=${data.status || '-'} source_turn=${sourceTurnNumber}`);
      appendLogRow(eventTime(), 'RISK_RESULT', `current=${valueOrDash(vm.risk.current_risk)} peak=${valueOrDash(vm.risk.peak_risk)}`);
      appendLogRow(eventTime(), 'KERN3_RESULT', `status=${valueOrDash(vm.canary.status)} action=${valueOrDash(vm.canary.action)}`);
    } catch (err) {
      console.error('Pipeline execution error:', err);
      alert(`Pipeline error: ${err.message}`);
      setText(inputState, 'ERROR');
      renderCanaryViewModel(buildCanaryViewModel({ error: { kind: 'REQUEST_FAILED', message: err.message } }, inputSource, trimmed));
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyze.textContent = 'EXECUTE ANALYSIS';
    }
  }

  btnAnalyze?.addEventListener('click', async () => {
    const text = inputText.value.trim();
    if (!text) {
      alert('Please enter call text or load a test tape.');
      return;
    }
    await submitTurnText(text, 'TEXT');
  });

  function clearRecordingTimer() {
    if (recordingTimer) {
      clearTimeout(recordingTimer);
      recordingTimer = null;
    }
  }

  function stopRecordingTracks() {
    if (recordingStream) {
      recordingStream.getTracks().forEach((track) => track.stop());
      recordingStream = null;
    }
  }

  function audioBlobToBase64(blob) {
    return blob.arrayBuffer().then((buffer) => {
      const bytes = new Uint8Array(buffer);
      let binary = '';
      const chunkSize = 8192;
      for (let offset = 0; offset < bytes.length; offset += chunkSize) {
        const chunk = bytes.subarray(offset, offset + chunkSize);
        binary += String.fromCharCode(...chunk);
      }
      return btoa(binary);
    });
  }

  async function submitAudioBlob(blob) {
    setSTTStatus('TRANSCRIBING');
    btnRecordStart.disabled = true;
    btnRecordStop.disabled = true;
    try {
      const response = await fetch('/api/v1/experimental/stt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio_base64: await audioBlobToBase64(blob),
          mime_type: blob.type || 'audio/webm',
          language_hint: sttLanguage?.value || 'auto',
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.status !== 'TRANSCRIBED' || !data.transcript) {
        const failure = data.error && data.error.kind ? data.error.kind : 'STT_FAILED';
        setSTTStatus(failure);
        appendLogRow(eventTime(), 'STT_FAILED', `kind=${failure}`);
        renderCanaryViewModel(buildSTTFailureViewModel(data.error || { kind: failure }, sttLanguage?.value || 'auto'));
        return;
      }
      setSTTStatus('TRANSCRIBED');
      lastSTTMeta = {
        status: data.status,
        provider: data.provider,
        requested_model: data.requested_model,
        language_hint: data.language_hint,
        audio_bytes: data.audio_bytes,
      };
      inputText.value = data.transcript;
      appendLogRow(eventTime(), 'STT_TRANSCRIBED', `language=${data.language_hint || 'auto'} bytes=${data.audio_bytes || 0}`);
      await submitTurnText(data.transcript, 'VOICE');
    } catch (err) {
      console.error('STT execution error:', err);
      setSTTStatus('STT ERROR');
      appendLogRow(eventTime(), 'STT_FAILED', err.message || 'STT error');
      renderCanaryViewModel(buildSTTFailureViewModel({ kind: 'REQUEST_FAILED', message: err.message }, sttLanguage?.value || 'auto'));
    } finally {
      btnRecordStart.disabled = false;
      btnRecordStop.disabled = true;
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === 'undefined') {
      setSTTStatus('UNAVAILABLE');
      return;
    }
    try {
      recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingChunks = [];
      mediaRecorder = new MediaRecorder(recordingStream);
      mediaRecorder.addEventListener('dataavailable', (event) => {
        if (event.data && event.data.size > 0) recordingChunks.push(event.data);
      });
      mediaRecorder.addEventListener('stop', async () => {
        clearRecordingTimer();
        stopRecordingTracks();
        const blob = new Blob(recordingChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
        recordingChunks = [];
        await submitAudioBlob(blob);
      }, { once: true });
      mediaRecorder.start();
      setSTTStatus('RECORDING');
      btnRecordStart.disabled = true;
      btnRecordStop.disabled = false;
      recordingTimer = setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
      }, MAX_RECORDING_MS);
    } catch (err) {
      console.error('Microphone capture error:', err);
      setSTTStatus('MIC FAILED');
      stopRecordingTracks();
      btnRecordStart.disabled = false;
      btnRecordStop.disabled = true;
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
  }

  btnRecordStart?.addEventListener('click', startRecording);
  btnRecordStop?.addEventListener('click', stopRecording);

  resetWorkstation();
  loadScenarios();
  initSSE();
});
