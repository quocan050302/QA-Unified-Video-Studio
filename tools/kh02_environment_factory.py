#!/usr/bin/env python3
"""kh02_environment_factory.py — Deterministic 2D Layered Roman Location & Landmark Continuity Factory (KH-02.1).

Provides:
- derive_scene_spec(script_beats)
- build_original_layers(scene_spec)
- export_2d_scene_manifest(spec, layer_files)
- validate_scene_continuity(manifest)

Pure 2D multi-plane parallax architecture (3-5 layers). Forbids reusing old marketplace, scroll,
runaway cart, fountain, or fog legion stock imagery, and forbids claiming stretched bitmaps as camera angles.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

FORBIDDEN_REUSED_MOTIFS = (
    "marketplace_chase",
    "urgent_scroll",
    "runaway_cart",
    "market_awnings",
    "fountain_catch",
    "fog_legion_stock",
)


def derive_scene_spec(script_beats: Any = None) -> Dict[str, Any]:
    """Derive cohesive hilltop Roman bell-tower world specification & multi-angle camera views."""
    beats = script_beats if isinstance(script_beats, list) else []
    spec = {
        "schema_version": "kh02_environment_bible.v1",
        "location_id": "loc_janiculum_bell_tower",
        "location_name": "Roman Hilltop Civic Watch & Bell Tower at Pre-Dawn",
        "time_of_day_arc": "pre_dawn_indigo_to_apricot_horizon",
        "render_mode": "canvas2d_only",
        "fixed_world_landmarks": [
            {
                "landmark_id": "lm_5arch_aqueduct",
                "description": "Five-arch travertine Roman aqueduct spanning the eastern misty valley",
                "world_azimuth": "east_southeast",
            },
            {
                "landmark_id": "lm_twin_cypresses_umbrella_pine",
                "description": "Pair of tall Mediterranean cypresses beside one umbrella pine on western ridge",
                "world_azimuth": "west_ridge",
            },
            {
                "landmark_id": "lm_bronze_watch_bell_rig",
                "description": "Giant cast-bronze civic bell on mortised oak yoke with iron clapper and single coiled hemp rope",
                "world_azimuth": "tower_center_axis",
            },
        ],
        "views": [
            {
                "view_id": "belfry_lower_arch",
                "camera_projection_2d": "close_floor_level_2d",
                "purpose": "Close framing of coiled hemp rope base and Pip the goat with upper bell blurred in 2D depth",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_twin_cypresses_umbrella_pine", "lm_bronze_watch_bell_rig"],
                "layer_count": 5,
                "authored_geometry": "distinct_floor_arch_and_blurred_upper_belfry",
            },
            {
                "view_id": "belfry_wide_interior",
                "camera_projection_2d": "eye_level_wide_2d",
                "purpose": "Full belfry arch showing oak crossbeam, bronze bell, vertical rope, stone piers, and valley horizon",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_twin_cypresses_umbrella_pine", "lm_bronze_watch_bell_rig"],
                "layer_count": 5,
                "authored_geometry": "full_pier_arch_crossbeam_bell_and_slab_floor",
            },
            {
                "view_id": "belfry_low_angle",
                "camera_projection_2d": "authored_upward_2d_perspective",
                "purpose": "Artist-authored 2D upward framing of taut rope, hand grip, and looming bronze bell overhead",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_bronze_watch_bell_rig"],
                "layer_count": 5,
                "authored_geometry": "converging_2d_arch_soffit_and_overhead_yoke",
            },
            {
                "view_id": "tower_stairwell_ascent",
                "camera_projection_2d": "side_elevation_tracking_2d",
                "purpose": "Stepped travertine tower stairwell with arched window to aqueduct horizon and vertical rope shaft",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_twin_cypresses_umbrella_pine"],
                "layer_count": 5,
                "authored_geometry": "nine_step_travertine_risers_window_cutout_and_foreground_rail",
            },
            {
                "view_id": "belfry_catwalk_clapper",
                "camera_projection_2d": "upper_catwalk_medium_and_detail_2d",
                "purpose": "Upper maintenance oak catwalk directly beside bronze bell mouth and iron clapper bulb",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_bronze_watch_bell_rig"],
                "layer_count": 5,
                "authored_geometry": "upper_oak_catwalk_bell_mouth_cavity_and_clapper_shaft",
            },
            {
                "view_id": "hilltop_courtyard_wide",
                "camera_projection_2d": "exterior_wide_courtyard_2d",
                "purpose": "Cobbled courtyard below the bell tower with shuttered insula balcony, amphorae, and waking citizens",
                "visible_landmarks": ["lm_5arch_aqueduct", "lm_twin_cypresses_umbrella_pine", "lm_bronze_watch_bell_rig"],
                "layer_count": 5,
                "authored_geometry": "exterior_bell_tower_facade_insula_shutters_and_cobbled_court",
            },
        ],
        "beat_count_bound": len(beats),
    }
    spec["spec_sha256"] = hashlib.sha256(
        json.dumps(spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return spec


def build_original_layers(scene_spec: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate the explicit 5-layer Canvas2D parallax plane table for each authored camera view."""
    layers_by_view: Dict[str, List[Dict[str, Any]]] = {}
    for vw in scene_spec.get("views", []):
        vid = vw["view_id"]
        layers_by_view[vid] = [
            {
                "layer_id": f"{vid}__L0_sky_dawn",
                "plane": "L0_sky_atmosphere",
                "depth": 0.12,
                "elements": ["pre_dawn_gradient", "horizon_glow", "fading_stars", "stratified_clouds"],
            },
            {
                "layer_id": f"{vid}__L1_valley_landmarks",
                "plane": "L1_far_hills_aqueduct",
                "depth": 0.34,
                "elements": list(vw["visible_landmarks"]),
            },
            {
                "layer_id": f"{vid}__L2_mid_architecture",
                "plane": "L2_mid_architecture",
                "depth": 0.72,
                "elements": [vw["authored_geometry"], "travertine_masonry", "mortised_oak_timbers"],
            },
            {
                "layer_id": f"{vid}__L3_subject_stage",
                "plane": "L3_subject_stage",
                "depth": 1.00,
                "elements": ["bell_and_rope_mechanics", "planted_ground_or_treads", "cast_actors"],
            },
            {
                "layer_id": f"{vid}__L4_foreground_occluder",
                "plane": "L4_foreground_occluder",
                "depth": 1.25,
                "elements": ["dark_arch_spandrel_or_timber_rail_silhouette"],
            },
        ]
    return layers_by_view


def export_2d_scene_manifest(
    spec: Dict[str, Any],
    layer_files: Dict[str, Any] | None = None,
    out_path: Path | None = None,
) -> Dict[str, Any]:
    """Assemble and optionally write complete 2D environment continuity manifest."""
    layers = build_original_layers(spec)
    manifest = {
        "schema_version": "kh02_environment_manifest.v1",
        "location_id": spec["location_id"],
        "location_name": spec["location_name"],
        "render_mode": spec["render_mode"],
        "spec_sha256": spec["spec_sha256"],
        "fixed_world_landmarks": copy.deepcopy(spec["fixed_world_landmarks"]),
        "views": copy.deepcopy(spec["views"]),
        "layers_by_view": layers,
        "rendered_view_proofs": copy.deepcopy(layer_files or {}),
        "forbidden_motifs_absent": list(FORBIDDEN_REUSED_MOTIFS),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def validate_scene_continuity(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Validate >=3 genuinely distinct authored 2D views, 3-5 layers per view, landmark continuity, and hash distinctness."""
    errors: List[str] = []
    if manifest.get("render_mode") != "canvas2d_only":
        errors.append(f"Environment manifest render_mode must be 'canvas2d_only', got '{manifest.get('render_mode')}'")

    views = manifest.get("views", [])
    if len(views) < 3:
        errors.append(f"Expected >= 3 related views of new location, got {len(views)}")

    landmarks = {lm["landmark_id"] for lm in manifest.get("fixed_world_landmarks", [])}
    if len(landmarks) < 2:
        errors.append("Environment must define >= 2 fixed geographic/architectural landmarks")

    authored_geoms = set()
    layers_by_view = manifest.get("layers_by_view", {})
    for vw in views:
        vid = vw.get("view_id", "")
        authored_geoms.add(vw.get("authored_geometry"))
        v_layers = layers_by_view.get(vid, [])
        if not (3 <= len(v_layers) <= 5):
            errors.append(f"View '{vid}' must have 3..5 2D parallax layers, got {len(v_layers)}")
        vis = set(vw.get("visible_landmarks", []))
        if not vis.intersection(landmarks):
            errors.append(f"View '{vid}' shares zero fixed world landmarks with location '{manifest.get('location_id')}'")

    if len(authored_geoms) < len(views):
        errors.append("Multiple views share identical authored_geometry (stretched-bitmap angle violation)")

    # Verify rendered proof images are distinct files with distinct SHA-256 digests
    proof_hashes = set()
    proofs = manifest.get("rendered_view_proofs") or {}
    for view_key, meta in proofs.items():
        fpath = Path(meta.get("abs_path") or view_key)
        if not fpath.is_file():
            errors.append(f"Rendered environment view missing on disk: {view_key}")
            continue
        actual_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
        if meta.get("sha256") and actual_sha != meta["sha256"]:
            errors.append(f"SHA-256 mismatch for rendered view '{view_key}'")
        if actual_sha in proof_hashes:
            errors.append(f"Duplicate SHA-256 across environment views ('{view_key}')")
        proof_hashes.add(actual_sha)

    # Ensure no forbidden reused KH01 / old demo stock motifs appear in view descriptions
    blob = json.dumps(views).lower()
    for motif in FORBIDDEN_REUSED_MOTIFS:
        if motif in blob:
            errors.append(f"Forbidden reused motif '{motif}' detected in scene spec")

    return {
        "valid": len(errors) == 0,
        "location_id": manifest.get("location_id"),
        "view_count": len(views),
        "verified_proof_count": len(proof_hashes),
        "errors": errors,
    }


if __name__ == "__main__":
    sp = derive_scene_spec()
    man = export_2d_scene_manifest(sp, {})
    res = validate_scene_continuity(man)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["valid"] else 1)
