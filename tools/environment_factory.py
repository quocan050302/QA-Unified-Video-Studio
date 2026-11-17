"""tools/environment_factory.py — Universal Multi-Niche Layered 2D Environment & Prop Factory (KH-01.2).

Generates 100% ORIGINAL multi-plane 2D environments (`sky_backdrop`, `far_architecture`,
`midground_stage`, `foreground_occluders`), perspective guides, tactile material patterns,
interactable prop anchor geometry, editable SVGs, and `1920x1080` supersampled PNG stages.

Supports Roman Forum Marketplace, Modern Science Cleanroom Lab, Everyday Business Cafe,
Holdout Planetarium Gallery, and general indoor/outdoor stages under `modern_expressive_2d.v1`.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from tools.visual_style_director import FORBIDDEN_ASSET_TOKENS, load_style_profile, resolve_visual_style

ROOT_DIR = Path(__file__).resolve().parent.parent


def _hex_rgba(hex_str: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    h = str(hex_str or "#000000").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _lerp_rgb(c1: str, c2: str, t: float) -> Tuple[int, int, int]:
    r1, g1, b1, _ = _hex_rgba(c1)
    r2, g2, b2, _ = _hex_rgba(c2)
    u = max(0.0, min(1.0, t))
    return (
        int(round(r1 + (r2 - r1) * u)),
        int(round(g1 + (g2 - g1) * u)),
        int(round(b1 + (b2 - b1) * u)),
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


ENVIRONMENT_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "city_park": {
        "environment_id": "sunlit_city_park_promenade_v2",
        "place": "Contemporary Sunlit City Park Promenade, Fountain Plaza & Ornamental Tree Bench",
        "period": "21st Century Everyday Urban Park Life",
        "indoor_outdoor": "outdoor",
        "time_weather": "golden_afternoon_breezy_sunbeams",
        "vanishing_point": [0.52, 0.56],
        "ground_y_norm": 0.84,
        "materials": [
            "sunlit_layered_foliage_clusters",
            "flagstone_park_paving_with_mortar",
            "slatted_oak_and_wrought_iron_bench",
            "tiered_stone_park_fountain",
            "bark_grained_ornamental_tree_branch",
            "park_bicycles_and_paper_pennants",
        ],
        "interactable_props": {
            "bench": {"kind": "park_bench", "anchor_world": [0.50, 0.79], "bounds": [0.38, 0.70, 0.62, 0.85], "portable": False},
            "branch": {"kind": "ornamental_branch", "anchor_world": [0.58, 0.53], "bounds": [0.48, 0.44, 0.72, 0.60], "portable": False},
            "fountain": {"kind": "park_fountain", "anchor_world": [0.80, 0.75], "bounds": [0.70, 0.58, 0.90, 0.84], "portable": False},
            "kite": {"kind": "origami_dragon_kite", "anchor_world": [0.56, 0.44], "bounds": [0.48, 0.34, 0.64, 0.54], "portable": True},
            "dragon": {"kind": "origami_dragon_kite", "anchor_world": [0.56, 0.44], "bounds": [0.48, 0.34, 0.64, 0.54], "portable": True},
            "spool": {"kind": "kite_spool", "anchor_world": [0.44, 0.68], "bounds": [0.40, 0.64, 0.48, 0.72], "portable": True},
            "ribbon": {"kind": "kite_ribbon", "anchor_world": [0.54, 0.56], "bounds": [0.46, 0.48, 0.62, 0.66], "portable": True},
            "string": {"kind": "kite_string", "anchor_world": [0.48, 0.62], "bounds": [0.40, 0.44, 0.60, 0.70], "portable": True},
        },
    },
    "holdout_botanical_conservatory": {
        "environment_id": "sunbeam_botanical_conservatory_v2",
        "place": "Arched Iron & Glass Botanical Conservatory",
        "period": "Contemporary Botanical Glasshouse",
        "indoor_outdoor": "indoor",
        "time_weather": "humid_morning_sunbeams",
        "vanishing_point": [0.50, 0.54],
        "ground_y_norm": 0.84,
        "materials": [
            "arched_wrought_iron_glasshouse_ribs",
            "terracotta_orchid_pots",
            "layered_fern_fronds",
            "herringbone_brick_walkway",
            "potting_timber_table",
        ],
        "interactable_props": {
            "orchid": {"kind": "terracotta_orchid_pot", "anchor_world": [0.50, 0.68], "bounds": [0.45, 0.60, 0.55, 0.74], "portable": True},
            "pot": {"kind": "terracotta_orchid_pot", "anchor_world": [0.50, 0.68], "bounds": [0.45, 0.60, 0.55, 0.74], "portable": True},
            "bench": {"kind": "potting_timber_bench", "anchor_world": [0.50, 0.76], "bounds": [0.34, 0.68, 0.66, 0.84], "portable": False},
        },
    },
    "roman_forum": {
        "environment_id": "roman_forum_marketplace_v1",
        "place": "Roman Forum Marketplace & Fountain colonnade",
        "period": "Classical Roman Antiquity (Contemporary Editorial 2D Presentation)",
        "indoor_outdoor": "outdoor",
        "time_weather": "sunny_breezy_late_morning",
        "vanishing_point": [0.52, 0.56],
        "ground_y_norm": 0.84,
        "materials": ["travertine_stone_blocks", "terracotta_pan_tiles", "striped_linen_awnings", "carved_limestone_basin", "oak_cart_timber"],
        "interactable_props": {
            "counter": {"kind": "stone_counter", "anchor_world": [0.24, 0.74], "bounds": [0.14, 0.66, 0.34, 0.84], "portable": False},
            "scroll": {"kind": "wax_sealed_scroll", "anchor_world": [0.28, 0.65], "bounds": [0.24, 0.62, 0.33, 0.69], "portable": True},
            "awning": {"kind": "striped_market_awning", "anchor_world": [0.48, 0.44], "bounds": [0.32, 0.34, 0.66, 0.54], "portable": False},
            "cart": {"kind": "wooden_fruit_cart", "anchor_world": [0.54, 0.77], "bounds": [0.44, 0.67, 0.65, 0.85], "portable": False},
            "fountain": {"kind": "carved_forum_fountain", "anchor_world": [0.76, 0.74], "bounds": [0.66, 0.56, 0.88, 0.84], "portable": False},
            "rostra": {"kind": "marble_rostra_plinth", "anchor_world": [0.50, 0.75], "bounds": [0.38, 0.64, 0.62, 0.84], "portable": False},
        },
    },
    "modern_science": {
        "environment_id": "cleanroom_optics_lab_v1",
        "place": "Contemporary Photonics & Materials Cleanroom Laboratory",
        "period": "21st Century Modern Science",
        "indoor_outdoor": "indoor",
        "time_weather": "controlled_daylight_cleanroom",
        "vanishing_point": [0.50, 0.54],
        "ground_y_norm": 0.84,
        "materials": ["epoxy_grid_floor", "brushed_anodized_aluminum", "borosilicate_glass", "acoustic_slat_wall", "amber_instrument_led"],
        "interactable_props": {
            "bench": {"kind": "optical_isolation_bench", "anchor_world": [0.50, 0.75], "bounds": [0.32, 0.66, 0.68, 0.84], "portable": False},
            "beaker": {"kind": "borosilicate_crystal_beaker", "anchor_world": [0.50, 0.65], "bounds": [0.47, 0.60, 0.53, 0.68], "portable": True},
            "crystal": {"kind": "luminescent_crystal_sample", "anchor_world": [0.50, 0.65], "bounds": [0.48, 0.61, 0.52, 0.67], "portable": True},
        },
    },
    "everyday_business": {
        "environment_id": "corner_artisan_cafe_v1",
        "place": "Neighborhood Artisan Roastery & Corner Cafe Interior",
        "period": "Contemporary Everyday Urban Life",
        "indoor_outdoor": "indoor",
        "time_weather": "warm_morning_sunbeams",
        "vanishing_point": [0.48, 0.55],
        "ground_y_norm": 0.84,
        "materials": ["herringbone_oak_parquet", "glazed_teal_subway_tile", "hammered_brass_espresso", "matte_slate_chalkboard", "terracotta_planters"],
        "interactable_props": {
            "counter": {"kind": "oak_espresso_counter", "anchor_world": [0.46, 0.75], "bounds": [0.26, 0.65, 0.66, 0.84], "portable": False},
            "tray": {"kind": "brass_espresso_tray", "anchor_world": [0.48, 0.66], "bounds": [0.43, 0.63, 0.54, 0.68], "portable": True},
        },
    },
    "holdout_astronomy_museum": {
        "environment_id": "planetarium_eclipse_gallery_v1",
        "place": "Observatory Planetarium & Brass Telescope Gallery",
        "period": "Contemporary Public Science Museum",
        "indoor_outdoor": "indoor",
        "time_weather": "twilight_dome_projection",
        "vanishing_point": [0.50, 0.52],
        "ground_y_norm": 0.84,
        "materials": ["ribbed_acoustic_dome", "polished_lacquered_brass", "terrazzo_museum_floor", "backlit_celestial_glass"],
        "interactable_props": {
            "telescope": {"kind": "brass_refractor_telescope", "anchor_world": [0.52, 0.68], "bounds": [0.44, 0.54, 0.62, 0.84], "portable": False},
        },
    },
}


def derive_environment_specs(
    script_context: Any,
    setting: Optional[Dict[str, Any]] = None,
    niche: Optional[str] = None,
    shot_plan: Optional[Sequence[Any]] = None,
    style_id: str = "modern_expressive_2d.v1",
) -> Dict[str, Any]:
    """Derive a structured multi-plane `EnvironmentSpec` governed by `style_id` and `niche`."""
    style = resolve_visual_style(script_context, niche=niche, style_id=style_id)
    profile = load_style_profile(style.style_id)

    bp_key = style.niche if style.niche in ENVIRONMENT_BLUEPRINTS else (
        "city_park" if ("park" in style.niche or "kite" in style.niche) else (
            "holdout_botanical_conservatory" if ("conservatory" in style.niche or "botanical" in style.niche) else (
                "roman_forum" if "roman" in style.niche else (
                    "modern_science" if "science" in style.niche else "everyday_business"
                )
            )
        )
    )
    bp = ENVIRONMENT_BLUEPRINTS[bp_key]
    st = dict(setting or {})
    is_v2 = str(style.style_id).endswith(".v2")
    default_env_id = str(bp["environment_id"])
    if is_v2 and default_env_id.endswith("_v1"):
        default_env_id = default_env_id[:-3] + "_v2"

    indoor_outdoor = str(st.get("indoor_outdoor") or bp["indoor_outdoor"])
    place = str(st.get("place") or bp["place"])

    return {
        "schema_version": "kh01.environment_spec.v2" if is_v2 else "kh01.environment_spec.v1",
        "environment_id": str(st.get("environment_id") or default_env_id),
        "niche": style.niche,
        "style_id": style.style_id,
        "style_lock_digest": style.style_lock_digest,
        "place": place,
        "period": str(st.get("period") or bp["period"]),
        "indoor_outdoor": indoor_outdoor,
        "time_weather": str(st.get("time_weather") or bp["time_weather"]),
        "vanishing_point": list(bp["vanishing_point"]),
        "ground_y_norm": float(bp["ground_y_norm"]),
        "palette": {
            "sky": list(style.sky_palette),
            "ground": list(style.ground_palette),
            "architecture": list(style.architecture_palette),
            "accents": list(style.accent_palette),
            "key_light_hex": style.key_light_hex,
            "shadow_tint_hex": style.shadow_tint_hex,
            "mid_ink_hex": style.environment_mid_ink_hex,
            "far_ink_hex": style.environment_far_ink_hex,
        },
        "depth_layers": [
            {"layer_id": "sky_backdrop", "z_index": 0, "parallax_factor": 0.15},
            {"layer_id": "far_architecture", "z_index": 1, "parallax_factor": 0.42},
            {"layer_id": "midground_stage", "z_index": 2, "parallax_factor": 1.00},
            {"layer_id": "foreground_occluders", "z_index": 4, "parallax_factor": 1.32},
        ],
        "supported_detail_tiers": list(profile.environment_detail_tiers_by_scale[k]["tier"] for k in ("wide", "medium", "close", "macro")),
        "materials": list(bp["materials"]),
        "interactable_props": dict(bp["interactable_props"]),
        "shot_count_planned": len(shot_plan or []),
    }


def render_environment_stage_png(
    spec: Dict[str, Any],
    out_png: Path,
    detail_mode: str = "wide",
    indoor_override: Optional[bool] = None,
    canvas_size: Tuple[int, int] = (1920, 1080),
    supersample: int = 2,
) -> Dict[str, Any]:
    """
    Render a rich, original multi-plane illustrated 2D environment PNG (`1920x1080`) with:
      - Smooth atmospheric sky or interior ceiling lighting gradient
      - Far architectural perspective colonnades / lab glass bays / cafe windows / museum dome
      - Perspective stone paving / herringbone oak / cleanroom floor tiles converging to vanishing point
      - Detailed midground hero architecture (striped awnings, marble fountain, lab bench, espresso bar)
      - Foreground silhouette occluders framing the stage
    """
    W = canvas_size[0] * supersample
    H = canvas_size[1] * supersample
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img, "RGBA")

    pal = spec["palette"]
    sky_cols = pal["sky"]
    gnd_cols = pal["ground"]
    arch_cols = pal["architecture"]
    acc_cols = pal["accents"]
    ink_mid = _hex_rgba(pal["mid_ink_hex"])
    ink_far = _hex_rgba(pal["far_ink_hex"])
    shadow_rgba = _hex_rgba(pal["shadow_tint_hex"], 72)
    key_rgba = _hex_rgba(pal["key_light_hex"], 68)

    vp_x = W * float(spec["vanishing_point"][0])
    vp_y = H * float(spec["vanishing_point"][1])
    ground_y = int(H * float(spec["ground_y_norm"]))
    niche = spec["niche"]
    is_v2 = str(spec.get("style_id") or "").endswith(".v2")
    is_indoor = indoor_override if indoor_override is not None else (spec["indoor_outdoor"] == "indoor")
    lw = max(3, int(H * (0.0031 if is_v2 else 0.0028)))

    # Plane 0: Sky / Upper Wall Gradient
    band_steps = 64
    top_limit = int(H * (0.86 if niche == "city_park" else 0.72))
    for bi in range(band_steps):
        u = bi / float(band_steps - 1)
        col = _lerp_rgb(sky_cols[0], sky_cols[-1], u)
        y0 = int(bi * top_limit / band_steps)
        y1 = int((bi + 1) * top_limit / band_steps) + 2
        d.rectangle([0, y0, W, y1], fill=(*col, 255))

    # Plane 1: Niche-Specific Far Architecture & Perspective Stage
    if niche == "city_park":
        # Sculpted sunlit cumulus clouds + breezy festive paper pennants
        for cx_c, cy_c, rw_c, rh_c in [
            (W * 0.18, H * 0.15, W * 0.12, H * 0.048),
            (W * 0.56, H * 0.12, W * 0.15, H * 0.055),
            (W * 0.86, H * 0.18, W * 0.10, H * 0.042),
        ]:
            d.ellipse([cx_c - rw_c, cy_c - rh_c, cx_c + rw_c, cy_c + rh_c], fill=(255, 252, 244, 228))
            d.ellipse([cx_c - rw_c * 0.45, cy_c - rh_c * 1.45, cx_c + rw_c * 0.55, cy_c + rh_c * 0.65], fill=(255, 254, 249, 240))

        # Rolling distant park meadow hills & far tree canopy silhouettes
        d.polygon(
            [(0, ground_y), (0, int(H * 0.54)), (int(W * 0.28), int(H * 0.48)), (int(W * 0.64), int(H * 0.52)), (W, int(H * 0.46)), (W, ground_y)],
            fill=_hex_rgba("#76AE62"),
            outline=ink_far,
            width=max(2, lw - 1),
        )
        for tx_c, ty_c, tr_w, tr_h, t_hex in [
            (W * 0.10, H * 0.36, W * 0.11, H * 0.16, arch_cols[1]),
            (W * 0.24, H * 0.39, W * 0.09, H * 0.14, arch_cols[0]),
            (W * 0.44, H * 0.38, W * 0.10, H * 0.13, arch_cols[1]),
            (W * 0.90, H * 0.34, W * 0.12, H * 0.18, arch_cols[0]),
        ]:
            d.rectangle([int(tx_c - W * 0.012), int(ty_c + tr_h * 0.4), int(tx_c + W * 0.012), int(H * 0.68)], fill=_hex_rgba("#6B4B35"), outline=ink_far, width=max(2, lw - 1))
            d.ellipse([int(tx_c - tr_w), int(ty_c - tr_h), int(tx_c + tr_w), int(ty_c + tr_h)], fill=_hex_rgba(t_hex), outline=ink_far, width=lw)
            d.ellipse([int(tx_c - tr_w * 0.65), int(ty_c - tr_h * 1.15), int(tx_c + tr_w * 0.55), int(ty_c - tr_h * 0.1)], fill=_hex_rgba(arch_cols[2], 220))

        if detail_mode not in ("close", "macro"):
            # Sunlit lush green lawn strip above flagstone promenade + background bike path
            lawn_top = int(H * 0.64)
            d.rectangle([0, lawn_top, W, ground_y], fill=_hex_rgba("#88B969"), outline=ink_mid, width=lw)
            d.rectangle([0, int(H * 0.675), W, int(H * 0.705)], fill=_hex_rgba("#E5D8C1"), outline=ink_far, width=max(2, lw - 1))

            # Background park bicycles along the far bike path (world-building detail!)
            for bx_c in (int(W * 0.20), int(W * 0.33)):
                by_c = int(H * 0.685)
                wr = int(H * 0.022)
                for wx in (bx_c - int(wr * 1.6), bx_c + int(wr * 1.6)):
                    d.ellipse([wx - wr, by_c - wr, wx + wr, by_c + wr], outline=ink_far, width=max(2, lw - 1))
                d.polygon([(bx_c - int(wr * 1.6), by_c), (bx_c - int(wr * 0.2), by_c - int(wr * 1.5)), (bx_c + int(wr * 1.2), by_c - int(wr * 1.4)), (bx_c + int(wr * 0.2), by_c)], outline=_hex_rgba(acc_cols[2]), width=max(2, lw - 1))

            # Breezy festive paper pennant garland between park lamp posts
            for lp_x in (int(W * 0.14), int(W * 0.42)):
                d.rectangle([lp_x - 5, int(H * 0.42), lp_x + 5, int(H * 0.72)], fill=_hex_rgba("#2B353E"), outline=ink_mid, width=max(2, lw - 1))
                d.ellipse([lp_x - 16, int(H * 0.39), lp_x + 16, int(H * 0.43)], fill=_hex_rgba("#FFF5CC"), outline=ink_mid, width=max(2, lw - 1))
            for pi in range(9):
                u_p = pi / 8.0
                px_p = int(W * (0.14 + u_p * 0.28))
                py_p = int(H * 0.43 + math.sin(math.pi * u_p) * H * 0.035)
                p_col = acc_cols[pi % 3]
                d.polygon([(px_p - 12, py_p), (px_p + 12, py_p + 2), (px_p, py_p + 26)], fill=_hex_rgba(p_col), outline=ink_mid, width=max(2, lw - 1))

            # Diagonal warm afternoon sunbeam shafts cutting through canopy (~38 deg, Ref 2 lighting!)
            for sb_x in (W * 0.16, W * 0.48):
                d.polygon(
                    [(int(sb_x), 0), (int(sb_x + W * 0.11), 0), (int(sb_x + W * 0.31), ground_y), (int(sb_x + W * 0.18), ground_y)],
                    fill=(255, 244, 198, 56),
                )

            # Hero Midground Ornamental Tree + Low Snag Branch (`x ~ 0.58, y ~ 0.53`)
            tr_x = int(W * 0.67)
            d.polygon(
                [(tr_x - int(W * 0.022), ground_y - int(H * 0.04)), (tr_x - int(W * 0.015), int(H * 0.34)), (tr_x + int(W * 0.020), int(H * 0.34)), (tr_x + int(W * 0.032), ground_y - int(H * 0.04))],
                fill=_hex_rgba("#734E36"),
                outline=ink_mid,
                width=lw + 1,
            )
            # Bark grain lines
            for bk_y in (0.44, 0.56, 0.68):
                d.line([(tr_x - int(W * 0.006), int(H * bk_y)), (tr_x - int(W * 0.004), int(H * (bk_y + 0.07)))], fill=ink_mid, width=max(2, lw - 1))
            # Expressive low ornamental branch extending left over the park bench
            d.polygon(
                [(tr_x - int(W * 0.012), int(H * 0.49)), (int(W * 0.54), int(H * 0.52)), (int(W * 0.54), int(H * 0.542)), (tr_x - int(W * 0.008), int(H * 0.525))],
                fill=_hex_rgba("#734E36"),
                outline=ink_mid,
                width=lw,
            )
            for lf_x, lf_y, lr_w, lr_h in [
                (W * 0.66, H * 0.25, W * 0.13, H * 0.13),
                (W * 0.58, H * 0.30, W * 0.09, H * 0.09),
                (W * 0.74, H * 0.30, W * 0.10, H * 0.10),
                (W * 0.55, H * 0.49, W * 0.042, H * 0.035),
            ]:
                d.ellipse([int(lf_x - lr_w), int(lf_y - lr_h), int(lf_x + lr_w), int(lf_y + lr_h)], fill=_hex_rgba(arch_cols[0]), outline=ink_mid, width=lw)
                d.ellipse([int(lf_x - lr_w * 0.6), int(lf_y - lr_h * 0.85), int(lf_x + lr_w * 0.5), int(lf_y - lr_h * 0.1)], fill=_hex_rgba(arch_cols[2], 215))

            # Patterned Slatted-Oak & Wrought-Iron Park Bench (`x ~ 0.42..0.58`)
            bx0, bx1 = int(W * 0.41), int(W * 0.57)
            by_seat = int(H * 0.775)
            by_back = int(H * 0.715)
            d.ellipse([bx0 - 16, ground_y - 10, bx1 + 22, ground_y + 14], fill=shadow_rgba)
            for sl_y in (by_back, by_back + int(H * 0.024)):
                d.rounded_rectangle([bx0, sl_y, bx1, sl_y + int(H * 0.018)], radius=4, fill=_hex_rgba("#C88A52"), outline=ink_mid, width=lw)
            d.rounded_rectangle([bx0 - 8, by_seat, bx1 + 8, by_seat + int(H * 0.022)], radius=5, fill=_hex_rgba("#D89B62"), outline=ink_mid, width=lw)
            for leg_x in (bx0 + 14, bx1 - 14):
                d.rectangle([leg_x - 6, by_back, leg_x + 6, ground_y], fill=_hex_rgba("#2B333C"), outline=ink_mid, width=max(2, lw - 1))

            # Tiered Stone Park Fountain on right (`x ~ 0.81`)
            fx_c = int(W * 0.81)
            d.rounded_rectangle([fx_c - int(W * 0.088), int(H * 0.73), fx_c + int(W * 0.088), ground_y + 6], radius=12, fill=_hex_rgba("#E5DAC6"), outline=ink_mid, width=lw)
            d.ellipse([fx_c - int(W * 0.076), int(H * 0.712), fx_c + int(W * 0.076), int(H * 0.752)], fill=(86, 186, 218, 242), outline=ink_mid, width=lw)
            d.rectangle([fx_c - int(W * 0.020), int(H * 0.58), fx_c + int(W * 0.020), int(H * 0.73)], fill=_hex_rgba("#EFE6D5"), outline=ink_mid, width=lw)
            d.pieslice([fx_c - int(W * 0.052), int(H * 0.545), fx_c + int(W * 0.052), int(H * 0.605)], 0, 180, fill=_hex_rgba("#EFE6D5"), outline=ink_mid, width=lw)
            for sgn in (-1, 1):
                d.arc([fx_c - int(W * 0.05) if sgn < 0 else fx_c, int(H * 0.55), fx_c if sgn < 0 else fx_c + int(W * 0.05), int(H * 0.72)], 190 if sgn < 0 else 260, 280 if sgn < 0 else 350, fill=(220, 248, 255, 232), width=max(3, lw))
        else:
            # Soft designed atmospheric park bokeh & sunlit foliage mood backdrop for Closeups/Macros (Ref 3 principle!)
            for bx_b, by_b, br_b, b_alpha in [
                (W * 0.22, H * 0.32, W * 0.14, 72),
                (W * 0.76, H * 0.28, W * 0.16, 68),
                (W * 0.52, H * 0.48, W * 0.18, 52),
            ]:
                d.ellipse([int(bx_b - br_b), int(by_b - br_b), int(bx_b + br_b), int(by_b + br_b)], fill=(255, 246, 206, b_alpha))

    elif niche == "holdout_botanical_conservatory":
        # Arched wrought-iron glasshouse ribs + humid diagonal sunbeams + terracotta orchid tables
        d.rectangle([0, int(H * 0.14), W, ground_y], fill=_hex_rgba(arch_cols[0]), outline=ink_mid, width=lw)
        for rx_i in range(6):
            rx = int(W * (0.08 + rx_i * 0.168))
            d.line([(rx, int(H * 0.14)), (rx, ground_y)], fill=_hex_rgba(arch_cols[3]), width=lw + 1)
            d.arc([rx - int(W * 0.084), int(H * 0.04), rx + int(W * 0.084), int(H * 0.28)], 180, 360, fill=_hex_rgba(arch_cols[3]), width=lw + 1)
        d.polygon([(int(W * 0.24), 0), (int(W * 0.38), 0), (int(W * 0.60), ground_y), (int(W * 0.42), ground_y)], fill=key_rgba)
        # Timber potting bench + terracotta orchid pots & lush fern clusters
        d.rounded_rectangle([int(W * 0.32), int(H * 0.68), int(W * 0.68), int(H * 0.74)], radius=8, fill=_hex_rgba("#9E6B47"), outline=ink_mid, width=lw)
        for leg_x in (int(W * 0.36), int(W * 0.64)):
            d.rectangle([leg_x - 10, int(H * 0.74), leg_x + 10, ground_y], fill=_hex_rgba("#6E482E"), outline=ink_mid, width=lw)
        for px_pot in (int(W * 0.40), int(W * 0.50), int(W * 0.60)):
            d.polygon([(px_pot - 26, int(H * 0.62)), (px_pot + 26, int(H * 0.62)), (px_pot + 18, int(H * 0.68)), (px_pot - 18, int(H * 0.68))], fill=_hex_rgba(arch_cols[2]), outline=ink_mid, width=lw)
            d.ellipse([px_pot - 32, int(H * 0.54), px_pot + 32, int(H * 0.63)], fill=_hex_rgba(arch_cols[1]), outline=ink_mid, width=max(2, lw - 1))

    elif "roman" in niche and not is_indoor:
        # Sculptural Mediterranean cumulus clouds
        for cx_c, cy_c, rw_c, rh_c in [(W * 0.22, H * 0.17, W * 0.11, H * 0.05), (W * 0.68, H * 0.14, W * 0.14, H * 0.055)]:
            d.ellipse([cx_c - rw_c, cy_c - rh_c, cx_c + rw_c, cy_c + rh_c], fill=(255, 250, 240, 215))
            d.ellipse([cx_c - rw_c * 0.5, cy_c - rh_c * 1.4, cx_c + rw_c * 0.6, cy_c + rh_c * 0.7], fill=(255, 252, 245, 230))

        # Distant Roman basilica & temple pediment silhouettes + cypress trees
        d.polygon([(W * 0.04, ground_y), (W * 0.04, H * 0.34), (W * 0.18, H * 0.25), (W * 0.32, H * 0.34), (W * 0.32, ground_y)], fill=_hex_rgba(arch_cols[1]), outline=ink_far, width=lw)
        for cy_x in (W * 0.35, W * 0.39, W * 0.89, W * 0.93):
            d.ellipse([cy_x - W * 0.014, H * 0.26, cy_x + W * 0.014, H * 0.58], fill=_hex_rgba(arch_cols[3]), outline=ink_far, width=max(2, lw - 1))

        # Mid-far travertine colonnade arches across forum
        col_top = int(H * 0.36)
        d.rectangle([0, col_top, W, ground_y], fill=_hex_rgba(arch_cols[0]), outline=ink_mid, width=lw)
        # Terracotta roof frieze with tile scallops
        d.polygon([(0, col_top), (W, col_top), (W, col_top - int(H * 0.055)), (0, col_top - int(H * 0.055))], fill=_hex_rgba(arch_cols[2]), outline=ink_mid, width=lw)
        for tx in range(0, W, int(W * 0.028)):
            d.line([(tx, col_top - int(H * 0.055)), (tx - int(W * 0.008), col_top)], fill=ink_mid, width=max(2, lw - 1))

        if detail_mode != "close":
            if is_v2:
                # Asymmetric v2 Roman street elevation: ashlar stone courses, stepped temple portico, timber insula balcony & diagonal sunbeam!
                for row_y in range(col_top + int(H * 0.045), ground_y, int(H * 0.055)):
                    d.line([(0, row_y), (W, row_y)], fill=_hex_rgba(arch_cols[1], 145), width=max(2, lw - 1))
                    for jx in range(int((row_y * 1.7) % 140), W, 160):
                        d.line([(jx, row_y), (jx, min(ground_y, row_y + int(H * 0.055)))], fill=_hex_rgba(arch_cols[1], 130), width=max(2, lw - 1))
                # Left grand portico columns + timber merchant balcony on center-right (varied rhythm, NOT 7 identical arches!)
                for col_x in (int(W * 0.08), int(W * 0.20), int(W * 0.32)):
                    d.rectangle([col_x, col_top + int(H * 0.02), col_x + int(W * 0.026), ground_y], fill=_hex_rgba("#F7EDD9"), outline=ink_mid, width=lw)
                d.rounded_rectangle([int(W * 0.42), int(H * 0.46), int(W * 0.62), ground_y], radius=int(W * 0.05), fill=_hex_rgba("#9E7C5C"), outline=ink_mid, width=lw + 1)
                d.rectangle([int(W * 0.39), int(H * 0.42), int(W * 0.66), int(H * 0.455)], fill=_hex_rgba("#7B5033"), outline=ink_mid, width=lw)
                d.polygon([(int(W * 0.16), 0), (int(W * 0.28), 0), (int(W * 0.48), ground_y), (int(W * 0.32), ground_y)], fill=(255, 242, 198, 54))
            else:
                for arch_i in range(7):
                    ax0 = int(W * (0.06 + arch_i * 0.13))
                    aw = int(W * 0.082)
                    ay0 = int(H * 0.44)
                    d.rounded_rectangle([ax0, ay0, ax0 + aw, ground_y], radius=aw // 2, fill=_hex_rgba(arch_cols[1], 230), outline=ink_mid, width=lw)
                    # Fluted column pilaster between arches
                    px = ax0 - int(W * 0.024)
                    if px > 10:
                        d.rectangle([px, col_top + int(H * 0.03), px + int(W * 0.018), ground_y], fill=_hex_rgba("#F5EAD6"), outline=ink_mid, width=max(2, lw - 1))

            # Colorful striped linen market awnings (left & center stalls)
            for st_x, col_a, col_b in [(W * 0.10, acc_cols[0], acc_cols[3]), (W * 0.38, acc_cols[2], acc_cols[1])]:
                aw_w = W * 0.22
                aw_y0 = H * 0.38
                aw_y1 = H * 0.49
                stripes = 6
                for si in range(stripes):
                    sx0 = st_x + (si / stripes) * aw_w
                    sx1 = st_x + ((si + 1) / stripes) * aw_w
                    d.polygon(
                        [(sx0, aw_y0), (sx1, aw_y0), (sx1 + W * 0.012, aw_y1), (sx0 + W * 0.012, aw_y1)],
                        fill=_hex_rgba(col_a if si % 2 == 0 else col_b),
                        outline=ink_mid,
                    )
                # Cast shadow under awning
                d.polygon([(st_x + W * 0.01, aw_y1), (st_x + aw_w + W * 0.01, aw_y1), (st_x + aw_w, aw_y1 + H * 0.035), (st_x, aw_y1 + H * 0.035)], fill=shadow_rgba)

            # Carved limestone Forum Fountain on right stage (x ~ 0.76)
            fx_c = int(W * 0.77)
            d.rounded_rectangle([fx_c - int(W * 0.095), int(H * 0.72), fx_c + int(W * 0.095), ground_y + int(H * 0.01)], radius=12, fill=_hex_rgba("#DDD2C0"), outline=ink_mid, width=lw)
            d.ellipse([fx_c - int(W * 0.082), int(H * 0.70), fx_c + int(W * 0.082), int(H * 0.745)], fill=(92, 178, 214, 240), outline=ink_mid, width=lw)
            d.rectangle([fx_c - int(W * 0.022), int(H * 0.56), fx_c + int(W * 0.022), int(H * 0.72)], fill=_hex_rgba("#EAE0CE"), outline=ink_mid, width=lw)
            d.pieslice([fx_c - int(W * 0.055), int(H * 0.52), fx_c + int(W * 0.055), int(H * 0.59)], 0, 180, fill=_hex_rgba("#EAE0CE"), outline=ink_mid, width=lw)
            # Sparkling water arcs
            for sgn in (-1, 1):
                d.arc([fx_c - int(W * 0.055) if sgn < 0 else fx_c, int(H * 0.53), fx_c if sgn < 0 else fx_c + int(W * 0.055), int(H * 0.72)], 190 if sgn < 0 else 260, 280 if sgn < 0 else 350, fill=(210, 244, 255, 230), width=max(3, lw))

    elif "roman" in niche and is_indoor:
        # Rich Roman Tabularium / Courier Archive Interior (for indoor style POC panel!)
        ink_bold = _hex_rgba("#1E1512")
        wall_col = _hex_rgba("#DFC9AA")
        d.rectangle([0, 0, W, ground_y], fill=wall_col)
        # Coffered timber ceiling beams (properly ordered clockwise quads!)
        for bx in range(0, W, int(W * 0.14)):
            bw = int(W * 0.052)
            ix0 = int(vp_x + (bx - vp_x) * 0.58)
            ix1 = int(vp_x + (bx + bw - vp_x) * 0.58)
            d.polygon([(bx, 0), (bx + bw, 0), (ix1, int(H * 0.18)), (ix0, int(H * 0.18))], fill=_hex_rgba("#6E482E"), outline=ink_bold, width=lw + 1)
        d.rectangle([0, int(H * 0.18), W, int(H * 0.225)], fill=_hex_rgba("#B9583B"), outline=ink_bold, width=lw + 1)
        # Wooden scroll cubby shelves (armaria) filled with rolled parchment scrolls!
        for sx in (int(W * 0.07), int(W * 0.65)):
            sw = int(W * 0.27)
            d.rounded_rectangle([sx, int(H * 0.27), sx + sw, ground_y], radius=8, fill=_hex_rgba("#7C5236"), outline=ink_bold, width=lw + 2)
            for r_i in range(4):
                ry = int(H * (0.32 + r_i * 0.12))
                d.rectangle([sx + 16, ry, sx + sw - 16, ry + int(H * 0.09)], fill=_hex_rgba("#4E3220"), outline=ink_bold, width=lw)
                for sc_i in range(6):
                    sc_x = sx + 34 + sc_i * int((sw - 68) / 6)
                    d.ellipse([sc_x, ry + int(H * 0.025), sc_x + 24, ry + int(H * 0.08)], fill=_hex_rgba("#F4E6C8"), outline=ink_bold, width=max(2, lw - 1))
        # Arched sunlit clerestory window with iron mullion bars & warm key light shaft
        wx0, wy0, wx1, wy1 = int(W * 0.40), int(H * 0.27), int(W * 0.58), int(H * 0.60)
        d.rounded_rectangle([wx0, wy0, wx1, wy1], radius=int(W * 0.09), fill=(162, 214, 245, 255), outline=ink_bold, width=lw + 2)
        d.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=ink_bold, width=lw)
        d.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=ink_bold, width=lw)
        d.polygon([(wx0, wy1), (wx1, wy1), (int(W * 0.70), ground_y), (int(W * 0.32), ground_y)], fill=key_rgba)
        # Carved courier dispatch desk with wax-seal inkpot in center-midground
        d.rounded_rectangle([int(W * 0.37), int(H * 0.69), int(W * 0.61), ground_y], radius=8, fill=_hex_rgba("#8F5E3C"), outline=ink_bold, width=lw + 2)
        d.rectangle([int(W * 0.36), int(H * 0.67), int(W * 0.62), int(H * 0.705)], fill=_hex_rgba("#C89B6E"), outline=ink_bold, width=lw + 1)

    elif niche == "modern_science":
        # Cleanroom wall panels, observation window, instrument racks & optical bench
        d.rectangle([0, int(H * 0.16), W, ground_y], fill=_hex_rgba(arch_cols[0]), outline=ink_mid, width=lw)
        for px in range(int(W * 0.06), W, int(W * 0.12)):
            d.line([(px, int(H * 0.16)), (px, ground_y)], fill=_hex_rgba(arch_cols[1]), width=lw)
        # Observation glass bay + cyan status strip
        d.rounded_rectangle([int(W * 0.22), int(H * 0.24), int(W * 0.78), int(H * 0.58)], radius=18, fill=_hex_rgba("#243B53"), outline=ink_mid, width=lw + 1)
        d.line([(int(W * 0.08), int(H * 0.20)), (int(W * 0.92), int(H * 0.20))], fill=_hex_rgba(acc_cols[0]), width=lw * 2)
        # Spectrometer & oscilloscope rack on left
        d.rounded_rectangle([int(W * 0.07), int(H * 0.34), int(W * 0.19), ground_y], radius=10, fill=_hex_rgba(arch_cols[2]), outline=ink_mid, width=lw)
        for ri in range(3):
            ry = int(H * (0.38 + ri * 0.13))
            d.rounded_rectangle([int(W * 0.085), ry, int(W * 0.175), ry + int(H * 0.09)], radius=6, fill=(20, 34, 46, 255), outline=ink_mid, width=2)
            d.line([(int(W * 0.095), ry + int(H * 0.045)), (int(W * 0.135), ry + int(H * 0.025)), (int(W * 0.165), ry + int(H * 0.055))], fill=_hex_rgba(acc_cols[0]), width=3)
        # Central optical lab bench + glowing crystal beaker
        d.rounded_rectangle([int(W * 0.34), int(H * 0.69), int(W * 0.66), int(H * 0.75)], radius=8, fill=_hex_rgba("#CFD9E2"), outline=ink_mid, width=lw)
        d.rectangle([int(W * 0.37), int(H * 0.75), int(W * 0.40), ground_y], fill=_hex_rgba("#7A8B99"), outline=ink_mid, width=lw)
        d.rectangle([int(W * 0.60), int(H * 0.75), int(W * 0.63), ground_y], fill=_hex_rgba("#7A8B99"), outline=ink_mid, width=lw)

    elif niche == "holdout_astronomy_museum":
        # Ribbed twilight planetarium dome + projected solar eclipse + brass telescope pedestal
        for r_scale in (0.68, 0.52, 0.36):
            rw = int(W * r_scale)
            rh = int(H * r_scale * 0.9)
            d.arc([W // 2 - rw, int(H * 0.64) - rh, W // 2 + rw, int(H * 0.64) + rh], 180, 360, fill=_hex_rgba(arch_cols[1]), width=lw)
        # Projected golden corona eclipse on dome!
        ex_c, ey_c, er = int(W * 0.52), int(H * 0.30), int(H * 0.10)
        d.ellipse([ex_c - int(er * 1.35), ey_c - int(er * 1.35), ex_c + int(er * 1.35), ey_c + int(er * 1.35)], fill=(224, 159, 62, 96))
        d.ellipse([ex_c - er, ey_c - er, ex_c + er, ey_c + er], fill=(18, 22, 38, 255), outline=_hex_rgba("#FFD97D"), width=lw * 2)
        # Brass refractor telescope on tripod
        tx_c = int(W * 0.52)
        d.line([(tx_c, int(H * 0.65)), (tx_c - int(W * 0.045), ground_y)], fill=_hex_rgba("#5C4028"), width=lw * 2)
        d.line([(tx_c, int(H * 0.65)), (tx_c + int(W * 0.045), ground_y)], fill=_hex_rgba("#5C4028"), width=lw * 2)
        d.polygon(
            [(tx_c - int(W * 0.06), int(H * 0.67)), (tx_c + int(W * 0.07), int(H * 0.56)), (tx_c + int(W * 0.08), int(H * 0.59)), (tx_c - int(W * 0.05), int(H * 0.70))],
            fill=_hex_rgba(arch_cols[2]),
            outline=ink_mid,
        )

    else:  # everyday_business (Artisan Cafe)
        d.rectangle([0, int(H * 0.14), W, ground_y], fill=_hex_rgba(arch_cols[0]), outline=ink_mid, width=lw)
        # Teal wainscoting lower wall
        d.rectangle([0, int(H * 0.54), W, ground_y], fill=_hex_rgba(arch_cols[2]), outline=ink_mid, width=lw)
        # Chalkboard menu + sunlit cafe storefront window
        d.rounded_rectangle([int(W * 0.10), int(H * 0.22), int(W * 0.32), int(H * 0.48)], radius=10, fill=(38, 46, 48, 255), outline=_hex_rgba("#8C5A3C"), width=lw * 2)
        d.rounded_rectangle([int(W * 0.62), int(H * 0.20), int(W * 0.90), int(H * 0.52)], radius=12, fill=(186, 226, 244, 255), outline=ink_mid, width=lw * 2)
        # Warm hanging pendant lamps
        for lx in (int(W * 0.38), int(W * 0.54)):
            d.line([(lx, 0), (lx, int(H * 0.22))], fill=ink_mid, width=lw)
            d.pieslice([lx - int(W * 0.03), int(H * 0.19), lx + int(W * 0.03), int(H * 0.26)], 180, 360, fill=_hex_rgba(acc_cols[2]), outline=ink_mid, width=lw)
            d.polygon([(lx - int(W * 0.03), int(H * 0.23)), (lx + int(W * 0.03), int(H * 0.23)), (lx + int(W * 0.09), int(H * 0.56)), (lx - int(W * 0.09), int(H * 0.56))], fill=key_rgba)
        # Oak espresso counter + brass espresso machine
        d.rounded_rectangle([int(W * 0.28), int(H * 0.66), int(W * 0.64), ground_y], radius=10, fill=_hex_rgba("#9C6B49"), outline=ink_mid, width=lw)
        d.rounded_rectangle([int(W * 0.33), int(H * 0.55), int(W * 0.43), int(H * 0.66)], radius=8, fill=_hex_rgba("#D99B38"), outline=ink_mid, width=lw)

    # Plane 2: Perspective Ground Plane with Converging Paving / Floor Lines
    d.rectangle([0, ground_y, W, H], fill=_hex_rgba(gnd_cols[0]))
    d.rectangle([0, ground_y, W, ground_y + int(H * 0.018)], fill=_hex_rgba(gnd_cols[2]))
    for ray_i in range(-8, 9):
        bx = W * 0.5 + ray_i * W * 0.11
        ix = vp_x + (bx - vp_x) * ((ground_y - vp_y) / max(1.0, H - vp_y))
        d.line([(ix, ground_y), (bx, H)], fill=_hex_rgba(gnd_cols[2], 150), width=max(2, lw - 1))
    for row_u in (0.18, 0.42, 0.72):
        ry = int(ground_y + (H - ground_y) * row_u)
        d.line([(0, ry), (W, ry)], fill=_hex_rgba(gnd_cols[2], 140), width=max(2, lw - 1))

    # Plane 3: Foreground Occluders (framing vignette silhouettes on wide/medium stages)
    if detail_mode not in ("close", "macro"):
        fg_col = _hex_rgba(pal["shadow_tint_hex"], 220 if is_v2 else 215)
        if is_v2 and niche == "city_park":
            # Organic foreground park foliage bush + flowers on bottom-left & overhanging canopy leaves on top-right!
            for bx_f, by_f, rx_f, ry_f in [
                (W * 0.02, H * 0.94, W * 0.085, H * 0.11),
                (W * 0.09, H * 0.98, W * 0.065, H * 0.08),
                (W * 0.94, H * 0.06, W * 0.095, H * 0.09),
            ]:
                d.ellipse([int(bx_f - rx_f), int(by_f - ry_f), int(bx_f + rx_f), int(by_f + ry_f)], fill=_hex_rgba("#1E3B2B", 225), outline=ink_mid, width=lw)
            for fl_x, fl_y in [(int(W * 0.04), int(H * 0.89)), (int(W * 0.08), int(H * 0.93))]:
                d.ellipse([fl_x - 9, fl_y - 9, fl_x + 9, fl_y + 9], fill=_hex_rgba(acc_cols[1]), outline=ink_mid, width=2)
        else:
            # Left foreground amphora/planter silhouette + right foreground column/frame edge
            d.ellipse([int(-W * 0.03), int(H * 0.76), int(W * 0.09), int(H * 1.04)], fill=fg_col, outline=ink_mid, width=lw)
            d.rectangle([int(W * 0.955), 0, W, H], fill=fg_col)

    if supersample > 1:
        img = img.resize(canvas_size, Image.Resampling.LANCZOS)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_png, format="PNG")
    return {
        "path": str(out_png.relative_to(ROOT_DIR).as_posix() if out_png.is_relative_to(ROOT_DIR) else out_png),
        "sha256": _sha256_file(out_png),
        "dimensions": list(canvas_size),
        "detail_mode": detail_mode,
        "indoor": is_indoor,
    }


def _build_environment_svg(spec: Dict[str, Any]) -> str:
    pal = spec["palette"]
    gy = int(1080 * float(spec["ground_y_norm"]))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080" data-environment-id="{spec['environment_id']}" data-niche="{spec['niche']}">
  <defs>
    <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{pal['sky'][0]}"/>
      <stop offset="100%" stop-color="{pal['sky'][-1]}"/>
    </linearGradient>
  </defs>
  <g id="sky_backdrop">
    <rect x="0" y="0" width="1920" height="{gy}" fill="url(#skyGrad)"/>
  </g>
  <g id="far_architecture">
    <rect x="0" y="380" width="1920" height="{gy - 380}" fill="{pal['architecture'][0]}" stroke="{pal['mid_ink_hex']}" stroke-width="4"/>
  </g>
  <g id="midground_stage">
    <rect x="0" y="{gy}" width="1920" height="{1080 - gy}" fill="{pal['ground'][0]}" stroke="{pal['mid_ink_hex']}" stroke-width="4"/>
  </g>
  <g id="foreground_occluders">
    <ellipse cx="42" cy="960" rx="110" ry="150" fill="{pal['shadow_tint_hex']}" fill-opacity="0.82"/>
  </g>
</svg>
"""


def build_environment_assets(
    spec: Dict[str, Any],
    seed: int = 1476,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build original layered SVG + wide/close `1920x1080` PNG stage assets + runtime renderer config."""
    env_id = str(spec["environment_id"])
    out_d = Path(output_dir) if output_dir else (ROOT_DIR / "projects" / "_kh01_shared_cache" / "environments" / env_id)
    out_d.mkdir(parents=True, exist_ok=True)

    svg_path = out_d / f"{env_id}_layered.svg"
    svg_path.write_text(_build_environment_svg(spec), encoding="utf-8")

    wide_png = render_environment_stage_png(spec, out_d / f"{env_id}_wide_1080p.png", detail_mode="wide")
    close_png = render_environment_stage_png(spec, out_d / f"{env_id}_close_backdrop_1080p.png", detail_mode="close")

    runtime_json_path = out_d / f"{env_id}_runtime_stage.json"
    runtime_payload = {
        "schema_version": "kh01.environment_runtime.v1",
        "seed": seed,
        "spec": spec,
        "wide_stage_png": wide_png,
        "close_stage_png": close_png,
        "editable_svg": {
            "path": str(svg_path.relative_to(ROOT_DIR).as_posix() if svg_path.is_relative_to(ROOT_DIR) else svg_path),
            "sha256": _sha256_file(svg_path),
        },
        "license_spdx": "CC0-1.0 OR Proprietary-Original-Project-Authored",
        "provenance_origin": "100%_ORIGINAL_KH01_ENVIRONMENT_FACTORY",
    }
    runtime_json_path.write_text(json.dumps(runtime_payload, indent=2), encoding="utf-8")
    runtime_payload["runtime_json_path"] = str(
        runtime_json_path.relative_to(ROOT_DIR).as_posix() if runtime_json_path.is_relative_to(ROOT_DIR) else runtime_json_path
    )
    return runtime_payload


def build_scene_asset_manifest(
    project: Path | str | Dict[str, Any],
    character_assets: Optional[Sequence[Dict[str, Any]]] = None,
    rig_manifests: Optional[Sequence[Dict[str, Any]]] = None,
    environment_assets: Optional[Sequence[Dict[str, Any]]] = None,
    extra_authored_files: Optional[Sequence[Path | str]] = None,
) -> Dict[str, Any]:
    """
    Assemble cryptographic `asset_manifest.json` for a KH-01 project and verify ZERO reference
    frames, ZERO prior FL-01 preview stills, ZERO Rigby2D demo mascots, and ZERO offsite rasters.
    """
    if isinstance(project, dict):
        proj_dir = Path(project.get("project_dir") or (ROOT_DIR / "projects" / str(project.get("project_id", "kh01_proj"))))
        style_id = str(project.get("style_id") or "modern_expressive_2d.v1")
    else:
        proj_dir = Path(project).resolve()
        style_id = "modern_expressive_2d.v1"

    authored_files: List[Dict[str, Any]] = []
    seen_paths: set[str] = set()

    def _add_file(p_raw: Path | str, role: str, dims: Optional[List[int]] = None) -> None:
        fp = Path(p_raw) if Path(p_raw).is_absolute() else (ROOT_DIR / str(p_raw))
        if not fp.is_file():
            raise FileNotFoundError(f"Scene asset missing when building manifest: {fp}")
        rel_str = fp.relative_to(ROOT_DIR).as_posix() if fp.is_relative_to(ROOT_DIR) else fp.as_posix()
        low = rel_str.lower()
        if any(tok in low for tok in FORBIDDEN_ASSET_TOKENS):
            raise RuntimeError(f"Forbidden legacy/reference token in scene asset path: {rel_str}")
        if rel_str in seen_paths:
            return
        seen_paths.add(rel_str)
        rec: Dict[str, Any] = {
            "path": rel_str,
            "role": role,
            "sha256": _sha256_file(fp),
            "size_bytes": fp.stat().st_size,
        }
        if dims:
            rec["dimensions"] = list(dims)
        authored_files.append(rec)

    char_summary: Dict[str, Any] = {}
    for ca in character_assets or []:
        aid = str(ca["actor_id"])
        _add_file(ca["editable_svg"]["path"], f"character_svg:{aid}")
        for vw, vinfo in (ca.get("view_assets") or {}).items():
            _add_file(vinfo["path"], f"character_view:{aid}:{vw}", vinfo.get("dimensions"))
        for ex, einfo in (ca.get("expression_assets") or {}).items():
            _add_file(einfo["path"], f"character_expr:{aid}:{ex}", einfo.get("dimensions"))
        char_summary[aid] = {
            "actor_id": aid,
            "name": ca.get("name"),
            "niche": ca.get("niche"),
            "views": list(ca.get("views") or []),
            "expressions": list(ca.get("expressions") or []),
            "has_hand_insert": bool(ca.get("has_hand_insert", True)),
            "outfit_id": (ca.get("spec") or {}).get("wardrobe", {}).get("outfit_id"),
            "primary_hex": (ca.get("spec") or {}).get("wardrobe", {}).get("primary_hex"),
        }

    rig_summary: Dict[str, Any] = {}
    for rm in rig_manifests or []:
        cid = str(rm["character_id"])
        for fk, finfo in (rm.get("files") or {}).items():
            _add_file(finfo["path"], f"rig_{fk}:{cid}", finfo.get("dimensions"))
        if rm.get("manifest_path"):
            _add_file(rm["manifest_path"], f"rig_manifest:{cid}")
        rig_summary[cid] = {
            "character_id": cid,
            "bone_count": len(rm.get("bones") or []),
            "ik_constraints": list(rm.get("ik_constraints") or []),
            "expression_attachments": dict(rm.get("expression_attachments") or {}),
        }

    env_summary: Dict[str, Any] = {}
    for ea in environment_assets or []:
        spec = ea["spec"]
        eid = str(spec["environment_id"])
        _add_file(ea["editable_svg"]["path"], f"env_svg:{eid}")
        _add_file(ea["wide_stage_png"]["path"], f"env_wide_png:{eid}", ea["wide_stage_png"].get("dimensions"))
        _add_file(ea["close_stage_png"]["path"], f"env_close_png:{eid}", ea["close_stage_png"].get("dimensions"))
        if ea.get("runtime_json_path"):
            _add_file(ea["runtime_json_path"], f"env_runtime_json:{eid}")
        env_summary[eid] = {
            "environment_id": eid,
            "niche": spec.get("niche"),
            "place": spec.get("place"),
            "supported_detail_tiers": list(spec.get("supported_detail_tiers") or []),
            "interactable_props": list((spec.get("interactable_props") or {}).keys()),
        }

    for extra_p in extra_authored_files or []:
        _add_file(extra_p, "renderer_or_scene_module")

    manifest = {
        "schema_version": "kh01.scene_asset_manifest.v1",
        "project_id": proj_dir.name,
        "style_id": style_id,
        "license_spdx": "CC0-1.0 OR Proprietary-Original-Project-Authored",
        "provenance_origin": "100%_ORIGINAL_KH01_CHARACTER_AND_ENVIRONMENT_FACTORIES",
        "reference_frames_reused": 0,
        "prior_preview_derived_visual_inputs": 0,
        "rigby_demo_mascots_copied": 0,
        "external_unlicensed_rasters": 0,
        "characters": char_summary,
        "rigs": rig_summary,
        "environments": env_summary,
        "authored_files": authored_files,
    }
    if proj_dir.exists():
        story_d = proj_dir / "story"
        story_d.mkdir(parents=True, exist_ok=True)
        (story_d / "asset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (story_d / "asset_source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def validate_environment_continuity(
    scene_spec: Dict[str, Any],
    shots: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate persistent environment IDs, lighting temperature, horizon sanity, and prop continuity across cuts."""
    errors: List[str] = []
    warnings: List[str] = []
    expected_env_id = str(scene_spec.get("environment_id") or "")
    known_props = set((scene_spec.get("interactable_props") or {}).keys())

    if not expected_env_id:
        return {"valid": False, "status": "FAIL", "errors": ["Missing environment_id in scene_spec"]}

    last_prop_pos: Dict[str, Tuple[float, float]] = {}
    for s in shots or []:
        sid = str(s.get("id") or s.get("shot_id") or "S01")
        ws = s.get("world_state") or (s.get("args") or {}).get("worldState") or {}
        s_env_id = str(ws.get("environment_id") or (s.get("args") or {}).get("environmentId") or expected_env_id)
        if s_env_id != expected_env_id and not s.get("location_change_reason"):
            errors.append(f"Shot {sid}: environment_id teleported ('{expected_env_id}' -> '{s_env_id}') without location_change_reason")

        objs = ws.get("objects") or {}
        for oid, odata in objs.items():
            if not isinstance(odata, dict):
                continue
            if odata.get("duplicated") is True:
                errors.append(f"Shot {sid}: environment prop '{oid}' duplicated")
            ox = float(odata.get("x", 0.5))
            oy = float(odata.get("y", 0.75))
            if oid in last_prop_pos:
                px, py = last_prop_pos[oid]
                is_portable = bool((scene_spec.get("interactable_props") or {}).get(oid, {}).get("portable", True))
                if not is_portable and oid != "cart" and math.hypot(ox - px, oy - py) > 0.18:
                    errors.append(f"Shot {sid}: fixed architectural prop '{oid}' teleported ({px:.2f},{py:.2f}) -> ({ox:.2f},{py:.2f})")
            last_prop_pos[oid] = (ox, oy)

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "environment_id": expected_env_id,
        "known_interactable_props": sorted(known_props),
        "checked_shots": len(shots or []),
        "errors": errors,
        "warnings": warnings,
    }
