// ink.js — bo phong cach "dem": phim ngan hoat hinh khong loi doc (self-improvement). Nen toi, vat phang xam xanh,
// net vien manh mau sang, nhan vat dau tron mau kem, "giong noi" la bong den phat sang mau nhan.
// Toa do: don vi logic 1920x1080 (doc 1080x1920). x, y trong args: 0..1 = ti le khung, > 1.5 = px.
import { E, clamp, lerp, ease, rng, noise, text, measure, alpha, shade, mix, radGrad } from '/engine/core.js';

export const PAL = {
  bg: '#141418', bg2: '#1b1c22', floor: '#17181d', line: '#c9ccd4', lineDim: '#7d808a', obj: '#25272e', obj2: '#2e3038', obj3: '#383b45',
  blanket: '#3b4462', blanketDark: '#2c3349', pillow: '#5a5e6b', wood: '#3a3029', woodLine: '#8c7a68',
  hero: '#ece6d6', heroShade: '#d3ccbb', heroLine: '#7f7a6f', friend1: '#d8d1c2', friend2: '#c8c4bb', girlSkin: '#efe3d2',
  hair: '#17161a', hood: '#55585f', hoodDark: '#3e4047', scarf: '#e8b33c', coat: '#4e6b52', capY: '#e8b33c', capB: '#3f7fd0', capR: '#c8463c',
  clock: '#ff3b30', moon: '#e9ecf2', lamp: '#ffc56b', screen: '#9fb6ff', white: '#f4f2ee', grey: '#8d9099',
  red: '#e8363a', pink: '#ff4fa3', amber: '#ffb03b', teal: '#38d1c4', blueMsg: '#3d7cf2', green: '#5fd36a',
};
// mau nhan cua kenh: red (mac dinh) | pink | amber | teal  (config.json: "accent")
export const ACCENTS = { red: '#ff3b3b', pink: '#ff4fa3', amber: '#ffb03b', teal: '#38d1c4' };
export const accent = () => ACCENTS[E.cfg.accent] || E.cfg.accent || ACCENTS.red;

export const FONT_NARR = '"Comic Neue"';      // chu ke chuyen
export const FONT_HAND = '"Caveat"';          // giong cam do, chu viet tay
export const FONT_THUMB = '"Luckiest Guy"';   // chu thumbnail
export const FONT_UI = '"Be Vietnam Pro"';    // giao dien dien thoai

// ---------- toa do va thoi gian
export const fx = (v, d = 0.5) => (v === undefined || v === null ? d * E.W : v <= 1.5 ? v * E.W : v);
export const fy = (v, d = 0.5) => (v === undefined || v === null ? d * E.H : v <= 1.5 ? v * E.H : v);
export const fs = (v, d = 0.3) => (v === undefined || v === null ? d * E.H : v <= 1.5 ? v * E.H : v);
export const T = (at, def = 0) => (typeof at === 'number' ? at : def);
export const fadeIn = (lt, at = 0, dur = 0.35) => clamp((lt - at) / dur);
export const pop = (lt, at = 0, dur = 0.35) => (lt < at ? 0 : ease.outBack(clamp((lt - at) / dur)));
// hien trong [at, at+dur], mo vao / mo ra
export function window01(lt, at, dur, fi = 0.4, fo = 0.4) {
  if (lt < at) return 0; if (dur == null) return clamp((lt - at) / fi);
  return Math.min(clamp((lt - at) / fi), clamp((at + dur - lt) / fo));
}
// gia tri doi theo moc thoi gian: list = [[giay, gia tri], ...]
export function at(lt, list, def) { let v = def; for (const [t, x] of list || []) if (lt >= t) v = x; return v; }

// vung an toan (trong dai den dien anh)
export function safe() {
  const b = E.cfg.bars, ratio = b === 'scope' ? 2.39 : b === 'wide' ? 2.0 : typeof b === 'number' ? b : 0;
  const bar = !E.vertical && ratio ? Math.max(0, (E.H - E.W / ratio) / 2) : 0;
  return { top: bar, bottom: E.H - bar, h: E.H - 2 * bar };
}

// ---------- hinh co vien manh sang
export function obj(g, build, o = {}) {
  const { fill = PAL.obj, line = PAL.line, lw = 2.4, a = 1, la = 0.75, dash = null } = o;
  g.save(); g.globalAlpha *= a; g.beginPath(); build(g);
  if (fill) { g.fillStyle = fill; g.fill(o.rule || 'nonzero'); }
  if (line && lw > 0) { g.globalAlpha *= la; g.lineWidth = lw; g.strokeStyle = line; g.lineJoin = 'round'; g.lineCap = 'round'; if (dash) g.setLineDash(dash); g.stroke(); }
  g.restore();
}
export const box = (g, x, y, w, h, o = {}) => obj(g, (c) => { c.roundRect ? c.roundRect(x, y, w, h, o.r ?? 6) : c.rect(x, y, w, h); }, o);
export const oval = (g, x, y, rx, ry, o = {}) => obj(g, (c) => c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), o.rot || 0, 0, Math.PI * 2), o);
export const ln = (g, pts, o = {}) => {
  g.save(); g.globalAlpha *= (o.a ?? 1) * (o.la ?? 0.75); g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); pts.slice(1).forEach((p) => g.lineTo(p[0], p[1]));
  g.lineWidth = o.lw ?? 2.4; g.strokeStyle = o.color || PAL.line; g.lineCap = 'round'; g.lineJoin = 'round'; if (o.dash) g.setLineDash(o.dash); g.stroke(); g.restore();
};
export function fillAll(g, c) { g.fillStyle = c; g.fillRect(-60, -60, E.W + 120, E.H + 120); }
// gradient ve san vao canvas nho roi phong to (SwiftShader ve gradient full khung rat cham)
const _gc = new Map();
function gradCanvas(key, w, h, paint) { let c = _gc.get(key); if (!c) { c = document.createElement('canvas'); c.width = w; c.height = h; paint(c.getContext('2d'), w, h); _gc.set(key, c); if (_gc.size > 200) _gc.delete(_gc.keys().next().value); } return c; }
export function vgrad(g, stops, y0 = 0, y1 = E.H) {
  const c = gradCanvas('v' + JSON.stringify(stops), 4, 256, (x, w, h) => { const gr = x.createLinearGradient(0, 0, 0, h); stops.forEach(([o, col]) => gr.addColorStop(o, col)); x.fillStyle = gr; x.fillRect(0, 0, w, h); });
  g.save(); g.imageSmoothingEnabled = true; g.fillStyle = stops[0][1]; g.fillRect(-60, y0 - 60, E.W + 120, 60); g.fillStyle = stops[stops.length - 1][1]; g.fillRect(-60, y1, E.W + 120, 60); g.drawImage(c, -60, y0, E.W + 120, y1 - y0); g.restore();
}
// anh sang mem (cong them)
export function light(g, x, y, r, color, a = 0.5) {
  if (!(r > 1) || !(a > 0)) return;
  const c = gradCanvas('L' + color, 128, 128, (q, w) => { const gr = q.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); gr.addColorStop(0, alpha(color, 1)); gr.addColorStop(0.4, alpha(color, 0.38)); gr.addColorStop(1, alpha(color, 0)); q.fillStyle = gr; q.fillRect(0, 0, w, w); });
  g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha *= Math.min(1, a); g.drawImage(c, x - r, y - r, r * 2, r * 2); g.restore();
}
// chum sang hinh non (den ban, cua so)
export function beam(g, x0, y0, x1a, x1b, y1, color, a = 0.12) {
  g.save(); g.globalCompositeOperation = 'lighter';
  const gr = g.createLinearGradient(x0, y0, (x1a + x1b) / 2, y1); gr.addColorStop(0, alpha(color, a)); gr.addColorStop(1, alpha(color, 0));
  g.fillStyle = gr; g.beginPath(); g.moveTo(x0 - 6, y0); g.lineTo(x0 + 6, y0); g.lineTo(x1b, y1); g.lineTo(x1a, y1); g.closePath(); g.fill(); g.restore();
}
// lam toi ca khung (vignette dien anh)
export function vignette(g, a = 0.55) {
  const c = gradCanvas('vig' + E.W + 'x' + E.H, 192, Math.round(192 * E.H / E.W), (q, w, h) => { const r = Math.hypot(w, h) / 2; const gr = q.createRadialGradient(w / 2, h / 2, r * 0.35, w / 2, h / 2, r); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,1)'); q.fillStyle = gr; q.fillRect(0, 0, w, h); });
  g.save(); g.globalAlpha *= a; g.drawImage(c, 0, 0, E.W, E.H); g.restore();
}

// ---------- chu
function wrapLines(g, str, maxW, size, font, weight = 700) {
  const words = String(str).split(/\s+/); const out = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (cur && measure(g, t, size, font, weight) > maxW) { out.push(cur); cur = w; } else cur = t; }
  if (cur) out.push(cur); return out;
}
export { wrapLines as wrap };
// chu ke chuyen: trang, bong toi mem. o.type = hien tung chu cai
export function narr(g, str, x, y, o = {}) {
  const size = o.size || (E.vertical ? 64 : 58), a = o.a ?? 1; if (a <= 0) return;
  const lines = wrapLines(g, str, o.maxW || E.W * (E.vertical ? 0.84 : 0.7), size, FONT_NARR, 700);
  let shown = Infinity; if (o.type !== undefined && o.type < 1) shown = Math.floor(o.type * String(str).length);
  let used = 0;
  lines.forEach((l, i) => {
    const vis = l.slice(0, Math.max(0, shown - used)); used += l.length + 1; if (!vis) return;
    const yy = y + (i - (lines.length - 1) / 2) * size * 1.25;
    g.save(); g.shadowColor = 'rgba(0,0,0,0.85)'; g.shadowBlur = size * 0.35; g.shadowOffsetY = 2;
    text(g, vis, x - (o.align === 'left' ? 0 : 0), yy, { size, font: FONT_NARR, weight: 700, color: o.color || PAL.white, a, align: o.align || 'center' });
    g.restore();
    if (o.emph) { // tu nhan doi mau
      for (const [word, col] of Object.entries(o.emph)) { const k = vis.indexOf(word); if (k < 0) continue; const lw = measure(g, l, size, FONT_NARR, 700), pre = measure(g, vis.slice(0, k), size, FONT_NARR, 700);
        text(g, word, x - lw / 2 + pre, yy, { size, font: FONT_NARR, weight: 700, color: col, a, align: 'left' }); }
    }
  });
}
// giong cam do: chu viet tay, mau nhan, phat sang, go tung chu, run nhe
export function tempt(g, str, x, y, o = {}) {
  const size = o.size || (E.vertical ? 76 : 62), a = o.a ?? 1, col = o.color || accent(); if (a <= 0) return;
  const lines = String(str).split('\n'); let shown = Infinity; if (o.type !== undefined && o.type < 1) shown = Math.floor(o.type * String(str).replace(/\n/g, '').length); let used = 0;
  lines.forEach((l, i) => {
    const vis = l.slice(0, Math.max(0, shown - used)); used += l.length; if (!vis) return;
    const jx = noise((o.t || 0) * 6 + i, 3) * 1.6, jy = noise((o.t || 0) * 6 + i, 9) * 1.6;
    text(g, vis, x + jx, y + jy + i * size * 1.05, { size, font: FONT_HAND, weight: 700, color: col, a, align: o.align || 'center', glowColor: alpha(col, 0.55), rot: o.rot });
  });
}
// bong bong loi noi trang nho ("hi.", "hey!")
export function say(g, str, x, y, o = {}) {
  const size = o.size || 38, a = o.a ?? 1; if (a <= 0) return; const k = ease.outBack(clamp(a * 1.4));
  const w = measure(g, str, size, FONT_NARR, 700) + size * 1.1, h = size * 1.6;
  g.save(); g.globalAlpha *= clamp(a * 2); g.translate(x, y); g.scale(k, k);
  g.fillStyle = PAL.white; g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, h * 0.45); g.fill();
  const tx = (o.tail ?? -0.25) * w; g.beginPath(); g.moveTo(tx - 10, h / 2 - 2); g.lineTo(tx + 10, h / 2 - 2); g.lineTo(tx - 6, h / 2 + 18); g.closePath(); g.fill();
  text(g, str, 0, 2, { size, font: FONT_NARR, weight: 700, color: '#141418' }); g.restore();
}
// chu to giua man hinh ("30 minutes later...")
// chu nhan to (dong thu 2 tren man den): trang, vien xam day, bong toi — kieu chu "noi" cua kenh mau
export function big(g, str, x, y, o = {}) {
  const size = o.size || (E.vertical ? 92 : 112), a = o.a ?? 1; if (a <= 0) return;
  const lines = wrapLines(g, str, o.maxW || E.W * (E.vertical ? 0.88 : 0.86), size, FONT_NARR, 700);
  let shown = Infinity; if (o.type !== undefined && o.type < 1) shown = Math.floor(o.type * String(str).length); let used = 0;
  lines.forEach((l, i) => {
    const vis = l.slice(0, Math.max(0, shown - used)); used += l.length + 1; if (!vis) return;
    const yy = y + (i - (lines.length - 1) / 2) * size * 1.15;
    g.save(); g.shadowColor = 'rgba(0,0,0,0.9)'; g.shadowBlur = size * 0.25; g.shadowOffsetY = size * 0.04;
    text(g, vis, x, yy, { size, font: FONT_NARR, weight: 700, color: '#a9a59d', a, stroke: size * 0.11, strokeColor: '#a9a59d' }); g.restore();
    text(g, vis, x, yy, { size, font: FONT_NARR, weight: 700, color: o.color || '#f2efe8', a, stroke: size * 0.035, strokeColor: '#ffffff' });
  });
}
// duong gach tay (gach chan, gach xoa) ve dan p
export function stroke(g, x0, y0, x1, y1, o = {}) {
  const p = clamp(o.p ?? 1); if (p <= 0) return; const r = rng(o.seed || 3);
  g.save(); g.strokeStyle = o.color || accent(); g.lineWidth = o.lw || 7; g.lineCap = 'round'; if (o.glow) { g.shadowColor = o.color || accent(); g.shadowBlur = 14; }
  g.beginPath(); g.moveTo(x0, y0); const n = 8; for (let i = 1; i <= n; i++) { const k = (i / n) * p; g.lineTo(lerp(x0, x1, k), lerp(y0, y1, k) + (r() - 0.5) * (o.wob ?? 3)); } g.stroke(); g.restore();
}
