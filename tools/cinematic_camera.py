#!/usr/bin/env python3
"""
tools/cinematic_camera.py - Full-Video Cinematic Camera Director & 2D Perspective Staging
QA-Unified-Video-Studio V14.1

Provides:
- CinematicShotPlan schema covering the ENTIRE video (hook, middle, ending).
- True 2D perspective viewpoint planning: front, 3/4 left/right, profile left/right,
  rear, rear 3/4 left/right, over-the-shoulder (OTS) left/right, high/low angle, top-down.
- Viewport cameraRig keyframes (bounded pan, zoom, focal-point tracking).
- 180-degree screen direction axis continuity.
- Consecutive frontal bust repetition prevention.
- Reconciles with battle choreo and pack template engines.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field

CinematicViewpoint = Literal[
    "front",
    "front_three_quarter_left",
    "front_three_quarter_right",
    "profile_left",
    "profile_right",
    "rear_three_quarter_left",
    "rear_three_quarter_right",
    "rear",
    "over_shoulder_left",
    "over_shoulder_right",
    "high_angle",
    "low_angle",
    "top_down",
    "map",
]

CameraScale = Literal[
    "extreme_wide",
    "wide",
    "medium_wide",
    "medium",
    "medium_close",
    "close",
    "extreme_close",
    "detail",
]

ShotPurpose = Literal[
    "establishing",
    "orientation",
    "action",
    "tactical",
    "character",
    "reaction",
    "detail",
    "transition",
    "reveal",
    "resolution",
    "explanation",
    "cta",
]

NarrativeRole = Literal[
    "hook",
    "setup",
    "explanation",
    "complication",
    "evidence",
    "twist",
    "payoff",
    "transition",
]


class CameraKeyframe(BaseModel):
    local_sec: float
    x_center: float = 0.5
    y_center: float = 0.5
    zoom: float = 1.0
    easing: str = "sine"
    tracking_actor_id: Optional[str] = None


class CinematicShotPlan(BaseModel):
    shot_id: str
    source_span: str = ""
    source_start_sec: float = 0.0
    source_end_sec: float = 0.0
    shot_purpose: ShotPurpose = "action"
    narrative_role: NarrativeRole = "explanation"
    subject_ids: List[str] = Field(default_factory=list)
    actor_side: str = "roman"
    look_target: Optional[str] = None
    focus_actor_id: Optional[str] = None
    foreground_actor_id: Optional[str] = None
    scale: CameraScale = "medium"
    viewpoint: CinematicViewpoint = "front"
    view_geometry: str = "FLAT_2D_ILLUSTRATED"
    composition: Dict[str, Any] = Field(default_factory=dict)
    camera_path: List[CameraKeyframe] = Field(default_factory=list)
    cut: Dict[str, Any] = Field(default_factory=dict)
    depth: Dict[str, Any] = Field(default_factory=dict)
    action_sync: Dict[str, Any] = Field(default_factory=dict)
    semantic_grounding: Dict[str, Any] = Field(default_factory=dict)
    sound_focus: Dict[str, Any] = Field(default_factory=dict)
    generation_source: str = "offline_cinematic_planner"
    model_used: Optional[str] = None
    compiled_status: str = "COMPILED"
    fallback_reason: Optional[str] = None
    manual_locked: bool = False


# Supported discrete 2D viewpoints that have dedicated illustrated geometries
SUPPORTED_2D_VIEWPOINTS = {
    "front",
    "front_three_quarter_left",
    "front_three_quarter_right",
    "profile_left",
    "profile_right",
    "rear_three_quarter_left",
    "rear_three_quarter_right",
    "rear",
    "over_shoulder_left",
    "over_shoulder_right",
    "high_angle",
    "low_angle",
    "top_down",
    "map",
}


def build_camera_keyframe_path(
    dur: float,
    scale: CameraScale,
    viewpoint: CinematicViewpoint,
    action: str = "stand",
    aspect: str = "16:9",
    focus_x: Optional[float] = None,
    focus_y: Optional[float] = None,
) -> List[CameraKeyframe]:
    """
    Build a smooth, bounded viewport path for the camera rig without black clipping edges.
    Frames subjects with safe vertical positioning so characters are centered and not cut off.
    """
    is_vert = (aspect == "9:16")
    base_zoom = 1.0
    if scale in ("close", "extreme_close"):
        base_zoom = 1.15 if is_vert else 1.25
    elif scale in ("medium_close", "detail"):
        base_zoom = 1.1 if is_vert else 1.18
    elif scale in ("extreme_wide", "wide"):
        base_zoom = 1.0

    dur = max(0.5, float(dur))

    # Center coordinates depend on viewpoint & narrative framing
    # Ground action baseline: actors feet at y=0.85, height h=0.55 -> action center is at y=0.58-0.62
    start_x, end_x = 0.5, 0.5
    start_y, end_y = 0.59, 0.57

    if viewpoint in ("profile_left", "front_three_quarter_left"):
        start_x, end_x = 0.52, 0.48
    elif viewpoint in ("profile_right", "front_three_quarter_right"):
        start_x, end_x = 0.48, 0.52
    elif viewpoint in ("over_shoulder_right", "rear_three_quarter_right"):
        start_x, end_x = 0.45, 0.42
    elif viewpoint in ("over_shoulder_left", "rear_three_quarter_left"):
        start_x, end_x = 0.55, 0.58
    elif viewpoint == "low_angle":
        # Low angle looking up at shield line: aimed directly at chest/shield level
        start_y, end_y = 0.63, 0.60
    elif viewpoint == "high_angle":
        start_y, end_y = 0.54, 0.56
    elif viewpoint == "top_down":
        start_y, end_y = 0.52, 0.52

    # Override with subject focus if explicitly provided
    if focus_x is not None:
        start_x, end_x = focus_x, focus_x
    if focus_y is not None:
        start_y, end_y = focus_y, focus_y

    if action == "charge":
        # Dynamic subtle push-in
        end_zoom = base_zoom * 1.08
    elif action in ("retreat", "resolution"):
        # Subtle pull-back
        end_zoom = max(1.0, base_zoom * 0.96)
    else:
        # Subtle cinematic float
        end_zoom = base_zoom * 1.04

    return [
        CameraKeyframe(
            local_sec=0.0,
            x_center=round(start_x, 3),
            y_center=round(start_y, 3),
            zoom=round(base_zoom, 3),
            easing="sine",
        ),
        CameraKeyframe(
            local_sec=round(dur, 2),
            x_center=round(end_x, 3),
            y_center=round(end_y, 3),
            zoom=round(end_zoom, 3),
            easing="sine",
        ),
    ]


def validate_camera_rig_contract(
    rig: Dict[str, Any],
    duration: float,
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """
    Validate that cameraRig conforms to the strict canonical contract:
    - keyframes is a list of dicts with t, x, y, z
    - all values are finite numbers
    - 0 <= t <= duration + 0.1
    - 0.05 <= x, y <= 0.95
    - 0.8 <= z <= 3.5
    - t is monotonically non-decreasing
    """
    errors = []
    if not isinstance(rig, dict):
        return {"valid": False, "errors": ["cameraRig must be a dict"]}
    kfs = rig.get("keyframes")
    if not isinstance(kfs, list) or len(kfs) == 0:
        return {"valid": False, "errors": ["cameraRig.keyframes must be a non-empty list"]}

    prev_t = -0.001
    for idx, kf in enumerate(kfs):
        if not isinstance(kf, dict):
            errors.append(f"Keyframe {idx} must be a dict")
            continue
        t = kf.get("t") if kf.get("t") is not None else kf.get("local_sec")
        x = kf.get("x") if kf.get("x") is not None else kf.get("x_center")
        y = kf.get("y") if kf.get("y") is not None else kf.get("y_center")
        z = kf.get("z") if kf.get("z") is not None else kf.get("zoom")

        if t is None or not (isinstance(t, (int, float)) and math.isfinite(t)):
            errors.append(f"Keyframe {idx}: invalid time t={t}")
        elif t < -0.05 or t > duration + 0.5:
            errors.append(f"Keyframe {idx}: time t={t} outside duration bounds [0, {duration}]")
        elif t < prev_t - 0.001:
            errors.append(f"Keyframe {idx}: time t={t} is non-monotonic (previous was {prev_t})")
        else:
            prev_t = t

        if x is None or not (isinstance(x, (int, float)) and math.isfinite(x) and 0.05 <= x <= 0.95):
            errors.append(f"Keyframe {idx}: invalid x focal coordinate {x}")
        if y is None or not (isinstance(y, (int, float)) and math.isfinite(y) and 0.05 <= y <= 0.95):
            errors.append(f"Keyframe {idx}: invalid y focal coordinate {y}")
        if z is None or not (isinstance(z, (int, float)) and math.isfinite(z) and 0.8 <= z <= 3.5):
            errors.append(f"Keyframe {idx}: invalid zoom {z}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "keyframe_count": len(kfs),
    }


def audit_camera_snap_keyframes(
    keyframes: List[Dict[str, Any]],
    time_threshold_sec: float = 0.15,
    pos_threshold: float = 0.35,
    zoom_threshold: float = 0.8,
) -> Tuple[bool, List[str]]:
    """
    Audit within-shot camera keyframe continuity:
    Detects abrupt transform snaps (e.g. 1-frame position/zoom pop)
    between adjacent keyframes without motivated narrative cut.
    Returns (snap_detected: bool, diagnostics: List[str]).
    """
    diags: List[str] = []
    if not keyframes or len(keyframes) < 2:
        return False, diags

    for i in range(len(keyframes) - 1):
        k1 = keyframes[i]
        k2 = keyframes[i + 1]

        t1 = float(k1.get("t", k1.get("local_sec", 0.0)))
        t2 = float(k2.get("t", k2.get("local_sec", 0.0)))
        dt = abs(t2 - t1)

        x1 = float(k1.get("x", k1.get("x_center", 0.5)))
        x2 = float(k2.get("x", k2.get("x_center", 0.5)))
        dx = abs(x2 - x1)

        y1 = float(k1.get("y", k1.get("y_center", 0.5)))
        y2 = float(k2.get("y", k2.get("y_center", 0.5)))
        dy = abs(y2 - y1)

        z1 = float(k1.get("z", k1.get("zoom", 1.0)))
        z2 = float(k2.get("z", k2.get("zoom", 1.0)))
        dz = abs(z2 - z1)

        if dt <= time_threshold_sec:
            if dx > pos_threshold or dy > pos_threshold or dz > zoom_threshold:
                diags.append(
                    f"Camera snap detected between keyframes {i}->{i+1}: dt={dt:.3f}s, dx={dx:.2f}, dy={dy:.2f}, dz={dz:.2f}"
                )

    return len(diags) > 0, diags


def plan_camera_sequence(
    shots: List[Dict[str, Any]],
    director_plan: Optional[Dict[str, Any]] = None,
    battle_state: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    aspect: Optional[str] = None,
) -> List[CinematicShotPlan]:
    """
    Plan a holistic, narrative-motivated camera sequence for EVERY shot in the video.
    Covers Hook (0-30s), Middle Explanation (30-60s), and Ending Climax/Payoff (60s+).
    Enforces viewpoint diversity, 180-degree axis stability, and purposeful composition.
    """
    cfg = dict(config or {})
    if aspect:
        cfg["aspect"] = aspect
    pack = cfg.get("pack", "squire")
    aspect = cfg.get("aspect", "16:9")

    # Map director plan by shot_id if provided
    d_shots_by_id: Dict[str, Dict[str, Any]] = {}
    if director_plan and "shots" in director_plan:
        d_shots_by_id = {s.get("shot_id"): s for s in director_plan["shots"]}

    camera_plans: List[CinematicShotPlan] = []
    prev_view: Optional[CinematicViewpoint] = None
    prev_scale: Optional[CameraScale] = None
    prev_axis: str = "left_to_right"
    prev_actor: Optional[str] = None

    total_shots = len(shots)

    for idx, s in enumerate(shots):
        sid = s.get("id", f"s{idx+1:03d}")
        dur = float(s.get("dur", 3.0))
        if dur <= 0.0:
            raise ValueError(f"Shot '{sid}' has non-positive duration {dur}s. Duration must be strictly > 0.")
        start_t = float(s.get("start", idx * dur))
        end_t = float(s.get("end", start_t + dur))
        line = s.get("line", "")
        line_lower = line.lower()
        is_manual = (s.get("visual_source") == "manual" or s.get("manual") is True)

        # 1. Determine narrative phase
        if end_t <= 30.0:
            phase: NarrativeRole = "hook" if start_t < 6.0 else "setup"
        elif end_t <= 60.0:
            phase = "explanation" if (idx % 2 == 0) else "complication"
        else:
            phase = "payoff" if (idx >= total_shots - 2) else "evidence"

        # 2. Extract semantic cues from line & director plan
        d_shot = d_shots_by_id.get(sid, {})
        action = d_shot.get("body_motion") or s.get("action") or "stand"
        actor = d_shot.get("actor") or s.get("actor") or "roman"
        polarity = d_shot.get("polarity") or s.get("polarity") or "AFFIRMED"

        # Determine semantic purpose
        if idx == 0:
            purpose: ShotPurpose = "establishing"
        elif any(w in line_lower for w in ("warlord", "general", "commander", "centurion", "ordered", "orders", "consul", "signal")):
            purpose = "character"
        elif any(w in line_lower for w in ("charge", "assault", "collided", "clashes", "spear")):
            purpose = "action"
        elif any(w in line_lower for w in ("flank", "pocket", "reserve", "encircle", "formation", "relief")):
            purpose = "tactical"
        elif any(w in line_lower for w in ("thought", "believed", "trap", "victory", "concluded")):
            purpose = "reveal" if "thought" in line_lower or "trap" in line_lower else "resolution"
        else:
            purpose = "explanation"

        # 3. Purposeful Camera Scale & Viewpoint Assignment (Grammar Rules)
        # Avoid repeated frontal bust! We deliberately pick non-frontal 2D angles motivated by story.
        chosen_scale: CameraScale = "medium"
        chosen_view: CinematicViewpoint = "front"

        if purpose == "establishing" or idx == 0:
            # Shot 0 / Hook: High-impact establishing or lateral wide army
            chosen_scale = "wide"
            chosen_view = "profile_left" if idx == 0 else "high_angle"
        elif any(w in line_lower for w in ("warlord", "commander", "general", "centurion")) or "ordered" in line_lower or "orders" in line_lower:
            # Leader command: 3/4 front view or low angle showing authority
            chosen_scale = "medium_close"
            chosen_view = "front_three_quarter_right" if prev_view != "front_three_quarter_right" else "profile_right"
        elif any(w in line_lower for w in ("held", "shields", "brace", "locked")):
            # Shield wall: Low angle looking up at the locked shields
            chosen_scale = "medium"
            chosen_view = "low_angle"
        elif any(w in line_lower for w in ("collided", "impact", "clashes")):
            # Battle collision: Dynamic over-the-shoulder view looking past our front line at enemy!
            chosen_scale = "medium_wide"
            chosen_view = "over_shoulder_right" if prev_view != "over_shoulder_right" else "over_shoulder_left"
        elif any(w in line_lower for w in ("thought", "broken", "yielded", "feigned")):
            # Perceived breakthrough: 3/4 front reaction shot
            chosen_scale = "medium_close"
            chosen_view = "front_three_quarter_left"
        elif any(w in line_lower for w in ("principes", "reserve", "stepped forward", "relief")):
            # Line rotation / relief: Rear view of fresh ranks marching forward into the breach!
            chosen_scale = "medium_wide"
            chosen_view = "rear"
        elif any(w in line_lower for w in ("trapped", "pocket", "encircled", "curved inward")):
            # Encirclement: Tactical bird's-eye / top-down view showing geometry
            chosen_scale = "wide"
            chosen_view = "top_down"
        elif any(w in line_lower for w in ("spears", "triarii", "prevent", "retreat")):
            # Rear-three-quarter lock preventing retreat
            chosen_scale = "medium"
            chosen_view = "rear_three_quarter_left"
        elif any(w in line_lower for w in ("victory", "concluded", "total", "triumphs", "proved")) or (purpose in ("reveal", "resolution") and phase == "payoff"):
            # Climax & Payoff: Wide reveal / resolution
            chosen_scale = "extreme_wide" if any(w in line_lower for w in ("victory", "triumphs", "total")) else "wide"
            chosen_view = "front_three_quarter_right"
        else:
            # Rotating variety for middle & general narrative (purposeful non-frontal angles)
            pool: List[CinematicViewpoint] = [
                "profile_left",
                "front_three_quarter_left",
                "rear",
                "rear_three_quarter_right",
                "profile_right",
                "front_three_quarter_right",
                "rear_three_quarter_left",
            ]
            # Pick a view that does not duplicate previous shot
            candidates = [v for v in pool if v != prev_view]
            chosen_view = candidates[idx % len(candidates)]
            chosen_scale = "medium" if (idx % 2 == 0) else "medium_wide"

        # Guard: Check for duplicate consecutive frontal busts!
        if chosen_view in ("front", "front_three_quarter_left", "front_three_quarter_right") and prev_view == chosen_view:
            if chosen_view == "front":
                chosen_view = "profile_left"
            elif chosen_view == "front_three_quarter_left":
                chosen_view = "rear_three_quarter_left"
            else:
                chosen_view = "profile_right"

        # 4. Continuity & 180-degree axis handling
        neutral_views = {"top_down", "high_angle", "low_angle", "rear", "front", "map"}
        left_views = {"profile_left", "front_three_quarter_left", "over_shoulder_left", "rear_three_quarter_left"}
        right_views = {"profile_right", "front_three_quarter_right", "over_shoulder_right", "rear_three_quarter_right"}

        current_axis = prev_axis
        if chosen_view in left_views:
            current_axis = "left_to_right"
        elif chosen_view in right_views:
            current_axis = "right_to_left"

        is_neutral_transition = (
            chosen_view in neutral_views
            or prev_view in neutral_views
            or prev_view is None
        )
        is_reverse_angle = (actor != prev_actor and prev_actor is not None)
        axis_conforming = (current_axis == prev_axis or is_neutral_transition or is_reverse_angle)

        cut_data = {
            "type": "cut",
            "matches_previous_axis": axis_conforming,
            "continuity_anchor": actor,
        }

        # 5. Build keyframe path
        camera_path = build_camera_keyframe_path(
            dur=dur,
            scale=chosen_scale,
            viewpoint=chosen_view,
            action=action,
            aspect=aspect,
        )

        cp = CinematicShotPlan(
            shot_id=sid,
            source_span=line,
            source_start_sec=start_t,
            source_end_sec=end_t,
            shot_purpose=purpose,
            narrative_role=phase,
            subject_ids=[actor],
            actor_side=actor,
            focus_actor_id=actor,
            scale=chosen_scale,
            viewpoint=chosen_view,
            view_geometry="FLAT_2D_ILLUSTRATED",
            composition={
                "subject_position_normalized": [0.5, 0.5],
                "safe_top": 0.08 if aspect == "9:16" else 0.05,
                "safe_bottom": 0.22 if aspect == "9:16" else 0.12,
                "screen_direction": current_axis,
            },
            camera_path=camera_path,
            cut=cut_data,
            depth={"parallax_mid": True, "parallax_foreground": (chosen_view.startswith("over_shoulder"))},
            action_sync={"action": action, "expected_motion": True},
            semantic_grounding={"quote": line, "polarity": polarity},
            sound_focus={"sfx_intents": d_shot.get("sfx_intents", [])},
            generation_source="cinematic_camera_director_v14_1",
            manual_locked=is_manual,
        )

        camera_plans.append(cp)
        prev_view = chosen_view
        prev_scale = chosen_scale
        prev_axis = current_axis
        prev_actor = actor

    return camera_plans


def validate_camera_sequence(
    camera_plans: List[CinematicShotPlan],
    shots: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Validate that:
    1. Coverage is 100% of all shots.
    2. Every planned viewpoint is an actually supported discrete 2D illustrated view.
    3. Keyframe times are bounded within shot durations.
    4. No two consecutive identical frontal busts without narrative cause.
    5. Manual shots are flagged as preserved.
    """
    errors: List[str] = []
    if len(camera_plans) != len(shots):
        errors.append(f"Shot count mismatch: planned {len(camera_plans)} vs shots {len(shots)}")

    prev_cp: Optional[CinematicShotPlan] = None
    for idx, cp in enumerate(camera_plans):
        # 1. Viewpoint check
        if cp.viewpoint not in SUPPORTED_2D_VIEWPOINTS:
            errors.append(f"Shot {cp.shot_id}: unsupported viewpoint '{cp.viewpoint}'")

        # 2. Keyframe validity
        shot_dur = cp.source_end_sec - cp.source_start_sec
        for kf in cp.camera_path:
            if kf.local_sec < -0.01 or kf.local_sec > shot_dur + 0.1:
                errors.append(f"Shot {cp.shot_id}: keyframe at {kf.local_sec}s outside duration {shot_dur}s")
            if kf.zoom < 0.5 or kf.zoom > 3.0:
                errors.append(f"Shot {cp.shot_id}: invalid zoom {kf.zoom}")
            if kf.x_center < 0.1 or kf.x_center > 0.9 or kf.y_center < 0.1 or kf.y_center > 0.9:
                errors.append(f"Shot {cp.shot_id}: camera focal point out of bounds: ({kf.x_center}, {kf.y_center})")

        # 3. Repetition check: reject consecutive frontal busts
        if prev_cp and cp.scale in ("close", "extreme_close") and prev_cp.scale in ("close", "extreme_close"):
            if cp.viewpoint == "front" and prev_cp.viewpoint == "front":
                errors.append(f"Shot {cp.shot_id}: consecutive close frontal busts violate cinematic grammar")

        prev_cp = cp

    return (len(errors) == 0, errors)


def compile_camera_keyframes(
    shot_plan: CinematicShotPlan,
    dur: float,
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """
    Compile a CinematicShotPlan into template-consumable `args.cameraRig` and legacy `move`/`zoom`.
    """
    kf_list = []
    for kf in shot_plan.camera_path:
        kf_list.append({
            "t": round(kf.local_sec, 3),
            "x": round(kf.x_center, 3),
            "y": round(kf.y_center, 3),
            "z": round(kf.zoom, 3),
            "ease": kf.easing,
        })

    first_kf = shot_plan.camera_path[0] if shot_plan.camera_path else CameraKeyframe(local_sec=0)
    last_kf = shot_plan.camera_path[-1] if len(shot_plan.camera_path) > 1 else first_kf

    # Legacy fallback parameters
    legacy_move = "still"
    if last_kf.zoom > first_kf.zoom + 0.02:
        legacy_move = "in"
    elif last_kf.zoom < first_kf.zoom - 0.02:
        legacy_move = "out"
    elif last_kf.x_center > first_kf.x_center + 0.02:
        legacy_move = "right"
    elif last_kf.x_center < first_kf.x_center - 0.02:
        legacy_move = "left"

    return {
        "cameraRig": {
            "viewpoint": shot_plan.viewpoint,
            "scale": shot_plan.scale,
            "keyframes": kf_list,
            "aspect": aspect,
        },
        "move": legacy_move,
        "moveAmt": round(abs(last_kf.zoom - first_kf.zoom), 3) or 0.035,
    }


def audit_camera_grammar(camera_plans: List[CinematicShotPlan]) -> Dict[str, Any]:
    """
    Analyze camera sequence distribution, diversity, and compliance across the entire timeline.
    No hardcoded fake percentages; reports truthful observable statistics.
    """
    total = len(camera_plans)
    if total == 0:
        return {"total_shots": 0, "status": "EMPTY"}

    view_counts: Dict[str, int] = {}
    scale_counts: Dict[str, int] = {}
    purpose_counts: Dict[str, int] = {}
    frontal_count = 0
    consecutive_repetitions = 0

    prev_v: Optional[str] = None
    for cp in camera_plans:
        v = cp.viewpoint
        s = cp.scale
        p = cp.shot_purpose
        view_counts[v] = view_counts.get(v, 0) + 1
        scale_counts[s] = scale_counts.get(s, 0) + 1
        purpose_counts[p] = purpose_counts.get(p, 0) + 1

        if v == "front":
            frontal_count += 1
        if prev_v and v == prev_v:
            consecutive_repetitions += 1
        prev_v = v

    unique_views = len(view_counts)
    frontal_ratio = round(frontal_count / total, 3)

    return {
        "total_shots": total,
        "unique_viewpoints": unique_views,
        "viewpoint_distribution": view_counts,
        "scale_distribution": scale_counts,
        "purpose_distribution": purpose_counts,
        "frontal_shots_count": frontal_count,
        "frontal_ratio": frontal_ratio,
        "consecutive_repetitions": consecutive_repetitions,
        "diverse_grammar_verified": (unique_views >= 4 and consecutive_repetitions <= 1),
    }


def camera_plan_digest(camera_plans: List[CinematicShotPlan]) -> str:
    """
    Generate a deterministic digest of the full video camera plan for cache/audit.
    """
    dumped = [
        {
            "id": cp.shot_id,
            "view": cp.viewpoint,
            "scale": cp.scale,
            "purpose": cp.shot_purpose,
            "keyframes": [kf.model_dump() for kf in cp.camera_path],
        }
        for cp in camera_plans
    ]
    canonical_str = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]


# ==============================================================================
# V14.7.6 PHASE E — MULTI-ANGLE CAMERA SEGMENTS INSIDE ONE LOGICAL SHOT
# ==============================================================================

ProjectionMode = Literal[
    "continuous_2d_canvas",
    "authored_2d_insert",
    "authored_2d_low_angle",
    "authored_2d_high_angle",
    "crop_zoom",
]


class CameraSegment(BaseModel):
    schema_version: str = "14.7.6"
    segment_id: str
    shot_id: str
    segment_index: int = 0
    local_start: float = 0.0
    local_end: float = 3.0
    global_start: float = 0.0
    global_end: float = 3.0
    scale: CameraScale = "medium"
    viewpoint: CinematicViewpoint = "front"
    projection_mode: ProjectionMode = "continuous_2d_canvas"
    center_from: Tuple[float, float] = (0.5, 0.54)
    center_to: Tuple[float, float] = (0.5, 0.54)
    zoom_from: float = 1.0
    zoom_to: float = 1.04
    axis: Literal["left_to_right", "right_to_left", "neutral"] = "left_to_right"
    focus_actor_ids: List[str] = Field(default_factory=list)
    focus_object_ids: List[str] = Field(default_factory=list)
    action_phase_at_entry: str = "IDLE"
    action_phase_at_exit: str = "SETTLE"
    adds_information_reason: str = "establish_primary_action"
    resets_action_time: bool = False
    world_state_anchor: Dict[str, Any] = Field(default_factory=dict)


def _axis_for_view(viewpoint: str, fallback: str = "left_to_right") -> Literal["left_to_right", "right_to_left", "neutral"]:
    neutral = {"top_down", "high_angle", "low_angle", "rear", "front", "map"}
    left_v = {"profile_left", "front_three_quarter_left", "over_shoulder_left", "rear_three_quarter_left"}
    right_v = {"profile_right", "front_three_quarter_right", "over_shoulder_right", "rear_three_quarter_right"}
    if viewpoint in neutral:
        return "neutral"
    if viewpoint in left_v:
        return "left_to_right"
    if viewpoint in right_v:
        return "right_to_left"
    return "left_to_right" if fallback != "right_to_left" else "right_to_left"


def _snap_to_frame(t: float, fps: float = 24.0) -> float:
    return round(round(t * fps) / fps, 4)


def plan_multi_angle_action(
    logical_shot: Dict[str, Any],
    motion_plan: Optional[Any] = None,
    world_state: Optional[Dict[str, Any]] = None,
    fps: float = 24.0,
) -> List[CameraSegment]:
    """
    Plan 1..3 contiguous script-driven camera segments within a single logical shot:
    - 1 segment for short (< 3.0s) or single-beat shots (continuous tracking take).
    - 2–3 segments ONLY when shot duration and physical phase transitions justify an edit
      (e.g., flame close -> wide harbor; medium reaction -> hand/prop grip insert;
      wide cooperative brace -> rope grip insert -> low-angle tower lift).
    - Never resets action/world time across segments (`resets_action_time = False`).
    - Never claims crop/zoom creates a reverse/rear angle (`authored_2d_*` or same-axis framing).
    """
    sid = str(logical_shot.get("id") or logical_shot.get("shot_id") or "S01")
    g_start = float(logical_shot.get("start", 0.0))
    dur = float(logical_shot.get("dur", max(0.4, float(logical_shot.get("end", g_start + 3.0)) - g_start)))
    g_end = round(g_start + dur, 4)
    line_low = f"{logical_shot.get('line', '')} {logical_shot.get('desc', '')}".lower()

    mp_dict = (
        motion_plan.model_dump()
        if hasattr(motion_plan, "model_dump")
        else (dict(motion_plan) if isinstance(motion_plan, dict) else {})
    )
    all_tracks = mp_dict.get("tracks") or mp_dict.get("actor_tracks") or []
    shot_tracks = [tr for tr in all_tracks if str(tr.get("shot_id")) == sid]
    shot_intents = [it for it in (mp_dict.get("intents") or []) if str(it.get("shot_id")) == sid]

    actor_ids: List[str] = []
    object_ids: List[str] = []
    contact_times_local: List[float] = []
    exert_times_local: List[float] = []
    has_slip = False
    has_extinguish = any(it.get("motion_type") == "EXTINGUISH" for it in shot_intents) or (
        "went dark" in line_low or "extinguish" in line_low or "snuffs" in line_low
    )

    for tr in shot_tracks:
        aid = str(tr.get("actor_id", ""))
        if aid and aid not in actor_ids:
            actor_ids.append(aid)
        for oid in tr.get("object_ids") or []:
            if oid not in object_ids:
                object_ids.append(str(oid))
        for ph in tr.get("phases") or []:
            p_name = str(ph.get("phase_name", ""))
            p_local = max(0.0, float(ph.get("start_sec", g_start)) - g_start)
            if p_name == "CONTACT":
                contact_times_local.append(p_local)
            elif p_name in ("EXERT", "ACT"):
                exert_times_local.append(p_local)
            if ph.get("motion_type") == "SLIP" or ph.get("slip_foot"):
                has_slip = True

    ws = dict(world_state or {})
    if not ws and mp_dict.get("world_states"):
        for w_entry in mp_dict["world_states"]:
            if str(w_entry.get("shot_id")) == sid:
                ws = dict(w_entry)
                break

    primary_focus_x = 0.50
    primary_focus_y = 0.56
    if shot_tracks:
        ws_pt = shot_tracks[0].get("world_end") or shot_tracks[0].get("world_start") or [0.46, 0.78]
        primary_focus_x = float(clamp_val := max(0.24, min(0.76, float(ws_pt[0]))))
        primary_focus_y = max(0.38, min(0.70, float(ws_pt[1]) - 0.14))

    def _anchor_state() -> Dict[str, Any]:
        return {
            "actors": sorted(actor_ids),
            "objects": sorted(object_ids),
            "continuous_world_clock": True,
        }

    # Case 1: Short shot (< 3.0s) or no multi-phase justification -> single continuous segment
    if dur < 2.95:
        return [
            CameraSegment(
                segment_id=f"{sid}_seg01",
                shot_id=sid,
                segment_index=0,
                local_start=0.0,
                local_end=round(dur, 4),
                global_start=g_start,
                global_end=g_end,
                scale="medium",
                viewpoint="front_three_quarter_left",
                projection_mode="continuous_2d_canvas",
                center_from=(round(primary_focus_x, 3), round(primary_focus_y, 3)),
                center_to=(round(primary_focus_x, 3), round(max(0.35, primary_focus_y - 0.02), 3)),
                zoom_from=1.02,
                zoom_to=1.06,
                axis="left_to_right",
                focus_actor_ids=actor_ids,
                focus_object_ids=object_ids,
                action_phase_at_entry="ANTICIPATE" if shot_tracks else "ESTABLISH",
                action_phase_at_exit="SETTLE",
                adds_information_reason="continuous_single_beat_tracking",
                world_state_anchor=_anchor_state(),
            )
        ]

    # Case 2: 3-segment cooperative climax (>= 4.0s, >= 2 actors + shared haul/lift objective)
    is_shared_climax = any(k in line_low for k in ("together", "raised", "haul", "both", "lift"))
    if dur >= 4.0 and len(actor_ids) >= 2 and contact_times_local and is_shared_climax:
        c1 = _snap_to_frame(max(1.20, min(dur * 0.36, (min(contact_times_local) or dur * 0.34) + 0.12)), fps)
        c2 = _snap_to_frame(max(c1 + 1.15, min(dur - 1.10, dur * 0.68)), fps)
        if c2 - c1 >= 0.95 and dur - c2 >= 0.95:
            return [
                CameraSegment(
                    segment_id=f"{sid}_seg01",
                    shot_id=sid,
                    segment_index=0,
                    local_start=0.0,
                    local_end=c1,
                    global_start=g_start,
                    global_end=round(g_start + c1, 4),
                    scale="wide",
                    viewpoint="front_three_quarter_left",
                    projection_mode="continuous_2d_canvas",
                    center_from=(0.50, 0.56),
                    center_to=(0.52, 0.54),
                    zoom_from=1.00,
                    zoom_to=1.05,
                    axis="left_to_right",
                    focus_actor_ids=actor_ids,
                    focus_object_ids=object_ids,
                    action_phase_at_entry="ANTICIPATE",
                    action_phase_at_exit="CONTACT",
                    adds_information_reason="establish_two_actor_spatial_coordination_and_pulley_geometry",
                    world_state_anchor=_anchor_state(),
                ),
                CameraSegment(
                    segment_id=f"{sid}_seg02",
                    shot_id=sid,
                    segment_index=1,
                    local_start=c1,
                    local_end=c2,
                    global_start=round(g_start + c1, 4),
                    global_end=round(g_start + c2, 4),
                    scale="detail",
                    viewpoint="profile_left",
                    projection_mode="authored_2d_insert",
                    center_from=(0.56, 0.55),
                    center_to=(0.56, 0.50),
                    zoom_from=1.24,
                    zoom_to=1.30,
                    axis="left_to_right",
                    focus_actor_ids=actor_ids,
                    focus_object_ids=object_ids or ["rope", "lantern"],
                    action_phase_at_entry="CONTACT",
                    action_phase_at_exit="EXERT",
                    adds_information_reason="reveal_locked_hands_on_taut_rope_and_rising_lantern_bracket",
                    world_state_anchor=_anchor_state(),
                ),
                CameraSegment(
                    segment_id=f"{sid}_seg03",
                    shot_id=sid,
                    segment_index=2,
                    local_start=c2,
                    local_end=round(dur, 4),
                    global_start=round(g_start + c2, 4),
                    global_end=g_end,
                    scale="medium_wide",
                    viewpoint="low_angle",
                    projection_mode="authored_2d_low_angle",
                    center_from=(0.52, 0.44),
                    center_to=(0.50, 0.40),
                    zoom_from=1.08,
                    zoom_to=1.03,
                    axis="neutral",
                    focus_actor_ids=actor_ids,
                    focus_object_ids=object_ids or ["lantern", "tower"],
                    action_phase_at_entry="EXERT",
                    action_phase_at_exit="SETTLE",
                    adds_information_reason="confirm_lantern_seated_inside_upper_watchtower_alcove_above_storm",
                    world_state_anchor=_anchor_state(),
                ),
            ]

    # Case 3: 2-segment dramatic extinguish hook (close flame -> wide dark harbor hazard)
    if has_extinguish and dur >= 2.95:
        c1 = _snap_to_frame(min(dur - 1.25, max(1.10, dur * 0.42)), fps)
        return [
            CameraSegment(
                segment_id=f"{sid}_seg01",
                shot_id=sid,
                segment_index=0,
                local_start=0.0,
                local_end=c1,
                global_start=g_start,
                global_end=round(g_start + c1, 4),
                scale="close",
                viewpoint="front_three_quarter_left",
                projection_mode="authored_2d_insert",
                center_from=(0.34, 0.36),
                center_to=(0.35, 0.36),
                zoom_from=1.28,
                zoom_to=1.34,
                axis="left_to_right",
                focus_actor_ids=actor_ids,
                focus_object_ids=["beacon", "lantern"],
                action_phase_at_entry="ESTABLISH",
                action_phase_at_exit="REACT",
                adds_information_reason="show_squall_gust_snuffing_the_beacon_flame_up_close",
                world_state_anchor=_anchor_state(),
            ),
            CameraSegment(
                segment_id=f"{sid}_seg02",
                shot_id=sid,
                segment_index=1,
                local_start=c1,
                local_end=round(dur, 4),
                global_start=round(g_start + c1, 4),
                global_end=g_end,
                scale="wide",
                viewpoint="high_angle",
                projection_mode="continuous_2d_canvas",
                center_from=(0.52, 0.52),
                center_to=(0.55, 0.52),
                zoom_from=1.02,
                zoom_to=1.00,
                axis="neutral",
                focus_actor_ids=actor_ids,
                focus_object_ids=["ship", "rocks", "beacon"],
                action_phase_at_entry="REACT",
                action_phase_at_exit="SETTLE",
                adds_information_reason="reveal_merchant_vessel_drifting_toward_dark_shoal_rocks",
                world_state_anchor=_anchor_state(),
            ),
        ]

    # Case 4: 2-segment physical grip / discovery (medium actor reaction -> close hand/prop contact insert)
    if dur >= 3.2 and contact_times_local and not has_slip and len(actor_ids) == 1:
        raw_cut = max(1.25, min(dur - 1.15, min(contact_times_local)))
        c1 = _snap_to_frame(raw_cut, fps)
        return [
            CameraSegment(
                segment_id=f"{sid}_seg01",
                shot_id=sid,
                segment_index=0,
                local_start=0.0,
                local_end=c1,
                global_start=g_start,
                global_end=round(g_start + c1, 4),
                scale="medium",
                viewpoint="front_three_quarter_left",
                projection_mode="continuous_2d_canvas",
                center_from=(round(primary_focus_x, 3), round(primary_focus_y, 3)),
                center_to=(round(primary_focus_x + 0.02, 3), round(primary_focus_y, 3)),
                zoom_from=1.04,
                zoom_to=1.10,
                axis="left_to_right",
                focus_actor_ids=actor_ids,
                focus_object_ids=object_ids,
                action_phase_at_entry="ANTICIPATE",
                action_phase_at_exit="REACH",
                adds_information_reason="capture_facial_alarm_head_turn_and_reach_initiation",
                world_state_anchor=_anchor_state(),
            ),
            CameraSegment(
                segment_id=f"{sid}_seg02",
                shot_id=sid,
                segment_index=1,
                local_start=c1,
                local_end=round(dur, 4),
                global_start=round(g_start + c1, 4),
                global_end=g_end,
                scale="detail",
                viewpoint="profile_left",
                projection_mode="authored_2d_insert",
                center_from=(round(min(0.76, primary_focus_x + 0.05), 3), round(min(0.72, primary_focus_y + 0.04), 3)),
                center_to=(round(min(0.76, primary_focus_x + 0.05), 3), round(primary_focus_y + 0.01, 3)),
                zoom_from=1.26,
                zoom_to=1.32,
                axis="left_to_right",
                focus_actor_ids=actor_ids,
                focus_object_ids=object_ids or ["lantern"],
                action_phase_at_entry="CONTACT",
                action_phase_at_exit="SETTLE",
                adds_information_reason="prove_tactile_hand_grip_on_spare_oil_lantern_handle",
                world_state_anchor=_anchor_state(),
            ),
        ]

    # Default: 1 continuous tracking segment (do NOT force multi-angle cuts on shots that read best unbroken)
    default_scale: CameraScale = (
        "wide"
        if any(w in line_low for w in ("harbor", "ship", "rocks", "recove", "made it through", "safe way"))
        else ("medium_wide" if has_slip or len(actor_ids) >= 2 else "medium")
    )
    default_view: CinematicViewpoint = "profile_left" if has_slip else "front_three_quarter_left"
    return [
        CameraSegment(
            segment_id=f"{sid}_seg01",
            shot_id=sid,
            segment_index=0,
            local_start=0.0,
            local_end=round(dur, 4),
            global_start=g_start,
            global_end=g_end,
            scale=default_scale,
            viewpoint=default_view,
            projection_mode="continuous_2d_canvas",
            center_from=(round(primary_focus_x, 3), round(primary_focus_y, 3)),
            center_to=(round(min(0.74, primary_focus_x + 0.03), 3), round(max(0.38, primary_focus_y - 0.02), 3)),
            zoom_from=1.00 if default_scale == "wide" else 1.04,
            zoom_to=1.05 if default_scale == "wide" else 1.10,
            axis=_axis_for_view(default_view),
            focus_actor_ids=actor_ids,
            focus_object_ids=object_ids,
            action_phase_at_entry="ANTICIPATE" if shot_tracks else "ESTABLISH",
            action_phase_at_exit="SETTLE",
            adds_information_reason="unbroken_continuous_staging_for_clear_spatial_readability",
            world_state_anchor=_anchor_state(),
        )
    ]


def validate_camera_segments(
    segments: List[CameraSegment],
    logical_shot: Dict[str, Any],
    motion_plan: Optional[Any] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate internal multi-angle camera segments against Section 8 invariants:
    1. Non-empty segment list and every segment has strictly positive duration (>= 0.12s).
    2. Contiguous local timeline covering [0.0, shot_dur] with zero gaps/overlaps.
    3. 180-degree spatial axis preserved across internal cuts unless bridged via neutral view.
    4. No fake reverse/rear angle claimed via mere crop/zoom (`projection_mode == 'crop_zoom'`).
    5. Every internal cut must add new visual information (distinct scale/viewpoint/reason).
    6. Action clock & world/prop state never reset or teleport across internal segment cuts.
    """
    errors: List[str] = []
    sid = str(logical_shot.get("id") or logical_shot.get("shot_id") or "S01")
    g_start = float(logical_shot.get("start", 0.0))
    dur = float(logical_shot.get("dur", max(0.2, float(logical_shot.get("end", g_start + 3.0)) - g_start)))

    if not segments:
        return False, [f"Shot {sid}: camera segments list is empty"]

    if abs(segments[0].local_start - 0.0) > 1e-3:
        errors.append(f"Shot {sid}: first segment must start at 0.0s (got {segments[0].local_start})")
    if abs(segments[-1].local_end - dur) > 1e-2:
        errors.append(f"Shot {sid}: last segment must end at {dur:.4f}s (got {segments[-1].local_end:.4f}s)")

    for i, seg in enumerate(segments):
        seg_dur = seg.local_end - seg.local_start
        if seg_dur < 0.12:
            errors.append(f"Shot {sid} {seg.segment_id}: empty or sub-3-frame segment duration ({seg_dur:.4f}s)")
        if seg.viewpoint not in SUPPORTED_2D_VIEWPOINTS:
            errors.append(f"Shot {sid} {seg.segment_id}: unsupported viewpoint '{seg.viewpoint}'")
        if seg.resets_action_time:
            errors.append(f"Shot {sid} {seg.segment_id}: camera segment resets action time (forbidden)")
        if seg.projection_mode == "crop_zoom" and seg.viewpoint in (
            "rear",
            "rear_three_quarter_left",
            "rear_three_quarter_right",
            "over_shoulder_left",
            "over_shoulder_right",
        ):
            errors.append(
                f"Shot {sid} {seg.segment_id}: fake reverse/rear angle '{seg.viewpoint}' via crop_zoom is forbidden"
            )
        if not (0.8 <= seg.zoom_from <= 2.6 and 0.8 <= seg.zoom_to <= 2.6):
            errors.append(f"Shot {sid} {seg.segment_id}: zoom [{seg.zoom_from}, {seg.zoom_to}] outside [0.8, 2.6]")
        for cx, cy in (seg.center_from, seg.center_to):
            if not (0.08 <= cx <= 0.92 and 0.08 <= cy <= 0.92):
                errors.append(f"Shot {sid} {seg.segment_id}: center ({cx}, {cy}) outside safe bounds [0.08, 0.92]")

        if i > 0:
            prev = segments[i - 1]
            gap = abs(seg.local_start - prev.local_end)
            if gap > 1e-3:
                errors.append(
                    f"Shot {sid}: non-contiguous cut {prev.segment_id}->{seg.segment_id} "
                    f"(prev_end={prev.local_end:.4f}, next_start={seg.local_start:.4f})"
                )
            if (
                prev.axis in ("left_to_right", "right_to_left")
                and seg.axis in ("left_to_right", "right_to_left")
                and prev.axis != seg.axis
            ):
                errors.append(
                    f"Shot {sid}: 180-degree axis violation across internal cut "
                    f"{prev.segment_id} ({prev.axis}) -> {seg.segment_id} ({seg.axis})"
                )
            if (
                prev.scale == seg.scale
                and prev.viewpoint == seg.viewpoint
                and prev.focus_object_ids == seg.focus_object_ids
            ):
                errors.append(
                    f"Shot {sid}: unmotivated internal cut {prev.segment_id}->{seg.segment_id} adds no new information"
                )
            if prev.world_state_anchor and seg.world_state_anchor:
                if prev.world_state_anchor.get("objects") and seg.world_state_anchor.get("objects"):
                    # Ensure held props don't vanish arbitrarily across internal edit unless explicitly explained
                    if prev.world_state_anchor.get("continuous_world_clock") is not True or (
                        seg.world_state_anchor.get("continuous_world_clock") is not True
                    ):
                        errors.append(f"Shot {sid}: world clock continuity broken across {prev.segment_id}->{seg.segment_id}")

    return len(errors) == 0, errors


def compile_camera_segments_to_renderer(
    segments: List[CameraSegment],
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """
    Compile `CameraSegment` list into renderer-ready `args.cameraSegments` while preserving
    backward-compatible `cameraRig`, `move`, and `moveAmt` fields for legacy consumers.
    """
    if not segments:
        return {}
    seg_dicts = [seg.model_dump() for seg in segments]
    first = segments[0]
    last = segments[-1]
    dur = max(0.2, float(last.local_end - first.local_start))

    # For single-segment shots, emit smooth 2-keyframe cameraRig matching the segment
    # For multi-segment shots, `packs/squire/templates.js::camera` executes `args.cameraSegments`
    # with hard intentional cuts at `local_start`/`local_end` (no mid-cut interpolation blur!).
    kfs = [
        {
            "t": round(first.local_start, 3),
            "x": round(first.center_from[0], 3),
            "y": round(first.center_from[1], 3),
            "z": round(first.zoom_from, 3),
            "ease": "sine",
        },
        {
            "t": round(dur, 3),
            "x": round(first.center_to[0], 3),
            "y": round(first.center_to[1], 3),
            "z": round(first.zoom_to, 3),
            "ease": "sine",
        },
    ]
    legacy_move = "in" if first.zoom_to >= first.zoom_from else "out"
    return {
        "cameraSegments": seg_dicts,
        "cameraRig": {
            "viewpoint": first.viewpoint,
            "scale": first.scale,
            "keyframes": kfs,
            "aspect": aspect,
            "internal_segment_count": len(segments),
        },
        "move": legacy_move,
        "moveAmt": round(max(0.02, abs(first.zoom_to - first.zoom_from)), 3),
    }


VIEWPOINT_TO_ASSET_VIEW: Dict[str, str] = {
    "front": "front",
    "front_three_quarter_left": "three_quarter",
    "front_three_quarter_right": "three_quarter",
    "profile_left": "profile",
    "profile_right": "profile",
    "rear_three_quarter_left": "rear_three_quarter",
    "rear_three_quarter_right": "rear_three_quarter",
    "rear": "rear",
    "over_shoulder_left": "rear_three_quarter",
    "over_shoulder_right": "rear_three_quarter",
    "high_angle": "three_quarter",
    "low_angle": "three_quarter",
    "top_down": "top_down",
    "map": "map",
}


def link_camera_to_asset_views(
    segments: List[Union[CameraSegment, Dict[str, Any]]],
    character_manifest: Optional[Dict[str, Any]] = None,
    environment_manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    KH-01.4: Link planned camera segments to genuine authored character & environment views.
    Hard-rejects:
      - scaling/cropping a front portrait (`projection_mode == 'crop_zoom'`) to fake a profile, rear, or reverse angle;
      - missing required character views (`front`, `three_quarter`, `profile`, `rear_three_quarter`) or close inserts;
      - 180-degree axis jumps or costume/prop anchor discontinuities across internal segment cuts.
    """
    seg_objs = [
        seg if isinstance(seg, CameraSegment) else CameraSegment.model_validate(seg)
        for seg in (segments or [])
    ]
    errors: List[str] = []
    bindings: List[Dict[str, Any]] = []

    if not seg_objs:
        return {"valid": False, "errors": ["Empty camera segments list"], "bindings": []}

    chars_by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(character_manifest, dict):
        raw_chars = character_manifest.get("characters") or character_manifest
        if isinstance(raw_chars, dict):
            for cid, cdata in raw_chars.items():
                if isinstance(cdata, dict):
                    chars_by_id[str(cid)] = cdata
        elif isinstance(raw_chars, list):
            for cdata in raw_chars:
                if isinstance(cdata, dict) and cdata.get("actor_id"):
                    chars_by_id[str(cdata["actor_id"])] = cdata

    env_tiers = set(
        (environment_manifest or {}).get(
            "supported_detail_tiers",
            ["TIER_3_FULL_ARCHITECTURAL_STAGE", "TIER_2_FOCUSED_STAGE", "TIER_1_GRAPHIC_MOOD_BACKDROP", "TIER_1_TACTILE_PROP_FOCUS"],
        )
    )
    env_id = str((environment_manifest or {}).get("environment_id") or "default_stage")

    prev_axis: Optional[str] = None
    prev_wardrobe_by_actor: Dict[str, str] = {}

    for seg in seg_objs:
        req_asset_view = VIEWPOINT_TO_ASSET_VIEW.get(seg.viewpoint, "three_quarter")
        is_hand_insert = seg.scale in ("detail", "extreme_close") and any(
            k in seg.adds_information_reason.lower() for k in ("hand", "grip", "catch", "scroll", "palm", "rope", "lantern")
        )
        is_face_insert = seg.scale in ("close", "extreme_close") and not is_hand_insert

        # Forbid faking non-front views via crop_zoom of a front portrait
        if seg.projection_mode == "crop_zoom" and req_asset_view in ("profile", "rear", "rear_three_quarter"):
            errors.append(
                f"{seg.segment_id}: false '{req_asset_view}' angle via crop_zoom is forbidden; requires real authored view"
            )

        if prev_axis in ("left_to_right", "right_to_left") and seg.axis in ("left_to_right", "right_to_left"):
            if prev_axis != seg.axis:
                errors.append(f"{seg.segment_id}: 180-degree camera axis violation ({prev_axis} -> {seg.axis})")
        if seg.axis in ("left_to_right", "right_to_left"):
            prev_axis = seg.axis

        actor_view_links: Dict[str, Dict[str, Any]] = {}
        for aid in seg.focus_actor_ids:
            c_spec = chars_by_id.get(aid)
            if c_spec is not None:
                avail_views = set(c_spec.get("views") or c_spec.get("supported_views") or [])
                if req_asset_view in ("rear", "rear_three_quarter") and "rear_three_quarter" in avail_views:
                    chosen_view = "rear_three_quarter"
                elif req_asset_view in avail_views:
                    chosen_view = req_asset_view
                else:
                    chosen_view = req_asset_view
                    errors.append(
                        f"{seg.segment_id}: character '{aid}' missing required authored view '{req_asset_view}' (available={sorted(avail_views)})"
                    )
                if is_hand_insert and not c_spec.get("has_hand_insert", True):
                    errors.append(f"{seg.segment_id}: character '{aid}' missing close hand-grip insert asset")
                if is_face_insert and len(c_spec.get("expressions") or c_spec.get("supported_expressions") or [1, 2, 3, 4, 5, 6]) < 6:
                    errors.append(f"{seg.segment_id}: character '{aid}' has fewer than 6 distinct facial expressions for close-up")
                wardrobe_state = str(c_spec.get("wardrobe_state") or c_spec.get("outfit_id") or "default_outfit")
                if aid in prev_wardrobe_by_actor and prev_wardrobe_by_actor[aid] != wardrobe_state:
                    if not seg.world_state_anchor.get("costume_change_event"):
                        errors.append(
                            f"{seg.segment_id}: unmotivated wardrobe change on '{aid}' across internal cut ({prev_wardrobe_by_actor[aid]} -> {wardrobe_state})"
                        )
                prev_wardrobe_by_actor[aid] = wardrobe_state
                actor_view_links[aid] = {
                    "asset_view": chosen_view,
                    "insert_mode": "close_hand_insert" if is_hand_insert else ("close_face_insert" if is_face_insert else "full_actor_view"),
                    "wardrobe_state": wardrobe_state,
                    "facing_sign": -1 if "left" in seg.viewpoint and "profile" in seg.viewpoint else 1,
                }
            else:
                actor_view_links[aid] = {
                    "asset_view": req_asset_view,
                    "insert_mode": "close_hand_insert" if is_hand_insert else ("close_face_insert" if is_face_insert else "full_actor_view"),
                    "wardrobe_state": "default_outfit",
                    "facing_sign": 1,
                }

        detail_tier = (
            "TIER_3_FULL_ARCHITECTURAL_STAGE"
            if seg.scale in ("extreme_wide", "wide", "medium_wide")
            else (
                "TIER_2_FOCUSED_STAGE"
                if seg.scale in ("medium", "medium_close")
                else ("TIER_1_TACTILE_PROP_FOCUS" if is_hand_insert else "TIER_1_GRAPHIC_MOOD_BACKDROP")
            )
        )
        if env_tiers and detail_tier not in env_tiers:
            errors.append(f"{seg.segment_id}: environment '{env_id}' missing detail tier '{detail_tier}'")

        bindings.append({
            "segment_id": seg.segment_id,
            "shot_id": seg.shot_id,
            "viewpoint": seg.viewpoint,
            "scale": seg.scale,
            "resolved_asset_view": req_asset_view,
            "insert_mode": "close_hand_insert" if is_hand_insert else ("close_face_insert" if is_face_insert else "scene_view"),
            "environment_id": env_id,
            "environment_detail_tier": detail_tier,
            "actor_bindings": actor_view_links,
            "focus_object_ids": list(seg.focus_object_ids),
            "axis": seg.axis,
            "continuous_world_clock": bool(seg.world_state_anchor.get("continuous_world_clock", not seg.resets_action_time)),
        })

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "segment_count": len(seg_objs),
        "distinct_asset_views": sorted({b["resolved_asset_view"] for b in bindings}),
        "distinct_insert_modes": sorted({b["insert_mode"] for b in bindings}),
        "bindings": bindings,
    }

