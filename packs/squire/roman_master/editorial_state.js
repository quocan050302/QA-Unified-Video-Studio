// editorial_state.js — Deterministic Script-Driven Shot & Causal World State Evaluator for KH-03.0.R1.
// Decouples visual state transitions from narration timing boundaries cleanly with zero mutable globals.
import { clamp, lerp } from '../ink.js';
import { c1Smooth, c2Smooth, sampleTrack } from './motion.js';

export function resolveShotAtFrame(shotPlan, frameIdx) {
  const shots = shotPlan?.shots || [];
  if (!shots.length) return null;
  const fps = shotPlan.fps || 24;
  const f = clamp(Math.floor(frameIdx), 0, Math.max(0, (shotPlan.total_frames || 720) - 1));

  for (let i = 0; i < shots.length; i++) {
    const sh = shots[i];
    if (f >= sh.frame_start && f <= sh.frame_end) {
      const localFrame = f - sh.frame_start;
      const denom = Math.max(1, sh.frame_count - 1);
      const normT = sh.frame_count <= 1 ? 1.0 : clamp(localFrame / denom, 0, 1);
      return {
        shot: sh,
        index: i,
        frameIdx: f,
        fps,
        localFrame,
        localT: localFrame / fps,
        normT,
      };
    }
  }
  const last = shots[shots.length - 1];
  return {
    shot: last,
    index: shots.length - 1,
    frameIdx: f,
    fps,
    localFrame: Math.max(0, f - last.frame_start),
    localT: Math.max(0, (f - last.frame_start) / fps),
    normT: 1.0,
  };
}

// Evaluate causal physical world properties purely from (shotPlan, activeShotInfo, globalT, frameIdx)
export function evaluateWorldStateAt(shotPlan, activeInfo, globalT, frameIdx) {
  const sh = activeInfo?.shot || {};
  const shots = shotPlan?.shots || [];
  const normT = activeInfo?.normT ?? 0;
  const totalDur = shotPlan?.duration_sec || 30.0;

  // Locate causal anchor frame indices dynamically from shot semantics (NOT hardcoded timestamps!)
  const findFirstFrame = (pred, fallback) => {
    const found = shots.find(pred);
    return found ? found.frame_start : fallback;
  };
  const stompFrame = findFirstFrame((s) => s.sub_action === 'sandal_stomps_scroll_at_drain_edge', Math.round(totalDur * 0.56 * 24));
  const sealFrame = findFirstFrame((s) => s.sub_action === 'break_wax_seal_unroll_scroll', Math.round(totalDur * 0.66 * 24));
  const readFrame = findFirstFrame((s) => s.sub_action === 'legible_scroll_text_card_reveal', Math.round(totalDur * 0.76 * 24));
  const slamShot = shots.find((s) => s.sub_action === 'oak_gate_bolt_slams_home_behind_guard');
  const slamStart = slamShot ? slamShot.frame_start : Math.round(totalDur * 0.90 * 24);
  const slamEnd = slamShot ? slamShot.frame_end : Math.min(719, slamStart + 24);

  // Monotonically closing oak city gate from 0.34 (34% closed at sunset) -> 0.91 before slam -> 1.00 locked
  let gateCloseFrac;
  if (frameIdx <= slamStart) {
    const preFrac = clamp(frameIdx / Math.max(1, slamStart), 0, 1);
    gateCloseFrac = lerp(0.34, 0.89, c1Smooth(preFrac));
  } else if (frameIdx <= slamEnd) {
    const slamSpan = clamp((frameIdx - slamStart) / Math.max(1, (slamEnd - slamStart) * 0.68), 0, 1);
    gateCloseFrac = lerp(0.89, 1.0, c2Smooth(slamSpan));
  } else {
    gateCloseFrac = 1.0;
  }

  // Heavy iron locking bolt stays raised until gate is 96% shut, then drops fast inside slam shot
  let boltDropFrac = 0.0;
  if (frameIdx > slamStart) {
    const slamLocal = clamp((frameIdx - slamStart) / Math.max(1, slamEnd - slamStart), 0, 1);
    boltDropFrac = clamp((slamLocal - 0.32) / 0.36, 0, 1);
  }

  // Scroll mode + mud smudge continuity across the entire 30s story
  let scrollMode = 'rolled_sealed';
  if (frameIdx >= readFrame) {
    scrollMode = 'unrolled_message';
  } else if (frameIdx >= sealFrame) {
    const sealShot = shots.find((s) => s.frame_start === sealFrame);
    const localU = sealShot ? clamp((frameIdx - sealFrame) / Math.max(1, sealShot.frame_count - 1), 0, 1) : normT;
    scrollMode = localU > 0.58 ? 'unrolled_message' : 'breaking_seal';
  } else if (frameIdx >= stompFrame) {
    scrollMode = sh.sub_action === 'sandal_stomps_scroll_at_drain_edge' ? 'pinned_under_sandal' : 'rolled_sealed';
  }

  const mudAmount = frameIdx >= stompFrame + 6 ? 0.88 : 0.0;
  const sealCrackFrac = frameIdx >= sealFrame
    ? clamp((frameIdx - sealFrame) / 14, 0, 1)
    : 0.0;

  return Object.freeze({
    globalT,
    frameIdx,
    totalFrames: shotPlan?.total_frames || 720,
    gateCloseFrac: clamp(gateCloseFrac, 0, 1),
    boltDropFrac: clamp(boltDropFrac, 0, 1),
    winchAngleRad: gateCloseFrac * Math.PI * 6.0,
    scrollMode,
    mudAmount,
    sealCrackFrac,
    stageAxisSign: sh.stage_axis_sign ?? 1,
    activeSubAction: sh.sub_action || 'continuous_action',
  });
}

// Compute camera framing parameters strictly from (shot, camBeats, worldState) — smooth, bounded, purposeful
export function evaluateShotCameraAt(shot, camBeats, activeInfo, worldState, W, H) {
  const normT = activeInfo?.normT ?? 0;
  const localT = activeInfo?.localT ?? 0;
  const sCurve = c2Smooth(normT);
  const rawShots = camBeats?.shots;
  const camSpec = Array.isArray(rawShots)
    ? (rawShots.find((b) => b.shot_id === shot?.id) || shot?.camera_intent || {})
    : (rawShots?.[shot?.id] || shot?.camera_intent || {});

  let zoom, targetX, targetY;
  if (Array.isArray(camSpec.zoomKeys) && camSpec.zoomKeys.length) {
    zoom = sampleTrack(localT, camSpec.zoomKeys, 1.0);
    targetX = sampleTrack(localT, camSpec.cxKeys, 0.50);
    targetY = sampleTrack(localT, camSpec.cyKeys, 0.45);
  } else {
    const zoomStart = camSpec.zoom_start ?? 1.0;
    const zoomEnd = camSpec.zoom_end ?? 1.08;
    zoom = lerp(zoomStart, zoomEnd, sCurve);
    const tx0 = camSpec.target_start?.[0] ?? 0.5;
    const ty0 = camSpec.target_start?.[1] ?? 0.45;
    const tx1 = camSpec.target_end?.[0] ?? tx0;
    const ty1 = camSpec.target_end?.[1] ?? ty0;
    targetX = lerp(tx0, tx1, sCurve);
    targetY = lerp(ty0, ty1, sCurve);
  }

  // Brief impact shake ONLY at real mechanical impacts (stumble curb / stomp impact / gate slam)
  let shakeX = 0;
  let shakeY = 0;
  const sub = worldState?.activeSubAction || '';
  if (sub === 'oak_gate_bolt_slams_home_behind_guard' && normT > 0.28 && normT < 0.72) {
    const k = Math.sin(((normT - 0.28) / 0.44) * Math.PI);
    shakeX = Math.sin(localT * 62.0) * W * 0.011 * k;
    shakeY = Math.cos(localT * 49.0) * H * 0.008 * k;
  } else if ((sub === 'sandal_stomps_scroll_at_drain_edge' || sub === 'stumble_trip_impact') && normT > 0.35 && normT < 0.68) {
    const k = Math.sin(((normT - 0.35) / 0.33) * Math.PI);
    shakeX = Math.sin(localT * 54.0) * W * 0.006 * k;
    shakeY = Math.cos(localT * 43.0) * H * 0.005 * k;
  }

  return Object.freeze({
    zoom,
    targetX,
    targetY,
    shakeX,
    shakeY,
    W,
    H,
  });
}

// Helper for canvas camera application centered around targetX/Y cleanly
export function withEditorialCamera(g, cam, drawFn) {
  const cx = cam.W * cam.targetX;
  const cy = cam.H * cam.targetY;
  g.save();
  g.translate(cam.W * 0.5 + cam.shakeX, cam.H * 0.45 + cam.shakeY);
  g.scale(cam.zoom, cam.zoom);
  g.translate(-cx, -cy);
  drawFn();
  g.restore();
}
