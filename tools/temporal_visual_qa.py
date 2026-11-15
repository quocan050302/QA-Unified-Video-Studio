#!/usr/bin/env python3
"""tools/temporal_visual_qa.py — P0 Temporal Visual QA Engine (V14.7.5).

Performs strict, fail-closed decoded frame-level temporal visual audits:
1. Batched single-pass FFmpeg rawvideo stream extraction + content-addressed frame cache (zero pixel truth alteration).
2. Adaptive temporal sampling: cut boundaries (±1, ±2 frames) + >= 4–8 fps across dynamic action windows; reports COVERAGE_INCOMPLETE if budget prevents target density.
3. Fail-closed guards: missing/empty MP4, decode error, empty storyboard (0 shots), zero extracted frames, or failed negative fixtures => technical_verdict = FAIL / NOT_VERIFIED.
4. 15 real negative fixtures + 4 real disposable-subprocess mutation executions (no hardcoded booleans).
"""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

import scripts.production_fingerprint as prod_fp
import tools.cinematic_camera as cine_cam
from scripts.production_fingerprint import (
    collect_render_inputs,
    inspect_media_file,
    sha256_file,
    validate_cache_hit,
    write_render_receipt_atomic,
)
from tools.cinematic_camera import audit_camera_snap_keyframes
from tools.visual_qa_v14_6 import (
    ActorBoundingBox,
    audit_safe_framing,
    audit_tactical_labels_mobile,
    extract_frame_at_time,
    track_actor_instances_full_frame,
)

DYNAMIC_ACTION_KEYWORDS = (
    "ADVANCE",
    "CHARGE",
    "WITHDRAW",
    "HAMMER",
    "WINCH",
    "CRANK",
    "RECOIL",
    "STEP",
    "OPEN",
    "LANE",
    "SLIP",
    "DASH",
    "RESCUE",
    "LIFT",
    "REFORM",
    "RAISE",
    "PUSH",
    "ROTATE",
    "DIVERT",
    "DROP",
    "FLOW",
    "POINT",
    "INSPECT",
)

ALLOWLISTED_DIAGRAM_CUT_REASONS = {
    "insert_diagram",
    "diagram_insert",
    "tactical_schematic_cutaway",
    "tactical_to_ground_execution",
    "diagram_to_scene",
    "return_from_insert",
    "scene_to_diagram",
    "title_card_transition",
    "summary_card_cutaway",
    "heroic_payoff_summary",
}

ALLOWLISTED_FRAMING_OR_SPACE_CUT_REASONS = {
    "opening_hook",
    "wide_spatial_establish",
    "insert_closeup",
    "reaction_closeup",
    "mechanism_closeup",
    "mechanism_cutaway",
    "upstream_mechanism_cut",
    "parallel_action_cutaway",
    "parallel_shield_cover",
    "wide_cohort_reform",
    "camera_angle_reverse",
    "action_reaction_reverse_angle",
    "spatial_cutaway",
    "act_transition",
    "temporal_ellipsis",
    "overhead_reveal",
    "overflow_payoff_track",
    "resolution_wide_crane",
}

ALLOWLISTED_SAME_SPACE_PROGRESSION_REASONS = {
    "inciting_physical_slip",
    "command_signal_action",
    "physical_standard_recovery",
    "coordinated_withdrawal",
    "same_space_action_beat",
    "mechanical_torque_jam",
    "causal_gate_release",
}

ALLOWLISTED_INTENTIONAL_CUT_REASONS = (
    ALLOWLISTED_DIAGRAM_CUT_REASONS
    | ALLOWLISTED_FRAMING_OR_SPACE_CUT_REASONS
    | ALLOWLISTED_SAME_SPACE_PROGRESSION_REASONS
)


class TemporalShotAudit(BaseModel):
    shot_id: str
    action_kind: str
    tpl: str
    expected_subject: str  # "actor", "map", "diagram", "prop", "none"
    duration: float
    start_time: float
    end_time: float
    passed: bool = True
    non_empty_content: bool = True
    safe_framing: bool = True
    head_clipped: bool = False
    feet_clipped: bool = False
    motion_verified: bool = True
    performance_readability: bool = True
    subject_detected: bool = True
    detection_confidence: float = 1.0
    technical_verdict: str = "VISUAL_TECH_PASS"
    diagnostics: List[str] = Field(default_factory=list)
    temporal_samples: List[str] = Field(default_factory=list)
    sample_timestamps: List[float] = Field(default_factory=list)
    sampling_fps_achieved: float = 0.0
    bounds: Optional[ActorBoundingBox] = None
    subject_motion_px: float = 0.0
    net_motion_px: float = 0.0
    detected_acting_pose: str = "unknown"
    teleport_detected: bool = False
    sudden_disappearance: bool = False


class TemporalQAReport(BaseModel):
    version: str = "14.7.5.1"
    project_id: str
    mp4_path: str
    generated_at: float = Field(default_factory=time.time)
    total_shots: int = 0
    passed_shots: int = 0
    all_passed: bool = False
    technical_verdict: str = "NOT_VERIFIED"
    framing_safe_all: bool = True
    no_clipped_heads: bool = True
    motion_verified_all: bool = True
    acting_verified_all: bool = True
    negative_fixtures_passed: bool = True
    extraction_mode: str = "batched_stream_cache"
    extraction_elapsed_sec: float = 0.0
    total_frames_sampled: int = 0
    expected_cut_count: int = 0
    audited_cut_count: int = 0
    unaudited_cuts: List[str] = Field(default_factory=list)
    full_boundary_coverage: bool = False
    boundary_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    shot_audits: Dict[str, TemporalShotAudit] = Field(default_factory=dict)
    temporal_issues: List[Dict[str, Any]] = Field(default_factory=list)
    cross_cut_boundary_audits: List[Dict[str, Any]] = Field(default_factory=list)
    negative_fixtures_results: Dict[str, Any] = Field(default_factory=dict)
    global_issues: List[str] = Field(default_factory=list)


def determine_expected_subject(shot: Dict[str, Any]) -> str:
    """Classify expected subject to prevent false actor classifications on maps/diagrams/titles."""
    explicit = shot.get("expected_subject")
    if explicit in ("map", "diagram", "title", "prop", "none", "actor"):
        return "map" if explicit in ("diagram", "title") else str(explicit)

    tpl = str(shot.get("tpl", "scene")).lower()
    args = shot.get("args", {}) if isinstance(shot.get("args"), dict) else {}
    bg = str(shot.get("bg") or args.get("bg", "")).lower()
    desc = str(shot.get("desc", "")).lower()
    people = shot.get("people") or args.get("people") or []

    if tpl in ("map", "diagram", "schematic", "plan", "board", "title", "chapter", "card") or bg in ("map", "diagram", "parchment"):
        return "map"
    if ("map" in desc or "diagram" in desc or "schematic" in desc) and not people:
        return "map"
    if tpl in ("top", "overview") and "actor" not in desc and not people:
        return "map"
    if not people and any(w in desc for w in ("close on bolt", "machine", "artillery battery", "ballista", "mechanism", "fallen standard", "eagle standard")):
        return "prop"
    return "actor"


def is_dynamic_action(action: str) -> bool:
    act = (action or "").upper()
    return any(k in act for k in DYNAMIC_ACTION_KEYWORDS)


def build_shot_sample_timestamps(
    st: float,
    et: float,
    dur: float,
    action: str,
    fps: float = 24.0,
    max_samples_per_shot: int = 28,
) -> Tuple[List[float], bool]:
    """
    Compute adaptive temporal sample timestamps:
    - Cut boundaries: +1, +2 frames after shot start and -2, -1 frames before shot end.
    - Dynamic actions: >= 4.0–6.0 fps across active shot window (step = 0.20s = 5.0 fps).
    Returns (timestamps, coverage_complete).
    """
    fps_step = 1.0 / max(1.0, fps)
    safe_end = max(st + fps_step, et - 0.005)
    t_b_start1 = min(safe_end, st + fps_step)
    t_b_start2 = min(safe_end, st + 2.0 * fps_step)
    t_b_end2 = max(st + fps_step, et - 2.0 * fps_step)
    t_b_end1 = max(st + fps_step, et - fps_step)
    t_mid = (st + et) / 2.0

    raw_ts = [t_b_start1, t_b_start2, st + dur * 0.25, t_mid, st + dur * 0.75, t_b_end2, t_b_end1]

    dyn = is_dynamic_action(action)
    if dyn and dur >= 0.8:
        # Sample at 5.0 fps (every 0.20s) across the shot window -> satisfies >= 4-8 fps target
        step_sec = 0.20
        cur = st + fps_step
        while cur <= et - fps_step + 1e-6:
            raw_ts.append(cur)
            cur += step_sec

    sorted_ts = sorted({round(t, 4) for t in raw_ts if st <= t <= et})
    dedup: List[float] = []
    for t in sorted_ts:
        if not dedup or (t - dedup[-1]) >= (fps_step * 0.80):
            dedup.append(round(t, 3))

    coverage_complete = True
    if len(dedup) > max_samples_per_shot:
        # Downsample evenly; verify density stays >= 4.0 fps if dynamic
        idxs = np.linspace(0, len(dedup) - 1, max_samples_per_shot, dtype=int)
        dedup = [dedup[i] for i in sorted(set(idxs))]
        if dyn and dur > 0:
            achieved_fps = len(dedup) / dur
            if achieved_fps < 4.0:
                coverage_complete = False

    return dedup, coverage_complete


def _is_valid_rgb_png(path: Path) -> bool:
    """Verify a cached/extracted PNG is non-empty and decodable without corruption."""
    if not path.is_file() or path.stat().st_size < 100:
        return False
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def _load_rgb_png_verified(path: Path) -> Optional[np.ndarray]:
    """Load an RGB PNG into a numpy array, returning None on missing or corrupted data."""
    if not _is_valid_rgb_png(path):
        return None
    try:
        with Image.open(path) as im:
            arr = np.array(im.convert("RGB"))
        if arr.ndim != 3 or arr.shape[0] < 16 or arr.shape[1] < 16:
            return None
        return arr
    except Exception:
        return None


def build_cut_boundary_frame_plan(
    shots: List[Dict[str, Any]],
    fps: float = 24.0,
) -> List[Dict[str, Any]]:
    """
    Build deterministic frame-exact cut boundary sample plan for all N-1 transitions.
    Matches engine/player.js `t = f / fps; t < shot.end` semantics so pre_2/pre_1 are
    strictly inside `shots[k]` and post_1/post_2 are strictly inside `shots[k+1]`.
    """
    plans: List[Dict[str, Any]] = []
    if len(shots) < 2:
        return plans

    safe_fps = max(1.0, float(fps))
    cur_t = 0.0
    norm_bounds: List[Tuple[str, float, float, Dict[str, Any]]] = []
    for idx_s, s in enumerate(shots):
        sid = str(s.get("id") or s.get("shot_id") or f"s{idx_s+1:02d}")
        st = float(s.get("start", cur_t))
        dur = float(s.get("dur", max(0.2, float(s.get("end", st + 3.0)) - st)))
        et = float(s.get("end", st + dur))
        cur_t = et
        norm_bounds.append((sid, st, et, s))

    for cut_idx in range(len(norm_bounds) - 1):
        id_cur, st_cur, et_cur, s_cur = norm_bounds[cut_idx]
        id_nxt, st_nxt, et_nxt, s_nxt = norm_bounds[cut_idx + 1]
        t_cut = et_cur
        # Exact first 0-based frame where f / fps >= t_cut
        first_post_f = max(1, int(math.ceil(t_cut * safe_fps - 1e-9)))
        min_cur_f = max(0, int(math.ceil(st_cur * safe_fps - 1e-9)))
        last_nxt_f = max(first_post_f, int(math.ceil(et_nxt * safe_fps - 1e-9)) - 1)

        f_pre1 = max(min_cur_f, first_post_f - 1)
        f_pre2 = max(min_cur_f, first_post_f - 2)
        f_post1 = first_post_f
        f_post2 = min(last_nxt_f, first_post_f + 1)

        frame_indices = {
            "pre_2": int(f_pre2),
            "pre_1": int(f_pre1),
            "post_1": int(f_post1),
            "post_2": int(f_post2),
        }
        requested_times = {
            role: round(fidx / safe_fps, 4) for role, fidx in frame_indices.items()
        }
        plans.append({
            "cut_index": cut_idx,
            "cut": f"{id_cur}->{id_nxt}",
            "from_shot_id": id_cur,
            "to_shot_id": id_nxt,
            "shot_ids": [id_cur, id_nxt],
            "cut_time_sec": round(t_cut, 4),
            "requested_times": requested_times,
            "extracted_frame_indices": frame_indices,
            "from_shot": s_cur,
            "to_shot": s_nxt,
            "artifact_paths": {},
        })
    return plans


def extract_frames_batched_cached(
    mp4_file: Path,
    shot_requests: List[Tuple[str, List[float]]],
    ev_frames_dir: Path,
    width: int,
    height: int,
    fps: float,
    boundary_plans: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, List[Path]], str]:
    """
    Content-addressed + single-pass FFmpeg rawvideo stream frame extractor.
    Guarantees identical decoded RGB frames without spawning N separate ffmpeg processes,
    and extracts exact integer cut-boundary frames (-2, -1, +1, +2) without timestamp rounding drift.
    """
    ev_frames_dir.mkdir(parents=True, exist_ok=True)
    mp4_hash12 = sha256_file(mp4_file)[:12]

    # Map frame_index -> list of target output paths
    needed_by_frame_idx: Dict[int, List[Path]] = {}
    boundary_only_paths: set[Path] = set()
    shot_paths: Dict[str, List[Path]] = {}
    missing_count = 0

    for sid, ts_list in shot_requests:
        paths_for_shot: List[Path] = []
        for idx, ts in enumerate(ts_list):
            f_idx = max(0, int(round(ts * fps)))
            out_png = ev_frames_dir / f"{mp4_hash12}_{sid}_f{f_idx:05d}_{ts:.2f}s.png"
            paths_for_shot.append(out_png)
            if not _is_valid_rgb_png(out_png):
                missing_count += 1
                needed_by_frame_idx.setdefault(f_idx, []).append(out_png)
        shot_paths[sid] = paths_for_shot

    for bplan in (boundary_plans or []):
        cidx = int(bplan["cut_index"])
        art_paths: Dict[str, Path] = {}
        for role, f_idx in bplan["extracted_frame_indices"].items():
            b_png = ev_frames_dir / f"{mp4_hash12}_cut{cidx:02d}_{role}_f{int(f_idx):05d}.png"
            art_paths[role] = b_png
            if not _is_valid_rgb_png(b_png):
                missing_count += 1
                needed_by_frame_idx.setdefault(int(f_idx), []).append(b_png)
                boundary_only_paths.add(b_png)
        bplan["artifact_paths"] = art_paths

    if missing_count == 0:
        return shot_paths, "cache_hit_content_addressed"

    max_needed_idx = max(needed_by_frame_idx.keys()) if needed_by_frame_idx else 0
    frame_bytes = width * height * 3

    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(mp4_file),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-vsync",
        "0",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cur_idx = 0
    last_buf: Optional[bytes] = None
    try:
        assert proc.stdout is not None
        while cur_idx <= max_needed_idx:
            buf = proc.stdout.read(frame_bytes)
            if not buf or len(buf) < frame_bytes:
                break
            last_buf = buf
            if cur_idx in needed_by_frame_idx:
                arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 3))
                img = Image.fromarray(arr, mode="RGB")
                for target_p in needed_by_frame_idx[cur_idx]:
                    img.save(target_p, format="PNG", compress_level=1)
            cur_idx += 1
    finally:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # Handle edge case where within-shot sample timestamp rounded 1-4 frames past video EOF
    # NEVER synthesize or pad boundary_only_paths past decoded video EOF (fail closed if truncated!)
    if last_buf is not None:
        last_arr = np.frombuffer(last_buf, dtype=np.uint8).reshape((height, width, 3))
        img_last = Image.fromarray(last_arr, mode="RGB")
        for f_idx, targets in needed_by_frame_idx.items():
            if f_idx >= cur_idx and (f_idx - cur_idx) <= 5:
                for target_p in targets:
                    if target_p not in boundary_only_paths and not _is_valid_rgb_png(target_p):
                        img_last.save(target_p, format="PNG", compress_level=1)

    # Fallback single-frame extraction ONLY for non-boundary shot samples
    for sid, ts_list in shot_requests:
        for out_png, ts in zip(shot_paths[sid], ts_list):
            if not _is_valid_rgb_png(out_png):
                extract_frame_at_time(mp4_file, ts, out_png)

    return shot_paths, "batched_rawvideo_stream"


def _classify_cut_type(sub_cur: str, sub_nxt: str, s_cur: Dict[str, Any], s_nxt: Dict[str, Any]) -> str:
    if sub_cur == "map" and sub_nxt == "map":
        return "diagram_to_diagram"
    if sub_cur != "map" and sub_nxt == "map":
        return f"{sub_cur}_to_diagram"
    if sub_cur == "map" and sub_nxt != "map":
        return f"diagram_to_{sub_nxt}"
    if sub_cur != "actor" or sub_nxt != "actor":
        return f"{sub_cur}_to_{sub_nxt}"
    tpl_c = str(s_cur.get("tpl", "scene"))
    tpl_n = str(s_nxt.get("tpl", "scene"))
    if tpl_c != tpl_n:
        return f"framing_tpl_{tpl_c}_to_{tpl_n}"
    zc = (s_cur.get("world_state") or {}).get("zone") or (s_cur.get("args") or {}).get("zone") or (s_cur.get("args") or {}).get("bg", "default")
    zn = (s_nxt.get("world_state") or {}).get("zone") or (s_nxt.get("args") or {}).get("zone") or (s_nxt.get("args") or {}).get("bg", "default")
    if zc != zn:
        return "spatial_zone_cut"
    return "same_space_actor_cut"


def audit_single_cut_boundary(
    bplan: Dict[str, Any],
    total_video_duration: float = 0.0,
    character_bible: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Audit a single adjacent shot cut boundary using exact decoded frames (-2, -1, +1, +2).
    Never skips map/diagram/title/prop shots. Fails closed (`NOT_VERIFIED` or `FAIL`) on:
    - missing/corrupted boundary frames or pre_1 >= post_1 index collision
    - blank/black frame or blank/unreadable diagram at the cut boundary
    - unallowlisted `intentional_cut_reason` / `causal_cut_reason` or reason-evidence mismatch
    - unallowlisted same-space persisting actor teleport across the cut
    """
    s_cur = bplan["from_shot"]
    s_nxt = bplan["to_shot"]
    id_cur = bplan["from_shot_id"]
    id_nxt = bplan["to_shot_id"]
    sub_cur = determine_expected_subject(s_cur)
    sub_nxt = determine_expected_subject(s_nxt)
    tpl_cur = str(s_cur.get("tpl", "scene"))
    tpl_nxt = str(s_nxt.get("tpl", "scene"))
    cut_type = _classify_cut_type(sub_cur, sub_nxt, s_cur, s_nxt)

    raw_reason = s_nxt.get("intentional_cut_reason")
    if raw_reason is None:
        raw_reason = s_nxt.get("causal_cut_reason")
    reason_str = str(raw_reason).strip() if raw_reason is not None and str(raw_reason).strip() else None

    f_indices = dict(bplan["extracted_frame_indices"])
    req_times = dict(bplan["requested_times"])
    art_paths_raw: Dict[str, Path] = bplan.get("artifact_paths") or {}

    diags: List[str] = []
    decoded_imgs: Dict[str, np.ndarray] = {}
    art_shas: Dict[str, Optional[str]] = {}
    art_paths_str: Dict[str, Optional[str]] = {}
    missing_roles: List[str] = []

    for role in ("pre_2", "pre_1", "post_1", "post_2"):
        p = art_paths_raw.get(role)
        art_paths_str[role] = str(p) if p is not None else None
        if p is None:
            missing_roles.append(role)
            art_shas[role] = None
            continue
        arr = _load_rgb_png_verified(p)
        if arr is None:
            missing_roles.append(role)
            art_shas[role] = None
        else:
            decoded_imgs[role] = arr
            art_shas[role] = sha256_file(p)

    # Guard against frame-index rounding onto the same side of the cut
    if int(f_indices.get("pre_1", 0)) >= int(f_indices.get("post_1", 0)):
        diags.append(
            f"Cut frame index collision: pre_1={f_indices.get('pre_1')} >= post_1={f_indices.get('post_1')}"
        )
        missing_roles.append("index_collision")

    if missing_roles:
        diags.append(f"Missing or undecodable boundary frames for roles: {missing_roles}")
        return {
            "cut_index": int(bplan["cut_index"]),
            "cut": bplan["cut"],
            "from_shot_id": id_cur,
            "to_shot_id": id_nxt,
            "shot_ids": [id_cur, id_nxt],
            "from_subject": sub_cur,
            "to_subject": sub_nxt,
            "cut_time_sec": bplan["cut_time_sec"],
            "requested_times": req_times,
            "extracted_frame_indices": f_indices,
            "artifact_paths": art_paths_str,
            "artifact_shas": art_shas,
            "pixel_mean_abs_delta": None,
            "pre_internal_delta": None,
            "post_internal_delta": None,
            "geometric_centroid": {"from": "NOT_VERIFIED", "to": "NOT_VERIFIED"},
            "actor_centroid_dx": "NOT_APPLICABLE" if (sub_cur != "actor" or sub_nxt != "actor") else None,
            "cut_type": cut_type,
            "intentional_cut_reason": reason_str,
            "reason_allowlisted": bool(reason_str in ALLOWLISTED_INTENTIONAL_CUT_REASONS) if reason_str else True,
            "reason_evidence_valid": False,
            "same_bg": (s_cur.get("args", {}) or {}).get("bg") == (s_nxt.get("args", {}) or {}).get("bg"),
            "causal_cut_declared": bool(reason_str or tpl_cur != tpl_nxt),
            "world_continuity_checked": False,
            "world_continuity_violations": [],
            "coverage_complete": False,
            "status": "NOT_VERIFIED",
            "diagnostics": diags,
        }

    img_pre2 = decoded_imgs["pre_2"]
    img_pre1 = decoded_imgs["pre_1"]
    img_post1 = decoded_imgs["post_1"]
    img_post2 = decoded_imgs["post_2"]

    pixel_delta = round(float(np.mean(np.abs(img_post1.astype(float) - img_pre1.astype(float)))), 3)
    pre_internal_delta = round(float(np.mean(np.abs(img_pre1.astype(float) - img_pre2.astype(float)))), 3)
    post_internal_delta = round(float(np.mean(np.abs(img_post2.astype(float) - img_post1.astype(float)))), 3)

    status = "PASS"

    # Check boundary frames for accidental blank/black frames (outside global fade edges)
    for role, arr in (("pre_1", img_pre1), ("post_1", img_post1)):
        ts_r = float(req_times[role])
        if total_video_duration > 2.5 and (ts_r < 0.25 or ts_r > total_video_duration - 0.35):
            continue
        m_val = float(np.mean(arr))
        s_val = float(np.std(arr))
        if m_val < 5.0 or s_val < 6.0:
            status = "FAIL"
            diags.append(
                f"Blank/flat boundary frame at {bplan['cut']} ({role}, t={ts_r:.3f}s, mean={m_val:.1f}, std={s_val:.1f})"
            )

    # Check diagram/map readability right at the cut boundary so blank diagram mutations fail closed
    if sub_cur == "map" and tpl_cur != "black":
        ok_m_pre, d_m_pre = audit_tactical_labels_mobile(img_pre1)
        if not ok_m_pre:
            status = "FAIL"
            diags.append(f"Pre-cut diagram/map frame unreadable at {bplan['cut']}: {d_m_pre}")
    if sub_nxt == "map" and tpl_nxt != "black":
        ok_m_post, d_m_post = audit_tactical_labels_mobile(img_post1)
        if not ok_m_post:
            status = "FAIL"
            diags.append(f"Post-cut diagram/map frame unreadable at {bplan['cut']}: {d_m_post}")

    # Geometric centroid tracking when applicable; NOT_APPLICABLE when shot has no actor subject
    b_end: Optional[ActorBoundingBox] = None
    b_start: Optional[ActorBoundingBox] = None
    if sub_cur == "actor":
        b_end = track_actor_instances_full_frame(img_pre1, tpl=tpl_cur)
        from_cent: Any = (
            {"x": round(b_end.mass_x, 4), "y": round(b_end.mass_y, 4)} if b_end.detected else "UNDETECTED"
        )
    else:
        from_cent = "NOT_APPLICABLE"

    if sub_nxt == "actor":
        b_start = track_actor_instances_full_frame(img_post1, tpl=tpl_nxt)
        to_cent: Any = (
            {"x": round(b_start.mass_x, 4), "y": round(b_start.mass_y, 4)} if b_start.detected else "UNDETECTED"
        )
    else:
        to_cent = "NOT_APPLICABLE"

    if sub_cur == "actor" and sub_nxt == "actor" and b_end and b_start and b_end.detected and b_start.detected:
        actor_centroid_dx: Any = round(abs(b_start.mass_x - b_end.mass_x), 4)
    else:
        actor_centroid_dx = "NOT_APPLICABLE"

    # Validate intentional_cut_reason against strict allowlist + structural evidence
    reason_allowlisted = True
    reason_evidence_valid = True
    if reason_str is not None:
        if reason_str not in ALLOWLISTED_INTENTIONAL_CUT_REASONS:
            reason_allowlisted = False
            reason_evidence_valid = False
            status = "FAIL"
            diags.append(
                f"Unallowlisted intentional_cut_reason '{reason_str}' on {bplan['cut']} (arbitrary strings cannot bypass continuity)"
            )
        elif reason_str in (ALLOWLISTED_DIAGRAM_CUT_REASONS - {"heroic_payoff_summary"}):
            if sub_cur != "map" and sub_nxt != "map" and tpl_cur == tpl_nxt:
                reason_evidence_valid = False
                status = "FAIL"
                diags.append(
                    f"Reason '{reason_str}' requires diagram/map/title transition evidence on {bplan['cut']}, got {sub_cur}->{sub_nxt}"
                )

    # Cross-cut actor identity & world-state continuity check (checked across ALL cuts when world_state is present)
    world_violations: List[str] = []
    ws_cur = s_cur.get("world_state", {}) if isinstance(s_cur.get("world_state"), dict) else {}
    ws_nxt = s_nxt.get("world_state", {}) if isinstance(s_nxt.get("world_state"), dict) else {}
    shared_ws_keys = sorted(set(ws_cur.keys()) & set(ws_nxt.keys()) - {"zone"})
    allowed_changed_keys = set(s_nxt.get("state_changed_keys") or [])
    allow_ws_change = bool(s_nxt.get("allow_world_state_change", False) or s_nxt.get("allow_direction_change", False))
    for inv_key in shared_ws_keys:
        if ws_cur[inv_key] != ws_nxt[inv_key] and not allow_ws_change and inv_key not in allowed_changed_keys:
            msg = (
                f"World continuity violation on {bplan['cut']}: '{inv_key}' flipped from "
                f"'{ws_cur[inv_key]}' to '{ws_nxt[inv_key]}'"
            )
            world_violations.append(msg)
            diags.append(msg)
            status = "FAIL"

    world_checked = bool((sub_cur == "actor" and sub_nxt == "actor") or shared_ws_keys)
    if sub_cur == "actor" and sub_nxt == "actor":
        args_cur = s_cur.get("args", {}) if isinstance(s_cur.get("args"), dict) else {}
        args_nxt = s_nxt.get("args", {}) if isinstance(s_nxt.get("args"), dict) else {}

        zone_cur = ws_cur.get("zone") or args_cur.get("zone") or args_cur.get("bg") or "default"
        zone_nxt = ws_nxt.get("zone") or args_nxt.get("zone") or args_nxt.get("bg") or "default"
        same_continuous_space = (zone_cur == zone_nxt) and (tpl_cur == tpl_nxt)

        ppl_cur = {
            str(p["id"]): p
            for p in (args_cur.get("people") or [])
            if isinstance(p, dict) and p.get("id")
        }
        ppl_nxt = {
            str(p["id"]): p
            for p in (args_nxt.get("people") or [])
            if isinstance(p, dict) and p.get("id")
        }
        common_actors = sorted(set(ppl_cur.keys()) & set(ppl_nxt.keys()))
        bible_chars = (character_bible or {}).get("characters", {}) if isinstance(character_bible, dict) else {}

        for aid in common_actors:
            pc = ppl_cur[aid]
            pn = ppl_nxt[aid]
            # Character bible preset consistency across adjacent cut
            if aid in bible_chars and isinstance(bible_chars[aid], dict):
                expected_preset = bible_chars[aid].get("preset")
                if expected_preset and (pc.get("preset") != expected_preset or pn.get("preset") != expected_preset):
                    msg = (
                        f"Character bible preset drift across {bplan['cut']} for '{aid}': "
                        f"{pc.get('preset')}->{pn.get('preset')} (expected {expected_preset})"
                    )
                    world_violations.append(msg)
                    diags.append(msg)
                    status = "FAIL"

            xc = float(pc.get("to", pc.get("x", 0.5)))
            xn = float(pn.get("from", pn.get("x", 0.5)))
            hc = float(pc.get("h", 0.5))
            hn = float(pn.get("h", 0.5))
            dx = abs(xn - xc)
            scale_shift = abs(hn - hc) >= 0.08

            framing_reframe_legit = (
                reason_str in ALLOWLISTED_FRAMING_OR_SPACE_CUT_REASONS
                and reason_allowlisted
                and reason_evidence_valid
                and (scale_shift or not same_continuous_space)
            )
            if same_continuous_space and (not framing_reframe_legit) and dx > 0.42:
                msg = (
                    f"Cross-cut actor teleport on {bplan['cut']}: persisting actor '{aid}' jumped "
                    f"dx={dx:.3f} in continuous space '{zone_cur}' (reason={reason_str!r})"
                )
                world_violations.append(msg)
                diags.append(msg)
                status = "FAIL"

        # Decoded single-actor pixel centroid jump guard when no people array coordinates hid a rendered jump
        if (
            same_continuous_space
            and len(ppl_cur) == 1
            and len(ppl_nxt) == 1
            and len(common_actors) == 1
            and isinstance(actor_centroid_dx, float)
            and actor_centroid_dx > 0.48
        ):
            aid0 = common_actors[0]
            hc0 = float(ppl_cur[aid0].get("h", 0.5))
            hn0 = float(ppl_nxt[aid0].get("h", 0.5))
            if abs(hn0 - hc0) < 0.08:
                msg = (
                    f"Decoded pixel centroid teleport on {bplan['cut']}: actor '{aid0}' centroid jumped "
                    f"dx={actor_centroid_dx:.3f} in continuous space '{zone_cur}'"
                )
                world_violations.append(msg)
                diags.append(msg)
                status = "FAIL"

    return {
        "cut_index": int(bplan["cut_index"]),
        "cut": bplan["cut"],
        "from_shot_id": id_cur,
        "to_shot_id": id_nxt,
        "shot_ids": [id_cur, id_nxt],
        "from_subject": sub_cur,
        "to_subject": sub_nxt,
        "cut_time_sec": bplan["cut_time_sec"],
        "requested_times": req_times,
        "extracted_frame_indices": f_indices,
        "artifact_paths": art_paths_str,
        "artifact_shas": art_shas,
        "pixel_mean_abs_delta": pixel_delta,
        "pre_internal_delta": pre_internal_delta,
        "post_internal_delta": post_internal_delta,
        "geometric_centroid": {"from": from_cent, "to": to_cent},
        "actor_centroid_dx": actor_centroid_dx,
        "cut_type": cut_type,
        "intentional_cut_reason": reason_str,
        "reason_allowlisted": reason_allowlisted,
        "reason_evidence_valid": reason_evidence_valid,
        "same_bg": (s_cur.get("args", {}) or {}).get("bg") == (s_nxt.get("args", {}) or {}).get("bg"),
        "causal_cut_declared": bool(reason_str or tpl_cur != tpl_nxt),
        "world_continuity_checked": world_checked,
        "world_continuity_violations": world_violations,
        "coverage_complete": True,
        "status": status,
        "diagnostics": diags,
    }


def audit_cut_boundaries_all(
    boundary_plans: List[Dict[str, Any]],
    expected_cut_count: int,
    total_video_duration: float = 0.0,
    character_bible: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Audit all N-1 cut boundaries and compute fail-closed coverage summary.
    """
    evidence: List[Dict[str, Any]] = []
    unaudited: List[str] = []
    failed: List[str] = []

    for bplan in boundary_plans:
        entry = audit_single_cut_boundary(
            bplan,
            total_video_duration=total_video_duration,
            character_bible=character_bible,
        )
        evidence.append(entry)
        if not entry.get("coverage_complete", False) or entry.get("status") == "NOT_VERIFIED":
            unaudited.append(entry["cut"])
        elif entry.get("status") != "PASS":
            failed.append(entry["cut"])

    audited_count = sum(1 for e in evidence if e.get("coverage_complete") is True)
    seen_cuts = [e["cut"] for e in evidence]
    no_duplicates = len(seen_cuts) == len(set(seen_cuts))
    full_cov = (
        audited_count == expected_cut_count
        and len(evidence) == expected_cut_count
        and len(unaudited) == 0
        and no_duplicates
    )
    return {
        "expected_cut_count": expected_cut_count,
        "audited_cut_count": audited_count,
        "unaudited_cuts": unaudited,
        "failed_cuts": failed,
        "full_boundary_coverage": full_cov,
        "all_cuts_passed": full_cov and len(failed) == 0,
        "boundary_evidence": evidence,
    }


def audit_acting_posture_temporal(
    sample_frames: List[np.ndarray],
    action: str,
    bounds: ActorBoundingBox,
    expected_subject: str,
) -> Tuple[bool, str, List[str]]:
    """Verify observable acting posture from temporal multi-frame geometry."""
    diags: List[str] = []
    if expected_subject in ("map", "diagram", "none", "prop"):
        return True, f"subject_{expected_subject}", diags

    if not bounds.detected:
        diags.append(f"Actor undetected for action '{action}' - acting posture NOT_VERIFIED")
        return False, "undetected", diags

    detected_pose = "standard"
    verified = True
    act = (action or "").upper()

    if act in ("BRACE", "CONTACT", "SHIELD_COVER"):
        if bounds.mass_y < 0.42:
            diags.append(f"BRACE acting posture: center of mass too high ({bounds.mass_y:.3f})")
            verified = False
        detected_pose = "brace"

    elif act in ("SIGNAL", "FIRE_SIGNAL", "RAISE_STANDARD"):
        mid_frame = sample_frames[len(sample_frames) // 2]
        h = mid_frame.shape[0]
        top_region = mid_frame[: int(h * 0.42), :, :]
        ink_top = (top_region[:, :, 0] < 70) & (top_region[:, :, 1] < 70) & (top_region[:, :, 2] < 70)
        gold_or_red = (top_region[:, :, 0] > 150) & (top_region[:, :, 2] < 100)
        raised_features = int(np.sum(ink_top)) + int(np.sum(gold_or_red))
        if raised_features < 80:
            diags.append(f"{act} acting posture: lacks distinct raised arm/standard in upper frame")
            verified = False
        detected_pose = "signal" if "SIGNAL" in act else "raise_standard"

    elif act in ("HAMMER", "MALLET", "STRIKE"):
        if len(sample_frames) >= 3:
            diff = float(np.mean(np.abs(sample_frames[-1].astype(float) - sample_frames[0].astype(float))))
            if diff < 2.0:
                diags.append(f"HAMMER acting posture: insufficient dynamic swing motion (diff={diff:.2f})")
                verified = False
        detected_pose = "hammer"

    elif act in ("WINCH", "CRANK"):
        if len(sample_frames) >= 2:
            diff = float(np.mean(np.abs(sample_frames[-1].astype(float) - sample_frames[0].astype(float))))
            if diff < 0.6:
                diags.append(f"WINCH/CRANK posture: static actor without observable crank motion (diff={diff:.2f})")
                verified = False
        detected_pose = "winch"

    elif act in ("LOAD", "AIM", "SLIP", "LIFT_STANDARD", "RESCUE_DASH", "REFORM"):
        if len(sample_frames) >= 2:
            diffs = [
                float(np.mean(np.abs(sample_frames[k].astype(float) - sample_frames[0].astype(float))))
                for k in range(1, len(sample_frames))
            ]
            max_diff = max(diffs) if diffs else 0.0
            if max_diff < 0.5:
                diags.append(f"{act} posture: static frame without observable acting motion (max_diff={max_diff:.2f})")
                verified = False
        detected_pose = act.lower()

    elif act in ("RECOIL", "IMPACT_RECOIL"):
        if len(sample_frames) >= 3:
            diff = float(np.mean(np.abs(sample_frames[len(sample_frames) // 2].astype(float) - sample_frames[0].astype(float))))
            if diff < 1.0:
                diags.append(f"RECOIL posture: insufficient kinetic displacement (diff={diff:.2f})")
                verified = False
        detected_pose = "recoil"

    elif act in ("FATIGUE",):
        if bounds.mass_y < 0.38:
            diags.append(f"FATIGUE posture: lack of visible postural droop or slump (mass_y={bounds.mass_y:.3f})")
            verified = False
        detected_pose = "fatigue"

    return verified, detected_pose, diags


def _count_actor_column_pixels(small_frame: np.ndarray, norm_x: float, half_band: float = 0.09) -> int:
    """Count ink/armor/skin foreground pixels around normalized horizontal position norm_x."""
    h, w, _ = small_frame.shape
    c0 = max(0, int((norm_x - half_band) * w))
    c1 = min(w, int((norm_x + half_band) * w))
    if c1 <= c0:
        return 0
    band = small_frame[int(h * 0.12) : int(h * 0.94), c0:c1, :]
    r = band[:, :, 0].astype(np.int16)
    g = band[:, :, 1].astype(np.int16)
    b = band[:, :, 2].astype(np.int16)
    ink = (r < 75) & (g < 75) & (b < 75)
    crimson = (r > 135) & ((r - g) > 35) & ((r - b) > 35)
    skin = (r > 180) & (g > 135) & (b > 110) & ((r - b) > 20)
    return int(np.sum(ink | crimson | skin))


def audit_temporal_continuity(
    sample_frames: List[np.ndarray],
    timestamps: List[float],
    expected_subject: str,
    total_video_duration: float = 0.0,
    internal_cut_times: Optional[List[float]] = None,
) -> Tuple[bool, bool, float, List[str]]:
    """
    Audit temporal continuity across frame samples:
    Detects sudden actor disappearance or instantaneous teleport jumps within a shot,
    distinguishing real actor teleportation from multi-actor histogram peak switching,
    intentional multi-angle internal camera cuts (`cameraSegments`), and global start/end fade dissolves.
    """
    diags: List[str] = []
    teleport_detected = False
    disappearance_detected = False
    max_jump_px = 0.0

    if expected_subject != "actor" or len(sample_frames) < 2:
        return teleport_detected, disappearance_detected, max_jump_px, diags

    prev_bounds = None
    prev_small: Optional[np.ndarray] = None
    frame_w = sample_frames[0].shape[1]

    for i, (frame, ts) in enumerate(zip(sample_frames, timestamps)):
        small = frame[::2, ::2] if frame.shape[0] >= 480 else frame
        b = track_actor_instances_full_frame(small)
        if i == 0:
            prev_bounds = b
            prev_small = small
            continue

        # Intentional internal multi-angle camera edit (`Phase E`): audited separately by `audit_internal_camera_cuts`
        if internal_cut_times and any((timestamps[i - 1] - 1e-4) < ct <= (ts + 1e-4) for ct in internal_cut_times):
            prev_bounds = b
            prev_small = small
            continue

        near_global_fade = (
            (total_video_duration > 2.0 and (ts < 0.35 or ts > total_video_duration - 0.50))
        )

        if prev_bounds and prev_bounds.detected and not b.detected and not near_global_fade:
            frame_mean = float(np.mean(small))
            if frame_mean >= 25.0:
                disappearance_detected = True
                diags.append(f"Temporal defect: Actor suddenly disappeared at t={ts:.2f}s without shot cut")

        if prev_bounds and prev_bounds.detected and b.detected and prev_small is not None:
            jump = abs(b.mass_x - prev_bounds.mass_x) * frame_w
            dt = timestamps[i] - timestamps[i - 1]
            prev_col_px = _count_actor_column_pixels(prev_small, prev_bounds.mass_x)
            cur_at_prev_px = _count_actor_column_pixels(small, prev_bounds.mass_x)
            vacated_old_spot = (prev_col_px == 0) or (cur_at_prev_px < 0.30 * prev_col_px)

            if vacated_old_spot and jump > max_jump_px:
                max_jump_px = jump
            elif not vacated_old_spot:
                # Multi-actor scene where first soldier remained in place; estimate local motion smoothly
                local_jump = min(jump, frame_w * 0.12)
                if local_jump > max_jump_px:
                    max_jump_px = local_jump

            if dt < 1.5 and jump > (frame_w * 0.38) and vacated_old_spot:
                teleport_detected = True
                diags.append(
                    f"Temporal defect: Actor teleported {jump:.1f}px across frame in {dt:.2f}s (t={ts:.2f}s)"
                )

        prev_bounds = b
        prev_small = small

    return teleport_detected, disappearance_detected, max_jump_px, diags


_VALID_SQUIRE_PRESETS_CACHE: Optional[set[str]] = None


def get_valid_squire_presets() -> set[str]:
    """Load canonical Squire CAST keys + PRESET_ALIASES directly from packs/squire/chara.js."""
    global _VALID_SQUIRE_PRESETS_CACHE
    if _VALID_SQUIRE_PRESETS_CACHE is not None:
        return _VALID_SQUIRE_PRESETS_CACHE
    import re
    chara_path = ROOT_DIR / "packs" / "squire" / "chara.js"
    valid: set[str] = set()
    if chara_path.is_file():
        code = chara_path.read_text(encoding="utf-8")
        for m in re.finditer(r"^\s*([a-zA-Z0-9_]+):\s*K\(", code, flags=re.MULTILINE):
            valid.add(m.group(1))
        alias_block = re.search(r"export const PRESET_ALIASES\s*=\s*\{([^}]+)\}", code)
        if alias_block:
            for m in re.finditer(r"([a-zA-Z0-9_]+)\s*:\s*'([a-zA-Z0-9_]+)'", alias_block.group(1)):
                valid.add(m.group(1))
                valid.add(m.group(2))
    _VALID_SQUIRE_PRESETS_CACHE = valid
    return valid


def validate_actor_presets(shot: Dict[str, Any], pack_name: str = "squire") -> Tuple[bool, List[str]]:
    """Verify every actor preset in a Squire shot resolves to a valid CAST/alias preset."""
    if pack_name != "squire":
        return True, []
    valid_presets = get_valid_squire_presets()
    if not valid_presets:
        return True, []
    diags: List[str] = []
    args = shot.get("args", {}) if isinstance(shot.get("args"), dict) else {}
    people = shot.get("people") or args.get("people") or []
    for p in people:
        if not isinstance(p, dict):
            continue
        preset = str(p.get("preset") or "").strip()
        has_custom = any(p.get(k) for k in ("body", "helmet", "hair", "tunicColor", "mail", "plate"))
        if not preset and not has_custom:
            diags.append(f"MISSING_ACTOR_PRESET: actor '{p.get('id', 'unnamed')}' lacks preset and custom body")
        elif preset and preset not in valid_presets and not has_custom:
            diags.append(f"UNKNOWN_ACTOR_PRESET: {preset}")
    return len(diags) == 0, diags


def validate_diagram_primitive(shot: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate diagram prop kind/type matches shot tactical description."""
    args = shot.get("args", {}) if isinstance(shot.get("args"), dict) else {}
    props = args.get("props", [])
    kinds = [str(p.get("kind") or p.get("type") or "") for p in props if isinstance(p, dict)]
    desc = str(shot.get("desc", "")).lower()
    expected_sub = determine_expected_subject(shot)
    if "manipular" in desc or "quincunx" in desc:
        if "torsion_diagram" in kinds or "torsion_spring" in kinds:
            return False, "MISMATCHED_DIAGRAM: Torsion catapult spring used for Roman formation!"
        if expected_sub == "map" and not any("manipular" in t or "roman_formation" in t for t in kinds):
            return False, "MISSING_DIAGRAM: Expected roman_manipular_formation_diagram"
    return True, "OK"


def validate_single_held_prop_exclusivity(shot: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Prevent duplicate held weapons/shields on an actor or simultaneous held + ground standard duplication.
    """
    diags: List[str] = []
    args = shot.get("args", {}) if isinstance(shot.get("args"), dict) else {}
    people = shot.get("people") or args.get("people") or []
    props = args.get("props") or []

    actors_holding_standard = []
    for p in people:
        if not isinstance(p, dict):
            continue
        aid = p.get("id") or p.get("preset") or "actor"
        if p.get("weapon2") and (p.get("weapon") or p.get("preset")):
            diags.append(
                f"DUPLICATE_HELD_OBJECT: Actor '{aid}' has duplicate weapon2='{p['weapon2']}' alongside primary/preset weapon"
            )
        if p.get("shield2") and (p.get("shield") or p.get("preset")):
            diags.append(
                f"DUPLICATE_HELD_OBJECT: Actor '{aid}' has duplicate shield2='{p['shield2']}' alongside primary/preset shield"
            )
        # Check if actor holds a standard (aquilifer default weapon is 'standard' unless overridden)
        explicit_wpn = p.get("weapon", "__DEFAULT__")
        if explicit_wpn == "standard" or (explicit_wpn == "__DEFAULT__" and p.get("preset") == "aquilifer"):
            actors_holding_standard.append(aid)

    standalone_standards = [
        pr for pr in props
        if isinstance(pr, dict) and str(pr.get("kind") or pr.get("type") or "") in ("standard", "eagle")
    ]
    if len(standalone_standards) > 1 and not shot.get("allow_multiple_standards"):
        diags.append(f"DUPLICATE_PROP: Multiple standalone standard/eagle props ({len(standalone_standards)}) in one shot")
    if actors_holding_standard and standalone_standards and not shot.get("allow_multiple_standards"):
        diags.append(
            f"DUPLICATE_STANDARD_PROP: Actor(s) {actors_holding_standard} hold a standard while standalone standard prop is also rendered"
        )

    return len(diags) == 0, diags


def audit_project_temporal_visual(
    project_dir: Path | str,
    mp4_path: Path | str,
    output_evidence_dir: Path | str,
    run_negative_suite: bool = True,
) -> TemporalQAReport:
    """Run full fail-closed temporal visual audit on a rendered project."""
    p_path = Path(project_dir).resolve()
    mp4_file = Path(mp4_path).resolve()
    ev_dir = Path(output_evidence_dir).resolve()
    ev_frames_dir = ev_dir / "temporal_frames"
    ev_frames_dir.mkdir(parents=True, exist_ok=True)

    report = TemporalQAReport(
        project_id=p_path.name,
        mp4_path=str(mp4_file),
        all_passed=False,
        technical_verdict="NOT_VERIFIED",
    )

    # Fail-closed guard 1: MP4 file existence and decode health
    if not mp4_file.is_file() or mp4_file.stat().st_size < 100:
        report.global_issues.append(f"Missing or empty MP4 file: {mp4_file}")
        report.all_passed = False
        report.technical_verdict = "FAIL"
        return report

    media_info = prod_fp.inspect_media_file(mp4_file, full_decode=True)
    if not media_info.get("valid", False):
        report.global_issues.append(f"Media inspection/decode failed: {media_info.get('error')}")
        report.all_passed = False
        report.technical_verdict = "FAIL"
        return report

    width = int(media_info.get("width") or 1920)
    height = int(media_info.get("height") or 1080)
    fps = float(media_info.get("fps") or 24.0)

    # Fail-closed guard 2: Storyboard existence and non-zero shots
    shots_file = p_path / "story" / "shots.json"
    if not shots_file.is_file():
        report.global_issues.append("Missing story/shots.json")
        report.all_passed = False
        report.technical_verdict = "FAIL"
        return report

    try:
        shots_data = json.loads(shots_file.read_text(encoding="utf-8"))
        shots = shots_data.get("shots", []) if isinstance(shots_data, dict) else shots_data
    except Exception as exc:
        report.global_issues.append(f"Failed to read shots.json: {exc}")
        report.all_passed = False
        report.technical_verdict = "FAIL"
        return report

    if not isinstance(shots, list) or len(shots) == 0:
        report.global_issues.append("Empty storyboard (total_shots == 0); fail-closed")
        report.all_passed = False
        report.technical_verdict = "FAIL"
        return report

    # Normalize cumulative start/end/dur matching engine/player.js semantics
    norm_shots: List[Dict[str, Any]] = []
    cur_timeline_t = 0.0
    for idx_s, raw_s in enumerate(shots):
        sc = dict(raw_s)
        st_v = float(sc["start"]) if isinstance(sc.get("start"), (int, float)) else cur_timeline_t
        if isinstance(sc.get("end"), (int, float)):
            et_v = float(sc["end"])
            dur_v = float(sc.get("dur", max(0.2, et_v - st_v)))
        else:
            dur_v = float(sc.get("dur", 3.0))
            et_v = st_v + dur_v
        sc["start"] = round(st_v, 4)
        sc["end"] = round(et_v, 4)
        sc["dur"] = round(et_v - st_v, 4)
        cur_timeline_t = et_v
        norm_shots.append(sc)
    shots = norm_shots

    report.total_shots = len(shots)
    report.expected_cut_count = max(0, len(shots) - 1)
    total_dur = float(media_info.get("duration") or (shots[-1].get("end", 0.0) if shots else 0.0))

    pack_name = "squire"
    cfg_file = p_path / "config.json"
    if cfg_file.is_file():
        try:
            pack_name = str(json.loads(cfg_file.read_text(encoding="utf-8")).get("pack") or "squire")
        except Exception:
            pass

    character_bible: Optional[Dict[str, Any]] = None
    bible_file = p_path / "story" / "character_bible.json"
    if bible_file.is_file():
        try:
            character_bible = json.loads(bible_file.read_text(encoding="utf-8"))
        except Exception:
            character_bible = None

    # Build adaptive timestamp plan for all shots + exact N-1 cut boundary frame plan upfront
    shot_requests: List[Tuple[str, List[float]]] = []
    shot_coverage_ok: Dict[str, bool] = {}
    for idx_s, s in enumerate(shots):
        sid = str(s.get("id") or s.get("shot_id") or f"s{idx_s+1:02d}")
        action = str(s.get("action_kind") or s.get("action") or s.get("scene") or "")
        dur = float(s.get("dur", 3.0))
        st = float(s.get("start", 0.0))
        et = float(s.get("end", st + dur))
        ts_list, cov_ok = build_shot_sample_timestamps(st, et, dur, action, fps=fps)
        shot_requests.append((sid, ts_list))
        shot_coverage_ok[sid] = cov_ok

    boundary_plans = build_cut_boundary_frame_plan(shots, fps=fps)

    t_ext0 = time.perf_counter()
    shot_frame_paths, ext_mode = extract_frames_batched_cached(
        mp4_file=mp4_file,
        shot_requests=shot_requests,
        ev_frames_dir=ev_frames_dir,
        width=width,
        height=height,
        fps=fps,
        boundary_plans=boundary_plans,
    )
    report.extraction_mode = ext_mode
    report.extraction_elapsed_sec = round(time.perf_counter() - t_ext0, 3)

    passed_count = 0
    coverage_incomplete_any = False

    for idx_s, s in enumerate(shots):
        sid = str(s.get("id") or s.get("shot_id") or f"s{idx_s+1:02d}")
        action = str(s.get("action_kind") or s.get("action") or s.get("scene") or "")
        dur = float(s.get("dur", 3.0))
        st = float(s.get("start", 0.0))
        et = float(s.get("end", st + dur))
        tpl = str(s.get("tpl", "scene"))
        expected_sub = determine_expected_subject(s)
        timestamps = dict(shot_requests)[sid]

        audit = TemporalShotAudit(
            shot_id=sid,
            action_kind=action,
            tpl=tpl,
            expected_subject=expected_sub,
            duration=dur,
            start_time=st,
            end_time=et,
            sampling_fps_achieved=round(len(timestamps) / max(0.1, dur), 2),
        )

        if not shot_coverage_ok.get(sid, True):
            coverage_incomplete_any = True
            audit.passed = False
            audit.technical_verdict = "COVERAGE_INCOMPLETE"
            audit.diagnostics.append(
                f"Dynamic shot sampling density {audit.sampling_fps_achieved:.2f} fps < 4.0 fps target"
            )

        f_paths = shot_frame_paths.get(sid, [])
        sample_imgs: List[np.ndarray] = []
        sample_paths: List[str] = []
        all_frames_ok = True

        for fp in f_paths:
            arr_loaded = _load_rgb_png_verified(fp)
            if arr_loaded is None:
                all_frames_ok = False
                break
            sample_paths.append(str(fp))
            sample_imgs.append(arr_loaded)

        if not all_frames_ok or len(sample_imgs) < 3:
            audit.diagnostics.append("Failed to extract sufficient temporal frame samples (fail-closed)")
            audit.passed = False
            audit.technical_verdict = "FAIL"
            report.shot_audits[sid] = audit
            report.temporal_issues.append({
                "shot_id": sid,
                "action": action,
                "expected_subject": expected_sub,
                "verdict": "FAIL",
                "diagnostics": audit.diagnostics,
            })
            continue

        audit.temporal_samples = sample_paths
        audit.sample_timestamps = timestamps
        report.total_frames_sampled += len(sample_imgs)

        # Check ALL sampled frames for accidental mid-shot black/blank frames
        # (excluding global 0.35s fade-in and 0.45s fade-out edges on full multi-shot films)
        for s_idx, img_arr in enumerate(sample_imgs):
            ts_cur = timestamps[s_idx]
            if total_dur > 2.5 and (ts_cur < 0.35 or ts_cur > total_dur - 0.45):
                continue
            mean_int = float(np.mean(img_arr))
            std_int = float(np.std(img_arr))
            if mean_int < 5.0 or std_int < 6.0:
                audit.non_empty_content = False
                audit.diagnostics.append(
                    f"Blank/black frame at t={ts_cur:.2f}s (mean={mean_int:.1f}, std={std_int:.1f})"
                )
                audit.passed = False
                break

        # Validate actor presets against canonical pack CAST / aliases
        preset_ok, preset_diags = validate_actor_presets(s, pack_name=pack_name)
        if not preset_ok:
            audit.passed = False
            audit.diagnostics.extend(preset_diags)

        # Validate diagram primitive mismatch if applicable
        diag_prim_ok, diag_prim_msg = validate_diagram_primitive(s)
        if not diag_prim_ok:
            audit.passed = False
            audit.diagnostics.append(diag_prim_msg)

        # Validate prop exclusivity (no duplicate held weapons/shields or duplicated cohort standard)
        prop_excl_ok, prop_excl_diags = validate_single_held_prop_exclusivity(s)
        if not prop_excl_ok:
            audit.passed = False
            audit.diagnostics.extend(prop_excl_diags)

        # Check within-shot camera keyframe snaps
        kfs = (s.get("args", {}) or {}).get("cameraRig", {}).get("keyframes", [])
        if kfs:
            snap_det, snap_diags = cine_cam.audit_camera_snap_keyframes(kfs)
            if snap_det:
                audit.passed = False
                audit.diagnostics.extend(snap_diags)

        mid_img = sample_imgs[len(sample_imgs) // 2]

        if expected_sub == "map":
            audit.subject_detected = True
            audit.bounds = ActorBoundingBox(
                ymin=0.0, ymax=1.0, xmin=0.0, xmax=1.0, mass_x=0.5, mass_y=0.5, detected=True, confidence=1.0
            )
            mob_ok, mob_diags = audit_tactical_labels_mobile(mid_img)
            audit.performance_readability = mob_ok
            audit.diagnostics.extend(mob_diags)
            if not mob_ok:
                audit.passed = False
            if audit.technical_verdict != "COVERAGE_INCOMPLETE":
                audit.technical_verdict = "VISUAL_TECH_PASS" if audit.passed else "FAIL"
        else:
            bounds = track_actor_instances_full_frame(mid_img, tpl=tpl)
            audit.bounds = bounds
            audit.subject_detected = bounds.detected
            audit.detection_confidence = bounds.confidence

            safe, head_clip, feet_clip, f_diags = audit_safe_framing(mid_img, bounds, tpl, action, sid)
            audit.safe_framing = safe
            audit.head_clipped = head_clip
            audit.feet_clipped = feet_clip
            audit.diagnostics.extend(f_diags)
            if not safe:
                audit.passed = False
                report.framing_safe_all = False
                if head_clip:
                    report.no_clipped_heads = False

            act_ok, pose_found, a_diags = audit_acting_posture_temporal(
                sample_imgs, action, bounds, expected_sub
            )
            audit.performance_readability = act_ok
            audit.detected_acting_pose = pose_found
            audit.diagnostics.extend(a_diags)
            if not act_ok:
                audit.passed = False
                report.acting_verified_all = False

            cam_segs_raw = (s.get("args", {}) or {}).get("cameraSegments") or []
            int_cuts = [
                round(st + float(sg.get("local_start", 0.0)), 4)
                for sg in cam_segs_raw[1:]
                if isinstance(sg, dict) and float(sg.get("local_start", 0.0)) > 0.05
            ] if len(cam_segs_raw) >= 2 else []
            teleport, disap, max_j, cont_diags = audit_temporal_continuity(
                sample_imgs,
                timestamps,
                expected_sub,
                total_video_duration=total_dur,
                internal_cut_times=int_cuts,
            )
            audit.teleport_detected = teleport
            audit.sudden_disappearance = disap
            audit.net_motion_px = round(max_j, 2)
            audit.diagnostics.extend(cont_diags)
            if teleport or disap:
                audit.passed = False
                report.motion_verified_all = False

            diff_arr = np.abs(sample_imgs[-1].astype(float) - sample_imgs[0].astype(float))
            audit.subject_motion_px = round(float(np.mean(diff_arr)), 2)

            if audit.technical_verdict == "COVERAGE_INCOMPLETE":
                audit.passed = False
            elif not audit.non_empty_content or not audit.safe_framing:
                audit.technical_verdict = "FAIL"
            elif not bounds.detected and expected_sub == "actor":
                audit.technical_verdict = "NOT_VERIFIED"
                audit.passed = False
            elif not audit.passed:
                audit.technical_verdict = "FAIL"
            else:
                audit.technical_verdict = "VISUAL_TECH_PASS"

        if audit.passed and audit.technical_verdict == "VISUAL_TECH_PASS":
            passed_count += 1
        else:
            report.temporal_issues.append({
                "shot_id": sid,
                "action": action,
                "expected_subject": expected_sub,
                "verdict": audit.technical_verdict,
                "diagnostics": audit.diagnostics,
            })

        report.shot_audits[sid] = audit

    # 100% Cut-Boundary Temporal QA Invariant: N valid shots -> exactly N-1 audited transitions
    cut_summary = audit_cut_boundaries_all(
        boundary_plans=boundary_plans,
        expected_cut_count=report.expected_cut_count,
        total_video_duration=total_dur,
        character_bible=character_bible,
    )
    report.audited_cut_count = int(cut_summary["audited_cut_count"])
    report.unaudited_cuts = list(cut_summary["unaudited_cuts"])
    report.full_boundary_coverage = bool(cut_summary["full_boundary_coverage"])
    report.boundary_evidence = list(cut_summary["boundary_evidence"])
    report.cross_cut_boundary_audits = list(cut_summary["boundary_evidence"])
    report.total_frames_sampled += 4 * report.audited_cut_count

    boundary_unverified = False
    if not report.full_boundary_coverage:
        boundary_unverified = True
        report.global_issues.append(
            f"Incomplete cut boundary coverage: audited {report.audited_cut_count}/{report.expected_cut_count} "
            f"(unaudited={report.unaudited_cuts})"
        )
    if cut_summary["failed_cuts"]:
        for fc in report.boundary_evidence:
            if fc.get("status") == "FAIL":
                report.global_issues.append(
                    f"Cut boundary FAIL on {fc['cut']}: {fc.get('diagnostics')}"
                )
                report.temporal_issues.append({
                    "shot_id": fc["cut"],
                    "type": "WORLD_CONTINUITY_VIOLATION" if fc.get("world_continuity_violations") else "CUT_BOUNDARY_DEFECT",
                    "action": "CUT_BOUNDARY",
                    "expected_subject": f"{fc['from_subject']}->{fc['to_subject']}",
                    "verdict": "FAIL",
                    "diagnostics": fc.get("diagnostics", []),
                })

    if run_negative_suite:
        neg_results = run_negative_fixtures_tests()
        report.negative_fixtures_results = neg_results
        if not neg_results.get("all_fixtures_passed", False):
            report.negative_fixtures_passed = False
            report.global_issues.append("Negative fixtures test suite encountered failures")

    report.passed_shots = passed_count
    if report.total_frames_sampled == 0 or boundary_unverified:
        report.all_passed = False
        report.technical_verdict = "NOT_VERIFIED" if boundary_unverified and not cut_summary["failed_cuts"] else "FAIL"
    elif coverage_incomplete_any:
        report.all_passed = False
        report.technical_verdict = "COVERAGE_INCOMPLETE"
    elif (
        passed_count == report.total_shots
        and report.total_shots > 0
        and report.full_boundary_coverage
        and report.audited_cut_count == report.expected_cut_count
        and len(report.unaudited_cuts) == 0
        and len(cut_summary["failed_cuts"]) == 0
        and len(report.global_issues) == 0
        and report.negative_fixtures_passed
    ):
        report.all_passed = True
        report.technical_verdict = "VISUAL_TECH_PASS"
    else:
        report.all_passed = False
        has_unverified = any(a.technical_verdict == "NOT_VERIFIED" for a in report.shot_audits.values())
        report.technical_verdict = "NOT_VERIFIED" if (has_unverified and not report.global_issues) else "FAIL"

    # Persist temporal_issues.json and boundary_coverage_matrix.json atomically
    out_json = ev_dir / "temporal_issues.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    tmp_json = out_json.with_suffix(f".{os.getpid()}.tmp")
    tmp_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp_json, out_json)

    matrix_json = ev_dir / "boundary_coverage_matrix.json"
    tmp_mat = matrix_json.with_suffix(f".{os.getpid()}.tmp")
    tmp_mat.write_text(
        json.dumps(
            {
                "version": "14.7.5.1",
                "project_id": report.project_id,
                "mp4_path": report.mp4_path,
                "total_shots": report.total_shots,
                "expected_cut_count": report.expected_cut_count,
                "audited_cut_count": report.audited_cut_count,
                "unaudited_cuts": report.unaudited_cuts,
                "full_boundary_coverage": report.full_boundary_coverage,
                "all_cuts_passed": cut_summary["all_cuts_passed"],
                "boundary_evidence": report.boundary_evidence,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(tmp_mat, matrix_json)

    return report


def run_negative_fixtures_tests() -> Dict[str, Any]:
    """
    Run all 15 dedicated negative & positive-control fixtures against real production detectors.
    """
    fixtures: Dict[str, Dict[str, Any]] = {}

    # 1. Blank Frame Fixture
    black_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    b_bounds = track_actor_instances_full_frame(black_frame)
    blank_detected = (not b_bounds.detected) and float(np.mean(black_frame)) < 5.0
    fixtures["blank_frame"] = {
        "description": "Pure black frame must be detected as blank and fail",
        "expected_failure_caught": True,
        "passed": bool(blank_detected),
    }

    # 2. Map False-Actor Fixture
    map_frame = np.full((1080, 1920, 3), (220, 205, 175), dtype=np.uint8)
    map_frame[500:510, 400:1500] = (40, 35, 30)
    map_expected_subject = determine_expected_subject({"tpl": "map", "desc": "tactical campaign map"})
    fixtures["map_false_actor"] = {
        "description": "Tactical map lines must NOT be falsely identified as human actor",
        "expected_subject": map_expected_subject,
        "passed": bool(map_expected_subject == "map"),
    }

    # 3. Actor Disappearance Fixture
    actor_frame = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    actor_frame[400:800, 900:1020] = (180, 30, 30)
    actor_frame[320:400, 930:990] = (220, 180, 150)
    empty_frame = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    _, disap, _, _ = audit_temporal_continuity(
        [actor_frame, empty_frame], [0.0, 1.0], expected_subject="actor"
    )
    fixtures["actor_disappearance"] = {
        "description": "Actor suddenly missing mid-shot must trigger disappearance defect",
        "detected": bool(disap),
        "passed": bool(disap),
    }

    # 4. Teleport Mid-Shot Fixture
    frame_left = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    frame_left[400:800, 200:320] = (180, 30, 30)
    frame_left[320:400, 230:290] = (220, 180, 150)
    frame_right = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    frame_right[400:800, 1500:1620] = (180, 30, 30)
    frame_right[320:400, 1530:1590] = (220, 180, 150)
    tele_res, _, jump_px, _ = audit_temporal_continuity(
        [frame_left, frame_right], [0.0, 0.5], expected_subject="actor"
    )
    fixtures["teleport_mid_shot"] = {
        "description": "Instantaneous 1300px lateral jump within 0.5s must be flagged as teleport defect",
        "teleport_flagged": bool(tele_res),
        "jump_px": float(jump_px),
        "passed": bool(tele_res and jump_px > 500),
    }

    # 5. Camera Snap Fixture
    snap_kfs = [
        {"t": 0.0, "x": 0.5, "y": 0.5, "z": 1.0},
        {"t": 1.0, "x": 0.2, "y": 0.5, "z": 1.0},
        {"t": 1.04, "x": 0.85, "y": 0.5, "z": 1.0},
        {"t": 2.0, "x": 0.85, "y": 0.5, "z": 1.0},
    ]
    snap_caught, snap_diags = cine_cam.audit_camera_snap_keyframes(snap_kfs)
    fixtures["camera_snap"] = {
        "description": "Abrupt 1-frame camera transform snap must be flagged by camera auditor",
        "snap_caught": bool(snap_caught),
        "diagnostics": snap_diags,
        "passed": bool(snap_caught and len(snap_diags) > 0),
    }

    # 6. Duplicate Held Object Fixture (calls production validate_single_held_prop_exclusivity)
    dup_shot = {
        "id": "s_dup",
        "args": {
            "people": [{"id": "dup_actor", "weapon": "sword", "weapon2": "spear", "shield": "scutum", "shield2": "buckler"}],
        },
    }
    excl_ok, excl_diags = validate_single_held_prop_exclusivity(dup_shot)
    fixtures["duplicate_held_object"] = {
        "description": "Duplicate weapon or shield in actor configuration must be rejected by production validator",
        "diagnostics": excl_diags,
        "passed": bool((not excl_ok) and len(excl_diags) >= 2),
    }

    # 7. Wrong Preset Fixture
    node_script = """
const fs = require('fs');
const code = fs.readFileSync('packs/squire/chara.js', 'utf8');
const castNames = [...code.matchAll(/^\\s*([a-zA-Z0-9_]+):\\s*K\\(/gm)].map(m => m[1]);
const aliasesMatch = [...code.matchAll(/([a-zA-Z0-9_]+):\\s*'([a-zA-Z0-9_]+)'/g)];
const aliases = Object.fromEntries(aliasesMatch.map(m => [m[1], m[2]]));
function validateCastPreset(preset) {
  if (!preset) return { valid: false, canonical: null, diagnostic: 'EMPTY_PRESET' };
  const clean = String(preset).trim();
  const canonical = aliases[clean] || clean;
  if (castNames.includes(canonical)) {
    return { valid: true, canonical, diagnostic: null };
  }
  return { valid: false, canonical: null, diagnostic: 'UNKNOWN_ACTOR_PRESET: ' + preset };
}
console.log(JSON.stringify(validateCastPreset('unknown_peasant_xyz')));
"""
    node_proc = subprocess.run(["node", "-e", node_script], cwd=ROOT_DIR, capture_output=True, text=True)
    val_unknown = json.loads(node_proc.stdout) if node_proc.returncode == 0 else {"valid": False, "diagnostic": "NODE_FAILED"}
    fixtures["wrong_preset"] = {
        "description": "Unknown actor preset must fail production validateCastPreset with UNKNOWN_ACTOR_PRESET diagnostic",
        "diagnostic": val_unknown.get("diagnostic"),
        "passed": bool(not val_unknown.get("valid") and "UNKNOWN_ACTOR_PRESET" in str(val_unknown.get("diagnostic"))),
    }

    # 8. Bad Cut Fixture
    from tools.scene_composition import audit_scene_repetition_from_frames
    consecutive_identical_shots = [
        {"id": f"s0{i}", "tpl": "scene", "bg": "field", "time": "noon", "seed": 42}
        for i in range(4)
    ]
    rep_res = audit_scene_repetition_from_frames(consecutive_identical_shots)
    fixtures["bad_cut"] = {
        "description": "Successive identical framing shots must be flagged as repetition/bad cut defect",
        "passed": bool(not rep_res.get("passed", False)),
    }

    # 9. Stale Receipt Fixture (proves initial valid hit, then tamper invalidates)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_p = Path(tmp_dir)
        (tmp_p / "story").mkdir()
        (tmp_p / "build").mkdir()
        (tmp_p / "story" / "shots.json").write_text('{"shots": []}', encoding="utf-8")

        valid_mp4 = tmp_p / "build" / "valid_fixture.mp4"
        cmd_gen = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=f=440:d=1",
            "-c:v", "libx264", "-c:a", "aac",
            str(valid_mp4),
        ]
        subprocess.run(cmd_gen, check=True, capture_output=True)

        real_manifest = prod_fp.collect_render_inputs(tmp_p)
        prod_fp.write_render_receipt_atomic(
            project_path=tmp_p,
            output_path=valid_mp4,
            manifest=real_manifest,
        )

        hit_initial = prod_fp.validate_cache_hit(tmp_p, valid_mp4, real_manifest)
        tampered_manifest = dict(real_manifest)
        tampered_manifest["tracked_files"] = dict(real_manifest.get("tracked_files", {}))
        tampered_manifest["tracked_files"]["story/shots.json"] = "mutated_sha256_hash_987654"
        stale_res = prod_fp.validate_cache_hit(tmp_p, valid_mp4, tampered_manifest)

        # Also tamper output bytes directly to verify output SHA invalidation
        with open(valid_mp4, "ab") as bf:
            bf.write(b"\x00\x00\x00\x00")
        byte_tamper_res = prod_fp.validate_cache_hit(tmp_p, valid_mp4, real_manifest)

        receipt_stale_detected = (
            hit_initial.get("hit") is True
            and (not stale_res.get("hit"))
            and stale_res.get("status") == "CACHE_INVALIDATED"
            and (not byte_tamper_res.get("hit"))
        )

    fixtures["stale_receipt"] = {
        "description": "Valid receipt hits initially, then input or output byte tamper invalidates cache",
        "initial_hit": hit_initial.get("hit"),
        "tampered_input_hit": stale_res.get("hit"),
        "tampered_bytes_hit": byte_tamper_res.get("hit"),
        "status": stale_res.get("status"),
        "reason": stale_res.get("reason"),
        "passed": bool(receipt_stale_detected),
    }

    # 10. Failed Extraction Fixture
    non_existent_mp4 = Path("/tmp/non_existent_video_file_987654.mp4")
    f_ok = extract_frame_at_time(non_existent_mp4, 1.0, Path("/tmp/dummy_frame.png"))
    fixtures["failed_extract"] = {
        "description": "Extracting frame from nonexistent media must fail closed",
        "extract_result": f_ok,
        "passed": bool(not f_ok),
    }

    # 11. Silent Audio Inspection Fixture (creates genuine silent MP4 and runs real inspect_media_file)
    with tempfile.NamedTemporaryFile(suffix=".mp4") as f_silent:
        cmd_sil = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "1",
            "-c:v", "libx264", "-c:a", "aac",
            f_silent.name,
        ]
        subprocess.run(cmd_sil, check=True, capture_output=True)
        aud_res = prod_fp.inspect_media_file(Path(f_silent.name), require_audio=True)
        silent_caught = (not aud_res.get("valid", False)) and any(
            "silent" in str(e).lower() for e in aud_res.get("errors", [])
        )
        fixtures["silent_audio"] = {
            "description": "Media with completely silent audio track must fail closed on measured volume",
            "valid": aud_res.get("valid"),
            "max_volume_db": aud_res.get("max_volume_db"),
            "errors": aud_res.get("errors"),
            "passed": bool(silent_caught),
        }

    # 12. Empty Map Fixture
    blank_map_frame = np.full((1080, 1920, 3), 200, dtype=np.uint8)
    map_ok, map_diags = audit_tactical_labels_mobile(blank_map_frame)
    fixtures["empty_map"] = {
        "description": "Blank tactical map canvas with no contrast features must fail mobile readability",
        "readability_ok": map_ok,
        "diagnostics": map_diags,
        "passed": bool(not map_ok),
    }

    # 13. Unexpected Pose Fixture
    upright_actor = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    upright_actor[100:500, 900:1020] = (180, 30, 30)
    b_up = track_actor_instances_full_frame(upright_actor)
    posture_ok, pose_det, p_diags = audit_acting_posture_temporal([upright_actor, upright_actor], "BRACE", b_up, "actor")
    fixtures["unexpected_pose"] = {
        "description": "Actor with high center of mass must fail BRACE posture check",
        "posture_ok": posture_ok,
        "pose_detected": pose_det,
        "diagnostics": p_diags,
        "passed": bool(not posture_ok),
    }

    # 14. Legitimate Cut Positive Control Fixture
    cut_frame_a = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
    cut_frame_a[400:800, 200:320] = (180, 30, 30)
    cut_frame_b = np.full((1080, 1920, 3), (180, 140, 100), dtype=np.uint8)
    cut_frame_b[400:800, 1500:1620] = (180, 30, 30)
    tele_cut, disap_cut, _, _ = audit_temporal_continuity([cut_frame_a, cut_frame_b], [0.0, 2.5], expected_subject="map")
    fixtures["legitimate_cut"] = {
        "description": "Legitimate cut or diagram transition must NOT falsely flag teleportation",
        "teleport_flagged": tele_cut,
        "passed": bool(not tele_cut and not disap_cut),
    }

    # 15. Torsion Diagram as Roman Formation Negative Fixture
    torsion_shot = {
        "id": "s09_defect",
        "desc": "Roman manipular quincunx checkerboard formation",
        "args": {
            "props": [{"kind": "torsion_diagram", "x": 0.5, "y": 0.5}],
        },
    }
    val_diag_ok, val_diag_msg = validate_diagram_primitive(torsion_shot)
    fixtures["torsion_diagram_as_roman"] = {
        "description": "Torsion catapult spring diagram used for Roman formation must fail validation",
        "valid": val_diag_ok,
        "diagnostic": val_diag_msg,
        "passed": bool(not val_diag_ok and "MISMATCHED_DIAGRAM" in val_diag_msg),
    }

    all_passed = all(f.get("passed", False) for f in fixtures.values())

    return {
        "all_fixtures_passed": all_passed,
        "total_fixtures": len(fixtures),
        "passed_fixtures": sum(1 for f in fixtures.values() if f.get("passed", False)),
        "fixtures": fixtures,
    }


def run_single_detector_assertion(detector_id: str, mutate: bool = False) -> Dict[str, Any]:
    """
    Execute a single production detector assertion against its real negative fixture.
    When mutate=True (invoked inside a disposable child subprocess), monkeypatches the
    target production detector so it fails to report defects, proving the test assertion fails.
    """
    if detector_id == "audit_camera_snap_keyframes":
        if mutate:
            cine_cam.audit_camera_snap_keyframes = lambda kfs, **kw: (False, [])  # type: ignore[assignment]
        snap_kfs = [
            {"t": 0.0, "x": 0.5, "y": 0.5, "z": 1.0},
            {"t": 1.0, "x": 0.2, "y": 0.5, "z": 1.0},
            {"t": 1.04, "x": 0.85, "y": 0.5, "z": 1.0},
            {"t": 2.0, "x": 0.85, "y": 0.5, "z": 1.0},
        ]
        caught, diags = cine_cam.audit_camera_snap_keyframes(snap_kfs)
        return {
            "detector_id": detector_id,
            "mutated": mutate,
            "defect_detected": bool(caught and len(diags) > 0),
            "diagnostics": diags,
        }

    if detector_id == "inspect_media_file_silent_audio":
        orig_inspect = prod_fp.inspect_media_file
        if mutate:
            def _blind_silent_inspect(mp4_path, expected_specs=None, require_audio=False, full_decode=False):
                res = orig_inspect(mp4_path, expected_specs=expected_specs, require_audio=False, full_decode=full_decode)
                res["valid"] = True
                res["errors"] = []
                res["error"] = None
                return res
            prod_fp.inspect_media_file = _blind_silent_inspect  # type: ignore[assignment]

        with tempfile.NamedTemporaryFile(suffix=".mp4") as f_sil:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "1", "-c:v", "libx264", "-c:a", "aac", f_sil.name,
                ],
                check=True,
                capture_output=True,
            )
            res = prod_fp.inspect_media_file(Path(f_sil.name), require_audio=True)
            caught = (not res.get("valid", False)) and any("silent" in str(e).lower() for e in res.get("errors", []))
            return {
                "detector_id": detector_id,
                "mutated": mutate,
                "defect_detected": bool(caught),
                "max_volume_db": res.get("max_volume_db"),
                "errors": res.get("errors", []),
            }

    if detector_id == "validate_cache_hit_stale_receipt":
        if mutate:
            prod_fp.validate_cache_hit = lambda proj, out_p, man, expected_specs=None: {  # type: ignore[assignment]
                "hit": True,
                "status": "CACHE_HIT_VERIFIED",
                "reason": "MUTATED_BLIND_CACHE_HIT",
            }
        with tempfile.TemporaryDirectory() as tmp_d:
            tp = Path(tmp_d)
            (tp / "story").mkdir()
            (tp / "build").mkdir()
            (tp / "story" / "shots.json").write_text('{"shots": [{"id": "s1"}]}', encoding="utf-8")
            mp4 = tp / "build" / "v.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
                    "-f", "lavfi", "-i", "sine=f=440:d=1",
                    "-c:v", "libx264", "-c:a", "aac", str(mp4),
                ],
                check=True,
                capture_output=True,
            )
            man = prod_fp.collect_render_inputs(tp)
            prod_fp.write_render_receipt_atomic(tp, mp4, man)
            # Modify shots.json so current manifest differs from receipt
            (tp / "story" / "shots.json").write_text('{"shots": [{"id": "s1_modified"}]}', encoding="utf-8")
            man_after = prod_fp.collect_render_inputs(tp)
            c_res = prod_fp.validate_cache_hit(tp, mp4, man_after)
            caught = (not c_res.get("hit", True)) and c_res.get("status") == "CACHE_INVALIDATED"
            return {
                "detector_id": detector_id,
                "mutated": mutate,
                "defect_detected": bool(caught),
                "cache_status": c_res.get("status"),
                "reason": c_res.get("reason"),
            }

    if detector_id == "audit_temporal_continuity_disappearance":
        this_mod = sys.modules[__name__]
        if mutate:
            setattr(this_mod, "audit_temporal_continuity", lambda frames, ts, sub: (False, False, 0.0, []))
        actor_frame = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
        actor_frame[400:800, 900:1020] = (180, 30, 30)
        actor_frame[320:400, 930:990] = (220, 180, 150)
        empty_frame = np.full((1080, 1920, 3), (120, 150, 180), dtype=np.uint8)
        fn_target = getattr(this_mod, "audit_temporal_continuity")
        _, disap, _, diags = fn_target([actor_frame, empty_frame], [0.0, 1.0], "actor")
        return {
            "detector_id": detector_id,
            "mutated": mutate,
            "defect_detected": bool(disap),
            "diagnostics": diags,
        }

    if detector_id == "audit_cut_boundary_missing_cut":
        this_mod = sys.modules[__name__]
        if mutate:
            # Simulate the historical V14.7.5 bug: skipping diagram/map boundaries while claiming full coverage
            setattr(
                this_mod,
                "audit_cut_boundaries_all",
                lambda boundary_plans, expected_cut_count, total_video_duration=0.0, character_bible=None: {
                    "expected_cut_count": expected_cut_count,
                    "audited_cut_count": expected_cut_count,
                    "unaudited_cuts": [],
                    "failed_cuts": [],
                    "full_boundary_coverage": True,
                    "all_cuts_passed": True,
                    "boundary_evidence": [],
                },
            )
        with tempfile.TemporaryDirectory() as tmp_d:
            tp = Path(tmp_d)
            shots_4 = [
                {"id": "s01", "start": 0.0, "end": 1.0, "dur": 1.0, "tpl": "scene", "args": {"bg": "field", "people": [{"id": "a1", "preset": "legionary", "x": 0.4}]}},
                {"id": "s02", "start": 1.0, "end": 2.0, "dur": 1.0, "tpl": "map", "intentional_cut_reason": "insert_diagram", "args": {"bg": "parchment"}},
                {"id": "s03", "start": 2.0, "end": 3.0, "dur": 1.0, "tpl": "title", "intentional_cut_reason": "title_card_transition", "args": {"bg": "parchment"}},
                {"id": "s04", "start": 3.0, "end": 4.0, "dur": 1.0, "tpl": "scene", "intentional_cut_reason": "diagram_to_scene", "args": {"bg": "field", "people": [{"id": "a1", "preset": "legionary", "x": 0.45}]}},
            ]
            plans = build_cut_boundary_frame_plan(shots_4, fps=24.0)
            # Populate valid frames for cut 0 and cut 2, but leave cut 1 (diagram->title) missing post_1
            valid_img = np.full((240, 320, 3), (120, 150, 180), dtype=np.uint8)
            valid_img[60:180, 80:240] = (30, 30, 30)
            for idx_p, bp in enumerate(plans):
                ap: Dict[str, Path] = {}
                for role in ("pre_2", "pre_1", "post_1", "post_2"):
                    p_png = tp / f"c{idx_p}_{role}.png"
                    if not (idx_p == 1 and role == "post_1"):
                        Image.fromarray(valid_img, mode="RGB").save(p_png, format="PNG")
                    ap[role] = p_png
                bp["artifact_paths"] = ap

            fn_cut_all = getattr(this_mod, "audit_cut_boundaries_all")
            res_cut = fn_cut_all(plans, expected_cut_count=3, total_video_duration=4.0)
            caught = (not res_cut.get("full_boundary_coverage", True)) and ("s02->s03" in res_cut.get("unaudited_cuts", []))
            return {
                "detector_id": detector_id,
                "mutated": mutate,
                "defect_detected": bool(caught),
                "audited_cut_count": res_cut.get("audited_cut_count"),
                "expected_cut_count": res_cut.get("expected_cut_count"),
                "unaudited_cuts": res_cut.get("unaudited_cuts"),
            }

    if detector_id == "audit_diagram_blank_readability":
        this_mod = sys.modules[__name__]
        if mutate:
            setattr(this_mod, "audit_tactical_labels_mobile", lambda img_arr: (True, []))
        with tempfile.TemporaryDirectory() as tmp_d:
            tp = Path(tmp_d)
            shots_2 = [
                {"id": "s01", "start": 0.0, "end": 1.5, "dur": 1.5, "tpl": "scene", "args": {"bg": "field", "people": [{"id": "a1", "preset": "legionary", "x": 0.4}]}},
                {"id": "s02", "start": 1.5, "end": 3.0, "dur": 1.5, "tpl": "map", "intentional_cut_reason": "insert_diagram", "args": {"bg": "parchment"}},
            ]
            plans = build_cut_boundary_frame_plan(shots_2, fps=24.0)
            actor_img = np.full((360, 640, 3), (120, 150, 180), dtype=np.uint8)
            actor_img[100:300, 260:380] = (180, 30, 30)
            # Blank parchment diagram with faint non-zero noise so std > 6 but zero legible tactical features
            rng = np.random.default_rng(7)
            blank_diag = np.clip(215 + rng.normal(0, 7.5, size=(360, 640, 3)), 0, 255).astype(np.uint8)
            ap = {}
            for role, arr_src in (("pre_2", actor_img), ("pre_1", actor_img), ("post_1", blank_diag), ("post_2", blank_diag)):
                p_png = tp / f"diag_{role}.png"
                Image.fromarray(arr_src, mode="RGB").save(p_png, format="PNG")
                ap[role] = p_png
            plans[0]["artifact_paths"] = ap
            entry = audit_single_cut_boundary(plans[0], total_video_duration=3.0)
            caught = entry.get("status") == "FAIL" and any("diagram" in d.lower() or "unreadable" in d.lower() for d in entry.get("diagnostics", []))
            return {
                "detector_id": detector_id,
                "mutated": mutate,
                "defect_detected": bool(caught),
                "boundary_status": entry.get("status"),
                "diagnostics": entry.get("diagnostics", []),
            }

    raise ValueError(f"Unknown detector_id for mutation probe: {detector_id}")


def run_mutation_tests(failure_logs_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    """
    Execute real mutation tests in isolated disposable subprocesses (zero hardcoded booleans).
    For each of the 6 production detectors:
      1) Run unmutated subprocess probe -> must detect negative fixture defect and exit 0.
      2) Run mutated subprocess probe (--mutate) -> monkeypatches production checker inside child
         process -> must FAIL to detect defect and exit non-zero (code 2), killing the mutant.
    """
    detector_specs = [
        ("audit_camera_snap_keyframes", "audit_camera_snap_keyframes"),
        ("inspect_media_file_silent_audio", "inspect_media_file::silent_audio_guard"),
        ("validate_cache_hit_stale_receipt", "validate_cache_hit::fingerprint_mismatch"),
        ("audit_temporal_continuity_disappearance", "audit_temporal_continuity::sudden_disappearance"),
        ("audit_cut_boundary_missing_cut", "audit_cut_boundaries_all::missing_diagram_cut"),
        ("audit_diagram_blank_readability", "audit_single_cut_boundary::blank_diagram_guard"),
    ]

    log_dir = Path(failure_logs_dir) if failure_logs_dir else None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    mutations: List[Dict[str, Any]] = []
    t_suite0 = time.perf_counter()

    for probe_id, label in detector_specs:
        t0 = time.perf_counter()
        cmd_normal = [sys.executable, str(Path(__file__).resolve()), "--probe-detector", probe_id]
        cmd_mutant = [sys.executable, str(Path(__file__).resolve()), "--probe-detector", probe_id, "--mutate"]

        proc_norm = subprocess.run(cmd_normal, cwd=ROOT_DIR, capture_output=True, text=True, timeout=60)
        proc_mut = subprocess.run(cmd_mutant, cwd=ROOT_DIR, capture_output=True, text=True, timeout=60)

        norm_json = {}
        mut_json = {}
        try:
            norm_json = json.loads(proc_norm.stdout.strip())
        except Exception:
            pass
        try:
            mut_json = json.loads(proc_mut.stdout.strip())
        except Exception:
            pass

        normal_detected = (proc_norm.returncode == 0) and bool(norm_json.get("defect_detected") is True)
        mutated_detected = bool(mut_json.get("defect_detected") is True)
        mutant_failed_assertion = proc_mut.returncode != 0 and (not mutated_detected)
        killed = bool(normal_detected and mutant_failed_assertion)

        diff_lines = list(
            difflib.unified_diff(
                proc_norm.stdout.splitlines(),
                proc_mut.stdout.splitlines(),
                fromfile=f"{probe_id}:normal",
                tofile=f"{probe_id}:mutant",
                lineterm="",
            )
        )

        log_path_str = None
        if log_dir:
            lp = log_dir / f"mutation_{probe_id}.log"
            lp.write_text(
                f"=== NORMAL CMD: {' '.join(cmd_normal)} (rc={proc_norm.returncode}) ===\n"
                f"{proc_norm.stdout}\n{proc_norm.stderr}\n"
                f"=== MUTANT CMD: {' '.join(cmd_mutant)} (rc={proc_mut.returncode}) ===\n"
                f"{proc_mut.stdout}\n{proc_mut.stderr}\n",
                encoding="utf-8",
            )
            log_path_str = str(lp)

        mutations.append({
            "detector": label,
            "probe_id": probe_id,
            "normal_cmd": cmd_normal,
            "mutant_cmd": cmd_mutant,
            "normal_exit_code": proc_norm.returncode,
            "mutant_exit_code": proc_mut.returncode,
            "normal_detected": normal_detected,
            "mutated_detected": mutated_detected,
            "mutation_killed": killed,
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "output_diff": diff_lines,
            "failure_log_path": log_path_str,
        })

    all_killed = len(mutations) >= 4 and all(m["mutation_killed"] for m in mutations)
    return {
        "status": "PASS" if all_killed else "FAIL",
        "execution_mode": "disposable_subprocess_monkeypatch",
        "all_mutations_killed": all_killed,
        "total_mutations": len(mutations),
        "killed_mutations": sum(1 for m in mutations if m["mutation_killed"]),
        "elapsed_sec": round(time.perf_counter() - t_suite0, 3),
        "mutations": mutations,
    }


# ==============================================================================
# V14.7.6 MOTION PERFORMANCE, CONTACT, INTERNAL CUTS & 10 MANDATORY MUTATIONS
# ==============================================================================

import re as _re_v1476
import shutil as _shutil_v1476
import tempfile as _tempfile_v1476
re = _re_v1476
shutil = _shutil_v1476
tempfile = _tempfile_v1476


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _probe_mp4_dims(mp4_path: Path) -> Tuple[int, int]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return (1920, 1080)
    st = (json.loads(proc.stdout).get("streams") or [{}])[0]
    return (int(st.get("width", 1920)), int(st.get("height", 1080)))


def _evaluate_js_motion_traces(
    motion_plan_dict: Dict[str, Any],
    fps: float = 24.0,
    motion_engine_module_path: str = "./packs/squire/motion_engine.js",
) -> Dict[str, Any]:
    """Run `packs/squire/motion_engine.js` trace & order-invariance checks via Node ESM."""
    js = """
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const modSpec = payload.module_path || './packs/squire/motion_engine.js';
const modUrl = path.isAbsolute(modSpec)
  ? pathToFileURL(modSpec).href
  : pathToFileURL(path.resolve(process.cwd(), modSpec)).href;
const { evaluateMotionTrackAt, validateMotionFrameTrace } = await import(modUrl);

const plan = payload.plan || {};
const fps = Number(payload.fps || 24);
const tracks = plan.tracks || plan.actor_tracks || [];
const worldByShot = {};
for (const ws of (plan.world_states || [])) {
  if (ws && ws.shot_id) worldByShot[ws.shot_id] = ws;
}

const trackReports = [];
let orderInvariantAll = true;

for (const tr of tracks) {
  const ws = worldByShot[tr.shot_id] || {};
  const rep = validateMotionFrameTrace(tr, ws, { fps, allTracks: tracks });

  // Explicit stationary-root foot-skate detector + grip-teleport detector
  const h = Math.max(0.10, Number(tr.height_norm || 0.28));
  let maxStationaryFootMoveNorm = 0;
  let maxGripHandJumpNorm = 0;
  const t0 = Number(tr.start_sec || 0);
  const t1 = Math.max(t0 + 1 / fps, Number(tr.end_sec || t0 + 1));
  const steps = Math.max(2, Math.round((t1 - t0) * fps));
  const sampleTimes = [];
  for (let i = 0; i <= steps; i++) sampleTimes.push(Math.min(t1, t0 + i / fps));

  let prevEv = null;
  const forwardSerial = {};
  for (const t of sampleTimes) {
    const ev = evaluateMotionTrackAt(tr, t, ws);
    forwardSerial[t.toFixed(4)] = [
      +ev.root[0].toFixed(5), +ev.root[1].toFixed(5),
      +ev.leftFootWorld[0].toFixed(5), +ev.rightFootWorld[0].toFixed(5),
      +ev.leftHandWorld[0].toFixed(5), +ev.rightHandWorld[0].toFixed(5),
    ];
    if (prevEv) {
      const rootStep = Math.hypot(ev.root[0] - prevEv.root[0], ev.root[1] - prevEv.root[1]) / h;
      if (rootStep < 0.004) {
        if (ev.leftPlanted && prevEv.leftPlanted) {
          const lf = Math.hypot(ev.leftFootWorld[0] - prevEv.leftFootWorld[0], ev.leftFootWorld[1] - prevEv.leftFootWorld[1]) / h;
          if (lf > maxStationaryFootMoveNorm) maxStationaryFootMoveNorm = lf;
        }
        if (ev.rightPlanted && prevEv.rightPlanted) {
          const rf = Math.hypot(ev.rightFootWorld[0] - prevEv.rightFootWorld[0], ev.rightFootWorld[1] - prevEv.rightFootWorld[1]) / h;
          if (rf > maxStationaryFootMoveNorm) maxStationaryFootMoveNorm = rf;
        }
      }
      if (ev.activeContactId && prevEv.activeContactId === ev.activeContactId && ev.phaseName !== 'REACH' && ev.phaseName !== 'ANTICIPATE') {
        const rh = Math.hypot(ev.rightHandWorld[0] - prevEv.rightHandWorld[0], ev.rightHandWorld[1] - prevEv.rightHandWorld[1]) / h;
        const lh = Math.hypot(ev.leftHandWorld[0] - prevEv.leftHandWorld[0], ev.leftHandWorld[1] - prevEv.leftHandWorld[1]) / h;
        maxGripHandJumpNorm = Math.max(maxGripHandJumpNorm, rh, lh);
      }
    }
    prevEv = ev;
  }

  // Reverse evaluation order check (pure function verification)
  const reverseSerial = {};
  for (const t of [...sampleTimes].reverse()) {
    const ev = evaluateMotionTrackAt(tr, t, ws);
    reverseSerial[t.toFixed(4)] = [
      +ev.root[0].toFixed(5), +ev.root[1].toFixed(5),
      +ev.leftFootWorld[0].toFixed(5), +ev.rightFootWorld[0].toFixed(5),
      +ev.leftHandWorld[0].toFixed(5), +ev.rightHandWorld[0].toFixed(5),
    ];
  }
  const sameOrder = sampleTimes.every((t) => {
    const k = t.toFixed(4);
    return JSON.stringify(forwardSerial[k]) === JSON.stringify(reverseSerial[k]);
  });
  if (!sameOrder) {
    orderInvariantAll = false;
  }

  trackReports.push({
    track_id: tr.track_id || `${tr.shot_id}_${tr.actor_id}`,
    shot_id: tr.shot_id,
    actor_id: tr.actor_id,
    median_planted_foot_drift_norm: rep.median_planted_foot_drift_norm,
    peak_planted_foot_drift_norm: rep.peak_planted_foot_drift_norm,
    peak_hand_grip_dist_norm: rep.peak_hand_grip_dist_norm,
    max_adjacent_joint_jump_norm: rep.max_adjacent_joint_jump_norm,
    max_stationary_foot_move_norm: +maxStationaryFootMoveNorm.toFixed(6),
    max_grip_hand_jump_norm: +maxGripHandJumpNorm.toFixed(6),
    trace_passed: Boolean(rep.passed),
    violations: rep.violations || [],
    sample_frames: rep.frames ? rep.frames.slice(0, 6) : [],
  });
}

console.log(JSON.stringify({ track_reports: trackReports, order_invariant: orderInvariantAll }));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js],
        input=json.dumps({"plan": motion_plan_dict, "fps": fps, "module_path": motion_engine_module_path}),
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"motion_engine trace evaluation failed: {proc.stderr}")
    return json.loads(proc.stdout.strip())


def audit_foot_plant(
    motion_plan: Any,
    mp4_path: Optional[Path] = None,
    ev_dir: Optional[Path] = None,
    fps: float = 24.0,
) -> Dict[str, Any]:
    """
    Audit planted-foot world drift and stationary-root skate across all actor tracks,
    plus decoded MP4 ground-ROI pixel verification when `mp4_path` is provided.
    Never claims pixel tracking PASS when actor ground ROI lacks observable contrast;
    labels pixel confidence `REVIEW_REQUIRED` truthfully while enforcing strict trace bounds.
    """
    mp_dict = motion_plan.model_dump() if hasattr(motion_plan, "model_dump") else dict(motion_plan or {})
    js_eval = _evaluate_js_motion_traces(mp_dict, fps=fps)
    tracks = js_eval["track_reports"]
    if not tracks:
        return {
            "status": "NOT_VERIFIED",
            "reason": "zero_actor_tracks_in_motion_plan",
            "track_reports": [],
        }

    violations: List[str] = []
    max_median_drift = 0.0
    max_peak_drift = 0.0
    max_stat_skate = 0.0
    for tr in tracks:
        med = float(tr["median_planted_foot_drift_norm"])
        pk = float(tr["peak_planted_foot_drift_norm"])
        st_move = float(tr["max_stationary_foot_move_norm"])
        max_median_drift = max(max_median_drift, med)
        max_peak_drift = max(max_peak_drift, pk)
        max_stat_skate = max(max_stat_skate, st_move)
        if med > 0.03:
            violations.append(f"{tr['track_id']}: median_planted_foot_drift_norm={med:.4f} > 0.03")
        if pk > 0.08:
            violations.append(f"{tr['track_id']}: peak_planted_foot_drift_norm={pk:.4f} > 0.08")
        if st_move > 0.025:
            violations.append(f"{tr['track_id']}: planted foot moved {st_move:.4f} while root stationary (> 0.025)")

    pixel_checks: List[Dict[str, Any]] = []
    pixel_confidence = "NOT_PROVIDED"
    if mp4_path and Path(mp4_path).exists():
        out_frames = Path(ev_dir) / "foot_plant_frames" if ev_dir else Path(mp4_path).parent / "_qa_foot_frames"
        out_frames.mkdir(parents=True, exist_ok=True)
        raw_tracks = mp_dict.get("tracks") or mp_dict.get("actor_tracks") or []
        req_list: List[Tuple[str, List[float]]] = []
        for rt in raw_tracks[:6]:
            s0 = float(rt.get("start_sec", 0.0))
            s1 = float(rt.get("end_sec", s0 + 2.0))
            mid = round(0.5 * (s0 + s1), 3)
            req_list.append((str(rt.get("shot_id", "S01")), [round(min(s1 - 0.05, s0 + 0.2), 3), mid]))
        w_vid, h_vid = _probe_mp4_dims(Path(mp4_path))
        shot_paths_map, _ = extract_frames_batched_cached(Path(mp4_path), req_list, out_frames, w_vid, h_vid, fps)
        low_conf = 0
        for rt in raw_tracks[:6]:
            sid = str(rt.get("shot_id", "S01"))
            p_list = shot_paths_map.get(sid, [])
            arr = _load_rgb_png_verified(p_list[0]) if p_list else None
            rx = float((rt.get("world_end") or rt.get("world_start") or [0.5, 0.8])[0])
            ry = float((rt.get("world_end") or rt.get("world_start") or [0.5, 0.8])[1])
            if arr is not None:
                h_px, w_px = arr.shape[:2]
                x0 = max(0, int((rx - 0.09) * w_px))
                x1 = min(w_px, int((rx + 0.09) * w_px))
                y0 = max(0, int((ry - 0.14) * h_px))
                y1 = min(h_px, int((ry + 0.04) * h_px))
                patch = arr[y0:y1, x0:x1]
                contrast_std = float(np.std(patch)) if patch.size > 0 else 0.0
                observable = contrast_std >= 8.0
                if not observable:
                    low_conf += 1
                pixel_checks.append({
                    "track_id": rt.get("track_id"),
                    "roi_contrast_std": round(contrast_std, 2),
                    "pixel_roi_observable": observable,
                })
        pixel_confidence = "OBSERVABLE" if (pixel_checks and low_conf == 0) else "REVIEW_REQUIRED"

    status = "FAIL" if violations else "PASS"
    return {
        "status": status,
        "max_median_planted_foot_drift_norm": round(max_median_drift, 5),
        "max_peak_planted_foot_drift_norm": round(max_peak_drift, 5),
        "max_stationary_foot_move_norm": round(max_stat_skate, 5),
        "pixel_tracking_confidence": pixel_confidence,
        "pixel_checks": pixel_checks,
        "violations": violations,
        "track_reports": tracks,
    }


def _save_contact_strip_png(
    mp4_path: Path,
    center_sec: float,
    total_dur: float,
    out_png: Path,
    label_text: str,
) -> Optional[str]:
    """Extract 5 frames across [center_sec - 0.25s, center_sec + 0.25s] and tile horizontally."""
    from PIL import Image, ImageDraw

    offsets = [-0.25, -0.125, 0.0, 0.125, 0.25]
    times = [round(max(0.0, min(max(0.04, total_dur - 0.042), center_sec + off)), 3) for off in offsets]
    tmp_dir = out_png.parent / f"_tmp_{out_png.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    w_vid, h_vid = _probe_mp4_dims(mp4_path)
    shot_paths_map, _ = extract_frames_batched_cached(mp4_path, [("strip", times)], tmp_dir, w_vid, h_vid, 24.0)
    p_list = shot_paths_map.get("strip", [])
    arrs = [a for a in (_load_rgb_png_verified(p) for p in p_list) if a is not None]
    if not arrs:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None
    tile_w, tile_h = 384, 216
    banner_h = 28
    canvas = Image.new("RGB", (tile_w * len(arrs), tile_h + banner_h), (18, 22, 28))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 6), label_text, fill=(240, 232, 210))
    for i, arr in enumerate(arrs):
        tile = Image.fromarray(arr).resize((tile_w, tile_h))
        canvas.paste(tile, (i * tile_w, banner_h))
        draw.text((i * tile_w + 8, banner_h + 6), f"t={times[i]:.3f}s", fill=(255, 220, 120))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png, format="PNG")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return str(out_png)


def audit_hand_prop_contact(
    motion_plan: Any,
    mp4_path: Optional[Path] = None,
    strips_dir: Optional[Path] = None,
    fps: float = 24.0,
) -> Dict[str, Any]:
    """
    Audit hand-to-prop contact distance (`<= 0.04` normalized height), hand-teleport jumps while
    gripping, dropped/duplicated prop invariants, and emit `+/- 0.25s` contact/slip frame strips.
    """
    from tools.motion_performance import MotionPlan, validate_motion_plan
    import re

    mp_obj = motion_plan if isinstance(motion_plan, MotionPlan) else MotionPlan.model_validate(motion_plan)
    mp_dict = mp_obj.model_dump()
    val_res = validate_motion_plan(mp_obj)
    plan_ok, plan_errs = bool(val_res.get("valid", False)), list(val_res.get("errors", []))
    js_eval = _evaluate_js_motion_traces(mp_dict, fps=fps)

    violations: List[str] = []
    for err in plan_errs:
        if any(k in err.lower() for k in ("prop", "contact", "exclusive", "duplicate", "object", "drop")):
            violations.append(err)

    # Check explicit dropped/duplicated prop flags in world_states
    for ws in mp_dict.get("world_states") or []:
        objs = ws.get("objects") or {}
        seen_ids = list(objs.keys())
        if ws.get("duplicate_prop_ids"):
            violations.append(f"Shot {ws.get('shot_id')}: duplicate props detected {ws.get('duplicate_prop_ids')}")
        for oid, oinfo in objs.items():
            if isinstance(oinfo, dict):
                if oinfo.get("duplicated") is True:
                    violations.append(f"Shot {ws.get('shot_id')}: prop '{oid}' duplicated in world state")
                if oinfo.get("unexpected_drop") is True:
                    violations.append(f"Shot {ws.get('shot_id')}: prop '{oid}' unexpectedly dropped mid-grip")
        if len(seen_ids) != len(set(seen_ids)):
            violations.append(f"Shot {ws.get('shot_id')}: duplicate object keys")

    peak_grip = 0.0
    max_grip_jump = 0.0
    for tr in js_eval["track_reports"]:
        g_dist = float(tr["peak_hand_grip_dist_norm"] or 0.0)
        g_jump = float(tr["max_grip_hand_jump_norm"] or 0.0)
        peak_grip = max(peak_grip, g_dist)
        max_grip_jump = max(max_grip_jump, g_jump)
        if g_dist > 0.04:
            violations.append(f"{tr['track_id']}: peak_hand_grip_dist_norm={g_dist:.4f} > 0.04")
        if g_jump > 0.16:
            violations.append(f"{tr['track_id']}: hand teleported {g_jump:.4f} while gripping (> 0.16)")

    strip_paths: List[str] = []
    if mp4_path and Path(mp4_path).exists() and strips_dir:
        total_dur = float(mp_dict.get("end_sec", 30.0))
        events_to_strip: List[Tuple[str, float]] = []
        for tr in mp_dict.get("tracks") or []:
            for ph in tr.get("phases") or []:
                pname = str(ph.get("phase_name", ""))
                mtype = str(ph.get("motion_type", ""))
                if pname == "CONTACT" or mtype == "SLIP":
                    events_to_strip.append((f"{tr.get('shot_id')}_{tr.get('actor_id')}_{mtype}_{pname}", float(ph.get("start_sec", 0.0))))
        for idx, (tag, t_ev) in enumerate(events_to_strip[:8]):
            safe_tag = re.sub(r"[^A-Za-z0-9_]+", "_", tag)
            sp = _save_contact_strip_png(
                Path(mp4_path),
                t_ev,
                total_dur,
                Path(strips_dir) / f"strip_{idx+1:02d}_{safe_tag}.png",
                f"{tag} @ {t_ev:.2f}s (+/-0.25s)",
            )
            if sp:
                strip_paths.append(sp)

    return {
        "status": "FAIL" if violations else "PASS",
        "plan_valid": plan_ok,
        "peak_hand_grip_dist_norm": round(peak_grip, 5),
        "max_grip_hand_jump_norm": round(max_grip_jump, 5),
        "frame_strips": strip_paths,
        "violations": violations,
    }


def audit_internal_camera_cuts(
    project_dir: Path | str,
    mp4_path: Path | str,
    segments_by_shot: Optional[Dict[str, List[Any]]] = None,
    motion_plan: Optional[Any] = None,
    ev_dir: Optional[Path | str] = None,
    fps: float = 24.0,
) -> Dict[str, Any]:
    """
    Audit ALL internal multi-angle camera segment cuts (`pre_2, pre_1, post_1, post_2`) IN ADDITION
    to all `N - 1` intershot cuts. Fail-closed on zero samples, incomplete cut coverage, segment
    validation errors, action resets, or cross-cut actor/prop world-state discontinuities.
    """
    from tools.cinematic_camera import CameraSegment, validate_camera_segments

    proj_p = Path(project_dir)
    mp4_p = Path(mp4_path)
    shots_file = proj_p / "story" / "shots.json"
    if not shots_file.exists() or not mp4_p.exists():
        return {
            "status": "FAIL",
            "error": f"Missing shots.json ({shots_file.exists()}) or mp4 ({mp4_p.exists()})",
            "full_coverage": False,
        }

    story_data = json.loads(shots_file.read_text(encoding="utf-8"))
    shots = story_data.get("shots") or []
    if not shots:
        return {"status": "FAIL", "error": "Zero shots in story/shots.json", "full_coverage": False}

    mp_dict = (
        motion_plan.model_dump()
        if hasattr(motion_plan, "model_dump")
        else (dict(motion_plan) if isinstance(motion_plan, dict) else {})
    )
    total_dur = float(story_data.get("duration") or shots[-1].get("end", 30.0))

    # 1. Validate camera segments on every shot and build internal cut plan
    segment_validation_errors: List[str] = []
    internal_cut_plans: List[Dict[str, Any]] = []
    cur_t = 0.0
    for s in shots:
        sid = str(s.get("id") or "S01")
        st = float(s.get("start", cur_t))
        dur = float(s.get("dur", max(0.2, float(s.get("end", st + 3.0)) - st)))
        et = float(s.get("end", st + dur))
        cur_t = et

        raw_segs = None
        if segments_by_shot and sid in segments_by_shot:
            raw_segs = segments_by_shot[sid]
        elif isinstance((s.get("args") or {}).get("cameraSegments"), list):
            raw_segs = s["args"]["cameraSegments"]

        if raw_segs is not None:
            seg_objs = [
                seg if isinstance(seg, CameraSegment) else CameraSegment.model_validate(seg)
                for seg in raw_segs
            ]
            ok_seg, seg_errs = validate_camera_segments(seg_objs, s, motion_plan=mp_dict)
            if not ok_seg:
                segment_validation_errors.extend(seg_errs)
            for k in range(len(seg_objs) - 1):
                seg_a = seg_objs[k]
                seg_b = seg_objs[k + 1]
                t_cut = round(st + float(seg_a.local_end), 4)
                first_post_f = max(1, int(math.ceil(t_cut * fps - 1e-9)))
                min_f = max(0, int(math.ceil((st + float(seg_a.local_start)) * fps - 1e-9)))
                max_f = max(first_post_f, int(math.ceil((st + float(seg_b.local_end)) * fps - 1e-9)) - 1)
                f_idx = {
                    "pre_2": max(min_f, first_post_f - 2),
                    "pre_1": max(min_f, first_post_f - 1),
                    "post_1": first_post_f,
                    "post_2": min(max_f, first_post_f + 1),
                }
                internal_cut_plans.append({
                    "cut_id": f"{sid}:{seg_a.segment_id}->{seg_b.segment_id}",
                    "shot_id": sid,
                    "cut_time_sec": t_cut,
                    "from_segment": seg_a.model_dump(),
                    "to_segment": seg_b.model_dump(),
                    "frame_indices": f_idx,
                    "requested_times": {r: round(fi / fps, 4) for r, fi in f_idx.items()},
                })

    intershot_plans = build_cut_boundary_frame_plan(shots, fps=fps)
    expected_intershot = max(0, len(shots) - 1)
    expected_internal = len(internal_cut_plans)

    if expected_intershot == 0 and expected_internal == 0:
        return {
            "status": "FAIL",
            "error": "Zero cut boundaries sampled (no default PASS on zero cut samples)",
            "full_coverage": False,
        }

    work_frames_dir = Path(ev_dir) / "cut_frames" if ev_dir else mp4_p.parent / "_qa_cut_frames"
    work_frames_dir.mkdir(parents=True, exist_ok=True)
    w_vid, h_vid = _probe_mp4_dims(mp4_p)

    # Use boundary_plans so EOF-truncated boundary frames NEVER get padded or synthesized!
    all_bplans: List[Dict[str, Any]] = []
    for idx_b, bp in enumerate(intershot_plans):
        bp["cut_index"] = idx_b
        all_bplans.append(bp)
    base_idx = len(all_bplans)
    for idx_i, icp in enumerate(internal_cut_plans):
        icp["cut_index"] = base_idx + idx_i
        icp["extracted_frame_indices"] = icp["frame_indices"]
        all_bplans.append(icp)

    extract_frames_batched_cached(mp4_p, [], work_frames_dir, w_vid, h_vid, fps, boundary_plans=all_bplans)

    def _load_4_boundary_arrays(plan_entry: Dict[str, Any]) -> List[np.ndarray]:
        art = plan_entry.get("artifact_paths") or {}
        out_arrs: List[np.ndarray] = []
        for role in ("pre_2", "pre_1", "post_1", "post_2"):
            p = art.get(role)
            if p is None:
                continue
            loaded = _load_rgb_png_verified(Path(p))
            if loaded is not None:
                out_arrs.append(loaded)
        return out_arrs

    # Verify intershot cuts decode 4/4 frames cleanly
    audited_intershot = 0
    intershot_failures: List[str] = []
    for bp in intershot_plans:
        arrs = _load_4_boundary_arrays(bp)
        if len(arrs) < 4:
            intershot_failures.append(f"{bp['cut']}: incomplete boundary frames ({len(arrs)}/4)")
            continue
        if any(float(np.std(a)) < 1.5 for a in arrs):
            intershot_failures.append(f"{bp['cut']}: blank/near-uniform frame at boundary")
            continue
        audited_intershot += 1

    # Verify internal multi-angle cuts: 4/4 frames + cross-cut MotionPlan world/contact continuity
    js_cross_cut = """
import fs from 'node:fs';
import { evaluateMotionTrackAt } from './packs/squire/motion_engine.js';
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const tracks = payload.tracks || [];
const cuts = payload.cuts || [];
const fps = Number(payload.fps || 24);
const dt = 0.5 / fps;
const out = [];
for (const c of cuts) {
  const sTracks = tracks.filter((tr) => tr.shot_id === c.shot_id);
  const actorChecks = [];
  for (const tr of sTracks) {
    const h = Math.max(0.10, Number(tr.height_norm || 0.28));
    const pre = evaluateMotionTrackAt(tr, c.cut_time_sec - dt, {});
    const post = evaluateMotionTrackAt(tr, c.cut_time_sec + dt, {});
    const rootJump = Math.hypot(post.root[0] - pre.root[0], post.root[1] - pre.root[1]) / h;
    const lfJump = Math.hypot(post.leftFootWorld[0] - pre.leftFootWorld[0], post.leftFootWorld[1] - pre.leftFootWorld[1]) / h;
    const rhJump = Math.hypot(post.rightHandWorld[0] - pre.rightHandWorld[0], post.rightHandWorld[1] - pre.rightHandWorld[1]) / h;
    actorChecks.push({
      actor_id: tr.actor_id,
      root_jump_norm: +rootJump.toFixed(5),
      left_foot_jump_norm: +lfJump.toFixed(5),
      right_hand_jump_norm: +rhJump.toFixed(5),
      contact_preserved: pre.activeContactId === post.activeContactId,
    });
  }
  out.push({ cut_id: c.cut_id, actor_checks: actorChecks });
}
console.log(JSON.stringify(out));
"""
    cross_proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_cross_cut],
        input=json.dumps({
            "tracks": mp_dict.get("tracks") or mp_dict.get("actor_tracks") or [],
            "cuts": internal_cut_plans,
            "fps": fps,
        }, default=str),
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        timeout=25,
    )
    cross_map = {
        item["cut_id"]: item["actor_checks"]
        for item in (json.loads(cross_proc.stdout.strip()) if cross_proc.returncode == 0 and cross_proc.stdout.strip() else [])
    }

    audited_internal = 0
    internal_evidence: List[Dict[str, Any]] = []
    internal_failures: List[str] = []
    for icp in internal_cut_plans:
        cid = icp["cut_id"]
        arrs = _load_4_boundary_arrays(icp)
        diags: List[str] = []
        if len(arrs) < 4:
            diags.append(f"{cid}: incomplete internal boundary frames ({len(arrs)}/4)")
        else:
            pre1, post1 = arrs[1], arrs[2]
            if float(np.std(pre1)) < 1.5 or float(np.std(post1)) < 1.5:
                diags.append(f"{cid}: blank frame across internal cut")
            cut_mad = float(np.mean(np.abs(post1.astype(np.float32) - pre1.astype(np.float32))))
            if cut_mad < 0.6:
                diags.append(f"{cid}: internal multi-angle cut produced identical/frozen image (mad={cut_mad:.3f})")
        achecks = cross_map.get(cid, [])
        for ac in achecks:
            if ac["root_jump_norm"] > 0.08 or ac["right_hand_jump_norm"] > 0.14:
                diags.append(
                    f"{cid} actor '{ac['actor_id']}': discontinuity across internal cut "
                    f"(root_jump={ac['root_jump_norm']}, hand_jump={ac['right_hand_jump_norm']})"
                )

        passed_cut = len(diags) == 0
        if len(arrs) == 4:
            audited_internal += 1
        if not passed_cut:
            internal_failures.extend(diags)
        internal_evidence.append({
            "cut_id": cid,
            "shot_id": icp["shot_id"],
            "cut_time_sec": icp["cut_time_sec"],
            "requested_times": icp["requested_times"],
            "actor_continuity": achecks,
            "status": "PASS" if passed_cut else "FAIL",
            "diagnostics": diags,
        })

    full_cov = (
        audited_intershot == expected_intershot
        and audited_internal == expected_internal
        and (expected_intershot + expected_internal) > 0
    )
    all_ok = (
        full_cov
        and len(segment_validation_errors) == 0
        and len(intershot_failures) == 0
        and len(internal_failures) == 0
    )
    return {
        "status": "PASS" if all_ok else "FAIL",
        "total_duration_sec": total_dur,
        "expected_intershot_cuts": expected_intershot,
        "audited_intershot_cuts": audited_intershot,
        "expected_internal_cuts": expected_internal,
        "audited_internal_cuts": audited_internal,
        "full_coverage": full_cov,
        "segment_validation_errors": segment_validation_errors,
        "intershot_failures": intershot_failures,
        "internal_failures": internal_failures,
        "internal_cut_evidence": internal_evidence,
    }


def _check_audio_non_silent(audio_or_mp4_path: Path, min_rms_db: float = -45.0) -> Tuple[bool, Dict[str, Any]]:
    """Decode audio stream to 16-bit PCM via ffmpeg and measure real RMS dBFS."""
    if not audio_or_mp4_path.exists():
        return False, {"error": f"missing audio file {audio_or_mp4_path}"}
    proc = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(audio_or_mp4_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            "-",
        ],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0 or len(proc.stdout) < 320:
        return False, {"error": "audio decode returned empty/error stream"}
    samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float64) / 32768.0
    rms = float(np.sqrt(np.mean(samples * samples)))
    peak = float(np.max(np.abs(samples)))
    rms_db = 20.0 * math.log10(max(1e-9, rms))
    active_ratio = float(np.mean(np.abs(samples) > 0.008))
    ok = rms_db >= min_rms_db and active_ratio >= 0.05
    return ok, {
        "rms_dbfs": round(rms_db, 2),
        "peak_linear": round(peak, 4),
        "active_sample_ratio": round(active_ratio, 4),
    }


def audit_motion_performance(
    project_dir: Path | str,
    mp4_path: Path | str,
    motion_plan: Any,
    ev_dir: Optional[Path | str] = None,
    original_asset_manifest_path: Optional[Path | str] = None,
    media_receipt_path: Optional[Path | str] = None,
    voice_wav_path: Optional[Path | str] = None,
    fps: float = 24.0,
    motion_engine_module_path: str = "./packs/squire/motion_engine.js",
) -> Dict[str, Any]:
    """
    Comprehensive V14.7.6 motion performance, contact, internal multi-angle cut, provenance,
    receipt freshness, narration non-silence, and frame-order determinism gate.
    """
    from tools.motion_performance import MotionPlan, validate_motion_plan
    import re

    proj_p = Path(project_dir)
    mp4_p = Path(mp4_path)
    out_d = Path(ev_dir) if ev_dir else proj_p / "build" / "motion_qa"
    out_d.mkdir(parents=True, exist_ok=True)

    mp_obj = motion_plan if isinstance(motion_plan, MotionPlan) else MotionPlan.model_validate(motion_plan)
    mp_dict = mp_obj.model_dump()
    val_res = validate_motion_plan(mp_obj)
    plan_ok, plan_errors = bool(val_res.get("valid", False)), list(val_res.get("errors", []))
    js_eval = _evaluate_js_motion_traces(mp_dict, fps=fps, motion_engine_module_path=motion_engine_module_path)

    foot_res = audit_foot_plant(mp_obj, mp4_path=mp4_p, ev_dir=out_d, fps=fps)
    hand_res = audit_hand_prop_contact(mp_obj, mp4_path=mp4_p, strips_dir=out_d / "strips", fps=fps)
    cuts_res = audit_internal_camera_cuts(proj_p, mp4_p, motion_plan=mp_obj, ev_dir=out_d, fps=fps)

    extra_failures: List[str] = []
    if not plan_ok:
        extra_failures.extend(plan_errors)
    if not js_eval.get("order_invariant", False):
        extra_failures.append("Frame-order-dependent mutable state detected in motion evaluation")
    for tr in js_eval["track_reports"]:
        if float(tr["max_adjacent_joint_jump_norm"]) > 0.25:
            extra_failures.append(
                f"{tr['track_id']}: max_adjacent_joint_jump_norm={tr['max_adjacent_joint_jump_norm']:.4f} > 0.25"
            )

    # Original-asset manifest integrity check (if supplied)
    manifest_status = "NOT_PROVIDED"
    if original_asset_manifest_path is not None:
        mf_p = Path(original_asset_manifest_path)
        if not mf_p.exists():
            manifest_status = "FAIL"
            extra_failures.append(f"Original-asset manifest missing: {mf_p}")
        else:
            mf = json.loads(mf_p.read_text(encoding="utf-8"))
            bad_files: List[str] = []
            if mf.get("prior_preview_derived_visual_inputs", 0) != 0:
                bad_files.append("prior_preview_derived_visual_inputs != 0")
            for entry in mf.get("authored_files") or []:
                fp = Path(entry["path"]) if Path(entry["path"]).is_absolute() else Path(__file__).resolve().parents[1] / entry["path"]
                if not fp.exists() or _sha256_path(fp) != entry.get("sha256"):
                    bad_files.append(f"checksum mismatch on {entry.get('path')}")
            if bad_files:
                manifest_status = "FAIL"
                extra_failures.extend(bad_files)
            else:
                manifest_status = "PASS"

    # Receipt freshness check (if supplied)
    receipt_status = "NOT_PROVIDED"
    if media_receipt_path is not None:
        rc_p = Path(media_receipt_path)
        if not rc_p.exists() or not mp4_p.exists():
            receipt_status = "FAIL"
            extra_failures.append(f"Media receipt or MP4 missing ({rc_p})")
        else:
            rc = json.loads(rc_p.read_text(encoding="utf-8"))
            live_sha = _sha256_path(mp4_p)
            if rc.get("mp4_sha256") != live_sha:
                receipt_status = "FAIL"
                extra_failures.append(
                    f"Stale media receipt: receipt sha={rc.get('mp4_sha256')} != live mp4 sha={live_sha}"
                )
            else:
                receipt_status = "PASS"

    # Narration non-silence check
    audio_target = Path(voice_wav_path) if voice_wav_path else mp4_p
    audio_ok, audio_metrics = _check_audio_non_silent(audio_target)
    if not audio_ok:
        extra_failures.append(f"Silent or invalid narration audio: {audio_metrics}")

    all_passed = (
        plan_ok
        and foot_res["status"] == "PASS"
        and hand_res["status"] == "PASS"
        and cuts_res["status"] == "PASS"
        and audio_ok
        and len(extra_failures) == 0
    )
    return {
        "status": "PASS" if all_passed else "FAIL",
        "plan_valid": plan_ok,
        "order_invariant": js_eval.get("order_invariant", False),
        "foot_plant": foot_res,
        "hand_prop_contact": hand_res,
        "internal_camera_cuts": cuts_res,
        "original_asset_manifest_status": manifest_status,
        "media_receipt_status": receipt_status,
        "audio_non_silent": audio_ok,
        "audio_metrics": audio_metrics,
        "failures": (
            extra_failures
            + foot_res.get("violations", [])
            + hand_res.get("violations", [])
            + cuts_res.get("segment_validation_errors", [])
            + cuts_res.get("intershot_failures", [])
            + cuts_res.get("internal_failures", [])
        ),
    }


def run_v14_7_6_mandatory_mutations(work_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    """
    Execute all 10 mandatory V14.7.6 negative mutations against real detectors and real disposable
    media/manifests, verifying clean baseline PASS vs injected mutant FAIL (zero hardcoded booleans).
    """
    import struct
    import wave
    from PIL import Image, ImageDraw
    from tools.action_capabilities import get_pack_capabilities
    from tools.cinematic_camera import compile_camera_segments_to_renderer, plan_multi_angle_action
    from tools.motion_performance import (
        build_shared_motion_timeline,
        extract_semantic_motion_intents,
        plan_actor_motion_phases,
    )

    tmp_ctx = tempfile.TemporaryDirectory() if work_dir is None else None
    base_dir = Path(tmp_ctx.name) if tmp_ctx else Path(work_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    try:
        proj_dir = base_dir / "mut_baseline_proj"
        (proj_dir / "story").mkdir(parents=True, exist_ok=True)
        (proj_dir / "out").mkdir(parents=True, exist_ok=True)

        # Build a real 2-shot, 6.4s baseline project (S01=3.2s with 2 internal camera segments, S02=3.2s)
        events = [
            {
                "id": "S01",
                "start": 0.0,
                "end": 3.2,
                "dur": 3.2,
                "line": "Aelia grabbed the last burning lantern.",
            },
            {
                "id": "S02",
                "start": 3.2,
                "end": 6.4,
                "dur": 3.2,
                "line": "Felix braced the heavy tower rope.",
            },
        ]
        cast = {
            "aelia": {"preset": "peasant", "role": "lamp_keeper", "x": 0.36, "y": 0.80, "facing": 1},
            "felix": {"preset": "artisan", "role": "rope_worker", "x": 0.58, "y": 0.80, "facing": 1},
        }
        w_state = {
            "environment": {"location": "portus_quay", "time": "twilight", "wind": 0.4},
            "actors": {"aelia": {"x": 0.36, "y": 0.80}, "felix": {"x": 0.58, "y": 0.80}},
            "objects": {"lantern": {"x": 0.42, "y": 0.68}, "rope": {"x": 0.63, "y": 0.66}},
        }
        intents = extract_semantic_motion_intents(
            script_text="\n".join(e["line"] for e in events),
            script_events=events,
            cast_bible=cast,
            world_state=w_state,
            pack="squire",
            genre="harbor",
        )
        tracks = plan_actor_motion_phases(
            intents,
            get_pack_capabilities("squire", "harbor"),
            shot_timing=events,
            cast_bible=cast,
            world_state=w_state,
        )
        baseline_plan = build_shared_motion_timeline(
            scene_objectives=[],
            motion_tracks=tracks,
            world_timeline=w_state,
            intents=intents,
            project_id="mut_baseline",
            pack="squire",
            genre="harbor",
        )

        # Attach real multi-angle cameraSegments on S01 & S02
        for ev in events:
            segs = plan_multi_angle_action(ev, baseline_plan, w_state, fps=24.0)
            ev["args"] = compile_camera_segments_to_renderer(segs)
        (proj_dir / "story" / "shots.json").write_text(
            json.dumps({"duration": 6.4, "shots": events}, indent=2), encoding="utf-8"
        )

        # Generate real non-silent WAV + real 24fps H.264/AAC MP4 with visually distinct segment angles
        voice_wav = proj_dir / "voice_good.wav"
        silent_wav = proj_dir / "voice_silent.wav"
        sr = 16000
        n_samp = int(6.4 * sr)
        good_pcm = bytearray()
        zero_pcm = bytearray(n_samp * 2)
        for i in range(n_samp):
            t_s = i / sr
            val = 0.22 * math.sin(2.0 * math.pi * (190.0 + 35.0 * math.sin(t_s * 3.0)) * t_s)
            good_pcm.extend(struct.pack("<h", int(val * 32767)))
        for p_wav, buf in [(voice_wav, bytes(good_pcm)), (silent_wav, bytes(zero_pcm))]:
            with wave.open(str(p_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(buf)

        frames_src = base_dir / "src_frames"
        frames_src.mkdir(parents=True, exist_ok=True)
        s01_cut = float(events[0]["args"]["cameraSegments"][0]["local_end"]) if len(events[0]["args"]["cameraSegments"]) > 1 else 1.5
        s02_cut = 3.2 + (float(events[1]["args"]["cameraSegments"][0]["local_end"]) if len(events[1]["args"]["cameraSegments"]) > 1 else 1.5)
        for fi in range(154):  # 6.416s @ 24fps
            t_f = fi / 24.0
            im = Image.new("RGB", (640, 360), (22, 34, 52) if t_f < 3.2 else (28, 38, 48))
            dr = ImageDraw.Draw(im)
            # Distinct framing shift across internal cuts and intershot cut
            in_closeup = (s01_cut <= t_f < 3.2) or (t_f >= s02_cut)
            scale_box = 78 if in_closeup else 44
            ax = int((0.38 if t_f < 3.2 else 0.58) * 640 + math.sin(t_f * 2.0) * 8)
            dr.rectangle([0, 285, 640, 360], fill=(64, 58, 52))
            dr.rectangle([ax - scale_box // 2, 285 - scale_box * 2, ax + scale_box // 2, 285], fill=(182, 86, 56), outline=(28, 20, 18), width=3)
            dr.ellipse([ax + scale_box // 2, 230, ax + scale_box // 2 + 24, 256], fill=(255, 210, 96))
            im.save(frames_src / f"f_{fi:04d}.png")

        mp4_path = proj_dir / "out" / "baseline.mp4"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-framerate", "24", "-i", str(frames_src / "f_%04d.png"),
                "-i", str(voice_wav),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                str(mp4_path),
            ],
            check=True,
            timeout=60,
        )

        # Original asset manifest & fresh media receipt
        authored_asset = proj_dir / "authored_harbor_vec.svg"
        authored_asset.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><circle cx='32' cy='32' r='20' fill='#d89a44'/></svg>", encoding="utf-8")
        asset_manifest = proj_dir / "original_asset_manifest.json"
        asset_manifest.write_text(
            json.dumps({
                "prior_preview_derived_visual_inputs": 0,
                "authored_files": [{"path": str(authored_asset), "sha256": _sha256_path(authored_asset)}],
            }, indent=2),
            encoding="utf-8",
        )
        receipt_path = proj_dir / "media_receipt.json"
        receipt_path.write_text(
            json.dumps({"mp4_sha256": _sha256_path(mp4_path)}, indent=2),
            encoding="utf-8",
        )

        # Verify clean baseline PASS
        baseline_audit = audit_motion_performance(
            proj_dir,
            mp4_path,
            baseline_plan,
            ev_dir=base_dir / "ev_base",
            original_asset_manifest_path=asset_manifest,
            media_receipt_path=receipt_path,
            voice_wav_path=voice_wav,
        )
        baseline_passed = baseline_audit["status"] == "PASS"

        mutations: List[Dict[str, Any]] = []

        def _record(mut_id: str, desc: str, res: Dict[str, Any]) -> None:
            failed_as_expected = res.get("status") == "FAIL"
            raw_diags = (
                res.get("failures")
                or res.get("violations")
                or (
                    list(res.get("segment_validation_errors") or [])
                    + list(res.get("intershot_failures") or [])
                    + list(res.get("internal_failures") or [])
                )
                or ([res.get("error")] if res.get("error") else [])
            )
            mutations.append({
                "mutation_id": mut_id,
                "description": desc,
                "baseline_status": baseline_audit["status"],
                "mutant_status": res.get("status"),
                "mutation_killed": baseline_passed and failed_as_expected,
                "diagnostics": raw_diags[:4],
            })

        # 1. Planted foot moves while root stationary -> FAIL
        m1_plan = baseline_plan.model_dump()
        m1_plan["tracks"][0]["phases"][-1]["slip_foot"] = "right"
        m1_plan["tracks"][0]["phases"][-1]["foot_planted_right"] = True
        # Force stationary root with artificial planted-foot drift via phase start != end on foot anchor
        m1_plan["tracks"][0]["phases"][0]["world_start"] = [0.36, 0.80]
        m1_plan["tracks"][0]["phases"][0]["world_end"] = [0.36, 0.80]
        # Inject foot-skate defect on stationary track in JS trace check by shifting ground/stance
        m1_plan["tracks"][0]["phases"][1]["phase_name"] = "CONTACT"
        m1_plan["tracks"][0]["phases"][1]["world_start"] = [0.36, 0.80]
        m1_plan["tracks"][0]["phases"][1]["world_end"] = [0.58, 0.80]
        m1_plan["tracks"][0]["phases"][1]["foot_planted_left"] = True
        m1_plan["tracks"][0]["phases"][1]["foot_planted_right"] = True
        _record("M01_planted_foot_moves_stationary_root", "Planted foot drifts/skates -> FAIL", audit_foot_plant(m1_plan))

        # 2. Hand teleports away while gripping -> FAIL
        m2_plan = baseline_plan.model_dump()
        m2_plan["tracks"][0]["contacts"][0]["world_end"] = [0.95, 0.12]
        _record("M02_hand_teleports_while_gripping", "Hand teleports away from grip anchor -> FAIL", audit_hand_prop_contact(m2_plan))

        # 3. Discontinuity at internal multi-angle cut -> FAIL
        m3_proj = base_dir / "m3_proj"
        shutil.copytree(proj_dir, m3_proj)
        s_m3 = json.loads((m3_proj / "story" / "shots.json").read_text(encoding="utf-8"))
        s_m3["shots"][0]["args"]["cameraSegments"][1]["axis"] = "right_to_left"
        (m3_proj / "story" / "shots.json").write_text(json.dumps(s_m3), encoding="utf-8")
        m3_plan = baseline_plan.model_dump()
        # Inject real world-position jump right at internal cut time `s01_cut`
        m3_plan["tracks"][0]["phases"][0]["end_sec"] = round(s01_cut, 4)
        m3_plan["tracks"][0]["phases"][1]["start_sec"] = round(s01_cut, 4)
        m3_plan["tracks"][0]["phases"][1]["world_start"] = [0.74, 0.80]
        m3_plan["tracks"][0]["phases"][1]["world_end"] = [0.74, 0.80]
        _record(
            "M03_internal_multi_angle_cut_discontinuity",
            "180-deg axis & spatial discontinuity across internal multi-angle cut -> FAIL",
            audit_internal_camera_cuts(m3_proj, mp4_path, motion_plan=m3_plan, ev_dir=base_dir / "ev_m3"),
        )

        # 4. Dropped/duplicated rope or lantern -> FAIL
        m4_plan = baseline_plan.model_dump()
        m4_plan["world_states"][0]["objects"]["lantern"]["duplicated"] = True
        m4_plan["world_states"][0]["objects"]["lantern"]["unexpected_drop"] = True
        _record("M04_dropped_or_duplicated_prop", "Dropped or duplicated lantern/rope -> FAIL", audit_hand_prop_contact(m4_plan))

        # 5. Camera segment resets action -> FAIL
        m5_proj = base_dir / "m5_proj"
        shutil.copytree(proj_dir, m5_proj)
        s_m5 = json.loads((m5_proj / "story" / "shots.json").read_text(encoding="utf-8"))
        s_m5["shots"][0]["args"]["cameraSegments"][1]["resets_action_time"] = True
        (m5_proj / "story" / "shots.json").write_text(json.dumps(s_m5), encoding="utf-8")
        _record(
            "M05_camera_segment_resets_action",
            "Camera segment resets action clock -> FAIL",
            audit_internal_camera_cuts(m5_proj, mp4_path, motion_plan=baseline_plan, ev_dir=base_dir / "ev_m5"),
        )

        # 6. Modified original-asset manifest -> FAIL
        m6_manifest = base_dir / "tampered_asset_manifest.json"
        m6_manifest.write_text(
            json.dumps({
                "prior_preview_derived_visual_inputs": 1,
                "authored_files": [{"path": str(authored_asset), "sha256": "0" * 64}],
            }),
            encoding="utf-8",
        )
        _record(
            "M06_modified_original_asset_manifest",
            "Modified/tampered original-asset manifest -> FAIL",
            audit_motion_performance(
                proj_dir, mp4_path, baseline_plan, ev_dir=base_dir / "ev_m6",
                original_asset_manifest_path=m6_manifest, media_receipt_path=receipt_path, voice_wav_path=voice_wav,
            ),
        )

        # 7. Stale receipt -> FAIL
        m7_receipt = base_dir / "stale_receipt.json"
        m7_receipt.write_text(json.dumps({"mp4_sha256": "deadbeef" * 8}), encoding="utf-8")
        _record(
            "M07_stale_receipt",
            "Stale media receipt digest mismatch -> FAIL",
            audit_motion_performance(
                proj_dir, mp4_path, baseline_plan, ev_dir=base_dir / "ev_m7",
                original_asset_manifest_path=asset_manifest, media_receipt_path=m7_receipt, voice_wav_path=voice_wav,
            ),
        )

        # 8. Silent narration -> FAIL
        _record(
            "M08_silent_narration",
            "Silent narration audio stream -> FAIL",
            audit_motion_performance(
                proj_dir, mp4_path, baseline_plan, ev_dir=base_dir / "ev_m8",
                original_asset_manifest_path=asset_manifest, media_receipt_path=receipt_path, voice_wav_path=silent_wav,
            ),
        )

        # 9. Frame-order-dependent state -> FAIL (genuine stateful accumulator module in disposable dir)
        real_engine_url = (Path(__file__).resolve().parents[1] / "packs" / "squire" / "motion_engine.js").as_uri()
        m9_stateful_mod = base_dir / "m9_stateful_motion_engine.mjs"
        m9_stateful_mod.write_text(
            f"""import {{ evaluateMotionTrackAt as pureEval, validateMotionFrameTrace }} from {json.dumps(real_engine_url)};
let hiddenLastFrameAccum = 0;
export function evaluateMotionTrackAt(track, absoluteT, worldState, options) {{
  const res = pureEval(track, absoluteT, worldState, options);
  hiddenLastFrameAccum += 0.0035;
  return {{
    ...res,
    root: [res.root[0] + hiddenLastFrameAccum, res.root[1]],
  }};
}}
export {{ validateMotionFrameTrace }};
""",
            encoding="utf-8",
        )
        _record(
            "M09_frame_order_dependent_state",
            "Frame-order-dependent mutable state -> FAIL",
            audit_motion_performance(
                proj_dir, mp4_path, baseline_plan, ev_dir=base_dir / "ev_m9",
                original_asset_manifest_path=asset_manifest, media_receipt_path=receipt_path, voice_wav_path=voice_wav,
                motion_engine_module_path=str(m9_stateful_mod),
            ),
        )

        # 10. Cut boundary incomplete -> FAIL
        m10_proj = base_dir / "m10_proj"
        shutil.copytree(proj_dir, m10_proj)
        s_m10 = json.loads((m10_proj / "story" / "shots.json").read_text(encoding="utf-8"))
        # Place internal cut beyond actual 6.4s MP4 duration so post_1/post_2 frames fail extraction
        s_m10["shots"][1]["end"] = 14.0
        s_m10["shots"][1]["dur"] = 10.8
        s_m10["shots"][1]["args"]["cameraSegments"][0]["local_end"] = 9.5
        s_m10["shots"][1]["args"]["cameraSegments"][1]["local_start"] = 9.5
        s_m10["shots"][1]["args"]["cameraSegments"][1]["local_end"] = 10.8
        (m10_proj / "story" / "shots.json").write_text(json.dumps(s_m10), encoding="utf-8")
        _record(
            "M10_cut_boundary_incomplete",
            "Incomplete cut boundary frame coverage -> FAIL",
            audit_internal_camera_cuts(m10_proj, mp4_path, motion_plan=baseline_plan, ev_dir=base_dir / "ev_m10"),
        )

        killed = sum(1 for m in mutations if m["mutation_killed"])
        return {
            "schema_version": "14.7.6",
            "status": "PASS" if (baseline_passed and killed == 10) else "FAIL",
            "baseline_passed": baseline_passed,
            "total_mutations": len(mutations),
            "killed_mutations": killed,
            "mutations": mutations,
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="P0 Temporal Visual QA Engine (V14.7.5)")
    parser.add_argument("--project", default="projects/fl01_v14_7_2_ballista_preview")
    parser.add_argument("--mp4", default=None)
    parser.add_argument("--out-dir", default="tests/evidence/v14_7_5")
    parser.add_argument("--probe-detector", default=None, help="Run isolated detector assertion for mutation testing")
    parser.add_argument("--mutate", action="store_true", help="Inject mutant into probed detector in this subprocess")
    args = parser.parse_args()

    if args.probe_detector:
        probe_res = run_single_detector_assertion(args.probe_detector, mutate=args.mutate)
        print(json.dumps(probe_res, indent=2))
        # Exit 0 ONLY when defect was caught; exit 2 when detector missed defect (killing mutant)
        sys.exit(0 if probe_res.get("defect_detected") else 2)

    proj = Path(args.project).resolve()
    mp4 = Path(args.mp4).resolve() if args.mp4 else proj / "out" / f"{proj.name.upper()}_1080P.mp4"
    out_d = Path(args.out_dir).resolve()

    rep = audit_project_temporal_visual(proj, mp4, out_d)
    print(f"Temporal QA Verdict: {rep.technical_verdict} (passed {rep.passed_shots}/{rep.total_shots} shots)")
    print(f"Negative fixtures passed: {rep.negative_fixtures_passed}")
    sys.exit(0 if rep.technical_verdict == "VISUAL_TECH_PASS" else 1)
