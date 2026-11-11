// world.js (pack squire) — phong nen hoat hinh vector: troi + may vien, doi xa mo suong, hang cay, dat co, bun cay xoi,
// noi that da/go/leu/nha tho, chien hao, bien. bg(g, kind, o). o = { time, t, seed, groundY, mud, rain, sun, haze, castle, tents,
// flags, volcano, trees, color }. Ve sac net; template tu lam mo (blurLayer) theo do sau.
import { E, rng, lerp, clamp, noise, alpha, mix, shade } from './ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, blob, polyS, line, tube, smoothPath, darker, lighter, haze } from './ink.js';
import { charge } from './chara.js';

const W = () => E.W, H = () => E.H;
// ---------- bang mau theo gio
export const TIMES = {
  day:    { sky: ['#8fc3e3', '#d8edf5'], cloud: '#fbf8f3', cloudSh: '#dde4ea', far: '#a9bfcf', mid: '#8fae5c', grass: '#86a046', grassD: '#6f8c39', tint: null, sun: '#fff6d8' },
  sunset: { sky: ['#e7a08a', '#f6c596'], cloud: '#f6b79b', cloudSh: '#e0937c', far: '#b7a6a4', mid: '#8aa05a', grass: '#7e9a42', grassD: '#667f33', tint: ['#ff9a5a', 0.1], sun: '#f8c27a' },
  golden: { sky: ['#e3ae6c', '#f3d79a'], cloud: '#f5dcae', cloudSh: '#e2bd88', far: '#c9ad84', mid: '#a9a15c', grass: '#a59b52', grassD: '#8a8240', tint: ['#e8b060', 0.16], sun: '#fff1c4' },
  dusk:   { sky: ['#5e4d78', '#c77a72'], cloud: '#8d6d86', cloudSh: '#6f5470', far: '#6d5d73', mid: '#5d6a4a', grass: '#56653f', grassD: '#455233', tint: ['#4a2f5a', 0.18], sun: '#f4a46a' },
  storm:  { sky: ['#66717c', '#9aa3aa'], cloud: '#7b8690', cloudSh: '#5d6770', far: '#7f8b8f', mid: '#5f7148', grass: '#5b6c3e', grassD: '#4a5932', tint: ['#4c5a66', 0.18], sun: null },
  night:  { sky: ['#1d2a48', '#3d4f74'], cloud: '#45557a', cloudSh: '#34426a', far: '#34405c', mid: '#2f3d3c', grass: '#2f4034', grassD: '#24332a', tint: ['#1a2448', 0.25], sun: '#f1ecd2' },
  dawn:   { sky: ['#a9b9d6', '#f3d2b8'], cloud: '#f2dfd2', cloudSh: '#d3c0bd', far: '#a7aabb', mid: '#86a06a', grass: '#7f9b4f', grassD: '#68833e', tint: ['#ffcfa0', 0.08], sun: '#ffe9c2' },
};
const TM = (o) => TIMES[o.time] || TIMES.day;
function skyGrad(g, c) { const gr = g.createLinearGradient(0, 0, 0, H() * 0.8); gr.addColorStop(0, c[0]); gr.addColorStop(1, c[1]); g.fillStyle = gr; g.fillRect(-W(), -H(), W() * 3, H() * 3); }
export function cloud(g, x, y, s, o = {}) {
  const c = o.color || TIMES.day.cloud, sh = o.shade || TIMES.day.cloudSh, lw = o.lw ?? Math.max(2, s * 0.025);
  const pts = [[-1, 0.18], [-0.95, -0.12], [-0.62, -0.32], [-0.3, -0.62], [0.08, -0.55], [0.35, -0.78], [0.72, -0.5], [0.98, -0.2], [1.02, 0.18]];
  shape(g, (cc) => { cc.moveTo(x - s, y + s * 0.18); for (let i = 1; i < pts.length; i++) { const p0 = pts[i - 1], p1 = pts[i]; cc.quadraticCurveTo(x + (p0[0] + p1[0]) / 2 * s + (p1[0] - p0[0]) * 0.1 * s, y + Math.min(p0[1], p1[1]) * s * 1.25, x + p1[0] * s, y + p1[1] * s); } cc.quadraticCurveTo(x, y + s * 0.34, x - s, y + s * 0.18); }, { fill: c, lw, inner: (cc) => { cc.fillStyle = sh; cc.beginPath(); cc.ellipse(x, y + s * 0.34, s * 1.1, s * 0.26, 0, 0, Math.PI * 2); cc.fill(); } });
}
// may dai mong (kieu vet troi hoang hon)
function streak(g, x, y, w, c) { g.save(); g.fillStyle = c; g.beginPath(); g.roundRect(x, y, w, 10, 5); g.fill(); g.restore(); }
function hillBand(g, y, amp, col, seed, o = {}) {
  const r = rng(seed), n = o.n || 7, pts = [[-80, H() + 60], [-80, y]];
  for (let i = 0; i <= n; i++) pts.push([-80 + i * (W() + 160) / n, y - r() * amp]);
  pts.push([W() + 80, y], [W() + 80, H() + 60]);
  shape(g, (c) => { c.moveTo(pts[0][0], pts[0][1]); smoothPath(c, pts.slice(1, -1), false); c.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]); c.closePath(); }, { fill: col, lw: o.lw ?? 0, ink: o.ink || OUT });
}
function treeLine(g, y, col, seed, o = {}) {
  const r = rng(seed), lw = o.lw ?? 2.5;
  for (let x = -60; x < W() + 60; x += 22 + r() * 30) { const s = (o.s || 34) * (0.7 + r() * 0.6); ellipse(g, x, y - s * 0.5, s * 0.9, s * 0.7, { fill: r() < 0.5 ? col : darker(col, 0.06), lw }); }
  rect(g, -80, y - 10, W() + 160, 30, { fill: col, lw: 0, r: 0 });
}
export function tree(g, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(2, s * 0.03), col = o.color || '#6f9a3e';
  if (o.kind === 'pine') { tube(g, [[x, y], [x, y - s * 0.7]], s * 0.06, PAL.woodDark, lw); ellipse(g, x, y - s * 0.82, s * 0.42, s * 0.2, { fill: col, lw }); ellipse(g, x - s * 0.2, y - s * 0.76, s * 0.25, s * 0.14, { fill: darker(col, 0.05), lw }); return; }
  if (o.kind === 'cypress') { tube(g, [[x, y], [x, y - s * 0.15]], s * 0.05, PAL.woodDark, lw); blob(g, [[x, y - s * 1.1], [x + s * 0.13, y - s * 0.6], [x + s * 0.1, y - s * 0.12], [x - s * 0.1, y - s * 0.12], [x - s * 0.13, y - s * 0.6]], { fill: col, lw }); return; }
  tube(g, [[x, y], [x, y - s * 0.45]], s * 0.08, PAL.woodDark, lw);
  blob(g, [[x - s * 0.42, y - s * 0.42], [x - s * 0.48, y - s * 0.7], [x - s * 0.22, y - s * 0.95], [x + s * 0.12, y - s * 0.98], [x + s * 0.45, y - s * 0.78], [x + s * 0.44, y - s * 0.46], [x, y - s * 0.36]], { fill: col, lw, inner: (c) => { c.fillStyle = darker(col, 0.12); c.beginPath(); c.ellipse(x + s * 0.2, y - s * 0.45, s * 0.4, s * 0.2, 0, 0, Math.PI * 2); c.fill(); } });
}
export function bush(g, x, y, s, o = {}) { const col = o.color || '#6b9a3c', lw = o.lw ?? Math.max(1.5, s * 0.04); blob(g, [[x - s, y], [x - s * 0.9, y - s * 0.5], [x - s * 0.4, y - s * 0.85], [x + s * 0.3, y - s * 0.8], [x + s * 0.95, y - s * 0.45], [x + s, y]], { fill: col, lw }); if (o.flowers) for (let i = 0; i < 4; i++) circ(g, x - s * 0.5 + i * s * 0.33, y - s * (0.3 + (i % 2) * 0.25), s * 0.07, { fill: o.flowers, lw: lw * 0.5 }); }
export function tuft(g, x, y, s, col = PAL.grassDark, lw = 2) {
  g.save(); g.strokeStyle = OUT; g.lineWidth = lw; g.lineCap = 'round'; g.lineJoin = 'round'; g.fillStyle = col;
  g.beginPath(); g.moveTo(x - s * 0.5, y); g.lineTo(x - s * 0.35, y - s * 0.7); g.lineTo(x - s * 0.15, y - s * 0.15); g.lineTo(x, y - s); g.lineTo(x + s * 0.15, y - s * 0.15); g.lineTo(x + s * 0.38, y - s * 0.65); g.lineTo(x + s * 0.5, y); g.closePath(); g.fill(); g.stroke(); g.restore();
}
function sunDisc(g, x, y, r, col, a = 1) {
  g.save(); g.globalAlpha = a; const gr = g.createRadialGradient(x, y, r * 0.6, x, y, r * 3.2); gr.addColorStop(0, alpha(col, 0.7)); gr.addColorStop(1, alpha(col, 0)); g.fillStyle = gr; g.fillRect(x - r * 4, y - r * 4, r * 8, r * 8);
  g.fillStyle = col; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.restore();
}
export function flag(g, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(1.5, s * 0.03), wv = Math.sin((o.t || 0) * 3 + x * 0.01) * s * 0.06;
  tube(g, [[x, y], [x, y - s]], s * 0.035, PAL.woodDark, lw);
  shape(g, (c) => { c.moveTo(x, y - s); c.quadraticCurveTo(x + s * 0.28, y - s + wv, x + s * 0.55, y - s * 0.98); c.lineTo(x + s * 0.55, y - s * 0.62); c.quadraticCurveTo(x + s * 0.28, y - s * 0.62 + wv, x, y - s * 0.64); c.closePath(); }, { fill: o.color || PAL.red, lw, inner: (c) => { if (o.charge) charge(c, o.charge, x + s * 0.27, y - s * 0.81, s * 0.28, o.chargeColor || PAL.yellow); if (o.color2) { c.fillStyle = o.color2; c.fillRect(x, y - s, s * 0.27, s * 0.18); c.fillRect(x + s * 0.27, y - s * 0.82, s * 0.3, s * 0.2); } } });
}
export function tent(g, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(1.5, s * 0.025), c1 = o.color || PAL.white, c2 = o.color2 || PAL.red;
  shape(g, (c) => { c.moveTo(x - s * 0.5, y); c.lineTo(x - s * 0.42, y - s * 0.45); c.lineTo(x, y - s * 0.82); c.lineTo(x + s * 0.42, y - s * 0.45); c.lineTo(x + s * 0.5, y); c.closePath(); }, { fill: c1, lw, inner: (c) => { c.fillStyle = c2; for (let i = -3; i <= 3; i += 2) { c.beginPath(); c.moveTo(x, y - s * 0.82); c.lineTo(x + i * s * 0.09, y); c.lineTo(x + (i + 1) * s * 0.09, y); c.closePath(); c.fill(); } } });
  polyS(g, [[x - s * 0.45, y - s * 0.42], [x + s * 0.45, y - s * 0.42], [x + s * 0.42, y - s * 0.34], [x - s * 0.42, y - s * 0.34]], { fill: c2, lw: lw * 0.8 });
  tube(g, [[x, y - s * 0.82], [x, y - s * 1.0]], s * 0.02, PAL.woodDark, lw * 0.6); polyS(g, [[x, y - s], [x + s * 0.12, y - s * 0.96], [x, y - s * 0.92]], { fill: c2, lw: lw * 0.6 });
}
export function castle(g, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(1.5, s * 0.015), col = o.color || PAL.stone;
  const crenel = (x0, y0, w) => { for (let i = 0; i < w / (s * 0.06); i += 2) rect(g, x0 + i * s * 0.06, y0 - s * 0.05, s * 0.06, s * 0.06, { fill: col, lw: lw * 0.8, r: 0 }); };
  rect(g, x - s * 0.5, y - s * 0.35, s, s * 0.35, { fill: col, lw, r: 0 }); crenel(x - s * 0.5, y - s * 0.35, s);
  for (const k of [-0.5, 0.38]) { rect(g, x + k * s, y - s * 0.62, s * 0.14, s * 0.62, { fill: lighter(col, 0.04), lw, r: 0 }); crenel(x + k * s, y - s * 0.62, s * 0.14); polyS(g, [[x + k * s - s * 0.01, y - s * 0.66], [x + k * s + s * 0.07, y - s * 0.84], [x + k * s + s * 0.15, y - s * 0.66]], { fill: PAL.red, lw }); }
  rect(g, x - s * 0.07, y - s * 0.2, s * 0.14, s * 0.2, { fill: PAL.woodDark, lw, r: s * 0.06 });
}
function volcano(g, x, y, s, col) {
  shape(g, (c) => { c.moveTo(x - s, y); c.bezierCurveTo(x - s * 0.55, y - s * 0.1, x - s * 0.25, y - s * 0.38, x - s * 0.1, y - s * 0.42); c.lineTo(x + s * 0.12, y - s * 0.42); c.bezierCurveTo(x + s * 0.3, y - s * 0.36, x + s * 0.6, y - s * 0.08, x + s, y); c.closePath(); }, { fill: col, lw: 0, inner: (c) => { c.fillStyle = alpha('#ffffff', 0.12); c.beginPath(); c.moveTo(x - s * 0.1, y - s * 0.42); c.lineTo(x - s * 0.6, y); c.lineTo(x - s * 0.2, y); c.closePath(); c.fill(); } });
}
// bun cay xoi: luong bun nam ngang co phoi canh
function furrows(g, gy, o) {
  const top = gy, bot = H() + 40, cx = W() / 2;
  g.save(); g.fillStyle = o.wet ? PAL.mud : PAL.dirt; g.fillRect(-80, top, W() + 160, bot - top);
  for (let i = 0; i < 22; i++) {
    const k = i / 22, y = top + (bot - top) * k * k * 1.05 + 4, th = 3 + k * 16;
    g.fillStyle = o.wet ? PAL.mudDark : darker(PAL.dirt, 0.15); g.fillRect(-80, y, W() + 160, th * 0.5);
    g.fillStyle = alpha('#ffffff', 0.06); g.fillRect(-80, y - th * 0.4, W() + 160, th * 0.25);
  }
  if (o.wet) { const r = rng(o.seed || 3); for (let i = 0; i < 14; i++) { const y = top + 40 + r() * (bot - top - 40), x = r() * W(), s = 20 + (y - top) * 0.15; ellipse(g, x, y, s * 2, s * 0.35, { fill: alpha('#9fb6c6', 0.55), lw: Math.max(1, s * 0.05) }); } }
  g.restore();
}
// bui co nhieu la (kieu tranh vector: la nhon cao thap, vien nau, mau sang hon nen)
export function grassClump(g, x, y, s, col, lw, seed = 0) {
  const r = rng(seed + 3), n = 5 + Math.floor(r() * 3);
  g.save(); g.lineJoin = 'round'; g.lineCap = 'round';
  g.beginPath(); g.moveTo(x - s * 0.55, y);
  for (let i = 0; i < n; i++) { const k = (i + 0.5) / n, bx = x - s * 0.55 + k * s * 1.1, hh = s * (0.55 + r() * 0.6) * (1 - Math.abs(k - 0.5) * 0.7), lean = (k - 0.5) * s * 0.5 + (r() - 0.5) * s * 0.15;
    g.lineTo(bx - s * 0.07, y - hh * 0.25); g.lineTo(bx + lean, y - hh); g.lineTo(bx + s * 0.07, y - hh * 0.2); }
  g.lineTo(x + s * 0.55, y); g.closePath();
  g.fillStyle = col; g.fill(); g.lineWidth = lw; g.strokeStyle = OUT; g.stroke(); g.restore();
}
export function pebble(g, x, y, s, lw) { ellipse(g, x, y, s, s * 0.55, { fill: '#a39d96', lw, inner: (c) => ellipse(c, x - s * 0.25, y - s * 0.2, s * 0.35, s * 0.15, { fill: '#c9c3bb', lw: 0 }) }); }
function dirtPatch(g, x, y, s, col, lw, seed) {
  const r = rng(seed), pts = []; for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2, rr = 1 + (r() - 0.5) * 0.45; pts.push([x + Math.cos(a) * s * 1.5 * rr, y + Math.sin(a) * s * 0.3 * rr]); }
  blob(g, pts, { fill: col, lw, inner: (c) => { ellipse(c, x + s * 0.2, y - s * 0.12, s * 1.1, s * 0.12, { fill: alpha('#000', 0.12), lw: 0 }); for (let i = 0; i < 3; i++) ellipse(c, x + (r() - 0.5) * s * 2, y + (r() - 0.3) * s * 0.3, s * 0.08, s * 0.045, { fill: alpha('#3a2a1c', 0.45), lw: 0 }); } });
}
function grassGround(g, gy, c, o) {
  shape(g, (cc) => { cc.moveTo(-80, gy); for (let x = -80; x <= W() + 80; x += 160) cc.quadraticCurveTo(x + 80, gy - 8 + noise(x * 0.01, o.seed || 1) * 10, x + 160, gy); cc.lineTo(W() + 80, H() + 60); cc.lineTo(-80, H() + 60); cc.closePath(); }, { fill: c.grass, lw: 0 });
  const r = rng((o.seed || 1) + 9), dep = (y) => clamp((y - gy) / (H() - gy), 0, 1);
  // dai sang toi nam ngang (doi thoai)
  for (let i = 0; i < 5; i++) { const y = gy + (i + 0.6) / 5 * (H() - gy), w = W() * (0.5 + r() * 0.6), x = r() * W(); ellipse(g, x, y, w, (H() - gy) * 0.06, { fill: alpha(i % 2 ? lighter(c.grass, 0.08) : c.grassD, 0.3), lw: 0 }); }
  // duong dat
  if (o.path) { const pw = (H() - gy) * 0.18; g.save(); g.beginPath(); g.moveTo(-80, H() - pw * 2.2); g.bezierCurveTo(W() * 0.3, gy + (H() - gy) * 0.35, W() * 0.6, gy + (H() - gy) * 0.55, W() + 80, gy + (H() - gy) * 0.25); g.lineWidth = pw; g.strokeStyle = OUT; g.lineCap = 'butt'; g.stroke(); g.lineWidth = pw - 6; g.strokeStyle = o.pathColor || '#b89a6a'; g.stroke(); g.lineWidth = pw * 0.15; g.strokeStyle = alpha('#000', 0.1); g.stroke(); g.restore(); }
  if (o.patches !== false) for (let i = 0; i < (o.patches ?? 3); i++) { const y = gy + 40 + r() * (H() - gy - 40), x = r() * W(), s = 28 + dep(y) * 70; dirtPatch(g, x, y, s, o.patchColor || '#9b7a52', Math.max(1.5, s * 0.05), i * 13 + (o.seed || 1)); }
  // soi
  for (let i = 0; i < (o.pebbles ?? 10); i++) { const y = gy + 20 + r() * (H() - gy), s = 3 + dep(y) * 9; pebble(g, r() * W(), y, s, Math.max(1, s * 0.18)); }
  // bui co: xa nho nhat, gan to dam
  const tl = [];
  for (let i = 0; i < (o.tufts ?? 34); i++) { const y = gy + 15 + Math.pow(r(), 0.8) * (H() - gy), x = r() * W(); tl.push([x, y]); }
  tl.sort((p, q) => p[1] - q[1]);
  tl.forEach(([x, y], i) => { const k = dep(y), s = 9 + k * 34; grassClump(g, x, y, s, mix(c.grassD, '#b5cc63', 0.35 + 0.35 * k), Math.max(1.1, s * 0.07), i); });
  if (o.flowers) for (let i = 0; i < 22; i++) { const y = gy + 20 + r() * (H() - gy), x = r() * W(), s = 2.5 + dep(y) * 5; for (let k = 0; k < 3; k++) circ(g, x + (k - 1) * s * 2.2, y - (k % 2) * s * 1.5, s, { fill: [PAL.white, PAL.yellow, '#e98aa8'][i % 3], lw: s * 0.35 }); }
}

export function bg(g, kind = 'field', o = {}) {
  const t = o.t || 0, s = o.seed || 1, gy = H() * (o.groundY ?? 0.66), c = TM(o);
  switch (kind) {
    case 'paper': { g.fillStyle = o.color || PAL.cream; g.fillRect(-W(), -H(), W() * 3, H() * 3); break; }
    case 'color': { g.fillStyle = o.color || '#c9b48c'; g.fillRect(-W(), -H(), W() * 3, H() * 3); break; }
    case 'field': case 'hills': case 'mud': case 'plain': case 'battlefield': {
      const plain = kind === 'plain', t2 = plain ? TIMES[o.time || 'golden'] : c;
      skyGrad(g, t2.sky);
      if (t2.sun && o.sun !== false) sunDisc(g, W() * (o.sunX ?? 0.78), H() * (o.sunY ?? 0.3), H() * 0.07, t2.sun, o.time === 'day' ? 0.6 : 1);
      if (o.time === 'night') { const r = rng(s); for (let i = 0; i < 70; i++) circ(g, r() * W(), r() * H() * 0.5, 1 + r() * 2.2, { fill: '#fff6d0', lw: 0 }); }
      if (o.time === 'sunset' || o.time === 'dusk' || plain) for (let i = 0; i < 6; i++) streak(g, W() * (0.05 + (i * 0.17) % 0.8), H() * (0.08 + i * 0.045), W() * (0.15 + (i % 3) * 0.08), alpha(lighter(t2.cloud, 0.1), 0.6));
      const nc = o.clouds ?? (o.time === 'storm' ? 0 : plain ? 1 : 3), rr = rng(s + 2);
      for (let i = 0; i < nc; i++) cloud(g, ((rr() * W() * 1.2 + t * 8 * (0.5 + rr())) % (W() * 1.3)) - W() * 0.15, H() * (0.1 + rr() * 0.22), H() * (0.08 + rr() * 0.06), { color: t2.cloud, shade: t2.cloudSh });
      if (o.time === 'storm') { for (let i = 0; i < 7; i++) cloud(g, W() * (i / 6) + noise(i) * 80 + t * 6, H() * (0.06 + (i % 2) * 0.07), H() * 0.16, { color: i % 2 ? '#6c7781' : '#7d8892', shade: '#56606a' }); }
      if (o.volcano ?? plain) volcano(g, W() * (o.volcanoX ?? 0.55), gy - H() * 0.02, W() * (o.volcanoS ?? 0.62) * (H() > W() ? 1.6 : 1), mix(t2.far, '#ffffff', 0.18));
      hillBand(g, gy - H() * 0.06, H() * 0.08, t2.far, s + 4, { n: 5 });
      if (o.castle) castle(g, W() * (o.castleX ?? 0.72), gy - H() * 0.045, H() * 0.32, { color: mix(PAL.stone, t2.far, 0.45) });
      if (plain) { const r = rng(s + 31); for (let i = 0; i < 9; i++) { const x = W() * (0.05 + r() * 0.9), y = gy - H() * 0.03; tree(g, x, y, H() * (0.07 + r() * 0.05), { kind: r() < 0.5 ? 'pine' : 'cypress', color: mix('#6f8a46', t2.far, 0.5), lw: 1.5 }); } }
      treeLine(g, gy - H() * 0.015, mix(t2.mid, t2.far, 0.45), s + 7, { s: H() * 0.03, lw: 1.5 });
      hillBand(g, gy + H() * 0.01, H() * 0.03, t2.mid, s + 8, { n: 4 });
      if (o.tents) { const r = rng(s + 41); for (let i = 0; i < o.tents; i++) tent(g, W() * (0.08 + i / Math.max(1, o.tents) * 0.85 + r() * 0.04), gy + H() * 0.03, H() * (0.09 + r() * 0.04), { color2: [PAL.red, PAL.blue, PAL.green, PAL.yellow][i % 4], lw: 1.6 }); }
      if (o.flags) { const fl = Array.isArray(o.flags) ? o.flags : [{ color: PAL.red }, { color: PAL.blue, charge: 'fleur' }, { color: PAL.yellow }]; fl.forEach((f, i) => flag(g, W() * (f.x ?? (0.12 + i * 0.3)), gy + H() * (f.y ?? 0.02), H() * (f.s ?? 0.16), { ...f, t, lw: 1.8 })); }
      if (kind === 'mud' || o.mud) furrows(g, gy + H() * 0.02, { wet: o.wet ?? true, seed: s });
      else grassGround(g, gy + H() * 0.02, plain ? { grass: '#b8a35e', grassD: '#9c8a49' } : t2, { seed: s, flowers: o.flowers ?? (o.time === 'day'), patches: o.patches, tufts: o.tufts, pebbles: o.pebbles, path: o.path, pathColor: plain ? '#c9ae78' : undefined, patchColor: plain ? '#a88c5a' : undefined });
      if (o.trees) { const r = rng(s + 51); for (let i = 0; i < o.trees; i++) tree(g, W() * (0.05 + r() * 0.9), gy + H() * (0.03 + r() * 0.03), H() * (0.15 + r() * 0.08), { color: mix('#6f9a3e', t2.mid, 0.3) }); }
      if (o.bushes) { const r = rng(s + 61); for (let i = 0; i < o.bushes; i++) bush(g, W() * (0.03 + r() * 0.94), gy + H() * (0.05 + r() * 0.06), H() * (0.03 + r() * 0.02), { color: mix('#6b9a3c', t2.mid, 0.3), flowers: r() < 0.5 ? '#f4d35e' : null }); }
      if (t2.tint) haze(g, t2.tint[0], t2.tint[1]);
      break;
    }
    case 'castle': case 'stone': case 'hall': {
      // tuong da xay: gach so le, duoc thap duoc, cua so vom, co/ban treo
      g.fillStyle = o.color || PAL.stone; g.fillRect(-W(), -H(), W() * 3, H() * 3);
      const bw = H() * 0.15, bh = H() * 0.075, r = rng(s);
      g.save(); g.strokeStyle = alpha(OUT, 0.75); g.lineWidth = Math.max(2, H() * 0.004);
      for (let j = 0, y = 0; y < H(); j++, y += bh) for (let x = -(j % 2) * bw * 0.5; x < W(); x += bw) { const k = r(); g.fillStyle = k < 0.25 ? PAL.stoneDark : k < 0.45 ? PAL.stoneLight : (o.color || PAL.stone); g.beginPath(); g.roundRect(x + 2, y + 2, bw - 4, bh - 4, 4); g.fill(); g.stroke(); }
      g.restore();
      const fy = H() * (o.floorY ?? 0.82);
      rect(g, -40, fy, W() + 80, H(), { fill: PAL.plankDark, lw: 5, r: 0, inner: (cc) => { for (let i = 0; i < 6; i++) line(cc, [[-40, fy + i * H() * 0.04], [W() + 40, fy + i * H() * 0.04]], { lw: 3, a: 0.5 }); } });
      if (o.window !== false) { const wx = W() * (o.windowX ?? 0.82), wy = H() * 0.2; shape(g, (cc) => { cc.moveTo(wx - H() * 0.07, wy + H() * 0.28); cc.lineTo(wx - H() * 0.07, wy); cc.arc(wx, wy, H() * 0.07, Math.PI, 0); cc.lineTo(wx + H() * 0.07, wy + H() * 0.28); cc.closePath(); }, { fill: o.windowColor || '#a9cde3', lw: 5, inner: (cc) => { line(cc, [[wx, wy - H() * 0.07], [wx, wy + H() * 0.3]], { lw: 4 }); for (let i = 1; i < 4; i++) line(cc, [[wx - H() * 0.08, wy + i * H() * 0.07], [wx + H() * 0.08, wy + i * H() * 0.07]], { lw: 3 }); } }); }
      if (o.torch !== false) { const tx = W() * (o.torchX ?? 0.2), ty = H() * 0.36; rect(g, tx - 8, ty, 16, 40, { fill: PAL.steelDark, lw: 4, r: 3 }); tube(g, [[tx, ty], [tx + 6, ty - H() * 0.07]], 12, PAL.wood, 4); const f = 1 + Math.sin(t * 13) * 0.08; shape(g, (cc) => { const x = tx + 7, y = ty - H() * 0.07; cc.moveTo(x - 16, y); cc.quadraticCurveTo(x - 22, y - 40 * f, x, y - 70 * f); cc.quadraticCurveTo(x + 22, y - 40 * f, x + 16, y); cc.closePath(); }, { fill: '#f6a43a', lw: 4, inner: (cc) => ellipse(cc, tx + 7, ty - H() * 0.07 - 16, 8, 18, { fill: '#ffe38a', lw: 0 }) }); g.save(); const gr = g.createRadialGradient(tx, ty - 60, 10, tx, ty - 60, H() * 0.35); gr.addColorStop(0, 'rgba(255,190,90,0.35)'); gr.addColorStop(1, 'rgba(255,190,90,0)'); g.fillStyle = gr; g.fillRect(tx - H() * 0.4, ty - H() * 0.45, H() * 0.8, H() * 0.8); g.restore(); }
      if (o.banner) { const bx = W() * (o.bannerX ?? 0.05), bw2 = H() * 0.16; shape(g, (cc) => { cc.moveTo(bx, 0); cc.lineTo(bx + bw2, 0); cc.lineTo(bx + bw2, H() * 0.5); cc.lineTo(bx + bw2 / 2, H() * 0.44); cc.lineTo(bx, H() * 0.5); cc.closePath(); }, { fill: o.banner.color || PAL.yellow, lw: 5, inner: (cc) => charge(cc, o.banner.charge || 'lion', bx + bw2 / 2, H() * 0.22, bw2 * 0.8, o.banner.chargeColor || PAL.red) }); }
      if (o.door) { const dx = W() * (o.doorX ?? 0.6); shape(g, (cc) => { cc.moveTo(dx - H() * 0.1, fy); cc.lineTo(dx - H() * 0.1, fy - H() * 0.32); cc.arc(dx, fy - H() * 0.32, H() * 0.1, Math.PI, 0); cc.lineTo(dx + H() * 0.1, fy); cc.closePath(); }, { fill: o.doorOpen ? '#6a5a8a' : PAL.woodDark, lw: 5 }); }
      if (kind === 'hall') { for (let i = 0; i < 4; i++) { const x = W() * (0.1 + i * 0.27); rect(g, x - H() * 0.04, H() * 0.05, H() * 0.08, fy - H() * 0.05, { fill: PAL.stoneLight, lw: 5, r: 0, inner: (cc) => { for (let k = -2; k <= 2; k++) line(cc, [[x + k * H() * 0.014, 0], [x + k * H() * 0.014, H()]], { lw: 2, a: 0.4 }); } }); } }
      haze(g, '#2a1a10', o.dark ?? 0.08);
      break;
    }
    case 'workshop': case 'wood': {
      g.fillStyle = PAL.plank; g.fillRect(-W(), -H(), W() * 3, H() * 3);
      const ph = H() * 0.11, r = rng(s); g.save(); g.strokeStyle = alpha(OUT, 0.7); g.lineWidth = 3;
      for (let y = 0; y < H(); y += ph) { g.fillStyle = r() < 0.4 ? PAL.plankDark : r() < 0.7 ? PAL.plank : lighter(PAL.plank, 0.05); g.fillRect(-10, y, W() + 20, ph); g.beginPath(); g.moveTo(-10, y); g.lineTo(W() + 10, y); g.stroke(); for (let k = 0; k < 3; k++) { const x = r() * W(); ellipse(g, x, y + ph * 0.5, 9, 4, { fill: null, lw: 2, ink: alpha(OUT, 0.4) }); } }
      g.restore();
      if (o.beam !== false) rect(g, W() * 0.74, -10, H() * 0.12, H() + 20, { fill: PAL.woodDark, lw: 5, r: 0 });
      const fy = H() * (o.floorY ?? 0.85); rect(g, -40, fy, W() + 80, H(), { fill: PAL.woodDark, lw: 5, r: 0 });
      haze(g, '#2a1a10', 0.1);
      break;
    }
    case 'tent': {
      g.fillStyle = '#d7b98a'; g.fillRect(-W(), -H(), W() * 3, H() * 3);
      g.save(); g.strokeStyle = alpha(OUT, 0.55); g.lineWidth = 4; for (let i = -8; i <= 8; i++) { g.beginPath(); g.moveTo(W() / 2, -H() * 0.1); g.lineTo(W() / 2 + i * W() * 0.12, H()); g.stroke(); } g.restore();
      tube(g, [[W() * 0.5, H()], [W() * 0.5, -10]], H() * 0.025, PAL.woodDark, 5);
      const fy = H() * 0.8; rect(g, -40, fy, W() + 80, H(), { fill: '#a88a5c', lw: 5, r: 0 }); ellipse(g, W() * 0.5, fy + H() * 0.1, W() * 0.3, H() * 0.06, { fill: PAL.red, lw: 4 });
      if (o.lantern !== false) { const lx = W() * 0.35, ly = H() * 0.22; line(g, [[lx, 0], [lx, ly - 30]], { lw: 3 }); rect(g, lx - 22, ly - 30, 44, 60, { fill: '#f6d37a', lw: 4, r: 8 }); g.save(); const gr = g.createRadialGradient(lx, ly, 10, lx, ly, H() * 0.4); gr.addColorStop(0, 'rgba(255,214,120,0.4)'); gr.addColorStop(1, 'rgba(255,214,120,0)'); g.fillStyle = gr; g.fillRect(lx - H() * 0.5, ly - H() * 0.5, H(), H()); g.restore(); }
      break;
    }
    case 'cathedral': {
      g.fillStyle = '#c9b99c'; g.fillRect(-W(), -H(), W() * 3, H() * 3);
      const vx = W() / 2, vy = H() * 0.42;
      shape(g, (cc) => { cc.moveTo(vx - W() * 0.06, vy + H() * 0.05); cc.lineTo(vx + W() * 0.06, vy + H() * 0.05); cc.lineTo(vx + W() * 0.3, H() + 10); cc.lineTo(vx - W() * 0.3, H() + 10); cc.closePath(); }, { fill: '#b3302c', lw: 4 });
      for (let i = 0; i < 6; i++) for (const sd of [-1, 1]) { const k = 1 - i / 6, x = vx + sd * (W() * 0.07 + k * k * W() * 0.42), h = H() * (0.15 + k * 0.8), w = H() * (0.012 + k * 0.05); rect(g, x - w / 2, vy + H() * 0.05 - h * 0.85, w, h, { fill: '#e2d6bd', lw: 2 + k * 3, r: 0 }); if (i < 5) { const wx = x + sd * w * 1.2; rect(g, wx - w * 0.4, vy - h * 0.35, w * 0.8, h * 0.3, { fill: i % 2 ? '#3f6fb0' : '#c0473f', lw: 2 + k * 2, r: w * 0.4 }); } }
      rect(g, vx - W() * 0.03, vy - H() * 0.06, W() * 0.06, H() * 0.1, { fill: '#e7c45c', lw: 3, r: 20 });
      g.save(); g.globalAlpha = 0.18; g.fillStyle = '#fff6d8'; g.beginPath(); g.moveTo(W() * 0.68, 0); g.lineTo(W() * 0.78, 0); g.lineTo(W() * 0.5, H()); g.lineTo(W() * 0.36, H()); g.fill(); g.restore();
      haze(g, '#2a1a10', 0.1);
      break;
    }
    case 'trench': {
      skyGrad(g, (TIMES[o.time] || TIMES.storm).sky);
      if (o.smoke !== false) for (let i = 0; i < 4; i++) { const x = W() * (0.15 + i * 0.25), y = H() * 0.35; blob(g, [[x - 60, y + 60], [x - 70, y - 20], [x - 20, y - 90], [x + 40, y - 70], [x + 70, y], [x + 40, y + 60]], { fill: alpha('#6b6660', 0.75), lw: 3 }); }
      const ty = H() * 0.45; rect(g, -40, ty, W() + 80, H(), { fill: '#7d6146', lw: 5, r: 0 });
      // ke go + bao cat
      for (let x = -40; x < W() + 40; x += H() * 0.11) for (let k = 0; k < 2; k++) ellipse(g, x + (k % 2) * H() * 0.05, ty - k * H() * 0.05, H() * 0.06, H() * 0.03, { fill: k ? '#b09a72' : '#a08a62', lw: 4 });
      rect(g, -40, ty + H() * 0.06, W() + 80, H() * 0.3, { fill: '#8d6c49', lw: 5, r: 0, inner: (cc) => { for (let x = 0; x < W(); x += H() * 0.06) line(cc, [[x, ty], [x, ty + H() * 0.4]], { lw: 3, a: 0.6 }); } });
      rect(g, -40, H() * 0.82, W() + 80, H(), { fill: '#5f4a36', lw: 5, r: 0 });
      haze(g, '#3c3a38', 0.1);
      break;
    }
    case 'sea': case 'underwater': {
      if (kind === 'underwater') { const gr = g.createLinearGradient(0, 0, 0, H()); gr.addColorStop(0, '#3f87a6'); gr.addColorStop(1, '#13314a'); g.fillStyle = gr; g.fillRect(-W(), -H(), W() * 3, H() * 3); g.save(); g.globalAlpha = 0.15; g.fillStyle = '#fff'; for (let i = 0; i < 6; i++) { g.beginPath(); g.moveTo(W() * (0.1 + i * 0.16), 0); g.lineTo(W() * (0.14 + i * 0.16), 0); g.lineTo(W() * (0.05 + i * 0.16), H()); g.lineTo(W() * (0.0 + i * 0.16), H()); g.fill(); } g.restore(); break; }
      skyGrad(g, c.sky); if (c.sun) sunDisc(g, W() * 0.75, H() * 0.3, H() * 0.06, c.sun, 0.8);
      const hy = H() * (o.horizon ?? 0.5); rect(g, -40, hy, W() + 80, H(), { fill: o.color || PAL.water, lw: 0, r: 0 });
      for (let i = 0; i < 14; i++) { const k = i / 14, y = hy + (H() - hy) * k * k + 6; line(g, [[W() * ((i * 0.37) % 1) - 60, y], [W() * ((i * 0.37) % 1) + 60 + k * 120, y]], { lw: 2 + k * 5, ink: alpha('#ffffff', 0.35) }); }
      if (c.tint) haze(g, c.tint[0], c.tint[1]);
      break;
    }
    case 'sky': { skyGrad(g, c.sky); const rr = rng(s); for (let i = 0; i < 5; i++) cloud(g, W() * rr(), H() * (0.1 + rr() * 0.8), H() * (0.08 + rr() * 0.07), { color: c.cloud, shade: c.cloudSh }); break; }
    case 'city': {
      skyGrad(g, TIMES.dusk.sky); const r = rng(s), gy2 = H() * 0.72;
      for (let i = 0; i < 12; i++) { const w = W() * (0.06 + r() * 0.06), h = H() * (0.25 + r() * 0.35), x = i * W() / 11 - w / 2; rect(g, x, gy2 - h, w, h, { fill: i % 2 ? '#3d4a6a' : '#4a5878', lw: 4, r: 0, inner: (cc) => { for (let a = 0; a < 5; a++) for (let b = 0; b < 8; b++) if (r() < 0.5) rect(cc, x + w * 0.12 + a * w * 0.17, gy2 - h + H() * 0.03 + b * H() * 0.05, w * 0.1, H() * 0.025, { fill: '#f3d68a', lw: 0, r: 0 }); } }); }
      rect(g, -40, gy2, W() + 80, H(), { fill: '#5c5f66', lw: 5, r: 0 });
      break;
    }
    case 'night': return bg(g, 'field', { ...o, time: 'night' });
    default: return bg(g, 'field', o);
  }
}
