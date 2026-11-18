// market_env.js — Original Squire 2D Sunny Roman Market Hill Street, Stalls & Crowd Layers for KH-03.0.R2.
// Built strictly with Production ink.js / world.js primitives & #392a21 outlines. Zero 3D, zero R1/KH03.0 reuse.
import { E, clamp, lerp, alpha } from '../ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, line } from '../ink.js';
import { cloud, bush, tree, pebble } from '../world.js';
import { soldier } from '../chara.js';

const W = () => E.W || 1080;
const H = () => E.H || 1920;

export function drawRomanMarketSlopeBackdrop2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const scrollX = opts.scrollX ?? 0;
  const slopeDrop = opts.slopeDropFrac ?? 0.08;
  const lw = Math.max(2.2, w * 0.0028);

  // Bright warm Mediterranean Roman morning sky (distinct terracotta daylight palette vs R1 dusk!)
  const sky = g.createLinearGradient(0, 0, 0, h * 0.56);
  sky.addColorStop(0.0, '#629cc8');
  sky.addColorStop(0.62, '#a7cde4');
  sky.addColorStop(1.0, '#f4dec1');
  g.fillStyle = sky;
  g.fillRect(-40, -40, w + 80, h * 0.65);

  for (let i = 0; i < 4; i++) {
    const cx = (((i * 0.29 + t * 0.006 - scrollX * 0.0001) % 1.25 + 1.25) % 1.25 - 0.12) * w;
    cloud(g, cx, (0.09 + (i % 2) * 0.06) * h, w * 0.16, '#fffdf7');
  }

  // Distant Palatine-style hillside, cypresses & temple gable silhouette
  const hillY = h * 0.40;
  shape(
    g,
    (c) => {
      c.moveTo(-40, hillY + h * 0.12);
      c.lineTo(-40, hillY);
      c.quadraticCurveTo(w * 0.32, hillY - h * 0.07, w * 0.66, hillY - h * 0.02);
      c.quadraticCurveTo(w * 0.85, hillY - h * 0.05, w + 40, hillY + h * 0.01);
      c.lineTo(w + 40, hillY + h * 0.14);
      c.closePath();
    },
    { fill: '#889f69', lw: lw * 0.85 }
  );
  tree(g, w * 0.16, hillY - h * 0.01, w * 0.14, 'cypress', PAL.treeDark);
  tree(g, w * 0.84, hillY + h * 0.005, w * 0.13, 'cypress', PAL.treeDark);

  // Market stalls & travertine colonnade descending slightly downhill left -> right
  const floorLeftY = h * (0.50 - slopeDrop * 0.5);
  const floorRightY = h * (0.50 + slopeDrop * 0.5);

  const stallSpan = w * 0.55;
  const shift = ((scrollX % (stallSpan * 2)) + stallSpan * 2) % (stallSpan * 2);
  for (let k = -1; k <= 3; k++) {
    const sx = k * stallSpan - shift * 0.65;
    const u = clamp(sx / w, 0, 1);
    const sy = lerp(floorLeftY, floorRightY, u);
    // Masonry shopfront back wall + timber awning + red/cream striped canopy
    rect(g, sx + w * 0.03, sy - h * 0.21, w * 0.44, h * 0.21, { fill: '#dcc8a8', lw, r: 3 });
    // Striped terracotta market awning
    for (let st = 0; st < 5; st++) {
      const aw = (w * 0.46) / 5;
      rect(g, sx + w * 0.02 + st * aw, sy - h * 0.22, aw, h * 0.055, {
        fill: st % 2 === 0 ? '#c9473a' : '#f7efe0',
        lw: lw * 0.75,
        r: 2,
      });
    }
    // Shop wooden counter
    rect(g, sx + w * 0.05, sy - h * 0.07, w * 0.36, h * 0.07, { fill: '#8a5730', lw: lw * 0.85, r: 2 });
  }

  // Descending cobbled street road apron across lower half (clean clear contrast for cart/runners/captions!)
  shape(
    g,
    (c) => {
      c.moveTo(-40, floorLeftY - slopeDrop * 0.1 * h);
      c.lineTo(w + 40, floorRightY + slopeDrop * 0.1 * h);
      c.lineTo(w + 40, h + 40);
      c.lineTo(-40, h + 40);
      c.closePath();
    },
    { fill: '#a9957b', lw }
  );

  // Foreground scrolling market cobbles & road curbs
  const cobStep = w * 0.18;
  const cShift = ((scrollX % cobStep) + cobStep) % cobStep;
  for (let r = 0; r < 5; r++) {
    const baseY = lerp(floorLeftY, floorRightY, 0.5) + (r + 0.5) * (h * 0.082);
    for (let c = -1; c < 8; c++) {
      const cx = c * cobStep - cShift + (r % 2) * cobStep * 0.5;
      ellipse(g, cx, baseY + (cx / w - 0.5) * slopeDrop * h, w * 0.072, h * 0.021, {
        fill: (r + c) % 2 === 0 ? '#978268' : '#857058',
        lw: lw * 0.65,
      });
    }
  }
  pebble(g, w * 0.20, h * 0.74, w * 0.024, 1);
  pebble(g, w * 0.78, h * 0.79, w * 0.028, 4);
}

// Style-matched Squire Roman market citizens reacting / cheering along upper plaza curb
export function drawMarketCrowdGroup2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const mood = opts.mood || 'watch'; // 'watch' | 'gasp' | 'cheer' | 'hush'
  const t = state.globalT ?? 0;
  const positions = opts.positions || [
    { x: 0.12, y: 0.46, h: 0.165, col: PAL.red, look: 0.4, seed: 3, flip: false },
    { x: 0.27, y: 0.45, h: 0.17, col: '#4a7a5c', look: 0.2, seed: 5, flip: false },
    { x: 0.73, y: 0.46, h: 0.17, col: '#c79745', look: -0.3, seed: 9, flip: true },
    { x: 0.88, y: 0.47, h: 0.165, col: PAL.crimson, look: -0.5, seed: 12, flip: true },
  ];
  for (const p of positions) {
    const hop = mood === 'cheer' ? Math.abs(Math.sin(t * 9.0 + p.seed)) * h * 0.018 : 0;
    const pose = mood === 'cheer' ? 'cheer' : mood === 'gasp' ? 'cower' : 'stand';
    const face = mood === 'cheer' ? 'laugh' : mood === 'gasp' ? 'shock' : mood === 'hush' ? 'awkward' : 'neutral';
    soldier(g, p.x * w, p.y * h - hop, p.h * h, {
      helmet: null,
      hair: 'short',
      hairColor: p.seed % 2 ? '#593b25' : '#8e7459',
      body: 'tunic',
      tunicColor: p.col,
      legs: 'bare',
      pose,
      face,
      look: p.look,
      flip: p.flip,
      shield: null,
      weapon: 'none',
      t: t + p.seed,
      seed: p.seed,
    });
  }
}

export function drawMarketForegroundPass2D(g, progress = 0) {
  const w = W(), h = H();
  // Clean Squire speed-streak & market awning banner pennant along top edge ONLY (never darkens y>=0.615*H caption band)
  const px = lerp(1.12, -0.18, clamp(progress, 0, 1)) * w;
  g.save();
  g.globalAlpha = 0.45;
  rect(g, px, h * 0.16, w * 0.038, h * 0.28, { fill: '#7c4c29', lw: 2, r: 4 });
  line(g, [[px - w * 0.14, h * 0.56], [px - w * 0.02, h * 0.56]], { lw: 4, ink: '#fff4da' });
  line(g, [[px - w * 0.22, h * 0.585], [px - w * 0.06, h * 0.585]], { lw: 3, ink: '#fff4da' });
  g.restore();
}
