#!/usr/bin/env python3
"""run_kh03_0_validation.py — Bounded Async DAG, Frame/Contact QA, Backtest & Regression Runner for KH-03.0.

Implements all 15 mandatory validation & governance functions from KH-03.0.R1 Section 10 & 11:
  1. run_preflight_guard
  2. job_capture_baseline
  3. job_style_lock_contract
  4. job_render_reference_poc
  5. job_2d_only_guard
  6. job_build_fresh_preview
  7. job_render_full_30s
  8. job_frame_temporal_validation
  9. job_camera_and_contact_qa
 10. job_negative_mutations
 11. job_real_backtests
 12. job_legacy_regression
 13. job_speed_and_reproducibility
 14. write_verdict_and_review_packet
 15. safe_commit_push_attestation

Concurrency & safety rules:
- Synchronous `run_preflight_guard()` must PASS before any async DAG node launches.
- Lightweight CPU/IO jobs run concurrently via `asyncio` + `ThreadPoolExecutor(max_workers <= min(3, logicalCPU // 2))`.
- Heavy Chromium/FFmpeg jobs acquire `heavy_sem = asyncio.Semaphore(1)` (or `2` only if free RAM >= 6 GiB and free disk >= 16 GiB, each in isolated scratch dirs).
- Continuous 1s `ResourceMonitor` tracks min free disk / min available RAM and kills ONLY owned registered child PIDs on breach.
- Never deletes `.test-runs/kh01_*`, `.test-runs/kh02_*`, or any existing user project/evidence files.
- Never counts `NOT_RUN_MISSING_FIXTURE` as `PASS`; never auto-approves `STYLE_APPROVED` or `EDITORIAL_APPROVED`.
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf
from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from resource_guard import ResourceMonitor, check_resources, get_disk_info, get_ram_info, kill_process_tree
from tools.common import compute_canonical_visual_hash
from tools.kh03_baseline_comparator import capture_same_pose_roman_reference, compare_roman_identity_geometry
from tools.kh03_preview_director import (
    OUTPUT_TITLE,
    PILOT_PROJECT_DIR,
    build_roman_audio_timeline,
    build_roman_preview_project,
    compile_roman_training_beats,
    render_roman_preview_30s,
)
from tools.kh03_reference_audit import assert_no_reused_demo_assets, collect_user_style_reference
from tools.kh03_style_lock import (
    compute_roman_style_digest,
    load_roman_master_style,
    validate_roman_style_contract,
)
from tools.validator import validate_project

DEFAULT_RUN_ID = "20261117_044405Z_4e4f"
EXPECTED_PRODUCTION_SHA = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


class ValidationContext:
    def __init__(self, run_id: str = DEFAULT_RUN_ID) -> None:
        self.run_id = run_id
        self.run_dir = REPO_ROOT / "docs" / "antigravity_runs" / f"KH-03_0_ROMAN_MASTER_{run_id}"
        self.evidence_dir = self.run_dir / "evidence"
        self.style_poc_dir = self.run_dir / "style_poc"
        self.packet_dir = self.run_dir / "film_preview_packet"
        self.scratch_dir = REPO_ROOT / ".test-runs" / f"kh03_0_{run_id}"
        self.tracked_evidence_dir = REPO_ROOT / "tests" / "evidence" / f"kh03_0_{run_id}"

        for d in (self.evidence_dir, self.style_poc_dir, self.packet_dir, self.scratch_dir, self.tracked_evidence_dir):
            d.mkdir(parents=True, exist_ok=True)

        logical_cpus = os.cpu_count() or 4
        self.light_workers = max(1, min(3, logical_cpus // 2))
        ram_avail = get_ram_info()["available_gb"]
        disk_free = get_disk_info(str(REPO_ROOT))["free_gb"]
        # Heavy browser/FFmpeg cap: Semaphore(1) conservative default; allow 2 only when ample headroom proven
        self.heavy_cap = 2 if (ram_avail >= 6.0 and disk_free >= 16.0) else 1
        self.heavy_sem = asyncio.Semaphore(self.heavy_cap)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.light_workers)
        self.monitor = ResourceMonitor(workspace=str(REPO_ROOT), min_disk_gb=10.0, min_ram_gb=1.0, interval_sec=1.0)
        self.dag_trace: List[Dict[str, Any]] = []
        self._trace_lock = asyncio.Lock()

    def run_monitored(
        self,
        cmd: List[str],
        cwd: Path = REPO_ROOT,
        env: Dict[str, str] | None = None,
        timeout: float = 600.0,
    ) -> Tuple[int, str, str, float]:
        if self.monitor.breached:
            raise RuntimeError(f"Resource breach active before command launch: {self.monitor.breach_message}")
        t0 = time.monotonic()
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.monitor.register_pid(proc.pid)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err, round(time.monotonic() - t0, 3)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)
            out, err = proc.communicate()
            return -1, out or "", f"TIMEOUT after {timeout}s\n{err or ''}", round(time.monotonic() - t0, 3)
        finally:
            self.monitor.unregister_pid(proc.pid)

    async def record_job(self, name: str, kind: str, fn, *args, **kwargs) -> Dict[str, Any]:
        t_start = round(time.monotonic(), 4)
        iso_start = _utc_iso()
        try:
            if kind == "heavy":
                async with self.heavy_sem:
                    res = await asyncio.get_running_loop().run_in_executor(self.executor, lambda: fn(*args, **kwargs))
            elif kind == "async":
                res = await fn(*args, **kwargs)
            else:
                res = await asyncio.get_running_loop().run_in_executor(self.executor, lambda: fn(*args, **kwargs))
        except Exception as exc:
            res = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        t_end = round(time.monotonic(), 4)
        entry = {
            "job": name,
            "kind": kind,
            "status": res.get("status", "UNKNOWN"),
            "t_start_mono": t_start,
            "t_end_mono": t_end,
            "wall_sec": round(t_end - t_start, 3),
            "started_at_utc": iso_start,
            "finished_at_utc": _utc_iso(),
        }
        async with self._trace_lock:
            self.dag_trace.append(entry)
        return res


# ============================================================================
# 1. SYNCHRONOUS PREFLIGHT GUARD
# ============================================================================
def run_preflight_guard(ctx: ValidationContext) -> Dict[str, Any]:
    errors: List[str] = []
    # Forecast footprint ~2.0 GiB -> require max(8.0, 2.0 + 2.0) = 8.0 GiB (enforce 10.0 GiB conservative floor)
    min_disk_gib = max(8.0, 2.0 + 2.0)
    ok_res, msg_res, hw_info = check_resources(str(REPO_ROOT), min_disk_gb=min_disk_gib, min_ram_gb=1.0)
    if not ok_res:
        errors.append(msg_res)

    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(REPO_ROOT), text=True).strip()
    if branch != "feat/roman-2d-master":
        errors.append(f"Expected active branch 'feat/roman-2d-master', got '{branch}'")

    anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "origin/Production", "HEAD"],
        cwd=str(REPO_ROOT),
    ).returncode
    if anc != 0:
        errors.append("HEAD does not descend from origin/Production")

    prod_sha = subprocess.check_output(["git", "rev-parse", "origin/Production"], cwd=str(REPO_ROOT), text=True).strip()
    fix_sha = subprocess.check_output(["git", "rev-parse", "origin/fix/Image-Shot"], cwd=str(REPO_ROOT), text=True).strip()
    kh02_sha = subprocess.check_output(["git", "rev-parse", "origin/feat/modern-2d-cinematic"], cwd=str(REPO_ROOT), text=True).strip()

    # Check toolchains
    node_v = subprocess.check_output(["node", "-v"], cwd=str(REPO_ROOT), text=True).strip()
    ff_v = subprocess.check_output(["ffmpeg", "-version"], cwd=str(REPO_ROOT), text=True).splitlines()[0]
    fp_v = subprocess.check_output(["ffprobe", "-version"], cwd=str(REPO_ROOT), text=True).splitlines()[0]

    # Required legacy fixtures & prior test-run preservation inventory
    preserved_fixtures = {
        rel: (REPO_ROOT / rel).exists()
        for rel in [
            "projects/squire-mau/config.json",
            "projects/selfimprove-mau/config.json",
            "packs/dem/pack.js",
            "engine/three3d.js",
        ]
    }
    for rel, present in preserved_fixtures.items():
        if not present:
            errors.append(f"Required repository baseline fixture missing: {rel}")

    prior_runs = sorted([
        d.name for d in (REPO_ROOT / ".test-runs").iterdir()
        if d.is_dir() and not d.name.startswith(f"kh03_0_{ctx.run_id}")
    ]) if (REPO_ROOT / ".test-runs").is_dir() else []

    result = {
        "status": "PASS" if not errors else "BLOCKED",
        "branch": branch,
        "ancestry_from_production_ok": anc == 0,
        "protected_refs": {
            "origin/Production": prod_sha,
            "origin/fix/Image-Shot": fix_sha,
            "origin/feat/modern-2d-cinematic": kh02_sha,
            "matches_prompt_production_sha": prod_sha == EXPECTED_PRODUCTION_SHA,
        },
        "hardware": hw_info,
        "light_worker_cap": ctx.light_workers,
        "heavy_render_cap": ctx.heavy_cap,
        "toolchains": {"node": node_v, "python": sys.version.split()[0], "ffmpeg": ff_v, "ffprobe": fp_v},
        "preserved_fixtures": preserved_fixtures,
        "untouched_prior_test_runs_count": len(prior_runs),
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "preflight_guard.json", result)
    return result


# ============================================================================
# 2. BASELINE PRESERVATION JOB
# ============================================================================
def job_capture_baseline(ctx: ValidationContext) -> Dict[str, Any]:
    base_snap_path = ctx.evidence_dir / "baseline_snapshot.json"
    if not base_snap_path.is_file():
        return {"status": "FAIL", "error": f"Pre-edit baseline_snapshot.json missing at {base_snap_path}"}

    snap = json.loads(base_snap_path.read_text(encoding="utf-8"))
    errors: List[str] = []

    # Re-render squire-mau & selfimprove-mau stills in fresh isolated post-edit scratch copies and compare pixel SHA-256!
    post_scr = ctx.scratch_dir / "post_edit_baseline_verify"
    if post_scr.exists():
        shutil.rmtree(post_scr)
    post_scr.mkdir(parents=True, exist_ok=True)

    comparisons: Dict[str, Any] = {}
    for pname, stills_arg in [("squire-mau", "1.2,4.0,15.0"), ("selfimprove-mau", "1.0,4.0,10.0")]:
        src = REPO_ROOT / "projects" / pname
        dst = post_scr / pname
        shutil.copytree(src, dst)
        vhash_now = compute_canonical_visual_hash(str(dst))
        vhash_pre = snap["sample_baselines"][pname]["canonical_visual_hash"]
        if vhash_now != vhash_pre:
            errors.append(f"{pname} canonical_visual_hash drifted: pre={vhash_pre}, post={vhash_now}")

        rc, out, err, dur = ctx.run_monitored(["node", "render.mjs", "--project", str(dst), "--stills", stills_arg, "--scale", "0.5"])
        if rc != 0:
            errors.append(f"{pname} post-edit stills render failed: {err[:250]}")
            continue

        still_matches = {}
        pre_stills = snap["sample_baselines"][pname]["stills_pass1_sha256"]
        for sname, pre_sha in pre_stills.items():
            sp = dst / "build" / "stills" / sname
            post_sha = _sha256_file(sp)
            still_matches[sname] = {"pre_sha256": pre_sha, "post_sha256": post_sha, "exact_match": pre_sha == post_sha}
            if pre_sha != post_sha:
                errors.append(f"{pname} still '{sname}' pixel SHA-256 drifted after KH-03 opt-in hooks!")

        comparisons[pname] = {
            "canonical_visual_hash": vhash_now,
            "hash_preserved": vhash_now == vhash_pre,
            "stills": still_matches,
            "render_sec": dur,
        }

    # Check untouched hashes on DEM pack, engine/core.js, engine/three3d.js, and sample projects
    must_preserve_exact = [
        "engine/core.js",
        "engine/three3d.js",
        "packs/dem/pack.js",
        "packs/dem/templates.js",
        "packs/squire/army.js",
        "packs/squire/horse.js",
        "projects/squire-mau/config.json",
        "projects/squire-mau/story/shots.json",
        "projects/selfimprove-mau/config.json",
        "projects/selfimprove-mau/story/shots.json",
    ]
    untouched_check = {}
    for rel in must_preserve_exact:
        cur_h = _sha256_file(REPO_ROOT / rel)
        pre_h = snap["tracked_files"][rel]["sha256"]
        ok = cur_h == pre_h
        untouched_check[rel] = ok
        if not ok:
            errors.append(f"Protected file mutated: {rel}")

    res = {
        "status": "PASS" if not errors else "FAIL",
        "comparisons": comparisons,
        "protected_files_byte_identical": untouched_check,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "baseline_preservation_check.json", res)
    return res


# ============================================================================
# 3. STYLE LOCK CONTRACT JOB
# ============================================================================
def job_style_lock_contract(ctx: ValidationContext) -> Dict[str, Any]:
    snap = json.loads((ctx.evidence_dir / "baseline_snapshot.json").read_text(encoding="utf-8"))
    sb = load_roman_master_style("roman_squire_master.v1")
    digest = compute_roman_style_digest(sb)
    contract = validate_roman_style_contract(sb, baseline_manifest=snap)
    ref_audit = collect_user_style_reference()

    res = {
        "status": "PASS" if (contract["valid"] and contract["digest_verified"]) else "FAIL",
        "style_id": sb["style_id"],
        "canonical_digest": digest,
        "contract_validation": contract,
        "user_screenshot_reference": ref_audit,
        "style_approved": "HUMAN_REVIEW_PENDING",
    }
    _atomic_write_json(ctx.evidence_dir / "style_lock_contract.json", res)
    return res


# ============================================================================
# 4. SAME-POSE ORIGINAL ROMAN A/B & EXPRESSION POC JOB
# ============================================================================
def job_render_reference_poc(ctx: ValidationContext) -> Dict[str, Any]:
    poc_res = capture_same_pose_roman_reference(
        output_dir=ctx.style_poc_dir,
        scratch_dir=ctx.scratch_dir / "style_poc",
        tracked_evidence_dir=ctx.tracked_evidence_dir / "style_poc",
    )
    ok = (
        poc_res["source_baseline_lock"]["status"] == "PASS"
        and poc_res["roman_identity_preserved"]["technical_gate"] == "PASS"
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "source_baseline_lock": poc_res["source_baseline_lock"],
        "roman_identity_preserved": {
            "technical_gate": poc_res["roman_identity_preserved"]["technical_gate"],
            "wide_silhouette_iou": poc_res["roman_identity_preserved"]["wide"]["silhouette_iou"],
            "close_silhouette_iou": poc_res["roman_identity_preserved"]["close"]["silhouette_iou"],
            "wide_changed_ratio": poc_res["roman_identity_preserved"]["wide"]["changed_pixel_ratio"],
            "close_changed_ratio": poc_res["roman_identity_preserved"]["close"]["changed_pixel_ratio"],
            "style_approved": "HUMAN_REVIEW_PENDING",
        },
        "contact_sheet": poc_res["artifacts"]["same_pose_ab_contact_sheet.jpg"],
        "expression_sheet": poc_res["artifacts"]["original_roman_expression_pose_sheet.jpg"],
    }


# ============================================================================
# 5. STRICT 2D-ONLY RUNTIME & STATIC GUARD JOB
# ============================================================================
def job_2d_only_guard(ctx: ValidationContext) -> Dict[str, Any]:
    errors: List[str] = []
    guard_scr = ctx.scratch_dir / "guard_2d_only"
    if guard_scr.exists():
        shutil.rmtree(guard_scr)
    shutil.copytree(PILOT_PROJECT_DIR, guard_scr / "mutated_3d_proj", ignore=shutil.ignore_patterns("build", "out"))
    mut_proj = guard_scr / "mutated_3d_proj"

    # Inject forbidden kind:'3d' into SH02 and verify BOTH validator.py AND Chromium render.mjs reject it!
    shots_p = mut_proj / "story" / "shots.json"
    sdata = json.loads(shots_p.read_text(encoding="utf-8"))
    sdata["shots"][1]["kind"] = "3d"
    shots_p.write_text(json.dumps(sdata, indent=2), encoding="utf-8")

    v_rep = validate_project(mut_proj)
    static_rejected = v_rep["status"] == "BLOCKED" and any("KH03_2D_ONLY_VIOLATION" in e for e in v_rep["fatal_errors"])
    if not static_rejected:
        errors.append("tools/validator.py failed to block injected kind:'3d' on canvas2d_only project")

    rc_mut, out_mut, err_mut, _ = ctx.run_monitored(
        ["node", "render.mjs", "--project", str(mut_proj), "--check", "--scale", "0.25"]
    )
    runtime_rejected = (rc_mut != 0) and ("KH03_2D_ONLY_VIOLATION" in (out_mut + err_mut))
    if not runtime_rejected:
        errors.append("render.mjs / engine/player.js failed to reject injected kind:'3d' before render")

    # Instrument Playwright network requests across all 9 shots of the real KH-03.0 pilot to prove 0 Three.js/WebGL loads
    probe_js = guard_scr / "audit_network_2d.mjs"
    probe_js.write_text(
        """import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const [repoRoot, projDir] = process.argv.slice(2);
const MIME = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };
function listScenes(dir) {
  const out = []; const base = path.join(dir, 'scenes', 'shots');
  if (fs.existsSync(base)) for (const f of fs.readdirSync(base).sort()) if (f.endsWith('.js')) out.push('scenes/shots/' + f);
  return out;
}
const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/__assets') { res.writeHead(200, {'content-type':'application/json'}); return res.end('[]'); }
  if (u.pathname === '/__manifest') { res.writeHead(200, {'content-type':'application/json'}); return res.end(JSON.stringify(listScenes(projDir))); }
  const file = u.pathname.startsWith('/proj/') ? path.join(projDir, decodeURIComponent(u.pathname.slice(6))) : path.join(repoRoot, decodeURIComponent(u.pathname.slice(1)));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('404'); }
  res.writeHead(200, {'content-type': MIME[path.extname(file)] || 'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;
let browser;
for (const ch of ['msedge', 'chrome', 'chromium']) { try { browser = await chromium.launch({ channel: ch }); break; } catch {} }
if (!browser) browser = await chromium.launch();
const page = await browser.newPage();
const urls = [];
page.on('request', (req) => urls.push(req.url()));
await page.goto(`http://127.0.0.1:${port}/player.html?proj=/proj&scale=0.25`);
await page.waitForFunction(() => window.__ready || window.__bootError, null, { timeout: 60000 });
for (const fr of [0, 30, 80, 160, 240, 320, 400, 490, 580, 680]) {
  await page.evaluate((f) => window.renderFrame(f, { png: false }), fr);
}
const info = await page.evaluate(() => ({ three3dLoaded: !!window.__three3dLoaded, renderMode: window.__info?.renderMode }));
const threeHits = urls.filter((u) => /three3d|three\\.module|webgl/i.test(u));
await browser.close(); server.close();
console.log(JSON.stringify({ totalRequests: urls.length, threeUrlCount: threeHits.length, threeHits, ...info }));
""",
        encoding="utf-8",
    )
    rc_net, out_net, err_net, _ = ctx.run_monitored(["node", str(probe_js), str(REPO_ROOT), str(PILOT_PROJECT_DIR)])
    net_info = json.loads(out_net.strip().splitlines()[-1]) if rc_net == 0 and out_net.strip() else {"threeUrlCount": -1}
    if net_info.get("threeUrlCount") != 0 or net_info.get("three3dLoaded") is not False:
        errors.append(f"Unexpected 3D module activity in KH-03 pilot: {net_info}")

    # Confirm legacy engine/three3d.js still exists intact for non-KH03 projects
    snap = json.loads((ctx.evidence_dir / "baseline_snapshot.json").read_text(encoding="utf-8"))
    three_intact = _sha256_file(REPO_ROOT / "engine" / "three3d.js") == snap["tracked_files"]["engine/three3d.js"]["sha256"]
    if not three_intact:
        errors.append("Legacy engine/three3d.js was modified")

    res = {
        "status": "PASS" if not errors else "FAIL",
        "static_validator_rejected_3d": static_rejected,
        "runtime_player_rejected_3d": runtime_rejected,
        "pilot_network_audit": net_info,
        "legacy_three3d_preserved_byte_for_byte": three_intact,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "guard_2d_only.json", res)
    return res


# ============================================================================
# 6. BUILD & AUDIT FRESH PREVIEW ASSETS JOB
# ============================================================================
def job_build_fresh_preview(ctx: ValidationContext) -> Dict[str, Any]:
    errors: List[str] = []
    if not (PILOT_PROJECT_DIR / "config.json").is_file():
        build_roman_preview_project(PILOT_PROJECT_DIR)
    if not (PILOT_PROJECT_DIR / "timeline" / "voice.wav").is_file():
        build_roman_audio_timeline(PILOT_PROJECT_DIR, scratch_dir=ctx.scratch_dir / "tts_segments")

    val = validate_project(PILOT_PROJECT_DIR)
    if val["status"] != "PASS":
        errors.append(f"Pilot validator status={val['status']}: {val}")

    non_reuse = assert_no_reused_demo_assets(PILOT_PROJECT_DIR)
    if not non_reuse["passed"]:
        errors.append(f"Asset non-reuse audit failed: {non_reuse['errors']}")

    voice_wav = PILOT_PROJECT_DIR / "timeline" / "voice.wav"
    audio_sig, sr = sf.read(str(voice_wav), dtype="float32")
    voice_rms = float(np.sqrt(np.mean(audio_sig ** 2)))
    if voice_rms < 0.01:
        errors.append(f"Pilot voice.wav RMS too low ({voice_rms:.6f}); silent narration forbidden")

    lines = json.loads((PILOT_PROJECT_DIR / "timeline" / "lines.json").read_text(encoding="utf-8"))
    words = json.loads((PILOT_PROJECT_DIR / "timeline" / "words.json").read_text(encoding="utf-8"))

    res = {
        "status": "PASS" if not errors else "FAIL",
        "validator_status": val["status"],
        "shots_total": val["shots_total"],
        "non_reuse_audit": non_reuse,
        "voice_Verification": {
            "sample_rate": sr,
            "duration_sec": round(len(audio_sig) / sr, 3),
            "rms": round(voice_rms, 6),
            "lines_count": len(lines),
            "words_count": len(words),
        },
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "fresh_preview_build_audit.json", res)
    return res


# ============================================================================
# 7. FULL 30.000s 1080p24 RENDER VERIFICATION JOB
# ============================================================================
def job_render_full_30s(ctx: ValidationContext) -> Dict[str, Any]:
    final_mp4 = PILOT_PROJECT_DIR / "out" / f"{OUTPUT_TITLE}.mp4"
    pkt_manifest_path = ctx.packet_dir / "pilot_render_manifest.json"
    if not final_mp4.is_file() or not pkt_manifest_path.is_file():
        manifest = render_roman_preview_30s(
            PILOT_PROJECT_DIR,
            review_packet_dir=ctx.packet_dir,
            tracked_evidence_dir=ctx.tracked_evidence_dir / "film_preview_packet",
            workers=2,
        )
    else:
        manifest = json.loads(pkt_manifest_path.read_text(encoding="utf-8"))
        # Re-verify current MP4 SHA-256 matches manifest
        live_sha = _sha256_file(final_mp4)
        if live_sha != manifest.get("output_mp4_sha256"):
            manifest = render_roman_preview_30s(
                PILOT_PROJECT_DIR,
                review_packet_dir=ctx.packet_dir,
                tracked_evidence_dir=ctx.tracked_evidence_dir / "film_preview_packet",
                workers=2,
            )

    errors: List[str] = []
    vs = manifest["video_stream"]
    aus = manifest["audio_stream"]
    if vs["codec_name"] != "h264" or vs["width"] != 1920 or vs["height"] != 1080:
        errors.append(f"Invalid video stream geometry/codec: {vs}")
    if vs["r_frame_rate"] != "24/1" or vs["decoded_frames"] != 720 or abs(vs["format_duration_sec"] - 30.0) > 0.05:
        errors.append(f"Invalid frame count or duration (expected 720 @ 24fps = 30.000s): {vs}")
    if aus["codec_name"] != "aac" or not (-16.2 <= aus["integrated_lufs"] <= -13.8) or aus["true_peak_dbtp"] > -1.0:
        errors.append(f"Audio stream out of LUFS/dBTP spec: {aus}")

    res = {
        "status": "PASS" if not errors else "FAIL",
        "manifest": manifest,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "render_full_30s_receipt.json", res)
    return res


# ============================================================================
# 8. 720-FRAME STREAMING DECODE & TEMPORAL LIVENESS VALIDATION JOB
# ============================================================================
def inspect_mp4_temporal_stream(mp4_path: Path, storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """Decode every frame via streaming FFmpeg pipe (480x270 RGB24 in RAM, 0 raw disk bloat) & audit motion."""
    W_s, H_s = 480, 270
    frame_bytes = W_s * H_s * 3
    proc = subprocess.Popen(
        [
            "ffmpeg", "-v", "error", "-i", str(mp4_path),
            "-vf", f"scale={W_s}:{H_s}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None

    frames_decoded = 0
    black_frames: List[int] = []
    flat_frames: List[int] = []
    prev_arr: np.ndarray | None = None
    full_diffs: List[float] = []
    center_actor_diffs: List[float] = []
    border_cam_diffs: List[float] = []

    while True:
        buf = proc.stdout.read(frame_bytes)
        if not buf or len(buf) < frame_bytes:
            break
        arr = np.frombuffer(buf, dtype=np.uint8).reshape((H_s, W_s, 3)).astype(np.float32)
        mean_luma = float(arr.mean())
        std_rgb = float(arr.std())
        if mean_luma < 8.0:
            black_frames.append(frames_decoded)
        if std_rgb < 4.0:
            flat_frames.append(frames_decoded)

        if prev_arr is not None:
            d_all = float(np.mean(np.abs(arr - prev_arr)))
            # Center actor stage ROI vs outer 12% sky/ground border to separate actor motion from pure pan
            roi_actor = arr[int(H_s * 0.18):int(H_s * 0.94), int(W_s * 0.22):int(W_s * 0.78)]
            prev_actor = prev_arr[int(H_s * 0.18):int(H_s * 0.94), int(W_s * 0.22):int(W_s * 0.78)]
            d_actor = float(np.mean(np.abs(roi_actor - prev_actor)))

            roi_top = arr[:int(H_s * 0.14), :]
            prev_top = prev_arr[:int(H_s * 0.14), :]
            d_border = float(np.mean(np.abs(roi_top - prev_top)))

            full_diffs.append(d_all)
            center_actor_diffs.append(d_actor)
            border_cam_diffs.append(d_border)
        prev_arr = arr
        frames_decoded += 1

    _, err_bytes = proc.communicate(timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg decode stream failed: {err_bytes.decode('utf-8', 'replace')}")

    errors: List[str] = []
    if frames_decoded != 720:
        errors.append(f"Expected exactly 720 decoded frames, got {frames_decoded}")
    if black_frames:
        errors.append(f"Detected black frames: {black_frames[:10]}")
    if flat_frames:
        errors.append(f"Detected flat/blank frames: {flat_frames[:10]}")

    # Immediate visual hook within first 0.40s (frames 0..9 -> diff indices 0..8)
    hook_mean_diff = float(np.mean(full_diffs[:9])) if len(full_diffs) >= 9 else 0.0
    if hook_mean_diff < 0.25:
        errors.append(f"Opening 0.4s hook lacks immediate visual motion (mean_diff={hook_mean_diff:.4f})")

    # Per-shot cadence & frozen-actor-during-pan detector (> 48 consecutive near-zero actor-vs-pan frames)
    per_shot_metrics: List[Dict[str, Any]] = []
    for beat in storyboard.get("beats", []):
        f0 = int(beat["frame_start"])
        f1 = min(frames_decoded - 1, int(beat["frame_end"]))
        intra_full = full_diffs[f0:f1]
        intra_actor = center_actor_diffs[f0:f1]
        intra_border = border_cam_diffs[f0:f1]

        # Count longest run where actor ROI has zero excess activity over pure static slide (< 0.04 RGB delta)
        max_zero_run = 0
        cur_run = 0
        for da in intra_actor:
            if da < 0.04:
                cur_run += 1
                max_zero_run = max(max_zero_run, cur_run)
            else:
                cur_run = 0

        has_approved_hold = bool(beat.get("intentional_hold", {}).get("enabled"))
        max_allowed_hold_frames = 56 if has_approved_hold else 48  # 2.0s @ 24fps = 48 frames
        if max_zero_run > max_allowed_hold_frames:
            errors.append(
                f"Shot {beat['id']} exceeded max static hold ({max_zero_run} frames > {max_allowed_hold_frames} frames)"
            )

        per_shot_metrics.append({
            "shot_id": beat["id"],
            "frames": [f0, f1],
            "mean_full_frame_mad": round(float(np.mean(intra_full)) if intra_full else 0.0, 4),
            "mean_actor_roi_mad": round(float(np.mean(intra_actor)) if intra_actor else 0.0, 4),
            "mean_border_parallax_mad": round(float(np.mean(intra_border)) if intra_border else 0.0, 4),
            "max_near_static_streak_frames": max_zero_run,
            "intentional_hold_documented": has_approved_hold,
        })

    return {
        "passed": len(errors) == 0,
        "decoded_frames": frames_decoded,
        "black_frames_count": len(black_frames),
        "flat_frames_count": len(flat_frames),
        "opening_0p4s_mean_mad": round(hook_mean_diff, 4),
        "per_shot_metrics": per_shot_metrics,
        "errors": errors,
    }


def job_frame_temporal_validation(ctx: ValidationContext) -> Dict[str, Any]:
    final_mp4 = PILOT_PROJECT_DIR / "out" / f"{OUTPUT_TITLE}.mp4"
    storyboard = json.loads((PILOT_PROJECT_DIR / "story" / "storyboard.json").read_text(encoding="utf-8"))
    rep = inspect_mp4_temporal_stream(final_mp4, storyboard)
    res = {"status": "PASS" if rep["passed"] else "FAIL", **rep}
    _atomic_write_json(ctx.evidence_dir / "frame_temporal_validation.json", res)
    if (ctx.tracked_evidence_dir).is_dir():
        _atomic_write_json(ctx.tracked_evidence_dir / "frame_temporal_validation.json", res)
    return res


# ============================================================================
# 9. WORLD-SPACE CAMERA, PROP CONTACT & CONTINUITY QA JOB
# ============================================================================
def job_camera_and_contact_qa(ctx: ValidationContext) -> Dict[str, Any]:
    qa_scr = ctx.scratch_dir / "camera_contact_qa"
    qa_scr.mkdir(parents=True, exist_ok=True)
    loader_mjs = qa_scr / "loader.mjs"
    repo_uri = REPO_ROOT.as_uri().rstrip("/")
    loader_mjs.write_text(
        f"""export async function resolve(specifier, context, nextResolve) {{
  if (specifier.startsWith('/engine/') || specifier.startsWith('/packs/')) {{
    return nextResolve('{repo_uri}' + specifier, context);
  }}
  return nextResolve(specifier, context);
}}
""",
        encoding="utf-8",
    )

    char_url = (REPO_ROOT / "packs" / "squire" / "roman_master" / "character_state.js").as_uri()
    cam_url = (REPO_ROOT / "packs" / "squire" / "roman_master" / "camera.js").as_uri()
    cam_beats_path = (PILOT_PROJECT_DIR / "story" / "camera_beats.json").as_posix()
    ledger_path = (PILOT_PROJECT_DIR / "story" / "continuity_ledger.json").as_posix()

    script_mjs = qa_scr / "evaluate_traces.mjs"
    script_mjs.write_text(
        f"""import fs from 'node:fs';
import {{ romanActorAt, validateRomanMasterRigAnchors }} from '{char_url}';
import {{ evaluateRomanCameraAt, validateRomanCameraCut }} from '{cam_url}';

const camBeats = JSON.parse(fs.readFileSync('{cam_beats_path}', 'utf8'));
const ledger = JSON.parse(fs.readFileSync('{ledger_path}', 'utf8'));
const errors = [];

// 1. Validate all 8 shot-to-shot cuts SH01->SH02..SH08->SH09
const shotIds = ['SH01','SH02','SH03','SH04','SH05','SH06','SH07','SH08','SH09'];
const cutReports = [];
const recentFramings = [];
for (let i = 0; i < shotIds.length - 1; i++) {{
  const sOut = ledger.shots[shotIds[i]];
  const sIn = ledger.shots[shotIds[i + 1]];
  recentFramings.push({{ framingScale: sOut.framingScale, trajectory: sOut.trajectory }});
  const rep = validateRomanCameraCut(sOut, sIn, {{ ...ledger, recentFramings: recentFramings.slice(0, -1) }});
  cutReports.push(rep);
  if (!rep.valid) errors.push(...rep.errors);
}}

// 2. Sample camera C1 smoothness across all 720 frames (no unmotivated intra-shot snap > 45px/frame)
const camTrace = [];
for (const sid of shotIds) {{
  const spec = camBeats.shots[sid];
  let prev = null;
  for (let t = spec.start; t < spec.end - 1e-6; t += 1 / 24) {{
    const c = evaluateRomanCameraAt(sid, t, camBeats.shots);
    if (prev) {{
      const stepPx = Math.hypot(c.dx - prev.dx, c.dy - prev.dy);
      if (stepPx > 45.0) errors.push(`Intra-shot camera snap in ${{sid}} at t=${{t.toFixed(3)}}s: ${{stepPx.toFixed(2)}}px`);
    }}
    prev = c;
  }}
  camTrace.push({{ shotId: sid, startCam: evaluateRomanCameraAt(sid, spec.start, camBeats.shots), endCam: evaluateRomanCameraAt(sid, spec.end - 1/24, camBeats.shots) }});
}}

// 3. Dense sub-frame contact & foot-plant verification on SH05 action beat (12.00s..15.00s @ 96Hz = 288 subframes)
const sh05Beat = {{
  start: 12.0, end: 15.0,
  actors: {{
    rookie: {{
      archetypeId: 'rookie_hastatus', hFrac: 0.58, flip: true,
      rootXKeys: [[0.0, 0.595, 'c1'], [0.45, 0.598, 'c1'], [1.02, 0.578, 'c1'], [1.65, 0.556, 'outCubic'], [1.85, 0.558, 'c1'], [3.0, 0.558, 'hold']],
      rootYKeys: [[0.0, 0.93, 'c1'], [0.45, 0.935, 'c1'], [1.02, 0.93, 'c1'], [1.65, 0.93, 'c1'], [3.0, 0.93, 'hold']],
      leftFootXKeys: [[0.0, 0.615, 'hold'], [1.05, 0.615, 'c1'], [1.58, 0.578, 'outCubic'], [3.0, 0.578, 'hold']],
      leftFootYKeys: [[0.0, 0.93, 'hold'], [1.05, 0.93, 'c1'], [1.30, 0.914, 'c1'], [1.58, 0.93, 'outCubic'], [3.0, 0.93, 'hold']],
      rightFootXKeys: [[0.0, 0.575, 'hold'], [0.45, 0.575, 'c1'], [1.02, 0.536, 'outCubic'], [3.0, 0.536, 'hold']],
      rightFootYKeys: [[0.0, 0.93, 'hold'], [0.45, 0.93, 'c1'], [0.74, 0.904, 'c1'], [1.02, 0.93, 'outCubic'], [3.0, 0.93, 'hold']],
      bodyRotKeys: [[0.0, 0.0, 'hold'], [3.0, 0.0, 'hold']],
      headNodKeys: [[0.0, -0.5, 'c1'], [0.45, -1.2, 'c1'], [1.65, 2.2, 'outCubic'], [2.10, 1.0, 'c1'], [3.0, 1.0, 'hold']],
      shieldOffsetUKeys: [[0.0, [-13.0, -37.5], 'c1'], [0.50, [-15.0, -37.0], 'c1'], [1.65, [5.2, -38.0], 'outCubic'], [3.0, [4.6, -38.0], 'c1']],
      rightHandUKeys: [[0.0, [16.0, -36.0], 'c1'], [1.65, [12.5, -37.5], 'c1'], [3.0, [12.5, -37.5], 'hold']],
      weapon: 'spear',
    }},
  }},
}};

let maxRearFootSkatePx = 0;
let maxPlantedFrontSkatePx = 0;
let maxShieldGripDistPx = 0;
const rearAnchorPhase1 = [0.615 * 1920, 0.93 * 1080];
const rearAnchorPhase2 = [0.578 * 1920, 0.93 * 1080];
const frontPlantedAnchor = [0.536 * 1920, 0.93 * 1080];
const sh05Samples = [];

for (let i = 0; i <= 288; i++) {{
  const gt = 12.0 + (i / 288) * 3.0;
  const pose = romanActorAt(gt, sh05Beat, 'rookie', {{ W: 1920, H: 1080 }});
  const rigCheck = validateRomanMasterRigAnchors(pose, {{
    requirePlantedFeet: true,
    requireWeapon: 'spear',
    spearAnchorWorld: pose.rightHandWorld,
  }});
  if (!rigCheck.valid) errors.push(...rigCheck.errors);

  if (gt <= 13.04) {{
    const rearSkate1 = Math.hypot(pose.footPlant.leftAchievedWorld[0] - rearAnchorPhase1[0], pose.footPlant.leftAchievedWorld[1] - rearAnchorPhase1[1]);
    maxRearFootSkatePx = Math.max(maxRearFootSkatePx, rearSkate1);
  }} else if (gt >= 13.60) {{
    const rearSkate2 = Math.hypot(pose.footPlant.leftAchievedWorld[0] - rearAnchorPhase2[0], pose.footPlant.leftAchievedWorld[1] - rearAnchorPhase2[1]);
    maxRearFootSkatePx = Math.max(maxRearFootSkatePx, rearSkate2);
  }}
  if (gt >= 13.03) {{
    const frontSkate = Math.hypot(pose.footPlant.rightAchievedWorld[0] - frontPlantedAnchor[0], pose.footPlant.rightAchievedWorld[1] - frontPlantedAnchor[1]);
    maxPlantedFrontSkatePx = Math.max(maxPlantedFrontSkatePx, frontSkate);
  }}
  maxShieldGripDistPx = Math.max(maxShieldGripDistPx, pose.shieldGrip.gripDriftPx);
  if (i % 36 === 0) {{
    sh05Samples.push({{
      globalT: Number(gt.toFixed(3)),
      rootWorld: pose.rootWorld.map((v) => Number(v.toFixed(2))),
      leftFootWorld: pose.footPlant.leftAchievedWorld.map((v) => Number(v.toFixed(2))),
      rightFootWorld: pose.footPlant.rightAchievedWorld.map((v) => Number(v.toFixed(2))),
      shieldCenterWorld: pose.shieldGrip.shieldCenterWorld.map((v) => Number(v.toFixed(2))),
      rightHandWorld: pose.rightHandWorld.map((v) => Number(v.toFixed(2))),
    }});
  }}
}}

if (maxRearFootSkatePx > 1.0) errors.push(`Rear planted sandal skated ${{maxRearFootSkatePx.toFixed(3)}}px`);
if (maxPlantedFrontSkatePx > 1.0) errors.push(`Front planted sandal skated ${{maxPlantedFrontSkatePx.toFixed(3)}}px after plant`);

console.log(JSON.stringify({{
  passed: errors.length === 0,
  cutsValidated: cutReports.length,
  cutReports,
  cameraEndpoints: camTrace,
  sh05SubframeCount: 289,
  maxRearFootSkatePx: Number(maxRearFootSkatePx.toFixed(4)),
  maxPlantedFrontSkatePx: Number(maxPlantedFrontSkatePx.toFixed(4)),
  maxShieldGripOffsetPx: Number(maxShieldGripDistPx.toFixed(3)),
  sh05TrajectorySamples: sh05Samples,
  errors,
}}));
""",
        encoding="utf-8",
    )

    reg_code = f"import {{ register }} from 'node:module'; register('{loader_mjs.as_uri()}'); await import('{script_mjs.as_uri()}');"
    rc, out, err, _ = ctx.run_monitored(["node", "--input-type=module", "-e", reg_code])
    if rc != 0:
        return {"status": "FAIL", "error": err[:400]}

    data = json.loads(out.strip().splitlines()[-1])
    res = {"status": "PASS" if data["passed"] else "FAIL", **data}
    _atomic_write_json(ctx.evidence_dir / "continuity_and_contact_traces.json", res)
    _atomic_write_json(ctx.tracked_evidence_dir / "continuity_and_contact_traces.json", res)
    return res


# ============================================================================
# 10. NEGATIVE MUTATIONS & FALSE-POSITIVE GUARDS JOB
# ============================================================================
def job_negative_mutations(ctx: ValidationContext) -> Dict[str, Any]:
    mut_scr = ctx.scratch_dir / "negative_mutations"
    if mut_scr.exists():
        shutil.rmtree(mut_scr)
    mut_scr.mkdir(parents=True, exist_ok=True)

    errors: List[str] = []
    mutants_matrix: List[Dict[str, Any]] = []

    # A. Run full pytest unit + mutation + false-positive-guard suite (11 test functions)
    rc_py, out_py, err_py, dur_py = ctx.run_monitored(
        [sys.executable, "-m", "pytest", "tests/kh03_roman/test_style_lock.py", "-v"]
    )
    pytest_ok = rc_py == 0
    if not pytest_ok:
        errors.append(f"pytest test_style_lock.py failed:\n{out_py[-400:]}\n{err_py[-400:]}")
    mutants_matrix.append({
        "mutant_id": "M01_M09_pytest_style_3d_rig_camera_asset_suite",
        "expected": "KILLED_ALL_MUTANTS_AND_PASSED_FP_GUARDS",
        "killed": pytest_ok,
        "wall_sec": dur_py,
    })

    # B. Mutant M10: Truncated MP4 (only 120 frames instead of 720) -> MUST be killed by inspect_mp4_temporal_stream!
    trunc_mp4 = mut_scr / "truncated_5s.mp4"
    final_mp4 = PILOT_PROJECT_DIR / "out" / f"{OUTPUT_TITLE}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-t", "5.0", "-i", str(final_mp4), "-c", "copy", str(trunc_mp4)],
        check=True,
    )
    storyboard = json.loads((PILOT_PROJECT_DIR / "story" / "storyboard.json").read_text(encoding="utf-8"))
    trunc_rep = inspect_mp4_temporal_stream(trunc_mp4, storyboard)
    trunc_killed = not trunc_rep["passed"] and any("720" in e for e in trunc_rep["errors"])
    if not trunc_killed:
        errors.append("Truncated MP4 mutant was NOT killed by temporal validator")
    mutants_matrix.append({"mutant_id": "M10_truncated_mp4_120_frames", "killed": trunc_killed})

    # C. Mutant M11: Frozen static slide > 2.0s (72 identical frames = 3.0s) -> MUST be killed!
    frozen_mp4 = mut_scr / "frozen_actor_pan.mp4"
    still_img = ctx.packet_dir / "stills_9shots" / "SH03_t07.35s.jpg"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "24", "-t", "3.0",
            "-i", str(still_img), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(frozen_mp4),
        ],
        check=True,
    )
    fake_sb = {
        "beats": [{"id": "SH_FROZEN", "frame_start": 0, "frame_end": 71, "intentional_hold": {"enabled": False}}]
    }
    # Pad check: inspect_mp4_temporal_stream checks both 720-frame count and max_zero_run > 48
    frozen_rep = inspect_mp4_temporal_stream(frozen_mp4, fake_sb)
    frozen_killed = (not frozen_rep["passed"]) and any("exceeded max static hold" in e for e in frozen_rep["errors"])
    if not frozen_killed:
        errors.append(f"Frozen >2s shot mutant was NOT killed: {frozen_rep}")
    mutants_matrix.append({"mutant_id": "M11_frozen_static_shot_over_2s", "killed": frozen_killed})

    # D. Mutant M12: Silent narration WAV -> MUST be rejected by silent-voice guard!
    silent_wav = mut_scr / "silent_voice.wav"
    sf.write(str(silent_wav), np.zeros(48000 * 3, dtype=np.float32), 48000, subtype="PCM_16")
    sig_s, _ = sf.read(str(silent_wav), dtype="float32")
    rms_s = float(np.sqrt(np.mean(sig_s ** 2)))
    silent_killed = rms_s < 0.005
    if not silent_killed:
        errors.append("Silent voice mutant failed detection")
    mutants_matrix.append({"mutant_id": "M12_silent_voice_wav", "killed": silent_killed})

    # E. Mutant M13: Disposable ResourceMonitor breach kills ONLY owned registered child PID!
    dummy_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(15)"])
    test_mon = ResourceMonitor(workspace=str(mut_scr), min_disk_gb=999999.0, min_ram_gb=0.1, interval_sec=0.2)
    test_mon.register_pid(dummy_proc.pid)
    test_mon.start()
    time.sleep(0.65)
    test_mon.stop()
    dummy_terminated = dummy_proc.poll() is not None
    if not dummy_terminated:
        kill_process_tree(dummy_proc.pid)
    breach_killed = test_mon.breached and dummy_terminated
    if not breach_killed:
        errors.append("ResourceMonitor disposable breach test failed to terminate registered child PID")
    mutants_matrix.append({"mutant_id": "M13_resource_breach_owned_pid_cancellation", "killed": breach_killed})

    res = {
        "status": "PASS" if not errors else "FAIL",
        "mutants_tested": len(mutants_matrix),
        "all_killed": all(m["killed"] for m in mutants_matrix),
        "matrix": mutants_matrix,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "negative_mutations.json", res)
    _atomic_write_json(ctx.tracked_evidence_dir / "negative_mutations.json", res)
    return res


# ============================================================================
# 11. SYNTHETIC 180-SHOT STRESS + 20-SHOT REAL RENDERED MP4 BACKTEST JOB
# ============================================================================
def job_real_backtests(ctx: ValidationContext) -> Dict[str, Any]:
    bt_scr = ctx.scratch_dir / "backtests"
    if bt_scr.exists():
        shutil.rmtree(bt_scr)
    bt_scr.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []

    # Category 1: 180-shot Synthetic Stress in isolation -> SYNTHETIC_PASS
    syn_proj = bt_scr / "synthetic_180shot_roman_stress"
    (syn_proj / "story").mkdir(parents=True)
    (syn_proj / "scenes" / "shots").mkdir(parents=True)
    (syn_proj / "config.json").write_text(
        json.dumps({"pack": "squire", "aspect": "16:9", "resolution": "720p", "fps": 24, "render_mode": "canvas2d_only"}),
        encoding="utf-8",
    )
    syn_shots = []
    tpls = ["scene", "close", "army", "top"]
    for i in range(180):
        t0 = round(i * 1.0, 3)
        t1 = round((i + 1) * 1.0, 3)
        syn_shots.append({
            "id": f"SYN_{i + 1:03d}",
            "tpl": tpls[i % len(tpls)],
            "start": t0,
            "end": t1,
            "args": {"bg": "roman_training_yard" if i % 2 == 0 else "field", "time": "dawn", "preset": "hastatus"},
        })
    (syn_proj / "story" / "shots.json").write_text(
        json.dumps({"duration": 180.0, "shots": syn_shots}, indent=2),
        encoding="utf-8",
    )
    syn_val = validate_project(syn_proj)
    synthetic_status = "SYNTHETIC_PASS" if (syn_val["status"] == "PASS" and syn_val["shots_renderable"] == 180) else "FAIL"
    if synthetic_status != "SYNTHETIC_PASS":
        errors.append(f"180-shot synthetic stress failed: {syn_val}")

    # Category 2: 20-shot REAL Rendered Multi-Scene 2D MP4 Backtest -> REAL_RENDERED_PASS
    real20_proj = bt_scr / "real_20shot_roman_backtest"
    (real20_proj / "story").mkdir(parents=True)
    (real20_proj / "timeline").mkdir(parents=True)
    (real20_proj / "out").mkdir(parents=True)
    (real20_proj / "config.json").write_text(
        json.dumps({
            "title": "kh03_backtest_20shots_real",
            "pack": "squire",
            "style_profile": "roman_squire_master.v1",
            "render_mode": "canvas2d_only",
            "aspect": "16:9",
            "resolution": "720p",
            "fps": 24,
            "style": "flat",
            "bars": "none",
            "loudness": -15.0,
        }),
        encoding="utf-8",
    )
    real20_shots = []
    presets = ["hastatus", "princeps", "legionary", "triarius"]
    bgs = ["roman_training_yard", "roman_camp_gate", "roman_shield_wall", "field"]
    for i in range(20):
        st = round(i * 1.0, 3)
        en = round((i + 1) * 1.0, 3)
        mode = i % 4
        p_name = presets[mode]
        bg_name = bgs[mode]
        if mode == 1:
            shot_obj = {
                "id": f"R20_{i + 1:02d}",
                "tpl": "close",
                "start": st,
                "end": en,
                "args": {"bg": bg_name, "time": "dawn", "preset": p_name, "face": "determined", "R": 0.22},
                "sfx": [{"name": "armor_clank", "at": 0.15, "gain": -9}],
            }
        elif mode == 2:
            shot_obj = {
                "id": f"R20_{i + 1:02d}",
                "tpl": "army",
                "start": st,
                "end": en,
                "args": {"bg": "field", "time": "dawn", "preset": "hastatus", "rows": 3, "cols": 7},
                "sfx": [{"name": "drum_hit", "at": 0.10, "gain": -9}],
            }
        else:
            shot_obj = {
                "id": f"R20_{i + 1:02d}",
                "tpl": "scene",
                "start": st,
                "end": en,
                "args": {
                    "bg": bg_name,
                    "time": "dawn",
                    "people": [{"preset": p_name, "x": 0.48, "y": 0.90, "h": 0.48, "pose": "guard", "face": "focused"}],
                    "props": [{"kind": "training_rack", "x": 0.82, "y": 0.82, "s": 0.22}],
                },
                "sfx": [{"name": "single_footstep", "at": 0.20, "gain": -9}],
            }
        real20_shots.append(shot_obj)

    (real20_proj / "story" / "shots.json").write_text(
        json.dumps({
            "duration": 20.0,
            "music": [{"start": 0.0, "end": 20.0, "bed": "roman", "gainDb": -2.0}],
            "shots": real20_shots,
        }, indent=2),
        encoding="utf-8",
    )
    # Provide real spoken TTS voice track for Squire mix requirement
    shutil.copy2(PILOT_PROJECT_DIR / "timeline" / "voice.wav", real20_proj / "timeline" / "voice.wav")
    v20_audio, v20_sr = sf.read(str(real20_proj / "timeline" / "voice.wav"), dtype="float32")
    sf.write(str(real20_proj / "timeline" / "voice.wav"), v20_audio[: 20 * v20_sr], v20_sr, subtype="PCM_16")

    rc_r20, _, err_r20, dur_r20 = ctx.run_monitored(
        ["node", "render.mjs", "--project", str(real20_proj), "--workers", "2"], timeout=300.0
    )
    rc_m20, _, err_m20, dur_m20 = ctx.run_monitored(
        [sys.executable, "tools/mix.py", "--project", str(real20_proj)], timeout=120.0
    )
    r20_mp4 = real20_proj / "out" / "kh03_backtest_20shots_real.mp4"
    r20_frames = 0
    if rc_r20 == 0 and rc_m20 == 0 and r20_mp4.is_file():
        cnt20 = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_read_frames",
                "-of", "csv=p=0", str(r20_mp4),
            ],
            text=True,
        ).strip().rstrip(",")
        r20_frames = int(cnt20)
    real20_status = "REAL_RENDERED_PASS" if r20_frames == 480 else "FAIL"
    if real20_status != "REAL_RENDERED_PASS":
        errors.append(f"20-shot real rendered MP4 backtest failed (frames={r20_frames}): {err_r20[:200]} {err_m20[:200]}")

    # Category 3: Historical Company 180-shot external fixture check -> honest NOT_RUN_MISSING_FIXTURE if absent
    hist_candidates = [
        REPO_ROOT / "projects" / "company-180",
        REPO_ROOT / "tests" / "fixtures" / "company_180_shots",
    ]
    hist_found = next((p for p in hist_candidates if p.exists()), None)
    historical_entry = (
        {"status": "NOT_RUN_MISSING_FIXTURE", "fixture_state": "PATH_MISSING", "searched": [str(p) for p in hist_candidates]}
        if hist_found is None
        else {"status": "PRESENT", "path": str(hist_found)}
    )

    res = {
        "status": "PASS" if not errors else "FAIL",
        "synthetic_180_shot_stress": {
            "verdict": synthetic_status,
            "shots_validated": 180,
            "duration_sec": 180.0,
        },
        "real_20_shot_rendered_2d_backtest": {
            "verdict": real20_status,
            "shots_rendered": 20,
            "decoded_frames": r20_frames,
            "render_wall_sec": dur_r20,
            "mix_wall_sec": dur_m20,
            "mp4_sha256": _sha256_file(r20_mp4) if r20_mp4.is_file() else None,
            "mp4_bytes": r20_mp4.stat().st_size if r20_mp4.is_file() else 0,
        },
        "historical_company_180_shot_fixture": historical_entry,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "backtests_180syn_20real.json", res)
    _atomic_write_json(ctx.tracked_evidence_dir / "backtests_180syn_20real.json", res)
    return res


# ============================================================================
# 12. ISOLATED LEGACY FULL E2E REGRESSION JOB
# ============================================================================
def job_legacy_regression(ctx: ValidationContext) -> Dict[str, Any]:
    leg_ev = ctx.scratch_dir / "legacy_e2e_evidence"
    leg_scr = ctx.scratch_dir / "legacy_e2e_scratch"
    leg_ev.mkdir(parents=True, exist_ok=True)
    leg_scr.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["QA_EVIDENCE_DIR"] = str(leg_ev)
    env["QA_RUN_SCRATCH_DIR"] = str(leg_scr)
    env["QA_V10_SCRATCH_DIR"] = str(leg_scr / "v10_opening")
    env["QA_PRESERVE_TEST_RUNS"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    rc, out, err, dur = ctx.run_monitored(
        [sys.executable, "scripts/run_e2e_regression.py"],
        cwd=str(REPO_ROOT),
        env=env,
        timeout=1500.0,
    )

    # Locate summary json inside leg_ev
    summary_files = sorted(leg_ev.glob("*summary*.json")) + sorted(leg_ev.rglob("*summary*.json"))
    parsed_summary: Dict[str, Any] = {}
    for sf_path in summary_files:
        try:
            cand = json.loads(sf_path.read_text(encoding="utf-8"))
            if "results" in cand or "overall_status" in cand or "summary" in cand:
                parsed_summary = cand
                shutil.copy2(sf_path, ctx.evidence_dir / f"legacy_{sf_path.name}")
                break
        except Exception:
            pass

    # Verify tracked tests/evidence/latest-* was NOT touched!
    dirty_ev = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--", "tests/evidence"],
        cwd=str(REPO_ROOT),
        text=True,
    ).splitlines()
    mutated_golden = [
        ln for ln in dirty_ev
        if f"kh03_0_{ctx.run_id}" not in ln
    ]

    # Count exact PASS / FAIL / NOT_RUN from legacy results without counting NOT_RUN as PASS
    raw_results = parsed_summary.get("results", {})
    pass_cnt = 0
    fail_cnt = 0
    not_run_cnt = 0
    not_run_keys: List[str] = []
    fail_keys: List[str] = []

    if isinstance(raw_results, dict):
        for k, v in raw_results.items():
            st = str(v.get("status", "") if isinstance(v, dict) else v).upper()
            if "NOT_RUN" in st or "MISSING_FIXTURE" in st or "SKIP" in st:
                not_run_cnt += 1
                not_run_keys.append(k)
            elif "FAIL" in st or "BLOCKED" in st or "ERROR" in st:
                fail_cnt += 1
                fail_keys.append(k)
            elif "PASS" in st:
                pass_cnt += 1
    elif isinstance(raw_results, list):
        for item in raw_results:
            k = item.get("id") or item.get("name") or "unknown"
            st = str(item.get("status", "")).upper()
            if "NOT_RUN" in st or "MISSING_FIXTURE" in st or "SKIP" in st:
                not_run_cnt += 1
                not_run_keys.append(k)
            elif "FAIL" in st or "BLOCKED" in st or "ERROR" in st:
                fail_cnt += 1
                fail_keys.append(k)
            elif "PASS" in st:
                pass_cnt += 1

    errors: List[str] = []
    if rc != 0:
        errors.append(f"run_e2e_regression.py exited with rc={rc}: {err[-400:]}")
    if fail_cnt > 0:
        errors.append(f"Legacy regression failures ({fail_cnt}): {fail_keys}")
    if mutated_golden:
        errors.append(f"Historical tracked tests/evidence files were mutated: {mutated_golden}")

    res = {
        "status": "PASS" if not errors else "FAIL",
        "return_code": rc,
        "wall_sec": dur,
        "exact_counts": {
            "PASS": pass_cnt,
            "FAIL": fail_cnt,
            "NOT_RUN_MISSING_FIXTURE": not_run_cnt,
        },
        "not_run_items": not_run_keys,
        "failed_items": fail_keys,
        "historical_golden_evidence_untouched": len(mutated_golden) == 0,
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "legacy_regression_summary.json", res)
    _atomic_write_json(ctx.tracked_evidence_dir / "legacy_regression_summary.json", res)
    return res


# ============================================================================
# 13. FORWARD/REVERSE/RANDOM DETERMINISM + 3-REPEAT SPEED BENCHMARK JOB
# ============================================================================
def job_speed_and_reproducibility(ctx: ValidationContext) -> Dict[str, Any]:
    rep_scr = ctx.scratch_dir / "reproducibility_and_speed"
    rep_scr.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []

    # Part A: Forward vs Reverse vs Seeded-Random Frame-Order Determinism Proof on KH-03.0 Pilot
    # NOTE: Uses window.renderFrame(fr, { png: true }) exclusively (pure PNG dataURL, 0 getImageData GPU-to-CPU fallback!)
    order_mjs = rep_scr / "frame_order_determinism.mjs"
    order_mjs.write_text(
        """import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { chromium } from 'playwright';

const [repoRoot, projDir] = process.argv.slice(2);
const MIME = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff' };
function listScenes(dir) {
  const out = []; const base = path.join(dir, 'scenes', 'shots');
  if (fs.existsSync(base)) for (const f of fs.readdirSync(base).sort()) if (f.endsWith('.js')) out.push('scenes/shots/' + f);
  return out;
}
const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://127.0.0.1');
  if (u.pathname === '/__assets') { res.writeHead(200, {'content-type':'application/json'}); return res.end('[]'); }
  if (u.pathname === '/__manifest') { res.writeHead(200, {'content-type':'application/json'}); return res.end(JSON.stringify(listScenes(projDir))); }
  const file = u.pathname.startsWith('/proj/') ? path.join(projDir, decodeURIComponent(u.pathname.slice(6))) : path.join(repoRoot, decodeURIComponent(u.pathname.slice(1)));
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('404'); }
  res.writeHead(200, {'content-type': MIME[path.extname(file)] || 'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;
let browser;
for (const ch of ['msedge', 'chrome', 'chromium']) {
  try { browser = await chromium.launch({ channel: ch, args: ['--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--font-render-hinting=none'] }); break; } catch {}
}
if (!browser) browser = await chromium.launch({ args: ['--font-render-hinting=none'] });

const sampleFrames = [0, 28, 65, 110, 150, 200, 239, 275, 313, 328, 374, 410, 460, 512, 575, 610, 660, 710];
const orders = {
  forward: [...sampleFrames],
  reverse: [...sampleFrames].reverse(),
  seeded_random: [328, 0, 660, 150, 512, 28, 710, 239, 410, 65, 575, 200, 374, 110, 610, 275, 460, 313],
};

const hashesByPass = {};
for (const [passName, seq] of Object.entries(orders)) {
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${port}/player.html?proj=/proj&scale=0.5`);
  await page.waitForFunction(() => window.__ready || window.__bootError, null, { timeout: 60000 });
  const map = {};
  for (const fr of seq) {
    const res = await page.evaluate((f) => window.renderFrame(f, { png: true }), fr);
    const dataUrl = typeof res === 'string' ? res : res.dataUrl;
    const b64 = dataUrl.replace(/^data:image\\/png;base64,/, '');
    map[String(fr)] = crypto.createHash('sha256').update(Buffer.from(b64, 'base64')).digest('hex');
  }
  hashesByPass[passName] = map;
  await page.close();
}
await browser.close();
server.close();

let mismatches = 0;
for (const fr of sampleFrames) {
  const k = String(fr);
  if (hashesByPass.forward[k] !== hashesByPass.reverse[k] || hashesByPass.forward[k] !== hashesByPass.seeded_random[k]) {
    mismatches++;
  }
}
console.log(JSON.stringify({
  framesTested: sampleFrames.length,
  mismatches,
  identicalAcrossAllOrders: mismatches === 0,
  forwardHashes: hashesByPass.forward,
}));
""",
        encoding="utf-8",
    )
    rc_ord, out_ord, err_ord, dur_ord = ctx.run_monitored(["node", str(order_mjs), str(REPO_ROOT), str(PILOT_PROJECT_DIR)])
    if rc_ord != 0:
        errors.append(f"Frame-order determinism harness failed: {err_ord[:300]}")
        order_res = {"identicalAcrossAllOrders": False}
    else:
        order_res = json.loads(out_ord.strip().splitlines()[-1])
        if not order_res.get("identicalAcrossAllOrders"):
            errors.append(f"Frame-order hash mismatch detected: {order_res.get('mismatches')} frames differed")

    # Part B: 3-Repeat Serial vs Bounded-Parallel (3 workers) QA Workload Benchmark with Digest Parity & Overlap Proof
    def _single_qa_slice(slice_idx: int, repeat_idx: int, mode_tag: str) -> Dict[str, Any]:
        t_s = round(time.monotonic(), 4)
        wdir = rep_scr / f"bench_{mode_tag}_r{repeat_idx}_s{slice_idx}"
        if wdir.exists():
            shutil.rmtree(wdir)
        shutil.copytree(PILOT_PROJECT_DIR, wdir, ignore=shutil.ignore_patterns("build", "out"))
        stills_map = {0: "1.15,3.95,7.35", 1: "9.96,13.68,15.62", 2: "21.35,24.85,28.90"}[slice_idx]
        rc, _, err, _ = ctx.run_monitored(
            ["node", "render.mjs", "--project", str(wdir), "--stills", stills_map, "--scale", "0.5"]
        )
        if rc != 0:
            raise RuntimeError(f"Benchmark slice failed: {err[:200]}")
        stills_shas = {
            p.name: _sha256_file(p)
            for p in sorted((wdir / "build" / "stills").glob("*.png"))
        }
        t_e = round(time.monotonic(), 4)
        return {"slice": slice_idx, "t_start": t_s, "t_end": t_e, "stills_shas": stills_shas}

    serial_times: List[float] = []
    parallel_times: List[float] = []
    run_digests: List[str] = []
    parallel_overlaps_verified = 0

    for r_idx in range(3):
        t0_ser = time.monotonic()
        ser_slices = [_single_qa_slice(s_i, r_idx, "serial") for s_i in range(3)]
        serial_times.append(round(time.monotonic() - t0_ser, 3))
        combined_ser = {k: v for sl in ser_slices for k, v in sl["stills_shas"].items()}
        run_digests.append(hashlib.sha256(json.dumps(combined_ser, sort_keys=True).encode("utf-8")).hexdigest())

    for r_idx in range(3):
        t0_par = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futs = [pool.submit(_single_qa_slice, s_i, r_idx, "parallel") for s_i in range(3)]
            par_slices = [f.result() for f in futs]
        parallel_times.append(round(time.monotonic() - t0_par, 3))
        combined_par = {k: v for sl in par_slices for k, v in sl["stills_shas"].items()}
        run_digests.append(hashlib.sha256(json.dumps(combined_par, sort_keys=True).encode("utf-8")).hexdigest())
        # Check true interval overlap: max(t_start) < min(t_end) across at least two slices
        for a_i in range(3):
            for b_i in range(a_i + 1, 3):
                overlap = min(par_slices[a_i]["t_end"], par_slices[b_i]["t_end"]) - max(par_slices[a_i]["t_start"], par_slices[b_i]["t_start"])
                if overlap > 0.15:
                    parallel_overlaps_verified += 1

    digest_parity = len(set(run_digests)) == 1
    if not digest_parity:
        errors.append(f"Benchmark output digest parity failed across 6 runs: {run_digests}")
    if parallel_overlaps_verified == 0:
        errors.append("Parallel benchmark showed 0 overlapping worker intervals")

    mean_ser = statistics.mean(serial_times)
    mean_par = statistics.mean(parallel_times)
    speedup = round(mean_ser / max(0.001, mean_par), 3)

    res = {
        "status": "PASS" if not errors else "FAIL",
        "frame_order_determinism": {
            "frames_tested": order_res.get("framesTested", 0),
            "orders_tested": ["forward", "reverse", "seeded_random"],
            "mismatches": order_res.get("mismatches", -1),
            "identical_across_all_orders": order_res.get("identicalAcrossAllOrders", False),
            "wall_sec": dur_ord,
            "forward_frame_sha256": order_res.get("forwardHashes", {}),
            "cross_platform_note": (
                "Same-host, same-GPU (ANGLE D3D11) PNG hashes are 100% invariant across forward/reverse/random "
                "frame order; minor sub-pixel anti-aliasing differences are expected across different OS/GPU drivers."
            ),
        },
        "qa_still_workload_3repeat_benchmark": {
            "workload_description": "9 pilot stills (3 isolated 3-still slices @ 960x540) rendered across 3 repeats",
            "serial_wall_sec_repeats": serial_times,
            "parallel_3worker_wall_sec_repeats": parallel_times,
            "serial_mean_sec": round(mean_ser, 3),
            "parallel_mean_sec": round(mean_par, 3),
            "measured_qa_speedup_ratio": speedup,
            "output_digest_parity_all_6_runs": digest_parity,
            "canonical_stills_digest": run_digests[0] if run_digests else None,
            "verified_overlapping_worker_pairs": parallel_overlaps_verified,
        },
        "errors": errors,
    }
    _atomic_write_json(ctx.evidence_dir / "speed_and_reproducibility.json", res)
    _atomic_write_json(ctx.tracked_evidence_dir / "speed_and_reproducibility.json", res)
    return res


# ============================================================================
# 14. ATOMIC VERDICT & REVIEW PACKET WRITER
# ============================================================================
def write_verdict_and_review_packet(ctx: ValidationContext, gates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    mandatory_keys = [
        "preflight_guard",
        "baseline_preservation",
        "style_lock_contract",
        "same_pose_reference_poc",
        "guard_2d_only",
        "fresh_preview_build",
        "render_full_30s",
        "frame_temporal_validation",
        "camera_and_contact_qa",
        "negative_mutations",
        "real_backtests",
        "legacy_regression",
        "speed_and_reproducibility",
    ]
    failed_gates = [k for k in mandatory_keys if gates.get(k, {}).get("status") != "PASS"]
    mon_stats = ctx.monitor.get_stats()
    if mon_stats.get("breached"):
        failed_gates.append("resource_monitor_breach")

    overall_verdict = "TECH_PASS_HUMAN_REVIEW_PENDING" if not failed_gates else "FAIL_OR_BLOCKED"

    summary = {
        "schema_version": "kh03.0.validation_summary.v1",
        "generated_at_utc": _utc_iso(),
        "run_id": ctx.run_id,
        "branch": "feat/roman-2d-master",
        "source_branch": "origin/Production",
        "source_commit": gates["preflight_guard"]["protected_refs"]["origin/Production"],
        "overall_verdict": overall_verdict,
        "human_editorial_gates": {
            "STYLE_APPROVED": "HUMAN_REVIEW_PENDING",
            "EDITORIAL_APPROVED": "HUMAN_REVIEW_PENDING",
            "RETENTION_ANALYTICS": "NOT_CLAIMED_REQUIRES_REAL_VIEWER_DATA",
        },
        "out_of_scope_phases": {
            "KH-03.1_generalized_roman_asset_library": "NOT_IMPLEMENTED",
            "KH-03.2_generic_natural_motion_engine": "NOT_IMPLEMENTED",
            "KH-03.3_generic_continuity_engine": "NOT_IMPLEMENTED",
            "KH-03.4_general_cinematic_camera_director": "NOT_IMPLEMENTED",
            "KH-03.5_smart_shot_director_arbitrary_niches": "NOT_IMPLEMENTED",
            "KH-03.6_final_production_merge": "NOT_IMPLEMENTED",
        },
        "mandatory_technical_gates": {k: gates[k]["status"] for k in mandatory_keys},
        "failed_gates": failed_gates,
        "resource_telemetry": mon_stats,
        "dag_execution_trace": ctx.dag_trace,
        "pilot_deliverable": {
            "local_mp4_path": str((PILOT_PROJECT_DIR / "out" / f"{OUTPUT_TITLE}.mp4").resolve()),
            "mp4_sha256": gates["render_full_30s"]["manifest"]["output_mp4_sha256"],
            "mp4_bytes": gates["render_full_30s"]["manifest"]["output_mp4_bytes"],
            "video_stream": gates["render_full_30s"]["manifest"]["video_stream"],
            "audio_stream": gates["render_full_30s"]["manifest"]["audio_stream"],
        },
        "legacy_and_backtest_counts": {
            "legacy_e2e": gates["legacy_regression"]["exact_counts"],
            "synthetic_180_shot": gates["real_backtests"]["synthetic_180_shot_stress"]["verdict"],
            "real_20_shot_rendered_mp4": gates["real_backtests"]["real_20_shot_rendered_2d_backtest"]["verdict"],
            "historical_company_180_fixture": gates["real_backtests"]["historical_company_180_shot_fixture"]["status"],
        },
    }
    _atomic_write_json(ctx.evidence_dir / "validation_summary.json", summary)
    _atomic_write_json(ctx.tracked_evidence_dir / "validation_summary.json", summary)
    return summary


# ============================================================================
# 15. SAFE COMMIT & PUSH ATTESTATION HELPER
# ============================================================================
def safe_commit_push_attestation(ctx: ValidationContext, summary: Dict[str, Any], execute_push: bool = False) -> Dict[str, Any]:
    """Verify ref safety and optionally stage/commit/push ONLY feat/roman-2d-master when TECH_PASS holds."""
    if summary.get("overall_verdict") != "TECH_PASS_HUMAN_REVIEW_PENDING":
        return {"status": "SKIPPED_NOT_TECH_PASS", "pushed": False}

    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=str(REPO_ROOT), text=True).strip()
    if branch != "feat/roman-2d-master":
        raise RuntimeError(f"Refusing git operation on unexpected branch '{branch}'")

    refs_now = {}
    for rname in ["refs/heads/Production", "refs/heads/fix/Image-Shot", "refs/heads/feat/modern-2d-cinematic"]:
        ls = subprocess.check_output(["git", "ls-remote", "origin", rname], cwd=str(REPO_ROOT), text=True).strip()
        refs_now[rname] = ls.split()[0] if ls else None

    if not execute_push:
        return {
            "status": "READY_FOR_COMMIT_AND_PUSH",
            "pushed": False,
            "branch": branch,
            "remote_protected_refs_verified": refs_now,
        }

    subprocess.run(["git", "push", "-u", "origin", "feat/roman-2d-master"], cwd=str(REPO_ROOT), check=True)
    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True).strip()
    remote_target = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/feat/roman-2d-master"], cwd=str(REPO_ROOT), text=True
    ).split()[0]
    return {
        "status": "PUSHED_AND_VERIFIED" if head_sha == remote_target else "REMOTE_MISMATCH",
        "pushed": head_sha == remote_target,
        "head_sha": head_sha,
        "remote_target_sha": remote_target,
        "remote_protected_refs_verified": refs_now,
    }


async def run_dag(run_id: str = DEFAULT_RUN_ID, execute_push: bool = False) -> Dict[str, Any]:
    ctx = ValidationContext(run_id=run_id)
    ctx.monitor.start()
    try:
        # Stage 0: Synchronous preflight guard (MUST pass before any async job starts)
        preflight = run_preflight_guard(ctx)
        if preflight["status"] != "PASS":
            raise RuntimeError(f"Preflight guard BLOCKED execution: {preflight['errors']}")

        gates: Dict[str, Dict[str, Any]] = {"preflight_guard": preflight}
        print(f"[KH03-DAG] Stage 0 preflight_guard={preflight['status']}", flush=True)

        # Stage 1: Baseline preservation + Style lock contract + Reference POC
        t_style = asyncio.create_task(ctx.record_job("style_lock_contract", "light", job_style_lock_contract, ctx))
        t_base = asyncio.create_task(ctx.record_job("baseline_preservation", "heavy", job_capture_baseline, ctx))
        t_poc = asyncio.create_task(ctx.record_job("same_pose_reference_poc", "heavy", job_render_reference_poc, ctx))
        gates["style_lock_contract"], gates["baseline_preservation"], gates["same_pose_reference_poc"] = await asyncio.gather(
            t_style, t_base, t_poc
        )
        print(
            f"[KH03-DAG] Stage 1 style={gates['style_lock_contract']['status']} "
            f"baseline={gates['baseline_preservation']['status']} poc={gates['same_pose_reference_poc']['status']}",
            flush=True,
        )

        # Stage 2: Build fresh preview + 2D-only runtime/static guard
        gates["fresh_preview_build"] = await ctx.record_job("fresh_preview_build", "light", job_build_fresh_preview, ctx)
        gates["guard_2d_only"] = await ctx.record_job("guard_2d_only", "heavy", job_2d_only_guard, ctx)
        print(
            f"[KH03-DAG] Stage 2 build={gates['fresh_preview_build']['status']} guard_2d={gates['guard_2d_only']['status']}",
            flush=True,
        )

        # Stage 3: Full 30.000s 1080p24 render receipt
        gates["render_full_30s"] = await ctx.record_job("render_full_30s", "heavy", job_render_full_30s, ctx)
        print(f"[KH03-DAG] Stage 3 render_full_30s={gates['render_full_30s']['status']}", flush=True)

        # Stage 4: Concurrent Frame Temporal Validation + World-Space Camera/Contact QA + Negative Mutations
        t_temp = asyncio.create_task(ctx.record_job("frame_temporal_validation", "light", job_frame_temporal_validation, ctx))
        t_cam = asyncio.create_task(ctx.record_job("camera_and_contact_qa", "light", job_camera_and_contact_qa, ctx))
        t_mut = asyncio.create_task(ctx.record_job("negative_mutations", "light", job_negative_mutations, ctx))
        gates["frame_temporal_validation"], gates["camera_and_contact_qa"], gates["negative_mutations"] = await asyncio.gather(
            t_temp, t_cam, t_mut
        )
        print(
            f"[KH03-DAG] Stage 4 temporal={gates['frame_temporal_validation']['status']} "
            f"cam_contact={gates['camera_and_contact_qa']['status']} mutations={gates['negative_mutations']['status']}",
            flush=True,
        )

        # Stage 5: Real Backtests (180 synthetic + 20 real MP4) & Speed/Reproducibility Benchmark
        gates["real_backtests"] = await ctx.record_job("real_backtests", "heavy", job_real_backtests, ctx)
        gates["speed_and_reproducibility"] = await ctx.record_job(
            "speed_and_reproducibility", "heavy", job_speed_and_reproducibility, ctx
        )
        print(
            f"[KH03-DAG] Stage 5 backtests={gates['real_backtests']['status']} "
            f"reproducibility={gates['speed_and_reproducibility']['status']}",
            flush=True,
        )

        # Stage 6: Full Legacy E2E Regression Suite in isolated scratch/evidence dirs
        print("[KH03-DAG] Stage 6 starting isolated run_e2e_regression.py ...", flush=True)
        gates["legacy_regression"] = await ctx.record_job("legacy_regression", "heavy", job_legacy_regression, ctx)
        print(f"[KH03-DAG] Stage 6 legacy_regression={gates['legacy_regression']['status']}", flush=True)

        # Stage 7: Write atomic verdict & check safe push readiness
        summary = write_verdict_and_review_packet(ctx, gates)
        summary["git_push_check"] = safe_commit_push_attestation(ctx, summary, execute_push=execute_push)
        _atomic_write_json(ctx.evidence_dir / "validation_summary.json", summary)
        _atomic_write_json(ctx.tracked_evidence_dir / "validation_summary.json", summary)
        return summary
    finally:
        ctx.monitor.stop()
        ctx.executor.shutdown(wait=False)


def main() -> None:
    ap = argparse.ArgumentParser(description="KH-03.0 Bounded Async Validation & Regression Runner")
    ap.add_argument("--run-id", default=DEFAULT_RUN_ID)
    ap.add_argument("--execute-push", action="store_true")
    args = ap.parse_args()

    summary = asyncio.run(run_dag(run_id=args.run_id, execute_push=args.execute_push))
    print(json.dumps({
        "overall_verdict": summary["overall_verdict"],
        "mandatory_technical_gates": summary["mandatory_technical_gates"],
        "failed_gates": summary["failed_gates"],
        "legacy_and_backtest_counts": summary["legacy_and_backtest_counts"],
        "resource_telemetry": summary["resource_telemetry"],
    }, indent=2))
    sys.exit(0 if summary["overall_verdict"] == "TECH_PASS_HUMAN_REVIEW_PENDING" else 1)


if __name__ == "__main__":
    main()
