// templates.js — mau canh dung bang du lieu trong shots.json: { "tpl": "<ten>", "args": {...} }.
// Toa do x, y trong args: 0..1 = ti le khung (0.5 = giua), >1.5 = don vi logic (px tren khung 1920x1080). Co (h, s, size): 0..1 = ti le chieu cao khung.
// Moi mau deu nhan them cac lop phu chung: labels, arrows, marks, props, people, bubble (xem overlays()).
import { E, clamp, lerp, ease, kf, registerTemplate, img, talkAmount, text } from '/engine/core.js';
import { INK, PAL, T, pop, grow, fadeIn, bob, rect, circ, ellipse, poly, line, arrow, label, tag, note, stamp, cross, ban, check, qmark, excl, bubble, cover, wrap, FONT_HAND, FONT_BOLD, FONT_BODY, shadow } from './ink.js';
import { guy, head, CAST } from './host.js';
import { prop } from './props.js';
import { bg } from './world.js';
import { drawMap, mapPin, mapRoute, mapArea, VIEWS } from './map.js';

export const fx = (v, d = 0.5) => (v === undefined ? d * E.W : v <= 1.5 ? v * E.W : v);
export const fy = (v, d = 0.5) => (v === undefined ? d * E.H : v <= 1.5 ? v * E.H : v);
export const fs = (v, d = 0.3) => (v === undefined ? d * E.H : v <= 1.5 ? v * E.H : v);
const at = (info, v, d = 0) => T(info, v, d);

// ---------- may quay: move = in | out | left | right | up | down | still ; zoom = [x, y, z, tu_giay, den_giay] dap vao 1 diem
export function camera(g, lt, info, fn) {
  const a = info.args, d = info.dur, k = ease.sine(clamp(lt / Math.max(d, 0.1))), mv = a.move || 'in', amt = a.moveAmt ?? 0.06;
  let z = 1, dx = 0, dy = 0;
  if (mv === 'in') z = 1 + amt * k; else if (mv === 'out') z = 1 + amt * (1 - k);
  else if (mv === 'left') { z = 1 + amt; dx = lerp(amt, -amt, k) * E.W * 0.45; } else if (mv === 'right') { z = 1 + amt; dx = lerp(-amt, amt, k) * E.W * 0.45; }
  else if (mv === 'up') { z = 1 + amt; dy = lerp(amt, -amt, k) * E.H * 0.45; } else if (mv === 'down') { z = 1 + amt; dy = lerp(-amt, amt, k) * E.H * 0.45; }
  let cx = E.W / 2, cy = E.H / 2;
  if (a.zoom) { const [zx, zy, zz = 1.6, t0 = 0, t1 = 0.8] = a.zoom; const q = ease.inOut(clamp((lt - at(info, t0)) / Math.max(0.05, (typeof t1 === 'number' ? t1 : 0.8)))); z *= lerp(1, zz, q); cx = lerp(cx, fx(zx), q); cy = lerp(cy, fy(zy), q); }
  // khong de may quay lo ra ngoai khung hinh
  { const hw = E.W / (2 * z), hh = E.H / (2 * z); cx = clamp(cx + dx, hw, E.W - hw) - dx; cy = clamp(cy + dy, hh, E.H - hh) - dy; }
  if (a.shake) { const s = a.shake * Math.max(0, 1 - lt / 0.4); dx += Math.sin(lt * 70) * 14 * s; dy += Math.cos(lt * 60) * 10 * s; }
  g.save(); g.translate(E.W / 2, E.H / 2); g.scale(z, z); g.translate(-cx - dx, -cy - dy); fn(); g.restore();
}

// ---------- nguoi: people = [{ preset, x, y, h, pose, face, look, flip, talk, prop, at, faceAt: [[giay|cumchu, mat], ...], poseAt, walk, from: [x0], to: [x1] }]
function facesAt(info, lt, list, def) { let v = def; for (const [tt, f] of list || []) if (lt >= at(info, tt, 1e9)) v = f; return v; }
export function drawPeople(g, lt, info, people, gy = 0.86) {
  people = people || [];
  for (const p of people) {
    const a0 = at(info, p.at, 0); if (lt < a0) continue;
    const pk = pop(lt, a0, 0.4), h = fs(p.h, 0.62), y = fy(p.y, gy);
    let x = fx(p.x, 0.5);
    if (p.to !== undefined) x = lerp(fx(p.from ?? p.x), fx(p.to), ease.inOut(clamp((lt - a0) / (p.dur || info.dur))));
    const talk = p.talk ? talkAmount(info.globalT, info.start, info.start + info.dur) : 0;
    g.save(); if (pk < 1) { g.translate(x, y); g.scale(pk, pk); g.translate(-x, -y); }
    const o = { ...p, t: lt + (p.seed || 0), pose: facesAt(info, lt, p.poseAt, p.pose || 'stand'), face: facesAt(info, lt, p.faceAt, p.face || 'neutral'), talk, walk: p.walk || p.to !== undefined };
    if (p.prop) o.drawProp = (gg, hx, hy, s) => prop(gg, p.prop, hx, hy - s * 0.3, s * 1.6, { color: p.propColor, t: lt });
    guy(g, x, y + bob(lt, 0, 1), h, o);
    g.restore();
  }
}
// ---------- do vat: props = [{ name, x, y, s, at, anim: pop|drop|float|spin|shake|grow, color, rot, flip, ...tuy chon rieng }]
export function drawProps(g, lt, info, props = []) {
  for (const p of props) {
    const a0 = at(info, p.at, 0); if (lt < a0) continue;
    const x = fx(p.x), s = fs(p.s, 0.22); let y = fy(p.y), sc = 1, rot = p.rot || 0;
    const anim = p.anim || 'pop', k = clamp((lt - a0) / 0.45);
    if (anim === 'pop') sc = ease.outBack(k); else if (anim === 'drop') y -= (1 - ease.outBack(k)) * E.H * 0.5; else if (anim === 'grow') sc = ease.inOut(clamp((lt - a0) / 0.9));
    if (anim === 'float') y += bob(lt, 10, 0.8, x); if (anim === 'spin') rot += lt * 1.2; if (anim === 'shake') rot += Math.sin(lt * 30) * 0.08 * Math.max(0, 1 - (lt - a0) / 0.8);
    if (p.shadow) shadow(g, x, y + s * 0.5, s * 0.8);
    prop(g, p.name, x, y, s, { ...p, scale: sc, rot, t: lt });
  }
}
// ---------- lop phu chung: chu, mui ten, dau hieu, bong bong
export function overlays(g, lt, info) {
  const a = info.args;
  drawProps(g, lt, info, a.props);
  drawPeople(g, lt, info, a.people, a.groundY ? a.groundY + 0.08 : 0.86);
  if (a.bubble) {
    const b = a.bubble, a0 = at(info, b.at, 0.2), p = clamp((lt - a0) / 0.4);
    const r = bubble(g, fx(b.x, 0.7), fy(b.y, 0.3), fx(b.w, 0.26), fy(b.h, 0.3), { tail: b.tail ? [fx(b.tail[0]), fy(b.tail[1])] : null, thought: b.thought !== false, p });
    if (r && p > 0.5) {
      if (b.prop) prop(g, b.prop, r.x, r.y, r.h * 1.05, { t: lt, color: b.color, wings: b.wings, stripes: b.stripes });
      if (b.img && img(b.img)) cover(g, img(b.img), r.x - r.w / 2, r.y - r.h / 2, r.w, r.h);
      if (b.text) { const ls = wrap(g, b.text, r.w * 1.1, b.size || 40); ls.forEach((l, i) => label(g, l, r.x, r.y + (i - (ls.length - 1) / 2) * (b.size || 40) * 1.1, { size: b.size || 40 })); }
      if (b.mark === 'cross') cross(g, r.x, r.y, r.h * 0.45, { p: clamp((lt - a0 - 0.5) / 0.4) });
      if (b.mark === 'q') qmark(g, r.x, r.y, r.h * 0.9);
    }
  }
  for (const l of a.arrows || []) { const a0 = at(info, l.at, 0); arrow(g, fx(l.from[0]), fy(l.from[1]), fx(l.to[0]), fy(l.to[1]), { p: clamp((lt - a0) / (l.dur || 0.5)), bend: l.bend ?? 0.15, ink: l.color || INK, lw: l.lw || 6, dash: l.dash ? [16, 12] : null, both: l.both }); }
  for (const m of a.marks || []) {
    const a0 = at(info, m.at, 0), p = clamp((lt - a0) / 0.45), x = fx(m.x), y = fy(m.y), r = fs(m.r, 0.08);
    if (lt < a0) continue;
    if (m.kind === 'cross') cross(g, x, y, r, { p, circle: m.circle }); else if (m.kind === 'ban') ban(g, x, y, r, { p }); else if (m.kind === 'check') check(g, x, y, r, { p });
    else if (m.kind === 'q') { g.save(); g.translate(x, y); g.scale(ease.outBack(p), ease.outBack(p)); qmark(g, 0, 0, r * 2); g.restore(); }
    else if (m.kind === '!') { g.save(); g.translate(x, y); g.scale(ease.outBack(p), ease.outBack(p)); excl(g, 0, 0, r * 2); g.restore(); }
    else if (m.kind === 'circle') { g.save(); g.beginPath(); g.ellipse(x, y, r * (m.rx || 1.3), r, 0, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ease.out(p)); g.lineWidth = 7; g.strokeStyle = m.color || PAL.red; g.stroke(); g.restore(); }
    else if (m.kind === 'underline') line(g, [[x - r, y], [x + r, y + 4]], { lw: 7, ink: m.color || PAL.red, p });
  }
  for (const l of a.labels || []) {
    const a0 = at(info, l.at, 0); if (lt < a0) continue; const p = clamp((lt - a0) / (l.kind === 'note' ? 0.35 : 0.5)), x = fx(l.x), y = fy(l.y), size = l.size || (l.kind === 'tag' ? 46 : l.kind === 'stamp' ? 64 : 56);
    if (l.kind === 'tag') tag(g, l.text, x, y, { size, p, hl: l.hl || PAL.yellow, align: l.align });
    else if (l.kind === 'note') note(g, l.text, x, y, { w: fx(l.w, 0.3), size, p, rot: l.rot ?? -0.025, sub: l.sub });
    else if (l.kind === 'stamp') stamp(g, l.text, x, y, { size, p, rot: l.rot ?? -0.08, color: l.color || PAL.red });
    else if (l.kind === 'big') label(g, l.text, x, y, { size: l.size || 110, font: FONT_BOLD, weight: 800, color: l.color || INK, p: ease.out(p) > 0 ? 1 : 0, rot: l.rot || 0, stroke: l.stroke || 0, strokeColor: l.strokeColor || '#fff', a: clamp(p * 2) });
    else label(g, l.text, x, y, { size, p, caps: l.caps !== false, color: l.color || INK, rot: l.rot || 0, align: l.align || 'center' });
  }
}

const tpl = (name, draw) => registerTemplate(name, { draw: (g, lt, info) => draw(g, lt, info, info.args || {}) });

// ---------- comp: bo cuc tu do (nen + nguoi + do vat + chu). host: nhu comp, mac dinh co nguoi dan chuyen o giua
tpl('comp', (g, lt, info, a) => camera(g, lt, info, () => { bg(g, a.bg || 'paper', { t: lt, groundY: a.groundY, color: a.bgColor, ground: a.ground, fire: a.fire, seed: a.seed }); overlays(g, lt, info); }));
tpl('host', (g, lt, info, a) => {
  const ppl = a.people || [{ preset: 'host', x: a.x ?? 0.5, pose: a.pose || 'stand', face: a.face || 'neutral', faceAt: a.faceAt, poseAt: a.poseAt, look: a.look, h: a.h, prop: a.prop, talk: a.talk }];
  camera(g, lt, info, () => { bg(g, a.bg || 'white', { t: lt, groundY: a.groundY, color: a.bgColor, ground: a.ground, seed: a.seed }); overlays(g, lt, { ...info, args: { ...a, people: ppl } }); });
});
// ---------- bighead: mat to can canh (phan ung). face, faceAt, talk, x, side: { prop | text }
tpl('bighead', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'white', { color: a.bgColor });
  const R = fs(a.r, 0.36), x = fx(a.x, 0.42), y = fy(a.y, 0.55) + bob(lt, 4, 0.8);
  const o = { ...(CAST[a.preset || 'host'] || CAST.host), ...a, face: facesAt(info, lt, a.faceAt, a.face || 'surprised'), t: lt, talk: a.talk ? talkAmount(info.globalT, info.start, info.start + info.dur) : 0 };
  // vai ao
  rect(g, x - R * 1.15, y + R * 0.82, R * 2.3, R * 1.4, { fill: o.shirt || PAL.shirt, r: R * 0.5, lw: 7 });
  head(g, x, y, R, o);
  if (a.hand) { const hx = x + R * 1.35, hy = y + R * 0.25 + bob(lt, 6, 1.4); line(g, [[x + R * 0.95, y + R * 1.15], [hx, hy]], { lw: 12 }); circ(g, hx, hy, R * 0.2, { fill: '#fff', lw: 6 }); if (a.hand !== true) label(g, a.hand, hx, hy, { size: R * 0.28, font: FONT_BOLD, weight: 800 }); }
  overlays(g, lt, info);
}));
// ---------- ai: anh AI (dat trong <du an>/anh/<img>.png). focus [x,y] tam zoom. Thieu anh -> the bao "THIEU ANH"
tpl('ai', (g, lt, info, a) => {
  const im = img(a.img);
  camera(g, lt, info, () => {
    if (im) cover(g, im, 0, 0, E.W, E.H, { z: a.crop ?? 1.08, fx: a.focus ? a.focus[0] : 0.5, fy: a.focus ? a.focus[1] : 0.5 });
    else { bg(g, 'paper'); rect(g, E.W * 0.2, E.H * 0.25, E.W * 0.6, E.H * 0.5, { fill: '#fff', lw: 5, dash: [18, 12] }); label(g, `THIẾU ẢNH ${a.img || '?'}`, E.W / 2, E.H * 0.4, { size: 70, color: PAL.red, font: FONT_BOLD, weight: 800 }); const ls = wrap(g, info.line || '', E.W * 0.52, 34, FONT_BODY, 600); ls.slice(0, 4).forEach((l, i) => text(g, l, E.W / 2, E.H * 0.52 + i * 44, { size: 34, font: FONT_BODY, weight: 600, color: PAL.grey })); }
    overlays(g, lt, info);
  });
});
// ---------- map: view (ten | [lon0,lat0,lon1,lat1]), highlight {ten nuoc: mau}, pins [{lon,lat,label,at}], routes [{from:[lon,lat],to,at,dur}], areas [{lon,lat,r,label,at}], host: true
tpl('map', (g, lt, info, a) => camera(g, lt, info, () => {
  const hl = {}; for (const [k, v] of Object.entries(a.highlight || {})) { const a0 = typeof v === 'object' ? at(info, v.at, 0) : 0; if (lt >= a0) hl[k] = typeof v === 'object' ? v.color : v; }
  const P = drawMap(g, a.view || 'sea', { highlight: hl, islands: a.islands, islandLabels: a.islandLabels, borders: a.borders });
  for (const r of a.areas || []) mapArea(g, P, r.lon, r.lat, r.r || 3, lt, { ...r, at: at(info, r.at, 0) });
  for (const r of a.routes || []) mapRoute(g, P, r.from, r.to, lt, { ...r, at: at(info, r.at, 0) });
  for (const p of a.pins || []) mapPin(g, P, p.lon, p.lat, lt, { ...p, at: at(info, p.at, 0) });
  if (a.host) drawPeople(g, lt, info, [{ preset: 'host', x: a.host.x ?? 0.12, h: a.host.h ?? 0.5, pose: a.host.pose || 'point', face: a.host.face || 'neutral', ...(typeof a.host === 'object' ? a.host : {}) }], 0.98);
  overlays(g, lt, { ...info, args: { ...a, people: null } });
}));
// ---------- compare: hai ben. left/right = { prop | img | text, label, color, s }, sign: 'vs' | '≠' | '=' | '>' | '<' | 'arrow'
function item(g, lt, info, it, x, y, s) {
  if (!it) return; const a0 = at(info, it.at, 0); if (lt < a0) return; const k = ease.outBack(clamp((lt - a0) / 0.45));
  g.save(); g.translate(x, y); g.scale(k, k);
  if (it.img && img(it.img)) { rect(g, -s * 0.6, -s * 0.6, s * 1.2, s * 1.2, { fill: '#fff', lw: 6, r: 18 }); g.save(); g.beginPath(); g.roundRect(-s * 0.6 + 3, -s * 0.6 + 3, s * 1.2 - 6, s * 1.2 - 6, 15); g.clip(); cover(g, img(it.img), -s * 0.6, -s * 0.6, s * 1.2, s * 1.2); g.restore(); }
  else if (it.prop) prop(g, it.prop, 0, 0, s, { ...it, t: lt });
  else if (it.person) guy(g, 0, s * 0.5, s, { ...(typeof it.person === 'object' ? it.person : { preset: it.person }), t: lt });
  else if (it.text) label(g, it.text, 0, 0, { size: it.size || s * 0.35, font: FONT_BOLD, weight: 800, color: it.color || INK });
  g.restore();
  if (it.label) label(g, it.label, x, y + s * 0.62 + 44, { size: it.labelSize || 56, p: clamp((lt - a0 - 0.2) / 0.5) });
}
tpl('compare', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'white', { color: a.bgColor }); const s = fs(a.s, 0.36), y = fy(a.y, 0.45);
  item(g, lt, info, a.left, E.W * 0.28, y, s); item(g, lt, info, a.right, E.W * 0.72, y, s);
  const sg = a.sign || 'vs', k = pop(lt, at(info, a.signAt, 0.5));
  if (k > 0) { g.save(); g.translate(E.W / 2, y); g.scale(k, k); if (sg === 'arrow') arrow(g, -90, 0, 90, 0, { bend: 0, lw: 9 }); else label(g, sg === 'vs' ? 'VS' : sg, 0, 0, { size: 120, font: FONT_BOLD, weight: 800, color: sg === '≠' ? PAL.red : INK }); g.restore(); }
  overlays(g, lt, info);
}));
// ---------- scale: can 2 dia. left/right nhu compare, tilt -1..1 (+ = ben phai nang hon), tiltAt
tpl('scale', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'white', { color: a.bgColor }); const cx = E.W / 2, by = fy(a.y, 0.86), top = by - E.H * 0.6;
  const tilt = (a.tilt ?? 0.5) * 0.22 * ease.outBack(clamp((lt - at(info, a.tiltAt, 0.6)) / 0.9));
  poly(g, [[cx - 120, by], [cx, by - 40], [cx + 120, by]], { fill: PAL.wood, lw: 6 }); rect(g, cx - 12, top, 24, by - top - 30, { fill: PAL.woodDark, lw: 6, r: 6 });
  const arm = E.W * 0.26, ax = Math.cos(tilt) * arm, ay = Math.sin(tilt) * arm;
  line(g, [[cx - ax, top + 10 - ay], [cx + ax, top + 10 + ay]], { lw: 18 }); line(g, [[cx - ax, top + 10 - ay], [cx + ax, top + 10 + ay]], { lw: 10, ink: PAL.woodDark });
  circ(g, cx, top + 6, 20, { fill: PAL.gold, lw: 6 });
  [[-1, a.left], [1, a.right]].forEach(([d, it]) => {
    const px = cx + d * ax, py = top + 10 + d * ay, pan = py + E.H * 0.3;
    line(g, [[px, py], [px - 130, pan]], { lw: 4 }); line(g, [[px, py], [px + 130, pan]], { lw: 4 });
    g.save(); g.beginPath(); g.ellipse(px, pan, 150, 34, 0, 0, Math.PI); g.fillStyle = '#c9a25a'; g.fill(); g.lineWidth = 6; g.strokeStyle = INK; g.stroke(); g.restore(); line(g, [[px - 150, pan], [px + 150, pan]], { lw: 6 });
    item(g, lt, info, it ? { ...it, label: null } : null, px, pan - fs(it?.s, 0.2) * 0.5, fs(it?.s, 0.2));
    if (it?.label) label(g, it.label, px, pan + 84, { size: 56 });
  });
  overlays(g, lt, info);
}));
// ---------- measure: vat dung canh nhau tren mat dat + thuoc do. items [{prop|person|img, s, label, x}], dim {x, from, to (0..1 y), text, at}
tpl('measure', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'sky', { groundY: a.groundY ?? 0.82, t: lt }); const gy = fy(a.groundY ?? 0.82);
  (a.items || []).forEach((it, i) => { const s = fs(it.s, 0.4), x = fx(it.x, 0.3 + i * 0.4); if (it.person) { const a0 = at(info, it.at, 0); if (lt >= a0) guy(g, x, gy, s, { ...(typeof it.person === 'object' ? it.person : { preset: it.person }), t: lt }); if (it.label) label(g, it.label, x, gy + 62, { size: 52 }); } else item(g, lt, info, { ...it, label: null }, x, gy - s * 0.5, s); if (it.label && !it.person) label(g, it.label, x, gy + 62, { size: 52 }); });
  for (const d of [].concat(a.dim || [])) {
    const a0 = at(info, d.at, 0.3), p = clamp((lt - a0) / 0.7); if (p <= 0) continue;
    if (d.horizontal) { const y = fy(d.y, 0.25), x0 = fx(d.from), x1 = fx(d.to), mx = (x0 + x1) / 2; arrow(g, mx, y, lerp(mx, x1, p), y, { bend: 0, lw: 5, head: 18 }); arrow(g, mx, y, lerp(mx, x0, p), y, { bend: 0, lw: 5, head: 18 }); [x0, x1].forEach((xx) => line(g, [[xx, y - 26], [xx, y + 26]], { lw: 4, a: p })); label(g, d.text, mx, y - 40, { size: d.size || 50, p: clamp(p * 1.5 - 0.5), caps: false }); }
    else { const x = fx(d.x, 0.5), y0 = fy(d.from), y1 = fy(d.to), my = (y0 + y1) / 2; arrow(g, x, my, x, lerp(my, y0, p), { bend: 0, lw: 5, head: 18 }); arrow(g, x, my, x, lerp(my, y1, p), { bend: 0, lw: 5, head: 18 }); label(g, d.text, x + 30, my, { size: d.size || 50, p: clamp(p * 1.5 - 0.5), align: 'left', caps: false }); }
  }
  overlays(g, lt, info);
}));
// ---------- list: to giay danh sach (don dat hang). title, items [{icon, text, state: check|cross|null, at, stateAt}]
tpl('list', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'table'); const n = (a.items || []).length, w = fx(a.w, 0.42), lh = Math.min(120, E.H * 0.7 / Math.max(1, n)), h = n * lh + (a.title ? 150 : 70), x0 = fx(a.x, 0.5) - w / 2, y0 = (E.H - h) / 2;
  g.save(); g.translate(E.W / 2, E.H / 2); g.rotate(a.rot ?? -0.03); g.translate(-E.W / 2, -E.H / 2);
  g.fillStyle = 'rgba(40,25,10,0.25)'; g.fillRect(x0 + 14, y0 + 16, w, h);
  rect(g, x0, y0, w, h, { fill: '#fffaf0', lw: 5, r: 8 });
  if (a.title) label(g, a.title, x0 + w / 2, y0 + 70, { size: 58 });
  (a.items || []).forEach((it, i) => {
    const a0 = at(info, it.at, 0); if (lt < a0) return; const y = y0 + (a.title ? 140 : 50) + lh * (i + 0.5), p = clamp((lt - a0) / 0.4);
    if (it.icon) prop(g, it.icon, x0 + 80, y, lh * 0.7, { scale: ease.outBack(p), t: lt });
    label(g, it.text, x0 + 150, y, { size: Math.min(56, lh * 0.5), align: 'left', caps: false, p });
    rect(g, x0 + w - 110, y - lh * 0.28, lh * 0.56, lh * 0.56, { fill: '#fff', lw: 4, r: 6 });
    const s0 = at(info, it.stateAt, 1e9), sp = clamp((lt - s0) / 0.4);
    if (it.state === 'check' && sp > 0) check(g, x0 + w - 110 + lh * 0.28, y, lh * 0.32, { p: sp });
    if (it.state === 'cross' && sp > 0) cross(g, x0 + w - 110 + lh * 0.28, y, lh * 0.3, { p: sp, circle: false });
    if (it.strike && sp > 0) line(g, [[x0 + 140, y + 4], [lerp(x0 + 140, x0 + w - 140, sp), y - 4]], { lw: 6, ink: PAL.red });
  });
  g.restore(); overlays(g, lt, info);
}));
// ---------- note: giay note lon (cau trich, con so, dinh nghia). text, sub, size
tpl('note', (g, lt, info, a) => camera(g, lt, info, () => { bg(g, a.bg || 'table', { color: a.bgColor }); note(g, a.text || '', fx(a.x, 0.5), fy(a.y, 0.5), { w: fx(a.w, 0.55), size: a.size || 72, p: clamp((lt - at(info, a.at, 0.05)) / 0.4), sub: a.sub, rot: a.rot ?? -0.02 }); overlays(g, lt, info); }));
// ---------- counter: so dem len. from, to, decimals, prefix, suffix, label, at, dur
tpl('counter', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'paper', { color: a.bgColor }); const a0 = at(info, a.at, 0.1), k = ease.out(clamp((lt - a0) / (a.dur || 1.4)));
  const v = lerp(a.from ?? 0, a.to ?? 100, k), d = a.decimals ?? 0;
  const s = v.toLocaleString(({ ja: 'ja-JP', en: 'en-US' })[E.cfg.lang] || 'vi-VN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const pk = pop(lt, a0, 0.4);
  g.save(); g.translate(fx(a.x, 0.5), fy(a.y, 0.45)); g.scale(pk, pk); label(g, (a.prefix || '') + s + (a.suffix || ''), 0, 0, { size: a.size || 190, font: FONT_BOLD, weight: 800, color: a.color || INK }); g.restore();
  if (a.label) label(g, a.label, fx(a.x, 0.5), fy(a.y, 0.45) + (a.size || 190) * 0.75, { size: 56, p: clamp((lt - a0 - 0.3) / 0.6) });
  overlays(g, lt, info);
}));
// ---------- timeline: truc thoi gian ngang. ticks ["4 tỷ năm", ...] hoac marks [{pos 0..1, label, icon, at, above}], pointer {from, to}
tpl('timeline', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'paper'); const y = fy(a.y, 0.6), x0 = E.W * 0.08, x1 = E.W * 0.92, p = grow(lt, at(info, a.at, 0), 0.8);
  arrow(g, x0, y, lerp(x0, x1, p), y, { bend: 0, lw: 8, head: 30 });
  (a.ticks || []).forEach((tk, i, arr) => { const x = lerp(x0, x1 - 60, i / Math.max(1, arr.length - 1)); if ((x - x0) / (x1 - x0) > p) return; line(g, [[x, y - 18], [x, y + 18]], { lw: 6 }); label(g, tk, x, y + 64, { size: 48, caps: false }); });
  (a.marks || []).forEach((m) => { const a0 = at(info, m.at, 0.4); if (lt < a0) return; const x = lerp(x0, x1 - 60, m.pos ?? 0.5), k = clamp((lt - a0) / 0.45), up = m.above !== false; circ(g, x, y, 16 * ease.outBack(k), { fill: m.color || PAL.red, lw: 5 }); if (m.icon) prop(g, m.icon, x, y + (up ? -190 : 190), 200, { scale: ease.outBack(k), t: lt }); if (m.label) tag(g, m.label, x, y + (up ? -60 : 70) + (m.icon ? (up ? -230 : 230) : 0), { size: 46, p: clamp((lt - a0 - 0.2) / 0.5), hl: m.hl }); });
  if (a.pointer) { const k = ease.inOut(clamp((lt - at(info, a.pointer.at, 0.5)) / (a.pointer.dur || 1.5))); const x = lerp(x0, x1 - 60, lerp(a.pointer.from ?? 0, a.pointer.to ?? 1, k)); poly(g, [[x - 22, y - 70], [x + 22, y - 70], [x, y - 30]], { fill: PAL.red, lw: 5 }); }
  overlays(g, lt, info);
}));
// ---------- chart: kind line | bar | pie. data [so], labels [chu], highlight (chi so), unit, at, title
tpl('chart', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'paper'); const d = a.data || [], n = d.length, mx = Math.max(...d, 1), x0 = E.W * 0.14, x1 = E.W * 0.86, y0 = E.H * 0.2, y1 = E.H * (a.bottom ?? 0.78), p = grow(lt, at(info, a.at, 0), a.dur || 1.2);
  if (a.title) label(g, a.title, E.W / 2, E.H * 0.1, { size: 56 });
  if (a.kind === 'pie') {
    const cx = E.W / 2, cy = E.H * 0.53, r = E.H * 0.3, tot = d.reduce((s, v) => s + v, 0) || 1; let ang = -Math.PI / 2; const cols = a.colors || [PAL.sand, PAL.sea, PAL.sage, PAL.terracotta, PAL.yellow, PAL.purple];
    d.forEach((v, i) => { const sw = v / tot * Math.PI * 2 * p; g.save(); g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, r, ang, ang + sw); g.closePath(); g.fillStyle = cols[i % cols.length]; g.fill(); g.lineWidth = 5; g.strokeStyle = INK; g.stroke(); g.restore(); if (a.labels?.[i] && p >= 1) { const m = ang + sw / 2; label(g, a.labels[i], cx + Math.cos(m) * r * 1.3, cy + Math.sin(m) * r * 1.2, { size: 48, caps: false }); } ang += sw; });
  } else {
    line(g, [[x0, y0 - 20], [x0, y1], [x1 + 20, y1]], { lw: 6, smooth: false });
    if (a.kind === 'bar') { const bw = (x1 - x0) / n * 0.6; d.forEach((v, i) => { const x = x0 + (x1 - x0) * (i + 0.5) / n, h = (y1 - y0) * v / mx * clamp(p * 1.3 - i * 0.3 / n); rect(g, x - bw / 2, y1 - h, bw, h, { fill: a.highlight === i ? PAL.red : (a.color || PAL.sea), lw: 5, r: 4 }); if (a.labels?.[i]) label(g, a.labels[i], x, y1 + 46, { size: 48, caps: false }); if (p >= 1 && a.values !== false) label(g, String(v) + (a.unit || ''), x, y1 - h - 34, { size: 46, caps: false }); }); }
    else { const pts = d.map((v, i) => [x0 + (x1 - x0) * i / Math.max(1, n - 1), y1 - (y1 - y0) * v / mx]); line(g, pts, { lw: 7, ink: a.color || PAL.blue, p, smooth: n > 4 }); if (a.highlight !== undefined && p >= 1) circ(g, pts[a.highlight][0], pts[a.highlight][1], 16, { fill: PAL.red, lw: 5 }); (a.labels || []).forEach((l, i) => label(g, l, x0 + (x1 - x0) * i / Math.max(1, (a.labels.length - 1)), y1 + 46, { size: 46, caps: false })); }
  }
  overlays(g, lt, info);
}));
// ---------- icons: hang o vuong, moi o 1 hinh + nhan, hien lan luot. items [{prop|img|person, label, at, mark}], dividers
tpl('icons', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'white', { color: a.bgColor }); const it = a.items || [], n = it.length, s = fs(a.s, Math.min(0.34, 1.1 / Math.max(n, 1))), y = fy(a.y, 0.45);
  it.forEach((x, i) => { const cx = E.W * (i + 0.5) / n; item(g, lt, info, { ...x, at: x.at ?? i * 0.4 }, cx, y, s); if (x.mark) { const a0 = at(info, x.markAt, 1e9); if (lt >= a0) { const p = clamp((lt - a0) / 0.4); if (x.mark === 'cross') cross(g, cx, y, s * 0.55, { p }); if (x.mark === 'check') check(g, cx + s * 0.4, y - s * 0.4, s * 0.25, { p }); if (x.mark === 'circle') { g.save(); g.beginPath(); g.ellipse(cx, y, s * 0.75, s * 0.7, 0, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ease.out(p)); g.lineWidth = 8; g.strokeStyle = PAL.red; g.stroke(); g.restore(); } } } if (a.dividers !== false && i > 0) line(g, [[E.W * i / n, E.H * 0.18], [E.W * i / n, E.H * 0.82]], { lw: 4, ink: '#bdb6aa' }); });
  overlays(g, lt, info);
}));
// ---------- title: the chuong / mo dau. text, sub, icon (prop), bg
tpl('title', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'paper', { color: a.bgColor }); const p = clamp((lt - at(info, a.at, 0.1)) / 0.6);
  if (a.icon) prop(g, a.icon, E.W / 2, E.H * 0.3, E.H * 0.26, { scale: ease.outBack(clamp(p * 1.4)), t: lt });
  const ls = wrap(g, a.text || '', E.W * 0.8, a.size || 96, FONT_BOLD, 800);
  ls.forEach((l, i) => label(g, l, E.W / 2, E.H * (a.icon ? 0.58 : 0.45) + i * (a.size || 96) * 1.1, { size: a.size || 96, font: FONT_BOLD, weight: 800, a: clamp(p * 2), color: a.color || INK }));
  line(g, [[E.W * 0.3, E.H * (a.icon ? 0.58 : 0.45) + ls.length * (a.size || 96) * 1.1 - 20], [E.W * 0.7, E.H * (a.icon ? 0.58 : 0.45) + ls.length * (a.size || 96) * 1.1 - 10]], { lw: 8, ink: PAL.red, p: clamp(p * 1.5 - 0.5) });
  if (a.sub) label(g, a.sub, E.W / 2, E.H * 0.82, { size: 48, caps: false, p: clamp(p * 1.5 - 0.6), color: PAL.grey });
  overlays(g, lt, info);
}));
// ---------- branch: so do nhanh (cay tien hoa / chia nhanh). root [x,y], branches [{to:[x,y], label, color, at, from:[x,y]}]
tpl('branch', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'paper'); const r = a.root || [0.5, 0.9];
  for (const b of a.branches || []) { const a0 = at(info, b.at, 0), p = clamp((lt - a0) / (b.dur || 0.7)); if (p <= 0) continue; const f = b.from || r; line(g, [[fx(f[0]), fy(f[1])], [lerp(fx(f[0]), fx(b.to[0]), 0.5), lerp(fy(f[1]), fy(b.to[1]), 0.65)], [fx(b.to[0]), fy(b.to[1])]], { lw: b.lw || 9, ink: b.color || PAL.woodDark, p }); if (b.label) tag(g, b.label, fx(b.to[0]), fy(b.to[1]) - 44, { size: 48, p: clamp(p * 2 - 1), hl: b.hl }); }
  overlays(g, lt, info);
}));
// ---------- endcard: nguoi dan chuyen vay tay + nut dang ky
tpl('endcard', (g, lt, info, a) => camera(g, lt, info, () => {
  bg(g, a.bg || 'room'); guy(g, E.W * 0.32, E.H * 0.86, E.H * 0.62, { preset: 'host', pose: lt % 2 < 1 ? 'wave' : 'stand', face: 'happy', t: lt });
  const k = pop(lt, 0.5), cl = lt > 1.6 && lt < 1.9;
  g.save(); g.translate(E.W * 0.68, E.H * 0.42); g.scale(k * (cl ? 0.92 : 1), k * (cl ? 0.92 : 1)); rect(g, -230, -60, 460, 120, { fill: lt > 1.75 ? '#8c8c8c' : PAL.red, lw: 6, r: 24 }); label(g, lt > 1.75 ? (a.done || ({ ja: '登録済み', en: 'SUBSCRIBED' })[E.cfg.lang] || 'ĐÃ ĐĂNG KÝ') : (a.button || ({ ja: 'チャンネル登録', en: 'SUBSCRIBE' })[E.cfg.lang] || 'ĐĂNG KÝ'), 0, 4, { size: 64, font: FONT_BOLD, weight: 800, color: '#fff' }); g.restore();
  if (a.text) label(g, a.text, E.W * 0.68, E.H * 0.65, { size: 46, caps: false, p: clamp((lt - 0.9) / 0.8) });
  overlays(g, lt, info);
}));
export const TEMPLATE_LIST = ['comp', 'host', 'bighead', 'ai', 'map', 'compare', 'scale', 'measure', 'list', 'note', 'counter', 'timeline', 'chart', 'icons', 'title', 'branch', 'endcard'];
export { VIEWS };
