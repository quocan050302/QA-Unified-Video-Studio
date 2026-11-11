// map.js — ban do doodle tu du lieu world-atlas (Natural Earth 1:50m). Luon ve Hoang Sa, Truong Sa thuoc Viet Nam.
// drawMap(g, view, opts) -> proj(lon, lat) => [x, y].  view: ten co san (VIEWS) hoac [lonMin, latMin, lonMax, latMax]
import { E, clamp, ease } from '/engine/core.js';
import { INK, PAL, line, circ, label, tag, arrow, cutPolyline } from './ink.js';
import { prop } from './props.js';

let WORLD = null;
export async function loadWorld() {
  if (WORLD) return;
  const topo = await import('/node_modules/topojson-client/src/index.js');
  const w = await (await fetch('/node_modules/world-atlas/countries-50m.json')).json();
  WORLD = topo.feature(w, w.objects.countries).features;
}
export const VIEWS = {
  world: [-168, -56, 180, 78], eurasia: [-12, -8, 150, 66], asia: [58, -12, 150, 56], sea: [90, -12, 136, 28], vn: [100, 7, 118, 24.2],
  vnNorth: [102, 18.5, 109, 23.6], china: [72, 16, 138, 54], india: [64, 5, 98, 36], japan: [124, 28, 148, 46], europe: [-12, 34, 42, 64],
  mideast: [24, 10, 64, 42], mesopotamia: [36, 27, 52, 39], egypt: [22, 20, 38, 33], africa: [-20, -37, 55, 38], americas: [-130, -56, -30, 62],
  oceania: [105, -48, 180, 4], beringia: [150, 50, -150 + 360, 72],
};
// ten nuoc tieng Viet -> ten trong du lieu
export const NAMES = { 'Việt Nam': 'Vietnam', 'Trung Quốc': 'China', 'Lào': 'Laos', 'Campuchia': 'Cambodia', 'Thái Lan': 'Thailand', 'Ấn Độ': 'India', 'Nhật Bản': 'Japan', 'Hàn Quốc': 'South Korea', 'Triều Tiên': 'North Korea', 'Indonesia': 'Indonesia', 'Malaysia': 'Malaysia', 'Philippines': 'Philippines', 'Myanmar': 'Myanmar', 'Ai Cập': 'Egypt', 'Iraq': 'Iraq', 'Úc': 'Australia', 'Mỹ': 'United States of America', 'Nga': 'Russia', 'Pháp': 'France', 'Anh': 'United Kingdom', 'Hy Lạp': 'Greece', 'Ý': 'Italy', 'Đức': 'Germany', 'Mông Cổ': 'Mongolia', 'Ấn Độ Dương': null };
const HOANG_SA = [[111.2, 16.9], [111.6, 16.55], [111.75, 16.8], [112.25, 16.95], [112.35, 16.7], [112.6, 16.45], [112.1, 16.3], [111.6, 16.25], [111.9, 17.05]];
const TRUONG_SA = [[111.9, 10.4], [112.6, 9.9], [113.2, 10.7], [114.3, 10.4], [114.1, 9.55], [114.9, 10.9], [115.5, 9.9], [113.8, 8.9], [112.9, 8.6], [114.6, 8.4], [115.8, 10.6], [111.6, 8.65], [113.4, 11.2], [115.2, 8.9]];

const cache = new Map();
function viewBox(view) { const b = Array.isArray(view) ? view : VIEWS[view] || VIEWS.sea; return b; }
// phep chieu: dang tru deu, keo ngang theo cos(vi do giua); phu kin khung (cat bot phan thua)
export function projector(view, rect = [0, 0, E.W, E.H], fit = 'contain') {
  const [l0, b0, l1, b1] = viewBox(view), mid = ((b0 + b1) / 2) * Math.PI / 180, kx = Math.cos(mid);
  const w = (l1 - l0) * kx, h = b1 - b0, [rx, ry, rw, rh] = rect;
  const sc = fit === 'cover' ? Math.max(rw / w, rh / h) : Math.min(rw / w, rh / h);
  const ox = rx + (rw - w * sc) / 2, oy = ry + (rh - h * sc) / 2;
  const P = (lon, lat) => { if (l1 > 180 && lon < 0) lon += 360; return [ox + (lon - l0) * kx * sc, oy + (b1 - lat) * sc]; };
  P.scale = sc * kx; P.key = `${l0},${b0},${l1},${b1},${rect.join(',')},${fit}`;
  return P;
}
function pathOf(P, geoms) {
  const p = new Path2D();
  for (const gm of geoms) {
    const polys = gm.type === 'Polygon' ? [gm.coordinates] : gm.type === 'MultiPolygon' ? gm.coordinates : [];
    for (const poly of polys) for (const ring of poly) {
      let prev = null;
      ring.forEach((c, i) => { const q = P(c[0], c[1]); if (i === 0 || (prev && Math.abs(q[0] - prev[0]) > E.W * 1.5)) p.moveTo(q[0], q[1]); else p.lineTo(q[0], q[1]); prev = q; });
      p.closePath();
    }
  }
  return p;
}
function landPath(P) { const k = 'land|' + P.key; if (!cache.has(k)) cache.set(k, pathOf(P, WORLD.map((f) => f.geometry))); return cache.get(k); }
function countryPath(P, name) { const n = NAMES[name] || name; const k = 'c|' + n + '|' + P.key; if (!cache.has(k)) { const f = WORLD.filter((x) => x.properties.name === n); cache.set(k, f.length ? pathOf(P, f.map((x) => x.geometry)) : null); } return cache.get(k); }
function borderPaths(P) { const k = 'b|' + P.key; if (!cache.has(k)) cache.set(k, WORLD.map((f) => pathOf(P, [f.geometry]))); return cache.get(k); }

// opts: sea, land, highlight {ten: mau}, dim (lam mo cac nuoc khac), islands (true), islandLabels (true), borders (true)
// ve ban do vao anh dem (cache theo vung + mau), roi dan len khung: nhanh gap nhieu lan khi ban do dung yen hoac zoom
const bmp = new Map();
export function drawMap(g, view, o = {}) {
  if (!WORLD) throw new Error('chua nap ban do (loadWorld)');
  const P = projector(view, o.rect, o.fit);
  const key = P.key + '|' + JSON.stringify([o.sea, o.land, o.highlight, o.islands, o.islandLabels, o.borders, o.coast]) + '|' + E.PX;
  let c = bmp.get(key);
  if (!c) {
    const k = E.PX * (o.sharp ?? 2); c = document.createElement('canvas'); c.width = Math.round(E.W * k); c.height = Math.round(E.H * k);
    const x = c.getContext('2d'); x.setTransform(k, 0, 0, k, 0, 0); paintMap(x, P, view, o);
    if (bmp.size >= 4) bmp.delete(bmp.keys().next().value); bmp.set(key, c);
  }
  g.fillStyle = o.sea || PAL.sea; g.fillRect(-60, -60, E.W + 120, E.H + 120);
  g.drawImage(c, 0, 0, E.W, E.H);
  return P;
}
function paintMap(g, P, view, o) {
  g.save();
  g.fillStyle = o.sea || PAL.sea; g.fillRect(-60, -60, E.W + 120, E.H + 120);
  const land = landPath(P);
  g.fillStyle = o.land || PAL.land; g.fill(land);
  for (const [name, col] of Object.entries(o.highlight || {})) { const cp = countryPath(P, name); if (cp) { g.fillStyle = col; g.fill(cp); } }
  if (o.borders !== false) { g.strokeStyle = 'rgba(120,90,55,0.45)'; g.lineWidth = 2; g.lineJoin = 'round'; for (const bp of borderPaths(P)) g.stroke(bp); }
  g.strokeStyle = INK; g.lineWidth = o.coast ?? 4; g.lineJoin = 'round'; g.stroke(land);
  for (const [name, col] of Object.entries(o.highlight || {})) { const cp = countryPath(P, name); if (cp) { g.lineWidth = 4.5; g.strokeStyle = INK; g.stroke(cp); } }
  const [l0, b0, l1, b1] = viewBox(view);
  if (o.islands !== false && l0 < 116 && l1 > 110 && b0 < 17 && b1 > 8) {
    const r = clamp(P.scale * 0.06, 2.5, 7), col = o.highlight && (o.highlight['Việt Nam'] || o.highlight.Vietnam) || INK;
    [...HOANG_SA, ...TRUONG_SA].forEach(([lo, la]) => { const q = P(lo, la); circ(g, q[0], q[1], r, { fill: col === INK ? PAL.land : col, lw: 1.6 }); });
    if (o.islandLabels !== false && P.scale > 18) {
      const sz = clamp(P.scale * 0.8, 26, 42), a = P(112, 16.4), b = P(113.8, 9.2);
      label(g, 'QĐ. Hoàng Sa', a[0], a[1] + sz * 1.3, { size: sz, color: PAL.red }); label(g, '(Việt Nam)', a[0], a[1] + sz * 2.3, { size: sz * 0.8, color: PAL.red });
      label(g, 'QĐ. Trường Sa', b[0], b[1] + sz * 1.6, { size: sz, color: PAL.red }); label(g, '(Việt Nam)', b[0], b[1] + sz * 2.6, { size: sz * 0.8, color: PAL.red });
    }
  }
  g.restore();
}
// cac lop tren ban do (deu nhan lt = thoi gian trong shot, at = thoi diem xuat hien)
export function mapPin(g, P, lon, lat, lt, o = {}) {
  const at = o.at ?? 0; if (lt < at) return; const k = clamp((lt - at) / 0.45), q = P(lon, lat), drop = (1 - ease.outBack(k)) * -80;
  prop(g, 'pin', q[0], q[1] - (o.size || 80) * 0.5 + drop, o.size || 80, { color: o.color });
  if (o.label) tag(g, o.label, q[0] + (o.dx ?? 0), q[1] - (o.size || 80) * 1.25 + (o.dy ?? 0), { size: o.labelSize || 46, p: clamp((lt - at - 0.25) / 0.5), hl: o.hl });
}
export function mapRoute(g, P, from, to, lt, o = {}) {
  const at = o.at ?? 0; if (lt < at) return; const a = P(from[0], from[1]), b = P(to[0], to[1]);
  arrow(g, a[0], a[1], b[0], b[1], { bend: o.bend ?? 0.2, p: clamp((lt - at) / (o.dur || 1.2)), ink: o.color || PAL.red, lw: o.lw || 7, dash: o.dash === false ? null : [18, 12], head: 30 });
}
export function mapArea(g, P, lon, lat, rDeg, lt, o = {}) {
  const at = o.at ?? 0; if (lt < at) return; const q = P(lon, lat), r = rDeg * P.scale, k = clamp((lt - at) / 0.6);
  g.save(); g.beginPath(); g.arc(q[0], q[1], r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ease.out(k)); g.lineWidth = o.lw || 7; g.strokeStyle = o.color || PAL.red; g.stroke(); g.restore();
  if (o.label) tag(g, o.label, q[0] + (o.dx ?? 0), q[1] - r - 36 + (o.dy ?? 0), { size: o.labelSize || 40, p: clamp((lt - at - 0.4) / 0.5), hl: o.hl });
}
