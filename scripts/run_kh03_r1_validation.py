#!/usr/bin/env python3
"""run_kh03_r1_validation.py — Comprehensive Async Gate Suite (G00..G14) for KH-03.0.R1.

Enforces truthful PASS / FAIL / NOT_RUN receipts with zero relaxed assertions:
- G00 BRANCH, G01 STYLE LOCK, G02 2D-ONLY RUNTIME & NETWORK, G03 STORY & BEATS
- G04 NARRATION/EDIT DECOUPLING, G05 PACING PROXIES + CONTROLLED A/B COMPARISON
- G06 REAL PIXEL MOTION PHYSICS (Hook <0.5s, Parabolic Scroll, Sandal Drain Stomp, Gate Closure)
- G07 CAMERA, G08 MP4 QUALITY & NON-REUSE, G09 3-ORDER DETERMINISM (24 frames)
- G10 16 NEGATIVE MUTATIONS + 2 FALSE-POSITIVE GUARDS
- G11 180 SYNTHETIC + 20 REAL RENDERED MP4 BACKTESTS + HONEST MISSING COMPANY-180 RECEIPT
- G12 ISOLATED 81-GATE LEGACY E2E REGRESSION
- G13 3-REPEAT SERIAL VS PARALLEL BENCHMARK + RESOURCE MONITOR
- G14 HUMAN_REVIEW_PENDING EDITORIAL & STYLE SIGN-OFF
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from resource_guard import ResourceMonitor, check_resources, get_disk_info, get_ram_info
from kh03_style_lock import compute_roman_style_digest, load_roman_master_style, validate_roman_style_contract
from kh03_reference_audit import assert_no_reused_demo_assets
from kh03_narration_timeline import align_words_and_lines, pack_narration_into_30s
from kh03_script_beat_director import (
    build_line_shot_crosswalk,
    compose_shot_plan,
    extract_semantic_beats,
    normalize_script_lines,
    schedule_editorial_camera,
    score_pacing_proxies,
    split_beat_into_visual_events,
    validate_shot_plan_contract,
)
from kh03_r1_project_builder import DEFAULT_R1_PROJECT_DIR, THE_MESSAGE_ONE_SECOND_LATE_SCRIPT

RUN_ID = "20261117_080723Z_4ff0"
RUN_DIR = REPO_ROOT / "docs" / "antigravity_runs" / f"KH-03_0_R1_SCRIPT_SHOT_{RUN_ID}"
EVIDENCE_DIR = RUN_DIR / "evidence"
PKT_DIR = RUN_DIR / "preview_packet"
TRACKED_EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / f"kh03_r1_{RUN_ID}"
SCRATCH_DIR = REPO_ROOT / ".test-runs" / f"kh03_r1_{RUN_ID}"

BASELINE_COMMIT = "8d10b6e81b27632769fbf000487794925c6b0937"
SOURCE_PRODUCTION = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"
PROTECTED_REFS = {
    "refs/heads/Production": "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1",
    "refs/heads/fix/Image-Shot": "c96c4f366b873aa3e81a299ab70a330b4adae5ee",
    "refs/heads/feat/modern-2d-cinematic": "688ec5351cf8fbcdb7740420d81e1bbeac4eb727",
}
EXPECTED_STYLE_DIGEST = "1d3209a715bdd38a73f11acf5c5e2cb6974a6a1855d470e590eaa934360e1259"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _extract_frame_rgb(mp4_path: Path, frame_idx: int, out_png: Path, fps: int = 24) -> np.ndarray:
    t_sec = frame_idx / fps + 0.002
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t_sec:.4f}", "-i", str(mp4_path), "-frames:v", "1", str(out_png)],
        check=True,
    )
    arr = np.asarray(Image.open(out_png).convert("RGB"), dtype=np.uint8)
    return arr


def gate_g00_branch() -> Dict[str, Any]:
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(REPO_ROOT), text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    is_base_anc = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"], cwd=str(REPO_ROOT)).returncode == 0
    is_prod_anc = subprocess.run(["git", "merge-base", "--is-ancestor", SOURCE_PRODUCTION, "HEAD"], cwd=str(REPO_ROOT)).returncode == 0
    ls_remote = subprocess.check_output(["git", "ls-remote", "origin"], cwd=str(REPO_ROOT), text=True)
    ref_map = {}
    for ln in ls_remote.splitlines():
        parts = ln.split()
        if len(parts) == 2:
            ref_map[parts[1]] = parts[0]
    protected_ok = all(ref_map.get(r) == h for r, h in PROTECTED_REFS.items())
    ok = branch == "feat/roman-2d-master" and is_base_anc and is_prod_anc and protected_ok
    return {
        "gate": "G00_BRANCH",
        "status": "PASS" if ok else "FAIL",
        "branch": branch,
        "head": head,
        "baseline_ancestor": is_base_anc,
        "production_ancestor": is_prod_anc,
        "protected_refs_verified": {r: ref_map.get(r) for r in PROTECTED_REFS},
    }


def gate_g01_style(proj: Path) -> Dict[str, Any]:
    sb = load_roman_master_style("roman_squire_master.v1")
    sb_res = validate_roman_style_contract(sb)
    diff_cmd = [
        "git", "diff", BASELINE_COMMIT, "--",
        "projects/kh03_roman_last_gap_30s", "projects/squire-mau", "projects/selfimprove-mau",
        "packs/dem", "visual_styles/roman_squire_master/v1/style_bible.json",
        "engine/core.js", "engine/three3d.js",
    ]
    protected_diff = subprocess.check_output(diff_cmd, cwd=str(REPO_ROOT), text=True).strip()
    legacy_chk = subprocess.run(
        ["node", "render.mjs", "--project", "projects/kh03_roman_last_gap_30s", "--check", "--scale", "0.25"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    ok = (
        sb["canonical_digest"] == EXPECTED_STYLE_DIGEST
        and sb_res["valid"]
        and sb_res["digest_verified"]
        and len(protected_diff) == 0
        and legacy_chk.returncode == 0
    )
    return {
        "gate": "G01_STYLE",
        "status": "PASS" if ok else "FAIL",
        "style_digest": sb["canonical_digest"],
        "protected_files_diff_bytes": len(protected_diff),
        "legacy_kh03_render_check_exit": legacy_chk.returncode,
        "style_approved": "HUMAN_REVIEW_PENDING",
    }


def gate_g02_2d_only(proj: Path) -> Dict[str, Any]:
    cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
    js_hits = []
    for p in list((proj / "scenes").rglob("*.js")) + [
        REPO_ROOT / "packs" / "squire" / "roman_master" / "editorial_state.js",
        REPO_ROOT / "packs" / "squire" / "roman_master" / "gate_city_env.js",
        REPO_ROOT / "packs" / "squire" / "roman_master" / "script_shot_renderer.js",
    ]:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"three3d|THREE\.|WebGLRenderer|kind\s*:\s*['\"]3d['\"]", txt):
            js_hits.append(str(p))

    probe_js = SCRATCH_DIR / "probe_2d_runtime.mjs"
    probe_js.write_text(f"""
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {{ chromium }} from 'playwright';

const ROOT = {json.dumps(str(REPO_ROOT))};
const PROJ = {json.dumps(str(proj))};
const reqs = [];
const server = http.createServer((req, res) => {{
  const u = new URL(req.url, 'http://x');
  reqs.push(u.pathname);
  if (u.pathname === '/__assets') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end('[]'); }}
  if (u.pathname === '/__manifest') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end(JSON.stringify(['scenes/shots/gate_message_r1.js'])); }}
  let f = u.pathname.startsWith('/proj/') ? path.join(PROJ, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) {{ res.writeHead(404); return res.end('not found'); }}
  const ext = path.extname(f);
  const MIME = {{ '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png' }};
  res.writeHead(200, {{ 'content-type': MIME[ext] || 'application/octet-stream' }});
  fs.createReadStream(f).pipe(res);
}});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;
const browser = await chromium.launch({{ channel: 'msedge', headless: true, args: ['--disable-dev-shm-usage', '--font-render-hinting=none'] }});
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${{port}}/player.html?proj=/proj&scale=0.25`);
await page.waitForFunction(() => window.__ready === true || window.__bootError);
const bootInfo = await page.evaluate(() => ({{ ready: !!window.__ready, err: window.__bootError || null, info: window.__info, threeLoaded: window.__three3dLoaded }}));
await browser.close();
server.closeAllConnections?.();
server.close();
console.log(JSON.stringify({{ bootInfo, threeRequests: reqs.filter(r => r.includes('three')) }}));
""", encoding="utf-8")
    p_res = subprocess.run(["node", str(probe_js)], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    rt = json.loads(p_res.stdout.strip().splitlines()[-1])
    ok = (
        cfg.get("render_mode") == "canvas2d_only"
        and cfg.get("allow_3d_legacy_fallback") is False
        and not js_hits
        and rt["bootInfo"]["ready"]
        and rt["bootInfo"]["threeLoaded"] is False
        and len(rt["threeRequests"]) == 0
    )
    return {"gate": "G02_2D_ONLY", "status": "PASS" if ok else "FAIL", "static_3d_hits": js_hits, "runtime": rt}


def gate_g03_g04(proj: Path) -> List[Dict[str, Any]]:
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    cw = json.loads((proj / "story" / "shot_to_line_map.json").read_text(encoding="utf-8"))
    cam = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    words = json.loads((proj / "timeline" / "words.json").read_text(encoding="utf-8"))
    snd = json.loads((proj / "story" / "sound_design.json").read_text(encoding="utf-8"))
    px = json.loads((proj / "story" / "pacing_report.json").read_text(encoding="utf-8"))
    vt = {"valid": True, "lines": lines, "words": words}

    val = validate_shot_plan_contract(shot_plan, cw, cam, vt)
    wav_sig, sr = sf.read(str(proj / "timeline" / "voice.wav"), dtype="float32")
    wav_rms = float(np.sqrt(np.mean(wav_sig ** 2)))
    no_1to1_line_key = all("shot_id" not in ln for ln in lines)

    g03_ok = val["valid"] and len(shot_plan["shots"]) >= 12 and px["max_shot_dur_sec"] <= 3.0 and px["repeated_scale_3x_runs"] == 0
    g04_ok = (
        no_1to1_line_key
        and cw["summary"]["one_to_many_count"] >= 1
        and cw["summary"]["many_to_one_count"] >= 1
        and cw["summary"]["mid_sentence_cuts_count"] >= 1
        and cw["summary"]["word_coverage_ratio"] == 1.0
        and snd["global_tempo_scale"] <= 1.15
        and wav_rms > 0.01
    )
    return [
        {
            "gate": "G03_STORY_BEATS",
            "status": "PASS" if g03_ok else "FAIL",
            "shots_count": len(shot_plan["shots"]),
            "total_frames": val["total_frames_covered"],
            "min_dur_sec": px["min_shot_dur_sec"],
            "mean_dur_sec": px["mean_shot_dur_sec"],
            "max_dur_sec": px["max_shot_dur_sec"],
            "repeated_3x_runs": px["repeated_scale_3x_runs"],
        },
        {
            "gate": "G04_NARRATION_EDIT_DECOUPLE",
            "status": "PASS" if g04_ok else "FAIL",
            "no_forced_shot_id_on_lines": no_1to1_line_key,
            "one_to_many_lines": cw["summary"]["one_to_many_count"],
            "many_to_one_shots": cw["summary"]["many_to_one_count"],
            "mid_sentence_cuts": cw["summary"]["mid_sentence_cuts_count"],
            "word_coverage_ratio": cw["summary"]["word_coverage_ratio"],
            "global_tempo_scale": snd["global_tempo_scale"],
            "voice_rms": round(wav_rms, 5),
        },
    ]


def gate_g05_ab_and_proxies(proj: Path) -> Dict[str, Any]:
    """Build real A/B comparison visuals (Old 9-shot + Controlled Same-Script 1:1 vs Script-Beat Director)."""
    old_pilot_shots = json.loads((REPO_ROOT / "projects" / "kh03_roman_last_gap_30s" / "story" / "shots.json").read_text(encoding="utf-8"))["shots"]
    old_durs = [round(s["end"] - s["start"], 3) for s in old_pilot_shots]

    new_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    new_lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    new_px = json.loads((proj / "story" / "pacing_report.json").read_text(encoding="utf-8"))
    new_durs = [round(s["duration"], 3) for s in new_plan["shots"]]

    # Controlled Same-Script 1:1 Baseline (force each line -> 1 shot only on identical gate message script!)
    vt = {"valid": True, "lines": new_lines, "words": json.loads((proj / "timeline" / "words.json").read_text(encoding="utf-8"))}
    beats = extract_semantic_beats(new_lines)
    one_to_one_events = [split_beat_into_visual_events(b, new_lines[i])[0] for i, b in enumerate(beats)]
    ctrl_1to1_plan = compose_shot_plan(beats, vt, one_to_one_events, target_frames=720, fps=24, aspect="9:16", allow_many_to_one_merge=False)
    ctrl_durs = [round(s["duration"], 3) for s in ctrl_1to1_plan["shots"]]
    ctrl_max_gap = max(old_durs)

    # Render A/B pacing timeline & duration histogram PNG chart cleanly in Pillow
    W, H = 1400, 760
    im = Image.new("RGB", (W, H), (22, 19, 17))
    dr = ImageDraw.Draw(im)
    dr.text((28, 18), "KH-03.0.R1 Pacing Comparison: Old 9-Shot 1:1 vs Same-Script 1:1 vs Script-Beat Director (30.0s)", fill=(248, 240, 224))
    dr.text((28, 44), "Note: Proxy pacing metrics only; actual audience viewer retention requires upload analytics (HUMAN_REVIEW_PENDING).", fill=(224, 178, 102))

    # Draw horizontal timelines
    rows_spec = [
        (95, "1) Prior KH-03.0 Pilot (9 shots 1:1 | mean 3.33s | max 4.50s | 3 gaps > 0.75s)", old_pilot_shots, (190, 92, 74)),
        (195, f"2) Controlled Same-Script 1:1 ({len(ctrl_1to1_plan['shots'])} shots 1:1 | mean {round(sum(ctrl_durs)/len(ctrl_durs),2)}s | max {max(ctrl_durs):.2f}s)", ctrl_1to1_plan["shots"], (196, 152, 72)),
        (295, f"3) KH-03.0.R1 Script-Beat Director ({len(new_plan['shots'])} shots decoupled | mean {new_px['mean_shot_dur_sec']}s | max {new_px['max_shot_dur_sec']}s | 0 slow holds)", new_plan["shots"], (88, 168, 114)),
    ]
    tx0, tx1 = 36, 1364
    for y0, title, sh_list, col in rows_spec:
        dr.text((tx0, y0), title, fill=(240, 232, 220))
        bar_y0, bar_y1 = y0 + 24, y0 + 68
        for idx, sh in enumerate(sh_list):
            x0 = tx0 + (sh["start"] / 30.0) * (tx1 - tx0)
            x1 = tx0 + (sh["end"] / 30.0) * (tx1 - tx0) - 2
            shade = (min(255, col[0] + (idx % 2) * 20), min(255, col[1] + (idx % 2) * 20), min(255, col[2] + (idx % 2) * 18))
            dr.rectangle([x0, bar_y0, max(x0 + 4, x1), bar_y1], fill=shade, outline=(25, 20, 18))
            if x1 - x0 > 34:
                dr.text((x0 + 4, bar_y0 + 14), f"S{idx+1}", fill=(255, 255, 255))

    # Plot narration line intervals beneath R1 shots showing deliberate crossings!
    dr.text((tx0, 392), "Independent Narration Windows (L01..L09) — Notice R1 cuts cross inside & across sentence boundaries:", fill=(215, 210, 202))
    for i, ln in enumerate(new_lines):
        x0 = tx0 + (ln["start"] / 30.0) * (tx1 - tx0)
        x1 = tx0 + (ln["end"] / 30.0) * (tx1 - tx0)
        dr.rectangle([x0, 418, x1, 448], fill=(70, 128, 178), outline=(15, 22, 30))
        dr.text((x0 + 4, 426), ln["id"], fill=(255, 255, 255))

    # Histogram panel bottom
    dr.text((tx0, 480), "Shot Duration Buckets: Old 9-Shot vs R1 Script-Driven (15 shots)", fill=(248, 240, 224))
    buckets = [("<1.5s", 0, 1.5), ("1.5-2.2s", 1.5, 2.2), ("2.2-3.0s", 2.2, 3.01), (">=3.0s (Slow)", 3.01, 9.9)]
    for b_idx, (lbl, lo, hi) in enumerate(buckets):
        bx = 60 + b_idx * 320
        c_old = sum(1 for d in old_durs if lo <= d < hi)
        c_new = sum(1 for d in new_durs if lo <= d < hi)
        dr.text((bx, 515), lbl, fill=(230, 224, 214))
        dr.rectangle([bx, 680 - c_old * 18, bx + 48, 680], fill=(190, 92, 74))
        dr.text((bx + 12, 656 - c_old * 18), f"Old:{c_old}", fill=(255, 215, 205))
        dr.rectangle([bx + 64, 680 - c_new * 18, bx + 112, 680], fill=(88, 168, 114))
        dr.text((bx + 76, 656 - c_new * 18), f"R1:{c_new}", fill=(215, 255, 225))

    ab_chart_path = PKT_DIR / "ab_pacing_timeline_and_histogram.png"
    ab_chart_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(ab_chart_path)
    shutil.copy2(ab_chart_path, TRACKED_EVIDENCE_DIR / ab_chart_path.name)

    # Render controlled low-res 0.5x 5-frame comparison on scratch 1:1 same-script project vs R1 around L04/L05 (t=11.8..18.5s)
    ctrl_dir = SCRATCH_DIR / "ab_ctrl_1to1"
    if ctrl_dir.exists():
        shutil.rmtree(ctrl_dir)
    ctrl_dir.mkdir(parents=True, exist_ok=True)
    for sub_dir in ("timeline", "audio", "scenes/shots"):
        shutil.copytree(proj / sub_dir, ctrl_dir / sub_dir)
    shutil.copytree(proj / "story", ctrl_dir / "story")
    shutil.copy2(proj / "config.json", ctrl_dir / "config.json")
    ctrl_shots = {
        "title": "CTRL_1TO1",
        "duration": 30.0,
        "aspect": "9:16",
        "fps": 24,
        "shots": [
            {
                "id": sh["id"],
                "start": sh["start"],
                "end": sh["end"],
                "tpl": "custom",
                "scene": "gate_message_r1",
                "sub_action": sh["sub_action"],
                "location_id": sh["location_id"],
                "framing_scale": sh["framing_scale"],
                "line_ids": sh["line_ids"],
                "in": {"type": "cut"},
            }
            for sh in ctrl_1to1_plan["shots"]
        ],
    }
    _write_json(ctrl_dir / "story" / "shot_plan.json", ctrl_1to1_plan)
    _write_json(ctrl_dir / "story" / "shots.json", ctrl_shots)
    _write_json(ctrl_dir / "story" / "camera_beats.json", schedule_editorial_camera(ctrl_1to1_plan["shots"], aspect="9:16"))
    from kh03_r1_project_builder import _generate_r1_scene_js
    (ctrl_dir / "scenes" / "shots" / "gate_message_r1.js").write_text(_generate_r1_scene_js(ctrl_shots["shots"]), encoding="utf-8")
    subprocess.run(
        ["node", "render.mjs", "--project", str(ctrl_dir), "--stills", "12.0,14.1,16.1,17.8,19.0", "--scale", "0.25"],
        cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["node", "render.mjs", "--project", str(proj), "--stills", "12.0,14.1,16.1,17.8,19.0", "--scale", "0.25"],
        cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL,
    )
    strip = Image.new("RGB", (5 * 270, 2 * 480 + 64), (20, 16, 14))
    sdr = ImageDraw.Draw(strip)
    sdr.text((16, 8), "TOP: Same-Script 1:1 Baseline (drops parabolic scroll & drain-stomp cuts) | BOTTOM: R1 Script-Beat Director (distinct action & scale cuts)", fill=(248, 240, 224))
    for i, ts in enumerate(["12.00", "14.10", "16.10", "17.80", "19.00"]):
        top_im = Image.open(ctrl_dir / "build" / "stills" / f"t_{ts}.png").convert("RGB").resize((270, 480))
        bot_im = Image.open(proj / "build" / "stills" / f"t_{ts}.png").convert("RGB").resize((270, 480))
        strip.paste(top_im, (i * 270, 36))
        strip.paste(bot_im, (i * 270, 520))
    ab_img = PKT_DIR / "ab_identical_script_1to1_vs_director.jpg"
    strip.save(ab_img, quality=90)
    shutil.copy2(ab_img, TRACKED_EVIDENCE_DIR / ab_img.name)

    ok = (
        new_px["mean_shot_dur_sec"] < 2.5
        and new_px["max_shot_dur_sec"] < 3.0
        and len(new_px["narration_gaps_gt_0p75s"]) == 0
        and new_px["subjective_retention_verified"] is False
    )
    return {
        "gate": "G05_RETENTION_PROXY",
        "status": "PASS" if ok else "FAIL",
        "old_9shot": {"shots": 9, "mean_dur": round(statistics.mean(old_durs), 3), "max_dur": max(old_durs)},
        "ctrl_same_script_1to1": {"shots": len(ctrl_durs), "mean_dur": round(statistics.mean(ctrl_durs), 3), "max_dur": max(ctrl_durs)},
        "r1_script_beat": new_px,
        "ab_artifacts": [str(ab_chart_path), str(ab_img)],
    }


def gate_g06_motion_physics(proj: Path, mp4_path: Path) -> Dict[str, Any]:
    """Verify real decoded pixel ROIs/centroids across hook, airborne scroll arc, sandal drain stomp, and gate slam."""
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    shots = {s["sub_action"]: s for s in shot_plan["shots"]}
    tmp = SCRATCH_DIR / "g06_frames"
    tmp.mkdir(parents=True, exist_ok=True)

    # 1. Hook < 0.5s motion: frame 0 vs frame 8
    f0 = _extract_frame_rgb(mp4_path, 0, tmp / "f0.png")
    f8 = _extract_frame_rgb(mp4_path, 8, tmp / "f8.png")
    y0, y1 = int(0.24 * 1920), int(0.60 * 1920)
    hook_mad = float(np.mean(np.abs(f8[y0:y1].astype(np.float32) - f0[y0:y1].astype(np.float32))))

    # 2. Parabolic airborne scroll arc (SH07: track crimson wax seal centroid in airborne corridor y=0.20..0.445H, below white sky clouds!)
    s_arc = shots["airborne_scroll_arc"]
    fa = _extract_frame_rgb(mp4_path, s_arc["frame_start"] + 2, tmp / "arc_0.png")
    fb = _extract_frame_rgb(mp4_path, (s_arc["frame_start"] + s_arc["frame_end"]) // 2, tmp / "arc_mid.png")
    fc = _extract_frame_rgb(mp4_path, s_arc["frame_end"] - 2, tmp / "arc_end.png")

    def seal_centroid(arr):
        y_top = int(0.20 * 1920)
        y_bot = int(0.445 * 1920)
        sub = arr[y_top:y_bot]
        # Crimson wax seal (#c22e29): high R, very low G and B (distinguishes from sky clouds & orange flames)
        mask = (sub[:, :, 0] > 165) & (sub[:, :, 1] < 78) & (sub[:, :, 2] < 78)
        ys, xs = np.where(mask)
        if len(xs) < 15:
            return None
        return float(np.median(xs)), float(np.median(ys)) + y_top

    ca, cb, cc = seal_centroid(fa), seal_centroid(fb), seal_centroid(fc)
    arc_ok = bool(ca and cb and cc and cc[0] > ca[0] + 250 and cb[1] < max(ca[1], cc[1]) - 15)

    # 3. Sandal stomp at drain (SH09: track moving sandal sole/leather strap vertically strictly above fixed scroll at y=0.465H!)
    s_pin = shots["sandal_stomps_scroll_at_drain_edge"]
    pe = _extract_frame_rgb(mp4_path, s_pin["frame_start"] + 3, tmp / "pin_early.png")
    pf = _extract_frame_rgb(mp4_path, int(s_pin["frame_start"] + s_pin["frame_count"] * 0.65), tmp / "pin_land.png")

    def sandal_sole_y(arr):
        sub = arr[int(0.02 * 1920):int(0.46 * 1920), int(0.14 * 1080):int(0.56 * 1080)]
        # Warm leather brown (#8a522c / #573219): distinct from travertine flagstones (#9e886e/#79644d) via high R-B contrast
        leather = (sub[:, :, 0] > 70) & (sub[:, :, 0] < 165) & (sub[:, :, 1] > 35) & (sub[:, :, 1] < 105) & (sub[:, :, 2] < 55)
        ys, _ = np.where(leather)
        return float(np.median(ys)) + int(0.02 * 1920) if len(ys) > 30 else None

    sy_early, sy_land = sandal_sole_y(pe), sandal_sole_y(pf)
    stomp_ok = bool(sy_early and sy_land and sy_land > sy_early + 250)
    # Check dark drain grate sits cleanly to the right (x=0.60..0.86W)
    drain_roi = pf[int(0.40 * 1920):int(0.51 * 1920), int(0.60 * 1080):int(0.86 * 1080)]
    drain_dark_ratio = float(np.mean((drain_roi[:, :, 0] < 45) & (drain_roi[:, :, 1] < 45) & (drain_roi[:, :, 2] < 45)))

    # 4. Monotonic gate closure (bright sunset amber gap inside unobstructed center arch x=0.45..0.52W, y=0.31..0.48H: SH01 -> SH14 bolted shut!)
    s_slam = shots["oak_gate_bolt_slams_home_behind_guard"]
    f_open = _extract_frame_rgb(mp4_path, 4, tmp / "gate_open.png")
    f_shut = _extract_frame_rgb(mp4_path, s_slam["frame_end"] - 2, tmp / "gate_shut_sh14.png")
    def amber_slit_ratio(arr):
        roi = arr[int(0.31 * 1920):int(0.48 * 1920), int(0.45 * 1080):int(0.52 * 1080)]
        return float(np.mean((roi[:, :, 0] > 215) & (roi[:, :, 1] > 145) & (roi[:, :, 2] < 120)))
    amber_start = amber_slit_ratio(f_open)
    amber_end = amber_slit_ratio(f_shut)
    gate_ok = amber_start > 0.25 and amber_end < 0.02

    all_ok = hook_mad >= 2.0 and arc_ok and stomp_ok and drain_dark_ratio > 0.25 and gate_ok
    return {
        "gate": "G06_MOTION_PHYSICS",
        "status": "PASS" if all_ok else "FAIL",
        "hook_0_to_8_mad": round(hook_mad, 3),
        "scroll_arc_centroids": {"start": ca, "mid": cb, "end": cc, "passed": arc_ok},
        "sandal_drain_stomp": {"early_y": sy_early, "land_y": sy_land, "drain_dark_ratio": round(drain_dark_ratio, 3), "passed": stomp_ok},
        "gate_amber_slit": {"open_sh01": round(amber_start, 3), "shut_sh14": round(amber_end, 3), "passed": gate_ok},
    }


def gate_g07_g08(proj: Path, mp4_path: Path) -> List[Dict[str, Any]]:
    cam = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    cshots = cam.get("shots", {})
    cam_ok = all(s["id"] in cshots and 0.9 <= min(k[1] for k in cshots[s["id"]]["zoomKeys"]) <= 1.45 for s in shot_plan["shots"])

    probe = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(mp4_path)], text=True
    ))
    cnt = int(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4_path)], text=True
    ).strip().rstrip(","))
    ebur = subprocess.run(["ffmpeg", "-v", "info", "-i", str(mp4_path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur)[-1])
    tp = float((re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur))[-1])
    vs = next(s for s in probe["streams"] if s["codec_type"] == "video")
    aus = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    non_reuse = assert_no_reused_demo_assets(proj)

    q_ok = (
        vs["width"] == 1080 and vs["height"] == 1920 and cnt == 720
        and abs(float(probe["format"]["duration"]) - 30.0) < 0.1
        and -16.2 <= lufs <= -13.8 and tp <= -1.0 and non_reuse["passed"]
    )
    return [
        {"gate": "G07_CAMERA", "status": "PASS" if cam_ok else "FAIL", "camera_shots_count": len(cshots), "aspect": cam.get("aspect")},
        {
            "gate": "G08_QUALITY",
            "status": "PASS" if q_ok else "FAIL",
            "mp4_sha256": _sha256_file(mp4_path),
            "width": vs["width"], "height": vs["height"], "decoded_frames": cnt,
            "duration": round(float(probe["format"]["duration"]), 3),
            "lufs": lufs, "true_peak_dbtp": tp, "non_reuse_passed": non_reuse["passed"],
        },
    ]


def gate_g09_determinism(proj: Path) -> Dict[str, Any]:
    """Verify exact SHA-256 pixel determinism across forward, reverse, and scrambled frame access + runtime shot_plan mutability."""
    mut_dir = SCRATCH_DIR / "runtime_shotplan_mutant"
    if mut_dir.exists():
        shutil.rmtree(mut_dir)
    for sub in ("timeline", "audio", "scenes/shots"):
        shutil.copytree(proj / sub, mut_dir / sub)
    shutil.copytree(proj / "story", mut_dir / "story")
    shutil.copy2(proj / "config.json", mut_dir / "config.json")
    sp_m = json.loads((mut_dir / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    # Swap frame 250 inside runtime shot_plan.json to render drain stomp instead of cobbles!
    for s in sp_m["shots"]:
        if s["id"] == "SH05":
            s["sub_action"] = "sandal_stomps_scroll_at_drain_edge"
    _write_json(mut_dir / "story" / "shot_plan.json", sp_m)

    probe_det = SCRATCH_DIR / "probe_determinism.mjs"
    probe_det.write_text(f"""
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {{ chromium }} from 'playwright';

const ROOT = {json.dumps(str(REPO_ROOT))};
const PROJ_A = {json.dumps(str(proj))};
const PROJ_B = {json.dumps(str(mut_dir))};

function makeServer(projDir) {{
  const server = http.createServer((req, res) => {{
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/__assets') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end('[]'); }}
    if (u.pathname === '/__manifest') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end(JSON.stringify(['scenes/shots/gate_message_r1.js'])); }}
    let f = u.pathname.startsWith('/proj/') ? path.join(projDir, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) {{ res.writeHead(404); return res.end('not found'); }}
    const MIME = {{ '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png' }};
    res.writeHead(200, {{ 'content-type': MIME[path.extname(f)] || 'application/octet-stream' }});
    fs.createReadStream(f).pipe(res);
  }});
  return server;
}}

const frames = [0, 18, 35, 36, 102, 103, 170, 219, 240, 260, 285, 310, 335, 359, 385, 420, 441, 476, 544, 575, 607, 652, 684, 719];
const rev = [...frames].reverse();
const scr = [441, 0, 684, 240, 35, 575, 170, 719, 310, 102, 285, 607, 36, 385, 219, 544, 18, 420, 652, 103, 476, 335, 260, 359];

const sA = makeServer(PROJ_A);
await new Promise(r => sA.listen(0, '127.0.0.1', r));
const browser = await chromium.launch({{ channel: 'msedge', headless: true, args: ['--disable-dev-shm-usage', '--font-render-hinting=none'] }});
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${{sA.address().port}}/player.html?proj=/proj&scale=0.5`);
await page.waitForFunction(() => window.__ready === true);

async function snap(list) {{
  const out = {{}};
  for (const fr of list) {{
    const durl = await page.evaluate((f) => window.renderFrame(f, {{ png: true }}), fr);
    out[fr] = crypto.createHash('sha256').update(durl).digest('hex');
  }}
  return out;
}}
const hFwd = await snap(frames);
const hRev = await snap(rev);
const hScr = await snap(scr);
const mismatches = frames.filter(f => hFwd[f] !== hRev[f] || hFwd[f] !== hScr[f]);

// Check runtime shot_plan driving: frame 240 (inside SH05) MUST differ when shot_plan.json mutates
const sB = makeServer(PROJ_B);
await new Promise(r => sB.listen(0, '127.0.0.1', r));
const pageB = await browser.newPage();
await pageB.goto(`http://127.0.0.1:${{sB.address().port}}/player.html?proj=/proj&scale=0.5`);
await pageB.waitForFunction(() => window.__ready === true);
const durlMut240 = await pageB.evaluate(() => window.renderFrame(240, {{ png: true }}));
const hMut240 = crypto.createHash('sha256').update(durlMut240).digest('hex');

await browser.close();
sA.closeAllConnections?.();
sB.closeAllConnections?.();
sA.close();
sB.close();
console.log(JSON.stringify({{ checked: frames.length, mismatches, runtimePlanChangedFrame240: hMut240 !== hFwd[240] }}));
""", encoding="utf-8")
    out = subprocess.run(["node", str(probe_det)], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    res = json.loads(out.stdout.strip().splitlines()[-1])
    ok = res["checked"] == 24 and len(res["mismatches"]) == 0 and res["runtimePlanChangedFrame240"] is True
    return {"gate": "G09_DETERMINISM", "status": "PASS" if ok else "FAIL", **res}


def gate_g10_negative_mutations(proj: Path) -> Dict[str, Any]:
    """Run 16 negative mutants + 2 false-positive guards verifying strict rejection & zero false alarm."""
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    cw = json.loads((proj / "story" / "shot_to_line_map.json").read_text(encoding="utf-8"))
    cam = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    words = json.loads((proj / "timeline" / "words.json").read_text(encoding="utf-8"))
    vt = {"valid": True, "lines": lines, "words": words}

    mutants = []
    def rec(name: str, caught: bool, detail: str = ""):
        mutants.append({"name": name, "caught": bool(caught), "detail": detail[:120]})

    # 1. Frame gap
    m1 = copy.deepcopy(shot_plan); m1["shots"][2]["frame_end"] -= 1
    rec("M01_frame_gap", not validate_shot_plan_contract(m1)["valid"])
    # 2. Frame overlap
    m2 = copy.deepcopy(shot_plan); m2["shots"][2]["frame_start"] -= 1
    rec("M02_frame_overlap", not validate_shot_plan_contract(m2)["valid"])
    # 3. 3x repeated framing scale
    m3 = copy.deepcopy(shot_plan)
    for k in (1, 2, 3): m3["shots"][k]["framing_scale"] = "wide_geography"
    rec("M03_3x_identical_scale", not validate_shot_plan_contract(m3)["valid"])
    # 4. Unannotated > 3.05s sluggish hold
    m4 = copy.deepcopy(shot_plan); m4["shots"][0]["frame_end"] = m4["shots"][0]["frame_start"] + 80; m4["shots"][0]["intentional_hold"] = None
    rec("M04_sluggish_gt_3s_hold", not validate_shot_plan_contract(m4)["valid"])
    # 5. Sub-minimum flash shot < 0.25s
    m5 = copy.deepcopy(shot_plan); m5["shots"][0]["frame_end"] = m5["shots"][0]["frame_start"] + 2
    rec("M05_sub_min_flash_shot", not validate_shot_plan_contract(m5)["valid"])
    # 6. Render mode 3D violation
    m6 = copy.deepcopy(shot_plan); m6["render_mode"] = "three3d_hybrid"
    rec("M06_3d_render_mode", not validate_shot_plan_contract(m6)["valid"])
    # 7. Shot kind='3d'
    m7 = copy.deepcopy(shot_plan); m7["shots"][0]["kind"] = "3d"
    rec("M07_shot_kind_3d", not validate_shot_plan_contract(m7)["valid"])
    # 8. Alien style profile
    m8 = copy.deepcopy(shot_plan); m8["style_profile"] = "modern2d_cinematic.v1"
    rec("M08_wrong_style_profile", not validate_shot_plan_contract(m8)["valid"])
    # 9. Orphan word uncovered
    cw9 = copy.deepcopy(cw); cw9["summary"]["word_coverage_ratio"] = 0.85
    rec("M09_uncovered_words", not validate_shot_plan_contract(shot_plan, cw9, cam, vt)["valid"])
    # 10. Zero multi-shot sentences (forced 1:1 collapse)
    cw10 = copy.deepcopy(cw); cw10["summary"]["one_to_many_count"] = 0
    rec("M10_forced_1to1_collapse", not validate_shot_plan_contract(shot_plan, cw10, cam, vt)["valid"])
    # 11. Duplicate shot ID
    m11 = copy.deepcopy(shot_plan); m11["shots"][1]["id"] = m11["shots"][0]["id"]
    rec("M11_duplicate_shot_id", not validate_shot_plan_contract(m11)["valid"])
    # 12. Missing camera beat
    cam12 = copy.deepcopy(cam); cam12["shots"].pop("SH05", None)
    rec("M12_missing_camera_beat", not validate_shot_plan_contract(shot_plan, cw, cam12, vt)["valid"])
    # 13. Unlocked non-Roman archetype
    m13 = copy.deepcopy(shot_plan); m13["shots"][0]["actors"] = ["alien_robot"]
    rec("M13_unlocked_archetype", not validate_shot_plan_contract(m13, cw, cam, vt, config={"actor_archetypes": {"alien_robot": "sci_fi_mech"}})["valid"])
    # 14. Total frame sum != 720
    m14 = copy.deepcopy(shot_plan); m14["shots"].pop()
    rec("M14_incomplete_total_frames", not validate_shot_plan_contract(m14)["valid"])
    # 15. Overcompressed >1.15x speech
    tmp_ov = SCRATCH_DIR / "mut15_wav"; tmp_ov.mkdir(parents=True, exist_ok=True)
    p15 = tmp_ov / "L1.wav"
    sf.write(str(p15), np.zeros(48000, dtype=np.float32), 48000)
    caught_15 = False
    try:
        pack_narration_into_30s([{"id": "L1", "text": "x", "wav_path": str(p15), "raw_duration_sec": 40.0, "pause_after_hint_sec": 0.1}], target_duration=30.0, max_stretch=1.15, scratch_dir=tmp_ov)
    except RuntimeError as exc:
        caught_15 = "AUDIO_STRETCH_EXCEEDED" in str(exc)
    rec("M15_tts_overcompression", caught_15)
    # 16. Negation false positive ("missed" / "never opened")
    nb = extract_semantic_beats(normalize_script_lines(["Guard missed the leather satchel completely."]))
    rec("M16_negation_guard", "sandal_catch" not in nb[0]["actions"] and "catch" in nb[0]["negated_verbs"])

    # 2 False-Positive Guards:
    fp1 = validate_shot_plan_contract(shot_plan, cw, cam, vt)
    m_fp2 = copy.deepcopy(shot_plan)
    m_fp2["shots"][-1]["intentional_hold"] = {"enabled": True, "frames": 9, "editorial_justification": "End comic hold"}
    fp2 = validate_shot_plan_contract(m_fp2, cw, cam, vt)
    fp_guards = [
        {"name": "FP1_valid_r1_shot_plan_passes", "passed": fp1["valid"]},
        {"name": "FP2_annotated_intentional_hold_passes", "passed": fp2["valid"]},
    ]
    all_ok = all(m["caught"] for m in mutants) and all(f["passed"] for f in fp_guards)
    return {
        "gate": "G10_NEGATIVE_MUTATIONS",
        "status": "PASS" if all_ok else "FAIL",
        "mutants_caught": f"{sum(m['caught'] for m in mutants)}/{len(mutants)}",
        "false_positive_guards": fp_guards,
        "mutants": mutants,
    }


def _run_synth_case(idx: int) -> Dict[str, Any]:
    rng = random.Random(20261117 + idx)
    templates = [
        "At dusk, courier {name} sprinted past {place} before the heavy oak gate shut.",
        "Inside his leather satchel lay an urgent order stamped with red wax.",
        "Twenty paces short he stumbled over a wet stone—the scroll flew forward.",
        "Guard {guard} lunged and missed. His sandal pinned the parchment before the drain.",
        "Wait.",
        "Breathless, he cracked the crimson seal open.",
        "Four painted words glared back: KEEP THE GATE OPEN.",
        "He yelled.",
        "Too late—the heavy iron bolt slammed home.",
    ]
    names = ["Marcus", "Lucius", "Quintus", "Titus", "Gaius"]
    places = ["torchlit arches", "wet cobbles", "stone pillars", "alley corners"]
    n_lines = rng.choice([7, 8, 9])
    lines_txt = []
    for k in range(n_lines):
        s = templates[k % len(templates)].format(name=rng.choice(names), place=rng.choice(places), guard="Gaius")
        lines_txt.append({"id": f"L{k+1:02d}", "text": s})
    # Deliberately test negation cases on 15% of synthetic runs & tight scripts on others
    if idx % 7 == 0:
        lines_txt[3]["text"] = "The guard did not catch the flying parchment in midair."

    norm = normalize_script_lines(lines_txt)
    dur_total = 0.0
    clips = []
    cursor = 0.08
    t_lines, t_words = [], []
    scale_dur = rng.uniform(0.85, 1.05)
    for ln in norm:
        d = round(max(0.7, len(ln["text"].split()) * 0.28 * scale_dur), 3)
        st = round(cursor, 3)
        en = round(min(29.6, st + d), 3)
        if en <= st + 0.2:
            break
        t_lines.append({**ln, "start": st, "end": en, "duration": round(en - st, 3)})
        toks = ln["text"].split()
        dt_w = (en - st) / max(1, len(toks))
        for wi, w in enumerate(toks):
            t_words.append({"id": f"{ln['id']}_W{wi+1:02d}", "w": w, "t": round(st + wi * dt_w, 3), "e": round(st + (wi + 1) * dt_w, 3)})
        cursor = en + 0.12

    vt = {"valid": True, "lines": t_lines, "words": t_words}
    beats = extract_semantic_beats(t_lines)
    evs = []
    lmap = {l["id"]: l for l in t_lines}
    for b in beats:
        evs.extend(split_beat_into_visual_events(b, lmap[b["line_id"]], min_event_frames=10, aspect="9:16"))
    plan = compose_shot_plan(beats, vt, evs, target_frames=720, fps=24, aspect="9:16", seed=idx)
    cw = build_line_shot_crosswalk(t_lines, plan["shots"], t_words)
    cam = schedule_editorial_camera(plan["shots"], aspect="9:16")
    val = validate_shot_plan_contract(plan, cw, cam, vt)
    return {"idx": idx, "valid": val["valid"], "shots": len(plan["shots"]), "errors": val["errors"]}


def gate_g11_backtest(proj: Path) -> Dict[str, Any]:
    # 1. 180 Synthetic Script Benchmark
    with ThreadPoolExecutor(max_workers=4) as ex:
        synth_results = list(ex.map(_run_synth_case, range(180)))
    synth_pass = sum(1 for r in synth_results if r["valid"])

    # 2. 20 Real Rendered Low-Res MP4 Mini-Runs via render.mjs + ffprobe
    rt_dir = SCRATCH_DIR / "backtest_real20"
    if rt_dir.exists():
        shutil.rmtree(rt_dir)
    rt_dir.mkdir(parents=True, exist_ok=True)

    full_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    full_cam = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    full_lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    full_words = json.loads((proj / "timeline" / "words.json").read_text(encoding="utf-8"))
    real_cases = []
    # Slice 20 overlapping/distinct 2.5s..3.0s real story sub-clips across the Roman corpus -> render real MP4 each!
    for i in range(20):
        cdir = rt_dir / f"case_{i+1:02d}"
        cdir.mkdir(parents=True, exist_ok=True)
        for sub in ("audio", "scenes/shots"):
            shutil.copytree(proj / sub, cdir / sub)
        shutil.copytree(proj / "story", cdir / "story")
        shutil.copytree(proj / "timeline", cdir / "timeline")

        sh_pick = full_plan["shots"][i % len(full_plan["shots"])]
        dur = 2.5
        s_copy = copy.deepcopy(sh_pick)
        s_copy["id"] = "SH01"
        s_copy["start"] = 0.0
        s_copy["end"] = dur
        s_copy["frame_start"] = 0
        s_copy["frame_end"] = 59
        s_copy["frame_count"] = 60
        s_copy["duration"] = dur
        mini_plan = {**full_plan, "total_frames": 60, "duration_sec": dur, "shots": [s_copy]}
        mini_cam = {"schema_version": "kh03.r1.camera_beats.v1", "aspect": "9:16", "shots": {"SH01": full_cam["shots"][sh_pick["id"]]}}
        cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
        cfg["title"] = f"BT_{i+1:02d}"
        _write_json(cdir / "config.json", cfg)
        _write_json(cdir / "story" / "shot_plan.json", mini_plan)
        _write_json(cdir / "story" / "camera_beats.json", mini_cam)
        _write_json(cdir / "story" / "shots.json", {
            "title": cfg["title"], "duration": dur, "aspect": "9:16", "fps": 24,
            "shots": [{"id": "SH01", "start": 0.0, "end": dur, "tpl": "custom", "scene": "gate_message_r1", "sub_action": s_copy["sub_action"], "location_id": s_copy["location_id"], "framing_scale": s_copy["framing_scale"], "in": {"type": "cut"}}],
        })
        from kh03_r1_project_builder import _generate_r1_scene_js
        (cdir / "scenes" / "shots" / "gate_message_r1.js").write_text(_generate_r1_scene_js(mini_plan["shots"]), encoding="utf-8")

        subprocess.run(
            ["node", "render.mjs", "--project", str(cdir), "--workers", "1", "--scale", "0.5"],
            cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        mp4_p = cdir / "build" / "video_silent.mp4"
        nb_frames = int(subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4_p)], text=True
        ).strip().rstrip(","))
        real_cases.append({"case": i + 1, "sub_action": s_copy["sub_action"], "decoded_frames": nb_frames, "passed": nb_frames == 60})

    real_pass = sum(1 for r in real_cases if r["passed"])
    return {
        "gate": "G11_BACKTEST",
        "status": "PASS" if (synth_pass == 180 and real_pass == 20) else "FAIL",
        "synthetic_180": {"total": 180, "passed": synth_pass, "pass_rate": round(synth_pass / 180.0, 4)},
        "real_20_rendered_mp4s": {"total": 20, "passed": real_pass, "cases": real_cases},
        "company_180_real_videos": "NOT_RUN_MISSING_FIXTURE",
    }


def gate_g12_legacy_regression(skip_e2e: bool) -> Dict[str, Any]:
    if skip_e2e:
        return {"gate": "G12_LEGACY_REGRESSION", "status": "NOT_RUN_SKIPPED_FLAG", "note": "Skipped only when --skip-legacy-e2e specified"}
    e2e_scratch = SCRATCH_DIR / "legacy_e2e_scratch"
    e2e_evidence = SCRATCH_DIR / "legacy_e2e_evidence"
    e2e_scratch.mkdir(parents=True, exist_ok=True)
    e2e_evidence.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["QA_RUN_ID"] = "r1_legacy_20261117_080723"
    env["QA_RUN_SCRATCH_DIR"] = str(e2e_scratch)
    env["QA_EVIDENCE_DIR"] = str(e2e_evidence)
    env["QA_PRESERVE_TEST_RUNS"] = "1"

    t0 = time.monotonic()
    res = subprocess.run([sys.executable, "scripts/run_e2e_regression.py"], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)
    dur = round(time.monotonic() - t0, 2)
    (SCRATCH_DIR / "legacy_e2e_stdout.log").write_text((res.stdout or "") + "\n---STDERR---\n" + (res.stderr or ""), encoding="utf-8")
    summary_file = e2e_evidence / "v10" / "v10_execution_ledger.json"
    summary_data = json.loads(summary_file.read_text(encoding="utf-8")) if summary_file.is_file() else {}
    return {
        "gate": "G12_LEGACY_REGRESSION",
        "status": "PASS" if res.returncode == 0 else "FAIL",
        "returncode": res.returncode,
        "duration_sec": dur,
        "isolated_evidence_dir": str(e2e_evidence),
        "log_path": str(SCRATCH_DIR / "legacy_e2e_stdout.log"),
        "verdict_line": next((l for l in res.stdout.splitlines() if "VERDICT:" in l), ""),
        "stderr_tail": (res.stderr or "")[-500:],
        "summary_excerpt": summary_data.get("verdict"),
    }


def gate_g13_perf_and_resources(proj: Path) -> Dict[str, Any]:
    mon = ResourceMonitor(workspace=str(REPO_ROOT), min_disk_gb=5.0, min_ram_gb=1.0, interval_sec=0.5)
    mon.start()
    serial_times, parallel_times = [], []
    bench_dir = SCRATCH_DIR / "perf_bench"
    if bench_dir.exists():
        shutil.rmtree(bench_dir)
    bench_dir.mkdir(parents=True, exist_ok=True)
    for rep in range(3):
        for workers, store in ((1, serial_times), (2, parallel_times)):
            t0 = time.monotonic()
            subprocess.run(
                ["node", "render.mjs", "--project", str(proj), "--from", "0", "--to", "6", "--scale", "0.5", "--workers", str(workers)],
                cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            store.append(round(time.monotonic() - t0, 3))
    mon.stop()
    disk = get_disk_info(str(REPO_ROOT))
    ram = get_ram_info()
    med_s = statistics.median(serial_times)
    med_p = statistics.median(parallel_times)
    return {
        "gate": "G13_PERFORMANCE_DISK_SAFETY",
        "status": "PASS" if (not mon.breached and disk["free_gb"] >= 5.0) else "FAIL",
        "serial_3repeats_sec": serial_times,
        "parallel_2w_3repeats_sec": parallel_times,
        "median_serial_sec": med_s,
        "median_parallel_2w_sec": med_p,
        "speedup_factor": round(med_s / max(0.05, med_p), 3),
        "min_disk_free_gb_observed": min(disk["free_gb"], round(mon.min_free_disk_gb, 2) if mon.min_free_disk_gb < 1e9 else disk["free_gb"]),
        "min_ram_free_gb_observed": min(ram["available_gb"], round(mon.min_avail_ram_gb, 2) if mon.min_avail_ram_gb < 1e9 else ram["available_gb"]),
        "monitor_breached": mon.breached,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(DEFAULT_R1_PROJECT_DIR))
    ap.add_argument("--skip-legacy-e2e", action="store_true")
    args = ap.parse_args()

    proj = Path(args.project).resolve()
    mp4_path = proj / "out" / f"{json.loads((proj / 'config.json').read_text(encoding='utf-8'))['title']}.mp4"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    TRACKED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    gates: List[Dict[str, Any]] = []
    gates.append(gate_g00_branch())
    gates.append(gate_g01_style(proj))
    gates.append(gate_g02_2d_only(proj))
    gates.extend(gate_g03_g04(proj))
    gates.append(gate_g05_ab_and_proxies(proj))
    gates.append(gate_g06_motion_physics(proj, mp4_path))
    gates.extend(gate_g07_g08(proj, mp4_path))
    gates.append(gate_g09_determinism(proj))
    gates.append(gate_g10_negative_mutations(proj))
    gates.append(gate_g11_backtest(proj))
    gates.append(gate_g12_legacy_regression(args.skip_legacy_e2e))
    gates.append(gate_g13_perf_and_resources(proj))
    gates.append({
        "gate": "G14_EDITORIAL_SIGN_OFF",
        "status": "HUMAN_REVIEW_PENDING",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "note": "Human visual & pacing review of rendered 9:16 MP4 and preview_packet remains pending.",
    })

    tech_gates = [g for g in gates if g["gate"] != "G14_EDITORIAL_SIGN_OFF"]
    tech_pass = all(g["status"] == "PASS" for g in tech_gates)
    verdict = {
        "schema_version": "kh03.r1.master_verdict.v1",
        "run_id": RUN_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(proj),
        "mp4_path": str(mp4_path),
        "technical_gates_all_pass": tech_pass,
        "master_verdict": "TECH_PASS_HUMAN_REVIEW_PENDING" if tech_pass else "TECH_FAIL",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "gates": gates,
    }
    _write_json(EVIDENCE_DIR / "master_verdict.json", verdict)
    _write_json(TRACKED_EVIDENCE_DIR / "master_verdict.json", verdict)
    print(json.dumps({
        "master_verdict": verdict["master_verdict"],
        "summary": [{g["gate"]: g["status"]} for g in gates],
    }, indent=2))
    return 0 if tech_pass else 1


if __name__ == "__main__":
    sys.exit(main())
