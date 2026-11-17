// gate_city_env.js — Original Squire 2D Roman Dusk City Gate, Cobble Alley, Winch Tower & Scroll Props for KH-03.0.R1.
// 100% 2D Canvas built strictly with Production packs/squire/{ink.js,world.js,army.js} primitives & #392a21 ink discipline.
import { E, clamp, lerp, alpha, mix } from '../ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, polyS, line, tube, darker, lighter, haze, FONT_CAP } from '../ink.js';
import { cloud, pebble, bush, grassClump } from '../world.js';
import { dustPuff } from '../army.js';

const W = () => E.W || 1080;
const H = () => E.H || 1920;

export function drawDuskSkyAndWallsBackdrop(g, w, h, opts = {}) {
  const skyGrad = g.createLinearGradient(0, 0, 0, h * 0.66);
  skyGrad.addColorStop(0.0, '#36324d');
  skyGrad.addColorStop(0.38, '#7a5260');
  skyGrad.addColorStop(0.75, '#d67e4f');
  skyGrad.addColorStop(1.0, '#f3b768');
  g.fillStyle = skyGrad;
  g.fillRect(-40, -40, w + 80, h * 0.72);

  // Subtle golden sun disc low near horizon
  const sunX = (opts.sunXFrac ?? 0.50) * w;
  const sunY = (opts.sunYFrac ?? 0.44) * h;
  const sunGlow = g.createRadialGradient(sunX, sunY, w * 0.02, sunX, sunY, w * 0.42);
  sunGlow.addColorStop(0, alpha('#ffe79e', 0.85));
  sunGlow.addColorStop(0.45, alpha('#f59f4c', 0.35));
  sunGlow.addColorStop(1, alpha('#f59f4c', 0));
  g.fillStyle = sunGlow;
  g.fillRect(0, 0, w, h * 0.72);

  const t = opts.t ?? 0;
  for (let i = 0; i < 4; i++) {
    const cx = (((i * 0.31 + t * 0.008) % 1.2) - 0.1) * w;
    const cy = (0.10 + (i % 2) * 0.065) * h;
    cloud(g, cx, cy, w * (0.16 + (i % 2) * 0.04), '#e8a88d');
  }

  // Distant Roman aqueduct & hills in dusky mauve-brown silhouette
  const horizY = (opts.horizonYFrac ?? 0.48) * h;
  shape(
    g,
    (c) => {
      c.moveTo(-40, horizY + h * 0.10);
      c.lineTo(-40, horizY - h * 0.02);
      c.quadraticCurveTo(w * 0.25, horizY - h * 0.075, w * 0.55, horizY - h * 0.025);
      c.quadraticCurveTo(w * 0.82, horizY - h * 0.06, w + 40, horizY - h * 0.015);
      c.lineTo(w + 40, horizY + h * 0.12);
      c.closePath();
    },
    { fill: '#5d4757', lw: Math.max(1.8, w * 0.0022) }
  );

  // Aqueduct silhouette band
  const aqTop = horizY - h * 0.055;
  const aqBottom = horizY + h * 0.01;
  rect(g, -20, aqTop, w + 40, h * 0.018, { fill: '#4e3c4a', lw: Math.max(1.5, w * 0.0018), r: 0 });
  const piers = 8;
  for (let p = 0; p < piers; p++) {
    const px = (p / (piers - 1)) * w;
    rect(g, px - w * 0.018, aqTop + h * 0.012, w * 0.036, aqBottom - aqTop, {
      fill: '#4e3c4a',
      lw: Math.max(1.4, w * 0.0016),
      r: 0,
    });
  }
}

export function drawTorchFlame2D(g, x, y, s, t = 0) {
  const fl = Math.sin(t * 17.3 + x * 0.05) * 0.14 + Math.cos(t * 23.1 + y * 0.03) * 0.08;
  const glow = g.createRadialGradient(x, y - s * 0.25, s * 0.08, x, y - s * 0.25, s * 1.45);
  glow.addColorStop(0, alpha('#ffd36e', 0.55));
  glow.addColorStop(1, alpha('#f07c29', 0));
  g.fillStyle = glow;
  g.beginPath();
  g.arc(x, y - s * 0.25, s * 1.45, 0, Math.PI * 2);
  g.fill();

  // Iron bracket & torch cup
  rect(g, x - s * 0.10, y, s * 0.20, s * 0.42, { fill: '#4f3c33', lw: Math.max(1.5, s * 0.045), r: 2 });
  shape(
    g,
    (c) => {
      c.moveTo(x - s * 0.26, y - s * 0.02);
      c.quadraticCurveTo(x - s * 0.18 + fl * s, y - s * 0.58, x + fl * s * 0.8, y - s * 0.92);
      c.quadraticCurveTo(x + s * 0.26, y - s * 0.52, x + s * 0.24, y - s * 0.02);
      c.closePath();
    },
    { fill: '#ef7b2d', lw: Math.max(1.6, s * 0.05) }
  );
  shape(
    g,
    (c) => {
      c.moveTo(x - s * 0.13, y);
      c.quadraticCurveTo(x + fl * s * 0.4, y - s * 0.44, x + fl * s * 0.35, y - s * 0.60);
      c.quadraticCurveTo(x + s * 0.14, y - s * 0.34, x + s * 0.12, y);
      c.closePath();
    },
    { fill: '#ffe57f', lw: 0 }
  );
}

// Heavy twin oak city gate leaves converging dynamically via `closeFrac` (0 = wide open, 1 = slammed shut)
export function drawRomanGateLeaves2D(g, cx, baseY, doorW, doorH, closeFrac = 0.45, opts = {}) {
  const cf = clamp(closeFrac, 0, 1);
  const gapPx = (1 - cf) * doorW * 0.92;
  const leafW = doorW * 0.52;
  const topY = baseY - doorH;
  const lw = opts.lw ?? Math.max(2.0, doorW * 0.008);
  const boltDrop = clamp(opts.boltDropFrac ?? (cf > 0.95 ? (cf - 0.95) * 20 : 0), 0, 1);
  const t = opts.t ?? 0;

  // Sunset light wedge pouring through closing slit onto floor behind/below doors
  if (gapPx > 3) {
    g.save();
    const beamGrad = g.createLinearGradient(cx, topY, cx, baseY + doorH * 0.42);
    beamGrad.addColorStop(0, alpha('#ffd382', 0.42));
    beamGrad.addColorStop(1, alpha('#f08a41', 0.0));
    g.fillStyle = beamGrad;
    g.beginPath();
    g.moveTo(cx - gapPx * 0.48, topY + doorH * 0.06);
    g.lineTo(cx + gapPx * 0.48, topY + doorH * 0.06);
    g.lineTo(cx + gapPx * 1.45, baseY + doorH * 0.38);
    g.lineTo(cx - gapPx * 1.45, baseY + doorH * 0.38);
    g.closePath();
    g.fill();
    g.restore();
  }

  for (const side of [-1, 1]) {
    const innerX = cx + side * (gapPx * 0.5);
    const x0 = side < 0 ? innerX - leafW : innerX;
    // Main oak panel
    rect(g, x0, topY, leafW, doorH, { fill: '#7e4e2d', lw, r: 2 });
    // Vertical plank ink seams
    for (let p = 1; p < 4; p++) {
      const px = x0 + (leafW * p) / 4;
      line(g, [[px, topY + lw], [px, baseY - lw]], { lw: lw * 0.65, ink: darker('#7e4e2d', 0.25) });
    }
    // Iron hinge bands + studs
    for (const fy of [0.22, 0.52, 0.80]) {
      const by = topY + doorH * fy;
      rect(g, x0 + lw * 0.5, by, leafW - lw, doorH * 0.055, { fill: '#4c4649', lw: lw * 0.78, r: 2 });
      for (let st = 0; st < 3; st++) {
        circ(g, x0 + leafW * (0.2 + st * 0.3), by + doorH * 0.027, lw * 1.4, { fill: '#8a8286', lw: lw * 0.45 });
      }
    }
    // Iron lock staple near center seam
    const lockX = side < 0 ? innerX - doorW * 0.07 : innerX + doorW * 0.02;
    rect(g, lockX, baseY - doorH * 0.46, doorW * 0.05, doorH * 0.075, { fill: '#3f3b3e', lw: lw * 0.75, r: 2 });
  }

  // Massive iron locking bar / bolt beam across center seam (slides down on slam!)
  if (opts.showBolt !== false) {
    const barW = doorW * 0.64;
    const barH = doorH * 0.07;
    const raisedY = baseY - doorH * 0.58;
    const lockedY = baseY - doorH * 0.455;
    const barY = lerp(raisedY, lockedY, boltDrop);
    const barX = cx - barW * (opts.interiorSide ? 0.5 : 0.72) + (1 - cf) * doorW * 0.16;
    rect(g, barX, barY, barW, barH, { fill: '#5b4232', lw: lw * 0.9, r: 4 });
    rect(g, barX + barW * 0.08, barY + barH * 0.18, barW * 0.18, barH * 0.64, { fill: '#6c666a', lw: lw * 0.6, r: 2 });
    rect(g, barX + barW * 0.74, barY + barH * 0.18, barW * 0.18, barH * 0.64, { fill: '#6c666a', lw: lw * 0.6, r: 2 });
  }

  // Impact dust bursts at center seam on slam
  if (cf > 0.95 && opts.slamFlash !== false) {
    const k = clamp((cf - 0.95) / 0.05, 0, 1);
    dustPuff(g, cx, baseY - doorH * 0.42, doorW * 0.18, k * 0.8 + (t % 0.4) * 0.2);
  }
}

export function drawRomanCityApproachDusk2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const closeFrac = clamp(state.gateCloseFrac ?? 0.35, 0, 1);
  const horizonY = (opts.horizonYFrac ?? 0.51) * h;

  drawDuskSkyAndWallsBackdrop(g, w, h, { t, horizonYFrac: 0.48 });

  // Stone roadway trapezoid ascending to the city gate archway
  const roadGrad = g.createLinearGradient(0, horizonY, 0, h);
  roadGrad.addColorStop(0, '#c6b192');
  roadGrad.addColorStop(0.6, '#b09878');
  roadGrad.addColorStop(1, '#8d7559');
  g.fillStyle = roadGrad;
  g.fillRect(-30, horizonY, w + 60, h - horizonY + 40);

  // Ashlar city gate towers flanking left/right
  const gateCx = (opts.gateCxFrac ?? 0.50) * w;
  const archW = (opts.archWFrac ?? 0.52) * w;
  const archH = (opts.archHFrac ?? 0.32) * h;
  const groundY = (opts.groundYFrac ?? 0.58) * h;
  const lw = Math.max(2.2, w * 0.0028);

  // City walls left & right bastions
  for (const s of [-1, 1]) {
    const bx = s < 0 ? -20 : gateCx + archW * 0.48;
    const bw = s < 0 ? (gateCx - archW * 0.48 + 20) : (w - (gateCx + archW * 0.48) + 20);
    rect(g, bx, groundY - archH * 1.25, bw, archH * 1.32, { fill: '#cbb694', lw, r: 2 });
    // Battlements
    const merlons = 4;
    for (let m = 0; m < merlons; m++) {
      const mx = bx + (bw / merlons) * m + lw;
      rect(g, mx, groundY - archH * 1.38, (bw / merlons) * 0.62, archH * 0.14, { fill: '#d6c2a0', lw, r: 2 });
    }
    // Ashlar stone joint lines
    for (let row = 1; row <= 4; row++) {
      const ry = groundY - archH * (1.2 - row * 0.24);
      line(g, [[bx, ry], [bx + bw, ry]], { lw: lw * 0.55, ink: '#9e8869' });
    }
  }

  // Gate arch lintel & masonry voussoirs
  rect(g, gateCx - archW * 0.52, groundY - archH * 1.18, archW * 1.04, archH * 0.22, { fill: '#d8c4a2', lw, r: 3 });
  rect(g, gateCx - archW * 0.48, groundY - archH * 0.96, archW * 0.96, archH * 0.96, { fill: '#f0af5b', lw, r: 2 });
  drawRomanGateLeaves2D(g, gateCx, groundY, archW * 0.94, archH * 0.94, closeFrac, {
    t,
    lw,
    boltDropFrac: state.boltDropFrac ?? 0,
    showBolt: false,
  });

  // Flanking bronze torches
  drawTorchFlame2D(g, gateCx - archW * 0.56, groundY - archH * 0.54, w * 0.055, t);
  drawTorchFlame2D(g, gateCx + archW * 0.56, groundY - archH * 0.54, w * 0.055, t + 1.1);

  // Perspective cobbled avenue slabs & travertine gutter blocks across full foreground
  const scrollY = (opts.scrollPx ?? 0) % (h * 0.08);
  for (let i = 0; i < 12; i++) {
    const ry = groundY + ((i * h * 0.055 + scrollY) % (h - groundY + h * 0.04));
    const u = clamp((ry - groundY) / (h - groundY), 0, 1);
    const halfSpan = lerp(archW * 0.44, w * 0.54, u);
    line(g, [[gateCx - halfSpan, ry], [gateCx + halfSpan, ry]], {
      lw: lw * lerp(0.5, 1.05, u),
      ink: alpha('#594431', 0.42),
    });
    if (i % 2 === 0) {
      line(g, [[gateCx - halfSpan * 0.5, ry], [gateCx - halfSpan * 0.56, Math.min(h, ry + h * 0.055)]], { lw: lw * 0.45, ink: alpha('#594431', 0.30) });
      line(g, [[gateCx + halfSpan * 0.5, ry], [gateCx + halfSpan * 0.56, Math.min(h, ry + h * 0.055)]], { lw: lw * 0.45, ink: alpha('#594431', 0.30) });
    }
  }
  // Framing Roman cypress bushes at bastion wall base + subtle road pebbles
  bush(g, w * 0.08, groundY + h * 0.015, w * 0.14, PAL.grassDark, 3);
  bush(g, w * 0.92, groundY + h * 0.015, w * 0.14, PAL.grassDark, 7);
  pebble(g, w * 0.18, groundY + h * 0.11, w * 0.025, 1);
  pebble(g, w * 0.81, groundY + h * 0.15, w * 0.022, 2);
  pebble(g, w * 0.28, groundY + h * 0.25, w * 0.028, 3);
}

export function drawRomanGateWinch2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const closeFrac = clamp(state.gateCloseFrac ?? 0.45, 0, 1);
  const winchRad = state.winchAngleRad ?? closeFrac * Math.PI * 5.0;
  const lw = Math.max(2.4, w * 0.003);

  // Dark stone interior tower backdrop with warm dusk arch slot
  rect(g, -20, -20, w + 40, h + 40, { fill: '#473936', lw: 0, r: 0 });
  const winGlow = g.createRadialGradient(w * 0.5, h * 0.46, w * 0.05, w * 0.5, h * 0.46, w * 0.65);
  winGlow.addColorStop(0, '#c87344');
  winGlow.addColorStop(1, '#3b2e2c');
  g.fillStyle = winGlow;
  g.fillRect(0, 0, w, h);

  // Arched twilight slot showing distant gate sunset
  shape(
    g,
    (c) => {
      c.moveTo(w * 0.24, h * 0.64);
      c.lineTo(w * 0.24, h * 0.36);
      c.arc(w * 0.5, h * 0.36, w * 0.26, Math.PI, 0);
      c.lineTo(w * 0.76, h * 0.64);
      c.closePath();
    },
    { fill: '#f2a957', lw: lw * 1.1 }
  );

  // Below arch: converging twin oak door leaves viewed from above/inside
  drawRomanGateLeaves2D(g, w * 0.5, h * 0.68, w * 0.68, h * 0.24, closeFrac, {
    t,
    lw,
    interiorSide: true,
    boltDropFrac: state.boltDropFrac ?? 0,
  });

  // Heavy overhead oak support beams
  rect(g, -10, h * 0.18, w + 20, h * 0.048, { fill: '#6c4125', lw, r: 3 });
  rect(g, w * 0.10, h * 0.14, w * 0.06, h * 0.44, { fill: '#5d371e', lw, r: 3 });
  rect(g, w * 0.84, h * 0.14, w * 0.06, h * 0.44, { fill: '#5d371e', lw, r: 3 });

  // Vertical chains & ropes unwinding down toward gate leaves
  const ropeOffset = (closeFrac * h * 0.14) % (h * 0.04);
  for (const rx of [w * 0.30, w * 0.70]) {
    tube(g, [[rx, h * 0.28], [rx, h * 0.60]], w * 0.016, '#a38258', lw * 0.8);
    for (let k = 0; k < 6; k++) {
      const ly = h * 0.30 + k * h * 0.048 + ropeOffset;
      if (ly < h * 0.58) {
        ellipse(g, rx, ly, w * 0.014, h * 0.006, { fill: '#594332', lw: lw * 0.5 });
      }
    }
  }

  // Central spoked Roman wooden winch drum rotating with `winchRad`
  const wx = w * 0.5, wy = h * 0.265, wr = w * 0.14;
  rect(g, w * 0.26, wy - wr * 0.36, w * 0.48, wr * 0.72, { fill: '#7d4d2c', lw, r: 6 });
  for (let coil = -4; coil <= 4; coil++) {
    const cx = wx + coil * w * 0.04;
    line(g, [[cx, wy - wr * 0.36], [cx, wy + wr * 0.36]], { lw: lw * 1.4, ink: PAL.rope });
  }
  // Spoked side wheel
  g.save();
  g.translate(wx, wy);
  g.rotate(winchRad);
  circ(g, 0, 0, wr * 0.92, { fill: '#945b35', lw: lw * 1.1 });
  for (let sp = 0; sp < 4; sp++) {
    const a = (sp * Math.PI) / 4;
    line(g, [[-Math.cos(a) * wr, -Math.sin(a) * wr], [Math.cos(a) * wr, Math.sin(a) * wr]], {
      lw: lw * 2.0,
      ink: '#633b20',
    });
  }
  circ(g, 0, 0, wr * 0.22, { fill: '#51494b', lw });
  g.restore();

  drawTorchFlame2D(g, w * 0.15, h * 0.42, w * 0.055, t);
  drawTorchFlame2D(g, w * 0.85, h * 0.42, w * 0.055, t + 0.7);
}

export function drawRomanCobbleAlley2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const scrollX = opts.scrollX ?? 0;
  const lw = Math.max(2.2, w * 0.0028);

  drawDuskSkyAndWallsBackdrop(g, w, h, { t, horizonYFrac: 0.43, sunXFrac: 0.56 });

  // Stone insula alley facades framing side corridor in perspective
  shape(
    g,
    (c) => {
      c.moveTo(-20, h * 0.06);
      c.lineTo(w * 0.24, h * 0.32);
      c.lineTo(w * 0.24, h * 0.62);
      c.lineTo(-20, h * 0.72);
      c.closePath();
    },
    { fill: '#c8b08d', lw }
  );
  shape(
    g,
    (c) => {
      c.moveTo(w + 20, h * 0.10);
      c.lineTo(w * 0.78, h * 0.34);
      c.lineTo(w * 0.78, h * 0.62);
      c.lineTo(w + 20, h * 0.70);
      c.closePath();
    },
    { fill: '#b79e7c', lw }
  );

  // Foreground wet Roman cobble street floor
  const floorY = (opts.floorYFrac ?? 0.56) * h;
  const flGrad = g.createLinearGradient(0, floorY, 0, h);
  flGrad.addColorStop(0, '#9d876d');
  flGrad.addColorStop(1, '#6f5c49');
  g.fillStyle = flGrad;
  g.fillRect(-30, floorY, w + 60, h - floorY + 30);
  line(g, [[-30, floorY], [w + 30, floorY]], { lw, ink: OUT });

  // Scrolling cobbles + raised trip curbstone!
  const stepX = w * 0.16;
  const shift = ((scrollX % stepX) + stepX) % stepX;
  for (let row = 0; row < 5; row++) {
    const ry = floorY + (row + 0.5) * (h * 0.072);
    for (let col = -1; col < 8; col++) {
      const cx = col * stepX - shift + (row % 2) * stepX * 0.5;
      ellipse(g, cx, ry, w * 0.068, h * 0.022, {
        fill: (row + col) % 2 === 0 ? '#8c765d' : '#7b6650',
        lw: lw * 0.65,
      });
    }
  }

  // Distinct raised chipped limestone curb block aligned squarely to running sandal level
  if (opts.curbXFrac !== undefined) {
    const cbx = opts.curbXFrac * w;
    const cby = floorY + h * 0.036;
    rect(g, cbx - w * 0.085, cby - h * 0.024, w * 0.17, h * 0.044, { fill: '#e0ccb0', lw: lw * 1.15, r: 4 });
    line(g, [[cbx - w * 0.065, cby - h * 0.012], [cbx + w * 0.055, cby - h * 0.012]], { lw: lw * 0.6, ink: '#fff5de' });
  }

  // Warm dusk puddle reflecting gate torch glow
  ellipse(g, w * 0.64, floorY + h * 0.18, w * 0.18, h * 0.025, {
    fill: alpha('#e59555', 0.45),
    lw: lw * 0.5,
  });

  drawTorchFlame2D(g, w * 0.14, h * 0.42, w * 0.048, t);
  drawTorchFlame2D(g, w * 0.87, h * 0.43, w * 0.046, t + 1.3);
}

export function drawStoneDrainGrate2D(g, x, y, gw, gh, opts = {}) {
  const lw = opts.lw ?? Math.max(2.2, gw * 0.015);
  g.save();
  g.translate(x, y);

  // Carved stone drain lip collar
  rect(g, -gw * 0.56, -gh * 0.62, gw * 1.12, gh * 1.24, { fill: '#b8a386', lw, r: 6 });
  // Deep dark gutter cavity
  rect(g, -gw * 0.44, -gh * 0.46, gw * 0.88, gh * 0.92, { fill: '#1b1514', lw: lw * 0.9, r: 4 });

  // Vertical iron grate bars
  const bars = opts.bars ?? 5;
  for (let b = 0; b < bars; b++) {
    const bx = -gw * 0.34 + (b / Math.max(1, bars - 1)) * (gw * 0.68);
    rect(g, bx - gw * 0.032, -gh * 0.44, gw * 0.064, gh * 0.88, { fill: '#575155', lw: lw * 0.72, r: 2 });
    line(g, [[bx - gw * 0.01, -gh * 0.38], [bx - gw * 0.01, gh * 0.38]], { lw: lw * 0.35, ink: '#8b8287' });
  }
  // Water trickle highlight at rim
  ellipse(g, -gw * 0.14, gh * 0.55, gw * 0.38, gh * 0.11, { fill: alpha('#4d7e8d', 0.38), lw: lw * 0.4 });
  g.restore();
}

export function drawRomanGuardThreshold2D(g, state = {}, opts = {}) {
  const w = W(), h = H();
  const t = state.globalT ?? 0;
  const closeFrac = clamp(state.gateCloseFrac ?? 0.65, 0, 1);
  const floorY = (opts.floorYFrac ?? 0.58) * h;
  const lw = Math.max(2.2, w * 0.0028);

  // Warm interior stone gatehouse backdrop
  const wallGrad = g.createLinearGradient(0, 0, 0, floorY);
  wallGrad.addColorStop(0, '#5a453b');
  wallGrad.addColorStop(1, '#8c6d56');
  g.fillStyle = wallGrad;
  g.fillRect(-20, -20, w + 40, floorY + 20);

  // Masonry joints
  for (let r = 1; r <= 5; r++) {
    const y = (r / 6) * floorY;
    line(g, [[-20, y], [w + 20, y]], { lw: lw * 0.55, ink: alpha(OUT, 0.32) });
  }

  // Flagstone threshold floor with perspective ashlar slab joints
  const flGrad = g.createLinearGradient(0, floorY, 0, h);
  flGrad.addColorStop(0, '#a89278');
  flGrad.addColorStop(1, '#786552');
  g.fillStyle = flGrad;
  g.fillRect(-30, floorY, w + 60, h - floorY + 30);
  line(g, [[-30, floorY], [w + 30, floorY]], { lw, ink: OUT });
  for (let row = 1; row <= 6; row++) {
    const ry = floorY + (row / 6.2) * (h - floorY);
    line(g, [[-30, ry], [w + 30, ry]], { lw: lw * 0.55, ink: alpha('#4d3c2e', 0.36) });
    for (let c = 0; c < 4; c++) {
      const cx = (c / 3.5 + (row % 2) * 0.14) * w;
      line(g, [[cx, ry - (h - floorY) / 6.2], [cx + (cx - w * 0.5) * 0.12, ry]], { lw: lw * 0.48, ink: alpha('#4d3c2e', 0.28) });
    }
  }

  // Central gate opening & massive closing oak leaves (viewed from inside city gate!)
  const gateCx = (opts.gateCxFrac ?? 0.50) * w;
  const archW = (opts.archWFrac ?? 0.54) * w;
  const archH = (opts.archHFrac ?? 0.34) * h;
  rect(g, gateCx - archW * 0.54, floorY - archH * 1.12, archW * 1.08, archH * 1.12, { fill: '#b89f80', lw, r: 4 });
  rect(g, gateCx - archW * 0.48, floorY - archH * 0.96, archW * 0.96, archH * 0.96, { fill: '#efa151', lw, r: 2 });

  drawRomanGateLeaves2D(g, gateCx, floorY, archW * 0.94, archH * 0.94, closeFrac, {
    t,
    lw,
    interiorSide: true,
    boltDropFrac: state.boltDropFrac ?? 0,
  });

  // Storm drain grate near front-right threshold stone
  if (opts.showDrain !== false) {
    drawStoneDrainGrate2D(
      g,
      (opts.drainXFrac ?? 0.72) * w,
      (opts.drainYFrac ?? 0.67) * h,
      (opts.drainWFrac ?? 0.24) * w,
      (opts.drainHFrac ?? 0.075) * h,
      { lw }
    );
  }

  // Twin guard braziers / sconces
  drawTorchFlame2D(g, w * 0.13, floorY - archH * 0.48, w * 0.052, t);
  drawTorchFlame2D(g, w * 0.87, floorY - archH * 0.48, w * 0.052, t + 0.9);
}

// Sealed / Pinned / Unrolled Legible Roman Scroll Prop
export function drawSealedRomanScroll2D(g, x, y, s, opts = {}) {
  const mode = opts.mode || 'rolled_sealed'; // 'rolled_sealed' | 'pinned_under_sandal' | 'breaking_seal' | 'unrolled_message'
  const rot = opts.rot ?? 0;
  const lw = opts.lw ?? Math.max(2.0, s * 0.025);
  const mud = clamp(opts.mudAmount ?? 0, 0, 1);

  g.save();
  g.translate(x, y);
  g.rotate(rot);

  if (mode === 'unrolled_message') {
    const pw = s * 1.05;
    const ph = s * 1.38;
    // Wooden scroll spindles top & bottom
    rect(g, -pw * 0.58, -ph * 0.54, pw * 1.16, ph * 0.075, { fill: PAL.wood, lw, r: 6 });
    rect(g, -pw * 0.58, ph * 0.465, pw * 1.16, ph * 0.075, { fill: PAL.wood, lw, r: 6 });
    for (const endX of [-pw * 0.58, pw * 0.58]) {
      circ(g, endX, -ph * 0.502, ph * 0.046, { fill: PAL.gold, lw: lw * 0.8 });
      circ(g, endX, ph * 0.502, ph * 0.046, { fill: PAL.gold, lw: lw * 0.8 });
    }
    // Crisp creamy Roman parchment face
    rect(g, -pw * 0.5, -ph * 0.46, pw, ph * 0.92, {
      fill: '#f7ebd0',
      lw: lw * 1.05,
      r: 4,
      inner: (c) => {
        rect(c, -pw * 0.46, ph * 0.34, pw * 0.92, ph * 0.12, { fill: alpha('#d8b989', 0.32), lw: 0 });
      },
    });
    // Optional mud smudge corner for state continuity after drain stomp!
    if (mud > 0.05) {
      ellipse(g, pw * 0.34, ph * 0.34, pw * 0.11, ph * 0.055, { fill: alpha('#6e4e35', 0.42 * mud), lw: 0 });
    }
    // Snapped wax seal halves dangling on right margin
    circ(g, pw * 0.37, -ph * 0.34, s * 0.075, { fill: '#b52824', lw: lw * 0.8 });
    line(g, [[pw * 0.32, -ph * 0.39], [pw * 0.42, -ph * 0.29]], { lw: lw * 0.9, ink: '#51110f' });

    // BOLD, HIGH-CONTRAST 4 WORDS — readable cleanly on phone Vertical 9:16!
    const words = Array.isArray(opts.lines) ? opts.lines : ['KEEP', 'THE GATE', 'OPEN'];
    g.fillStyle = '#241712';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    const fontBase = s * 0.195;
    g.font = `900 ${Math.round(fontBase)}px ${FONT_CAP}`;
    g.fillText(words[0] || 'KEEP', 0, -ph * 0.22);
    g.font = `900 ${Math.round(fontBase * 0.88)}px ${FONT_CAP}`;
    g.fillText(words[1] || 'THE GATE', 0, ph * 0.01);
    g.fillStyle = '#a8221e';
    g.font = `900 ${Math.round(fontBase * 1.12)}px ${FONT_CAP}`;
    g.fillText(words[2] || 'OPEN', 0, ph * 0.25);

    // Engraved double rule underline
    line(g, [[-pw * 0.34, ph * 0.37], [pw * 0.34, ph * 0.37]], { lw: lw * 0.75, ink: '#a8221e' });
    g.restore();
    return;
  }

  // Motion smear streak if airborne
  if (opts.airborneStreak) {
    line(g, [[-s * 1.15, -s * 0.12], [-s * 0.35, -s * 0.03]], { lw: lw * 1.6, ink: alpha('#fff0c9', 0.45) });
    line(g, [[-s * 0.95, s * 0.14], [-s * 0.30, s * 0.05]], { lw: lw * 1.1, ink: alpha('#fff0c9', 0.35) });
  }

  const rw = s * 0.92;
  const rh = s * 0.26;
  // Rolled wooden ends
  rect(g, -rw * 0.56, -rh * 0.25, rw * 1.12, rh * 0.5, { fill: PAL.wood, lw: lw * 0.85, r: 4 });
  // Parchment cylinder
  rect(g, -rw * 0.5, -rh * 0.5, rw, rh, { fill: '#f6ead0', lw, r: rh * 0.22 });
  // Inner spiral edge
  ellipse(g, -rw * 0.48, 0, rh * 0.22, rh * 0.46, { fill: '#dfd0ad', lw: lw * 0.8 });
  ellipse(g, rw * 0.48, 0, rh * 0.22, rh * 0.46, { fill: '#dfd0ad', lw: lw * 0.8 });

  if (mud > 0.05) {
    ellipse(g, rw * 0.2, rh * 0.18, rw * 0.18, rh * 0.26, { fill: alpha('#6e4e35', 0.48 * mud), lw: 0 });
  }

  // Crimson binding ribbon + wax seal
  rect(g, -rw * 0.05, -rh * 0.52, rw * 0.10, rh * 1.04, { fill: '#9f2320', lw: lw * 0.7, r: 1 });
  const crack = clamp(opts.sealCrackFrac ?? 0, 0, 1);
  if (crack > 0.05) {
    const sep = crack * rh * 0.35;
    circ(g, -sep, -sep * 0.4, rh * 0.42, { fill: '#c22e29', lw: lw * 0.8 });
    circ(g, sep, sep * 0.4, rh * 0.40, { fill: '#a92521', lw: lw * 0.8 });
  } else {
    circ(g, 0, 0, rh * 0.46, { fill: '#c22e29', lw: lw * 0.85 });
    circ(g, 0, 0, rh * 0.28, { fill: '#e04842', lw: lw * 0.5 });
  }
  g.restore();
}

// Tight macro Squire-style Roman leather sandal sole + ankle straps (for stumble curb trip or drain stomp pin)
export function drawRomanSandalMacro2D(g, x, y, s, opts = {}) {
  const rot = opts.rot ?? 0;
  const lw = opts.lw ?? Math.max(2.4, s * 0.022);
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  // Lower calf extending into Roman tunic hem when desired
  const shinTop = opts.tallShin ? -s * 1.15 : -s * 0.65;
  const shinH = opts.tallShin ? s * 1.02 : s * 0.52;
  rect(g, -s * 0.145, shinTop, s * 0.29, shinH, { fill: PAL.skin, lw, r: s * 0.04 });
  if (opts.showTunicHem) {
    rect(g, -s * 0.24, shinTop - s * 0.22, s * 0.48, s * 0.36, { fill: PAL.red, lw: lw * 1.05, r: s * 0.04 });
    line(g, [[-s * 0.12, shinTop - s * 0.18], [-s * 0.12, shinTop + s * 0.14]], { lw: lw * 0.6, ink: alpha(OUT, 0.45) });
    line(g, [[s * 0.08, shinTop - s * 0.18], [s * 0.08, shinTop + s * 0.14]], { lw: lw * 0.6, ink: alpha(OUT, 0.45) });
  }
  // Criss-cross caliga leather straps on ankle
  tube(g, [[-s * 0.15, -s * 0.42], [s * 0.15, -s * 0.26]], s * 0.045, PAL.leather, lw * 0.75);
  tube(g, [[s * 0.15, -s * 0.42], [-s * 0.15, -s * 0.26]], s * 0.045, PAL.leather, lw * 0.75);
  // Bare toes & leather sandal upper
  shape(
    g,
    (c) => {
      c.moveTo(-s * 0.22, -s * 0.02);
      c.quadraticCurveTo(0, -s * 0.16, s * 0.32, -s * 0.06);
      c.quadraticCurveTo(s * 0.42, -s * 0.01, s * 0.38, s * 0.06);
      c.lineTo(-s * 0.26, s * 0.06);
      c.closePath();
    },
    { fill: '#8a522c', lw }
  );
  // Hobnail leather sole pad
  rect(g, -s * 0.28, s * 0.02, s * 0.69, s * 0.095, { fill: '#573219', lw: lw * 0.95, r: s * 0.03 });
  for (let n = 0; n < 5; n++) {
    circ(g, -s * 0.20 + n * s * 0.13, s * 0.09, s * 0.02, { fill: '#a69fa3', lw: lw * 0.45 });
  }
  g.restore();
}
