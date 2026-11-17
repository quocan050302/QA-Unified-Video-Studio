// character.js (packs/squire/cinematic2d) — KH-02.1 Evolutionary Squire 2D Character & Quadruped Renderer.
// Pure Canvas2D. Zero Three.js / WebGL / external bitmap dependencies.
// Preserves Production Squire round cream caricature head & #392a21 ink identity while upgrading
// tapered limbs, articulated hands, 2-3 cel-shading planes, cloth folds, and turnaround views.

import { E, clamp, lerp, ease, noise } from '/engine/core.js';
import {
  OUT,
  PAL,
  alpha,
  darker,
  lighter,
  shape,
  ellipse,
  circ,
  line,
  scaleStrokeWeight2D,
  strokeTapered2D,
  fillCelShadedShape2D,
  shadeClothFold2D,
  drawInkEdgeHighlight2D,
} from '../ink.js';
import { ik2, blinkAt } from '../chara.js';

export const CINEMATIC_CAST_PROFILES = {
  TAVI: {
    character_id: 'char_tavi_keeper',
    canonical_name: 'TAVI',
    role: 'apprentice_bell_keeper',
    rig_class: 'human_squire_caricature_2d',
    stature_scale: 0.95,
    head_scale: 1.03,
    skin: '#f4ede1',
    skinShade: '#d6c8c6',
    skinDeep: '#bfaeb0',
    hair: 'tousled_tufts',
    hairColor: '#4c3020',
    hairShade: '#2f1d13',
    tunic: '#b84b39',
    tunicShade: '#863124',
    tunicDeep: '#5c1e15',
    undertunic: '#eadbc2',
    undertunicShade: '#cbb798',
    scarf: '#df9b43',
    scarfShade: '#ad6f22',
    belt: '#694226',
    sandal: '#6e472b',
    brass: '#d4a24c',
    freckles: true,
    keyRing: true,
  },
  LYRA: {
    character_id: 'char_lyra_master',
    canonical_name: 'LYRA',
    role: 'elder_bell_mistress',
    rig_class: 'human_squire_caricature_2d',
    stature_scale: 0.91,
    head_scale: 1.01,
    stoop: 0.055,
    skin: '#f1e7d8',
    skinShade: '#d2c3bf',
    skinDeep: '#b8a6a4',
    hair: 'elder_braided_bun',
    hairColor: '#9e9a95',
    hairShade: '#706c68',
    tunic: '#415980',
    tunicShade: '#2b3d59',
    tunicDeep: '#1c293d',
    undertunic: '#dfd3be',
    undertunicShade: '#bfb097',
    palla: '#d8c39e',
    pallaShade: '#b39b74',
    belt: '#8c6635',
    sandal: '#5c3d28',
    brass: '#c99642',
    ageLines: true,
  },
  CITIZEN_A: {
    character_id: 'char_courtyard_baker',
    canonical_name: 'MARCUS',
    role: 'courtyard_resident',
    rig_class: 'human_squire_caricature_2d',
    stature_scale: 0.98,
    head_scale: 1.0,
    skin: '#f3eadc',
    skinShade: '#d5c7c4',
    skinDeep: '#bca9a7',
    hair: 'curly_crop',
    hairColor: '#5c3b26',
    hairShade: '#3a2417',
    tunic: '#687d48',
    tunicShade: '#495931',
    tunicDeep: '#323e21',
    undertunic: '#e6d8bf',
    undertunicShade: '#c6b598',
    belt: '#634127',
    sandal: '#613f26',
    brass: '#c59240',
  },
};

export const CINEMATIC_EXPRESSIONS = {
  calm_watchful:     { eyes: 'focused', brows: 'soft', mouth: 'calm_smile', pupilScale: 1.0 },
  anxious_alert:     { eyes: 'open_alert', brows: 'worried_tilt', mouth: 'wavy_anxious', sweat: true, pupilScale: 0.86 },
  wide_shock:        { eyes: 'wide_shock', brows: 'high_arch', mouth: 'gasp_o', sweat: true, pupilScale: 0.62 },
  strained_pull:     { eyes: 'squint_effort', brows: 'furrowed', mouth: 'clenched_effort', sweat: true, blush: true },
  determined_climb:  { eyes: 'sharp_focus', brows: 'angled_drive', mouth: 'set_firm', pupilScale: 0.92 },
  breathless_relief: { eyes: 'soft_wide', brows: 'relieved_up', mouth: 'sigh_relief', sweat: true, blush: true },
  deadpan_disbelief: { eyes: 'half_lid', brows: 'flat_deadpan', mouth: 'deadpan_line', pupilScale: 0.95 },
  sleepy_blink:      { eyes: 'half_lid', brows: 'soft', mouth: 'small_yawn', pupilScale: 0.95 },
  startled_gasp:     { eyes: 'wide_shock', brows: 'high_arch', mouth: 'gasp_o', pupilScale: 0.68 },
  grumpy_glare:      { eyes: 'half_lid', brows: 'furrowed', mouth: 'frown_deep', pupilScale: 0.9 },
  wry_amusement:     { eyes: 'focused', brows: 'asymmetric_smug', mouth: 'smirk_warm', blush: true },
  // Legacy Squire expression aliases for seamless compatibility
  neutral:           { eyes: 'focused', brows: 'flat_deadpan', mouth: 'deadpan_line', pupilScale: 1.0 },
  worried:           { eyes: 'open_alert', brows: 'worried_tilt', mouth: 'wavy_anxious', sweat: true, pupilScale: 0.86 },
  shock:             { eyes: 'wide_shock', brows: 'high_arch', mouth: 'gasp_o', pupilScale: 0.62 },
  determined:        { eyes: 'sharp_focus', brows: 'angled_drive', mouth: 'set_firm', pupilScale: 0.92 },
  tired:             { eyes: 'half_lid', brows: 'worried_tilt', mouth: 'sigh_relief', sweat: true },
  happy:             { eyes: 'happy_arc', brows: 'relieved_up', mouth: 'calm_smile', blush: true },
};

function _taperedLimbEnvelope(g, p0, p1, p2, w0, w1, w2, o = {}) {
  const { fill = '#f4ede1', shadow = null, lw = 4.2, ink = OUT, rim = null } = o;
  const pts = _buildTwoSegSpine(p0, p1, p2, 10);
  const m = pts.length - 1;
  const left = [], right = [];
  for (let i = 0; i <= m; i++) {
    const prev = pts[Math.max(0, i - 1)], next = pts[Math.min(m, i + 1)];
    const dx = next[0] - prev[0], dy = next[1] - prev[1];
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    const u = i / m;
    const w = u < 0.5 ? lerp(w0, w1, u * 2) : lerp(w1, w2, (u - 0.5) * 2);
    left.push([pts[i][0] + nx * w * 0.5, pts[i][1] + ny * w * 0.5]);
    right.push([pts[i][0] - nx * w * 0.5, pts[i][1] - ny * w * 0.5]);
  }
  const cx = (p0[0] + p1[0] + p2[0]) / 3, cy = (p0[1] + p1[1] + p2[1]) / 3;
  const span = Math.hypot(p2[0] - p0[0], p2[1] - p0[1]) * 0.65 + w0;
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(left[0][0], left[0][1]);
      for (let i = 1; i < left.length; i++) c.lineTo(left[i][0], left[i][1]);
      c.arc(p2[0], p2[1], w2 * 0.48, Math.atan2(left[m][1] - p2[1], left[m][0] - p2[0]), Math.atan2(right[m][1] - p2[1], right[m][0] - p2[0]));
      for (let i = right.length - 1; i >= 0; i--) c.lineTo(right[i][0], right[i][1]);
      c.closePath();
    },
    {
      fill,
      shadow,
      rim,
      bounds: [cx, cy, span, span],
      lw,
      ink,
    }
  );
  // Subtle elbow/knee anatomical crease (tapered, never a circle sticker)
  const d1x = p2[0] - p0[0], d1y = p2[1] - p0[1];
  const bendMag = Math.hypot(p1[0] - (p0[0] + p2[0]) / 2, p1[1] - (p0[1] + p2[1]) / 2);
  if (bendMag > w1 * 0.22 && (Math.abs(d1x) + Math.abs(d1y) > 1)) {
    const cxCrease = lerp(p1[0], (p0[0] + p2[0]) / 2, 0.28);
    const cyCrease = lerp(p1[1], (p0[1] + p2[1]) / 2, 0.28);
    strokeTapered2D(
      g,
      [[p1[0] - w1 * 0.22, p1[1]], [cxCrease, cyCrease]],
      { lw: lw * 0.55, ink: alpha(OUT, 0.7) }
    );
  }
}

function _buildTwoSegSpine(p0, p1, p2, n = 10) {
  const out = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    // Quadratic blend around joint p1 so elbow/knee bends organically without sharp折 kinks or circle caps
    const c1x = lerp(p0[0], p1[0], 0.85), c1y = lerp(p0[1], p1[1], 0.85);
    const c2x = lerp(p2[0], p1[0], 0.85), c2y = lerp(p2[1], p1[1], 0.85);
    if (t < 0.42) {
      const k = t / 0.42;
      out.push([lerp(p0[0], c1x, k), lerp(p0[1], c1y, k)]);
    } else if (t <= 0.58) {
      const k = (t - 0.42) / 0.16, ik = 1 - k;
      out.push([
        ik * ik * c1x + 2 * ik * k * p1[0] + k * k * c2x,
        ik * ik * c1y + 2 * ik * k * p1[1] + k * k * c2y,
      ]);
    } else {
      const k = (t - 0.58) / 0.42;
      out.push([lerp(c2x, p2[0], k), lerp(c2y, p2[1], k)]);
    }
  }
  return out;
}

export function drawCinematicHand2D(g, x, y, r, o = {}) {
  const {
    pose = 'relaxed', // rope_grip | pin_catch | open_recoil | point_alert | lantern_hold | palm_raised_react | relaxed
    ang = 0,
    side = 1,
    skin = '#f4ede1',
    skinShade = '#d6c8c6',
    lw = 3.2,
    wrapLeather = false,
  } = o;
  g.save();
  g.translate(x, y);
  g.rotate(ang);
  if (side < 0) g.scale(-1, 1);

  if (wrapLeather) {
    fillCelShadedShape2D(
      g,
      (c) => c.roundRect(-r * 0.78, -r * 1.18, r * 1.56, r * 0.68, r * 0.22),
      { fill: '#7a4d2b', shadow: alpha('#472913', 0.5), bounds: [0, -r * 0.85, r, r * 0.5], lw: lw * 0.88 }
    );
  }

  // Palm block (organic trapezoidal palm, NOT a round white mitten)
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-r * 0.72, -r * 0.62);
      c.quadraticCurveTo(0, -r * 0.78, r * 0.74, -r * 0.55);
      c.quadraticCurveTo(r * 0.88, r * 0.15, r * 0.64, r * 0.68);
      c.quadraticCurveTo(0, r * 0.85, -r * 0.68, r * 0.62);
      c.closePath();
    },
    { fill: skin, shadow: alpha(skinShade, 0.85), bounds: [0, 0, r * 0.9, r * 0.9], lw }
  );

  if (pose === 'rope_grip' || pose === 'pin_catch' || pose === 'lantern_hold') {
    // 3 curled fingers wrapping tightly around prop axis + opposing thumb lock
    for (let i = 0; i < 3; i++) {
      const fy = -r * 0.24 + i * r * 0.36;
      fillCelShadedShape2D(
        g,
        (c) => c.roundRect(-r * 0.55, fy, r * 1.32, r * 0.34, r * 0.16),
        { fill: skin, shadow: alpha(skinShade, 0.75), bounds: [r * 0.1, fy + r * 0.17, r * 0.7, r * 0.25], lw: lw * 0.82 }
      );
    }
    // Opposing thumb locked across index finger
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(-r * 0.68, -r * 0.35);
        c.quadraticCurveTo(-r * 0.15, -r * 0.76, r * 0.48, -r * 0.32);
        c.quadraticCurveTo(r * 0.35, r * 0.04, -r * 0.52, r * 0.02);
        c.closePath();
      },
      { fill: skin, shadow: alpha(skinShade, 0.6), bounds: [-r * 0.1, -r * 0.25, r * 0.6, r * 0.4], lw: lw * 0.86 }
    );
  } else if (pose === 'open_recoil' || pose === 'palm_raised_react') {
    // Splayed fingers showing sudden slip / startled reaction
    const angles = [-0.42, -0.14, 0.14, 0.4];
    angles.forEach((fa, idx) => {
      g.save();
      g.translate((idx - 1.5) * r * 0.36, r * 0.52);
      g.rotate(fa);
      fillCelShadedShape2D(
        g,
        (c) => c.roundRect(-r * 0.18, 0, r * 0.36, r * (idx === 1 || idx === 2 ? 0.92 : 0.76), r * 0.16),
        { fill: skin, shadow: alpha(skinShade, 0.6), bounds: [0, r * 0.4, r * 0.25, r * 0.5], lw: lw * 0.78 }
      );
      g.restore();
    });
    // Splayed thumb
    g.save();
    g.translate(r * 0.68, -r * 0.1);
    g.rotate(-0.72);
    fillCelShadedShape2D(
      g,
      (c) => c.roundRect(-r * 0.2, 0, r * 0.4, r * 0.74, r * 0.18),
      { fill: skin, shadow: alpha(skinShade, 0.6), bounds: [0, r * 0.3, r * 0.25, r * 0.4], lw: lw * 0.8 }
    );
    g.restore();
  } else if (pose === 'point_alert') {
    // Extended index finger + 2 tucked fingers
    fillCelShadedShape2D(
      g,
      (c) => c.roundRect(r * 0.22, r * 0.35, r * 0.38, r * 1.05, r * 0.16),
      { fill: skin, shadow: alpha(skinShade, 0.65), bounds: [r * 0.4, r * 0.85, r * 0.25, r * 0.55], lw: lw * 0.82 }
    );
    for (let i = 0; i < 2; i++) {
      fillCelShadedShape2D(
        g,
        (c) => c.roundRect(-r * 0.58 + i * r * 0.38, r * 0.32, r * 0.38, r * 0.48, r * 0.16),
        { fill: skin, shadow: alpha(skinShade, 0.75), bounds: [-r * 0.38 + i * r * 0.38, r * 0.55, r * 0.25, r * 0.3], lw: lw * 0.78 }
      );
    }
    ellipse(g, r * 0.68, r * 0.08, r * 0.34, r * 0.22, { fill: skin, lw: lw * 0.8, rot: 0.45 });
  } else {
    // Natural relaxed semi-curled fingers + thumb
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(-r * 0.58, r * 0.48);
        c.quadraticCurveTo(-r * 0.55, r * 1.02, 0, r * 1.04);
        c.quadraticCurveTo(r * 0.58, r * 1.0, r * 0.58, r * 0.48);
        c.closePath();
      },
      { fill: skin, shadow: alpha(skinShade, 0.7), bounds: [0, r * 0.75, r * 0.6, r * 0.4], lw: lw * 0.84 }
    );
    strokeTapered2D(g, [[-r * 0.18, r * 0.54], [-r * 0.15, r * 0.94]], { lw: lw * 0.52 });
    strokeTapered2D(g, [[r * 0.2, r * 0.54], [r * 0.18, r * 0.94]], { lw: lw * 0.52 });
    ellipse(g, r * 0.72, -r * 0.04, r * 0.36, r * 0.24, { fill: skin, lw: lw * 0.82, rot: 0.55 });
  }

  g.restore();
  return [x, y];
}

export function drawCinematicFace2D(g, cx, cy, R, o = {}) {
  const exprKey = o.expression || o.face || 'calm_watchful';
  const expr = typeof exprKey === 'object' ? exprKey : (CINEMATIC_EXPRESSIONS[exprKey] || CINEMATIC_EXPRESSIONS.calm_watchful);
  const lw = o.lw ?? scaleStrokeWeight2D(R * 5.2, 3.9, 1.5, 7.2);
  const view = o.view || 'three_quarter'; // front | three_quarter | profile
  const look = clamp(o.look ?? (view === 'profile' ? 0.85 : view === 'three_quarter' ? 0.28 : 0), -1.1, 1.1);
  const pupilSnapX = clamp((o.pupilX ?? look) * 1.15, -1.2, 1.2);
  const pupilSnapY = clamp(o.pupilY ?? 0, -1.0, 1.0);
  const blinkK = o.blink ?? blinkAt(o.t || 0, o.seed || 3);

  const shiftX = view === 'profile' ? R * 0.34 : view === 'three_quarter' ? R * 0.15 : look * R * 0.14;
  const ey = cy + R * 0.03;
  const sp = view === 'profile' ? R * 0.14 : view === 'three_quarter' ? R * 0.29 : R * 0.33;

  // Blush / effort warmth
  if (expr.blush || o.blush) {
    const cheeks = view === 'profile' ? [[cx + shiftX - R * 0.08, ey + R * 0.22]] : [
      [cx + shiftX - sp - R * 0.05, ey + R * 0.21],
      [cx + shiftX + sp + R * 0.04, ey + R * 0.21],
    ];
    for (const [bx, by] of cheeks) {
      ellipse(g, bx, by, R * 0.13, R * 0.075, { fill: alpha(PAL.blush, 0.68), lw: 0 });
    }
  }

  // Youth freckles (Tavi)
  if (o.freckles) {
    const groups = view === 'profile' ? [0] : [-1, 1];
    for (const s of groups) {
      for (let i = 0; i < 3; i++) {
        const fx = cx + shiftX + s * (sp * 0.95) + (i - 1) * R * 0.055;
        const fy = ey + R * 0.19 + (i % 2) * R * 0.028;
        circ(g, fx, fy, R * 0.015, { fill: '#c47d56', lw: 0 });
      }
    }
  }

  // Elder wisdom lines (Lyra)
  if (o.ageLines) {
    const sides = view === 'profile' ? [1] : [-1, 1];
    for (const s of sides) {
      const lx = cx + shiftX + s * (sp + R * 0.08);
      strokeTapered2D(g, [[lx - s * R * 0.08, ey + R * 0.14], [lx + s * R * 0.05, ey + R * 0.18]], {
        lw: lw * 0.46,
        ink: alpha('#7c6760', 0.65),
      });
    }
  }

  // Subtle nose bridge cue in 3/4 and profile views (preserves Squire front roundness while clarifying turnaround!)
  if (view === 'three_quarter' || view === 'profile') {
    const nx = cx + shiftX + (view === 'profile' ? R * 0.56 : R * 0.05);
    strokeTapered2D(
      g,
      [[nx - R * 0.03, ey + R * 0.04], [nx + R * 0.07, ey + R * 0.16], [nx - R * 0.01, ey + R * 0.21]],
      { lw: lw * 0.62, ink: alpha(OUT, 0.85) }
    );
  }

  // Eyes (1 eye visible in strict profile, 2 in front/3-4)
  const eyeSides = view === 'profile' ? [1] : [-1, 1];
  for (const s of eyeSides) {
    const ex = view === 'profile'
      ? cx + shiftX + R * 0.22
      : cx + shiftX + s * sp * (view === 'three_quarter' && s > 0 ? 0.88 : 1.0);
    const scaleSide = view === 'three_quarter' && s > 0 ? 0.92 : 1.0;
    _drawSingleCinematicEye(g, ex, ey, R * scaleSide, expr, lw, pupilSnapX, pupilSnapY, blinkK, s, o.skin || PAL.skin);
    _drawSingleCinematicBrow(g, ex, ey - R * 0.22, R * scaleSide, expr.brows, lw, s);
  }

  // Mouth
  const mx = cx + shiftX * (view === 'profile' ? 1.12 : 0.82);
  const my = cy + R * 0.42;
  _drawCinematicMouth(g, mx, my, R, expr.mouth, lw, o.talk || 0);

  // Sweat drop when anxious/strained
  if (expr.sweat || o.sweat) {
    const sx = cx - R * 0.66, sy = cy - R * 0.34 + Math.sin((o.t || 0) * 5) * R * 0.025;
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(sx, sy - R * 0.14);
        c.quadraticCurveTo(sx + R * 0.095, sy + R * 0.04, sx, sy + R * 0.08);
        c.quadraticCurveTo(sx - R * 0.095, sy + R * 0.04, sx, sy - R * 0.14);
        c.closePath();
      },
      { fill: '#bce5fa', shadow: alpha('#7ab5d6', 0.6), bounds: [sx, sy, R * 0.1, R * 0.12], lw: lw * 0.58 }
    );
  }
}

function _drawSingleCinematicEye(g, x, y, R, expr, lw, px, py, blinkK, side, skinHex) {
  const kind = expr.eyes || 'focused';
  if (blinkK > 0.5 && kind !== 'squint_effort' && kind !== 'happy_arc') {
    strokeTapered2D(g, [[x - R * 0.12, y + R * 0.01], [x, y + R * 0.035], [x + R * 0.12, y + R * 0.01]], { lw: lw * 0.95 });
    return;
  }
  if (kind === 'squint_effort') {
    const s = side < 0 ? 1 : -1;
    strokeTapered2D(
      g,
      [[x - R * 0.12 * s, y - R * 0.075], [x + R * 0.09 * s, y], [x - R * 0.12 * s, y + R * 0.075]],
      { lw: lw * 1.05, startRatio: 0.45, midRatio: 1.15, endRatio: 0.45 }
    );
    return;
  }
  if (kind === 'happy_arc') {
    strokeTapered2D(g, [[x - R * 0.12, y + R * 0.03], [x, y - R * 0.07], [x + R * 0.12, y + R * 0.03]], { lw: lw * 0.95 });
    return;
  }
  if (kind === 'wide_shock' || kind === 'open_alert' || kind === 'soft_wide') {
    const rx = kind === 'wide_shock' ? R * 0.165 : R * 0.138;
    const ry = kind === 'wide_shock' ? R * 0.185 : R * 0.148;
    ellipse(g, x, y, rx, ry, { fill: '#ffffff', lw: lw * 0.82 });
    const pr = rx * (expr.pupilScale || 0.72) * 0.55;
    const ox = px * (rx - pr * 0.9) * 0.72, oy = py * (ry - pr * 0.9) * 0.65;
    circ(g, x + ox, y + oy, pr, { fill: OUT, lw: 0 });
    circ(g, x + ox - pr * 0.32, y + oy - pr * 0.35, Math.max(0.8, pr * 0.32), { fill: '#ffffff', lw: 0 });
    return;
  }
  if (kind === 'half_lid') {
    ellipse(g, x, y + R * 0.015, R * 0.13, R * 0.12, { fill: '#ffffff', lw: lw * 0.78 });
    circ(g, x + px * R * 0.045, y + R * 0.03 + py * R * 0.02, R * 0.058, { fill: OUT, lw: 0 });
    g.save();
    g.beginPath();
    g.ellipse(x, y + R * 0.015, R * 0.14, R * 0.13, 0, 0, Math.PI * 2);
    g.clip();
    g.fillStyle = skinHex;
    g.fillRect(x - R * 0.18, y - R * 0.16, R * 0.36, R * 0.165);
    g.restore();
    strokeTapered2D(g, [[x - R * 0.14, y], [x + R * 0.14, y]], { lw: lw * 0.95 });
    return;
  }
  // Default Squire characteristic dark bead eye with crisp specular catchlight ('focused' / 'sharp_focus')
  const ox = px * R * 0.065, oy = py * R * 0.04;
  ellipse(g, x + ox, y + oy, R * 0.07, R * 0.102, { fill: OUT, lw: 0 });
  circ(g, x + ox - R * 0.022, y + oy - R * 0.036, R * 0.025, { fill: '#ffffff', lw: 0 });
}

function _drawSingleCinematicBrow(g, x, y, R, kind, lw, side) {
  const curves = {
    soft: [0.01, -0.025, 0.015],
    worried_tilt: [-0.08, -0.045, 0.04],
    high_arch: [-0.05, -0.11, -0.04],
    furrowed: [0.065, 0.015, -0.055],
    angled_drive: [0.055, -0.01, -0.065],
    relieved_up: [-0.065, -0.075, -0.01],
    flat_deadpan: [0.005, 0.005, 0.005],
    asymmetric_smug: side < 0 ? [0.01, 0.0, 0.01] : [-0.02, -0.065, -0.08],
  }[kind || 'soft'] || [0, -0.02, 0];
  const xin = x - side * R * 0.115, xout = x + side * R * 0.135;
  strokeTapered2D(
    g,
    [
      [xin, y + curves[0] * R],
      [x + side * R * 0.01, y + curves[1] * R],
      [xout, y + curves[2] * R],
    ],
    { lw: lw * 1.12, startRatio: 0.65, midRatio: 1.05, endRatio: 0.35 }
  );
}

function _drawCinematicMouth(g, x, y, R, kind, lw, talk) {
  const tk = clamp(talk || 0);
  if (tk > 0.16 && ['calm_smile', 'deadpan_line', 'set_firm', 'wavy_anxious'].includes(kind)) {
    const openH = lerp(0.05, 0.13, tk);
    shape(
      g,
      (c) => {
        c.moveTo(x - R * 0.1, y - R * 0.01);
        c.quadraticCurveTo(x, y - R * 0.03, x + R * 0.1, y - R * 0.01);
        c.quadraticCurveTo(x, y + R * openH, x - R * 0.1, y - R * 0.01);
      },
      { fill: PAL.mouth, lw: lw * 0.78, inner: (c) => ellipse(c, x, y + R * openH * 0.62, R * 0.055, R * openH * 0.35, { fill: PAL.tongue, lw: 0 }) }
    );
    return;
  }
  switch (kind) {
    case 'calm_smile':
    case 'smirk_warm':
      strokeTapered2D(
        g,
        [[x - R * 0.095, y - R * 0.01], [x + R * 0.01, y + R * 0.042], [x + R * 0.11, y - R * (kind === 'smirk_warm' ? 0.038 : 0.015)]],
        { lw: lw * 0.88 }
      );
      break;
    case 'wavy_anxious':
      strokeTapered2D(
        g,
        [
          [x - R * 0.115, y + R * 0.015],
          [x - R * 0.055, y - R * 0.025],
          [x, y + R * 0.018],
          [x + R * 0.055, y - R * 0.022],
          [x + R * 0.115, y + R * 0.015],
        ],
        { lw: lw * 0.8 }
      );
      break;
    case 'gasp_o':
    case 'small_yawn': {
      const rx = kind === 'small_yawn' ? R * 0.05 : R * 0.072;
      const ry = kind === 'small_yawn' ? R * 0.065 : R * 0.098;
      ellipse(g, x, y + R * 0.015, rx, ry, {
        fill: PAL.mouth,
        lw: lw * 0.8,
        inner: (c) => ellipse(c, x, y + R * 0.065, rx * 0.68, ry * 0.42, { fill: PAL.tongue, lw: 0 }),
      });
      break;
    }
    case 'clenched_effort': {
      const w = R * 0.145, h = R * 0.078;
      shape(
        g,
        (c) => c.roundRect(x - w, y - h * 0.55, w * 2, h * 1.15, h * 0.45),
        {
          fill: '#ffffff',
          lw: lw * 0.78,
          inner: (c) => {
            line(c, [[x - w, y + h * 0.04], [x + w, y + h * 0.04]], { lw: lw * 0.45 });
            for (let i = -2; i <= 2; i++) {
              line(c, [[x + i * w * 0.36, y - h], [x + i * w * 0.36, y + h]], { lw: lw * 0.42 });
            }
          },
        }
      );
      break;
    }
    case 'sigh_relief':
      shape(
        g,
        (c) => {
          c.moveTo(x - R * 0.095, y);
          c.quadraticCurveTo(x, y + R * 0.085, x + R * 0.095, y - R * 0.008);
          c.quadraticCurveTo(x, y + R * 0.025, x - R * 0.095, y);
        },
        { fill: PAL.mouth, lw: lw * 0.78 }
      );
      break;
    case 'frown_deep':
      strokeTapered2D(g, [[x - R * 0.105, y + R * 0.04], [x, y - R * 0.022], [x + R * 0.105, y + R * 0.04]], { lw: lw * 0.88 });
      break;
    case 'set_firm':
      strokeTapered2D(g, [[x - R * 0.095, y + R * 0.008], [x + R * 0.02, y - R * 0.012], [x + R * 0.095, y + R * 0.012]], { lw: lw * 0.9 });
      break;
    case 'deadpan_line':
    default:
      strokeTapered2D(g, [[x - R * 0.095, y], [x + R * 0.095, y]], { lw: lw * 0.88, startRatio: 0.75, endRatio: 0.75 });
      break;
  }
}

function _drawCharacterHairBack(g, cx, cy, R, prof, lw, view, secondaryLag = 0) {
  if (prof.hair === 'elder_braided_bun') {
    const bx = view === 'profile' ? cx - R * 0.88 : cx - R * 0.65;
    const by = cy - R * 0.18 + secondaryLag * R * 0.06;
    fillCelShadedShape2D(
      g,
      (c) => c.arc(bx, by, R * 0.36, 0, Math.PI * 2),
      { fill: prof.hairColor, shadow: alpha(prof.hairShade, 0.85), bounds: [bx, by, R * 0.36, R * 0.36], lw }
    );
    // Bronze hairpin
    strokeTapered2D(g, [[bx - R * 0.42, by - R * 0.24], [bx + R * 0.35, by + R * 0.22]], { lw: lw * 0.9, ink: prof.brass || '#c99642' });
  }
}

function _drawCharacterHairFront(g, cx, cy, R, prof, lw, view, secondaryLag = 0) {
  if (prof.hair === 'tousled_tufts') {
    const lag = secondaryLag * R * 0.14;
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(cx - R * 1.04, cy + R * 0.04);
        c.bezierCurveTo(cx - R * 1.16, cy - R * 1.48, cx + R * 1.04, cy - R * 1.54, cx + R * 1.04, cy - R * 0.14);
        // Two expressive apprentice forelock tufts with secondary motion lag
        c.lineTo(cx + R * 1.20 - lag * 0.6, cy - R * 0.40 + Math.abs(lag) * 0.3);
        c.lineTo(cx + R * 0.88, cy - R * 0.58);
        c.lineTo(cx + R * 1.08 - lag, cy - R * 0.84 + Math.abs(lag) * 0.25);
        c.quadraticCurveTo(cx + R * 0.42, cy - R * 0.54, cx + R * 0.06, cy - R * 0.64);
        c.quadraticCurveTo(cx - R * 0.50, cy - R * 0.48, cx - R * 1.04, cy + R * 0.04);
        c.closePath();
      },
      {
        fill: prof.hairColor,
        shadow: alpha(prof.hairShade, 0.85),
        rim: alpha('#ffd49e', 0.55),
        bounds: [cx, cy - R * 0.72, R * 1.12, R * 0.72],
        lw,
      }
    );
  } else if (prof.hair === 'elder_braided_bun') {
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(cx - R * 1.04, cy + R * 0.06);
        c.bezierCurveTo(cx - R * 1.14, cy - R * 1.48, cx + R * 1.12, cy - R * 1.48, cx + R * 1.03, cy - R * 0.04);
        c.quadraticCurveTo(cx + R * 0.45, cy - R * 0.62, cx, cy - R * 0.52);
        c.quadraticCurveTo(cx - R * 0.48, cy - R * 0.62, cx - R * 1.04, cy + R * 0.06);
        c.closePath();
      },
      { fill: prof.hairColor, shadow: alpha(prof.hairShade, 0.8), bounds: [cx, cy - R * 0.7, R * 1.08, R * 0.7], lw }
    );
    // Braided crown band
    strokeTapered2D(g, [[cx - R * 0.88, cy - R * 0.58], [cx, cy - R * 0.90], [cx + R * 0.84, cy - R * 0.55]], {
      lw: lw * 1.1,
      ink: prof.hairShade,
    });
  } else {
    // Curly Roman crop
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(cx - R * 1.03, cy - R * 0.02);
        c.bezierCurveTo(cx - R * 1.14, cy - R * 1.46, cx + R * 1.14, cy - R * 1.46, cx + R * 1.03, cy - R * 0.02);
        c.quadraticCurveTo(cx, cy - R * 0.56, cx - R * 1.03, cy - R * 0.02);
        c.closePath();
      },
      { fill: prof.hairColor, shadow: alpha(prof.hairShade, 0.8), bounds: [cx, cy - R * 0.68, R * 1.06, R * 0.65], lw }
    );
  }
}

function _drawPlantedSandal2D(g, fx, fy, u, sideView, sandalCol, lw) {
  // Flat planted sole at y = fy (local 0 when standing on ground)
  g.save();
  g.translate(fx, fy);
  const w = sideView ? 12.2 * u : 10.6 * u;
  const h = 5.4 * u;
  const xOff = sideView ? -3.6 * u : -w * 0.5;
  fillCelShadedShape2D(
    g,
    (c) => c.roundRect(xOff, -h, w, h, [2.2 * u, 4.2 * u, 1.2 * u, 1.2 * u]),
    { fill: sandalCol, shadow: alpha(darker(sandalCol, 0.25), 0.85), bounds: [xOff + w / 2, -h / 2, w * 0.6, h * 0.6], lw: lw * 0.9 }
  );
  // Flat leather sole strip
  line(g, [[xOff + 0.8 * u, -0.9 * u], [xOff + w - 0.8 * u, -0.9 * u]], { lw: lw * 0.7, ink: darker(sandalCol, 0.35) });
  // Cross-laced caligae ankle straps
  strokeTapered2D(g, [[xOff + 2 * u, -h - 1.5 * u], [xOff + 6.5 * u, -h - 4.2 * u]], { lw: lw * 0.62, ink: sandalCol });
  strokeTapered2D(g, [[xOff + 6.5 * u, -h - 1.5 * u], [xOff + 2 * u, -h - 4.2 * u]], { lw: lw * 0.62, ink: sandalCol });
  g.restore();
}

export function drawSquireCinematic2DActor(g, x, y, h, o = {}) {
  const prof = { ...(CINEMATIC_CAST_PROFILES[o.castId || o.character || 'TAVI'] || CINEMATIC_CAST_PROFILES.TAVI), ...o };
  const effH = h * (o.ignoreStatureScale ? 1.0 : (prof.stature_scale || 1.0));
  const u = effH / 100;
  const lw = o.lw ?? scaleStrokeWeight2D(effH, 5.1, 1.8, 9.0);
  const lwInner = Math.max(1.3, lw * 0.64);
  const view = o.view || 'three_quarter'; // front | three_quarter | profile
  const flip = !!o.flip;
  const dirSign = flip ? -1 : 1;
  const spineLean = (o.spineLean ?? 0) + (prof.stoop || 0);
  const secondaryLag = clamp(o.secondaryLag ?? 0, -1.5, 1.5);
  const bobU = (o.bobU ?? 0) * u;

  g.save();
  g.translate(x, y);
  if (flip) g.scale(-1, 1);

  const hipX = (o.hipShiftU ?? 0) * u;
  const hipY = -30 * u + bobU;
  const L1 = 14.2 * u, L2 = 14.0 * u;
  const sideMode = view === 'profile' || o.legMode === 'side';

  // --- LEGS (2-segment IK with world/local foot targets so planted feet NEVER skate)
  const leftFoot = Array.isArray(o.leftFootWorld)
    ? [dirSign * (o.leftFootWorld[0] - x), o.leftFootWorld[1] - y]
    : o.leftFootU
      ? [o.leftFootU[0] * u, o.leftFootU[1] * u]
      : (sideMode ? [-5.5 * u, 0] : [-6.4 * u, 0]);
  const rightFoot = Array.isArray(o.rightFootWorld)
    ? [dirSign * (o.rightFootWorld[0] - x), o.rightFootWorld[1] - y]
    : o.rightFootU
      ? [o.rightFootU[0] * u, o.rightFootU[1] * u]
      : (sideMode ? [5.8 * u, 0] : [6.4 * u, 0]);

  const legSpecs = [
    { hip: [hipX - (sideMode ? 2.0 : 5.8) * u, hipY], foot: leftFoot, far: true, bend: sideMode ? 1 : 0.32 },
    { hip: [hipX + (sideMode ? 2.2 : 5.8) * u, hipY], foot: rightFoot, far: false, bend: sideMode ? 1 : -0.32 },
  ];

  for (const lg of legSpecs) {
    const pts = ik2(lg.hip[0], lg.hip[1], lg.foot[0], lg.foot[1] - 3.2 * u, L1, L2, lg.bend);
    const skinFill = lg.far ? darker(prof.skin, 0.08) : prof.skin;
    const skinSh = alpha(prof.skinShade, 0.85);
    _taperedLimbEnvelope(g, pts[0], pts[1], pts[2], 7.4 * u, 6.2 * u, 4.8 * u, {
      fill: skinFill,
      shadow: skinSh,
      lw: lw * 0.92,
    });
    _drawPlantedSandal2D(g, lg.foot[0], lg.foot[1], u, sideMode, lg.far ? darker(prof.sandal, 0.12) : prof.sandal, lw);
  }

  // --- UPPER BODY PIVOT AT HIP (supports line-of-action spine lean!)
  g.save();
  g.translate(hipX, hipY);
  if (spineLean) g.rotate(spineLean);

  const torsoTop = -29 * u;
  const skirtBot = (prof.palla ? 22 : 10.5) * u;
  const wShoulder = (view === 'profile' ? 9.8 : view === 'three_quarter' ? 12.6 : 13.6) * u;
  const wHem = (view === 'profile' ? 13.0 : 16.4) * u + Math.abs(secondaryLag) * 1.8 * u;
  const hemSkew = -secondaryLag * 3.2 * u;

  // Shoulder sockets in hip-local coords
  const shFar = [view === 'profile' ? 0 : -wShoulder * 0.92, torsoTop + 5 * u];
  const shNear = [view === 'profile' ? 1.5 * u : wShoulder * 0.92, torsoTop + 5.2 * u];

  // Resolve arm IK or shoulder/elbow angles
  const resolveArm = (shPt, targetU, worldTarget, shDeg, elDeg, sgn) => {
    const L_up = 13.0 * u, L_fore = 12.5 * u;
    if (Array.isArray(worldTarget)) {
      const dx = dirSign * (worldTarget[0] - x) - hipX;
      const dy = (worldTarget[1] - y) - hipY;
      const cInv = Math.cos(-spineLean), sInv = Math.sin(-spineLean);
      const tx = dx * cInv - dy * sInv;
      const ty = dx * sInv + dy * cInv;
      const pts = ik2(shPt[0], shPt[1], tx, ty, L_up, L_fore, worldTarget[2] ?? -sgn);
      const ang = Math.atan2(pts[2][1] - pts[1][1], pts[2][0] - pts[1][0]) - Math.PI / 2;
      return { S: pts[0], E: pts[1], H: pts[2], ang };
    }
    if (targetU) {
      const tx = targetU[0] * u, ty = targetU[1] * u;
      const pts = ik2(shPt[0], shPt[1], tx, ty, L_up, L_fore, targetU[2] ?? -sgn);
      const ang = Math.atan2(pts[2][1] - pts[1][1], pts[2][0] - pts[1][0]) - Math.PI / 2;
      return { S: pts[0], E: pts[1], H: pts[2], ang };
    }
    const a1 = (shDeg ?? 18) * Math.PI / 180;
    const a2 = ((shDeg ?? 18) + (elDeg ?? 14)) * Math.PI / 180;
    const ex = shPt[0] + sgn * Math.sin(a1) * L_up;
    const ey = shPt[1] + Math.cos(a1) * L_up;
    const hx = ex + sgn * Math.sin(a2) * L_fore;
    const hy = ey + Math.cos(a2) * L_fore;
    return { S: shPt, E: [ex, ey], H: [hx, hy], ang: Math.atan2(hy - ey, hx - ex) - Math.PI / 2 };
  };

  const armPose = o.armAngles || [18, 14, 22, 18];
  const farArm = resolveArm(shFar, o.leftHandTargetU, o.leftHandWorldTarget, armPose[0], armPose[1], -1);
  const nearArm = resolveArm(shNear, o.rightHandTargetU, o.rightHandWorldTarget, armPose[2], armPose[3], 1);

  // --- FAR ARM (behind torso)
  if (view !== 'profile' || o.showBothArmsInProfile) {
    _taperedLimbEnvelope(g, farArm.S, farArm.E, farArm.H, 6.8 * u, 5.6 * u, 4.4 * u, {
      fill: darker(prof.skin, 0.08),
      shadow: alpha(prof.skinShade, 0.85),
      lw: lw * 0.9,
    });
    // Short tunic sleeve cap on far shoulder
    fillCelShadedShape2D(
      g,
      (c) => c.ellipse(farArm.S[0], farArm.S[1] + 1.5 * u, 4.4 * u, 4.8 * u, 0.2, 0, Math.PI * 2),
      { fill: darker(prof.tunic, 0.1), shadow: alpha(prof.tunicDeep, 0.7), bounds: [farArm.S[0], farArm.S[1], 4.5 * u, 4.8 * u], lw: lw * 0.85 }
    );
    drawCinematicHand2D(g, farArm.H[0], farArm.H[1], 4.6 * u, {
      pose: o.leftHandPose || o.handPose || 'relaxed',
      ang: farArm.ang,
      side: -1,
      skin: darker(prof.skin, 0.06),
      skinShade: prof.skinShade,
      lw: lw * 0.85,
      wrapLeather: !!o.leatherWraps,
    });
  }

  // --- SCARF BACK TAIL (Tavi secondary action!)
  if (prof.scarf) {
    const tailX = -wShoulder * 0.85 - secondaryLag * 12 * u;
    const tailY = torsoTop + 14 * u + Math.abs(secondaryLag) * 3 * u;
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(-4 * u, torsoTop + 2 * u);
        c.quadraticCurveTo(-10 * u - secondaryLag * 5 * u, torsoTop + 5 * u, tailX, tailY);
        c.lineTo(tailX + 4.5 * u, tailY + 5 * u);
        c.quadraticCurveTo(-7 * u, torsoTop + 10 * u, -1 * u, torsoTop + 5 * u);
        c.closePath();
      },
      { fill: prof.scarf, shadow: alpha(prof.scarfShade, 0.85), bounds: [tailX * 0.5, torsoTop + 9 * u, 12 * u, 8 * u], lw: lw * 0.85 }
    );
  }

  // --- UNDERTUNIC LAYER PEEKING AT HEM
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-wHem * 0.96 + hemSkew, skirtBot - 2 * u);
      c.lineTo(wHem * 0.96 + hemSkew, skirtBot - 2 * u);
      c.lineTo(wHem * 1.02 + hemSkew, skirtBot + 3.4 * u);
      c.quadraticCurveTo(hemSkew, skirtBot + 5.2 * u, -wHem * 1.02 + hemSkew, skirtBot + 3.4 * u);
      c.closePath();
    },
    { fill: prof.undertunic, shadow: alpha(prof.undertunicShade, 0.85), bounds: [0, skirtBot, wHem, 4 * u], lw: lw * 0.88 }
  );

  // --- MAIN TUNIC / STOLA TORSO (2-3 cel-shading bands + warm dawn rim + cloth folds)
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-wShoulder, torsoTop + 5 * u);
      c.quadraticCurveTo(-wShoulder * 0.85, torsoTop - 1 * u, -wShoulder * 0.35, torsoTop);
      c.lineTo(wShoulder * 0.35, torsoTop);
      c.quadraticCurveTo(wShoulder * 0.85, torsoTop - 1 * u, wShoulder, torsoTop + 5 * u);
      c.lineTo(wHem + hemSkew, skirtBot);
      c.quadraticCurveTo(hemSkew, skirtBot + 2.6 * u, -wHem + hemSkew, skirtBot);
      c.closePath();
    },
    {
      fill: prof.tunic,
      shadow: alpha(prof.tunicShade, 0.9),
      deepShadow: alpha(prof.tunicDeep, 0.55),
      rim: alpha('#ffd49e', 0.65),
      bounds: [0, (torsoTop + skirtBot) / 2, wHem, (skirtBot - torsoTop) * 0.62],
      lw,
      inner: (c) => {
        // Undertunic collar V-trim
        shape(
          c,
          (cc) => {
            cc.moveTo(-6.2 * u, torsoTop - 1 * u);
            cc.lineTo(0, torsoTop + 6.5 * u);
            cc.lineTo(6.2 * u, torsoTop - 1 * u);
            cc.closePath();
          },
          { fill: prof.undertunic, lw: lwInner }
        );
        // Purposeful anchored cloth drape folds
        shadeClothFold2D(c, [-4 * u, -2 * u], [-8.5 * u + hemSkew * 0.6, skirtBot - 1 * u], [-6.8 * u, skirtBot * 0.45], {
          shadow: alpha(prof.tunicDeep, 0.42),
          lw: lwInner * 0.85,
          spread: 3.2 * u,
        });
        shadeClothFold2D(c, [3.5 * u, -1 * u], [7.2 * u + hemSkew * 0.6, skirtBot - 1.2 * u], [5.8 * u, skirtBot * 0.48], {
          shadow: alpha(prof.tunicDeep, 0.42),
          lw: lwInner * 0.85,
          spread: 3.0 * u,
        });
      },
    }
  );

  // --- ELDER PALLA SHAWL DRAPE (Lyra) OR SAFFRON NECK SCARF + BELT POUCH (Tavi)
  if (prof.palla) {
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(-wShoulder * 1.02, torsoTop + 1 * u);
        c.lineTo(-wShoulder * 0.25, torsoTop + 1 * u);
        c.quadraticCurveTo(4 * u, torsoTop + 14 * u, wHem * 0.95, skirtBot - 4 * u);
        c.lineTo(wHem * 0.35, skirtBot - 1 * u);
        c.quadraticCurveTo(-8 * u, torsoTop + 18 * u, -wShoulder * 1.06, torsoTop + 12 * u);
        c.closePath();
      },
      {
        fill: prof.palla,
        shadow: alpha(prof.pallaShade, 0.82),
        bounds: [0, 0, wHem, 18 * u],
        lw: lw * 0.9,
        inner: (c) => strokeTapered2D(c, [[-wShoulder * 0.9, torsoTop + 10 * u], [wHem * 0.5, skirtBot - 2.5 * u]], { lw: lwInner, ink: prof.brass }),
      }
    );
    circ(g, -wShoulder * 0.58, torsoTop + 3.2 * u, 2.5 * u, { fill: prof.brass, lw: lwInner });
  } else {
    // Leather belt + brass buckle + keeper pouch & tuning key
    fillCelShadedShape2D(
      g,
      (c) => c.roundRect(-wHem * 0.9, -3.5 * u, wHem * 1.8, 4.4 * u, 1.4 * u),
      { fill: prof.belt, shadow: alpha('#3b2211', 0.7), bounds: [0, -1.3 * u, wHem, 3 * u], lw: lw * 0.86 }
    );
    circ(g, 0, -1.3 * u, 2.3 * u, { fill: prof.brass, lw: lwInner });
    if (prof.keyRing) {
      // Leather pouch + brass bell-tower pin key at hip
      fillCelShadedShape2D(
        g,
        (c) => c.roundRect(5.2 * u, -0.5 * u, 5.8 * u, 6.4 * u, 2.0 * u),
        { fill: '#7d4f2d', shadow: alpha('#4a2c16', 0.75), bounds: [8 * u, 2.7 * u, 3.5 * u, 3.5 * u], lw: lwInner }
      );
      circ(g, -7.2 * u, 0.8 * u, 1.9 * u, { fill: null, lw: lwInner * 0.9, ink: prof.brass });
      line(g, [[-7.2 * u, 2.7 * u], [-7.2 * u, 7.2 * u], [-5.4 * u, 7.2 * u]], { lw: lwInner * 0.85, ink: prof.brass });
    }
    if (prof.scarf) {
      fillCelShadedShape2D(
        g,
        (c) => {
          c.moveTo(-wShoulder * 0.78, torsoTop + 0.5 * u);
          c.quadraticCurveTo(0, torsoTop + 6.5 * u, wShoulder * 0.78, torsoTop + 0.5 * u);
          c.quadraticCurveTo(wShoulder * 0.5, torsoTop + 9.2 * u, 0, torsoTop + 9.8 * u);
          c.quadraticCurveTo(-wShoulder * 0.55, torsoTop + 9.0 * u, -wShoulder * 0.78, torsoTop + 0.5 * u);
          c.closePath();
        },
        { fill: prof.scarf, shadow: alpha(prof.scarfShade, 0.8), bounds: [0, torsoTop + 5 * u, wShoulder * 0.8, 5 * u], lw: lw * 0.88 }
      );
    }
  }

  // --- HEAD (Preserving signature Squire ~38% caricature round head + upgraded cel/rim/features)
  const R = 19 * (prof.head_scale || 1.0) * u;
  const headCx = (o.headTiltX ?? (view === 'profile' ? 2.2 : 0.6)) * u;
  const headCy = torsoTop - R * 0.92;
  const headRot = o.headRot ?? 0;

  g.save();
  g.translate(headCx, headCy);
  if (headRot) g.rotate(headRot);

  _drawCharacterHairBack(g, 0, 0, R, prof, lw, view, secondaryLag);

  // Neck bridge with chin cast shadow
  fillCelShadedShape2D(
    g,
    (c) => c.roundRect(-4.2 * u, R * 0.72, 8.4 * u, 5.2 * u, 2 * u),
    { fill: prof.skinShade, shadow: alpha(prof.skinDeep, 0.7), bounds: [0, R * 0.95, 5 * u, 3 * u], lw: lw * 0.82 }
  );

  // Signature round Squire head with 2-band cel shading + warm dawn rim highlight
  fillCelShadedShape2D(
    g,
    (c) => c.arc(0, 0, R, 0, Math.PI * 2),
    {
      fill: prof.skin,
      shadow: alpha(prof.skinShade, 0.88),
      deepShadow: alpha(prof.skinDeep, 0.42),
      rim: alpha('#ffe1b5', 0.78),
      bounds: [0, 0, R, R],
      lw,
    }
  );

  // Ear in 3/4 and profile views
  if (view === 'three_quarter' || view === 'profile') {
    const earX = view === 'profile' ? -R * 0.12 : -R * 0.92;
    fillCelShadedShape2D(
      g,
      (c) => c.ellipse(earX, R * 0.08, R * 0.16, R * 0.22, 0, 0, Math.PI * 2),
      { fill: prof.skin, shadow: alpha(prof.skinShade, 0.85), bounds: [earX, R * 0.08, R * 0.16, R * 0.22], lw: lw * 0.82 }
    );
  }

  drawCinematicFace2D(g, 0, 0, R, {
    ...o,
    view,
    lw: lw * 0.86,
    skin: prof.skin,
    freckles: prof.freckles,
    ageLines: prof.ageLines,
  });

  _drawCharacterHairFront(g, 0, 0, R, prof, lw, view, secondaryLag);
  g.restore();

  // --- NEAR ARM (in front of torso for clear action silhouette)
  fillCelShadedShape2D(
    g,
    (c) => c.ellipse(nearArm.S[0], nearArm.S[1] + 1.4 * u, 4.8 * u, 5.2 * u, -0.15, 0, Math.PI * 2),
    { fill: prof.tunic, shadow: alpha(prof.tunicShade, 0.8), bounds: [nearArm.S[0], nearArm.S[1], 5 * u, 5 * u], lw: lw * 0.88 }
  );
  _taperedLimbEnvelope(g, nearArm.S, nearArm.E, nearArm.H, 7.2 * u, 5.9 * u, 4.6 * u, {
    fill: prof.skin,
    shadow: alpha(prof.skinShade, 0.82),
    rim: alpha('#ffe1b5', 0.6),
    lw: lw * 0.94,
  });
  drawCinematicHand2D(g, nearArm.H[0], nearArm.H[1], 4.8 * u, {
    pose: o.rightHandPose || o.handPose || 'relaxed',
    ang: nearArm.ang,
    side: 1,
    skin: prof.skin,
    skinShade: prof.skinShade,
    lw: lw * 0.9,
    wrapLeather: !!o.leatherWraps,
  });

  g.restore(); // hip pivot
  g.restore(); // actor root

  // Compute exact world-space anchors for deterministic prop/rope contact verification
  const cosL = Math.cos(spineLean), sinL = Math.sin(spineLean);
  const toWorld = (lx, ly) => {
    const rx = lx * cosL - ly * sinL + hipX;
    const ry = lx * sinL + ly * cosL + hipY;
    return [x + dirSign * rx, y + ry];
  };
  return {
    character_id: prof.character_id,
    canonical_name: prof.canonical_name,
    root: [x, y],
    headCenter: toWorld(headCx, headCy),
    headRadius: R,
    rightHandWorld: toWorld(nearArm.H[0], nearArm.H[1]),
    leftHandWorld: toWorld(farArm.H[0], farArm.H[1]),
    leftFootWorld: [x + dirSign * leftFoot[0], y + leftFoot[1]],
    rightFootWorld: [x + dirSign * rightFoot[0], y + rightFoot[1]],
  };
}

// ======================================================================================
// PIP — ORIGINAL ROMAN HILLTOP GOAT (QUADRUPED ANIMAL 2D; EXPLICITLY NON-HUMAN RIG)
// ======================================================================================
export function drawPipGoat2D(g, x, y, h, o = {}) {
  const u = h / 100;
  const lw = o.lw ?? scaleStrokeWeight2D(h * 1.25, 4.8, 1.8, 8.6);
  const flip = !!o.flip;
  const dirSign = flip ? -1 : 1;
  const action = o.action || 'curious_tilt'; // rope_nudge | curious_tilt | sneeze_anticipation | sneeze_burst | innocent_blink
  const phase = clamp(o.phase ?? 0.5, 0, 1);
  const t = o.t || 0;

  const coat = '#efe3cc', coatShade = '#cbbba0', coatDeep = '#a9977b';
  const darkMark = '#4c382c', hornCol = '#bfa070', collarCol = '#b84234';

  // 2D squash & stretch around ground contact (x, y) — feet stay planted!
  let sx = 1.0, sy = 1.0, headPitch = 0, neckReachX = 0, neckReachY = 0;
  if (action === 'rope_nudge') {
    neckReachX = lerp(2, 9.5, Math.sin(phase * Math.PI)) * u;
    neckReachY = lerp(2, -3.5, Math.sin(phase * Math.PI)) * u;
    headPitch = lerp(0.08, -0.18, Math.sin(phase * Math.PI));
  } else if (action === 'sneeze_anticipation') {
    const k = ease.inOut(phase);
    sx = lerp(1.0, 1.15, k);
    sy = lerp(1.0, 0.87, k);
    neckReachX = lerp(0, -6.5, k) * u;
    neckReachY = lerp(0, -5.5, k) * u;
    headPitch = lerp(0, -0.36, k);
  } else if (action === 'sneeze_burst') {
    const k = ease.out(clamp(phase * 2.2));
    sx = lerp(1.16, 0.93, k);
    sy = lerp(0.86, 1.09, k);
    neckReachX = lerp(-6, 14.5, k) * u;
    neckReachY = lerp(-5, 5.5, k) * u;
    headPitch = lerp(-0.35, 0.34, k);
  }

  g.save();
  g.translate(x, y);
  if (flip) g.scale(-1, 1);
  g.scale(sx, sy);

  // Four quadruped legs with cloven dark hooves planted on ground y=0
  const drawGoatLeg = (hx, hy, fx, fy, far) => {
    const cFill = far ? darker(coat, 0.1) : coat;
    _taperedLimbEnvelope(
      g,
      [hx * u, hy * u],
      [(hx + fx) * 0.5 * u + (far ? -1 : 1) * u, (hy + fy) * 0.5 * u],
      [fx * u, (fy - 4.5) * u],
      6.2 * u,
      4.5 * u,
      3.5 * u,
      { fill: cFill, shadow: alpha(coatShade, 0.8), lw: lw * 0.88 }
    );
    // Cloven hoof
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo((fx - 2.6) * u, (fy - 4.8) * u);
        c.lineTo((fx + 3.0) * u, (fy - 4.8) * u);
        c.lineTo((fx + 3.8) * u, fy * u);
        c.lineTo((fx + 0.8) * u, fy * u);
        c.lineTo((fx + 0.2) * u, (fy - 2.2) * u);
        c.lineTo((fx - 0.4) * u, fy * u);
        c.lineTo((fx - 3.0) * u, fy * u);
        c.closePath();
      },
      { fill: darkMark, bounds: [fx * u, (fy - 2.4) * u, 3.5 * u, 3 * u], lw: lw * 0.82 }
    );
  };

  drawGoatLeg(-18, -28, -21, 0, true);
  drawGoatLeg(15, -28, 19, 0, true);

  // Upright perky goat tail
  const tailWag = Math.sin(t * 9) * 2.2 * u;
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-26 * u, -42 * u);
      c.quadraticCurveTo(-35 * u, -54 * u, -31 * u + tailWag, -60 * u);
      c.quadraticCurveTo(-24 * u, -53 * u, -22 * u, -44 * u);
      c.closePath();
    },
    { fill: coat, shadow: alpha(coatShade, 0.8), bounds: [-28 * u, -51 * u, 7 * u, 9 * u], lw: lw * 0.86 }
  );

  // Compact barrel body
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-25 * u, -46 * u);
      c.bezierCurveTo(-14 * u, -52 * u, 10 * u, -52 * u, 22 * u, -46 * u);
      c.bezierCurveTo(29 * u, -41 * u, 28 * u, -26 * u, 18 * u, -24 * u);
      c.bezierCurveTo(4 * u, -21 * u, -14 * u, -22 * u, -24 * u, -26 * u);
      c.bezierCurveTo(-30 * u, -30 * u, -30 * u, -42 * u, -25 * u, -46 * u);
      c.closePath();
    },
    {
      fill: coat,
      shadow: alpha(coatShade, 0.88),
      deepShadow: alpha(coatDeep, 0.45),
      rim: alpha('#ffe1b5', 0.65),
      bounds: [-2 * u, -37 * u, 28 * u, 16 * u],
      lw,
    }
  );

  // Near legs
  drawGoatLeg(-14, -27, -15, 0, false);
  drawGoatLeg(18, -27, 22 + (action === 'rope_nudge' ? Math.sin(phase * Math.PI) * 4 : 0), action === 'rope_nudge' ? -Math.sin(phase * Math.PI) * 3 : 0, false);

  // Head target coordinates + continuous organic neck bridge (prevents head gap during stretch!)
  const hx = 25 * u + neckReachX;
  const hy = -58 * u + neckReachY;
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(9 * u, -46 * u);
      c.quadraticCurveTo(lerp(12 * u, hx - 5 * u, 0.5), lerp(-48 * u, hy + 2 * u, 0.5), hx - 6 * u, hy + 2 * u);
      c.lineTo(hx + 6 * u, hy + 9 * u);
      c.quadraticCurveTo(lerp(22 * u, hx + 4 * u, 0.5), lerp(-34 * u, hy + 10 * u, 0.5), 22 * u, -32 * u);
      c.closePath();
    },
    { fill: coat, shadow: alpha(coatShade, 0.85), bounds: [(15 * u + hx) / 2, (-39 * u + hy) / 2, 14 * u, 14 * u], lw: lw * 0.9 }
  );

  // Braided red wool collar cord + wooden toggle
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(13 * u, -48 * u);
      c.quadraticCurveTo(22 * u, -42 * u, 24 * u, -30 * u);
      c.lineTo(19 * u, -28 * u);
      c.quadraticCurveTo(17 * u, -39 * u, 9 * u, -45 * u);
      c.closePath();
    },
    { fill: collarCol, shadow: alpha('#7c241a', 0.8), bounds: [17 * u, -39 * u, 8 * u, 10 * u], lw: lw * 0.85 }
  );
  circ(g, 22 * u, -27 * u, 2.8 * u, { fill: '#b88648', lw: lw * 0.78 });

  // Head + Horns + Rectangular Goat Eye
  g.save();
  g.translate(hx, hy);
  g.rotate(headPitch);

  // Curved goat horns (back then near)
  for (const [ox, sc, col] of [[-3 * u, 0.88, darker(hornCol, 0.14)], [-6 * u, 1.0, hornCol]]) {
    fillCelShadedShape2D(
      g,
      (c) => {
        c.moveTo(ox, -11 * u);
        c.quadraticCurveTo(ox - 10 * u * sc, -28 * u * sc, ox - 21 * u * sc, -22 * u * sc);
        c.quadraticCurveTo(ox - 12 * u * sc, -19 * u * sc, ox - 5 * u * sc, -9 * u);
        c.closePath();
      },
      { fill: col, bounds: [ox - 10 * u, -18 * u, 12 * u, 10 * u], lw: lw * 0.86 }
    );
  }

  // Droopy expressive dark ear
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-8 * u, -5 * u);
      c.quadraticCurveTo(-22 * u, -2 * u, -20 * u, 6 * u);
      c.quadraticCurveTo(-12 * u, 6 * u, -6 * u, 0);
      c.closePath();
    },
    { fill: darkMark, bounds: [-14 * u, 1 * u, 8 * u, 5 * u], lw: lw * 0.84 }
  );

  // Chin tuft beard
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(8 * u, 10 * u);
      c.quadraticCurveTo(10 * u, 21 * u, 4 * u, 22 * u);
      c.quadraticCurveTo(3 * u, 15 * u, 3 * u, 9 * u);
      c.closePath();
    },
    { fill: coatShade, bounds: [6 * u, 15 * u, 5 * u, 7 * u], lw: lw * 0.8 }
  );

  // Charming Squire-proportioned goat head + puffed cheek on sneeze anticipation
  const cheekPuff = action === 'sneeze_anticipation' ? phase * 3.8 * u : 0;
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-12 * u, -8 * u);
      c.bezierCurveTo(-8 * u, -18 * u, 8 * u, -17 * u, 16 * u, -6 * u);
      c.quadraticCurveTo(24 * u + cheekPuff, 2 * u, 21 * u + cheekPuff, 9 * u);
      c.quadraticCurveTo(14 * u, 14 * u + cheekPuff * 0.5, 1 * u, 11 * u);
      c.quadraticCurveTo(-13 * u, 9 * u, -12 * u, -8 * u);
      c.closePath();
    },
    {
      fill: coat,
      shadow: alpha(coatShade, 0.86),
      rim: alpha('#ffe1b5', 0.72),
      bounds: [4 * u, -1 * u, 18 * u, 15 * u],
      lw,
    }
  );

  // Eye: squint on sneeze, wide innocent rectangle pupil otherwise
  const ex = 4 * u, ey = -3.5 * u;
  if (action === 'sneeze_anticipation' || action === 'sneeze_burst') {
    strokeTapered2D(g, [[ex - 5 * u, ey - 3.2 * u], [ex + 4.5 * u, ey], [ex - 5 * u, ey + 3.2 * u]], { lw: lw * 0.98 });
  } else {
    ellipse(g, ex, ey, 5.4 * u, 4.8 * u, { fill: '#fff8dc', lw: lw * 0.82 });
    // Classic horizontal rectangular goat pupil!
    shape(g, (c) => c.roundRect(ex - 2.6 * u, ey - 1.2 * u, 5.6 * u, 2.4 * u, 0.8 * u), { fill: OUT, lw: 0 });
    circ(g, ex - 1.8 * u, ey - 1.8 * u, 1.1 * u, { fill: '#ffffff', lw: 0 });
  }

  // Nostril + mouth
  ellipse(g, 17.8 * u + cheekPuff * 0.8, 3.2 * u, 1.5 * u, 1.0 * u, { fill: OUT, lw: 0, rot: -0.3 });
  if (action === 'sneeze_burst') {
    shape(
      g,
      (c) => {
        c.moveTo(11 * u, 7 * u);
        c.lineTo(21 * u, 5.5 * u);
        c.lineTo(18 * u, 12.5 * u);
        c.closePath();
      },
      { fill: PAL.mouth, lw: lw * 0.75 }
    );
    // Crisp 2D sneeze puff lines & droplets (no blurry bloom!)
    for (let i = 0; i < 4; i++) {
      const a = -0.35 + i * 0.24;
      const d0 = 24 * u + phase * 8 * u, d1 = d0 + 12 * u;
      strokeTapered2D(
        g,
        [[Math.cos(a) * d0, 4 * u + Math.sin(a) * d0], [Math.cos(a) * d1, 4 * u + Math.sin(a) * d1]],
        { lw: lw * 0.72, ink: '#fff4df', a: clamp(1.3 - phase) }
      );
    }
  } else {
    strokeTapered2D(g, [[11.5 * u, 8.2 * u], [16 * u, 9.2 * u], [20 * u + cheekPuff * 0.6, 7.6 * u]], { lw: lw * 0.78 });
  }

  const noseLocalX = 21 * u + cheekPuff;
  const noseLocalY = 4.5 * u;
  g.restore(); // head
  g.restore(); // goat root

  const cosP = Math.cos(headPitch), sinP = Math.sin(headPitch);
  const snoutX = (hx + noseLocalX * cosP - noseLocalY * sinP) * sx;
  const snoutY = (hy + noseLocalX * sinP + noseLocalY * cosP) * sy;
  return {
    character_id: 'animal_pip_goat',
    canonical_name: 'PIP',
    rig_class: 'quadruped_animal_2d',
    is_human_rig: false,
    root: [x, y],
    snoutWorld: [x + dirSign * snoutX, y + snoutY],
  };
}
