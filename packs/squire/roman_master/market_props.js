// market_props.js — Original Squire 2D Procedural Market Cart, Brake Peg, Hemp Rope, Bakery Oven & Roman Loaf Props for KH-03.0.R2.
// Built strictly with Production packs/squire/ink.js primitives & locked OUT (#392a21) line discipline. Zero 3D.
import { clamp, lerp, alpha } from '../ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, polyS, line, tube, darker } from '../ink.js';
import { dustPuff } from '../army.js';

export function drawRomanLoaf2D(g, x, y, s, opts = {}) {
  const rot = opts.rot ?? 0;
  const lw = opts.lw ?? Math.max(2.0, s * 0.06);
  const squish = clamp(opts.squishFrac ?? 0, 0, 0.35);
  g.save();
  g.translate(x, y);
  g.rotate(rot);
  g.scale(1.0 + squish * 0.4, 1.0 - squish);
  if (opts.trail) {
    line(g, [[-s * 1.15, -s * 0.15], [-s * 0.45, -s * 0.04]], { lw: lw * 1.1, ink: alpha('#fff2d4', 0.55) });
    line(g, [[-s * 0.95, s * 0.18], [-s * 0.42, s * 0.06]], { lw: lw * 0.85, ink: alpha('#fff2d4', 0.42) });
  }
  // Classic segmented Roman panis quadratus bread loaf
  ellipse(g, 0, 0, s * 0.55, s * 0.34, {
    fill: '#d98f3f',
    lw,
    inner: (c) => {
      ellipse(c, 0, -s * 0.07, s * 0.48, s * 0.22, { fill: '#ebb161', lw: 0 });
      rect(c, -s * 0.65, s * 0.10, s * 1.3, s * 0.35, { fill: alpha('#7c461a', 0.32), lw: 0 });
    },
  });
  // Scored cross wedges + golden top crust highlight
  for (const ang of [-0.55, 0.0, 0.55]) {
    line(g, [[Math.sin(ang) * s * 0.45, -s * 0.28], [Math.sin(ang) * s * 0.2, s * 0.18]], {
      lw: lw * 0.65,
      ink: '#8b4e1e',
    });
  }
  circ(g, -s * 0.16, -s * 0.12, s * 0.065, { fill: '#f6d697', lw: 0 });
  g.restore();
}

export function drawSpokedWheel2D(g, x, y, r, angleRad = 0, lw = 3) {
  g.save();
  g.translate(x, y);
  g.rotate(angleRad);
  circ(g, 0, 0, r, { fill: '#4e484a', lw: lw * 1.1 });
  circ(g, 0, 0, r * 0.85, { fill: '#915c34', lw: lw * 0.95 });
  circ(g, 0, 0, r * 0.66, { fill: '#6c4122', lw: lw * 0.8 });
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3;
    line(g, [[0, 0], [Math.cos(a) * r * 0.72, Math.sin(a) * r * 0.72]], {
      lw: Math.max(2.5, r * 0.14),
      ink: '#b27846',
    });
    line(g, [[0, 0], [Math.cos(a) * r * 0.72, Math.sin(a) * r * 0.72]], {
      lw: lw * 0.55,
      ink: OUT,
    });
  }
  circ(g, 0, 0, r * 0.24, { fill: PAL.bronze, lw: lw * 0.9 });
  circ(g, 0, 0, r * 0.08, { fill: OUT, lw: 0 });
  g.restore();
}

export function drawBrakePeg2D(g, x, y, s, opts = {}) {
  const crack = clamp(opts.crackFrac ?? 0, 0, 1);
  const snapped = !!opts.snapped || crack >= 0.95;
  const lw = opts.lw ?? Math.max(2.2, s * 0.032);
  g.save();
  g.translate(x, y);

  // Heavy wheel rim & cobble chock context behind peg
  drawSpokedWheel2D(g, -s * 0.08, -s * 0.34, s * 0.44, opts.wheelAngleRad ?? 0, lw);
  // Ashlar wedge block below hub
  polyS(g, [[-s * 0.32, s * 0.10], [s * 0.36, s * 0.10], [s * 0.28, -s * 0.08], [-s * 0.16, s * 0.04]], {
    fill: '#8f7d68',
    lw: lw * 0.9,
  });

  if (!snapped) {
    const rot = lerp(0.18, 0.36, crack);
    g.save();
    g.rotate(rot);
    rect(g, -s * 0.065, -s * 0.22, s * 0.13, s * 0.36, { fill: '#b57b42', lw, r: 3 });
    if (crack > 0.1) {
      // Zigzag wood stress crack line across middle
      line(g, [[-s * 0.06, -s * 0.04], [0, -s * 0.01], [-s * 0.03, s * 0.03], [s * 0.06, s * 0.05]], {
        lw: lw * 0.9,
        ink: '#2d1c12',
      });
    }
    g.restore();
  } else {
    // Two snapped peg halves + flying splinters!
    g.save();
    g.translate(-s * 0.05, s * 0.02);
    g.rotate(0.55);
    rect(g, -s * 0.06, -s * 0.12, s * 0.12, s * 0.18, { fill: '#a66e39', lw, r: 2 });
    g.restore();

    const sep = clamp(opts.flySep ?? 0.5, 0, 1);
    g.save();
    g.translate(s * (0.14 + sep * 0.28), -s * (0.12 + sep * 0.18));
    g.rotate(-0.8 - sep * 1.4);
    rect(g, -s * 0.055, -s * 0.11, s * 0.11, s * 0.18, { fill: '#c68a4c', lw, r: 2 });
    g.restore();

    // Impact crack burst lines
    for (const [ax, ay] of [[-0.25, -0.30], [0.22, -0.35], [0.34, -0.10]]) {
      line(g, [[s * ax * 0.4, s * ay * 0.4], [s * ax * (0.8 + sep * 0.5), s * ay * (0.8 + sep * 0.5)]], {
        lw: lw * 0.85,
        ink: '#fff1d0',
      });
    }
  }
  g.restore();
}

export function drawAmphoraJar2D(g, x, y, s, lw = 2.2) {
  g.save();
  g.translate(x, y);
  shape(
    g,
    (c) => {
      c.moveTo(-s * 0.16, -s * 0.55);
      c.lineTo(s * 0.16, -s * 0.55);
      c.quadraticCurveTo(s * 0.12, -s * 0.35, s * 0.34, -s * 0.12);
      c.quadraticCurveTo(s * 0.36, s * 0.30, 0, s * 0.50);
      c.quadraticCurveTo(-s * 0.36, s * 0.30, -s * 0.34, -s * 0.12);
      c.quadraticCurveTo(-s * 0.12, -s * 0.35, -s * 0.16, -s * 0.55);
      c.closePath();
    },
    { fill: '#c46c44', lw }
  );
  // Twin curved Roman amphora handles
  tube(g, [[-s * 0.13, -s * 0.48], [-s * 0.34, -s * 0.34], [-s * 0.28, -s * 0.14]], s * 0.05, '#a85634', lw * 0.7);
  tube(g, [[s * 0.13, -s * 0.48], [s * 0.34, -s * 0.34], [s * 0.28, -s * 0.14]], s * 0.05, '#a85634', lw * 0.7);
  g.restore();
}

// Complete Squire 2D Roman cargo cart (facing rightwards downhill by default, flip=-1 flips facing)
export function drawRomanCart2D(g, x, y, wCart, opts = {}) {
  const wheelR = wCart * 0.175;
  const lw = opts.lw ?? Math.max(2.2, wCart * 0.012);
  const jiggle = opts.jiggleY ?? 0;
  const tiltRad = opts.tiltRad ?? 0;
  const wAng = opts.wheelAngleRad ?? 0;

  g.save();
  g.translate(x, y);
  if (opts.flip) g.scale(-1, 1);
  g.rotate(tiltRad);

  // Soft ground shadow
  ellipse(g, 0, wheelR * 0.12, wCart * 0.56, wheelR * 0.26, { fill: alpha('#241811', 0.25), lw: 0 });

  // Rear axle towing hitch ring at x = -0.49*wCart, y = -wheelR
  circ(g, -wCart * 0.50, -wheelR * 1.02, wheelR * 0.20, { fill: '#4f484b', lw: lw * 0.85 });

  // Slatted wooden cargo bed + amphorae/grain crates rattling with jiggle
  const bedY = -wheelR * 1.32 + jiggle;
  rect(g, -wCart * 0.46, bedY - wCart * 0.24, wCart * 0.90, wCart * 0.12, { fill: '#88532c', lw, r: 4 });
  drawAmphoraJar2D(g, -wCart * 0.18, bedY - wCart * 0.30, wCart * 0.24, lw * 0.85);
  drawAmphoraJar2D(g, wCart * 0.04, bedY - wCart * 0.29, wCart * 0.23, lw * 0.85);
  rect(g, wCart * 0.15, bedY - wCart * 0.34, wCart * 0.24, wCart * 0.18, { fill: '#c8a873', lw: lw * 0.85, r: 4 });

  // Outer cart oak bed rail & red Roman trim panel
  rect(g, -wCart * 0.48, bedY - wCart * 0.18, wCart * 0.94, wCart * 0.18, { fill: '#9f6537', lw, r: 4 });
  rect(g, -wCart * 0.44, bedY - wCart * 0.14, wCart * 0.86, wCart * 0.065, { fill: PAL.red, lw: lw * 0.7, r: 2 });
  // Vertical oak stakes along side
  for (let s = -2; s <= 2; s++) {
    rect(g, s * wCart * 0.19 - wCart * 0.02, bedY - wCart * 0.29, wCart * 0.04, wCart * 0.29, { fill: '#754624', lw: lw * 0.75, r: 2 });
  }
  // Front pull shafts jutting forward
  tube(g, [[wCart * 0.42, bedY - wCart * 0.05], [wCart * 0.62, bedY + wCart * 0.03]], wCart * 0.03, '#7b4b28', lw * 0.9);

  // Twin spoked wheels rotating strictly proportional to distance!
  drawSpokedWheel2D(g, -wCart * 0.31, -wheelR, wheelR, wAng, lw);
  drawSpokedWheel2D(g, wCart * 0.29, -wheelR, wheelR, wAng, lw);

  if (opts.skidDust > 0.05) {
    dustPuff(g, wCart * 0.22, 0, wCart * 0.22, opts.skidDust);
    dustPuff(g, -wCart * 0.32, 0, wCart * 0.18, (opts.skidDust + 0.35) % 1);
  }
  g.restore();

  // Compute exact rear axle rope attach world coordinate for causal rope linkage
  const rearLocalX = -wCart * 0.50 * (opts.flip ? -1 : 1);
  const rearLocalY = -wheelR * 1.02;
  const c = Math.cos(tiltRad);
  const sn = Math.sin(tiltRad);
  return {
    rearAxleWorld: [x + rearLocalX * c - rearLocalY * sn, y + rearLocalX * sn + rearLocalY * c],
    frontBumperWorld: [x + wCart * 0.58 * (opts.flip ? -1 : 1), y - wheelR * 0.8],
    wheelR,
  };
}

export function drawStoneBollard2D(g, x, y, s, opts = {}) {
  const lw = opts.lw ?? Math.max(2.2, s * 0.03);
  g.save();
  g.translate(x, y);
  ellipse(g, 0, 0, s * 0.38, s * 0.10, { fill: alpha('#241811', 0.24), lw: 0 });
  // Carved Roman granite mooring bollard
  rect(g, -s * 0.24, -s * 0.72, s * 0.48, s * 0.72, { fill: '#b5a592', lw, r: 6 });
  ellipse(g, 0, -s * 0.72, s * 0.28, s * 0.12, { fill: '#cec0ae', lw });
  line(g, [[-s * 0.20, -s * 0.42], [s * 0.20, -s * 0.42]], { lw: lw * 0.65, ink: '#7e6f5e' });
  // Wound rope coils around waist if looped
  const loops = opts.ropeLoops ?? 0;
  for (let i = 0; i < loops; i++) {
    ellipse(g, 0, -s * (0.48 + i * 0.075), s * 0.275, s * 0.062, { fill: '#c8a66e', lw: lw * 0.85 });
  }
  g.restore();
  return { loopWorld: [x, y - s * 0.48] };
}

export function drawRopePath2D(g, p0, p1, opts = {}) {
  const lw = opts.lw ?? 4.5;
  const taut = clamp(opts.tautFrac ?? 0, 0, 1);
  const vib = opts.vibrateAmp ?? 0;
  const mx = (p0[0] + p1[0]) * 0.5;
  const my = (p0[1] + p1[1]) * 0.5 + (1 - taut) * (opts.sagPx ?? 65) + vib;
  shape(
    g,
    (c) => {
      c.moveTo(p0[0], p0[1]);
      c.quadraticCurveTo(mx, my, p1[0], p1[1]);
    },
    { fill: null, lw: lw + 3.2, ink: OUT }
  );
  shape(
    g,
    (c) => {
      c.moveTo(p0[0], p0[1]);
      c.quadraticCurveTo(mx, my, p1[0], p1[1]);
    },
    { fill: null, lw, ink: '#c9a66b' }
  );
}

export function drawBakeryOvenAndTray2D(g, x, y, s, opts = {}) {
  const t = opts.t ?? 0;
  const lw = opts.lw ?? Math.max(2.2, s * 0.015);
  const trayShake = opts.trayShakePx ?? 0;
  const loavesOnTray = opts.loavesOnTray ?? 3;

  g.save();
  g.translate(x, y);

  // Masonry brick Roman oven dome (fornax)
  ellipse(g, 0, 0, s * 0.52, s * 0.10, { fill: alpha('#241811', 0.25), lw: 0 });
  rect(g, -s * 0.46, -s * 0.54, s * 0.92, s * 0.54, { fill: '#a96244', lw, r: 8 });
  // Chimney flue
  rect(g, s * 0.14, -s * 1.18, s * 0.18, s * 0.48, { fill: '#915035', lw, r: 4 });
  shape(
    g,
    (c) => {
      c.moveTo(-s * 0.46, -s * 0.54);
      c.quadraticCurveTo(0, -s * 1.06, s * 0.46, -s * 0.54);
      c.closePath();
    },
    { fill: '#b86c4c', lw }
  );

  // Glowing oven hearth opening with amber embers
  const glow = g.createRadialGradient(0, -s * 0.34, s * 0.05, 0, -s * 0.34, s * 0.45);
  glow.addColorStop(0, alpha('#ffca57', 0.65));
  glow.addColorStop(1, alpha('#f06423', 0));
  g.fillStyle = glow;
  g.beginPath();
  g.arc(0, -s * 0.34, s * 0.45, 0, Math.PI * 2);
  g.fill();

  shape(
    g,
    (c) => {
      c.moveTo(-s * 0.22, -s * 0.18);
      c.lineTo(-s * 0.22, -s * 0.42);
      c.arc(0, -s * 0.42, s * 0.22, Math.PI, 0);
      c.lineTo(s * 0.22, -s * 0.18);
      c.closePath();
    },
    { fill: '#351b14', lw }
  );
  // Dancing hearth flames
  const fl = Math.sin(t * 14.0) * s * 0.025;
  for (let i = -1; i <= 1; i++) {
    shape(
      g,
      (c) => {
        c.moveTo(i * s * 0.09 - s * 0.05, -s * 0.19);
        c.quadraticCurveTo(i * s * 0.09 + fl, -s * 0.36, i * s * 0.09 + s * 0.05, -s * 0.19);
        c.closePath();
      },
      { fill: i === 0 ? '#ffe680' : '#f5842c', lw: 0 }
    );
  }

  // Side timber bread table + shaking baker tray holding golden panis quadratus loaves
  const tx = -s * 0.68;
  rect(g, tx - s * 0.24, -s * 0.34, s * 0.48, s * 0.34, { fill: '#7e4e2d', lw, r: 3 });
  rect(g, tx - s * 0.28 + trayShake, -s * 0.40, s * 0.56, s * 0.075, { fill: '#c69355', lw, r: 4 });
  for (let l = 0; l < loavesOnTray; l++) {
    const lx = tx - s * 0.16 + l * s * 0.16 + trayShake;
    drawRomanLoaf2D(g, lx, -s * 0.445, s * 0.135, { lw: lw * 0.75 });
  }
  g.restore();
  return { trayTopWorld: [x - s * 0.68, y - s * 0.45] };
}
