// render.mjs — H2 2D Studio: ve tung khung hinh bang Chromium chay ngam roi ghep bang ffmpeg.
// Cach dung:
//   node render.mjs --project projects/<ten> --sheet [--scale 0.5]          anh tong hop: 1 khung / shot
//   node render.mjs --project projects/<ten> --stills 3.2,7.5 [--scale 0.5] anh tai cac thoi diem
//   node render.mjs --project projects/<ten> --from 0 --to 30 [--scale 0.5] video xem truoc (build/preview.mp4, co voice)
//   node render.mjs --project projects/<ten> [--workers N]                  ban cuoi (build/video_silent.mp4)
//   node render.mjs --project projects/<ten> --thumb                        anh thumbnail tu canh 'thumb' -> out/thumbnail.png
//   node render.mjs --project projects/<ten> --check --scale 0.25           quet loi toan video, khong xuat file
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
  if (u.pathname === '/favicon.ico') {
    res.writeHead(204);
    return res.end();
  }
  if (u.pathname === '/__assets') { const d = path.join(PROJ, 'anh'); const list = fs.existsSync(d) ? fs.readdirSync(d).filter((f) => /\.(png|jpe?g|webp)$/i.test(f)).sort().map((f) => ({ id: path.parse(f).name, file: 'anh/' + f })) : []; res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(list)); }
  if (u.pathname === '/__manifest') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(listScenes(PROJ))); }
  let file = u.pathname.startsWith('/proj/') ? path.join(PROJ, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    if (u.pathname.includes('/timeline/words.json') || u.pathname.includes('/timeline/lines.json')) {
      res.writeHead(200, { 'content-type': 'application/json' });
      return res.end('[]');
    }
    res.writeHead(404); return res.end('not found');
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

// ---------- trinh duyet
let _cfg = {}; try { _cfg = JSON.parse(fs.readFileSync(path.join(PROJ, 'config.json'), 'utf8')); } catch {}
const gl = args.gl || _cfg.gl || (process.platform === 'linux' && !_cfg.pack ? 'swiftshader' : 'auto');
const LAUNCH = { args: ['--disable-dev-shm-usage', '--font-render-hinting=none', ...(gl === 'swiftshader' ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : [])] };
async function launch() {
  if (process.platform === 'win32' && gl !== 'swiftshader') {
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
  page.on('console', (m) => {
    if (m.type() === 'error') {
      const txt = m.text();
      if (!txt.includes('404') && !txt.includes('/favicon.ico')) console.log('  [trinh duyet]', txt.slice(0, 300));
    }
  });
  page.on('response', (r) => {
    if (r.status() >= 400) {
      const u = r.url();
      if (!u.includes('/timeline/') && !u.includes('favicon.ico')) console.log('  [404 Required]', u.slice(0, 200));
    }
  });
  page.on('pageerror', (e) => console.log('  [loi trang]', String(e).slice(0, 300)));
  const qs = new URLSearchParams({ proj: '/proj', scale: String(SCALE) });
  await page.goto(`http://127.0.0.1:${PORT}/player.html?${qs}`);
  await page.waitForFunction(() => window.__ready || window.__bootError, null, { timeout: 120000 });
  const err = await page.evaluate(() => window.__bootError);
  if (err) throw new Error('Khong khoi dong duoc player: ' + err);
  if (style) await page.evaluate((s) => { window.__setStyle && window.__setStyle(s); }, style);
  const info = await page.evaluate(() => window.__info);
  if (!globalThis.__gpuShown) {
    globalThis.__gpuShown = 1;
    try {
      const r = await page.evaluate(() => {
        const c = document.createElement('canvas').getContext('webgl');
        const e = c && c.getExtension('WEBGL_debug_renderer_info');
        return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : 'khong ro';
      });
      console.log('  Card do hoa dang dung: ' + r);
    } catch {}
  }
  await page.setViewportSize({ width: Math.min(info.W, 4096), height: Math.min(info.H, 4096) });
  return { page, info };
}
const b64 = (d) => Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');

function validateInfo(info) {
  const fatal = [];
  if (!info.shots || info.shots.length === 0) {
    fatal.push('Du an khong co shot nao (story/shots.json rong).');
  }
  const missShots = (info.shots || []).filter((s) => !s.has).map((s) => s.id);
  if (missShots.length > 0) {
    fatal.push(`THIEU ${missShots.length} shot chua co dinh nghia/template: ${missShots.slice(0, 30).join(', ')}${missShots.length > 30 ? ' ...' : ''}`);
  }
  if (info.missingImages && info.missingImages.length > 0) {
    fatal.push(`THIEU ${info.missingImages.length}/${info.images} anh AI (dat vao <du an>/anh/): ${info.missingImages.slice(0, 30).join(', ')}${info.missingImages.length > 30 ? ' ...' : ''}`);
  }
  if (info.importErrors && info.importErrors.length > 0) {
    fatal.push(`LOI NAP FILE CANH:\n${info.importErrors.map((e) => '   - ' + e).join('\n')}`);
  }
  return { ok: fatal.length === 0, fatal, missShots };
}

function report(info) {
  const check = validateInfo(info);
  if (!check.ok) {
    console.error('\n[PREFLIGHT GATE: BLOCKED]');
    check.fatal.forEach((e) => console.error('  ' + e));
  }
  return check;
}

const voicePath = () => { for (const f of ['build/mix.wav', 'timeline/voice.wav']) { const p = path.join(PROJ, f); if (fs.existsSync(p)) return p; } return null; };
function ff(argv) { const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...argv], { stdio: 'inherit' }); if (r.status) throw new Error('ffmpeg loi: exit ' + r.status); }

// ---------- che do
const browser = await launch();
try {
  if (args.thumb) {
    const { page, info } = await openPlayer(browser, args.style);
    const d = await page.evaluate((t) => window.renderThumb(t), +(args.at || 1));
    await page.close();
    if (!d) throw new Error("Chua co canh 'thumb' (registerShot('thumb', ...) trong scenes/shots/).");
    fs.mkdirSync(path.join(PROJ, 'out'), { recursive: true });
    const p = path.join(PROJ, 'out', 'thumbnail.png');
    fs.writeFileSync(p, b64(d));
    const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', p, '-vf', 'scale=1280:-2', path.join(PROJ, 'out', 'thumbnail_1280.jpg')]);
    if (r.status !== 0) throw new Error('Khong tao duoc thumbnail_1280.jpg');
    console.log('  ' + p);
  } else if (args.check) {
    // quet toan video tim loi (khong xuat file)
    const { page, info } = await openPlayer(browser, args.style);
    const check = report(info);
    if (!check.ok) {
      await page.close();
      throw new Error(`PREFLIGHT THAT BAI: ${check.fatal.join('; ')}`);
    }
    const errs = new Set();
    page.on('console', (m) => {
      const txt = m.text();
      if (m.type() === 'error' && /THIEU SHOT|LOI CANH|IMPORT|Uncaught/.test(txt)) errs.add(txt.slice(0, 200));
    });
    page.on('pageerror', (e) => errs.add(String(e).slice(0, 200)));

    const mode = args['check-mode'] || (info.frames > 2000 ? 'fast' : 'full');
    let framesToCheck = [];
    if (mode === 'fast') {
      framesToCheck.push(0);
      for (const s of info.shots) {
        const fStart = Math.min(info.frames - 1, Math.round(s.start * info.fps));
        const fMid = Math.min(info.frames - 1, Math.round((s.start + s.end) / 2 * info.fps));
        const fEnd = Math.min(info.frames - 1, Math.max(0, Math.round(s.end * info.fps) - 1));
        framesToCheck.push(fStart, fMid, fEnd);
      }
      framesToCheck.push(info.frames - 1);
      framesToCheck = [...new Set(framesToCheck)].sort((a, b) => a - b);
    } else {
      for (let f = 0; f < info.frames; f++) framesToCheck.push(f);
    }

    for (const f of framesToCheck) {
      await page.evaluate((f) => window.renderFrame(f, { q: 0.3 }).then(() => 0), f);
      if (errs.size > 0) break;
    }
    await page.close();
    if (errs.size > 0) {
      console.error('LOI:\n' + [...errs].join('\n'));
      throw new Error(`Renderer phat hien ${errs.size} loi khi ve khung.`);
    }
    console.log(`PASS: 0 loi trong ${framesToCheck.length} khung kiem tra (${info.shots.length} shots hop le, che do ${mode}).`);
  } else if (args.sheet || args.stills) {
    const { page, info } = await openPlayer(browser, args.style);
    const check = report(info);
    if (!check.ok) {
      await page.close();
      throw new Error(`Khong the tao contact sheet: ${check.fatal.join('; ')}`);
    }
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
      for (const t of String(args.stills).split(',').map(Number)) {
        const f = Math.round(t * info.fps);
        const src = await page.evaluate((f) => window.renderFrame(f, { png: true }), f);
        fs.mkdirSync(path.join(BUILD, 'stills'), { recursive: true });
        const p = path.join(BUILD, 'stills', `t_${t.toFixed(2)}.png`);
        fs.writeFileSync(p, b64(src));
        console.log('  ' + p);
        items.push({ src, label: `${t}s` });
      }
    }
    const dir = path.join(BUILD, 'sheets'); fs.mkdirSync(dir, { recursive: true });
    for (let k = 0, n = 1; k < items.length; k += 16, n++) {
      const sheet = await page.evaluate(([it]) => window.makeSheet(it, 4, 480), [items.slice(k, k + 16)]);
      const p = path.join(dir, `${args.stills ? 'stills' : 'sheet'}${args.style ? '_' + args.style : ''}_${String(n).padStart(2, '0')}.jpg`);
      fs.writeFileSync(p, b64(sheet));
      console.log('  ' + p);
    }
    await page.close();
  } else {
    // video: xem truoc hoac ban cuoi
    const { page: p0, info } = await openPlayer(browser, args.style);
    const check = report(info);
    await p0.close();
    if (!check.ok) {
      throw new Error(`Khong the render video: ${check.fatal.join('; ')}`);
    }

    const preview = args.from !== undefined || args.to !== undefined;
    const f0 = Math.max(0, Math.round(+(args.from || 0) * info.fps));
    const f1 = Math.min(info.frames, Math.round((args.to !== undefined ? +args.to : info.duration) * info.fps));
    const total = f1 - f0;
    if (total <= 0) throw new Error(`Khoang render khong hop le: ${f0} -> ${f1} (0 khung)`);

    const is4K = info.W >= 3840 || info.H >= 3840 || _cfg.resolution === '2160p';
    const is2K = info.W >= 2560 || info.H >= 2560 || _cfg.resolution === '1440p';
    const is720p = (info.W <= 1280 && info.H <= 720) || _cfg.resolution === '720p';

    // Enforce hard memory-safety limits even if caller passes excessive --workers
    let maxAllowedWorkers = Math.max(1, Math.min(6, Math.floor(os.cpus().length / 2)));
    if (is4K) {
      maxAllowedWorkers = 1;
    } else if (is2K) {
      maxAllowedWorkers = Math.min(2, maxAllowedWorkers);
    }
    const requestedWorkers = args.workers ? +args.workers : maxAllowedWorkers;
    const W = Math.max(1, Math.min(requestedWorkers, maxAllowedWorkers, Math.ceil(total / 48)));

    const maxrate = is4K ? '32M' : is2K ? '16M' : is720p ? '5M' : '8M';
    const bufsize = is4K ? '64M' : is2K ? '32M' : is720p ? '10M' : '16M';
    const crf = String(args.crf || (is4K ? 18 : is2K ? 19 : is720p ? 22 : 20));

    console.log(`Render ${total} khung (${(total / info.fps).toFixed(1)} giay) ${info.W}x${info.H} @${info.fps}fps, ${W} luong (CRF ${crf}, maxrate ${maxrate})`);
    const parts = []; let done = 0; const t0 = Date.now();
    const tick = setInterval(() => { const el = (Date.now() - t0) / 1000, fps = done / Math.max(el, 0.1); console.log(`  ${done}/${total} khung  ${fps.toFixed(2)} khung/giay  da chay ${Math.floor(el / 60)}p${Math.round(el % 60)}s  con lai ~${Math.round((total - done) / Math.max(fps, 0.01) / 60)} phut`); }, 15000);
    const chunk = Math.ceil(total / W);

    try {
      await Promise.all(Array.from({ length: W }, async (_, k) => {
        const a = f0 + k * chunk, b = Math.min(f1, a + chunk); if (a >= b) return;
        const out = path.join(BUILD, `part_${String(k).padStart(2, '0')}.mp4`); parts[k] = out;
        const br = k === 0 ? browser : await launch();
        const { page } = await openPlayer(br, args.style);
        let encError = null;
        const enc = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(info.fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', preview ? 'veryfast' : 'medium', '-crf', crf, '-maxrate', maxrate, '-bufsize', bufsize, '-tune', 'animation', '-pix_fmt', 'yuv420p', '-r', String(info.fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
        enc.on('error', (err) => { encError = err; });
        enc.stdin.on('error', (err) => { if (!encError) encError = err; });

        try {
          for (let f = a; f < b; f++) {
            if (encError) throw encError;
            const d = await page.evaluate((f) => window.renderFrame(f, { q: 0.93 }), f);
            if (!enc.stdin.write(b64(d))) await new Promise((r) => enc.stdin.once('drain', r));
            done++;
          }
          enc.stdin.end();
          const code = await new Promise((r) => enc.on('close', r));
          if (code !== 0 || encError) throw new Error(`FFmpeg worker ${k} failed with code ${code}${encError ? ': ' + encError.message : ''}`);
        } finally {
          await page.close();
          if (br !== browser) await br.close();
        }
      }));
    } finally {
      clearInterval(tick);
    }

    const list = path.join(BUILD, 'parts.txt');
    fs.writeFileSync(list, parts.filter(Boolean).map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join('\n'));
    const silentPartial = path.join(BUILD, preview ? 'preview_silent.partial.mp4' : 'video_silent.partial.mp4');
    const silentFinal = path.join(BUILD, preview ? 'preview_silent.mp4' : 'video_silent.mp4');
    
    // Concat vao file partial
    ff(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-f', 'mp4', silentPartial]);
    parts.filter(Boolean).forEach((p) => { try { fs.unlinkSync(p); } catch {} });
    try { fs.unlinkSync(list); } catch {}

    // Kiem tra file partial hop le truoc khi promote
    if (!fs.existsSync(silentPartial) || fs.statSync(silentPartial).size < 100) {
      throw new Error('File video_silent.partial.mp4 bi rong hoac khong ton tai');
    }
    fs.renameSync(silentPartial, silentFinal);

    // Ghi visual hash de mix.py khong bat render lai neu chi thay doi am thanh/SFX
    try {
      const storyPath = path.join(PROJ, 'story', 'shots.json');
      if (fs.existsSync(storyPath)) {
        const storyData = JSON.parse(fs.readFileSync(storyPath, 'utf8'));
        const vis = (storyData.shots || []).map(s => ({ id: s.id, start: s.start, end: s.end, tpl: s.tpl, args: s.args, scene: s.scene }));
        const crypto = await import('node:crypto');
        const vHash = crypto.createHash('sha256').update(JSON.stringify(vis)).digest('hex');
        fs.writeFileSync(path.join(BUILD, 'visual_hash.txt'), vHash, 'utf8');
      }
    } catch {}

    if (preview) {
      const vp = voicePath(), outp = path.join(BUILD, 'preview.mp4');
      if (vp) ff(['-i', silentFinal, '-ss', String(f0 / info.fps), '-t', String(total / info.fps), '-i', vp, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', outp]);
      else fs.copyFileSync(silentFinal, outp);
      console.log(`\nXong: ${outp}`);
    } else {
      console.log(`\nXong: ${silentFinal}  (${((Date.now() - t0) / 60000).toFixed(1)} phut). Buoc tiep: python tools/mix.py --project ${args.project}`);
    }
  }
} finally { await browser.close(); server.close(); }
