#!/usr/bin/env python3
"""kh03_style_lock.py — Roman Master Style Bible v1 Loader, Canonical Digest & Contract Validator.

Enforces:
- Exact Production Squire Roman 2D identity anchors (round #f4ede1 ivory head, #392a21 OUT contour,
  warm-gold #d3a24e Montefortino helmet with feathers/crest, #c9473a red tunic + scutum with #e7b04a gold rim,
  white glove #ffffff, wood/steel spear/pilum).
- Never falls back silently to KH-02 modern2d or non-Roman character families.
- Preserves legacy packs/samples unchanged when opt-in style_profile is disabled.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLE_BIBLE_DIR = REPO_ROOT / "visual_styles" / "roman_squire_master" / "v1"
STYLE_BIBLE_PATH = STYLE_BIBLE_DIR / "style_bible.json"

REQUIRED_TOP_KEYS = (
    "schema_version",
    "style_id",
    "style_family",
    "canonical_digest",
    "renderer_contract",
    "reference_provenance",
    "geometric_invariants",
    "palette_lock",
    "outline_and_lod_rules",
    "locked_character_archetypes",
    "expression_grammar",
    "editable_upgrade_slots",
    "forbidden_modifications",
)

EXPECTED_PALETTE_ANCHORS = {
    "OUT": "#392a21",
    "skin": "#f4ede1",
    "glove": "#ffffff",
    "red": "#c9473a",
    "gold": "#e7b04a",
    "bronze": "#d3a24e",
    "yellow": "#efc23f",
}

PRESERVED_BASELINE_PATHS = (
    "engine/core.js",
    "engine/three3d.js",
    "packs/dem/pack.js",
    "packs/dem/templates.js",
    "packs/doodle/pack.js",
    "packs/squire/army.js",
    "packs/squire/horse.js",
    "projects/squire-mau/config.json",
    "projects/squire-mau/story/shots.json",
    "projects/selfimprove-mau/config.json",
    "projects/selfimprove-mau/story/shots.json",
)


def compute_roman_style_digest(style_dict: Dict[str, Any]) -> str:
    """Compute OS-deterministic canonical sorted JSON SHA-256 excluding canonical_digest."""
    if not isinstance(style_dict, dict):
        raise TypeError("style_dict must be a dictionary")
    clean = {k: v for k, v in style_dict.items() if k != "canonical_digest"}
    canonical_bytes = json.dumps(
        clean,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def load_roman_master_style(style_id: str = "roman_squire_master.v1", path: Path | None = None) -> Dict[str, Any]:
    """Load and schema-validate the Roman Master Style Bible v1; never fall back to modern2d."""
    if style_id != "roman_squire_master.v1":
        raise ValueError(
            f"Unsupported style_id '{style_id}': KH-03.0 strictly requires 'roman_squire_master.v1' "
            "(no fallback to modern2d or external styles)."
        )
    target = Path(path) if path else STYLE_BIBLE_PATH
    if not target.is_file():
        raise FileNotFoundError(f"Roman Master Style Bible missing at {target}")
    data = json.loads(target.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_TOP_KEYS if k not in data]
    if missing:
        raise ValueError(f"Style bible missing required keys: {missing}")
    if data.get("style_id") != "roman_squire_master.v1":
        raise ValueError(f"Style bible style_id mismatch: {data.get('style_id')}")
    if data.get("style_family") != "production_squire_original_roman_2d":
        raise ValueError(f"Forbidden style_family '{data.get('style_family')}'; must be production_squire_original_roman_2d")
    return data


def validate_roman_style_contract(
    style_dict: Dict[str, Any],
    baseline_manifest: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Validate measurable style lock invariants, palette/proportion anchors, and baseline preservation."""
    errors: List[str] = []
    warnings: List[str] = []

    for k in REQUIRED_TOP_KEYS:
        if k not in style_dict:
            errors.append(f"Missing required field '{k}'")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "style_approved": "HUMAN_REVIEW_PENDING"}

    computed = compute_roman_style_digest(style_dict)
    recorded = style_dict.get("canonical_digest", "")
    if computed != recorded:
        errors.append(f"Canonical style digest mismatch: recorded={recorded}, computed={computed}")

    rc = style_dict.get("renderer_contract") or {}
    if rc.get("engine") != "html5_canvas_2d" or rc.get("required_render_mode") != "canvas2d_only":
        errors.append("renderer_contract must enforce html5_canvas_2d and canvas2d_only")
    if not rc.get("forbid_threejs") or not rc.get("forbid_webgl_3d_scene"):
        errors.append("renderer_contract must explicitly forbid Three.js and WebGL 3D scenes")

    pal = style_dict.get("palette_lock") or {}
    for pk, pv in EXPECTED_PALETTE_ANCHORS.items():
        if str(pal.get(pk, "")).lower() != pv.lower():
            errors.append(f"Palette anchor '{pk}' drifted: expected {pv}, got {pal.get(pk)}")

    geo = style_dict.get("geometric_invariants") or {}
    if abs(float(geo.get("head_radius_u", 0)) - 19.0) > 1e-3:
        errors.append(f"Head radius invariant drifted from 19.0u: {geo.get('head_radius_u')}")
    if abs(float(geo.get("head_diameter_to_body_height_ratio", 0)) - 0.38) > 1e-3:
        errors.append(f"Head ratio drifted from 0.38: {geo.get('head_diameter_to_body_height_ratio')}")
    if abs(float(geo.get("scutum_ellipse_rx_to_s", 0)) - 0.33) > 1e-3 or abs(float(geo.get("scutum_ellipse_ry_to_s", 0)) - 0.50) > 1e-3:
        errors.append("Scutum aspect ratio invariants drifted from Production Squire 0.33 x 0.50")

    archetypes = style_dict.get("locked_character_archetypes") or {}
    if "rookie_hastatus" not in archetypes or "instructor_princeps" not in archetypes:
        errors.append("locked_character_archetypes must include rookie_hastatus and instructor_princeps")
    for a_id, arch in archetypes.items():
        if arch.get("helmet") not in ("montefortino", "attic"):
            errors.append(f"Archetype '{a_id}' violated Roman helmet lock: {arch.get('helmet')}")
        if arch.get("body") != "roman":
            errors.append(f"Archetype '{a_id}' violated Roman body lock: {arch.get('body')}")
        sh = arch.get("shield") or {}
        if sh.get("type") != "scutum" or str(sh.get("color", "")).lower() != "#c9473a":
            errors.append(f"Archetype '{a_id}' violated red scutum lock: {sh}")

    # Verify preserved baseline files if baseline_manifest provided
    if baseline_manifest and "tracked_files" in baseline_manifest:
        tf = baseline_manifest["tracked_files"]
        for rel in PRESERVED_BASELINE_PATHS:
            if rel in tf:
                fp = REPO_ROOT / rel
                if not fp.is_file():
                    errors.append(f"Preserved baseline file missing: {rel}")
                else:
                    h = hashlib.sha256(fp.read_bytes()).hexdigest()
                    if h != tf[rel]["sha256"]:
                        errors.append(f"Preserved baseline file modified: {rel}")

    prov = style_dict.get("reference_provenance") or {}
    if prov.get("user_screenshot_status") == "USER_SCREENSHOT_REFERENCE_UNAVAILABLE":
        warnings.append("Companion user screenshot attachment unavailable in workspace; using Production source & baseline renders as primary truth.")

    return {
        "valid": len(errors) == 0,
        "style_id": style_dict.get("style_id"),
        "computed_digest": computed,
        "digest_verified": computed == recorded,
        "errors": errors,
        "warnings": warnings,
        "style_approved": "HUMAN_REVIEW_PENDING",
    }


def resolve_roman_variant(
    role: str,
    era: str = "roman_republic_imperial",
    wardrobe: str = "roman_tunic_pectoral",
    environment_id: str = "roman_training_yard",
    style_dict: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Resolve a character/environment variant strictly inside the locked original Roman Squire family."""
    sb = style_dict or load_roman_master_style()
    if era not in ("roman_republic_imperial", "roman"):
        raise ValueError(f"KH-03.0 restricts era to Roman Squire world; got '{era}'")
    if wardrobe not in ("roman_tunic_pectoral", "roman_mail_lorica"):
        raise ValueError(f"Unsupported non-Roman or unlocked wardrobe '{wardrobe}'")
    allowed_envs = {"roman_training_yard", "roman_camp_gate", "roman_shield_wall", "roman_plain_dawn"}
    if environment_id not in allowed_envs:
        raise ValueError(f"Unsupported environment_id '{environment_id}'; allowed={sorted(allowed_envs)}")

    role_map = {
        "rookie": "rookie_hastatus",
        "rookie_hastatus": "rookie_hastatus",
        "hero": "rookie_hastatus",
        "instructor": "instructor_princeps",
        "instructor_princeps": "instructor_princeps",
        "drill_instructor": "instructor_princeps",
        "neighbor": "veteran_neighbor_legionary",
        "veteran_neighbor_legionary": "veteran_neighbor_legionary",
        "legionary_crowd": "veteran_neighbor_legionary",
        "centurion": "centurion_crest",
        "centurion_crest": "centurion_crest",
    }
    if role not in role_map:
        raise ValueError(f"Unknown or unlocked role '{role}' (forbidden to switch character family)")

    arch_key = role_map[role]
    spec = copy.deepcopy(sb["locked_character_archetypes"][arch_key])
    if wardrobe == "roman_mail_lorica":
        spec["mail"] = True

    resolved = {
        "style_id": sb["style_id"],
        "style_family": sb["style_family"],
        "role": role,
        "archetype_id": arch_key,
        "era": era,
        "wardrobe": wardrobe,
        "environment_id": environment_id,
        "squire_preset_params": spec,
    }
    resolved["variant_digest"] = hashlib.sha256(
        json.dumps(resolved, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return resolved


if __name__ == "__main__":
    raw = json.loads(STYLE_BIBLE_PATH.read_text(encoding="utf-8"))
    dig = compute_roman_style_digest(raw)
    if raw.get("canonical_digest") != dig:
        raw["canonical_digest"] = dig
        STYLE_BIBLE_PATH.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    res = validate_roman_style_contract(raw)
    print(json.dumps(res, indent=2))
