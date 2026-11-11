// phone.js — can canh: dien thoai (feed, reel, chat, email, man khoa, tat, bo dem), dong ho bao thuc to, so tay viet chu.
import { E, clamp, lerp, ease, rng, noise, alpha, shade, text, measure, radGrad } from '/engine/core.js';
import { PAL, accent, box, oval, ln, light, FONT_UI, FONT_HAND, FONT_NARR, wrap } from './ink.js';
import { bigHand } from './bean.js';
import { postArt, ARTS } from './art.js';

const UIF = '"Be Vietnam Pro"';
function rr(g, x, y, w, h, r, fill) { g.beginPath(); g.roundRect(x, y, w, h, r); g.fillStyle = fill; g.fill(); }
const fmt = (s) => { s = Math.max(0, Math.floor(s)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(x).padStart(2, '0'); };

// phone(g, cx, cy, h, o): o.screen = feed | reel | chat | email | lock | off | counter ; o.t = giay trong canh
export function phone(g, cx, cy, h, o = {}) {
  const w = h * 0.49, x = cx - w / 2, y = cy - h / 2, t = o.t || 0, s = h / 1000;
  light(g, cx, cy, h * 0.9, o.glowColor || (o.screen === 'reel' ? accent() : PAL.screen), o.screen === 'off' ? 0 : 0.18);
  rr(g, x - 14 * s, y - 14 * s, w + 28 * s, h + 28 * s, 70 * s, '#0e0f12'); g.lineWidth = 3 * s; g.strokeStyle = '#5b5e66'; g.stroke();
  g.save(); g.beginPath(); g.roundRect(x, y, w, h, 56 * s); g.clip();
  const sc = o.screen || 'feed', U = s;
  g.fillStyle = sc === 'chat' || sc === 'email' ? '#121317' : '#0b0b0e'; g.fillRect(x, y, w, h);
  const status = (col = '#e8e8ea') => { text(g, o.clock || '23:41', x + 70 * U, y + 52 * U, { size: 30 * U, font: UIF, weight: 700, color: col }); rr(g, x + w - 110 * U, y + 40 * U, 60 * U, 24 * U, 6 * U, alpha(col, 0.8)); };
  if (sc === 'feed' && o.style === 'blocks') {
    status(); const off = (t * (o.scroll ?? 220)) % (h * 0.62);
    const cols = o.colors || ['#ff4f8a', '#7a4dff', '#ff8a3d', '#3dc6ff', '#ff3d6b', '#c94dff'];
    for (let i = -1; i < 4; i++) {
      const cy0 = y + 110 * U + i * h * 0.62 - off; rr(g, x + 24 * U, cy0, w - 48 * U, h * 0.5, 22 * U, '#1d1e24');
      const c = cols[(i + 10 + Math.floor((t * (o.scroll ?? 220)) / (h * 0.62))) % cols.length];
      g.fillStyle = c; g.fillRect(x + 24 * U, cy0 + 60 * U, w - 48 * U, h * 0.36);
    }
  } else if (sc === 'feed') {
    // moi lan 1 bai dang (minh hoa phang), giu "hold" giay roi vuot len; posts = ['ramen', 'car', ...]
    const posts = o.posts && o.posts.length ? o.posts : ['ramen', 'car', 'burger', 'beach', 'watch', 'game'];
    const hold = o.hold ?? 1.1, sw = Math.min(0.3, hold * 0.4), per = hold + sw, k = Math.max(0, t) / per, n = Math.floor(k), f = k - n, slide = f < hold / per ? 0 : (f - hold / per) / (sw / per);
    const off = -(n + (slide < 1 ? slide * slide * (3 - 2 * slide) : 1)) * h;
    const avc = ['#e0875a', '#5a7fe0', '#5ac08a', '#c05ab0', '#e0c05a', '#5ab8e0'];
    for (let i = Math.max(0, n - 1); i <= n + 1; i++) {
      const yy = y + i * h + off, kind = posts[i % posts.length];
      if (yy > y + h || yy + h < y) continue;
      oval(g, x + 62 * U, yy + 220 * U, 32 * U, 32 * U, { fill: avc[i % avc.length], line: null }); rr(g, x + 110 * U, yy + 208 * U, 230 * U, 24 * U, 12 * U, '#4a4d57'); text(g, '•••', x + w - 70 * U, yy + 220 * U, { size: 36 * U, font: UIF, weight: 700, color: '#ddd' });
      postArt(g, kind, x, yy + 275 * U, w, w * 1.05, t, o);
      const iy = yy + 275 * U + w * 1.05 + 60 * U; g.lineWidth = 4 * U; g.strokeStyle = '#eee';
      g.beginPath(); const hx = x + 60 * U; g.moveTo(hx, iy + 14 * U); g.bezierCurveTo(hx - 30 * U, iy - 10 * U, hx - 16 * U, iy - 34 * U, hx, iy - 16 * U); g.bezierCurveTo(hx + 16 * U, iy - 34 * U, hx + 30 * U, iy - 10 * U, hx, iy + 14 * U); g.stroke();
      g.beginPath(); g.arc(x + 140 * U, iy - 6 * U, 22 * U, 0.6, Math.PI * 2.35); g.lineTo(x + 118 * U, iy + 20 * U); g.closePath(); g.stroke();
    }
    g.fillStyle = '#0b0b0e'; g.fillRect(x, y, w, 150 * U); status(); rr(g, x + w / 2 - 110 * U, y + 110 * U, 220 * U, 28 * U, 14 * U, '#555864'); text(g, '•••', x + w - 70 * U, y + 120 * U, { size: 36 * U, font: UIF, weight: 700, color: '#eee' });
  } else if (sc === 'reel') {
    const c = o.color || accent();
    if (o.art) { g.fillStyle = '#000'; g.fillRect(x, y, w, h); postArt(g, o.art, x, y + h * 0.25, w, w * 1.0, t, o); }
    else { const gr = g.createRadialGradient(x + w / 2, y + h * 0.45, 0, x + w / 2, y + h * 0.45, h * 0.6); gr.addColorStop(0, alpha(c, 0.85)); gr.addColorStop(1, '#100810'); g.fillStyle = gr; g.fillRect(x, y, w, h);
    g.save(); g.globalAlpha = 0.35 + 0.1 * Math.sin(t * 3); oval(g, x + w / 2, y + h * 0.42 + Math.sin(t * 2) * 10, w * 0.22, h * 0.2, { fill: shade(c, 0.4), line: null }); g.restore(); }
    status(); const a = (o.from ?? 47) + t * (o.speed ?? 1) , tot = o.total ?? 9720;
    rr(g, x + 30 * U, y + h - 120 * U, w - 60 * U, 8 * U, 4 * U, 'rgba(255,255,255,0.3)'); rr(g, x + 30 * U, y + h - 120 * U, (w - 60 * U) * clamp(a / tot), 8 * U, 4 * U, c);
    text(g, fmt(a) + ' / ' + fmt(tot), x + 30 * U, y + h - 80 * U, { size: 28 * U, font: UIF, weight: 700, color: '#fff', align: 'left' });
  } else if (sc === 'chat') {
    status(); rr(g, x, y + 80 * U, w, 110 * U, 0, '#18191e');
    text(g, '‹', x + 40 * U, y + 135 * U, { size: 60 * U, font: UIF, weight: 700, color: '#ddd' }); oval(g, x + 105 * U, y + 135 * U, 32 * U, 32 * U, { fill: o.avatar || PAL.capB, line: null });
    text(g, o.name || 'jay', x + 155 * U, y + 135 * U, { size: 38 * U, font: UIF, weight: 700, color: '#f2f2f4', align: 'left' });
    let yy = y + 240 * U; const bw = w * 0.72;
    for (const m of o.messages || []) {
      const at = m.at ?? 0; if (t < at - (m.me ? 0 : 0.9)) break;
      const size = 32 * U, lines = wrap(g, m.text, bw - 50 * U, size, UIF, 700), bh = lines.length * size * 1.3 + 30 * U;
      if (t < at) { rr(g, x + 30 * U, yy, 110 * U, 60 * U, 30 * U, '#2a2c33'); for (let k = 0; k < 3; k++) oval(g, x + 62 * U + k * 24 * U, yy + 30 * U - Math.max(0, Math.sin(t * 9 - k)) * 6 * U, 7 * U, 7 * U, { fill: '#bbb', line: null }); break; }
      const bwr = Math.min(bw, Math.max(...lines.map((l) => measure(g, l, size, UIF, 700))) + 50 * U), bx = m.me ? x + w - 30 * U - bwr : x + 30 * U;
      const k = ease.outBack(clamp((t - at) / 0.3)); g.save(); g.translate(bx + bwr / 2, yy + bh / 2); g.scale(k, k); g.translate(-(bx + bwr / 2), -(yy + bh / 2));
      rr(g, bx, yy, bwr, bh, 26 * U, m.me ? PAL.blueMsg : '#2a2c33'); lines.forEach((l, i) => text(g, l, bx + 25 * U, yy + 15 * U + size * 0.65 + i * size * 1.3, { size, font: UIF, weight: 600, color: '#fff', align: 'left' })); g.restore();
      yy += bh + 18 * U; if (m.day) { text(g, m.day, x + w / 2, yy - bh - 40 * U, { size: 22 * U, font: UIF, weight: 600, color: '#888' }); }
    }
    if (o.seen !== undefined && t >= o.seen) text(g, 'Seen', x + w - 40 * U, yy, { size: 24 * U, font: UIF, weight: 600, color: '#9a9aa0', align: 'right' });
    // o nhap + ban phim
    const ky = o.keyboard ? y + h * 0.62 : y + h - 110 * U; rr(g, x + 24 * U, ky, w - 48 * U, 70 * U, 35 * U, '#24262c');
    const draft = o.draft || ''; const shown = draft.slice(0, Math.floor(clamp((t - (o.draftAt ?? 0)) * 12) / 1) || 0); if (draft) text(g, draft.slice(0, Math.max(0, Math.floor((t - (o.draftAt ?? 0)) * 12))), x + 50 * U, ky + 36 * U, { size: 30 * U, font: UIF, weight: 600, color: '#eee', align: 'left' });
    if (Math.floor(t * 2) % 2 === 0) rr(g, x + 50 * U + (draft ? measure(g, draft.slice(0, Math.max(0, Math.floor((t - (o.draftAt ?? 0)) * 12))), 30 * U, UIF, 600) : 0), ky + 18 * U, 3 * U, 36 * U, 1, '#4d8cff');
    oval(g, x + w - 62 * U, ky + 35 * U, 26 * U, 26 * U, { fill: PAL.blueMsg, line: null }); text(g, '↑', x + w - 62 * U, ky + 36 * U, { size: 32 * U, font: UIF, weight: 700, color: '#fff' });
    if (o.keyboard) { rr(g, x, ky + 90 * U, w, h, 0, '#1a1b20'); ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'].forEach((row, ri) => [...row].forEach((ch, ci) => { const kw = (w - 40 * U) / 10, kx = x + 20 * U + ci * kw + ri * kw * 0.5; rr(g, kx + 3 * U, ky + 110 * U + ri * 80 * U, kw - 6 * U, 66 * U, 10 * U, '#3a3c44'); text(g, ch, kx + kw / 2, ky + 143 * U + ri * 80 * U, { size: 28 * U, font: UIF, weight: 600, color: '#ddd' }); })); }
  } else if (sc === 'email') {
    status(); text(g, 'Inbox', x + 40 * U, y + 140 * U, { size: 50 * U, font: UIF, weight: 700, color: '#fff', align: 'left' });
    const rows = o.rows || [{ from: o.from || 'Recruiting', subject: o.subject || 'Re: your application', preview: o.preview || 'Thank you for your time. We have decided to move forward with other candidates.', hl: true }, { from: 'Promo', subject: '50% off', preview: '...' }, { from: 'Bank', subject: 'Statement', preview: '...' }];
    rows.forEach((r, i) => { const yy = y + 200 * U + i * 210 * U; if (r.hl) rr(g, x + 14 * U, yy - 10 * U, w - 28 * U, 200 * U, 20 * U, '#1f2230'); oval(g, x + 52 * U, yy + 40 * U, 10 * U, 10 * U, { fill: r.hl ? '#4d8cff' : '#333', line: null }); text(g, r.from, x + 80 * U, yy + 30 * U, { size: 30 * U, font: UIF, weight: 700, color: '#fff', align: 'left' }); text(g, r.subject, x + 80 * U, yy + 72 * U, { size: 27 * U, font: UIF, weight: 600, color: '#ddd', align: 'left' }); wrap(g, r.preview, w - 120 * U, 24 * U, UIF, 600).slice(0, 2).forEach((l, k) => text(g, l, x + 80 * U, yy + 112 * U + k * 32 * U, { size: 24 * U, font: UIF, weight: 600, color: '#8c8f99', align: 'left' })); });
  } else if (sc === 'lock') {
    const gr = g.createLinearGradient(x, y, x, y + h); gr.addColorStop(0, '#1d2340'); gr.addColorStop(1, '#3a2240'); g.fillStyle = gr; g.fillRect(x, y, w, h);
    text(g, o.time || '3:17', x + w / 2, y + h * 0.22, { size: 150 * U, font: UIF, weight: 700, color: '#f4f4f6' }); text(g, o.date || 'Tuesday, March 4', x + w / 2, y + h * 0.12, { size: 30 * U, font: UIF, weight: 600, color: '#ddd' });
    (o.notes || []).forEach((n, i) => { if (t < (n.at ?? 0)) return; const k = ease.outBack(clamp((t - (n.at ?? 0)) / 0.35)), yy = y + h * 0.38 + i * 150 * U; g.save(); g.globalAlpha = k; rr(g, x + 24 * U, yy, w - 48 * U, 130 * U, 26 * U, 'rgba(60,62,74,0.85)'); text(g, n.app || 'Messages', x + 60 * U, yy + 38 * U, { size: 24 * U, font: UIF, weight: 700, color: '#bbb', align: 'left' }); text(g, n.text, x + 60 * U, yy + 86 * U, { size: 30 * U, font: UIF, weight: 600, color: '#fff', align: 'left' }); g.restore(); });
  } else if (sc === 'counter') {
    status(); const n = o.n ?? 0; text(g, o.label || 'CLEAN STREAK', x + w / 2, y + h * 0.3, { size: 34 * U, font: UIF, weight: 700, color: '#aaa', spacing: 4 });
    text(g, String(n), x + w / 2, y + h * 0.45, { size: 200 * U, font: UIF, weight: 700, color: o.color || '#fff' }); text(g, 'days', x + w / 2, y + h * 0.56, { size: 40 * U, font: UIF, weight: 600, color: '#aaa' });
  } else if (sc === 'off') {
    const gr = g.createLinearGradient(x, y, x + w, y + h); gr.addColorStop(0, '#16171b'); gr.addColorStop(0.5, '#0b0b0d'); gr.addColorStop(1, '#141418'); g.fillStyle = gr; g.fillRect(x, y, w, h);
    g.save(); g.globalAlpha = 0.08; g.fillStyle = '#fff'; g.beginPath(); g.moveTo(x, y + h * 0.3); g.lineTo(x + w, y); g.lineTo(x + w, y + h * 0.1); g.lineTo(x, y + h * 0.45); g.fill(); g.restore();
    if (o.reflect) { g.save(); g.globalAlpha = 0.18; oval(g, x + w / 2, y + h * 0.45, w * 0.26, w * 0.26, { fill: PAL.hero, line: null }); g.restore(); }
  }
  g.restore();
  return { x, y, w, h };
}

// dong ho bao thuc can canh
export function bigClock(g, cx, cy, s, o = {}) {
  const w = s * 1.5, h = s * 0.75, col = o.color || PAL.clock, t = o.t || 0;
  light(g, cx, cy, s * 1.6, col, 0.15);
  box(g, cx - w / 2, cy - h / 2, w, h, { fill: '#1c1d22', line: PAL.line, r: s * 0.1, lw: 4 });
  box(g, cx - s * 0.18, cy - h / 2 - s * 0.07, s * 0.36, s * 0.08, { fill: '#2a2c33', r: s * 0.03 }); text(g, 'SNOOZE', cx, cy - h / 2 - s * 0.03, { size: s * 0.035, font: UIF, weight: 700, color: '#888' });
  const show = o.blink ? Math.floor(t * 2) % 2 === 0 : true;
  g.save(); g.shadowColor = col; g.shadowBlur = s * 0.12; text(g, show ? String(o.time ?? '5:00') : String(o.time ?? '5:00').replace(':', ' '), cx, cy + s * 0.02, { size: s * 0.42, font: UIF, weight: 700, color: col, spacing: s * 0.02 }); g.restore();
  if (o.ring && Math.sin(t * 24) > -0.2) for (const d of [-1, 1]) for (let i = 0; i < 3; i++) ln(g, [[cx + d * (w / 2 + s * 0.06 + i * s * 0.05), cy - h * 0.6 + i * s * 0.05], [cx + d * (w / 2 + s * 0.11 + i * s * 0.05), cy - h * 0.75 + i * s * 0.05]], { color: col, lw: s * 0.015, la: 1 });
}

// so tay mo, chu viet tay hien dan, tay cam but
export function notebook(g, cx, cy, s, o = {}) {
  const w = s * 1.25, h = s * 0.85, t = o.t || 0;
  light(g, cx, cy, s * 1.2, PAL.lamp, 0.25);
  box(g, cx - w / 2, cy - h / 2, w, h, { fill: '#efe8d6', line: '#7a705e', r: 8 }); ln(g, [[cx, cy - h / 2], [cx, cy + h / 2]], { color: '#7a705e', lw: 2 });
  for (let i = 1; i < 9; i++) ln(g, [[cx + 20, cy - h / 2 + i * h / 9], [cx + w / 2 - 20, cy - h / 2 + i * h / 9]], { color: '#9fb4cf', lw: 1.2, la: 0.6 });
  const str = o.text || 'day 1.', lines = String(str).split('\n'), cps = o.cps || 9, at = o.at ?? 0.3; let n = Math.max(0, Math.floor((t - at) * cps)), lastX = cx - w * 0.38, lastY = cy - h * 0.2;
  lines.forEach((l, i) => { const vis = l.slice(0, n); n -= l.length; if (!vis) return; const x0 = (o.page === 'right' ? cx + 40 : cx - w / 2 + 40), y0 = cy - h * 0.3 + i * s * 0.14; text(g, vis, x0, y0, { size: s * 0.1, font: FONT_HAND, weight: 700, color: '#2b2a33', align: 'left' }); lastX = x0 + measure(g, vis, s * 0.1, FONT_HAND, 700); lastY = y0; });
  if (o.hand !== false) { bigHand(g, lastX + s * 0.08, lastY + s * 0.16 + Math.sin(t * 14) * 3, s * 0.13, { rot: -0.5, sleeve: o.sleeve || PAL.hood }); ln(g, [[lastX + s * 0.02, lastY + s * 0.04], [lastX + s * 0.1, lastY + s * 0.14]], { color: '#222', lw: s * 0.012, la: 1 }); }
}

// tay cam dien thoai: back = long ban tay + ngon tay o mep (ve truoc dien thoai), front = ngon cai de len man hinh (ve sau)
export function phoneHand(g, px, py, pw, ph, side, part, o = {}) {
  // trai: 4 ngon tay om mep trai (co mong). phai: ngon cai cheo len man hinh + tay ao.
  const skin = o.skin || '#d9d6cf', ed = '#1b1c22', s = pw * 0.3, t = o.t || 0, lw = Math.max(2.5, s * 0.06);
  g.save(); g.lineWidth = lw; g.strokeStyle = ed; g.lineJoin = 'round';
  const nail = (x, y, w, h) => { g.beginPath(); g.roundRect(x, y, w, h, w * 0.3); g.fillStyle = '#ecebe6'; g.fill(); g.lineWidth = lw * 0.6; g.stroke(); g.lineWidth = lw; };
  if (side < 0 && part === 'front') {
    const fx0 = px - s * 0.45, fy0 = py + ph * (o.handY ?? 0.55);
    for (let i = 0; i < 4; i++) { const yy = fy0 + i * s * 0.5, ww = s * (0.95 - Math.abs(i - 1.2) * 0.08); g.beginPath(); g.roundRect(fx0, yy, ww, s * 0.48, s * 0.22); g.fillStyle = skin; g.fill(); g.stroke(); nail(fx0 + ww - s * 0.34, yy + s * 0.1, s * 0.24, s * 0.28); g.beginPath(); g.arc(fx0 + ww - s * 0.5, yy + s * 0.24, s * 0.08, -1, 1); g.lineWidth = lw * 0.5; g.stroke(); g.lineWidth = lw; }
  }
  if (side > 0 && part === 'front') {
    const tap = o.tap ? Math.max(0, Math.sin(t * 6)) * s * 0.15 : 0;
    const bx = px + pw + s * 0.55, by = py + ph * (o.thumbY ?? 0.8);
    if (o.sleeve) { g.save(); g.translate(bx + s * 0.3, by + s * 0.4); g.rotate(-0.55); g.beginPath(); g.roundRect(-s * 0.9, -s * 0.5, s * 3, s * 1.6, s * 0.3); g.fillStyle = o.sleeve; g.fill(); g.stroke(); g.lineWidth = lw * 0.5; for (let k = 0; k < 4; k++) { g.beginPath(); g.moveTo(-s * 0.7 + k * s * 0.18, -s * 0.45); g.lineTo(-s * 0.7 + k * s * 0.18, s * 0.2); g.stroke(); } g.restore(); g.lineWidth = lw; }
    g.save(); g.translate(bx - s * 0.2, by - s * 0.2 - tap); g.rotate(-0.42); g.scale(0.82, 0.82);
    g.beginPath(); g.moveTo(s * 0.5, s * 0.9); g.lineTo(-s * 1.9, s * 0.35); g.quadraticCurveTo(-s * 2.45, s * 0.3, -s * 2.45, -s * 0.15); g.quadraticCurveTo(-s * 2.45, -s * 0.55, -s * 1.9, -s * 0.5); g.lineTo(s * 0.5, -s * 0.35); g.closePath();
    const gr = g.createLinearGradient(0, -s * 0.5, 0, s * 0.6); gr.addColorStop(0, '#e4e8f2'); gr.addColorStop(1, skin); g.fillStyle = gr; g.fill(); g.stroke();
    nail(-s * 2.3, -s * 0.35, s * 0.42, s * 0.52); g.lineWidth = lw * 0.5; g.beginPath(); g.moveTo(-s * 1.2, -s * 0.3); g.lineTo(-s * 1.2, -s * 0.05); g.moveTo(-s * 1.1, -s * 0.28); g.lineTo(-s * 1.1, -s * 0.1); g.stroke();
    g.restore();
  }
  g.restore();
}
