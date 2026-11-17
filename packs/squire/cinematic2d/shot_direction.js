// shot_direction.js (packs/squire/cinematic2d) — Bounded 2D Camera & Deterministic Pose Helpers for KH-02.1 Preview.
// NOTE (Scope Honesty): Minimal bounded 2D helpers for the KH-02.1 30s preview; NOT the future full KH-02.3/KH-02.4 engine.

import { E, clamp, lerp, ease, kf } from '/engine/core.js';

export const KH02_CAMERA_LIMITS = {
  minZoom: 0.94,
  maxZoom: 1.35,
  maxPanX: 380,
  maxPanY: 220,
  maxRotRad: 0.045,
};

export function resolve2DCameraAt(lt, dur, spec = {}) {
  const safeDur = Math.max(0.05, dur || 1);
  if (spec.keys && Array.isArray(spec.keys) && spec.keys.length > 0) {
    // keys: [[tNorm, [z, x, y, r]], ...]
    const tNorm = clamp(lt / safeDur, 0, 1);
    const easeFn = ease[spec.ease || 'inOut'] || ease.inOut;
    const [z, x, y, r] = kf(tNorm, spec.keys, easeFn);
    return _clampCam2D({ z, x, y, r: r || 0 });
  }
  const k = (ease[spec.ease || 'inOut'] || ease.inOut)(clamp(lt / safeDur, 0, 1));
  const z = lerp(spec.z0 ?? 1.0, spec.z1 ?? 1.0, k);
  const x = lerp(spec.x0 ?? 0, spec.x1 ?? 0, k);
  const y = lerp(spec.y0 ?? 0, spec.y1 ?? 0, k);
  const r = lerp(spec.r0 ?? 0, spec.r1 ?? 0, k);
  return _clampCam2D({ z, x, y, r });
}

function _clampCam2D(cam) {
  const z = clamp(cam.z ?? 1, KH02_CAMERA_LIMITS.minZoom, KH02_CAMERA_LIMITS.maxZoom);
  const maxX = Math.min(KH02_CAMERA_LIMITS.maxPanX, (E.W * (z - 0.92)) * 0.48 + 90);
  const maxY = Math.min(KH02_CAMERA_LIMITS.maxPanY, (E.H * (z - 0.92)) * 0.48 + 60);
  return {
    z,
    x: clamp(cam.x || 0, -maxX, maxX),
    y: clamp(cam.y || 0, -maxY, maxY),
    r: clamp(cam.r || 0, -KH02_CAMERA_LIMITS.maxRotRad, KH02_CAMERA_LIMITS.maxRotRad),
  };
}

export function evaluate2DActionAt(lt, phases = []) {
  // Pure function stateAt(lt): evaluates non-looping action phases [{start, end, name, from, to, ease}]
  if (!phases || phases.length === 0) {
    return { phaseName: 'hold', progress: 0, value: 0 };
  }
  for (let i = 0; i < phases.length; i++) {
    const p = phases[i];
    if (lt <= p.end || i === phases.length - 1) {
      const kRaw = clamp((lt - p.start) / Math.max(0.001, p.end - p.start), 0, 1);
      const fn = ease[p.ease || 'inOut'] || ease.inOut;
      const k = fn(kRaw);
      const val = Array.isArray(p.from)
        ? p.from.map((v, j) => lerp(v, p.to[j], k))
        : lerp(p.from ?? 0, p.to ?? 1, k);
      return { phaseName: p.name || `phase_${i}`, progress: k, rawProgress: kRaw, value: val };
    }
  }
  const last = phases[phases.length - 1];
  return { phaseName: last.name || 'end', progress: 1, rawProgress: 1, value: last.to ?? 1 };
}

export function drawCinematic2DLayers(g, cam, layerDefs = []) {
  for (const def of layerDefs) {
    if (!def || typeof def.draw !== 'function') continue;
    const depth = def.depth ?? 1.0;
    const cx = E.W / 2, cy = E.H / 2;
    const zz = 1 + ((cam?.z ?? 1) - 1) * depth;
    g.save();
    g.translate(cx, cy);
    g.rotate((cam?.r || 0) * depth);
    g.scale(zz, zz);
    g.translate(-cx - (cam?.x || 0) * depth, -cy - (cam?.y || 0) * depth);
    def.draw(g);
    g.restore();
  }
}
