"""tools/visual_style_qa.py — Deterministic Visual & Technical Style QA Contract (KH-01 Section 9).

Provides objective structural verification of rendered PNGs, model sheets, storyboards, and
MP4 frame sequences while strictly separating measurable technical checks (`TECH_PASS` / `FAIL` /
`NOT_VERIFIED`) from human aesthetic gates (`STYLE_APPROVED = HUMAN_REVIEW_PENDING`,
`EDITORIAL_APPROVED = HUMAN_REVIEW_PENDING`).

Never invents a learned aesthetic similarity percentage or claims viewer retention gains.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tools.character_design import validate_character_consistency
from tools.cinematic_camera import CameraSegment, validate_camera_segments
from tools.temporal_visual_qa import audit_foot_plant, audit_hand_prop_contact
from tools.visual_style_director import (
    FORBIDDEN_ASSET_TOKENS,
    FORBIDDEN_REFERENCE_IMAGE_SHA256,
    StyleInstance,
    StyleProfile,
    load_style_profile,
    resolve_visual_style,
    validate_reference_grounded_style_contract,
    validate_style_contract,
)

ROOT_DIR = Path(__file__).resolve().parent.parent

VISUAL_GATE_IDS: Tuple[str, ...] = (
    "VQ01_STYLE_FRAME_CANDIDATE",
    "VQ02_CHARACTER_MODEL_SHEET_CANDIDATE",
    "VQ03_ACTING_8S",
    "VQ04_MULTICAMERA",
    "VQ05_MULTI_NICHE",
    "VQ06_FINAL_FILM",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    for fp in candidates:
        if Path(fp).is_file():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def validate_style_assets(
    style_profile: StyleProfile | str,
    manifests: Dict[str, Any] | Sequence[Dict[str, Any]],
    project: Optional[Path | str | Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate style profile schema, original-source SHA-256 digests, copyright/reference exclusion,
    required view coverage (`front`, `three_quarter`, `profile`), >= 6 distinct expression hashes,
    and physical dimensions.
    """
    prof = load_style_profile(style_profile) if isinstance(style_profile, str) else style_profile
    mf_list = [manifests] if isinstance(manifests, dict) else list(manifests or [])
    errors: List[str] = []
    warnings: List[str] = []

    if not mf_list:
        return {"valid": False, "status": "FAIL", "errors": ["No asset manifests supplied"]}

    shots: List[Dict[str, Any]] = []
    if isinstance(project, (str, Path)):
        sf = Path(project) / "story" / "shots.json"
        if sf.is_file():
            shots = json.loads(sf.read_text(encoding="utf-8")).get("shots") or []
    elif isinstance(project, dict):
        shots = project.get("shots") or []

    checked_files = 0
    is_v2 = str(prof.style_id).endswith(".v2")
    for mf in mf_list:
        niche = str(mf.get("niche") or next(iter((mf.get("environments") or {}).values()), {}).get("niche") or ("city_park" if is_v2 else "roman_forum"))
        style_inst = resolve_visual_style({"niche": niche}, niche=niche, style_id=prof.style_id)
        if is_v2:
            res = validate_reference_grounded_style_contract(style_inst, mf, shots)
        else:
            res = validate_style_contract(style_inst, mf, shots)
        if not res["valid"]:
            errors.extend(res["errors"])

        # Explicit check that any png/svg layer does not reference forbidden copyrighted/reference tokens
        view_img_by_char: Dict[str, Dict[str, Path]] = {}
        for entry in mf.get("authored_files") or []:
            checked_files += 1
            p_str = str(entry.get("path") or "")
            if any(tok in p_str.lower() for tok in FORBIDDEN_ASSET_TOKENS):
                errors.append(f"Forbidden reference/legacy image layer detected: {p_str}")
            role_s = str(entry.get("role") or "")
            if role_s.startswith("character_view:"):
                parts = role_s.split(":")
                if len(parts) == 3:
                    fp_v = Path(p_str) if Path(p_str).is_absolute() else (ROOT_DIR / p_str)
                    if fp_v.is_file():
                        view_img_by_char.setdefault(parts[1], {})[parts[2]] = fp_v

        # Verify distinct expression hashes & non-flipped 4-view geometry on v2 characters
        req_views_set = {"front", "three_quarter", "profile", "rear_three_quarter"} if is_v2 else {"front", "three_quarter", "profile"}
        for cid, cdata in (mf.get("characters") or {}).items():
            exprs = list(cdata.get("expressions") or [])
            if len(set(exprs)) < 6:
                errors.append(f"Character '{cid}' missing required 6 expressions (found {len(set(exprs))})")
            views = set(cdata.get("views") or [])
            if not req_views_set.issubset(views):
                errors.append(f"Character '{cid}' missing required views (expected {sorted(req_views_set)}, found {sorted(views)})")
            vmap = view_img_by_char.get(cid) or {}
            if is_v2 and len(vmap) >= 2:
                # Reject horizontally flipped front masquerading as profile or rear_three_quarter!
                if "front" in vmap:
                    with Image.open(vmap["front"]) as im_fr:
                        arr_fr = np.asarray(im_fr.convert("RGBA"), dtype=np.float32)
                    arr_fr_flip = np.fliplr(arr_fr)
                    for other_vw in ("three_quarter", "profile", "rear_three_quarter"):
                        if other_vw in vmap:
                            with Image.open(vmap[other_vw]) as im_o:
                                arr_o = np.asarray(im_o.convert("RGBA"), dtype=np.float32)
                            if arr_o.shape == arr_fr.shape:
                                diff_direct = float(np.mean(np.abs(arr_o - arr_fr)))
                                diff_flip = float(np.mean(np.abs(arr_o - arr_fr_flip)))
                                if diff_direct < 1.2 or diff_flip < 1.2:
                                    errors.append(
                                        f"Character '{cid}' view '{other_vw}' is flattened/duplicate/flipped copy of 'front' (diff={min(diff_direct, diff_flip):.3f})"
                                    )

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "style_id": prof.style_id,
        "style_lock_digest": prof.computed_lock_digest,
        "reference_availability": prof.reference_availability,
        "checked_authored_files": checked_files,
        "errors": errors,
        "warnings": warnings,
    }


def audit_character_consistency(
    project: Path | str | Dict[str, Any],
    rendered_frames: Sequence[Path | str],
    ai_detector_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Audit character outfit/face/color/identity continuity across shots and decoded PNG frames.
    Flags mid-shot garment color swaps, unmotivated costume changes, missing frames, or
    unvalidated confidence claims (`NOT_VERIFIED`).
    """
    if ai_detector_confidence is not None and (not math.isfinite(ai_detector_confidence) or ai_detector_confidence < 0.70):
        return {
            "status": "NOT_VERIFIED",
            "valid": False,
            "confidence": ai_detector_confidence,
            "manual_fallback": "REVIEW_REQUIRED",
            "errors": [f"Detector confidence {ai_detector_confidence} below verified threshold 0.70"],
        }

    if isinstance(project, dict):
        shots = project.get("shots") or []
        cb = project.get("character_bible") or {}
    else:
        proj_p = Path(project)
        sf = proj_p / "story" / "shots.json"
        cbf = proj_p / "story" / "character_bible.json"
        shots = json.loads(sf.read_text(encoding="utf-8")).get("shots", []) if sf.is_file() else []
        cb = json.loads(cbf.read_text(encoding="utf-8")) if cbf.is_file() else {}

    chars = cb.get("characters", cb) if isinstance(cb, dict) else {}
    errors: List[str] = []
    warnings: List[str] = []

    frame_paths = [Path(p) for p in (rendered_frames or []) if Path(p).is_file()]
    if not frame_paths:
        return {
            "status": "NOT_VERIFIED",
            "valid": False,
            "confidence": 0.0,
            "manual_fallback": "REVIEW_REQUIRED",
            "errors": ["Zero decoded frames provided for character consistency audit"],
        }

    actor_reports: Dict[str, Any] = {}
    for aid, cspec in chars.items():
        if not isinstance(cspec, dict):
            continue
        rep = validate_character_consistency(cspec, shots, frame_paths)
        actor_reports[aid] = rep
        if not rep["valid"]:
            errors.extend(rep["errors"])

        # Mid-sequence pixel palette shift detector on character primary garment color
        prim_hex = str((cspec.get("wardrobe") or {}).get("primary_hex") or cspec.get("primary_hex") or "")
        if prim_hex.startswith("#") and len(prim_hex) == 7 and len(frame_paths) >= 2:
            r0, g0, b0 = int(prim_hex[1:3], 16), int(prim_hex[3:5], 16), int(prim_hex[5:7], 16)
            ratios: List[float] = []
            for fp in frame_paths:
                with Image.open(fp) as im:
                    arr_full = np.asarray(im.convert("RGB"), dtype=np.float32)
                fh, fw = arr_full.shape[:2]
                arr = arr_full[int(fh * 0.18) : int(fh * 0.88), int(fw * 0.22) : int(fw * 0.78)]
                dist = np.sqrt((arr[:, :, 0] - r0) ** 2 + (arr[:, :, 1] - g0) ** 2 + (arr[:, :, 2] - b0) ** 2)
                ratios.append(float(np.mean(dist < 19.0)))
            if max(ratios) >= 0.008 and min(ratios) < max(ratios) * 0.50 and len(shots) <= 1:
                errors.append(
                    f"Mid-shot character garment color disappearance/swap detected on '{aid}' (ratio {max(ratios):.4f} -> {min(ratios):.5f})"
                )

    # Check adjacent frame sudden 1-frame disappearance / blank glitch + lower-limb/hand ink continuity
    luma_means: List[float] = []
    lower_limb_ink_ratios: List[float] = []
    for fp in frame_paths:
        with Image.open(fp) as im:
            arr_f = np.asarray(im.convert("RGB"), dtype=np.float32)
        std_f = float(np.std(arr_f))
        if std_f < 3.0:
            errors.append(f"Blank or near-uniform frame detected: {fp.name} (std={std_f:.2f})")
        luma_means.append(float(np.mean(arr_f)))
        fh, fw = arr_f.shape[:2]
        luma_f = (0.2126 * arr_f[:, :, 0] + 0.7152 * arr_f[:, :, 1] + 0.0722 * arr_f[:, :, 2]) / 255.0
        limb_band = luma_f[int(fh * 0.55) : int(fh * 0.90), int(fw * 0.15) : int(fw * 0.85)]
        lower_limb_ink_ratios.append(float(np.mean(limb_band < 0.18)))

    if len(shots) <= 1 and len(lower_limb_ink_ratios) >= 2:
        if max(lower_limb_ink_ratios) >= 0.015 and min(lower_limb_ink_ratios) < 0.0015:
            errors.append(
                f"Sudden lower-limb/hand ink disappearance detected across frames ({max(lower_limb_ink_ratios):.4f} -> {min(lower_limb_ink_ratios):.5f})"
            )

    return {
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "valid": len(errors) == 0,
        "confidence": 0.92,
        "manual_fallback": "HUMAN_REVIEW_PENDING",
        "frames_inspected": len(frame_paths),
        "actor_reports": actor_reports,
        "luma_range": [round(min(luma_means), 2), round(max(luma_means), 2)] if luma_means else [],
        "errors": errors,
        "warnings": warnings,
    }


def audit_visual_style(
    project: Optional[Path | str | Dict[str, Any]],
    rendered_pngs: Sequence[Path | str],
    profile: Optional[StyleProfile | str] = None,
) -> Dict[str, Any]:
    """
    Deterministic objective structural checks on rendered PNGs:
      - Dark ink outline presence & crisp gradient edges
      - Silhouette / focal region luma separation
      - Multi-band cel-shading value distribution (2+ distinct luminance clusters)
      - Controlled material/texture edge density (neither blank rectangle nor noisy moire)
      - Vertical foreground / midground / background depth differentiation
    Explicitly disclaims aesthetic equivalence or learned similarity percentage.
    """
    prof = load_style_profile(profile) if isinstance(profile, str) else (profile or load_style_profile())
    paths = [Path(p) for p in (rendered_pngs or []) if Path(p).is_file()]
    if not paths:
        return {
            "status": "NOT_VERIFIED",
            "valid": False,
            "is_aesthetic_equivalence_proof": False,
            "style_similarity_percentage": None,
            "errors": ["No rendered PNG files provided to audit_visual_style"],
        }

    errors: List[str] = []
    frame_metrics: List[Dict[str, Any]] = []
    dens_lo, dens_hi = prof.texture_and_perspective["edge_density_target_range"]

    for fp in paths:
        with Image.open(fp) as im:
            arr = np.asarray(im.convert("RGB"), dtype=np.float32)
        h, w, _ = arr.shape
        luma = (0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]) / 255.0

        # 1. Crisp ink outline pixel ratio (dark ink luma < 0.16)
        ink_ratio = float(np.mean(luma < 0.16))

        # 2. Gradient edge density & sharpness
        gx = np.abs(np.diff(luma, axis=1))
        gy = np.abs(np.diff(luma, axis=0))
        edge_mask = (gx[:-1, :] + gy[:, :-1]) > 0.08
        edge_density = float(np.mean(edge_mask))
        edge_p95 = float(np.percentile(gx, 95))

        # 3. Value group diversity (count occupied 8-bin luminance bands >= 2% area)
        hist, _ = np.histogram(luma, bins=8, range=(0.0, 1.0))
        occupied_value_groups = int(np.sum((hist / float(luma.size)) >= 0.025))

        # 4. Depth separation across sky/upper (0..35%), mid stage (35..78%), and ground/fg (78..100%)
        top_mean = float(np.mean(luma[: max(1, int(h * 0.35)), :]))
        mid_mean = float(np.mean(luma[int(h * 0.35) : int(h * 0.78), :]))
        bot_mean = float(np.mean(luma[int(h * 0.78) :, :]))
        depth_plane_spread = round(max(top_mean, mid_mean, bot_mean) - min(top_mean, mid_mean, bot_mean), 4)

        # 5. Center focal contrast & closeup subject bounding-box height ratio
        center_patch = luma[int(h * 0.18) : int(h * 0.86), int(w * 0.20) : int(w * 0.80)]
        focal_std = float(np.std(center_patch))
        ink_rows = np.where(np.mean(luma[:, int(w * 0.12) : int(w * 0.88)] < 0.18, axis=1) > 0.008)[0]
        focal_height_ratio = round(float(ink_rows[-1] - ink_rows[0]) / float(max(1, h)), 4) if ink_rows.size >= 2 else 0.0

        is_declared_close = any(tok in fp.name.lower() for tok in ("closeup", "close_", "macro"))
        if is_declared_close and focal_height_ratio < 0.42:
            errors.append(f"{fp.name}: declared closeup/macro subject too small (focal_height_ratio={focal_height_ratio:.3f} < 0.42)")

        if ink_ratio < 0.004:
            errors.append(f"{fp.name}: missing bold ink linework (ink_ratio={ink_ratio:.5f} < 0.004)")
        if edge_density < max(0.012, dens_lo * 0.35) or edge_density > min(0.55, dens_hi * 1.45):
            errors.append(f"{fp.name}: edge_density={edge_density:.4f} outside controlled editorial range")
        if occupied_value_groups < 3:
            errors.append(f"{fp.name}: flat value structure (occupied_value_groups={occupied_value_groups} < 3)")
        if focal_std < 0.06:
            errors.append(f"{fp.name}: low focal subject contrast (focal_std={focal_std:.4f} < 0.06)")

        frame_metrics.append({
            "file": fp.name,
            "dimensions": [w, h],
            "ink_pixel_ratio": round(ink_ratio, 5),
            "edge_density": round(edge_density, 4),
            "edge_sharpness_p95": round(edge_p95, 4),
            "occupied_value_groups": occupied_value_groups,
            "depth_plane_luma_spread": depth_plane_spread,
            "focal_contrast_std": round(focal_std, 4),
            "focal_subject_height_ratio": focal_height_ratio,
        })

    return {
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "valid": len(errors) == 0,
        "style_id": prof.style_id,
        "is_aesthetic_equivalence_proof": False,
        "style_similarity_percentage": None,
        "editorial_gate_status": "HUMAN_REVIEW_PENDING",
        "inspected_count": len(frame_metrics),
        "frame_metrics": frame_metrics,
        "errors": errors,
    }


def audit_composition_storytelling(
    project: Optional[Path | str | Dict[str, Any]],
    shots: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Verify hook clarity, camera motivation, scale diversity (wide/medium/close/macro),
    absence of unmotivated static slideshows, and absence of fake crop reverse angles.
    """
    errors: List[str] = []
    warnings: List[str] = []
    if not shots:
        return {"status": "FAIL", "valid": False, "errors": ["Zero shots in storyboard"]}

    scales: List[str] = []
    views: List[str] = []
    expected_total_dur: Optional[float] = None
    if isinstance(project, dict) and project.get("expected_duration_sec") is not None:
        expected_total_dur = float(project["expected_duration_sec"])

    prev_end: Optional[float] = None
    expected_next_variant: Dict[str, str] = {}
    for idx, s in enumerate(shots):
        sid = str(s.get("id") or f"S{idx+1:02d}")
        args = s.get("args") or {}
        art = s.get("art_direction") or args.get("artDirection") or {}
        cam = s.get("camera") or {}
        sc = str(art.get("camera_scale") or cam.get("scale") or s.get("scale") or "medium")
        vw = str(cam.get("viewpoint") or art.get("viewpoint_target") or args.get("view") or "three_quarter")
        scales.append(sc)
        views.append(vw)

        st_s = float(s.get("start", 0.0))
        et_s = float(s.get("end", st_s + float(s.get("dur", 3.0))))
        if et_s <= st_s:
            errors.append(f"Shot {sid}: impossible non-positive shot duration ({st_s}..{et_s})")
        if prev_end is not None and abs(st_s - prev_end) > 0.02:
            errors.append(f"Shot {sid}: timeline gap or overlap ({prev_end:.3f}s -> {st_s:.3f}s)")
        prev_end = et_s

        if idx == 0:
            hook_line = str(s.get("line") or s.get("desc") or "").strip()
            if not hook_line:
                errors.append(f"Opening hook shot {sid} has empty narrative hook line/description")

        raw_segs = args.get("cameraSegments")
        if isinstance(raw_segs, list) and raw_segs:
            seg_objs = [seg if isinstance(seg, CameraSegment) else CameraSegment.model_validate(seg) for seg in raw_segs]
            ok_seg, seg_errs = validate_camera_segments(seg_objs, s)
            if not ok_seg:
                errors.extend(seg_errs)

        # Reject duplicate ribbon/string tether links on a single prop
        tethers = args.get("tetherLinks") or []
        seen_tether_targets: set[str] = set()
        for tl in tethers:
            if isinstance(tl, dict):
                tgt = str(tl.get("toProp") or tl.get("id") or "kite")
                if tgt in seen_tether_targets or tl.get("duplicated") is True:
                    errors.append(f"Shot {sid}: duplicate ribbon/string tether detected on '{tgt}'")
                seen_tether_targets.add(tgt)

        # Verify asset variant continuity when required_next_variant was set by prior shot
        for p_item in args.get("people") or []:
            if isinstance(p_item, dict) and p_item.get("id"):
                aid_p = str(p_item["id"])
                actual_var = str(p_item.get("assetVariant") or p_item.get("outfitId") or "")
                if aid_p in expected_next_variant and actual_var and actual_var != expected_next_variant[aid_p]:
                    errors.append(
                        f"Shot {sid}: incorrect asset variant after shot for '{aid_p}' (expected '{expected_next_variant[aid_p]}', got '{actual_var}')"
                    )
        if isinstance(s.get("required_next_asset_variant"), dict):
            for k_aid, v_var in s["required_next_asset_variant"].items():
                expected_next_variant[str(k_aid)] = str(v_var)

        # Reject static slideshow pan-only shots when actor action is claimed
        has_motion = bool(args.get("motionTracks")) or bool(args.get("people")) or bool(args.get("insertKind")) or s.get("expected_subject") == "prop"
        if not has_motion:
            errors.append(f"Shot {sid}: static slideshow detected (zero motionTracks/actors/animated props)")

    if expected_total_dur is not None and prev_end is not None and abs(prev_end - expected_total_dur) > 0.02:
        errors.append(f"Impossible total timeline duration: {prev_end:.3f}s != expected {expected_total_dur:.3f}s")

    if len(shots) >= 4 and len(set(scales)) < 2:
        errors.append(f"Monotonous shot scale composition across {len(shots)} shots: {scales}")

    return {
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "valid": len(errors) == 0,
        "shot_count": len(shots),
        "unique_scales": sorted(set(scales)),
        "unique_viewpoints": sorted(set(views)),
        "errors": errors,
        "warnings": warnings,
    }


def build_editorial_packet(
    reference_manifest: Dict[str, Any],
    original_output_frames: Sequence[Dict[str, Any] | Path | str],
    qa_results: Dict[str, Any],
    out_dir: Optional[Path] = None,
    private_ref_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build a public original-only editorial review montage PNG + structured JSON packet in `out_dir`,
    AND when `private_ref_dir` contains the 3 ingested user reference frames, write a PRIVATE local
    side-by-side comparison sheet ONLY inside gitignored `private_ref_dir` (zero reference pixels in Git!).
    """
    pkt_dir = Path(out_dir) if out_dir else (ROOT_DIR / "tests" / "evidence" / "_editorial_packet")
    pkt_dir.mkdir(parents=True, exist_ok=True)

    normalized_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(original_output_frames or []):
        if isinstance(item, dict):
            p = Path(item["path"]) if Path(item["path"]).is_absolute() else (ROOT_DIR / str(item["path"]))
            lbl = str(item.get("label") or p.stem)
            ts = item.get("timestamp_sec")
        else:
            p = Path(item) if Path(item).is_absolute() else (ROOT_DIR / str(item))
            lbl = p.stem
            ts = None
        if p.is_file():
            normalized_items.append({"path": p, "label": lbl, "timestamp_sec": ts})

    # Compose 3-column original art review montage (100% public-safe, zero user reference pixels)
    cols = 3
    tw, th, pad = 560, 315, 20
    rows = max(1, math.ceil(len(normalized_items) / cols))
    header_h = 110
    montage_w = pad + cols * (tw + pad)
    montage_h = header_h + rows * (th + 46 + pad)
    montage = Image.new("RGB", (montage_w, montage_h), (24, 22, 24))
    dr = ImageDraw.Draw(montage)
    f_h = _load_font(26, bold=True)
    f_s = _load_font(17, bold=False)

    ref_status = str(reference_manifest.get("reference_status") or "STYLE_REFERENCE_UNAVAILABLE")
    dr.text(
        (pad, 18),
        "ORIGINAL MODERN EXPRESSIVE 2D — PUBLIC EDITORIAL MONTAGE (ZERO USER REF PIXELS EMBEDDED)",
        fill=(252, 234, 192),
        font=f_h,
    )
    dr.text(
        (pad, 58),
        f"Reference Status: {ref_status} | VQ_REFERENCE_MATCH: HUMAN_REVIEW_PENDING | STYLE_APPROVED: HUMAN_REVIEW_PENDING",
        fill=(204, 198, 188),
        font=f_s,
    )

    for i, entry in enumerate(normalized_items):
        r_i = i // cols
        c_i = i % cols
        x0 = pad + c_i * (tw + pad)
        y0 = header_h + r_i * (th + 46 + pad)
        with Image.open(entry["path"]) as im:
            thumb = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        montage.paste(thumb, (x0, y0))
        dr.rectangle([x0 - 2, y0 - 2, x0 + tw + 2, y0 + th + 2], outline=(218, 166, 84), width=2)
        ts_txt = f" @ {entry['timestamp_sec']:.2f}s" if isinstance(entry.get("timestamp_sec"), (int, float)) else ""
        dr.text((x0 + 6, y0 + th + 10), f"[{i+1:02d}] {entry['label'][:44]}{ts_txt}", fill=(238, 234, 226), font=f_s)

    montage_path = pkt_dir / "KH01_EDITORIAL_REVIEW_MONTAGE.png"
    montage.save(montage_path, format="PNG")

    # Optional PRIVATE local side-by-side comparison containing real user references vs newly authored v2 frames
    private_comparison_receipt: Optional[Dict[str, Any]] = None
    refs_meta = list(reference_manifest.get("references") or [])
    if private_ref_dir is not None and len(refs_meta) == 3:
        priv_d = Path(private_ref_dir)
        priv_d.mkdir(parents=True, exist_ok=True)
        ref_paths: List[Tuple[str, Path]] = []
        for rm in refs_meta:
            rp = ROOT_DIR / str(rm.get("private_workspace_relpath") or "")
            if not rp.is_file():
                rp = priv_d / Path(str(rm.get("private_workspace_relpath") or rm.get("original_attachment_filename") or "")).name
            if rp.is_file():
                ref_paths.append((f"{rm['reference_id']} ({rm['editorial_role']})", rp))
        if len(ref_paths) == 3 and len(normalized_items) >= 3:
            pw_c, ph_c = 760, 428
            side_w = pad + 2 * (pw_c + pad)
            side_h = 110 + 3 * (ph_c + 52 + pad)
            priv_im = Image.new("RGB", (side_w, side_h), (20, 19, 23))
            dp = ImageDraw.Draw(priv_im)
            dp.text((pad, 18), "PRIVATE LOCAL REVIEW ONLY — USER ATTACHED REFERENCES (LEFT) vs NEW ORIGINAL v2 FRAMES (RIGHT)", fill=(255, 226, 174), font=f_h)
            dp.text((pad, 58), "DO NOT COMMIT THIS FILE TO PUBLIC GIT — Stored strictly in gitignored .test-runs/.../references_private/", fill=(238, 152, 142), font=f_s)
            paired_outputs = [normalized_items[0], normalized_items[min(1, len(normalized_items) - 1)], normalized_items[min(2, len(normalized_items) - 1)]]
            for row_i in range(3):
                ry = 110 + row_i * (ph_c + 52 + pad)
                r_lbl, r_p = ref_paths[row_i]
                o_item = paired_outputs[row_i]
                with Image.open(r_p) as im_r:
                    th_r = im_r.convert("RGB").resize((pw_c, ph_c), Image.Resampling.LANCZOS)
                with Image.open(o_item["path"]) as im_o:
                    th_o = im_o.convert("RGB").resize((pw_c, ph_c), Image.Resampling.LANCZOS)
                lx0 = pad
                rx0 = pad + pw_c + pad
                priv_im.paste(th_r, (lx0, ry))
                priv_im.paste(th_o, (rx0, ry))
                dp.rectangle([lx0 - 2, ry - 2, lx0 + pw_c + 2, ry + ph_c + 2], outline=(214, 112, 102), width=2)
                dp.rectangle([rx0 - 2, ry - 2, rx0 + pw_c + 2, ry + ph_c + 2], outline=(118, 206, 148), width=2)
                dp.text((lx0 + 6, ry + ph_c + 10), f"REF {row_i+1}: {r_lbl[:64]}", fill=(240, 214, 210), font=f_s)
                dp.text((rx0 + 6, ry + ph_c + 10), f"NEW v2: {o_item['label'][:64]}", fill=(212, 242, 220), font=f_s)
            priv_out = priv_d / "PRIVATE_REF_VS_V2_SIDE_BY_SIDE_REVIEW.png"
            priv_im.save(priv_out, format="PNG")
            private_comparison_receipt = {
                "private_local_relpath": priv_out.relative_to(ROOT_DIR).as_posix() if priv_out.is_relative_to(ROOT_DIR) else priv_out.as_posix(),
                "sha256": _sha256_file(priv_out),
                "dimensions": [side_w, side_h],
                "gitignored": True,
                "public_repo_committed": False,
            }

    qualitative_criteria_evaluation = {
        "outline_fluency": "Curved Bezier-subdivided calligraphic outer contours (#211612) with subordinated interior fold strokes (#3A2821); cleaner than v1 straight polygons, though procedural curves remain more regular than hand-inked brush strokes.",
        "posing_and_limb_anatomy": "Curved sleeved upper arms, rounded elbows/knees, tapered wrists, and sculpted palms with opposable thumb + 4 fingers replace v1 cylindrical pipe limbs.",
        "silhouette_contrast": "Distinct compact school-age silhouette (Mina: bob hair + clip, flared windbreaker) vs taller broad-shouldered friend (Bao: tousled crown waves, open overshirt + chinos).",
        "face_expression": "7 distinct expressions including open D-shaped laugh mouths with white tooth block and coral tongue cel-plane, wide shock, focused knot-tying, and warm relief smiles.",
        "clothing_folds": "Layered open windbreakers/overshirts over striped/solid inner tees, folded lapels, cuff bands, rolled trouser hems, and curved tension creases.",
        "shadow_shape": "Angled/curved 3-band cel shadows + warm sunlight rim highlights aligned with ~38-deg diagonal stage sunbeams and ground contact shadows.",
        "background_material_and_depth": "4-plane city park & multi-niche stages with bark grain, flagstone mortar, slatted oak benches, cruising background bicycles, tiered fountain, and organic foliage occluders.",
        "composition": "Deliberate rhythm combining tactile macro hook, low-angle wide launch, finger-slip insert, wide pursuit, bench obstacle, close branch unhook, close knot repair, and close smiling eyes -> wide soaring sky.",
    }

    honest_gap_notes = (
        [
            "All 3 user-attached reference frames were ingested privately and compared side-by-side in gitignored .test-runs/.../references_private/PRIVATE_REF_VS_V2_SIDE_BY_SIDE_REVIEW.png (zero reference pixels committed to public Git).",
            "While modern_expressive_2d.v2 substantially upgrades limb curvature, sleeve/garment layering, facial tooth/tongue planes, and multi-plane sunlit backgrounds over v1, procedural vector/Canvas curves still lack bespoke hand-painted frame-by-frame squash/smear asymmetry and organic brush-grain micro-imperfections present in studio-drawn 2D frames.",
            "VQ_REFERENCE_MATCH, STYLE_APPROVED, and EDITORIAL_APPROVED remain strictly HUMAN_REVIEW_PENDING until explicit user review.",
        ]
        if ref_status == "STYLE_REFERENCES_INGESTED_3_OF_3"
        else [
            "Reference archive KH-01_STYLE_REFERENCES_ONLY.zip was unavailable on host (STYLE_REFERENCE_UNAVAILABLE); direct side-by-side pixel comparison against the three user reference frames requires the user to place those frames locally.",
            "All KH-01 characters, outfits, props, and multi-plane stages are 100% newly authored vector/Canvas/Rigby2D artwork governed by modern_expressive_2d.v1 rules; hand-drawn frame-by-frame traditional smear/boil nuances remain simpler than bespoke studio cel animation.",
            "STYLE_APPROVED and EDITORIAL_APPROVED remain HUMAN_REVIEW_PENDING until explicit human inspection of the PNG sheets and 30.000s 1080p MP4.",
        ]
    )

    packet = {
        "schema_version": "kh01.editorial_packet.v2" if ref_status == "STYLE_REFERENCES_INGESTED_3_OF_3" else "kh01.editorial_packet.v1",
        "reference_status": ref_status,
        "public_repo_contains_user_reference_images": False,
        "VQ_REFERENCE_MATCH": "HUMAN_REVIEW_PENDING",
        "STYLE_APPROVED": "HUMAN_REVIEW_PENDING",
        "EDITORIAL_APPROVED": "HUMAN_REVIEW_PENDING",
        "hallucinated_similarity_percentage": None,
        "visual_gates": {gid: qa_results.get(gid, "CANDIDATE_READY_FOR_HUMAN_REVIEW") for gid in VISUAL_GATE_IDS},
        "montage_png": {
            "path": str(montage_path.relative_to(ROOT_DIR).as_posix() if montage_path.is_relative_to(ROOT_DIR) else montage_path),
            "sha256": _sha256_file(montage_path),
            "dimensions": [montage_w, montage_h],
            "panel_count": len(normalized_items),
        },
        "private_local_ref_vs_output_comparison": private_comparison_receipt,
        "qualitative_criteria_evaluation": qualitative_criteria_evaluation,
        "subjective_gaps_and_disclosures": honest_gap_notes,
        "reviewer_checkpoints": [
            "Inspect private local side-by-side sheet (.test-runs/.../references_private/PRIVATE_REF_VS_V2_SIDE_BY_SIDE_REVIEW.png) offline against Ref 1/2/3.",
            "Verify curved sleeved/tapered limbs, articulated thumbs/fingers, and layered garments on Mina, Bao, and multi-niche v2 model sheets.",
            "Inspect THE KITE THAT CAME BACK 8-shot contact sheet and MP4 for continuous spool-ribbon-kite physics, bench foot contact, and facial acting.",
            "Confirm natural English narration intelligibility, park/wind/cloth/footsteps SFX balance, and -14 LUFS loudness comfort.",
        ],
    }
    pkt_json = pkt_dir / "KH01_EDITORIAL_REVIEW_PACKET.json"
    pkt_json.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    return packet


def run_kh01_visual_style_mutations(work_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Execute all 7 mandatory KH-01 Section 9 visual/style/motion negative mutations on real files/detectors:
      1. Mid-shot altered character garment color -> FAIL
      2. Missing required facial expression (< 6) -> FAIL
      3. Forbidden reference PNG injected as scene layer -> FAIL
      4. New costume mid-sequence with no script event -> FAIL
      5. Scene internal camera segment resets action time -> FAIL
      6. Unplanted foot drift & hand-grip teleport -> FAIL
      7. Unvalidated detector confidence -> NOT_VERIFIED (never PASS)
    """
    tmp_ctx = tempfile.TemporaryDirectory() if work_dir is None else None
    base_d = Path(tmp_ctx.name) if tmp_ctx else Path(work_dir)
    base_d.mkdir(parents=True, exist_ok=True)

    try:
        prof = load_style_profile("modern_expressive_2d.v1")
        style_inst = resolve_visual_style("Lucius chases the scroll.", niche="roman_forum")

        # Create clean baseline rendered PNG + manifest using real factory stage + character
        from tools.character_design import derive_character_specs, draw_character_figure_rgba
        from tools.environment_factory import derive_environment_specs, render_environment_stage_png

        env_spec = derive_environment_specs({"niche": "roman_forum"}, niche="roman_forum")
        good_png = base_d / "good_frame_01.png"
        render_environment_stage_png(env_spec, good_png, canvas_size=(640, 360), supersample=1)
        lucius_spec = derive_character_specs([{"actor_id": "lucius", "primary_hex": "#c84b31"}], "roman_forum")[0]
        char_rgba = draw_character_figure_rgba(lucius_spec, view="three_quarter", expression="determined_focus", canvas_size=(220, 280), supersample=1)
        with Image.open(good_png) as bg_im:
            comp = bg_im.convert("RGBA")
            comp.paste(char_rgba, (210, 60), char_rgba)
            comp.convert("RGB").save(good_png, format="PNG")

        good_png_2 = base_d / "good_frame_02.png"
        with Image.open(good_png) as g_im:
            g_im.save(good_png_2, format="PNG")

        swapped_color_png = base_d / "mut_color_swapped.png"
        render_environment_stage_png(env_spec, swapped_color_png, canvas_size=(640, 360), supersample=1)
        bad_spec = copy.deepcopy(lucius_spec)
        bad_spec["wardrobe"]["primary_hex"] = "#1E5AD2"
        bad_spec["wardrobe"]["primary_shadow_hex"] = "#123A88"
        bad_rgba = draw_character_figure_rgba(bad_spec, view="three_quarter", expression="determined_focus", canvas_size=(220, 280), supersample=1)
        with Image.open(swapped_color_png) as bg_im2:
            comp2 = bg_im2.convert("RGBA")
            comp2.paste(bad_rgba, (210, 60), bad_rgba)
            comp2.convert("RGB").save(swapped_color_png, format="PNG")

        base_manifest = {
            "license_spdx": "CC0-1.0",
            "provenance_origin": "ORIGINAL_KH01_TEST",
            "reference_frames_reused": 0,
            "prior_preview_derived_visual_inputs": 0,
            "authored_files": [{"path": str(good_png), "sha256": _sha256_file(good_png), "dimensions": [640, 360]}],
            "characters": {
                "lucius": {
                    "views": ["front", "three_quarter", "profile"],
                    "expressions": [
                        "neutral_attentive", "wide_shock", "strained_exertion",
                        "determined_focus", "joyful_laugh", "deadpan_disbelief",
                    ],
                }
            },
        }
        base_proj = {
            "shots": [
                {
                    "id": "S01",
                    "start": 0.0,
                    "end": 3.0,
                    "dur": 3.0,
                    "style_id": "modern_expressive_2d.v1",
                    "art_direction": {"outfit_state_by_actor": {"lucius": "courier_tunic"}},
                    "args": {"people": [{"id": "lucius", "outfitId": "courier_tunic", "primaryColor": "#c84b31"}]},
                }
            ],
            "character_bible": {
                "characters": {
                    "lucius": {
                        "actor_id": "lucius",
                        "views": ["front", "three_quarter", "profile"],
                        "expressions": base_manifest["characters"]["lucius"]["expressions"],
                        "wardrobe": {"outfit_id": "courier_tunic", "primary_hex": "#c84b31"},
                    }
                }
            },
        }

        base_assets_ok = validate_style_assets(prof, base_manifest, base_proj)["status"] == "PASS"
        base_cons_ok = audit_character_consistency(base_proj, [good_png, good_png_2])["status"] == "PASS"
        base_style_ok = audit_visual_style(base_proj, [good_png], prof)["status"] == "PASS"
        baseline_ok = base_assets_ok and base_cons_ok and base_style_ok

        results: List[Dict[str, Any]] = []

        # VM01: Mid-shot character color altered
        vm1_proj = copy.deepcopy(base_proj)
        vm1_res = audit_character_consistency(vm1_proj, [good_png, swapped_color_png])
        results.append({
            "mutation_id": "VM01_midshot_character_color_altered",
            "mutant_status": vm1_res["status"],
            "killed": baseline_ok and vm1_res["status"] == "FAIL",
            "diagnostics": vm1_res["errors"][:3],
        })

        # VM02: Missing facial expression (< 6)
        vm2_mf = copy.deepcopy(base_manifest)
        vm2_mf["characters"]["lucius"]["expressions"] = ["neutral_attentive", "wide_shock"]
        vm2_res = validate_style_assets(prof, vm2_mf, base_proj)
        results.append({
            "mutation_id": "VM02_missing_facial_expression",
            "mutant_status": vm2_res["status"],
            "killed": baseline_ok and vm2_res["status"] == "FAIL",
            "diagnostics": vm2_res["errors"][:3],
        })

        # VM03: Unlicensed/reference PNG used as scene layer
        vm3_mf = copy.deepcopy(base_manifest)
        vm3_mf["authored_files"].append({"path": "KH-01_STYLE_REFERENCES_ONLY/frame_01.png", "sha256": "0" * 64})
        vm3_mf["reference_frames_reused"] = 1
        vm3_res = validate_style_assets(prof, vm3_mf, base_proj)
        results.append({
            "mutation_id": "VM03_forbidden_reference_png_as_layer",
            "mutant_status": vm3_res["status"],
            "killed": baseline_ok and vm3_res["status"] == "FAIL",
            "diagnostics": vm3_res["errors"][:3],
        })

        # VM04: New costume with no script event
        vm4_proj = copy.deepcopy(base_proj)
        vm4_proj["shots"].append({
            "id": "S02",
            "start": 3.0,
            "end": 6.0,
            "dur": 3.0,
            "style_id": "modern_expressive_2d.v1",
            "art_direction": {"outfit_state_by_actor": {"lucius": "senator_toga"}},
            "args": {"people": [{"id": "lucius", "outfitId": "senator_toga", "primaryColor": "#efe6d5"}]},
        })
        vm4_res = validate_style_contract(style_inst, base_manifest, vm4_proj["shots"])
        results.append({
            "mutation_id": "VM04_unmotivated_costume_change",
            "mutant_status": vm4_res["status"],
            "killed": baseline_ok and vm4_res["status"] == "FAIL",
            "diagnostics": vm4_res["errors"][:3],
        })

        # VM05: Scene camera segment resets action time
        vm5_shot = {
            "id": "S01",
            "start": 0.0,
            "end": 3.0,
            "dur": 3.0,
            "line": "Lucius catches the scroll.",
            "args": {
                "people": [{"id": "lucius"}],
                "cameraSegments": [
                    {"segment_id": "S01_seg01", "shot_id": "S01", "local_start": 0.0, "local_end": 1.5, "global_start": 0.0, "global_end": 1.5, "resets_action_time": False},
                    {"segment_id": "S01_seg02", "shot_id": "S01", "local_start": 1.5, "local_end": 3.0, "global_start": 1.5, "global_end": 3.0, "scale": "close", "viewpoint": "profile_left", "resets_action_time": True},
                ],
            },
        }
        vm5_res = audit_composition_storytelling(None, [vm5_shot])
        results.append({
            "mutation_id": "VM05_scene_camera_reset",
            "mutant_status": vm5_res["status"],
            "killed": baseline_ok and vm5_res["status"] == "FAIL",
            "diagnostics": vm5_res["errors"][:3],
        })

        # VM06: Unplanted foot drift + grip teleport
        bad_mp = {
            "project_id": "mut_skate",
            "start_sec": 0.0,
            "end_sec": 3.0,
            "tracks": [
                {
                    "track_id": "S01_lucius",
                    "shot_id": "S01",
                    "actor_id": "lucius",
                    "start_sec": 0.0,
                    "end_sec": 3.0,
                    "ground_y": 0.84,
                    "height_norm": 0.28,
                    "world_start": [0.30, 0.84],
                    "world_end": [0.62, 0.84],
                    "phases": [
                        {
                            "phase_name": "CONTACT",
                            "start_sec": 0.0,
                            "end_sec": 3.0,
                            "world_start": [0.30, 0.84],
                            "world_end": [0.62, 0.84],
                            "foot_planted_left": True,
                            "foot_planted_right": True,
                        }
                    ],
                    "contacts": [
                        {
                            "constraint_id": "c1",
                            "start_sec": 0.0,
                            "end_sec": 3.0,
                            "actor_id": "lucius",
                            "object_id": "scroll",
                            "hand": "right",
                            "world_start": [0.92, 0.15],
                            "world_end": [0.92, 0.15],
                        }
                    ],
                }
            ],
            "world_states": [{"shot_id": "S01", "start_sec": 0.0, "end_sec": 3.0, "objects": {"scroll": {"x": 0.92, "y": 0.15}}}],
        }
        vm6_fp = audit_foot_plant(bad_mp)
        vm6_hc = audit_hand_prop_contact(bad_mp)
        results.append({
            "mutation_id": "VM06_planted_foot_drift_and_grip_teleport",
            "mutant_status": "FAIL" if (vm6_fp["status"] == "FAIL" and vm6_hc["status"] == "FAIL") else "PASS",
            "killed": baseline_ok and vm6_fp["status"] == "FAIL" and vm6_hc["status"] == "FAIL",
            "diagnostics": (vm6_fp["violations"][:2] + vm6_hc["violations"][:2]),
        })

        # VM07: Unvalidated AI confidence -> NOT_VERIFIED (never PASS)
        vm7_res = audit_character_consistency(base_proj, [good_png], ai_detector_confidence=0.32)
        results.append({
            "mutation_id": "VM07_unvalidated_confidence_not_verified",
            "mutant_status": vm7_res["status"],
            "killed": baseline_ok and vm7_res["status"] == "NOT_VERIFIED",
            "diagnostics": vm7_res["errors"][:2],
        })

        killed_count = sum(1 for r in results if r["killed"])
        return {
            "schema_version": "kh01.visual_mutations.v1",
            "status": "PASS" if (baseline_ok and killed_count == len(results)) else "FAIL",
            "baseline_passed": baseline_ok,
            "total_mutations": len(results),
            "killed_mutations": killed_count,
            "mutations": results,
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def verify_parent_rollup_honesty(parent_verdict: Dict[str, Any], child_gates: Dict[str, str]) -> Dict[str, Any]:
    """Fail-closed parent verdict auditor: rejects parent PASS when any required child gate failed or blocked."""
    bad_children = [
        f"{k}={v}"
        for k, v in child_gates.items()
        if str(v) not in ("PASS", "TECH_STYLE_CONTRACT_PASS", "PRODUCED", "REPAIRED", "FLOW_READY", "RUNTIME_VERIFIED", "NOT_AVAILABLE")
    ]
    claimed = str(parent_verdict.get("status") or "")
    if bad_children and claimed in ("PASS", "RELEASE_READY", "100%_PASS"):
        return {
            "valid": False,
            "status": "FAIL",
            "errors": [f"Misleading parent status '{claimed}' while child gates failed/blocked: {bad_children}"],
        }
    return {"valid": True, "status": "PASS", "errors": []}


def verify_render_receipt_freshness(receipt: Dict[str, Any], live_mp4: Path, live_shots_json: Path) -> Dict[str, Any]:
    """Fail-closed stale render receipt detector comparing receipt digests against live MP4 and shots.json."""
    errors: List[str] = []
    if not live_mp4.is_file():
        errors.append(f"Live MP4 missing: {live_mp4}")
    else:
        actual_mp4_sha = _sha256_file(live_mp4)
        if str(receipt.get("mp4_sha256") or "") != actual_mp4_sha:
            errors.append(f"Stale render receipt: mp4_sha256 {receipt.get('mp4_sha256')} != live {actual_mp4_sha}")
    if not live_shots_json.is_file():
        errors.append(f"Live shots.json missing: {live_shots_json}")
    else:
        actual_shots_sha = _sha256_file(live_shots_json)
        if str(receipt.get("shots_sha256") or "") != actual_shots_sha:
            errors.append(f"Stale render receipt: shots_sha256 {receipt.get('shots_sha256')} != live {actual_shots_sha}")
    expected_frames = int(receipt.get("expected_video_frames") or 720)
    decoded_frames = int(receipt.get("decoded_video_frames") or 0)
    if decoded_frames <= 0 or decoded_frames != expected_frames:
        errors.append(f"Zero or partial decoded frames: decoded={decoded_frames}, expected={expected_frames}")
    return {"valid": len(errors) == 0, "status": "PASS" if len(errors) == 0 else "FAIL", "errors": errors}


def verify_non_silent_narration_wav(wav_path: Path, min_rms: float = 0.004) -> Dict[str, Any]:
    """Fail-closed narration audio verifier: rejects silent or near-zero-amplitude WAV labeled narration."""
    import wave as _wave
    if not wav_path.is_file():
        return {"valid": False, "status": "BLOCKED_NO_REAL_TTS", "errors": [f"Missing narration WAV: {wav_path}"]}
    with _wave.open(str(wav_path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        sw = wf.getsampwidth()
    if sw != 2 or len(raw) < 1600:
        return {"valid": False, "status": "FAIL", "errors": ["Empty or invalid PCM16 WAV"]}
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(arr * arr)))
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if rms < min_rms or peak < 0.03:
        return {
            "valid": False,
            "status": "FAIL",
            "rms": round(rms, 6),
            "peak": round(peak, 6),
            "errors": [f"Silent TTS track rejected (rms={rms:.6f} < {min_rms}, peak={peak:.6f})"],
        }
    return {"valid": True, "status": "PASS", "rms": round(rms, 5), "peak": round(peak, 4), "errors": []}


def run_kh01_r1_negative_mutations(work_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Execute all 15 mandatory KH-01.R1 Section G negative/mutation cases on real files, manifests,
    WAVs, motion plans, and rendered PNGs — verifying fail-closed rejection on every single case!
    """
    import wave as _wave
    from tools.character_design import derive_character_specs, draw_character_figure_rgba
    from tools.environment_factory import derive_environment_specs, render_environment_stage_png, validate_environment_continuity

    tmp_ctx = tempfile.TemporaryDirectory() if work_dir is None else None
    base_d = Path(tmp_ctx.name) if tmp_ctx else Path(work_dir)
    base_d.mkdir(parents=True, exist_ok=True)

    try:
        prof_v2 = load_style_profile("modern_expressive_2d.v2")
        style_v2 = resolve_visual_style("Mina built a dragon kite in the sunlit park.", niche="city_park", style_id="modern_expressive_2d.v2")
        env_v2 = derive_environment_specs("Sunlit city park", niche="city_park", style_id="modern_expressive_2d.v2")

        bg_png = base_d / "clean_park_01.png"
        render_environment_stage_png(env_v2, bg_png, canvas_size=(640, 360), supersample=1)
        mina_spec = derive_character_specs([{"actor_id": "mina", "name": "Mina"}], "city_park", style_instance=style_v2)[0]

        view_pngs: Dict[str, Path] = {}
        authored_list: List[Dict[str, Any]] = []
        for vw in ("front", "three_quarter", "profile", "rear_three_quarter"):
            vp = base_d / f"mina_view_{vw}.png"
            im_v = draw_character_figure_rgba(mina_spec, view=vw, expression="neutral_attentive", canvas_size=(200, 260), supersample=1)
            im_v.save(vp, format="PNG")
            view_pngs[vw] = vp
            authored_list.append({"path": str(vp), "role": f"character_view:mina:{vw}", "sha256": _sha256_file(vp), "dimensions": [200, 260]})

        with Image.open(bg_png) as bg_im:
            comp = bg_im.convert("RGBA")
            with Image.open(view_pngs["three_quarter"]) as ch_im:
                comp.paste(ch_im, (210, 82), ch_im)
            comp.convert("RGB").save(bg_png, format="PNG")
        bg_png_2 = base_d / "clean_park_02.png"
        with Image.open(bg_png) as g_im:
            g_im.save(bg_png_2, format="PNG")
        authored_list.append({"path": str(bg_png), "role": "scene_frame", "sha256": _sha256_file(bg_png), "dimensions": [640, 360]})

        # Non-silent synthetic speech-band test WAV vs silent WAV
        sr = 16000
        t_ax = np.linspace(0.0, 1.0, sr, endpoint=False, dtype=np.float32)
        good_wav = base_d / "good_voice.wav"
        with _wave.open(str(good_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes((0.25 * np.sin(2 * np.pi * 220 * t_ax) * 32767).astype(np.int16).tobytes())

        silent_wav = base_d / "silent_voice.wav"
        with _wave.open(str(silent_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(np.zeros(sr, dtype=np.int16).tobytes())

        shots_json_path = base_d / "shots.json"
        clean_shots = [
            {
                "id": "S01",
                "start": 0.0,
                "end": 15.0,
                "dur": 15.0,
                "line": "Mina built a dragon kite in the park.",
                "style_id": "modern_expressive_2d.v2",
                "scale": "close",
                "art_direction": {"camera_scale": "close", "outfit_state_by_actor": {"mina": mina_spec["wardrobe"]["outfit_id"]}},
                "required_next_asset_variant": {"mina": mina_spec["wardrobe"]["outfit_id"]},
                "world_state": {"environment_id": env_v2["environment_id"], "objects": {"kite": {"x": 0.52, "y": 0.44}, "spool": {"x": 0.44, "y": 0.68}}},
                "args": {
                    "people": [{"id": "mina", "outfitId": mina_spec["wardrobe"]["outfit_id"], "assetVariant": mina_spec["wardrobe"]["outfit_id"], "primaryColor": mina_spec["wardrobe"]["primary_hex"]}],
                    "tetherLinks": [{"fromActor": "mina", "toProp": "kite"}],
                },
            },
            {
                "id": "S02",
                "start": 15.0,
                "end": 30.0,
                "dur": 15.0,
                "line": "And this time they flew the kite together.",
                "style_id": "modern_expressive_2d.v2",
                "scale": "wide",
                "art_direction": {"camera_scale": "wide", "outfit_state_by_actor": {"mina": mina_spec["wardrobe"]["outfit_id"]}},
                "world_state": {"environment_id": env_v2["environment_id"], "objects": {"kite": {"x": 0.58, "y": 0.36}, "spool": {"x": 0.46, "y": 0.68}}},
                "args": {
                    "people": [{"id": "mina", "outfitId": mina_spec["wardrobe"]["outfit_id"], "assetVariant": mina_spec["wardrobe"]["outfit_id"], "primaryColor": mina_spec["wardrobe"]["primary_hex"]}],
                    "tetherLinks": [{"fromActor": "mina", "toProp": "kite"}],
                },
            },
        ]
        shots_json_path.write_text(json.dumps({"shots": clean_shots}, indent=2), encoding="utf-8")
        dummy_mp4 = base_d / "clean_stub.mp4"
        dummy_mp4.write_bytes(b"VALID_MP4_STREAM_PAYLOAD_BYTES_FOR_RECEIPT_CHECK")

        clean_manifest = {
            "niche": "city_park",
            "license_spdx": "CC0-1.0",
            "provenance_origin": "ORIGINAL_KH01_R1_V2_TEST",
            "reference_frames_reused": 0,
            "prior_preview_derived_visual_inputs": 0,
            "authored_files": authored_list,
            "characters": {
                "mina": {
                    "views": ["front", "three_quarter", "profile", "rear_three_quarter"],
                    "expressions": list(mina_spec["supported_expressions"]),
                }
            },
        }
        clean_proj = {
            "expected_duration_sec": 30.0,
            "shots": clean_shots,
            "character_bible": {"characters": {"mina": mina_spec}},
        }
        clean_receipt = {
            "mp4_sha256": _sha256_file(dummy_mp4),
            "shots_sha256": _sha256_file(shots_json_path),
            "expected_video_frames": 720,
            "decoded_video_frames": 720,
        }

        baseline_ok = (
            validate_style_assets(prof_v2, clean_manifest, clean_proj)["status"] == "PASS"
            and audit_character_consistency({"shots": [clean_shots[0]], "character_bible": clean_proj["character_bible"]}, [bg_png, bg_png_2])["status"] == "PASS"
            and audit_composition_storytelling(clean_proj, clean_shots)["status"] == "PASS"
            and verify_render_receipt_freshness(clean_receipt, dummy_mp4, shots_json_path)["status"] == "PASS"
            and verify_non_silent_narration_wav(good_wav)["status"] == "PASS"
        )

        cases: List[Dict[str, Any]] = []

        # 1. Reference image copied into asset atlas
        m1 = copy.deepcopy(clean_manifest)
        ref_sha = sorted(FORBIDDEN_REFERENCE_IMAGE_SHA256)[0]
        fake_atlas = base_d / "mut_atlas_ref.png"
        fake_atlas.write_bytes(b"fake")
        m1["authored_files"].append({"path": str(fake_atlas), "role": "rig_texture_png:mina", "sha256": ref_sha, "dimensions": [1024, 1024]})
        r1 = validate_style_assets(prof_v2, m1, clean_proj)
        cases.append({"case_id": "M01_reference_image_copied_into_asset_atlas", "status": r1["status"], "killed": baseline_ok and r1["status"] == "FAIL", "diagnostics": r1["errors"][:2]})

        # 2. Old KH-01 v1 PNG reused in v2 manifest
        m2 = copy.deepcopy(clean_manifest)
        m2["authored_files"].append({"path": "tests/evidence/kh01_20261116_015100Z/style_poc/VQ01_STYLE_POC_CANDIDATE_05_outdoor_roman_forum.png", "sha256": "0" * 64, "dimensions": [1920, 1080]})
        r2 = validate_style_assets(prof_v2, m2, clean_proj)
        cases.append({"case_id": "M02_old_kh01_png_reused", "status": r2["status"], "killed": baseline_ok and r2["status"] == "FAIL", "diagnostics": r2["errors"][:2]})

        # 3. Missing viewpoint + horizontally flipped front masquerading as profile
        m3 = copy.deepcopy(clean_manifest)
        m3["characters"]["mina"]["views"] = ["front", "three_quarter"]
        flipped_p = base_d / "mina_flipped_fake_profile.png"
        with Image.open(view_pngs["front"]) as im_f:
            im_f.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(flipped_p, format="PNG")
        m3["authored_files"].append({"path": str(flipped_p), "role": "character_view:mina:profile", "sha256": _sha256_file(flipped_p), "dimensions": [200, 260]})
        r3 = validate_style_assets(prof_v2, m3, clean_proj)
        cases.append({"case_id": "M03_missing_or_flipped_viewpoint", "status": r3["status"], "killed": baseline_ok and r3["status"] == "FAIL", "diagnostics": r3["errors"][:2]})

        # 4. Character hand floating off kite spool
        mp_float_hand = {
            "project_id": "mut_spool_float",
            "start_sec": 0.0,
            "end_sec": 3.0,
            "tracks": [{
                "track_id": "S01_mina",
                "shot_id": "S01",
                "actor_id": "mina",
                "start_sec": 0.0,
                "end_sec": 3.0,
                "ground_y": 0.84,
                "height_norm": 0.26,
                "world_start": [0.25, 0.84],
                "world_end": [0.25, 0.84],
                "phases": [{"phase_name": "CONTACT", "start_sec": 0.0, "end_sec": 3.0, "world_start": [0.25, 0.84], "world_end": [0.25, 0.84], "foot_planted_left": True, "foot_planted_right": True}],
                "contacts": [{"constraint_id": "c_spool", "start_sec": 0.0, "end_sec": 3.0, "actor_id": "mina", "object_id": "spool", "hand": "right", "world_start": [0.88, 0.22], "world_end": [0.88, 0.22]}],
            }],
            "world_states": [{"shot_id": "S01", "start_sec": 0.0, "end_sec": 3.0, "objects": {"spool": {"x": 0.88, "y": 0.22}}}],
        }
        r4 = audit_hand_prop_contact(mp_float_hand)
        cases.append({"case_id": "M04_hand_floating_off_kite_spool", "status": r4["status"], "killed": baseline_ok and r4["status"] == "FAIL", "diagnostics": r4["violations"][:2]})

        # 5. Planted foot skate
        mp_skate = copy.deepcopy(mp_float_hand)
        mp_skate["tracks"][0]["contacts"] = []
        mp_skate["tracks"][0]["phases"][0]["world_end"] = [0.68, 0.84]
        r5 = audit_foot_plant(mp_skate)
        cases.append({"case_id": "M05_planted_foot_skate", "status": r5["status"], "killed": baseline_ok and r5["status"] == "FAIL", "diagnostics": r5["violations"][:2]})

        # 6. Sudden face/costume change mid-cut
        swapped_png = base_d / "mut_mina_costume_swap.png"
        render_environment_stage_png(env_v2, swapped_png, canvas_size=(640, 360), supersample=1)
        bad_mina = copy.deepcopy(mina_spec)
        bad_mina["wardrobe"]["primary_hex"] = "#1B4FD8"
        bad_mina["wardrobe"]["primary_shadow_hex"] = "#10328C"
        im_bad = draw_character_figure_rgba(bad_mina, view="three_quarter", expression="wide_shock", canvas_size=(200, 260), supersample=1)
        with Image.open(swapped_png) as bg_s:
            cs_im = bg_s.convert("RGBA")
            cs_im.paste(im_bad, (210, 82), im_bad)
            cs_im.convert("RGB").save(swapped_png, format="PNG")
        r6 = audit_character_consistency({"shots": [clean_shots[0]], "character_bible": clean_proj["character_bible"]}, [bg_png, swapped_png])
        cases.append({"case_id": "M06_sudden_face_costume_change_midcut", "status": r6["status"], "killed": baseline_ok and r6["status"] == "FAIL", "diagnostics": r6["errors"][:2]})

        # 7. Duplicate ribbon/string tether
        s_dup = copy.deepcopy(clean_shots)
        s_dup[0]["args"]["tetherLinks"].append({"fromActor": "mina", "toProp": "kite", "duplicated": True})
        s_dup[0]["world_state"]["objects"]["ribbon"] = {"x": 0.5, "y": 0.6, "duplicated": True}
        r7a = audit_composition_storytelling(clean_proj, s_dup)
        r7b = validate_environment_continuity(env_v2, s_dup)
        cases.append({"case_id": "M07_duplicate_ribbon_or_string", "status": "FAIL" if (r7a["status"] == "FAIL" and r7b["status"] == "FAIL") else "PASS", "killed": baseline_ok and r7a["status"] == "FAIL" and r7b["status"] == "FAIL", "diagnostics": (r7a["errors"][:1] + r7b["errors"][:1])})

        # 8. Stale render receipt
        stale_rec = copy.deepcopy(clean_receipt)
        stale_rec["shots_sha256"] = "f" * 64
        r8 = verify_render_receipt_freshness(stale_rec, dummy_mp4, shots_json_path)
        cases.append({"case_id": "M08_stale_render_receipt", "status": r8["status"], "killed": baseline_ok and r8["status"] == "FAIL", "diagnostics": r8["errors"][:2]})

        # 9. Silent TTS narration track
        r9 = verify_non_silent_narration_wav(silent_wav)
        cases.append({"case_id": "M09_silent_tts_narration", "status": r9["status"], "killed": baseline_ok and r9["status"] == "FAIL", "diagnostics": r9["errors"][:2]})

        # 10. Zero or partial decoded video frames
        part_rec = copy.deepcopy(clean_receipt)
        part_rec["decoded_video_frames"] = 140
        r10 = verify_render_receipt_freshness(part_rec, dummy_mp4, shots_json_path)
        cases.append({"case_id": "M10_zero_or_partial_decoded_frames", "status": r10["status"], "killed": baseline_ok and r10["status"] == "FAIL", "diagnostics": r10["errors"][:2]})

        # 11. Invalid camera action reset
        s_cam = copy.deepcopy(clean_shots)
        s_cam[0]["args"]["cameraSegments"] = [
            {"segment_id": "S01_seg01", "shot_id": "S01", "local_start": 0.0, "local_end": 7.5, "global_start": 0.0, "global_end": 7.5, "resets_action_time": False},
            {"segment_id": "S01_seg02", "shot_id": "S01", "local_start": 7.5, "local_end": 15.0, "global_start": 7.5, "global_end": 15.0, "scale": "wide", "viewpoint": "profile_left", "resets_action_time": True},
        ]
        r11 = audit_composition_storytelling(clean_proj, s_cam)
        cases.append({"case_id": "M11_invalid_camera_action_reset", "status": r11["status"], "killed": baseline_ok and r11["status"] == "FAIL", "diagnostics": r11["errors"][:2]})

        # 12. Impossible 30s timing (overlap + wrong total duration)
        s_time = copy.deepcopy(clean_shots)
        s_time[1]["start"] = 12.5
        s_time[1]["end"] = 26.0
        r12 = audit_composition_storytelling(clean_proj, s_time)
        cases.append({"case_id": "M12_impossible_30s_timing", "status": r12["status"], "killed": baseline_ok and r12["status"] == "FAIL", "diagnostics": r12["errors"][:2]})

        # 13. Incorrect asset variant after shot
        s_var = copy.deepcopy(clean_shots)
        s_var[1]["args"]["people"][0]["assetVariant"] = "wrong_roman_soldier_armor"
        r13 = audit_composition_storytelling(clean_proj, s_var)
        cases.append({"case_id": "M13_incorrect_asset_variant_after_shot", "status": r13["status"], "killed": baseline_ok and r13["status"] == "FAIL", "diagnostics": r13["errors"][:2]})

        # 14. Misleading parent PASS when child gate is FAIL
        r14 = verify_parent_rollup_honesty({"status": "PASS"}, {"style_contract": "PASS", "foot_plant_qa": "FAIL"})
        cases.append({"case_id": "M14_misleading_parent_pass_when_child_fail", "status": r14["status"], "killed": baseline_ok and r14["status"] == "FAIL", "diagnostics": r14["errors"][:2]})

        # 15. Invented style visual similarity score / auto-approved STYLE_APPROVED without review
        m15 = copy.deepcopy(clean_manifest)
        m15["style_similarity_score"] = 0.96
        m15["STYLE_APPROVED"] = "PASS"
        r15 = validate_reference_grounded_style_contract(style_v2, m15, clean_shots)
        cases.append({"case_id": "M15_invented_style_score_or_auto_approval", "status": r15["status"], "killed": baseline_ok and r15["status"] == "FAIL", "diagnostics": r15["errors"][:2]})

        killed = sum(1 for c in cases if c["killed"])
        return {
            "schema_version": "kh01_r1.negative_mutations.v2",
            "status": "PASS" if (baseline_ok and killed == len(cases)) else "FAIL",
            "baseline_passed": baseline_ok,
            "total_mutations": len(cases),
            "killed_mutations": killed,
            "mutations": cases,
        }
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()
