// FL-01 V14.7.6 — Original Procedural Harbor Drama & Natural 2D Acting Primitives
// Project: "THE LAST LIGHT OF PORTUS — A ROMAN HARBOR STORY"
// Fictional Roman harbor lighthouse drama at twilight; stylized 2D reconstruction.
// Zero reused prior-preview visuals, zero external copyrighted rasters, zero military props.
// Pure deterministic functions of (MotionPlan, worldState, mechanics, globalT, seed).

import { E, clamp, lerp, ease, registerShot, alpha } from '/engine/core.js';
import { rect, ellipse, circ, polyS } from '/packs/squire/ink.js';
import {
  evaluateMotionTrackAt,
  evaluateMultiActorInteraction,
} from '/packs/squire/motion_engine.js';
import {
  createSeparatedActionClock,
  applyHarborInteractionFX,
} from '/integrations/claude_motion/adapter.js';
import {
  loadBrowserRigbyAsset,
  convertMotionPlanToRigbyTracks,
  renderRigbyActorToCanvas,
} from '/integrations/rigby2d/adapter.js';

const circle = circ;
const smooth = (k) => {
  const u = clamp(k, 0, 1);
  return u * u * (3 - 2 * u);
};
const easeIO = (k) => ease.inOut(clamp(k, 0, 1));
function line(g, x1, y1, x2, y2, o = {}) {
  g.save();
  g.beginPath();
  g.moveTo(x1, y1);
  g.lineTo(x2, y2);
  g.lineWidth = o.lw ?? 3;
  g.strokeStyle = o.ink ?? '#4e4740';
  g.lineCap = o.cap ?? 'round';
  g.lineJoin = 'round';
  g.stroke();
  g.restore();
}

// Palette calibrated so background outlines & twilight sea never collide with actor-ink QA (<55 RGB)
const INK_ACTOR = '#1c1512';
const INK_STONE = '#4e4740';
const INK_TIMBER = '#524034';
const INK_SEA = '#3d4f63';

let _cachedRigbyBrowserAsset = null;
let _rigbyInitAttempted = false;

export async function ensureHarborRigbyAssetLoaded(extraAnimations = {}) {
  if (typeof document === 'undefined') return null;
  if (_cachedRigbyBrowserAsset && Object.keys(extraAnimations).length === 0) {
    return _cachedRigbyBrowserAsset;
  }
  _rigbyInitAttempted = true;
  _cachedRigbyBrowserAsset = await loadBrowserRigbyAsset({ extraAnimations });
  return _cachedRigbyBrowserAsset;
}

function interpMech(mech, keyBase, u, fallback = 0) {
  if (!mech) return fallback;
  const s = Number(mech[`${keyBase}_start`] ?? mech[keyBase] ?? fallback);
  const e = Number(mech[`${keyBase}_end`] ?? mech[keyBase] ?? s);
  return lerp(s, e, clamp(u, 0, 1));
}

function getActiveCameraSegment(shot, lt) {
  const segs = shot?.args?.cameraSegments;
  if (!Array.isArray(segs) || segs.length === 0) {
    return {
      segment_id: 'seg_default',
      projection_mode: shot?.args?.viewMode || 'continuous_2d_canvas',
      scale: 'wide',
      subject_focus: shot?.args?.focus || 'harbor',
      local_u: clamp(lt / Math.max(0.1, Number(shot?.dur || 3)), 0, 1),
      zoom: 1.0,
      panX: 0.5,
      panY: 0.5,
    };
  }
  let chosen = segs[segs.length - 1];
  for (let i = 0; i < segs.length; i++) {
    const sg = segs[i];
    const s0 = Number(sg.local_start ?? 0);
    const s1 = Number(sg.local_end ?? shot?.dur ?? 3);
    if (i === segs.length - 1 || (lt >= s0 - 1e-6 && lt < s1 - 1e-6)) {
      chosen = sg;
      break;
    }
  }
  const s0 = Number(chosen.local_start ?? 0);
  const s1 = Math.max(s0 + 0.05, Number(chosen.local_end ?? shot?.dur ?? 3));
  const u = smooth(clamp((lt - s0) / (s1 - s0), 0, 1));
  const kfs = Array.isArray(chosen.keyframes) && chosen.keyframes.length >= 2 ? chosen.keyframes : null;
  const panX = Array.isArray(chosen.center_from) && Array.isArray(chosen.center_to)
    ? lerp(Number(chosen.center_from[0] ?? 0.5), Number(chosen.center_to[0] ?? 0.5), u)
    : kfs
      ? lerp(Number(kfs[0].x ?? 0.5), Number(kfs[kfs.length - 1].x ?? 0.5), u)
      : 0.5;
  const panY = Array.isArray(chosen.center_from) && Array.isArray(chosen.center_to)
    ? lerp(Number(chosen.center_from[1] ?? 0.5), Number(chosen.center_to[1] ?? 0.5), u)
    : kfs
      ? lerp(Number(kfs[0].y ?? 0.5), Number(kfs[kfs.length - 1].y ?? 0.5), u)
      : 0.5;
  const zoom = chosen.zoom_from !== undefined && chosen.zoom_to !== undefined
    ? lerp(Number(chosen.zoom_from ?? 1.0), Number(chosen.zoom_to ?? 1.0), u)
    : kfs
      ? lerp(Number(kfs[0].z ?? 1.0), Number(kfs[kfs.length - 1].z ?? 1.0), u)
      : 1.0;
  return {
    ...chosen,
    local_u: u,
    panX,
    panY,
    zoom,
  };
}

/**
 * Draw twilight coastal squall sky, wind-streaked clouds, and wheeling harbor gulls.
 * Preserves dusk/twilight storm continuity throughout (no dawn transition).
 */
export function drawTwilightStormHarborSky(g, globalT, opts = {}) {
  const W = E.W;
  const H = E.H;
  const warmth = clamp(Number(opts.duskWarmth ?? 0.25), 0, 1);
  const wind = clamp(Number(opts.wind ?? 0.65), 0, 1.4);

  const skyGrad = g.createLinearGradient(0, 0, 0, H * 0.66);
  skyGrad.addColorStop(0, '#3a4a66');
  skyGrad.addColorStop(0.54, warmth > 0.45 ? '#525b6e' : '#46586b');
  skyGrad.addColorStop(1, warmth > 0.45 ? '#9c7864' : '#657382');
  g.fillStyle = skyGrad;
  g.fillRect(0, 0, W, H);

  // Subtle residual twilight amber glow along western horizon
  const horizGrad = g.createRadialGradient(W * 0.26, H * 0.56, 20, W * 0.26, H * 0.56, W * 0.48);
  horizGrad.addColorStop(0, `rgba(218, 154, 106, ${(0.14 + warmth * 0.26).toFixed(3)})`);
  horizGrad.addColorStop(1, 'rgba(100, 114, 130, 0)');
  g.fillStyle = horizGrad;
  g.fillRect(0, 0, W, H * 0.68);

  // Wind-driven twilight storm cloud bands
  const cloudShift = globalT * (28 + wind * 38);
  g.save();
  const cloudBands = [
    [220, 108, 250, 36, 0.36],
    [760, 88, 310, 42, 0.42],
    [1340, 124, 280, 38, 0.38],
    [520, 186, 240, 28, 0.28],
    [1140, 198, 260, 30, 0.30],
  ];
  for (const [bx, by, rx, ry, al] of cloudBands) {
    const cx = (((bx - cloudShift) % (W + 520)) + (W + 520)) % (W + 520) - 260;
    g.fillStyle = `rgba(74, 88, 105, ${al})`;
    g.beginPath();
    g.ellipse(cx, by, rx, ry, -0.04 * wind, 0, Math.PI * 2);
    g.ellipse(cx + rx * 0.45, by + 10, rx * 0.66, ry * 0.74, 0, 0, Math.PI * 2);
    g.fill();
  }

  // Diagonal wind streaks in squall
  g.strokeStyle = `rgba(188, 206, 222, ${(0.08 + wind * 0.10).toFixed(3)})`;
  g.lineWidth = 2;
  for (let i = 0; i < 9; i++) {
    const sx = (((i * 250 - globalT * (180 + wind * 140)) % (W + 300)) + (W + 300)) % (W + 300) - 150;
    const sy = 90 + ((i * 73) % 280);
    g.beginPath();
    g.moveTo(sx, sy);
    g.lineTo(sx - 85 * wind, sy + 18 * wind);
    g.stroke();
  }

  // Harbor gulls banking against coastal wind
  if (opts.showGulls !== false) {
    g.strokeStyle = '#d6dfe8';
    g.lineWidth = 2.6;
    for (let k = 0; k < 3; k++) {
      const gx = W * (0.20 + k * 0.14) - Math.sin(globalT * 0.9 + k) * 34 - globalT * 8 * wind;
      const gy = H * (0.22 + k * 0.045) + Math.cos(globalT * 2.4 + k * 1.7) * 9;
      const flap = Math.sin(globalT * 6.2 + k * 2.1) * 8;
      g.beginPath();
      g.moveTo(gx - 14, gy + flap);
      g.quadraticCurveTo(gx - 5, gy - 6, gx, gy);
      g.quadraticCurveTo(gx + 5, gy - 6, gx + 14, gy + flap * 0.9);
      g.stroke();
    }
  }
  g.restore();

  // Distant Roman harbor breakwater mole & headlands
  polyS(
    g,
    [
      [0, H * 0.58],
      [W * 0.16, H * 0.53],
      [W * 0.34, H * 0.56],
      [W * 0.56, H * 0.55],
      [W, H * 0.57],
      [W, H * 0.66],
      [0, H * 0.66],
    ],
    { fill: '#4b5968', lw: 0 },
  );
}

/**
 * Draw Roman merchant sailing vessel (corbita) with curved wooden hull, square sail,
 * rigging, steering oars, and small bow oil lamp.
 */
export function drawRomanMerchantShip(g, cx, cy, scale = 1.0, opts = {}) {
  const rollRad = Number(opts.rollRad ?? 0.08);
  const turnAway = clamp(Number(opts.turnAway ?? 0), 0, 1); // 0 = heading toward right shoals, 1 = turned safely to open channel
  const wind = clamp(Number(opts.wind ?? 0.7), 0, 1.3);
  const bowDir = turnAway > 0.45 ? -1 : 1;
  const hullSquash = 1.0 - 0.24 * Math.sin(Math.PI * clamp(turnAway, 0, 1));

  g.save();
  g.translate(cx, cy);
  g.rotate(rollRad);
  g.scale(scale * bowDir * hullSquash, scale);

  // Curved merchant hull (oak planking)
  polyS(
    g,
    [
      [-92, -6],
      [-74, 22],
      [68, 22],
      [98, -14],
      [78, -18],
      [-78, -16],
    ],
    { fill: '#7c5842', lw: 3, ink: INK_TIMBER },
  );
  // Decorative stern swan-neck post & gunwale rail
  line(g, -82, -8, 76, -10, { lw: 3, ink: '#9e7658' });
  polyS(g, [[-90, -6], [-104, -36], [-92, -38], [-80, -12]], {
    fill: '#8e654b',
    lw: 2.5,
    ink: INK_TIMBER,
  });

  // Dual Roman steering oars (gubernacula)
  line(g, -64, 4, -88, 28, { lw: 4, ink: '#684a38' });

  // Central mast & yardarm
  line(g, -4, 10, -4, -118, { lw: 5, ink: INK_TIMBER });
  line(g, -58, -96, 56, -90, { lw: 4, ink: INK_TIMBER });

  // Billowing square linen mainsail reacting to coastal gust
  const belly = 22 + wind * 18;
  g.save();
  g.fillStyle = '#dfd4c2';
  g.strokeStyle = INK_TIMBER;
  g.lineWidth = 2.6;
  g.beginPath();
  g.moveTo(-54, -95);
  g.quadraticCurveTo(10 + belly * 0.4, -56, -46, -24);
  g.quadraticCurveTo(8, -18, 52, -22);
  g.quadraticCurveTo(56 + belly, -56, 52, -90);
  g.closePath();
  g.fill();
  g.stroke();
  g.restore();

  // Rigging stays
  line(g, -4, -114, -76, -12, { lw: 1.8, ink: '#6e6256' });
  line(g, -4, -114, 82, -14, { lw: 1.8, ink: '#6e6256' });

  // Small bow oil navigation lamp
  circle(g, 92, -16, 5.5, { fill: '#ffd46e', lw: 1.5, ink: '#8a6236' });
  g.fillStyle = 'rgba(255, 214, 112, 0.28)';
  g.beginPath();
  g.arc(92, -16, 18, 0, Math.PI * 2);
  g.fill();

  g.restore();
}

/**
 * Draw churning harbor swells, jagged coastal shoal rocks, ancient oil-flame channel reflection,
 * and the merchant vessel.
 */
export function drawHarborSeaShoalsAndShip(g, globalT, world = {}, mech = {}, u = 0) {
  const W = E.W;
  const H = E.H;
  const seaTop = H * 0.57;
  const wind = clamp(Number(world.wind ?? 0.72), 0, 1.4);
  const beaconGlow = interpMech(mech, 'beacon_glow', u, world.beacon_lit ? 0.95 : 0.0);
  const shipProgress = interpMech(mech, 'ship_progress', u, 0.35);
  const shipTurn = interpMech(mech, 'ship_turn', u, 0.0);

  // Base twilight harbor sea (kept in storm slate [60..104] RGB to avoid false actor-blue mask)
  const seaGrad = g.createLinearGradient(0, seaTop, 0, H);
  seaGrad.addColorStop(0, '#445768');
  seaGrad.addColorStop(0.55, '#3d4f62');
  seaGrad.addColorStop(1, '#4c5c6b');
  g.fillStyle = seaGrad;
  g.fillRect(0, seaTop, W, H - seaTop);

  // Ancient oil-flame harbor channel illumination path (warm stylized water shimmer, NOT rotating beam)
  if (beaconGlow > 0.03) {
    g.save();
    const glowGrad = g.createLinearGradient(W * 0.74, seaTop, W * 0.18, H * 0.88);
    glowGrad.addColorStop(0, `rgba(255, 206, 118, ${(0.38 * beaconGlow).toFixed(3)})`);
    glowGrad.addColorStop(0.55, `rgba(238, 178, 98, ${(0.22 * beaconGlow).toFixed(3)})`);
    glowGrad.addColorStop(1, 'rgba(180, 140, 96, 0)');
    g.fillStyle = glowGrad;
    g.beginPath();
    g.moveTo(W * 0.68, seaTop + 6);
    g.lineTo(W * 0.82, seaTop + 6);
    g.lineTo(W * 0.38, H * 0.90);
    g.lineTo(W * 0.10, H * 0.82);
    g.closePath();
    g.fill();
    g.restore();
  }

  // Rolling swell ridges
  g.save();
  for (let row = 0; row < 5; row++) {
    const wy = seaTop + 26 + row * 44;
    g.strokeStyle = row % 2 === 0 ? '#687e92' : '#5b7084';
    g.lineWidth = 3;
    g.beginPath();
    for (let x = 0; x <= W; x += 48) {
      const wave = Math.sin(x * 0.012 + globalT * (2.6 + row * 0.3) + row) * (6 + wind * 6);
      if (x === 0) g.moveTo(x, wy + wave);
      else g.lineTo(x, wy + wave);
    }
    g.stroke();
  }
  g.restore();

  // Merchant vessel position: drifts toward jagged shoals (x ~ 0.46) in S01-S02, turns into safe channel (x ~ 0.24) in S07-S08
  if (mech?.show_ship !== false) {
    const hazardX = lerp(W * 0.26, W * 0.47, clamp(shipProgress, 0, 1));
    const safeX = lerp(hazardX, W * 0.20, clamp(shipTurn, 0, 1));
    const shipY =
      seaTop +
      lerp(56, 78, clamp(shipProgress, 0, 1)) -
      shipTurn * 18 +
      Math.sin(globalT * 2.7) * (5 + wind * 4);
    const roll = Math.sin(globalT * 2.3 + 0.6) * (0.04 + 0.07 * wind * (1 - shipTurn * 0.55));
    const shipScale = lerp(0.84, 0.66, clamp(shipTurn * 0.7, 0, 1));
    drawRomanMerchantShip(g, safeX, shipY, shipScale, {
      rollRad: roll,
      turnAway: shipTurn,
      wind,
    });
  }

  // Jagged coastal shoal rocks on mid-right hazard zone + breaking white surf
  if (mech?.show_shoals !== false) {
    const rxBase = W * 0.58;
    const ryBase = seaTop + 82;
    polyS(
      g,
      [
        [rxBase - 78, ryBase + 22],
        [rxBase - 46, ryBase - 34],
        [rxBase - 14, ryBase + 4],
        [rxBase + 18, ryBase - 52],
        [rxBase + 54, ryBase - 8],
        [rxBase + 86, ryBase - 28],
        [rxBase + 112, ryBase + 24],
      ],
      { fill: '#48525e', lw: 3, ink: INK_SEA },
    );
    // Breaking surf foam around rocks (bright b >= 214)
    const surfPulse = 0.72 + 0.28 * Math.sin(globalT * 4.2);
    g.fillStyle = `rgba(220, 234, 246, ${(0.65 * surfPulse).toFixed(3)})`;
    g.beginPath();
    g.ellipse(rxBase + 12, ryBase + 20, 96 * surfPulse, 13, 0, 0, Math.PI * 2);
    g.fill();
  }
}

/**
 * Draw period-plausible ancient Roman bronze oil lantern (lucerna / hoist lantern)
 * with horn panes, bail ring, and wind-reactive olive-oil wick flame.
 */
export function drawAncientBronzeOilLantern(g, cx, cy, scale = 1.0, opts = {}) {
  const lit = opts.lit !== false;
  const flameStrength = clamp(Number(opts.flameStrength ?? (lit ? 1.0 : 0.0)), 0, 1.3);
  const swingRad = Number(opts.swingRad ?? 0);
  const wind = Number(opts.wind ?? 0.5);
  const globalT = Number(opts.globalT ?? 0);

  g.save();
  g.translate(cx, cy);
  g.rotate(swingRad);
  g.scale(scale, scale);

  // Warm ambient oil-flame halo (kept soft & period-plausible, never rotating beam)
  if (flameStrength > 0.04) {
    const rHalo = 68 * flameStrength;
    const halo = g.createRadialGradient(0, 14, 4, 0, 14, rHalo);
    halo.addColorStop(0, `rgba(255, 218, 128, ${(0.44 * clamp(flameStrength, 0, 1)).toFixed(3)})`);
    halo.addColorStop(0.6, `rgba(232, 162, 88, ${(0.18 * clamp(flameStrength, 0, 1)).toFixed(3)})`);
    halo.addColorStop(1, 'rgba(180, 130, 88, 0)');
    g.fillStyle = halo;
    g.beginPath();
    g.arc(0, 14, rHalo, 0, Math.PI * 2);
    g.fill();
  }

  // Iron bail ring at top (cx, cy is top grip ring!)
  circle(g, 0, 0, 7, { fill: 'rgba(0,0,0,0)', lw: 3, ink: '#5a4634' });
  // Conical bronze cap
  polyS(g, [[-17, 10], [0, 2], [17, 10]], { fill: '#9e7444', lw: 2.4, ink: INK_TIMBER });
  // Horn-paned lantern body
  rect(g, -13, 10, 26, 28, {
    fill: flameStrength > 0.05 ? '#f2cf88' : '#6c747e',
    lw: 2.4,
    ink: INK_TIMBER,
    r: 3,
  });
  // Vertical bronze struts
  line(g, -6, 10, -6, 38, { lw: 2, ink: '#7e5a34' });
  line(g, 6, 10, 6, 38, { lw: 2, ink: '#7e5a34' });
  // Oil reservoir base
  rect(g, -16, 37, 32, 8, { fill: '#8c6438', lw: 2.4, ink: INK_TIMBER, r: 2 });

  // Oil wick flame inside lantern
  if (flameStrength > 0.05) {
    const lean = clamp(wind * 4.5 + Math.sin(globalT * 13.0) * 2.2, -7, 7);
    polyS(
      g,
      [
        [-5, 32],
        [lean, 15 - 4 * flameStrength],
        [5, 32],
      ],
      { fill: '#fff2b2', lw: 1.4, ink: '#e28432' },
    );
  } else if (opts.smokeWisp) {
    g.strokeStyle = 'rgba(196, 206, 218, 0.55)';
    g.lineWidth = 2.5;
    g.beginPath();
    g.moveTo(0, 24);
    g.quadraticCurveTo(-14 - wind * 16, 6, -28 - wind * 26, -12);
    g.stroke();
  }

  g.restore();
}

/**
 * Draw stone Roman harbor mole, steps, stone watchtower, overhead wooden pulley sheave,
 * timber ladder, iron railing, and continuous hemp hoist rope.
 */
export function drawHarborMoleAndWatchtower(g, globalT, world = {}, mech = {}, u = 0, opts = {}) {
  const W = E.W;
  const H = E.H;
  const groundY = Number(opts.groundY ?? 0.84) * H;
  const towerX = Number(opts.towerX ?? 0.72) * W;
  const towerW = Number(opts.towerW ?? 0.19) * W;
  const towerTopY = H * 0.19;

  const liftProg = clamp(interpMech(mech, 'lantern_lift', u, world.lantern_raised ? 1.0 : 0.0), 0, 1);
  const pulleyAng = interpMech(mech, 'pulley_angle', u, liftProg * 5.2);
  const ladderTiltDeg = interpMech(mech, 'ladder_tilt_deg', u, 0.0);
  const upperBeaconLit = interpMech(mech, 'upper_beacon', u, 0.0);

  // Foreground Roman travertine harbor mole (mid-warm stone >= 110 RGB down to bottom of frame!)
  rect(g, 0, groundY, W, H - groundY, { fill: '#8f8476', lw: 0 });
  rect(g, 0, groundY, W, 14, { fill: '#a39788', lw: 2.5, ink: INK_STONE });

  // Ashlar stone courses along harbor mole
  g.save();
  g.strokeStyle = '#6f665b';
  g.lineWidth = 2;
  for (let r = 0; r < 3; r++) {
    const ry = groundY + 34 + r * 42;
    g.beginPath();
    g.moveTo(0, ry);
    g.lineTo(W, ry);
    g.stroke();
    for (let c = 0; c < 14; c++) {
      const cx = (c * 146 + r * 58) % W;
      g.beginPath();
      g.moveTo(cx, ry - 42);
      g.lineTo(cx, ry);
      g.stroke();
    }
  }
  g.restore();

  // Narrow stone steps leading to tower plinth
  for (let st = 0; st < 3; st++) {
    const sx = towerX - 150 + st * 38;
    const sy = groundY - (st + 1) * 14;
    rect(g, sx, sy, 160 - st * 24, (st + 1) * 14, { fill: '#9a8e7f', lw: 2.5, ink: INK_STONE });
  }

  // Stone harbor watchtower shaft (opus quadratum)
  polyS(
    g,
    [
      [towerX - towerW * 0.52, groundY],
      [towerX - towerW * 0.42, towerTopY + 92],
      [towerX + towerW * 0.42, towerTopY + 92],
      [towerX + towerW * 0.52, groundY],
    ],
    { fill: '#978a7a', lw: 3.5, ink: INK_STONE },
  );

  // Sheltered upper stone beacon alcove
  const alcW = towerW * 0.72;
  const alcH = 92;
  const alcX = towerX - alcW * 0.5;
  const alcY = towerTopY;
  rect(g, alcX, alcY, alcW, alcH, { fill: '#8b7e6f', lw: 3, ink: INK_STONE, r: 4 });
  rect(g, alcX + 18, alcY + 18, alcW - 36, alcH - 22, {
    fill: upperBeaconLit > 0.1 || liftProg > 0.85 ? '#6d5844' : '#4a535e',
    lw: 2.5,
    ink: INK_STONE,
    r: 10,
  });
  // Pitched terracotta tower roof
  polyS(
    g,
    [
      [alcX - 18, alcY + 4],
      [towerX, alcY - 36],
      [alcX + alcW + 18, alcY + 4],
    ],
    { fill: '#a45640', lw: 3, ink: INK_STONE },
  );

  // Snuffed or burning brazier in upper alcove (S01 hook vs S07/S08 steady oil light)
  if (upperBeaconLit > 0.02 || opts.showSnuffedBrazier) {
    drawAncientBronzeOilLantern(g, towerX, alcY + 34, 1.18, {
      lit: upperBeaconLit > 0.06,
      flameStrength: upperBeaconLit,
      smokeWisp: upperBeaconLit <= 0.06,
      wind: Number(world.wind ?? 0.7),
      globalT,
    });
  }

  // Projecting timber hoist cathead & rotating wooden pulley sheave on left side of tower
  const beamX0 = towerX - towerW * 0.42 - 96;
  const beamY = towerTopY + 106;
  rect(g, beamX0, beamY - 8, 128, 16, { fill: '#7c5a42', lw: 2.8, ink: INK_TIMBER });
  line(g, beamX0 + 32, beamY + 8, towerX - towerW * 0.44, beamY + 56, { lw: 6, ink: INK_TIMBER });

  const sheaveX = beamX0 + 18;
  const sheaveY = beamY + 16;
  circle(g, sheaveX, sheaveY, 18, { fill: '#b28752', lw: 3, ink: INK_TIMBER });
  for (let sp = 0; sp < 4; sp++) {
    const a = pulleyAng + (sp * Math.PI) / 2;
    line(
      g,
      sheaveX + Math.cos(a) * 15,
      sheaveY + Math.sin(a) * 15,
      sheaveX - Math.cos(a) * 15,
      sheaveY - Math.sin(a) * 15,
      { lw: 2.4, ink: INK_TIMBER },
    );
  }

  // Iron safety railing beside tower steps (contact target for CATCH_RAIL in S05!)
  const railX = towerX - towerW * 0.52 - 58;
  const railTopY = groundY - 122;
  line(g, railX - 38, railTopY + 18, railX + 34, railTopY, { lw: 5, ink: '#575c64' });
  line(g, railX - 34, groundY - 14, railX - 34, railTopY + 16, { lw: 4.5, ink: '#575c64' });
  line(g, railX + 28, groundY - 40, railX + 28, railTopY + 2, { lw: 4.5, ink: '#575c64' });

  // Wooden service ladder leaning against tower (tilts slightly in S05 wind gust)
  g.save();
  const ladBaseX = towerX - towerW * 0.48 - 18;
  const ladBaseY = groundY - 28;
  g.translate(ladBaseX, ladBaseY);
  g.rotate(((ladderTiltDeg || 0) * Math.PI) / 180);
  line(g, -12, 0, 26, -240, { lw: 5, ink: '#7c593e' });
  line(g, 8, 0, 46, -240, { lw: 5, ink: '#7c593e' });
  for (let rg = 1; rg <= 6; rg++) {
    const uR = rg / 7;
    line(g, lerp(-12, 26, uR), -240 * uR, lerp(8, 46, uR), -240 * uR, { lw: 3.4, ink: '#8e694b' });
  }
  g.restore();

  // Dockside wooden lantern rack on left quay (for S03 spare burning oil lantern)
  if (opts.showLanternRack) {
    const rackX = W * 0.53;
    const rackTopY = groundY - 148;
    line(g, rackX, groundY, rackX, rackTopY, { lw: 7, ink: INK_TIMBER });
    line(g, rackX - 4, rackTopY + 8, rackX - 46, rackTopY + 8, { lw: 5.5, ink: INK_TIMBER });
    if (!opts.lanternTakenFromRack) {
      drawAncientBronzeOilLantern(g, rackX - 42, rackTopY + 14, 1.02, {
        lit: true,
        flameStrength: 0.95,
        swingRad: Math.sin(globalT * 3.4) * 0.08,
        wind: Number(world.wind ?? 0.6),
        globalT,
      });
    }
  }

  // Continuous hemp hoist rope: from worker grip point -> over sheave -> down to hoist hook / lantern bracket
  const hoistBottomY = groundY - 168;
  const hoistTopY = alcY + 38;
  const hookX = lerp(sheaveX, towerX - 18, smooth(clamp((liftProg - 0.65) / 0.35, 0, 1)));
  const hookY = lerp(hoistBottomY, hoistTopY, liftProg);
  const haulGripX = Number(opts.ropeGripWorld?.[0] ?? towerX + 22);
  const haulGripY = Number(opts.ropeGripWorld?.[1] ?? groundY - 128);

  g.save();
  g.strokeStyle = '#cbb082';
  g.lineWidth = 4.2;
  g.beginPath();
  g.moveTo(haulGripX, haulGripY);
  g.lineTo(sheaveX + 12, sheaveY);
  g.lineTo(sheaveX - 12, sheaveY);
  g.lineTo(hookX, hookY);
  g.stroke();
  g.restore();

  // Hoisted lantern when attached to hoist rope (S05 hook / S06 lift / S07-S08 raised)
  if (opts.lanternOnHoist) {
    const swing = Number(opts.lanternSwingRad ?? Math.sin(globalT * 4.4) * 0.09 * (1 - liftProg * 0.65));
    drawAncientBronzeOilLantern(g, hookX, hookY + 4, 1.08, {
      lit: true,
      flameStrength: 1.05,
      swingRad: swing,
      wind: Number(world.wind ?? 0.7),
      globalT,
    });
  }

  return {
    groundY,
    sheave: [sheaveX, sheaveY],
    railAnchor: [railX, railTopY + 8],
    hoistHook: [hookX, hookY],
    towerAlcove: [towerX, alcY + 38],
  };
}

/**
 * Render an articulated 2D Roman harbor civilian actor (`aelia` or `felix`) purely from
 * `evaluateMotionTrackAt` world-space IK joints, foot plants, secondary motion, and hand contacts.
 */
export function drawHarborActorFromMotionPlan(g, actorId, ev, opts = {}) {
  const W = E.W;
  const H = E.H;
  const isAelia = String(actorId).toLowerCase().includes('aelia') || opts.role === 'lamp_keeper';
  const tunicMain = isAelia ? '#b6423a' : '#667458';
  const tunicTrim = isAelia ? '#d9a44c' : '#9c5a40';
  const cloakCol = isAelia ? '#8f332d' : '#525d48';
  const hairCol = isAelia ? '#32231d' : '#423126';
  const skinCol = '#e4b28a';

  const hipSrc = ev.hipWorld || ev.hipCenter || ev.root || [0.5, 0.7];
  const hip = [hipSrc[0] * W, hipSrc[1] * H];
  const neck = [ev.neckWorld[0] * W, ev.neckWorld[1] * H];
  const head = [ev.headWorld[0] * W, ev.headWorld[1] * H];
  const hPx = Math.max(90, Number(ev.heightNorm || 0.28) * H);
  const dir = ev.facing < 0 ? -1 : 1;

  const mapChain = (ch) => (ch || []).map(([nx, ny]) => [nx * W, ny * H]);
  const lLeg = mapChain(ev.leftLegWorld || ev.leftLeg);
  const rLeg = mapChain(ev.rightLegWorld || ev.rightLeg);
  const lArm = mapChain(ev.leftArmWorld || ev.leftArm);
  const rArm = mapChain(ev.rightArmWorld || ev.rightArm);

  g.save();

  // Wind-reactive civilian cloak behind torso (amplitude from applySecondaryMotion)
  const clothSway = Number(ev.secondary?.clothSwayNorm ?? 0.01) * W;
  polyS(
    g,
    [
      [neck[0] - dir * hPx * 0.05, neck[1] + hPx * 0.03],
      [hip[0] - dir * hPx * 0.14 - clothSway, hip[1] + hPx * 0.14],
      [hip[0] - dir * hPx * 0.03 - clothSway * 0.5, hip[1] + hPx * 0.16],
    ],
    { fill: cloakCol, lw: 2.6, ink: INK_ACTOR },
  );

  // Helper to draw articulated leg + Roman leather sandal
  const drawLeg = (chain, shade) => {
    const [Hpt, Kpt, Fpt] = chain;
    line(g, Hpt[0], Hpt[1], Kpt[0], Kpt[1], { lw: hPx * 0.068, ink: INK_ACTOR });
    line(g, Hpt[0], Hpt[1], Kpt[0], Kpt[1], { lw: hPx * 0.048, ink: shade });
    line(g, Kpt[0], Kpt[1], Fpt[0], Fpt[1], { lw: hPx * 0.058, ink: INK_ACTOR });
    line(g, Kpt[0], Kpt[1], Fpt[0], Fpt[1], { lw: hPx * 0.040, ink: skinCol });
    // Sandal sole planted flat on ground
    polyS(
      g,
      [
        [Fpt[0] - dir * hPx * 0.035, Fpt[1] - hPx * 0.018],
        [Fpt[0] + dir * hPx * 0.068, Fpt[1] - hPx * 0.014],
        [Fpt[0] + dir * hPx * 0.072, Fpt[1] + 2],
        [Fpt[0] - dir * hPx * 0.038, Fpt[1] + 2],
      ],
      { fill: '#5b3c2a', lw: 2.2, ink: INK_ACTOR },
    );
  };

  // Back leg & back arm first for clean 2D depth layering
  drawLeg(lLeg, '#c99872');

  const drawArm = (chain, skin) => {
    const [Spt, Ept, Hnd] = chain;
    line(g, Spt[0], Spt[1], Ept[0], Ept[1], { lw: hPx * 0.056, ink: INK_ACTOR });
    line(g, Spt[0], Spt[1], Ept[0], Ept[1], { lw: hPx * 0.038, ink: skin });
    line(g, Ept[0], Ept[1], Hnd[0], Hnd[1], { lw: hPx * 0.050, ink: INK_ACTOR });
    line(g, Ept[0], Ept[1], Hnd[0], Hnd[1], { lw: hPx * 0.034, ink: skin });
    circle(g, Hnd[0], Hnd[1], hPx * 0.024, { fill: skin, lw: 2.0, ink: INK_ACTOR });
  };
  drawArm(lArm, '#cfa07b');

  // Tunic torso & skirt with natural lean
  const torsoAngle = Math.atan2(neck[0] - hip[0], hip[1] - neck[1]);
  g.save();
  g.translate(hip[0], hip[1]);
  g.rotate(torsoAngle);
  polyS(
    g,
    [
      [-hPx * 0.095, -hPx * 0.24],
      [hPx * 0.095, -hPx * 0.24],
      [hPx * 0.125 - clothSway * 0.12, hPx * 0.13],
      [-hPx * 0.125 - clothSway * 0.18, hPx * 0.13],
    ],
    { fill: tunicMain, lw: 3, ink: INK_ACTOR },
  );
  // Woven waist belt / sash
  rect(g, -hPx * 0.098, -hPx * 0.04, hPx * 0.196, hPx * 0.038, {
    fill: tunicTrim,
    lw: 2,
    ink: INK_ACTOR,
    r: 2,
  });
  g.restore();

  // Front leg
  drawLeg(rLeg, skinCol);

  // Head, hair, & expressive face (gaze, urgent brow vs relieved smile)
  const headR = hPx * 0.072;
  circle(g, head[0], head[1], headR, { fill: skinCol, lw: 2.8, ink: INK_ACTOR });
  // Hair cap + tied bun for Aelia / short curls for Felix
  g.fillStyle = hairCol;
  g.beginPath();
  g.arc(head[0] - dir * headR * 0.12, head[1] - headR * 0.18, headR * 0.96, Math.PI * 0.95, Math.PI * 2.15);
  g.fill();
  if (isAelia) {
    circle(g, head[0] - dir * headR * 0.92, head[1] - headR * 0.1, headR * 0.38, {
      fill: hairCol,
      lw: 2.2,
      ink: INK_ACTOR,
    });
  }

  // Eye & brow expression driven by MotionPlan expression / emotion
  const eyeX = head[0] + dir * headR * 0.42;
  const eyeY = head[1] - headR * 0.05 + Number(ev.secondary?.eyeGazeY ?? 0) * 6;
  circle(g, eyeX, eyeY, Math.max(2.2, headR * 0.13), { fill: INK_ACTOR, lw: 0 });
  const relieved = opts.relieved === true || ev.faceExpression === 'smile' || ev.expression === 'relieved';
  line(
    g,
    eyeX - headR * 0.22,
    eyeY - headR * (relieved ? 0.28 : 0.22),
    eyeX + headR * 0.20,
    eyeY - headR * (relieved ? 0.24 : 0.34),
    { lw: 2.2, ink: INK_ACTOR },
  );
  // Mouth (determined strain vs warm relief)
  g.strokeStyle = INK_ACTOR;
  g.lineWidth = 2.0;
  g.beginPath();
  if (relieved) {
    g.arc(head[0] + dir * headR * 0.34, head[1] + headR * 0.28, headR * 0.22, 0.15, Math.PI * 0.85);
  } else {
    g.moveTo(head[0] + dir * headR * 0.22, head[1] + headR * 0.38);
    g.lineTo(head[0] + dir * headR * 0.52, head[1] + headR * 0.36);
  }
  g.stroke();

  // Held lantern locked directly to gripping hand when actor carries lantern!
  if (opts.carryLantern) {
    const handPt = opts.lanternHand === 'left' ? lArm[2] : rArm[2];
    drawAncientBronzeOilLantern(g, handPt[0], handPt[1] + 4, opts.lanternScale ?? 0.95, {
      lit: true,
      flameStrength: 1.0,
      swingRad: Number(opts.lanternSwingRad ?? 0),
      wind: Number(opts.wind ?? 0.65),
      globalT: Number(opts.globalT ?? 0),
    });
  }

  // Front arm drawn last so gripping hand overlaps lantern bail / rope cleanly!
  drawArm(rArm, skinCol);

  g.restore();
}

/**
 * Legacy V14.7.5.1 sine-wave gait & formula-arm performer used ONLY in 8s Comparison Clip A
 * so A vs B vs C isolates the exact V14.7.5.1 -> V14.7.6 motion upgrade on identical scenery.
 */
export function drawLegacySineHarborActor(g, actorId, spec, lt, dur, opts = {}) {
  const W = E.W;
  const H = E.H;
  const u = easeIO(clamp(lt / Math.max(0.1, dur), 0, 1));
  const rx = lerp(Number(spec.from ?? spec.x ?? 0.4), Number(spec.to ?? spec.x ?? 0.4), u) * W;
  const ry = Number(spec.y ?? 0.84) * H;
  const hPx = Number(spec.h ?? 0.28) * H;
  const stride = Math.sin(lt * 7.5) * 18;
  const heave = Math.sin(lt * 5.6) * 10;
  const isAelia = String(actorId).toLowerCase().includes('aelia');

  g.save();
  // Formula legs (notice stride keeps oscillating via sin(lt*7.5) independent of root velocity!)
  line(g, rx - 8, ry - hPx * 0.34, rx - 10 - stride, ry, { lw: hPx * 0.06, ink: INK_ACTOR });
  line(g, rx + 8, ry - hPx * 0.34, rx + 10 + stride, ry, { lw: hPx * 0.06, ink: INK_ACTOR });
  rect(g, rx - hPx * 0.09, ry - hPx * 0.62, hPx * 0.18, hPx * 0.32, {
    fill: isAelia ? '#b6423a' : '#667458',
    lw: 3,
    ink: INK_ACTOR,
    r: 4,
  });
  circle(g, rx, ry - hPx * 0.70, hPx * 0.07, { fill: '#e4b28a', lw: 2.8, ink: INK_ACTOR });
  const handX = rx + hPx * 0.16;
  const handY = ry - hPx * 0.48 + heave;
  line(g, rx + 10, ry - hPx * 0.56, handX, handY, { lw: hPx * 0.052, ink: INK_ACTOR });
  if (opts.carryLantern) {
    // Uncoupled lantern hover offset in baseline formula
    drawAncientBronzeOilLantern(g, handX + 18, handY + 12, 0.92, {
      lit: true,
      flameStrength: 0.95,
      globalT: lt,
    });
  }
  g.restore();
}

/**
 * Genuine pre-authored 2D close-up insert view (`authored_2d_insert`) for hand-prop grips:
 * - `'lantern_grab'`: Aelia's fingers closing around the warm bronze oil lantern bail on the rack (`S03`).
 * - `'rope_haul'`: Felix & Aelia's braced hands hauling taut hemp hoist rope (`S06`).
 * Driven by the exact same continuous `MotionPlan` phase progress at `globalT`!
 */
export function drawAuthoredGripInsert(g, globalT, insertKind, evPrimary, world = {}, mech = {}, u = 0, segU = 0) {
  const W = E.W;
  const H = E.H;
  const windVal = Number(mech.wind_strength ?? world.wind ?? 0.7);
  drawTwilightStormHarborSky(g, globalT, { wind: windVal, duskWarmth: insertKind === 'beacon_snuff' ? lerp(0.55, 0.14, segU) : 0.18, showGulls: false });

  if (insertKind === 'beacon_snuff') {
    // S01_seg01 close-up of stone watchtower alcove & bronze oil beacon guttering out in coastal squall
    const flameStr = clamp(1.0 - smooth(clamp((segU - 0.26) / 0.52, 0, 1)), 0, 1);
    rect(g, W * 0.24, H * 0.12, W * 0.52, H * 0.88, { fill: '#867868', lw: 4, ink: INK_STONE, r: 10 });
    rect(g, W * 0.32, H * 0.20, W * 0.36, H * 0.64, {
      fill: flameStr > 0.18 ? '#685442' : '#46505c',
      lw: 3.5,
      ink: INK_STONE,
      r: 18,
    });
    polyS(g, [[W * 0.18, H * 0.14], [W * 0.50, H * 0.02], [W * 0.82, H * 0.14]], {
      fill: '#a45640',
      lw: 4,
      ink: INK_STONE,
    });
    drawAncientBronzeOilLantern(g, W * 0.50, H * 0.28, 3.8, {
      lit: flameStr > 0.05,
      flameStrength: flameStr,
      smokeWisp: flameStr <= 0.22,
      swingRad: Math.sin(globalT * 8.5) * 0.13 * (0.35 + 0.65 * segU),
      wind: 1.15,
      globalT,
    });
    return;
  }

  // Soft out-of-focus harbor stone wall backdrop
  rect(g, 0, H * 0.18, W, H * 0.82, { fill: '#6c655d', lw: 0 });
  rect(g, 0, H * 0.76, W, H * 0.24, { fill: '#887d70', lw: 3, ink: INK_STONE });

  const gripW = evPrimary?.activeContactId ? 1.0 : clamp(Number(evPrimary?.phaseProgress ?? u), 0, 1);

  if (insertKind === 'rope_haul') {
    const liftProg = clamp(interpMech(mech, 'lantern_lift', u, 0.4), 0, 1);
    const ropeTravel = (liftProg * 220) % 44;
    // Heavy timber cleat & taut diagonal hemp hoist rope
    rect(g, W * 0.18, H * 0.70, W * 0.64, H * 0.14, { fill: '#7a5840', lw: 4, ink: INK_TIMBER, r: 6 });
    line(g, W * 0.48, -20, W * 0.52, H + 20, { lw: 26, ink: INK_TIMBER });
    line(g, W * 0.48, -20, W * 0.52, H + 20, { lw: 20, ink: '#d2b684' });
    for (let k = -2; k < 14; k++) {
      const ry = k * 44 + ropeTravel;
      const rx = lerp(W * 0.48, W * 0.52, clamp(ry / H, 0, 1));
      line(g, rx - 9, ry - 8, rx + 9, ry + 8, { lw: 3, ink: '#8f7248' });
    }
    const strainY = Math.sin(globalT * 5.0) * 6;
    // Left actor (Aelia russet wool sleeve + articulated forearm + fingers wrapped around rope)
    polyS(g, [[0, H * 0.36], [W * 0.24, H * 0.34 + strainY * 0.5], [W * 0.26, H * 0.48 + strainY * 0.5], [0, H * 0.52]], {
      fill: '#b6423a',
      lw: 4,
      ink: INK_ACTOR,
    });
    line(g, W * 0.23, H * 0.41 + strainY * 0.5, W * 0.48, H * 0.39 + strainY, { lw: 44, ink: INK_ACTOR });
    line(g, W * 0.23, H * 0.41 + strainY * 0.5, W * 0.48, H * 0.39 + strainY, { lw: 36, ink: '#e4b28a' });
    ellipse(g, W * 0.495, H * 0.39 + strainY, 34, 24, { fill: '#e4b28a', lw: 3.5, ink: INK_ACTOR });
    for (let fg = 0; fg < 4; fg++) {
      ellipse(g, W * 0.512, H * 0.365 + strainY + fg * 11, 16, 6, { fill: '#d8a27a', lw: 2.5, ink: INK_ACTOR });
    }
    // Right actor (Felix olive harbor sleeve + braced forearm + fingers gripping lower span)
    polyS(g, [[W, H * 0.54], [W * 0.74, H * 0.52 + strainY * 0.5], [W * 0.72, H * 0.66 + strainY * 0.5], [W, H * 0.70]], {
      fill: '#667458',
      lw: 4,
      ink: INK_ACTOR,
    });
    line(g, W * 0.75, H * 0.59 + strainY * 0.5, W * 0.52, H * 0.56 + strainY, { lw: 46, ink: INK_ACTOR });
    line(g, W * 0.75, H * 0.59 + strainY * 0.5, W * 0.52, H * 0.56 + strainY, { lw: 38, ink: '#dfa980' });
    ellipse(g, W * 0.505, H * 0.56 + strainY, 34, 25, { fill: '#dfa980', lw: 3.5, ink: INK_ACTOR });
    for (let fg = 0; fg < 4; fg++) {
      ellipse(g, W * 0.488, H * 0.535 + strainY + fg * 11, 16, 6, { fill: '#cfa07b', lw: 2.5, ink: INK_ACTOR });
    }
  } else {
    // 'lantern_grab': Wooden wall bracket + large detailed bronze oil lantern + Aelia's articulated arm & fingers
    rect(g, W * 0.52, H * 0.24, W * 0.36, 32, { fill: '#7c593e', lw: 4, ink: INK_TIMBER, r: 4 });
    const liftUp = gripW > 0.65 ? smooth((gripW - 0.65) / 0.35) * 28 : 0;
    const lx = W * 0.56;
    const ly = H * 0.34 - liftUp;
    drawAncientBronzeOilLantern(g, lx, ly, 3.2, {
      lit: true,
      flameStrength: 1.15,
      swingRad: Math.sin(globalT * 4.2) * 0.05,
      wind: windVal,
      globalT,
    });
    const hx = lerp(W * 0.32, lx - 8, gripW);
    const hy = lerp(H * 0.46, ly - 2, gripW);
    polyS(
      g,
      [
        [0, H * 0.52],
        [W * 0.24, H * 0.46],
        [W * 0.27, H * 0.60],
        [0, H * 0.68],
      ],
      { fill: '#b6423a', lw: 4, ink: INK_ACTOR },
    );
    line(g, W * 0.24, H * 0.53, hx - 14, hy + 4, { lw: 42, ink: INK_ACTOR });
    line(g, W * 0.24, H * 0.53, hx - 14, hy + 4, { lw: 34, ink: '#e4b28a' });
    ellipse(g, hx, hy + 2, 28, 20, { fill: '#e4b28a', lw: 3.5, ink: INK_ACTOR });
    for (let fg = 0; fg < 4; fg++) {
      ellipse(g, hx + 16, hy - 8 + fg * 8, 13, 5.5, { fill: '#d8a27a', lw: 2.4, ink: INK_ACTOR });
    }
  }
}

/**
 * Genuine foreshortened upward 2D projection (`authored_2d_low_angle`) looking up the stone
 * watchtower shaft as the hoisted bronze oil lantern enters the sheltered beacon alcove (`S06`).
 */
export function drawAuthoredLowWatchtowerView(g, globalT, world = {}, mech = {}, u = 0) {
  const W = E.W;
  const H = E.H;
  drawTwilightStormHarborSky(g, globalT, { wind: world.wind ?? 0.78, duskWarmth: 0.14, showGulls: true });

  const liftProg = clamp(interpMech(mech, 'lantern_lift', u, 0.75), 0, 1);
  // Upward-converging stone tower perspective
  polyS(
    g,
    [
      [W * 0.22, H],
      [W * 0.38, H * 0.16],
      [W * 0.78, H * 0.16],
      [W * 0.94, H],
    ],
    { fill: '#938676', lw: 4, ink: INK_STONE },
  );
  // Sheltered stone beacon alcove near top
  rect(g, W * 0.43, H * 0.18, W * 0.28, H * 0.22, { fill: '#6c5846', lw: 3.5, ink: INK_STONE, r: 12 });
  polyS(g, [[W * 0.34, H * 0.17], [W * 0.58, H * 0.06], [W * 0.82, H * 0.17]], {
    fill: '#a45640',
    lw: 3.5,
    ink: INK_STONE,
  });

  // Overhead cathead & rotating sheave seen from below
  rect(g, W * 0.26, H * 0.24, W * 0.20, 22, { fill: '#7c5a42', lw: 3, ink: INK_TIMBER });
  const sx = W * 0.31;
  const sy = H * 0.27;
  circle(g, sx, sy, 24, { fill: '#b28752', lw: 3.5, ink: INK_TIMBER });

  // Taut hoist rope & rising oil lantern entering upper alcove
  const lx = lerp(sx, W * 0.56, smooth(clamp((liftProg - 0.45) / 0.55, 0, 1)));
  const ly = lerp(H * 0.74, H * 0.24, liftProg);
  line(g, W * 0.36, H, sx + 10, sy, { lw: 5, ink: '#cbb082' });
  line(g, sx - 10, sy, lx, ly, { lw: 5, ink: '#cbb082' });
  drawAncientBronzeOilLantern(g, lx, ly, 2.0, {
    lit: true,
    flameStrength: 1.2,
    swingRad: Math.sin(globalT * 4.0) * 0.06 * (1 - liftProg * 0.6),
    wind: Number(world.wind ?? 0.75),
    globalT,
  });
}

/**
 * Draw mobile-readable end card plaque without obscuring hero characters or beacon tower.
 */
export function drawPortusEndCard(g, title, subtitle) {
  const W = E.W;
  const H = E.H;
  const cardW = 760;
  const cardH = subtitle ? 116 : 84;
  const x0 = 72;
  const y0 = 64;

  g.save();
  rect(g, x0, y0, cardW, cardH, {
    fill: 'rgba(46, 56, 70, 0.90)',
    lw: 3,
    ink: '#e0b464',
    r: 10,
  });
  g.fillStyle = '#fff5dc';
  g.font = '700 38px Georgia, serif';
  g.textBaseline = 'top';
  g.fillText(String(title || 'ONE LIGHT. ONE SAFE PASSAGE.'), x0 + 28, y0 + 20);
  if (subtitle) {
    g.fillStyle = '#dfd4c0';
    g.font = '500 21px Georgia, serif';
    g.fillText(String(subtitle), x0 + 28, y0 + 72);
  }
  g.restore();
}

/**
 * Core deterministic harbor shot renderer driven by `MotionPlan`, `worldState`, `mechanics`,
 * `cameraSegments`, optional `Rigby2D` skeletal runtime, and optional `claude_motion` FX.
 */
export function renderHarborShot(g, lt, info) {
  const W = E.W;
  const H = E.H;
  const shot = info?.shot || {};
  const dur = Math.max(0.1, Number(shot.dur || 3.5));
  const u = clamp(lt / dur, 0, 1);
  const globalT = Number(info?.globalT ?? (Number(shot.start || 0) + lt));
  const world = shot.world_state || {};
  const mech = shot.mechanics || {};
  const args = shot.args || {};
  const fxProfile = args.fx_profile || args.motionPlan?.fx_profile || 'none';
  const backend = args.actorBackend || 'natural_canvas';

  // Separated action clock: cameraSegments & voice use exact `lt` / `globalT`;
  // only local actor pose/FX uses `actionT` when `fxProfile === 'claude_selective'`!
  let actionT = globalT;
  if (fxProfile === 'claude_selective' && Array.isArray(args.actionWarpSpecs) && args.actionWarpSpecs.length > 0) {
    const stops = args.actionWarpSpecs.map((w) =>
      Array.isArray(w) ? w : [Number(w.at ?? 0), Number(w.hold ?? 0.05)],
    );
    const clock = createSeparatedActionClock({
      shotStartSec: Number(shot.start || 0),
      shotEndSec: Number(shot.end || Number(shot.start || 0) + dur),
      stops,
      fxProfile,
    });
    actionT = clock.actionTime(globalT);
  }

  const seg = getActiveCameraSegment(shot, lt);
  const projMode = seg.projection_mode || args.viewMode || 'continuous_2d_canvas';

  // Evaluate MotionPlan tracks at `actionT`
  const planObj = args.motionPlan || {};
  const allTracks = args.motionTracks || planObj.tracks || [];
  const shotTracks = allTracks.filter((tr) => !tr.shot_id || tr.shot_id === shot.id);
  const windVal = Number(mech.wind_strength ?? world.wind ?? 0.68);
  const worldStateForEval = {
    environment: { wind: windVal },
    objects: { ...(world.objects || {}) },
  };

  // Multi-actor shared object interaction when >= 2 tracks act in same shot
  const resolvedObjects =
    shotTracks.length >= 2 ? evaluateMultiActorInteraction(shotTracks, actionT, worldStateForEval) : undefined;
  const evalByActor = {};
  for (const tr of shotTracks) {
    evalByActor[tr.actor_id] = evaluateMotionTrackAt(tr, actionT, worldStateForEval, {
      resolvedObjects,
      seed: Number(args.seed ?? 1476),
      cameraScale: seg.scale || 'medium',
    });
  }

  // Authored 2D close insert or low watchtower angle (genuine vector projection, zero fake crop!)
  if (projMode === 'authored_2d_insert') {
    const primaryEv = Object.values(evalByActor)[0] || null;
    const kind =
      mech.insert_kind ||
      (mech.opening_flame_snuff
        ? 'beacon_snuff'
        : String(seg.subject_focus || '').includes('rope')
          ? 'rope_haul'
          : 'lantern_grab');
    drawAuthoredGripInsert(g, globalT, kind, primaryEv, world, mech, u, Number(seg.local_u ?? u));
    if (fxProfile === 'claude_selective' && Array.isArray(args.fxEvents) && args.fxEvents.length > 0) {
      const pixelEvents = args.fxEvents.map((fe) => ({
        ...fe,
        x: Number(fe.x ?? 0.5) <= 2.0 ? Number(fe.x ?? 0.5) * W : Number(fe.x),
        y: Number(fe.y ?? 0.5) <= 2.0 ? Number(fe.y ?? 0.5) * H : Number(fe.y),
      }));
      applyHarborInteractionFX(g, {
        fxProfile,
        realT: globalT,
        events: pixelEvents,
        seed: Number(args.seed ?? 1476),
      });
    }
    return;
  }
  if (projMode === 'authored_2d_low_angle') {
    drawAuthoredLowWatchtowerView(g, globalT, world, mech, u);
    return;
  }

  // Continuous 2D harbor canvas view with smooth camera segment framing (clamped so 0px black border!)
  g.save();
  const z = clamp(Number(seg.zoom ?? 1.0), 1.0, 1.26);
  if (z > 1.002) {
    const minPan = 0.5 / z;
    const maxPan = 1.0 - 0.5 / z;
    const cx = clamp(Number(seg.panX ?? 0.5), minPan, maxPan) * W;
    const cy = clamp(Number(seg.panY ?? 0.5), minPan, maxPan) * H;
    g.translate(W * 0.5, H * 0.5);
    g.scale(z, z);
    g.translate(-cx, -cy);
  }

  const duskWarmth = interpMech(mech, 'dusk_warmth', u, 0.22);
  drawTwilightStormHarborSky(g, globalT, {
    wind: windVal,
    duskWarmth,
    showGulls: mech.show_gulls !== false,
  });

  drawHarborSeaShoalsAndShip(g, globalT, { ...world, wind: windVal }, mech, u);

  // Determine live rope grip anchor from Felix's right hand if Felix is in shot
  const felixEv = evalByActor.felix;
  const aeliaEv = evalByActor.aelia;
  const ropeGripWorld = felixEv
    ? [felixEv.rightHandWorld[0] * W, felixEv.rightHandWorld[1] * H]
    : [W * 0.64, H * 0.71];

  const lanternGrabbed =
    Boolean(mech.lantern_carried) ||
    (Boolean(mech.lantern_grab_in_shot) && u >= Number(mech.lantern_grab_u ?? 0.42));

  drawHarborMoleAndWatchtower(g, globalT, { ...world, wind: windVal }, mech, u, {
    groundY: Number(args.groundY ?? 0.84),
    towerX: Number(args.towerX ?? 0.74),
    showSnuffedBrazier: Boolean(mech.show_snuffed_brazier),
    showLanternRack: Boolean(mech.show_lantern_rack),
    lanternTakenFromRack: lanternGrabbed,
    lanternOnHoist: Boolean(mech.lantern_on_hoist),
    lanternSwingRad: Number(mech.lantern_swing_amp ?? 0.08) * Math.sin(actionT * 5.2),
    ropeGripWorld,
  });

  // Render actors according to selected backend (`natural_canvas`, `rigby2d`, or `legacy_v14_7_5_1`)
  const peopleList = Array.isArray(args.people) ? args.people : [];
  if (backend === 'legacy_v14_7_5_1') {
    for (const p of peopleList) {
      drawLegacySineHarborActor(g, p.id, p, lt, dur, {
        carryLantern: p.id === 'aelia' && lanternGrabbed && !mech.lantern_on_hoist,
      });
    }
  } else if (backend === 'rigby2d' && _cachedRigbyBrowserAsset) {
    for (const p of peopleList) {
      const ev = evalByActor[p.id];
      const rx = (ev ? ev.root[0] : Number(p.x ?? 0.45)) * W;
      const ry = (ev ? ev.root[1] : Number(p.y ?? 0.84)) * H;
      const hPx = (ev ? ev.heightNorm : Number(p.h ?? 0.28)) * H;
      const animName = args.rigbyAnimByActor?.[p.id] || `mp_${shot.id}_${p.id}`;
      renderRigbyActorToCanvas(
        g,
        actionT,
        { x: rx, y: ry, facing: ev?.facing ?? 1, actorHeight: hPx },
        _cachedRigbyBrowserAsset,
        {
          animationName: animName,
          animStartSec: Number(shot.start || 0),
          actorHeight: hPx,
          tint: p.id === 'felix' ? [0.88, 0.95, 0.86, 1.0] : [1, 1, 1, 1],
        },
      );
      if (p.id === 'aelia' && lanternGrabbed && !mech.lantern_on_hoist && ev) {
        drawAncientBronzeOilLantern(g, ev.rightHandWorld[0] * W, ev.rightHandWorld[1] * H + 4, 0.95, {
          lit: true,
          flameStrength: 1.0,
          swingRad: Math.sin(actionT * 4.6) * 0.09,
          wind: windVal,
          globalT,
        });
      }
    }
  } else {
    // Default FL-01 V14.7.6 Natural Canvas IK + Contact + Secondary Motion performer
    const actorIdsToDraw =
      Object.keys(evalByActor).length > 0
        ? Object.keys(evalByActor)
        : peopleList.map((p) => p.id);
    for (const aid of actorIdsToDraw) {
      const ev = evalByActor[aid];
      if (!ev) continue;
      const isAelia = String(aid).toLowerCase().includes('aelia');
      drawHarborActorFromMotionPlan(g, aid, ev, {
        carryLantern: isAelia && lanternGrabbed && !mech.lantern_on_hoist,
        lanternSwingRad: Math.sin(actionT * 4.8) * (mech.gust_setback ? 0.24 : 0.07),
        wind: windVal,
        relieved: Boolean(mech.relieved_look),
        globalT,
      });
    }
  }

  // Unseen-script generic civic props (woven basket, terracotta amphora, dock lantern post)
  for (const pr of args.props || []) {
    if (pr.kind === 'woven_basket') {
      const bx = Number(pr.x ?? 0.48) * W;
      const by = Number(pr.y ?? 0.78) * H;
      ellipse(g, bx, by, 26, 18, { fill: '#c8a262', lw: 2.8, ink: INK_TIMBER });
    } else if (pr.kind === 'heavy_amphora') {
      const liftY = aeliaEv || Object.values(evalByActor)[0]
        ? Object.values(evalByActor)[0].rightHandWorld[1] * H + 12
        : Number(pr.y ?? 0.76) * H;
      const ax = Number(pr.x ?? 0.50) * W;
      ellipse(g, ax, liftY, 20, 32, { fill: '#b96948', lw: 2.8, ink: INK_TIMBER });
    } else if (pr.kind === 'dock_lantern_post') {
      const px = Number(pr.x ?? 0.62) * W;
      const py = Number(args.groundY ?? 0.84) * H;
      line(g, px, py, px, py - 156, { lw: 6, ink: INK_TIMBER });
      drawAncientBronzeOilLantern(g, px - 18, py - 148, 1.0, { lit: true, flameStrength: 1.0, globalT });
    }
  }

  // Optional sparse interaction FX from integrations/claude_motion/adapter.js
  if (fxProfile === 'claude_selective' && Array.isArray(args.fxEvents) && args.fxEvents.length > 0) {
    const pixelEvents = args.fxEvents.map((fe) => ({
      ...fe,
      x: Number(fe.x ?? 0.5) <= 2.0 ? Number(fe.x ?? 0.5) * W : Number(fe.x),
      y: Number(fe.y ?? 0.5) <= 2.0 ? Number(fe.y ?? 0.5) * H : Number(fe.y),
    }));
    applyHarborInteractionFX(g, {
      fxProfile,
      realT: globalT,
      events: pixelEvents,
      seed: Number(args.seed ?? 1476),
    });
  }

  g.restore();

  for (const pr of args.props || []) {
    if (pr.kind === 'portus_end_card') {
      drawPortusEndCard(g, pr.title, pr.subtitle);
    }
  }
}

export function registerPortusShots(shotIds = ['S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08']) {
  for (const sid of shotIds) {
    registerShot(sid, {
      draw(ctx, lt, info) {
        renderHarborShot(ctx, lt, info);
      },
    });
  }
}
