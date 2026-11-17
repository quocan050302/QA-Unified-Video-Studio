#!/usr/bin/env python3
"""kh03_preview_director.py — Pilot-Scoped 30.000s Original Roman 2D Preview Director for KH-03.0.

Authors, compiles, synthesizes audio/TTS, and renders the brand-new 30.000s (720-frame @ 24fps)
1080p Canvas2D pilot:
  Working title: "THE LAST GAP IN THE SHIELD WALL"
  Project root:  projects/kh03_roman_last_gap_30s/
  Output MP4:    projects/kh03_roman_last_gap_30s/out/KH03_ROMAN_LAST_GAP_ORIGINAL_30S_1080P.mp4

Scope honesty:
- Pilot-scoped authoring & compilation for KH-03.0 only (NOT generalized KH-03.2..KH-03.5 engines).
- Uses 100% original Production Squire Roman character identity (`hastatus`, `princeps`, `legionary`)
  locked by `visual_styles/roman_squire_master/v1/style_bible.json`.
- Pure HTML5 Canvas2D (`render_mode = "canvas2d_only"`), zero Three.js/WebGL 3D, zero external bitmaps,
  zero reused KH-01/KH-02/baseline assets.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tts_helper import synthesize_speech
from tools.kh03_reference_audit import assert_no_reused_demo_assets, collect_user_style_reference
from tools.kh03_style_lock import load_roman_master_style, resolve_roman_variant, validate_roman_style_contract
from tools.validator import validate_project

PILOT_PROJECT_DIR = REPO_ROOT / "projects" / "kh03_roman_last_gap_30s"
OUTPUT_TITLE = "KH03_ROMAN_LAST_GAP_ORIGINAL_30S_1080P"

CANONICAL_SCRIPT_LINES: List[Dict[str, Any]] = [
    {
        "line_id": "L01",
        "shot_id": "SH01",
        "text": "One tiny gap could ruin a Roman shield wall.",
        "min_offset_in_shot": 0.10,
    },
    {
        "line_id": "L02",
        "shot_id": "SH02",
        "text": "At dawn, a rookie was still adjusting his grip.",
        "min_offset_in_shot": 0.12,
    },
    {
        "line_id": "L03",
        "shot_id": "SH03",
        "text": "The instructor spotted it,",
        "min_offset_in_shot": 0.22,
    },
    {
        "line_id": "L04",
        "shot_id": "SH04",
        "text": "and sent a wooden practice spear straight at the opening.",
        "min_offset_in_shot": 0.08,
    },
    {
        "line_id": "L05",
        "shot_id": "SH05",
        "text": "The rookie planted his foot, shoved his shield into place,",
        "min_offset_in_shot": 0.08,
    },
    {
        "line_id": "L06",
        "shot_id": "SH06",
        "text": "and the spear snapped aside.",
        "min_offset_in_shot": 0.16,
    },
    {
        "line_id": "L07",
        "shot_id": "SH07",
        "text": "Perfect drill. Almost.",
        "min_offset_in_shot": 0.30,
    },
    {
        "line_id": "L08",
        "shot_id": "SH08",
        "text": "His own spear was now tangled in his neighbor's strap.",
        "min_offset_in_shot": 0.12,
    },
    {
        "line_id": "L09",
        "shot_id": "SH09",
        "text": "The instructor didn't smile. But he nodded.",
        "min_offset_in_shot": 0.14,
    },
]


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def compile_roman_training_beats(
    script: str | None = None,
    style_bible: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Compile and validate the 9 authored pilot beats (0.000s..30.000s, pilot-scoped)."""
    sb = style_bible or load_roman_master_style()
    check = validate_roman_style_contract(sb)
    if not check["valid"]:
        raise ValueError(f"Style contract invalid: {check['errors']}")

    rookie_var = resolve_roman_variant("rookie", style_dict=sb)
    inst_var = resolve_roman_variant("instructor", style_dict=sb)
    neigh_var = resolve_roman_variant("neighbor", style_dict=sb)

    beats: List[Dict[str, Any]] = [
        {
            "id": "SH01",
            "index": 1,
            "start": 0.00,
            "end": 2.50,
            "duration": 2.50,
            "frame_start": 0,
            "frame_end": 59,
            "beat_role": "HOOK",
            "purpose": "hook_exposed_shield_gap_and_approaching_wooden_spear",
            "framing_scale": "extreme_detail_insert",
            "camera_trajectory": "push_in_focus",
            "stage_axis_sign": 1,
            "gap_state_start": "OPEN_SLIVER",
            "gap_state_end": "OPEN_SLIVER",
            "snagged_spear_start": False,
            "snagged_spear_end": False,
            "primary_actors": [rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[0]["text"],
            "visual_summary": (
                "Extreme close-up of trembling red gold-rimmed scutum edge beside neighbor's steady scutum; "
                "warm dawn sunbeam slices through the narrow gap while a blunt wooden practice spear approaches from left."
            ),
            "sfx": [
                {"name": "sfx/kh03_scutum_grip_rattle.wav", "at": 0.08, "gain": -5.0},
                {"name": "sfx/kh03_spear_whoosh_launch.wav", "at": 1.38, "gain": -6.5},
            ],
        },
        {
            "id": "SH02",
            "index": 2,
            "start": 2.50,
            "end": 5.50,
            "duration": 3.00,
            "frame_start": 60,
            "frame_end": 131,
            "beat_role": "REVEAL",
            "purpose": "reveal_rookie_hastatus_noticing_exposed_line",
            "framing_scale": "medium_over_shoulder",
            "camera_trajectory": "subtle_lateral_drift",
            "stage_axis_sign": 1,
            "gap_state_start": "OPEN_SLIVER",
            "gap_state_end": "OPEN_SLIVER",
            "snagged_spear_start": False,
            "snagged_spear_end": False,
            "primary_actors": [rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[1]["text"],
            "visual_summary": (
                "Medium over-shoulder on original Squire rookie Roman soldier (Montefortino feathers, ivory round face, "
                "white glove, red scutum & spear); eyes shift toward the sunlit gap and his grip tightens."
            ),
            "sfx": [
                {"name": "sfx/kh03_scutum_grip_rattle.wav", "at": 0.65, "gain": -6.0},
                {"name": "sfx/kh03_armor_nod_settle.wav", "at": 1.85, "gain": -8.0},
            ],
        },
        {
            "id": "SH03",
            "index": 3,
            "start": 5.50,
            "end": 9.00,
            "duration": 3.50,
            "frame_start": 132,
            "frame_end": 215,
            "beat_role": "WIDE_GEOGRAPHY",
            "purpose": "establish_castra_gate_ramp_and_training_shield_line",
            "framing_scale": "wide_geography",
            "camera_trajectory": "pan_left_to_right_establish",
            "stage_axis_sign": 1,
            "gap_state_start": "OPEN_SLIVER",
            "gap_state_end": "OPEN_SLIVER",
            "snagged_spear_start": False,
            "snagged_spear_end": False,
            "primary_actors": [inst_var["archetype_id"], rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[2]["text"],
            "visual_summary": (
                "Wide multi-plane 2D Roman training yard at warm dawn: timber castra gate & ramp on left, "
                "legionary tents, cohort bracing red shields with exposed gap on right-center, instructor raising practice spear."
            ),
            "sfx": [
                {"name": "sfx/kh03_sand_foot_plant.wav", "at": 0.75, "gain": -7.5},
                {"name": "sfx/kh03_armor_nod_settle.wav", "at": 2.10, "gain": -8.5},
            ],
        },
        {
            "id": "SH04",
            "index": 4,
            "start": 9.00,
            "end": 12.00,
            "duration": 3.00,
            "frame_start": 216,
            "frame_end": 287,
            "beat_role": "INCITING_BEAT",
            "purpose": "instructor_launches_harmless_wooden_training_spear",
            "framing_scale": "low_angle_profile",
            "camera_trajectory": "dynamic_follow_launch",
            "stage_axis_sign": 1,
            "gap_state_start": "OPEN_SLIVER",
            "gap_state_end": "OPEN_SLIVER",
            "snagged_spear_start": False,
            "snagged_spear_end": False,
            "primary_actors": [inst_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[3]["text"],
            "visual_summary": (
                "Low-angle profile of princeps drill instructor coiling and launching a blunt leather-tipped wooden "
                "practice spear strictly left-to-right across frame toward the shield line."
            ),
            "sfx": [
                {"name": "sfx/kh03_sand_foot_plant.wav", "at": 0.55, "gain": -6.5},
                {"name": "sfx/kh03_spear_whoosh_launch.wav", "at": 0.92, "gain": -3.5},
            ],
        },
        {
            "id": "SH05",
            "index": 5,
            "start": 12.00,
            "end": 15.00,
            "duration": 3.00,
            "frame_start": 288,
            "frame_end": 359,
            "beat_role": "ACTION",
            "purpose": "rookie_plants_foot_and_shoves_scutum_into_wall",
            "framing_scale": "medium_full_tracking",
            "camera_trajectory": "lateral_track_into_lock",
            "stage_axis_sign": 1,
            "gap_state_start": "OPEN_SLIVER",
            "gap_state_end": "SEALED_TIGHT",
            "motivate_gap_transition": True,
            "snagged_spear_start": False,
            "snagged_spear_end": True,
            "motivate_snag_transition": True,
            "primary_actors": [rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[4]["text"],
            "visual_summary": (
                "Tracking shot as rookie anticipates, plants front sandal into drill sand with dust puff, "
                "and shoves his red scutum flush against neighbor's rim—inadvertently hooking his spear into neighbor's strap."
            ),
            "sfx": [
                {"name": "sfx/kh03_sand_foot_plant.wav", "at": 1.02, "gain": -4.0},
                {"name": "sfx/kh03_shield_wall_lock.wav", "at": 1.65, "gain": -3.5},
            ],
        },
        {
            "id": "SH06",
            "index": 6,
            "start": 15.00,
            "end": 18.50,
            "duration": 3.50,
            "frame_start": 360,
            "frame_end": 443,
            "beat_role": "IMPACT_INSERT",
            "purpose": "wooden_practice_tip_strikes_shield_rim_and_glances_away",
            "framing_scale": "macro_physics_insert",
            "camera_trajectory": "snap_push_and_recoil",
            "stage_axis_sign": 1,
            "gap_state_start": "SEALED_TIGHT",
            "gap_state_end": "SEALED_TIGHT",
            "snagged_spear_start": True,
            "snagged_spear_end": True,
            "primary_actors": [rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[5]["text"],
            "visual_summary": (
                "24fps close-up insert: blunt leather-padded wooden spear tip strikes the sealed gold scutum rim "
                "with readable pad compression, recoil impulse, and spinning deflection onto the sand."
            ),
            "sfx": [
                {"name": "sfx/kh03_wood_spear_glance.wav", "at": 0.58, "gain": -2.5},
                {"name": "sfx/kh03_sand_foot_plant.wav", "at": 2.18, "gain": -7.5},
            ],
        },
        {
            "id": "SH07",
            "index": 7,
            "start": 18.50,
            "end": 23.00,
            "duration": 4.50,
            "frame_start": 444,
            "frame_end": 551,
            "beat_role": "PAYOFF",
            "purpose": "shield_line_holds_and_instructor_narrows_eyes_then_nods",
            "framing_scale": "wide_to_medium_payoff",
            "camera_trajectory": "push_in_to_instructor",
            "stage_axis_sign": 1,
            "gap_state_start": "SEALED_TIGHT",
            "gap_state_end": "SEALED_TIGHT",
            "snagged_spear_start": True,
            "snagged_spear_end": True,
            "intentional_hold": {
                "enabled": True,
                "window_local_sec": [2.25, 2.58],
                "frames": 8,
                "editorial_justification": "Deadpan 8-frame pause as drill instructor narrows eyes before single nod.",
            },
            "primary_actors": [inst_var["archetype_id"], rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[6]["text"],
            "visual_summary": (
                "Unbroken crimson shield wall holds firm with desynchronized breathing troops; camera pushes in to "
                "drill instructor narrowing his eyes in a brief deadpan pause before nodding once."
            ),
            "sfx": [
                {"name": "sfx/kh03_armor_nod_settle.wav", "at": 2.82, "gain": -6.5},
            ],
        },
        {
            "id": "SH08",
            "index": 8,
            "start": 23.00,
            "end": 26.50,
            "duration": 3.50,
            "frame_start": 552,
            "frame_end": 635,
            "beat_role": "COMIC_TWIST",
            "purpose": "rookie_exhales_then_discovers_spear_caught_in_neighbor_strap",
            "framing_scale": "medium_two_shot",
            "camera_trajectory": "pull_back_comic_reveal",
            "stage_axis_sign": 1,
            "gap_state_start": "SEALED_TIGHT",
            "gap_state_end": "SEALED_TIGHT",
            "snagged_spear_start": True,
            "snagged_spear_end": True,
            "primary_actors": [rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[7]["text"],
            "visual_summary": (
                "Rookie exhales in relief, then tugs his spear—discovering its tip caught in his neighbor's leather "
                "scutum strap; awkward side-eye reaction while veteran neighbor stares deadpan."
            ),
            "sfx": [
                {"name": "sfx/kh03_leather_strap_tug.wav", "at": 1.05, "gain": -4.5},
                {"name": "sfx/kh03_leather_strap_tug.wav", "at": 2.02, "gain": -5.5},
            ],
        },
        {
            "id": "SH09",
            "index": 9,
            "start": 26.50,
            "end": 30.00,
            "duration": 3.50,
            "frame_start": 636,
            "frame_end": 719,
            "beat_role": "OUTRO_LOOP",
            "purpose": "instructor_deadpan_nod_and_return_to_closed_red_scutum_seam",
            "framing_scale": "motif_return_close",
            "camera_trajectory": "lateral_glide_to_sealed_seam",
            "stage_axis_sign": 1,
            "gap_state_start": "SEALED_TIGHT",
            "gap_state_end": "SEALED_TIGHT",
            "snagged_spear_start": True,
            "snagged_spear_end": True,
            "primary_actors": [inst_var["archetype_id"], rookie_var["archetype_id"], neigh_var["archetype_id"]],
            "narration": CANONICAL_SCRIPT_LINES[8]["text"],
            "visual_summary": (
                "Side reaction of unsmiling instructor giving one final crisp nod, gliding back to foreground "
                "close-up of the tightly locked red scutum rims in warm dawn light (loop-ready motif payoff)."
            ),
            "sfx": [
                {"name": "sfx/kh03_armor_nod_settle.wav", "at": 1.08, "gain": -6.0},
                {"name": "sfx/kh03_shield_wall_lock.wav", "at": 2.35, "gain": -7.0},
            ],
        },
    ]

    # Validate exact 30.000s contiguity & framing diversity
    t_cursor = 0.0
    purposes = set()
    for b in beats:
        if abs(b["start"] - t_cursor) > 1e-6:
            raise ValueError(f"Beat timing gap/overlap at {b['id']}: start={b['start']} vs expected={t_cursor}")
        t_cursor = b["end"]
        purposes.add((b["framing_scale"], b["purpose"]))
    if abs(t_cursor - 30.0) > 1e-6:
        raise ValueError(f"Total pilot duration must be exactly 30.000s; got {t_cursor}")
    if len(purposes) < 7:
        raise ValueError(f"Expected >= 7 distinct shot purposes/framings; got {len(purposes)}")

    if script is not None:
        norm = " ".join(script.strip().split())
        expected = " ".join(x["text"] for x in CANONICAL_SCRIPT_LINES)
        if not norm:
            raise ValueError("Provided script is empty")
    return beats


def _generate_pilot_scene_js() -> str:
    """Return deterministic, manifest-driven Canvas2D scene code for SH01..SH09."""
    return """// last_gap_pilot.js — Fresh 100% Canvas2D Procedural Shots SH01..SH09 for KH-03.0 Pilot.
// Uses ONLY Production Squire primitives + opt-in roman_master/{motion,character_state,camera,environment}.
// Zero Three.js, zero external bitmaps, zero reused demo plates, zero mutable frame-to-frame state.
import { E, clamp, lerp, registerShot } from '/engine/core.js';
import {
  OUT, PAL, shape, rect, ellipse, circ, polyS, line, tube, alpha, mix, haze, vignette,
  soldier, shield, weapon, dustPuff,
  sampleTrack, romanActorAt, drawRomanMasterActor2D,
  evaluateRomanCameraAt, drawRomanParallaxPlanes,
  drawRomanDawnSkyAndHills, drawRomanGateAndRamp2D, drawRomanDrillGroundPlane,
  drawRomanCohortLine2D, drawRomanTrainingRack2D, drawRomanTrainingYard2D, drawRomanShieldWall2D, drawWoodenPracticeSpear2D,
} from '/packs/squire/pack.js';

function camFor(shotId, globalT, fallback) {
  const beats = E.kh03?.camBeats?.shots || {};
  const spec = beats[shotId] || fallback;
  return evaluateRomanCameraAt(shotId, globalT, { [shotId]: spec });
}

// ============================================================================
// SH01 (0.00 - 2.50s): HOOK — Extreme close-up of shaking red scutum edge,
// sunlit gap sliver, and blunt wooden practice spear approaching from left.
// ============================================================================
registerShot('SH01', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? lt;
    const W = E.W, H = E.H;
    const cam = camFor('SH01', gt, {
      start: 0.0, end: 2.5, framingScale: 'extreme_detail_insert', purpose: 'hook_exposed_gap',
      zoomKeys: [[0.0, 1.06, 'c1'], [2.5, 1.22, 'c1']],
      cxKeys: [[0.0, 0.50, 'c1'], [2.5, 0.52, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [2.5, 0.49, 'c1']],
    });

    const gapPx = sampleTrack(lt, [[0.0, 118, 'c1'], [1.1, 108, 'c1'], [2.5, 96, 'c1']], 110);
    const tremorPx = Math.sin(gt * 41.0) * 4.8 * sampleTrack(lt, [[0.0, 1.0, 'c1'], [1.8, 0.72, 'c1'], [2.5, 0.55, 'c1']], 0.8);
    const spearX = sampleTrack(lt, [[0.0, 0.14, 'c1'], [0.35, 0.24, 'c1'], [2.5, 0.445, 'c1']], 0.25) * W;
    const spearY = sampleTrack(lt, [[0.0, 0.45, 'c1'], [2.5, 0.485, 'c1']], 0.47) * H;

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 8,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.58, sunX: 0.51, sunY: 0.43, seed: 17 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.58, chalkLineY: 0.86, seed: 23 });
          drawRomanCohortLine2D(c, { globalT: gt }, { y: 0.69, hFrac: 0.17, x0: 0.18, x1: 0.84, count: 6, seed: 61 });
        },
      },
      {
        depth: 0.78,
        blurPx: 1.5,
        draw: (c) => {
          // Approaching harmless wooden practice spear slicing through the dawn sunbeam toward the gap
          drawWoodenPracticeSpear2D(c, spearX, spearY, H * 0.34, -Math.PI / 2 + 0.055, { smear: 0.45 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: gapPx,
            gapCenterX: 0.515,
            wallY: 1.04,
            shieldScaleH: 0.98,
            drawNeighborShields: true,
            rookieTremorPx: tremorPx,
            rookieDropPx: 14,
            rookieRot: 0.055,
            showSunSliver: true,
          });
          // Rookie's white round Squire glove visible gripping the inner edge of the right scutum
          const gloveX = W * 0.515 + gapPx * 0.5 + 34 + tremorPx;
          const gloveY = H * 0.58 + Math.sin(gt * 28) * 2.0;
          circ(c, gloveX, gloveY, H * 0.036, { fill: '#ffffff', lw: 4.2 });
          ellipse(c, gloveX - H * 0.022, gloveY - H * 0.014, H * 0.016, H * 0.012, { fill: '#ffffff', lw: 3.4, rot: -0.5 });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH02 (2.50 - 5.50s): REVEAL — Medium over-shoulder on rookie hastatus
// noticing the exposed shield gap and tightening his grip.
// ============================================================================
registerShot('SH02', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (2.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH02', gt, {
      start: 2.5, end: 5.5, framingScale: 'medium_over_shoulder', purpose: 'character_reveal_grip',
      zoomKeys: [[0.0, 1.04, 'c1'], [3.0, 1.13, 'c1']],
      cxKeys: [[0.0, 0.53, 'c1'], [3.0, 0.50, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.0, 0.48, 'c1']],
    });

    const rookiePose = romanActorAt(gt, {
      start: 2.5,
      end: 5.5,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.78,
          xFrac: 0.58,
          yFrac: 1.14,
          lookKeys: [[0.0, 0.12, 'c1'], [0.55, -0.58, 'c1'], [3.0, -0.62, 'c1']],
          faceKeys: [[0.0, 'neutral'], [0.50, 'focused'], [1.25, 'worried']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.1, -0.025, 'c1'], [3.0, -0.015, 'c1']],
          headNodKeys: [[0.0, 0.0, 'c1'], [0.8, 1.4, 'c1'], [2.0, 0.6, 'c1']],
          shieldOffsetUKeys: [[0.0, [-15.5, -37.0], 'c1'], [1.2, [-12.0, -38.0], 'c1'], [2.6, [-9.5, -38.2], 'c1']],
          shieldRotKeys: [[0.0, 0.06, 'c1'], [1.4, 0.01, 'c1'], [3.0, -0.02, 'c1']],
          rightHandUKeys: [[0.0, [16.5, -35.0], 'c1'], [1.3, [15.2, -37.5], 'c1'], [3.0, [15.0, -37.0], 'c1']],
          weaponAngKeys: [[0.0, Math.PI + 0.18, 'c1'], [1.4, Math.PI + 0.11, 'c1'], [3.0, Math.PI + 0.12, 'c1']],
          tremorKeys: [[0.0, 0.55, 'c1'], [1.6, 0.15, 'c1'], [3.0, 0.0, 'c1']],
          phaseKeys: [[0.0, 'anticipation'], [1.1, 'action'], [2.2, 'settle']],
        },
      },
    }, 'rookie', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.30,
        blurPx: 6.5,
        draw: (c) => {
          drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.64, gateX: 0.18, showCohort: true, showRack: false });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          // Warm sun sliver visible to the left of the rookie before his shield closes it
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: sampleTrack(lt, [[0.0, 92, 'c1'], [3.0, 76, 'c1']], 84),
            gapCenterX: 0.355,
            wallY: 0.96,
            shieldScaleH: 0.56,
            drawNeighborShields: false,
            showSunSliver: true,
          });
          drawRomanMasterActor2D(c, rookiePose, { polish: true, seed: 11 });
        },
      },
      {
        depth: 1.16,
        blurPx: 3.5,
        draw: (c) => {
          // Over-shoulder foreground edge of neighbor's red scutum on screen-left
          shield(c, W * 0.14, H * 0.63, H * 0.72, {
            type: 'scutum',
            color: PAL.red,
            rim: PAL.gold,
            charge: 'wings',
            chargeColor: PAL.yellow,
            romanMasterPolish: true,
            rot: -0.02,
          });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH03 (5.50 - 9.00s): WIDE GEOGRAPHY — Full Roman training ground at dawn:
// castra gate/ramp on left, shield cohort with open gap on right, instructor spotting it.
// ============================================================================
registerShot('SH03', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (5.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH03', gt, {
      start: 5.5, end: 9.0, framingScale: 'wide_geography', purpose: 'establish_castra_and_line',
      zoomKeys: [[0.0, 1.01, 'c1'], [3.5, 1.08, 'c1']],
      cxKeys: [[0.0, 0.46, 'c1'], [3.5, 0.53, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.5, 0.51, 'c1']],
    });

    const instructorPose = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.39,
          rootXKeys: [[0.0, 0.20, 'c1'], [1.4, 0.225, 'c1'], [3.5, 0.225, 'hold']],
          rootYKeys: [[0.0, 0.875, 'c1'], [3.5, 0.875, 'hold']],
          leftFootXKeys: [[0.0, 0.186, 'c1'], [1.4, 0.210, 'c1'], [3.5, 0.210, 'hold']],
          rightFootXKeys: [[0.0, 0.214, 'c1'], [1.4, 0.242, 'c1'], [3.5, 0.242, 'hold']],
          lookKeys: [[0.0, 0.45, 'c1'], [1.2, 0.72, 'c1']],
          faceKeys: [[0.0, 'neutral'], [1.1, 'focused'], [2.4, 'determined']],
          shieldOffsetUKeys: [[0.0, [-13, -38], 'c1'], [3.5, [-14, -38], 'c1']],
          rightHandUKeys: [[0.0, [15, -36], 'c1'], [1.8, [20, -48], 'c1'], [3.5, [22, -52], 'c1']],
          weapon: 'none',
        },
      },
    }, 'instructor', { W, H });

    const rookieWide = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.38,
          xFrac: 0.695,
          yFrac: 0.885,
          flip: true,
          lookKeys: [[0.0, 0.35, 'c1'], [2.0, 0.65, 'c1']],
          faceKeys: [[0.0, 'worried'], [2.2, 'focused']],
          shieldOffsetUKeys: [[0.0, [-14, -37], 'c1'], [2.0, [-11, -37.5], 'c1'], [3.5, [-12, -37.5], 'c1']],
          weaponAngKeys: [[0.0, Math.PI + 0.16, 'c1'], [3.5, Math.PI + 0.12, 'c1']],
          tremorKeys: [[0.0, 0.35, 'c1'], [3.5, 0.2, 'c1']],
        },
      },
    }, 'rookie', { W, H });

    const neighborWide = romanActorAt(gt, {
      start: 5.5,
      end: 9.0,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.38,
          xFrac: 0.585,
          yFrac: 0.885,
          flip: true,
          look: 0.4,
          face: 'determined',
          shieldOffsetU: [2.5, -38],
          shieldRot: 0.0,
          weaponAng: Math.PI + 0.08,
        },
      },
    }, 'neighbor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.22,
        blurPx: 2.0,
        draw: (c) => drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.65, sunX: 0.64, sunY: 0.33, seed: 17 }),
      },
      {
        depth: 0.55,
        blurPx: 0.8,
        draw: (c) => {
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.14, scale: 0.32 });
          drawRomanCohortLine2D(c, { globalT: gt }, { y: 0.72, hFrac: 0.145, x0: 0.40, x1: 0.82, count: 7, flip: true, seed: 71 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.65, chalkLineY: 0.885, seed: 23 });
          drawRomanTrainingRack2D(c, W * 0.11, H * 0.84, H * 0.19, { withPalus: false, spearCount: 3 });
          drawRomanTrainingRack2D(c, W * 0.89, H * 0.83, H * 0.20, { withPalus: true, spearCount: 4 });

          // Front shield-wall squad with sunlit gap between neighbor (0.585) and rookie (0.695)
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: 42,
            gapCenterX: 0.64,
            wallY: 0.885,
            shieldScaleH: 0.24,
            drawNeighborShields: false,
            showSunSliver: true,
          });
          for (let i = 0; i < 3; i++) {
            const fx = W * (0.435 + i * 0.05);
            soldier(c, fx, H * 0.885, H * 0.38, {
              preset: 'hastatus',
              flip: true,
              pose: 'stand',
              face: i === 1 ? 'focused' : 'determined',
              t: gt + i * 0.83,
              seed: 90 + i * 7,
              romanMasterPolish: true,
              armsAng: [-28, -45, 14, 10],
              weaponAng: Math.PI + 0.08,
              shield: { type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'lightning', chargeColor: PAL.yellow, x: 3, y: -38, s: 62, rot: 0 },
              lod: 'high',
            });
          }
          drawRomanMasterActor2D(c, neighborWide, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookieWide, { polish: true, seed: 11 });

          // Instructor on left holding wooden practice spear ready to test the gap
          drawRomanMasterActor2D(c, instructorPose, { polish: true, seed: 21 });
          const rh = instructorPose.rightHandWorld;
          const aimAng = sampleTrack(lt, [[0.0, Math.PI * 0.82, 'c1'], [2.0, Math.PI * 0.53, 'c1'], [3.5, Math.PI * 0.49, 'c1']], Math.PI * 0.52);
          drawWoodenPracticeSpear2D(c, rh[0], rh[1], H * 0.26, -aimAng);
        },
      },
    ]);
    vignette(g, 0.16);
  },
});

// ============================================================================
// SH04 (9.00 - 12.00s): BEAT — Low-angle profile of instructor launching
// harmless wooden practice spear strictly left-to-right across stage axis.
// ============================================================================
registerShot('SH04', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (9.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH04', gt, {
      start: 9.0, end: 12.0, framingScale: 'low_angle_profile', purpose: 'inciting_spear_launch',
      zoomKeys: [[0.0, 1.05, 'c1'], [0.85, 1.12, 'c1'], [1.35, 1.06, 'c1'], [3.0, 1.10, 'c1']],
      cxKeys: [[0.0, 0.42, 'c1'], [0.95, 0.40, 'c1'], [1.6, 0.54, 'c1'], [3.0, 0.58, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [3.0, 0.50, 'c1']],
    });

    const releaseT = 0.96;
    const instPose = romanActorAt(gt, {
      start: 9.0,
      end: 12.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.64,
          rootXKeys: [[0.0, 0.34, 'c1'], [0.70, 0.325, 'c1'], [1.02, 0.375, 'c1'], [1.6, 0.372, 'c1']],
          rootYKeys: [[0.0, 0.96, 'c1'], [3.0, 0.96, 'hold']],
          leftFootXKeys: [[0.0, 0.31, 'c1'], [0.7, 0.30, 'c1'], [1.02, 0.30, 'hold'], [3.0, 0.30, 'hold']],
          rightFootXKeys: [[0.0, 0.37, 'c1'], [0.65, 0.36, 'c1'], [0.95, 0.425, 'c1'], [3.0, 0.425, 'hold']],
          bodyRotKeys: [[0.0, -0.02, 'c1'], [0.72, -0.10, 'c1'], [1.02, 0.11, 'c1'], [1.65, 0.05, 'c1']],
          lookKeys: [[0.0, 0.65, 'c1'], [3.0, 0.78, 'c1']],
          faceKeys: [[0.0, 'focused'], [0.72, 'determined'], [1.3, 'sternNod']],
          shieldOffsetUKeys: [[0.0, [-15, -36], 'c1'], [0.95, [-18, -35], 'c1'], [1.6, [-14, -37], 'c1']],
          rightHandUKeys: [
            [0.0, [8.0, -46.0], 'c1'],
            [0.72, [-14.0, -58.0], 'c1'],
            [0.98, [22.5, -53.0], 'outCubic'],
            [1.45, [19.0, -44.0], 'c1'],
            [3.0, [16.5, -40.0], 'c1'],
          ],
          weapon: 'none',
          phaseKeys: [[0.0, 'anticipation'], [0.72, 'action'], [0.96, 'contact'], [1.35, 'settle']],
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 4.0,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.76, sunX: 0.76, sunY: 0.38, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.76, gateX: 0.16, scale: 0.38 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.76, chalkLineY: 0.96, seed: 29 });
          if (lt >= 0.88 && lt <= 1.75) {
            dustPuff(c, W * 0.425, H * 0.955, H * 0.085, (1 - (lt - 0.88) / 0.87) * 0.65, gt);
          }
          drawRomanMasterActor2D(c, instPose, { polish: true, seed: 21, shoeMode: 'side' });

          // Wooden practice spear: locked in instructor's right hand before releaseT, then flying ballistic left->right
          const spearLen = H * 0.42;
          if (lt <= releaseT) {
            const rh = instPose.rightHandWorld;
            const windAng = sampleTrack(lt, [[0.0, -Math.PI * 0.48, 'c1'], [0.72, -Math.PI * 0.54, 'c1'], [releaseT, -Math.PI * 0.49, 'c1']], -Math.PI * 0.5);
            drawWoodenPracticeSpear2D(c, rh[0], rh[1], spearLen, windAng, { smear: lt > 0.78 ? 0.45 : 0 });
          } else {
            const flyDt = lt - releaseT;
            const sx = instPose.rightHandWorld[0] + flyDt * W * 0.78;
            const sy = instPose.rightHandWorld[1] - flyDt * H * 0.06 + flyDt * flyDt * H * 0.045;
            if (sx < W * 1.35) {
              drawWoodenPracticeSpear2D(c, sx, sy, spearLen, -Math.PI * 0.49 + flyDt * 0.04, { smear: 0.78 });
            }
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH05 (12.00 - 15.00s): ACTION — Tracking shot as rookie plants sandal and
// shoves his red scutum leftward into the shield wall to seal the gap.
// ============================================================================
registerShot('SH05', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (12.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH05', gt, {
      start: 12.0, end: 15.0, framingScale: 'medium_full_tracking', purpose: 'foot_plant_and_shield_shove',
      zoomKeys: [[0.0, 1.06, 'c1'], [1.05, 1.14, 'c1'], [1.75, 1.18, 'c1'], [3.0, 1.15, 'c1']],
      cxKeys: [[0.0, 0.58, 'c1'], [1.65, 0.51, 'c1'], [3.0, 0.50, 'c1']],
      cyKeys: [[0.0, 0.54, 'c1'], [3.0, 0.53, 'c1']],
      impactImpulse: { atLocal: 1.65, dur: 0.22, ampPx: 6.0 },
    });

    const neighborPose = romanActorAt(gt, {
      start: 12.0,
      end: 15.0,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.58,
          xFrac: 0.41,
          yFrac: 0.93,
          flip: true,
          leftFootXKeys: [[0.0, 0.445, 'hold'], [3.0, 0.445, 'hold']],
          rightFootXKeys: [[0.0, 0.375, 'hold'], [3.0, 0.375, 'hold']],
          lookKeys: [[0.0, 0.45, 'c1'], [1.65, 0.25, 'c1']],
          faceKeys: [[0.0, 'determined'], [1.65, 'focused']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.65, 0.0, 'c1'], [1.78, -0.02, 'c1'], [2.2, 0.0, 'c1']],
          shieldOffsetUKeys: [[0.0, [3.0, -38.0], 'c1'], [3.0, [3.0, -38.0], 'hold']],
          shieldRot: 0.0,
          weaponAng: Math.PI + 0.12,
        },
      },
    }, 'neighbor', { W, H });

    const rookiePose = romanActorAt(gt, {
      start: 12.0,
      end: 15.0,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.58,
          flip: true,
          // Anticipation coil (0..0.45s) -> Lead sandal step & plant (0.45..1.02s) -> Shield shove & rear follow-plant (1.02..1.65s) -> Settle (1.65..3.0s)
          rootXKeys: [
            [0.0, 0.595, 'c1'],
            [0.45, 0.598, 'c1'],
            [1.02, 0.578, 'c1'],
            [1.65, 0.556, 'outCubic'],
            [1.85, 0.558, 'c1'],
            [3.0, 0.558, 'hold'],
          ],
          rootYKeys: [
            [0.0, 0.93, 'c1'],
            [0.45, 0.935, 'c1'],
            [1.02, 0.93, 'c1'],
            [1.65, 0.93, 'c1'],
            [3.0, 0.93, 'hold'],
          ],
          // Two-phase world-locked footwork within exact 28.3u anatomical leg reach (0.00px drift!)
          leftFootXKeys: [
            [0.0, 0.615, 'hold'],
            [1.05, 0.615, 'c1'],
            [1.58, 0.578, 'outCubic'],
            [3.0, 0.578, 'hold'],
          ],
          leftFootYKeys: [
            [0.0, 0.93, 'hold'],
            [1.05, 0.93, 'c1'],
            [1.30, 0.914, 'c1'],
            [1.58, 0.93, 'outCubic'],
            [3.0, 0.93, 'hold'],
          ],
          rightFootXKeys: [
            [0.0, 0.575, 'hold'],
            [0.45, 0.575, 'c1'],
            [1.02, 0.536, 'outCubic'],
            [3.0, 0.536, 'hold'],
          ],
          rightFootYKeys: [
            [0.0, 0.93, 'hold'],
            [0.45, 0.93, 'c1'],
            [0.74, 0.904, 'c1'],
            [1.02, 0.93, 'outCubic'],
            [3.0, 0.93, 'hold'],
          ],
          bodyRotKeys: [
            [0.0, 0.0, 'hold'],
            [3.0, 0.0, 'hold'],
          ],
          headNodKeys: [
            [0.0, -0.5, 'c1'],
            [0.45, -1.2, 'c1'],
            [1.65, 2.2, 'outCubic'],
            [2.10, 1.0, 'c1'],
            [3.0, 1.0, 'hold'],
          ],
          lookKeys: [[0.0, 0.65, 'c1'], [1.65, 0.55, 'c1']],
          faceKeys: [[0.0, 'shock'], [0.55, 'determined'], [1.65, 'focused']],
          shieldOffsetUKeys: [
            [0.0, [-13.0, -37.5], 'c1'],
            [0.50, [-15.0, -37.0], 'c1'],
            [1.65, [5.2, -38.0], 'outCubic'],
            [3.0, [4.6, -38.0], 'c1'],
          ],
          shieldRotKeys: [[0.0, 0.05, 'c1'], [1.65, 0.0, 'outCubic'], [3.0, 0.0, 'hold']],
          rightHandUKeys: [[0.0, [16.0, -36.0], 'c1'], [1.65, [12.5, -37.5], 'c1'], [3.0, [12.5, -37.5], 'hold']],
          weaponAngKeys: [[0.0, Math.PI + 0.15, 'c1'], [1.65, Math.PI - 0.14, 'c1'], [3.0, Math.PI - 0.14, 'hold']],
          phaseKeys: [[0.0, 'anticipation'], [0.50, 'action'], [1.65, 'contact'], [2.1, 'settle']],
        },
      },
    }, 'rookie', { W, H });

    const gapRemainingPx = sampleTrack(lt, [[0.0, 96, 'c1'], [0.50, 102, 'c1'], [1.65, 0, 'outCubic'], [3.0, 0, 'hold']], 0);

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.30,
        blurPx: 4.5,
        draw: (c) => drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.14, showCohort: true }),
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.66, chalkLineY: 0.93, seed: 23 });
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: gapRemainingPx,
            gapCenterX: 0.485,
            wallY: 0.93,
            shieldScaleH: 0.36,
            drawNeighborShields: false,
            showSunSliver: gapRemainingPx > 3,
          });

          // Sand dust burst right as front sandal plants at lt=1.02s
          if (lt >= 1.00 && lt <= 1.95) {
            dustPuff(c, W * 0.522, H * 0.932, H * 0.095, (1 - (lt - 1.00) / 0.95) * 0.75, gt);
          }

          drawRomanMasterActor2D(c, neighborPose, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookiePose, { polish: true, seed: 11, shoeMode: 'side' });

          // Incoming wooden practice spear streaking in from screen-left during final 0.42s before cut to insert
          if (lt >= 2.52) {
            const p = (lt - 2.52) / 0.48;
            const spX = lerp(-W * 0.08, W * 0.36, p);
            const spY = lerp(H * 0.61, H * 0.65, p);
            drawWoodenPracticeSpear2D(c, spX, spY, H * 0.32, -Math.PI * 0.48, { smear: 0.85 });
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH06 (15.00 - 18.50s): INSERT — Blunt wooden spear tip strikes the newly
// closed red/gold scutum rim at 24fps, compresses, and glances harmlessly aside.
// ============================================================================
registerShot('SH06', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (15.0 + lt);
    const W = E.W, H = E.H;
    const hitT = 0.58;
    const cam = camFor('SH06', gt, {
      start: 15.0, end: 18.5, framingScale: 'macro_physics_insert', purpose: 'wooden_tip_deflection',
      zoomKeys: [[0.0, 1.12, 'c1'], [hitT, 1.24, 'outCubic'], [1.4, 1.16, 'c1'], [3.5, 1.10, 'c1']],
      cxKeys: [[0.0, 0.47, 'c1'], [hitT, 0.51, 'c1'], [2.4, 0.46, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [hitT, 0.50, 'c1'], [2.4, 0.56, 'c1']],
      impactImpulse: { atLocal: hitT, dur: 0.26, ampPx: 9.5 },
    });

    // Shield recoil curve: rock-solid absorb (5.5px peak at hitT + 0.06s, damped back to 0)
    const recoilPx = lt < hitT
      ? 0
      : Math.max(0, Math.sin(Math.min(Math.PI, ((lt - hitT) / 0.24) * Math.PI)) * 7.5);

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 9.0,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.60, sunX: 0.52, sunY: 0.40, seed: 17 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.60, chalkLineY: 0.88, seed: 23 });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          // Sealed crimson-and-gold scutum wall (gap = 0px!)
          const seamX = W * 0.53 + recoilPx;
          const shieldS = H * 0.94;
          const rx = shieldS * 0.33;
          shield(c, seamX - rx * 0.95, H * 0.56, shieldS, {
            type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'wings', chargeColor: PAL.yellow,
            romanMasterPolish: true, rot: -0.01,
          });
          shield(c, seamX + rx * 0.95, H * 0.56, shieldS, {
            type: 'scutum', color: PAL.red, rim: PAL.gold, charge: 'lightning', chargeColor: PAL.yellow,
            romanMasterPolish: true, rot: 0.012,
          });

          // Contact flash & wood-dust ring during 4 impact frames around hitT
          const hitContactX = seamX + 12;
          const hitContactY = H * 0.49;
          if (lt >= hitT - 0.02 && lt <= hitT + 0.36) {
            const k = clamp((lt - (hitT - 0.02)) / 0.38, 0, 1);
            for (let i = 0; i < 7; i++) {
              const ang = Math.PI * (0.62 + i * 0.13);
              const r0 = 14 + k * 54;
              const r1 = 30 + k * 92;
              line(c, [
                [hitContactX + Math.cos(ang) * r0, hitContactY + Math.sin(ang) * r0],
                [hitContactX + Math.cos(ang) * r1, hitContactY + Math.sin(ang) * r1],
              ], { lw: 4.5 * (1 - k), ink: i % 2 ? '#ffe596' : '#e6c58e', a: 1 - k });
            }
            dustPuff(c, hitContactX - 18, hitContactY, H * 0.09, (1 - k) * 0.72, gt);
          }

          // Wooden practice spear trajectory: fast approach -> 2-frame pad squash -> spinning glance bounce -> sand rest
          const spLen = H * 0.44;
          if (lt < hitT) {
            const k = clamp(lt / hitT, 0, 1);
            const tipX = lerp(W * 0.06, hitContactX, k);
            const tipY = lerp(H * 0.44, hitContactY, k);
            const ang = -Math.PI * 0.47;
            // Draw shaft so tip (+0.93L along local +Y) lands at (tipX, tipY)
            const hx = tipX + Math.sin(ang) * (spLen * 0.93);
            const hy = tipY - Math.cos(ang) * (spLen * 0.93);
            drawWoodenPracticeSpear2D(c, hx, hy, spLen, ang, { smear: 0.85 });
          } else if (lt <= hitT + 0.09) {
            // Squash contact frame on gold rim
            const ang = -Math.PI * 0.43;
            const hx = hitContactX + Math.sin(ang) * (spLen * 0.90);
            const hy = hitContactY - Math.cos(ang) * (spLen * 0.90);
            c.save();
            c.translate(hitContactX, hitContactY);
            c.scale(0.92, 1.06);
            c.translate(-hitContactX, -hitContactY);
            drawWoodenPracticeSpear2D(c, hx, hy, spLen, ang, { smear: 0.2 });
            c.restore();
          } else {
            const dt = lt - (hitT + 0.09);
            const landDt = 1.52;
            const bDt = Math.min(dt, landDt);
            const cxSp = hitContactX - spLen * 0.42 - bDt * W * 0.16;
            const cySp = hitContactY - spLen * 0.06 - bDt * H * 0.18 + bDt * bDt * H * 0.31;
            const spinAng = -Math.PI * 0.43 - bDt * 2.55;
            const settleAng = dt > landDt ? spinAng + Math.sin((dt - landDt) * 14) * 0.04 * Math.max(0, 1 - (dt - landDt)) : spinAng;
            drawWoodenPracticeSpear2D(c, cxSp, cySp, spLen, settleAng, { smear: dt < landDt ? 0.32 : 0 });
            if (dt >= landDt && dt <= landDt + 0.55) {
              dustPuff(c, cxSp, cySp + 16, H * 0.065, (1 - (dt - landDt) / 0.55) * 0.55, gt);
            }
          }
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH07 (18.50 - 23.00s): PAYOFF — Unbroken shield line holds; camera pushes in
// as drill instructor narrows his eyes (8-frame intentional hold) then nods once.
// ============================================================================
registerShot('SH07', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (18.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH07', gt, {
      start: 18.5, end: 23.0, framingScale: 'wide_to_medium_payoff', purpose: 'wall_holds_instructor_evaluates',
      zoomKeys: [[0.0, 1.02, 'c1'], [1.5, 1.18, 'c1'], [3.2, 1.36, 'c1'], [4.5, 1.38, 'c1']],
      cxKeys: [[0.0, 0.50, 'c1'], [1.6, 0.36, 'c1'], [3.2, 0.29, 'c1'], [4.5, 0.29, 'c1']],
      cyKeys: [[0.0, 0.52, 'c1'], [3.2, 0.48, 'c1'], [4.5, 0.48, 'c1']],
    });

    const instPayoff = romanActorAt(gt, {
      start: 18.5,
      end: 23.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.48,
          xFrac: 0.26,
          yFrac: 0.91,
          lookKeys: [[0.0, 0.65, 'c1'], [2.25, 0.65, 'hold'], [4.5, 0.62, 'c1']],
          faceKeys: [[0.0, 'determined'], [1.65, 'focused'], [2.65, 'sternNod']],
          // Intentional 8-frame hold [2.25..2.58s], followed by single crisp downward nod [2.65..3.45s]
          headNodKeys: [
            [0.0, 0.0, 'c1'],
            [2.25, 0.0, 'hold'],
            [2.58, 0.0, 'hold'],
            [2.95, 3.4, 'c1'],
            [3.45, 0.2, 'c1'],
            [4.5, 0.2, 'hold'],
          ],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [2.25, 0.02, 'hold'], [2.58, 0.02, 'hold'], [2.95, 0.04, 'c1'], [3.5, 0.02, 'c1']],
          shieldOffsetU: [-14, -38],
          rightHandU: [15.5, -36.5],
          weapon: 'pilum',
          weaponAng: Math.PI + 0.14,
          phaseKeys: [[0.0, 'settle'], [2.25, 'hold'], [2.60, 'reaction'], [3.5, 'settle']],
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.25,
        blurPx: 2.5,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.66, sunX: 0.68, sunY: 0.32, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.66, gateX: 0.13, scale: 0.32 });
        },
      },
      {
        depth: 0.72,
        blurPx: 1.2,
        draw: (c) => {
          // Desynchronized background Roman squad holding locked crimson shield wall (zero gap!)
          drawRomanCohortLine2D(c, { globalT: gt }, {
            y: 0.84, hFrac: 0.34, x0: 0.48, x1: 0.88, count: 6, flip: true, shieldXU: 4.5, seed: 107,
          });
        },
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.66, chalkLineY: 0.91, seed: 23 });
          // Deflected wooden practice spear resting harmlessly on the sand in front of the wall
          drawWoodenPracticeSpear2D(c, W * 0.46, H * 0.915, H * 0.22, -Math.PI * 0.52);
          drawRomanMasterActor2D(c, instPayoff, { polish: true, seed: 21 });
        },
      },
    ]);
    vignette(g, 0.17);
  },
});

// ============================================================================
// SH08 (23.00 - 26.50s): TWIST — Rookie exhales in relief, then tugs his own
// spear and realizes it is caught in his neighbor's leather shield strap!
// ============================================================================
registerShot('SH08', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (23.0 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH08', gt, {
      start: 23.0, end: 26.5, framingScale: 'medium_two_shot', purpose: 'comic_spear_strap_twist',
      zoomKeys: [[0.0, 1.18, 'c1'], [1.2, 1.10, 'c1'], [3.5, 1.08, 'c1']],
      cxKeys: [[0.0, 0.54, 'c1'], [1.4, 0.51, 'c1'], [3.5, 0.50, 'c1']],
      cyKeys: [[0.0, 0.51, 'c1'], [3.5, 0.52, 'c1']],
    });

    const tugPulse = (lt >= 1.02 && lt <= 1.42 ? Math.sin(((lt - 1.02) / 0.40) * Math.PI * 2) : 0)
      + (lt >= 1.98 && lt <= 2.38 ? Math.sin(((lt - 1.98) / 0.40) * Math.PI * 2) * 0.8 : 0);

    const neighborTwist = romanActorAt(gt, {
      start: 23.0,
      end: 26.5,
      actors: {
        neighbor: {
          archetypeId: 'veteran_neighbor_legionary',
          hFrac: 0.68,
          xFrac: 0.37,
          yFrac: 1.03,
          lookKeys: [[0.0, 0.15, 'c1'], [1.25, 0.72, 'c1'], [3.5, 0.75, 'hold']],
          faceKeys: [[0.0, 'determined'], [1.30, 'bored']],
          headRotKeys: [[0.0, 0.0, 'c1'], [1.35, 0.06, 'c1'], [3.5, 0.06, 'hold']],
          shieldOffsetUKeys: [[0.0, [5.0, -38.0], 'c1'], [3.5, [5.0 + tugPulse * 1.1, -38.0], 'c1']],
          shieldRot: -0.01 + tugPulse * 0.025,
          rightHandU: [-14.0, -36.0],
          weapon: 'none',
        },
      },
    }, 'neighbor', { W, H });

    const rookieTwist = romanActorAt(gt, {
      start: 23.0,
      end: 26.5,
      actors: {
        rookie: {
          archetypeId: 'rookie_hastatus',
          hFrac: 0.68,
          xFrac: 0.62,
          yFrac: 1.03,
          flip: true,
          lookKeys: [[0.0, 0.10, 'c1'], [0.85, 0.15, 'c1'], [1.20, 0.72, 'c1'], [3.5, 0.68, 'c1']],
          faceKeys: [[0.0, 'exhale'], [0.95, 'surprised'], [1.45, 'awkward']],
          headNodKeys: [[0.0, 2.2, 'c1'], [0.75, 3.0, 'c1'], [1.15, -0.6, 'c1'], [1.8, 0.8, 'c1']],
          bodyRotKeys: [[0.0, 0.02, 'c1'], [1.15, -0.03 + tugPulse * 0.03, 'c1'], [2.6, -0.015, 'c1']],
          shieldOffsetU: [3.5, -38.0],
          shieldRot: 0.01,
          rightHandUKeys: [
            [0.0, [13.5, -36.5], 'c1'],
            [1.05, [16.8, -41.5], 'c1'],
            [1.35, [14.2, -38.0], 'c1'],
            [2.05, [17.2, -42.0], 'c1'],
            [2.45, [14.8, -38.5], 'c1'],
          ],
          weapon: 'none',
          phaseKeys: [[0.0, 'settle'], [0.95, 'action'], [1.45, 'reaction']],
        },
      },
    }, 'rookie', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.28,
        blurPx: 6.0,
        draw: (c) => drawRomanTrainingYard2D(c, { globalT: gt }, cam, { groundY: 0.64, gateX: 0.16, showCohort: true }),
      },
      {
        depth: 1.0,
        blurPx: 0,
        draw: (c) => {
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.64, chalkLineY: 0.96, seed: 23 });
          drawRomanMasterActor2D(c, neighborTwist, { polish: true, seed: 31 });
          drawRomanMasterActor2D(c, rookieTwist, { polish: true, seed: 11 });

          // Visible leather strap loop on neighbor's right scutum edge + rookie's spear snagged through it!
          const strapX = neighborTwist.shieldGrip.rimRightWorld[0] - 8 + tugPulse * 5;
          const strapY = neighborTwist.shieldGrip.shieldCenterWorld[1] - 48;
          const rh = rookieTwist.rightHandWorld;
          const snaggedAng = Math.atan2(rh[0] - strapX, strapY - rh[1]);
          weapon(c, 'spear', rh[0], rh[1], rookieTwist.actorH * 0.66, snaggedAng, { lw: 3.8 });
          shape(
            c,
            (ctx) => {
              ctx.moveTo(strapX - 14, strapY - 12);
              ctx.quadraticCurveTo(strapX + 18, strapY, strapX - 12, strapY + 14);
            },
            { fill: null, lw: 6.5, ink: PAL.leather }
          );
          circ(c, strapX - 12, strapY - 12, 4, { fill: PAL.gold, lw: 2 });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});

// ============================================================================
// SH09 (26.50 - 30.00s): OUTRO / LOOP — Unsmiling instructor gives one crisp
// nod, gliding smoothly to the tightly sealed red scutum gap motif (loop-ready).
// ============================================================================
registerShot('SH09', {
  draw(g, lt, info) {
    const gt = info?.globalT ?? (26.5 + lt);
    const W = E.W, H = E.H;
    const cam = camFor('SH09', gt, {
      start: 26.5, end: 30.0, framingScale: 'motif_return_close', purpose: 'deadpan_nod_and_closed_wall_loop',
      zoomKeys: [[0.0, 1.06, 'c1'], [1.8, 1.14, 'c1'], [3.5, 1.22, 'c1']],
      cxKeys: [[0.0, 0.36, 'c1'], [1.7, 0.48, 'c1'], [3.5, 0.52, 'c1']],
      cyKeys: [[0.0, 0.50, 'c1'], [3.5, 0.51, 'c1']],
    });

    const instOutro = romanActorAt(gt, {
      start: 26.5,
      end: 30.0,
      actors: {
        instructor: {
          archetypeId: 'instructor_princeps',
          hFrac: 0.62,
          xFrac: 0.25,
          yFrac: 0.98,
          look: 0.62,
          face: 'sternNod',
          headNodKeys: [[0.0, 0.0, 'c1'], [0.85, 0.0, 'hold'], [1.18, 3.8, 'c1'], [1.62, 0.2, 'c1'], [3.5, 0.2, 'hold']],
          shieldOffsetU: [-14, -38],
          rightHandU: [15.5, -36.5],
          weapon: 'pilum',
          weaponAng: Math.PI + 0.14,
        },
      },
    }, 'instructor', { W, H });

    drawRomanParallaxPlanes(g, cam, [
      {
        depth: 0.26,
        blurPx: 5.5,
        draw: (c) => {
          drawRomanDawnSkyAndHills(c, { globalT: gt }, { groundY: 0.60, sunX: 0.53, sunY: 0.42, seed: 17 });
          drawRomanGateAndRamp2D(c, { globalT: gt }, cam, { groundY: 0.60, gateX: 0.12, scale: 0.28 });
          drawRomanDrillGroundPlane(c, { globalT: gt }, { groundY: 0.60, chalkLineY: 0.88, seed: 23 });
        },
      },
      {
        depth: 0.82,
        blurPx: 0.8,
        draw: (c) => {
          drawRomanMasterActor2D(c, instOutro, { polish: true, seed: 21 });
        },
      },
      {
        depth: 1.06,
        blurPx: 0,
        draw: (c) => {
          // Return to SH01 foreground red scutum motif — now locked flush with 0px gap!
          const wallX = lerp(W * 0.74, W * 0.56, sampleTrack(lt, [[0.0, 0.0, 'c1'], [2.2, 1.0, 'c1'], [3.5, 1.0, 'hold']], 1.0));
          drawRomanShieldWall2D(c, { globalT: gt }, cam, {
            gapWidthPx: 0,
            gapCenterX: wallX / W,
            wallY: 1.05,
            shieldScaleH: 0.90,
            drawNeighborShields: true,
            rookieTremorPx: 0,
            rookieDropPx: 0,
            rookieRot: 0.008,
            showSunSliver: false,
            showNeighborStrap: true,
            snaggedSpear: true,
          });
        },
      },
    ]);
    vignette(g, 0.18);
  },
});
"""


def _generate_thumb_js() -> str:
    return """// thumb.js — Original Squire Roman Thumbnail for KH-03.0 Pilot
import { thumb } from '/packs/squire/pack.js';

thumb({
  bg: 'roman_training_yard',
  time: 'dawn',
  seed: 17,
  blur: 6,
  heroes: [
    {
      preset: 'hastatus',
      full: true,
      x: 0.70,
      y: 1.03,
      h: 0.72,
      flip: true,
      face: 'shock',
      look: 0.6,
      romanMasterPolish: true,
      shield: { type: 'scutum', color: '#c9473a', rim: '#e7b04a', charge: 'lightning', chargeColor: '#efc23f', x: -10, y: -38, s: 62 },
    },
    {
      preset: 'princeps',
      full: true,
      x: 0.24,
      y: 1.02,
      h: 0.68,
      face: 'sternNod',
      look: 0.55,
      romanMasterPolish: true,
    },
  ],
  symbols: [
    { kind: 'wooden_practice_spear', x: 0.47, y: 0.58, r: 0.34, ang: -Math.PI * 0.48 },
  ],
  title: ['LAST GAP', 'SHIELD WALL'],
  tx: 0.50,
  ty: 0.11,
  tsize: 0.135,
  tgap: 0.145,
});
"""


def build_roman_preview_project(
    project_dir: Path | str = PILOT_PROJECT_DIR,
    style_bible: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Write all KH-03.0 pilot project manifests, script, storyboard, and 2D scene code atomically."""
    proj = Path(project_dir).resolve()
    sb = style_bible or load_roman_master_style()
    beats = compile_roman_training_beats(style_bible=sb)
    ref_info = collect_user_style_reference()

    for sub in ("story", "timeline", "scenes/shots", "sfx", "build", "out"):
        (proj / sub).mkdir(parents=True, exist_ok=True)

    config = {
        "title": OUTPUT_TITLE,
        "pack": "squire",
        "style_profile": "roman_squire_master.v1",
        "render_mode": "canvas2d_only",
        "aspect": "16:9",
        "resolution": "1080p",
        "fps": 24,
        "lang": "en",
        "style": "flat",
        "bars": "none",
        "captions": False,
        "fadeIn": 0,
        "fadeOut": 0,
        "transition": {"type": "cut", "duration": 0.0},
        "loudness": -15.0,
        "music": {"enabled": True, "gainDb": -14.0},
        "sfx": {"enabled": True, "gainDb": -3.0},
        "stills": [0.8, 3.8, 7.2, 10.1, 13.7, 15.65, 21.3, 24.8, 28.8],
        "pilot_scope_notice": (
            "KH-03.0 style-locked pilot only. Fictional dramatized Roman training-yard vignette. "
            "KH-03.1..KH-03.6 generalized engines are NOT implemented."
        ),
    }
    _atomic_write_json(proj / "config.json", config)

    full_script_txt = "\n".join(x["text"] for x in CANONICAL_SCRIPT_LINES) + "\n"
    _atomic_write_text(proj / "story" / "script.txt", full_script_txt)

    shots_json = {
        "schema_version": "kh03.0.shots.v1",
        "title": "THE LAST GAP IN THE SHIELD WALL",
        "fictional_dramatization": True,
        "duration": 30.0,
        "fps": 24,
        "total_frames": 720,
        "style_profile": "roman_squire_master.v1",
        "render_mode": "canvas2d_only",
        "music": [
            {"start": 0.0, "end": 30.0, "bed": "roman", "gainDb": -1.5},
        ],
        "shots": [
            {
                "id": b["id"],
                "start": b["start"],
                "end": b["end"],
                "line": b["narration"],
                "purpose": b["purpose"],
                "framing_scale": b["framing_scale"],
                "sfx": b["sfx"],
            }
            for b in beats
        ],
    }
    _atomic_write_json(proj / "story" / "shots.json", shots_json)

    storyboard = {
        "schema_version": "kh03.0.storyboard.v1",
        "working_title": "THE LAST GAP IN THE SHIELD WALL",
        "historical_framing": (
            "Original fictional dramatized Roman training-yard practice vignette; "
            "not attributed to a specific recorded ancient incident."
        ),
        "duration_sec": 30.0,
        "fps": 24,
        "total_frames": 720,
        "beats": beats,
    }
    _atomic_write_json(proj / "story" / "storyboard.json", storyboard)

    style_ref = {
        "style_id": sb["style_id"],
        "style_family": sb["style_family"],
        "canonical_digest": sb["canonical_digest"],
        "source_bible_path": "visual_styles/roman_squire_master/v1/style_bible.json",
        "user_screenshot_status": ref_info["status"],
        "forbid_reference_screenshot_in_video_frames": True,
    }
    _atomic_write_json(proj / "story" / "roman_master_style_ref.json", style_ref)

    char_bible = {
        "style_id": sb["style_id"],
        "characters": {
            "rookie": resolve_roman_variant("rookie", style_dict=sb),
            "instructor": resolve_roman_variant("instructor", style_dict=sb),
            "neighbor": resolve_roman_variant("neighbor", style_dict=sb),
        },
    }
    _atomic_write_json(proj / "story" / "character_bible.json", char_bible)

    env_bible = {
        "environment_id": "roman_training_yard",
        "time_of_day": "dawn",
        "stage_axis": "instructor_and_castra_gate_left_to_shield_wall_right",
        "landmarks": {
            "castra_timber_gate_and_ramp": {"world_x_norm": 0.15, "ground_y_norm": 0.66},
            "legionary_tents": {"world_x_range_norm": [0.44, 0.79], "ground_y_norm": 0.68},
            "shield_wall_chalk_line": {"world_x_range_norm": [0.38, 0.84], "ground_y_norm": 0.885},
            "wooden_practice_spear_rack_and_palus": {"world_x_norm": 0.89, "ground_y_norm": 0.77},
        },
    }
    _atomic_write_json(proj / "story" / "environment_bible.json", env_bible)

    props_manifest = {
        "props": [
            {
                "prop_id": "rookie_scutum",
                "owner": "rookie",
                "type": "scutum",
                "color": "#c9473a",
                "rim": "#e7b04a",
                "charge": "lightning",
            },
            {
                "prop_id": "neighbor_scutum_with_strap",
                "owner": "neighbor",
                "type": "scutum",
                "color": "#c9473a",
                "rim": "#e7b04a",
                "charge": "wings",
                "has_inner_leather_strap": True,
            },
            {
                "prop_id": "rookie_spear",
                "owner": "rookie",
                "type": "spear",
                "snags_in_neighbor_strap_at_sec": 13.65,
            },
            {
                "prop_id": "wooden_practice_spear_01",
                "owner": "instructor",
                "type": "wooden_practice_spear",
                "blunt_leather_padded_tip": True,
                "launched_at_sec": 9.96,
                "deflected_at_sec": 15.58,
            },
        ]
    }
    _atomic_write_json(proj / "story" / "props.json", props_manifest)

    continuity_ledger = {
        "stage_axis_sign": 1,
        "shots": {
            b["id"]: {
                "shotId": b["id"],
                "framingScale": b["framing_scale"],
                "trajectory": b["camera_trajectory"],
                "stageAxisSign": b["stage_axis_sign"],
                "motivateGapTransition": bool(b.get("motivate_gap_transition")),
                "motivateSnagTransition": bool(b.get("motivate_snag_transition")),
                "startState": {
                    "gapState": b["gap_state_start"],
                    "rookieHelmet": "montefortino_3_feathers",
                    "rookieShield": "red_scutum_gold_rim",
                    "snaggedSpear": b["snagged_spear_start"],
                },
                "endState": {
                    "gapState": b["gap_state_end"],
                    "rookieHelmet": "montefortino_3_feathers",
                    "rookieShield": "red_scutum_gold_rim",
                    "snaggedSpear": b["snagged_spear_end"],
                },
            }
            for b in beats
        },
    }
    _atomic_write_json(proj / "story" / "continuity_ledger.json", continuity_ledger)

    cam_beats = {
        "schema_version": "kh03.0.camera_beats.v1",
        "shots": {
            "SH01": {
                "start": 0.0, "end": 2.5, "framingScale": "extreme_detail_insert", "purpose": "hook_exposed_gap",
                "zoomKeys": [[0.0, 1.06, "c1"], [2.5, 1.22, "c1"]],
                "cxKeys": [[0.0, 0.50, "c1"], [2.5, 0.52, "c1"]],
                "cyKeys": [[0.0, 0.52, "c1"], [2.5, 0.49, "c1"]],
            },
            "SH02": {
                "start": 2.5, "end": 5.5, "framingScale": "medium_over_shoulder", "purpose": "character_reveal_grip",
                "zoomKeys": [[0.0, 1.04, "c1"], [3.0, 1.13, "c1"]],
                "cxKeys": [[0.0, 0.53, "c1"], [3.0, 0.50, "c1"]],
                "cyKeys": [[0.0, 0.50, "c1"], [3.0, 0.48, "c1"]],
            },
            "SH03": {
                "start": 5.5, "end": 9.0, "framingScale": "wide_geography", "purpose": "establish_castra_and_line",
                "zoomKeys": [[0.0, 1.01, "c1"], [3.5, 1.08, "c1"]],
                "cxKeys": [[0.0, 0.46, "c1"], [3.5, 0.53, "c1"]],
                "cyKeys": [[0.0, 0.50, "c1"], [3.5, 0.51, "c1"]],
            },
            "SH04": {
                "start": 9.0, "end": 12.0, "framingScale": "low_angle_profile", "purpose": "inciting_spear_launch",
                "zoomKeys": [[0.0, 1.05, "c1"], [0.85, 1.12, "c1"], [1.35, 1.06, "c1"], [3.0, 1.10, "c1"]],
                "cxKeys": [[0.0, 0.42, "c1"], [0.95, 0.40, "c1"], [1.6, 0.54, "c1"], [3.0, 0.58, "c1"]],
                "cyKeys": [[0.0, 0.52, "c1"], [3.0, 0.50, "c1"]],
            },
            "SH05": {
                "start": 12.0, "end": 15.0, "framingScale": "medium_full_tracking", "purpose": "foot_plant_and_shield_shove",
                "zoomKeys": [[0.0, 1.06, "c1"], [1.05, 1.14, "c1"], [1.75, 1.18, "c1"], [3.0, 1.15, "c1"]],
                "cxKeys": [[0.0, 0.58, "c1"], [1.65, 0.51, "c1"], [3.0, 0.50, "c1"]],
                "cyKeys": [[0.0, 0.54, "c1"], [3.0, 0.53, "c1"]],
                "impactImpulse": {"atLocal": 1.65, "dur": 0.22, "ampPx": 6.0},
            },
            "SH06": {
                "start": 15.0, "end": 18.5, "framingScale": "macro_physics_insert", "purpose": "wooden_tip_deflection",
                "zoomKeys": [[0.0, 1.12, "c1"], [0.58, 1.24, "outCubic"], [1.4, 1.16, "c1"], [3.5, 1.10, "c1"]],
                "cxKeys": [[0.0, 0.47, "c1"], [0.58, 0.51, "c1"], [2.4, 0.46, "c1"]],
                "cyKeys": [[0.0, 0.52, "c1"], [0.58, 0.50, "c1"], [2.4, 0.56, "c1"]],
                "impactImpulse": {"atLocal": 0.58, "dur": 0.26, "ampPx": 9.5},
            },
            "SH07": {
                "start": 18.5, "end": 23.0, "framingScale": "wide_to_medium_payoff", "purpose": "wall_holds_instructor_evaluates",
                "zoomKeys": [[0.0, 1.02, "c1"], [1.5, 1.18, "c1"], [3.2, 1.36, "c1"], [4.5, 1.38, "c1"]],
                "cxKeys": [[0.0, 0.50, "c1"], [1.6, 0.36, "c1"], [3.2, 0.29, "c1"], [4.5, 0.29, "c1"]],
                "cyKeys": [[0.0, 0.52, "c1"], [3.2, 0.48, "c1"], [4.5, 0.48, "c1"]],
            },
            "SH08": {
                "start": 23.0, "end": 26.5, "framingScale": "medium_two_shot", "purpose": "comic_spear_strap_twist",
                "zoomKeys": [[0.0, 1.18, "c1"], [1.2, 1.10, "c1"], [3.5, 1.08, "c1"]],
                "cxKeys": [[0.0, 0.54, "c1"], [1.4, 0.51, "c1"], [3.5, 0.50, "c1"]],
                "cyKeys": [[0.0, 0.51, "c1"], [3.5, 0.52, "c1"]],
            },
            "SH09": {
                "start": 26.5, "end": 30.0, "framingScale": "motif_return_close", "purpose": "deadpan_nod_and_closed_wall_loop",
                "zoomKeys": [[0.0, 1.06, "c1"], [1.8, 1.14, "c1"], [3.5, 1.22, "c1"]],
                "cxKeys": [[0.0, 0.36, "c1"], [1.7, 0.48, "c1"], [3.5, 0.52, "c1"]],
                "cyKeys": [[0.0, 0.50, "c1"], [3.5, 0.51, "c1"]],
            },
        },
    }
    _atomic_write_json(proj / "story" / "camera_beats.json", cam_beats)

    _atomic_write_text(proj / "scenes" / "shots" / "last_gap_pilot.js", _generate_pilot_scene_js())
    _atomic_write_text(proj / "scenes" / "shots" / "thumb.js", _generate_thumb_js())

    val = validate_project(proj)
    if val["status"] != "PASS":
        raise RuntimeError(f"KH-03 pilot validation failed ({val['status']}): {val}")

    return {
        "project_dir": str(proj),
        "beats_count": len(beats),
        "validator_status": val["status"],
        "style_digest": sb["canonical_digest"],
    }


def _synth_kh03_procedural_sfx(sfx_dir: Path) -> Dict[str, str]:
    """Synthesize deterministic 48kHz procedural Roman training-yard foley WAVs (100% original & licensed)."""
    sr = 48000
    rng = np.random.default_rng(2026111703)
    sfx_dir.mkdir(parents=True, exist_ok=True)
    created: Dict[str, str] = {}

    def write_sfx(filename: str, sig: np.ndarray, peak: float = 0.82) -> None:
        m = float(np.max(np.abs(sig))) + 1e-9
        y = (sig / m * peak).astype(np.float32)
        p = sfx_dir / filename
        sf.write(str(p), y, sr, subtype="PCM_16")
        created[filename] = _sha256_file(p)

    # 1. Scutum grip wood/bronze rattle
    t1 = np.linspace(0, 0.46, int(0.46 * sr), endpoint=False)
    rattle = np.zeros_like(t1)
    for off, f0, amp in [(0.02, 165, 0.7), (0.11, 210, 0.55), (0.21, 145, 0.5), (0.30, 980, 0.22)]:
        idx = int(off * sr)
        tt = t1[: len(t1) - idx]
        rattle[idx:] += amp * np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 28.0)
        rattle[idx:] += amp * 0.35 * rng.standard_normal(len(tt)) * np.exp(-tt * 42.0)
    write_sfx("kh03_scutum_grip_rattle.wav", rattle, 0.75)

    # 2. Wooden practice spear release whoosh
    t2 = np.linspace(0, 0.62, int(0.62 * sr), endpoint=False)
    env2 = np.sin(np.pi * np.clip(t2 / 0.62, 0, 1)) ** 1.8
    noise2 = rng.standard_normal(len(t2))
    # Simple moving-average band-shaping for brisk wooden shaft air cut
    k_lo = np.ones(18) / 18.0
    k_hi = np.ones(64) / 64.0
    band2 = np.convolve(noise2, k_lo, mode="same") - np.convolve(noise2, k_hi, mode="same")
    swish_tone = np.sin(2 * np.pi * np.cumsum(np.linspace(260, 520, len(t2))) / sr) * 0.28
    write_sfx("kh03_spear_whoosh_launch.wav", (band2 * 2.2 + swish_tone) * env2, 0.84)

    # 3. Gritty drill-sand foot plant
    t3 = np.linspace(0, 0.34, int(0.34 * sr), endpoint=False)
    thud3 = np.sin(2 * np.pi * np.cumsum(np.linspace(155, 58, len(t3))) / sr) * np.exp(-t3 * 22.0)
    grit3 = np.convolve(rng.standard_normal(len(t3)), np.ones(9) / 9.0, mode="same") * np.exp(-t3 * 19.0) * 0.85
    write_sfx("kh03_sand_foot_plant.wav", thud3 + grit3, 0.82)

    # 4. Solid oak-and-bronze shield wall lock
    t4 = np.linspace(0, 0.55, int(0.55 * sr), endpoint=False)
    oak4 = np.sin(2 * np.pi * np.cumsum(np.linspace(190, 74, len(t4))) / sr) * np.exp(-t4 * 16.0)
    rim4 = (
        0.45 * np.sin(2 * np.pi * 1180 * t4) * np.exp(-t4 * 24.0)
        + 0.28 * np.sin(2 * np.pi * 1760 * t4) * np.exp(-t4 * 31.0)
    )
    transient4 = rng.standard_normal(len(t4)) * np.exp(-t4 * 55.0) * 0.55
    write_sfx("kh03_shield_wall_lock.wav", oak4 + rim4 + transient4, 0.88)

    # 5. Blunt ash-wood spear tip glance & spin off scutum rim
    t5 = np.linspace(0, 0.72, int(0.72 * sr), endpoint=False)
    wood_knock = (
        0.9 * np.sin(2 * np.pi * 340 * t5) * np.exp(-t5 * 34.0)
        + 0.65 * np.sin(2 * np.pi * 585 * t5) * np.exp(-t5 * 42.0)
        + 0.4 * np.sin(2 * np.pi * 1420 * t5) * np.exp(-t5 * 48.0)
    )
    ricochet = np.sin(2 * np.pi * np.cumsum(np.linspace(460, 290, len(t5))) / sr) * np.exp(-np.maximum(0, t5 - 0.04) * 9.0) * (t5 > 0.04) * 0.32
    write_sfx("kh03_wood_spear_glance.wav", wood_knock + ricochet + rng.standard_normal(len(t5)) * np.exp(-t5 * 65.0) * 0.5, 0.90)

    # 6. Taut leather strap snag / tug
    t6 = np.linspace(0, 0.36, int(0.36 * sr), endpoint=False)
    creak = np.sin(2 * np.pi * np.cumsum(210 + 45 * np.sin(2 * np.pi * 34 * t6)) / sr) * np.exp(-t6 * 14.0) * 0.55
    wood_tap = np.sin(2 * np.pi * 410 * t6) * np.exp(-t6 * 38.0) * 0.5
    write_sfx("kh03_leather_strap_tug.wav", creak + wood_tap, 0.76)

    # 7. Subtle bronze cheek-guard / leather nod settle
    t7 = np.linspace(0, 0.30, int(0.30 * sr), endpoint=False)
    nod = (
        0.45 * np.sin(2 * np.pi * 240 * t7) * np.exp(-t7 * 26.0)
        + 0.25 * np.sin(2 * np.pi * 1640 * t7) * np.exp(-t7 * 36.0)
        + 0.25 * rng.standard_normal(len(t7)) * np.exp(-t7 * 40.0)
    )
    write_sfx("kh03_armor_nod_settle.wav", nod, 0.68)

    return created


def _trim_silence(sig: np.ndarray, sr: int, thresh: float = 0.008, pad_sec: float = 0.03) -> np.ndarray:
    idx = np.where(np.abs(sig) > thresh)[0]
    if len(idx) == 0:
        return sig
    pad = int(pad_sec * sr)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(sig), int(idx[-1]) + pad)
    return sig[i0:i1]


def build_roman_audio_timeline(
    project_dir: Path | str = PILOT_PROJECT_DIR,
    scratch_dir: Path | str | None = None,
) -> Dict[str, Any]:
    """Synthesize real spoken English narration per beat, measure exact word/line timings, and build SFX."""
    proj = Path(project_dir).resolve()
    scr = Path(scratch_dir).resolve() if scratch_dir else (REPO_ROOT / ".test-runs" / "kh03_tts_tmp")
    scr.mkdir(parents=True, exist_ok=True)

    shots_data = json.loads((proj / "story" / "shots.json").read_text(encoding="utf-8"))
    shot_map = {s["id"]: s for s in shots_data["shots"]}
    sr = 48000
    total_samples = 30 * sr
    voice_master = np.zeros(total_samples, dtype=np.float32)

    lines_out: List[Dict[str, Any]] = []
    words_out: List[Dict[str, Any]] = []

    for entry in CANONICAL_SCRIPT_LINES:
        lid = entry["line_id"]
        sid = entry["shot_id"]
        text = entry["text"]
        shot = shot_map[sid]
        seg_wav = scr / f"{lid}.wav"
        ok = synthesize_speech(text, seg_wav)
        if not ok or not seg_wav.is_file():
            raise RuntimeError(f"AUDIO_VOICE_BLOCKED: Local OS TTS failed to synthesize line {lid}")

        seg_audio, seg_sr = sf.read(str(seg_wav), dtype="float32")
        if seg_audio.ndim > 1:
            seg_audio = seg_audio.mean(axis=1)
        if seg_sr != sr:
            raise RuntimeError(f"Expected 48kHz WAV from synthesize_speech; got {seg_sr}")

        trimmed = _trim_silence(seg_audio, sr)
        rms = float(np.sqrt(np.mean(trimmed ** 2))) if len(trimmed) else 0.0
        if rms < 0.005 or len(trimmed) < int(0.35 * sr):
            raise RuntimeError(f"AUDIO_VOICE_BLOCKED: Synthesized speech for {lid} is silent or invalid (rms={rms:.5f})")

        seg_dur = len(trimmed) / sr
        shot_start = float(shot["start"])
        shot_end = float(shot["end"])
        avail_window = (shot_end - shot_start) - float(entry["min_offset_in_shot"]) - 0.08

        # If a spoken line is slightly longer than its tight shot window (e.g. 2.5s SH01),
        # allow mild natural tempo adjustment <= 1.18x via ffmpeg atempo (never extreme stretch!)
        tempo_used = 1.0
        if seg_dur > avail_window:
            needed = seg_dur / max(0.5, avail_window)
            if needed > 1.25:
                raise RuntimeError(
                    f"AUDIO_TIMING_OVERFLOW: {lid} duration {seg_dur:.2f}s exceeds {sid} window {avail_window:.2f}s by >1.25x"
                )
            tempo_used = round(min(1.22, needed * 1.03), 3)
            atempo_wav = scr / f"{lid}_atempo.wav"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-i", str(seg_wav),
                    "-af", f"atempo={tempo_used}", "-ar", str(sr), "-ac", "1", str(atempo_wav),
                ],
                check=True,
            )
            seg_audio2, _ = sf.read(str(atempo_wav), dtype="float32")
            trimmed = _trim_silence(seg_audio2 if seg_audio2.ndim == 1 else seg_audio2.mean(axis=1), sr)
            seg_dur = len(trimmed) / sr

        # Gentle 15ms fade-in/out to prevent clicks
        fade_n = min(int(0.015 * sr), len(trimmed) // 4)
        if fade_n > 1:
            trimmed[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
            trimmed[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

        t_start = round(shot_start + float(entry["min_offset_in_shot"]), 3)
        t_end = round(t_start + seg_dur, 3)
        i0 = int(t_start * sr)
        i1 = min(total_samples, i0 + len(trimmed))
        voice_master[i0:i1] += trimmed[: i1 - i0]

        lines_out.append({
            "id": lid,
            "shot_id": sid,
            "slot": "NARRATOR",
            "start": t_start,
            "end": t_end,
            "duration": round(seg_dur, 3),
            "tempo_rate": tempo_used,
            "rms": round(rms, 5),
            "text": text,
        })

        # Character-weighted word timings anchored to measured line [t_start, t_end]
        tokens = [w for w in text.split() if w.strip()]
        weights = [max(2, len(re.sub(r"[^\w]", "", w))) + (2 if re.search(r"[.,—;:!?]$", w) else 0) for w in tokens]
        w_sum = sum(weights) or 1
        w_cursor = t_start
        for tok, wt in zip(tokens, weights):
            wd = seg_dur * (wt / w_sum)
            words_out.append({
                "w": tok,
                "t": round(w_cursor, 3),
                "e": round(w_cursor + wd, 3),
                "line_id": lid,
            })
            w_cursor += wd

    voice_wav_path = proj / "timeline" / "voice.wav"
    sf.write(str(voice_wav_path), voice_master, sr, subtype="PCM_16")
    _atomic_write_json(proj / "timeline" / "lines.json", lines_out)
    _atomic_write_json(proj / "timeline" / "words.json", words_out)

    sfx_hashes = _synth_kh03_procedural_sfx(proj / "sfx")

    sound_design = {
        "schema_version": "kh03.0.sound_design.v1",
        "voice_provenance": {
            "engine": "local_os_sapi_speech_synthesizer",
            "helper": "scripts/tts_helper.py::synthesize_speech",
            "sample_rate_hz": sr,
            "channels": 1,
            "lines_count": len(lines_out),
            "words_count": len(words_out),
            "voice_wav_sha256": _sha256_file(voice_wav_path),
            "voice_rms": round(float(np.sqrt(np.mean(voice_master ** 2))), 6),
        },
        "music_provenance": {
            "bed": "roman",
            "source_file": "audio/music/bed_roman_Am_80bpm.wav",
            "generator": "packs/squire/audio.py::bed('bed_roman_Am_80bpm')",
            "license": "100% repository-procedural synthesis (numpy/soundfile)",
            "ducking_under_narration_db": -16.0,
        },
        "sfx_provenance": {
            "generator": "tools/kh03_preview_director.py::_synth_kh03_procedural_sfx",
            "license": "100% repository-procedural synthesis (seed=2026111703)",
            "files_sha256": sfx_hashes,
        },
        "target_loudness_lufs_range": [-16.0, -14.0],
        "max_true_peak_dbtp": -1.0,
    }
    _atomic_write_json(proj / "story" / "sound_design.json", sound_design)

    return sound_design


def _label_tile(im: Image.Image, header: str, footer: str = "") -> Image.Image:
    out = im.copy()
    d = ImageDraw.Draw(out)
    w, h = out.size
    bh = max(28, int(h * 0.11))
    d.rectangle([0, 0, w, bh], fill=(28, 20, 16))
    try:
        f1 = ImageFont.truetype("arialbd.ttf", max(13, int(bh * 0.48)))
        f2 = ImageFont.truetype("arial.ttf", max(11, int(bh * 0.38)))
    except OSError:
        f1 = ImageFont.load_default()
        f2 = f1
    d.text((10, 4), header, fill=(255, 243, 214), font=f1)
    if footer:
        d.rectangle([0, h - bh, w, h], fill=(28, 20, 16))
        d.text((10, h - bh + 5), footer, fill=(230, 205, 162), font=f2)
    return out


def _extract_frame_png(mp4_path: Path, t_sec: float, out_png: Path) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{t_sec:.3f}",
            "-i", str(mp4_path), "-frames:v", "1", str(out_png),
        ],
        check=True,
    )


def render_roman_preview_30s(
    project_dir: Path | str = PILOT_PROJECT_DIR,
    review_packet_dir: Path | str | None = None,
    tracked_evidence_dir: Path | str | None = None,
    workers: int = 2,
) -> Dict[str, Any]:
    """Render full 1080p24 silent video via render.mjs, mix audio via tools/mix.py, and build review packet."""
    proj = Path(project_dir).resolve()
    pkt_dir = (
        Path(review_packet_dir).resolve()
        if review_packet_dir
        else (REPO_ROOT / "docs" / "antigravity_runs" / "KH-03_0_ROMAN_MASTER_20261117_044405Z_4e4f" / "film_preview_packet")
    )
    pkt_dir.mkdir(parents=True, exist_ok=True)
    stills_dir = pkt_dir / "stills_9shots"
    stills_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    # 0. Fast 720-frame preflight error sweep
    subprocess.run(
        ["node", "render.mjs", "--project", str(proj), "--check", "--scale", "0.25"],
        cwd=str(REPO_ROOT),
        check=True,
    )
    # 1. Full 1920x1080 24fps render via existing render.mjs
    subprocess.run(
        ["node", "render.mjs", "--project", str(proj), "--workers", str(max(1, min(3, workers)))],
        cwd=str(REPO_ROOT),
        check=True,
    )
    render_wall_sec = round(time.monotonic() - t0, 3)

    # 2. Thumbnail via render.mjs --thumb
    subprocess.run(
        ["node", "render.mjs", "--project", str(proj), "--thumb"],
        cwd=str(REPO_ROOT),
        check=True,
    )

    # 3. Audio mix & H.264+AAC remux via existing tools/mix.py
    t_mix0 = time.monotonic()
    subprocess.run(
        [sys.executable, "tools/mix.py", "--project", str(proj)],
        cwd=str(REPO_ROOT),
        check=True,
    )
    mix_wall_sec = round(time.monotonic() - t_mix0, 3)

    final_mp4 = proj / "out" / f"{OUTPUT_TITLE}.mp4"
    if not final_mp4.is_file():
        raise FileNotFoundError(f"Expected rendered MP4 missing at {final_mp4}")

    # 4. Probe streams, exact decoded frame count, and EBU R128 loudness + True Peak
    probe_raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(final_mp4),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    probe_json = json.loads(probe_raw)

    cnt_raw = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=nb_read_frames",
            "-of", "csv=p=0", str(final_mp4),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip().rstrip(",")
    decoded_frames = int(cnt_raw)

    ebur_stderr = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(final_mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    lufs_matches = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur_stderr)
    tp_matches = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur_stderr) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur_stderr)
    integrated_lufs = float(lufs_matches[-1]) if lufs_matches else -99.0
    true_peak_dbtp = float(tp_matches[-1]) if tp_matches else 0.0

    # If AAC post-encode true peak slightly exceeds -1.0 dBTP or LUFS drifts outside [-16.2, -13.8], calibrate cleanly
    if not (-16.2 <= integrated_lufs <= -13.8 and true_peak_dbtp <= -1.0):
        mix_wav = proj / "build" / "mix.wav"
        video_silent = proj / "build" / "video_silent.mp4"
        cal_wav = proj / "build" / "mix_calibrated.wav"
        target_adj = (-15.0 - integrated_lufs) if (-30 < integrated_lufs < 0) else 0.0
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(mix_wav),
                "-af", f"volume={target_adj:.2f}dB,alimiter=limit=0.82:level=false",
                "-ar", "48000", "-ac", "2", str(cal_wav),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-i", str(video_silent), "-i", str(cal_wav),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(final_mp4),
            ],
            check=True,
        )
        cal_wav.unlink(missing_ok=True)
        ebur_stderr = subprocess.run(
            ["ffmpeg", "-v", "info", "-i", str(final_mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stderr
        lufs_matches = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur_stderr)
        tp_matches = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur_stderr) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur_stderr)
        integrated_lufs = float(lufs_matches[-1])
        true_peak_dbtp = float(tp_matches[-1])

    # 5. Build 9-shot contact sheet, 9 per-shot stills, 3 multi-frame action strips, thumbnail_1280.jpg & 9:16 framing proof
    shot_samples = [
        ("SH01", 1.15, "SH01 (1.15s) Hook: Gap & Spear"),
        ("SH02", 3.95, "SH02 (3.95s) Reveal: Rookie Grip"),
        ("SH03", 7.35, "SH03 (7.35s) Wide: Castra & Wall"),
        ("SH04", 9.96, "SH04 (9.96s) Beat: Spear Launch"),
        ("SH05", 13.68, "SH05 (13.68s) Action: Foot & Shove"),
        ("SH06", 15.62, "SH06 (15.62s) Insert: Rim Glance"),
        ("SH07", 21.35, "SH07 (21.35s) Payoff: Wall & Nod"),
        ("SH08", 24.85, "SH08 (24.85s) Twist: Snagged Strap"),
        ("SH09", 28.90, "SH09 (28.90s) Outro: Sealed Seam"),
    ]
    contact = Image.new("RGB", (1920, 1080), (20, 16, 14))
    cw, ch = 640, 360
    still_records = []
    for idx, (sid, ts, label) in enumerate(shot_samples):
        spng = stills_dir / f"{sid}_t{ts:05.2f}s.png"
        sjpg = stills_dir / f"{sid}_t{ts:05.2f}s.jpg"
        _extract_frame_png(final_mp4, ts, spng)
        im = Image.open(spng).convert("RGB")
        im.save(sjpg, quality=90)
        spng.unlink(missing_ok=True)
        tile = _label_tile(im.resize((cw, ch), Image.Resampling.LANCZOS), label)
        contact.paste(tile, ((idx % 3) * cw, (idx // 3) * ch))
        still_records.append({"shot_id": sid, "t_sec": ts, "jpg": str(sjpg), "sha256": _sha256_file(sjpg)})

    contact_path = pkt_dir / "contact_sheet_9shots.jpg"
    contact.save(contact_path, quality=91)

    # 3 Multi-frame 24fps action strips (5 frames each)
    strips_spec = [
        (
            "action_strip_1_sh05_footplant_and_shield_shove.jpg",
            [(12.30, "12.30s Anticipate"), (12.80, "12.80s Step"), (13.05, "13.05s Foot Plant"), (13.40, "13.40s Shove"), (13.70, "13.70s Wall Locked")],
        ),
        (
            "action_strip_2_sh06_wooden_spear_deflection.jpg",
            [(15.38, "15.38s Approach"), (15.54, "15.54s Pre-Hit"), (15.60, "15.60s Rim Squash"), (15.85, "15.85s Glance Bounce"), (16.45, "16.45s Spin Away")],
        ),
        (
            "action_strip_3_sh07_sh08_camera_push_and_strap_twist.jpg",
            [(18.90, "18.90s Wide Hold"), (21.30, "21.30s Push + Nod"), (23.35, "23.35s Exhale"), (24.15, "24.15s Strap Tug"), (25.20, "25.20s Awkward Look")],
        ),
    ]
    strip_records = []
    tmp_strip_png = proj / "build" / "_strip_frame.png"
    for sname, frames in strips_spec:
        strip_im = Image.new("RGB", (1920, 240), (20, 16, 14))
        fw, fh = 384, 240
        for j, (fts, flbl) in enumerate(frames):
            _extract_frame_png(final_mp4, fts, tmp_strip_png)
            fim = Image.open(tmp_strip_png).convert("RGB").resize((fw, fh), Image.Resampling.LANCZOS)
            fim = _label_tile(fim, flbl)
            strip_im.paste(fim, (j * fw, 0))
        tmp_strip_png.unlink(missing_ok=True)
        spath = pkt_dir / sname
        strip_im.save(spath, quality=91)
        strip_records.append({"name": sname, "path": str(spath), "sha256": _sha256_file(spath)})

    # Thumbnail 1280x720
    thumb_png = proj / "out" / "thumbnail.png"
    thumb_1280 = pkt_dir / "thumbnail_1280.jpg"
    if thumb_png.is_file():
        Image.open(thumb_png).convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS).save(thumb_1280, quality=91)

    # Lightweight 9:16 center-safe framing proof contact sheet (4 key shots)
    vert_sheet = Image.new("RGB", (1080, 960), (20, 16, 14))
    for k_idx, (sid, ts, lbl) in enumerate([shot_samples[0], shot_samples[1], shot_samples[4], shot_samples[7]]):
        sjpg = stills_dir / f"{sid}_t{ts:05.2f}s.jpg"
        src = Image.open(sjpg).convert("RGB")
        # 9:16 crop from 1920x1080 -> 608x1080 centered
        crop = src.crop((656, 0, 1264, 1080)).resize((270, 480), Image.Resampling.LANCZOS)
        crop = _label_tile(crop, f"9:16 {sid}")
        vert_sheet.paste(crop, (k_idx * 270, 240))
    vert_proof_path = pkt_dir / "contact_sheet_9x16_framing_proof.jpg"
    vert_sheet.save(vert_proof_path, quality=89)

    # Audit zero reused demo/reference assets
    non_reuse = assert_no_reused_demo_assets(proj)
    if not non_reuse["passed"]:
        raise RuntimeError(f"Non-reuse audit failed on pilot project: {non_reuse['errors']}")

    v_stream = next((s for s in probe_json.get("streams", []) if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in probe_json.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt_dur = float(probe_json.get("format", {}).get("duration", 0.0))

    manifest = {
        "project": proj.name,
        "output_mp4_local_path": str(final_mp4),
        "output_mp4_sha256": _sha256_file(final_mp4),
        "output_mp4_bytes": final_mp4.stat().st_size,
        "render_wall_sec": render_wall_sec,
        "mix_wall_sec": mix_wall_sec,
        "video_stream": {
            "codec_name": v_stream.get("codec_name"),
            "width": int(v_stream.get("width", 0)),
            "height": int(v_stream.get("height", 0)),
            "r_frame_rate": v_stream.get("r_frame_rate"),
            "decoded_frames": decoded_frames,
            "format_duration_sec": round(fmt_dur, 3),
        },
        "audio_stream": {
            "codec_name": a_stream.get("codec_name"),
            "sample_rate": int(a_stream.get("sample_rate", 0)),
            "channels": int(a_stream.get("channels", 0)),
            "integrated_lufs": round(integrated_lufs, 2),
            "true_peak_dbtp": round(true_peak_dbtp, 2),
        },
        "non_reuse_audit": non_reuse,
        "review_packet": {
            "contact_sheet_9shots": str(contact_path),
            "thumbnail_1280": str(thumb_1280),
            "contact_sheet_9x16_framing_proof": str(vert_proof_path),
            "action_strips": strip_records,
            "stills": still_records,
        },
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "style_approved": "HUMAN_REVIEW_PENDING",
    }
    _atomic_write_json(pkt_dir / "pilot_render_manifest.json", manifest)

    if tracked_evidence_dir:
        tev = Path(tracked_evidence_dir).resolve()
        tev.mkdir(parents=True, exist_ok=True)
        for p in [contact_path, thumb_1280, vert_proof_path, pkt_dir / "pilot_render_manifest.json"]:
            if p.is_file():
                shutil.copy2(p, tev / p.name)
        for sr_item in strip_records:
            shutil.copy2(sr_item["path"], tev / sr_item["name"])

    return manifest


# Opt-in KH-03.0.R1 script-driven builder & renderer (zero change to KH-03.0 legacy functions above)
from tools.kh03_r1_project_builder import build_roman_script_driven_project, render_roman_r1_preview


if __name__ == "__main__":
    scr_tts = REPO_ROOT / ".test-runs" / "kh03_0_20261117_044405Z_4e4f" / "tts_segments"
    pkt = REPO_ROOT / "docs" / "antigravity_runs" / "KH-03_0_ROMAN_MASTER_20261117_044405Z_4e4f" / "film_preview_packet"
    tev = REPO_ROOT / "tests" / "evidence" / "kh03_0_20261117_044405Z_4e4f" / "film_preview_packet"
    info_build = build_roman_preview_project(PILOT_PROJECT_DIR)
    info_audio = build_roman_audio_timeline(PILOT_PROJECT_DIR, scratch_dir=scr_tts)
    info_render = render_roman_preview_30s(PILOT_PROJECT_DIR, review_packet_dir=pkt, tracked_evidence_dir=tev, workers=2)
    print(json.dumps({
        "build": info_build,
        "voice": info_audio["voice_provenance"],
        "video": info_render["video_stream"],
        "audio": info_render["audio_stream"],
        "mp4_sha256": info_render["output_mp4_sha256"],
        "mp4_bytes": info_render["output_mp4_bytes"],
    }, indent=2))
