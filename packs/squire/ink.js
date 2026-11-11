// ink.js (pack squire) — net ve hoat hinh vector kieu kenh lich su quan su: vien nau den day, mang phang + 1 tang bong cel,
// vet sang manh tren kim loai. Moi toa do la don vi logic (1920x1080 hoac 1080x1920).
import { E, clamp, lerp, ease, rng, noise, text, measure, alpha, shade, mix, phraseTime } from '/engine/core.js';
export { E, clamp, lerp, ease, rng, noise, text, measure, alpha, shade, mix };

export const OUT = '#392a21';                     // vien nau den
export const PAL = {
  out: OUT, skin: '#f4ede1', skinShade: '#d9cfd0', blush: '#f2a7a0', tongue: '#e9707a', mouth: '#5a2a25',
  steel: '#b9b5b3', steelDark: '#8f8986', steelLight: '#dedbd8', mail: '#9a938f', mailDark: '#7b7471',
  gold: '#e7b04a', goldDark: '#b98429', bronze: '#d3a24e', bronzeDark: '#a8782f',
  red: '#c9473a', redDark: '#9b3127', crimson: '#b8352d', blue: '#3e64a3', blueDark: '#2b4878', navy: '#2c3550',
  yellow: '#efc23f', yellowDark: '#c99a22', green: '#5d7f3a', greenDark: '#435f28', white: '#f7f3ea', black: '#2b2523',
  olive: '#7c8456', oliveDark: '#5e6640', khaki: '#c8b27e', khakiDark: '#a38d5b', camo1: '#5f7a3a', camo2: '#3f5428', camo3: '#8a8a4a',
  brown: '#8a5a37', brownDark: '#64401f', leather: '#7b4f2c', leatherDark: '#5a3a22', wood: '#a8733f', woodDark: '#7a5129', rope: '#c8a46a',
  hair: '#6b4128', hairDark: '#3d2a1e', ginger: '#c0652f', grey: '#a8a39f', cream: '#efe3c8', parchment: '#e9d8ad', parchDark: '#c9b07a',
  grass: '#86a046', grassDark: '#6c8836', grassLight: '#a4bb5d', dirt: '#8f6a45', mud: '#6e5038', mudDark: '#4f3a29',
  sky: '#a9d1e8', skyHi: '#d6ecf5', cloud: '#fbf7f2', cloudShade: '#dfe3e8',
  stone: '#c8bfae', stoneDark: '#a99f8c', stoneLight: '#ddd5c5', plank: '#a77546', plankDark: '#87592f',
  water: '#5f8db0', waterDeep: '#3f6a8c', sand: '#dcc28e', sandDark: '#c3a670', dust: '#d9b77a',
  chalk: '#3c5446', chalkLine: '#f2efe6', xray: '#10243f', xrayLine: '#7ec8ff',
};
export const FONT_SIGN = '"Patrick Hand"';        // bien chu tren hinh (IN HOA viet tay)
export const FONT_THUMB = '"Luckiest Guy"';       // chu thumbnail
export const FONT_CAP = '"Be Vietnam Pro"';       // phu de short (IN HOA sieu dam)

// ---------- thoi gian: at = so giay tinh tu dau shot, hoac cum chu trong loi doc
export function T(info, at, def = 0) {
  if (at === undefined || at === null) return def;
  if (typeof at === 'number') return at;
  const t = phraseTime(at, info.start - 0.3); return t === null ? def : Math.max(0, t - info.start);
}
export const pop = (lt, at = 0, dur = 0.35) => (lt < at ? 0 : ease.outBack(clamp((lt - at) / dur)));
export const grow = (lt, at = 0, dur = 0.6) => (lt < at ? 0 : ease.inOut(clamp((lt - at) / dur)));
export const fadeIn = (lt, at = 0, dur = 0.3) => clamp((lt - at) / dur);
export const bob = (lt, amp = 4, sp = 1.6, seed = 0) => Math.sin(lt * sp * Math.PI + seed) * amp;

// ---------- hinh co vien
export function shape(g, build, o = {}) {
  const { fill = PAL.white, lw = 6, ink = OUT, a = 1, dash = null } = o;
  g.save(); if (a < 1) g.globalAlpha *= a; g.beginPath(); build(g);
  if (fill) { g.fillStyle = fill; g.fill(o.rule || 'nonzero'); }
  if (o.inner) { g.save(); g.clip(o.rule || 'nonzero'); o.inner(g); g.restore(); g.beginPath(); build(g); }
  if (lw > 0) { g.lineWidth = lw; g.strokeStyle = ink; g.lineJoin = 'round'; g.lineCap = 'round'; if (dash) g.setLineDash(dash); g.stroke(); }
  g.restore();
}
export const rect = (g, x, y, w, h, o = {}) => shape(g, (c) => { c.roundRect ? c.roundRect(x, y, w, h, o.r ?? 8) : c.rect(x, y, w, h); }, o);
export const ellipse = (g, x, y, rx, ry, o = {}) => shape(g, (c) => c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), o.rot || 0, 0, Math.PI * 2), o);
export const circ = (g, x, y, r, o = {}) => ellipse(g, x, y, r, r, o);
export function smoothPath(c, pts, closed = false) {
  const n = pts.length; if (n < 2) return;
  const P = (i) => (closed ? pts[(i + n) % n] : pts[clamp(i, 0, n - 1)]);
  c.moveTo(pts[0][0], pts[0][1]);
  const m = closed ? n : n - 1;
  for (let i = 0; i < m; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    c.bezierCurveTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]);
  }
  if (closed) c.closePath();
}
export const blob = (g, pts, o = {}) => shape(g, (c) => smoothPath(c, pts, true), o);
export const polyS = (g, pts, o = {}) => shape(g, (c) => { c.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) c.lineTo(pts[i][0], pts[i][1]); c.closePath(); }, o);
export function line(g, pts, o = {}) {
  const { lw = 6, ink = OUT, p = 1, a = 1, cap = 'round', dash = null } = o; if (p <= 0) return;
  g.save(); if (a < 1) g.globalAlpha *= a; g.beginPath();
  if (p >= 1) smoothPath(g, pts, false);
  else { const n = Math.max(1, Math.floor((pts.length - 1) * p)); const sub = pts.slice(0, n + 1); const k = (pts.length - 1) * p - n; if (pts[n + 1]) sub.push([lerp(pts[n][0], pts[n + 1][0], k), lerp(pts[n][1], pts[n + 1][1], k)]); smoothPath(g, sub, false); }
  g.lineWidth = lw; g.strokeStyle = ink; g.lineCap = cap; g.lineJoin = 'round'; if (dash) g.setLineDash(dash); g.stroke(); g.restore();
}
// ong co vien (tay, chan, can giao): ve 2 lan — vien roi ruot
export function tube(g, pts, w, fill, lw = 6, ink = OUT) {
  g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); smoothPath(g, pts, false); g.lineWidth = w + lw * 2; g.strokeStyle = ink; g.stroke();
  g.beginPath(); smoothPath(g, pts, false); g.lineWidth = w; g.strokeStyle = fill; g.stroke(); g.restore();
}
// bong cel: ve trong vung clip hien tai mot mang toi hon lech ve 1 phia
export function celShade(g, cx, cy, r, color, dx = 0.35, dy = 0.1, k = 1) {
  g.save(); g.fillStyle = color; g.beginPath(); g.arc(cx, cy, r * 1.05, 0, Math.PI * 2); g.arc(cx - r * dx, cy - r * dy, r * k, 0, Math.PI * 2, true); g.fill(); g.restore();
}
export function hilite(g, pts, w = 4, a = 0.7) { line(g, pts, { lw: w, ink: '#ffffff', a }); }
export const darker = (c, k = 0.16) => shade(c, -k);
export const lighter = (c, k = 0.2) => shade(c, k);

// ---------- chu
export function label(g, str, x, y, o = {}) {
  const { size = 48, font = FONT_SIGN, weight = 400, color = OUT, align = 'center', rot = 0, a = 1, stroke = 0, strokeColor = '#fff', caps = true, spacing = 0, shadowC = null } = o;
  const s = caps ? String(str).toUpperCase() : String(str);
  g.save(); g.translate(x, y); g.rotate(rot); if (a < 1) g.globalAlpha *= a;
  text(g, s, 0, 0, { size, font, weight, color, align, stroke, strokeColor, spacing, shadow: shadowC });
  g.restore();
}
export function wrap(g, str, maxW, size, font = FONT_CAP, weight = 700) {
  const ws = String(str).split(/\s+/); const lines = []; let cur = '';
  for (const w of ws) { const t = cur ? cur + ' ' + w : w; if (measure(g, t, size, font, weight) > maxW && cur) { lines.push(cur); cur = w; } else cur = t; }
  if (cur) lines.push(cur); return lines;
}
// bien chu giay kem vien nau (kieu "ENGLISH ARCHERS"), co duoi nhon chi xuong (tail: 'down'|'up'|null)
export function sign(g, str, x, y, o = {}) {
  const { size = 40, p = 1, tail = 'down', fill = PAL.cream, color = OUT, rot = 0 } = o; if (p <= 0) return;
  const s = String(str).toUpperCase(); const w = measure(g, s, size, FONT_SIGN, 400) + size * 0.9, h = size * 1.25, k = ease.outBack(clamp(p));
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(k, k);
  shape(g, (c) => {
    c.roundRect(-w / 2, -h / 2, w, h, size * 0.22);
    if (tail === 'down') { c.moveTo(-size * 0.25, h / 2 - 1); c.lineTo(0, h / 2 + size * 0.38); c.lineTo(size * 0.25, h / 2 - 1); }
  }, { fill, lw: Math.max(3, size * 0.11) });
  if (tail === 'down') { g.fillStyle = fill; g.fillRect(-size * 0.22, h / 2 - size * 0.12, size * 0.44, size * 0.14); }
  text(g, s, 0, size * 0.04, { size, font: FONT_SIGN, weight: 400, color, align: 'center' });
  g.restore();
}
// mui ten khoi do vien nau (so do, thumbnail)
export function blockArrow(g, x0, y0, x1, y1, o = {}) {
  const { w = 38, p = 1, fill = PAL.red, lw = 6, head = 1.9 } = o; if (p <= 0) return;
  const L = Math.hypot(x1 - x0, y1 - y0) * clamp(p), ang = Math.atan2(y1 - y0, x1 - x0), hl = w * head * 0.9;
  g.save(); g.translate(x0, y0); g.rotate(ang);
  polyS(g, [[0, -w / 2], [Math.max(0, L - hl), -w / 2], [Math.max(0, L - hl), -w * head / 2], [L, 0], [Math.max(0, L - hl), w * head / 2], [Math.max(0, L - hl), w / 2], [0, w / 2]], { fill, lw });
  g.restore();
}
// mui ten cong (duong cong + dau tam giac), kieu ban do giay
export function curveArrow(g, pts, o = {}) {
  const { lw = 14, p = 1, color = PAL.red, outline = true } = o; if (p <= 0 || pts.length < 2) return;
  const n = pts.length - 1, f = clamp(p) * n, i = Math.min(n - 1, Math.floor(f)), k = f - i;
  const sub = pts.slice(0, i + 1).concat([[lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k)]]);
  const tip = sub[sub.length - 1], prev = sub[sub.length - 2], ang = Math.atan2(tip[1] - prev[1], tip[0] - prev[0]);
  if (outline) tube(g, sub, lw, color, Math.max(3, lw * 0.3)); else line(g, sub, { lw, ink: color });
  g.save(); g.translate(tip[0], tip[1]); g.rotate(ang);
  polyS(g, [[lw * 1.6, 0], [-lw * 0.6, -lw * 1.6], [-lw * 0.6, lw * 1.6]], { fill: color, lw: outline ? Math.max(3, lw * 0.3) : 0 });
  g.restore();
}
// dau hoi do / dau than do kieu thumbnail
export function qmark(g, x, y, s, o = {}) {
  const { color = PAL.red, ch = '?' } = o;
  text(g, ch, x, y + s * 0.35, { size: s, font: FONT_THUMB, weight: 400, color, align: 'center', stroke: s * 0.08, strokeColor: OUT });
}
// bien cam do (vong tron gach cheo)
export function ban(g, x, y, r, o = {}) {
  const { p = 1, lw = r * 0.2 } = o; if (p <= 0) return; const k = ease.outBack(clamp(p));
  g.save(); g.translate(x, y); g.scale(k, k);
  g.lineWidth = lw + 8; g.strokeStyle = OUT; g.beginPath(); g.arc(0, 0, r, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.moveTo(-r * 0.7, -r * 0.7); g.lineTo(r * 0.7, r * 0.7); g.lineCap = 'butt'; g.stroke();
  g.lineWidth = lw; g.strokeStyle = '#d8323a'; g.beginPath(); g.arc(0, 0, r, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.moveTo(-r * 0.68, -r * 0.68); g.lineTo(r * 0.68, r * 0.68); g.stroke();
  g.restore();
}
// phu suong / anh sang: lop mau trong suot cho ca khung
export function haze(g, color, a) { if (a <= 0) return; g.save(); g.globalAlpha = a; g.fillStyle = color; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3); g.restore(); }
export function vignette(g, a = 0.25, color = '#2a1a10') {
  g.save(); const gr = g.createRadialGradient(E.W / 2, E.H / 2, Math.min(E.W, E.H) * 0.35, E.W / 2, E.H / 2, Math.max(E.W, E.H) * 0.75);
  gr.addColorStop(0, alpha(color, 0)); gr.addColorStop(1, alpha(color, a)); g.fillStyle = gr; g.fillRect(0, 0, E.W, E.H); g.restore();
}
