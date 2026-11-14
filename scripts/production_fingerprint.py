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
        "story/director_plan.json",
        "story/character_bible.json",
        "story/claims_manifest.json",
        "timeline/lines.json",
        "timeline/words.json",
        "timeline/blocks.json",
        "timeline/transcript.txt",
        "timeline/voice.wav",
        "timeline/voice_manifest.json",
        "input/voice_script.txt",
        "input/voice_source.wav",
    ]

    for rel in candidate_rel_paths:
        fp = proj / rel
        if fp.is_file():
            tracked_files[rel] = sha256_file(fp)

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

    # Pack-specific code files
    pack_dir = ROOT_DIR / "packs" / pack
    if pack_dir.is_dir():
        for pf in sorted(pack_dir.glob("*.js")):
            if pf.is_file():
                code_modules[str(pf.relative_to(ROOT_DIR))] = sha256_file(pf)

    # 4. Normalized render options
    norm_options = {
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


def inspect_media_file(mp4_path: Path | str) -> Dict[str, Any]:
    """Run ffprobe on an MP4 file to inspect streams, codecs, duration, dimensions."""
    p = Path(mp4_path)
    if not p.is_file() or p.stat().st_size < 100:
        return {"valid": False, "error": "File missing or empty"}

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,duration,channels,sample_rate",
        "-of", "json",
        str(p)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        probe = json.loads(res.stdout)
    except Exception as e:
        return {"valid": False, "error": f"ffprobe failed: {e}"}

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

    return {
        "valid": True,
        "duration": duration,
        "file_size": file_size,
        "width": width,
        "height": height,
        "fps": fps,
        "video_codec": v_codec,
        "audio_codec": a_codec,
        "has_video": v_stream is not None,
        "has_audio": a_stream is not None,
        "sha256": sha256_file(p),
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

    media_info = inspect_media_file(out_p)
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
        },
    }

    # Write atomically
    receipt_path = build_dir / "render_receipt.json"
    temp_fd, temp_path = tempfile.mkstemp(dir=build_dir, prefix="rcpt_", suffix=".tmp")
    with open(temp_fd, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, receipt_path)

    # Also write alongside output file if in out/ directory
    if out_p.parent.name == "out" or out_p.parent.name == "build":
        sidecar = out_p.with_suffix(".receipt.json")
        try:
            shutil.copyfile(receipt_path, sidecar)
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

    # Verify input fingerprint match
    current_fingerprint = compute_render_fingerprint(manifest)
    recorded_fingerprint = receipt.get("input_fingerprint")
    if current_fingerprint != recorded_fingerprint:
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Input fingerprint mismatch: code, storyboard, voice, or assets modified. Recorded={recorded_fingerprint[:12]}, Current={current_fingerprint[:12]}",
            "receipt": receipt,
            "media_info": None,
        }

    # Inspect media file & verify file sha256
    media_info = inspect_media_file(out_p)
    if not media_info.get("valid"):
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Output media verification failed: {media_info.get('error')}",
            "receipt": receipt,
            "media_info": media_info,
        }

    if media_info["sha256"] != receipt.get("output_sha256"):
        return {
            "hit": False,
            "status": "CACHE_INVALIDATED",
            "reason": f"Output artifact content SHA256 mismatch: file on disk was modified or corrupted.",
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
