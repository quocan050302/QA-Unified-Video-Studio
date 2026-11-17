// camera.js — Pilot-scoped pure 2D keyframed camera, multi-plane parallax & cut continuity validator for KH-03.0.
// NOTE: Scoped to KH-03.0 pilot; NOT the generalized KH-03.4 Cinematic Camera & Editing Director.
import { E, clamp, blurLayer } from '/engine/core.js';
import { sampleTrack } from './motion.js';

// Evaluate pure 2D camera state at globalT within shotId
export function evaluateRomanCameraAt(shotId, globalT, camBeats = {}) {
  const beat = camBeats[shotId] || camBeats.shots?.[shotId] || {};
  const start = beat.start ?? 0;
  const end = beat.end ?? (start + 3.0);
  const lt = clamp(globalT - start, 0, Math.max(0.001, end - start));
  const W = E.W || 1920;
  const H = E.H || 1080;

  const z = clamp(sampleTrack(lt, beat.zoomKeys, beat.zoom ?? 1.0), 0.75, 2.8);
  const rawCx = sampleTrack(lt, beat.cxKeys, beat.cx ?? 0.5) * W;
  const rawCy = sampleTrack(lt, beat.cyKeys, beat.cy ?? 0.5) * H;
  const rot = sampleTrack(lt, beat.rotKeys, beat.rot ?? 0);

  // Subtle damped impact impulse (e.g. wooden spear glancing off scutum rim)
  let shakeX = 0;
  let shakeY = 0;
  if (beat.impactImpulse) {
    const imp = beat.impactImpulse;
    const dt = lt - (imp.atLocal ?? 0);
    const dur = imp.dur ?? 0.24;
    if (dt >= 0 && dt <= dur) {
      const env = Math.pow(1 - dt / dur, 2);
      const amp = (imp.ampPx ?? 7) * env;
      shakeX = Math.sin(dt * 82) * amp;
      shakeY = Math.cos(dt * 68) * amp * 0.65;
    }
  }

  // Clamp viewport within overscan-safe bounds so world edges never crop into blank space
  const overscanMarginX = (beat.overscanMargin ?? 0.08) * W;
  const overscanMarginY = (beat.overscanMargin ?? 0.08) * H;
  const halfW = W / (2 * Math.max(1.0, z));
  const halfH = H / (2 * Math.max(1.0, z));
  const cx = clamp(rawCx, halfW - overscanMarginX, W - halfW + overscanMarginX);
  const cy = clamp(rawCy, halfH - overscanMarginY, H - halfH + overscanMarginY);

  return Object.freeze({
    shotId,
    globalT,
    localT: lt,
    z,
    cx,
    cy,
    dx: cx - W / 2 + shakeX,
    dy: cy - H / 2 + shakeY,
    rot,
    shakeX,
    shakeY,
    framingScale: beat.framingScale || 'medium',
    purpose: beat.purpose || 'narrative_beat',
    stageAxisSign: beat.stageAxisSign ?? 1,
  });
}

// Render ordered 2D vector planes with distance-weighted parallax & optional depth-of-field blur
export function drawRomanParallaxPlanes(g, cam, planes = []) {
  const W = E.W || 1920;
  const H = E.H || 1080;
  const zBase = cam?.z ?? 1;
  const dxBase = cam?.dx ?? 0;
  const dyBase = cam?.dy ?? 0;
  const rotBase = cam?.rot ?? 0;

  for (const plane of planes) {
    if (!plane || typeof plane.draw !== 'function') continue;
    const depth = plane.depth ?? 1.0;
    const blurPx = plane.blurPx ?? 0;
    const renderPlane = (ctx) => {
      const zz = depth === 0 ? 1.0 : Math.max(0.5, 1 + (zBase - 1) * depth);
      ctx.save();
      ctx.translate(W / 2, H / 2);
      if (rotBase && depth > 0) ctx.rotate(rotBase * Math.min(1, depth));
      ctx.scale(zz, zz);
      ctx.translate(-W / 2 - dxBase * depth, -H / 2 - dyBase * depth);
      plane.draw(ctx);
      ctx.restore();
    };
    if (blurPx > 0.25) {
      blurLayer(g, blurPx, renderPlane);
    } else {
      renderPlane(g);
    }
  }
}

// Validate stage axis, framing variety, and prop/actor continuity across shot boundaries
export function validateRomanCameraCut(shotOut, nextShotIn, stateLedger = {}) {
  const errors = [];
  if (!shotOut || !nextShotIn) {
    return { valid: false, errors: ['Both shotOut and nextShotIn are required'] };
  }

  // 1. 180-degree stage axis rule within same continuous drill line
  if ((shotOut.stageAxisSign ?? 1) !== (nextShotIn.stageAxisSign ?? 1) && !nextShotIn.allowAxisReverse) {
    errors.push(`180-degree stage axis violation between ${shotOut.shotId} and ${nextShotIn.shotId}`);
  }

  // 2. Disallow 3 consecutive shots with identical framingScale + cameraTrajectory
  const history = stateLedger.recentFramings || [];
  if (
    history.length >= 2 &&
    history[history.length - 1]?.framingScale === nextShotIn.framingScale &&
    history[history.length - 2]?.framingScale === nextShotIn.framingScale &&
    history[history.length - 1]?.trajectory === nextShotIn.trajectory &&
    history[history.length - 2]?.trajectory === nextShotIn.trajectory
  ) {
    errors.push(`Repetitive framing/trajectory across >2 consecutive shots ending at ${nextShotIn.shotId}`);
  }

  // 3. World-state prop & shield-gap continuity ledger check
  const outWorld = stateLedger.shots?.[shotOut.shotId]?.endState;
  const inWorld = stateLedger.shots?.[nextShotIn.shotId]?.startState;
  if (outWorld && inWorld) {
    if (outWorld.gapState !== inWorld.gapState && !nextShotIn.motivateGapTransition) {
      errors.push(
        `Shield-wall gap state mutated across cut ${shotOut.shotId}->${nextShotIn.shotId}: ` +
        `${outWorld.gapState} != ${inWorld.gapState}`
      );
    }
    if (outWorld.rookieHelmet !== inWorld.rookieHelmet || outWorld.rookieShield !== inWorld.rookieShield) {
      errors.push(`Hero wardrobe/scutum identity mutated across cut ${shotOut.shotId}->${nextShotIn.shotId}`);
    }
    if (outWorld.snaggedSpear !== inWorld.snaggedSpear && !nextShotIn.motivateSnagTransition) {
      errors.push(`Rookie spear snag state mutated unexpectedly across cut ${shotOut.shotId}->${nextShotIn.shotId}`);
    }
  }

  return {
    valid: errors.length === 0,
    fromShot: shotOut.shotId,
    toShot: nextShotIn.shotId,
    cutType: nextShotIn.cutType || 'motivated_action_cut',
    errors,
  };
}
