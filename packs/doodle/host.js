// host.js — nhan vat doodle dau tron (nguoi dan chuyen "minh") va cac vai phu: nha khoa hoc, khao co, nguoi tien su...
// guy(g, x, yChan, chieuCao, opts)   head(g, x, y, R, opts)   CAST: bo nhan vat dung san.
import { E, clamp, lerp, ease, noise, rng } from '/engine/core.js';
import { INK, PAL, shape, circ, ellipse, line, tube, blob, poly, rect, smoothPath, shadow } from './ink.js';

// ---------- bo nhan vat dung san (sua mau / them vai trong scenes/cast.js cua du an)
export const CAST = {
  host:          { skin: '#ffffff', shirt: PAL.shirt, pants: '#5b5f6a', shoes: '#3a3a40', hands: 'glove' },
  scientist:     { skin: PAL.skin, hair: 'messy', hairColor: '#4a3a30', glasses: true, outfit: 'coat', shirt: '#cfe3d4', pants: '#4b4f58' },
  scientistF:    { skin: PAL.skin, hair: 'bob', hairColor: '#2b2420', outfit: 'coat', shirt: '#f2d7a8', pants: '#4b4f58' },
  archaeologist: { skin: PAL.skin, hair: 'bun', hairColor: '#9a948c', glasses: true, hat: 'pith', outfit: 'shirt', shirt: '#f3efe2', pants: '#8f7a55', shoes: '#6b4b2e' },
  explorer:      { skin: PAL.skin, hair: 'short', hairColor: '#5a3e2b', hat: 'safari', outfit: 'shirt', shirt: '#c9b98f', pants: '#7a6a4a', shoes: '#5a3e2b' },
  farmer:        { skin: PAL.skinTan, hair: 'short', hairColor: PAL.hair, hat: 'nonla', outfit: 'shirt', shirt: '#f1e6cf', pants: '#8b5e3c', shoes: '#4a3a2a' },
  caveman:       { skin: PAL.skinBrown, hair: 'wild', hairColor: '#2a1d16', outfit: 'pelt', pants: PAL.skinBrown, shoes: null, hands: 'skin' },
  cavewoman:     { skin: PAL.skinBrown, hair: 'long', hairColor: '#2a1d16', outfit: 'pelt', pants: PAL.skinBrown, shoes: null, hands: 'skin' },
  kid:           { skin: PAL.skin, hair: 'short', hairColor: PAL.hair, shirt: '#f2c66d', pants: '#5b7fa6', kid: true, hands: 'skin' },
  elder:         { skin: PAL.skin, hair: 'bald', hairColor: PAL.hairGrey, beard: 'long', beardColor: '#e9e5de', outfit: 'robe', shirt: '#e8dcc4', hands: 'skin' },
  greek:         { skin: PAL.skinTan, hair: 'curly', hairColor: '#cfc8bd', beard: 'full', beardColor: '#cfc8bd', outfit: 'robe', shirt: '#f7f3ea', hands: 'skin', shoes: '#8a6a45' },
  craftsman:     { skin: '#b9c6d6', hair: 'tuft', hairColor: PAL.hair, brows: 'thick', outfit: 'apron', shirt: '#f3efe6', apron: '#8a5a33', pants: '#4b4f58', hands: 'glove' },
  king:          { skin: PAL.skin, hair: 'short', hairColor: PAL.hair, beard: 'goatee', beardColor: PAL.hair, hat: 'crown', outfit: 'robe', shirt: '#d9a73c', hands: 'skin' },
  soldier:       { skin: PAL.skinTan, hair: 'short', hairColor: PAL.hair, hat: 'helmet', outfit: 'shirt', shirt: '#7c8a5a', pants: '#5d6844', shoes: '#3a3a30', hands: 'skin' },
};

// tu the: goc tay (rad, 0 = buong thang xuong, + = giang ra ngoai), [canhTay, cangTay] cho tay trai (L, phia trai man hinh) va phai (R)
export const POSES = {
  stand:   { L: [0.18, 0.08], R: [0.18, 0.08] },
  wave:    { L: [0.18, 0.08], R: [2.5, 2.95] },
  point:   { L: [0.18, 0.08], R: [1.45, 1.55] },
  pointL:  { L: [1.45, 1.55], R: [0.18, 0.08] },
  pointUp: { L: [0.18, 0.08], R: [2.9, 3.05] },
  shrug:   { L: [0.55, 2.0], R: [0.55, 2.0] },
  think:   { L: [0.18, 0.08], R: [-0.25, -2.65] },
  cheer:   { L: [2.45, 2.8], R: [2.45, 2.8] },
  hips:    { L: [0.6, -0.55], R: [0.6, -0.55] },
  present: { L: [0.18, 0.08], R: [0.95, 1.5] },
  presentL:{ L: [0.95, 1.5], R: [0.18, 0.08] },
  hold:    { L: [0.18, 0.08], R: [0.25, 1.45] },
  holdBoth:{ L: [0.25, 1.35], R: [0.25, 1.35] },
  write:   { L: [0.05, 1.25], R: [-0.05, 1.05] },
  facepalm:{ L: [0.18, 0.08], R: [-0.15, -2.85] },
  scared:  { L: [0.5, 2.6], R: [0.5, 2.6] },
  stop:    { L: [0.18, 0.08], R: [1.2, 2.3] },
};

// ---------- dau: R ban kinh, opts: skin, face, look [-1..1], lookY, talk 0..1, blink, hair, hat, glasses, beard
export function head(g, x, y, R, o = {}) {
  const skin = o.skin || '#ffffff', lw = Math.max(3, R * 0.075);
  const lx = (o.look || 0) * R * 0.22, ly = (o.lookY || 0) * R * 0.15;
  if (o.hair === 'long' || o.hair === 'bob') blob(g, [[x - R * 1.05, y - R * 0.2], [x - R * 0.9, y + (o.hair === 'long' ? R * 1.25 : R * 0.65)], [x + R * 0.9, y + (o.hair === 'long' ? R * 1.25 : R * 0.65)], [x + R * 1.05, y - R * 0.2], [x, y - R * 1.15]], { fill: o.hairColor || PAL.hair, lw });
  if (o.hair === 'wild') blob(g, Array.from({ length: 11 }, (_, i) => { const a = Math.PI * (0.95 + i * 0.11); const r = R * (1.18 + 0.12 * ((i * 7) % 3)); return [x + Math.cos(a) * r, y + Math.sin(a) * r * 0.95 + R * 0.05]; }).concat([[x + R * 1.05, y + R * 0.5], [x - R * 1.05, y + R * 0.5]]), { fill: o.hairColor || PAL.hair, lw });
  circ(g, x, y, R, { fill: skin, lw });
  // toc tren dinh
  const hc = o.hairColor || PAL.hair;
  if (o.hair === 'short') shape(g, (c) => { c.moveTo(x - R * 0.95, y - R * 0.25); c.bezierCurveTo(x - R * 0.9, y - R * 1.2, x + R * 0.9, y - R * 1.2, x + R * 0.95, y - R * 0.25); c.quadraticCurveTo(x + R * 0.3, y - R * 0.6, x - R * 0.95, y - R * 0.25); }, { fill: hc, lw: lw * 0.8 });
  if (o.hair === 'messy') shape(g, (c) => { c.moveTo(x - R * 0.97, y - R * 0.15); [[-0.8, -0.95], [-0.45, -0.75], [-0.25, -1.15], [0.05, -0.8], [0.3, -1.12], [0.5, -0.78], [0.82, -0.98], [0.97, -0.2]].forEach(([a, b]) => c.lineTo(x + a * R, y + b * R)); c.quadraticCurveTo(x, y - R * 0.55, x - R * 0.97, y - R * 0.15); }, { fill: hc, lw: lw * 0.8 });
  if (o.hair === 'curly') for (let i = 0; i < 7; i++) { const a = Math.PI * (1.05 + i * 0.15); circ(g, x + Math.cos(a) * R * 0.92, y + Math.sin(a) * R * 0.92, R * 0.22, { fill: hc, lw: lw * 0.6 }); }
  if (o.hair === 'bun') { circ(g, x, y - R * 1.05, R * 0.3, { fill: hc, lw: lw * 0.8 }); shape(g, (c) => { c.arc(x, y, R, Math.PI * 1.08, Math.PI * 1.92); c.quadraticCurveTo(x, y - R * 0.55, x - R * 0.97, y - R * 0.25); }, { fill: hc, lw: lw * 0.8 }); }
  if (o.hair === 'bob' || o.hair === 'long') shape(g, (c) => { c.arc(x, y, R, Math.PI * 1.02, Math.PI * 1.98); c.quadraticCurveTo(x + R * 0.2, y - R * 0.35, x - R * 0.2, y - R * 0.7); c.quadraticCurveTo(x - R * 0.5, y - R * 0.3, x - R * 0.99, y - R * 0.1); }, { fill: hc, lw: lw * 0.8 });
  if (o.hair === 'wild') shape(g, (c) => { c.arc(x, y, R, Math.PI * 1.0, Math.PI * 2.0); [[0.7, -0.45], [0.4, -0.25], [0.15, -0.5], [-0.15, -0.28], [-0.45, -0.5], [-0.75, -0.3]].forEach(([a, b]) => c.lineTo(x + a * R, y + b * R)); c.closePath(); }, { fill: hc, lw: lw * 0.8 });
  if (o.hair === 'tuft') for (let i = -1; i <= 1; i++) line(g, [[x + i * R * 0.12, y - R * 0.98], [x + i * R * 0.22, y - R * 1.28]], { lw: lw * 0.7 });
  if (o.hair === 'bald') { shape(g, (c) => c.arc(x - R * 0.92, y, R * 0.3, Math.PI * 0.5, Math.PI * 1.5), { fill: hc, lw: lw * 0.7 }); shape(g, (c) => c.arc(x + R * 0.92, y, R * 0.3, -Math.PI * 0.5, Math.PI * 0.5), { fill: hc, lw: lw * 0.7 }); }
  // rau
  if (o.beard === 'full' || o.beard === 'long') blob(g, [[x - R * 0.85, y + R * 0.15], [x - R * 0.6, y + R * (o.beard === 'long' ? 1.5 : 1.15)], [x, y + R * (o.beard === 'long' ? 1.75 : 1.3)], [x + R * 0.6, y + R * (o.beard === 'long' ? 1.5 : 1.15)], [x + R * 0.85, y + R * 0.15], [x, y + R * 0.55]], { fill: o.beardColor || PAL.hairGrey, lw: lw * 0.8 });
  if (o.beard === 'goatee') blob(g, [[x - R * 0.2, y + R * 0.7], [x, y + R * 1.15], [x + R * 0.2, y + R * 0.7]], { fill: o.beardColor || PAL.hair, lw: lw * 0.6 });
  // mat
  face(g, x + lx, y + ly, R, o, lw);
  // kinh
  if (o.glasses) { [-1, 1].forEach((s) => circ(g, x + lx + s * R * 0.34, y + ly - R * 0.05, R * 0.24, { fill: 'rgba(255,255,255,0.25)', lw: lw * 0.75 })); line(g, [[x + lx - R * 0.1, y + ly - R * 0.07], [x + lx + R * 0.1, y + ly - R * 0.07]], { lw: lw * 0.6 }); }
  // mu
  if (o.hat === 'nonla') poly(g, [[x - R * 1.55, y - R * 0.45], [x, y - R * 1.75], [x + R * 1.55, y - R * 0.45]], { fill: '#e8d39a', lw }), line(g, [[x - R * 0.7, y - R * 0.7], [x + R * 0.7, y - R * 0.7]], { lw: lw * 0.4, ink: '#b49a5c' });
  if (o.hat === 'pith' || o.hat === 'safari') { ellipse(g, x, y - R * 0.62, R * 1.35, R * 0.22, { fill: o.hat === 'pith' ? '#e9dcb6' : '#b8a477', lw }); shape(g, (c) => { c.ellipse(x, y - R * 0.66, R * 0.85, R * 0.75, 0, Math.PI, 0); c.closePath(); }, { fill: o.hat === 'pith' ? '#efe4c4' : '#c9b78a', lw }); line(g, [[x - R * 0.82, y - R * 0.72], [x + R * 0.82, y - R * 0.72]], { lw: lw * 0.9, ink: '#7a5a3a' }); }
  if (o.hat === 'crown') poly(g, [[x - R * 0.7, y - R * 0.75], [x - R * 0.75, y - R * 1.45], [x - R * 0.35, y - R * 1.1], [x, y - R * 1.55], [x + R * 0.35, y - R * 1.1], [x + R * 0.75, y - R * 1.45], [x + R * 0.7, y - R * 0.75]], { fill: PAL.gold, lw });
  if (o.hat === 'helmet') shape(g, (c) => { c.ellipse(x, y - R * 0.45, R * 1.1, R * 0.75, 0, Math.PI, 0); c.closePath(); }, { fill: '#6d7a4a', lw });
  if (o.hat === 'cap') { shape(g, (c) => { c.ellipse(x, y - R * 0.5, R * 0.98, R * 0.7, 0, Math.PI, 0); c.closePath(); }, { fill: o.hatColor || PAL.red, lw }); ellipse(g, x + R * 0.6, y - R * 0.5, R * 0.6, R * 0.12, { fill: o.hatColor || PAL.red, lw: lw * 0.8 }); }
  if (o.sweat) { const sx = x + R * 0.95, sy = y - R * 0.35; shape(g, (c) => { c.moveTo(sx, sy - R * 0.25); c.quadraticCurveTo(sx + R * 0.16, sy, sx, sy + R * 0.08); c.quadraticCurveTo(sx - R * 0.16, sy, sx, sy - R * 0.25); }, { fill: '#9fd3f0', lw: lw * 0.6 }); }
}

// bieu cam: neutral happy smile surprised shock worried sad thinking smirk angry scared sleepy proud
function face(g, x, y, R, o, lw) {
  const ex = R * 0.34, ey = -R * 0.05, er = R * 0.085, fc = o.face || 'neutral', ink = INK;
  const t = (o.t ?? 0) + (o.seed || 0) * 1.37;
  const blinking = o.blink !== false && ((t % 3.7) < 0.12 || fc === 'sleepy');
  const brows = (yy, ang, len = 0.3, th = o.brows === 'thick' ? 1.9 : 1) => [-1, 1].forEach((s) => {
    const cx = x + s * ex, cy = y + yy * R, a = ang * s;
    line(g, [[cx - Math.cos(a) * R * len / 2, cy - Math.sin(a) * R * len / 2], [cx + Math.cos(a) * R * len / 2, cy + Math.sin(a) * R * len / 2]], { lw: lw * 0.75 * th, smooth: false });
  });
  // mat
  if (blinking) [-1, 1].forEach((s) => line(g, [[x + s * ex - er * 1.4, y + ey], [x + s * ex + er * 1.4, y + ey]], { lw: lw * 0.7 }));
  else if (fc === 'happy' || fc === 'proud') [-1, 1].forEach((s) => line(g, [[x + s * ex - er * 1.6, y + ey + er * 0.6], [x + s * ex, y + ey - er * 0.9], [x + s * ex + er * 1.6, y + ey + er * 0.6]], { lw: lw * 0.75 }));
  else if (fc === 'shock' || fc === 'scared') [-1, 1].forEach((s) => { circ(g, x + s * ex, y + ey, er * 2.4, { fill: '#fff', lw: lw * 0.6 }); circ(g, x + s * ex, y + ey, er * 0.9, { fill: ink, lw: 0 }); });
  else { const big = fc === 'surprised' ? 1.3 : 1; [-1, 1].forEach((s) => circ(g, x + s * ex, y + ey + (fc === 'thinking' ? -er * 0.8 : 0), er * big, { fill: ink, lw: 0 })); }
  // long may
  if (fc === 'surprised' || fc === 'shock') brows(-0.42, 0, 0.32);
  else if (fc === 'worried' || fc === 'sad' || fc === 'scared') brows(-0.36, -0.35);
  else if (fc === 'angry') brows(-0.32, 0.4);
  else if (fc === 'thinking') { line(g, [[x - ex - R * 0.15, y - R * 0.32], [x - ex + R * 0.15, y - R * 0.3]], { lw: lw * 0.75 }); line(g, [[x + ex - R * 0.15, y - R * 0.38], [x + ex, y - R * 0.46], [x + ex + R * 0.15, y - R * 0.4]], { lw: lw * 0.75 }); }
  else if (o.brows === 'thick') brows(-0.36, 0.1);
  // mieng
  const my = y + R * 0.4, talk = clamp(o.talk || 0);
  if (talk > 0.06) { ellipse(g, x, my, R * (0.12 + talk * 0.06), R * (0.05 + talk * 0.16), { fill: '#7a2e2a', lw: lw * 0.6 }); return; }
  if (fc === 'happy' || fc === 'proud') shape(g, (c) => { c.moveTo(x - R * 0.26, my - R * 0.06); c.quadraticCurveTo(x, my + R * 0.42, x + R * 0.26, my - R * 0.06); c.closePath(); }, { fill: '#7a2e2a', lw: lw * 0.6 });
  else if (fc === 'surprised') circ(g, x, my + R * 0.03, R * 0.075, { fill: '#fff', lw: lw * 0.6 });
  else if (fc === 'shock') ellipse(g, x, my + R * 0.05, R * 0.13, R * 0.18, { fill: '#7a2e2a', lw: lw * 0.6 });
  else if (fc === 'sad' || fc === 'angry') line(g, [[x - R * 0.17, my + R * 0.08], [x, my - R * 0.02], [x + R * 0.17, my + R * 0.08]], { lw: lw * 0.7 });
  else if (fc === 'worried' || fc === 'scared') line(g, [[x - R * 0.2, my + R * 0.04], [x - R * 0.1, my - R * 0.03], [x, my + R * 0.04], [x + R * 0.1, my - R * 0.03], [x + R * 0.2, my + R * 0.04]], { lw: lw * 0.6 });
  else if (fc === 'thinking') line(g, [[x - R * 0.05, my + R * 0.02], [x + R * 0.2, my - R * 0.02]], { lw: lw * 0.7, smooth: false });
  else if (fc === 'smirk') line(g, [[x - R * 0.15, my + R * 0.02], [x + R * 0.08, my + R * 0.04], [x + R * 0.2, my - R * 0.06]], { lw: lw * 0.7 });
  else if (fc === 'sleepy') line(g, [[x - R * 0.1, my], [x + R * 0.1, my]], { lw: lw * 0.7 });
  else line(g, [[x - R * 0.16, my - R * 0.01], [x, my + R * 0.07], [x + R * 0.16, my - R * 0.01]], { lw: lw * 0.7 });
}

// ---------- ca nguoi. y = mat dat (chan). h = chieu cao. opts: preset (ten trong CAST) hoac cac truong o tren + pose, face, look, talk, prop, propR, walk, flip, t
export function guy(g, x, y, h, opts = {}) {
  const o = { ...(CAST[opts.preset || 'host'] || CAST.host), ...opts };
  const kid = o.kid ? 0.78 : 1; h *= kid;
  const t = o.t ?? 0, br = Math.sin(t * 2.4 + (o.seed || 0)) * h * 0.004;
  const R = h * (o.kid ? 0.2 : 0.165), lw = Math.max(3, h * 0.012);
  const legL = h * 0.32, hipY = y - legL, torsoH = h * 0.28, shY = hipY - torsoH + br, headY = shY - R * 0.78 + br;
  const sw = h * 0.105, armW = h * 0.034, legW = h * 0.07;
  const pose = typeof o.pose === 'object' ? o.pose : (POSES[o.pose] || POSES.stand);
  g.save();
  if (o.flip) { g.translate(x, 0); g.scale(-1, 1); g.translate(-x, 0); }
  shadow(g, x, y + h * 0.005, h * 0.36);
  // chan
  const wk = o.walk ? Math.sin((t * (o.walkSpeed || 1.8)) * Math.PI * 2) : 0;
  const footL = [x - h * 0.06 + wk * h * 0.07, y - Math.max(0, -wk) * h * 0.02], footR = [x + h * 0.06 - wk * h * 0.07, y - Math.max(0, wk) * h * 0.02];
  const legCol = o.outfit === 'pelt' ? o.skin : (o.pants || '#5b5f6a');
  if (o.outfit !== 'robe') {
    tube(g, [[x - h * 0.05, hipY], footL], legW, legCol, { border: lw * 0.9, smooth: false });
    tube(g, [[x + h * 0.05, hipY], footR], legW, legCol, { border: lw * 0.9, smooth: false });
  }
  if (o.shoes !== null) [footL, footR].forEach((f, i) => ellipse(g, f[0] + (i ? 1 : -1) * h * 0.02, f[1] - h * 0.012, h * 0.055, h * 0.028, { fill: o.shoes || '#3a3a40', lw: lw * 0.8 }));
  else [footL, footR].forEach((f, i) => ellipse(g, f[0] + (i ? 1 : -1) * h * 0.015, f[1] - h * 0.012, h * 0.045, h * 0.022, { fill: o.skin, lw: lw * 0.8 }));
  // than
  const shirt = o.shirt || PAL.shirt;
  const torso = (c, bot = hipY + h * 0.03, wb = 1) => { c.moveTo(x - sw, shY + h * 0.02); c.quadraticCurveTo(x - sw - h * 0.01, shY - h * 0.02, x - sw * 0.6, shY - h * 0.015); c.lineTo(x + sw * 0.6, shY - h * 0.015); c.quadraticCurveTo(x + sw + h * 0.01, shY - h * 0.02, x + sw, shY + h * 0.02); c.lineTo(x + sw * 0.95 * wb, bot); c.lineTo(x - sw * 0.95 * wb, bot); c.closePath(); };
  if (o.outfit === 'robe') { shape(g, (c) => torso(c, y - h * 0.02, 1.35), { fill: shirt, lw }); line(g, [[x - sw * 0.5, shY], [x + sw * 0.7, hipY + h * 0.05]], { lw: lw * 0.6, ink: 'rgba(0,0,0,0.35)' }); }
  else if (o.outfit === 'pelt') { shape(g, (c) => torso(c), { fill: o.skin, lw }); shape(g, (c) => { c.moveTo(x - sw * 0.7, shY - h * 0.01); c.lineTo(x - sw * 0.2, shY - h * 0.01); c.lineTo(x + sw, hipY - h * 0.02); c.lineTo(x + sw * 1.05, hipY + h * 0.09); c.lineTo(x + sw * 0.4, hipY + h * 0.06); c.lineTo(x - sw * 0.2, hipY + h * 0.1); c.lineTo(x - sw * 1.05, hipY + h * 0.07); c.closePath(); }, { fill: '#c9944f', lw }); [[-0.4, 0.55], [0.2, 0.75], [0.6, 0.9], [-0.6, 0.95], [0.1, 1.05]].forEach(([a, b]) => ellipse(g, x + a * sw, shY + b * torsoH, h * 0.013, h * 0.01, { fill: '#6b4321', lw: 0 })); }
  else {
    shape(g, (c) => torso(c), { fill: shirt, lw });
    if (o.outfit === 'coat') { shape(g, (c) => torso(c, hipY + h * 0.13, 1.08), { fill: '#fbfbf7', lw }); poly(g, [[x - sw * 0.35, shY - h * 0.012], [x, shY + h * 0.09], [x + sw * 0.35, shY - h * 0.012]], { fill: shirt, lw: lw * 0.8 }); line(g, [[x, shY + h * 0.09], [x, hipY + h * 0.12]], { lw: lw * 0.6 }); }
    if (o.outfit === 'shirt') { poly(g, [[x - sw * 0.35, shY - h * 0.012], [x, shY + h * 0.05], [x + sw * 0.35, shY - h * 0.012]], { fill: shade(shirt, -0.06), lw: lw * 0.7 }); rect(g, x + sw * 0.25, shY + h * 0.06, sw * 0.4, h * 0.05, { fill: shade(shirt, -0.05), lw: lw * 0.6, r: 3 }); }
    if (o.outfit === 'apron') shape(g, (c) => { c.moveTo(x - sw * 0.6, shY + h * 0.03); c.lineTo(x + sw * 0.6, shY + h * 0.03); c.lineTo(x + sw * 0.85, hipY + h * 0.12); c.lineTo(x - sw * 0.85, hipY + h * 0.12); c.closePath(); }, { fill: o.apron || '#8a5a33', lw }), rect(g, x - sw * 0.35, shY + h * 0.12, sw * 0.7, h * 0.06, { fill: shade(o.apron || '#8a5a33', -0.12), lw: lw * 0.6, r: 3 });
    if (!o.outfit || o.outfit === 'tee') shape(g, (c) => c.arc(x, shY - h * 0.012, sw * 0.32, 0, Math.PI), { fill: o.skin, lw: lw * 0.8 });
  }
  // tay
  const handCol = o.hands === 'glove' ? '#ffffff' : o.skin;
  const sleeve = o.outfit === 'pelt' ? null : o.outfit === 'coat' ? '#fbfbf7' : shirt;
  const arm = (side, ang) => {
    const s = side === 'L' ? -1 : 1, sx = x + s * sw * 0.92, sy = shY + h * 0.03;
    const [a1, a2] = ang, ua = h * 0.15, fa = h * 0.14;
    const ex = sx + s * Math.sin(a1) * ua, ey = sy + Math.cos(a1) * ua, hx = ex + s * Math.sin(a2) * fa, hy = ey + Math.cos(a2) * fa;
    tube(g, [[sx, sy], [ex, ey], [hx, hy]], armW, o.outfit === 'robe' || o.outfit === 'coat' ? (sleeve) : o.skin, { border: lw * 0.85, smooth: false });
    if (sleeve && o.outfit !== 'robe' && o.outfit !== 'coat') tube(g, [[sx, sy], [lerp(sx, ex, 0.45), lerp(sy, ey, 0.45)]], armW * 1.55, sleeve, { border: lw * 0.85, smooth: false });
    circ(g, hx, hy, h * 0.03, { fill: handCol, lw: lw * 0.85 });
    return [hx, hy];
  };
  const hands = { L: arm('L', pose.L), R: arm('R', pose.R) };
  // dau
  head(g, x, headY, R, { ...o, t });
  // do vat cam tay
  if (o.prop && o.drawProp) o.drawProp(g, hands[o.propHand || 'R'][0], hands[o.propHand || 'R'][1], h * 0.16 * (o.propScale || 1));
  g.restore();
  return { hands, head: [x, headY, R], top: headY - R };
}
function shade(c, k) { const n = parseInt(c.slice(1), 16); let r = n >> 16, gg = (n >> 8) & 255, b = n & 255; const f = (v) => Math.round(k >= 0 ? v + (255 - v) * k : v * (1 + k)); return `rgb(${f(r)},${f(gg)},${f(b)})`; }
