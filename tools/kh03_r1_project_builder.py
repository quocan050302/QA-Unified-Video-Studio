#!/usr/bin/env python3
"""kh03_r1_project_builder.py — End-to-End Deterministic Project Builder & Renderer for KH-03.0.R1.

Builds native 9:16 (1080x1920 @ 24fps, 30.000s, 720 frames) Roman Squire 2D films driven by
tools/kh03_script_beat_director.py and tools/kh03_narration_timeline.py, synthesizes original
dusk city-gate foley + Roman underscore, renders via render.mjs, mixes via tools/mix.py,
and compiles full contact sheets, action strips & render manifests.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.kh03_style_lock import load_roman_master_style
from tools.kh03_narration_timeline import (
    synthesize_or_import_narration,
    pack_narration_into_30s,
    align_words_and_lines,
    merge_narration_visual_mapping,
)
from tools.kh03_script_beat_director import (
    normalize_script_lines,
    measure_voice_timeline,
    extract_semantic_beats,
    split_beat_into_visual_events,
    compose_shot_plan,
    build_line_shot_crosswalk,
    schedule_editorial_camera,
    score_pacing_proxies,
    validate_shot_plan_contract,
)
from tools.validator import validate_project

DEFAULT_R1_PROJECT_DIR = REPO_ROOT / "projects" / "kh03_r1_roman_gate_message_30s"
DEFAULT_R1_TITLE = "KH03_R1_ROMAN_GATE_MESSAGE_ORIGINAL_30S_9x16"

THE_MESSAGE_ONE_SECOND_LATE_SCRIPT: List[Dict[str, Any]] = [
    {"id": "L01", "text": "At sunset, the city gate began to close with one last courier outside.", "pause_after_sec": 0.14},
    {"id": "L02", "text": "Inside Marcus's satchel lay one urgent wax-sealed order.", "pause_after_sec": 0.14},
    {"id": "L03", "text": "His sandals hammered damp cobbles as the oak gap narrowed.", "pause_after_sec": 0.14},
    {"id": "L04", "text": "Twenty paces short he clipped a curb—the scroll flew from his grip.", "pause_after_sec": 0.12},
    {"id": "L05", "text": "Guard Gaius lunged and missed. His heel pinned the scroll beside the drain.", "pause_after_sec": 0.16},
    {"id": "L06", "text": "Out of breath, he cracked the crimson seal open.", "pause_after_sec": 0.14},
    {"id": "L07", "text": "Four painted words stared up: KEEP THE GATE OPEN.", "pause_after_sec": 0.22},
    {"id": "L08", "text": "He yelled to the tower.", "pause_after_sec": 0.10},
    {"id": "L09", "text": "Too late—the heavy oak leaves slammed shut.", "pause_after_sec": 0.20},
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


def _synth_r1_gate_sfx_and_music(project_dir: Path) -> Dict[str, Any]:
    """Synthesize deterministic 48kHz procedural dusk city-gate SFX & original Roman chase music bed."""
    sr = 48000
    rng = np.random.default_rng(2026111709)
    sfx_dir = project_dir / "audio" / "sfx"
    music_dir = project_dir / "audio" / "music"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)

    sfx_hashes: Dict[str, str] = {}

    def save_norm_wav(out_path: Path, sig: np.ndarray, peak: float = 0.85) -> str:
        m = float(np.max(np.abs(sig))) + 1e-9
        y = (sig / m * peak).astype(np.float32)
        sf.write(str(out_path), y, sr, subtype="PCM_16")
        return _sha256_file(out_path)

    # 1. Cobblestone brisk sandal footstep burst (3 quick taps)
    t = np.linspace(0, 0.72, int(0.72 * sr), endpoint=False)
    cobble = np.zeros_like(t)
    for idx_t in (0.04, 0.25, 0.46):
        i0 = int(idx_t * sr)
        tt = t[: len(t) - i0]
        snap = np.sin(2 * np.pi * np.cumsum(np.linspace(380, 95, len(tt))) / sr) * np.exp(-tt * 42.0)
        grit = np.convolve(rng.standard_normal(len(tt)), np.ones(7) / 7.0, mode="same") * np.exp(-tt * 38.0) * 0.5
        cobble[i0:] += (snap + grit) * 0.75
    sfx_hashes["kh03_r1_cobble_step.wav"] = save_norm_wav(sfx_dir / "kh03_r1_cobble_step.wav", cobble, 0.80)

    # 2. Heavy timber winch creak & hemp rope strain
    t = np.linspace(0, 1.15, int(1.15 * sr), endpoint=False)
    winch = np.sin(2 * np.pi * np.cumsum(145 + 32 * np.sin(2 * np.pi * 6.5 * t)) / sr) * np.exp(-t * 2.1) * 0.65
    gear = np.zeros_like(t)
    for k in range(5):
        off = int((0.08 + k * 0.21) * sr)
        if off < len(t):
            tt = t[: len(t) - off]
            gear[off:] += np.sin(2 * np.pi * 240 * tt) * np.exp(-tt * 32.0) * 0.55
    sfx_hashes["kh03_r1_winch_creak.wav"] = save_norm_wav(sfx_dir / "kh03_r1_winch_creak.wav", winch + gear, 0.76)

    # 3. Curb stumble impact + stone skid scrape
    t = np.linspace(0, 0.56, int(0.56 * sr), endpoint=False)
    thump = np.sin(2 * np.pi * np.cumsum(np.linspace(190, 52, len(t))) / sr) * np.exp(-t * 20.0)
    scrape = np.convolve(rng.standard_normal(len(t)), np.ones(11) / 11.0, mode="same") * np.exp(-t * 14.0) * 0.7
    sfx_hashes["kh03_r1_stumble_scrape.wav"] = save_norm_wav(sfx_dir / "kh03_r1_stumble_scrape.wav", thump + scrape, 0.84)

    # 4. Crisp parchment scroll whoosh / airborne tumble flutter
    t = np.linspace(0, 0.80, int(0.80 * sr), endpoint=False)
    env = np.sin(np.pi * np.clip(t / 0.80, 0, 1)) ** 1.5
    n_raw = rng.standard_normal(len(t))
    band = np.convolve(n_raw, np.ones(14) / 14.0, mode="same") - np.convolve(n_raw, np.ones(56) / 56.0, mode="same")
    flutter = band * (1.0 + 0.45 * np.sin(2 * np.pi * 19.0 * t)) * env * 2.4
    sfx_hashes["kh03_r1_scroll_whoosh.wav"] = save_norm_wav(sfx_dir / "kh03_r1_scroll_whoosh.wav", flutter, 0.82)

    # 5. Guard cloak lunge swoosh
    t = np.linspace(0, 0.50, int(0.50 * sr), endpoint=False)
    env = np.sin(np.pi * np.clip(t / 0.50, 0, 1)) ** 1.4
    lunge_band = np.convolve(rng.standard_normal(len(t)), np.ones(22) / 22.0, mode="same") * env
    sfx_hashes["kh03_r1_guard_lunge_swoosh.wav"] = save_norm_wav(sfx_dir / "kh03_r1_guard_lunge_swoosh.wav", lunge_band, 0.78)

    # 6. Heavy leather sandal stomp at wet stone drain edge
    t = np.linspace(0, 0.48, int(0.48 * sr), endpoint=False)
    heel = np.sin(2 * np.pi * np.cumsum(np.linspace(230, 56, len(t))) / sr) * np.exp(-t * 25.0)
    grate_ring = 0.28 * np.sin(2 * np.pi * 760 * t) * np.exp(-t * 18.0) + 0.18 * np.sin(2 * np.pi * 1190 * t) * np.exp(-t * 22.0)
    splash = np.convolve(rng.standard_normal(len(t)), np.ones(8) / 8.0, mode="same") * np.exp(-t * 21.0) * 0.65
    sfx_hashes["kh03_r1_sandal_stomp_drain.wav"] = save_norm_wav(sfx_dir / "kh03_r1_sandal_stomp_drain.wav", heel + grate_ring + splash, 0.88)

    # 7. Brittle crimson wax seal crack + parchment snap
    t = np.linspace(0, 0.52, int(0.52 * sr), endpoint=False)
    crack = rng.standard_normal(len(t)) * np.exp(-t * 75.0) * 0.9
    rustle = np.convolve(rng.standard_normal(len(t)), np.ones(9) / 9.0, mode="same") * np.exp(-np.maximum(0, t - 0.08) * 11.0) * (t > 0.08) * 0.65
    sfx_hashes["kh03_r1_wax_seal_crack.wav"] = save_norm_wav(sfx_dir / "kh03_r1_wax_seal_crack.wav", crack + rustle, 0.82)

    # 8. Distant tower watch-bell ping / alarm echo under guard shout
    t = np.linspace(0, 0.68, int(0.68 * sr), endpoint=False)
    echo = (0.45 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 660 * t)) * np.exp(-t * 6.5)
    sfx_hashes["kh03_r1_tower_shout_echo.wav"] = save_norm_wav(sfx_dir / "kh03_r1_tower_shout_echo.wav", echo, 0.72)

    # 9. Massive oak gate slam + heavy iron slide bolt locking home
    t = np.linspace(0, 0.92, int(0.92 * sr), endpoint=False)
    oak_boom = np.sin(2 * np.pi * np.cumsum(np.linspace(140, 38, len(t))) / sr) * np.exp(-t * 8.5) * 1.15
    oak_crack = np.convolve(rng.standard_normal(len(t)), np.ones(12) / 12.0, mode="same") * np.exp(-t * 32.0) * 0.75
    bolt_idx = int(0.18 * sr)
    bolt = np.zeros_like(t)
    tb = t[: len(t) - bolt_idx]
    bolt[bolt_idx:] = (0.62 * np.sin(2 * np.pi * 310 * tb) * np.exp(-tb * 24.0) + 0.35 * np.sin(2 * np.pi * 890 * tb) * np.exp(-tb * 36.0))
    sfx_hashes["kh03_r1_iron_bolt_slam.wav"] = save_norm_wav(sfx_dir / "kh03_r1_iron_bolt_slam.wav", oak_boom + oak_crack + bolt, 0.92)

    # 10. Original 12.0s Loopable Dusk Roman Urgency Underscore (frame drum ostinato + low Dorian plucked pulse)
    bed_dur = 12.0
    tb_full = np.linspace(0, bed_dur, int(bed_dur * sr), endpoint=False)
    bed = np.zeros_like(tb_full)
    step_dt = 0.25  # 120 BPM eighth-note drive
    scale_hz = [110.0, 110.0, 130.81, 146.83, 130.81, 123.47, 110.0, 98.0]  # A2 Dorian urgent motif
    n_steps = int(bed_dur / step_dt)
    for k in range(n_steps):
        i0 = int(k * step_dt * sr)
        n_rem = min(int(0.42 * sr), len(bed) - i0)
        tt = np.arange(n_rem, dtype=np.float32) / sr
        f_note = scale_hz[k % len(scale_hz)]
        # Plucked gut lyre bass note (soft triangle + warm 2nd harmonic)
        pluck = (0.55 * np.sin(2 * np.pi * f_note * tt) + 0.18 * np.sin(4 * np.pi * f_note * tt)) * np.exp(-tt * 7.5)
        bed[i0 : i0 + n_rem] += pluck * 0.42
        # Muted Roman tympanum downbeat / backbeat
        if k % 2 == 0:
            drum_f = 92.0 if k % 4 == 0 else 78.0
            drum = np.sin(2 * np.pi * drum_f * tt * np.exp(-tt * 3.0)) * np.exp(-tt * 14.0)
            bed[i0 : i0 + n_rem] += drum * (0.55 if k % 4 == 0 else 0.36)
    bed_path = music_dir / "bed_r1_dusk_chase.wav"
    bed_hash = save_norm_wav(bed_path, bed, 0.65)

    return {
        "sfx_files": {k: {"path": f"audio/sfx/{k}", "sha256": v} for k, v in sfx_hashes.items()},
        "music_bed": {"path": "audio/music/bed_r1_dusk_chase.wav", "sha256": bed_hash, "bpm": 120, "duration_sec": bed_dur},
    }


def _map_sub_action_sfx(shot: Dict[str, Any]) -> List[Dict[str, Any]]:
    sub = shot.get("sub_action", "")
    dur = float(shot.get("duration", 1.5))
    mapping = {
        "moving_scroll_toward_closing_oak_gap": [{"at": 0.08, "name": "audio/sfx/kh03_r1_cobble_step.wav", "gainDb": -3.0}],
        "winch_drum_turns_and_doors_converge": [{"at": 0.12, "name": "audio/sfx/kh03_r1_winch_creak.wav", "gainDb": -2.0}],
        "courier_sprint_with_satchel": [
            {"at": 0.10, "name": "audio/sfx/kh03_r1_cobble_step.wav", "gainDb": -2.0},
            {"at": round(min(dur - 0.3, 1.35), 2), "name": "audio/sfx/kh03_r1_cobble_step.wav", "gainDb": -1.5},
        ],
        "sandals_hammer_damp_cobbles": [
            {"at": 0.05, "name": "audio/sfx/kh03_r1_cobble_step.wav", "gainDb": -1.0},
            {"at": round(dur * 0.52, 2), "name": "audio/sfx/kh03_r1_cobble_step.wav", "gainDb": -0.5},
        ],
        "closing_oak_gap_tension_cut": [{"at": 0.10, "name": "audio/sfx/kh03_r1_winch_creak.wav", "gainDb": -1.0}],
        "stumble_trip_impact": [{"at": round(dur * 0.34, 2), "name": "audio/sfx/kh03_r1_stumble_scrape.wav", "gainDb": 0.5}],
        "airborne_scroll_arc": [{"at": 0.06, "name": "audio/sfx/kh03_r1_scroll_whoosh.wav", "gainDb": 0.0}],
        "guard_lunges_and_scroll_slips_past_gloves": [{"at": 0.12, "name": "audio/sfx/kh03_r1_guard_lunge_swoosh.wav", "gainDb": 0.0}],
        "sandal_stomps_scroll_at_drain_edge": [{"at": round(dur * 0.44, 2), "name": "audio/sfx/kh03_r1_sandal_stomp_drain.wav", "gainDb": 1.5}],
        "guard_relieved_exhale_retrieving_scroll": [],
        "break_wax_seal_unroll_scroll": [{"at": round(dur * 0.25, 2), "name": "audio/sfx/kh03_r1_wax_seal_crack.wav", "gainDb": 0.5}],
        "legible_scroll_text_card_reveal": [],
        "guard_shouts_up_to_winch_tower": [{"at": round(dur * 0.18, 2), "name": "audio/sfx/kh03_r1_tower_shout_echo.wav", "gainDb": -1.0}],
        "oak_gate_bolt_slams_home_behind_guard": [{"at": round(dur * 0.32, 2), "name": "audio/sfx/kh03_r1_iron_bolt_slam.wav", "gainDb": 2.5}],
        "guard_deadpan_blink_with_open_scroll": [],
    }
    return mapping.get(sub, [])


def _generate_r1_scene_js(shots: List[Dict[str, Any]]) -> str:
    shot_lines = [
        f"registerShot('{sh['id']}', {{ draw(g, lt, info) {{ renderScriptShotFrame(g, info?.globalT ?? ({sh['start']} + lt)); }} }});"
        for sh in shots
    ]
    return "\n".join([
        "// gate_message_r1.js — Runtime 2D Scene Binder for KH-03.0.R1 Script-Driven Film.",
        "// 100% 2D Canvas via Production Squire renderScriptShotFrame(). Zero Three.js.",
        "import { registerShot, E } from '/engine/core.js';",
        "import { renderScriptShotFrame } from '/packs/squire/pack.js';",
        "",
        *shot_lines,
        "",
        "// Also bind any dynamically injected shot_plan shots cleanly at runtime:",
        "for (const s of (E.shots || [])) {",
        "  if (s?.id && !['" + "', '".join(sh["id"] for sh in shots) + "'].includes(s.id)) {",
        "    registerShot(s.id, { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (s.start + lt)); } });",
        "  }",
        "}",
        "",
    ])


def _generate_r1_thumb_js() -> str:
    return """// thumb.js — Native 9:16 Thumbnail Cover Art for KH-03.0.R1 ("The Message That Arrived One Second Late").
import { E, registerShot } from '/engine/core.js';
import { PAL, titleText, blockArrow, drawRomanCityApproachDusk2D, drawSealedRomanScroll2D, romanActorAt, drawRomanMasterActor2D } from '/packs/squire/pack.js';

registerShot('thumb', {
  draw(g) {
    const w = E.W || 1080;
    const h = E.H || 1920;
    drawRomanCityApproachDusk2D(g, { globalT: 1.5, gateCloseFrac: 0.78, boltDropFrac: 0.0 }, { horizonYFrac: 0.48, groundYFrac: 0.60 });
    const courier = romanActorAt(1.5, {
      start: 0, end: 2,
      actors: {
        courier_marcus: {
          archetypeId: 'courier_marcus', courierSatchel: true, hasShield: false, weapon: 'none',
          xFrac: 0.25, yFrac: 0.67, hFrac: 0.30, bodyRot: 0.14,
          leftFootLocal: [-12, 0], rightFootLocal: [14, -6], armsAng: [-45, -30, 58, 22], face: 'shock', look: 0.85,
        },
      },
    }, 'courier_marcus', { W: w, H: h, globalT: 1.5 });
    drawRomanMasterActor2D(g, courier, { seed: 7, courierSatchel: true, feathers: 2, featherColors: [PAL.white, PAL.gold], shoeMode: 'side' });
    blockArrow(g, w * 0.64, h * 0.27, w * 0.51, h * 0.35, { w: w * 0.048, fill: '#e0352f', lw: 6 });
    drawSealedRomanScroll2D(g, w * 0.70, h * 0.49, w * 0.27, { mode: 'unrolled_message', rot: 0.04, mudAmount: 0.85, lines: ['KEEP', 'THE GATE', 'OPEN'] });
    titleText(g, 'ONE SECOND', w * 0.5, h * 0.115, h * 0.064, { color: '#ffe875', rot: -0.025 });
    titleText(g, 'TOO LATE!', w * 0.5, h * 0.195, h * 0.068, { color: '#ff5247', rot: -0.025 });
  },
});
"""


def build_roman_script_driven_project(
    script: str | List[str] | List[Dict[str, Any]] = THE_MESSAGE_ONE_SECOND_LATE_SCRIPT,
    project_dir: Path | str = DEFAULT_R1_PROJECT_DIR,
    title: str = DEFAULT_R1_TITLE,
    aspect: str = "9:16",
    fps: int = 24,
    target_duration: float = 30.0,
    seed: int = 20261117,
    voice_cfg: Optional[Dict[str, Any]] = None,
    scratch_dir: Optional[Path | str] = None,
    allow_many_to_one_merge: bool = True,
) -> Dict[str, Any]:
    """Compile any script into a complete, deterministic, 2D-only Squire Roman project."""
    proj = Path(project_dir).resolve()
    proj.mkdir(parents=True, exist_ok=True)
    scr = Path(scratch_dir).resolve() if scratch_dir else (proj / "build" / "r1_tts")
    scr.mkdir(parents=True, exist_ok=True)

    sb = load_roman_master_style()
    norm_lines = normalize_script_lines(script)
    synth = synthesize_or_import_narration(norm_lines, proj, voice_cfg=voice_cfg, scratch_dir=scr / "raw")
    packed = pack_narration_into_30s(
        synth["clips"],
        target_duration=target_duration,
        preferred_stretch=1.10,
        max_stretch=1.15,
        scratch_dir=scr / "packed",
    )
    aligned = align_words_and_lines(packed)
    vt = measure_voice_timeline(proj, aligned)

    cast_entities = [
        {"actor_id": "courier_marcus", "aliases": ["marcus", "courier", "sandals", "his", "he"], "archetype": "rookie_hastatus"},
        {"actor_id": "gate_guard_gaius", "aliases": ["gaius", "guard"], "archetype": "instructor_princeps"},
        {"actor_id": "watchman_sec", "aliases": ["winch", "tower", "crew"], "archetype": "veteran_neighbor_legionary"},
    ]
    beats = extract_semantic_beats(aligned["lines"], entities=cast_entities)

    line_by_id = {l["id"]: l for l in aligned["lines"]}
    visual_events: List[Dict[str, Any]] = []
    for b in beats:
        lt = line_by_id.get(b["line_ids"][0] if b.get("line_ids") else b["line_id"])
        visual_events.extend(split_beat_into_visual_events(b, lt, min_event_frames=12, aspect=aspect))

    target_frames = int(round(target_duration * fps))
    shot_plan = compose_shot_plan(
        beats,
        vt,
        visual_events,
        target_frames=target_frames,
        fps=fps,
        aspect=aspect,
        seed=seed,
        allow_many_to_one_merge=allow_many_to_one_merge,
    )
    crosswalk = build_line_shot_crosswalk(aligned["lines"], shot_plan["shots"], aligned["words"])
    cam_beats = schedule_editorial_camera(shot_plan["shots"], aspect=aspect)
    proxies = score_pacing_proxies(shot_plan["shots"], aligned["lines"], aligned["words"], cam_beats)
    contract = validate_shot_plan_contract(shot_plan, crosswalk, cam_beats, vt, style_bible=sb)
    if not contract["valid"]:
        raise RuntimeError(f"KH03_R1_SHOT_PLAN_INVALID: {contract['errors']}")

    merge_res = merge_narration_visual_mapping(aligned, packed["master_voice"], shot_plan, crosswalk, proj)
    audio_assets = _synth_r1_gate_sfx_and_music(proj)

    config_data = {
        "title": title,
        "pack": "squire",
        "lang": "en",
        "aspect": aspect,
        "resolution": "1080p",
        "fps": fps,
        "style": "flat",
        "bars": "none",
        "fadeIn": 0.0,
        "fadeOut": 0.0,
        "captions": True,
        "captionStyle": "squire",
        "style_profile": "roman_squire_master.v1",
        "editorial_mode": "script_beat_director_v1",
        "render_mode": "canvas2d_only",
        "allow_3d_legacy_fallback": False,
        "music": {"enabled": True, "file": "audio/music/bed_r1_dusk_chase.wav", "gainDb": -14.0},
        "sfx": {"enabled": True, "gainDb": 0.0},
    }
    _atomic_write_json(proj / "config.json", config_data)

    # story/shots.json for player.js & tools/mix.py
    shots_payload = {
        "title": title,
        "duration": round(target_duration, 3),
        "aspect": aspect,
        "fps": fps,
        "shots": [
            {
                "id": sh["id"],
                "start": sh["start"],
                "end": sh["end"],
                "tpl": "custom",
                "scene": "gate_message_r1",
                "sub_action": sh["sub_action"],
                "location_id": sh["location_id"],
                "framing_scale": sh["framing_scale"],
                "line_ids": sh["line_ids"],
                "line": " / ".join(line_by_id[lid]["text"] for lid in sh["line_ids"] if lid in line_by_id),
                "sfx": _map_sub_action_sfx(sh),
                "notes": "DROP" if sh["sub_action"] in ("oak_gate_bolt_slams_home_behind_guard", "guard_deadpan_blink_with_open_scroll") else "",
                "in": {"type": "cut"},
            }
            for sh in shot_plan["shots"]
        ],
        "music": [
            {"start": 0.0, "end": round(max(0.5, shot_plan["shots"][-2]["start"]), 3), "bed": "user", "gainDb": -1.5}
        ],
    }
    _atomic_write_json(proj / "story" / "shots.json", shots_payload)

    _atomic_write_text(proj / "story" / "script.txt", "\n".join(f"{l['id']}: {l['text']}" for l in aligned["lines"]) + "\n")
    _atomic_write_json(proj / "story" / "shot_plan.json", shot_plan)
    _atomic_write_json(proj / "story" / "beats.json", {"schema_version": "kh03.r1.beats.v1", "beats": beats})
    _atomic_write_json(proj / "story" / "shot_to_line_map.json", crosswalk)
    _atomic_write_json(proj / "story" / "camera_beats.json", cam_beats)
    _atomic_write_json(proj / "story" / "pacing_report.json", proxies)
    _atomic_write_json(proj / "story" / "visual_timeline.json", {
        "schema_version": "kh03.r1.visual_timeline.v1",
        "total_frames": target_frames,
        "fps": fps,
        "shots": [
            {k: s[k] for k in ("id", "frame_start", "frame_end", "frame_count", "start", "end", "location_id", "framing_scale", "sub_action", "cut_rationale")}
            for s in shot_plan["shots"]
        ],
    })
    _atomic_write_json(proj / "story" / "storyboard.json", {
        "schema_version": "kh03.r1.storyboard.v1",
        "title": "The Message That Arrived One Second Late",
        "editorial_mode": "script_beat_director_v1",
        "style_profile": "roman_squire_master.v1",
        "shots": shot_plan["shots"],
    })
    _atomic_write_json(proj / "story" / "continuity_ledger.json", {
        "schema_version": "kh03.r1.continuity_ledger.v1",
        "world_invariants": {
            "gate_closure_monotonic": True,
            "axis_direction": "left_to_right_outside_to_inside",
            "scroll_mud_after_drain_stomp": True,
            "wardrobe_locked": True,
        },
        "actors": {
            "courier_marcus": {"archetype": "rookie_hastatus", "helmet": "montefortino_white_gold", "tunic": "#b83b31", "satchel": True, "shield": None},
            "gate_guard_gaius": {"archetype": "instructor_princeps", "helmet": "montefortino_red", "mustache": "big", "tunic": "#b83b31"},
            "watchman_sec": {"archetype": "veteran_neighbor_legionary", "helmet": "montefortino_white_red", "beard": "stubble", "tunic": "#b83b31"},
        },
        "props": {
            "sealed_scroll": {"text": "KEEP THE GATE OPEN", "seal_state_transitions": ["sealed", "pinned_muddy", "cracking", "unrolled"]},
            "city_gate": {"leaves_monotonic_close": True, "bolt_drops_on_slam": True},
        },
    })
    _atomic_write_json(proj / "story" / "sound_design.json", {
        "schema_version": "kh03.r1.sound_design.v1",
        "voice_provenance": synth["clips"][0]["source_kind"],
        "voice_sha256": merge_res["voice_wav_sha256"],
        "global_tempo_scale": packed["global_tempo_scale"],
        "audio_assets": audio_assets,
        "editorial_drop_shots": ["SH14", "SH15"],
    })
    _atomic_write_json(proj / "story" / "roman_master_style_ref.json", {
        "style_profile": "roman_squire_master.v1",
        "canonical_digest": sb["canonical_digest"],
        "out_ink": "#392a21",
        "render_mode": "canvas2d_only",
    })
    _atomic_write_json(proj / "story" / "character_bible.json", {
        "style_profile": "roman_squire_master.v1",
        "cast": cast_entities,
    })
    _atomic_write_json(proj / "story" / "environment_bible.json", {
        "locations": ["exterior_gate_approach", "gate_winch_machinery", "cobble_alley_chase", "interior_guard_threshold"],
        "aspect": aspect,
        "render_mode": "canvas2d_only",
    })
    _atomic_write_json(proj / "story" / "props.json", {
        "props": ["sealed_scroll", "city_gate", "drain_grate", "courier_satchel", "roman_caliga_sandal"],
    })

    _atomic_write_text(proj / "scenes" / "shots" / "gate_message_r1.js", _generate_r1_scene_js(shot_plan["shots"]))
    _atomic_write_text(proj / "scenes" / "shots" / "thumb.js", _generate_r1_thumb_js())
    _atomic_write_text(
        proj / "ARTIFACT_README.md",
        f"# {title}\n\n"
        f"- **Style Profile**: `roman_squire_master.v1` (digest `{sb['canonical_digest']}`)\n"
        f"- **Editorial Mode**: `script_beat_director_v1` (1:many & many:1 decoupled)\n"
        f"- **Format**: `{aspect}` (`1080x1920 @ {fps}fps`, `{target_frames}` frames, `{target_duration:.3f}s`)\n"
        f"- **Render Mode**: `canvas2d_only` (Zero Three.js/WebGL)\n"
        f"- **Shots / Lines**: `{len(shot_plan['shots'])}` shots from `{len(aligned['lines'])}` lines (`1:many={crosswalk['summary']['one_to_many_count']}`, `many:1={crosswalk['summary']['many_to_one_count']}`)\n"
        f"- **Editorial & Style Sign-Off**: `HUMAN_REVIEW_PENDING`\n",
    )

    val = validate_project(proj)
    if val["status"] != "PASS":
        raise RuntimeError(f"KH03_R1_VALIDATOR_BLOCKED: {val}")

    return {
        "status": "PASS",
        "project_dir": str(proj),
        "title": title,
        "shots_count": len(shot_plan["shots"]),
        "lines_count": len(aligned["lines"]),
        "words_count": len(aligned["words"]),
        "raw_total_speech_sec": synth["raw_total_speech_sec"],
        "global_tempo_scale": packed["global_tempo_scale"],
        "crosswalk_summary": crosswalk["summary"],
        "pacing_proxies": proxies,
        "validator_status": val["status"],
        "style_digest": sb["canonical_digest"],
    }


def _label_tile(im: Image.Image, text: str) -> Image.Image:
    out = im.copy()
    dr = ImageDraw.Draw(out)
    tw = max(120, min(out.width - 12, len(text) * 8 + 18))
    dr.rectangle([4, 4, tw, 28], fill=(18, 14, 12))
    dr.text((10, 9), text, fill=(248, 240, 224))
    return out


def _extract_frame_png(mp4_path: Path, t_sec: float, out_png: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, t_sec):.3f}", "-i", str(mp4_path), "-frames:v", "1", str(out_png)],
        check=True,
    )


def render_roman_r1_preview(
    project_dir: Path | str = DEFAULT_R1_PROJECT_DIR,
    review_packet_dir: Path | str | None = None,
    tracked_evidence_dir: Path | str | None = None,
    workers: int = 1,
) -> Dict[str, Any]:
    """Render native 1080x1920 24fps R1 film via render.mjs, mix via mix.py, and build review packet."""
    proj = Path(project_dir).resolve()
    cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    title = cfg.get("title", DEFAULT_R1_TITLE)
    pkt_dir = (
        Path(review_packet_dir).resolve()
        if review_packet_dir
        else (REPO_ROOT / "docs" / "antigravity_runs" / "KH-03_0_R1_SCRIPT_SHOT_20261117_080723Z_4ff0" / "preview_packet")
    )
    pkt_dir.mkdir(parents=True, exist_ok=True)
    stills_dir = pkt_dir / "stills_per_shot"
    stills_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    subprocess.run(["node", "render.mjs", "--project", str(proj), "--check", "--scale", "0.25"], cwd=str(REPO_ROOT), check=True)
    subprocess.run(["node", "render.mjs", "--project", str(proj), "--workers", str(max(1, min(3, workers)))], cwd=str(REPO_ROOT), check=True)
    render_wall_sec = round(time.monotonic() - t0, 3)

    subprocess.run(["node", "render.mjs", "--project", str(proj), "--thumb"], cwd=str(REPO_ROOT), check=True)

    t_mix0 = time.monotonic()
    subprocess.run([sys.executable, "tools/mix.py", "--project", str(proj)], cwd=str(REPO_ROOT), check=True)
    mix_wall_sec = round(time.monotonic() - t_mix0, 3)

    final_mp4 = proj / "out" / f"{title}.mp4"
    if not final_mp4.is_file():
        raise FileNotFoundError(f"Expected R1 MP4 missing at {final_mp4}")

    probe_raw = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(final_mp4)],
        capture_output=True, text=True, check=True,
    ).stdout
    probe_json = json.loads(probe_raw)
    decoded_frames = int(
        subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(final_mp4)],
            capture_output=True, text=True, check=True,
        ).stdout.strip().rstrip(",")
    )

    ebur_stderr = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(final_mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    ).stderr
    lufs_matches = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur_stderr)
    tp_matches = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur_stderr) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur_stderr)
    integrated_lufs = float(lufs_matches[-1]) if lufs_matches else -99.0
    true_peak_dbtp = float(tp_matches[-1]) if tp_matches else 0.0

    if not (-16.2 <= integrated_lufs <= -13.8 and true_peak_dbtp <= -1.0):
        mix_wav = proj / "build" / "mix.wav"
        video_silent = proj / "build" / "video_silent.mp4"
        cal_wav = proj / "build" / "mix_calibrated.wav"
        target_adj = (-15.0 - integrated_lufs) if (-30 < integrated_lufs < 0) else 0.0
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(mix_wav), "-af", f"volume={target_adj:.2f}dB,alimiter=limit=0.82:level=false", "-ar", "48000", "-ac", "2", str(cal_wav)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(video_silent), "-i", str(cal_wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final_mp4)],
            check=True,
        )
        cal_wav.unlink(missing_ok=True)
        ebur_stderr = subprocess.run(["ffmpeg", "-v", "info", "-i", str(final_mp4), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
        integrated_lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ebur_stderr)[-1])
        tp2 = re.findall(r"True peak:\s+(-?[\d.]+) dBFS", ebur_stderr) or re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ebur_stderr)
        true_peak_dbtp = float(tp2[-1])

    # Build 9:16 contact sheet (4 cols x rows) & 1 still per shot
    shots = shot_plan["shots"]
    cols = 5 if len(shots) >= 13 else 4
    rows = (len(shots) + cols - 1) // cols
    tw, th = 270, 480
    contact = Image.new("RGB", (cols * tw, rows * th), (20, 16, 14))
    still_records: List[Dict[str, Any]] = []
    for idx, sh in enumerate(shots):
        mid_t = round((sh["start"] + sh["end"]) * 0.5, 3)
        spng = stills_dir / f"{sh['id']}_t{mid_t:05.2f}s.png"
        sjpg = stills_dir / f"{sh['id']}_t{mid_t:05.2f}s.jpg"
        _extract_frame_png(final_mp4, mid_t, spng)
        im = Image.open(spng).convert("RGB")
        im.save(sjpg, quality=90)
        spng.unlink(missing_ok=True)
        lbl = f"{sh['id']} ({sh['duration']:.2f}s) {sh['sub_action'][:22]}"
        tile = _label_tile(im.resize((tw, th), Image.Resampling.LANCZOS), lbl)
        contact.paste(tile, ((idx % cols) * tw, (idx // cols) * th))
        still_records.append({"shot_id": sh["id"], "t_sec": mid_t, "jpg": str(sjpg), "sha256": _sha256_file(sjpg)})
    contact_path = pkt_dir / "contact_sheet_all_shots.jpg"
    contact.save(contact_path, quality=91)

    # Multi-frame 9:16 Action Strips around Stumble+Scroll, Guard Lunge+Drain Pin, and Reveal+Bolt Slam
    find_shot = lambda sub: next((s for s in shots if s.get("sub_action") == sub), shots[0])
    s_trip = find_shot("stumble_trip_impact")
    s_arc = find_shot("airborne_scroll_arc")
    s_lunge = find_shot("guard_lunges_and_scroll_slips_past_gloves")
    s_pin = find_shot("sandal_stomps_scroll_at_drain_edge")
    s_read = find_shot("legible_scroll_text_card_reveal")
    s_slam = find_shot("oak_gate_bolt_slams_home_behind_guard")
    s_dead = find_shot("guard_deadpan_blink_with_open_scroll")

    strips_spec = [
        (
            "action_strip_1_stumble_and_scroll_launch.jpg",
            [
                (s_trip["start"] + 0.15, f"{s_trip['start']+0.15:.2f}s Approach"),
                (s_trip["start"] + s_trip["duration"] * 0.55, f"{s_trip['start']+s_trip['duration']*0.55:.2f}s Curb Trip"),
                (s_trip["end"] - 0.12, f"{s_trip['end']-0.12:.2f}s Slip Free"),
                (s_arc["start"] + s_arc["duration"] * 0.45, f"{s_arc['start']+s_arc['duration']*0.45:.2f}s Scroll Arc"),
                (s_arc["end"] - 0.12, f"{s_arc['end']-0.12:.2f}s Arch Entry"),
            ],
        ),
        (
            "action_strip_2_guard_lunge_and_drain_pin.jpg",
            [
                (s_lunge["start"] + 0.12, f"{s_lunge['start']+0.12:.2f}s Guard Lunge"),
                (s_lunge["end"] - 0.15, f"{s_lunge['end']-0.15:.2f}s Fingertip Miss"),
                (s_pin["start"] + 0.18, f"{s_pin['start']+0.18:.2f}s Slide to Drain"),
                (s_pin["start"] + s_pin["duration"] * 0.58, f"{s_pin['start']+s_pin['duration']*0.58:.2f}s Sandal Pin"),
                (s_pin["end"] - 0.12, f"{s_pin['end']-0.12:.2f}s Drain Safe"),
            ],
        ),
        (
            "action_strip_3_scroll_reveal_and_bolt_slam.jpg",
            [
                (s_read["start"] + s_read["duration"] * 0.40, f"{s_read['start']+s_read['duration']*0.40:.2f}s KEEP OPEN"),
                (s_read["end"] - 0.15, f"{s_read['end']-0.15:.2f}s Clear Read"),
                (s_slam["start"] + s_slam["duration"] * 0.48, f"{s_slam['start']+s_slam['duration']*0.48:.2f}s Bolt Drop"),
                (s_dead["start"] + 0.35, f"{s_dead['start']+0.35:.2f}s Locked In"),
                (s_dead["end"] - 0.08, f"{s_dead['end']-0.08:.2f}s Deadpan End"),
            ],
        ),
        (
            "cut_interval_strip_0p5s.jpg",
            [(t_c, f"{t_c:.1f}s") for t_c in [round(s_trip["start"] + i * 0.5, 2) for i in range(6)]],
        ),
    ]
    tmp_png = proj / "build" / "_r1_strip.png"
    strip_records: List[Dict[str, Any]] = []
    for sname, frames in strips_spec:
        sw, sh_h = 270, 480
        sim = Image.new("RGB", (len(frames) * sw, sh_h), (20, 16, 14))
        for j, (fts, flbl) in enumerate(frames):
            _extract_frame_png(final_mp4, min(29.95, float(fts)), tmp_png)
            fim = Image.open(tmp_png).convert("RGB").resize((sw, sh_h), Image.Resampling.LANCZOS)
            sim.paste(_label_tile(fim, flbl), (j * sw, 0))
        tmp_png.unlink(missing_ok=True)
        sp = pkt_dir / sname
        sim.save(sp, quality=91)
        strip_records.append({"name": sname, "path": str(sp), "sha256": _sha256_file(sp)})

    thumb_png = proj / "out" / "thumbnail.png"
    thumb_9x16 = pkt_dir / "thumbnail_9x16.jpg"
    if thumb_png.is_file():
        Image.open(thumb_png).convert("RGB").save(thumb_9x16, quality=92)

    v_stream = next((s for s in probe_json.get("streams", []) if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in probe_json.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt_dur = float(probe_json.get("format", {}).get("duration", 0.0))

    manifest = {
        "project": proj.name,
        "title": title,
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
        "review_packet": {
            "contact_sheet_all_shots": str(contact_path),
            "thumbnail_9x16": str(thumb_9x16),
            "action_strips": strip_records,
            "stills_count": len(still_records),
        },
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "style_approved": "HUMAN_REVIEW_PENDING",
    }
    _atomic_write_json(pkt_dir / "r1_render_manifest.json", manifest)

    if tracked_evidence_dir:
        tev = Path(tracked_evidence_dir).resolve()
        tev.mkdir(parents=True, exist_ok=True)
        for p in [contact_path, thumb_9x16, pkt_dir / "r1_render_manifest.json"]:
            if p.is_file():
                shutil.copy2(p, tev / p.name)
        for sr_item in strip_records:
            shutil.copy2(sr_item["path"], tev / sr_item["name"])

    return manifest
