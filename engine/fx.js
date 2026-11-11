// fx.js — khong khi, anh sang va do vat phang cho boi canh. Moi ham ve trong don vi logic.
import { E, V, clamp, lerp, ease, rng, noise, circle, ring, seg, poly, glow, linGrad, radGrad, alpha, shade, mix, hex, css, UI } from './core.js';

// ---------- bau troi & anh sang
export function sky(g, M, y0 = 0, y1 = E.H) {
  g.fillStyle = linGrad(g, 0, y0, 0, y1, M.sky.map((c, i) => [i / (M.sky.length - 1), c]));
  g.fillRect(-E.W, y0 - E.H, E.W * 3, y1 - y0 + E.H);
}
export function sun(g, x, y, r, color, a = 1) {
  glow(g, x, y, r * 9, color, 0.35 * a); glow(g, x, y, r * 3.5, color, 0.6 * a); circle(g, x, y, r, alpha(shade(color, 0.4), a));
}
export function moon(g, x, y, r, color = '#eef2ff') { glow(g, x, y, r * 6, color, 0.25); circle(g, x, y, r, color); }
export function godRays(g, x, y, t, o = {}) {
  const { count = 9, len = E.W * 1.2, spread = 1.1, color = '#ffd8a0', a = 0.12, dir = Math.PI / 2 } = o;
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < count; i++) {
    const ang = dir + (i / (count - 1) - 0.5) * spread + noise(t * 0.15 + i, 4) * 0.03, w = 0.025 + (i % 3) * 0.012;
    g.fillStyle = linGrad(g, x, y, x + Math.cos(ang) * len, y + Math.sin(ang) * len, [[0, alpha(color, a * (0.6 + 0.4 * Math.sin(t * 0.7 + i)))], [1, alpha(color, 0)]]);
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(ang - w) * len, y + Math.sin(ang - w) * len); g.lineTo(x + Math.cos(ang + w) * len, y + Math.sin(ang + w) * len); g.closePath(); g.fill();
  }
  g.restore();
}
export function lightCone(g, x, y, w, h, color = '#ffc47a', a = 0.25) {
  g.save(); g.globalCompositeOperation = 'lighter';
  g.fillStyle = linGrad(g, x, y, x, y + h, [[0, alpha(color, a)], [1, alpha(color, 0)]]);
  g.beginPath(); g.moveTo(x - 6, y); g.lineTo(x + 6, y); g.lineTo(x + w / 2, y + h); g.lineTo(x - w / 2, y + h); g.closePath(); g.fill(); g.restore();
}
export function pool(g, x, y, rx, color = '#ffc47a', a = 0.35) {
  g.save(); g.globalCompositeOperation = 'lighter'; g.translate(x, y); g.scale(1, 0.22);
  g.fillStyle = radGrad(g, 0, 0, 0, rx, [[0, alpha(color, a)], [1, alpha(color, 0)]]); g.fillRect(-rx, -rx, rx * 2, rx * 2); g.restore();
}
export function lensStreak(g, x, y, w, color = '#ffe0b0', a = 0.2) {
  g.save(); g.globalCompositeOperation = 'lighter';
  g.fillStyle = linGrad(g, x - w / 2, y, x + w / 2, y, [[0, alpha(color, 0)], [0.5, alpha(color, a)], [1, alpha(color, 0)]]); g.fillRect(x - w / 2, y - 3, w, 6);
  g.fillStyle = linGrad(g, x - w / 2, y, x + w / 2, y, [[0, alpha(color, 0)], [0.5, alpha(color, a * 0.3)], [1, alpha(color, 0)]]); g.fillRect(x - w / 2, y - 16, w, 32); g.restore();
}
export function fogBand(g, y, h, color, a = 0.25) { g.fillStyle = linGrad(g, 0, y - h, 0, y + h, [[0, alpha(color, 0)], [0.5, alpha(color, a)], [1, alpha(color, 0)]]); g.fillRect(-E.W, y - h, E.W * 3, h * 2); }

// ---------- hat trong khong khi
export function dust(g, t, o = {}) {
  const { count = 45, color = '#ffe6c4', a = 0.4, seed = 5, size = 2.6 } = o; const r = rng(seed);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < count; i++) { const x0 = r() * E.W, y0 = r() * E.H, sp = 6 + r() * 14, ph = r() * 9; const x = (x0 + t * sp + noise(t * 0.3 + ph, i) * 30 + E.W * 2) % E.W, y = (y0 - t * sp * 0.4 + noise(t * 0.25 + ph, i + 3) * 26 + E.H * 2) % E.H; circle(g, x, y, size * (0.4 + r()), alpha(color, a * (0.4 + 0.6 * Math.abs(Math.sin(t * 0.8 + ph))))); }
  g.restore();
}
export function rain(g, t, o = {}) {
  const { count = 160, color = '#b8c8e8', a = 0.35, len = 38, slant = -0.18, seed = 9, speed = 1900 } = o; const r = rng(seed);
  g.save(); g.strokeStyle = alpha(color, a); g.lineWidth = 2; g.beginPath();
  for (let i = 0; i < count; i++) { const x0 = r() * (E.W + 400) - 200, v = speed * (0.7 + r() * 0.6), y = ((r() * E.H + t * v) % (E.H + 200)) - 100, x = x0 + y * slant; g.moveTo(x, y); g.lineTo(x + slant * len, y + len); }
  g.stroke(); g.restore();
}
export function drops(g, t, o = {}) { // giot nuoc dung yen (dung thoi gian)
  const { count = 60, color = '#d8e4ff', rMax = 9, seed = 21, drift = 4 } = o; const r = rng(seed);
  for (let i = 0; i < count; i++) { const x = r() * E.W + noise(t * 0.2 + i, 2) * drift, y = r() * E.H + noise(t * 0.2 + i, 7) * drift, rad = 2 + r() * rMax; circle(g, x, y, rad, alpha(color, 0.18)); ring(g, x, y, rad, 1.2, alpha(color, 0.45)); circle(g, x - rad * 0.35, y - rad * 0.35, rad * 0.25, alpha('#ffffff', 0.7)); }
}
export function stars(g, t, o = {}) { const { count = 120, yMax = E.H * 0.55, seed = 3, a = 0.8 } = o; const r = rng(seed); for (let i = 0; i < count; i++) { const x = r() * E.W, y = r() * yMax, s = 0.8 + r() * 1.8; circle(g, x, y, s, alpha('#ffffff', a * (0.4 + 0.6 * Math.abs(Math.sin(t * (0.5 + r()) + i))))); } }
export function snow(g, t, o = {}) { const { count = 90, seed = 4 } = o; const r = rng(seed); for (let i = 0; i < count; i++) { const v = 60 + r() * 80, x = (r() * E.W + noise(t * 0.4 + i, 1) * 40), y = (r() * E.H + t * v) % E.H; circle(g, x, y, 1.5 + r() * 3, alpha('#ffffff', 0.7)); } }
export function sparkle(g, x, y, r, color = '#ffffff', a = 1) {
  if (!(r > 0.5)) return;
  g.save(); g.globalAlpha *= a; glow(g, x, y, r * 2.4, color, 0.5);
  g.beginPath(); for (let i = 0; i < 8; i++) { const ang = (i * Math.PI) / 4, rr = i % 2 ? r * 0.2 : r; g.lineTo(x + Math.cos(ang) * rr, y + Math.sin(ang) * rr); } g.closePath(); g.fillStyle = color; g.fill(); g.restore();
}
// vong tron lan ra (bat dau o t=0)
export function rings(g, x, y, t, o = {}) {
  const { count = 3, r0 = 30, r1 = 300, speed = 1, color = '#fff3e0', a = 0.5, w = 3 } = o;
  for (let i = 0; i < count; i++) { const k = ((t * speed + i / count) % 1); if (t * speed < i / count) continue; ring(g, x, y, lerp(r0, r1, ease.out(k)), w * (1 - k) + 0.5, alpha(color, a * (1 - k))); }
}
export function speedLines(g, t, o = {}) {
  const { cx = E.W / 2, cy = E.H / 2, count = 50, color = '#ffffff', a = 0.35, seed = 2, inner = 0.35 } = o; const r = rng(seed);
  g.save(); g.strokeStyle = alpha(color, a); g.lineCap = 'round';
  for (let i = 0; i < count; i++) { const ang = r() * Math.PI * 2, d0 = E.W * (inner + r() * 0.2) + ((t * 900 + r() * 400) % 300), d1 = d0 + 80 + r() * 260; g.lineWidth = 1 + r() * 3; g.beginPath(); g.moveTo(cx + Math.cos(ang) * d0, cy + Math.sin(ang) * d0); g.lineTo(cx + Math.cos(ang) * d1, cy + Math.sin(ang) * d1); g.stroke(); }
  g.restore();
}
export function lightning(g, x, y0, y1, seed = 1, color = '#e8f0ff') {
  const r = rng(seed); const pts = [[x, y0]]; let cx = x; for (let y = y0; y < y1; y += 40) { cx += (r() - 0.5) * 70; pts.push([cx, y]); }
  g.save(); g.shadowColor = color; g.shadowBlur = 30; seg(g, pts, 5, color); seg(g, pts, 2, '#ffffff'); g.restore();
}

// ---------- canh vat xa
export function skyline(g, y, o = {}) {
  const { color = '#2a1d34', lit = '#ffc47a', seed = 7, density = 1, h = 220, litA = 0.75, width = E.W * 1.8 } = o; const r = rng(seed); let x = -width * 0.25;
  while (x < width * 0.85) {
    const w = 50 + r() * 110, hh = h * (0.35 + r() * 0.75); g.fillStyle = color; g.fillRect(x, y - hh, w, hh + 4);
    if (r() < 0.25) g.fillRect(x + w * 0.4, y - hh - 30, 4, 30);
    for (let wy = y - hh + 14; wy < y - 10; wy += 22) for (let wx = x + 9; wx < x + w - 12; wx += 18) if (r() < 0.32 * density) { g.fillStyle = alpha(lit, litA * (0.4 + r() * 0.6)); g.fillRect(wx, wy, 8, 11); }
    x += w + 4 + r() * 18;
  }
}
export function hills(g, y, color, amp = 60, seed = 2) { g.fillStyle = color; g.beginPath(); g.moveTo(-E.W, E.H * 2); for (let x = -E.W; x <= E.W * 2; x += 40) g.lineTo(x, y - (noise(x * 0.003, seed) * 0.5 + 0.5) * amp); g.lineTo(E.W * 2, E.H * 2); g.closePath(); g.fill(); }
export function clouds(g, t, o = {}) { const { y = E.H * 0.2, color = '#ffffff', a = 0.18, count = 5, seed = 8 } = o; const r = rng(seed); for (let i = 0; i < count; i++) { const x = ((r() * E.W * 1.4 + t * (6 + r() * 10)) % (E.W * 1.6)) - E.W * 0.3, yy = y + r() * 120, w = 160 + r() * 260; g.fillStyle = alpha(color, a); g.beginPath(); g.ellipse(x, yy, w, 22 + r() * 18, 0, 0, Math.PI * 2); g.fill(); } }
export function tree(g, x, y, s = 1, color = '#1a1220') { seg(g, [[x, y], [x, y - 110 * s]], 12 * s, color); circle(g, x, y - 150 * s, 60 * s, color); circle(g, x - 40 * s, y - 120 * s, 44 * s, color); circle(g, x + 42 * s, y - 118 * s, 46 * s, color); }
export function pine(g, x, y, s = 1, color = '#1a1220') { poly(g, [[x, y - 210 * s], [x + 50 * s, y], [x - 50 * s, y]], color); }
export function lampPost(g, x, y, s = 1, color = '#120d16', light = '#ffc47a', on = true) {
  seg(g, [[x, y], [x, y - 300 * s], [x + 40 * s, y - 310 * s]], 9 * s, color); poly(g, [[x + 22 * s, y - 312 * s], [x + 62 * s, y - 312 * s], [x + 54 * s, y - 296 * s], [x + 30 * s, y - 296 * s]], color);
  if (on) { glow(g, x + 42 * s, y - 296 * s, 110 * s, light, 0.6); lightCone(g, x + 42 * s, y - 296 * s, 300 * s, 296 * s, light, 0.18); pool(g, x + 42 * s, y, 170 * s, light, 0.35); }
}

// ---------- kien truc & noi that
// cua so lon co song cua va troi phia sau: fn(gWin) ve canh troi ben trong
export function windowFrame(g, x, y, w, h, o = {}) {
  const { cols = 3, rows = 2, frame = '#140e18', bar = 10, inner = null, arch = false, blinds = 0 } = o;
  g.save(); g.beginPath(); if (arch) { g.moveTo(x, y + h); g.lineTo(x, y + w / 2); g.arc(x + w / 2, y + w / 2, w / 2, Math.PI, 0); g.lineTo(x + w, y + h); g.closePath(); } else g.rect(x, y, w, h); g.clip();
  if (inner) inner(g, x, y, w, h);
  if (blinds) { g.fillStyle = alpha(frame, 0.55); for (let k = y; k < y + h * blinds; k += 14) g.fillRect(x, k, w, 7); }
  g.restore();
  g.fillStyle = frame; for (let i = 0; i <= cols; i++) g.fillRect(x + (w / cols) * i - bar / 2, y + (arch ? w / 2 : 0) * (i === 0 || i === cols ? 0 : 0), bar, h);
  for (let j = 0; j <= rows; j++) g.fillRect(x, y + (h / rows) * j - bar / 2, w, bar);
  if (arch) { g.beginPath(); g.arc(x + w / 2, y + w / 2, w / 2, Math.PI, 0); g.lineWidth = bar; g.strokeStyle = frame; g.stroke(); }
}
// mat tien nha co cua so sang
export function facade(g, x, y, w, h, o = {}) {
  const { color = '#2a1d2c', lit = '#ffc47a', seed = 3, floors = 3, cols = 4, litChance = 0.6, roof = true } = o; const r = rng(seed);
  g.fillStyle = color; g.fillRect(x, y - h, w, h); if (roof) { g.fillStyle = shade(color, -0.3); g.fillRect(x - 10, y - h - 14, w + 20, 16); }
  const fh = h / floors, cw = w / cols;
  for (let f = 0; f < floors; f++) for (let c = 0; c < cols; c++) {
    const wx = x + c * cw + cw * 0.22, wy = y - h + f * fh + fh * 0.22, ww = cw * 0.56, wh = fh * 0.55, on = r() < litChance;
    g.fillStyle = on ? lit : shade(color, -0.35); g.fillRect(wx, wy, ww, wh);
    if (on) { glow(g, wx + ww / 2, wy + wh / 2, ww * 1.1, lit, 0.25); g.fillStyle = alpha(shade(color, -0.4), 0.8); g.fillRect(wx + ww / 2 - 2, wy, 4, wh); g.fillRect(wx, wy + wh / 2 - 2, ww, 4); }
  }
}
export function door(g, x, y, w = 90, h = 190, color = '#1c1418', lit = null) { g.fillStyle = color; g.fillRect(x - w / 2, y - h, w, h); if (lit) { g.fillStyle = lit; g.fillRect(x - w / 2 + 12, y - h + 14, w - 24, h * 0.35); } circle(g, x + w * 0.32, y - h * 0.48, 4, '#d9b46a'); }
export function floorLines(g, y, color, o = {}) { const { count = 9, spread = 2.2, a = 0.18 } = o; g.strokeStyle = alpha(color, a); g.lineWidth = 2; for (let i = -count; i <= count; i++) { g.beginPath(); g.moveTo(E.W / 2 + i * 60, y); g.lineTo(E.W / 2 + i * 60 * spread * 3, E.H + 200); g.stroke(); } for (let k = 1; k < 6; k++) { const yy = y + (k * k) * 9; g.beginPath(); g.moveTo(-E.W, yy); g.lineTo(E.W * 2, yy); g.stroke(); } }
export function chair(g, x, y, s = 1, color = '#24181e', facing = 1) { g.save(); g.translate(x, y); g.scale(facing * s, s); g.fillStyle = color; g.fillRect(-30, -72, 60, 9); g.fillRect(-28, -72, 6, 72); g.fillRect(22, -72, 6, 72); g.fillRect(-30, -150, 7, 85); g.restore(); }
export function table(g, x, y, w = 220, h = 110, color = '#2a1c22', top = null) { g.fillStyle = color; g.fillRect(x - w / 2, y - h, w, 12); g.fillRect(x - w / 2 + 14, y - h, 10, h); g.fillRect(x + w / 2 - 24, y - h, 10, h); if (top) { g.fillStyle = top; g.fillRect(x - w / 2, y - h - 3, w, 4); } return { top: y - h }; }
export function desk(g, x, y, w = 300, color = '#2a1c22') { g.fillStyle = color; g.fillRect(x - w / 2, y - 100, w, 14); g.fillRect(x - w / 2 + 10, y - 100, w * 0.28, 100); g.fillRect(x + w / 2 - 22, y - 100, 12, 100); return { top: y - 100 }; }
export function bed(g, x, y, w = 360, color = '#3a2a3a', sheet = '#d8d0e0') { g.fillStyle = shade(color, -0.3); g.fillRect(x - w / 2, y - 120, 18, 120); g.fillStyle = color; g.fillRect(x - w / 2, y - 60, w, 50); g.fillStyle = sheet; g.fillRect(x - w / 2 + 70, y - 72, w - 70, 16); g.fillStyle = shade(sheet, 0.2); g.beginPath(); g.roundRect(x - w / 2 + 20, y - 80, 70, 24, 10); g.fill(); }
export function screen(g, x, y, w, h, o = {}) { const { color = '#9fd0ff', a = 0.9, frame = '#0c0a10', content = null } = o; g.fillStyle = frame; g.fillRect(x - w / 2 - 8, y - h / 2 - 8, w + 16, h + 16); g.fillStyle = alpha(color, a); g.fillRect(x - w / 2, y - h / 2, w, h); glow(g, x, y, Math.max(w, h) * 0.8, color, 0.25); if (content) content(g, x - w / 2, y - h / 2, w, h); }
export function clock(g, x, y, r, t = 0, color = '#e8e0d0') { circle(g, x, y, r, alpha('#0c0a10', 0.85)); ring(g, x, y, r, r * 0.1, color); const a1 = t * 0.5 - Math.PI / 2, a2 = t * 6 - Math.PI / 2; seg(g, [[x, y], [x + Math.cos(a1) * r * 0.5, y + Math.sin(a1) * r * 0.5]], r * 0.1, color); seg(g, [[x, y], [x + Math.cos(a2) * r * 0.75, y + Math.sin(a2) * r * 0.75]], r * 0.06, color); }
export function car(g, x, y, s = 1, color = '#1a1418', lights = true) { g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = color; g.beginPath(); g.roundRect(-150, -70, 300, 50, 12); g.fill(); g.beginPath(); g.roundRect(-90, -112, 170, 50, 20); g.fill(); circle(g, -90, -20, 26, '#08060a'); circle(g, 90, -20, 26, '#08060a'); if (lights) { g.fillStyle = '#ffe6b0'; g.fillRect(138, -60, 12, 12); glow(g, 150, -54, 60, '#ffe6b0', 0.4); g.fillStyle = '#ff4a4a'; g.fillRect(-150, -60, 10, 12); } g.restore(); }
// dam dong toi (dau va vai)
export function crowd(g, y, o = {}) { const { rows = 3, color = '#120c16', seed = 6, step = 46, rise = 40, t = 0, bounce = 0 } = o; const r = rng(seed); for (let k = rows - 1; k >= 0; k--) for (let x = -60 + (k % 2) * 20; x < E.W + 60; x += step + r() * 14) { const yy = y - k * rise + Math.sin(t * 6 + x) * bounce * (r() > 0.5 ? 1 : 0); const c = shade(color, 0.04 * k); circle(g, x, yy - 40, 16 + r() * 4, c); g.fillStyle = c; g.beginPath(); g.ellipse(x, yy, 26, 26, 0, Math.PI, 0); g.fill(); g.fillRect(x - 26, yy, 52, 60); } }
