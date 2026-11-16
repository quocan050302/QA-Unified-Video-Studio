// packs/squire/modern2d/style_renderer.js — Universal Modern Expressive 2D Renderer (KH-01)
//
// Data-driven HTML5 Canvas 2D + optional Rigby2D WebGL skeletal compositor governed by
// `visual_styles/modern_expressive_2d/v1/style_bible.json`, `CharacterSpec`, `EnvironmentSpec`,
// `MotionPlan`, `CameraSegment`, and separated Claude FX clocks.
//
// Pure deterministic stateless function of `(shot, lt, globalT)`:
// - ZERO Math.random(), ZERO mutable frame-to-frame state, 100% arbitrary-frame order invariant.
// - ZERO story-specific JS modules required per niche: drives Roman Forum, Modern Science Lab,
//   Everyday Business Cafe, Planetarium Holdout, Acting Showcase, Multi-Angle, and the 30s film
//   "ROME'S MOST URGENT SCROLL" from project JSON specs alone.

import { E, clamp, lerp, ease, registerTemplate, registerShot, talkAmount, alpha, text, FONTS } from '/engine/core.js';
import { soldier } from '/packs/squire/chara.js';
import {
  evaluateMotionTrackAt,
  evaluateMultiActorInteraction,
} from '/packs/squire/motion_engine.js';
import {
  createSeparatedActionClock,
  burstParticles,
  landDust,
  ring as fxRing,
} from '/integrations/claude_motion/adapter.js';
import {
  loadBrowserRigbyAsset,
  convertMotionPlanToRigbyTracks,
  renderRigbyActorToCanvas,
} from '/integrations/rigby2d/adapter.js';

const smooth01 = (x) => {
  const u = clamp(x, 0, 1);
  return u * u * (3 - 2 * u);
};

const _projectCache = {
  projUrl: null,
  charBible: null,
  envSpec: null,
  styleProfile: null,
  rigAssetsByActor: new Map(),
};

async function fetchJsonSafe(url, fallback = null) {
  try {
    const r = await fetch(url);
    if (!r.ok) return fallback;
    return await r.json();
  } catch {
    return fallback;
  }
}

export async function initModernExpressive2D(engineState = E) {
  const q = typeof location !== 'undefined' ? new URLSearchParams(location.search) : null;
  const projBase = (q && q.get('proj')) || '/proj';
  if (_projectCache.projUrl === projBase && _projectCache.charBible) {
    return _projectCache;
  }
  _projectCache.projUrl = projBase;
  _projectCache.charBible = await fetchJsonSafe(`${projBase}/story/character_bible.json`, { characters: {} });
  _projectCache.envSpec = await fetchJsonSafe(`${projBase}/story/environment_spec.json`, null);
  _projectCache.styleProfile = await fetchJsonSafe(`${projBase}/story/style_profile.json`, null);
  _projectCache.rigAssetsByActor.clear();

  // Preload any Rigby2D character rigs declared in shots or character_bible
  const shots = engineState?.shots || [];
  const wantsRigby = shots.some((s) => {
    const b = String(s?.args?.actorBackend || '');
    return b === 'rigby2d' || b === 'rigby2d_modern';
  });
  if (wantsRigby && typeof document !== 'undefined') {
    const motionPlan = await fetchJsonSafe(`${projBase}/story/motion_plan.json`, null);
    const rigConfigs = _projectCache.charBible?.rig_manifests || {};
    for (const [actorId, rm] of Object.entries(rigConfigs)) {
      try {
        const extraAnims = {};
        if (motionPlan && Array.isArray(motionPlan.tracks)) {
          const actorMp = { ...motionPlan, tracks: motionPlan.tracks.filter((t) => t.actor_id === actorId) };
          if (actorMp.tracks.length > 0) {
            const compiled = convertMotionPlanToRigbyTracks(actorMp, rm);
            for (const info of Object.values(compiled.tracks || {})) {
              extraAnims[info.animation_name] = info.spine_animation;
            }
          }
        }
        const skUrl = '/' + String(rm.files.skeleton_json.path).replace(/^\/+/, '');
        const atUrl = '/' + String(rm.files.atlas.path).replace(/^\/+/, '');
        const txUrl = '/' + String(rm.files.texture_png.path).replace(/^\/+/, '');
        const mfUrl = rm.manifest_path ? '/' + String(rm.manifest_path).replace(/^\/+/, '') : skUrl;
        const loaded = await loadBrowserRigbyAsset({
          skeletonUrl: skUrl,
          atlasUrl: atUrl,
          textureUrl: txUrl,
          manifestUrl: mfUrl,
          extraAnimations: extraAnims,
          offscreenWidth: 448,
          offscreenHeight: 512,
        });
        _projectCache.rigAssetsByActor.set(actorId, loaded);
      } catch (err) {
        console.warn('[modern2d] Rigby preload fallback for', actorId, err?.message || err);
      }
    }
  }
  return _projectCache;
}

// ---------- Variable-Weight Calligraphic Ink & Cel-Shading Primitives ----------

function drawVariableStroke(g, pts, color, maxLw, taperEnds = true) {
  if (!pts || pts.length < 2) return;
  g.save();
  g.strokeStyle = color;
  g.lineCap = 'round';
  g.lineJoin = 'round';
  if (!taperEnds || pts.length === 2) {
    g.beginPath();
    g.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
    g.lineWidth = maxLw;
    g.stroke();
    g.restore();
    return;
  }
  const n = pts.length - 1;
  for (let i = 0; i < n; i++) {
    const u = (i + 0.5) / n;
    const w = Math.max(1.1, maxLw * (0.38 + 0.62 * Math.sin(Math.PI * u)));
    g.beginPath();
    g.moveTo(pts[i][0], pts[i][1]);
    g.lineTo(pts[i + 1][0], pts[i + 1][1]);
    g.lineWidth = w;
    g.stroke();
  }
  g.restore();
}

function fillCelPolygon(g, pts, baseHex, shadowHex, rimHex, outerInkHex, lwOuter, lightSide = -1) {
  if (!pts || pts.length < 3) return;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const [px, py] of pts) {
    if (px < minX) minX = px;
    if (px > maxX) maxX = px;
    if (py < minY) minY = py;
    if (py > maxY) maxY = py;
  }
  const spanW = Math.max(1, maxX - minX);
  const spanH = Math.max(1, maxY - minY);

  g.save();
  g.beginPath();
  g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.closePath();
  g.fillStyle = baseHex;
  g.fill();

  // Clip interior for hard-edged cel shadow band & key-light rim highlight
  g.save();
  g.clip();
  if (shadowHex) {
    g.fillStyle = shadowHex;
    const shX = lightSide < 0 ? minX + spanW * 0.56 : minX - spanW * 0.1;
    g.fillRect(shX, minY - 4, spanW * 0.58, spanH + 8);
  }
  if (rimHex) {
    g.fillStyle = rimHex;
    const rimX = lightSide < 0 ? minX : maxX - Math.max(3, spanW * 0.12);
    g.fillRect(rimX, minY - 2, Math.max(3, spanW * 0.12), spanH + 4);
  }
  g.restore();

  if (lwOuter > 0) {
    g.lineWidth = lwOuter;
    g.strokeStyle = outerInkHex;
    g.lineJoin = 'round';
    g.lineCap = 'round';
    g.stroke();
  }
  g.restore();
}

// ---------- Active Camera Segment Evaluator ----------

function resolveActiveCameraSegment(shot, lt) {
  const dur = Math.max(0.1, Number(shot?.dur || 3.0));
  const segs = shot?.args?.cameraSegments;
  if (!Array.isArray(segs) || segs.length === 0) {
    return {
      segment_id: 'seg_01',
      scale: shot?.art_direction?.camera_scale || shot?.camera?.scale || 'medium',
      viewpoint: shot?.camera?.viewpoint || 'front_three_quarter_left',
      projection_mode: 'continuous_2d_canvas',
      panX: 0.5,
      panY: 0.54,
      zoom: 1.02,
      localU: smooth01(lt / dur),
    };
  }
  let seg = segs[segs.length - 1];
  for (let i = 0; i < segs.length; i++) {
    const s0 = Number(segs[i].local_start ?? 0);
    const s1 = Number(segs[i].local_end ?? dur);
    if (i === segs.length - 1 || (lt >= s0 - 1e-6 && lt < s1 - 1e-6)) {
      seg = segs[i];
      break;
    }
  }
  const s0 = Number(seg.local_start ?? 0);
  const s1 = Math.max(s0 + 0.04, Number(seg.local_end ?? dur));
  const u = smooth01((lt - s0) / (s1 - s0));
  const cf = Array.isArray(seg.center_from) ? seg.center_from : [0.5, 0.54];
  const ct = Array.isArray(seg.center_to) ? seg.center_to : cf;
  return {
    ...seg,
    panX: lerp(Number(cf[0] ?? 0.5), Number(ct[0] ?? 0.5), u),
    panY: lerp(Number(cf[1] ?? 0.54), Number(ct[1] ?? 0.54), u),
    zoom: clamp(lerp(Number(seg.zoom_from ?? 1.0), Number(seg.zoom_to ?? 1.04), u), 1.0, 2.45),
    localU: u,
  };
}

// ---------- Multi-Plane Niche Environment Stage ----------

export function drawModernEnvironmentStage(g, envSpec, globalT, camSeg, mech = {}) {
  const W = E.W;
  const H = E.H;
  const spec = envSpec || _projectCache.envSpec || {};
  const niche = String(spec.niche || 'roman_forum');
  const rawPal = spec.palette || {
    sky: ['#4A88C7', '#8EC5E8', '#F4DEC0'],
    ground: ['#C9B193', '#B09678', '#8B735B'],
    architecture: ['#E8D5B7', '#D4B894', '#B9583B', '#5A7D58'],
    accents: ['#C83E2B', '#E29B27', '#2B6E78', '#F7EFE2'],
    key_light_hex: '#FFF0CE',
    shadow_tint_hex: '#3B2D38',
    mid_ink_hex: '#1F1613',
    far_ink_hex: '#46505C',
  };
  const pal = { ...rawPal, mid_ink_hex: '#1F1613' };
  const groundY = H * Number(spec.ground_y_norm ?? 0.84);
  const vpX = W * Number(spec.vanishing_point?.[0] ?? 0.52);
  const vpY = H * Number(spec.vanishing_point?.[1] ?? 0.56);
  const isClose = ['close', 'extreme_close', 'detail', 'macro'].includes(String(camSeg?.scale || ''));
  const wind = Number(mech.wind_strength ?? 0.45);
  const lw = 3.8;

  // Plane 0: Sky / Upper Atmosphere
  const skyGrad = g.createLinearGradient(0, 0, 0, groundY);
  skyGrad.addColorStop(0, pal.sky[0]);
  skyGrad.addColorStop(0.55, pal.sky[Math.min(1, pal.sky.length - 1)]);
  skyGrad.addColorStop(1, pal.sky[pal.sky.length - 1]);
  g.fillStyle = skyGrad;
  g.fillRect(0, 0, W, H);

  if (niche.includes('roman')) {
    // Drifting sculptural clouds
    const drift = (globalT * (14 + wind * 22)) % (W + 400);
    g.save();
    g.fillStyle = 'rgba(255, 250, 242, 0.86)';
    for (const [bx, by, rx, ry] of [[340, 155, 165, 42], [1180, 128, 210, 48], [1760, 175, 145, 36]]) {
      const cx = ((bx - drift) + W + 400) % (W + 400) - 200;
      g.beginPath();
      g.ellipse(cx, by, rx, ry, 0, 0, Math.PI * 2);
      g.ellipse(cx + rx * 0.35, by - ry * 0.45, rx * 0.62, ry * 0.78, 0, 0, Math.PI * 2);
      g.fill();
    }
    g.restore();

    // Distant Roman Basilica pediment & cypress silhouettes
    fillCelPolygon(
      g,
      [[W * 0.03, groundY], [W * 0.03, H * 0.33], [W * 0.17, H * 0.24], [W * 0.31, H * 0.33], [W * 0.31, groundY]],
      pal.architecture[1],
      null,
      '#F8EBD4',
      pal.far_ink_hex,
      2.6,
    );
    for (const cyX of [0.34, 0.375, 0.895, 0.93]) {
      g.save();
      g.beginPath();
      g.ellipse(W * cyX, H * 0.42, W * 0.013, H * 0.16, Math.sin(globalT * 2.1 + cyX * 10) * 0.02 * wind, 0, Math.PI * 2);
      g.fillStyle = pal.architecture[3] || '#5A7D58';
      g.fill();
      g.lineWidth = 2.4;
      g.strokeStyle = pal.far_ink_hex;
      g.stroke();
      g.restore();
    }

    // Travertine colonnade wall + terracotta tiled frieze
    const colTop = H * 0.37;
    g.fillStyle = pal.architecture[0];
    g.fillRect(0, colTop, W, groundY - colTop);
    drawVariableStroke(g, [[0, colTop], [W, colTop]], pal.mid_ink_hex, lw, false);

    fillCelPolygon(
      g,
      [[0, colTop - H * 0.052], [W, colTop - H * 0.052], [W, colTop], [0, colTop]],
      pal.architecture[2],
      '#923F27',
      '#DF7A58',
      pal.mid_ink_hex,
      lw,
    );
    for (let tx = 20; tx < W; tx += 52) {
      drawVariableStroke(g, [[tx, colTop - H * 0.05], [tx - 12, colTop - 2]], pal.mid_ink_hex, 2.2, false);
    }

    // Arched market stalls & fluted pilasters
    const archAlpha = isClose ? 0.45 : 1.0;
    g.save();
    g.globalAlpha = archAlpha;
    for (let ai = 0; ai < 7; ai++) {
      const ax = W * (0.055 + ai * 0.132);
      const aw = W * 0.082;
      const ay = H * 0.45;
      g.beginPath();
      g.roundRect(ax, ay, aw, groundY - ay, [aw * 0.5, aw * 0.5, 0, 0]);
      g.fillStyle = '#B89B7A';
      g.fill();
      g.lineWidth = lw;
      g.strokeStyle = pal.mid_ink_hex;
      g.stroke();

      // Fluted pilaster column
      const colX = ax - W * 0.025;
      if (colX > 8) {
        fillCelPolygon(
          g,
          [[colX, colTop + 8], [colX + W * 0.017, colTop + 8], [colX + W * 0.017, groundY], [colX, groundY]],
          '#F5EAD6',
          '#D4C2A6',
          '#FFFDF7',
          pal.mid_ink_hex,
          2.5,
        );
      }
    }

    // Subtle background forum crowd silhouettes on wide chase shots
    if (mech.show_crowd_silhouettes && !isClose) {
      g.fillStyle = 'rgba(92, 74, 62, 0.42)';
      for (let ci = 0; ci < 6; ci++) {
        const cxP = W * (0.18 + ci * 0.12) + Math.sin(globalT * 1.6 + ci) * 6;
        const cyP = groundY - 4;
        g.beginPath();
        g.ellipse(cxP, cyP - 54, 22, 52, 0, 0, Math.PI * 2);
        g.arc(cxP, cyP - 118, 16, 0, Math.PI * 2);
        g.fill();
      }
    }

    // Animated Striped Linen Market Awnings (reacting with spring & wind inertia!)
    const awningWave = Math.sin(globalT * (4.2 + wind * 2.5)) * (8 + wind * 14) + (mech.awning_impulse ? Math.sin(globalT * 11.0) * 14 : 0);
    for (const [stX, cA, cB] of [[W * 0.08, pal.accents[0], pal.accents[3]], [W * 0.36, pal.accents[2], pal.accents[1]]]) {
      const awW = W * 0.24;
      const yTop = H * 0.38;
      const yBot = H * 0.495 + awningWave * 0.45;
      const stripes = 6;
      for (let si = 0; si < stripes; si++) {
        const sx0 = stX + (si / stripes) * awW;
        const sx1 = stX + ((si + 1) / stripes) * awW;
        const localFlutter = Math.sin(globalT * 6.4 + si * 0.9) * (3 + wind * 6);
        fillCelPolygon(
          g,
          [
            [sx0, yTop],
            [sx1, yTop],
            [sx1 + 18 + awningWave * 0.4, yBot + localFlutter],
            [sx0 + 18 + awningWave * 0.4, yBot + localFlutter],
          ],
          si % 2 === 0 ? cA : cB,
          null,
          null,
          pal.mid_ink_hex,
          2.6,
        );
      }
    }

    // Carved Forum Limestone Fountain + Live Sparkling Water Arcs
    if (mech.show_fountain !== false) {
      const fxC = W * Number(mech.fountain_x ?? 0.78);
      fillCelPolygon(
        g,
        [[fxC - 165, groundY - 96], [fxC + 165, groundY - 96], [fxC + 152, groundY + 6], [fxC - 152, groundY + 6]],
        '#DFD3BE',
        '#BDB09A',
        '#FBF5E8',
        pal.mid_ink_hex,
        lw,
      );
      g.beginPath();
      g.ellipse(fxC, groundY - 96, 148, 22, 0, 0, Math.PI * 2);
      g.fillStyle = '#5BB6DA';
      g.fill();
      g.lineWidth = lw;
      g.strokeStyle = pal.mid_ink_hex;
      g.stroke();

      // Pedestal & upper bowl
      fillCelPolygon(
        g,
        [[fxC - 32, groundY - 236], [fxC + 32, groundY - 236], [fxC + 38, groundY - 96], [fxC - 38, groundY - 96]],
        '#EAE0CE',
        '#C5B8A2',
        '#FFFDF8',
        pal.mid_ink_hex,
        lw,
      );
      g.beginPath();
      g.ellipse(fxC, groundY - 238, 86, 20, 0, 0, Math.PI * 2);
      g.fillStyle = '#EAE0CE';
      g.fill();
      g.stroke();

      // Animated water arcs & ripples
      g.save();
      g.strokeStyle = 'rgba(218, 248, 255, 0.88)';
      g.lineWidth = 4.0;
      for (const sgn of [-1, 1]) {
        const dropShift = Math.sin(globalT * 7.5 + sgn) * 5;
        g.beginPath();
        g.moveTo(fxC + sgn * 18, groundY - 252);
        g.quadraticCurveTo(fxC + sgn * (92 + dropShift), groundY - 248, fxC + sgn * 105, groundY - 102);
        g.stroke();
      }
      const rippleR = 28 + ((globalT * 48) % 85);
      g.strokeStyle = `rgba(255, 255, 255, ${(1 - rippleR / 115) * 0.65})`;
      g.lineWidth = 2.2;
      g.beginPath();
      g.ellipse(fxC, groundY - 96, rippleR, rippleR * 0.16, 0, 0, Math.PI * 2);
      g.stroke();
      g.restore();
    }
    g.restore();
  } else if (niche === 'modern_science') {
    // Cleanroom wall panels, observation window & live spectrometer trace
    g.fillStyle = pal.architecture[0];
    g.fillRect(0, H * 0.16, W, groundY - H * 0.16);
    for (let px = 120; px < W; px += 220) {
      drawVariableStroke(g, [[px, H * 0.16], [px, groundY]], pal.architecture[1], 3.0, false);
    }
    g.save();
    g.beginPath();
    g.roundRect(W * 0.22, H * 0.24, W * 0.56, H * 0.34, 16);
    g.fillStyle = '#1E3448';
    g.fill();
    g.lineWidth = lw + 1;
    g.strokeStyle = pal.mid_ink_hex;
    g.stroke();
    // LED status bar
    drawVariableStroke(g, [[W * 0.08, H * 0.20], [W * 0.92, H * 0.20]], pal.accents[0], 7.0, false);
    // Live animated waveform on spectrometer rack
    g.beginPath();
    g.roundRect(W * 0.07, H * 0.34, W * 0.12, groundY - H * 0.34, 10);
    g.fillStyle = pal.architecture[2];
    g.fill();
    g.stroke();
    g.beginPath();
    for (let wx = 0; wx <= 140; wx += 6) {
      const wy = H * 0.44 + Math.sin(globalT * 6.5 + wx * 0.09) * 18 * Math.sin((wx / 140) * Math.PI);
      if (wx === 0) g.moveTo(W * 0.085 + wx, wy);
      else g.lineTo(W * 0.085 + wx, wy);
    }
    g.strokeStyle = pal.accents[0];
    g.lineWidth = 3.2;
    g.stroke();
    // Optical isolation bench
    fillCelPolygon(
      g,
      [[W * 0.33, H * 0.70], [W * 0.67, H * 0.70], [W * 0.67, H * 0.75], [W * 0.33, H * 0.75]],
      '#D7E1EA',
      '#AEBECB',
      '#FFFFFF',
      pal.mid_ink_hex,
      lw,
    );
    g.fillStyle = '#7A8C9B';
    g.fillRect(W * 0.36, H * 0.75, 28, groundY - H * 0.75);
    g.fillRect(W * 0.61, H * 0.75, 28, groundY - H * 0.75);
    g.restore();
  } else if (niche === 'holdout_astronomy_museum') {
    // Ribbed twilight planetarium dome + shimmering solar eclipse projection
    g.save();
    g.strokeStyle = pal.architecture[1];
    g.lineWidth = 3.2;
    for (const rScale of [0.68, 0.52, 0.36]) {
      g.beginPath();
      g.ellipse(W * 0.5, H * 0.66, W * rScale, H * rScale * 0.88, 0, Math.PI, Math.PI * 2);
      g.stroke();
    }
    const exC = W * 0.54;
    const eyC = H * 0.29;
    const coronaR = 96 + Math.sin(globalT * 2.8) * 6;
    const corGrad = g.createRadialGradient(exC, eyC, 54, exC, eyC, coronaR * 1.45);
    corGrad.addColorStop(0, 'rgba(255, 218, 122, 0.88)');
    corGrad.addColorStop(0.5, 'rgba(224, 159, 62, 0.34)');
    corGrad.addColorStop(1, 'rgba(24, 34, 56, 0)');
    g.fillStyle = corGrad;
    g.fillRect(exC - 180, eyC - 180, 360, 360);
    g.beginPath();
    g.arc(exC, eyC, 62, 0, Math.PI * 2);
    g.fillStyle = '#141B2E';
    g.fill();
    g.lineWidth = 4.0;
    g.strokeStyle = '#FFE29A';
    g.stroke();

    // Brass refractor telescope on wooden tripod
    const txC = W * 0.53;
    drawVariableStroke(g, [[txC, H * 0.66], [txC - 68, groundY]], '#5C4028', 9.0, false);
    drawVariableStroke(g, [[txC, H * 0.66], [txC + 68, groundY]], '#5C4028', 9.0, false);
    fillCelPolygon(
      g,
      [[txC - 92, H * 0.69], [txC + 108, H * 0.56], [txC + 122, H * 0.595], [txC - 78, H * 0.725]],
      '#D4A244',
      '#9B7024',
      '#FFF0B8',
      pal.mid_ink_hex,
      lw,
    );
    g.restore();
  } else {
    // everyday_business: Cozy Morning Corner Cafe
    g.fillStyle = pal.architecture[0];
    g.fillRect(0, H * 0.14, W, groundY - H * 0.14);
    g.fillStyle = pal.architecture[2];
    g.fillRect(0, H * 0.54, W, groundY - H * 0.54);
    drawVariableStroke(g, [[0, H * 0.54], [W, H * 0.54]], pal.mid_ink_hex, lw, false);

    // Chalkboard menu & sunlit window
    g.save();
    g.beginPath();
    g.roundRect(W * 0.09, H * 0.22, W * 0.22, H * 0.25, 10);
    g.fillStyle = '#262F30';
    g.fill();
    g.lineWidth = 6;
    g.strokeStyle = '#8C5A3C';
    g.stroke();
    text(g, 'TODAY: ESPRESSO & PASTRY', W * 0.20, H * 0.29, { size: 22, font: FONTS.body, weight: 700, color: '#F6EBD8' });

    g.beginPath();
    g.roundRect(W * 0.63, H * 0.20, W * 0.26, H * 0.31, 12);
    g.fillStyle = '#BEE4F7';
    g.fill();
    g.lineWidth = 5;
    g.strokeStyle = pal.mid_ink_hex;
    g.stroke();

    // Gently swaying pendant lamps
    for (const lx of [W * 0.39, W * 0.53]) {
      const sway = Math.sin(globalT * 1.9 + lx * 0.01) * 4;
      drawVariableStroke(g, [[lx, 0], [lx + sway, H * 0.22]], pal.mid_ink_hex, 3.5, false);
      g.beginPath();
      g.arc(lx + sway, H * 0.24, 34, Math.PI, Math.PI * 2);
      g.fillStyle = pal.accents[2];
      g.fill();
      g.stroke();
    }
    // Oak espresso counter + steaming brass machine
    fillCelPolygon(
      g,
      [[W * 0.27, H * 0.67], [W * 0.64, H * 0.67], [W * 0.64, groundY], [W * 0.27, groundY]],
      '#9C6B49',
      '#754C30',
      '#C4906A',
      pal.mid_ink_hex,
      lw,
    );
    fillCelPolygon(
      g,
      [[W * 0.32, H * 0.55], [W * 0.42, H * 0.55], [W * 0.42, H * 0.67], [W * 0.32, H * 0.67]],
      '#D99B38',
      '#A6701E',
      '#FFE29A',
      pal.mid_ink_hex,
      lw,
    );
    g.restore();
  }

  // Plane 2: Perspective Ground Floor Plane with Converging Lines
  g.fillStyle = pal.ground[0];
  g.fillRect(0, groundY, W, H - groundY);
  g.fillStyle = pal.ground[2];
  g.fillRect(0, groundY, W, 10);
  drawVariableStroke(g, [[0, groundY], [W, groundY]], pal.mid_ink_hex, lw + 0.6, false);

  g.save();
  g.strokeStyle = alpha(pal.ground[2], 0.55);
  g.lineWidth = 2.2;
  for (let ri = -8; ri <= 8; ri++) {
    const bx = W * 0.5 + ri * W * 0.115;
    const ix = vpX + (bx - vpX) * ((groundY - vpY) / Math.max(1, H - vpY));
    g.beginPath();
    g.moveTo(ix, groundY);
    g.lineTo(bx, H);
    g.stroke();
  }
  for (const ru of [0.22, 0.48, 0.78]) {
    const ry = groundY + (H - groundY) * ru;
    g.beginPath();
    g.moveTo(0, ry);
    g.lineTo(W, ry);
    g.stroke();
  }
  g.restore();
}

export function drawForegroundOccluders(g, envSpec, camSeg) {
  const isClose = ['close', 'extreme_close', 'detail', 'macro'].includes(String(camSeg?.scale || ''));
  if (isClose) return;
  const W = E.W;
  const H = E.H;
  const pal = (envSpec || _projectCache.envSpec || {}).palette || { shadow_tint_hex: '#2E2228', mid_ink_hex: '#1F1716' };
  g.save();
  // Left foreground silhouette amphora/planter + right subtle frame column
  g.fillStyle = alpha(pal.shadow_tint_hex || '#2E2228', 0.84);
  g.strokeStyle = pal.mid_ink_hex || '#1F1716';
  g.lineWidth = 3.5;
  g.beginPath();
  g.ellipse(W * 0.02, H * 0.90, W * 0.065, H * 0.15, 0.08, 0, Math.PI * 2);
  g.fill();
  g.stroke();
  g.fillRect(W * 0.968, 0, W * 0.032, H);
  g.restore();
}

// ---------- Rich Dynamic Props ----------

export function drawModernProp(g, kind, x, y, scale = 1.0, opts = {}) {
  const s = scale;
  const rot = Number(opts.rot || 0);
  const ink = '#191210';

  g.save();
  g.translate(x, y);
  g.rotate(rot);

  if (kind === 'scroll' || kind === 'wax_sealed_scroll') {
    const w = 68 * s;
    const h = 22 * s;
    // Wooden scroll end-knobs
    g.fillStyle = '#7A4928';
    g.strokeStyle = ink;
    g.lineWidth = 3.0 * s;
    for (const sx of [-w * 0.56, w * 0.56]) {
      g.beginPath();
      g.roundRect(sx - 5 * s, -h * 0.68, 10 * s, h * 1.36, 4 * s);
      g.fill();
      g.stroke();
    }
    // Rolled ivory parchment body with cel shadow & highlight
    fillCelPolygon(
      g,
      [[-w * 0.5, -h * 0.5], [w * 0.5, -h * 0.5], [w * 0.5, h * 0.5], [-w * 0.5, h * 0.5]],
      '#F7EBD2',
      '#DFCCA8',
      '#FFFDF7',
      ink,
      3.2 * s,
    );
    // Crimson ribbon + embossed wax seal
    g.fillStyle = '#C8372D';
    g.fillRect(-7 * s, -h * 0.52, 14 * s, h * 1.04);
    g.beginPath();
    g.arc(0, h * 0.12, 11 * s, 0, Math.PI * 2);
    g.fillStyle = '#B82923';
    g.fill();
    g.lineWidth = 2.6 * s;
    g.stroke();
    // Fluttering ribbon tails
    const flutter = Math.sin(Number(opts.globalT || 0) * 12.0) * 6 * s;
    drawVariableStroke(g, [[0, h * 0.22], [-14 * s, h * 0.95 + flutter]], '#C8372D', 4.0 * s);
    drawVariableStroke(g, [[2 * s, h * 0.22], [15 * s, h * 0.88 - flutter]], '#C8372D', 4.0 * s);
  } else if (kind === 'cart' || kind === 'wooden_fruit_cart') {
    const cw = 210 * s;
    const ch = 84 * s;
    // Fruit pile inside cart (apples, golden pears, grapes)
    const fruits = [
      [-58, -ch - 8, 18, '#D63E2F'],
      [-24, -ch - 14, 20, '#E8A838'],
      [14, -ch - 12, 19, '#D63E2F'],
      [48, -ch - 8, 17, '#6D4378'],
      [-4, -ch - 24, 17, '#588B48'],
    ];
    for (const [fx, fy, fr, fc] of fruits) {
      g.beginPath();
      g.arc(fx * s, fy * s, fr * s, 0, Math.PI * 2);
      g.fillStyle = fc;
      g.fill();
      g.lineWidth = 2.8 * s;
      g.strokeStyle = ink;
      g.stroke();
    }
    // Slatted oak cart body
    fillCelPolygon(
      g,
      [[-cw * 0.5, -ch], [cw * 0.5, -ch], [cw * 0.44, -22 * s], [-cw * 0.44, -22 * s]],
      '#9E6B43',
      '#784E2D',
      '#C48E62',
      ink,
      3.8 * s,
    );
    drawVariableStroke(g, [[-cw * 0.46, -ch * 0.62], [cw * 0.46, -ch * 0.62]], ink, 3.0 * s, false);
    // Push handles on left/right
    drawVariableStroke(g, [[-cw * 0.5, -ch * 0.85], [-cw * 0.66, -ch * 0.96]], '#784E2D', 7.5 * s, false);
    // Spoked wooden wheel rotating with cart travel
    const wheelAng = Number(opts.wheelAngle || 0);
    for (const wx of [-cw * 0.28, cw * 0.28]) {
      g.save();
      g.translate(wx, -18 * s);
      g.rotate(wheelAng);
      g.beginPath();
      g.arc(0, 0, 32 * s, 0, Math.PI * 2);
      g.fillStyle = '#6E462A';
      g.fill();
      g.lineWidth = 4.2 * s;
      g.strokeStyle = ink;
      g.stroke();
      g.beginPath();
      g.arc(0, 0, 22 * s, 0, Math.PI * 2);
      g.fillStyle = '#C9B193';
      g.fill();
      g.stroke();
      for (let sp = 0; sp < 4; sp++) {
        const sa = (sp * Math.PI) / 4;
        drawVariableStroke(g, [[Math.cos(sa) * -22 * s, Math.sin(sa) * -22 * s], [Math.cos(sa) * 22 * s, Math.sin(sa) * 22 * s]], ink, 3.2 * s, false);
      }
      g.restore();
    }
  } else if (kind === 'counter' || kind === 'stone_counter') {
    fillCelPolygon(
      g,
      [[-110 * s, -86 * s], [110 * s, -86 * s], [102 * s, 0], [-102 * s, 0]],
      '#DFD1BA',
      '#BBA98E',
      '#FAF3E6',
      ink,
      3.6 * s,
    );
    fillCelPolygon(
      g,
      [[-122 * s, -104 * s], [122 * s, -104 * s], [122 * s, -84 * s], [-122 * s, -84 * s]],
      '#EAE0CE',
      '#C8B9A0',
      '#FFFFFF',
      ink,
      3.6 * s,
    );
  } else if (kind === 'beaker' || kind === 'crystal') {
    fillCelPolygon(
      g,
      [[-20 * s, -36 * s], [20 * s, -36 * s], [26 * s, 18 * s], [-26 * s, 18 * s]],
      'rgba(210, 245, 255, 0.85)',
      'rgba(140, 205, 225, 0.75)',
      '#FFFFFF',
      ink,
      3.0 * s,
    );
    fillCelPolygon(
      g,
      [[0, -24 * s], [14 * s, -4 * s], [0, 12 * s], [-14 * s, -4 * s]],
      '#00C2B8',
      '#00857E',
      '#9EFFF8',
      ink,
      2.4 * s,
    );
  } else if (kind === 'tray') {
    fillCelPolygon(
      g,
      [[-46 * s, -4 * s], [46 * s, -4 * s], [38 * s, 6 * s], [-38 * s, 6 * s]],
      '#D99B38',
      '#9E6C1E',
      '#FFE6A3',
      ink,
      3.0 * s,
    );
    for (const cxCup of [-18 * s, 18 * s]) {
      fillCelPolygon(
        g,
        [[cxCup - 11 * s, -22 * s], [cxCup + 11 * s, -22 * s], [cxCup + 9 * s, -4 * s], [cxCup - 9 * s, -4 * s]],
        '#FBF7F0',
        '#D8CFC2',
        '#FFFFFF',
        ink,
        2.6 * s,
      );
    }
  } else if (kind === 'apple' || kind === 'fruit') {
    const rA = 22 * s;
    g.beginPath();
    g.arc(0, -rA, rA, 0, Math.PI * 2);
    g.fillStyle = '#D63E2F';
    g.fill();
    g.lineWidth = 3.0 * s;
    g.strokeStyle = ink;
    g.stroke();
    g.beginPath();
    g.arc(-rA * 0.35, -rA * 1.32, rA * 0.28, 0, Math.PI * 2);
    g.fillStyle = '#FF9C8E';
    g.fill();
    drawVariableStroke(g, [[0, -rA * 1.95], [3 * s, -rA * 2.35]], '#5C3A21', 3.0 * s, false);
    fillCelPolygon(
      g,
      [[2 * s, -rA * 2.1], [14 * s, -rA * 2.38], [10 * s, -rA * 1.88]],
      '#588B48',
      null,
      null,
      ink,
      2.2 * s,
    );
  } else {
    // Generic banded parcel / ceramic vessel / rostra prop
    fillCelPolygon(
      g,
      [[-28 * s, -28 * s], [28 * s, -28 * s], [24 * s, 24 * s], [-24 * s, 24 * s]],
      '#D98245',
      '#A45826',
      '#FFBA82',
      ink,
      3.2 * s,
    );
    drawVariableStroke(g, [[-26 * s, 0], [26 * s, 0]], '#F7EFE2', 5.0 * s, false);
  }

  g.restore();
}

function solvePixelLimb2D(pStart, pEnd, len1, len2, bendDir = 1, clampEnd = false) {
  let dx = pEnd[0] - pStart[0];
  let dy = pEnd[1] - pStart[1];
  let d = Math.hypot(dx, dy);
  const maxReach = (len1 + len2) * 0.996;
  let endX = pEnd[0];
  let endY = pEnd[1];
  if (d > maxReach && d > 1e-4) {
    if (clampEnd) {
      endX = pStart[0] + (dx / d) * maxReach;
      endY = pStart[1] + (dy / d) * maxReach;
      dx = endX - pStart[0];
      dy = endY - pStart[1];
      d = maxReach;
    } else {
      const scaleUp = (d * 1.015) / (len1 + len2);
      len1 *= scaleUp;
      len2 *= scaleUp;
    }
  }
  const dSafe = Math.max(d, Math.abs(len1 - len2) + 1.0);
  const cosA = clamp((len1 * len1 + dSafe * dSafe - len2 * len2) / (2 * len1 * dSafe), -1, 1);
  const ang = Math.atan2(dy, dx) - bendDir * Math.acos(cosA);
  const midPt = [pStart[0] + Math.cos(ang) * len1, pStart[1] + Math.sin(ang) * len1];
  return [pStart, midPt, [endX, endY]];
}

export function drawModernExpressiveActor(g, actorSpec, evalState, opts = {}) {
  const W = E.W;
  const H = E.H;
  const spec = actorSpec || {};
  const wd = spec.wardrobe || {
    garment_kind: 'pleated_tunic_with_scarf_and_satchel',
    primary_hex: '#C84B31',
    primary_shadow_hex: '#93321E',
    primary_rim_hex: '#F2795E',
    secondary_hex: '#F3E5AB',
    trim_hex: '#D99B26',
    accessory_hex: '#6E4228',
    footwear: 'laced_leather_caligae',
    accessories: ['flowing_neck_scarf'],
  };
  const sk = spec.skin_palette || { base: '#E3AE88', shadow: '#BD825D', rim: '#FCE0C5', blush: '#DF7362' };
  const hr = spec.hair_palette || { base: '#3B261E', shadow: '#221410', highlight: '#6E4A3A' };
  const ink = spec.ink_outer_hex || '#191210';
  const inkIn = spec.ink_inner_hex || '#2A1F1B';

  const hPx = Number(evalState.heightNorm || 0.30) * H;
  const lwOuter = clamp(hPx * 0.013, 3.0, 8.8);
  const lwInner = lwOuter * 0.48;
  const facing = (evalState.facing ?? 1) >= 0 ? 1 : -1;
  const viewMode = String(opts.view || 'three_quarter');

  const toPx = (pt) => [pt[0] * W, pt[1] * H];
  const rootPx = toPx(evalState.root);
  const hipPx = toPx(evalState.pelvisCenter || evalState.hipWorld);
  const neckPx = toPx(evalState.neckWorld);
  const headPx = toPx(evalState.headWorld);
  const lLeg = evalState.leftLegWorld.map(toPx);
  const rLeg = evalState.rightLegWorld.map(toPx);
  const lArm = evalState.leftArmWorld.map(toPx);
  const rArm = evalState.rightArmWorld.map(toPx);

  const headRatio = Number(spec.proportions?.head_to_height_ratio ?? 0.215);
  const headR = hPx * headRatio * 0.56;
  const shWidth = headR * Number(spec.proportions?.shoulder_to_head_width ?? 1.40) * (viewMode === 'profile' ? 0.62 : 0.88);

  // 1. Ground Contact Shadow locked beneath feet
  const shadowCx = 0.5 * (lLeg[2][0] + rLeg[2][0]);
  const shadowCy = Math.max(lLeg[2][1], rLeg[2][1]);
  g.save();
  g.beginPath();
  g.ellipse(shadowCx, shadowCy + 2, shWidth * 1.15, Math.max(5, headR * 0.22), 0, 0, Math.PI * 2);
  g.fillStyle = 'rgba(25, 18, 16, 0.32)';
  g.fill();
  g.restore();

  // 2. Flowing Scarf / Coat Tail Secondary Motion Layer
  const clothLag = Number(evalState.secondary?.clothSwayNorm || 0) * W * 1.25;
  if ((wd.accessories || []).some((a) => String(a).includes('scarf')) || String(wd.garment_kind).includes('tunic')) {
    const scPts = [
      [neckPx[0] - facing * headR * 0.15, neckPx[1] + headR * 0.12],
      [neckPx[0] - facing * (shWidth * 1.25) + clothLag, neckPx[1] + headR * 0.52 - Math.abs(clothLag) * 0.2],
      [neckPx[0] - facing * (shWidth * 1.05) + clothLag * 1.15, neckPx[1] + headR * 1.15],
      [neckPx[0] - facing * headR * 0.10, neckPx[1] + headR * 0.58],
    ];
    fillCelPolygon(g, scPts, wd.secondary_hex, null, '#FFFDF6', ink, lwOuter * 0.88, -facing);
  }

  // 3. Helper for Tapered Articulated Limbs + Footwear/Hands (solved in square pixel space!)
  const standLegSpan = Math.max(hPx * 0.20, shadowCy - hipPx[1]);
  const drawLegLimb = (chain, isFar) => {
    const [Hpt, _rawKpt, Fpt] = chain;
    const [, Kpt] = solvePixelLimb2D(Hpt, Fpt, standLegSpan * 0.52, standLegSpan * 0.515, -facing, false);
    const isPants = ['modern_science', 'everyday_business', 'holdout_astronomy_museum'].includes(String(spec.niche || ''));
    const limbFill = isPants ? (isFar ? '#243847' : '#344E63') : (isFar ? sk.shadow : sk.base);
    drawVariableStroke(g, [Hpt, Kpt, Fpt], ink, headR * 0.62, false);
    drawVariableStroke(g, [Hpt, Kpt, Fpt], limbFill, headR * 0.44, false);
    // Footwear anchored cleanly on floor
    const shoePts = [
      [Fpt[0] - facing * headR * 0.26, Fpt[1] - headR * 0.22],
      [Fpt[0] + facing * headR * 0.26, Fpt[1] - headR * 0.22],
      [Fpt[0] + facing * headR * 0.54, Fpt[1]],
      [Fpt[0] - facing * headR * 0.30, Fpt[1]],
    ];
    fillCelPolygon(g, shoePts, wd.accessory_hex, null, null, ink, lwOuter * 0.85, -facing);
  };

  const drawArmLimb = (chain, isFar, handShape) => {
    const [Spt, _rawEpt, rawHnd] = chain;
    const [, Ept, Hnd] = solvePixelLimb2D(
      Spt,
      rawHnd,
      hPx * 0.165,
      hPx * 0.165,
      facing,
      handShape !== 'locked_grip',
    );
    const sleeveCol = isFar ? wd.primary_shadow_hex : wd.primary_hex;
    const armCol = isFar ? sk.shadow : sk.base;
    // Upper sleeved arm + bare/cuffed forearm
    drawVariableStroke(g, [Spt, Ept], ink, headR * 0.54, false);
    drawVariableStroke(g, [Spt, Ept], sleeveCol, headR * 0.38, false);
    drawVariableStroke(g, [Ept, Hnd], ink, headR * 0.44, false);
    drawVariableStroke(g, [Ept, Hnd], armCol, headR * 0.30, false);

    // Articulated Expressive Hand + Fingers
    const hrPx = headR * 0.22;
    g.save();
    g.beginPath();
    g.arc(Hnd[0], Hnd[1], hrPx, 0, Math.PI * 2);
    g.fillStyle = armCol;
    g.fill();
    g.lineWidth = lwOuter * 0.8;
    g.strokeStyle = ink;
    g.stroke();
    if (handShape === 'locked_grip') {
      for (let fi = -1; fi <= 1; fi++) {
        g.beginPath();
        g.roundRect(Hnd[0] - hrPx * 0.3, Hnd[1] + fi * hrPx * 0.45 - 3, facing * hrPx * 0.95, 6, 3);
        g.fillStyle = armCol;
        g.fill();
        g.lineWidth = lwInner;
        g.stroke();
      }
    } else if (handShape === 'open_reach' || handShape === 'spread_shock' || handShape === 'pointing') {
      const fCount = handShape === 'pointing' ? 1 : 3;
      for (let fi = 0; fi < fCount; fi++) {
        const ang = -0.38 + fi * 0.36;
        const fx1 = Hnd[0] + facing * Math.cos(ang) * hrPx * 1.65;
        const fy1 = Hnd[1] + Math.sin(ang) * hrPx * 1.65;
        drawVariableStroke(g, [Hnd, [fx1, fy1]], ink, hrPx * 0.54, true);
        drawVariableStroke(g, [Hnd, [fx1, fy1]], armCol, hrPx * 0.32, true);
      }
    }
    g.restore();
  };

  // Far limbs behind torso
  drawLegLimb(lLeg, true);
  drawArmLimb(lArm, true, evalState.handShapeLeft || 'relaxed');

  // 4. Layered Cel-Shaded Torso Garment
  const skirtLen = String(wd.garment_kind || '').includes('tunic') || String(wd.garment_kind || '').includes('stola') || String(wd.garment_kind || '').includes('coat')
    ? headR * 0.72
    : headR * 0.22;
  const torsoPts = [
    [neckPx[0] - shWidth * 0.72, neckPx[1] + headR * 0.14],
    [neckPx[0] + shWidth * 0.72, neckPx[1] + headR * 0.14],
    [hipPx[0] + shWidth * 0.68, hipPx[1] + skirtLen],
    [hipPx[0] - shWidth * 0.68, hipPx[1] + skirtLen],
  ];
  fillCelPolygon(g, torsoPts, wd.primary_hex, wd.primary_shadow_hex, wd.primary_rim_hex, ink, lwOuter, -facing);

  // Apron / Coat Lapels / Satchel Strap & Belt
  if (String(wd.garment_kind || '').includes('apron')) {
    const apPts = [
      [hipPx[0] - shWidth * 0.46, hipPx[1] - headR * 0.35],
      [hipPx[0] + shWidth * 0.46, hipPx[1] - headR * 0.35],
      [hipPx[0] + shWidth * 0.54, hipPx[1] + skirtLen - 4],
      [hipPx[0] - shWidth * 0.54, hipPx[1] + skirtLen - 4],
    ];
    fillCelPolygon(g, apPts, wd.trim_hex, null, null, ink, lwInner * 1.3, -facing);
  } else {
    // Satchel diagonal strap + belt + buckle
    drawVariableStroke(
      g,
      [
        [neckPx[0] - facing * shWidth * 0.45, neckPx[1] + headR * 0.18],
        [hipPx[0] + facing * shWidth * 0.48, hipPx[1] + headR * 0.12],
      ],
      wd.accessory_hex,
      lwOuter * 1.25,
      false,
    );
    fillCelPolygon(
      g,
      [
        [hipPx[0] - shWidth * 0.64, hipPx[1] - headR * 0.14],
        [hipPx[0] + shWidth * 0.64, hipPx[1] - headR * 0.14],
        [hipPx[0] + shWidth * 0.64, hipPx[1] + headR * 0.06],
        [hipPx[0] - shWidth * 0.64, hipPx[1] + headR * 0.06],
      ],
      wd.accessory_hex,
      null,
      wd.trim_hex,
      ink,
      lwInner * 1.2,
      -facing,
    );
  }
  // Interior cloth fold lines
  drawVariableStroke(
    g,
    [[neckPx[0] - shWidth * 0.18, neckPx[1] + headR * 0.52], [hipPx[0] - shWidth * 0.22, hipPx[1] + skirtLen - 8]],
    inkIn,
    lwInner,
    true,
  );

  // Near leg & near arm in front of torso
  drawLegLimb(rLeg, false);
  drawArmLimb(rArm, false, opts.handOverride || evalState.handShapeRight || 'relaxed');

  // 5. Expressive Head, Connected Neck, Cranium Cel Shading, Hair & Live Facial Performance
  const anchoredHeadY = Math.max(headPx[1], neckPx[1] - headR * 1.04);
  // Draw connected neck cylinder bridging head center down into collar/shoulders (zero floating gap!)
  drawVariableStroke(g, [[headPx[0], anchoredHeadY + headR * 0.65], [neckPx[0], neckPx[1] + headR * 0.24]], ink, headR * 0.62, false);
  drawVariableStroke(g, [[headPx[0], anchoredHeadY + headR * 0.65], [neckPx[0], neckPx[1] + headR * 0.24]], sk.shadow, headR * 0.46, false);

  g.save();
  g.translate(headPx[0], anchoredHeadY);
  g.rotate(clamp(Number(evalState.secondary?.headLagRad || 0), -0.14, 0.14));

  // Cranium with cel shadow & warm rim arc
  g.beginPath();
  g.ellipse(0, 0, headR * (viewMode === 'profile' ? 0.88 : 0.95), headR, 0, 0, Math.PI * 2);
  g.fillStyle = sk.base;
  g.fill();
  g.lineWidth = lwOuter;
  g.strokeStyle = ink;
  g.stroke();

  // Ear
  const earX = -facing * headR * (viewMode === 'profile' ? 0.24 : 0.82);
  g.beginPath();
  g.ellipse(earX, headR * 0.08, headR * 0.16, headR * 0.22, 0, 0, Math.PI * 2);
  g.fillStyle = sk.base;
  g.fill();
  g.lineWidth = lwOuter * 0.8;
  g.stroke();

  // Expressive Eyes, Brows, Nose & Lip-Synced Mouth
  const expr = opts.expressionOverride || evalState.modernExpression || 'neutral_attentive';
  const talkVal = Number(opts.talk || 0);
  const eyeCenters =
    viewMode === 'profile'
      ? [[facing * headR * 0.36, -headR * 0.06, 0.92]]
      : viewMode === 'front'
        ? [[-headR * 0.34, -headR * 0.05, 1.0], [headR * 0.34, -headR * 0.05, 1.0]]
        : [[-facing * headR * 0.12, -headR * 0.05, 1.0], [facing * headR * 0.44, -headR * 0.06, 0.78]];

  for (let ei = 0; ei < eyeCenters.length; ei++) {
    const [ex, ey, sc] = eyeCenters[ei];
    const ew = headR * 0.20 * sc;
    const eh = headR * (expr === 'wide_shock' ? 0.27 : expr === 'deadpan_disbelief' ? 0.13 : 0.20);
    if (expr === 'joyful_laugh') {
      drawVariableStroke(g, [[ex - ew, ey + headR * 0.04], [ex, ey - headR * 0.10], [ex + ew, ey + headR * 0.04]], ink, lwOuter * 1.05);
    } else {
      g.beginPath();
      g.ellipse(ex, ey, ew, eh, 0, 0, Math.PI * 2);
      g.fillStyle = '#FCFAF6';
      g.fill();
      g.lineWidth = lwOuter * 0.75;
      g.strokeStyle = ink;
      g.stroke();

      const pr = ew * (expr === 'wide_shock' ? 0.34 : 0.54);
      g.beginPath();
      g.arc(ex + facing * ew * 0.15, ey, pr, 0, Math.PI * 2);
      g.fillStyle = ink;
      g.fill();
      g.beginPath();
      g.arc(ex + facing * ew * 0.05 - pr * 0.3, ey - pr * 0.35, Math.max(1.5, pr * 0.34), 0, Math.PI * 2);
      g.fillStyle = '#FFFFFF';
      g.fill();

      if (expr === 'deadpan_disbelief') {
        g.beginPath();
        g.ellipse(ex, ey - eh * 0.35, ew * 1.02, eh * 0.55, 0, Math.PI, Math.PI * 2);
        g.fillStyle = sk.shadow;
        g.fill();
        g.stroke();
      }
    }
    // Eyebrow
    const by = ey - eh - headR * (expr === 'wide_shock' ? 0.15 : 0.08);
    const tilt = expr === 'determined_focus' || expr === 'strained_exertion' ? (ei === 0 ? headR * 0.07 : -headR * 0.07) : (expr === 'wide_shock' ? -headR * 0.08 : 0);
    drawVariableStroke(g, [[ex - ew * 1.1, by - tilt], [ex, by - Math.abs(tilt) * 0.4], [ex + ew * 1.1, by + tilt]], hr.base, lwOuter * 1.15);

    if (spec.has_glasses) {
      g.beginPath();
      g.roundRect(ex - ew * 1.35, ey - eh * 1.25, ew * 2.7, eh * 2.5, 4);
      g.lineWidth = lwInner * 1.2;
      g.strokeStyle = '#2B1E1A';
      g.stroke();
    }
  }

  // Nose
  const nx = facing * headR * (viewMode === 'profile' ? 0.88 : 0.24);
  drawVariableStroke(g, [[nx - facing * headR * 0.12, -headR * 0.08], [nx + facing * headR * 0.12, headR * 0.14], [nx - facing * headR * 0.06, headR * 0.19]], inkIn, lwInner * 1.15);

  // Mouth + Speech Viseme Modulation
  const mx = facing * headR * (viewMode === 'profile' ? 0.48 : 0.14);
  const my = headR * 0.44;
  const mw = headR * 0.28;
  if (talkVal > 0.18 || expr === 'wide_shock' || expr === 'joyful_laugh') {
    const openH = headR * (expr === 'wide_shock' ? 0.22 : expr === 'joyful_laugh' ? 0.24 : 0.08 + talkVal * 0.16);
    g.beginPath();
    g.ellipse(mx, my, mw * 0.78, openH, 0, 0, Math.PI * 2);
    g.fillStyle = '#4A181B';
    g.fill();
    g.lineWidth = lwOuter * 0.72;
    g.strokeStyle = ink;
    g.stroke();
  } else if (expr === 'strained_exertion') {
    g.beginPath();
    g.roundRect(mx - mw * 0.85, my - headR * 0.08, mw * 1.7, headR * 0.16, 4);
    g.fillStyle = '#FFFFFF';
    g.fill();
    g.lineWidth = lwOuter * 0.72;
    g.strokeStyle = ink;
    g.stroke();
  } else if (expr === 'deadpan_disbelief') {
    drawVariableStroke(g, [[mx - mw * 0.75, my], [mx + mw * 0.75, my + 1]], ink, lwOuter * 0.88);
  } else {
    drawVariableStroke(g, [[mx - mw * 0.72, my - 2], [mx, my + headR * 0.06], [mx + mw * 0.72, my - 3]], ink, lwOuter * 0.88);
  }

  // Sculpted Hair + Wind Sway Tuft / Kerchief
  const hairSway = Number(evalState.hairSwayRad || 0) * headR * 0.55;
  const hairPts = [
    [-headR * 0.96, -headR * 0.18],
    [-headR * 0.78, -headR * 1.06],
    [facing * headR * 0.22 + hairSway, -headR * 1.24],
    [headR * 0.92, -headR * 0.82],
    [headR * 0.95, -headR * 0.30],
    [headR * 0.32, -headR * 0.58],
    [-headR * 0.30, -headR * 0.52],
  ];
  fillCelPolygon(g, hairPts, hr.base, hr.shadow, hr.highlight, ink, lwOuter * 0.92, -facing);
  if (String(spec.hair_style || '').includes('kerchief')) {
    fillCelPolygon(
      g,
      [[-headR * 0.94, -headR * 0.36], [headR * 0.88, -headR * 0.54], [headR * 0.92, -headR * 0.32], [-headR * 0.90, -headR * 0.14]],
      wd.secondary_hex,
      null,
      wd.trim_hex,
      ink,
      lwInner * 1.2,
      -facing,
    );
  }
  g.restore();
}

// ---------- Authored Cinematic Macro & Close-Up Inserts ----------

function drawAuthoredModernInsert(g, insertKind, lt, dur, globalT, charSpecs, envSpec) {
  const W = E.W;
  const H = E.H;
  const u = smooth01(lt / Math.max(0.1, dur));
  const ink = '#191210';

  if (insertKind === 'macro_scroll_gust_hook') {
    // S01 HOOK: Macro stone counter + wax-sealed scroll sliding off under wind gust + Lucius wide shock eyes
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'macro' }, { wind_strength: 0.95, show_fountain: false });
    g.fillStyle = 'rgba(28, 22, 20, 0.24)';
    g.fillRect(0, 0, W, H);

    // Lucius expressive close reaction in upper-right midground before counter edge
    const luciusSpec = charSpecs.lucius || Object.values(charSpecs)[0];
    const shockGrow = smooth01((u - 0.18) / 0.35);
    drawModernExpressiveActor(
      g,
      luciusSpec,
      {
        heightNorm: 0.72,
        facing: -1,
        root: [0.74, 1.18],
        pelvisCenter: [0.74, 0.94],
        hipWorld: [0.74, 0.94],
        neckWorld: [0.73, 0.56],
        headWorld: [0.72, 0.38 - shockGrow * 0.02],
        leftLegWorld: [[0.72, 0.94], [0.72, 1.06], [0.72, 1.18]],
        rightLegWorld: [[0.76, 0.94], [0.76, 1.06], [0.76, 1.18]],
        leftArmWorld: [[0.69, 0.58], [0.63, 0.68], [0.58, 0.52]],
        rightArmWorld: [[0.77, 0.58], [0.68, 0.66], [0.54 - shockGrow * 0.08, 0.56 - shockGrow * 0.04]],
        modernExpression: u > 0.22 ? 'wide_shock' : 'neutral_attentive',
        handShapeLeft: 'spread_shock',
        handShapeRight: 'open_reach',
        hairSwayRad: -0.18 * shockGrow,
        secondary: { clothSwayNorm: 0.05 * shockGrow, headLagRad: 0.04 * shockGrow },
      },
      { view: 'three_quarter' },
    );

    // Foreground carved travertine counter slab
    fillCelPolygon(
      g,
      [[0, H * 0.68], [W * 0.58, H * 0.68], [W * 0.54, H], [0, H]],
      '#DFD1BA',
      '#B8A58A',
      '#FAF3E6',
      ink,
      6.5,
    );
    // Sliding & lifting wax-sealed urgent scroll
    const slideK = ease.in(clamp((u - 0.12) / 0.88, 0, 1));
    const scX = lerp(W * 0.30, W * 0.64, slideK);
    const scY = lerp(H * 0.63, H * 0.50, Math.pow(slideK, 1.4)) + Math.sin(globalT * 24) * (u < 0.25 ? 2.5 : 0);
    const scRot = lerp(-0.04, 0.48, slideK);
    drawModernProp(g, 'wax_sealed_scroll', scX, scY, 2.65, { rot: scRot, globalT });

    // Crisp wind gust ribbons sweeping across counter
    g.save();
    g.strokeStyle = 'rgba(255, 250, 238, 0.78)';
    g.lineWidth = 4.5;
    for (let wi = 0; wi < 4; wi++) {
      const wy = H * (0.44 + wi * 0.065);
      const wx0 = lerp(-180, W * 0.72, clamp((u * 1.35) - wi * 0.08, 0, 1));
      g.beginPath();
      g.moveTo(wx0 - 220, wy);
      g.bezierCurveTo(wx0 - 110, wy - 26, wx0 - 40, wy + 22, wx0 + 45, wy - 8);
      g.stroke();
    }
    g.restore();
    return true;
  }

  if (insertKind === 'close_hand_scroll_catch') {
    // S06 Segment 2: Genuine close hand-grip insert catching tumbling scroll beside fountain spray!
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.65, show_fountain: true, fountain_x: 0.68 });
    g.fillStyle = 'rgba(26, 38, 52, 0.22)';
    g.fillRect(0, 0, W, H);

    const gripLock = smooth01(clamp(u / 0.38, 0, 1));
    const targetX = W * 0.54;
    const targetY = H * 0.50;
    const scrollX = lerp(W * 0.62, targetX, gripLock);
    const scrollY = lerp(H * 0.42, targetY, gripLock);
    const scrollRot = lerp(0.55, 0.14, gripLock);

    // Forearm entering dynamically from bottom-left (compact anatomical close-up!)
    const wristX = lerp(W * 0.40, targetX - 36, gripLock);
    const wristY = lerp(H * 0.68, targetY + 26, gripLock);
    drawVariableStroke(g, [[W * 0.22, H * 1.02], [wristX, wristY]], ink, 98, false);
    drawVariableStroke(g, [[W * 0.22, H * 1.02], [wristX, wristY]], '#E3AE88', 82, false);
    // Terracotta sleeve cuff with gold trim at bottom-left
    drawVariableStroke(g, [[W * 0.18, H * 1.05], [W * 0.34, H * 0.82]], ink, 132, false);
    drawVariableStroke(g, [[W * 0.18, H * 1.05], [W * 0.34, H * 0.82]], '#C84B31', 114, false);

    // Palm behind scroll
    g.save();
    g.beginPath();
    g.ellipse(wristX + 34, wristY - 20, 56, 46, -0.35, 0, Math.PI * 2);
    g.fillStyle = '#E3AE88';
    g.fill();
    g.lineWidth = 7.5;
    g.strokeStyle = ink;
    g.stroke();
    g.restore();

    // Wax-sealed scroll
    drawModernProp(g, 'wax_sealed_scroll', scrollX, scrollY, 2.85, { rot: scrollRot, globalT });

    // Articulated 4 fingers + thumb wrapping tightly OVER scroll upon contact!
    for (let fi = 0; fi < 4; fi++) {
      const fx = targetX - 34 + fi * 24;
      const fy = lerp(targetY - 78, targetY - 14, gripLock);
      g.save();
      g.beginPath();
      g.roundRect(fx - 10, fy - 24, 21, 50, 10);
      g.fillStyle = '#E3AE88';
      g.fill();
      g.lineWidth = 6.5;
      g.strokeStyle = ink;
      g.stroke();
      g.restore();
    }
    if (gripLock > 0.32) {
      fxRing(g, u, 0.32, targetX, targetY, 135, { dur: 0.45, w: 6, color: 'rgba(255, 240, 188, 0.82)' });
    }
    return true;
  }

  if (insertKind === 'close_scroll_unfold_reveal') {
    // S07 REVEAL: Expressive close-up of Lucius unfolding scroll; triumphant grin -> wide shock -> deadpan;
    // readable diegetic text 'MEETING MOVED TO TOMORROW' inside parchment (~11% screen area!)
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.22, show_fountain: true, fountain_x: 0.82 });
    g.fillStyle = 'rgba(32, 24, 22, 0.20)';
    g.fillRect(0, 0, W, H);

    const luciusSpec = charSpecs.lucius || Object.values(charSpecs)[0];
    const exprNow = u < 0.32 ? 'joyful_laugh' : u < 0.72 ? 'wide_shock' : 'deadpan_disbelief';
    const unfoldK = smooth01(clamp(u / 0.42, 0, 1));

    drawModernExpressiveActor(
      g,
      luciusSpec,
      {
        heightNorm: 0.82,
        facing: 1,
        root: [0.36, 1.24],
        pelvisCenter: [0.36, 0.96],
        hipWorld: [0.36, 0.96],
        neckWorld: [0.36, 0.52],
        headWorld: [0.37, 0.33],
        leftLegWorld: [[0.34, 0.96], [0.34, 1.10], [0.34, 1.24]],
        rightLegWorld: [[0.38, 0.96], [0.38, 1.10], [0.38, 1.24]],
        leftArmWorld: [[0.30, 0.56], [0.42, 0.68], [0.53, 0.60]],
        rightArmWorld: [[0.42, 0.56], [0.54, 0.68], [0.76, 0.60]],
        modernExpression: exprNow,
        handShapeLeft: 'locked_grip',
        handShapeRight: 'locked_grip',
        hairSwayRad: 0.03,
        secondary: { clothSwayNorm: 0.01, headLagRad: 0 },
      },
      { view: 'three_quarter', expressionOverride: exprNow },
    );

    // Unfolding parchment scroll held between Lucius's hands (right-center foreground, ~540x240px = 6.2% of 1080p!)
    const pw = lerp(140, 540, unfoldK);
    const ph = 236;
    const px = W * 0.64 - pw * 0.5;
    const py = H * 0.50;
    fillCelPolygon(
      g,
      [[px, py], [px + pw, py], [px + pw, py + ph], [px, py + ph]],
      '#F8ECD4',
      '#E2D0AE',
      '#FFFDF8',
      ink,
      6.0,
    );
    // Wooden scroll rollers on left & right edges
    for (const rx of [px - 10, px + pw - 8]) {
      g.beginPath();
      g.roundRect(rx, py - 16, 18, ph + 32, 8);
      g.fillStyle = '#7A4928';
      g.fill();
      g.lineWidth = 5.5;
      g.strokeStyle = ink;
      g.stroke();
    }
    if (unfoldK > 0.55) {
      const txtAlpha = smooth01((unfoldK - 0.55) / 0.35);
      text(g, 'IMPERIAL DISPATCH', W * 0.64, py + 52, {
        size: 22,
        font: FONTS.serif,
        weight: 700,
        color: '#8C2D23',
        a: txtAlpha,
        spacing: 2,
      });
      text(g, 'MEETING MOVED', W * 0.64, py + 114, {
        size: 38,
        font: FONTS.body,
        weight: 800,
        color: '#241712',
        a: txtAlpha,
      });
      text(g, 'TO TOMORROW', W * 0.64, py + 164, {
        size: 38,
        font: FONTS.body,
        weight: 800,
        color: '#241712',
        a: txtAlpha,
      });
    }
    return true;
  }

  return false;
}

function drawMinimalEditorialEndBadge(g, titleStr, lt, dur) {
  // Minimal corner/lower-third editorial card (< 11% of frame area, scene remains live & animated!)
  const appear = smooth01((lt - (dur - 1.55)) / 0.42);
  if (appear <= 0.01) return;
  const W = E.W;
  const H = E.H;
  const bw = 520;
  const bh = 96;
  const bx = W - bw - 72;
  const by = H - bh - 64 + (1 - appear) * 24;

  g.save();
  g.globalAlpha = appear;
  fillCelPolygon(
    g,
    [[bx, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh]],
    '#1E1614',
    '#120D0C',
    '#C84B31',
    '#F7EBD2',
    4.0,
  );
  text(g, String(titleStr || 'ALL THAT RUNNING.'), bx + bw * 0.5, by + bh * 0.52, {
    size: 36,
    font: FONTS.title,
    weight: 800,
    color: '#FBF3E0',
    spacing: 2,
  });
  g.restore();
}

// ---------- Master Shot Render Entry ----------

export function renderModernExpressive2DShot(g, lt, info) {
  const W = E.W;
  const H = E.H;
  const shot = info?.shot || E.shots?.find((s) => s.id === info?.id) || info || {};
  const args = shot.args || {};
  const mech = shot.mechanics || args.mechanics || {};
  const world = shot.world_state || args.worldState || {};
  const dur = Math.max(0.1, Number(shot.dur || info?.dur || 3.0));
  const globalT = Number.isFinite(info?.globalT) ? info.globalT : Number(shot.start || 0) + lt;
  const fxProfile = args.fx_profile || args.motionPlan?.fx_profile || 'none';

  // Separated action clock (voice & camera stay on exact unwarped `globalT` / `lt`)
  const warpStops = Array.isArray(args.actionWarpSpecs)
    ? args.actionWarpSpecs.map((w) => [Number(w.at || 0), Number(w.hold || 0.04)])
    : [];
  const clock = createSeparatedActionClock({
    shotStartSec: Number(shot.start || 0),
    shotEndSec: Number(shot.end || Number(shot.start || 0) + dur),
    stops: warpStops,
    fxProfile,
  });
  const actionT = clock.actionTime(globalT);

  const camSeg = resolveActiveCameraSegment(shot, lt);
  const envSpec = args.environmentSpec || _projectCache.envSpec || {};
  const charSpecs = args.characterSpecs || _projectCache.charBible?.characters || {};

  // Check if active segment or shot requests an authored close-up / macro insert
  const segInsert = camSeg.insert_kind || (camSeg.projection_mode === 'authored_2d_insert' ? mech.insert_kind : null);
  const isCloseScale = ['close', 'extreme_close', 'macro', 'detail'].includes(String(camSeg.scale || ''));
  const activeInsert = segInsert || (args.insertKind && isCloseScale ? args.insertKind : mech.only_insert_kind);
  if (activeInsert) {
    const insLt = segInsert ? Math.max(0, lt - Number(camSeg.local_start ?? 0)) : lt;
    const insDur = segInsert ? Math.max(0.15, Number(camSeg.local_end ?? dur) - Number(camSeg.local_start ?? 0)) : dur;
    const handled = drawAuthoredModernInsert(g, activeInsert, insLt, insDur, globalT, charSpecs, envSpec);
    if (handled) {
      if (mech.end_badge_title) {
        drawMinimalEditorialEndBadge(g, mech.end_badge_title, lt, dur);
      }
      return;
    }
  }

  // Camera transform for standard / multi-angle continuous 2D stage
  g.save();
  const z = clamp(Number(camSeg.zoom || 1.0), 1.0, 2.35);
  const hw = W / (2 * z);
  const hh = H / (2 * z);
  const cx = clamp(Number(camSeg.panX ?? 0.5) * W, hw, W - hw);
  const cy = clamp(Number(camSeg.panY ?? 0.54) * H, hh, H - hh);
  g.translate(W * 0.5, H * 0.5);
  g.scale(z, z);
  g.translate(-cx, -cy);

  // 1. Multi-Plane Environment Stage
  drawModernEnvironmentStage(g, envSpec, globalT, camSeg, mech);

  // 2. Evaluate Authoritative MotionPlan & Shared Object Interactions
  const tracks = Array.isArray(args.motionTracks) ? args.motionTracks : [];
  const resolvedObjects = evaluateMultiActorInteraction(tracks, actionT, world);
  const evalByActor = {};
  const backend = String(args.actorBackend || 'modern_2d_canvas');

  for (const tr of tracks) {
    evalByActor[tr.actor_id] = evaluateMotionTrackAt(tr, actionT, world, {
      resolvedObjects,
      seed: Number(args.seed ?? 1476),
      cameraScale: camSeg.scale || 'medium',
    });
  }

  // 3. Draw Background/Midground Interactive Props (counter, cart, rostra, flying/held scroll, beaker, tray)
  const propsToDraw = Array.isArray(args.props) ? args.props : [];
  for (const pr of propsToDraw) {
    if (pr.kind === 'minimal_end_badge') continue;
    let px = Number(pr.x ?? 0.5);
    let py = Number(pr.y ?? 0.76);
    let rot = Number(pr.rot ?? 0);
    if (pr.fromX !== undefined && pr.toX !== undefined) {
      const uP = smooth01(lt / dur);
      px = lerp(Number(pr.fromX), Number(pr.toX), uP);
      py = lerp(Number(pr.fromY ?? py), Number(pr.toY ?? py), uP) - Math.sin(Math.PI * uP) * Number(pr.arcLift ?? 0);
      rot = lerp(Number(pr.rotFrom ?? 0), Number(pr.rotTo ?? 0), uP);
    } else if (pr.objectId && resolvedObjects[pr.objectId]) {
      px = Number(resolvedObjects[pr.objectId].x);
      py = Number(resolvedObjects[pr.objectId].y);
      rot = Number(resolvedObjects[pr.objectId].tiltRad || 0);
    }
    const wheelAngle = (px * W) / 36.0;
    drawModernProp(g, pr.kind, px * W, py * H, Number(pr.scale ?? 1.0), { rot, wheelAngle, globalT });
  }

  // 4. Render Actors via Selected Backend (`legacy_basic_canvas`, `modern_2d_legacy_motion`, `modern_2d_canvas`, `rigby2d_modern`)
  const peopleList = Array.isArray(args.people) ? args.people : [];
  const viewFromCam = String(camSeg.viewpoint || '').includes('profile')
    ? 'profile'
    : String(camSeg.viewpoint || '').includes('rear')
      ? 'rear_three_quarter'
      : String(camSeg.viewpoint || '') === 'front'
        ? 'front'
        : 'three_quarter';

  for (const p of peopleList) {
    const aid = p.id;
    const cSpec = charSpecs[aid] || p.characterSpec || {};
    const ev = evalByActor[aid];
    const talkVal = talkAmount(globalT, Number(shot.start || 0), Number(shot.end || Number(shot.start || 0) + dur));

    if (backend === 'legacy_basic_canvas') {
      // Clip A control: basic legacy Squire geometric figure + sine motion
      const uL = smooth01(lt / dur);
      const lx = lerp(Number(p.from ?? p.x ?? 0.42), Number(p.to ?? p.x ?? 0.42), uL) * W;
      const ly = Number(p.y ?? 0.84) * H;
      soldier(g, lx, ly, Number(p.h ?? 0.28) * H, {
        preset: p.preset || 'peasant',
        t: lt,
        pose: Math.abs(Number(p.to ?? p.x ?? 0) - Number(p.from ?? p.x ?? 0)) > 0.02 ? 'walk' : 'stand',
        walk: Math.abs(Number(p.to ?? p.x ?? 0) - Number(p.from ?? p.x ?? 0)) > 0.02,
        walkMode: 'side',
        walkPhase: lt * 2.2,
        face: 'determined',
      });
    } else if (backend === 'modern_2d_legacy_motion') {
      // Clip B1 art-matched control: NEW Modern Expressive 2D artwork + naive unplanted linear/sine root interpolation
      const uL = smooth01(lt / dur);
      const rx = lerp(Number(p.from ?? p.x ?? 0.42), Number(p.to ?? p.x ?? 0.42), uL);
      const ry = Number(p.y ?? 0.84);
      const hN = Number(p.h ?? 0.30);
      const stepOsc = Math.sin(lt * 10.0) * 0.025;
      drawModernExpressiveActor(
        g,
        cSpec,
        {
          heightNorm: hN,
          facing: Number(p.facing ?? 1),
          root: [rx, ry],
          pelvisCenter: [rx, ry - hN * 0.32],
          hipWorld: [rx, ry - hN * 0.32],
          neckWorld: [rx, ry - hN * 0.56],
          headWorld: [rx, ry - hN * 0.68],
          leftLegWorld: [[rx - 0.015, ry - hN * 0.32], [rx - 0.015 + stepOsc * 0.5, ry - hN * 0.16], [rx - 0.02 + stepOsc, ry]],
          rightLegWorld: [[rx + 0.015, ry - hN * 0.32], [rx + 0.015 - stepOsc * 0.5, ry - hN * 0.16], [rx + 0.02 - stepOsc, ry]],
          leftArmWorld: [[rx - 0.02, ry - hN * 0.54], [rx - 0.03, ry - hN * 0.40], [rx + 0.02, ry - hN * 0.34]],
          rightArmWorld: [[rx + 0.02, ry - hN * 0.54], [rx + 0.05, ry - hN * 0.42], [rx + 0.09, ry - hN * 0.38]],
          modernExpression: p.expression || 'determined_focus',
          handShapeLeft: 'relaxed',
          handShapeRight: 'open_reach',
          hairSwayRad: 0,
          secondary: { clothSwayNorm: 0, headLagRad: 0 },
        },
        { view: viewFromCam, talk: talkVal },
      );
    } else if ((backend === 'rigby2d_modern' || backend === 'rigby2d') && _projectCache.rigAssetsByActor.has(aid) && ev) {
      // Real Rigby2D 0.5.1 WebGL skeletal compositor with NEW 1024x1024 Modern Expressive 2D rig + dynamic expression slots!
      const rigAsset = _projectCache.rigAssetsByActor.get(aid);
      const exprName = p.expression || ev.modernExpression || 'neutral_attentive';
      const handGrip = ev.handShapeRight === 'locked_grip' ? 'hand_r_grip' : 'hand_r';
      renderRigbyActorToCanvas(
        g,
        actionT,
        { x: ev.root[0] * W, y: ev.root[1] * H, facing: ev.facing ?? 1, actorHeight: ev.heightNorm * H },
        rigAsset,
        {
          animationName: `mp_${shot.id}_${aid}`,
          animStartSec: Number(shot.start || 0),
          actorHeight: ev.heightNorm * H,
          slotAttachments: {
            head: `head_${exprName}`,
            hand_r: handGrip,
          },
        },
      );
    } else if (ev) {
      // Default: High-Craft Modern Expressive 2D Canvas + Authoritative MotionPlan IK & Secondary Motion
      drawModernExpressiveActor(g, cSpec, ev, {
        view: p.view || viewFromCam,
        expressionOverride: p.expression || null,
        handOverride: p.handPose || null,
        talk: p.talk !== false ? talkVal * 0.65 : 0,
      });
    }

    // Draw actor-held portable prop locked directly to rightHandWorld!
    if (p.heldProp && ev) {
      drawModernProp(g, p.heldProp, ev.rightHandWorld[0] * W, ev.rightHandWorld[1] * H, Number(p.heldPropScale ?? 0.92), {
        rot: Number(ev.torsoLeanRad || 0) * 0.8,
        globalT,
      });
    }
  }

  // 5. Motivated Sparse FX (dust puffs on foot brace/land, wind sparkles — ZERO neon/halftone!)
  if (fxProfile && fxProfile !== 'none' && Array.isArray(args.fxEvents)) {
    for (let i = 0; i < args.fxEvents.length; i++) {
      const fe = args.fxEvents[i];
      const fxX = Number(fe.x ?? 0.5) * W;
      const fxY = Number(fe.y ?? 0.8) * H;
      const t0 = Number(fe.t0 ?? shot.start ?? 0);
      if (fe.kind === 'foot_brace_dust') {
        landDust(g, globalT, t0, fxX, fxY, 1.15, 'rgba(218, 198, 168, 0.68)');
      } else if (fe.kind === 'catch_accent_ring') {
        fxRing(g, globalT, t0, fxX, fxY, 88, { dur: 0.36, w: 4, color: 'rgba(255, 240, 188, 0.72)' });
      } else {
        burstParticles(g, globalT, t0, fxX, fxY, {
          n: 10,
          speed: 210,
          life: 0.48,
          colors: ['#FFF4D2', '#F2C97D', '#E8A838'],
          size: 4.5,
          kind: 'dust',
          seed: Number(args.seed ?? 1476) + i * 29,
        });
      }
    }
  }

  // 6. Foreground Depth Occluders
  drawForegroundOccluders(g, envSpec, camSeg);

  g.restore();

  if (mech.end_badge_title) {
    drawMinimalEditorialEndBadge(g, mech.end_badge_title, lt, dur);
  }
}

// Register universal pack template so `tpl: "modern_expressive_2d"` works across ALL projects with zero per-story JS!
registerTemplate('modern_expressive_2d', {
  draw(ctx, lt, info) {
    renderModernExpressive2DShot(ctx, lt, info);
  },
});

export async function registerModernExpressive2DShots(shotIds = null) {
  await initModernExpressive2D(E);
  const ids = shotIds || (E.shots || []).map((s) => s.id);
  for (const sid of ids) {
    registerShot(sid, {
      draw(ctx, lt, info) {
        renderModernExpressive2DShot(ctx, lt, info);
      },
    });
  }
}
