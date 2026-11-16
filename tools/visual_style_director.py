"""tools/visual_style_director.py — Universal Visual Style Director & Contract Validator (KH-01.1).

Maintains FL-01's unified pipeline by locking modern expressive 2D linework, cel-shading bands,
silhouette contrast, and facial acting rules while adapting palettes, costumes, materials, and
architecture to any script niche (Roman forum, modern science, everyday business, museum, etc.).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from tools.visual_storytelling import SceneObjective, StoryContext, infer_niche_from_script

ROOT_DIR = Path(__file__).resolve().parent.parent
STYLES_ROOT = ROOT_DIR / "visual_styles"

FORBIDDEN_ASSET_TOKENS: Tuple[str, ...] = (
    "kh-01_style_references_only",
    "fxuwqg7ujkg",
    "rigbytron",
    "nila.",
    "fl01_v14_7_night_warning",
    "fl01_v14_7_1_bridge",
    "fl01_v14_7_2_ballista",
    "fl01_v14_7_3_roman_continuity",
    "fl01_v14_7_4_roman_arrow",
    "fl01_v14_7_5_roman_eagle",
    "fl01_v14_7_5_1_roman_water_gate",
    "fl01_v14_7_6_roman_last_light_portus",
)


def _hex_to_rel_luminance(hex_color: str) -> float:
    h = str(hex_color or "#000000").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return 0.0
    rgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def compute_contrast_ratio(hex_a: str, hex_b: str) -> float:
    l1 = _hex_to_rel_luminance(hex_a)
    l2 = _hex_to_rel_luminance(hex_b)
    hi, lo = max(l1, l2), min(l1, l2)
    return round((hi + 0.05) / (lo + 0.05), 3)


def _compute_core_lock_digest(raw_bible: Dict[str, Any]) -> str:
    locked_subset = {
        "style_id": raw_bible.get("style_id"),
        "ink_linework": raw_bible.get("ink_linework"),
        "silhouette_and_proportions": raw_bible.get("silhouette_and_proportions"),
        "facial_acting": raw_bible.get("facial_acting"),
        "cel_shading_and_lighting": raw_bible.get("cel_shading_and_lighting"),
        "clothing_and_materials": raw_bible.get("clothing_and_materials"),
        "fx_discipline": raw_bible.get("fx_discipline"),
    }
    canon = json.dumps(locked_subset, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class StyleProfile(BaseModel):
    """Validated immutable Style Lock profile loaded from `visual_styles/<name>/v1/style_bible.json`."""

    model_config = ConfigDict(frozen=True)

    schema_version: str
    style_id: str
    style_name: str
    version: str
    editorial_origin: str
    style_reference_manifest_path: str
    reference_availability: str
    style_lock_digest: str
    computed_lock_digest: str
    asset_resolution_target: Dict[str, Any]
    ink_linework: Dict[str, Any]
    silhouette_and_proportions: Dict[str, Any]
    facial_acting: Dict[str, Any]
    cel_shading_and_lighting: Dict[str, Any]
    clothing_and_materials: Dict[str, Any]
    texture_and_perspective: Dict[str, Any]
    environment_detail_tiers_by_scale: Dict[str, Any]
    camera_composition_and_safe_zones: Dict[str, Any]
    typography_and_legibility: Dict[str, Any]
    fx_discipline: Dict[str, Any]
    niche_overrides: Dict[str, Dict[str, Any]]


class StyleInstance(BaseModel):
    """Resolved per-project / per-niche style instance preserving core line & cel-shading locks."""

    model_config = ConfigDict(frozen=True)

    style_id: str
    style_lock_digest: str
    niche: str
    aspect: Literal["16:9", "9:16"] = "16:9"
    temperature: str
    sky_palette: Tuple[str, ...]
    ground_palette: Tuple[str, ...]
    architecture_palette: Tuple[str, ...]
    accent_palette: Tuple[str, ...]
    key_light_hex: str
    shadow_tint_hex: str
    character_outer_ink_hex: str
    character_inner_ink_hex: str
    environment_mid_ink_hex: str
    environment_far_ink_hex: str
    outer_stroke_to_actor_height_range: Tuple[float, float]
    inner_detail_to_outer_stroke_ratio: Tuple[float, float]
    cel_value_groups: int
    wardrobe_templates: Tuple[str, ...]
    material_motifs: Tuple[str, ...]
    required_views: Tuple[str, ...]
    required_expressions: Tuple[str, ...]
    safe_zone: Dict[str, float]
    poster_fx_enabled: bool = False
    reference_availability: str = "STYLE_REFERENCE_UNAVAILABLE"


class ShotArtPlan(BaseModel):
    """Per-shot art direction plan linking narrative objective to framing, lighting, detail tier, and wardrobe."""

    shot_id: str
    style_id: str
    niche: str
    start_sec: float
    end_sec: float
    camera_scale: Literal["wide", "medium", "close", "macro"]
    viewpoint_target: str
    silhouette_focus: str
    facial_expression_target: str
    hand_pose_target: str
    lighting_mood: str
    key_light_hex: str
    rim_intensity: float
    environment_detail_tier: str
    foreground_occlusion_enabled: bool
    outfit_state_by_actor: Dict[str, str] = Field(default_factory=dict)
    outfit_change_reason: Optional[str] = None
    fx_budget: int = 0


STYLE_PATH_REGISTRY: Dict[str, Path] = {
    "modern_expressive_2d.v1": STYLES_ROOT / "modern_expressive_2d" / "v1" / "style_bible.json",
    "modern_expressive_2d": STYLES_ROOT / "modern_expressive_2d" / "v1" / "style_bible.json",
}


def load_style_profile(profile_id: str = "modern_expressive_2d.v1") -> StyleProfile:
    """Load and validate an immutable `StyleProfile` from `visual_styles/`."""
    bible_path = STYLE_PATH_REGISTRY.get(profile_id)
    if bible_path is None:
        candidate = STYLES_ROOT / profile_id.replace(".", "/") / "style_bible.json"
        if candidate.is_file():
            bible_path = candidate
    if bible_path is None or not bible_path.is_file():
        raise FileNotFoundError(f"Unknown or missing style profile '{profile_id}' (expected under {STYLES_ROOT})")

    raw = json.loads(bible_path.read_text(encoding="utf-8"))
    ref_rel = str(raw.get("style_reference_manifest_path") or "")
    ref_abs = ROOT_DIR / ref_rel if ref_rel else bible_path.parent / "style_reference_manifest.json"
    if not ref_abs.is_file():
        raise ValueError(f"Style profile '{profile_id}' missing style_reference_manifest.json at {ref_abs}")

    ref_data = json.loads(ref_abs.read_text(encoding="utf-8"))
    if ref_data.get("public_repo_payload_included") is True:
        raise ValueError("Forbidden: copyrighted reference frame payload cannot be included in public repo")

    req_views = list((raw.get("silhouette_and_proportions") or {}).get("required_authored_views") or [])
    if not {"front", "three_quarter", "profile"}.issubset(set(req_views)):
        raise ValueError(f"Style profile '{profile_id}' must require front, three_quarter, and profile views")

    req_exprs = list((raw.get("facial_acting") or {}).get("required_distinct_expressions") or [])
    if len(set(req_exprs)) < 6:
        raise ValueError(f"Style profile '{profile_id}' must define >= 6 distinct facial expressions")

    computed_digest = _compute_core_lock_digest(raw)
    return StyleProfile(
        schema_version=str(raw["schema_version"]),
        style_id=str(raw["style_id"]),
        style_name=str(raw["style_name"]),
        version=str(raw["version"]),
        editorial_origin=str(raw["editorial_origin"]),
        style_reference_manifest_path=ref_rel,
        reference_availability=str(ref_data.get("reference_status") or raw.get("reference_availability") or "STYLE_REFERENCE_UNAVAILABLE"),
        style_lock_digest=str(raw.get("style_lock_digest") or computed_digest),
        computed_lock_digest=computed_digest,
        asset_resolution_target=dict(raw["asset_resolution_target"]),
        ink_linework=dict(raw["ink_linework"]),
        silhouette_and_proportions=dict(raw["silhouette_and_proportions"]),
        facial_acting=dict(raw["facial_acting"]),
        cel_shading_and_lighting=dict(raw["cel_shading_and_lighting"]),
        clothing_and_materials=dict(raw["clothing_and_materials"]),
        texture_and_perspective=dict(raw["texture_and_perspective"]),
        environment_detail_tiers_by_scale=dict(raw["environment_detail_tiers_by_scale"]),
        camera_composition_and_safe_zones=dict(raw["camera_composition_and_safe_zones"]),
        typography_and_legibility=dict(raw["typography_and_legibility"]),
        fx_discipline=dict(raw["fx_discipline"]),
        niche_overrides=dict(raw.get("niche_overrides") or {}),
    )


def resolve_visual_style(
    script_context: Any,
    niche: Optional[str] = None,
    shot_requirements: Optional[Dict[str, Any]] = None,
    style_id: str = "modern_expressive_2d.v1",
) -> StyleInstance:
    """Resolve a domain-adapted `StyleInstance` while preserving the locked linework & shading language."""
    profile = load_style_profile(style_id)
    req = dict(shot_requirements or {})

    if isinstance(script_context, StoryContext):
        script_text = " ".join(str(b.get("line", "")) for b in script_context.beats)
        ctx_niche = niche or script_context.niche
        aspect: Literal["16:9", "9:16"] = script_context.aspect
    elif isinstance(script_context, dict):
        beats = script_context.get("beats") or script_context.get("shots") or []
        script_text = str(script_context.get("script_text") or " ".join(str(b.get("line", "")) for b in beats))
        ctx_niche = niche or script_context.get("niche")
        aspect = "9:16" if script_context.get("aspect") == "9:16" else "16:9"
    else:
        script_text = str(script_context or "")
        ctx_niche = niche
        aspect = "9:16" if req.get("aspect") == "9:16" else "16:9"

    resolved_niche = infer_niche_from_script(script_text, explicit_niche=ctx_niche)
    override_map = profile.niche_overrides
    if resolved_niche in override_map:
        ov = override_map[resolved_niche]
    elif "roman" in resolved_niche:
        ov = override_map["roman_forum"]
    elif "science" in resolved_niche or "lab" in resolved_niche or "tech" in resolved_niche:
        ov = override_map["modern_science"]
    elif "museum" in resolved_niche or "astronomy" in resolved_niche or "planetarium" in resolved_niche:
        ov = override_map["holdout_astronomy_museum"]
    else:
        ov = override_map["everyday_business"]

    ink = profile.ink_linework
    safe_key = "safe_zone_9x16" if aspect == "9:16" else "safe_zone_16x9"
    poster_fx = bool(req.get("poster_thumbnail_mode", False)) and bool(
        profile.fx_discipline.get("poster_thumbnail_accent_opt_in_only", True)
    )

    return StyleInstance(
        style_id=profile.style_id,
        style_lock_digest=profile.computed_lock_digest,
        niche=resolved_niche,
        aspect=aspect,
        temperature=str(ov["temperature"]),
        sky_palette=tuple(ov["sky_palette"]),
        ground_palette=tuple(ov["ground_palette"]),
        architecture_palette=tuple(ov["architecture_palette"]),
        accent_palette=tuple(ov["accent_palette"]),
        key_light_hex=str(ov["key_light_hex"]),
        shadow_tint_hex=str(ov["shadow_tint_hex"]),
        character_outer_ink_hex=str(ink["character_outer_ink_hex"]),
        character_inner_ink_hex=str(ink["character_inner_ink_hex"]),
        environment_mid_ink_hex=str(ink["environment_mid_ink_hex"]),
        environment_far_ink_hex=str(ink["environment_far_ink_hex"]),
        outer_stroke_to_actor_height_range=(
            float(ink["outer_stroke_to_actor_height_range"][0]),
            float(ink["outer_stroke_to_actor_height_range"][1]),
        ),
        inner_detail_to_outer_stroke_ratio=(
            float(ink["inner_detail_to_outer_stroke_ratio"][0]),
            float(ink["inner_detail_to_outer_stroke_ratio"][1]),
        ),
        cel_value_groups=int(profile.cel_shading_and_lighting["value_group_count_range"][1]),
        wardrobe_templates=tuple(ov["wardrobe_templates"]),
        material_motifs=tuple(ov["material_motifs"]),
        required_views=tuple(profile.silhouette_and_proportions["required_authored_views"]),
        required_expressions=tuple(profile.facial_acting["required_distinct_expressions"]),
        safe_zone=dict(profile.camera_composition_and_safe_zones[safe_key]),
        poster_fx_enabled=poster_fx,
        reference_availability=profile.reference_availability,
    )


def build_shot_art_direction(
    scene_objective: SceneObjective | Dict[str, Any],
    script_timing: Dict[str, Any],
    style_instance: StyleInstance,
) -> ShotArtPlan:
    """Build motivated shot-level art direction (`ShotArtPlan`) from scene objective and timing."""
    obj = (
        scene_objective
        if isinstance(scene_objective, SceneObjective)
        else SceneObjective.model_validate(scene_objective)
    )
    start_sec = float(script_timing.get("start", 0.0))
    end_sec = float(script_timing.get("end", start_sec + float(script_timing.get("dur", 3.5))))
    line_low = str(script_timing.get("line") or obj.narrative_goal or "").lower()
    explicit_scale = script_timing.get("scale")

    if explicit_scale in ("wide", "medium", "close", "macro"):
        scale: Literal["wide", "medium", "close", "macro"] = explicit_scale
    elif obj.pacing_role == "HOOK" and any(w in line_low for w in ("scroll", "sliding", "gust", "macro", "seal")):
        scale = "macro"
    elif any(w in line_low for w in ("read", "order", "close", "unfold", "tomorrow", "deadpan")):
        scale = "close"
    elif any(w in line_low for w in ("forum", "chase", "street", "crowd", "wide", "fountain")):
        scale = "wide"
    else:
        scale = "medium"

    if scale == "macro":
        viewpoint = "three_quarter"
        detail_tier = "TIER_1_TACTILE_PROP_FOCUS"
        fg_occl = False
    elif scale == "close":
        viewpoint = "three_quarter" if "laugh" not in line_low else "front"
        detail_tier = "TIER_1_GRAPHIC_MOOD_BACKDROP"
        fg_occl = False
    elif scale == "wide":
        viewpoint = "profile" if any(w in line_low for w in ("chase", "run", "wind", "jump")) else "three_quarter"
        detail_tier = "TIER_3_FULL_ARCHITECTURAL_STAGE"
        fg_occl = True
    else:
        viewpoint = "three_quarter"
        detail_tier = "TIER_2_FOCUSED_STAGE"
        fg_occl = True

    if any(w in line_low for w in ("gust", "urgent", "read", "shock", "widen", "miss")):
        expr = "wide_shock"
    elif any(w in line_low for w in ("cart", "brace", "strain", "heavy", "caught", "jump")):
        expr = "strained_exertion"
    elif any(w in line_low for w in ("tomorrow", "postponed", "deadpan")):
        expr = "deadpan_disbelief"
    elif any(w in line_low for w in ("laugh", "relief", "safe", "smile")):
        expr = "joyful_laugh"
    elif any(w in line_low for w in ("chase", "lose", "vanish", "duck", "wind")):
        expr = "determined_focus"
    else:
        expr = "neutral_attentive"

    hand_pose = (
        "locked_grip"
        if any(w in line_low for w in ("caught", "catch", "brace", "steady", "read", "unfold", "hold", "pass"))
        else ("open_reach" if any(w in line_low for w in ("lunge", "miss", "reach")) else "relaxed")
    )

    actors = list(script_timing.get("actor_ids") or ([obj.focal_subject] if obj.focal_subject else ["lead_actor"]))
    outfits: Dict[str, str] = {}
    default_wt = style_instance.wardrobe_templates[0] if style_instance.wardrobe_templates else "standard_garment"
    alt_wt = style_instance.wardrobe_templates[1] if len(style_instance.wardrobe_templates) > 1 else default_wt
    for idx, aid in enumerate(actors):
        outfits[str(aid)] = str((script_timing.get("outfits") or {}).get(aid) or (default_wt if idx == 0 else alt_wt))

    fx_budget = 12 if any(w in line_low for w in ("wind", "gust", "cart", "fountain", "chase")) else 4

    return ShotArtPlan(
        shot_id=obj.shot_id,
        style_id=style_instance.style_id,
        niche=style_instance.niche,
        start_sec=round(start_sec, 4),
        end_sec=round(end_sec, 4),
        camera_scale=scale,
        viewpoint_target=viewpoint,
        silhouette_focus=obj.focal_subject or (actors[0] if actors else "hero"),
        facial_expression_target=expr,
        hand_pose_target=hand_pose,
        lighting_mood=f"{style_instance.temperature}_{obj.pacing_role.lower()}",
        key_light_hex=style_instance.key_light_hex,
        rim_intensity=0.34 if scale in ("close", "macro") else 0.24,
        environment_detail_tier=detail_tier,
        foreground_occlusion_enabled=fg_occl,
        outfit_state_by_actor=outfits,
        outfit_change_reason=script_timing.get("outfit_change_reason"),
        fx_budget=fx_budget,
    )


def validate_style_contract(
    style_instance: StyleInstance,
    asset_manifest: Dict[str, Any],
    shots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Fail-closed contract validator for KH-01 visual style & assets.
    Hard-rejects:
      - missing source files or SHA-256 mismatch
      - missing required views (`front`, `three_quarter`, `profile`) or < 6 distinct expressions
      - incoherent dimensions or missing licensing/provenance
      - style_id drift across shots or forbidden poster neon/halftone FX on scene shots
      - costume teleport across shots without an explicit `outfit_change_reason` / scene event
      - image alias or token match to reference frames, Rigby mascots, or legacy FL-01 previews
      - invalid ink-to-background / palette contrast
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(asset_manifest, dict) or not asset_manifest:
        return {"valid": False, "status": "FAIL", "errors": ["Empty or missing asset_manifest"], "warnings": []}

    # 1. Licensing & provenance fields
    license_id = str(asset_manifest.get("license") or asset_manifest.get("license_spdx") or "")
    provenance_origin = str(asset_manifest.get("provenance_origin") or asset_manifest.get("visual_generation_mode") or "")
    if not license_id or not provenance_origin:
        errors.append("Asset manifest missing mandatory license or provenance_origin metadata")

    if int(asset_manifest.get("reference_frames_reused", 0)) != 0:
        errors.append("Forbidden: reference_frames_reused != 0")
    if int(asset_manifest.get("prior_preview_derived_visual_inputs", 0)) != 0:
        errors.append("Forbidden: prior_preview_derived_visual_inputs != 0")

    # 2. Check authored files exist, match SHA-256, and do not alias forbidden assets
    forbidden_hashes: Set[str] = set(asset_manifest.get("forbidden_sha256_blocklist") or [])
    for item in asset_manifest.get("authored_files") or []:
        rel_p = str(item.get("path") or "")
        low_p = rel_p.lower()
        if any(tok in low_p for tok in FORBIDDEN_ASSET_TOKENS):
            errors.append(f"Forbidden reference/legacy asset alias detected in path '{rel_p}'")
        fp = Path(rel_p) if Path(rel_p).is_absolute() else (ROOT_DIR / rel_p)
        if not fp.is_file():
            errors.append(f"Declared authored asset missing on disk: '{rel_p}'")
            continue
        actual_sha = hashlib.sha256(fp.read_bytes()).hexdigest()
        if item.get("sha256") and actual_sha != item.get("sha256"):
            errors.append(f"SHA-256 mismatch on '{rel_p}' (expected {item.get('sha256')}, got {actual_sha})")
        if actual_sha in forbidden_hashes:
            errors.append(f"Asset '{rel_p}' matches forbidden reference/legacy SHA-256 {actual_sha}")
        dims = item.get("dimensions")
        if dims is not None:
            if not (isinstance(dims, (list, tuple)) and len(dims) == 2 and int(dims[0]) >= 64 and int(dims[1]) >= 64):
                errors.append(f"Incoherent asset dimensions {dims} on '{rel_p}'")

    # 3. Validate character views & expressions coverage
    chars = asset_manifest.get("characters") or {}
    if isinstance(chars, list):
        chars = {str(c.get("actor_id") or f"char_{i}"): c for i, c in enumerate(chars) if isinstance(c, dict)}
    for aid, cinfo in chars.items():
        views = set(cinfo.get("views") or cinfo.get("supported_views") or [])
        missing_views = set(style_instance.required_views) - views
        if missing_views:
            errors.append(f"Character '{aid}' missing required views: {sorted(missing_views)}")
        exprs = set(cinfo.get("expressions") or cinfo.get("supported_expressions") or [])
        if len(exprs) < 6:
            errors.append(f"Character '{aid}' has only {len(exprs)} distinct expressions (< 6 required)")

    # 4. Palette & ink contrast check
    bg_mid = style_instance.architecture_palette[0] if style_instance.architecture_palette else "#D8C8B0"
    ink_contrast = compute_contrast_ratio(style_instance.character_outer_ink_hex, bg_mid)
    if ink_contrast < 3.5:
        errors.append(
            f"Invalid palette contrast: character ink {style_instance.character_outer_ink_hex} vs stage {bg_mid} ratio={ink_contrast} (< 3.5)"
        )

    # 5. Shot-level style drift, FX discipline, and wardrobe continuity
    last_outfit: Dict[str, str] = {}
    last_color_sig: Dict[str, str] = {}
    for s in shots or []:
        sid = str(s.get("id") or s.get("shot_id") or "S01")
        args = s.get("args") or {}
        s_style = s.get("style_id") or args.get("styleId") or style_instance.style_id
        if s_style != style_instance.style_id:
            errors.append(f"Shot {sid}: style drift detected ('{s_style}' != '{style_instance.style_id}')")

        if args.get("chromaticAberration") or args.get("halftoneOverlay") or args.get("neonGlow"):
            if not s.get("is_poster_thumbnail", False):
                errors.append(f"Shot {sid}: poster-only FX (chromatic fringe/halftone/neon glow) forbidden in scene shot")

        art_plan = s.get("art_direction") or args.get("artDirection") or {}
        outfit_map = art_plan.get("outfit_state_by_actor") or {}
        change_reason = art_plan.get("outfit_change_reason") or s.get("outfit_change_reason")
        for aid, outfit in outfit_map.items():
            if aid in last_outfit and last_outfit[aid] != outfit and not change_reason:
                errors.append(
                    f"Shot {sid}: unmotivated costume teleport for '{aid}' ('{last_outfit[aid]}' -> '{outfit}') without scene event"
                )
            last_outfit[aid] = str(outfit)

        for p_entry in args.get("people") or []:
            if isinstance(p_entry, dict) and p_entry.get("id"):
                aid = str(p_entry["id"])
                col_sig = str(p_entry.get("primaryColor") or p_entry.get("outfitColor") or "")
                if col_sig:
                    if aid in last_color_sig and last_color_sig[aid] != col_sig and not change_reason:
                        errors.append(
                            f"Shot {sid}: character '{aid}' primary garment color changed mid-sequence ({last_color_sig[aid]} -> {col_sig}) without event"
                        )
                    last_color_sig[aid] = col_sig

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "style_id": style_instance.style_id,
        "style_lock_digest": style_instance.style_lock_digest,
        "niche": style_instance.niche,
        "ink_stage_contrast_ratio": ink_contrast,
        "errors": errors,
        "warnings": warnings,
    }
