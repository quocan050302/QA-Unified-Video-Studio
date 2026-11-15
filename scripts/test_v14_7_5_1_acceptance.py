#!/usr/bin/env python3
"""scripts/test_v14_7_5_1_acceptance.py — Master Technical Acceptance Suite (FL-01 / V14.7.5.1).

Evaluates Mandatory Technical Gates R1–R8 across BOTH:
  1) Brand-new 30.000s / 720-frame original film:
     "THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET"
     (`projects/fl01_v14_7_5_1_roman_water_gate_preview/out/FL01_V14_7_5_1_ROMAN_WATER_GATE_ORIGINAL_30S_1080P.mp4`)
  2) Preserved V14.7.5 benchmark film:
     "THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE"
     (`projects/fl01_v14_7_5_roman_eagle_in_fog_preview/out/FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4`)

Plus Independent Human Editorial Gate J13 (`EDITORIAL_REVIEW_PENDING` — never self-approved by machine;
technical green yields `master_status = "TECH_VERIFIED_PENDING_EDITORIAL"`, never `PRODUCTION_COMPLETE`).
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    inspect_media_file,
    sha256_file,
    sha256_json,
    verify_receipt_and_lineage,
)
from scripts.qa_scheduler import inspect_resource_budget
from scripts.test_v14_7_5_acceptance import (
    _evaluate_voice_intervals_truth,
    run_failure_injection_self_checks,
)
from tools.ai_director import resolve_ai_director_policy
from tools.cinematic_camera import (
    audit_camera_grammar,
    audit_camera_snap_keyframes,
    plan_camera_sequence,
    validate_camera_sequence,
)
from tools.global_settings import InMemorySecretStore, isolated_secret_store
from tools.produce_fl01_v14_7_5_1_roman_water_gate_preview import (
    FILM_SUBTITLE as WG_SUBTITLE,
    FILM_TITLE as WG_TITLE,
    NOMINAL_VIDEO_FRAMES as WG_FRAMES,
    OUT_MP4_PATH as WG_MP4_PATH,
    PROJECT_DIR as WG_PROJECT_DIR,
    build_water_gate_storyboard,
    inspect_water_gate_preview,
    verify_water_gate_causality,
)
from tools.produce_fl01_v14_7_5_roman_eagle_in_fog_preview import (
    OUT_MP4_PATH as EAGLE_MP4_PATH,
    PROJECT_DIR as EAGLE_PROJECT_DIR,
    inspect_eagle_preview,
)
from tools.temporal_visual_qa import (
    TemporalQAReport,
    audit_project_temporal_visual,
)
from tools.visual_qa_v14_6 import audit_tactical_labels_mobile, extract_frame_at_time

EVIDENCE_DIR = ROOT_DIR / "tests" / "evidence" / "v14_7_5_1"


def _iso_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class GateRecord:
    def __init__(
        self,
        gate_id: str,
        name: str,
        status: str,
        command_or_function: str,
        exit_code: int,
        started_at: str,
        ended_at: str,
        measured_duration_sec: float,
        input_sha256: str,
        output_sha256: str,
        evaluator_evidence_paths: List[str],
        details: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        self.gate_id = gate_id
        self.name = name
        self.status = status
        self.command_or_function = command_or_function
        self.exit_code = exit_code
        self.started_at = started_at
        self.ended_at = ended_at
        self.measured_duration_sec = measured_duration_sec
        self.input_sha256 = input_sha256
        self.output_sha256 = output_sha256
        self.evaluator_evidence_paths = evaluator_evidence_paths
        self.details = details
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "status": self.status,
            "command_or_function": self.command_or_function,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "measured_duration_sec": self.measured_duration_sec,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "evaluator_evidence_paths": self.evaluator_evidence_paths,
            "details": self.details,
            "error": self.error,
        }


def _load_or_run_temporal_report(
    project_dir: Path,
    mp4_path: Path,
    cached_json_path: Optional[Path],
    work_dir: Path,
) -> TemporalQAReport:
    if cached_json_path and cached_json_path.is_file():
        data = json.loads(cached_json_path.read_text(encoding="utf-8"))
        # Support either direct TemporalQAReport JSON or wrapper dict with "report"
        rep_dict = data.get("report") if isinstance(data, dict) and "report" in data else data
        return TemporalQAReport.model_validate(rep_dict)
    rep = audit_project_temporal_visual(
        project_dir=project_dir,
        mp4_path=mp4_path,
        output_evidence_dir=work_dir,
        run_negative_suite=False,
    )
    shutil.rmtree(work_dir, ignore_errors=True)
    return rep


def _measure_water_blue_fraction(rgb: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> float:
    h, w, _ = rgb.shape
    roi = rgb[int(y0 * h) : int(y1 * h), int(x0 * w) : int(x1 * w)]
    if roi.size == 0:
        return 0.0
    r = roi[:, :, 0].astype(np.int16)
    g = roi[:, :, 1].astype(np.int16)
    b = roi[:, :, 2].astype(np.int16)
    # Civic water palette (#2978b5 / #4da3df / #79c4f2): strong blue channel dominance over red
    mask = (b > 135) & ((b - r) > 35) & (g > 90)
    return round(float(np.mean(mask)), 5)


def _measure_dark_timber_gate_fraction(rgb: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> float:
    h, w, _ = rgb.shape
    roi = rgb[int(y0 * h) : int(y1 * h), int(x0 * w) : int(x1 * w)]
    if roi.size == 0:
        return 0.0
    r = roi[:, :, 0].astype(np.int16)
    g = roi[:, :, 1].astype(np.int16)
    b = roi[:, :, 2].astype(np.int16)
    # Timber sluice gate (#6f4c2f / #53361f / #3d352e iron strap): warm dark brown/iron replacing blue channel
    mask = (r > 55) & (r < 140) & (b < 80) & ((r - b) >= 18)
    return round(float(np.mean(mask)), 5)


def run_v14_7_5_1_acceptance_suite(
    evidence_dir: Path = EVIDENCE_DIR,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute R1–R8 mandatory technical gates + J13 human editorial gate on real V14.7.5.1 artifacts."""
    t_suite0 = time.perf_counter()
    ev_dir = Path(evidence_dir).resolve()
    ev_dir.mkdir(parents=True, exist_ok=True)
    effective_run_id = run_id or f"v14_7_5_1_accept_{int(time.time())}"

    wg_tq = _load_or_run_temporal_report(
        WG_PROJECT_DIR,
        WG_MP4_PATH,
        ev_dir / "11_water_gate_temporal.json",
        ev_dir / "_tmp_wg_tq",
    )

    cov_json = _load_json_if_exists(ev_dir / "07_cut_boundary_coverage.json")
    if cov_json and isinstance(cov_json.get("eagle_temporal_report"), dict):
        eagle_tq = TemporalQAReport.model_validate(cov_json["eagle_temporal_report"])
    else:
        eagle_tq = _load_or_run_temporal_report(
            EAGLE_PROJECT_DIR,
            EAGLE_MP4_PATH,
            None,
            ev_dir / "_tmp_eagle_tq",
        )

    wg_shots_sha = sha256_file(WG_PROJECT_DIR / "story" / "shots.json") if (WG_PROJECT_DIR / "story" / "shots.json").is_file() else ""
    wg_mp4_sha = sha256_file(WG_MP4_PATH) if WG_MP4_PATH.is_file() else ""
    eagle_mp4_sha = sha256_file(EAGLE_MP4_PATH) if EAGLE_MP4_PATH.is_file() else ""
    combined_in_sha = sha256_json({"wg_shots": wg_shots_sha, "wg_mp4": wg_mp4_sha, "eagle_mp4": eagle_mp4_sha})

    gates: List[GateRecord] = []

    def run_gate(
        gate_id: str,
        name: str,
        fn_label: str,
        ev_paths: List[str],
        fn: Callable[[], Tuple[str, Dict[str, Any], Optional[str]]],
    ) -> None:
        started_at = _iso_utc()
        t0 = time.perf_counter()
        try:
            status, details, err = fn()
            dur = round(time.perf_counter() - t0, 4)
            ended_at = _iso_utc()
            exit_code = 0 if status in ("PASS", "EDITORIAL_REVIEW_PENDING") else 1
            out_sha = sha256_json({"gate_id": gate_id, "status": status, "details": details})
            rec = GateRecord(
                gate_id=gate_id,
                name=name,
                status=status,
                command_or_function=fn_label,
                exit_code=exit_code,
                started_at=started_at,
                ended_at=ended_at,
                measured_duration_sec=dur,
                input_sha256=combined_in_sha,
                output_sha256=out_sha,
                evaluator_evidence_paths=ev_paths,
                details=details,
                error=err,
            )
            gates.append(rec)
            print(f"[{status}] Gate {gate_id}: {name} ({dur:.3f}s)")
            if err:
                print(f"    Reason: {err}")
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            dur = round(time.perf_counter() - t0, 4)
            ended_at = _iso_utc()
            rec = GateRecord(
                gate_id=gate_id,
                name=name,
                status="FAIL",
                command_or_function=fn_label,
                exit_code=1,
                started_at=started_at,
                ended_at=ended_at,
                measured_duration_sec=dur,
                input_sha256=combined_in_sha,
                output_sha256=sha256_json({"exception": str(exc)}),
                evaluator_evidence_paths=ev_paths,
                details={"exception": str(exc), "traceback": tb},
                error=str(exc),
            )
            gates.append(rec)
            print(f"[FAIL] Gate {gate_id}: {name} -> EXCEPTION: {exc}")

    # =========================================================================
    # R1: NO_UNINTENDED_TELEPORT_AND_FULL_CUT_COVERAGE (Eagle 11/11 + Water Gate 7/7)
    # =========================================================================
    def check_r1() -> Tuple[str, Dict[str, Any], Optional[str]]:
        wg_shots = json.loads((WG_PROJECT_DIR / "story" / "shots.json").read_text(encoding="utf-8")).get("shots", [])
        eagle_shots = json.loads((EAGLE_PROJECT_DIR / "story" / "shots.json").read_text(encoding="utf-8")).get("shots", [])

        wg_teleports = [sid for sid, a in wg_tq.shot_audits.items() if a.teleport_detected or a.sudden_disappearance]
        eagle_teleports = [sid for sid, a in eagle_tq.shot_audits.items() if a.teleport_detected or a.sudden_disappearance]

        details = {
            "water_gate": {
                "verdict": wg_tq.technical_verdict,
                "shots_passed": f"{wg_tq.passed_shots}/{wg_tq.total_shots}",
                "expected_cut_count": wg_tq.expected_cut_count,
                "audited_cut_count": wg_tq.audited_cut_count,
                "unaudited_cuts": wg_tq.unaudited_cuts,
                "full_boundary_coverage": wg_tq.full_boundary_coverage,
                "within_shot_teleports": wg_teleports,
            },
            "eagle_in_fog": {
                "verdict": eagle_tq.technical_verdict,
                "shots_passed": f"{eagle_tq.passed_shots}/{eagle_tq.total_shots}",
                "expected_cut_count": eagle_tq.expected_cut_count,
                "audited_cut_count": eagle_tq.audited_cut_count,
                "unaudited_cuts": eagle_tq.unaudited_cuts,
                "full_boundary_coverage": eagle_tq.full_boundary_coverage,
                "within_shot_teleports": eagle_teleports,
            },
        }
        if wg_tq.technical_verdict == "NOT_VERIFIED" or eagle_tq.technical_verdict == "NOT_VERIFIED":
            return "NOT_VERIFIED", details, "Temporal QA returned NOT_VERIFIED"

        ok = (
            wg_tq.technical_verdict == "VISUAL_TECH_PASS"
            and eagle_tq.technical_verdict == "VISUAL_TECH_PASS"
            and len(wg_shots) == 8
            and wg_tq.expected_cut_count == 7
            and wg_tq.audited_cut_count == 7
            and wg_tq.full_boundary_coverage is True
            and wg_tq.unaudited_cuts == []
            and len(eagle_shots) == 12
            and eagle_tq.expected_cut_count == 11
            and eagle_tq.audited_cut_count == 11
            and eagle_tq.full_boundary_coverage is True
            and eagle_tq.unaudited_cuts == []
            and not wg_teleports
            and not eagle_teleports
        )
        if not ok:
            return "FAIL", details, f"R1 cut-coverage or teleport failure: {details}"
        return "PASS", details, None

    run_gate(
        "R1",
        "NO_UNINTENDED_TELEPORT_AND_FULL_CUT_COVERAGE",
        "scripts/test_v14_7_5_1_acceptance.py::check_r1",
        [
            "tests/evidence/v14_7_5_1/07_cut_boundary_coverage.json",
            "tests/evidence/v14_7_5_1/11_water_gate_temporal.json",
        ],
        check_r1,
    )

    # =========================================================================
    # R2: ACTOR_ID_APPEARANCE_RATIO_POSITION
    # =========================================================================
    def check_r2() -> Tuple[str, Dict[str, Any], Optional[str]]:
        chara_js = (ROOT_DIR / "packs" / "squire" / "chara.js").read_text(encoding="utf-8")
        cast_presets = set(re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:\s*K\(", chara_js, flags=re.MULTILINE))

        def _audit_film_actors(proj_dir: Path, tq: TemporalQAReport) -> Dict[str, Any]:
            bible = json.loads((proj_dir / "story" / "character_bible.json").read_text(encoding="utf-8")).get("characters", {})
            shots = json.loads((proj_dir / "story" / "shots.json").read_text(encoding="utf-8")).get("shots", [])
            invalid_presets = [cid for cid, inf in bible.items() if inf.get("preset") not in cast_presets]
            drift: List[str] = []
            for s in shots:
                for p in s.get("args", {}).get("people", []):
                    if isinstance(p, dict) and p.get("id") in bible:
                        if p.get("preset") != bible[p["id"]]["preset"]:
                            drift.append(f"{s['id']}:{p['id']}")
            ratios: Dict[str, float] = {}
            outliers: List[str] = []
            for sid, aud in tq.shot_audits.items():
                if aud.expected_subject == "actor" and aud.bounds and aud.bounds.detected:
                    hr = round(aud.bounds.ymax - aud.bounds.ymin, 3)
                    ratios[sid] = hr
                    if aud.tpl == "scene" and not (0.16 <= hr <= 0.92):
                        outliers.append(f"{sid}:{hr}")
            return {
                "characters": list(bible.keys()),
                "invalid_presets": invalid_presets,
                "preset_drift": drift,
                "decoded_actor_height_ratios": ratios,
                "ratio_outliers": outliers,
                "no_clipped_heads": tq.no_clipped_heads,
                "framing_safe_all": tq.framing_safe_all,
                "valid": (
                    bool(ratios)
                    and not invalid_presets
                    and not drift
                    and not outliers
                    and tq.no_clipped_heads
                    and tq.framing_safe_all
                ),
            }

        wg_actors = _audit_film_actors(WG_PROJECT_DIR, wg_tq)
        eagle_actors = _audit_film_actors(EAGLE_PROJECT_DIR, eagle_tq)
        details = {
            "water_gate_actors": wg_actors,
            "eagle_actors": eagle_actors,
            "manual_facial_resemblance_disclosure": (
                "2D procedural vector actors maintain deterministic tunic palettes, headbands, scrolls, and height ratios; "
                "fine facial expression and emotional nuance remain subject to J13 human editorial review."
            ),
        }
        if not wg_actors["valid"] or not eagle_actors["valid"]:
            return "FAIL", details, f"Actor identity/bounds check failed: {details}"
        return "PASS", details, None

    run_gate(
        "R2",
        "ACTOR_ID_APPEARANCE_RATIO_POSITION",
        "scripts/test_v14_7_5_1_acceptance.py::check_r2",
        [
            "projects/fl01_v14_7_5_1_roman_water_gate_preview/story/character_bible.json",
            "tests/evidence/v14_7_5_1/11_water_gate_temporal.json",
        ],
        check_r2,
    )

    # =========================================================================
    # R3: CAMERA_CUT_VALIDITY_AND_100PCT_BOUNDARY_SAMPLES
    # =========================================================================
    def check_r3() -> Tuple[str, Dict[str, Any], Optional[str]]:
        def _audit_cam(proj_dir: Path, tq: TemporalQAReport) -> Dict[str, Any]:
            shots = json.loads((proj_dir / "story" / "shots.json").read_text(encoding="utf-8")).get("shots", [])
            snaps: List[str] = []
            for s in shots:
                kfs = (s.get("args", {}) or {}).get("cameraRig", {}).get("keyframes", [])
                det, diags = audit_camera_snap_keyframes(kfs)
                if det:
                    snaps.append(f"{s['id']}:{diags}")
            plans = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
            seq_ok, seq_errs = validate_camera_sequence(plans, shots)
            gram = audit_camera_grammar(plans)
            b_ev = tq.boundary_evidence
            frozen = [b["cut"] for b in b_ev if float(b.get("pixel_mean_abs_delta", 0.0)) < 0.5]
            invalid_reasons = [b["cut"] for b in b_ev if not b.get("reason_allowlisted", False)]
            complete_frames = all(
                len(b.get("extracted_frame_indices", {})) == 4
                and len(b.get("artifact_shas", {})) == 4
                and b.get("coverage_complete") is True
                and b.get("status") == "PASS"
                for b in b_ev
            )
            return {
                "shots_count": len(shots),
                "expected_cuts": max(0, len(shots) - 1),
                "audited_cuts": len(b_ev),
                "boundary_frame_samples_decoded": len(b_ev) * 4,
                "complete_4frame_windows": complete_frames,
                "within_shot_snaps": snaps,
                "camera_sequence_valid": seq_ok,
                "diverse_grammar_verified": gram.get("diverse_grammar_verified"),
                "frozen_cuts": frozen,
                "invalid_cut_reasons": invalid_reasons,
                "valid": (
                    len(b_ev) == max(0, len(shots) - 1)
                    and complete_frames
                    and not snaps
                    and seq_ok
                    and bool(gram.get("diverse_grammar_verified"))
                    and not frozen
                    and not invalid_reasons
                ),
            }

        wg_cam = _audit_cam(WG_PROJECT_DIR, wg_tq)
        eagle_cam = _audit_cam(EAGLE_PROJECT_DIR, eagle_tq)
        neg_snap_caught, _ = audit_camera_snap_keyframes(
            [{"t": 0.0, "x": 0.5, "y": 0.5, "z": 1.0}, {"t": 0.04, "x": 0.92, "y": 0.5, "z": 1.0}]
        )
        details = {
            "water_gate_camera": wg_cam,
            "eagle_camera": eagle_cam,
            "negative_1frame_snap_caught": bool(neg_snap_caught),
        }
        if not (wg_cam["valid"] and eagle_cam["valid"] and neg_snap_caught):
            return "FAIL", details, f"R3 camera/boundary audit failed: {details}"
        return "PASS", details, None

    run_gate(
        "R3",
        "CAMERA_CUT_VALIDITY_AND_BOUNDARY_SAMPLES",
        "scripts/test_v14_7_5_1_acceptance.py::check_r3",
        [
            "tests/evidence/v14_7_5_1/07_cut_boundary_coverage.json",
            "tests/evidence/v14_7_5_1/11_water_gate_temporal.json",
        ],
        check_r3,
    )

    # =========================================================================
    # R4: NARRATION_ACTION_ALIGNMENT_CAUSALITY
    # =========================================================================
    def check_r4() -> Tuple[str, Dict[str, Any], Optional[str]]:
        wg_v = json.loads((WG_PROJECT_DIR / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
        wg_truth = _evaluate_voice_intervals_truth(wg_v.get("events", []), min_tail_floor=0.25)

        eagle_v = json.loads((EAGLE_PROJECT_DIR / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
        eagle_truth = _evaluate_voice_intervals_truth(eagle_v.get("events", []), min_tail_floor=0.25)

        wg_sb = json.loads((WG_PROJECT_DIR / "story" / "shots.json").read_text(encoding="utf-8"))
        causality = verify_water_gate_causality(wg_sb)

        # Negative causality control: corrupting gate direction or swapping stream layer MUST fail
        bad_sb = copy.deepcopy(wg_sb)
        bad_sb["shots"][5]["mechanics"]["gate_drop_end"] = 0.05  # Fails to close gate in S06
        corrupted_causality = verify_water_gate_causality(bad_sb)

        # Decoded pixel confirmation of sluice gate sealing downstream flow in S06 and diverting water into basin in S07
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            f_s06_start = td_p / "s06_start.png"
            f_s06_end = td_p / "s06_end.png"
            f_s07 = td_p / "s07.png"
            extract_frame_at_time(WG_MP4_PATH, 19.15, f_s06_start)
            extract_frame_at_time(WG_MP4_PATH, 22.75, f_s06_end)
            extract_frame_at_time(WG_MP4_PATH, 25.2, f_s07)
            rgb_s06_start = np.array(Image.open(f_s06_start).convert("RGB"))
            rgb_s06_end = np.array(Image.open(f_s06_end).convert("RGB"))
            rgb_s07 = np.array(Image.open(f_s07).convert("RGB"))

        # Sluice mechanism ROI (x=0.52..0.74, y=0.40..0.62) exhibits genuine mechanical motion across S06
        mech_roi_start = rgb_s06_start[int(0.40 * 1080) : int(0.62 * 1080), int(0.52 * 1920) : int(0.74 * 1920)].astype(np.float32)
        mech_roi_end = rgb_s06_end[int(0.40 * 1080) : int(0.62 * 1080), int(0.52 * 1920) : int(0.74 * 1920)].astype(np.float32)
        sluice_motion_delta = round(float(np.mean(np.abs(mech_roi_end - mech_roi_start))), 3)
        # In S07 right-hand overflow basin (x=0.63..0.83, y=0.52..0.80), diverted blue water cascade is visibly present
        overflow_blue_s07 = _measure_water_blue_fraction(rgb_s07, 0.63, 0.52, 0.83, 0.80)
        pixel_causality_ok = (sluice_motion_delta >= 4.0) and (overflow_blue_s07 >= 0.08)

        details = {
            "water_gate_voice": wg_truth,
            "water_gate_last_spoken_end_sec": wg_v["events"][-1]["spoken_end"],
            "eagle_voice": eagle_truth,
            "water_gate_causality": causality,
            "corrupted_causality_rejected": (not corrupted_causality["valid"]),
            "decoded_pixel_causality": {
                "s06_sluice_mechanism_mean_abs_delta": sluice_motion_delta,
                "overflow_basin_blue_fraction_s07": overflow_blue_s07,
                "pixel_causality_confirmed": pixel_causality_ok,
            },
        }
        ok = (
            wg_truth["valid"]
            and float(wg_v["events"][-1]["spoken_end"]) <= 29.75
            and eagle_truth["valid"]
            and causality["valid"]
            and (not corrupted_causality["valid"])
            and pixel_causality_ok
        )
        if not ok:
            return "FAIL", details, f"R4 voice timing or action causality failed: {details}"
        return "PASS", details, None

    run_gate(
        "R4",
        "NARRATION_ACTION_ALIGNMENT_CAUSALITY",
        "scripts/test_v14_7_5_1_acceptance.py::check_r4",
        [
            "tests/evidence/v14_7_5_1/12_voice_and_audio_metrics.json",
            "projects/fl01_v14_7_5_1_roman_water_gate_preview/timeline/timeline_voice_events.json",
        ],
        check_r4,
    )

    # =========================================================================
    # R5: NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR
    # =========================================================================
    def check_r5() -> Tuple[str, Dict[str, Any], Optional[str]]:
        forbidden = [
            "THIEU SHOT",
            "THIẾU ẢNH",
            "LOI CANH",
            "PREFLIGHT GATE: BLOCKED",
            "[404 Required]",
            "[loi trang]",
            "Uncaught",
            "Fatal:",
            "Error:",
        ]
        wg_log_p = WG_PROJECT_DIR / "build" / "render.log"
        eagle_log_p = EAGLE_PROJECT_DIR / "build" / "render.log"
        if not wg_log_p.is_file() or not eagle_log_p.is_file():
            return "NOT_VERIFIED", {}, "Missing build/render.log on Water Gate or Eagle"

        wg_errs = [tok for tok in forbidden if tok in wg_log_p.read_text(encoding="utf-8")]
        eagle_errs = [tok for tok in forbidden if tok in eagle_log_p.read_text(encoding="utf-8")]

        pixel_checks: Dict[str, Any] = {}
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            for label, mp4_p, ts, require_badge in [
                ("wg_s01_hook_badge", WG_MP4_PATH, 1.5, True),
                ("wg_s06_sluice_gate", WG_MP4_PATH, 21.2, False),
                ("wg_s08_end_card", WG_MP4_PATH, 28.5, True),
                ("eagle_s06_diagram", EAGLE_MP4_PATH, 25.0, True),
            ]:
                png_p = td_p / f"{label}.png"
                if not extract_frame_at_time(mp4_p, ts, png_p):
                    return "NOT_VERIFIED", {}, f"Failed to decode {label} at {ts}s"
                arr = np.array(Image.open(png_p).convert("RGB"))
                if require_badge:
                    mob_ok, mob_diags = audit_tactical_labels_mobile(arr)
                else:
                    # S06 is an unbadged mechanical action shot: verify rich bronze/water/actor pixels
                    water_f = _measure_water_blue_fraction(arr, 0.45, 0.35, 0.80, 0.68)
                    mob_ok = (float(np.std(arr)) >= 25.0) and (water_f >= 0.01)
                    mob_diags = [] if mob_ok else [f"Sluice water/actor pixels missing (water_f={water_f})"]
                pixel_checks[label] = {
                    "timestamp_sec": ts,
                    "mean_luma": round(float(np.mean(arr)), 2),
                    "std_luma": round(float(np.std(arr)), 2),
                    "verified": mob_ok,
                    "diagnostics": mob_diags,
                }

        wg_non_empty = all(a.non_empty_content for a in wg_tq.shot_audits.values())
        eagle_non_empty = all(a.non_empty_content for a in eagle_tq.shot_audits.values())
        details = {
            "water_gate_render_log_bytes": wg_log_p.stat().st_size,
            "eagle_render_log_bytes": eagle_log_p.stat().st_size,
            "water_gate_forbidden_tokens": wg_errs,
            "eagle_forbidden_tokens": eagle_errs,
            "water_gate_all_shots_non_empty": wg_non_empty,
            "eagle_all_shots_non_empty": eagle_non_empty,
            "decoded_pixel_checks": pixel_checks,
        }
        ok = (
            not wg_errs
            and not eagle_errs
            and wg_non_empty
            and eagle_non_empty
            and all(v["verified"] and v["std_luma"] >= 18.0 for v in pixel_checks.values())
        )
        if not ok:
            return "FAIL", details, f"R5 render log or pixel check failed: {details}"
        return "PASS", details, None

    run_gate(
        "R5",
        "NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR",
        "scripts/test_v14_7_5_1_acceptance.py::check_r5",
        [
            "projects/fl01_v14_7_5_1_roman_water_gate_preview/build/render.log",
            "tests/evidence/v14_7_5_1/10_water_gate_media.json",
        ],
        check_r5,
    )

    # =========================================================================
    # R6: GEMINI_FALLBACK_PROVENANCE
    # =========================================================================
    def check_r6() -> Tuple[str, Dict[str, Any], Optional[str]]:
        wg_rcpt = json.loads((WG_PROJECT_DIR / "build" / "render_receipt.json").read_text(encoding="utf-8"))
        eagle_rcpt = json.loads((EAGLE_PROJECT_DIR / "build" / "render_receipt.json").read_text(encoding="utf-8"))
        wg_prov = wg_rcpt.get("provenance", {})
        eagle_prov = eagle_rcpt.get("provenance", {})

        matrix_results: Dict[str, Any] = {}
        saved_tm = os.environ.get("QA_STUDIO_TEST_MODE")
        os.environ["QA_STUDIO_TEST_MODE"] = "1"
        try:
            with isolated_secret_store(InMemorySecretStore(initial_key=None)):
                with tempfile.TemporaryDirectory() as tmp_d:
                    tp = Path(tmp_d)
                    (tp / "config.json").write_text(json.dumps({"ai_director_mode": "OFFLINE_ONLY"}), encoding="utf-8")
                    matrix_results["OFFLINE_ONLY"] = resolve_ai_director_policy(tp).get("mode")

                    (tp / "config.json").write_text(
                        json.dumps({"ai_director_mode": "LIVE_REQUIRED", "force_test_live": True}), encoding="utf-8"
                    )
                    p2 = resolve_ai_director_policy(tp)
                    matrix_results["LIVE_REQUIRED_NO_KEY"] = (p2.get("mode") == "LIVE_REQUIRED" and not p2.get("has_key"))
                    (tp / "story").mkdir(parents=True, exist_ok=True)
                    (tp / "story" / "shots.json").write_text(json.dumps({"shots": [{"id": "s01", "dur": 3.0}]}), encoding="utf-8")
                    env_clean = dict(os.environ)
                    env_clean.pop("GEMINI_API_KEY", None)
                    cli = subprocess.run(
                        [sys.executable, "tools/assign_visuals.py", "--project", str(tp)],
                        cwd=ROOT_DIR,
                        env=env_clean,
                        capture_output=True,
                    )
                    matrix_results["CLI_LIVE_REQUIRED_FAIL_CLOSED"] = (cli.returncode != 0)
        finally:
            if saved_tm is None:
                os.environ.pop("QA_STUDIO_TEST_MODE", None)
            else:
                os.environ["QA_STUDIO_TEST_MODE"] = saved_tm

        details = {
            "water_gate_provenance": wg_prov,
            "eagle_provenance": eagle_prov,
            "policy_matrix": matrix_results,
        }
        ok = (
            wg_prov.get("ai_director_mode") == "OFFLINE_ONLY"
            and wg_prov.get("ai_director_live_used") is False
            and wg_prov.get("render_mode") in ("REAL_RENDER", "CACHE_HIT_VERIFIED")
            and eagle_prov.get("ai_director_mode") == "OFFLINE_ONLY"
            and eagle_prov.get("ai_director_live_used") is False
            and matrix_results.get("OFFLINE_ONLY") == "OFFLINE_ONLY"
            and matrix_results.get("LIVE_REQUIRED_NO_KEY") is True
            and matrix_results.get("CLI_LIVE_REQUIRED_FAIL_CLOSED") is True
        )
        if not ok:
            return "FAIL", details, f"R6 provenance/Gemini policy failed: {details}"
        return "PASS", details, None

    run_gate(
        "R6",
        "GEMINI_FALLBACK_PROVENANCE",
        "scripts/test_v14_7_5_1_acceptance.py::check_r6",
        [
            "tests/evidence/v14_7_5_1/08_fingerprint_receipt_integrity.json",
            "tests/evidence/v14_7_5_1/10_water_gate_media.json",
        ],
        check_r6,
    )

    # =========================================================================
    # R7: VERIFIED_NEW_30S_MP4_LINEAGE_ORIGINALITY_AND_SHEETS
    # =========================================================================
    def check_r7() -> Tuple[str, Dict[str, Any], Optional[str]]:
        if not WG_MP4_PATH.is_file():
            return "NOT_VERIFIED", {}, f"Missing {WG_MP4_PATH}"

        wg_insp = inspect_water_gate_preview(WG_PROJECT_DIR, WG_MP4_PATH)
        wg_lin = wg_insp["lineage"]
        wg_mi = wg_insp["media_info"]

        eagle_lin = verify_receipt_and_lineage(
            EAGLE_PROJECT_DIR,
            EAGLE_MP4_PATH,
            expected_specs={"width": 1920, "height": 1080, "fps": 24.0, "min_duration": 50.0, "max_duration": 58.0, "require_audio": True},
        )

        # Verify final spoken line in S08 is audible inside muxed MP4
        v_ledger = json.loads((WG_PROJECT_DIR / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
        last_ev = v_ledger["events"][-1]
        tail_res = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                f"{last_ev['spoken_start']:.3f}",
                "-to",
                f"{last_ev['spoken_end']:.3f}",
                "-i",
                str(WG_MP4_PATH),
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        m_mean = re.search(r"mean_volume:\s+([-\d.]+)\s+dB", tail_res.stderr)
        final_line_db = float(m_mean.group(1)) if m_mean else -99.0
        final_line_audible = (final_line_db > -36.0) and (float(last_ev["spoken_end"]) <= float(wg_mi.get("duration", 0.0)) - 0.25)

        sheets_ok = True
        sheets_info: Dict[str, Any] = {}
        for sname in ("contact_sheet_full.png", "contact_sheet_hook.png", "contact_sheet_action.png"):
            sp = WG_PROJECT_DIR / "out" / sname
            ev_sp = ev_dir / sname
            if not sp.is_file() or sp.stat().st_size < 10000 or not ev_sp.is_file():
                sheets_ok = False
                sheets_info[sname] = {"exists": False}
            else:
                with Image.open(sp) as sim:
                    sarr = np.array(sim.convert("RGB"))
                    sheets_info[sname] = {
                        "exists": True,
                        "size_bytes": sp.stat().st_size,
                        "sha256": sha256_file(sp),
                        "dimensions": list(sim.size),
                        "std_luma": round(float(np.std(sarr)), 2),
                    }
                    if float(np.std(sarr)) < 10.0:
                        sheets_ok = False

        orig = wg_insp.get("asset_originality") or {}
        details = {
            "evidence_schema_version": "14.7.5.1",
            "mp4_path": str(WG_MP4_PATH),
            "decoded_video_frames": wg_mi.get("decoded_video_frames"),
            "duration_sec": wg_mi.get("duration"),
            "video_stream_duration_sec": wg_mi.get("video_stream_duration"),
            "audio_stream_duration_sec": wg_mi.get("audio_stream_duration"),
            "width": wg_mi.get("width"),
            "height": wg_mi.get("height"),
            "fps": wg_mi.get("fps"),
            "video_codec": wg_mi.get("video_codec"),
            "audio_codec": wg_mi.get("audio_codec"),
            "integrated_lufs": wg_mi.get("integrated_lufs"),
            "true_peak_dbtp": wg_mi.get("true_peak_dbtp"),
            "final_line_mean_db": final_line_db,
            "final_line_audible": final_line_audible,
            "input_fingerprint": wg_lin.get("input_fingerprint"),
            "recomputed_input_fingerprint": wg_lin.get("recomputed_input_fingerprint"),
            "fingerprint_match": wg_lin.get("fingerprint_match"),
            "output_sha256": wg_lin.get("output_sha256"),
            "receipt_verified": wg_lin.get("receipt_verified"),
            "cache_verified": wg_lin.get("cache_verified"),
            "media_decode_verified": wg_lin.get("media_decode_verified"),
            "prior_preview_derived_visual_inputs": orig.get("prior_preview_derived_visual_inputs"),
            "eagle_receipt_lineage_status": eagle_lin.get("status"),
            "eagle_input_fingerprint": eagle_lin.get("input_fingerprint"),
            "contact_sheets": sheets_info,
        }
        ok = (
            wg_insp.get("valid") is True
            and int(wg_mi.get("decoded_video_frames") or 0) == WG_FRAMES
            and wg_lin.get("status") == "PASS"
            and wg_lin.get("receipt_verified") is True
            and wg_lin.get("cache_verified") is True
            and wg_lin.get("media_decode_verified") is True
            and eagle_lin.get("status") == "PASS"
            and eagle_lin.get("receipt_verified") is True
            and final_line_audible
            and orig.get("prior_preview_derived_visual_inputs") == 0
            and sheets_ok
        )
        if not ok:
            return "FAIL", details, f"R7 30s MP4 / 720-frame / lineage / originality check failed: {details}"
        return "PASS", details, None

    run_gate(
        "R7",
        "VERIFIED_NEW_30S_MP4_LINEAGE_ORIGINALITY_AND_SHEETS",
        "scripts/test_v14_7_5_1_acceptance.py::check_r7",
        [
            "tests/evidence/v14_7_5_1/08_fingerprint_receipt_integrity.json",
            "tests/evidence/v14_7_5_1/10_water_gate_media.json",
            "tests/evidence/v14_7_5_1/14_new_visual_asset_lineage.json",
        ],
        check_r7,
    )

    # =========================================================================
    # R8: FULL_REGRESSION_BACKTEST_MUTATION_RESOURCE_PRESERVATION
    # =========================================================================
    def check_r8() -> Tuple[str, Dict[str, Any], Optional[str]]:
        budget = inspect_resource_budget(min_disk_gb=6.0, min_ram_gb=1.0)
        if not budget["healthy"]:
            return "BLOCKED_RESOURCE", budget, f"Resource floor breached: {budget['message']}"

        b01 = _load_json_if_exists(ev_dir / "01_branch_and_preservation.json")
        r02 = _load_json_if_exists(ev_dir / "02_resource_timeseries.json")
        j03 = _load_json_if_exists(ev_dir / "03_async_real_jobs.json")
        m04 = _load_json_if_exists(ev_dir / "04_mutation_negative_real.json")
        e05 = _load_json_if_exists(ev_dir / "05_e2e_full_regression.json")
        h06 = _load_json_if_exists(ev_dir / "06_backtest_truth.json")
        s09 = _load_json_if_exists(ev_dir / "09_shot_repair_video.json")
        sp13 = _load_json_if_exists(ev_dir / "13_speed_micro_and_e2e.json")

        missing = [
            name
            for name, obj in [
                ("01_branch_and_preservation.json", b01),
                ("02_resource_timeseries.json", r02),
                ("03_async_real_jobs.json", j03),
                ("04_mutation_negative_real.json", m04),
                ("05_e2e_full_regression.json", e05),
                ("06_backtest_truth.json", h06),
                ("09_shot_repair_video.json", s09),
                ("13_speed_micro_and_e2e.json", sp13),
            ]
            if obj is None
        ]
        if missing:
            return "NOT_VERIFIED", {"missing_evidence_files": missing}, f"Missing mandatory evidence: {missing}"

        assert b01 and r02 and j03 and m04 and e05 and h06 and s09 and sp13

        res_ts_ok = (
            r02.get("breach_detected") is False
            and float(r02.get("min_disk_free_gb") or 0.0) >= 6.0
            and float(r02.get("min_ram_available_gb") or 0.0) >= 1.0
        )
        dag_cp = j03.get("concurrency_proof") or {}
        overlap_pairs = int(dag_cp.get("overlapping_pairs_count", 0) or 0)
        dag_ok = (
            int(j03.get("total_jobs") or 0) >= 7
            and j03.get("all_succeeded") is True
            and overlap_pairs >= 1
            and int(j03.get("orphan_worker_processes_after_run", 0) or 0) == 0
        )
        mut_ok = (
            m04.get("all_mutations_killed") is True
            and int(m04.get("killed_mutations") or 0) >= 6
            and str(m04.get("execution_mode", "")).startswith("disposable_subprocess")
            and m04.get("negative_fixtures_all_passed") is True
            and int(m04.get("negative_fixtures_passed_count") or 0) >= 15
        )
        e2e_ok = (
            e05.get("exit_code") == 0
            and e05.get("verdict") == "FLOW_READY"
            and int(e05.get("required_gates_failed", 1)) == 0
            and int(e05.get("required_gates_passed", 0)) >= 81
        )
        hist_ok = (
            h06.get("synthetic_180_stress_gate_g5") == "PASS"
            and h06.get("medium_20_shot_real_render_g5b") == "PASS"
            and h06.get("historical_180_real_replay") in ("NOT_AVAILABLE", "PASS_REAL_FIXTURE")
            and h06.get("counted_not_available_as_real_replay_pass") is False
        )
        rep_ok = (
            s09.get("test_status") == "PASS"
            and s09.get("mp4_rebuilt_and_changed") is True
            and s09.get("manual_locked_preserved") is True
            and s09.get("locked_defect_status") == "BLOCKED_MANUAL_REVIEW"
        )
        pres_ok = (
            b01.get("all_preserved_intact") is True
            and b01.get("production_unchanged") is True
            and b01.get("current_branch") == "fix/Image-Shot"
        )
        speed_ok = (
            sp13.get("status") == "PASS"
            and sp13.get("microbenchmark", {}).get("all_output_digests_identical") is True
            and int(sp13.get("microbenchmark", {}).get("iterations") or 0) >= 3
        )

        details = {
            "live_resource_budget": budget,
            "runtime_min_disk_free_gb": r02.get("min_disk_free_gb"),
            "runtime_min_ram_available_gb": r02.get("min_ram_available_gb"),
            "runtime_peak_rss_mb": r02.get("peak_rss_mb"),
            "dag_total_jobs": j03.get("total_jobs"),
            "dag_overlapping_pairs": overlap_pairs,
            "orphan_worker_processes_after_run": j03.get("orphan_worker_processes_after_run"),
            "mutations_killed": f"{m04.get('killed_mutations')}/{m04.get('total_mutations')}",
            "negative_fixtures": f"{m04.get('negative_fixtures_passed_count')}/{m04.get('negative_fixtures_total_count')}",
            "e2e_run_id": e05.get("run_id"),
            "e2e_verdict": e05.get("verdict"),
            "e2e_required_passed": f"{e05.get('required_gates_passed')}/{e05.get('required_gates_total')}",
            "synthetic_180_stress_g5": h06.get("synthetic_180_stress_gate_g5"),
            "medium_20_shot_real_g5b": h06.get("medium_20_shot_real_render_g5b"),
            "historical_180_real_replay_g5c": h06.get("historical_180_real_replay"),
            "counted_not_available_as_real_replay_pass": h06.get("counted_not_available_as_real_replay_pass"),
            "shot_repair_status": s09.get("test_status"),
            "preserved_historical_artifacts_intact": pres_ok,
            "microbenchmark_digests_identical": sp13.get("microbenchmark", {}).get("all_output_digests_identical"),
        }
        if not res_ts_ok:
            return "BLOCKED_RESOURCE", details, f"Runtime telemetry breached >=6GiB disk or >=1GiB RAM floor: {details}"
        if not (dag_ok and mut_ok and e2e_ok and hist_ok and rep_ok and pres_ok and speed_ok):
            return "FAIL", details, f"R8 check failed: {details}"
        return "PASS", details, None

    run_gate(
        "R8",
        "FULL_REGRESSION_BACKTEST_MUTATION_RESOURCE_PRESERVATION",
        "scripts/test_v14_7_5_1_acceptance.py::check_r8",
        [
            "tests/evidence/v14_7_5_1/01_branch_and_preservation.json",
            "tests/evidence/v14_7_5_1/02_resource_timeseries.json",
            "tests/evidence/v14_7_5_1/03_async_real_jobs.json",
            "tests/evidence/v14_7_5_1/04_mutation_negative_real.json",
            "tests/evidence/v14_7_5_1/05_e2e_full_regression.json",
            "tests/evidence/v14_7_5_1/06_backtest_truth.json",
            "tests/evidence/v14_7_5_1/09_shot_repair_video.json",
            "tests/evidence/v14_7_5_1/13_speed_micro_and_e2e.json",
        ],
        check_r8,
    )

    # =========================================================================
    # J13: EDITORIAL_HUMAN_REVIEW (ALWAYS PENDING UNTIL HUMAN WATCHES FILM)
    # =========================================================================
    def check_j13() -> Tuple[str, Dict[str, Any], Optional[str]]:
        details = {
            "reviewer": "USER / Human Editorial Director",
            "verdict": "EDITORIAL_REVIEW_PENDING",
            "note": (
                "Machine verification attests technical, frame-exact cut continuity, audio loudness, and lineage truth only. "
                "Dramatic emotion, pacing feel, and audience engagement require human watch sign-off."
            ),
            "film": {
                "title": WG_TITLE,
                "subtitle": WG_SUBTITLE,
                "path": str(WG_MP4_PATH),
                "nominal_duration_sec": 30.0,
                "decoded_video_frames": WG_FRAMES,
                "launch_command": f'open "{WG_MP4_PATH}"',
            },
        }
        return "EDITORIAL_REVIEW_PENDING", details, None

    run_gate(
        "J13",
        "EDITORIAL_HUMAN_REVIEW",
        "scripts/test_v14_7_5_1_acceptance.py::check_j13",
        ["tests/evidence/v14_7_5_1/EDITORIAL_REVIEW_PACKET.md"],
        check_j13,
    )

    self_checks = run_failure_injection_self_checks()
    elapsed = round(time.perf_counter() - t_suite0, 3)

    mandatory_gates = [g for g in gates if g.gate_id != "J13"]
    j13_gate = next((g for g in gates if g.gate_id == "J13"), None)
    blocked_gates = [g.gate_id for g in mandatory_gates if g.status.startswith("BLOCKED")]
    tech_all_passed = (
        len(mandatory_gates) == 8
        and all(g.status == "PASS" for g in mandatory_gates)
        and j13_gate is not None
        and j13_gate.status == "EDITORIAL_REVIEW_PENDING"
        and self_checks.get("all_self_checks_passed") is True
    )
    if blocked_gates:
        master_status = "BLOCKED_RESOURCE"
    elif tech_all_passed:
        master_status = "TECH_VERIFIED_PENDING_EDITORIAL"
    else:
        master_status = "FAIL"

    acceptance_payload = {
        "evidence_schema_version": "14.7.5.1",
        "release": "V14.7.5.1",
        "fl_initiative": "FL-01",
        "run_id": effective_run_id,
        "title": WG_TITLE,
        "subtitle": WG_SUBTITLE,
        "timestamp": _iso_utc(),
        "elapsed_sec": elapsed,
        "master_status": master_status,
        "tech_all_passed": tech_all_passed,
        "editorial_status": j13_gate.status if j13_gate else "EDITORIAL_REVIEW_PENDING",
        "total_gates": len(gates),
        "mandatory_technical_gates_total": len(mandatory_gates),
        "mandatory_technical_gates_passed": sum(1 for g in mandatory_gates if g.status == "PASS"),
        "failed_or_unverified_gates": [g.gate_id for g in mandatory_gates if g.status != "PASS"],
        "failure_injection_self_checks": self_checks,
        "gates": [g.to_dict() for g in gates],
    }

    out_p = ev_dir / "00_acceptance.json"
    tmp_p = out_p.with_suffix(f".{os.getpid()}.tmp")
    tmp_p.write_text(json.dumps(acceptance_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_p, out_p)

    print("\n" + "=" * 84)
    print(
        f"V14.7.5.1 MASTER ACCEPTANCE: {acceptance_payload['mandatory_technical_gates_passed']}/8 TECH GATES PASS | "
        f"J13={acceptance_payload['editorial_status']} | MASTER={master_status}"
    )
    print(f"Evidence: {out_p}")
    print("=" * 84)
    return acceptance_payload


if __name__ == "__main__":
    rep = run_v14_7_5_1_acceptance_suite()
    sys.exit(0 if rep["tech_all_passed"] else 1)
