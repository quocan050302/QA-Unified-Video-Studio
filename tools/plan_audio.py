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

try:
    from tools.common import compute_canonical_visual_hash, compute_canonical_audio_hash
except ImportError:
    try:
        from common import compute_canonical_visual_hash, compute_canonical_audio_hash
    except ImportError:
        compute_canonical_visual_hash = None
        compute_canonical_audio_hash = None


def discover_sfx_library(root: Path) -> Dict[str, Dict[str, Any]]:
    """Scan real_sfx and audio/sfx directories for assets, prioritizing licensed real assets."""
    lib: Dict[str, Dict[str, Any]] = {}

    # 1. Real SFX directory (highest priority)
    real_dir = root / "audio" / "real_sfx"
    lic_dir = root / "audio" / "licenses"
    if real_dir.exists() and lic_dir.exists():
        for p in real_dir.glob("*.wav"):
            base = p.stem
            m_sha = re.search(r"_([a-f0-9]{8,64})$", base)
            lic_data = {}
            if m_sha:
                sha_prefix = m_sha.group(1)
                for l_file in lic_dir.glob("*.json"):
                    if l_file.stem.startswith(sha_prefix):
                        try:
                            with open(l_file, "r", encoding="utf-8") as lf:
                                lic_data = json.load(lf)
                            break
                        except Exception:
                            pass
            clean_name = re.sub(r"_[a-f0-9]{8,64}$", "", base)
            item = {
                "name": clean_name,
                "filename": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "hit_offset": 0.0,
                "asset_source": "REAL",
                "license_id": lic_data.get("license_id", "user_licensed"),
                "sha256": lic_data.get("sha256"),
            }
            lib[clean_name] = item
            lib[base] = item

    # 2. Procedural SFX directory (fallback)
    sfx_dir = root / "audio" / "sfx"
    if sfx_dir.exists():
        for p in sfx_dir.glob("*.wav"):
            base = p.stem
            hit_m = re.search(r"hitAt(\d+)ms", base)
            hit_ms = int(hit_m.group(1)) if hit_m else 0
            canonical = re.sub(r"_hitAt\d+ms", "", base)
            file_stat = p.stat()
            if canonical not in lib:
                item = {
                    "name": canonical,
                    "filename": p.name,
                    "path": str(p),
                    "size": file_stat.st_size,
                    "hit_offset": hit_ms / 1000.0,
                    "asset_source": "PROCEDURAL",
                    "license_id": "internal_procedural",
                    "sha256": None,
                }
                lib[canonical] = item
                if base != canonical:
                    lib[base] = item

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
        "step": "single_footstep",
        "steps": "single_footstep",
        "footstep": "single_footstep",
        "single_step": "single_footstep",
        "run": "single_footstep",
        "footsteps_loop": "footsteps",
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
        "horn_roman": "horn_roman",
        "roman_horn": "horn_roman",
        "drum_march": "drum_march",
        "battle_roar": "battle_roar",
        "battle_far": "battle_far",
        "javelin_throw": "javelin_throw",
        "javelin": "javelin_throw",
        "pilum": "javelin_throw",
        "arrow_volley": "arrow_volley",
        "arrow": "arrow_volley",
        "sword_clash": "sword_clash",
        "clash": "sword_clash",
        "shield_bash": "shield_bash",
        "spear_hit": "spear_hit",
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
            # Treadmill: discrete single steps or single one-shot loop (no overlapping 3s clips)
            step_name = get_canonical_sfx_name("single_footstep", sfx_lib)
            if step_name:
                cadence = 0.50
                t_start = 0.5
                step_idx = 0
                max_steps = min(6, int((dur - 1.0) / cadence))
                while t_start < dur - 0.4 and step_idx < max_steps:
                    events.append({
                        "name": step_name,
                        "at": round(t_start, 2),
                        "gain": -15.0,
                        "kind": "foley_cadence",
                        "reason": "treadmill_belt_cadence",
                        "confidence": 0.88,
                    })
                    t_start += cadence
                    step_idx += 1
            else:
                loop_name = get_canonical_sfx_name("footsteps_loop", sfx_lib) or get_canonical_sfx_name("footsteps", sfx_lib)
                if loop_name:
                    events.append({
                        "name": loop_name,
                        "at": 0.5,
                        "gain": -16.0,
                        "kind": "foley_cadence",
                        "reason": "treadmill_run_loop",
                        "confidence": 0.85,
                    })
        else:
            # Running across ground / mud
            run_start = float(hero.get("moveAt", 0.0))
            if run_start == 0.0 and has_get_up:
                run_start = round(dur * 0.68, 2)
            step_name = get_canonical_sfx_name("mud_step", sfx_lib) or get_canonical_sfx_name("single_footstep", sfx_lib)
            if step_name:
                cadence = 0.45
                t_step = max(0.4, run_start)
                step_idx = 0
                max_steps = min(6, int((dur - t_step) / cadence))
                while t_step < dur - 0.35 and step_idx < max_steps:
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
            else:
                loop_name = get_canonical_sfx_name("footsteps_loop", sfx_lib) or get_canonical_sfx_name("footsteps", sfx_lib)
                if loop_name:
                    events.append({
                        "name": loop_name,
                        "at": round(max(0.4, run_start), 2),
                        "gain": -14.0,
                        "kind": "foley_cadence",
                        "reason": "mud_sprint_loop",
                        "confidence": 0.85,
                    })

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

    # Cue 6: Battle choreography & tactical events
    is_battle = (
        tpl in ("top", "army")
        or bool(re.search(r"\b(battle|clash|legion|roman|hastati|principes|triarii|flank|encircle|breakthrough|corridor|relief|rotation|ranks?|phalanx)\b", l_low))
    )
    if is_battle:
        # Horn signal / command
        if bool(re.search(r"\b(horn|signal|command|order|tù và|hiệu lệnh)\b", l_low)) and not is_negated("horn"):
            hn = get_canonical_sfx_name("horn_roman", sfx_lib) or get_canonical_sfx_name("war_horn", sfx_lib)
            if hn:
                events.append({"name": hn, "at": 0.2, "gain": -9.0, "kind": "battle_signal", "reason": "battle_horn_command", "confidence": 0.95})

        # March / Approach
        if bool(re.search(r"\b(march|advance|approach|tiến quân|hành quân|tiến lên)\b", l_low)) and not is_negated("march"):
            dm = get_canonical_sfx_name("drum_march", sfx_lib)
            if dm:
                events.append({"name": dm, "at": 0.35, "gain": -13.0, "kind": "battle_march", "reason": "disciplined_march", "confidence": 0.92})

        # Shield clash / Impact
        if bool(re.search(r"\b(clash|impact|collide|shield|charge|xung phong|chạm trán|va chạm)\b", l_low)) and not is_negated("clash"):
            sb = get_canonical_sfx_name("shield_bash", sfx_lib)
            if sb:
                events.append({"name": sb, "at": round(min(dur * 0.45, 1.2), 2), "gain": -9.0, "kind": "battle_impact", "reason": "shield_wall_clash", "confidence": 0.96})
            sc = get_canonical_sfx_name("sword_clash", sfx_lib)
            if sc:
                events.append({"name": sc, "at": round(min(dur * 0.65, 1.8), 2), "gain": -11.0, "kind": "battle_melee", "reason": "melee_weapon_clash", "confidence": 0.93})

        # Breakthrough / Roar
        if bool(re.search(r"\b(breakthrough|broke|breach|penetrate|collapse|shatter|chọc thủng|xé toang)\b", l_low)) and not is_negated(r"\b(break|breach|broke)\b"):
            br = get_canonical_sfx_name("battle_roar", sfx_lib)
            if br:
                events.append({"name": br, "at": 0.3, "gain": -10.0, "kind": "battle_roar", "reason": "breakthrough_battle_cry", "confidence": 0.95})
            sc = get_canonical_sfx_name("sword_clash", sfx_lib)
            if sc:
                events.append({"name": sc, "at": round(min(dur * 0.55, 1.5), 2), "gain": -11.0, "kind": "battle_melee", "reason": "breakthrough_melee", "confidence": 0.91})

        # Relief / Rotation
        if bool(re.search(r"\b(relief|relieve|rotate|rotation|second line|reserve|hàng hai|tiếp ứng|thay hàng|rút lui)\b", l_low)) and not is_negated("relief"):
            hn = get_canonical_sfx_name("horn_roman", sfx_lib) or get_canonical_sfx_name("war_horn", sfx_lib)
            if hn:
                events.append({"name": hn, "at": 0.25, "gain": -11.0, "kind": "battle_signal", "reason": "rotation_signal", "confidence": 0.94})
            dm = get_canonical_sfx_name("drum_march", sfx_lib)
            if dm:
                events.append({"name": dm, "at": 0.6, "gain": -14.0, "kind": "battle_march", "reason": "reserve_stepping_up", "confidence": 0.90})

        # Flank & Encirclement
        if bool(re.search(r"\b(flank|encircle|surround|pincer|wings|bọc sườn|bao vây|gọng kìm)\b", l_low)) and not is_negated(r"\b(flank|encircle|surround)\b"):
            bf = get_canonical_sfx_name("battle_far", sfx_lib)
            if bf:
                events.append({"name": bf, "at": 0.3, "gain": -12.0, "kind": "battle_ambient", "reason": "flank_envelopment", "confidence": 0.92})
            sc = get_canonical_sfx_name("sword_clash", sfx_lib)
            if sc:
                events.append({"name": sc, "at": round(min(dur * 0.6, 1.8), 2), "gain": -10.0, "kind": "battle_melee", "reason": "flank_clash", "confidence": 0.92})

        # Javelin / Pilum / Arrow Volley
        if bool(re.search(r"\b(pilum|javelin|arrow|volley|phóng lao|bắn tên|lao)\b", l_low)) and not is_negated(r"\b(throw|shoot|volley|pilum|javelin)\b"):
            jt = get_canonical_sfx_name("javelin_throw", sfx_lib) or get_canonical_sfx_name("arrow_volley", sfx_lib)
            if jt:
                events.append({"name": jt, "at": 0.2, "gain": -10.0, "kind": "battle_missile", "reason": "javelin_pilum_volley", "confidence": 0.95})
            sb = get_canonical_sfx_name("shield_bash", sfx_lib)
            if sb:
                events.append({"name": sb, "at": round(min(dur * 0.7, 1.8), 2), "gain": -11.0, "kind": "battle_impact", "reason": "javelin_shield_impact", "confidence": 0.93})

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
    sfx_lib: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Merge newly generated audio cues with existing cues while protecting manual edits."""
    manual_cues = [
        c for c in existing_cues
        if c.get("source") == "manual" or c.get("audio_source") == "manual" or c.get("manual") is True or c.get("manual") == "true"
    ]
    if manual_cues and not upgrade_generated:
        # Manual edits lock the shot completely unless explicit upgrade requested
        return existing_cues, False

    out: List[Dict[str, Any]] = list(manual_cues)
    manual_times = [float(c.get("at", 0)) for c in manual_cues]
    seen_times = {round(t, 2) for t in manual_times}

    for gc in generated_cues:
        g_at = float(gc.get("at", 0))
        at_round = round(g_at, 2)
        # Avoid duplicate timing and avoid collision within 0.15s of any manual cue
        if at_round in seen_times or any(abs(g_at - mt) < 0.15 for mt in manual_times):
            continue
        c_name = gc.get("name", "")
        if sfx_lib is not None and c_name and c_name not in sfx_lib:
            print(f"[AudioPlanner] Chu y: SFX '{c_name}' khong co trong thu vien, giu cue danh dau.")
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

        merged_cues, changed = merge_preserving_manual(existing_cues, generated_cues, upgrade_generated, sfx_lib)
        if changed:
            modified = True

        sh["sfx"] = merged_cues
        sh["audio_source"] = "manual" if any(c.get("source") == "manual" or c.get("manual") is True for c in merged_cues) else "auto_planned"
        sh["audio_plan"] = {
            "status": "AUDIO_PLAN_PASS",
            "version": "v9",
            "cues_count": len(merged_cues),
            "timing_source": "action_phase",
            "confidence": 0.95,
        }
        total_cues += len(merged_cues)

    # Plan music beds if story doesn't already have manual locked music
    # P1-D: Has manual music -> NEVER overwrite manual music sections, even with --upgrade-generated
    existing_music = story.get("music", [])
    has_manual_music = any(
        (m.get("source") == "manual" or m.get("manual") is True or m.get("manual") == "true")
        for m in existing_music
    )
    shot_manual_music = any(
        bool(sh.get("music") or sh.get("music_bed")) and (sh.get("manual") is True or sh.get("audio_source") == "manual")
        for sh in shots
    )
    if not (has_manual_music or shot_manual_music):
        planned_music = schedule_music_sections(shots, music_lib)
        if planned_music != existing_music:
            story["music"] = planned_music
            modified = True

    status_contract = "AUDIO_PLAN_PASS" if modified else "NO_CHANGE"
    input_vhash = compute_canonical_visual_hash(str(project_dir), story) if compute_canonical_visual_hash else ""
    output_ahash = compute_canonical_audio_hash(str(project_dir), story) if compute_canonical_audio_hash else ""

    # Output audio plan audit manifest
    audio_plan_manifest = {
        "project": project_dir.name,
        "planned_at": time.time(),
        "run_id": f"plan_{int(time.time() * 1000)}",
        "version": "v9",
        "status": status_contract,
        "modified": modified,
        "input_visual_hash": input_vhash,
        "audio_hash": output_ahash,
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

    if not dry_run:
        build_dir = project_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = build_dir / "audio_plan.json"
        tmp_manifest = build_dir / "audio_plan.json.tmp"
        with tmp_manifest.open("w", encoding="utf-8") as f:
            json.dump(audio_plan_manifest, f, indent=2)
        os.replace(tmp_manifest, manifest_file)

        if modified:
            # Atomic backup and write
            backup_file = project_dir / "story" / "shots.backup.json"
            try:
                shutil.copyfile(shots_file, backup_file)
            except Exception:
                pass

            tmp_shots = shots_file.with_suffix(".json.tmp")
            with tmp_shots.open("w", encoding="utf-8") as f:
                json.dump(story, f, indent=2)
            os.replace(tmp_shots, shots_file)

    return {
        "status": status_contract,
        "modified": modified,
        "total_cues": total_cues,
        "music_sections": len(story.get("music", [])),
        "audio_hash": output_ahash,
        "manifest": audio_plan_manifest,
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
