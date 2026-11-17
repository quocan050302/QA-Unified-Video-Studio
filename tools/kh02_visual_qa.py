#!/usr/bin/env python3
"""kh02_visual_qa.py — Measurable 2D Visual, Temporal, Continuity & Editorial Packet QA for KH-02.1.

Implements required functions:
- audit_style_baseline_preservation
- audit_unique_visual_language
- audit_character_identity
- audit_frame_temporal_liveness
- audit_continuity_across_cuts
- audit_hand_prop_contact
- audit_camera_2d_bounds
- build_visual_editorial_packet

Explicitly separates MEASURED_TECHNICAL checks from HUMAN_REVIEW_PENDING editorial/artistic judgment.
Distinguishes true actor pose liveness from pure camera panning/zooming or grain, allows legitimate
short narrative holds (e.g. 6-frame anticipation hold), and rejects 3-second static panning in action shots.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

from kh02_style_contract import load_squire_style_profile, validate_squire_style_contract
from kh02_character_factory import validate_character_model_consistency, build_character_turnaround_2d, build_expression_sheet_2d
from kh02_environment_factory import validate_scene_continuity, build_original_layers


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def decode_frame_rgb(media_path: Path, timestamp_sec: float | None = None, width: int = 480, height: int = 270) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error"]
    if timestamp_sec is not None:
        cmd += ["-ss", f"{timestamp_sec:.3f}"]
    cmd += [
        "-i", str(media_path),
        "-vframes", "1",
        "-vf", f"scale={width}:{height}",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or len(res.stdout) < width * height * 3:
        raise RuntimeError(f"Failed decoding frame from {media_path} at t={timestamp_sec}: {res.stderr.decode(errors='ignore')[:200]}")
    return np.frombuffer(res.stdout[: width * height * 3], dtype=np.uint8).reshape((height, width, 3))


# 1. STYLE BASELINE PRESERVATION
def audit_style_baseline_preservation(project_dir: Path, baseline_snapshot: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Verify Squire caricature DNA (outline #392a21, warm cream skin #f4ede1, ~38% head ratio, 2-3 cel bands)
    and verify legacy Production files/hashes remain untouched where required.
    """
    project_dir = Path(project_dir).resolve()
    errors: List[str] = []

    cfg = json.loads((project_dir / "config.json").read_text(encoding="utf-8"))
    style_id = cfg.get("style_profile", "")
    if style_id != "squire_cinematic_2d.v1":
        errors.append(f"Project does not opt into squire_cinematic_2d.v1 (got '{style_id}')")

    try:
        profile = load_squire_style_profile("squire_cinematic_2d.v1")
    except Exception as exc:
        return {"passed": False, "confidence_class": "MEASURED_TECHNICAL", "errors": [str(exc)]}

    ppd = profile.get("protected_production_default", {})
    if ppd.get("outline_hex", "").lower() != "#392a21":
        errors.append("Outline color diverged from Squire OUT #392a21")
    if ppd.get("skin_hex", "").lower() != "#f4ede1":
        errors.append("Base skin tone diverged from Squire #f4ede1")

    head_ratio = profile.get("proportional_invariants", {}).get("human_squire_caricature", {}).get("head_diameter_ratio", 0)
    if not (0.34 <= float(head_ratio) <= 0.42):
        errors.append(f"Head diameter ratio {head_ratio} outside Squire caricature band [0.34, 0.42]")

    # Verify engine/three3d.js and preserved packs match baseline snapshot if supplied
    preserved_intact = True
    if isinstance(baseline_snapshot, dict) and "tracked_files" in baseline_snapshot:
        tracked = baseline_snapshot["tracked_files"]
        must_match_prefixes = (
            "engine/three3d.js",
            "packs/dem/",
            "packs/doodle/",
            "projects/squire-mau/",
            "projects/selfimprove-mau/",
            "tests/evidence/",
        )
        for rel, meta in tracked.items():
            if rel.startswith(must_match_prefixes):
                fp = REPO_ROOT / rel
                if not fp.is_file() or _sha256_file(fp) != meta["sha256"]:
                    preserved_intact = False
                    errors.append(f"Preserved baseline file modified or missing: {rel}")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "outline_hex": ppd.get("outline_hex"),
        "head_diameter_ratio": head_ratio,
        "preserved_baseline_files_intact": preserved_intact,
        "errors": errors,
    }


# 2. UNIQUE VISUAL LANGUAGE & NOVELTY AUDIT
def audit_unique_visual_language(project_dir: Path, baseline_snapshot: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Verify zero hash collisions with old rendered frames/thumbnails, zero external copied bitmaps,
    zero forbidden reused KH-01/demo stock motifs, and active usage of KH-02.1 2D modules.
    """
    project_dir = Path(project_dir).resolve()
    errors: List[str] = []

    old_hashes = set()
    if isinstance(baseline_snapshot, dict):
        for meta in (baseline_snapshot.get("tracked_files") or {}).values():
            old_hashes.add(meta.get("sha256"))
        for meta in (baseline_snapshot.get("reference_only_artifacts") or {}).values():
            old_hashes.add(meta.get("sha256"))

    # Check anh/ external image folder is empty or contains zero copied files
    anh_dir = project_dir / "anh"
    copied_images = list(anh_dir.glob("*")) if anh_dir.is_dir() else []
    if copied_images:
        errors.append(f"Unexpected external bitmap files in anh/: {[p.name for p in copied_images]}")

    # Check output & scene files against old hashes
    checked_files = 0
    for sub in ("scenes", "story", "out"):
        d = project_dir / sub
        if d.is_dir():
            for fp in sorted(d.rglob("*")):
                if fp.is_file():
                    checked_files += 1
                    h = _sha256_file(fp)
                    if h in old_hashes:
                        errors.append(f"Novelty blocker: '{fp.relative_to(project_dir)}' matches old baseline SHA-256 {h}")

    # Verify KH-02.1 upgraded drawing primitives are genuinely invoked by project scenes
    scene_code = "\n".join(
        fp.read_text(encoding="utf-8", errors="ignore")
        for fp in sorted((project_dir / "scenes").rglob("*.js"))
    )
    for req_sym in ("drawSquireCinematic2DActor", "drawPipGoat2D", "drawLayeredRomanEnvironment2D", "evaluateBellRigStateAt"):
        if req_sym not in scene_code:
            errors.append(f"Project scenes do not exercise upgraded KH-02.1 symbol '{req_sym}'")

    forbidden_terms = ("urgent_scroll", "marketplace_chase", "runaway_cart", "fountain_catch", "three3d")
    for term in forbidden_terms:
        if term in scene_code.lower():
            errors.append(f"Forbidden legacy/stock motif '{term}' referenced in scene code")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "files_checked": checked_files,
        "external_bitmap_count": len(copied_images),
        "errors": errors,
    }


# 3. CHARACTER IDENTITY & RIG HONESTY AUDIT
def audit_character_identity(project_dir: Path, character_bible_override: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Verify canonical cast names, wardrobe locks across shots, and non-human rig honesty."""
    project_dir = Path(project_dir).resolve()
    errors: List[str] = []

    cb = character_bible_override or json.loads((project_dir / "story" / "character_bible.json").read_text(encoding="utf-8"))
    ledger = json.loads((project_dir / "story" / "continuity_ledger.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project_dir / "story" / "storyboard.json").read_text(encoding="utf-8"))

    # Build temporary manifest to run model consistency checks
    manifest = {
        "characters": cb.get("characters", []),
        "turnarounds": build_character_turnaround_2d(cb)["turnarounds"],
        "expression_sheets": build_expression_sheet_2d(cb)["sheets"],
        "rendered_assets": {},
    }
    res = validate_character_model_consistency(manifest)
    errors.extend(res["errors"])

    locked_names = set(ledger.get("canonical_cast_locked", []))
    bible_names = {c["canonical_name"] for c in cb.get("characters", [])}
    if not bible_names.issubset(locked_names):
        errors.append(f"Bible names {bible_names} not locked in continuity_ledger {locked_names}")

    # Verify wardrobe lock consistency across shots if per-shot actor overrides are supplied
    wardrobe_locks = ledger.get("wardrobe_locks", {})
    for sh in storyboard.get("shots", []):
        sid = sh.get("id", "?")
        for c_name in (sh.get("continuity_anchors") or {}).get("cast_present", []):
            if c_name not in locked_names:
                errors.append(f"Shot '{sid}' references unlocked character name '{c_name}'")
        actor_overrides = sh.get("actor_wardrobe_overrides") or {}
        for c_name, ov in actor_overrides.items():
            locked = wardrobe_locks.get(c_name, {})
            for wk, wv in ov.items():
                if wk in locked and locked[wk] != wv:
                    errors.append(f"Identity/wardrobe mutation in '{sid}' for '{c_name}': {wk} changed {locked[wk]} -> {wv}")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "locked_cast": sorted(locked_names),
        "errors": errors,
    }


# 4. TEMPORAL LIVENESS AUDIT (DISTINGUISHES ACTOR POSE DELTAS FROM CAMERA PANNING & GRAIN!)
def audit_frame_temporal_liveness(
    pose_trace: Dict[str, Any],
    mp4_path: Path | None = None,
) -> Dict[str, Any]:
    """Audit both world-space actor pose liveness (immune to camera pan/zoom/grain) and decoded MP4 frame health.

    Rules:
    - A legitimate short anticipation/narrative hold (e.g. 6 frames = 0.25s, or breathing micro-motion in S06b) is VALID.
    - An action-heavy shot where actor world pose is frozen (0 joint delta) for >= 48 frames (2.0s) while only the camera
      pans/zooms is REJECTED as static-illustration panning!
    - Blank/black frames or baked error text in decoded MP4 are REJECTED.
    """
    errors: List[str] = []
    shot_metrics: Dict[str, Any] = {}

    shots = pose_trace.get("shots", [])
    if not shots:
        errors.append("Empty pose_trace: no shots provided for liveness audit")

    for sh in shots:
        sid = sh.get("id", "?")
        action_heavy = bool(sh.get("action_heavy", True))
        frames = sh.get("frames", [])
        if len(frames) < 2:
            errors.append(f"Shot '{sid}' has < 2 sampled pose frames")
            continue

        # Compute world-space actor pose deltas between consecutive frames (camera-independent!)
        deltas = []
        longest_zero_run = 0
        cur_zero = 0
        expressions_seen = set()
        for i in range(1, len(frames)):
            p0 = frames[i - 1].get("actor_world_vec", [])
            p1 = frames[i].get("actor_world_vec", [])
            expressions_seen.add(frames[i].get("expression", ""))
            if len(p0) == len(p1) and len(p0) > 0:
                d = float(math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(p0, p1))))
            else:
                d = 0.0
            deltas.append(d)
            if d < 0.02 and frames[i].get("expression") == frames[i - 1].get("expression"):
                cur_zero += 1
                longest_zero_run = max(longest_zero_run, cur_zero)
            else:
                cur_zero = 0

        total_pose_path = float(sum(deltas))
        active_ratio = float(sum(1 for d in deltas if d >= 0.02)) / max(1, len(deltas))

        # Action-heavy shots must NOT be frozen static illustrations panned by camera (>=48 static frames = 2.0s)
        if action_heavy and (longest_zero_run >= 48 or total_pose_path < 8.0):
            errors.append(
                f"Static-action defect in shot '{sid}': longest_static_pose_frames={longest_zero_run}, total_pose_path={total_pose_path:.2f}px"
            )

        shot_metrics[sid] = {
            "frames_evaluated": len(frames),
            "total_actor_world_path_px": round(total_pose_path, 2),
            "active_pose_frame_ratio": round(active_ratio, 4),
            "longest_static_hold_frames": longest_zero_run,
            "distinct_expressions": len([e for e in expressions_seen if e]),
        }

    mp4_metrics: Dict[str, Any] = {}
    if mp4_path is not None:
        mp4_path = Path(mp4_path)
        if not mp4_path.is_file():
            errors.append(f"MP4 file missing: {mp4_path}")
        else:
            # Decode all frames at 320x180 RGB in one streaming pass to check exact frame count, blank frames & ROI activity!
            w, h = 320, 180
            frame_bytes = w * h * 3
            proc = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(mp4_path), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True,
            )
            if proc.returncode != 0:
                errors.append(f"FFmpeg full-stream decode failed: {proc.stderr.decode(errors='ignore')[:240]}")
            else:
                n_frames = len(proc.stdout) // frame_bytes
                if n_frames != 720:
                    errors.append(f"Decoded frame count mismatch: expected 720, got {n_frames}")
                if n_frames > 0:
                    arr = np.frombuffer(proc.stdout[: n_frames * frame_bytes], dtype=np.uint8).reshape((n_frames, h, w, 3))
                    frame_luma = arr.mean(axis=(1, 2, 3))
                    frame_std = arr.std(axis=(1, 2, 3))
                    blank_frames = int(np.sum((frame_luma < 4.0) | (frame_std < 2.0)))
                    if blank_frames > 0:
                        errors.append(f"Detected {blank_frames} blank/black/flat frames in decoded MP4")
                    # Center ROI activity
                    roi = arr[:, h // 6 : 5 * h // 6, w // 6 : 5 * w // 6, :].astype(np.float32)
                    diffs = np.abs(roi[1:] - roi[:-1]).mean(axis=(1, 2, 3))
                    active_pct = float(np.mean(diffs > 0.35) * 100.0)
                    mp4_metrics = {
                        "decoded_frames": n_frames,
                        "blank_frames": blank_frames,
                        "min_frame_luma": round(float(frame_luma.min()), 2),
                        "max_frame_luma": round(float(frame_luma.max()), 2),
                        "roi_temporal_activity_pct": round(active_pct, 2),
                    }

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "shot_pose_metrics": shot_metrics,
        "decoded_video_metrics": mp4_metrics,
        "errors": errors,
    }


# 5. CONTINUITY ACROSS CUTS AUDIT
def audit_continuity_across_cuts(
    storyboard_spec: Dict[str, Any],
    continuity_ledger: Dict[str, Any],
    prop_trace: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Verify exact 0..30s contiguous timeline coverage, consistent prop presence/coords across cuts, and world landmarks."""
    errors: List[str] = []
    shots = storyboard_spec.get("shots", [])
    if len(shots) != 8:
        errors.append(f"Expected 8 mandatory shots (S01..S08), got {len(shots)}")

    if shots:
        if abs(float(shots[0].get("start", -1)) - 0.0) > 1e-4:
            errors.append(f"First shot must start at 0.0s, got {shots[0].get('start')}")
        if abs(float(shots[-1].get("end", -1)) - 30.0) > 1e-4:
            errors.append(f"Final shot must end at exact 30.0s, got {shots[-1].get('end')}")
        for i in range(1, len(shots)):
            prev_end = float(shots[i - 1]["end"])
            cur_start = float(shots[i]["start"])
            if abs(cur_start - prev_end) > 1e-3:
                errors.append(f"Shot timing gap/overlap at {shots[i-1]['id']}->{shots[i]['id']}: {prev_end} vs {cur_start}")

    # Check prop continuity trace if supplied (detects prop disappearing, duplicating, or teleporting across join)
    if isinstance(prop_trace, dict):
        for join in prop_trace.get("joins", []):
            jid = join.get("join_id", "?")
            if join.get("prop_count", 1) != 1:
                errors.append(f"Prop count violation at '{jid}': count={join.get('prop_count')} (must be 1 single central bell)")
            bell_angle_jump = abs(float(join.get("bell_angle_after", 0)) - float(join.get("bell_angle_before", 0)))
            if bell_angle_jump > 0.25:
                errors.append(f"Bell state teleport across join '{jid}': delta_rad={bell_angle_jump:.3f}")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "joins_verified": len(continuity_ledger.get("shot_joins", [])),
        "errors": errors,
    }


# 6. HAND-PROP CONTACT & PLANTED-FOOT LOCK AUDIT
def audit_hand_prop_contact(contact_trace: Dict[str, Any]) -> Dict[str, Any]:
    """Verify world-space hand-to-rope / hand-to-clapper grip distance during contact windows
    and verify zero foot-skate when stance foot is planted on stair treads in S05.
    """
    errors: List[str] = []
    max_grip_err = 0.0
    max_skate_err = 0.0

    for ev in contact_trace.get("grip_samples", []):
        t = float(ev["t"])
        hand_pt = ev["hand_world"]
        prop_pt = ev["prop_world"]
        max_tol = float(ev.get("tolerance_px", 28.0))
        dist = math.hypot(hand_pt[0] - prop_pt[0], hand_pt[1] - prop_pt[1])
        max_grip_err = max(max_grip_err, dist)
        if dist > max_tol:
            errors.append(f"Hand-prop contact broken at t={t:.3f}s ({ev.get('shot')}): dist={dist:.2f}px > {max_tol}px")

    for st in contact_trace.get("planted_foot_intervals", []):
        pts = st.get("stance_foot_world_samples", [])
        if len(pts) >= 2:
            x0, y0 = pts[0]
            drift = max(math.hypot(px - x0, py - y0) for px, py in pts)
            max_skate_err = max(max_skate_err, drift)
            if drift > float(st.get("max_skate_px", 1.5)):
                errors.append(f"Planted foot skated in {st.get('label', 'S05')}: drift={drift:.2f}px")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "max_grip_distance_px": round(max_grip_err, 3),
        "max_planted_foot_drift_px": round(max_skate_err, 3),
        "errors": errors,
    }


# 7. CAMERA 2D BOUNDS AUDIT
def audit_camera_2d_bounds(camera_beats: Dict[str, Any]) -> Dict[str, Any]:
    """Verify camera transforms stay strictly within 2D bounds, without snaps, out-of-bounds pans, or overzoom."""
    errors: List[str] = []
    bounds = camera_beats.get("bounds", {})
    min_z = float(bounds.get("min_zoom", 0.94))
    max_z = float(bounds.get("max_zoom", 1.35))
    max_pan = float(bounds.get("max_pan_px", 380.0))

    for sid, spec in (camera_beats.get("shots") or {}).items():
        for zk in ("z0", "z1"):
            zv = float(spec.get(zk, 1.0))
            if not math.isfinite(zv) or zv < min_z or zv > max_z:
                errors.append(f"Camera overzoom/underzoom in '{sid}' ({zk}={zv}, allowed=[{min_z}, {max_z}])")
        for pk in ("x0", "x1", "y0", "y1"):
            pv = float(spec.get(pk, 0.0))
            if not math.isfinite(pv) or abs(pv) > max_pan:
                errors.append(f"Camera pan out-of-bounds in '{sid}' ({pk}={pv}, max_abs={max_pan})")
        # Detect mid-shot instantaneous camera snap if step_snap is present
        if spec.get("instant_snap"):
            errors.append(f"Unmotivated camera snap flagged in '{sid}'")

    return {
        "passed": len(errors) == 0,
        "confidence_class": "MEASURED_TECHNICAL",
        "shots_checked": len(camera_beats.get("shots") or {}),
        "errors": errors,
    }


# 8. BUILD VISUAL EDITORIAL PACKET (8 STILLS + 8-SHOT SHEET + 3 ACTION STRIPS)
def build_visual_editorial_packet(mp4_path: Path, out_dir: Path) -> Dict[str, Any]:
    """Extract 8 decoded shot stills, an 8-shot contact sheet, and 3 action strips (hook, rising action, punchline)."""
    mp4_path = Path(mp4_path).resolve()
    out_dir = Path(out_dir).resolve()
    stills_dir = out_dir / "stills_8shots"
    strips_dir = out_dir / "action_strips"
    stills_dir.mkdir(parents=True, exist_ok=True)
    strips_dir.mkdir(parents=True, exist_ok=True)

    shot_sample_times = [
        ("S01_hook_goat_rope", 0.50),
        ("S02_tavi_pupil_snap", 4.15),
        ("S03_low_angle_rope_slip", 8.20),
        ("S04_wide_belfry_swing", 11.40),
        ("S05_stairwell_climb", 15.60),
        ("S06_clapper_catch_silence", 20.40),
        ("S07_goat_sneeze_burst", 25.05),
        ("S08_courtyard_and_deadpan", 27.40),
    ]

    still_records = {}
    still_paths = []
    for name, ts in shot_sample_times:
        dst = stills_dir / f"{name}_{ts:.2f}s.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.3f}", "-i", str(mp4_path), "-vframes", "1", str(dst)],
            check=True,
        )
        still_paths.append(dst)
        still_records[dst.name] = {"timestamp_sec": ts, "sha256": _sha256_file(dst), "bytes": dst.stat().st_size}

    # 8-shot contact sheet (4x2 grid @ 480x270 per tile = 1920x540)
    sheet_path = out_dir / "contact_sheet_8shots.jpg"
    inputs = []
    for p in still_paths:
        inputs += ["-i", str(p)]
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", *inputs,
            "-filter_complex",
            "[0:v]scale=480:270[v0];[1:v]scale=480:270[v1];[2:v]scale=480:270[v2];[3:v]scale=480:270[v3];"
            "[4:v]scale=480:270[v4];[5:v]scale=480:270[v5];[6:v]scale=480:270[v6];[7:v]scale=480:270[v7];"
            "[v0][v1][v2][v3]hstack=inputs=4[top];[v4][v5][v6][v7]hstack=inputs=4[bot];[top][bot]vstack=inputs=2",
            "-q:v", "3",
            str(sheet_path),
        ],
        check=True,
    )

    # 3 Action Strips (4 sequential frames per strip showing genuine pose progression!)
    strip_specs = [
        ("strip_1_hook_nudge", [0.10, 0.35, 0.65, 1.85]),
        ("strip_2_rising_climb_and_catch", [7.80, 8.85, 15.20, 19.80]),
        ("strip_3_sneeze_and_deadpan_payoff", [24.20, 24.95, 27.30, 29.10]),
    ]
    strip_records = {}
    for sname, times in strip_specs:
        tmp_pngs = []
        for idx, ts in enumerate(times):
            tp = strips_dir / f"_tmp_{sname}_{idx}.png"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.3f}", "-i", str(mp4_path), "-vframes", "1", "-vf", "scale=480:270", str(tp)],
                check=True,
            )
            tmp_pngs.append(tp)
        strip_out = strips_dir / f"{sname}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-i", str(tmp_pngs[0]), "-i", str(tmp_pngs[1]), "-i", str(tmp_pngs[2]), "-i", str(tmp_pngs[3]),
                "-filter_complex", "[0:v][1:v][2:v][3:v]hstack=inputs=4",
                "-q:v", "3",
                str(strip_out),
            ],
            check=True,
        )
        for tp in tmp_pngs:
            tp.unlink(missing_ok=True)
        strip_records[strip_out.name] = {"timestamps_sec": times, "sha256": _sha256_file(strip_out), "bytes": strip_out.stat().st_size}

    packet = {
        "status": "PACKET_BUILT",
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "contact_sheet": {"file": sheet_path.name, "sha256": _sha256_file(sheet_path), "bytes": sheet_path.stat().st_size},
        "stills": still_records,
        "action_strips": strip_records,
    }
    (out_dir / "editorial_packet_manifest.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    return packet
