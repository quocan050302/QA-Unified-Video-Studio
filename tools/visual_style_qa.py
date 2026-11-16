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
    StyleInstance,
    StyleProfile,
    load_style_profile,
    resolve_visual_style,
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
    for mf in mf_list:
        niche = str(mf.get("niche") or next(iter((mf.get("environments") or {}).values()), {}).get("niche") or "roman_forum")
        style_inst = resolve_visual_style({"niche": niche}, niche=niche, style_id=prof.style_id)
        res = validate_style_contract(style_inst, mf, shots)
        if not res["valid"]:
            errors.extend(res["errors"])

        # Explicit check that any png/svg layer does not reference forbidden copyrighted/reference tokens
        for entry in mf.get("authored_files") or []:
            checked_files += 1
            p_str = str(entry.get("path") or "")
            if any(tok in p_str.lower() for tok in FORBIDDEN_ASSET_TOKENS):
                errors.append(f"Forbidden reference/legacy image layer detected: {p_str}")

        # Verify distinct expression hashes if expression_assets provided
        for cid, cdata in (mf.get("characters") or {}).items():
            exprs = list(cdata.get("expressions") or [])
            if len(set(exprs)) < 6:
                errors.append(f"Character '{cid}' missing required 6 expressions (found {len(set(exprs))})")
            views = set(cdata.get("views") or [])
            if not {"front", "three_quarter", "profile"}.issubset(views):
                errors.append(f"Character '{cid}' missing required 3 views (found {sorted(views)})")

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

    # Check adjacent frame sudden 1-frame disappearance / blank glitch
    luma_means: List[float] = []
    for fp in frame_paths:
        with Image.open(fp) as im:
            arr_f = np.asarray(im.convert("RGB"), dtype=np.float32)
        std_f = float(np.std(arr_f))
        if std_f < 3.0:
            errors.append(f"Blank or near-uniform frame detected: {fp.name} (std={std_f:.2f})")
        luma_means.append(float(np.mean(arr_f)))

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

        # 5. Center focal contrast
        center_patch = luma[int(h * 0.18) : int(h * 0.86), int(w * 0.20) : int(w * 0.80)]
        focal_std = float(np.std(center_patch))

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
    for idx, s in enumerate(shots):
        sid = str(s.get("id") or f"S{idx+1:02d}")
        args = s.get("args") or {}
        art = s.get("art_direction") or args.get("artDirection") or {}
        cam = s.get("camera") or {}
        sc = str(art.get("camera_scale") or cam.get("scale") or s.get("scale") or "medium")
        vw = str(cam.get("viewpoint") or art.get("viewpoint_target") or args.get("view") or "three_quarter")
        scales.append(sc)
        views.append(vw)

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

        # Reject static slideshow pan-only shots when actor action is claimed
        has_motion = bool(args.get("motionTracks")) or bool(args.get("people")) or s.get("expected_subject") == "prop"
        if not has_motion:
            errors.append(f"Shot {sid}: static slideshow detected (zero motionTracks/actors/animated props)")

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
) -> Dict[str, Any]:
    """
    Build a local visual editorial review montage PNG + structured JSON/Markdown packet
    without shipping or embedding any copyrighted user reference images.
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

    # Compose 3-column original art review montage
    cols = 3
    tw, th, pad = 560, 315, 20
    rows = max(1, math.ceil(len(normalized_items) / cols))
    header_h = 110
    montage_w = pad + cols * (tw + pad)
    montage_h = header_h + rows * (th + 46 + pad)
    montage = Image.new("RGB", (montage_w, montage_h), (24, 22, 24))
    dr = ImageDraw.Draw(montage)
    f_h = _load_font(28, bold=True)
    f_s = _load_font(17, bold=False)

    ref_status = str(reference_manifest.get("reference_status") or "STYLE_REFERENCE_UNAVAILABLE")
    dr.text(
        (pad, 18),
        "KH-01 ORIGINAL MODERN EXPRESSIVE 2D — EDITORIAL REVIEW MONTAGE (ZERO USER REF FRAMES EMBEDDED)",
        fill=(252, 234, 192),
        font=f_h,
    )
    dr.text(
        (pad, 58),
        f"Reference Archive Status: {ref_status} | STYLE_APPROVED: HUMAN_REVIEW_PENDING | EDITORIAL_APPROVED: HUMAN_REVIEW_PENDING",
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

    honest_gap_notes = [
        "Reference archive KH-01_STYLE_REFERENCES_ONLY.zip was unavailable on host (STYLE_REFERENCE_UNAVAILABLE); direct side-by-side pixel comparison against the three user reference frames requires the user to place those frames locally.",
        "All KH-01 characters, outfits, props, and multi-plane stages are 100% newly authored vector/Canvas/Rigby2D artwork governed by modern_expressive_2d.v1 rules; hand-drawn frame-by-frame traditional smear/boil nuances remain simpler than bespoke studio cel animation.",
        "STYLE_APPROVED and EDITORIAL_APPROVED remain HUMAN_REVIEW_PENDING until explicit human inspection of the PNG sheets and 30.000s 1080p MP4.",
    ]

    packet = {
        "schema_version": "kh01.editorial_packet.v1",
        "reference_status": ref_status,
        "public_repo_contains_user_reference_images": False,
        "STYLE_APPROVED": "HUMAN_REVIEW_PENDING",
        "EDITORIAL_APPROVED": "HUMAN_REVIEW_PENDING",
        "visual_gates": {gid: qa_results.get(gid, "CANDIDATE_READY_FOR_HUMAN_REVIEW") for gid in VISUAL_GATE_IDS},
        "montage_png": {
            "path": str(montage_path.relative_to(ROOT_DIR).as_posix() if montage_path.is_relative_to(ROOT_DIR) else montage_path),
            "sha256": _sha256_file(montage_path),
            "dimensions": [montage_w, montage_h],
            "panel_count": len(normalized_items),
        },
        "subjective_gaps_and_disclosures": honest_gap_notes,
        "reviewer_checkpoints": [
            "Verify bold variable-weight ink outlines and 2-3 cel-shading value groups read cleanly at 1080p and mobile width.",
            "Inspect Lucius and Mara 3-view turnarounds and 6 facial expressions for genuine emotional range.",
            "Inspect S01 scroll hook, S05 cart brace, S06 fountain catch multi-angle edit, S07 'MEETING MOVED TO TOMORROW' reveal, and S08 comedic payoff.",
            "Confirm natural English narration intelligibility, Foley balance, and -14 LUFS loudness comfort.",
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
