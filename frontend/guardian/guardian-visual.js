(function () {
  'use strict';

  const STATES = Object.freeze({
    READY: 'READY',
    LISTENING: 'LISTENING',
    TRANSCRIBING: 'CHECKING',
    CHECKING: 'CHECKING',
    PROTECTED_NO_INTERVENTION: 'PROTECTED_NO_INTERVENTION',
    CAUTION: 'CAUTION',
    INTERVENTION: 'INTERVENTION',
    ANALYSIS_UNAVAILABLE: 'ANALYSIS_UNAVAILABLE',
  });

  const PALETTE = Object.freeze({
    READY: [73, 108, 99],
    LISTENING: [82, 130, 119],
    CHECKING: [92, 149, 139],
    PROTECTED_NO_INTERVENTION: [78, 112, 101],
    CAUTION: [181, 132, 62],
    INTERVENTION: [187, 82, 72],
    ANALYSIS_UNAVAILABLE: [96, 116, 128],
  });

  const HIGHLIGHT = Object.freeze({
    READY: [167, 214, 200],
    LISTENING: [160, 218, 207],
    CHECKING: [174, 229, 219],
    PROTECTED_NO_INTERVENTION: [156, 204, 190],
    CAUTION: [232, 187, 104],
    INTERVENTION: [236, 142, 128],
    ANALYSIS_UNAVAILABLE: [160, 178, 188],
  });

  const ENERGY = Object.freeze({
    READY: 0.38,
    LISTENING: 0.50,
    CHECKING: 0.66,
    PROTECTED_NO_INTERVENTION: 0.40,
    CAUTION: 0.72,
    INTERVENTION: 0.86,
    ANALYSIS_UNAVAILABLE: 0.25,
  });

  function mulberry32(seed) {
    return function next() {
      let t = seed += 0x6D2B79F5;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function mixColor(a, b, t) {
    return [
      Math.round(lerp(a[0], b[0], t)),
      Math.round(lerp(a[1], b[1], t)),
      Math.round(lerp(a[2], b[2], t)),
    ];
  }

  function rgba(color, alpha) {
    return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
  }

  function smoothstep(edge0, edge1, value) {
    const t = clamp((value - edge0) / (edge1 - edge0), 0, 1);
    return t * t * (3 - 2 * t);
  }

  function createPoint(rand, cluster, index) {
    const angle = rand() * Math.PI * 2;
    const deepCore = cluster.weight > 0.8;
    const radius = Math.pow(rand(), deepCore ? 1.32 : 0.78) * cluster.spread;
    const wobble = (rand() - 0.5) * 0.08;
    const x = clamp(cluster.x + Math.cos(angle) * radius * cluster.ovalX + wobble, -0.78, 0.80);
    const y = clamp(cluster.y + Math.sin(angle) * radius * cluster.ovalY + (rand() - 0.5) * 0.08, -0.62, 0.64);
    const z = clamp(cluster.z + (rand() - 0.5) * cluster.depth, -0.72, 0.78);
    const distance = Math.hypot(x * 1.06, y * 1.18);
    const anchorChance = rand();
    const role = anchorChance > 0.965 ? 'anchor' : anchorChance > 0.78 ? 'medium' : 'tiny';

    return {
      originX: x,
      originY: y,
      originZ: z,
      layer: z > 0.26 ? 'front' : z < -0.28 ? 'back' : 'mid',
      role,
      radius: role === 'anchor' ? 2.8 + rand() * 1.2 : role === 'medium' ? 1.7 + rand() * 1.2 : 0.8 + rand() * 1.2,
      halo: role === 'anchor' ? 30 + rand() * 20 : role === 'medium' ? 20 + rand() * 22 : 12 + rand() * 26,
      route: clamp((x + 0.80) / 1.60 + y * 0.10 + z * 0.08 + (rand() - 0.5) * 0.08, 0, 1),
      core: clamp(1 - distance, 0, 1),
      clusterId: cluster.id,
      clusterWeight: cluster.weight,
      opacity: 0.42 + rand() * 0.50,
      phase: rand() * Math.PI * 2,
      driftX: (0.006 + rand() * 0.018) * (z > 0 ? 1.0 : 0.55),
      driftY: (0.006 + rand() * 0.016) * (z > 0 ? 0.9 : 0.50),
      rateX: 0.030 + rand() * 0.072 + index * 0.0003,
      rateY: 0.026 + rand() * 0.066,
    };
  }

  function buildField() {
    const rand = mulberry32(0x51A7E11);
    const clusters = [
      { id: 0, x: -0.04, y: -0.02, z: 0.18, spread: 0.36, ovalX: 1.00, ovalY: 0.82, depth: 0.80, weight: 1.00, count: 56 },
      { id: 1, x: 0.20, y: 0.08, z: 0.34, spread: 0.25, ovalX: 0.92, ovalY: 0.72, depth: 0.48, weight: 0.86, count: 24 },
      { id: 2, x: -0.26, y: 0.16, z: -0.08, spread: 0.24, ovalX: 1.12, ovalY: 0.78, depth: 0.50, weight: 0.68, count: 18 },
      { id: 3, x: 0.10, y: -0.24, z: -0.18, spread: 0.26, ovalX: 0.84, ovalY: 1.00, depth: 0.52, weight: 0.62, count: 16 },
      { id: 4, x: -0.42, y: -0.08, z: -0.30, spread: 0.26, ovalX: 1.18, ovalY: 0.66, depth: 0.42, weight: 0.38, count: 10 },
      { id: 5, x: 0.44, y: 0.20, z: -0.12, spread: 0.22, ovalX: 1.08, ovalY: 0.76, depth: 0.38, weight: 0.34, count: 8 },
    ];
    const particles = [];

    clusters.forEach((cluster) => {
      for (let i = 0; i < cluster.count; i += 1) {
        particles.push(createPoint(rand, cluster, particles.length));
      }
    });

    return { particles, clusters };
  }

  function createCssFallback(canvas) {
    canvas.dataset.visualRenderer = 'css-fallback';
    canvas.dataset.visualReady = 'false';
    const core = canvas.closest('.living-core');
    if (core) core.classList.add('visual-fallback');
    return {
      setState() {},
      setActivity() {},
      triggerSignal() {},
      start() {},
      renderer: 'css-fallback',
    };
  }

  function createGuardianVisual(canvas) {
    const context = canvas.getContext('2d', { alpha: true });
    if (!context) return createCssFallback(canvas);
    const tissue = document.createElement('canvas');
    const tissueContext = tissue.getContext('2d', { alpha: true });
    if (!tissueContext) return createCssFallback(canvas);

    const reducedMotion = window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const params = new URLSearchParams(window.location.search);
    const diagnostic = params.has('guardianVisualDebug');
    const field = buildField();
    const state = {
      current: STATES.READY,
      previous: STATES.READY,
      transitionStart: performance.now() - 2400,
      activity: 0,
      signalStart: performance.now() - 9000,
      pulseStart: performance.now() - 9000,
    };

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(rect.width * ratio));
      const height = Math.max(1, Math.round(rect.height * ratio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
        tissue.width = width;
        tissue.height = height;
      }
      return { width, height, ratio };
    }

    function projectedParticle(particle, time, energy, wave) {
      const motion = reducedMotion ? 0 : 1;
      const depth = clamp((particle.originZ + 0.78) / 1.56, 0, 1);
      const lag = lerp(0.42, 1.08, depth);
      const phaseX = time * particle.rateX * lag + particle.phase;
      const phaseY = time * particle.rateY * lag + particle.phase * 1.37;
      const clusterShiftX = Math.sin(time * 0.028 + particle.clusterId * 1.7) * 0.018 * motion;
      const clusterShiftY = Math.cos(time * 0.024 + particle.clusterId * 1.2) * 0.014 * motion;
      const thought = Math.sin(time * 0.12 + particle.route * 8.0) * 0.010 * motion * energy;
      const waveLift = smoothstep(0.26, 0.0, Math.abs(particle.route - wave));
      const x = particle.originX
        + clusterShiftX * particle.clusterWeight
        + Math.sin(phaseX) * particle.driftX * motion
        + thought * waveLift;
      const y = particle.originY
        + clusterShiftY * particle.clusterWeight
        + Math.cos(phaseY) * particle.driftY * motion
        - thought * 0.56 * waveLift;
      const orbFade = clamp(1 - Math.hypot(x * 0.94, y * 1.06) / 0.86, 0, 1);
      const density = clamp(
        0.24 + particle.core * 0.72 + particle.clusterWeight * 0.30 + waveLift * 0.28 + state.activity * 0.16,
        0,
        1
      );

      return {
        x,
        y,
        z: particle.originZ,
        depth,
        role: particle.role,
        route: particle.route,
        clusterId: particle.clusterId,
        orbFade,
        density,
        waveLift,
        radius: particle.radius * lerp(0.74, 1.34, depth) * (1 + waveLift * 0.18),
        halo: particle.halo * lerp(0.74, 1.22, depth) * (1 + density * 0.26),
        opacity: particle.opacity * orbFade * lerp(0.46, 1.0, depth) * (0.58 + density * 0.60),
      };
    }

    function colorFor(point, transition, wave) {
      const previous = PALETTE[state.previous] || PALETTE.READY;
      const next = PALETTE[state.current] || PALETTE.READY;
      const highlight = HIGHLIGHT[state.current] || HIGHLIGHT.READY;
      const localArrival = smoothstep(-0.24, 0.58, transition - point.route * 0.52);
      const waveArrival = smoothstep(0.32, 0.0, Math.abs(point.route - wave));
      const blend = reducedMotion ? transition : clamp(localArrival * 0.72 + waveArrival * 0.28, 0, 1);
      const base = mixColor(previous, next, blend);
      const active = point.role === 'anchor' ? 0.34 : point.role === 'medium' ? 0.18 : 0.05;
      return mixColor(base, highlight, clamp(active + point.waveLift * 0.18 + state.activity * 0.05, 0, 0.48));
    }

    function drawRadial(ctx, x, y, radius, color, alpha) {
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
      gradient.addColorStop(0, rgba(color, alpha));
      gradient.addColorStop(0.44, rgba(color, alpha * 0.30));
      gradient.addColorStop(1, rgba(color, 0));
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    function toScreen(point, centerX, centerY, scale) {
      const perspective = lerp(0.86, 1.06, point.depth);
      return {
        ...point,
        sx: centerX + point.x * scale * perspective,
        sy: centerY + point.y * scale * 0.90 * perspective,
      };
    }

    function drawClusterTissue(points, centerX, centerY, size, scale, color, unavailable) {
      const clusterStats = new Map();
      points.forEach((point) => {
        const current = clusterStats.get(point.clusterId) || { x: 0, y: 0, weight: 0, density: 0 };
        const weight = Math.max(0.04, point.opacity * point.density);
        current.x += point.sx * weight;
        current.y += point.sy * weight;
        current.weight += weight;
        current.density += point.density * weight;
        clusterStats.set(point.clusterId, current);
      });

      tissueContext.globalCompositeOperation = 'source-over';
      tissueContext.clearRect(0, 0, tissue.width, tissue.height);
      [...clusterStats.values()].forEach((cluster, index) => {
        if (!cluster.weight) return;
        const x = cluster.x / cluster.weight;
        const y = cluster.y / cluster.weight;
        const density = cluster.density / cluster.weight;
        const radius = size * (0.14 + density * 0.095 + (index % 2) * 0.020);
        const alpha = (unavailable ? 0.036 : 0.082 + density * 0.062) * (diagnostic ? 1.45 : 1);
        drawRadial(tissueContext, x, y, radius, color, alpha);
      });

      drawRadial(tissueContext, centerX - size * 0.02, centerY + size * 0.01, size * 0.30, color, unavailable ? 0.032 : 0.070);
      drawRadial(tissueContext, centerX + size * 0.09, centerY - size * 0.06, size * 0.22, color, unavailable ? 0.022 : 0.052);
      drawRadial(tissueContext, centerX - size * 0.12, centerY + size * 0.08, size * 0.21, color, unavailable ? 0.020 : 0.048);

      context.save();
      context.globalCompositeOperation = 'source-over';
      context.filter = `blur(${Math.max(4, size * 0.010)}px)`;
      context.globalAlpha = diagnostic ? 0.98 : 0.94;
      context.drawImage(tissue, 0, 0);
      context.restore();
    }

    function drawLinks(points, size, energy, unavailable) {
      const localLimit = size * (0.144 + energy * 0.046);
      const structuralLimit = size * (0.230 + energy * 0.034);
      context.globalCompositeOperation = 'source-over';
      for (let i = 0; i < points.length; i += 1) {
        const point = points[i];
        for (let j = i + 1; j < points.length; j += 1) {
          const other = points[j];
          const dx = point.sx - other.sx;
          const dy = point.sy - other.sy;
          const distance = Math.hypot(dx, dy);
          const sameCluster = point.clusterId === other.clusterId;
          const anchorPair = point.role === 'anchor' || other.role === 'anchor';
          const structural = anchorPair && Math.abs(point.route - other.route) < 0.34 && distance < structuralLimit;
          if (!structural && (!sameCluster || distance > localLimit || Math.abs(point.route - other.route) > 0.24)) continue;
          if (unavailable && !sameCluster) continue;
          const limit = structural ? structuralLimit : localLimit;
          const closeness = 1 - distance / limit;
          if (closeness <= 0) continue;
          const depthMatch = 1 - Math.min(1, Math.abs(point.depth - other.depth) * 1.2);
          const alphaBase = structural ? 0.044 : 0.024;
          const alpha = closeness * depthMatch * point.orbFade * other.orbFade
            * (alphaBase + energy * (structural ? 0.046 : 0.034))
            * (unavailable ? 0.34 : 1);
          if (alpha < 0.006) continue;
          const color = mixColor(point.color, other.color, 0.5);
          context.beginPath();
          context.moveTo(point.sx, point.sy);
          const bend = reducedMotion ? 0 : Math.sin((point.route + other.route) * 7.0 + point.clusterId) * size * 0.010;
          context.quadraticCurveTo((point.sx + other.sx) * 0.5 + bend, (point.sy + other.sy) * 0.5 - bend * 0.5, other.sx, other.sy);
          context.lineWidth = structural ? 0.82 : 0.54;
          context.strokeStyle = rgba(color, diagnostic ? alpha * 2.2 : alpha);
          context.stroke();
        }
      }
    }

    function drawNodes(points, ratio, energy, unavailable) {
      context.globalCompositeOperation = 'lighter';
      points.forEach((point, index) => {
        if (point.orbFade <= 0.03) return;
        if (unavailable && index % 5 === 0) return;
        const roleLift = point.role === 'anchor' ? 1.75 : point.role === 'medium' ? 1.18 : 0.88;
        const nodeAlpha = point.opacity * (point.role === 'anchor' ? 0.42 : point.role === 'medium' ? 0.24 : 0.14) * (unavailable ? 0.55 : 1);
        const haloAlpha = point.opacity * (point.role === 'anchor' ? 0.150 : point.role === 'medium' ? 0.100 : 0.066) * (unavailable ? 0.45 : 1);
        drawRadial(context, point.sx, point.sy, point.halo * ratio * (0.72 + energy * 0.28), point.color, haloAlpha);
        drawRadial(context, point.sx, point.sy, Math.max(1.0, point.radius * ratio * roleLift), point.color, diagnostic ? 0.42 : nodeAlpha);
      });
    }

    function render(now) {
      const { width, height, ratio } = resize();
      const size = Math.min(width, height);
      const centerX = width * 0.50;
      const centerY = height * 0.50;
      const scale = size * 0.70;
      const time = now / 1000;
      const transition = clamp((now - state.transitionStart) / 2100, 0, 1);
      const wave = reducedMotion ? 0.52 : clamp((now - state.signalStart) / 2500, 0, 1);
      const pulse = Math.max(0, 1 - (now - state.pulseStart) / 1700);
      const currentColor = PALETTE[state.current] || PALETTE.READY;
      const unavailable = state.current === STATES.ANALYSIS_UNAVAILABLE;
      const energy = diagnostic ? 0.94 : Math.max(ENERGY[state.current] || ENERGY.READY, state.activity * 0.72);
      const points = field.particles
        .map((particle) => projectedParticle(particle, time, energy, wave))
        .map((point) => {
          const colored = { ...point, color: colorFor(point, transition, wave) };
          return toScreen(colored, centerX, centerY, scale);
        })
        .sort((a, b) => a.depth - b.depth);

      context.clearRect(0, 0, width, height);
      drawClusterTissue(points, centerX, centerY, size, scale, currentColor, unavailable);
      drawLinks(points, size, energy, unavailable);
      drawNodes(points, ratio, energy, unavailable);

      if (pulse > 0 && state.current === STATES.INTERVENTION) {
        context.globalCompositeOperation = 'lighter';
        drawRadial(context, centerX + size * 0.04, centerY - size * 0.01, size * (0.16 + pulse * 0.05), PALETTE.INTERVENTION, 0.040 * pulse);
      }

      requestAnimationFrame(render);
    }

    return {
      setState(nextState) {
        const normalized = STATES[nextState] || STATES.READY;
        if (normalized === state.current) return;
        state.previous = state.current;
        state.current = normalized;
        state.transitionStart = performance.now();
        if (normalized !== STATES.PROTECTED_NO_INTERVENTION) this.triggerSignal();
      },
      setActivity(value) {
        state.activity = clamp(Number(value) || 0, 0, 1);
      },
      triggerSignal(origin) {
        state.signalStart = performance.now();
        state.pulseStart = performance.now();
        state.signalOrigin = Number.isFinite(origin) ? origin : state.signalOrigin;
      },
      particles: field.particles,
      renderer: 'canvas2d-sentient-network-orb',
      start() {
        canvas.dataset.visualReady = 'true';
        canvas.dataset.visualRenderer = 'canvas2d-sentient-network-orb';
        requestAnimationFrame(render);
      },
    };
  }

  window.createGuardianVisual = createGuardianVisual;
})();
