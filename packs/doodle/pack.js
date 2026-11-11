// pack.js — bo phong cach "doodle": minh hoa phang vien den day, mau pastel am, chu viet tay (kieu kenh giai thich "Vi sao...").
// Player goi init() khi config.json co "pack": "doodle". Canh trong du an import truc tiep tu /packs/doodle/*.js
import { E, registerShot, img, text } from '/engine/core.js';
import { loadWorld } from './map.js';
import { INK, PAL, FONT_HAND, FONT_BOLD, FONT_BODY, cover, wrap, label } from './ink.js';
import './templates.js';
export * from './ink.js';
export * from './host.js';
export * from './props.js';
export * from './world.js';
export * from './map.js';
export * from './templates.js';
export * from './sketch.js';
import { caveman, thumbTitle, savanna } from './sketch.js';
export { img, E } from '/engine/core.js';

function css(href) { return new Promise((r) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; l.onload = r; l.onerror = r; document.head.appendChild(l); }); }
export async function init(E) {
  await css('/node_modules/@fontsource/patrick-hand/400.css');
  await Promise.all([document.fonts.load(`400 40px ${FONT_HAND}`, 'Việt Nam ĐẶT HÀNG'), document.fonts.load(`800 40px ${FONT_BOLD}`, 'Việt ĐĂNG KÝ'), document.fonts.load(`700 40px ${FONT_BODY}`, 'Việt')]);
  // mac dinh cua ngach: khong dai den, khong chinh mau, phu de vang
  if (!E.cfg.style || E.cfg.style === 'dusk') E.cfg.style = 'flat';
  if (E.cfg.bars === null || E.cfg.bars === undefined) E.cfg.bars = 'none';
  if (!E.cfg.captionStyle) E.cfg.captionStyle = 'doodle';
  if (E.shots.some((s) => s.tpl === 'map') || E.cfg.map) await loadWorld();
  else await loadWorld().catch(() => {});
}
// phu de: ca cau ngan (toi da ~9 chu), chu vang vien toi, chu dang doc sang hon
export function captions(g, ws, idx, t, style) {
  const N = E.vertical ? 5 : 9; let st = 0;
  // tach nhom theo dau cau / so chu
  const groups = []; let cur = [];
  ws.forEach((w, i) => { cur.push(i); if (cur.length >= N || /[,.!?;:…]$/.test(w.w) && cur.length >= 3) { groups.push(cur); cur = []; } });
  if (cur.length) groups.push(cur);
  const grp = groups.find((gp) => gp.includes(idx)) || groups[groups.length - 1];
  const words = grp.map((i) => ws[i].w.replace(/[“”"]/g, ''));
  const size = E.vertical ? 62 : 46, y = E.H * (E.vertical ? 0.78 : 0.93);
  text(g, words.join(' '), E.W / 2, y, { size, font: FONT_BODY, weight: 700, color: '#ffd84a', stroke: size * 0.22, strokeColor: '#2a2016' });
}
// thumbnail kieu kenh "Vi sao": anh nen AI (canh + con vat, KHONG co nguoi, KHONG chu) + nguoi tien su ve bang code + chu vang vien den.
//   import { thumb } from '/packs/doodle/pack.js';
//   thumb({ img: 'T01', title: 'ĐỌ SAO NỔI?', people: [{ x: 0.2, face: 'scream', pose: 'hold-head' }, { x: 0.36, face: 'shock', pose: 'point', look: 1 }] })
// people[]: x, y (chan, mac dinh 1.12 = cat bot chan nhu kenh mau), h (mac dinh 0.86), face: scream|shock|cry|squint|grin|worried|angry, pose: point|hands-up|hold-head|hug|spear|flee|down,
//           look (-1..1 huong mat), flip, mark ('!' '?' '!?'), sweat (false de tat), seed (doi net ve)
// Chua co anh nen thi tu ve thao nguyen bang code.
export function thumb(o = {}) {
  registerShot('thumb', {
    images: o.img ? [o.img] : [],
    draw(g) {
      const im = img(o.img);
      if (im) cover(g, im, 0, 0, E.W, E.H, { z: o.crop ?? 1.04, fx: o.focus?.[0] ?? 0.5, fy: o.focus?.[1] ?? 0.5 }); else savanna(g, { treeX: o.treeX });
      if (o.draw) o.draw(g);
      for (const [i, p] of (o.people || []).entries()) caveman(g, (p.x ?? 0.25) * E.W, (p.y ?? 1.12) * E.H, (p.h ?? 0.86) * E.H, { seed: i + 1, ...p });
    },
    overlay(g) {
      const lines = o.title ? [o.title] : (o.lines || []);
      lines.forEach((l, i) => thumbTitle(g, l, E.W * (o.x ?? 0.5), E.H * ((o.y ?? 0.16) + i * 0.2), { size: o.size || 200, arc: o.arc, rot: o.rot, color: (o.colors || [])[i] }));
    },
  });
}
