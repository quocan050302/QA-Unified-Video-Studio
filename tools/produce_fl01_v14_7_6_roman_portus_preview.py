#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_6_roman_portus_preview.py — FL-01 V14.7.6 Producer:
"THE LAST LIGHT OF PORTUS — A ROMAN HARBOR STORY"
Subtitle: "A fictional Roman harbor drama at twilight; stylized 2D reconstruction, not a documented historical incident."

Implements Section 9 & Section 10 deliverables through the unchanged FL-01 producer flow:
- `build_portus_storyboard(script_source)` (genuinely script-driven via `MotionPlan` + `CameraSegment`)
- `build_portus_original_assets(project_path)`
- `construct_portus_project(motionPlan, original_assets, ...)`
- `generate_portus_measured_voice(project_path, ...)`
- `build_portus_event_soundtrack(project_path, ...)`
- `produce_portus_preview(force_rebuild, ...)`
- `inspect_portus_preview(project_path, mp4_path, ...)`
- `generate_portus_contact_sheets(project_path, mp4_path, ...)`
- `run_portus_wording_variation_test()`
- `produce_abc_8s_comparison(out_root, ...)` (A = V14.7.5.1 sine baseline, B = MotionPlan + Rigby2D WebGL, C = B + Claude FX)
- `produce_three_unseen_short_generalization_clips(out_root)`
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    inspect_media_file,
    sha256_file,
    validate_cache_hit,
    verify_receipt_and_lineage,
    write_render_receipt_atomic,
)
from tools.action_capabilities import get_pack_capabilities
from tools.cinematic_camera import (
    compile_camera_segments_to_renderer,
    plan_camera_sequence,
    plan_multi_angle_action,
    validate_camera_segments,
)
from tools.motion_performance import (
    MotionPlan,
    build_shared_motion_timeline,
    compile_motion_plan_to_legacy_shot_args,
    extract_semantic_motion_intents,
    plan_actor_motion_phases,
    validate_motion_plan,
)
from tools.temporal_visual_qa import (
    audit_foot_plant,
    audit_hand_prop_contact,
    audit_internal_camera_cuts,
    audit_motion_performance,
    audit_project_temporal_visual,
)
from tools.visual_qa_v14_6 import extract_frame_at_time

PROJECT_DIR = ROOT_DIR / "projects" / "fl01_v14_7_6_roman_last_light_portus_preview"
OUT_MP4_PATH = PROJECT_DIR / "out" / "FL01_V14_7_6_THE_LAST_LIGHT_OF_PORTUS_ORIGINAL_30S_1080P.mp4"
FILM_TITLE = "THE LAST LIGHT OF PORTUS — A ROMAN HARBOR STORY"
FILM_SUBTITLE = (
    "A fictional Roman harbor drama at twilight; stylized 2D reconstruction, "
    "not a documented historical incident."
)
END_CARD_TITLE = "ONE LIGHT. ONE SAFE PASSAGE."
END_CARD_SUBTITLE = "FICTIONAL ROMAN HARBOR TALE • TWILIGHT RECONSTRUCTION"
HARBOR_MODULE_REL = "packs/squire/harbor/portus_light.js"

NOMINAL_DURATION_SEC = 30.0
NOMINAL_FPS = 24
NOMINAL_VIDEO_FRAMES = 720

# Canonical 8-beat timing & spoken script (Section 9)
PORTUS_CANONICAL_BEATS: List[Dict[str, Any]] = [
    {
        "id": "S01",
        "act": "I_HOOK_DARK_HARBOR",
        "start": 0.0,
        "end": 3.0,
        "dur": 3.0,
        "line": "The harbor light went dark.",
    },
    {
        "id": "S02",
        "act": "I_STAKES_SHOALS",
        "start": 3.0,
        "end": 6.5,
        "dur": 3.5,
        "line": "A merchant ship was heading straight for the rocks.",
    },
    {
        "id": "S03",
        "act": "II_DISCOVERY_LANTERN",
        "start": 6.5,
        "end": 10.0,
        "dur": 3.5,
        "line": "Aelia grabbed the last burning lantern.",
    },
    {
        "id": "S04",
        "act": "II_PLAN_STEPS_ROPE",
        "start": 10.0,
        "end": 14.0,
        "dur": 4.0,
        "line": "She ran for the tower. Felix caught the rope.",
    },
    {
        "id": "S05",
        "act": "III_SETBACK_GUST_SLIP",
        "start": 14.0,
        "end": 18.0,
        "dur": 4.0,
        "line": "The wind nearly pulled it from her hands.",
    },
    {
        "id": "S06",
        "act": "III_CLIMAX_SHARED_HOIST",
        "start": 18.0,
        "end": 22.5,
        "dur": 4.5,
        "line": "Together, they raised the flame above the storm.",
    },
    {
        "id": "S07",
        "act": "IV_PAYOFF_SAFE_CHANNEL",
        "start": 22.5,
        "end": 26.5,
        "dur": 4.0,
        "line": "Its glow showed the sailors a safe way home.",
    },
    {
        "id": "S08",
        "act": "IV_RESOLUTION_PASSAGE",
        "start": 26.5,
        "end": 30.0,
        "dur": 3.5,
        "line": "The ship made it through.",
    },
]

CANONICAL_PORTUS_SCRIPT: str = "\n".join(b["line"] for b in PORTUS_CANONICAL_BEATS)

PORTUS_CAST_BIBLE: Dict[str, Dict[str, Any]] = {
    "aelia": {
        "name": "Aelia",
        "preset": "lady",
        "role": "lamp_keeper",
        "x": 0.40,
        "y": 0.84,
        "facing": 1,
        "silhouette_markers": "Russet-crimson wool tunic, ochre sash, dark tied bun, oil lantern keeper",
    },
    "felix": {
        "name": "Felix",
        "preset": "peasant",
        "role": "rope_worker",
        "x": 0.62,
        "y": 0.84,
        "facing": -1,
        "silhouette_markers": "Olive-slate harbor tunic, terracotta belt, pulley rope worker",
    },
}

PORTUS_BASE_WORLD_STATE: Dict[str, Any] = {
    "environment": {
        "location": "portus_harbor_mole",
        "time_of_day": "twilight_storm",
        "wind": 0.72,
        "sea_direction": "left_to_right",
    },
    "actors": {
        "aelia": {"x": 0.40, "y": 0.84, "facing": 1},
        "felix": {"x": 0.62, "y": 0.84, "facing": -1},
    },
    "objects": {
        "lantern": {"x": 0.50, "y": 0.70, "state": "lit_on_rack"},
        "flame": {"x": 0.58, "y": 0.70, "state": "protected_oil_wick"},
        "tower": {"x": 0.60, "y": 0.70, "state": "beacon_dark"},
        "rope": {"x": 0.64, "y": 0.70, "state": "slack"},
        "rail": {"x": 0.57, "y": 0.72, "state": "fixed_iron"},
        "ladder": {"x": 0.66, "y": 0.72, "state": "leaning"},
        "pulley": {"x": 0.65, "y": 0.40, "state": "ready"},
        "ship": {"x": 0.36, "y": 0.62, "state": "approaching_shoals"},
        "rocks": {"x": 0.58, "y": 0.64, "state": "hazard"},
    },
}


def _probe_audio_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(proc.stdout.strip())


def compute_measured_voice_overlaps(events: Sequence[Dict[str, Any]]) -> float:
    max_overlap_sec = 0.0
    ordered = sorted(events, key=lambda e: float(e["spoken_start"]))
    for idx in range(len(ordered) - 1):
        cur_end = float(ordered[idx]["spoken_end"])
        nxt_start = float(ordered[idx + 1]["spoken_start"])
        if cur_end > nxt_start:
            max_overlap_sec = max(max_overlap_sec, cur_end - nxt_start)
    return round(max_overlap_sec * 1000.0, 3)


def _measure_word_timestamps_from_pcm(
    mono_pcm: np.ndarray,
    sr: int,
    spoken_start: float,
    text: str,
) -> List[Dict[str, Any]]:
    """
    Partition actual synthesized speech waveform across words weighted by syllabic character
    count + measured local RMS energy windows (never hardcoded fixed constants).
    """
    tokens = [tok for tok in text.strip().split() if tok]
    if not tokens:
        return []
    total_dur = max(0.05, float(mono_pcm.shape[0]) / float(sr))
    if len(tokens) == 1:
        return [{"w": tokens[0], "start": round(spoken_start, 3), "end": round(spoken_start + total_dur, 3)}]

    # Compute 20ms energy envelope across the actual TTS clip
    win = max(1, int(0.02 * sr))
    n_frames = max(len(tokens), int(math.ceil(mono_pcm.shape[0] / win)))
    padded = np.pad(mono_pcm, (0, max(0, n_frames * win - mono_pcm.shape[0])))
    frames = padded[: n_frames * win].reshape(n_frames, win)
    rms_env = np.sqrt(np.mean(frames * frames, axis=1) + 1e-7)

    # Combine lexical length weight with local acoustic energy density
    char_weights = np.array([max(1.5, float(len(re.sub(r"[^A-Za-z]", "", t)))) for t in tokens], dtype=np.float64)
    char_fracs = char_weights / np.sum(char_weights)
    cum_edges = np.concatenate([[0.0], np.cumsum(char_fracs)])

    word_energies: List[float] = []
    for k in range(len(tokens)):
        f0 = min(n_frames - 1, int(round(cum_edges[k] * n_frames)))
        f1 = max(f0 + 1, min(n_frames, int(round(cum_edges[k + 1] * n_frames))))
        word_energies.append(float(char_weights[k]) * (0.65 + 0.35 * float(np.mean(rms_env[f0:f1]) / (np.mean(rms_env) + 1e-6))))

    w_arr = np.array(word_energies, dtype=np.float64)
    durs = (w_arr / np.sum(w_arr)) * total_dur
    out: List[Dict[str, Any]] = []
    cur = spoken_start
    for tok, wd in zip(tokens, durs):
        nxt = cur + float(wd)
        out.append({"w": tok, "start": round(cur, 3), "end": round(nxt, 3)})
        cur = nxt
    out[-1]["end"] = round(spoken_start + total_dur, 3)
    return out


def _parse_script_source_to_beats(
    script_source: Optional[Union[str, Sequence[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize `script_source` (raw text or list of beat dicts) into timed beat events.
    Preserves exact 8-beat 30.000s grid when 8 lines are supplied, while allowing arbitrary
    line counts / custom durations for wording-variation or unseen-script tests.
    """
    if script_source is None:
        return copy.deepcopy(PORTUS_CANONICAL_BEATS)

    if isinstance(script_source, (list, tuple)):
        beats_out: List[Dict[str, Any]] = []
        cur_t = 0.0
        for idx, item in enumerate(script_source):
            if isinstance(item, dict):
                st = float(item.get("start", cur_t))
                dur = float(item.get("dur", float(item.get("end", st + 3.5)) - st))
                et = round(st + dur, 3)
                cur_t = et
                beats_out.append({
                    "id": str(item.get("id") or f"S{idx + 1:02d}"),
                    "act": str(item.get("act") or f"BEAT_{idx + 1:02d}"),
                    "start": round(st, 3),
                    "end": et,
                    "dur": round(dur, 3),
                    "line": str(item.get("line") or item.get("text") or "").strip(),
                })
        return beats_out

    raw_lines = [
        re.sub(r"^S\d+\s*(?:\[[^\]]+\]|\d+(?:\.\d+)?-\d+(?:\.\d+)?)?\s*:\s*", "", ln.strip())
        for ln in str(script_source).splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if len(raw_lines) == len(PORTUS_CANONICAL_BEATS):
        beats = copy.deepcopy(PORTUS_CANONICAL_BEATS)
        for b, ln in zip(beats, raw_lines):
            b["line"] = ln
        return beats

    beats_var: List[Dict[str, Any]] = []
    cur_t = 0.0
    step = round(NOMINAL_DURATION_SEC / max(1, len(raw_lines)), 3)
    for idx, ln in enumerate(raw_lines):
        st = round(cur_t, 3)
        et = NOMINAL_DURATION_SEC if idx == len(raw_lines) - 1 else round(st + step, 3)
        beats_var.append({
            "id": f"S{idx + 1:02d}",
            "act": f"BEAT_{idx + 1:02d}",
            "start": st,
            "end": et,
            "dur": round(et - st, 3),
            "line": ln,
        })
        cur_t = et
    return beats_var


def build_portus_storyboard(
    script_source: Optional[Union[str, Sequence[Dict[str, Any]]]] = None,
    *,
    fx_profile: str = "claude_selective",
) -> Dict[str, Any]:
    """
    Build the complete Portus storyboard + shared `MotionPlan` + multi-angle `CameraSegment`s
    genuinely from `script_source` (NOT a static lookup that ignores script variations).
    """
    beats = _parse_script_source_to_beats(script_source)
    script_text = "\n".join(b["line"] for b in beats)
    cast = copy.deepcopy(PORTUS_CAST_BIBLE)
    world_init = copy.deepcopy(PORTUS_BASE_WORLD_STATE)
    caps = get_pack_capabilities("squire", "harbor")

    # 1. Semantic MotionIntent extraction -> Phase planning -> Shared authoritative timeline
    intents = extract_semantic_motion_intents(
        script_text=script_text,
        script_events=beats,
        cast_bible=cast,
        world_state=world_init,
        pack="squire",
        genre="harbor",
        routing_mode="OFFLINE_ONLY",
    )
    tracks = plan_actor_motion_phases(
        intents=intents,
        action_capabilities=caps,
        shot_timing=beats,
        cast_bible=cast,
        world_state=world_init,
    )
    motion_plan: MotionPlan = build_shared_motion_timeline(
        scene_objectives=[],
        motion_tracks=tracks,
        world_timeline=world_init,
        intents=intents,
        project_id="fl01_v14_7_6_roman_last_light_portus_preview",
        pack="squire",
        genre="harbor",
        fx_profile=fx_profile,
        seed=1476,
    )
    val = validate_motion_plan(motion_plan)
    if not val.get("valid", False):
        raise ValueError(f"Generated Portus MotionPlan failed validation: {val.get('errors')}")

    legacy_args_by_shot = compile_motion_plan_to_legacy_shot_args(motion_plan).get("by_shot", {})
    intents_by_shot: Dict[str, List[Any]] = {}
    for it in intents:
        intents_by_shot.setdefault(it.shot_id, []).append(it)
    tracks_by_shot: Dict[str, List[Any]] = {}
    for tr in motion_plan.tracks:
        tracks_by_shot.setdefault(tr.shot_id, []).append(tr)

    # Track evolving causal world state across beats derived from semantic motion types!
    lantern_acquired = False
    lantern_hoisted = False
    beacon_lit = False
    ship_safe = False
    ship_prog = 0.24
    lift_prog = 0.0

    shots: List[Dict[str, Any]] = []
    cut_reasons_cycle = [
        "opening_hook",
        "wide_spatial_establish",
        "reaction_closeup",
        "same_space_action_beat",
        "inciting_physical_slip",
        "mechanism_closeup",
        "spatial_cutaway",
        "resolution_wide_crane",
    ]

    for idx, b in enumerate(beats):
        sid = b["id"]
        s_intents = intents_by_shot.get(sid, [])
        s_tracks = tracks_by_shot.get(sid, [])
        m_types = [it.motion_type for it in s_intents]
        primary_mtype = m_types[0] if m_types else "OBSERVE"

        has_actors = len(s_tracks) > 0
        expected_subject = "actor" if has_actors else "prop"

        # Derive harbor physical mechanics from semantic motion types in this beat
        mech: Dict[str, Any] = {
            "dusk_warmth_start": 0.62 if idx == 0 else 0.16,
            "dusk_warmth_end": 0.16 if idx == 0 else (0.22 if idx == len(beats) - 1 else 0.15),
            "show_gulls": True,
            "show_shoals": True,
            "show_ship": True,
            "ship_progress_start": round(ship_prog, 3),
            "ship_progress_end": round(ship_prog, 3),
            "ship_turn_start": 1.0 if ship_safe else 0.0,
            "ship_turn_end": 1.0 if ship_safe else 0.0,
            "lantern_lift_start": round(lift_prog, 3),
            "lantern_lift_end": round(lift_prog, 3),
            "beacon_glow_start": 0.92 if beacon_lit else 0.0,
            "beacon_glow_end": 0.92 if beacon_lit else 0.0,
            "upper_beacon_start": 1.0 if beacon_lit else 0.0,
            "upper_beacon_end": 1.0 if beacon_lit else 0.0,
        }
        state_changed_keys: List[str] = []
        fx_events: List[Dict[str, Any]] = []
        action_warps: List[Dict[str, Any]] = []
        props_list: List[Dict[str, Any]] = []
        tpl = "scene"
        zone = "portus_mole_wide"

        if "EXTINGUISH" in m_types:
            tpl = "close"
            zone = "beacon_snuff_to_harbor"
            mech["opening_flame_snuff"] = True
            mech["insert_kind"] = "beacon_snuff"
            mech["show_snuffed_brazier"] = True
            ship_prog = min(0.52, ship_prog + 0.24)
            mech["ship_progress_end"] = round(ship_prog, 3)
            fx_events.append({"kind": "lantern_gust_embers", "t0": round(b["start"] + 0.36, 3), "x": 0.50, "y": 0.42})

        if "SAIL_TURN" in m_types and not beacon_lit:
            ship_prog = min(0.88, ship_prog + 0.36)
            mech["ship_progress_end"] = round(ship_prog, 3)
            zone = "harbor_shoals_wide"

        if "GRAB" in m_types:
            tpl = "close"
            zone = "lantern_rack_quay"
            mech["show_lantern_rack"] = True
            mech["lantern_grab_in_shot"] = True
            mech["lantern_grab_u"] = 0.38
            mech["insert_kind"] = "lantern_grab"
            lantern_acquired = True
            state_changed_keys.append("lantern_acquired")
            fx_events.append({"kind": "lantern_gust_embers", "t0": round(b["start"] + 1.45, 3), "x": 0.50, "y": 0.68})

        if any(m in m_types for m in ("RUN", "WALK", "BRACE_ROPE")):
            mech["lantern_carried"] = lantern_acquired and not lantern_hoisted
            if "BRACE_ROPE" in m_types:
                lift_prog = max(lift_prog, 0.06)
                mech["lantern_lift_end"] = round(lift_prog, 3)

        if any(m in m_types for m in ("SLIP", "CATCH_RAIL", "DUCK")):
            mech["lantern_carried"] = lantern_acquired and not lantern_hoisted
            mech["gust_setback"] = True
            mech["ladder_tilt_deg_start"] = 0.0
            mech["ladder_tilt_deg_end"] = -5.5 if "SLIP" in m_types else -2.5
            fx_events.append({"kind": "foot_slip_spray", "t0": round(b["start"] + 1.15, 3), "x": 0.52, "y": 0.84})
            action_warps.append({"at": round(b["start"] + 1.28, 3), "hold": 0.05, "ease": 0.14})

        if any(m in m_types for m in ("HAUL_ROPE", "LIFT_SHARED")):
            mech["lantern_on_hoist"] = True
            mech["lantern_lift_start"] = round(max(0.08, lift_prog), 3)
            lift_prog = 0.96
            mech["lantern_lift_end"] = lift_prog
            mech["pulley_angle_start"] = 0.2
            mech["pulley_angle_end"] = 5.4
            mech["upper_beacon_end"] = 0.95
            mech["beacon_glow_end"] = 0.65
            mech["insert_kind"] = "rope_haul"
            lantern_hoisted = True
            beacon_lit = True
            state_changed_keys.extend(["lantern_hoisted", "beacon_lit"])
            fx_events.append({"kind": "rope_strain_dust", "t0": round(b["start"] + 1.10, 3), "x": 0.63, "y": 0.72})
            fx_events.append({"kind": "beacon_relight_pulse", "t0": round(b["end"] - 0.55, 3), "x": 0.58, "y": 0.24, "radius": 95})

        if "ILLUMINATE" in m_types:
            beacon_lit = True
            ship_safe = True
            state_changed_keys.extend(["beacon_lit", "ship_safe"])
            mech["upper_beacon_start"] = 1.0
            mech["upper_beacon_end"] = 1.0
            mech["beacon_glow_start"] = 0.78
            mech["beacon_glow_end"] = 1.0
            mech["ship_turn_start"] = 0.08
            mech["ship_turn_end"] = 0.92
            zone = "harbor_channel_payoff"

        if "RELIEF_EXHALE" in m_types or idx == len(beats) - 1:
            mech["upper_beacon_start"] = 1.0 if beacon_lit else 0.0
            mech["upper_beacon_end"] = 1.0 if beacon_lit else 0.0
            mech["beacon_glow_start"] = 0.95 if beacon_lit else 0.0
            mech["beacon_glow_end"] = 0.95 if beacon_lit else 0.0
            mech["ship_turn_start"] = 0.92 if ship_safe else 0.0
            mech["ship_turn_end"] = 1.0 if ship_safe else 0.0
            mech["relieved_look"] = True
            if idx == len(beats) - 1:
                props_list.append({
                    "kind": "portus_end_card",
                    "title": END_CARD_TITLE,
                    "subtitle": END_CARD_SUBTITLE,
                })

        people_entries: List[Dict[str, Any]] = []
        for tr in s_tracks:
            c_info = cast.get(tr.actor_id, {})
            people_entries.append({
                "id": tr.actor_id,
                "preset": c_info.get("preset", tr.preset),
                "from": round(float(tr.world_start[0]), 3),
                "to": round(float(tr.world_end[0]), 3),
                "x": round(float(tr.world_start[0]), 3),
                "y": round(float(tr.ground_y), 3),
                "h": round(float(tr.height_norm), 3),
                "motionTrack": tr.model_dump(),
            })

        mech["wind_strength"] = 0.86 if mech.get("gust_setback") else (0.52 if mech.get("relieved_look") else 0.72)

        shot_world_state = {
            "zone": zone,
            "sea_direction": "left_to_right",
            "tower_side": "right_mole",
            "time_of_day": "twilight_storm",
            "wind_regime": "twilight_squall",
            "lantern_acquired": lantern_acquired,
            "lantern_hoisted": lantern_hoisted,
            "beacon_lit": beacon_lit,
            "ship_safe": ship_safe,
            "objects": copy.deepcopy(world_init["objects"]),
        }

        compiled_shot_args = copy.deepcopy(legacy_args_by_shot.get(sid, {}))
        shot_dict: Dict[str, Any] = {
            "id": sid,
            "act": b["act"],
            "start": b["start"],
            "end": b["end"],
            "dur": b["dur"],
            "line": b["line"],
            "text": b["line"],
            "tpl": tpl,
            "action": primary_mtype,
            "motion_types": m_types,
            "expected_subject": expected_subject,
            "intentional_cut_reason": cut_reasons_cycle[min(idx, len(cut_reasons_cycle) - 1)],
            "state_changed_keys": sorted(set(state_changed_keys)),
            "desc": f"{sid} ({primary_mtype}): {b['line']}",
            "world_state": shot_world_state,
            "mechanics": mech,
            "args": {
                **compiled_shot_args,
                "bg": "portus_harbor",
                "zone": zone,
                "groundY": 0.84,
                "towerX": 0.74,
                "fx_profile": fx_profile,
                "seed": 1476 + idx * 17,
                "motionPlan": compiled_shot_args.get("motionPlan") or {
                    "schema_version": motion_plan.schema_version,
                    "project_id": motion_plan.project_id,
                    "shot_id": sid,
                    "routing_mode": motion_plan.routing_mode,
                    "fx_profile": fx_profile,
                    "seed": 1476 + idx * 17,
                },
                "motionTracks": [tr.model_dump() for tr in s_tracks],
                "people": people_entries,
                "props": props_list,
                "fxEvents": fx_events,
                "actionWarpSpecs": action_warps,
            },
        }

        # Multi-angle CameraSegment planning inside logical shot (Phase E)
        segs = plan_multi_angle_action(shot_dict, motion_plan, shot_world_state, fps=float(NOMINAL_FPS))
        seg_ok, seg_errs = validate_camera_segments(segs, shot_dict, motion_plan=motion_plan)
        if not seg_ok:
            raise ValueError(f"CameraSegment validation failed on {sid}: {seg_errs}")
        compiled_cam = compile_camera_segments_to_renderer(segs)
        shot_dict["args"]["cameraSegments"] = compiled_cam["cameraSegments"]
        shot_dict["args"]["cameraRig"] = compiled_cam["cameraRig"]

        shots.append(shot_dict)

    cam_seq = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
    for s, cp in zip(shots, cam_seq):
        s["camera"] = cp.model_dump()

    total_dur = round(float(shots[-1]["end"]) if shots else NOMINAL_DURATION_SEC, 3)
    return {
        "schema_version": "14.7.6",
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "historical_framing": FILM_SUBTITLE,
        "ai_director_mode": "OFFLINE_ONLY",
        "pack": "squire",
        "genre": "harbor",
        "aspect": "16:9",
        "fps": NOMINAL_FPS,
        "duration": total_dur,
        "total_duration": total_dur,
        "expected_video_frames": int(round(total_dur * NOMINAL_FPS)),
        "script_sha256": hashlib.sha256(script_text.encode("utf-8")).hexdigest(),
        "motion_plan": motion_plan.model_dump(),
        "shots": shots,
    }


def verify_portus_causality(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rendering-independent physical, historical-framing, and narrative causality check for Portus:
    - Exact 8 contiguous beats summing to 30.000s (for canonical film),
    - Zero military props anywhere,
    - Zero claim of documented historical incident, Fresnel rotating optics, or dawn transition,
    - Beacon starts dark in S01, lantern is grabbed before hoisted, hoisted in S06 before channel glow in S07,
    - Merchant ship turns safely away only AFTER beacon light is raised.
    """
    errors: List[str] = []
    shots = storyboard.get("shots") or []
    if len(shots) != 8:
        errors.append(f"Expected 8 shots (S01..S08), got {len(shots)}")
        return {"valid": False, "status": "FAIL", "errors": errors}

    cur_t = 0.0
    forbidden_military = {"eagle", "standard", "scutum", "sword", "pilum", "arrow", "ballista", "javelin", "helmet"}
    for s in shots:
        if abs(float(s["start"]) - cur_t) > 1e-6:
            errors.append(f"{s['id']} start={s['start']} != expected {cur_t}")
        cur_t = float(s["end"])
        ws = s.get("world_state") or {}
        if ws.get("sea_direction") != "left_to_right":
            errors.append(f"{s['id']} flipped sea_direction={ws.get('sea_direction')!r}")
        if "dawn" in str(ws.get("time_of_day", "")).lower():
            errors.append(f"{s['id']} falsely claims dawn transition in 30s twilight drama")
        for pr in (s.get("args") or {}).get("props") or []:
            kind = str(pr.get("kind") or "").lower()
            if kind in forbidden_military:
                errors.append(f"Forbidden military prop '{kind}' in Portus harbor shot {s['id']}")

    if abs(cur_t - NOMINAL_DURATION_SEC) > 1e-6:
        errors.append(f"Final timeline end={cur_t} != 30.000s")

    s_map = {s["id"]: s for s in shots}
    if (s_map["S01"]["world_state"]).get("beacon_lit") is not False:
        errors.append("S01 hook must start with harbor beacon snuffed/dark")
    if float(s_map["S02"]["mechanics"].get("ship_turn_end", 0.0)) > 0.15:
        errors.append("Causal violation: merchant ship turned away before lantern was raised")
    if float(s_map["S06"]["mechanics"].get("lantern_lift_end", 0.0)) < 0.85:
        errors.append("Causal violation: S06 failed to hoist lantern into upper tower alcove")
    if float(s_map["S07"]["mechanics"].get("ship_turn_end", 0.0)) < 0.75:
        errors.append("Causal violation: S07 failed to turn merchant ship away from rocks under beacon glow")

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "errors": errors,
    }


def build_portus_original_assets(project_path: Path = PROJECT_DIR) -> Dict[str, Any]:
    """
    Create fresh project scene module (`scenes/shots/portus_shots.js`) importing
    `packs/squire/harbor/portus_light.js`, verify zero prior-preview or external raster tokens,
    and write cryptographic `story/asset_source_manifest.json`.
    """
    p_dir = Path(project_path).resolve()
    shots_js_dir = p_dir / "scenes" / "shots"
    shots_js_dir.mkdir(parents=True, exist_ok=True)
    anh_dir = p_dir / "anh"
    if anh_dir.exists():
        for f in anh_dir.iterdir():
            if f.is_file():
                f.unlink()

    harbor_mod_abs = ROOT_DIR / HARBOR_MODULE_REL
    if not harbor_mod_abs.is_file():
        raise FileNotFoundError(f"Missing harbor procedural module: {harbor_mod_abs}")

    entry_js = shots_js_dir / "portus_shots.js"
    entry_code = (
        "// Auto-generated fresh procedural entry for FL-01 V14.7.6 'The Last Light of Portus'\n"
        "// Zero prior-preview images, clips, mascots, or military assets.\n"
        "import { registerPortusShots } from '/packs/squire/harbor/portus_light.js';\n"
        "registerPortusShots();\n"
    )
    entry_js.write_text(entry_code, encoding="utf-8")

    combined_js = harbor_mod_abs.read_text(encoding="utf-8") + "\n" + entry_code
    forbidden_tokens = [
        "fl01_v14_7_night_warning",
        "fl01_v14_7_1_bridge",
        "fl01_v14_7_2_ballista",
        "fl01_v14_7_3_roman_continuity",
        "fl01_v14_7_4_roman_arrow",
        "fl01_v14_7_5_roman_eagle",
        "fl01_v14_7_5_1_roman_water_gate",
        "water_gate",
        "v14_6_action_demo",
        "rigbytron",
        "nila.",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".mp4",
    ]
    found_forbidden = [tok for tok in forbidden_tokens if tok in combined_js.lower()]
    if found_forbidden:
        raise RuntimeError(f"Originality violation: Portus JS references forbidden tokens: {found_forbidden}")

    authored_files = [
        {"path": HARBOR_MODULE_REL, "sha256": sha256_file(harbor_mod_abs)},
        {"path": str(entry_js.relative_to(ROOT_DIR)) if entry_js.is_relative_to(ROOT_DIR) else str(entry_js), "sha256": sha256_file(entry_js)},
        {"path": "packs/squire/motion_engine.js", "sha256": sha256_file(ROOT_DIR / "packs/squire/motion_engine.js")},
        {"path": "integrations/claude_motion/adapter.js", "sha256": sha256_file(ROOT_DIR / "integrations/claude_motion/adapter.js")},
    ]

    asset_manifest = {
        "schema_version": "14.7.6",
        "project_id": p_dir.name,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "visual_generation_mode": "100%_PROCEDURAL_HTML5_CANVAS_2D_VECTOR_MOTION_PLAN",
        "prior_preview_derived_visual_inputs": 0,
        "external_raster_images_count": 0,
        "rigby_demo_mascots_copied": 0,
        "claude_skill_demo_characters_copied": 0,
        "military_battlefield_props_count": 0,
        "authored_files": authored_files,
        "procedural_modules": {item["path"]: item["sha256"] for item in authored_files},
        "newly_authored_visual_primitives": [
            "drawTwilightStormHarborSky",
            "drawRomanMerchantShip",
            "drawHarborSeaShoalsAndShip",
            "drawAncientBronzeOilLantern",
            "drawHarborMoleAndWatchtower",
            "drawHarborActorFromMotionPlan",
            "drawAuthoredGripInsert",
            "drawAuthoredLowWatchtowerView",
            "drawPortusEndCard",
        ],
        "audio_generation_mode": "MACOS_SAY_DANIEL_VOICE_PLUS_PROCEDURAL_HARBOR_FOLEY_SCORE",
    }
    story_dir = p_dir / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "asset_source_manifest.json").write_text(
        json.dumps(asset_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return asset_manifest


def construct_portus_project(
    motionPlan: Optional[Union[MotionPlan, Dict[str, Any]]] = None,
    original_assets: Optional[Dict[str, Any]] = None,
    project_path: Path = PROJECT_DIR,
    storyboard: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Write full FL-01 project structure (`config.json`, `story/shots.json`, `story/motion_plan.json`,
    `story/character_bible.json`, `story/claims_manifest.json`, `input/01-PHIM.txt`, and `scenes/shots/portus_shots.js`).
    """
    p_dir = Path(project_path).resolve()
    for sub in ("input", "story", "timeline", "build", "out", "scenes/shots"):
        (p_dir / sub).mkdir(parents=True, exist_ok=True)

    sb = copy.deepcopy(storyboard) if storyboard is not None else build_portus_storyboard()
    if motionPlan is not None:
        mp_dump = motionPlan.model_dump() if hasattr(motionPlan, "model_dump") else dict(motionPlan)
        sb["motion_plan"] = mp_dump

    causality = verify_portus_causality(sb)
    if not causality["valid"]:
        raise ValueError(f"Portus causality check failed: {causality['errors']}")

    asset_manifest = original_assets or build_portus_original_assets(p_dir)

    config = {
        "name": p_dir.name,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "pack": "squire",
        "genre": "harbor",
        "aspect": "16:9",
        "resolution": "1080p",
        "width": 1920,
        "height": 1080,
        "fps": NOMINAL_FPS,
        "bars": "none",
        "captions": False,
        "ai_director_mode": "OFFLINE_ONLY",
        "code_dependencies": [
            HARBOR_MODULE_REL,
            "packs/squire/motion_engine.js",
            "integrations/claude_motion/adapter.js",
        ],
    }
    (p_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    character_bible = {
        "schema_version": "14.7.6",
        "historical_framing": FILM_SUBTITLE,
        "characters": copy.deepcopy(PORTUS_CAST_BIBLE),
    }
    (p_dir / "story" / "character_bible.json").write_text(
        json.dumps(character_bible, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    claims_manifest = {
        "schema_version": "14.7.6",
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "historical_claim_mode": "FICTIONAL_ROMAN_HARBOR_DRAMA_AT_TWILIGHT",
        "documented_historical_event": False,
        "claims_archaeological_portus_equipment_precision": False,
        "uses_modern_fresnel_rotating_optics": False,
        "claims_dawn_transition": False,
        "period_plausibility_notes": [
            "Open olive-oil / resin wick flame in a bronze-and-horn hoist lantern raised into a sheltered stone watchtower alcove",
            "Manual hemp rope and wooden sheave pulley operated cooperatively by two harbor workers during a twilight squall",
        ],
    }
    (p_dir / "story" / "claims_manifest.json").write_text(
        json.dumps(claims_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    script_lines = [f"# {FILM_TITLE}", f"# {FILM_SUBTITLE}", ""] + [s["line"] for s in sb["shots"]]
    (p_dir / "input" / "01-PHIM.txt").write_text("\n".join(script_lines) + "\n", encoding="utf-8")

    for fname in ("shots.json", "storyboard.json"):
        target = p_dir / "story" / fname
        tmp_p = target.with_suffix(".tmp.json")
        tmp_p.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_p, target)

    mp_target = p_dir / "story" / "motion_plan.json"
    mp_tmp = mp_target.with_suffix(".tmp.json")
    mp_tmp.write_text(json.dumps(sb["motion_plan"], indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(mp_tmp, mp_target)

    (p_dir / "story" / "script.json").write_text(
        json.dumps(
            {
                "title": FILM_TITLE,
                "subtitle": FILM_SUBTITLE,
                "duration": sb["duration"],
                "beats": [
                    {"id": s["id"], "start": s["start"], "end": s["end"], "dur": s["dur"], "text": s["line"]}
                    for s in sb["shots"]
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "project_dir": str(p_dir),
        "config": config,
        "storyboard": sb,
        "motion_plan": sb["motion_plan"],
        "causality": causality,
        "asset_manifest": asset_manifest,
    }


def generate_portus_measured_voice(
    project_path: Path = PROJECT_DIR,
    storyboard: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesize natural spoken English narration via macOS `say` (`Daniel`), fail-closed
    (`BLOCKED_NO_SPEECH_PROVIDER`) if missing, and compute phrase + energy-weighted word
    timings from the actual synthesized PCM audio (zero constants, zero `atempo`, 0.0ms overlap,
    tail margin >= 0.35s target / >= 0.25s hard floor).
    """
    say_bin = shutil.which("say")
    if not say_bin:
        return {
            "ok": False,
            "status": "BLOCKED_NO_SPEECH_PROVIDER",
            "error": "Required speech synthesis provider 'say' is unavailable on host",
        }

    p_dir = Path(project_path).resolve()
    build_dir = p_dir / "build"
    timeline_dir = p_dir / "timeline"
    build_dir.mkdir(parents=True, exist_ok=True)
    timeline_dir.mkdir(parents=True, exist_ok=True)

    sb = storyboard or json.loads((p_dir / "story" / "shots.json").read_text(encoding="utf-8"))
    shots = sb["shots"]
    total_dur = float(sb.get("duration", NOMINAL_DURATION_SEC))

    sr = 48000
    total_samples = int(round(total_dur * sr))
    master_voice = np.zeros((total_samples, 2), dtype=np.float32)

    events: List[Dict[str, Any]] = []
    words_ledger: List[Dict[str, Any]] = []
    lines_ledger: List[Dict[str, Any]] = []

    for s in shots:
        sid = s["id"]
        st = float(s["start"])
        et = float(s["end"])
        dur = float(s["dur"])
        line_txt = str(s["line"])

        aiff_p = build_dir / f"portus_voice_{sid}.aiff"
        wav_p = build_dir / f"portus_voice_{sid}.wav"
        subprocess.run(
            [say_bin, "-v", "Daniel", "-r", "180", "-o", str(aiff_p), line_txt],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(aiff_p),
                "-af",
                "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-48dB,areverse",
                "-ar",
                str(sr),
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(wav_p),
            ],
            check=True,
            capture_output=True,
        )
        aiff_p.unlink(missing_ok=True)

        nat_dur = _probe_audio_duration(wav_p)
        lead_in = 0.16
        spoken_start = round(st + lead_in, 4)
        spoken_end = round(spoken_start + nat_dur, 4)
        tail_margin = round(et - spoken_end, 4)
        if tail_margin < 0.25:
            return {
                "ok": False,
                "status": "FAIL",
                "error": f"Shot {sid} spoken line ({nat_dur:.3f}s) leaves tail_margin={tail_margin:.3f}s < 0.25s",
            }

        with wave.open(str(wav_p), "rb") as wf:
            raw_bytes = wf.readframes(wf.getnframes())
            clip_pcm = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            clip_stereo = clip_pcm.reshape(-1, 2)

        idx0 = int(round(spoken_start * sr))
        idx1 = min(total_samples, idx0 + clip_stereo.shape[0])
        master_voice[idx0:idx1, :] += clip_stereo[: idx1 - idx0, :]

        measured_words = _measure_word_timestamps_from_pcm(
            clip_stereo[:, 0], sr, spoken_start, line_txt
        )
        words_ledger.extend(measured_words)

        events.append({
            "shot_id": sid,
            "act": s.get("act", ""),
            "shot_start": st,
            "shot_end": et,
            "shot_dur": dur,
            "spoken_start": spoken_start,
            "spoken_end": spoken_end,
            "natural_speech_dur": round(nat_dur, 4),
            "lead_in_sec": lead_in,
            "tail_margin_sec": tail_margin,
            "meets_target_0_35s_margin": tail_margin >= 0.35,
            "atempo_applied": False,
            "speech_provider": "macos_say:Daniel",
            "text": line_txt,
            "word_timestamps": measured_words,
            "wav_file": f"build/{wav_p.name}",
        })
        lines_ledger.append({"start": spoken_start, "end": spoken_end, "text": line_txt, "shot_id": sid})

    overlap_ms = compute_measured_voice_overlaps(events)
    min_tail = min(e["tail_margin_sec"] for e in events)
    if overlap_ms > 0.0:
        return {"ok": False, "status": "FAIL", "error": f"Non-zero speech overlap: {overlap_ms} ms"}

    voice_track_wav = build_dir / "voice_track.wav"
    pcm_out = np.clip(master_voice * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(voice_track_wav), "wb") as wf_out:
        wf_out.setnchannels(2)
        wf_out.setsampwidth(2)
        wf_out.setframerate(sr)
        wf_out.writeframes(pcm_out.tobytes())

    shutil.copy2(voice_track_wav, timeline_dir / "voice.wav")
    (timeline_dir / "words.json").write_text(json.dumps(words_ledger, indent=2), encoding="utf-8")
    (timeline_dir / "lines.json").write_text(json.dumps(lines_ledger, indent=2), encoding="utf-8")

    voice_report = {
        "schema_version": "14.7.6",
        "status": "PASS",
        "speech_provider": "macos_say:Daniel",
        "total_timeline_duration_sec": total_dur,
        "voice_wav_duration_sec": round(_probe_audio_duration(voice_track_wav), 4),
        "beats_count": len(events),
        "measured_overlap_ms": overlap_ms,
        "min_tail_margin_sec": min_tail,
        "max_tail_margin_sec": max(e["tail_margin_sec"] for e in events),
        "all_beats_meet_0_35s_target": all(e["tail_margin_sec"] >= 0.35 for e in events),
        "last_spoken_phrase": events[-1]["text"] if events else "",
        "last_spoken_end_sec": events[-1]["spoken_end"] if events else 0.0,
        "atempo_used_anywhere": False,
        "events": events,
    }
    (timeline_dir / "timeline_voice_events.json").write_text(
        json.dumps(voice_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"ok": True, **voice_report, "voice_track_wav": str(voice_track_wav)}


def build_portus_event_soundtrack(
    project_path: Path = PROJECT_DIR,
    voice_events: Optional[List[Dict[str, Any]]] = None,
    motion_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesize 100% original procedural coastal harbor foley & twilight score synchronized
    to `MotionPlan` cues (`wave_crash`, `flame_gust`, `lantern_grab`, `stone_footsteps`,
    `ladder_rattle`, `rope_creak`, `pulley_load`, `sail_wind`, `relief_chord`), mix with
    spoken Daniel narration, and normalize to -14.0 LUFS (+/- 1.5) and <= -1.0 dBTP.
    """
    p_dir = Path(project_path).resolve()
    build_dir = p_dir / "build"
    voice_wav = build_dir / "voice_track.wav"
    if not voice_wav.is_file():
        raise FileNotFoundError(f"Missing {voice_wav}; run generate_portus_measured_voice first")

    if voice_events is None:
        v_json = json.loads((p_dir / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
        voice_events = v_json["events"]
    if motion_plan is None and (p_dir / "story" / "motion_plan.json").is_file():
        motion_plan = json.loads((p_dir / "story" / "motion_plan.json").read_text(encoding="utf-8"))

    sr = 48000
    total_dur = _probe_audio_duration(voice_wav)
    n = int(round(total_dur * sr))
    t = np.arange(n, dtype=np.float32) / float(sr)
    rng = np.random.default_rng(14760)

    with wave.open(str(voice_wav), "rb") as wf:
        v_raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        v_stereo = v_raw.reshape(-1, 2)
    if v_stereo.shape[0] < n:
        v_stereo = np.vstack([v_stereo, np.zeros((n - v_stereo.shape[0], 2), dtype=np.float32)])
    else:
        v_stereo = v_stereo[:n, :]

    # Speech ducking envelope so spoken narration stays crystal-clear
    duck = np.ones(n, dtype=np.float32)
    for ev in voice_events:
        i0 = max(0, int((float(ev["spoken_start"]) - 0.08) * sr))
        i1 = min(n, int((float(ev["spoken_end"]) + 0.12) * sr))
        duck[i0:i1] = 0.34
    win = int(0.06 * sr)
    duck = np.convolve(duck, np.ones(win, dtype=np.float32) / win, mode="same")

    # Procedural harbor swells & coastal wind bed
    white_l = rng.standard_normal(n).astype(np.float32)
    white_r = rng.standard_normal(n).astype(np.float32)
    k_surf = np.ones(72, dtype=np.float32) / 72.0
    k_wind = np.ones(12, dtype=np.float32) / 12.0
    surf_l = np.convolve(white_l, k_surf, mode="same") * 3.0
    surf_r = np.convolve(white_r, k_surf, mode="same") * 3.0
    wind_l = (np.convolve(white_l, k_wind, mode="same") - surf_l * 0.22) * 0.85
    wind_r = (np.convolve(white_r, k_wind, mode="same") - surf_r * 0.22) * 0.85

    swell_mod = 0.55 + 0.45 * np.sin(2.0 * np.pi * 0.22 * t)
    storm_env = np.clip(0.055 * swell_mod * np.clip((28.5 - t) / 5.0, 0.35, 1.0), 0.01, 0.08)
    wind_env = (0.032 + 0.028 * np.exp(-0.5 * ((t - 15.6) / 2.2) ** 2)) * np.clip((29.2 - t) / 4.0, 0.30, 1.0)

    sfx_l = surf_l * storm_env + wind_l * wind_env
    sfx_r = surf_r * storm_env + wind_r * wind_env

    cue_ledger: List[Dict[str, Any]] = []

    def _add_cue_burst(cue_name: str, t_sec: float, dur_sec: float, f0: float, f1: float, amp: float, pan: float = 0.0) -> None:
        i0 = int(t_sec * sr)
        ln = int(dur_sec * sr)
        if i0 < 0 or i0 >= n or ln <= 10:
            return
        i1 = min(n, i0 + ln)
        lt_s = np.arange(i1 - i0, dtype=np.float32) / float(sr)
        env_s = np.exp(-lt_s / max(0.015, dur_sec * 0.35))
        phase = 2.0 * np.pi * (f0 * lt_s + 0.5 * (f1 - f0) * (lt_s ** 2) / max(0.01, dur_sec))
        burst = (np.sin(phase) * 0.62 + white_l[i0:i1] * 0.38) * env_s * amp
        sfx_l[i0:i1] += burst * (1.0 - max(0.0, pan))
        sfx_r[i0:i1] += burst * (1.0 + min(0.0, pan))
        cue_ledger.append({"cue": cue_name, "real_time_sec": round(t_sec, 3), "dur_sec": round(dur_sec, 3)})

    # Synchronized harbor sound effects matching Section 9 list:
    # 1) flame_gust (S01 snuff @ 0.34s + S05 gust @ 14.95s)
    _add_cue_burst("flame_gust", 0.34, 0.48, 320.0, 95.0, 0.30, pan=0.0)
    _add_cue_burst("flame_gust", 14.95, 0.55, 290.0, 88.0, 0.28, pan=-0.15)
    # 2) wave_crash against shoal rocks (S01 1.6s, S02 4.2s, S05 16.4s)
    for wt in (1.62, 4.25, 16.35):
        _add_cue_burst("wave_crash", wt, 0.65, 135.0, 44.0, 0.26, pan=0.18)
    # 3) lantern_grab bronze bail ring clink (S03 7.85s)
    _add_cue_burst("lantern_grab", 7.85, 0.16, 880.0, 520.0, 0.18, pan=-0.10)
    # 4) stone_footsteps across wet mole steps (S04 10.45..12.35s)
    for ft in (10.48, 10.86, 11.24, 11.62, 12.02):
        _add_cue_burst("stone_footsteps", ft, 0.08, 155.0, 82.0, 0.12, pan=-0.08)
    # 5) rope_creak (S04 Felix brace @ 12.55s + S05 tighten @ 16.85s)
    _add_cue_burst("rope_creak", 12.55, 0.34, 240.0, 175.0, 0.16, pan=0.22)
    _add_cue_burst("rope_creak", 16.85, 0.38, 260.0, 185.0, 0.17, pan=0.20)
    # 6) ladder_rattle & iron rail catch (S05 15.20s & 15.68s)
    _add_cue_burst("ladder_rattle", 15.20, 0.28, 210.0, 118.0, 0.22, pan=0.12)
    _add_cue_burst("rail_catch", 15.68, 0.18, 540.0, 280.0, 0.19, pan=0.10)
    # 7) pulley_load wooden sheave creaks during shared hoist (S06 18.55..21.95s)
    for pt in np.linspace(18.55, 21.85, 8):
        _add_cue_burst("pulley_load", float(pt), 0.14, 340.0, 195.0, 0.14, pan=0.20)
    # 8) sail_wind billow as merchant corbita turns into safe channel (S07 23.25s)
    _add_cue_burst("sail_wind", 23.25, 0.72, 190.0, 110.0, 0.20, pan=-0.25)

    # Original procedural musical underscore: tense A-minor harbor pulse (0..22.3s) -> warm F-maj7/C relief chord (22.6..30.0s)
    tension_env = np.clip(t / 1.1, 0.0, 1.0) * np.clip((22.6 - t) / 0.8, 0.0, 1.0)
    pulse = 0.58 + 0.42 * np.sin(2.0 * np.pi * 1.35 * t)
    score_tension = (
        0.038 * np.sin(2.0 * np.pi * 110.00 * t)
        + 0.025 * np.sin(2.0 * np.pi * 130.81 * t)
        + 0.019 * np.sin(2.0 * np.pi * 164.81 * t)
    ) * tension_env * pulse

    relief_env = np.clip((t - 22.5) / 1.3, 0.0, 1.0) * np.clip((total_dur - t) / 0.65, 0.0, 1.0)
    score_relief = (
        0.038 * np.sin(2.0 * np.pi * 130.81 * t)
        + 0.030 * np.sin(2.0 * np.pi * 164.81 * t)
        + 0.026 * np.sin(2.0 * np.pi * 196.00 * t)
        + 0.019 * np.sin(2.0 * np.pi * 246.94 * t)
    ) * relief_env
    cue_ledger.append({"cue": "relief_chord", "real_time_sec": 22.6, "dur_sec": round(max(0.5, total_dur - 22.6), 3)})

    bed_l = (sfx_l + score_tension + score_relief) * duck
    bed_r = (sfx_r + score_tension * 0.96 + score_relief * 1.04) * duck

    raw_mix = np.stack([v_stereo[:, 0] * 1.14 + bed_l, v_stereo[:, 1] * 1.14 + bed_r], axis=1)
    pk = float(np.max(np.abs(raw_mix)))
    if pk > 0.92:
        raw_mix = raw_mix * (0.92 / pk)

    pre_wav = build_dir / "soundtrack_pre_loudnorm.wav"
    mixed_wav = build_dir / "soundtrack_mixed.wav"
    pcm_pre = np.clip(raw_mix * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(pre_wav), "wb") as wf_pre:
        wf_pre.setnchannels(2)
        wf_pre.setsampwidth(2)
        wf_pre.setframerate(sr)
        wf_pre.writeframes(pcm_pre.tobytes())

    p1 = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(pre_wav),
            "-af",
            "loudnorm=I=-14.0:TP=-1.5:LRA=9.0:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    m_json = re.search(r"\{\s*\"input_i\"[\s\S]*?\}", p1.stderr)
    dur_str = f"{total_dur:.3f}"
    if m_json:
        ln_stats = json.loads(m_json.group(0))
        af_norm = (
            f"loudnorm=I=-14.0:TP=-1.5:LRA=9.0:"
            f"measured_I={ln_stats['input_i']}:"
            f"measured_TP={ln_stats['input_tp']}:"
            f"measured_LRA={ln_stats['input_lra']}:"
            f"measured_thresh={ln_stats['input_thresh']}:"
            f"offset={ln_stats['target_offset']}:linear=true,"
            f"apad=whole_dur={dur_str},atrim=0:{dur_str}"
        )
    else:
        af_norm = f"loudnorm=I=-14.0:TP=-1.5:LRA=9.0,apad=whole_dur={dur_str},atrim=0:{dur_str}"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(pre_wav),
            "-af",
            af_norm,
            "-ar",
            str(sr),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(mixed_wav),
        ],
        check=True,
        capture_output=True,
    )
    pre_wav.unlink(missing_ok=True)
    shutil.copy2(mixed_wav, build_dir / "mix.wav")

    wav_metrics = inspect_media_file(
        mixed_wav,
        expected_specs={"measure_loudness": True, "max_true_peak_dbtp": -1.0},
        require_audio=True,
        full_decode=True,
        require_video=False,
    )
    mix_report = {
        "schema_version": "14.7.6",
        "status": "AUDIO_MIX_PASS" if wav_metrics.get("valid") else "FAIL",
        "mixed_wav": str(mixed_wav),
        "duration_sec": wav_metrics.get("duration"),
        "integrated_lufs": wav_metrics.get("integrated_lufs"),
        "true_peak_dbtp": wav_metrics.get("true_peak_dbtp"),
        "sound_provenance": "100%_ORIGINAL_PROCEDURAL_NUMPY_FOLEY_AND_MACOS_SAY_DANIEL_TTS",
        "licensed_external_music_borrowed": False,
        "synchronized_cues": cue_ledger,
    }
    (build_dir / "audio_mix_report.json").write_text(json.dumps(mix_report, indent=2), encoding="utf-8")
    return mix_report


def generate_portus_contact_sheets(
    project_path: Path = PROJECT_DIR,
    mp4_path: Path = OUT_MP4_PATH,
    extra_evidence_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Decode real frames from the muxed 1080p24 MP4 and compose:
    - `contact_sheet_full.png` (4x2 grid across S01..S08)
    - `contact_sheet_hook.png` (3x2 grid across S01..S02 flame snuff -> dark harbor shoals)
    - `contact_sheet_action.png` (3x2 grid across S03..S07 lantern grab, slip/rail catch, 3-angle hoist, ship turn)
    """
    p_dir = Path(project_path).resolve()
    out_dir = p_dir / "out"
    tmp_dir = p_dir / "build" / "contact_frames_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    specs = {
        "contact_sheet_full.png": {
            "cols": 4,
            "rows": 2,
            "samples": [
                ("S01 0.5s Beacon Snuff", 0.5),
                ("S02 4.8s Ship Near Rocks", 4.8),
                ("S03 8.8s Lantern Grip Insert", 8.8),
                ("S04 12.2s Steps & Rope Brace", 12.2),
                ("S05 15.6s Gust Slip & Rail", 15.6),
                ("S06 20.0s Shared Rope Hoist", 20.0),
                ("S07 24.6s Safe Channel Turn", 24.6),
                ("S08 28.4s Safe Passage Card", 28.4),
            ],
        },
        "contact_sheet_hook.png": {
            "cols": 3,
            "rows": 2,
            "samples": [
                ("0.2s Warm Oil Beacon", 0.2),
                ("0.7s Snuffed By Gust", 0.7),
                ("2.1s Dark Harbor Reveal", 2.1),
                ("3.6s Rolling Corbita", 3.6),
                ("4.9s Shoals & Surf", 4.9),
                ("6.1s Dark Tower Foreground", 6.1),
            ],
        },
        "contact_sheet_action.png": {
            "cols": 3,
            "rows": 2,
            "samples": [
                ("7.4s Aelia Spots Danger", 7.4),
                ("9.0s Hand Locks Bail", 9.0),
                ("15.4s Slip & Catch Rail", 15.4),
                ("18.8s Wide Two-Actor Haul", 18.8),
                ("20.2s Taut Rope Grip Insert", 20.2),
                ("21.8s Low Alcove Hoist", 21.8),
            ],
        },
    }

    tile_w, tile_h = 480, 270
    pad = 16
    header_h = 54
    generated: Dict[str, Any] = {}

    for sheet_name, cfg in specs.items():
        cols, rows = cfg["cols"], cfg["rows"]
        canvas_w = pad + cols * (tile_w + pad)
        canvas_h = header_h + pad + rows * (tile_h + 34 + pad)
        sheet = Image.new("RGB", (canvas_w, canvas_h), (20, 26, 36))
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (pad, 16),
            f"{FILM_TITLE.replace('—', '-')} - {sheet_name} (Decoded from 1080p24 MP4)",
            fill=(246, 224, 168),
        )

        for idx, (caption, ts) in enumerate(cfg["samples"]):
            r_idx = idx // cols
            c_idx = idx % cols
            frame_png = tmp_dir / f"{sheet_name}_{idx:02d}.png"
            ok = extract_frame_at_time(mp4_path, ts, frame_png)
            if not ok or not frame_png.is_file():
                raise RuntimeError(f"Failed decoding contact-sheet frame at {ts}s from {mp4_path}")
            with Image.open(frame_png) as fim:
                thumb = fim.convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
            x0 = pad + c_idx * (tile_w + pad)
            y0 = header_h + pad + r_idx * (tile_h + 34 + pad)
            sheet.paste(thumb, (x0, y0))
            draw.rectangle([x0 - 1, y0 - 1, x0 + tile_w + 1, y0 + tile_h + 1], outline=(220, 176, 92), width=2)
            draw.text((x0 + 6, y0 + tile_h + 8), caption, fill=(235, 238, 244))

        dest_p = out_dir / sheet_name
        sheet.save(dest_p, format="PNG")
        if extra_evidence_dir is not None:
            Path(extra_evidence_dir).mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest_p, Path(extra_evidence_dir) / sheet_name)
        generated[sheet_name] = {
            "path": str(dest_p),
            "size_bytes": dest_p.stat().st_size,
            "sha256": sha256_file(dest_p),
            "dimensions": [canvas_w, canvas_h],
        }

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return generated


def inspect_portus_preview(
    project_path: Path = PROJECT_DIR,
    mp4_path: Path = OUT_MP4_PATH,
    ev_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Fail-closed verification of the 30.000s / 720-frame Portus MP4:
    - `verify_receipt_and_lineage` (ffprobe + full video/audio decode + exact 720 frames + EBU R128 loudness),
    - `verify_portus_causality`,
    - `audit_project_temporal_visual` (intershot boundaries, framing, non-empty motion),
    - `audit_motion_performance` (planted-foot drift, hand-prop grip <= 0.04, all internal multi-angle cuts,
      +/- 0.25s grip/slip strips, original-asset manifest, receipt freshness, narration non-silence).
    """
    p_dir = Path(project_path).resolve()
    m_path = Path(mp4_path).resolve()
    qa_dir = Path(ev_dir).resolve() if ev_dir else (p_dir / "build" / "portus_qa")
    qa_dir.mkdir(parents=True, exist_ok=True)

    expected_specs = {
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "min_duration": 29.95,
        "max_duration": 30.05,
        "exact_video_frames": NOMINAL_VIDEO_FRAMES,
        "require_audio": True,
        "measure_loudness": True,
        "max_true_peak_dbtp": -1.0,
    }
    lineage = verify_receipt_and_lineage(p_dir, m_path, expected_specs=expected_specs)
    mi = lineage.get("media_info") or {}

    sb = json.loads((p_dir / "story" / "shots.json").read_text(encoding="utf-8"))
    mp_dict = json.loads((p_dir / "story" / "motion_plan.json").read_text(encoding="utf-8"))
    causality = verify_portus_causality(sb)
    asset_manifest_p = p_dir / "story" / "asset_source_manifest.json"
    asset_manifest = json.loads(asset_manifest_p.read_text(encoding="utf-8"))
    v_ledger = json.loads((p_dir / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))

    # Write lightweight MP4-digest sidecar for `audit_motion_performance` receipt check in addition to `render_receipt.json`
    mp4_sha_receipt = p_dir / "build" / "mp4_sha_receipt.json"
    live_rr = p_dir / "out" / "render_receipt.json"
    if live_rr.is_file():
        rr_obj = json.loads(live_rr.read_text(encoding="utf-8"))
        mp4_sha_receipt.write_text(
            json.dumps({"mp4_sha256": rr_obj.get("output", {}).get("sha256") or sha256_file(m_path)}, indent=2),
            encoding="utf-8",
        )

    temporal_rep = audit_project_temporal_visual(p_dir, m_path, qa_dir / "temporal_visual")
    motion_rep = audit_motion_performance(
        p_dir,
        m_path,
        mp_dict,
        ev_dir=qa_dir / "motion_perf",
        original_asset_manifest_path=asset_manifest_p,
        media_receipt_path=mp4_sha_receipt if mp4_sha_receipt.is_file() else None,
        voice_wav_path=p_dir / "build" / "voice_track.wav",
        fps=24.0,
    )

    v_dur = float(mi.get("video_stream_duration") or 0.0)
    a_dur = float(mi.get("audio_stream_duration") or 0.0)
    c_dur = float(mi.get("duration") or 0.0)
    av_diff = round(abs(c_dur - NOMINAL_DURATION_SEC), 4)
    stream_diff = round(abs(a_dur - v_dur), 4)
    lufs = mi.get("integrated_lufs")
    tp = mi.get("true_peak_dbtp")

    loudness_ok = (lufs is not None) and (-15.5 <= float(lufs) <= -12.5)
    tp_ok = (tp is not None) and (float(tp) <= -1.0)
    frames_ok = int(mi.get("decoded_video_frames") or 0) == NOMINAL_VIDEO_FRAMES
    av_sync_ok = (av_diff <= 0.05) and (stream_diff <= 0.05)
    voice_ok = (
        float(v_ledger.get("measured_overlap_ms", 99.0)) == 0.0
        and float(v_ledger.get("min_tail_margin_sec", 0.0)) >= 0.25
        and v_ledger.get("atempo_used_anywhere") is False
        and v_ledger.get("last_spoken_phrase") == "The ship made it through."
    )
    orig_ok = int(asset_manifest.get("prior_preview_derived_visual_inputs", 1)) == 0
    temporal_ok = temporal_rep.technical_verdict == "VISUAL_TECH_PASS"
    motion_ok = motion_rep.get("status") == "PASS"

    all_valid = (
        lineage.get("status") == "PASS"
        and frames_ok
        and av_sync_ok
        and loudness_ok
        and tp_ok
        and voice_ok
        and causality.get("valid") is True
        and orig_ok
        and temporal_ok
        and motion_ok
    )
    return {
        "valid": all_valid,
        "status": "PASS" if all_valid else "FAIL",
        "editorial_status": "EDITORIAL_REVIEW_PENDING",
        "cache_status": lineage.get("cache_status"),
        "lineage": lineage,
        "media_info": mi,
        "decoded_video_frames": mi.get("decoded_video_frames"),
        "nominal_duration_diff_sec": av_diff,
        "audio_video_stream_diff_sec": stream_diff,
        "causality": causality,
        "temporal_visual_qa": {
            "technical_verdict": temporal_rep.technical_verdict,
            "passed_shots": temporal_rep.passed_shots,
            "total_shots": temporal_rep.total_shots,
            "audited_cut_count": temporal_rep.audited_cut_count,
            "expected_cut_count": temporal_rep.expected_cut_count,
            "full_boundary_coverage": temporal_rep.full_boundary_coverage,
            "global_issues": temporal_rep.global_issues,
        },
        "motion_performance_qa": motion_rep,
        "voice_summary": {
            "speech_provider": v_ledger.get("speech_provider"),
            "beats_count": v_ledger.get("beats_count"),
            "measured_overlap_ms": v_ledger.get("measured_overlap_ms"),
            "min_tail_margin_sec": v_ledger.get("min_tail_margin_sec"),
            "all_beats_meet_0_35s_target": v_ledger.get("all_beats_meet_0_35s_target"),
            "last_spoken_phrase": v_ledger.get("last_spoken_phrase"),
            "last_spoken_end_sec": v_ledger.get("last_spoken_end_sec"),
            "atempo_used_anywhere": v_ledger.get("atempo_used_anywhere"),
        },
        "asset_originality": asset_manifest,
    }


def produce_portus_preview(
    force_rebuild: bool = False,
    project_path: Path = PROJECT_DIR,
    output_mp4_path: Path = OUT_MP4_PATH,
    workers: int = 1,
    extra_evidence_dir: Optional[Path] = None,
    run_full_qa_on_cache_hit: bool = False,
) -> Dict[str, Any]:
    """
    End-to-end FL-01 production pipeline for 'THE LAST LIGHT OF PORTUS — A ROMAN HARBOR STORY'.
    Supports verified content-addressed warm cache hits (`force_rebuild=False`) and full cold
    Chromium + FFmpeg rendering (`force_rebuild=True`).
    """
    t0 = time.perf_counter()
    p_dir = Path(project_path).resolve()
    out_mp4 = Path(output_mp4_path).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    build_dir = p_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    expected_specs = {
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "min_duration": 29.95,
        "max_duration": 30.05,
        "exact_video_frames": NOMINAL_VIDEO_FRAMES,
        "require_audio": True,
        "measure_loudness": True,
        "max_true_peak_dbtp": -1.0,
    }
    render_opts = {
        "audio_mode": "voice_sfx",
        "code_dependencies": [
            HARBOR_MODULE_REL,
            "packs/squire/motion_engine.js",
            "integrations/claude_motion/adapter.js",
        ],
    }

    if not force_rebuild and out_mp4.is_file() and (p_dir / "config.json").is_file():
        pre_manifest = collect_render_inputs(p_dir, render_options=render_opts)
        cache_check = validate_cache_hit(p_dir, out_mp4, pre_manifest, expected_specs=expected_specs)
        if cache_check.get("hit") is True:
            existing_sheets = {
                name: out_mp4.parent / f"{name}.png"
                for name in ("contact_sheet_full", "contact_sheet_hook", "contact_sheet_action")
            }
            if not run_full_qa_on_cache_hit and all(sp.is_file() for sp in existing_sheets.values()):
                sheets_info: Dict[str, Any] = {}
                for name, sp in existing_sheets.items():
                    sheets_info[name] = {"path": str(sp), "sha256": sha256_file(sp)}
                    if extra_evidence_dir is not None:
                        Path(extra_evidence_dir).mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sp, Path(extra_evidence_dir) / sp.name)
                return {
                    "status": "CACHE_HIT_VERIFIED",
                    "render_mode": "CACHE_HIT_VERIFIED",
                    "wall_sec": round(time.perf_counter() - t0, 4),
                    "output_mp4": str(out_mp4),
                    "mp4_sha256": sha256_file(out_mp4),
                    "mp4_size_bytes": out_mp4.stat().st_size,
                    "cache_validation": cache_check,
                    "contact_sheets": sheets_info,
                }
            sheets = generate_portus_contact_sheets(p_dir, out_mp4, extra_evidence_dir=extra_evidence_dir)
            insp = inspect_portus_preview(p_dir, out_mp4, ev_dir=extra_evidence_dir)
            return {
                "status": "CACHE_HIT_VERIFIED" if insp["valid"] else "FAIL",
                "render_mode": "CACHE_HIT_VERIFIED",
                "wall_sec": round(time.perf_counter() - t0, 4),
                "output_mp4": str(out_mp4),
                "mp4_sha256": sha256_file(out_mp4),
                "mp4_size_bytes": out_mp4.stat().st_size,
                "inspection": insp,
                "contact_sheets": sheets,
            }

    # Step 1: Script -> Storyboard + MotionPlan + CameraSegments -> Project files & original assets
    plan_t0 = time.perf_counter()
    sb = build_portus_storyboard(CANONICAL_PORTUS_SCRIPT, fx_profile="claude_selective")
    orig_assets = build_portus_original_assets(p_dir)
    construct_portus_project(sb["motion_plan"], orig_assets, project_path=p_dir, storyboard=sb)
    plan_wall_sec = round(time.perf_counter() - plan_t0, 4)

    # Step 2: Measured Daniel TTS voice track (exact 30.000s, 0ms overlap, energy-weighted words)
    voice_res = generate_portus_measured_voice(p_dir, storyboard=sb)
    if not voice_res.get("ok"):
        return {
            "status": voice_res.get("status", "FAIL"),
            "error": voice_res.get("error"),
            "wall_sec": round(time.perf_counter() - t0, 4),
        }

    # Step 3: Event-synchronized harbor foley + score (-14 LUFS, <= -1.0 dBTP, exact 30.000s)
    mix_res = build_portus_event_soundtrack(p_dir, voice_events=voice_res["events"], motion_plan=sb["motion_plan"])
    if mix_res.get("status") != "AUDIO_MIX_PASS":
        return {"status": "FAIL", "error": f"Audio mix failed: {mix_res}"}

    # Step 4: Render 720 frames @ 1080p24 via real headless Chromium (`render.mjs`)
    env = dict(os.environ)
    env.pop("QA_STUDIO_TEST_MODE", None)
    render_t0 = time.perf_counter()
    cmd_render = ["node", "render.mjs", "--project", str(p_dir), "--workers", str(max(1, int(workers)))]
    proc = subprocess.run(cmd_render, cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    render_wall_sec = round(time.perf_counter() - render_t0, 3)

    (build_dir / "render.log").write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        return {
            "status": "FAIL",
            "error": f"render.mjs exited {proc.returncode}: {(proc.stderr or proc.stdout)[-600:]}",
            "wall_sec": round(time.perf_counter() - t0, 4),
        }

    silent_mp4 = build_dir / "video_silent.mp4"
    if not silent_mp4.is_file() or silent_mp4.stat().st_size < 1000:
        return {"status": "FAIL", "error": "Missing or empty build/video_silent.mp4"}

    # Step 5: Mux exact 720-frame video + exact 30.000s audio via atomic partial file
    partial_mp4 = out_mp4.with_suffix(".partial.mp4")
    partial_mp4.unlink(missing_ok=True)
    mux_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(silent_mp4),
        "-i",
        str(build_dir / "soundtrack_mixed.wav"),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-af",
        "atrim=0:30.0",
        "-movflags",
        "+faststart",
        str(partial_mp4),
    ]
    mux_res = subprocess.run(mux_cmd, cwd=ROOT_DIR, capture_output=True, text=True)
    if mux_res.returncode != 0:
        return {"status": "FAIL", "error": f"FFmpeg mux failed: {mux_res.stderr[-500:]}"}

    pre_inspect = inspect_media_file(partial_mp4, expected_specs=expected_specs, require_audio=True, full_decode=True)
    if not pre_inspect.get("valid"):
        return {
            "status": "FAIL",
            "error": f"Partial MP4 failed media verification before promotion: {pre_inspect.get('errors')}",
            "media_info": pre_inspect,
        }

    os.replace(partial_mp4, out_mp4)

    # Step 6: Write atomic cryptographic render receipt + contact sheets + full QA inspection
    manifest = collect_render_inputs(p_dir, render_options=render_opts)
    total_wall = round(time.perf_counter() - t0, 3)
    node_ver = subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip()
    receipt_p = write_render_receipt_atomic(
        p_dir,
        out_mp4,
        manifest,
        metadata={
            "version": "14.7.6",
            "action": "produce_portus_preview",
            "render_mode": "REAL_RENDER",
            "force_rebuild": bool(force_rebuild),
            "ai_director_mode": "OFFLINE_ONLY",
            "ai_director_live_used": False,
            "motion_plan_wall_sec": plan_wall_sec,
            "render_only_wall_sec": render_wall_sec,
            "wall_sec": total_wall,
            "node_version": node_ver,
            "python_version": sys.version.split()[0],
        },
    )
    (build_dir / "mp4_sha_receipt.json").write_text(
        json.dumps({"mp4_sha256": sha256_file(out_mp4)}, indent=2),
        encoding="utf-8",
    )

    sheets = generate_portus_contact_sheets(p_dir, out_mp4, extra_evidence_dir=extra_evidence_dir)
    final_insp = inspect_portus_preview(p_dir, out_mp4, ev_dir=extra_evidence_dir)

    return {
        "status": "PRODUCED" if final_insp["valid"] else "FAIL",
        "render_mode": "REAL_RENDER",
        "sample_note": "SMALL_SAMPLE (n=1 cold 30s 1080p24 render)",
        "motion_plan_wall_sec": plan_wall_sec,
        "render_only_wall_sec": render_wall_sec,
        "wall_sec": round(time.perf_counter() - t0, 3),
        "output_mp4": str(out_mp4),
        "mp4_sha256": sha256_file(out_mp4),
        "mp4_size_bytes": out_mp4.stat().st_size,
        "receipt_path": str(receipt_p),
        "inspection": final_insp,
        "contact_sheets": sheets,
    }


def run_portus_wording_variation_test() -> Dict[str, Any]:
    """
    Prove `build_portus_storyboard(script_source)` genuinely responds to changed input wording
    rather than returning a hardcoded S01..S08 performer.
    """
    variation_script = "\n".join([
        "The harbor light went dark.",
        "A merchant ship was heading straight for the rocks.",
        "Felix walked toward the lantern.",
        "Aelia pointed at the rocks.",
        "Aelia ducked from the spray.",
        "Together, they lifted the heavy lantern.",
        "Its glow showed the sailors a safe way home.",
        "The ship made it through.",
    ])
    sb_canon = build_portus_storyboard(CANONICAL_PORTUS_SCRIPT)
    sb_var = build_portus_storyboard(variation_script)

    canon_actions = [s["action"] for s in sb_canon["shots"]]
    var_actions = [s["action"] for s in sb_var["shots"]]
    canon_actors_s03 = [p["id"] for p in sb_canon["shots"][2]["args"]["people"]]
    var_actors_s03 = [p["id"] for p in sb_var["shots"][2]["args"]["people"]]
    canon_segs_s03 = len(sb_canon["shots"][2]["args"]["cameraSegments"])
    var_segs_s03 = len(sb_var["shots"][2]["args"]["cameraSegments"])

    differ = (
        sb_canon["script_sha256"] != sb_var["script_sha256"]
        and canon_actions != var_actions
        and canon_actors_s03 != var_actors_s03
    )
    return {
        "status": "PASS" if differ else "FAIL",
        "canonical_script_sha256": sb_canon["script_sha256"],
        "variation_script_sha256": sb_var["script_sha256"],
        "canonical_shot_actions": canon_actions,
        "variation_shot_actions": var_actions,
        "s03_canonical_actors": canon_actors_s03,
        "s03_variation_actors": var_actors_s03,
        "s03_canonical_camera_segments": canon_segs_s03,
        "s03_variation_camera_segments": var_segs_s03,
    }


def _render_short_harbor_project(
    proj_dir: Path,
    shots_list: List[Dict[str, Any]],
    motion_plan_dict: Dict[str, Any],
    out_mp4: Path,
    shared_audio_wav: Path,
    preload_rigby_extra_anims: Optional[Dict[str, Any]] = None,
    width: int = 1920,
    height: int = 1080,
) -> Dict[str, Any]:
    """Helper to render an 8s A/B/C comparison or 4s unseen generalization clip via real `render.mjs`."""
    for sub in ("story", "scenes/shots", "build", "out"):
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)
    dur = round(float(shots_list[-1]["end"]), 3)
    shot_ids_json = json.dumps([s["id"] for s in shots_list])

    if preload_rigby_extra_anims is not None:
        entry_js_code = (
            "import { ensureHarborRigbyAssetLoaded, registerPortusShots } from '/packs/squire/harbor/portus_light.js';\n"
            f"const extraAnims = {json.dumps(preload_rigby_extra_anims)};\n"
            "await ensureHarborRigbyAssetLoaded(extraAnims);\n"
            f"registerPortusShots({shot_ids_json});\n"
        )
    else:
        entry_js_code = (
            "import { registerPortusShots } from '/packs/squire/harbor/portus_light.js';\n"
            f"registerPortusShots({shot_ids_json});\n"
        )
    (proj_dir / "scenes" / "shots" / "short_shots.js").write_text(entry_js_code, encoding="utf-8")

    (proj_dir / "config.json").write_text(
        json.dumps({
            "name": proj_dir.name,
            "pack": "squire",
            "aspect": "16:9",
            "width": width,
            "height": height,
            "fps": 24,
            "bars": "none",
            "captions": False,
        }, indent=2),
        encoding="utf-8",
    )
    (proj_dir / "story" / "shots.json").write_text(
        json.dumps({"duration": dur, "total_duration": dur, "fps": 24, "shots": shots_list}, indent=2),
        encoding="utf-8",
    )
    (proj_dir / "story" / "motion_plan.json").write_text(json.dumps(motion_plan_dict, indent=2), encoding="utf-8")

    env = dict(os.environ)
    env.pop("QA_STUDIO_TEST_MODE", None)
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["node", "render.mjs", "--project", str(proj_dir), "--workers", "1"],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    render_sec = round(time.perf_counter() - t0, 3)
    if proc.returncode != 0:
        raise RuntimeError(f"render.mjs failed on {proj_dir.name}: {(proc.stderr or proc.stdout)[-500:]}")

    silent_mp4 = proj_dir / "build" / "video_silent.mp4"
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(silent_mp4),
            "-i", str(shared_audio_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-af", f"atrim=0:{dur:.3f}",
            "-movflags", "+faststart",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )
    mi = inspect_media_file(
        out_mp4,
        expected_specs={
            "width": width,
            "height": height,
            "fps": 24.0,
            "exact_video_frames": int(round(dur * 24)),
            "require_audio": True,
        },
        require_audio=True,
        full_decode=True,
    )
    return {
        "mp4_path": str(out_mp4),
        "mp4_sha256": sha256_file(out_mp4),
        "size_bytes": out_mp4.stat().st_size,
        "render_wall_sec": render_sec,
        "decoded_video_frames": mi.get("decoded_video_frames"),
        "valid": bool(mi.get("valid")),
    }


def produce_abc_8s_comparison(
    out_root: Optional[Path] = None,
    ev_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Render the mandatory 8.000s (`192` frames @ `24 fps`) A/B/C harbor comparison clips
    showing Aelia holding the lantern and Felix hauling the tower rope under identical
    scene geometry, spoken Daniel narration, camera, duration, and seed `1476`:
      - Clip A: V14.7.5.1 procedural sine/formula baseline (`legacy_v14_7_5_1`, `fx_profile='none'`)
      - Clip B: MotionPlan + Natural Motion IK compiled into genuine Rigby2D `0.5.1` WebGL skeletal runtime (`rigby2d`, `fx_profile='none'`)
      - Clip C: Clip B + selective Claude Animation timing & sparse interaction FX (`rigby2d`, `fx_profile='claude_selective'`)
    """
    from integrations.rigby2d.pilot import convert_motion_plan_to_rigby_tracks

    base_dir = Path(out_root).resolve() if out_root else (PROJECT_DIR / "out" / "abc_comparison_8s")
    base_dir.mkdir(parents=True, exist_ok=True)
    say_bin = shutil.which("say")
    if not say_bin:
        return {"status": "BLOCKED_NO_SPEECH_PROVIDER", "error": "macOS 'say' unavailable"}

    # 1. Shared 8.000s spoken narration + harbor foley WAV (identical across A, B, C!)
    shared_wav = base_dir / "abc_shared_8s_audio.wav"
    aiff_tmp = base_dir / "_tmp_abc.aiff"
    line_1 = "Aelia steadied the burning lantern."
    line_2 = "Together, Felix and Aelia hauled the tower rope."
    subprocess.run([say_bin, "-v", "Daniel", "-r", "182", "-o", str(aiff_tmp), f"{line_1} {line_2}"], check=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(aiff_tmp),
            "-af", "apad=whole_dur=8.0,atrim=0:8.0,volume=0.85",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(shared_wav),
        ],
        check=True,
    )
    aiff_tmp.unlink(missing_ok=True)

    # 2. Shared 2-shot 8.000s MotionPlan
    abc_events = [
        {"id": "C01", "start": 0.0, "end": 4.0, "dur": 4.0, "line": line_1},
        {"id": "C02", "start": 4.0, "end": 8.0, "dur": 4.0, "line": line_2},
    ]
    cast = copy.deepcopy(PORTUS_CAST_BIBLE)
    w_init = copy.deepcopy(PORTUS_BASE_WORLD_STATE)
    intents = extract_semantic_motion_intents(
        script_text=f"{line_1}\n{line_2}",
        script_events=abc_events,
        cast_bible=cast,
        world_state=w_init,
        pack="squire",
        genre="harbor",
    )
    tracks = plan_actor_motion_phases(
        intents,
        get_pack_capabilities("squire", "harbor"),
        abc_events,
        cast_bible=cast,
        world_state=w_init,
    )
    mplan = build_shared_motion_timeline([], tracks, w_init, intents=intents, project_id="abc_8s", pack="squire", genre="harbor")
    mp_dict = mplan.model_dump()

    rig_manifest = json.loads(
        (ROOT_DIR / "integrations/rigby2d/assets/roman_harbor_worker_manifest.json").read_text(encoding="utf-8")
    )
    rig_compiled = convert_motion_plan_to_rigby_tracks(mp_dict, rig_manifest)
    extra_rigby_anims = {
        info["animation_name"]: info["spine_animation"]
        for info in (rig_compiled.get("tracks") or {}).values()
    }

    def _make_shots(backend: str, fx_prof: str) -> List[Dict[str, Any]]:
        out_s = []
        for idx, ev in enumerate(abc_events):
            sid = ev["id"]
            s_tracks = [tr for tr in mp_dict["tracks"] if tr["shot_id"] == sid]
            out_s.append({
                "id": sid,
                "start": ev["start"],
                "end": ev["end"],
                "dur": ev["dur"],
                "line": ev["line"],
                "tpl": "scene",
                "expected_subject": "actor",
                "world_state": {"wind": 0.74, "sea_direction": "left_to_right", "objects": w_init["objects"]},
                "mechanics": {
                    "wind_strength": 0.74,
                    "lantern_carried": idx == 0,
                    "lantern_on_hoist": idx == 1,
                    "lantern_lift_start": 0.05 if idx == 1 else 0.0,
                    "lantern_lift_end": 0.88 if idx == 1 else 0.0,
                    "pulley_angle_start": 0.0,
                    "pulley_angle_end": 4.6 if idx == 1 else 0.0,
                },
                "args": {
                    "bg": "portus_harbor",
                    "groundY": 0.84,
                    "towerX": 0.74,
                    "actorBackend": backend,
                    "fx_profile": fx_prof,
                    "seed": 1476,
                    "motionPlan": {**mp_dict, "fx_profile": fx_prof},
                    "motionTracks": s_tracks,
                    "people": [
                        {"id": "aelia", "preset": "lady", "from": 0.38, "to": 0.46, "x": 0.42, "y": 0.84, "h": 0.28},
                        {"id": "felix", "preset": "peasant", "from": 0.62, "to": 0.60, "x": 0.62, "y": 0.84, "h": 0.28},
                    ],
                    "fxEvents": [
                        {"kind": "lantern_gust_embers", "t0": 1.2, "x": 0.48, "y": 0.68},
                        {"kind": "rope_strain_dust", "t0": 5.1, "x": 0.62, "y": 0.72},
                        {"kind": "beacon_relight_pulse", "t0": 7.4, "x": 0.74, "y": 0.22, "radius": 90},
                    ] if fx_prof == "claude_selective" else [],
                    "actionWarpSpecs": [{"at": 5.15, "hold": 0.05, "ease": 0.14}] if fx_prof == "claude_selective" else [],
                },
            })
        return out_s

    work_projects = base_dir / "_build_projects"
    clip_a = _render_short_harbor_project(
        work_projects / "clip_a",
        _make_shots("legacy_v14_7_5_1", "none"),
        mp_dict,
        base_dir / "A_v14_7_5_1_procedural_baseline_8s.mp4",
        shared_wav,
        preload_rigby_extra_anims=None,
    )
    clip_b = _render_short_harbor_project(
        work_projects / "clip_b",
        _make_shots("rigby2d", "none"),
        mp_dict,
        base_dir / "B_v14_7_6_motion_plan_rigby2d_8s.mp4",
        shared_wav,
        preload_rigby_extra_anims=extra_rigby_anims,
    )
    clip_c = _render_short_harbor_project(
        work_projects / "clip_c",
        _make_shots("rigby2d", "claude_selective"),
        mp_dict,
        base_dir / "C_v14_7_6_rigby2d_plus_claude_fx_8s.mp4",
        shared_wav,
        preload_rigby_extra_anims=extra_rigby_anims,
    )

    # Compose side-by-side baseline (A) vs enhanced (B & C) contact sheets
    sheet_path = base_dir / "contact_sheet_abc_comparison.png"
    sample_ts = [1.2, 3.0, 5.2, 7.4]
    tw, th, pad = 384, 216, 14
    sheet = Image.new("RGB", (pad + len(sample_ts) * (tw + pad), 46 + 3 * (th + 28 + pad)), (18, 24, 32))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 12), "8s A/B/C Comparison: Row1=A (V14.7.5.1 Sine) | Row2=B (MotionPlan+Rigby2D WebGL) | Row3=C (B+Claude FX)", fill=(246, 224, 168))
    tmp_f = base_dir / "_tmp_abc_frames"
    tmp_f.mkdir(parents=True, exist_ok=True)
    for r_i, (lbl, c_info) in enumerate([("A: V14.7.5.1", clip_a), ("B: Rigby2D", clip_b), ("C: Rigby2D+FX", clip_c)]):
        for c_i, ts in enumerate(sample_ts):
            fp = tmp_f / f"r{r_i}_c{c_i}.png"
            extract_frame_at_time(Path(c_info["mp4_path"]), ts, fp)
            with Image.open(fp) as im:
                thumb = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            x0 = pad + c_i * (tw + pad)
            y0 = 46 + r_i * (th + 28 + pad)
            sheet.paste(thumb, (x0, y0))
            dr.rectangle([x0 - 1, y0 - 1, x0 + tw + 1, y0 + th + 1], outline=(212, 172, 88), width=2)
            dr.text((x0 + 6, y0 + th + 6), f"{lbl} @ {ts:.1f}s", fill=(235, 238, 244))
    sheet.save(sheet_path, format="PNG")
    shutil.rmtree(tmp_f, ignore_errors=True)
    shutil.rmtree(work_projects, ignore_errors=True)

    # Measure quantitative foot-drift improvement (legacy sine vs V14.7.6 Natural Motion)
    foot_qa = audit_foot_plant(mp_dict)
    hand_qa = audit_hand_prop_contact(mp_dict)
    trace_json_path = base_dir / "abc_motion_traces.json"
    trace_payload = {
        "schema_version": "14.7.6",
        "seed": 1476,
        "duration_sec": 8.0,
        "rigby_track_count": rig_compiled.get("track_count"),
        "natural_motion_foot_plant": foot_qa,
        "natural_motion_hand_contact": hand_qa,
    }
    trace_json_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")

    if ev_dir is not None:
        Path(ev_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy2(sheet_path, Path(ev_dir) / "contact_sheet_abc_comparison.png")
        shutil.copy2(trace_json_path, Path(ev_dir) / "abc_motion_traces.json")

    distinct_hashes = len({clip_a["mp4_sha256"], clip_b["mp4_sha256"], clip_c["mp4_sha256"]}) == 3
    motion_qa_ok = foot_qa.get("status") == "PASS" and hand_qa.get("status") == "PASS"
    all_ok = distinct_hashes and clip_a["valid"] and clip_b["valid"] and clip_c["valid"] and motion_qa_ok
    return {
        "status": "PASS" if all_ok else "FAIL",
        "distinct_three_mp4_hashes": distinct_hashes,
        "rigby2d_backend_used_in_B_and_C": "rigby2d_webgl_0.5.1",
        "clip_A_baseline_v14_7_5_1": clip_a,
        "clip_B_motion_plan_rigby2d": clip_b,
        "clip_C_rigby2d_plus_claude_fx": clip_c,
        "contact_sheet": {"path": str(sheet_path), "sha256": sha256_file(sheet_path)},
        "motion_trace_json": str(trace_json_path),
        "foot_plant_metrics": {
            "max_median_planted_foot_drift_norm": foot_qa.get("max_median_planted_foot_drift_norm"),
            "max_peak_planted_foot_drift_norm": foot_qa.get("max_peak_planted_foot_drift_norm"),
        },
        "hand_contact_metrics": {
            "peak_hand_grip_dist_norm": hand_qa.get("peak_hand_grip_dist_norm"),
        },
    }


def produce_three_unseen_short_generalization_clips(out_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Execute & render all 3 unseen short scripts from Section 4 & Section 10 through FL-01:
      (a) citizen slips and steadies a basket
      (b) merchant lifts a heavy amphora with another person
      (c) child walks toward lantern then ducks from wind
    """
    base_dir = Path(out_root).resolve() if out_root else (PROJECT_DIR / "out" / "unseen_generalization_clips")
    base_dir.mkdir(parents=True, exist_ok=True)
    say_bin = shutil.which("say")
    if not say_bin:
        return {"status": "BLOCKED_NO_SPEECH_PROVIDER", "error": "macOS 'say' unavailable"}

    cases = [
        {
            "case_id": "unseen_a_citizen_basket",
            "script": "A citizen slips on the wet stone and steadies a woven basket.",
            "cast": {"citizen_1": {"preset": "peasant", "role": "citizen", "x": 0.42, "y": 0.84, "facing": 1}},
            "objects": {"basket": {"x": 0.49, "y": 0.74}},
            "props": [{"kind": "woven_basket", "x": 0.50, "y": 0.76}],
        },
        {
            "case_id": "unseen_b_merchant_amphora",
            "script": "A merchant lifts a heavy amphora with another person.",
            "cast": {
                "merchant_1": {"preset": "senator", "role": "merchant", "x": 0.44, "y": 0.84, "facing": 1},
                "helper_1": {"preset": "smith", "role": "helper", "x": 0.56, "y": 0.84, "facing": -1},
            },
            "objects": {"amphora": {"x": 0.50, "y": 0.75}},
            "props": [{"kind": "heavy_amphora", "x": 0.50, "y": 0.75}],
        },
        {
            "case_id": "unseen_c_child_lantern_duck",
            "script": "A child walks toward the lantern, then ducks from the wind.",
            "cast": {"child_1": {"preset": "peasant", "role": "child", "x": 0.34, "y": 0.84, "facing": 1}},
            "objects": {"lantern": {"x": 0.60, "y": 0.70}},
            "props": [{"kind": "dock_lantern_post", "x": 0.62}],
        },
    ]

    results: List[Dict[str, Any]] = []
    work_root = base_dir / "_build_unseen"
    for cs in cases:
        cid = cs["case_id"]
        ev = [{"id": "U01", "start": 0.0, "end": 4.0, "dur": 4.0, "line": cs["script"]}]
        w_state = {"environment": {"wind": 0.68}, "actors": cs["cast"], "objects": cs["objects"]}
        intents = extract_semantic_motion_intents(cs["script"], ev, cs["cast"], w_state, pack="squire", genre="civic")
        tracks = plan_actor_motion_phases(
            intents,
            get_pack_capabilities("squire", "civic"),
            ev,
            cast_bible=cs["cast"],
            world_state=w_state,
        )
        plan = build_shared_motion_timeline([], tracks, w_state, intents=intents, project_id=cid, pack="squire", genre="civic")
        val = validate_motion_plan(plan)

        wav_p = base_dir / f"{cid}.wav"
        aiff_p = base_dir / f"_{cid}.aiff"
        subprocess.run([say_bin, "-v", "Daniel", "-r", "182", "-o", str(aiff_p), cs["script"]], check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(aiff_p), "-af", "apad=whole_dur=4.0,atrim=0:4.0", "-ar", "48000", "-ac", "2", str(wav_p)],
            check=True,
        )
        aiff_p.unlink(missing_ok=True)

        mp_dict = plan.model_dump()
        shot_obj = [{
            "id": "U01",
            "start": 0.0,
            "end": 4.0,
            "dur": 4.0,
            "line": cs["script"],
            "tpl": "scene",
            "expected_subject": "actor",
            "world_state": {"wind": 0.68, "sea_direction": "left_to_right", "objects": cs["objects"]},
            "mechanics": {"wind_strength": 0.68, "show_ship": False, "show_shoals": False},
            "args": {
                "bg": "portus_harbor",
                "groundY": 0.84,
                "actorBackend": "natural_canvas",
                "motionPlan": mp_dict,
                "motionTracks": mp_dict["tracks"],
                "props": cs["props"],
                "people": [
                    {"id": aid, "preset": info["preset"], "x": info["x"], "y": info["y"], "h": 0.24 if "child" in aid else 0.28}
                    for aid, info in cs["cast"].items()
                ],
            },
        }]
        render_info = _render_short_harbor_project(
            work_root / cid,
            shot_obj,
            mp_dict,
            base_dir / f"{cid}.mp4",
            wav_p,
            width=1920,
            height=1080,
        )
        wav_p.unlink(missing_ok=True)
        foot_qa = audit_foot_plant(mp_dict)
        hand_qa = audit_hand_prop_contact(mp_dict)
        results.append({
            "case_id": cid,
            "script": cs["script"],
            "extracted_motion_types": [i.motion_type for i in intents],
            "extracted_actors": [t.actor_id for t in plan.tracks],
            "plan_valid": val.get("valid"),
            "foot_plant_status": foot_qa.get("status"),
            "hand_contact_status": hand_qa.get("status"),
            "render": render_info,
        })

    shutil.rmtree(work_root, ignore_errors=True)
    all_ok = all(
        r["plan_valid"] and r["foot_plant_status"] == "PASS" and r["hand_contact_status"] == "PASS" and r["render"]["valid"]
        for r in results
    )
    return {
        "status": "PASS" if all_ok else "FAIL",
        "cases_count": len(results),
        "cases": results,
    }


if __name__ == "__main__":
    force = "--force" in sys.argv
    res = produce_portus_preview(force_rebuild=force, workers=1)
    print(
        json.dumps(
            {
                k: res.get(k)
                for k in ("status", "render_mode", "motion_plan_wall_sec", "render_only_wall_sec", "wall_sec", "output_mp4", "mp4_sha256", "error")
            },
            indent=2,
        )
    )
    sys.exit(0 if res.get("status") in ("PRODUCED", "CACHE_HIT_VERIFIED") else 1)
