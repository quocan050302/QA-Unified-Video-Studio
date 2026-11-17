// environment.js — Original Squire 2D Roman Castra Training Yard, Gate/Ramp & Shield-Wall Layers for KH-03.0.
// Built strictly with Production packs/squire/{ink.js,world.js,chara.js,army.js} primitives.
import { E, rng, lerp, clamp, noise, alpha, mix } from '../ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, blob, polyS, line, tube, darker, lighter, haze } from '../ink.js';
import { TIMES, cloud, tree, bush, tent, flag, grassClump, pebble } from '../world.js';
import { soldier, shield, weapon } from '../chara.js';
import { standard, dustPuff } from '../army.js';

const W = () => E.W || 1920;
const H = () => E.H || 1080;

// Harmless blunt wooden practice spear (leather-bound padded tip, zero lethal steel blade)
export function drawWoodenPracticeSpear2D(g, x, y, L, ang = Math.PI / 2, o = {}) {
  const lw = o.lw ?? Math.max(1.8, L * 0.018);
  g.save();
  g.translate(x, y);
  g.rotate(ang);
  if (o.smear && o.smear > 0.02) {
    const sm = clamp(o.smear, 0, 1);
    g.save();
    g.globalAlpha = 0.28 * sm;
    line(g, [[0, -L * 0.62], [0, L * 0.25]], { lw: L * 0.055, ink: '#f6dfb2' });
    g.restore();
  }
  // Ash-wood practice shaft (-0.42L to +0.86L, tip pointing along +Y like chara.js::weapon)
  tube(g, [[0, -L * 0.42], [0, L * 0.86]], L * 0.036, o.shaftColor || PAL.wood, lw);
  // Grip cord wrap near center
  rect(g, -L * 0.024, -L * 0.05, L * 0.048, L * 0.12, { fill: PAL.leather, lw: lw * 0.75, r: 2 });
  // Blunt leather-padded practice knob at +Y front
  rect(g, -L * 0.026, L * 0.82, L * 0.052, L * 0.06, { fill: PAL.rope, lw: lw * 0.75, r: 2 });
  ellipse(g, 0, L * 0.93, L * 0.046, L * 0.062, {
    fill: o.knobColor || PAL.leather,
    lw: lw * 0.9,
    inner: (c) => circ(c, -L * 0.014, L * 0.91, L * 0.016, { fill: alpha('#fff3dc', 0.45), lw: 0 }),
  });
  g.restore();
}

// Timber A-frame rack with spare wooden practice spears + straw-wrapped palus post
export function drawRomanTrainingRack2D(g, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(1.8, s * 0.02);
  g.save();
  g.translate(x, y);
  // Ground shadow
  ellipse(g, 0, s * 0.02, s * 0.56, s * 0.09, { fill: alpha('#2a1c12', 0.22), lw: 0 });
  // A-frame posts
  tube(g, [[-s * 0.42, 0], [-s * 0.26, -s * 0.58]], s * 0.055, PAL.woodDark, lw);
  tube(g, [[s * 0.34, 0], [s * 0.18, -s * 0.58]], s * 0.055, PAL.woodDark, lw);
  rect(g, -s * 0.4, -s * 0.34, s * 0.72, s * 0.06, { fill: PAL.wood, lw, r: 3 });
  rect(g, -s * 0.34, -s * 0.52, s * 0.6, s * 0.055, { fill: PAL.wood, lw, r: 3 });
  // Spare practice spears resting in rack
  const count = o.spearCount ?? 4;
  for (let i = 0; i < count; i++) {
    const sx = -s * 0.24 + i * (s * 0.14);
    drawWoodenPracticeSpear2D(g, sx, -s * 0.36, s * 0.72, Math.PI + 0.07 * (i - 1.5), { lw: lw * 0.85 });
  }
  // Wooden palus practice dummy post on right side
  if (o.withPalus !== false) {
    const px = s * 0.58;
    ellipse(g, px, s * 0.02, s * 0.18, s * 0.05, { fill: alpha('#2a1c12', 0.22), lw: 0 });
    tube(g, [[px, 0], [px, -s * 0.78]], s * 0.09, PAL.woodDark, lw);
    rect(g, px - s * 0.22, -s * 0.58, s * 0.44, s * 0.075, { fill: PAL.wood, lw, r: 3 });
    rect(g, px - s * 0.085, -s * 0.66, s * 0.17, s * 0.26, {
      fill: '#d8be7d',
      lw: lw * 0.9,
      r: 4,
      inner: (c) => {
        for (let k = 1; k <= 4; k++) {
          line(c, [[px - s * 0.09, -s * 0.66 + k * s * 0.052], [px + s * 0.09, -s * 0.66 + k * s * 0.052]], { lw: lw * 0.55, ink: PAL.rope });
        }
      },
    });
  }
  g.restore();
}

// Roman timber castra gate (porta) + palisade wall + earth/timber ramp landmark
export function drawRomanGateAndRamp2D(g, worldState = {}, cam = null, opts = {}) {
  const w = W(), h = H();
  const gx = (opts.gateX ?? 0.16) * w;
  const gy = (opts.groundY ?? 0.68) * h;
  const s = (opts.scale ?? 0.34) * h;
  const lw = opts.lw ?? Math.max(1.8, s * 0.012);
  const t = worldState.globalT ?? opts.t ?? 0;

  // Palisade stakes stretching left & slightly right from gate
  const stakeW = s * 0.055;
  const stakeH = s * 0.44;
  for (let x = gx - s * 1.15; x <= gx + s * 0.95; x += stakeW * 0.92) {
    if (Math.abs(x - gx) < s * 0.28) continue; // gateway opening
    polyS(
      g,
      [
        [x - stakeW * 0.5, gy],
        [x - stakeW * 0.5, gy - stakeH * 0.82],
        [x, gy - stakeH],
        [x + stakeW * 0.5, gy - stakeH * 0.82],
        [x + stakeW * 0.5, gy],
      ],
      { fill: Math.round(x) % 2 ? PAL.wood : darker(PAL.wood, 0.08), lw: lw * 0.85 }
    );
  }
  // Horizontal timber walkway beam
  rect(g, gx - s * 1.18, gy - stakeH * 0.72, s * 2.16, s * 0.065, { fill: PAL.woodDark, lw, r: 2 });

  // Twin Roman timber gate towers
  for (const side of [-1, 1]) {
    const tx = gx + side * s * 0.42;
    const tw = s * 0.28;
    const th = s * 0.78;
    rect(g, tx - tw / 2, gy - th, tw, th, {
      fill: PAL.wood,
      lw,
      r: 2,
      inner: (c) => {
        c.fillStyle = alpha(PAL.woodDark, 0.26);
        c.fillRect(tx, gy - th, tw, th);
        for (let k = 1; k <= 4; k++) {
          line(c, [[tx - tw / 2, gy - (th * k) / 5], [tx + tw / 2, gy - (th * k) / 5]], { lw: lw * 0.65, a: 0.55 });
        }
      },
    });
    // Low-pitched Roman tile/timber tower roof
    polyS(
      g,
      [
        [tx - tw * 0.64, gy - th],
        [tx, gy - th - s * 0.16],
        [tx + tw * 0.64, gy - th],
      ],
      { fill: PAL.redDark, lw }
    );
  }
  // Gate lintel & open arch
  rect(g, gx - s * 0.32, gy - s * 0.56, s * 0.64, s * 0.11, { fill: PAL.woodDark, lw, r: 2 });
  rect(g, gx - s * 0.22, gy - s * 0.45, s * 0.44, s * 0.45, { fill: '#4a3524', lw, r: [s * 0.16, s * 0.16, 0, 0] });

  // Earth-and-timber access ramp leading from gate onto drill yard
  polyS(
    g,
    [
      [gx - s * 0.18, gy],
      [gx + s * 0.22, gy],
      [gx + s * 0.74, gy + s * 0.18],
      [gx + s * 0.08, gy + s * 0.18],
    ],
    {
      fill: '#b99968',
      lw,
      inner: (c) => {
        for (let i = 1; i <= 4; i++) {
          const yy = gy + (i / 5) * s * 0.18;
          line(c, [[gx - s * 0.2, yy], [gx + s * 0.76, yy]], { lw: lw * 0.65, ink: PAL.woodDark, a: 0.55 });
        }
      },
    }
  );

  // Red Roman vexillum banner & eagle standard beside gate
  flag(g, gx + s * 0.62, gy + s * 0.02, s * 0.55, { color: PAL.red, charge: 'wings', chargeColor: PAL.yellow, t, lw });
  standard(g, gx - s * 0.64, gy + s * 0.02, s * 0.58, { kind: 'eagle', t });
}

// Draw warm dawn sky + distant Italian hills + cypresses + camp tents
export function drawRomanDawnSkyAndHills(g, worldState = {}, opts = {}) {
  const w = W(), h = H();
  const gy = (opts.groundY ?? 0.66) * h;
  const t = worldState.globalT ?? opts.t ?? 0;
  const seed = opts.seed ?? 17;
  const tm = TIMES.dawn;

  // Warm dawn sky gradient (overscanned 3x so camera pan/zoom never reveals canvas border)
  const gr = g.createLinearGradient(0, -h * 0.15, 0, gy + h * 0.08);
  gr.addColorStop(0, '#9fb3d4');
  gr.addColorStop(0.55, '#e8c7aa');
  gr.addColorStop(1, '#fae0b8');
  g.fillStyle = gr;
  g.fillRect(-w, -h, w * 3, h * 3);

  // Low dawn sun disc positioned to cast warm golden shafts across the shield line
  const sunX = (opts.sunX ?? 0.74) * w;
  const sunY = (opts.sunY ?? 0.34) * h;
  const sunR = h * 0.068;
  g.save();
  const sgr = g.createRadialGradient(sunX, sunY, sunR * 0.4, sunX, sunY, sunR * 3.8);
  sgr.addColorStop(0, alpha('#fff3cf', 0.82));
  sgr.addColorStop(0.45, alpha('#ffd996', 0.32));
  sgr.addColorStop(1, alpha('#ffd996', 0));
  g.fillStyle = sgr;
  g.fillRect(sunX - sunR * 4, sunY - sunR * 4, sunR * 8, sunR * 8);
  circ(g, sunX, sunY, sunR, { fill: '#fff3d1', lw: 0 });
  g.restore();

  // Soft dawn clouds drifting deterministically by globalT
  const rc = rng(seed + 3);
  const nClouds = opts.clouds ?? 3;
  for (let i = 0; i < nClouds; i++) {
    const baseX = rc() * w * 1.15 - w * 0.08;
    const cx = ((baseX + t * (4.5 + i * 1.8)) % (w * 1.35)) - w * 0.15;
    const cy = h * (0.12 + rc() * 0.18);
    const cs = h * (0.075 + rc() * 0.045);
    cloud(g, cx, cy, cs, { color: tm.cloud, shade: tm.cloudSh, lw: 2 });
  }

  // Far ridge & mid ridge in Squire vector style
  const drawRidge = (yBase, amp, fillCol, rSeed) => {
    const r = rng(rSeed);
    g.save();
    g.beginPath();
    g.moveTo(-w * 0.3, h * 1.4);
    g.lineTo(-w * 0.3, yBase);
    for (let i = 0; i <= 8; i++) {
      const x = -w * 0.3 + (i / 8) * (w * 1.6);
      const y = yBase - r() * amp;
      g.lineTo(x, y);
    }
    g.lineTo(w * 1.3, h * 1.4);
    g.closePath();
    g.fillStyle = fillCol;
    g.fill();
    g.restore();
  };
  drawRidge(gy - h * 0.075, h * 0.085, '#b5b2c0', seed + 11);
  drawRidge(gy - h * 0.015, h * 0.045, '#92a56b', seed + 19);

  // Mediterranean cypress & pine treeline
  const rt = rng(seed + 29);
  for (let i = 0; i < 11; i++) {
    const tx = -w * 0.05 + (i / 10) * (w * 1.1) + (rt() - 0.5) * 35;
    const ts = h * (0.068 + rt() * 0.042);
    tree(g, tx, gy - h * 0.01, ts, {
      kind: i % 2 === 0 ? 'cypress' : 'pine',
      color: mix('#6a8a44', '#a7aabb', 0.38),
      lw: 1.6,
    });
  }
}

// Draw compacted sandy drill ground with chalk shield-line marker, grass tufts & pebbles
export function drawRomanDrillGroundPlane(g, worldState = {}, opts = {}) {
  const w = W(), h = H();
  const gy = (opts.groundY ?? 0.66) * h;
  const seed = opts.seed ?? 23;

  // Base meadow skirt + compacted sandy Roman drill arena
  g.fillStyle = '#869d50';
  g.fillRect(-w * 0.5, gy - 4, w * 2, h * 1.5);

  // Sandy training lane
  const laneTop = gy + h * 0.045;
  const laneBot = h * 1.25;
  shape(
    g,
    (c) => {
      c.moveTo(-w * 0.4, laneTop);
      c.quadraticCurveTo(w * 0.5, laneTop - h * 0.015, w * 1.4, laneTop + h * 0.008);
      c.lineTo(w * 1.4, laneBot);
      c.lineTo(-w * 0.4, laneBot);
      c.closePath();
    },
    { fill: '#c8ab79', lw: 2.5, ink: OUT }
  );

  // Subtle warm-sand tonal bands
  const r = rng(seed + 5);
  for (let i = 0; i < 6; i++) {
    const yy = laneTop + (i + 0.6) * ((h - laneTop) / 6);
    ellipse(g, w * (0.18 + r() * 0.65), yy, w * (0.32 + r() * 0.25), h * 0.028, {
      fill: alpha(i % 2 ? '#d9be8d' : '#b1915f', 0.38),
      lw: 0,
    });
  }

  // Chalk/lime formation line where recruits plant their front sandals & scutum rims
  const lineY = (opts.chalkLineY ?? 0.885) * h;
  line(g, [[-w * 0.15, lineY], [w * 1.15, lineY]], {
    lw: Math.max(3, h * 0.0055),
    ink: alpha('#f5eedc', 0.62),
    dash: [26, 16],
  });

  // Pebbles & grass tufts along border
  for (let i = 0; i < 14; i++) {
    const px = -w * 0.05 + r() * w * 1.1;
    const py = laneTop + r() * (h - laneTop);
    const ps = 3 + ((py - laneTop) / Math.max(1, h - laneTop)) * 7;
    pebble(g, px, py, ps, Math.max(1.1, ps * 0.18));
  }
  for (let i = 0; i < 12; i++) {
    const gx = -w * 0.04 + r() * w * 1.08;
    const gy2 = gy + h * 0.012 + r() * h * 0.038;
    grassClump(g, gx, gy2, 12 + r() * 10, '#789444', 1.5, i + seed);
  }
}

// Seeded non-synchronized background Roman cohort line (genuine independent phase, faces & breathing)
export function drawRomanCohortLine2D(g, worldState = {}, opts = {}) {
  const w = W(), h = H();
  const t = worldState.globalT ?? opts.t ?? 0;
  const count = opts.count ?? 7;
  const x0 = (opts.x0 ?? 0.28) * w;
  const x1 = (opts.x1 ?? 0.86) * w;
  const yBase = (opts.y ?? 0.74) * h;
  const unitH = (opts.hFrac ?? 0.18) * h;
  const seed = opts.seed ?? 41;
  const r = rng(seed);
  const faces = ['neutral', 'determined', 'focused', 'calm', 'bored', 'neutral'];

  for (let i = 0; i < count; i++) {
    if (opts.skipIndices && opts.skipIndices.includes(i)) continue;
    const k = count === 1 ? 0.5 : i / (count - 1);
    const sx = lerp(x0, x1, k) + (r() - 0.5) * unitH * 0.12;
    const sy = yBase + (r() - 0.5) * unitH * 0.05;
    const sh = unitH * (0.95 + r() * 0.08);
    const unitSeed = seed + i * 19;
    const phaseT = t + i * 0.67 + r() * 0.9;
    const face = faces[(i * 3 + Math.floor(phaseT * 0.22)) % faces.length];
    const preset = i === 0 ? 'princeps' : 'hastatus';
    const braceShift = Math.sin(phaseT * 1.35 + unitSeed) * 1.2;

    soldier(g, sx, sy, sh, {
      preset,
      face,
      pose: opts.pose || 'guard',
      flip: !!opts.flip,
      look: opts.look ?? -0.25,
      t: phaseT,
      seed: unitSeed,
      featherBend: Math.sin(phaseT * 2.1 + unitSeed) * 0.04,
      romanMasterPolish: true,
      shield: {
        type: 'scutum',
        color: PAL.red,
        rim: PAL.gold,
        charge: preset === 'princeps' ? 'wings' : 'lightning',
        chargeColor: PAL.yellow,
        x: (opts.shieldXU ?? 4) + braceShift * 0.3,
        y: -38,
        rot: -0.03,
      },
      lod: sh < 72 ? 'low' : 'high',
    });
  }
}

// Composite 2D Roman Training Yard (used by world.js opt-in bg & pilot shots)
export function drawRomanTrainingYard2D(g, worldState = {}, cam = null, opts = {}) {
  const w = W(), h = H();
  const gy = (opts.groundY ?? 0.66) * h;
  const t = worldState.globalT ?? opts.t ?? 0;

  drawRomanDawnSkyAndHills(g, worldState, opts);
  // Legionary camp tents in midground right-center
  if (opts.showTents !== false) {
    for (let i = 0; i < 4; i++) {
      tent(g, w * (0.44 + i * 0.115), gy + h * 0.025, h * 0.105, {
        color: PAL.cream,
        color2: PAL.red,
        lw: 1.7,
      });
    }
  }
  if (opts.showGate !== false) {
    drawRomanGateAndRamp2D(g, worldState, cam, { groundY: opts.groundY ?? 0.66, gateX: opts.gateX ?? 0.15, scale: 0.31 });
  }
  drawRomanDrillGroundPlane(g, worldState, opts);
  if (opts.showCohort) {
    drawRomanCohortLine2D(g, worldState, { y: 0.73, hFrac: 0.155, x0: 0.38, x1: 0.84, count: 6, seed: 53 });
  }
  if (opts.showRack !== false) {
    drawRomanTrainingRack2D(g, w * (opts.rackX ?? 0.89), gy + h * 0.11, h * 0.21);
  }
  if (opts.warmHaze !== false) {
    haze(g, '#ffd39b', opts.hazeAlpha ?? 0.06);
  }
}

// Composite 2D Roman Shield Wall line with controllable gap width & sunlight sliver
export function drawRomanShieldWall2D(g, worldState = {}, cam = null, opts = {}) {
  const w = W(), h = H();
  const gapPx = opts.gapWidthPx ?? 0;
  const gapCenterX = (opts.gapCenterX ?? 0.52) * w;
  const wallY = (opts.wallY ?? 0.86) * h;
  const shieldS = (opts.shieldScaleH ?? 0.42) * h;
  const lw = opts.lw ?? Math.max(2.2, shieldS * 0.032);

  // Golden dawn sunlight shaft streaming through the exposed gap before closure
  if (gapPx > 3 && opts.showSunSliver !== false) {
    const normGap = clamp(gapPx / (shieldS * 0.32), 0, 1);
    g.save();
    const beamGrad = g.createLinearGradient(gapCenterX, wallY - shieldS * 0.65, gapCenterX, wallY + shieldS * 0.65);
    beamGrad.addColorStop(0, alpha('#fff6d1', 0.78 * normGap));
    beamGrad.addColorStop(0.55, alpha('#ffd98c', 0.48 * normGap));
    beamGrad.addColorStop(1, alpha('#ffd98c', 0.0));
    g.fillStyle = beamGrad;
    g.beginPath();
    g.moveTo(gapCenterX - gapPx * 0.52, wallY - shieldS * 0.56);
    g.lineTo(gapCenterX + gapPx * 0.52, wallY - shieldS * 0.56);
    g.lineTo(gapCenterX + gapPx * 1.45, wallY + shieldS * 0.68);
    g.lineTo(gapCenterX - gapPx * 1.45, wallY + shieldS * 0.68);
    g.closePath();
    g.fill();
    g.restore();
  }

  if (opts.drawNeighborShields) {
    const rx = shieldS * 0.33;
    const leftShieldX = gapCenterX - gapPx / 2 - rx * 1.01;
    const rightShieldX = gapCenterX + gapPx / 2 + rx * 1.01 + (opts.rookieTremorPx || 0);
    shield(g, leftShieldX, wallY - shieldS * 0.46, shieldS, {
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'wings',
      chargeColor: PAL.yellow,
      romanMasterPolish: true,
      rot: -0.015,
      lw,
    });
    shield(g, rightShieldX, wallY - shieldS * 0.46 + (opts.rookieDropPx || 0), shieldS, {
      type: 'scutum',
      color: PAL.red,
      rim: PAL.gold,
      charge: 'lightning',
      chargeColor: PAL.yellow,
      romanMasterPolish: true,
      rot: opts.rookieRot ?? 0.045,
      lw,
    });

    // Optional leather strap loop on inner edge of neighboring shield (for SH08 comic snag motif)
    if (opts.showNeighborStrap) {
      const strapX = leftShieldX + rx * 0.84;
      const strapY = wallY - shieldS * 0.54;
      shape(
        g,
        (c) => {
          c.moveTo(strapX - shieldS * 0.03, strapY - shieldS * 0.05);
          c.quadraticCurveTo(strapX + shieldS * 0.055, strapY, strapX - shieldS * 0.03, strapY + shieldS * 0.055);
        },
        { fill: null, lw: Math.max(3, lw * 1.25), ink: PAL.leather }
      );
      if (opts.snaggedSpear) {
        weapon(g, 'spear', strapX + shieldS * 0.02, strapY + shieldS * 0.24, shieldS * 0.92, Math.PI - 0.24, { lw });
      }
    }
  }
}

export { dustPuff };
