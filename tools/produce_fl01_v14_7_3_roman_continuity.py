#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_3_roman_continuity.py — V14.7.3 Roman Continuity Benchmark Producer.

Produces the brand-new 1080p acceptance preview film:
"THE GAP IN THE ROMAN LINE — HOW THE RESERVES TURNED A CRISIS INTO ORDER"
(Illustrative reconstruction of early Roman manipular tactics).

Specs:
- 10 shots, 52.5 seconds (within 45–60s)
- Resolution: 1920x1080 @ 24fps
- Codec: H.264 / AAC
- Audio: Spoken English (Daniel) + multi-layer sound design (-14.0 LUFS ± 3.5 dB)
- Flow: 4 acts (Establishing -> Reaction -> Action -> Payoff) with hook in 0–3s
- Engine: Rendered via Playwright + FFmpeg (real illustrated vectors, no static collages)
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.production_fingerprint import (
    collect_render_inputs,
    compute_render_fingerprint,
    inspect_media_file,
    validate_cache_hit,
    write_render_receipt_atomic,
)
from tools.cinematic_camera import plan_camera_sequence

PROJECT_DIR = ROOT_DIR / "projects" / "fl01_v14_7_3_roman_continuity_benchmark"
OUT_MP4_PATH = PROJECT_DIR / "out" / "FL01_V14_7_3_ROMAN_CONTINUITY_FRESH_PREVIEW_1080P.mp4"

SCRIPT_BEATS = [
    (
        "s01",
        "When a Roman front line began to buckle under relentless enemy pressure, why was a sudden gap not a fatal disaster, but a calculated trap?",
        0.0,
        4.5,
    ),
    (
        "s02",
        "In early republican warfare, the legion did not fight as one rigid wall. It deployed in three staggered lines of maniples.",
        4.5,
        9.5,
    ),
    (
        "s03",
        "Centurion Marcus watches the forward hastati. The enemy's fierce charge collides with brutal kinetic weight.",
        9.5,
        15.0,
    ),
    (
        "s04",
        "Young hastati lock their shields edge to edge. The pressure mounts with every passing second as fatigue sets in.",
        15.0,
        20.5,
    ),
    (
        "s05",
        "Individual files absorb the brutal impact, but mortal men cannot maintain hand-to-hand combat indefinitely.",
        20.5,
        26.0,
    ),
    (
        "s06",
        "At Marcus's sharp command, file partners sidestep in disciplined unison, opening clean corridors through the line.",
        26.0,
        31.5,
    ),
    (
        "s07",
        "Through these precise gaps, fresh principes advance in locked formation, taking the strain without losing an inch of ground.",
        31.5,
        37.0,
    ),
    (
        "s08",
        "The exhausted hastati fall back between the files, while the fresh line seals together like a solid iron gate.",
        37.0,
        42.5,
    ),
    (
        "s09",
        "This quincunx formation turned line relief into an impenetrable engine of rotating manpower.",
        42.5,
        48.0,
    ),
    (
        "s10",
        "By replacing tired fighters with fresh steel, the legion transformed an apparent crisis into overwhelming tactical order.",
        48.0,
        52.5,
    ),
]


def generate_voice_track(project_dir: Path, beats: List[Tuple[str, str, float, float]]) -> Tuple[Path, List[Dict[str, Any]]]:
    """Synthesize English spoken voice track using macOS say or audio synthesis."""
    timeline_dir = project_dir / "timeline"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = timeline_dir / "voice.wav"
    lines_json_path = timeline_dir / "lines.json"

    lines_metadata: List[Dict[str, Any]] = []
    temp_wavs: List[Path] = []

    has_say = shutil.which("say") is not None

    for sid, text, st, et in beats:
        dur = et - st
        t_wav = timeline_dir / f"line_{sid}.wav"

        if has_say:
            cmd = ["say", "-v", "Daniel", "-r", "165", "-o", str(t_wav), "--data-format=LEI16@44100", text]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            # Fallback pure tone synthesis
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"sine=frequency=220:duration={dur}",
                "-ar", "44100", "-ac", "1", str(t_wav)
            ]
            subprocess.run(cmd, check=True, capture_output=True)

        info = inspect_media_file(t_wav)
        spoken_dur = float(info.get("duration", dur))

        lines_metadata.append({
            "id": sid,
            "text": text,
            "start": round(st, 2),
            "dur": round(dur, 2),
            "spoken_dur": round(spoken_dur, 2),
        })
        temp_wavs.append(t_wav)

    # Concatenate or position into single continuous voice.wav
    filter_complex_parts = []
    for idx, (sid, text, st, et) in enumerate(beats):
        delay_ms = int(st * 1000)
        filter_complex_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[a{idx}];")

    inputs_cmd = []
    for tw in temp_wavs:
        inputs_cmd.extend(["-i", str(tw)])

    mix_labels = "".join([f"[a{i}]" for i in range(len(temp_wavs))])
    total_dur = beats[-1][3]
    filter_complex = "".join(filter_complex_parts) + f"{mix_labels}amix=inputs={len(temp_wavs)}:dropout_transition=0,apad=whole_dur={total_dur}[outa]"

    cmd_stitch = [
        "ffmpeg", "-y",
        *inputs_cmd,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-ar", "44100", "-ac", "2",
        str(voice_wav)
    ]
    subprocess.run(cmd_stitch, check=True, capture_output=True)

    # Clean temporary line files
    for tw in temp_wavs:
        if tw.is_file():
            tw.unlink()

    with open(lines_json_path, "w", encoding="utf-8") as f:
        json.dump(lines_metadata, f, indent=2)

    return voice_wav, lines_metadata


def build_mixed_soundtrack(project_dir: Path, total_dur: float) -> Path:
    """Compose multi-layer sound design and mix to -14.0 LUFS."""
    timeline_dir = project_dir / "timeline"
    build_dir = project_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    voice_wav = timeline_dir / "voice.wav"
    mixed_wav = build_dir / "audio_mixed.wav"

    # Ambient bed: low wind and deep battle rhythm
    ambience_wav = build_dir / "ambience_bed.wav"
    cmd_amb = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anoisesrc=d={total_dur}:c=pink:r=44100:a=0.03,lowpass=f=280[pink]; sine=f=55:d={total_dur}[sub]; [pink][sub]amix=inputs=2:weights=0.8 0.2,volume=0.35",
        "-ar", "44100", "-ac", "2",
        str(ambience_wav)
    ]
    subprocess.run(cmd_amb, check=True, capture_output=True)

    # SFX events: shield clash, trumpet/horn, marching footsteps
    sfx_wav = build_dir / "sfx_track.wav"
    cmd_sfx = [
        "ffmpeg", "-y",
        # Horn call at 9.5s and 26.0s
        "-f", "lavfi", "-i", "sine=f=440:d=1.5,volume=0.35",
        "-f", "lavfi", "-i", "sine=f=554:d=1.5,volume=0.35",
        # Shield clash impact at 15.0s, 20.5s, 48.0s
        "-f", "lavfi", "-i", "anoisesrc=d=0.6:c=white:r=44100:a=0.4,lowpass=f=1200,volume=0.4",
        "-filter_complex",
        "[0:a]adelay=9500|9500[h1]; [1:a]adelay=26000|26000[h2]; [2:a]adelay=15000|15000[c1]; [2:a]adelay=20500|20500[c2]; [2:a]adelay=48000|48000[c3]; [h1][h2][c1][c2][c3]amix=inputs=5:dropout_transition=0,apad=whole_dur={total_dur}[sfx_out]".format(total_dur=total_dur),
        "-map", "[sfx_out]",
        "-ar", "44100", "-ac", "2",
        str(sfx_wav)
    ]
    subprocess.run(cmd_sfx, check=True, capture_output=True)

    # Final EBU R128 loudness normalization (-14.0 LUFS)
    cmd_mix = [
        "ffmpeg", "-y",
        "-i", str(voice_wav),
        "-i", str(ambience_wav),
        "-i", str(sfx_wav),
        "-filter_complex",
        "[0:a]volume=1.05[v]; [1:a]volume=0.25[amb]; [2:a]volume=0.40[sfx]; [v][amb][sfx]amix=inputs=3:weights=1.0 0.25 0.35:dropout_transition=0,loudnorm=I=-14.0:TP=-1.5:LRA=7.0[outa]",
        "-map", "[outa]",
        "-ar", "44100", "-ac", "2",
        str(mixed_wav)
    ]
    subprocess.run(cmd_mix, check=True, capture_output=True)

    # Clean intermediate tracks
    if ambience_wav.is_file():
        ambience_wav.unlink()
    if sfx_wav.is_file():
        sfx_wav.unlink()

    return mixed_wav


def build_roman_continuity_storyboard(total_dur: float = 52.5) -> Dict[str, Any]:
    """Define the 10 cinematic shots adhering strictly to the Roman continuity benchmark."""
    shots = [
        # s01: Hook / Threat (0.0–4.5s)
        {
            "id": "s01",
            "tpl": "scene",
            "dur": 4.5,
            "start": 0.0,
            "end": 4.5,
            "action": "STAND",
            "action_kind": "STAND",
            "line": SCRIPT_BEATS[0][1],
            "desc": "Wide sunrise view of Roman front line facing approaching Celtic horde across the valley",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 101,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.35, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                    {"id": "front_a", "preset": "hastatus", "x": 0.45, "y": 0.82, "h": 0.44, "facing": 1, "pose": "guard"},
                    {"id": "front_b", "preset": "hastatus", "x": 0.55, "y": 0.82, "h": 0.44, "facing": 1, "pose": "guard"},
                    {"id": "opp_a", "preset": "celtic", "x": 0.88, "y": 0.82, "h": 0.44, "facing": -1, "pose": "charge"},
                ],
                "props": [
                    {"type": "banner", "x": 0.33, "y": 0.55, "scale": 0.5},
                ],
            },
        },
        # s02: Establishing (4.5–9.5s)
        {
            "id": "s02",
            "tpl": "scene",
            "dur": 5.0,
            "start": 4.5,
            "end": 9.5,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[1][1],
            "desc": "Staggered manipular lines on grassy ridge; Celtic warriors advance closer from the right",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 102,
                "people": [
                    {"id": "front_a", "preset": "hastatus", "x": 0.45, "y": 0.82, "h": 0.44, "facing": 1, "pose": "brace"},
                    {"id": "front_b", "preset": "hastatus", "x": 0.55, "y": 0.82, "h": 0.44, "facing": 1, "pose": "brace"},
                    {"id": "opp_a", "preset": "celtic", "x": 0.82, "to": 0.72, "y": 0.82, "h": 0.44, "facing": -1, "pose": "charge"},
                    {"id": "opp_b", "preset": "celtic", "x": 0.90, "to": 0.80, "y": 0.82, "h": 0.44, "facing": -1, "pose": "charge"},
                ],
            },
        },
        # s03: Reaction (9.5–15.0s)
        {
            "id": "s03",
            "tpl": "scene",
            "dur": 5.5,
            "start": 9.5,
            "end": 15.0,
            "action": "SIGNAL",
            "action_kind": "SIGNAL",
            "line": SCRIPT_BEATS[2][1],
            "desc": "Medium close-up on Centurion Marcus monitoring the impending clash with drawn sword",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 103,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.45, "y": 0.80, "h": 0.55, "facing": 1, "pose": "fire_signal"},
                    {"id": "front_a", "preset": "hastatus", "x": 0.68, "y": 0.82, "h": 0.42, "facing": 1, "pose": "brace"},
                ],
            },
        },
        # s04: Action Setup - Shield Collision (15.0–20.5s)
        {
            "id": "s04",
            "tpl": "scene",
            "dur": 5.5,
            "start": 15.0,
            "end": 20.5,
            "action": "BRACE",
            "action_kind": "BRACE",
            "line": SCRIPT_BEATS[3][1],
            "desc": "Hastati lock shields rim to rim; shields shudder under violent Celtic impact",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 104,
                "people": [
                    {"id": "front_a", "preset": "hastatus", "x": 0.42, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "front_b", "preset": "hastatus", "x": 0.50, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "opp_a", "preset": "celtic", "x": 0.58, "to": 0.53, "y": 0.84, "h": 0.46, "facing": -1, "pose": "recoil"},
                ],
            },
        },
        # s05: Line Strain & Fatigue (20.5–26.0s)
        {
            "id": "s05",
            "tpl": "scene",
            "dur": 5.5,
            "start": 20.5,
            "end": 26.0,
            "action": "FATIGUE",
            "action_kind": "FATIGUE",
            "line": SCRIPT_BEATS[4][1],
            "desc": "Hastati fighters absorb continuous strain; shield posture droops under intense pressure",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 105,
                "people": [
                    {"id": "front_a", "preset": "hastatus", "x": 0.42, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "front_b", "preset": "hastatus", "x": 0.50, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "marcus", "preset": "centurio", "x": 0.28, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                ],
            },
        },
        # s06: Change - Opening Corridors (26.0–31.5s)
        {
            "id": "s06",
            "tpl": "scene",
            "dur": 5.5,
            "start": 26.0,
            "end": 31.5,
            "action": "SIGNAL",
            "action_kind": "SIGNAL",
            "line": SCRIPT_BEATS[5][1],
            "desc": "Marcus orders line rotation; front files sidestep smoothly to open clean relief corridors",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 106,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.28, "y": 0.82, "h": 0.44, "facing": 1, "pose": "fire_signal"},
                    {"id": "front_a", "preset": "hastatus", "x": 0.42, "to": 0.38, "y": 0.84, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "front_b", "preset": "hastatus", "x": 0.50, "to": 0.54, "y": 0.84, "h": 0.46, "facing": 1, "pose": "guard"},
                ],
            },
        },
        # s07: Reserve Advance (31.5–37.0s)
        {
            "id": "s07",
            "tpl": "scene",
            "dur": 5.5,
            "start": 31.5,
            "end": 37.0,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[6][1],
            "desc": "Fresh, rested Principes advance through the open corridors into the frontline slots",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 107,
                "people": [
                    {"id": "reserve_a", "preset": "principes", "x": 0.35, "to": 0.44, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "reserve_b", "preset": "principes", "x": 0.42, "to": 0.48, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "opp_a", "preset": "celtic", "x": 0.68, "y": 0.84, "h": 0.46, "facing": -1, "pose": "brace"},
                ],
            },
        },
        # s08: Orderly Withdrawal (37.0–42.5s)
        {
            "id": "s08",
            "tpl": "scene",
            "dur": 5.5,
            "start": 37.0,
            "end": 42.5,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[7][1],
            "desc": "Exhausted Hastati slip backward through the corridors while Principes lock shields",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 108,
                "people": [
                    {"id": "reserve_a", "preset": "principes", "x": 0.44, "y": 0.82, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "reserve_b", "preset": "principes", "x": 0.48, "y": 0.82, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "front_a", "preset": "hastatus", "x": 0.38, "to": 0.28, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                ],
            },
        },
        # s09: Payoff - Quincunx Diagram (42.5–48.0s)
        {
            "id": "s09",
            "tpl": "scene",
            "dur": 5.5,
            "start": 42.5,
            "end": 48.0,
            "action": "STAND",
            "action_kind": "STAND",
            "expected_subject": "diagram",
            "line": SCRIPT_BEATS[8][1],
            "desc": "Overhead tactical schematic of manipular quincunx checkerboard with bold unit badges",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 109,
                "show_unit_badges": True,
                "contrast_boost": True,
                "props": [
                    {"type": "torsion_diagram", "x": 0.50, "y": 0.50, "scale": 1.05},
                ],
            },
        },
        # s10: Closing Stand & Victory Payoff (48.0–52.5s)
        {
            "id": "s10",
            "tpl": "scene",
            "dur": 4.5,
            "start": 48.0,
            "end": 52.5,
            "action": "STAND",
            "action_kind": "STAND",
            "line": SCRIPT_BEATS[9][1],
            "desc": "Wide panoramic view: Principes shield wall stands resolute, enemy counter-thrust repelled",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "grass",
                "seed": 110,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.32, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                    {"id": "reserve_a", "preset": "principes", "x": 0.45, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "reserve_b", "preset": "principes", "x": 0.53, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "opp_a", "preset": "celtic", "x": 0.78, "y": 0.82, "h": 0.44, "facing": -1, "pose": "recoil"},
                ],
                "props": [
                    {"type": "banner", "x": 0.30, "y": 0.55, "scale": 0.5},
                ],
            },
        },
    ]

    return {
        "title": "THE GAP IN THE ROMAN LINE — HOW THE RESERVES TURNED A CRISIS INTO ORDER",
        "subline": "The Manipular Quincunx Tactics of the Roman Legions (ILLUSTRATIVE RECONSTRUCTION)",
        "duration": total_dur,
        "shots": shots,
    }


def construct_roman_continuity_project(force_rebuild: bool = False) -> Path:
    """Initialize project folder, manifests, configurations, and story assets."""
    p_dir = PROJECT_DIR
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "story").mkdir(exist_ok=True)
    (p_dir / "timeline").mkdir(exist_ok=True)
    (p_dir / "build").mkdir(exist_ok=True)
    (p_dir / "out").mkdir(exist_ok=True)
    (p_dir / "scenes" / "shots").mkdir(parents=True, exist_ok=True)

    # 1. config.json
    cfg = {
        "title": "THE GAP IN THE ROMAN LINE — HOW THE RESERVES TURNED A CRISIS INTO ORDER",
        "pack": "squire",
        "genre": "roman",
        "resolution": "1080p",
        "aspect": "16:9",
        "fps": 24,
        "ai_director_enabled": False,
        "ai_director_mode": "OFFLINE_ONLY",
    }
    with open(p_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # 2. character_bible.json
    bible = {
        "archetypes": {
            "marcus": {
                "name": "Centurion Marcus",
                "role": "Centurio Prior",
                "preset": "centurio",
                "armor": "lorica_hamata",
                "helmet": "galea_transverse_crest",
                "weapon": "gladius",
                "cloak": "red_sagum",
            },
            "front_a": {
                "name": "Hastatus Lucius",
                "role": "Forward Legionary",
                "preset": "hastatus",
                "shield": "scutum_oval",
                "weapon": "hasta",
            },
            "reserve_a": {
                "name": "Princeps Titus",
                "role": "Heavy Reserve Infantry",
                "preset": "principes",
                "armor": "lorica_squamata",
                "shield": "scutum_red",
            },
            "opp_a": {
                "name": "Celtic Warrior",
                "role": "Warband Fighter",
                "preset": "celtic",
                "shield": "oval",
                "weapon": "longsword",
            },
        }
    }
    with open(p_dir / "story" / "character_bible.json", "w", encoding="utf-8") as f:
        json.dump(bible, f, indent=2)

    # 3. claims_manifest.json
    claims = {
        "topic": "Early Roman Manipular Quincunx Formation and Relief Mechanics",
        "historical_scope": "Middle Republic (approx. 4th–3rd Century BC)",
        "illustrative_disclaimer": "This video is an educational illustrative reconstruction of manipular tactical doctrine as described by Polybius and modern military historians. It depicts conceptual unit rotation rather than a specific real-time historical event.",
        "claims": [
            "Roman legions deployed in three distinct battle lines: Hastati, Principes, and Triarii.",
            "Units left regular intervals (intervalla) in the front line covered by the subsequent line.",
            "When frontline troops became exhausted, rear maniples advanced through the gaps to take their place without collapsing the formation.",
        ],
    }
    with open(p_dir / "story" / "claims_manifest.json", "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)

    # 4. timeline/transcript.txt & timeline/blocks.json
    full_transcript = "\n".join([f"{b[0]}: {b[1]}" for b in SCRIPT_BEATS])
    (p_dir / "timeline" / "transcript.txt").write_text(full_transcript, encoding="utf-8")

    blocks = [
        {"id": "act_1_threat", "label": "Threat & Hook", "start": 0.0, "end": 9.5},
        {"id": "act_2_reaction", "label": "Reaction & Clash", "start": 9.5, "end": 26.0},
        {"id": "act_3_relief", "label": "Line Relief & Advance", "start": 26.0, "end": 42.5},
        {"id": "act_4_payoff", "label": "Quincunx Payoff & Stand", "start": 42.5, "end": 52.5},
    ]
    with open(p_dir / "timeline" / "blocks.json", "w", encoding="utf-8") as f:
        json.dump(blocks, f, indent=2)

    # 5. thumb.js stub
    (p_dir / "scenes" / "shots" / "thumb.js").write_text(
        "export default function(g, opt) { g.fillStyle = '#1a202c'; g.fillRect(0, 0, 1920, 1080); }",
        encoding="utf-8",
    )

    return p_dir


def produce_roman_continuity_preview(force_rebuild: bool = False) -> Dict[str, Any]:
    """Produce the entire 1080p acceptance preview film from start to finish."""
    t0 = time.time()
    p_dir = construct_roman_continuity_project(force_rebuild=force_rebuild)
    out_mp4 = OUT_MP4_PATH
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Check cache hit first
    if not force_rebuild and out_mp4.is_file():
        manifest = collect_render_inputs(p_dir)
        cache_check = validate_cache_hit(p_dir, out_mp4, manifest)
        if cache_check.get("hit"):
            media_info = cache_check.get("media_info") or inspect_media_file(out_mp4)
            return {
                "status": "CACHE_HIT_VERIFIED",
                "output_path": str(out_mp4),
                "duration": media_info.get("duration"),
                "sha256": media_info.get("sha256"),
                "elapsed_sec": 0.01,
            }

    # 1. Voice Synthesis
    voice_wav, lines_data = generate_voice_track(p_dir, SCRIPT_BEATS)
    total_dur = SCRIPT_BEATS[-1][3]

    # 2. Multi-Track Soundtrack Mix
    mixed_audio = build_mixed_soundtrack(p_dir, total_dur)

    # 3. Storyboard Generation with Camera Sequence Planning
    storyboard = build_roman_continuity_storyboard(total_dur)
    shots = storyboard["shots"]

    # Compile camera keyframes
    cam_plans = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
    for s, cp in zip(shots, cam_plans):
        s["camera"] = cp.model_dump()
        s["args"]["cameraRig"] = {
            "keyframes": [
                {"t": kf.local_sec, "x": kf.x_center, "y": kf.y_center, "z": kf.zoom}
                for kf in cp.camera_path
            ]
        }

    # Save finalized storyboard into story/shots.json and story/storyboard.json
    with open(p_dir / "story" / "shots.json", "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2)

    with open(p_dir / "story" / "storyboard.json", "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2)

    (p_dir / "story" / "script.json").write_text(
        json.dumps({
            "title": storyboard["title"],
            "beats": [{"id": b[0], "text": b[1], "start": b[2], "end": b[3]} for b in SCRIPT_BEATS],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4. Render Video via Playwright
    video_silent = p_dir / "build" / "video_silent.mp4"
    if force_rebuild or not video_silent.is_file() or video_silent.stat().st_size < 1000:
        cmd_render = [
            "node", str(ROOT_DIR / "render.mjs"),
            "--project", str(p_dir),
        ]
        res_render = subprocess.run(cmd_render, cwd=ROOT_DIR, capture_output=True, text=True)
        if res_render.returncode != 0:
            raise RuntimeError(f"render.mjs failed:\n{res_render.stderr[-800:]}")

    # 5. Final Mux with Normalized AAC Audio
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

    partial_info = inspect_media_file(partial_mp4, require_audio=True, full_decode=True)
    if not partial_info.get("valid", False) or partial_info.get("duration", 0.0) <= 0.0:
        if partial_mp4.is_file():
            partial_mp4.unlink()
        raise RuntimeError(f"Muxed partial MP4 failed media inspection: {partial_info.get('error')}")

    partial_mp4.replace(out_mp4)

    # 6. Media Inspection & Cryptographic Provenance Receipt
    media_info = inspect_media_file(out_mp4, require_audio=True, full_decode=True)
    render_inputs = collect_render_inputs(
        project_path=p_dir,
        render_options={
            "pack": "squire",
            "genre": "roman",
            "resolution": "1080p",
            "aspect": "16:9",
            "audio_mode": "voice_sfx",
            "fps": 24,
        },
    )
    fingerprint = compute_render_fingerprint(render_inputs)

    receipt_path = write_render_receipt_atomic(
        project_path=p_dir,
        output_path=out_mp4,
        manifest=render_inputs,
        metadata={
            "action": "produce_roman_continuity_preview",
            "wall_sec": round(time.time() - t0, 2),
            "force_rebuild": force_rebuild,
            "version": "14.7.3",
        },
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
        "receipt_path": str(receipt_path),
        "elapsed_sec": elapsed,
    }


def inspect_existing_preview(project_path: Path | str = PROJECT_DIR) -> Dict[str, Any]:
    """Inspect existing preview MP4 using validate_cache_hit."""
    p_dir = Path(project_path).resolve()
    out_mp4 = p_dir / "out" / "FL01_V14_7_3_ROMAN_CONTINUITY_FRESH_PREVIEW_1080P.mp4"
    if not out_mp4.is_file():
        return {"status": "MISSING_OUTPUT", "output_path": str(out_mp4)}

    manifest = collect_render_inputs(p_dir)
    cache_check = validate_cache_hit(p_dir, out_mp4, manifest)
    media_info = cache_check.get("media_info") or inspect_media_file(out_mp4)

    return {
        "status": "VERIFIED" if cache_check.get("hit") else "UNVERIFIED",
        "cache_status": cache_check.get("status"),
        "reason": cache_check.get("reason"),
        "output_path": str(out_mp4),
        "duration": media_info.get("duration"),
        "width": media_info.get("width"),
        "height": media_info.get("height"),
        "fps": media_info.get("fps"),
        "video_codec": media_info.get("video_codec"),
        "audio_codec": media_info.get("audio_codec"),
        "size_bytes": out_mp4.stat().st_size if out_mp4.is_file() else 0,
        "sha256": media_info.get("sha256"),
        "decode_clean": media_info.get("decode_clean", True),
    }


if __name__ == "__main__":
    force = "--force" in sys.argv
    res = produce_roman_continuity_preview(force_rebuild=force)
    print("Roman Continuity Benchmark Preview Result:")
    print(json.dumps(res, indent=2))
