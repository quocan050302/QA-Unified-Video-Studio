// thumb.js — thumbnail: anh AI liền khối (T01: nhan vat + vat chinh + nen, KHONG chu) + chu tieu de trang rat dam, vien den, bong do, nam tren cung.
//   import { thumb } from '/packs/dem/pack.js';
//   thumb({ img: 'T01', title: 'WAKE UP.' })
//   thumb({ img: 'T01', lines: ['JUST ONE', 'MORE.'], accent: ['MORE.'] })      // tu doi mau nhan
//   thumb({ img: 'T01', title: 'DAY 600 0.', strike: '600', accent: ['0.'] })   // gach xoa so
// Tuy chon: y (0..1, mac dinh 0.16), size (px, mac dinh tu co theo be ngang), arc (do cong), rot, focus [x, y], crop, align ('center' | 'left')
// Chua co anh: tu ve canh mau bang code (nhan vat + giong noi) de xem bo cuc.
import { E, registerShot, img, text, measure, alpha, radGrad } from '/engine/core.js';
import { PAL, accent, FONT_THUMB, light, fillAll, vignette } from './ink.js';
import { bean } from './bean.js';
import { set } from './sets.js';

function cover(g, im, x, y, w, h, o = {}) {
  const z = o.z ?? 1, s = Math.max(w / im.width, h / im.height) * z, iw = im.width * s, ih = im.height * s;
  g.drawImage(im, x + (w - iw) * (o.fx ?? 0.5), y + (h - ih) * (o.fy ?? 0.5), iw, ih);
}
export function thumbTitle(g, str, x, y, o = {}) {
  const maxW = E.W * (o.maxW ?? 0.9); let size = o.size || 230; while (measure(g, str, size, FONT_THUMB, 400) > maxW && size > 60) size -= 6;
  const words = str.split(' '), acc = new Set(o.accent || []), sp = measure(g, ' ', size, FONT_THUMB, 400), tot = measure(g, str, size, FONT_THUMB, 400);
  let cx = o.align === 'left' ? x : x - tot / 2;
  g.save(); g.translate(0, 0);
  for (const w of words) {
    const ww = measure(g, w, size, FONT_THUMB, 400), mid = cx + ww / 2, dy = o.arc ? -Math.cos(((mid - x) / (tot / 2 + 1)) * 1.2) * o.arc * size * 0.25 : 0, rot = o.arc ? ((mid - x) / tot) * o.arc * 0.25 : 0;
    g.save(); g.translate(mid, y + dy); g.rotate((o.rot || 0) + rot);
    g.save(); g.shadowColor = 'rgba(0,0,0,0.85)'; g.shadowBlur = size * 0.12; g.shadowOffsetY = size * 0.06;
    text(g, w, 0, 0, { size, font: FONT_THUMB, weight: 400, color: '#000', stroke: size * 0.16, strokeColor: '#000' }); g.restore();
    text(g, w, 0, 0, { size, font: FONT_THUMB, weight: 400, color: acc.has(w) ? (o.accentColor || accent()) : '#ffffff' });
    if (o.strike && w.replace(/[^\w]/g, '') === String(o.strike)) { g.save(); g.strokeStyle = o.accentColor || accent(); g.lineWidth = size * 0.09; g.lineCap = 'round'; g.beginPath(); g.moveTo(-ww * 0.55, size * 0.05); g.lineTo(ww * 0.55, -size * 0.1); g.stroke(); g.restore(); }
    g.restore(); cx += ww + sp;
  }
  g.restore();
}
export function thumb(o = {}) {
  registerShot('thumb', {
    images: o.img ? [o.img] : [],
    draw(g) {
      const im = img(o.img);
      if (im) cover(g, im, 0, 0, E.W, E.H, { z: o.crop ?? 1.0, fx: o.focus?.[0] ?? 0.5, fy: o.focus?.[1] ?? 0.5 });
      else { // canh mau bang code (chi de xem bo cuc khi chua co anh AI)
        set(g, o.set || 'bedroom', { clock: o.clock ?? '3:17', calendar: false, desk: false, sky: 'moon' }); fillAll(g, 'rgba(0,0,0,0.35)');
        light(g, E.W * 0.55, E.H * 0.7, E.H * 0.6, o.glow || accent(), 0.3);
        bean(g, E.W * 0.7, E.H * 1.05, E.H * 0.95, { who: 'voice', pose: 'reach', face: 'grin', facing: -1, t: 1, glow: accent() });
        bean(g, E.W * 0.45, E.H * 1.45, E.H * 1.35, { who: o.who || 'hoodie', pose: 'phone', hold: 'phone', screen: accent(), face: o.face || 'scared', look: -0.3, t: 0.5, glowFace: accent() });
      }
      if (o.draw) o.draw(g);
    },
    overlay(g) {
      const lines = o.title ? [o.title] : (o.lines || []);
      lines.forEach((l, i) => thumbTitle(g, l, o.align === 'left' ? E.W * (o.x ?? 0.04) : E.W * (o.x ?? 0.5), E.H * ((o.y ?? 0.16) + i * 0.19), { size: o.size, arc: o.arc, rot: o.rot, accent: o.accent, strike: o.strike, align: o.align, accentColor: o.accentColor }));
    },
  });
}
