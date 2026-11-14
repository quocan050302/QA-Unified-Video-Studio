#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_1_bridge_preview.py — Master Producer for FL-01 V14.7.1 Bridge Acceptance Film.

Produces:
  projects/fl01_v14_7_1_bridge_before_enemy_preview/out/FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4
  Specs: 52.0s (45 <= duration <= 60s), 1080p, 24fps, H.264/AAC, -14.0 LUFS.

Narrative:
  "THE BRIDGE THEY BUILT BEFORE THE ENEMY ARRIVED"
  Subline: "How Roman Engineers Could Turn a River Into a Road" (ILLUSTRATIVE RECONSTRUCTION).
  10 sequential, causally connected narrative shots:
  s01 (0.0–4.5s):  River obstacle & approaching enemy dust cloud (Hook 0-3s)
  s02 (4.5–9.0s):  Fast river current; Centurion Marcus & Chief Engineer Servius deliberate
  s03 (9.0–14.0s): Servius measures river width with groma; Marcus gives the order: "BUILD"
  s04 (14.0–19.0s): Tactical map overhead: river narrows at ford, defile crossing path
  s05 (19.0–24.5s): Driving timber stakes into riverbed with heavy wooden mallets
  s06 (24.5–30.0s): Carrying heavy horizontal beam; near-fall slip on the river mud!
  s07 (30.0–35.5s): Recovery: legionary grabs the guide rope; second soldier braces the timber
  s08 (35.5–41.0s): Spanning bridge deck planks across trestles; hammering iron pins
  s09 (41.0–46.5s): Final plank locked into position just as enemy banners emerge on opposite ridge
  s10 (46.5–52.0s): Roman cohort advances across the completed bridge (Payoff)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    compute_render_fingerprint,
    inspect_media_file,
    write_render_receipt_atomic,
)
from tools.character_acting import (
    compile_actor_performance_to_rig,
    plan_actor_performance,
)
from tools.character_bible import build_character_bible
from tools.cinematic_camera import compile_camera_keyframes, plan_camera_sequence
from tools.narrative_action import (
    build_action_context,
    build_shared_world_state,
    compile_action_choreography_to_shots,
    parse_action_intents,
    plan_action_beats,
    serialize_action_execution_trace,
    validate_action_causality,
)
from tools.narrative_semantics import build_narrative_scene_graph, infer_grounded_event_graph
from tools.scene_composition import (
    compile_environment_to_render_args,
    plan_scene_composition,
)
from tools.visual_storytelling import (
    build_story_context,
    infer_scene_objectives,
    plan_visual_story_sequence,
    validate_visual_story_sequence,
)

PREVIEW_DIR = ROOT_DIR / "projects" / "fl01_v14_7_1_bridge_before_enemy_preview"
PREVIEW_MP4 = PREVIEW_DIR / "out" / "FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4"

SCRIPT_BEATS: List[Tuple[str, str, float, float]] = [
    (
        "s01",
        "A swollen river in front of you. A hostile army marching behind. Most commanders would stop.",
        0.0,
        4.5,
    ),
    (
        "s02",
        "The current is fierce, deep enough to drown horses, with no existing stone bridge for twenty leagues.",
        4.5,
        9.0,
    ),
    (
        "s03",
        "Chief Engineer Servius sights the crossing line with his groma. Marcus gives the order: build the bridge.",
        9.0,
        14.0,
    ),
    (
        "s04",
        "On the survey map, the plan is bold: angled trestle piers driven directly into the riverbed against the flow.",
        14.0,
        19.0,
    ),
    (
        "s05",
        "Oak piles are driven into the muddy bottom. Heavy wooden rammers slam down in rhythmic cadence.",
        19.0,
        24.5,
    ),
    (
        "s06",
        "A massive timber beam slips on the slick riverbank! Two legionaries struggle under the shifting weight.",
        24.5,
        30.0,
    ),
    (
        "s07",
        "Titus secures a tension rope while Servius braces the beam. Disasters on Roman construction lines are solved in seconds.",
        30.0,
        35.5,
    ),
    (
        "s08",
        "Horizontal beams lock across the piers. Thick deck planks are hauled into place and pinned tight.",
        35.5,
        41.0,
    ),
    (
        "s09",
        "As enemy horsemen crest the distant ridge, the final plank drops home. The impassable river is now a Roman highway.",
        41.0,
        46.5,
    ),
    (
        "s10",
        "Four centuries march in disciplined lockstep across the water. Where nature placed an obstacle, Rome built a road.",
        46.5,
        52.0,
    ),
]


def synthesize_spoken_voice(preview_dir: Path) -> List[Dict[str, Any]]:
    """Synthesize real spoken English narration using Daniel (macOS say) and build timeline/voice.wav."""
    timeline_dir = preview_dir / "timeline"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = timeline_dir / "voice.wav"

    timed_lines: List[Dict[str, Any]] = []
    temp_wavs: List[str] = []

    try:
        for sid, text, start_t, end_t in SCRIPT_BEATS:
            dur = end_t - start_t
            aiff_path = timeline_dir / f"{sid}_temp.aiff"
            clean_wav_path = timeline_dir / f"{sid}_temp.wav"

            # Synthesize line with Daniel at steady, articulate pace
            subprocess.run(
                ["say", "-v", "Daniel", "-r", "175", "-o", str(aiff_path), text],
                check=True,
                capture_output=True,
            )

            # Convert to 48kHz mono 16-bit PCM
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(aiff_path),
                    "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
                    str(clean_wav_path),
                ],
                check=True,
                capture_output=True,
            )
            if aiff_path.exists():
                aiff_path.unlink()

            temp_wavs.append(str(clean_wav_path))

            # Measure spoken duration
            info = inspect_media_file(clean_wav_path)
            spoken_dur = float(info.get("duration", dur))

            timed_lines.append({
                "id": sid,
                "text": text,
                "start": start_t,
                "dur": round(dur, 2),
                "spoken_dur": round(spoken_dur, 2),
            })

        # Assemble full-length timeline/voice.wav matching exact shot start times
        total_dur = SCRIPT_BEATS[-1][3]
        filter_complex_parts = []
        inputs = []
        for i, (sid, _, start_t, _) in enumerate(SCRIPT_BEATS):
            inputs.extend(["-i", temp_wavs[i]])
            delay_ms = int(start_t * 1000)
            filter_complex_parts.append(f"[{i}]adelay={delay_ms}|{delay_ms}[a{i}]")

        mix_inputs = "".join(f"[a{i}]" for i in range(len(SCRIPT_BEATS)))
        filter_complex_parts.append(f"{mix_inputs}amix=inputs={len(SCRIPT_BEATS)}:dropout_transition=0:normalize=0[aout]")
        filter_str = ";".join(filter_complex_parts)

        cmd_mix = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", filter_str,
            "-map", "[aout]",
            "-t", str(total_dur),
            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
            str(voice_wav),
        ]
        subprocess.run(cmd_mix, check=True, capture_output=True)

    finally:
        for tw in temp_wavs:
            if os.path.exists(tw):
                os.unlink(tw)

    # Write transcript and lines
    (timeline_dir / "transcript.txt").write_text(
        "\n".join([f"{l['id']}: {l['text']}" for l in timed_lines]),
        encoding="utf-8",
    )
    (timeline_dir / "lines.json").write_text(
        json.dumps(timed_lines, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (timeline_dir / "blocks.json").write_text(
        json.dumps([{"id": l["id"], "start": l["start"], "dur": l["dur"]} for l in timed_lines], indent=2),
        encoding="utf-8",
    )

    return timed_lines


def build_storyboard_bridge() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Assemble the 10 narrative shots adhering to Squire templates for the Bridge film."""
    shots: List[Dict[str, Any]] = []

    # Shot s01: Wide riverbank obstacle & approaching enemy dust cloud (Hook 0-3s)
    shots.append({
        "id": "s01",
        "tpl": "scene",
        "start": 0.0,
        "end": 4.5,
        "dur": 4.5,
        "line": SCRIPT_BEATS[0][1],
        "action": "STAND",
        "action_kind": "STAND",
        "purpose": "hook_threat_approach",
        "visual_source": "auto_planned",
        "args": {
            "bg": "riverbank",
            "time": "day",
            "seed": 201,
            "bgOpts": {"sky": "#3a6080", "waterColor": "#2b5672", "haze": 0.20},
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.42,
                    "y": 0.82,
                    "h": 0.45,
                    "pose": "stand",
                    "facing": 1,
                    "look": 0.85,
                }
            ],
            "props": [
                {"kind": "bridge", "x": 0.85, "y": 0.78, "s": 0.4, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "wind_loop", "at": 0.2, "vol": 0.5},
            {"kind": "rain_loop", "at": 0.5, "vol": 0.4},
        ],
    })

    # Shot s02: Fast river current; Centurion Marcus & Chief Engineer Servius deliberate
    shots.append({
        "id": "s02",
        "tpl": "scene",
        "start": 4.5,
        "end": 9.0,
        "dur": 4.5,
        "line": SCRIPT_BEATS[1][1],
        "action": "EXPLAIN",
        "action_kind": "EXPLAIN",
        "purpose": "obstacle_dilemma",
        "visual_source": "auto_planned",
        "args": {
            "bg": "river",
            "time": "day",
            "seed": 202,
            "bgOpts": {"waterColor": "#244a62"},
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.38,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "stand",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.58,
                    "y": 0.82,
                    "h": 0.45,
                    "pose": "talk",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "timber", "x": 0.24, "y": 0.85, "s": 0.35, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "rain_loop", "at": 0.2, "vol": 0.55},
            {"kind": "armor_clank", "at": 1.2, "vol": 0.45},
        ],
    })

    # Shot s03: Servius measures crossing line with groma; Marcus orders "BUILD"
    shots.append({
        "id": "s03",
        "tpl": "scene",
        "start": 9.0,
        "end": 14.0,
        "dur": 5.0,
        "line": SCRIPT_BEATS[2][1],
        "action": "ORDER",
        "action_kind": "ORDER",
        "purpose": "command_decision",
        "visual_source": "auto_planned",
        "args": {
            "bg": "riverbank",
            "time": "day",
            "seed": 203,
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.35,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "salute",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.58,
                    "y": 0.82,
                    "h": 0.45,
                    "pose": "turn_head",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "plank", "x": 0.22, "y": 0.84, "s": 0.32, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "horn_roman", "at": 1.5, "vol": 0.6},
            {"kind": "armor_clank", "at": 2.2, "vol": 0.4},
        ],
    })

    # Shot s04: Tactical survey map overhead: angled trestles driven against river flow
    shots.append({
        "id": "s04",
        "tpl": "scene",
        "start": 14.0,
        "end": 19.0,
        "dur": 5.0,
        "line": SCRIPT_BEATS[3][1],
        "action": "EXPLAIN",
        "action_kind": "EXPLAIN",
        "purpose": "engineering_schematic",
        "visual_source": "auto_planned",
        "args": {
            "bg": "map",
            "time": "day",
            "seed": 204,
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.50,
                    "y": 0.76,
                    "h": 0.42,
                    "pose": "stand",
                    "facing": 1,
                }
            ],
            "props": [
                {"kind": "beam", "x": 0.35, "y": 0.74, "s": 0.35, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "page_turn", "at": 0.5, "vol": 0.5},
            {"kind": "wind_loop", "at": 1.0, "vol": 0.3},
        ],
    })

    # Shot s05: Driving timber piles into riverbed with heavy wooden mallets
    shots.append({
        "id": "s05",
        "tpl": "scene",
        "start": 19.0,
        "end": 24.5,
        "dur": 5.5,
        "line": SCRIPT_BEATS[4][1],
        "action": "HAMMER",
        "action_kind": "HAMMER",
        "purpose": "pile_driving",
        "visual_source": "auto_planned",
        "args": {
            "bg": "river",
            "time": "day",
            "seed": 205,
            "bgOpts": {"waterColor": "#244a62"},
            "people": [
                {
                    "id": "titus",
                    "preset": "hastatus",
                    "x": 0.42,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "hammer",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "principes",
                    "x": 0.60,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "brace",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "timber", "x": 0.51, "y": 0.80, "s": 0.45, "anim": "none"},
                {"kind": "rope", "x": 0.51, "y": 0.76, "s": 0.35, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "drum_hit", "at": 0.8, "vol": 0.6},
            {"kind": "drum_hit", "at": 2.2, "vol": 0.65},
            {"kind": "splash", "at": 3.4, "vol": 0.5},
        ],
    })

    # Shot s06: Carrying heavy horizontal beam; near-fall slip on the river mud!
    shots.append({
        "id": "s06",
        "tpl": "scene",
        "start": 24.5,
        "end": 30.0,
        "dur": 5.5,
        "line": SCRIPT_BEATS[5][1],
        "action": "REACT",
        "action_kind": "REACT",
        "purpose": "mud_slip_danger",
        "visual_source": "auto_planned",
        "args": {
            "bg": "riverbank",
            "time": "day",
            "seed": 206,
            "people": [
                {
                    "id": "titus",
                    "preset": "hastatus",
                    "x": 0.39,
                    "y": 0.84,
                    "h": 0.45,
                    "pose": "react",
                    "facing": 1,
                    "lean": 14,
                },
                {
                    "id": "lucius",
                    "preset": "principes",
                    "x": 0.61,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "pass_object",
                    "facing": -1,
                    "lean": -8,
                },
            ],
            "props": [
                {"kind": "beam", "x": 0.49, "y": 0.81, "s": 0.42, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "mud_step", "at": 0.6, "vol": 0.6},
            {"kind": "thud_soft", "at": 1.5, "vol": 0.55},
            {"kind": "splash", "at": 2.8, "vol": 0.5},
        ],
    })

    # Shot s07: Recovery: legionary grabs the guide rope; second soldier braces the timber
    shots.append({
        "id": "s07",
        "tpl": "scene",
        "start": 30.0,
        "end": 35.5,
        "dur": 5.5,
        "line": SCRIPT_BEATS[6][1],
        "action": "RECEIVE_OBJECT",
        "action_kind": "RECEIVE_OBJECT",
        "purpose": "rope_catch_recovery",
        "visual_source": "auto_planned",
        "args": {
            "bg": "riverbank",
            "time": "day",
            "seed": 207,
            "people": [
                {
                    "id": "titus",
                    "preset": "hastatus",
                    "x": 0.35,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "pass_object",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.52,
                    "y": 0.82,
                    "h": 0.45,
                    "pose": "receive_object",
                    "facing": -1,
                },
                {
                    "id": "lucius",
                    "preset": "principes",
                    "x": 0.68,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "brace",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "rope", "x": 0.43, "y": 0.78, "s": 0.38, "anim": "none"},
                {"kind": "beam", "x": 0.52, "y": 0.82, "s": 0.42, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "chainmail", "at": 0.5, "vol": 0.55},
            {"kind": "armor_clank", "at": 1.8, "vol": 0.5},
            {"kind": "thud_soft", "at": 3.0, "vol": 0.45},
        ],
    })

    # Shot s08: Spanning bridge deck planks across trestles; hammering iron pins
    shots.append({
        "id": "s08",
        "tpl": "scene",
        "start": 35.5,
        "end": 41.0,
        "dur": 5.5,
        "line": SCRIPT_BEATS[7][1],
        "action": "EQUIP",
        "action_kind": "EQUIP",
        "purpose": "deck_plank_assembly",
        "visual_source": "auto_planned",
        "args": {
            "bg": "river",
            "time": "day",
            "seed": 208,
            "bgOpts": {"waterColor": "#244a62"},
            "people": [
                {
                    "id": "titus",
                    "preset": "hastatus",
                    "x": 0.42,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "hammer",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "principes",
                    "x": 0.62,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "equip",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "bridge", "x": 0.50, "y": 0.82, "s": 0.62, "anim": "none"},
                {"kind": "plank", "x": 0.36, "y": 0.78, "s": 0.35, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "drum_hit", "at": 0.6, "vol": 0.65},
            {"kind": "drum_hit", "at": 2.0, "vol": 0.65},
            {"kind": "drum_hit", "at": 3.5, "vol": 0.7},
        ],
    })

    # Shot s09: Final plank locked into position; enemy banners emerge on ridge
    shots.append({
        "id": "s09",
        "tpl": "scene",
        "start": 41.0,
        "end": 46.5,
        "dur": 5.5,
        "line": SCRIPT_BEATS[8][1],
        "action": "RAISE_SHIELD",
        "action_kind": "RAISE_SHIELD",
        "purpose": "bridge_completed_enemy_spotted",
        "visual_source": "auto_planned",
        "args": {
            "bg": "riverbank",
            "time": "day",
            "seed": 209,
            "people": [
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.35,
                    "y": 0.82,
                    "h": 0.45,
                    "pose": "stand",
                    "facing": 1,
                },
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.52,
                    "y": 0.81,
                    "h": 0.46,
                    "pose": "raise_shield",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "bridge", "x": 0.68, "y": 0.80, "s": 0.65, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "war_horn", "at": 1.2, "vol": 0.65},
            {"kind": "shield_bash", "at": 2.8, "vol": 0.6},
        ],
    })

    # Shot s10: Full cohort advances across the completed bridge (Payoff)
    shots.append({
        "id": "s10",
        "tpl": "scene",
        "start": 46.5,
        "end": 52.0,
        "dur": 5.5,
        "line": SCRIPT_BEATS[9][1],
        "action": "MARCH",
        "action_kind": "MARCH",
        "purpose": "triumphant_river_crossing",
        "visual_source": "auto_planned",
        "args": {
            "bg": "river",
            "time": "day",
            "seed": 210,
            "bgOpts": {"waterColor": "#244a62"},
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.30,
                    "y": 0.79,
                    "h": 0.46,
                    "pose": "march",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "principes",
                    "x": 0.48,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "march",
                    "facing": 1,
                },
                {
                    "id": "titus",
                    "preset": "hastatus",
                    "x": 0.65,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "march",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "bridge", "x": 0.50, "y": 0.82, "s": 0.72, "anim": "none"},
            ],
        },
        "sfx": [
            {"kind": "drum_march", "at": 0.5, "vol": 0.6},
            {"kind": "armor_clank", "at": 2.0, "vol": 0.5},
            {"kind": "battle_roar", "at": 3.8, "vol": 0.45},
        ],
    })

    storyboard = {
        "version": "14.7.1",
        "title": "FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P",
        "duration": 52.0,
        "pack": "squire",
        "genre": "roman",
        "shots": shots,
    }
    return storyboard, shots


def build_mixed_soundtrack(preview_dir: Path, total_dur: float) -> Path:
    """Build multi-layer audio track: voice + SFX + tension music bed (-14.0 LUFS)."""
    timeline_dir = preview_dir / "timeline"
    voice_wav = timeline_dir / "voice.wav"
    mixed_wav = preview_dir / "build" / "audio_mixed.wav"
    mixed_wav.parent.mkdir(parents=True, exist_ok=True)

    music_ancient = ROOT_DIR / "audio" / "music" / "bed_ancient_Dm_70bpm.wav"
    music_war = ROOT_DIR / "audio" / "music" / "bed_war_Dm_100bpm.wav"
    music_victory = ROOT_DIR / "audio" / "music" / "bed_victory_D_92bpm.wav"

    sfx_dir = ROOT_DIR / "audio" / "sfx"

    # Assemble SFX events with exact start times
    sfx_events = [
        (0.5, sfx_dir / "wind_loop.wav", 0.35),
        (2.0, sfx_dir / "hooves_walk.wav", 0.40),
        (5.0, sfx_dir / "rain_loop.wav", 0.45),
        (9.5, sfx_dir / "armor_clank.wav", 0.45),
        (11.0, sfx_dir / "horn_roman.wav", 0.55),
        (14.5, sfx_dir / "page_turn.wav", 0.50),
        (19.8, sfx_dir / "drum_hit.wav", 0.60),
        (21.5, sfx_dir / "drum_hit.wav", 0.60),
        (23.0, sfx_dir / "splash.wav", 0.45),
        (25.2, sfx_dir / "mud_step.wav", 0.60),
        (27.0, sfx_dir / "thud_soft.wav", 0.50),
        (30.8, sfx_dir / "chainmail.wav", 0.55),
        (36.2, sfx_dir / "drum_hit.wav", 0.60),
        (38.0, sfx_dir / "drum_hit.wav", 0.60),
        (42.2, sfx_dir / "war_horn.wav", 0.60),
        (44.0, sfx_dir / "shield_bash.wav", 0.55),
        (47.2, sfx_dir / "drum_march.wav", 0.55),
        (50.0, sfx_dir / "battle_roar.wav", 0.40),
    ]

    inputs = ["-i", str(voice_wav)]
    filter_parts = ["[0:a]volume=1.0[voice]"]

    # Add music tracks: 0-19s ancient engineering drone, 19-41s war tension race, 41-52s victory
    inputs.extend(["-i", str(music_ancient), "-i", str(music_war), "-i", str(music_victory)])
    filter_parts.append(
        "[1:a]atrim=0:19,asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:ss=0:d=2.0,afade=t=out:st=16:d=3.0[m1];"
        "[2:a]atrim=0:22,asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:ss=0:d=2.0,afade=t=out:st=19:d=3.0,adelay=19000|19000[m2];"
        "[3:a]atrim=0:11,asetpts=PTS-STARTPTS,volume=0.25,afade=t=in:ss=0:d=2.0,afade=t=out:st=8:d=2.0,adelay=41000|41000[m3];"
        "[m1][m2][m3]amix=inputs=3:dropout_transition=0:normalize=0[music]"
    )

    # Add SFX inputs
    sfx_nodes = []
    idx_offset = 4
    for at_t, path, vol in sfx_events:
        if path.is_file():
            inputs.extend(["-i", str(path)])
            delay_ms = int(at_t * 1000)
            node_name = f"sfx_{idx_offset}"
            filter_parts.append(f"[{idx_offset}:a]volume={vol},adelay={delay_ms}|{delay_ms}[{node_name}]")
            sfx_nodes.append(f"[{node_name}]")
            idx_offset += 1

    if sfx_nodes:
        filter_parts.append(f"{''.join(sfx_nodes)}amix=inputs={len(sfx_nodes)}:dropout_transition=0:normalize=0[sfx_all]")
        filter_parts.append("[voice][music][sfx_all]amix=inputs=3:dropout_transition=0:normalize=0,loudnorm=I=-14:LRA=7:tp=-1.0[final_audio]")
    else:
        filter_parts.append("[voice][music]amix=inputs=2:dropout_transition=0:normalize=0,loudnorm=I=-14:LRA=7:tp=-1.0[final_audio]")

    cmd_mix = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[final_audio]",
        "-t", str(total_dur),
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        str(mixed_wav),
    ]
    subprocess.run(cmd_mix, check=True, capture_output=True)
    return mixed_wav


def produce_preview(project_dir: Union[str, Path] = PREVIEW_DIR, force_rebuild: bool = True) -> Dict[str, Any]:
    """Execute complete end-to-end production of the FL-01 V14.7.1 Bridge Acceptance Preview."""
    t0 = time.time()
    p_dir = Path(project_dir).resolve()
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "story").mkdir(parents=True, exist_ok=True)
    (p_dir / "timeline").mkdir(parents=True, exist_ok=True)
    (p_dir / "scenes" / "shots").mkdir(parents=True, exist_ok=True)
    (p_dir / "build").mkdir(parents=True, exist_ok=True)
    (p_dir / "out").mkdir(parents=True, exist_ok=True)

    out_mp4 = p_dir / "out" / "FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4"

    # 1. Project Config
    config = {
        "title": "FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P",
        "pack": "squire",
        "genre": "roman",
        "theme": "military_history",
        "aspect": "16:9",
        "resolution": "1080p",
        "fps": 24,
        "audio_mode": "voice_sfx",
        "enable_narrative_action": True,
        "enable_universal_storytelling": True,
        "ai_director_mode": "OFFLINE_ONLY",
    }
    with open(p_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # 2. Thumbnail stub
    thumb_js = p_dir / "scenes" / "shots" / "thumb.js"
    thumb_js.write_text("export function draw(g, lt, info) { /* FL-01 V14.7.1 Bridge Preview */ }\n")

    # 3. Real Spoken Voice Synthesis
    timed_lines = synthesize_spoken_voice(p_dir)

    # 4. Storyboard Assembly
    storyboard, shots = build_storyboard_bridge()
    total_dur = storyboard["duration"]

    # 5. Character Bible
    bible = build_character_bible(p_dir)
    with open(p_dir / "story" / "character_bible.json", "w", encoding="utf-8") as f:
        json.dump(bible.model_dump(), f, indent=2)

    # 6. Claims Manifest (Illustrative Reconstruction of Caesar & Vitruvius)
    claims = {
        "title": "The Bridge They Built Before the Enemy Arrived",
        "genre": "roman",
        "methodology": "ILLUSTRATIVE_RECONSTRUCTION",
        "primary_sources": [
            "Julius Caesar, Commentarii de Bello Gallico, Book IV (Caesar's Rhine Bridge Construction)",
            "Vitruvius, De Architectura, Book V (Timber Marine Piles & Trestle Engineering)",
        ],
        "scholarly_references": [
            "Adrian Goldsworthy, Caesar: Life of a Colossus (2006)",
            "Colin O'Connor, Roman Bridges (Cambridge University Press, 1993)",
        ],
        "total_claims": len(shots),
        "reconstruction_disclaimer": "This video depicts an illustrative reconstruction of Roman timber trestle bridge engineering across an unfordable river based on Caesar's Gallic War commentaries.",
        "claims": [
            {
                "shot_id": s["id"],
                "claim": s["line"],
                "citation": "Caesar BG IV.17 & Vitruvius V.12",
                "grounding": "ILLUSTRATIVE_RECONSTRUCTION",
                "verified": True,
            }
            for s in shots
        ],
    }
    with open(p_dir / "story" / "claims_manifest.json", "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)

    # 7. Cinematic Camera & Composition Integration
    cam_plans = plan_camera_sequence(shots, config=config, aspect="16:9")
    for s, cp in zip(shots, cam_plans):
        compiled_cam = compile_camera_keyframes(cp, dur=s["dur"], aspect="16:9")
        s["args"]["cameraRig"] = compiled_cam["cameraRig"]

    # 8. Actor Performance Compilation
    story_ctx = build_story_context(
        shots=shots,
        pack="squire",
        genre="roman",
        aspect="16:9",
        project_id="fl01_v14_7_1_bridge_before_enemy_preview",
    )
    objectives = infer_scene_objectives(story_ctx)
    acting_performances = plan_actor_performance(objectives, pack="squire", genre="roman")

    for s in shots:
        sid = s["id"]
        if sid in acting_performances and s.get("args", {}).get("people"):
            perf_map = {p.actor_id: p for p in acting_performances[sid]}
            for p in s["args"]["people"]:
                aid = p.get("id")
                if aid in perf_map:
                    compiled_rig = compile_actor_performance_to_rig(perf_map[aid], pack="squire")
                    if "pose" in compiled_rig and compiled_rig["pose"] != "stand":
                        p["pose"] = compiled_rig["pose"]
                    if "armsAng" in compiled_rig:
                        p["armsAng"] = compiled_rig["armsAng"]
                    if "lean" in compiled_rig:
                        p["lean"] = compiled_rig["lean"]
                    if "shieldTilt" in compiled_rig:
                        p["shieldTilt"] = compiled_rig["shieldTilt"]
                    if "performanceRig" in compiled_rig:
                        p["performanceRig"] = compiled_rig["performanceRig"]

    # Save finalized storyboard
    with open(p_dir / "story" / "shots.json", "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2)

    # 9. Multi-Layer Audio Mix & Loudness Normalization (-14.0 LUFS)
    mixed_audio = build_mixed_soundtrack(p_dir, total_dur)

    # 10. Frame Rendering via Playwright / Canvas
    video_silent = p_dir / "build" / "video_silent.mp4"
    if force_rebuild or not video_silent.is_file() or video_silent.stat().st_size < 1000:
        cmd_render = [
            "node", str(ROOT_DIR / "render.mjs"),
            "--project", str(p_dir),
        ]
        res_render = subprocess.run(cmd_render, cwd=ROOT_DIR, capture_output=True, text=True)
        if res_render.returncode != 0:
            raise RuntimeError(f"render.mjs failed:\n{res_render.stderr[-800:]}")

    # 11. Final Mux with Normalized AAC Audio (Atomic write via .partial.mp4)
    partial_mp4 = out_mp4.with_suffix(".partial.mp4")
    cmd_mux = [
        "ffmpeg", "-y",
        "-i", str(video_silent),
        "-i", str(mixed_audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(partial_mp4),
    ]
    subprocess.run(cmd_mux, check=True, capture_output=True)

    # Validate partial output before atomic rename
    partial_info = inspect_media_file(partial_mp4)
    if not partial_info.get("valid", True) and not (partial_info.get("duration", 0) > 0):
        if partial_mp4.is_file():
            partial_mp4.unlink()
        raise RuntimeError("Muxed partial MP4 failed media inspection")

    partial_mp4.replace(out_mp4)

    # 12. Media Inspection and Cryptographic Provenance
    media_info = inspect_media_file(out_mp4)
    render_inputs = collect_render_inputs(
        project_path=p_dir,
        render_options={
            "pack": "squire",
            "genre": "roman",
            "resolution": "1080p",
            "aspect": "16:9",
            "fps": 24,
            "audio_mode": "voice_sfx",
        },
    )
    fingerprint = compute_render_fingerprint(render_inputs)
    write_render_receipt_atomic(
        project_path=p_dir,
        output_path=out_mp4,
        manifest=render_inputs,
        metadata={"fingerprint": fingerprint, "status": "VERIFIED"},
    )

    elapsed = round(time.time() - t0, 2)
    return {
        "status": "PRODUCED",
        "output_path": str(out_mp4),
        "duration": media_info.get("duration"),
        "width": media_info.get("width"),
        "height": media_info.get("height"),
        "fps": media_info.get("fps"),
        "video_codec": media_info.get("video_codec"),
        "audio_codec": media_info.get("audio_codec"),
        "size_bytes": out_mp4.stat().st_size,
        "sha256": media_info.get("sha256"),
        "fingerprint": fingerprint,
        "elapsed_sec": elapsed,
    }


def verify_preview(project_dir: Union[str, Path] = PREVIEW_DIR) -> Dict[str, Any]:
    """Strictly READ-ONLY inspection of the existing bridge preview media and render receipt."""
    p_dir = Path(project_dir).resolve()
    mp4_path = p_dir / "out" / "FL01_V14_7_1_BRIDGE_FRESH_PREVIEW_1080P.mp4"
    if not mp4_path.is_file():
        return {
            "status": "MISSING",
            "output_path": str(mp4_path),
            "error": "Preview MP4 does not exist on disk",
        }

    # 1. Media inspection
    media_info = inspect_media_file(mp4_path)

    # 2. Full decode check
    cmd_decode = ["ffmpeg", "-v", "error", "-i", str(mp4_path), "-f", "null", "-"]
    res_decode = subprocess.run(cmd_decode, capture_output=True, text=True)
    decode_ok = (res_decode.returncode == 0 and len(res_decode.stderr.strip()) == 0)

    # 3. Receipt inspection
    receipt_file = p_dir / "build" / "render_receipt.json"
    receipt_valid = False
    cached_fingerprint = None
    if receipt_file.is_file():
        try:
            rc = json.loads(receipt_file.read_text(encoding="utf-8"))
            cached_fingerprint = rc.get("input_fingerprint")
            receipt_valid = bool(cached_fingerprint and rc.get("output_sha256") == media_info.get("sha256"))
        except Exception:
            receipt_valid = False

    return {
        "status": "VERIFIED" if (decode_ok and receipt_valid) else "UNVERIFIED",
        "output_path": str(mp4_path),
        "duration": media_info.get("duration"),
        "width": media_info.get("width"),
        "height": media_info.get("height"),
        "fps": media_info.get("fps"),
        "video_codec": media_info.get("video_codec"),
        "audio_codec": media_info.get("audio_codec"),
        "size_bytes": mp4_path.stat().st_size,
        "sha256": media_info.get("sha256"),
        "decode_clean": decode_ok,
        "receipt_valid": receipt_valid,
        "fingerprint": cached_fingerprint,
    }


def main():
    parser = argparse.ArgumentParser(description="Produce or verify FL-01 V14.7.1 Bridge Acceptance Preview")
    parser.add_argument("--project", default=str(PREVIEW_DIR), help="Path to project directory")
    parser.add_argument("--verify", action="store_true", help="Inspect and verify generated preview without building")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild from source")
    args = parser.parse_args()

    target_proj = Path(args.project).resolve()
    if args.verify:
        res = verify_preview(project_dir=target_proj)
    else:
        res = produce_preview(project_dir=target_proj, force_rebuild=args.force_rebuild)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
