// render.mjs — H2 2D Studio: ve tung khung hinh bang Chromium chay ngam roi ghep bang ffmpeg.
// Cach dung:
//   node render.mjs --project projects/<ten> --sheet [--scale 0.5]          anh tong hop: 1 khung / shot
//   node render.mjs --project projects/<ten> --stills 3.2,7.5 [--scale 0.5] anh tai cac thoi diem
//   node render.mjs --project projects/<ten> --from 0 --to 30 [--scale 0.5] video xem truoc (build/preview.mp4, co voice)
//   node render.mjs --project projects/<ten> [--workers N]                  ban cuoi (build/video_silent.mp4)
//   node render.mjs --project projects/<ten> --thumb                        anh thumbnail tu canh 'thumb' -> out/thumbnail.png
//   node render.mjs --project projects/<ten> --check --scale 0.25        quet loi toan video, khong xuat file
// Tuy chon: --style <id> (thu style khac), --at 0.45 (vi tri lay khung trong shot cho --sheet), --crf 18, --gl swiftshader|auto
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const args = {}; process.argv.slice(2).forEach((a, i, arr) => { if (a.startsWith('--')) { const k = a.slice(2); const v = arr[i + 1]; args[k] = v && !v.startsWith('--') ? v : true; } });
if (!args.project) { console.error('Thieu --project projects/<ten>'); process.exit(1); }
const PROJ = path.resolve(args.project);
const SCALE = +(args.scale || 1);
const BUILD = path.join(PROJ, 'build'); fs.mkdirSync(BUILD, { recursive: true });
const MIME = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml' };

// ---------- may chu tinh
function listScenes(dir) {
  const out = []; const base = path.join(dir, 'scenes');
  const walk = (d) => { if (!fs.existsSync(d)) return; for (const f of fs.readdirSync(d).sort()) { const p = path.join(d, f); if (fs.statSync(p).isDirectory()) walk(p); else if (f.endsWith('.js') && !f.startsWith('_')) out.push(path.relative(dir, p).split(path.sep).join('/')); } };
  walk(path.join(base, 'sets')); walk(path.join(base, 'shots'));
  for (const f of fs.existsSync(base) ? fs.readdirSync(base).sort() : []) { if (f.endsWith('.js') && !f.startsWith('_') && f !== 'cast.js') out.push('scenes/' + f); }
  return out;
}
const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/__assets') { const d = path.join(PROJ, 'anh'); const list = fs.existsSync(d) ? fs.readdirSync(d).filter((f) => /\.(png|jpe?g|webp)$/i.test(f)).sort().map((f) => ({ id: path.parse(f).name, file: 'anh/' + f })) : []; res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(list)); }
  if (u.pathname === '/__manifest') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(listScenes(PROJ))); }
  let file = u.pathname.startsWith('/proj/') ? path.join(PROJ, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('not found'); }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

// ---------- trinh duyet
// SwiftShader chi can cho canh 3D (nguoi que What If). Du an dung pack 2D (doodle, dem...) ve bang CPU nhanh hon nhieu lan.
let _cfg = {}; try { _cfg = JSON.parse(fs.readFileSync(path.join(PROJ, 'config.json'), 'utf8')); } catch {}
const gl = args.gl || _cfg.gl || (process.platform === 'linux' && !_cfg.pack ? 'swiftshader' : 'auto');
const LAUNCH = { args: ['--disable-dev-shm-usage', '--font-render-hinting=none', ...(gl === 'swiftshader' ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : [])] };
async function launch() {
  if (process.platform === 'win32' && gl !== 'swiftshader') {
    // Windows co card do hoa: dung Edge / Chrome co san tren may (khong can tai Chromium), ve 3D bang GPU (ANGLE D3D11)
    const gpu = [...LAUNCH.args, '--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization'];
    for (const channel of ['msedge', 'chrome', 'chromium']) {
      try { const b = await chromium.launch({ channel, args: gpu }); console.log('  Trinh ve: ' + channel + ' (GPU)'); return b; } catch (e) { console.log('  (khong mo duoc ' + channel + ')'); }
    }
  }
  try { return await chromium.launch(LAUNCH); }
  catch (e) {
    const base = process.env.PLAYWRIGHT_BROWSERS_PATH; let exe = null;
    if (base && fs.existsSync(base)) for (const d of fs.readdirSync(base)) for (const sub of ['chrome-linux', 'chrome-linux64']) { const c = path.join(base, d, sub, 'chrome'); if (d.startsWith('chromium-') && fs.existsSync(c)) exe = c; }
    if (!exe) throw new Error('Chua co Chromium. Chay: npx playwright install chromium\n' + e.message);
    return await chromium.launch({ ...LAUNCH, executablePath: exe });
  }
}
async function openPlayer(browser, style) {
  const page = await browser.newPage();
  page.on('console', (m) => { if (m.type() === 'error') console.log('  [trinh duyet]', m.text().slice(0, 300)); });
  page.on('response', (r) => { if (r.status() >= 400 && !r.url().includes('/timeline/')) console.log('  [404]', r.url().slice(0, 200)); });
  page.on('pageerror', (e) => console.log('  [loi trang]', String(e).slice(0, 300)));
  const qs = new URLSearchParams({ proj: '/proj', scale: String(SCALE) });
  await page.goto(`http://127.0.0.1:${PORT}/player.html?${qs}`);
  await page.waitForFunction(() => window.__ready || window.__bootError, null, { timeout: 120000 });
  const err = await page.evaluate(() => window.__bootError); if (err) throw new Error('Khong khoi dong duoc player: ' + err);
  if (style) await page.evaluate((s) => { window.__setStyle && window.__setStyle(s); }, style);
  const info = await page.evaluate(() => window.__info);
  if (!globalThis.__gpuShown) { globalThis.__gpuShown = 1; try { const r = await page.evaluate(() => { const c = document.createElement('canvas').getContext('webgl'); const e = c && c.getExtension('WEBGL_debug_renderer_info'); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'khong ro'; }); console.log('  Card do hoa dang dung: ' + r); } catch {} }
  await page.setViewportSize({ width: Math.min(info.W, 4000), height: Math.min(info.H, 4000) });
  return { page, info };
}
const b64 = (d) => Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');
function report(info) {
  const miss = info.shots.filter((s) => !s.has).map((s) => s.id);
  if (miss.length) console.log(`  THIEU ${miss.length} shot: ${miss.slice(0, 30).join(', ')}${miss.length > 30 ? ' ...' : ''}`);
  if (info.missingImages && info.missingImages.length) console.log(`  THIEU ${info.missingImages.length}/${info.images} anh AI (dat vao <du an>/anh/): ${info.missingImages.slice(0, 40).join(', ')}${info.missingImages.length > 40 ? ' ...' : ''}`);
  if (info.importErrors.length) { console.log('  LOI NAP FILE CANH:'); info.importErrors.forEach((e) => console.log('   - ' + e)); }
}
const voicePath = () => { for (const f of ['build/mix.wav', 'timeline/voice.wav']) { const p = path.join(PROJ, f); if (fs.existsSync(p)) return p; } return null; };
function ff(argv) { const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...argv], { stdio: 'inherit' }); if (r.status) throw new Error('ffmpeg loi'); }

// ---------- che do
const browser = await launch();
try {
  if (args.thumb) {
    const { page } = await openPlayer(browser, args.style);
    const d = await page.evaluate((t) => window.renderThumb(t), +(args.at || 1));
    if (!d) throw new Error("Chua co canh 'thumb' (registerShot('thumb', ...) trong scenes/shots/).");
    fs.mkdirSync(path.join(PROJ, 'out'), { recursive: true }); const p = path.join(PROJ, 'out', 'thumbnail.png'); fs.writeFileSync(p, b64(d));
    spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', p, '-vf', 'scale=1280:-2', path.join(PROJ, 'out', 'thumbnail_1280.jpg')]); console.log('  ' + p);
  } else if (args.check) {
    // quet nhanh toan video tim loi (khong xuat file): moi 3 khung ve 1 lan o kich thuoc nho
    const { page, info } = await openPlayer(browser, args.style); report(info);
    const errs = new Set(); page.on('console', (m) => { if (m.type() === 'error' && /SHOT|IMPORT/.test(m.text())) errs.add(m.text().slice(0, 200)); });
    for (let f = 0; f < info.frames; f += 3) await page.evaluate((f) => window.renderFrame(f, { q: 0.3 }).then(() => 0), f);
    console.log(errs.size ? 'LOI:\n' + [...errs].join('\n') : 'Khong co loi trong ' + info.frames + ' khung.');
  } else if (args.sheet || args.stills) {
    const { page, info } = await openPlayer(browser, args.style); report(info);
    const items = [];
    if (args.sheet) {
      const at = +(args.at || 0.45), sel = args.ids ? String(args.ids).split(',') : null;
      for (let i = 0; i < info.shots.length; i++) {
        const s = info.shots[i]; if (sel && !sel.includes(s.id)) continue;
        const t = s.start + (s.end - s.start) * at, f = Math.min(info.frames - 1, Math.round(t * info.fps));
        const src = await page.evaluate((f) => window.renderFrame(f), f);
        items.push({ src, label: `${s.id} ${s.start.toFixed(1)}s ${s.line}` });
      }
    } else {
      for (const t of String(args.stills).split(',').map(Number)) { const f = Math.round(t * info.fps); const src = await page.evaluate((f) => window.renderFrame(f, { png: true }), f); fs.mkdirSync(path.join(BUILD, 'stills'), { recursive: true }); const p = path.join(BUILD, 'stills', `t_${t.toFixed(2)}.png`); fs.writeFileSync(p, b64(src)); console.log('  ' + p); items.push({ src, label: `${t}s` }); }
    }
    const dir = path.join(BUILD, 'sheets'); fs.mkdirSync(dir, { recursive: true });
    for (let k = 0, n = 1; k < items.length; k += 16, n++) {
      const sheet = await page.evaluate(([it]) => window.makeSheet(it, 4, 480), [items.slice(k, k + 16)]);
      const p = path.join(dir, `${args.stills ? 'stills' : 'sheet'}${args.style ? '_' + args.style : ''}_${String(n).padStart(2, '0')}.jpg`); fs.writeFileSync(p, b64(sheet)); console.log('  ' + p);
    }
  } else {
    // video: xem truoc hoac ban cuoi
    const { page: p0, info } = await openPlayer(browser, args.style); report(info); await p0.close();
    const preview = args.from !== undefined || args.to !== undefined;
    const f0 = Math.max(0, Math.round(+(args.from || 0) * info.fps)), f1 = Math.min(info.frames, Math.round((args.to !== undefined ? +args.to : info.duration) * info.fps));
    const total = f1 - f0;
    const W = Math.max(1, Math.min(+(args.workers || Math.max(1, Math.min(6, Math.floor(os.cpus().length / 2)))), Math.ceil(total / 48)));
    console.log(`Render ${total} khung (${(total / info.fps).toFixed(1)} giay) ${info.W}x${info.H} @${info.fps}fps, ${W} luong`);
    const parts = []; let done = 0; const t0 = Date.now();
    const tick = setInterval(() => { const el = (Date.now() - t0) / 1000, fps = done / Math.max(el, 0.1); console.log(`  ${done}/${total} khung  ${fps.toFixed(2)} khung/giay  da chay ${Math.floor(el / 60)}p${Math.round(el % 60)}s  con lai ~${Math.round((total - done) / Math.max(fps, 0.01) / 60)} phut`); }, 15000);
    const chunk = Math.ceil(total / W);
    await Promise.all(Array.from({ length: W }, async (_, k) => {
      const a = f0 + k * chunk, b = Math.min(f1, a + chunk); if (a >= b) return;
      const out = path.join(BUILD, `part_${String(k).padStart(2, '0')}.mp4`); parts[k] = out;
      const br = k === 0 ? browser : await launch();
      const { page } = await openPlayer(br, args.style);
      const enc = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(info.fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', preview ? 'veryfast' : 'medium', '-crf', String(args.crf || 20), '-maxrate', '8M', '-bufsize', '16M', '-tune', 'animation', '-pix_fmt', 'yuv420p', '-r', String(info.fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
      for (let f = a; f < b; f++) {
        const d = await page.evaluate((f) => window.renderFrame(f, { q: 0.93 }), f);
        if (!enc.stdin.write(b64(d))) await new Promise((r) => enc.stdin.once('drain', r));
        done++;
      }
      enc.stdin.end(); await new Promise((r) => enc.on('close', r));
      if (br !== browser) await br.close();
    }));
    clearInterval(tick);
    const list = path.join(BUILD, 'parts.txt'); fs.writeFileSync(list, parts.filter(Boolean).map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join('\n'));
    const silent = path.join(BUILD, preview ? 'preview_silent.mp4' : 'video_silent.mp4');
    ff(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', silent]);
    parts.filter(Boolean).forEach((p) => fs.unlinkSync(p)); fs.unlinkSync(list);
    if (preview) {
      const vp = voicePath(), outp = path.join(BUILD, 'preview.mp4');
      if (vp) ff(['-i', silent, '-ss', String(f0 / info.fps), '-t', String(total / info.fps), '-i', vp, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', outp]);
      else fs.copyFileSync(silent, outp);
      console.log(`\nXong: ${outp}`);
    } else console.log(`\nXong: ${silent}  (${((Date.now() - t0) / 60000).toFixed(1)} phut). Buoc tiep: python tools/mix.py --project ${args.project}`);
  }
} finally { await browser.close(); server.close(); }
