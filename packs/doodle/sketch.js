// sketch.js — net "but muc ve tay" cho THUMBNAIL kieu kenh "Vi sao": nguoi tien su dau tron trang, mat loi, mieng ha to,
// toc rau ri, khu do da bao; chu tieu de vang vien den day. Ve bang code de nhan vat thumbnail luon dong nhat giua cac video.
//   caveman(g, x, yChan, h, { face, pose, look, flip, seed, sweat, mark })
//   thumbTitle(g, 'SAO LẮM NGƯỜI THẾ?', cx, cy, { size, arc, rot })
//   savanna(g, { t, seed }) — nen thao nguyen ve code (dung khi chua co anh nen AI)
import { E, rng, clamp, lerp, text, measure } from '/engine/core.js';
import { FONT_BOLD } from './ink.js';

const INK = '#1b1612', SKIN = '#fbf8f1', MOUTH = '#4a1712', TONGUE = '#e0707a', LEO = '#e3a54e', SPOT = '#3b2a1a', TEAR = '#8fd0f2';

// ---------- net run tay: ve 2 lan lech nhau, net manh
function jit(r, a) { return (r() - 0.5) * 2 * a; }
export function rough(g, pts, o = {}) {
  const { lw = 3.2, ink = INK, passes = 2, amp = 1.6, seed = 1, close = false, fill = null } = o;
  if (fill) { g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fillStyle = fill; g.fill(); }
  for (let k = 0; k < passes; k++) {
    const r = rng(seed * 31 + k * 7); g.beginPath();
    const P = close ? [...pts, pts[0], pts[1] || pts[0]] : pts;
    P.forEach((p, i) => { const x = p[0] + jit(r, amp), y = p[1] + jit(r, amp); if (i === 0) g.moveTo(x, y); else { const q = P[i - 1]; g.quadraticCurveTo(q[0] + jit(r, amp), q[1] + jit(r, amp), (q[0] + x) / 2, (q[1] + y) / 2); } });
    const L = P[P.length - 1]; g.lineTo(L[0], L[1]);
    g.lineWidth = lw * (k ? 0.6 : 1); g.strokeStyle = ink; g.lineCap = 'round'; g.lineJoin = 'round'; g.stroke();
  }
}
const ell = (cx, cy, rx, ry, n = 28, a0 = 0, a1 = Math.PI * 2) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]; });
const sk = (g, pts, lw, fill, seed, amp = 1.6) => rough(g, pts, { lw, fill, seed, amp, close: true });

// ---------- dau
function headSketch(g, x, y, R, o, s) {
  const lw = Math.max(2.5, R * 0.045), lk = o.look || 0, face = o.face || 'scream';
  // toc rau ri: khoi toc den nhieu chom tron phia sau dau
  const r = rng(s + 3); g.fillStyle = INK; g.beginPath();
  const N = 15;
  for (let i = 0; i <= N; i++) {
    const a = Math.PI * (0.88 + 1.24 * i / N), a2 = Math.PI * (0.88 + 1.24 * (i + 0.5) / N);
    const r0 = R * 1.0, r1 = R * (1.2 + r() * 0.22);
    const p0 = [x + Math.cos(a) * r0, y - R * 0.08 + Math.sin(a) * r0], pc = [x + Math.cos(a2) * r1 * 1.08, y - R * 0.08 + Math.sin(a2) * r1], p1 = [x + Math.cos(a + 1.24 * Math.PI / N) * r0, y - R * 0.08 + Math.sin(a + 1.24 * Math.PI / N) * r0];
    if (i === 0) g.moveTo(p0[0], p0[1]); if (i < N) g.quadraticCurveTo(pc[0] + (r() - 0.5) * R * 0.25, pc[1], p1[0], p1[1]);
  }
  g.lineTo(x + R * 0.6, y); g.lineTo(x - R * 0.6, y); g.closePath(); g.fill();
  // mat (hinh dau hoi oval)
  sk(g, ell(x, y, R, R * 1.02), lw, SKIN, s);
  // toc mai rui xuong tran: cac chom den nhon
  g.fillStyle = INK;
  for (let i = 0; i < 9; i++) {
    const a = Math.PI * (1.12 + 0.76 * i / 8), bx = x + Math.cos(a) * R * 0.98, by = y + Math.sin(a) * R * 1.0;
    const tipx = lerp(bx, x, 0.32 + r() * 0.18) + (r() - 0.5) * R * 0.15, tipy = lerp(by, y, 0.3 + r() * 0.2) + R * 0.08;
    const w = R * (0.13 + r() * 0.06);
    g.beginPath(); g.moveTo(bx - Math.sin(a) * w, by + Math.cos(a) * w * 0.3 - w * 0.4); g.quadraticCurveTo(lerp(bx, tipx, 0.5) + w * 0.4, lerp(by, tipy, 0.5), tipx, tipy); g.quadraticCurveTo(lerp(bx, tipx, 0.5) - w * 0.4, lerp(by, tipy, 0.5), bx + Math.sin(a) * w, by - Math.cos(a) * w * 0.3 - w * 0.4); g.closePath(); g.fill();
  }
  g.beginPath(); g.ellipse(x, y - R * 0.7, R * 0.82, R * 0.32, 0, Math.PI, 0); g.fill();
  // mat
  const ex = R * 0.34, ey = -R * 0.04 + (face === 'cry' ? 0 : 0);
  if (face === 'cry' || face === 'squeeze') {
    [-1, 1].forEach((d) => { rough(g, ell(x + d * ex, y + ey, R * 0.2, R * 0.12, 10, Math.PI * 1.05, Math.PI * 1.95), { lw: lw * 1.2, seed: s + d }); });
    if (face === 'cry') [-1, 1].forEach((d) => { const tx = x + d * ex; g.fillStyle = TEAR; g.beginPath(); g.moveTo(tx - R * 0.06, y + R * 0.08); g.quadraticCurveTo(tx + d * R * 0.2, y + R * 0.5, tx + d * R * 0.12, y + R * 0.75); g.lineTo(tx + d * R * 0.02, y + R * 0.72); g.quadraticCurveTo(tx + d * R * 0.08, y + R * 0.4, tx - R * 0.06, y + R * 0.08); g.fill(); });
  } else {
    const er = face === 'shock' || face === 'scream' ? R * 0.27 : R * 0.22;
    [-1, 1].forEach((d) => {
      const squint = face === 'squint' && d === 1;
      if (squint) { rough(g, [[x + d * ex - er, y + ey], [x + d * ex + er * 0.9, y + ey - er * 0.2]], { lw: lw * 1.3, seed: s + 9 }); return; }
      sk(g, ell(x + d * ex, y + ey, er, er * 1.08, 20), lw, '#ffffff', s + d * 5, 1);
      const pr = er * (face === 'shock' ? 0.22 : 0.3); g.fillStyle = INK; g.beginPath(); g.arc(x + d * ex + lk * er * 0.45, y + ey + (o.lookY || 0) * er * 0.4, pr, 0, Math.PI * 2); g.fill();
    });
  }
  // long may
  const bh = face === 'squint' ? -0.05 : face === 'angry' ? 0.12 : -0.18;
  [-1, 1].forEach((d) => rough(g, [[x + d * (ex - R * 0.2), y - R * 0.38 + (face === 'angry' ? -d * 0 : 0)], [x + d * (ex + R * 0.18), y - R * 0.42 + bh * R * d * (face === 'worried' ? -1 : 1)]], { lw: lw * 1.6, seed: s + 20 + d, passes: 1 }));
  // mieng
  const my = y + R * 0.48;
  if (face === 'scream' || face === 'cry') {
    const w = R * 0.34, h = R * 0.34; const pts = ell(x, my + R * 0.06, w, h, 26);
    sk(g, pts, lw, MOUTH, s + 31, 1.2);
    g.save(); g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.clip();
    g.fillStyle = TONGUE; g.beginPath(); g.ellipse(x, my + R * 0.06 + h * 0.75, w * 0.62, h * 0.42, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#fff'; g.fillRect(x - w, my + R * 0.06 - h, w * 2, h * 0.3); g.restore(); rough(g, ell(x, my + R * 0.06, w, h, 26), { lw, seed: s + 37, close: true, amp: 1 });
  } else if (face === 'shock') {
    sk(g, ell(x, my + R * 0.04, R * 0.16, R * 0.26, 16), lw, MOUTH, s + 32, 1);
  } else if (face === 'grin') {
    const pts = ell(x, my - R * 0.08, R * 0.38, R * 0.26, 18, 0, Math.PI); sk(g, pts, lw, '#ffffff', s + 33, 1); rough(g, [[x - R * 0.36, my - R * 0.02], [x + R * 0.36, my - R * 0.02]], { lw: lw * 0.6, seed: s + 34, passes: 1 });
  } else if (face === 'squint' || face === 'angry') {
    rough(g, [[x - R * 0.25, my + R * 0.04], [x - R * 0.08, my - R * 0.05], [x + R * 0.1, my + R * 0.03], [x + R * 0.26, my - R * 0.04]], { lw: lw * 1.2, seed: s + 35 });
  } else sk(g, ell(x, my, R * 0.2, R * 0.13, 14), lw, MOUTH, s + 36, 1);
  // mo hoi
  if (o.sweat !== false) [[1, -0.5], [1.15, -0.15]].forEach(([a, b], i) => { const sx = x + a * R * (o.flip ? -1 : 1) * (i ? 0.95 : 1), sy = y + b * R; sk(g, [[sx, sy - R * 0.14], [sx + R * 0.07, sy], [sx, sy + R * 0.07], [sx - R * 0.07, sy]], lw * 0.6, TEAR, s + 40 + i, 0.6); });
}

// ---------- ca nguoi. pose: point | hands-up | hold-head | hug | spear | flee
export function caveman(g, x, y, h, o = {}) {
  const s = o.seed || 1, R = h * 0.22, hy = y - h + R * 1.05, lw = Math.max(2.5, h * 0.008);
  g.save(); if (o.flip) { g.translate(x, 0); g.scale(-1, 1); g.translate(-x, 0); }
  const shY = hy + R * 1.05, hipY = y - h * 0.3, tw = R * 0.62;
  // chan
  const leg = (dx, k) => { rough(g, [[x + dx, hipY], [x + dx * 1.3 + k * h * 0.03, lerp(hipY, y, 0.5)], [x + dx * 1.5 + k * h * 0.05, y - h * 0.02]], { lw: lw * 1.1, seed: s + 50 + k }); sk(g, ell(x + dx * 1.5 + k * h * 0.05 + k * h * 0.03, y - h * 0.01, h * 0.045, h * 0.02, 10), lw, SKIN, s + 52 + k, 0.8); };
  leg(-tw * 0.45, -1); leg(tw * 0.45, 1);
  // than + khu da bao
  sk(g, [[x - tw * 0.7, shY], [x + tw * 0.7, shY], [x + tw * 0.85, hipY + h * 0.04], [x - tw * 0.85, hipY + h * 0.04]], lw, SKIN, s + 60);
  const pelt = [[x - tw * 0.75, shY + h * 0.03], [x - tw * 0.1, shY], [x + tw * 0.9, hipY - h * 0.02], [x + tw * 0.95, hipY + h * 0.09], [x + tw * 0.5, hipY + h * 0.06], [x + tw * 0.2, hipY + h * 0.11], [x - tw * 0.2, hipY + h * 0.07], [x - tw * 0.55, hipY + h * 0.12], [x - tw * 0.95, hipY + h * 0.07]];
  sk(g, pelt, lw, LEO, s + 61);
  const r = rng(s + 62); g.save(); g.beginPath(); pelt.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.clip();
  for (let i = 0; i < 22; i++) { const px = x - tw + r() * tw * 2, py = shY + r() * (hipY + h * 0.12 - shY); g.fillStyle = SPOT; g.beginPath(); g.ellipse(px, py, h * 0.012 + r() * h * 0.008, h * 0.009, r() * 3, 0, Math.PI * 2); g.fill(); }
  g.restore();
  // tay
  const P = { point: [[-0.4, 0.35], [1.25, -0.05]], 'hands-up': [[-0.85, -0.55], [0.85, -0.55]], 'hold-head': [[-0.55, -0.85], [0.55, -0.85]], hug: [[0.5, 0.25], [0.35, 0.15]], spear: [[-0.45, 0.3], [0.7, -0.2]], flee: [[-0.9, -0.2], [0.9, 0.3]], down: [[-0.45, 0.45], [0.45, 0.45]] }[o.pose || 'point'];
  [[-1, P[0]], [1, P[1]]].forEach(([d, [hx, hyy]]) => {
    const sx = x + d * tw * 0.7, sy = shY + h * 0.02, ex = x + hx * h * 0.42, ey = shY + hyy * h * 0.42;
    const mx = (sx + ex) / 2 + d * h * 0.03, my = (sy + ey) / 2 + h * 0.04;
    rough(g, [[sx, sy], [mx, my], [ex, ey]], { lw: lw * 2.6, seed: s + 70 + d, passes: 1 }); rough(g, [[sx, sy], [mx, my], [ex, ey]], { lw: lw * 1.2, ink: SKIN, seed: s + 72 + d, passes: 1, amp: 0.3 });
    sk(g, ell(ex, ey, h * 0.032, h * 0.03, 12), lw, SKIN, s + 74 + d, 0.8);
    if (o.pose === 'point' && d === 1) rough(g, [[ex, ey], [ex + h * 0.06, ey - h * 0.005]], { lw: lw * 1.4, seed: s + 76 });
  });
  if (o.pose === 'spear') { rough(g, [[x + 0.7 * h * 0.42, shY + h * 0.35], [x + 0.75 * h * 0.42, shY - h * 0.55]], { lw: lw * 1.6, ink: '#6b4a2a', seed: s + 80 }); sk(g, [[x + 0.75 * h * 0.42 - h * 0.025, shY - h * 0.5], [x + 0.75 * h * 0.42, shY - h * 0.62], [x + 0.75 * h * 0.42 + h * 0.025, shY - h * 0.5]], lw, '#9a948a', s + 81); }
  headSketch(g, x, hy, R, o, s);
  g.restore();
  // dau ! ? quanh dau
  if (o.mark) { const t = String(o.mark); text(g, t, x + (o.flip ? -1 : 1) * R * 1.25, hy - R * 1.05, { size: R * 0.7, font: FONT_BOLD, weight: 800, color: INK }); }
}

// ---------- chu tieu de thumbnail: vang, vien den day, bong do 3D, cong nhe
export function thumbTitle(g, str, cx, cy, o = {}) {
  const size = o.size || 190, arc = o.arc ?? 0.07, rot = o.rot ?? -0.03, color = o.color || '#ffe23a';
  const chars = [...String(str)], font = `800 ${size}px ${FONT_BOLD}`;
  g.save(); g.font = font; const ws = chars.map((c) => g.measureText(c).width * 0.97); const tot = ws.reduce((a, b) => a + b, 0);
  let maxW = o.maxW || E.W * 0.92; const k = tot > maxW ? maxW / tot : 1;
  g.translate(cx, cy); g.rotate(rot); g.scale(k, k);
  const pass = (fn) => { let xx = -tot / 2; chars.forEach((c, i) => { const mid = xx + ws[i] / 2, u = mid / (tot / 2); const yy = arc * size * 2.2 * u * u; g.save(); g.translate(mid, yy); g.rotate(u * arc * 1.2); fn(c); g.restore(); xx += ws[i]; }); };
  g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = font; g.lineJoin = 'round';
  pass((c) => { g.fillStyle = '#000'; g.lineWidth = size * 0.3; g.strokeStyle = '#000'; g.strokeText(c, size * 0.05, size * 0.08); g.fillText(c, size * 0.05, size * 0.08); });
  pass((c) => { g.lineWidth = size * 0.22; g.strokeStyle = '#120d08'; g.strokeText(c, 0, 0); });
  pass((c) => { g.fillStyle = color; g.fillText(c, 0, 0); });
  pass((c) => { g.save(); g.beginPath(); g.rect(-size, -size, size * 2, size * 0.42); g.clip(); g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillText(c, 0, 0); g.restore(); });
  g.restore();
}

// ---------- nen thao nguyen ve code (tam thoi khi chua co anh nen AI)
export function savanna(g, o = {}) {
  const W = E.W, H = E.H, gy = H * 0.62, s = o.seed || 4, r = rng(s);
  const sky = g.createLinearGradient(0, 0, 0, gy); sky.addColorStop(0, o.sky || '#bfe0ea'); sky.addColorStop(1, '#f6e7c4'); g.fillStyle = sky; g.fillRect(0, 0, W, gy + 2);
  g.fillStyle = '#d9c39a'; g.beginPath(); g.moveTo(0, gy); for (let i = 0; i <= 10; i++) g.lineTo(i * W / 10, gy - 20 - r() * 40); g.lineTo(W, gy); g.fill();
  const gr = g.createLinearGradient(0, gy, 0, H); gr.addColorStop(0, '#e2b663'); gr.addColorStop(1, '#c48a3e'); g.fillStyle = gr; g.fillRect(0, gy, W, H - gy);
  for (let i = 0; i < 260; i++) { const x = r() * W, y = gy + r() * (H - gy), l = 10 + r() * 26 * (y / H); rough(g, [[x, y], [x + (r() - 0.5) * 8, y - l]], { lw: 2, ink: 'rgba(110,70,25,0.55)', seed: i, passes: 1, amp: 0.5 }); }
  const tx = W * (o.treeX ?? 0.62), ty = gy - 4; rough(g, [[tx, ty], [tx + 6, ty - 70], [tx - 20, ty - 110]], { lw: 7, ink: '#4a3523', seed: 3 }); rough(g, [[tx + 6, ty - 70], [tx + 40, ty - 105]], { lw: 5, ink: '#4a3523', seed: 4 });
  g.fillStyle = '#6f7d45'; g.beginPath(); g.ellipse(tx + 8, ty - 118, 95, 22, 0, 0, Math.PI * 2); g.fill();
}
