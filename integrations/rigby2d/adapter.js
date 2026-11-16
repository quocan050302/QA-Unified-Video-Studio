// SPDX-License-Identifier: MIT
// FL-01 V14.7.6 Rigby2D Runtime Adapter (browser Chromium render.mjs + Node ESM).
// Uses unmodified vendored Rigby2D core + WebGL runtime (MIT OR Apache-2.0,
// jaisurya-dev-art/rigby2d develop SHA 130562a94e76a19986aa8b737f998a89c1270bb8)
// and 100% original procedural Roman harbor civilian assets.

import {
  Pose,
  parseAtlas,
  readSkeletonJson,
  drawSkeletonGeometry,
} from './vendor/core/index.js';
import { WebGLRenderer } from './vendor/webgl/renderer.js';
import { evaluateMotionTrackAt } from '../../packs/squire/motion_engine.js';

export const RIGBY_UPSTREAM_INFO = Object.freeze({
  package_name: 'rigby2d',
  version: '0.5.1',
  repository: 'https://github.com/jaisurya-dev-art/rigby2d',
  branch: 'develop',
  commit_sha: '130562a94e76a19986aa8b737f998a89c1270bb8',
  license: 'MIT OR Apache-2.0',
  demo_assets_copied: false,
});

function round4(v) {
  return Math.round(Number(v || 0) * 10000) / 10000;
}

/**
 * Inspect Rigby2D runtime capabilities from parsed skeleton JSON + atlas text.
 * Fails closed if skeleton or atlas is missing/invalid.
 */
export function inspectRigbyRuntimeCapabilities({ skeletonJson, atlasText, manifest = null } = {}) {
  if (!skeletonJson || typeof skeletonJson !== 'object') {
    throw new Error('RIGBY_PILOT_BLOCKED: missing skeletonJson input');
  }
  if (!atlasText || typeof atlasText !== 'string') {
    throw new Error('RIGBY_PILOT_BLOCKED: missing atlasText input');
  }
  const { skeleton, warnings } = readSkeletonJson(skeletonJson, manifest?.character_id || 'roman_harbor_worker');
  const validationError = skeleton.validate();
  if (validationError) {
    throw new Error(`RIGBY_PILOT_BLOCKED: skeleton validation failed: ${validationError}`);
  }
  const atlas = parseAtlas(atlasText);
  if (!atlas.pages || atlas.pages.length === 0 || (atlas.pages[0].regions || []).length === 0) {
    throw new Error('RIGBY_PILOT_BLOCKED: atlas contains zero pages or regions');
  }

  // Stateless Pose smoke check on setup + first animation
  const pose = new Pose(skeleton);
  pose.reset(skeleton);
  if (skeleton.animations.length > 0) {
    pose.apply(skeleton, skeleton.animations[0], 0.25, 1.0);
  }
  pose.updateWorld(skeleton);

  let emittedTriangles = 0;
  let emittedAttachments = 0;
  const dummyLookup = (name) => ({
    tex: { name, width: 512, height: 512 },
    trim: [0, 0, 1, 1],
    map(u, v, out) {
      out[0] = u;
      out[1] = v;
      return out;
    },
  });
  drawSkeletonGeometry(skeleton, pose, dummyLookup, (_tex, _blend, _pos, _uvs, tris) => {
    emittedAttachments += 1;
    emittedTriangles += (tris ? tris.length : 0) / 3;
  });
  if (emittedAttachments === 0 || emittedTriangles === 0) {
    throw new Error('RIGBY_PILOT_BLOCKED: zero attachments/triangles emitted by drawSkeletonGeometry');
  }

  return {
    status: 'RUNTIME_VERIFIED',
    ...RIGBY_UPSTREAM_INFO,
    webgl_renderer_exported: typeof WebGLRenderer === 'function',
    character_id: skeleton.name,
    spine_format_version: skeleton.header?.version || '3.8',
    bone_count: skeleton.bones.length,
    bones: skeleton.bones.map((b) => b.name),
    slot_count: skeleton.slots.length,
    slots: skeleton.slots.map((s) => s.name),
    ik_constraint_count: skeleton.ik.length,
    ik_constraints: skeleton.ik.map((c) => ({
      name: c.name,
      bones: c.bones.map((bi) => skeleton.bones[bi]?.name),
      target: skeleton.bones[c.target]?.name,
      bendPositive: c.bendPositive,
      mix: c.mix,
    })),
    animations: skeleton.animations.map((a) => ({ name: a.name, duration: round4(a.duration) })),
    atlas_pages: atlas.pages.map((p) => ({
      name: p.name,
      width: p.width,
      height: p.height,
      region_count: p.regions.length,
      regions: p.regions.map((r) => r.name),
    })),
    emitted_attachments: emittedAttachments,
    emitted_triangles: emittedTriangles,
    warnings,
  };
}

export const inspect_rigby_runtime_capabilities = inspectRigbyRuntimeCapabilities;

/**
 * Convert FL-01 MotionPlan ActorMotionTracks into genuine Spine 3.8 / Rigby2D animation timelines
 * mapped onto `roman_harbor_worker` bones and 2-bone IK target bones.
 */
export function convertMotionPlanToRigbyTracks(motionPlan, characterRigManifest = {}, options = {}) {
  const inputTracks = motionPlan?.tracks || motionPlan?.actor_tracks;
  if (!motionPlan || !Array.isArray(inputTracks)) {
    throw new Error('convertMotionPlanToRigbyTracks requires a MotionPlan with tracks');
  }
  const rigHeight = Number(characterRigManifest?.height_units || 210.0);
  const setupTargets = characterRigManifest?.setup_targets || {
    ik_foot_l_target: { x: 10.0, y: 6.0 },
    ik_foot_r_target: { x: -8.0, y: 6.0 },
    ik_hand_l_target: { x: 28.0, y: 98.0 },
    ik_hand_r_target: { x: 24.0, y: 94.0 },
  };
  const fps = Number(options.fps || 24);
  const worldState = options.worldState || (motionPlan.world_states && motionPlan.world_states[0]) || {};

  const compiledTracks = {};
  for (const track of inputTracks) {
    const startSec = Number(track.start_sec || 0);
    const endSec = Math.max(startSec + 1 / fps, Number(track.end_sec || startSec + 1));
    const dur = endSec - startSec;
    const totalSteps = Math.max(2, Math.round(dur * fps));
    const heightNorm = Math.max(0.12, Number(track.height_norm || options.heightNorm || 0.28));
    const unitScale = rigHeight / heightNorm;

    const pelvisTranslate = [];
    const torsoRotate = [];
    const headRotate = [];
    const cloakRotate = [];
    const footLTranslate = [];
    const footRTranslate = [];
    const handLTranslate = [];
    const handRTranslate = [];
    const rootWorldSamples = [];

    for (let i = 0; i <= totalSteps; i++) {
      const localT = round4(Math.min(dur, i / fps));
      const absT = startSec + localT;
      const ev = evaluateMotionTrackAt(track, absT, worldState);
      const facing = (ev.facing ?? 1) >= 0 ? 1 : -1;
      const rx = Number(ev.root[0]);
      const ry = Number(ev.root[1]);

      const toRigLocal = (pt) => {
        const dx = (Number(pt[0]) - rx) * facing * unitScale;
        const dy = -(Number(pt[1]) - ry) * unitScale;
        return { x: dx, y: dy };
      };

      const fl = toRigLocal(ev.leftFootWorld);
      const fr = toRigLocal(ev.rightFootWorld);
      const hl = toRigLocal(ev.leftHandWorld);
      const hr = toRigLocal(ev.rightHandWorld);

      const pelvisDy = -(Number(ev.hipWorld[1]) - (ry - heightNorm * 0.32)) * unitScale;
      const pelvisDx = (Number(ev.hipWorld[0]) - rx) * facing * unitScale * 0.55;
      const leanDeg = -(Number(ev.torsoLeanRad || 0) * 180) / Math.PI;
      const headDeg = -((Number(ev.secondary?.headLagRad || 0)) * 180) / Math.PI;
      const cloakDeg = (Number(ev.secondary?.clothTrailNorm || 0) / heightNorm) * 120.0;

      pelvisTranslate.push({ time: localT, x: round4(pelvisDx), y: round4(pelvisDy) });
      torsoRotate.push({ time: localT, angle: round4(leanDeg) });
      headRotate.push({ time: localT, angle: round4(headDeg) });
      cloakRotate.push({ time: localT, angle: round4(cloakDeg) });

      footLTranslate.push({
        time: localT,
        x: round4(fl.x - setupTargets.ik_foot_l_target.x),
        y: round4(Math.max(-setupTargets.ik_foot_l_target.y, fl.y - setupTargets.ik_foot_l_target.y)),
      });
      footRTranslate.push({
        time: localT,
        x: round4(fr.x - setupTargets.ik_foot_r_target.x),
        y: round4(Math.max(-setupTargets.ik_foot_r_target.y, fr.y - setupTargets.ik_foot_r_target.y)),
      });
      handLTranslate.push({
        time: localT,
        x: round4(hl.x - setupTargets.ik_hand_l_target.x),
        y: round4(hl.y - setupTargets.ik_hand_l_target.y),
      });
      handRTranslate.push({
        time: localT,
        x: round4(hr.x - setupTargets.ik_hand_r_target.x),
        y: round4(hr.y - setupTargets.ik_hand_r_target.y),
      });

      rootWorldSamples.push({
        time: localT,
        abs_t: round4(absT),
        x: round4(rx),
        y: round4(ry),
        facing,
        phase_name: ev.phaseName,
        posture_state: ev.postureState,
      });
    }

    const animName = `mp_${track.shot_id}_${track.actor_id}`;
    compiledTracks[`${track.shot_id}:${track.actor_id}`] = {
      animation_name: animName,
      shot_id: track.shot_id,
      actor_id: track.actor_id,
      start_sec: startSec,
      end_sec: endSec,
      duration_sec: round4(dur),
      height_norm: heightNorm,
      rig_height_units: rigHeight,
      root_samples: rootWorldSamples,
      spine_animation: {
        bones: {
          pelvis: { translate: pelvisTranslate },
          torso: { rotate: torsoRotate },
          head: { rotate: headRotate },
          cloak: { rotate: cloakRotate },
          ik_foot_l_target: { translate: footLTranslate },
          ik_foot_r_target: { translate: footRTranslate },
          ik_hand_l_target: { translate: handLTranslate },
          ik_hand_r_target: { translate: handRTranslate },
        },
        ik: {
          ik_leg_l: [{ time: 0, mix: 1.0, bendPositive: false }],
          ik_leg_r: [{ time: 0, mix: 1.0, bendPositive: false }],
          ik_arm_l: [{ time: 0, mix: 1.0, bendPositive: true }],
          ik_arm_r: [{ time: 0, mix: 1.0, bendPositive: true }],
        },
      },
    };
  }

  return {
    schema_version: '14.7.6',
    rig_character_id: characterRigManifest?.character_id || 'roman_harbor_worker',
    track_count: Object.keys(compiledTracks).length,
    tracks: compiledTracks,
  };
}

export const convert_motion_plan_to_rigby_tracks = convertMotionPlanToRigbyTracks;

/**
 * Browser helper: preload skeleton JSON, atlas text, page PNG, and initialize offscreen WebGLRenderer.
 */
export async function loadBrowserRigbyAsset({
  skeletonUrl = '/integrations/rigby2d/assets/roman_harbor_worker.json',
  atlasUrl = '/integrations/rigby2d/assets/roman_harbor_worker.atlas',
  textureUrl = '/integrations/rigby2d/assets/roman_harbor_worker.png',
  manifestUrl = '/integrations/rigby2d/assets/roman_harbor_worker_manifest.json',
  extraAnimations = {},
  offscreenWidth = 384,
  offscreenHeight = 448,
} = {}) {
  if (typeof document === 'undefined') {
    throw new Error('loadBrowserRigbyAsset requires a browser DOM/WebGL environment');
  }
  const [skelRes, atlasRes, manifestRes] = await Promise.all([
    fetch(skeletonUrl),
    fetch(atlasUrl),
    fetch(manifestUrl),
  ]);
  if (!skelRes.ok || !atlasRes.ok) {
    throw new Error(`RIGBY_PILOT_BLOCKED: failed fetching Rigby assets (${skelRes.status}/${atlasRes.status})`);
  }
  const skeletonJson = await skelRes.json();
  const atlasText = await atlasRes.text();
  const manifest = manifestRes.ok ? await manifestRes.json() : {};

  if (extraAnimations && Object.keys(extraAnimations).length > 0) {
    skeletonJson.animations = { ...(skeletonJson.animations || {}), ...extraAnimations };
  }

  const pageImage = await new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => (im.decode ? im.decode().catch(() => {}) : Promise.resolve()).then(() => resolve(im));
    im.onerror = () => reject(new Error(`RIGBY_PILOT_BLOCKED: failed loading atlas texture ${textureUrl}`));
    im.src = textureUrl;
  });

  const glCanvas = document.createElement('canvas');
  glCanvas.width = offscreenWidth;
  glCanvas.height = offscreenHeight;
  const gl =
    glCanvas.getContext('webgl2', { alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true, antialias: true }) ||
    glCanvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true, antialias: true });
  if (!gl) {
    throw new Error('RIGBY_PILOT_BLOCKED: WebGL context unavailable in Chromium page');
  }

  const { skeleton, warnings } = readSkeletonJson(skeletonJson, manifest?.character_id || 'roman_harbor_worker');
  const atlas = parseAtlas(atlasText);
  const renderer = new WebGLRenderer(gl);
  const pageName = atlas.pages[0]?.name || 'roman_harbor_worker.png';
  const lookup = renderer.atlasTextures(atlas, { [pageName]: pageImage });
  const pose = new Pose(skeleton);

  return {
    backend: 'rigby2d_webgl_0.5.1',
    skeleton,
    skeletonJson,
    atlas,
    manifest,
    warnings,
    glCanvas,
    gl,
    renderer,
    lookup,
    pose,
    animationsByName: new Map(skeleton.animations.map((a) => [a.name, a])),
  };
}

/**
 * Statelessly pose & render a Rigby2D skeletal actor at `absoluteT` via WebGLRenderer
 * and composite onto FL-01's 2D Canvas `ctx` at `worldRoot`.
 */
export function renderRigbyActorToCanvas(ctx, absoluteT, worldRoot, rigAsset, options = {}) {
  if (!ctx || !rigAsset || !rigAsset.renderer || !rigAsset.skeleton) {
    throw new Error('renderRigbyActorToCanvas: missing 2D ctx or initialized rigAsset');
  }
  const { skeleton, pose, renderer, gl, glCanvas, lookup, animationsByName } = rigAsset;
  const animName = options.animationName || 'idle';
  const anim = animationsByName.get(animName) || skeleton.animations[0] || null;
  const animStartSec = Number(options.animStartSec || 0);
  const loop = Boolean(options.loop);
  let localT = Math.max(0, Number(absoluteT || 0) - animStartSec);
  if (loop && anim && anim.duration > 0) {
    localT = localT % anim.duration;
  }

  // Stateless pure evaluation of Pose at localT
  pose.reset(skeleton);
  if (typeof pose.resetPhysics === 'function') {
    pose.resetPhysics();
  }
  if (anim) {
    pose.apply(skeleton, anim, localT, 1.0);
  }
  if (options.slotAttachments && typeof options.slotAttachments === 'object') {
    for (let si = 0; si < skeleton.slots.length; si++) {
      const sName = skeleton.slots[si]?.name;
      if (sName && Object.prototype.hasOwnProperty.call(options.slotAttachments, sName)) {
        pose.attachment[si] = options.slotAttachments[sName];
      }
    }
  }
  pose.updateWorld(skeleton);

  const cw = glCanvas.width;
  const ch = glCanvas.height;
  const camY = Number(options.rigCameraCenterY ?? 105);
  const camZoom = Number(options.rigCameraZoom ?? 1.35);

  gl.viewport(0, 0, cw, ch);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);

  renderer.begin(cw, ch, { x: 0, y: camY, zoom: camZoom });
  renderer.drawSkeleton(skeleton, pose, lookup, { tint: options.tint || [1, 1, 1, 1] });
  renderer.end();
  gl.flush();

  // In WebGL buffer, world (0, 0) [actor feet] maps to pixel:
  // clip_y = (0 - camY) * (2 * camZoom / ch) => canvas_y_from_top = ch * 0.5 + camY * camZoom
  const anchorPxX = cw * 0.5;
  const anchorPxY = ch * 0.5 + camY * camZoom;

  const targetHeightPx = Number(options.actorHeight || worldRoot?.actorHeight || 170);
  const rigUnitsHeight = Number(rigAsset.manifest?.height_units || 210);
  const drawScale = targetHeightPx / (rigUnitsHeight * camZoom);
  const facing = (worldRoot?.facing ?? 1) >= 0 ? 1 : -1;
  const rx = Number(worldRoot?.x ?? 0);
  const ry = Number(worldRoot?.y ?? 0);

  ctx.save();
  ctx.translate(rx, ry);
  ctx.scale(facing * drawScale, drawScale);
  ctx.drawImage(glCanvas, -anchorPxX, -anchorPxY);
  ctx.restore();

  return {
    backend: rigAsset.backend,
    animation: anim ? anim.name : null,
    local_t: round4(localT),
    draw_calls: renderer.drawCalls,
    world_root: { x: round4(rx), y: round4(ry), facing },
  };
}

export const render_rigby_actor_to_canvas = renderRigbyActorToCanvas;
