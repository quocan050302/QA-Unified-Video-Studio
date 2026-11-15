#!/usr/bin/env python3
"""scripts/production_fingerprint.py — P0 Cryptographic Render Lineage, Fingerprinting & Cache Verification.

Ensures:
1. Strict deterministic hashing of all input files, stories, voices, assets, renderer code modules, and render options.
2. Complete elimination of false cache hits (e.g., build/preview.mp4 > 50KB).
3. Atomic render receipt writing and fail-closed validation.
4. Prevention of cross-project MP4 substitution (e.g., Roman MP4 substituted for Samurai or DEM).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent

RENDERER_CORE_MODULES = [
    ROOT_DIR / "render.mjs",
    ROOT_DIR / "engine" / "core.js",
    ROOT_DIR / "engine" / "canonical_hash.js",
    ROOT_DIR / "tools" / "ai_director.py",
    ROOT_DIR / "tools" / "cinematic_camera.py",
    ROOT_DIR / "tools" / "mix.py",
    ROOT_DIR / "tools" / "plan_audio.py",
]


def sha256_file(path: Path | str) -> str:
    """Compute hex SHA256 of a file in 64KB blocks."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for sha256: {p}")
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(data: Any) -> str:
    """Compute hex SHA256 of canonical JSON."""
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def collect_render_inputs(project_path: Path | str, render_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Collect comprehensive input file hashes, code module hashes, and render parameters.
    Returns canonical InputManifest dictionary.
    """
    proj = Path(project_path).resolve()
    if not proj.is_dir():
        raise FileNotFoundError(f"Project directory not found: {proj}")

    options = render_options or {}
    
    # 1. Project config
    cfg_path = proj / "config.json"
    cfg_data = {}
    cfg_sha = ""
    if cfg_path.is_file():
        cfg_sha = sha256_file(cfg_path)
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
        except Exception:
            pass

    pack = options.get("pack") or cfg_data.get("pack") or "squire"
    genre = options.get("genre") or cfg_data.get("genre") or ("self_improvement" if pack == "dem" else "roman")
    resolution = options.get("resolution") or cfg_data.get("resolution") or "1080p"
    aspect = options.get("aspect") or cfg_data.get("aspect") or "16:9"
    fps = options.get("fps") or cfg_data.get("fps") or 24

    # 2. Tracked project files (sorted for determinism)
    tracked_files: Dict[str, str] = {}
    if cfg_sha:
        tracked_files["config.json"] = cfg_sha

    candidate_rel_paths = [
        "story/shots.json",
        "story/storyboard.json",
        "story/script.json",
        "story/director_plan.json",
        "story/character_bible.json",
        "story/claims_manifest.json",
        "story/asset_source_manifest.json",
        "timeline/lines.json",
        "timeline/words.json",
        "timeline/blocks.json",
        "timeline/transcript.txt",
        "timeline/voice.wav",
        "timeline/voice_manifest.json",
        "timeline/voice_events.json",
        "timeline/timeline_voice_events.json",
        "build/voice_events.json",
        "build/audio_plan.json",
        "build/voice_track.wav",
        "build/soundtrack_mixed.wav",
        "input/voice_script.txt",
        "input/voice_source.wav",
        "input/01-PHIM.txt",
    ]

    for rel in candidate_rel_paths:
        fp = proj / rel
        if fp.is_file():
            tracked_files[rel] = sha256_file(fp)

    # Track voice/audio segment files if present
    for seg_sub in ("timeline/segments", "build/segments", "audio/segments"):
        seg_dir = proj / seg_sub
        if seg_dir.is_dir():
            for seg_f in sorted(seg_dir.glob("*.*")):
                if seg_f.is_file() and seg_f.suffix.lower() in (".wav", ".mp3", ".aac", ".m4a", ".ogg", ".json"):
                    tracked_files[str(seg_f.relative_to(proj))] = sha256_file(seg_f)

    # Track scenes directory JS files
    scenes_dir = proj / "scenes"
    if scenes_dir.is_dir():
        for sf in sorted(scenes_dir.rglob("*.js")):
            if sf.is_file() and not sf.name.startswith("."):
                rel_p = str(sf.relative_to(proj))
                tracked_files[rel_p] = sha256_file(sf)

    # Track anh (assets) directory images
    anh_dir = proj / "anh"
    if anh_dir.is_dir():
        for img in sorted(anh_dir.glob("*.*")):
            if img.is_file() and img.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
                rel_p = str(img.relative_to(proj))
                tracked_files[rel_p] = sha256_file(img)

    # 3. Renderer & engine code modules
    code_modules: Dict[str, str] = {}
    for mod in RENDERER_CORE_MODULES:
        if mod.is_file():
            code_modules[str(mod.relative_to(ROOT_DIR))] = sha256_file(mod)

    # Pack-specific code files (JS visual/diagram modules + Python audio packs)
    pack_dir = ROOT_DIR / "packs" / pack
    if pack_dir.is_dir():
        for pf in sorted(pack_dir.glob("*.*")):
            if pf.is_file() and pf.suffix.lower() in (".js", ".mjs", ".py"):
                code_modules[str(pf.relative_to(ROOT_DIR))] = sha256_file(pf)

    # Optional explicit project code_dependencies (e.g. packs/squire/civic/water_gate.js)
    raw_code_deps = options.get("code_dependencies")
    if raw_code_deps is None:
        raw_code_deps = cfg_data.get("code_dependencies")
    extra_code_deps: List[str] = []
    if isinstance(raw_code_deps, list) and len(raw_code_deps) > 0:
        for dep_rel in sorted({str(d).strip().lstrip("/") for d in raw_code_deps if str(d).strip()}):
            dep_path = (ROOT_DIR / dep_rel).resolve()
            if not dep_path.is_file():
                raise FileNotFoundError(f"Declared code_dependency missing: {dep_rel} ({dep_path})")
            rel_norm = str(dep_path.relative_to(ROOT_DIR)) if dep_path.is_relative_to(ROOT_DIR) else dep_rel
            code_modules[rel_norm] = sha256_file(dep_path)
            extra_code_deps.append(rel_norm)

    # 4. Normalized render options
    norm_options: Dict[str, Any] = {
        "pack": pack,
        "genre": genre,
        "resolution": resolution,
        "aspect": aspect,
        "fps": int(fps),
        "from_sec": float(options.get("from_sec", 0.0)),
        "to_sec": float(options.get("to_sec", 0.0)) if options.get("to_sec") is not None else None,
        "crf": int(options.get("crf", 20)),
        "scale": float(options.get("scale", 1.0)),
        "audio_mode": options.get("audio_mode", "silent" if pack == "dem" else "voice_sfx"),
    }
    if extra_code_deps:
        norm_options["code_dependencies"] = extra_code_deps

    manifest = {
        "schema_version": "1.0",
        "project_id": proj.name,
        "project_rel_path": str(proj.relative_to(ROOT_DIR)) if proj.is_relative_to(ROOT_DIR) else proj.name,
        "tracked_files": tracked_files,
        "code_modules": code_modules,
        "render_options": norm_options,
    }
    return manifest


def compute_render_fingerprint(manifest: Dict[str, Any]) -> str:
    """Compute deterministic SHA256 of the input manifest."""
    return sha256_json(manifest)


def inspect_media_file(
    mp4_path: Path | str,
    expected_specs: Optional[Dict[str, Any]] = None,
    require_audio: bool = False,
    full_decode: bool = False,
    require_video: bool = True,
) -> Dict[str, Any]:
    """
    Run ffprobe and optional FFmpeg full decode on an MP4 file.
    Validates streams, codecs, duration, dimensions, decode integrity, and audio level.
    """
    p = Path(mp4_path)
    if not p.is_file() or p.stat().st_size < 100:
        return {"valid": False, "error": f"File missing or empty: {p}", "errors": ["File missing or empty"]}

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,duration,channels,sample_rate",
        "-of", "json",
        str(p)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        probe = json.loads(res.stdout)
    except Exception as e:
        return {"valid": False, "error": f"ffprobe failed: {e}", "errors": [str(e)]}

    streams = probe.get("streams", [])
    format_info = probe.get("format", {})
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(format_info.get("duration", 0.0))
    file_size = int(format_info.get("size", p.stat().st_size))

    width = v_stream.get("width") if v_stream else None
    height = v_stream.get("height") if v_stream else None
    v_codec = v_stream.get("codec_name") if v_stream else None
    a_codec = a_stream.get("codec_name") if a_stream else None

    # Calculate fps from avg_frame_rate
    fps = None
    if v_stream and "avg_frame_rate" in v_stream:
        fr = v_stream["avg_frame_rate"]
        if "/" in fr:
            num, den = fr.split("/")
            if float(den) > 0:
                fps = round(float(num) / float(den), 2)
        else:
            try:
                fps = round(float(fr), 2)
            except Exception:
                pass

    has_video = v_stream is not None
    has_audio = a_stream is not None

    errors: List[str] = []
    if require_video and not has_video:
        errors.append("No video stream found in media file")
    if duration <= 0.0:
        errors.append(f"Invalid duration: {duration}s <= 0")
    if file_size < 1000:
        errors.append(f"File size suspiciously small: {file_size} bytes")

    if require_audio and not has_audio:
        errors.append("Audio stream required but not found in media file")

    if expected_specs:
        if "width" in expected_specs and width != expected_specs["width"]:
            errors.append(f"Width mismatch: expected {expected_specs['width']}, got {width}")
        if "height" in expected_specs and height != expected_specs["height"]:
            errors.append(f"Height mismatch: expected {expected_specs['height']}, got {height}")
        if "video_codec" in expected_specs and v_codec != expected_specs["video_codec"]:
            errors.append(f"Video codec mismatch: expected {expected_specs['video_codec']}, got {v_codec}")
        if "audio_codec" in expected_specs and a_codec != expected_specs["audio_codec"]:
            errors.append(f"Audio codec mismatch: expected {expected_specs['audio_codec']}, got {a_codec}")
        if "min_duration" in expected_specs and duration < expected_specs["min_duration"]:
            errors.append(f"Duration {duration:.2f}s below minimum {expected_specs['min_duration']}s")
        if "max_duration" in expected_specs and duration > expected_specs["max_duration"]:
            errors.append(f"Duration {duration:.2f}s exceeds maximum {expected_specs['max_duration']}s")
        if "fps" in expected_specs and fps and abs(fps - expected_specs["fps"]) > 0.5:
            errors.append(f"FPS mismatch: expected {expected_specs['fps']}, got {fps}")

    decode_clean = True
    decoded_video_frames: Optional[int] = None
    video_stream_duration = float(v_stream.get("duration")) if (v_stream and v_stream.get("duration") is not None) else None
    audio_stream_duration = float(a_stream.get("duration")) if (a_stream and a_stream.get("duration") is not None) else None

    if full_decode and (has_video or has_audio):
        dec_cmd = ["ffmpeg", "-v", "error", "-i", str(p), "-f", "null", "-"]
        dec_res = subprocess.run(dec_cmd, capture_output=True, text=True)
        if dec_res.returncode != 0 or dec_res.stderr.strip():
            decode_clean = False
            errors.append(f"Full ffmpeg decode failed: {dec_res.stderr.strip()[:200]}")

    if has_video and (full_decode or (expected_specs and "exact_video_frames" in expected_specs)):
        fc_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(p),
        ]
        fc_res = subprocess.run(fc_cmd, capture_output=True, text=True)
        if fc_res.returncode == 0 and fc_res.stdout.strip().isdigit():
            decoded_video_frames = int(fc_res.stdout.strip())
            if expected_specs and "exact_video_frames" in expected_specs:
                exp_vf = int(expected_specs["exact_video_frames"])
                if decoded_video_frames != exp_vf:
                    errors.append(
                        f"Decoded video frame count mismatch: expected exact {exp_vf}, got {decoded_video_frames}"
                    )
        elif expected_specs and "exact_video_frames" in expected_specs:
            errors.append("Failed to count decoded video frames via ffprobe -count_frames")

    max_volume_db = None
    mean_volume_db = None
    integrated_lufs = None
    true_peak_dbtp = None
    if has_audio and (require_audio or (expected_specs and expected_specs.get("check_volume"))):
        vol_cmd = ["ffmpeg", "-i", str(p), "-af", "volumedetect", "-f", "null", "-"]
        vol_res = subprocess.run(vol_cmd, capture_output=True, text=True)
        import re
        m_max = re.search(r"max_volume:\s+([-\d.]+)\s+dB", vol_res.stderr)
        m_mean = re.search(r"mean_volume:\s+([-\d.]+)\s+dB", vol_res.stderr)
        if m_mean:
            try:
                mean_volume_db = float(m_mean.group(1))
            except ValueError:
                pass
        if m_max:
            try:
                max_volume_db = float(m_max.group(1))
                if max_volume_db <= -60.0:
                    errors.append(f"Audio is silent (max_volume={max_volume_db} dB)")
                if expected_specs and expected_specs.get("reject_clipping") and max_volume_db >= 0.0:
                    errors.append(f"Audio clipping detected (max_volume={max_volume_db} dB >= 0.0 dB)")
            except ValueError:
                pass
        else:
            errors.append("Failed to measure audio max_volume via volumedetect")

        if expected_specs and (expected_specs.get("measure_loudness") or "max_true_peak_dbtp" in expected_specs):
            ebur_cmd = ["ffmpeg", "-nostats", "-i", str(p), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]
            ebur_res = subprocess.run(ebur_cmd, capture_output=True, text=True)
            m_lufs = re.findall(r"I:\s+([-\d.]+)\s+LUFS", ebur_res.stderr)
            m_tp = re.findall(r"Peak:\s+([-\d.]+)\s+dBFS", ebur_res.stderr)
            if m_lufs:
                try:
                    integrated_lufs = float(m_lufs[-1])
                except ValueError:
                    pass
            if m_tp:
                try:
                    true_peak_dbtp = float(m_tp[-1])
                    if "max_true_peak_dbtp" in expected_specs and true_peak_dbtp > float(expected_specs["max_true_peak_dbtp"]):
                        errors.append(
                            f"Audio true peak {true_peak_dbtp:.2f} dBTP exceeds limit {expected_specs['max_true_peak_dbtp']} dBTP"
                        )
                except ValueError:
                    pass

    sha_val = sha256_file(p)

    return {
        "valid": len(errors) == 0,
        "error": "; ".join(errors) if errors else None,
        "errors": errors,
        "duration": duration,
        "video_stream_duration": video_stream_duration,
        "audio_stream_duration": audio_stream_duration,
        "decoded_video_frames": decoded_video_frames,
        "file_size": file_size,
        "width": width,
        "height": height,
        "fps": fps,
        "video_codec": v_codec,
        "audio_codec": a_codec,
        "has_video": has_video,
        "has_audio": a_stream is not None,
        "decode_clean": decode_clean,
        "max_volume_db": max_volume_db,
        "mean_volume_db": mean_volume_db,
        "integrated_lufs": integrated_lufs,
        "true_peak_dbtp": true_peak_dbtp,
        "sha256": sha_val,
    }


def write_render_receipt_atomic(
    project_path: Path | str,
    output_path: Path | str,
    manifest: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Atomically write verified render receipt to build/render_receipt.json and output receipt.
    """
    proj = Path(project_path).resolve()
    out_p = Path(output_path).resolve()
    build_dir = proj / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    if not out_p.is_file():
        raise FileNotFoundError(f"Cannot write receipt for nonexistent output: {out_p}")

    req_audio = (manifest.get("render_options", {}).get("audio_mode") == "voice_sfx")
    media_info = inspect_media_file(
        out_p,
        expected_specs={"measure_loudness": True} if req_audio else None,
        require_audio=req_audio,
        full_decode=True,
    )
    if not media_info.get("valid"):
        raise ValueError(f"Cannot write receipt for invalid media: {media_info.get('error')}")

    input_fingerprint = compute_render_fingerprint(manifest)
    output_sha256 = media_info["sha256"]

    receipt = {
        "schema_version": "1.0",
        "receipt_id": f"rcpt_{int(time.time())}_{output_sha256[:10]}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_id": manifest["project_id"],
        "pack": manifest["render_options"]["pack"],
        "genre": manifest["render_options"]["genre"],
        "aspect": manifest["render_options"]["aspect"],
        "resolution": manifest["render_options"]["resolution"],
        "audio_mode": manifest["render_options"]["audio_mode"],
        "input_fingerprint": input_fingerprint,
        "input_manifest": manifest,
        "output_path": str(out_p.relative_to(ROOT_DIR)) if out_p.is_relative_to(ROOT_DIR) else str(out_p),
        "output_sha256": output_sha256,
        "media_info": media_info,
        "provenance": {
            "node_version": subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip(),
            "python_version": sys.version.split()[0],
            "action": metadata.get("action", "render") if metadata else "render",
            "wall_sec": metadata.get("wall_sec", 0.0) if metadata else 0.0,
            "force_rebuild": metadata.get("force_rebuild", False) if metadata else False,
            "render_mode": metadata.get("render_mode", "REAL_RENDER") if metadata else "REAL_RENDER",
            "ai_director_mode": metadata.get("ai_director_mode", "OFFLINE_ONLY") if metadata else "OFFLINE_ONLY",
            "ai_director_live_used": bool(metadata.get("ai_director_live_used", False)) if metadata else False,
            "version": metadata.get("version", "14.7.5") if metadata else "14.7.5",
        },
    }

    # Write atomically with fsync
    receipt_path = build_dir / "render_receipt.json"
    temp_fd, temp_path = tempfile.mkstemp(dir=build_dir, prefix="rcpt_", suffix=".tmp")
    with open(temp_fd, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, receipt_path)

    # Also write alongside output file if in out/ or build/ directory atomically
    if out_p.parent.name == "out" or out_p.parent.name == "build":
        sidecar = out_p.with_suffix(".receipt.json")
        try:
            s_fd, s_tmp = tempfile.mkstemp(dir=out_p.parent, prefix="sidecar_", suffix=".tmp")
            with open(s_fd, "w", encoding="utf-8") as sf:
                json.dump(receipt, sf, indent=2, ensure_ascii=False)
                sf.write("\n")
                sf.flush()
                os.fsync(sf.fileno())
            os.replace(s_tmp, sidecar)
        except Exception:
            pass

    return receipt_path


def validate_cache_hit(
    project_path: Path | str,
    output_path: Path | str,
    manifest: Dict[str, Any],
    expected_specs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate whether existing output MP4 is a strict, cryptographically verified cache hit.
    Returns:
      {
        "hit": bool,
        "status": "CACHE_HIT_VERIFIED" | "CACHE_INVALIDATED" | "CACHE_MISS",
        "reason": str,
        "receipt": Optional[dict],
        "media_info": Optional[dict],
      }
    """
    proj = Path(project_path).resolve()
    out_p = Path(output_path).resolve()

    if not out_p.is_file():
        return {
            "hit": False,
            "status": "CACHE_MISS",
            "reason": f"Output artifact does not exist: {out_p}",
            "receipt": None,
            "media_info": None,
        }

    # Locate receipt
    receipt_p = proj / "build" / "render_receipt.json"
    sidecar_p = out_p.with_suffix(".receipt.json")
    chosen_receipt_p = receipt_p if receipt_p.is_file() else (sidecar_p if sidecar_p.is_file() else None)

    if not chosen_receipt_p:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": "Missing cryptographic render_receipt.json (legacy or unverified artifact).",
            "receipt": None,
            "media_info": None,
        }

    try:
        with open(chosen_receipt_p, "r", encoding="utf-8") as f:
            receipt = json.load(f)
    except Exception as e:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Corrupted render receipt: {e}",
            "receipt": None,
            "media_info": None,
        }

    # Verify project ID match
    if receipt.get("project_id") != manifest.get("project_id"):
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Project ID mismatch: receipt has '{receipt.get('project_id')}', current manifest has '{manifest.get('project_id')}'. Cross-project substitution rejected.",
            "receipt": receipt,
            "media_info": None,
        }

    # Verify input fingerprint match (fail closed on null, empty, or non-64-hex values)
    current_fingerprint = compute_render_fingerprint(manifest)
    recorded_fingerprint = receipt.get("input_fingerprint")
    if not isinstance(recorded_fingerprint, str) or len(recorded_fingerprint.strip()) < 64:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Missing, null, or malformed input_fingerprint in receipt: {recorded_fingerprint!r}",
            "receipt": receipt,
            "media_info": None,
        }
    recorded_fingerprint = recorded_fingerprint.strip()
    if current_fingerprint != recorded_fingerprint:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Input fingerprint mismatch: code, storyboard, voice, or assets modified. Recorded={recorded_fingerprint[:12]}, Current={current_fingerprint[:12]}",
            "receipt": receipt,
            "media_info": None,
        }

    recorded_out_sha = receipt.get("output_sha256")
    if not isinstance(recorded_out_sha, str) or len(recorded_out_sha.strip()) < 64:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Missing, null, or malformed output_sha256 in receipt: {recorded_out_sha!r}",
            "receipt": receipt,
            "media_info": None,
        }

    # Inspect media file with full decode & audio requirement, and verify file sha256
    req_audio = (manifest.get("render_options", {}).get("audio_mode") == "voice_sfx")
    spec_filter = {
        k: v
        for k, v in (expected_specs or {}).items()
        if k in (
            "width",
            "height",
            "video_codec",
            "audio_codec",
            "min_duration",
            "max_duration",
            "fps",
            "exact_video_frames",
            "check_volume",
            "reject_clipping",
            "measure_loudness",
            "max_true_peak_dbtp",
        )
    }
    media_info = inspect_media_file(
        out_p,
        expected_specs=spec_filter if spec_filter else None,
        require_audio=req_audio,
        full_decode=True,
    )
    if not media_info.get("valid"):
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Output media verification failed: {media_info.get('error')}",
            "receipt": receipt,
            "media_info": media_info,
        }

    if media_info["sha256"] != recorded_out_sha.strip():
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": "Output artifact content SHA256 mismatch: file on disk was modified or corrupted.",
            "receipt": receipt,
            "media_info": media_info,
        }

    # Verify expected specs if supplied
    if expected_specs:
        if "pack" in expected_specs and expected_specs["pack"] != receipt.get("pack"):
            return {
                "hit": False,
                "status": "CACHE_INVALIDATED",
                "reason": f"Pack mismatch: expected {expected_specs['pack']}, got {receipt.get('pack')}",
                "receipt": receipt,
                "media_info": media_info,
            }
        if "aspect" in expected_specs and expected_specs["aspect"] != receipt.get("aspect"):
            return {
                "hit": False,
                "status": "CACHE_INVALIDATED",
                "reason": f"Aspect ratio mismatch: expected {expected_specs['aspect']}, got {receipt.get('aspect')}",
                "receipt": receipt,
                "media_info": media_info,
            }
        if "audio_mode" in expected_specs and expected_specs["audio_mode"] != receipt.get("audio_mode"):
            return {
                "hit": False,
                "status": "CACHE_INVALIDATED",
                "reason": f"Audio mode mismatch: expected {expected_specs['audio_mode']}, got {receipt.get('audio_mode')}",
                "receipt": receipt,
                "media_info": media_info,
            }

    return {
        "hit": True,
        "status": "CACHE_HIT_VERIFIED",
        "reason": "Cryptographically verified cache hit (matching input manifest, output SHA256, and valid media streams).",
        "receipt": receipt,
        "media_info": media_info,
    }


def _is_valid_hex64(val: Any) -> bool:
    if not isinstance(val, str):
        return False
    s = val.strip().lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def extract_receipt_lineage_fields(receipt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Explicit versioned receipt field adapter (supports schema_version '1.0' and '0.9-legacy').
    Never guesses arbitrary fields and never treats null/empty values as valid.
    """
    if not isinstance(receipt, dict):
        return {
            "valid_schema": False,
            "schema_version": None,
            "input_fingerprint": None,
            "output_sha256": None,
            "stored_render_options": None,
            "error": "Receipt is missing or not a JSON object",
        }
    ver = str(receipt.get("schema_version") or "")
    if ver == "1.0":
        inp_fp = receipt.get("input_fingerprint")
        out_sha = receipt.get("output_sha256")
        man = receipt.get("input_manifest")
        opts = man.get("render_options") if isinstance(man, dict) else None
    elif ver == "0.9-legacy":
        inp_fp = receipt.get("legacy_input_sha256")
        out_sha = receipt.get("legacy_output_sha256")
        opts = receipt.get("legacy_render_options")
    else:
        return {
            "valid_schema": False,
            "schema_version": ver or None,
            "input_fingerprint": None,
            "output_sha256": None,
            "stored_render_options": None,
            "error": f"Unsupported or missing receipt schema_version: {ver!r}",
        }

    if not _is_valid_hex64(inp_fp):
        return {
            "valid_schema": False,
            "schema_version": ver,
            "input_fingerprint": None,
            "output_sha256": out_sha if _is_valid_hex64(out_sha) else None,
            "stored_render_options": opts if isinstance(opts, dict) else None,
            "error": f"Receipt input_fingerprint is null, empty, or invalid 64-hex: {inp_fp!r}",
        }
    if not _is_valid_hex64(out_sha):
        return {
            "valid_schema": False,
            "schema_version": ver,
            "input_fingerprint": inp_fp.strip(),
            "output_sha256": None,
            "stored_render_options": opts if isinstance(opts, dict) else None,
            "error": f"Receipt output_sha256 is null, empty, or invalid 64-hex: {out_sha!r}",
        }
    if not isinstance(opts, dict):
        return {
            "valid_schema": False,
            "schema_version": ver,
            "input_fingerprint": inp_fp.strip(),
            "output_sha256": out_sha.strip(),
            "stored_render_options": None,
            "error": "Receipt missing stored input_manifest.render_options dict",
        }

    return {
        "valid_schema": True,
        "schema_version": ver,
        "input_fingerprint": inp_fp.strip(),
        "output_sha256": out_sha.strip(),
        "stored_render_options": dict(opts),
        "error": None,
    }


def verify_receipt_and_lineage(
    project_path: Path | str,
    output_path: Path | str,
    expected_specs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Strict fail-closed provenance, input_fingerprint, output_sha256, and cache-hit verifier (V14.7.5.1).
    Recomputes fresh `collect_render_inputs(project_path, exact_stored_render_options)` and verifies:
      1. Receipt exists and passes versioned schema validation (no null/empty hashes).
      2. Recomputed fresh `input_fingerprint == receipt.input_fingerprint`.
      3. Current disk MP4 `sha256 == receipt.output_sha256`.
      4. `validate_cache_hit(project_path, output_path, fresh_manifest, expected_specs).hit is True`.
    """
    proj = Path(project_path).resolve()
    out_p = Path(output_path).resolve()
    errors: List[str] = []

    receipt_p = proj / "build" / "render_receipt.json"
    sidecar_p = out_p.with_suffix(".receipt.json")
    chosen_receipt_p = receipt_p if receipt_p.is_file() else (sidecar_p if sidecar_p.is_file() else None)

    receipt: Optional[Dict[str, Any]] = None
    if chosen_receipt_p is None:
        errors.append("Missing build/render_receipt.json and sidecar receipt")
    else:
        try:
            receipt = json.loads(chosen_receipt_p.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Corrupted receipt JSON: {exc}")

    adapted = extract_receipt_lineage_fields(receipt)
    if not adapted["valid_schema"]:
        errors.append(str(adapted["error"]))

    stored_opts = adapted["stored_render_options"]
    recorded_fp = adapted["input_fingerprint"]
    recorded_out_sha = adapted["output_sha256"]

    recomputed_fp: Optional[str] = None
    fresh_manifest: Optional[Dict[str, Any]] = None
    if proj.is_dir() and isinstance(stored_opts, dict):
        try:
            fresh_manifest = collect_render_inputs(proj, stored_opts)
            recomputed_fp = compute_render_fingerprint(fresh_manifest)
        except Exception as exc:
            errors.append(f"Failed to recompute fresh render inputs: {exc}")

    live_out_sha: Optional[str] = None
    if out_p.is_file():
        live_out_sha = sha256_file(out_p)
    else:
        errors.append(f"Output MP4 missing on disk: {out_p}")

    fp_match = bool(
        recorded_fp is not None
        and recomputed_fp is not None
        and recorded_fp == recomputed_fp
    )
    if not fp_match and recorded_fp is not None and recomputed_fp is not None:
        errors.append(
            f"input_fingerprint mismatch: receipt={recorded_fp[:16]} != recomputed={recomputed_fp[:16]}"
        )

    out_sha_match = bool(
        recorded_out_sha is not None
        and live_out_sha is not None
        and recorded_out_sha == live_out_sha
    )
    if not out_sha_match and recorded_out_sha is not None and live_out_sha is not None:
        errors.append(
            f"output_sha256 mismatch: receipt={recorded_out_sha[:16]} != disk={live_out_sha[:16]}"
        )

    cache_res: Dict[str, Any] = {"hit": False, "status": "NOT_RUN", "reason": "Skipped due to invalid manifest", "media_info": None}
    if fresh_manifest is not None and out_p.is_file():
        cache_res = validate_cache_hit(proj, out_p, fresh_manifest, expected_specs=expected_specs)
        if not cache_res.get("hit"):
            errors.append(f"validate_cache_hit rejected artifact: {cache_res.get('reason')}")

    media_info = cache_res.get("media_info")
    media_decode_verified = bool(
        isinstance(media_info, dict)
        and media_info.get("valid") is True
        and media_info.get("decode_clean") is True
    )
    receipt_verified = bool(adapted["valid_schema"] and fp_match and out_sha_match)
    cache_verified = bool(cache_res.get("hit") is True)
    all_ok = bool(receipt_verified and cache_verified and media_decode_verified and len(errors) == 0)

    return {
        "evidence_schema_version": "14.7.5.1",
        "status": "PASS" if all_ok else "FAIL",
        "project_id": proj.name,
        "receipt_path": str(chosen_receipt_p.relative_to(ROOT_DIR)) if (chosen_receipt_p and chosen_receipt_p.is_relative_to(ROOT_DIR)) else (str(chosen_receipt_p) if chosen_receipt_p else None),
        "output_path": str(out_p.relative_to(ROOT_DIR)) if out_p.is_relative_to(ROOT_DIR) else str(out_p),
        "input_fingerprint": recorded_fp,
        "recomputed_input_fingerprint": recomputed_fp,
        "fingerprint_match": fp_match,
        "output_sha256": live_out_sha,
        "recorded_output_sha256": recorded_out_sha,
        "output_sha_match": out_sha_match,
        "receipt_verified": receipt_verified,
        "cache_verified": cache_verified,
        "cache_status": cache_res.get("status"),
        "media_decode_verified": media_decode_verified,
        "stored_render_options": stored_opts,
        "tracked_files_count": len((fresh_manifest or {}).get("tracked_files", {})),
        "code_modules_count": len((fresh_manifest or {}).get("code_modules", {})),
        "media_info": media_info,
        "provenance": (receipt or {}).get("provenance", {}),
        "errors": errors,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/production_fingerprint.py <project_path> [output_path]")
        sys.exit(1)
    proj = sys.argv[1]
    man = collect_render_inputs(proj)
    fp = compute_render_fingerprint(man)
    print(f"Project: {proj}")
    print(f"Fingerprint: {fp}")
    print(f"Tracked files: {len(man['tracked_files'])}")
    print(f"Code modules: {len(man['code_modules'])}")
    if len(sys.argv) > 2:
        out_f = sys.argv[2]
        res = validate_cache_hit(proj, out_f, man)
        print(f"Cache status: {res['status']} | {res['reason']}")
