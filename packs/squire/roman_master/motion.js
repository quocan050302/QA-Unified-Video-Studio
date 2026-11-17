// motion.js — Pilot-scoped deterministic 2D keyframe, C1 curve, IK contact & secondary motion for KH-03.0.
// Preserves original Production Squire soldier() silhouette and proportions 100%.
// NOTE: Scoped to KH-03.0 pilot; NOT the generalized KH-03.2 Natural Motion Engine.
import { clamp, lerp } from '../ink.js';
import { CAST, POSES, STEP, ik2, blinkAt } from '../chara.js';

const D2R = Math.PI / 180;
const R2D = 180 / Math.PI;

// C1-continuous smoothstep (zero derivative at endpoints: 3k^2 - 2k^3)
export function c1Smooth(k) {
  const x = clamp(k, 0, 1);
  return x * x * (3 - 2 * x);
}

// C2-continuous quintic smoothstep (6k^5 - 15k^4 + 10k^3)
export function c2Smooth(k) {
  const x = clamp(k, 0, 1);
  return x * x * x * (x * (x * 6 - 15) + 10);
}

// Fast-out impact settle curve (C1 continuous when joined from impact peak)
export function settleCurve(k) {
  const x = clamp(k, 0, 1);
  return 1 - Math.pow(1 - x, 3) * Math.cos(x * Math.PI * 1.35);
}

const EASINGS = {
  linear: (k) => clamp(k, 0, 1),
  c1: c1Smooth,
  c2: c2Smooth,
  outCubic: (k) => { const x = clamp(k, 0, 1); return 1 - Math.pow(1 - x, 3); },
  inCubic: (k) => { const x = clamp(k, 0, 1); return x * x * x; },
  settle: settleCurve,
  hold: () => 0,
};

// Evaluate piecewise keyframe track [[t0, v0, easeName?], [t1, v1, easeName?], ...]
export function sampleTrack(t, keys, fallback = 0) {
  if (!Array.isArray(keys) || keys.length === 0) return fallback;
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const prev = keys[i - 1];
    const curr = keys[i];
    if (t <= curr[0]) {
      const dt = Math.max(1e-6, curr[0] - prev[0]);
      const rawK = clamp((t - prev[0]) / dt, 0, 1);
      const mode = curr[2] || 'c1';
      if (mode === 'hold') return prev[1];
      const fn = EASINGS[mode] || c1Smooth;
      const k = fn(rawK);
      if (Array.isArray(prev[1]) && Array.isArray(curr[1])) {
        return prev[1].map((v, idx) => lerp(v, curr[1][idx], k));
      }
      return lerp(prev[1], curr[1], k);
    }
  }
  return keys[keys.length - 1][1];
}

// Discrete step track [[t0, label], [t1, label], ...]
export function sampleDiscrete(t, keys, fallback) {
  if (!Array.isArray(keys) || keys.length === 0) return fallback;
  let val = fallback ?? keys[0][1];
  for (const [kt, kv] of keys) {
    if (t >= kt - 1e-6) val = kv;
  }
  return val;
}

// Numerical derivative for velocity/acceleration inspection & secondary lag
export function sampleTrackDerivative(t, keys, fallback = 0, eps = 1 / 120) {
  const v0 = sampleTrack(t - eps, keys, fallback);
  const v1 = sampleTrack(t + eps, keys, fallback);
  if (Array.isArray(v0) && Array.isArray(v1)) {
    return v0.map((a, i) => (v1[i] - a) / (2 * eps));
  }
  return (v1 - v0) / (2 * eps);
}

function invTransformRoot(wx, wy, rootX, rootY, flip, totalRot) {
  const dirSign = flip ? -1 : 1;
  const dx = dirSign * (wx - rootX);
  const dy = wy - rootY;
  const c = Math.cos(totalRot);
  const s = Math.sin(totalRot);
  return [dx * c + dy * s, -dx * s + dy * c];
}

function fwdTransformRoot(lx, ly, rootX, rootY, flip, totalRot) {
  const dirSign = flip ? -1 : 1;
  const c = Math.cos(totalRot);
  const s = Math.sin(totalRot);
  const rx = lx * c - ly * s;
  const ry = lx * s + ly * c;
  return [rootX + dirSign * rx, rootY + ry];
}

// Solve world-locked foot-plant coordinates for soldier() legs()
export function solveRomanFootPlant(actorRoot, actorH, leftFootWorld, rightFootWorld, flip = false, bodyRot = 0) {
  const [rx, ry] = actorRoot;
  const u = actorH / 100;
  const hipY = -30 * u;
  const fy0 = -3.2 * u;
  const L1 = ((30 - 3.2 + 1.5) / 2) * u;
  const L2 = L1;

  const solveOne = (hxU, worldPt, bend) => {
    const [lx, ly] = invTransformRoot(worldPt[0], worldPt[1], rx, ry, flip, bodyRot);
    const pts = ik2(hxU * u, hipY, lx, ly + fy0, L1, L2, bend);
    const ankleLocal = pts[2];
    const soleLocal = [ankleLocal[0], ankleLocal[1] - fy0];
    const achievedWorld = fwdTransformRoot(soleLocal[0], soleLocal[1], rx, ry, flip, bodyRot);
    const driftPx = Math.hypot(achievedWorld[0] - worldPt[0], achievedWorld[1] - worldPt[1]);
    return {
      local: [lx, ly],
      achievedWorld,
      driftPx,
      planted: driftPx <= 1.25,
    };
  };

  const left = solveOne(-6.2, leftFootWorld, 0.3);
  const right = solveOne(6.2, rightFootWorld, -0.3);
  return {
    leftFootLocal: left.local,
    rightFootLocal: right.local,
    leftAchievedWorld: left.achievedWorld,
    rightAchievedWorld: right.achievedWorld,
    leftDriftPx: left.driftPx,
    rightDriftPx: right.driftPx,
    bothPlanted: left.planted && right.planted,
  };
}

// Solve exact 2-segment arm angles (sh, el in degrees) matching chara.js::armPts()
export function solveArmAnglesU(side, targetHxU, targetHyU, bend = 1) {
  const sx = side * 12.2;
  const sy = -54.0;
  const Lseg = 12.5;
  const [S, Eb, H] = ik2(sx, sy, targetHxU, targetHyU, Lseg, Lseg, bend);
  const dx1 = Eb[0] - S[0];
  const dy1 = Eb[1] - S[1];
  const dx2 = H[0] - Eb[0];
  const dy2 = H[1] - Eb[1];
  // In armPts: ex = sx + side * sin(a1)*L, ey = sy + cos(a1)*L
  const a1 = Math.atan2(side * dx1, dy1);
  const a2 = Math.atan2(side * dx2, dy2);
  return {
    shDeg: a1 * R2D,
    elDeg: (a2 - a1) * R2D,
    handU: H,
    elbowU: Eb,
    shoulderU: S,
    handToTargetU: Math.hypot(H[0] - targetHxU, H[1] - targetHyU),
  };
}

// Resolve hand-to-scutum anchor in both local soldier units and world pixels
export function solveRomanShieldGrip(actorRoot, actorH, shieldWorldTarget, opts = {}) {
  const [rx, ry] = actorRoot;
  const u = actorH / 100;
  const flip = !!opts.flip;
  const bodyRot = opts.bodyRot || 0;
  const brPx = (opts.bobU || 0) * u;

  const [lx, ly] = invTransformRoot(shieldWorldTarget[0], shieldWorldTarget[1], rx, ry, flip, bodyRot);
  // In soldier(): g.translate(0, br) is active, and shield() is called at (sxp, syp + br) -> total y offset = syp + 2*br
  const shX_u = lx / u;
  const shY_u = (ly - 2 * brPx) / u;
  // Inner grip strap sits slightly toward torso from shield boss
  const gripX_u = opts.gripOffsetXU !== undefined ? shX_u + opts.gripOffsetXU : shX_u - 1.5;
  const gripY_u = opts.gripOffsetYU !== undefined ? shY_u + opts.gripOffsetYU : (ly - brPx) / u;

  const armSol = solveArmAnglesU(-1, gripX_u, gripY_u, opts.elbowBend ?? -1);
  const handWorld = fwdTransformRoot(armSol.handU[0] * u, armSol.handU[1] * u + brPx, rx, ry, flip, bodyRot);
  const shieldCenterWorld = fwdTransformRoot(shX_u * u, shY_u * u + 2 * brPx, rx, ry, flip, bodyRot);
  const scutumS = (opts.scutumSizeU || 62) * u;
  const scutumRx = scutumS * 0.33;
  const shRot = opts.shieldRot ?? -0.04;
  const rimRightLocal = [shX_u * u + Math.cos(shRot) * scutumRx, shY_u * u + 2 * brPx + Math.sin(shRot) * scutumRx];
  const rimLeftLocal = [shX_u * u - Math.cos(shRot) * scutumRx, shY_u * u + 2 * brPx - Math.sin(shRot) * scutumRx];

  return {
    shX_u,
    shY_u,
    shieldRot: shRot,
    scutumSizeU: opts.scutumSizeU || 62,
    lshDeg: armSol.shDeg,
    lelDeg: armSol.elDeg,
    handWorld,
    shieldCenterWorld,
    rimRightWorld: fwdTransformRoot(rimRightLocal[0], rimRightLocal[1], rx, ry, flip, bodyRot),
    rimLeftWorld: fwdTransformRoot(rimLeftLocal[0], rimLeftLocal[1], rx, ry, flip, bodyRot),
    gripDriftPx: Math.hypot(handWorld[0] - shieldCenterWorld[0], handWorld[1] - shieldCenterWorld[1]),
    contactLocked: armSol.handToTargetU * u <= Math.max(6.5, 4.5 * u),
  };
}

// Seeded, physically motivated secondary motion (plume lag, tunic sway, breathing, blink)
export function evaluateRomanSecondaryMotionAt(globalT, velocityX = 0, accelX = 0, seed = 1, opts = {}) {
  const breathFreq = 1.7; // matches chara.js line 785: Math.sin(t * 1.7 + seed) * 0.6
  const tLocal = globalT + (seed || 0) * 0.31;
  const breathBobU = Math.sin(tLocal * breathFreq + (seed || 0)) * 0.6;
  const plumeIdle = Math.sin(tLocal * 2.35 + seed * 1.1) * 0.024;
  const featherBend = clamp(-velocityX * 0.00075 - accelX * 0.00018 + plumeIdle, -0.26, 0.26);
  const skirtSway = clamp(-velocityX * 0.0038 - accelX * 0.0006 + Math.sin(tLocal * 1.9 + seed * 0.7) * 0.16, -1.45, 1.45);
  const tremorAmp = opts.tremor || 0;
  const scutumTremorU = tremorAmp > 0
    ? (Math.sin(globalT * 37.0 + seed * 2.3) * 0.65 + Math.cos(globalT * 53.0 + seed) * 0.35) * tremorAmp
    : 0;
  const blink = opts.blinkOverride !== undefined ? opts.blinkOverride : blinkAt(tLocal, seed);

  return Object.freeze({
    tLocal,
    breathBobU,
    featherBend,
    skirtSway,
    scutumTremorU,
    blink,
  });
}

// Deterministic pose evaluator: derives 100% from (globalT, shot, actor, worldState) with zero mutable state
export function evaluateRomanActorPoseAt(globalT, shot, actor = {}, worldState = {}) {
  const W = worldState.W || 1920;
  const H = worldState.H || 1080;
  const start = shot?.start ?? 0;
  const lt = clamp(globalT - start, 0, Math.max(0.001, (shot?.end ?? 30) - start));
  const seed = actor.seed ?? 11;
  const flip = !!actor.flip;
  const dirSign = flip ? -1 : 1;

  const actorH = (actor.hFrac ?? 0.56) * H;
  const u = actorH / 100;

  const rootXFrac = sampleTrack(lt, actor.rootXKeys, actor.xFrac ?? 0.5);
  const rootYFrac = sampleTrack(lt, actor.rootYKeys, actor.yFrac ?? 0.88);
  const velX = sampleTrackDerivative(lt, actor.rootXKeys, actor.xFrac ?? 0.5) * W * dirSign;
  const velX2 = sampleTrackDerivative(lt + 1 / 120, actor.rootXKeys, actor.xFrac ?? 0.5) * W * dirSign;
  const accelX = (velX2 - velX) * 120;

  const rootX = rootXFrac * W;
  const rootY = rootYFrac * H;
  const bodyRot = sampleTrack(lt, actor.bodyRotKeys, actor.bodyRot ?? 0);
  const headNodU = sampleTrack(lt, actor.headNodKeys, actor.headNodU ?? 0);
  const headRot = sampleTrack(lt, actor.headRotKeys, actor.headRot ?? 0);
  const look = sampleTrack(lt, actor.lookKeys, actor.look ?? 0);
  const face = sampleDiscrete(lt, actor.faceKeys, actor.face || 'neutral');
  const phase = sampleDiscrete(lt, actor.phaseKeys, actor.phase || 'idle');
  const tremor = sampleTrack(lt, actor.tremorKeys, actor.tremor ?? 0);
  const hipBobU = actor.hipBobUKeys ? sampleTrack(lt, actor.hipBobUKeys, actor.hipBobU ?? 0) : (actor.hipBobU ?? 0);

  const sec = evaluateRomanSecondaryMotionAt(globalT, velX, accelX, seed, {
    tremor,
    blinkOverride: actor.blinkKeys ? sampleDiscrete(lt, actor.blinkKeys, undefined) : undefined,
  });

  // World-space foot plant
  const defaultSpanPx = 7.2 * u;
  const leftFootX = actor.leftFootXKeys
    ? sampleTrack(lt, actor.leftFootXKeys, rootXFrac) * W
    : rootX - dirSign * defaultSpanPx;
  const leftFootY = actor.leftFootYKeys
    ? sampleTrack(lt, actor.leftFootYKeys, rootYFrac) * H
    : rootY;
  const rightFootX = actor.rightFootXKeys
    ? sampleTrack(lt, actor.rightFootXKeys, rootXFrac) * W
    : rootX + dirSign * defaultSpanPx;
  const rightFootY = actor.rightFootYKeys
    ? sampleTrack(lt, actor.rightFootYKeys, rootYFrac) * H
    : rootY;

  const footSol = solveRomanFootPlant(
    [rootX, rootY],
    actorH,
    [leftFootX, leftFootY],
    [rightFootX, rightFootY],
    flip,
    bodyRot
  );

  // Shield world target or local u-space target
  let shieldSol = null;
  let lsh = POSES.stand[0];
  let lel = POSES.stand[1];
  if (actor.hasShield !== false) {
    const shOffU = sampleTrack(lt, actor.shieldOffsetUKeys, actor.shieldOffsetU || [-11, -38]);
    const shRot = sampleTrack(lt, actor.shieldRotKeys, actor.shieldRot ?? -0.05);
    const shTremX = sec.scutumTremorU;
    const shWorldTarget = actor.shieldWorldXKeys
      ? [
          sampleTrack(lt, actor.shieldWorldXKeys, rootXFrac) * W + shTremX * u,
          sampleTrack(lt, actor.shieldWorldYKeys, rootYFrac - 0.38 * (actorH / H)) * H,
        ]
      : fwdTransformRoot((shOffU[0] + shTremX) * u, shOffU[1] * u + 2 * sec.breathBobU * u, rootX, rootY, flip, bodyRot);

    shieldSol = solveRomanShieldGrip([rootX, rootY], actorH, shWorldTarget, {
      flip,
      bodyRot,
      bobU: sec.breathBobU,
      shieldRot: shRot,
      scutumSizeU: actor.scutumSizeU || 62,
      elbowBend: actor.leftElbowBend ?? -1,
    });
    lsh = shieldSol.lshDeg;
    lel = shieldSol.lelDeg;
  } else if (actor.leftArmDegKeys) {
    const la = sampleTrack(lt, actor.leftArmDegKeys, [18, 20]);
    lsh = la[0];
    lel = la[1];
  }

  // Right arm & weapon
  const rHandU = sampleTrack(lt, actor.rightHandUKeys, actor.rightHandU || [15.5, -35.5]);
  const rArmSol = solveArmAnglesU(1, rHandU[0], rHandU[1], actor.rightElbowBend ?? 1);
  let rsh = rArmSol.shDeg;
  let rel = rArmSol.elDeg;
  if (actor.rightArmDegKeys) {
    const ra = sampleTrack(lt, actor.rightArmDegKeys, [rsh, rel]);
    rsh = ra[0];
    rel = ra[1];
  }
  const weaponKind = actor.weapon !== undefined ? actor.weapon : (CAST[actor.preset || 'hastatus']?.weapon || 'spear');
  const weaponLenU = actor.weaponLenU || (weaponKind === 'pilum' ? 60 : 62);
  const weaponAng = sampleTrack(lt, actor.weaponAngKeys, actor.weaponAng ?? Math.PI);

  // Compute exact right hand & spear tip in world space
  const a1 = rsh * D2R;
  const a2 = (rsh + rel) * D2R;
  const rEx = 12.2 + Math.sin(a1) * 12.5;
  const rEy = -54.0 + Math.cos(a1) * 12.5;
  const rHx = rEx + Math.sin(a2) * 12.5;
  const rHy = rEy + Math.cos(a2) * 12.5;
  const rightHandWorld = fwdTransformRoot(rHx * u, (rHy + sec.breathBobU) * u, rootX, rootY, flip, bodyRot);
  // In weapon(): g.translate(hx, hy); g.rotate(ang); tip at [0, front * 1.02] -> local delta [-sin(ang)*L, cos(ang)*L]
  const tipLocalX = rHx * u - Math.sin(weaponAng) * (weaponLenU * 1.02 * u);
  const tipLocalY = (rHy + sec.breathBobU) * u + Math.cos(weaponAng) * (weaponLenU * 1.02 * u);
  const buttLocalX = rHx * u + Math.sin(weaponAng) * (weaponLenU * 0.35 * u);
  const buttLocalY = (rHy + sec.breathBobU) * u - Math.cos(weaponAng) * (weaponLenU * 0.35 * u);
  const spearTipWorld = weaponKind ? fwdTransformRoot(tipLocalX, tipLocalY, rootX, rootY, flip, bodyRot) : null;
  const spearButtWorld = weaponKind ? fwdTransformRoot(buttLocalX, buttLocalY, rootX, rootY, flip, bodyRot) : null;

  const headWorld = fwdTransformRoot(0, (-78 + headNodU + sec.breathBobU) * u, rootX, rootY, flip, bodyRot);

  return Object.freeze({
    actorId: actor.actorId || 'rookie',
    archetypeId: actor.archetypeId || 'rookie_hastatus',
    preset: actor.preset || 'hastatus',
    globalT,
    localT: lt,
    phase,
    flip,
    rootWorld: Object.freeze([rootX, rootY]),
    actorH,
    u,
    bodyRot,
    headNodU,
    headRot,
    headWorld: Object.freeze(headWorld),
    headRadiusPx: 19 * u,
    look,
    face,
    blink: sec.blink,
    featherBend: sec.featherBend,
    skirtSway: sec.skirtSway,
    breathBobU: sec.breathBobU,
    hipBobU,
    leftKneeBend: actor.leftKneeBend,
    rightKneeBend: actor.rightKneeBend,
    courierSatchel: !!actor.courierSatchel,
    shoeMode: actor.shoeMode,
    armsAng: Object.freeze([lsh, lel, rsh, rel]),
    footPlant: Object.freeze(footSol),
    shieldGrip: shieldSol ? Object.freeze(shieldSol) : null,
    hasShield: actor.hasShield !== false,
    weapon: weaponKind,
    weaponLenU,
    weaponAng,
    rightHandWorld: Object.freeze(rightHandWorld),
    spearTipWorld: spearTipWorld ? Object.freeze(spearTipWorld) : null,
    spearButtWorld: spearButtWorld ? Object.freeze(spearButtWorld) : null,
    stepStridePx: STEP * u,
  });
}
