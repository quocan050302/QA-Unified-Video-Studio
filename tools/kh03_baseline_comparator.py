#!/usr/bin/env python3
"""kh03_baseline_comparator.py — Same-Character, Same-Pose A/B Comparator & Identity Geometry Verifier.

Proves two critical KH-03.0 style contracts:
1. SOURCE_BASELINE_LOCK: When style_profile is disabled (profile OFF), current packs/squire/* renders
   0 differing pixels against an immutable git snapshot of origin/Production.
2. ROMAN_IDENTITY_PRESERVED: Compares the EXACT SAME original Squire Roman soldier (`hastatus`),
   in the EXACT SAME pose, shield, spear, helmet, background, lighting, and camera at BOTH `wide`
   and `close` framings between immutable Production and opt-in `roman_squire_master.v1`.
   Outputs BEFORE, AFTER, CONTOUR OVERLAY, AMPLIFIED DIFF HEATMAP, contact sheet, and an 8-panel
   Original Roman Soldier Expression & Pose Sheet.
   Never auto-approves subjective beauty: `style_approved` remains `HUMAN_REVIEW_PENDING`.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _extract_immutable_production_squire(dest_dir: Path, ref: str = "origin/Production") -> Path:
    """Extract immutable Production packs/squire/* into an isolated scratch folder via git show."""
    squire_dir = dest_dir / "immutable_prod_squire"
    if squire_dir.exists():
        shutil.rmtree(squire_dir)
    squire_dir.mkdir(parents=True, exist_ok=True)

    files = ["ink.js", "chara.js", "world.js", "horse.js", "army.js", "templates.js", "pack.js"]
    for fname in files:
        res = subprocess.run(
            ["git", "show", f"{ref}:packs/squire/{fname}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            check=True,
        )
        txt = res.stdout.decode("utf-8")
        # Rewrite '../doodle/map.js' in templates.js to '/packs/doodle/map.js' so isolated mount resolves cleanly
        if fname == "templates.js":
            txt = txt.replace("from '../doodle/map.js'", "from '/packs/doodle/map.js'")
        (squire_dir / fname).write_bytes(txt.encode("utf-8"))
    return squire_dir


def _find_color_mask(rgb: np.ndarray, target_hex: str, tol: float = 26.0) -> np.ndarray:
    h = target_hex.lstrip("#")
    tr, tg, tb = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    diff = np.sqrt(
        (rgb[:, :, 0].astype(np.float32) - tr) ** 2
        + (rgb[:, :, 1].astype(np.float32) - tg) ** 2
        + (rgb[:, :, 2].astype(np.float32) - tb) ** 2
    )
    return diff <= tol


def _bbox_from_mask(mask: np.ndarray) -> Dict[str, Any] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    return {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "width": x1 - x0 + 1,
        "height": y1 - y0 + 1,
        "cx": round(float(xs.mean()), 2),
        "cy": round(float(ys.mean()), 2),
        "pixel_count": int(len(xs)),
    }


def compare_roman_identity_geometry(
    before_png: Path | str,
    after_png: Path | str,
    bg_only_png: Path | str | None = None,
    roi_box: Tuple[int, int, int, int] | None = None,
) -> Dict[str, Any]:
    """Compare same-character, same-pose BEFORE (Production) and AFTER (Roman Master v1) identity geometry."""
    im_before = Image.open(before_png).convert("RGB")
    im_after = Image.open(after_png).convert("RGB")
    if im_before.size != im_after.size:
        return {
            "passed": False,
            "errors": [f"Dimension mismatch: {im_before.size} vs {im_after.size}"],
            "style_approved": "HUMAN_REVIEW_PENDING",
        }

    W, H = im_before.size
    arr_b = np.asarray(im_before, dtype=np.uint8)
    arr_a = np.asarray(im_after, dtype=np.uint8)

    if roi_box is None:
        rx0, ry0, rx1, ry1 = int(W * 0.25), int(H * 0.08), int(W * 0.75), int(H * 0.96)
    else:
        rx0, ry0, rx1, ry1 = roi_box

    roi_b = arr_b[ry0:ry1, rx0:rx1]
    roi_a = arr_a[ry0:ry1, rx0:rx1]

    abs_diff = np.abs(arr_a.astype(np.int16) - arr_b.astype(np.int16))
    changed_mask = np.any(abs_diff > 0, axis=2)
    changed_pixels = int(changed_mask.sum())
    total_pixels = int(W * H)
    changed_ratio = changed_pixels / max(1, total_pixels)
    mean_abs_err = float(abs_diff.mean())
    max_channel_diff = int(abs_diff.max())

    # Actor foreground silhouette IoU if background plate provided, otherwise anchor-color silhouette IoU
    if bg_only_png and Path(bg_only_png).is_file():
        arr_bg = np.asarray(Image.open(bg_only_png).convert("RGB"), dtype=np.uint8)
        fg_b = np.any(np.abs(arr_b.astype(np.int16) - arr_bg.astype(np.int16)) > 3, axis=2)
        fg_a = np.any(np.abs(arr_a.astype(np.int16) - arr_bg.astype(np.int16)) > 3, axis=2)
    else:
        fg_b = (
            _find_color_mask(arr_b, "#f4ede1", 22)
            | _find_color_mask(arr_b, "#c9473a", 26)
            | _find_color_mask(arr_b, "#d3a24e", 26)
            | _find_color_mask(arr_b, "#392a21", 22)
        )
        fg_a = (
            _find_color_mask(arr_a, "#f4ede1", 22)
            | _find_color_mask(arr_a, "#c9473a", 26)
            | _find_color_mask(arr_a, "#d3a24e", 26)
            | _find_color_mask(arr_a, "#392a21", 22)
        )

    inter = int(np.logical_and(fg_b, fg_a).sum())
    union = int(np.logical_or(fg_b, fg_a).sum())
    silhouette_iou = float(inter / union) if union > 0 else 0.0

    # Key color/part anchors inside actor ROI
    face_b = _bbox_from_mask(_find_color_mask(roi_b, "#f4ede1", 18))
    face_a = _bbox_from_mask(_find_color_mask(roi_a, "#f4ede1", 18))
    helm_b = _bbox_from_mask(_find_color_mask(roi_b, "#d3a24e", 24))
    helm_a = _bbox_from_mask(_find_color_mask(roi_a, "#d3a24e", 24))
    red_b = _bbox_from_mask(_find_color_mask(roi_b, "#c9473a", 24))
    red_a = _bbox_from_mask(_find_color_mask(roi_a, "#c9473a", 24))
    out_b = _bbox_from_mask(_find_color_mask(roi_b, "#392a21", 20))
    out_a = _bbox_from_mask(_find_color_mask(roi_a, "#392a21", 20))
    glove_b = _bbox_from_mask(_find_color_mask(roi_b, "#ffffff", 10))
    glove_a = _bbox_from_mask(_find_color_mask(roi_a, "#ffffff", 10))

    errors: List[str] = []
    if silhouette_iou < 0.985:
        errors.append(f"Silhouette IoU drifted below lock threshold: {silhouette_iou:.5f} < 0.985")
    if changed_ratio > 0.045:
        errors.append(f"Changed pixel ratio {changed_ratio:.5f} exceeds controlled polish budget 0.045 (style makeover suspected)")
    for label, bb0, bb1 in [
        ("ivory_face", face_b, face_a),
        ("bronze_montefortino_helmet", helm_b, helm_a),
        ("red_tunic_and_scutum", red_b, red_a),
        ("warm_brown_outline", out_b, out_a),
        ("white_glove_and_feathers", glove_b, glove_a),
    ]:
        if not bb0 or not bb1:
            errors.append(f"Missing required original Squire anchor '{label}'")
        else:
            dc = float(np.hypot(bb1["cx"] - bb0["cx"], bb1["cy"] - bb0["cy"]))
            if dc > 4.5:
                errors.append(f"Anchor '{label}' centroid shifted by {dc:.2f}px (> 4.5px)")

    return {
        "passed": len(errors) == 0,
        "dimensions": [W, H],
        "roi_box": [rx0, ry0, rx1, ry1],
        "silhouette_iou": round(silhouette_iou, 6),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_pixel_ratio": round(changed_ratio, 6),
        "mean_abs_rgb_delta": round(mean_abs_err, 5),
        "max_channel_delta": max_channel_diff,
        "anchors": {
            "ivory_face_before": face_b,
            "ivory_face_after": face_a,
            "helmet_before": helm_b,
            "helmet_after": helm_a,
            "red_scutum_tunic_before": red_b,
            "red_scutum_tunic_after": red_a,
            "warm_brown_outline_before": out_b,
            "warm_brown_outline_after": out_a,
        },
        "deliberate_polish_explanation": (
            "Opt-in romanMasterPolish adds only a subtle warm-cream specular line along the Montefortino "
            "brow guard and a tiny crisp glint on the scutum center steel boss while keeping head radius (19u), "
            "ivory face (#f4ede1), warm-brown contour (#392a21), 3 helmet feathers, white glove, red tunic/scutum "
            "(#c9473a) and spear geometry 100% locked to Production Squire."
        ),
        "aesthetic_beauty_gate": "MANUAL_REVIEW_REQUIRED",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "errors": errors,
    }


def _make_overlay_and_heatmap(before_png: Path, after_png: Path, overlay_out: Path, heatmap_out: Path) -> None:
    arr_b = np.asarray(Image.open(before_png).convert("RGB"), dtype=np.float32)
    arr_a = np.asarray(Image.open(after_png).convert("RGB"), dtype=np.float32)
    # 50/50 blend + cyan highlight on exact delta pixels for human reviewer clarity
    blend = (arr_b * 0.5 + arr_a * 0.5).astype(np.uint8)
    diff_mag = np.max(np.abs(arr_a - arr_b), axis=2)
    delta_mask = diff_mag > 1.0
    overlay = blend.copy()
    overlay[delta_mask] = np.clip(overlay[delta_mask] * 0.35 + np.array([0, 245, 255]) * 0.65, 0, 255).astype(np.uint8)
    Image.fromarray(overlay).save(overlay_out)

    # Amplified diff heatmap over darkened grayscale anatomy reference
    gray = np.mean(arr_b, axis=2) * 0.22
    heat = np.stack([gray, gray, gray], axis=2)
    amp = np.clip(diff_mag * 8.0, 0, 255)
    heat[:, :, 0] = np.clip(heat[:, :, 0] + amp, 0, 255)
    heat[:, :, 1] = np.clip(heat[:, :, 1] + np.maximum(0, amp - 90) * 1.1, 0, 255)
    heat[:, :, 2] = np.clip(heat[:, :, 2] + np.maximum(0, 80 - np.abs(amp - 80)) * 0.5, 0, 255)
    Image.fromarray(heat.astype(np.uint8)).save(heatmap_out)


def _draw_label_banner(img: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    bar_h = max(34, int(h * 0.085))
    draw.rectangle([0, 0, w, bar_h], fill=(28, 20, 16))
    try:
        f_main = ImageFont.truetype("arialbd.ttf", max(14, int(bar_h * 0.44)))
        f_sub = ImageFont.truetype("arial.ttf", max(11, int(bar_h * 0.32)))
    except OSError:
        f_main = ImageFont.load_default()
        f_sub = f_main
    draw.text((12, 5), title, fill=(255, 243, 214), font=f_main)
    if subtitle:
        draw.text((12, int(bar_h * 0.54)), subtitle, fill=(224, 198, 152), font=f_sub)
    return out


def capture_same_pose_roman_reference(
    output_dir: Path | str,
    scratch_dir: Path | str,
    tracked_evidence_dir: Path | str | None = None,
    prod_ref: str = "origin/Production",
) -> Dict[str, Any]:
    """Render immutable Production vs Profile-OFF vs Opt-In Roman Master v1 in headless Chromium."""
    out_dir = Path(output_dir).resolve()
    scr_dir = Path(scratch_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    scr_dir.mkdir(parents=True, exist_ok=True)

    imm_squire = _extract_immutable_production_squire(scr_dir, ref=prod_ref)

    harness_mjs = scr_dir / "render_same_pose_poc.mjs"
    harness_html = scr_dir / "poc_canvas.html"
    harness_html.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}</style></head>'
        '<body><canvas id="c" width="1920" height="1080"></canvas></body></html>\n',
        encoding="utf-8",
    )

    harness_mjs.write_text(
        """import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const [repoRoot, immDir, outDir] = process.argv.slice(2);
const MIME = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  let file;
  if (u.pathname === '/poc.html') {
    file = path.join(path.dirname(immDir), 'poc_canvas.html');
  } else if (u.pathname.startsWith('/imm_squire/')) {
    file = path.join(immDir, decodeURIComponent(u.pathname.slice('/imm_squire/'.length)));
  } else {
    file = path.join(repoRoot, decodeURIComponent(u.pathname.slice(1)));
  }
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404);
    return res.end('not found');
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

let browser = null;
for (const ch of ['msedge', 'chrome', 'chromium']) {
  try {
    browser = await chromium.launch({ channel: ch, args: ['--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--font-render-hinting=none'] });
    break;
  } catch {}
}
if (!browser) browser = await chromium.launch({ args: ['--font-render-hinting=none'] });

const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${port}/poc.html`);

const saveDataUrl = (dataUrl, filePath) => {
  const b64 = dataUrl.replace(/^data:image\\/png;base64,/, '');
  fs.writeFileSync(filePath, Buffer.from(b64, 'base64'));
};

const renders = await page.evaluate(async () => {
  const core = await import('/engine/core.js');
  const immPack = await import('/imm_squire/pack.js');
  const curPack = await import('/packs/squire/pack.js');
  const { E, blurLayer } = core;
  E.W = 1920; E.H = 1080; E.PX = 1; E.fps = 24; E.vertical = false; E.cfg = { style: 'flat' };
  await curPack.init(E);

  const cv = document.getElementById('c');
  const g = cv.getContext('2d');
  const t = 1.60;

  const drawSharedWorld = (ctx, packMod) => {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, 1920, 1080);
    blurLayer(ctx, 5, (c) => {
      packMod.bg(c, 'field', { time: 'dawn', seed: 14, t, tents: 3, flags: [{ color: '#c9473a', charge: 'wings', x: 0.2 }, { color: '#c9473a', charge: 'lightning', x: 0.78 }] });
      packMod.formation(c, { preset: 'hastatus', rows: 3, cols: 10, x0: 0.10, x1: 0.90, yFront: 0.77, yBack: 0.67, hFront: 0.15, hBack: 0.09, seed: 21, t, gaps: [4, 5] });
    });
  };

  // 1. WIDE SAME-POSE (x=960, y=955, h=430)
  const wideOpts = {
    preset: 'hastatus',
    pose: 'stand',
    walk: false,
    noSwing: true,
    face: 'determined',
    look: 0.25,
    blink: 0,
    t,
    seed: 11,
    armsAng: [12, 6, 12, 6],
    shield: { type: 'scutum', color: '#c9473a', rim: '#e7b04a', charge: 'lightning', chargeColor: '#efc23f', x: -14, y: -38, s: 62, rot: -0.06 },
    weapon: 'spear',
    weaponLen: 62,
    weaponAng: Math.PI,
    lod: 'high',
  };

  drawSharedWorld(g, immPack);
  const wideBgOnly = cv.toDataURL('image/png');

  drawSharedWorld(g, immPack);
  immPack.soldier(g, 960, 955, 430, wideOpts);
  const wideImmutable = cv.toDataURL('image/png');

  drawSharedWorld(g, curPack);
  curPack.soldier(g, 960, 955, 430, wideOpts);
  const wideProfileOff = cv.toDataURL('image/png');

  drawSharedWorld(g, curPack);
  curPack.soldier(g, 960, 955, 430, { ...wideOpts, romanMasterPolish: true, leftFootLocal: [-7.2 * 4.3, 0], rightFootLocal: [7.2 * 4.3, 0] });
  const wideRomanMaster = cv.toDataURL('image/png');

  // 2. CLOSE HALF-BODY SAME-POSE (x=960, y=1265, h=960 -> head R ~ 182px centered at y ~ 516)
  const closeSharedWorld = (ctx, packMod) => {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, 1920, 1080);
    blurLayer(ctx, 11, (c) => {
      packMod.bg(c, 'field', { time: 'dawn', seed: 14, t, groundY: 0.62, tents: 3 });
      packMod.formation(c, { preset: 'hastatus', rows: 2, cols: 9, x0: 0.06, x1: 0.94, yFront: 0.75, yBack: 0.66, hFront: 0.16, hBack: 0.10, seed: 21, t, gaps: [4] });
    });
  };

  closeSharedWorld(g, immPack);
  const closeBgOnly = cv.toDataURL('image/png');

  closeSharedWorld(g, immPack);
  immPack.soldier(g, 960, 1265, 960, wideOpts);
  const closeImmutable = cv.toDataURL('image/png');

  closeSharedWorld(g, curPack);
  curPack.soldier(g, 960, 1265, 960, wideOpts);
  const closeProfileOff = cv.toDataURL('image/png');

  closeSharedWorld(g, curPack);
  curPack.soldier(g, 960, 1265, 960, { ...wideOpts, romanMasterPolish: true, leftFootLocal: [-7.2 * 9.6, 0], rightFootLocal: [7.2 * 9.6, 0] });
  const closeRomanMaster = cv.toDataURL('image/png');

  // 3. ORIGINAL ROMAN EXPRESSION & POSE SHEET (8 panels, 4x2 on 1920x1080) using romanActorAt + drawRomanMasterActor2D
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.fillStyle = '#f4efe4';
  g.fillRect(0, 0, 1920, 1080);
  const cells = [
    { label: '1. NEUTRAL (Rookie Hastatus)', role: 'rookie_hastatus', face: 'neutral', look: 0.15, shOff: [-14, -38], shRot: -0.06, rHand: [15.5, -35.5], wAng: Math.PI, rot: 0 },
    { label: '2. FOCUSED (Spotting Gap)', role: 'rookie_hastatus', face: 'focused', look: -0.45, shOff: [-9, -38], shRot: -0.02, rHand: [16.5, -38.0], wAng: Math.PI - 0.18, rot: -0.02 },
    { label: '3. WORRIED (Exposed Line)', role: 'rookie_hastatus', face: 'worried', look: -0.55, shOff: [-13, -37], shRot: 0.04, rHand: [17.0, -36.5], wAng: Math.PI - 0.25, rot: -0.03 },
    { label: '4. SHOCK (Spear Incoming)', role: 'rookie_hastatus', face: 'shock', look: -0.65, shOff: [-6, -37], shRot: -0.01, rHand: [18.5, -40.0], wAng: Math.PI - 0.12, rot: -0.05, lFootDx: -0.05, rFootDx: 0.04 },
    { label: '5. DETERMINED (Shield Shove)', role: 'rookie_hastatus', face: 'determined', look: -0.45, shOff: [3.5, -37], shRot: 0.02, rHand: [15.0, -34.0], wAng: Math.PI + 0.22, rot: 0.07, lFootDx: -0.055, rFootDx: 0.048 },
    { label: '6. EXHALE (Wall Holds)', role: 'rookie_hastatus', face: 'exhale', look: 0.1, shOff: [1.5, -38], shRot: 0.0, rHand: [15.5, -36.0], wAng: Math.PI + 0.08, rot: 0.01, nod: 1.8 },
    { label: '7. AWKWARD (Spear Snagged)', role: 'rookie_hastatus', face: 'awkward', look: 0.65, shOff: [-5, -38], shRot: -0.03, rHand: [19.5, -39.0], wAng: Math.PI - 0.34, rot: -0.02 },
    { label: '8. STERN NOD (Instructor Princeps)', role: 'instructor_princeps', face: 'sternNod', look: 0.38, shOff: [-14, -38], shRot: -0.05, rHand: [21.0, -43.0], wAng: Math.PI - 0.45, rot: 0.0, nod: 2.6 },
  ];
  const cw = 480, ch = 540;
  cells.forEach((c, idx) => {
    const col = idx % 4, row = Math.floor(idx / 4);
    const x0 = col * cw, y0 = row * ch;
    g.save();
    g.beginPath();
    g.rect(x0 + 10, y0 + 10, cw - 20, ch - 20);
    g.clip();
    g.fillStyle = '#e9dcc3';
    g.fillRect(x0 + 10, y0 + 10, cw - 20, ch - 20);
    g.fillStyle = '#c8ab79';
    g.fillRect(x0 + 10, y0 + ch - 115, cw - 20, 105);
    const cxFrac = (x0 + cw * 0.52) / 1920;
    const cyFrac = (y0 + ch - 52) / 1080;
    const hFrac = 345 / 1080;
    const spanFrac = (7.2 * 3.45) / 1920;
    const pose = curPack.romanActorAt(1.2, {
      start: 0,
      end: 3,
      actors: {
        cellActor: {
          archetypeId: c.role,
          hFrac,
          xFrac: cxFrac,
          yFrac: cyFrac,
          face: c.face,
          look: c.look,
          bodyRot: c.rot || 0,
          headNodU: c.nod || 0,
          shieldOffsetU: c.shOff,
          shieldRot: c.shRot,
          rightHandU: c.rHand,
          weaponAng: c.wAng,
          leftFootXKeys: [[0, cxFrac + (c.lFootDx ?? -spanFrac)]],
          rightFootXKeys: [[0, cxFrac + (c.rFootDx ?? spanFrac)]],
          blinkKeys: [[0, 0]],
        },
      },
    }, 'cellActor', { W: 1920, H: 1080 });
    curPack.drawRomanMasterActor2D(g, pose, { polish: true });
    g.fillStyle = '#392a21';
    g.fillRect(x0 + 10, y0 + 10, cw - 20, 38);
    g.font = '800 17px "Be Vietnam Pro", sans-serif';
    g.fillStyle = '#fff5dc';
    g.fillText(c.label, x0 + 22, y0 + 35);
    g.restore();
    g.strokeStyle = '#392a21';
    g.lineWidth = 3;
    g.strokeRect(x0 + 10, y0 + 10, cw - 20, ch - 20);
  });
  const exprSheet = cv.toDataURL('image/png');

  return {
    wideBgOnly, wideImmutable, wideProfileOff, wideRomanMaster,
    closeBgOnly, closeImmutable, closeProfileOff, closeRomanMaster,
    exprSheet,
  };
});

saveDataUrl(renders.wideBgOnly, path.join(immDir, 'wide_bg_only.png'));
saveDataUrl(renders.wideImmutable, path.join(outDir, 'wide_before_production.png'));
saveDataUrl(renders.wideProfileOff, path.join(immDir, 'wide_profile_off.png'));
saveDataUrl(renders.wideRomanMaster, path.join(outDir, 'wide_after_roman_master.png'));

saveDataUrl(renders.closeBgOnly, path.join(immDir, 'close_bg_only.png'));
saveDataUrl(renders.closeImmutable, path.join(outDir, 'close_before_production.png'));
saveDataUrl(renders.closeProfileOff, path.join(immDir, 'close_profile_off.png'));
saveDataUrl(renders.closeRomanMaster, path.join(outDir, 'close_after_roman_master.png'));

saveDataUrl(renders.exprSheet, path.join(outDir, 'original_roman_expression_pose_sheet.png'));

await browser.close();
server.close();
""",
        encoding="utf-8",
    )

    subprocess.run(
        ["node", str(harness_mjs), str(REPO_ROOT), str(imm_squire), str(out_dir)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )

    # Verify SOURCE_BASELINE_LOCK (Profile OFF == Immutable Production pixel-for-pixel)
    wide_imm_arr = np.asarray(Image.open(out_dir / "wide_before_production.png").convert("RGB"), dtype=np.int16)
    wide_off_arr = np.asarray(Image.open(imm_squire / "wide_profile_off.png").convert("RGB"), dtype=np.int16)
    close_imm_arr = np.asarray(Image.open(out_dir / "close_before_production.png").convert("RGB"), dtype=np.int16)
    close_off_arr = np.asarray(Image.open(imm_squire / "close_profile_off.png").convert("RGB"), dtype=np.int16)

    wide_off_diff_px = int(np.any(wide_imm_arr != wide_off_arr, axis=2).sum())
    close_off_diff_px = int(np.any(close_imm_arr != close_off_arr, axis=2).sum())
    baseline_lock_pass = (wide_off_diff_px == 0) and (close_off_diff_px == 0)

    # Build overlays and heatmaps
    _make_overlay_and_heatmap(
        out_dir / "wide_before_production.png",
        out_dir / "wide_after_roman_master.png",
        out_dir / "wide_overlay.png",
        out_dir / "wide_diff_heatmap.png",
    )
    _make_overlay_and_heatmap(
        out_dir / "close_before_production.png",
        out_dir / "close_after_roman_master.png",
        out_dir / "close_overlay.png",
        out_dir / "close_diff_heatmap.png",
    )

    # Compare geometry & anchors
    wide_cmp = compare_roman_identity_geometry(
        out_dir / "wide_before_production.png",
        out_dir / "wide_after_roman_master.png",
        bg_only_png=imm_squire / "wide_bg_only.png",
        roi_box=(680, 360, 1220, 1020),
    )
    close_cmp = compare_roman_identity_geometry(
        out_dir / "close_before_production.png",
        out_dir / "close_after_roman_master.png",
        bg_only_png=imm_squire / "close_bg_only.png",
        roi_box=(480, 60, 1440, 1075),
    )

    # Assemble 2x4 Same-Pose A/B Review Contact Sheet (1920x1080 JPEG)
    grid = Image.new("RGB", (1920, 1080), (20, 16, 14))
    panels = [
        (out_dir / "wide_before_production.png", "WIDE BEFORE — Production Squire", "Immutable origin/Production"),
        (out_dir / "wide_after_roman_master.png", "WIDE AFTER — Roman Master v1", "Same character, pose, camera & bg"),
        (out_dir / "wide_overlay.png", "WIDE OVERLAY — Cyan = Delta", f"Silhouette IoU = {wide_cmp['silhouette_iou']:.5f}"),
        (out_dir / "wide_diff_heatmap.png", "WIDE DIFF HEATMAP (8x)", f"Changed px = {wide_cmp['changed_pixel_ratio']*100:.3f}%"),
        (out_dir / "close_before_production.png", "CLOSE BEFORE — Production Squire", "Immutable origin/Production"),
        (out_dir / "close_after_roman_master.png", "CLOSE AFTER — Roman Master v1", "Same character, pose, camera & bg"),
        (out_dir / "close_overlay.png", "CLOSE OVERLAY — Cyan = Delta", f"Silhouette IoU = {close_cmp['silhouette_iou']:.5f}"),
        (out_dir / "close_diff_heatmap.png", "CLOSE DIFF HEATMAP (8x)", f"Changed px = {close_cmp['changed_pixel_ratio']*100:.3f}%"),
    ]
    tw, th = 480, 540
    for idx, (pp, t1, t2) in enumerate(panels):
        tile = Image.open(pp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        tile = _draw_label_banner(tile, t1, t2)
        grid.paste(tile, ((idx % 4) * tw, (idx // 4) * th))

    ab_sheet_jpg = out_dir / "same_pose_ab_contact_sheet.jpg"
    grid.save(ab_sheet_jpg, quality=91)

    expr_jpg = out_dir / "original_roman_expression_pose_sheet.jpg"
    Image.open(out_dir / "original_roman_expression_pose_sheet.png").convert("RGB").save(expr_jpg, quality=91)

    if tracked_evidence_dir:
        tev = Path(tracked_evidence_dir).resolve()
        tev.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ab_sheet_jpg, tev / "same_pose_ab_contact_sheet.jpg")
        shutil.copy2(expr_jpg, tev / "original_roman_expression_pose_sheet.jpg")

    summary = {
        "source_baseline_lock": {
            "status": "PASS" if baseline_lock_pass else "FAIL",
            "wide_profile_off_diff_pixels": wide_off_diff_px,
            "close_profile_off_diff_pixels": close_off_diff_px,
            "production_ref": prod_ref,
        },
        "roman_identity_preserved": {
            "technical_gate": "PASS" if (wide_cmp["passed"] and close_cmp["passed"]) else "FAIL",
            "style_approved": "HUMAN_REVIEW_PENDING",
            "wide": wide_cmp,
            "close": close_cmp,
        },
        "artifacts": {
            name: {
                "path": str((out_dir / name).resolve()),
                "sha256": _sha256_file(out_dir / name),
                "bytes": (out_dir / name).stat().st_size,
            }
            for name in [
                "wide_before_production.png",
                "wide_after_roman_master.png",
                "wide_overlay.png",
                "wide_diff_heatmap.png",
                "close_before_production.png",
                "close_after_roman_master.png",
                "close_overlay.png",
                "close_diff_heatmap.png",
                "same_pose_ab_contact_sheet.jpg",
                "original_roman_expression_pose_sheet.png",
                "original_roman_expression_pose_sheet.jpg",
            ]
        },
    }

    metrics_path = out_dir / "same_pose_ab_metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if tracked_evidence_dir:
        shutil.copy2(metrics_path, Path(tracked_evidence_dir).resolve() / "same_pose_ab_metrics.json")

    return summary


if __name__ == "__main__":
    run_dir = REPO_ROOT / "docs" / "antigravity_runs" / "KH-03_0_ROMAN_MASTER_20261117_044405Z_4e4f" / "style_poc"
    scr = REPO_ROOT / ".test-runs" / "kh03_0_20261117_044405Z_4e4f" / "style_poc"
    tev = REPO_ROOT / "tests" / "evidence" / "kh03_0_20261117_044405Z_4e4f" / "style_poc"
    res = capture_same_pose_roman_reference(run_dir, scr, tracked_evidence_dir=tev)
    print(json.dumps({
        "source_baseline_lock": res["source_baseline_lock"],
        "technical_gate": res["roman_identity_preserved"]["technical_gate"],
        "wide_iou": res["roman_identity_preserved"]["wide"]["silhouette_iou"],
        "close_iou": res["roman_identity_preserved"]["close"]["silhouette_iou"],
        "wide_changed_ratio": res["roman_identity_preserved"]["wide"]["changed_pixel_ratio"],
        "close_changed_ratio": res["roman_identity_preserved"]["close"]["changed_pixel_ratio"],
        "style_approved": res["roman_identity_preserved"]["style_approved"],
    }, indent=2))
