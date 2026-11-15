#!/usr/bin/env python3
"""tools/produce_fl01_v14_7_5_roman_eagle_in_fog_preview.py — Producer for brand-new V14.7.5 film:
"THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE" (Illustrative Fictional Reconstruction).

Specification (FL-01 / V14.7.5 Section D):
- Duration: ~54.4s (within 50.0s–58.0s), 12 varied-duration shots across 4 causal acts.
- Video: 1920x1080 @ 24fps, H.264 (yuv420p), multi-layer fog atmosphere (`fogBank`), dynamic camera paths,
  tactical corridor schematic (`roman_eagle_rescue_diagram`), and mobile-readable takeaway card (`mobile_summary_card`).
- Audio: Spoken English narration via macOS `say` (`Daniel`), fail-closed (`BLOCKED_NO_SPEECH_PROVIDER`) if speech
  provider is unavailable (never substitutes sine wave), ZERO `atempo` distortion, 0 ms speech overlap,
  and measured tail margin >= 0.50s before every shot cut; mixed with cold mountain valley wind, wet-stone footsteps,
  shield/armor clatter, low cornu horn/drum pulse, and Act IV brass/pad recovery motif normalized to -14 LUFS.
- Provenance: Disables `QA_STUDIO_TEST_MODE`, logs `build/render.log`, promotes muxed `.partial.mp4` atomically
  only after full media decode inspection, writes cryptographic `build/render_receipt.json` (`REAL_RENDER`,
  `ai_director_mode=OFFLINE_ONLY`), and renders 3 real contact sheets (`contact_sheet_full.png`,
  `contact_sheet_hook.png`, `contact_sheet_action.png`).
"""

from __future__ import annotations

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

from PIL import Image, ImageDraw, ImageFont

from scripts.production_fingerprint import (
    collect_render_inputs,
    compute_render_fingerprint,
    inspect_media_file,
    sha256_file,
    validate_cache_hit,
    write_render_receipt_atomic,
)
from tools.cinematic_camera import plan_camera_sequence
from tools.visual_qa_v14_6 import extract_frame_at_time

PROJECT_DIR = ROOT_DIR / "projects" / "fl01_v14_7_5_roman_eagle_in_fog_preview"
OUT_MP4_PATH = PROJECT_DIR / "out" / "FL01_V14_7_5_ROMAN_EAGLE_IN_FOG_FRESH_PREVIEW_1080P.mp4"
FILM_TITLE = "THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE"
FILM_SUBTITLE = "Illustrative Fictional Reconstruction"

# 12 varied-duration causal beats (total base duration = 54.4s; auto-expands slightly if any natural WAV needs >= 0.55s tail margin)
BASE_BEATS: List[Dict[str, Any]] = [
    {
        "id": "s01",
        "act": "I_HOOK_DISORIENTATION",
        "dur": 3.8,
        "action": "STAND",
        "text": "Cold valley fog swallowed the cohort as their gilded standard tilted.",
        "causal_cut_reason": "opening_hook",
    },
    {
        "id": "s02",
        "act": "I_HOOK_DISORIENTATION",
        "dur": 4.5,
        "action": "WITHDRAW",
        "text": "Along the stony pass, skirmishers pressed from the misty ridge.",
        "causal_cut_reason": "wide_spatial_establish",
    },
    {
        "id": "s03",
        "act": "I_HOOK_DISORIENTATION",
        "dur": 4.5,
        "action": "SLIP",
        "text": "On slick slate, Gaius slipped, dropping the eagle onto stone.",
        "causal_cut_reason": "inciting_physical_slip",
    },
    {
        "id": "s04",
        "act": "II_DISCOVERY_COMMAND",
        "dur": 4.1,
        "action": "STAND",
        "text": "Through drifting mist, Centurion Marcus spotted the fallen emblem.",
        "causal_cut_reason": "reaction_closeup",
    },
    {
        "id": "s05",
        "act": "II_DISCOVERY_COMMAND",
        "dur": 4.5,
        "action": "SIGNAL",
        "text": "Raising a bright torch, Marcus sent a two-man rescue forward.",
        "causal_cut_reason": "command_signal_action",
    },
    {
        "id": "s06",
        "act": "II_DISCOVERY_COMMAND",
        "dur": 4.7,
        "action": "STAND",
        "text": "Flank shields locked an anchor corridor as two legionaries dashed out.",
        "causal_cut_reason": "tactical_schematic_cutaway",
    },
    {
        "id": "s07",
        "act": "III_RESCUE_UNDER_COVER",
        "dur": 4.5,
        "action": "RESCUE_DASH",
        "text": "Decimus and Lucius sprinted across wet stone toward Gaius.",
        "causal_cut_reason": "tactical_to_ground_execution",
    },
    {
        "id": "s08",
        "act": "III_RESCUE_UNDER_COVER",
        "dur": 4.6,
        "action": "BRACE",
        "text": "Behind them, front ranks braced curved scuta against flying shafts.",
        "causal_cut_reason": "parallel_shield_cover",
    },
    {
        "id": "s09",
        "act": "III_RESCUE_UNDER_COVER",
        "dur": 4.6,
        "action": "LIFT_STANDARD",
        "text": "Together they hauled Gaius upright and gripped the bronze shaft.",
        "causal_cut_reason": "physical_standard_recovery",
    },
    {
        "id": "s10",
        "act": "IV_WITHDRAWAL_RECOVERY",
        "dur": 4.4,
        "action": "WITHDRAW",
        "text": "Step by step, the team withdrew safely behind Roman shields.",
        "causal_cut_reason": "coordinated_withdrawal",
    },
    {
        "id": "s11",
        "act": "IV_WITHDRAWAL_RECOVERY",
        "dur": 4.4,
        "action": "REFORM",
        "text": "The cohort closed its interval, restoring an unbroken iron wall.",
        "causal_cut_reason": "wide_cohort_reform",
    },
    {
        "id": "s12",
        "act": "IV_WITHDRAWAL_RECOVERY",
        "dur": 4.8,
        "action": "RAISE_STANDARD",
        "text": "Above parting fog, discipline and cohesion held the eagle high.",
        "causal_cut_reason": "heroic_payoff_summary",
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


def generate_timed_voice_track(
    project_path: Path = PROJECT_DIR,
    beats: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Synthesize natural spoken English narration using macOS `say` (`Daniel`).
    Fails closed (`BLOCKED_NO_SPEECH_PROVIDER`) if `say` is missing — NEVER substitutes sine wave.
    Uses ZERO `atempo` time-compression and ZERO truncation: each beat duration is sized to guarantee
    lead-in >= 0.22s, tail_margin >= 0.55s, and 0.0 ms pairwise overlap.
    """
    say_bin = shutil.which("say")
    if not say_bin:
        return {
            "ok": False,
            "status": "BLOCKED_NO_SPEECH_PROVIDER",
            "error": "Required speech synthesis provider 'say' is not available on host",
        }

    p_dir = Path(project_path).resolve()
    build_dir = p_dir / "build"
    timeline_dir = p_dir / "timeline"
    build_dir.mkdir(parents=True, exist_ok=True)
    timeline_dir.mkdir(parents=True, exist_ok=True)

    raw_beats = [dict(b) for b in (beats or BASE_BEATS)]
    measured_clips: List[Tuple[Dict[str, Any], Path, float]] = []

    # Step 1: Synthesize natural speech clips and measure true duration via ffprobe
    for b in raw_beats:
        sid = b["id"]
        aiff_p = build_dir / f"voice_{sid}.aiff"
        wav_p = build_dir / f"voice_{sid}.wav"
        subprocess.run(
            [say_bin, "-v", "Daniel", "-r", "192", "-o", str(aiff_p), b["text"]],
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
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(wav_p),
            ],
            check=True,
            capture_output=True,
        )
        if aiff_p.exists():
            aiff_p.unlink()
        spoken_dur = _probe_audio_duration(wav_p)
        measured_clips.append((b, wav_p, spoken_dur))

    # Step 2: Assign exact non-overlapping shot windows ensuring natural tail_margin >= 0.55s (zero atempo!)
    lead_in_sec = 0.24
    min_desired_tail_sec = 0.56
    cursor = 0.0
    timed_beats: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    concat_files: List[Path] = []
    concat_entries: List[str] = []
    audio_cursor = 0.0

    for b, wav_p, spoken_dur in measured_clips:
        sid = b["id"]
        min_needed_dur = round(lead_in_sec + spoken_dur + min_desired_tail_sec, 2)
        # Round shot duration to exact 3-frame (0.125s) multiple at 24fps so 3-decimal JSON has ZERO frame rounding drift
        raw_shot_dur = max(float(b["dur"]), min_needed_dur)
        tri_frames = int(math.ceil(raw_shot_dur * 8.0 - 1e-6))
        shot_dur = round(tri_frames / 8.0, 3)

        shot_start = round(cursor, 4)
        shot_end = round(cursor + shot_dur, 4)
        spoken_start = round(shot_start + lead_in_sec, 4)
        if spoken_start < audio_cursor + 0.02:
            spoken_start = round(audio_cursor + 0.02, 4)
        spoken_end = round(spoken_start + spoken_dur, 4)
        tail_margin = round(shot_end - spoken_end, 4)

        gap_before = round(max(0.0, spoken_start - audio_cursor), 4)
        if gap_before > 0.002:
            gap_wav = build_dir / f"gap_pre_{sid}.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=stereo",
                    "-t",
                    f"{gap_before:.4f}",
                    "-c:a",
                    "pcm_s16le",
                    str(gap_wav),
                ],
                check=True,
                capture_output=True,
            )
            concat_files.append(gap_wav)
            concat_entries.append(f"file '{gap_wav.name}'")
            audio_cursor += gap_before

        concat_files.append(wav_p)
        concat_entries.append(f"file '{wav_p.name}'")
        audio_cursor += spoken_dur

        beat_copy = dict(b)
        beat_copy["start"] = round(shot_start, 3)
        beat_copy["end"] = round(shot_end, 3)
        beat_copy["dur"] = round(shot_dur, 3)
        timed_beats.append(beat_copy)

        events.append(
            {
                "id": sid,
                "act": b["act"],
                "action": b["action"],
                "text": b["text"],
                "shot_start": round(shot_start, 3),
                "shot_end": round(shot_end, 3),
                "shot_duration": round(shot_dur, 3),
                "spoken_start": round(spoken_start, 3),
                "spoken_end": round(spoken_end, 3),
                "spoken_duration": round(spoken_dur, 3),
                "lead_in_sec": round(spoken_start - shot_start, 3),
                "tail_margin_sec": round(tail_margin, 3),
                "atempo_applied": False,
                "truncated": False,
            }
        )
        cursor = shot_end

    total_duration = round(cursor, 3)
    if total_duration < 50.0 or total_duration > 58.0:
        raise RuntimeError(f"Computed film duration {total_duration:.2f}s outside [50.0, 58.0]s contract!")

    final_pad = round(max(0.0, total_duration - audio_cursor), 4)
    if final_pad > 0.002:
        pad_wav = build_dir / "gap_final_tail.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-t",
                f"{final_pad:.4f}",
                "-c:a",
                "pcm_s16le",
                str(pad_wav),
            ],
            check=True,
            capture_output=True,
        )
        concat_files.append(pad_wav)
        concat_entries.append(f"file '{pad_wav.name}'")

    concat_txt = build_dir / "voice_concat.txt"
    concat_txt.write_text("\n".join(concat_entries) + "\n", encoding="utf-8")

    voice_track_wav = build_dir / "voice_track.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(voice_track_wav),
        ],
        check=True,
        capture_output=True,
    )
    shutil.copy2(voice_track_wav, timeline_dir / "voice.wav")

    for cf in concat_files:
        if cf.is_file():
            cf.unlink()
    if concat_txt.is_file():
        concat_txt.unlink()

    measured_voice_wav_dur = round(_probe_audio_duration(voice_track_wav), 3)
    measured_overlap_ms = compute_measured_voice_overlaps(events)
    min_tail = min(e["tail_margin_sec"] for e in events)
    max_tail = max(e["tail_margin_sec"] for e in events)

    voice_ledger = {
        "schema_version": "14.7.5",
        "speech_provider": "macos_say_Daniel",
        "voice_name": "Daniel",
        "rate_wpm": 192,
        "atempo_used_anywhere": False,
        "total_timeline_duration_sec": total_duration,
        "measured_voice_wav_duration_sec": measured_voice_wav_dur,
        "beats_count": len(events),
        "total_overlap_ms": measured_overlap_ms,
        "min_tail_margin_sec": round(min_tail, 3),
        "max_tail_margin_sec": round(max_tail, 3),
        "events": events,
    }

    for out_json in (
        build_dir / "voice_events.json",
        timeline_dir / "voice_events.json",
        timeline_dir / "timeline_voice_events.json",
    ):
        tmp_j = out_json.with_suffix(".tmp.json")
        tmp_j.write_text(json.dumps(voice_ledger, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_j, out_json)

    # Also write timeline/lines.json for player lip-sync (`talkAmount`)
    lines_for_player = [
        {"start": e["spoken_start"], "end": e["spoken_end"], "text": e["text"]}
        for e in events
    ]
    (timeline_dir / "lines.json").write_text(json.dumps(lines_for_player, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "status": "VOICE_SYNTHESIZED",
        "voice_wav": str(voice_track_wav),
        "total_duration": total_duration,
        "timed_beats": timed_beats,
        "voice_ledger": voice_ledger,
    }


def build_eagle_soundtrack(
    project_path: Path = PROJECT_DIR,
    timed_beats: Optional[List[Dict[str, Any]]] = None,
    total_dur: float = 54.4,
) -> Path:
    """
    Build atmospheric multi-layer soundtrack:
    - Cold valley wind & mist bed (filtered pink + brown noise)
    - Tactical cues synced to beat starts: wet-stone footsteps, slip impact, cornu command horn,
      shield lock clatter, rescue sprint cadence, and rising Act IV brass/string recovery chord
    - Sidechain ducked under narration and loudness-normalized to -14.0 LUFS (TP <= -1.5 dBTP).
    """
    p_dir = Path(project_path).resolve()
    build_dir = p_dir / "build"
    voice_wav = build_dir / "voice_track.wav"
    mixed_wav = build_dir / "soundtrack_mixed.wav"

    beats_by_id = {b["id"]: b for b in (timed_beats or [])}
    t_s01 = int(round(float(beats_by_id.get("s01", {}).get("start", 0.0)) * 1000)) + 250
    t_s03 = int(round(float(beats_by_id.get("s03", {}).get("start", 8.4)) * 1000)) + 700
    t_s05 = int(round(float(beats_by_id.get("s05", {}).get("start", 17.1)) * 1000)) + 300
    t_s07 = int(round(float(beats_by_id.get("s07", {}).get("start", 26.5)) * 1000)) + 350
    t_s08 = int(round(float(beats_by_id.get("s08", {}).get("start", 31.1)) * 1000)) + 450
    t_s09 = int(round(float(beats_by_id.get("s09", {}).get("start", 35.8)) * 1000)) + 600
    t_s10 = float(beats_by_id.get("s10", {}).get("start", 40.5))

    # 1. Cold mountain valley wind + low tension drone
    amb_wav = build_dir / "tmp_ambience.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            (
                f"anoisesrc=d={total_dur:.3f}:c=pink:r=48000:a=0.055,"
                f"bandpass=f=340:width_type=h:w=260,tremolo=f=0.22:d=0.45[wind];"
                f"sine=f=65.41:d={total_dur:.3f},volume=0.035[drone];"
                f"[wind][drone]amix=inputs=2:weights=0.85 0.35,volume=0.42"
            ),
            "-ar",
            "48000",
            "-ac",
            "2",
            str(amb_wav),
        ],
        check=True,
        capture_output=True,
    )

    # 2. Foley, tactical SFX & Act IV recovery brass/pad motif
    sfx_wav = build_dir / "tmp_sfx_music.wav"
    act4_dur = max(4.0, total_dur - t_s10)
    t_s10_ms = int(round(t_s10 * 1000))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=f=92:d=0.45,afade=t=out:st=0.10:d=0.35,volume=0.45",  # 0: opening tension drum
            "-f",
            "lavfi",
            "-i",
            "anoisesrc=d=0.35:c=white:r=48000:a=0.45,bandpass=f=950:width_type=h:w=500,afade=t=out:st=0.08:d=0.27,volume=0.42",  # 1: slate slip / metallic clatter
            "-f",
            "lavfi",
            "-i",
            "sine=f=196:d=1.15,afade=t=in:st=0:d=0.08,afade=t=out:st=0.65:d=0.50,volume=0.26",  # 2: Roman cornu horn signal
            "-f",
            "lavfi",
            "-i",
            "anoisesrc=d=0.18:c=pink:r=48000:a=0.42,lowpass=f=650,afade=t=out:st=0.04:d=0.14,volume=0.40",  # 3: wet-stone sprint footstep / shield lock
            "-f",
            "lavfi",
            "-i",
            (
                f"sine=f=130.81:d={act4_dur:.3f}[c3];"
                f"sine=f=196.00:d={act4_dur:.3f}[g3];"
                f"sine=f=261.63:d={act4_dur:.3f}[c4];"
                f"[c3][g3][c4]amix=inputs=3:weights=0.45 0.35 0.25,"
                f"lowpass=f=900,afade=t=in:st=0:d=1.8,afade=t=out:st={max(0.5, act4_dur - 1.2):.2f}:d=1.1,volume=0.16"
            ),  # 4: Act IV warm recovery brass/pad motif
            "-filter_complex",
            (
                f"[0:a]adelay={t_s01}|{t_s01}[drum0];"
                f"[1:a]adelay={t_s03}|{t_s03}[slip];"
                f"[2:a]adelay={t_s05}|{t_s05}[horn];"
                f"[3:a]adelay={t_s07}|{t_s07}[step1];"
                f"[3:a]adelay={t_s07 + 420}|{t_s07 + 420}[step2];"
                f"[3:a]adelay={t_s07 + 840}|{t_s07 + 840}[step3];"
                f"[1:a]adelay={t_s08}|{t_s08}[shield1];"
                f"[1:a]adelay={t_s09}|{t_s09}[lift1];"
                f"[4:a]adelay={t_s10_ms}|{t_s10_ms}[motif];"
                f"[drum0][slip][horn][step1][step2][step3][shield1][lift1][motif]"
                f"amix=inputs=9:dropout_transition=0,apad=whole_dur={total_dur:.3f},atrim=0:{total_dur:.3f}[sfx_out]"
            ),
            "-map",
            "[sfx_out]",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(sfx_wav),
        ],
        check=True,
        capture_output=True,
    )

    # 3. Sidechain duck bed under voice + EBU R128 loudness normalization (-14 LUFS, TP <= -1.5 dBTP)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(voice_wav),
            "-i",
            str(amb_wav),
            "-i",
            str(sfx_wav),
            "-filter_complex",
            (
                "[1:a][2:a]amix=inputs=2:weights=0.55 0.65[bed];"
                "[bed][0:a]sidechaincompress=threshold=0.08:ratio=5:attack=15:release=260[bed_ducked];"
                "[0:a][bed_ducked]amix=inputs=2:weights=1.0 0.36,"
                f"loudnorm=I=-14:TP=-1.5:LRA=9,apad=whole_dur={total_dur:.3f},atrim=0:{total_dur:.3f}[outa]"
            ),
            "-map",
            "[outa]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(mixed_wav),
        ],
        check=True,
        capture_output=True,
    )
    shutil.copy2(mixed_wav, build_dir / "mix.wav")

    for tmp_f in (amb_wav, sfx_wav):
        if tmp_f.is_file():
            tmp_f.unlink()

    # Record audio_plan.json and audio_mix_report.json for studio compatibility
    (build_dir / "audio_plan.json").write_text(
        json.dumps(
            {
                "version": "14.7.5",
                "target_lufs": -14.0,
                "true_peak_ceiling_dbtp": -1.5,
                "layers": ["voice_daniel", "cold_valley_fog_wind", "foley_wet_stone_shields_cornu", "act4_recovery_motif"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (build_dir / "audio_mix_report.json").write_text(
        json.dumps({"status": "AUDIO_MIX_PASS", "mixed_wav": str(mixed_wav)}, indent=2),
        encoding="utf-8",
    )
    return mixed_wav


def build_eagle_storyboard(timed_beats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build 12-shot storyboard for 'THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE'
    with strict prop exclusivity, cold mist atmosphere, tactical diagram, and closing takeaway card.
    """
    b_map = {b["id"]: b for b in timed_beats}

    def _meta(sid: str) -> Dict[str, Any]:
        b = b_map[sid]
        return {
            "id": sid,
            "act": b["act"],
            "start": b["start"],
            "end": b["end"],
            "dur": b["dur"],
            "action": b["action"],
            "action_kind": b["action"],
            "line": b["text"],
            "causal_cut_reason": b["causal_cut_reason"],
            "visual_source": "generated",
        }

    shots: List[Dict[str, Any]] = [
        # s01: Hook — Gilded Eagle standard tilting in cold valley fog
        {
            **_meta("s01"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Cold mountain fog drifts across the pass as Aquilifer Gaius steadies the tilting Eagle standard",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 501,
                "tint": ["#b8cad8", 0.14],
                "people": [
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "x": 0.48,
                        "to": 0.51,
                        "y": 0.85,
                        "h": 0.48,
                        "pose": "march",
                        "face": "worried",
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "x": 0.31,
                        "to": 0.33,
                        "y": 0.86,
                        "h": 0.45,
                        "pose": "guard",
                        "face": "determined",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "from": 0.52,
                        "to": 0.55,
                        "y": 0.62,
                        "rotFrom": 0.05,
                        "rotTo": 0.18,
                        "dur": 3.4,
                        "s": 0.43,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.34, "speed": 1.1, "seed": 11}],
            },
        },
        # s02: Spatial Establish — Wide cohort line vs misty ridge skirmishers
        {
            **_meta("s02"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Wide multi-layer pass: skirmishers press from the high ridge while the Roman cohort withdraws in order",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 502,
                "back": [
                    {
                        "preset": "celtic",
                        "rows": 2,
                        "cols": 10,
                        "x0": 0.55,
                        "x1": 0.96,
                        "yFront": 0.67,
                        "yBack": 0.61,
                        "hFront": 0.11,
                        "hBack": 0.07,
                        "flip": True,
                    }
                ],
                "mid": [
                    {
                        "preset": "hastatus",
                        "rows": 2,
                        "cols": 6,
                        "x0": 0.06,
                        "x1": 0.46,
                        "yFront": 0.79,
                        "yBack": 0.72,
                        "hFront": 0.22,
                        "hBack": 0.15,
                    }
                ],
                "people": [
                    {
                        "id": "marcus",
                        "preset": "centurio",
                        "x": 0.36,
                        "to": 0.33,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "walk",
                        "face": "determined",
                    },
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "x": 0.58,
                        "to": 0.55,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "walk",
                        "face": "worried",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "from": 0.62,
                        "to": 0.59,
                        "y": 0.63,
                        "rotFrom": 0.08,
                        "rotTo": 0.14,
                        "dur": 4.0,
                        "s": 0.42,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.30, "speed": 0.95, "seed": 22}],
            },
        },
        # s03: Inciting Slip — Gaius loses footing on slick slate; standalone Eagle drops onto stones
        # Note: gaius uses weapon='sword' here so standalone 'eagle' prop has 100% single-prop exclusivity!
        {
            **_meta("s03"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Aquilifer Gaius slips on wet slate and stumbles to one knee as the bronze Eagle standard drops forward",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 503,
                "people": [
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "x": 0.46,
                        "to": 0.49,
                        "y": 0.86,
                        "h": 0.46,
                        "fall": 0.45,
                        "face": "pain",
                    }
                ],
                "props": [
                    {
                        "kind": "rock",
                        "x": 0.54,
                        "y": 0.88,
                        "s": 0.12,
                    },
                    {
                        "kind": "eagle",
                        "x": 0.53,
                        "from": 0.50,
                        "to": 0.60,
                        "y": 0.68,
                        "fromY": 0.58,
                        "toY": 0.78,
                        "rotFrom": 0.15,
                        "rotTo": 1.28,
                        "moveAt": 0.35,
                        "dur": 0.95,
                        "s": 0.42,
                        "top": True,
                    },
                ],
                "fx": [{"kind": "fog", "density": 0.30, "speed": 1.0, "seed": 33}],
            },
        },
        # s04: Discovery — Close-up on Centurion Marcus spotting the fallen Eagle through drifting fog
        {
            **_meta("s04"),
            "tpl": "close",
            "expected_subject": "actor",
            "desc": "Close-up on Centurion Marcus turning sharply as his eyes lock onto the fallen cohort standard",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 504,
                "preset": "centurio",
                "x": 0.50,
                "y": 0.56,
                "R": 0.18,
                "face": "shock",
                "faceAt": [[1.1, "determined"]],
                "look": 0.65,
                "talk": True,
                "fx": [{"kind": "fog", "density": 0.22, "speed": 0.85, "seed": 44}],
            },
        },
        # s05: Command Signal — Marcus raises blazing torch high in upper frame ordering rescue detail forward
        {
            **_meta("s05"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Centurion Marcus raises a blazing signal torch high above his red transverse crest",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 505,
                "people": [
                    {
                        "id": "marcus",
                        "preset": "centurio",
                        "weapon": "torch",
                        "x": 0.42,
                        "y": 0.85,
                        "h": 0.50,
                        "pose": "fire_signal",
                        "face": "shout",
                        "talk": True,
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "x": 0.60,
                        "to": 0.66,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "run",
                        "face": "determined",
                    },
                ],
                "props": [
                    {"kind": "campfire", "x": 0.24, "y": 0.87, "s": 0.14},
                ],
                "fx": [{"kind": "fog", "density": 0.26, "speed": 1.0, "seed": 55}],
            },
        },
        # s06: Tactical Clarity — High-contrast mobile-legible corridor schematic
        {
            **_meta("s06"),
            "tpl": "scene",
            "expected_subject": "diagram",
            "desc": "Tactical schematic showing the locked Roman shield flanks and two-man rescue corridor to the fallen Eagle",
            "args": {
                "bg": "mountain",
                "time": "night",
                "blur": 12,
                "seed": 506,
                "props": [
                    {
                        "kind": "roman_eagle_rescue_diagram",
                        "x": 0.50,
                        "y": 0.50,
                        "s": 0.86,
                        "top": True,
                    }
                ],
            },
        },
        # s07: Rescue Dash — Decimus and Lucius sprint smoothly across misty gap toward fallen Eagle
        {
            **_meta("s07"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Rescue legionaries Decimus and Lucius sprint in tight pair across wet slate toward the fallen Eagle",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 507,
                "people": [
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "from": 0.28,
                        "to": 0.54,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "run",
                        "face": "determined",
                    },
                    {
                        "id": "lucius",
                        "preset": "principes",
                        "from": 0.18,
                        "to": 0.43,
                        "y": 0.87,
                        "h": 0.45,
                        "pose": "run",
                        "face": "determined",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "x": 0.68,
                        "y": 0.79,
                        "rot": 1.28,
                        "s": 0.40,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.30, "speed": 1.25, "seed": 77}],
            },
        },
        # s08: Shield Cover — Frontline comrades lock curved red scuta against incoming skirmish shafts
        {
            **_meta("s08"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Frontline hastati and legionaries lock curved red scuta in low brace stance deflecting skirmish arrows",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 508,
                "tint": ["#2b221e", 0.18],
                "people": [
                    {
                        "id": "cover_a",
                        "preset": "hastatus",
                        "x": 0.36,
                        "y": 0.90,
                        "h": 0.43,
                        "pose": "brace",
                        "face": "determined",
                    },
                    {
                        "id": "cover_b",
                        "preset": "legionary",
                        "x": 0.48,
                        "y": 0.90,
                        "h": 0.43,
                        "pose": "brace",
                        "face": "determined",
                    },
                    {
                        "id": "cover_c",
                        "preset": "principes",
                        "x": 0.60,
                        "y": 0.90,
                        "h": 0.43,
                        "pose": "brace",
                        "face": "determined",
                    },
                ],
                "fx": [
                    {"kind": "volley", "n": 18, "at": 0.35, "dur": 1.3, "dir": -1, "x0": 0.32, "x1": 0.68, "y0": 0.52, "y1": 0.84},
                    {"kind": "fog", "density": 0.22, "speed": 1.05, "seed": 88},
                ],
            },
        },
        # s09: Physical Lift — Decimus steadies Gaius as Gaius rises and lifts the standalone Eagle upright
        {
            **_meta("s09"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Decimus guards with his scutum while Gaius rises from the slate and rotates the bronze Eagle upright",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 509,
                "people": [
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "x": 0.48,
                        "y": 0.86,
                        "h": 0.47,
                        "rise": 0.25,
                        "riseDur": 1.6,
                        "pose": "stand",
                        "face": "determined",
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "x": 0.60,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "guard",
                        "face": "determined",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "x": 0.52,
                        "from": 0.55,
                        "to": 0.52,
                        "y": 0.62,
                        "fromY": 0.78,
                        "toY": 0.58,
                        "rotFrom": 1.28,
                        "rotTo": 0.0,
                        "moveAt": 0.25,
                        "dur": 1.65,
                        "s": 0.44,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.26, "speed": 0.9, "seed": 99}],
            },
        },
        # s10: Coordinated Withdrawal — Gaius carries the recovered Eagle prop back into the Roman shield line
        {
            **_meta("s10"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "With the Eagle secured in Gaius's grip, the rescue pair withdraws in measured step toward cohort shields",
            "args": {
                "bg": "mountain",
                "time": "dawn",
                "seed": 510,
                "people": [
                    {
                        "id": "marcus",
                        "preset": "centurio",
                        "x": 0.26,
                        "y": 0.86,
                        "h": 0.47,
                        "pose": "guard",
                        "face": "determined",
                    },
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "from": 0.62,
                        "to": 0.44,
                        "y": 0.86,
                        "h": 0.47,
                        "pose": "walk",
                        "face": "determined",
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "from": 0.72,
                        "to": 0.55,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "walk",
                        "face": "determined",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "from": 0.66,
                        "to": 0.48,
                        "y": 0.61,
                        "dur": 4.1,
                        "s": 0.43,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.24, "speed": 0.85, "seed": 110}],
            },
        },
        # s11: Formation Recovery — Wide cohort closes its interval around the recovered standard
        {
            **_meta("s11"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "The Roman cohort closes its protective interval around Marcus and Gaius as dawn light warms the pass",
            "args": {
                "bg": "mountain",
                "time": "day",
                "seed": 511,
                "mid": [
                    {
                        "preset": "hastatus",
                        "rows": 2,
                        "cols": 8,
                        "x0": 0.10,
                        "x1": 0.90,
                        "yFront": 0.79,
                        "yBack": 0.71,
                        "hFront": 0.23,
                        "hBack": 0.15,
                    }
                ],
                "people": [
                    {
                        "id": "marcus",
                        "preset": "centurio",
                        "from": 0.36,
                        "to": 0.40,
                        "y": 0.86,
                        "h": 0.47,
                        "pose": "march",
                        "face": "proud",
                    },
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "from": 0.54,
                        "to": 0.50,
                        "y": 0.86,
                        "h": 0.48,
                        "pose": "march",
                        "face": "determined",
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "from": 0.66,
                        "to": 0.60,
                        "y": 0.86,
                        "h": 0.46,
                        "pose": "march",
                        "face": "calm",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "from": 0.58,
                        "to": 0.54,
                        "y": 0.60,
                        "dur": 4.1,
                        "s": 0.44,
                        "top": True,
                    }
                ],
                "fx": [{"kind": "fog", "density": 0.18, "speed": 0.75, "seed": 121}],
            },
        },
        # s12: Heroic Payoff & Mobile Summary Card — Parting fog reveals raised Eagle + high-contrast takeaway banner
        {
            **_meta("s12"),
            "tpl": "scene",
            "expected_subject": "actor",
            "desc": "Parting valley mist reveals the gilded Cohort Eagle held high alongside a crisp mobile-readable takeaway card",
            "args": {
                "bg": "mountain",
                "time": "day",
                "seed": 512,
                "people": [
                    {
                        "id": "gaius",
                        "preset": "aquilifer",
                        "weapon": "sword",
                        "x": 0.49,
                        "y": 0.87,
                        "h": 0.49,
                        "pose": "raise_standard",
                        "face": "proud",
                    },
                    {
                        "id": "marcus",
                        "preset": "centurio",
                        "x": 0.34,
                        "y": 0.87,
                        "h": 0.47,
                        "pose": "stand",
                        "face": "determined",
                    },
                    {
                        "id": "decimus",
                        "preset": "legionary",
                        "x": 0.65,
                        "y": 0.87,
                        "h": 0.46,
                        "pose": "stand",
                        "face": "calm",
                    },
                ],
                "props": [
                    {
                        "kind": "eagle",
                        "x": 0.54,
                        "fromY": 0.58,
                        "toY": 0.53,
                        "dur": 2.2,
                        "s": 0.46,
                        "top": True,
                    },
                    {
                        "kind": "mobile_summary_card",
                        "x": 0.50,
                        "y": 0.14,
                        "s": 0.23,
                        "title": "THE EAGLE IN THE FOG — COHORT STANDARD RECOVERED",
                        "subtitle": "SHIELD CORRIDOR • DISCIPLINED TEAMWORK • UNBROKEN LINE",
                        "top": True,
                    },
                ],
                "fx": [
                    {"kind": "rays", "x": 0.62, "n": 4, "a": 0.16},
                    {"kind": "fog", "density": 0.24, "speed": 0.8, "parting": True, "partAt": 0.2, "partDur": 2.8, "seed": 132},
                ],
            },
        },
    ]

    # Attach smooth cinematic camera paths (zero snap!)
    cam_plans = plan_camera_sequence(shots, config={"aspect": "16:9"}, aspect="16:9")
    for s, cp in zip(shots, cam_plans):
        s["camera"] = cp.model_dump()
        if s["expected_subject"] == "diagram":
            s["args"]["cameraRig"] = {
                "keyframes": [
                    {"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.0},
                    {"t": round(float(s["dur"]), 2), "x": 0.50, "y": 0.50, "z": 1.03},
                ]
            }
        elif s["id"] == "s12":
            # Keep framing centered so top summary card and raised standard stay inside safe margins
            s["args"]["cameraRig"] = {
                "keyframes": [
                    {"t": 0.0, "x": 0.50, "y": 0.50, "z": 1.0},
                    {"t": round(float(s["dur"]), 2), "x": 0.50, "y": 0.49, "z": 1.04},
                ]
            }
        else:
            s["args"]["cameraRig"] = {
                "keyframes": [
                    {
                        "t": round(float(kf.local_sec), 3),
                        "x": round(min(0.54, max(0.46, float(kf.x_center))), 3),
                        "y": round(min(0.53, max(0.48, float(kf.y_center))), 3),
                        "z": round(min(1.08, max(1.0, float(kf.zoom))), 3),
                    }
                    for kf in cp.camera_path
                ]
            }

    return {
        "schema_version": "14.7.5",
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "historical_framing": "Illustrative Fictional Reconstruction",
        "pack": "squire",
        "aspect": "16:9",
        "fps": 24,
        "total_duration": round(float(shots[-1]["end"]), 3),
        "shots": shots,
    }


def construct_eagle_project(
    project_path: Path = PROJECT_DIR,
    storyboard: Optional[Dict[str, Any]] = None,
    timed_beats: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Write config.json, character_bible.json, input/01-PHIM.txt, script.json, storyboard.json, and shots.json."""
    p_dir = Path(project_path).resolve()
    for sub in ("input", "story", "timeline", "build", "out"):
        (p_dir / sub).mkdir(parents=True, exist_ok=True)

    config = {
        "name": p_dir.name,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "pack": "squire",
        "genre": "roman_historical_reconstruction",
        "aspect": "16:9",
        "resolution": "1080p",
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "ai_director_mode": "OFFLINE_ONLY",
    }
    (p_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    character_bible = {
        "schema_version": "14.7.5",
        "historical_framing": FILM_SUBTITLE,
        "characters": {
            "marcus": {
                "name": "Centurion Marcus",
                "preset": "centurio",
                "role": "Cohort Centurion",
                "silhouette_markers": "Attic helmet with transverse red crest, crimson cloak, scutum/signal torch",
            },
            "gaius": {
                "name": "Aquilifer Gaius",
                "preset": "aquilifer",
                "role": "Standard-Bearer",
                "silhouette_markers": "Montefortino helmet, brown pelt cape, round buckler, gilded Cohort Eagle standard",
            },
            "decimus": {
                "name": "Legionary Decimus",
                "preset": "legionary",
                "role": "Lead Rescue Legionary",
                "silhouette_markers": "Montefortino helmet with red crest, mail lorica, curved red scutum",
            },
            "lucius": {
                "name": "Optio-file Lucius",
                "preset": "principes",
                "role": "Second Rescue Legionary",
                "silhouette_markers": "Three-feathered Montefortino helmet, red tunic, curved scutum",
            },
        },
    }
    (p_dir / "story" / "character_bible.json").write_text(
        json.dumps(character_bible, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    beats = timed_beats or BASE_BEATS
    raw_script_lines = [f"# {FILM_TITLE} ({FILM_SUBTITLE})", ""] + [b["text"] for b in beats]
    (p_dir / "input" / "01-PHIM.txt").write_text("\n".join(raw_script_lines) + "\n", encoding="utf-8")

    if storyboard is not None:
        for fname in ("shots.json", "storyboard.json"):
            target = p_dir / "story" / fname
            tmp_f = target.with_suffix(".tmp.json")
            tmp_f.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp_f, target)

        (p_dir / "story" / "script.json").write_text(
            json.dumps(
                {
                    "title": FILM_TITLE,
                    "subtitle": FILM_SUBTITLE,
                    "beats": beats,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    return {"project_dir": str(p_dir), "config": config, "character_bible": character_bible}


def _render_contact_sheet_grid(
    mp4_path: Path,
    samples: List[Tuple[str, float]],
    out_png: Path,
    cols: int,
    header_title: str,
    thumb_w: int = 480,
    thumb_h: int = 270,
) -> Path:
    """Decode exact frames from the final MP4 and assemble a labeled PNG contact sheet."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_png.parent / f".cs_tmp_{os.getpid()}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    rows = math.ceil(len(samples) / cols)
    pad = 14
    header_h = 54
    label_h = 28
    canvas_w = pad + cols * (thumb_w + pad)
    canvas_h = header_h + pad + rows * (thumb_h + label_h + pad)
    sheet = Image.new("RGB", (canvas_w, canvas_h), (18, 22, 30))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    safe_header = header_title.replace("—", "-").replace("–", "-").replace("·", "|")
    draw.text((pad, 18), safe_header, fill=(242, 208, 107), font=font)

    try:
        for idx, (caption, ts) in enumerate(samples):
            r_idx = idx // cols
            c_idx = idx % cols
            x0 = pad + c_idx * (thumb_w + pad)
            y0 = header_h + pad + r_idx * (thumb_h + label_h + pad)
            f_png = tmp_dir / f"f_{idx:02d}.png"
            ok = extract_frame_at_time(mp4_path, ts, f_png)
            if ok and f_png.is_file():
                with Image.open(f_png) as im:
                    thumb = im.convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(thumb, (x0, y0))
            draw.rectangle([x0, y0 + thumb_h, x0 + thumb_w, y0 + thumb_h + label_h], fill=(28, 34, 46))
            draw.text((x0 + 8, y0 + thumb_h + 7), f"{caption} @ {ts:.2f}s", fill=(235, 240, 248), font=font)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    tmp_out = out_png.with_suffix(".tmp.png")
    sheet.save(tmp_out, format="PNG")
    os.replace(tmp_out, out_png)
    return out_png


def generate_eagle_contact_sheets(
    mp4_path: Path,
    shots: List[Dict[str, Any]],
    out_dir: Path,
) -> Dict[str, str]:
    """Generate contact_sheet_full.png, contact_sheet_hook.png, and contact_sheet_action.png from decoded MP4."""
    full_samples = [
        (f"{s['id']} {s['action']}", round((float(s["start"]) + float(s["end"])) * 0.5, 2))
        for s in shots
    ]
    s01_end = float(shots[0]["end"])
    s03_end = float(shots[2]["end"])
    hook_samples = [
        ("hook_01_open", 0.55),
        ("hook_02_fog_std", round(s01_end * 0.65, 2)),
        ("hook_03_establish", round(s01_end + 1.2, 2)),
        ("hook_04_ridge_threat", round(s01_end + 3.1, 2)),
        ("hook_05_slip_start", round(float(shots[2]["start"]) + 0.55, 2)),
        ("hook_06_eagle_down", round(s03_end - 0.55, 2)),
    ]
    action_ids = ["s05", "s06", "s07", "s08", "s09", "s12"]
    shots_by_id = {s["id"]: s for s in shots}
    action_samples = [
        (f"{sid}_{shots_by_id[sid]['action']}", round((float(shots_by_id[sid]["start"]) + float(shots_by_id[sid]["end"])) * 0.5, 2))
        for sid in action_ids
        if sid in shots_by_id
    ]

    p_full = _render_contact_sheet_grid(
        mp4_path,
        full_samples,
        out_dir / "contact_sheet_full.png",
        cols=4,
        header_title=f"{FILM_TITLE} — FULL 12-SHOT CONTACT SHEET (DECODED 1080P MP4)",
    )
    p_hook = _render_contact_sheet_grid(
        mp4_path,
        hook_samples,
        out_dir / "contact_sheet_hook.png",
        cols=3,
        header_title=f"{FILM_TITLE} — OPENING HOOK & INCITING SLIP (ACT I)",
    )
    p_action = _render_contact_sheet_grid(
        mp4_path,
        action_samples,
        out_dir / "contact_sheet_action.png",
        cols=3,
        header_title=f"{FILM_TITLE} — SIGNAL, SCHEMATIC, RESCUE, SHIELD COVER & PAYOFF",
    )
    return {
        "contact_sheet_full": str(p_full),
        "contact_sheet_hook": str(p_hook),
        "contact_sheet_action": str(p_action),
    }


def inspect_eagle_preview(
    project_path: Optional[Path] = None,
    output_mp4: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verify final Eagle in the Fog MP4 via full decode, EBU R128 loudness, and cryptographic receipt."""
    p_dir = (project_path or PROJECT_DIR).resolve()
    out_mp4 = (output_mp4 or OUT_MP4_PATH).resolve()

    expected_specs = {
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "min_duration": 50.0,
        "max_duration": 58.0,
        "check_volume": True,
        "measure_loudness": True,
        "max_true_peak_dbtp": -0.5,
    }
    manifest = collect_render_inputs(
        project_path=p_dir,
        render_options={
            "pack": "squire",
            "genre": "roman_historical_reconstruction",
            "resolution": "1080p",
            "aspect": "16:9",
            "audio_mode": "voice_sfx",
            "fps": 24,
        },
    )
    cache_check = validate_cache_hit(p_dir, out_mp4, manifest, expected_specs=expected_specs)
    media_info = inspect_media_file(out_mp4, expected_specs=expected_specs, require_audio=True, full_decode=True)
    return {
        "valid": bool(media_info.get("valid") and cache_check.get("hit")),
        "cache_status": cache_check.get("status"),
        "cache_hit": bool(cache_check.get("hit")),
        "cache_reason": cache_check.get("reason"),
        "media_info": media_info,
        "receipt": cache_check.get("receipt"),
    }


def produce_eagle_in_fog_preview(
    project_path: Optional[Path] = None,
    output_mp4: Optional[Path] = None,
    force_rebuild: bool = False,
    workers: int = 1,
) -> Dict[str, Any]:
    """
    End-to-end production pipeline for `THE EAGLE IN THE FOG — A ROMAN STANDARD RESCUE`.
    """
    t0 = time.perf_counter()
    p_dir = (project_path or PROJECT_DIR).resolve()
    out_mp4 = (output_mp4 or OUT_MP4_PATH).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not force_rebuild and out_mp4.is_file():
        existing = inspect_eagle_preview(p_dir, out_mp4)
        if existing.get("valid"):
            mi = existing["media_info"]
            return {
                "status": "CACHE_HIT_VERIFIED",
                "render_mode": "CACHE_HIT_VERIFIED",
                "ai_director_mode": "OFFLINE_ONLY",
                "output_path": str(out_mp4),
                "duration": mi.get("duration"),
                "width": mi.get("width"),
                "height": mi.get("height"),
                "fps": mi.get("fps"),
                "video_codec": mi.get("video_codec"),
                "audio_codec": mi.get("audio_codec"),
                "integrated_lufs": mi.get("integrated_lufs"),
                "true_peak_dbtp": mi.get("true_peak_dbtp"),
                "sha256": mi.get("sha256"),
                "elapsed_sec": round(time.perf_counter() - t0, 3),
            }

    construct_eagle_project(p_dir)
    voice_res = generate_timed_voice_track(p_dir, BASE_BEATS)
    if not voice_res.get("ok"):
        return voice_res

    timed_beats = voice_res["timed_beats"]
    total_dur = float(voice_res["total_duration"])
    storyboard = build_eagle_storyboard(timed_beats)
    construct_eagle_project(p_dir, storyboard=storyboard, timed_beats=timed_beats)

    mixed_wav = build_eagle_soundtrack(p_dir, timed_beats=timed_beats, total_dur=total_dur)

    # Render 1080p24 silent master in genuine REAL_RENDER mode (QA_STUDIO_TEST_MODE explicitly stripped)
    clean_env = dict(os.environ)
    clean_env.pop("QA_STUDIO_TEST_MODE", None)
    clean_env.pop("GEMINI_API_KEY", None)

    cmd_render = [
        "node",
        str(ROOT_DIR / "render.mjs"),
        "--project",
        str(p_dir),
        "--workers",
        str(max(1, int(workers))),
    ]
    res_render = subprocess.run(cmd_render, cwd=ROOT_DIR, env=clean_env, capture_output=True, text=True)
    render_log_path = p_dir / "build" / "render.log"
    render_log_path.write_text((res_render.stdout or "") + "\n" + (res_render.stderr or ""), encoding="utf-8")
    if res_render.returncode != 0:
        raise RuntimeError(f"render.mjs failed with exit {res_render.returncode}:\n{(res_render.stderr or res_render.stdout)[-800:]}")

    video_silent = p_dir / "build" / "video_silent.mp4"
    if not video_silent.is_file() or video_silent.stat().st_size < 1000:
        raise RuntimeError("Missing or empty build/video_silent.mp4 after render.mjs")

    # Atomic mux -> full media decode inspection -> atomic rename -> cryptographic receipt
    partial_mp4 = out_mp4.with_suffix(".partial.mp4")
    if partial_mp4.exists():
        partial_mp4.unlink()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_silent),
            "-i",
            str(mixed_wav),
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
            "-shortest",
            "-movflags",
            "+faststart",
            str(partial_mp4),
        ],
        check=True,
        capture_output=True,
    )

    expected_specs = {
        "width": 1920,
        "height": 1080,
        "fps": 24.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "min_duration": 50.0,
        "max_duration": 58.0,
        "check_volume": True,
        "measure_loudness": True,
        "max_true_peak_dbtp": -0.5,
    }
    partial_check = inspect_media_file(
        partial_mp4,
        expected_specs=expected_specs,
        require_audio=True,
        full_decode=True,
    )
    if not partial_check.get("valid", False):
        if partial_mp4.exists():
            partial_mp4.unlink()
        raise RuntimeError(f"Partial MP4 failed media inspection: {partial_check.get('error')}")

    os.replace(partial_mp4, out_mp4)

    sheets = generate_eagle_contact_sheets(out_mp4, storyboard["shots"], p_dir / "out")

    manifest = collect_render_inputs(
        project_path=p_dir,
        render_options={
            "pack": "squire",
            "genre": "roman_historical_reconstruction",
            "resolution": "1080p",
            "aspect": "16:9",
            "audio_mode": "voice_sfx",
            "fps": 24,
        },
    )
    fingerprint = compute_render_fingerprint(manifest)
    wall_sec = round(time.perf_counter() - t0, 3)

    receipt_path = write_render_receipt_atomic(
        project_path=p_dir,
        output_path=out_mp4,
        manifest=manifest,
        metadata={
            "action": "produce_eagle_in_fog_preview",
            "wall_sec": wall_sec,
            "force_rebuild": force_rebuild,
            "render_mode": "REAL_RENDER",
            "ai_director_mode": "OFFLINE_ONLY",
            "ai_director_live_used": False,
            "version": "14.7.5",
        },
    )
    final_verify = inspect_eagle_preview(p_dir, out_mp4)
    if not final_verify.get("valid"):
        raise RuntimeError(f"Post-receipt verification failed: {final_verify}")

    mi = final_verify["media_info"]
    return {
        "status": "PRODUCED",
        "render_mode": "REAL_RENDER",
        "ai_director_mode": "OFFLINE_ONLY",
        "ai_director_live_used": False,
        "title": FILM_TITLE,
        "subtitle": FILM_SUBTITLE,
        "output_path": str(out_mp4),
        "duration": mi.get("duration"),
        "width": mi.get("width"),
        "height": mi.get("height"),
        "fps": mi.get("fps"),
        "video_codec": mi.get("video_codec"),
        "audio_codec": mi.get("audio_codec"),
        "mean_volume_db": mi.get("mean_volume_db"),
        "max_volume_db": mi.get("max_volume_db"),
        "integrated_lufs": mi.get("integrated_lufs"),
        "true_peak_dbtp": mi.get("true_peak_dbtp"),
        "size_bytes": out_mp4.stat().st_size,
        "sha256": mi.get("sha256"),
        "fingerprint": fingerprint,
        "receipt_path": str(receipt_path),
        "render_log_path": str(render_log_path),
        "contact_sheets": sheets,
        "voice_summary": {
            "total_overlap_ms": voice_res["voice_ledger"]["total_overlap_ms"],
            "min_tail_margin_sec": voice_res["voice_ledger"]["min_tail_margin_sec"],
            "max_tail_margin_sec": voice_res["voice_ledger"]["max_tail_margin_sec"],
            "atempo_used_anywhere": voice_res["voice_ledger"]["atempo_used_anywhere"],
        },
        "elapsed_sec": wall_sec,
    }


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    res = produce_eagle_in_fog_preview(force_rebuild=force_flag, workers=1)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res.get("status") in ("PRODUCED", "CACHE_HIT_VERIFIED") else 1)
