// templates.js (pack squire) — mau canh dung bang du lieu trong story/shots.json: { "tpl": "<ten>", "args": {...} }
// Toa do x, y: 0..1 = ti le khung; h, R, s: 0..1 = ti le chieu cao khung. at: so giay trong shot hoac cum chu trong loi doc.
// Mau: scene | close | army | top | map | plan | board | xray | frame | item | split | title | black
import { E, clamp, lerp, ease, registerTemplate, blurLayer, talkAmount, text, img } from '/engine/core.js';
import { OUT, PAL, T, pop, grow, bob, shape, rect, ellipse, circ, blob, polyS, line, tube, sign, blockArrow, curveArrow, qmark, ban, label, haze, vignette, wrap, darker, lighter, alpha, mix, FONT_SIGN, FONT_THUMB, FONT_CAP } from './ink.js';
import { soldier, bust, shield, weapon, charge, CAST, hand, head, arrowStuck, STEP } from './chara.js';
import { horse } from './horse.js';
import { bg, tree, bush, tent, flag, castle, cloud, TIMES } from './world.js';
import { formation, standard, topGround, topBlock, dustPuff, rain, volley, stuckArrows, dust, javelins, smoke, sparks, arrowFly } from './army.js';
import { loadWorld, drawMap, projector, VIEWS } from '../doodle/map.js';
export { loadWorld };

export const fx = (v, d = 0.5) => (v === undefined ? d * E.W : v <= 1.5 ? v * E.W : v);
export const fy = (v, d = 0.5) => (v === undefined ? d * E.H : v <= 1.5 ? v * E.H : v);
export const fs = (v, d = 0.3) => (v === undefined ? d * E.H : v <= 1.5 ? v * E.H : v);
const at = (info, v, d = 0) => T(info, v, d);
const SC = () => Math.min(E.W, E.H) / 1080;            // ti le net/blur theo do phan giai logic
const vert = () => E.H > E.W;

// ---------- may quay: move in|out|left|right|up|down|still, moveAmt, zoom [x, y, z, tu, keo_dai], shake
export function camera(g, lt, info, fn) {
  const a = info.args || {}, d = info.dur, k = ease.sine(clamp(lt / Math.max(d, 0.1))), mv = a.move || 'in', amt = a.moveAmt ?? 0.035;
  let z = 1, dx = 0, dy = 0;
  if (mv === 'in') z = 1 + amt * k; else if (mv === 'out') z = 1 + amt * (1 - k);
  else if (mv === 'left') { z = 1 + amt; dx = lerp(amt, -amt, k) * E.W * 0.45; } else if (mv === 'right') { z = 1 + amt; dx = lerp(-amt, amt, k) * E.W * 0.45; }
  else if (mv === 'up') { z = 1 + amt; dy = lerp(amt, -amt, k) * E.H * 0.45; } else if (mv === 'down') { z = 1 + amt; dy = lerp(-amt, amt, k) * E.H * 0.45; }
  let cx = E.W / 2, cy = E.H / 2;
  if (a.zoom) { const [zx, zy, zz = 1.5, t0 = 0, t1 = 0.8] = a.zoom; const q = ease.inOut(clamp((lt - at(info, t0)) / Math.max(0.05, t1))); z *= lerp(1, zz, q); cx = lerp(cx, fx(zx), q); cy = lerp(cy, fy(zy), q); }
  { const hw = E.W / (2 * z), hh = E.H / (2 * z); cx = clamp(cx + dx, hw, E.W - hw) - dx; cy = clamp(cy + dy, hh, E.H - hh) - dy; }
  if (a.shake) { const t0 = at(info, a.shakeAt, 0), s = a.shake * Math.max(0, 1 - (lt - t0) / 0.5) * (lt >= t0 ? 1 : 0); dx += Math.sin(lt * 70) * 14 * s; dy += Math.cos(lt * 60) * 10 * s; }
  g.save(); g.translate(E.W / 2, E.H / 2); g.scale(z, z); g.translate(-cx - dx, -cy - dy); fn(); g.restore();
}
function listAt(info, lt, list, def) { let v = def; for (const [tt, f] of list || []) if (lt >= at(info, tt, 1e9)) v = f; return v; }

// ---------- nguoi trong canh: { preset, x, y, h, pose, face, faceAt, poseAt, look, lookAt, flip, talk, walk, from, to, dur, at, enter, exit, jump, tremble, rot, fall, ... }
export function person(g, lt, info, p, gy = 0.93, dh = 0.5) {
  const a0 = at(info, p.at, 0); if (lt < a0) return;
  if (p.exit !== undefined && lt > at(info, p.exit, 1e9) + 0.4) return;
  const h = fs(p.h, dh); let x = fx(p.x, 0.5), y = fy(p.y, gy);
  // --- di chuyen: chan cham dat that. walk: true -> tu di ngang theo huong mat; to -> di toi diem; walk: 'front' -> buoc tai cho
  const pose0 = listAt(info, lt, p.poseAt, p.pose || 'stand'), run = pose0 === 'run';
  let walkMode = null, walkPhase, flip = p.flip, travel = 0;
  const hu = (p.horse ? h * (p.horse.h ?? 0.85) : h * (p.kid ? 0.78 : 1)) / 100;
  if (p.to !== undefined) {
    const t0 = at(info, p.moveAt, a0), x0 = fx(p.from ?? p.x), x1 = fx(p.to), k = ease.inOut(clamp((lt - t0) / (p.dur || Math.max(0.3, info.dur - t0))));
    x = lerp(x0, x1, k); travel = Math.abs(x - x0); if (p.flip === undefined) flip = x1 < x0; walkMode = Math.abs(x1 - x0) > 2 ? 'side' : null;
  } else if (p.walk === true || ((pose0 === 'walk' || pose0 === 'run') && p.walk !== 'front' && p.walk !== false) || (p.horse && ['walk', 'gallop'].includes(p.horse.gait) && p.horse.travel !== false)) {
    const dir = (p.dir ?? (p.flip ? -1 : 1)), sp = p.speed ?? 1;
    const v = p.horse ? (p.horse.gait === 'gallop' ? 2.2 * 105 : 0.85 * 35.5) * hu * sp : 2 * STEP * (run ? 1.5 : 1) * hu * (run ? 1.6 : 0.95) * sp;
    travel = v * lt; x += dir * (travel - v * info.dur / 2); flip = dir < 0; walkMode = 'side';
  } else if (p.walk === 'front' || pose0 === 'march') walkMode = 'front';
  if (walkMode === 'side') walkPhase = travel / (2 * STEP * (run ? 1.5 : 1) * hu * 100 / 100 * 1);
  if (p.enter) { const k = ease.out(clamp((lt - a0) / 0.5)); x += (1 - k) * (p.enter === 'left' ? -1 : 1) * E.W * 0.5; }
  if (p.exit !== undefined) { const k = ease.in(clamp((lt - at(info, p.exit, 1e9)) / 0.4)); x += k * E.W * 0.6 * (p.exitDir === 'left' ? -1 : 1); }
  if (p.jump !== undefined) { const t0 = at(info, p.jump, 0); if (lt >= t0) y -= Math.abs(Math.sin((lt - t0) * 9)) * h * 0.06 * Math.max(0, 1 - (lt - t0) / 1.2); }
  if (p.tremble) x += Math.sin(lt * 60) * h * 0.004;
  const talk = p.talk ? talkAmount(info.globalT, info.start + at(info, p.talkFrom, 0), info.start + (p.talkTo !== undefined ? at(info, p.talkTo, info.dur) : info.dur)) : 0;
  const pk = p.pop ? pop(lt, a0, 0.4) : 1;
  g.save(); if (pk < 1) { g.translate(x, y); g.scale(pk, pk); g.translate(-x, -y); }
  if (p.fall !== undefined) { const t0 = at(info, p.fall, 0), k = ease.inOut(clamp((lt - t0) / 0.5)); if (lt >= t0) { g.translate(x, y); g.rotate(k * (p.flip ? -1 : 1) * 1.45); g.translate(-x, -y); } }
  const lk = listAt(info, lt, p.lookAt, p.look);
  const o = { ...p, t: lt + (p.seed || 0) * 0.37, pose: pose0, face: listAt(info, lt, p.faceAt, p.face || 'neutral'), look: lk === undefined ? (walkMode === 'side' ? 0.75 : 0) : lk, talk, flip, walkMode: p.horse ? null : walkMode, walkPhase: p.horse ? undefined : walkPhase, walk: p.horse ? false : !!walkMode, lw: p.lw };
  if (p.horse) horse(g, x, y, h * (p.horse.h ?? 0.85), { ...p.horse, t: lt, flip, travel: walkMode === 'side' ? travel : undefined, rider: { ...o, x: undefined, y: undefined, h: undefined, flip: false, look: lk ?? 0.5 }, riderH: p.horse.riderH });
  else soldier(g, x, y, h, o);
  g.restore();
}
export function drawPeople(g, lt, info, list, gy, dh) { for (const p of list || []) person(g, lt, info, p, gy, dh); }
// ---------- do vat: { kind, x, y, s, at, anim: pop|drop|grow|fall|spin, rot, ...tuy chon }
export function prop(g, lt, info, p) {
  const a0 = at(info, p.at, 0); if (lt < a0) return;
  const x = fx(p.x), s = fs(p.s, 0.2); let y = fy(p.y), sc = 1, rot = p.rot || 0; const k = clamp((lt - a0) / 0.45), anim = p.anim || 'none';
  if (anim === 'pop') sc = ease.outBack(k); else if (anim === 'drop') y -= (1 - ease.outBack(k)) * E.H * 0.5; else if (anim === 'grow') sc = ease.inOut(clamp((lt - a0) / 0.9));
  else if (anim === 'spin') rot += lt * 1.4; else if (anim === 'float') y += bob(lt, 8, 0.8, x);
  if (p.gone !== undefined) { const kk = clamp((lt - at(info, p.gone, 1e9)) / 0.4); if (kk >= 1) { if (p.ghost) ghost(g, p, x, y, s); return; } sc *= 1 - kk; }
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(sc, sc); if (p.flip) g.scale(-1, 1);
  drawThing(g, p.kind, 0, 0, s, { ...p, t: lt });
  g.restore();
}
function ghost(g, p, x, y, s) { g.save(); g.translate(x, y); g.setLineDash([s * 0.06, s * 0.05]); g.lineWidth = Math.max(3, s * 0.025); g.strokeStyle = '#ffffff'; g.beginPath(); if (p.kind === 'shield' && (p.type || 'heater') === 'kite') { g.moveTo(0, -s * 0.5); g.bezierCurveTo(s * 0.4, -s * 0.5, s * 0.36, -s * 0.05, 0, s * 0.62); g.bezierCurveTo(-s * 0.36, -s * 0.05, -s * 0.4, -s * 0.5, 0, -s * 0.5); } else { g.moveTo(-s * 0.36, -s * 0.42); g.lineTo(s * 0.36, -s * 0.42); g.bezierCurveTo(s * 0.38, s * 0.05, s * 0.2, s * 0.32, 0, s * 0.46); g.bezierCurveTo(-s * 0.2, s * 0.32, -s * 0.38, s * 0.05, -s * 0.36, -s * 0.42); } g.stroke(); g.restore(); }
// cac do vat ve duoc: shield | sword | spear | pilum | pollaxe | bow | crossbow | rifle | torch | flag | standard | eagle | tent | tree | pine | cypress | bush | castle | cloud |
// helmet (o.helmet) | gauntlet | arrow | arrows | sack | barrel | rock | cart | pavise | horse | campfire | chest | coin | scroll | seal | anvil | easel | crane | car | grenade | lantern | cauldron
export function drawThing(g, kind, x, y, s, o = {}) {
  const lw = o.lw ?? Math.max(1.5, s * 0.025);
  switch (kind) {
    case 'shield': shield(g, x, y, s, { ...o, type: o.type || 'heater', lw: o.lw }); break;
    case 'pavise': shield(g, x, y, s, { ...o, type: 'pavise' }); break;
    case 'shovel': case 'pickaxe': case 'saw': case 'stake': case 'pot': case 'basket': case 'sword': case 'spear': case 'pilum': case 'pollaxe': case 'axe': case 'bow': case 'crossbow': case 'rifle': case 'musket': case 'torch': case 'katana': case 'lance': case 'mace': case 'hammer': case 'dagger': case 'naginata': case 'grenade': case 'scroll': case 'pouch':
      weapon(g, kind, x, y + ((kind === 'pot' || kind === 'basket') ? -s * 0.25 : s * 0.5), s, o.ang ?? (kind === 'bow' ? Math.PI / 2 : (kind === 'pot' || kind === 'basket') ? 0 : Math.PI), { ...o, lw }); break;
    case 'flag': flag(g, x, y + s * 0.5, s, o); break;
    case 'standard': case 'eagle': standard(g, x, y + s * 0.5, s, { ...o, kind: kind === 'eagle' ? 'eagle' : o.style }); break;
    case 'tent': tent(g, x, y + s * 0.5, s, o); break;
    case 'tree': case 'pine': case 'cypress': tree(g, x, y + s * 0.5, s, { ...o, kind: kind === 'tree' ? o.style : kind }); break;
    case 'bush': bush(g, x, y, s * 0.5, o); break;
    case 'castle': castle(g, x, y + s * 0.5, s, o); break;
    case 'cloud': cloud(g, x, y, s * 0.5, o); break;
    case 'helmet': head(g, x, y + s * 0.12, s * 0.32, { helmet: o.helmet || 'bucket', visor: o.visor, face: 'neutral', skin: o.empty ? '#3a2f2a' : undefined, feathers: o.feathers, crest: o.crest, lw }); break;
    case 'gauntlet': { g.save(); g.translate(x, y); g.rotate(o.rot2 || 0); rect(g, -s * 0.5, -s * 0.12, s * 0.55, s * 0.24, { fill: PAL.steel, lw, r: s * 0.04, inner: (c) => { line(c, [[-s * 0.3, -s * 0.12], [-s * 0.3, s * 0.12]], { lw: lw * 0.6 }); line(c, [[-s * 0.1, -s * 0.12], [-s * 0.1, s * 0.12]], { lw: lw * 0.6 }); rect(c, -s * 0.42, -s * 0.13, s * 0.05, s * 0.26, { fill: PAL.leather, lw: lw * 0.5, r: 1 }); } }); for (let i = 0; i < 4; i++) { const yy = -s * 0.1 + i * s * 0.07; tube(g, [[s * 0.05, yy], [s * 0.3, yy - s * 0.03], [s * 0.42, yy + s * 0.02]], s * 0.055, PAL.steelLight, lw * 0.9); } ellipse(g, s * 0.05, -s * 0.16, s * 0.12, s * 0.05, { fill: PAL.steelLight, lw: lw * 0.9, rot: -0.6 }); g.restore(); break; }
    case 'arrow': arrowFly(g, x + s * 0.5, y, s, o.ang ?? 0, lw); break;
    case 'arrowhead': polyS(g, [[x, y - s * 0.5], [x + s * 0.18, y + s * 0.2], [x, y + s * 0.1], [x - s * 0.18, y + s * 0.2]], { fill: PAL.steelDark, lw, inner: (c) => line(c, [[x, y - s * 0.45], [x, y + s * 0.1]], { lw: lw * 0.5, ink: '#fff', a: 0.5 }) }); tube(g, [[x, y + s * 0.12], [x, y + s * 0.5]], s * 0.08, PAL.steelDark, lw); break;
    case 'arrows': for (let i = 0; i < (o.n || 5); i++) arrowStuck(g, x + (i - 2) * s * 0.12, y + s * 0.3, s * 0.6, -Math.PI / 2 + (i - 2) * 0.12, lw); break;
    case 'sack': blob(g, [[x - s * 0.35, y + s * 0.4], [x - s * 0.4, y], [x - s * 0.18, y - s * 0.38], [x + s * 0.18, y - s * 0.38], [x + s * 0.4, y], [x + s * 0.35, y + s * 0.4]], { fill: '#c8a873', lw }); line(g, [[x - s * 0.16, y - s * 0.28], [x + s * 0.16, y - s * 0.28]], { lw: lw * 1.2 }); break;
    case 'barrel': rect(g, x - s * 0.3, y - s * 0.45, s * 0.6, s * 0.9, { fill: PAL.wood, lw, r: s * 0.18, inner: (c) => { for (const k of [-0.25, 0.25]) rect(c, x - s * 0.4, y + k * s, s * 0.8, s * 0.07, { fill: PAL.steelDark, lw: lw * 0.6, r: 0 }); } }); break;
    case 'rock': blob(g, [[x - s * 0.5, y + s * 0.2], [x - s * 0.35, y - s * 0.2], [x, y - s * 0.3], [x + s * 0.4, y - s * 0.15], [x + s * 0.5, y + s * 0.2]], { fill: PAL.stoneDark, lw }); break;
    case 'campfire': { for (const k of [-1, 1]) tube(g, [[x - k * s * 0.3, y + s * 0.15], [x + k * s * 0.3, y - s * 0.02]], s * 0.08, PAL.woodDark, lw); const f = 1 + Math.sin((o.t || 0) * 12) * 0.08; shape(g, (c) => { c.moveTo(x - s * 0.22, y + s * 0.05); c.quadraticCurveTo(x - s * 0.3, y - s * 0.3 * f, x, y - s * 0.55 * f); c.quadraticCurveTo(x + s * 0.3, y - s * 0.3 * f, x + s * 0.22, y + s * 0.05); c.closePath(); }, { fill: '#f6a43a', lw, inner: (c) => ellipse(c, x, y - s * 0.08, s * 0.08, s * 0.16, { fill: '#ffe38a', lw: 0 }) }); break; }
    case 'chest': rect(g, x - s * 0.4, y - s * 0.25, s * 0.8, s * 0.5, { fill: PAL.wood, lw, r: s * 0.05, inner: (c) => { line(c, [[x - s * 0.4, y - s * 0.05], [x + s * 0.4, y - s * 0.05]], { lw }); rect(c, x - s * 0.05, y - s * 0.1, s * 0.1, s * 0.12, { fill: PAL.gold, lw: lw * 0.6, r: 2 }); } }); break;
    case 'coin': circ(g, x, y, s * 0.4, { fill: PAL.gold, lw, inner: (c) => { circ(c, x, y, s * 0.3, { fill: null, lw: lw * 0.6, ink: PAL.goldDark }); } }); break;
    case 'seal': circ(g, x, y, s * 0.42, { fill: '#c64b3a', lw, inner: (c) => charge(c, o.charge || 'lion', x, y, s * 0.5, '#8a2a20') }); break;
    case 'easel': { line(g, [[x - s * 0.35, y + s * 0.5], [x, y - s * 0.5], [x + s * 0.35, y + s * 0.5]], { lw: s * 0.05, ink: PAL.woodDark }); rect(g, x - s * 0.42, y + s * 0.05, s * 0.84, s * 0.05, { fill: PAL.wood, lw, r: 2 }); break; }
    case 'anvil': polyS(g, [[x - s * 0.5, y - s * 0.2], [x + s * 0.35, y - s * 0.2], [x + s * 0.5, y - s * 0.32], [x + s * 0.4, y - s * 0.05], [x + s * 0.15, y], [x + s * 0.25, y + s * 0.3], [x - s * 0.3, y + s * 0.3], [x - s * 0.18, y], [x - s * 0.5, y - s * 0.05]], { fill: '#4c4a4c', lw }); break;
    case 'lantern': rect(g, x - s * 0.2, y - s * 0.3, s * 0.4, s * 0.6, { fill: '#f6d37a', lw, r: s * 0.08 }); break;
    case 'cart': { rect(g, x - s * 0.5, y - s * 0.3, s, s * 0.3, { fill: PAL.wood, lw, r: 4 }); for (const k of [-0.32, 0.32]) circ(g, x + k * s, y + s * 0.05, s * 0.16, { fill: PAL.woodDark, lw }); break; }
    case 'car': { blob(g, [[x - s * 0.5, y + s * 0.1], [x - s * 0.45, y - s * 0.12], [x - s * 0.2, y - s * 0.32], [x + s * 0.25, y - s * 0.32], [x + s * 0.45, y - s * 0.1], [x + s * 0.5, y + s * 0.12]], { fill: o.color || PAL.red, lw }); rect(g, x - s * 0.14, y - s * 0.28, s * 0.32, s * 0.15, { fill: '#cfe5f0', lw: lw * 0.8, r: 4 }); for (const k of [-0.3, 0.3]) circ(g, x + k * s, y + s * 0.12, s * 0.12, { fill: PAL.black, lw }); if (o.badge) charge(g, 'quarter', x, y, s * 0.05, PAL.black); break; }
    case 'cauldron': ellipse(g, x, y, s * 0.4, s * 0.32, { fill: PAL.black, lw }); break;
    case 'skull': circ(g, x, y, s * 0.3, { fill: '#efe7d6', lw }); circ(g, x - s * 0.1, y, s * 0.07, { fill: OUT, lw: 0 }); circ(g, x + s * 0.1, y, s * 0.07, { fill: OUT, lw: 0 }); break;
    case 'soldier': soldier(g, x, y + s * 0.5, s, { ...o, t: o.t }); break;
    case 'horse': horse(g, x, y + s * 0.5, s, o); break;
  }
}
// ---------- lop phu chung
export function overlays(g, lt, info) {
  const a = info.args || {};
  for (const l of a.arrows || []) {
    const a0 = at(info, l.at, 0); if (lt < a0) continue; const p = clamp((lt - a0) / (l.dur || 0.45));
    if (l.kind === 'curve') curveArrow(g, l.pts.map(([x, y]) => [fx(x), fy(y)]), { p, lw: (l.lw || 14) * SC(), color: l.color || PAL.red });
    else if (l.kind === 'line') line(g, [[fx(l.from[0]), fy(l.from[1])], [fx(l.to[0]), fy(l.to[1])]], { p, lw: (l.lw || 8) * SC(), ink: l.color || PAL.red, dash: l.dash ? [20, 14] : null });
    else blockArrow(g, fx(l.from[0]), fy(l.from[1]), fx(l.to[0]), fy(l.to[1]), { p, w: (l.w || 40) * SC(), fill: l.color || PAL.red, lw: 6 * SC() });
  }
  for (const m of a.marks || []) {
    const a0 = at(info, m.at, 0); if (lt < a0) continue; const p = clamp((lt - a0) / 0.4), x = fx(m.x), y = fy(m.y), r = fs(m.r, 0.08);
    if (m.kind === 'q' || m.kind === '!') { const k = ease.outBack(p); g.save(); g.translate(x, y); g.scale(k, k); if (m.glow) { const gr = g.createRadialGradient(0, 0, r * 0.2, 0, 0, r * 2); gr.addColorStop(0, 'rgba(230,60,50,0.5)'); gr.addColorStop(1, 'rgba(230,60,50,0)'); g.fillStyle = gr; g.fillRect(-r * 2, -r * 2, r * 4, r * 4); } qmark(g, 0, 0, r * 2.2, { ch: m.kind === 'q' ? '?' : '!', color: m.color || PAL.red }); g.restore(); }
    else if (m.kind === 'ban') ban(g, x, y, r, { p });
    else if (m.kind === 'circle') { g.save(); g.beginPath(); g.ellipse(x, y, r * (m.rx || 1.3), r, 0, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ease.out(p)); g.lineWidth = 9 * SC(); g.strokeStyle = OUT; g.stroke(); g.lineWidth = 5.5 * SC(); g.strokeStyle = m.color || PAL.red; g.stroke(); g.restore(); }
    else if (m.kind === 'dashed') { g.save(); g.setLineDash([16 * SC(), 12 * SC()]); g.lineWidth = 5 * SC(); g.strokeStyle = m.color || '#ffffff'; g.globalAlpha = p; g.beginPath(); g.ellipse(x, y, r * (m.rx || 1), r * (m.ry || 1.2), 0, 0, Math.PI * 2); g.stroke(); g.restore(); }
    else if (m.kind === 'sparks') sparks(g, x, y, r * 2, lt, a0);
    else if (m.kind === 'x') { line(g, [[x - r, y - r], [x + r, y + r]], { lw: r * 0.3, ink: OUT, p }); line(g, [[x + r, y - r], [x - r, y + r]], { lw: r * 0.3, ink: OUT, p: clamp(p * 2 - 1) }); line(g, [[x - r, y - r], [x + r, y + r]], { lw: r * 0.18, ink: PAL.red, p }); line(g, [[x + r, y - r], [x - r, y + r]], { lw: r * 0.18, ink: PAL.red, p: clamp(p * 2 - 1) }); }
  }
  for (const s of a.signs || []) { const a0 = at(info, s.at, 0); if (lt < a0) continue; sign(g, s.text, fx(s.x), fy(s.y), { size: (s.size || 40) * SC(), p: clamp((lt - a0) / 0.35), tail: s.tail ?? 'down', fill: s.fill, color: s.color, rot: s.rot || 0 }); }
  for (const l of a.labels || []) {
    const a0 = at(info, l.at, 0); if (lt < a0) continue; const p = clamp((lt - a0) / 0.3), k = ease.outBack(p), size = (l.size || 90) * SC();
    g.save(); g.translate(fx(l.x), fy(l.y)); g.rotate(l.rot || 0); g.scale(k, k);
    if (l.kind === 'chalk') label(g, l.text, 0, 0, { size, font: FONT_SIGN, color: l.color || PAL.chalkLine });
    else if (l.kind === 'sign') label(g, l.text, 0, 0, { size, font: FONT_SIGN, color: l.color || OUT });
    else { text(g, String(l.text).toUpperCase(), size * 0.05, size * 0.1, { size, font: FONT_THUMB, weight: 400, color: OUT, stroke: size * 0.26, strokeColor: OUT, align: 'center' }); text(g, String(l.text).toUpperCase(), 0, 0, { size, font: FONT_THUMB, weight: 400, color: l.color || '#ffffff', stroke: size * 0.2, strokeColor: OUT, align: 'center' }); text(g, String(l.text).toUpperCase(), 0, 0, { size, font: FONT_THUMB, weight: 400, color: l.color || '#ffffff', align: 'center' }); }
    g.restore();
  }
}
function effects(g, lt, info, list) {
  for (const f of list || []) {
    const a0 = at(info, f.at, 0); if (lt < a0 && f.kind !== 'rain') continue; const tt = lt;
    if (f.kind === 'rain') rain(g, lt, { ...f, len: fs(f.len, 0.05) });
    else if (f.kind === 'volley' || f.kind === 'arrows') volley(g, tt, { ...f, at: a0 });
    else if (f.kind === 'javelins') javelins(g, tt, { ...f, at: a0 });
    else if (f.kind === 'stuck') stuckArrows(g, f);
    else if (f.kind === 'dust') dust(g, lt, f);
    else if (f.kind === 'smoke') smoke(g, lt, f);
    else if (f.kind === 'rays') { g.save(); g.globalAlpha = f.a ?? 0.18; g.fillStyle = f.color || '#fff4d6'; for (let i = 0; i < (f.n || 4); i++) { const x = E.W * ((f.x ?? 0.7) + i * 0.08); g.beginPath(); g.moveTo(x, -10); g.lineTo(x + E.W * 0.05, -10); g.lineTo(x - E.W * 0.25, E.H + 10); g.lineTo(x - E.W * 0.32, E.H + 10); g.fill(); } g.restore(); }
    else if (f.kind === 'flash') { const k = clamp((lt - a0) / 0.3); if (k < 1) haze(g, f.color || '#ffffff', (1 - k) * 0.7); }
    else if (f.kind === 'thunder') { const k = (lt - a0) % 3; if (k < 0.15) haze(g, '#eef4ff', 0.5 - k * 3); }
  }
}

// ======================================================================================= SCENE
// args: bg, time, bgOpts, blur (px nen), back: [doi hinh trong nen mo], mid: [doi hinh net phia sau], people, props, front: [nguoi tien canh mo],
//       fx: [{kind:'rain'|'volley'|'javelins'|'stuck'|'dust'|'smoke'|'rays'|'flash'|'thunder'}], signs, arrows, marks, labels, tint: [mau, a], dark, vignette
function sceneBody(g, lt, info, a) {
  const bo = { time: a.time, seed: a.seed, ...(a.bgOpts || {}), t: lt };
  const bl = (a.blur ?? (vert() ? 5 : 6)) * SC();
  const backLayer = (c) => { bg(c, a.bg || 'field', bo); for (const f of a.back || []) formation(c, { lodH: 120, ...f, t: lt }); for (const p of a.backPeople || []) person(c, lt, info, p, 0.7, 0.2); for (const p of a.backProps || []) prop(c, lt, info, p); };
  if (bl > 0.3) blurLayer(g, bl, backLayer); else backLayer(g);
  if (a.midHaze) haze(g, a.midHaze[0], a.midHaze[1]); else if ((a.bg || 'field') === 'plain') haze(g, '#e9c486', 0.1);
  for (const f of a.mid || []) formation(g, { ...f, t: lt });
  for (const p of a.props || []) if (!p.top) prop(g, lt, info, p);
  drawPeople(g, lt, info, a.people, 0.93, vert() ? 0.36 : 0.55);
  for (const p of a.props || []) if (p.top) prop(g, lt, info, p);
  if (a.front && a.front.length) blurLayer(g, (a.frontBlur ?? 7) * SC(), (c) => drawPeople(c, lt, info, a.front, 1.25, 0.9));
  effects(g, lt, info, a.fx);
  if (a.tint) haze(g, a.tint[0], a.tint[1]);
  if (a.dark) haze(g, '#1a1020', a.dark);
}
registerTemplate('scene', { draw(g, lt, info) { const a = info.args || {}; camera(g, lt, info, () => { sceneBody(g, lt, info, a); overlays(g, lt, info); }); if (a.vignette !== false) vignette(g, a.vignette ?? 0.18); } });
// army: canh doi hinh (mac dinh 1 khoi quan lon, co the them doi hinh doi dien)
registerTemplate('army', { draw(g, lt, info) {
  const a = info.args || {};
  const mid = a.mid || [{ preset: a.preset || 'hastatus', presets: a.presets, rows: a.rows || 4, cols: a.cols || 9, x0: 0.02, x1: 0.98, yFront: 1.02, yBack: 0.72, hFront: vert() ? 0.26 : 0.42, hBack: 0.16, march: a.march, flip: a.flip, face: a.face, flags: a.flags }];
  camera(g, lt, info, () => { sceneBody(g, lt, info, { ...a, mid, back: a.back || [{ preset: a.enemy || a.preset || 'latin', presets: a.enemyPresets, rows: 3, cols: 22, x0: 0, x1: 1, yFront: 0.74, yBack: 0.66, hFront: 0.09, hBack: 0.06, flip: !a.flip, flags: a.enemyFlags }] }); overlays(g, lt, info); });
  vignette(g, 0.2);
} });
// ======================================================================================= CLOSE
// can mat: preset, face, faceAt, talk, x, y, R (ban kinh dau / H), look, others: [{preset,x,y,R,face,...}], bg + back (mo manh), lean
registerTemplate('close', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    const bo = { time: a.time, seed: a.seed, ...(a.bgOpts || {}), t: lt, groundY: a.groundY ?? 0.62 };
    blurLayer(g, (a.blur ?? 12) * SC(), (c) => { bg(c, a.bg || 'field', bo); for (const f of a.back || []) formation(c, { lodH: 140, ...f, t: lt }); });
    if (a.tint) haze(g, a.tint[0], a.tint[1]);
    const R = fs(a.R, vert() ? 0.13 : 0.24);
    const list = [...(a.others || []), { ...a, others: undefined, main: true }];
    for (const p of list) {
      const a0 = at(info, p.at, 0); if (lt < a0) continue;
      const r = p.main ? R : fs(p.R, 0.16), x = fx(p.x, p.main ? 0.5 : 0.2), y = fy(p.y, p.main ? (vert() ? 0.5 : 0.48) : 0.5) + bob(lt, r * 0.012, 0.7, x);
      const talk = p.talk ? talkAmount(info.globalT, info.start + at(info, p.talkFrom, 0), info.start + info.dur) : 0;
      bust(g, x, y, r, { ...p, shield: p.keepShield ? undefined : (p.shieldClose ?? null), x: undefined, y: undefined, t: lt + (p.seed || 0), face: listAt(info, lt, p.faceAt, p.face || 'neutral'), look: listAt(info, lt, p.lookAt, p.look || 0), pose: listAt(info, lt, p.poseAt, p.pose || 'stand'), talk, gesture: p.gesture });
    }
    effects(g, lt, info, a.fx);
    for (const p of a.props || []) prop(g, lt, info, p);
    overlays(g, lt, info);
  });
  vignette(g, 0.2);
} });
// vung/tuong chu nhat ve dan (trai, hao, tuong ranh): zones: [{x,y,w,h,color,fill,dashed,lw,at,dur}]
function zones(g, lt, info, list) {
  for (const z of list || []) { const a0 = at(info, z.at, 0); if (lt < a0) continue; const p = clamp((lt - a0) / (z.dur || 1)), x = fx(z.x), y = fy(z.y), w = fx(z.w, 0.3), h = fy(z.h, 0.3);
    if (z.fill) { g.save(); g.globalAlpha = p * (z.fa ?? 0.5); g.fillStyle = z.fill; g.fillRect(x - w / 2, y - h / 2, w, h); g.restore(); }
    const per = 2 * (w + h), L = per * ease.inOut(p), pts = [[x - w / 2, y - h / 2], [x + w / 2, y - h / 2], [x + w / 2, y + h / 2], [x - w / 2, y + h / 2], [x - w / 2, y - h / 2]];
    g.save(); g.lineWidth = (z.lw || 10) * SC(); g.strokeStyle = z.color || PAL.woodDark; g.lineCap = 'round'; if (z.dashed) g.setLineDash([18 * SC(), 12 * SC()]); g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); let rem = L; for (let i = 1; i < pts.length && rem > 0; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]), k = Math.min(1, rem / d); g.lineTo(lerp(pts[i - 1][0], pts[i][0], k), lerp(pts[i - 1][1], pts[i][1], k)); rem -= d; } g.stroke(); g.restore(); }
}
// ======================================================================================= TOP (so do nhin tu tren)
// args: ground {color, grass, rocks}, blocks: [...], dust: [{x,y,s,at}], fx, arrows, labels, signs, fog: [x0, x1] (vung bui mo che)
registerTemplate('top', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    topGround(g, a.ground || {});
    for (const b of a.blocks || []) { const a0 = at(info, b.at, 0); if (lt < a0) continue; const bb = { ...b, path: b.path ? b.path.map(([tt, x, y]) => [at(info, tt, 0), x, y]) : null, fade: b.fade ? b.fade.map((v) => at(info, v, 0)) : null }; topBlock(g, bb, lt); }
    zones(g, lt, info, a.zones);
    for (const d of a.dust || []) { const a0 = at(info, d.at, 0); if (lt < a0) continue; dustPuff(g, fx(d.x), fy(d.y), fs(d.s, 0.12), (d.a ?? 0.7) * clamp((lt - a0) / 0.5), lt); }
    if (a.fog) { const [x0, x1] = a.fog; g.save(); const gr = g.createLinearGradient(fx(x0), 0, fx(x1), 0); gr.addColorStop(0, 'rgba(225,206,160,0)'); gr.addColorStop(0.3, 'rgba(225,206,160,0.92)'); gr.addColorStop(0.7, 'rgba(225,206,160,0.92)'); gr.addColorStop(1, 'rgba(225,206,160,0)'); g.fillStyle = gr; g.fillRect(fx(x0), -10, fx(x1) - fx(x0), E.H + 20); g.restore(); }
    effects(g, lt, info, a.fx);
    overlays(g, lt, info);
  });
  vignette(g, 0.22);
} });
// ======================================================================================= MAP (ban do giay da tren ban go)
// args: view (ten VIEWS hoac [lon0,lat0,lon1,lat1]), places: [{text, lon, lat, at}], routes: [{pts: [[lon,lat],...], at, dur, color}],
//       troops: [{lon, lat, side, at, n}], mountains: [{lon, lat, s, label}], table (true), props (compa, but)
function parchment(g, x, y, w, h, o = {}) {
  shape(g, (c) => { c.moveTo(x, y + h * 0.02); c.quadraticCurveTo(x + w * 0.5, y - h * 0.015, x + w, y + h * 0.01); c.quadraticCurveTo(x + w * 1.01, y + h * 0.5, x + w - w * 0.005, y + h); c.quadraticCurveTo(x + w * 0.5, y + h * 1.015, x + w * 0.005, y + h * 0.99); c.quadraticCurveTo(x - w * 0.01, y + h * 0.5, x, y + h * 0.02); c.closePath(); }, { fill: o.color || PAL.parchment, lw: 5 * SC(), inner: (c) => { const gr = c.createRadialGradient(x + w / 2, y + h / 2, Math.min(w, h) * 0.3, x + w / 2, y + h / 2, Math.max(w, h) * 0.7); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(1, 'rgba(150,110,60,0.35)'); c.fillStyle = gr; c.fillRect(x, y, w, h); if (o.inner) o.inner(c); } });
}
function table(g) { g.fillStyle = '#6e4a2c'; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3); g.save(); g.strokeStyle = 'rgba(40,25,15,0.4)'; g.lineWidth = 3 * SC(); for (let y = 0; y < E.H; y += E.H * 0.14) { g.beginPath(); g.moveTo(0, y); g.lineTo(E.W, y); g.stroke(); } g.restore(); }
registerTemplate('map', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    table(g);
    const m = vert() ? 0.06 : 0.08, X = E.W * m, Y = E.H * (vert() ? 0.18 : 0.08), Wd = E.W * (1 - 2 * m), Hd = E.H * (vert() ? 0.64 : 0.84);
    let P = null;
    parchment(g, X, Y, Wd, Hd, { inner: (c) => {
      if (a.view) { P = drawMapClip(c, a.view, [X, Y, Wd, Hd]); }
    } });
    if (!P && a.view) P = projector(a.view, [X, Y, Wd, Hd], 'cover');
    const proj = (lon, lat) => (P ? P(lon, lat) : [fx(lon), fy(lat)]);
    for (const mt of a.mountains || []) { const [x, y] = proj(mt.lon, mt.lat), s = fs(mt.s, 0.09); polyS(g, [[x - s, y + s * 0.4], [x, y - s * 0.7], [x + s, y + s * 0.4]], { fill: '#b9a27a', lw: 4 * SC(), inner: (c) => { c.fillStyle = 'rgba(70,40,20,0.2)'; c.beginPath(); c.moveTo(x, y - s * 0.7); c.lineTo(x + s, y + s * 0.4); c.lineTo(x + s * 0.2, y + s * 0.4); c.fill(); } }); if (mt.label) label(g, mt.label, x, y - s * 0.95, { size: 36 * SC(), color: OUT }); }
    for (const tp of a.troops || []) { const a0 = at(info, tp.at, 0); if (lt < a0) continue; const [x, y] = proj(tp.lon, tp.lat), k = ease.outBack(clamp((lt - a0) / 0.4)), col = tp.side === 'red' ? PAL.red : tp.side === 'green' ? PAL.green : PAL.blue; g.save(); g.translate(x, y); g.scale(k, k); for (let i = 0; i < (tp.n || 6); i++) { const xx = ((i % 3) - 1) * 26 * SC(), yy = (Math.floor(i / 3) - 0.5) * 30 * SC(); rect(g, xx - 10 * SC(), yy - 12 * SC(), 20 * SC(), 24 * SC(), { fill: col, lw: 3 * SC(), r: 3 }); } g.restore(); }
    for (const r of a.routes || []) { const a0 = at(info, r.at, 0); if (lt < a0) continue; curveArrow(g, r.pts.map(([lo, la]) => proj(lo, la)), { p: clamp((lt - a0) / (r.dur || 1.2)), lw: (r.lw || 12) * SC(), color: r.color || '#a3392c', outline: false }); }
    for (const p of a.places || []) { const a0 = at(info, p.at, 0); if (lt < a0) continue; const [x, y] = proj(p.lon, p.lat), k = clamp((lt - a0) / 0.3); if (p.dot !== false) circ(g, x, y, 7 * SC(), { fill: '#a3392c', lw: 3 * SC(), a: k }); label(g, p.text, x + (p.dx || 0) * E.W, y - 30 * SC() + (p.dy || 0) * E.H, { size: (p.size || 46) * SC(), color: OUT, a: k, rot: p.rot || 0 }); }
    if (a.compass !== false) { const cx = X + Wd * 0.92, cy = Y + Hd * 0.85, s = 40 * SC(); polyS(g, [[cx, cy - s], [cx + s * 0.25, cy], [cx, cy + s], [cx - s * 0.25, cy]], { fill: PAL.cream, lw: 3 * SC() }); polyS(g, [[cx, cy - s], [cx + s * 0.25, cy], [cx - s * 0.25, cy]], { fill: '#a3392c', lw: 3 * SC() }); }
    overlays(g, lt, info);
  });
  vignette(g, 0.25);
} });
function drawMapClip(c, view, rect4) {
  // ban do mau giay: bien xanh nhat, dat kem, bo bien nau
  const P = drawMap(c, view, { rect: rect4, fit: 'cover', sea: '#a9c3c0', land: '#e8d6a8', borders: false, coast: 3, islands: true, islandLabels: false });
  return P;
}
// ======================================================================================= PLAN (so do khoi tren giay / bang - toa do 0..1 trong to giay)
// args: paper: 'parchment' | 'notebook', blocks: [{x,y,w,h,side,at,path,cols,rows,style:'rect'}], arrows, labels, signs
registerTemplate('plan', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    table(g);
    const X = E.W * 0.06, Y = E.H * (vert() ? 0.2 : 0.07), Wd = E.W * 0.88, Hd = E.H * (vert() ? 0.6 : 0.86);
    parchment(g, X, Y, Wd, Hd, { color: a.paper === 'notebook' ? '#f3ecd8' : PAL.parchment, inner: (c) => { if (a.paper === 'notebook') { c.save(); c.strokeStyle = 'rgba(120,150,190,0.4)'; c.lineWidth = 2; for (let y = Y + 30; y < Y + Hd; y += 30 * SC()) { c.beginPath(); c.moveTo(X, y); c.lineTo(X + Wd, y); c.stroke(); } c.restore(); } } });
    zones(g, lt, info, a.zones);
    for (const b of a.blocks || []) { const a0 = at(info, b.at, 0); if (lt < a0) continue; const bb = { style: 'rect', ...b, path: b.path ? b.path.map(([tt, x, y]) => [at(info, tt, 0), x, y]) : null, fade: b.fade ? b.fade.map((v) => at(info, v, 0)) : null }; topBlock(g, bb, lt); }
    overlays(g, lt, info);
  });
  vignette(g, 0.25);
} });
// ======================================================================================= BOARD (bang phan)
// args: title, bars: [{label, v, at, hatch}], max, chart: 'bars' | 'none', curve: [[x,y],...] (0..1 trong bang), labels(kind chalk), arrows
registerTemplate('board', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    g.fillStyle = '#4a3324'; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3);
    const X = E.W * 0.03, Y = E.H * (vert() ? 0.15 : 0.03), Wd = E.W * 0.94, Hd = E.H * (vert() ? 0.7 : 0.9);
    rect(g, X, Y, Wd, Hd, { fill: PAL.woodDark, lw: 6 * SC(), r: 10 * SC() }); rect(g, X + 26 * SC(), Y + 26 * SC(), Wd - 52 * SC(), Hd - 52 * SC(), { fill: PAL.chalk, lw: 5 * SC(), r: 4, inner: (c) => { c.save(); c.globalAlpha = 0.07; c.fillStyle = '#fff'; for (let i = 0; i < 30; i++) c.fillRect(X + ((i * 397) % Wd), Y + ((i * 211) % Hd), 120, 6); c.restore(); } });
    if (a.title) label(g, a.title, X + Wd * 0.14, Y + Hd * 0.12, { size: 54 * SC(), color: PAL.chalkLine, align: 'left' });
    const base = Y + Hd * 0.8;
    line(g, [[X + Wd * 0.08, base], [X + Wd * 0.92, base]], { lw: 5 * SC(), ink: PAL.chalkLine });
    const bars = a.bars || [], max = a.max || Math.max(1, ...bars.map((b) => b.v));
    bars.forEach((b, i) => {
      const a0 = at(info, b.at, 0); if (lt < a0) return; const k = ease.out(clamp((lt - a0) / 0.8));
      const bw = Wd * 0.14, x = X + Wd * (0.2 + i * (0.62 / Math.max(1, bars.length - 1 || 1))) - bw / 2, hh = Hd * 0.58 * (b.v / max) * k;
      g.save(); g.strokeStyle = PAL.chalkLine; g.lineWidth = 5 * SC(); g.strokeRect(x, base - hh, bw, hh); g.beginPath(); g.rect(x, base - hh, bw, hh); g.clip(); g.lineWidth = 3 * SC(); for (let s = -Hd; s < Hd; s += 22 * SC()) { g.beginPath(); g.moveTo(x + s, base); g.lineTo(x + s + hh, base - hh); g.stroke(); } g.restore();
      label(g, b.label, x + bw / 2, base + 44 * SC(), { size: 40 * SC(), color: PAL.chalkLine });
      if (b.top) label(g, b.top, x + bw / 2, base - hh - 40 * SC(), { size: 44 * SC(), color: PAL.chalkLine });
    });
    if (a.curve) { const a0 = at(info, a.curveAt, 0); line(g, a.curve.map(([x, y]) => [X + Wd * x, Y + Hd * y]), { lw: 5 * SC(), ink: '#e98a7a', p: clamp((lt - a0) / 1) }); }
    if (a.mult) { const a0 = at(info, a.mult.at, 0); if (lt >= a0) label(g, a.mult.text, fx(a.mult.x, 0.5), fy(a.mult.y, 0.4), { size: 90 * SC(), color: '#e98a7a', a: clamp((lt - a0) / 0.3) }); }
    overlays(g, lt, info);
  });
  vignette(g, 0.22);
} });
// ======================================================================================= XRAY (man hinh soi xanh)
// args: subject: 'head' | 'body' | 'arm', hit: {x, y, ang} (vi tri vat la, 0..1 trong khung tieu de), label
registerTemplate('xray', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    g.fillStyle = PAL.xray; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3);
    g.save(); g.strokeStyle = 'rgba(126,200,255,0.12)'; g.lineWidth = 2; for (let x = 0; x < E.W; x += 40 * SC()) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, E.H); g.stroke(); } for (let y = 0; y < E.H; y += 40 * SC()) { g.beginPath(); g.moveTo(0, y); g.lineTo(E.W, y); g.stroke(); } g.restore();
    const X = E.W * 0.08, Y = E.H * 0.08, Wd = E.W * 0.84, Hd = E.H * 0.84;
    g.save(); g.strokeStyle = 'rgba(126,200,255,0.6)'; g.lineWidth = 4 * SC(); g.beginPath(); g.roundRect(X, Y, Wd, Hd, 18 * SC()); g.stroke(); g.restore();
    const cx = E.W / 2, cy = E.H * 0.46, R = E.H * (vert() ? 0.15 : 0.22);
    g.save(); g.shadowColor = '#7ec8ff'; g.shadowBlur = 24 * SC(); g.strokeStyle = '#bfe6ff'; g.lineWidth = 5 * SC();
    g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.stroke();
    g.fillStyle = 'rgba(126,200,255,0.22)'; g.fill();
    g.setLineDash([12 * SC(), 10 * SC()]); g.lineWidth = 3 * SC(); g.beginPath(); g.arc(cx, cy - R * 0.05, R * 1.25, Math.PI * 1.05, Math.PI * 1.95); g.stroke(); g.setLineDash([]);
    // co + vai
    g.beginPath(); g.moveTo(cx - R * 0.35, cy + R * 0.95); g.lineTo(cx - R * 0.35, cy + R * 1.6); g.moveTo(cx + R * 0.35, cy + R * 0.95); g.lineTo(cx + R * 0.35, cy + R * 1.6); g.moveTo(cx - R * 1.8, cy + R * 1.9); g.quadraticCurveTo(cx - R * 1.2, cy + R * 1.5, cx - R * 0.35, cy + R * 1.6); g.moveTo(cx + R * 1.8, cy + R * 1.9); g.quadraticCurveTo(cx + R * 1.2, cy + R * 1.5, cx + R * 0.35, cy + R * 1.6); g.stroke();
    // mat (lo rong)
    for (const s of [-1, 1]) { g.beginPath(); g.arc(cx + s * R * 0.4, cy - R * 0.02, R * 0.2, 0, Math.PI * 2); g.stroke(); }
    g.beginPath(); g.moveTo(cx, cy + R * 0.2); g.lineTo(cx - R * 0.08, cy + R * 0.38); g.lineTo(cx + R * 0.08, cy + R * 0.38); g.closePath(); g.stroke();
    g.restore();
    if (a.hit) { const a0 = at(info, a.hit.at, 0); if (lt >= a0) { const k = clamp((lt - a0) / 0.4), hx = cx + (a.hit.dx ?? -0.25) * R, hy = cy + (a.hit.dy ?? 0.25) * R; g.save(); g.translate(hx, hy); g.rotate(a.hit.ang ?? -0.4); g.globalAlpha = k; const gr = g.createRadialGradient(0, 0, 4, 0, 0, R * 0.4); gr.addColorStop(0, 'rgba(255,80,70,0.7)'); gr.addColorStop(1, 'rgba(255,80,70,0)'); g.fillStyle = gr; g.fillRect(-R * 0.5, -R * 0.5, R, R); polyS(g, [[R * 0.22, 0], [-R * 0.08, -R * 0.09], [-R * 0.02, 0], [-R * 0.08, R * 0.09]], { fill: '#ff5b4f', lw: 3 * SC(), ink: '#ffd0c8' }); g.restore(); } }
    if (a.label) label(g, a.label, E.W / 2, Y + Hd * 0.93, { size: 44 * SC(), color: '#bfe6ff' });
    overlays(g, lt, info);
  });
} });
// ======================================================================================= FRAME (vat / nguoi treo tuong, khung tranh)
// args: bg ('castle'|'wood'), thing: {kind, ...} hoac person: {...}, card: true (khung giay vien), arrows, marks
registerTemplate('frame', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    g.fillStyle = '#2c201a'; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3);
    const X = E.W * 0.08, Y = E.H * (vert() ? 0.15 : 0.06), Wd = E.W * 0.84, Hd = E.H * (vert() ? 0.7 : 0.88);
    rect(g, X - 14 * SC(), Y - 14 * SC(), Wd + 28 * SC(), Hd + 28 * SC(), { fill: '#e4d2a6', lw: 6 * SC(), r: 16 * SC() });
    g.save(); g.beginPath(); g.roundRect(X, Y, Wd, Hd, 10 * SC()); g.clip(); g.translate(0, 0);
    bg(g, a.bg || 'castle', { ...(a.bgOpts || {}), t: lt, torch: false, banner: null, window: a.window ?? true, floorY: 0.86 });
    for (const p of a.props || []) prop(g, lt, info, p);
    drawPeople(g, lt, info, a.people, 0.9, vert() ? 0.36 : 0.62);
    g.restore();
    overlays(g, lt, info);
  });
} });
// ======================================================================================= ITEM (can canh do vat tren nen mo)
// args: thing: {kind, s, x, y, ...}, bg, time, bgOpts, blur, spin, hand: true (gang tay cam)
registerTemplate('item', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    blurLayer(g, (a.blur ?? 14) * SC(), (c) => { bg(c, a.bg || 'castle', { time: a.time, ...(a.bgOpts || {}), t: lt }); for (const f of a.back || []) formation(c, { ...f, t: lt }); });
    if (a.tint) haze(g, a.tint[0], a.tint[1]);
    const th = a.thing || { kind: 'shield' };
    prop(g, lt, info, { x: 0.5, y: 0.5, s: vert() ? 0.32 : 0.62, anim: 'none', ...th, rot: (th.rot || 0) + (a.sway ? Math.sin(lt * 1.2) * 0.03 : 0) });
    for (const p of a.props || []) prop(g, lt, info, p);
    drawPeople(g, lt, info, a.people, 0.95, 0.6);
    effects(g, lt, info, a.fx);
    overlays(g, lt, info);
  });
  vignette(g, 0.22);
} });
// ======================================================================================= SPLIT (chia doi cheo, 2 canh)
// args: left: {bg, time, people, props, color}, right: {...}, slant (0..0.2), labels
registerTemplate('split', { draw(g, lt, info) {
  const a = info.args || {}, sl = a.slant ?? 0.08;
  camera(g, lt, info, () => {
    for (const [side, sp] of [['left', a.left || {}], ['right', a.right || {}]]) {
      g.save(); g.beginPath();
      if (side === 'left') { g.moveTo(-10, -10); g.lineTo(E.W * (0.5 + sl), -10); g.lineTo(E.W * (0.5 - sl), E.H + 10); g.lineTo(-10, E.H + 10); }
      else { g.moveTo(E.W * (0.5 + sl), -10); g.lineTo(E.W + 10, -10); g.lineTo(E.W + 10, E.H + 10); g.lineTo(E.W * (0.5 - sl), E.H + 10); }
      g.closePath(); g.clip();
      if (sp.color) { g.fillStyle = sp.color; g.fillRect(-10, -10, E.W + 20, E.H + 20); } else blurLayer(g, 8 * SC(), (c) => bg(c, sp.bg || 'field', { time: sp.time, ...(sp.bgOpts || {}), t: lt }));
      for (const p of sp.props || []) prop(g, lt, info, p);
      drawPeople(g, lt, info, sp.people, 0.95, 0.6);
      g.restore();
    }
    line(g, [[E.W * (0.5 + sl), -10], [E.W * (0.5 - sl), E.H + 10]], { lw: 26 * SC(), ink: OUT }); line(g, [[E.W * (0.5 + sl), -10], [E.W * (0.5 - sl), E.H + 10]], { lw: 16 * SC(), ink: a.divider || '#f4efe4' });
    overlays(g, lt, info);
  });
} });
// ======================================================================================= TITLE / BLACK
registerTemplate('title', { draw(g, lt, info) {
  const a = info.args || {};
  camera(g, lt, info, () => {
    if (a.bg) blurLayer(g, 12 * SC(), (c) => bg(c, a.bg, { time: a.time, ...(a.bgOpts || {}), t: lt })); else { g.fillStyle = a.color || '#2a1f1a'; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3); }
    haze(g, '#000', a.dim ?? 0.25);
    const lines = String(a.text || '').split('\n'), size = (a.size || (vert() ? 120 : 150)) * SC(), k = ease.outBack(clamp(lt / 0.35));
    g.save(); g.translate(E.W / 2, fy(a.y, 0.45)); g.scale(k, k);
    lines.forEach((l, i) => { const y = (i - (lines.length - 1) / 2) * size * 1.05; text(g, l.toUpperCase(), size * 0.05, y + size * 0.1, { size, font: FONT_THUMB, weight: 400, color: OUT, stroke: size * 0.26, strokeColor: OUT }); text(g, l.toUpperCase(), 0, y, { size, font: FONT_THUMB, weight: 400, color: a.textColor || '#fff', stroke: size * 0.2, strokeColor: OUT }); text(g, l.toUpperCase(), 0, y, { size, font: FONT_THUMB, weight: 400, color: a.textColor || '#fff' }); });
    g.restore();
    if (a.sub) label(g, a.sub, E.W / 2, fy(a.y, 0.45) + size * (lines.length * 0.55 + 0.5), { size: 48 * SC(), color: '#f4efe4', a: clamp((lt - 0.3) / 0.3) });
    overlays(g, lt, info);
  });
} });
registerTemplate('black', { draw(g, lt, info) { g.fillStyle = (info.args || {}).color || '#000'; g.fillRect(-E.W, -E.H, E.W * 3, E.H * 3); overlays(g, lt, info); } });
