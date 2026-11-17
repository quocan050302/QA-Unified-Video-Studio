#!/usr/bin/env python3
"""kh02_style_contract.py — Deterministic 2D Style Lock & Validation Contract for KH-02.1.

Provides:
- load_squire_style_profile(style_id)
- resolve_squire_niche_style(script_context, style_id)
- validate_squire_style_contract(profile, scene_specs)
- compute_style_lock_digest(profile)

Pure Python + local JSON schema checks. Zero network or external model calls.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_ROOT = REPO_ROOT / "visual_styles"

STYLE_ID_MAP = {
    "squire_cinematic_2d.v1": STYLES_ROOT / "squire_cinematic_2d" / "v1" / "style_bible.json",
}

REQUIRED_TOP_KEYS = (
    "style_id",
    "schema_version",
    "lineage",
    "render_contract",
    "protected_production_default",
    "stroke_weight_model",
    "tapered_strokes",
    "silhouette_clarity_360px",
    "proportional_invariants",
    "cel_shading_bands",
    "cloth_fold_rules",
    "face_emotional_range",
    "layer_value_separation",
    "line_of_action_and_fx_rules",
    "cinematic_composition",
    "semantic_palettes",
    "canonical_digest",
)

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _canonical_json_without_digest(profile: Dict[str, Any]) -> str:
    payload = copy.deepcopy(profile)
    payload.pop("canonical_digest", None)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_style_lock_digest(profile: Dict[str, Any]) -> str:
    """Return deterministic SHA-256 hex digest of canonicalized style profile."""
    if not isinstance(profile, dict):
        raise TypeError("profile must be a dict")
    serialized = _canonical_json_without_digest(profile)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_squire_style_profile(style_id: str = "squire_cinematic_2d.v1") -> Dict[str, Any]:
    """Load and verify a versioned Squire 2D style bible by style_id."""
    style_path = STYLE_ID_MAP.get(style_id)
    if style_path is None:
        # Allow resolving folder pattern <family>.<version>
        if "." in style_id:
            fam, ver = style_id.rsplit(".", 1)
            cand = STYLES_ROOT / fam / ver / "style_bible.json"
            if cand.is_file():
                style_path = cand
    if style_path is None or not style_path.is_file():
        raise FileNotFoundError(f"Unknown or missing Squire style profile for style_id='{style_id}'")

    profile = json.loads(style_path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_TOP_KEYS if k not in profile]
    if missing:
        raise ValueError(f"Style profile '{style_id}' missing required keys: {missing}")

    if profile.get("style_id") != style_id:
        raise ValueError(f"Style ID mismatch: expected '{style_id}', got '{profile.get('style_id')}'")

    expected_digest = compute_style_lock_digest(profile)
    recorded_digest = profile.get("canonical_digest", "")
    if recorded_digest != expected_digest:
        raise ValueError(
            f"Style lock digest mismatch for '{style_id}': recorded={recorded_digest}, computed={expected_digest}"
        )

    return profile


def resolve_squire_niche_style(
    script_context: Any,
    style_id: str = "squire_cinematic_2d.v1",
) -> Dict[str, Any]:
    """Deterministically resolve semantic palette & wardrobe/material overrides for a script context.

    Supports 'roman', 'medieval', and 'non_historical_future' without hardcoding Roman clothes
    inside generic Canvas2D ink utilities.
    """
    profile = load_squire_style_profile(style_id)
    palettes = profile.get("semantic_palettes", {})

    explicit_niche: Optional[str] = None
    text_blob = ""
    if isinstance(script_context, dict):
        explicit_niche = script_context.get("niche") or script_context.get("era")
        text_blob = " ".join(
            str(script_context.get(k, ""))
            for k in ("title", "summary", "setting", "script", "location", "notes")
        )
    elif isinstance(script_context, (list, tuple)):
        text_blob = " ".join(str(x) for x in script_context)
    else:
        text_blob = str(script_context or "")

    low = text_blob.lower()
    if explicit_niche in palettes:
        chosen_niche = explicit_niche
    else:
        roman_hits = len(
            re.findall(
                r"\b(rome|roman|latin|toga|tunic|bell-keeper|hilltop|villa|courtyard|bronze|legion|senator|aqueduct)\b",
                low,
            )
        )
        medieval_hits = len(
            re.findall(r"\b(knight|medieval|castle|cathedral|bascinet|mail|gambeson|feudal|norman|king)\b", low)
        )
        future_hits = len(
            re.findall(r"\b(future|station|orbital|cyber|reactor|colony|modern|laboratory|industrial)\b", low)
        )
        if roman_hits >= max(medieval_hits, future_hits) and roman_hits > 0:
            chosen_niche = "roman"
        elif medieval_hits >= future_hits and medieval_hits > 0:
            chosen_niche = "medieval"
        elif future_hits > 0:
            chosen_niche = "non_historical_future"
        else:
            chosen_niche = "roman"

    niche_data = copy.deepcopy(palettes[chosen_niche])
    resolved = {
        "style_id": profile["style_id"],
        "style_lock_digest": profile["canonical_digest"],
        "resolved_niche": chosen_niche,
        "render_mode": profile["render_contract"]["render_mode"],
        "base_ink": profile["protected_production_default"]["outline_hex"],
        "base_skin": profile["protected_production_default"]["skin_hex"],
        "stroke_weight_model": copy.deepcopy(profile["stroke_weight_model"]),
        "cel_shading_bands": copy.deepcopy(profile["cel_shading_bands"]),
        "layer_value_separation": copy.deepcopy(profile["layer_value_separation"]),
        "niche_palette": niche_data,
    }
    resolved["resolved_sha256"] = hashlib.sha256(
        json.dumps(resolved, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return resolved


def validate_squire_style_contract(
    profile: Dict[str, Any],
    scene_specs: Any,
) -> Dict[str, Any]:
    """Validate profile invariants and scene specifications against KH-02.1 2D cinematic rules."""
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(profile, dict):
        return {"valid": False, "errors": ["profile must be a dict"], "warnings": [], "style_digest": ""}

    for k in REQUIRED_TOP_KEYS:
        if k not in profile:
            errors.append(f"Missing required profile key: '{k}'")

    rc = profile.get("render_contract", {})
    if rc.get("render_mode") != "canvas2d_only" or not rc.get("forbid_three3d"):
        errors.append("render_contract must enforce render_mode='canvas2d_only' and forbid_three3d=True")

    ppd = profile.get("protected_production_default", {})
    if ppd.get("outline_hex", "").lower() != "#392a21":
        errors.append("protected_production_default.outline_hex must preserve Production Squire OUT '#392a21'")
    if not HEX_COLOR_RE.match(ppd.get("skin_hex", "")):
        errors.append("protected_production_default.skin_hex must be a valid 6-digit hex color")

    bands = profile.get("cel_shading_bands", {})
    band_count = int(bands.get("band_count_max", 0))
    if not (2 <= band_count <= 3):
        errors.append(f"cel_shading_bands.band_count_max must be 2 or 3, got {band_count}")

    sem = profile.get("semantic_palettes", {})
    for req_niche in ("roman", "medieval", "non_historical_future"):
        if req_niche not in sem:
            errors.append(f"semantic_palettes missing required profile '{req_niche}'")

    digest_ok = False
    computed_digest = ""
    try:
        computed_digest = compute_style_lock_digest(profile)
        digest_ok = computed_digest == profile.get("canonical_digest")
        if not digest_ok:
            errors.append(
                f"canonical_digest mismatch: expected {computed_digest}, found {profile.get('canonical_digest')}"
            )
    except Exception as exc:
        errors.append(f"digest computation error: {exc}")

    # Validate scene_specs (list of shots or dict with shots)
    shots: List[Dict[str, Any]] = []
    if isinstance(scene_specs, dict):
        if scene_specs.get("render_mode") not in (None, "canvas2d_only"):
            errors.append(f"scene_specs render_mode='{scene_specs.get('render_mode')}' violates canvas2d_only")
        shots = list(scene_specs.get("shots", []))
    elif isinstance(scene_specs, list):
        shots = list(scene_specs)
    else:
        errors.append("scene_specs must be a dict or list of shot specs")

    cam_bounds = profile.get("cinematic_composition", {}).get("camera_bounds", {})
    max_zoom = float(cam_bounds.get("max_zoom", 1.38))
    min_zoom = float(cam_bounds.get("min_zoom", 0.92))

    prev_end: Optional[float] = None
    for idx, sh in enumerate(shots):
        sid = sh.get("id", f"shot_{idx}")
        if sh.get("kind") == "3d" or sh.get("tpl") == "3d" or (sh.get("args") or {}).get("kind") == "3d":
            errors.append(f"KH02_2D_ONLY_VIOLATION: shot '{sid}' uses forbidden 3D kind/template")
        if sh.get("three3d") or sh.get("webgl"):
            errors.append(f"KH02_2D_ONLY_VIOLATION: shot '{sid}' requests WebGL/Three.js")

        st = sh.get("start")
        en = sh.get("end")
        if isinstance(st, (int, float)) and isinstance(en, (int, float)):
            if en <= st:
                errors.append(f"Shot '{sid}' has non-positive duration ({st} -> {en})")
            if prev_end is not None and abs(st - prev_end) > 0.002:
                errors.append(f"Timeline discontinuity before '{sid}': prev_end={prev_end}, start={st}")
            prev_end = float(en)

        cam = sh.get("camera") or (sh.get("args") or {}).get("camera_2d") or {}
        if isinstance(cam, dict):
            for zk in ("z0", "z1", "zoom"):
                zv = cam.get(zk)
                if isinstance(zv, (int, float)) and (zv < min_zoom or zv > max_zoom):
                    errors.append(
                        f"Shot '{sid}' camera {zk}={zv} outside 2D safe bounds [{min_zoom}, {max_zoom}]"
                    )

        layers = sh.get("layers") or (sh.get("args") or {}).get("layers_2d")
        if isinstance(layers, list) and 0 < len(layers) < 3:
            warnings.append(f"Shot '{sid}' specifies fewer than 3 2D depth layers ({len(layers)})")

    return {
        "valid": len(errors) == 0,
        "style_id": profile.get("style_id", ""),
        "style_digest": computed_digest,
        "digest_verified": digest_ok,
        "shots_checked": len(shots),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="KH-02.1 Squire Cinematic 2D Style Contract Tool")
    ap.add_argument("--style-id", default="squire_cinematic_2d.v1")
    ap.add_argument("--stamp", action="store_true", help="Compute and stamp canonical_digest into style_bible.json")
    ap.add_argument("--scene-spec", help="Optional path to storyboard.json or shots.json to validate")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    style_path = STYLE_ID_MAP.get(args.style_id)
    if args.stamp:
        if not style_path or not style_path.is_file():
            print(f"Style file not found for {args.style_id}", file=sys.stderr)
            return 1
        raw = json.loads(style_path.read_text(encoding="utf-8"))
        raw["canonical_digest"] = compute_style_lock_digest(raw)
        style_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    profile = load_squire_style_profile(args.style_id)
    scene_data: Any = []
    if args.scene_spec:
        scene_data = json.loads(Path(args.scene_spec).read_text(encoding="utf-8"))
    res = validate_squire_style_contract(profile, scene_data)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[{'PASS' if res['valid'] else 'FAIL'}] {res['style_id']} digest={res['style_digest'][:16]}... shots={res['shots_checked']}")
        for e in res["errors"]:
            print(f"  ERROR: {e}")
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
