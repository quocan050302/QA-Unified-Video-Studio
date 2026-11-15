#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_5_1_roman_water_gate_preview.py — Producer for original V14.7.5.1 film:
"THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET"
Subtitle: "A fictional Roman engineering rescue; stylized reconstruction, NOT a documented historical event."

Specification (FL-01 / V14.7.5.1 Section 06):
- Exact nominal duration: 30.000s @ 24 fps = exact 720 decoded video frames (container/audio diff <= 0.05s).
- Resolution: 1920x1080 (16:9), H.264 (yuv420p) + AAC stereo 48 kHz.
- Strict visual originality: 100% newly authored procedural vector/canvas civic-engineering scenes via
  `packs/squire/civic/water_gate.js` + `scenes/shots/water_gate_shots.js`. Zero reuse of prior preview MP4s,
  frames, PNGs, contact sheets, storyboards, or military props. Records `story/asset_source_manifest.json`
  with `prior_preview_derived_visual_inputs = 0`.
- Audio: Spoken English voice (`say -v Daniel`), fail-closed (`BLOCKED_NO_SPEECH_PROVIDER`) if absent,
  0.0 ms speech overlap, tail margin >= 0.40s (hard floor >= 0.25s) before every cut, zero `atempo` distortion,
  mixed with procedural wind, stone fracture crack, pressurized water jet, bronze wheel strain/gears,
  heavy timber sluice drop, diverted overflow cascade, footsteps, crowd murmur, and dramatic -> warm score
  normalized to -14.0 LUFS integrated (true peak <= -1.0 dBTP).
"""

from __future__ import annotations

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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
from tools.cinematic_camera import plan_camera_sequence
from tools.visual_qa_v14_6 import extract_frame_at_time

PROJECT_DIR = ROOT_DIR / "projects" / "fl01_v14_7_5_1_roman_water_gate_preview"
OUT_MP4_PATH = PROJECT_DIR / "out" / "FL01_V14_7_5_1_ROMAN_WATER_GATE_ORIGINAL_30S_1080P.mp4"
FILM_TITLE = "THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET"
FILM_SUBTITLE = "A fictional Roman engineering rescue; stylized reconstruction, NOT a documented historical event."
NOMINAL_DURATION_SEC = 30.0
NOMINAL_FPS = 24
NOMINAL_VIDEO_FRAMES = 720
CIVIC_MODULE_REL = "packs/squire/civic/water_gate.js"

# Exact 8-shot causal arc summing to 30.000s (720 frames @ 24fps)
WATER_GATE_BEATS: List[Dict[str, Any]] = [
    {
        "id": "S01",
        "act": "I_FRACTURE_HOOK",
        "start": 0.0,
        "end": 3.0,
        "dur": 3.0,
        "action": "CRACK_BURST",
        "expected_subject": "prop",
        "intentional_cut_reason": "opening_hook",
        "text": "The aqueduct cracked.",
    },
    {
        "id": "S02",
        "act": "I_FRACTURE_HOOK",
        "start": 3.0,
        "end": 7.0,
        "dur": 4.0,
        "action": "INSPECT",
        "expected_subject": "actor",
        "intentional_cut_reason": "wide_spatial_establish",
        "text": "Below it, a crowded street stood in danger.",
    },
    {
        "id": "S03",
        "act": "II_DECISION_UPSTREAM",
        "start": 7.0,
        "end": 11.0,
        "dur": 4.0,
        "action": "SIGNAL",
        "expected_subject": "actor",
        "intentional_cut_reason": "reaction_closeup",
        "text": "Livia saw the stone begin to give way.",
    },
    {
        "id": "S04",
        "act": "II_DECISION_UPSTREAM",
        "start": 11.0,
        "end": 15.0,
        "dur": 4.0,
        "action": "LOAD",
        "expected_subject": "actor",
        "intentional_cut_reason": "upstream_mechanism_cut",
        "text": "She shouted, Close the upper gate!",
    },
    {
        "id": "S05",
        "act": "III_MECHANICAL_STRUGGLE",
        "start": 15.0,
        "end": 19.0,
        "dur": 4.0,
        "action": "BRACE",
        "expected_subject": "actor",
        "intentional_cut_reason": "mechanical_torque_jam",
        "text": "The wheel jammed. Two workers pushed together.",
    },
    {
        "id": "S06",
        "act": "III_MECHANICAL_STRUGGLE",
        "start": 19.0,
        "end": 23.0,
        "dur": 4.0,
        "action": "WINCH",
        "expected_subject": "actor",
        "intentional_cut_reason": "same_space_action_beat",
        "text": "At last, the gate dropped into place.",
    },
    {
        "id": "S07",
        "act": "IV_DIVERSION_RESOLUTION",
        "start": 23.0,
        "end": 27.0,
        "dur": 4.0,
        "action": "WINCH",
        "expected_subject": "actor",
        "intentional_cut_reason": "overflow_payoff_track",
        "text": "The torrent turned toward the overflow channel.",
    },
    {
        "id": "S08",
        "act": "IV_DIVERSION_RESOLUTION",
        "start": 27.0,
        "end": 30.0,
        "dur": 3.0,
        "action": "REFORM",
        "expected_subject": "actor",
        "intentional_cut_reason": "resolution_wide_crane",
        "text": "The street was safe.",
    },
]


def _probe_audio_duration(path: Path) -> float:
    res = subprocess.run(
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
        check=True,
        capture_output=True,
        text=True,
    )
    return float(res.stdout.strip())


def compute_measured_voice_overlaps(events: List[Dict[str, Any]]) -> float:
    """Recompute pairwise spoken interval overlap in milliseconds directly from timestamps."""
    total_overlap_sec = 0.0
    for i in range(len(events)):
        s1 = float(events[i]["spoken_start"])
        e1 = float(events[i]["spoken_end"])
        for j in range(i + 1, len(events)):
            s2 = float(events[j]["spoken_start"])
            e2 = float(events[j]["spoken_end"])
            ov = max(0.0, min(e1, e2) - max(s1, s2))
            total_overlap_sec += ov
    return round(total_overlap_sec * 1000.0, 3)


def build_water_gate_storyboard(beats: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Build deterministic 8-shot storyboard summing to exact 30.000s (720 frames @ 24fps)
    with explicit hydraulic/mechanical world_state, causal physics metadata, and zero military props.
    """
    src_beats = [dict(b) for b in (beats or WATER_GATE_BEATS)]
    total_dur = round(sum(float(b["dur"]) for b in src_beats), 3)
    if abs(total_dur - NOMINAL_DURATION_SEC) > 1e-6:
        raise ValueError(f"Water Gate beats must sum to exact 30.000s, got {total_dur}")

    def _base(b: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": b["id"],
            "act": b["act"],
            "start": round(float(b["start"]), 3),
            "end": round(float(b["end"]), 3),
            "dur": round(float(b["dur"]), 3),
            "action": b["action"],
            "action_kind": b["action"],
            "expected_subject": b["expected_subject"],
            "line": b["text"],
            "intentional_cut_reason": b["intentional_cut_reason"],
            "causal_cut_reason": b["intentional_cut_reason"],
            "visual_source": "generated",
        }

    b_map = {b["id"]: b for b in src_beats}
    shots: List[Dict[str, Any]] = [
        {
            **_base(b_map["S01"]),
            "tpl": "scene",
            "desc": "Upper Roman travertine aqueduct pier splits along a jagged seam as pressurized water bursts outward with ONE CRACK badge",
            "world_state": {
                "zone": "upper_aqueduct_pier",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": False,
                "diversion_open": False,
            },
            "mechanics": {
                "fissure_start": 0.28,
                "fissure_end": 1.00,
                "leak_jet_start": 0.25,
                "leak_jet_end": 1.00,
                "wheel_angle_start": 0.0,
                "wheel_angle_end": 0.0,
                "gate_drop_start": 0.0,
                "gate_drop_end": 0.0,
                "overflow_flow_start": 0.0,
                "overflow_flow_end": 0.0,
                "stream_layer_order": ["masonry_wall", "stone_fissure", "water_jet", "badge"],
            },
            "args": {
                "bg": "aqueduct_pier",
                "zone": "upper_aqueduct_pier",
                "shake": 0.35,
                "shakeAt": 0.15,
                "shakeDur": 0.85,
                "people": [],
                "props": [{"kind": "civic_badge", "title": "ONE CRACK"}],
            },
        },
        {
            **_base(b_map["S02"]),
            "tpl": "scene",
            "desc": "Wide two-tier Roman stone aqueduct spanning above a sunlit cobbled market street as Engineer Livia inspects the leaking pier",
            "world_state": {
                "zone": "aqueduct_over_market_wide",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": False,
                "diversion_open": False,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.92,
                "leak_jet_end": 0.92,
                "wheel_angle_start": 0.0,
                "wheel_angle_end": 0.0,
                "gate_drop_start": 0.0,
                "gate_drop_end": 0.0,
                "overflow_flow_start": 0.0,
                "overflow_flow_end": 0.0,
                "stream_layer_order": ["market_street", "aqueduct_masonry", "water_jet", "civic_actors"],
            },
            "args": {
                "bg": "aqueduct_market",
                "zone": "aqueduct_over_market_wide",
                "people": [
                    {"id": "livia", "preset": "lady", "from": 0.35, "to": 0.41, "y": 0.36, "h": 0.22},
                    {"id": "citizen_a", "preset": "senator", "x": 0.44, "y": 0.86, "h": 0.30},
                    {"id": "cassius", "preset": "peasant", "x": 0.68, "y": 0.86, "h": 0.29},
                ],
                "props": [],
            },
        },
        {
            **_base(b_map["S03"]),
            "tpl": "close",
            "desc": "Medium-close on Engineer Livia on the upper stone catwalk raising her surveyor scroll to order the upstream sluice shut",
            "world_state": {
                "zone": "catwalk_closeup",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": False,
                "diversion_open": False,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.88,
                "leak_jet_end": 0.88,
                "wheel_angle_start": 0.0,
                "wheel_angle_end": 0.0,
                "gate_drop_start": 0.0,
                "gate_drop_end": 0.0,
                "overflow_flow_start": 0.0,
                "overflow_flow_end": 0.0,
                "stream_layer_order": ["aqueduct_masonry", "water_jet", "livia_signal"],
            },
            "args": {
                "bg": "aqueduct_catwalk",
                "zone": "catwalk_closeup",
                "people": [
                    {"id": "livia", "preset": "lady", "from": 0.47, "to": 0.50, "y": 0.84, "h": 0.52},
                ],
                "props": [{"kind": "surveyor_scroll"}],
            },
        },
        {
            **_base(b_map["S04"]),
            "tpl": "scene",
            "desc": "Upstream sluice tower: rushing open aqueduct channel, bronze spoked handwheel, meshed gear, rope, and raised timber gate as Titus approaches",
            "world_state": {
                "zone": "sluice_tower_deck",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": False,
                "diversion_open": False,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.88,
                "leak_jet_end": 0.88,
                "wheel_angle_start": 0.0,
                "wheel_angle_end": 0.0,
                "gate_drop_start": 0.02,
                "gate_drop_end": 0.02,
                "overflow_flow_start": 0.0,
                "overflow_flow_end": 0.0,
                "stream_layer_order": ["sluice_frame", "channel_water", "timber_gate", "bronze_wheel", "civic_actors"],
            },
            "args": {
                "bg": "sluice_deck",
                "zone": "sluice_tower_deck",
                "people": [
                    {"id": "titus", "preset": "smith", "from": 0.34, "to": 0.40, "y": 0.84, "h": 0.45},
                ],
                "props": [{"kind": "bronze_sluice_wheel"}],
            },
        },
        {
            **_base(b_map["S05"]),
            "tpl": "scene",
            "desc": "Titus braces his sandals hard against the stone curb as hydraulic pressure jams the shuddering bronze wheel; Livia and Cassius rush in",
            "world_state": {
                "zone": "sluice_tower_deck",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": False,
                "diversion_open": False,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.88,
                "leak_jet_end": 0.88,
                "wheel_angle_start": 0.02,
                "wheel_angle_end": 0.14,
                "gate_drop_start": 0.04,
                "gate_drop_end": 0.04,
                "overflow_flow_start": 0.0,
                "overflow_flow_end": 0.0,
                "stream_layer_order": ["sluice_frame", "channel_water", "timber_gate", "bronze_wheel", "civic_actors"],
            },
            "args": {
                "bg": "sluice_deck",
                "zone": "sluice_tower_deck",
                "shake": 0.16,
                "shakeAt": 0.4,
                "shakeDur": 1.2,
                "people": [
                    {"id": "titus", "preset": "smith", "from": 0.41, "to": 0.41, "y": 0.85, "h": 0.45},
                    {"id": "livia", "preset": "lady", "from": 0.18, "to": 0.25, "y": 0.85, "h": 0.44},
                    {"id": "cassius", "preset": "peasant", "from": 0.84, "to": 0.74, "y": 0.85, "h": 0.45},
                ],
                "props": [{"kind": "bronze_sluice_wheel"}],
            },
        },
        {
            **_base(b_map["S06"]),
            "tpl": "scene",
            "state_changed_keys": ["gate_closed", "diversion_open"],
            "desc": "Titus and Cassius heave together on the bronze spokes while Livia releases the iron pawl; gears mesh, rope pays out, and the timber gate drops shut",
            "world_state": {
                "zone": "sluice_tower_deck",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": True,
                "diversion_open": True,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.85,
                "leak_jet_end": 0.62,
                "wheel_angle_start": 0.16,
                "wheel_angle_end": 3.95,
                "gate_drop_start": 0.06,
                "gate_drop_end": 0.98,
                "gate_direction": "downward",
                "overflow_flow_start": 0.05,
                "overflow_flow_end": 0.32,
                "stream_layer_order": ["sluice_frame", "channel_water", "timber_gate", "bronze_wheel", "civic_actors"],
            },
            "args": {
                "bg": "sluice_deck",
                "zone": "sluice_tower_deck",
                "people": [
                    {"id": "livia", "preset": "lady", "from": 0.24, "to": 0.24, "y": 0.85, "h": 0.44},
                    {"id": "titus", "preset": "smith", "from": 0.40, "to": 0.40, "y": 0.85, "h": 0.46},
                    {"id": "cassius", "preset": "peasant", "from": 0.56, "to": 0.56, "y": 0.85, "h": 0.45},
                ],
                "props": [{"kind": "bronze_sluice_wheel"}],
            },
        },
        {
            **_base(b_map["S07"]),
            "tpl": "scene",
            "desc": "Hydraulic payoff: with the upstream gate sealed, the roaring current diverts down the stepped stone overflow basin while the pier crack leak subsides",
            "world_state": {
                "zone": "overflow_basin_terrace",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": True,
                "diversion_open": True,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.62,
                "leak_jet_end": 0.04,
                "wheel_angle_start": 3.95,
                "wheel_angle_end": 3.95,
                "gate_drop_start": 1.00,
                "gate_drop_end": 1.00,
                "overflow_flow_start": 0.32,
                "overflow_flow_end": 1.00,
                "stream_layer_order": ["aqueduct_masonry", "overflow_basin", "diverted_stream", "civic_actors"],
            },
            "args": {
                "bg": "overflow_basin",
                "zone": "overflow_basin_terrace",
                "people": [
                    {"id": "livia", "preset": "lady", "from": 0.43, "to": 0.47, "y": 0.44, "h": 0.25},
                    {"id": "titus", "preset": "smith", "from": 0.34, "to": 0.37, "y": 0.44, "h": 0.25},
                ],
                "props": [{"kind": "overflow_basin"}],
            },
        },
        {
            **_base(b_map["S08"]),
            "tpl": "scene",
            "desc": "Golden-hour resolution: dry market street below the intact Roman arch as Livia, Titus, and Cassius stand above under ONE DECISION. A CITY SPARED.",
            "world_state": {
                "zone": "aqueduct_over_market_wide",
                "water_flow_dir": "left_to_right",
                "crack_side": "left_pier",
                "gate_side": "upper_right_sluice",
                "gate_closed": True,
                "diversion_open": True,
            },
            "mechanics": {
                "fissure_start": 1.00,
                "fissure_end": 1.00,
                "leak_jet_start": 0.02,
                "leak_jet_end": 0.00,
                "wheel_angle_start": 3.95,
                "wheel_angle_end": 3.95,
                "gate_drop_start": 1.00,
                "gate_drop_end": 1.00,
                "overflow_flow_start": 0.85,
                "overflow_flow_end": 0.80,
                "stream_layer_order": ["market_street", "aqueduct_masonry", "civic_actors", "top_plaque"],
            },
            "args": {
                "bg": "aqueduct_market",
                "zone": "aqueduct_over_market_wide",
                "people": [
                    {"id": "livia", "preset": "lady", "x": 0.48, "y": 0.42, "h": 0.21},
                    {"id": "titus", "preset": "smith", "x": 0.39, "y": 0.42, "h": 0.21},
                    {"id": "cassius", "preset": "peasant", "x": 0.57, "y": 0.42, "h": 0.21},
                    {"id": "citizen_a", "preset": "senator", "x": 0.38, "y": 0.87, "h": 0.31},
                ],
                "props": [
                    {
                        "kind": "civic_summary_plaque",
                        "title": "ONE DECISION. A CITY SPARED.",
                        "subtitle": "ROMAN CIVIC ENGINEERING • STYLIZED RECONSTRUCTION",
                    }
                ],
            },
        },
    ]

    # Attach smooth cinematic camera trajectories (zero 1-frame snaps)
    cam_plans = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
    custom_rigs = {
        "S01": [{"t": 0.0, "x": 0.47, "y": 0.49, "z": 1.02}, {"t": 3.0, "x": 0.45, "y": 0.47, "z": 1.12}],
        "S02": [{"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.00}, {"t": 4.0, "x": 0.48, "y": 0.49, "z": 1.05}],
        "S03": [{"t": 0.0, "x": 0.49, "y": 0.50, "z": 1.02}, {"t": 4.0, "x": 0.51, "y": 0.48, "z": 1.09}],
        "S04": [{"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.01}, {"t": 4.0, "x": 0.53, "y": 0.50, "z": 1.07}],
        "S05": [{"t": 0.0, "x": 0.51, "y": 0.51, "z": 1.04}, {"t": 4.0, "x": 0.52, "y": 0.50, "z": 1.10}],
        "S06": [{"t": 0.0, "x": 0.49, "y": 0.50, "z": 1.02}, {"t": 4.0, "x": 0.52, "y": 0.50, "z": 1.08}],
        "S07": [{"t": 0.0, "x": 0.48, "y": 0.50, "z": 1.02}, {"t": 4.0, "x": 0.53, "y": 0.51, "z": 1.06}],
        "S08": [{"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.04}, {"t": 3.0, "x": 0.50, "y": 0.50, "z": 1.00}],
    }
    for s, cp in zip(shots, cam_plans):
        s["camera"] = cp.model_dump()
        s["args"]["cameraRig"] = {"keyframes": custom_rigs[s["id"]]}

    return {
        "schema_version": "14.7.5.1",
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "historical_framing": FILM_SUBTITLE,
        "pack": "squire",
        "aspect": "16:9",
        "fps": NOMINAL_FPS,
        "duration": NOMINAL_DURATION_SEC,
        "total_duration": NOMINAL_DURATION_SEC,
        "expected_video_frames": NOMINAL_VIDEO_FRAMES,
        "shots": shots,
    }


def verify_water_gate_causality(storyboard: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rendering-independent physical & narrative causality validator for 'The Water Gate'.
    Fails closed if:
    - shots do not cover exact [0.0, 30.0] across 8 contiguous beats,
    - military props (eagle, scutum, sword, arrow, ballista, spear) appear anywhere,
    - sluice gate moves upward instead of downward in S06,
    - wheel fails to rotate forward during S06,
    - overflow cascade surges BEFORE the sluice gate drops in S06,
    - fissure leak jet increases AFTER the gate closes in S07/S08,
    - stream layer order places masonry OVER water jet/diverted stream (hiding the water),
    - or world_state flow direction flips across cuts.
    """
    errors: List[str] = []
    shots = storyboard.get("shots") or []
    if len(shots) != 8:
        errors.append(f"Expected 8 shots (S01..S08), got {len(shots)}")
        return {"valid": False, "status": "FAIL", "errors": errors}

    s_by_id = {s["id"]: s for s in shots}
    for req_id in ("S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"):
        if req_id not in s_by_id:
            errors.append(f"Missing required shot {req_id}")
    if errors:
        return {"valid": False, "status": "FAIL", "errors": errors}

    # Check exact contiguous 30.000s timeline
    cur_t = 0.0
    forbidden_military = {"eagle", "standard", "scutum", "sword", "pilum", "arrow", "ballista", "javelin", "helmet"}
    for s in shots:
        if abs(float(s["start"]) - cur_t) > 1e-6:
            errors.append(f"{s['id']} start={s['start']} != expected {cur_t}")
        cur_t = float(s["end"])
        for pr in (s.get("args") or {}).get("props") or []:
            kind = str(pr.get("kind") or "").lower()
            if kind in forbidden_military:
                errors.append(f"Forbidden military prop '{kind}' in civic film shot {s['id']}")
        ws = s.get("world_state") or {}
        if ws.get("water_flow_dir") != "left_to_right":
            errors.append(f"{s['id']} flipped water_flow_dir={ws.get('water_flow_dir')!r}")

    if abs(cur_t - NOMINAL_DURATION_SEC) > 1e-6:
        errors.append(f"Final timeline end={cur_t} != 30.000s")

    m4 = s_by_id["S04"].get("mechanics") or {}
    m5 = s_by_id["S05"].get("mechanics") or {}
    m6 = s_by_id["S06"].get("mechanics") or {}
    m7 = s_by_id["S07"].get("mechanics") or {}
    m8 = s_by_id["S08"].get("mechanics") or {}

    # 1. Before S06, gate must remain open (drop <= 0.15) and overflow must NOT surge prematurely
    if float(m4.get("overflow_flow_end", 0.0)) > 0.15 or float(m5.get("overflow_flow_end", 0.0)) > 0.15:
        errors.append("Causal violation: overflow basin surged BEFORE sluice gate dropped in S06")
    if float(m5.get("gate_drop_end", 0.0)) > 0.20:
        errors.append("Causal violation: gate dropped during jammed S05 before second worker joined")

    # 2. In S06, wheel must rotate > 2.0 rad and gate must drop downward from <0.20 to >0.85
    if str(m6.get("gate_direction", "downward")) != "downward":
        errors.append(f"Causal violation: S06 gate_direction={m6.get('gate_direction')!r} (must be 'downward')")
    if float(m6.get("gate_drop_end", 0.0)) <= float(m6.get("gate_drop_start", 0.0)) + 0.70:
        errors.append(
            f"Causal violation: S06 gate failed to drop downward ({m6.get('gate_drop_start')} -> {m6.get('gate_drop_end')})"
        )
    if float(m6.get("wheel_angle_end", 0.0)) <= float(m6.get("wheel_angle_start", 0.0)) + 2.0:
        errors.append("Causal violation: S06 bronze handwheel failed to rotate sufficiently to drive gate")

    # 3. In S07 & S08, leak jet must subside monotonically while overflow carries the diverted water
    if float(m7.get("leak_jet_end", 1.0)) >= float(m7.get("leak_jet_start", 0.0)):
        errors.append("Causal violation: S07 fissure leak jet did not subside after gate closure")
    if float(m7.get("overflow_flow_end", 0.0)) <= float(m7.get("overflow_flow_start", 0.0)):
        errors.append("Causal violation: S07 overflow basin flow failed to rise after diversion")
    if float(m8.get("leak_jet_end", 1.0)) > 0.05:
        errors.append("Causal violation: S08 resolution still shows pressurized leak jet")

    # 4. Stream layer occlusion order check
    s1_layers = list((s_by_id["S01"].get("mechanics") or {}).get("stream_layer_order") or [])
    if "masonry_wall" in s1_layers and "water_jet" in s1_layers:
        if s1_layers.index("masonry_wall") > s1_layers.index("water_jet"):
            errors.append("Layer order corruption in S01: masonry_wall occludes water_jet")

    s7_layers = list(m7.get("stream_layer_order") or [])
    if "overflow_basin" in s7_layers and "diverted_stream" in s7_layers:
        if s7_layers.index("overflow_basin") > s7_layers.index("diverted_stream"):
            errors.append("Layer order corruption in S07: overflow_basin occludes diverted_stream")

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "errors": errors,
    }


def build_water_gate_assets(project_path: Path = PROJECT_DIR) -> Dict[str, Any]:
    """
    Write project scene entry (`scenes/shots/water_gate_shots.js`) importing the fresh procedural
    civic module `packs/squire/civic/water_gate.js`, verify zero external raster images in `anh/`,
    and write cryptographic `story/asset_source_manifest.json` proving zero prior-preview inputs.
    """
    p_dir = Path(project_path).resolve()
    shots_js_dir = p_dir / "scenes" / "shots"
    shots_js_dir.mkdir(parents=True, exist_ok=True)
    anh_dir = p_dir / "anh"
    if anh_dir.exists():
        # Ensure zero stale/imported raster images exist
        for f in anh_dir.iterdir():
            if f.is_file():
                f.unlink()

    civic_mod_abs = ROOT_DIR / CIVIC_MODULE_REL
    if not civic_mod_abs.is_file():
        raise FileNotFoundError(f"Missing procedural civic module: {civic_mod_abs}")

    entry_js = shots_js_dir / "water_gate_shots.js"
    entry_code = (
        "// Auto-generated fresh procedural entry for FL-01 V14.7.5.1 'The Water Gate'\n"
        "// Zero prior-preview images, clips, or military assets.\n"
        "import { registerWaterGateShots } from '/packs/squire/civic/water_gate.js';\n"
        "registerWaterGateShots();\n"
    )
    entry_js.write_text(entry_code, encoding="utf-8")

    # Scan source code of both JS files to verify zero references to prior preview dirs or image extensions
    combined_js = civic_mod_abs.read_text(encoding="utf-8") + "\n" + entry_code
    prior_tokens = [
        "fl01_v14_7_night_warning",
        "fl01_v14_7_1_bridge",
        "fl01_v14_7_2_ballista",
        "fl01_v14_7_3_roman_continuity",
        "fl01_v14_7_4_roman_arrow",
        "fl01_v14_7_5_roman_eagle",
        "v14_6_action_demo",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".mp4",
    ]
    referenced_prior = [tok for tok in prior_tokens if tok in combined_js.lower()]
    if referenced_prior:
        raise RuntimeError(f"Originality violation: civic JS references forbidden prior/raster tokens: {referenced_prior}")

    asset_manifest = {
        "schema_version": "14.7.5.1",
        "project_id": p_dir.name,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "visual_generation_mode": "100%_PROCEDURAL_HTML5_CANVAS_2D_VECTOR",
        "prior_preview_derived_visual_inputs": 0,
        "external_raster_images_count": 0,
        "military_battlefield_props_count": 0,
        "procedural_modules": {
            CIVIC_MODULE_REL: sha256_file(civic_mod_abs),
            "scenes/shots/water_gate_shots.js": sha256_file(entry_js),
        },
        "newly_authored_visual_primitives": [
            "drawMediterraneanSkyAndHills",
            "drawRomanMarketStreet",
            "drawAqueductMasonry",
            "drawStoneFissureAndJet",
            "drawSluiceMechanism",
            "drawOverflowBasin",
            "drawCivicPerson",
            "drawHighContrastCivicBadge",
        ],
        "audio_generation_mode": "MACOS_SAY_DANIEL_VOICE_PLUS_PROCEDURAL_HYDRAULIC_FOLEY_SCORE",
    }
    story_dir = p_dir / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    manifest_p = story_dir / "asset_source_manifest.json"
    manifest_p.write_text(json.dumps(asset_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return asset_manifest


def construct_water_gate_project(
    project_path: Path = PROJECT_DIR,
    storyboard: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create config.json, character_bible.json, input/01-PHIM.txt, script.json, storyboard.json, shots.json, and assets."""
    p_dir = Path(project_path).resolve()
    for sub in ("input", "story", "timeline", "build", "out", "scenes/shots"):
        (p_dir / sub).mkdir(parents=True, exist_ok=True)

    sb = storyboard or build_water_gate_storyboard()
    causality = verify_water_gate_causality(sb)
    if not causality["valid"]:
        raise ValueError(f"Water Gate causality check failed: {causality['errors']}")

    asset_manifest = build_water_gate_assets(p_dir)

    config = {
        "name": p_dir.name,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "pack": "squire",
        "genre": "roman_civic_engineering_reconstruction",
        "aspect": "16:9",
        "resolution": "1080p",
        "width": 1920,
        "height": 1080,
        "fps": NOMINAL_FPS,
        "bars": "none",
        "captions": False,
        "ai_director_mode": "OFFLINE_ONLY",
        "code_dependencies": [CIVIC_MODULE_REL],
    }
    (p_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    character_bible = {
        "schema_version": "14.7.5.1",
        "historical_framing": FILM_SUBTITLE,
        "characters": {
            "livia": {
                "name": "Engineer Livia",
                "preset": "lady",
                "role": "Roman Civic Hydraulic Engineer",
                "silhouette_markers": "Ochre tunic, crimson-trimmed stole, slate headband, rolled surveyor scroll",
            },
            "titus": {
                "name": "Worker Titus",
                "preset": "smith",
                "role": "Lead Aqueduct Sluice Worker",
                "silhouette_markers": "Terracotta work tunic, leather belt, muscular forearm grip on bronze spokes",
            },
            "cassius": {
                "name": "Worker Cassius",
                "preset": "peasant",
                "role": "Second Aqueduct Sluice Worker",
                "silhouette_markers": "Slate-blue work tunic, crimson sash, bracing sandals",
            },
            "citizen_a": {
                "name": "Market Townsman",
                "preset": "senator",
                "role": "Street Merchant Below Arch",
                "silhouette_markers": "Warm ochre civic tunic beside market awning and amphorae",
            },
        },
    }
    (p_dir / "story" / "character_bible.json").write_text(
        json.dumps(character_bible, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    claims_manifest = {
        "schema_version": "14.7.5.1",
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "historical_claim_mode": "FICTIONAL_STYLIZED_RECONSTRUCTION",
        "documented_historical_event": False,
        "disclaimer": FILM_SUBTITLE,
        "engineering_plausibility_notes": [
            "Elevated Roman stone aqueduct channel (specus) carrying gravity-fed flow above civic streets",
            "Manual bronze spoked screw/gear wheel raising and lowering a timber sluice gate (cataracta) into an overflow basin (castellum)",
        ],
    }
    (p_dir / "story" / "claims_manifest.json").write_text(
        json.dumps(claims_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    script_lines = [f"# {FILM_TITLE}", f"# {FILM_SUBTITLE}", ""] + [s["line"] for s in sb["shots"]]
    (p_dir / "input" / "01-PHIM.txt").write_text("\n".join(script_lines) + "\n", encoding="utf-8")

    for fname in ("shots.json", "storyboard.json"):
        target = p_dir / "story" / fname
        tmp_p = target.with_suffix(".tmp.json")
        tmp_p.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_p, target)

    (p_dir / "story" / "script.json").write_text(
        json.dumps(
            {
                "title": FILM_TITLE,
                "subtitle": FILM_SUBTITLE,
                "duration": NOMINAL_DURATION_SEC,
                "beats": [
                    {
                        "id": s["id"],
                        "start": s["start"],
                        "end": s["end"],
                        "dur": s["dur"],
                        "text": s["line"],
                    }
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
        "causality": causality,
        "asset_manifest": asset_manifest,
    }


def generate_water_gate_voice(
    project_path: Path = PROJECT_DIR,
    storyboard: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesize natural spoken English narration via macOS `say` (`Daniel`) across the exact 30.000s timeline.
    Fails closed (`BLOCKED_NO_SPEECH_PROVIDER`) if `say` is missing.
    Guarantees:
      - 0.0 ms pairwise speech overlap,
      - spoken_end <= shot_end - 0.25s hard floor (target >= 0.40s),
      - zero `atempo` distortion,
      - exact 30.000s (`1,440,000` stereo samples @ 48 kHz) `build/voice_track.wav`.
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

    sr = 48000
    total_samples = int(round(NOMINAL_DURATION_SEC * sr))  # Exact 1,440,000 samples
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

        aiff_p = build_dir / f"wg_voice_{sid}.aiff"
        wav_p = build_dir / f"wg_voice_{sid}.wav"
        subprocess.run(
            [say_bin, "-v", "Daniel", "-r", "182", "-o", str(aiff_p), line_txt],
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
        lead_in = 0.18
        spoken_start = round(st + lead_in, 4)
        spoken_end = round(spoken_start + nat_dur, 4)
        tail_margin = round(et - spoken_end, 4)
        if tail_margin < 0.25:
            return {
                "ok": False,
                "status": "FAIL",
                "error": f"Shot {sid} spoken line ({nat_dur:.3f}s) leaves tail_margin={tail_margin:.3f}s < 0.25s in {dur:.1f}s shot",
            }

        with wave.open(str(wav_p), "rb") as wf:
            raw_bytes = wf.readframes(wf.getnframes())
            clip_pcm = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            clip_stereo = clip_pcm.reshape(-1, 2)

        idx0 = int(round(spoken_start * sr))
        idx1 = min(total_samples, idx0 + clip_stereo.shape[0])
        master_voice[idx0:idx1, :] += clip_stereo[: idx1 - idx0, :]

        events.append(
            {
                "shot_id": sid,
                "act": s["act"],
                "shot_start": st,
                "shot_end": et,
                "shot_dur": dur,
                "spoken_start": spoken_start,
                "spoken_end": spoken_end,
                "natural_speech_dur": round(nat_dur, 4),
                "lead_in_sec": lead_in,
                "tail_margin_sec": tail_margin,
                "atempo_applied": False,
                "speech_provider": "macos_say:Daniel",
                "text": line_txt,
                "wav_file": f"build/{wav_p.name}",
            }
        )
        lines_ledger.append({"start": spoken_start, "end": spoken_end, "text": line_txt, "shot_id": sid})
        toks = line_txt.split()
        if toks:
            w_step = nat_dur / len(toks)
            for wi, tok in enumerate(toks):
                words_ledger.append(
                    {
                        "w": tok,
                        "start": round(spoken_start + wi * w_step, 3),
                        "end": round(spoken_start + (wi + 1) * w_step, 3),
                    }
                )

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
        "schema_version": "14.7.5.1",
        "status": "PASS",
        "speech_provider": "macos_say:Daniel",
        "total_timeline_duration_sec": NOMINAL_DURATION_SEC,
        "voice_wav_duration_sec": round(_probe_audio_duration(voice_track_wav), 4),
        "beats_count": len(events),
        "measured_overlap_ms": overlap_ms,
        "min_tail_margin_sec": min_tail,
        "max_tail_margin_sec": max(e["tail_margin_sec"] for e in events),
        "atempo_used_anywhere": False,
        "events": events,
    }
    (timeline_dir / "timeline_voice_events.json").write_text(
        json.dumps(voice_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"ok": True, **voice_report, "voice_track_wav": str(voice_track_wav)}


def build_water_gate_soundtrack(
    project_path: Path = PROJECT_DIR,
    voice_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build rich, multi-layer 30.000s civic rescue soundtrack:
    - Spoken Daniel narration track (primary foreground intelligibility)
    - Mediterranean wind + stone channel hydraulic rush
    - Stone fissure crack transients (S01), pressurized water spray hiss (S01-S06, tapering in S07)
    - Travertine footsteps (S02, S04, S05), strained bronze wheel groan (S05),
      iron pawl release + rhythmic bronze gear meshing (S06), heavy timber gate water-seal thud (22.45s),
      and roaring diverted cascade in the overflow catch-basin (S07)
    - Subtle dramatic low pulse (0-22.5s) resolving into warm C-major chord (23.0-30.0s), ducked under speech
    - Normalized via 2-pass EBU R128 loudnorm to -14.0 LUFS integrated and <= -1.5 dBTP true peak at exact 30.000s.
    """
    p_dir = Path(project_path).resolve()
    build_dir = p_dir / "build"
    voice_wav = build_dir / "voice_track.wav"
    if not voice_wav.is_file():
        raise FileNotFoundError(f"Missing {voice_wav}; run generate_water_gate_voice first")

    if voice_events is None:
        v_json = json.loads((p_dir / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))
        voice_events = v_json["events"]

    sr = 48000
    n = int(round(NOMINAL_DURATION_SEC * sr))
    t = np.arange(n, dtype=np.float32) / float(sr)
    rng = np.random.default_rng(14751)

    with wave.open(str(voice_wav), "rb") as wf:
        v_raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        v_stereo = v_raw.reshape(-1, 2)
    if v_stereo.shape[0] < n:
        pad = np.zeros((n - v_stereo.shape[0], 2), dtype=np.float32)
        v_stereo = np.vstack([v_stereo, pad])
    else:
        v_stereo = v_stereo[:n, :]

    # Speech ducking envelope (1.0 during gaps, 0.36 while voice speaks)
    duck = np.ones(n, dtype=np.float32)
    for ev in voice_events:
        i0 = max(0, int((float(ev["spoken_start"]) - 0.08) * sr))
        i1 = min(n, int((float(ev["spoken_end"]) + 0.12) * sr))
        duck[i0:i1] = 0.36
    # Smooth ducking transitions (60 ms moving average)
    win = int(0.06 * sr)
    duck = np.convolve(duck, np.ones(win, dtype=np.float32) / win, mode="same")

    # 1. Filtered noise beds: breeze + pressurized water spray + diverted cascade
    white_l = rng.standard_normal(n).astype(np.float32)
    white_r = rng.standard_normal(n).astype(np.float32)
    # Simple 1-pole lowpass filters for water roar vs spray hiss
    def _lowpass(sig: np.ndarray, alpha_lp: float) -> np.ndarray:
        out = np.empty_like(sig)
        acc = 0.0
        for idx in range(sig.shape[0]):
            acc += alpha_lp * (float(sig[idx]) - acc)
            out[idx] = acc
        return out

    # Fast vectorized moving-average band shaping (much faster than Python loop on 1.44M samples!)
    k_roar = np.ones(64, dtype=np.float32) / 64.0
    k_spray = np.ones(8, dtype=np.float32) / 8.0
    roar_l = np.convolve(white_l, k_roar, mode="same") * 3.2
    roar_r = np.convolve(white_r, k_roar, mode="same") * 3.2
    spray_l = (np.convolve(white_l, k_spray, mode="same") - roar_l * 0.25) * 0.9
    spray_r = (np.convolve(white_r, k_spray, mode="same") - roar_r * 0.25) * 0.9

    # Pressurized leak spray envelope: rises at 0.2s, strong 0.4-22.5s, subsides 23.0-26.5s, near zero in S08
    spray_env = np.clip((t - 0.15) / 0.4, 0.0, 1.0) * np.clip((26.2 - t) / 3.2, 0.04, 1.0) * 0.055
    # Diverted overflow cascade roar: surges in S07 (22.6s -> 27.2s) then settles gently
    divert_env = (
        0.025 * np.clip(t / 1.0, 0.0, 1.0)
        + 0.085 * np.exp(-0.5 * ((t - 24.8) / 1.9) ** 2)
    )

    sfx_l = spray_l * spray_env + roar_l * divert_env
    sfx_r = spray_r * spray_env + roar_r * divert_env

    # Helper to add localized foley events
    def _add_burst(t_sec: float, dur_sec: float, freq0: float, freq1: float, amp: float, pan: float = 0.0) -> None:
        i0 = int(t_sec * sr)
        ln = int(dur_sec * sr)
        if i0 < 0 or i0 >= n or ln <= 10:
            return
        i1 = min(n, i0 + ln)
        lt_s = np.arange(i1 - i0, dtype=np.float32) / float(sr)
        env_s = np.exp(-lt_s / max(0.015, dur_sec * 0.32))
        phase = 2.0 * np.pi * (freq0 * lt_s + 0.5 * (freq1 - freq0) * (lt_s ** 2) / max(0.01, dur_sec))
        burst = (np.sin(phase) * 0.65 + white_l[i0:i1] * 0.35) * env_s * amp
        sfx_l[i0:i1] += burst * (1.0 - max(0.0, pan))
        sfx_r[i0:i1] += burst * (1.0 + min(0.0, pan))

    # S01: Stone fissure sharp fracture impacts
    _add_burst(0.16, 0.38, 195.0, 58.0, 0.34, pan=-0.25)
    _add_burst(0.64, 0.45, 165.0, 46.0, 0.28, pan=-0.20)

    # S02, S04, S05: Travertine footsteps
    for ft in (3.35, 3.85, 4.35, 4.85, 11.4, 11.95, 12.5, 15.4, 15.85, 16.3):
        _add_burst(ft, 0.09, 140.0, 75.0, 0.11, pan=0.1)

    # S05 (15.3 - 18.6s): Strained bronze wheel groan / shudder under water pressure
    i_s5_0, i_s5_1 = int(15.35 * sr), int(18.55 * sr)
    lt5 = t[i_s5_0:i_s5_1] - 15.35
    groan = (
        0.045
        * (0.5 + 0.5 * np.sin(2.0 * np.pi * 6.5 * lt5))
        * (np.sin(2.0 * np.pi * 148.0 * lt5 + 0.8 * np.sin(2.0 * np.pi * 24.0 * lt5)) + 0.5 * np.sin(2.0 * np.pi * 221.0 * lt5))
    )
    sfx_l[i_s5_0:i_s5_1] += groan
    sfx_r[i_s5_0:i_s5_1] += groan * 0.92

    # S06 (19.12s pawl release + 19.25..22.35s bronze gear ratchet clicks + 22.45s heavy timber gate water seal)
    _add_burst(19.12, 0.14, 620.0, 290.0, 0.20, pan=0.15)
    for gt in np.linspace(19.30, 22.25, 11):
        _add_burst(float(gt), 0.11, 310.0, 145.0, 0.14, pan=0.18)
    _add_burst(22.45, 0.62, 112.0, 38.0, 0.36, pan=0.20)

    # 2. Subtle cinematic score: tense urgent D-minor pulse (0-22.4s) -> warm C-major civic resolution chord (22.6-30.0s)
    tension_env = np.clip(t / 1.2, 0.0, 1.0) * np.clip((22.8 - t) / 0.8, 0.0, 1.0)
    pulse_mod = 0.55 + 0.45 * np.sin(2.0 * np.pi * 1.5 * t)
    score_tension = (
        0.042 * np.sin(2.0 * np.pi * 73.42 * t)
        + 0.026 * np.sin(2.0 * np.pi * 110.00 * t)
        + 0.018 * np.sin(2.0 * np.pi * 146.83 * t)
    ) * tension_env * pulse_mod

    res_env = np.clip((t - 22.5) / 1.4, 0.0, 1.0) * np.clip((30.0 - t) / 0.65, 0.0, 1.0)
    score_resolve = (
        0.040 * np.sin(2.0 * np.pi * 130.81 * t)   # C3
        + 0.032 * np.sin(2.0 * np.pi * 164.81 * t) # E3
        + 0.028 * np.sin(2.0 * np.pi * 196.00 * t) # G3
        + 0.020 * np.sin(2.0 * np.pi * 261.63 * t) # C4
    ) * res_env

    bed_l = (sfx_l + score_tension + score_resolve) * duck
    bed_r = (sfx_r + score_tension * 0.96 + score_resolve * 1.04) * duck

    # Combine crisp spoken voice + ducked hydraulic foley & score
    raw_mix = np.stack([v_stereo[:, 0] * 1.12 + bed_l, v_stereo[:, 1] * 1.12 + bed_r], axis=1)
    peak = float(np.max(np.abs(raw_mix)))
    if peak > 0.92:
        raw_mix = raw_mix * (0.92 / peak)

    pre_wav = build_dir / "soundtrack_pre_loudnorm.wav"
    mixed_wav = build_dir / "soundtrack_mixed.wav"
    pcm_pre = np.clip(raw_mix * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(pre_wav), "wb") as wf_pre:
        wf_pre.setnchannels(2)
        wf_pre.setsampwidth(2)
        wf_pre.setframerate(sr)
        wf_pre.writeframes(pcm_pre.tobytes())

    # Pass 1: Measure EBU R128 loudness
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
    if m_json:
        ln_stats = json.loads(m_json.group(0))
        af_norm = (
            f"loudnorm=I=-14.0:TP=-1.5:LRA=9.0:"
            f"measured_I={ln_stats['input_i']}:"
            f"measured_TP={ln_stats['input_tp']}:"
            f"measured_LRA={ln_stats['input_lra']}:"
            f"measured_thresh={ln_stats['input_thresh']}:"
            f"offset={ln_stats['target_offset']}:linear=true,"
            f"apad=whole_dur=30.0,atrim=0:30.0"
        )
    else:
        af_norm = "loudnorm=I=-14.0:TP=-1.5:LRA=9.0,apad=whole_dur=30.0,atrim=0:30.0"

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
        "schema_version": "14.7.5.1",
        "status": "AUDIO_MIX_PASS" if wav_metrics.get("valid") else "FAIL",
        "mixed_wav": str(mixed_wav),
        "duration_sec": wav_metrics.get("duration"),
        "integrated_lufs": wav_metrics.get("integrated_lufs"),
        "true_peak_dbtp": wav_metrics.get("true_peak_dbtp"),
        "layers": [
            "voice_daniel_english",
            "mediterranean_wind_and_channel_rush",
            "stone_fissure_crack_and_pressurized_spray",
            "travertine_footsteps_bronze_wheel_groan_gears_timber_gate_drop",
            "overflow_basin_cascade_and_civic_resolution_chord",
        ],
    }
    (build_dir / "audio_mix_report.json").write_text(json.dumps(mix_report, indent=2), encoding="utf-8")
    return mix_report


def generate_water_gate_contact_sheets(
    project_path: Path = PROJECT_DIR,
    mp4_path: Path = OUT_MP4_PATH,
    extra_evidence_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Decode real frames from the muxed 1080p MP4 and compose 3 high-clarity contact sheets:
    - contact_sheet_full.png (4x2 grid across all 8 shots S01..S08)
    - contact_sheet_hook.png (3x2 grid across opening fracture & stakes 0.0s..7.0s)
    - contact_sheet_action.png (3x2 grid across jammed wheel, two-worker heave, gate drop & overflow 15.0s..27.0s)
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
                ("S01 1.5s Hook Crack", 1.5),
                ("S02 5.0s Market Stakes", 5.0),
                ("S03 9.0s Livia Command", 9.0),
                ("S04 13.0s Sluice Wheel", 13.0),
                ("S05 17.0s Jammed Torque", 17.0),
                ("S06 21.2s Gate Dropping", 21.2),
                ("S07 25.2s Overflow Basin", 25.2),
                ("S08 28.5s City Spared", 28.5),
            ],
        },
        "contact_sheet_hook.png": {
            "cols": 3,
            "rows": 2,
            "samples": [
                ("0.4s Seam Cracking", 0.4),
                ("1.4s ONE CRACK Jet", 1.4),
                ("2.5s Full Pier Spray", 2.5),
                ("3.6s Wide Arch Street", 3.6),
                ("5.2s Livia On Catwalk", 5.2),
                ("6.6s Spray Over Stalls", 6.6),
            ],
        },
        "contact_sheet_action.png": {
            "cols": 3,
            "rows": 2,
            "samples": [
                ("15.8s Titus Bracing", 15.8),
                ("18.2s Wheel Jammed", 18.2),
                ("19.8s Two Workers Heave", 19.8),
                ("21.6s Gate Sliding Down", 21.6),
                ("23.8s Stream Diverting", 23.8),
                ("26.2s Crack Leak Subsides", 26.2),
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
        sheet = Image.new("RGB", (canvas_w, canvas_h), (20, 25, 34))
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (pad, 16),
            f"{FILM_TITLE.replace('—', '-')} - {sheet_name} (Decoded from 1080p24 MP4)",
            fill=(244, 224, 172),
        )

        for idx, (caption, ts) in enumerate(cfg["samples"]):
            r_idx = idx // cols
            c_idx = idx % cols
            frame_png = tmp_dir / f"{sheet_name}_{idx:02d}.png"
            ok = extract_frame_at_time(mp4_path, ts, frame_png)
            if not ok or not frame_png.is_file():
                raise RuntimeError(f"Failed to decode contact-sheet frame at {ts}s from {mp4_path}")
            with Image.open(frame_png) as fim:
                thumb = fim.convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
            x0 = pad + c_idx * (tile_w + pad)
            y0 = header_h + pad + r_idx * (tile_h + 34 + pad)
            sheet.paste(thumb, (x0, y0))
            draw.rectangle([x0 - 1, y0 - 1, x0 + tile_w + 1, y0 + tile_h + 1], outline=(218, 174, 88), width=2)
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


def inspect_water_gate_preview(
    project_path: Path = PROJECT_DIR,
    mp4_path: Path = OUT_MP4_PATH,
) -> Dict[str, Any]:
    """
    Full fail-closed media, exact 720-frame count, loudness, speech sync, causality,
    originality manifest, and cryptographic receipt lineage verification on Water Gate MP4.
    """
    p_dir = Path(project_path).resolve()
    m_path = Path(mp4_path).resolve()
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
    causality = verify_water_gate_causality(sb)
    asset_manifest = json.loads((p_dir / "story" / "asset_source_manifest.json").read_text(encoding="utf-8"))
    v_ledger = json.loads((p_dir / "timeline" / "timeline_voice_events.json").read_text(encoding="utf-8"))

    v_dur = float(mi.get("video_stream_duration") or 0.0)
    a_dur = float(mi.get("audio_stream_duration") or 0.0)
    c_dur = float(mi.get("duration") or 0.0)
    av_diff = round(abs(c_dur - NOMINAL_DURATION_SEC), 4)
    stream_diff = round(abs(a_dur - v_dur), 4)
    lufs = mi.get("integrated_lufs")
    tp = mi.get("true_peak_dbtp")

    loudness_ok = (lufs is not None) and (-16.0 <= float(lufs) <= -12.0)
    tp_ok = (tp is not None) and (float(tp) <= -1.0)
    frames_ok = int(mi.get("decoded_video_frames") or 0) == NOMINAL_VIDEO_FRAMES
    av_sync_ok = (av_diff <= 0.05) and (stream_diff <= 0.05)
    voice_ok = (
        float(v_ledger.get("measured_overlap_ms", 99.0)) == 0.0
        and float(v_ledger.get("min_tail_margin_sec", 0.0)) >= 0.25
        and v_ledger.get("atempo_used_anywhere") is False
    )
    orig_ok = int(asset_manifest.get("prior_preview_derived_visual_inputs", 1)) == 0

    all_valid = (
        lineage.get("status") == "PASS"
        and frames_ok
        and av_sync_ok
        and loudness_ok
        and tp_ok
        and voice_ok
        and causality.get("valid") is True
        and orig_ok
    )
    return {
        "valid": all_valid,
        "status": "PASS" if all_valid else "FAIL",
        "cache_status": lineage.get("cache_status"),
        "lineage": lineage,
        "media_info": mi,
        "decoded_video_frames": mi.get("decoded_video_frames"),
        "nominal_duration_diff_sec": av_diff,
        "audio_video_stream_diff_sec": stream_diff,
        "causality": causality,
        "voice_summary": {
            "speech_provider": v_ledger.get("speech_provider"),
            "beats_count": v_ledger.get("beats_count"),
            "measured_overlap_ms": v_ledger.get("measured_overlap_ms"),
            "min_tail_margin_sec": v_ledger.get("min_tail_margin_sec"),
            "atempo_used_anywhere": v_ledger.get("atempo_used_anywhere"),
        },
        "asset_originality": asset_manifest,
    }


def produce_water_gate_preview(
    project_path: Path = PROJECT_DIR,
    output_mp4_path: Path = OUT_MP4_PATH,
    force_rebuild: bool = False,
    workers: int = 1,
    extra_evidence_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    End-to-end production pipeline for 'THE WATER GATE — THIRTY SECONDS TO SAVE THE STREET'.
    Supports verified warm cache hits when `force_rebuild=False` and full real Chromium+FFmpeg
    rendering when `force_rebuild=True` or cache is stale.
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
    render_opts = {"audio_mode": "voice_sfx", "code_dependencies": [CIVIC_MODULE_REL]}

    # Check warm cache hit BEFORE touching project files when force_rebuild=False
    if not force_rebuild and out_mp4.is_file() and (p_dir / "config.json").is_file():
        pre_manifest = collect_render_inputs(p_dir, render_options=render_opts)
        cache_check = validate_cache_hit(p_dir, out_mp4, pre_manifest, expected_specs=expected_specs)
        if cache_check.get("hit") is True:
            sheets = {}
            for sname in ("contact_sheet_full.png", "contact_sheet_hook.png", "contact_sheet_action.png"):
                sp = out_mp4.parent / sname
                if not sp.is_file():
                    sheets = generate_water_gate_contact_sheets(p_dir, out_mp4, extra_evidence_dir=extra_evidence_dir)
                    break
            else:
                if extra_evidence_dir is not None:
                    Path(extra_evidence_dir).mkdir(parents=True, exist_ok=True)
                    for sname in ("contact_sheet_full.png", "contact_sheet_hook.png", "contact_sheet_action.png"):
                        shutil.copy2(out_mp4.parent / sname, Path(extra_evidence_dir) / sname)
            insp = inspect_water_gate_preview(p_dir, out_mp4)
            return {
                "status": "CACHE_HIT_VERIFIED" if insp["valid"] else "FAIL",
                "render_mode": "CACHE_HIT_VERIFIED",
                "wall_sec": round(time.perf_counter() - t0, 4),
                "output_mp4": str(out_mp4),
                "inspection": insp,
                "contact_sheets": sheets,
            }

    # Step 1: Build storyboard, civic JS assets, config, character bible
    sb = build_water_gate_storyboard()
    construct_water_gate_project(p_dir, storyboard=sb)

    # Step 2: Synthesize spoken Daniel voice track (exact 30.000s, 0ms overlap)
    voice_res = generate_water_gate_voice(p_dir, storyboard=sb)
    if not voice_res.get("ok"):
        return {
            "status": voice_res.get("status", "FAIL"),
            "error": voice_res.get("error"),
            "wall_sec": round(time.perf_counter() - t0, 4),
        }

    # Step 3: Build multi-layer hydraulic foley + score soundtrack (-14 LUFS, exact 30.000s)
    mix_res = build_water_gate_soundtrack(p_dir, voice_events=voice_res["events"])
    if mix_res.get("status") != "AUDIO_MIX_PASS":
        return {"status": "FAIL", "error": f"Audio mix failed: {mix_res}"}

    # Step 4: Render 720 frames @ 1080p24 via real headless Chromium (`render.mjs`), QA_STUDIO_TEST_MODE unset
    env = dict(os.environ)
    env.pop("QA_STUDIO_TEST_MODE", None)
    render_t0 = time.perf_counter()
    cmd_render = ["node", "render.mjs", "--project", str(p_dir), "--workers", str(max(1, int(workers)))]
    proc = subprocess.run(cmd_render, cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    render_wall_sec = round(time.perf_counter() - render_t0, 3)

    render_log_p = build_dir / "render.log"
    render_log_p.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        return {
            "status": "FAIL",
            "error": f"render.mjs exited {proc.returncode}: {(proc.stderr or proc.stdout)[-600:]}",
            "wall_sec": round(time.perf_counter() - t0, 4),
        }

    silent_mp4 = build_dir / "video_silent.mp4"
    if not silent_mp4.is_file() or silent_mp4.stat().st_size < 1000:
        return {"status": "FAIL", "error": "Missing or empty build/video_silent.mp4"}

    # Step 5: Mux video_silent.mp4 (exact 720 frames) + soundtrack_mixed.wav (exact 30.000s) WITHOUT -shortest
    # so video stream is guaranteed to preserve all 720 frames!
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

    pre_inspect = inspect_media_file(
        partial_mp4,
        expected_specs=expected_specs,
        require_audio=True,
        full_decode=True,
    )
    if not pre_inspect.get("valid"):
        return {
            "status": "FAIL",
            "error": f"Partial MP4 failed media verification before promotion: {pre_inspect.get('errors')}",
            "media_info": pre_inspect,
        }

    os.replace(partial_mp4, out_mp4)

    # Step 6: Write cryptographic render_receipt.json & generate 3 contact sheets from decoded MP4
    manifest = collect_render_inputs(p_dir, render_options=render_opts)
    total_wall = round(time.perf_counter() - t0, 3)
    node_ver = subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip()
    receipt_p = write_render_receipt_atomic(
        p_dir,
        out_mp4,
        manifest,
        metadata={
            "version": "14.7.5.1",
            "action": "produce_water_gate_preview",
            "render_mode": "REAL_RENDER",
            "force_rebuild": bool(force_rebuild),
            "ai_director_mode": "OFFLINE_ONLY",
            "ai_director_live_used": False,
            "node_version": node_ver,
            "python_version": sys.version.split()[0],
            "render_only_wall_sec": render_wall_sec,
            "wall_sec": total_wall,
        },
    )

    sheets = generate_water_gate_contact_sheets(p_dir, out_mp4, extra_evidence_dir=extra_evidence_dir)
    final_insp = inspect_water_gate_preview(p_dir, out_mp4)

    return {
        "status": "PRODUCED" if final_insp["valid"] else "FAIL",
        "render_mode": "REAL_RENDER",
        "render_only_wall_sec": render_wall_sec,
        "wall_sec": round(time.perf_counter() - t0, 3),
        "output_mp4": str(out_mp4),
        "receipt_path": str(receipt_p),
        "inspection": final_insp,
        "contact_sheets": sheets,
    }


if __name__ == "__main__":
    force = "--force" in sys.argv
    res = produce_water_gate_preview(force_rebuild=force, workers=1)
    print(json.dumps({k: res.get(k) for k in ("status", "render_mode", "render_only_wall_sec", "wall_sec", "output_mp4", "error")}, indent=2))
    sys.exit(0 if res.get("status") in ("PRODUCED", "CACHE_HIT_VERIFIED") else 1)
