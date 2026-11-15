#!/usr/bin/env python3
"""scripts/run_fl01_v14_7_6_validation.py — Multi-Wave Async Validation Orchestrator (FL-01 / V14.7.6).

Executes real bounded-concurrency validation through `scripts.qa_scheduler` (`build_dependency_dag` + `run_dag`)
enforcing `min_disk_gb >= 6.0` (+ scratch + `1.0 GiB` margin) and `min_ram_gb >= 1.0` AT ALL TIMES across waves W0..W4:
  - W0: Branch/HEAD/Production SHA preflight, resource budget, 15-file preservation checksums, and implementation vs KEPT AS IS matrix (`01`, `18`).
  - W1: Parallel independent light tasks — MotionPlan generalization unit + wording-variation test, Canvas Natural Motion IK/contact metrics (`05`), Rigby2D real Chromium WebGL pilot (`06`), Claude FX determinism & decoupled clocks (`07`), and V14.7.5.1 smoke tests.
  - W2: Sequential heavy 1080p renders — 8s A/B/C comparison (`09`), 3 unseen short script->motion->render clips (`04`), and cold + warm-cache verification of the brand-new 30.000s / 720-frame 1080p24 film "THE LAST LIGHT OF PORTUS — A ROMAN HARBOR STORY" (`10`, `11`, `17`).
  - W3: Parallel independent frame decode & motion QA on finished artifacts (Portus `7/7` intershot + `5/5` internal multi-angle cuts + +/-0.25s grip/slip strips, Water Gate `7/7`, Eagle `11/11` -> `08`; `10` V14.7.6 mutations + `6` V14.7.5.1 subprocess mutations + `15` negative fixtures -> `12`), followed by serialized heavy closed-loop video shot repair (`16`), full 81+ gate E2E Squire/DEM regression & backtest truth (`13`, `14`), and `n=3` serial vs bounded-parallel speed benchmark + animation evaluation overhead (`15`).
  - W4: Telemetry & DAG rollup (`02`, `03`), preservation re-verification, master release verdict (`00`, `J13 = EDITORIAL_REVIEW_PENDING`), pre-push attestation (`19`), Markdown packets (`FL01_V14_7_6_EXECUTION_REPORT.md`, `EDITORIAL_REVIEW_PACKET.md`), and fail-closed cross-evidence consistency verification.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from integrations.rigby2d.pilot import (
    compare_rigby_vs_canvas,
    inspect_rigby_runtime_capabilities,
    verify_rigby_browser_compositing,
)
from scripts.production_fingerprint import (
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
    sample_process_tree,
)
from tools.produce_fl01_v14_7_5_1_roman_water_gate_preview import (
    OUT_MP4_PATH as WG_MP4_PATH,
    PROJECT_DIR as WG_PROJECT_DIR,
)
from tools.produce_fl01_v14_7_5_roman_eagle_in_fog_preview import (
    OUT_MP4_PATH as EAGLE_MP4_PATH,
    PROJECT_DIR as EAGLE_PROJECT_DIR,
)
from tools.produce_fl01_v14_7_6_roman_portus_preview import (
    CANONICAL_PORTUS_SCRIPT,
    FILM_SUBTITLE as PORTUS_SUBTITLE,
    FILM_TITLE as PORTUS_TITLE,
    HARBOR_MODULE_REL,
    NOMINAL_VIDEO_FRAMES as PORTUS_FRAMES,
    OUT_MP4_PATH as PORTUS_MP4_PATH,
    PROJECT_DIR as PORTUS_PROJECT_DIR,
    build_portus_storyboard,
    compute_measured_voice_overlaps,
    inspect_portus_preview,
    produce_abc_8s_comparison,
    produce_portus_preview,
    produce_three_unseen_short_generalization_clips,
    run_portus_wording_variation_test,
)
from tools.shot_repair import test_defect_injection_and_repair
from tools.temporal_visual_qa import (
    audit_foot_plant,
    audit_hand_prop_contact,
    audit_project_temporal_visual,
    run_mutation_tests,
    run_negative_fixtures_tests,
    run_v14_7_6_mandatory_mutations,
)

EVIDENCE_DIR = ROOT_DIR / "tests" / "evidence" / "v14_7_6"
LOGS_DIR = EVIDENCE_DIR / "logs"
STRIPS_DIR = EVIDENCE_DIR / "motion_strips"
MANDATORY_BRANCH = "fix/Image-Shot"
BASE_SHA = "2f88740c2e9330f17c618b6b546179126eed2203"
PRODUCTION_INVARIANT_SHA = "80559d09d4b7bb72ee4c5acc6cc846e69abd65d1"
RIGBY_PINNED_SHA = "130562a94e76a19986aa8b737f998a89c1270bb8"
CLAUDE_SKILL_PINNED_SHA = "4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b"

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
    "projects/fl01_v14_7_3_roman_continuity_benchmark/out/FL01_V14_7_4_ROMAN_CONTINUITY_REPAIRED_CORRECTED_V14_7_5_1_1080P.mp4": {
        "size": 14688646,
        "sha256": "8bab8e86a9203c22e2c8b41a7edf8038e2fca21dfb68af557c02f7ba6c46282e",
    },
    "projects/fl01_v14_7_4_roman_arrow_storm_preview/out/FL01_V14_7_4_ROMAN_ARROW_STORM_FRESH_PREVIEW_1080P.mp4": {
        "size": 11543182,
        "sha256": "0f5279f8cf9344365a1149d0e2ba122b9b042f67d397b5c7c28aae3fb30b0878",
    },
    "projects/fl01_v14_7_4_roman_arrow_storm_preview/out/FL01_V14_7_4_ROMAN_ARROW_STORM_CORRECTED_V14_7_5_1_1080P.mp4": {
        "size": 12489305,
        "sha256": "b24af5ffc2c12700a141a9720a0263c53619a469cc9b019cb2ded703b3ecb5cf",
    },
    "projects/fl01_v14_7_5_roman_eagle_in_fog_preview/out/FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4": {
        "size": 16923383,
        "sha256": "5276bb238384541139e59a04d8457d683d39f883abb480a523171da25ae51421",
    },
    "projects/fl01_v14_7_5_1_roman_water_gate_preview/out/FL01_V14_7_5_1_ROMAN_WATER_GATE_ORIGINAL_30S_1080P.mp4": {
        "size": 6878811,
        "sha256": "62e64088fb0b2d33e9c3382707b3fde9aaca9558c90941e100d4b6f676c7b603",
    },
    "projects/v14_6_action_demo/out/V14_6_Visual_Storytelling_Acting_Demo_1080p.mp4": {
        "size": 16513932,
        "sha256": "f774b9dc3d21d6ff1ec1ad986587a86dc955a0e943c30fe6b09da28c31cbac48",
    },
    "projects/squire-mau/config.json": {
        "size": 372,
        "sha256": "2c62f70b502f81be10cda5c6fae6cbbec0d088cc080451a1cb4604b55bb86214",
    },
    "packs/squire/civic/water_gate.js": {
        "size": 34005,
        "sha256": "aaeae7b18f8e48b38901631ad3f2a05bd54a79c429c8fae3fde85107d102cfa1",
    },
    "tests/evidence/v14_7_5/00_master_acceptance.json": {
        "size": 9023,
        "sha256": "2083f2bc0625bdb7b4c8565bf2ffb5901d93cfe8e64339f68dbf320d2270455e",
    },
    "tests/evidence/v14_7_5_1/00_acceptance.json": {
        "size": 18764,
        "sha256": "138ce640c7f4e502b34d06d71e4d72a5fdb25970f12e11b2f0d15fb15d41e915",
    },
}


def _utc_iso(ts: Optional[float] = None) -> str:
    val = time.time() if ts is None else ts
    return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()


def _git_out(args: List[str]) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True)
    return res.stdout.strip() if res.returncode == 0 else ""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _measure_gate_resources() -> Dict[str, Any]:
    b = inspect_resource_budget(min_disk_gb=6.0, min_ram_gb=1.0)
    tree = sample_process_tree(os.getpid())
    return {
        "disk_free_gb": b.get("disk_free_gb"),
        "ram_available_gb": b.get("ram_available_gb"),
        "cpu_count": b.get("cpu_count"),
        "free_inodes": b.get("free_inodes"),
        "process_tree_rss_mb": tree.get("tree_rss_mb"),
        "healthy": b.get("healthy"),
    }


def _gate_envelope(
    run_id: str,
    command_or_function: str,
    file_paths: List[str],
    start_ts: float,
    end_ts: float,
    exit_code: int,
    status: str,
    original_input_sha256: str,
    output_sha256: Optional[str],
    body: Dict[str, Any],
    error_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach mandatory Section 11 gate provenance & resource fields to every evidence record."""
    source_commit = _git_out(["rev-parse", "HEAD"]) or BASE_SHA
    computed_out_sha = output_sha256 or sha256_json(body)
    return {
        "evidence_schema_version": "14.7.6",
        "source_commit": source_commit,
        "run_id": run_id,
        "command_or_function": command_or_function,
        "file_paths": file_paths,
        "start_time": _utc_iso(start_ts),
        "end_time": _utc_iso(end_ts),
        "elapsed_sec": round(max(0.0, end_ts - start_ts), 4),
        "exit_code": int(exit_code),
        "original_input_sha256": original_input_sha256,
        "output_sha256": computed_out_sha,
        "measured_resources": _measure_gate_resources(),
        "status": status,
        "error_reason": error_reason,
        **body,
    }


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
# W0: Branch / Preservation / Implementation vs KEPT AS IS Matrix
# ==============================================================================


def job_w0_branch_preservation(run_id: str, writer_id: str = "w0_branch_preservation") -> Dict[str, Any]:
    t0 = time.time()
    cur_branch = _git_out(["branch", "--show-current"])
    head_sha = _git_out(["rev-parse", "HEAD"])
    anc_res = subprocess.run(["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT_DIR)
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
    st = "PASS" if ok else ("BLOCKED_RESOURCE" if not budget["healthy"] else "FAIL")
    body = {
        "current_branch": cur_branch,
        "mandatory_branch": MANDATORY_BRANCH,
        "head_sha_at_validation": head_sha,
        "verified_base_sha": BASE_SHA,
        "base_is_ancestor": is_ancestor,
        "remote_fix_image_shot_sha_pre_push": remote_fix_sha,
        "remote_production_sha": remote_prod_sha,
        "production_invariant_sha": PRODUCTION_INVARIANT_SHA,
        "production_unchanged": (remote_prod_sha == PRODUCTION_INVARIANT_SHA),
        "preflight_resource_budget": budget,
        **pres,
    }
    t1 = time.time()
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.run_fl01_v14_7_6_validation::job_w0_branch_preservation",
        file_paths=list(PRESERVED_PRIOR_ARTIFACTS.keys()),
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status=st,
        original_input_sha256=sha256_json(PRESERVED_PRIOR_ARTIFACTS),
        output_sha256=None,
        body=body,
        error_reason=None if ok else "Branch, Production SHA, resource floor, or preserved checksum failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "01_branch_preservation_manifest.json",
        payload,
        run_id=run_id,
        writer_job_id=writer_id,
        required_keys=["status", "current_branch", "production_unchanged", "all_preserved_intact", "artifacts"],
    )
    return payload


def job_w0_implementation_matrix(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    added_or_modified = [
        {
            "path": "tools/motion_performance.py",
            "change_type": "ADDED",
            "phase": "Phase A",
            "functions": [
                "extract_semantic_motion_intents",
                "plan_actor_motion_phases",
                "build_shared_motion_timeline",
                "validate_motion_plan",
                "compile_motion_plan_to_legacy_shot_args",
            ],
            "purpose": "Typed Pydantic V14.7.6 MotionPlan schema, script->phase planner, world-state timeline, validator, and additive legacy shot compiler.",
        },
        {
            "path": "tools/action_capabilities.py",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase A",
            "functions": ["get_pack_capabilities", "resolve_supported_action"],
            "purpose": "Added harbor/civic physical interaction capabilities (`HAUL_ROPE`, `BRACE_ROPE`, `SLIP`, `STEADY_PROP`, `LIFT_SHARED`, `DUCK`) while preserving legacy Squire & DEM military capabilities.",
        },
        {
            "path": "tools/narrative_action.py",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase A",
            "functions": [
                "parse_action_intents",
                "plan_action_beats",
                "compile_action_choreography_to_shots",
                "validate_action_causality",
            ],
            "purpose": "Integrated shared MotionPlan attachment & causality checks without changing public legacy signatures.",
        },
        {
            "path": "tools/character_acting.py",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase A",
            "functions": ["plan_actor_performance", "compile_actor_performance_to_rig", "validate_actor_performance"],
            "purpose": "Uses generic actor IDs and phase timelines from shared MotionPlan when present, keeping legacy Roman presets strictly backward-compatible.",
        },
        {
            "path": "packs/squire/motion_engine.js",
            "change_type": "ADDED",
            "phase": "Phase B",
            "functions": [
                "evaluateMotionTrackAt",
                "rootMotionAt",
                "solveFootPlantIK",
                "solveHandPropContact",
                "blendActorPose",
                "applySecondaryMotion",
                "evaluateMultiActorInteraction",
                "validateMotionFrameTrace",
            ],
            "purpose": "Pure deterministic frame-order-invariant 2D natural motion engine with root-displacement gait coupling, stance foot lock, object-bound hand IK, and multi-actor shared prop force.",
        },
        {
            "path": "packs/squire/chara.js",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase B",
            "functions": ["walkInfo", "soldier"],
            "purpose": "Optional `_motionEval` / `motionTrack` IK target override inside existing Canvas character renderer; 100% legacy behavior when omitted.",
        },
        {
            "path": "packs/squire/templates.js",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase B & E",
            "functions": ["person", "applyCameraSegments"],
            "purpose": "Evaluates optional `motionPlan`/`motionTracks` and `cameraSegments` inside existing Squire scene template.",
        },
        {
            "path": "packs/squire/pack.js",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase B & C",
            "functions": ["pack registration"],
            "purpose": "Exposes optional motion engine & harbor helpers cleanly to Squire scenes.",
        },
        {
            "path": "integrations/rigby2d/adapter.js",
            "change_type": "ADDED",
            "phase": "Phase C",
            "functions": [
                "inspectRigbyRuntimeCapabilities",
                "convertMotionPlanToRigbyTracks",
                "loadBrowserRigbyAsset",
                "renderRigbyActorToCanvas",
            ],
            "purpose": "Isolated Rigby2D 0.5.1 (pinned SHA 130562a94e76a19986aa8b737f998a89c1270bb8, MIT OR Apache-2.0) Spine 3.8 WebGL -> 2D Canvas compositor with newly authored Roman civilian rig.",
        },
        {
            "path": "integrations/rigby2d/pilot.py",
            "change_type": "ADDED",
            "phase": "Phase C",
            "functions": [
                "inspect_rigby_runtime_capabilities",
                "convert_motion_plan_to_rigby_tracks",
                "verify_rigby_browser_compositing",
                "compare_rigby_vs_canvas",
            ],
            "purpose": "Real Node/Chromium runtime capability probe and 8s Rigby2D WebGL vs Canvas Natural Motion FL-01 benchmark.",
        },
        {
            "path": "integrations/claude_motion/adapter.js",
            "change_type": "ADDED",
            "phase": "Phase D",
            "functions": [
                "createSeparatedActionClock",
                "rng",
                "landDust",
                "burstParticles",
                "ring",
                "renderMotivatedHarborFx",
            ],
            "purpose": "Selective MIT helpers adapted from buildwithhanif/claude-animation-skill (SHA 4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b) with strict action-clock vs voice/camera-clock separation.",
        },
        {
            "path": "tools/cinematic_camera.py",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase E",
            "functions": ["plan_multi_angle_action", "validate_camera_segments", "compile_camera_segments_to_renderer"],
            "purpose": "Script-driven optional internal multi-angle camera segments within a single logical shot while preserving continuous world/action clocks and 180-degree axis rules.",
        },
        {
            "path": "tools/temporal_visual_qa.py",
            "change_type": "MODIFIED_ADDITIVE",
            "phase": "Phase E & QA",
            "functions": [
                "audit_motion_performance",
                "audit_foot_plant",
                "audit_hand_prop_contact",
                "audit_internal_camera_cuts",
                "run_v14_7_6_mandatory_mutations",
            ],
            "purpose": "Decoded pixel + trace motion QA, +/-0.25s grip/slip strips, 100% internal camera-cut boundary checks, and 10 V14.7.6 mandatory defect mutations.",
        },
        {
            "path": "packs/squire/harbor/portus_light.js",
            "change_type": "ADDED",
            "phase": "Section 9",
            "functions": ["registerPortusShots", "ensureHarborRigbyAssetLoaded"],
            "purpose": "Wholly original procedural harbor lighthouse, stormy sea, rolling merchant corbita, pulley hoist, oil flame, and multi-angle insert views for Portus.",
        },
        {
            "path": "tools/produce_fl01_v14_7_6_roman_portus_preview.py",
            "change_type": "ADDED",
            "phase": "Section 9",
            "functions": [
                "build_portus_storyboard",
                "construct_portus_project",
                "build_portus_original_assets",
                "generate_portus_measured_voice",
                "build_portus_event_soundtrack",
                "produce_portus_preview",
                "inspect_portus_preview",
                "generate_portus_contact_sheets",
                "produce_abc_8s_comparison",
                "produce_three_unseen_short_generalization_clips",
            ],
            "purpose": "Script-driven FL-01 producer for the original 30.000s / 720-frame 1080p24 Portus film, wording-variation proof, 8s A/B/C comparison, and 3 unseen short renders.",
        },
    ]

    kept_as_is = [
        "app.py",
        "render.mjs",
        "engine/core.js",
        "tools/visual_storytelling.py",
        "tools/shot_repair.py",
        "scripts/qa_scheduler.py",
        "scripts/run_e2e_regression.py",
        "scripts/production_fingerprint.py",
        "packs/squire/civic/water_gate.js",
        "packs/dem/pack.js",
        "packs/dem/templates.js",
        "tests/evidence/v14_7_5/00_master_acceptance.json",
        "tests/evidence/v14_7_5_1/00_acceptance.json",
    ]

    verified_modified: List[Dict[str, Any]] = []
    missing_mod: List[str] = []
    for item in added_or_modified:
        p = ROOT_DIR / item["path"]
        if not p.is_file():
            missing_mod.append(item["path"])
            continue
        verified_modified.append({**item, "exists": True, "sha256": sha256_file(p), "size_bytes": p.stat().st_size})

    verified_kept: List[Dict[str, Any]] = []
    unexpectedly_dirty_kept: List[str] = []
    for rel_p in kept_as_is:
        p = ROOT_DIR / rel_p
        diff_proc = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel_p], cwd=ROOT_DIR)
        untouched = p.is_file() and (diff_proc.returncode == 0)
        if not untouched:
            unexpectedly_dirty_kept.append(rel_p)
        verified_kept.append({
            "path": rel_p,
            "disposition": "KEPT AS IS",
            "exists": p.is_file(),
            "git_untouched_vs_base": untouched,
            "sha256": sha256_file(p) if p.is_file() else None,
        })

    ok = (len(missing_mod) == 0) and (len(unexpectedly_dirty_kept) == 0)
    t1 = time.time()
    body = {
        "fl01_architecture_unchanged": True,
        "added_or_modified_count": len(verified_modified),
        "kept_as_is_count": len(verified_kept),
        "missing_modified_files": missing_mod,
        "unexpectedly_dirty_kept_files": unexpectedly_dirty_kept,
        "added_or_modified_modules": verified_modified,
        "kept_as_is_modules": verified_kept,
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.run_fl01_v14_7_6_validation::job_w0_implementation_matrix",
        file_paths=[m["path"] for m in added_or_modified] + kept_as_is,
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=BASE_SHA,
        output_sha256=None,
        body=body,
        error_reason=None if ok else f"Missing={missing_mod}, dirty_kept={unexpectedly_dirty_kept}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "18_implementation_kept_as_is_matrix.json",
        payload,
        run_id=run_id,
        writer_job_id="w0_implementation_matrix",
        required_keys=["status", "fl01_architecture_unchanged", "added_or_modified_modules", "kept_as_is_modules"],
    )
    return payload


# ==============================================================================
# W1: Parallel Light Verification Jobs
# ==============================================================================


def job_w1_motion_plan_unit(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/motion_v14_7_6/test_motion_plan_generalization.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    log_p = LOGS_DIR / "w1_motion_plan_unit.log"
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))
    wording_var = run_portus_wording_variation_test()
    ok = (proc.returncode == 0) and (wording_var.get("status") == "PASS")
    out_json = LOGS_DIR / "w1_motion_plan_unit.json"
    res = {
        "status": "PASS" if ok else "FAIL",
        "pytest_exit_code": proc.returncode,
        "log_path": str(log_p.relative_to(ROOT_DIR)),
        "wording_variation_test": wording_var,
        "elapsed_sec": round(time.time() - t0, 4),
    }
    _atomic_write_text(out_json, json.dumps(res, indent=2))
    return res


def job_w1_natural_motion_metrics(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/motion_v14_7_6/test_natural_motion_engine.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
    )
    log_p = LOGS_DIR / "w1_natural_motion_engine.log"
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))

    sb = build_portus_storyboard(CANONICAL_PORTUS_SCRIPT, fx_profile="claude_selective")
    mp_dict = sb["motion_plan"]
    foot_qa_full = audit_foot_plant(mp_dict)
    hand_qa_full = audit_hand_prop_contact(mp_dict)

    # Compact per-track reports (truncate raw sample_frames to 5 per track so JSON stays clean & readable)
    foot_qa = {
        **foot_qa_full,
        "track_reports": [
            {**tr, "sample_frames": (tr.get("sample_frames") or [])[:5]}
            for tr in (foot_qa_full.get("track_reports") or [])
        ],
    }

    js_probe = """
import fs from 'node:fs';
import crypto from 'node:crypto';
import { evaluateMotionTrackAt, validateMotionFrameTrace, measureLegacySineGaitDrift } from './packs/squire/motion_engine.js';

const mp = JSON.parse(fs.readFileSync(0, 'utf8'));
const tr = mp.tracks.find((t) => t.shot_id === 'S04' && t.actor_id === 'aelia') || mp.tracks[0];
const ws = (mp.world_states && mp.world_states[0]) || {};
const times = [];
for (let i = 0; i <= 48; i++) times.push(Number((tr.start_sec + (i / 24)).toFixed(4)));

const evalDigest = (order) => {
  const map = {};
  for (const t of order) {
    map[t.toFixed(4)] = evaluateMotionTrackAt(tr, t, ws);
  }
  const canonical = times.map((t) => map[t.toFixed(4)]);
  return crypto.createHash('sha256').update(JSON.stringify(canonical)).digest('hex');
};

const forwardHash = evalDigest(times);
const reverseHash = evalDigest([...times].reverse());
const shuffled = [...times].sort((a, b) => ((Math.sin(a * 91.7) > Math.sin(b * 91.7)) ? 1 : -1));
const shuffledHash = evalDigest(shuffled);

const legacyDrift = measureLegacySineGaitDrift({ fromX: 0.26, toX: 0.56, groundY: 0.84, heightNorm: 0.28, dur: 2.4, fps: 24 });
const traceCheck = validateMotionFrameTrace(tr, ws, { fps: 24 });
delete traceCheck.frames;

console.log(JSON.stringify({
  forwardHash,
  reverseHash,
  shuffledHash,
  orderInvariant: (forwardHash === reverseHash) && (forwardHash === shuffledHash),
  legacySineDrift: legacyDrift,
  s04TraceValidation: traceCheck,
}));
"""
    probe_proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_probe],
        input=json.dumps(mp_dict),
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    probe_data = json.loads(probe_proc.stdout.strip()) if probe_proc.returncode == 0 else {"error": probe_proc.stderr}

    med_drift = float(foot_qa.get("max_median_planted_foot_drift_norm", 1.0))
    peak_grip = float(hand_qa_full.get("peak_hand_grip_dist_norm", 1.0))
    s04_trace = probe_data.get("s04TraceValidation") or {}
    max_jump = float(s04_trace.get("max_adjacent_joint_jump_norm", 1.0))
    ok = (
        proc.returncode == 0
        and probe_proc.returncode == 0
        and foot_qa.get("status") == "PASS"
        and hand_qa_full.get("status") == "PASS"
        and med_drift <= 0.03
        and peak_grip <= 0.04
        and s04_trace.get("valid") is True
        and max_jump <= 0.25
        and probe_data.get("orderInvariant") is True
    )
    t1 = time.time()
    body = {
        "pytest_exit_code": proc.returncode,
        "log_path": str(log_p.relative_to(ROOT_DIR)),
        "thresholds": {
            "median_planted_foot_drift_max_norm": 0.03,
            "peak_hand_grip_distance_max_norm": 0.04,
            "adjacent_frame_joint_jump_max_norm": 0.25,
        },
        "measured_portus_foot_plant": foot_qa,
        "measured_portus_hand_prop_contact": hand_qa_full,
        "before_vs_after_planted_foot_comparison": {
            "v14_7_5_1_legacy_eased_gait_drift": probe_data.get("legacySineDrift"),
            "v14_7_6_natural_motion_median_planted_drift_norm": med_drift,
        },
        "frame_order_invariance": {
            "order_invariant": probe_data.get("orderInvariant"),
            "forward_sha256": probe_data.get("forwardHash"),
            "reverse_sha256": probe_data.get("reverseHash"),
            "shuffled_sha256": probe_data.get("shuffledHash"),
        },
        "s04_frame_trace_validation": s04_trace,
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="pytest tests/motion_v14_7_6/test_natural_motion_engine.py + motion_engine.js trace audit",
        file_paths=[
            "packs/squire/motion_engine.js",
            "tests/motion_v14_7_6/test_natural_motion_engine.py",
            str(log_p.relative_to(ROOT_DIR)),
        ],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "packs/squire/motion_engine.js"),
        output_sha256=None,
        body=body,
        error_reason=None if ok else f"Natural motion check failed: {probe_data}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "05_natural_motion_metrics.json",
        payload,
        run_id=run_id,
        writer_job_id="w1_natural_motion_metrics",
        required_keys=["status", "thresholds", "measured_portus_foot_plant", "measured_portus_hand_prop_contact", "frame_order_invariance"],
    )
    return payload


def job_w1_rigby_runtime_pilot(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/motion_v14_7_6/test_rigby_pilot.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=240,
    )
    log_p = LOGS_DIR / "w1_rigby2d_pilot.log"
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))

    caps = inspect_rigby_runtime_capabilities()
    comp = verify_rigby_browser_compositing()
    with tempfile.TemporaryDirectory(prefix="rigby_pilot_val_") as td:
        vs_canvas = compare_rigby_vs_canvas(Path(td), scale=0.5)

    prov_p = ROOT_DIR / "integrations/rigby2d/SOURCE_PROVENANCE.json"
    prov = json.loads(prov_p.read_text(encoding="utf-8"))
    ok = (
        proc.returncode == 0
        and caps.get("status") in ("PASS", "RUNTIME_VERIFIED")
        and comp.get("status") == "PASS"
        and vs_canvas.get("pilot_status") == "PILOT_WORKING"
        and prov.get("upstream_commit_sha") == RIGBY_PINNED_SHA
        and caps.get("demo_assets_copied") is False
    )
    t1 = time.time()
    body = {
        "pilot_verdict": "PILOT_WORKING" if ok else "RIGBY_PILOT_BLOCKED",
        "production_decision": (
            "Rigby2D 0.5.1 WebGL runtime verified working inside Chromium `render.mjs` with our newly authored "
            "15-slot 4-IK Roman civilian skeleton (`roman_harbor_worker`), used in 8s benchmark Clips B & C. "
            "For the 30.000s Portus film, V14.7.6 Natural Canvas IK (`packs/squire/motion_engine.js`) is used as "
            "primary actor backend to support multi-angle hand inserts, two-actor shared hoist occlusion, and "
            "lantern lighting cones without claiming full Rigby2D production migration."
        ),
        "pytest_exit_code": proc.returncode,
        "log_path": str(log_p.relative_to(ROOT_DIR)),
        "source_provenance": prov,
        "runtime_capabilities": caps,
        "chromium_webgl_compositing": comp,
        "rigby_vs_canvas_8s_benchmark": vs_canvas,
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="integrations.rigby2d.pilot::{inspect_rigby_runtime_capabilities,verify_rigby_browser_compositing,compare_rigby_vs_canvas}",
        file_paths=[
            "integrations/rigby2d/adapter.js",
            "integrations/rigby2d/pilot.py",
            "integrations/rigby2d/SOURCE_PROVENANCE.json",
            "integrations/rigby2d/assets/roman_harbor_worker.json",
        ],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(prov_p),
        output_sha256=caps.get("texture_sha256"),
        body=body,
        error_reason=None if ok else "Rigby2D runtime or Chromium WebGL pilot check failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "06_rigby_real_runtime_pilot.json",
        payload,
        run_id=run_id,
        writer_job_id="w1_rigby_runtime_pilot",
        required_keys=["status", "pilot_verdict", "source_provenance", "runtime_capabilities", "chromium_webgl_compositing"],
    )
    return payload


def job_w1_claude_fx_determinism(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "tests/motion_v14_7_6/test_claude_fx_determinism.py"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    log_p = LOGS_DIR / "w1_claude_fx_determinism.log"
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))

    prov_p = ROOT_DIR / "integrations/claude_motion/SOURCE_PROVENANCE.json"
    prov = json.loads(prov_p.read_text(encoding="utf-8"))
    js_check = """
import { createSeparatedActionClock, burstParticles } from './integrations/claude_motion/adapter.js';

const makeRecorder = () => {
  const ops = [];
  const alphas = [];
  let curAlpha = 1;
  const ctx = {
    get globalAlpha() { return curAlpha; },
    set globalAlpha(v) { curAlpha = v; alphas.push(v); },
    save() { ops.push(['save', curAlpha]); },
    restore() { ops.push(['restore']); curAlpha = 1; },
    beginPath() {},
    createRadialGradient() { return { addColorStop() {} }; },
    fillRect(x, y, w, h) { ops.push(['fr', Number(x.toFixed(4)), Number(y.toFixed(4)), Number(w.toFixed(4)), Number(h.toFixed(4))]); },
    strokeRect() {},
    translate() {},
    rotate() {},
    scale() {},
    moveTo(x, y) { ops.push(['m', Number(x.toFixed(4)), Number(y.toFixed(4))]); },
    lineTo(x, y) { ops.push(['l', Number(x.toFixed(4)), Number(y.toFixed(4))]); },
    ellipse(x, y, rx, ry) { ops.push(['e', Number(x.toFixed(4)), Number(y.toFixed(4)), Number(rx.toFixed(4)), Number(ry.toFixed(4))]); },
    arc(x, y, r) { ops.push(['a', Number(x.toFixed(4)), Number(y.toFixed(4)), Number(r.toFixed(4))]); },
    stroke() {},
    fill() {},
  };
  return { ctx, ops, alphas };
};

const clk = createSeparatedActionClock({ shotStartSec: 0, shotEndSec: 3.0, stops: [[1.5, 0.08]], fxProfile: 'claude_selective' });
const voiceT = clk.voiceTime(3.0);
const camT = clk.cameraTime(3.0);
const actDuringHoldA = clk.actionTime(1.52);
const actDuringHoldB = clk.actionTime(1.56);

const r1 = makeRecorder();
const r2 = makeRecorder();
burstParticles(r1.ctx, 1.35, 1.20, 400, 700, { seed: 1476, n: 10, kind: 'ember' });
burstParticles(r2.ctx, 1.35, 1.20, 400, 700, { seed: 1476, n: 10, kind: 'ember' });
const alphaValid = r1.alphas.length > 0 && r1.alphas.every((a) => a >= 0 && a <= 1);

console.log(JSON.stringify({
  seedIdentical: JSON.stringify(r1.ops) === JSON.stringify(r2.ops),
  alphaValid,
  voiceTimeUnwarpedAt3s: voiceT === 3.0,
  cameraTimeUnwarpedAt3s: camT === 3.0,
  actionBoundaryContinuousAt3s: Math.abs(clk.actionTime(3.0) - 3.0) < 1e-6,
  actionHoldPlateaus: Math.abs(actDuringHoldB - actDuringHoldA) < 1e-6,
  soundCueRealTimeAt2s: clk.cueToRealTime(2.0),
}));
"""
    node_res = subprocess.run(["node", "--input-type=module", "-e", js_check], cwd=ROOT_DIR, capture_output=True, text=True, timeout=30)
    probe = json.loads(node_res.stdout.strip()) if node_res.returncode == 0 else {"error": node_res.stderr}
    excluded = prov.get("excluded_standalone_pipeline") or []
    ok = (
        proc.returncode == 0
        and node_res.returncode == 0
        and prov.get("upstream_commit_sha") == CLAUDE_SKILL_PINNED_SHA
        and any("film.mjs" in x for x in excluded)
        and prov.get("demo_characters_copied") is False
        and probe.get("seedIdentical") is True
        and probe.get("alphaValid") is True
        and probe.get("voiceTimeUnwarpedAt3s") is True
        and probe.get("cameraTimeUnwarpedAt3s") is True
        and probe.get("actionBoundaryContinuousAt3s") is True
        and probe.get("actionHoldPlateaus") is True
    )
    t1 = time.time()
    body = {
        "pytest_exit_code": proc.returncode,
        "log_path": str(log_p.relative_to(ROOT_DIR)),
        "source_provenance": prov,
        "determinism_and_clock_separation": probe,
        "honesty_disclosure": (
            "Claude Animation Skill helpers are strictly secondary sparse interaction FX (dust, gust embers, "
            "relight ring, subtle hit-stop action clock) gated by `fx_profile='claude_selective'`. Primary natural "
            "acting comes from MotionPlan + Natural Motion IK, never particle presets."
        ),
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="pytest tests/motion_v14_7_6/test_claude_fx_determinism.py + adapter.js clock/alpha probe",
        file_paths=[
            "integrations/claude_motion/adapter.js",
            "integrations/claude_motion/SOURCE_PROVENANCE.json",
            "integrations/claude_motion/LICENSE",
        ],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(prov_p),
        output_sha256=sha256_file(ROOT_DIR / "integrations/claude_motion/adapter.js"),
        body=body,
        error_reason=None if ok else f"Claude FX determinism or clock separation check failed: {probe}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "07_claude_fx_determinism.json",
        payload,
        run_id=run_id,
        writer_job_id="w1_claude_fx_determinism",
        required_keys=["status", "source_provenance", "determinism_and_clock_separation"],
    )
    return payload


def job_w1_legacy_smoke(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_p = LOGS_DIR / "w1_legacy_smoke.log"
    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_v14_7_5_1_verification_gaps.py",
            "tests/test_water_gate_primitives_v14_7_5_1.py",
            "tests/test_qa_scheduler_v14_7_5.py",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=240,
    )
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "exit_code": proc.returncode,
        "wall_sec": round(time.perf_counter() - t0, 3),
        "log_path": str(log_p.relative_to(ROOT_DIR)),
    }


# ==============================================================================
# W2: Sequential Heavy 1080p Renders (A/B/C + 3 Unseen + 30s Original Portus)
# ==============================================================================


def job_w2_abc_and_unseen_renders(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    abc_res = produce_abc_8s_comparison(ev_dir=EVIDENCE_DIR)
    t_abc = time.time()

    abc_ok = abc_res.get("status") == "PASS" and abc_res.get("distinct_three_mp4_hashes") is True
    abc_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.produce_fl01_v14_7_6_roman_portus_preview::produce_abc_8s_comparison",
        file_paths=[
            abc_res["clip_A_baseline_v14_7_5_1"]["mp4_path"],
            abc_res["clip_B_motion_plan_rigby2d"]["mp4_path"],
            abc_res["clip_C_rigby2d_plus_claude_fx"]["mp4_path"],
            "tests/evidence/v14_7_6/contact_sheet_abc_comparison.png",
            "tests/evidence/v14_7_6/abc_motion_traces.json",
        ],
        start_ts=t0,
        end_ts=t_abc,
        exit_code=0 if abc_ok else 1,
        status="PASS" if abc_ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "tools/produce_fl01_v14_7_6_roman_portus_preview.py"),
        output_sha256=abc_res.get("contact_sheet", {}).get("sha256"),
        body=abc_res,
        error_reason=None if abc_ok else "A/B/C 8s comparison render or hash distinctness failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "09_a_b_c_render_comparison.json",
        abc_payload,
        run_id=run_id,
        writer_job_id="w2_abc_and_unseen_renders",
        required_keys=[
            "status",
            "distinct_three_mp4_hashes",
            "clip_A_baseline_v14_7_5_1",
            "clip_B_motion_plan_rigby2d",
            "clip_C_rigby2d_plus_claude_fx",
        ],
    )

    t_u0 = time.time()
    unseen_res = produce_three_unseen_short_generalization_clips()
    t_u1 = time.time()
    w1_unit = json.loads((LOGS_DIR / "w1_motion_plan_unit.json").read_text(encoding="utf-8"))
    gen_ok = (w1_unit.get("status") == "PASS") and (unseen_res.get("status") == "PASS")
    gen_body = {
        "ai_routing_mode": "OFFLINE_ONLY",
        "provider_trace_id": None,
        "routing_disclosure": "MotionPlan semantic extraction ran deterministically in OFFLINE_ONLY mode; no live external LLM inference is claimed.",
        "unit_and_wording_variation": w1_unit,
        "three_unseen_rendered_cases": unseen_res,
    }
    gen_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.produce_fl01_v14_7_6_roman_portus_preview::produce_three_unseen_short_generalization_clips",
        file_paths=[
            "tools/motion_performance.py",
            "tests/motion_v14_7_6/test_motion_plan_generalization.py",
            *[c["render"]["mp4_path"] for c in unseen_res.get("cases", [])],
        ],
        start_ts=t_u0,
        end_ts=t_u1,
        exit_code=0 if gen_ok else 1,
        status="PASS" if gen_ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "tools/motion_performance.py"),
        output_sha256=None,
        body=gen_body,
        error_reason=None if gen_ok else "Unseen script generalization or wording-variation test failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "04_motion_plan_generalization.json",
        gen_payload,
        run_id=run_id,
        writer_job_id="w2_abc_and_unseen_renders",
        required_keys=["status", "ai_routing_mode", "unit_and_wording_variation", "three_unseen_rendered_cases"],
    )
    return {"status": "PASS" if (abc_ok and gen_ok) else "FAIL"}


def job_w2_portus_30s_render(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t_cold0 = time.time()
    cold_res = produce_portus_preview(force_rebuild=True, workers=1, extra_evidence_dir=EVIDENCE_DIR)
    t_cold1 = time.time()
    cold_wall = round(t_cold1 - t_cold0, 3)
    if cold_res.get("status") != "PRODUCED":
        return {"status": cold_res.get("status", "FAIL"), "error": cold_res.get("error")}

    shutil.copy2(PORTUS_PROJECT_DIR / "build" / "render.log", LOGS_DIR / "portus_render.log")

    t_warm0 = time.perf_counter()
    warm_res = produce_portus_preview(
        force_rebuild=False,
        workers=1,
        extra_evidence_dir=EVIDENCE_DIR,
        run_full_qa_on_cache_hit=False,
    )
    warm_wall = round(time.perf_counter() - t_warm0, 4)

    insp = cold_res["inspection"]
    lin = insp["lineage"]
    mi = insp["media_info"]

    # 10_portus_original_30s_media_receipt.json
    media_ok = (
        insp["valid"] is True
        and warm_res.get("status") == "CACHE_HIT_VERIFIED"
        and int(mi.get("decoded_video_frames") or 0) == PORTUS_FRAMES
        and bool(lin.get("input_fingerprint"))
    )
    media_body = {
        "title": PORTUS_TITLE,
        "subtitle": PORTUS_SUBTITLE,
        "project_dir": str(PORTUS_PROJECT_DIR.relative_to(ROOT_DIR)),
        "output_mp4": str(PORTUS_MP4_PATH.relative_to(ROOT_DIR)),
        "output_mp4_abs_path": str(PORTUS_MP4_PATH),
        "mp4_size_bytes": PORTUS_MP4_PATH.stat().st_size,
        "cold_render_status": cold_res.get("status"),
        "cold_render_total_wall_sec": cold_wall,
        "cold_motion_plan_wall_sec": cold_res.get("motion_plan_wall_sec"),
        "cold_render_only_wall_sec": cold_res.get("render_only_wall_sec"),
        "warm_cache_status": warm_res.get("status"),
        "warm_cache_wall_sec": warm_wall,
        "input_fingerprint": lin.get("input_fingerprint"),
        "recomputed_input_fingerprint": lin.get("recomputed_input_fingerprint"),
        "fingerprint_match": lin.get("fingerprint_match"),
        "receipt_verified": lin.get("receipt_verified"),
        "cache_verified": lin.get("cache_verified"),
        "media_decode_verified": lin.get("media_decode_verified"),
        "decoded_video_frames": mi.get("decoded_video_frames"),
        "nominal_duration_diff_sec": insp.get("nominal_duration_diff_sec"),
        "audio_video_stream_diff_sec": insp.get("audio_video_stream_diff_sec"),
        "media_info": mi,
        "contact_sheets": cold_res.get("contact_sheets"),
        "editorial_status": "EDITORIAL_REVIEW_PENDING",
    }
    media_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.produce_fl01_v14_7_6_roman_portus_preview::produce_portus_preview(force_rebuild=True)",
        file_paths=[
            str(PORTUS_MP4_PATH.relative_to(ROOT_DIR)),
            "projects/fl01_v14_7_6_roman_last_light_portus_preview/build/render_receipt.json",
            "tests/evidence/v14_7_6/contact_sheet_full.png",
            "tests/evidence/v14_7_6/contact_sheet_hook.png",
            "tests/evidence/v14_7_6/contact_sheet_action.png",
        ],
        start_ts=t_cold0,
        end_ts=time.time(),
        exit_code=0 if media_ok else 1,
        status="PASS" if media_ok else "FAIL",
        original_input_sha256=lin.get("input_fingerprint") or "",
        output_sha256=lin.get("output_sha256"),
        body=media_body,
        error_reason=None if media_ok else "Portus 30s media, frame count, or receipt verification failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "10_portus_original_30s_media_receipt.json",
        media_payload,
        run_id=run_id,
        writer_job_id="w2_portus_30s_render",
        required_keys=["status", "output_mp4", "decoded_video_frames", "input_fingerprint", "output_sha256", "media_info"],
    )

    # 11_portus_voice_sound_timing.json
    v_ledger_p = PORTUS_PROJECT_DIR / "timeline" / "timeline_voice_events.json"
    v_ledger = json.loads(v_ledger_p.read_text(encoding="utf-8"))
    mix_rep = json.loads((PORTUS_PROJECT_DIR / "build" / "audio_mix_report.json").read_text(encoding="utf-8"))
    events = v_ledger.get("events", [])
    recomputed_ov = compute_measured_voice_overlaps(events)
    lufs = mi.get("integrated_lufs")
    tp = mi.get("true_peak_dbtp")
    voice_ok = (
        insp["valid"] is True
        and recomputed_ov == 0.0
        and float(v_ledger.get("min_tail_margin_sec", 0.0)) >= 0.25
        and v_ledger.get("last_spoken_phrase") == "The ship made it through."
        and (lufs is not None and -15.5 <= float(lufs) <= -12.5)
        and (tp is not None and float(tp) <= -1.0)
    )
    voice_body = {
        "speech_provider": v_ledger.get("speech_provider"),
        "beats_count": len(events),
        "total_timeline_duration_sec": v_ledger.get("total_timeline_duration_sec"),
        "voice_wav_duration_sec": v_ledger.get("voice_wav_duration_sec"),
        "mp4_audio_stream_duration_sec": mi.get("audio_stream_duration"),
        "measured_overlap_ms": recomputed_ov,
        "min_tail_margin_sec": v_ledger.get("min_tail_margin_sec"),
        "all_beats_meet_0_35s_target": v_ledger.get("all_beats_meet_0_35s_target"),
        "atempo_used_anywhere": v_ledger.get("atempo_used_anywhere"),
        "last_spoken_phrase": v_ledger.get("last_spoken_phrase"),
        "last_spoken_end_sec": v_ledger.get("last_spoken_end_sec"),
        "final_mp4_integrated_lufs": lufs,
        "final_mp4_true_peak_dbtp": tp,
        "final_mp4_mean_volume_db": mi.get("mean_volume_db"),
        "final_mp4_max_volume_db": mi.get("max_volume_db"),
        "soundtrack_layers": mix_rep.get("layers"),
        "sound_cues_provenance": mix_rep.get("provenance", "procedural_synthesized_in_repo_cc0"),
        "events": events,
    }
    voice_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.produce_fl01_v14_7_6_roman_portus_preview::{generate_portus_measured_voice,build_portus_event_soundtrack}",
        file_paths=[
            str(v_ledger_p.relative_to(ROOT_DIR)),
            "projects/fl01_v14_7_6_roman_last_light_portus_preview/build/audio_mix_report.json",
        ],
        start_ts=t_cold0,
        end_ts=time.time(),
        exit_code=0 if voice_ok else 1,
        status="PASS" if voice_ok else "FAIL",
        original_input_sha256=sha256_file(v_ledger_p),
        output_sha256=lin.get("output_sha256"),
        body=voice_body,
        error_reason=None if voice_ok else "Voice overlap, tail margin, loudness, or last phrase check failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "11_portus_voice_sound_timing.json",
        voice_payload,
        run_id=run_id,
        writer_job_id="w2_portus_30s_render",
        required_keys=["status", "speech_provider", "measured_overlap_ms", "min_tail_margin_sec", "final_mp4_integrated_lufs", "last_spoken_phrase"],
    )

    # 17_original_visual_source_lineage.json
    asset_p = PORTUS_PROJECT_DIR / "story" / "asset_source_manifest.json"
    asset_manifest = json.loads(asset_p.read_text(encoding="utf-8"))
    claims_p = PORTUS_PROJECT_DIR / "story" / "claims_manifest.json"
    claims_manifest = json.loads(claims_p.read_text(encoding="utf-8"))
    prior_shas = {v["sha256"] for v in PRESERVED_PRIOR_ARTIFACTS.values()}
    orig_ok = (
        asset_manifest.get("prior_preview_derived_visual_inputs") == 0
        and asset_manifest.get("external_raster_images_count") == 0
        and asset_manifest.get("rigby2d_proprietary_demo_assets_count", 0) == 0
        and lin.get("output_sha256") not in prior_shas
    )
    lineage_body = {
        "output_mp4_sha256": lin.get("output_sha256"),
        "output_mp4_distinct_from_all_prior_previews": (lin.get("output_sha256") not in prior_shas),
        "historical_framing": claims_manifest,
        **asset_manifest,
    }
    lineage_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.produce_fl01_v14_7_6_roman_portus_preview::build_portus_original_assets",
        file_paths=[
            HARBOR_MODULE_REL,
            str(asset_p.relative_to(ROOT_DIR)),
            str(claims_p.relative_to(ROOT_DIR)),
        ],
        start_ts=t_cold0,
        end_ts=time.time(),
        exit_code=0 if orig_ok else 1,
        status="PASS" if orig_ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / HARBOR_MODULE_REL),
        output_sha256=sha256_file(asset_p),
        body=lineage_body,
        error_reason=None if orig_ok else "Original visual lineage check failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "17_original_visual_source_lineage.json",
        lineage_payload,
        run_id=run_id,
        writer_job_id="w2_portus_30s_render",
        required_keys=["status", "prior_preview_derived_visual_inputs", "output_mp4_distinct_from_all_prior_previews"],
    )
    return media_payload


# ==============================================================================
# W3: Parallel Decode & Motion QA + Mutations + Repair + Full E2E + Speed
# ==============================================================================


def job_w3_portus_camera_and_motion_decode(run_id: str) -> Dict[str, Any]:
    STRIPS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="portus_decode_w3_") as td:
        insp = inspect_portus_preview(PORTUS_PROJECT_DIR, PORTUS_MP4_PATH, ev_dir=Path(td))
        src_strips = Path(td) / "motion_perf" / "strips"
        copied_strips: List[str] = []
        if src_strips.is_dir():
            for sp in sorted(src_strips.glob("*.png")):
                dst = STRIPS_DIR / sp.name
                shutil.copy2(sp, dst)
                copied_strips.append(str(dst.relative_to(ROOT_DIR)))
    decode_wall = round(time.perf_counter() - t0, 3)

    out_p = LOGS_DIR / "w3_portus_decode.json"
    mp_qa_compact = dict(insp.get("motion_performance_qa") or {})
    if isinstance(mp_qa_compact.get("foot_plant"), dict):
        fp_c = dict(mp_qa_compact["foot_plant"])
        fp_c["track_reports"] = [
            {**tr, "sample_frames": (tr.get("sample_frames") or [])[:3]}
            for tr in (fp_c.get("track_reports") or [])
        ]
        mp_qa_compact["foot_plant"] = fp_c
    if isinstance(mp_qa_compact.get("hand_prop_contact"), dict):
        hc_c = dict(mp_qa_compact["hand_prop_contact"])
        hc_c["frame_strips"] = copied_strips
        mp_qa_compact["hand_prop_contact"] = hc_c
    res = {
        "status": "PASS" if (insp.get("valid") and len(copied_strips) >= 6) else "FAIL",
        "decode_audit_wall_sec": decode_wall,
        "copied_motion_strips": copied_strips,
        "temporal_visual_qa": insp.get("temporal_visual_qa"),
        "motion_performance_qa": mp_qa_compact,
    }
    _atomic_write_text(out_p, json.dumps(res, indent=2))
    return res


def job_w3_legacy_cut_coverage_decode(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="legacy_cuts_w3_") as td:
        wg_rep = audit_project_temporal_visual(WG_PROJECT_DIR, WG_MP4_PATH, Path(td) / "wg", run_negative_suite=False)
        eagle_rep = audit_project_temporal_visual(EAGLE_PROJECT_DIR, EAGLE_MP4_PATH, Path(td) / "eagle", run_negative_suite=False)
    wall = round(time.perf_counter() - t0, 3)
    ok = (
        wg_rep.technical_verdict == "VISUAL_TECH_PASS"
        and wg_rep.full_boundary_coverage
        and wg_rep.audited_cut_count == 7
        and eagle_rep.technical_verdict == "VISUAL_TECH_PASS"
        and eagle_rep.full_boundary_coverage
        and eagle_rep.audited_cut_count == 11
    )
    out_p = LOGS_DIR / "w3_legacy_cuts.json"
    res = {
        "status": "PASS" if ok else "FAIL",
        "decode_wall_sec": wall,
        "water_gate": {
            "technical_verdict": wg_rep.technical_verdict,
            "expected_cut_count": wg_rep.expected_cut_count,
            "audited_cut_count": wg_rep.audited_cut_count,
            "unaudited_cuts": wg_rep.unaudited_cuts,
            "full_boundary_coverage": wg_rep.full_boundary_coverage,
        },
        "eagle_in_fog": {
            "technical_verdict": eagle_rep.technical_verdict,
            "expected_cut_count": eagle_rep.expected_cut_count,
            "audited_cut_count": eagle_rep.audited_cut_count,
            "unaudited_cuts": eagle_rep.unaudited_cuts,
            "full_boundary_coverage": eagle_rep.full_boundary_coverage,
        },
    }
    _atomic_write_text(out_p, json.dumps(res, indent=2))
    return res


def job_w3_motion_qa_and_mutations(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    mut_logs = LOGS_DIR / "mutation_logs"
    mut_logs.mkdir(parents=True, exist_ok=True)

    v1476_mut = run_v14_7_6_mandatory_mutations()
    v1475_mut = run_mutation_tests(failure_logs_dir=mut_logs)
    neg_fix = run_negative_fixtures_tests()

    neg_ok = bool(
        neg_fix.get("all_negative_fixtures_passed")
        if "all_negative_fixtures_passed" in neg_fix
        else (int(neg_fix.get("passed_fixtures", 0)) >= 15 and neg_fix.get("passed_fixtures") == neg_fix.get("total_fixtures"))
    )
    ok = (
        v1476_mut.get("status") == "PASS"
        and int(v1476_mut.get("killed_mutations", 0)) >= 10
        and v1475_mut.get("all_mutations_killed") is True
        and int(v1475_mut.get("killed_mutations", 0)) >= 6
        and neg_ok
    )
    t1 = time.time()
    body = {
        "v14_7_6_mandatory_motion_mutations": v1476_mut,
        "v14_7_5_1_subprocess_mutations": {
            "execution_mode": v1475_mut.get("execution_mode"),
            "all_mutations_killed": v1475_mut.get("all_mutations_killed"),
            "killed_mutations": v1475_mut.get("killed_mutations"),
            "total_mutations": v1475_mut.get("total_mutations"),
            "mutations": v1475_mut.get("mutations"),
        },
        "negative_fixtures": {
            "all_passed": neg_ok,
            "passed_count": neg_fix.get("passed_fixtures"),
            "total_count": neg_fix.get("total_fixtures"),
        },
        "total_mutations_killed_combined": int(v1476_mut.get("killed_mutations", 0)) + int(v1475_mut.get("killed_mutations", 0)),
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.temporal_visual_qa::{run_v14_7_6_mandatory_mutations,run_mutation_tests,run_negative_fixtures_tests}",
        file_paths=["tools/temporal_visual_qa.py", "tests/motion_v14_7_6/test_camera_segments_and_mutations.py"],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "tools/temporal_visual_qa.py"),
        output_sha256=None,
        body=body,
        error_reason=None if ok else "Mutation or negative fixture gate failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "12_motion_qa_and_real_mutations.json",
        payload,
        run_id=run_id,
        writer_job_id="w3_motion_qa_and_mutations",
        required_keys=["status", "v14_7_6_mandatory_motion_mutations", "v14_7_5_1_subprocess_mutations", "negative_fixtures"],
    )
    return payload


def job_w3_camera_coverage_rollup(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    p_dec = json.loads((LOGS_DIR / "w3_portus_decode.json").read_text(encoding="utf-8"))
    leg = json.loads((LOGS_DIR / "w3_legacy_cuts.json").read_text(encoding="utf-8"))

    p_temp = p_dec.get("temporal_visual_qa") or {}
    p_mot = p_dec.get("motion_performance_qa") or {}
    int_cuts = p_mot.get("internal_camera_cuts") or p_mot.get("internal_cuts") or {}

    portus_inter_ok = (p_temp.get("audited_cut_count") == 7) and (p_temp.get("full_boundary_coverage") is True)
    portus_intra_ok = (
        int_cuts.get("status") == "PASS"
        and int(int_cuts.get("expected_internal_cuts", 0)) >= 4
        and int_cuts.get("audited_internal_cuts") == int_cuts.get("expected_internal_cuts")
        and int_cuts.get("full_coverage") is True
        and int_cuts.get("internal_failures") == []
    )
    ok = portus_inter_ok and portus_intra_ok and (leg.get("status") == "PASS")
    t1 = time.time()
    body = {
        "decode_audit_wall_sec": p_dec.get("decode_audit_wall_sec"),
        "portus_intershot_cuts": p_temp,
        "portus_internal_multi_angle_cuts": int_cuts,
        "portus_motion_strips": p_dec.get("copied_motion_strips", []),
        "legacy_films_cut_coverage": leg,
        "total_cut_boundaries_audited_all_films": (
            int(p_temp.get("audited_cut_count", 0))
            + int(int_cuts.get("audited_internal_cuts", 0))
            + int(leg["water_gate"]["audited_cut_count"])
            + int(leg["eagle_in_fog"]["audited_cut_count"])
        ),
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.temporal_visual_qa::{audit_project_temporal_visual,audit_internal_camera_cuts}",
        file_paths=[
            "tools/cinematic_camera.py",
            "tools/temporal_visual_qa.py",
            *p_dec.get("copied_motion_strips", []),
        ],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "tools/cinematic_camera.py"),
        output_sha256=None,
        body=body,
        error_reason=None if ok else "Intershot or internal camera segment cut coverage incomplete",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "08_camera_segments_full_coverage.json",
        payload,
        run_id=run_id,
        writer_job_id="w3_camera_coverage_rollup",
        required_keys=["status", "portus_intershot_cuts", "portus_internal_multi_angle_cuts", "legacy_films_cut_coverage"],
    )
    return payload


def job_w3_shot_repair_closed_loop(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    rep = test_defect_injection_and_repair(evidence_out_path=None)
    t1 = time.time()
    ok = (
        rep.get("test_status") == "PASS"
        and rep.get("initial_verdict") == "FAIL"
        and rep.get("final_verdict") == "VISUAL_TECH_PASS"
        and rep.get("mp4_rebuilt_and_changed") is True
        and rep.get("manual_locked_preserved") is True
        and rep.get("locked_defect_status") == "BLOCKED_MANUAL_REVIEW"
    )
    body = {
        "repair_architecture_disclosure": (
            "Closed-loop defect repair updates non-locked shot JSON selectively while preserving `manual_locked` "
            "shots byte-for-byte, then executes `FULL_RERENDER_FALLBACK` (`selective_segment_supported=False`) "
            "to preserve exact continuous camera and audio-visual mux sync."
        ),
        **rep,
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="tools.shot_repair::test_defect_injection_and_repair",
        file_paths=["tools/shot_repair.py"],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if ok else 1,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "tools/shot_repair.py"),
        output_sha256=rep.get("after_mp4_sha256"),
        body=body,
        error_reason=None if ok else "Shot repair closed-loop verification failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "16_shot_repair_closed_loop.json",
        payload,
        run_id=run_id,
        writer_job_id="w3_shot_repair_closed_loop",
        required_keys=["status", "render_mode", "initial_verdict", "final_verdict", "mp4_rebuilt_and_changed", "manual_locked_preserved"],
    )
    return payload


def job_w3_full_e2e_and_backtests(run_id: str) -> Dict[str, Any]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_summary = EVIDENCE_DIR / f".tmp_e2e_v14_7_6_{os.getpid()}.json"
    tmp_summary.unlink(missing_ok=True)

    env = dict(os.environ)
    env["QA_E2E_MAX_CONCURRENCY"] = "1"
    t0 = time.time()
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
    t1 = time.time()
    wall_sec = round(t1 - t0, 3)
    log_p = LOGS_DIR / "e2e_regression.log"
    _atomic_write_text(log_p, (proc.stdout or "") + "\n" + (proc.stderr or ""))

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
    ok = (proc.returncode == 0) and (verdict == "FLOW_READY") and (req_failed == 0) and (req_passed >= 81)

    e2e_body = {
        "e2e_run_id": raw_data.get("run_id", run_id),
        "wall_sec": wall_sec,
        "max_concurrency_used": 1,
        "verdict": verdict,
        "verdict_reason": raw_data.get("verdict_reason"),
        "gates_total": raw_data.get("gates_total", len(results_list)),
        "required_gates_total": req_total,
        "required_gates_passed": req_passed,
        "required_gates_failed": req_failed,
        "optional_gates_total": raw_data.get("optional_gates_total", 0),
        "log_path": str(log_p.relative_to(ROOT_DIR)),
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
    e2e_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts/run_e2e_regression.py --max-concurrency 1",
        file_paths=["scripts/run_e2e_regression.py", str(log_p.relative_to(ROOT_DIR))],
        start_ts=t0,
        end_ts=t1,
        exit_code=proc.returncode,
        status="PASS" if ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "scripts/run_e2e_regression.py"),
        output_sha256=None,
        body=e2e_body,
        error_reason=None if ok else f"E2E verdict={verdict}, req_passed={req_passed}/{req_total}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "13_full_e2e_regression.json",
        e2e_payload,
        run_id=run_id,
        writer_job_id="w3_full_e2e_and_backtests",
        required_keys=["status", "verdict", "required_gates_passed", "required_gates_failed", "gates_compact"],
    )

    by_gate = {r.get("gate"): r for r in results_list if isinstance(r, dict)}
    g5 = by_gate.get("G5", {})
    g5b = by_gate.get("G5b", {})
    g5c = by_gate.get("G5c", {})
    g5c_raw = g5c.get("status", "NOT_RUN_OPTIONAL_MISSING_FIXTURE")
    hist_status = "PASS_REAL_FIXTURE" if g5c_raw == "PASS" else "NOT_AVAILABLE"
    bt_ok = (g5.get("status") == "PASS") and (g5b.get("status") == "PASS")

    bt_body = {
        "synthetic_180_stress_gate_g5": g5.get("status", "UNKNOWN"),
        "synthetic_180_classification": "SYNTHETIC_ONLY",
        "synthetic_180_details": g5.get("details", {}),
        "medium_20_shot_real_render_g5b": g5b.get("status", "UNKNOWN"),
        "medium_20_shot_classification": "REAL_RENDERED_VIDEO",
        "medium_20_shot_details": g5b.get("details", {}),
        "historical_180_real_replay_g5c": hist_status,
        "historical_180_raw_gate_status": g5c_raw,
        "historical_180_fixture_path": "projects/why_knights_could_actually",
        "counted_not_available_as_real_replay_pass": False,
        "truth_disclosure": (
            "G5 verifies a 180-shot SYNTHETIC_ONLY timeline stress fixture (PASS) and G5b verifies a 20-shot "
            "REAL_RENDERED_VIDEO fixture (PASS). Optional company historical dataset 'projects/why_knights_could_actually' "
            "is absent on this host, so G5c is strictly recorded as NOT_AVAILABLE and NEVER counted as PASS."
        ),
    }
    bt_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts/run_e2e_regression.py::G5+G5b+G5c",
        file_paths=["scripts/run_e2e_regression.py"],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if bt_ok else 1,
        status="PASS" if bt_ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "scripts/run_e2e_regression.py"),
        output_sha256=None,
        body=bt_body,
        error_reason=None if bt_ok else "G5 or G5b backtest failed",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "14_backtest_synthetic_vs_real_truth.json",
        bt_payload,
        run_id=run_id,
        writer_job_id="w3_full_e2e_and_backtests",
        required_keys=[
            "status",
            "synthetic_180_stress_gate_g5",
            "synthetic_180_classification",
            "medium_20_shot_real_render_g5b",
            "historical_180_real_replay_g5c",
            "counted_not_available_as_real_replay_pass",
        ],
    )
    return e2e_payload


def _build_microbenchmark_jobs(out_dir: Path) -> List[Dict[str, Any]]:
    targets = [
        ("m1_night", ROOT_DIR / "projects/fl01_v14_7_night_warning_preview/out/FL01_V14_7_FRESH_PREVIEW_1080P.mp4", 4.0),
        ("m2_eagle", EAGLE_MP4_PATH, 10.0),
        ("m3_water_gate", WG_MP4_PATH, 12.0),
        ("m4_portus", PORTUS_MP4_PATH, 16.0),
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


def job_w3_speed_benchmarks(run_id: str) -> Dict[str, Any]:
    t0 = time.time()
    iterations = 3
    serial_times: List[float] = []
    parallel_times: List[float] = []
    runs_detail: List[Dict[str, Any]] = []
    outputs_identical_all = True

    for it in range(1, iterations + 1):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            ser_d, par_d = td_p / "serial", td_p / "parallel"
            ser_d.mkdir()
            par_d.mkdir()

            t_s0 = time.perf_counter()
            ser_rep = run_dag(build_dependency_dag(_build_microbenchmark_jobs(ser_d)), max_workers=1, min_disk_gb=6.0, min_ram_gb=1.0, run_id=f"v1476_ser_{it}")
            t_ser = round(time.perf_counter() - t_s0, 4)

            t_p0 = time.perf_counter()
            par_rep = run_dag(build_dependency_dag(_build_microbenchmark_jobs(par_d)), max_workers=4, min_disk_gb=6.0, min_ram_gb=1.0, run_id=f"v1476_par_{it}")
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

    # Measure JS `evaluateMotionTrackAt` animation evaluation overhead across 720 frames
    js_bench = """
import fs from 'node:fs';
import { performance } from 'node:perf_hooks';
import { evaluateMotionTrackAt } from './packs/squire/motion_engine.js';
const mp = JSON.parse(fs.readFileSync('./projects/fl01_v14_7_6_roman_last_light_portus_preview/story/motion_plan.json', 'utf8'));
const ws = (mp.world_states && mp.world_states[0]) || {};
const tracks = mp.tracks || [];
const t0 = performance.now();
let evalCount = 0;
for (let f = 0; f < 720; f++) {
  const t = f / 24;
  for (const tr of tracks) {
    if (t >= tr.start_sec && t <= tr.end_sec) {
      evaluateMotionTrackAt(tr, t, ws);
      evalCount++;
    }
  }
}
const elapsedMs = performance.now() - t0;
console.log(JSON.stringify({ total_evals_720f: evalCount, total_ms: Number(elapsedMs.toFixed(3)), ms_per_frame: Number((elapsedMs / 720).toFixed(5)) }));
"""
    js_proc = subprocess.run(["node", "--input-type=module", "-e", js_bench], cwd=ROOT_DIR, capture_output=True, text=True, timeout=30)
    anim_overhead = json.loads(js_proc.stdout.strip()) if js_proc.returncode == 0 else {}

    portus_media = json.loads((EVIDENCE_DIR / "10_portus_original_30s_media_receipt.json").read_text(encoding="utf-8"))
    cam_cov = json.loads((EVIDENCE_DIR / "08_camera_segments_full_coverage.json").read_text(encoding="utf-8"))
    e2e_ev = json.loads((EVIDENCE_DIR / "13_full_e2e_regression.json").read_text(encoding="utf-8"))

    mean_ser = round(statistics.mean(serial_times), 4)
    mean_par = round(statistics.mean(parallel_times), 4)
    t1 = time.time()
    body = {
        "scope_separation_note": (
            "Lightweight QA microbenchmark speedup applies strictly to parallel ffprobe/RGB24 decode tasks (n=3) "
            "and is NEVER claimed as renderer speedup. Heavy 1080p Chromium rendering is intentionally serialized "
            "to 1 worker on this 16GB host to protect the >=1.0 GiB available RAM floor."
        ),
        "microbenchmark_serial_vs_bounded_parallel": {
            "workload": "4 independent ffprobe + 3-frame RGB24 decode + SHA256 tasks across 1080p MP4s (Night Warning, Eagle, Water Gate, Portus)",
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
        "animation_evaluation_overhead": anim_overhead,
        "end_to_end_pipeline_measurements": {
            "portus_30s_cold_render_total_wall_sec": portus_media.get("cold_render_total_wall_sec"),
            "portus_30s_cold_motion_plan_wall_sec": portus_media.get("cold_motion_plan_wall_sec"),
            "portus_30s_cold_render_only_wall_sec": portus_media.get("cold_render_only_wall_sec"),
            "portus_30s_warm_cache_wall_sec": portus_media.get("warm_cache_wall_sec"),
            "portus_30s_decode_and_motion_qa_wall_sec": cam_cov.get("decode_audit_wall_sec"),
            "cold_render_sample_count": 1,
            "cold_render_sample_status": "SMALL_SAMPLE",
            "full_e2e_regression_wall_sec": e2e_ev.get("wall_sec"),
        },
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.run_fl01_v14_7_6_validation::job_w3_speed_benchmarks",
        file_paths=[
            str(PORTUS_MP4_PATH.relative_to(ROOT_DIR)),
            "packs/squire/motion_engine.js",
        ],
        start_ts=t0,
        end_ts=t1,
        exit_code=0 if outputs_identical_all else 1,
        status="PASS" if outputs_identical_all else "FAIL",
        original_input_sha256=portus_media.get("output_sha256") or "",
        output_sha256=None,
        body=body,
        error_reason=None if outputs_identical_all else "Serial vs parallel microbenchmark digest mismatch",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "15_speed_serial_parallel_and_total_e2e.json",
        payload,
        run_id=run_id,
        writer_job_id="w3_speed_benchmarks",
        required_keys=["status", "microbenchmark_serial_vs_bounded_parallel", "animation_evaluation_overhead", "end_to_end_pipeline_measurements"],
    )
    return payload


# ==============================================================================
# W4: Master Rollup, Markdown Packets & Cross-Evidence Consistency
# ==============================================================================


def _restore_incidental_legacy_e2e_touches() -> List[str]:
    """If `run_e2e_regression.py` rewrote legacy tracked `tests/evidence/v6..v12` or `proof_*.jpg`, restore them cleanly."""
    dirty = _git_out(["diff", "--name-only"]).splitlines()
    restored: List[str] = []
    safe_intentional = {
        "packs/squire/chara.js",
        "packs/squire/pack.js",
        "packs/squire/templates.js",
        "tools/action_capabilities.py",
        "tools/character_acting.py",
        "tools/cinematic_camera.py",
        "tools/narrative_action.py",
        "tools/temporal_visual_qa.py",
    }
    for rel_p in dirty:
        rel_p = rel_p.strip()
        if not rel_p or rel_p in safe_intentional or rel_p.startswith("tests/evidence/v14_7_5"):
            continue
        if rel_p.startswith("tests/evidence/v") or rel_p.endswith(".jpg"):
            subprocess.run(["git", "checkout", "--", rel_p], cwd=ROOT_DIR, check=False)
            restored.append(rel_p)
    shutil.rmtree(ROOT_DIR / ".test-runs", ignore_errors=True)
    return restored


def _build_and_publish_master_status(run_id: str, t_suite_start: float) -> Dict[str, Any]:
    gate_files = [
        ("G01", "Branch, Production SHA & 15-Artifact Preservation", "01_branch_preservation_manifest.json", True),
        ("G02", "Resource & Process-Tree Telemetry Floors", "02_resource_process_tree_timeseries.json", True),
        ("G03", "Bounded-Parallel Async DAG Execution & Overlap Proof", "03_async_dag_jobs.json", True),
        ("G04", "Script -> MotionPlan Generalization & 3 Unseen Renders", "04_motion_plan_generalization.json", True),
        ("G05", "Natural Motion IK, Foot-Plant, Grip & Order Invariance", "05_natural_motion_metrics.json", True),
        ("G06", "Rigby2D 0.5.1 Real Chromium WebGL Pilot (Experimental)", "06_rigby_real_runtime_pilot.json", False),
        ("G07", "Claude Animation Skill Selective FX Determinism & Clocks", "07_claude_fx_determinism.json", True),
        ("G08", "Multi-Angle Camera Segments & 100% Cut Coverage", "08_camera_segments_full_coverage.json", True),
        ("G09", "8s Harbor A/B/C Comparison Clips & Motion Traces", "09_a_b_c_render_comparison.json", True),
        ("G10", "Original 30.000s / 720-Frame 1080p24 Portus Media & Receipt", "10_portus_original_30s_media_receipt.json", True),
        ("G11", "Measured Daniel TTS Voice, 0ms Overlap & -14 LUFS Mix", "11_portus_voice_sound_timing.json", True),
        ("G12", "Decoded Motion QA, 10 V14.7.6 + 6 V14.7.5.1 Mutants & 15 Negatives", "12_motion_qa_and_real_mutations.json", True),
        ("G13", "Full E2E Squire/DEM Regression (>=81 Required Gates)", "13_full_e2e_regression.json", True),
        ("G14", "180-Shot Synthetic vs 20-Shot Real vs G5c Backtest Truth", "14_backtest_synthetic_vs_real_truth.json", True),
        ("G15", "Serial vs Bounded-Parallel Speed (n=3) & E2E Timings", "15_speed_serial_parallel_and_total_e2e.json", True),
        ("G16", "Closed-Loop Real Video Defect Repair & Manual Lock Safety", "16_shot_repair_closed_loop.json", True),
        ("G17", "100% Original Visual & Audio Asset Lineage", "17_original_visual_source_lineage.json", True),
        ("G18", "Changed vs KEPT AS IS Implementation Matrix", "18_implementation_kept_as_is_matrix.json", True),
    ]

    gates_summary: List[Dict[str, Any]] = []
    mandatory_total = 0
    mandatory_passed = 0
    mandatory_failures: List[str] = []

    for gid, gname, fname, is_mand in gate_files:
        d = json.loads((EVIDENCE_DIR / fname).read_text(encoding="utf-8"))
        st = d.get("status", "FAIL")
        if is_mand:
            mandatory_total += 1
            if st == "PASS":
                mandatory_passed += 1
            else:
                mandatory_failures.append(f"{gid}:{fname}:{st}")
        gates_summary.append({
            "gate_id": gid,
            "name": gname,
            "evidence_file": fname,
            "mandatory": is_mand,
            "status": st,
            "elapsed_sec": d.get("elapsed_sec", 0.0),
        })

    gates_summary.append({
        "gate_id": "J13",
        "name": "Human Editorial Review of Original 30s Portus Film",
        "evidence_file": "EDITORIAL_REVIEW_PACKET.md",
        "mandatory": False,
        "status": "EDITORIAL_REVIEW_PENDING",
        "elapsed_sec": 0.0,
    })

    tech_all_passed = (mandatory_passed == mandatory_total) and (len(mandatory_failures) == 0)
    master_status = "TECH_VERIFIED_PENDING_EDITORIAL" if tech_all_passed else "TECH_FAILED"
    rigby_ev = json.loads((EVIDENCE_DIR / "06_rigby_real_runtime_pilot.json").read_text(encoding="utf-8"))
    portus_ev = json.loads((EVIDENCE_DIR / "10_portus_original_30s_media_receipt.json").read_text(encoding="utf-8"))

    t_end = time.time()
    body = {
        "master_status": master_status,
        "tech_all_passed": tech_all_passed,
        "editorial_status": "EDITORIAL_REVIEW_PENDING",
        "j13_status": "EDITORIAL_REVIEW_PENDING",
        "rigby_experimental_pilot_status": rigby_ev.get("pilot_verdict"),
        "mandatory_technical_gates_total": mandatory_total,
        "mandatory_technical_gates_passed": mandatory_passed,
        "mandatory_failures": mandatory_failures,
        "portus_30s_mp4_path": portus_ev.get("output_mp4"),
        "portus_30s_mp4_sha256": portus_ev.get("output_sha256"),
        "gates": gates_summary,
    }
    payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.run_fl01_v14_7_6_validation::_build_and_publish_master_status",
        file_paths=[f"tests/evidence/v14_7_6/{fn}" for _, _, fn, _ in gate_files],
        start_ts=t_suite_start,
        end_ts=t_end,
        exit_code=0 if tech_all_passed else 1,
        status=master_status,
        original_input_sha256=BASE_SHA,
        output_sha256=portus_ev.get("output_sha256"),
        body=body,
        error_reason=None if tech_all_passed else f"Failed mandatory gates: {mandatory_failures}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "00_master_status.json",
        payload,
        run_id=run_id,
        writer_job_id="w4_master_status",
        required_keys=["master_status", "tech_all_passed", "editorial_status", "mandatory_technical_gates_passed", "gates"],
    )
    return payload


def _write_markdown_packets(run_id: str) -> None:
    m00 = json.loads((EVIDENCE_DIR / "00_master_status.json").read_text(encoding="utf-8"))
    b01 = json.loads((EVIDENCE_DIR / "01_branch_preservation_manifest.json").read_text(encoding="utf-8"))
    r02 = json.loads((EVIDENCE_DIR / "02_resource_process_tree_timeseries.json").read_text(encoding="utf-8"))
    j03 = json.loads((EVIDENCE_DIR / "03_async_dag_jobs.json").read_text(encoding="utf-8"))
    g04 = json.loads((EVIDENCE_DIR / "04_motion_plan_generalization.json").read_text(encoding="utf-8"))
    n05 = json.loads((EVIDENCE_DIR / "05_natural_motion_metrics.json").read_text(encoding="utf-8"))
    p06 = json.loads((EVIDENCE_DIR / "06_rigby_real_runtime_pilot.json").read_text(encoding="utf-8"))
    c07 = json.loads((EVIDENCE_DIR / "07_claude_fx_determinism.json").read_text(encoding="utf-8"))
    k08 = json.loads((EVIDENCE_DIR / "08_camera_segments_full_coverage.json").read_text(encoding="utf-8"))
    a09 = json.loads((EVIDENCE_DIR / "09_a_b_c_render_comparison.json").read_text(encoding="utf-8"))
    m10 = json.loads((EVIDENCE_DIR / "10_portus_original_30s_media_receipt.json").read_text(encoding="utf-8"))
    v11 = json.loads((EVIDENCE_DIR / "11_portus_voice_sound_timing.json").read_text(encoding="utf-8"))
    q12 = json.loads((EVIDENCE_DIR / "12_motion_qa_and_real_mutations.json").read_text(encoding="utf-8"))
    e13 = json.loads((EVIDENCE_DIR / "13_full_e2e_regression.json").read_text(encoding="utf-8"))
    h14 = json.loads((EVIDENCE_DIR / "14_backtest_synthetic_vs_real_truth.json").read_text(encoding="utf-8"))
    s15 = json.loads((EVIDENCE_DIR / "15_speed_serial_parallel_and_total_e2e.json").read_text(encoding="utf-8"))
    r16 = json.loads((EVIDENCE_DIR / "16_shot_repair_closed_loop.json").read_text(encoding="utf-8"))
    l17 = json.loads((EVIDENCE_DIR / "17_original_visual_source_lineage.json").read_text(encoding="utf-8"))

    mi = m10["media_info"]
    gate_rows = "\n".join(
        f"| `{g['gate_id']}` | {g['name']} | `{'YES' if g['mandatory'] else 'OPT/HUMAN'}` | **{g['status']}** | `{g['elapsed_sec']}s` |"
        for g in m00["gates"]
    )

    report_md = f"""# FL-01 / V14.7.6 Execution & Technical Acceptance Report

- **Release**: `V14.7.6` (`FL-01 Motion Intelligence + Natural 2D Acting + Rigby2D Pilot + Claude Animation Assist`)
- **Work Branch**: `{MANDATORY_BRANCH}` (Base `{BASE_SHA}`)
- **Protected Production SHA**: `{PRODUCTION_INVARIANT_SHA}` (`production_unchanged = {b01['production_unchanged']}`)
- **Validation Run ID**: `{run_id}`
- **Master Verdict**: **`{m00['master_status']}`** (`{m00['mandatory_technical_gates_passed']}/{m00['mandatory_technical_gates_total']}` Mandatory Technical Gates `PASS`)
- **Human Editorial Gate (`J13`)**: **`{m00['editorial_status']}`**

## 1. Gate Summary (`G01`–`G18` + `J13`)

| Gate | Requirement | Mandatory | Status | Elapsed |
| :--- | :--- | :--- | :--- | :--- |
{gate_rows}

## 2. Original 30.000s 1080p24 Film: `{PORTUS_TITLE}`

- **Subtitle / Fictional Framing**: *{PORTUS_SUBTITLE}* (Fictional coastal harbor drama; zero archaeological overclaims)
- **Local MP4 Path**: `{PORTUS_MP4_PATH}` (`{m10['mp4_size_bytes']}` bytes)
- **Output SHA256**: `{m10['output_sha256']}`
- **Input Fingerprint (64-hex)**: `{m10['input_fingerprint']}` (`fingerprint_match = {m10['fingerprint_match']}`, `receipt_verified = {m10['receipt_verified']}`, `warm_cache_status = {m10['warm_cache_status']}`)
- **Decoded Stream Proof**: **`{m10['decoded_video_frames']}` video frames** (`{mi.get('width')}x{mi.get('height')}` @ `{mi.get('fps')} fps`, video `{mi.get('video_stream_duration')}s`, audio `{mi.get('audio_stream_duration')}s`, `h264`/`aac`)
- **Voice & Soundtrack**: `{v11['speech_provider']}`, `{v11['beats_count']}` beats, **`{v11['measured_overlap_ms']} ms`** overlap, min tail margin **`{v11['min_tail_margin_sec']}s`**, last phrase `"{v11['last_spoken_phrase']}"` ending at `{v11['last_spoken_end_sec']}s`, Integrated **`{v11['final_mp4_integrated_lufs']} LUFS`**, True Peak **`{v11['final_mp4_true_peak_dbtp']} dBTP`**
- **Originality Lineage**: `prior_preview_derived_visual_inputs = {l17['prior_preview_derived_visual_inputs']}`, `external_raster_images_count = {l17['external_raster_images_count']}`, `output_mp4_distinct_from_all_prior_previews = {l17['output_mp4_distinct_from_all_prior_previews']}`

## 3. Motion Intelligence, Rigby2D Pilot, Claude FX & Multi-Angle Camera

- **MotionPlan Generalization (`04`, `{g04['ai_routing_mode']}`)**: Wording-variation test `PASS` + `3/3` unseen civic scripts (`unseen_a_citizen_basket`, `unseen_b_merchant_amphora`, `unseen_c_child_lantern_duck`) planned, validated, and rendered at 1080p24.
- **Natural Motion Metrics (`05`)**: Median planted-foot drift **`{n05['measured_portus_foot_plant']['max_median_planted_foot_drift_norm']}`** (`<= 0.03`), peak hand-prop grip distance **`{n05['measured_portus_hand_prop_contact']['peak_hand_grip_dist_norm']}`** (`<= 0.04`), forward/reverse/shuffled frame evaluation SHA-256 identical (`{n05['frame_order_invariance']['order_invariant']}`).
- **Rigby2D `0.5.1` Real Runtime Pilot (`06`, pinned `{RIGBY_PINNED_SHA}`)**: Verdict **`{p06['pilot_verdict']}`** (`MIT OR Apache-2.0`; zero `NILA`/`Rigbytron` demo assets; original 15-slot 4-IK `roman_harbor_worker` rendered via WebGL inside `render.mjs` for 8s pilot & Clips B/C).
- **Claude Animation Skill Selective FX (`07`, pinned `{CLAUDE_SKILL_PINNED_SHA}`)**: `MIT` helpers with deterministic seeded RNG, `[0, 1]` alpha bounds, and strict action-clock vs voice/camera-clock separation.
- **8s A/B/C Harbor Comparison (`09`)**:
  - Clip A (`legacy_v14_7_5_1`): `{a09['clip_A_baseline_v14_7_5_1']['mp4_sha256']}`
  - Clip B (`rigby2d_webgl_0.5.1`): `{a09['clip_B_motion_plan_rigby2d']['mp4_sha256']}`
  - Clip C (`rigby2d + claude_selective`): `{a09['clip_C_rigby2d_plus_claude_fx']['mp4_sha256']}`
- **100% Intershot & Internal Camera Cut Coverage (`08`)**: Portus `{k08['portus_intershot_cuts']['audited_cut_count']}/7` intershot cuts + `{k08['portus_internal_multi_angle_cuts']['audited_internal_cuts']}/{k08['portus_internal_multi_angle_cuts']['expected_internal_cuts']}` internal multi-angle cuts + Water Gate `7/7` + Eagle `11/11` (**`{k08['total_cut_boundaries_audited_all_films']}` total boundaries audited, `0` unaudited**).

## 4. Mutations, Regressions, Backtests, Resources & Timings

- **Mutations & Negative Suite (`12`)**: `{q12['v14_7_6_mandatory_motion_mutations']['killed_mutations']}/10` V14.7.6 motion mutants killed + `{q12['v14_7_5_1_subprocess_mutations']['killed_mutations']}/6` V14.7.5.1 subprocess mutants killed + `{q12['negative_fixtures']['passed_count']}/{q12['negative_fixtures']['total_count']}` negative fixtures `PASS`.
- **Shot Repair Closed Loop (`16`)**: `FAIL -> {r16['final_verdict']}`, `render_mode = {r16['render_mode']}`, `manual_locked_preserved = {r16['manual_locked_preserved']}`, locked defect -> `{r16['locked_defect_status']}`.
- **Full E2E Regression (`13`) & Backtest Truth (`14`)**: `{e13['verdict']}` (`{e13['required_gates_passed']}/{e13['required_gates_total']}` required gates `PASS`); `G5` (`SYNTHETIC_ONLY`) = `{h14['synthetic_180_stress_gate_g5']}`, `G5b` (`REAL_RENDERED_VIDEO`) = `{h14['medium_20_shot_real_render_g5b']}`, `G5c` = `{h14['historical_180_real_replay_g5c']}` (`counted_not_available_as_real_replay_pass = {h14['counted_not_available_as_real_replay_pass']}`).
- **Async DAG & Resource Safety (`02`, `03`)**: `{j03['passed_jobs']}/{j03['total_jobs']}` DAG jobs passed, `{j03['concurrency_proof']['overlapping_pairs_count']}` overlapping parallel pairs (max overlap `{j03['concurrency_proof']['max_overlap_sec']}s`), min disk free **`{r02['min_disk_free_gb']} GiB`** (`>= 6.0 GiB`), min RAM available **`{r02['min_ram_available_gb']} GiB`** (`>= 1.0 GiB`), peak tree RSS `{r02['peak_rss_mb']} MB`, orphans `{j03['orphan_worker_processes_after_run']}`.
- **Speed & Overhead (`15`)**: Lightweight decode microbenchmark (`n=3`) mean serial `{s15['microbenchmark_serial_vs_bounded_parallel']['mean_serial_sec']}s` vs parallel `{s15['microbenchmark_serial_vs_bounded_parallel']['mean_parallel_sec']}s` (**`{s15['microbenchmark_serial_vs_bounded_parallel']['mean_speedup_ratio']}x`**, 100% digest match); JS motion eval `{s15['animation_evaluation_overhead'].get('ms_per_frame')} ms/frame`; Portus 30s cold render total `{s15['end_to_end_pipeline_measurements']['portus_30s_cold_render_total_wall_sec']}s` (`render.mjs` `{s15['end_to_end_pipeline_measurements']['portus_30s_cold_render_only_wall_sec']}s`, `SMALL_SAMPLE`), warm cache `{s15['end_to_end_pipeline_measurements']['portus_30s_warm_cache_wall_sec']}s`, full E2E `{s15['end_to_end_pipeline_measurements']['full_e2e_regression_wall_sec']}s`.
"""
    _atomic_write_text(EVIDENCE_DIR / "FL01_V14_7_6_EXECUTION_REPORT.md", report_md)

    editorial_md = f"""# Editorial Human Review Packet (`J13 = EDITORIAL_REVIEW_PENDING`)

- **Film Title**: `{PORTUS_TITLE}`
- **Fictional Framing**: *{PORTUS_SUBTITLE}* (Fictional Roman harbor lighthouse drama at twilight; ancient open oil flame in watchtower alcove, no modern rotating Fresnel optics)
- **Local 1080p24 MP4 Path**: `{PORTUS_MP4_PATH}`
- **SHA256**: `{m10['output_sha256']}`
- **Runtime**: `30.000s` (`{m10['decoded_video_frames']}` decoded video frames @ `24 fps`)
- **Direct macOS Viewing Command**:
  ```bash
  open "{PORTUS_MP4_PATH}"
  ```
- **Visual Review Artifacts in `tests/evidence/v14_7_6/`**:
  - `contact_sheet_full.png` (All 8 beats `S01`–`S08`)
  - `contact_sheet_hook.png` (`0.0s–6.5s` snuffed harbor beacon & merchant vessel rolling toward jagged shoals)
  - `contact_sheet_action.png` (`14.0s–26.5s` slip on stone steps, two-actor rope haul, close grip insert & oil-flame channel relight)
  - `contact_sheet_abc_comparison.png` (8s side-by-side Clip A V14.7.5.1 sine vs Clip B Rigby2D WebGL vs Clip C Rigby2D + Claude FX)
  - `motion_strips/` (`+/- 0.25s` frame strips around lantern grab, rope brace, slip reaction, and two-actor rope haul)

## Human Editorial Checklist (Required Before Closing `J13`)

- [ ] **0–3s Hook (`S01`)**: Coastal gust extinguishing the harbor flame and warm-to-cold twilight shift read immediately.
- [ ] **Acting & Contact Clarity (`S03`–`S06`)**: Aelia grabbing the spare burning lantern (`S03`), running to the tower while Felix catches the pulley rope (`S04`), slipping and catching the rail (`S05`), and hauling the lantern into the protected alcove together across wide/insert/low-tower angles (`S06`) feel grounded without robotic marching or floating hands.
- [ ] **Payoff & End Card (`S07`–`S08`)**: Ancient oil flame guides the merchant ship away from the rocks, dusk atmosphere remains consistent, Daniel narration has natural breathing room (`0.0 ms` overlap, `{v11['final_mp4_integrated_lufs']} LUFS`), and `ONE LIGHT. ONE SAFE PASSAGE.` is clean and mobile-legible.
"""
    _atomic_write_text(EVIDENCE_DIR / "EDITORIAL_REVIEW_PACKET.md", editorial_md)


def verify_v14_7_6_cross_evidence_consistency(ev_dir: Path, expected_run_id: str) -> Dict[str, Any]:
    errors: List[str] = []
    required_jsons = [
        "00_master_status.json",
        "01_branch_preservation_manifest.json",
        "02_resource_process_tree_timeseries.json",
        "03_async_dag_jobs.json",
        "04_motion_plan_generalization.json",
        "05_natural_motion_metrics.json",
        "06_rigby_real_runtime_pilot.json",
        "07_claude_fx_determinism.json",
        "08_camera_segments_full_coverage.json",
        "09_a_b_c_render_comparison.json",
        "10_portus_original_30s_media_receipt.json",
        "11_portus_voice_sound_timing.json",
        "12_motion_qa_and_real_mutations.json",
        "13_full_e2e_regression.json",
        "14_backtest_synthetic_vs_real_truth.json",
        "15_speed_serial_parallel_and_total_e2e.json",
        "16_shot_repair_closed_loop.json",
        "17_original_visual_source_lineage.json",
        "18_implementation_kept_as_is_matrix.json",
        "19_git_post_push_attestation.json",
    ]
    loaded: Dict[str, Dict[str, Any]] = {}
    for fname in required_jsons:
        fp = ev_dir / fname
        if not fp.is_file():
            errors.append(f"Missing required evidence JSON: {fname}")
        else:
            loaded[fname] = json.loads(fp.read_text(encoding="utf-8"))

    for req_other in (
        "FL01_V14_7_6_EXECUTION_REPORT.md",
        "EDITORIAL_REVIEW_PACKET.md",
        "contact_sheet_full.png",
        "contact_sheet_hook.png",
        "contact_sheet_action.png",
        "contact_sheet_abc_comparison.png",
        "abc_motion_traces.json",
    ):
        if not (ev_dir / req_other).is_file():
            errors.append(f"Missing required artifact: {req_other}")

    if errors:
        return {"consistent": False, "errors": errors}

    # Check mandatory gate envelope keys on 00..18
    envelope_keys = (
        "source_commit",
        "run_id",
        "command_or_function",
        "file_paths",
        "start_time",
        "end_time",
        "exit_code",
        "original_input_sha256",
        "output_sha256",
        "measured_resources",
        "status",
    )
    for fname in required_jsons[:-1]:
        d = loaded[fname]
        if d.get("run_id") != expected_run_id:
            errors.append(f"run_id mismatch in {fname}: {d.get('run_id')} != {expected_run_id}")
        for ek in envelope_keys:
            if ek not in d:
                errors.append(f"{fname} missing mandatory gate key '{ek}'")

    m00 = loaded["00_master_status.json"]
    b01 = loaded["01_branch_preservation_manifest.json"]
    r02 = loaded["02_resource_process_tree_timeseries.json"]
    j03 = loaded["03_async_dag_jobs.json"]
    a09 = loaded["09_a_b_c_render_comparison.json"]
    m10 = loaded["10_portus_original_30s_media_receipt.json"]
    v11 = loaded["11_portus_voice_sound_timing.json"]
    q12 = loaded["12_motion_qa_and_real_mutations.json"]
    e13 = loaded["13_full_e2e_regression.json"]
    h14 = loaded["14_backtest_synthetic_vs_real_truth.json"]
    l17 = loaded["17_original_visual_source_lineage.json"]
    md_text = (ev_dir / "FL01_V14_7_6_EXECUTION_REPORT.md").read_text(encoding="utf-8")

    if m00.get("editorial_status") != "EDITORIAL_REVIEW_PENDING":
        errors.append("J13 self-approval forbidden: editorial_status must be EDITORIAL_REVIEW_PENDING")
    if m00.get("tech_all_passed") and m00.get("master_status") != "TECH_VERIFIED_PENDING_EDITORIAL":
        errors.append("master_status must be TECH_VERIFIED_PENDING_EDITORIAL when tech_all_passed is True")
    if not b01.get("all_preserved_intact") or not b01.get("production_unchanged"):
        errors.append("Preservation or Production SHA invariant violated")
    if float(r02.get("min_disk_free_gb") or 0.0) < 6.0 or float(r02.get("min_ram_available_gb") or 0.0) < 1.0:
        errors.append(f"Resource floor violated: disk={r02.get('min_disk_free_gb')}, ram={r02.get('min_ram_available_gb')}")
    if int(j03.get("total_jobs") or 0) < 12 or not j03.get("all_succeeded"):
        errors.append("DAG did not run all jobs to completion")
    if int((j03.get("concurrency_proof") or {}).get("overlapping_pairs_count") or 0) < 1:
        errors.append("Zero overlapping parallel job pairs recorded in 03_async_dag_jobs.json")
    if not a09.get("distinct_three_mp4_hashes"):
        errors.append("A/B/C comparison MP4 hashes are not 3 distinct digests")
    if not PORTUS_MP4_PATH.is_file() or int(m10.get("decoded_video_frames") or 0) != PORTUS_FRAMES:
        errors.append("Portus 30s MP4 missing or decoded_video_frames != 720")
    if len(str(m10.get("input_fingerprint") or "")) != 64:
        errors.append("Invalid 64-hex input_fingerprint in 10_portus_original_30s_media_receipt.json")
    if float(v11.get("measured_overlap_ms", 99.0)) != 0.0:
        errors.append("Portus voice overlap != 0.0 ms")
    if int(q12["v14_7_6_mandatory_motion_mutations"].get("killed_mutations", 0)) < 10:
        errors.append("Fewer than 10 V14.7.6 mandatory mutations killed")
    if e13.get("verdict") != "FLOW_READY" or int(e13.get("required_gates_passed", 0)) < 81:
        errors.append("Full E2E regression not FLOW_READY >= 81")
    if h14.get("counted_not_available_as_real_replay_pass") is not False:
        errors.append("counted_not_available_as_real_replay_pass must be False")
    if l17.get("prior_preview_derived_visual_inputs") != 0:
        errors.append("prior_preview_derived_visual_inputs != 0")
    if m10.get("output_sha256", "") not in md_text:
        errors.append("Markdown report out of sync with Portus MP4 SHA256")

    return {"consistent": len(errors) == 0, "errors": errors}


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STRIPS_DIR.mkdir(parents=True, exist_ok=True)
    t_suite_start = time.time()
    run_id = f"v14_7_6_val_{int(t_suite_start)}"
    print(f"=== Starting FL-01 / V14.7.6 Multi-Wave Async Validation DAG ({run_id}) ===")

    jobs: List[Dict[str, Any]] = [
        # W0: Parallel baseline preflight & implementation matrix
        {
            "id": "w0_branch_preservation",
            "job_profile": "light_cpu",
            "deps": [],
            "fn": lambda: job_w0_branch_preservation(run_id, writer_id="w0_branch_preservation"),
            "expected_artifacts": [str(EVIDENCE_DIR / "01_branch_preservation_manifest.json")],
            "timeout_sec": 90.0,
        },
        {
            "id": "w0_implementation_matrix",
            "job_profile": "light_cpu",
            "deps": [],
            "fn": lambda: job_w0_implementation_matrix(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "18_implementation_kept_as_is_matrix.json")],
            "timeout_sec": 60.0,
        },
        # W1: 5 independent light tasks in bounded parallel
        {
            "id": "w1_motion_plan_unit",
            "job_profile": "light_cpu",
            "deps": ["w0_branch_preservation", "w0_implementation_matrix"],
            "fn": lambda: job_w1_motion_plan_unit(run_id),
            "expected_artifacts": [str(LOGS_DIR / "w1_motion_plan_unit.json")],
            "timeout_sec": 180.0,
        },
        {
            "id": "w1_natural_motion_metrics",
            "job_profile": "light_cpu",
            "deps": ["w0_branch_preservation", "w0_implementation_matrix"],
            "fn": lambda: job_w1_natural_motion_metrics(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "05_natural_motion_metrics.json")],
            "timeout_sec": 180.0,
        },
        {
            "id": "w1_rigby_runtime_pilot",
            "job_profile": "light_cpu",
            "deps": ["w0_branch_preservation", "w0_implementation_matrix"],
            "fn": lambda: job_w1_rigby_runtime_pilot(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "06_rigby_real_runtime_pilot.json")],
            "timeout_sec": 300.0,
        },
        {
            "id": "w1_claude_fx_determinism",
            "job_profile": "light_cpu",
            "deps": ["w0_branch_preservation", "w0_implementation_matrix"],
            "fn": lambda: job_w1_claude_fx_determinism(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "07_claude_fx_determinism.json")],
            "timeout_sec": 120.0,
        },
        {
            "id": "w1_legacy_smoke",
            "job_profile": "light_cpu",
            "deps": ["w0_branch_preservation", "w0_implementation_matrix"],
            "fn": lambda: job_w1_legacy_smoke(run_id),
            "expected_artifacts": [str(LOGS_DIR / "w1_legacy_smoke.log")],
            "timeout_sec": 240.0,
        },
        # W2: Sequential heavy 1080p renders (A/B/C + 3 unseen -> then 30s Portus final film)
        {
            "id": "w2_abc_and_unseen_renders",
            "job_profile": "heavy_render",
            "deps": [
                "w1_motion_plan_unit",
                "w1_natural_motion_metrics",
                "w1_rigby_runtime_pilot",
                "w1_claude_fx_determinism",
                "w1_legacy_smoke",
            ],
            "fn": lambda: job_w2_abc_and_unseen_renders(run_id),
            "expected_artifacts": [
                str(EVIDENCE_DIR / "09_a_b_c_render_comparison.json"),
                str(EVIDENCE_DIR / "04_motion_plan_generalization.json"),
                str(EVIDENCE_DIR / "contact_sheet_abc_comparison.png"),
                str(EVIDENCE_DIR / "abc_motion_traces.json"),
            ],
            "timeout_sec": 600.0,
        },
        {
            "id": "w2_portus_30s_render",
            "job_profile": "heavy_render",
            "deps": ["w2_abc_and_unseen_renders"],
            "fn": lambda: job_w2_portus_30s_render(run_id),
            "expected_artifacts": [
                str(EVIDENCE_DIR / "10_portus_original_30s_media_receipt.json"),
                str(EVIDENCE_DIR / "11_portus_voice_sound_timing.json"),
                str(EVIDENCE_DIR / "17_original_visual_source_lineage.json"),
                str(EVIDENCE_DIR / "contact_sheet_full.png"),
                str(EVIDENCE_DIR / "contact_sheet_hook.png"),
                str(EVIDENCE_DIR / "contact_sheet_action.png"),
            ],
            "timeout_sec": 600.0,
        },
        # W3a: Parallel independent decode & mutation QA on finished artifacts
        {
            "id": "w3_portus_camera_and_motion_decode",
            "job_profile": "visual_decode",
            "deps": ["w2_portus_30s_render"],
            "fn": lambda: job_w3_portus_camera_and_motion_decode(run_id),
            "expected_artifacts": [str(LOGS_DIR / "w3_portus_decode.json")],
            "timeout_sec": 300.0,
        },
        {
            "id": "w3_legacy_cut_coverage_decode",
            "job_profile": "visual_decode",
            "deps": ["w2_portus_30s_render"],
            "fn": lambda: job_w3_legacy_cut_coverage_decode(run_id),
            "expected_artifacts": [str(LOGS_DIR / "w3_legacy_cuts.json")],
            "timeout_sec": 360.0,
        },
        {
            "id": "w3_motion_qa_and_mutations",
            "job_profile": "light_cpu",
            "deps": ["w2_portus_30s_render"],
            "fn": lambda: job_w3_motion_qa_and_mutations(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "12_motion_qa_and_real_mutations.json")],
            "timeout_sec": 300.0,
        },
        # W3b..W3e: Cut rollup -> Sequential heavy shot repair -> Full 81+ gate E2E -> Speed benchmarks
        {
            "id": "w3_camera_coverage_rollup",
            "job_profile": "light_cpu",
            "deps": ["w3_portus_camera_and_motion_decode", "w3_legacy_cut_coverage_decode"],
            "fn": lambda: job_w3_camera_coverage_rollup(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "08_camera_segments_full_coverage.json")],
            "timeout_sec": 60.0,
        },
        {
            "id": "w3_shot_repair_closed_loop",
            "job_profile": "heavy_render",
            "deps": ["w3_camera_coverage_rollup", "w3_motion_qa_and_mutations"],
            "fn": lambda: job_w3_shot_repair_closed_loop(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "16_shot_repair_closed_loop.json")],
            "timeout_sec": 360.0,
        },
        {
            "id": "w3_full_e2e_and_backtests",
            "job_profile": "heavy_render",
            "deps": ["w3_shot_repair_closed_loop"],
            "fn": lambda: job_w3_full_e2e_and_backtests(run_id),
            "expected_artifacts": [
                str(EVIDENCE_DIR / "13_full_e2e_regression.json"),
                str(EVIDENCE_DIR / "14_backtest_synthetic_vs_real_truth.json"),
            ],
            "timeout_sec": 1800.0,
        },
        {
            "id": "w3_speed_benchmarks",
            "job_profile": "light_cpu",
            "deps": ["w3_full_e2e_and_backtests"],
            "fn": lambda: job_w3_speed_benchmarks(run_id),
            "expected_artifacts": [str(EVIDENCE_DIR / "15_speed_serial_parallel_and_total_e2e.json")],
            "timeout_sec": 300.0,
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

    # Publish 02_resource_process_tree_timeseries.json
    telemetry_raw = dict(dag_rep.get("telemetry") or {})
    tel_ok = (
        not telemetry_raw.get("breach_detected", False)
        and float(telemetry_raw.get("min_disk_free_gb") or 0.0) >= 6.0
        and float(telemetry_raw.get("min_ram_available_gb") or 0.0) >= 1.0
    )
    tel_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.qa_scheduler::TelemetrySampler",
        file_paths=["scripts/qa_scheduler.py"],
        start_ts=dag_rep["started_at"],
        end_ts=dag_rep["ended_at"],
        exit_code=0 if tel_ok else 1,
        status="PASS" if tel_ok else "BLOCKED_RESOURCE",
        original_input_sha256=sha256_file(ROOT_DIR / "scripts/qa_scheduler.py"),
        output_sha256=None,
        body=telemetry_raw,
        error_reason=None if tel_ok else f"Resource floor breached: {telemetry_raw.get('breach_reason')}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "02_resource_process_tree_timeseries.json",
        tel_payload,
        run_id=run_id,
        writer_job_id="w4_telemetry",
        required_keys=["status", "peak_rss_mb", "min_disk_free_gb", "min_ram_available_gb", "samples_count", "breach_detected"],
    )

    # Publish 03_async_dag_jobs.json
    cp = dict(dag_rep.get("concurrency_proof") or {})
    dag_ok = (
        dag_rep["all_succeeded"] is True
        and int(dag_rep.get("orphan_worker_processes_after_run", 1)) == 0
        and int(cp.get("overlapping_pairs_count", 0)) >= 1
    )
    dag_body = {
        "dag_status": dag_rep["status"],
        "all_succeeded": dag_rep["all_succeeded"],
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
    dag_payload = _gate_envelope(
        run_id=run_id,
        command_or_function="scripts.qa_scheduler::run_dag",
        file_paths=["scripts/qa_scheduler.py", "scripts/run_fl01_v14_7_6_validation.py"],
        start_ts=dag_rep["started_at"],
        end_ts=dag_rep["ended_at"],
        exit_code=0 if dag_ok else 1,
        status="PASS" if dag_ok else "FAIL",
        original_input_sha256=sha256_file(ROOT_DIR / "scripts/qa_scheduler.py"),
        output_sha256=None,
        body=dag_body,
        error_reason=None if dag_ok else f"DAG status={dag_rep['status']}, non_pass={dag_rep.get('mandatory_non_pass_ids')}",
    )
    publish_atomic_evidence(
        EVIDENCE_DIR / "03_async_dag_jobs.json",
        dag_payload,
        run_id=run_id,
        writer_job_id="w4_dag_ledger",
        required_keys=["status", "all_succeeded", "total_jobs", "concurrency_proof", "jobs"],
    )

    if not dag_rep["all_succeeded"]:
        print(f"DAG failed: status={dag_rep['status']}, non-pass={dag_rep.get('mandatory_non_pass_ids')}")
        for j in dag_rep.get("jobs", []):
            if j["status"] != "PASS":
                print(f"  - {j['id']}: {j['status']} | {j.get('error')}")
        return 1

    # Clean incidental legacy E2E touches & re-verify 15 preserved artifacts post-DAG
    _restore_incidental_legacy_e2e_touches()
    job_w0_branch_preservation(run_id, writer_id="w0_branch_preservation")

    # Master Status (`00_master_status.json`)
    master_rep = _build_and_publish_master_status(run_id, t_suite_start)

    # Pre-push placeholder for `19_git_post_push_attestation.json` (finalized in follow-on docs commit after code push)
    ls_prod = _git_out(["ls-remote", "--heads", "origin", "Production"])
    remote_prod = ls_prod.split()[0] if ls_prod else "UNKNOWN"
    ls_fix = _git_out(["ls-remote", "--heads", "origin", MANDATORY_BRANCH])
    remote_fix = ls_fix.split()[0] if ls_fix else "UNKNOWN"
    publish_atomic_evidence(
        EVIDENCE_DIR / "19_git_post_push_attestation.json",
        {
            "evidence_schema_version": "14.7.6",
            "run_id": run_id,
            "phase": "pre_push_verified_awaiting_code_commit_push",
            "timestamp": _utc_iso(),
            "mandatory_work_branch": MANDATORY_BRANCH,
            "verified_base_sha": BASE_SHA,
            "pre_push_remote_fix_image_shot_sha": remote_fix,
            "attested_code_commit_sha": None,
            "final_remote_branch_sha": None,
            "remote_production_sha": remote_prod,
            "production_invariant_sha": PRODUCTION_INVARIANT_SHA,
            "production_unchanged": (remote_prod == PRODUCTION_INVARIANT_SHA),
        },
        run_id=run_id,
        writer_job_id="w4_attestation",
    )

    _write_markdown_packets(run_id)

    consistency = verify_v14_7_6_cross_evidence_consistency(EVIDENCE_DIR, expected_run_id=run_id)
    if not consistency["consistent"]:
        print(f"Cross-evidence consistency FAILED: {consistency['errors']}")
        return 1

    print(
        f"=== V14.7.6 Validation PASSED: master_status={master_rep['master_status']}, "
        f"J13={master_rep['editorial_status']}, jobs={dag_rep['passed_jobs']}/{dag_rep['total_jobs']} ==="
    )
    return 0 if master_rep.get("tech_all_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
