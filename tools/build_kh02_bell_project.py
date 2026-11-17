#!/usr/bin/env python3
"""build_kh02_bell_project.py — Builds 'THE BELL THAT RANG TOO EARLY' (projects/kh02_bell_before_sunrise_30s).

Generates:
1. Real spoken English narration via native OS TTS (Windows SAPI / macOS say), measured per shot at 1.0x speed.
2. 100% code-synthesized procedural foley SFX & Roman pre-dawn comedy-suspense score (zero copyright risk).
3. All 8 mandatory KH-02.1 source-of-truth story manifests:
   style_profile.json, character_bible.json, environment_bible.json, props.json,
   continuity_ledger.json, storyboard.json, camera_beats.json, asset_manifest.json, plus shots.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from scipy import signal

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from common import SR, load_audio, save_wav, trim
from tts_helper import synthesize_speech
from kh02_style_contract import load_squire_style_profile, resolve_squire_niche_style, validate_squire_style_contract
from kh02_character_factory import derive_character_identity
from kh02_environment_factory import derive_scene_spec

PROJ_DIR_DEFAULT = REPO_ROOT / "projects" / "kh02_bell_before_sunrise_30s"

# Eight mandatory shot intervals covering exact [0.0, 30.0] seconds (720 frames @ 24fps)
SHOT_PLAN = [
    {
        "id": "S01",
        "start": 0.0,
        "end": 3.0,
        "voice_offset": 0.16,
        "line": "Before dawn, Pip found the bell rope.",
        "view": "belfry_lower_arch",
        "frame_scale": "CU",
        "lens_equivalent_2d": "65mm_shallow_dof_2d",
        "purpose": "Immediate visual hook in first 0.5s: goat nudging coiled hemp rope while giant bell blurs behind in 2D",
        "action": "PIP lunges snout into coiled hemp rope at t=0.05..0.48s, sending a crisp 2D wave up the rope",
        "motion_phases": ["nudge_hook_0.0_0.9s", "curious_pause_0.9_1.35s", "second_tug_1.35_2.6s"],
        "camera_curve": {"z0": 1.03, "z1": 1.11, "x0": -18, "x1": 16, "y0": 10, "y1": 2, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "prop_rope_x_side": "right_of_bell_axis",
            "cast_present": ["PIP"],
        },
        "sfx": [
            {"name": "build/audio_gen/goat_hoof_tap.wav", "at": 0.08, "gain": -7},
            {"name": "build/audio_gen/rope_hemp_swish.wav", "at": 0.22, "gain": -8},
            {"name": "build/audio_gen/goat_hoof_tap.wav", "at": 1.48, "gain": -8},
        ],
    },
    {
        "id": "S02",
        "start": 3.0,
        "end": 6.5,
        "voice_offset": 0.22,
        "line": "Tavi had one rule: wait for sunrise.",
        "view": "belfry_wide_interior",
        "frame_scale": "MS_TWO_SHOT",
        "lens_equivalent_2d": "35mm_two_shot_2d",
        "purpose": "Establish apprentice keeper TAVI, his rule, and clear spatial relation to PIP and swaying bell rope",
        "action": "TAVI stands watchful, hears rope creak, pupils snap up-right in wide shock, leans ready to lunge",
        "motion_phases": ["calm_watchful_0.0_0.5s", "pupil_snap_shock_0.5_1.55s", "anxious_lean_ready_1.55_3.5s"],
        "camera_curve": {"z0": 1.01, "z1": 1.09, "x0": -28, "x1": 24, "y0": 0, "y1": -8, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "prop_rope_x_side": "right_of_bell_axis",
            "cast_present": ["TAVI", "PIP"],
        },
        "sfx": [
            {"name": "build/audio_gen/bell_creak_swing.wav", "at": 0.42, "gain": -9},
            {"name": "build/audio_gen/stone_stair_steps.wav", "at": 1.85, "gain": -11},
        ],
    },
    {
        "id": "S03",
        "start": 6.5,
        "end": 10.0,
        "voice_offset": 0.20,
        "line": "He lunged, but the rope slipped free.",
        "view": "belfry_low_angle",
        "frame_scale": "MCU_LOW_ANGLE_2D",
        "lens_equivalent_2d": "28mm_authored_upward_2d",
        "purpose": "Escalating physical stakes: TAVI grabs rope, strains downward, hemp slips through fingers and whips upward",
        "action": "Anticipate & reach -> taut two-handed pull -> friction slip & open-hand recoil as bell begins swinging",
        "motion_phases": ["anticipate_reach_0.0_1.05s", "pull_strain_1.05_2.05s", "slip_recoil_2.05_3.5s"],
        "camera_curve": {"z0": 1.06, "z1": 1.16, "x0": -16, "x1": 18, "y0": 22, "y1": -26, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "hand_to_rope_contact_window_local": [0.95, 2.05],
            "cast_present": ["TAVI"],
        },
        "sfx": [
            {"name": "build/audio_gen/rope_hemp_swish.wav", "at": 0.85, "gain": -6},
            {"name": "build/audio_gen/rope_hemp_swish.wav", "at": 2.05, "gain": -5},
            {"name": "build/audio_gen/bell_creak_swing.wav", "at": 2.25, "gain": -7},
        ],
    },
    {
        "id": "S04",
        "start": 10.0,
        "end": 13.5,
        "voice_offset": 0.24,
        "line": "One tug set the whole bell tower shaking.",
        "view": "belfry_wide_interior",
        "frame_scale": "WS_INTERIOR",
        "lens_equivalent_2d": "24mm_layered_wide_2d",
        "purpose": "Show heavy bronze bell swinging in rhythmic arcs across 5 parallax planes while TAVI bolts for the stairs",
        "action": "Giant bronze bell rotates on oak yoke; clapper nears bronze lip; TAVI sprints right toward stairwell",
        "motion_phases": ["shock_look_up_0.0_0.65s", "stairwell_dash_0.65_3.5s"],
        "camera_curve": {"z0": 1.00, "z1": 1.14, "x0": -12, "x1": 22, "y0": 8, "y1": -18, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "exit_direction": "screen_right_to_stairs",
            "cast_present": ["TAVI", "PIP"],
        },
        "sfx": [
            {"name": "build/audio_gen/bell_creak_swing.wav", "at": 0.15, "gain": -6},
            {"name": "build/audio_gen/stone_stair_steps.wav", "at": 0.85, "gain": -8},
            {"name": "build/audio_gen/bell_creak_swing.wav", "at": 1.95, "gain": -6},
        ],
    },
    {
        "id": "S05",
        "start": 13.5,
        "end": 17.5,
        "voice_offset": 0.25,
        "line": "He sprinted up the stairs to catch the clapper.",
        "view": "tower_stairwell_ascent",
        "frame_scale": "MS_SIDE_TRACKING",
        "lens_equivalent_2d": "40mm_tracking_elevation_2d",
        "purpose": "Dynamic vertical climb with planted sandals on stone treads, scarf/hair lag, and diagonal tracking camera",
        "action": "TAVI climbs 6 consecutive travertine steps (step 1 -> step 7) with world-locked stance foot and progressive effort",
        "motion_phases": ["steps_1_2_anxious", "steps_3_4_determined", "steps_5_6_strained_summit"],
        "camera_curve": {"z0": 1.08, "z1": 1.15, "x0": -155, "x1": 145, "y0": 80, "y1": -72, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "planted_foot_skate_px": 0.0,
            "visible_landmark": "lm_5arch_aqueduct",
            "cast_present": ["TAVI"],
        },
        "sfx": [
            {"name": "build/audio_gen/stone_stair_steps.wav", "at": 0.12, "gain": -6},
            {"name": "build/audio_gen/stone_stair_steps.wav", "at": 2.02, "gain": -6},
            {"name": "build/audio_gen/bell_creak_swing.wav", "at": 1.40, "gain": -8},
        ],
    },
    {
        "id": "S06",
        "start": 17.5,
        "end": 23.0,
        "voice_offset": 0.35,
        "line": "For one breathless second, total silence.",
        "view": "belfry_catwalk_clapper",
        "frame_scale": "MS_TO_ECU_INTERNAL_CUT",
        "lens_equivalent_2d": "35mm_catwalk_cut_to_85mm_clapper_closeup_2d",
        "purpose": "Physically plausible catwalk clapper catch across motivated internal cut at 19.3s, dropping sound to silence",
        "action": "S06a [17.5-19.3s]: TAVI reaches from oak catwalk to catch clapper shaft; S06b [19.3-23.0s]: close grip & relief",
        "motion_phases": ["catwalk_lunge_catch_0.0_1.8s", "closeup_strained_hold_1.8_2.75s", "breathless_relief_hold_2.75_5.5s"],
        "camera_curve": {"z0": 1.02, "z1": 1.10, "x0": -24, "x1": 8, "y0": 6, "y1": -10, "ease": "out"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "internal_cut_local_sec": 1.80,
            "hand_to_clapper_contact_from_global_sec": 18.65,
            "cast_present": ["TAVI"],
        },
        "notes": "DROP",
        "sfx": [
            {"name": "build/audio_gen/clapper_leather_catch.wav", "at": 1.12, "gain": -5},
        ],
    },
    {
        "id": "S07",
        "start": 23.0,
        "end": 26.5,
        "voice_offset": 0.14,
        "line": "Then little Pip sneezed.",
        "view": "belfry_lower_arch",
        "frame_scale": "CU_SURPRISE",
        "lens_equivalent_2d": "65mm_goat_closeup_2d",
        "purpose": "Micro-surprise reversal: golden dust mote tickles PIP -> 2D inhale squash -> explosive sneeze yanks rope!",
        "action": "PIP inhales with puffed cheeks & squashed body (0.45..1.85s), then sneezes forward at 24.85s yanking rope & ringing bell",
        "motion_phases": ["dust_tickle_0.0_0.45s", "inhale_squash_0.45_1.85s", "sneeze_stretch_bell_strike_1.85_3.5s"],
        "camera_curve": {"z0": 1.04, "z1": 1.15, "x0": -10, "x1": 16, "y0": 8, "y1": -6, "ease": "inOut"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "sneeze_burst_global_sec": 24.85,
            "cast_present": ["PIP"],
        },
        "sfx": [
            {"name": "build/audio_gen/goat_sneeze_choo.wav", "at": 1.55, "gain": -4},
            {"name": "build/audio_gen/rope_hemp_swish.wav", "at": 1.90, "gain": -6},
            {"name": "build/audio_gen/roman_bell_early_toll.wav", "at": 2.08, "gain": -4},
        ],
    },
    {
        "id": "S08",
        "start": 26.5,
        "end": 30.0,
        "voice_offset": 0.28,
        "line": "And Rome woke up an hour early.",
        "view": "hilltop_courtyard_wide",
        "frame_scale": "WS_PAYOFF_TO_CU_DEADPAN",
        "lens_equivalent_2d": "28mm_courtyard_cut_to_85mm_deadpan_2d",
        "purpose": "Comic payoff: courtyard shutters fly open as LYRA & MARCUS wake to ringing bell, fast cut to TAVI's deadpan face",
        "action": "S08a [26.5-28.35s]: wide courtyard waking reaction; S08b [28.35-30.0s]: fast cut to TAVI deadpan disbelief",
        "motion_phases": ["courtyard_shutters_open_0.0_1.85s", "tavi_deadpan_blink_1.85_3.5s"],
        "camera_curve": {"z0": 1.00, "z1": 1.05, "x0": 0, "x1": 12, "y0": 0, "y1": -6, "ease": "out"},
        "continuity_anchors": {
            "location": "loc_janiculum_bell_tower",
            "internal_cut_local_sec": 1.85,
            "cast_present": ["LYRA", "MARCUS", "TAVI"],
        },
        "sfx": [
            {"name": "build/audio_gen/roman_bell_early_toll.wav", "at": 0.05, "gain": -5},
            {"name": "build/audio_gen/courtyard_waking_murmur.wav", "at": 0.22, "gain": -6},
        ],
    },
]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _bp(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def _lp(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, "lowpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def _hp(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, "highpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def _norm(x: np.ndarray, peak: float = 0.82) -> np.ndarray:
    m = float(np.max(np.abs(x))) + 1e-9
    return (x / m * peak).astype(np.float32)


def generate_procedural_audio_assets(audio_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Synthesize 100% original procedural foley SFX & 30s Roman pre-dawn score with deterministic RNG."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261117)
    manifest: Dict[str, Dict[str, Any]] = {}

    def write_cue(filename: str, y: np.ndarray, formula_desc: str):
        out = audio_dir / filename
        fade = min(int(0.02 * SR), len(y) // 6)
        y2 = _norm(y.copy(), 0.82)
        if fade > 0:
            y2[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
        save_wav(str(out), y2, SR)
        manifest[f"build/audio_gen/{filename}"] = {
            "origin": "PROCEDURAL_CODE_GENERATED_KH02",
            "license": "100% original procedural synthesis in tools/build_kh02_bell_project.py",
            "formula": formula_desc,
            "duration_sec": round(len(y2) / SR, 4),
            "sha256": _sha256_file(out),
            "bytes": out.stat().st_size,
        }

    # 1. goat_hoof_tap.wav — crisp double cloven stone tap
    d = 0.42
    buf = np.zeros(int(d * SR), dtype=np.float32)
    for off, amp in [(0.0, 1.0), (0.13, 0.78)]:
        tt = np.arange(int(0.08 * SR)) / SR
        tap = (_bp(rng.standard_normal(len(tt)), 600, 3200) * np.exp(-tt * 65) + np.sin(2 * np.pi * 240 * tt) * np.exp(-tt * 50) * 0.7) * amp
        i0 = int(off * SR)
        buf[i0:i0 + len(tap)] += tap.astype(np.float32)
    write_cue("goat_hoof_tap.wav", buf, "bandpass stone click + 240Hz wood/hoof resonance double tap")

    # 2. rope_hemp_swish.wav — braided hemp friction + taut creak
    tt = np.arange(int(0.68 * SR)) / SR
    swish = _bp(rng.standard_normal(len(tt)), 450, 4200) * np.sin(np.pi * tt / 0.68) ** 1.6
    creak = np.sin(2 * np.pi * np.cumsum(np.linspace(190, 310, len(tt))) / SR) * np.exp(-tt * 5.5) * 0.35
    write_cue("rope_hemp_swish.wav", swish + creak, "bandpass hemp friction envelope + 190..310Hz tension creak")

    # 3. bell_creak_swing.wav — heavy oak yoke creak + deep air whoosh (no strike!)
    tt = np.arange(int(1.45 * SR)) / SR
    whoosh = _bp(rng.standard_normal(len(tt)), 90, 680) * np.sin(np.pi * tt / 1.45) ** 2.0 * 0.9
    oak_creak = sum(np.sin(2 * np.pi * (145 * k + 18 * np.sin(2 * np.pi * 6 * tt)) * tt) * (0.5 ** k) for k in range(1, 4)) * np.exp(-tt * 2.4) * 0.35
    write_cue("bell_creak_swing.wav", whoosh + oak_creak, "low-band yoke air whoosh + FM timber creak harmonics")

    # 4. stone_stair_steps.wav — 4 quick sandal steps ascending travertine risers
    buf = np.zeros(int(1.85 * SR), dtype=np.float32)
    for k in range(4):
        tt = np.arange(int(0.14 * SR)) / SR
        step = _lp(rng.standard_normal(len(tt)), 1500) * np.exp(-tt * 38) + np.sin(2 * np.pi * (135 + k * 8) * tt) * np.exp(-tt * 32) * 0.65
        i0 = int((k * 0.42) * SR)
        buf[i0:i0 + len(step)] += step.astype(np.float32)
    write_cue("stone_stair_steps.wav", buf, "4-step travertine impact sequence with ascending pitch")

    # 5. clapper_leather_catch.wav — firm muffled leather-on-iron catch thud (no bell ring!)
    tt = np.arange(int(0.46 * SR)) / SR
    thud = np.sin(2 * np.pi * np.cumsum(np.linspace(170, 58, len(tt))) / SR) * np.exp(-tt * 22) * 0.95
    leather = _bp(rng.standard_normal(len(tt)), 300, 1900) * np.exp(-tt * 34) * 0.55
    dull_iron = np.sin(2 * np.pi * 420 * tt) * np.exp(-tt * 28) * 0.22
    write_cue("clapper_leather_catch.wav", thud + leather + dull_iron, "damped iron-clapper thud + leather grip transient")

    # 6. goat_sneeze_choo.wav — quick inhale + crisp comic sneeze burst!
    inh_t = np.arange(int(0.28 * SR)) / SR
    inhale = _bp(rng.standard_normal(len(inh_t)), 900, 3800) * (inh_t / 0.28) ** 1.8 * 0.45
    gap = np.zeros(int(0.05 * SR), dtype=np.float32)
    ch_t = np.arange(int(0.42 * SR)) / SR
    burst = _bp(rng.standard_normal(len(ch_t)), 700, 6500) * np.exp(-ch_t * 11) * 1.0
    chirp = np.sin(2 * np.pi * np.cumsum(np.linspace(680, 310, len(ch_t))) / SR) * np.exp(-ch_t * 13) * 0.65
    write_cue("goat_sneeze_choo.wav", np.concatenate([inhale, gap, burst + chirp]), "inhale noise swell + 680->310Hz comic sneeze burst")

    # 7. roman_bell_early_toll.wav — rich cast-bronze civic bell strike (G3 + D4 + F4 + G4 + B4 + D5 partials)
    tt = np.arange(int(3.2 * SR)) / SR
    partials = [(196.0, 0.85, 1.0), (293.66, 1.15, 0.52), (349.23, 1.35, 0.36), (392.0, 1.05, 0.65), (493.88, 1.7, 0.28), (587.33, 2.1, 0.24), (980.0, 3.4, 0.16)]
    bell = sum(amp * np.sin(2 * np.pi * freq * tt) * np.exp(-tt * dec) for freq, dec, amp in partials)
    strike = _hp(rng.standard_normal(len(tt)), 1800) * np.exp(-tt * 55) * 0.45
    write_cue("roman_bell_early_toll.wav", (bell + strike) * np.minimum(1.0, tt / 0.004), "7-partial cast bronze harmonic bell synthesis + clapper transient")

    # 8. courtyard_waking_murmur.wav — wooden shutters clattering open + startled crowd murmur
    tt = np.arange(int(2.4 * SR)) / SR
    shutter1 = _lp(rng.standard_normal(int(0.16 * SR)), 1400) * np.exp(-np.arange(int(0.16 * SR)) / SR * 26)
    shutter2 = _lp(rng.standard_normal(int(0.16 * SR)), 1600) * np.exp(-np.arange(int(0.16 * SR)) / SR * 26) * 0.85
    murmur = (
        _bp(rng.standard_normal(len(tt)), 220, 780) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * tt))
        + _bp(rng.standard_normal(len(tt)), 750, 1900) * (0.5 + 0.5 * np.sin(2 * np.pi * 4.7 * tt + 1.1)) * 0.55
    ) * np.minimum(1.0, tt / 0.35) * np.exp(-np.maximum(0.0, tt - 1.2) * 0.9) * 0.55
    murmur[:len(shutter1)] += shutter1 * 0.9
    s2_off = int(0.22 * SR)
    murmur[s2_off:s2_off + len(shutter2)] += shutter2 * 0.85
    write_cue("courtyard_waking_murmur.wav", murmur, "dual wooden shutter impacts + modulated formant crowd murmur")

    # 9. roman_dawn_bell_score.wav — 30.0s original plucked lyre/lute & soft frame-drum comedy-suspense score
    # Automatically drops to near-total hush during S06 [18.85s .. 24.80s] for the dramatic silence & sneeze!
    dur = 30.0
    score = np.zeros(int(dur * SR), dtype=np.float32)
    bpm = 104.0
    step_sec = 60.0 / bpm / 2.0  # eighth notes
    scale_notes = [220.0, 261.63, 293.66, 329.63, 392.0, 440.0, 329.63, 293.66]  # A minor / Dorian plucked motif
    t_cursor = 0.0
    idx = 0
    while t_cursor < dur - 0.3:
        # Respect dramatic silence window [18.85s .. 24.80s]
        if 18.85 <= t_cursor <= 24.80:
            t_cursor += step_sec
            idx += 1
            continue
        freq = scale_notes[idx % len(scale_notes)] * (1.25 if t_cursor >= 26.5 and idx % 4 == 0 else 1.0)
        nt = np.arange(int(0.42 * SR)) / SR
        pluck = (np.sin(2 * np.pi * freq * nt) + 0.45 * np.sin(4 * np.pi * freq * nt) + 0.2 * np.sin(6 * np.pi * freq * nt)) * np.exp(-nt * 7.5) * np.minimum(1.0, nt / 0.005)
        i0 = int(t_cursor * SR)
        L = min(len(pluck), len(score) - i0)
        score[i0:i0 + L] += (pluck[:L] * 0.38).astype(np.float32)
        if idx % 4 == 0 and t_cursor < 18.6:
            dt = np.arange(int(0.18 * SR)) / SR
            fdrum = np.sin(2 * np.pi * 92 * dt) * np.exp(-dt * 18) * 0.34
            Ld = min(len(fdrum), len(score) - i0)
            score[i0:i0 + Ld] += fdrum[:Ld].astype(np.float32)
        t_cursor += step_sec
        idx += 1

    # Gentle warm pre-dawn drone pad under active sections
    full_t = np.arange(len(score)) / SR
    pad = (np.sin(2 * np.pi * 110.0 * full_t) + 0.5 * np.sin(2 * np.pi * 164.81 * full_t)) * 0.11
    silence_mask = np.ones_like(full_t)
    silence_mask[(full_t >= 18.7) & (full_t <= 24.85)] = 0.0
    # Smooth transitions into/out of S06 silence
    win = int(0.22 * SR)
    kernel = np.ones(win) / win
    silence_mask = np.convolve(silence_mask, kernel, mode="same")
    score = (score + pad * silence_mask).astype(np.float32)
    write_cue("roman_dawn_bell_score.wav", score, "104bpm plucked Dorian lyre ostinato + soft 92Hz frame drum + S06 silence drop")

    return manifest


def _words_for_line(text: str, t0: float, t1: float) -> List[Dict[str, Any]]:
    tokens = text.split()
    weights = [max(1, len(re.sub(r"[\W_]", "", w))) + 1 for w in tokens]
    total_w = sum(weights) or 1
    acc = 0
    out = []
    for tok, w in zip(tokens, weights):
        ws = t0 + (t1 - t0) * (acc / total_w)
        acc += w
        we = t0 + (t1 - t0) * (acc / total_w)
        clean = re.sub(r"^[\"'(\u201c]+|[\"'),.!?:;\u201d\u2026]+$", "", tok)
        out.append({"w": clean, "t": round(ws, 3), "e": round(max(ws + 0.04, we - 0.02), 3)})
    return out


def generate_measured_narration(proj_dir: Path) -> Dict[str, Any]:
    """Synthesize each of the 8 shot lines via lawful local OS TTS at 1.0x speed, measure exact WAV durations,
    verify zero overlap with shot boundaries, and build exact 30.000s timeline/voice.wav + JSON manifests.
    """
    tl_dir = proj_dir / "timeline"
    clip_dir = proj_dir / "build" / "voice_clips"
    tl_dir.mkdir(parents=True, exist_ok=True)
    clip_dir.mkdir(parents=True, exist_ok=True)

    master_samples = int(30.0 * SR)
    voice_master = np.zeros(master_samples, dtype=np.float32)
    lines_json = []
    words_json = []
    blocks_json = []
    clip_receipts = {}

    for idx, sh in enumerate(SHOT_PLAN, 1):
        sid = sh["id"]
        raw_wav = clip_dir / f"{sid}_tts.wav"
        ok = synthesize_speech(sh["line"], raw_wav)
        if not ok or not raw_wav.is_file() or raw_wav.stat().st_size < 1000:
            return {"status": "VOICE_BLOCKED", "error": f"OS TTS failed on shot {sid}"}

        y = trim(load_audio(str(raw_wav), sr=SR, ch=1))
        # Verify real speech energy (not silent or pure sine)
        rms = float(np.sqrt(np.mean(y ** 2)))
        if rms < 0.005 or len(y) < int(0.5 * SR):
            return {"status": "VOICE_BLOCKED", "error": f"Synthesized speech for {sid} has invalid RMS={rms:.5f}"}

        dur_sec = len(y) / SR
        st_sec = round(sh["start"] + sh["voice_offset"], 3)
        en_sec = round(st_sec + dur_sec, 3)
        shot_end = float(sh["end"])
        if en_sec > shot_end - 0.12:
            return {
                "status": "VOICE_TIMING_OVERFLOW",
                "error": f"Line {sid} duration {dur_sec:.3f}s overflows shot window [{sh['start']}, {shot_end}] (end={en_sec:.3f}s)",
            }

        i0 = int(round(st_sec * SR))
        i1 = min(master_samples, i0 + len(y))
        voice_master[i0:i1] += y[:i1 - i0]

        lid = f"L{idx:03d}"
        bid = f"V{idx:03d}"
        lines_json.append({
            "id": lid,
            "block": bid,
            "slot": "NARRATOR",
            "char": "TAVI",
            "text": sh["line"],
            "start": st_sec,
            "end": en_sec,
            "measured_wav_duration_sec": round(dur_sec, 4),
            "drop": sh.get("notes") == "DROP",
        })
        blocks_json.append({
            "id": bid,
            "slot": "NARRATOR",
            "char": "TAVI",
            "drop": sh.get("notes") == "DROP",
            "text": sh["line"],
            "start": st_sec,
            "end": en_sec,
        })
        words_json.extend(_words_for_line(sh["line"], st_sec, en_sec))
        clip_receipts[f"build/voice_clips/{sid}_tts.wav"] = {
            "origin": "LOCAL_OS_SAPI_TTS_1X_MEASURED",
            "shot_id": sid,
            "text": sh["line"],
            "start_sec": st_sec,
            "end_sec": en_sec,
            "measured_duration_sec": round(dur_sec, 4),
            "rms": round(rms, 5),
            "sha256": _sha256_file(raw_wav),
        }

    voice_wav_path = tl_dir / "voice.wav"
    save_wav(str(voice_wav_path), voice_master, SR)
    (tl_dir / "lines.json").write_text(json.dumps(lines_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (tl_dir / "words.json").write_text(json.dumps(words_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (tl_dir / "blocks.json").write_text(json.dumps(blocks_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    transcript_lines = [
        f"[{l['start']:7.3f} - {l['end']:7.3f}] {l['block']} {l['slot']:<9} {l['text']}"
        for l in lines_json
    ]
    (tl_dir / "transcript.txt").write_text("\n".join(transcript_lines) + "\n", encoding="utf-8")

    return {
        "status": "VOICE_READY",
        "voice_wav_sha256": _sha256_file(voice_wav_path),
        "voice_duration_sec": round(len(voice_master) / SR, 3),
        "lines": lines_json,
        "clips": clip_receipts,
    }


def build_bell_project(proj_dir: Path = PROJ_DIR_DEFAULT) -> Dict[str, Any]:
    proj_dir = Path(proj_dir).resolve()
    story_dir = proj_dir / "story"
    for sub in ("story", "timeline", "scenes/shots", "build", "out"):
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    # 1. Resolve style contract & factories
    style_bible = load_squire_style_profile("squire_cinematic_2d.v1")
    resolved_style = resolve_squire_niche_style(
        {
            "niche": "roman",
            "title": "The Bell That Rang Too Early",
            "setting": "Fictional Roman hilltop bell tower, stairwell, and courtyard right before dawn",
        },
        "squire_cinematic_2d.v1",
    )
    char_bible = derive_character_identity()
    env_bible = derive_scene_spec(SHOT_PLAN)

    # 2. Generate procedural SFX + score & real measured TTS narration
    audio_assets = generate_procedural_audio_assets(proj_dir / "build" / "audio_gen")
    voice_res = generate_measured_narration(proj_dir)
    if voice_res["status"] != "VOICE_READY":
        raise RuntimeError(f"Narration generation blocked: {voice_res}")

    # 3. Write config.json (opt-in canvas2d_only + squire_cinematic_2d.v1)
    config = {
        "title": "The Bell That Rang Too Early",
        "pack": "squire",
        "aspect": "16:9",
        "resolution": "1080p",
        "fps": 24,
        "style": "flat",
        "style_profile": "squire_cinematic_2d.v1",
        "render_mode": "canvas2d_only",
        "kh02_2d_only": True,
        "experimental_preview": True,
        "kh02_stage": "KH-02.0+KH-02.1_EXPERIMENTAL_PREVIEW",
        "captions": False,
        "bars": "none",
        "fadeIn": 0.0,
        "fadeOut": 0.35,
        "lang": "en",
        "music": {
            "enabled": True,
            "file": "build/audio_gen/roman_dawn_bell_score.wav",
            "gainDb": -14,
        },
        "sfx": {
            "enabled": True,
            "gainDb": -3,
        },
        "loudness": -14,
        "duration": 30.0,
    }
    (proj_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 4. Write all 8 mandatory B6 story manifests + shots.json
    (story_dir / "style_profile.json").write_text(json.dumps(resolved_style, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (story_dir / "character_bible.json").write_text(json.dumps(char_bible, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (story_dir / "environment_bible.json").write_text(json.dumps(env_bible, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    props_spec = {
        "schema_version": "kh02_props.v1",
        "central_prop_id": "prop_giant_bronze_bell",
        "props": [
            {
                "prop_id": "prop_giant_bronze_bell",
                "name": "Giant Roman Civic Watch-Bell",
                "materials": ["aged_cast_bronze", "mortised_oak_yoke", "iron_clapper_bulb", "coiled_hemp_rope"],
                "mechanical_solver": "packs/squire/cinematic2d/environment.js::evaluateBellRigStateAt",
                "continuous_across_shots": ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"],
                "physical_plausibility_note": "Mounted above an upper oak maintenance catwalk so apprentice bell-keeper TAVI can physically reach and brace the internal iron clapper shaft with leather-wrapped hands in S06 without teleporting or floating.",
            },
            {
                "prop_id": "prop_courtyard_amphorae",
                "name": "Terracotta Courtyard Storage Amphorae",
                "materials": ["fired_terracotta_clay"],
                "continuous_across_shots": ["S08"],
            },
        ],
    }
    (story_dir / "props.json").write_text(json.dumps(props_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    camera_beats = {
        "schema_version": "kh02_camera_beats.v1",
        "render_mode": "canvas2d_only",
        "bounds": {"min_zoom": 0.94, "max_zoom": 1.35, "max_pan_px": 380},
        "shots": {sh["id"]: sh["camera_curve"] for sh in SHOT_PLAN},
    }
    (story_dir / "camera_beats.json").write_text(json.dumps(camera_beats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    storyboard_spec = {
        "schema_version": "kh02_storyboard_grammar.v1",
        "working_title": "THE BELL THAT RANG TOO EARLY",
        "fictional_disclaimer": "Original fictional Roman-comedy short authored for KH-02.1 2D style & motion review; not claimed as historical fact.",
        "experimental_status": "EXPERIMENTAL_PREVIEW_HUMAN_REVIEW_PENDING",
        "duration_sec": 30.0,
        "fps": 24,
        "total_frames": 720,
        "shots": SHOT_PLAN,
    }
    (story_dir / "storyboard.json").write_text(json.dumps(storyboard_spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    continuity_ledger = {
        "schema_version": "kh02_continuity_ledger.v1",
        "canonical_cast_locked": ["TAVI", "PIP", "LYRA", "MARCUS"],
        "wardrobe_locks": {
            c["canonical_name"]: c["wardrobe"] for c in char_bible["characters"]
        },
        "world_landmarks_locked": [lm["landmark_id"] for lm in env_bible["fixed_world_landmarks"]],
        "shot_joins": [
            {"join": "S01->S02", "invariant": "Hemp rope remains on right of bell axis; PIP stays at coiled rope base"},
            {"join": "S02->S03", "invariant": "TAVI lunges from left toward right-side hemp rope; upward 2D framing"},
            {"join": "S03->S04", "invariant": "Rope slip at 8.55s drives continuous bell oscillation into S04 wide interior"},
            {"join": "S04->S05", "invariant": "TAVI exits right in S04 and ascends left-to-right up tower stairs in S05"},
            {"join": "S05->S06", "invariant": "Stair summit leads onto upper oak catwalk beside swinging bronze bell mouth"},
            {"join": "S06->S07", "invariant": "While TAVI holds clapper silent above, rope remains taut down to PIP at base"},
            {"join": "S07->S08", "invariant": "PIP sneeze yank at 24.85s triggers bell toll heard & seen across courtyard in S08"},
        ],
    }
    (story_dir / "continuity_ledger.json").write_text(json.dumps(continuity_ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    shots_runtime = {
        "title": "The Bell That Rang Too Early",
        "duration": 30.0,
        "render_mode": "canvas2d_only",
        "style_profile": "squire_cinematic_2d.v1",
        "shots": [
            {
                "id": sh["id"],
                "start": sh["start"],
                "end": sh["end"],
                "line": sh["line"],
                "speaker": "NARRATOR",
                "char": "TAVI",
                "in": {"type": "cut"},
                "notes": sh.get("notes", ""),
                "sfx": sh["sfx"],
            }
            for sh in SHOT_PLAN
        ],
        "music": [
            {"start": 0.0, "end": 18.85, "bed": "user", "gainDb": 0},
            {"start": 24.85, "end": 30.0, "bed": "user", "gainDb": 1},
        ],
    }
    (story_dir / "shots.json").write_text(json.dumps(shots_runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 5. Build complete SHA-256 asset provenance manifest
    code_files = [
        "scenes/shots/bell_film.js",
        "scenes/shots/thumb.js",
        "story/style_profile.json",
        "story/character_bible.json",
        "story/environment_bible.json",
        "story/props.json",
        "story/camera_beats.json",
        "story/storyboard.json",
        "story/continuity_ledger.json",
        "story/shots.json",
    ]
    tracked_code_entries = {}
    for rel in code_files:
        fp = proj_dir / rel
        if fp.is_file():
            tracked_code_entries[rel] = {
                "origin": "AUTHORED_FRESH_IN_KH02_RUN",
                "sha256": _sha256_file(fp),
                "bytes": fp.stat().st_size,
            }

    asset_manifest = {
        "schema_version": "kh02_asset_manifest.v1",
        "project": proj_dir.name,
        "render_mode": "canvas2d_only",
        "style_id": "squire_cinematic_2d.v1",
        "style_lock_digest": style_bible["canonical_digest"],
        "external_copied_images_count": 0,
        "reused_demo_frames_count": 0,
        "three3d_assets_count": 0,
        "voice_provenance": {
            "status": voice_res["status"],
            "provider": "Local OS SpeechSynthesizer (Windows SAPI 48kHz mono, 1.0x rate)",
            "timeline_voice_sha256": voice_res["voice_wav_sha256"],
            "duration_sec": voice_res["voice_duration_sec"],
            "clips": voice_res["clips"],
        },
        "procedural_audio_assets": audio_assets,
        "project_source_files": tracked_code_entries,
    }
    (story_dir / "asset_manifest.json").write_text(json.dumps(asset_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Validate style contract on storyboard
    contract_check = validate_squire_style_contract(style_bible, storyboard_spec)
    if not contract_check["valid"]:
        raise RuntimeError(f"Style contract validation failed: {contract_check['errors']}")

    return {
        "status": "PROJECT_BUILT",
        "project_dir": str(proj_dir),
        "voice_status": voice_res["status"],
        "style_contract": contract_check,
        "audio_cues_count": len(audio_assets),
    }


if __name__ == "__main__":
    res = build_bell_project()
    print(json.dumps(res, indent=2))
