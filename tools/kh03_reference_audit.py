#!/usr/bin/env python3
"""kh03_reference_audit.py — User Screenshot Provenance & Demo-Asset Non-Reuse Auditor for KH-03.0."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_SCENE_TOKENS = (
    "kh02_bell",
    "bell_before_sunrise",
    "tavi",
    "lyra",
    "pip_goat",
    "drawpipgoat",
    "urgent_scroll",
    "marketplace_chase",
    "runaway_cart",
    "fountain_catch",
    "KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY",
    "three3d.js",
)


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def collect_user_style_reference(ref_paths: Iterable[Path | str] | None = None) -> Dict[str, Any]:
    """Locate & checksum optional user style screenshot; return honest UNAVAILABLE if absent."""
    candidates: List[Path] = []
    if ref_paths:
        candidates.extend(Path(p) for p in ref_paths)
    else:
        candidates.extend([
            REPO_ROOT / "visual_styles" / "roman_squire_master" / "v1" / "references" / "KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY.png",
            REPO_ROOT / "KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY.png",
            REPO_ROOT.parent / "KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY.png",
        ])

    for cp in candidates:
        if cp.is_file():
            return {
                "status": "USER_SCREENSHOT_REFERENCE_AVAILABLE",
                "path": str(cp.resolve()),
                "sha256": _sha256_file(cp),
                "bytes": cp.stat().st_size,
                "allowed_usage": "STYLE_AUDIT_COMPARISON_ONLY",
                "forbid_video_frame_ingest": True,
            }

    return {
        "status": "USER_SCREENSHOT_REFERENCE_UNAVAILABLE",
        "path": None,
        "sha256": None,
        "bytes": 0,
        "allowed_usage": "FALLBACK_TO_PRODUCTION_SOURCE_AND_BASELINE_RENDERS",
        "forbid_video_frame_ingest": True,
    }


def assert_no_reused_demo_assets(
    new_project_root: Path | str,
    forbidden_roots: Iterable[Path | str] | None = None,
    forbidden_hashes: Set[str] | None = None,
) -> Dict[str, Any]:
    """Assert zero file/hash reuse from prior demos/baselines and zero KH01/KH02/screenshot references."""
    proj = Path(new_project_root).resolve()
    errors: List[str] = []

    if not proj.is_dir():
        return {"passed": False, "errors": [f"Project root does not exist: {proj}"], "files_audited": 0}

    banned_hashes: Set[str] = set(forbidden_hashes or set())
    default_roots = [
        REPO_ROOT / "projects" / "squire-mau",
        REPO_ROOT / "projects" / "selfimprove-mau",
        REPO_ROOT / "projects" / "kh02_bell_before_sunrise_30s",
        REPO_ROOT / "tests" / "evidence",
    ]
    roots = [Path(r) for r in (forbidden_roots if forbidden_roots is not None else default_roots)]
    for rt in roots:
        if rt.is_dir():
            for f in rt.rglob("*"):
                if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".wav", ".js", ".json"}:
                    try:
                        banned_hashes.add(_sha256_file(f))
                    except OSError:
                        pass

    ref_info = collect_user_style_reference()
    if ref_info.get("sha256"):
        banned_hashes.add(ref_info["sha256"])

    # 1. Check anh/ external image folder — KH03 pilot must be 100% fresh Canvas2D code, zero imported bitmaps!
    anh_dir = proj / "anh"
    if anh_dir.is_dir():
        ext_imgs = [f.name for f in anh_dir.iterdir() if f.is_file()]
        if ext_imgs:
            errors.append(f"Forbidden external bitmap plates in {anh_dir}: {ext_imgs}")

    # 2. Check every file in story/, scenes/, timeline/, out/ against banned demo hashes & forbidden tokens
    files_audited = 0
    for sub in ("config.json", "story", "scenes", "timeline", "out"):
        target = proj / sub
        items = [target] if target.is_file() else (sorted(target.rglob("*")) if target.is_dir() else [])
        for fp in items:
            if not fp.is_file():
                continue
            files_audited += 1
            fhash = _sha256_file(fp)
            if fhash in banned_hashes:
                errors.append(f"Reused demo/reference hash detected in '{fp.relative_to(proj)}': {fhash}")

            if fp.suffix.lower() in {".js", ".mjs", ".json", ".txt"}:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
                for tok in FORBIDDEN_SCENE_TOKENS:
                    if re.search(re.escape(tok), txt, flags=re.IGNORECASE):
                        errors.append(f"Forbidden legacy/KH01/KH02/reference token '{tok}' found in '{fp.relative_to(proj)}'")

    return {
        "passed": len(errors) == 0,
        "project": proj.name,
        "files_audited": files_audited,
        "banned_hashes_checked": len(banned_hashes),
        "reference_screenshot_status": ref_info["status"],
        "errors": errors,
    }
