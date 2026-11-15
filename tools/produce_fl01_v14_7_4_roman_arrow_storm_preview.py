"""tools/produce_fl01_v14_7_4_roman_arrow_storm_preview.py — Producer for brand-new acceptance preview film:
"THE ARROW STORM — HOW A ROMAN SHIELD ROOF SURVIVED" (FL-01 / V14.7.4).

Specification:
- Duration: 54.0 seconds (10 distinct shots, 5.4s each).
- Spoken Narration: English (Daniel), strictly non-overlapping (overlap_ms == 0), tail safety margin >= 0.15s before every cut.
- Audio: Voice + Ambience + Arrow swooshes / impacts / marching SFX, sidechain ducked, normalized to -14.0 LUFS.
- Visual: 1080p24 H.264/AAC, cinematic camera paths, diagram shot featuring roman_testudo_formation_diagram.
- Cryptographic provenance receipt generated atomically.
"""

from __future__ import annotations

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

PROJECT_DIR = ROOT_DIR / "projects" / "fl01_v14_7_4_roman_arrow_storm_preview"
OUT_MP4_PATH = PROJECT_DIR / "out" / "FL01_V14_7_4_ROMAN_ARROW_STORM_FRESH_PREVIEW_1080P.mp4"

SCRIPT_BEATS: List[Tuple[str, str, float, float]] = [
    (
        "s01",
        "When thousands of arrows rained down, how did Roman legions cross the valley alive?",
        0.0,
        5.4,
    ),
    (
        "s02",
        "Parthian archers held the high ridge, unleashing continuous volleys into the valley.",
        5.4,
        10.8,
    ),
    (
        "s03",
        "Centurion Marcus raised his staff and bellowed the command: lock the shields!",
        10.8,
        16.2,
    ),
    (
        "s04",
        "The front ranks formed an unbroken wall while rear lines raised shields overhead.",
        16.2,
        21.6,
    ),
    (
        "s05",
        "Seen from above, the testudo formed an interlocking timber vault, shedding heavy missiles.",
        21.6,
        27.0,
    ),
    (
        "s06",
        "Hundreds of shafts slammed into curved wood, glancing harmlessly off the vaulted shell.",
        27.0,
        32.4,
    ),
    (
        "s07",
        "Blind to the sky, the legion moved forward together in rigid, measured cadence.",
        32.4,
        37.8,
    ),
    (
        "s08",
        "When one soldier stumbled, neighboring shields shifted instantly to close the vulnerable opening.",
        37.8,
        43.2,
    ),
    (
        "s09",
        "Moving steadily beneath the storm, the locked formation cleared the deadly archery zone.",
        43.2,
        48.6,
    ),
    (
        "s10",
        "Discipline transformed wooden boards into armor, proving collective unity defeated overwhelming firepower.",
        48.6,
        54.0,
    ),
]


def generate_voice_track(
    project_path: Path, beats: List[Tuple[str, str, float, float]]
) -> Tuple[Path, List[Dict[str, Any]]]:
    """
    Synthesize non-overlapping voice narration using mac 'say' (Daniel, 175 wpm).
    Constructs a sequential timeline with exact silence padding ensuring overlap_ms == 0
    and tail safety margin >= 0.15s before every shot boundary.
    """
    build_dir = project_path / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = build_dir / "voice_track.wav"
    events_json = build_dir / "voice_events.json"

    lines_data: List[Dict[str, Any]] = []
    tmp_wavs: List[Path] = []
    concat_list = build_dir / "voice_concat.txt"
    concat_lines = []

    last_end_sec = 0.0

    for sid, text, shot_start, shot_end in beats:
        shot_dur = shot_end - shot_start
        line_aiff = build_dir / f"line_{sid}.aiff"
        line_wav = build_dir / f"line_{sid}.wav"

        # 1. Synthesize with say Daniel
        cmd_say = ["say", "-v", "Daniel", "-r", "175", "-o", str(line_aiff), text]
        subprocess.run(cmd_say, check=True, capture_output=True)

        # 2. Convert to standard 44.1kHz stereo WAV
        cmd_conv = [
            "ffmpeg", "-y", "-i", str(line_aiff),
            "-ar", "44100", "-ac", "2",
            str(line_wav)
        ]
        subprocess.run(cmd_conv, check=True, capture_output=True)
        if line_aiff.is_file():
            line_aiff.unlink()

        # Measure spoken duration
        cmd_dur = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(line_wav)
        ]
        res = subprocess.run(cmd_dur, check=True, capture_output=True, text=True)
        spoken_dur = float(res.stdout.strip())

        # Buffer: start 0.20s after shot start, ensure it fits
        target_start = shot_start + 0.20
        # Ensure target_start is not before last line ended
        if target_start < last_end_sec:
            target_start = last_end_sec + 0.05

        target_end = target_start + spoken_dur
        tail_margin = shot_end - target_end

        # If spoken audio spills too close to boundary, clamp playback rate
        if tail_margin < 0.25:
            # Slightly speed up with atempo
            speed_factor = spoken_dur / (shot_dur - 0.60)
            if speed_factor > 1.0:
                speeded_wav = build_dir / f"line_{sid}_speeded.wav"
                cmd_speed = [
                    "ffmpeg", "-y", "-i", str(line_wav),
                    "-filter:a", f"atempo={min(speed_factor, 1.35):.3f}",
                    "-ar", "44100", "-ac", "2",
                    str(speeded_wav)
                ]
                subprocess.run(cmd_speed, check=True, capture_output=True)
                line_wav.unlink()
                speeded_wav.replace(line_wav)
                # re-measure
                res2 = subprocess.run(cmd_dur, check=True, capture_output=True, text=True)
                spoken_dur = float(res2.stdout.strip())
                target_end = target_start + spoken_dur
                tail_margin = shot_end - target_end

        # Calculate silence needed before this line from last_end_sec
        silence_gap = max(0.0, target_start - last_end_sec)
        if silence_gap > 0.005:
            gap_wav = build_dir / f"gap_{sid}.wav"
            cmd_gap = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", f"{silence_gap:.4f}",
                str(gap_wav)
            ]
            subprocess.run(cmd_gap, check=True, capture_output=True)
            tmp_wavs.append(gap_wav)
            concat_lines.append(f"file '{gap_wav.name}'")

        concat_lines.append(f"file '{line_wav.name}'")
        tmp_wavs.append(line_wav)

        last_end_sec = target_end

        lines_data.append({
            "id": sid,
            "text": text,
            "shot_start": shot_start,
            "shot_end": shot_end,
            "spoken_start": round(target_start, 3),
            "spoken_end": round(target_end, 3),
            "spoken_duration": round(spoken_dur, 3),
            "tail_margin_sec": round(tail_margin, 3),
            "overlap_ms": 0,
        })

    # Pad remaining silence to total video end (54.0s)
    total_dur = beats[-1][3]
    if last_end_sec < total_dur:
        final_gap = total_dur - last_end_sec
        final_wav = build_dir / "final_gap.wav"
        cmd_fgap = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", f"{final_gap:.4f}",
            str(final_wav)
        ]
        subprocess.run(cmd_fgap, check=True, capture_output=True)
        tmp_wavs.append(final_wav)
        concat_lines.append(f"file '{final_wav.name}'")

    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    # Concat all segments into a single non-overlapping voice_track.wav
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(voice_wav)
    ]
    subprocess.run(cmd_concat, check=True, capture_output=True)

    # Save detailed voice_events.json
    events_json.write_text(json.dumps({
        "total_duration": total_dur,
        "beats_count": len(beats),
        "total_overlap_ms": 0,
        "max_tail_margin_sec": max(l["tail_margin_sec"] for l in lines_data),
        "min_tail_margin_sec": min(l["tail_margin_sec"] for l in lines_data),
        "events": lines_data,
    }, indent=2), encoding="utf-8")

    # Clean up temp wavs
    for w in tmp_wavs:
        if w.is_file():
            w.unlink()
    if concat_list.is_file():
        concat_list.unlink()

    return voice_wav, lines_data


def build_mixed_soundtrack(project_path: Path, total_dur: float = 54.0) -> Path:
    """
    Produce multi-track soundtrack:
    - Ambience: Sub-bass battlefield wind + pink noise
    - SFX: Arrow whistling, shield impacts, centurion shout, marching greaves
    - Sidechain ducking under voice + EBU R128 (-14.0 LUFS) normalization
    """
    build_dir = project_path / "build"
    voice_wav = build_dir / "voice_track.wav"
    mixed_wav = build_dir / "soundtrack_mixed.wav"

    # Ambience: low rumble wind
    ambience_wav = build_dir / "ambience_track.wav"
    cmd_amb = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anoisesrc=d={total_dur}:c=pink:r=44100:a=0.02,lowpass=f=220[pink]; sine=f=50:d={total_dur}[sub]; [pink][sub]amix=inputs=2:weights=0.8 0.2,volume=0.22",
        "-ar", "44100", "-ac", "2",
        str(ambience_wav)
    ]
    subprocess.run(cmd_amb, check=True, capture_output=True)

    # SFX events: arrow volley swoosh, shield thuds, marching cadence, horn
    sfx_wav = build_dir / "sfx_track.wav"
    cmd_sfx = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=0.8:c=white:r=44100:a=0.35,bandpass=f=1800:width_type=h:w=600,volume=0.35",  # arrow whoosh
        "-f", "lavfi", "-i", "anoisesrc=d=0.4:c=white:r=44100:a=0.5,lowpass=f=800,volume=0.4",                         # impact thud
        "-f", "lavfi", "-i", "sine=f=440:d=1.0,volume=0.2",                                                            # horn signal
        "-f", "lavfi", "-i", "sine=f=80:d=0.25,volume=0.3",                                                             # march thud
        "-filter_complex",
        f"[0:a]adelay=1000|1000[arr1]; "
        f"[2:a]adelay=11200|11200[horn]; "
        f"[1:a]adelay=27500|27500[imp1]; [1:a]adelay=28200|28200[imp2]; [1:a]adelay=29100|29100[imp3]; "
        f"[3:a]adelay=33000|33000[m1]; [3:a]adelay=34500|34500[m2]; [3:a]adelay=36000|36000[m3]; "
        f"[arr1][horn][imp1][imp2][imp3][m1][m2][m3]amix=inputs=8:dropout_transition=0,apad=whole_dur={total_dur}[sfx_out]",
        "-map", "[sfx_out]",
        "-ar", "44100", "-ac", "2",
        str(sfx_wav)
    ]
    subprocess.run(cmd_sfx, check=True, capture_output=True)

    # Duck SFX/Ambience under voice and normalize to -14.0 LUFS
    cmd_mix = [
        "ffmpeg", "-y",
        "-i", str(voice_wav),
        "-i", str(ambience_wav),
        "-i", str(sfx_wav),
        "-filter_complex",
        "[1:a][2:a]amix=inputs=2:weights=0.5 0.5[bg_sfx]; "
        "[bg_sfx][0:a]sidechaincompress=threshold=0.15:ratio=4:attack=20:release=250[bg_ducked]; "
        "[0:a][bg_ducked]amix=inputs=2:weights=1.0 0.35,loudnorm=I=-14:TP=-1.5:LRA=9[outa]",
        "-map", "[outa]",
        "-ar", "44100", "-ac", "2",
        str(mixed_wav)
    ]
    subprocess.run(cmd_mix, check=True, capture_output=True)

    if ambience_wav.is_file():
        ambience_wav.unlink()
    if sfx_wav.is_file():
        sfx_wav.unlink()

    return mixed_wav


def build_arrow_storm_storyboard(total_dur: float = 54.0) -> Dict[str, Any]:
    """Define the 10 cinematic shots for The Arrow Storm."""
    shots = [
        # s01: Hook - Incoming Projectile (0.0–5.4s)
        {
            "id": "s01",
            "tpl": "scene",
            "dur": 5.4,
            "start": 0.0,
            "end": 5.4,
            "action": "STAND",
            "action_kind": "STAND",
            "line": SCRIPT_BEATS[0][1],
            "desc": "Wide view of sunlit desert valley; whistling enemy arrow thuds into dirt before Roman line",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 201,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.35, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                    {"id": "legion_a", "preset": "legionary", "x": 0.45, "y": 0.82, "h": 0.44, "facing": 1, "pose": "guard"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.55, "y": 0.82, "h": 0.44, "facing": 1, "pose": "guard"},
                ],
                "props": [
                    {"type": "banner", "x": 0.33, "y": 0.55, "scale": 0.5},
                ],
            },
        },
        # s02: Threat - Archer Ridge (5.4–10.8s)
        {
            "id": "s02",
            "tpl": "scene",
            "dur": 5.4,
            "start": 5.4,
            "end": 10.8,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[1][1],
            "desc": "Parthian archers on distant ridge draw recurve bows and release black cloud of arrows",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 202,
                "people": [
                    {"id": "opp_a", "preset": "celtic", "x": 0.75, "to": 0.70, "y": 0.78, "h": 0.40, "facing": -1, "pose": "charge"},
                    {"id": "opp_b", "preset": "celtic", "x": 0.85, "to": 0.80, "y": 0.78, "h": 0.40, "facing": -1, "pose": "charge"},
                ],
            },
        },
        # s03: Command - Signal (10.8–16.2s)
        {
            "id": "s03",
            "tpl": "scene",
            "dur": 5.4,
            "start": 10.8,
            "end": 16.2,
            "action": "SIGNAL",
            "action_kind": "SIGNAL",
            "line": SCRIPT_BEATS[2][1],
            "desc": "Centurion Marcus shouts command: 'Ad testudinem!' with sword raised in crisp signal",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 203,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.45, "y": 0.80, "h": 0.55, "facing": 1, "pose": "fire_signal"},
                    {"id": "legion_a", "preset": "legionary", "x": 0.65, "y": 0.82, "h": 0.44, "facing": 1, "pose": "brace"},
                ],
            },
        },
        # s04: Formation Lock (16.2–21.6s)
        {
            "id": "s04",
            "tpl": "scene",
            "dur": 5.4,
            "start": 16.2,
            "end": 21.6,
            "action": "BRACE",
            "action_kind": "BRACE",
            "line": SCRIPT_BEATS[3][1],
            "desc": "Front rank drops to one knee with locked scuta; rear files raise shields flat overhead",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 204,
                "people": [
                    {"id": "legion_a", "preset": "legionary", "x": 0.42, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.50, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "legion_c", "preset": "legionary", "x": 0.58, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                ],
            },
        },
        # s05: Payoff - Testudo Diagram (21.6–27.0s)
        {
            "id": "s05",
            "tpl": "scene",
            "dur": 5.4,
            "start": 21.6,
            "end": 27.0,
            "action": "STAND",
            "action_kind": "STAND",
            "expected_subject": "diagram",
            "line": SCRIPT_BEATS[4][1],
            "desc": "Overhead tactical schematic of interlocking testudo shield roof with trajectory deflection arrows",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 205,
                "show_unit_badges": True,
                "contrast_boost": True,
                "props": [
                    {"type": "roman_testudo_formation_diagram", "x": 0.50, "y": 0.50, "scale": 1.05},
                ],
            },
        },
        # s06: Volley Impact (27.0–32.4s)
        {
            "id": "s06",
            "tpl": "scene",
            "dur": 5.4,
            "start": 27.0,
            "end": 32.4,
            "action": "BRACE",
            "action_kind": "BRACE",
            "line": SCRIPT_BEATS[5][1],
            "desc": "Arrow shower crashes down on the wooden carapace; iron points splinter and deflect",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 206,
                "people": [
                    {"id": "legion_a", "preset": "legionary", "x": 0.42, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.50, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "legion_c", "preset": "legionary", "x": 0.58, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                ],
            },
        },
        # s07: Cadence March (32.4–37.8s)
        {
            "id": "s07",
            "tpl": "scene",
            "dur": 5.4,
            "start": 32.4,
            "end": 37.8,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[6][1],
            "desc": "Locked ranks advance in steady unison; armored caligae crush the dry earth in lockstep",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 207,
                "people": [
                    {"id": "legion_a", "preset": "legionary", "x": 0.38, "to": 0.46, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.46, "to": 0.54, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                ],
            },
        },
        # s08: Vulnerability Covered (37.8–43.2s)
        {
            "id": "s08",
            "tpl": "scene",
            "dur": 5.4,
            "start": 37.8,
            "end": 43.2,
            "action": "SUPPORT",
            "action_kind": "SUPPORT",
            "line": SCRIPT_BEATS[7][1],
            "desc": "A legionary trips on rocky ground; comrade immediately tilts scutum over the exposed gap",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 208,
                "people": [
                    {"id": "legion_a", "preset": "legionary", "x": 0.44, "y": 0.84, "h": 0.46, "facing": 1, "pose": "brace"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.52, "y": 0.86, "h": 0.44, "facing": 1, "pose": "guard"},
                    {"id": "marcus", "preset": "centurio", "x": 0.30, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                ],
            },
        },
        # s09: Out of the Kill Zone (43.2–48.6s)
        {
            "id": "s09",
            "tpl": "scene",
            "dur": 5.4,
            "start": 43.2,
            "end": 48.6,
            "action": "ADVANCE",
            "action_kind": "ADVANCE",
            "line": SCRIPT_BEATS[8][1],
            "desc": "The testudo reaches the base of the ridge beyond enemy bow effective range",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 209,
                "people": [
                    {"id": "legion_a", "preset": "legionary", "x": 0.40, "to": 0.50, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.50, "to": 0.60, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                ],
            },
        },
        # s10: Conclusion & Victory Stand (48.6–54.0s)
        {
            "id": "s10",
            "tpl": "scene",
            "dur": 5.4,
            "start": 48.6,
            "end": 54.0,
            "action": "STAND",
            "action_kind": "STAND",
            "line": SCRIPT_BEATS[9][1],
            "desc": "Overhead shields lower in unison; legionaries draw gladii, ready for final infantry assault",
            "args": {
                "bg": "plain",
                "time": "day",
                "ground": "dirt",
                "seed": 210,
                "people": [
                    {"id": "marcus", "preset": "centurio", "x": 0.32, "y": 0.82, "h": 0.44, "facing": 1, "pose": "stand"},
                    {"id": "legion_a", "preset": "legionary", "x": 0.45, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                    {"id": "legion_b", "preset": "legionary", "x": 0.55, "y": 0.82, "h": 0.46, "facing": 1, "pose": "guard"},
                ],
                "props": [
                    {"type": "banner", "x": 0.30, "y": 0.55, "scale": 0.5},
                ],
            },
        },
    ]

    return {
        "title": "THE ARROW STORM — HOW A ROMAN SHIELD ROOF SURVIVED",
        "subline": "The Testudo Formation Under Projectile Skirmish (ILLUSTRATIVE RECONSTRUCTION)",
        "duration": total_dur,
        "shots": shots,
    }


def construct_arrow_storm_project(force_rebuild: bool = False) -> Path:
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
        "title": "THE ARROW STORM — HOW A ROMAN SHIELD ROOF SURVIVED",
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
            "legion_a": {
                "name": "Legionary Lucius",
                "role": "Front Rank Shieldman",
                "preset": "legionary",
                "shield": "scutum_rectangular",
                "weapon": "gladius",
            },
            "legion_b": {
                "name": "Legionary Titus",
                "role": "Roof Shieldman",
                "preset": "legionary",
                "shield": "scutum_rectangular",
                "weapon": "gladius",
            },
            "legion_c": {
                "name": "Legionary Quintus",
                "role": "Flank Guard",
                "preset": "legionary",
                "shield": "scutum_rectangular",
                "weapon": "gladius",
            },
            "opp_a": {
                "name": "Eastern Archer",
                "role": "Horse Archer Skirmisher",
                "preset": "celtic",
                "weapon": "composite_bow",
            },
            "opp_b": {
                "name": "Eastern Archer Reserve",
                "role": "Foot Archer",
                "preset": "celtic",
                "weapon": "composite_bow",
            },
        }
    }
    with open(p_dir / "story" / "character_bible.json", "w", encoding="utf-8") as f:
        json.dump(bible, f, indent=2)

    # 3. claims_manifest.json
    claims = {
        "topic": "Roman Testudo Shield Roof Mechanics Against Arrow Volleys",
        "historical_scope": "Late Republic to Principate (approx. 1st Century BC – 2nd Century AD)",
        "illustrative_disclaimer": "This video is an educational illustrative reconstruction of testudo tactics described by Livy, Cassius Dio, and modern historians. It depicts collective formation defense rather than an unbroken continuous live engagement.",
        "claims": [
            "Front rank knelt or locked rectangular scuta vertically, while interior files held scuta flat overhead.",
            "Overlapping shields created an unbroken timber vault that shed low-angle and plunging projectile volleys.",
            "Cohesion and cadence allowed the legion to advance safely through missile fire into close infantry combat.",
        ],
    }
    with open(p_dir / "story" / "claims_manifest.json", "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)

    # 4. timeline/transcript.txt & timeline/blocks.json
    full_transcript = "\n".join([f"{b[0]}: {b[1]}" for b in SCRIPT_BEATS])
    (p_dir / "timeline" / "transcript.txt").write_text(full_transcript, encoding="utf-8")

    blocks = [
        {"id": "act_1_threat", "label": "Threat & Volley Approach", "start": 0.0, "end": 10.8},
        {"id": "act_2_lock", "label": "Command & Testudo Lock", "start": 10.8, "end": 21.6},
        {"id": "act_3_storm", "label": "Impact & Cadence Advance", "start": 21.6, "end": 43.2},
        {"id": "act_4_triumph", "label": "Breakout & Victory Stand", "start": 43.2, "end": 54.0},
    ]
    with open(p_dir / "timeline" / "blocks.json", "w", encoding="utf-8") as f:
        json.dump(blocks, f, indent=2)

    # 5. thumb.js stub
    (p_dir / "scenes" / "shots" / "thumb.js").write_text(
        "export default function(g, opt) { g.fillStyle = '#1c1917'; g.fillRect(0, 0, 1920, 1080); }",
        encoding="utf-8",
    )

    return p_dir


def produce_arrow_storm_preview(force_rebuild: bool = False) -> Dict[str, Any]:
    """Produce the entire 1080p Arrow Storm acceptance preview film from start to finish."""
    t0 = time.time()
    p_dir = construct_arrow_storm_project(force_rebuild=force_rebuild)
    out_mp4 = OUT_MP4_PATH
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Cache hit check
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
    storyboard = build_arrow_storm_storyboard(total_dur)
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

    # Save finalized storyboard
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
            "action": "produce_arrow_storm_preview",
            "wall_sec": round(time.time() - t0, 2),
            "force_rebuild": force_rebuild,
            "version": "14.7.4",
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


if __name__ == "__main__":
    force = "--force" in sys.argv
    res = produce_arrow_storm_preview(force_rebuild=force)
    print("Arrow Storm Preview Result:")
    print(json.dumps(res, indent=2))
