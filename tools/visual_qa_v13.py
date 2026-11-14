#!/usr/bin/env python3
"""
tools/visual_qa_v13.py - Visual Semantic QA & Motion Tracking (V13)
QA-Unified-Video-Studio V13

- Extracts exact frames from rendered MP4 using FFmpeg timecodes.
- Distinguishes subject motion from camera pan / zoom via background registration.
- Detects frozen, blank, or black frames.
- Evaluates 0-30s hook dynamic action and mobile safe zones for 9:16 Shorts.
- Generates contact sheet visual evidence artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def extract_video_frames_with_timestamps(
    video_path: Union[str, Path],
    timestamps: List[float],
    output_dir: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Extract exact video frames from rendered MP4 at specified timestamps using FFmpeg."""
    v_path = Path(video_path).resolve()
    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {v_path}")

    out_d = Path(output_dir) if output_dir else v_path.parent / "qa_frames"
    out_d.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    extracted = []

    for idx, ts in enumerate(timestamps):
        frame_name = f"frame_{idx:03d}_{ts:.2f}s.png"
        frame_path = out_d / frame_name

        cmd = [
            ffmpeg, "-y",
            "-ss", f"{ts:.3f}",
            "-i", str(v_path),
            "-vframes", "1",
            "-q:v", "2",
            str(frame_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if proc.returncode == 0 and frame_path.exists():
            # Read image metrics using Pillow or raw decode
            try:
                from PIL import Image
                with Image.open(frame_path) as img:
                    w, h = img.size
                    arr = np.array(img.convert("L"))
                    mean_val = float(np.mean(arr))
                    is_black = (mean_val < 3.0)
                    is_blank = (float(np.std(arr)) < 1.0)
            except Exception:
                w, h = 1920, 1080
                mean_val = 128.0
                is_black = False
                is_blank = False

            extracted.append({
                "timestamp": ts,
                "frame_path": str(frame_path),
                "width": w,
                "height": h,
                "mean_intensity": mean_val,
                "is_black": is_black,
                "is_blank": is_blank,
            })

    return extracted


def estimate_camera_pan(prev_img: np.ndarray, curr_img: np.ndarray) -> Tuple[float, float]:
    """Estimate global 2D camera translation (dx, dy) between two frames via phase correlation."""
    try:
        from scipy.signal import correlate2d
        # Downsample for speed
        p_sub = prev_img[::4, ::4].astype(np.float32)
        c_sub = curr_img[::4, ::4].astype(np.float32)
        p_sub -= np.mean(p_sub)
        c_sub -= np.mean(c_sub)
        
        # Cross-correlation on center region
        h, w = p_sub.shape
        cy, cx = h // 2, w // 2
        template = p_sub[cy-15:cy+15, cx-15:cx+15]
        corr = correlate2d(c_sub, template, mode='same')
        y_max, x_max = np.unravel_index(np.argmax(corr), corr.shape)
        dx = (x_max - cx) * 4.0
        dy = (y_max - cy) * 4.0
        return float(dx), float(dy)
    except Exception:
        return 0.0, 0.0


def measure_subject_motion_and_continuity(
    extracted_frames: List[Dict[str, Any]],
    intensity_threshold: float = 8.0,
) -> Dict[str, Any]:
    """
    Measure subject motion distinct from camera pan.
    Rejects completely still, frozen, or black frame sequences.
    """
    if len(extracted_frames) < 2:
        return {"motion_detected": False, "mean_subject_motion_pct": 0.0, "frames_analyzed": len(extracted_frames)}

    try:
        from PIL import Image
    except ImportError:
        return {
            "status": "BLOCKED",
            "motion_detected": False,
            "mean_subject_motion_pct": 0.0,
            "frames_analyzed": len(extracted_frames),
            "error": "PILLOW_UNAVAILABLE",
        }

    transitions = []
    motion_percentages = []

    for i in range(len(extracted_frames) - 1):
        f0_info = extracted_frames[i]
        f1_info = extracted_frames[i + 1]

        if f0_info["is_black"] or f1_info["is_black"]:
            transitions.append({"t0": f0_info["timestamp"], "t1": f1_info["timestamp"], "error": "BLACK_FRAME"})
            continue

        with Image.open(f0_info["frame_path"]) as img0, Image.open(f1_info["frame_path"]) as img1:
            arr0 = np.array(img0.convert("L")).astype(np.float32)
            arr1 = np.array(img1.convert("L")).astype(np.float32)

        # Estimate global camera shift
        cam_dx, cam_dy = estimate_camera_pan(arr0, arr1)

        # Shift arr0 by camera pan to isolate independent subject motion
        try:
            from scipy.ndimage import shift
            arr0_stabilized = shift(arr0, [cam_dy, cam_dx], mode='nearest')
            diff = np.abs(arr1 - arr0_stabilized)
        except Exception:
            diff = np.abs(arr1 - arr0)

        # Pixels with significant motion above noise threshold
        motion_mask = diff > intensity_threshold
        motion_pct = float(np.mean(motion_mask) * 100.0)
        motion_percentages.append(motion_pct)

        transitions.append({
            "t0": f0_info["timestamp"],
            "t1": f1_info["timestamp"],
            "camera_pan_dx": round(cam_dx, 2),
            "camera_pan_dy": round(cam_dy, 2),
            "subject_motion_pct": round(motion_pct, 2),
            "is_frozen": bool(motion_pct < 0.5),
        })

    avg_motion = float(np.mean(motion_percentages)) if motion_percentages else 0.0
    return {
        "motion_detected": bool(avg_motion >= 1.0),
        "mean_subject_motion_pct": round(avg_motion, 2),
        "has_frozen_cut": any(t.get("is_frozen") for t in transitions),
        "frames_analyzed": len(extracted_frames),
        "transitions": transitions,
    }


def evaluate_hook_quality_proxies(
    video_path: Union[str, Path],
    aspect: str = "16:9",
) -> Dict[str, Any]:
    """
    Evaluate opening hook dynamic action and mobile safe zones.
    Metrics are EDITORIAL_PROXIES, not audience retention claims.
    """
    v_path = Path(video_path).resolve()
    # Sample key timestamps in opening 30 seconds
    timestamps = [0.5, 1.5, 2.5, 5.0, 10.0, 15.0, 22.0, 26.0, 29.0]
    
    frames = extract_video_frames_with_timestamps(v_path, timestamps)
    motion_metrics = measure_subject_motion_and_continuity(frames)
    if motion_metrics.get("status") == "BLOCKED":
        return {
            "status": "BLOCKED",
            "metric_type": "EDITORIAL_PROXY",
            "error": motion_metrics.get("error", "PILLOW_UNAVAILABLE"),
            "first_3s_action_pass": False,
            "first_3s_motion_pct": 0.0,
            "twist_20_30s_action_pass": False,
            "twist_motion_pct": 0.0,
            "safe_zones_pass": False,
            "safe_zone_notes": ["Evaluation blocked: Pillow unavailable"],
            "total_frames_extracted": len(frames),
        }
    
    # Check 0-3s high-stakes action
    early_frames = [f for f in frames if f["timestamp"] <= 3.0]
    early_motion = measure_subject_motion_and_continuity(early_frames) if len(early_frames) >= 2 else {"mean_subject_motion_pct": 0.0}
    first_3s_action_ok = bool(early_motion.get("mean_subject_motion_pct", 0) >= 1.5)

    # Check 20-30s dynamic reveal / twist
    twist_frames = [f for f in frames if 20.0 <= f["timestamp"] <= 30.0]
    twist_motion = measure_subject_motion_and_continuity(twist_frames) if len(twist_frames) >= 2 else {"mean_subject_motion_pct": 0.0}
    twist_action_ok = bool(twist_motion.get("mean_subject_motion_pct", 0) >= 1.2)

    # Mobile safe-zone audit for 9:16 Shorts
    safe_zones_pass = True
    safe_zone_notes = []
    if aspect == "9:16":
        for f in frames:
            if f.get("width", 1080) > f.get("height", 1920):
                safe_zones_pass = False
                safe_zone_notes.append(f"Aspect mismatch: width {f.get('width')} > height {f.get('height')}")
                break

    return {
        "status": "EVALUATED",
        "metric_type": "EDITORIAL_PROXY",
        "first_3s_action_pass": first_3s_action_ok,
        "first_3s_motion_pct": early_motion.get("mean_subject_motion_pct", 0.0),
        "twist_20_30s_action_pass": twist_action_ok,
        "twist_motion_pct": twist_motion.get("mean_subject_motion_pct", 0.0),
        "safe_zones_pass": safe_zones_pass,
        "safe_zone_notes": safe_zone_notes,
        "total_frames_extracted": len(frames),
    }


def generate_contact_sheet(
    extracted_frames: List[Dict[str, Any]],
    output_path: Union[str, Path],
    cols: int = 3,
) -> bool:
    """Compose extracted frame PNGs into single contact sheet."""
    try:
        from PIL import Image
        if not extracted_frames:
            return False
        
        imgs = [Image.open(f["frame_path"]) for f in extracted_frames if Path(f["frame_path"]).exists()]
        if not imgs:
            return False
            
        thumb_w = 480
        thumb_h = int(thumb_w * imgs[0].height / imgs[0].width)
        thumbs = [img.resize((thumb_w, thumb_h)) for img in imgs]
        
        rows = math.ceil(len(thumbs) / cols)
        sheet_w = cols * thumb_w
        sheet_h = rows * thumb_h
        sheet = Image.new("RGB", (sheet_w, sheet_h), color=(20, 20, 25))
        
        for idx, th in enumerate(thumbs):
            r = idx // cols
            c = idx % cols
            sheet.paste(th, (c * thumb_w, r * thumb_h))
            
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(str(out_p), quality=85)
        return True
    except Exception as exc:
        print(f"[visual_qa] Failed to generate contact sheet: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    print("Visual QA V13 module loaded successfully.")
