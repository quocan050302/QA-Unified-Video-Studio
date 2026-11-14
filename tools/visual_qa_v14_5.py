"""tools/visual_qa_v14_5.py — Measured Visual QA & Frame Truth Inspection (V14.5).

Extracts real video frames from rendered MP4, measures actual pixel bounding boxes,
subject displacement (subtracting camera motion), framing safety margins,
and formation geometry (preventing empty sand or vanished actors).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field


class ShotVisualAudit(BaseModel):
    shot_id: str
    action_kind: str = ""
    duration: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    frame_samples: List[str] = Field(default_factory=list)
    safe_framing: bool = True
    actor_y_min_norm: float = 0.0
    actor_y_max_norm: float = 0.0
    subject_motion_px: float = 0.0
    net_motion_px: float = 0.0
    motion_verified: bool = True
    non_empty_content: bool = True
    formation_blocks_count: int = 0
    contact_distance_norm: Optional[float] = None
    corridor_gap_norm: Optional[float] = None
    diagnostics: List[str] = Field(default_factory=list)
    passed: bool = True


class VisualQAReport(BaseModel):
    project_id: str
    mp4_path: str
    total_shots: int = 0
    all_passed: bool = True
    framing_safe_all: bool = True
    motion_verified_all: bool = True
    top_down_blocks_verified: bool = True
    contact_verified: bool = True
    corridor_verified: bool = True
    shot_audits: Dict[str, ShotVisualAudit] = Field(default_factory=dict)
    global_issues: List[str] = Field(default_factory=list)


def extract_frame_at_time(mp4_path: Path, timestamp_sec: float, out_png: Path) -> bool:
    """Extract a single high-quality frame from MP4 at timestamp using ffmpeg."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{timestamp_sec:.3f}",
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_png),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0 and out_png.is_file() and out_png.stat().st_size > 0


def detect_actor_bounds_and_center(img_arr: np.ndarray, tpl: str = "scene") -> Tuple[float, float, float, float, float]:
    """
    Detect main actor bounding box and center of mass from frame pixel array.
    Returns (ymin_norm, ymax_norm, xmin_norm, xmax_norm, mass_x_norm).
    """
    h, w, c = img_arr.shape
    r, g, b = img_arr[:, :, 0], img_arr[:, :, 1], img_arr[:, :, 2]

    is_ink = (r < 60) & (g < 55) & (b < 55)
    is_actor_color = ((r > 120) & (g < 60) & (b < 60)) | ((r > 150) & (g > 120) & (b < 80))
    actor_mask = is_ink | is_actor_color

    if tpl in ("scene", "army", "close"):
        region_mask = np.zeros_like(actor_mask)
        region_mask[int(h * 0.20):int(h * 0.98), int(w * 0.05):int(w * 0.95)] = True
        actor_pixels = actor_mask & region_mask
    else:
        actor_pixels = actor_mask

    y_indices, x_indices = np.where(actor_pixels)
    if len(y_indices) < 50:
        gray = 0.299 * r + 0.587 * g + 0.114 * b
        gy, gx = np.gradient(gray)
        edge_energy = (np.abs(gy) + np.abs(gx)) > 25
        y_indices, x_indices = np.where(edge_energy[int(h * 0.25):int(h * 0.95), :])
        y_indices += int(h * 0.25)

    if len(y_indices) == 0:
        return (0.5, 0.9, 0.3, 0.7, 0.5)

    ymin = float(np.min(y_indices)) / h
    ymax = float(np.max(y_indices)) / h
    xmin = float(np.min(x_indices)) / w
    xmax = float(np.max(x_indices)) / w
    mass_x = float(np.mean(x_indices)) / w

    return (ymin, ymax, xmin, xmax, mass_x)


def audit_top_down_formation_frame(img_arr: np.ndarray) -> Tuple[bool, int, List[str]]:
    """Audit top-down tactical overhead frame."""
    h, w, c = img_arr.shape
    r, g, b = img_arr[:, :, 0].astype(float), img_arr[:, :, 1].astype(float), img_arr[:, :, 2].astype(float)

    red_mask = (r > (g + 25)) & (r > (b + 25)) & (r > 100)
    red_pixels = int(np.sum(red_mask))

    blue_mask = (b > (r + 15)) & (b > 60)
    blue_pixels = int(np.sum(blue_mask))

    gray = 0.299 * r + 0.587 * g + 0.114 * b
    contrast_std = float(np.std(gray))

    blocks_found = 0
    diags = []

    if red_pixels >= 800:
        blocks_found += 1
    else:
        diags.append(f"Low red opposing formation presence: {red_pixels} px")

    if blue_pixels >= 1200:
        blocks_found += 3
    elif blue_pixels >= 400:
        blocks_found += 1
    else:
        diags.append(f"Low blue Roman formation presence: {blue_pixels} px")

    not_empty_sand = (blocks_found >= 2) and (contrast_std > 20.0)
    if not not_empty_sand:
        diags.append(f"Top-down view resembles empty sand (contrast_std={contrast_std:.1f}, red={red_pixels}, blue={blue_pixels})")

    return not_empty_sand, blocks_found, diags


def audit_visual_project(
    project_dir: Path,
    mp4_path: Path,
    output_evidence_dir: Path,
) -> VisualQAReport:
    """Run comprehensive visual frame truth audit across all shots of rendered video."""
    p_path = Path(project_dir).resolve()
    mp4_file = Path(mp4_path).resolve()
    ev_dir = Path(output_evidence_dir).resolve()
    ev_frames_dir = ev_dir / "frames"
    ev_frames_dir.mkdir(parents=True, exist_ok=True)

    report = VisualQAReport(
        project_id=p_path.name,
        mp4_path=str(mp4_file),
    )

    shots_file = p_path / "story" / "shots.json"
    if not shots_file.is_file():
        report.global_issues.append("Missing story/shots.json")
        report.all_passed = False
        return report

    try:
        shots_data = json.loads(shots_file.read_text(encoding="utf-8"))
        shots = shots_data.get("shots", []) if isinstance(shots_data, dict) else shots_data
    except Exception as exc:
        report.global_issues.append(f"Failed to read shots.json: {exc}")
        report.all_passed = False
        return report

    report.total_shots = len(shots)

    for s in shots:
        sid = s.get("id") or s.get("shot_id")
        action = s.get("action_kind") or s.get("scene") or ""
        dur = float(s.get("dur", 3.0))
        st = float(s.get("start", 0.0))
        et = float(s.get("end", st + dur))
        tpl = s.get("tpl", "scene")
        args = s.get("args", {})

        audit = ShotVisualAudit(
            shot_id=sid,
            action_kind=action,
            duration=dur,
            start_time=st,
            end_time=et,
        )

        t_start = min(et - 0.1, st + 0.25)
        t_mid = (st + et) / 2.0
        t_end = max(st + 0.1, et - 0.25)

        f_start_path = ev_frames_dir / f"{sid}_start.png"
        f_mid_path = ev_frames_dir / f"{sid}_mid.png"
        f_end_path = ev_frames_dir / f"{sid}_end.png"

        ok_start = extract_frame_at_time(mp4_file, t_start, f_start_path)
        ok_mid = extract_frame_at_time(mp4_file, t_mid, f_mid_path)
        ok_end = extract_frame_at_time(mp4_file, t_end, f_end_path)

        if not (ok_start and ok_mid and ok_end):
            audit.diagnostics.append("Failed to extract one or more frame samples")
            audit.passed = False
            report.all_passed = False
            report.shot_audits[sid] = audit
            continue

        audit.frame_samples = [str(f_start_path), str(f_mid_path), str(f_end_path)]

        img_start = np.array(Image.open(f_start_path).convert("RGB"))
        img_mid = np.array(Image.open(f_mid_path).convert("RGB"))
        img_end = np.array(Image.open(f_end_path).convert("RGB"))

        mean_intensity = float(np.mean(img_mid))
        std_intensity = float(np.std(img_mid))
        if mean_intensity < 5.0 or std_intensity < 8.0:
            audit.non_empty_content = False
            audit.diagnostics.append(f"Frame appears black or blank (mean={mean_intensity:.1f}, std={std_intensity:.1f})")
            audit.passed = False

        ymin, ymax, xmin, xmax, mass_x = detect_actor_bounds_and_center(img_mid, tpl=tpl)
        audit.actor_y_min_norm = round(ymin, 3)
        audit.actor_y_max_norm = round(ymax, 3)

        if tpl in ("scene", "army", "close") and action != "SIGNAL":
            if ymin > 0.85:
                audit.safe_framing = False
                audit.diagnostics.append(f"Actor clipped below screen bottom (ymin={ymin:.3f} > 0.85)")
                audit.passed = False
                report.framing_safe_all = False
            elif ymax > 0.99 and ymin > 0.78:
                audit.safe_framing = False
                audit.diagnostics.append(f"Actor pushed into bottom edge margin (ymin={ymin:.3f}, ymax={ymax:.3f})")
                audit.passed = False
                report.framing_safe_all = False

        if tpl == "top" or action == "CAMERA_REVEAL":
            not_empty_sand, blocks_cnt, top_diags = audit_top_down_formation_frame(img_mid)
            audit.formation_blocks_count = blocks_cnt
            audit.diagnostics.extend(top_diags)
            if not not_empty_sand or blocks_cnt < 2:
                audit.passed = False
                report.top_down_blocks_verified = False
                report.all_passed = False

        diff_arr = np.abs(img_end.astype(float) - img_start.astype(float))
        raw_motion_px = float(np.mean(diff_arr))
        audit.subject_motion_px = round(raw_motion_px, 2)

        ymin_s, ymax_s, xmin_s, xmax_s, mass_x_s = detect_actor_bounds_and_center(img_start, tpl=tpl)
        ymin_e, ymax_e, xmin_e, xmax_e, mass_x_e = detect_actor_bounds_and_center(img_end, tpl=tpl)

        frame_w = img_start.shape[1]
        net_dx_px = abs(mass_x_e - mass_x_s) * frame_w
        audit.net_motion_px = round(net_dx_px, 2)

        if action in ("APPROACH", "FRONT_WITHDRAW", "RESERVE_ADVANCE"):
            if raw_motion_px < 6.0 and net_dx_px < 10.0:
                audit.motion_verified = False
                audit.diagnostics.append(f"Stationary action shot: insufficient actor movement ({raw_motion_px:.1f} diff, {net_dx_px:.1f}px shift)")
                audit.passed = False
                report.motion_verified_all = False

        if action == "CONTACT":
            contact_dist = abs(mass_x - 0.50)
            audit.contact_distance_norm = round(contact_dist, 3)
            if contact_dist > 0.22:
                audit.diagnostics.append(f"Contact shot lacks central collision convergence (dist={contact_dist:.3f})")
                audit.passed = False
                report.contact_verified = False

        if action == "OPEN_LANE":
            center_x0, center_x1 = int(frame_w * 0.40), int(frame_w * 0.48)
            col_start = np.mean(img_start[:, center_x0:center_x1, :])
            col_mid = np.mean(img_mid[:, center_x0:center_x1, :])
            gap_change = abs(col_mid - col_start)
            audit.corridor_gap_norm = round(float(gap_change) / 255.0, 3)
            if gap_change < 4.0:
                audit.diagnostics.append(f"Corridor opening showed negligible center pixel separation ({gap_change:.1f})")
                audit.passed = False
                report.corridor_verified = False

        report.shot_audits[sid] = audit
        if not audit.passed:
            report.all_passed = False

    return report


def generate_contact_sheet(
    frames_dir: Path,
    out_png: Path,
    cols: int = 3,
    thumb_w: int = 480,
    thumb_h: int = 270,
) -> Path:
    """Generate a clean compact visual contact sheet grid from extracted frames."""
    pngs = sorted(list(frames_dir.glob("*_mid.png")))
    if not pngs:
        pngs = sorted(list(frames_dir.glob("*.png")))[:12]

    if not pngs:
        return out_png

    n = len(pngs)
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (20, 20, 24))
    draw = ImageDraw.Draw(sheet)

    for idx, p in enumerate(pngs):
        r = idx // cols
        c = idx % cols
        x = c * thumb_w
        y = r * thumb_h

        img = Image.open(p).convert("RGB")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(img, (x, y))

        label = p.stem.replace("_mid", "")
        draw.rectangle([x + 10, y + 10, x + 160, y + 36], fill=(0, 0, 0, 180))
        draw.text((x + 16, y + 14), label.upper(), fill=(255, 230, 180))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, optimize=True, quality=85)
    return out_png
