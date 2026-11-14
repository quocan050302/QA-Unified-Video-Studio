// scripts/render_v14_2_proofs.mjs
// V14.2 Multi-Genre 2D Perspective & DEM Geometry Proofs Generator

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(ROOT, '..');
const OUT_DIR = path.join(REPO_ROOT, 'tests', 'evidence', 'v14_2', 'v14_2_geometry_proofs');
fs.mkdirSync(OUT_DIR, { recursive: true });

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

function createHtmlPage(title, sub, imports, drawScript) {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>${title}</title>
<style>
  body { margin: 0; background: #0c1017; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; overflow: hidden; }
  canvas { display: block; width: 1920px; height: 1080px; }
</style>
</head>
<body>
<canvas id="c" width="1920" height="1080"></canvas>
<script type="module">
  import { E } from '/engine/core.js';
  ${imports}

  E.W = 1920;
  E.H = 1080;
  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');

  // Background
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, 1920, 1080);

  // Subtle grid
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
  ctx.font = 'bold 34px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('${title}', 960, 65);

  ctx.fillStyle = '#94a3b8';
  ctx.font = '19px sans-serif';
  ctx.fillText('${sub}', 960, 105);

  ${drawScript}
</script>
</body>
</html>`;
}

// 1. Squire Roman Proof Script
const romanImports = `import * as chara from '/packs/squire/chara.js';`;
const romanDrawScript = `
  const panels = [
    { label: '1. FRONT VIEW', sub: 'Frontal bust, eyes/mouth, pectoral plate', view: 'front', x: 210, y: 720, h: 420 },
    { label: '2. PROFILE (RIGHT)', sub: 'Buccula cheek guard, nasal ridge, single eye', view: 'profile_right', x: 585, y: 720, h: 420 },
    { label: '3. 3/4 TURN (RIGHT)', sub: 'Asymmetric cheek plates, offset eyes, turned torso', view: 'front_three_quarter_right', x: 960, y: 720, h: 420 },
    { label: '4. REAR VIEW', sub: 'Montefortino dome, neck flange, ZERO eyes/mouth', view: 'rear', x: 1335, y: 720, h: 420 },
    { label: '5. OVER-SHOULDER', sub: 'Foreground rear silhouette occluding target', view: 'over_shoulder', x: 1710, y: 720, h: 420 },
  ];

  panels.forEach((p) => {
    ctx.fillStyle = '#1e293b88';
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(p.x - 170, 145, 340, 875, 16);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(p.label, p.x, 190);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '13px sans-serif';
    ctx.fillText(p.sub, p.x, 220);

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 40, 100, 20, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    if (p.view === 'over_shoulder') {
      chara.soldier(ctx, p.x - 50, p.y - 40, p.h * 0.55, {
        preset: 'consul',
        view: 'front',
        action: 'stand',
        pose: 'stand',
        face: 'determined',
      });
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
  });
`;

// 2. Squire Knight & Samurai Proof Script
const knightSamuraiImports = `import * as chara from '/packs/squire/chara.js';`;
const knightSamuraiDrawScript = `
  const panels = [
    {
      label: 'KNIGHT: PROFILE',
      sub: 'Bascinet snout visor, eye-slit, aventail, pollaxe',
      preset: 'knight15',
      view: 'profile_right',
      x: 210, y: 720, h: 420
    },
    {
      label: 'KNIGHT: REAR',
      sub: 'Rear bascinet skull, mail aventail down, back plate',
      preset: 'knight15',
      view: 'rear',
      x: 585, y: 720, h: 420
    },
    {
      label: 'SAMURAI: PROFILE',
      sub: 'Kabuto crest/horns, shikoro neck plates, katana',
      preset: 'samurai',
      view: 'profile_right',
      x: 960, y: 720, h: 420
    },
    {
      label: 'SAMURAI: REAR',
      sub: 'Tiered shikoro neck guard, lacing cords, ZERO face',
      preset: 'samurai',
      view: 'rear',
      x: 1335, y: 720, h: 420
    },
    {
      label: 'CROSS-GENRE OTS',
      sub: 'Foreground Knight rear occluding opposing Samurai',
      preset: 'knight15',
      view: 'over_shoulder',
      x: 1710, y: 720, h: 420
    },
  ];

  panels.forEach((p) => {
    ctx.fillStyle = '#1e293b88';
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(p.x - 170, 145, 340, 875, 16);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 20px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(p.label, p.x, 190);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '13px sans-serif';
    ctx.fillText(p.sub, p.x, 220);

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 40, 100, 20, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    if (p.view === 'over_shoulder') {
      chara.soldier(ctx, p.x - 50, p.y - 40, p.h * 0.55, {
        preset: 'samurai',
        view: 'front',
        action: 'stand',
        pose: 'stand',
        face: 'fierce',
      });
      chara.soldier(ctx, p.x + 60, p.y + 80, p.h * 0.95, {
        preset: 'knight15',
        view: 'rear',
        action: 'stand',
        pose: 'stand',
      });
    } else {
      chara.soldier(ctx, p.x, p.y, p.h, {
        preset: p.preset,
        view: p.view,
        action: 'stand',
        pose: 'stand',
        face: 'fierce',
      });
    }
    ctx.restore();
  });
`;

// 3. DEM Bean Proof Script
const demBeanImports = `import { bean } from '/packs/dem/bean.js';`;
const demBeanDrawScript = `
  const panels = [
    { label: '1. FRONT VIEW', sub: 'Two eyes, centered mouth, symmetrical torso', view: 'front', x: 210, y: 720, h: 400 },
    { label: '2. PROFILE (RIGHT)', sub: 'Single eye, subtle brow/nose contour, trailing ear', view: 'profile_right', x: 585, y: 720, h: 400 },
    { label: '3. 3/4 TURN (RIGHT)', sub: 'Asymmetric eyes/mouth, curved perspective seam', view: 'three_quarter_right', x: 960, y: 720, h: 400 },
    { label: '4. REAR VIEW', sub: 'Back of head/hood, collar seam, ZERO eyes/mouth', view: 'rear', x: 1335, y: 720, h: 400 },
    { label: '5. OVER-SHOULDER', sub: 'Foreground rear Bean observing distant companion', view: 'over_shoulder', x: 1710, y: 720, h: 400 },
  ];

  panels.forEach((p) => {
    ctx.fillStyle = '#1e293b88';
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(p.x - 170, 145, 340, 875, 16);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(p.label, p.x, 190);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '13px sans-serif';
    ctx.fillText(p.sub, p.x, 220);

    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 40, 100, 20, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    if (p.view === 'over_shoulder') {
      bean(ctx, p.x - 50, p.y - 30, p.h * 0.55, {
        view: 'front',
        face: 'neutral',
        pose: 'stand',
        who: 'companion',
      });
      bean(ctx, p.x + 60, p.y + 70, p.h * 0.95, {
        view: 'rear',
        face: 'neutral',
        pose: 'stand',
        who: 'hero',
      });
    } else {
      bean(ctx, p.x, p.y, p.h, {
        view: p.view,
        face: 'neutral',
        pose: 'stand',
        who: 'hero',
      });
    }
    ctx.restore();
  });
`;

const proofs = [
  {
    fileName: 'squire_roman_proof.png',
    title: 'V14.2 SQUIRE ROMAN 2D PERSPECTIVE GEOMETRY PROOF',
    sub: 'Discrete illustrated geometries (front, profile, 3/4, rear, OTS) · True Vector Silhouettes',
    imports: romanImports,
    script: romanDrawScript,
  },
  {
    fileName: 'squire_knight_samurai_proof.png',
    title: 'V14.2 SQUIRE KNIGHT & SAMURAI MULTI-GENRE GEOMETRY PROOF',
    sub: 'Distinct medieval bascinet/aventail and samurai kabuto/shikoro 2D silhouettes in profile & rear',
    imports: knightSamuraiImports,
    script: knightSamuraiDrawScript,
  },
  {
    fileName: 'dem_bean_proof.png',
    title: 'V14.2 DEM SELF-IMPROVEMENT BEAN 2D PERSPECTIVE PROOF',
    sub: 'True DEM perspective views: profile nasal curve, 3/4 asymmetry, rear (ZERO eyes), and OTS',
    imports: demBeanImports,
    script: demBeanDrawScript,
  },
];

const buildDir = path.join(REPO_ROOT, 'build');
fs.mkdirSync(buildDir, { recursive: true });

console.log('[render_v14_2_proofs] Launching Chromium browser channel...');
const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

for (const prf of proofs) {
  const html = createHtmlPage(prf.title, prf.sub, prf.imports, prf.script);
  const htmlFile = path.join(buildDir, `proof_${prf.fileName.replace('.png', '.html')}`);
  fs.writeFileSync(htmlFile, html, 'utf-8');

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });

  page.on('console', (msg) => console.log(`  [browser console] ${msg.text()}`));
  page.on('pageerror', (err) => console.error(`  [browser error] ${err.message}`));

  const url = `http://127.0.0.1:${PORT}/build/${path.basename(htmlFile)}`;
  console.log(`[render_v14_2_proofs] Rendering ${prf.fileName} from ${url}...`);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1000);

  const outPath = path.join(OUT_DIR, prf.fileName);
  await page.screenshot({ path: outPath, type: 'png' });
  const stat = fs.statSync(outPath);
  console.log(`✅ [render_v14_2_proofs] Generated ${prf.fileName} (${(stat.size / 1024).toFixed(1)} KB)`);
  await page.close();
}

await browser.close();
server.close();
console.log('🎉 [render_v14_2_proofs] All V14.2 geometry proofs rendered successfully.');
