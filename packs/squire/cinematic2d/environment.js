// environment.js (packs/squire/cinematic2d) — KH-02.1 Layered 2D Roman Hilltop Bell-Tower Environments & Bell Rig.
// Pure Canvas2D (3-5 parallax depth planes). Zero Three.js / WebGL / external bitmap dependencies.
// Preserves geographic & mechanical continuity across wide, medium, stairwell, catwalk, and courtyard views.

import { E, clamp, lerp, ease, rng, noise, layer, blurLayer } from '/engine/core.js';
import {
  OUT,
  PAL,
  alpha,
  mix,
  darker,
  lighter,
  shape,
  rect,
  ellipse,
  circ,
  line,
  scaleStrokeWeight2D,
  strokeTapered2D,
  fillCelShadedShape2D,
  drawInkEdgeHighlight2D,
} from '../ink.js';

// Deterministic world-continuous mechanical state of the bell, clapper, and hemp rope across 0..30s!
export function evaluateBellRigStateAt(globalT = 0) {
  const t = clamp(globalT, 0, 30);
  let bellAngle = 0;       // rad, pivot at oak yoke axle
  let clapperRelAngle = 0; // rad relative to bell axis
  let ropePullPx = 0;      // downward pull offset in logical units
  let ropeSlackWave = 0;   // lateral wave amplitude on rope
  let acousticRing = 0;    // 0..1 visual sound wave intensity
  let clapperHeld = false;

  if (t < 3.0) {
    // S01: Pip nudges & tugs loose lower rope loop; tiny micro-tremor on bell far above
    const nudge = Math.sin(clamp((t - 0.15) / 2.6, 0, 1) * Math.PI * 3);
    ropePullPx = Math.max(0, nudge) * 14;
    ropeSlackWave = nudge * 10;
    bellAngle = nudge * 0.018;
    clapperRelAngle = -nudge * 0.012;
  } else if (t < 6.5) {
    // S02: Rope sways gently after goat's tug as Tavi notices in alarm
    const decay = Math.exp(-(t - 3.0) * 0.55);
    const osc = Math.sin((t - 3.0) * 3.8);
    ropeSlackWave = osc * 11 * decay;
    bellAngle = osc * 0.032 * decay;
    clapperRelAngle = -osc * 0.02 * decay;
  } else if (t < 10.0) {
    // S03: Tavi lunges -> grabs rope -> taut pull -> rope slips -> recoil whip -> bell begins to swing!
    const lt = t - 6.5;
    if (lt < 1.05) {
      const k = ease.out(lt / 1.05);
      ropePullPx = lerp(0, 8, k);
      ropeSlackWave = lerp(4, 2, k);
      bellAngle = 0.02;
    } else if (lt < 2.05) {
      // Pull tension peak right before slip
      const k = ease.inOut((lt - 1.05) / 1.0);
      ropePullPx = lerp(8, 52, k);
      ropeSlackWave = Math.sin(lt * 18) * 3 * k;
      bellAngle = lerp(0.02, -0.16, k);
      clapperRelAngle = lerp(0, 0.07, k);
    } else {
      // Slip at globalT = 8.55s! Rope whips upward as heavy bell swings into motion
      const k = clamp((lt - 2.05) / 1.45, 0, 1);
      ropePullPx = lerp(52, -34, ease.out(k));
      ropeSlackWave = Math.sin((lt - 2.05) * 16) * 22 * (1 - k * 0.55);
      bellAngle = -0.16 * Math.cos((lt - 2.05) * 2.4) * lerp(1.0, 1.45, k);
      clapperRelAngle = 0.11 * Math.sin((lt - 2.05) * 2.4 - 0.35);
    }
  } else if (t < 17.5) {
    // S04 & S05: Heavy bell swings rhythmically with growing momentum while Tavi sprints up stairwell
    const dt = t - 8.55;
    const amp = lerp(0.22, 0.34, clamp((t - 10.0) / 7.5, 0, 1));
    bellAngle = -amp * Math.cos(dt * 2.45);
    clapperRelAngle = amp * 0.62 * Math.sin(dt * 2.45 - 0.25);
    ropePullPx = Math.sin(dt * 2.45) * 38;
    ropeSlackWave = Math.cos(dt * 4.9) * 8;
  } else if (t < 23.0) {
    // S06: Tavi catches & braces the iron clapper at t = 18.65s! Motion dampens to silent stillness!
    const lt = t - 17.5;
    if (lt < 1.15) {
      const dt = t - 8.55;
      const damp = lerp(1.0, 0.38, ease.inOut(lt / 1.15));
      bellAngle = -0.32 * damp * Math.cos(dt * 2.45);
      clapperRelAngle = 0.20 * damp * Math.sin(dt * 2.45 - 0.2);
      ropePullPx = Math.sin(dt * 2.45) * 28 * damp;
    } else {
      // Caught & held firm! Bell settles to slight poised tilt, clapper locked by Tavi's hands -> SILENCE
      clapperHeld = true;
      const settle = Math.exp(-(lt - 1.15) * 3.2);
      bellAngle = 0.085 + Math.sin((lt - 1.15) * 7) * 0.025 * settle;
      clapperRelAngle = -0.045;
      ropePullPx = -10 + settle * 4;
      ropeSlackWave = settle * 2;
    }
  } else if (t < 24.85) {
    // S07 pre-sneeze (23.0..24.85s): Pip inhales slowly while bell stays poised
    const lt = t - 23.0;
    clapperHeld = true;
    bellAngle = 0.085;
    clapperRelAngle = -0.045;
    ropePullPx = -10 + ease.in(lt / 1.85) * 6;
  } else {
    // S07 sneeze burst (24.85..26.5s) seamlessly continuing into S08 courtyard tolling (26.5..30.0s)!
    // Single C^1-continuous damped pendulum across the S07->S08 cut!
    const st = t - 24.85;
    const yank = ease.out(clamp(st / 0.35, 0, 1));
    const decay = Math.exp(-Math.max(0, st - 1.65) * 0.22);
    ropePullPx = lerp(-4, 62, yank) * Math.cos(st * 3.1) * decay;
    ropeSlackWave = Math.sin(st * 22) * 24 * Math.exp(-st * 1.1);
    bellAngle = lerp(0.085, -0.36, yank) * Math.cos(st * 3.1) * decay;
    clapperRelAngle = 0.26 * Math.sin(st * 3.1 + 0.35) * decay;
    acousticRing = st > 0.22 ? clamp((1.0 - Math.max(0, st - 1.65) * 0.22), 0.18, 1.0) : 0;
  }

  return {
    bellAngle,
    clapperRelAngle,
    ropePullPx,
    ropeSlackWave,
    acousticRing,
    clapperHeld,
  };
}

export function drawSkyAndLandmarks2D(g, cam, o = {}) {
  const W = E.W, H = E.H;
  const dawnProgress = clamp((o.globalT ?? 0) / 30, 0, 1);
  const horizonY = H * (o.horizonY ?? 0.68);

  // LAYER 0 (depth 0.12): Pre-dawn Roman sky gradient + fading stars + stratified dawn clouds
  layer(g, cam, 0.12, (c) => {
    const zenith = mix('#1b2440', '#2d3f66', dawnProgress * 0.55);
    const midSky = mix('#493d61', '#785774', dawnProgress * 0.55);
    const glowHi = mix('#cb7d63', '#eb9e6c', dawnProgress * 0.6);
    const horizon = mix('#f0b680', '#ffd89c', dawnProgress * 0.65);

    const gr = c.createLinearGradient(0, -H * 0.2, 0, horizonY + H * 0.12);
    gr.addColorStop(0, zenith);
    gr.addColorStop(0.46, midSky);
    gr.addColorStop(0.78, glowHi);
    gr.addColorStop(1, horizon);
    c.fillStyle = gr;
    c.fillRect(-W * 0.5, -H * 0.5, W * 2, H * 2);

    // Subtle pre-dawn rim glow below horizon (not overexposed bloom!)
    const sunX = W * (o.sunX ?? 0.74), sunY = horizonY + H * (0.04 - dawnProgress * 0.05);
    const sGr = c.createRadialGradient(sunX, sunY, H * 0.02, sunX, sunY, H * 0.38);
    sGr.addColorStop(0, alpha('#ffe3ae', 0.48));
    sGr.addColorStop(0.5, alpha('#f4a672', 0.18));
    sGr.addColorStop(1, alpha('#f4a672', 0));
    c.fillStyle = sGr;
    c.fillRect(sunX - H * 0.4, sunY - H * 0.4, H * 0.8, H * 0.8);

    // Fading pre-dawn stars in upper indigo sky
    const r = rng(107);
    const starAlpha = clamp(0.65 - dawnProgress * 0.45, 0.12, 0.7);
    for (let i = 0; i < 26; i++) {
      const sx = r() * W * 1.2 - W * 0.1;
      const sy = r() * horizonY * 0.48;
      circ(c, sx, sy, 1.2 + (i % 3) * 0.6, { fill: alpha('#fff5da', starAlpha), lw: 0 });
    }

    // Stratified warm-edged pre-dawn clouds
    const drift = (o.globalT ?? 0) * 3.5;
    const clouds = [
      [W * 0.22 + drift, horizonY * 0.34, W * 0.22, H * 0.032],
      [W * 0.66 + drift * 0.7, horizonY * 0.26, W * 0.26, H * 0.036],
      [W * 0.48 + drift * 0.5, horizonY * 0.48, W * 0.19, H * 0.025],
    ];
    for (const [cx, cy, cw, ch] of clouds) {
      fillCelShadedShape2D(
        c,
        (cc) => cc.roundRect(cx - cw / 2, cy - ch / 2, cw, ch, ch * 0.5),
        {
          fill: '#6b5573',
          shadow: alpha('#483956', 0.75),
          rim: alpha('#f7be8e', 0.65),
          bounds: [cx, cy, cw * 0.5, ch],
          lw: 1.8,
          ink: alpha(OUT, 0.55),
        }
      );
    }
  });

  // LAYER 1 (depth 0.34): Fixed Geographic Landmarks — Distant Seven Hills, 5-Arch Roman Aqueduct & Twin Cypresses
  layer(g, cam, 0.34, (c) => {
    const farCol = '#474661', midHill = '#3a4254';
    // Far Alban hills silhouette
    shape(
      c,
      (cc) => {
        cc.moveTo(-W * 0.3, H * 1.3);
        cc.lineTo(-W * 0.3, horizonY - H * 0.04);
        cc.quadraticCurveTo(W * 0.12, horizonY - H * 0.13, W * 0.44, horizonY - H * 0.05);
        cc.quadraticCurveTo(W * 0.78, horizonY - H * 0.15, W * 1.3, horizonY - H * 0.03);
        cc.lineTo(W * 1.3, H * 1.3);
        cc.closePath();
      },
      { fill: farCol, lw: 2.0, ink: alpha(OUT, 0.6) }
    );

    // LANDMARK 1: 5-Arch Roman Stone Aqueduct spanning valley right-of-center
    const aqX = W * (o.aqueductX ?? 0.56), aqY = horizonY - H * 0.035;
    const archW = W * 0.052, archH = H * 0.075;
    fillCelShadedShape2D(
      c,
      (cc) => {
        cc.moveTo(aqX, aqY - archH);
        cc.lineTo(aqX + archW * 5.4, aqY - archH);
        cc.lineTo(aqX + archW * 5.4, aqY + archH * 0.4);
        for (let i = 4; i >= 0; i--) {
          const ax = aqX + (i + 0.55) * archW;
          cc.lineTo(ax + archW * 0.32, aqY + archH * 0.4);
          cc.arc(ax, aqY - archH * 0.18, archW * 0.32, 0, Math.PI, true);
          cc.lineTo(ax - archW * 0.32, aqY + archH * 0.4);
        }
        cc.lineTo(aqX, aqY + archH * 0.4);
        cc.closePath();
      },
      {
        fill: '#7d7380',
        shadow: alpha('#544d5e', 0.8),
        rim: alpha('#f5c396', 0.5),
        bounds: [aqX + archW * 2.7, aqY - archH * 0.3, archW * 3, archH],
        lw: 2.0,
        ink: alpha(OUT, 0.7),
      }
    );

    // Mid-distance ridge + LANDMARK 2: Twin Mediterranean Cypresses & Umbrella Pine on left ridge
    shape(
      c,
      (cc) => {
        cc.moveTo(-W * 0.3, H * 1.3);
        cc.lineTo(-W * 0.3, horizonY + H * 0.01);
        cc.quadraticCurveTo(W * 0.25, horizonY - H * 0.06, W * 0.62, horizonY + H * 0.02);
        cc.quadraticCurveTo(W * 0.92, horizonY - H * 0.03, W * 1.3, horizonY + H * 0.02);
        cc.lineTo(W * 1.3, H * 1.3);
        cc.closePath();
      },
      { fill: midHill, lw: 2.2, ink: alpha(OUT, 0.75) }
    );

    const cypBaseX = W * (o.cypressX ?? 0.18), cypBaseY = horizonY - H * 0.015;
    for (const [dx, ch] of [[0, H * 0.13], [W * 0.032, H * 0.105]]) {
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(cypBaseX + dx, cypBaseY - ch);
          cc.quadraticCurveTo(cypBaseX + dx + ch * 0.16, cypBaseY - ch * 0.45, cypBaseX + dx + ch * 0.11, cypBaseY);
          cc.lineTo(cypBaseX + dx - ch * 0.11, cypBaseY);
          cc.quadraticCurveTo(cypBaseX + dx - ch * 0.16, cypBaseY - ch * 0.45, cypBaseX + dx, cypBaseY - ch);
          cc.closePath();
        },
        { fill: '#354b45', shadow: alpha('#22312e', 0.8), bounds: [cypBaseX + dx, cypBaseY - ch / 2, ch * 0.18, ch * 0.5], lw: 2.0, ink: alpha(OUT, 0.75) }
      );
    }
    // Roman umbrella pine silhouette
    const px = cypBaseX + W * 0.078, py = cypBaseY + H * 0.008;
    line(c, [[px, py], [px, py - H * 0.075]], { lw: 4, ink: '#3b2b24' });
    ellipse(c, px, py - H * 0.085, W * 0.036, H * 0.022, { fill: '#3a5248', lw: 2.0, ink: alpha(OUT, 0.75) });
  });
}

export function drawBronzeBellAssembly2D(g, pivotX, pivotY, bellRadius, rigState, o = {}) {
  const lw = o.lw ?? scaleStrokeWeight2D(bellRadius * 2.4, 5.2, 2.0, 9.2);
  const R = bellRadius;
  const ang = rigState.bellAngle || 0;
  const clapRel = rigState.clapperRelAngle || 0;
  const bronze = '#c99642', bronzeSh = '#875d21', bronzeDeep = '#583a11', bronzeHi = '#f5d48c';
  const oak = '#8f5d32', oakSh = '#5c391b';

  g.save();
  g.translate(pivotX, pivotY);

  // Stationary heavy iron axle brackets bolted to crossbeam
  for (const s of [-1, 1]) {
    fillCelShadedShape2D(
      g,
      (c) => c.roundRect(s * R * 0.78 - R * 0.12, -R * 0.24, R * 0.24, R * 0.36, R * 0.04),
      { fill: '#575350', shadow: alpha('#2e2b29', 0.85), bounds: [s * R * 0.78, 0, R * 0.15, R * 0.2], lw: lw * 0.88 }
    );
  }

  // Rotating oak yoke + wheel + bronze bell body
  g.save();
  g.rotate(ang);

  // Pulley rope wheel on right side of yoke
  const wheelR = R * 0.58;
  circ(g, R * 0.62, 0, wheelR, { fill: null, lw: lw * 1.35, ink: oakSh });
  circ(g, R * 0.62, 0, wheelR, { fill: null, lw: lw * 0.8, ink: oak });
  for (let i = 0; i < 4; i++) {
    const sa = (i * Math.PI) / 2;
    line(g, [[R * 0.62 - Math.cos(sa) * wheelR, -Math.sin(sa) * wheelR], [R * 0.62 + Math.cos(sa) * wheelR, Math.sin(sa) * wheelR]], {
      lw: lw * 0.7,
      ink: oak,
    });
  }

  // Heavy counterweighted oak yoke beam
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-R * 0.92, -R * 0.22);
      c.lineTo(R * 0.92, -R * 0.22);
      c.lineTo(R * 0.82, R * 0.16);
      c.lineTo(-R * 0.82, R * 0.16);
      c.closePath();
    },
    { fill: oak, shadow: alpha(oakSh, 0.85), rim: alpha('#ffd49e', 0.5), bounds: [0, 0, R * 0.9, R * 0.22], lw }
  );

  // Dark interior mouth cavity of bell (drawn behind clapper, before front lip highlight)
  const bellH = R * 1.58;
  ellipse(g, 0, bellH, R * 0.96, R * 0.22, { fill: '#2c1c10', lw });

  // Suspended internal iron clapper shaft + heavy striking bulb
  const clapperPivotY = R * 0.34;
  const clapperLen = R * 1.34;
  g.save();
  g.translate(0, clapperPivotY);
  g.rotate(clapRel);
  strokeTapered2D(g, [[0, 0], [0, clapperLen]], { lw: lw * 1.9, startRatio: 0.7, midRatio: 0.85, endRatio: 1.0, ink: OUT });
  strokeTapered2D(g, [[0, 0], [0, clapperLen]], { lw: lw * 1.05, startRatio: 0.7, midRatio: 0.85, endRatio: 1.0, ink: '#706a66' });
  fillCelShadedShape2D(
    g,
    (c) => c.arc(0, clapperLen * 0.92, R * 0.18, 0, Math.PI * 2),
    {
      fill: '#7d7772',
      shadow: alpha('#45403d', 0.88),
      rim: alpha('#ffe3b3', 0.7),
      bounds: [0, clapperLen * 0.92, R * 0.18, R * 0.18],
      lw: lw * 0.92,
    }
  );
  g.restore();

  // Giant cast-bronze Roman watch-bell profile (flared sound-bow + engraved bands)
  fillCelShadedShape2D(
    g,
    (c) => {
      c.moveTo(-R * 0.52, R * 0.14);
      c.lineTo(R * 0.52, R * 0.14);
      c.bezierCurveTo(R * 0.62, R * 0.62, R * 0.72, R * 1.18, R * 1.02, bellH);
      c.quadraticCurveTo(0, bellH - R * 0.12, -R * 1.02, bellH);
      c.bezierCurveTo(-R * 0.72, R * 1.18, -R * 0.62, R * 0.62, -R * 0.52, R * 0.14);
      c.closePath();
    },
    {
      fill: bronze,
      shadow: alpha(bronzeSh, 0.88),
      deepShadow: alpha(bronzeDeep, 0.52),
      bounds: [0, bellH * 0.55, R, bellH * 0.55],
      lw,
      inner: (c) => {
        // Warm specular bronze highlight band on dawn-lit side
        drawInkEdgeHighlight2D(
          c,
          [[-R * 0.42, R * 0.26], [-R * 0.54, R * 0.86], [-R * 0.78, bellH - R * 0.12]],
          { lw: Math.max(3, R * 0.085), color: bronzeHi, a: 0.76 }
        );
        // Cast bronze decorative Roman rib moldings
        strokeTapered2D(c, [[-R * 0.58, R * 0.46], [0, R * 0.42], [R * 0.58, R * 0.46]], { lw: lw * 0.75, ink: bronzeDeep });
        strokeTapered2D(c, [[-R * 0.88, bellH - R * 0.22], [0, bellH - R * 0.28], [R * 0.88, bellH - R * 0.22]], { lw: lw * 0.82, ink: bronzeDeep });
      },
    }
  );

  // Acoustic 2D ring wave arcs when bell tolls (S07 burst / S08 payoff)
  if ((rigState.acousticRing || 0) > 0.05) {
    const ar = rigState.acousticRing;
    for (let k = 1; k <= 3; k++) {
      const waveR = R * (1.2 + k * 0.34 + ((o.globalT || 0) * 1.8 % 0.35));
      for (const s of [-1, 1]) {
        g.save();
        g.beginPath();
        g.arc(0, bellH * 0.8, waveR, s > 0 ? -0.42 : Math.PI - 0.42, s > 0 ? 0.42 : Math.PI + 0.42);
        g.strokeStyle = alpha('#ffe4a8', ar * (1.0 - k * 0.24));
        g.lineWidth = Math.max(2, lw * (1.1 - k * 0.2));
        g.lineCap = 'round';
        g.stroke();
        g.restore();
      }
    }
  }

  g.restore(); // bell rotation
  g.restore(); // pivot

  // Compute exact world-space coordinates of clapper bulb & rope attachment point!
  const sinA = Math.sin(ang), cosA = Math.cos(ang);
  const totClap = ang + clapRel;
  const cPivotWorld = [pivotX - R * 0.34 * sinA, pivotY + R * 0.34 * cosA];
  const clapperBulbWorld = [
    cPivotWorld[0] - R * 1.23 * Math.sin(totClap),
    cPivotWorld[1] + R * 1.23 * Math.cos(totClap),
  ];
  const ropeTopWorld = [
    pivotX + (R * 0.62 + wheelR * 0.92) * cosA,
    pivotY + (R * 0.62 + wheelR * 0.92) * sinA,
  ];
  return {
    pivotWorld: [pivotX, pivotY],
    clapperBulbWorld,
    ropeTopWorld,
    mouthCenterWorld: [pivotX - bellH * sinA, pivotY + bellH * cosA],
  };
}

export function drawBellRopeSegment2D(g, topPt, bottomPt, rigState, o = {}) {
  const lw = o.lw ?? 4.2;
  const ropeW = o.ropeWidth ?? 11;
  const wave = rigState.ropeSlackWave || 0;
  const mid1 = [
    lerp(topPt[0], bottomPt[0], 0.33) + wave * 0.75,
    lerp(topPt[1], bottomPt[1], 0.33),
  ];
  const mid2 = [
    lerp(topPt[0], bottomPt[0], 0.68) - wave * 0.55,
    lerp(topPt[1], bottomPt[1], 0.68),
  ];
  const pts = [topPt, mid1, mid2, bottomPt];

  // Outer dark contour + braided hemp fill + twist ticks
  line(g, pts, { lw: ropeW + lw * 2, ink: OUT });
  line(g, pts, { lw: ropeW, ink: '#cbb07c' });
  line(g, pts, { lw: ropeW * 0.35, ink: alpha('#fff0cc', 0.45) });

  const steps = Math.max(5, Math.min(26, Math.round(Math.hypot(bottomPt[0] - topPt[0], bottomPt[1] - topPt[1]) / 26)));
  for (let i = 1; i < steps; i++) {
    const k = i / steps;
    const px = k < 0.5 ? lerp(topPt[0], mid1[0], k * 2) : lerp(mid2[0], bottomPt[0], (k - 0.5) * 2);
    const py = lerp(topPt[1], bottomPt[1], k);
    line(g, [[px - ropeW * 0.38, py - 3], [px + ropeW * 0.38, py + 3]], { lw: Math.max(1.2, lw * 0.45), ink: '#7d6238' });
  }

  if (o.coiledBase) {
    const [bx, by] = bottomPt;
    for (let rIdx = 2; rIdx >= 0; rIdx--) {
      ellipse(g, bx + 18, by + 6 + rIdx * 6, 36 + rIdx * 10, 9 + rIdx * 2.5, {
        fill: rIdx % 2 ? '#b89b67' : '#cbb07c',
        lw: lw * 0.85,
      });
    }
  }
  return { topPt, bottomPt, mid1, mid2 };
}

function _drawStoneBlocks2D(g, x, y, w, h, seed = 11, col = '#9c9284', shadowCol = '#756c60', lw = 3.0) {
  rect(g, x, y, w, h, { fill: col, lw, r: 2 });
  const r = rng(seed);
  const rowH = 54;
  g.save();
  g.beginPath();
  g.rect(x, y, w, h);
  g.clip();
  for (let ry = y; ry < y + h; ry += rowH) {
    line(g, [[x, ry], [x + w, ry]], { lw: lw * 0.65, ink: alpha(OUT, 0.65) });
    const off = ((Math.round((ry - y) / rowH) % 2) * 58);
    for (let rx = x - off; rx < x + w; rx += 116) {
      if (r() < 0.38) {
        g.fillStyle = alpha(shadowCol, 0.42);
        g.fillRect(rx + 3, ry + 3, 110, rowH - 6);
      }
      line(g, [[rx, ry], [rx, ry + rowH]], { lw: lw * 0.55, ink: alpha(OUT, 0.55) });
    }
  }
  g.restore();
}

export function drawLayeredRomanEnvironment2D(g, cam, o = {}) {
  const W = E.W, H = E.H;
  const view = o.view || 'belfry_wide_interior';
  const globalT = o.globalT ?? 0;
  const rigState = o.rigState || evaluateBellRigStateAt(globalT);

  drawSkyAndLandmarks2D(g, cam, {
    globalT,
    horizonY: view === 'belfry_low_angle' ? 0.82 : view === 'hilltop_courtyard_wide' ? 0.64 : 0.72,
    aqueductX: view === 'tower_stairwell_ascent' ? 0.52 : 0.56,
    cypressX: view === 'hilltop_courtyard_wide' ? 0.78 : 0.18,
  });

  let anchors = { rigState };

  if (view === 'belfry_lower_arch' || view === 'belfry_wide_interior' || view === 'belfry_low_angle') {
    const isLow = view === 'belfry_low_angle';
    const isCloseFloor = view === 'belfry_lower_arch';
    const floorY = isLow ? H * 1.08 : isCloseFloor ? H * 0.83 : H * 0.88;

    // LAYER 2 (depth 0.74): Stone belfry piers + Roman arch + heavy oak crossbeams
    const renderMidArch = (c) => {
      _drawStoneBlocks2D(c, -120, -120, W * 0.21 + 120, H + 240, 21, '#8c8276', '#635b52', 3.6);
      _drawStoneBlocks2D(c, W * 0.79, -120, W * 0.21 + 140, H + 240, 29, '#8c8276', '#635b52', 3.6);
      // Warm dawn inner-arch rim light on left pier
      drawInkEdgeHighlight2D(c, [[W * 0.21 - 4, H * 0.12], [W * 0.21 - 4, floorY]], { lw: 5, color: '#ffd39b', a: 0.65 });

      // Roman stone arch header & oak main crossbeam
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(-80, -100);
          cc.lineTo(W + 80, -100);
          cc.lineTo(W + 80, H * 0.26);
          cc.lineTo(W * 0.79, H * 0.26);
          cc.quadraticCurveTo(W * 0.5, H * 0.02, W * 0.21, H * 0.26);
          cc.lineTo(-80, H * 0.26);
          cc.closePath();
        },
        { fill: '#786f64', shadow: alpha('#524b43', 0.85), bounds: [W * 0.5, H * 0.08, W * 0.6, H * 0.2], lw: 4.0 }
      );
      // Heavy mortised oak crossbeam supporting the bell
      const beamY = isLow ? H * 0.16 : isCloseFloor ? -H * 0.12 : H * 0.14;
      fillCelShadedShape2D(
        c,
        (cc) => cc.roundRect(W * 0.16, beamY, W * 0.68, H * 0.068, 4),
        { fill: '#7d5029', shadow: alpha('#4d2f16', 0.85), rim: alpha('#ffd49e', 0.55), bounds: [W * 0.5, beamY + H * 0.03, W * 0.35, H * 0.04], lw: 4.2 }
      );
    };

    if (o.blurBackBell) {
      blurLayer(g, o.blurBackBell, (c) => {
        renderMidArch(c);
        drawBronzeBellAssembly2D(c, W * 0.52, H * 0.16, H * 0.19, rigState, { globalT, lw: 4.0 });
      }, cam, 0.74);
    } else {
      layer(g, cam, 0.74, renderMidArch);
    }

    // LAYER 3 (depth 1.0): Main Action Stage — Stone floor, bronze bell, coiled hemp rope
    layer(g, cam, 1.0, (c) => {
      if (!isLow) {
        fillCelShadedShape2D(
          c,
          (cc) => cc.rect(-180, floorY, W + 360, H - floorY + 220),
          { fill: '#70675e', shadow: alpha('#4c453e', 0.8), bounds: [W * 0.5, floorY + 80, W * 0.7, 120], lw: 4.5 }
        );
        for (let sx = 80; sx < W; sx += 210) {
          line(c, [[sx, floorY], [sx - 45, H + 80]], { lw: 2.8, ink: alpha(OUT, 0.55) });
        }
        drawInkEdgeHighlight2D(c, [[W * 0.18, floorY + 3], [W * 0.82, floorY + 3]], { lw: 4.0, color: '#ffd39b', a: 0.55 });
      }

      if (!o.blurBackBell) {
        const bellPivotY = isLow ? H * 0.20 : H * 0.18;
        const bellR = isLow ? H * 0.25 : H * 0.22;
        const bellInfo = drawBronzeBellAssembly2D(c, W * 0.5, bellPivotY, bellR, rigState, { globalT });
        const ropeBottom = [
          bellInfo.ropeTopWorld[0] + 6,
          (isLow ? H * 1.12 : floorY - 12) + rigState.ropePullPx * 0.65,
        ];
        drawBellRopeSegment2D(c, bellInfo.ropeTopWorld, ropeBottom, rigState, {
          coiledBase: !isLow,
          ropeWidth: isLow ? 14 : 11,
        });
        anchors.bell = bellInfo;
        anchors.ropeGripWorld = [
          lerp(bellInfo.ropeTopWorld[0], ropeBottom[0], 0.58) + rigState.ropeSlackWave * 0.45,
          lerp(bellInfo.ropeTopWorld[1], ropeBottom[1], 0.58) + rigState.ropePullPx * 0.35,
        ];
        anchors.ropeFloorLoopWorld = [ropeBottom[0], ropeBottom[1] - 28];
      } else {
        // Close floor view (S01 / S07): crisp foreground rope descending from blurred upper belfry to stone cleat & floor coil!
        const ropeTop = [W * 0.58, -80];
        const ropeBot = [W * 0.58, floorY - 14 + rigState.ropePullPx * 0.45];
        drawBellRopeSegment2D(c, ropeTop, ropeBot, rigState, { coiledBase: true, ropeWidth: 14, lw: 4.8 });
        anchors.ropeFloorLoopWorld = [ropeBot[0] - 4, ropeBot[1] - 46];
        anchors.ropeGripWorld = [ropeBot[0], floorY - H * 0.32];
      }

      if (o.drawStageActors) o.drawStageActors(c, anchors);
    });

    // LAYER 4 (depth 1.26): Dark foreground framing timber & stone spandrel occluder
    layer(g, cam, 1.26, (c) => {
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(-220, -180);
          cc.lineTo(W * 0.11, -180);
          cc.quadraticCurveTo(W * 0.04, H * 0.22, W * 0.03, H + 180);
          cc.lineTo(-220, H + 180);
          cc.closePath();
        },
        { fill: '#221c24', lw: 3.5 }
      );
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(W * 0.92, -180);
          cc.lineTo(W + 220, -180);
          cc.lineTo(W + 220, H + 180);
          cc.lineTo(W * 0.96, H + 180);
          cc.quadraticCurveTo(W * 0.95, H * 0.28, W * 0.92, -180);
          cc.closePath();
        },
        { fill: '#221c24', lw: 3.5 }
      );
    });
  } else if (view === 'tower_stairwell_ascent') {
    // VIEW 2: Rising Roman stone stairwell with arched window overlooking the SAME aqueduct horizon + vertical bell rope shaft!
    const steps = [];
    const numSteps = 9;
    for (let i = 0; i < numSteps; i++) {
      // Steps ascend left -> right (x: 180 -> 1620, y: 980 -> 340)
      const sx = 150 + i * 175;
      const sy = 985 - i * 76;
      steps.push({ index: i, treadX: sx + 85, treadY: sy, rawX: sx, w: 190, h: 82 });
    }
    anchors.stairs = steps;

    layer(g, cam, 0.72, (c) => {
      // Back stairwell stone wall with arched window cut-out showing Layer 0/1 sky & aqueduct!
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.rect(-200, -200, W + 400, H + 400);
          // Arched window cutout (evenodd)
          const wx = W * 0.56, wy = H * 0.34, ww = W * 0.19, wh = H * 0.28;
          cc.moveTo(wx - ww / 2, wy + wh / 2);
          cc.lineTo(wx - ww / 2, wy - wh * 0.15);
          cc.arc(wx, wy - wh * 0.15, ww / 2, Math.PI, 0, false);
          cc.lineTo(wx + ww / 2, wy + wh / 2);
          cc.closePath();
        },
        { fill: '#6d645c', lw: 0 }
      );
      // Stone arch window trim + warm dawn light shaft angling across stairs
      const wx = W * 0.56, wy = H * 0.34, ww = W * 0.19, wh = H * 0.28;
      g.save();
      c.strokeStyle = OUT;
      c.lineWidth = 5;
      c.beginPath();
      c.moveTo(wx - ww / 2, wy + wh / 2);
      c.lineTo(wx - ww / 2, wy - wh * 0.15);
      c.arc(wx, wy - wh * 0.15, ww / 2, Math.PI, 0, false);
      c.lineTo(wx + ww / 2, wy + wh / 2);
      c.closePath();
      c.stroke();
      // Subtle warm dawn light shaft
      c.fillStyle = alpha('#ffd79e', 0.14);
      c.beginPath();
      c.moveTo(wx - ww * 0.45, wy + wh * 0.45);
      c.lineTo(wx + ww * 0.45, wy + wh * 0.45);
      c.lineTo(wx - ww * 1.4, H + 120);
      c.lineTo(wx - ww * 2.5, H + 120);
      c.closePath();
      c.fill();
      g.restore();

      // Vertical bell rope oscillating up through ceiling shaft on right!
      drawBellRopeSegment2D(c, [W * 0.84, -120], [W * 0.84, H + 120], rigState, { ropeWidth: 10, lw: 3.8 });
    });

    layer(g, cam, 1.0, (c) => {
      // Stepped travertine stone staircase + timber handrail
      for (const st of steps) {
        fillCelShadedShape2D(
          c,
          (cc) => cc.rect(st.rawX, st.treadY, st.w + 40, H - st.treadY + 180),
          { fill: '#8a8073', shadow: alpha('#595249', 0.85), bounds: [st.treadX, st.treadY + 50, 100, 60], lw: 4.0 }
        );
        // Crisp sunlit top tread slab
        fillCelShadedShape2D(
          c,
          (cc) => cc.roundRect(st.rawX - 8, st.treadY - 6, st.w + 18, 18, 3),
          { fill: '#b8ad9d', rim: alpha('#ffe1b0', 0.65), bounds: [st.treadX, st.treadY, 100, 12], lw: 3.8 }
        );
      }
      if (o.drawStageActors) o.drawStageActors(c, anchors);
    });

    layer(g, cam, 1.25, (c) => {
      // Foreground diagonal oak handrail beam for authentic 2D parallax!
      strokeTapered2D(c, [[-80, H * 0.96], [W + 80, H * 0.24]], { lw: 22, startRatio: 1.0, midRatio: 1.0, endRatio: 0.9, ink: '#1e1718' });
    });
  } else if (view === 'belfry_catwalk_clapper') {
    // VIEW 3: Upper belfry timber catwalk right beside the bronze bell mouth & iron clapper!
    const catwalkY = H * 0.88;
    layer(g, cam, 0.68, (c) => {
      _drawStoneBlocks2D(c, -140, -140, W * 0.16 + 140, H + 280, 33, '#7b7267', '#544d45', 3.8);
      _drawStoneBlocks2D(c, W * 0.86, -140, W * 0.16 + 160, H + 280, 37, '#7b7267', '#544d45', 3.8);
    });

    layer(g, cam, 1.0, (c) => {
      // Heavy oak catwalk planks & safety brace
      fillCelShadedShape2D(
        c,
        (cc) => cc.rect(-140, catwalkY, W + 280, H - catwalkY + 200),
        { fill: '#754b27', shadow: alpha('#472c14', 0.85), bounds: [W * 0.5, catwalkY + 60, W * 0.6, 80], lw: 4.5 }
      );
      drawInkEdgeHighlight2D(c, [[W * 0.1, catwalkY + 3], [W * 0.9, catwalkY + 3]], { lw: 4.2, color: '#ffd39b', a: 0.6 });

      const bellPivotX = o.closeupClapper ? W * 0.54 : W * 0.58;
      const bellPivotY = o.closeupClapper ? -H * 0.42 : -H * 0.04;
      const bellR = o.closeupClapper ? H * 0.56 : H * 0.34;
      const bellInfo = drawBronzeBellAssembly2D(c, bellPivotX, bellPivotY, bellR, rigState, { globalT, lw: o.closeupClapper ? 6.2 : 5.0 });
      drawBellRopeSegment2D(c, bellInfo.ropeTopWorld, [bellInfo.ropeTopWorld[0] + 10, H + 160], rigState, { ropeWidth: o.closeupClapper ? 16 : 12 });
      anchors.bell = bellInfo;
      anchors.catwalkY = catwalkY;
      if (o.drawStageActors) o.drawStageActors(c, anchors);
    });

    layer(g, cam, 1.24, (c) => {
      // Foreground timber cross-strut framing top-left corner
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(-120, -80);
          cc.lineTo(W * 0.26, -80);
          cc.lineTo(-120, H * 0.32);
          cc.closePath();
        },
        { fill: '#21191d', lw: 3.5 }
      );
    });
  } else if (view === 'hilltop_courtyard_wide') {
    // VIEW 4: Hilltop cobbled courtyard directly below the bell tower (with bell tower rising on left!)
    const groundY = H * 0.84;
    layer(g, cam, 0.66, (c) => {
      // The SAME hilltop bell tower rising on left with swinging bronze bell visible inside its open belfry!
      _drawStoneBlocks2D(c, W * 0.06, H * 0.08, W * 0.24, groundY - H * 0.08, 41, '#94897b', '#6b6257', 3.4);
      // Terracotta pitched belfry roof
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(W * 0.03, H * 0.09);
          cc.lineTo(W * 0.18, H * 0.01);
          cc.lineTo(W * 0.33, H * 0.09);
          cc.closePath();
        },
        { fill: '#b6533c', shadow: alpha('#7c3322', 0.85), bounds: [W * 0.18, H * 0.05, W * 0.15, H * 0.05], lw: 3.6 }
      );
      // Open belfry arch cutout + miniature synchronized bronze bell!
      const bx = W * 0.18, by = H * 0.21;
      fillCelShadedShape2D(
        c,
        (cc) => cc.roundRect(bx - W * 0.055, by - H * 0.07, W * 0.11, H * 0.16, [W * 0.055, W * 0.055, 2, 2]),
        { fill: '#2a283d', bounds: [bx, by, W * 0.06, H * 0.08], lw: 3.2 }
      );
      drawBronzeBellAssembly2D(c, bx, by - H * 0.045, H * 0.055, rigState, { globalT, lw: 2.4 });
    });

    layer(g, cam, 0.88, (c) => {
      // Adjacent Roman insula courtyard facade on right with shuttered balcony windows
      _drawStoneBlocks2D(c, W * 0.44, H * 0.22, W * 0.52, groundY - H * 0.22, 53, '#cbbba4', '#9c8c76', 3.5);
      fillCelShadedShape2D(
        c,
        (cc) => {
          cc.moveTo(W * 0.41, H * 0.23);
          cc.lineTo(W * 0.98, H * 0.17);
          cc.lineTo(W * 0.98, H * 0.24);
          cc.lineTo(W * 0.41, H * 0.27);
          cc.closePath();
        },
        { fill: '#b6533c', shadow: alpha('#7c3322', 0.85), bounds: [W * 0.7, H * 0.22, W * 0.28, H * 0.05], lw: 3.6 }
      );

      // Upper shuttered window where Elder Bell-Mistress LYRA pops out at dawn!
      const openK = clamp(o.shutterOpenK ?? 1.0, 0, 1);
      const wx = W * 0.68, wy = H * 0.44, ww = W * 0.11, wh = H * 0.16;
      rect(c, wx - ww / 2, wy - wh / 2, ww, wh, { fill: '#28222e', lw: 3.5, r: 4 });
      const shW = lerp(ww * 0.48, ww * 0.22, openK);
      rect(c, wx - ww / 2 - shW, wy - wh / 2, shW, wh, { fill: '#7d5029', lw: 3.0, r: 2 });
      rect(c, wx + ww / 2, wy - wh / 2, shW, wh, { fill: '#7d5029', lw: 3.0, r: 2 });
      anchors.balconyWindowWorld = [wx, wy + wh * 0.46];
    });

    layer(g, cam, 1.0, (c) => {
      // Cobbled courtyard ground + terracotta amphorae (zero marketplace awnings, zero carts, zero scrolls!)
      fillCelShadedShape2D(
        c,
        (cc) => cc.rect(-180, groundY, W + 360, H - groundY + 200),
        { fill: '#82786d', shadow: alpha('#595149', 0.85), bounds: [W * 0.5, groundY + 80, W * 0.6, 100], lw: 4.2 }
      );
      // Clay amphorae resting beside tower wall
      for (const [ax, ay, sc] of [[W * 0.34, groundY + 12, 1.0], [W * 0.38, groundY + 18, 0.82]]) {
        fillCelShadedShape2D(
          c,
          (cc) => {
            cc.moveTo(ax - 12 * sc, ay - 52 * sc);
            cc.lineTo(ax + 12 * sc, ay - 52 * sc);
            cc.bezierCurveTo(ax + 28 * sc, ay - 34 * sc, ax + 24 * sc, ay - 8 * sc, ax + 8 * sc, ay);
            cc.lineTo(ax - 8 * sc, ay);
            cc.bezierCurveTo(ax - 24 * sc, ay - 8 * sc, ax - 28 * sc, ay - 34 * sc, ax - 12 * sc, ay - 52 * sc);
            cc.closePath();
          },
          { fill: '#b86346', shadow: alpha('#7c3d28', 0.85), bounds: [ax, ay - 26 * sc, 24 * sc, 26 * sc], lw: 3.2 }
        );
      }
      anchors.courtyardGroundY = groundY;
      if (o.drawStageActors) o.drawStageActors(c, anchors);
    });

    layer(g, cam, 1.22, (c) => {
      // Foreground olive branch silhouette top-right
      for (let i = 0; i < 5; i++) {
        ellipse(c, W * (0.88 + i * 0.025), H * (0.06 + (i % 2) * 0.03), 38, 16, {
          fill: '#232d28',
          lw: 2.5,
          rot: -0.35 + i * 0.15,
        });
      }
    });
  }

  return anchors;
}
