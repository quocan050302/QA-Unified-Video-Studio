// player.js — nap du an, ve tung khung hinh: shot + chuyen canh + dai den + chinh mau + hat nhieu.
import { E, V, clamp, lerp, ease, prog, rng, css, hex, alpha, getShot, shotIds, STYLES, text, FONTS, UI, mood, getTemplate, IMG, ASSETS } from './core.js';

const q = new URLSearchParams(location.search);
const PROJ = q.get('proj');                  // vd /proj
const SCALE = +(q.get('scale') || 1);
const RES = { '720p': 720, '1080p': 1080, '1440p': 1440, '2160p': 2160 };
let cv, g, scv, sg, pcv, pg, grains = [];
let T3 = null; const S3 = new Map();   // canh 3D: nap Three.js khi can, giu trang thai theo shot

async function getJSON(u, def) { try { const r = await fetch(u); if (!r.ok) return def; return await r.json(); } catch { return def; } }

async function boot() {
  const cfg = await getJSON(`${PROJ}/config.json`, {});
  const story = await getJSON(`${PROJ}/story/shots.json`, { shots: [] });
  E.cfg = cfg; E.shots = story.shots || []; E.story = story;
  E.words = await getJSON(`${PROJ}/timeline/words.json`, []);
  E.lines = await getJSON(`${PROJ}/timeline/lines.json`, []);
  E.fps = cfg.fps || 24; E.vertical = cfg.aspect === '9:16';
  E.W = E.vertical ? 1080 : 1920; E.H = E.vertical ? 1920 : 1080;
  const shortSide = (RES[cfg.resolution] || 1080) * SCALE;
  E.PX = shortSide / (E.vertical ? E.W : E.H);
  E.duration = story.duration || (E.shots.length ? E.shots[E.shots.length - 1].end : 10);
  const pw = Math.round(E.W * E.PX), ph = Math.round(E.H * E.PX);
  cv = document.getElementById('c'); cv.width = pw; cv.height = ph; g = cv.getContext('2d');
  scv = document.createElement('canvas'); scv.width = pw; scv.height = ph; sg = scv.getContext('2d');
  pcv = document.createElement('canvas'); pcv.width = pw; pcv.height = ph; pg = pcv.getContext('2d');
  // hat nhieu: 4 tam nho lap lai
  for (let k = 0; k < 4; k++) {
    const c = document.createElement('canvas'); c.width = 256; c.height = 256; const x = c.getContext('2d'); const id = x.createImageData(256, 256); const r = rng(k + 11);
    for (let i = 0; i < id.data.length; i += 4) { const v = 128 + (r() - 0.5) * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
    x.putImageData(id, 0, 0); grains.push(c);
  }
  // bo phong cach ngach (pack): font, mau canh, ham ve rieng
  E.pack = null;
  if (cfg.pack) { try { E.pack = await import(`/packs/${cfg.pack}/pack.js`); if (E.pack.init) await E.pack.init(E); } catch (e) { window.__bootError = `Khong nap duoc pack ${cfg.pack}: ${e.stack || e}`; return; } }
  // anh ngoai trong <du an>/anh/
  for (const a of await getJSON(`/__assets?proj=${encodeURIComponent(PROJ)}`, [])) ASSETS.set(a.id, a.file);
  // nap canh
  const list = await getJSON(`/__manifest?proj=${encodeURIComponent(PROJ)}`, []);
  const errs = [];
  for (const f of list) { try { await import(`${PROJ}/${f}`); } catch (e) { errs.push(`${f}: ${e.message}`); console.error('IMPORT', f, e); } }
  if ([...E.shots].some((x) => getShot(x.id)?.kind === '3d')) T3 = await import('/engine/three3d.js');
  await document.fonts.load(`800 40px ${FONTS.title}`); await document.fonts.load(`600 40px ${FONTS.body}`); await document.fonts.load(`700 40px ${FONTS.body}`); await document.fonts.load(`italic 700 40px ${FONTS.serif}`);
  await document.fonts.ready;
  const need = new Set(); E.shots.forEach((s, i) => imagesFor(i).forEach((x) => need.add(x)));
  window.__info = { W: pw, H: ph, fps: E.fps, duration: E.duration, frames: Math.ceil(E.duration * E.fps), shots: E.shots.map((s) => ({ id: s.id, start: s.start, end: s.end, line: s.line || '', has: !!defOf(s) })), importErrors: errs, style: cfg.style, missingImages: [...need].filter((x) => !ASSETS.has(x)).sort(), images: need.size };
  window.__ready = true;
}

function shotAt(t) {
  const S = E.shots; for (let i = 0; i < S.length; i++) if (t < S[i].end || i === S.length - 1) return i; return S.length - 1;
}
const BARS = { wide: 2.0, scope: 2.39, none: 0 };
function barH(s) {
  let b = s.bars ?? E.cfg.bars ?? (E.vertical ? 'none' : 'wide');
  if (b === null) b = E.vertical ? 'none' : 'wide';
  const ratio = typeof b === 'number' ? b : BARS[b] ?? 2.0;
  if (!ratio) return 0;
  if (E.vertical) return Math.max(0, (E.H - E.W * 1.25) / 2) * (b === 'scope' ? 0.5 : 0);
  return Math.max(0, (E.H - E.W / ratio) / 2);
}

const defOf = (s) => getShot(s.id) || (s.tpl ? getTemplate(s.tpl) : null);
// cac ma anh ma shot i can: args.img / args.imgs / args.bgImg / args.layers[].img / def.images
function imagesFor(i) {
  const s = E.shots[i]; if (!s) return []; const a = s.args || {}, out = [];
  const add = (x) => { if (x && typeof x === 'string') out.push(x); };
  add(a.img); add(a.bgImg); (a.imgs || []).forEach(add); (a.layers || []).forEach((l) => add(l && l.img)); (a.items || []).forEach((l) => add(l && l.img));
  const d = getShot(s.id); if (d && d.images) d.images.forEach(add);
  return out;
}
const loadImg = (id) => new Promise((res) => { const f = ASSETS.get(id); if (!f) return res(null); const im = new Image(); im.onload = () => (im.decode ? im.decode().catch(() => {}) : Promise.resolve()).then(() => res(im)); im.onerror = () => res(null); im.src = `${PROJ}/${f}`; });
async function ensureImages(ids) {
  const want = new Set(ids);
  for (const id of want) if (!IMG.has(id) && ASSETS.has(id)) { const im = await loadImg(id); if (im) IMG.set(id, im); }
  if (IMG.size > 12) for (const k of [...IMG.keys()]) { if (IMG.size <= 8) break; if (!want.has(k)) IMG.delete(k); }
}

function drawShot(ctx, i, t) {
  const s = E.shots[i], def = defOf(s), lt = t - s.start, dur = s.end - s.start;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height); ctx.setTransform(E.PX, 0, 0, E.PX, 0, 0);
  ctx.fillStyle = '#0c0a10'; ctx.fillRect(0, 0, E.W, E.H);
  const info = { dur, globalT: t, p: clamp(lt / dur), line: s.line || '', shot: s, start: s.start, args: s.args || {}, ...(s.params || {}) };
  if (!def) {
    ctx.fillStyle = '#1a0f14'; ctx.fillRect(0, 0, E.W, E.H);
    text(ctx, s.tpl ? `THIEU MAU ${s.tpl} (${s.id})` : `THIEU SHOT ${s.id}`, E.W / 2, E.H * 0.42, { size: 70, color: '#ff5a5a' });
    text(ctx, (s.scene || s.line || '').slice(0, 90), E.W / 2, E.H * 0.55, { size: 30, font: FONTS.body, weight: 600, color: '#f0d8d8' });
  } else {
    try {
      if (def.kind === '3d') {
        if (!T3) throw new Error('chua nap bo 3D');
        let st = S3.get(s.id);
        if (!st) { for (const [k, v] of S3) { if (S3.size < 2) break; T3.dispose(v.stage); S3.delete(k); } st = def.init(T3, info) || {}; S3.set(s.id, st); }
        def.draw(st, lt, info, T3);
        const c3 = T3.render(st.stage, ctx.canvas.width, ctx.canvas.height);
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(c3, 0, 0); ctx.restore();
        if (def.overlay) def.overlay(ctx, lt, info, st);
      } else def.draw(ctx, lt, info);
    }
    catch (e) { ctx.setTransform(E.PX, 0, 0, E.PX, 0, 0); text(ctx, `LOI ${s.id}: ${e.message}`.slice(0, 120), E.W / 2, E.H / 2, { size: 34, font: FONTS.body, weight: 700, color: '#ff4040' }); console.error('SHOT', s.id, e); }
  }
  ctx.restore();
}

function grade(ctx) {
  const st = (STYLES[E.cfg.style] || STYLES.dusk).grade, w = ctx.canvas.width, h = ctx.canvas.height;
  if (!st) return;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  // tuong phan + bao hoa
  if (st.contrast !== 1 || st.sat !== 1) { pg.setTransform(1, 0, 0, 1, 0, 0); pg.clearRect(0, 0, w, h); pg.drawImage(ctx.canvas, 0, 0); ctx.filter = `contrast(${st.contrast}) saturate(${st.sat})`; ctx.drawImage(pcv, 0, 0); ctx.filter = 'none'; }
  // nang vung toi (lift) va nhuom vung sang (gain)
  ctx.globalCompositeOperation = 'lighten'; ctx.fillStyle = css(st.lift); ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = css(st.gain); ctx.fillRect(0, 0, w, h);
  // vignette
  ctx.globalCompositeOperation = 'source-over';
  const r = Math.hypot(w, h) / 2, vg = ctx.createRadialGradient(w / 2, h / 2, r * 0.45, w / 2, h / 2, r);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, `rgba(0,0,0,${st.vignette})`); ctx.fillStyle = vg; ctx.fillRect(0, 0, w, h);
  // hat nhieu doi moi 2 khung
  ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = st.grain; const gi = grains[Math.floor(E.frame / 2) % grains.length];
  const pat = ctx.createPattern(gi, 'repeat'); ctx.fillStyle = pat; ctx.fillRect(0, 0, w, h);
  ctx.restore();
}

function transition(i, t) {
  const s = E.shots[i], tin = s.in || { type: 'cut' }, lt = t - s.start, d = tin.dur ?? 0.35;
  if (!tin.type || tin.type === 'cut' || lt >= d) return;
  const k = clamp(lt / d), w = cv.width, h = cv.height;
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
  if (tin.type === 'flash' || tin.type === 'dipWhite') { g.fillStyle = `rgba(255,250,240,${1 - ease.out(k)})`; g.fillRect(0, 0, w, h); }
  if (tin.type === 'dip') { g.fillStyle = `rgba(0,0,0,${1 - ease.inOut(k)})`; g.fillRect(0, 0, w, h); }
  if ((tin.type === 'fade' || tin.type === 'whip' || tin.type === 'zoom') && i > 0) {
    const prev = E.shots[i - 1]; drawShot(sg, i - 1, Math.min(prev.end - 0.001, prev.start + (prev.end - prev.start) + lt * 0.5) - 0.0005);
    if (tin.type === 'fade') { g.globalAlpha = 1 - ease.inOut(k); g.drawImage(scv, 0, 0); }
    if (tin.type === 'whip') {
      const dir = tin.dir || 1, off = ease.inOut(k) * w * dir;
      pg.setTransform(1, 0, 0, 1, 0, 0); pg.clearRect(0, 0, w, h); pg.drawImage(cv, 0, 0);
      g.clearRect(0, 0, w, h); g.filter = `blur(${Math.sin(k * Math.PI) * 40 * E.PX}px)`;
      g.drawImage(scv, -off, 0); g.drawImage(pcv, w * dir - off, 0); g.filter = 'none';
    }
    if (tin.type === 'zoom') { const z = 1 + ease.in(k) * 0.6; g.globalAlpha = 1 - ease.inOut(k); g.translate(w / 2, h / 2); g.scale(z, z); g.translate(-w / 2, -h / 2); g.drawImage(scv, 0, 0); }
  }
  g.restore();
}

let lastBar = null;
function bars(i, t) {
  const s = E.shots[i], lt = t - s.start, cur = barH(s);
  const prev = i > 0 ? barH(E.shots[i - 1]) : cur;
  const bh = lerp(prev, cur, ease.inOut(clamp(lt / 0.35))) * E.PX;
  if (bh <= 0.5) return;
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = '#000'; g.fillRect(0, 0, cv.width, bh); g.fillRect(0, cv.height - bh, cv.width, bh); g.restore();
}

function captions(t, i) {
  if (!E.cfg.captions || E.shots[i].captions === false) return;
  const line = E.lines.find((l) => t >= l.start && t <= l.end); if (!line) return;
  const ws = E.words.filter((w) => w.t >= line.start - 0.01 && w.t <= line.end);
  let idx = ws.findIndex((w) => t >= w.t && t < (w.e + 0.15)); if (idx < 0) idx = ws.filter((w) => w.t <= t).length - 1; if (idx < 0) return;
  const cs = E.cfg.captionStyle || 'bold';
  if (E.pack && E.pack.captions && cs !== 'bold') { g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); E.pack.captions(g, ws, idx, t, cs); g.restore(); return; }
  // nhom 3-5 chu dang noi
  const st = Math.floor(idx / 4) * 4, grp = ws.slice(st, st + 4).map((w) => w.w).join(' ').toUpperCase();
  g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0);
  text(g, grp, E.W / 2, E.H * (E.vertical ? 0.79 : 0.86), { size: E.vertical ? 74 : 56, color: '#ffffff', stroke: 12, strokeColor: '#000', spacing: 1 });
  g.restore();
}

window.renderFrame = async function (f, opts = {}) {
  E.frame = f; const t = f / E.fps, i = shotAt(t);
  await ensureImages([...imagesFor(i), ...(i > 0 ? imagesFor(i - 1) : [])]);
  drawShot(g, i, t);
  transition(i, t);
  grade(g);
  bars(i, t);
  captions(t, i);
  // mo dau / ket thuc
  const fi = E.cfg.fadeIn ?? 0.5, fo = E.cfg.fadeOut ?? 0.8;
  const a = Math.max(fi > 0 ? 1 - clamp(t / fi) : 0, fo > 0 ? clamp((t - (E.duration - fo)) / fo) : 0);
  if (a > 0) { g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = `rgba(0,0,0,${a})`; g.fillRect(0, 0, cv.width, cv.height); g.restore(); }
  if (opts.label) { g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.font = `700 ${Math.round(cv.height * 0.035)}px sans-serif`; g.fillStyle = '#0f0'; g.fillText(opts.label, 10, cv.height * 0.05); g.restore(); }
  return cv.toDataURL(opts.png ? 'image/png' : 'image/jpeg', opts.q ?? 0.92);
};
// thumbnail: canh dang ky ten 'thumb' (khong can nam trong shots.json), khong dai den, khong phu de
window.renderThumb = async function (t = 1) {
  const def = getShot('thumb'); if (!def) return null;
  await ensureImages(def.images || []);
  g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); g.fillStyle = '#0c0a10'; g.fillRect(0, 0, E.W, E.H);
  try { def.draw(g, t, { dur: 2, globalT: 0, p: 0.5, line: '', shot: { id: 'thumb' }, start: 0 }); } catch (e) { console.error('SHOT thumb', e); }
  g.restore(); grade(g);
  if (def.overlay) { g.save(); g.setTransform(E.PX, 0, 0, E.PX, 0, 0); try { def.overlay(g, t); } catch (e) { console.error('SHOT thumb', e); } g.restore(); }
  return cv.toDataURL('image/png');
};
window.__setStyle = (st) => { if (st) E.cfg.style = st; };
window.frameAtTime = (t) => Math.round(t * E.fps);
window.shotStillTime = (i, p = 0.5) => { const s = E.shots[i]; return s.start + (s.end - s.start) * p; };

// ghep anh tong hop (contact sheet) ngay trong trinh duyet
window.makeSheet = async function (items, cols = 4, tw = 480) {
  const imgs = await Promise.all(items.map((it) => new Promise((res) => { const im = new Image(); im.onload = () => res({ im, label: it.label }); im.src = it.src; })));
  const th = Math.round(tw * cv.height / cv.width), pad = 10, lab = 26, rows = Math.ceil(imgs.length / cols);
  const c = document.createElement('canvas'); c.width = cols * (tw + pad) + pad; c.height = rows * (th + lab + pad) + pad; const x = c.getContext('2d');
  x.fillStyle = '#111'; x.fillRect(0, 0, c.width, c.height);
  imgs.forEach(({ im, label }, k) => {
    const cx = pad + (k % cols) * (tw + pad), cy = pad + Math.floor(k / cols) * (th + lab + pad);
    x.drawImage(im, cx, cy, tw, th); x.fillStyle = '#e8e8e8'; x.font = '600 15px sans-serif'; x.fillText(label.slice(0, 64), cx + 2, cy + th + 18);
  });
  return c.toDataURL('image/jpeg', 0.88);
};

boot().catch((e) => { window.__bootError = String(e && e.stack || e); });
