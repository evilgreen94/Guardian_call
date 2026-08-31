document.addEventListener('DOMContentLoaded', () => {
  const UX_STATES = Object.freeze({
    READY: 'READY',
    LISTENING: 'LISTENING',
    TRANSCRIBING: 'TRANSCRIBING',
    CHECKING: 'CHECKING',
    PROTECTED_NO_INTERVENTION: 'PROTECTED_NO_INTERVENTION',
    CAUTION: 'CAUTION',
    INTERVENTION: 'INTERVENTION',
    ANALYSIS_UNAVAILABLE: 'ANALYSIS_UNAVAILABLE',
  });

  const shell = document.querySelector('.guardian-shell');
  const livingCore = document.getElementById('living-core');
  const stateLabel = document.getElementById('state-label');
  const headline = document.getElementById('guardian-headline');
  const detail = document.getElementById('guardian-detail');
  const warningPanel = document.getElementById('warning-panel');
  const previewDisclaimer = document.getElementById('preview-disclaimer');
  const btnAckWarning = document.getElementById('btn-ack-warning');
  const btnRecordStart = document.getElementById('btn-record-start');
  const btnRecordStop = document.getElementById('btn-record-stop');
  const languageHint = document.getElementById('language-hint');
  const manualText = document.getElementById('manual-text');
  const btnSubmitText = document.getElementById('btn-submit-text');
  const btnReset = document.getElementById('btn-reset');
  const previewButtons = document.querySelectorAll('[data-preview-state]');
  const btnPreviewMic = document.getElementById('btn-preview-mic');
  const btnPreviewMicStop = document.getElementById('btn-preview-mic-stop');
  const btnPreviewCue = document.getElementById('btn-preview-cue');
  const uxState = document.getElementById('ux-state');
  const inputSource = document.getElementById('input-source');
  const sttState = document.getElementById('stt-state');
  const analysisState = document.getElementById('analysis-state');

  const MAX_RECORDING_MS = 15000;
  const liveSessionId = `guardian-${Date.now().toString(36)}`;
  let sourceTurnNumber = 0;
  let mediaRecorder = null;
  let recordingStream = null;
  let previewMicStream = null;
  let recordingChunks = [];
  let recordingTimer = null;
  let audioContext = null;
  let analyser = null;
  let amplitudeAnimation = null;
  let targetAmplitude = 0;
  let conversationActive = false;
  let lastValidatedViewModel = null;
  let lastInterventionKey = null;
  let lastHapticKey = null;
  let guardianVisual = null;
  const reduceMotionQuery = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

  function setText(element, value) {
    if (element) element.textContent = value;
  }

  function showRecordingAction(action) {
    if (btnRecordStart) {
      btnRecordStart.hidden = action !== 'start';
      btnRecordStart.disabled = action !== 'start';
    }
    if (btnRecordStop) {
      btnRecordStop.hidden = action !== 'stop';
      btnRecordStop.disabled = action !== 'stop';
    }
  }

  function setGuardianState(nextState) {
    if (shell) shell.dataset.state = nextState;
    setPresenceState(nextState);
    guardianVisual?.setState(nextState);
    setText(uxState, humanStateLabel(nextState));
  }

  function setPresenceState(nextState) {
    if (livingCore) livingCore.dataset.presenceState = nextState;
  }

  function setPresenceAmplitude(value) {
    guardianVisual?.setActivity(value);
    if (reduceMotionQuery && reduceMotionQuery.matches) return;
    if (livingCore) livingCore.style.setProperty('--presence-energy', String(Math.max(0, Math.min(1, value || 0)).toFixed(3)));
  }

  function triggerPresenceIntervention() {
    guardianVisual?.triggerSignal();
    if (!livingCore) return;
    livingCore.classList.remove('presence-intervention-pulse');
    void livingCore.offsetWidth;
    livingCore.classList.add('presence-intervention-pulse');
  }

  function setConversationActive(active) {
    conversationActive = active;
    if (shell) shell.dataset.mode = active ? 'conversation' : 'entry';
  }

  function humanStateLabel(nextState) {
    if (nextState === UX_STATES.LISTENING) return 'Listening';
    if (nextState === UX_STATES.TRANSCRIBING) return 'Transcribing';
    if (nextState === UX_STATES.CHECKING) return 'Checking';
    if (nextState === UX_STATES.PROTECTED_NO_INTERVENTION) return 'Protected';
    if (nextState === UX_STATES.CAUTION) return 'Pause and verify';
    if (nextState === UX_STATES.INTERVENTION) return 'Stop and check';
    if (nextState === UX_STATES.ANALYSIS_UNAVAILABLE) return 'Could not check';
    return 'Ready';
  }

  function humanAnalysisLabel(vm) {
    if (vm.ux_state === UX_STATES.ANALYSIS_UNAVAILABLE) return 'Unavailable';
    if (vm.ux_state === UX_STATES.INTERVENTION) return 'Checked';
    if (vm.ux_state === UX_STATES.CAUTION) return 'Checked';
    if (vm.ux_state === UX_STATES.PROTECTED_NO_INTERVENTION) return 'Checked';
    return 'No assessment';
  }

  function currentLanguageHint() {
    return languageHint?.value || 'auto';
  }

  function clearRecordingTimer() {
    if (recordingTimer) {
      clearTimeout(recordingTimer);
      recordingTimer = null;
    }
  }

  function stopTracks(stream) {
    if (!stream) return;
    stream.getTracks().forEach((track) => track.stop());
  }

  function stopAmplitudeAnalysis() {
    if (amplitudeAnimation) {
      cancelAnimationFrame(amplitudeAnimation);
      amplitudeAnimation = null;
    }
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
    }
    analyser = null;
    targetAmplitude = 0;
    setPresenceAmplitude(0);
  }

  function startAmplitudeAnalysis(stream) {
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor || !stream || !livingCore) return;
    try {
      audioContext = new AudioContextCtor();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        if (!analyser) return;
        analyser.getByteTimeDomainData(data);
        let total = 0;
        data.forEach((sample) => {
          const centered = sample - 128;
          total += centered * centered;
        });
        const rms = Math.sqrt(total / data.length) / 128;
        const bounded = Math.min(1, Math.max(0, rms * 3.2));
        targetAmplitude += (bounded - targetAmplitude) * 0.22;
        setPresenceAmplitude(targetAmplitude);
        amplitudeAnimation = requestAnimationFrame(tick);
      };
      tick();
    } catch (error) {
      stopAmplitudeAnalysis();
    }
  }

  function audioBlobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrl = String(reader.result || '');
        resolve(dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl);
      };
      reader.onerror = () => reject(reader.error || new Error('Audio read failed.'));
      reader.readAsDataURL(blob);
    });
  }

  function isCanaryIntervention(turn) {
    const canary = turn && turn.canary_authorization;
    return canary && canary.status === 'ALLOW' && canary.action === 'warn_user';
  }

  function isM0CanaryIntervention(data) {
    const canary = data && data.canary_decision;
    return canary && canary.decision === 'ALLOW' && canary.action === 'warn_user';
  }

  function extractActs(turn) {
    const normalized = turn && turn.normalized_m2_summary;
    const extracted = turn && turn.extracted_v2_summary && turn.extracted_v2_summary.signals;
    if (normalized && Array.isArray(normalized.acts) && normalized.acts.length > 0) {
      return normalized.acts.map((act) => ({
        action: String(act.action || '').toUpperCase(),
        asset: String(act.asset || '').toUpperCase(),
      }));
    }
    if (extracted && Array.isArray(extracted.interaction_acts)) {
      return extracted.interaction_acts.map((act) => ({
        action: String(act.action || '').toUpperCase(),
        asset: String(act.asset && act.asset.subtype ? act.asset.subtype : '').toUpperCase(),
      }));
    }
    return [];
  }

  function warningFromEvidence(turn) {
    const acts = extractActs(turn);
    const hasAction = (name) => acts.some((act) => act.action === name);
    const hasAsset = (test) => acts.some((act) => test(act.asset));
    if (hasAction('DISCLOSE') && hasAsset((asset) => asset.includes('OTP') || asset.includes('SECURITY_CODE'))) {
      return {
        primary: 'Do not share that code.',
        secondary: "It's private. It's only for you.",
      };
    }
    if (hasAction('TRANSFER') && hasAsset((asset) => ['BANK_FUNDS', 'FIAT_FUNDS', 'PAYMENT_APP_FUNDS', 'PAYMENT_APP_PAYMENT', 'CASH', 'CRYPTO_ASSET'].includes(asset))) {
      return {
        primary: 'Do not make the transfer yet.',
        secondary: 'Pause and verify independently before sending money.',
      };
    }
    if ((hasAction('INSTALL') || hasAction('GRANT_ACCESS')) && hasAsset((asset) => ['REMOTE_SOFTWARE', 'REMOTE_CONTROL', 'SCREEN_CONTENT'].includes(asset))) {
      return {
        primary: 'Do not allow remote access.',
        secondary: 'Do not install software or let anyone control your device.',
      };
    }
    if (hasAction('DISCLOSE') && hasAsset((asset) => ['PASSWORD', 'PIN', 'RECOVERY_CODE', 'SEED_PHRASE', 'PRIVATE_KEY', 'LOGIN_APPROVAL'].includes(asset))) {
      return {
        primary: 'Do not share your credentials.',
        secondary: 'Passwords, PINs and recovery details are only for you.',
      };
    }
    return {
      primary: 'Do not act yet.',
      secondary: 'Pause and verify independently before continuing.',
    };
  }

  function warningFromM0Response(data) {
    const warning = data && data.warning && data.warning.payload ? data.warning.payload : null;
    const directives = warning && Array.isArray(warning.directives) ? warning.directives : [];
    if (directives.some((directive) => String(directive).toUpperCase().includes('CODIGO'))) {
      return {
        primary: 'Do not share that code.',
        secondary: "It's private. It's only for you.",
      };
    }
    if (directives.some((directive) => String(directive).toUpperCase().includes('TRANSFER'))) {
      return {
        primary: 'Do not make the transfer yet.',
        secondary: 'Pause and verify independently before sending money.',
      };
    }
    if (directives.some((directive) => String(directive).toUpperCase().includes('REMOTO'))) {
      return {
        primary: 'Do not allow remote access.',
        secondary: 'Do not install software or let anyone control your device.',
      };
    }
    if (directives.some((directive) => String(directive).toUpperCase().includes('CONTRASENA'))) {
      return {
        primary: 'Do not share your credentials.',
        secondary: 'Passwords, PINs and recovery details are only for you.',
      };
    }
    return {
      primary: 'Do not act yet.',
      secondary: 'Pause and verify independently before continuing.',
    };
  }

  function buildGuardianViewModel(data, submittedText, source) {
    if (data && (data.risk_assessment || data.canary_decision || data.warning || data.signals)) {
      const risk = data.risk_assessment && data.risk_assessment.level ? data.risk_assessment.level : null;
      const failed = !!data.error || !data.risk_assessment || !data.canary_decision;
      const intervention = !failed && isM0CanaryIntervention(data);
      let state = UX_STATES.PROTECTED_NO_INTERVENTION;
      if (failed) {
        state = UX_STATES.ANALYSIS_UNAVAILABLE;
      } else if (intervention) {
        state = UX_STATES.INTERVENTION;
      } else if (risk === 'HIGH' || risk === 'CRITICAL') {
        state = UX_STATES.CAUTION;
      }
      return {
        ux_state: state,
        input_source: source,
        submitted_text: submittedText,
        turn_status: data.error ? 'EXTRACTION_FAILED' : 'ANALYZED',
        current_risk: risk,
        canary_status: data.canary_decision ? data.canary_decision.decision : 'NOT_REQUESTED',
        canary_action: data.canary_decision ? data.canary_decision.action : null,
        warning: intervention ? warningFromM0Response(data) : null,
        failure_kind: data.error ? 'EXTRACTION_FAILED' : null,
        preserved_risk: failed && lastValidatedViewModel ? lastValidatedViewModel.current_risk : null,
      };
    }

    const turn = data && data.turn ? data.turn : null;
    const status = turn ? turn.status : (data && data.status) || 'REQUEST_FAILED';
    const risk = turn && turn.current_risk ? turn.current_risk : null;
    const canary = turn && turn.canary_authorization ? turn.canary_authorization : null;
    const failed = !turn || status === 'EXTRACTION_FAILED' || status === 'UNSUPPORTED_MAPPING' || !!(data && data.error);
    const intervention = !failed && isCanaryIntervention(turn);
    const warning = intervention ? warningFromEvidence(turn) : null;
    let state = UX_STATES.PROTECTED_NO_INTERVENTION;
    if (failed) {
      state = UX_STATES.ANALYSIS_UNAVAILABLE;
    } else if (intervention) {
      state = UX_STATES.INTERVENTION;
    } else if (risk === 'HIGH' || risk === 'CRITICAL') {
      state = UX_STATES.CAUTION;
    }
    return {
      ux_state: state,
      input_source: source,
      submitted_text: submittedText,
      turn_status: status,
      current_risk: risk,
      canary_status: canary ? canary.status : 'NOT_REQUESTED',
      canary_action: canary ? canary.action : null,
      warning,
      failure_kind: data && data.error && data.error.kind ? data.error.kind : status,
      preserved_risk: failed && lastValidatedViewModel ? lastValidatedViewModel.current_risk : null,
    };
  }

  function renderGuardianViewModel(vm) {
    setGuardianState(vm.ux_state);
    setText(inputSource, vm.input_source || '-');
    setText(analysisState, humanAnalysisLabel(vm));
    warningPanel.hidden = true;
    if (previewDisclaimer) previewDisclaimer.hidden = true;

    if (vm.ux_state === UX_STATES.ANALYSIS_UNAVAILABLE) {
      setText(stateLabel, 'We could not check this part.');
      setText(headline, vm.input_source === 'VOICE'
        ? 'No hemos podido escuchar esta parte de la llamada.'
        : 'No hemos podido comprobar esta parte de la llamada.');
    setText(detail, vm.preserved_risk
        ? 'Esto no significa que sea segura. Seguimos manteniendo la ultima indicacion fiable.'
        : 'Esto no significa que sea segura.');
      return;
    }

    if (vm.ux_state === UX_STATES.INTERVENTION) {
      setText(stateLabel, 'Stop.');
      setText(headline, vm.warning.primary);
      setText(detail, vm.warning.secondary);
      if (previewDisclaimer) previewDisclaimer.hidden = !vm.preview;
      warningPanel.hidden = false;
      triggerPresenceIntervention();
      playInterventionCueOnce(vm);
      requestHapticCueOnce(vm);
      return;
    }

    if (vm.ux_state === UX_STATES.CAUTION) {
      setText(stateLabel, 'Slow down and verify.');
      setText(headline, 'Pause before doing anything important.');
      setText(detail, 'Take a moment. You can verify independently before acting.');
      return;
    }

    setText(stateLabel, 'Protection active');
    if (conversationActive) {
      setText(stateLabel, 'No action needed');
      setText(headline, 'Keep talking normally.');
      setText(detail, 'Protection remains active.');
    } else {
      setText(headline, 'You can keep talking normally.');
      setText(detail, 'Guardian stays with you while you talk.');
    }
  }

  function renderImmediateState(state, source = '-') {
    setGuardianState(state);
    setText(inputSource, source);
    warningPanel.hidden = true;
    if (previewDisclaimer) previewDisclaimer.hidden = true;
    if (state === UX_STATES.LISTENING) {
      setText(stateLabel, 'Listening');
      setText(headline, 'Keep talking normally.');
      setText(detail, "I'll let you know if you need to stop.");
    } else if (state === UX_STATES.TRANSCRIBING) {
      setText(stateLabel, 'Transcribing');
      setText(headline, 'One moment.');
      setText(detail, 'Keep the call open.');
    } else if (state === UX_STATES.CHECKING) {
      setText(stateLabel, 'Checking');
      setText(headline, 'One moment.');
      setText(detail, 'Keep the call open.');
    } else {
      setText(stateLabel, 'Protection active');
      setText(headline, 'You can keep talking normally.');
      setText(detail, 'Guardian stays with you while you talk.');
    }
  }

  function renderPreviewState(state) {
    stopPreviewMicResponse();
    lastInterventionKey = null;
    lastHapticKey = null;
    setConversationActive(state !== UX_STATES.PROTECTED_NO_INTERVENTION);
    if (state === UX_STATES.INTERVENTION) {
      renderGuardianViewModel({
        preview: true,
        ux_state: UX_STATES.INTERVENTION,
        input_source: 'DEMO PREVIEW',
        turn_status: 'VISUAL_PREVIEW',
        current_risk: 'PREVIEW',
        canary_status: 'PREVIEW_ONLY',
        canary_action: 'preview_warn_user',
        warning: {
          primary: 'Do not share that code.',
          secondary: "It's private. It's only for you.",
        },
      });
      return;
    }
    if (state === UX_STATES.ANALYSIS_UNAVAILABLE) {
      renderGuardianViewModel({
        ux_state: UX_STATES.ANALYSIS_UNAVAILABLE,
        input_source: 'DEMO PREVIEW',
        turn_status: 'VISUAL_PREVIEW',
        current_risk: null,
        failure_kind: 'VISUAL_PREVIEW',
        preserved_risk: null,
      });
      return;
    }
    if (state === UX_STATES.CAUTION) {
      renderGuardianViewModel({
        ux_state: UX_STATES.CAUTION,
        input_source: 'DEMO PREVIEW',
        turn_status: 'VISUAL_PREVIEW',
        current_risk: 'PREVIEW',
        canary_status: 'PREVIEW_ONLY',
        canary_action: null,
        warning: null,
      });
      return;
    }
    renderImmediateState(state, 'DEMO PREVIEW');
  }

  async function startPreviewMicResponse() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      renderGuardianViewModel({
        ux_state: UX_STATES.ANALYSIS_UNAVAILABLE,
        input_source: 'DEMO PREVIEW',
        turn_status: 'VISUAL_PREVIEW',
        preserved_risk: null,
      });
      return;
    }
    try {
      stopPreviewMicResponse();
      setConversationActive(true);
      previewMicStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      startAmplitudeAnalysis(previewMicStream);
      renderImmediateState(UX_STATES.LISTENING, 'DEMO PREVIEW');
      if (btnPreviewMic) btnPreviewMic.disabled = true;
      if (btnPreviewMicStop) btnPreviewMicStop.disabled = false;
    } catch (error) {
      renderGuardianViewModel({
        ux_state: UX_STATES.ANALYSIS_UNAVAILABLE,
        input_source: 'DEMO PREVIEW',
        turn_status: 'VISUAL_PREVIEW',
        preserved_risk: null,
      });
    }
  }

  function stopPreviewMicResponse() {
    if (!previewMicStream) return;
    stopAmplitudeAnalysis();
    stopTracks(previewMicStream);
    previewMicStream = null;
    if (btnPreviewMic) btnPreviewMic.disabled = false;
    if (btnPreviewMicStop) btnPreviewMicStop.disabled = true;
  }

  async function submitCanonicalText(text, source = 'TEXT') {
    const trimmed = String(text || '').trim();
    if (!trimmed) return;
    setConversationActive(true);
    sourceTurnNumber += 1;
    renderImmediateState(UX_STATES.CHECKING, source);
    try {
      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      const vm = buildGuardianViewModel(data, trimmed, source);
      renderGuardianViewModel(vm);
      if (vm.ux_state !== UX_STATES.ANALYSIS_UNAVAILABLE) {
        lastValidatedViewModel = vm;
      }
    } catch (error) {
      renderGuardianViewModel(buildGuardianViewModel({
        status: 'REQUEST_FAILED',
        error: { kind: 'REQUEST_FAILED' },
      }, trimmed, source));
    }
  }

  async function transcribeAudio(blob) {
    renderImmediateState(UX_STATES.TRANSCRIBING, 'VOICE');
    setText(sttState, 'TRANSCRIBING');
    try {
      const response = await fetch('/api/v1/experimental/stt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio_base64: await audioBlobToBase64(blob),
          mime_type: blob.type || 'audio/webm',
          language_hint: currentLanguageHint(),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      if (data.status !== 'TRANSCRIBED' || !data.transcript) {
        setText(sttState, 'FAILED');
        renderGuardianViewModel(buildGuardianViewModel({
          status: 'STT_FAILED',
          error: data.error || { kind: 'STT_FAILED' },
        }, '', 'VOICE'));
        return;
      }
      setText(sttState, 'TRANSCRIBED');
      manualText.value = data.transcript;
      await submitCanonicalText(data.transcript, 'VOICE');
    } catch (error) {
      setText(sttState, 'FAILED');
      renderGuardianViewModel(buildGuardianViewModel({
        status: 'STT_FAILED',
        error: { kind: 'REQUEST_FAILED' },
      }, '', 'VOICE'));
    } finally {
      showRecordingAction('start');
    }
  }

  function playInterventionCueOnce(vm) {
    const key = `${sourceTurnNumber}:${vm.canary_action}:${vm.current_risk}:${vm.warning.primary}`;
    if (lastInterventionKey === key) return;
    lastInterventionKey = key;
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) return;
    try {
      const context = new AudioContextCtor();
      const gain = context.createGain();
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.22);
      gain.connect(context.destination);
      [440, 660].forEach((frequency, index) => {
        const oscillator = context.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(frequency, context.currentTime + index * 0.08);
        oscillator.connect(gain);
        oscillator.start(context.currentTime + index * 0.08);
        oscillator.stop(context.currentTime + 0.24 + index * 0.03);
      });
      setTimeout(() => context.close().catch(() => {}), 420);
    } catch (error) {
      // Audio availability never affects protection logic.
    }
  }

  function requestHapticCueOnce(vm) {
    const key = `${sourceTurnNumber}:${vm.canary_action}:${vm.current_risk}:${vm.warning.primary}:haptic`;
    if (lastHapticKey === key) return;
    lastHapticKey = key;
    if (navigator.vibrate) navigator.vibrate([90, 40, 90]);
  }

  btnRecordStart?.addEventListener('click', async () => {
    stopPreviewMicResponse();
    setConversationActive(true);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      setText(sttState, 'UNAVAILABLE');
      renderGuardianViewModel(buildGuardianViewModel({
        status: 'STT_FAILED',
        error: { kind: 'MEDIA_UNAVAILABLE' },
      }, '', 'VOICE'));
      return;
    }
    try {
      recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingChunks = [];
      mediaRecorder = new MediaRecorder(recordingStream);
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) recordingChunks.push(event.data);
      };
      mediaRecorder.onstop = async () => {
        clearRecordingTimer();
        stopAmplitudeAnalysis();
        stopTracks(recordingStream);
        const blob = new Blob(recordingChunks, {
          type: recordingChunks[0]?.type || mediaRecorder.mimeType || 'audio/webm',
        });
        await transcribeAudio(blob);
      };
      mediaRecorder.start();
      startAmplitudeAnalysis(recordingStream);
      setText(sttState, 'LISTENING');
      renderImmediateState(UX_STATES.LISTENING, 'VOICE');
      showRecordingAction('stop');
      recordingTimer = setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
      }, MAX_RECORDING_MS);
    } catch (error) {
      setText(sttState, 'MICROPHONE BLOCKED');
      renderGuardianViewModel(buildGuardianViewModel({
        status: 'STT_FAILED',
        error: { kind: 'MICROPHONE_UNAVAILABLE' },
      }, '', 'VOICE'));
    }
  });

  btnRecordStop?.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
    btnRecordStop.disabled = true;
  });

  btnSubmitText?.addEventListener('click', async () => {
    await submitCanonicalText(manualText.value, 'TEXT');
  });

  btnAckWarning?.addEventListener('click', () => {
    warningPanel.hidden = true;
  });

  btnReset?.addEventListener('click', () => {
    stopPreviewMicResponse();
    setConversationActive(false);
    sourceTurnNumber = 0;
    lastValidatedViewModel = null;
    lastInterventionKey = null;
    lastHapticKey = null;
    manualText.value = '';
    setText(sttState, 'IDLE');
    setText(analysisState, 'No assessment');
    showRecordingAction('start');
    renderImmediateState(UX_STATES.READY);
  });

  previewButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const state = button.getAttribute('data-preview-state');
      if (UX_STATES[state]) renderPreviewState(UX_STATES[state]);
    });
  });

  btnPreviewMic?.addEventListener('click', () => {
    startPreviewMicResponse();
  });

  btnPreviewMicStop?.addEventListener('click', () => {
    stopPreviewMicResponse();
    renderImmediateState(UX_STATES.READY, 'DEMO PREVIEW');
  });

  btnPreviewCue?.addEventListener('click', () => {
    renderPreviewState(UX_STATES.INTERVENTION);
  });

  function startVisualReviewMode() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has('guardianVisualReview')) return;
    const states = [
      UX_STATES.READY,
      UX_STATES.LISTENING,
      UX_STATES.CHECKING,
      UX_STATES.CAUTION,
      UX_STATES.INTERVENTION,
      UX_STATES.PROTECTED_NO_INTERVENTION,
      UX_STATES.ANALYSIS_UNAVAILABLE,
    ];
    let index = 0;
    setInterval(() => {
      index = (index + 1) % states.length;
      renderPreviewState(states[index]);
    }, 2200);
  }

  function initializeGuardianVisual() {
    const canvas = document.getElementById('guardian-visual');
    if (!canvas || !window.createGuardianVisual) return;
    try {
      guardianVisual = window.createGuardianVisual(canvas);
      if (!guardianVisual) {
        livingCore?.classList.add('visual-fallback');
        return;
      }
      livingCore?.classList.add('visual-ready');
      guardianVisual.start();
    } catch (error) {
      guardianVisual = null;
      livingCore?.classList.add('visual-fallback');
    }
  }

  window.guardianCall = {
    UX_STATES,
    buildGuardianViewModel,
    warningFromEvidence,
    submitCanonicalText,
    initializeGuardianVisual,
  };

  initializeGuardianVisual();
  setConversationActive(false);
  renderImmediateState(UX_STATES.READY);
  showRecordingAction('start');
  startVisualReviewMode();
});
