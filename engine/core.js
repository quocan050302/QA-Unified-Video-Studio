// core.js — H2 2D Studio: he toa do, thoi gian, mau, phong cach, may quay, dang ky shot.
// Moi kich thuoc tinh theo "don vi logic": 16:9 -> 1920x1080, 9:16 -> 1080x1920.

export const E = { W: 1920, H: 1080, PX: 1, fps: 24, vertical: false, cfg: {}, words: [], lines: [], shots: [], style: null, frame: 0 };
export const V = (land, vert) => (E.vertical ? vert : land);

// ---------- toan hoc
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const prog = (t, a, b) => clamp((t - a) / (b - a));      // 0..1 giua a va b
export const ease = {
  linear: (k) => k,
  in: (k) => k * k,
  out: (k) => 1 - (1 - k) * (1 - k),
  inOut: (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2),
  sine: (k) => 0.5 - 0.5 * Math.cos(Math.PI * k),
  outBack: (k) => { const c = 1.7; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); },
  outElastic: (k) => (k <= 0 ? 0 : k >= 1 ? 1 : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * (2 * Math.PI) / 3) + 1),
};
// keyframes: kf(t, [[t0,v0],[t1,v1],...], easeFn)  (v co the la so hoac mang so)
export function kf(t, keys, fn = ease.inOut) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i][0]) {
      const [t0, a] = keys[i - 1], [t1, b] = keys[i], k = fn((t - t0) / (t1 - t0));
      return Array.isArray(a) ? a.map((x, j) => lerp(x, b[j], k)) : lerp(a, b, k);
    }
  }
  return keys[keys.length - 1][1];
}
// so ngau nhien co dinh theo seed (khong dung Math.random de moi lan render giong nhau)
export function rng(seed = 1) {
  let s = (Math.floor(seed * 9301 + 49297) % 233280 + 233280) % 233280 || 1;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}
export function noise(x, seed = 0) {
  const h = (n) => { const s = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453; return s - Math.floor(s); };
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(h(i), h(i + 1), u) * 2 - 1;
}
export const shake = (t, amp = 10, freq = 18, seed = 3) => [noise(t * freq, seed) * amp, noise(t * freq, seed + 7) * amp];

// ---------- mau
export function hex(c) {
  if (Array.isArray(c)) return c;
  if (c.startsWith('rgb')) return c.replace(/[^\d.,]/g, '').split(',').slice(0, 3).map(Number);
  c = c.replace('#', '');
  if (c.length === 3) c = c.split('').map((x) => x + x).join('');
  return [parseInt(c.slice(0, 2), 16), parseInt(c.slice(2, 4), 16), parseInt(c.slice(4, 6), 16)];
}
export const css = (r, a = 1) => (a >= 1 ? `rgb(${r[0] | 0},${r[1] | 0},${r[2] | 0})` : `rgba(${r[0] | 0},${r[1] | 0},${r[2] | 0},${a})`);
export const mix = (a, b, k) => { const x = hex(a), y = hex(b); return css([lerp(x[0], y[0], k), lerp(x[1], y[1], k), lerp(x[2], y[2], k)]); };
export const alpha = (c, a) => css(hex(c), a);
export const shade = (c, k) => (k >= 0 ? mix(c, '#ffffff', k) : mix(c, '#000000', -k));

// ---------- phong cach + bang mau theo khong khi (mood)
// Dung mood(name) va S() thay vi ma mau cung, de doi style la doi ca video.
const MOODS = {
  dusk:   { sky: ['#2a1d3d', '#5c3a63', '#c0626a', '#f2a36b'], sun: '#ffd49a', key: '#ffb876', rim: '#ffd3a0', wall: '#3a2a40', floor: '#2b1f2e', dark: '#140e18', practical: '#ffc47a', fog: '#6b4a6e', far: '#4a3352' },
  golden: { sky: ['#3b2a4a', '#8a4f5e', '#e48a5a', '#ffcf86'], sun: '#ffe6a8', key: '#ffc27a', rim: '#ffe0b0', wall: '#4a3036', floor: '#33242a', dark: '#1a1014', practical: '#ffd08a', fog: '#8a5a5a', far: '#5c3c44' },
  night:  { sky: ['#0b1024', '#16204a', '#2a3466', '#3e4a7e'], sun: '#dfe8ff', key: '#a8c4ff', rim: '#bcd2ff', wall: '#1c2238', floor: '#141a2c', dark: '#070a14', practical: '#ffb35c', fog: '#2c3658', far: '#232c4c' },
  interiorWarm: { sky: ['#3a2638', '#7a4a52', '#d07a5c', '#ffc584'], sun: '#ffe2a8', key: '#ffbe7a', rim: '#ffd8a6', wall: '#3e2c34', floor: '#2c2026', dark: '#160f13', practical: '#ffc985', fog: '#5e4250', far: '#4c3440' },
  interiorCool: { sky: ['#141a2e', '#24304e', '#3c4c72', '#6a7aa6'], sun: '#e4ecff', key: '#c4d4ff', rim: '#d0dcff', wall: '#222a40', floor: '#181e30', dark: '#0a0d16', practical: '#9fd0ff', fog: '#34405e', far: '#2a3350' },
  storm:  { sky: ['#0e1118', '#1c2230', '#2c3444', '#46505e'], sun: '#cfd8e8', key: '#b8c6dc', rim: '#cad6ea', wall: '#1e232c', floor: '#15191f', dark: '#08090c', practical: '#ffcf7a', fog: '#3a424e', far: '#262c36' },
  void:   { sky: ['#0a1630', '#0e1d3e', '#12244a', '#163058'], sun: '#9fd2ff', key: '#9fd2ff', rim: '#bfe2ff', wall: '#0e1d3e', floor: '#0a1630', dark: '#050b18', practical: '#ffd36b', fog: '#1c3060', far: '#12244a' },
};
export const STYLES = {
  dusk:      { name: 'Hoang hon (mac dinh)', tint: null, grade: { lift: [14, 6, 22], gain: [255, 236, 214], contrast: 1.05, sat: 1.0, vignette: 0.55, grain: 0.07 } },
  midnight:  { name: 'Dem xanh', tint: { dusk: 'night', golden: 'night', interiorWarm: 'interiorCool' }, grade: { lift: [4, 10, 26], gain: [222, 236, 255], contrast: 1.08, sat: 0.92, vignette: 0.6, grain: 0.07 } },
  golden:    { name: 'Nang vang', tint: { dusk: 'golden', interiorCool: 'interiorWarm' }, grade: { lift: [18, 10, 14], gain: [255, 232, 200], contrast: 1.04, sat: 1.08, vignette: 0.45, grain: 0.06 } },
  storybook: { name: 'Truyen tranh diu', tint: null, grade: { lift: [40, 34, 46], gain: [255, 246, 236], contrast: 0.9, sat: 0.85, vignette: 0.3, grain: 0.04 } },
  flat:      { name: 'Phang, khong chinh mau (minh hoa doodle)', tint: null, grade: null },
};
export const UI = { gold: '#ffc83d', accent: '#ff6b5a', cream: '#fff1dc', blue: '#8fd0ff', bp: '#0e1d3e', ink: '#0c0a10', inkFar: '#2a2232' };
export function mood(name = 'dusk') {
  const st = STYLES[E.cfg.style] || STYLES.dusk;
  const n = (st.tint && st.tint[name]) || name;
  return { name: n, ...(MOODS[n] || MOODS.dusk) };
}
export const S = () => ({ ...UI, style: STYLES[E.cfg.style] || STYLES.dusk });

// ---------- ve co ban
export function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect ? g.roundRect(x, y, w, h, r) : g.rect(x, y, w, h); }
export function circle(g, x, y, r, fill) { if (!(r > 0)) return; g.beginPath(); g.arc(x, y, Math.max(0.01, r), 0, Math.PI * 2); g.fillStyle = fill; g.fill(); }
export function ring(g, x, y, r, w, stroke) { g.beginPath(); g.arc(x, y, Math.max(0.01, r), 0, Math.PI * 2); g.lineWidth = w; g.strokeStyle = stroke; g.stroke(); }
export function seg(g, pts, w, stroke, cap = 'round') {
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.lineWidth = w; g.lineCap = cap; g.lineJoin = 'round'; g.strokeStyle = stroke; g.stroke();
}
export function poly(g, pts, fill) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); g.closePath(); g.fillStyle = fill; g.fill(); }
export function linGrad(g, x0, y0, x1, y1, stops) { const gr = g.createLinearGradient(x0, y0, x1, y1); stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; }
export function radGrad(g, x, y, r0, r1, stops) { const gr = g.createRadialGradient(x, y, r0, x, y, r1); stops.forEach(([o, c]) => gr.addColorStop(o, c)); return gr; }
export function glow(g, x, y, r, color, a = 0.6) {
  if (!(r > 0.5) || !(a > 0)) return;
  g.save(); g.globalCompositeOperation = 'lighter';
  g.fillStyle = radGrad(g, x, y, 0, r, [[0, alpha(color, a)], [0.35, alpha(color, a * 0.35)], [1, alpha(color, 0)]]);
  g.fillRect(x - r, y - r, r * 2, r * 2); g.restore();
}
export function fill(g, color) { g.fillStyle = color; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3); }
export function veil(g, color = '#000', a = 0.4) { g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); g.fillStyle = alpha(color, a); g.fillRect(0, 0, E.W, E.H); g.restore(); }

// ---------- chu
export const FONTS = { title: '"Baloo 2"', body: '"Be Vietnam Pro"', serif: '"Lora"', mono: 'ui-monospace, monospace' };
export function text(g, str, x, y, o = {}) {
  const { size = 48, font = FONTS.title, weight = 800, color = UI.cream, align = 'center', base = 'middle', spacing = 0, glowColor = null, a = 1, stroke = 0, strokeColor = '#000', italic = false } = o;
  g.save(); g.globalAlpha *= a;
  g.font = `${italic ? 'italic ' : ''}${weight} ${size}px ${font}`; g.textAlign = align; g.textBaseline = base;
  if ('letterSpacing' in g) g.letterSpacing = `${spacing}px`;
  if (glowColor) { g.shadowColor = glowColor; g.shadowBlur = size * 0.6; }
  if (stroke) { g.lineWidth = stroke; g.strokeStyle = strokeColor; g.lineJoin = 'round'; g.strokeText(str, x, y); }
  g.fillStyle = color; g.fillText(str, x, y);
  g.restore();
}
export function measure(g, str, size = 48, font = FONTS.title, weight = 800, spacing = 0) {
  g.save(); g.font = `${weight} ${size}px ${font}`; if ('letterSpacing' in g) g.letterSpacing = `${spacing}px`; const w = g.measureText(str).width; g.restore(); return w;
}

// ---------- may quay va lop chieu sau
// cam = { z: zoom, x, y: dich chuyen (don vi logic), r: xoay (rad) }.  depth 1 = lop nhan vat, <1 xa hon (truot it), >1 gan hon.
export function layer(g, cam, depth, fn) {
  cam = cam || {}; const z = cam.z ?? 1, cx = E.W / 2, cy = E.H / 2;
  const zz = 1 + (z - 1) * depth;
  g.save();
  g.translate(cx, cy); g.rotate((cam.r || 0) * depth); g.scale(zz, zz); g.translate(-cx - (cam.x || 0) * depth, -cy - (cam.y || 0) * depth);
  fn(g); g.restore();
}
// ve vao canvas phu roi lam mo (foreground/background mo)
let _tmp = null;
export function blurLayer(g, px, fn, cam = null, depth = 1) {
  const W = g.canvas.width, H = g.canvas.height;
  if (!_tmp || _tmp.width !== W || _tmp.height !== H) { _tmp = document.createElement('canvas'); _tmp.width = W; _tmp.height = H; }
  const t = _tmp.getContext('2d'); t.setTransform(1, 0, 0, 1, 0, 0); t.clearRect(0, 0, W, H); t.setTransform(E.PX, 0, 0, E.PX, 0, 0);
  if (cam) layer(t, cam, depth, fn); else fn(t);
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.filter = `blur(${px * E.PX}px)`; g.drawImage(_tmp, 0, 0); g.restore();
}

// ---------- dong bo voi loi doc
// wordTime('fifty', sau giay x) -> thoi diem (giay toan video) chu do bat dau
export function wordTime(word, after = 0) {
  const nz = (x) => String(x).normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}']/gu, '');
  const w = nz(word);
  const hit = E.words.find((x) => x.t >= after - 0.01 && nz(x.w) === w);
  return hit ? hit.t : null;
}
// phraseTime('ba trăm triệu', sau giay x) -> thoi diem cum chu bat dau (tieng Viet: moi am tiet la 1 chu)
export function phraseTime(phrase, after = 0) {
  const nz = (x) => String(x).normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}']/gu, '');
  const toks = String(phrase).split(/\s+/).map(nz).filter(Boolean); if (!toks.length) return null;
  const W = E.words;
  // tieng Nhat/Trung (khong co dau cach): khop chuoi ky tu noi lien, noi suy thoi diem trong chu
  if (/[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]/.test(phrase)) {
    const q = toks.join(''); let s = '', idx = [];
    for (let i = 0; i < W.length; i++) { if (W[i].t < after - 0.01) continue; const w = nz(W[i].w); for (let k = 0; k < w.length; k++) idx.push([i, k, w.length]); s += w; }
    const p = s.indexOf(q); if (p < 0) return null;
    const [i, k, n] = idx[p]; const e = W[i].e ?? (W[i + 1] ? W[i + 1].t : W[i].t + 0.3);
    return W[i].t + (e - W[i].t) * (k / Math.max(1, n));
  }
  for (let i = 0; i < W.length; i++) {
    if (W[i].t < after - 0.01) continue;
    let ok = true; for (let k = 0; k < toks.length; k++) if (!W[i + k] || nz(W[i + k].w) !== toks[k]) { ok = false; break; }
    if (ok) return W[i].t;
  }
  return null;
}
// do mo mieng 0..1 trong khoang [from,to] (giay toan video), nhay theo tung chu
export function talkAmount(gt, from, to) {
  if (gt < from || gt > to) return 0;
  const inWords = E.words.filter((x) => x.t < to && x.e > from);
  const cur = inWords.find((x) => gt >= x.t && gt <= x.e + 0.04);
  if (!cur && inWords.length) return 0;
  const k = Math.abs(Math.sin(gt * 17)) * 0.6 + Math.abs(Math.sin(gt * 7.3)) * 0.4;
  return clamp(0.25 + 0.75 * k);
}

// ---------- dang ky shot
const SHOTS = new Map();
export function registerShot(id, def) { SHOTS.set(id, def); }
export const getShot = (id) => SHOTS.get(id);
export const shotIds = () => [...SHOTS.keys()];
// mau canh (template) dung lai nhieu lan: shots.json ghi "tpl": "<ten>", "args": {...} thay vi viet code tung shot
const TPLS = new Map();
export function registerTemplate(name, def) { TPLS.set(name, def); }
export const getTemplate = (name) => TPLS.get(name);
export const templateNames = () => [...TPLS.keys()];

// anh ngoai (anh AI dat trong <du an>/anh/, ten file = ma anh, vd A012.png). Player nap truoc khi ve shot can dung.
export const IMG = new Map();             // ma anh -> HTMLImageElement da giai ma
export const ASSETS = new Map();          // ma anh -> duong dan file (tu /__assets)
export const img = (id) => IMG.get(String(id)) || null;
export const hasAsset = (id) => ASSETS.has(String(id));

// nhan vat co dang noi khong (theo timeline/lines.json): who = ten o giong (HERO, YOUNG_F...) hoac ten nhan vat
export function speaking(gt, who) {
  const l = E.lines.find((x) => (x.slot === who || x.char === who) && gt >= x.start - 0.02 && gt <= x.end);
  return l ? talkAmount(gt, l.start, l.end) : 0;
}
