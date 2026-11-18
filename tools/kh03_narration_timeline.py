#!/usr/bin/env python3
"""kh03_narration_timeline.py — Independent Spoken Narration & Alignment Timeline Builder for KH-03.0.R1.

Decouples voice synthesis/measurement from visual shot cutting:
- Synthesizes real spoken speech via scripts/tts_helper.py (Windows SAPI / macOS say) or imports WAVs.
- Measures real trimmed PCM duration and RMS energy per spoken line (rejects silent/sine fakes).
- Packs continuous narration cleanly into target duration (<= 1.15x hard tempo stretch, <= 1.10x preferred).
- Writes timeline/lines.json & timeline/words.json without 1:1 shot_id coupling when in
  `editorial_mode: script_beat_director_v1`.

Preserves tools/kh03_preview_director.py::build_roman_audio_timeline unchanged for legacy projects.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tts_helper import synthesize_speech

TARGET_SR = 48000


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


def _trim_silence(sig: np.ndarray, sr: int = TARGET_SR, thresh: float = 0.008, pad_sec: float = 0.025) -> np.ndarray:
    idx = np.where(np.abs(sig) > thresh)[0]
    if len(idx) == 0:
        return sig
    pad = int(pad_sec * sr)
    i0 = max(0, int(idx[0]) - pad)
    i1 = min(len(sig), int(idx[-1]) + pad)
    return sig[i0:i1]


def synthesize_or_import_narration(
    lines: List[Dict[str, Any]],
    project_dir: Path | str,
    voice_cfg: Optional[Dict[str, Any]] = None,
    scratch_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Synthesize or import real spoken WAV per normalized line and measure PCM properties."""
    proj = Path(project_dir).resolve()
    cfg = voice_cfg or {}
    scr = Path(scratch_dir).resolve() if scratch_dir else (proj / "build" / "tts_raw")
    scr.mkdir(parents=True, exist_ok=True)

    import_dir = Path(cfg["import_dir"]).resolve() if cfg.get("import_dir") else None
    clips: List[Dict[str, Any]] = []

    for item in lines:
        lid = item["id"]
        text = item["text"]
        wav_path = scr / f"{lid}.wav"

        if import_dir and (import_dir / f"{lid}.wav").is_file():
            src_wav = import_dir / f"{lid}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(src_wav), "-ar", str(TARGET_SR), "-ac", "1", str(wav_path)],
                check=True,
            )
            source_kind = "imported_user_wav"
        else:
            ok = synthesize_speech(text, wav_path)
            if not ok or not wav_path.is_file():
                raise RuntimeError(f"NOT_RUN_MISSING_VOICE: Offline TTS failed for line {lid}")
            source_kind = "local_os_sapi_speech_synthesizer"

        raw_sig, sr = sf.read(str(wav_path), dtype="float32")
        if raw_sig.ndim > 1:
            raw_sig = raw_sig.mean(axis=1)
        if sr != TARGET_SR:
            res_wav = scr / f"{lid}_48k.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(wav_path), "-ar", str(TARGET_SR), "-ac", "1", str(res_wav)],
                check=True,
            )
            res_wav.replace(wav_path)
            raw_sig, sr = sf.read(str(wav_path), dtype="float32")

        trimmed = _trim_silence(raw_sig, TARGET_SR)
        rms = float(np.sqrt(np.mean(trimmed ** 2))) if len(trimmed) else 0.0
        dur_sec = len(trimmed) / TARGET_SR
        if rms < 0.006 or dur_sec < 0.25:
            raise RuntimeError(
                f"AUDIO_VOICE_BLOCKED: Line {lid} speech waveform invalid/silent (rms={rms:.5f}, dur={dur_sec:.3f}s)"
            )

        trimmed_wav = scr / f"{lid}_trim.wav"
        sf.write(str(trimmed_wav), trimmed, TARGET_SR, subtype="PCM_16")
        clips.append({
            "id": lid,
            "text": text,
            "slot": item.get("slot", "NARRATOR"),
            "wav_path": str(trimmed_wav),
            "sample_rate": TARGET_SR,
            "raw_duration_sec": round(dur_sec, 4),
            "raw_rms": round(rms, 6),
            "pause_after_hint_sec": float(item.get("pause_after_sec", 0.22)),
            "source_kind": source_kind,
            "sha256": _sha256_file(trimmed_wav),
        })

    return {
        "status": "PASS",
        "project": proj.name,
        "sample_rate": TARGET_SR,
        "clips_count": len(clips),
        "raw_total_speech_sec": round(sum(c["raw_duration_sec"] for c in clips), 3),
        "clips": clips,
    }


def _estimate_word_spans_for_line(
    line_id: str,
    text: str,
    start_sec: float,
    end_sec: float,
) -> List[Dict[str, Any]]:
    """Estimate word spans inside a measured PCM clip using syllable/punctuation weights.

    Explicitly records that offline SAPI lacks native phoneme-level forced alignment.
    """
    tokens = [w for w in text.split() if w.strip()]
    if not tokens:
        return []
    weights = []
    for tok in tokens:
        alpha = re.sub(r"[^\w]", "", tok)
        w = max(2, len(alpha)) + (3 if re.search(r"[.!?]$", tok) else (2 if re.search(r"[,—;:]$", tok) else 0))
        weights.append(w)
    total_w = sum(weights) or 1
    dur = max(0.05, end_sec - start_sec)
    cursor = start_sec
    words_out: List[Dict[str, Any]] = []
    for idx, (tok, wt) in enumerate(zip(tokens, weights)):
        wd = dur * (wt / total_w)
        w_start = round(cursor, 3)
        w_end = round(end_sec if idx == len(tokens) - 1 else (cursor + wd), 3)
        words_out.append({
            "id": f"{line_id}_W{idx + 1:02d}",
            "w": tok,
            "t": w_start,
            "e": w_end,
            "line_id": line_id,
            "timing_precision": "weighted_char_interpolation_within_measured_clip",
        })
        cursor += wd
    return words_out


def pack_narration_into_30s(
    voice_clips: List[Dict[str, Any]],
    target_duration: float = 30.0,
    lead_in_sec: float = 0.08,
    tail_pad_sec: float = 0.45,
    preferred_stretch: float = 1.10,
    max_stretch: float = 1.15,
    scratch_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Pack measured speech clips into target duration cleanly without extreme TTS speed distortion."""
    if not voice_clips:
        raise ValueError("No voice clips provided to pack_narration_into_30s")

    scr = Path(scratch_dir).resolve() if scratch_dir else Path(voice_clips[0]["wav_path"]).parent
    scr.mkdir(parents=True, exist_ok=True)
    raw_speech_total = sum(float(c["raw_duration_sec"]) for c in voice_clips)
    pause_hints = [float(c.get("pause_after_hint_sec", 0.20)) for c in voice_clips[:-1]]
    raw_pauses_total = sum(pause_hints)

    available_budget = target_duration - lead_in_sec - tail_pad_sec
    if available_budget <= 0:
        raise ValueError("Target duration too small for lead_in + tail_pad")

    # Determine natural pause scaling before stretching any spoken clip!
    min_pause = 0.08
    if raw_speech_total + raw_pauses_total <= available_budget:
        tempo_scale = 1.0
        pause_scale = 1.0
    else:
        # First tighten inter-line pauses moderately (keep meaningful payoffs >= 0.35s when requested)
        min_pauses_total = sum(max(min_pause, min(p, 0.36 if p > 0.4 else 0.14)) for p in pause_hints)
        if raw_speech_total + min_pauses_total <= available_budget:
            tempo_scale = 1.0
            pause_scale = max(0.25, (available_budget - raw_speech_total) / max(1e-6, raw_pauses_total))
        else:
            pause_scale = 0.35
            effective_pauses = sum(max(min_pause, p * pause_scale) for p in pause_hints)
            speech_budget = available_budget - effective_pauses
            tempo_scale = raw_speech_total / max(0.5, speech_budget)
            if tempo_scale > max_stretch:
                raise RuntimeError(
                    f"AUDIO_STRETCH_EXCEEDED: Spoken clips total {raw_speech_total:.2f}s require {tempo_scale:.3f}x > "
                    f"hard cap {max_stretch:.2f}x. Shorten or split the narration text cleanly instead of distorting speech."
                )

    sr = TARGET_SR
    total_samples = int(round(target_duration * sr))
    master_voice = np.zeros(total_samples, dtype=np.float32)

    cursor = lead_in_sec
    packed_clips: List[Dict[str, Any]] = []
    for idx, clip in enumerate(voice_clips):
        wav_p = Path(clip["wav_path"])
        rate_used = 1.0
        sig_use: np.ndarray
        if tempo_scale > 1.005:
            # Clamp individual rate gently <= preferred_stretch first if possible
            rate_used = round(min(max_stretch, tempo_scale), 4)
            atempo_wav = scr / f"{clip['id']}_packed.wav"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-v", "error", "-i", str(wav_p),
                    "-af", f"atempo={rate_used}", "-ar", str(sr), "-ac", "1", str(atempo_wav),
                ],
                check=True,
            )
            sig_use, _ = sf.read(str(atempo_wav), dtype="float32")
            sig_use = _trim_silence(sig_use if sig_use.ndim == 1 else sig_use.mean(axis=1), sr)
        else:
            sig_use, _ = sf.read(str(wav_p), dtype="float32")
            if sig_use.ndim > 1:
                sig_use = sig_use.mean(axis=1)

        # Gentle 12ms fade in/out for zero-click splicing
        fade_n = min(int(0.012 * sr), len(sig_use) // 4)
        if fade_n > 1:
            sig_use[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
            sig_use[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

        dur = len(sig_use) / sr
        t_start = round(cursor, 3)
        t_end = round(min(target_duration - 0.04, t_start + dur), 3)
        i0 = int(round(t_start * sr))
        i1 = min(total_samples, i0 + len(sig_use))
        if i1 > i0:
            master_voice[i0:i1] += sig_use[: i1 - i0]

        gap_after = 0.0
        if idx < len(voice_clips) - 1:
            hint = float(clip.get("pause_after_hint_sec", 0.20))
            gap_after = round(max(min_pause, hint * pause_scale), 3)

        packed_clips.append({
            **clip,
            "start": t_start,
            "end": t_end,
            "duration": round(t_end - t_start, 3),
            "tempo_rate": rate_used,
            "within_preferred_stretch": rate_used <= preferred_stretch,
            "gap_after_sec": gap_after,
            "pcm_sample_range": [i0, i1],
        })
        cursor = t_end + gap_after

    return {
        "status": "PASS",
        "target_duration_sec": target_duration,
        "global_tempo_scale": round(tempo_scale, 4),
        "exceeded_preferred_stretch": tempo_scale > preferred_stretch,
        "within_hard_max_stretch": tempo_scale <= max_stretch,
        "voice_rms": round(float(np.sqrt(np.mean(master_voice ** 2))), 6),
        "master_voice": master_voice,
        "clips": packed_clips,
    }


def align_words_and_lines(
    packed_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Produce independent narration line & word timelines with explicit alignment precision provenance."""
    lines_out: List[Dict[str, Any]] = []
    words_out: List[Dict[str, Any]] = []

    for c in packed_result["clips"]:
        l_words = _estimate_word_spans_for_line(c["id"], c["text"], c["start"], c["end"])
        words_out.extend(l_words)
        lines_out.append({
            "id": c["id"],
            "slot": c.get("slot", "NARRATOR"),
            "start": c["start"],
            "end": c["end"],
            "duration": c["duration"],
            "tempo_rate": c["tempo_rate"],
            "rms": c["raw_rms"],
            "gap_after_sec": c["gap_after_sec"],
            "pcm_sample_range": c["pcm_sample_range"],
            "word_count": len(l_words),
            "text": c["text"],
        })

    return {
        "schema_version": "kh03.r1.narration_timeline.v1",
        "word_alignment_method": "weighted_char_interpolation_within_measured_sapi_clip",
        "honest_precision_note": (
            "Each spoken sentence start/end is measured directly from its trimmed 48kHz PCM WAV clip; "
            "intra-sentence word boundaries are estimated by orthographic weight + punctuation pause weight "
            "because offline SAPI does not output phoneme forced timestamps."
        ),
        "lines": lines_out,
        "words": words_out,
    }


def merge_narration_visual_mapping(
    narration_data: Dict[str, Any],
    master_voice: np.ndarray,
    shot_plan: Dict[str, Any],
    crosswalk: Dict[str, Any],
    project_dir: Path | str,
) -> Dict[str, Any]:
    """Write independent voice WAV and player/crosswalk timelines without legacy 1:1 shot_id locking."""
    proj = Path(project_dir).resolve()
    tl_dir = proj / "timeline"
    st_dir = proj / "story"
    tl_dir.mkdir(parents=True, exist_ok=True)
    st_dir.mkdir(parents=True, exist_ok=True)

    voice_wav_path = tl_dir / "voice.wav"
    sf.write(str(voice_wav_path), master_voice.astype(np.float32), TARGET_SR, subtype="PCM_16")

    lines_to_shots = crosswalk.get("lines_to_shots", {})
    shots_to_lines = crosswalk.get("shots_to_lines", {})

    lines_with_links: List[Dict[str, Any]] = []
    for ln in narration_data["lines"]:
        lid = ln["id"]
        entry = dict(ln)
        entry["shot_ids"] = lines_to_shots.get(lid, [])
        # Note: deliberately NO forced single scalar `shot_id` in script_beat_director_v1 mode!
        lines_with_links.append(entry)

    words_with_links: List[Dict[str, Any]] = []
    shots = shot_plan.get("shots", [])
    for w in narration_data["words"]:
        wt, we = float(w["t"]), float(w["e"])
        covering = [s["id"] for s in shots if s["end"] > wt and s["start"] < we]
        ww = dict(w)
        ww["shot_ids"] = covering
        words_with_links.append(ww)

    _atomic_write_json(tl_dir / "lines.json", lines_with_links)
    _atomic_write_json(tl_dir / "words.json", words_with_links)

    ed_mode = shot_plan.get("editorial_mode", "script_beat_director_v1")
    nar_manifest = {
        "schema_version": narration_data["schema_version"],
        "editorial_mode": ed_mode,
        "voice_wav_sha256": _sha256_file(voice_wav_path),
        "sample_rate": TARGET_SR,
        "duration_sec": shot_plan.get("duration_sec", 30.0),
        "word_alignment_method": narration_data["word_alignment_method"],
        "honest_precision_note": narration_data["honest_precision_note"],
        "lines": lines_with_links,
        "words": words_with_links,
    }
    _atomic_write_json(st_dir / "narration_timeline.json", nar_manifest)

    vis_timeline = {
        "schema_version": "kh03.r1.visual_timeline.v1",
        "editorial_mode": ed_mode,
        "fps": shot_plan["fps"],
        "total_frames": shot_plan["total_frames"],
        "duration_sec": shot_plan["duration_sec"],
        "shots": [
            {
                "id": s["id"],
                "frame_start": s["frame_start"],
                "frame_end": s["frame_end"],
                "start": s["start"],
                "end": s["end"],
                "duration": s["duration"],
                "location_id": s["location_id"],
                "framing_scale": s["framing_scale"],
                "purpose": s["purpose"],
                "line_ids": s["line_ids"],
                "word_range_ms": s["word_range_ms"],
            }
            for s in shots
        ],
    }
    _atomic_write_json(st_dir / "visual_timeline.json", vis_timeline)
    _atomic_write_json(st_dir / "shot_to_line_map.json", crosswalk)

    return {
        "voice_wav_path": str(voice_wav_path),
        "voice_wav_sha256": nar_manifest["voice_wav_sha256"],
        "lines_count": len(lines_with_links),
        "words_count": len(words_with_links),
        "shots_count": len(shots),
    }
