// scripts/render_geometry_proof.mjs
// Renders the 5 core 2D illustrated viewpoints side-by-side using Squire chara.js

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(ROOT, '..');
const OUT_DIR = path.join(REPO_ROOT, 'tests', 'evidence', 'v14_1');
fs.mkdirSync(OUT_DIR, { recursive: true });
const OUT_FILE = path.join(OUT_DIR, 'v14_1_multi_view_geometry_proof.png');

const MIME = {
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.json': 'application/json',
  '.html': 'text/html',
  '.css': 'text/css',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
};

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  let rel = decodeURIComponent(u.pathname);
  if (rel.startsWith('/')) rel = rel.slice(1);
  let filePath = path.join(REPO_ROOT, rel);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    console.log('  [404]', u.pathname, '->', filePath);
    res.writeHead(404);
    return res.end('not found');
  }
  res.writeHead(200, {
    'content-type': MIME[path.extname(filePath)] || 'application/octet-stream',
    'cache-control': 'no-store',
  });
  fs.createReadStream(filePath).pipe(res);
});

await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

const htmlContent = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>V14.1 Multi-View 2D Geometry Proof</title>
<style>
  body { margin: 0; background: #0c1017; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; }
  canvas { display: block; width: 1920px; height: 1080px; }
</style>
</head>
<body>
<canvas id="c" width="1920" height="1080"></canvas>
<script type="module">
  import { E } from '/engine/core.js';
  import * as chara from '/packs/squire/chara.js';

  E.W = 1920;
  E.H = 1080;

  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');

  // Background
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, 1920, 1080);

  // Grid lines
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  for (let x = 0; x < 1920; x += 80) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 1080); ctx.stroke();
  }
  for (let y = 0; y < 1080; y += 80) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(1920, y); ctx.stroke();
  }

  // Header Title
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 36px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('V14.1 FULL-VIDEO CINEMATIC CAMERA DIRECTOR — 2D PERSPECTIVE GEOMETRY PROOF', 960, 70);

  ctx.fillStyle = '#94a3b8';
  ctx.font = '20px sans-serif';
  ctx.fillText('Grounded Distinct 2D Vector Silhouettes (packs/squire/chara.js) · Not 2D Zoom/Pan Scale Shuffling', 960, 110);

  const panels = [
    { label: '1. FRONT VIEW', sub: 'Frontal bust, eyes/mouth, pectoral cuirass', view: 'front', x: 210, y: 720, h: 420 },
    { label: '2. PROFILE (RIGHT)', sub: 'Buccula cheek guard, nasal contour, single eye', view: 'profile_right', x: 585, y: 720, h: 420 },
    { label: '3. 3/4 TURN (RIGHT)', sub: 'Asymmetric cheek plates, offset eyes, turned torso', view: 'front_three_quarter_right', x: 960, y: 720, h: 420 },
    { label: '4. REAR VIEW', sub: 'Dome helmet, neck flange, backplate, ZERO eyes/mouth', view: 'rear', x: 1335, y: 720, h: 420 },
    { label: '5. OVER-SHOULDER', sub: 'Foreground rear silhouette occluding target', view: 'over_shoulder', x: 1710, y: 720, h: 420 },
  ];

  panels.forEach((p, idx) => {
    // Card backdrop
    ctx.fillStyle = '#1e293b88';
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(p.x - 170, 150, 340, 860, 16);
    ctx.fill();
    ctx.stroke();

    // Panel title
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(p.label, p.x, 200);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '13px sans-serif';
    ctx.fillText(p.sub, p.x, 230);

    // Ground shadow
    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 40, 100, 20, 0, 0, Math.PI * 2);
    ctx.fill();

    // Draw Character Geometry
    ctx.save();
    if (p.view === 'over_shoulder') {
      // Draw background target character
      chara.soldier(ctx, p.x - 50, p.y - 40, p.h * 0.55, {
        preset: 'consul',
        view: 'front',
        action: 'stand',
        pose: 'stand',
        face: 'determined',
      });
      // Draw foreground occluding soldier (rear view, large scale)
      chara.soldier(ctx, p.x + 60, p.y + 80, p.h * 0.95, {
        preset: 'hastatus',
        view: 'rear',
        action: 'stand',
        pose: 'stand',
      });
    } else {
      chara.soldier(ctx, p.x, p.y, p.h, {
        preset: 'hastatus',
        view: p.view,
        action: 'stand',
        pose: 'stand',
        face: 'determined',
      });
    }
    ctx.restore();

    // Bottom badge
    ctx.fillStyle = '#0ea5e922';
    ctx.strokeStyle = '#0ea5e9';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(p.x - 140, 930, 280, 48, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 14px monospace';
    ctx.fillText('view: "' + p.view + '"', p.x, 960);
  });

  window.__RENDER_DONE = true;
</script>
</body>
</html>`;

const tempHtml = path.join(REPO_ROOT, 'build', 'geometry_proof.html');
fs.mkdirSync(path.dirname(tempHtml), { recursive: true });
fs.writeFileSync(tempHtml, htmlContent, 'utf-8');

console.log('Launching browser to capture multi-view proof...');
let browser;
for (const channel of ['chrome', 'msedge', 'chromium']) {
  try {
    browser = await chromium.launch({ channel, args: ['--disable-dev-shm-usage', '--no-sandbox'] });
    console.log('  Launched browser channel:', channel);
    break;
  } catch (e) {
    // continue
  }
}
if (!browser) {
  browser = await chromium.launch({ args: ['--disable-dev-shm-usage', '--no-sandbox'] });
}
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('console', (m) => console.log('  [browser]', m.type(), m.text()));
page.on('pageerror', (err) => console.error('  [browser-error]', err));
await page.goto('http://127.0.0.1:' + PORT + '/build/geometry_proof.html');
await page.waitForFunction('window.__RENDER_DONE === true', { timeout: 15000 });
await page.waitForTimeout(500);

await page.screenshot({ path: OUT_FILE });
console.log('Successfully saved proof to:', OUT_FILE);

await browser.close();
server.close();
