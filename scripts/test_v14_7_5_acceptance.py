#!/usr/bin/env python3
"""scripts/test_v14_7_5_acceptance.py — Evidence-Driven Master Acceptance Suite (FL-01 / V14.7.5).

Validates the 8 Mandatory Technical Gates (R1–R8), Independent Human Gate (J13),
and Internal Consistency / Failure-Injection Self-Checks:
- R1: NO_UNINTENDED_TELEPORT (decoded cut-boundary + >=4-8fps dynamic frame tracking + causal cut whitelist)
- R2: ACTOR_ID_APPEARANCE_RATIO_POSITION (character bible <-> packs/squire/chara.js + decoded actor bbox stability + explicit silhouette uncertainty note)
- R3: CAMERA_CUT_VALIDITY (zero keyframe snap + decoded pixel boundary delta audit + camera grammar diversity + negative snap control)
- R4: NARRATION_ACTION_ALIGNMENT_CAUSALITY (recomputed 0ms speech overlap from intervals, tail_margin >= 0.25s, zero atempo, ffprobe duration match, causal sequence)
- R5: NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR (mandatory render.log + render_receipt.json, zero error tokens, decoded pixel verification of diagram & summary card)
- R6: GEMINI_FALLBACK_PROVENANCE (receipt provenance OFFLINE_ONLY / REAL_RENDER + isolated secret-store fail-closed matrix)
- R7: VERIFIED_MP4_MEDIA_VISUAL (full decode 1080p24 H.264/AAC, 50-58s, -14 LUFS loudness, unclipped final spoken line, verified cache receipt, 3 decoded contact sheets)
- R8: FULL_REGRESSION_BACKTEST_RESOURCE (real run_e2e_regression.py FLOW_READY ledger, nonzero DAG jobs with measured overlap, 4 subprocess mutations killed, real video repair PASS, 7 preserved prior MP4 SHA256s intact, >=6.0 GiB disk floor, historical_180_real_replay=NOT_AVAILABLE reported honestly)
- J13: EDITORIAL_REVIEW_PENDING (never auto-passed by machine)
"""

from __future__ import annotations

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
    collect_render_inputs,
    inspect_media_file,
    sha256_file,
    validate_cache_hit,
    verify_receipt_and_lineage,
)
from scripts.qa_scheduler import inspect_resource_budget
from tools.ai_director import resolve_ai_director_policy
from tools.cinematic_camera import (
    audit_camera_grammar,
    audit_camera_snap_keyframes,
    plan_camera_sequence,
    validate_camera_sequence,
)
from tools.global_settings import InMemorySecretStore, isolated_secret_store
from tools.produce_fl01_v14_7_5_roman_eagle_in_fog_preview import (
    OUT_MP4_PATH as EAGLE_MP4_PATH,
    PROJECT_DIR as EAGLE_PROJECT_DIR,
    compute_measured_voice_overlaps,
    inspect_eagle_preview,
)
from tools.temporal_visual_qa import (
    audit_project_temporal_visual,
    validate_actor_presets,
)
from tools.visual_qa_v14_6 import audit_tactical_labels_mobile, extract_frame_at_time

EVIDENCE_DIR = ROOT_DIR / "tests" / "evidence" / "v14_7_5"


class GateResult:
    def __init__(
        self,
        gate_id: str,
        name: str,
        status: str,
        details: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        self.gate_id = gate_id
        self.name = name
        self.status = status  # PASS, FAIL, NOT_VERIFIED, BLOCKED, EDITORIAL_REVIEW_PENDING
        self.details = details
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "error": self.error,
        }


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _evaluate_voice_intervals_truth(events: List[Dict[str, Any]], min_tail_floor: float = 0.25) -> Dict[str, Any]:
    """Pure validator used both for R4 and failure-injection self-testing."""
    if not events:
        return {"valid": False, "status": "NOT_VERIFIED", "reason": "Empty voice events"}
    overlap_ms = compute_measured_voice_overlaps(events)
    recomputed_tails = [
        round(float(e["shot_end"]) - float(e["spoken_end"]), 4)
        for e in events
    ]
    recomputed_leads = [
        round(float(e["spoken_start"]) - float(e["shot_start"]), 4)
        for e in events
    ]
    min_tail = min(recomputed_tails)
    min_lead = min(recomputed_leads)
    atempo_any = any(bool(e.get("atempo_applied", False)) for e in events)
    ok = (overlap_ms == 0.0) and (min_tail >= min_tail_floor) and (min_lead >= 0.05) and (not atempo_any)
    return {
        "valid": ok,
        "status": "PASS" if ok else "FAIL",
        "recomputed_overlap_ms": overlap_ms,
        "min_tail_margin_sec": round(min_tail, 3),
        "max_tail_margin_sec": round(max(recomputed_tails), 3),
        "min_lead_in_sec": round(min_lead, 3),
        "atempo_used_anywhere": atempo_any,
    }


def run_failure_injection_self_checks() -> Dict[str, Any]:
    """Verify gate validators fail closed when overlap, render log, or DAG job count is corrupted."""
    # 1. Overlap corruption must FAIL _evaluate_voice_intervals_truth
    corrupted_events = [
        {"shot_start": 0.0, "shot_end": 4.0, "spoken_start": 0.3, "spoken_end": 3.9},
        {"shot_start": 4.0, "shot_end": 8.0, "spoken_start": 3.7, "spoken_end": 6.5},
    ]
    ov_res = _evaluate_voice_intervals_truth(corrupted_events)
    overlap_caught = (ov_res["status"] == "FAIL" and ov_res["recomputed_overlap_ms"] > 150.0)

    # 2. Empty voice events must return NOT_VERIFIED
    empty_res = _evaluate_voice_intervals_truth([])
    empty_caught = (empty_res["status"] == "NOT_VERIFIED")

    # 3. Camera 1-frame snap must be caught
    snap_caught, _ = audit_camera_snap_keyframes(
        [
            {"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.0},
            {"t": 1.0, "x": 0.20, "y": 0.50, "z": 1.0},
            {"t": 1.04, "x": 0.86, "y": 0.50, "z": 1.0},
        ]
    )

    # 4. Unknown preset must fail validate_actor_presets
    preset_ok, preset_diags = validate_actor_presets(
        {"id": "s_bad", "args": {"people": [{"id": "x", "preset": "nonexistent_alien_preset"}]}},
        pack_name="squire",
    )
    preset_caught = (not preset_ok) and any("UNKNOWN_ACTOR_PRESET" in d for d in preset_diags)

    all_ok = bool(overlap_caught and empty_caught and snap_caught and preset_caught)
    return {
        "all_self_checks_passed": all_ok,
        "overlap_corruption_caught": overlap_caught,
        "empty_events_not_verified": empty_caught,
        "camera_snap_caught": bool(snap_caught),
        "unknown_preset_caught": preset_caught,
    }


def run_v14_7_5_acceptance_suite(evidence_dir: Path = EVIDENCE_DIR) -> Dict[str, Any]:
    """Execute all R1–R8 mandatory technical gates + J13 editorial gate + consistency audit."""
    t_start = time.perf_counter()
    ev_dir = Path(evidence_dir).resolve()
    ev_dir.mkdir(parents=True, exist_ok=True)
    gates: List[GateResult] = []

    # Load or run decoded Temporal Visual QA on Eagle in the Fog once and persist 10_eagle_fog_temporal_qa.json
    temporal_json_p = ev_dir / "10_eagle_fog_temporal_qa.json"
    temporal_report = audit_project_temporal_visual(
        project_dir=EAGLE_PROJECT_DIR,
        mp4_path=EAGLE_MP4_PATH,
        output_evidence_dir=ev_dir / "eagle_temporal_work",
        run_negative_suite=True,
    )
    tmp_tq = temporal_json_p.with_suffix(f".{os.getpid()}.tmp")
    tmp_tq.write_text(temporal_report.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_tq, temporal_json_p)

    def gate(gate_id: str, name: str, fn: Callable[[], Tuple[str, Dict[str, Any], Optional[str]]]) -> None:
        try:
            status, details, err = fn()
            gr = GateResult(gate_id, name, status, details, err)
            gates.append(gr)
            mark = "PASS" if status == "PASS" else ("PENDING" if "PENDING" in status else status)
            print(f"[{mark}] Gate {gate_id}: {name} -> {status}")
            if err:
                print(f"    Reason: {err}")
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            gr = GateResult(gate_id, name, "FAIL", {"exception": str(exc)}, tb)
            gates.append(gr)
            print(f"[FAIL] Gate {gate_id}: {name} -> EXCEPTION: {exc}")

    # =========================================================================
    # Gate R1: NO_UNINTENDED_TELEPORT
    # =========================================================================
    def check_r1() -> Tuple[str, Dict[str, Any], Optional[str]]:
        shots_file = EAGLE_PROJECT_DIR / "story" / "shots.json"
        if not shots_file.is_file():
            return "NOT_VERIFIED", {}, f"Missing {shots_file}"
        shots = json.loads(shots_file.read_text(encoding="utf-8")).get("shots", [])
        if not shots or temporal_report.total_frames_sampled == 0:
            return "NOT_VERIFIED", {}, "Zero shots or zero decoded temporal frames sampled"

        cross_shot_violations: List[str] = []
        for i in range(len(shots) - 1):
            s_c = shots[i]
            s_n = shots[i + 1]
            ppl_c = {p["id"]: p for p in s_c.get("args", {}).get("people", []) if isinstance(p, dict) and p.get("id")}
            ppl_n = {p["id"]: p for p in s_n.get("args", {}).get("people", []) if isinstance(p, dict) and p.get("id")}
            common = set(ppl_c.keys()) & set(ppl_n.keys())
            causal_whitelisted = bool(s_n.get("causal_cut_reason"))
            for aid in common:
                xc = float(ppl_c[aid].get("to", ppl_c[aid].get("x", 0.5)))
                xn = float(ppl_n[aid].get("from", ppl_n[aid].get("x", 0.5)))
                dx = abs(xn - xc)
                same_tpl = s_c.get("tpl") == s_n.get("tpl")
                if same_tpl and dx > 0.42 and not causal_whitelisted:
                    cross_shot_violations.append(
                        f"Cut {s_c['id']}->{s_n['id']}: unwhitelisted actor '{aid}' jump dx={dx:.2f}"
                    )

        dynamic_densities = {
            sid: aud.sampling_fps_achieved
            for sid, aud in temporal_report.shot_audits.items()
            if aud.sampling_fps_achieved >= 4.0
        }
        within_shot_teleports = [
            sid for sid, aud in temporal_report.shot_audits.items() if aud.teleport_detected
        ]
        within_shot_disappearances = [
            sid for sid, aud in temporal_report.shot_audits.items() if aud.sudden_disappearance
        ]

        details = {
            "temporal_verdict": temporal_report.technical_verdict,
            "passed_shots": temporal_report.passed_shots,
            "total_shots": temporal_report.total_shots,
            "total_frames_sampled": temporal_report.total_frames_sampled,
            "expected_cut_count": temporal_report.expected_cut_count,
            "audited_cut_count": temporal_report.audited_cut_count,
            "unaudited_cuts": temporal_report.unaudited_cuts,
            "full_boundary_coverage": temporal_report.full_boundary_coverage,
            "dynamic_shot_sampling_fps": dynamic_densities,
            "within_shot_teleports": within_shot_teleports,
            "within_shot_disappearances": within_shot_disappearances,
            "cross_cut_boundary_audits_count": len(temporal_report.cross_cut_boundary_audits),
            "cross_shot_violations": cross_shot_violations,
        }
        if temporal_report.technical_verdict == "NOT_VERIFIED":
            return "NOT_VERIFIED", details, "Temporal Visual QA returned NOT_VERIFIED"
        if (
            temporal_report.technical_verdict != "VISUAL_TECH_PASS"
            or not temporal_report.full_boundary_coverage
            or temporal_report.audited_cut_count != max(0, len(shots) - 1)
            or temporal_report.unaudited_cuts
            or cross_shot_violations
            or within_shot_teleports
            or within_shot_disappearances
        ):
            return "FAIL", details, f"Continuity/temporal QA issues: {temporal_report.temporal_issues or cross_shot_violations}"
        return "PASS", details, None

    gate("R1", "NO_UNINTENDED_TELEPORT", check_r1)

    # =========================================================================
    # Gate R2: ACTOR_ID_APPEARANCE_RATIO_POSITION
    # =========================================================================
    def check_r2() -> Tuple[str, Dict[str, Any], Optional[str]]:
        bible_f = EAGLE_PROJECT_DIR / "story" / "character_bible.json"
        shots_f = EAGLE_PROJECT_DIR / "story" / "shots.json"
        if not bible_f.is_file() or not shots_f.is_file():
            return "NOT_VERIFIED", {}, "Missing character_bible.json or shots.json"

        chara_js = (ROOT_DIR / "packs" / "squire" / "chara.js").read_text(encoding="utf-8")
        cast_presets = set(re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:\s*K\(", chara_js, flags=re.MULTILINE))
        bible = json.loads(bible_f.read_text(encoding="utf-8")).get("characters", {})
        shots = json.loads(shots_f.read_text(encoding="utf-8")).get("shots", [])

        bible_invalid = [
            cid for cid, info in bible.items() if info.get("preset") not in cast_presets
        ]
        preset_drift: List[str] = []
        for s in shots:
            for p in s.get("args", {}).get("people", []):
                if not isinstance(p, dict):
                    continue
                pid = p.get("id")
                if pid in bible and p.get("preset") != bible[pid]["preset"]:
                    preset_drift.append(
                        f"{s['id']}:{pid} expected preset '{bible[pid]['preset']}', got '{p.get('preset')}'"
                    )

        # Decoded actor bounding-box height ratio & position audit across scene shots
        decoded_ratios: Dict[str, float] = {}
        ratio_outliers: List[str] = []
        for sid, aud in temporal_report.shot_audits.items():
            if aud.expected_subject == "actor" and aud.bounds and aud.bounds.detected:
                h_ratio = round(aud.bounds.ymax - aud.bounds.ymin, 3)
                decoded_ratios[sid] = h_ratio
                if aud.tpl == "scene" and not (0.20 <= h_ratio <= 0.92):
                    ratio_outliers.append(f"{sid}: abnormal actor height ratio {h_ratio}")

        details = {
            "cast_presets_count": len(cast_presets),
            "bible_characters_verified": list(bible.keys()),
            "bible_invalid_presets": bible_invalid,
            "shot_preset_drift": preset_drift,
            "decoded_actor_height_ratios": decoded_ratios,
            "ratio_outliers": ratio_outliers,
            "no_clipped_heads": temporal_report.no_clipped_heads,
            "framing_safe_all": temporal_report.framing_safe_all,
            "silhouette_manual_uncertainty": (
                "2D Squire helmeted silhouettes share stylized proportions; fine emblem/facial continuity "
                "remains subject to J13 human editorial sign-off."
            ),
        }
        if not decoded_ratios:
            return "NOT_VERIFIED", details, "No decoded actor bounding boxes measured"
        if bible_invalid or preset_drift or ratio_outliers or not temporal_report.framing_safe_all:
            return "FAIL", details, f"Actor identity/ratio/framing error: {bible_invalid or preset_drift or ratio_outliers}"
        return "PASS", details, None

    gate("R2", "ACTOR_ID_APPEARANCE_RATIO_POSITION", check_r2)

    # =========================================================================
    # Gate R3: CAMERA_CUT_VALIDITY
    # =========================================================================
    def check_r3() -> Tuple[str, Dict[str, Any], Optional[str]]:
        shots_f = EAGLE_PROJECT_DIR / "story" / "shots.json"
        shots = json.loads(shots_f.read_text(encoding="utf-8")).get("shots", [])
        snap_violations: List[str] = []
        for s in shots:
            kfs = (s.get("args", {}) or {}).get("cameraRig", {}).get("keyframes", [])
            snap_det, snap_diags = audit_camera_snap_keyframes(kfs)
            if snap_det:
                snap_violations.append(f"{s['id']}: {snap_diags}")

        cam_plans = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
        valid_seq, seq_errors = validate_camera_sequence(cam_plans, shots)
        grammar_rep = audit_camera_grammar(cam_plans)

        # Verify decoded cut boundary pixel deltas exist and show genuine non-frozen visual cuts
        boundary_audits = temporal_report.cross_cut_boundary_audits
        frozen_cuts = [
            b["cut"] for b in boundary_audits if float(b.get("pixel_mean_abs_delta", 0.0)) < 0.5
        ]

        # Negative control: 1-frame snap MUST be flagged
        neg_snap_caught, _ = audit_camera_snap_keyframes(
            [{"t": 0.0, "x": 0.5, "y": 0.5, "z": 1.0}, {"t": 0.04, "x": 0.9, "y": 0.5, "z": 1.0}]
        )

        details = {
            "within_shot_snap_violations": snap_violations,
            "camera_sequence_valid": valid_seq,
            "sequence_errors": seq_errors,
            "unique_viewpoints": grammar_rep.get("unique_viewpoints"),
            "diverse_grammar_verified": grammar_rep.get("diverse_grammar_verified"),
            "expected_cut_count": max(0, len(shots) - 1),
            "decoded_cut_boundaries_checked": len(boundary_audits),
            "full_boundary_coverage": temporal_report.full_boundary_coverage,
            "unaudited_cuts": temporal_report.unaudited_cuts,
            "frozen_cuts": frozen_cuts,
            "negative_snap_control_caught": bool(neg_snap_caught),
        }
        if len(boundary_audits) < max(0, len(shots) - 1) or not temporal_report.full_boundary_coverage:
            return "FAIL" if len(boundary_audits) > 0 else "NOT_VERIFIED", details, (
                f"Incomplete cut-boundary coverage: {len(boundary_audits)}/{max(0, len(shots) - 1)} cuts audited"
            )
        if (
            snap_violations
            or not valid_seq
            or not grammar_rep.get("diverse_grammar_verified")
            or frozen_cuts
            or not neg_snap_caught
        ):
            return "FAIL", details, f"Camera/cut audit failed: {snap_violations or seq_errors or frozen_cuts}"
        return "PASS", details, None

    gate("R3", "CAMERA_CUT_VALIDITY", check_r3)

    # =========================================================================
    # Gate R4: NARRATION_ACTION_ALIGNMENT_CAUSALITY
    # =========================================================================
    def check_r4() -> Tuple[str, Dict[str, Any], Optional[str]]:
        voice_json_p = EAGLE_PROJECT_DIR / "timeline" / "timeline_voice_events.json"
        voice_wav_p = EAGLE_PROJECT_DIR / "build" / "voice_track.wav"
        shots_f = EAGLE_PROJECT_DIR / "story" / "shots.json"
        if not voice_json_p.is_file() or not voice_wav_p.is_file() or not shots_f.is_file():
            return "NOT_VERIFIED", {}, "Missing timeline_voice_events.json, voice_track.wav, or shots.json"

        v_ledger = json.loads(voice_json_p.read_text(encoding="utf-8"))
        events = v_ledger.get("events", [])
        truth = _evaluate_voice_intervals_truth(events, min_tail_floor=0.25)

        wav_info = inspect_media_file(voice_wav_p, require_audio=True, full_decode=True, require_video=False)
        mp4_info = inspect_media_file(EAGLE_MP4_PATH, require_audio=True, full_decode=False)
        timeline_dur = float(v_ledger.get("total_timeline_duration_sec") or 0.0)
        wav_dur = float(wav_info.get("duration") or 0.0)
        mp4_dur = float(mp4_info.get("duration") or 0.0)
        dur_drift_sec = round(max(abs(timeline_dur - wav_dur), abs(timeline_dur - mp4_dur)), 3)

        shots = json.loads(shots_f.read_text(encoding="utf-8")).get("shots", [])
        actions = [str(s.get("action_kind") or s.get("action") or "") for s in shots]
        required_chain = ["SLIP", "SIGNAL", "RESCUE_DASH", "BRACE", "LIFT_STANDARD", "REFORM", "RAISE_STANDARD"]
        chain_indices: List[int] = []
        cur_pos = 0
        for req_act in required_chain:
            found_idx = -1
            for k in range(cur_pos, len(actions)):
                if actions[k] == req_act:
                    found_idx = k
                    cur_pos = k + 1
                    break
            chain_indices.append(found_idx)
        causal_chain_ok = all(idx >= 0 for idx in chain_indices) and chain_indices == sorted(chain_indices)

        details = {
            "speech_provider": v_ledger.get("speech_provider"),
            "beats_count": len(events),
            "recomputed_overlap_ms": truth["recomputed_overlap_ms"],
            "min_tail_margin_sec": truth["min_tail_margin_sec"],
            "max_tail_margin_sec": truth["max_tail_margin_sec"],
            "min_lead_in_sec": truth["min_lead_in_sec"],
            "atempo_used_anywhere": truth["atempo_used_anywhere"],
            "timeline_duration_sec": timeline_dur,
            "voice_wav_duration_sec": wav_dur,
            "mp4_duration_sec": mp4_dur,
            "duration_drift_sec": dur_drift_sec,
            "actions_sequence": actions,
            "required_causal_chain": required_chain,
            "causal_chain_indices": chain_indices,
            "causal_chain_verified": causal_chain_ok,
        }
        if truth["status"] == "NOT_VERIFIED":
            return "NOT_VERIFIED", details, truth.get("reason")
        if not truth["valid"] or not wav_info.get("valid") or dur_drift_sec > 0.15 or not causal_chain_ok:
            return "FAIL", details, "Voice overlap/tail margin/duration alignment or action causality failed"
        return "PASS", details, None

    gate("R4", "NARRATION_ACTION_ALIGNMENT_CAUSALITY", check_r4)

    # =========================================================================
    # Gate R5: NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR
    # =========================================================================
    def check_r5() -> Tuple[str, Dict[str, Any], Optional[str]]:
        log_file = EAGLE_PROJECT_DIR / "build" / "render.log"
        receipt_file = EAGLE_PROJECT_DIR / "build" / "render_receipt.json"
        shots_f = EAGLE_PROJECT_DIR / "story" / "shots.json"
        if not log_file.is_file() or not receipt_file.is_file() or not shots_f.is_file():
            return "NOT_VERIFIED", {
                "render_log_exists": log_file.is_file(),
                "render_receipt_exists": receipt_file.is_file(),
            }, "Mandatory build/render.log or build/render_receipt.json missing"

        log_text = log_file.read_text(encoding="utf-8")
        forbidden_tokens = [
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
        found_errors = [tok for tok in forbidden_tokens if tok in log_text]

        # Pixel-level verification of diagram shot (s06) and payoff takeaway card shot (s12)
        shots = json.loads(shots_f.read_text(encoding="utf-8")).get("shots", [])
        shots_by_id = {s["id"]: s for s in shots}
        pixel_checks: Dict[str, Any] = {}
        with tempfile.TemporaryDirectory() as td:
            for sid in ("s06", "s12"):
                s = shots_by_id[sid]
                mid_t = round((float(s["start"]) + float(s["end"])) * 0.5, 2)
                png_p = Path(td) / f"{sid}_mid.png"
                ok = extract_frame_at_time(EAGLE_MP4_PATH, mid_t, png_p)
                if not ok or not png_p.is_file():
                    return "NOT_VERIFIED", {}, f"Failed to decode {sid} frame at {mid_t}s"
                with Image.open(png_p) as im:
                    arr = np.array(im.convert("RGB"))
                mob_ok, mob_diags = audit_tactical_labels_mobile(arr)
                pixel_checks[sid] = {
                    "timestamp_sec": mid_t,
                    "mobile_legible": mob_ok,
                    "mean_luma": round(float(np.mean(arr)), 2),
                    "std_luma": round(float(np.std(arr)), 2),
                    "diagnostics": mob_diags,
                }

        details = {
            "render_log_bytes": log_file.stat().st_size,
            "forbidden_tokens_found": found_errors,
            "decoded_overlay_pixel_checks": pixel_checks,
            "all_shots_non_empty": all(a.non_empty_content for a in temporal_report.shot_audits.values()),
        }
        if (
            found_errors
            or not all(v["mobile_legible"] for v in pixel_checks.values())
            or not details["all_shots_non_empty"]
        ):
            return "FAIL", details, f"Render log errors or unreadable diagram/card pixels: {found_errors or pixel_checks}"
        return "PASS", details, None

    gate("R5", "NO_PLACEHOLDER_OR_HIDDEN_RENDER_ERROR", check_r5)

    # =========================================================================
    # Gate R6: GEMINI_FALLBACK_PROVENANCE
    # =========================================================================
    def check_r6() -> Tuple[str, Dict[str, Any], Optional[str]]:
        receipt_file = EAGLE_PROJECT_DIR / "build" / "render_receipt.json"
        if not receipt_file.is_file():
            return "NOT_VERIFIED", {}, "Missing build/render_receipt.json"

        rcpt = json.loads(receipt_file.read_text(encoding="utf-8"))
        prov = rcpt.get("provenance", {})
        actual_ai_mode = prov.get("ai_director_mode")
        actual_live_used = prov.get("ai_director_live_used")
        actual_render_mode = prov.get("render_mode")

        # Isolated policy matrix checks (no ambient secret leakage)
        matrix_results: Dict[str, Any] = {}
        saved_test_mode = os.environ.get("QA_STUDIO_TEST_MODE")
        os.environ["QA_STUDIO_TEST_MODE"] = "1"
        try:
            with isolated_secret_store(InMemorySecretStore(initial_key=None)):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_p = Path(tmp_dir)
                    (tmp_p / "config.json").write_text(
                        json.dumps({"ai_director_mode": "OFFLINE_ONLY", "ai_director_enabled": True}),
                        encoding="utf-8",
                    )
                    p1 = resolve_ai_director_policy(tmp_p)
                    matrix_results["OFFLINE_ONLY"] = p1.get("mode")

                    (tmp_p / "config.json").write_text(
                        json.dumps({"ai_director_mode": "LIVE_REQUIRED", "force_test_live": True}),
                        encoding="utf-8",
                    )
                    p2 = resolve_ai_director_policy(tmp_p)
                    matrix_results["LIVE_REQUIRED_NO_KEY"] = (
                        p2.get("mode") == "LIVE_REQUIRED" and not p2.get("has_key")
                    )

                    (tmp_p / "story").mkdir(parents=True, exist_ok=True)
                    (tmp_p / "story" / "shots.json").write_text(
                        json.dumps({"shots": [{"id": "s01", "dur": 3.0}]}),
                        encoding="utf-8",
                    )
                    env_no_key = dict(os.environ)
                    env_no_key.pop("GEMINI_API_KEY", None)
                    res_cli = subprocess.run(
                        [sys.executable, "tools/assign_visuals.py", "--project", str(tmp_p)],
                        cwd=ROOT_DIR,
                        env=env_no_key,
                        capture_output=True,
                    )
                    matrix_results["CLI_LIVE_REQUIRED_FAIL_CLOSED"] = (res_cli.returncode != 0)
        finally:
            if saved_test_mode is None:
                os.environ.pop("QA_STUDIO_TEST_MODE", None)
            else:
                os.environ["QA_STUDIO_TEST_MODE"] = saved_test_mode

        details = {
            "production_receipt_render_mode": actual_render_mode,
            "production_receipt_ai_director_mode": actual_ai_mode,
            "production_receipt_ai_director_live_used": actual_live_used,
            "policy_matrix": matrix_results,
        }
        ok = (
            actual_render_mode in ("REAL_RENDER", "CACHE_HIT_VERIFIED")
            and actual_ai_mode == "OFFLINE_ONLY"
            and actual_live_used is False
            and matrix_results.get("OFFLINE_ONLY") == "OFFLINE_ONLY"
            and matrix_results.get("LIVE_REQUIRED_NO_KEY") is True
            and matrix_results.get("CLI_LIVE_REQUIRED_FAIL_CLOSED") is True
        )
        if not ok:
            return "FAIL", details, "Provenance or Gemini fail-closed policy matrix check failed"
        return "PASS", details, None

    gate("R6", "GEMINI_FALLBACK_PROVENANCE", check_r6)

    # =========================================================================
    # Gate R7: VERIFIED_MP4_MEDIA_VISUAL
    # =========================================================================
    def check_r7() -> Tuple[str, Dict[str, Any], Optional[str]]:
        if not EAGLE_MP4_PATH.is_file():
            return "NOT_VERIFIED", {}, f"Missing {EAGLE_MP4_PATH}"

        eagle_check = inspect_eagle_preview(EAGLE_PROJECT_DIR, EAGLE_MP4_PATH)
        lineage = verify_receipt_and_lineage(
            EAGLE_PROJECT_DIR,
            EAGLE_MP4_PATH,
            expected_specs={"width": 1920, "height": 1080, "fps": 24.0, "min_duration": 50.0, "max_duration": 58.0, "require_audio": True},
        )
        mi = eagle_check.get("media_info", {})
        lufs = mi.get("integrated_lufs")
        tp = mi.get("true_peak_dbtp")
        loudness_ok = (lufs is not None) and (-16.8 <= float(lufs) <= -11.2)
        tp_ok = (tp is not None) and (float(tp) <= -0.5)

        # Verify final spoken line in s12 is audible and unclipped inside the muxed MP4
        v_ledger = json.loads(
            (EAGLE_PROJECT_DIR / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8")
        )
        last_ev = v_ledger["events"][-1]
        tail_seg_cmd = [
            "ffmpeg",
            "-ss",
            f"{last_ev['spoken_start']:.3f}",
            "-to",
            f"{last_ev['spoken_end']:.3f}",
            "-i",
            str(EAGLE_MP4_PATH),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ]
        tail_res = subprocess.run(tail_seg_cmd, capture_output=True, text=True)
        m_tail_mean = re.search(r"mean_volume:\s+([-\d.]+)\s+dB", tail_res.stderr)
        tail_mean_db = float(m_tail_mean.group(1)) if m_tail_mean else -99.0
        final_line_audible = (
            tail_mean_db > -38.0
            and float(last_ev["spoken_end"]) <= float(mi.get("duration", 0.0)) - 0.25
        )

        # Verify all 3 decoded PNG contact sheets exist and are non-empty
        sheets_ok = True
        sheet_info: Dict[str, Any] = {}
        for sname in ("contact_sheet_full.png", "contact_sheet_hook.png", "contact_sheet_action.png"):
            sp = EAGLE_PROJECT_DIR / "out" / sname
            if not sp.is_file() or sp.stat().st_size < 5000:
                sheets_ok = False
                sheet_info[sname] = {"exists": False}
            else:
                with Image.open(sp) as sim:
                    sarr = np.array(sim.convert("RGB"))
                    sheet_info[sname] = {
                        "exists": True,
                        "size_bytes": sp.stat().st_size,
                        "dimensions": list(sim.size),
                        "mean_luma": round(float(np.mean(sarr)), 2),
                    }
                    if float(np.std(sarr)) < 8.0:
                        sheets_ok = False

        details = {
            "evidence_schema_version": lineage.get("evidence_schema_version"),
            "mp4_path": str(EAGLE_MP4_PATH),
            "valid": eagle_check.get("valid"),
            "cache_status": eagle_check.get("cache_status"),
            "input_fingerprint": lineage.get("input_fingerprint"),
            "recomputed_input_fingerprint": lineage.get("recomputed_input_fingerprint"),
            "fingerprint_match": lineage.get("fingerprint_match"),
            "output_sha256": lineage.get("output_sha256"),
            "receipt_verified": lineage.get("receipt_verified"),
            "cache_verified": lineage.get("cache_verified"),
            "media_decode_verified": lineage.get("media_decode_verified"),
            "duration_sec": mi.get("duration"),
            "width": mi.get("width"),
            "height": mi.get("height"),
            "fps": mi.get("fps"),
            "video_codec": mi.get("video_codec"),
            "audio_codec": mi.get("audio_codec"),
            "integrated_lufs": lufs,
            "true_peak_dbtp": tp,
            "mean_volume_db": mi.get("mean_volume_db"),
            "final_line_mean_db": tail_mean_db,
            "final_line_audible_and_unclipped": final_line_audible,
            "sha256": mi.get("sha256"),
            "contact_sheets": sheet_info,
        }
        if (
            not eagle_check.get("valid")
            or lineage.get("status") != "PASS"
            or not lineage.get("receipt_verified")
            or not lineage.get("cache_verified")
            or not lineage.get("media_decode_verified")
            or not loudness_ok
            or not tp_ok
            or not final_line_audible
            or not sheets_ok
        ):
            return "FAIL", details, f"MP4 media/loudness/receipt/contact-sheet verification failed: {details}"
        return "PASS", details, None

    gate("R7", "VERIFIED_MP4_MEDIA_VISUAL", check_r7)

    # =========================================================================
    # Gate R8: FULL_REGRESSION_BACKTEST_RESOURCE
    # =========================================================================
    def check_r8() -> Tuple[str, Dict[str, Any], Optional[str]]:
        budget = inspect_resource_budget(min_disk_gb=6.0, min_ram_gb=1.0)
        if not budget["healthy"]:
            return "BLOCKED", budget, f"Host resource safety floor breached: {budget['message']}"

        e2e_ev = _load_json_if_exists(ev_dir / "05_e2e_regression_full.json")
        dag_ev = _load_json_if_exists(ev_dir / "03_real_async_dag_jobs.json")
        mut_ev = _load_json_if_exists(ev_dir / "04_mutation_actual_execution.json")
        rep_ev = _load_json_if_exists(ev_dir / "07_repair_loop_real_video.json")
        pres_ev = _load_json_if_exists(ev_dir / "08_old_films_preservation.json")
        hist_ev = _load_json_if_exists(ev_dir / "06_historical_backtest_truth.json")

        missing_ev = [
            name
            for name, obj in [
                ("05_e2e_regression_full.json", e2e_ev),
                ("03_real_async_dag_jobs.json", dag_ev),
                ("04_mutation_actual_execution.json", mut_ev),
                ("07_repair_loop_real_video.json", rep_ev),
                ("08_old_films_preservation.json", pres_ev),
                ("06_historical_backtest_truth.json", hist_ev),
            ]
            if obj is None
        ]
        if missing_ev:
            return "NOT_VERIFIED", {"missing_evidence_files": missing_ev}, f"Missing mandatory evidence: {missing_ev}"

        assert e2e_ev and dag_ev and mut_ev and rep_ev and pres_ev and hist_ev

        e2e_ok = (
            e2e_ev.get("exit_code") == 0
            and e2e_ev.get("verdict") == "FLOW_READY"
            and int(e2e_ev.get("required_gates_failed", 1)) == 0
            and int(e2e_ev.get("required_gates_passed", 0)) >= 80
        )
        cp = dag_ev.get("concurrency_proof") or {}
        overlap_cnt = int(cp.get("overlapping_pairs_count", cp.get("overlapping_job_pairs_count", 0)) or 0)
        dag_ok = (
            int(dag_ev.get("total_jobs", 0)) >= 5
            and dag_ev.get("all_succeeded") is True
            and overlap_cnt >= 1
        )
        mut_ok = (
            mut_ev.get("all_mutations_killed") is True
            and int(mut_ev.get("killed_mutations", 0)) >= 4
            and str(mut_ev.get("execution_mode", "")).startswith("disposable_subprocess")
        )
        rep_ok = (
            rep_ev.get("test_status") == "PASS"
            and rep_ev.get("mp4_rebuilt_and_changed") is True
            and rep_ev.get("manual_locked_preserved") is True
            and rep_ev.get("locked_defect_status") == "BLOCKED_MANUAL_REVIEW"
        )
        pres_ok = pres_ev.get("all_preserved_intact") is True

        # Enforce truthful separation: historical_180_real_replay == NOT_AVAILABLE must NEVER be counted as real replay PASS
        hist_180_real = hist_ev.get("historical_180_real_replay")
        synth_180 = hist_ev.get("synthetic_180_stress_gate_g5")
        hist_truth_ok = (
            hist_180_real in ("NOT_AVAILABLE", "PASS_REAL_FIXTURE")
            and hist_ev.get("counted_not_available_as_real_replay_pass") is False
            and synth_180 == "PASS"
        )

        details = {
            "resource_budget": budget,
            "e2e_run_id": e2e_ev.get("run_id"),
            "e2e_verdict": e2e_ev.get("verdict"),
            "e2e_required_passed": e2e_ev.get("required_gates_passed"),
            "e2e_required_total": e2e_ev.get("required_gates_total"),
            "dag_total_jobs": dag_ev.get("total_jobs"),
            "dag_overlapping_pairs": overlap_cnt,
            "mutations_killed": f"{mut_ev.get('killed_mutations')}/{mut_ev.get('total_mutations')}",
            "negative_fixtures_passed": f"{temporal_report.negative_fixtures_results.get('passed_fixtures')}/{temporal_report.negative_fixtures_results.get('total_fixtures')}",
            "shot_repair_real_video": rep_ev.get("test_status"),
            "preserved_prior_mp4s_intact": pres_ok,
            "synthetic_180_stress": synth_180,
            "historical_180_real_replay": hist_180_real,
            "counted_not_available_as_real_replay_pass": False,
        }
        if not (
            e2e_ok
            and dag_ok
            and mut_ok
            and rep_ok
            and pres_ok
            and hist_truth_ok
            and temporal_report.negative_fixtures_passed
        ):
            return "FAIL", details, f"R8 regression/DAG/mutation/repair/preservation check failed: {details}"
        return "PASS", details, None

    gate("R8", "FULL_REGRESSION_BACKTEST_RESOURCE", check_r8)

    # =========================================================================
    # Gate J13: Independent Creative Editorial Human Review Gate
    # =========================================================================
    def check_j13() -> Tuple[str, Dict[str, Any], Optional[str]]:
        details = {
            "reviewer": "USER / Human Editorial Director",
            "verdict": "EDITORIAL_REVIEW_PENDING",
            "note": "Machine verification confirms technical, geometric, audio, and continuity truth only. Dramatic emotion and editorial polish require human review.",
            "film": {
                "title": "THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE",
                "subtitle": "Illustrative Fictional Reconstruction",
                "path": str(EAGLE_MP4_PATH),
                "launch_command": f'open "{EAGLE_MP4_PATH}"',
            },
        }
        return "EDITORIAL_REVIEW_PENDING", details, None

    gate("J13", "EDITORIAL_HUMAN_REVIEW", check_j13)

    self_checks = run_failure_injection_self_checks()
    elapsed = round(time.perf_counter() - t_start, 3)

    mandatory_gates = [g for g in gates if g.gate_id != "J13"]
    j13_gate = next((g for g in gates if g.gate_id == "J13"), None)
    tech_all_passed = (
        all(g.status == "PASS" for g in mandatory_gates)
        and len(mandatory_gates) == 8
        and j13_gate is not None
        and j13_gate.status == "EDITORIAL_REVIEW_PENDING"
        and self_checks.get("all_self_checks_passed") is True
    )
    master_status = "TECH_VERIFIED_PENDING_EDITORIAL" if tech_all_passed else "FAIL"

    master_report = {
        "release": "V14.7.5",
        "fl_initiative": "FL-01",
        "title": "THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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

    out_master = ev_dir / "00_master_acceptance.json"
    tmp_m = out_master.with_suffix(f".{os.getpid()}.tmp")
    tmp_m.write_text(json.dumps(master_report, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_m, out_master)

    # Remove temporary decoded PNG scratch directory after persisting 10_eagle_fog_temporal_qa.json & 00_master_acceptance.json
    shutil.rmtree(ev_dir / "eagle_temporal_work", ignore_errors=True)

    print("\n" + "=" * 80)
    print(
        f"V14.7.5 MASTER ACCEPTANCE: {master_report['mandatory_technical_gates_passed']}/8 TECH GATES PASS | "
        f"J13={master_report['editorial_status']} | MASTER={master_status}"
    )
    print(f"Report: {out_master}")
    print("=" * 80)
    return master_report


if __name__ == "__main__":
    rep = run_v14_7_5_acceptance_suite()
    sys.exit(0 if rep["tech_all_passed"] else 1)
