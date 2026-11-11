// sets.js — boi canh nen toi net manh: set(g, ten, o) ve nen va tra ve "moc" (vi tri giuong, ghe, cua...) de dat nhan vat.
// Ten: bedroom city street lockers classroom court cafe gym stairs hill mirror kitchen void black doorway
// o chung: t (giay), gy (mat san 0..1), dim (0..1 lam toi), seed
import { E, clamp, lerp, ease, rng, noise, alpha, shade, mix, text } from '/engine/core.js';
import { PAL, accent, obj, box, oval, ln, fillAll, vgrad, light, beam, FONT_UI, FONT_NARR } from './ink.js';

const W = () => E.W, H = () => E.H;
const X = (k) => k * E.W, Y = (k) => k * E.H;
// khung doc: dat vat theo ti le cua chieu ngang 16:9 trung tam
const VX = (k) => (E.vertical ? E.W / 2 + (k - 0.5) * E.H * 0.5625 * 1.0 : k * E.W);

function wall(g, top = '#17171c', bot = '#1d1e24') { vgrad(g, [[0, top], [1, bot]]); }
function floor(g, gy, c = PAL.floor) { g.fillStyle = c; g.fillRect(-60, gy, E.W + 120, E.H - gy + 60); ln(g, [[-60, gy], [E.W + 60, gy]], { lw: 2, la: 0.45 }); }
export function rain(g, t, o = {}) {
  const r = rng(o.seed || 7), n = o.n || 160, sp = o.speed || 1400, len = o.len || 34;
  g.save(); g.strokeStyle = alpha(o.color || '#aab4c8', o.a ?? 0.35); g.lineWidth = o.lw || 1.6;
  for (let i = 0; i < n; i++) { const x0 = r() * (E.W + 200) - 100, y0 = r() * E.H, y = (y0 + t * sp * (0.8 + r() * 0.4)) % (E.H + 60) - 30, x = x0 - (y / E.H) * 60; g.beginPath(); g.moveTo(x, y); g.lineTo(x - 6, y + len); g.stroke(); }
  g.restore();
}
export function dust(g, t, o = {}) {
  const r = rng(o.seed || 5); g.save();
  for (let i = 0; i < (o.n || 40); i++) { const x = (r() * E.W + Math.sin(t * 0.3 + i) * 30), y = (r() * E.H - t * 12 * (0.5 + r())) % E.H; g.fillStyle = alpha(o.color || '#e8e2d0', 0.15 + r() * 0.25); g.beginPath(); g.arc(x, y < 0 ? y + E.H : y, 1 + r() * 2, 0, 7); g.fill(); }
  g.restore();
}
function moon(g, x, y, r) { light(g, x, y, r * 4, '#cfd8ff', 0.25); g.beginPath(); g.arc(x, y, r, 0, 7); g.fillStyle = PAL.moon; g.fill(); }
function skyGrad(g, x, y, w, h, kind, t = 0) {
  const S = { moon: ['#151a2c', '#202842'], night: ['#11131f', '#1c2238'], dawn: ['#3b2b4f', '#c8705a'], dusk: ['#2c2140', '#d47a5e'], day: ['#6e9cc8', '#a9cce6'], rain: ['#151821', '#232a38'], dark: ['#0f1014', '#15161b'] }[kind] || ['#151a2c', '#202842'];
  const gr = g.createLinearGradient(0, y, 0, y + h); gr.addColorStop(0, S[0]); gr.addColorStop(1, S[1]); g.fillStyle = gr; g.fillRect(x, y, w, h);
  if (kind === 'moon' || kind === 'night') moon(g, x + w * 0.62, y + h * 0.3, Math.min(w, h) * 0.09);
  if (kind === 'rain') { g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.strokeStyle = 'rgba(170,185,210,0.35)'; g.lineWidth = 1.2; const r = rng(3); for (let i = 0; i < 26; i++) { const xx = x + r() * w, yy = y + ((r() * h + t * 500) % h); g.beginPath(); g.moveTo(xx, yy); g.lineTo(xx - 3, yy + 16); g.stroke(); } g.restore(); }
  if (kind === 'day') { const r = rng(9); for (let i = 0; i < 4; i++) { g.beginPath(); g.ellipse(x + w * (0.15 + i * 0.25), y + h * (0.88 + r() * 0.05), w * 0.16, h * 0.2, 0, 0, 7); g.fillStyle = '#5c9a5a'; g.fill(); } }
}
export function windowBox(g, x, y, w, h, o = {}) {
  box(g, x - 8, y - 8, w + 16, h + 16, { fill: '#2a2c33', r: 6 });
  skyGrad(g, x, y, w, h, o.sky || 'moon', o.t);
  g.save(); g.strokeStyle = alpha(PAL.line, 0.8); g.lineWidth = 5; g.strokeRect(x, y, w, h); g.beginPath(); g.moveTo(x + w / 2, y); g.lineTo(x + w / 2, y + h); g.moveTo(x, y + h / 2); g.lineTo(x + w, y + h / 2); g.stroke(); g.restore();
}
// ---------- do vat
export function digitClock(g, x, y, s, o = {}) {
  const w = s * 1.6, h = s * 0.8, col = o.color || PAL.clock;
  box(g, x - w / 2, y - h, w, h, { fill: '#202127', r: s * 0.12 });
  const blink = o.blink ? (Math.floor((o.t || 0) * 2) % 2 === 0) : true;
  let str = String(o.time ?? '3:17'); if (!blink) str = str.replace(':', ' ');
  g.save(); g.shadowColor = col; g.shadowBlur = s * 0.25;
  text(g, str, x, y - h / 2 + s * 0.02, { size: s * 0.5, font: '"Be Vietnam Pro"', weight: 700, color: col, spacing: 2 }); g.restore();
  light(g, x, y - h / 2, s * 1.4, col, 0.12);
  if (o.ring) { const k = Math.sin((o.t || 0) * 26) > 0; if (k) for (const d of [-1, 1]) for (let i = 0; i < 2; i++) ln(g, [[x + d * (w / 2 + 10 + i * 12), y - h * 0.9 + i * 6], [x + d * (w / 2 + 22 + i * 12), y - h * 1.1 + i * 6]], { color: col, lw: 3, la: 0.9 }); }
}
export function calendar(g, x, y, w, o = {}) {
  const h = w * 1.1, col = o.headColor || '#c9463d';
  box(g, x, y, w, h, { fill: '#e9e6df', line: '#6d6f76', r: 4 });
  g.fillStyle = col; g.fillRect(x + 1, y + 1, w - 2, h * 0.2);
  text(g, o.month || 'OCT', x + w / 2, y + h * 0.105, { size: h * 0.12, font: '"Be Vietnam Pro"', weight: 700, color: '#fff' });
  const cw = (w - 12) / 7, ch = (h * 0.78 - 8) / 5, n = Math.round(o.fill ?? 0), mode = o.mode || 'x', mc = o.color || (mode === 'x' ? '#d23b33' : accent());
  for (let i = 0; i < 35; i++) {
    const cx = x + 6 + (i % 7) * cw, cy = y + h * 0.22 + 4 + Math.floor(i / 7) * ch;
    g.fillStyle = '#d6d2c9'; g.fillRect(cx + 1, cy + 1, cw - 2, ch - 2);
    if (i < n) { if (mode === 'x') { g.strokeStyle = mc; g.lineWidth = Math.max(1.5, cw * 0.12); g.beginPath(); g.moveTo(cx + 3, cy + 3); g.lineTo(cx + cw - 3, cy + ch - 3); g.moveTo(cx + cw - 3, cy + 3); g.lineTo(cx + 3, cy + ch - 3); g.stroke(); } else { g.fillStyle = mc; g.fillRect(cx + 1, cy + 1, cw - 2, ch - 2); } }
  }
}
export function deskLamp(g, x, y, s, on = true) {
  ln(g, [[x, y], [x + s * 0.25, y - s * 0.6], [x - s * 0.05, y - s * 0.95]], { lw: s * 0.05, color: '#6b6e77', la: 1 });
  obj(g, (c) => { c.moveTo(x - s * 0.05, y - s * 0.95); c.lineTo(x - s * 0.4, y - s * 0.7); c.lineTo(x - s * 0.15, y - s * 1.12); c.closePath(); }, { fill: '#5a5d66' });
  box(g, x - s * 0.2, y - s * 0.06, s * 0.4, s * 0.08, { fill: '#4a4d55', r: 3 });
  if (on) { beam(g, x - s * 0.3, y - s * 0.82, x - s * 1.2, x + s * 0.6, y + s * 0.05, PAL.lamp, 0.22); light(g, x - s * 0.3, y - s * 0.8, s * 1.6, PAL.lamp, 0.35); }
}
export function books(g, x, y, s) { const cs = ['#3f6ea8', '#c9463d', '#5f8f5a', '#e8b33c', '#7b6a8a']; for (let i = 0; i < 5; i++) box(g, x - s * 0.5 + (i % 2) * 6, y - (i + 1) * s * 0.13, s * (0.9 - i * 0.05), s * 0.12, { fill: cs[i], line: '#222', r: 2, la: 0.4 }); }
export function laptop(g, x, y, s, o = {}) {
  const c = o.color || '#9fb6ff';
  obj(g, (k) => { k.moveTo(x - s * 0.55, y - 2); k.lineTo(x + s * 0.55, y - 2); k.lineTo(x + s * 0.62, y + 4); k.lineTo(x - s * 0.62, y + 4); k.closePath(); }, { fill: '#3a3d45' });
  obj(g, (k) => { k.moveTo(x - s * 0.5, y - 4); k.lineTo(x - s * 0.42, y - s * 0.72); k.lineTo(x + s * 0.48, y - s * 0.72); k.lineTo(x + s * 0.5, y - 4); k.closePath(); }, { fill: o.on ? c : '#202127' });
  if (o.on) light(g, x, y - s * 0.4, s * 2.2, c, 0.28);
}
export function chair(g, x, gy, s, f = 1) {
  ln(g, [[x - f * s * 0.25, gy - s * 0.95], [x - f * s * 0.25, gy]], { lw: 5, color: '#5c5f68', la: 1 });
  ln(g, [[x - f * s * 0.25, gy - s * 0.5], [x + f * s * 0.25, gy - s * 0.5], [x + f * s * 0.25, gy]], { lw: 5, color: '#5c5f68', la: 1 });
  box(g, x - s * 0.3, gy - s * 0.54, s * 0.6, s * 0.07, { fill: '#3a3d45', r: 3 });
}
export function table(g, x, gy, w, h, o = {}) { box(g, x - w / 2, gy - h, w, h * 0.08, { fill: o.fill || '#3a3d45', r: 3 }); ln(g, [[x - w * 0.42, gy - h], [x - w * 0.42, gy]], { lw: 4, la: 0.7 }); ln(g, [[x + w * 0.42, gy - h], [x + w * 0.42, gy]], { lw: 4, la: 0.7 }); }
export function door(g, x, gy, w, h, o = {}) {
  box(g, x - w / 2, gy - h, w, h, { fill: o.open ? '#0d0d10' : '#2b2d34', r: 3 });
  if (o.open) { const k = o.open; g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = alpha(o.lightColor || PAL.lamp, 0.55 * k); g.fillRect(x - w / 2 + 4, gy - h + 4, w * k - 8, h - 8); g.restore(); beam(g, x, gy - h * 0.5, x - w * 0.2, x + w * 1.6, gy + E.H * 0.2, o.lightColor || PAL.lamp, 0.18 * k); }
  else { oval(g, x + w * 0.35, gy - h * 0.48, 5, 5, { fill: '#9a9da6', line: null }); }
}
export function punchBag(g, x, y, s, o = {}) {
  const sw = Math.sin((o.t || 0) * 5) * (o.swing ?? 0.04);
  g.save(); g.translate(x, y); g.rotate(sw); ln(g, [[0, 0], [0, s * 0.2]], { lw: 3, color: '#777' });
  box(g, -s * 0.18, s * 0.2, s * 0.36, s * 0.8, { fill: o.color || '#c4302b', line: '#5e1512', r: s * 0.12, la: 1 }); g.restore();
  light(g, x, y + s * 0.6, s * 0.7, o.color || '#c4302b', 0.12);
}
export function barbell(g, x, gy, s) { ln(g, [[x - s * 0.7, gy - s * 0.18], [x + s * 0.7, gy - s * 0.18]], { lw: 6, color: '#8a8d96', la: 1 }); for (const d of [-1, 1]) for (let i = 0; i < 2; i++) box(g, x + d * s * (0.5 + i * 0.09) - 9, gy - s * 0.18 - s * (0.18 - i * 0.04), 18, s * (0.36 - i * 0.08), { fill: '#202127', r: 4 }); }
export function plant(g, x, gy, s) { box(g, x - s * 0.18, gy - s * 0.3, s * 0.36, s * 0.3, { fill: '#7a5340', r: 3 }); const r = rng(4); for (let i = 0; i < 7; i++) { const a = -Math.PI / 2 + (r() - 0.5) * 1.6; obj(g, (c) => c.ellipse(x + Math.cos(a) * s * 0.3, gy - s * 0.3 + Math.sin(a) * s * 0.35, s * 0.07, s * 0.24, a + Math.PI / 2, 0, 7), { fill: '#4f7a4e', line: '#2c4a2c', la: 0.6 }); } }
export function bench(g, x, gy, w) { box(g, x - w / 2, gy - 52, w, 10, { fill: '#6b4e3a', r: 3 }); box(g, x - w / 2, gy - 82, w, 9, { fill: '#6b4e3a', r: 3 }); ln(g, [[x - w * 0.4, gy - 42], [x - w * 0.4, gy]], { lw: 4 }); ln(g, [[x + w * 0.4, gy - 42], [x + w * 0.4, gy]], { lw: 4 }); }
export function streetLamp(g, x, gy, h, on = true) { ln(g, [[x, gy], [x, gy - h], [x + h * 0.12, gy - h - 10]], { lw: 4, color: '#555861', la: 1 }); if (on) { light(g, x + h * 0.12, gy - h - 4, h * 0.35, PAL.lamp, 0.5); beam(g, x + h * 0.12, gy - h, x - h * 0.15, x + h * 0.4, gy, PAL.lamp, 0.08); } }

function skyline(g, gy, o = {}) {
  const r = rng(o.seed || 11), n = o.n || 14, col = o.color || '#1b1622', lit = o.lit ?? 0.25;
  for (let i = 0; i < n; i++) {
    const w = E.W / n * (0.8 + r() * 0.6), x = i * E.W / n - 20, h = E.H * (o.hmin ?? 0.18) + r() * E.H * (o.hvar ?? 0.28);
    obj(g, (c) => c.rect(x, gy - h, w, h + 4), { fill: col, line: o.line ?? null, la: 0.25 });
    if (lit) for (let k = 0; k < h / 34; k++) for (let j = 0; j < w / 30; j++) if (r() < lit) { g.fillStyle = alpha(PAL.lamp, 0.35 + r() * 0.4); g.fillRect(x + 10 + j * 30, gy - h + 14 + k * 34, 8, 12); }
  }
}

// ---------- boi canh
// moc tra ve: { gy, bed: {head:[x,y], sit:[x,y], lie:[x,y]}, clock:[x,y], desk:{seat:[x,y]}, door:[x,y], ... }
export function set(g, kind = 'bedroom', o = {}) {
  const t = o.t || 0, gy = Y(o.gy ?? (E.vertical ? 0.7 : 0.8)), M = { gy };
  switch (kind) {
    case 'black': fillAll(g, '#0b0b0d'); break;
    case 'void': {
      fillAll(g, '#0d0d10'); const sx = X(o.spot ?? 0.5); beam(g, sx, -20, sx - E.W * 0.16, sx + E.W * 0.16, gy + 40, '#e8e4dc', 0.13);
      g.save(); g.scale(1, 0.18); light(g, sx, gy / 0.18, E.W * 0.16, '#e8e4dc', 0.22); g.restore(); ln(g, [[-60, gy], [E.W + 60, gy]], { lw: 1.5, la: 0.18 }); dust(g, t, { n: 30 }); break; }
    case 'bedroom': {
      wall(g); floor(g, gy);
      const bx = VX(o.bedX ?? 0.27), bw = E.vertical ? E.W * 0.5 : X(o.bedW ?? 0.33), bh = E.H * 0.11;
      // cua so + chum trang
      const wx = VX(o.windowX ?? 0.5), wy = Y(0.24), ww = E.vertical ? E.W * 0.26 : X(0.115), wh = Y(0.2);
      if (o.window !== false) { windowBox(g, wx, wy, ww, wh, { sky: o.sky || 'moon', t }); if ((o.sky || 'moon') === 'moon' || o.sky === 'dawn') beam(g, wx + ww / 2, wy + wh, bx + bw * 0.2, bx + bw * 0.9, gy + 30, o.sky === 'dawn' ? '#ffb48a' : '#c8d4ff', 0.07); }
      // lich + ban hoc
      if (o.calendar !== false && !E.vertical) calendar(g, X(o.calX ?? 0.79), Y(0.26), X(0.055), o.calendar || {});
      if (o.desk !== false && !E.vertical) {
        const dx = X(o.deskX ?? 0.84), dw = X(0.15), dh = E.H * 0.17; table(g, dx, gy, dw, dh); chair(g, dx - dw * 0.15, gy, E.H * 0.2, -1); books(g, dx + dw * 0.18, gy - dh, 60); deskLamp(g, dx - dw * 0.38, gy - dh, 90, o.lamp);
        if (o.laptop) laptop(g, dx - dw * 0.02, gy - dh, 70, { on: o.laptop !== 'off', t, color: o.laptopColor });
        M.desk = { seat: [dx - dw * 0.15, gy], top: [dx, gy - dh] };
      }
      if (o.door) door(g, X(o.doorX ?? 0.95), gy, X(0.07), E.H * 0.42, { open: o.doorOpen });
      // tu dau giuong + dong ho
      const nx = bx - E.W * (E.vertical ? 0.1 : 0.045);
      box(g, nx - 50, gy - 95, 100, 95, { fill: '#26272d', r: 6 }); ln(g, [[nx - 40, gy - 55], [nx + 40, gy - 55]], { lw: 1.5, la: 0.5 }); oval(g, nx, gy - 30, 4, 4, { fill: '#888', line: null });
      if (o.clock !== false) digitClock(g, nx, gy - 97, 62, { time: o.clock ?? '3:17', ring: o.ring, blink: o.blink, t });
      M.clock = [nx, gy - 130];
      // giuong
      ln(g, [[bx, gy], [bx, gy - E.H * 0.25]], { lw: 9, color: '#33353d', la: 1 }); ln(g, [[bx, gy - E.H * 0.25], [bx, gy - E.H * 0.13]], { lw: 3, la: 0.5 });
      box(g, bx, gy - bh, bw, bh * 0.55, { fill: '#2c2e35', r: 4 }); ln(g, [[bx + bw - 6, gy - bh * 0.5], [bx + bw - 6, gy]], { lw: 6, color: '#33353d', la: 1 });
      M.bed = { head: [bx + bw * 0.1, gy - bh - 22], sit: [bx + bw * 0.62, gy], lie: [bx + bw * 0.4, gy - bh], x0: bx, x1: bx + bw, top: gy - bh };
      M.pillow = () => oval(g, bx + bw * 0.1, gy - bh - 6, bw * 0.09, 16, { fill: PAL.pillow });
      M.blanket = (occupied) => obj(g, (c) => { c.moveTo(bx + bw * (occupied ? 0.17 : 0.24), gy - bh + 4); if (occupied) { c.quadraticCurveTo(bx + bw * 0.19, gy - bh - 34, bx + bw * 0.35, gy - bh - 28); c.quadraticCurveTo(bx + bw * 0.6, gy - bh - 36, bx + bw * 0.8, gy - bh - 18); } else c.quadraticCurveTo(bx + bw * 0.6, gy - bh - 14, bx + bw * 0.95, gy - bh - 4); c.lineTo(bx + bw * 0.98, gy - bh + bh * 0.5); c.lineTo(bx + bw * 0.16, gy - bh + bh * 0.5); c.closePath(); }, { fill: PAL.blanket, line: '#8c95b5', la: 0.5 });
      if (!o.occupied) { M.pillow(); M.blanket(false); }
      break; }
    case 'city': {
      const tm = o.time || 'dusk', S = { dusk: ['#251c35', '#6a3f5c', '#d0745a'], night: ['#0c0f1c', '#182038', '#25304e'], dawn: ['#2a2a4a', '#8a5a78', '#f0a070'], day: ['#5c8fc4', '#8fb8de', '#cfe2f0'] }[tm] || ['#251c35', '#6a3f5c', '#d0745a'];
      vgrad(g, [[0, S[0]], [0.55, S[1]], [1, S[2]]], 0, gy);
      if (tm !== 'night') light(g, X(0.5), gy, E.W * 0.45, tm === 'day' ? '#ffffff' : '#ffb070', 0.35); else moon(g, X(0.8), Y(0.25), 22);
      skyline(g, gy, { color: tm === 'day' ? '#7d8fa6' : '#2a2033', seed: 3, hmin: 0.22, hvar: 0.3, lit: tm === 'day' ? 0 : 0.18 });
      skyline(g, gy, { color: tm === 'day' ? '#5d6e86' : '#17131d', seed: 8, n: 9, hmin: 0.1, hvar: 0.22, lit: tm === 'day' ? 0 : 0.3 });
      g.fillStyle = '#1a1a20'; g.fillRect(-60, gy, E.W + 120, E.H); ln(g, [[-60, gy], [E.W + 60, gy]], { lw: 2, la: 0.35 });
      for (let i = 0; i < 12; i++) { const x = ((i * 220 - t * (o.scroll || 0) * 60) % (E.W + 220) + E.W + 220) % (E.W + 220) - 110; g.fillStyle = 'rgba(200,200,210,0.25)'; g.fillRect(x, gy + (E.H - gy) * 0.55, 90, 5); }
      for (const k of o.lamps || [0.12, 0.88]) streetLamp(g, X(k), gy, E.H * 0.3);
      if (o.birds) { g.save(); g.strokeStyle = '#2a2030'; g.lineWidth = 2.5; for (let i = 0; i < 3; i++) { const bx = X(0.7) + i * 34 + t * 20, by = Y(0.25) + i * 10 + Math.sin(t * 3 + i) * 4; g.beginPath(); g.moveTo(bx - 8, by); g.quadraticCurveTo(bx - 3, by - 6, bx, by); g.quadraticCurveTo(bx + 3, by - 6, bx + 8, by); g.stroke(); } g.restore(); }
      break; }
    case 'street': {
      wall(g, '#15171d', '#1d212a'); skyline(g, gy - E.H * 0.05, { color: '#1b1f27', seed: 21, n: 10, hmin: 0.3, hvar: 0.25, lit: 0.12 });
      g.fillStyle = '#16181d'; g.fillRect(-60, gy, E.W + 120, E.H); ln(g, [[-60, gy], [E.W + 60, gy]], { lw: 2, la: 0.4 });
      if (o.neonDoor !== undefined && o.neonDoor !== false) { const dx = X(o.neonDoor === true ? 0.32 : o.neonDoor), dh = E.H * 0.34; box(g, dx - 60, gy - dh, 120, dh, { fill: '#0b0b0f', line: accent(), la: 0.9, lw: 3 }); g.save(); g.globalCompositeOperation = 'lighter'; const gr = g.createLinearGradient(0, gy - dh, 0, gy); gr.addColorStop(0, alpha(accent(), 0.05)); gr.addColorStop(1, alpha(accent(), 0.45)); g.fillStyle = gr; g.fillRect(dx - 56, gy - dh + 4, 112, dh - 4); g.restore(); light(g, dx, gy - dh * 0.5, dh * 0.8, accent(), 0.2); M.neon = [dx, gy]; }
      if (o.busstop !== false) { const sx = X(o.busX ?? 0.72), sw = X(0.2); box(g, sx - sw / 2, gy - E.H * 0.36, sw, 10, { fill: '#30333b' }); ln(g, [[sx - sw / 2 + 6, gy - E.H * 0.36], [sx - sw / 2 + 6, gy]], { lw: 5 }); ln(g, [[sx + sw / 2 - 6, gy - E.H * 0.36], [sx + sw / 2 - 6, gy]], { lw: 5 }); g.fillStyle = 'rgba(160,180,210,0.07)'; g.fillRect(sx - sw / 2 + 8, gy - E.H * 0.35, sw - 16, E.H * 0.3); bench(g, sx, gy, sw * 0.7); light(g, sx, gy - E.H * 0.34, sw * 0.6, '#d8e4ff', 0.25); box(g, sx + sw / 2 + 20, gy - E.H * 0.42, 34, 26, { fill: '#2f6fd0', r: 3 }); M.bus = { seat: [sx, gy], x: sx }; }
      streetLamp(g, X(o.lampX ?? 0.55), gy, E.H * 0.42);
      if (o.rain !== false) { rain(g, t, { n: 180 }); g.save(); g.globalAlpha = 0.12; g.fillStyle = '#9fb0d0'; for (let i = 0; i < 10; i++) g.fillRect(X(0.05 + i * 0.1), gy + 12 + (i % 3) * 18, 70, 3); g.restore(); }
      break; }
    case 'lockers': {
      wall(g, '#1c1d22', '#23252c'); floor(g, gy, '#1e1f24'); const n = 16, lw = E.W / n, top = gy - E.H * 0.5, cs = ['#3d5277', '#3d5277', '#6b3f3f', '#3d5277', '#3d5277', '#3d5277', '#6b3f3f'];
      for (let i = 0; i < n; i++) { const x = i * lw; box(g, x + 2, top, lw - 4, E.H * 0.5, { fill: cs[(i * 3) % cs.length], line: '#151619', la: 0.8, r: 3 }); ln(g, [[x + lw * 0.3, top + E.H * 0.12], [x + lw * 0.3, top + E.H * 0.18]], { lw: 3, la: 0.6 }); for (let k = 0; k < 3; k++) ln(g, [[x + lw * 0.55, top + 20 + k * 10], [x + lw * 0.8, top + 20 + k * 10]], { lw: 2, la: 0.3 }); }
      if (o.board !== false) { const bx = X(o.boardX ?? 0.68); box(g, bx - 110, top - E.H * 0.17, 220, 130, { fill: '#8a6a45', r: 8 }); const nc = ['#f4e48b', '#bcdaf5', '#f4e48b', '#f2f0ea']; for (let i = 0; i < 4; i++) box(g, bx - 90 + i * 46, top - E.H * 0.15 + (i % 2) * 22, 38, 42, { fill: nc[i], line: null, r: 2 }); }
      break; }
    case 'classroom': {
      wall(g, '#1e2027', '#24262e'); floor(g, gy, '#1d1e23'); windowBox(g, X(0.08), Y(0.18), X(0.16), Y(0.28), { sky: o.sky || 'day', t });
      box(g, X(0.62), Y(0.17), X(0.3), Y(0.3), { fill: '#2b3a33', line: '#8c7a68', r: 4 }); text(g, o.board || 'x + 4 = 10', X(0.77), Y(0.27), { size: 46, font: FONT_NARR, weight: 700, color: '#d8ddd5' }); text(g, 'x = ?', X(0.72), Y(0.37), { size: 46, font: FONT_NARR, weight: 700, color: '#d8ddd5' });
      oval(g, X(0.47), Y(0.18), 26, 26, { fill: '#e9e6df', line: '#555' }); ln(g, [[X(0.47), Y(0.18)], [X(0.47), Y(0.18) - 16]], { color: '#222', lw: 3, la: 1 }); ln(g, [[X(0.47), Y(0.18)], [X(0.47) + 12, Y(0.18)]], { color: '#222', lw: 3, la: 1 });
      for (const k of o.desks || [0.2, 0.45, 0.7]) table(g, X(k) + 60, gy, 150, E.H * 0.16, { fill: '#5a4a3c' });
      break; }
    case 'court': {
      vgrad(g, [[0, '#2a2038'], [1, '#7a4a5c']], 0, gy - E.H * 0.1); skyline(g, gy - E.H * 0.1, { color: '#2a2234', seed: 5, n: 12, hmin: 0.12, hvar: 0.18, lit: 0.25 });
      g.fillStyle = '#b77a45'; g.fillRect(-60, gy - E.H * 0.1, E.W + 120, E.H); ln(g, [[-60, gy + E.H * 0.06], [E.W + 60, gy + E.H * 0.06]], { lw: 3, color: '#f0d6b0', la: 0.5 });
      g.save(); g.strokeStyle = 'rgba(200,200,210,0.25)'; g.lineWidth = 1.5; const ft = gy - E.H * 0.42, fb = gy - E.H * 0.1; for (let x = -200; x < E.W + 200; x += 26) { g.beginPath(); g.moveTo(x, fb); g.lineTo(x + (fb - ft), ft); g.moveTo(x, ft); g.lineTo(x + (fb - ft), fb); g.stroke(); } g.restore(); ln(g, [[-60, gy - E.H * 0.42], [E.W + 60, gy - E.H * 0.42]], { lw: 3, la: 0.5 });
      const hx = X(o.hoopX ?? 0.84); ln(g, [[hx, gy], [hx, gy - E.H * 0.5]], { lw: 7, color: '#3d4048', la: 1 }); box(g, hx - 70, gy - E.H * 0.56, 90, 60, { fill: '#e9e6df', line: '#444', r: 2 }); oval(g, hx - 80, gy - E.H * 0.47, 26, 6, { fill: null, line: '#e2562b', lw: 4, la: 1 });
      streetLamp(g, X(0.55), gy - E.H * 0.1, E.H * 0.35); bench(g, X(o.benchX ?? 0.3), gy - E.H * 0.06, 220); M.bench = [X(o.benchX ?? 0.3), gy - E.H * 0.06];
      break; }
    case 'cafe': {
      wall(g, '#2a2019', '#33271f'); floor(g, gy, '#241b15');
      const wx = X(0.22), ww = X(0.56); box(g, wx, Y(0.16), ww, Y(0.42), { fill: '#141821', line: '#6b5644', r: 4 }); g.save(); g.beginPath(); g.rect(wx, Y(0.16), ww, Y(0.42)); g.clip(); skyline(g, Y(0.58), { color: '#1d2230', seed: 13, n: 9, hmin: 0.12, hvar: 0.2, lit: 0.35 }); rain(g, t, { n: 70, a: 0.3 }); g.restore();
      ln(g, [[wx + ww / 2, Y(0.16)], [wx + ww / 2, Y(0.58)]], { lw: 4, color: '#6b5644', la: 1 });
      const lx = X(o.lampX ?? 0.5); ln(g, [[lx, -10], [lx, Y(0.2)]], { lw: 2, color: '#666' }); obj(g, (c) => { c.moveTo(lx - 40, Y(0.26)); c.lineTo(lx + 40, Y(0.26)); c.lineTo(lx + 12, Y(0.2)); c.lineTo(lx - 12, Y(0.2)); c.closePath(); }, { fill: '#c99a3a', line: null }); light(g, lx, Y(0.27), E.H * 0.55, PAL.lamp, 0.45);
      table(g, lx, gy, 260, E.H * 0.2, { fill: '#5a3f2c' }); M.table = { left: [lx - 190, gy], right: [lx + 190, gy], top: gy - E.H * 0.2 };
      plant(g, X(0.9), gy, 160);
      break; }
    case 'gym': {
      wall(g, '#141417', '#1a1a1e'); floor(g, gy, '#111114'); for (let i = 0; i < 8; i++) ln(g, [[X(i / 7), gy], [X(i / 7) + (i - 3.5) * 40, E.H]], { lw: 1, la: 0.12 });
      beam(g, X(o.spot ?? 0.5), -20, X(o.spot ?? 0.5) - 380, X(o.spot ?? 0.5) + 380, gy + 60, '#ffe2b0', 0.1);
      if (o.bag !== false) punchBag(g, X(o.bagX ?? 0.62), Y(0.1), E.H * 0.42, { t, swing: o.swing });
      if (o.barbell) barbell(g, X(o.barbellX ?? 0.3), gy, 220);
      break; }
    case 'stairs': {
      fillAll(g, '#0f0f12'); const n = 9, sx = X(0.1), sy = gy, dx = (E.W * 0.85) / n, dy = (E.H * 0.62) / n;
      obj(g, (c) => { c.moveTo(sx, sy + 200); for (let i = 0; i < n; i++) { c.lineTo(sx + i * dx, sy - i * dy); c.lineTo(sx + (i + 1) * dx, sy - i * dy); } c.lineTo(E.W + 60, sy - n * dy); c.lineTo(E.W + 60, E.H + 60); c.lineTo(sx, E.H + 60); c.closePath(); }, { fill: '#25262c', line: PAL.line, la: 0.5 });
      if (o.top !== false) light(g, E.W * 0.98, sy - n * dy, E.H * 0.5, o.topColor || '#ffd9a0', 0.35);
      M.step = (k) => [sx + (k + 0.5) * dx, sy - k * dy]; M.steps = n;
      break; }
    case 'hill': {
      vgrad(g, [[0, '#2a1c2e'], [0.45, '#6b3446'], [0.8, '#c4604a'], [1, '#e8915a']], 0, gy); light(g, X(0.55), gy - E.H * 0.06, E.W * 0.4, '#ffb070', 0.45);
      for (const [c, a, s] of [['#4a2a3a', 0.18, 2], ['#3a2030', 0.12, 5]]) { g.fillStyle = c; g.beginPath(); g.moveTo(-60, gy); const r = rng(s); for (let i = 0; i <= 10; i++) g.lineTo(-60 + i * (E.W + 120) / 10, gy - E.H * a * (0.4 + r())); g.lineTo(E.W + 60, gy); g.closePath(); g.fill(); }
      g.fillStyle = '#c87a50'; g.fillRect(-60, gy, E.W + 120, E.H * 0.04); g.fillStyle = '#18121a'; g.beginPath(); g.moveTo(X(0.18), E.H + 20); g.quadraticCurveTo(X(0.45), gy - E.H * 0.33, X(0.72), E.H + 20); g.closePath(); g.fill();
      ln(g, [[X(0.25), E.H * 0.97], [X(0.45), gy - E.H * 0.16]], { color: '#e8915a', lw: 2, la: 0.4 });
      M.top = [X(0.45), gy - E.H * 0.165];
      break; }
    case 'mirror': {
      wall(g, '#1b1d22', '#202228'); g.save(); g.strokeStyle = 'rgba(200,205,215,0.09)'; g.lineWidth = 2; for (let x = 0; x < E.W; x += 70) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, E.H); g.stroke(); } for (let y = 0; y < E.H; y += 70) { g.beginPath(); g.moveTo(0, y); g.lineTo(E.W, y); g.stroke(); } g.restore();
      const mx = X(o.mirrorX ?? 0.55), mw = X(0.18), mh = Y(0.36); box(g, mx - mw / 2, Y(0.24), mw, mh, { fill: '#2b3038', line: PAL.line, r: 10 }); box(g, mx - mw * 0.35, Y(0.2), mw * 0.7, 10, { fill: '#e8ecf5', line: null, r: 5 }); light(g, mx, Y(0.2), mw * 0.8, '#e8ecf5', 0.35);
      box(g, mx - mw * 0.6, gy - E.H * 0.2, mw * 1.2, E.H * 0.06, { fill: '#c9ccd4', line: '#666', r: 6 });
      M.mirror = { x: mx, y: Y(0.24), w: mw, h: mh };
      break; }
    case 'kitchen': {
      wall(g, '#1c1e24', '#22242b'); floor(g, gy); windowBox(g, X(0.45), Y(0.2), X(0.12), Y(0.2), { sky: o.sky || 'moon', t });
      box(g, X(0.08), gy - E.H * 0.5, X(0.11), E.H * 0.5, { fill: '#3a3d45', r: 6 }); ln(g, [[X(0.08), gy - E.H * 0.3], [X(0.19), gy - E.H * 0.3]], { lw: 2, la: 0.5 });
      box(g, X(0.25), gy - E.H * 0.2, X(0.6), E.H * 0.2, { fill: '#2c2e35', r: 3 }); box(g, X(0.25), gy - E.H * 0.22, X(0.6), 14, { fill: '#4a4d55', r: 3 }); box(g, X(0.62), Y(0.17), X(0.22), E.H * 0.16, { fill: '#2c2e35', r: 3 });
      if (o.lamp) light(g, X(0.5), gy - E.H * 0.24, E.H * 0.4, PAL.lamp, 0.3);
      break; }
    case 'doorway': {
      wall(g, '#121216', '#18181d'); floor(g, gy); door(g, X(o.doorX ?? 0.62), gy, X(0.1), E.H * 0.45, { open: o.doorOpen ?? 1 }); M.door = [X(o.doorX ?? 0.62), gy];
      break; }
    default: wall(g); floor(g, gy);
  }
  if (o.dim) { g.save(); g.fillStyle = `rgba(0,0,0,${o.dim})`; g.fillRect(-60, -60, E.W + 120, E.H + 120); g.restore(); }
  return M;
}
export const SETS = ['bedroom', 'city', 'street', 'lockers', 'classroom', 'court', 'cafe', 'gym', 'stairs', 'hill', 'mirror', 'kitchen', 'void', 'black', 'doorway'];
