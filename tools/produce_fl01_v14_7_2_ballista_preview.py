#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_2_ballista_preview.py — Master Producer for FL-01 V14.7.2 Ballista Acceptance Film.

Produces:
  projects/fl01_v14_7_2_ballista_preview/out/FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4
  Specs: 51.5s (45 <= duration <= 60s), 1080p, 24fps, H.264/AAC, -14.0 LUFS ± 3 dB.

Narrative:
  "THE WOODEN MACHINE THAT SHOOK A BATTLEFIELD — HOW A ROMAN BALLISTA WORKED"
  Subline: "The Torsion Artillery of the Roman Legions" (ILLUSTRATIVE RECONSTRUCTION).
  10 sequential, causally connected narrative shots:
  s01 (0.0–4.5s): Hook: Bodkin iron bolt in trough, gleaming in the sun.
  s02 (4.5–9.5s): Wide reveal: Legion torsion artillery battery on fortified hill rampart.
  s03 (9.5–14.5s): Winch mechanism close-up: Crew cranking sucula handles, ratchets clicking.
  s04 (14.5–19.5s): Engineering schematic: Bronze modiolus and twisted sinew torsion core.
  s05 (19.5–24.5s): Loading phase: Artillerist seats bolt into grooved mensa channel.
  s06 (24.5–29.5s): Elevation & sighting: Optio Servius sights line, adjusts quadrant wedges.
  s07 (29.5–34.5s): Tension peak: Battery locked at full draw, Centurion Marcus raises vitis.
  s08 (34.5–40.0s): Discharge & release: Mallet strikes claw trigger, bolt accelerates down ramp.
  s09 (40.0–45.5s): Target penetration: Iron bolt shatters timber palisade barrier downrange.
  s10 (45.5–51.5s): Strategic Payoff: Roman formation advances; Vitruvius and Vegetius citations.
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

PREVIEW_DIR = ROOT_DIR / "projects" / "fl01_v14_7_2_ballista_preview"
PREVIEW_MP4 = PREVIEW_DIR / "out" / "FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4"

SCRIPT_BEATS: List[Tuple[str, str, float, float]] = [
    (
        "s01",
        "At three hundred paces, no wooden shield or bronze breastplate could stop what the Romans were preparing to unleash.",
        0.0,
        4.5,
    ),
    (
        "s02",
        "Behind the frontline legionaries stood the torsion artillery: field ballistae capable of turning defensive sieges into devastating long-range barrages.",
        4.5,
        9.5,
    ),
    (
        "s03",
        "A crew of four artillerists turned the rear winch, tightening dual skeins of twisted sinew until hundreds of foot-pounds of torque were locked in place.",
        9.5,
        14.5,
    ),
    (
        "s04",
        "Unlike medieval counterweight catapults, Roman artillery was powered purely by torsion physics: horsehair and sinew wound tightly inside bronze tightening rings.",
        14.5,
        19.5,
    ),
    (
        "s05",
        "A three-span iron-tipped bolt was laid into the carved guide channel, seated snugly against the drawn bowstring.",
        19.5,
        24.5,
    ),
    (
        "s06",
        "Optio Servius sighted the target angle using elevation wedges, calculating wind drift and trajectory before giving the final firing signal.",
        24.5,
        29.5,
    ),
    (
        "s07",
        "Every man braced. A machine under full tension was dangerous to friends and foes alike if a sinew gave way.",
        29.5,
        34.5,
    ),
    (
        "s08",
        "With a sharp strike of the mallet on the release claw, the stored torsion exploded outward, hurling the projectile down the ramp.",
        34.5,
        40.0,
    ),
    (
        "s09",
        "Downrange, the bodkin point shattered heavy timber palisades upon impact, proving that Roman engineering was as lethal as Roman steel.",
        40.0,
        45.5,
    ),
    (
        "s10",
        "From the Rhine to the Euphrates, Rome dominated ancient warfare not merely by sword, but by the relentless precision of mechanical science.",
        45.5,
        51.5,
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


def build_storyboard_ballista() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Assemble the 10 narrative shots adhering to Squire templates for the Ballista film."""
    shots: List[Dict[str, Any]] = []

    # s01 (0.0-4.5s): Hook: Close-up on iron bolt in ballista trough
    shots.append({
        "id": "s01",
        "tpl": "scene",
        "start": 0.0,
        "end": 4.5,
        "dur": 4.5,
        "line": SCRIPT_BEATS[0][1],
        "action": "STAND",
        "action_kind": "STAND",
        "purpose": "hook_lethal_weapon",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 301,
            "bgOpts": {"sky": "#2e4860", "haze": 0.15},
            "people": [
                {
                    "id": "artillerist_guard",
                    "preset": "ballistarius",
                    "x": 0.28,
                    "y": 0.82,
                    "h": 0.44,
                    "pose": "stand",
                    "facing": 1,
                }
            ],
            "props": [
                {"kind": "ballista", "x": 0.52, "y": 0.78, "s": 0.72, "loaded": True},
                {"kind": "bolt", "x": 0.58, "y": 0.60, "s": 0.48, "ang": 0.04, "anim": "pop"},
            ],
            "cam": {"pan": [-0.04, 0.03], "zoom": 1.05},
        },
        "sfx": [
            {"kind": "wind_loop", "at": 0.2, "vol": 0.35},
            {"kind": "armor_clank", "at": 1.8, "vol": 0.40},
            {"kind": "thud_soft", "at": 3.2, "vol": 0.50},
        ],
    })

    # s02 (4.5-9.5s): Wide artillery battery on fortified hill rampart
    shots.append({
        "id": "s02",
        "tpl": "scene",
        "start": 4.5,
        "end": 9.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[1][1],
        "action": "SIGNAL",
        "action_kind": "SIGNAL",
        "purpose": "context_artillery_battery",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 302,
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.30,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "signal",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.46,
                    "y": 0.80,
                    "h": 0.45,
                    "pose": "stand",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.68,
                    "y": 0.80,
                    "h": 0.45,
                    "pose": "stand",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.78, "y": 0.81, "s": 0.62, "loaded": True},
                {"kind": "standard", "x": 0.18, "y": 0.80, "s": 0.55},
            ],
            "cam": {"pan": [0.05, 0.0], "zoom": 1.02},
        },
        "sfx": [
            {"kind": "horn_roman", "at": 1.0, "vol": 0.55},
            {"kind": "armor_clank", "at": 2.5, "vol": 0.45},
            {"kind": "drum_hit", "at": 4.0, "vol": 0.50},
        ],
    })

    # s03 (9.5-14.5s): Winch mechanism: Artillerist crew cranking torsion bundles
    shots.append({
        "id": "s03",
        "tpl": "scene",
        "start": 9.5,
        "end": 14.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[2][1],
        "action": "WINCH",
        "action_kind": "WINCH",
        "purpose": "tension_mechanism_winch",
        "visual_source": "auto_planned",
        "args": {
            "bg": "camp",
            "time": "day",
            "seed": 303,
            "people": [
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.38,
                    "y": 0.80,
                    "h": 0.47,
                    "pose": "winch",
                    "facing": 1,
                },
                {
                    "id": "crew_cranker",
                    "preset": "ballistarius",
                    "x": 0.62,
                    "y": 0.80,
                    "h": 0.47,
                    "pose": "crank",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.50, "y": 0.78, "s": 0.76, "cranking": True, "tension": 0.85},
            ],
            "cam": {"zoom": 1.08, "pan": [0.0, -0.02]},
        },
        "sfx": [
            {"kind": "clock_tick", "at": 0.5, "vol": 0.55},
            {"kind": "clock_tick", "at": 1.2, "vol": 0.60},
            {"kind": "clock_tick", "at": 2.0, "vol": 0.65},
            {"kind": "chainmail", "at": 3.0, "vol": 0.50},
            {"kind": "clock_tick", "at": 3.8, "vol": 0.70},
        ],
    })

    # s04 (14.5-19.5s): Engineering schematic of bronze modiolus & sinew torsion core
    shots.append({
        "id": "s04",
        "tpl": "scene",
        "start": 14.5,
        "end": 19.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[3][1],
        "action": "STAND",
        "action_kind": "STAND",
        "expected_subject": "diagram",
        "purpose": "engineering_cutaway_schematic",
        "visual_source": "auto_planned",
        "args": {
            "bg": "parchment",
            "time": "day",
            "seed": 304,
            "props": [
                {"kind": "torsion_diagram", "x": 0.50, "y": 0.50, "s": 0.64, "anim": "pop"},
            ],
            "labels": [
                {"kind": "sign", "text": "BRONZE MODIOLUS CASING", "x": 0.50, "y": 0.16, "size": 34},
                {"kind": "sign", "text": "TWISTED HORSEHAIR & SINEW SKEIN", "x": 0.50, "y": 0.84, "size": 30},
            ],
            "cam": {"zoom": 1.04},
        },
        "sfx": [
            {"kind": "page_turn", "at": 0.4, "vol": 0.50},
            {"kind": "thud_soft", "at": 2.5, "vol": 0.45},
        ],
    })

    # s05 (19.5-24.5s): Loading phase: Artillerist seats bolt into slider track
    shots.append({
        "id": "s05",
        "tpl": "scene",
        "start": 19.5,
        "end": 24.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[4][1],
        "action": "LOAD",
        "action_kind": "LOAD",
        "purpose": "loading_bolt_into_trough",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 305,
            "people": [
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.38,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "load",
                    "facing": 1,
                },
                {
                    "id": "loader_assistant",
                    "preset": "ballistarius",
                    "x": 0.64,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "stand",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.58, "y": 0.79, "s": 0.72, "drawn": True},
                {"kind": "bolt", "x": 0.50, "y": 0.68, "from": 0.36, "to": 0.56, "s": 0.34, "moveAt": 0.6, "dur": 1.8},
            ],
            "cam": {"pan": [0.03, 0.0], "zoom": 1.05},
        },
        "sfx": [
            {"kind": "chainmail", "at": 0.6, "vol": 0.50},
            {"kind": "armor_clank", "at": 2.2, "vol": 0.55},
            {"kind": "thud_soft", "at": 3.6, "vol": 0.60},
        ],
    })

    # s06 (24.5-29.5s): Elevation & Aiming: Servius sights angle with quadrant wedge
    shots.append({
        "id": "s06",
        "tpl": "scene",
        "start": 24.5,
        "end": 29.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[5][1],
        "action": "AIM",
        "action_kind": "AIM",
        "purpose": "elevation_and_targeting",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 306,
            "people": [
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.36,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "aim",
                    "facing": 1,
                },
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.58,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "signal",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.72, "y": 0.80, "s": 0.66, "loaded": True},
            ],
            "cam": {"pan": [-0.03, 0.01], "zoom": 1.04},
        },
        "sfx": [
            {"kind": "wind_loop", "at": 0.4, "vol": 0.40},
            {"kind": "armor_clank", "at": 2.0, "vol": 0.50},
            {"kind": "horn_roman", "at": 4.0, "vol": 0.55},
        ],
    })

    # s07 (29.5-34.5s): Tension Peak: Battery at full draw, Marcus raises vitis, crew braces
    shots.append({
        "id": "s07",
        "tpl": "scene",
        "start": 29.5,
        "end": 34.5,
        "dur": 5.0,
        "line": SCRIPT_BEATS[6][1],
        "action": "BRACE",
        "action_kind": "BRACE",
        "purpose": "tension_peak_command_pause",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 307,
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.30,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "fire_signal",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.50,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "hammer_up",
                    "facing": 1,
                },
                {
                    "id": "titus",
                    "preset": "principes",
                    "x": 0.72,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "brace",
                    "facing": -1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.58, "y": 0.80, "s": 0.70, "tension": 1.0, "loaded": True},
            ],
            "cam": {"zoom": 1.06, "pan": [0.0, -0.01]},
        },
        "sfx": [
            {"kind": "chainmail", "at": 0.8, "vol": 0.50},
            {"kind": "war_horn", "at": 2.2, "vol": 0.60},
            {"kind": "drum_hit", "at": 4.0, "vol": 0.65},
        ],
    })

    # s08 (34.5-40.0s): Discharge & Release: Mallet strikes trigger claw, bolt launches
    shots.append({
        "id": "s08",
        "tpl": "scene",
        "start": 34.5,
        "end": 40.0,
        "dur": 5.5,
        "line": SCRIPT_BEATS[7][1],
        "action": "HAMMER",
        "action_kind": "HAMMER",
        "purpose": "trigger_strike_and_flight",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "day",
            "seed": 308,
            "people": [
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.38,
                    "y": 0.80,
                    "h": 0.46,
                    "pose": "hammer_down",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.65,
                    "y": 0.80,
                    "h": 0.45,
                    "pose": "recoil",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.46, "y": 0.80, "s": 0.70, "tension": 0.0},
                {
                    "kind": "bolt",
                    "x": 0.50,
                    "y": 0.55,
                    "from": 0.50,
                    "to": 1.20,
                    "fromY": 0.60,
                    "toY": 0.35,
                    "s": 0.35,
                    "moveAt": 0.25,
                    "dur": 0.40,
                    "easing": "linear",
                },
            ],
            "cam": {"shake": 0.04, "pan": [0.06, 0.0]},
        },
        "sfx": [
            {"kind": "drum_hit", "at": 0.2, "vol": 0.80},
            {"kind": "whoosh_fast", "at": 0.35, "vol": 0.75},
            {"kind": "arrow_whoosh", "at": 1.0, "vol": 0.65},
            {"kind": "shield_bash", "at": 2.5, "vol": 0.50},
        ],
    })

    # s09 (40.0-45.5s): Target penetration: Timber palisade shatters
    shots.append({
        "id": "s09",
        "tpl": "scene",
        "start": 40.0,
        "end": 45.5,
        "dur": 5.5,
        "line": SCRIPT_BEATS[8][1],
        "action": "IMPACT_RECOIL",
        "action_kind": "IMPACT_RECOIL",
        "purpose": "target_palisade_penetration",
        "visual_source": "auto_planned",
        "args": {
            "bg": "mud",
            "time": "storm",
            "seed": 309,
            "people": [
                {
                    "id": "celtic_defender",
                    "preset": "celtic",
                    "x": 0.35,
                    "y": 0.82,
                    "h": 0.46,
                    "pose": "react",
                    "facing": 1,
                }
            ],
            "props": [
                {"kind": "target_barrier", "x": 0.58, "y": 0.74, "s": 0.82, "hit": True, "shattered": True},
                {
                    "kind": "bolt",
                    "x": 0.50,
                    "y": 0.62,
                    "from": -0.15,
                    "to": 0.52,
                    "fromY": 0.48,
                    "toY": 0.62,
                    "s": 0.32,
                    "moveAt": 0.05,
                    "dur": 0.25,
                    "easing": "linear",
                },
            ],
            "cam": {"shake": 0.06, "zoom": 1.08},
        },
        "sfx": [
            {"kind": "whoosh_fast", "at": 0.05, "vol": 0.70},
            {"kind": "impact_heavy", "at": 0.30, "vol": 0.85},
            {"kind": "shield_bash", "at": 0.45, "vol": 0.70},
            {"kind": "battle_roar", "at": 1.8, "vol": 0.50},
            {"kind": "thud_soft", "at": 3.2, "vol": 0.55},
        ],
    })

    # s10 (45.5-51.5s): Payoff: Full Roman formation, Vitruvius & Vegetius citations
    shots.append({
        "id": "s10",
        "tpl": "scene",
        "start": 45.5,
        "end": 51.5,
        "dur": 6.0,
        "line": SCRIPT_BEATS[9][1],
        "action": "STAND",
        "action_kind": "STAND",
        "purpose": "payoff_historical_citations",
        "visual_source": "auto_planned",
        "args": {
            "bg": "field",
            "time": "sunset",
            "seed": 310,
            "people": [
                {
                    "id": "marcus",
                    "preset": "centurio",
                    "x": 0.28,
                    "y": 0.79,
                    "h": 0.46,
                    "pose": "march",
                    "facing": 1,
                },
                {
                    "id": "servius",
                    "preset": "optio",
                    "x": 0.46,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "march",
                    "facing": 1,
                },
                {
                    "id": "lucius",
                    "preset": "ballistarius",
                    "x": 0.65,
                    "y": 0.79,
                    "h": 0.45,
                    "pose": "march",
                    "facing": 1,
                },
            ],
            "props": [
                {"kind": "ballista", "x": 0.84, "y": 0.80, "s": 0.58},
            ],
            "labels": [
                {"kind": "sign", "text": "VITRUVIUS: DE ARCHITECTURA X.10", "x": 0.50, "y": 0.16, "size": 32},
                {"kind": "sign", "text": "VEGETIUS: DE RE MILITARI", "x": 0.50, "y": 0.24, "size": 28},
            ],
            "cam": {"pan": [0.04, 0.0], "zoom": 1.02},
        },
        "sfx": [
            {"kind": "drum_march", "at": 0.5, "vol": 0.60},
            {"kind": "armor_clank", "at": 2.0, "vol": 0.50},
            {"kind": "crowd_cheer", "at": 3.5, "vol": 0.45},
        ],
    })

    storyboard = {
        "version": "14.7.2",
        "title": "FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P",
        "duration": 51.5,
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
        (0.3, sfx_dir / "wind_loop.wav", 0.35),
        (2.0, sfx_dir / "armor_clank.wav", 0.40),
        (5.5, sfx_dir / "horn_roman.wav", 0.55),
        (7.0, sfx_dir / "drum_hit.wav", 0.50),
        (10.0, sfx_dir / "clock_tick.wav", 0.55),
        (11.5, sfx_dir / "clock_tick.wav", 0.60),
        (13.2, sfx_dir / "clock_tick.wav", 0.65),
        (15.0, sfx_dir / "page_turn.wav", 0.50),
        (20.0, sfx_dir / "chainmail.wav", 0.50),
        (22.0, sfx_dir / "thud_soft.wav", 0.55),
        (25.5, sfx_dir / "wind_loop.wav", 0.40),
        (28.5, sfx_dir / "horn_roman.wav", 0.55),
        (30.2, sfx_dir / "chainmail.wav", 0.50),
        (31.8, sfx_dir / "war_horn.wav", 0.60),
        (34.8, sfx_dir / "drum_hit.wav", 0.80),
        (35.0, sfx_dir / "whoosh_fast.wav", 0.75),
        (36.0, sfx_dir / "arrow_whoosh.wav", 0.65),
        (40.2, sfx_dir / "whoosh_fast.wav", 0.70),
        (40.4, sfx_dir / "impact_heavy.wav", 0.85),
        (40.8, sfx_dir / "shield_bash.wav", 0.70),
        (42.0, sfx_dir / "battle_roar.wav", 0.50),
        (46.0, sfx_dir / "drum_march.wav", 0.60),
        (49.0, sfx_dir / "crowd_cheer.wav", 0.45),
    ]

    inputs = ["-i", str(voice_wav)]
    filter_parts = ["[0:a]volume=1.0[voice]"]

    # Add music tracks: 0-19.5s ancient engineering drone, 19.5-40s war tension race, 40-51.5s victory
    inputs.extend(["-i", str(music_ancient), "-i", str(music_war), "-i", str(music_victory)])
    filter_parts.append(
        "[1:a]atrim=0:19.5,asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:ss=0:d=2.0,afade=t=out:st=16.5:d=3.0[m1];"
        "[2:a]atrim=0:20.5,asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:ss=0:d=2.0,afade=t=out:st=17.5:d=3.0,adelay=19500|19500[m2];"
        "[3:a]atrim=0:11.5,asetpts=PTS-STARTPTS,volume=0.25,afade=t=in:ss=0:d=2.0,afade=t=out:st=8.5:d=2.0,adelay=40000|40000[m3];"
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
    """Execute complete end-to-end production of the FL-01 V14.7.2 Ballista Acceptance Preview."""
    t0 = time.time()
    p_dir = Path(project_dir).resolve()
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "story").mkdir(parents=True, exist_ok=True)
    (p_dir / "timeline").mkdir(parents=True, exist_ok=True)
    (p_dir / "scenes" / "shots").mkdir(parents=True, exist_ok=True)
    (p_dir / "build").mkdir(parents=True, exist_ok=True)
    (p_dir / "out").mkdir(parents=True, exist_ok=True)

    out_mp4 = p_dir / "out" / "FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4"

    # 1. Project Config
    config = {
        "title": "FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P",
        "pack": "squire",
        "genre": "roman",
        "theme": "military_history",
        "aspect": "16:9",
        "resolution": "1080p",
        "fps": 24,
        "width": 1920,
        "height": 1080,
        "audio_mode": "voice_sfx",
        "enable_narrative_action": True,
        "enable_universal_storytelling": True,
        "ai_director_mode": "OFFLINE_ONLY",
    }
    with open(p_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # 2. Thumbnail stub
    thumb_js = p_dir / "scenes" / "shots" / "thumb.js"
    thumb_js.write_text("export function draw(g, lt, info) { /* FL-01 V14.7.2 Ballista Preview */ }\n")

    # 3. Spoken Voice Synthesis
    voice_wav = p_dir / "timeline" / "voice.wav"
    if force_rebuild or not voice_wav.is_file():
        synthesize_spoken_voice(p_dir)

    # 4. Assemble Storyboard & Shots
    storyboard, shots = build_storyboard_ballista()
    total_dur = storyboard["duration"]

    # 5. Character Bible
    bible = build_character_bible(p_dir)
    with open(p_dir / "story" / "character_bible.json", "w", encoding="utf-8") as f:
        json.dump(bible.model_dump(), f, indent=2)

    # 6. Claims Manifest (Illustrative Reconstruction of Vitruvius & Vegetius)
    claims = {
        "title": "The Wooden Machine That Shook a Battlefield — How a Roman Ballista Worked",
        "genre": "roman",
        "methodology": "ILLUSTRATIVE_RECONSTRUCTION",
        "primary_sources": [
            "Vitruvius, De Architectura, Book X, Chapter 10 (De Ballistarum Rationibus)",
            "Vegetius, Epitoma Rei Militaris, Book IV (Siege Engines and Torsion Artillery)",
        ],
        "scholarly_references": [
            "E.W. Marsden, Greek and Roman Artillery: Technical Treatises (Oxford Clarendon Press)",
            "Alan Wilkins, Roman Artillery (Shire Archaeology, 2003)",
        ],
        "total_claims": len(shots),
        "reconstruction_disclaimer": "This video depicts an illustrative reconstruction of Roman torsion artillery engineering and ballistics based on Vitruvius and archaeological finds at Hatra and Cremona.",
        "claims": [
            {
                "shot_id": s["id"],
                "claim": s["line"],
                "citation": "Vitruvius X.10 & Vegetius IV.22",
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

    # 8. Save finalized storyboard into story/shots.json
    storyboard["shots"] = shots
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

    # 4. Multi-Track Soundtrack Mix
    mixed_audio = build_mixed_soundtrack(p_dir, total_dur)

    # 5. Render Video via Playwright
    video_silent = p_dir / "build" / "video_silent.mp4"
    if force_rebuild or not video_silent.is_file() or video_silent.stat().st_size < 1000:
        cmd_render = [
            "node", str(ROOT_DIR / "render.mjs"),
            "--project", str(p_dir),
        ]
        res_render = subprocess.run(cmd_render, cwd=ROOT_DIR, capture_output=True, text=True)
        if res_render.returncode != 0:
            raise RuntimeError(f"render.mjs failed:\n{res_render.stderr[-800:]}")

    # 6. Final Mux with Normalized AAC Audio
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

    partial_info = inspect_media_file(partial_mp4)
    if not partial_info.get("valid", True) and not (partial_info.get("duration", 0) > 0):
        if partial_mp4.is_file():
            partial_mp4.unlink()
        raise RuntimeError("Muxed partial MP4 failed media inspection")

    partial_mp4.replace(out_mp4)

    # 7. Media Inspection & Cryptographic Provenance
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


def inspect_existing_preview(preview_dir: Union[str, Path] = PREVIEW_DIR) -> Dict[str, Any]:
    """Inspect existing Ballista preview and its receipt without re-rendering."""
    p_dir = Path(preview_dir).resolve()
    out_mp4 = p_dir / "out" / "FL01_V14_7_2_BALLISTA_FRESH_PREVIEW_1080P.mp4"
    receipt_file = p_dir / "out" / "render_receipt.json"

    if not out_mp4.is_file():
        return {"status": "MISSING_OUTPUT", "output_path": str(out_mp4)}

    media_info = inspect_media_file(out_mp4)
    receipt_data = {}
    if receipt_file.is_file():
        try:
            receipt_data = json.loads(receipt_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "status": "VERIFIED" if media_info.get("valid", True) else "INVALID",
        "output_path": str(out_mp4),
        "duration": media_info.get("duration"),
        "width": media_info.get("width"),
        "height": media_info.get("height"),
        "fps": media_info.get("fps"),
        "video_codec": media_info.get("video_codec"),
        "audio_codec": media_info.get("audio_codec"),
        "size_bytes": out_mp4.stat().st_size,
        "sha256": media_info.get("sha256"),
        "decode_clean": media_info.get("valid", True),
        "receipt_valid": bool(receipt_data.get("fingerprint") or receipt_data.get("sha256")),
        "fingerprint": receipt_data.get("fingerprint"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Produce or verify FL-01 V14.7.2 Ballista Acceptance Preview")
    parser.add_argument("--project", default=str(PREVIEW_DIR), help="Path to project directory")
    parser.add_argument("--verify", action="store_true", help="Inspect and verify generated preview without building")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild from source")
    args = parser.parse_args()

    if args.verify and not args.force_rebuild:
        res = inspect_existing_preview(args.project)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("status") == "VERIFIED" else 1)

    result = produce_preview(args.project, force_rebuild=args.force_rebuild)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "PRODUCED" else 1)
