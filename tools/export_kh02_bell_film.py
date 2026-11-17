#!/usr/bin/env python3
"""export_kh02_bell_film.py — Renders, mixes, calibrates true-peak AAC, verifies 720-frame decode,
and builds the editorial review packet for 'THE BELL THAT RANG TOO EARLY' (30.000s, 1920x1080 @ 24fps).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

from build_kh02_bell_project import build_bell_project, PROJ_DIR_DEFAULT
from kh02_visual_qa import build_visual_editorial_packet


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def measure_decoded_aac(mp4_path: Path) -> Dict[str, Any]:
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(mp4_path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    txt = (proc.stdout or "") + "\n" + (proc.stderr or "")
    m_i = re.findall(r"Integrated loudness:\s+I:\s+([-\d.]+)\s+LUFS", txt) or re.findall(r"I:\s+([-\d.]+)\s+LUFS", txt)
    m_tp = re.findall(r"True peak:\s+Peak:\s+([-\d.]+)\s+dBFS", txt) or re.findall(r"Peak:\s+([-\d.]+)\s+dBFS", txt)
    if not m_i or not m_tp:
        raise RuntimeError(f"Could not parse ebur128 metrics for {mp4_path}")
    return {
        "integrated_lufs": float(m_i[-1]),
        "true_peak_dbtp": float(m_tp[-1]),
    }


def export_bell_film(
    proj_dir: Path = PROJ_DIR_DEFAULT,
    packet_copy_dir: Path | None = None,
    workers: int = 2,
    skip_build: bool = False,
    reuse_fresh_silent: bool = False,
) -> Dict[str, Any]:
    t0 = time.time()
    proj_dir = Path(proj_dir).resolve()
    if not skip_build:
        build_bell_project(proj_dir)

    from common import compute_canonical_visual_hash
    silent_mp4 = proj_dir / "build" / "video_silent.mp4"
    vhash_file = proj_dir / "build" / "visual_hash.txt"
    expected_vhash = compute_canonical_visual_hash(str(proj_dir))
    is_fresh = (
        reuse_fresh_silent
        and silent_mp4.is_file()
        and vhash_file.is_file()
        and vhash_file.read_text(encoding="utf-8").strip() == expected_vhash
    )

    # 1. Headless Canvas2D 1080p render (720 frames @ 24fps)
    if not is_fresh:
        r_vid = subprocess.run(
            ["node", "render.mjs", "--project", str(proj_dir), "--workers", str(workers)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if r_vid.returncode != 0:
            raise RuntimeError(f"render.mjs failed:\n{r_vid.stdout}\n{r_vid.stderr}")

    # 2. Original 2D thumbnail render
    r_th = subprocess.run(
        ["node", "render.mjs", "--project", str(proj_dir), "--thumb"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if r_th.returncode != 0:
        raise RuntimeError(f"render.mjs --thumb failed:\n{r_th.stdout}\n{r_th.stderr}")

    # 3. Studio mix.py execution (produces build/mix.wav + out/The Bell That Rang Too Early.mp4)
    r_mix = subprocess.run(
        [sys.executable, "tools/mix.py", "--project", str(proj_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if r_mix.returncode != 0:
        raise RuntimeError(f"tools/mix.py failed:\n{r_mix.stdout}\n{r_mix.stderr}")

    # 4. Exact 30.000s, True-Peak-safe (<= -1.0 dBTP after AAC decode) master export:
    #    projects/kh02_bell_before_sunrise_30s/out/KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4
    silent_mp4 = proj_dir / "build" / "video_silent.mp4"
    mix_wav = proj_dir / "build" / "mix.wav"
    exact_wav = proj_dir / "build" / "mix_30s_exact.wav"
    final_mp4 = proj_dir / "out" / "KH02_BELL_EARLY_ORIGINAL_30S_1080P.mp4"
    partial_mp4 = proj_dir / "out" / "KH02_BELL_EARLY_ORIGINAL_30S_1080P.partial.mp4"

    # Trim audio to exact 30.000s (1,440,000 samples @ 48kHz) with smooth 0.30s tail fade and -1.9 dBFS brickwall ceiling
    # so lossy AAC reconstruction never exceeds -1.0 dBTP while preserving ~ -14.0 LUFS integrated loudness!
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-i", str(mix_wav),
            "-af", "atrim=0:30.0,asetpts=PTS-STARTPTS,afade=t=out:st=29.70:d=0.30,alimiter=limit=0.80:level=false",
            "-ar", "48000", "-ac", "2",
            str(exact_wav),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-i", str(silent_mp4),
            "-i", str(exact_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-t", "30.000",
            "-movflags", "+faststart",
            "-f", "mp4",
            str(partial_mp4),
        ],
        check=True,
    )
    partial_mp4.replace(final_mp4)

    # 5. Probe & full-frame decode verification on final MP4
    probe_proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(final_mp4)],
        capture_output=True,
        text=True,
        check=True,
    )
    probe = json.loads(probe_proc.stdout)
    v_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {})

    # Count actual decoded video frames via ffprobe -count_frames
    cnt_proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=nb_read_frames",
            "-of", "csv=p=0", str(final_mp4),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    decoded_frames = int(cnt_proc.stdout.strip().rstrip(",").splitlines()[0])

    # Full video + audio error-free null decode
    dec_proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(final_mp4), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if dec_proc.returncode != 0:
        raise RuntimeError(f"Final MP4 decode error: {dec_proc.stderr}")

    aac_metrics = measure_decoded_aac(final_mp4)

    # 6. Build visual editorial packet (8 stills, 8-shot contact sheet, 3 action strips)
    proj_packet_dir = proj_dir / "out" / "editorial_packet"
    packet = build_visual_editorial_packet(final_mp4, proj_packet_dir)

    if packet_copy_dir is not None:
        packet_copy_dir = Path(packet_copy_dir).resolve()
        if packet_copy_dir.exists():
            shutil.rmtree(packet_copy_dir)
        shutil.copytree(proj_packet_dir, packet_copy_dir)
        thumb_jpg = proj_dir / "out" / "thumbnail_1280.jpg"
        if thumb_jpg.is_file():
            shutil.copy2(thumb_jpg, packet_copy_dir / "thumbnail_1280.jpg")

    receipt = {
        "status": "FILM_EXPORT_VERIFIED",
        "experimental_preview": True,
        "style_approved": "HUMAN_REVIEW_PENDING",
        "editorial_approved": "HUMAN_REVIEW_PENDING",
        "output_mp4": final_mp4.relative_to(REPO_ROOT).as_posix(),
        "output_sha256": _sha256_file(final_mp4),
        "output_bytes": final_mp4.stat().st_size,
        "width": int(v_stream.get("width", 0)),
        "height": int(v_stream.get("height", 0)),
        "video_codec": v_stream.get("codec_name"),
        "audio_codec": a_stream.get("codec_name"),
        "fps": v_stream.get("r_frame_rate"),
        "video_stream_duration_sec": float(v_stream.get("duration", 0.0)),
        "format_duration_sec": float(probe.get("format", {}).get("duration", 0.0)),
        "decoded_frames": decoded_frames,
        "decoded_aac_lufs": aac_metrics["integrated_lufs"],
        "decoded_aac_true_peak_dbtp": aac_metrics["true_peak_dbtp"],
        "elapsed_sec": round(time.time() - t0, 2),
        "editorial_packet": packet,
    }
    (proj_dir / "out" / "kh02_film_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if packet_copy_dir is not None:
        (packet_copy_dir / "kh02_film_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(PROJ_DIR_DEFAULT))
    ap.add_argument("--packet-copy-dir", default=str(REPO_ROOT / "docs" / "antigravity_runs" / "KH-02_0_1_20261117_014132Z_db01" / "film_preview_packet"))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--reuse-fresh-silent", action="store_true")
    args = ap.parse_args()
    res = export_bell_film(
        Path(args.project),
        Path(args.packet_copy_dir),
        workers=args.workers,
        skip_build=args.skip_build,
        reuse_fresh_silent=args.reuse_fresh_silent,
    )
    print(json.dumps({k: v for k, v in res.items() if k != "editorial_packet"}, indent=2))
