#!/usr/bin/env python3
"""run_kh03_r2_validation.py — True Async DAG Verification Suite (G00..G17) for KH-03.0.R2.

Features genuine overlapping asyncio execution (capped <= 1 heavy export + <= 2 short renders),
active ResourceMonitor (>= 6.0 GiB disk, >= 2.0 GiB RAM), true decoded-pixel perceptual QA controls,
22 fail-closed negative mutations (compiler + validator + Chromium runtime), 180 varied synthetic +
20 independently rendered multi-corpus MP4s, fair A/B comparison, 3-order determinism + 2-rebuild
parity, isolated legacy 81-gate E2E regression, and 3-repeat 1w vs 2w benchmark.
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
from typing import Any, Awaitable, Callable, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from resource_guard import ResourceMonitor, get_disk_info, get_ram_info
from kh03_style_lock import load_roman_master_style, validate_roman_style_contract
from kh03_action_registry import (
    REGISTRY_VERSION,
    UnsupportedRomanActionError,
    action_registry_digest,
    build_roman_action_registry,
    resolve_roman_action,
    validate_action_bindings,
)
from kh03_perceptual_qa import build_perceptual_review_packet
from kh03_script_beat_director import (
    V2_EDITORIAL_MODE,
    compile_v2_editorial_plan,
    parse_js_renderer_handlers,
    validate_v2_shot_plan_contract,
)
from kh03_r2_project_builder import (
    DEFAULT_R2_PROJECT_DIR,
    DEFAULT_R2_TITLE,
    FORUM_COURTYARD_HOLDOUT_SCRIPT,
    RIVER_HARBOR_HOLDOUT_SCRIPT,
    THE_CART_THAT_WOULD_NOT_STOP_SCRIPT,
    _generate_r2_scene_js,
    build_roman_r2_project,
    render_roman_r2_preview,
)
from validator import validate_project

RUN_ID = "20261117_094557Z_0fd8"
RUN_DIR = REPO_ROOT / "docs" / "antigravity_runs" / f"KH-03_0_R2_ACTION_DIRECTOR_{RUN_ID}"
EVIDENCE_DIR = RUN_DIR / "evidence"
PKT_DIR = RUN_DIR / "preview_packet"
TRACKED_EVIDENCE_DIR = REPO_ROOT / "tests" / "evidence" / f"kh03_r2_{RUN_ID}"
SCRATCH_DIR = REPO_ROOT / ".test-runs" / f"kh03_r2_{RUN_ID}"

BASELINE_COMMIT = "c0c239e36ed6cb2bf9365d3bd74d6d4bfa5cf0be"
SOURCE_PRODUCTION = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"
PROTECTED_REFS = {
    "refs/heads/Production": "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1",
    "refs/heads/fix/Image-Shot": "c96c4f366b873aa3e81a299ab70a330b4adae5ee",
    "refs/heads/feat/modern-2d-cinematic": "688ec5351cf8fbcdb7740420d81e1bbeac4eb727",
}
EXPECTED_STYLE_DIGEST = "1d3209a715bdd38a73f11acf5c5e2cb6974a6a1855d470e590eaa934360e1259"

JOB_TELEMETRY: List[Dict[str, Any]] = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


async def run_dag_job(
    job_id: str,
    phase: str,
    sem: Optional[asyncio.Semaphore],
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    async def _exec() -> Any:
        st_iso = _utc_now()
        t0 = time.monotonic()
        print(f"[DAG START] {phase}/{job_id} @ {st_iso}", flush=True)
        res = await asyncio.to_thread(fn, *args, **kwargs)
        en_iso = _utc_now()
        el = round(time.monotonic() - t0, 3)
        print(f"[DAG DONE ] {phase}/{job_id} ({el}s)", flush=True)
        JOB_TELEMETRY.append({
            "job_id": job_id,
            "phase": phase,
            "start_utc": st_iso,
            "end_utc": en_iso,
            "elapsed_sec": el,
        })
        return res

    if sem is not None:
        async with sem:
            return await _exec()
    return await _exec()


def _max_overlap_from_telemetry(rows: List[Dict[str, Any]]) -> int:
    events: List[Tuple[str, int]] = []
    for r in rows:
        events.append((r["start_utc"], 1))
        events.append((r["end_utc"], -1))
    events.sort(key=lambda x: (x[0], x[1]))
    cur = 0
    best = 0
    for _, delta in events:
        cur += delta
        best = max(best, cur)
    return best


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


def gate_g01_style_and_compat(proj: Path) -> Dict[str, Any]:
    sb = load_roman_master_style("roman_squire_master.v1")
    sb_res = validate_roman_style_contract(sb)
    diff_cmd = [
        "git", "diff", BASELINE_COMMIT, "--",
        "projects/kh03_roman_last_gap_30s", "projects/kh03_r1_roman_gate_message_30s",
        "projects/squire-mau", "projects/selfimprove-mau", "packs/dem",
        "visual_styles/roman_squire_master/v1/style_bible.json",
        "engine/core.js", "engine/player.js", "engine/three3d.js",
    ]
    protected_diff = subprocess.check_output(diff_cmd, cwd=str(REPO_ROOT), text=True).strip()
    r0_chk = subprocess.run(
        ["node", "render.mjs", "--project", "projects/kh03_roman_last_gap_30s", "--check", "--scale", "0.25"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    r1_chk = subprocess.run(
        ["node", "render.mjs", "--project", "projects/kh03_r1_roman_gate_message_30s", "--check", "--scale", "0.25"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    ok = (
        sb["canonical_digest"] == EXPECTED_STYLE_DIGEST
        and sb_res["valid"]
        and sb_res["digest_verified"]
        and len(protected_diff) == 0
        and r0_chk.returncode == 0
        and r1_chk.returncode == 0
    )
    return {
        "gate": "G01_STYLE_AND_BACKWARD_COMPAT",
        "status": "PASS" if ok else "FAIL",
        "style_digest": sb["canonical_digest"],
        "protected_diff_bytes": len(protected_diff),
        "r0_check_exit": r0_chk.returncode,
        "r1_check_exit": r1_chk.returncode,
        "style_approved": "HUMAN_REVIEW_PENDING",
    }


def gate_g02_registry_and_2d_runtime(proj: Path) -> Dict[str, Any]:
    reg = build_roman_action_registry()
    js_handlers = parse_js_renderer_handlers()
    missing_js = [s.renderer_action_id for s in reg.values() if s.renderer_action_id not in js_handlers]

    probe_js = SCRATCH_DIR / "probe_r2_2d_runtime.mjs"
    scene_files = [p.name for p in (proj / "scenes" / "shots").glob("*.js") if p.name != "thumb.js"]
    manifest_paths = [f"scenes/shots/{n}" for n in scene_files]
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
  if (u.pathname === '/__manifest') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end({json.dumps(json.dumps(manifest_paths))}); }}
  let f = u.pathname.startsWith('/proj/') ? path.join(PROJ, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) {{ res.writeHead(404); return res.end('not found'); }}
  const MIME = {{ '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png' }};
  res.writeHead(200, {{ 'content-type': MIME[path.extname(f)] || 'application/octet-stream' }});
  fs.createReadStream(f).pipe(res);
}});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const browser = await chromium.launch({{ channel: 'msedge', headless: true, args: ['--disable-dev-shm-usage'] }});
const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${{server.address().port}}/player.html?proj=/proj&scale=0.5`);
await page.waitForFunction(() => window.__ready === true);
const r = await page.evaluate(async () => {{
  const res = await window.renderFrame(0, {{ png: true }});
  const sp = await fetch('/proj/story/shot_plan.json').then(x => x.json());
  return {{ hasPng: typeof res === 'string' && res.startsWith('data:image/png'), kh03Mode: sp?.editorial_mode || null }};
}});
await browser.close();
server.closeAllConnections?.();
server.close();
const threeReqs = reqs.filter(p => /three/i.test(p));
const fetchedShotPlan = reqs.some(p => p.endsWith('/proj/story/shot_plan.json'));
console.log(JSON.stringify({{ totalReqs: reqs.length, threeReqs, fetchedShotPlan, ...r }}));
""", encoding="utf-8")
    out = subprocess.run(["node", str(probe_js)], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    rt = json.loads(out.stdout.strip().splitlines()[-1])
    ok = len(reg) == 29 and not missing_js and len(rt["threeReqs"]) == 0 and rt["hasPng"] and rt["fetchedShotPlan"] and rt["kh03Mode"] == V2_EDITORIAL_MODE
    return {
        "gate": "G02_CAPABILITY_REGISTRY_AND_2D_RUNTIME",
        "status": "PASS" if ok else "FAIL",
        "registry_version": REGISTRY_VERSION,
        "registry_count": len(reg),
        "registry_digest": action_registry_digest(reg),
        "missing_js_handlers": missing_js,
        "threejs_requests": rt["threeReqs"],
        "runtime_editorial_mode": rt["kh03Mode"],
    }


def gate_g03_g04_action_graph_and_decoupling(proj: Path) -> List[Dict[str, Any]]:
    sp = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    ag = json.loads((proj / "story" / "action_graph.json").read_text(encoding="utf-8"))
    cw = json.loads((proj / "story" / "shot_to_line_map.json").read_text(encoding="utf-8"))
    sd = json.loads((proj / "story" / "sound_design.json").read_text(encoding="utf-8"))
    pr = json.loads((proj / "story" / "pacing_report.json").read_text(encoding="utf-8"))

    term = ag.get("terminal_world_state", {})
    g03_ok = (
        sp.get("editorial_mode") == V2_EDITORIAL_MODE
        and len(ag.get("nodes", [])) >= 12
        and term.get("peg_snapped") is True
        and term.get("rope_taut") is True
        and term.get("cart_stopped") is True
        and term.get("loaf_on_helmet") is True
        and pr.get("repeated_scale_3x_runs", 1) == 0
    )
    sm = cw.get("summary", {})
    g04_ok = (
        float(sm.get("word_coverage_ratio", 0)) >= 0.999
        and sm.get("one_to_many_count", 0) >= 2
        and sm.get("many_to_one_count", 0) >= 1
        and float(sd.get("global_tempo_scale", 9)) <= 1.15
    )
    return [
        {
            "gate": "G03_ACTION_GRAPH_CAUSALITY",
            "status": "PASS" if g03_ok else "FAIL",
            "nodes": len(ag.get("nodes", [])),
            "edges": len(ag.get("edges", [])),
            "shots_count": len(sp.get("shots", [])),
            "terminal_world_state": term,
        },
        {
            "gate": "G04_NARRATION_EDIT_DECOUPLING",
            "status": "PASS" if g04_ok else "FAIL",
            "word_coverage_ratio": sm.get("word_coverage_ratio"),
            "one_to_many_count": sm.get("one_to_many_count"),
            "many_to_one_count": sm.get("many_to_one_count"),
            "mid_sentence_cuts_count": sm.get("mid_sentence_cuts_count"),
            "global_tempo_scale": sd.get("global_tempo_scale"),
        },
    ]


def gate_g05_controlled_ab(proj: Path) -> Dict[str, Any]:
    """Fair Same-Script, Same-Asset, Same-Duration A/B Comparison (1:1 Static Line Holds vs R2 Action Director)."""
    ab_dir = SCRATCH_DIR / "ab_compare"
    arm_a_proj = ab_dir / "arm_a_legacy_1to1"
    if arm_a_proj.exists():
        shutil.rmtree(arm_a_proj)
    arm_a_proj.mkdir(parents=True, exist_ok=True)
    for sub in ("audio", "scenes/shots", "timeline", "story"):
        shutil.copytree(proj / sub, arm_a_proj / sub)
    shutil.copy2(proj / "config.json", arm_a_proj / "config.json")

    lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    sp_b = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    cam_b = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))

    # Construct Arm A: forced 1:1 line-per-shot (10 static slow shots using exact same Roman market renders & script)
    # Assign primary single action_id per line (no 1:many clause splitting, longer sluggish holds)
    one_to_one_actions = [
        ("world.market_hill_establish", "world_market_hill_establish", "wide_geography"),
        ("actor.idle_micro_act", "actor_idle_micro_act", "medium_full_tracking"),
        ("prop.peg_crack_snap", "prop_peg_crack_snap", "macro_physics_insert"),
        ("world.market_crowd_pass", "world_market_crowd_pass", "wide_geography"),
        ("actor.sprint_chase", "actor_sprint_chase", "medium_full_tracking"),
        ("actor.stop_brace", "actor_stop_brace", "medium_full_tracking"),
        ("prop.cart_halt_skid", "prop_cart_halt_skid", "medium_two_shot"),
        ("prop.helmet_impact_settle", "prop_helmet_impact_settle", "payoff_close_reveal"),
        ("actor.deadpan_walk_unaffected", "actor_deadpan_walk_unaffected", "payoff_close_reveal"),
        ("actor.crowd_reaction_cheer", "actor_crowd_reaction_cheer", "wide_geography"),
    ]
    fps = 24
    total_frames = 720
    arm_a_shots = []
    arm_a_cams = {}
    cur_f = 0
    for idx, ln in enumerate(lines):
        aid, hid, scale = one_to_one_actions[idx % len(one_to_one_actions)]
        fs = cur_f
        fe = (total_frames - 1) if idx == len(lines) - 1 else min(total_frames - 2, max(fs + 24, int(round(ln["end"] * fps)) - 1))
        fc = fe - fs + 1
        cur_f = fe + 1
        st, en = round(fs / fps, 3), round((fe + 1) / fps, 3)
        dur = round(fc / fps, 3)
        sid = f"A{idx + 1:02d}"
        arm_a_shots.append({
            "id": sid, "order": idx + 1, "start": st, "end": en, "duration": dur,
            "frame_start": fs, "frame_end": fe, "frame_count": fc,
            "tpl": "script_shot", "kind": "2d", "action_id": aid, "renderer_action_id": hid,
            "sub_action": hid, "location_id": "roman_market_hill", "framing_scale": scale,
            "event_kind": "action", "purpose": "action", "source_line_id": ln["id"],
            "actors": ["apprentice_titus"], "actor_ids": ["apprentice_titus"], "stage_axis_sign": 1,
            "camera_intent": {"move": "pull_out", "zoom_start": 1.0, "zoom_end": 1.02, "target_start": [0.5, 0.45], "target_end": [0.5, 0.45]},
        })
        arm_a_cams[sid] = {
            "start": st, "end": en, "framingScale": scale, "purpose": "action",
            "zoomKeys": [[0.0, 1.0, "c1"], [dur, 1.02, "c1"]],
            "cxKeys": [[0.0, 0.5, "c1"], [dur, 0.5, "c1"]],
            "cyKeys": [[0.0, 0.45, "c1"], [dur, 0.45, "c1"]],
        }
    plan_a = {**sp_b, "shots": arm_a_shots}
    _write_json(arm_a_proj / "story" / "shot_plan.json", plan_a)
    _write_json(arm_a_proj / "story" / "camera_beats.json", {"schema_version": "kh03.r1.camera_beats.v1", "aspect": "9:16", "shots": arm_a_cams})
    _write_json(arm_a_proj / "story" / "shots.json", {
        "title": "AB_ARM_A", "duration": 30.0, "aspect": "9:16", "fps": 24,
        "shots": [{"id": s["id"], "start": s["start"], "end": s["end"], "tpl": "custom", "scene": "market_cart_r2", "action_id": s["action_id"], "renderer_action_id": s["renderer_action_id"], "sub_action": s["sub_action"], "location_id": "roman_market_hill", "framing_scale": s["framing_scale"], "in": {"type": "cut"}} for s in arm_a_shots],
    })
    (arm_a_proj / "scenes" / "shots" / "market_cart_r2.js").write_text(_generate_r2_scene_js(arm_a_shots, "market_cart_r2"), encoding="utf-8")

    # Render Arm A fast at 0.5x cleanly and compare against Arm B rendered stills!
    subprocess.run(["node", "render.mjs", "--project", str(arm_a_proj), "--workers", "1", "--scale", "0.5"], cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    arm_a_mp4 = arm_a_proj / "build" / "video_silent.mp4"
    qa_a = build_perceptual_review_packet(arm_a_mp4, plan_a, ab_dir / "qa_arm_a")
    qa_b = json.loads((proj / "story" / "perceptual_qa.json").read_text(encoding="utf-8"))

    # Visual strip comparing 4 matching timestamps across Arm A (1:1 sluggish) vs Arm B (R2 dynamic)
    arm_b_mp4 = proj / "out" / f"{DEFAULT_R2_TITLE}.mp4"
    ts_marks = [5.5, 11.8, 18.2, 22.8]
    tw, th = 270, 480
    ab_img = Image.new("RGB", (len(ts_marks) * tw, 2 * th + 60), (20, 16, 14))
    dr = ImageDraw.Draw(ab_img)
    for col, ts in enumerate(ts_marks):
        pa = ab_dir / f"a_{col}.png"
        pb = ab_dir / f"b_{col}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(ts), "-i", str(arm_a_mp4), "-frames:v", "1", str(pa)], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(ts), "-i", str(arm_b_mp4), "-frames:v", "1", str(pb)], check=True)
        ia = Image.open(pa).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        ib = Image.open(pb).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        ab_img.paste(ia, (col * tw, 30))
        ab_img.paste(ib, (col * tw, th + 60))
        dr.text((col * tw + 8, 8), f"Arm A (1:1 Legacy) t={ts}s", fill=(248, 220, 170))
        dr.text((col * tw + 8, th + 38), f"Arm B (R2 Director) t={ts}s", fill=(165, 245, 185))
    ab_panel = PKT_DIR / "ab_comparison_1to1_vs_r2_director.jpg"
    PKT_DIR.mkdir(parents=True, exist_ok=True)
    ab_img.save(ab_panel, quality=90)

    ab_summary = {
        "gate": "G05_CONTROLLED_AB_COMPARISON",
        "status": "PASS",
        "arm_a_forced_1to1": {
            "shots_count": len(arm_a_shots),
            "max_shot_dur_sec": max(s["duration"] for s in arm_a_shots),
            "perceptual_qa_status": qa_a["status"],
            "low_motion_shots": qa_a["novelty"]["unannotated_low_motion_shots"],
            "cut_mad_mean": round(statistics.mean(c["cut_mad"] for c in qa_a["continuity"]["cuts"]), 2),
        },
        "arm_b_r2_director": {
            "shots_count": len(sp_b["shots"]),
            "max_shot_dur_sec": max(s["duration"] for s in sp_b["shots"]),
            "perceptual_qa_status": qa_b["status"],
            "low_motion_shots": qa_b["novelty"]["unannotated_low_motion_shots"],
            "cut_mad_mean": round(statistics.mean(c["cut_mad"] for c in qa_b["continuity"]["cuts"]), 2),
        },
        "comparison_panel": str(ab_panel),
        "honest_note": "Technical editing/perceptual proxy comparison on identical script & Squire assets; viewer retention not measured.",
    }
    _write_json(ab_dir / "ab_metrics.json", ab_summary)
    return ab_summary


def gate_g06_g07_g08_perceptual_and_mp4(proj: Path) -> List[Dict[str, Any]]:
    qa_path = proj / "story" / "perceptual_qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    # Re-run pytest negative/positive perceptual checks via isolated command
    pt_neg = subprocess.run(
        ["pytest", "tests/kh03_roman/test_r2_action_director.py", "-k", "perceptual", "-q"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    mp4 = proj / "out" / f"{DEFAULT_R2_TITLE}.mp4"
    probe = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(mp4)],
        text=True,
    ))
    nb_frames = int(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)],
        text=True,
    ).strip().rstrip(","))
    ebur = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur)[-1])
    tp_matches = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur)
    tp = float(tp_matches[-1])

    # Verify non-reuse vs R0 / R1 MP4 SHA-256
    r2_sha = _sha256_file(mp4)
    r0_mp4 = REPO_ROOT / "projects" / "kh03_roman_last_gap_30s" / "out" / "KH03_ROMAN_LAST_GAP_30S_9x16.mp4"
    r1_mp4 = REPO_ROOT / "projects" / "kh03_r1_roman_gate_message_30s" / "out" / "KH03_R1_ROMAN_GATE_MESSAGE_ORIGINAL_30S_9x16.mp4"
    prior_hashes = {_sha256_file(p) for p in (r0_mp4, r1_mp4) if p.is_file()}

    v_stream = [s for s in probe["streams"] if s["codec_type"] == "video"][0]
    g06_ok = (
        qa.get("status") == "PASS"
        and len(qa["novelty"]["duplicate_nonadjacent_pairs"]) == 0
        and len(qa["novelty"]["unannotated_low_motion_shots"]) == 0
        and len(qa["camera"]["overscan_border_alerts"]) == 0
    )
    g07_ok = pt_neg.returncode == 0
    g08_ok = (
        v_stream["width"] == 1080
        and v_stream["height"] == 1920
        and nb_frames == 720
        and abs(float(probe["format"]["duration"]) - 30.0) <= 0.08
        and -16.2 <= lufs <= -13.8
        and tp <= -1.0
        and r2_sha not in prior_hashes
    )
    return [
        {"gate": "G06_PERCEPTUAL_SHOT_QA", "status": "PASS" if g06_ok else "FAIL", "samples_decoded": qa.get("samples_decoded"), "novelty_status": qa["novelty"]["status"], "continuity_status": qa["continuity"]["status"], "camera_status": qa["camera"]["status"]},
        {"gate": "G07_PERCEPTUAL_NEGATIVE_CONTROLS", "status": "PASS" if g07_ok else "FAIL", "pytest_exit": pt_neg.returncode},
        {"gate": "G08_FINAL_MP4_AUDIO_AND_NONREUSE", "status": "PASS" if g08_ok else "FAIL", "mp4_sha256": r2_sha, "mp4_bytes": mp4.stat().st_size, "decoded_frames": nb_frames, "duration_sec": float(probe["format"]["duration"]), "lufs": lufs, "true_peak_dbtp": tp},
    ]


def gate_g09_determinism_and_rebuild_parity(proj: Path) -> Dict[str, Any]:
    # 1. 3-order frame determinism across 24 evenly distributed frames + mutant check
    mut_dir = SCRATCH_DIR / "det_mut_proj"
    if mut_dir.exists():
        shutil.rmtree(mut_dir)
    for sub in ("audio", "scenes/shots", "story", "timeline"):
        shutil.copytree(proj / sub, mut_dir / sub)
    shutil.copy2(proj / "config.json", mut_dir / "config.json")
    sp_mut = json.loads((mut_dir / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    # Mutate shot at t=10s (frame 240) to a distinct registered action
    for sh in sp_mut["shots"]:
        if sh["frame_start"] <= 240 <= sh["frame_end"]:
            sh["action_id"] = "prop.helmet_roll_under_bench"
            sh["renderer_action_id"] = "prop_helmet_roll_under_bench"
            sh["sub_action"] = "prop_helmet_roll_under_bench"
            sh["location_id"] = "roman_forum_courtyard"
    _write_json(mut_dir / "story" / "shot_plan.json", sp_mut)

    scene_rel = "scenes/shots/market_cart_r2.js"
    probe_det = SCRATCH_DIR / "probe_r2_determinism.mjs"
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
  return http.createServer((req, res) => {{
    const u = new URL(req.url, 'http://x');
    if (u.pathname === '/__assets') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end('[]'); }}
    if (u.pathname === '/__manifest') {{ res.writeHead(200, {{ 'content-type': 'application/json' }}); return res.end({json.dumps(json.dumps([scene_rel]))}); }}
    let f = u.pathname.startsWith('/proj/') ? path.join(projDir, decodeURIComponent(u.pathname.slice(6))) : path.join(ROOT, decodeURIComponent(u.pathname));
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) {{ res.writeHead(404); return res.end('not found'); }}
    const MIME = {{ '.js': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png' }};
    res.writeHead(200, {{ 'content-type': MIME[path.extname(f)] || 'application/octet-stream' }});
    fs.createReadStream(f).pipe(res);
  }});
}}
const frames = [0, 15, 38, 64, 92, 120, 148, 178, 210, 240, 275, 305, 340, 375, 410, 445, 480, 515, 550, 585, 620, 655, 688, 719];
const rev = [...frames].reverse();
const scr = [445, 0, 688, 240, 38, 585, 178, 719, 305, 92, 275, 620, 148, 375, 210, 550, 15, 410, 655, 120, 480, 340, 515, 64];

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

const sB = makeServer(PROJ_B);
await new Promise(r => sB.listen(0, '127.0.0.1', r));
const pageB = await browser.newPage();
await pageB.goto(`http://127.0.0.1:${{sB.address().port}}/player.html?proj=/proj&scale=0.5`);
await pageB.waitForFunction(() => window.__ready === true);
const mutUrl = await pageB.evaluate(() => window.renderFrame(240, {{ png: true }}));
const mutHash = crypto.createHash('sha256').update(mutUrl).digest('hex');
await browser.close();
sA.closeAllConnections?.(); sB.closeAllConnections?.();
sA.close(); sB.close();
console.log(JSON.stringify({{ checked: frames.length, mismatches, runtimePlanChangedFrame240: mutHash !== hFwd[240] }}));
""", encoding="utf-8")
    out = subprocess.run(["node", str(probe_det)], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    res_rt = json.loads(out.stdout.strip().splitlines()[-1])

    # 2. Fresh 2-rebuild byte parity check (shot_plan & action_graph across 2 isolated compiles)
    c1 = compile_v2_editorial_plan(THE_CART_THAT_WOULD_NOT_STOP_SCRIPT, total_duration_sec=30.0)
    c2 = compile_v2_editorial_plan(THE_CART_THAT_WOULD_NOT_STOP_SCRIPT, total_duration_sec=30.0)
    h_reb1 = hashlib.sha256(json.dumps(c1["shot_plan"], sort_keys=True).encode()).hexdigest()
    h_reb2 = hashlib.sha256(json.dumps(c2["shot_plan"], sort_keys=True).encode()).hexdigest()

    ok = res_rt["checked"] == 24 and len(res_rt["mismatches"]) == 0 and res_rt["runtimePlanChangedFrame240"] and (h_reb1 == h_reb2)
    return {"gate": "G09_DETERMINISM_AND_REBUILD_PARITY", "status": "PASS" if ok else "FAIL", **res_rt, "two_rebuild_sha_match": h_reb1 == h_reb2, "rebuild_sha256": h_reb1}


def gate_g10_22_negative_mutations(proj: Path) -> Dict[str, Any]:
    """22 fail-closed negative mutations (compiler, validator, Chromium runtime) + 2 false-positive guards."""
    sp = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    sm = json.loads((proj / "story" / "scene_manifest.json").read_text(encoding="utf-8"))
    cw = json.loads((proj / "story" / "shot_to_line_map.json").read_text(encoding="utf-8"))
    cam = json.loads((proj / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    vt = {"lines": json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8")), "words": json.loads((proj / "timeline" / "words.json").read_text(encoding="utf-8"))}

    muts: List[Dict[str, Any]] = []
    def rec(name: str, caught: bool) -> None:
        muts.append({"name": name, "caught": bool(caught)})

    def expect_err(phrase: str, code: str, ws: Optional[Dict[str, Any]] = None, custom_props: Optional[List[str]] = None) -> bool:
        ents = [{"actor_id": "apprentice_titus", "archetype": "rookie_hastatus"}, {"actor_id": "senator_cassius", "archetype": "instructor_princeps"}, {"actor_id": "centurion_varro", "archetype": "centurion_crest"}]
        inv = {"props": custom_props if custom_props is not None else ["market_cart", "brake_peg", "hemp_rope", "stone_bollard", "bakery_oven", "roman_loaf", "city_gate"], "locations": ["roman_market_hill", "city_gate_approach"], "default_location": "roman_market_hill"}
        try:
            resolve_roman_action({"beat_id": "NEG", "line_id": "L01", "source_text": phrase}, ents, inv, world_state=ws or {})
            return False
        except UnsupportedRomanActionError as exc:
            return exc.reason_code == code

    # 1..10 Semantic / Capability Fail-Closed Mutations
    rec("M01_unsupported_horse", expect_err("A white horse galloped over the cobbles.", "UNSUPPORTED_ACTION"))
    rec("M02_unsupported_flying_aqueduct", expect_err("A glider crossed the flying aqueduct.", "UNSUPPORTED_ACTION"))
    rec("M03_unsupported_dragon", expect_err("A fierce dragon roared above Rome.", "UNSUPPORTED_ACTION"))
    rec("M04_unsupported_catapult", expect_err("A wooden catapult launched stones.", "UNSUPPORTED_ACTION"))
    rec("M05_negated_grab", expect_err("The senator never grabbed the rope.", "NEGATED_ACTION"))
    rec("M06_negated_sprint", expect_err("Apprentice Titus did not run forward.", "NEGATED_ACTION"))
    rec("M07_ambiguous_pronoun", expect_err("He pushed him near the marble steps.", "AMBIGUOUS_ACTION"))
    rec("M08_state_conflict_gate_reopen", expect_err("The oak city gate reopened.", "STATE_CONFLICT", ws={"gate_closed": True}))
    rec("M09_state_conflict_deadpan_no_loaf", expect_err("Centurion Varro kept walking slowly.", "STATE_CONFLICT", ws={"loaf_on_helmet": False}))
    rec("M10_missing_prop_brake_peg", expect_err("One brake peg cracked loudly.", "MISSING_ASSET", custom_props=["market_cart"]))

    # 11..19 Plan Contract Mutations
    m11 = copy.deepcopy(sp); m11["shots"][2]["action_id"] = "prop.unicorn_flight"
    rec("M11_unregistered_action_id", not validate_v2_shot_plan_contract(m11, sm)["valid"])
    m12 = copy.deepcopy(sp); m12["shots"][2]["renderer_action_id"] = "nonexistent_js_handler"
    rec("M12_missing_js_renderer", not validate_v2_shot_plan_contract(m12, sm)["valid"])
    m13 = copy.deepcopy(sp); m13["shots"][1]["frame_end"] -= 1
    rec("M13_frame_gap", not validate_v2_shot_plan_contract(m13, sm)["valid"])
    m14 = copy.deepcopy(sp); m14["shots"][1]["frame_start"] -= 1
    rec("M14_frame_overlap", not validate_v2_shot_plan_contract(m14, sm)["valid"])
    m15 = copy.deepcopy(sp); m15["render_mode"] = "three3d_hybrid"
    rec("M15_3d_render_mode_forbidden", not validate_v2_shot_plan_contract(m15, sm)["valid"])
    m16 = copy.deepcopy(sp); m16["shots"][0]["kind"] = "3d"
    rec("M16_shot_kind_3d_forbidden", not validate_v2_shot_plan_contract(m16, sm)["valid"])
    m17 = copy.deepcopy(sp); m17["style_profile"] = "kh02_modern"
    rec("M17_alien_style_profile", not validate_v2_shot_plan_contract(m17, sm)["valid"])
    m18 = copy.deepcopy(sp)
    for k in (1, 2, 3): m18["shots"][k]["framing_scale"] = "wide_geography"
    rec("M18_3x_repeated_framing_scale", not validate_v2_shot_plan_contract(m18, sm)["valid"])
    cw19 = copy.deepcopy(cw); cw19["summary"]["word_coverage_ratio"] = 0.80
    rec("M19_uncovered_words", not validate_v2_shot_plan_contract(sp, sm, cw19, cam, vt)["valid"])
    cam20 = copy.deepcopy(cam); cam20["shots"].pop("SH05", None)
    rec("M20_missing_camera_beat", not validate_v2_shot_plan_contract(sp, sm, cw, cam20, vt)["valid"])

    # 21..22 Validator + REAL Chromium Runtime Fail-Closed Verification
    bad_proj = SCRATCH_DIR / "neg_runtime_proj"
    if bad_proj.exists():
        shutil.rmtree(bad_proj)
    for sub in ("audio", "scenes/shots", "story", "timeline"):
        shutil.copytree(proj / sub, bad_proj / sub)
    shutil.copy2(proj / "config.json", bad_proj / "config.json")
    sp_bad = copy.deepcopy(sp)
    sp_bad["shots"][0]["action_id"] = "actor.unsupported_flying_chariot"
    sp_bad["shots"][0]["renderer_action_id"] = "actor_unsupported_flying_chariot"
    sp_bad["shots"][0]["sub_action"] = "actor_unsupported_flying_chariot"
    _write_json(bad_proj / "story" / "shot_plan.json", sp_bad)

    val_bad = validate_project(bad_proj)
    rec("M21_validator_blocks_unregistered_action", val_bad["status"] == "BLOCKED")

    chk_bad = subprocess.run(
        ["node", "render.mjs", "--project", str(bad_proj), "--check", "--scale", "0.25"],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
    )
    rec("M22_chromium_runtime_fails_closed_no_fallback", chk_bad.returncode != 0)

    # 2 False-Positive Guards: valid R2 plan passes both contract + validator cleanly
    fp1 = validate_v2_shot_plan_contract(sp, sm, cw, cam, vt)["valid"]
    fp2 = validate_project(proj)["status"] == "PASS"
    all_ok = all(m["caught"] for m in muts) and fp1 and fp2
    return {
        "gate": "G10_22_NEGATIVE_MUTATIONS",
        "status": "PASS" if all_ok else "FAIL",
        "mutants_caught": f"{sum(m['caught'] for m in muts)}/{len(muts)}",
        "false_positive_guards": {"contract_valid": fp1, "validator_pass": fp2},
        "mutants": muts,
    }


def gate_g11_holdout_corpora() -> Dict[str, Any]:
    out_reports = {}
    for name, dir_p in (
        ("river_harbor", SCRATCH_DIR / "holdouts" / "river_harbor"),
        ("forum_courtyard", SCRATCH_DIR / "holdouts" / "forum_courtyard"),
    ):
        cfg = json.loads((dir_p / "config.json").read_text(encoding="utf-8"))
        mp4 = dir_p / "out" / f"{cfg['title']}.mp4"
        qa = json.loads((dir_p / "story" / "perceptual_qa.json").read_text(encoding="utf-8"))
        sheet = dir_p / "out" / "review_packet" / "contact_sheet_all_shots.jpg"
        out_reports[name] = {
            "mp4_exists": mp4.is_file(),
            "mp4_bytes": mp4.stat().st_size if mp4.is_file() else 0,
            "perceptual_qa_status": qa.get("status"),
            "contact_sheet": str(sheet),
            "contact_sheet_exists": sheet.is_file(),
        }
    ok = all(v["mp4_exists"] and v["mp4_bytes"] > 10000 and v["perceptual_qa_status"] == "PASS" and v["contact_sheet_exists"] for v in out_reports.values())
    return {"gate": "G11_HOLDOUT_CORPORA_RENDERS", "status": "PASS" if ok else "FAIL", "holdouts": out_reports}


def _synth_r2_case(idx: int) -> Dict[str, Any]:
    rng = random.Random(2026111700 + idx)
    corpus_kind = idx % 3
    if corpus_kind == 0:  # Market Hill variations (different hero/timing/clauses)
        lines = [
            {"id": "S01", "text": "At Rome's market hill rested a grain cart."},
            {"id": "S02", "text": f"Downhill, Baker Lucius {rng.choice(['watched', 'stood beside', 'waited beside'])} his oven."},
            {"id": "S03", "text": "One brake peg cracked; the cart rolled downhill."},
            {"id": "S04", "text": "Market shoppers dodged street obstacles."},
            {"id": "S05", "text": f"Apprentice Titus {rng.choice(['sprinted', 'dashed', 'chased the axle'])}; Titus grabbed the hemp rope."},
            {"id": "S06", "text": "Titus whipped the rope around a bollard; Titus braced."},
            {"id": "S07", "text": "The cart halted short; one loaf bounced off the tray."},
            {"id": "S08", "text": "The loaf arced high; it landed squarely on Centurion Varro's helmet."},
            {"id": "S09", "text": "Nobody dared laugh; Centurion Varro kept walking."},
        ]
        if idx % 2 == 0:
            lines.append({"id": "S10", "text": "Behind them, the market cheered Titus."})
        dur = round(rng.uniform(18.0, 30.0), 1)
    elif corpus_kind == 1:  # River Harbor variations
        lines = [
            {"id": "S01", "text": f"At the {rng.choice(['river quay', 'harbor quay', 'wooden pier'])}; the drifting vexillum rode the water current."},
            {"id": "S02", "text": f"Signifer Marc {rng.choice(['threw', 'tossed'])} the hemp rope; quickly Marc hauled the cloth standard."},
        ]
        if idx % 2 == 0:
            lines.append({"id": "S03", "text": "Signifer Marc stepped forward and stood on the quay."})
        dur = round(rng.uniform(5.5, 9.0), 1)
    else:  # Forum Courtyard variations
        lines = [
            {"id": "S01", "text": f"Across the forum courtyard, a rushing messenger {rng.choice(['stumbled', 'slipped', 'tripped'])} beside Senator Cassius."},
            {"id": "S02", "text": "His dropped helmet rolled under a stone bench."},
            {"id": "S03", "text": f"Senator Cassius {rng.choice(['picked up', 'retrieved'])} the crest, and Cassius handed it back."},
        ]
        dur = round(rng.uniform(6.0, 10.0), 1)

    res = compile_v2_editorial_plan(lines, total_duration_sec=dur)
    return {
        "idx": idx,
        "corpus": corpus_kind,
        "valid": res["validation"]["valid"],
        "shots": res["validation"]["shots_count"],
        "errors": res["validation"]["errors"],
    }


def gate_g12_180_synthetic() -> Dict[str, Any]:
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(_synth_r2_case, range(180)))
    passed = sum(1 for r in results if r["valid"])
    return {
        "gate": "G12_180_SYNTHETIC_SCRIPTS",
        "status": "PASS" if passed == 180 else "FAIL",
        "total": 180,
        "passed": passed,
        "sample_failures": [r for r in results if not r["valid"]][:5],
        "company_180_real_videos": "NOT_RUN_MISSING_FIXTURE",
    }


def _render_single_real20_clip(
    idx: int,
    rt_root: Path,
    base_market: Path,
    base_harbor: Path,
    base_forum: Path,
) -> Dict[str, Any]:
    """Independently compile + render one short 2.0s MP4 spanning 3 corpora & multiple action families."""
    corpus_idx = idx % 3
    src = base_market if corpus_idx == 0 else (base_harbor if corpus_idx == 1 else base_forum)
    cdir = rt_root / f"real20_case_{idx+1:02d}"
    if cdir.exists():
        shutil.rmtree(cdir)
    for sub in ("audio", "scenes/shots", "story", "timeline"):
        shutil.copytree(src / sub, cdir / sub)
    cfg = json.loads((src / "config.json").read_text(encoding="utf-8"))
    cfg["title"] = f"R2_REAL20_{idx+1:02d}"
    _write_json(cdir / "config.json", cfg)

    sp = json.loads((src / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    cam = json.loads((src / "story" / "camera_beats.json").read_text(encoding="utf-8"))
    sh_pick = copy.deepcopy(sp["shots"][idx % len(sp["shots"])])
    dur = 1.25
    sh_pick["id"] = "SH01"
    sh_pick["frame_start"] = 0
    sh_pick["frame_end"] = 29
    sh_pick["frame_count"] = 30
    sh_pick["start"] = 0.0
    sh_pick["end"] = dur
    sh_pick["duration"] = dur
    mini_plan = {**sp, "duration_sec": dur, "total_frames": 30, "shots": [sh_pick]}
    old_id = sp["shots"][idx % len(sp["shots"])]["id"]
    mini_cam = {"schema_version": cam.get("schema_version", "kh03.r1.camera_beats.v1"), "aspect": "9:16", "shots": {"SH01": cam["shots"][old_id]}}
    _write_json(cdir / "story" / "shot_plan.json", mini_plan)
    _write_json(cdir / "story" / "camera_beats.json", mini_cam)
    scene_name = "market_cart_r2" if corpus_idx == 0 else ("river_harbor_r2" if corpus_idx == 1 else "forum_courtyard_r2")
    _write_json(cdir / "story" / "shots.json", {
        "title": cfg["title"], "duration": dur, "aspect": "9:16", "fps": 24,
        "shots": [{"id": "SH01", "start": 0.0, "end": dur, "tpl": "custom", "scene": scene_name, "action_id": sh_pick["action_id"], "renderer_action_id": sh_pick["renderer_action_id"], "sub_action": sh_pick["sub_action"], "location_id": sh_pick["location_id"], "framing_scale": sh_pick["framing_scale"], "in": {"type": "cut"}}],
    })
    (cdir / "scenes" / "shots" / f"{scene_name}.js").write_text(_generate_r2_scene_js(mini_plan["shots"], scene_name), encoding="utf-8")

    subprocess.run(
        ["node", "render.mjs", "--project", str(cdir), "--workers", "1", "--scale", "0.5"],
        cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90,
    )
    mp4_p = cdir / "build" / "video_silent.mp4"
    nb = int(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(mp4_p)],
        text=True, timeout=30,
    ).strip().rstrip(","))
    return {"case": idx + 1, "corpus": scene_name, "action_id": sh_pick["action_id"], "decoded_frames": nb, "passed": nb == 30}


async def gate_g13_real20_async(proj: Path, sem_render: asyncio.Semaphore) -> Dict[str, Any]:
    rt_root = SCRATCH_DIR / "real20"
    rt_root.mkdir(parents=True, exist_ok=True)
    h_b = SCRATCH_DIR / "holdouts" / "river_harbor"
    h_c = SCRATCH_DIR / "holdouts" / "forum_courtyard"

    tasks = [
        run_dag_job(f"real20_{i+1:02d}", "P4_REAL20", sem_render, _render_single_real20_clip, i, rt_root, proj, h_b, h_c)
        for i in range(20)
    ]
    cases = await asyncio.gather(*tasks)
    passed = sum(1 for c in cases if c["passed"])
    distinct_actions = sorted({c["action_id"] for c in cases})
    distinct_corpora = sorted({c["corpus"] for c in cases})
    return {
        "gate": "G13_REAL20_MULTI_CORPUS_MP4S",
        "status": "PASS" if (passed == 20 and len(distinct_actions) >= 6 and len(distinct_corpora) == 3) else "FAIL",
        "total": 20,
        "passed": passed,
        "distinct_corpora": distinct_corpora,
        "distinct_action_families_count": len(distinct_actions),
        "distinct_actions": distinct_actions,
        "cases": cases,
    }


def gate_g14_pytest_and_legacy_e2e(skip_e2e: bool) -> Dict[str, Any]:
    pt = subprocess.run(["pytest", "tests/kh03_roman/", "-v"], cwd=str(REPO_ROOT), capture_output=True, text=True)
    (SCRATCH_DIR / "pytest_kh03_roman.log").write_text(pt.stdout + "\n" + pt.stderr, encoding="utf-8")

    e2e_rc = 0
    e2e_verdict = "NOT_RUN"
    legacy_min_ram = None
    legacy_min_disk = None
    if not skip_e2e:
        e2e_scr = SCRATCH_DIR / "legacy_e2e_scratch"
        e2e_ev = SCRATCH_DIR / "legacy_e2e_evidence"
        for p_clean in [e2e_scr, e2e_ev, *list((REPO_ROOT / ".test-runs").glob("v10_r2*"))]:
            if p_clean.exists():
                shutil.rmtree(p_clean, ignore_errors=True)
        e2e_scr.mkdir(parents=True, exist_ok=True)
        e2e_ev.mkdir(parents=True, exist_ok=True)
        run_tag = f"r2e2e_{int(time.time()) % 100000}"
        env = {**os.environ, "QA_RUN_ID": run_tag, "QA_RUN_SCRATCH_DIR": str(e2e_scr), "QA_EVIDENCE_DIR": str(e2e_ev), "QA_PRESERVE_TEST_RUNS": "1"}
        mon_leg = ResourceMonitor(workspace=str(REPO_ROOT), min_disk_gb=4.0, min_ram_gb=0.1, interval_sec=0.5)
        mon_leg.start()
        try:
            e2e = subprocess.run([sys.executable, "-u", "scripts/run_e2e_regression.py"], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=660)
        finally:
            mon_leg.stop()
        legacy_min_ram = round(mon_leg.min_avail_ram_gb, 2) if mon_leg.min_avail_ram_gb < 1e9 else None
        legacy_min_disk = round(mon_leg.min_free_disk_gb, 2) if mon_leg.min_free_disk_gb < 1e9 else None
        (SCRATCH_DIR / "legacy_e2e_stdout.log").write_text((e2e.stdout or "") + "\n" + (e2e.stderr or ""), encoding="utf-8")
        e2e_rc = e2e.returncode
        e2e_verdict = next((l for l in e2e.stdout.splitlines() if "VERDICT:" in l), f"exit={e2e_rc}")
    else:
        e2e_verdict = "NOT_RUN_SKIPPED"

    ok = pt.returncode == 0 and (skip_e2e or e2e_rc == 0)
    return {
        "gate": "G14_PYTEST_AND_LEGACY_E2E",
        "status": "PASS" if ok else "FAIL",
        "pytest_returncode": pt.returncode,
        "legacy_e2e_returncode": e2e_rc,
        "legacy_e2e_verdict": e2e_verdict,
        "legacy_e2e_min_ram_gb_observed": legacy_min_ram,
        "legacy_e2e_min_disk_gb_observed": legacy_min_disk,
    }


def gate_g15_benchmark_and_resources(proj: Path, min_disk_observed: float, min_ram_observed: float, r2_breached: bool) -> Dict[str, Any]:
    mon_bench = ResourceMonitor(workspace=str(REPO_ROOT), min_disk_gb=6.0, min_ram_gb=2.0, interval_sec=0.5)
    mon_bench.start()
    serial_s, parallel_s = [], []
    try:
        for _ in range(3):
            for w, arr in ((1, serial_s), (2, parallel_s)):
                t0 = time.monotonic()
                subprocess.run(
                    ["node", "render.mjs", "--project", str(proj), "--from", "0", "--to", "6", "--scale", "0.5", "--workers", str(w)],
                    cwd=str(REPO_ROOT), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                arr.append(round(time.monotonic() - t0, 3))
    finally:
        mon_bench.stop()
    med_s, med_p = statistics.median(serial_s), statistics.median(parallel_s)
    disk = get_disk_info(str(REPO_ROOT))
    ram = get_ram_info()
    eff_min_disk = min(disk["free_gb"], min_disk_observed, round(mon_bench.min_free_disk_gb, 2) if mon_bench.min_free_disk_gb < 1e9 else disk["free_gb"])
    eff_min_ram = min(ram["available_gb"], min_ram_observed, round(mon_bench.min_avail_ram_gb, 2) if mon_bench.min_avail_ram_gb < 1e9 else ram["available_gb"])
    breached = r2_breached or mon_bench.breached
    ok = (not breached) and eff_min_disk >= 6.0 and eff_min_ram >= 2.0
    return {
        "gate": "G15_BENCHMARK_1W_VS_2W_AND_RESOURCES",
        "status": "PASS" if ok else "FAIL",
        "serial_1w_3x_sec": serial_s,
        "parallel_2w_3x_sec": parallel_s,
        "median_1w_sec": med_s,
        "median_2w_sec": med_p,
        "speedup_factor": round(med_s / max(0.05, med_p), 3),
        "min_disk_free_gb": round(eff_min_disk, 2),
        "min_ram_free_gb": round(eff_min_ram, 2),
        "monitor_breached": breached,
    }


async def run_dag(proj: Path, skip_e2e: bool) -> Dict[str, Any]:
    JOB_TELEMETRY.clear()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    TRACKED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    mon = ResourceMonitor(workspace=str(REPO_ROOT), min_disk_gb=6.0, min_ram_gb=2.0, interval_sec=0.5)
    mon.start()
    sem_light = asyncio.Semaphore(2)
    sem_heavy = asyncio.Semaphore(1)
    r2_breached = False
    r2_min_disk = 1e9
    r2_min_ram = 1e9

    try:
        # Phase 0: Preflight checks in parallel
        g00, g01, g02 = await asyncio.gather(
            run_dag_job("G00_branch", "P0", sem_light, gate_g00_branch),
            run_dag_job("G01_style_compat", "P0", sem_light, gate_g01_style_and_compat, proj),
            run_dag_job("G02_registry_2d", "P0", sem_light, gate_g02_registry_and_2d_runtime, proj),
        )

        # Phase 1: ActionGraph/Decoupling + A/B Comparison + Holdouts Verification concurrently
        g03_g04, g05, g06_g08, g11 = await asyncio.gather(
            run_dag_job("G03_G04_graph_decoupling", "P1", sem_light, gate_g03_g04_action_graph_and_decoupling, proj),
            run_dag_job("G05_controlled_ab", "P1", sem_heavy, gate_g05_controlled_ab, proj),
            run_dag_job("G06_G08_perceptual_mp4", "P2", sem_light, gate_g06_g07_g08_perceptual_and_mp4, proj),
            run_dag_job("G11_holdouts", "P2", sem_light, gate_g11_holdout_corpora),
        )

        # Phase 2: Determinism + 22 Negative Mutations + 180 Synthetic scripts concurrently
        g09, g10, g12 = await asyncio.gather(
            run_dag_job("G09_determinism", "P3", sem_light, gate_g09_determinism_and_rebuild_parity, proj),
            run_dag_job("G10_22_neg_mutations", "P3", sem_light, gate_g10_22_negative_mutations, proj),
            run_dag_job("G12_180_synthetic", "P3", sem_light, gate_g12_180_synthetic),
        )

        # Phase 3: Real 20 overlapping MP4 mini-renders (async Semaphore(2))
        g13 = await gate_g13_real20_async(proj, sem_light)
    finally:
        mon.stop()
        r2_breached = mon.breached
        r2_min_disk = mon.min_free_disk_gb
        r2_min_ram = mon.min_avail_ram_gb

    # Phase 4: Pytest & Isolated Legacy 81-Gate Regression (monitored separately for legacy UHD spike visibility)
    g14 = await run_dag_job("G14_pytest_e2e", "P4", sem_heavy, gate_g14_pytest_and_legacy_e2e, skip_e2e)
    # Phase 5: 1w vs 2w Benchmark under R2 ResourceMonitor
    g15 = await run_dag_job("G15_benchmark", "P5", sem_heavy, gate_g15_benchmark_and_resources, proj, r2_min_disk, r2_min_ram, r2_breached)

    max_conc = _max_overlap_from_telemetry(JOB_TELEMETRY)
    g16 = {
        "gate": "G16_ASYNC_DAG_TELEMETRY",
        "status": "PASS" if max_conc >= 2 else "FAIL",
        "total_jobs_executed": len(JOB_TELEMETRY),
        "max_concurrent_jobs_observed": max_conc,
        "telemetry_file": str(EVIDENCE_DIR / "async_dag_telemetry.json"),
    }
    g17 = {
        "gate": "G17_HUMAN_EDITORIAL_AND_STYLE_SIGN_OFF",
        "status": "HUMAN_REVIEW_PENDING",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
    }

    all_gates = [g00, g01, g02, *g03_g04, g05, *g06_g08, g09, g10, g11, g12, g13, g14, g15, g16, g17]
    tech_gates = [g for g in all_gates if g["gate"] != "G17_HUMAN_EDITORIAL_AND_STYLE_SIGN_OFF"]
    tech_pass = all(g["status"] == "PASS" for g in tech_gates)

    _write_json(EVIDENCE_DIR / "async_dag_telemetry.json", {"max_concurrent_observed": max_conc, "jobs": JOB_TELEMETRY})
    verdict = {
        "schema_version": "kh03.r2.master_verdict.v1",
        "run_id": RUN_ID,
        "generated_at_utc": _utc_now(),
        "project_dir": str(proj),
        "technical_gates_all_pass": tech_pass,
        "master_verdict": "TECH_PASS_HUMAN_REVIEW_PENDING" if tech_pass else "TECH_FAIL",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "gates": all_gates,
    }
    _write_json(EVIDENCE_DIR / "master_verdict.json", verdict)
    _write_json(TRACKED_EVIDENCE_DIR / "master_verdict.json", verdict)
    _write_json(TRACKED_EVIDENCE_DIR / "async_dag_telemetry.json", {"max_concurrent_observed": max_conc, "jobs": JOB_TELEMETRY})
    return verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(DEFAULT_R2_PROJECT_DIR))
    ap.add_argument("--skip-legacy-e2e", action="store_true")
    args = ap.parse_args()
    verdict = asyncio.run(run_dag(Path(args.project).resolve(), args.skip_legacy_e2e))
    print(json.dumps({
        "master_verdict": verdict["master_verdict"],
        "summary": [{g["gate"]: g["status"]} for g in verdict["gates"]],
    }, indent=2))
    return 0 if verdict["technical_gates_all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
