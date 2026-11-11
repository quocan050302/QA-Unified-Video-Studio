// pack.js — bo phong cach "squire": hoat hinh vector lich su quan su (kieu kenh giai thich chien tranh, hiep si, La Ma, samurai, the chien).
// Nhan vat dau tron trang vien nau den, trang phuc theo thoi dai, ngua, doi hinh dong nguoi, so do nhin tu tren, ban do giay da,
// nen mo sau kieu may anh. Video dai 16:9 khong phu de; Short 9:16 phu de 1-3 chu IN HOA trang vien den.
// config.json: "pack": "squire", "lang": "en", "captions": true|false, "format": "long" | "short"
import { E, registerShot, text, measure, blurLayer } from '/engine/core.js';
import { OUT, PAL, FONT_THUMB, FONT_CAP, ban, qmark, blockArrow, haze, alpha, shape, polyS, rect, label } from './ink.js';
import { soldier, bust, CAST } from './chara.js';
import { bg } from './world.js';
import { formation } from './army.js';
import { drawThing, loadWorld } from './templates.js';
export * from './ink.js';
export * from './chara.js';
export * from './world.js';
export * from './horse.js';
export * from './army.js';
export * from './templates.js';
export { E } from '/engine/core.js';

function css(href) { return new Promise((r) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; l.onload = r; l.onerror = r; document.head.appendChild(l); }); }
export async function init(E) {
  await Promise.all(['/node_modules/@fontsource/patrick-hand/400.css', '/node_modules/@fontsource/luckiest-guy/400.css', '/node_modules/@fontsource/be-vietnam-pro/800.css', '/node_modules/@fontsource/be-vietnam-pro/900.css'].map(css));
  await Promise.all([document.fonts.load('400 40px "Patrick Hand"', 'ENGLISH ARCHERS'), document.fonts.load(`400 40px ${FONT_THUMB}`, 'USELESS?!'), document.fonts.load(`800 40px ${FONT_CAP}`, 'THE KNIGHT'), document.fonts.load(`900 40px ${FONT_CAP}`, 'THE KNIGHT')]);
  if (!E.cfg.style || E.cfg.style === 'dusk') E.cfg.style = 'flat';
  if (E.cfg.bars === null || E.cfg.bars === undefined) E.cfg.bars = 'none';
  if (E.cfg.captions === undefined || E.cfg.captions === null) E.cfg.captions = E.vertical;
  if (!E.cfg.captionStyle) E.cfg.captionStyle = 'squire';
  if (E.shots.some((s) => s.tpl === 'map')) await loadWorld(); else await loadWorld().catch(() => {});
}

// ---------- phu de Short: 1-3 chu IN HOA trang sieu dam, vien den, bong; chu dang doc to hon chut
export function captions(g, ws, idx, t, style) {
  const N = E.vertical ? 3 : 6; const groups = []; let cur = [];
  ws.forEach((w, i) => { cur.push(i); if (cur.length >= N || (/[,.!?;:…]$/.test(w.w) && cur.length >= 1)) { groups.push(cur); cur = []; } });
  if (cur.length) groups.push(cur);
  const grp = groups.find((gp) => gp.includes(idx)) || groups[groups.length - 1];
  const words = grp.map((i) => ws[i].w.replace(/[“”"]/g, '').toUpperCase());
  const size = E.vertical ? 64 : 52, y = E.H * (E.vertical ? 0.665 : 0.9), gap = size * 0.32;
  const ws2 = words.map((w, k) => measure(g, w, grp[k] === idx ? size * 1.08 : size, FONT_CAP, 900));
  let total = ws2.reduce((a, b) => a + b, 0) + gap * (words.length - 1);
  const maxW = E.W * 0.86, sc = total > maxW ? maxW / total : 1; total *= sc;
  let x = E.W / 2 - total / 2;
  words.forEach((w, k) => {
    const s = (grp[k] === idx ? size * 1.08 : size) * sc, ww = ws2[k] * sc;
    text(g, w, x + ww / 2 + s * 0.04, y + s * 0.07, { size: s, font: FONT_CAP, weight: 900, color: alpha('#000', 0.55), stroke: s * 0.2, strokeColor: alpha('#000', 0.55) });
    text(g, w, x + ww / 2, y, { size: s, font: FONT_CAP, weight: 900, color: '#ffffff', stroke: s * 0.17, strokeColor: '#1a1210' });
    text(g, w, x + ww / 2, y, { size: s, font: FONT_CAP, weight: 900, color: '#ffffff' });
    x += ww + gap * sc;
  });
}

// ---------- thumbnail (video dai): nen canh mo + 1-2 nhan vat lon + 1 ky hieu do + 1-3 chu trang vien den
// thumb({ bg, time, bgOpts, back: [doi hinh], hero: {preset, face, x, y, R, ...} | heroes: [...], symbols: [{kind:'ban'|'arrow'|'q'|'!'|'vs'|thing...}],
//         title: 'USELESS.' | ['DON\'T', 'BREAK IN'], tx, ty, tsize, tcolor, align, split: { left, right, slant } })
export function titleText(g, str, x, y, size, o = {}) {
  const s = String(str).toUpperCase(), col = o.color || '#ffffff';
  g.save(); g.translate(x, y); g.rotate(o.rot || 0);
  const al = o.align || 'center';
  text(g, s, size * 0.06, size * 0.11, { size, font: FONT_THUMB, weight: 400, color: '#120c0a', stroke: size * 0.3, strokeColor: '#120c0a', align: al });
  text(g, s, 0, 0, { size, font: FONT_THUMB, weight: 400, color: col, stroke: size * 0.24, strokeColor: '#120c0a', align: al });
  text(g, s, 0, 0, { size, font: FONT_THUMB, weight: 400, color: col, align: al });
  g.restore();
}
function vsBurst(g, x, y, r) {
  const pts = []; for (let i = 0; i < 16; i++) { const a = i * Math.PI / 8, rr = i % 2 ? r * 0.62 : r; pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]); }
  polyS(g, pts, { fill: PAL.yellow, lw: r * 0.06 }); polyS(g, pts.map(([a, b]) => [x + (a - x) * 0.72, y + (b - y) * 0.72]), { fill: '#e7473c', lw: r * 0.04 });
  titleText(g, 'VS', x, y + r * 0.05, r * 0.7, { rot: -0.08 });
}
export function thumb(o = {}) {
  registerShot('thumb', { draw(g, t) {
    const tt = 1.3;
    if (o.split) {
      const sl = o.split.slant ?? 0.06;
      for (const [side, c] of [['l', o.split.left || '#c9473a'], ['r', o.split.right || '#9fb3c4']]) { g.save(); g.beginPath(); if (side === 'l') { g.moveTo(-10, -10); g.lineTo(E.W * (0.5 + sl), -10); g.lineTo(E.W * (0.5 - sl), E.H + 10); g.lineTo(-10, E.H + 10); } else { g.moveTo(E.W * (0.5 + sl), -10); g.lineTo(E.W + 10, -10); g.lineTo(E.W + 10, E.H + 10); g.lineTo(E.W * (0.5 - sl), E.H + 10); } g.closePath(); g.clip(); if (typeof c === 'string') { g.fillStyle = c; g.fillRect(-10, -10, E.W + 20, E.H + 20); } else blurLayer(g, 9, (cc) => bg(cc, c.bg || 'field', { time: c.time, ...(c.bgOpts || {}) })); g.restore(); }
      g.save(); g.lineWidth = 30; g.strokeStyle = '#120c0a'; g.beginPath(); g.moveTo(E.W * (0.5 + sl), -10); g.lineTo(E.W * (0.5 - sl), E.H + 10); g.stroke(); g.lineWidth = 18; g.strokeStyle = '#f4efe4'; g.stroke(); g.restore();
    } else {
      blurLayer(g, o.blur ?? 9, (c) => { bg(c, o.bg || 'field', { time: o.time, seed: o.seed, ...(o.bgOpts || {}), t: tt }); for (const f of o.back || []) formation(c, { lodH: 120, ...f, t: tt }); });
      haze(g, '#ffffff', o.wash ?? 0.06);
    }
    for (const f of o.mid || []) formation(g, { ...f, t: tt });
    for (const s of o.symbols || []) {
      const x = s.x * E.W, y = s.y * E.H, r = (s.r || 0.2) * E.H;
      if (s.kind === 'ban') { if (s.thing) drawThing(g, s.thing.kind, x, y, r * 1.7, { ...s.thing, t: tt }); ban(g, x, y, r, { lw: r * 0.2 }); }
      else if (s.kind === 'arrow') blockArrow(g, x, y, s.to[0] * E.W, s.to[1] * E.H, { w: r * 0.35, fill: s.color || '#e0352f', lw: 7 });
      else if (s.kind === 'q' || s.kind === '!') { if (s.glow !== false) { const gr = g.createRadialGradient(x, y, r * 0.2, x, y, r * 1.8); gr.addColorStop(0, 'rgba(220,40,35,0.55)'); gr.addColorStop(1, 'rgba(220,40,35,0)'); g.fillStyle = gr; g.fillRect(x - r * 2, y - r * 2, r * 4, r * 4); } qmark(g, x, y, r * 2.2, { ch: s.kind === 'q' ? '?' : '!', color: s.color || '#e0352f' }); }
      else if (s.kind === 'vs') vsBurst(g, x, y, r);
      else if (s.kind === 'eyes') { for (const k of [-1, 1]) { g.fillStyle = '#fff'; g.beginPath(); g.ellipse(x + k * r * 0.25, y, r * 0.12, r * 0.09, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = OUT; g.beginPath(); g.arc(x + k * r * 0.25, y, r * 0.05, 0, Math.PI * 2); g.fill(); } }
      else drawThing(g, s.kind, x, y, r, { ...s, t: tt });
    }
    const heroes = o.heroes || (o.hero ? [o.hero] : []);
    for (const h of heroes) { if (h.full) soldier(g, h.x * E.W, h.y * E.H, h.h * E.H, { ...h, t: tt, lod: 'high' }); else bust(g, (h.x ?? 0.72) * E.W, (h.y ?? 0.5) * E.H, (h.R ?? 0.2) * E.H, { ...h, t: tt }); }
    for (const s of o.overSymbols || []) { const x = s.x * E.W, y = s.y * E.H, r = (s.r || 0.2) * E.H; if (s.kind === 'ban') ban(g, x, y, r, { lw: r * 0.2 }); else if (s.kind === 'vs') vsBurst(g, x, y, r); else if (s.kind === 'q') qmark(g, x, y, r * 2.2, { color: s.color || '#e0352f' }); else if (s.kind === 'arrow') blockArrow(g, x, y, s.to[0] * E.W, s.to[1] * E.H, { w: r * 0.35, fill: s.color || '#e0352f', lw: 7 }); }
    const lines = Array.isArray(o.title) ? o.title : o.title ? [o.title] : [];
    const size = (o.tsize || 0.2) * E.H;
    lines.forEach((l, i) => { const ln = typeof l === 'string' ? { text: l } : l; titleText(g, ln.text, (ln.x ?? o.tx ?? 0.3) * E.W, (ln.y ?? ((o.ty ?? 0.16) + i * (o.tgap ?? 0.19))) * E.H, (ln.size || o.tsize || 0.2) * E.H, { color: ln.color || o.tcolor, rot: ln.rot ?? o.trot ?? -0.02, align: o.align }); });
  } });
}
