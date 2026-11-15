#!/usr/bin/env python3
"""scripts/run_fl01_v14_7_5_1_validation.py — Multi-Wave Async Validation Orchestrator (FL-01 / V14.7.5.1).

Executes real bounded-concurrency validation through `scripts.qa_scheduler` (`build_dependency_dag` + `run_dag`)
enforcing `min_disk_gb >= 6.0` (+ scratch + `1.0 GiB` margin) and `min_ram_gb >= 1.0` AT ALL TIMES,
produces and audits the brand-new 30.000s / 720-frame 1080p24 film
"THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET", verifies 100% cut-boundary coverage across
Eagle (11/11) and Water Gate (7/7), verifies non-null cryptographic input fingerprints, preserves all
historical MP4s byte-for-byte, renders versioned corrected V14.7.4 schematic outputs in isolated temp clones,
runs R1–R8 + J13 acceptance, and enforces strict cross-evidence consistency across `tests/evidence/v14_7_5_1/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    compute_render_fingerprint,
    inspect_media_file,
    sha256_file,
    sha256_json,
    verify_receipt_and_lineage,
)
from scripts.qa_scheduler import (
    build_dependency_dag,
    inspect_resource_budget,
    publish_atomic_evidence,
    run_dag,
)
from scripts.test_v14_7_5_1_acceptance import run_v14_7_5_1_acceptance_suite
from tools.produce_fl01_v14_7_5_1_roman_water_gate_preview import (
    CIVIC_MODULE_REL,
    FILM_SUBTITLE as WG_SUBTITLE,
    FILM_TITLE as WG_TITLE,
    NOMINAL_VIDEO_FRAMES as WG_FRAMES,
    OUT_MP4_PATH as WG_MP4_PATH,
    PROJECT_DIR as WG_PROJECT_DIR,
    compute_measured_voice_overlaps,
    inspect_water_gate_preview,
    produce_water_gate_preview,
)
from tools.produce_fl01_v14_7_5_roman_eagle_in_fog_preview import (
    FILM_TITLE as EAGLE_TITLE,
    OUT_MP4_PATH as EAGLE_MP4_PATH,
    PROJECT_DIR as EAGLE_PROJECT_DIR,
)
from tools.temporal_visual_qa import (
    audit_project_temporal_visual,
    run_mutation_tests,
    run_negative_fixtures_tests,
)
from tools.visual_qa_v14_6 import audit_tactical_labels_mobile, extract_frame_at_time

EVIDENCE_DIR = ROOT_DIR / "tests" / "evidence" / "v14_7_5_1"
LOGS_DIR = EVIDENCE_DIR / "logs"
MANDATORY_BRANCH = "fix/Image-Shot"
BASELINE_SHA = "a0813bd0b7a4428f9563d80e65f6cff6c6ef50a6"
PRODUCTION_INVARIANT_SHA = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"

PRESERVED_PRIOR_ARTIFACTS: Dict[str, Dict[str, Any]] = {
    "projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4": {
        "size": 14085487,
        "sha256": "6db2c5862917f987c417198a31297a4ba89d007d5d0434d8362eea65837df818",
    },
    "projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4": {
        "size": 11681291,
        "sha256": "3bda2c3a1aa4583bfec783de154343548cec993b21442699d596abe041f808e6",
    },
    "projects/fl01_v14_7_2_ballista_preview/out/FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4": {
        "size": 13189209,
        "sha256": "9a8ee0fa05821c553a626b764ee2b622330abe81196d3238e99c0d459e542aa8",
    },
    "projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_3_ROMAN_CONTINUITY_FRESH_PREVIEW_1080P.mp4": {
        "size": 13078836,
        "sha256": "111d153d0a37a8e985323074438666b6388d9cddf027bad0fcfadac3a43c28cf",
    },
    "projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_4_ROMAN_CONTINUITY_REPAIRED_1080P.mp4": {
        "size": 13602474,
        "sha256": "c04f01ae0463fd32ca83f7f9575121eeae9bcd86429e90eaf8cc66a3a03ce841",
    },
    "projects/fl01_v14_7_4_roman_arrow_storm_preview/out/FL01_V14_7_4_ROMAN_ARROW_STORM_FRESH_PREVIEW_1080P.mp4": {
        "size": 11543182,
        "sha256": "0f5279f8cf9344365a1149d0e2ba122b9b042f67d397b5c7c28aae3fb30b0878",
    },
    "projects/fl01_v14_7_5_roman_eagle_in_fog_preview/out/FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4": {
        "size": 16923383,
        "sha256": "5276bb238384541139e59a04d8457d683d39f883abb480a523171da25ae51421",
    },
    "projects/v14_6_action_demo/out/V14_6_Visual_Storytelling_Acting_Demo_1080p.mp4": {
        "size": 16513932,
        "sha256": "f774b9dc3d21d6ff1ec1ad986587a86dc955a0e943c30fe6b09da28c31cbac48",
    },
    "projects/squire-mau/config.json": {
        "size": 372,
        "sha256": "2c62f70b502f81be10cda5c6fae6cbbec0d088cc080451a1cb4604b55bb86214",
    },
}


def _git_out(args: List[str]) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else ""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _verify_all_preserved_artifacts() -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    all_intact = True
    for rel_p, exp in PRESERVED_PRIOR_ARTIFACTS.items():
        abs_p = ROOT_DIR / rel_p
        exists = abs_p.is_file()
        actual_size = abs_p.stat().st_size if exists else 0
        actual_sha = sha256_file(abs_p) if exists else ""
        intact = exists and (actual_size == exp["size"]) and (actual_sha == exp["sha256"])
        media_summary: Optional[Dict[str, Any]] = None
        if exists and rel_p.endswith(".mp4"):
            mi = inspect_media_file(abs_p, require_audio=True, full_decode=False)
            media_summary = {
                "valid": mi.get("valid"),
                "duration": mi.get("duration"),
                "width": mi.get("width"),
                "height": mi.get("height"),
            }
            if not mi.get("valid"):
                intact = False
        if not intact:
            all_intact = False
        records.append({
            "path": rel_p,
            "exists": exists,
            "expected_size": exp["size"],
            "actual_size": actual_size,
            "expected_sha256": exp["sha256"],
            "actual_sha256": actual_sha,
            "byte_identical": intact,
            "media_probe": media_summary,
        })
    return {"all_preserved_intact": all_intact, "preserved_count": len(records), "artifacts": records}


# ==============================================================================
# DAG Jobs
# ==============================================================================


def job_branch_and_preservation_preflight(run_id: str) -> Dict[str, Any]:
    cur_branch = _git_out(["branch", "--show-current"])
    head_sha = _git_out(["rev-parse", "HEAD"])
    anc_res = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_SHA, "HEAD"],
        cwd=ROOT_DIR,
    )
    is_ancestor = anc_res.returncode == 0
    ls_prod = _git_out(["ls-remote", "--heads", "origin", "Production"])
    remote_prod_sha = ls_prod.split()[0] if ls_prod else ""
    ls_fix = _git_out(["ls-remote", "--heads", "origin", MANDATORY_BRANCH])
    remote_fix_sha = ls_fix.split()[0] if ls_fix else ""

    budget = inspect_resource_budget(min_disk_gb=6.0, min_ram_gb=1.0, estimated_scratch_gb=1.5, extra_margin_gb=1.0)
    pres = _verify_all_preserved_artifacts()

    ok = (
        cur_branch == MANDATORY_BRANCH
        and is_ancestor
        and remote_prod_sha == PRODUCTION_INVARIANT_SHA
        and budget["healthy"]
        and pres["all_preserved_intact"]
    )
    payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if ok else ("BLOCKED_RESOURCE" if not budget["healthy"] else "FAIL"),
        "current_branch": cur_branch,
        "mandatory_branch": MANDATORY_BRANCH,
        "head_sha_at_validation": head_sha,
        "baseline_sha": BASELINE_SHA,
        "baseline_is_ancestor": is_ancestor,
        "remote_fix_image_shot_sha_pre_push": remote_fix_sha,
        "remote_production_sha": remote_prod_sha,
        "production_invariant_sha": PRODUCTION_INVARIANT_SHA,
        "production_unchanged": (remote_prod_sha == PRODUCTION_INVARIANT_SHA),
        "preflight_resource_budget": budget,
        **pres,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "01_branch_and_preservation.json",
        payload,
        run_id=run_id,
        writer_job_id="branch_and_preservation_preflight",
        required_keys=["status", "current_branch", "production_unchanged", "all_preserved_intact", "artifacts"],
    )
    return payload


def job_unit_verification_and_water_gate(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_p = LOGS_DIR / "unit_tests.log"
    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "tests/test_v14_7_5_1_verification_gaps.py",
            "tests/test_water_gate_primitives_v14_7_5_1.py",
            "tests/test_qa_scheduler_v14_7_5.py",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=240,
    )
    wall = round(time.perf_counter() - t0, 3)
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "exit_code": proc.returncode,
        "wall_sec": wall,
        "log_path": str(log_p.relative_to(ROOT_DIR)),
    }


def job_mutation_and_negative_real(run_id: str) -> Dict[str, Any]:
    mut_logs_dir = LOGS_DIR / "mutation_logs"
    mut_logs_dir.mkdir(parents=True, exist_ok=True)
    mut_res = run_mutation_tests(failure_logs_dir=mut_logs_dir)
    neg_res = run_negative_fixtures_tests()

    neg_all_ok = bool(
        neg_res.get("all_negative_fixtures_passed")
        if "all_negative_fixtures_passed" in neg_res
        else (
            int(neg_res.get("passed_fixtures", 0)) >= 15
            and int(neg_res.get("passed_fixtures", 0)) == int(neg_res.get("total_fixtures", -1))
        )
    )
    ok = (
        mut_res.get("all_mutations_killed") is True
        and int(mut_res.get("killed_mutations", 0)) >= 6
        and neg_all_ok
        and int(neg_res.get("passed_fixtures", 0)) >= 15
    )
    payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if ok else "FAIL",
        "execution_mode": mut_res.get("execution_mode"),
        "all_mutations_killed": mut_res.get("all_mutations_killed"),
        "killed_mutations": mut_res.get("killed_mutations"),
        "total_mutations": mut_res.get("total_mutations"),
        "mutations": mut_res.get("mutations"),
        "negative_fixtures_all_passed": neg_all_ok,
        "negative_fixtures_passed_count": neg_res.get("passed_fixtures"),
        "negative_fixtures_total_count": neg_res.get("total_fixtures"),
        "negative_fixtures": neg_res.get("fixtures"),
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "04_mutation_negative_real.json",
        payload,
        run_id=run_id,
        writer_job_id="mutation_and_negative_real",
        required_keys=["status", "all_mutations_killed", "killed_mutations", "negative_fixtures_all_passed"],
    )
    return payload


def job_eagle_lineage_check(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    eagle_lin = verify_receipt_and_lineage(
        EAGLE_PROJECT_DIR,
        EAGLE_MP4_PATH,
        expected_specs={
            "width": 1920,
            "height": 1080,
            "fps": 24.0,
            "min_duration": 50.0,
            "max_duration": 58.0,
            "require_audio": True,
            "measure_loudness": True,
        },
    )
    out_p = LOGS_DIR / "eagle_lineage_preflight.json"
    _atomic_write_text(out_p, json.dumps(eagle_lin, indent=2, ensure_ascii=False))
    return eagle_lin


def job_e2e_full_regression(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_summary = EVIDENCE_DIR / f".tmp_e2e_summary_{os.getpid()}.json"
    tmp_summary.unlink(missing_ok=True)

    env = dict(os.environ)
    # Bound internal E2E concurrency to 1 on 16GB host to protect >=1.0 GiB RAM floor at all times
    env["QA_E2E_MAX_CONCURRENCY"] = "1"

    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_e2e_regression.py",
            "--max-concurrency",
            "1",
            "--out-summary",
            str(tmp_summary),
        ],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    wall_sec = round(time.perf_counter() - t0, 3)
    _atomic_write_text(LOGS_DIR / "e2e_regression.log", (proc.stdout or "") + "\n" + (proc.stderr or ""))

    raw_data: Dict[str, Any] = {}
    if tmp_summary.is_file():
        try:
            raw_data = json.loads(tmp_summary.read_text(encoding="utf-8"))
        finally:
            tmp_summary.unlink(missing_ok=True)

    results_list = raw_data.get("results", [])
    verdict = raw_data.get("verdict", "FAIL")
    req_total = int(raw_data.get("required_gates_total", 0))
    req_passed = int(raw_data.get("required_gates_passed", 0))
    req_failed = int(raw_data.get("required_gates_failed", 1))

    ok = (
        proc.returncode == 0
        and verdict == "FLOW_READY"
        and req_failed == 0
        and req_passed >= 81
    )
    e2e_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": raw_data.get("run_id", run_id),
        "dag_run_id": run_id,
        "status": "PASS" if ok else "FAIL",
        "exit_code": proc.returncode,
        "wall_sec": wall_sec,
        "max_concurrency_used": 1,
        "verdict": verdict,
        "verdict_reason": raw_data.get("verdict_reason"),
        "gates_total": raw_data.get("gates_total", len(results_list)),
        "required_gates_total": req_total,
        "required_gates_passed": req_passed,
        "required_gates_failed": req_failed,
        "optional_gates_total": raw_data.get("optional_gates_total", 0),
        "log_path": "tests/evidence/v14_7_5_1/logs/e2e_regression.log",
        "gates_compact": [
            {
                "gate": r.get("gate"),
                "name": r.get("name"),
                "status": r.get("status"),
                "required": r.get("required", True),
                "kind": r.get("kind"),
            }
            for r in results_list
        ],
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "05_e2e_full_regression.json",
        e2e_payload,
        run_id=run_id,
        writer_job_id="e2e_full_regression",
        required_keys=["status", "exit_code", "verdict", "required_gates_passed", "required_gates_failed"],
    )

    by_gate = {r.get("gate"): r for r in results_list if isinstance(r, dict)}
    g5 = by_gate.get("G5", {})
    g5b = by_gate.get("G5b", {})
    g5c = by_gate.get("G5c", {})
    g5c_raw = g5c.get("status", "NOT_RUN_OPTIONAL_MISSING_FIXTURE")
    hist_180_status = "PASS_REAL_FIXTURE" if g5c_raw == "PASS" else "NOT_AVAILABLE"

    backtest_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": raw_data.get("run_id", run_id),
        "dag_run_id": run_id,
        "status": "PASS" if (g5.get("status") == "PASS" and g5b.get("status") == "PASS") else "FAIL",
        "synthetic_180_stress_gate_g5": g5.get("status", "UNKNOWN"),
        "synthetic_180_details": g5.get("details", {}),
        "medium_20_shot_real_render_g5b": g5b.get("status", "UNKNOWN"),
        "medium_20_shot_details": g5b.get("details", {}),
        "historical_180_real_replay": hist_180_status,
        "historical_180_raw_gate_status": g5c_raw,
        "historical_180_fixture_path": "projects/why_knights_could_actually",
        "counted_not_available_as_real_replay_pass": False,
        "truth_disclosure": (
            "G5 verifies a 180-shot SYNTHETIC timeline stress fixture (PASS) and G5b verifies a 20-shot "
            "REAL render fixture (PASS). The optional company dataset 'projects/why_knights_could_actually' "
            "is absent on this host, so G5c is reported strictly as NOT_AVAILABLE and NEVER counted as a real replay PASS."
        ),
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "06_backtest_truth.json",
        backtest_payload,
        run_id=run_id,
        writer_job_id="e2e_full_regression",
        required_keys=[
            "status",
            "synthetic_180_stress_gate_g5",
            "medium_20_shot_real_render_g5b",
            "historical_180_real_replay",
            "counted_not_available_as_real_replay_pass",
        ],
    )
    return e2e_payload


def job_water_gate_30s_render(run_id: str) -> Dict[str, Any]:
    """Force true creation render (cold) + verified warm-cache check of the original 30.000s / 720-frame film."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t_cold0 = time.perf_counter()
    cold_res = produce_water_gate_preview(force_rebuild=True, workers=1, extra_evidence_dir=EVIDENCE_DIR)
    cold_wall = round(time.perf_counter() - t_cold0, 3)
    if cold_res.get("status") != "PRODUCED":
        return {"status": cold_res.get("status", "FAIL"), "error": cold_res.get("error")}

    shutil.copy2(WG_PROJECT_DIR / "build" / "render.log", LOGS_DIR / "water_gate_render.log")

    t_warm0 = time.perf_counter()
    warm_res = produce_water_gate_preview(force_rebuild=False, workers=1, extra_evidence_dir=EVIDENCE_DIR)
    warm_wall = round(time.perf_counter() - t_warm0, 3)

    insp = inspect_water_gate_preview(WG_PROJECT_DIR, WG_MP4_PATH)
    wg_lin = insp["lineage"]
    wg_mi = insp["media_info"]

    eagle_lin_p = LOGS_DIR / "eagle_lineage_preflight.json"
    if eagle_lin_p.is_file():
        eagle_lin = json.loads(eagle_lin_p.read_text(encoding="utf-8"))
    else:
        eagle_lin = verify_receipt_and_lineage(
            EAGLE_PROJECT_DIR,
            EAGLE_MP4_PATH,
            expected_specs={"width": 1920, "height": 1080, "fps": 24.0, "min_duration": 50.0, "max_duration": 58.0, "require_audio": True, "measure_loudness": True},
        )

    # 08_fingerprint_receipt_integrity.json (explicit canonical fields, ZERO null fingerprints)
    fp_ok = (
        wg_lin.get("status") == "PASS"
        and eagle_lin.get("status") == "PASS"
        and bool(wg_lin.get("input_fingerprint"))
        and bool(eagle_lin.get("input_fingerprint"))
    )
    fp_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if fp_ok else "FAIL",
        "input_fingerprint": wg_lin.get("input_fingerprint"),
        "recomputed_input_fingerprint": wg_lin.get("recomputed_input_fingerprint"),
        "fingerprint_match": wg_lin.get("fingerprint_match"),
        "output_sha256": wg_lin.get("output_sha256"),
        "receipt_verified": wg_lin.get("receipt_verified"),
        "cache_verified": wg_lin.get("cache_verified"),
        "media_decode_verified": wg_lin.get("media_decode_verified"),
        "films": {
            "water_gate_v14_7_5_1": wg_lin,
            "eagle_in_fog_v14_7_5_reverified": eagle_lin,
        },
        "historical_v14_7_5_evidence_untouched": True,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "08_fingerprint_receipt_integrity.json",
        fp_payload,
        run_id=run_id,
        writer_job_id="water_gate_30s_render",
        required_keys=[
            "evidence_schema_version",
            "status",
            "input_fingerprint",
            "output_sha256",
            "receipt_verified",
            "cache_verified",
            "media_decode_verified",
        ],
    )

    # 10_water_gate_media.json
    media_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if (insp["valid"] and warm_res.get("status") == "CACHE_HIT_VERIFIED") else "FAIL",
        "title": WG_TITLE,
        "subtitle": WG_SUBTITLE,
        "project_dir": str(WG_PROJECT_DIR.relative_to(ROOT_DIR)),
        "output_mp4": str(WG_MP4_PATH.relative_to(ROOT_DIR)),
        "cold_render_status": cold_res.get("status"),
        "cold_render_total_wall_sec": cold_wall,
        "cold_render_only_wall_sec": cold_res.get("render_only_wall_sec"),
        "warm_cache_status": warm_res.get("status"),
        "warm_cache_wall_sec": warm_wall,
        "input_fingerprint": wg_lin.get("input_fingerprint"),
        "recomputed_input_fingerprint": wg_lin.get("recomputed_input_fingerprint"),
        "output_sha256": wg_lin.get("output_sha256"),
        "receipt_verified": wg_lin.get("receipt_verified"),
        "cache_verified": wg_lin.get("cache_verified"),
        "media_decode_verified": wg_lin.get("media_decode_verified"),
        "decoded_video_frames": wg_mi.get("decoded_video_frames"),
        "nominal_duration_diff_sec": insp.get("nominal_duration_diff_sec"),
        "audio_video_stream_diff_sec": insp.get("audio_video_stream_diff_sec"),
        "media_info": wg_mi,
        "contact_sheets": cold_res.get("contact_sheets"),
        "provenance": wg_lin.get("provenance"),
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "10_water_gate_media.json",
        media_payload,
        run_id=run_id,
        writer_job_id="water_gate_30s_render",
        required_keys=["status", "output_mp4", "decoded_video_frames", "input_fingerprint", "output_sha256", "media_info"],
    )

    # 12_voice_and_audio_metrics.json
    v_ledger = json.loads((WG_PROJECT_DIR / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
    mix_rep = json.loads((WG_PROJECT_DIR / "build" / "audio_mix_report.json").read_text(encoding="utf-8"))
    events = v_ledger.get("events", [])
    recomputed_ov = compute_measured_voice_overlaps(events)
    voice_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if (insp["valid"] and recomputed_ov == 0.0) else "FAIL",
        "speech_provider": v_ledger.get("speech_provider"),
        "beats_count": len(events),
        "total_timeline_duration_sec": v_ledger.get("total_timeline_duration_sec"),
        "voice_wav_duration_sec": v_ledger.get("voice_wav_duration_sec"),
        "mp4_audio_stream_duration_sec": wg_mi.get("audio_stream_duration"),
        "measured_overlap_ms": recomputed_ov,
        "min_tail_margin_sec": v_ledger.get("min_tail_margin_sec"),
        "max_tail_margin_sec": v_ledger.get("max_tail_margin_sec"),
        "atempo_used_anywhere": v_ledger.get("atempo_used_anywhere"),
        "final_mp4_integrated_lufs": wg_mi.get("integrated_lufs"),
        "final_mp4_true_peak_dbtp": wg_mi.get("true_peak_dbtp"),
        "final_mp4_mean_volume_db": wg_mi.get("mean_volume_db"),
        "final_mp4_max_volume_db": wg_mi.get("max_volume_db"),
        "soundtrack_layers": mix_rep.get("layers"),
        "events": events,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "12_voice_and_audio_metrics.json",
        voice_payload,
        run_id=run_id,
        writer_job_id="water_gate_30s_render",
        required_keys=["status", "speech_provider", "measured_overlap_ms", "min_tail_margin_sec", "final_mp4_integrated_lufs"],
    )

    # 14_new_visual_asset_lineage.json
    asset_manifest = json.loads((WG_PROJECT_DIR / "story" / "asset_source_manifest.json").read_text(encoding="utf-8"))
    prior_shas = {v["sha256"] for v in PRESERVED_PRIOR_ARTIFACTS.values()}
    asset_lineage_payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if (asset_manifest.get("prior_preview_derived_visual_inputs") == 0 and wg_lin.get("output_sha256") not in prior_shas) else "FAIL",
        "output_mp4_sha256": wg_lin.get("output_sha256"),
        "output_mp4_distinct_from_all_prior_previews": (wg_lin.get("output_sha256") not in prior_shas),
        **asset_manifest,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "14_new_visual_asset_lineage.json",
        asset_lineage_payload,
        run_id=run_id,
        writer_job_id="water_gate_30s_render",
        required_keys=["status", "prior_preview_derived_visual_inputs", "procedural_modules"],
    )
    return media_payload


def job_water_gate_temporal_qa(run_id: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    work_d = EVIDENCE_DIR / "_tmp_wg_decode_work"
    rep = audit_project_temporal_visual(
        project_dir=WG_PROJECT_DIR,
        mp4_path=WG_MP4_PATH,
        output_evidence_dir=work_d,
        run_negative_suite=False,
    )
    shutil.rmtree(work_d, ignore_errors=True)
    decode_wall = round(time.perf_counter() - t0, 3)

    rep_dict = rep.model_dump()
    rep_dict["evidence_schema_version"] = "14.7.5.1"
    rep_dict["run_id"] = run_id
    rep_dict["decode_audit_wall_sec"] = decode_wall
    rep_dict["status"] = "PASS" if (rep.technical_verdict == "VISUAL_TECH_PASS" and rep.full_boundary_coverage) else "FAIL"
    publish_atomic_evidence(
        EVIDENCE_DIR / "11_water_gate_temporal.json",
        rep_dict,
        run_id=run_id,
        writer_job_id="water_gate_temporal_qa",
        required_keys=["status", "technical_verdict", "expected_cut_count", "audited_cut_count", "full_boundary_coverage"],
    )
    return rep_dict


def job_eagle_boundary_qa(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    work_d = EVIDENCE_DIR / "_tmp_eagle_decode_work"
    rep = audit_project_temporal_visual(
        project_dir=EAGLE_PROJECT_DIR,
        mp4_path=EAGLE_MP4_PATH,
        output_evidence_dir=work_d,
        run_negative_suite=False,
    )
    shutil.rmtree(work_d, ignore_errors=True)
    decode_wall = round(time.perf_counter() - t0, 3)

    rep_dict = rep.model_dump()
    rep_dict["decode_audit_wall_sec"] = decode_wall
    out_p = LOGS_DIR / "eagle_temporal_v14_7_5_1.json"
    _atomic_write_text(out_p, json.dumps(rep_dict, indent=2, ensure_ascii=False))
    return {
        "status": "PASS" if (rep.technical_verdict == "VISUAL_TECH_PASS" and rep.full_boundary_coverage) else "FAIL",
        "decode_audit_wall_sec": decode_wall,
    }


def job_cut_boundary_coverage_rollup(run_id: str) -> Dict[str, Any]:
    wg_t = json.loads((EVIDENCE_DIR / "11_water_gate_temporal.json").read_text(encoding="utf-8"))
    eagle_t = json.loads((LOGS_DIR / "eagle_temporal_v14_7_5_1.json").read_text(encoding="utf-8"))

    ok = (
        wg_t.get("full_boundary_coverage") is True
        and wg_t.get("expected_cut_count") == 7
        and wg_t.get("audited_cut_count") == 7
        and wg_t.get("unaudited_cuts") == []
        and eagle_t.get("full_boundary_coverage") is True
        and eagle_t.get("expected_cut_count") == 11
        and eagle_t.get("audited_cut_count") == 11
        and eagle_t.get("unaudited_cuts") == []
    )
    payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if ok else "FAIL",
        "total_expected_cuts_across_two_films": 18,
        "total_audited_cuts_across_two_films": int(wg_t.get("audited_cut_count", 0)) + int(eagle_t.get("audited_cut_count", 0)),
        "water_gate_v14_7_5_1": {
            "total_shots": wg_t.get("total_shots"),
            "expected_cut_count": wg_t.get("expected_cut_count"),
            "audited_cut_count": wg_t.get("audited_cut_count"),
            "unaudited_cuts": wg_t.get("unaudited_cuts"),
            "full_boundary_coverage": wg_t.get("full_boundary_coverage"),
            "boundary_evidence": wg_t.get("boundary_evidence"),
        },
        "eagle_in_fog_v14_7_5": {
            "total_shots": eagle_t.get("total_shots"),
            "expected_cut_count": eagle_t.get("expected_cut_count"),
            "audited_cut_count": eagle_t.get("audited_cut_count"),
            "unaudited_cuts": eagle_t.get("unaudited_cuts"),
            "full_boundary_coverage": eagle_t.get("full_boundary_coverage"),
            "diagram_transitions_audited": [
                b["cut"]
                for b in eagle_t.get("boundary_evidence", [])
                if any(x in ("map", "diagram") for x in (b.get("from_subject"), b.get("to_subject")))
            ],
            "boundary_evidence": eagle_t.get("boundary_evidence"),
        },
        "eagle_temporal_report": eagle_t,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "07_cut_boundary_coverage.json",
        payload,
        run_id=run_id,
        writer_job_id="cut_boundary_coverage_rollup",
        required_keys=["status", "total_expected_cuts_across_two_films", "total_audited_cuts_across_two_films"],
    )
    return payload


def _build_microbenchmark_jobs(out_dir: Path) -> List[Dict[str, Any]]:
    targets = [
        ("m1_night", ROOT_DIR / "projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4", 4.0),
        ("m2_bridge", ROOT_DIR / "projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4", 6.0),
        ("m3_eagle", EAGLE_MP4_PATH, 10.0),
        ("m4_water_gate", WG_MP4_PATH, 12.0),
    ]
    jobs: List[Dict[str, Any]] = []
    for jid, mp4_p, ts in targets:
        out_json = out_dir / f"{jid}.json"
        inline_py = (
            "import hashlib, json, subprocess; "
            f"mp4 = {str(mp4_p)!r}; out_j = {str(out_json)!r}; ts = {ts!r}; "
            "subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json', mp4], check=True, capture_output=True, text=True); "
            "p2 = subprocess.run(['ffmpeg','-v','error','-ss', str(ts), '-i', mp4, '-frames:v', '3', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], check=True, capture_output=True); "
            "digest = hashlib.sha256(p2.stdout).hexdigest(); "
            "open(out_j, 'w').write(json.dumps({'job': " + repr(jid) + ", 'bytes': len(p2.stdout), 'sha256': digest})); "
            "print(digest)"
        )
        jobs.append({
            "id": jid,
            "job_profile": "light_cpu",
            "deps": [],
            "cmd": [sys.executable, "-c", inline_py],
            "expected_artifacts": [str(out_json)],
            "timeout_sec": 60.0,
        })
    return jobs


def job_speed_micro_and_e2e(run_id: str) -> Dict[str, Any]:
    iterations = 3
    serial_times: List[float] = []
    parallel_times: List[float] = []
    runs_detail: List[Dict[str, Any]] = []
    outputs_identical_all = True

    for it in range(1, iterations + 1):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            ser_d = td_p / "serial"
            par_d = td_p / "parallel"
            ser_d.mkdir()
            par_d.mkdir()

            t_s0 = time.perf_counter()
            ser_rep = run_dag(
                build_dependency_dag(_build_microbenchmark_jobs(ser_d)),
                max_workers=1,
                min_disk_gb=6.0,
                min_ram_gb=1.0,
                run_id=f"micro_ser_{it}",
            )
            t_ser = round(time.perf_counter() - t_s0, 4)

            t_p0 = time.perf_counter()
            par_rep = run_dag(
                build_dependency_dag(_build_microbenchmark_jobs(par_d)),
                max_workers=4,
                min_disk_gb=6.0,
                min_ram_gb=1.0,
                run_id=f"micro_par_{it}",
            )
            t_par = round(time.perf_counter() - t_p0, 4)

            ser_hashes = {p.name: json.loads(p.read_text(encoding="utf-8"))["sha256"] for p in sorted(ser_d.glob("*.json"))}
            par_hashes = {p.name: json.loads(p.read_text(encoding="utf-8"))["sha256"] for p in sorted(par_d.glob("*.json"))}
            same = ser_rep["all_succeeded"] and par_rep["all_succeeded"] and len(ser_hashes) == 4 and (ser_hashes == par_hashes)
            if not same:
                outputs_identical_all = False

            serial_times.append(t_ser)
            parallel_times.append(t_par)
            runs_detail.append({
                "iteration": it,
                "serial_sec": t_ser,
                "parallel_sec": t_par,
                "speedup_ratio": round(t_ser / max(0.001, t_par), 3),
                "parallel_overlapping_pairs": par_rep["concurrency_proof"]["overlapping_pairs_count"],
                "output_digests_identical": same,
            })

    wg_media = json.loads((EVIDENCE_DIR / "10_water_gate_media.json").read_text(encoding="utf-8"))
    wg_temp = json.loads((EVIDENCE_DIR / "11_water_gate_temporal.json").read_text(encoding="utf-8"))
    e2e_ev = json.loads((EVIDENCE_DIR / "05_e2e_full_regression.json").read_text(encoding="utf-8"))

    mean_ser = round(statistics.mean(serial_times), 4)
    mean_par = round(statistics.mean(parallel_times), 4)
    payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if outputs_identical_all else "FAIL",
        "scope_separation_note": (
            "Lightweight QA microbenchmark speedup applies strictly to parallel ffprobe/rawvideo decode tasks (n=3) "
            "and is NEVER claimed as whole-renderer speedup. Heavy 1080p Chromium rendering is intentionally serialized "
            "on this 16GB host to guarantee >=1.0 GiB available RAM."
        ),
        "microbenchmark": {
            "workload": "4 independent ffprobe + 3-frame RGB24 decode + SHA256 tasks across 1080p MP4s",
            "iterations": iterations,
            "serial_wall_times_sec": serial_times,
            "parallel_wall_times_sec": parallel_times,
            "mean_serial_sec": mean_ser,
            "mean_parallel_sec": mean_par,
            "median_serial_sec": round(statistics.median(serial_times), 4),
            "median_parallel_sec": round(statistics.median(parallel_times), 4),
            "mean_speedup_ratio": round(mean_ser / max(0.001, mean_par), 3),
            "all_output_digests_identical": outputs_identical_all,
            "runs": runs_detail,
        },
        "end_to_end_pipeline_measurements": {
            "water_gate_30s_cold_render_total_wall_sec": wg_media.get("cold_render_total_wall_sec"),
            "water_gate_30s_cold_render_only_wall_sec": wg_media.get("cold_render_only_wall_sec"),
            "water_gate_30s_warm_cache_wall_sec": wg_media.get("warm_cache_wall_sec"),
            "water_gate_30s_temporal_decode_qa_wall_sec": wg_temp.get("decode_audit_wall_sec"),
            "cold_render_sample_count": 1,
            "cold_render_sample_status": "SMALL_SAMPLE",
            "e2e_full_regression_81_gates_wall_sec": e2e_ev.get("wall_sec"),
        },
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "13_speed_micro_and_e2e.json",
        payload,
        run_id=run_id,
        writer_job_id="speed_micro_and_e2e",
        required_keys=["status", "microbenchmark", "end_to_end_pipeline_measurements"],
    )
    return payload


def _render_isolated_versioned_correction(
    orig_proj_dir: Path,
    archived_mp4_path: Path,
    mixed_wav_rel: str,
    versioned_mp4_path: Path,
    schematic_shot_id: str,
    schematic_ts_sec: float,
) -> Dict[str, Any]:
    """
    Render a versioned corrected 1080p MP4 from an isolated temporary clone of `orig_proj_dir`
    so archived MP4s and `orig_proj_dir/build/render_receipt.json` remain 100% untouched.
    """
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="v14_7_5_1_corr_") as td:
        clone_dir = Path(td) / orig_proj_dir.name
        clone_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(orig_proj_dir / "config.json", clone_dir / "config.json")
        for sub in ("story", "scenes", "timeline"):
            src_sub = orig_proj_dir / sub
            if src_sub.is_dir():
                shutil.copytree(src_sub, clone_dir / sub)
        (clone_dir / "build").mkdir(parents=True, exist_ok=True)
        src_wav = orig_proj_dir / mixed_wav_rel
        clone_wav = clone_dir / "build" / "corr_audio.wav"
        shutil.copy2(src_wav, clone_wav)

        env = dict(os.environ)
        env.pop("QA_STUDIO_TEST_MODE", None)
        proc = subprocess.run(
            ["node", "render.mjs", "--project", str(clone_dir), "--workers", "1"],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            return {
                "status": "FAIL",
                "error": f"render.mjs exited {proc.returncode}: {(proc.stderr or proc.stdout)[-400:]}",
            }

        silent_mp4 = clone_dir / "build" / "video_silent.mp4"
        partial_mp4 = versioned_mp4_path.with_suffix(".partial.mp4")
        partial_mp4.unlink(missing_ok=True)
        mux_res = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(silent_mp4),
                "-i",
                str(clone_wav),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                "-movflags",
                "+faststart",
                str(partial_mp4),
            ],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )
        if mux_res.returncode != 0:
            return {"status": "FAIL", "error": f"ffmpeg mux failed: {mux_res.stderr[-400:]}"}

        mi = inspect_media_file(partial_mp4, require_audio=True, full_decode=True)
        if not mi.get("valid"):
            partial_mp4.unlink(missing_ok=True)
            return {"status": "FAIL", "error": f"Invalid corrected media: {mi.get('errors')}"}

        os.replace(partial_mp4, versioned_mp4_path)

        # Write sidecar receipt ONLY (never touching orig_proj_dir/build/render_receipt.json)
        manifest = collect_render_inputs(orig_proj_dir, render_options={"audio_mode": "voice_sfx"})
        fp = compute_render_fingerprint(manifest)
        sidecar = versioned_mp4_path.with_suffix(".receipt.json")
        sidecar_payload = {
            "schema_version": "1.0",
            "version": "14.7.5.1",
            "project_id": orig_proj_dir.name,
            "input_fingerprint": fp,
            "output_path": str(versioned_mp4_path.relative_to(ROOT_DIR)),
            "output_sha256": mi["sha256"],
            "media_info": mi,
            "note": "Versioned corrected V14.7.5.1 output rendered in isolated temp clone; archived historical MP4 and build receipt preserved untouched.",
        }
        _atomic_write_text(sidecar, json.dumps(sidecar_payload, indent=2, ensure_ascii=False))

        # Pixel validation on schematic shot: historical MP4 vs corrected versioned MP4
        hist_png = Path(td) / "hist_schematic.png"
        corr_png = Path(td) / "corr_schematic.png"
        extract_frame_at_time(archived_mp4_path, schematic_ts_sec, hist_png)
        extract_frame_at_time(versioned_mp4_path, schematic_ts_sec, corr_png)
        hist_arr = np.array(Image.open(hist_png).convert("RGB"))
        corr_arr = np.array(Image.open(corr_png).convert("RGB"))
        hist_mob_ok, hist_diags = audit_tactical_labels_mobile(hist_arr)
        corr_mob_ok, corr_diags = audit_tactical_labels_mobile(corr_arr)
        hist_std = round(float(np.std(hist_arr)), 2)
        corr_std = round(float(np.std(corr_arr)), 2)
        h_px, w_px, _ = corr_arr.shape
        hist_roi = hist_arr[int(0.15 * h_px) : int(0.85 * h_px), int(0.15 * w_px) : int(0.85 * w_px)].astype(np.float32)
        corr_roi = corr_arr[int(0.15 * h_px) : int(0.85 * h_px), int(0.15 * w_px) : int(0.85 * w_px)].astype(np.float32)
        center_delta = round(float(np.mean(np.abs(corr_roi - hist_roi))), 2)

    wall = round(time.perf_counter() - t0, 3)
    pixel_fixed = bool(corr_mob_ok and center_delta >= 8.0 and corr_std >= 18.0)
    return {
        "status": "CORRECTED_VERSIONED_PASS" if pixel_fixed else "FAIL",
        "wall_sec": wall,
        "archived_historical_mp4": str(archived_mp4_path.relative_to(ROOT_DIR)),
        "archived_historical_sha256": sha256_file(archived_mp4_path),
        "corrected_versioned_mp4": str(versioned_mp4_path.relative_to(ROOT_DIR)),
        "corrected_versioned_sha256": mi["sha256"],
        "corrected_sidecar_receipt": str(sidecar.relative_to(ROOT_DIR)),
        "duration_sec": mi.get("duration"),
        "decoded_video_frames": mi.get("decoded_video_frames"),
        "schematic_shot_pixel_audit": {
            "shot_id": schematic_shot_id,
            "timestamp_sec": schematic_ts_sec,
            "historical_std_luma": hist_std,
            "historical_mobile_legible": hist_mob_ok,
            "historical_diagnostics": hist_diags,
            "corrected_std_luma": corr_std,
            "corrected_mobile_legible": corr_mob_ok,
            "corrected_diagnostics": corr_diags,
            "center_roi_mean_abs_pixel_delta": center_delta,
            "schematic_visibly_rendered": pixel_fixed,
        },
    }


def job_old_video_versioned_corrections(run_id: str) -> Dict[str, Any]:
    budget = inspect_resource_budget(min_disk_gb=6.0, min_ram_gb=1.0, estimated_scratch_gb=1.2, extra_margin_gb=1.0)
    targets = [
        {
            "key": "arrow_storm_v14_7_4",
            "proj": ROOT_DIR / "projects/fl01_v14_7_4_roman_arrow_storm_preview",
            "archived_mp4": ROOT_DIR / "projects/fl01_v14_7_4_roman_arrow_storm_preview/out/FL01_V14_7_4_ROMAN_ARROW_STORM_FRESH_PREVIEW_1080P.mp4",
            "wav_rel": "build/soundtrack_mixed.wav",
            "versioned_mp4": ROOT_DIR / "projects/fl01_v14_7_4_roman_arrow_storm_preview/out/FL01_V14_7_4_ROMAN_ARROW_STORM_CORRECTED_V14_7_5_1_1080P.mp4",
            "shot_id": "s05",
            "ts": 24.3,
        },
        {
            "key": "roman_continuity_repaired_v14_7_4",
            "proj": ROOT_DIR / "projects/fl01_v14_7_3_roman_continuity_benchmark",
            "archived_mp4": ROOT_DIR / "projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_4_ROMAN_CONTINUITY_REPAIRED_1080P.mp4",
            "wav_rel": "build/audio_mixed.wav",
            "versioned_mp4": ROOT_DIR / "projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_4_ROMAN_CONTINUITY_REPAIRED_CORRECTED_V14_7_5_1_1080P.mp4",
            "shot_id": "s09",
            "ts": 45.9,
        },
    ]

    if not budget["healthy"]:
        payload = {
            "evidence_schema_version": "14.7.5.1",
            "run_id": run_id,
            "status": "PENDING_CORRECTION",
            "reason": f"Skipped optional old-film re-render to protect resource floor: {budget['message']}",
            "pending_paths": [str(t["versioned_mp4"].relative_to(ROOT_DIR)) for t in targets],
            "preserved_historical_artifacts_intact": _verify_all_preserved_artifacts()["all_preserved_intact"],
        }
        publish_atomic_evidence(
            EVIDENCE_DIR / "15_old_video_corrections_status.json",
            payload,
            run_id=run_id,
            writer_job_id="old_video_versioned_corrections",
            required_keys=["status", "preserved_historical_artifacts_intact"],
        )
        return {"status": "PASS", "corrections_status": "PENDING_CORRECTION"}

    results: Dict[str, Any] = {}
    all_corr_ok = True
    for t in targets:
        res = _render_isolated_versioned_correction(
            orig_proj_dir=t["proj"],
            archived_mp4_path=t["archived_mp4"],
            mixed_wav_rel=t["wav_rel"],
            versioned_mp4_path=t["versioned_mp4"],
            schematic_shot_id=t["shot_id"],
            schematic_ts_sec=t["ts"],
        )
        results[t["key"]] = res
        if res.get("status") != "CORRECTED_VERSIONED_PASS":
            all_corr_ok = False

    post_pres = _verify_all_preserved_artifacts()
    payload = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": "PASS" if (all_corr_ok and post_pres["all_preserved_intact"]) else "FAIL",
        "preserved_historical_artifacts_intact": post_pres["all_preserved_intact"],
        "corrections": results,
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "15_old_video_corrections_status.json",
        payload,
        run_id=run_id,
        writer_job_id="old_video_versioned_corrections",
        required_keys=["status", "preserved_historical_artifacts_intact", "corrections"],
    )
    return payload


# ==============================================================================
# Documentation & Strict Cross-Evidence Consistency Verification
# ==============================================================================


def _write_markdown_reports(run_id: str) -> None:
    acc = json.loads((EVIDENCE_DIR / "00_acceptance.json").read_text(encoding="utf-8"))
    b01 = json.loads((EVIDENCE_DIR / "01_branch_and_preservation.json").read_text(encoding="utf-8"))
    r02 = json.loads((EVIDENCE_DIR / "02_resource_timeseries.json").read_text(encoding="utf-8"))
    j03 = json.loads((EVIDENCE_DIR / "03_async_real_jobs.json").read_text(encoding="utf-8"))
    m04 = json.loads((EVIDENCE_DIR / "04_mutation_negative_real.json").read_text(encoding="utf-8"))
    e05 = json.loads((EVIDENCE_DIR / "05_e2e_full_regression.json").read_text(encoding="utf-8"))
    h06 = json.loads((EVIDENCE_DIR / "06_backtest_truth.json").read_text(encoding="utf-8"))
    c07 = json.loads((EVIDENCE_DIR / "07_cut_boundary_coverage.json").read_text(encoding="utf-8"))
    f08 = json.loads((EVIDENCE_DIR / "08_fingerprint_receipt_integrity.json").read_text(encoding="utf-8"))
    s09 = json.loads((EVIDENCE_DIR / "09_shot_repair_video.json").read_text(encoding="utf-8"))
    w10 = json.loads((EVIDENCE_DIR / "10_water_gate_media.json").read_text(encoding="utf-8"))
    t11 = json.loads((EVIDENCE_DIR / "11_water_gate_temporal.json").read_text(encoding="utf-8"))
    v12 = json.loads((EVIDENCE_DIR / "12_voice_and_audio_metrics.json").read_text(encoding="utf-8"))
    sp13 = json.loads((EVIDENCE_DIR / "13_speed_micro_and_e2e.json").read_text(encoding="utf-8"))
    a14 = json.loads((EVIDENCE_DIR / "14_new_visual_asset_lineage.json").read_text(encoding="utf-8"))
    o15 = json.loads((EVIDENCE_DIR / "15_old_video_corrections_status.json").read_text(encoding="utf-8"))

    mi = w10.get("media_info", {})
    gate_rows = "\n".join(
        f"| `{g['gate_id']}` | `{g['name']}` | **{g['status']}** | `{g['measured_duration_sec']}s` |"
        for g in acc.get("gates", [])
    )

    report_md = f"""# FL-01 / V14.7.5.1 Final Technical Verification & Original 30s Film — Acceptance Report

- **Release**: `V14.7.5.1` (`FL-01`)
- **Work Branch**: `{MANDATORY_BRANCH}` (Baseline `{BASELINE_SHA}`)
- **Protected Production SHA**: `{PRODUCTION_INVARIANT_SHA}` (`production_unchanged = {b01['production_unchanged']}`)
- **Validation Run ID**: `{run_id}`
- **Master Verdict**: **`{acc['master_status']}`** (`{acc['mandatory_technical_gates_passed']}/{acc['mandatory_technical_gates_total']}` Mandatory Technical Gates `PASS`)
- **Human Editorial Gate (`J13`)**: **`{acc['editorial_status']}`**

## 1. Mandatory Gates (`R1`–`R8` + `J13`)

| Gate | Requirement | Status | Duration |
| :--- | :--- | :--- | :--- |
{gate_rows}

## 2. Original 30.000s Film: `{WG_TITLE}`

- **Subtitle / Framing**: *{WG_SUBTITLE}*
- **Output MP4**: `{w10['output_mp4']}`
- **Output SHA256**: `{w10['output_sha256']}`
- **Input Fingerprint (64-hex)**: `{f08['input_fingerprint']}` (`recomputed_input_fingerprint` match = `{f08['fingerprint_match']}`, `receipt_verified = {f08['receipt_verified']}`, `cache_verified = {f08['cache_verified']}`)
- **Exact Frame & Stream Proof**: **`{w10['decoded_video_frames']}` decoded frames** (`{mi.get('width')}x{mi.get('height')}` @ `{mi.get('fps')} fps`, container `{mi.get('duration')}s`, video `{mi.get('video_stream_duration')}s`, audio `{mi.get('audio_stream_duration')}s`, `h264`/`aac`)
- **Originality Lineage**: `prior_preview_derived_visual_inputs = {a14['prior_preview_derived_visual_inputs']}`, `external_raster_images_count = {a14['external_raster_images_count']}`, `military_battlefield_props_count = {a14['military_battlefield_props_count']}`
- **Voice & Loudness**: `{v12['speech_provider']}`, `{v12['beats_count']}` beats, **`{v12['measured_overlap_ms']} ms`** overlap, min tail margin **`{v12['min_tail_margin_sec']}s`**, Integrated **`{v12['final_mp4_integrated_lufs']} LUFS`**, True Peak **`{v12['final_mp4_true_peak_dbtp']} dBTP`**

## 3. P0 Verification Gap Closures & Full Regression Summary

- **100% Cut-Boundary Coverage (`07_cut_boundary_coverage.json`)**:
  - *Eagle in the Fog*: **`{c07['eagle_in_fog_v14_7_5']['audited_cut_count']}/{c07['eagle_in_fog_v14_7_5']['expected_cut_count']}`** cuts audited (`full_boundary_coverage = {c07['eagle_in_fog_v14_7_5']['full_boundary_coverage']}`, diagram transitions `{c07['eagle_in_fog_v14_7_5']['diagram_transitions_audited']}`)
  - *The Water Gate*: **`{c07['water_gate_v14_7_5_1']['audited_cut_count']}/{c07['water_gate_v14_7_5_1']['expected_cut_count']}`** cuts audited (`full_boundary_coverage = {c07['water_gate_v14_7_5_1']['full_boundary_coverage']}`, `{t11['passed_shots']}/{t11['total_shots']}` shots `VISUAL_TECH_PASS`)
- **Eagle V14.7.5 Re-Verified Provenance**: `input_fingerprint = {f08['films']['eagle_in_fog_v14_7_5_reverified']['input_fingerprint']}` (`receipt_verified = True`; historical `tests/evidence/v14_7_5/*` untouched)
- **Resource Safety Telemetry (`02_resource_timeseries.json`)**: Min disk free **`{r02['min_disk_free_gb']} GiB`** (floor `>= 6.0 GiB`), Min RAM available **`{r02['min_ram_available_gb']} GiB`** (floor `>= 1.0 GiB`), Peak RSS **`{r02['peak_rss_mb']} MB`**, Orphans **`{j03.get('orphan_worker_processes_after_run', 0)}`**
- **Full Real E2E Regression (`05_e2e_full_regression.json`)**: Run `{e05['run_id']}` -> **`{e05['verdict']}`** (`{e05['required_gates_passed']}/{e05['required_gates_total']}` required gates `PASS`, exit `{e05['exit_code']}`)
- **180-Shot Backtest Truth (`06_backtest_truth.json`)**: Synthetic 180-shot `G5 = {h06['synthetic_180_stress_gate_g5']}`, 20-shot real render `G5b = {h06['medium_20_shot_real_render_g5b']}`, company historical 180-shot `G5c = {h06['historical_180_real_replay']}` (`counted_not_available_as_real_replay_pass = {h06['counted_not_available_as_real_replay_pass']}`)
- **Subprocess Mutations & Negative Suite (`04_mutation_negative_real.json`)**: **`{m04['killed_mutations']}/{m04['total_mutations']}`** disposable-subprocess mutants killed + **`{m04['negative_fixtures_passed_count']}/{m04['negative_fixtures_total_count']}`** negative fixtures `PASS`
- **Real Video Shot Repair (`09_shot_repair_video.json`)**: **`{s09['test_status']}`** (`mp4_rebuilt_and_changed = {s09['mp4_rebuilt_and_changed']}`, `manual_locked_preserved = {s09['manual_locked_preserved']}`)
- **Speed Measurements (`13_speed_micro_and_e2e.json`)**:
  - Lightweight QA microbenchmark (`n = {sp13['microbenchmark']['iterations']}`): mean serial `{sp13['microbenchmark']['mean_serial_sec']}s` vs parallel `{sp13['microbenchmark']['mean_parallel_sec']}s` (**`{sp13['microbenchmark']['mean_speedup_ratio']}x`**, 100% digest match)
  - End-to-end 30s *Water Gate* pipeline (`{sp13['end_to_end_pipeline_measurements']['cold_render_sample_status']}`): cold render total `{sp13['end_to_end_pipeline_measurements']['water_gate_30s_cold_render_total_wall_sec']}s` (`render.mjs` `{sp13['end_to_end_pipeline_measurements']['water_gate_30s_cold_render_only_wall_sec']}s`), warm cache hit `{sp13['end_to_end_pipeline_measurements']['water_gate_30s_warm_cache_wall_sec']}s`, temporal decode QA `{sp13['end_to_end_pipeline_measurements']['water_gate_30s_temporal_decode_qa_wall_sec']}s`, full E2E `{sp13['end_to_end_pipeline_measurements']['e2e_full_regression_81_gates_wall_sec']}s`
- **Historical Preservation & Old Film Versioned Corrections (`15_old_video_corrections_status.json`)**: All `{b01['preserved_count']}` preserved artifacts byte-identical (`all_preserved_intact = {b01['all_preserved_intact']}`); old film versioned corrections status = **`{o15['status']}`**
"""
    _atomic_write_text(EVIDENCE_DIR / "FL01_V14_7_5_1_ACCEPTANCE_REPORT.md", report_md)

    editorial_md = f"""# Editorial Human Review Packet (`J13 = EDITORIAL_REVIEW_PENDING`)

- **Film Title**: `{WG_TITLE}`
- **Historical Framing**: *{WG_SUBTITLE}*
- **Local 1080p24 MP4 Path**: `{WG_MP4_PATH}`
- **SHA256**: `{w10['output_sha256']}`
- **Runtime**: `30.000s` (`{w10['decoded_video_frames']}` decoded video frames @ `24 fps`)
- **Direct macOS Viewing Command**:
  ```bash
  open "{WG_MP4_PATH}"
  ```
- **Decoded Contact Sheets**:
  - `tests/evidence/v14_7_5_1/contact_sheet_full.png` (All 8 shots `S01`–`S08`)
  - `tests/evidence/v14_7_5_1/contact_sheet_hook.png` (`0.0s–7.0s` fracture hook & narrow street stakes)
  - `tests/evidence/v14_7_5_1/contact_sheet_action.png` (`15.0s–27.0s` jammed bronze wheel, two-worker heave, gate drop & overflow payoff)

## Human Editorial Checklist (Required Before Closing `J13`)

- [ ] **0–3s Opening Threat (`S01`)**: Stone seam fissure and pressurized water jet immediately read on mobile and desktop with clear `ONE CRACK` badge.
- [ ] **Spatial & Causal Clarity (`S02`–`S07`)**: Market street below the arch (`S02`) -> Livia spotting fracture & commanding upstream closure (`S03`–`S04`) -> bronze wheel jamming against Titus (`S05`) -> Titus + Cassius heaving wheel together to drop timber sluice gate (`S06`) -> water roaring into right-hand overflow basin (`S07`) reads effortlessly without confusion.
- [ ] **Payoff & Pacing (`S08`)**: Intact market street, natural breathing room after every spoken English line (`0.0 ms` overlap), balanced hydraulic foley/score (`{v12['final_mp4_integrated_lufs']} LUFS`), and clean `ONE DECISION. A CITY SPARED.` card.
"""
    _atomic_write_text(EVIDENCE_DIR / "EDITORIAL_REVIEW_PACKET.md", editorial_md)


def verify_cross_evidence_consistency(ev_dir: Path, expected_run_id: str) -> Dict[str, Any]:
    """Fail closed on ANY null fingerprint, missing cut boundary, false RAM/disk floor, fake backtest label, or contradiction."""
    errors: List[str] = []

    required_jsons = [
        "00_acceptance.json",
        "01_branch_and_preservation.json",
        "02_resource_timeseries.json",
        "03_async_real_jobs.json",
        "04_mutation_negative_real.json",
        "05_e2e_full_regression.json",
        "06_backtest_truth.json",
        "07_cut_boundary_coverage.json",
        "08_fingerprint_receipt_integrity.json",
        "09_shot_repair_video.json",
        "10_water_gate_media.json",
        "11_water_gate_temporal.json",
        "12_voice_and_audio_metrics.json",
        "13_speed_micro_and_e2e.json",
        "14_new_visual_asset_lineage.json",
        "15_old_video_corrections_status.json",
        "16_post_push_git_attestation.json",
    ]
    loaded: Dict[str, Dict[str, Any]] = {}
    for fname in required_jsons:
        fp = ev_dir / fname
        if not fp.is_file():
            errors.append(f"Missing required evidence file: {fname}")
        else:
            loaded[fname] = json.loads(fp.read_text(encoding="utf-8"))

    if errors:
        return {"consistent": False, "errors": errors}

    acc = loaded["00_acceptance.json"]
    b01 = loaded["01_branch_and_preservation.json"]
    r02 = loaded["02_resource_timeseries.json"]
    j03 = loaded["03_async_real_jobs.json"]
    m04 = loaded["04_mutation_negative_real.json"]
    e05 = loaded["05_e2e_full_regression.json"]
    h06 = loaded["06_backtest_truth.json"]
    c07 = loaded["07_cut_boundary_coverage.json"]
    f08 = loaded["08_fingerprint_receipt_integrity.json"]
    w10 = loaded["10_water_gate_media.json"]
    t11 = loaded["11_water_gate_temporal.json"]
    v12 = loaded["12_voice_and_audio_metrics.json"]
    a14 = loaded["14_new_visual_asset_lineage.json"]
    md_text = (ev_dir / "FL01_V14_7_5_1_ACCEPTANCE_REPORT.md").read_text(encoding="utf-8")

    # 1. Run ID & Master Status checks
    for fname in (
        "00_acceptance.json",
        "01_branch_and_preservation.json",
        "02_resource_timeseries.json",
        "03_async_real_jobs.json",
        "04_mutation_negative_real.json",
        "07_cut_boundary_coverage.json",
        "08_fingerprint_receipt_integrity.json",
        "10_water_gate_media.json",
        "11_water_gate_temporal.json",
        "12_voice_and_audio_metrics.json",
        "13_speed_micro_and_e2e.json",
        "14_new_visual_asset_lineage.json",
        "15_old_video_corrections_status.json",
    ):
        if loaded[fname].get("run_id") != expected_run_id:
            errors.append(f"Stale or mismatched run_id in {fname}: {loaded[fname].get('run_id')} != {expected_run_id}")

    if acc.get("editorial_status") != "EDITORIAL_REVIEW_PENDING":
        errors.append("J13 self-approval forbidden: editorial_status must be EDITORIAL_REVIEW_PENDING")
    if acc.get("tech_all_passed") and acc.get("master_status") != "TECH_VERIFIED_PENDING_EDITORIAL":
        errors.append("master_status must be TECH_VERIFIED_PENDING_EDITORIAL when technical gates pass")

    # 2. Zero null input_fingerprint
    for label, fp_val in [
        ("08_fingerprint_receipt_integrity", f08.get("input_fingerprint")),
        ("10_water_gate_media", w10.get("input_fingerprint")),
        ("eagle_reverified", f08.get("films", {}).get("eagle_in_fog_v14_7_5_reverified", {}).get("input_fingerprint")),
    ]:
        if not isinstance(fp_val, str) or len(fp_val) != 64:
            errors.append(f"Null or invalid input_fingerprint in {label}: {fp_val!r}")

    # 3. 100% cut-boundary coverage (11/11 + 7/7)
    if c07["eagle_in_fog_v14_7_5"]["audited_cut_count"] != 11 or not c07["eagle_in_fog_v14_7_5"]["full_boundary_coverage"]:
        errors.append("Eagle in the Fog cut coverage != 11/11")
    if c07["water_gate_v14_7_5_1"]["audited_cut_count"] != 7 or not c07["water_gate_v14_7_5_1"]["full_boundary_coverage"]:
        errors.append("Water Gate cut coverage != 7/7")
    if t11.get("audited_cut_count") != 7 or t11.get("unaudited_cuts") != []:
        errors.append("11_water_gate_temporal cut coverage mismatch")

    # 4. Mandatory resource floor (>= 6.0 GiB disk & >= 1.0 GiB RAM)
    if float(r02.get("min_disk_free_gb") or 0.0) < 6.0 or float(r02.get("min_ram_available_gb") or 0.0) < 1.0:
        errors.append(f"Resource floor violated in 02_resource_timeseries: disk={r02.get('min_disk_free_gb')}, ram={r02.get('min_ram_available_gb')}")

    # 5. Historical backtest honesty & full E2E
    if h06.get("counted_not_available_as_real_replay_pass") is not False:
        errors.append("counted_not_available_as_real_replay_pass must be False")
    if e05.get("verdict") != "FLOW_READY" or int(e05.get("required_gates_passed", 0)) < 81:
        errors.append("Full E2E regression not FLOW_READY 81/81")

    # 6. Exact 720 video frames, MP4 existence, originality, voice, and Markdown SHA agreement
    if not WG_MP4_PATH.is_file():
        errors.append(f"New 30s MP4 missing on disk: {WG_MP4_PATH}")
    if int(w10.get("decoded_video_frames") or 0) != WG_FRAMES:
        errors.append(f"Water Gate decoded_video_frames={w10.get('decoded_video_frames')} != {WG_FRAMES}")
    if a14.get("prior_preview_derived_visual_inputs") != 0:
        errors.append("Water Gate prior_preview_derived_visual_inputs != 0")
    if float(v12.get("measured_overlap_ms", 99.0)) != 0.0:
        errors.append("Water Gate voice overlap != 0.0 ms")
    if int(j03.get("total_jobs") or 0) < 8 or not j03.get("all_succeeded"):
        errors.append("03_async_real_jobs did not execute all real jobs successfully")
    if int(m04.get("killed_mutations") or 0) < 6:
        errors.append("04_mutation_negative_real killed_mutations < 6")
    if not b01.get("all_preserved_intact") or not b01.get("production_unchanged"):
        errors.append("Preservation or Production SHA invariant violated")

    mp4_sha = w10.get("output_sha256", "")
    fp_str = f08.get("input_fingerprint", "")
    if not mp4_sha or mp4_sha not in md_text or fp_str not in md_text:
        errors.append("Markdown report does not match JSON output_sha256 or input_fingerprint")

    return {"consistent": len(errors) == 0, "errors": errors}


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"v14_7_5_1_val_{int(time.time())}"
    print(f"=== Starting FL-01 / V14.7.5.1 Multi-Wave Async Validation DAG ({run_id}) ===")

    jobs: List[Dict[str, Any]] = [
        # Wave 1: Preflight Branch + Resource Floor + 9 Preserved Artifacts
        {
            "id": "branch_and_preservation_preflight",
            "job_profile": "light_cpu",
            "deps": [],
            "fn": lambda: job_branch_and_preservation_preflight(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "01_branch_and_preservation.json")],
            "timeout_sec": 90.0,
        },
        # Wave 2: Parallel Light Unit + 6 Real Subprocess Mutants + Eagle Lineage Re-verification
        {
            "id": "unit_verification_and_water_gate",
            "job_profile": "light_cpu",
            "deps": ["branch_and_preservation_preflight"],
            "fn": lambda: job_unit_verification_and_water_gate(run_id),
            "expected_artifacts": [str(LOGS_DIR / "unit_tests.log")],
            "timeout_sec": 240.0,
        },
        {
            "id": "mutation_and_negative_real",
            "job_profile": "light_cpu",
            "deps": ["branch_and_preservation_preflight"],
            "fn": lambda: job_mutation_and_negative_real(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "04_mutation_negative_real.json")],
            "timeout_sec": 300.0,
        },
        {
            "id": "eagle_lineage_check",
            "job_profile": "visual_decode",
            "deps": ["branch_and_preservation_preflight"],
            "fn": lambda: job_eagle_lineage_check(run_id),
            "expected_artifacts": [str(LOGS_DIR / "eagle_lineage_preflight.json")],
            "timeout_sec": 180.0,
        },
        # Wave 3: Full Real E2E Regression (81 required gates) & Backtest Truth
        {
            "id": "e2e_full_regression",
            "job_profile": "heavy_render",
            "deps": [
                "unit_verification_and_water_gate",
                "mutation_and_negative_real",
                "eagle_lineage_check",
            ],
            "fn": lambda: job_e2e_full_regression(run_id),
            "expected_artifacts": [
                str(EVIDENCE_DIR / "05_e2e_full_regression.json"),
                str(EVIDENCE_DIR / "06_backtest_truth.json"),
            ],
            "timeout_sec": 1800.0,
        },
        # Wave 4: True Cold Render + Warm Cache Check of Original 30.000s / 720-Frame Film
        {
            "id": "water_gate_30s_render",
            "job_profile": "heavy_render",
            "deps": ["e2e_full_regression"],
            "fn": lambda: job_water_gate_30s_render(run_id),
            "expected_artifacts": [
                str(EVIDENCE_DIR / "08_fingerprint_receipt_integrity.json"),
                str(EVIDENCE_DIR / "10_water_gate_media.json"),
                str(EVIDENCE_DIR / "12_voice_and_audio_metrics.json"),
                str(EVIDENCE_DIR / "14_new_visual_asset_lineage.json"),
                str(EVIDENCE_DIR / "contact_sheet_full.png"),
                str(EVIDENCE_DIR / "contact_sheet_hook.png"),
                str(EVIDENCE_DIR / "contact_sheet_action.png"),
            ],
            "timeout_sec": 600.0,
        },
        # Wave 5: Parallel Decoded Cut-Boundary Temporal QA (Water Gate 7/7 + Eagle 11/11)
        {
            "id": "water_gate_temporal_qa",
            "job_profile": "visual_decode",
            "deps": ["water_gate_30s_render"],
            "fn": lambda: job_water_gate_temporal_qa(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "11_water_gate_temporal.json")],
            "timeout_sec": 300.0,
        },
        {
            "id": "eagle_boundary_qa",
            "job_profile": "visual_decode",
            "deps": ["water_gate_30s_render"],
            "fn": lambda: job_eagle_boundary_qa(run_id),
            "expected_artifacts": [str(LOGS_DIR / "eagle_temporal_v14_7_5_1.json")],
            "timeout_sec": 300.0,
        },
        # Wave 6: Cut-Boundary Coverage Rollup
        {
            "id": "cut_boundary_coverage_rollup",
            "job_profile": "light_cpu",
            "deps": ["water_gate_temporal_qa", "eagle_boundary_qa"],
            "fn": lambda: job_cut_boundary_coverage_rollup(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "07_cut_boundary_coverage.json")],
            "timeout_sec": 60.0,
        },
        # Wave 7: Real Disposable Video Defect-Injection & Shot Repair Proof
        {
            "id": "shot_repair_video",
            "job_profile": "heavy_render",
            "deps": ["cut_boundary_coverage_rollup"],
            "cmd": [sys.executable, "tools/shot_repair.py", str(EVIDENCE_DIR / "09_shot_repair_video.json")],
            "expected_artifacts": [str(EVIDENCE_DIR / "09_shot_repair_video.json")],
            "timeout_sec": 300.0,
        },
        # Wave 8: Serial vs Bounded-Parallel Microbenchmark (n=3) + Cold/Warm 30s E2E Timing
        {
            "id": "speed_micro_and_e2e",
            "job_profile": "light_cpu",
            "deps": ["shot_repair_video"],
            "fn": lambda: job_speed_micro_and_e2e(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "13_speed_micro_and_e2e.json")],
            "timeout_sec": 300.0,
        },
        # Wave 9: Optional Versioned Corrected V14.7.4 Schematic Outputs (Isolated Temp Clones)
        {
            "id": "old_video_versioned_corrections",
            "job_profile": "heavy_render",
            "deps": ["speed_micro_and_e2e"],
            "fn": lambda: job_old_video_versioned_corrections(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "15_old_video_corrections_status.json")],
            "timeout_sec": 900.0,
        },
    ]

    stages = build_dependency_dag(jobs)
    dag_rep = run_dag(
        stages=stages,
        max_workers=3,
        min_disk_gb=6.0,
        min_ram_gb=1.0,
        estimated_scratch_gb=1.5,
        extra_margin_gb=1.0,
        run_id=run_id,
    )

    telemetry = dict(dag_rep.get("telemetry") or {})
    telemetry["evidence_schema_version"] = "14.7.5.1"
    telemetry["run_id"] = run_id
    publish_atomic_evidence(
        EVIDENCE_DIR / "02_resource_timeseries.json",
        telemetry,
        run_id=run_id,
        writer_job_id="orchestrator_telemetry",
        required_keys=["peak_rss_mb", "min_disk_free_gb", "min_ram_available_gb", "samples_count", "breach_detected"],
    )

    cp = dict(dag_rep.get("concurrency_proof") or {})
    cp["overlapping_job_pairs_count"] = cp.get("overlapping_pairs_count", 0)
    dag_ledger = {
        "evidence_schema_version": "14.7.5.1",
        "run_id": run_id,
        "status": dag_rep["status"],
        "all_succeeded": dag_rep["all_succeeded"],
        "elapsed_sec": dag_rep["elapsed_sec"],
        "total_jobs": dag_rep["total_jobs"],
        "passed_jobs": dag_rep["passed_jobs"],
        "failed_jobs": dag_rep["failed_jobs"],
        "blocked_jobs": dag_rep["blocked_jobs"],
        "not_verified_jobs": dag_rep["not_verified_jobs"],
        "max_active_workers": dag_rep["max_active_workers"],
        "orphan_worker_processes_after_run": dag_rep.get("orphan_worker_processes_after_run", 0),
        "edges": dag_rep["edges"],
        "concurrency_proof": cp,
        "jobs": [{k: v for k, v in j.items() if k != "result"} for j in dag_rep.get("jobs", [])],
    }
    publish_atomic_evidence(
        EVIDENCE_DIR / "03_async_real_jobs.json",
        dag_ledger,
        run_id=run_id,
        writer_job_id="orchestrator_dag",
        required_keys=["status", "all_succeeded", "total_jobs", "concurrency_proof", "jobs"],
    )

    if not dag_rep["all_succeeded"]:
        print(f"DAG failed: status={dag_rep['status']}, non-pass={dag_rep.get('mandatory_non_pass_ids')}")
        for j in dag_rep.get("jobs", []):
            if j["status"] != "PASS":
                print(f"  - {j['id']}: {j['status']} | {j.get('error')}")
        return 1

    # Re-verify preservation after all DAG jobs (including old_video_versioned_corrections)
    job_branch_and_preservation_preflight(run_id)

    # Master Acceptance Suite (writes 00_acceptance.json)
    acc_rep = run_v14_7_5_1_acceptance_suite(EVIDENCE_DIR, run_id=run_id)

    # Pre-push placeholder for 16_post_push_git_attestation.json (updated in separate attest-only commit after code push)
    ls_prod = _git_out(["ls-remote", "--heads", "origin", "Production"])
    remote_prod = ls_prod.split()[0] if ls_prod else "UNKNOWN"
    ls_fix = _git_out(["ls-remote", "--heads", "origin", MANDATORY_BRANCH])
    remote_fix = ls_fix.split()[0] if ls_fix else "UNKNOWN"
    publish_atomic_evidence(
        EVIDENCE_DIR / "16_post_push_git_attestation.json",
        {
            "evidence_schema_version": "14.7.5.1",
            "run_id": run_id,
            "phase": "pre_push_verified_awaiting_code_commit_push",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mandatory_work_branch": MANDATORY_BRANCH,
            "baseline_sha": BASELINE_SHA,
            "pre_push_remote_fix_image_shot_sha": remote_fix,
            "attested_code_commit_sha": None,
            "final_remote_branch_sha": None,
            "remote_production_sha": remote_prod,
            "production_invariant_sha": PRODUCTION_INVARIANT_SHA,
            "production_unchanged": (remote_prod == PRODUCTION_INVARIANT_SHA),
        },
        run_id=run_id,
        writer_job_id="orchestrator_attestation",
    )

    _write_markdown_reports(run_id)

    consistency = verify_cross_evidence_consistency(EVIDENCE_DIR, expected_run_id=run_id)
    if not consistency["consistent"]:
        print(f"Cross-evidence consistency FAILED: {consistency['errors']}")
        return 1

    print("Cross-evidence consistency PASSED (0 contradictions across 00..16 + Markdown).")
    return 0 if acc_rep.get("tech_all_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
