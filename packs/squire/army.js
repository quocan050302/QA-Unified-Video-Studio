// army.js (pack squire) — dam dong / doi hinh co phoi canh, so do nhin tu tren (khoi quan xanh - do), hieu ung: mua, mua ten, bui, lao.
import { E, clamp, lerp, ease, rng, noise, alpha, mix } from './ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, blob, polyS, line, tube, blockArrow, darker, lighter } from './ink.js';
import { soldier, shield, CAST } from './chara.js';

// ---------- doi hinh phoi canh: hang sau nho dan, ve tu sau ra truoc
// o = { preset | presets[], rows, cols, x0, x1 (0..1 nhip ngang hang truoc), yFront, yBack (0..1), hFront, hBack (0..1 chieu cao),
//       spread (hang sau hep lai), seed, jitter, flip, pose, face, faces[], t, march (toc do di), advance (dich theo thoi gian), flags: [{col, color, charge}],
//       gaps: [chi so cot bo trong], skipFront: so hang truoc bo (de cho nhan vat chinh), only: 'back'|'front' }
export function formation(g, o = {}) {
  const r = rng(o.seed || 7), rows = o.rows || 5, cols = o.cols || 12, t = o.t || 0;
  const X0 = (o.x0 ?? 0.05) * E.W, X1 = (o.x1 ?? 0.95) * E.W, yF = (o.yFront ?? 0.95) * E.H, yB = (o.yBack ?? 0.62) * E.H;
  const hF = (o.hFront ?? 0.32) * E.H, hB = (o.hBack ?? 0.08) * E.H, spread = o.spread ?? 0.82;
  const presets = o.presets || [o.preset || 'norman'], faces = o.faces || [o.face || 'neutral', 'neutral', 'determined', 'bored', 'worried'];
  const list = [];
  for (let j = rows - 1; j >= (o.skipFront || 0); j--) {
    const k = rows === 1 ? 0 : j / (rows - 1); // 0 = hang truoc
    const y = lerp(yF, yB, Math.pow(k, 0.85)), h = lerp(hF, hB, Math.pow(k, 0.7)), cx = (X0 + X1) / 2, half = (X1 - X0) / 2 * lerp(1, spread, k);
    for (let i = 0; i < cols; i++) {
      if (o.gaps && o.gaps.includes(i)) continue;
      const f = cols === 1 ? 0.5 : i / (cols - 1), jit = (o.jitter ?? 0.25) * (half * 2 / cols);
      let x = cx - half + f * half * 2 + (r() - 0.5) * jit + ((j % 2) ? half / cols * 0.5 : 0);
      if (o.advance) x += o.advance * t * E.W * (o.flip ? -1 : 1);
      const p = presets[Math.floor(r() * presets.length)];
      list.push({ x, y: y + (r() - 0.5) * h * 0.04, h: h * (0.94 + r() * 0.1), p, face: faces[Math.floor(r() * faces.length)], seed: i * 7 + j * 13, row: j });
    }
  }
  for (const s of list) soldier(g, s.x, s.y, s.h, { preset: s.p, face: s.face, flip: o.flip, pose: o.pose || (o.march ? 'march' : 'stand'), walk: !!(o.march || o.advance), walkMode: o.advance ? 'side' : (o.march ? 'front' : undefined), walkPhase: o.advance ? Math.abs(o.advance * t * E.W) / (2 * 17 * s.h / 100) + s.seed * 0.07 : undefined, t: t * (o.march || 1) + s.seed * 0.13, seed: s.seed, look: o.look ?? (o.flip ? -0.6 : 0.6) * 0, weapon: o.weapon ?? CAST[s.p]?.weapon, lod: s.h < (o.lodH ?? 90) ? 'low' : 'high' });
  if (o.flags) for (const fl of o.flags) { const x = lerp(X0, X1, fl.col ?? 0.5), y = lerp(yF, yB, fl.row ?? 0.7), hh = lerp(hF, hB, fl.row ?? 0.7); standard(g, x, y - hh * 0.3, hh * 2.4, { ...fl, t }); }
}
// co hieu / dai bang La Ma
export function standard(g, x, y, s, o = {}) {
  const lw = Math.max(1.5, s * 0.02);
  tube(g, [[x, y], [x, y - s]], s * 0.025, PAL.woodDark, lw);
  if (o.kind === 'eagle') { polyS(g, [[x - s * 0.12, y - s * 0.9], [x + s * 0.12, y - s * 0.9], [x + s * 0.08, y - s * 0.84], [x - s * 0.08, y - s * 0.84]], { fill: PAL.gold, lw }); circ(g, x, y - s * 0.97, s * 0.05, { fill: PAL.gold, lw }); for (const k of [-1, 1]) polyS(g, [[x, y - s * 0.95], [x + k * s * 0.13, y - s * 1.05], [x + k * s * 0.08, y - s * 0.93]], { fill: PAL.gold, lw }); rect(g, x - s * 0.1, y - s * 0.78, s * 0.2, s * 0.14, { fill: PAL.red, lw, r: 2 }); return; }
  if (o.kind === 'vexillum') { rect(g, x - s * 0.15, y - s * 0.92, s * 0.3, s * 0.2, { fill: o.color || PAL.red, lw, r: 2 }); line(g, [[x - s * 0.18, y - s * 0.93], [x + s * 0.18, y - s * 0.93]], { lw: lw * 1.5 }); return; }
  const wv = Math.sin((o.t || 0) * 3 + x * 0.01) * s * 0.03;
  shape(g, (c) => { c.moveTo(x, y - s); c.quadraticCurveTo(x + s * 0.18, y - s + wv, x + s * 0.34, y - s * 0.98); c.lineTo(x + s * 0.34, y - s * 0.76); c.quadraticCurveTo(x + s * 0.18, y - s * 0.76 + wv, x, y - s * 0.78); c.closePath(); }, { fill: o.color || PAL.red, lw });
}

// ---------- so do nhin tu tren: nen cat + khoi quan
// blocks: [{ x, y, w, h (0..1), cols, rows, side: 'blue'|'red'|'grey'|'purple', at, path: [[giay, x, y], ...], fade: [giay0, giay1], tilt, tired }]
const SIDE = { blue: [PAL.blue, '#d9e2ef'], red: [PAL.red, '#f0d9c8'], grey: ['#7d7671', '#d5cfc6'], purple: ['#6f4c8f', '#ddd0e6'], gold: [PAL.gold, '#f2e5c0'], green: [PAL.green, '#dfe8cf'] };
export function topGround(g, o = {}) {
  const r = rng(o.seed || 5), base = o.color || '#c9ad7a';
  g.fillStyle = base; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3);
  for (let i = 0; i < 260; i++) { const x = r() * E.W, y = r() * E.H; g.fillStyle = alpha(r() < 0.5 ? darker(base, 0.12) : lighter(base, 0.08), 0.6); g.beginPath(); g.ellipse(x, y, 2 + r() * 6, 1 + r() * 3, r() * 3, 0, Math.PI * 2); g.fill(); }
  if (o.grass) for (let i = 0; i < 60; i++) { const x = r() * E.W, y = r() * E.H; line(g, [[x, y], [x + 4, y - 9], [x + 8, y]], { lw: 2, ink: alpha('#6c7a3a', 0.6) }); }
  if (o.rocks) for (let i = 0; i < 25; i++) circ(g, r() * E.W, r() * E.H, 6 + r() * 10, { fill: '#4f5a3a', lw: 0, a: 0.6 });
}
function posAt(b, lt) {
  if (!b.path) return [b.x, b.y];
  let p = [b.x, b.y]; const P = [[0, b.x, b.y], ...b.path];
  for (let i = 1; i < P.length; i++) { const [t0, x0, y0] = P[i - 1], [t1, x1, y1] = P[i]; if (lt <= t0) break; const k = ease.inOut(clamp((lt - t0) / Math.max(0.01, t1 - t0))); p = [lerp(x0, x1, k), lerp(y0, y1, k)]; }
  return p;
}
export function topBlock(g, b, lt) {
  const [x, y] = posAt(b, lt), W = (b.w || 0.06) * E.W, H = (b.h || 0.1) * E.H, cell = Math.min(E.W, E.H) * (b.cell || 0.024), cols = b.cols || Math.max(2, Math.round(W / cell)), rows = b.rows || Math.max(2, Math.round(H / cell));
  const [col, light] = SIDE[b.side || 'blue'] || SIDE.blue, a = b.fade ? 1 - clamp((lt - b.fade[0]) / Math.max(0.05, b.fade[1] - b.fade[0])) : 1;
  if (a <= 0) return;
  g.save(); g.globalAlpha *= a; g.translate(x * E.W, y * E.H); g.rotate(b.tilt || 0);
  const dx = W / cols, dy = H / rows, r = Math.min(dx, dy) * 0.5, lw = Math.max(1, r * 0.2);
  if (b.style === 'rect') { rect(g, -W / 2, -H / 2, W, H, { fill: col, lw: lw * 2, r: 4, inner: (c) => { for (let i = 1; i < cols; i++) line(c, [[-W / 2 + i * dx, -H / 2], [-W / 2 + i * dx, H / 2]], { lw: lw * 0.6, a: 0.4 }); for (let j = 1; j < rows; j++) line(c, [[-W / 2, -H / 2 + j * dy], [W / 2, -H / 2 + j * dy]], { lw: lw * 0.6, a: 0.4 }); } }); g.restore(); return; }
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    const jx = noise(i * 3.1 + j * 7.7 + (b.seed || 0)) * dx * 0.12 + (b.tired ? Math.sin(lt * 3 + i + j) * dx * 0.05 : 0), jy = noise(i * 5.3 + j * 2.1 + (b.seed || 0)) * dy * 0.12;
    const cx = -W / 2 + (i + 0.5) * dx + jx, cy = -H / 2 + (j + 0.5) * dy + jy, face = b.face ?? 1;
    // khien (phia truoc theo huong mat) + mu
    ellipse(g, cx + face * r * 0.2, cy + r * 0.25, r * 0.95, r * 0.55, { fill: alpha('#000', 0.18), lw: 0 });
    ellipse(g, cx + face * r * 0.62, cy, r * 0.42, r * 1.05, { fill: col, lw, inner: (c) => circ(c, cx + face * r * 0.7, cy, r * 0.16, { fill: light, lw: 0 }) });
    circ(g, cx - face * r * 0.12, cy, r * 0.66, { fill: b.helmet || PAL.bronze, lw, inner: (c) => circ(c, cx - face * r * 0.3, cy - r * 0.2, r * 0.22, { fill: alpha('#fff', 0.45), lw: 0 }) });
    if (b.spears) line(g, [[cx, cy + r * 0.2], [cx + face * r * 2.4, cy - r * 0.2]], { lw: lw * 0.9, ink: PAL.woodDark });
  }
  g.restore();
}
export function dustPuff(g, x, y, s, a = 0.6, t = 0) {
  g.save(); g.globalAlpha *= a; const r = rng(Math.floor(x + y));
  for (let i = 0; i < 7; i++) { const ox = (r() - 0.5) * s * 1.3 + Math.sin(t * 0.8 + i) * s * 0.06, oy = (r() - 0.5) * s * 0.6, rr = s * (0.35 + r() * 0.35);
    const gr = g.createRadialGradient(x + ox, y + oy, rr * 0.1, x + ox, y + oy, rr); gr.addColorStop(0, 'rgba(236,218,178,0.85)'); gr.addColorStop(0.6, 'rgba(226,204,160,0.5)'); gr.addColorStop(1, 'rgba(226,204,160,0)');
    g.fillStyle = gr; g.beginPath(); g.arc(x + ox, y + oy, rr, 0, Math.PI * 2); g.fill(); }
  g.restore();
}

// ---------- hieu ung
export function rain(g, t, o = {}) {
  const n = o.n || 160, r = rng(o.seed || 11), a = o.a ?? 0.55, len = o.len || E.H * 0.05, sp = o.speed || 1.4, ang = o.angle ?? 0.12;
  g.save(); g.strokeStyle = alpha(o.color || '#dfe9f2', a); g.lineWidth = o.lw || 2.2; g.lineCap = 'round'; g.beginPath();
  for (let i = 0; i < n; i++) { const x0 = r() * (E.W + 200) - 100, ph = r(), y = (((ph + t * sp) % 1) * (E.H + len * 2)) - len; const x = x0 + y * ang; g.moveTo(x, y); g.lineTo(x + len * ang, y + len); }
  g.stroke(); g.restore();
}
// mua ten roi (volley): tu tren troi xuong, nghieng
export function volley(g, t, o = {}) {
  const n = o.n || 40, r = rng(o.seed || 21), dur = o.dur || 1.2, t0 = o.at || 0, s = o.s || E.H * 0.07, dir = o.dir ?? 1;
  for (let i = 0; i < n; i++) {
    const st = t0 + r() * (o.spread ?? 0.8), k = (t - st) / dur; if (k < 0 || k > 1.25) continue;
    const xe = (o.x0 ?? 0) * E.W + r() * ((o.x1 ?? 1) - (o.x0 ?? 0)) * E.W, ye = (o.y0 ?? 0.55) * E.H + r() * ((o.y1 ?? 1) - (o.y0 ?? 0.55)) * E.H;
    const kk = Math.min(1, k), x = xe - dir * (1 - kk) * E.W * 0.25, y = ye - (1 - kk) * E.H * 0.9, ang = Math.atan2(E.H * 0.9, dir * E.W * 0.25);
    arrowFly(g, x, y, s * (0.7 + r() * 0.5), ang, Math.max(1.2, s * 0.03));
  }
}
export function arrowFly(g, x, y, L, ang, lw = 2) {
  g.save(); g.translate(x, y); g.rotate(ang);
  line(g, [[-L, 0], [0, 0]], { lw: lw * 2.6 }); line(g, [[-L, 0], [0, 0]], { lw: lw * 1.2, ink: PAL.wood });
  polyS(g, [[L * 0.14, 0], [-L * 0.02, -L * 0.06], [-L * 0.02, L * 0.06]], { fill: PAL.steel, lw: lw * 0.8 });
  polyS(g, [[-L, 0], [-L * 0.82, -L * 0.08], [-L * 0.76, 0], [-L * 0.82, L * 0.08]], { fill: PAL.white, lw: lw * 0.7 });
  g.restore();
}
// mui ten cam dat (sau loat ban)
export function stuckArrows(g, o = {}) {
  const n = o.n || 20, r = rng(o.seed || 31), s = o.s || E.H * 0.06;
  for (let i = 0; i < n; i++) { const x = ((o.x0 ?? 0) + r() * ((o.x1 ?? 1) - (o.x0 ?? 0))) * E.W, y = ((o.y0 ?? 0.6) + r() * ((o.y1 ?? 1) - (o.y0 ?? 0.6))) * E.H, k = 0.5 + (y / E.H) * 0.8; arrowFly(g, x, y, s * k, -Math.PI / 2 + 0.4 + (r() - 0.5) * 0.4, Math.max(1.2, s * k * 0.03)); }
}
export function dust(g, t, o = {}) {
  const n = o.n || 8, r = rng(o.seed || 41), a = o.a ?? 0.22;
  for (let i = 0; i < n; i++) { const x = r() * E.W + Math.sin(t * 0.3 + i) * 40 + t * 20 * (o.wind ?? 1), y = E.H * ((o.y0 ?? 0.5) + r() * ((o.y1 ?? 0.9) - (o.y0 ?? 0.5))); dustPuff(g, ((x % (E.W + 400)) + E.W + 400) % (E.W + 400) - 200, y, E.H * (o.s ?? 0.14) * (0.6 + r()), a, t); }
}
export function javelins(g, t, o = {}) { volley(g, t, { n: o.n || 25, dur: o.dur || 1.0, s: o.s || E.H * 0.1, dir: o.dir ?? 1, ...o }); }
export function smoke(g, t, o = {}) {
  const r = rng(o.seed || 51);
  for (let i = 0; i < (o.n || 3); i++) { const x = E.W * ((o.x ?? 0.5) + (r() - 0.5) * 0.3), base = E.H * (o.y ?? 0.6); for (let k = 0; k < 5; k++) { const y = base - k * E.H * 0.09 - ((t * 30) % (E.H * 0.09)), s = E.H * (0.05 + k * 0.025); ellipse(g, x + Math.sin(t + k + i) * 20, y, s, s * 0.8, { fill: alpha(o.color || '#5b5752', 0.85 - k * 0.12), lw: 3, ink: alpha(OUT, 0.5 - k * 0.08) }); } }
}
export function sparks(g, x, y, s, t, at = 0) {
  const k = clamp((t - at) / 0.35); if (k <= 0 || k >= 1) return;
  for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4 + 0.3, d = s * (0.3 + k * 0.9); line(g, [[x + Math.cos(a) * d * 0.5, y + Math.sin(a) * d * 0.5], [x + Math.cos(a) * d, y + Math.sin(a) * d]], { lw: s * 0.06, ink: '#ffd34d', a: 1 - k }); }
}
