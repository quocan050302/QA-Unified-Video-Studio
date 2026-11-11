// world.js — phong nen doodle phang. bg(g, kieu, opts). Kieu: paper white sky desert forest jungle cave room lab classroom
//            beach river table night field village hill
// opts.groundY (0..1 chieu cao), opts.color doi mau chu dao, opts.t thoi gian (may troi), opts.seed
import { E, rng, lerp } from '/engine/core.js';
import { INK, PAL, rect, poly, blob, line, circ, ellipse, shape, smoothPath } from './ink.js';
import { prop } from './props.js';

const W = () => E.W, H = () => E.H;
function flat(g, c) { g.fillStyle = c; g.fillRect(-40, -40, W() + 80, H() + 80); }
function ground(g, y, c, lw = 6) { shape(g, (x) => { x.moveTo(-40, y); x.lineTo(W() + 40, y); x.lineTo(W() + 40, H() + 40); x.lineTo(-40, H() + 40); x.closePath(); }, { fill: c, lw }); }
function hills(g, y, c, amp, seed, lw = 5) { const r = rng(seed); const pts = [[-60, y + 200]]; for (let i = 0; i <= 8; i++) pts.push([-60 + i * (W() + 120) / 8, y - r() * amp]); pts.push([W() + 60, y + 200]); blob(g, pts, { fill: c, lw }); }
function clouds(g, t = 0, n = 3, seed = 3) { const r = rng(seed); for (let i = 0; i < n; i++) { const x = ((r() * W() + t * 12 * (0.5 + r())) % (W() + 300)) - 150, y = 70 + r() * 180; prop(g, 'cloud', x, y, 120 + r() * 80); } }
function texture(g, seed = 1, a = 0.05) { const r = rng(seed); g.save(); g.globalAlpha = a; g.strokeStyle = INK; g.lineWidth = 2; for (let i = 0; i < 70; i++) { const x = r() * W(), y = r() * H(); g.beginPath(); g.moveTo(x, y); g.lineTo(x + 8 + r() * 14, y + (r() - 0.5) * 4); g.stroke(); } g.restore(); }

export function bg(g, kind = 'paper', o = {}) {
  const t = o.t || 0, gy = H() * (o.groundY ?? 0.78), s = o.seed || 1;
  switch (kind) {
    case 'white': flat(g, '#ffffff'); break;
    case 'paper': flat(g, o.color || PAL.paper); texture(g, s, 0.035); break;
    case 'sky': flat(g, o.color || PAL.sky); clouds(g, t, 3, s); if (o.hills !== false) hills(g, gy - 10, PAL.sage, 70, s + 2); ground(g, gy, o.ground || PAL.grass); break;
    case 'hill': flat(g, o.color || PAL.sky); clouds(g, t, 2, s); hills(g, gy - 60, '#b9cf9a', 140, s + 5); hills(g, gy, PAL.sage, 60, s + 9); ground(g, gy + 40, o.ground || PAL.grass); break;
    case 'field': flat(g, o.color || PAL.sky); clouds(g, t, 2, s); hills(g, gy - 30, '#b9cf9a', 80, s + 4); ground(g, gy - 20, '#bfd68f'); for (let i = 0; i < 9; i++) line(g, [[-40, gy + i * 30], [W() + 40, gy + i * 30 + 6]], { lw: 3, ink: '#8fae62' }); break;
    case 'desert': flat(g, o.color || '#f6d9a0'); prop(g, 'sun', W() * 0.82, H() * 0.18, 150); poly(g, [[-40, gy], [W() * 0.05, H() * 0.42], [W() * 0.22, H() * 0.38], [W() * 0.3, gy]], { fill: '#d98b5a', lw: 6 }); poly(g, [[W() * 0.7, gy], [W() * 0.78, H() * 0.4], [W() * 0.98, H() * 0.36], [W() + 40, gy]], { fill: '#cf7e50', lw: 6 }); ground(g, gy, o.ground || '#e8b77a'); break;
    case 'forest': flat(g, o.color || '#f4ead2'); ground(g, gy, o.ground || '#c9a46c'); { const r = rng(s); for (let i = 0; i < 7; i++) prop(g, 'tree', 80 + i * (W() - 160) / 6 + (r() - 0.5) * 60, gy - 150 - r() * 30, 420 + r() * 80); } break;
    case 'jungle': flat(g, o.color || '#f7dfb6'); hills(g, gy - 40, '#a9c48a', 160, s + 1); ground(g, gy, o.ground || '#e9cf98'); { const r = rng(s + 3); for (let i = 0; i < 5; i++) prop(g, 'palm', 100 + i * (W() - 200) / 4 + (r() - 0.5) * 120, gy - 170, 380 + r() * 120); } break;
    case 'beach': flat(g, o.color || '#ffe0b5'); prop(g, 'sun', W() * 0.8, H() * 0.42, 220); shape(g, (x) => { x.rect(-40, H() * 0.48, W() + 80, H()); }, { fill: PAL.sea, lw: 0 }); line(g, [[-40, H() * 0.48], [W() + 40, H() * 0.48]], { lw: 5 }); shape(g, (x) => { smoothPath(x, [[-40, H() * 0.66], [W() * 0.3, H() * 0.6], [W() * 0.6, H() * 0.68], [W() + 40, H() * 0.62]]); x.lineTo(W() + 40, H() + 40); x.lineTo(-40, H() + 40); x.closePath(); }, { fill: '#f0d49c', lw: 6 }); break;
    case 'river': flat(g, o.color || '#e9d6a6'); { const pts = [[-40, H() * 0.15], [W() * 0.25, H() * 0.35], [W() * 0.45, H() * 0.2], [W() * 0.65, H() * 0.55], [W() * 0.85, H() * 0.5], [W() + 40, H() * 0.8]]; line(g, pts, { lw: 120, ink: INK }); line(g, pts, { lw: 108, ink: PAL.sea }); } texture(g, s, 0.04); break;
    case 'cave': flat(g, o.color || '#5a4434'); shape(g, (x) => { x.moveTo(W() * 0.08, H() + 40); x.lineTo(W() * 0.1, H() * 0.35); x.quadraticCurveTo(W() * 0.5, -H() * 0.12, W() * 0.9, H() * 0.35); x.lineTo(W() * 0.92, H() + 40); x.closePath(); }, { fill: '#8a6a50', lw: 7 }); ground(g, gy, '#6d523d'); if (o.fire) prop(g, 'fire', W() * 0.5, gy - 30, 140, { t }); break;
    case 'night': flat(g, o.color || '#27345a'); { const r = rng(s); for (let i = 0; i < 60; i++) circ(g, r() * W(), r() * H() * 0.6, 2 + r() * 3, { fill: '#fff6d0', lw: 0 }); } prop(g, 'moon', W() * 0.82, H() * 0.18, 140); hills(g, gy, '#3c4a6e', 60, s + 6); ground(g, gy + 30, '#2e3a58'); break;
    case 'room': case 'lab': case 'classroom': {
      flat(g, o.color || (kind === 'lab' ? '#cfe6d8' : '#f6ead5'));
      ground(g, gy, o.ground || (kind === 'lab' ? '#d9d2c3' : '#c99f6c'));
      rect(g, W() * 0.08, H() * 0.16, W() * 0.18, H() * 0.32, { fill: '#bfe2ef', lw: 7, r: 4 }); line(g, [[W() * 0.17, H() * 0.16], [W() * 0.17, H() * 0.48]], { lw: 5 });
      if (kind === 'classroom') { rect(g, W() * 0.32, H() * 0.12, W() * 0.4, H() * 0.3, { fill: '#3f6150', lw: 7, r: 6 }); }
      if (kind === 'lab') { rect(g, W() * 0.66, H() * 0.5, W() * 0.3, H() * 0.06, { fill: PAL.wood, lw: 6, r: 3 }); prop(g, 'flask', W() * 0.72, H() * 0.44, 110); prop(g, 'flask', W() * 0.8, H() * 0.44, 90, { color: '#e59a9a' }); prop(g, 'flask', W() * 0.88, H() * 0.45, 100, { color: '#f0d27a' }); }
      if (kind === 'room') { rect(g, W() * 0.78, H() * 0.18, W() * 0.12, H() * 0.18, { fill: '#fffaf0', lw: 6, r: 3 }); shape(g, (x) => { x.moveTo(W() * 0.86, gy); x.lineTo(W() * 0.84, gy - 70); x.lineTo(W() * 0.92, gy - 70); x.lineTo(W() * 0.9, gy); x.closePath(); }, { fill: PAL.terracotta, lw: 5 }); [[-0.04, -0.2], [0, -0.26], [0.04, -0.2]].forEach(([a, b]) => prop(g, 'leaf', W() * (0.88 + a), gy - 70 + b * 300, 90, { rot: a * 12 })); }
      break; }
    case 'table': flat(g, o.color || '#a87448'); { const r = rng(s); for (let i = 0; i < 14; i++) { const y = r() * H(); line(g, [[-20, y], [W() * 0.3, y + 10], [W() * 0.7, y - 6], [W() + 20, y + 4]], { lw: 3, ink: 'rgba(60,35,15,0.35)' }); } } break;
    case 'village': flat(g, o.color || PAL.sky); clouds(g, t, 2, s); hills(g, gy - 20, '#b9cf9a', 90, s + 2); ground(g, gy, o.ground || '#c9d48f'); prop(g, 'bamboo', W() * 0.08, gy - 160, 340); prop(g, 'hut', W() * 0.3, gy - 110, 260); prop(g, 'hut', W() * 0.72, gy - 100, 230); prop(g, 'bamboo', W() * 0.93, gy - 150, 320); break;
    default: flat(g, o.color || PAL.paper);
  }
}
export { flat, ground, hills, clouds, texture };
