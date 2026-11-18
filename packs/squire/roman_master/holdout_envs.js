// holdout_envs.js — Distinct Procedural Squire 2D Environments & Props for R2 Multi-Script Holdouts:
// B) Roman River Harbor Quay + Drifting Cloth Vexillum Standard
// C) Roman Forum Courtyard + Stone Senator Bench + Dropped Ceremonial Helmet
// 100% 2D Canvas via Production ink.js / world.js / chara.js primitives. Zero R1 or market-cart assets reused.
import { E, clamp, lerp, alpha } from '../ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, line, tube } from '../ink.js';
import { cloud, pebble } from '../world.js';

const W = () => E.W || 1080;
const H = () => E.H || 1920;

// ---- HOLDOUT B: ROMAN RIVER HARBOR QUAY & DRIFTING VEXILLUM ----
export function drawRomanRiverHarbor2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const lw = Math.max(2.2, w * 0.0028);

  const sky = g.createLinearGradient(0, 0, 0, h * 0.48);
  sky.addColorStop(0.0, '#4f8dc2');
  sky.addColorStop(1.0, '#cfe5f4');
  g.fillStyle = sky;
  g.fillRect(-30, -30, w + 60, h * 0.55);

  cloud(g, w * 0.22, h * 0.11, w * 0.18, '#fff');
  cloud(g, w * 0.78, h * 0.15, w * 0.15, '#fff');

  // Flowing Tiber/harbor river across right & middle water plane
  const riverY = h * 0.42;
  const waterGrad = g.createLinearGradient(0, riverY, 0, h);
  waterGrad.addColorStop(0, '#3e7da3');
  waterGrad.addColorStop(1, '#275978');
  g.fillStyle = waterGrad;
  g.fillRect(-30, riverY, w + 60, h - riverY + 30);

  // Flowing water current ripple highlights
  const curShift = ((t * w * 0.22) % (w * 0.35));
  for (let row = 0; row < 6; row++) {
    const ry = riverY + h * (0.04 + row * 0.075);
    for (let col = -1; col < 5; col++) {
      const rx = col * w * 0.35 + curShift;
      line(g, [[rx, ry], [rx + w * 0.14, ry]], { lw: lw * 1.1, ink: alpha('#d4effa', 0.48) });
    }
  }

  // Travertine stone harbor quay + oak pilings on left side
  const quayRight = w * (opts.quayRightFrac ?? 0.52);
  const quayTop = h * 0.38;
  rect(g, -20, quayTop, quayRight + 20, h * 0.34, { fill: '#cbb694', lw, r: 4 });
  rect(g, -20, quayTop, quayRight + 26, h * 0.04, { fill: '#dfccb0', lw, r: 3 });
  // Oak wharf mooring posts
  for (const px of [quayRight - w * 0.10, w * 0.14]) {
    rect(g, px - w * 0.032, quayTop - h * 0.07, w * 0.064, h * 0.14, { fill: '#7d4f2d', lw, r: 4 });
  }
}

export function drawClothVexillum2D(g, x, y, s, opts = {}) {
  const t = opts.t ?? 0;
  const rot = opts.rot ?? 0.35;
  const lw = opts.lw ?? Math.max(2.0, s * 0.025);
  const wave = Math.sin(t * 5.2) * s * 0.06;
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  // Water foam ripple if submerged in river
  if (opts.inWater) {
    ellipse(g, 0, s * 0.12, s * 0.65, s * 0.16, { fill: alpha('#d6f1fc', 0.45), lw: lw * 0.6 });
  }
  // Wooden spear crossbar & crimson SPQR cloth vexillum banner
  tube(g, [[-s * 0.45, 0], [s * 0.55, 0]], s * 0.04, PAL.wood, lw * 0.85);
  tube(g, [[0, -s * 0.36], [0, s * 0.36]], s * 0.035, PAL.wood, lw * 0.85);
  shape(
    g,
    (c) => {
      c.moveTo(0, -s * 0.34);
      c.lineTo(s * 0.42, -s * 0.28 + wave);
      c.lineTo(s * 0.38, s * 0.28 + wave);
      c.lineTo(0, s * 0.34);
      c.closePath();
    },
    { fill: PAL.red, lw }
  );
  // Gold embroidered fringe & eagle medallion
  circ(g, s * 0.20, wave * 0.5, s * 0.09, { fill: PAL.gold, lw: lw * 0.7 });
  g.restore();
}

// ---- HOLDOUT C: ROMAN FORUM COURTYARD, STONE BENCH & DROPPED HELMET ----
export function drawRomanForumCourtyard2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const lw = Math.max(2.2, w * 0.0028);

  const sky = g.createLinearGradient(0, 0, 0, h * 0.46);
  sky.addColorStop(0.0, '#78add6');
  sky.addColorStop(1.0, '#f5e8d0');
  g.fillStyle = sky;
  g.fillRect(-30, -30, w + 60, h * 0.52);

  // Fluted travertine forum colonnade wall in background
  const floorY = h * 0.55;
  rect(g, -20, h * 0.18, w + 40, floorY - h * 0.18, { fill: '#e5d6bd', lw, r: 0 });
  rect(g, -20, h * 0.14, w + 40, h * 0.05, { fill: '#d2c0a1', lw, r: 0 });
  for (let c = 0; c < 4; c++) {
    const cx = (0.14 + c * 0.24) * w;
    rect(g, cx - w * 0.045, h * 0.19, w * 0.09, floorY - h * 0.19, { fill: '#f1e5ce', lw, r: 2 });
    line(g, [[cx - w * 0.015, h * 0.20], [cx - w * 0.015, floorY - 4]], { lw: lw * 0.5, ink: '#c4b295' });
    line(g, [[cx + w * 0.015, h * 0.20], [cx + w * 0.015, floorY - 4]], { lw: lw * 0.5, ink: '#c4b295' });
  }

  // Polished forum travertine tile floor
  rect(g, -30, floorY, w + 60, h - floorY + 30, { fill: '#ceb99a', lw, r: 0 });
  for (let r = 1; r <= 5; r++) {
    const ry = floorY + (r / 5.2) * (h - floorY);
    line(g, [[-30, ry], [w + 30, ry]], { lw: lw * 0.55, ink: alpha('#7c6852', 0.4) });
  }
  pebble(g, w * 0.18, floorY + h * 0.15, w * 0.02, 2);
}

export function drawStoneSenatorBench2D(g, x, y, wBench, hBench, opts = {}) {
  const lw = opts.lw ?? Math.max(2.2, wBench * 0.012);
  g.save();
  g.translate(x, y);
  // Shadow underneath bench seat (clear negative gap where rolled helmet sits!)
  ellipse(g, 0, -hBench * 0.05, wBench * 0.46, hBench * 0.18, { fill: alpha('#291c15', 0.32), lw: 0 });
  // Carved marble lion-paw leg pedestals flanking ends so middle gap stays wide open
  rect(g, -wBench * 0.44, -hBench * 0.85, wBench * 0.14, hBench * 0.85, { fill: '#d6c6ac', lw, r: 3 });
  rect(g, wBench * 0.30, -hBench * 0.85, wBench * 0.14, hBench * 0.85, { fill: '#d6c6ac', lw, r: 3 });
  // Thick top marble bench slab
  rect(g, -wBench * 0.50, -hBench, wBench, hBench * 0.28, { fill: '#efe4cf', lw, r: 5 });
  g.restore();
}

export function drawCeremonialHelmetProp2D(g, x, y, r, opts = {}) {
  const rot = opts.rot ?? 0;
  const lw = opts.lw ?? Math.max(2.0, r * 0.06);
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  // Montefortino bronze dome + gold brow band + white/gold ceremonial plume
  shape(
    g,
    (c) => {
      c.moveTo(-r, r * 0.25);
      c.bezierCurveTo(-r * 0.95, -r * 0.95, r * 0.95, -r * 0.95, r, r * 0.25);
      c.closePath();
    },
    { fill: PAL.bronze, lw }
  );
  rect(g, -r * 1.04, r * 0.08, r * 2.08, r * 0.22, { fill: PAL.gold, lw: lw * 0.9, r: 3 });
  // Plume crest knob
  ellipse(g, 0, -r * 0.92, r * 0.18, r * 0.34, { fill: PAL.red, lw: lw * 0.85 });
  g.restore();
}
