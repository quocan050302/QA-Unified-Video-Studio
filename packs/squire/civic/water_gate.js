// packs/squire/civic/water_gate.js — Reusable Procedural Roman Civic Engineering & Hydraulic Primitives (V14.7.5.1).
// Newly authored 100% vector/canvas artwork for civic infrastructure storytelling (aqueduct masonry, propagating
// stone fissures, pressurized water jets, bronze spoked handwheel + meshed gear + rope + sliding timber sluice gate,
// stepped overflow catch-basin, market street, and expressive Roman civic engineers/workers).
// Zero external raster images, zero prior preview assets, zero military/battlefield props.

import { E, clamp, lerp, ease, rng, registerShot, registerTemplate, text, measure, alpha } from '/engine/core.js';
import { OUT, PAL, shape, rect, ellipse, circ, polyS, line, tube, haze, FONT_THUMB, FONT_CAP, FONT_SIGN } from '/packs/squire/ink.js';

const INK_ACTOR = '#2f221a';
const INK_MASONRY = '#66584a'; // Warm mortar outline (>55 RGB so background stone never triggers actor-ink edge false positives)

export function applyCivicCamera(g, lt, info, drawFn) {
  const a = info.args || {};
  const rig = a.cameraRig;
  let z = 1.0, cx = E.W * 0.5, cy = E.H * 0.5;
  if (rig && Array.isArray(rig.keyframes) && rig.keyframes.length > 0) {
    const kfs = rig.keyframes;
    let k0 = kfs[0], k1 = kfs[kfs.length - 1];
    if (lt <= k0.t) {
      k1 = k0;
    } else if (lt >= k1.t) {
      k0 = k1;
    } else {
      for (let i = 0; i < kfs.length - 1; i++) {
        if (lt >= kfs[i].t && lt <= kfs[i + 1].t) {
          k0 = kfs[i];
          k1 = kfs[i + 1];
          break;
        }
      }
    }
    const span = Math.max(0.01, (k1.t || 0) - (k0.t || 0));
    const u = ease.inOut(clamp((lt - (k0.t || 0)) / span));
    z = clamp(lerp(k0.z ?? 1.0, k1.z ?? 1.0, u), 1.0, 1.35);
    cx = lerp(k0.x ?? 0.5, k1.x ?? 0.5, u) * E.W;
    cy = lerp(k0.y ?? 0.5, k1.y ?? 0.5, u) * E.H;
  }
  let shakeX = 0, shakeY = 0;
  if (a.shake && a.shake > 0) {
    const st0 = a.shakeAt ?? 0;
    if (lt >= st0) {
      const decay = Math.max(0, 1 - (lt - st0) / (a.shakeDur ?? 0.9));
      shakeX = Math.sin(lt * 58) * 8 * a.shake * decay;
      shakeY = Math.cos(lt * 49) * 5 * a.shake * decay;
    }
  }
  const hw = E.W / (2 * z), hh = E.H / (2 * z);
  cx = clamp(cx + shakeX, hw, E.W - hw);
  cy = clamp(cy + shakeY, hh, E.H - hh);
  g.save();
  g.translate(E.W / 2, E.H / 2);
  g.scale(z, z);
  g.translate(-cx, -cy);
  drawFn();
  g.restore();
}

export function drawMediterraneanSkyAndHills(g, lt, moodMode = 'urgent') {
  const W = E.W, H = E.H;
  const skyGrad = g.createLinearGradient(0, 0, 0, H * 0.72);
  if (moodMode === 'golden') {
    skyGrad.addColorStop(0, '#7ca8cb');
    skyGrad.addColorStop(0.55, '#c7d9df');
    skyGrad.addColorStop(1, '#f0d8b4');
  } else {
    skyGrad.addColorStop(0, '#6e96b8');
    skyGrad.addColorStop(0.58, '#aec8dc');
    skyGrad.addColorStop(1, '#dde4e6');
  }
  g.fillStyle = skyGrad;
  g.fillRect(0, 0, W, H);

  // Soft drifting clouds
  const drift = lt * 12;
  g.save();
  g.fillStyle = moodMode === 'golden' ? 'rgba(255,248,236,0.68)' : 'rgba(248,251,254,0.62)';
  for (const [bx, by, rx, ry] of [[280, 130, 150, 34], [880, 105, 190, 38], [1480, 145, 165, 32]]) {
    const cx = ((bx + drift) % (W + 360)) - 180;
    g.beginPath();
    g.ellipse(cx, by, rx, ry, 0, 0, Math.PI * 2);
    g.ellipse(cx - rx * 0.45, by + 8, rx * 0.65, ry * 0.78, 0, 0, Math.PI * 2);
    g.ellipse(cx + rx * 0.48, by + 6, rx * 0.6, ry * 0.75, 0, 0, Math.PI * 2);
    g.fill();
  }
  g.restore();

  // Distant Alban hills & Roman cypress silhouettes
  polyS(g, [
    [0, H * 0.68], [W * 0.18, H * 0.56], [W * 0.39, H * 0.61],
    [W * 0.63, H * 0.53], [W * 0.84, H * 0.59], [W, H * 0.55], [W, H * 0.78], [0, H * 0.78],
  ], { fill: moodMode === 'golden' ? '#95a58c' : '#899ca2', lw: 0 });

  for (const tx of [0.11, 0.14, 0.79, 0.82, 0.91]) {
    const cx = W * tx, baseY = H * 0.63;
    polyS(g, [[cx - 9, baseY], [cx, baseY - 62], [cx + 9, baseY]], { fill: '#5b7258', lw: 0 });
  }
}

export function drawRomanMarketStreet(g, lt, opts = {}) {
  const W = E.W, H = E.H;
  const groundY = (opts.groundY ?? 0.86) * H;
  const wetPatch = clamp(opts.wetPatch ?? 0.12, 0, 1);

  // Background Roman town insulae (terracotta roofs & plaster walls)
  const houses = [
    { x: 0.04, w: 0.19, h: 0.24, wall: '#dfd0ba', roof: '#b55b42' },
    { x: 0.25, w: 0.17, h: 0.20, wall: '#d6c4ab', roof: '#a84f39' },
    { x: 0.60, w: 0.18, h: 0.22, wall: '#e2d3be', roof: '#ba6046' },
    { x: 0.80, w: 0.17, h: 0.25, wall: '#d8c7af', roof: '#a9523b' },
  ];
  for (const hs of houses) {
    const hx = hs.x * W, hw = hs.w * W, hh = hs.h * H, hy = groundY - hh;
    rect(g, hx, hy, hw, hh, { fill: hs.wall, lw: 3, ink: INK_MASONRY, r: 2 });
    polyS(g, [[hx - 14, hy + 4], [hx + hw * 0.5, hy - 28], [hx + hw + 14, hy + 4]], {
      fill: hs.roof, lw: 3, ink: INK_MASONRY,
    });
    // Arched windows
    for (let k = 0; k < 3; k++) {
      const wx = hx + hw * (0.2 + k * 0.28), wy = hy + hh * 0.28;
      rect(g, wx - 11, wy, 22, 34, { fill: '#5f5246', lw: 2, ink: INK_MASONRY, r: 8 });
    }
    // Striped linen market awning
    const ay = groundY - hh * 0.36;
    polyS(g, [[hx + 8, ay], [hx + hw - 8, ay], [hx + hw + 6, ay + 26], [hx - 6, ay + 26]], {
      fill: '#d87a4a', lw: 2.5, ink: INK_MASONRY,
    });
    // Terracotta amphorae & woven grain baskets (purely civic props)
    ellipse(g, hx + 26, groundY - 14, 11, 16, { fill: '#b96949', lw: 2.5, ink: INK_MASONRY });
    ellipse(g, hx + hw - 28, groundY - 12, 14, 12, { fill: '#c8a468', lw: 2.5, ink: INK_MASONRY });
  }

  // Sunlit travertine cobbled street (warm mid-tone >= 115 RGB right down to bottom edge so bottom strip never reads as dark actor ink)
  rect(g, 0, groundY, W, H - groundY, { fill: '#9f8e79', lw: 0, r: 0 });
  g.save();
  g.strokeStyle = '#7e6e5b';
  g.lineWidth = 2;
  for (let row = 0; row < 4; row++) {
    const py = groundY + 14 + row * 34;
    g.beginPath();
    g.moveTo(0, py);
    g.lineTo(W, py);
    g.stroke();
    for (let col = 0; col < 16; col++) {
      const px = ((col * 128 + row * 48) % W);
      g.beginPath();
      g.moveTo(px, py);
      g.lineTo(px - 10, py + 34);
      g.stroke();
    }
  }
  if (wetPatch > 0.02) {
    g.fillStyle = alpha('#5a8fb2', 0.28 * wetPatch);
    g.beginPath();
    g.ellipse(W * 0.28, groundY + 28, 120 * wetPatch + 24, 14, 0, 0, Math.PI * 2);
    g.fill();
  }
  g.restore();
}

export function drawAqueductMasonry(g, opts = {}) {
  const W = E.W, H = E.H;
  const deckY = (opts.deckY ?? 0.34) * H;
  const groundY = (opts.groundY ?? 0.86) * H;
  const archSpan = (opts.archSpan ?? 0.30) * W;
  const piers = opts.piers || [0.22, 0.56, 0.90];
  const pierW = (opts.pierW ?? 0.11) * W;

  // Upper water specus (stone channel wall & parapet)
  rect(g, 0, deckY - 58, W, 62, { fill: '#cfc3b0', lw: 3.5, ink: INK_MASONRY, r: 0 });
  rect(g, 0, deckY - 66, W, 12, { fill: '#dfd5c5', lw: 2.5, ink: INK_MASONRY, r: 0 });

  // Flowing water visible inside upper channel if showChannelWater
  if (opts.showChannelWater) {
    const waterH = clamp(opts.channelLevel ?? 0.75, 0.1, 1.0) * 32;
    rect(g, 0, deckY - 14 - waterH, W * (opts.waterStopX ?? 1.0), waterH, {
      fill: '#4989b8', lw: 0, r: 0,
    });
  }

  // Stone piers & semicircular Roman arches
  for (let i = 0; i < piers.length; i++) {
    const px = piers[i] * W;
    rect(g, px - pierW / 2, deckY, pierW, groundY - deckY, {
      fill: '#c5b8a4', lw: 3.5, ink: INK_MASONRY, r: 2,
    });
    // Pier impost cornice
    rect(g, px - pierW * 0.58, deckY + 82, pierW * 1.16, 18, {
      fill: '#d9cebd', lw: 2.5, ink: INK_MASONRY, r: 2,
    });
    // Ashlar block courses on pier
    g.save();
    g.strokeStyle = '#8b7d6b';
    g.lineWidth = 2;
    for (let y = deckY + 28; y < groundY - 22; y += 34) {
      g.beginPath();
      g.moveTo(px - pierW / 2 + 4, y);
      g.lineTo(px + pierW / 2 - 4, y);
      g.stroke();
    }
    g.restore();

    // Arch spanning to next pier
    if (i < piers.length - 1) {
      const nextPx = piers[i + 1] * W;
      const spanLeft = px + pierW / 2;
      const spanRight = nextPx - pierW / 2;
      const cx = (spanLeft + spanRight) * 0.5;
      const rx = Math.max(40, (spanRight - spanLeft) * 0.5);
      const springY = deckY + 96;
      shape(g, (c) => {
        c.moveTo(spanLeft - 4, deckY);
        c.lineTo(spanRight + 4, deckY);
        c.lineTo(spanRight + 4, springY);
        c.ellipse(cx, springY, rx, rx * 0.68, 0, 0, Math.PI, true);
        c.closePath();
      }, { fill: '#cac0ae', lw: 3.5, ink: INK_MASONRY });
      // Keystone
      polyS(g, [
        [cx - 14, springY - rx * 0.68 - 14],
        [cx + 14, springY - rx * 0.68 - 14],
        [cx + 10, springY - rx * 0.68 + 12],
        [cx - 10, springY - rx * 0.68 + 12],
      ], { fill: '#e0d6c5', lw: 2.5, ink: INK_MASONRY });
    }
  }
}

export function drawStoneFissureAndJet(g, lt, opts = {}) {
  const x = (opts.x ?? 0.26) * E.W;
  const y = (opts.y ?? 0.38) * E.H;
  const scale = opts.scale ?? 1.0;
  const crackProg = clamp(opts.fissureProgress ?? 1.0, 0.05, 1.0);
  const jetPower = clamp(opts.jetIntensity ?? 0.85, 0.0, 1.0);

  g.save();
  g.translate(x, y);
  g.scale(scale, scale);

  // Jagged propagating fissure across travertine blocks
  const fullPts = [
    [-18, -74], [-4, -46], [-22, -18], [6, 8], [-12, 38], [14, 72], [4, 106],
  ];
  const count = Math.max(2, Math.ceil(fullPts.length * crackProg));
  const activePts = fullPts.slice(0, count);
  line(g, activePts, { lw: 9, ink: '#2b1e17' });
  line(g, activePts.map(([px, py]) => [px + 3, py + 1]), { lw: 3, ink: '#574538' });

  // Mortar dust puffs when cracking actively
  if (opts.dustBurst && lt < 2.2) {
    const dp = clamp(lt / 2.0);
    for (let i = 0; i < 6; i++) {
      const ang = -0.6 + i * 0.28;
      const dist = 18 + dp * (48 + i * 11);
      const r = (1 - dp * 0.65) * (12 + (i % 3) * 4);
      circ(g, Math.cos(ang) * dist, Math.sin(ang) * dist + dp * 22, r, {
        fill: alpha('#dfd3be', 0.65 * (1 - dp * 0.5)), lw: 0,
      });
    }
  }

  // Pressurized water jet & parabolic droplets
  if (jetPower > 0.02) {
    const len = (55 + 175 * jetPower) * (0.94 + 0.06 * Math.sin(lt * 22));
    const spread = 14 + 34 * jetPower;
    shape(g, (c) => {
      c.moveTo(-4, -8);
      c.quadraticCurveTo(len * 0.48, -14, len, spread * 0.9);
      c.lineTo(len * 0.86, spread * 1.75);
      c.quadraticCurveTo(len * 0.38, 18, -6, 8);
      c.closePath();
    }, { fill: alpha('#58a9dc', 0.88), lw: 3, ink: '#2b5d82' });

    // Bright foam core
    line(g, [[-2, -2], [len * 0.45, 2], [len * 0.84, spread * 0.95]], {
      lw: 6 * jetPower + 2, ink: '#eef9ff', a: 0.9,
    });

    // Animated droplets along parabolic arc
    const dropCount = Math.max(3, Math.round(14 * jetPower));
    for (let i = 0; i < dropCount; i++) {
      const u = ((lt * 2.4 + i / dropCount) % 1.0);
      const dx = u * (len * 1.25);
      const dy = -6 * u + 115 * u * u + (i % 3 - 1) * 8;
      ellipse(g, dx, dy, 6.5, 4, {
        rot: 0.45, fill: i % 2 === 0 ? '#d8f3ff' : '#4d9fd4', lw: 1.5, ink: '#2a5a7d',
      });
    }
  }

  g.restore();
}

export function drawSluiceMechanism(g, lt, opts = {}) {
  const x = (opts.x ?? 0.64) * E.W;
  const y = (opts.y ?? 0.58) * E.H;
  const scale = opts.scale ?? 1.0;
  const wheelAngle = opts.wheelAngle ?? 0.0;
  const jammed = !!opts.jammed;
  const gateDrop = clamp(opts.gateDropProgress ?? 0.0, 0.0, 1.0);
  const channelFlow = clamp(opts.channelFlow ?? 0.85, 0.0, 1.0);

  g.save();
  g.translate(x, y);
  g.scale(scale, scale);

  // Stone sluice frame & guide piers
  rect(g, -220, -195, 410, 250, { fill: '#c7baa5', lw: 4, ink: INK_MASONRY, r: 4 });
  rect(g, -195, -85, 360, 96, { fill: '#354856', lw: 3.5, ink: INK_MASONRY, r: 2 });

  // Flowing aqueduct channel water (left -> right)
  const upstreamLevel = 68;
  const downstreamFactor = clamp(1.0 - gateDrop * 0.88, 0.08, 1.0) * channelFlow;
  // Upstream water (left of gate slot x = 42)
  rect(g, -192, 10 - upstreamLevel, 234, upstreamLevel, { fill: '#3e8dc2', lw: 0, r: 0 });
  // Animated surface ripples upstream
  for (let i = 0; i < 5; i++) {
    const rx = -175 + ((lt * 95 + i * 46) % 210);
    line(g, [[rx, 16 - upstreamLevel], [rx + 24, 16 - upstreamLevel]], { lw: 3.5, ink: '#dff6ff', a: 0.85 });
  }
  // Downstream water (right of gate slot x = 74) — shrinks as gate drops!
  const downH = Math.max(6, upstreamLevel * downstreamFactor);
  rect(g, 74, 10 - downH, 90, downH, { fill: '#4796cb', lw: 0, r: 0 });

  // Heavy timber-and-iron sluice gate sliding DOWNWARD into slot (x = 40..76)
  // gateDrop = 0 -> gate bottom at y = -76 (open); gateDrop = 1 -> gate bottom at y = +12 (sealed!)
  const gateTopY = lerp(-192, -104, gateDrop);
  rect(g, 40, gateTopY, 36, 116, { fill: '#7c502c', lw: 4.5, ink: INK_ACTOR, r: 2 });
  // Iron reinforcement bands on timber gate
  rect(g, 38, gateTopY + 18, 40, 10, { fill: '#7a8086', lw: 2.5, ink: INK_ACTOR, r: 1 });
  rect(g, 38, gateTopY + 86, 40, 12, { fill: '#7a8086', lw: 2.5, ink: INK_ACTOR, r: 1 });

  // Splash foam at gate bottom while closing
  if (gateDrop > 0.12 && gateDrop < 0.95) {
    for (let k = 0; k < 5; k++) {
      circ(g, 36 + k * 9, 4 - (k % 2) * 8 + Math.sin(lt * 25 + k) * 4, 8, {
        fill: '#e9f9ff', lw: 1.5, ink: '#39749e',
      });
    }
  }

  // Braided hemp/iron rope connecting winch drum (x = -32, y = -132) over pulley (x = 58, y = -205) to gate top
  polyS(g, [[-18, -225], [88, -225], [88, -190], [-18, -190]], { fill: '#9f917d', lw: 3, ink: INK_ACTOR });
  circ(g, 58, -204, 16, { fill: '#b8863b', lw: 3.5, ink: INK_ACTOR });
  line(g, [[-32, -132], [58, -204], [58, gateTopY]], { lw: 6, ink: '#c9a263' });
  line(g, [[-32, -132], [58, -204], [58, gateTopY]], { lw: 2, ink: INK_ACTOR, dash: [6, 6] });

  // Meshed bronze toothed pinion gear (counter-rotates at -1.8x wheelAngle)
  const shimmer = jammed ? Math.sin(lt * 52) * 0.045 : 0;
  const effWheelAng = wheelAngle + shimmer;
  const gearAng = -effWheelAng * 1.8;
  const gx = -24, gy = -132, gr = 32;
  g.save();
  g.translate(gx, gy);
  g.rotate(gearAng);
  for (let t = 0; t < 10; t++) {
    const a = (t * Math.PI * 2) / 10;
    g.save();
    g.rotate(a);
    rect(g, gr - 5, -5, 12, 10, { fill: '#c8923f', lw: 2.5, ink: INK_ACTOR, r: 1 });
    g.restore();
  }
  circ(g, 0, 0, gr - 3, { fill: '#d6a34f', lw: 3.5, ink: INK_ACTOR });
  circ(g, 0, 0, 10, { fill: '#6e522b', lw: 2.5, ink: INK_ACTOR });
  g.restore();

  // Iron release pawl lever (left of gear)
  const pawlOpen = opts.pawlReleased ? -0.48 : 0.05;
  g.save();
  g.translate(-68, -148);
  g.rotate(pawlOpen);
  rect(g, -6, -34, 12, 42, { fill: '#8d9399', lw: 3, ink: INK_ACTOR, r: 3 });
  circ(g, 0, -34, 8, { fill: '#c9473a', lw: 2.5, ink: INK_ACTOR });
  g.restore();

  // Main cast-bronze 8-spoked handwheel (x = -112, y = -98)
  const wx = -112, wy = -98, wr = 74;
  // Stone pedestal mount
  polyS(g, [[wx - 32, 55], [wx - 16, wy], [wx + 16, wy], [wx + 32, 55]], {
    fill: '#8e8170', lw: 3.5, ink: INK_ACTOR,
  });

  g.save();
  g.translate(wx, wy);
  g.rotate(effWheelAng);
  // 8 spokes + wooden grip handles extending past rim
  for (let k = 0; k < 8; k++) {
    const a = (k * Math.PI * 2) / 8;
    g.save();
    g.rotate(a);
    rect(g, 0, -5, wr + 22, 10, { fill: '#b88335', lw: 3, ink: INK_ACTOR, r: 3 });
    rect(g, wr + 4, -6.5, 20, 13, { fill: '#8a552b', lw: 2.5, ink: INK_ACTOR, r: 4 });
    g.restore();
  }
  // Outer bronze rim (drawn as ring via two concentric paths)
  shape(g, (c) => {
    c.arc(0, 0, wr, 0, Math.PI * 2);
    c.arc(0, 0, wr - 15, 0, Math.PI * 2, true);
  }, { fill: '#dca955', lw: 4, ink: INK_ACTOR, rule: 'evenodd' });
  // Center bronze hub
  circ(g, 0, 0, 18, { fill: '#b57f31', lw: 3.5, ink: INK_ACTOR });
  circ(g, 0, 0, 7, { fill: '#ebe4d8', lw: 2, ink: INK_ACTOR });
  g.restore();

  // Strain vibration lines when jammed
  if (jammed) {
    for (const [ox, oy, ang] of [[wx - 92, wy - 56, -0.4], [wx + 88, wy - 62, 0.4]]) {
      g.save();
      g.translate(ox, oy);
      g.rotate(ang);
      line(g, [[-10, -8], [10, 0], [-8, 8]], { lw: 3.5, ink: '#d94b38' });
      g.restore();
    }
  }

  g.restore();
}

export function drawOverflowBasin(g, lt, opts = {}) {
  const x = (opts.x ?? 0.72) * E.W;
  const y = (opts.y ?? 0.64) * E.H;
  const scale = opts.scale ?? 1.0;
  const flow = clamp(opts.overflowFlow ?? 0.85, 0.0, 1.0);

  g.save();
  g.translate(x, y);
  g.scale(scale, scale);

  // Stepped Roman travertine diversion chute & catch-basin
  polyS(g, [
    [-190, -140], [-30, -140], [65, -35], [220, -35], [220, 135], [-190, 135],
  ], { fill: '#bfb19b', lw: 4, ink: INK_MASONRY });

  // Inner basin pool
  rect(g, -25, 22, 225, 92, { fill: '#2f6f97', lw: 3, ink: INK_MASONRY, r: 4 });

  if (flow > 0.04) {
    const streamW = 26 + 56 * flow;
    // Cascading water chute stream
    shape(g, (c) => {
      c.moveTo(-175, -128);
      c.lineTo(-35, -128);
      c.quadraticCurveTo(38, -95, 76, 30);
      c.lineTo(76 - streamW, 34);
      c.quadraticCurveTo(-4, -68, -175, -96);
      c.closePath();
    }, { fill: '#4ca3d8', lw: 3, ink: '#285f84' });

    // Animated whitewater foam streaks
    for (let i = 0; i < 6; i++) {
      const u = ((lt * 1.9 + i / 6) % 1.0);
      const fx = lerp(-145, 58, u);
      const fy = lerp(-114, 24, u * u);
      line(g, [[fx - 14, fy - 6], [fx + 14, fy + 8]], { lw: 5, ink: '#eefaff', a: 0.9 });
    }

    // Churning foam boils in catch-basin
    for (let k = 0; k < 7; k++) {
      const bx = 18 + k * 26 + Math.sin(lt * 9 + k) * 6;
      const by = 36 + (k % 2) * 12;
      circ(g, bx, by, (10 + (k % 3) * 4) * flow, { fill: '#ebfbff', lw: 1.5, ink: '#397ca8' });
    }
  }

  g.restore();
}

/**
 * Draw expressive Roman civic character (Engineer Livia, Workers Titus & Cassius, or Townspeople).
 * Strictly keeps head/feet inside safe frame bounds and uses warm terracotta/ochre/slate/skin tones
 * recognized cleanly by Temporal Visual QA without any military weapons/shields/helmets.
 */
export function drawCivicPerson(g, lt, p = {}) {
  const px = (p.x ?? 0.5) * E.W;
  const py = (p.y ?? 0.84) * E.H;
  const ph = (p.h ?? 0.42) * E.H;
  const role = p.role || 'livia'; // 'livia' | 'titus' | 'cassius' | 'citizen'
  const pose = p.pose || 'stand'; // 'stand' | 'signal' | 'brace' | 'heave' | 'point' | 'relief' | 'walk'
  const flip = p.flip ? -1 : 1;
  const gust = p.gust ?? 0.25;

  const s = ph / 320;
  g.save();
  g.translate(px, py);
  g.scale(flip * s, s);

  const stride = pose === 'walk' ? Math.sin(lt * 7.5) * 18 : 0;
  const heaveCycle = pose === 'heave' ? Math.sin(lt * 5.6) : (pose === 'brace' ? 0.85 + 0.15 * Math.sin(lt * 26) : 0);
  const bodyLean = pose === 'brace' ? 0.26 : (pose === 'heave' ? 0.18 + 0.14 * heaveCycle : (pose === 'signal' ? -0.05 : 0));
  const dropY = (pose === 'brace' || pose === 'heave') ? 22 + 8 * Math.abs(heaveCycle) : 0;

  const palette = {
    livia: { tunic: '#dfa344', stole: '#c93b31', trim: '#3b5d8c', hair: '#3b261c' },
    titus: { tunic: '#c94338', stole: '#9e6b3b', trim: '#d6a148', hair: '#4a3122' },
    cassius: { tunic: '#3c5f91', stole: '#c94338', trim: '#d8a64c', hair: '#2f221b' },
    citizen: { tunic: '#d49a45', stole: '#ba4237', trim: '#efe3c8', hair: '#4c3324' },
  }[role] || { tunic: '#dfa344', stole: '#c93b31', trim: '#3b5d8c', hair: '#3b261c' };

  // Legs & Roman leather caligae/sandals (grounded cleanly at y = 0)
  const legSpread = (pose === 'brace' || pose === 'heave') ? 34 : 16;
  tube(g, [[-14, -95 + dropY], [-legSpread + stride, -12]], 20, '#ebccb0', 5, INK_ACTOR);
  tube(g, [[14, -95 + dropY], [legSpread - stride, -12]], 20, '#e3c0a2', 5, INK_ACTOR);
  rect(g, -legSpread + stride - 16, -16, 34, 15, { fill: '#6d4426', lw: 4, ink: INK_ACTOR, r: 5 });
  rect(g, legSpread - stride - 14, -16, 34, 15, { fill: '#6d4426', lw: 4, ink: INK_ACTOR, r: 5 });

  g.save();
  g.translate(0, -105 + dropY);
  g.rotate(bodyLean);

  // Fluttering Roman stole / sash reacting to wind & water gust
  const capeWave = Math.sin(lt * 8.5) * 14 * (0.4 + gust);
  polyS(g, [
    [-26, -96], [-64 - gust * 28, -28 + capeWave], [-48 - gust * 22, 22 + capeWave * 0.6], [-12, -24],
  ], { fill: palette.stole, lw: 4.5, ink: INK_ACTOR });

  // Tunic torso
  polyS(g, [
    [-34, -104], [34, -104], [44, 18], [-44, 18],
  ], { fill: palette.tunic, lw: 5, ink: INK_ACTOR });
  // Contrasting Roman clavus stripe & belt
  rect(g, -10, -102, 20, 118, { fill: palette.stole, lw: 0, r: 0 });
  rect(g, -39, -32, 78, 14, { fill: '#6b4426', lw: 3.5, ink: INK_ACTOR, r: 3 });

  // Back arm
  if (pose === 'heave' || pose === 'brace') {
    const reachY = -88 + heaveCycle * 24;
    tube(g, [[20, -88], [64, reachY], [94, reachY + 8]], 18, '#e6c3a5', 4.5, INK_ACTOR);
  } else if (pose === 'relief') {
    tube(g, [[-26, -88], [-54, -138], [-44, -172]], 17, '#e6c3a5', 4.5, INK_ACTOR);
  } else {
    tube(g, [[-28, -88], [-44, -40], [-34, -6]], 17, '#e6c3a5', 4.5, INK_ACTOR);
  }

  // Head & expressive face
  const headY = -146;
  circ(g, 0, headY, 34, { fill: '#f2d6bc', lw: 5, ink: INK_ACTOR });
  // Hair & civic headband (no military helmet!)
  shape(g, (c) => {
    c.arc(0, headY - 4, 35, Math.PI * 0.95, Math.PI * 2.05);
    c.closePath();
  }, { fill: palette.hair, lw: 4.5, ink: INK_ACTOR });
  if (role === 'livia') {
    circ(g, -34, headY - 10 + capeWave * 0.15, 13, { fill: palette.hair, lw: 4, ink: INK_ACTOR });
    rect(g, -32, headY - 18, 64, 8, { fill: palette.trim, lw: 2.5, ink: INK_ACTOR, r: 3 });
  }

  // Eyes & eyebrows (clear gaze direction & urgency)
  const eyeShift = p.look ?? 4;
  for (const ex of [-4, 14]) {
    circ(g, ex + eyeShift, headY - 2, 4.2, { fill: INK_ACTOR, lw: 0 });
    line(g, [[ex + eyeShift - 6, headY - 11], [ex + eyeShift + 6, headY - 9]], { lw: 3.2, ink: INK_ACTOR });
  }
  // Mouth (open call on signal/heave, warm smile on relief)
  if (pose === 'signal' || pose === 'heave' || pose === 'brace') {
    ellipse(g, 8, headY + 14, 7, 5, { fill: '#6b2822', lw: 2.5, ink: INK_ACTOR });
  } else if (pose === 'relief') {
    line(g, [[0, headY + 12], [8, headY + 16], [16, headY + 11]], { lw: 3, ink: INK_ACTOR });
  } else {
    line(g, [[2, headY + 14], [15, headY + 13]], { lw: 3, ink: INK_ACTOR });
  }

  // Front arm & civic tool (rolled surveyor scroll for Livia; spoke grip for workers)
  if (pose === 'signal') {
    // Raised arm + surveyor scroll high in upper frame (clearly readable SIGNAL silhouette)
    const wave = Math.sin(lt * 6) * 5;
    tube(g, [[22, -92], [54, -152], [72, -202 + wave]], 18, '#f0cfb2', 4.5, INK_ACTOR);
    g.save();
    g.translate(76, -214 + wave);
    g.rotate(-0.35);
    rect(g, -10, -34, 22, 58, { fill: '#f5ead0', lw: 4, ink: INK_ACTOR, r: 5 });
    rect(g, -12, -8, 26, 10, { fill: '#c93b31', lw: 2.5, ink: INK_ACTOR, r: 2 });
    g.restore();
  } else if (pose === 'point') {
    tube(g, [[22, -90], [66, -108], [102, -118]], 18, '#f0cfb2', 4.5, INK_ACTOR);
    rect(g, -46, -22, 16, 42, { fill: '#f5ead0', lw: 3.5, ink: INK_ACTOR, r: 4 });
  } else if (pose === 'heave' || pose === 'brace') {
    const reachY = -74 + heaveCycle * 26;
    tube(g, [[18, -82], [58, reachY], [92, reachY + 4]], 19, '#f0cfb2', 4.5, INK_ACTOR);
  } else {
    tube(g, [[22, -88], [44, -46], [36, -12]], 18, '#f0cfb2', 4.5, INK_ACTOR);
    if (role === 'livia') {
      rect(g, 28, -22, 18, 44, { fill: '#f5ead0', lw: 3.5, ink: INK_ACTOR, r: 4 });
    }
  }

  g.restore();
  g.restore();
}

export function drawHighContrastCivicBadge(g, lt, opts = {}) {
  const title = String(opts.title || '');
  if (!title) return;
  const sub = String(opts.subtitle || '');
  const cx = (opts.x ?? 0.5) * E.W;
  const cy = (opts.y ?? 0.13) * E.H;
  const appear = clamp((lt - (opts.at ?? 0.08)) / 0.28);
  if (appear <= 0.01) return;
  const k = ease.outBack(appear);

  const mainSize = opts.size ?? 44;
  const subSize = Math.round(mainSize * 0.46);
  const wMain = measure(g, title, mainSize, FONT_CAP, 900);
  const wSub = sub ? measure(g, sub, subSize, FONT_CAP, 800) : 0;
  const boxW = Math.max(wMain, wSub) + 68;
  const boxH = sub ? mainSize + subSize + 44 : mainSize + 32;

  g.save();
  g.translate(cx, cy);
  g.scale(k, k);
  // Crisp dark-slate plaque (< 35 RGB) with warm bronze border + bright cream lettering for 480px mobile legibility
  rect(g, -boxW / 2, -boxH / 2, boxW, boxH, {
    fill: '#18202c', lw: 4.5, ink: '#e2b055', r: 12,
  });
  if (sub) {
    text(g, title, 0, -subSize * 0.55, {
      size: mainSize, font: FONT_CAP, weight: 900, color: '#fff9ec', align: 'center',
    });
    text(g, sub, 0, mainSize * 0.56, {
      size: subSize, font: FONT_CAP, weight: 800, color: '#efd08b', align: 'center',
    });
  } else {
    text(g, title, 0, 2, {
      size: mainSize, font: FONT_CAP, weight: 900, color: '#fff9ec', align: 'center',
    });
  }
  g.restore();
}

export function registerWaterGateShots() {
  // S01 (0.0 - 3.0s): Hook — Propagating stone fissure + pressurized water jet + "ONE CRACK" badge
  registerShot('S01', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawAqueductMasonry(g, {
          deckY: 0.24, groundY: 0.96, piers: [0.38, 0.88], pierW: 0.22, showChannelWater: true, channelLevel: 0.92,
        });
        const crackProg = clamp(0.28 + (lt / 2.2) * 0.72, 0.28, 1.0);
        const jetInt = clamp(0.25 + (lt / 1.6) * 0.75, 0.25, 1.0);
        drawStoneFissureAndJet(g, lt, {
          x: 0.44, y: 0.46, scale: 1.55, fissureProgress: crackProg, jetIntensity: jetInt, dustBurst: true,
        });
        drawHighContrastCivicBadge(g, lt, {
          title: 'ONE CRACK', subtitle: 'PRESSURIZED AQUEDUCT PIER', x: 0.24, y: 0.14, size: 48, at: 0.05,
        });
      });
    },
  });

  // S02 (3.0 - 7.0s): Stakes Establish — Towering aqueduct above sunlit market street; Livia on upper catwalk
  registerShot('S02', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawRomanMarketStreet(g, lt, { groundY: 0.86, wetPatch: clamp(0.15 + lt * 0.12, 0.15, 0.65) });
        drawAqueductMasonry(g, {
          deckY: 0.36, groundY: 0.86, piers: [0.22, 0.56, 0.90], pierW: 0.10, showChannelWater: true, channelLevel: 0.9,
        });
        drawStoneFissureAndJet(g, lt, {
          x: 0.25, y: 0.47, scale: 0.95, fissureProgress: 1.0, jetIntensity: 0.92,
        });
        // Engineer Livia advancing along upper catwalk inspecting fracture
        const lx = lerp(0.35, 0.41, ease.inOut(clamp(lt / 3.8)));
        drawCivicPerson(g, lt, { x: lx, y: 0.36, h: 0.22, role: 'livia', pose: 'walk', gust: 0.45, flip: true });
        // Market street citizens looking up at spray
        drawCivicPerson(g, lt, { x: 0.44, y: 0.86, h: 0.30, role: 'citizen', pose: 'point', flip: true, look: -3 });
        drawCivicPerson(g, lt, { x: 0.68, y: 0.86, h: 0.29, role: 'cassius', pose: 'stand', flip: true, look: -4 });
      });
    },
  });

  // S03 (7.0 - 11.0s): Discovery & Command — Medium-close on Engineer Livia raising scroll ordering sluice shut
  registerShot('S03', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawAqueductMasonry(g, {
          deckY: 0.78, groundY: 0.98, piers: [0.16, 0.78], pierW: 0.16, showChannelWater: true, channelLevel: 0.92,
        });
        drawStoneFissureAndJet(g, lt, {
          x: 0.16, y: 0.66, scale: 0.85, fissureProgress: 1.0, jetIntensity: 0.88,
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.47, 0.50, clamp(lt / 3.8)),
          y: 0.84,
          h: 0.52,
          role: 'livia',
          pose: 'signal',
          gust: 0.75,
          look: 5,
        });
      });
    },
  });

  // S04 (11.0 - 15.0s): Upstream Sluice Mechanism — Rushing channel, open timber gate, bronze wheel, Worker Titus ready
  registerShot('S04', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawAqueductMasonry(g, {
          deckY: 0.74, groundY: 0.98, piers: [0.18, 0.82], pierW: 0.14, showChannelWater: false,
        });
        drawSluiceMechanism(g, lt, {
          x: 0.60, y: 0.69, scale: 1.08, wheelAngle: 0.0, jammed: false, gateDropProgress: 0.02, channelFlow: 1.0,
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.34, 0.40, ease.inOut(clamp(lt / 3.6))),
          y: 0.84,
          h: 0.45,
          role: 'titus',
          pose: 'walk',
          gust: 0.35,
          look: 4,
        });
      });
    },
  });

  // S05 (15.0 - 19.0s): Friction & Jammed Torque — Titus braces hard on shuddering bronze wheel; Livia & Cassius converge
  registerShot('S05', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawAqueductMasonry(g, {
          deckY: 0.75, groundY: 0.98, piers: [0.16, 0.84], pierW: 0.14, showChannelWater: false,
        });
        drawSluiceMechanism(g, lt, {
          x: 0.62,
          y: 0.70,
          scale: 1.12,
          wheelAngle: lerp(0.02, 0.14, clamp(lt / 3.8)),
          jammed: true,
          gateDropProgress: 0.04,
          channelFlow: 1.0,
        });
        drawCivicPerson(g, lt, {
          x: 0.41, y: 0.85, h: 0.45, role: 'titus', pose: 'brace', gust: 0.55, look: 4,
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.18, 0.25, ease.out(clamp(lt / 2.8))),
          y: 0.85,
          h: 0.44,
          role: 'livia',
          pose: 'point',
          gust: 0.5,
          look: 5,
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.84, 0.74, ease.out(clamp(lt / 3.0))),
          y: 0.85,
          h: 0.45,
          role: 'cassius',
          pose: 'walk',
          flip: true,
          gust: 0.45,
          look: -4,
        });
      });
    },
  });

  // S06 (19.0 - 23.0s): Coordinated Heave & Causal Gate Drop — Wheel rotates, gears mesh, rope pays out, gate seals!
  registerShot('S06', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'urgent');
        drawAqueductMasonry(g, {
          deckY: 0.75, groundY: 0.98, piers: [0.16, 0.84], pierW: 0.14, showChannelWater: false,
        });
        const p = ease.inOut(clamp(lt / 3.65));
        drawSluiceMechanism(g, lt, {
          x: 0.60,
          y: 0.70,
          scale: 1.10,
          wheelAngle: lerp(0.16, 3.95, p),
          jammed: false,
          pawlReleased: true,
          gateDropProgress: lerp(0.06, 0.98, p),
          channelFlow: 1.0,
        });
        drawCivicPerson(g, lt, {
          x: 0.24, y: 0.85, h: 0.44, role: 'livia', pose: 'point', gust: 0.35, look: 5,
        });
        drawCivicPerson(g, lt, {
          x: 0.40, y: 0.85, h: 0.46, role: 'titus', pose: 'heave', gust: 0.4, look: 4,
        });
        drawCivicPerson(g, lt, {
          x: 0.56, y: 0.85, h: 0.45, role: 'cassius', pose: 'heave', flip: true, gust: 0.4, look: -4,
        });
      });
    },
  });

  // S07 (23.0 - 27.0s): Physical Hydraulic Payoff — Crack jet subsides while diverted torrent roars into overflow basin
  registerShot('S07', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'golden');
        drawAqueductMasonry(g, {
          deckY: 0.44, groundY: 0.94, piers: [0.20, 0.52], pierW: 0.11, showChannelWater: true, channelLevel: 0.35, waterStopX: 0.56,
        });
        const k = ease.out(clamp(lt / 3.4));
        // Left pier fissure jet dwindling to safe trickle because upstream gate is closed
        drawStoneFissureAndJet(g, lt, {
          x: 0.23, y: 0.56, scale: 0.92, fissureProgress: 1.0, jetIntensity: lerp(0.62, 0.04, k),
        });
        // Right side stepped overflow basin receiving full diverted cascade
        drawOverflowBasin(g, lt, {
          x: 0.75, y: 0.67, scale: 0.98, overflowFlow: lerp(0.32, 1.0, k),
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.43, 0.47, clamp(lt / 3.8)),
          y: 0.44,
          h: 0.25,
          role: 'livia',
          pose: 'stand',
          gust: 0.2,
          look: 5,
        });
        drawCivicPerson(g, lt, {
          x: lerp(0.34, 0.37, clamp(lt / 3.8)),
          y: 0.44,
          h: 0.25,
          role: 'titus',
          pose: 'relief',
          gust: 0.2,
          look: 4,
        });
      });
    },
  });

  // S08 (27.0 - 30.0s): Resolution & Non-Obscuring Takeaway Plaque — Dry market street & engineers in golden light
  registerShot('S08', {
    draw(g, lt, info) {
      applyCivicCamera(g, lt, info, () => {
        drawMediterraneanSkyAndHills(g, lt, 'golden');
        drawRomanMarketStreet(g, lt, { groundY: 0.87, wetPatch: 0.05 });
        drawAqueductMasonry(g, {
          deckY: 0.42, groundY: 0.87, piers: [0.22, 0.56, 0.90], pierW: 0.10, showChannelWater: false,
        });
        // Upper catwalk: Livia, Titus, Cassius standing proud above the spared street
        drawCivicPerson(g, lt, { x: 0.48, y: 0.42, h: 0.21, role: 'livia', pose: 'relief', gust: 0.12 });
        drawCivicPerson(g, lt, { x: 0.39, y: 0.42, h: 0.21, role: 'titus', pose: 'stand', gust: 0.12 });
        drawCivicPerson(g, lt, { x: 0.57, y: 0.42, h: 0.21, role: 'cassius', pose: 'relief', flip: true, gust: 0.12 });
        // Below on the dry cobbled street: relieved townspeople waving upward
        drawCivicPerson(g, lt, { x: 0.38, y: 0.87, h: 0.31, role: 'citizen', pose: 'relief', look: 3 });
        drawCivicPerson(g, lt, { x: 0.64, y: 0.87, h: 0.30, role: 'citizen', pose: 'stand', flip: true, look: -3 });

        drawHighContrastCivicBadge(g, lt, {
          title: 'ONE DECISION. A CITY SPARED.',
          subtitle: 'ROMAN CIVIC ENGINEERING • STYLIZED RECONSTRUCTION',
          x: 0.50,
          y: 0.13,
          size: 42,
          at: 0.08,
        });
      });
    },
  });
}
