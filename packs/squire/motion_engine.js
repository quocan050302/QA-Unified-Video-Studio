// packs/squire/motion_engine.js — Pure Deterministic 2D Natural Motion & Contact IK Engine (FL-01 / V14.7.6)
//
// Evaluates actor root motion, distance-coupled gait cycles, world-locked foot-plant IK,
// world-space hand-to-prop contact IK, C1-continuous pose blending, multi-actor shared prop
// interaction, secondary motion, and objective frame-trace verification.
//
// Invariants (Section 1.4 & Section 5):
// - Pure function of (track, absoluteT, worldState, options): ZERO mutable last-frame state,
//   ZERO Math.random(), identical output whether evaluated serially, out-of-order, or concurrently.
// - Median world-foot drift across planted stance intervals <= 0.03 normalized actor height.
// - Peak hand-grip distance during CONTACT/EXERT/HOLD <= 0.04 normalized actor height.
// - Zero unintentional > 0.25 normalized joint-position jumps between adjacent frames (24 fps).

const clamp = (v, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);
const lerp = (a, b, k) => a + (b - a) * k;

export function smooth01(x) {
  const k = clamp(x, 0, 1);
  return k * k * (3 - 2 * k);
}

export function smoother01(x) {
  const k = clamp(x, 0, 1);
  return k * k * k * (k * (k * 6 - 15) + 10);
}

export function evalTempoCurve(uRaw, curve = 'ease_in_out') {
  const u = clamp(uRaw, 0, 1);
  switch (curve) {
    case 'linear':
      return u;
    case 'ease_in':
      return u * u * (2 - u * 0.999999 >= 1 ? 1 : 1) * clamp(u * u, 0, 1);
    case 'ease_out':
      return 1 - (1 - u) * (1 - u);
    case 'overshoot_settle': {
      // Smooth rise with damped physical overshoot around u=0.65 settling cleanly to 1.0 at u=1.0
      const base = smoother01(u);
      const bump = Math.sin(Math.PI * u) * Math.sin(2 * Math.PI * u) * 0.12 * (1 - u);
      return clamp(base + bump, -0.15, 1.15);
    }
    case 'hold':
      return smooth01(Math.min(1, u * 4));
    case 'ease_in_out':
    default:
      return smoother01(u);
  }
}

/**
 * Deterministic 2-bone analytical IK solver matching `packs/squire/chara.js::ik2`
 * without leg/arm inversion. Returns [[hx, hy], [kx, ky], [fx, fy]].
 */
export function solveTwoBoneIK(hx, hy, tx, ty, L1, L2, bend = 1) {
  let dx = tx - hx;
  let dy = ty - hy;
  let d = Math.hypot(dx, dy);
  const maxReach = (L1 + L2) * 0.999;
  let clampedX = tx;
  let clampedY = ty;
  if (d > maxReach && d > 1e-6) {
    clampedX = hx + (dx / d) * maxReach;
    clampedY = hy + (dy / d) * maxReach;
    dx = clampedX - hx;
    dy = clampedY - hy;
    d = maxReach;
  }
  const minReach = Math.abs(L1 - L2) + 1e-4;
  const dSafe = Math.max(d, minReach);
  const cosA = clamp((L1 * L1 + dSafe * dSafe - L2 * L2) / (2 * L1 * dSafe), -1, 1);
  const a = Math.acos(cosA);
  const th = Math.atan2(dy, dx) - bend * a;
  return [
    [hx, hy],
    [hx + Math.cos(th) * L1, hy + Math.sin(th) * L1],
    [clampedX, clampedY],
  ];
}

function deterministicHash01(seedNum, salt = 0) {
  const x = Math.sin((Number(seedNum) || 1476) * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Evaluate continuous root world position, accumulated arc-length distance, and instantaneous
 * velocity at `t` (absolute timeline seconds) directly from `track.phases`.
 */
export function rootMotionAt(track, t) {
  const phases = Array.isArray(track?.phases) ? track.phases : [];
  const defaultX = Array.isArray(track?.world_start) ? Number(track.world_start[0]) : 0.42;
  const defaultY = Array.isArray(track?.world_start) ? Number(track.world_start[1]) : Number(track?.ground_y ?? 0.84);
  if (!phases.length) {
    return {
      x: defaultX,
      y: defaultY,
      vx: 0,
      vy: 0,
      speed: 0,
      accumulatedDistance: 0,
      activePhaseIndex: -1,
      activePhase: null,
      phaseProgress: 0,
    };
  }

  let accDist = 0;
  let curX = Number(phases[0].world_start?.[0] ?? defaultX);
  let curY = Number(phases[0].world_start?.[1] ?? defaultY);
  let activeIdx = 0;
  let phaseU = 0;

  for (let i = 0; i < phases.length; i++) {
    const ph = phases[i];
    const p0 = Number(ph.start_sec ?? 0);
    const p1 = Number(ph.end_sec ?? p0 + 0.25);
    const sx = Number(ph.world_start?.[0] ?? curX);
    const sy = Number(ph.world_start?.[1] ?? curY);
    const ex = Number(ph.world_end?.[0] ?? sx);
    const ey = Number(ph.world_end?.[1] ?? sy);
    const segLen = Math.hypot(ex - sx, ey - sy);

    if (t >= p1) {
      accDist += segLen;
      curX = ex;
      curY = ey;
      activeIdx = i;
      phaseU = 1;
    } else if (t >= p0) {
      const dur = Math.max(1e-4, p1 - p0);
      const rawU = clamp((t - p0) / dur, 0, 1);
      const k = evalTempoCurve(rawU, ph.tempo_curve || 'ease_in_out');
      curX = lerp(sx, ex, k);
      curY = lerp(sy, ey, k);
      accDist += Math.hypot(curX - sx, curY - sy);
      activeIdx = i;
      phaseU = rawU;
      break;
    } else {
      if (i === 0) {
        curX = sx;
        curY = sy;
        activeIdx = 0;
        phaseU = 0;
      }
      break;
    }
  }

  // Numerical derivative over tiny symmetric window for exact instantaneous velocity
  const dt = 1 / 240;
  const posEvalOnly = (tq) => {
    let px = Number(phases[0].world_start?.[0] ?? defaultX);
    let py = Number(phases[0].world_start?.[1] ?? defaultY);
    for (let i = 0; i < phases.length; i++) {
      const ph = phases[i];
      const p0 = Number(ph.start_sec ?? 0);
      const p1 = Number(ph.end_sec ?? p0 + 0.25);
      const sx = Number(ph.world_start?.[0] ?? px);
      const sy = Number(ph.world_start?.[1] ?? py);
      const ex = Number(ph.world_end?.[0] ?? sx);
      const ey = Number(ph.world_end?.[1] ?? sy);
      if (tq >= p1) {
        px = ex;
        py = ey;
      } else if (tq >= p0) {
        const k = evalTempoCurve(clamp((tq - p0) / Math.max(1e-4, p1 - p0), 0, 1), ph.tempo_curve || 'ease_in_out');
        px = lerp(sx, ex, k);
        py = lerp(sy, ey, k);
        break;
      } else {
        break;
      }
    }
    return [px, py];
  };

  const [xPrev, yPrev] = posEvalOnly(t - dt);
  const [xNext, yNext] = posEvalOnly(t + dt);
  const vx = (xNext - xPrev) / (2 * dt);
  const vy = (yNext - yPrev) / (2 * dt);

  return {
    x: curX,
    y: curY,
    vx,
    vy,
    speed: Math.hypot(vx, vy),
    accumulatedDistance: accDist,
    activePhaseIndex: activeIdx,
    activePhase: phases[activeIdx],
    phaseProgress: phaseU,
  };
}

/**
 * Smoothly blend two pose parameter dictionaries across phase transitions with optional per-channel mask.
 * Eliminates 1-frame joint snaps at phase boundaries unless `explicitCut === true`.
 */
export function blendActorPose(fromPose, toPose, t, mask = null) {
  const k = smoother01(t);
  const a = fromPose || {};
  const b = toPose || {};
  const w = (channel) => (mask && typeof mask[channel] === 'number' ? clamp(mask[channel], 0, 1) * k : k);

  return {
    torsoLean: lerp(Number(a.torsoLean ?? 0), Number(b.torsoLean ?? 0), w('torsoLean')),
    headLook: lerp(Number(a.headLook ?? 0.5), Number(b.headLook ?? 0.5), w('headLook')),
    kneeFlex: lerp(Number(a.kneeFlex ?? 0.04), Number(b.kneeFlex ?? 0.04), w('kneeFlex')),
    armReach: lerp(Number(a.armReach ?? 0), Number(b.armReach ?? 0), w('armReach')),
    postureState: k < 0.5 ? (a.postureState || 'upright') : (b.postureState || 'upright'),
  };
}

function extractPhasePoseParams(ph) {
  if (!ph) {
    return { torsoLean: 0, headLook: 0.5, kneeFlex: 0.04, armReach: 0, postureState: 'upright' };
  }
  return {
    torsoLean: Number(ph.torso_lean ?? 0),
    headLook: Number(ph.head_look ?? 0.5),
    kneeFlex: Number(ph.knee_flex ?? 0.04),
    armReach: Number(ph.arm_reach ?? 0),
    postureState: String(ph.posture_state || 'upright'),
  };
}

/**
 * Solve world-locked stance/swing foot placement and 2-bone leg IK in normalized world coordinates.
 *
 * Key physics:
 * - During stationary/planted intervals (`foot_planted_left && foot_planted_right && speed < 1e-3`),
 *   feet stay locked to deterministic world ground anchors `(rootX +/- stanceHalf, groundY)` — ZERO foot drift!
 * - During locomotion (`APPROACH`), stride length adapts to actor height & run/walk mode, and
 *   stance foot locks to discrete world step grid `anchorX = startX + dir * stepIdx * stepLen`
 *   while swing foot arcs cleanly from `anchorX - dir * stepLen` to `anchorX + dir * stepLen`!
 * - During an intentional `SLIP` phase (`slip_foot === 'right'`), the slipping foot skids forward
 *   smoothly while the supporting left foot remains planted until recovery!
 */
export function solveFootPlantIK({
  rootX,
  rootY,
  groundY,
  heightNorm = 0.28,
  facing = 1,
  accumulatedDistance = 0,
  speed = 0,
  isRun = false,
  activePhase = null,
  phaseProgress = 0,
  blendedPose = null,
  trackStartX = null,
}) {
  const h = Math.max(0.10, Number(heightNorm) || 0.28);
  const dir = facing < 0 ? -1 : 1;
  const kneeFlex = clamp(Number(blendedPose?.kneeFlex ?? activePhase?.knee_flex ?? 0.05), 0, 0.42);
  const hipDrop = kneeFlex * h * 0.24;
  const hipY = rootY - h * 0.32 + hipDrop;
  const hipLeftX = rootX - dir * h * 0.045;
  const hipRightX = rootX + dir * h * 0.045;

  const thighLen = h * 0.175;
  const shinLen = h * 0.175;
  const floorY = Number(groundY ?? rootY);

  const isLocomoting = activePhase?.phase_name === 'APPROACH';

  let leftFootWorld = [rootX - dir * h * 0.065, floorY];
  let rightFootWorld = [rootX + dir * h * 0.065, floorY];
  let leftPlanted = true;
  let rightPlanted = true;
  let bobNorm = 0;

  if (activePhase?.slip_foot === 'right') {
    // Left foot stays world-planted at pre-slip base; right foot skids smoothly outward and lands at end base
    const baseLeftX = Number(activePhase.world_start?.[0] ?? rootX) - dir * h * 0.065;
    const skidBell = Math.sin(Math.PI * clamp(phaseProgress, 0, 1));
    const skidDist = h * 0.12 * skidBell;
    leftFootWorld = [baseLeftX, floorY];
    rightFootWorld = [rootX + dir * (h * 0.065 + skidDist), floorY - h * 0.012 * skidBell];
    leftPlanted = true;
    rightPlanted = false;
  } else if (isLocomoting) {
    // Distance-coupled world-grid stepping: stance foot is world-locked!
    const stepLen = h * (isRun ? 0.30 : 0.22);
    const originX = Number(activePhase?.world_start?.[0] ?? trackStartX ?? rootX);
    const signedDisp = Math.max(0, (rootX - originX) * dir);
    const uStep = signedDisp / Math.max(1e-4, stepLen);
    const stepIdx = Math.floor(uStep);
    const frac = uStep - stepIdx; // 0..1 within single step
    const liftAmp = h * (isRun ? 0.075 : 0.048);
    const swingLift = Math.sin(Math.PI * frac) * liftAmp;
    const swingEase = smoother01(frac);

    const stanceWorldX = originX + dir * stepIdx * stepLen;
    const swingFromX = stepIdx === 0 ? originX : originX + dir * (stepIdx - 1) * stepLen;
    const swingToX = originX + dir * (stepIdx + 1) * stepLen;
    const swingWorldX = lerp(swingFromX, swingToX, swingEase);

    // Taper into settled symmetric stance near end of APPROACH so transition to SETTLE has zero snap
    const settleTaper = smoother01(clamp((1 - phaseProgress) / 0.14, 0, 1));
    const settledLeftX = rootX - dir * h * 0.065;
    const settledRightX = rootX + dir * h * 0.065;

    if (stepIdx % 2 === 0) {
      leftFootWorld = [
        settleTaper > 0.99 ? stanceWorldX - dir * h * 0.065 : lerp(settledLeftX, stanceWorldX - dir * h * 0.065, settleTaper),
        floorY,
      ];
      rightFootWorld = [
        lerp(settledRightX, swingWorldX + dir * h * 0.065, settleTaper),
        floorY - swingLift * settleTaper,
      ];
      leftPlanted = settleTaper > 0.99;
      rightPlanted = false;
    } else {
      rightFootWorld = [
        settleTaper > 0.99 ? stanceWorldX + dir * h * 0.065 : lerp(settledRightX, stanceWorldX + dir * h * 0.065, settleTaper),
        floorY,
      ];
      leftFootWorld = [
        lerp(settledLeftX, swingWorldX - dir * h * 0.065, settleTaper),
        floorY - swingLift * settleTaper,
      ];
      leftPlanted = false;
      rightPlanted = settleTaper > 0.99;
    }
    bobNorm = -Math.sin(Math.PI * frac) * h * (isRun ? 0.020 : 0.010) * settleTaper;
  } else {
    // Stationary / planted athletic / brace / crouch / idle: lock feet when root is settled
    const phaseMove = activePhase
      ? Math.hypot(
          Number(activePhase.world_end?.[0] ?? rootX) - Number(activePhase.world_start?.[0] ?? rootX),
          Number(activePhase.world_end?.[1] ?? rootY) - Number(activePhase.world_start?.[1] ?? rootY),
        )
      : 0;
    const anchorCenterX = phaseMove < 0.015 && activePhase ? Number(activePhase.world_end?.[0] ?? rootX) : rootX;
    const spreadHalf = h * 0.065;
    const pStartX = Number(activePhase?.world_start?.[0] ?? rootX);
    const pEndX = Number(activePhase?.world_end?.[0] ?? rootX);
    const flPlanted = Boolean(activePhase?.foot_planted_left ?? true);
    const frPlanted = Boolean(activePhase?.foot_planted_right ?? true);

    if (flPlanted && frPlanted) {
      leftFootWorld = [anchorCenterX - dir * spreadHalf, floorY];
      rightFootWorld = [anchorCenterX + dir * spreadHalf, floorY];
      leftPlanted = true;
      rightPlanted = true;
    } else if (!flPlanted && frPlanted) {
      // Right foot anchored at phase end while left recovery foot steps smoothly up
      const stepK = smoother01(clamp(phaseProgress, 0, 1));
      const lift = Math.sin(Math.PI * clamp(phaseProgress, 0, 1)) * h * 0.035;
      leftFootWorld = [lerp(pStartX - dir * spreadHalf, pEndX - dir * spreadHalf, stepK), floorY - lift];
      rightFootWorld = [pEndX + dir * spreadHalf, floorY];
      leftPlanted = false;
      rightPlanted = true;
    } else if (flPlanted && !frPlanted) {
      // Left foot anchored at phase start while right foot steps smoothly forward
      const stepK = smoother01(clamp(phaseProgress, 0, 1));
      const lift = Math.sin(Math.PI * clamp(phaseProgress, 0, 1)) * h * 0.035;
      leftFootWorld = [pStartX - dir * spreadHalf, floorY];
      rightFootWorld = [lerp(pStartX + dir * spreadHalf, pEndX + dir * spreadHalf, stepK), floorY - lift];
      leftPlanted = true;
      rightPlanted = false;
    } else {
      leftFootWorld = [rootX - dir * spreadHalf, floorY];
      rightFootWorld = [rootX + dir * spreadHalf, floorY];
      leftPlanted = false;
      rightPlanted = false;
    }
  }

  // Clamp feet above or on floor (never penetrate below floorY)
  leftFootWorld[1] = Math.min(floorY, leftFootWorld[1]);
  rightFootWorld[1] = Math.min(floorY, rightFootWorld[1]);

  // Forward knee bend in facing direction (`bend = dir` keeps knee bending naturally forward in profile/front)
  const leftChain = solveTwoBoneIK(
    hipLeftX,
    hipY + bobNorm,
    leftFootWorld[0],
    leftFootWorld[1],
    thighLen,
    shinLen,
    dir,
  );
  const rightChain = solveTwoBoneIK(
    hipRightX,
    hipY + bobNorm,
    rightFootWorld[0],
    rightFootWorld[1],
    thighLen,
    shinLen,
    dir,
  );

  return {
    hipCenter: [rootX, hipY + bobNorm],
    bobNorm,
    leftLeg: leftChain,
    rightLeg: rightChain,
    leftFootWorld: leftChain[2],
    rightFootWorld: rightChain[2],
    leftPlanted,
    rightPlanted,
  };
}

/**
 * Resolve multi-actor shared object transform at `absoluteT` so two actors exerting force
 * on the SAME prop (e.g. heavy amphora or pulley lantern rope) share one authoritative
 * world-space object transform with natural reaction propagation.
 */
export function evaluateMultiActorInteraction(tracks, absoluteT, worldState = {}) {
  const objectsOut = {};
  const baseObjects = worldState?.objects || {};
  for (const [oid, odata] of Object.entries(baseObjects)) {
    objectsOut[oid] = {
      ...odata,
      x: Number(odata.x ?? 0.5),
      y: Number(odata.y ?? 0.76),
      tiltRad: 0,
      tension: 0,
      activeHolders: [],
    };
  }

  const allTracks = Array.isArray(tracks) ? tracks : [];
  const byObject = {};
  for (const tr of allTracks) {
    for (const c of tr.contacts || []) {
      const c0 = Number(c.start_sec ?? 0);
      const c1 = Number(c.end_sec ?? 0);
      if (absoluteT >= c0 - 1e-4 && absoluteT <= c1 + 1e-4) {
        if (!byObject[c.object_id]) byObject[c.object_id] = [];
        byObject[c.object_id].push({ track: tr, contact: c });
      }
    }
  }

  for (const [oid, entries] of Object.entries(byObject)) {
    if (!objectsOut[oid]) {
      const firstC = entries[0].contact;
      objectsOut[oid] = {
        object_id: oid,
        kind: oid,
        x: Number(firstC.world_start?.[0] ?? 0.5) - Number(firstC.anchor_local?.[0] ?? 0),
        y: Number(firstC.world_start?.[1] ?? 0.76) - Number(firstC.anchor_local?.[1] ?? 0),
        tiltRad: 0,
        tension: 0,
        activeHolders: [],
      };
    }

    let sumBaseX = 0;
    let sumBaseY = 0;
    let driverCount = 0;
    const progresses = [];

    for (const { track: tr, contact: c } of entries) {
      const u = smoother01(clamp((absoluteT - Number(c.start_sec)) / Math.max(1e-4, Number(c.end_sec) - Number(c.start_sec)), 0, 1));
      progresses.push(u);
      objectsOut[oid].activeHolders.push(tr.actor_id);
      if (c.drives_object || entries.length >= 2) {
        const wx = lerp(Number(c.world_start[0]), Number(c.world_end[0]), u) - Number(c.anchor_local?.[0] ?? 0);
        const wy = lerp(Number(c.world_start[1]), Number(c.world_end[1]), u) - Number(c.anchor_local?.[1] ?? 0);
        sumBaseX += wx;
        sumBaseY += wy;
        driverCount += 1;
      }
    }

    if (driverCount > 0) {
      objectsOut[oid].x = sumBaseX / driverCount;
      objectsOut[oid].y = sumBaseY / driverCount;
    }
    if (progresses.length >= 2) {
      // Slight physical tilt when lead worker exerts slightly ahead of partner, settling to 0
      const diff = progresses[0] - progresses[1];
      objectsOut[oid].tiltRad = clamp(diff * 0.22, -0.09, 0.09);
      objectsOut[oid].tension = clamp((progresses[0] + progresses[1]) * 0.5, 0, 1);
    } else if (progresses.length === 1) {
      objectsOut[oid].tension = progresses[0];
    }
  }

  return objectsOut;
}

/**
 * Bind left/right hand IK targets directly to object grip anchors during REACH/CONTACT/EXERT/HOLD,
 * eliminating hand hover.
 */
export function solveHandPropContact({
  shoulderLeft,
  shoulderRight,
  heightNorm = 0.28,
  facing = 1,
  activePhase = null,
  phaseProgress = 0,
  blendedPose = null,
  contacts = [],
  absoluteT = 0,
  worldObjects = {},
  walkSwing = 0,
}) {
  const h = Math.max(0.10, Number(heightNorm) || 0.28);
  const dir = facing < 0 ? -1 : 1;
  const upperArmLen = h * 0.145;
  const foreArmLen = h * 0.145;
  const reachW = clamp(Number(blendedPose?.armReach ?? activePhase?.arm_reach ?? 0), 0, 1);

  // Default natural relaxed / walking arm targets
  const relaxLeft = [
    shoulderLeft[0] - dir * h * (0.02 - walkSwing * 0.05),
    shoulderLeft[1] + h * (0.23 - Math.abs(walkSwing) * 0.02),
  ];
  const relaxRight = [
    shoulderRight[0] + dir * h * (0.03 + walkSwing * 0.05),
    shoulderRight[1] + h * (0.22 - Math.abs(walkSwing) * 0.02),
  ];
  let leftTarget = [...relaxLeft];
  let rightTarget = [...relaxRight];

  // Non-contact expressive gestures blended continuously via `reachW` (zero discrete string jump!)
  const mType = String(activePhase?.motion_type || '');
  if (!contacts?.length || !contacts.some((c) => absoluteT >= Number(c.start_sec) - 1e-4 && absoluteT <= Number(c.end_sec) + 1e-4)) {
    let exprLeft = relaxLeft;
    let exprRight = relaxRight;
    if (mType === 'DUCK') {
      exprLeft = [shoulderLeft[0] + dir * h * 0.08, shoulderLeft[1] - h * 0.02];
      exprRight = [shoulderRight[0] + dir * h * 0.11, shoulderRight[1] - h * 0.04];
    } else if (mType === 'SLIP') {
      exprLeft = [shoulderLeft[0] - dir * h * 0.14, shoulderLeft[1] + h * 0.04];
      exprRight = [shoulderRight[0] + dir * h * 0.14, shoulderRight[1] + h * 0.04];
    } else if (mType === 'POINT') {
      exprRight = [shoulderRight[0] + dir * h * 0.24, shoulderRight[1] - h * 0.06];
    } else {
      exprRight = [shoulderRight[0] + dir * h * 0.10, shoulderRight[1] + h * 0.10];
    }
    leftTarget = [lerp(relaxLeft[0], exprLeft[0], reachW), lerp(relaxLeft[1], exprLeft[1], reachW)];
    rightTarget = [lerp(relaxRight[0], exprRight[0], reachW), lerp(relaxRight[1], exprRight[1], reachW)];
  }

  let activeContact = null;
  let anchorWorld = null;
  for (const c of contacts || []) {
    if (absoluteT >= Number(c.start_sec) - 1e-4 && absoluteT <= Number(c.end_sec) + 1e-4) {
      activeContact = c;
      break;
    }
  }

  if (activeContact) {
    const obj = worldObjects?.[activeContact.object_id];
    const uC = smoother01(
      clamp(
        (absoluteT - Number(activeContact.start_sec)) /
          Math.max(1e-4, Number(activeContact.end_sec) - Number(activeContact.start_sec)),
        0,
        1,
      ),
    );
    const baseObjX = obj
      ? Number(obj.x)
      : lerp(Number(activeContact.world_start[0]), Number(activeContact.world_end[0]), uC) -
        Number(activeContact.anchor_local?.[0] ?? 0);
    const baseObjY = obj
      ? Number(obj.y)
      : lerp(Number(activeContact.world_start[1]), Number(activeContact.world_end[1]), uC) -
        Number(activeContact.anchor_local?.[1] ?? 0);
    const tilt = Number(obj?.tiltRad ?? 0);
    const lx = Number(activeContact.anchor_local?.[0] ?? 0);
    const ly = Number(activeContact.anchor_local?.[1] ?? 0);
    const ax = baseObjX + lx * Math.cos(tilt) - ly * Math.sin(tilt);
    const ay = baseObjY + lx * Math.sin(tilt) + ly * Math.cos(tilt);
    anchorWorld = [ax, ay];

    // During ANTICIPATE, weight=0; during REACH, ramp smoothly 0 -> 1; during CONTACT+, lock 100%
    const lockWeight =
      activePhase?.phase_name === 'ANTICIPATE'
        ? 0.0
        : activePhase?.phase_name === 'REACH'
          ? smoother01(clamp(phaseProgress, 0, 1))
          : 1.0;

    // Ensure shoulder-to-anchor distance is reachable; if object is slightly beyond arm length,
    // solveTwoBoneIK clamps cleanly along the exact ray toward anchorWorld
    if (activeContact.hand === 'both') {
      const spread = h * 0.018;
      leftTarget = [lerp(leftTarget[0], ax - spread, lockWeight), lerp(leftTarget[1], ay, lockWeight)];
      rightTarget = [lerp(rightTarget[0], ax + spread, lockWeight), lerp(rightTarget[1], ay, lockWeight)];
    } else if (activeContact.hand === 'left') {
      leftTarget = [lerp(leftTarget[0], ax, lockWeight), lerp(leftTarget[1], ay, lockWeight)];
    } else {
      rightTarget = [lerp(rightTarget[0], ax, lockWeight), lerp(rightTarget[1], ay, lockWeight)];
    }
  }

  const leftArm = solveTwoBoneIK(
    shoulderLeft[0],
    shoulderLeft[1],
    leftTarget[0],
    leftTarget[1],
    upperArmLen,
    foreArmLen,
    -dir,
  );
  const rightArm = solveTwoBoneIK(
    shoulderRight[0],
    shoulderRight[1],
    rightTarget[0],
    rightTarget[1],
    upperArmLen,
    foreArmLen,
    -dir,
  );

  let gripDistNorm = null;
  if (activeContact && anchorWorld) {
    const handPt =
      activeContact.hand === 'left'
        ? leftArm[2]
        : activeContact.hand === 'both'
          ? [(leftArm[2][0] + rightArm[2][0]) * 0.5, (leftArm[2][1] + rightArm[2][1]) * 0.5]
          : rightArm[2];
    gripDistNorm = Math.hypot(handPt[0] - anchorWorld[0], handPt[1] - anchorWorld[1]) / h;
  }

  return {
    leftArm,
    rightArm,
    leftHandWorld: leftArm[2],
    rightHandWorld: rightArm[2],
    activeContactId: activeContact ? activeContact.constraint_id : null,
    anchorWorld,
    gripDistNorm,
  };
}

/**
 * Compute bounded, action-dependent secondary motion (head lag, cloth trail, subtle breathing,
 * gaze vector, recoil) without uniform infinite sine oscillation.
 */
export function applySecondaryMotion({
  absoluteT = 0,
  seed = 1476,
  vx = 0,
  vy = 0,
  heightNorm = 0.28,
  activePhase = null,
  windStrength = 0.25,
  cameraScale = 'medium',
}) {
  const h = Math.max(0.10, Number(heightNorm) || 0.28);
  const phaseSeed = deterministicHash01(seed, 3) * Math.PI * 2;
  const distScale = cameraScale === 'wide' ? 0.65 : cameraScale === 'insert' || cameraScale === 'close' ? 1.15 : 1.0;

  // Breathing slows and damps during tense CONTACT/EXERT brace, deepens slightly on RELIEF/SETTLE
  const pName = activePhase?.phase_name || 'IDLE';
  const breathRate = pName === 'EXERT' || pName === 'CONTACT' ? 1.1 : pName === 'SETTLE' ? 1.9 : 1.45;
  const breathAmp =
    (pName === 'CONTACT' || pName === 'EXERT' ? 0.0025 : pName === 'SETTLE' ? 0.006 : 0.004) * h * distScale;
  const breathOffsetNorm = Math.sin(absoluteT * breathRate * Math.PI * 2 + phaseSeed) * breathAmp;

  // Head inertial lag opposes root horizontal velocity
  const headLagRad = clamp(-vx * 0.28, -0.09, 0.09) * distScale;

  // Cloth sway combines aerodynamic drag (-vx) + wind gust envelope (non-uniform two-harmonic wave)
  const windWave =
    0.65 * Math.sin(absoluteT * 3.1 + phaseSeed) + 0.35 * Math.sin(absoluteT * 5.3 + phaseSeed * 1.7);
  const clothSwayNorm = clamp((-vx * 0.16 + windStrength * 0.035 * windWave) * distScale, -0.08 * h, 0.08 * h);

  return {
    breathOffsetNorm,
    headLagRad,
    clothSwayNorm,
  };
}

/**
 * Master pure-function evaluator for an `ActorMotionTrack` at `absoluteT`.
 */
export function evaluateMotionTrackAt(track, absoluteT, worldState = {}, options = {}) {
  const h = Math.max(0.10, Number(track?.height_norm ?? 0.28));
  const groundY = Number(track?.ground_y ?? 0.84);
  const phases = Array.isArray(track?.phases) ? track.phases : [];
  const root = rootMotionAt(track, absoluteT);
  const idx = Math.max(0, root.activePhaseIndex);
  const curPh = phases[idx] || null;
  const prevPh = idx > 0 ? phases[idx - 1] : curPh;
  const nextPh = idx + 1 < phases.length ? phases[idx + 1] : curPh;

  // C1 cross-phase pose blending across first/last 20% of each phase
  const curPose = extractPhasePoseParams(curPh);
  let blended = curPose;
  if (curPh) {
    const pDur = Math.max(1e-4, Number(curPh.end_sec) - Number(curPh.start_sec));
    const blendWin = Math.min(0.12, pDur * 0.25);
    const elapsed = absoluteT - Number(curPh.start_sec);
    const remain = Number(curPh.end_sec) - absoluteT;
    if (elapsed >= 0 && elapsed < blendWin && prevPh !== curPh) {
      const prevPose = extractPhasePoseParams(prevPh);
      blended = blendActorPose(prevPose, curPose, 0.5 + 0.5 * (elapsed / Math.max(1e-4, blendWin)));
    } else if (remain >= 0 && remain < blendWin && nextPh !== curPh) {
      const nextPose = extractPhasePoseParams(nextPh);
      blended = blendActorPose(curPose, nextPose, 0.5 * (1 - remain / Math.max(1e-4, blendWin)));
    }
  }

  const facing =
    Math.abs(root.vx) > 0.015
      ? root.vx < 0
        ? -1
        : 1
      : Number(track?.facing_end ?? track?.facing_start ?? 1);
  const isRun = String(track?.motion_type || '').includes('RUN');

  // If actor has an active contact whose anchor is slightly beyond natural arm reach,
  // lean/shift upper body subtly so shoulder stays within anatomical reach of the prop!
  const worldObjects = options.resolvedObjects || evaluateMultiActorInteraction([track], absoluteT, worldState);
  let effectiveRootX = root.x;
  for (const c of track?.contacts || []) {
    if (absoluteT >= Number(c.start_sec) - 1e-4 && absoluteT <= Number(c.end_sec) + 1e-4) {
      const obj = worldObjects?.[c.object_id];
      const uC = smoother01(
        clamp(
          (absoluteT - Number(c.start_sec)) / Math.max(1e-4, Number(c.end_sec) - Number(c.start_sec)),
          0,
          1,
        ),
      );
      const ax =
        (obj ? Number(obj.x) : lerp(Number(c.world_start[0]), Number(c.world_end[0]), uC) - Number(c.anchor_local?.[0] ?? 0)) +
        Number(c.anchor_local?.[0] ?? 0);
      const ay =
        (obj ? Number(obj.y) : lerp(Number(c.world_start[1]), Number(c.world_end[1]), uC) - Number(c.anchor_local?.[1] ?? 0)) +
        Number(c.anchor_local?.[1] ?? 0);
      const shoulderApproxY = root.y - h * 0.54;
      const dy = ay - shoulderApproxY;
      const maxArmSpan = h * 0.285;
      const maxHoriz = Math.sqrt(Math.max(0.0004, maxArmSpan * maxArmSpan - dy * dy)) * 0.92;
      const dx = ax - effectiveRootX;
      if (Math.abs(dx) > maxHoriz) {
        const pullW =
          curPh?.phase_name === 'ANTICIPATE'
            ? 0.0
            : curPh?.phase_name === 'REACH'
              ? smooth01(root.phaseProgress)
              : 1.0;
        effectiveRootX = lerp(effectiveRootX, ax - Math.sign(dx) * maxHoriz, pullW);
      }
      break;
    }
  }

  const legsIK = solveFootPlantIK({
    rootX: effectiveRootX,
    rootY: root.y,
    groundY,
    heightNorm: h,
    facing,
    accumulatedDistance: root.accumulatedDistance,
    speed: root.speed,
    isRun,
    activePhase: curPh,
    phaseProgress: root.phaseProgress,
    blendedPose: blended,
    trackStartX: Number(track?.world_start?.[0] ?? effectiveRootX),
  });

  const secondary = applySecondaryMotion({
    absoluteT,
    seed: Number(options.seed ?? 1476),
    vx: root.vx,
    vy: root.vy,
    heightNorm: h,
    activePhase: curPh,
    windStrength: Number(worldState?.environment?.wind ?? 0.25),
    cameraScale: options.cameraScale || 'medium',
  });

  const leanRad = clamp(blended.torsoLean, -0.35, 0.35);
  const torsoLen = h * 0.24;
  const neckWorld = [
    legsIK.hipCenter[0] + Math.sin(leanRad) * torsoLen * facing,
    legsIK.hipCenter[1] - Math.cos(leanRad) * torsoLen + secondary.breathOffsetNorm,
  ];
  const shoulderLeft = [neckWorld[0] - facing * h * 0.042, neckWorld[1] + h * 0.025];
  const shoulderRight = [neckWorld[0] + facing * h * 0.042, neckWorld[1] + h * 0.025];
  const headWorld = [
    neckWorld[0] + Math.sin(leanRad + secondary.headLagRad) * h * 0.08 * facing,
    neckWorld[1] - h * 0.11,
  ];

  const walkSwing =
    curPh?.phase_name === 'APPROACH'
      ? Math.sin((root.accumulatedDistance / Math.max(1e-4, h * (isRun ? 0.34 : 0.24))) * Math.PI)
      : 0;

  const handsIK = solveHandPropContact({
    shoulderLeft,
    shoulderRight,
    heightNorm: h,
    facing,
    activePhase: curPh,
    phaseProgress: root.phaseProgress,
    blendedPose: blended,
    contacts: track?.contacts || [],
    absoluteT,
    worldObjects,
    walkSwing,
  });

  // Convert 2D IK arm chains into Squire-compatible shoulder/elbow angles (degrees) as well
  const chainToSquireAngles = (chain, sideSign) => {
    const [S, Ept, Hpt] = chain;
    const a1 = Math.atan2((Ept[0] - S[0]) * sideSign, Ept[1] - S[1]);
    const a2 = Math.atan2((Hpt[0] - Ept[0]) * sideSign, Hpt[1] - Ept[1]);
    return [(a1 * 180) / Math.PI, ((a2 - a1) * 180) / Math.PI];
  };
  const [lsh, lel] = chainToSquireAngles(handsIK.leftArm, -facing);
  const [rsh, rel] = chainToSquireAngles(handsIK.rightArm, facing);

  const exprMap = {
    startled: 'shock',
    strained: 'determined',
    strained_cooperative: 'determined',
    strained_determined: 'determined',
    urgent: 'worried',
    relieved: 'smile',
    hopeful: 'smile',
    alarm: 'scared',
    curious: 'surprised',
    calm: 'calm',
    focused: 'determined',
  };

  return {
    actorId: track?.actor_id || 'actor',
    absoluteT,
    phaseName: curPh?.phase_name || 'IDLE',
    postureState: blended.postureState,
    facing,
    heightNorm: h,
    groundY,
    root: [effectiveRootX, root.y],
    velocity: [root.vx, root.vy],
    speed: root.speed,
    accumulatedDistance: root.accumulatedDistance,
    hipWorld: legsIK.hipCenter,
    neckWorld,
    headWorld,
    torsoLeanRad: leanRad,
    headLook: blended.headLook,
    kneeFlex: blended.kneeFlex,
    faceExpression: exprMap[track?.emotion] || 'neutral',
    leftLegWorld: legsIK.leftLeg,
    rightLegWorld: legsIK.rightLeg,
    leftFootWorld: legsIK.leftFootWorld,
    rightFootWorld: legsIK.rightFootWorld,
    leftPlanted: legsIK.leftPlanted,
    rightPlanted: legsIK.rightPlanted,
    leftArmWorld: handsIK.leftArm,
    rightArmWorld: handsIK.rightArm,
    leftHandWorld: handsIK.leftHandWorld,
    rightHandWorld: handsIK.rightHandWorld,
    activeContactId: handsIK.activeContactId,
    anchorWorld: handsIK.anchorWorld,
    gripDistNorm: handsIK.gripDistNorm,
    squireArmsAng: [lsh, lel, rsh, rel],
    secondary,
    worldObjects,
  };
}

function medianOf(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : 0.5 * (sorted[mid - 1] + sorted[mid]);
}

/**
 * Evaluate an entire `ActorMotionTrack` across frames `[start_sec, end_sec]` at `fps` (default 24)
 * and compute objective natural-motion metrics against Section 5 thresholds:
 * - `median_planted_foot_drift_norm <= 0.03`
 * - `peak_hand_grip_dist_norm <= 0.04` (during CONTACT/EXERT/FOLLOW_THROUGH/SETTLE)
 * - `max_adjacent_joint_jump_norm <= 0.25`
 */
export function validateMotionFrameTrace(track, worldState = {}, options = {}) {
  const fps = Number(options.fps || 24);
  const t0 = Number(track?.start_sec ?? 0);
  const t1 = Number(track?.end_sec ?? 3);
  const totalFrames = Math.max(2, Math.round((t1 - t0) * fps));
  const h = Math.max(0.10, Number(track?.height_norm ?? 0.28));
  const allTracks = options.allTracks || [track];

  const frames = [];
  const plantedFootDrifts = [];
  const contactGripDists = [];
  const jointJumps = [];

  let prevEval = null;
  let leftStanceOrigin = null;
  let rightStanceOrigin = null;

  for (let fi = 0; fi < totalFrames; fi++) {
    const t = Number((t0 + fi / fps).toFixed(6));
    const resolvedObjects = evaluateMultiActorInteraction(allTracks, t, worldState);
    const ev = evaluateMotionTrackAt(track, t, worldState, { ...options, resolvedObjects });

    // Measure stance interval total drift from heel-strike anchor (not merely 1-frame delta!)
    if (ev.leftPlanted) {
      if (!leftStanceOrigin) leftStanceOrigin = [...ev.leftFootWorld];
      plantedFootDrifts.push(
        Math.hypot(ev.leftFootWorld[0] - leftStanceOrigin[0], ev.leftFootWorld[1] - leftStanceOrigin[1]) / h,
      );
    } else {
      leftStanceOrigin = null;
    }

    if (ev.rightPlanted) {
      if (!rightStanceOrigin) rightStanceOrigin = [...ev.rightFootWorld];
      plantedFootDrifts.push(
        Math.hypot(ev.rightFootWorld[0] - rightStanceOrigin[0], ev.rightFootWorld[1] - rightStanceOrigin[1]) / h,
      );
    } else {
      rightStanceOrigin = null;
    }

    if (
      ev.gripDistNorm !== null &&
      ['CONTACT', 'EXERT', 'FOLLOW_THROUGH', 'SETTLE'].includes(ev.phaseName)
    ) {
      contactGripDists.push(ev.gripDistNorm);
    }

    let maxFrameJump = 0;
    if (prevEval) {
      const pairs = [
        [ev.hipWorld, prevEval.hipWorld],
        [ev.headWorld, prevEval.headWorld],
        [ev.leftFootWorld, prevEval.leftFootWorld],
        [ev.rightFootWorld, prevEval.rightFootWorld],
        [ev.leftHandWorld, prevEval.leftHandWorld],
        [ev.rightHandWorld, prevEval.rightHandWorld],
      ];
      for (const [pNow, pPrev] of pairs) {
        const j = Math.hypot(pNow[0] - pPrev[0], pNow[1] - pPrev[1]) / h;
        if (j > maxFrameJump) maxFrameJump = j;
      }
      jointJumps.push(maxFrameJump);
    }

    frames.push({
      frameIndex: fi,
      t,
      phase: ev.phaseName,
      root: ev.root,
      speed: Number(ev.speed.toFixed(5)),
      leftFootWorld: ev.leftFootWorld,
      rightFootWorld: ev.rightFootWorld,
      leftPlanted: ev.leftPlanted,
      rightPlanted: ev.rightPlanted,
      leftHandWorld: ev.leftHandWorld,
      rightHandWorld: ev.rightHandWorld,
      gripDistNorm: ev.gripDistNorm !== null ? Number(ev.gripDistNorm.toFixed(5)) : null,
      maxJointJumpNorm: Number(maxFrameJump.toFixed(5)),
    });
    prevEval = ev;
  }

  const medFootDrift = Number(medianOf(plantedFootDrifts).toFixed(5));
  const peakFootDrift = Number((plantedFootDrifts.length ? Math.max(...plantedFootDrifts) : 0).toFixed(5));
  const peakGripDist = Number((contactGripDists.length ? Math.max(...contactGripDists) : 0).toFixed(5));
  const maxJointJump = Number((jointJumps.length ? Math.max(...jointJumps) : 0).toFixed(5));

  const violations = [];
  if (medFootDrift > 0.03) {
    violations.push(`median_planted_foot_drift_norm=${medFootDrift} > 0.03`);
  }
  if (peakFootDrift > 0.08) {
    violations.push(`peak_planted_foot_drift_norm=${peakFootDrift} > 0.08`);
  }
  if (contactGripDists.length > 0 && peakGripDist > 0.04) {
    violations.push(`peak_hand_grip_dist_norm=${peakGripDist} > 0.04`);
  }
  if (maxJointJump > 0.25) {
    violations.push(`max_adjacent_joint_jump_norm=${maxJointJump} > 0.25`);
  }

  return {
    valid: violations.length === 0,
    actorId: track?.actor_id || 'actor',
    shotId: track?.shot_id || 'S01',
    frameCount: frames.length,
    fps,
    median_planted_foot_drift_norm: medFootDrift,
    peak_planted_foot_drift_norm: peakFootDrift,
    peak_hand_grip_dist_norm: peakGripDist,
    contact_frames_evaluated: contactGripDists.length,
    max_adjacent_joint_jump_norm: maxJointJump,
    violations,
    frames,
  };
}

/**
 * Measure legacy `templates.js` eased-root + constant-speed gait foot drift on the same trajectory
 * so before/after improvement is quantified from exact math rather than appearance guesses.
 */
export function measureLegacySineGaitDrift({
  fromX = 0.26,
  toX = 0.56,
  groundY = 0.84,
  heightNorm = 0.28,
  dur = 2.4,
  fps = 24,
}) {
  const totalFrames = Math.max(2, Math.round(dur * fps));
  const stepS = 0.17 * heightNorm;
  // Legacy constant linear speed v = 2 * STEP * hu * 0.95 (independent of |toX - fromX| and ease.inOut!)
  const vNorm = 2 * stepS * 0.95;
  const plantedDrifts = [];
  let stanceAnchorX = null;
  let wasStance = false;

  for (let fi = 0; fi < totalFrames; fi++) {
    const lt = fi / fps;
    const k = smoother01(clamp(lt / dur, 0, 1));
    const rootX = lerp(fromX, toX, k);
    const travel = vNorm * lt;
    const walkPhase = travel / (2 * stepS);
    const f = ((walkPhase % 1) + 1) % 1;
    if (f < 0.5) {
      const localFx = lerp(stepS / 2, -stepS / 2, f / 0.5);
      const footWorldX = rootX + localFx;
      if (!wasStance) {
        stanceAnchorX = footWorldX;
        wasStance = true;
      }
      plantedDrifts.push(Math.abs(footWorldX - stanceAnchorX) / heightNorm);
    } else {
      wasStance = false;
      stanceAnchorX = null;
    }
  }

  return {
    median_planted_foot_drift_norm: Number(medianOf(plantedDrifts).toFixed(5)),
    peak_planted_foot_drift_norm: Number((plantedDrifts.length ? Math.max(...plantedDrifts) : 0).toFixed(5)),
    sample_count: plantedDrifts.length,
  };
}
