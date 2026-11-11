// templates.js — mau canh cho phim khong loi doc. shots.json: { "tpl": "<ten>", "args": {...} }. Thoi gian "at" = giay tinh tu dau canh.
// Mau: scene (boi canh + nhan vat + giong noi) | phone | clock | calendar | face | note | card | black | cta
// Lop phu chung cho moi mau: texts, hud, fx, lights, cam (xem README trong references/mau-canh.md)
import { E, clamp, lerp, ease, kf, rng, noise, alpha, shade, registerTemplate, text, measure, radGrad } from '/engine/core.js';
import { PAL, accent, fx, fy, fs, at, window01, safe, narr, tempt, say, big, stroke, light, beam, vignette, ln, box, oval, FONT_NARR, FONT_HAND, FONT_UI, fillAll, wrap } from './ink.js';
import { bean, lyingHead, head, bigHand, CAST } from './bean.js';
import { set, rain, dust, calendar, digitClock } from './sets.js';
import { phone, bigClock, notebook, phoneHand } from './phone.js';

// ---------- may quay: cam = { from: [x, y, zoom], to: [x, y, zoom], at, dur } (x, y = diem nhin 0..1). shake = { at, amt, dur }
export function camera(g, lt, info, fn) {
  const c = info.args.cam || {}, d = info.dur;
  const a0 = c.at ?? 0, dd = c.dur ?? (d - a0), k = (c.ease === 'linear' ? (x) => x : ease.sine)(clamp((lt - a0) / Math.max(0.1, dd)));
  const A = c.from || [0.5, 0.5, 1], B = c.to || (c.from ? c.from : [0.5, 0.5, info.args.push === false ? 1 : 1.05]);
  let z = lerp(A[2] ?? 1, B[2] ?? 1, k), cx = lerp(fx(A[0]), fx(B[0]), k), cy = lerp(fy(A[1]), fy(B[1]), k);
  const hw = E.W / (2 * z), hh = E.H / (2 * z); cx = clamp(cx, hw, E.W - hw); cy = clamp(cy, hh, E.H - hh);
  let dx = 0, dy = 0; for (const s of [].concat(info.args.shake || [])) { const p = (lt - (s.at ?? 0)) / (s.dur ?? 0.45); if (p >= 0 && p < 1) { const amp = (s.amt ?? 1) * 18 * (1 - p); dx += noise(lt * 40, 1) * amp; dy += noise(lt * 40, 5) * amp; } }
  g.save(); g.translate(E.W / 2, E.H / 2); g.scale(z, z); g.translate(-cx + dx, -cy + dy); fn(); g.restore();
}

// ---------- vi tri: so 0..1 | px | "moc" cua boi canh: bed.sit, bed.head, desk.seat, bus.seat, bench, table.left, table.right, top, door, neon, step:3, mirror
function anchor(M, v, axis, def) {
  if (typeof v === 'string') {
    let p = null; const [k, sub] = v.split('.');
    if (k.startsWith('step') && M.step) p = M.step(+(v.split(':')[1] || 0));
    else if (M[k]) p = sub ? M[k][sub] : (Array.isArray(M[k]) ? M[k] : M[k].seat || M[k].sit || [M[k].x, M.gy]);
    if (p) return axis === 'x' ? p[0] : p[1];
  }
  return axis === 'x' ? fx(v, def) : fy(v, def);
}
// ---------- nhan vat: actors = [{ who, x, y, h, pose, face, facing, look, at, out, walk: { to, at, dur, speed } | run, poseAt, faceAt, lookAt, hold, glowFace, scale, rot, z }]
function actorState(a, lt, M, info) {
  const a0 = a.at ?? 0; let x = anchor(M, a.x, 'x', 0.5), y = a.y !== undefined ? anchor(M, a.y, 'y', 0.8) : (typeof a.x === 'string' ? anchor(M, a.x, 'y', 0.8) : M.gy);
  let moving = false, facing = a.facing ?? 1;
  const mv = a.walk || a.run;
  if (mv && mv.to !== undefined) {
    const s0 = mv.at ?? a0, s1 = s0 + (mv.dur ?? Math.max(0.5, info.dur - s0)), k = clamp((lt - s0) / (s1 - s0));
    const tx = anchor(M, mv.to, 'x', 0.5), ty = mv.toY !== undefined ? anchor(M, mv.toY, 'y', 0.8) : (typeof mv.to === 'string' ? anchor(M, mv.to, 'y', y) : y);
    x = lerp(x, tx, mv.ease === false ? k : ease.inOut(k) * 0.3 + k * 0.7); y = lerp(y, ty, k); moving = k > 0 && k < 1; if (a.facing === undefined) facing = tx >= anchor(M, a.x, 'x', 0.5) ? 1 : -1;
  }
  return { x, y, moving, facing };
}
function drawActor(g, a, lt, M, info) {
  const a0 = a.at ?? 0; if (lt < a0 - 0.001) return null; if (a.out !== undefined && lt > a.out + (a.fade ?? 0.6)) return null;
  const st = actorState(a, lt, M, info), h = fs(a.h, a.who === 'voice' ? 0.48 : 0.42);
  let alphaK = 1; if (a.fadeIn !== false && a.at) alphaK = clamp((lt - a0) / (a.fadeIn ?? (a.who === 'voice' ? 0.8 : 0.001))); if (a.out !== undefined) alphaK *= clamp(1 - (lt - a.out) / (a.fade ?? 0.6));
  const mv = a.walk || a.run;
  const o = { ...a, t: lt + (a.seed || 0), facing: st.facing, pose: at(lt, a.poseAt, a.pose || 'stand'), face: at(lt, a.faceAt, a.face || (a.who === 'voice' ? 'grin' : 'neutral')), look: at(lt, a.lookAt, a.look ?? 0.25) };
  if (st.moving) { if (a.run) o.run = a.run.speed || 1.6; else o.walk = (a.walk && a.walk.speed) || 0.9; }
  const k = alphaK; if (k <= 0) return null;
  g.save(); g.globalAlpha *= k;
  if (a.who === 'ghost') g.globalAlpha *= 0.4;
  if (a.who === 'voice') { const pulse = 0.85 + 0.15 * Math.sin(lt * 3.2); o.glow = a.glow || accent(); g.globalAlpha *= pulse * 0.25 + 0.75; }
  const r = bean(g, st.x, st.y, h, o); g.restore();
  return r;
}

// ---------- chu: texts = [{ kind: narr | tempt | say | big | sign, t, at, dur, x, y, pos: top|bottom|center, size, color, type: true, emph: {"word": "#hex"} }]
export function drawTexts(g, lt, info, list, ctx = {}) {
  const S = safe();
  for (const tx of list || []) {
    const a0 = tx.at ?? 0.3, dur = tx.dur ?? (info.dur - a0 - 0.1), a = window01(lt, a0, dur, tx.fi ?? (tx.kind === 'tempt' ? 0.2 : 0.45), tx.fo ?? 0.45); if (a <= 0) continue;
    const kind = tx.kind || 'narr';
    if (kind === 'narr') { const pos = tx.pos || 'top', y = tx.y !== undefined ? fy(tx.y) : pos === 'bottom' ? S.bottom - (E.vertical ? 260 : 70) : pos === 'center' ? E.H / 2 : S.top + (E.vertical ? 260 : 64); narr(g, tx.t, fx(tx.x, 0.5), y, { a, size: tx.size, color: tx.color, emph: tx.emph, maxW: tx.maxW ? fx(tx.maxW) : undefined, type: tx.type ? clamp((lt - a0) / Math.max(0.4, String(tx.t).length / 28)) : undefined }); }
    else if (kind === 'big') big(g, tx.t, fx(tx.x, 0.5), fy(tx.y, 0.5), { maxW: tx.maxW ? fx(tx.maxW) : undefined, a, size: tx.size, color: tx.color, type: tx.type ? clamp((lt - a0) / Math.max(0.4, String(tx.t).length / 18)) : undefined });
    else if (kind === 'tempt') { const v = ctx.voice; const S2 = safe(); let x = tx.x !== undefined ? fx(tx.x) : v ? v.head[0] : E.W * 0.7, y = tx.y !== undefined ? fy(tx.y) : v ? v.head[1] - v.R * 2.3 : E.H * 0.3; if (tx.y === undefined && v && y < S2.top + 150) { y = v.head[1] - v.R * 0.2; x = v.head[0] + (v.head[0] > E.W * 0.55 ? -1 : 1) * v.R * 4.2; } if (tx.x === undefined) x = Math.min(E.W * 0.86, Math.max(E.W * 0.14, x)); tempt(g, tx.t, x, y, { a, size: tx.size, color: tx.color, t: lt, type: tx.type === false ? undefined : clamp((lt - a0) / Math.max(0.35, String(tx.t).length / 16)) }); }
    else if (kind === 'say') { const who = ctx.heads?.[tx.who || 'hero'] || ctx.heads?.first; const x = tx.x !== undefined ? fx(tx.x) : who ? who.head[0] + who.R * 1.6 : E.W * 0.55, y = tx.y !== undefined ? fy(tx.y) : who ? who.head[1] - who.R * 1.9 : E.H * 0.35; say(g, tx.t, x, y, { a: clamp((lt - a0) / 0.4) * clamp((a0 + dur - lt) / 0.3), size: tx.size, tail: tx.tail }); }
    else if (kind === 'sign') text(g, tx.t, fx(tx.x, 0.5), fy(tx.y, 0.5), { size: tx.size || 40, font: FONT_HAND, weight: 700, color: tx.color || PAL.white, a });
  }
}

// ---------- bo dem goc trai: hud = { label: "DAY", n | from+to (dem dan), at, dur, reset: { at, to }, rows: [{ label, n, from, to, color }], color, x, y }
export function drawHud(g, lt, info, h) {
  if (!h) return; const S = safe(), size = E.vertical ? 40 : 30;
  const rows = h.rows ? h.rows : [{ label: h.label ?? 'DAY', n: h.n, from: h.from, to: h.to, at: h.at, dur: h.dur, reset: h.reset, color: h.color }];
  rows.forEach((r, i) => {
    const x = fx(h.x, E.vertical ? 0.08 : 0.032), y = (h.y !== undefined ? fy(h.y) : S.top + (E.vertical ? 220 : 42)) + i * size * 1.25;
    let n = r.n ?? r.to ?? 0; if (r.from !== undefined && r.to !== undefined) n = Math.round(lerp(r.from, r.to, ease.inOut(clamp((lt - (r.at ?? 0)) / (r.dur ?? Math.max(0.5, info.dur * 0.8))))));
    const fmt = (v) => (typeof v === 'number' && r.comma !== false ? v.toLocaleString('en-US') : String(v));
    text(g, r.label, x, y, { size, font: FONT_UI, weight: 700, color: '#e9e9ec', align: 'left', spacing: 1 });
    const nx = x + measure(g, r.label, size, FONT_UI, 700) + size * 0.45;
    const rs = r.reset;
    if (rs && lt >= rs.at) {
      const p = clamp((lt - rs.at) / 0.35), w = measure(g, fmt(n), size, FONT_UI, 700), q = clamp((lt - rs.at - 0.45) / 0.3);
      text(g, fmt(n), nx, y, { size, font: FONT_UI, weight: 700, color: '#e9e9ec', align: 'left', a: 1 - q * 0.9 });
      stroke(g, nx - 4, y + 2, nx + w + 4, y - 2, { p, lw: 5, glow: true });
      if (q > 0) text(g, fmt(rs.to ?? 0), nx + w + 14, y, { size, font: FONT_UI, weight: 700, color: accent(), align: 'left', a: q, glowColor: alpha(accent(), 0.6) });
    } else text(g, fmt(n), nx, y, { size, font: FONT_UI, weight: 700, color: r.color || (r.accent ? accent() : '#e9e9ec'), align: 'left' });
  });
}

// ---------- hieu ung: fx = [{ kind: flash | shards | speed | zzz | embers | pulse | rain | dust | spot | glitch | dark, at, dur, x, y, color }]
export function drawFx(g, lt, info, list, ctx = {}) {
  for (const f of list || []) {
    const a0 = f.at ?? 0, d = f.dur ?? 0.8, p = (lt - a0) / d; if (lt < a0) continue;
    const x = f.x !== undefined ? fx(f.x) : ctx.voice ? ctx.voice.head[0] : E.W / 2, y = f.y !== undefined ? fy(f.y) : ctx.voice ? ctx.voice.head[1] + ctx.voice.R * 2 : E.H / 2;
    if (f.kind === 'shards' && p < 1.6) { const r = rng(f.seed || 3); g.save(); g.globalCompositeOperation = 'lighter'; for (let i = 0; i < 26; i++) { const ang = r() * Math.PI * 2, sp = 200 + r() * 520, px = x + Math.cos(ang) * sp * ease.out(clamp(p)), py = y + Math.sin(ang) * sp * ease.out(clamp(p)) + 200 * p * p, s = 10 + r() * 22; g.save(); g.translate(px, py); g.rotate(r() * 6 + p * 4); g.globalAlpha = clamp(1.4 - p); g.strokeStyle = f.color || accent(); g.lineWidth = 2.5; g.shadowColor = f.color || accent(); g.shadowBlur = 10; g.beginPath(); g.moveTo(-s, 0); g.lineTo(0, -s * 0.6); g.lineTo(s * 0.7, s * 0.4); g.closePath(); g.stroke(); g.restore(); } g.restore(); }
    else if (f.kind === 'flash' && p < 1) { g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); g.fillStyle = `rgba(255,250,240,${(1 - ease.out(clamp(p))) * (f.a ?? 0.85)})`; g.fillRect(0, 0, E.W, E.H); g.restore(); }
    else if (f.kind === 'speed' && (f.dur === undefined || p < 1)) { const r = rng(9); g.save(); g.strokeStyle = alpha(f.color || '#e8d9a0', 0.55); g.lineWidth = 3; for (let i = 0; i < 14; i++) { const yy = y + (r() - 0.5) * 220, len = 120 + r() * 200, xx = x - 100 - ((lt * 900 + r() * 400) % 500) * (f.dir ?? 1); g.beginPath(); g.moveTo(xx, yy); g.lineTo(xx - len * (f.dir ?? 1), yy + len * 0.18); g.stroke(); } g.restore(); }
    else if (f.kind === 'zzz') { for (let i = 0; i < 3; i++) { const q = ((lt * 0.5 + i / 3) % 1); text(g, 'z', x + q * 60 + i * 6, y - q * 90, { size: 22 + q * 26, font: FONT_NARR, weight: 700, color: '#d8d8de', a: Math.sin(q * Math.PI) }); } }
    else if (f.kind === 'embers') { const r = rng(5); g.save(); g.globalCompositeOperation = 'lighter'; for (let i = 0; i < 40; i++) { const q = (lt * (0.15 + r() * 0.2) + r()) % 1, px = x + (r() - 0.5) * E.W * 0.6 + Math.sin(lt + i) * 20, py = y + E.H * 0.25 - q * E.H * 0.7; g.fillStyle = alpha(f.color || '#ffb03b', Math.sin(q * Math.PI) * 0.8); g.beginPath(); g.arc(px, py, 2 + r() * 3, 0, 7); g.fill(); } g.restore(); }
    else if (f.kind === 'pulse') { const k = Math.max(0, Math.sin(lt * (f.speed ?? 6))) ** 3 * (f.a ?? 0.35); g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); const R = Math.hypot(E.W, E.H) / 2; g.fillStyle = radGrad(g, E.W / 2, E.H / 2, R * 0.4, R, [[0, 'rgba(0,0,0,0)'], [1, alpha(f.color || accent(), k)]]); g.fillRect(0, 0, E.W, E.H); g.restore(); }
    else if (f.kind === 'rain') rain(g, lt, { n: f.n || 160, a: f.a });
    else if (f.kind === 'dust') dust(g, lt, { n: f.n || 40 });
    else if (f.kind === 'spot') light(g, x, y, fs(f.r, 0.4), f.color || '#ffe9c0', f.a ?? 0.3);
    else if (f.kind === 'dark' ) { g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); g.fillStyle = `rgba(0,0,0,${clamp(p) * (f.a ?? 0.7)})`; g.fillRect(0, 0, E.W, E.H); g.restore(); }
    else if (f.kind === 'glitch' && p < 1) { const r = rng(Math.floor(lt * 30)); g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); for (let i = 0; i < 6; i++) { g.fillStyle = alpha(i % 2 ? accent() : '#5ad1ff', 0.18); g.fillRect(0, r() * E.H, E.W, 6 + r() * 30); } g.restore(); }
  }
}
function drawLights(g, list) { for (const l of list || []) light(g, fx(l.x), fy(l.y), fs(l.r, 0.3), l.color || PAL.lamp, l.a ?? 0.35); }

// lop phu chung (ngoai may quay): chu, bo dem, hieu ung man hinh
function overlays(g, lt, info, ctx) {
  const a = info.args;
  drawFx(g, lt, info, (a.fx || []).filter((f) => ['flash', 'pulse', 'dark', 'glitch'].includes(f.kind)), ctx);
  if (a.vignette !== false) vignette(g, a.vignette ?? 0.5);
  drawHud(g, lt, info, a.hud);
  drawTexts(g, lt, info, a.texts, ctx);
}
// nen mo (canh phone / face): ve boi canh 1 lan vao canvas nho, lam mo 1 lan, phong to -> nhanh
const _bgc = new Map();
function blurBg(g, kind, setArgs = {}, dim = 0.4) {
  const key = kind + JSON.stringify(setArgs) + E.W;
  let c = _bgc.get(key);
  if (!c) {
    const w = Math.round(E.W / 4), h = Math.round(E.H / 4), raw = document.createElement('canvas'); raw.width = w; raw.height = h;
    const q = raw.getContext('2d'); q.scale(0.25, 0.25); set(q, kind, { ...setArgs, t: 0 });
    c = document.createElement('canvas'); c.width = w; c.height = h; const z = c.getContext('2d'); z.filter = 'blur(3px)'; z.drawImage(raw, 0, 0); z.filter = 'none'; z.fillStyle = `rgba(0,0,0,${dim})`; z.fillRect(0, 0, w, h);
    _bgc.set(key, c); if (_bgc.size > 30) _bgc.delete(_bgc.keys().next().value);
  }
  g.save(); g.imageSmoothingEnabled = true; g.drawImage(c, -20, -12, E.W + 40, E.H + 24); g.restore();
}
const tpl = (name, draw) => registerTemplate(name, { draw: (g, lt, info) => draw(g, lt, info, info.args || {}) });

// ---------- scene: boi canh + nguoi + giong noi.  args: set, setArgs {...}, bed {who, face, faceAt, arm, at}, actors [...], lights, fx, cam, texts, hud
tpl('scene', (g, lt, info, a) => {
  const ctx = { heads: {} };
  camera(g, lt, info, () => {
    const so = { ...(a.setArgs || {}), t: lt, occupied: !!a.bed };
    const M = set(g, a.set || 'bedroom', so);
    drawLights(g, a.lights);
    const actors = (a.actors || []).slice().sort((p, q) => (p.z || 0) - (q.z || 0));
    const behind = actors.filter((x) => x.behind), front = actors.filter((x) => !x.behind);
    for (const ac of behind) { const r = drawActor(g, ac, lt, M, info); if (r) { if (ac.who === 'voice') ctx.voice = r; else { ctx.heads[ac.who] = r; ctx.heads.first = ctx.heads.first || r; } } }
    if (a.bed && M.bed) {
      M.pillow(); const b = a.bed, R = fs(b.r, 0.05);
      const hx = M.bed.head[0] + (b.dx || 0), hy = M.bed.head[1] + (b.dy || 0) + Math.sin(lt * 1.6) * 1.5;
      const face = at(lt, b.faceAt, b.face || 'sleep');
      lyingHead(g, hx, hy, R, { who: b.who || 'hero', face, look: at(lt, b.lookAt, b.look ?? -0.4), t: lt, rot: b.rot ?? -0.25, facing: b.facing ?? -1 });
      M.blanket(true);
      if (b.arm) { const k = typeof b.arm === 'object' ? ease.inOut(clamp((lt - (b.arm.at ?? 0)) / (b.arm.dur ?? 0.8))) : 1, ex = lerp(hx + R * 1.2, M.clock[0] + 30, k), ey = lerp(hy + R * 1.6, M.clock[1] + 30, k); g.save(); g.lineCap = 'round'; g.strokeStyle = PAL.heroLine; g.lineWidth = R * 0.42; g.beginPath(); g.moveTo(hx + R * 1.4, hy + R * 1.3); g.quadraticCurveTo((hx + ex) / 2, ey - R * 0.5, ex, ey); g.stroke(); g.strokeStyle = PAL.hero; g.lineWidth = R * 0.32; g.stroke(); g.fillStyle = PAL.hero; g.beginPath(); g.arc(ex, ey, R * 0.26, 0, 7); g.fill(); g.restore(); }
      ctx.heads.hero = ctx.heads.hero || { head: [hx, hy], R }; ctx.heads.first = ctx.heads.first || ctx.heads.hero;
      if (b.zzz) drawFx(g, lt, info, [{ kind: 'zzz', x: hx + R, y: hy - R * 1.2 }]);
    }
    for (const ac of front) { const r = drawActor(g, ac, lt, M, info); if (r) { if (ac.who === 'voice') ctx.voice = r; else { ctx.heads[ac.who] = r; ctx.heads.first = ctx.heads.first || r; } } }
    drawFx(g, lt, info, (a.fx || []).filter((f) => !['flash', 'pulse', 'dark', 'glitch'].includes(f.kind)), ctx);
  });
  overlays(g, lt, info, ctx);
});

// ---------- phone: dien thoai can canh, hai tay cam. args: screen + du lieu man hinh (xem phone.js), bg (boi canh mo phia sau), hands (true), tilt
tpl('phone', (g, lt, info, a) => {
  camera(g, lt, info, () => {
    if (a.bg) blurBg(g, a.bg, a.setArgs, 0.45); else { fillAll(g, '#0d0e12'); light(g, E.W / 2, E.H / 2, E.H, '#3a4a8a', 0.18); }
    const h = fs(a.h, E.vertical ? 0.62 : 0.95), cx = fx(a.x, 0.5), cy = fy(a.y, E.vertical ? 0.5 : 0.6) + Math.sin(lt * 1.3) * 3;
    const pw = h * 0.49, rot = a.tilt ?? -0.03, ho = { t: lt, sleeve: a.sleeve ?? PAL.hood, tap: a.thumb };
    g.save(); g.translate(cx, cy); g.rotate(rot);
    if (a.hands !== false) { phoneHand(g, -pw / 2, -h / 2, pw, h, -1, 'back', ho); phoneHand(g, -pw / 2, -h / 2, pw, h, 1, 'back', ho); }
    phone(g, 0, 0, h, { ...a, t: lt - (a.screenAt ?? 0) });
    if (a.hands !== false) { phoneHand(g, -pw / 2, -h / 2, pw, h, -1, 'front', ho); if (a.hands !== 'left') phoneHand(g, -pw / 2, -h / 2, pw, h, 1, 'front', ho); }
    g.restore();
    drawFx(g, lt, info, (a.fx || []).filter((f) => !['flash', 'pulse', 'dark', 'glitch'].includes(f.kind)));
  });
  // chu ke chuyen dat canh dien thoai (khong de len man hinh)
  const side = (a.texts || []).map((t) => (t.kind === 'narr' && t.x === undefined && t.y === undefined && !t.pos && !E.vertical ? { ...t, x: fx(a.x, 0.5) < E.W / 2 ? 0.76 : 0.78, y: 0.5, maxW: 0.32 } : t));
  overlays(g, lt, { ...info, args: { ...a, texts: side } }, {});
});
// ---------- clock: dong ho bao thuc to. args: time, timeAt [[giay, "5:01"]], ring, blink
tpl('clock', (g, lt, info, a) => { camera(g, lt, info, () => { fillAll(g, '#0d0d10'); bigClock(g, fx(a.x, 0.5), fy(a.y, 0.52), fs(a.s, 0.55), { time: at(lt, a.timeAt, a.time ?? '5:00'), ring: a.ring, blink: a.blink, t: lt, color: a.color }); drawFx(g, lt, info, (a.fx || []).filter((f) => !['flash', 'pulse', 'dark', 'glitch'].includes(f.kind))); }); overlays(g, lt, info, {}); });
// ---------- calendar: lich to. args: month, from, to (so o danh dau, dem dan), mode x|fill, reset {at}
tpl('calendar', (g, lt, info, a) => { camera(g, lt, info, () => { fillAll(g, '#121216'); const w = fs(a.s, 0.4) * (E.vertical ? 1.6 : 1); let n = Math.round(lerp(a.from ?? 0, a.to ?? a.from ?? 0, ease.inOut(clamp((lt - (a.at ?? 0.3)) / (a.dur ?? Math.max(0.5, info.dur * 0.7)))))); if (a.reset && lt >= a.reset.at) n = Math.round(lerp(n, 0, clamp((lt - a.reset.at) / 0.5))); calendar(g, E.W / 2 - w / 2, E.H * 0.56 - w * 0.55, w, { month: a.month, fill: n, mode: a.mode, color: a.color }); }); overlays(g, lt, info, {}); });
// ---------- face: can mat (tu nguc len). args: who, face, faceAt, look, lookAt, tears, sweat, bg (boi canh mo), glowFace, x
tpl('face', (g, lt, info, a) => {
  const ctx = { heads: {} };
  camera(g, lt, info, () => {
    if (a.bg) blurBg(g, a.bg, a.setArgs, 0.35); else fillAll(g, '#121216');
    drawLights(g, a.lights);
    const hgt = fs(a.h, E.vertical ? 0.95 : 1.2), x = fx(a.x, 0.5), y = fy(a.y, 0.52);
    const r = bean(g, x, y + hgt * 0.77, hgt, { who: a.who || 'hero', pose: at(lt, a.poseAt, a.pose || 'stand'), face: at(lt, a.faceAt, a.face || 'neutral'), look: at(lt, a.lookAt, a.look ?? 0), facing: a.facing ?? 1, t: lt, tears: a.tears, sweat: a.sweat, bloodshot: a.bloodshot, glowFace: a.glowFace, hold: a.hold });
    ctx.heads.hero = r; ctx.heads.first = r;
    for (const ac of a.actors || []) { const rr = drawActor(g, ac, lt, { gy: E.H * 0.8 }, info); if (rr && ac.who === 'voice') ctx.voice = rr; }
    drawFx(g, lt, info, (a.fx || []).filter((f) => !['flash', 'pulse', 'dark', 'glitch'].includes(f.kind)), ctx);
  });
  overlays(g, lt, info, ctx);
});
// ---------- note: so tay, tay viet chu (Caveat). args: text ("\n" xuong dong), at, cps
tpl('note', (g, lt, info, a) => { camera(g, lt, info, () => { fillAll(g, '#16130f'); notebook(g, fx(a.x, 0.5), fy(a.y, 0.52), fs(a.s, 0.8) * (E.vertical ? 0.9 : 1), { text: a.text, at: a.at, cps: a.cps, t: lt, sleeve: a.sleeve }); }); overlays(g, lt, info, {}); });
// ---------- black: nen den + chu (dung kem texts)
// black: nen den, chu to giua man. Dong ke chuyen (narr) co 72px; dong nhan (big) 112px vien xam. Tu xep doc giua man neu khong ghi y.
tpl('black', (g, lt, info, a) => {
  fillAll(g, '#0b0b0d'); if (a.dust) dust(g, lt, { n: 25 });
  const list = (a.texts || []).map((t) => ({ ...t })); const free = list.filter((t) => t.y === undefined && !t.pos && (t.kind === 'narr' || t.kind === 'big' || !t.kind));
  if (free.length) {
    const hs = free.map((t) => (t.kind === 'big' ? (E.vertical ? 92 : 112) * 1.25 : (E.vertical ? 72 : 78) * 1.5)); const tot = hs.reduce((p, q) => p + q, 0); let y = E.H * (a.cy ?? 0.43) - tot / 2;
    free.forEach((t, i) => { t.y = y + hs[i] / 2; y += hs[i]; if (t.kind !== 'big' && !t.size) t.size = E.vertical ? 72 : 78; t.maxW = t.maxW ?? 0.9; });
  }
  overlays(g, lt, { ...info, args: { ...a, texts: list, vignette: false } }, {});
  if (a.line !== false) { const S = safe(), w = E.W * 0.115, yy = S.bottom - (E.vertical ? 200 : 26); g.save(); g.strokeStyle = accent(); g.globalAlpha = 0.85; g.lineWidth = 6; g.lineCap = 'round'; g.shadowColor = accent(); g.shadowBlur = 12; g.beginPath(); g.moveTo(E.W / 2 - w / 2, yy); g.lineTo(E.W / 2 + w / 2, yy); g.stroke(); g.restore(); }
});
// ---------- card: the ket. args: word ("DISCIPLINE."), sub, sub2 (mau nhan), part ("PART 2"), type (go tung chu), at
tpl('card', (g, lt, info, a) => {
  fillAll(g, '#0f0f12'); dust(g, lt, { n: 22 }); light(g, E.W / 2, E.H * 0.45, E.H * 0.7, '#ffffff', 0.05);
  const word = a.word || 'DISCIPLINE.', a0 = a.at ?? 0.4, size = fs(a.size, E.vertical ? 0.075 : 0.15), cy = E.H * (E.vertical ? 0.45 : 0.42);
  const nType = a.type === false ? word.length : Math.floor(clamp((lt - a0) / (a.typeDur ?? 1.2)) * word.length);
  const vis = word.slice(0, nType), fullW = measure(g, word, size, FONT_NARR, 700);
  text(g, vis, E.W / 2 - fullW / 2, cy, { size, font: FONT_NARR, weight: 700, color: PAL.white, align: 'left', glowColor: 'rgba(255,255,255,0.25)' });
  const u0 = a0 + (a.typeDur ?? 1.2) + 0.1; stroke(g, E.W / 2 - fullW * 0.52, cy + size * 0.62, E.W / 2 + fullW * 0.52, cy + size * 0.6, { p: clamp((lt - u0) / 0.45), lw: size * 0.06, wob: 2 });
  let y = cy + size * 1.1;
  if (a.part) { const q = clamp((lt - u0 - 0.2) / 0.4); text(g, a.part, E.W / 2, y, { size: size * 0.38, font: FONT_NARR, weight: 700, color: PAL.white, a: q }); y += size * 0.55; }
  if (a.sub) { const q = clamp((lt - u0 - 0.5) / 0.5); text(g, a.sub, E.W / 2, y, { size: size * 0.3, font: FONT_NARR, weight: 700, color: '#e6e6ea', a: q }); y += size * 0.42; }
  if (a.sub2) { const q = clamp((lt - (a.sub2At ?? u0 + 1.5)) / 0.5); text(g, a.sub2, E.W / 2, y, { size: size * 0.3, font: FONT_NARR, weight: 700, color: accent(), a: q, glowColor: alpha(accent(), 0.5) }); }
  drawTexts(g, lt, info, a.texts);
});
// ---------- cta: man xin dang ky cuoi phim. args: line ("If this hit, like and subscribe."), line2, who (nhan vat vay tay)
tpl('cta', (g, lt, info, a) => {
  fillAll(g, '#0f0f12'); light(g, E.W / 2, E.H * 0.6, E.H * 0.6, '#ffffff', 0.05);
  const S = safe(), y0 = E.vertical ? E.H * 0.32 : S.top + (S.h * 0.18);
  narr(g, a.line || 'If this hit, like and subscribe.', E.W / 2, y0, { size: E.vertical ? 60 : 54, a: clamp((lt - 0.2) / 0.5) });
  const by = y0 + (E.vertical ? 150 : 120), k1 = lt > 1.6, k2 = lt > 2.6;
  const btn = (x, label, on, col) => { const w = measure(g, label, 38, FONT_UI, 700) + 90; g.save(); g.fillStyle = on ? col : '#2a2c33'; g.beginPath(); g.roundRect(x - w / 2, by - 36, w, 72, 36); g.fill(); g.restore(); text(g, (on && label === 'SUBSCRIBE' ? '✓ SUBSCRIBED' : label), x, by, { size: 34, font: FONT_UI, weight: 700, color: '#fff' }); };
  btn(E.W / 2 - 190, 'LIKE', k1, '#3d6ff2'); btn(E.W / 2 + 170, 'SUBSCRIBE', k2, '#4a4c55');
  const cxk = lt < 1.6 ? kf(lt, [[0.6, [E.W * 0.7, E.H * 0.7]], [1.5, [E.W / 2 - 180, by + 14]]]) : kf(lt, [[1.7, [E.W / 2 - 180, by + 14]], [2.5, [E.W / 2 + 200, by + 14]]]);
  g.save(); g.translate(cxk[0], cxk[1]); g.fillStyle = '#fff'; g.strokeStyle = '#000'; g.lineWidth = 2; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, 30); g.lineTo(8, 23); g.lineTo(14, 36); g.lineTo(19, 33); g.lineTo(13, 21); g.lineTo(23, 21); g.closePath(); g.fill(); g.stroke(); g.restore();
  if (a.line2) narr(g, a.line2, E.W / 2, by + 80, { size: 34, color: accent(), a: clamp((lt - 3) / 0.5) });
  bean(g, E.W / 2, (E.vertical ? E.H * 0.72 : S.bottom - 40), E.H * (E.vertical ? 0.16 : 0.2), { who: a.who || 'hero', pose: lt > 2.8 ? 'wave' : 'stand', face: lt > 2.8 ? 'smile' : 'neutral', t: lt, look: 0 });
});

export const TEMPLATE_LIST = ['scene', 'phone', 'clock', 'calendar', 'face', 'note', 'black', 'card', 'cta'];
