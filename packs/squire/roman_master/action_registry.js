// action_registry.js — Strict Fail-Closed 2D Canvas Runtime Registry for KH-03.0.R2.
// Every finite renderer_action_id declared in tools/kh03_action_registry.py MUST have an explicit
// 2D Squire Canvas handler here. Unsupported / unmapped actions throw immediately so frame renders fail closed.
import { clamp, lerp, alpha, rect, circ, ellipse, line, shape } from '../ink.js';
import { OUT, PAL } from '../ink.js';
import { dustPuff } from '../army.js';
import { c1Smooth, c2Smooth } from './motion.js';
import { romanActorAt, drawRomanMasterActor2D } from './character_state.js';
import {
  drawRomanLoaf2D,
  drawBrakePeg2D,
  drawRomanCart2D,
  drawStoneBollard2D,
  drawRopePath2D,
  drawBakeryOvenAndTray2D,
} from './market_props.js';
import {
  drawRomanMarketSlopeBackdrop2D,
  drawMarketCrowdGroup2D,
  drawMarketForegroundPass2D,
} from './market_env.js';
import {
  drawRomanRiverHarbor2D,
  drawClothVexillum2D,
  drawRomanForumCourtyard2D,
  drawStoneSenatorBench2D,
  drawCeremonialHelmetProp2D,
} from './holdout_envs.js';
import {
  drawRomanCityApproachDusk2D,
  drawRomanGuardThreshold2D,
  drawSealedRomanScroll2D,
} from './gate_city_env.js';

export const RENDERER_REGISTRY_VERSION = 'kh03.r2.action_registry.v1';

// Exact 1:1 mirror of tools/kh03_action_registry.py action_id -> renderer_action_id map (29 finite capabilities)
export const ACTION_ID_TO_RENDERER_ID = Object.freeze({
  'actor.idle_micro_act': 'actor_idle_micro_act',
  'actor.walk_stride': 'actor_walk_stride',
  'actor.deadpan_walk_unaffected': 'actor_deadpan_walk_unaffected',
  'actor.sprint_chase': 'actor_sprint_chase',
  'actor.reach_grab_prop': 'actor_reach_grab_prop',
  'actor.stop_brace': 'actor_stop_brace',
  'actor.release_throw_prop': 'actor_release_throw_prop',
  'actor.point_shout_look': 'actor_point_shout_look',
  'actor.pickup_prop': 'actor_pickup_prop',
  'actor.pull_drag_rope_tension': 'actor_pull_drag_rope_tension',
  'actor.push_hold_load': 'actor_push_hold_load',
  'actor.handoff_prop': 'actor_handoff_prop',
  'actor.stumble_recover': 'actor_stumble_recover',
  'actor.crowd_reaction_cheer': 'actor_crowd_reaction_cheer',
  'prop.peg_crack_snap': 'prop_peg_crack_snap',
  'prop.cart_roll_slope': 'prop_cart_roll_slope',
  'prop.rope_taut_post_wrap': 'prop_rope_taut_post_wrap',
  'prop.cart_halt_skid': 'prop_cart_halt_skid',
  'prop.prop_bounce_tray': 'prop_bounce_tray',
  'prop.prop_parabolic_arc': 'prop_parabolic_arc',
  'prop.helmet_impact_settle': 'prop_helmet_impact_settle',
  'prop.vexillum_river_drift': 'prop_vexillum_river_drift',
  'prop.helmet_roll_under_bench': 'prop_helmet_roll_under_bench',
  'prop.scroll_open_adapter': 'prop_scroll_open_adapter',
  'prop.door_close_adapter': 'prop_door_close_adapter',
  'world.market_hill_establish': 'world_market_hill_establish',
  'world.market_crowd_pass': 'world_market_crowd_pass',
  'world.river_harbor_establish': 'world_river_harbor_establish',
  'world.forum_courtyard_establish': 'world_forum_courtyard_establish',
});

// Shared grounded foot keyframe generator (prevents foot sliding across 2D shots)
function v2FeetKeys(cx, cy, hFrac, w, h, lxU, lyU, rxU, ryU) {
  const uPx = (hFrac * h) / 100.0;
  return {
    leftFootXKeys: [[0, cx + (lxU * uPx) / w]],
    leftFootYKeys: [[0, cy + (lyU * uPx) / h]],
    rightFootXKeys: [[0, cx + (rxU * uPx) / w]],
    rightFootYKeys: [[0, cy + (ryU * uPx) / h]],
  };
}

// Civilian / military Squire styling overrides preserving round ivory face + #392a21 outlines
const ACTOR_VISUAL_PROFILES = Object.freeze({
  apprentice_titus: {
    helmet: null,
    hair: 'short',
    hairColor: '#593b25',
    feathers: 0,
    body: 'apron',
    tunicColor: '#4c738f',
    courierSatchel: false,
    hasShield: false,
    weapon: 'none',
    seed: 21,
  },
  baker_lucius: {
    helmet: null,
    hair: 'curly',
    hairColor: '#8d6c53',
    mustache: 'big',
    feathers: 0,
    body: 'apron',
    tunicColor: '#f3ead8',
    hasShield: false,
    weapon: 'none',
    seed: 22,
  },
  centurion_varro: {
    helmet: 'montefortino',
    crest: PAL.red,
    feathers: 0,
    mail: true,
    body: 'roman',
    tunicColor: PAL.red,
    hasShield: false,
    weapon: 'none',
    seed: 23,
  },
  centurion_crest: {
    helmet: 'montefortino',
    crest: PAL.red,
    feathers: 0,
    mail: true,
    body: 'roman',
    tunicColor: PAL.red,
    hasShield: false,
    weapon: 'none',
    seed: 24,
  },
  signifer_marc: {
    helmet: 'montefortino',
    feathers: 3,
    featherColors: [PAL.white, PAL.red, PAL.white],
    body: 'roman',
    tunicColor: PAL.red,
    hasShield: false,
    weapon: 'none',
    seed: 25,
  },
  senator_cassius: {
    helmet: null,
    hair: 'short',
    hairColor: '#9c9288',
    beard: 'full',
    feathers: 0,
    body: 'toga',
    tunicColor: '#f6efe2',
    sash: PAL.crimson,
    hasShield: false,
    weapon: 'none',
    seed: 26,
  },
  forum_messenger: {
    helmet: null,
    hair: 'short',
    hairColor: '#4a3222',
    feathers: 0,
    body: 'tunic',
    tunicColor: '#c77a3f',
    courierSatchel: true,
    hasShield: false,
    weapon: 'none',
    seed: 27,
  },
  courier_marcus: {
    helmet: 'montefortino',
    feathers: 2,
    featherColors: [PAL.white, PAL.gold],
    body: 'roman',
    tunicColor: PAL.red,
    courierSatchel: true,
    hasShield: false,
    weapon: 'none',
    seed: 28,
  },
});

function profileForActor(actorId) {
  return ACTOR_VISUAL_PROFILES[actorId] || ACTOR_VISUAL_PROFILES.apprentice_titus;
}

function drawV2Actor(g, t, shot, actorId, spec, W, H, opts = {}) {
  const prof = profileForActor(actorId);
  const fullSpec = {
    archetypeId: actorId,
    hasShield: prof.hasShield ?? false,
    weapon: opts.weapon ?? prof.weapon ?? 'none',
    feathers: opts.feathers ?? prof.feathers ?? 0,
    featherColors: prof.featherColors,
    courierSatchel: !!(opts.courierSatchel ?? prof.courierSatchel),
    ...spec,
  };
  const pose = romanActorAt(
    t,
    { start: shot.start ?? 0, end: shot.end ?? (t + 1), actors: { [actorId]: fullSpec } },
    actorId,
    { W, H, globalT: t }
  );
  drawRomanMasterActor2D(g, pose, {
    ...prof,
    ...opts,
    pose: undefined,
  });
  return pose;
}

function drawShoutMotionArcs(g, x, y, s, k) {
  g.save();
  for (let i = 0; i < 3; i++) {
    const u = ((k * 2.4 + i * 0.32) % 1 + 1) % 1;
    g.strokeStyle = alpha('#ffe088', clamp(1 - u, 0.2, 0.92));
    g.lineWidth = Math.max(2.2, s * 0.045 * (1 - u * 0.4));
    g.beginPath();
    g.arc(x, y, s * (0.25 + u * 0.7), -Math.PI * 0.85, -Math.PI * 0.2);
    g.stroke();
  }
  g.restore();
}

// Compute Centurion helmet plume top coordinate (world space) so a falling/settled loaf lands flush
function helmetTopWorld(pose) {
  const offset = pose.actorH * 1.11;
  const r = pose.bodyRot || 0;
  return [pose.rootWorld[0] + Math.sin(r) * offset, pose.rootWorld[1] - Math.cos(r) * offset];
}

function resolveLocation(shot, worldState) {
  return shot?.location_id || worldState?.locationId || 'roman_market_hill';
}

function primaryActorId(shot, fallback = 'apprentice_titus') {
  const list = shot?.actor_ids;
  if (Array.isArray(list) && list.length > 0 && list[0] !== 'market_crowd') return list[0];
  return fallback;
}

function drawEnvironmentForLocation(g, locId, worldState, opts = {}) {
  const scrollX = opts.scrollX ?? (worldState?.streetScrollPx || 0);
  if (locId === 'roman_river_harbor') {
    drawRomanRiverHarbor2D(g, worldState, opts);
    return 'harbor';
  }
  if (locId === 'roman_forum_courtyard') {
    drawRomanForumCourtyard2D(g, worldState, opts);
    return 'forum';
  }
  if (locId === 'city_gate_approach' || locId === 'city_gate_threshold') {
    if (locId === 'city_gate_threshold') {
      drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.59, showDrain: false });
    } else {
      drawRomanCityApproachDusk2D(g, worldState, { horizonYFrac: 0.46, groundYFrac: 0.56 });
    }
    return 'gate';
  }
  drawRomanMarketSlopeBackdrop2D(g, worldState, {
    scrollX,
    slopeDropFrac: opts.slopeDropFrac ?? 0.08,
  });
  return 'market';
}

function computeRunCyclePose(lt, cx, cy, hFrac, W, H, freq = 10.5, lean = 0.14, strideU = 13.0) {
  const cyc = lt * freq;
  const s = Math.sin(cyc);
  const c = Math.cos(cyc);
  return {
    xFrac: cx,
    yFrac: cy,
    hFrac,
    bodyRot: lean + Math.sin(cyc * 2) * 0.025,
    hipBobU: -Math.abs(s) * 1.9,
    ...v2FeetKeys(cx, cy, hFrac, W, H, s * strideU - 3, -Math.max(0, c) * 7.5, -s * strideU + 3, -Math.max(0, -c) * 7.5),
    leftKneeBend: 0.42,
    rightKneeBend: 0.42,
    leftArmDegKeys: [[0, [-38 - s * 40, -48]]],
    rightArmDegKeys: [[0, [36 + s * 34, 32]]],
  };
}

function computeWalkCyclePose(lt, cx, cy, hFrac, W, H, freq = 6.2, strideU = 8.5) {
  const cyc = lt * freq;
  const s = Math.sin(cyc);
  const c = Math.cos(cyc);
  return {
    xFrac: cx,
    yFrac: cy,
    hFrac,
    bodyRot: 0.025 + Math.sin(cyc * 2) * 0.012,
    hipBobU: -Math.abs(s) * 0.95,
    ...v2FeetKeys(cx, cy, hFrac, W, H, s * strideU - 2, -Math.max(0, c) * 4.2, -s * strideU + 2, -Math.max(0, -c) * 4.2),
    leftKneeBend: 0.25,
    rightKneeBend: 0.25,
    leftArmDegKeys: [[0, [-14 - s * 22, -20]]],
    rightArmDegKeys: [[0, [14 + s * 22, 18]]],
  };
}

// ======================================================================================
// 29 VERIFIED FINITE CAPABILITY HANDLERS (ZERO DEFAULT GUARD FALLBACK)
// ======================================================================================
export const ROMAN_ACTION_RENDERERS = Object.freeze({
  actor_idle_micro_act(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    const kind = drawEnvironmentForLocation(g, loc, worldState);
    const actorId = primaryActorId(shot, kind === 'harbor' ? 'signifer_marc' : kind === 'forum' ? 'senator_cassius' : 'baker_lucius');
    if (kind === 'market') {
      drawBakeryOvenAndTray2D(g, W * 0.78, H * 0.56, W * 0.34, { t, loavesOnTray: worldState.loavesOnTray ?? 3 });
      drawMarketCrowdGroup2D(g, worldState, { mood: 'hush' });
    } else if (kind === 'forum') {
      drawStoneSenatorBench2D(g, W * 0.62, H * 0.58, W * 0.34, H * 0.065);
    }
    const blink = (normT > 0.32 && normT < 0.44) || (normT > 0.68 && normT < 0.79);
    drawV2Actor(g, t, shot, actorId, {
      xFrac: 0.44,
      yFrac: 0.58,
      hFrac: 0.30,
      headNodKeys: [[0, Math.sin(lt * 2.5) * 1.6]],
      ...v2FeetKeys(0.44, 0.58, 0.30, W, H, -7, 0, 7, 0),
      leftArmDegKeys: [[0, [-18, -28]]],
      rightArmDegKeys: [[0, [20, -34]]],
      face: worldState.loafOnHelmet ? 'awkward' : 'focused',
      blinkKeys: [[0, blink]],
      look: Math.sin(lt * 1.4) * 0.45,
    }, W, H, { shoeMode: 'front' });
  },

  actor_walk_stride(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    const dir = shot.stage_axis_sign ?? 1;
    const cx = dir > 0 ? lerp(0.24, 0.66, c1Smooth(normT)) : lerp(0.76, 0.34, c1Smooth(normT));
    const kind = drawEnvironmentForLocation(g, loc, worldState, { scrollX: lt * W * 0.14 });
    const actorId = primaryActorId(shot, kind === 'forum' ? 'senator_cassius' : kind === 'harbor' ? 'signifer_marc' : 'centurion_varro');
    if (kind === 'forum') drawStoneSenatorBench2D(g, W * 0.68, H * 0.58, W * 0.32, H * 0.062);
    if (kind === 'market') drawMarketCrowdGroup2D(g, worldState, { mood: 'watch' });
    drawV2Actor(g, t, shot, actorId, {
      ...computeWalkCyclePose(lt, cx, 0.59, 0.29, W, H),
      flip: dir < 0,
      look: 0.65,
      face: 'calm',
    }, W, H, { shoeMode: 'side' });
  },

  actor_deadpan_walk_unaffected(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.12, slopeDropFrac: 0.05 });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'hush',
      positions: [
        { x: 0.14, y: 0.49, h: 0.20, col: '#4a7a5c', look: 0.6, seed: 5, flip: false },
        { x: 0.86, y: 0.50, h: 0.20, col: PAL.crimson, look: -0.6, seed: 9, flip: true },
      ],
    });
    const cx = lerp(0.32, 0.66, c1Smooth(normT));
    const varro = drawV2Actor(g, t, shot, 'centurion_varro', {
      ...computeWalkCyclePose(lt, cx, 0.60, 0.32, W, H, 5.4, 7.5),
      face: 'bored',
      look: 0.55,
      blinkKeys: [[0, normT > 0.44 && normT < 0.56]],
    }, W, H, { shoeMode: 'side' });
    // Crown jewel comic payoff: golden scored Roman loaf still sitting squarely atop red helmet crest!
    const [hx, hy] = helmetTopWorld(varro);
    drawRomanLoaf2D(g, hx, hy - W * 0.012, W * 0.12, { rot: 0.03 * Math.sin(lt * 5.4), squishFrac: 0.12 });
  },

  actor_sprint_chase(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    if (loc === 'city_gate_approach') {
      drawRomanCityApproachDusk2D(g, worldState, { horizonYFrac: 0.46, groundYFrac: 0.56 });
      const marcusX = lerp(0.18, 0.68, c1Smooth(normT));
      drawV2Actor(g, t, shot, 'courier_marcus', {
        ...computeRunCyclePose(lt, marcusX, 0.60, 0.30, W, H),
        face: 'determined',
        look: 0.75,
      }, W, H, { shoeMode: 'side' });
      return;
    }
    const cartProg = clamp(worldState.cartRunFrac ?? normT, 0, 1);
    const slope = 0.095;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: cartProg * W * 1.15, slopeDropFrac: slope });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'gasp',
      positions: [
        { x: 0.13, y: 0.47, h: 0.19, col: '#c79745', look: 0.7, seed: 3, flip: false },
        { x: 0.87, y: 0.51, h: 0.19, col: PAL.red, look: -0.7, seed: 8, flip: true },
      ],
    });
    const cartX = lerp(0.58, 0.82, normT);
    const cartY = H * (0.56 + (cartX - 0.5) * slope);
    drawRomanCart2D(g, W * cartX, cartY, W * 0.40, {
      tiltRad: 0.085,
      wheelAngleRad: worldState.wheelAngleRad ?? (lt * 8.0),
      jiggleY: Math.sin(lt * 24) * 3,
    });
    // Titus sprinting hard behind runaway cart downhill!
    const titusX = lerp(0.20, 0.45, normT);
    const titusY = 0.56 + (titusX - 0.5) * slope;
    const pose = drawV2Actor(g, t, shot, 'apprentice_titus', {
      ...computeRunCyclePose(lt, titusX, titusY, 0.28, W, H, 12.2, 0.18, 14.5),
      face: 'scared',
      look: 0.8,
    }, W, H, { shoeMode: 'side' });
    dustPuff(g, pose.rootWorld[0] - W * 0.06, pose.rootWorld[1], W * 0.075, (lt * 2.8) % 1);
    drawMarketForegroundPass2D(g, normT);
  },

  actor_reach_grab_prop(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    if (loc === 'roman_river_harbor') {
      drawRomanRiverHarbor2D(g, worldState, { quayRightFrac: 0.52 });
      const reach = c2Smooth(normT);
      const vexX = lerp(W * 0.68, W * 0.55, reach);
      const vexY = H * 0.52 + Math.sin(lt * 4.5) * 6;
      drawClothVexillum2D(g, vexX, vexY, W * 0.22, { t, rot: 0.25, inWater: true });
      const marc = drawV2Actor(g, t, shot, 'signifer_marc', {
        xFrac: 0.36,
        yFrac: 0.46,
        hFrac: 0.30,
        bodyRot: lerp(0.08, 0.24, reach),
        ...v2FeetKeys(0.36, 0.46, 0.30, W, H, -9, 0, 9, 0),
        leftArmDegKeys: [[0, [-15, -25]]],
        rightArmDegKeys: [[0, [lerp(28, 72, reach), lerp(-10, -4, reach)]]],
        face: 'determined',
        look: 0.78,
      }, W, H, { shoeMode: 'side' });
      drawRopePath2D(g, marc.rightHandWorld, [vexX - W * 0.05, vexY], { tautFrac: reach * 0.8 });
      return;
    }
    const slope = 0.08;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.28, slopeDropFrac: slope });
    const grabK = c2Smooth(normT);
    const cartInfo = drawRomanCart2D(g, W * 0.72, H * 0.58, W * 0.38, {
      tiltRad: 0.07,
      wheelAngleRad: worldState.wheelAngleRad ?? (lt * 7.5),
      jiggleY: Math.sin(lt * 20) * 2.5,
    });
    const titus = drawV2Actor(g, t, shot, 'apprentice_titus', {
      ...computeRunCyclePose(lt, 0.33, 0.56, 0.29, W, H, 10.5, 0.16, 12.0),
      rightArmDegKeys: [[0, [lerp(36, 74, grabK), lerp(15, -8, grabK)]]],
      face: 'determined',
      look: 0.85,
    }, W, H, { shoeMode: 'side' });
    const coilTarget = [
      lerp(cartInfo.rearAxleWorld[0] - W * 0.08, titus.rightHandWorld[0], grabK),
      lerp(H * 0.56, titus.rightHandWorld[1], grabK),
    ];
    drawRopePath2D(g, cartInfo.rearAxleWorld, coilTarget, { tautFrac: 0.25 + grabK * 0.55, sagPx: 38 * (1 - grabK) });
  },

  actor_stop_brace(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.92, slopeDropFrac: 0.065 });
    const bollard = drawStoneBollard2D(g, W * 0.20, H * 0.57, W * 0.23, { ropeLoops: 2 });
    const braceK = c2Smooth(normT);
    const cartPosX = lerp(0.68, 0.72, Math.sin(normT * Math.PI * 0.5) * 0.35);
    const cartInfo = drawRomanCart2D(g, W * cartPosX, H * 0.59, W * 0.38, {
      tiltRad: lerp(0.06, -0.02, braceK),
      wheelAngleRad: worldState.wheelAngleRad ?? 14.0,
      skidDust: normT < 0.7 ? (1 - normT) : 0,
    });
    const titus = drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: 0.36,
      yFrac: 0.58,
      hFrac: 0.29,
      bodyRot: lerp(-0.08, -0.22, braceK),
      ...v2FeetKeys(0.36, 0.58, 0.29, W, H, -13, 0, 12, 0),
      leftKneeBend: 0.45,
      rightKneeBend: -0.35,
      leftArmDegKeys: [[0, [34, -22]]],
      rightArmDegKeys: [[0, [52, -16]]],
      face: 'pain',
      look: 0.65,
    }, W, H, { shoeMode: 'side' });
    // Continuous three-point rope: bollard post -> braced Titus hands -> runaway cart rear axle!
    drawRopePath2D(g, bollard.loopWorld, titus.rightHandWorld, {
      tautFrac: 0.96,
      vibrateAmp: Math.sin(lt * 32) * 3 * (1 - braceK * 0.5),
    });
    drawRopePath2D(g, titus.rightHandWorld, cartInfo.rearAxleWorld, {
      tautFrac: 0.98,
      vibrateAmp: Math.sin(lt * 38) * 3.5 * (1 - braceK * 0.5),
    });
  },

  actor_release_throw_prop(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    if (loc === 'roman_river_harbor') {
      drawRomanRiverHarbor2D(g, worldState, { quayRightFrac: 0.52 });
      const arcK = c1Smooth(normT);
      const vexX = W * 0.68, vexY = H * 0.52 + Math.sin(lt * 4.5) * 6;
      drawClothVexillum2D(g, vexX, vexY, W * 0.22, { t, rot: 0.25, inWater: true });
      const marc = drawV2Actor(g, t, shot, 'signifer_marc', {
        xFrac: 0.35,
        yFrac: 0.46,
        hFrac: 0.30,
        bodyRot: lerp(-0.1, 0.16, arcK),
        ...v2FeetKeys(0.35, 0.46, 0.30, W, H, -9, 0, 9, 0),
        leftArmDegKeys: [[0, [-20, -25]]],
        rightArmDegKeys: [[0, [lerp(130, 55, arcK), -10]]],
        face: 'shout',
        look: 0.7,
      }, W, H, { shoeMode: 'side' });
      const tipX = lerp(marc.rightHandWorld[0], vexX, arcK);
      const tipY = lerp(marc.rightHandWorld[1], vexY, arcK) - Math.sin(arcK * Math.PI) * H * 0.10;
      drawRopePath2D(g, marc.rightHandWorld, [tipX, tipY], { tautFrac: arcK * 0.4, sagPx: 45 });
      return;
    }
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.2 });
    const bollard = drawStoneBollard2D(g, W * 0.72, H * 0.58, W * 0.22, { ropeLoops: normT > 0.6 ? 1 : 0 });
    const throwK = c2Smooth(normT);
    const titus = drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: 0.42,
      yFrac: 0.58,
      hFrac: 0.29,
      bodyRot: lerp(-0.1, 0.18, throwK),
      ...v2FeetKeys(0.42, 0.58, 0.29, W, H, -10, 0, 10, 0),
      leftArmDegKeys: [[0, [-25, -35]]],
      rightArmDegKeys: [[0, [lerp(135, 58, throwK), -12]]],
      face: 'determined',
      look: 0.8,
    }, W, H, { shoeMode: 'side' });
    const endPt = [
      lerp(titus.rightHandWorld[0], bollard.loopWorld[0], throwK),
      lerp(titus.rightHandWorld[1], bollard.loopWorld[1], throwK) - Math.sin(throwK * Math.PI) * H * 0.09,
    ];
    drawRopePath2D(g, titus.rightHandWorld, endPt, { tautFrac: 0.5, sagPx: 28 * (1 - throwK) });
  },

  actor_point_shout_look(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    const kind = drawEnvironmentForLocation(g, loc, worldState);
    const actorId = primaryActorId(shot, kind === 'forum' ? 'forum_messenger' : kind === 'harbor' ? 'signifer_marc' : 'baker_lucius');
    if (kind === 'market') {
      drawBakeryOvenAndTray2D(g, W * 0.74, H * 0.56, W * 0.34, { t, loavesOnTray: worldState.loavesOnTray ?? 3 });
    } else if (kind === 'forum') {
      drawStoneSenatorBench2D(g, W * 0.68, H * 0.57, W * 0.33, H * 0.065);
    }
    const wave = Math.sin(lt * 10) * 8;
    const actor = drawV2Actor(g, t, shot, actorId, {
      xFrac: 0.36,
      yFrac: 0.57,
      hFrac: 0.31,
      headNodKeys: [[0, -2 + wave * 0.2]],
      ...v2FeetKeys(0.36, 0.57, 0.31, W, H, -8, 0, 8, 0),
      leftArmDegKeys: [[0, [-42, -55]]],
      rightArmDegKeys: [[0, [68 + wave, -16]]],
      face: 'shout',
      look: -0.5,
      talk: 0.7,
    }, W, H, { shoeMode: 'front' });
    drawShoutMotionArcs(g, actor.rootWorld[0] - W * 0.06, actor.rootWorld[1] - actor.actorH * 0.85, W * 0.14, lt);
  },

  actor_pickup_prop(g, ctx) {
    const { t, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    const kind = drawEnvironmentForLocation(g, loc, worldState);
    const k = c2Smooth(normT);
    const stoop = Math.sin(k * Math.PI);
    const actorId = primaryActorId(shot, kind === 'forum' ? 'senator_cassius' : 'apprentice_titus');
    if (kind === 'forum') {
      drawStoneSenatorBench2D(g, W * 0.64, H * 0.57, W * 0.34, H * 0.065);
    }
    const actor = drawV2Actor(g, t, shot, actorId, {
      xFrac: 0.42,
      yFrac: 0.57 + stoop * 0.02,
      hFrac: 0.30,
      bodyRot: lerp(0.10, 0.36 * stoop + 0.05, k),
      ...v2FeetKeys(0.42, 0.57 + stoop * 0.02, 0.30, W, H, -9, 0, 9, 0),
      leftKneeBend: 0.55 * stoop + 0.1,
      rightKneeBend: -0.5 * stoop - 0.1,
      leftArmDegKeys: [[0, [-18, -28]]],
      rightArmDegKeys: [[0, [lerp(50, 26, k), lerp(-10, -48, k)]]],
      face: normT > 0.65 ? 'smile' : 'focused',
      look: 0.4,
    }, W, H, { shoeMode: 'side' });
    if (kind === 'forum') {
      const helmPos = k < 0.45
        ? [lerp(W * 0.62, actor.rightHandWorld[0], k / 0.45), lerp(H * 0.55, actor.rightHandWorld[1], k / 0.45)]
        : [actor.rightHandWorld[0], actor.rightHandWorld[1]];
      drawCeremonialHelmetProp2D(g, helmPos[0], helmPos[1], W * 0.058, { rot: lerp(0.8, 0.05, k) });
    } else {
      drawRomanLoaf2D(g, actor.rightHandWorld[0], actor.rightHandWorld[1], W * 0.09);
    }
  },

  actor_pull_drag_rope_tension(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    if (loc === 'roman_river_harbor') {
      drawRomanRiverHarbor2D(g, worldState, { quayRightFrac: 0.52 });
      const pull = c2Smooth(normT);
      const vexX = lerp(W * 0.68, W * 0.49, pull);
      const vexY = lerp(H * 0.51, H * 0.41, pull) + Math.sin(lt * 6) * 4 * (1 - pull);
      drawClothVexillum2D(g, vexX, vexY, W * 0.22, { t, rot: lerp(0.32, 0.04, pull), inWater: pull < 0.72 });
      const marc = drawV2Actor(g, t, shot, 'signifer_marc', {
        xFrac: lerp(0.34, 0.26, pull),
        yFrac: 0.46,
        hFrac: 0.30,
        bodyRot: lerp(-0.10, -0.20, pull),
        ...v2FeetKeys(lerp(0.34, 0.26, pull), 0.46, 0.30, W, H, -10, 0, 11, 0),
        leftArmDegKeys: [[0, [30, -25]]],
        rightArmDegKeys: [[0, [48, -18]]],
        face: pull > 0.78 ? 'determined' : 'pain',
        look: 0.7,
      }, W, H, { shoeMode: 'side' });
      drawRopePath2D(g, marc.rightHandWorld, [vexX - W * 0.03, vexY], { tautFrac: 0.94, vibrateAmp: Math.sin(lt * 25) * 2 });
      return;
    }
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.85 });
    const bollard = drawStoneBollard2D(g, W * 0.18, H * 0.57, W * 0.22, { ropeLoops: 1 });
    const pullK = c2Smooth(normT);
    const cartInfo = drawRomanCart2D(g, W * 0.74, H * 0.59, W * 0.38, { tiltRad: 0.05, wheelAngleRad: lt * 2.5 });
    const titus = drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: lerp(0.42, 0.34, pullK),
      yFrac: 0.58,
      hFrac: 0.29,
      bodyRot: -0.18,
      ...v2FeetKeys(lerp(0.42, 0.34, pullK), 0.58, 0.29, W, H, -12, 0, 11, 0),
      leftArmDegKeys: [[0, [36, -24]]],
      rightArmDegKeys: [[0, [50, -18]]],
      face: 'pain',
      look: 0.6,
    }, W, H, { shoeMode: 'side' });
    drawRopePath2D(g, bollard.loopWorld, titus.rightHandWorld, { tautFrac: 0.9 });
    drawRopePath2D(g, titus.rightHandWorld, cartInfo.rearAxleWorld, { tautFrac: 0.96, vibrateAmp: Math.sin(lt * 28) * 3 });
  },

  actor_push_hold_load(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.15, slopeDropFrac: 0.07 });
    const cartInfo = drawRomanCart2D(g, W * 0.65, H * 0.58, W * 0.39, { tiltRad: 0.04, wheelAngleRad: lt * 3.0 });
    drawV2Actor(g, t, shot, primaryActorId(shot, 'apprentice_titus'), {
      xFrac: 0.40,
      yFrac: 0.58,
      hFrac: 0.29,
      bodyRot: 0.22 + Math.sin(lt * 10) * 0.02,
      ...v2FeetKeys(0.40, 0.58, 0.29, W, H, -12, 0, 12, 0),
      leftArmDegKeys: [[0, [52, -12]]],
      rightArmDegKeys: [[0, [62, -10]]],
      face: 'pain',
      look: 0.8,
    }, W, H, { shoeMode: 'side' });
    drawRopePath2D(g, [W * 0.32, H * 0.52], cartInfo.rearAxleWorld, { tautFrac: 0.7 });
  },

  actor_handoff_prop(g, ctx) {
    const { t, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    const kind = drawEnvironmentForLocation(g, loc, worldState);
    const give = c2Smooth(normT);
    const leftId = shot.actor_ids?.[0] || (kind === 'forum' ? 'senator_cassius' : 'apprentice_titus');
    const rightId = shot.actor_ids?.[1] || (kind === 'forum' ? 'forum_messenger' : 'baker_lucius');
    if (kind === 'forum') drawStoneSenatorBench2D(g, W * 0.81, H * 0.56, W * 0.25, H * 0.055);
    const a1 = drawV2Actor(g, t, shot, leftId, {
      xFrac: 0.30,
      yFrac: 0.58,
      hFrac: 0.30,
      bodyRot: 0.06,
      ...v2FeetKeys(0.30, 0.58, 0.30, W, H, -8, 0, 8, 0),
      rightArmDegKeys: [[0, [lerp(36, 56, give), -14]]],
      face: 'calm',
      look: 0.65,
    }, W, H, { shoeMode: 'side' });
    const a2 = drawV2Actor(g, t, shot, rightId, {
      xFrac: 0.58,
      yFrac: 0.58,
      hFrac: 0.30,
      flip: true,
      bodyRot: 0.05,
      ...v2FeetKeys(0.58, 0.58, 0.30, W, H, -8, 0, 8, 0),
      rightArmDegKeys: [[0, [lerp(32, 54, give), -16]]],
      face: normT > 0.6 ? 'happy' : 'surprised',
      look: 0.65,
    }, W, H, { shoeMode: 'side' });
    const hx = lerp(a1.rightHandWorld[0], a2.rightHandWorld[0], give);
    const hy = lerp(a1.rightHandWorld[1], a2.rightHandWorld[1], give);
    if (kind === 'forum') {
      drawCeremonialHelmetProp2D(g, hx, hy, W * 0.055, { rot: 0 });
    } else {
      drawRomanLoaf2D(g, hx, hy, W * 0.11);
    }
  },

  actor_stumble_recover(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const loc = resolveLocation(shot, worldState);
    drawEnvironmentForLocation(g, loc, worldState, { scrollX: lt * W * 0.18 });
    const slip = Math.sin(c1Smooth(normT) * Math.PI);
    const cx = lerp(0.32, 0.54, normT);
    const pose = drawV2Actor(g, t, shot, primaryActorId(shot, loc === 'roman_forum_courtyard' ? 'forum_messenger' : 'apprentice_titus'), {
      xFrac: cx,
      yFrac: 0.58 + slip * 0.02,
      hFrac: 0.29,
      bodyRot: 0.12 + slip * 0.34,
      ...v2FeetKeys(cx, 0.58 + slip * 0.02, 0.29, W, H, -11, -slip * 4, 12, slip * 3),
      leftArmDegKeys: [[0, [-40 - slip * 50, -35]]],
      rightArmDegKeys: [[0, [45 + slip * 55, -20]]],
      face: slip > 0.45 ? 'shock' : 'determined',
      look: 0.6,
    }, W, H, { shoeMode: 'side' });
    dustPuff(g, pose.rootWorld[0], pose.rootWorld[1], W * 0.09, clamp(normT * 1.4, 0, 1));
    if (loc === 'roman_forum_courtyard') {
      drawCeremonialHelmetProp2D(g, lerp(pose.rootWorld[0] + W * 0.08, W * 0.68, c1Smooth(normT)), H * 0.56, W * 0.052, { rot: normT * 5.0 });
    }
  },

  actor_crowd_reaction_cheer(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.98, slopeDropFrac: 0.05 });
    const bollard = drawStoneBollard2D(g, W * 0.16, H * 0.57, W * 0.20, { ropeLoops: 2 });
    const cartInfo = drawRomanCart2D(g, W * 0.54, H * 0.59, W * 0.36, { tiltRad: 0.0, wheelAngleRad: worldState.wheelAngleRad ?? 18 });
    drawRopePath2D(g, bollard.loopWorld, cartInfo.rearAxleWorld, { tautFrac: 0.92 });
    drawBakeryOvenAndTray2D(g, W * 0.85, H * 0.58, W * 0.29, { t, loavesOnTray: 2 });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'cheer',
      positions: [
        { x: 0.15, y: 0.46, h: 0.18, col: PAL.red, look: 0.4, seed: 3, flip: false },
        { x: 0.34, y: 0.45, h: 0.19, col: '#4a7a5c', look: 0.2, seed: 5, flip: false },
        { x: 0.66, y: 0.46, h: 0.19, col: '#c79745', look: -0.3, seed: 9, flip: true },
        { x: 0.85, y: 0.47, h: 0.18, col: PAL.crimson, look: -0.5, seed: 12, flip: true },
      ],
    });
    drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: 0.32,
      yFrac: 0.57,
      hFrac: 0.26,
      bodyRot: -0.02,
      ...v2FeetKeys(0.32, 0.57, 0.26, W, H, -7, 0, 7, 0),
      leftArmDegKeys: [[0, [-125 + Math.sin(lt * 10) * 14, -20]]],
      rightArmDegKeys: [[0, [125 + Math.cos(lt * 10) * 14, -20]]],
      face: 'happy',
      look: 0.0,
    }, W, H, { shoeMode: 'front' });
  },

  prop_peg_crack_snap(g, ctx) {
    const { lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: 0, slopeDropFrac: 0.085 });
    const snapped = normT > 0.46;
    const shake = normT < 0.46 ? Math.sin(lt * 55) * 3 : 0;
    const crack = clamp(normT / 0.46, 0, 1);
    const wheelAng = snapped ? (normT - 0.46) * 2.4 : 0;
    drawBrakePeg2D(g, W * 0.50 + shake, H * 0.56, W * 0.46, {
      crackFrac: crack,
      snapped,
      flySep: snapped ? clamp((normT - 0.46) / 0.54, 0, 1) : 0,
      wheelAngleRad: wheelAng,
    });
    // Titus alarmed reaction silhouette upper-left edge so shot stays populated cleanly
    drawV2Actor(g, ctx.t, shot, 'apprentice_titus', {
      xFrac: 0.20,
      yFrac: 0.56,
      hFrac: 0.25,
      ...v2FeetKeys(0.20, 0.56, 0.25, W, H, -7, 0, 7, 0),
      leftArmDegKeys: [[0, [-35, -45]]],
      rightArmDegKeys: [[0, [48, -32]]],
      face: snapped ? 'shock' : 'worried',
      look: 0.85,
    }, W, H, { shoeMode: 'side' });
  },

  prop_cart_roll_slope(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const prog = worldState.cartRunFrac ?? normT;
    const slope = 0.095;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: prog * W * 1.4, slopeDropFrac: slope });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'gasp',
      positions: [
        { x: 0.14, y: 0.46, h: 0.18, col: '#4a7a5c', look: 0.7, seed: 5, flip: false },
        { x: 0.86, y: 0.50, h: 0.18, col: '#c79745', look: -0.7, seed: 9, flip: true },
      ],
    });
    const cartX = lerp(0.32, 0.68, c1Smooth(normT));
    const cartY = H * (0.56 + (cartX - 0.5) * slope);
    drawRomanCart2D(g, W * cartX, cartY, W * 0.44, {
      tiltRad: 0.095,
      wheelAngleRad: worldState.wheelAngleRad ?? (lt * 9.5),
      jiggleY: Math.sin(lt * 26) * 3.5,
      skidDust: (lt * 2.2) % 1,
    });
    drawMarketForegroundPass2D(g, normT);
  },

  prop_rope_taut_post_wrap(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.85, slopeDropFrac: 0.07 });
    const wrapK = c2Smooth(normT);
    const loops = wrapK > 0.35 ? 2 : 1;
    const bollard = drawStoneBollard2D(g, W * 0.19, H * 0.57, W * 0.26, { ropeLoops: loops });
    const cartInfo = drawRomanCart2D(g, W * lerp(0.68, 0.74, 0.5), H * 0.58, W * 0.34, {
      tiltRad: 0.04,
      wheelAngleRad: worldState.wheelAngleRad ?? (lt * 3.0),
    });
    const titus = drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: 0.33,
      yFrac: 0.57,
      hFrac: 0.28,
      bodyRot: -0.14,
      ...v2FeetKeys(0.33, 0.57, 0.28, W, H, -10, 0, 10, 0),
      leftArmDegKeys: [[0, [24, -18]]],
      rightArmDegKeys: [[0, [52, -10]]],
      face: 'determined',
      look: 0.5,
    }, W, H, { shoeMode: 'side' });
    drawRopePath2D(g, bollard.loopWorld, titus.rightHandWorld, {
      tautFrac: wrapK,
      sagPx: 22 * (1 - wrapK),
      vibrateAmp: Math.sin(lt * 40) * 3 * wrapK,
    });
    drawRopePath2D(g, titus.rightHandWorld, cartInfo.rearAxleWorld, {
      tautFrac: wrapK,
      sagPx: 38 * (1 - wrapK),
      vibrateAmp: Math.sin(lt * 40) * 4 * wrapK,
    });
  },

  prop_cart_halt_skid(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.96, slopeDropFrac: 0.045 });
    const bollard = drawStoneBollard2D(g, W * 0.13, H * 0.58, W * 0.20, { ropeLoops: 2 });
    const easeStop = c2Smooth(normT);
    // Clear dramatic handspan gap between halted cart shafts and oven hearth!
    const cartX = lerp(0.36, 0.43, easeStop);
    drawBakeryOvenAndTray2D(g, W * 0.85, H * 0.58, W * 0.30, {
      t,
      trayShakePx: normT > 0.65 ? Math.sin(lt * 46) * 5 * (1 - normT) : 0,
      loavesOnTray: 3,
    });
    const cartInfo = drawRomanCart2D(g, W * cartX, H * 0.59, W * 0.33, {
      tiltRad: lerp(0.05, -0.04, easeStop),
      wheelAngleRad: (worldState.wheelAngleRad ?? 16.0) + (1 - easeStop) * 1.2,
      skidDust: clamp((1 - normT) * 1.1, 0, 1),
    });
    drawRopePath2D(g, bollard.loopWorld, cartInfo.rearAxleWorld, {
      tautFrac: 1.0,
      vibrateAmp: Math.sin(lt * 48) * 3.5 * (1 - easeStop),
    });
    drawV2Actor(g, t, shot, 'baker_lucius', {
      xFrac: 0.77,
      yFrac: 0.57,
      hFrac: 0.27,
      ...v2FeetKeys(0.77, 0.57, 0.27, W, H, -7, 0, 7, 0),
      leftArmDegKeys: [[0, [-42, -50]]],
      rightArmDegKeys: [[0, [42, -50]]],
      face: 'shock',
      look: -0.75,
    }, W, H, { shoeMode: 'front' });
  },

  prop_bounce_tray(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.96, slopeDropFrac: 0.04 });
    const cartInfo = drawRomanCart2D(g, W * 0.43, H * 0.59, W * 0.33, { tiltRad: 0.0, wheelAngleRad: worldState.wheelAngleRad ?? 18 });
    const jolt = Math.sin(c1Smooth(normT) * Math.PI);
    const ovenInfo = drawBakeryOvenAndTray2D(g, W * 0.83, H * 0.58, W * 0.35, {
      t,
      trayShakePx: Math.sin(lt * 48) * 9 * (1 - normT),
      loavesOnTray: 2,
    });
    const loafX = lerp(ovenInfo.trayTopWorld[0], ovenInfo.trayTopWorld[0] + W * 0.04, normT);
    const loafY = ovenInfo.trayTopWorld[1] - jolt * H * 0.08 - normT * H * 0.05;
    drawRomanLoaf2D(g, loafX, loafY, W * 0.105, { rot: normT * 1.4, trail: normT > 0.3 });
    drawV2Actor(g, t, shot, 'baker_lucius', {
      xFrac: 0.72,
      yFrac: 0.58,
      hFrac: 0.27,
      ...v2FeetKeys(0.72, 0.58, 0.27, W, H, -7, 0, 7, 0),
      rightArmDegKeys: [[0, [52, -40]]],
      face: 'surprised',
      look: 0.5,
    }, W, H, { shoeMode: 'front' });
    if (cartInfo.frontBumperWorld) {
      dustPuff(g, cartInfo.frontBumperWorld[0], H * 0.59, W * 0.06, clamp(normT, 0, 1));
    }
  },

  prop_parabolic_arc(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 0.98, slopeDropFrac: 0.04 });
    drawBakeryOvenAndTray2D(g, W * 0.20, H * 0.58, W * 0.28, { t, loavesOnTray: 2 });
    const varro = drawV2Actor(g, t, shot, 'centurion_varro', {
      ...computeWalkCyclePose(lt, 0.72, 0.59, 0.30, W, H, 5.2, 6.5),
      face: 'bored',
      look: 0.4,
    }, W, H, { shoeMode: 'side' });
    const [topX, topY] = helmetTopWorld(varro);
    const startX = W * 0.22, startY = H * 0.43;
    const lx = lerp(startX, topX, normT);
    const ly = lerp(startY, topY - H * 0.03, normT) - Math.sin(normT * Math.PI) * H * 0.11;
    drawRomanLoaf2D(g, lx, ly, W * 0.115, { rot: normT * Math.PI * 2.5, trail: true });
  },

  prop_helmet_impact_settle(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: W * 1.0, slopeDropFrac: 0.04 });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'hush',
      positions: [
        { x: 0.16, y: 0.49, h: 0.19, col: '#4a7a5c', look: 0.7, seed: 5, flip: false },
        { x: 0.85, y: 0.50, h: 0.19, col: '#c79745', look: -0.7, seed: 9, flip: true },
      ],
    });
    const landK = clamp(normT / 0.42, 0, 1);
    const nod = normT > 0.35 && normT < 0.75 ? Math.sin(((normT - 0.35) / 0.40) * Math.PI) * 3.5 : 0;
    const varro = drawV2Actor(g, t, shot, 'centurion_varro', {
      ...computeWalkCyclePose(lt, 0.50, 0.60, 0.33, W, H, 4.8, 5.5),
      headNodKeys: [[0, nod]],
      face: 'bored',
      look: 0.15,
    }, W, H, { shoeMode: 'side' });
    const [topX, topY] = helmetTopWorld(varro);
    const lx = lerp(topX - W * 0.12, topX, c2Smooth(landK));
    const ly = lerp(topY - H * 0.18, topY - W * 0.012, c2Smooth(landK));
    const squish = normT > 0.38 ? Math.sin(clamp((normT - 0.38) / 0.3, 0, 1) * Math.PI) * 0.25 + 0.10 : 0;
    drawRomanLoaf2D(g, lx, ly, W * 0.12, { rot: (1 - landK) * 1.5, squishFrac: squish, trail: landK < 0.85 });
  },

  prop_vexillum_river_drift(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanRiverHarbor2D(g, worldState, { quayRightFrac: 0.50 });
    const drift = c1Smooth(normT);
    const vx = lerp(W * 0.62, W * 0.72, drift);
    const vy = lerp(H * 0.48, H * 0.56, drift) + Math.sin(lt * 5.0) * 6;
    drawClothVexillum2D(g, vx, vy, W * 0.24, { t, rot: 0.28 + Math.sin(lt * 3) * 0.08, inWater: true });
    drawV2Actor(g, t, shot, 'signifer_marc', {
      xFrac: 0.30,
      yFrac: 0.45,
      hFrac: 0.28,
      bodyRot: 0.16,
      ...v2FeetKeys(0.30, 0.45, 0.28, W, H, -9, 0, 9, 0),
      rightArmDegKeys: [[0, [62, -16]]],
      face: 'worried',
      look: 0.75,
    }, W, H, { shoeMode: 'side' });
  },

  prop_helmet_roll_under_bench(g, ctx) {
    const { t, normT, shot, worldState, W, H } = ctx;
    drawRomanForumCourtyard2D(g, worldState);
    const roll = c2Smooth(normT);
    drawStoneSenatorBench2D(g, W * 0.64, H * 0.58, W * 0.38, H * 0.072);
    // Helmet visibly rolls along travertine floor from messenger's foot into open space under bench
    const hx = lerp(W * 0.28, W * 0.63, roll);
    const hy = H * 0.565 - Math.abs(Math.sin(roll * Math.PI * 2.5)) * H * 0.012;
    drawCeremonialHelmetProp2D(g, hx, hy, W * 0.056, { rot: roll * Math.PI * 3.0 });
    drawV2Actor(g, t, shot, 'forum_messenger', {
      xFrac: 0.22,
      yFrac: 0.58,
      hFrac: 0.29,
      bodyRot: 0.14,
      ...v2FeetKeys(0.22, 0.58, 0.29, W, H, -8, 0, 8, 0),
      rightArmDegKeys: [[0, [52, -20]]],
      face: 'shock',
      look: 0.85,
    }, W, H, { shoeMode: 'side' });
  },

  prop_scroll_open_adapter(g, ctx) {
    const { t, normT, shot, worldState, W, H } = ctx;
    drawRomanGuardThreshold2D(g, worldState, { floorYFrac: 0.61, showDrain: false });
    const k = clamp(normT / 0.6, 0, 1);
    const marcus = drawV2Actor(g, t, shot, 'courier_marcus', {
      xFrac: 0.24,
      yFrac: 0.61,
      hFrac: 0.29,
      ...v2FeetKeys(0.24, 0.61, 0.29, W, H, -7, 0, 7, 0),
      face: 'tired',
      look: 0.5,
    }, W, H, { shoeMode: 'side' });
    const scX = W * 0.62;
    const scY = marcus.rootWorld[1] - marcus.actorH * 0.35;
    drawSealedRomanScroll2D(g, scX, scY, W * 0.18, {
      mode: 'unrolled_message',
      mudAmount: 0.65,
      rot: lerp(-0.18, 0.02, c2Smooth(k)),
      lines: ['KEEP', 'THE GATE', 'OPEN'],
    });
  },

  prop_door_close_adapter(g, ctx) {
    const { t, normT, shot, worldState, W, H } = ctx;
    const state = { ...worldState, gateCloseFrac: clamp(0.45 + normT * 0.55, 0, 1), boltDropFrac: clamp((normT - 0.65) / 0.35, 0, 1) };
    drawRomanCityApproachDusk2D(g, state, { horizonYFrac: 0.46, groundYFrac: 0.56 });
    drawV2Actor(g, t, shot, 'courier_marcus', {
      xFrac: 0.32,
      yFrac: 0.60,
      hFrac: 0.29,
      ...v2FeetKeys(0.32, 0.60, 0.29, W, H, -7, 0, 7, 0),
      rightArmDegKeys: [[0, [68, -22]]],
      face: 'shock',
      look: 0.6,
    }, W, H, { shoeMode: 'side' });
  },

  world_market_hill_establish(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    const slope = 0.085;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.06, slopeDropFrac: slope });
    drawBakeryOvenAndTray2D(g, W * 0.80, H * 0.57, W * 0.31, { t, loavesOnTray: 3 });
    drawStoneBollard2D(g, W * 0.38, H * 0.54, W * 0.16, { ropeLoops: 0 });
    drawMarketCrowdGroup2D(g, worldState, { mood: 'watch' });
    // Steep uphill market cart poised above the slope while Titus wipes his brow beside the rear wheel
    drawRomanCart2D(g, W * 0.24, H * 0.51, W * 0.36, { tiltRad: 0.075, wheelAngleRad: Math.sin(normT * Math.PI) * 0.08 });
    drawV2Actor(g, t, shot, 'apprentice_titus', {
      xFrac: 0.15,
      yFrac: 0.52,
      hFrac: 0.26,
      ...v2FeetKeys(0.15, 0.52, 0.26, W, H, -7, 0, 7, 0),
      rightArmDegKeys: [[0, [48, -60]]],
      face: 'worried',
      look: 0.65,
    }, W, H, { shoeMode: 'side' });
    drawV2Actor(g, t, shot, 'baker_lucius', {
      xFrac: 0.62,
      yFrac: 0.57,
      hFrac: 0.28,
      flip: true,
      ...v2FeetKeys(0.62, 0.57, 0.28, W, H, -7, 0, 7, 0),
      rightArmDegKeys: [[0, [24, -40]]],
      face: 'calm',
      look: 0.35,
    }, W, H, { shoeMode: 'front' });
  },

  world_market_crowd_pass(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanMarketSlopeBackdrop2D(g, worldState, { scrollX: lt * W * 0.35, slopeDropFrac: 0.085 });
    drawMarketCrowdGroup2D(g, worldState, {
      mood: 'gasp',
      positions: [
        { x: 0.20, y: 0.48, h: 0.21, col: PAL.red, look: 0.6, seed: 3, flip: false },
        { x: 0.42, y: 0.47, h: 0.22, col: '#4a7a5c', look: 0.5, seed: 5, flip: false },
        { x: 0.64, y: 0.48, h: 0.22, col: '#c79745', look: -0.5, seed: 9, flip: true },
        { x: 0.84, y: 0.49, h: 0.21, col: PAL.crimson, look: -0.7, seed: 12, flip: true },
      ],
    });
    const cx = lerp(0.16, 0.72, normT);
    drawRomanCart2D(g, W * cx, H * 0.58, W * 0.38, {
      tiltRad: 0.08,
      wheelAngleRad: worldState.wheelAngleRad ?? (lt * 8.0),
    });
    drawMarketForegroundPass2D(g, normT);
  },

  world_river_harbor_establish(g, ctx) {
    const { t, lt, normT, shot, worldState, W, H } = ctx;
    drawRomanRiverHarbor2D(g, worldState, { quayRightFrac: 0.52 });
    const vexY = H * 0.49 + Math.sin(lt * 4.2) * 5;
    drawClothVexillum2D(g, W * 0.66, vexY, W * 0.23, { t, rot: 0.28, inWater: true });
    drawV2Actor(g, t, shot, 'signifer_marc', {
      xFrac: 0.30,
      yFrac: 0.45,
      hFrac: 0.29,
      ...v2FeetKeys(0.30, 0.45, 0.29, W, H, -8, 0, 8, 0),
      rightArmDegKeys: [[0, [48, -32]]],
      face: 'worried',
      look: 0.8,
    }, W, H, { shoeMode: 'side' });
  },

  world_forum_courtyard_establish(g, ctx) {
    const { t, shot, worldState, W, H } = ctx;
    drawRomanForumCourtyard2D(g, worldState);
    drawStoneSenatorBench2D(g, W * 0.64, H * 0.57, W * 0.36, H * 0.07);
    drawCeremonialHelmetProp2D(g, W * 0.62, H * 0.555, W * 0.052, { rot: 0.45 });
    drawV2Actor(g, t, shot, 'senator_cassius', {
      xFrac: 0.36,
      yFrac: 0.56,
      hFrac: 0.30,
      ...v2FeetKeys(0.36, 0.56, 0.30, W, H, -7, 0, 7, 0),
      rightArmDegKeys: [[0, [30, -35]]],
      face: 'surprised',
      look: 0.6,
    }, W, H, { shoeMode: 'side' });
  },
});

export function validateRomanActionRendererCoverage(requiredRendererIds = Object.values(ACTION_ID_TO_RENDERER_ID)) {
  const missing = [];
  for (const id of requiredRendererIds) {
    if (typeof ROMAN_ACTION_RENDERERS[id] !== 'function') {
      missing.push(id);
    }
  }
  return {
    valid: missing.length === 0,
    registeredCount: Object.values(ROMAN_ACTION_RENDERERS).filter((fn) => typeof fn === 'function').length,
    missing,
  };
}

// Fail-closed dispatcher for KH-03.0.R2 shots. NEVER falls back to an unrelated guard/default shot.
export function renderRomanAction2D(g, ctx) {
  const shot = ctx?.shot || {};
  const actionId = shot.action_id || '';
  const requestedHandler = shot.renderer_action_id || ACTION_ID_TO_RENDERER_ID[actionId] || '';
  if (!requestedHandler) {
    throw new Error(
      `KH03_R2_UNSUPPORTED_RUNTIME_ACTION: Shot '${shot.id || 'unknown'}' has empty/unregistered action_id='${actionId}'. Fail-closed (no default fallback).`
    );
  }
  if (actionId && ACTION_ID_TO_RENDERER_ID[actionId] && ACTION_ID_TO_RENDERER_ID[actionId] !== requestedHandler) {
    throw new Error(
      `KH03_R2_UNSAFE_HANDLER_MISMATCH: Shot '${shot.id}' action_id='${actionId}' expects '${ACTION_ID_TO_RENDERER_ID[actionId]}', got '${requestedHandler}'.`
    );
  }
  const fn = ROMAN_ACTION_RENDERERS[requestedHandler];
  if (typeof fn !== 'function') {
    throw new Error(
      `KH03_R2_MISSING_RENDER_HANDLER: Renderer handler '${requestedHandler}' is not registered in ROMAN_ACTION_RENDERERS. Fail-closed (no default fallback).`
    );
  }
  return fn(g, ctx);
}
