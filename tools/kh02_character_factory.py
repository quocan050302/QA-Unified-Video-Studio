#!/usr/bin/env python3
"""kh02_character_factory.py — Deterministic 2D Character Bible, Turnaround & Continuity Factory (KH-02.1).

Provides:
- derive_character_identity(script_entities)
- build_character_turnaround_2d(identity, style)
- build_expression_sheet_2d(identity, style)
- write_character_continuity_manifest(identity, assets)
- validate_character_model_consistency(manifest)

Pure 2D vector specification & validation. Explicitly separates human Squire-caricature rigs
from quadruped animal characters (e.g., PIP the goat is NEVER claimed as a human rig).
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kh02_style_contract import load_squire_style_profile

REQUIRED_VIEWS = ("front", "three_quarter", "profile")
MIN_HUMAN_EXPRESSIONS = 6
MIN_HUMAN_HAND_POSES = 2


DEFAULT_ROMAN_BELL_CAST = [
    {
        "entity_key": "TAVI",
        "character_id": "char_tavi_keeper",
        "canonical_name": "TAVI",
        "entity_kind": "human",
        "rig_class": "human_squire_caricature_2d",
        "is_human_rig": True,
        "role": "Young, anxious, clever apprentice Roman hilltop bell-keeper",
        "proportions": {
            "stature_scale": 0.95,
            "head_scale": 1.03,
            "head_radius_per_100u": 19.57,
            "shoulder_width_u": 12.6,
        },
        "layered_parts": [
            "hair_back",
            "far_arm_tapered",
            "scarf_tail_secondary",
            "undertunic_hem",
            "terracotta_tunic_cel",
            "leather_belt_brass_key_pouch",
            "saffron_neck_scarf",
            "neck_and_round_squire_head",
            "facial_features_freckles",
            "tousled_forelock_tufts",
            "near_arm_and_articulated_hand",
            "planted_caligae_sandals",
        ],
        "wardrobe": {
            "skin": "#f4ede1",
            "skin_shade": "#d6c8c6",
            "hair": "tousled_tufts",
            "hair_color": "#4c3020",
            "tunic": "#b84b39",
            "tunic_shadow": "#863124",
            "tunic_deep": "#5c1e15",
            "undertunic": "#eadbc2",
            "scarf": "#df9b43",
            "belt": "#694226",
            "sandals": "#6e472b",
            "accessories": ["saffron_neck_scarf", "brass_bell_key", "leather_hip_pouch", "caligae_sandals"],
        },
        "expressions": [
            "calm_watchful",
            "anxious_alert",
            "wide_shock",
            "strained_pull",
            "determined_climb",
            "breathless_relief",
            "deadpan_disbelief",
        ],
        "hand_poses": [
            "rope_grip",
            "pin_catch",
            "open_recoil",
            "point_alert",
        ],
    },
    {
        "entity_key": "LYRA",
        "character_id": "char_lyra_master",
        "canonical_name": "LYRA",
        "entity_kind": "human",
        "rig_class": "human_squire_caricature_2d",
        "is_human_rig": True,
        "role": "Elderly Roman head bell-mistress and courtyard matron",
        "proportions": {
            "stature_scale": 0.91,
            "head_scale": 1.01,
            "head_radius_per_100u": 19.19,
            "shoulder_width_u": 11.8,
            "stoop_rad": 0.055,
        },
        "layered_parts": [
            "silver_braided_bun_hairpin",
            "far_arm_tapered",
            "undertunic_hem",
            "slate_indigo_stola_cel",
            "oat_palla_drape_fibula",
            "neck_and_round_squire_head",
            "elder_cheek_lines_and_features",
            "braided_crown_hair",
            "near_arm_and_articulated_hand",
            "planted_matron_sandals",
        ],
        "wardrobe": {
            "skin": "#f1e7d8",
            "skin_shade": "#d2c3bf",
            "hair": "elder_braided_bun",
            "hair_color": "#9e9a95",
            "tunic": "#415980",
            "tunic_shadow": "#2b3d59",
            "tunic_deep": "#1c293d",
            "undertunic": "#dfd3be",
            "palla": "#d8c39e",
            "belt": "#8c6635",
            "sandals": "#5c3d28",
            "accessories": ["bronze_fibula_brooch", "silver_bun_hairpin", "woven_border_palla"],
        },
        "expressions": [
            "calm_watchful",
            "sleepy_blink",
            "startled_gasp",
            "grumpy_glare",
            "anxious_alert",
            "wry_amusement",
        ],
        "hand_poses": [
            "lantern_hold",
            "palm_raised_react",
            "point_alert",
        ],
    },
    {
        "entity_key": "PIP",
        "character_id": "animal_pip_goat",
        "canonical_name": "PIP",
        "entity_kind": "animal",
        "rig_class": "quadruped_animal_2d",
        "is_human_rig": False,
        "role": "Mischievous small Roman hilltop goat (quadruped 2D rig, non-human)",
        "proportions": {
            "withers_height_ratio": 0.44,
            "head_radius_per_100u": 21.5,
            "horn_curve": True,
            "cloven_hoof": True,
        },
        "layered_parts": [
            "far_quadruped_legs_cloven",
            "perky_tail",
            "compact_barrel_coat_cel",
            "near_quadruped_legs_cloven",
            "red_braided_wool_collar_toggle",
            "curved_horns_and_droopy_ear",
            "goat_head_rectangular_pupil_snout",
        ],
        "wardrobe": {
            "coat": "#efe3cc",
            "coat_shadow": "#cbbba0",
            "dark_markings": "#4c382c",
            "horns": "#bfa070",
            "collar": "#b84234",
            "accessories": ["red_wool_collar_cord", "wooden_toggle"],
        },
        "actions": [
            "rope_nudge",
            "curious_tilt",
            "sneeze_anticipation",
            "sneeze_burst",
        ],
    },
]


def derive_character_identity(script_entities: Any = None) -> Dict[str, Any]:
    """Derive locked canonical character identities from script entity specs (or default KH-02 cast)."""
    raw_list = script_entities if isinstance(script_entities, list) and len(script_entities) > 0 else DEFAULT_ROMAN_BELL_CAST
    characters: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_names = set()
    for item in raw_list:
        entry = copy.deepcopy(item)
        cid = str(entry["character_id"])
        cname = str(entry["canonical_name"]).upper()
        if cid in seen_ids or cname in seen_names:
            raise ValueError(f"Duplicate character_id='{cid}' or canonical_name='{cname}'")
        seen_ids.add(cid)
        seen_names.add(cname)
        entry["canonical_name"] = cname
        entry["identity_hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        characters.append(entry)

    bible = {
        "schema_version": "kh02_character_bible.v1",
        "human_character_count": sum(1 for c in characters if c.get("is_human_rig") is True),
        "animal_character_count": sum(1 for c in characters if c.get("is_human_rig") is False),
        "characters": characters,
    }
    bible["bible_sha256"] = hashlib.sha256(
        json.dumps(bible, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return bible


def build_character_turnaround_2d(identity: Dict[str, Any], style: Dict[str, Any] | str = "squire_cinematic_2d.v1") -> Dict[str, Any]:
    """Build deterministic 2D turnaround sheet specifications (front / three_quarter / profile) for human cast."""
    profile = load_squire_style_profile(style) if isinstance(style, str) else style
    sheets = []
    for char in identity.get("characters", []):
        if not char.get("is_human_rig"):
            continue
        views = []
        for vw in REQUIRED_VIEWS:
            views.append({
                "view": vw,
                "castId": char["entity_key"],
                "character_id": char["character_id"],
                "canonical_name": char["canonical_name"],
                "expression": "calm_watchful",
                "rightHandPose": char["hand_poses"][0],
                "leftHandPose": char["hand_poses"][1],
                "outline_hex": profile["protected_production_default"]["outline_hex"],
                "wardrobe_lock_hash": hashlib.sha256(
                    json.dumps(char["wardrobe"], sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
            })
        sheets.append({
            "character_id": char["character_id"],
            "canonical_name": char["canonical_name"],
            "rig_class": char["rig_class"],
            "style_id": profile["style_id"],
            "views": views,
        })
    return {"schema_version": "kh02_turnaround_2d.v1", "style_id": profile["style_id"], "turnarounds": sheets}


def build_expression_sheet_2d(identity: Dict[str, Any], style: Dict[str, Any] | str = "squire_cinematic_2d.v1") -> Dict[str, Any]:
    """Build deterministic 6+ state expression + hand-pose sheet specs per human character."""
    profile = load_squire_style_profile(style) if isinstance(style, str) else style
    sheets = []
    for char in identity.get("characters", []):
        if not char.get("is_human_rig"):
            continue
        expr_cells = []
        for idx, expr_name in enumerate(char.get("expressions", [])):
            hpose = char["hand_poses"][idx % len(char["hand_poses"])]
            expr_cells.append({
                "cell_index": idx,
                "expression": expr_name,
                "hand_pose": hpose,
                "view": "three_quarter",
                "head_radius_per_100u": char["proportions"]["head_radius_per_100u"],
            })
        sheets.append({
            "character_id": char["character_id"],
            "canonical_name": char["canonical_name"],
            "expression_count": len(expr_cells),
            "hand_poses": list(char["hand_poses"]),
            "cells": expr_cells,
        })
    return {"schema_version": "kh02_expression_sheet_2d.v1", "style_id": profile["style_id"], "sheets": sheets}


def write_character_continuity_manifest(
    identity: Dict[str, Any],
    assets: Dict[str, Any],
    out_path: Path | None = None,
) -> Dict[str, Any]:
    """Assemble and optionally write character continuity manifest with rendered sheet hashes."""
    turnarounds = build_character_turnaround_2d(identity)
    expressions = build_expression_sheet_2d(identity)
    manifest = {
        "schema_version": "kh02_character_continuity.v1",
        "bible_sha256": identity["bible_sha256"],
        "human_character_count": identity["human_character_count"],
        "animal_character_count": identity["animal_character_count"],
        "characters": identity["characters"],
        "turnarounds": turnarounds["turnarounds"],
        "expression_sheets": expressions["sheets"],
        "rendered_assets": copy.deepcopy(assets or {}),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def validate_character_model_consistency(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Validate character uniqueness, rig honesty (goat != human), views, expressions, hand poses, and wardrobe locks."""
    errors: List[str] = []
    chars = manifest.get("characters", [])
    humans = [c for c in chars if c.get("entity_kind") == "human"]
    animals = [c for c in chars if c.get("entity_kind") != "human"]

    if len(humans) < 2:
        errors.append(f"Expected >= 2 distinct human characters, got {len(humans)}")

    # Ensure goat or non-human entities are never claimed as human rigs
    for ani in animals:
        if ani.get("is_human_rig") is True or "human" in str(ani.get("rig_class", "")).lower():
            errors.append(f"Non-human entity '{ani.get('canonical_name')}' falsely marked as human rig")

    # Ensure human characters have distinct palettes, hair, and proportions (not soldier clones)
    tunic_colors = set()
    hair_styles = set()
    for hc in humans:
        cname = hc.get("canonical_name", "UNKNOWN")
        w = hc.get("wardrobe", {})
        tunic_colors.add(w.get("tunic"))
        hair_styles.add(w.get("hair"))
        if len(hc.get("expressions", [])) < MIN_HUMAN_EXPRESSIONS:
            errors.append(f"Human character '{cname}' has < {MIN_HUMAN_EXPRESSIONS} expressions")
        if len(hc.get("hand_poses", [])) < MIN_HUMAN_HAND_POSES:
            errors.append(f"Human character '{cname}' has < {MIN_HUMAN_HAND_POSES} hand poses")
        if len(hc.get("layered_parts", [])) < 6:
            errors.append(f"Human character '{cname}' lacks layered 2D part specification")

    if len(tunic_colors) < len(humans) or len(hair_styles) < len(humans):
        errors.append("Human characters share identical tunic color or hair style (clone violation)")

    # Validate turnaround views
    turn_map = {t["character_id"]: t for t in manifest.get("turnarounds", [])}
    for hc in humans:
        t = turn_map.get(hc["character_id"])
        if not t:
            errors.append(f"Missing turnaround spec for '{hc['character_id']}'")
            continue
        present_views = {v["view"] for v in t.get("views", [])}
        for rv in REQUIRED_VIEWS:
            if rv not in present_views:
                errors.append(f"Turnaround for '{hc['character_id']}' missing view '{rv}'")

    # Validate rendered assets if recorded
    for rel_path, meta in (manifest.get("rendered_assets") or {}).items():
        fpath = Path(meta.get("abs_path") or rel_path)
        if not fpath.is_file():
            errors.append(f"Rendered character asset missing on disk: {rel_path}")
        elif meta.get("sha256"):
            actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual_sha != meta["sha256"]:
                errors.append(f"SHA-256 mismatch for character asset '{rel_path}'")

    return {
        "valid": len(errors) == 0,
        "human_characters": [h["canonical_name"] for h in humans],
        "non_human_entities": [a["canonical_name"] for a in animals],
        "errors": errors,
    }


if __name__ == "__main__":
    ident = derive_character_identity()
    man = write_character_continuity_manifest(ident, {})
    res = validate_character_model_consistency(man)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["valid"] else 1)
