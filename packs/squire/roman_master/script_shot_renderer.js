// script_shot_renderer.js — Pure 2D Canvas Dynamic Script-Driven Scene & Action Renderer for KH-03.0.R1.
// Reads E.kh03.{shotPlan, camBeats, ledger} dynamically at render time (never hardcoded shot IDs).
// Defends locked Production Squire Roman 2D identity via romanActorAt() & drawRomanMasterActor2D().
import { E, clamp, lerp, alpha, rect, circ, line } from '../ink.js';
import { PAL, OUT } from '../ink.js';
import { pebble } from '../world.js';
import { blurLayer } from '/engine/core.js';
import { dustPuff } from '../army.js';
import { c1Smooth, c2Smooth } from './motion.js';
import { romanActorAt, drawRomanMasterActor2D } from './character_state.js';
import {
  drawRomanCityApproachDusk2D,
  drawRomanGateWinch2D,
  drawRomanCobbleAlley2D,
  drawRomanGuardThreshold2D,
  drawStoneDrainGrate2D,
  drawSealedRomanScroll2D,
  drawRomanSandalMacro2D,
} from './gate_city_env.js';
import {
  resolveShotAtFrame,
  evaluateWorldStateAt,
  evaluateShotCameraAt,
  withEditorialCamera,
} from './editorial_state.js';

function drawShoutWaves(g, x, y, s, progress) {
  g.save();
  for (let i = 0; i < 3; i++) {
    const u = (progress * 2.2 + i * 0.33) % 1;
    const r = s * (0.28 + u * 0.72);
    g.strokeStyle = alpha('#ffe28a', clamp(1 - u, 0.15, 0.92));
    g.lineWidth = Math.max(2.5, s * 0.045 * (1 - u * 0.5));
    g.beginPath();
    g.arc(x, y, r, -Math.PI * 0.85, -Math.PI * 0.25);
    g.stroke();
  }
  g.restore();
}

function drawMudSplashDroplets(g, x, y, s, k) {
  if (k <= 0.02 || k >= 0.99) return;
  const al = Math.sin(k * Math.PI);
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI * 0.15 - (i / 5) * Math.PI * 0.7;
    const dist = s * (0.14 + k * (0.35 + (i % 2) * 0.18));
    const dx = x + Math.cos(a) * dist;
    const dy = y + Math.sin(a) * dist * 0.8 + k * k * s * 0.18;
    circ(g, dx, dy, s * 0.032 * (1 - k * 0.45), { fill: alpha('#593b27', al * 0.9), lw: Math.max(1.2, s * 0.008) });
  }
}

function feetKeys(cx, cy, hFrac, w, h, lxU, lyU, rxU, ryU) {
  const uPx = (hFrac * h) / 100.0;
  return {
    leftFootXKeys: [[0, cx + (lxU * uPx) / w]],
    leftFootYKeys: [[0, cy + (lyU * uPx) / h]],
    rightFootXKeys: [[0, cx + (rxU * uPx) / w]],
    rightFootYKeys: [[0, cy + (ryU * uPx) / h]],
  };
}

function buildCourierSprintPose(localT, cx, cy, hFrac, w, h, seed = 17, actorExtra = {}) {
  const cyc = localT * 11.5;
  const s = Math.sin(cyc);
  const c = Math.cos(cyc);
  const lx = s * 15 - 4;
  const ly = -Math.max(0, c) * 8;
  const rx = -s * 15 + 4;
  const ry = -Math.max(0, -c) * 8;
  return {
    archetypeId: 'courier_marcus',
    courierSatchel: true,
    hasShield: false,
    weapon: 'none',
    feathers: 2,
    featherColors: [PAL.white, PAL.gold],
    xFrac: cx,
    yFrac: cy,
    hFrac,
    bodyRot: 0.13 + Math.sin(cyc * 2) * 0.025,
    hipBobU: Math.abs(s) * -1.8,
    ...feetKeys(cx, cy, hFrac, w, h, lx, ly, rx, ry),
    leftKneeBend: 0.45,
    rightKneeBend: 0.45,
    leftArmDegKeys: [[0, [-35 - s * 42, -52]]],
    rightArmDegKeys: [[0, [42 + s * 28, 35]]],
    look: 0.72,
    seed,
    ...actorExtra,
  };
}

// Render any single frame dynamically from E.kh03.{shotPlan, camBeats, ledger}
export function renderScriptShotFrame(g, t, shotOverride = null) {
  const w = E.W || 1080;
  const h = E.H || 1920;
  const kh = E.kh03 || {};
  const shotPlan = kh.shotPlan || { fps: 24, total_frames: 720, duration_sec: 30.0, shots: [] };
  const camBeats = kh.camBeats || { shots: {} };
  const fps = shotPlan.fps || 24;
  const frameIdx = clamp(Math.floor(t * fps + 1e-4), 0, Math.max(0, (shotPlan.total_frames || 720) - 1));

  const activeInfo = shotOverride
    ? {
        shot: shotOverride,
        frameIdx,
        fps,
        localFrame: Math.max(0, frameIdx - (shotOverride.frame_start ?? 0)),
        localT: Math.max(0, t - (shotOverride.start ?? 0)),
        normT: clamp((t - (shotOverride.start ?? 0)) / Math.max(0.05, (shotOverride.end ?? t + 1) - (shotOverride.start ?? 0)), 0, 1),
      }
    : resolveShotAtFrame(shotPlan, frameIdx);

  const sh = activeInfo.shot || {};
  const worldState = evaluateWorldStateAt(shotPlan, activeInfo, t, frameIdx);
  const cam = evaluateShotCameraAt(sh, camBeats, activeInfo, worldState, w, h);
  const sub = sh.sub_action || 'courier_sprint_with_satchel';
  const normT = activeInfo.normT;
  const lt = activeInfo.localT;

  g.fillStyle = '#2d262b';
  g.fillRect(0, 0, w, h);

  withEditorialCamera(g, cam, () => {
    const actorEvalCtx = { W: w, H: h, globalT: t };

    if (sub === 'moving_scroll_toward_closing_oak_gap') {
      drawRomanCityApproachDusk2D(g, worldState, { horizonYFrac: 0.46, groundYFrac: 0.56, archWFrac: 0.62, archHFrac: 0.36 });
      const cx = lerp(0.18, 0.54, c1Smooth(normT));
      const stridePose = buildCourierSprintPose(lt, cx, 0.61, 0.31, w, h, 11, {
        face: 'determined',
        rightArmDegKeys: [[0, [75, -18]]],
      });
      const marcus = romanActorAt(t, { start: sh.start, end: sh.end, actors: { courier_marcus: stridePose } }, 'courier_marcus', actorEvalCtx);
      drawRomanMasterActor2D(g, marcus, { seed: 11, courierSatchel: true, shoeMode: 'side' });
      const hx = marcus.rootWorld[0] + w * 0.085;
      const hy = marcus.rootWorld[1] - marcus.actorH * 0.42;
      drawSealedRomanScroll2D(g, hx, hy, w * 0.145, { mode: 'rolled_sealed', rot: -0.26, airborneStreak: true });
      dustPuff(g, marcus.rootWorld[0] - w * 0.06, marcus.rootWorld[1], w * 0.08, (lt * 2.5) % 1);
    } else if (sub === 'winch_drum_turns_and_doors_converge' || sub === 'closing_oak_gap_tension_cut') {
      drawRomanGateWinch2D(g, worldState);
      const strain = Math.sin(lt * 5.2);
      const wx = 0.78;
      const wy = 0.56;
      const wh = sub === 'closing_oak_gap_tension_cut' ? 0.24 : 0.29;
      const watchPose = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            watchman_sec: {
              archetypeId: 'watchman_sec',
              hasShield: false,
              flip: true,
              xFrac: wx,
              yFrac: wy,
              hFrac: wh,
              bodyRot: -0.06 + strain * 0.06,
              ...feetKeys(wx, wy, wh, w, h, -7, 0, 9, 0),
              leftArmDegKeys: [[0, [45 + strain * 18, -42]]],
              rightArmDegKeys: [[0, [-38 + strain * 16, 48]]],
              face: 'focused',
              weapon: 'none',
            },
          },
        },
        'watchman_sec',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, watchPose, { seed: 23, feathers: 3, featherColors: [PAL.white, PAL.red, PAL.white], shoeMode: 'front' });
    } else if (sub === 'courier_sprint_with_satchel') {
      drawRomanCityApproachDusk2D(g, worldState, { horizonYFrac: 0.47, groundYFrac: 0.58, scrollPx: lt * w * 0.95 });
      const cx = lerp(0.28, 0.64, c1Smooth(normT));
      const p = buildCourierSprintPose(lt, cx, 0.59, 0.32, w, h, 31, { face: 'determined' });
      const marcus = romanActorAt(t, { start: sh.start, end: sh.end, actors: { courier_marcus: p } }, 'courier_marcus', actorEvalCtx);
      drawRomanMasterActor2D(g, marcus, { seed: 31, courierSatchel: true, shoeMode: 'side' });
      drawSealedRomanScroll2D(
        g,
        marcus.rootWorld[0] + w * 0.068,
        marcus.rootWorld[1] - marcus.actorH * 0.39 + Math.sin(lt * 11.5) * 4,
        w * 0.115,
        { mode: 'rolled_sealed', rot: 0.18 }
      );
      dustPuff(g, marcus.rootWorld[0] - w * 0.055, marcus.rootWorld[1], w * 0.075, (lt * 2.2) % 1);
    } else if (sub === 'sandals_hammer_damp_cobbles') {
      drawRomanCobbleAlley2D(g, worldState, { scrollX: lt * w * 1.15, floorYFrac: 0.52 });
      const cx = lerp(0.26, 0.54, normT);
      const runP = buildCourierSprintPose(lt, cx, 0.56, 0.30, w, h, 41, { face: 'focused' });
      const marcus = romanActorAt(t, { start: sh.start, end: sh.end, actors: { courier_marcus: runP } }, 'courier_marcus', actorEvalCtx);
      drawRomanMasterActor2D(g, marcus, { seed: 41, courierSatchel: true, shoeMode: 'side' });
      const lLift = Math.max(0, Math.sin(lt * 13.0)) * h * 0.048;
      const rLift = Math.max(0, Math.sin(lt * 13.0 + Math.PI)) * h * 0.048;
      drawRomanSandalMacro2D(g, w * 0.36, h * 0.555 - lLift, w * 0.25, { rot: lLift > 5 ? -0.18 : 0.03 });
      drawRomanSandalMacro2D(g, w * 0.65, h * 0.56 - rLift, w * 0.25, { rot: rLift > 5 ? -0.18 : 0.03 });
      dustPuff(g, w * 0.42, h * 0.57, w * 0.08, (lt * 3.1) % 1);
    } else if (sub === 'stumble_trip_impact') {
      const curbFrac = 0.53;
      drawRomanCobbleAlley2D(g, worldState, { scrollX: normT * w * 0.22, floorYFrac: 0.55, curbXFrac: curbFrac });
      const tripK = clamp((normT - 0.18) / 0.55, 0, 1);
      const mX = lerp(0.24, 0.50, c1Smooth(clamp(normT * 1.15, 0, 1)));
      const bodyPitch = lerp(0.11, 0.56, c1Smooth(tripK));
      const mY = 0.59 + Math.sin(tripK * Math.PI) * 0.014;
      const tripPose = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            courier_marcus: {
              archetypeId: 'courier_marcus',
              courierSatchel: true,
              hasShield: false,
              weapon: 'none',
              xFrac: mX,
              yFrac: mY,
              hFrac: 0.31,
              bodyRot: bodyPitch,
              ...feetKeys(mX, mY, 0.31, w, h, lerp(-11, 7, tripK), -1, lerp(13, -15, tripK), lerp(0, -10, tripK)),
              leftArmDegKeys: [[0, [-52 - tripK * 38, -22]]],
              rightArmDegKeys: [[0, [65 + tripK * 45, 25]]],
              face: tripK > 0.15 ? 'shock' : 'worried',
              look: 0.85,
            },
          },
        },
        'courier_marcus',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, tripPose, { seed: 53, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold], shoeMode: 'side' });
      const launchU = clamp((normT - 0.34) / 0.66, 0, 1);
      const sx = launchU > 0 ? lerp(mX * w + w * 0.10, w * 0.86, launchU) : tripPose.rootWorld[0] + w * 0.09;
      const sy = launchU > 0 ? lerp(h * 0.44, h * 0.24, c1Smooth(launchU)) : (tripPose.rootWorld[1] - tripPose.actorH * 0.42);
      drawSealedRomanScroll2D(g, sx, sy, w * 0.135, { mode: 'rolled_sealed', rot: lerp(-0.2, 2.4, launchU), airborneStreak: launchU > 0.05 });
    } else if (sub === 'airborne_scroll_arc') {
      drawRomanCobbleAlley2D(g, worldState, { scrollX: w * 0.6 + normT * w * 0.45, floorYFrac: 0.56 });
      const bgMarcus = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            courier_marcus: {
              archetypeId: 'courier_marcus',
              courierSatchel: true,
              hasShield: false,
              weapon: 'none',
              xFrac: 0.22,
              yFrac: 0.59,
              hFrac: 0.21,
              bodyRot: 0.62,
              ...feetKeys(0.22, 0.59, 0.21, w, h, -12, -3, -18, -8),
              leftArmDegKeys: [[0, [68, 22]]],
              rightArmDegKeys: [[0, [82, 18]]],
              face: 'shock',
              look: 0.9,
            },
          },
        },
        'courier_marcus',
        actorEvalCtx
      );
      blurLayer(g, 4, (c) => {
        drawRomanMasterActor2D(c, bgMarcus, { seed: 61, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold] });
      });
      const arcX = lerp(0.18, 0.88, c1Smooth(normT)) * w;
      const arcY = (0.43 - 0.19 * Math.sin(Math.PI * normT)) * h;
      drawSealedRomanScroll2D(g, arcX, arcY, w * 0.21, {
        mode: 'rolled_sealed',
        rot: normT * Math.PI * 2.8,
        airborneStreak: true,
      });
    } else if (sub === 'guard_lunges_and_scroll_slips_past_gloves') {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.58, drainXFrac: 0.80, drainYFrac: 0.64 });
      const diveK = c1Smooth(normT);
      const gx = lerp(0.28, 0.45, diveK);
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              hasShield: false,
              weapon: 'none',
              xFrac: gx,
              yFrac: 0.59,
              hFrac: 0.30,
              bodyRot: lerp(0.05, 0.44, diveK),
              ...feetKeys(gx, 0.59, 0.30, w, h, -14, 0, 12, 0),
              leftArmDegKeys: [[0, [76, 12]]],
              rightArmDegKeys: [[0, [88, 10]]],
              face: 'shock',
              look: 0.9,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, gaius, { seed: 71, mustache: 'big', shoeMode: 'side' });
      const sx = lerp(0.22, 0.80, normT) * w;
      const sy = lerp(0.32, 0.54, normT) * h;
      drawSealedRomanScroll2D(g, sx, sy, w * 0.15, { mode: 'rolled_sealed', rot: normT * 5.2 + 0.4, airborneStreak: true });
    } else if (sub === 'sandal_stomps_scroll_at_drain_edge') {
      // Richly jointed Roman travertine flagstones around storm drain cavity
      const flGrad = g.createLinearGradient(0, 0, 0, h);
      flGrad.addColorStop(0, '#9e886e');
      flGrad.addColorStop(1, '#79644d');
      g.fillStyle = flGrad;
      g.fillRect(-20, -20, w + 40, h + 40);
      for (let r = 1; r <= 7; r++) {
        const y = (r / 7.5) * h;
        line(g, [[-20, y], [w + 20, y]], { lw: 2.2, ink: alpha(OUT, 0.34) });
        const xOff = (r % 2) * w * 0.24 + w * 0.18;
        line(g, [[xOff, y - h / 7.5], [xOff, y]], { lw: 2.0, ink: alpha(OUT, 0.28) });
        line(g, [[xOff + w * 0.45, y - h / 7.5], [xOff + w * 0.45, y]], { lw: 2.0, ink: alpha(OUT, 0.28) });
      }
      pebble(g, w * 0.16, h * 0.56, w * 0.03, 5);
      pebble(g, w * 0.26, h * 0.34, w * 0.025, 9);
      drawStoneDrainGrate2D(g, w * 0.74, h * 0.455, w * 0.34, h * 0.13);
      const slideK = clamp(normT / 0.42, 0, 1);
      const sx = lerp(0.14, 0.43, c1Smooth(slideK)) * w;
      const sy = h * 0.465;
      const pinK = clamp((normT - 0.38) / 0.24, 0, 1);
      const squashY = pinK > 0.7 ? 0.85 : 1.0;
      g.save();
      g.translate(sx, sy);
      g.scale(1.0, squashY);
      drawSealedRomanScroll2D(g, 0, 0, w * 0.23, {
        mode: pinK > 0.6 ? 'pinned_under_sandal' : 'rolled_sealed',
        rot: lerp(-0.35, -0.05, slideK),
        mudAmount: pinK > 0.5 ? 0.85 : 0.1,
      });
      g.restore();

      const stompY = pinK < 1.0
        ? lerp(0.14, 0.435, c2Smooth(clamp((normT - 0.22) / 0.35, 0, 1))) * h
        : (0.435 - Math.sin(clamp((normT - 0.62) / 0.38, 0, 1) * Math.PI) * 0.008) * h;
      drawRomanSandalMacro2D(g, sx - w * 0.015, stompY, w * 0.35, {
        rot: lerp(-0.14, 0.02, pinK),
        tallShin: true,
        showTunicHem: true,
      });
      drawMudSplashDroplets(g, sx + w * 0.04, h * 0.47, w * 0.24, clamp((normT - 0.54) / 0.45, 0, 1));
    } else if (sub === 'guard_relieved_exhale_retrieving_scroll') {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.58, drainXFrac: 0.74, drainYFrac: 0.63 });
      const exhaleK = Math.sin(normT * Math.PI);
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              hasShield: false,
              weapon: 'none',
              xFrac: 0.48,
              yFrac: 0.59,
              hFrac: 0.31,
              bodyRot: lerp(0.24, 0.04, c1Smooth(normT)),
              hipBobU: exhaleK * 1.4,
              ...feetKeys(0.48, 0.59, 0.31, w, h, -8, 0, 8, 0),
              leftArmDegKeys: [[0, [-20, -25]]],
              rightArmDegKeys: [[0, [lerp(58, 35, normT), -48]]],
              face: 'exhale',
              look: 0.35,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, gaius, { seed: 83, mustache: 'big', shoeMode: 'front' });
      drawSealedRomanScroll2D(
        g,
        gaius.rootWorld[0] + w * 0.11,
        lerp(h * 0.53, gaius.rootWorld[1] - gaius.actorH * 0.44, c1Smooth(normT)),
        w * 0.14,
        { mode: 'rolled_sealed', mudAmount: 0.88, rot: -0.22 }
      );
    } else if (sub === 'break_wax_seal_unroll_scroll') {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.60, showDrain: false });
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              hasShield: false,
              weapon: 'none',
              xFrac: 0.44,
              yFrac: 0.62,
              hFrac: 0.35,
              bodyRot: 0.04,
              ...feetKeys(0.44, 0.62, 0.35, w, h, -8, 0, 8, 0),
              leftArmDegKeys: [[0, [32, 46]]],
              rightArmDegKeys: [[0, [36, -42]]],
              face: normT > 0.6 ? 'shock' : 'neutral',
              look: 0.25,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, gaius, { seed: 91, mustache: 'big' });
      const unfurl = clamp((normT - 0.52) / 0.48, 0, 1);
      drawSealedRomanScroll2D(g, w * 0.54, h * 0.43, w * lerp(0.22, 0.34, unfurl), {
        mode: unfurl > 0.35 ? 'unrolled_message' : 'breaking_seal',
        sealCrackFrac: clamp(normT * 1.4, 0, 1),
        mudAmount: 0.88,
        rot: lerp(-0.08, 0.02, unfurl),
      });
    } else if (sub === 'legible_scroll_text_card_reveal') {
      blurLayer(g, 8, (c) => {
        drawRomanGuardThreshold2D(c, worldState, { floorYFrac: 0.60, showDrain: false });
        const tinyGaius = romanActorAt(
          t,
          {
            start: sh.start,
            end: sh.end,
            actors: {
              gate_guard_gaius: {
                archetypeId: 'gate_guard_gaius',
                hasShield: false,
                weapon: 'none',
                xFrac: 0.24,
                yFrac: 0.60,
                hFrac: 0.30,
                ...feetKeys(0.24, 0.60, 0.30, w, h, -7, 0, 7, 0),
                leftArmDegKeys: [[0, [15, -20]]],
                rightArmDegKeys: [[0, [25, -35]]],
                face: 'shock',
                look: 0.6,
              },
            },
          },
          'gate_guard_gaius',
          actorEvalCtx
        );
        drawRomanMasterActor2D(c, tinyGaius, { seed: 101, mustache: 'big' });
      });
      const introU = clamp(normT / 0.45, 0, 1);
      const cardScale = w * lerp(0.39, 0.435, c2Smooth(introU));
      drawSealedRomanScroll2D(g, w * 0.50, h * 0.37, cardScale, {
        mode: 'unrolled_message',
        mudAmount: 0.88,
        rot: lerp(-0.04, 0.0, c2Smooth(introU)),
        lines: ['KEEP', 'THE GATE', 'OPEN'],
      });
    } else if (sub === 'guard_shouts_up_to_winch_tower') {
      drawRomanGateWinch2D(g, worldState);
      const waveK = lt * 3.0;
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              flip: true,
              hasShield: false,
              weapon: 'none',
              xFrac: 0.36,
              yFrac: 0.59,
              hFrac: 0.31,
              headNodKeys: [[0, -3]],
              headRot: -0.22,
              ...feetKeys(0.36, 0.59, 0.31, w, h, -8, 0, 8, 0),
              leftArmDegKeys: [[0, [-82, -55]]],
              rightArmDegKeys: [[0, [118, -18]]],
              face: 'shout',
              look: -0.7,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, gaius, { seed: 113, mustache: 'big' });
      drawSealedRomanScroll2D(g, gaius.rootWorld[0] + w * 0.14, h * 0.33, w * 0.13, {
        mode: 'unrolled_message',
        mudAmount: 0.88,
        rot: 0.18 + Math.sin(lt * 14) * 0.08,
      });
      drawShoutWaves(g, gaius.headWorld[0] - w * 0.06, gaius.headWorld[1] - h * 0.025, w * 0.16, waveK);
    } else if (sub === 'oak_gate_bolt_slams_home_behind_guard') {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.59, showDrain: true, drainXFrac: 0.82, drainYFrac: 0.65 });
      const recoil = normT > 0.35 && normT < 0.72 ? Math.sin(((normT - 0.35) / 0.37) * Math.PI) : 0;
      const my = 0.60 - recoil * 0.015;
      const gy = 0.60 - recoil * 0.022;
      const marcus = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            courier_marcus: {
              archetypeId: 'courier_marcus',
              courierSatchel: true,
              hasShield: false,
              weapon: 'none',
              xFrac: 0.25,
              yFrac: my,
              hFrac: 0.29,
              bodyRot: 0.14 - recoil * 0.08,
              ...feetKeys(0.25, my, 0.29, w, h, -8, 0, 8, 0),
              leftArmDegKeys: [[0, [-35, -40]]],
              rightArmDegKeys: [[0, [48, 28]]],
              face: 'tired',
              look: 0.4,
            },
          },
        },
        'courier_marcus',
        actorEvalCtx
      );
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              hasShield: false,
              weapon: 'none',
              xFrac: 0.62,
              yFrac: gy,
              hFrac: 0.31,
              ...feetKeys(0.62, gy, 0.31, w, h, -9, 0, 9, 0),
              leftArmDegKeys: [[0, [-55, -25]]],
              rightArmDegKeys: [[0, [68, -22]]],
              face: 'shock',
              look: -0.35,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, marcus, { seed: 121, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold] });
      drawRomanMasterActor2D(g, gaius, { seed: 122, mustache: 'big' });
      drawSealedRomanScroll2D(g, gaius.rootWorld[0] + w * 0.13, gaius.rootWorld[1] - gaius.actorH * 0.43, w * 0.125, {
        mode: 'unrolled_message',
        mudAmount: 0.88,
        rot: -0.15 + recoil * 0.12,
      });
    } else {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.61, showDrain: false });
      const blinkNow = (normT > 0.34 && normT < 0.46) || (normT > 0.64 && normT < 0.74);
      const settleK = clamp(normT / 0.55, 0, 1);
      const gaius = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            gate_guard_gaius: {
              archetypeId: 'gate_guard_gaius',
              hasShield: false,
              weapon: 'none',
              xFrac: 0.46,
              yFrac: 0.62,
              hFrac: 0.33,
              headNodKeys: [[0, lerp(-1.5, 1.5, settleK)]],
              ...feetKeys(0.46, 0.62, 0.33, w, h, -8, 0, 8, 0),
              leftArmDegKeys: [[0, [-18, -32]]],
              rightArmDegKeys: [[0, [22, -45]]],
              face: 'awkward',
              blinkKeys: [[0, blinkNow]],
              look: 0.0,
            },
          },
        },
        'gate_guard_gaius',
        actorEvalCtx
      );
      const marcus = romanActorAt(
        t,
        {
          start: sh.start,
          end: sh.end,
          actors: {
            courier_marcus: {
              archetypeId: 'courier_marcus',
              courierSatchel: true,
              hasShield: false,
              weapon: 'none',
              xFrac: 0.22,
              yFrac: 0.62,
              hFrac: 0.29,
              bodyRot: 0.09,
              ...feetKeys(0.22, 0.62, 0.29, w, h, -7, 0, 7, 0),
              leftArmDegKeys: [[0, [-18, -22]]],
              rightArmDegKeys: [[0, [16, 20]]],
              face: 'tired',
              look: 0.5,
            },
          },
        },
        'courier_marcus',
        actorEvalCtx
      );
      drawRomanMasterActor2D(g, marcus, { seed: 131, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold] });
      drawRomanMasterActor2D(g, gaius, { seed: 132, mustache: 'big' });
      drawSealedRomanScroll2D(g, gaius.rootWorld[0] + w * 0.14, gaius.rootWorld[1] - gaius.actorH * 0.36, w * 0.175, {
        mode: 'unrolled_message',
        mudAmount: 0.88,
        rot: 0.04,
        lines: ['KEEP', 'THE GATE', 'OPEN'],
      });
    }
  });
}
