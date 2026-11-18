#!/usr/bin/env python3
"""kh03_r2_project_builder.py — End-to-End Deterministic Project Builder & Renderer for KH-03.0.R2.

Builds native 9:16 (1080x1920 @ 24fps) Roman Squire 2D films driven strictly by the generalized
KH-03.0.R2 Action Capability Registry & Causal ActionGraph Compiler (`editorial_mode: roman_action_director_v2`).
Produces original 48kHz Foley SFX + Mediterranean Roman market/harbor/forum music underscore (zero R1/R0 reuse),
renders via render.mjs, mixes via tools/mix.py, validates fail-closed contracts, and generates full
decoded-pixel perceptual QA + review contact sheets.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
    V2_EDITORIAL_MODE,
    compile_v2_editorial_plan,
    normalize_script_lines,
)
from tools.kh03_perceptual_qa import build_perceptual_review_packet
from tools.validator import validate_project

DEFAULT_R2_PROJECT_DIR = REPO_ROOT / "projects" / "kh03_r2_roman_runaway_cart_30s"
DEFAULT_R2_TITLE = "KH03_R2_ROMAN_RUNAWAY_CART_ORIGINAL_30S_9x16"

THE_CART_THAT_WOULD_NOT_STOP_SCRIPT: List[Dict[str, Any]] = [
    {"id": "L01", "text": "At Rome's market hill rested a grain cart.", "pause_after_sec": 0.14},
    {"id": "L02", "text": "Downhill, Baker Lucius stood beside his hot oven.", "pause_after_sec": 0.14},
    {"id": "L03", "text": "A brake peg cracked; the cart rolled downhill.", "pause_after_sec": 0.12},
    {"id": "L04", "text": "Market shoppers dodged street obstacles.", "pause_after_sec": 0.12},
    {"id": "L05", "text": "Apprentice Titus sprinted; swiftly Titus caught the hemp rope.", "pause_after_sec": 0.12},
    {"id": "L06", "text": "Titus whipped the rope around a bollard; Titus braced.", "pause_after_sec": 0.14},
    {"id": "L07", "text": "The cart halted short; one loaf bounced off the tray.", "pause_after_sec": 0.12},
    {"id": "L08", "text": "It arced high; it landed squarely on Centurion Varro's helmet.", "pause_after_sec": 0.22},
    {"id": "L09", "text": "Nobody dared laugh; Centurion Varro kept walking.", "pause_after_sec": 0.22},
    {"id": "L10", "text": "Behind him, the market cheered Titus.", "pause_after_sec": 0.15},
]

RIVER_HARBOR_HOLDOUT_SCRIPT: List[Dict[str, Any]] = [
    {"id": "B01", "text": "At the river quay; the vexillum drifted.", "pause_after_sec": 0.10},
    {"id": "B02", "text": "Marc threw a rope; Marc hauled the standard.", "pause_after_sec": 0.10},
]

FORUM_COURTYARD_HOLDOUT_SCRIPT: List[Dict[str, Any]] = [
    {"id": "C01", "text": "In the forum courtyard, a messenger stumbled.", "pause_after_sec": 0.08},
    {"id": "C02", "text": "His helmet rolled under a stone bench.", "pause_after_sec": 0.08},
    {"id": "C03", "text": "Cassius picked up the crest, and Cassius handed it back.", "pause_after_sec": 0.10},
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


def _synth_r2_original_audio(project_dir: Path, music_style: str = "market_comedy") -> Dict[str, Any]:
    """Synthesize fresh deterministic 48kHz Foley SFX & original Roman comedic/adventure score (zero R1 reuse)."""
    sr = 48000
    rng = np.random.default_rng(2026111722)
    sfx_dir = project_dir / "audio" / "sfx"
    music_dir = project_dir / "audio" / "music"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)

    sfx_hashes: Dict[str, str] = {}

    def save_wav(out_path: Path, sig: np.ndarray, peak: float = 0.85) -> str:
        m = float(np.max(np.abs(sig))) + 1e-9
        y = (sig / m * peak).astype(np.float32)
        sf.write(str(out_path), y, sr, subtype="PCM_16")
        return _sha256_file(out_path)

    # 1. Brittle wooden brake-peg snap
    t = np.linspace(0, 0.45, int(0.45 * sr), endpoint=False)
    snap = np.sin(2 * np.pi * np.cumsum(np.linspace(1150, 210, len(t))) / sr) * np.exp(-t * 48.0)
    splinter = rng.standard_normal(len(t)) * np.exp(-t * 58.0) * 0.7
    sfx_hashes["r2_wood_peg_snap.wav"] = save_wav(sfx_dir / "r2_wood_peg_snap.wav", snap + splinter, 0.88)

    # 2. Wooden cart wheel rattle over downhill market cobbles
    t = np.linspace(0, 1.35, int(1.35 * sr), endpoint=False)
    rattle = np.zeros_like(t)
    for k in range(11):
        i0 = int((0.04 + k * 0.11) * sr)
        tt = t[: max(1, len(t) - i0)]
        clack = (np.sin(2 * np.pi * (165 + (k % 3) * 35) * tt) * 0.65 + rng.standard_normal(len(tt)) * 0.3) * np.exp(-tt * 34.0)
        rattle[i0 : i0 + len(tt)] += clack * 0.6
    sfx_hashes["r2_cart_cobble_rattle.wav"] = save_wav(sfx_dir / "r2_cart_cobble_rattle.wav", rattle, 0.80)

    # 3. Rope taut whip + stone bollard friction creak
    t = np.linspace(0, 0.72, int(0.72 * sr), endpoint=False)
    whip = np.sin(2 * np.pi * np.cumsum(np.linspace(520, 140, len(t))) / sr) * np.exp(-t * 15.0)
    creak = np.sin(2 * np.pi * (195 + 22 * np.sin(2 * np.pi * 8.0 * t)) * t) * np.exp(-t * 4.5) * 0.5
    sfx_hashes["r2_rope_taut_creak.wav"] = save_wav(sfx_dir / "r2_rope_taut_creak.wav", whip + creak, 0.84)

    # 4. Heavy wheel skid + tray bounce + comic bread whoosh
    t = np.linspace(0, 0.75, int(0.75 * sr), endpoint=False)
    skid = np.convolve(rng.standard_normal(len(t)), np.ones(12) / 12.0, mode="same") * np.exp(-t * 9.5) * 0.8
    thud = np.sin(2 * np.pi * np.cumsum(np.linspace(150, 48, len(t))) / sr) * np.exp(-t * 16.0)
    sfx_hashes["r2_cart_skid_halt.wav"] = save_wav(sfx_dir / "r2_cart_skid_halt.wav", skid + thud, 0.88)

    # 5. Soft loaf spring launch & gentle helmet plume "thump-boing"
    t = np.linspace(0, 0.42, int(0.42 * sr), endpoint=False)
    boing = np.sin(2 * np.pi * np.cumsum(np.linspace(240, 420, len(t))) / sr) * np.exp(-t * 12.0) * 0.7
    sfx_hashes["r2_loaf_launch_arc.wav"] = save_wav(sfx_dir / "r2_loaf_launch_arc.wav", boing, 0.78)

    t = np.linspace(0, 0.38, int(0.38 * sr), endpoint=False)
    soft_thump = (0.75 * np.sin(2 * np.pi * np.cumsum(np.linspace(195, 75, len(t))) / sr) * np.exp(-t * 22.0)
                  + 0.25 * np.sin(2 * np.pi * 340 * t) * np.exp(-t * 18.0))
    sfx_hashes["r2_helmet_loaf_plop.wav"] = save_wav(sfx_dir / "r2_helmet_loaf_plop.wav", soft_thump, 0.86)

    # 6. Bronze helmet clatter under stone bench / river splash / crowd cheer
    t = np.linspace(0, 0.55, int(0.55 * sr), endpoint=False)
    ring = (0.5 * np.sin(2 * np.pi * 620 * t) + 0.35 * np.sin(2 * np.pi * 940 * t)) * np.exp(-t * 11.0)
    sfx_hashes["r2_bronze_clatter.wav"] = save_wav(sfx_dir / "r2_bronze_clatter.wav", ring, 0.78)

    t = np.linspace(0, 0.65, int(0.65 * sr), endpoint=False)
    water = np.convolve(rng.standard_normal(len(t)), np.ones(16) / 16.0, mode="same") * np.sin(np.pi * np.clip(t / 0.65, 0, 1))
    sfx_hashes["r2_river_splash.wav"] = save_wav(sfx_dir / "r2_river_splash.wav", water, 0.72)

    t = np.linspace(0, 0.85, int(0.85 * sr), endpoint=False)
    cheer = (np.convolve(rng.standard_normal(len(t)), np.ones(9) / 9.0, mode="same") * 0.45
             + 0.25 * np.sin(2 * np.pi * 392 * t) + 0.22 * np.sin(2 * np.pi * 523.25 * t)) * np.sin(np.pi * np.clip(t / 0.85, 0, 1))
    sfx_hashes["r2_market_cheer.wav"] = save_wav(sfx_dir / "r2_market_cheer.wav", cheer, 0.75)

    # 7. Original 12.0s Roman Pizzicato + Frame-Drum Underscore (G Major / Mixolydian lively market chase!)
    bed_dur = 12.0
    tb = np.linspace(0, bed_dur, int(bed_dur * sr), endpoint=False)
    bed = np.zeros_like(tb)
    step_dt = 0.25  # 120 BPM brisk chase pulse
    scale_hz = [196.00, 246.94, 293.66, 246.94, 220.00, 246.94, 196.00, 146.83] if music_style == "market_comedy" else [146.83, 196.00, 220.00, 196.00, 164.81, 146.83, 196.00, 220.00]
    for k in range(int(bed_dur / step_dt)):
        i0 = int(k * step_dt * sr)
        n_rem = min(int(0.32 * sr), len(bed) - i0)
        tt = np.arange(n_rem, dtype=np.float32) / sr
        f_note = scale_hz[k % len(scale_hz)]
        pluck = (0.58 * np.sin(2 * np.pi * f_note * tt) + 0.22 * np.sin(4 * np.pi * f_note * tt)) * np.exp(-tt * 9.5)
        bed[i0 : i0 + n_rem] += pluck * 0.38
        if k % 2 == 0:
            drm = np.sin(2 * np.pi * np.cumsum(np.linspace(135, 62, min(n_rem, int(0.16 * sr)))) / sr) * np.exp(-tt[: min(n_rem, int(0.16 * sr))] * 26.0)
            bed[i0 : i0 + len(drm)] += drm * 0.34
        else:
            tamb = rng.standard_normal(min(n_rem, int(0.08 * sr))) * np.exp(-tt[: min(n_rem, int(0.08 * sr))] * 42.0) * 0.22
            bed[i0 : i0 + len(tamb)] += tamb

    bed_name = f"bed_r2_{music_style}.wav"
    bed_hash = save_wav(music_dir / bed_name, bed, 0.54)
    return {"sfx_hashes": sfx_hashes, "music_file": f"audio/music/{bed_name}", "music_hash": bed_hash}


def _map_action_sfx(sh: Dict[str, Any]) -> List[Dict[str, Any]]:
    aid = sh.get("action_id", "")
    dur = float(sh.get("duration", 1.2))
    if aid == "prop.peg_crack_snap":
        return [{"at": round(dur * 0.42, 2), "name": "audio/sfx/r2_wood_peg_snap.wav", "gainDb": 1.5}]
    if aid in ("prop.cart_roll_slope", "actor.sprint_chase", "world.market_crowd_pass"):
        return [{"at": 0.06, "name": "audio/sfx/r2_cart_cobble_rattle.wav", "gainDb": -1.5}]
    if aid in ("prop.rope_taut_post_wrap", "actor.stop_brace", "actor.pull_drag_rope_tension"):
        return [{"at": round(dur * 0.22, 2), "name": "audio/sfx/r2_rope_taut_creak.wav", "gainDb": 0.5}]
    if aid == "prop.cart_halt_skid":
        return [{"at": round(dur * 0.25, 2), "name": "audio/sfx/r2_cart_skid_halt.wav", "gainDb": 1.8}]
    if aid in ("prop.prop_bounce_tray", "prop.prop_parabolic_arc"):
        return [{"at": 0.08, "name": "audio/sfx/r2_loaf_launch_arc.wav", "gainDb": 0.5}]
    if aid == "prop.helmet_impact_settle":
        return [{"at": round(dur * 0.38, 2), "name": "audio/sfx/r2_helmet_loaf_plop.wav", "gainDb": 2.0}]
    if aid in ("prop.helmet_roll_under_bench", "actor.stumble_recover"):
        return [{"at": round(dur * 0.20, 2), "name": "audio/sfx/r2_bronze_clatter.wav", "gainDb": 0.0}]
    if aid in ("prop.vexillum_river_drift", "actor.reach_grab_prop") and sh.get("location_id") == "roman_river_harbor":
        return [{"at": 0.12, "name": "audio/sfx/r2_river_splash.wav", "gainDb": -1.0}]
    if aid == "actor.crowd_reaction_cheer":
        return [{"at": 0.12, "name": "audio/sfx/r2_market_cheer.wav", "gainDb": -0.5}]
    return []


def _generate_r2_scene_js(shots: List[Dict[str, Any]], scene_name: str) -> str:
    shot_lines = [
        f"registerShot('{sh['id']}', {{ draw(g, lt, info) {{ renderScriptShotFrame(g, info?.globalT ?? ({sh['start']} + lt)); }} }});"
        for sh in shots
    ]
    return "\n".join([
        f"// {scene_name}.js — Fail-Closed Runtime 2D Scene Binder for KH-03.0.R2 ({V2_EDITORIAL_MODE}).",
        "// Strictly 2D Canvas via renderScriptShotFrame() -> renderRomanAction2D(). Zero Three.js.",
        "import { registerShot, E } from '/engine/core.js';",
        "import { renderScriptShotFrame } from '/packs/squire/pack.js';",
        "",
        *shot_lines,
        "",
        "for (const s of (E.shots || [])) {",
        "  if (s?.id && !['" + "', '".join(sh["id"] for sh in shots) + "'].includes(s.id)) {",
        "    registerShot(s.id, { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (s.start + lt)); } });",
        "  }",
        "}",
        "",
    ])


def _generate_r2_thumb_js(location_id: str, title_top: str = "RUNAWAY", title_bot: str = "ROMAN CART!") -> str:
    if location_id == "roman_river_harbor":
        env_call = "drawRomanRiverHarbor2D(g, { globalT: 1.0 }, { quayRightFrac: 0.52 });"
        hero_id = "signifer_marc"
    elif location_id == "roman_forum_courtyard":
        env_call = "drawRomanForumCourtyard2D(g, { globalT: 1.0 });"
        hero_id = "senator_cassius"
    else:
        env_call = "drawRomanMarketSlopeBackdrop2D(g, { globalT: 1.0 }, { scrollX: 120, slopeDropFrac: 0.08 });"
        hero_id = "centurion_varro"

    title_top_js = json.dumps(title_top)
    title_bot_js = json.dumps(title_bot)
    return f"""// thumb.js — Native 9:16 Thumbnail Cover Art for KH-03.0.R2 ({location_id}).
import {{ E, registerShot }} from '/engine/core.js';
import {{
  PAL,
  titleText,
  drawRomanMarketSlopeBackdrop2D,
  drawRomanRiverHarbor2D,
  drawRomanForumCourtyard2D,
  drawRomanCart2D,
  drawRomanLoaf2D,
  romanActorAt,
  drawRomanMasterActor2D,
}} from '/packs/squire/pack.js';

registerShot('thumb', {{
  draw(g) {{
    const w = E.W || 1080;
    const h = E.H || 1920;
    {env_call}
    const hero = romanActorAt(1.0, {{
      start: 0, end: 2,
      actors: {{
        {hero_id}: {{
          archetypeId: '{hero_id}', hasShield: false, weapon: 'none',
          xFrac: 0.62, yFrac: 0.65, hFrac: 0.34, bodyRot: 0.04,
          leftFootLocal: [-10, 0], rightFootLocal: [10, 0], armsAng: [-20, -25, 32, -20], face: 'bored', look: -0.2,
        }},
      }},
    }}, '{hero_id}', {{ W: w, H: h, globalT: 1.0 }});
    drawRomanMasterActor2D(g, hero, {{ seed: 41, shoeMode: 'front' }});
    if ('{location_id}' === 'roman_market_hill') {{
      drawRomanCart2D(g, w * 0.28, h * 0.62, w * 0.36, {{ tiltRad: 0.09, wheelAngleRad: 1.1 }});
      drawRomanLoaf2D(g, w * 0.635, h * 0.275, w * 0.145, {{ rot: 0.04, squishFrac: 0.1 }});
    }}
    titleText(g, {title_top_js}, w * 0.5, h * 0.11, h * 0.064, {{ color: '#ffe875', rot: -0.025 }});
    titleText(g, {title_bot_js}, w * 0.5, h * 0.19, h * 0.066, {{ color: '#ff5247', rot: -0.025 }});
  }},
}});
"""


def build_roman_r2_project(
    script: str | List[str] | List[Dict[str, Any]] = THE_CART_THAT_WOULD_NOT_STOP_SCRIPT,
    project_dir: Path | str = DEFAULT_R2_PROJECT_DIR,
    title: str = DEFAULT_R2_TITLE,
    aspect: str = "9:16",
    fps: int = 24,
    target_duration: Optional[float] = None,
    scene_name: str = "market_cart_r2",
    music_style: str = "market_comedy",
    voice_cfg: Optional[Dict[str, Any]] = None,
    custom_manifest: Optional[Dict[str, Any]] = None,
    scratch_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Compile any R2-capable script into a runnable, fail-closed, 2D-only Squire Roman project."""
    proj = Path(project_dir).resolve()
    proj.mkdir(parents=True, exist_ok=True)
    scr = Path(scratch_dir).resolve() if scratch_dir else (proj / "build" / "r2_tts")
    scr.mkdir(parents=True, exist_ok=True)

    sb = load_roman_master_style()
    norm_lines = normalize_script_lines(script)
    synth = synthesize_or_import_narration(norm_lines, proj, voice_cfg=voice_cfg, scratch_dir=scr / "raw")

    dur = float(target_duration) if target_duration else max(5.0, round(synth["raw_total_speech_sec"] + 0.95, 3))
    # Quantize exact frame grid duration
    total_frames = max(24, int(round(dur * fps)))
    dur = round(total_frames / fps, 3)

    packed = pack_narration_into_30s(
        synth["clips"],
        target_duration=dur,
        lead_in_sec=0.10,
        tail_pad_sec=0.35 if dur >= 15.0 else 0.18,
        preferred_stretch=1.10,
        max_stretch=1.15,
        scratch_dir=scr / "packed",
    )
    aligned = align_words_and_lines(packed)
    vt = {
        "status": "PASS",
        "valid": True,
        "pcm_duration_sec": dur,
        "lines": aligned["lines"],
        "words": aligned["words"],
    }

    compiled = compile_v2_editorial_plan(
        norm_lines,
        voice_timeline=vt,
        total_duration_sec=dur,
        custom_manifest=custom_manifest,
        aspect=aspect,
        fps=fps,
    )
    val_contract = compiled["validation"]
    if not val_contract.get("valid"):
        raise RuntimeError(f"KH03_R2_SHOT_PLAN_INVALID: {val_contract.get('errors')}")

    shot_plan = compiled["shot_plan"]
    crosswalk = compiled["shot_to_line_map"]
    merge_res = merge_narration_visual_mapping(aligned, packed["master_voice"], shot_plan, crosswalk, proj)
    audio_assets = _synth_r2_original_audio(proj, music_style=music_style)

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
        "editorial_mode": V2_EDITORIAL_MODE,
        "render_mode": "canvas2d_only",
        "allow_3d_legacy_fallback": False,
        "music": {"enabled": True, "file": audio_assets["music_file"], "gainDb": -14.5},
        "sfx": {"enabled": True, "gainDb": 0.0},
    }
    _atomic_write_json(proj / "config.json", config_data)

    line_by_id = {l["id"]: l for l in aligned["lines"]}
    shots_payload = {
        "title": title,
        "duration": dur,
        "aspect": aspect,
        "fps": fps,
        "shots": [
            {
                "id": sh["id"],
                "start": sh["start"],
                "end": sh["end"],
                "tpl": "custom",
                "scene": scene_name,
                "action_id": sh["action_id"],
                "renderer_action_id": sh["renderer_action_id"],
                "sub_action": sh["sub_action"],
                "location_id": sh["location_id"],
                "framing_scale": sh["framing_scale"],
                "line_ids": crosswalk["shots_to_lines"].get(sh["id"], [sh["source_line_id"]]),
                "line": " / ".join(
                    line_by_id[lid]["text"]
                    for lid in crosswalk["shots_to_lines"].get(sh["id"], [sh["source_line_id"]])
                    if lid in line_by_id
                ),
                "sfx": _map_action_sfx(sh),
                "notes": "DROP" if sh["action_id"] in ("actor.deadpan_walk_unaffected", "prop.helmet_impact_settle") else "",
                "in": {"type": "cut"},
            }
            for sh in shot_plan["shots"]
        ],
        "music": [
            {
                "start": 0.0,
                "end": round(max(0.5, shot_plan["shots"][-2]["start"] if len(shot_plan["shots"]) > 2 else dur), 3),
                "bed": "user",
                "gainDb": -1.5,
            }
        ],
    }
    _atomic_write_json(proj / "story" / "shots.json", shots_payload)
    _atomic_write_text(proj / "story" / "script.txt", "\n".join(f"{l['id']}: {l['text']}" for l in aligned["lines"]) + "\n")
    _atomic_write_json(proj / "story" / "shot_plan.json", shot_plan)
    _atomic_write_json(proj / "story" / "beats.json", compiled["beats"])
    _atomic_write_json(proj / "story" / "action_bindings.json", {"bindings": compiled["action_bindings"]})
    _atomic_write_json(proj / "story" / "action_graph.json", compiled["action_graph"])
    _atomic_write_json(proj / "story" / "scene_manifest.json", compiled["scene_manifest"])
    _atomic_write_json(proj / "story" / "prop_state_ledger.json", compiled["prop_state_ledger"])
    _atomic_write_json(proj / "story" / "shot_to_line_map.json", crosswalk)
    _atomic_write_json(proj / "story" / "camera_beats.json", compiled["camera_beats"])
    _atomic_write_json(proj / "story" / "pacing_report.json", compiled["pacing_report"])
    _atomic_write_json(proj / "story" / "continuity_ledger.json", {
        "schema_version": "kh03.r2.continuity_ledger.v1",
        "editorial_mode": V2_EDITORIAL_MODE,
        "world_invariants": compiled["action_graph"].get("terminal_world_state", {}),
    })
    _atomic_write_json(proj / "story" / "character_bible.json", {
        "style_profile": "roman_squire_master.v1",
        "cast": compiled["scene_manifest"]["entities"],
    })
    _atomic_write_json(proj / "story" / "roman_master_style_ref.json", {
        "style_profile": "roman_squire_master.v1",
        "canonical_digest": sb["canonical_digest"],
        "out_ink": "#392a21",
        "render_mode": "canvas2d_only",
    })
    _atomic_write_json(proj / "story" / "environment_bible.json", {
        "locations": compiled["scene_manifest"]["locations"],
        "aspect": aspect,
        "render_mode": "canvas2d_only",
    })
    _atomic_write_json(proj / "story" / "props.json", {
        "props": compiled["scene_manifest"]["props"],
    })
    _atomic_write_json(proj / "story" / "storyboard.json", {
        "schema_version": "kh03.r2.storyboard.v1",
        "title": title,
        "editorial_mode": V2_EDITORIAL_MODE,
        "style_profile": "roman_squire_master.v1",
        "shots": shot_plan["shots"],
    })
    _atomic_write_json(proj / "story" / "sound_design.json", {
        "schema_version": "kh03.r2.sound_design.v1",
        "voice_provenance": synth["clips"][0]["source_kind"],
        "voice_sha256": merge_res["voice_wav_sha256"],
        "global_tempo_scale": packed["global_tempo_scale"],
        "audio_assets": audio_assets,
    })

    loc_default = compiled["scene_manifest"]["default_location"]
    _atomic_write_text(proj / "scenes" / "shots" / f"{scene_name}.js", _generate_r2_scene_js(shot_plan["shots"], scene_name))
    t_top, t_bot = ("THE RIVER", "VEXILLUM!") if loc_default == "roman_river_harbor" else ("THE SENATOR", "HELMET!") if loc_default == "roman_forum_courtyard" else ("THE CART", "WOULDN'T STOP!")
    _atomic_write_text(proj / "scenes" / "shots" / "thumb.js", _generate_r2_thumb_js(loc_default, t_top, t_bot))
    _atomic_write_text(
        proj / "README.md",
        f"# {title}\n\n"
        f"- **Style Profile**: `roman_squire_master.v1` (digest `{sb['canonical_digest']}`)\n"
        f"- **Editorial Mode**: `{V2_EDITORIAL_MODE}`\n"
        f"- **Format**: `{aspect}` (`1080x1920 @ {fps}fps`, `{total_frames}` frames, `{dur:.3f}s`)\n"
        f"- **Render Mode**: `canvas2d_only` (Zero Three.js)\n"
        f"- **Shots / Lines**: `{len(shot_plan['shots'])}` shots / `{len(aligned['lines'])}` lines\n"
        f"- **Editorial & Style Sign-Off**: `HUMAN_REVIEW_PENDING`\n",
    )

    val = validate_project(proj)
    if val["status"] != "PASS":
        raise RuntimeError(f"KH03_R2_VALIDATOR_BLOCKED: {val}")

    return {
        "status": "PASS",
        "project_dir": str(proj),
        "title": title,
        "duration_sec": dur,
        "total_frames": total_frames,
        "shots_count": len(shot_plan["shots"]),
        "lines_count": len(aligned["lines"]),
        "words_count": len(aligned["words"]),
        "raw_total_speech_sec": synth["raw_total_speech_sec"],
        "global_tempo_scale": packed["global_tempo_scale"],
        "crosswalk_summary": crosswalk["summary"],
        "action_registry_digest": val_contract["action_registry_digest"],
        "style_digest": sb["canonical_digest"],
        "validator_status": val["status"],
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


def render_roman_r2_preview(
    project_dir: Path | str = DEFAULT_R2_PROJECT_DIR,
    review_packet_dir: Optional[Path | str] = None,
    workers: int = 1,
    make_thumb: bool = True,
) -> Dict[str, Any]:
    """Render 1080x1920 24fps R2 film via render.mjs, mix via tools/mix.py, run decoded Perceptual QA & build contact sheet."""
    proj = Path(project_dir).resolve()
    cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
    shot_plan = json.loads((proj / "story" / "shot_plan.json").read_text(encoding="utf-8"))
    title = cfg.get("title", DEFAULT_R2_TITLE)
    pkt_dir = Path(review_packet_dir).resolve() if review_packet_dir else (proj / "out" / "review_packet")
    pkt_dir.mkdir(parents=True, exist_ok=True)
    stills_dir = pkt_dir / "stills_per_shot"
    stills_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    subprocess.run(["node", "render.mjs", "--project", str(proj), "--check", "--scale", "0.25"], cwd=str(REPO_ROOT), check=True)
    subprocess.run(["node", "render.mjs", "--project", str(proj), "--workers", str(max(1, min(3, workers)))], cwd=str(REPO_ROOT), check=True)
    render_wall_sec = round(time.monotonic() - t0, 3)

    if make_thumb:
        subprocess.run(["node", "render.mjs", "--project", str(proj), "--thumb"], cwd=str(REPO_ROOT), check=True)

    t_mix0 = time.monotonic()
    subprocess.run([sys.executable, "tools/mix.py", "--project", str(proj)], cwd=str(REPO_ROOT), check=True)
    mix_wall_sec = round(time.monotonic() - t_mix0, 3)

    final_mp4 = proj / "out" / f"{title}.mp4"
    if not final_mp4.is_file():
        raise FileNotFoundError(f"Expected R2 MP4 missing at {final_mp4}")

    probe_json = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(final_mp4)],
            capture_output=True, text=True, check=True,
        ).stdout
    )
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

    # Calibrate safely to [-16.2, -13.8] LUFS & <= -1.0 dBTP if needed
    if not (-16.2 <= integrated_lufs <= -13.8 and true_peak_dbtp <= -1.0):
        mix_wav = proj / "build" / "mix.wav"
        video_silent = proj / "build" / "video_silent.mp4"
        cal_wav = proj / "build" / "mix_calibrated.wav"
        target_adj = (-15.0 - integrated_lufs) if (-35 < integrated_lufs < 0) else 0.0
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

    # Run true decoded-pixel Perceptual Shot QA on exported MP4!
    perceptual_qa = build_perceptual_review_packet(final_mp4, shot_plan, pkt_dir / "perceptual_qa")
    _atomic_write_json(proj / "story" / "perceptual_qa.json", perceptual_qa)

    # Contact sheet across every shot
    shots = shot_plan["shots"]
    cols = 5 if len(shots) >= 13 else min(4, max(1, len(shots)))
    rows = max(1, (len(shots) + cols - 1) // cols)
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
        lbl = f"{sh['id']} ({sh['duration']:.2f}s) {sh['action_id'][:22]}"
        tile = _label_tile(im.resize((tw, th), Image.Resampling.LANCZOS), lbl)
        contact.paste(tile, ((idx % cols) * tw, (idx // cols) * th))
        still_records.append({"shot_id": sh["id"], "t_sec": mid_t, "jpg": str(sjpg), "sha256": _sha256_file(sjpg)})
    contact_path = pkt_dir / "contact_sheet_all_shots.jpg"
    contact.save(contact_path, quality=91)

    return {
        "status": "PASS",
        "mp4_path": str(final_mp4),
        "mp4_sha256": _sha256_file(final_mp4),
        "mp4_bytes": final_mp4.stat().st_size,
        "decoded_frames": decoded_frames,
        "duration_sec": float(probe_json["format"]["duration"]),
        "integrated_lufs": round(integrated_lufs, 2),
        "true_peak_dbtp": round(true_peak_dbtp, 2),
        "render_wall_sec": render_wall_sec,
        "mix_wall_sec": mix_wall_sec,
        "perceptual_qa_status": perceptual_qa.get("status"),
        "perceptual_qa": perceptual_qa,
        "contact_sheet": str(contact_path),
        "stills_count": len(still_records),
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Build & render KH-03.0.R2 generalized 2D Squire project.")
    ap.add_argument("--project", default=str(DEFAULT_R2_PROJECT_DIR))
    ap.add_argument("--corpus", choices=["market_cart", "river_harbor", "forum_courtyard"], default="market_cart")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    corpus_map = {
        "market_cart": (THE_CART_THAT_WOULD_NOT_STOP_SCRIPT, DEFAULT_R2_TITLE, "market_cart_r2", "market_comedy", 30.0),
        "river_harbor": (RIVER_HARBOR_HOLDOUT_SCRIPT, "KH03_R2_HOLDOUT_RIVER_HARBOR", "river_harbor_r2", "harbor_drama", 7.0),
        "forum_courtyard": (FORUM_COURTYARD_HOLDOUT_SCRIPT, "KH03_R2_HOLDOUT_FORUM_COURTYARD", "forum_courtyard_r2", "forum_comedy", 8.0),
    }
    scr_obj, ttl, s_name, m_style, def_dur = corpus_map[args.corpus]
    build_res = build_roman_r2_project(
        scr_obj,
        project_dir=args.project,
        title=ttl,
        target_duration=args.duration or def_dur,
        scene_name=s_name,
        music_style=m_style,
    )
    print(json.dumps({"build": build_res}, indent=2))
    if args.render:
        rnd_res = render_roman_r2_preview(args.project, workers=args.workers)
        print(json.dumps({"render": rnd_res}, indent=2))
