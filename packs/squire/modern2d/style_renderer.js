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

function sampleQuadBezier2D(p0, p1, p2, steps = 12) {
  const out = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const mt = 1 - t;
    out.push([
      mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
      mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
    ]);
  }
  return out;
}

function buildCurvedTaperedLimb2D(p0, pMid, p2, w0, wMid, w2, steps = 12) {
  const ctrl = [
    2 * pMid[0] - 0.5 * (p0[0] + p2[0]),
    2 * pMid[1] - 0.5 * (p0[1] + p2[1]),
  ];
  const spine = sampleQuadBezier2D(p0, ctrl, p2, steps);
  const left = [];
  const right = [];
  const n = spine.length;
  for (let i = 0; i < n; i++) {
    const u = i / Math.max(1, n - 1);
    let hw;
    if (u <= 0.5) {
      const su = u * 2;
      hw = 0.5 * (w0 + (wMid - w0) * (su * (2 - su)));
    } else {
      const su = (u - 0.5) * 2;
      hw = 0.5 * (wMid + (w2 - wMid) * (su * su * (3 - 2 * su)));
    }
    const prev = spine[Math.max(0, i - 1)];
    const next = spine[Math.min(n - 1, i + 1)];
    const tx = next[0] - prev[0];
    const ty = next[1] - prev[1];
    const len = Math.max(1e-4, Math.hypot(tx, ty));
    const nx = -ty / len;
    const ny = tx / len;
    left.push([spine[i][0] + nx * hw, spine[i][1] + ny * hw]);
    right.push([spine[i][0] - nx * hw, spine[i][1] - ny * hw]);
  }
  const poly = left.concat([...right].reverse());
  return { poly, left, right, spine };
}

function drawVariableStroke(g, pts, color, maxLw, taperEnds = true, calligraphicSubdiv = false) {
  if (!pts || pts.length < 2) return;
  let workPts = pts;
  if (calligraphicSubdiv && pts.length === 2 && taperEnds) {
    const mx = 0.5 * (pts[0][0] + pts[1][0]);
    const my = 0.5 * (pts[0][1] + pts[1][1]);
    workPts = sampleQuadBezier2D(pts[0], [mx, my], pts[1], 8);
  }
  g.save();
  g.strokeStyle = color;
  g.lineCap = 'round';
  g.lineJoin = 'round';
  if (!taperEnds || workPts.length === 2) {
    g.beginPath();
    g.moveTo(workPts[0][0], workPts[0][1]);
    for (let i = 1; i < workPts.length; i++) g.lineTo(workPts[i][0], workPts[i][1]);
    g.lineWidth = maxLw;
    g.stroke();
    g.restore();
    return;
  }
  const n = workPts.length - 1;
  for (let i = 0; i < n; i++) {
    const u = (i + 0.5) / n;
    const w = Math.max(1.1, maxLw * (0.34 + 0.66 * Math.sin(Math.PI * u)));
    g.beginPath();
    g.moveTo(workPts[i][0], workPts[i][1]);
    g.lineTo(workPts[i + 1][0], workPts[i + 1][1]);
    g.lineWidth = w;
    g.stroke();
  }
  g.restore();
}

function fillCelPolygon(g, pts, baseHex, shadowHex, rimHex, outerInkHex, lwOuter, lightSide = -1, angledShadow = false) {
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
    if (angledShadow) {
      g.beginPath();
      if (lightSide < 0) {
        g.moveTo(minX + spanW * 0.50, minY - 6);
        g.lineTo(maxX + 8, minY - 6);
        g.lineTo(maxX + 8, maxY + 8);
        g.lineTo(minX + spanW * 0.36, maxY + 8);
      } else {
        g.moveTo(minX - 8, minY - 6);
        g.lineTo(minX + spanW * 0.50, minY - 6);
        g.lineTo(minX + spanW * 0.64, maxY + 8);
        g.lineTo(minX - 8, maxY + 8);
      }
      g.closePath();
      g.fill();
    } else {
      const shX = lightSide < 0 ? minX + spanW * 0.56 : minX - spanW * 0.1;
      g.fillRect(shX, minY - 4, spanW * 0.58, spanH + 8);
    }
  }
  if (rimHex) {
    g.fillStyle = rimHex;
    const rimW = Math.max(3.5, spanW * 0.13);
    const rimX = lightSide < 0 ? minX : maxX - rimW;
    g.fillRect(rimX, minY - 2, rimW, spanH + 4);
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
  const isV2Env = String(spec.style_id || '').endsWith('.v2');
  const skyGrad = g.createLinearGradient(0, 0, 0, groundY);
  skyGrad.addColorStop(0, pal.sky[0]);
  skyGrad.addColorStop(0.55, pal.sky[Math.min(1, pal.sky.length - 1)]);
  skyGrad.addColorStop(1, pal.sky[pal.sky.length - 1]);
  g.fillStyle = skyGrad;
  g.fillRect(0, 0, W, H);

  if (niche === 'city_park') {
    // Drifting sunlit cumulus clouds
    const drift = (globalT * (12 + wind * 18)) % (W + 460);
    g.save();
    g.fillStyle = 'rgba(255, 252, 245, 0.88)';
    for (const [bx, by, rx, ry] of [[300, 148, 175, 44], [1080, 118, 225, 50], [1720, 168, 155, 38]]) {
      const cx = ((bx - drift) + W + 460) % (W + 460) - 230;
      g.beginPath();
      g.ellipse(cx, by, rx, ry, 0, 0, Math.PI * 2);
      g.ellipse(cx + rx * 0.34, by - ry * 0.48, rx * 0.62, ry * 0.80, 0, 0, Math.PI * 2);
      g.fill();
    }
    g.restore();

    if (isClose) {
      // Soft atmospheric park bokeh & sunlit canopy mood backdrop (Ref 3 closeup discipline!)
      g.save();
      for (const [bx, by, br, colA] of [
        [W * 0.20, H * 0.30, 210, 'rgba(78, 139, 82, 0.24)'],
        [W * 0.78, H * 0.26, 245, 'rgba(136, 185, 105, 0.26)'],
        [W * 0.50, H * 0.44, 280, 'rgba(255, 244, 200, 0.24)'],
      ]) {
        g.beginPath();
        g.arc(bx + Math.sin(globalT * 1.4) * 8, by, br, 0, Math.PI * 2);
        g.fillStyle = colA;
        g.fill();
      }
      g.restore();
    } else {
      // Rolling park meadow hills & multi-plane tree canopies
      fillCelPolygon(
        g,
        [[0, groundY], [0, H * 0.55], [W * 0.28, H * 0.48], [W * 0.64, H * 0.52], [W, H * 0.46], [W, groundY]],
        '#76AE62',
        null,
        '#A4D484',
        pal.far_ink_hex,
        2.6,
      );
      for (const [tx, ty, rw, rh, cHex] of [
        [0.10, 0.37, 175, 130, pal.architecture[1] || '#2F663B'],
        [0.24, 0.40, 145, 112, pal.architecture[0] || '#4E8B52'],
        [0.44, 0.39, 152, 108, pal.architecture[1] || '#2F663B'],
        [0.91, 0.35, 185, 142, pal.architecture[0] || '#4E8B52'],
      ]) {
        const swayT = Math.sin(globalT * (1.8 + wind) + tx * 9) * (4 + wind * 6);
        fillCelPolygon(
          g,
          [[W * tx - 16, H * ty + 32], [W * tx + 16, H * ty + 32], [W * tx + 20, H * 0.68], [W * tx - 20, H * 0.68]],
          '#6B4B35',
          '#4B3323',
          '#8E684C',
          pal.far_ink_hex,
          2.6,
        );
        g.save();
        g.beginPath();
        g.ellipse(W * tx + swayT, H * ty, rw, rh, 0, 0, Math.PI * 2);
        g.fillStyle = cHex;
        g.fill();
        g.lineWidth = 3.0;
        g.strokeStyle = pal.far_ink_hex;
        g.stroke();
        g.beginPath();
        g.ellipse(W * tx - rw * 0.18 + swayT, H * ty - rh * 0.32, rw * 0.62, rh * 0.52, 0, 0, Math.PI * 2);
        g.fillStyle = pal.architecture[2] || '#88B969';
        g.fill();
        g.restore();
      }

      // Lush sunlit lawn strip + background park bicycle lane with cruising cyclists!
      g.fillStyle = pal.architecture[2] || '#88B969';
      g.fillRect(0, H * 0.64, W, groundY - H * 0.64);
      drawVariableStroke(g, [[0, H * 0.64], [W, H * 0.64]], pal.mid_ink_hex, 3.0, false);
      g.fillStyle = '#E5D8C1';
      g.fillRect(0, H * 0.675, W, H * 0.032);

      // Animated background bicycles cruising smoothly along the far park path
      for (let bi = 0; bi < 2; bi++) {
        const bxC = ((W * (0.18 + bi * 0.34) + globalT * (32 + bi * 14)) % (W + 180)) - 90;
        const byC = H * 0.686;
        g.save();
        g.strokeStyle = pal.far_ink_hex;
        g.lineWidth = 2.6;
        for (const wx of [bxC - 18, bxC + 18]) {
          g.beginPath();
          g.arc(wx, byC, 12, 0, Math.PI * 2);
          g.stroke();
        }
        drawVariableStroke(g, [[bxC - 18, byC], [bxC - 3, byC - 16], [bxC + 14, byC - 15], [bxC + 2, byC]], pal.accents[2] || '#2D7D90', 2.8, false);
        // Tiny background cyclist silhouette
        g.fillStyle = 'rgba(54, 68, 82, 0.72)';
        g.beginPath();
        g.ellipse(bxC - 2, byC - 26, 7, 12, 0.18, 0, Math.PI * 2);
        g.arc(bxC + 1, byC - 42, 6, 0, Math.PI * 2);
        g.fill();
        g.restore();
      }

      // Breezy paper pennant garland strung between park lampposts
      for (const lpX of [W * 0.14, W * 0.41]) {
        fillCelPolygon(g, [[lpX - 5, H * 0.41], [lpX + 5, H * 0.41], [lpX + 6, H * 0.72], [lpX - 6, H * 0.72]], '#2B353E', '#181E24', '#5A6B7C', pal.mid_ink_hex, 2.6);
        g.beginPath();
        g.arc(lpX, H * 0.40, 14, 0, Math.PI * 2);
        g.fillStyle = '#FFF5CC';
        g.fill();
        g.lineWidth = 2.6;
        g.strokeStyle = pal.mid_ink_hex;
        g.stroke();
      }
      for (let pi = 0; pi < 9; pi++) {
        const uP = pi / 8;
        const pxP = lerp(W * 0.14, W * 0.41, uP);
        const pyP = H * 0.425 + Math.sin(Math.PI * uP) * 34 + Math.sin(globalT * (5.2 + wind * 2) + pi * 0.8) * (4 + wind * 6);
        fillCelPolygon(
          g,
          [[pxP - 11, pyP], [pxP + 11, pyP + 2], [pxP + Math.sin(globalT * 6 + pi) * 4, pyP + 24]],
          pal.accents[pi % 3] || '#E0473B',
          null,
          null,
          pal.mid_ink_hex,
          2.2,
        );
      }

      // Diagonal warm golden sunbeams (~38 deg, Ref 2 lighting craft!)
      const warmBoost = Number(mech.warm_sun_boost ?? 0);
      g.save();
      g.fillStyle = `rgba(255, 243, 194, ${0.18 + warmBoost * 0.10})`;
      for (const sbX of [W * 0.14, W * 0.46]) {
        g.beginPath();
        g.moveTo(sbX, 0);
        g.lineTo(sbX + W * 0.11, 0);
        g.lineTo(sbX + W * 0.31, groundY);
        g.lineTo(sbX + W * 0.18, groundY);
        g.closePath();
        g.fill();
      }
      g.restore();

      // Hero Ornamental Park Tree (`x ~ 0.67`) + Low Overhanging Snag Branch (`x ~ 0.54..0.66, y ~ 0.52`)
      if (mech.show_ornamental_tree !== false) {
        const trX = W * Number(mech.tree_x ?? 0.67);
        const brSway = Math.sin(globalT * (2.6 + wind * 2.0)) * (2.5 + wind * 5.0);
        fillCelPolygon(
          g,
          [[trX - 36, groundY - 26], [trX - 24, H * 0.32], [trX + 30, H * 0.32], [trX + 48, groundY - 26]],
          '#734E36',
          '#4F3422',
          '#9C7152',
          pal.mid_ink_hex,
          lw + 0.6,
          -1,
          true,
        );
        // Bark grain strokes
        drawVariableStroke(g, [[trX - 10, H * 0.44], [trX - 6, H * 0.56]], pal.mid_ink_hex, 2.5, true, true);
        drawVariableStroke(g, [[trX + 8, H * 0.52], [trX + 12, H * 0.66]], pal.mid_ink_hex, 2.5, true, true);

        // Low ornamental branch reaching toward park bench
        const brTipX = W * Number(mech.branch_tip_x ?? 0.54);
        const brTipY = H * Number(mech.branch_tip_y ?? 0.525) + brSway;
        const brPoly = buildCurvedTaperedLimb2D([trX - 18, H * 0.495], [(trX + brTipX) * 0.5, H * 0.505 + brSway * 0.5], [brTipX, brTipY], 26, 18, 9, 10);
        fillCelPolygon(g, brPoly.poly, '#734E36', '#4F3422', '#9C7152', pal.mid_ink_hex, lw * 0.88);

        for (const [lx, ly, lrw, lrh] of [
          [trX - 10, H * 0.24, 210, 124],
          [trX - 125, H * 0.29, 145, 92],
          [trX + 115, H * 0.29, 155, 98],
          [brTipX + 18, brTipY - 18, 62, 34],
        ]) {
          g.save();
          g.beginPath();
          g.ellipse(lx + brSway * 0.7, ly, lrw, lrh, 0, 0, Math.PI * 2);
          g.fillStyle = pal.architecture[0] || '#4E8B52';
          g.fill();
          g.lineWidth = lw;
          g.strokeStyle = pal.mid_ink_hex;
          g.stroke();
          g.beginPath();
          g.ellipse(lx - lrw * 0.22 + brSway * 0.7, ly - lrh * 0.28, lrw * 0.58, lrh * 0.48, 0, 0, Math.PI * 2);
          g.fillStyle = pal.architecture[2] || '#88B969';
          g.fill();
          g.restore();
        }
      }

      // Patterned Slatted-Oak & Wrought-Iron Park Bench (`x ~ 0.41..0.57`)
      if (mech.show_park_bench !== false) {
        const bCx = W * Number(mech.bench_x ?? 0.49);
        const bwHalf = 148;
        const seatY = groundY - 68;
        const backY = groundY - 128;
        g.save();
        g.beginPath();
        g.ellipse(bCx, groundY - 2, bwHalf * 1.08, 12, 0, 0, Math.PI * 2);
        g.fillStyle = 'rgba(32, 26, 22, 0.30)';
        g.fill();
        g.restore();

        for (const sy of [backY, backY + 26]) {
          fillCelPolygon(
            g,
            [[bCx - bwHalf, sy], [bCx + bwHalf, sy], [bCx + bwHalf, sy + 18], [bCx - bwHalf, sy + 18]],
            '#C88A52',
            '#9B6536',
            '#EAB47E',
            pal.mid_ink_hex,
            3.2,
          );
        }
        fillCelPolygon(
          g,
          [[bCx - bwHalf - 10, seatY], [bCx + bwHalf + 10, seatY], [bCx + bwHalf + 6, seatY + 22], [bCx - bwHalf - 6, seatY + 22]],
          '#D89B62',
          '#A46E3C',
          '#F5C592',
          pal.mid_ink_hex,
          3.4,
        );
        for (const lx of [bCx - bwHalf + 22, bCx + bwHalf - 22]) {
          fillCelPolygon(g, [[lx - 7, backY - 4], [lx + 7, backY - 4], [lx + 7, groundY], [lx - 7, groundY]], '#2B333C', '#171C22', '#556373', pal.mid_ink_hex, 2.8);
          // Wrought-iron curved armrest scroll
          g.save();
          g.beginPath();
          g.arc(lx, seatY - 14, 16, Math.PI * 0.8, Math.PI * 2.1);
          g.lineWidth = 4.2;
          g.strokeStyle = '#2B333C';
          g.stroke();
          g.restore();
        }
      }

      // Tiered Carved Stone Park Fountain (`x ~ 0.81`)
      if (mech.show_fountain !== false) {
        const fxC = W * Number(mech.fountain_x ?? 0.81);
        fillCelPolygon(
          g,
          [[fxC - 154, groundY - 88], [fxC + 154, groundY - 88], [fxC + 142, groundY + 6], [fxC - 142, groundY + 6]],
          '#E5DAC6',
          '#BFB29B',
          '#FFF9ED',
          pal.mid_ink_hex,
          lw,
        );
        g.beginPath();
        g.ellipse(fxC, groundY - 88, 138, 20, 0, 0, Math.PI * 2);
        g.fillStyle = '#56BADA';
        g.fill();
        g.lineWidth = lw;
        g.strokeStyle = pal.mid_ink_hex;
        g.stroke();
        fillCelPolygon(
          g,
          [[fxC - 28, groundY - 216], [fxC + 28, groundY - 216], [fxC + 34, groundY - 88], [fxC - 34, groundY - 88]],
          '#EFE6D5',
          '#C6B9A3',
          '#FFFFFF',
          pal.mid_ink_hex,
          lw,
        );
        g.beginPath();
        g.ellipse(fxC, groundY - 218, 78, 18, 0, 0, Math.PI * 2);
        g.fillStyle = '#EFE6D5';
        g.fill();
        g.stroke();
        g.save();
        g.strokeStyle = 'rgba(222, 250, 255, 0.90)';
        g.lineWidth = 3.8;
        for (const sgn of [-1, 1]) {
          const dropShift = Math.sin(globalT * 7.2 + sgn) * 5;
          g.beginPath();
          g.moveTo(fxC + sgn * 16, groundY - 232);
          g.quadraticCurveTo(fxC + sgn * (84 + dropShift), groundY - 226, fxC + sgn * 96, groundY - 94);
          g.stroke();
        }
        g.restore();
      }
    }
  } else if (niche === 'holdout_botanical_conservatory') {
    // Arched wrought-iron glasshouse conservatory + diagonal sunbeam + terracotta orchid bench
    g.fillStyle = pal.architecture[0] || '#D9ECE8';
    g.fillRect(0, H * 0.14, W, groundY - H * 0.14);
    g.save();
    g.strokeStyle = pal.architecture[3] || '#2E5347';
    g.lineWidth = lw + 1.2;
    for (let ri = 0; ri < 6; ri++) {
      const rx = W * (0.08 + ri * 0.168);
      g.beginPath();
      g.moveTo(rx, H * 0.14);
      g.lineTo(rx, groundY);
      g.stroke();
      g.beginPath();
      g.arc(rx, H * 0.16, W * 0.084, Math.PI, Math.PI * 2);
      g.stroke();
    }
    g.fillStyle = 'rgba(255, 245, 209, 0.24)';
    g.beginPath();
    g.moveTo(W * 0.24, 0);
    g.lineTo(W * 0.38, 0);
    g.lineTo(W * 0.60, groundY);
    g.lineTo(W * 0.42, groundY);
    g.closePath();
    g.fill();
    g.restore();
    fillCelPolygon(
      g,
      [[W * 0.32, H * 0.69], [W * 0.68, H * 0.69], [W * 0.68, H * 0.74], [W * 0.32, H * 0.74]],
      '#9E6B47',
      '#734B2F',
      '#C9966E',
      pal.mid_ink_hex,
      lw,
    );
    g.fillStyle = '#6E482E';
    g.fillRect(W * 0.36, H * 0.74, 24, groundY - H * 0.74);
    g.fillRect(W * 0.62, H * 0.74, 24, groundY - H * 0.74);
  } else if (niche.includes('roman')) {
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
  const spec = envSpec || _projectCache.envSpec || {};
  const pal = spec.palette || { shadow_tint_hex: '#2E2228', mid_ink_hex: '#1F1716', accents: ['#E0473B', '#F2A93B'] };
  const isV2 = String(spec.style_id || '').endsWith('.v2');
  g.save();
  if (isV2 && spec.niche === 'city_park') {
    // Organic foreground park shrubs + wildflowers on bottom-left & overhanging canopy leaves on top-right
    g.fillStyle = 'rgba(28, 56, 40, 0.88)';
    g.strokeStyle = pal.mid_ink_hex || '#1F1716';
    g.lineWidth = 3.6;
    for (const [bx, by, rx, ry] of [[W * 0.03, H * 0.95, 148, 96], [W * 0.11, H * 0.99, 112, 72], [W * 0.95, H * 0.05, 156, 84]]) {
      g.beginPath();
      g.ellipse(bx, by, rx, ry, 0, 0, Math.PI * 2);
      g.fill();
      g.stroke();
    }
    for (const [fx, fy] of [[W * 0.045, H * 0.90], [W * 0.088, H * 0.935]]) {
      g.beginPath();
      g.arc(fx, fy, 8, 0, Math.PI * 2);
      g.fillStyle = pal.accents?.[1] || '#F2A93B';
      g.fill();
      g.stroke();
    }
  } else {
    // Left foreground silhouette amphora/planter + right subtle frame column
    g.fillStyle = alpha(pal.shadow_tint_hex || '#2E2228', 0.84);
    g.strokeStyle = pal.mid_ink_hex || '#1F1716';
    g.lineWidth = 3.5;
    g.beginPath();
    g.ellipse(W * 0.02, H * 0.90, W * 0.065, H * 0.15, 0.08, 0, Math.PI * 2);
    g.fill();
    g.stroke();
    g.fillRect(W * 0.968, 0, W * 0.032, H);
  }
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
  } else if (kind === 'origami_dragon_kite' || kind === 'kite' || kind === 'dragon') {
    // Original handcrafted faceted origami dragon kite with crisp paper creases & fluttering ribbon tail!
    const kw = 86 * s;
    const kh = 98 * s;
    const flap = Math.sin(Number(opts.globalT || 0) * 6.2) * 5.5 * s;
    // Left & right swept origami dragon wings
    fillCelPolygon(
      g,
      [[0, -kh * 0.34], [-kw * 0.98, -kh * 0.10 + flap], [-kw * 0.56, kh * 0.28 + flap * 0.6], [0, kh * 0.14]],
      '#E0473B',
      '#B53026',
      '#FF8B7E',
      ink,
      3.4 * s,
      -1,
      true,
    );
    fillCelPolygon(
      g,
      [[0, -kh * 0.34], [kw * 0.98, -kh * 0.10 - flap], [kw * 0.56, kh * 0.28 - flap * 0.6], [0, kh * 0.14]],
      '#F2A93B',
      '#C8821E',
      '#FFE29A',
      ink,
      3.4 * s,
      -1,
      true,
    );
    // Central origami diamond body + horn crests
    fillCelPolygon(
      g,
      [[0, -kh * 0.62], [kw * 0.34, -kh * 0.08], [0, kh * 0.52], [-kw * 0.34, -kh * 0.08]],
      '#FFF6E5',
      '#DFD0B6',
      '#FFFFFF',
      ink,
      3.6 * s,
      -1,
      true,
    );
    // Teal origami dragon horn crests
    fillCelPolygon(g, [[-8 * s, -kh * 0.50], [-28 * s, -kh * 0.78], [-2 * s, -kh * 0.62]], '#2D7D90', null, '#6DC4D8', ink, 2.6 * s);
    fillCelPolygon(g, [[8 * s, -kh * 0.50], [28 * s, -kh * 0.78], [2 * s, -kh * 0.62]], '#2D7D90', null, '#6DC4D8', ink, 2.6 * s);
    // Crisp bamboo spar & origami paper crease lines
    drawVariableStroke(g, [[0, -kh * 0.60], [0, kh * 0.50]], '#7E5433', 2.6 * s, false);
    drawVariableStroke(g, [[-kw * 0.92, -kh * 0.09 + flap], [kw * 0.92, -kh * 0.09 - flap]], '#7E5433', 2.4 * s, false);
    drawVariableStroke(g, [[-kw * 0.32, -kh * 0.08], [-kw * 0.55, kh * 0.26 + flap * 0.6]], ink, 1.8 * s, true, true);
    drawVariableStroke(g, [[kw * 0.32, -kh * 0.08], [kw * 0.55, kh * 0.26 - flap * 0.6]], ink, 1.8 * s, true, true);
    // Expressive painted dragon eyes on kite face
    for (const exSgn of [-1, 1]) {
      g.beginPath();
      g.ellipse(exSgn * 12 * s, -kh * 0.22, 5.5 * s, 4.0 * s, exSgn * -0.25, 0, Math.PI * 2);
      g.fillStyle = '#2D7D90';
      g.fill();
      g.strokeStyle = ink;
      g.lineWidth = 2.0 * s;
      g.stroke();
    }
    // Undulating crimson ribbon tail + colorful paper tail bows
    if (opts.hideTail !== true) {
      const tPts = [];
      const gt = Number(opts.globalT || 0);
      for (let ti = 0; ti <= 8; ti++) {
        const uT = ti / 8;
        const tx = Math.sin(gt * 6.8 - uT * 4.5) * (24 * uT) * s - uT * 18 * s;
        const ty = kh * 0.52 + uT * 112 * s;
        tPts.push([tx, ty]);
      }
      drawVariableStroke(g, tPts, ink, 7.2 * s, true);
      drawVariableStroke(g, tPts, '#DC392D', 4.6 * s, true);
      for (const bi of [2, 5, 7]) {
        const [bx, by] = tPts[bi];
        fillCelPolygon(
          g,
          [[bx - 11 * s, by - 5 * s], [bx + 11 * s, by + 5 * s], [bx + 11 * s, by - 5 * s], [bx - 11 * s, by + 5 * s]],
          bi === 5 ? '#2D7D90' : '#F2A93B',
          null,
          null,
          ink,
          2.0 * s,
        );
      }
    }
  } else if (kind === 'kite_spool' || kind === 'spool') {
    // Turned oak wooden spool wound with bright crimson kite string
    const sw = 38 * s;
    const sh = 26 * s;
    fillCelPolygon(
      g,
      [[-sw * 0.42, -sh * 0.45], [sw * 0.42, -sh * 0.45], [sw * 0.42, sh * 0.45], [-sw * 0.42, sh * 0.45]],
      '#DC392D',
      '#A12219',
      '#FF796E',
      ink,
      2.8 * s,
    );
    for (const fx of [-sw * 0.48, sw * 0.48]) {
      fillCelPolygon(
        g,
        [[fx - 5 * s, -sh * 0.68], [fx + 5 * s, -sh * 0.68], [fx + 5 * s, sh * 0.68], [fx - 5 * s, sh * 0.68]],
        '#B87B48',
        '#85522A',
        '#E5AD7B',
        ink,
        2.8 * s,
      );
    }
  } else if (kind === 'terracotta_orchid_pot' || kind === 'orchid' || kind === 'pot') {
    fillCelPolygon(
      g,
      [[-24 * s, -12 * s], [24 * s, -12 * s], [17 * s, 24 * s], [-17 * s, 24 * s]],
      '#C86D44',
      '#944828',
      '#EE9972',
      ink,
      3.0 * s,
    );
    drawVariableStroke(g, [[0, -12 * s], [4 * s, -48 * s]], '#2E6B4E', 4.2 * s, false);
    for (const [ox, oy] of [[-8, -42], [10, -48], [2, -30]]) {
      g.beginPath();
      g.arc(ox * s, oy * s, 9 * s, 0, Math.PI * 2);
      g.fillStyle = '#FAF2E6';
      g.fill();
      g.lineWidth = 2.4 * s;
      g.strokeStyle = ink;
      g.stroke();
    }
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

function drawV2ArticulatedHandCanvas(g, wristPt, elbowPt, headR, handShape, armCol, armSh, ink, inkIn, lwOuter, dirX) {
  const dx = wristPt[0] - elbowPt[0];
  const dy = wristPt[1] - elbowPt[1];
  const baseAng = Math.hypot(dx, dy) > 2.0 ? Math.atan2(dy, dx) : (dirX >= 0 ? 0.14 : Math.PI - 0.14);
  const palmR = headR * 0.23;
  const px = wristPt[0] + Math.cos(baseAng) * palmR * 0.70;
  const py = wristPt[1] + Math.sin(baseAng) * palmR * 0.70;
  const perpX = -Math.sin(baseAng);
  const perpY = Math.cos(baseAng);

  const palmPoly = [
    [wristPt[0] + perpX * palmR * 0.60, wristPt[1] + perpY * palmR * 0.60],
    [px + Math.cos(baseAng) * palmR * 0.66 + perpX * palmR * 0.84, py + Math.sin(baseAng) * palmR * 0.66 + perpY * palmR * 0.84],
    [px + Math.cos(baseAng) * palmR * 0.66 - perpX * palmR * 0.80, py + Math.sin(baseAng) * palmR * 0.66 - perpY * palmR * 0.80],
    [wristPt[0] - perpX * palmR * 0.56, wristPt[1] - perpY * palmR * 0.56],
  ];

  // Opposable curved thumb
  const thAng = baseAng - dirX * 0.86;
  const thMid = [px + Math.cos(thAng) * palmR * 0.76, py + Math.sin(thAng) * palmR * 0.76];
  const thTip = [thMid[0] + Math.cos(thAng + dirX * 0.26) * palmR * 0.64, thMid[1] + Math.sin(thAng + dirX * 0.26) * palmR * 0.64];
  const thShape = buildCurvedTaperedLimb2D([px, py], thMid, thTip, palmR * 0.58, palmR * 0.46, palmR * 0.28, 6);
  fillCelPolygon(g, thShape.poly, armCol, null, null, ink, lwOuter * 0.68);

  // Palm fill + outline
  fillCelPolygon(g, palmPoly, armCol, armSh, null, ink, lwOuter * 0.74, -dirX);

  if (handShape === 'locked_grip') {
    g.save();
    g.fillStyle = armCol;
    g.strokeStyle = ink;
    g.lineWidth = Math.max(1.6, lwOuter * 0.62);
    for (let fi = 0; fi < 4; fi++) {
      const off = (fi - 1.5) * palmR * 0.40;
      const fx = px + Math.cos(baseAng) * palmR * 0.54 + perpX * off;
      const fy = py + Math.sin(baseAng) * palmR * 0.54 + perpY * off;
      g.beginPath();
      g.roundRect(fx - palmR * 0.34, fy - palmR * 0.20, palmR * 0.68, palmR * 0.40, Math.max(2, palmR * 0.16));
      g.fill();
      g.stroke();
    }
    g.restore();
  } else {
    const spread = (handShape === 'open_reach' || handShape === 'spread_shock') ? 0.27 : 0.15;
    for (let fi = 0; fi < 4; fi++) {
      const fLen = (handShape === 'pointing' && fi > 0)
        ? palmR * 0.55
        : palmR * ((fi === 1 || fi === 2) ? 1.38 : 1.14) * (handShape === 'spread_shock' ? 1.12 : 1.0);
      const fAng = baseAng + (fi - 1.5) * spread;
      const curl = handShape === 'relaxed' ? 0.22 * dirX : (handShape === 'spread_shock' ? -0.08 * dirX : 0.08 * dirX);
      const kn = [
        px + Math.cos(baseAng) * palmR * 0.54 + perpX * (fi - 1.5) * palmR * 0.36,
        py + Math.sin(baseAng) * palmR * 0.54 + perpY * (fi - 1.5) * palmR * 0.36,
      ];
      const fMid = [kn[0] + Math.cos(fAng) * fLen * 0.54, kn[1] + Math.sin(fAng) * fLen * 0.54];
      const fTip = [fMid[0] + Math.cos(fAng + curl) * fLen * 0.50, fMid[1] + Math.sin(fAng + curl) * fLen * 0.50];
      const fShape = buildCurvedTaperedLimb2D(kn, fMid, fTip, palmR * 0.42, palmR * 0.34, palmR * 0.20, 6);
      fillCelPolygon(g, fShape.poly, armCol, null, null, ink, lwOuter * 0.62);
    }
  }
  drawVariableStroke(g, [[px - perpX * palmR * 0.22, py - perpY * palmR * 0.22], [px + perpX * palmR * 0.30, py + perpY * palmR * 0.30]], inkIn, lwOuter * 0.36, true, true);
}

function drawModernExpressiveActorV2(g, actorSpec, evalState, opts = {}) {
  const W = E.W;
  const H = E.H;
  const spec = actorSpec || {};
  const wd = spec.wardrobe || {
    garment_kind: 'layered_parka_windbreaker_over_striped_tee',
    primary_hex: '#E0533C',
    primary_shadow_hex: '#A83725',
    primary_rim_hex: '#FF8A75',
    secondary_hex: '#FFF5DE',
    pants_hex: '#3B4F6B',
    pants_shadow_hex: '#28364A',
    trim_hex: '#2D7D90',
    accessory_hex: '#E6A13B',
    footwear: 'cuffed_canvas_park_sneakers',
    accessories: ['star_hair_clip', 'striped_inner_tee'],
  };
  const sk = spec.skin_palette || { base: '#F0C19E', shadow: '#C89270', rim: '#FFF0DF', blush: '#E67B6B' };
  const hr = spec.hair_palette || { base: '#2B222C', shadow: '#171218', highlight: '#5D4E63' };
  const ink = spec.ink_outer_hex || '#211612';
  const inkIn = spec.ink_inner_hex || '#3A2821';

  const hPx = Number(evalState.heightNorm || 0.28) * H;
  const lwOuter = clamp(hPx * 0.0138, 3.2, 9.6);
  const lwInner = lwOuter * 0.44;
  const facing = (evalState.facing ?? 1) >= 0 ? 1 : -1;
  const viewMode = String(opts.view || 'three_quarter');

  const toPx = (pt) => [pt[0] * W, pt[1] * H];
  const hipPx = toPx(evalState.pelvisCenter || evalState.hipWorld);
  const neckPx = toPx(evalState.neckWorld);
  const headPx = toPx(evalState.headWorld);
  const lLeg = evalState.leftLegWorld.map(toPx);
  const rLeg = evalState.rightLegWorld.map(toPx);
  const lArm = evalState.leftArmWorld.map(toPx);
  const rArm = evalState.rightArmWorld.map(toPx);

  const headRatio = Number(spec.proportions?.head_to_height_ratio ?? 0.22);
  const headR = hPx * headRatio * 0.56;
  const shWidth = headR * Number(spec.proportions?.shoulder_to_head_width ?? 1.38) * (viewMode === 'profile' ? 0.58 : 0.88);
  const gk = String(wd.garment_kind || '');
  const hStyle = String(spec.hair_style || '');

  // 1. Soft Directional Cast Ground Shadow
  const shadowCx = 0.5 * (lLeg[2][0] + rLeg[2][0]);
  const shadowCy = Math.max(lLeg[2][1], rLeg[2][1]);
  g.save();
  g.beginPath();
  g.ellipse(shadowCx + 6, shadowCy + 2, shWidth * 1.22, Math.max(5.5, headR * 0.23), 0, 0, Math.PI * 2);
  g.fillStyle = 'rgba(26, 20, 18, 0.34)';
  g.fill();
  g.restore();

  const anchoredHeadY = Math.max(headPx[1], neckPx[1] - headR * 1.04);
  const hairSway = Number(evalState.hairSwayRad || 0) * headR * 0.65;
  const clothLag = Number(evalState.secondary?.clothSwayNorm || 0) * W * 1.30;

  // Back hair silhouette before torso/neck when not rear_three_quarter
  if (viewMode !== 'rear_three_quarter' && (hStyle.includes('bob') || hStyle.includes('waves') || hStyle.includes('updo'))) {
    g.save();
    g.translate(headPx[0], anchoredHeadY);
    g.beginPath();
    g.ellipse(hairSway * 0.25, headR * 0.26, headR * 1.12, headR * 0.78, 0, 0, Math.PI * 2);
    g.fillStyle = hr.shadow;
    g.fill();
    g.lineWidth = lwOuter * 0.88;
    g.strokeStyle = ink;
    g.stroke();
    g.restore();
  }

  // Flowing Scarf / Capelet Secondary Motion
  if ((wd.accessories || []).some((a) => String(a).includes('scarf')) || gk.includes('tunic')) {
    const scPts = sampleQuadBezier2D(
      [neckPx[0] - facing * headR * 0.15, neckPx[1] + headR * 0.10],
      [neckPx[0] - facing * shWidth * 0.85 + clothLag * 0.5, neckPx[1] + headR * 0.24],
      [neckPx[0] - facing * shWidth * 1.38 + clothLag, neckPx[1] + headR * 0.72],
      8,
    ).concat([
      [neckPx[0] - facing * shWidth * 1.12 + clothLag * 1.1, neckPx[1] + headR * 1.18],
      [neckPx[0] - facing * headR * 0.12, neckPx[1] + headR * 0.58],
    ]);
    fillCelPolygon(g, scPts, wd.secondary_hex, null, '#FFFDF6', ink, lwOuter * 0.88, -facing, true);
  }

  // 2. Curved Draped Trouser / Calf Legs + Stylized Sneakers / Footwear
  const standLegSpan = Math.max(hPx * 0.20, shadowCy - hipPx[1]);
  const isBareCalf = String(spec.niche || '').includes('roman') && !gk.includes('toga') && !gk.includes('stola');
  const pantsHex = wd.pants_hex || '#3B4F6B';
  const pantsShHex = wd.pants_shadow_hex || '#28364A';

  const drawLegV2 = (chain, isFar) => {
    const [Hpt, _rawKpt, Fpt] = chain;
    const [, Kpt] = solvePixelLimb2D(Hpt, Fpt, standLegSpan * 0.52, standLegSpan * 0.515, -facing, false);
    const anklePt = [Fpt[0], Fpt[1] - headR * 0.14];
    const legFill = isBareCalf ? (isFar ? sk.shadow : sk.base) : (isFar ? pantsShHex : pantsHex);
    const legSh = isBareCalf ? sk.shadow : pantsShHex;
    const wHip = headR * (isBareCalf ? 0.50 : 0.62);
    const wKnee = headR * (isBareCalf ? 0.44 : 0.58);
    const wAnk = headR * (isBareCalf ? 0.30 : 0.42);
    const legShape = buildCurvedTaperedLimb2D(Hpt, Kpt, anklePt, wHip, wKnee, wAnk, 10);
    fillCelPolygon(g, legShape.poly, legFill, isFar ? null : legSh, isFar ? null : '#8FA8C8', ink, lwOuter * 0.90, -facing, true);

    if (!isBareCalf) {
      // Rolled trouser cuff band + curved knee crease
      fillCelPolygon(
        g,
        [
          [anklePt[0] - wAnk * 0.58, anklePt[1] - headR * 0.12],
          [anklePt[0] + wAnk * 0.58, anklePt[1] - headR * 0.12],
          [anklePt[0] + wAnk * 0.58, anklePt[1] + headR * 0.03],
          [anklePt[0] - wAnk * 0.58, anklePt[1] + headR * 0.03],
        ],
        String(wd.footwear || '').includes('cuffed') ? wd.trim_hex : pantsShHex,
        null,
        null,
        ink,
        lwOuter * 0.72,
      );
      drawVariableStroke(g, [[Kpt[0] - wKnee * 0.24, Kpt[1] - 3], [Kpt[0] + wKnee * 0.20, Kpt[1] + 4]], inkIn, lwInner, true, true);
    }

    // Stylized 2D Sneaker / Trainer / Sandal anchored to Fpt
    const shoePts = [
      [Fpt[0] - facing * headR * 0.24, Fpt[1] - headR * 0.20],
      [Fpt[0] + facing * headR * 0.26, Fpt[1] - headR * 0.20],
      [Fpt[0] + facing * headR * 0.58, Fpt[1] - headR * 0.04],
      [Fpt[0] + facing * headR * 0.54, Fpt[1]],
      [Fpt[0] - facing * headR * 0.30, Fpt[1]],
    ];
    fillCelPolygon(g, shoePts, wd.accessory_hex, null, '#FFF8EA', ink, lwOuter * 0.85, -facing);
    if (String(wd.footwear || '').includes('sneaker') || String(wd.footwear || '').includes('trainer')) {
      drawVariableStroke(g, [[Fpt[0] - facing * headR * 0.28, Fpt[1] - 2.5], [Fpt[0] + facing * headR * 0.52, Fpt[1] - 2.5]], '#FAF8F2', Math.max(2.5, lwOuter * 0.62), false);
    }
  };

  // 3. Curved Sleeved Upper Arm + Rounded Elbow + Tapered Forearm + Articulated Hand
  const drawArmV2 = (chain, isFar, handShape) => {
    const [Spt, _rawEpt, rawHnd] = chain;
    const [, Ept, Hnd] = solvePixelLimb2D(
      Spt,
      rawHnd,
      hPx * 0.168,
      hPx * 0.168,
      facing,
      handShape !== 'locked_grip',
    );
    const sleeveCol = isFar ? wd.primary_shadow_hex : wd.primary_hex;
    const armCol = isFar ? sk.shadow : sk.base;

    const cuffPt = [
      Ept[0] + (Hnd[0] - Ept[0]) * 0.36,
      Ept[1] + (Hnd[1] - Ept[1]) * 0.36,
    ];
    const foreMid = [
      0.5 * (cuffPt[0] + Hnd[0]) + facing * headR * 0.04,
      0.5 * (cuffPt[1] + Hnd[1]) + headR * 0.04,
    ];
    const foreShape = buildCurvedTaperedLimb2D(cuffPt, foreMid, Hnd, headR * 0.36, headR * 0.31, headR * 0.22, 8);
    fillCelPolygon(g, foreShape.poly, armCol, isFar ? null : sk.shadow, null, ink, lwOuter * 0.82, -facing);

    const slShape = buildCurvedTaperedLimb2D(Spt, Ept, cuffPt, headR * 0.62, headR * 0.58, headR * 0.48, 10);
    fillCelPolygon(g, slShape.poly, sleeveCol, isFar ? null : wd.primary_shadow_hex, isFar ? null : wd.primary_rim_hex, ink, lwOuter * 0.88, -facing, true);
    // Contrasting sleeve cuff trim + elbow crease
    drawVariableStroke(g, [slShape.left[slShape.left.length - 1], slShape.right[slShape.right.length - 1]], wd.trim_hex, lwOuter * 0.96, false);
    drawVariableStroke(g, [[Ept[0] - headR * 0.10, Ept[1] - 3], [Ept[0] + headR * 0.10, Ept[1] + 4]], inkIn, lwInner, true, true);

    drawV2ArticulatedHandCanvas(g, Hnd, Ept, headR, isFar ? 'relaxed' : handShape, armCol, sk.shadow, ink, inkIn, lwOuter, facing);
  };

  drawLegV2(lLeg, true);
  drawArmV2(lArm, true, evalState.handShapeLeft || 'relaxed');
  if (viewMode === 'rear_three_quarter') {
    drawArmV2(rArm, true, opts.handOverride || evalState.handShapeRight || 'relaxed');
  }

  // 4. Multi-Layer Curved Flared Torso Garment + Inner Striped/Crew Tee + Lapels & Creases
  const hemDrop = (gk.includes('tunic') || gk.includes('stola') || gk.includes('coat') || gk.includes('smock'))
    ? headR * 0.78
    : headR * 0.30;
  const flare = 1.18;
  const topY = neckPx[1] + headR * 0.12;
  const botY = hipPx[1] + hemDrop;
  const swayShift = clothLag * 0.22;

  const leftSeam = sampleQuadBezier2D(
    [neckPx[0] - shWidth * 0.72, topY],
    [0.5 * (neckPx[0] + hipPx[0]) - shWidth * 0.74 + swayShift * 0.4, 0.5 * (topY + botY)],
    [hipPx[0] - shWidth * 0.70 * flare + swayShift, botY],
    8,
  );
  const botHem = sampleQuadBezier2D(
    [hipPx[0] - shWidth * 0.70 * flare + swayShift, botY],
    [hipPx[0] + swayShift, botY + headR * 0.12],
    [hipPx[0] + shWidth * 0.70 * flare + swayShift, botY],
    8,
  );
  const rightSeam = sampleQuadBezier2D(
    [hipPx[0] + shWidth * 0.70 * flare + swayShift, botY],
    [0.5 * (neckPx[0] + hipPx[0]) + shWidth * 0.74 + swayShift * 0.4, 0.5 * (topY + botY)],
    [neckPx[0] + shWidth * 0.72, topY],
    8,
  );
  const torsoPoly = leftSeam.concat(botHem.slice(1)).concat(rightSeam.slice(1));
  fillCelPolygon(g, torsoPoly, wd.primary_hex, wd.primary_shadow_hex, wd.primary_rim_hex, ink, lwOuter, -facing, true);

  if (viewMode !== 'rear_three_quarter') {
    const isOpenJacket = gk.includes('windbreaker') || gk.includes('parka') || gk.includes('overshirt') || gk.includes('cardigan') || gk.includes('coat') || gk.includes('blazer');
    if (isOpenJacket) {
      const cShift = facing * shWidth * (viewMode === 'profile' ? 0.30 : 0.10);
      const inW = shWidth * (viewMode === 'profile' ? 0.20 : 0.26);
      const inPoly = [
        [neckPx[0] + cShift - inW, topY + 2],
        [neckPx[0] + cShift + inW, topY + 2],
        [hipPx[0] + cShift + inW * 0.92, hipPx[1] + headR * 0.12],
        [hipPx[0] + cShift - inW * 0.92, hipPx[1] + headR * 0.12],
      ];
      fillCelPolygon(g, inPoly, wd.secondary_hex, null, null, inkIn, lwInner * 1.1, -facing);
      if (gk.includes('striped') || (wd.accessories || []).some((a) => String(a).includes('striped'))) {
        for (let si = 0; si < 3; si++) {
          const syS = lerp(topY + headR * 0.26, hipPx[1], si / 3);
          drawVariableStroke(g, [[neckPx[0] + cShift - inW * 0.88, syS], [neckPx[0] + cShift + inW * 0.88, syS]], wd.trim_hex, Math.max(2.2, lwInner * 1.25), false);
        }
      }
      // Folded jacket collar lapels
      fillCelPolygon(
        g,
        [
          [neckPx[0] + cShift - inW, topY],
          [neckPx[0] + cShift - inW * 1.75, topY + headR * 0.36],
          [neckPx[0] + cShift - inW * 0.95, topY + headR * 0.62],
        ],
        wd.trim_hex,
        null,
        null,
        ink,
        lwInner * 1.2,
      );
      if (viewMode !== 'profile') {
        fillCelPolygon(
          g,
          [
            [neckPx[0] + cShift + inW, topY],
            [neckPx[0] + cShift + inW * 1.75, topY + headR * 0.36],
            [neckPx[0] + cShift + inW * 0.95, topY + headR * 0.62],
          ],
          wd.trim_hex,
          null,
          null,
          ink,
          lwInner * 1.2,
        );
      }
    } else {
      // Cross-collar / apron / belt sash
      drawVariableStroke(g, [[neckPx[0] - shWidth * 0.30, topY + 2], [neckPx[0] + facing * headR * 0.14, topY + headR * 0.64]], wd.trim_hex, lwOuter * 0.95, false);
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
      );
    }
  } else {
    // Rear 3/4 back yoke & center seam
    drawVariableStroke(g, [[neckPx[0] - shWidth * 0.65, topY + headR * 0.38], [neckPx[0], topY + headR * 0.46], [neckPx[0] + shWidth * 0.65, topY + headR * 0.38]], inkIn, lwInner * 1.2, false);
  }

  // Curved interior garment tension creases + hem accent
  drawVariableStroke(g, botHem, wd.trim_hex, lwOuter * 0.85, false);
  drawVariableStroke(g, [[neckPx[0] - shWidth * 0.34, topY + headR * 0.48], [hipPx[0] - shWidth * 0.44, botY - headR * 0.16]], inkIn, lwInner, true, true);
  drawVariableStroke(g, [[neckPx[0] + shWidth * 0.28, topY + headR * 0.52], [hipPx[0] + shWidth * 0.38, botY - headR * 0.14]], inkIn, lwInner, true, true);

  drawLegV2(rLeg, false);
  if (viewMode !== 'rear_three_quarter') {
    drawArmV2(rArm, false, opts.handOverride || evalState.handShapeRight || 'relaxed');
  }

  // 5. Connected Neck + Sculpted Cheek/Jaw Head + Curved Cel Shadow + 7 Expressions
  drawVariableStroke(g, [[headPx[0], anchoredHeadY + headR * 0.64], [neckPx[0], neckPx[1] + headR * 0.22]], ink, headR * 0.58, false);
  drawVariableStroke(g, [[headPx[0], anchoredHeadY + headR * 0.64], [neckPx[0], neckPx[1] + headR * 0.22]], sk.shadow, headR * 0.42, false);

  g.save();
  g.translate(headPx[0], anchoredHeadY);
  g.rotate(clamp(Number(evalState.secondary?.headLagRad || 0), -0.15, 0.15));

  const cShape = String(spec.proportions?.cranium_shape || 'rounded_tapered_jaw');
  const rxHead = headR * (viewMode === 'profile' ? 0.88 : (cShape.includes('soft_cheek') ? 0.99 : 0.93));
  g.beginPath();
  g.ellipse(0, 0, rxHead, headR, 0, 0, Math.PI * 2);
  g.fillStyle = sk.base;
  g.fill();
  // Curved crescent cel shadow on away/lower side of face (Ref 1/2/3 volumetric cel shadow)
  g.save();
  g.clip();
  g.beginPath();
  g.arc(-facing * headR * 0.52, headR * 0.24, headR * 0.92, 0, Math.PI * 2);
  g.fillStyle = sk.shadow;
  g.fill();
  g.beginPath();
  g.arc(facing * headR * 0.35, -headR * 0.22, headR * 0.88, -Math.PI * 0.45, Math.PI * 0.22);
  g.strokeStyle = sk.rim;
  g.lineWidth = Math.max(3, lwOuter * 0.85);
  g.stroke();
  g.restore();

  g.beginPath();
  g.ellipse(0, 0, rxHead, headR, 0, 0, Math.PI * 2);
  g.lineWidth = lwOuter;
  g.strokeStyle = ink;
  g.stroke();

  if (viewMode === 'rear_three_quarter') {
    // Ear sliver + full sculpted back hair covering rear cranium!
    g.beginPath();
    g.ellipse(facing * headR * 0.60, headR * 0.10, headR * 0.16, headR * 0.23, 0, 0, Math.PI * 2);
    g.fillStyle = sk.base;
    g.fill();
    g.stroke();
    const rearHairPts = [
      [-headR * 1.02, headR * 0.52],
      [-headR * 1.06, -headR * 0.65],
      [-headR * 0.42, -headR * 1.12],
      [headR * 0.45, -headR * 1.08],
      [facing * headR * 0.64, headR * 0.42],
      [-facing * headR * 0.25, headR * 0.78],
    ];
    fillCelPolygon(g, rearHairPts, hr.base, hr.shadow, hr.highlight, ink, lwOuter * 0.95, -facing, true);
    g.restore();
    return;
  }

  // Ear
  const earX = -facing * headR * (viewMode === 'profile' ? 0.24 : 0.84);
  g.beginPath();
  g.ellipse(earX, headR * 0.08, headR * 0.16, headR * 0.22, 0, 0, Math.PI * 2);
  g.fillStyle = sk.base;
  g.fill();
  g.lineWidth = lwOuter * 0.82;
  g.stroke();

  const expr = opts.expressionOverride || evalState.modernExpression || 'neutral_attentive';
  const talkVal = Number(opts.talk || 0);
  const eyeCenters =
    viewMode === 'profile'
      ? [[facing * headR * 0.36, -headR * 0.05, 0.94]]
      : viewMode === 'front'
        ? [[-headR * 0.35, -headR * 0.04, 1.02], [headR * 0.35, -headR * 0.04, 1.02]]
        : [[-facing * headR * 0.14, -headR * 0.04, 1.04], [facing * headR * 0.44, -headR * 0.05, 0.78]];

  for (let ei = 0; ei < eyeCenters.length; ei++) {
    const [ex, ey, sc] = eyeCenters[ei];
    const ew = headR * 0.21 * sc;
    const eh = headR * (expr === 'wide_shock' ? 0.29 : expr === 'deadpan_disbelief' ? 0.14 : 0.21);
    if (expr === 'joyful_laugh' || expr === 'warm_relief_smile') {
      // Warm cheek blush
      g.beginPath();
      g.ellipse(ex, ey + headR * 0.24, ew * 0.95, headR * 0.08, 0, 0, Math.PI * 2);
      g.fillStyle = alpha(sk.blush || '#E67B6B', 0.48);
      g.fill();
    }
    if (expr === 'joyful_laugh') {
      drawVariableStroke(g, [[ex - ew * 1.06, ey + headR * 0.05], [ex, ey - headR * 0.12], [ex + ew * 1.06, ey + headR * 0.04]], ink, lwOuter * 1.18);
    } else {
      g.beginPath();
      g.ellipse(ex, ey, ew, eh, 0, 0, Math.PI * 2);
      g.fillStyle = '#FCFAF6';
      g.fill();
      g.lineWidth = lwOuter * 0.78;
      g.strokeStyle = ink;
      g.stroke();

      const pr = ew * (expr === 'wide_shock' ? 0.32 : 0.56);
      g.beginPath();
      g.arc(ex + facing * ew * 0.15, ey, pr, 0, Math.PI * 2);
      g.fillStyle = ink;
      g.fill();
      g.beginPath();
      g.arc(ex + facing * ew * 0.04 - pr * 0.32, ey - pr * 0.36, Math.max(1.6, pr * 0.38), 0, Math.PI * 2);
      g.fillStyle = '#FFFFFF';
      g.fill();
      // Bold upper eyelash stroke
      drawVariableStroke(g, [[ex - ew * 1.06, ey - eh * 0.32], [ex, ey - eh * 1.04], [ex + ew * 1.06, ey - eh * 0.28]], ink, lwOuter * 1.08);
    }
    const by = ey - eh - headR * (expr === 'wide_shock' ? 0.16 : 0.09);
    const tilt = (expr === 'determined_focus' || expr === 'strained_exertion')
      ? (ei === 0 ? headR * 0.08 : -headR * 0.08)
      : (expr === 'wide_shock' ? -headR * 0.09 : 0);
    drawVariableStroke(g, [[ex - ew * 1.1, by - tilt], [ex, by - Math.abs(tilt) * 0.4 - headR * 0.02], [ex + ew * 1.1, by + tilt]], hr.base, lwOuter * 1.2);
    if (spec.has_glasses) {
      g.beginPath();
      g.roundRect(ex - ew * 1.38, ey - eh * 1.28, ew * 2.76, eh * 2.56, 4);
      g.lineWidth = lwInner * 1.25;
      g.strokeStyle = '#2B3544';
      g.stroke();
    }
  }

  // Sculpted Nose
  const nx = facing * headR * (viewMode === 'profile' ? 0.92 : 0.24);
  if (viewMode === 'profile') {
    fillCelPolygon(g, [[nx - facing * headR * 0.18, -headR * 0.12], [nx + facing * headR * 0.18, headR * 0.12], [nx - facing * headR * 0.14, headR * 0.21]], sk.base, null, null, ink, lwOuter * 0.85);
  } else {
    drawVariableStroke(g, [[nx - facing * headR * 0.10, -headR * 0.08], [nx + facing * headR * 0.13, headR * 0.13], [nx - facing * headR * 0.05, headR * 0.19]], inkIn, lwInner * 1.18);
  }

  // Expressive Mouth with Tooth + Tongue Cel Planes on Open Laugh / Shock / Speech!
  const mx = facing * headR * (viewMode === 'profile' ? 0.50 : 0.15);
  const my = headR * 0.42;
  const mw = headR * 0.33;
  if (expr === 'joyful_laugh') {
    const dMouth = sampleQuadBezier2D([mx - mw, my - headR * 0.06], [mx, my - headR * 0.09], [mx + mw, my - headR * 0.06], 6)
      .concat(sampleQuadBezier2D([mx + mw, my - headR * 0.06], [mx, my + headR * 0.40], [mx - mw, my - headR * 0.06], 8));
    fillCelPolygon(g, dMouth, '#3E1418', null, null, ink, lwOuter * 0.80);
    g.save();
    g.beginPath();
    for (let i = 0; i < dMouth.length; i++) {
      if (i === 0) g.moveTo(dMouth[i][0], dMouth[i][1]);
      else g.lineTo(dMouth[i][0], dMouth[i][1]);
    }
    g.closePath();
    g.clip();
    g.fillStyle = '#FCFAF6';
    g.fillRect(mx - mw * 0.58, my - headR * 0.10, mw * 1.16, headR * 0.12);
    g.beginPath();
    g.arc(mx, my + headR * 0.24, mw * 0.65, Math.PI, Math.PI * 2);
    g.fillStyle = '#E26862';
    g.fill();
    g.restore();
  } else if (talkVal > 0.18 || expr === 'wide_shock') {
    const openH = headR * (expr === 'wide_shock' ? 0.23 : 0.09 + talkVal * 0.15);
    g.beginPath();
    g.ellipse(mx, my, mw * 0.68, openH, 0, 0, Math.PI * 2);
    g.fillStyle = '#3E1418';
    g.fill();
    g.lineWidth = lwOuter * 0.76;
    g.strokeStyle = ink;
    g.stroke();
    g.beginPath();
    g.arc(mx, my + openH * 0.35, mw * 0.42, 0, Math.PI);
    g.fillStyle = '#E26862';
    g.fill();
  } else if (expr === 'strained_exertion') {
    g.beginPath();
    g.roundRect(mx - mw * 0.88, my - headR * 0.08, mw * 1.76, headR * 0.17, 4);
    g.fillStyle = '#FFFFFF';
    g.fill();
    g.lineWidth = lwOuter * 0.75;
    g.strokeStyle = ink;
    g.stroke();
    drawVariableStroke(g, [[mx - mw * 0.80, my], [mx + mw * 0.80, my]], inkIn, lwInner, false);
  } else if (expr === 'warm_relief_smile') {
    drawVariableStroke(g, sampleQuadBezier2D([mx - mw * 0.82, my - headR * 0.04], [mx, my + headR * 0.16], [mx + mw * 0.82, my - headR * 0.04], 8), ink, lwOuter * 0.92);
  } else if (expr === 'deadpan_disbelief') {
    drawVariableStroke(g, [[mx - mw * 0.72, my + 2], [mx, my - 2], [mx + mw * 0.72, my + 2]], ink, lwOuter * 0.88);
  } else {
    drawVariableStroke(g, sampleQuadBezier2D([mx - mw * 0.72, my - 2], [mx, my + headR * 0.09], [mx + mw * 0.74, my - 3], 8), ink, lwOuter * 0.88);
  }

  // Distinct Hair Silhouettes (Mina's bob + star clip vs Bao's tousled layered waves!)
  if (hStyle.includes('bob')) {
    const bobPts = [
      [-headR * 1.02, headR * 0.16],
      [-headR * 1.00, -headR * 0.76],
      [-headR * 0.46, -headR * 1.18],
      [headR * 0.38 + hairSway * 0.5, -headR * 1.16],
      [headR * 0.96, -headR * 0.70],
      [headR * 1.00, headR * 0.06],
      [headR * 0.70, -headR * 0.42],
      [headR * 0.18, -headR * 0.34],
      [-headR * 0.12, -headR * 0.56],
      [-headR * 0.64, -headR * 0.32],
    ];
    fillCelPolygon(g, bobPts, hr.base, hr.shadow, hr.highlight, ink, lwOuter * 0.94, -facing, true);
    // Signature ochre hair clip on temple
    fillCelPolygon(
      g,
      [[-facing * headR * 0.74, -headR * 0.44], [-facing * headR * 0.40, -headR * 0.48], [-facing * headR * 0.38, -headR * 0.32], [-facing * headR * 0.72, -headR * 0.28]],
      wd.accessory_hex,
      null,
      '#FFF5CC',
      ink,
      lwInner * 1.15,
    );
  } else if (hStyle.includes('waves') || hStyle.includes('curly')) {
    const wavePts = [
      [-headR * 0.98, -headR * 0.16],
      [-headR * 0.95, -headR * 0.88],
      [-headR * 0.42 + hairSway * 0.4, -headR * 1.32],
      [-headR * 0.08, -headR * 1.12],
      [headR * 0.36 + hairSway, -headR * 1.36],
      [headR * 0.94, -headR * 0.86],
      [headR * 0.96, -headR * 0.26],
      [headR * 0.46, -headR * 0.62],
      [-headR * 0.18, -headR * 0.54],
      [-headR * 0.62, -headR * 0.46],
    ];
    fillCelPolygon(g, wavePts, hr.base, hr.shadow, hr.highlight, ink, lwOuter * 0.94, -facing, true);
  } else {
    const hairPts = [
      [-headR * 0.96, -headR * 0.18],
      [-headR * 0.78, -headR * 1.06],
      [facing * headR * 0.22 + hairSway, -headR * 1.24],
      [headR * 0.92, -headR * 0.82],
      [headR * 0.95, -headR * 0.30],
      [headR * 0.32, -headR * 0.58],
      [-headR * 0.30, -headR * 0.52],
    ];
    fillCelPolygon(g, hairPts, hr.base, hr.shadow, hr.highlight, ink, lwOuter * 0.92, -facing, true);
  }

  g.restore();
}

export function drawModernExpressiveActor(g, actorSpec, evalState, opts = {}) {
  if (String(actorSpec?.style_id || '').endsWith('.v2')) {
    drawModernExpressiveActorV2(g, actorSpec, evalState, opts);
    return;
  }
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

  // ---------- KH-01.R1 Reference-Grounded v2 Park Kite Close-Up & OTS Inserts ----------

  if (insertKind === 'kite_macro_ribbon_hook') {
    // SHOT 1 (0.0-3.0s) HOOK: Macro close-up of Mina's tiny hands threading bright red ribbon through
    // handcrafted origami dragon kite; sudden wind gust catches paper; Mina's delighted smile shifts to shock!
    const gustK = smooth01((u - 0.42) / 0.46);
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'macro' }, { wind_strength: 0.30 + gustK * 0.70 });

    const minaSpec = charSpecs.mina || Object.values(charSpecs)[0];
    const minaExpr = u < 0.46 ? 'joyful_laugh' : 'wide_shock';
    drawModernExpressiveActor(
      g,
      minaSpec,
      {
        heightNorm: 0.78,
        facing: -1,
        root: [0.70, 1.24],
        pelvisCenter: [0.70, 0.96],
        hipWorld: [0.70, 0.96],
        neckWorld: [0.69, 0.54],
        headWorld: [0.68, 0.34 - gustK * 0.02],
        leftLegWorld: [[0.68, 0.96], [0.68, 1.10], [0.68, 1.24]],
        rightLegWorld: [[0.72, 0.96], [0.72, 1.10], [0.72, 1.24]],
        leftArmWorld: [[0.64, 0.56], [0.56, 0.68], [0.46, 0.60 - gustK * 0.04]],
        rightArmWorld: [[0.74, 0.56], [0.62, 0.68], [0.50 - gustK * 0.05, 0.62 - gustK * 0.06]],
        modernExpression: minaExpr,
        handShapeLeft: gustK > 0.35 ? 'spread_shock' : 'locked_grip',
        handShapeRight: gustK > 0.35 ? 'open_reach' : 'pointing',
        hairSwayRad: -0.24 * gustK,
        secondary: { clothSwayNorm: 0.06 * gustK, headLagRad: 0.05 * gustK },
      },
      { view: 'three_quarter', expressionOverride: minaExpr },
    );

    // Park bench slatted corner in lower-left foreground
    fillCelPolygon(g, [[0, H * 0.74], [W * 0.56, H * 0.74], [W * 0.52, H], [0, H]], '#D89B62', '#A46E3C', '#F5C592', '#211612', 6.0, -1, true);

    // Handcrafted Origami Dragon Kite lifting off bench as wind catches paper!
    const kiteX = lerp(W * 0.35, W * 0.24, gustK);
    const kiteY = lerp(H * 0.60, H * 0.38, Math.pow(gustK, 1.25));
    const kiteRot = lerp(-0.18, -0.46, gustK);
    drawModernProp(g, 'origami_dragon_kite', kiteX, kiteY, 2.55, { rot: kiteRot, globalT });

    // Continuous crimson ribbon threaded through bridle eye into Mina's fingers & spool
    const spoolX = W * 0.48;
    const spoolY = H * 0.70;
    drawModernProp(g, 'kite_spool', spoolX, spoolY, 1.85, { rot: gustK * 1.4, globalT });
    const ribPts = sampleQuadBezier2D([spoolX, spoolY - 8], [lerp(W * 0.42, W * 0.36, gustK), lerp(H * 0.66, H * 0.46, gustK)], [kiteX + 18, kiteY + 14], 14);
    drawVariableStroke(g, ribPts, '#211612', 8.5, false);
    drawVariableStroke(g, ribPts, '#DC392D', 5.2, false);

    if (gustK > 0.08) {
      g.save();
      g.strokeStyle = `rgba(255, 250, 232, ${0.78 * gustK})`;
      g.lineWidth = 4.5;
      for (let wi = 0; wi < 4; wi++) {
        const wy = H * (0.34 + wi * 0.09);
        const wx = lerp(W * 0.76, W * 0.12, clamp(gustK * 1.25 - wi * 0.08, 0, 1));
        g.beginPath();
        g.moveTo(wx + 210, wy);
        g.bezierCurveTo(wx + 110, wy - 24, wx + 40, wy + 18, wx - 45, wy - 8);
        g.stroke();
      }
      g.restore();
    }
    return true;
  }

  if (insertKind === 'kite_slip_fingers_insert') {
    // SHOT 3 Segment 1: Tactile physical mechanism — taut crimson string yanked from Mina's straining fingers!
    const slipK = smooth01(clamp((u - 0.18) / 0.62, 0, 1));
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.92 });

    // Mina's coral windbreaker sleeve + curved forearm + splayed reaching hand in left foreground
    const wristPt = [lerp(W * 0.36, W * 0.42, slipK), lerp(H * 0.64, H * 0.56, slipK)];
    const elPt = [W * 0.16, H * 0.86];
    const fore = buildCurvedTaperedLimb2D(elPt, [W * 0.27, H * 0.75], wristPt, 92, 74, 52, 10);
    fillCelPolygon(g, fore.poly, '#F0C19E', '#C89270', '#FFF0DF', '#211612', 7.5, -1, true);
    const sleeve = buildCurvedTaperedLimb2D([-40, H * 1.06], [W * 0.10, H * 0.92], [W * 0.24, H * 0.78], 168, 146, 118, 10);
    fillCelPolygon(g, sleeve.poly, '#E0533C', '#A83725', '#FF8A75', '#211612', 8.0, -1, true);
    drawVariableStroke(g, [sleeve.left[sleeve.left.length - 1], sleeve.right[sleeve.right.length - 1]], '#2D7D90', 11.0, false);
    drawV2ArticulatedHandCanvas(g, wristPt, elPt, 195, slipK > 0.28 ? 'open_reach' : 'locked_grip', '#F0C19E', '#C89270', '#211612', '#3A2821', 7.5, 1);

    // Spinning wooden spool & taut crimson string pulling away toward upper-right sky!
    const spX = lerp(wristPt[0] + 54, W * 0.66, slipK);
    const spY = lerp(wristPt[1] - 18, H * 0.42, slipK);
    const kiteX = lerp(W * 0.74, W * 0.86, slipK);
    const kiteY = lerp(H * 0.26, H * 0.18, slipK);
    const linePts = sampleQuadBezier2D([spX, spY], [lerp(spX, kiteX, 0.5), lerp(spY, kiteY, 0.5) - 18], [kiteX, kiteY], 12);
    drawVariableStroke(g, linePts, '#211612', 7.0, false);
    drawVariableStroke(g, linePts, '#DC392D', 4.4, false);
    drawModernProp(g, 'kite_spool', spX, spY, 2.2, { rot: slipK * 5.2, globalT });
    drawModernProp(g, 'origami_dragon_kite', kiteX, kiteY, 1.65, { rot: 0.38, globalT });
    if (slipK > 0.22 && slipK < 0.75) {
      fxRing(g, u, 0.22, wristPt[0] + 48, wristPt[1] - 14, 118, { dur: 0.42, w: 5, color: 'rgba(255, 242, 196, 0.82)' });
    }
    return true;
  }

  if (insertKind === 'kite_close_branch_unhook') {
    // SHOT 6 Segment 2: Tactile close-up of Mina's hand gently unhooking snagged crimson ribbon from ornamental branch!
    const freeK = smooth01(clamp((u - 0.15) / 0.68, 0, 1));
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.35 });

    // Bark-grained ornamental tree branch across upper-left to center
    const brShape = buildCurvedTaperedLimb2D([W * 0.96, H * 0.34], [W * 0.62, H * 0.42], [W * 0.30, H * 0.46], 68, 44, 22, 12);
    fillCelPolygon(g, brShape.poly, '#734E36', '#4F3422', '#9C7152', '#211612', 6.5, -1, true);
    for (const [lx, ly] of [[W * 0.36, H * 0.40], [W * 0.52, H * 0.36]]) {
      fillCelPolygon(g, [[lx, ly], [lx + 42, ly - 24], [lx + 68, ly - 4], [lx + 28, ly + 14]], '#4E8B52', '#2F663B', '#88B969', '#211612', 4.5);
    }

    // Origami dragon kite gently lifted free as ribbon unhooks cleanly
    const kiteX = lerp(W * 0.54, W * 0.46, freeK);
    const kiteY = lerp(H * 0.56, H * 0.62, freeK);
    drawModernProp(g, 'origami_dragon_kite', kiteX, kiteY, 2.35, { rot: lerp(0.32, -0.08, freeK), globalT });

    // Snagged -> freed crimson ribbon loop
    const loopAnchorY = lerp(H * 0.44, H * 0.55, freeK);
    const ribPts = sampleQuadBezier2D([W * 0.44, loopAnchorY], [W * 0.48, H * 0.52], [kiteX, kiteY - 18], 10);
    drawVariableStroke(g, ribPts, '#211612', 8.0, false);
    drawVariableStroke(g, ribPts, '#DC392D', 5.0, false);

    // Mina's reaching hand unhooking the ribbon loop carefully
    const wristPt = [lerp(W * 0.28, W * 0.39, freeK), lerp(H * 0.72, loopAnchorY + 26, freeK)];
    const elPt = [W * 0.10, H * 0.98];
    const fore = buildCurvedTaperedLimb2D(elPt, [W * 0.20, H * 0.86], wristPt, 84, 68, 48, 10);
    fillCelPolygon(g, fore.poly, '#F0C19E', '#C89270', '#FFF0DF', '#211612', 7.0);
    const slv = buildCurvedTaperedLimb2D([-20, H * 1.08], [W * 0.08, H * 0.96], [W * 0.19, H * 0.85], 154, 132, 106, 8);
    fillCelPolygon(g, slv.poly, '#E0533C', '#A83725', '#FF8A75', '#211612', 7.5);
    drawV2ArticulatedHandCanvas(g, wristPt, elPt, 180, freeK > 0.45 ? 'locked_grip' : 'pointing', '#F0C19E', '#C89270', '#211612', '#3A2821', 7.0, 1);
    return true;
  }

  if (insertKind === 'kite_close_knot_repair') {
    // SHOT 7 (22.0-26.0s) RELIEF: Over-the-shoulder / close-up of Mina tying one careful knot in the crimson ribbon
    // against origami paper folds while Bao smiles warmly beside her!
    const knotK = smooth01(clamp(u / 0.75, 0, 1));
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.22, warm_sun_boost: 0.5 });

    const minaSpec = charSpecs.mina || Object.values(charSpecs)[0];
    const baoSpec = charSpecs.bao || Object.values(charSpecs)[1] || minaSpec;

    // Bao smiling warmly in right midground (taller caring older friend!)
    drawModernExpressiveActor(
      g,
      baoSpec,
      {
        heightNorm: 0.78,
        facing: -1,
        root: [0.74, 1.24],
        pelvisCenter: [0.74, 0.94],
        hipWorld: [0.74, 0.94],
        neckWorld: [0.73, 0.50],
        headWorld: [0.72, 0.30],
        leftLegWorld: [[0.72, 0.94], [0.72, 1.09], [0.72, 1.24]],
        rightLegWorld: [[0.76, 0.94], [0.76, 1.09], [0.76, 1.24]],
        leftArmWorld: [[0.68, 0.54], [0.60, 0.68], [0.55, 0.64]],
        rightArmWorld: [[0.78, 0.54], [0.68, 0.68], [0.58, 0.66]],
        modernExpression: u > 0.55 ? 'joyful_laugh' : 'warm_relief_smile',
        handShapeLeft: 'locked_grip',
        handShapeRight: 'open_reach',
        hairSwayRad: 0.04,
        secondary: { clothSwayNorm: 0.01, headLagRad: -0.03 },
      },
      { view: 'three_quarter' },
    );

    // Mina focused -> warm relief smile on left midground
    const mExpr = u < 0.62 ? 'determined_focus' : 'warm_relief_smile';
    drawModernExpressiveActor(
      g,
      minaSpec,
      {
        heightNorm: 0.68,
        facing: 1,
        root: [0.28, 1.22],
        pelvisCenter: [0.28, 0.96],
        hipWorld: [0.28, 0.96],
        neckWorld: [0.29, 0.58],
        headWorld: [0.30, 0.39],
        leftLegWorld: [[0.26, 0.96], [0.26, 1.09], [0.26, 1.22]],
        rightLegWorld: [[0.30, 0.96], [0.30, 1.09], [0.30, 1.22]],
        leftArmWorld: [[0.24, 0.60], [0.34, 0.72], [0.43, 0.66]],
        rightArmWorld: [[0.34, 0.60], [0.40, 0.72], [0.47, 0.65]],
        modernExpression: mExpr,
        handShapeLeft: 'locked_grip',
        handShapeRight: 'pointing',
        hairSwayRad: 0.03,
        secondary: { clothSwayNorm: 0.01, headLagRad: 0.04 },
      },
      { view: 'three_quarter', expressionOverride: mExpr },
    );

    // Close-up origami dragon kite + neat crimson ribbon knot between them!
    drawModernProp(g, 'origami_dragon_kite', W * 0.50, H * 0.69, 2.30, { rot: -0.10, globalT, hideTail: false });
    drawModernProp(g, 'kite_spool', W * 0.58, H * 0.67, 1.65, { rot: 0.12, globalT });
    const knotR = lerp(18, 9, knotK);
    g.save();
    g.beginPath();
    g.arc(W * 0.49, H * 0.64, knotR, 0, Math.PI * 2);
    g.strokeStyle = '#DC392D';
    g.lineWidth = 6.5;
    g.stroke();
    g.restore();
    const tiePts = sampleQuadBezier2D([W * 0.49, H * 0.64], [W * 0.54, H * 0.66 + (1 - knotK) * 18], [W * 0.58, H * 0.67], 10);
    drawVariableStroke(g, tiePts, '#211612', 7.0, false);
    drawVariableStroke(g, tiePts, '#DC392D', 4.5, false);
    return true;
  }

  if (insertKind === 'kite_payoff_eyes_close') {
    // SHOT 8 Segment 1 (26.0-27.5s): Warm golden close-up of Mina & Bao's smiling faces looking skyward
    // before cutting to the wide sunlit park sky as the dragon kite soars!
    drawModernEnvironmentStage(g, envSpec, globalT, { scale: 'close' }, { wind_strength: 0.45, warm_sun_boost: 0.85 });
    const minaSpec = charSpecs.mina || Object.values(charSpecs)[0];
    const baoSpec = charSpecs.bao || Object.values(charSpecs)[1] || minaSpec;

    drawModernExpressiveActor(
      g,
      minaSpec,
      {
        heightNorm: 0.76,
        facing: 1,
        root: [0.34, 1.24],
        pelvisCenter: [0.34, 0.98],
        hipWorld: [0.34, 0.98],
        neckWorld: [0.34, 0.58],
        headWorld: [0.35, 0.38 - u * 0.02],
        leftLegWorld: [[0.32, 0.98], [0.32, 1.11], [0.32, 1.24]],
        rightLegWorld: [[0.36, 0.98], [0.36, 1.11], [0.36, 1.24]],
        leftArmWorld: [[0.28, 0.60], [0.36, 0.72], [0.46, 0.64]],
        rightArmWorld: [[0.40, 0.60], [0.46, 0.70], [0.52, 0.62]],
        modernExpression: 'joyful_laugh',
        handShapeLeft: 'locked_grip',
        handShapeRight: 'locked_grip',
        hairSwayRad: 0.12,
        secondary: { clothSwayNorm: 0.03, headLagRad: -0.06 },
      },
      { view: 'three_quarter', expressionOverride: 'joyful_laugh' },
    );

    drawModernExpressiveActor(
      g,
      baoSpec,
      {
        heightNorm: 0.84,
        facing: -1,
        root: [0.68, 1.24],
        pelvisCenter: [0.68, 0.94],
        hipWorld: [0.68, 0.94],
        neckWorld: [0.68, 0.50],
        headWorld: [0.67, 0.29 - u * 0.02],
        leftLegWorld: [[0.66, 0.94], [0.66, 1.09], [0.66, 1.24]],
        rightLegWorld: [[0.70, 0.94], [0.70, 1.09], [0.70, 1.24]],
        leftArmWorld: [[0.62, 0.52], [0.56, 0.66], [0.52, 0.62]],
        rightArmWorld: [[0.74, 0.52], [0.78, 0.68], [0.74, 0.80]],
        modernExpression: 'joyful_laugh',
        handShapeLeft: 'locked_grip',
        handShapeRight: 'relaxed',
        hairSwayRad: 0.10,
        secondary: { clothSwayNorm: 0.03, headLagRad: 0.05 },
      },
      { view: 'three_quarter', expressionOverride: 'joyful_laugh' },
    );

    // Rising crimson kite line ascending toward the upper sky!
    drawModernProp(g, 'kite_spool', W * 0.50, H * 0.63, 1.75, { rot: -0.25, globalT });
    const skyLine = sampleQuadBezier2D([W * 0.50, H * 0.62], [W * 0.54, H * 0.32], [W * 0.62, -20], 10);
    drawVariableStroke(g, skyLine, '#211612', 6.5, false);
    drawVariableStroke(g, skyLine, '#DC392D', 4.2, false);
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

  // 3. Draw Background/Midground Interactive Props (counter, cart, rostra, flying/held scroll, kite, spool, beaker, tray)
  const renderedPropAnchors = {};
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
    if (pr.id || pr.objectId) {
      renderedPropAnchors[pr.id || pr.objectId] = [px * W, py * H];
    }
    const wheelAngle = (px * W) / 36.0;
    drawModernProp(g, pr.kind, px * W, py * H, Number(pr.scale ?? 1.0), { rot, wheelAngle, globalT, hideTail: Boolean(pr.hideTail) });
  }

  // 3b. Continuous Single Physical Tether / Ribbon Catenary (ZERO duplicate strings, 100% contact continuity!)
  if (Array.isArray(args.tetherLinks)) {
    for (const tl of args.tetherLinks) {
      let pA = null;
      let pB = null;
      if (tl.fromActor && evalByActor[tl.fromActor]) {
        const hPt = tl.fromHand === 'left' ? evalByActor[tl.fromActor].leftHandWorld : evalByActor[tl.fromActor].rightHandWorld;
        pA = [hPt[0] * W, hPt[1] * H];
      } else if (tl.fromProp && renderedPropAnchors[tl.fromProp]) {
        pA = renderedPropAnchors[tl.fromProp];
      } else if (Array.isArray(tl.fromWorld)) {
        pA = [tl.fromWorld[0] * W, tl.fromWorld[1] * H];
      }

      if (tl.toProp && renderedPropAnchors[tl.toProp]) {
        pB = renderedPropAnchors[tl.toProp];
      } else if (Array.isArray(tl.toWorld)) {
        const uT = smooth01(lt / dur);
        const txW = Array.isArray(tl.toWorldEnd) ? lerp(tl.toWorld[0], tl.toWorldEnd[0], uT) : tl.toWorld[0];
        const tyW = Array.isArray(tl.toWorldEnd) ? lerp(tl.toWorld[1], tl.toWorldEnd[1], uT) : tl.toWorld[1];
        pB = [txW * W, tyW * H];
      }
      if (pA && pB) {
        const sag = Number(tl.sagPx ?? 24) + Math.sin(globalT * 5.4) * 5;
        const midC = [0.5 * (pA[0] + pB[0]), 0.5 * (pA[1] + pB[1]) + sag];
        const cPts = sampleQuadBezier2D(pA, midC, pB, 14);
        drawVariableStroke(g, cPts, '#211612', Number(tl.outerWidth ?? 4.8), false);
        drawVariableStroke(g, cPts, tl.color || '#DC392D', Number(tl.innerWidth ?? 2.8), false);
      }
    }
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
