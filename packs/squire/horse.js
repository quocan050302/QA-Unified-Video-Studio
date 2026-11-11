// horse.js (pack squire) — ngua nhin ngang (huong phai; flip de quay trai), dang: stand | walk | gallop | rear.
// horse(g, x, y, h, o): x,y = giua 4 chan cham dat, h = chieu cao toi dinh tai. o = { color, mane, cloth: { color, charge, chargeColor }, saddle, rider, gait, t, flip, face }
import { E, clamp, lerp, alpha } from './ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, blob, polyS, line, tube, smoothPath, darker, lighter } from './ink.js';
import { soldier, charge, ik2 } from './chara.js';

export const HORSES = { brown: ['#a86634', '#3d2a1e'], bay: ['#8a4f2a', '#2b211c'], grey: ['#cfc7bd', '#8c847b'], white: ['#efe9e0', '#b7ada2'], black: ['#3b3330', '#1e1918'], chestnut: ['#b5582c', '#7a3519'], dun: ['#cfa76a', '#5a4030'] };

// chan ngua: IK 2 doan, mong cham dat that khi dang tru (khong truot). f = pha cua chan (0..1)
const GAITS = { walk: { S: 22, beta: 0.62, lift: 7, off: [0, 0.25, 0.5, 0.75], rate: 0.85 }, gallop: { S: 40, beta: 0.38, lift: 14, off: [0, 0.1, 0.5, 0.6], rate: 2.2 } };
export const HORSE_D = (gait) => { const G = GAITS[gait]; return G ? G.S / G.beta : 0; };
function hoofPos(f, G) {
  if (f < G.beta) { const k = f / G.beta; return [lerp(G.S / 2, -G.S / 2, k), 0, 0]; }
  const k = (f - G.beta) / (1 - G.beta), e = (1 - Math.cos(Math.PI * k)) / 2; return [lerp(-G.S / 2, G.S / 2, e), -Math.sin(Math.PI * k) * G.lift, Math.sin(Math.PI * k)];
}
// doan chan thon dan (hinh thang bo tron) co vien
function taper(g, p0, p1, w0, w1, col, lw) {
  const dx = p1[0] - p0[0], dy = p1[1] - p0[1], d = Math.hypot(dx, dy) || 1, nx = -dy / d, ny = dx / d;
  polyS(g, [[p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2], [p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2], [p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2], [p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2]], { fill: col, lw });
}
function leg(g, hipX, hipY, u, f, lw, col, hoof, front, gait, gb = 0, o = {}) {
  const G = GAITS[gait], L1 = (front ? 20.5 : 20) * u, L2 = (front ? 19 : 19.5) * u;
  let fx = hipX + (front ? 1 : -1) * 1 * u, fy = -5 * u - gb, sw = 0;
  if (G) { const [dx, dy, s2] = hoofPos(f, G); fx = hipX + dx * u; fy = -5 * u + dy * u - gb; sw = s2; }
  if (gait === 'rear' && front) { fx = hipX + 12 * u; fy = hipY + 22 * u; }
  let l1 = L1, l2 = L2; if (!G && gait !== 'rear') { const d = Math.hypot(fx - hipX, fy - hipY), k = d / (L1 + L2) * 1.02; l1 *= k; l2 *= k; }
  const P = ik2(hipX, hipY, fx, fy, l1, l2, front ? 1 : -1);
  const ang = Math.atan2(P[2][1] - P[1][1], P[2][0] - P[1][0]);
  const fold = sw * (front ? 0.6 : 0.3) * (gait === 'gallop' ? 1.3 : 1), a2 = ang + (front ? fold : -fold * 0.4);
  const H = [P[1][0] + Math.cos(a2) * l2, P[1][1] + Math.sin(a2) * l2];
  const lower = o.socks ? '#efe7da' : col;
  taper(g, [hipX, hipY - 8 * u], P[1], (front ? 13 : 16) * u, 6.6 * u, col, lw);
  taper(g, P[1], H, 6.4 * u, 5 * u, lower, lw);
  circ(g, P[1][0], P[1][1], 3.3 * u, { fill: col, lw: 0 });
  // mong: khoi toi co vien sang o tren
  g.save(); g.translate(H[0], H[1]); g.rotate(a2 - Math.PI / 2);
  shape(g, (c) => { c.moveTo(-3.2 * u, -0.6 * u); c.lineTo(3.2 * u, -0.6 * u); c.lineTo(4.4 * u, 5.2 * u); c.lineTo(-3.6 * u, 5.2 * u); c.closePath(); }, { fill: hoof, lw: lw * 0.9, inner: (c) => { c.fillStyle = '#d9d2c6'; c.fillRect(-5 * u, -0.6 * u, 10 * u, 1.3 * u); } });
  g.restore();
}
export function horse(g, x, y, h, o = {}) {
  const u = h / 100, lw = o.lw ?? Math.max(1.4, h * 0.011), t = o.t || 0;
  const [col, dark] = HORSES[o.color] || (Array.isArray(o.color) ? o.color : HORSES.brown);
  const gait = o.gait || 'stand', G = GAITS[gait];
  const cyc = G ? (o.travel !== undefined ? o.travel / (HORSE_D(gait) * u) : t * G.rate) + (o.seed || 0) * 0.13 : t;
  const ph = cyc * Math.PI * 2, F = (k) => (((cyc + (G ? G.off[k] : 0)) % 1) + 1) % 1;
  const bob = gait === 'gallop' ? -Math.abs(Math.sin(ph)) * 3.5 * u : gait === 'walk' ? -Math.abs(Math.sin(ph * 2)) * 0.9 * u : Math.sin(t * 1.5) * 0.4 * u;
  const rearA = gait === 'rear' ? -0.32 : 0;
  g.save(); g.translate(x, y); if (o.flip) g.scale(-1, 1);
  g.translate(0, bob); if (rearA) { g.translate(-30 * u, -40 * u); g.rotate(rearA); g.translate(30 * u, 40 * u); }
  const hoof = '#3a3332', D = darker(col, 0.14), muz = o.muzzle || lighter(col, 0.28);
  g.translate(0, 5 * u); const gb0 = bob + 5 * u;
  const legY = -45 * u;
  // chan phia xa
  leg(g, 25 * u, legY, u, F(3), lw, D, hoof, true, gait, gb0, o);
  leg(g, -33 * u, legY, u, F(2), lw, D, hoof, false, gait, gb0, o);
  // duoi
  const tw = Math.sin(t * 2.3) * 2.5 * u;
  shape(g, (c) => { c.moveTo(-42 * u, -66 * u); c.bezierCurveTo(-52 * u, -64 * u, -54 * u + tw, -44 * u, -50 * u + tw, -24 * u); c.bezierCurveTo(-46 * u + tw, -30 * u, -45 * u, -50 * u, -40 * u, -58 * u); c.closePath(); }, { fill: o.mane || dark, lw });
  // chan phia gan (duoi than)
  leg(g, 30 * u, legY, u, F(1), lw, col, hoof, true, gait, gb0, o);
  leg(g, -28 * u, legY, u, F(0), lw, col, hoof, false, gait, gb0, o);
  // co
  shape(g, (c) => { c.moveTo(12 * u, -71 * u); c.bezierCurveTo(24 * u, -82 * u, 32 * u, -94 * u, 38 * u, -102 * u); c.lineTo(58 * u, -90 * u); c.bezierCurveTo(54 * u, -76 * u, 48 * u, -62 * u, 42 * u, -48 * u); c.lineTo(20 * u, -50 * u); c.closePath(); }, { fill: col, lw });
  // than: hop dai bo tron, nguc nho ra truoc, mong tron
  shape(g, (c) => { c.moveTo(-34 * u, -73 * u); c.bezierCurveTo(-14 * u, -68 * u, 6 * u, -69 * u, 20 * u, -73 * u); c.bezierCurveTo(36 * u, -75 * u, 46 * u, -62 * u, 43 * u, -50 * u); c.bezierCurveTo(41 * u, -40 * u, 34 * u, -37 * u, 24 * u, -38 * u); c.bezierCurveTo(8 * u, -35 * u, -14 * u, -35 * u, -30 * u, -39 * u); c.bezierCurveTo(-44 * u, -40 * u, -48 * u, -52 * u, -47 * u, -60 * u); c.bezierCurveTo(-46 * u, -70 * u, -41 * u, -74 * u, -34 * u, -73 * u); c.closePath(); }, { fill: col, lw, inner: (c) => {
    c.fillStyle = alpha('#000', 0.1); c.beginPath(); c.ellipse(0, -40 * u, 50 * u, 9 * u, 0, 0, Math.PI * 2); c.fill();
    // nep co (vai, mong) — net manh
    line(c, [[22 * u, -66 * u], [25 * u, -58 * u], [24 * u, -50 * u]], { lw: lw * 0.55, ink: alpha(OUT, 0.55) });
    line(c, [[-30 * u, -66 * u], [-27 * u, -58 * u], [-30 * u, -50 * u]], { lw: lw * 0.55, ink: alpha(OUT, 0.55) });
    if (o.dapple) for (let i = 0; i < 8; i++) circ(c, -30 * u + (i % 4) * 13 * u, -62 * u + Math.floor(i / 4) * 10 * u, 3.4 * u, { fill: null, lw: lw * 0.5, ink: alpha(OUT, 0.3) });
  } });
  // bom
  shape(g, (c) => { c.moveTo(13 * u, -71 * u); c.bezierCurveTo(26 * u, -82 * u, 33 * u, -94 * u, 40 * u, -102 * u); c.lineTo(43 * u, -94 * u); c.bezierCurveTo(36 * u, -86 * u, 28 * u, -76 * u, 22 * u, -68 * u); c.closePath(); }, { fill: o.mane || dark, lw: lw * 0.9 });
  // dau: dai, mom thon, vung mom sang
  const hx = 42 * u, hy = -100 * u;
  g.save(); g.translate(hx, hy + 8 * u); g.scale(1.16, 1.16); g.translate(-hx, -(hy + 8 * u));
  const headP = (c) => { c.moveTo(hx - 4 * u, hy - 2 * u); c.bezierCurveTo(hx + 4 * u, hy - 8 * u, hx + 12 * u, hy - 4 * u, hx + 22 * u, hy + 12 * u); c.bezierCurveTo(hx + 27 * u, hy + 20 * u, hx + 25 * u, hy + 28 * u, hx + 18 * u, hy + 29 * u); c.bezierCurveTo(hx + 10 * u, hy + 29 * u, hx + 6 * u, hy + 22 * u, hx + 2 * u, hy + 17 * u); c.bezierCurveTo(hx - 4 * u, hy + 12 * u, hx - 8 * u, hy + 5 * u, hx - 4 * u, hy - 2 * u); c.closePath(); };
  shape(g, headP, { fill: col, lw, inner: (c) => {
    c.fillStyle = muz; c.beginPath(); c.ellipse(hx + 20 * u, hy + 23 * u, 9 * u, 7.5 * u, -0.5, 0, Math.PI * 2); c.fill();
    if (o.blaze !== false) { c.fillStyle = o.blazeColor || '#efe7da'; c.beginPath(); c.moveTo(hx + 4 * u, hy - 1 * u); c.quadraticCurveTo(hx + 15 * u, hy + 6 * u, hx + 21 * u, hy + 17 * u); c.lineTo(hx + 18 * u, hy + 19 * u); c.quadraticCurveTo(hx + 11 * u, hy + 8 * u, hx + 2 * u, hy + 2 * u); c.closePath(); c.fill(); }
    c.fillStyle = alpha('#000', 0.12); c.beginPath(); c.ellipse(hx + 2 * u, hy + 16 * u, 6 * u, 4 * u, 0.4, 0, Math.PI * 2); c.fill();
  } });
  // tai
  for (const [ex, k] of [[-1 * u, 0.85], [-5 * u, 1]]) polyS(g, [[hx + ex - 1 * u, hy - 1 * u], [hx + ex - 2.5 * u, hy - 12 * u * k], [hx + ex + 3 * u, hy - 3 * u]], { fill: k < 1 ? D : col, lw: lw * 0.9 });
  // mat: mi khep nua (kieu chan doi cua kenh mau) / gian / so
  const fc = o.face || 'calm', ex = hx + 5 * u, ey = hy + 5 * u;
  if (fc === 'scared') { circ(g, ex, ey, 3.2 * u, { fill: '#fff', lw: lw * 0.7 }); circ(g, ex + 0.4 * u, ey, 1.2 * u, { fill: OUT, lw: 0 }); }
  else { ellipse(g, ex, ey, 2.6 * u, 2.2 * u, { fill: '#fff', lw: lw * 0.6 }); circ(g, ex + 0.5 * u, ey + 0.4 * u, 1.3 * u, { fill: OUT, lw: 0 }); g.save(); g.beginPath(); g.ellipse(ex, ey, 3 * u, 2.6 * u, 0, 0, Math.PI * 2); g.clip(); g.fillStyle = col; g.fillRect(ex - 4 * u, ey - 4 * u, 8 * u, fc === 'angry' ? 3.6 * u : 3.2 * u); g.restore(); line(g, [[ex - 3 * u, ey - (fc === 'angry' ? 0.2 : 0.7) * u], [ex + 3 * u, ey - (fc === 'angry' ? 1.6 : 0.7) * u]], { lw: lw * 0.9 }); }
  ellipse(g, hx + 23 * u, hy + 22 * u, 1.3 * u, 2 * u, { fill: OUT, lw: 0, rot: -0.4 });
  line(g, [[hx + 13 * u, hy + 27.5 * u], [hx + 19 * u, hy + 28.6 * u]], { lw: lw * 0.6 });
  if (o.neigh) shape(g, (c) => { c.moveTo(hx + 12 * u, hy + 27 * u); c.lineTo(hx + 22 * u, hy + 28.5 * u); c.lineTo(hx + 14 * u, hy + 32 * u); c.closePath(); }, { fill: PAL.mouth, lw: lw * 0.6 });
  // day cuong
  if (o.bridle !== false) { const bc = o.bridleColor || '#4a2f1d'; line(g, [[hx - 1 * u, hy - 1 * u], [hx + 8 * u, hy + 20 * u]], { lw: lw * 1.3, ink: bc }); line(g, [[hx + 8 * u, hy + 20 * u], [hx + 23 * u, hy + 17 * u]], { lw: lw * 1.3, ink: bc }); line(g, [[hx - 3 * u, hy + 10 * u], [hx + 9 * u, hy + 6 * u]], { lw: lw * 1.1, ink: bc }); circ(g, hx + 8 * u, hy + 20 * u, 1.5 * u, { fill: PAL.gold, lw: lw * 0.5 }); if (o.rider) line(g, [[hx + 8 * u, hy + 20 * u], [6 * u, -74 * u]], { lw: lw * 0.6, ink: bc }); }
  g.restore();
  const bodyY = -56 * u;
  // ao phu ngua (caparison) / yen
  if (o.cloth) {
    const cl = o.cloth;
    shape(g, (c) => { c.moveTo(-36 * u, bodyY - 12 * u); c.bezierCurveTo(-14 * u, bodyY - 18 * u, 14 * u, bodyY - 18 * u, 32 * u, bodyY - 14 * u); c.lineTo(38 * u, bodyY + 22 * u); for (let i = 0; i <= 8; i++) { const xx = 38 * u - i * 9.5 * u; c.lineTo(xx - 4.7 * u, bodyY + 26 * u + (i % 2) * 2 * u); c.lineTo(xx - 9.5 * u, bodyY + 22 * u); } c.closePath(); }, { fill: cl.color || PAL.yellow, lw, inner: (c) => { if (cl.charge) { charge(c, cl.charge, -14 * u, bodyY + 4 * u, 22 * u, cl.chargeColor || PAL.red, null, lw * 0.6); charge(c, cl.charge, 18 * u, bodyY + 4 * u, 18 * u, cl.chargeColor || PAL.red, null, lw * 0.6); } c.fillStyle = alpha('#000', 0.1); c.fillRect(-60 * u, bodyY + 10 * u, 120 * u, 20 * u); } });
  }
  if (o.saddle !== false) {
    const sc = o.saddle || PAL.red;
    shape(g, (c) => c.roundRect(-14 * u, bodyY - 20 * u, 30 * u, 22 * u, 3 * u), { fill: sc, lw, inner: (c) => { line(c, [[-14 * u, bodyY - 2 * u], [16 * u, bodyY - 2 * u]], { lw: lw * 2, ink: PAL.gold }); } });
    rect(g, -6 * u, bodyY - 25 * u, 16 * u, 6 * u, { fill: PAL.leather, lw: lw * 0.9, r: 2 * u });
    if (!o.rider) { line(g, [[2 * u, bodyY - 4 * u], [2 * u, bodyY + 10 * u]], { lw: lw * 0.7 }); rect(g, -2 * u, bodyY + 10 * u, 8 * u, 3 * u, { fill: PAL.steelDark, lw: lw * 0.6, r: 1 }); }
  }
  // nguoi cuoi
  if (o.rider) {
    const rh = o.riderH ? o.riderH * u : 66 * u;
    soldier(g, 2 * u, bodyY + 7 * u, rh, { pose: 'ride', ...o.rider, t, flip: false, lod: 'high' });
  }
  g.restore();
}
