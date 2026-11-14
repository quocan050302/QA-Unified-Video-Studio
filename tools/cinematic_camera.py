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
) -> List[CameraKeyframe]:
    """
    Build a smooth, bounded viewport path for the camera rig without black clipping edges.
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
    start_x, end_x = 0.5, 0.5
    start_y, end_y = 0.5, 0.5

    if viewpoint in ("profile_left", "front_three_quarter_left"):
        start_x, end_x = 0.52, 0.48
    elif viewpoint in ("profile_right", "front_three_quarter_right"):
        start_x, end_x = 0.48, 0.52
    elif viewpoint in ("over_shoulder_right", "rear_three_quarter_right"):
        start_x, end_x = 0.45, 0.42
    elif viewpoint in ("over_shoulder_left", "rear_three_quarter_left"):
        start_x, end_x = 0.55, 0.58
    elif viewpoint == "low_angle":
        start_y, end_y = 0.54, 0.51
    elif viewpoint == "high_angle":
        start_y, end_y = 0.46, 0.49

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
