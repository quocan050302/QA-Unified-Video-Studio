// SPDX-License-Identifier: MIT
// Selective timing & sparse interaction FX helpers for FL-01 V14.7.6.
// Adapted from https://github.com/buildwithhanif/claude-animation-skill
// (main SHA 4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b)
// Copyright (c) 2026 Hanif (@hanifproduktif) — MIT License (see ./LICENSE).
//
// Browser & Node compatible pure functions of time and seed:
// - ZERO @napi-rs/canvas dependency, ZERO standalone film.mjs render pipeline.
// - Strictly separates local ACTION timeWarp from global VOICE and CAMERA time so
//   narration and shot/segment cut boundaries NEVER freeze or drift.
// - Feature-gated by `motionPlan.fx_profile` ("none" => strict no-op).

export const CLAUDE_SKILL_PROVENANCE = Object.freeze({
  repository: 'https://github.com/buildwithhanif/claude-animation-skill',
  branch: 'main',
  commit_sha: '4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b',
  license: 'MIT',
  copyright: 'Copyright (c) 2026 Hanif (@hanifproduktif)',
});

export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, Number(x) || 0));
export const lerp = (a, b, k) => a + (b - a) * k;
export const ss = (a, b, x) => {
  const span = b - a || 1e-6;
  const k = clamp((x - a) / span, 0, 1);
  return k * k * (3 - 2 * k);
};

export const hash = (n) => {
  const x = Math.sin(Number(n) * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export const rng = (seed = 1) => {
  let s = Math.max(1, Math.floor(Math.abs(Number(seed) || 1))) % 2147483647;
  if (s === 0) s = 1;
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
};

// Easing functions (k in 0..1)
export const eOut = (k) => 1 - Math.pow(1 - clamp(k, 0, 1), 3);
export const eIn = (k) => Math.pow(clamp(k, 0, 1), 3);
export const eIO = (k) => {
  const u = clamp(k, 0, 1);
  return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
};
export const eBack = (k, s = 1.8) => {
  const u = clamp(k, 0, 1) - 1;
  return 1 + (s + 1) * u * u * u + s * u * u;
};

/**
 * Exposure quantizer (`ones`, `twos`, `hold`) for secondary drawing cadence while
 * camera & voice remain strictly on raw `t` (24fps ones).
 */
export function exposure(t, mode = 'ones', fps = 24, holdTime = 0) {
  const raw = Number(t) || 0;
  if (mode === 'hold') return Number(holdTime) || 0;
  if (mode === 'twos') {
    const step = Math.max(1, fps / 2);
    return Math.floor(raw * step + 1e-6) / step;
  }
  return raw;
}

/**
 * Hit-stop / micro-hold timeWarp adapted from claude-animation-skill `lib/fx.mjs`.
 * `stops`: `[[actionTime, freezeDuration], ...]` sorted in action time.
 */
export function timeWarp(stops = []) {
  const S = [...(stops || [])]
    .map(([s, d]) => [Number(s) || 0, Math.max(0, Number(d) || 0)])
    .filter(([, d]) => d > 0)
    .sort((a, b) => a[0] - b[0]);
  return {
    stops: S,
    game(t) {
      let acc = 0;
      for (const [s, d] of S) {
        if (t < s + acc) break;
        if (t < s + acc + d) return s;
        acc += d;
      }
      return t - acc;
    },
    real(g) {
      let acc = 0;
      for (const [s, d] of S) {
        if (s >= g) break;
        acc += d;
      }
      return g + acc;
    },
    frozen(t) {
      let acc = 0;
      for (const [s, d] of S) {
        if (t < s + acc) break;
        if (t < s + acc + d) return true;
        acc += d;
      }
      return false;
    },
  };
}

/**
 * Separated FL-01 clock: warps ONLY local character action micro-holds (e.g. 1-2 frames
 * on foot slip catch or pulley lock) and recovers smoothly before `shotEndSec` so:
 * 1) `voiceTime(realT) === realT` (narration NEVER freezes)
 * 2) `cameraTime(realT) === realT` (shot & internal camera cut boundaries NEVER shift)
 * 3) `actionTime(shotStartSec) === shotStartSec` and `actionTime(shotEndSec) === shotEndSec`
 * 4) `cueToRealTime(actionCueSec)` maps action-time Foley cues to exact real timestamps.
 */
export function createSeparatedActionClock({
  shotStartSec = 0,
  shotEndSec = 4,
  stops = [],
  fxProfile = 'subtle_harbor_fx',
} = {}) {
  const enabled = Boolean(fxProfile && fxProfile !== 'none');
  const s0 = Number(shotStartSec) || 0;
  const s1 = Math.max(s0 + 0.1, Number(shotEndSec) || 4);
  if (!enabled || !stops || stops.length === 0) {
    return {
      enabled: false,
      actionTime: (t) => Number(t) || 0,
      voiceTime: (t) => Number(t) || 0,
      cameraTime: (t) => Number(t) || 0,
      isActionFrozen: () => false,
      cueToRealTime: (g) => Number(g) || 0,
    };
  }

  // Cap total micro-hold inside a shot to <= 8% of shot duration so motion never feels laggy
  const maxHoldBudget = (s1 - s0) * 0.08;
  let used = 0;
  const boundedStops = [];
  for (const [rawG, rawD] of stops) {
    const g = clamp(Number(rawG) || s0, s0 + 0.04, s1 - 0.18);
    const d = Math.min(Math.max(0, Number(rawD) || 0), 0.085, Math.max(0, maxHoldBudget - used));
    if (d > 1e-4) {
      boundedStops.push([g, d]);
      used += d;
    }
  }
  const tw = timeWarp(boundedStops);
  const totalHold = used;
  const lastStopRealEnd = boundedStops.length
    ? tw.real(boundedStops[boundedStops.length - 1][0]) + boundedStops[boundedStops.length - 1][1]
    : s0;

  return {
    enabled: boundedStops.length > 0,
    stops: boundedStops,
    voiceTime: (realT) => Number(realT) || 0,
    cameraTime: (realT) => Number(realT) || 0,
    isActionFrozen: (realT) => {
      const t = Number(realT) || 0;
      if (t <= s0 || t >= s1) return false;
      return tw.frozen(t);
    },
    actionTime: (realT) => {
      const t = Number(realT) || 0;
      if (t <= s0 || t >= s1 || totalHold <= 0) return t;
      const gRaw = tw.game(t);
      if (t <= lastStopRealEnd) return clamp(gRaw, s0, s1);
      // Smoothly catch up remaining `totalHold` before `s1` so shot boundary state is 100% continuous
      const catchupSpan = Math.max(0.08, s1 - lastStopRealEnd);
      const catchupProgress = ss(0, 1, (t - lastStopRealEnd) / catchupSpan);
      return clamp(gRaw + totalHold * catchupProgress, s0, s1);
    },
    cueToRealTime: (actionCueSec) => {
      const g = Number(actionCueSec) || 0;
      if (g <= s0 || g >= s1 || totalHold <= 0) return g;
      return clamp(tw.real(g), s0, s1);
    },
  };
}

export function convertSoundCuesToRealTime(cues = [], clockOrTw = null) {
  if (!Array.isArray(cues)) return [];
  return cues.map((cue) => {
    const actionT = Number(cue.action_time ?? cue.time ?? 0);
    const realT = clockOrTw
      ? typeof clockOrTw.cueToRealTime === 'function'
        ? clockOrTw.cueToRealTime(actionT)
        : typeof clockOrTw.real === 'function'
          ? clockOrTw.real(actionT)
          : actionT
      : actionT;
    return {
      ...cue,
      action_time: Math.round(actionT * 10000) / 10000,
      real_time: Math.round(realT * 10000) / 10000,
    };
  });
}

function safeAlpha(ctx, mult) {
  const base = Number.isFinite(ctx.globalAlpha) ? ctx.globalAlpha : 1;
  ctx.globalAlpha = clamp(base * clamp(mult, 0, 1), 0, 1);
}

/**
 * Sparse burst particles (sea spray, rope fibers, lantern embers, contact sparks).
 * Pure function of `(t, t0, seed)` with strictly clamped `[0, 1]` compositing alpha.
 */
export function burstParticles(ctx, t, t0, x, y, o = {}) {
  const d = Number(t) - Number(t0);
  const {
    n = 10,
    speed = 260,
    life = 0.55,
    gravity = 520,
    colors = ['#FFD35A', '#FFF3C4', '#F28C28'],
    size = 5,
    kind = 'spark',
    seed = 1,
    spread = Math.PI * 1.4,
    dir = -Math.PI / 2,
    alphaScale = 0.8,
  } = o;
  if (!ctx || d < 0 || d > life * 1.6) return 0;
  const r = rng(Math.floor(Math.abs(seed) * 977 + Math.floor(Math.abs(t0) * 1000) + 17));
  let drawn = 0;
  for (let i = 0; i < n; i++) {
    const a = dir + (r() - 0.5) * spread;
    const sp = speed * (0.45 + r() * 0.75);
    const L = life * (0.6 + r() * 0.6);
    const dd = Math.min(d, L);
    const sz = size * (0.6 + r() * 0.8);
    const fade = (1 - clamp(d / L, 0, 1)) * clamp(alphaScale, 0, 1);
    if (fade <= 0.005) continue;
    const px = x + Math.cos(a) * sp * dd;
    const py = y + Math.sin(a) * sp * dd + (kind === 'ember' ? -gravity * 0.3 * dd * dd : 0.5 * gravity * dd * dd);
    const col = colors[i % colors.length];

    ctx.save();
    safeAlpha(ctx, fade);
    if (kind === 'spark') {
      const vx = Math.cos(a) * sp;
      const vy = Math.sin(a) * sp + gravity * dd;
      const vl = Math.hypot(vx, vy) || 1;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px - (vx / vl) * sz * 2.6, py - (vy / vl) * sz * 2.6);
      ctx.lineWidth = Math.max(1, sz * 0.5);
      ctx.lineCap = 'round';
      ctx.strokeStyle = col;
      ctx.stroke();
    } else if (kind === 'spray' || kind === 'dust') {
      const s2 = sz * (1 + d * 2.2);
      ctx.beginPath();
      ctx.ellipse(px, py, Math.max(0.5, s2), Math.max(0.5, s2 * 0.72), 0, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
    } else if (kind === 'ember') {
      const rad = Math.max(1, sz * 1.8);
      const g = ctx.createRadialGradient(px, py, 0, px, py, rad);
      g.addColorStop(0, col);
      g.addColorStop(1, 'rgba(255,200,80,0)');
      ctx.fillStyle = g;
      ctx.fillRect(px - rad, py - rad, rad * 2, rad * 2);
    }
    ctx.restore();
    drawn += 1;
  }
  return drawn;
}

/**
 * Subtle stone-step dust / water-skid puff at feet on landing or slip recovery.
 */
export function landDust(ctx, t, t0, x, y, s = 1, color = 'rgba(196, 186, 172, 0.55)') {
  const d = Number(t) - Number(t0);
  if (!ctx || d < 0 || d > 0.5) return 0;
  const k = eOut(d / 0.5);
  const a = clamp(1 - d / 0.5, 0, 1);
  ctx.save();
  safeAlpha(ctx, a);
  for (const sg of [-1, 1]) {
    for (let i = 0; i < 3; i++) {
      const px = x + sg * (18 + k * (42 + i * 18)) * s;
      const py = y - (4 + i * 5) * s - k * 7 * s;
      const rad = Math.max(1, (10 + i * 3.5) * s * (1 - 0.3 * k));
      ctx.beginPath();
      ctx.ellipse(px, py, rad, rad * 0.72, 0, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }
  }
  ctx.restore();
  return 6;
}

/**
 * Subtle expanding tension / lantern relight ring.
 */
export function ring(ctx, t, t0, x, y, r1 = 90, { dur = 0.38, w = 4, color = 'rgba(255, 232, 168, 0.65)', squash = 1 } = {}) {
  const d = Number(t) - Number(t0);
  if (!ctx || d < 0 || d > dur) return 0;
  const k = eOut(d / dur);
  const a = clamp(1 - d / dur, 0, 1);
  ctx.save();
  safeAlpha(ctx, a);
  ctx.beginPath();
  ctx.ellipse(x, y, Math.max(1, r1 * k), Math.max(1, r1 * k * squash), 0, 0, Math.PI * 2);
  ctx.lineWidth = Math.max(0.5, w * (1 - k * 0.7));
  ctx.strokeStyle = color;
  ctx.stroke();
  ctx.restore();
  return 1;
}

/**
 * Motion afterimages for fast lantern swing or sudden slip catch.
 */
export function afterimages(ctx, g, draw, { n = 3, gap = 0.032, alpha = 0.24 } = {}) {
  if (!ctx || typeof draw !== 'function') return 0;
  let count = 0;
  for (let i = n; i >= 1; i--) {
    const layerAlpha = clamp(alpha * (1 - i / (n + 1)), 0, 1);
    if (layerAlpha <= 0.005) continue;
    ctx.save();
    safeAlpha(ctx, layerAlpha);
    draw(ctx, g - i * gap, i);
    ctx.restore();
    count += 1;
  }
  return count;
}

/**
 * Feature-gated interaction FX dispatcher (`motionPlan.fx_profile`).
 * Returns count of active FX primitives drawn at `realT` (0 when `fxProfile === 'none'`).
 */
export function applyHarborInteractionFX(ctx, { fxProfile = 'none', realT = 0, events = [], seed = 1476 } = {}) {
  if (!fxProfile || fxProfile === 'none' || !Array.isArray(events) || events.length === 0) {
    return 0;
  }
  let totalDrawn = 0;
  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    const t0 = Number(ev.t0 ?? ev.time ?? 0);
    const x = Number(ev.x ?? 0);
    const y = Number(ev.y ?? 0);
    const evSeed = Number(ev.seed ?? seed + i * 31);
    if (ev.kind === 'foot_slip_spray') {
      totalDrawn += landDust(ctx, realT, t0, x, y, Number(ev.scale ?? 0.85), 'rgba(182, 206, 224, 0.48)');
      totalDrawn += burstParticles(ctx, realT, t0, x, y - 4, {
        kind: 'spray',
        n: 7,
        speed: 155,
        life: 0.42,
        gravity: 440,
        size: 3.5,
        colors: ['rgba(216,236,248,0.75)', 'rgba(168,198,218,0.6)'],
        seed: evSeed,
        alphaScale: 0.65,
      });
    } else if (ev.kind === 'rope_strain_dust') {
      totalDrawn += burstParticles(ctx, realT, t0, x, y, {
        kind: 'dust',
        n: 6,
        speed: 95,
        life: 0.36,
        gravity: 260,
        size: 3.0,
        colors: ['rgba(212,184,132,0.55)', 'rgba(184,154,104,0.45)'],
        seed: evSeed,
        alphaScale: 0.55,
      });
    } else if (ev.kind === 'lantern_gust_embers') {
      totalDrawn += burstParticles(ctx, realT, t0, x, y, {
        kind: 'ember',
        n: 8,
        speed: 140,
        life: 0.55,
        gravity: 220,
        size: 4.5,
        dir: Number(ev.dir ?? -0.35),
        spread: 0.9,
        colors: ['#FFD86B', '#FFA63B', '#FFF2C2'],
        seed: evSeed,
        alphaScale: 0.72,
      });
    } else if (ev.kind === 'beacon_relight_pulse') {
      totalDrawn += ring(ctx, realT, t0, x, y, Number(ev.radius ?? 110), {
        dur: 0.45,
        w: 3.5,
        color: 'rgba(255, 226, 148, 0.55)',
      });
    }
  }
  return totalDrawn;
}
