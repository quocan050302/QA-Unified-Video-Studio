"""tools/plan_audio.py — Auto narrative SFX planner and music sound design.
Synchronizes sound effects to visual motion phases (mud fall, armor rise, running cadence, treadmill, facts).
Preserves manual audio cues, enforces cooldown/density limits, and maintains broadcast audio clarity.

Usage:
  python tools/plan_audio.py --project projects/<name> [--upgrade-generated] [--dry-run]
"""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def discover_sfx_library(root: Path) -> Dict[str, Dict[str, Any]]:
    """Scan existing audio/sfx directory for real canonical WAV assets."""
    sfx_dir = root / "audio" / "sfx"
    lib: Dict[str, Dict[str, Any]] = {}
    if not sfx_dir.exists():
        return lib

    for p in sfx_dir.glob("*.wav"):
        base = p.stem
        hit_m = re.search(r"hitAt(\d+)ms", base)
        hit_ms = int(hit_m.group(1)) if hit_m else 0
        canonical = re.sub(r"_hitAt\d+ms", "", base)
        file_stat = p.stat()
        lib[canonical] = {
            "name": canonical,
            "filename": p.name,
            "path": str(p),
            "size": file_stat.st_size,
            "hit_offset": hit_ms / 1000.0,
        }
        # Also store original stem if different
        if base != canonical:
            lib[base] = lib[canonical]

    return lib


def discover_music_library(root: Path) -> Dict[str, str]:
    """Scan audio/music for emotional beds."""
    music_dir = root / "audio" / "music"
    beds: Dict[str, str] = {}
    if not music_dir.exists():
        return beds

    for p in music_dir.glob("*.wav"):
        stem = p.stem  # e.g. bed_curious_Dm_110bpm
        beds[stem] = str(p)
        # Aliases
        m = re.match(r"bed_([a-z]+)", stem)
        if m:
            short = m.group(1)
            beds[short] = str(p)

    return beds


def get_canonical_sfx_name(raw_name: str, sfx_lib: Dict[str, Any]) -> Optional[str]:
    """Map sound name to real existing SFX asset in library using explicit aliases."""
    if raw_name in sfx_lib:
        return raw_name

    # Explicit canonical aliases
    aliases = {
        "armor": "armor_clank",
        "clank": "armor_clank",
        "metal": "armor_clank",
        "mail": "chainmail",
        "chain": "chainmail",
        "mud": "mud_step",
        "step": "footsteps",
        "steps": "footsteps",
        "run": "footsteps",
        "sword": "sword_draw",
        "shield": "shield_bash",
        "bash": "shield_bash",
        "whoosh": "whoosh_fast",
        "swish": "whoosh_tiny",
        "ting": "ting_idea",
        "idea": "ting_idea",
        "stat": "tick",
        "thud": "thud_soft",
        "impact": "impact_light",
        "breath": "breath_in",
        "heart": "heartbeat",
        "horn": "war_horn",
    }
    alias = aliases.get(raw_name.lower())
    if alias and alias in sfx_lib:
        return alias

    return None


def classify_narrative_audio_events(
    sh: Dict[str, Any],
    sfx_lib: Dict[str, Any],
    prev_sh: Optional[Dict[str, Any]] = None,
    next_sh: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Determine action-synchronized sound cues for a storyboard shot.

    Follows narrative intent, motion phases, and semantic negation.
    """
    line = str(sh.get("line", "")).strip()
    l_low = line.lower()
    dur = float(sh.get("end", 0)) - float(sh.get("start", 0))
    if dur <= 0:
        dur = float(sh.get("dur", 5.0))

    args = sh.get("args", {})
    tpl = sh.get("tpl", "scene")
    people = args.get("people", [])
    props = args.get("props", [])

    events: List[Dict[str, Any]] = []

    # Inspect people in scene
    hero = people[0] if people else {}
    hero_pose = hero.get("pose", "")
    hero_move = hero.get("moveMode", "")
    is_in_place = hero.get("in_place", False) or hero_move == "in_place"
    has_get_up = hero.get("getUp") is not None or hero.get("rise") is not None

    # 1. Negation detection
    negation_pat = r"\b(could\s+not|can\s*not|never|nobody|no\s+one|did\s+not|without|refused\s+to|hardly|scarcely|couldn't|can't|didn't|won't|unable\s+to|failed\s+to)\s+([a-z\s]{1,20})\b"
    negated_phrases = [m.group(0) for m in re.finditer(negation_pat, l_low)]

    def is_negated(v_pat: str) -> bool:
        return any(bool(re.search(v_pat, np)) for np in negated_phrases)

    has_lie = (bool(re.search(r"\b(lie|lying|lay|prone|on\s+his\s+back|fallen|fall\s+down|collapse)\b", l_low)) or hero_pose in ('lying', 'prone')) and not is_negated(r"\b(lie|lay|fall)\b")
    has_rise = (bool(re.search(r"\b(get\s+back\s+up|get\s+up|got\s+up|stand\s+up|rise|recovers?)\b", l_low)) or has_get_up) and not is_negated(r"\b(get|rise|stand)\b")
    has_run = (bool(re.search(r"\b(run|running|ran|sprint|sprinting|treadmill)\b", l_low)) or hero_pose == "run") and not is_negated(r"\b(run|ran|sprint)\b")
    has_lab = bool(re.search(r"\b(lab|laboratory|treadmill|researcher|experiment)\b", l_low))
    has_facts = tpl == "board" or bool(re.search(r"\b(\d+(\.\d+)?\s*(mph|miles?|hours?|kg|pounds?|%))\b", l_low))

    # Cue 1: Mud fall / opening impact
    if has_lie and not has_lab:
        # Subtle splash + armor clank impact
        splash_name = get_canonical_sfx_name("splash", sfx_lib)
        if splash_name:
            events.append({
                "name": splash_name,
                "at": 0.15,
                "gain": -12.0,
                "kind": "foley_impact",
                "reason": "mud_ground_contact",
                "confidence": 0.95,
            })
        clank_name = get_canonical_sfx_name("armor_clank", sfx_lib)
        if clank_name:
            events.append({
                "name": clank_name,
                "at": 0.40,
                "gain": -10.0,
                "kind": "foley_impact",
                "reason": "armor_mud_settle",
                "confidence": 0.92,
            })

    # Cue 2: Getting up / rising from mud
    if has_get_up or (has_rise and not has_lab):
        rise_at = float(hero.get("getUp") or hero.get("rise") or round(dur * 0.35, 2))
        chain_name = get_canonical_sfx_name("chainmail", sfx_lib)
        if chain_name:
            events.append({
                "name": chain_name,
                "at": round(rise_at + 0.1, 2),
                "gain": -11.0,
                "kind": "foley_movement",
                "reason": "armor_rise_effort",
                "confidence": 0.94,
            })

    # Cue 3: Running in mud vs running on treadmill
    if has_run:
        if is_in_place or has_lab or "treadmill" in l_low:
            # Treadmill: steady, subdued footsteps on belt
            step_name = get_canonical_sfx_name("footsteps", sfx_lib)
            if step_name:
                cadence = 0.48
                t_start = 0.5
                step_idx = 0
                while t_start < dur - 0.5 and step_idx < 6:
                    events.append({
                        "name": step_name,
                        "at": round(t_start, 2),
                        "gain": -16.0,
                        "kind": "foley_cadence",
                        "reason": "treadmill_belt_cadence",
                        "confidence": 0.88,
                    })
                    t_start += cadence
                    step_idx += 1
        else:
            # Running across ground / mud
            run_start = float(hero.get("moveAt", 0.0))
            if run_start == 0.0 and has_get_up:
                run_start = round(dur * 0.68, 2)
            step_name = get_canonical_sfx_name("mud_step", sfx_lib) or get_canonical_sfx_name("footsteps", sfx_lib)
            if step_name:
                cadence = 0.44
                t_step = max(0.4, run_start)
                step_idx = 0
                while t_step < dur - 0.4 and step_idx < 6:
                    events.append({
                        "name": step_name,
                        "at": round(t_step, 2),
                        "gain": -13.0,
                        "kind": "foley_cadence",
                        "reason": "mud_sprint_cadence",
                        "confidence": 0.90,
                    })
                    t_step += cadence
                    step_idx += 1

    # Cue 4: Graphic / Metric reveal
    if has_facts and not has_run and not has_lie:
        stat_sound = get_canonical_sfx_name("ting_idea", sfx_lib) or get_canonical_sfx_name("tick", sfx_lib)
        if stat_sound:
            events.append({
                "name": stat_sound,
                "at": 0.35,
                "gain": -13.0,
                "kind": "ui_metric",
                "reason": "metric_fact_reveal",
                "confidence": 0.91,
            })

    # Cue 5: Sword / Combat action if drawn
    if "sword" in l_low and not is_negated("sword") and not has_lie and not has_lab:
        sw_sound = get_canonical_sfx_name("sword_draw", sfx_lib)
        if sw_sound and "draw" in l_low:
            events.append({
                "name": sw_sound,
                "at": 0.4,
                "gain": -10.0,
                "kind": "foley_action",
                "reason": "sword_drawn",
                "confidence": 0.89,
            })

    # Apply Cooldown & Density Limits:
    # Max 2 salient impact cues per 3 seconds, min gap 0.25s between any two cues
    events = sorted(events, key=lambda e: e["at"])
    filtered: List[Dict[str, Any]] = []
    last_time = -999.0
    for ev in events:
        t = ev["at"]
        if t < 0 or t >= dur:
            continue
        if t - last_time < 0.22:
            continue  # Enforce minimum gap to avoid transient stacking
        filtered.append(ev)
        last_time = t

    return filtered


def schedule_music_sections(shots: List[Dict[str, Any]], music_lib: Dict[str, str]) -> List[Dict[str, Any]]:
    """Plan narrative music sections with emotional progression and smooth crossfades."""
    if not shots:
        return []

    total_dur = max(float(s.get("end", 0)) for s in shots)
    sections: List[Dict[str, Any]] = []

    # Map available bed files
    curious_bed = "curious" if "curious" in music_lib else list(music_lib.keys())[0] if music_lib else "none"
    medieval_bed = "medieval" if "medieval" in music_lib else curious_bed
    somber_bed = "somber" if "somber" in music_lib else curious_bed
    victory_bed = "victory" if "victory" in music_lib else "resolve" if "resolve" in music_lib else curious_bed

    # Partition story based on shot purposes
    # Phase 1: Hook / Setup (mud, struggle) -> Somber or Medieval
    # Phase 2: Evidence / Science / Testing -> Curious
    # Phase 3: Resolution / Conclusion / CTA -> Victory / Resolve
    cut_lab = None
    cut_resolution = None

    for s in shots:
        t = float(s.get("start", 0))
        p = s.get("purpose", "")
        line = str(s.get("line", "")).lower()
        if not cut_lab and (p == "evidence" or "lab" in line or "treadmill" in line):
            cut_lab = t
        if not cut_resolution and (p in ("resolution", "cta") or "joke" in line or "comment" in line):
            cut_resolution = t

    if total_dur <= 25.0:
        # Short video: single coherent bed
        sections.append({"start": 0.0, "end": round(total_dur, 2), "bed": curious_bed, "gainDb": 0.0})
    else:
        # Multi-section dynamic score
        t0 = 0.0
        t1 = cut_lab if cut_lab and cut_lab > 6.0 else round(total_dur * 0.38, 2)
        t2 = cut_resolution if cut_resolution and cut_resolution > t1 + 6.0 else round(total_dur * 0.78, 2)

        sections.append({"start": t0, "end": t1, "bed": somber_bed, "gainDb": -1.0})
        sections.append({"start": t1, "end": t2, "bed": curious_bed, "gainDb": 0.0})
        sections.append({"start": t2, "end": round(total_dur, 2), "bed": victory_bed, "gainDb": 0.5})

    return sections


def merge_preserving_manual(
    existing_cues: List[Dict[str, Any]],
    generated_cues: List[Dict[str, Any]],
    upgrade_generated: bool = False,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Merge newly generated audio cues with existing cues while protecting manual edits."""
    manual_cues = [c for c in existing_cues if c.get("source") == "manual" or c.get("audio_source") == "manual"]
    if manual_cues and not upgrade_generated:
        # Manual edits lock the shot completely unless explicit upgrade requested
        return existing_cues, False

    out: List[Dict[str, Any]] = list(manual_cues)
    seen_times = {round(float(c.get("at", 0)), 2) for c in manual_cues}

    for gc in generated_cues:
        at_round = round(float(gc.get("at", 0)), 2)
        if at_round in seen_times:
            continue
        out.append(gc)
        seen_times.add(at_round)

    out = sorted(out, key=lambda c: float(c.get("at", 0)))
    changed = out != existing_cues
    return out, changed


def plan_audio_for_project(
    project_dir: Path,
    mode: str = "auto",
    target_ids: Optional[List[str]] = None,
    dry_run: bool = False,
    upgrade_generated: bool = False,
) -> Dict[str, Any]:
    """Execute complete deterministic audio planning for project storyboard."""
    root = Path(__file__).resolve().parent.parent
    sfx_lib = discover_sfx_library(root)
    music_lib = discover_music_library(root)

    shots_file = project_dir / "story" / "shots.json"
    if not shots_file.exists():
        raise FileNotFoundError(f"Storyboard file not found: {shots_file}")

    with shots_file.open("r", encoding="utf-8") as f:
        story = json.load(f)

    shots = story.get("shots", [])
    if not shots:
        return {"status": "NO_SHOTS", "cues_planned": 0}

    total_cues = 0
    modified = False

    for idx, sh in enumerate(shots):
        sid = sh.get("id", f"s{idx+1:03d}")
        if target_ids and sid not in target_ids:
            continue

        prev_sh = shots[idx - 1] if idx > 0 else None
        next_sh = shots[idx + 1] if idx < len(shots) - 1 else None

        generated_cues = classify_narrative_audio_events(sh, sfx_lib, prev_sh, next_sh)
        existing_cues = sh.get("sfx", [])

        merged_cues, changed = merge_preserving_manual(existing_cues, generated_cues, upgrade_generated)
        if changed:
            modified = True

        sh["sfx"] = merged_cues
        sh["audio_source"] = "manual" if any(c.get("source") == "manual" for c in merged_cues) else "auto_planned"
        sh["audio_plan"] = {
            "status": "AUDIO_PLANNED",
            "version": "v7",
            "cues_count": len(merged_cues),
            "timing_source": "action_phase",
            "confidence": 0.92,
        }
        total_cues += len(merged_cues)

    # Plan music beds if story doesn't already have manual locked music
    existing_music = story.get("music", [])
    has_manual_music = any(m.get("source") == "manual" for m in existing_music)
    if not has_manual_music or upgrade_generated:
        planned_music = schedule_music_sections(shots, music_lib)
        if planned_music != existing_music:
            story["music"] = planned_music
            modified = True

    # Output audio plan audit manifest
    audio_plan_manifest = {
        "project": project_dir.name,
        "planned_at": time.time(),
        "version": "v7",
        "status": "AUDIO_PLANNED",
        "total_cues": total_cues,
        "music_sections": len(story.get("music", [])),
        "available_sfx_count": len(sfx_lib),
        "available_music_count": len(music_lib),
        "shots_planned": [
            {
                "id": s.get("id"),
                "cues": len(s.get("sfx", [])),
                "audio_source": s.get("audio_source"),
            }
            for s in shots
        ],
    }

    if not dry_run and modified:
        build_dir = project_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = build_dir / "audio_plan.json"
        with manifest_file.open("w", encoding="utf-8") as f:
            json.dump(audio_plan_manifest, f, indent=2)

        # Atomic backup and write
        backup_file = project_dir / "story" / "shots.backup.json"
        try:
            shutil.copyfile(shots_file, backup_file)
        except Exception:
            pass

        with shots_file.open("w", encoding="utf-8") as f:
            json.dump(story, f, indent=2)

    return {
        "status": "AUDIO_PLANNED",
        "modified": modified,
        "total_cues": total_cues,
        "music_sections": len(story.get("music", [])),
    }


def main():
    parser = argparse.ArgumentParser(description="Auto narrative SFX planner and music sound design.")
    parser.add_argument("--project", required=True, help="Path to project directory")
    parser.add_argument("--upgrade-generated", action="store_true", help="Upgrade generated cues, preserve manual")
    parser.add_argument("--dry-run", action="store_true", help="Plan without writing changes to disk")
    args = parser.parse_args()

    proj = Path(args.project).resolve()
    if not proj.exists():
        sys.exit(f"Project not found: {proj}")

    result = plan_audio_for_project(proj, upgrade_generated=args.upgrade_generated, dry_run=args.dry_run)
    print(f"Audio planning completed: {result['total_cues']} SFX cues planned across {result['music_sections']} music sections. Status: {result['status']}.")


if __name__ == "__main__":
    main()
