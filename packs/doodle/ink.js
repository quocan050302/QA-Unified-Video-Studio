// ink.js — net ve doodle: vien den day, mau pastel phang, chu viet tay, mui ten, giay note, con dau, dau X.
// Moi toa do la don vi logic (1920x1080). Ham nhan tham so p (0..1) de "ve dan" / "hien dan".
import { E, clamp, lerp, ease, rng, noise, text, measure, alpha, shade, mix, phraseTime } from '/engine/core.js';

export const INK = '#1f1b18';
export const LW = 6;                                  // net vien chuan
export const PAL = {
  ink: INK, paper: '#fbf4e4', cream: '#f6ecd6', white: '#ffffff', sky: '#bfe2ef', skyDeep: '#9fd0e6', sea: '#a9d3e6', seaDeep: '#86bcd8',
  sand: '#ecd29c', sandDark: '#d9b673', ochre: '#e3a75b', orange: '#e8914f', terracotta: '#c96b4b', brick: '#b5523b', rust: '#a4553a',
  sage: '#9fbd8f', leaf: '#7fab73', moss: '#5f8f5a', forest: '#4f7a4e', grass: '#a9c98a',
  wood: '#b67c4b', woodDark: '#7d5534', stone: '#b9b2a6', stoneDark: '#8c857a', grey: '#6d7079', greyLight: '#c9c6c0',
  shirt: '#9dcdee', navy: '#34506f', red: '#d6473a', yellow: '#f6c94b', gold: '#e8b33c', pink: '#ef9fae', purple: '#9f86c0', blue: '#5b9bd5',
  skin: '#fde6cd', skinTan: '#e2b083', skinBrown: '#a96b42', skinDark: '#7a4a2d', hair: '#2b2420', hairGrey: '#b9b4ad',
  land: '#ecd29c', landHi: '#e7a56b', border: '#9b7a52',
};
export const FONT_HAND = '"Patrick Hand"';
export const FONT_BOLD = '"Baloo 2"';
export const FONT_BODY = '"Be Vietnam Pro"';

// ---------- thoi gian: at = so giay (tinh tu dau shot) hoac cum chu trong loi doc
export function T(info, at, def = 0) {
  if (at === undefined || at === null) return def;
  if (typeof at === 'number') return at;
  const t = phraseTime(at, info.start - 0.3); return t === null ? def : Math.max(0, t - info.start);
}
export const pop = (lt, at = 0, dur = 0.35) => (lt < at ? 0 : ease.outBack(clamp((lt - at) / dur)));
export const grow = (lt, at = 0, dur = 0.6) => (lt < at ? 0 : ease.inOut(clamp((lt - at) / dur)));
export const fadeIn = (lt, at = 0, dur = 0.3) => clamp((lt - at) / dur);
// nhun nhe (song) de hinh khong dung chet
export const bob = (lt, amp = 4, sp = 1.6, seed = 0) => Math.sin(lt * sp * Math.PI + seed) * amp;

// ---------- hinh co vien
export function shape(g, build, o = {}) {
  const { fill = PAL.white, lw = LW, ink = INK, a = 1, dash = null } = o;
  g.save(); g.globalAlpha *= a; g.beginPath(); build(g);
  if (fill) { g.fillStyle = fill; g.fill(o.rule || 'nonzero'); }
  if (lw > 0) { g.lineWidth = lw; g.strokeStyle = ink; g.lineJoin = 'round'; g.lineCap = 'round'; if (dash) g.setLineDash(dash); g.stroke(); }
  g.restore();
}
export const rect = (g, x, y, w, h, o = {}) => shape(g, (c) => { c.roundRect ? c.roundRect(x, y, w, h, o.r ?? 14) : c.rect(x, y, w, h); }, o);
export const ellipse = (g, x, y, rx, ry, o = {}) => shape(g, (c) => c.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), o.rot || 0, 0, Math.PI * 2), o);
export const circ = (g, x, y, r, o = {}) => ellipse(g, x, y, r, r, o);
// duong cong muot qua cac diem (Catmull-Rom), kin hoac ho
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
export const poly = (g, pts, o = {}) => shape(g, (c) => { c.moveTo(pts[0][0], pts[0][1]); pts.slice(1).forEach((p) => c.lineTo(p[0], p[1])); c.closePath(); }, o);
// net ve (khong to), p = phan da ve
export function line(g, pts, o = {}) {
  const { lw = LW, ink = INK, p = 1, smooth = true, dash = null, a = 1 } = o;
  if (p <= 0) return;
  const q = p >= 1 ? pts : cutPolyline(pts, p);
  g.save(); g.globalAlpha *= a; g.beginPath(); smooth && q.length > 2 ? smoothPath(g, q, false) : (g.moveTo(q[0][0], q[0][1]), q.slice(1).forEach((x) => g.lineTo(x[0], x[1])));
  g.lineWidth = lw; g.strokeStyle = ink; g.lineCap = 'round'; g.lineJoin = 'round'; if (dash) g.setLineDash(dash); g.stroke(); g.restore();
}
export function cutPolyline(pts, p) {
  const L = []; let tot = 0; for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); L.push(d); tot += d; }
  let need = tot * clamp(p), out = [pts[0]];
  for (let i = 1; i < pts.length; i++) { if (need >= L[i - 1]) { out.push(pts[i]); need -= L[i - 1]; } else { const k = need / (L[i - 1] || 1); out.push([lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)]); break; } }
  return out.length > 1 ? out : [pts[0], pts[0]];
}
// ong co vien (tay, chan): ve net den day roi net mau mong hon len tren
export function tube(g, pts, w, color, o = {}) {
  const b = o.border ?? 5;
  line(g, pts, { lw: w + b * 2, ink: o.ink || INK, smooth: o.smooth ?? true });
  line(g, pts, { lw: w, ink: color, smooth: o.smooth ?? true });
}

// ---------- mui ten ve tay. bend: do cong (+/- ty le do dai), p: ve dan
export function arrow(g, x0, y0, x1, y1, o = {}) {
  const { bend = 0.18, p = 1, lw = LW, ink = INK, head = 26, dash = null, both = false } = o;
  if (p <= 0) return;
  const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = x1 - x0, dy = y1 - y0;
  const cx = mx - dy * bend, cy = my + dx * bend, N = 24, pts = [];
  for (let i = 0; i <= N; i++) { const k = i / N; pts.push([(1 - k) * (1 - k) * x0 + 2 * (1 - k) * k * cx + k * k * x1, (1 - k) * (1 - k) * y0 + 2 * (1 - k) * k * cy + k * k * y1]); }
  const q = cutPolyline(pts, p);
  line(g, q, { lw, ink, smooth: false, dash });
  const headAt = (a, b) => { const ang = Math.atan2(b[1] - a[1], b[0] - a[0]); line(g, [[b[0] - Math.cos(ang - 0.5) * head, b[1] - Math.sin(ang - 0.5) * head], b, [b[0] - Math.cos(ang + 0.5) * head, b[1] - Math.sin(ang + 0.5) * head]], { lw, ink, smooth: false }); };
  if (q.length > 1) headAt(q[q.length - 2], q[q.length - 1]);
  if (both && p >= 1) headAt(pts[1], pts[0]);
}

// ---------- chu
export function label(g, str, x, y, o = {}) {
  const { size = 54, color = INK, align = 'center', p = 1, caps = false, rot = 0, font = FONT_HAND, weight = 400, stroke = 0, strokeColor = '#fff', a = 1 } = o;
  if (p <= 0 || !str) return;
  let s = caps ? String(str).toUpperCase() : String(str);
  if (p < 1) s = [...s].slice(0, Math.ceil([...s].length * p)).join('');
  g.save(); g.translate(x, y); g.rotate(rot);
  text(g, s, 0, 0, { size, font, weight, color, align, stroke, strokeColor, a });
  g.restore();
}
export function wrap(g, str, maxW, size, font = FONT_HAND, weight = 400) {
  if (CJK.test(str)) return wrapCJK(g, String(str), maxW, size, font, weight);
  const words = String(str).split(/\s+/); const lines = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (measure(g, t, size, font, weight) > maxW && cur) { lines.push(cur); cur = w; } else cur = t; }
  if (cur) lines.push(cur); return lines;
}
// tieng Nhat: ngat theo ky tu, khong de dau cau / kana nho dau dong (kinsoku), uu tien ngat sau 、。
const CJK = /[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]/;
const NOHEAD = /^[、。，．！？!?）」』〕】ー…ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ々]/;
function wrapCJK(g, str, maxW, size, font, weight) {
  const lines = []; let cur = '';
  for (const ch of str.replace(/\s+/g, ' ')) {
    const t = cur + ch;
    if (measure(g, t, size, font, weight) > maxW && cur && !NOHEAD.test(ch)) {
      let cut = Math.max(cur.lastIndexOf('、'), cur.lastIndexOf('。'), cur.lastIndexOf(' '));
      if (cut <= cur.length * 0.55) { // khong co dau cau: cat o cho hiragana -> kanji/katakana (dau cum tu)
        const cs = [...cur]; for (let i = cs.length - 1; i > cs.length * 0.45; i--) if (/[\u3041-\u309f]/.test(cs[i - 1]) && /[\u30a0-\u30ff\u3400-\u9fff]/.test(cs[i]) && !NOHEAD.test(cs[i])) { cut = cs.slice(0, i).join('').length - 1; break; }
      }
      if (cut + 1 > cur.length * 0.45) { lines.push(cur.slice(0, cut + 1).trim()); cur = cur.slice(cut + 1) + ch; } else { lines.push(cur.trim()); cur = ch; }
    } else cur = t;
  }
  if (cur.trim()) lines.push(cur.trim()); return lines;
}
// nhan co vet but da quang phia sau (kieu "tag")
export function tag(g, str, x, y, o = {}) {
  const { size = 46, color = INK, hl = PAL.yellow, p = 1, align = 'center', rot = -0.02 } = o;
  if (p <= 0) return;
  const w = measure(g, str, size, FONT_HAND, 400) + size * 0.8, h = size * 1.05;
  const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  g.save(); g.translate(x0 + w / 2, y); g.rotate(rot);
  g.fillStyle = alpha(hl, 0.75); g.beginPath(); g.roundRect(-w / 2, -h / 2, w * clamp(p * 1.6), h, h * 0.35); g.fill();
  label(g, str, 0, 2, { size, color, p: clamp((p - 0.25) / 0.75) });
  g.restore();
}
// giay note dan bang dinh
export function note(g, str, x, y, o = {}) {
  const { w = 560, size = 44, rot = -0.025, p = 1, tape = true, paper = '#fffdf6', color = INK, sub = null, align = 'center' } = o;
  if (p <= 0) return;
  const lines = wrap(g, str, w - 60, size); const lh = size * 1.15;
  const h = lines.length * lh + 50 + (sub ? size * 0.8 : 0);
  const s = 0.6 + 0.4 * ease.outBack(clamp(p));
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s); g.globalAlpha *= clamp(p * 2);
  g.fillStyle = 'rgba(60,40,20,0.14)'; g.beginPath(); g.roundRect(-w / 2 + 8, -h / 2 + 10, w, h, 6); g.fill();
  rect(g, -w / 2, -h / 2, w, h, { fill: paper, lw: 3, r: 6 });
  if (tape) { g.save(); g.rotate(0.06); g.fillStyle = 'rgba(232,214,170,0.85)'; g.fillRect(-60, -h / 2 - 16, 120, 34); g.restore(); }
  lines.forEach((l, i) => label(g, l, align === 'left' ? -w / 2 + 30 : 0, -h / 2 + 34 + lh * (i + 0.5), { size, color, align }));
  if (sub) label(g, sub, 0, h / 2 - size * 0.55, { size: size * 0.6, color: PAL.grey });
  g.restore();
}
// con dau do
export function stamp(g, str, x, y, o = {}) {
  const { size = 64, color = PAL.red, rot = -0.08, p = 1 } = o;
  if (p <= 0) return;
  const w = measure(g, str.toUpperCase(), size, FONT_BOLD, 800) + size * 0.9, h = size * 1.35;
  const s = p < 1 ? lerp(1.8, 1, ease.out(clamp(p))) : 1;
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s); g.globalAlpha *= clamp(p * 1.5) * 0.92;
  g.strokeStyle = color; g.lineWidth = size * 0.09; g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, 8); g.stroke();
  g.lineWidth = size * 0.035; g.beginPath(); g.roundRect(-w / 2 + size * 0.12, -h / 2 + size * 0.12, w - size * 0.24, h - size * 0.24, 5); g.stroke();
  text(g, str.toUpperCase(), 0, size * 0.04, { size, font: FONT_BOLD, weight: 800, color });
  g.restore();
}
// dau hieu
export function cross(g, x, y, r = 60, o = {}) {
  const p = o.p ?? 1; if (p <= 0) return; const c = o.color || PAL.red, lw = o.lw || r * 0.22;
  if (o.circle !== false) { g.save(); g.beginPath(); g.arc(x, y, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * clamp(p * 2)); g.lineWidth = lw * 0.7; g.strokeStyle = c; g.lineCap = 'round'; g.stroke(); g.restore(); }
  line(g, [[x - r * 0.55, y - r * 0.55], [x + r * 0.55, y + r * 0.55]], { lw, ink: c, p: clamp(p * 2 - 0.6), smooth: false });
  line(g, [[x + r * 0.55, y - r * 0.55], [x - r * 0.55, y + r * 0.55]], { lw, ink: c, p: clamp(p * 2 - 1), smooth: false });
}
export function ban(g, x, y, r = 60, o = {}) {
  const p = o.p ?? 1; if (p <= 0) return; const c = o.color || PAL.red, lw = o.lw || r * 0.18;
  g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2 * clamp(p * 1.5)); g.lineWidth = lw; g.strokeStyle = c; g.stroke(); g.restore();
  line(g, [[x - r * 0.7, y + r * 0.7], [x + r * 0.7, y - r * 0.7]], { lw, ink: c, p: clamp(p * 2 - 1), smooth: false });
}
export function check(g, x, y, r = 50, o = {}) {
  const p = o.p ?? 1; line(g, [[x - r * 0.6, y], [x - r * 0.15, y + r * 0.5], [x + r * 0.7, y - r * 0.6]], { lw: o.lw || r * 0.25, ink: o.color || '#4f9a4a', p, smooth: false });
}
export function qmark(g, x, y, size = 120, o = {}) { label(g, '?', x, y, { size, font: FONT_BOLD, weight: 800, color: o.color || INK, rot: o.rot || 0.08, a: o.a ?? 1 }); }
export function excl(g, x, y, size = 120, o = {}) { label(g, '!', x, y, { size, font: FONT_BOLD, weight: 800, color: o.color || PAL.red, rot: o.rot || -0.08 }); }

// bong bong loi noi / suy nghi. Tra ve vung noi dung {x,y,w,h}
export function bubble(g, x, y, w, h, o = {}) {
  const { tail = null, thought = false, p = 1, fill = PAL.white } = o;
  if (p <= 0) return null;
  const s = ease.outBack(clamp(p));
  g.save(); g.translate(x, y); g.scale(s, s);
  if (thought) {
    const pts = []; const N = 14;
    for (let i = 0; i < N; i++) { const a = (i / N) * Math.PI * 2; const r = 1 + 0.09 * Math.sin(i * 2.7); pts.push([Math.cos(a) * w / 2 * r, Math.sin(a) * h / 2 * r]); }
    shape(g, (c) => { for (let i = 0; i < N; i++) { const a = (i / N) * Math.PI * 2, b = ((i + 1) / N) * Math.PI * 2; const ax = Math.cos(a) * w / 2, ay = Math.sin(a) * h / 2, bx = Math.cos(b) * w / 2, by = Math.sin(b) * h / 2; const mxx = Math.cos((a + b) / 2) * w / 2 * 1.16, myy = Math.sin((a + b) / 2) * h / 2 * 1.16; if (i === 0) c.moveTo(ax, ay); c.quadraticCurveTo(mxx, myy, bx, by); } c.closePath(); }, { fill, lw: 5 });
    if (tail) { const [tx, ty] = [tail[0] - x, tail[1] - y]; [0.55, 0.78, 0.93].forEach((k, i) => circ(g, tx * k, ty * k, 16 - i * 4.5, { fill, lw: 4 })); }
  } else {
    shape(g, (c) => { c.roundRect(-w / 2, -h / 2, w, h, Math.min(w, h) * 0.3); }, { fill, lw: 5 });
    if (tail) { const tx = tail[0] - x, ty = tail[1] - y; const bx = clamp(tx, -w / 2 + 40, w / 2 - 40); poly(g, [[bx - 24, h / 2 - 4], [tx * 0.9, ty * 0.9], [bx + 24, h / 2 - 4]], { fill, lw: 5 }); g.fillStyle = fill; g.fillRect(bx - 20, h / 2 - 12, 40, 12); }
  }
  g.restore();
  return { x, y, w: w * s * 0.8, h: h * s * 0.75 };
}

// net mau phu cho vat the (bong ngan duoi chan)
export function shadow(g, x, y, w, a = 0.18) { g.save(); g.fillStyle = `rgba(60,40,20,${a})`; g.beginPath(); g.ellipse(x, y, w / 2, w * 0.09, 0, 0, Math.PI * 2); g.fill(); g.restore(); }
// ve 1 anh (anh AI) phu kin vung, co Ken Burns: z zoom, fx/fy tam (0..1)
export function cover(g, im, x, y, w, h, o = {}) {
  const { z = 1, fx = 0.5, fy = 0.5, dx = 0, dy = 0 } = o;
  const k = Math.max(w / im.width, h / im.height) * z, iw = im.width * k, ih = im.height * k;
  const ox = x + (w - iw) * fx + dx, oy = y + (h - ih) * fy + dy;
  g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.drawImage(im, ox, oy, iw, ih); g.restore();
}
export const seeded = (s) => rng(s);
export { noise, alpha, shade, mix, clamp, lerp, ease };
