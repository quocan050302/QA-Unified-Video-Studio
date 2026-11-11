// ui.js — do hoa tren man hinh: tieu de, so lieu, bieu do, so do khoa hoc, bong thoai, man ket.
// Moi ham nhan a (do hien 0..1) de tu fade; dung ease.outBack khi xuat hien.
import { E, V, clamp, lerp, ease, prog, rng, circle, ring, seg, poly, glow, linGrad, radGrad, alpha, shade, text, measure, FONTS, UI, rr, fill } from './core.js';

const pop = (a) => ease.outBack(clamp(a));

// tieu de lon phat sang (sau phan mo dau). lines: ['WHAT IF YOU', 'NEVER FORGOT?']
export function titleCard(g, t, o = {}) {
  const { lines = ['WHAT IF'], y = E.H * 0.46, a = 1, color = UI.cream, accent = UI.gold, size = V(96, 92) } = o;
  const k = ease.out(prog(t, 0, 0.8)) * a;
  lines.forEach((l, i) => {
    const last = i === lines.length - 1, sz = last ? size : size * 0.58;
    const yy = y + (i - (lines.length - 1) / 2) * size * 0.95 + (1 - k) * 30;
    text(g, l.toUpperCase(), E.W / 2, yy, { size: sz, color: last ? accent : color, spacing: last ? 3 : 8, glowColor: alpha(last ? accent : color, 0.8), a: k });
  });
}
// mot dong chu lon giua man hinh (cau hoi, chuong). Dong cuoi mau vang.
export function bigLine(g, t, str, o = {}) {
  const { y = E.H * 0.5, size = V(84, 78), color = UI.cream, a = 1, accentLast = true } = o;
  const words = String(str).split('·').map((x) => x.trim());
  const k = pop(prog(t, 0, 0.45)) * a;
  words.forEach((w, i) => text(g, w.toUpperCase(), E.W / 2, y + (i - (words.length - 1) / 2) * size * 1.05, { size, color: accentLast && i === words.length - 1 && words.length > 1 ? UI.gold : color, glowColor: alpha('#000', 0.6), a: clamp(k), spacing: 2 }));
}
// nhan goc man hinh (vd "100x", "DAY 3")
export function badge(g, o = {}) {
  const { str = '100x', x = E.W - V(150, 120), y = V(120, 200), a = 1, color = UI.gold } = o; if (a <= 0) return;
  const s = pop(a), w = measure(g, str, 46) + 44;
  g.save(); g.translate(x, y); g.scale(s, s); g.globalAlpha *= clamp(a);
  rr(g, -w / 2, -34, w, 68, 34); g.fillStyle = alpha('#0c0a10', 0.7); g.fill(); g.lineWidth = 3; g.strokeStyle = alpha(color, 0.9); g.stroke();
  text(g, str, 0, 2, { size: 46, color, glowColor: alpha(color, 0.6) }); g.restore();
}
// "NORMAL: 0.25 s"
export function readout(g, o = {}) {
  const { label = 'NORMAL:', value = '0.25 s', x = V(120, 80), y = E.H - V(150, 520), a = 1, color = UI.gold, size = 54 } = o; if (a <= 0) return;
  text(g, label, x, y - size * 0.75, { size: size * 0.4, font: FONTS.body, weight: 700, color: alpha(UI.cream, 0.85), align: 'left', spacing: 4, a });
  text(g, value, x, y, { size, color, align: 'left', glowColor: alpha(color, 0.5), a });
}
// so chay tu from -> to theo thoi gian t (bat dau t0, dai dur)
export function counter(g, t, o = {}) {
  const { from = 0, to = 100, t0 = 0, dur = 1.2, x = E.W / 2, y = E.H / 2, size = V(150, 140), prefix = '', suffix = '', decimals = 0, color = UI.gold, label = '', a = 1 } = o;
  const k = ease.out(prog(t, t0, t0 + dur)), v = lerp(from, to, k), str = prefix + v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;
  const s = pop(prog(t, t0 - 0.1, t0 + 0.3)) * a;
  g.save(); g.translate(x, y); g.scale(s || 0.001, s || 0.001);
  text(g, str, 0, 0, { size, color, glowColor: alpha(color, 0.6) });
  if (label) text(g, label.toUpperCase(), 0, size * 0.75, { size: size * 0.24, font: FONTS.body, weight: 700, color: UI.cream, spacing: 5 });
  g.restore();
}
// the du lieu co duong cong ve dan (vd duong cong quen lang)
export function dataCard(g, t, o = {}) {
  const { title = 'FORGETTING CURVE', x = E.W / 2, y = E.H / 2, w = V(980, 900), h = V(520, 620), pts = null, fn = (k) => Math.exp(-k * 3), a = 1, color = UI.gold, labels = [], t0 = 0.2, dur = 1.6, xLabel = '', yLabel = '' } = o;
  const k = ease.inOut(prog(t, t0, t0 + dur)), s = pop(prog(t, 0, 0.4)) * a;
  g.save(); g.translate(x, y); g.scale(s || 0.001, s || 0.001); g.translate(-w / 2, -h / 2);
  rr(g, 0, 0, w, h, 28); g.fillStyle = alpha('#0c0a14', 0.78); g.fill(); g.lineWidth = 2; g.strokeStyle = alpha(UI.cream, 0.15); g.stroke();
  text(g, title.toUpperCase(), 48, 60, { size: 34, font: FONTS.body, weight: 700, color: UI.cream, align: 'left', spacing: 4 });
  const px = 70, py = 110, pw = w - 140, ph = h - 190;
  seg(g, [[px, py], [px, py + ph], [px + pw, py + ph]], 3, alpha(UI.cream, 0.4));
  if (xLabel) text(g, xLabel, px + pw, py + ph + 36, { size: 24, font: FONTS.body, weight: 600, color: alpha(UI.cream, 0.7), align: 'right' });
  if (yLabel) text(g, yLabel, px - 10, py - 20, { size: 24, font: FONTS.body, weight: 600, color: alpha(UI.cream, 0.7), align: 'left' });
  const N = 80, P = []; for (let i = 0; i <= N * k; i++) { const u = i / N, v = pts ? interp(pts, u) : fn(u); P.push([px + u * pw, py + ph - v * ph]); }
  if (P.length > 1) { g.save(); g.shadowColor = color; g.shadowBlur = 20; seg(g, P, 7, color); g.restore(); circle(g, P[P.length - 1][0], P[P.length - 1][1], 11, '#ffffff'); }
  labels.forEach((l) => { const la = clamp((k - l.at) * 6); if (la > 0) { const v = pts ? interp(pts, l.at) : fn(l.at); const lx = px + l.at * pw, ly = py + ph - v * ph; circle(g, lx, ly, 12, l.color || UI.accent); text(g, l.text, lx + 22, ly - 40, { size: 64, color: l.color || UI.accent, align: 'left', a: la }); } });
  g.restore();
}
const interp = (pts, u) => { for (let i = 1; i < pts.length; i++) if (u <= pts[i][0]) { const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; return lerp(y0, y1, (u - x0) / (x1 - x0)); } return pts[pts.length - 1][1]; };
// so sanh hai thanh: [{label:'NORMAL', value:0.25, text:'0.25 s'}, {label:'YOU', value:0.025, text:'0.025 s', color: gold}]
export function compareBars(g, t, o = {}) {
  const { items = [], x = E.W / 2, y = E.H / 2, w = V(1100, 860), max = null, t0 = 0, stagger = 0.6, a = 1 } = o; const m = max || Math.max(...items.map((i) => i.value));
  items.forEach((it, i) => {
    const k = ease.out(prog(t, t0 + i * stagger, t0 + i * stagger + 0.9)) * a, yy = y + (i - (items.length - 1) / 2) * 130, c = it.color || UI.blue;
    text(g, it.label.toUpperCase(), x - w / 2, yy - 38, { size: 28, font: FONTS.body, weight: 700, color: UI.cream, align: 'left', spacing: 4, a: clamp(k * 3) });
    rr(g, x - w / 2, yy - 14, w, 28, 14); g.fillStyle = alpha(UI.cream, 0.08 * clamp(k * 3)); g.fill();
    rr(g, x - w / 2, yy - 14, Math.max(28, (w * it.value / m) * k), 28, 14); g.save(); g.shadowColor = c; g.shadowBlur = 18; g.fillStyle = c; g.fill(); g.restore();
    text(g, it.text || String(it.value), x - w / 2 + Math.max(28, (w * it.value / m) * k) + 20, yy + 2, { size: 40, color: c, align: 'left', a: clamp(k * 3) });
  });
}
// dong ho do dang ban nguyet, value 0..1
export function meter(g, t, o = {}) {
  const { x = E.W / 2, y = E.H * 0.6, r = 240, value = 0.8, t0 = 0, label = '', ticks = [], color = UI.gold, broken = false, a = 1 } = o;
  const k = ease.outElastic(prog(t, t0, t0 + 1.4)), v = value * k;
  g.save(); g.globalAlpha *= a;
  g.beginPath(); g.arc(x, y, r, Math.PI, 0); g.lineWidth = 30; g.strokeStyle = alpha(UI.cream, 0.12); g.stroke();
  const segs = [['#3fb950', 0, 0.5], ['#f2c21a', 0.5, 0.78], ['#ff6b5a', 0.78, 1]]; segs.forEach(([c, s0, s1]) => { g.beginPath(); g.arc(x, y, r, Math.PI + s0 * Math.PI, Math.PI + s1 * Math.PI); g.lineWidth = 30; g.strokeStyle = alpha(c, 0.85); g.stroke(); });
  ticks.forEach((tk) => { const ang = Math.PI + tk.at * Math.PI; text(g, tk.text, x + Math.cos(ang) * (r - 62), y + Math.sin(ang) * (r - 62), { size: 28, font: FONTS.body, weight: 700, color: UI.cream }); });
  const ang = Math.PI + Math.min(v, broken ? 1.12 : 1) * Math.PI; seg(g, [[x, y], [x + Math.cos(ang) * (r - 20), y + Math.sin(ang) * (r - 20)]], 9, '#ffffff'); circle(g, x, y, 18, '#ffffff');
  if (broken && v > 1) { for (let i = 0; i < 5; i++) seg(g, [[x + r * 0.95, y - 20 - i * 8], [x + r * 1.15 + i * 6, y - 60 - i * 22]], 3, alpha('#ffffff', 0.7)); }
  if (label) text(g, label.toUpperCase(), x, y + 70, { size: 36, color, spacing: 4 });
  g.restore();
}
// nhan co duong dan
export function callout(g, x, y, str, o = {}) {
  const { dx = 120, dy = -90, a = 1, color = UI.cream, size = 30 } = o; if (a <= 0) return;
  const k = ease.out(clamp(a)); seg(g, [[x, y], [x + dx * 0.6 * k, y + dy * k], [x + dx * k, y + dy * k]], 3, alpha(color, 0.8)); circle(g, x, y, 6, color);
  text(g, str, x + dx * k + (dx > 0 ? 12 : -12), y + dy * k, { size, font: FONTS.body, weight: 700, color, align: dx > 0 ? 'left' : 'right', a: k });
}
// thuoc do co mui ten "30 m"
export function dimension(g, x0, y0, x1, y1, str, o = {}) {
  const { a = 1, color = UI.gold } = o; if (a <= 0) return; const k = ease.out(clamp(a)); const xm = lerp(x0, x1, 0.5), ym = lerp(y0, y1, 0.5);
  const xa = lerp(xm, x0, k), ya = lerp(ym, y0, k), xb = lerp(xm, x1, k), yb = lerp(ym, y1, k); seg(g, [[xa, ya], [xb, yb]], 3, color);
  const ang = Math.atan2(y1 - y0, x1 - x0); [[xa, ya, ang + Math.PI], [xb, yb, ang]].forEach(([x, y, an]) => poly(g, [[x, y], [x - Math.cos(an - 0.4) * 18, y - Math.sin(an - 0.4) * 18], [x - Math.cos(an + 0.4) * 18, y - Math.sin(an + 0.4) * 18]], color));
  text(g, str, xm - Math.sin(ang) * 30, ym + Math.cos(ang) * -30, { size: 38, color, a: k, glowColor: alpha(color, 0.5) });
}
// nen so do khoa hoc (xanh navy luoi o)
export function blueprint(g, t, o = {}) {
  const { grid = 60, color = UI.blue } = o; fill(g, UI.bp);
  g.fillStyle = radGrad(g, E.W / 2, E.H / 2, 0, E.W * 0.7, [[0, alpha('#2a4a8a', 0.5)], [1, alpha('#000000', 0)]]); g.fillRect(0, 0, E.W, E.H);
  g.strokeStyle = alpha(color, 0.08); g.lineWidth = 1.5; g.beginPath(); for (let x = (t * 6) % grid; x < E.W; x += grid) { g.moveTo(x, 0); g.lineTo(x, E.H); } for (let y = 0; y < E.H; y += grid) { g.moveTo(0, y); g.lineTo(E.W, y); } g.stroke();
}
// net ve so do, hien dan theo k (0..1)
export function bpStroke(g, pts, k, o = {}) {
  const { color = UI.blue, w = 4 } = o; if (k <= 0) return; let L = 0; const d = []; for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); d.push(l); L += l; }
  let rem = L * clamp(k); const P = [pts[0]]; for (let i = 1; i < pts.length && rem > 0; i++) { if (rem >= d[i - 1]) { P.push(pts[i]); rem -= d[i - 1]; } else { const u = rem / d[i - 1]; P.push([lerp(pts[i - 1][0], pts[i][0], u), lerp(pts[i - 1][1], pts[i][1], u)]); rem = 0; } }
  g.save(); g.shadowColor = color; g.shadowBlur = 10; seg(g, P, w, color); g.restore();
}
// nguoi que dang net (cho so do)
export function lineFigure(g, x, y, s = 1, o = {}) {
  const { color = UI.blue, k = 1, pose = 'stand' } = o; const P = { head: [0, -175], neck: [0, -150], hip: [0, -92], hN: [12, -95], hF: [-12, -95], fN: [8, 0], fF: [-8, 0] };
  if (pose === 'run') { P.hN = [30, -130]; P.hF = [-28, -110]; P.fN = [36, -10]; P.fF = [-30, 0]; }
  const T = ([a, b]) => [x + a * s, y + b * s];
  g.save(); g.globalAlpha *= clamp(k * 2); ring(g, T(P.head)[0], T(P.head)[1], 24 * s, 4, color);
  [[P.neck, P.hip], [P.neck, P.hN], [P.neck, P.hF], [P.hip, P.fN], [P.hip, P.fF]].forEach(([a, b]) => bpStroke(g, [T(a), T(b)], k, { color, w: 4 })); g.restore();
}
// bong thoai
export function bubble(g, x, y, str, o = {}) {
  const { a = 1, size = 34, tail = [-40, 60], color = '#fbf6ee', ink = '#141018' } = o; if (a <= 0) return;
  const w = measure(g, str, size, FONTS.body, 700) + 50, h = size + 40, s = pop(a);
  g.save(); g.translate(x, y); g.scale(s, s); rr(g, -w / 2, -h / 2, w, h, h / 2); g.fillStyle = color; g.fill(); poly(g, [[-14, h / 2 - 4], [14, h / 2 - 4], [tail[0], h / 2 + tail[1] * 0.6]], color);
  text(g, str, 0, 2, { size, font: FONTS.body, weight: 700, color: ink }); g.restore();
}
// man ket: cau hoi + nut subscribe + ca dan nhan vat (drawCast(g) do canh tu ve)
export function endScreen(g, t, o = {}) {
  const { question = 'What would you do?', sub = 'SUBSCRIBE', y = E.H * 0.3 } = o;
  const k = ease.out(prog(t, 0, 0.8));
  text(g, question, E.W / 2, y, { size: V(70, 64), font: FONTS.serif, weight: 700, italic: true, color: UI.cream, a: k, glowColor: alpha('#000', 0.7) });
  const kb = pop(prog(t, 0.6, 1.1)); g.save(); g.translate(E.W / 2 - V(170, 0), y + V(120, 140)); g.scale(kb || 0.001, kb || 0.001);
  rr(g, -150, -40, 300, 80, 18); g.fillStyle = '#fbf6ee'; g.fill(); text(g, 'COMMENT', 0, 2, { size: 34, color: '#141018' }); g.restore();
  const ks = pop(prog(t, 0.8, 1.3)); g.save(); g.translate(E.W / 2 + V(170, 0), y + V(120, 250)); g.scale(ks || 0.001, ks || 0.001);
  rr(g, -150, -40, 300, 80, 40); g.fillStyle = '#e5484d'; g.fill(); text(g, sub, 0, 2, { size: 36, color: '#ffffff', spacing: 2 }); g.restore();
}
