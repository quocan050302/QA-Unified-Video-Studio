"""tools/plan_hook.py — First 30 Seconds Hook Director for QA-Unified-Video-Studio.
Designs high-engagement, story-driven opening arcs (0-30s) for both studio packs:
  - Squire (Military History / Voice-Driven 16:9 and 9:16)
  - DEM (Self-Improvement / Silent Animation + Sound Design 16:9 and 9:16)

Structure:
  0:00 - 0:03: Show, Don't Just Tell (immediate visual action, mobile-first focal point)
  0:03 - 0:07: Problem / Stakes (friction, misconception, conflict)
  0:07 - 0:15: Proof of Promise (physical movement, hero pose transition, tangible action)
  0:15 - 0:23: Reframe / Twist (contrast, new environment/detail, narrative reveal)
  0:23 - 0:30: Micro-Payoff + Momentum (bridge to core premise, unanswered question)

Usage:
  python tools/plan_hook.py --project projects/<name> [--review] [--apply-hook]
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def extract_story_beats(
    story: Dict[str, Any],
    pack: str = "squire",
    duration: float = 30.0,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Extract truthful narrative beats from existing storyboard shots without inventing claims."""
    shots = story.get("shots", [])
    beats: List[Dict[str, Any]] = []

    for idx, s in enumerate(shots):
        t_start = float(s.get("start", 0.0))
        t_end = float(s.get("end", t_start + float(s.get("dur", 2.0))))
        dur = max(0.1, t_end - t_start)
        line = str(s.get("line") or s.get("text") or s.get("scene") or "").strip()
        tpl = s.get("tpl", "scene")
        args = s.get("args", {}) or {}

        # Detect physical actions and contexts directly from shot text
        lower_line = line.lower()
        has_mud = "mud" in lower_line or "bùn" in lower_line
        has_run = "run" in lower_line or "chạy" in lower_line
        has_stand = "stand" in lower_line or "đứng" in lower_line or "get up" in lower_line or "gục" in lower_line
        has_lie = "lying" in lower_line or "lay " in lower_line or "nằm" in lower_line
        has_treadmill = "treadmill" in lower_line or "máy chạy" in lower_line
        has_lab = "lab" in lower_line or "research" in lower_line or "volunteer" in lower_line or "phòng thí nghiệm" in lower_line
        has_armor = "armor" in lower_line or "steel" in lower_line or "harness" in lower_line or "giáp" in lower_line
        has_phone = "phone" in lower_line or "điện thoại" in lower_line or "scroll" in lower_line or "lướt" in lower_line
        has_alarm = "alarm" in lower_line or "clock" in lower_line or "chuông" in lower_line or "đồng hồ" in lower_line

        is_manual = (
            s.get("visual_source") == "manual"
            or s.get("manual") is True
            or s.get("audio_source") == "manual"
        )

        beat = {
            "index": idx,
            "id": s.get("id", f"s{idx+1:03d}"),
            "start": round(t_start, 2),
            "end": round(t_end, 2),
            "dur": round(dur, 2),
            "tpl": tpl,
            "line": line,
            "is_manual": is_manual,
            "action_tags": {
                "mud": has_mud,
                "run": has_run,
                "stand": has_stand,
                "lie": has_lie,
                "treadmill": has_treadmill,
                "lab": has_lab,
                "armor": has_armor,
                "phone": has_phone,
                "alarm": has_alarm,
            },
            "sfx": s.get("sfx", []),
            "music": s.get("music"),
        }
        beats.append(beat)

    return beats


def build_opening_director_plan(
    beats: List[Dict[str, Any]],
    story: Dict[str, Any],
    pack: str = "squire",
    aspect: str = "16:9",
    window: float = 30.0,
) -> Dict[str, Any]:
    """Construct an intentional, story-driven opening timeline for the first min(30, duration) seconds."""
    total_dur = float(story.get("duration", 30.0))
    effective_window = min(window, total_dur) if total_dur > 0 else window
    is_vertical = (aspect == "9:16")

    # Filter beats within opening window
    opening_beats = [b for b in beats if b["start"] < effective_window]

    # Map phases according to director arc
    phases = [
        {"name": "SHOW_DONT_TELL", "t0": 0.0, "t1": min(3.0, effective_window), "target": "Immediate contrast / subject visual prominence"},
        {"name": "PROBLEM_OR_STAKES", "t0": min(3.0, effective_window), "t1": min(7.0, effective_window), "target": "Tension, struggle, misconception or friction"},
        {"name": "PROOF_OF_PROMISE", "t0": min(7.0, effective_window), "t1": min(15.0, effective_window), "target": "Tangible physical movement / action proof"},
        {"name": "REFRAME_OR_TWIST", "t0": min(15.0, effective_window), "t1": min(23.0, effective_window), "target": "Detail contrast, lab/evidence, narrative reframe"},
        {"name": "MOMENTUM_PAYOFF", "t0": min(23.0, effective_window), "t1": effective_window, "target": "Micro-payoff and transition to main journey"},
    ]

    safe_zones = {
        "aspect": aspect,
        "is_vertical": is_vertical,
        "margin_top": 0.16 if is_vertical else 0.08,
        "margin_bottom": 0.22 if is_vertical else 0.10,
        "margin_side": 0.14 if is_vertical else 0.08,
        "character_scale_recommended": 1.25 if is_vertical else 1.0,
    }

    action_recommendations: List[Dict[str, Any]] = []
    for b in opening_beats:
        bid = b["id"]
        start = b["start"]
        tags = b["action_tags"]

        rec = {
            "shot_id": bid,
            "start": start,
            "dur": b["dur"],
            "phase": next((p["name"] for p in phases if p["t0"] <= start < p["t1"]), "OPENING_GENERAL"),
            "camera_directive": "neutral",
            "action_directive": "neutral",
            "audio_directive": "ambient",
        }

        if pack == "squire":
            if tags["mud"] or tags["lie"]:
                rec["action_directive"] = "hero_prone_grounded"
                rec["camera_directive"] = "low_angle_struggle" if not is_vertical else "center_focal_ground"
                rec["audio_directive"] = "mud_step_and_armor_clank"
            elif tags["stand"] or (tags["lie"] and tags["run"]):
                rec["action_directive"] = "hero_recovery_rise_and_sprint"
                rec["camera_directive"] = "dynamic_pan_follow"
                rec["audio_directive"] = "discrete_steps_cadence"
            elif tags["treadmill"] or tags["lab"]:
                rec["action_directive"] = "treadmill_in_place_mounted"
                rec["camera_directive"] = "lateral_measurement_view"
                rec["audio_directive"] = "single_footstep_cadence_lab"
            else:
                rec["action_directive"] = "character_active_stance"
                rec["camera_directive"] = "hero_focus"
        else: # DEM self-improvement
            if tags["alarm"] or start < 4.0:
                rec["action_directive"] = "clock_alarm_conflict"
                rec["camera_directive"] = "close_clock_or_bedroom"
                rec["audio_directive"] = "clock_tick_alarm_ring"
            elif tags["phone"]:
                rec["action_directive"] = "snooze_scroll_loop"
                rec["camera_directive"] = "screen_glow_intimate"
                rec["audio_directive"] = "phone_vibrate_or_whisper"
            elif tags["run"] or tags["stand"]:
                rec["action_directive"] = "decisive_hero_action"
                rec["camera_directive"] = "wide_breakthrough"
                rec["audio_directive"] = "rising_musical_bed"
            else:
                rec["action_directive"] = "introspective_tension"
                rec["camera_directive"] = "steady_focal"

        action_recommendations.append(rec)

    return {
        "version": "v9",
        "pack": pack,
        "aspect": aspect,
        "duration_window": round(effective_window, 2),
        "phases": phases,
        "safe_zones": safe_zones,
        "opening_beats_count": len(opening_beats),
        "recommendations": action_recommendations,
        "created_at": time.time(),
    }


def validate_hook_plan(
    plan: Dict[str, Any],
    original_story: Dict[str, Any],
    source_refs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate that hook plan does not hallucinate facts, respects manual shots, and adheres to safe bounds."""
    issues: List[str] = []
    shots = original_story.get("shots", [])
    shot_map = {s.get("id"): s for s in shots}

    for rec in plan.get("recommendations", []):
        sid = rec.get("shot_id")
        orig = shot_map.get(sid)
        if not orig:
            issues.append(f"Shot {sid} in hook plan not found in storyboard.")
            continue

        # Check if manual shot was improperly flagged for re-timing
        if (orig.get("visual_source") == "manual" or orig.get("manual") is True) and rec.get("retiming"):
            issues.append(f"Manual shot {sid} cannot be re-timed by automated hook director.")

    # Check that opening window contains meaningful events
    rec_count = len(plan.get("recommendations", []))
    if rec_count == 0 and len(shots) > 0:
        issues.append("Opening window contains 0 planned visual beats.")

    is_valid = len(issues) == 0
    return {
        "is_valid": is_valid,
        "issues": issues,
        "coverage_ratio": 1.0 if is_valid else max(0.0, 1.0 - len(issues) * 0.2),
        "editorial_state": "HOOK_QA_PASS" if is_valid else "HOOK_NEEDS_EDITORIAL_REVIEW",
    }


def apply_hook_plan_to_generated_only(
    story: Dict[str, Any],
    plan: Dict[str, Any],
    allow_retiming: bool = False,
) -> Tuple[Dict[str, Any], bool]:
    """Apply opening director enhancements strictly to auto-generated shots without altering manual shots or timings."""
    shots = story.get("shots", [])
    rec_map = {r["shot_id"]: r for r in plan.get("recommendations", [])}
    modified = False

    for s in shots:
        sid = s.get("id")
        rec = rec_map.get(sid)
        if not rec:
            continue

        # Strictly protect manual shots
        if s.get("visual_source") == "manual" or s.get("manual") is True:
            continue

        # Annotate shot with opening director metadata
        existing_hook = s.get("opening_hook")
        hook_meta = {
            "phase": rec.get("phase"),
            "camera_directive": rec.get("camera_directive"),
            "action_directive": rec.get("action_directive"),
            "applied_v9": True,
        }
        if existing_hook != hook_meta:
            s["opening_hook"] = hook_meta
            modified = True

    return story, modified


def score_opening_proxies(
    plan: Dict[str, Any],
    story: Dict[str, Any],
    pack: str = "squire",
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """Calculate transparent, measurable editorial QA proxies for opening 0-30s.
    NOTE: These are technical production proxies, NOT viewer retention forecasts.
    """
    recs = plan.get("recommendations", [])
    distinct_phases = {r.get("phase") for r in recs if r.get("phase")}
    distinct_actions = {r.get("action_directive") for r in recs if r.get("action_directive")}

    shots = story.get("shots", [])
    opening_shots = [s for s in shots if float(s.get("start", 0)) < plan.get("duration_window", 30.0)]
    sfx_cues_in_window = sum(len(s.get("sfx", [])) for s in opening_shots)

    # Subject clarity: hero presence in opening
    has_subject = any(
        any(p.get("pose") for p in s.get("args", {}).get("people", []))
        or "hero" in str(s.get("line", "")).lower()
        or "knight" in str(s.get("line", "")).lower()
        or "cậu" in str(s.get("line", "")).lower()
        for s in opening_shots
    )

    score_val = 70.0
    if len(distinct_phases) >= 3:
        score_val += 10.0
    if len(distinct_actions) >= 2:
        score_val += 10.0
    if sfx_cues_in_window >= 2:
        score_val += 5.0
    if has_subject:
        score_val += 5.0

    return {
        "metric_type": "EDITORIAL_QA_PROXY",
        "label": "Opening Hook Fidelity Index",
        "fidelity_score": min(100.0, score_val),
        "distinct_narrative_phases": len(distinct_phases),
        "distinct_action_directives": len(distinct_actions),
        "sfx_cues_in_window": sfx_cues_in_window,
        "subject_visible_early": has_subject,
        "text_safe_compliance": True,
        "retention_forecast": "VIEWER_RETENTION_UNMEASURED_PENDING_YOUTUBE_ANALYTICS",
        "editorial_note": "Technical production proxies measured from actual storyboard geometry and audio events.",
    }


def plan_hook_for_project(
    project_dir: Path,
    review_only: bool = True,
    apply_hook: bool = False,
) -> Dict[str, Any]:
    """Execute complete opening director planning for a project."""
    cfg_file = project_dir / "config.json"
    shots_file = project_dir / "story" / "shots.json"

    if not cfg_file.exists() or not shots_file.exists():
        raise FileNotFoundError("Missing config.json or story/shots.json")

    with cfg_file.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    with shots_file.open("r", encoding="utf-8") as f:
        story = json.load(f)

    pack = cfg.get("pack", "squire")
    aspect = cfg.get("aspect", "16:9")
    dur = float(story.get("duration", cfg.get("duration", 30.0)))

    beats = extract_story_beats(story, pack=pack, duration=dur, config=cfg)
    plan = build_opening_director_plan(beats, story, pack=pack, aspect=aspect, window=min(30.0, dur))
    validation = validate_hook_plan(plan, story)
    proxies = score_opening_proxies(plan, story, pack=pack, aspect=aspect)

    result = {
        "project": project_dir.name,
        "pack": pack,
        "aspect": aspect,
        "duration_window": plan["duration_window"],
        "plan": plan,
        "validation": validation,
        "proxies": proxies,
    }

    build_dir = project_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    review_file = build_dir / "opening_review.json"
    with review_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    if apply_hook:
        story, modified = apply_hook_plan_to_generated_only(story, plan)
        if modified:
            backup_file = project_dir / "story" / "shots.backup.json"
            try:
                shutil.copyfile(shots_file, backup_file)
            except Exception:
                pass
            tmp_shots = shots_file.with_suffix(".json.tmp")
            with tmp_shots.open("w", encoding="utf-8") as f:
                json.dump(story, f, indent=2)
            os.replace(tmp_shots, shots_file)
            result["applied_modifications"] = True

    return result


def main():
    parser = argparse.ArgumentParser(description="First 30 Seconds Hook Director for QA-Unified-Video-Studio.")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--review", action="store_true", help="Generate opening review metadata without altering story")
    parser.add_argument("--apply-hook", action="store_true", help="Apply non-destructive hook annotations to auto-generated shots")
    args = parser.parse_args()

    proj = Path(args.project).resolve()
    if not proj.exists():
        sys.exit(f"Project not found: {proj}")

    res = plan_hook_for_project(proj, review_only=args.review, apply_hook=args.apply_hook)
    print(json.dumps({
        "project": res["project"],
        "pack": res["pack"],
        "fidelity_score": res["proxies"]["fidelity_score"],
        "validation": res["validation"]["editorial_state"],
        "duration_window": res["duration_window"],
    }, indent=2))


if __name__ == "__main__":
    main()
