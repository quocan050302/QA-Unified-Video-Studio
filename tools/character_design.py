"""tools/character_design.py — Universal Multi-Niche Expressive 2D Character Factory & Rig Exporter (KH-01.2).

Generates 100% ORIGINAL multi-layer 2D character designs, editable SVG part sheets,
high-resolution 3-view + 6-expression turnaround model sheets (`VQ02_MODEL_SHEET_CANDIDATE`),
and Spine 3.8 / Rigby2D-compatible `1024x1024` RGBA skeletal rig packages across any niche.

Zero external reference pixels, zero Rigby2D demo mascots, zero legacy white-circle soldier clones.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from tools.visual_style_director import StyleInstance, load_style_profile, resolve_visual_style

ROOT_DIR = Path(__file__).resolve().parent.parent

REQUIRED_EXPRESSIONS: Tuple[str, ...] = (
    "neutral_attentive",
    "wide_shock",
    "strained_exertion",
    "determined_focus",
    "joyful_laugh",
    "deadpan_disbelief",
)

REQUIRED_VIEWS: Tuple[str, ...] = (
    "front",
    "three_quarter",
    "profile",
    "rear_three_quarter",
)


def _hex_rgba(hex_str: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    h = str(hex_str or "#000000").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _shade_hex(hex_str: str, factor: float, cool_shift: int = 0) -> str:
    r, g, b, _ = _hex_rgba(hex_str)
    r2 = max(0, min(255, int(round(r * factor - cool_shift * 0.6))))
    g2 = max(0, min(255, int(round(g * factor - cool_shift * 0.2))))
    b2 = max(0, min(255, int(round(b * factor + cool_shift * 0.8))))
    return f"#{r2:02x}{g2:02x}{b2:02x}"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]
    )
    for fp in candidates:
        if Path(fp).is_file():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_capsule_segment(
    draw: ImageDraw.ImageDraw,
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    width: float,
    color: Tuple[int, int, int, int],
) -> None:
    """Draw a perfectly smooth round-capped capsule segment with zero corner artifacts."""
    x0, y0 = p0
    x1, y1 = p1
    rad = max(1.0, width * 0.5)
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    if dist > 1e-4:
        nx = -dy / dist * rad
        ny = dx / dist * rad
        draw.polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill=color)
    draw.ellipse([x0 - rad, y0 - rad, x0 + rad, y0 + rad], fill=color)
    draw.ellipse([x1 - rad, y1 - rad, x1 + rad, y1 + rad], fill=color)


def _draw_tapered_stroke(
    draw: ImageDraw.ImageDraw,
    pts: Sequence[Tuple[float, float]],
    color: Tuple[int, int, int, int],
    max_width: float,
    taper_ends: bool = True,
) -> None:
    """Simulate calligraphic variable-weight ink linework via smooth capsule segments."""
    if len(pts) < 2:
        return
    if not taper_ends:
        for i in range(len(pts) - 1):
            _draw_capsule_segment(draw, pts[i], pts[i + 1], max_width, color)
        return
    dense: List[Tuple[float, float]] = []
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        steps = max(4, int(math.hypot(x1 - x0, y1 - y0) / 4.0))
        for s in range(steps):
            u = s / float(steps)
            dense.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
    dense.append(pts[-1])
    n = len(dense)
    for i in range(n - 1):
        u = (i + 0.5) / max(1, n - 1)
        taper = 0.35 + 0.65 * math.sin(math.pi * u)
        w = max(1.0, max_width * taper)
        _draw_capsule_segment(draw, dense[i], dense[i + 1], w, color)


# Curated diverse human skin & hair palettes (explicitly avoiding uniform white-circle faces)
SKIN_PALETTES: List[Dict[str, str]] = [
    {"name": "warm_olive", "base": "#E3AE88", "shadow": "#BD825D", "rim": "#FCE0C5", "blush": "#DF7362"},
    {"name": "golden_tan", "base": "#D5996F", "shadow": "#A96E48", "rim": "#F6CFAF", "blush": "#CF6656"},
    {"name": "light_peach_ochre", "base": "#F0C19E", "shadow": "#C89270", "rim": "#FFF0DF", "blush": "#E67B6B"},
    {"name": "rich_amber_brown", "base": "#AE724B", "shadow": "#834F30", "rim": "#D9A17C", "blush": "#B85248"},
    {"name": "warm_ivory_rose", "base": "#F2C9B0", "shadow": "#CA9980", "rim": "#FFF3E8", "blush": "#E58078"},
]

HAIR_PALETTES: List[Dict[str, str]] = [
    {"name": "espresso_chestnut", "base": "#3B261E", "shadow": "#221410", "highlight": "#6E4A3A"},
    {"name": "copper_auburn", "base": "#7E3722", "shadow": "#522012", "highlight": "#B55B3C"},
    {"name": "ink_indigo_black", "base": "#1E222E", "shadow": "#10131B", "highlight": "#45506B"},
    {"name": "warm_walnut", "base": "#563A28", "shadow": "#362216", "highlight": "#876046"},
    {"name": "silver_charcoal", "base": "#666C78", "shadow": "#434852", "highlight": "#9BA3B2"},
]


NICHE_WARDROBE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "roman_forum": [
        {
            "outfit_id": "royal_courier_tunic_satchel",
            "garment_kind": "pleated_tunic_with_scarf_and_satchel",
            "primary_hex": "#C84B31",
            "secondary_hex": "#F3E5AB",
            "trim_hex": "#D99B26",
            "accessory_hex": "#6E4228",
            "footwear": "laced_leather_caligae",
            "hair_style": "windswept_tuft",
            "archetype": "agile_youth",
            "accessories": ["wax_scroll_satchel", "courier_bronze_brooch", "flowing_neck_scarf"],
        },
        {
            "outfit_id": "forum_vendor_stola_apron",
            "garment_kind": "layered_stola_and_striped_apron",
            "primary_hex": "#2B6E78",
            "secondary_hex": "#E6A13B",
            "trim_hex": "#F7EFE2",
            "accessory_hex": "#9E422D",
            "footwear": "strapped_market_sandals",
            "hair_style": "braided_kerchief_updo",
            "archetype": "grounded_artisan",
            "accessories": ["saffron_head_kerchief", "striped_linen_apron", "coin_pouch"],
        },
        {
            "outfit_id": "senatorial_civic_toga",
            "garment_kind": "draped_toga_praetexta",
            "primary_hex": "#EFE6D5",
            "secondary_hex": "#9B2C2C",
            "trim_hex": "#C9963B",
            "accessory_hex": "#5E3C26",
            "footwear": "patrician_red_calcei",
            "hair_style": "silver_parted_waves",
            "archetype": "intellectual_specialist",
            "accessories": ["crimson_clavus_border", "signet_ring"],
        },
    ],
    "modern_science": [
        {
            "outfit_id": "lead_scientist_labcoat_knit",
            "garment_kind": "tailored_lab_coat_over_turtleneck",
            "primary_hex": "#EAF2F8",
            "secondary_hex": "#264653",
            "trim_hex": "#00A6A6",
            "accessory_hex": "#E76F51",
            "footwear": "cleanroom_slip_ons",
            "hair_style": "sleek_bob_with_glasses",
            "archetype": "intellectual_specialist",
            "accessories": ["tortoiseshell_glasses", "magnetic_id_badge", "pocket_stylus"],
        },
        {
            "outfit_id": "research_engineer_utility_jacket",
            "garment_kind": "cleanroom_utility_jacket",
            "primary_hex": "#3D5A73",
            "secondary_hex": "#F4A261",
            "trim_hex": "#CFE0EC",
            "accessory_hex": "#2A9D8F",
            "footwear": "antistatic_sneakers",
            "hair_style": "curly_fade",
            "archetype": "agile_youth",
            "accessories": ["safety_goggles_on_forehead", "sensor_wristband"],
        },
    ],
    "everyday_business": [
        {
            "outfit_id": "barista_chore_jacket_apron",
            "garment_kind": "rolled_sleeve_chore_jacket_and_apron",
            "primary_hex": "#4A6B5D",
            "secondary_hex": "#E09F3E",
            "trim_hex": "#F4EBE1",
            "accessory_hex": "#6B4226",
            "footwear": "canvas_work_sneakers",
            "hair_style": "windswept_tuft",
            "archetype": "grounded_artisan",
            "accessories": ["canvas_bib_apron", "tucked_towel"],
        },
        {
            "outfit_id": "cafe_customer_cardigan_blouse",
            "garment_kind": "layered_cardigan_and_collar_blouse",
            "primary_hex": "#D96B43",
            "secondary_hex": "#FBF7F0",
            "trim_hex": "#2F5D62",
            "accessory_hex": "#8D5B4C",
            "footwear": "leather_loafers",
            "hair_style": "sleek_long_waves",
            "archetype": "agile_youth",
            "accessories": ["crossbody_tote_strap", "brass_hoop_earrings"],
        },
    ],
    "holdout_astronomy_museum": [
        {
            "outfit_id": "planetarium_curator_blazer",
            "garment_kind": "tailored_curator_blazer_and_scarf",
            "primary_hex": "#2C354D",
            "secondary_hex": "#E09F3E",
            "trim_hex": "#F4F0E6",
            "accessory_hex": "#4EA8DE",
            "footwear": "oxford_shoes",
            "hair_style": "braided_kerchief_updo",
            "archetype": "intellectual_specialist",
            "accessories": ["brass_astrolabe_pin", "museum_lanyard"],
        },
        {
            "outfit_id": "museum_visitor_hoodie",
            "garment_kind": "layered_hoodie_and_vest",
            "primary_hex": "#D64550",
            "secondary_hex": "#F4F0E6",
            "trim_hex": "#4EA8DE",
            "accessory_hex": "#3C3948",
            "footwear": "sport_sneakers",
            "hair_style": "curly_fade",
            "archetype": "energetic_junior",
            "accessories": ["daypack_straps", "eclipse_ticket_badge"],
        },
    ],
}


def derive_character_specs(
    script_entities: Sequence[Dict[str, Any]] | Dict[str, Any],
    niche: str,
    scene_objectives: Optional[Sequence[Any]] = None,
    style_instance: Optional[StyleInstance] = None,
) -> List[Dict[str, Any]]:
    """
    Derive canonical multi-niche `CharacterSpec` records with stable actor IDs, non-homogeneous
    proportions, diverse skin/hair palettes, mood arcs, and event-locked wardrobes.
    """
    style = style_instance or resolve_visual_style("", niche=niche)
    profile = load_style_profile(style.style_id)
    archetype_map = profile.silhouette_and_proportions["archetypes"]

    if isinstance(script_entities, dict):
        raw_map = script_entities.get("characters", script_entities)
        ent_list = [
            {"actor_id": k, **(v if isinstance(v, dict) else {"name": str(v)})}
            for k, v in raw_map.items()
        ]
    else:
        ent_list = [dict(item) for item in (script_entities or [])]

    if not ent_list:
        ent_list = [{"actor_id": "hero_actor", "name": "Hero", "role": "protagonist"}]

    cat_key = style.niche if style.niche in NICHE_WARDROBE_CATALOG else (
        "roman_forum" if "roman" in style.niche else (
            "modern_science" if "science" in style.niche else "everyday_business"
        )
    )
    catalog = NICHE_WARDROBE_CATALOG[cat_key]

    mood_arc: List[str] = []
    for obj in scene_objectives or []:
        eb = getattr(obj, "emotional_beat", None) or (obj.get("emotional_beat") if isinstance(obj, dict) else None)
        if eb:
            mood_arc.append(str(eb))
    if not mood_arc:
        mood_arc = ["neutral_attentive", "wide_shock", "determined_focus", "strained_exertion", "joyful_laugh"]

    specs: List[Dict[str, Any]] = []
    for idx, ent in enumerate(ent_list):
        aid = str(ent.get("actor_id") or ent.get("id") or f"actor_{idx+1}").strip().lower()
        name = str(ent.get("name") or aid.capitalize())
        template = catalog[idx % len(catalog)]
        arch_name = str(ent.get("archetype") or template["archetype"])
        arch = archetype_map.get(arch_name, archetype_map["agile_youth"])

        skin = SKIN_PALETTES[(idx + (1 if cat_key == "modern_science" else 0)) % len(SKIN_PALETTES)]
        hair = HAIR_PALETTES[(idx + (2 if cat_key == "everyday_business" else 0)) % len(HAIR_PALETTES)]
        if ent.get("skin_base"):
            skin = {
                "name": "custom_skin",
                "base": str(ent["skin_base"]),
                "shadow": _shade_hex(str(ent["skin_base"]), 0.78, cool_shift=8),
                "rim": _shade_hex(str(ent["skin_base"]), 1.15, cool_shift=-6),
                "blush": "#DE6E60",
            }
        if ent.get("hair_base"):
            hair = {
                "name": "custom_hair",
                "base": str(ent["hair_base"]),
                "shadow": _shade_hex(str(ent["hair_base"]), 0.66, cool_shift=6),
                "highlight": _shade_hex(str(ent["hair_base"]), 1.32, cool_shift=-4),
            }

        prim = str(ent.get("primary_hex") or template["primary_hex"])
        sec = str(ent.get("secondary_hex") or template["secondary_hex"])
        trim = str(ent.get("trim_hex") or template["trim_hex"])
        acc = str(ent.get("accessory_hex") or template["accessory_hex"])

        specs.append({
            "schema_version": "kh01.character_spec.v1",
            "actor_id": aid,
            "name": name,
            "role": str(ent.get("role") or ("protagonist" if idx == 0 else "supporting")),
            "niche": style.niche,
            "style_id": style.style_id,
            "personality": str(ent.get("personality") or ("earnest" if idx == 0 else "witty")),
            "archetype": arch_name,
            "proportions": {
                "head_to_height_ratio": float(arch["head_to_height_ratio"]),
                "shoulder_to_head_width": float(arch["shoulder_to_head_width"]),
                "torso_to_height_ratio": float(arch["torso_to_height_ratio"]),
                "leg_to_height_ratio": float(arch["leg_to_height_ratio"]),
                "cranium_shape": str(arch["cranium_shape"]),
                "height_norm": float(ent.get("height_norm") or (0.31 if arch_name != "energetic_junior" else 0.25)),
            },
            "skin_palette": skin,
            "hair_palette": hair,
            "hair_style": str(ent.get("hair_style") or template["hair_style"]),
            "has_glasses": bool(ent.get("has_glasses", "glasses" in str(template["hair_style"]))),
            "wardrobe": {
                "outfit_id": str(ent.get("outfit_id") or template["outfit_id"]),
                "garment_kind": str(ent.get("garment_kind") or template["garment_kind"]),
                "primary_hex": prim,
                "primary_shadow_hex": _shade_hex(prim, 0.74, cool_shift=10),
                "primary_rim_hex": _shade_hex(prim, 1.24, cool_shift=-8),
                "secondary_hex": sec,
                "secondary_shadow_hex": _shade_hex(sec, 0.78, cool_shift=8),
                "trim_hex": trim,
                "accessory_hex": acc,
                "footwear": str(template["footwear"]),
                "accessories": list(ent.get("accessories") or template["accessories"]),
            },
            "wardrobe_timeline": [
                {"from_shot": "S01", "outfit_id": str(ent.get("outfit_id") or template["outfit_id"]), "reason": "initial_character_establishment"}
            ],
            "supported_views": list(REQUIRED_VIEWS),
            "supported_expressions": list(REQUIRED_EXPRESSIONS),
            "has_hand_insert": True,
            "mood_arc": mood_arc,
            "ink_outer_hex": style.character_outer_ink_hex,
            "ink_inner_hex": style.character_inner_ink_hex,
        })
    return specs


def _draw_character_expression_face(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r: float,
    spec: Dict[str, Any],
    expression: str,
    view: str,
    ink_outer: Tuple[int, int, int, int],
    ink_inner: Tuple[int, int, int, int],
    lw: float,
) -> None:
    """Draw expressive editorial 2D eyes, brows, nose, cheeks, and mouth adapted to physical `view`."""
    if view == "rear_three_quarter":
        # Only cheek hint & ear visible from rear 3/4
        ear_x = cx + r * 0.42
        ear_y = cy + r * 0.08
        d.ellipse(
            [ear_x - r * 0.16, ear_y - r * 0.22, ear_x + r * 0.16, ear_y + r * 0.22],
            fill=_hex_rgba(spec["skin_palette"]["base"]),
            outline=ink_outer,
            width=max(2, int(lw * 0.85)),
        )
        return

    skin_sh = _hex_rgba(spec["skin_palette"]["shadow"])
    blush_col = _hex_rgba(spec["skin_palette"]["blush"], 125)
    hair_col = _hex_rgba(spec["hair_palette"]["base"])
    white = (252, 250, 246, 255)
    mouth_dark = (68, 24, 26, 255)
    tongue_col = (214, 92, 86, 255)

    # View-dependent feature placement (true foreshortening, NOT cropped front!)
    if view == "profile":
        eye_positions = [(cx + r * 0.34, cy - r * 0.06, 0.92)]
        nose_pts = [(cx + r * 0.72, cy - r * 0.12), (cx + r * 1.04, cy + r * 0.14), (cx + r * 0.74, cy + r * 0.22)]
        mouth_cx = cx + r * 0.56
        ear_box = [cx - r * 0.36, cy - r * 0.06, cx - r * 0.04, cy + r * 0.36]
    elif view == "three_quarter":
        eye_positions = [
            (cx - r * 0.14, cy - r * 0.05, 1.0),
            (cx + r * 0.44, cy - r * 0.06, 0.76),  # foreshortened far eye!
        ]
        nose_pts = [(cx + r * 0.18, cy - r * 0.10), (cx + r * 0.38, cy + r * 0.14), (cx + r * 0.16, cy + r * 0.20)]
        mouth_cx = cx + r * 0.14
        ear_box = [cx - r * 0.96, cy - r * 0.04, cx - r * 0.66, cy + r * 0.36]
    else:  # front
        eye_positions = [
            (cx - r * 0.34, cy - r * 0.05, 1.0),
            (cx + r * 0.34, cy - r * 0.05, 1.0),
        ]
        nose_pts = [(cx - r * 0.03, cy - r * 0.06), (cx + r * 0.08, cy + r * 0.14), (cx - r * 0.05, cy + r * 0.18)]
        mouth_cx = cx
        ear_box = [cx - r * 1.04, cy - r * 0.04, cx - r * 0.78, cy + r * 0.34]

    # Ear(s) with interior concha line
    d.ellipse(ear_box, fill=_hex_rgba(spec["skin_palette"]["base"]), outline=ink_outer, width=max(2, int(lw * 0.85)))
    ex_mid = 0.5 * (ear_box[0] + ear_box[2])
    ey_mid = 0.5 * (ear_box[1] + ear_box[3])
    d.arc([ex_mid - r * 0.07, ey_mid - r * 0.09, ex_mid + r * 0.07, ey_mid + r * 0.09], 30, 220, fill=ink_inner, width=max(1, int(lw * 0.5)))
    if view == "front":
        r_ear = [cx + r * 0.78, cy - r * 0.04, cx + r * 1.04, cy + r * 0.34]
        d.ellipse(r_ear, fill=_hex_rgba(spec["skin_palette"]["base"]), outline=ink_outer, width=max(2, int(lw * 0.85)))

    # Cheek warmth on expressive beats
    if expression in ("joyful_laugh", "strained_exertion", "neutral_attentive"):
        for ex, ey, sc in eye_positions:
            d.ellipse(
                [ex - r * 0.18 * sc, ey + r * 0.18, ex + r * 0.18 * sc, ey + r * 0.34],
                fill=blush_col,
            )

    # Eyes + pupils + upper lid ink + eyebrows
    for idx_e, (ex, ey, sc) in enumerate(eye_positions):
        ew = r * 0.21 * sc
        eh = r * (0.27 if expression == "wide_shock" else (0.19 if expression == "deadpan_disbelief" else 0.21))
        if expression == "joyful_laugh":
            # Happy upward crescent arc eye
            _draw_tapered_stroke(
                d,
                [(ex - ew, ey + r * 0.05), (ex, ey - r * 0.10), (ex + ew, ey + r * 0.04)],
                ink_outer,
                lw * 1.15,
            )
        elif expression == "strained_exertion":
            # Tightly squinted lower-lid push eye
            d.ellipse([ex - ew, ey - eh * 0.65, ex + ew, ey + eh * 0.65], fill=white, outline=ink_outer, width=max(2, int(lw * 0.8)))
            d.ellipse([ex - ew * 0.38, ey - eh * 0.35, ex + ew * 0.38, ey + eh * 0.35], fill=ink_outer)
            _draw_tapered_stroke(
                d,
                [(ex - ew * 1.1, ey + eh * 0.45), (ex, ey + eh * 0.10), (ex + ew * 1.1, ey + eh * 0.50)],
                ink_outer,
                lw * 0.95,
            )
        else:
            d.ellipse([ex - ew, ey - eh, ex + ew, ey + eh], fill=white, outline=ink_outer, width=max(2, int(lw * 0.85)))
            pr = ew * (0.34 if expression == "wide_shock" else (0.44 if expression == "deadpan_disbelief" else 0.54))
            px_off = ew * 0.16 if view in ("three_quarter", "profile") else 0.0
            py_off = eh * 0.20 if expression == "deadpan_disbelief" else 0.0
            d.ellipse([ex + px_off - pr, ey + py_off - pr, ex + px_off + pr, ey + py_off + pr], fill=ink_outer)
            # Specular catchlight
            hl_r = max(2.0, pr * 0.36)
            d.ellipse([ex + px_off - pr * 0.55, ey + py_off - pr * 0.65, ex + px_off - pr * 0.55 + hl_r * 2, ey + py_off - pr * 0.65 + hl_r * 2], fill=(255, 255, 255, 255))
            if expression == "deadpan_disbelief":
                # Heavy flat upper eyelid mask leaving crisp white lower sclera clearly visible!
                d.chord(
                    [ex - ew * 1.02, ey - eh * 1.02, ex + ew * 1.02, ey + eh * 0.72],
                    start=185,
                    end=355,
                    fill=_hex_rgba(spec["skin_palette"]["shadow"]),
                    outline=ink_outer,
                    width=max(2, int(lw * 0.8)),
                )
            else:
                # Crisp bold upper eyelash line
                _draw_tapered_stroke(
                    d,
                    [(ex - ew * 1.05, ey - eh * 0.35), (ex, ey - eh * 1.05), (ex + ew * 1.05, ey - eh * 0.30)],
                    ink_outer,
                    lw * 1.15,
                )

        # Expressive Eyebrow
        side_sign = -1 if idx_e == 0 else 1
        by = ey - eh - r * (0.16 if expression == "wide_shock" else 0.09)
        if expression == "wide_shock":
            b_pts = [(ex - ew * 1.1, by + r * 0.05), (ex, by - r * 0.11), (ex + ew * 1.1, by + r * 0.04)]
        elif expression in ("determined_focus", "strained_exertion"):
            in_drop = r * 0.09
            b_pts = [
                (ex - ew * 1.1, by - side_sign * in_drop),
                (ex, by + r * 0.02),
                (ex + ew * 1.1, by + side_sign * in_drop),
            ]
        elif expression == "deadpan_disbelief":
            lift = -r * 0.08 if idx_e == 1 else r * 0.02
            b_pts = [(ex - ew * 1.05, by + lift), (ex, by + lift * 0.9), (ex + ew * 1.05, by + lift)]
        else:
            b_pts = [(ex - ew * 1.05, by + r * 0.02), (ex, by - r * 0.04), (ex + ew * 1.05, by + r * 0.02)]
        _draw_tapered_stroke(d, b_pts, hair_col, lw * 1.35, taper_ends=True)

        # Optional glasses (crisp slender frames with subtle lens sheen)
        if spec.get("has_glasses"):
            d.rounded_rectangle(
                [ex - ew * 1.42, ey - eh * 1.30, ex + ew * 1.42, ey + eh * 1.30],
                radius=max(4, int(r * 0.10)),
                outline=_hex_rgba("#2B3544"),
                width=max(2, int(lw * 0.62)),
            )
            d.line([(ex - ew * 0.95, ey - eh * 0.95), (ex - ew * 0.45, ey - eh * 0.45)], fill=(255, 255, 255, 190), width=max(1, int(lw * 0.4)))

    # Sculpted nose + shadow wedge
    if view == "profile":
        d.polygon(nose_pts, fill=_hex_rgba(spec["skin_palette"]["base"]))
        _draw_tapered_stroke(d, nose_pts, ink_outer, lw * 0.95, taper_ends=False)
    else:
        d.polygon([nose_pts[0], nose_pts[1], (nose_pts[2][0], nose_pts[1][1] + r * 0.05)], fill=skin_sh)
        _draw_tapered_stroke(d, nose_pts, ink_inner, lw * 0.78, taper_ends=True)

    # Expressive Mouth
    my = cy + r * 0.44
    mw = r * (0.22 if view == "profile" else 0.32)
    if expression == "wide_shock":
        d.ellipse([mouth_cx - mw * 0.65, my - r * 0.14, mouth_cx + mw * 0.65, my + r * 0.22], fill=mouth_dark, outline=ink_outer, width=max(2, int(lw * 0.85)))
        d.pieslice([mouth_cx - mw * 0.45, my + r * 0.02, mouth_cx + mw * 0.45, my + r * 0.21], 0, 180, fill=tongue_col)
    elif expression == "strained_exertion":
        d.rounded_rectangle(
            [mouth_cx - mw * 0.95, my - r * 0.09, mouth_cx + mw * 0.95, my + r * 0.11],
            radius=max(3, int(r * 0.06)),
            fill=white,
            outline=ink_outer,
            width=max(2, int(lw * 0.85)),
        )
        d.line([(mouth_cx - mw * 0.88, my + r * 0.01), (mouth_cx + mw * 0.88, my + r * 0.01)], fill=ink_inner, width=max(1, int(lw * 0.55)))
        # Sweat droplet on temple
        sx_sw = cx - r * 0.58 if view != "profile" else cx + r * 0.05
        sy_sw = cy - r * 0.30
        d.polygon([(sx_sw, sy_sw - r * 0.14), (sx_sw + r * 0.08, sy_sw + r * 0.04), (sx_sw - r * 0.08, sy_sw + r * 0.04)], fill=(172, 228, 250, 235), outline=ink_inner)
    elif expression == "joyful_laugh":
        d.pieslice(
            [mouth_cx - mw * 1.05, my - r * 0.18, mouth_cx + mw * 1.05, my + r * 0.26],
            start=0,
            end=180,
            fill=mouth_dark,
            outline=ink_outer,
            width=max(2, int(lw * 0.9)),
        )
        d.rectangle([mouth_cx - mw * 0.82, my + r * 0.01, mouth_cx + mw * 0.82, my + r * 0.08], fill=white)
        d.pieslice([mouth_cx - mw * 0.55, my + r * 0.08, mouth_cx + mw * 0.55, my + r * 0.25], 0, 180, fill=tongue_col)
    elif expression == "determined_focus":
        _draw_tapered_stroke(
            d,
            [(mouth_cx - mw * 0.80, my + r * 0.03), (mouth_cx, my - r * 0.03), (mouth_cx + mw * 0.72, my + r * 0.01)],
            ink_outer,
            lw * 1.0,
        )
    elif expression == "deadpan_disbelief":
        _draw_tapered_stroke(
            d,
            [(mouth_cx - mw * 0.78, my + r * 0.02), (mouth_cx + mw * 0.78, my + r * 0.03)],
            ink_outer,
            lw * 1.0,
        )
    else:  # neutral_attentive
        _draw_tapered_stroke(
            d,
            [(mouth_cx - mw * 0.72, my - r * 0.01), (mouth_cx, my + r * 0.06), (mouth_cx + mw * 0.76, my - r * 0.03)],
            ink_outer,
            lw * 0.95,
        )


def draw_character_figure_rgba(
    spec: Dict[str, Any],
    view: str = "three_quarter",
    expression: str = "neutral_attentive",
    hand_pose: str = "relaxed",
    canvas_size: Tuple[int, int] = (720, 960),
    supersample: int = 2,
) -> Image.Image:
    """
    Render a full-body layered editorial 2D character at `supersample` resolution with:
      - Variable-weight outer & interior ink lines
      - 3-band cel shading (base + cool core shadow + warm rim light)
      - True geometric projection for `front`, `three_quarter`, `profile`, and `rear_three_quarter`
      - Articulated hands (`relaxed`, `open_reach`, `locked_grip`, `spread_shock`, `pointing`)
    """
    W = canvas_size[0] * supersample
    H = canvas_size[1] * supersample
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")

    ink_outer = _hex_rgba(spec["ink_outer_hex"])
    ink_inner = _hex_rgba(spec["ink_inner_hex"])
    skin_base = _hex_rgba(spec["skin_palette"]["base"])
    skin_sh = _hex_rgba(spec["skin_palette"]["shadow"])
    skin_rim = _hex_rgba(spec["skin_palette"]["rim"])
    hair_base = _hex_rgba(spec["hair_palette"]["base"])
    hair_sh = _hex_rgba(spec["hair_palette"]["shadow"])
    hair_hl = _hex_rgba(spec["hair_palette"]["highlight"])

    wd = spec["wardrobe"]
    prim = _hex_rgba(wd["primary_hex"])
    prim_sh = _hex_rgba(wd["primary_shadow_hex"])
    prim_rim = _hex_rgba(wd["primary_rim_hex"])
    sec = _hex_rgba(wd["secondary_hex"])
    sec_sh = _hex_rgba(wd["secondary_shadow_hex"])
    trim = _hex_rgba(wd["trim_hex"])
    acc = _hex_rgba(wd["accessory_hex"])

    char_h = H * 0.78
    foot_y = H * 0.90
    cx = W * 0.50
    lw_outer = max(4.0, char_h * 0.0125)
    lw_inner = lw_outer * 0.48

    props = spec["proportions"]
    head_r = char_h * float(props["head_to_height_ratio"]) * 0.52
    sh_half = head_r * float(props["shoulder_to_head_width"]) * (
        0.58 if view == "profile" else (0.86 if view == "three_quarter" else 1.0)
    )
    hip_half = sh_half * (0.76 if view == "profile" else 0.78)
    head_cy = foot_y - char_h + head_r * 1.12
    neck_y = head_cy + head_r * 0.92
    torso_top = neck_y + head_r * 0.18
    pelvis_y = torso_top + char_h * float(props["torso_to_height_ratio"])

    # Ground contact shadow
    d.ellipse(
        [cx - sh_half * 1.15, foot_y - head_r * 0.22, cx + sh_half * 1.15, foot_y + head_r * 0.24],
        fill=(24, 18, 16, 86),
    )

    # Back flowing scarf / hair / coat tail layer
    if "scarf" in " ".join(wd["accessories"]) or "tunic" in wd["garment_kind"]:
        scarf_dir = -1 if view in ("three_quarter", "profile") else 1
        s_pts = [
            (cx - scarf_dir * sh_half * 0.2, torso_top + head_r * 0.1),
            (cx + scarf_dir * sh_half * 1.45, torso_top + head_r * 0.55),
            (cx + scarf_dir * sh_half * 1.25, torso_top + head_r * 1.35),
            (cx - scarf_dir * sh_half * 0.1, torso_top + head_r * 0.75),
        ]
        d.polygon(s_pts, fill=sec, outline=ink_outer)
        _draw_tapered_stroke(d, s_pts + [s_pts[0]], ink_outer, lw_outer * 0.85, taper_ends=False)

    # Hair back layer for long/updo styles
    h_style = spec["hair_style"]
    if h_style in ("braided_kerchief_updo", "sleek_long_waves", "sleek_bob_with_glasses"):
        d.ellipse(
            [cx - head_r * 1.16, head_cy - head_r * 1.08, cx + head_r * 1.12, head_cy + head_r * 1.05],
            fill=hair_sh,
            outline=ink_outer,
            width=int(lw_outer),
        )

    # Legs + cel-shaded calves + period/niche footwear
    leg_offsets = [0.0] if view == "profile" else [-hip_half * 0.52, hip_half * 0.52]
    if view == "profile":
        leg_offsets = [-head_r * 0.14, head_r * 0.18]
    for li, lx_off in enumerate(leg_offsets):
        is_far = (li == 1 and view in ("three_quarter", "profile"))
        leg_skin = skin_sh if is_far else skin_base
        lx = cx + lx_off
        knee_y = 0.5 * (pelvis_y + foot_y)
        leg_w = head_r * 0.34
        # Trouser vs bare calf by niche
        is_trousers = spec["niche"] in ("modern_science", "everyday_business", "holdout_astronomy_museum")
        upper_col = (sec_sh if is_far else sec) if is_trousers else leg_skin
        d.polygon(
            [
                (lx - leg_w, pelvis_y - head_r * 0.1),
                (lx + leg_w, pelvis_y - head_r * 0.1),
                (lx + leg_w * 0.82, foot_y - head_r * 0.22),
                (lx - leg_w * 0.82, foot_y - head_r * 0.22),
            ],
            fill=upper_col,
            outline=ink_outer,
        )
        _draw_tapered_stroke(
            d,
            [(lx - leg_w, pelvis_y), (lx - leg_w * 0.82, foot_y - head_r * 0.22)],
            ink_outer,
            lw_outer * 0.9,
            taper_ends=False,
        )
        _draw_tapered_stroke(
            d,
            [(lx + leg_w, pelvis_y), (lx + leg_w * 0.82, foot_y - head_r * 0.22)],
            ink_outer,
            lw_outer * 0.9,
            taper_ends=False,
        )
        # Footwear silhouette (toe projects in facing direction!)
        toe_dir = 1 if view in ("three_quarter", "profile") else (-1 if li == 0 else 1)
        shoe_pts = [
            (lx - leg_w * 0.85, foot_y - head_r * 0.26),
            (lx + leg_w * 0.85, foot_y - head_r * 0.26),
            (lx + toe_dir * leg_w * 1.65, foot_y),
            (lx - toe_dir * leg_w * 0.90, foot_y),
        ]
        d.polygon(shoe_pts, fill=acc, outline=ink_outer)
        _draw_tapered_stroke(d, shoe_pts + [shoe_pts[0]], ink_outer, lw_outer * 0.88, taper_ends=False)
        if "caligae" in wd["footwear"] or "sandals" in wd["footwear"]:
            for st_i in range(3):
                sy = foot_y - head_r * (0.34 + st_i * 0.14)
                d.line([(lx - leg_w * 0.82, sy), (lx + leg_w * 0.82, sy + head_r * 0.06)], fill=acc, width=max(2, int(lw_inner)))

    # Far arm (drawn behind torso in 3/4 and profile views)
    def _draw_arm(side_idx: int, behind: bool) -> None:
        sx = cx + (-sh_half * 0.92 if side_idx == 0 else sh_half * 0.92)
        if view == "profile":
            sx = cx + (-head_r * 0.12 if behind else head_r * 0.08)
        sy = torso_top + head_r * 0.28
        dir_x = -1 if side_idx == 0 else 1
        if hand_pose in ("open_reach", "locked_grip", "pointing") and not behind:
            ex_a = sx + dir_x * head_r * 0.72
            ey_a = sy + head_r * 0.45
            hx = ex_a + dir_x * head_r * 0.78
            hy = ey_a - head_r * 0.28
        elif hand_pose == "spread_shock":
            ex_a = sx + dir_x * head_r * 0.65
            ey_a = sy + head_r * 0.20
            hx = ex_a + dir_x * head_r * 0.35
            hy = ey_a - head_r * 0.68
        else:
            ex_a = sx + dir_x * head_r * 0.34
            ey_a = sy + head_r * 0.88
            hx = ex_a + dir_x * head_r * 0.18
            hy = ey_a + head_r * 0.78

        sleeve_col = prim_sh if behind else prim
        arm_skin = skin_sh if behind else skin_base
        # Upper sleeve + forearm
        _draw_tapered_stroke(d, [(sx, sy), (ex_a, ey_a)], ink_outer, head_r * 0.56, taper_ends=False)
        _draw_tapered_stroke(d, [(sx, sy), (ex_a, ey_a)], sleeve_col, head_r * 0.44, taper_ends=False)
        _draw_tapered_stroke(d, [(ex_a, ey_a), (hx, hy)], ink_outer, head_r * 0.44, taper_ends=False)
        _draw_tapered_stroke(d, [(ex_a, ey_a), (hx, hy)], arm_skin, head_r * 0.32, taper_ends=False)
        # Expressive hand + articulated fingers
        hr = head_r * 0.24
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=arm_skin, outline=ink_outer, width=max(2, int(lw_outer * 0.8)))
        if hand_pose == "locked_grip" and not behind:
            # Knuckle cluster wrapped tightly
            for fi in range(4):
                fy = hy - hr * 0.55 + fi * hr * 0.36
                kx0 = min(hx - dir_x * hr * 0.35, hx + dir_x * hr * 0.85)
                kx1 = max(hx - dir_x * hr * 0.35, hx + dir_x * hr * 0.85)
                d.rounded_rectangle(
                    [kx0, fy - hr * 0.16, kx1, fy + hr * 0.16],
                    radius=max(2, int(hr * 0.15)),
                    fill=arm_skin,
                    outline=ink_outer,
                    width=max(2, int(lw_inner)),
                )
        elif hand_pose in ("open_reach", "spread_shock", "pointing") and not behind:
            f_count = 1 if hand_pose == "pointing" else 4
            for fi in range(f_count):
                ang = -0.55 + fi * 0.34
                fx1 = hx + dir_x * math.cos(ang) * hr * 1.65
                fy1 = hy + math.sin(ang) * hr * 1.65
                _draw_tapered_stroke(d, [(hx, hy), (fx1, fy1)], ink_outer, hr * 0.52, taper_ends=True)
                _draw_tapered_stroke(d, [(hx, hy), (fx1, fy1)], arm_skin, hr * 0.34, taper_ends=True)

    if view in ("three_quarter", "profile"):
        _draw_arm(1, behind=True)

    # Layered Torso Garment + 3-Band Cel Shading (Base + Core Shadow + Rim Highlight)
    skirt_drop = head_r * (0.95 if "tunic" in wd["garment_kind"] or "stola" in wd["garment_kind"] or "coat" in wd["garment_kind"] else 0.25)
    torso_pts = [
        (cx - sh_half, torso_top),
        (cx + sh_half, torso_top),
        (cx + hip_half * 1.18, pelvis_y + skirt_drop),
        (cx - hip_half * 1.18, pelvis_y + skirt_drop),
    ]
    d.polygon(torso_pts, fill=prim)
    # Core cel-shadow band along right/away side of torso
    shadow_poly = [
        (cx + sh_half * 0.22, torso_top),
        (cx + sh_half, torso_top),
        (cx + hip_half * 1.18, pelvis_y + skirt_drop),
        (cx + hip_half * 0.18, pelvis_y + skirt_drop),
    ]
    d.polygon(shadow_poly, fill=prim_sh)
    # Warm key-light rim highlight strip along key-lit shoulder/chest
    rim_poly = [
        (cx - sh_half + lw_outer * 0.5, torso_top + lw_outer * 0.5),
        (cx - sh_half * 0.72, torso_top + lw_outer * 0.5),
        (cx - hip_half * 0.88, pelvis_y + skirt_drop - lw_outer),
        (cx - hip_half * 1.12, pelvis_y + skirt_drop - lw_outer),
    ]
    d.polygon(rim_poly, fill=prim_rim)

    # Secondary garment layer (apron / open lab coat lapels / draped sash / collar)
    gk = wd["garment_kind"]
    if "apron" in gk:
        ap_pts = [
            (cx - hip_half * 0.78, pelvis_y - head_r * 0.35),
            (cx + hip_half * 0.78, pelvis_y - head_r * 0.35),
            (cx + hip_half * 0.92, pelvis_y + skirt_drop - head_r * 0.08),
            (cx - hip_half * 0.92, pelvis_y + skirt_drop - head_r * 0.08),
        ]
        d.polygon(ap_pts, fill=trim, outline=ink_outer)
        for st_x in (-0.42, 0.0, 0.42):
            sx0 = cx + hip_half * st_x
            d.line([(sx0, pelvis_y - head_r * 0.32), (sx0, pelvis_y + skirt_drop - head_r * 0.10)], fill=sec, width=max(3, int(lw_inner * 1.4)))
    elif "coat" in gk or "blazer" in gk or "cardigan" in gk:
        # Center shirt/knit panel + tailored lapels
        d.polygon(
            [
                (cx - sh_half * 0.32, torso_top),
                (cx + sh_half * 0.32, torso_top),
                (cx + hip_half * 0.28, pelvis_y + head_r * 0.15),
                (cx - hip_half * 0.28, pelvis_y + head_r * 0.15),
            ],
            fill=sec,
            outline=ink_inner,
        )
        _draw_tapered_stroke(d, [(cx - sh_half * 0.32, torso_top), (cx - sh_half * 0.12, pelvis_y)], ink_outer, lw_inner * 1.3)
        _draw_tapered_stroke(d, [(cx + sh_half * 0.32, torso_top), (cx + sh_half * 0.12, pelvis_y)], ink_outer, lw_inner * 1.3)
    else:
        # Cross-body courier satchel strap + waist belt + hem border
        d.line([(cx - sh_half * 0.72, torso_top + head_r * 0.06), (cx + hip_half * 0.75, pelvis_y + head_r * 0.22)], fill=acc, width=max(4, int(lw_outer * 1.3)))
        d.rounded_rectangle(
            [cx - hip_half * 1.04, pelvis_y - head_r * 0.16, cx + hip_half * 1.04, pelvis_y + head_r * 0.06],
            radius=max(3, int(head_r * 0.06)),
            fill=acc,
            outline=ink_outer,
            width=max(2, int(lw_inner)),
        )
        d.ellipse([cx - head_r * 0.16, pelvis_y - head_r * 0.17, cx + head_r * 0.16, pelvis_y + head_r * 0.07], fill=trim, outline=ink_outer, width=max(2, int(lw_inner)))

    # Garment hem trim + interior cloth fold lines
    d.line(
        [(cx - hip_half * 1.12, pelvis_y + skirt_drop - head_r * 0.12), (cx + hip_half * 1.12, pelvis_y + skirt_drop - head_r * 0.12)],
        fill=trim,
        width=max(3, int(lw_outer * 0.9)),
    )
    for fold_x in (-0.38, 0.18):
        _draw_tapered_stroke(
            d,
            [(cx + sh_half * fold_x, torso_top + head_r * 0.55), (cx + hip_half * (fold_x * 1.15), pelvis_y + skirt_drop - head_r * 0.20)],
            ink_inner,
            lw_inner,
        )
    # Bold outer contour of torso
    _draw_tapered_stroke(d, torso_pts + [torso_pts[0]], ink_outer, lw_outer, taper_ends=False)

    # Near arm(s) in front of torso
    _draw_arm(0, behind=False)
    if view in ("front", "rear_three_quarter"):
        _draw_arm(1, behind=False)

    # Neck cylinder with cast chin shadow
    nw = head_r * 0.32
    d.rounded_rectangle([cx - nw, neck_y - head_r * 0.25, cx + nw, torso_top + head_r * 0.18], radius=int(nw * 0.5), fill=skin_sh, outline=ink_outer, width=int(lw_outer * 0.85))

    # Cranium + Jaw (view-accurate silhouette, cel shadow & rim highlight)
    if view == "profile":
        head_poly = [
            (cx - head_r * 0.88, head_cy - head_r * 0.52),
            (cx - head_r * 0.35, head_cy - head_r * 1.02),
            (cx + head_r * 0.58, head_cy - head_r * 0.92),
            (cx + head_r * 0.82, head_cy - head_r * 0.20),
            (cx + head_r * 0.78, head_cy + head_r * 0.58),
            (cx + head_r * 0.32, head_cy + head_r * 0.96),
            (cx - head_r * 0.54, head_cy + head_r * 0.78),
            (cx - head_r * 0.92, head_cy + head_r * 0.12),
        ]
        d.polygon(head_poly, fill=skin_base)
        _draw_tapered_stroke(d, head_poly + [head_poly[0]], ink_outer, lw_outer, taper_ends=False)
    elif view == "three_quarter":
        # Expressive 3/4 ogee cheek curve
        d.ellipse([cx - head_r * 0.94, head_cy - head_r * 0.98, cx + head_r * 0.92, head_cy + head_r * 0.98], fill=skin_base)
        d.pieslice([cx - head_r * 0.94, head_cy - head_r * 0.98, cx + head_r * 0.92, head_cy + head_r * 0.98], -55, 85, fill=skin_sh)
        d.arc([cx - head_r * 0.90, head_cy - head_r * 0.94, cx + head_r * 0.88, head_cy + head_r * 0.94], 135, 250, fill=skin_rim, width=max(3, int(lw_outer * 0.9)))
        d.ellipse([cx - head_r * 0.94, head_cy - head_r * 0.98, cx + head_r * 0.92, head_cy + head_r * 0.98], outline=ink_outer, width=int(lw_outer))
    else:
        d.ellipse([cx - head_r * 0.96, head_cy - head_r * 0.98, cx + head_r * 0.96, head_cy + head_r * 0.98], fill=skin_base)
        d.pieslice([cx - head_r * 0.96, head_cy - head_r * 0.98, cx + head_r * 0.96, head_cy + head_r * 0.98], -45, 75, fill=skin_sh)
        d.ellipse([cx - head_r * 0.96, head_cy - head_r * 0.98, cx + head_r * 0.96, head_cy + head_r * 0.98], outline=ink_outer, width=int(lw_outer))

    # Facial features (eyes/brows/nose/mouth)
    _draw_character_expression_face(d, cx, head_cy, head_r, spec, expression, view, ink_outer, ink_inner, lw_outer)

    # Crown hair & headgear / kerchief / tuft
    if view == "rear_three_quarter":
        d.pieslice([cx - head_r * 1.02, head_cy - head_r * 1.06, cx + head_r * 0.98, head_cy + head_r * 0.86], 110, 355, fill=hair_base, outline=ink_outer, width=int(lw_outer))
    else:
        hair_cap = [
            (cx - head_r * 0.98, head_cy - head_r * 0.18),
            (cx - head_r * 0.82, head_cy - head_r * 1.08),
            (cx + head_r * 0.18, head_cy - head_r * 1.24),
            (cx + head_r * 0.92, head_cy - head_r * 0.86),
            (cx + head_r * 0.98, head_cy - head_r * 0.34),
            (cx + head_r * 0.36, head_cy - head_r * 0.62),
            (cx - head_r * 0.28, head_cy - head_r * 0.54),
        ]
        d.polygon(hair_cap, fill=hair_base)
        # Hair specular ribbon
        _draw_tapered_stroke(
            d,
            [(cx - head_r * 0.52, head_cy - head_r * 0.92), (cx + head_r * 0.08, head_cy - head_r * 1.04), (cx + head_r * 0.56, head_cy - head_r * 0.78)],
            hair_hl,
            lw_outer * 1.2,
            taper_ends=True,
        )
        _draw_tapered_stroke(d, hair_cap + [hair_cap[0]], ink_outer, lw_outer * 0.92, taper_ends=False)
        if h_style == "braided_kerchief_updo":
            # Saffron/accent head kerchief band + top bun
            d.ellipse([cx - head_r * 0.45, head_cy - head_r * 1.48, cx + head_r * 0.25, head_cy - head_r * 0.96], fill=hair_base, outline=ink_outer, width=int(lw_outer * 0.9))
            d.polygon(
                [
                    (cx - head_r * 0.96, head_cy - head_r * 0.36),
                    (cx + head_r * 0.88, head_cy - head_r * 0.56),
                    (cx + head_r * 0.92, head_cy - head_r * 0.34),
                    (cx - head_r * 0.92, head_cy - head_r * 0.14),
                ],
                fill=sec,
                outline=ink_outer,
            )

    if supersample > 1:
        img = img.resize(canvas_size, Image.Resampling.LANCZOS)
    return img


def _build_editable_character_svg(spec: Dict[str, Any]) -> str:
    """Emit clean multilayer editable SVG separating `<g id='cloak_back'>`, `<g id='legs'>`, `<g id='torso'>`, `<g id='arms'>`, `<g id='head'>`, `<g id='face_controls'>`."""
    wd = spec["wardrobe"]
    sk = spec["skin_palette"]
    hr = spec["hair_palette"]
    ink = spec["ink_outer_hex"]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768" width="512" height="768" data-actor-id="{spec['actor_id']}" data-style-id="{spec['style_id']}" data-niche="{spec['niche']}">
  <defs>
    <filter id="celShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="4" dy="6" stdDeviation="0" flood-color="{wd['primary_shadow_hex']}" flood-opacity="0.45"/>
    </filter>
  </defs>
  <g id="ground_shadow">
    <ellipse cx="256" cy="706" rx="88" ry="18" fill="#191210" fill-opacity="0.30"/>
  </g>
  <g id="back_accessory_layer">
    <path d="M236 278 C312 292 356 336 344 398 C306 382 268 352 238 326 Z" fill="{wd['secondary_hex']}" stroke="{ink}" stroke-width="6" stroke-linejoin="round"/>
  </g>
  <g id="legs_and_footwear">
    <path d="M214 452 L242 452 L236 676 L210 676 Z" fill="{sk['base']}" stroke="{ink}" stroke-width="6"/>
    <path d="M270 452 L298 452 L292 676 L266 676 Z" fill="{sk['shadow']}" stroke="{ink}" stroke-width="6"/>
    <path d="M204 674 L244 674 L264 704 L198 704 Z" fill="{wd['accessory_hex']}" stroke="{ink}" stroke-width="6"/>
    <path d="M262 674 L300 674 L322 704 L256 704 Z" fill="{wd['accessory_hex']}" stroke="{ink}" stroke-width="6"/>
  </g>
  <g id="upper_arm_far">
    <path d="M312 288 Q352 346 364 416" fill="none" stroke="{ink}" stroke-width="32" stroke-linecap="round"/>
    <path d="M312 288 Q352 346 364 416" fill="none" stroke="{sk['shadow']}" stroke-width="20" stroke-linecap="round"/>
  </g>
  <g id="torso_and_clothing_masks">
    <path d="M188 274 L324 274 L344 512 L168 512 Z" fill="{wd['primary_hex']}" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/>
    <path d="M276 274 L324 274 L344 512 L272 512 Z" fill="{wd['primary_shadow_hex']}"/>
    <path d="M192 278 L212 278 L194 506 L174 506 Z" fill="{wd['primary_rim_hex']}"/>
    <rect x="176" y="424" width="160" height="22" rx="6" fill="{wd['accessory_hex']}" stroke="{ink}" stroke-width="5"/>
    <line x1="172" y1="494" x2="340" y2="494" stroke="{wd['trim_hex']}" stroke-width="8"/>
  </g>
  <g id="upper_and_forearm_near">
    <path d="M196 290 Q164 356 184 432" fill="none" stroke="{ink}" stroke-width="34" stroke-linecap="round"/>
    <path d="M196 290 Q164 356 184 432" fill="none" stroke="{sk['base']}" stroke-width="22" stroke-linecap="round"/>
    <circle cx="188" cy="442" r="18" fill="{sk['base']}" stroke="{ink}" stroke-width="6"/>
  </g>
  <g id="head_and_hair">
    <rect x="238" y="236" width="36" height="46" rx="12" fill="{sk['shadow']}" stroke="{ink}" stroke-width="6"/>
    <circle cx="256" cy="176" r="74" fill="{sk['base']}" stroke="{ink}" stroke-width="7"/>
    <path d="M182 164 C194 94 282 78 330 128 C302 118 242 124 182 164 Z" fill="{hr['base']}" stroke="{ink}" stroke-width="7" stroke-linejoin="round"/>
  </g>
  <g id="face_expression_controls">
    <ellipse cx="236" cy="172" rx="14" ry="18" fill="#FCFAF6" stroke="{ink}" stroke-width="5"/>
    <ellipse cx="288" cy="172" rx="11" ry="17" fill="#FCFAF6" stroke="{ink}" stroke-width="5"/>
    <circle cx="239" cy="172" r="7" fill="{ink}"/>
    <circle cx="290" cy="172" r="6" fill="{ink}"/>
    <path d="M220 146 Q236 136 252 146" fill="none" stroke="{hr['base']}" stroke-width="7" stroke-linecap="round"/>
    <path d="M274 146 Q288 136 302 146" fill="none" stroke="{hr['base']}" stroke-width="7" stroke-linecap="round"/>
    <path d="M242 214 Q262 226 282 212" fill="none" stroke="{ink}" stroke-width="6" stroke-linecap="round"/>
  </g>
</svg>
"""


def generate_character_design(
    spec: Dict[str, Any],
    style_instance: Optional[StyleInstance] = None,
    seed: int = 1476,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Generate original multilayer editable SVG + per-view and per-expression RGBA plates
    for `spec`, recording cryptographic SHA-256 provenance.
    """
    style = style_instance or resolve_visual_style("", niche=spec.get("niche", "roman_forum"))
    aid = str(spec["actor_id"])
    out_d = Path(output_dir) if output_dir else (ROOT_DIR / "projects" / "_kh01_shared_cache" / "characters" / aid)
    out_d.mkdir(parents=True, exist_ok=True)

    svg_path = out_d / f"{aid}_layered_master.svg"
    svg_path.write_text(_build_editable_character_svg(spec), encoding="utf-8")

    view_files: Dict[str, Dict[str, Any]] = {}
    for vw in REQUIRED_VIEWS:
        im_v = draw_character_figure_rgba(spec, view=vw, expression="neutral_attentive", hand_pose="relaxed", canvas_size=(480, 640), supersample=2)
        vp = out_d / f"{aid}_view_{vw}.png"
        im_v.save(vp, format="PNG")
        view_files[vw] = {
            "path": str(vp.relative_to(ROOT_DIR).as_posix() if vp.is_relative_to(ROOT_DIR) else vp),
            "sha256": _sha256_file(vp),
            "dimensions": [im_v.width, im_v.height],
        }

    expression_files: Dict[str, Dict[str, Any]] = {}
    hand_for_expr = {
        "neutral_attentive": "relaxed",
        "wide_shock": "spread_shock",
        "strained_exertion": "locked_grip",
        "determined_focus": "open_reach",
        "joyful_laugh": "relaxed",
        "deadpan_disbelief": "relaxed",
    }
    for expr in REQUIRED_EXPRESSIONS:
        im_e = draw_character_figure_rgba(
            spec,
            view="three_quarter",
            expression=expr,
            hand_pose=hand_for_expr[expr],
            canvas_size=(420, 560),
            supersample=2,
        )
        ep = out_d / f"{aid}_expr_{expr}.png"
        im_e.save(ep, format="PNG")
        expression_files[expr] = {
            "path": str(ep.relative_to(ROOT_DIR).as_posix() if ep.is_relative_to(ROOT_DIR) else ep),
            "sha256": _sha256_file(ep),
            "dimensions": [im_e.width, im_e.height],
            "hand_pose": hand_for_expr[expr],
        }

    return {
        "schema_version": "kh01.character_asset.v1",
        "actor_id": aid,
        "name": spec["name"],
        "niche": spec["niche"],
        "style_id": style.style_id,
        "seed": seed,
        "spec": spec,
        "output_dir": str(out_d),
        "editable_svg": {
            "path": str(svg_path.relative_to(ROOT_DIR).as_posix() if svg_path.is_relative_to(ROOT_DIR) else svg_path),
            "sha256": _sha256_file(svg_path),
            "layers": [
                "ground_shadow",
                "back_accessory_layer",
                "legs_and_footwear",
                "upper_arm_far",
                "torso_and_clothing_masks",
                "upper_and_forearm_near",
                "head_and_hair",
                "face_expression_controls",
            ],
        },
        "view_assets": view_files,
        "expression_assets": expression_files,
        "views": list(REQUIRED_VIEWS),
        "expressions": list(REQUIRED_EXPRESSIONS),
        "has_hand_insert": True,
        "license_spdx": "CC0-1.0 OR Proprietary-Original-Project-Authored",
        "provenance_origin": "100%_ORIGINAL_KH01_LAYERED_VECTOR_CHARACTER_FACTORY",
    }


def build_character_model_sheet(
    character_asset: Dict[str, Any],
    out_png_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Compose a high-resolution `2400x1600` (`VQ02_MODEL_SHEET_CANDIDATE`) Character Model Sheet PNG:
      - Top tier: Front, 3/4 Turn, and True Profile full-body turnarounds on orthographic alignment guides + color swatches
      - Bottom tier: 6 genuinely distinct expression & hand-acting close-ups (zero duplicate crops!)
    """
    spec = character_asset["spec"]
    aid = character_asset["actor_id"]
    out_d = Path(character_asset["output_dir"])
    sheet_path = Path(out_png_path) if out_png_path else (out_d / f"VQ02_MODEL_SHEET_CANDIDATE_{aid}.png")
    sheet_path.parent.mkdir(parents=True, exist_ok=True)

    W, H = 2400, 1600
    sheet = Image.new("RGB", (W, H), (245, 240, 230))
    dr = ImageDraw.Draw(sheet)

    f_title = _load_font(38, bold=True)
    f_sub = _load_font(22, bold=False)
    f_lbl = _load_font(20, bold=True)

    # Header bar
    dr.rectangle([0, 0, W, 96], fill=(28, 22, 20))
    dr.text(
        (36, 18),
        f"VQ02_MODEL_SHEET_CANDIDATE — {spec['name'].upper()} ({aid}) • NICHE: {spec['niche'].upper()}",
        fill=(252, 238, 206),
        font=f_title,
    )
    dr.text(
        (36, 62),
        f"Style Lock: {spec['style_id']} | Archetype: {spec['archetype']} (head/height={spec['proportions']['head_to_height_ratio']}) | Original Authored Turnaround + 6 Expressions | EDITORIAL_REVIEW_PENDING",
        fill=(206, 198, 186),
        font=f_sub,
    )

    # Orthographic construction guide lines across turnaround box
    turn_box = [36, 118, 1740, 860]
    dr.rounded_rectangle(turn_box, radius=16, fill=(252, 249, 242), outline=(196, 184, 166), width=3)
    for guide_y, g_lbl in [(215, "CRANIUM TOP"), (335, "SHOULDER LINE"), (520, "PELVIS / BELT"), (790, "GROUND ANCHOR")]:
        dr.line([(56, guide_y), (1720, guide_y)], fill=(224, 214, 198), width=2)
        dr.text((62, guide_y - 22), g_lbl, fill=(154, 142, 126), font=f_sub)

    for v_idx, vw in enumerate(("front", "three_quarter", "profile")):
        vp = ROOT_DIR / character_asset["view_assets"][vw]["path"]
        with Image.open(vp) as im_v:
            rgba_v = im_v.convert("RGBA")
        target_h = 680
        target_w = int(round(rgba_v.width * (target_h / rgba_v.height)))
        resized = rgba_v.resize((target_w, target_h), Image.Resampling.LANCZOS)
        x_slot = 110 + v_idx * 540
        y_slot = 135
        sheet.paste(resized, (x_slot, y_slot), resized)
        dr.text((x_slot + target_w // 2 - 70, 822), f"VIEW: {vw.upper()}", fill=(36, 28, 24), font=f_lbl)

    # Color & Wardrobe Specification Panel (top right)
    spec_box = [1772, 118, 2364, 860]
    dr.rounded_rectangle(spec_box, radius=16, fill=(252, 249, 242), outline=(196, 184, 166), width=3)
    dr.text((1802, 142), "PALETTE & WARDROBE LOCK", fill=(32, 24, 22), font=f_lbl)
    wd = spec["wardrobe"]
    swatches = [
        ("Primary Garment", wd["primary_hex"]),
        ("Garment Core Shadow", wd["primary_shadow_hex"]),
        ("Secondary Layer", wd["secondary_hex"]),
        ("Trim / Accent", wd["trim_hex"]),
        ("Leather / Prop", wd["accessory_hex"]),
        ("Skin Base", spec["skin_palette"]["base"]),
        ("Skin Shadow", spec["skin_palette"]["shadow"]),
        ("Hair Base", spec["hair_palette"]["base"]),
    ]
    for s_i, (s_name, s_hex) in enumerate(swatches):
        sy = 192 + s_i * 64
        dr.rounded_rectangle([1802, sy, 1868, sy + 46], radius=8, fill=_hex_rgba(s_hex)[:3], outline=(28, 20, 18), width=2)
        dr.text((1886, sy + 10), f"{s_name}: {s_hex.upper()}", fill=(46, 38, 34), font=f_sub)
    dr.text((1802, 724), f"Outfit ID: {wd['outfit_id']}", fill=(58, 48, 42), font=f_sub)
    dr.text((1802, 756), f"Footwear: {wd['footwear']}", fill=(58, 48, 42), font=f_sub)
    dr.text((1802, 788), f"Hair: {spec['hair_style']}", fill=(58, 48, 42), font=f_sub)

    # Bottom tier: 6 Distinct Expressions + Hand Poses
    expr_hashes: List[str] = []
    card_w = 372
    card_h = 660
    for e_idx, expr in enumerate(REQUIRED_EXPRESSIONS):
        ex_x = 36 + e_idx * (card_w + 19)
        ex_y = 892
        dr.rounded_rectangle([ex_x, ex_y, ex_x + card_w, ex_y + card_h], radius=14, fill=(252, 249, 242), outline=(196, 184, 166), width=3)
        ep_info = character_asset["expression_assets"][expr]
        expr_hashes.append(ep_info["sha256"])
        ep_abs = ROOT_DIR / ep_info["path"]
        with Image.open(ep_abs) as im_e:
            # Focus upper 72% (head, shoulders, expressive arms & hands)
            crop_h = int(im_e.height * 0.76)
            bust = im_e.crop((0, 0, im_e.width, crop_h)).convert("RGBA")
        fit_w = card_w - 20
        fit_h = int(round(bust.height * (fit_w / bust.width)))
        bust_res = bust.resize((fit_w, min(card_h - 84, fit_h)), Image.Resampling.LANCZOS)
        sheet.paste(bust_res, (ex_x + 10, ex_y + 12), bust_res)
        dr.rectangle([ex_x, ex_y + card_h - 68, ex_x + card_w, ex_y + card_h], fill=(36, 28, 25))
        dr.text((ex_x + 14, ex_y + card_h - 58), f"E{e_idx+1}: {expr}", fill=(252, 236, 198), font=f_lbl)
        dr.text((ex_x + 14, ex_y + card_h - 30), f"Hand: {ep_info['hand_pose']}", fill=(198, 190, 176), font=f_sub)

    sheet.save(sheet_path, format="PNG")
    return {
        "gate_id": "VQ02_CHARACTER_MODEL_SHEET_CANDIDATE",
        "editorial_status": "HUMAN_REVIEW_PENDING",
        "actor_id": aid,
        "model_sheet_path": str(sheet_path.relative_to(ROOT_DIR).as_posix() if sheet_path.is_relative_to(ROOT_DIR) else sheet_path),
        "model_sheet_sha256": _sha256_file(sheet_path),
        "dimensions": [W, H],
        "unique_view_hashes": len({character_asset["view_assets"][v]["sha256"] for v in ("front", "three_quarter", "profile")}),
        "unique_expression_hashes": len(set(expr_hashes)),
    }


def export_character_rig_manifest(
    character_asset: Dict[str, Any],
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Export a genuine Spine 3.8 / Rigby2D `1024x1024` RGBA character sprite atlas, `.atlas` text,
    `.json` multi-bone + 4-IK skeleton (with all 6 facial expression head attachments and open/grip
    hand attachments!), and cryptographic `<actor_id>_rig_manifest.json`.
    """
    spec = character_asset["spec"]
    aid = character_asset["actor_id"]
    rig_d = Path(out_dir) if out_dir else (Path(character_asset["output_dir"]) / "rigby2d")
    rig_d.mkdir(parents=True, exist_ok=True)

    atlas_size = (1024, 1024)
    atlas_img = Image.new("RGBA", atlas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(atlas_img, "RGBA")

    ink = _hex_rgba(spec["ink_outer_hex"])
    ink_in = _hex_rgba(spec["ink_inner_hex"])
    skin = _hex_rgba(spec["skin_palette"]["base"])
    skin_sh = _hex_rgba(spec["skin_palette"]["shadow"])
    skin_rim = _hex_rgba(spec["skin_palette"]["rim"])
    hair = _hex_rgba(spec["hair_palette"]["base"])
    hair_hl = _hex_rgba(spec["hair_palette"]["highlight"])
    wd = spec["wardrobe"]
    prim = _hex_rgba(wd["primary_hex"])
    prim_sh = _hex_rgba(wd["primary_shadow_hex"])
    prim_rim = _hex_rgba(wd["primary_rim_hex"])
    sec = _hex_rgba(wd["secondary_hex"])
    trim = _hex_rgba(wd["trim_hex"])
    acc = _hex_rgba(wd["accessory_hex"])

    regions: Dict[str, Tuple[int, int, int, int]] = {
        "torso_tunic": (16, 16, 168, 224),
        "cloak_back": (200, 16, 152, 232),
        "upper_arm_r": (368, 16, 68, 118),
        "lower_arm_r": (448, 16, 62, 112),
        "hand_r": (524, 16, 56, 56),
        "hand_r_grip": (592, 16, 56, 56),
        "upper_arm_l": (368, 148, 68, 118),
        "lower_arm_l": (448, 148, 62, 112),
        "hand_l": (524, 148, 56, 56),
        "upper_leg_r": (16, 264, 78, 136),
        "lower_leg_r": (108, 264, 68, 128),
        "sandal_r": (190, 264, 98, 54),
        "upper_leg_l": (304, 264, 78, 136),
        "lower_leg_l": (396, 264, 68, 128),
        "sandal_l": (478, 264, 98, 54),
    }
    # 6 distinct expression head plates on bottom half of 1024x1024 atlas!
    for idx_e, expr in enumerate(REQUIRED_EXPRESSIONS):
        col = idx_e % 4
        row = idx_e // 4
        rx = 16 + col * 240
        ry = 432 + row * 248
        regions[f"head_{expr}"] = (rx, ry, 220, 228)
    regions["head"] = regions["head_neutral_attentive"]

    # 1. Torso with cel shading + rim light + satchel/belt/apron detail
    x, y, w, h = regions["torso_tunic"]
    d.polygon([(x + 22, y + 14), (x + w - 22, y + 14), (x + w - 10, y + h - 14), (x + 10, y + h - 14)], fill=prim)
    d.polygon([(x + w // 2 + 10, y + 14), (x + w - 22, y + 14), (x + w - 10, y + h - 14), (x + w // 2 + 4, y + h - 14)], fill=prim_sh)
    d.polygon([(x + 24, y + 18), (x + 42, y + 18), (x + 30, y + h - 18), (x + 14, y + h - 18)], fill=prim_rim)
    d.line([(x + 34, y + 20), (x + w - 28, y + 148)], fill=acc, width=10)
    d.rounded_rectangle([x + 16, y + 132, x + w - 16, y + 154], radius=6, fill=acc, outline=ink, width=5)
    d.ellipse([x + w // 2 - 11, y + 130, x + w // 2 + 11, y + 156], fill=trim, outline=ink, width=4)
    d.rectangle([x + 14, y + h - 30, x + w - 14, y + h - 18], fill=trim)
    _draw_tapered_stroke(
        d,
        [(x + 22, y + 14), (x + w - 22, y + 14), (x + w - 10, y + h - 14), (x + 10, y + h - 14), (x + 22, y + 14)],
        ink,
        6.5,
        taper_ends=False,
    )

    # 2. Flowing scarf / cloak back
    x, y, w, h = regions["cloak_back"]
    d.polygon([(x + 28, y + 12), (x + w - 28, y + 12), (x + w - 10, y + h - 12), (x + 14, y + h - 18)], fill=sec)
    _draw_tapered_stroke(
        d,
        [(x + 28, y + 12), (x + w - 28, y + 12), (x + w - 10, y + h - 12), (x + 14, y + h - 18), (x + 28, y + 12)],
        ink,
        6.0,
        taper_ends=False,
    )

    # 3. Arms & Hands (open vs locked grip)
    for side, sk_c, tn_c in [("r", skin, prim), ("l", skin_sh, prim_sh)]:
        x, y, w, h = regions[f"upper_arm_{side}"]
        d.rounded_rectangle([x + 10, y + 10, x + w - 10, y + h - 10], radius=18, fill=sk_c, outline=ink, width=6)
        d.rounded_rectangle([x + 6, y + 6, x + w - 6, y + 54], radius=14, fill=tn_c, outline=ink, width=6)

        x, y, w, h = regions[f"lower_arm_{side}"]
        d.rounded_rectangle([x + 9, y + 9, x + w - 9, y + h - 9], radius=16, fill=sk_c, outline=ink, width=6)
        d.rounded_rectangle([x + 10, y + h - 30, x + w - 10, y + h - 16], radius=4, fill=acc, outline=ink, width=4)

        x, y, w, h = regions[f"hand_{side}"]
        d.ellipse([x + 6, y + 6, x + w - 6, y + h - 6], fill=sk_c, outline=ink, width=5)
        for fi in range(3):
            d.line([(x + w - 12, y + 14 + fi * 10), (x + w - 2, y + 14 + fi * 10)], fill=ink, width=4)

    # Dedicated locked-grip hand attachment
    x, y, w, h = regions["hand_r_grip"]
    d.rounded_rectangle([x + 6, y + 8, x + w - 6, y + h - 8], radius=14, fill=skin, outline=ink, width=6)
    for fi in range(3):
        d.line([(x + 14, y + 18 + fi * 9), (x + w - 12, y + 18 + fi * 9)], fill=ink_in, width=4)

    # 4. Legs & Footwear
    for side, sk_c, tn_c in [("r", skin, prim), ("l", skin_sh, prim_sh)]:
        x, y, w, h = regions[f"upper_leg_{side}"]
        d.rounded_rectangle([x + 10, y + 8, x + w - 10, y + h - 8], radius=18, fill=sk_c, outline=ink, width=6)
        d.rounded_rectangle([x + 6, y + 6, x + w - 6, y + 56], radius=14, fill=tn_c, outline=ink, width=6)

        x, y, w, h = regions[f"lower_leg_{side}"]
        d.rounded_rectangle([x + 9, y + 8, x + w - 9, y + h - 8], radius=16, fill=sk_c, outline=ink, width=6)
        d.line([(x + 12, y + h - 42), (x + w - 12, y + h - 18)], fill=acc, width=5)
        d.line([(x + w - 12, y + h - 42), (x + 12, y + h - 18)], fill=acc, width=5)

        x, y, w, h = regions[f"sandal_{side}"]
        d.polygon([(x + 10, y + 10), (x + 62, y + 14), (x + w - 8, y + h - 8), (x + 8, y + h - 8)], fill=acc, outline=ink)
        _draw_tapered_stroke(
            d,
            [(x + 10, y + 10), (x + 62, y + 14), (x + w - 8, y + h - 8), (x + 8, y + h - 8), (x + 10, y + 10)],
            ink,
            5.5,
            taper_ends=False,
        )

    # 5. Render all 6 distinct facial expression heads into the atlas!
    for expr in REQUIRED_EXPRESSIONS:
        rx, ry, rw, rh = regions[f"head_{expr}"]
        cx_h = rx + rw * 0.48
        cy_h = ry + rh * 0.48
        r_h = rw * 0.34
        d.rounded_rectangle([cx_h - r_h * 0.32, cy_h + r_h * 0.78, cx_h + r_h * 0.32, ry + rh - 10], radius=10, fill=skin_sh, outline=ink, width=5)
        d.ellipse([cx_h - r_h, cy_h - r_h, cx_h + r_h, cy_h + r_h], fill=skin, outline=ink, width=6)
        d.arc([cx_h - r_h * 0.94, cy_h - r_h * 0.94, cx_h + r_h * 0.94, cy_h + r_h * 0.94], 140, 250, fill=skin_rim, width=5)
        _draw_character_expression_face(d, cx_h, cy_h, r_h, spec, expr, "three_quarter", ink, ink_in, 5.5)
        hair_cap = [
            (cx_h - r_h * 0.98, cy_h - r_h * 0.16),
            (cx_h - r_h * 0.80, cy_h - r_h * 1.08),
            (cx_h + r_h * 0.22, cy_h - r_h * 1.24),
            (cx_h + r_h * 0.94, cy_h - r_h * 0.84),
            (cx_h + r_h * 0.98, cy_h - r_h * 0.32),
            (cx_h + r_h * 0.34, cy_h - r_h * 0.60),
            (cx_h - r_h * 0.28, cy_h - r_h * 0.52),
        ]
        d.polygon(hair_cap, fill=hair)
        _draw_tapered_stroke(d, [(cx_h - r_h * 0.45, cy_h - r_h * 0.92), (cx_h + r_h * 0.45, cy_h - r_h * 0.82)], hair_hl, 6.0)
        _draw_tapered_stroke(d, hair_cap + [hair_cap[0]], ink, 5.5, taper_ends=False)

    png_name = f"{aid}.png"
    png_path = rig_d / png_name
    atlas_img.save(png_path, format="PNG")

    # Spine .atlas text
    atlas_lines = [
        png_name,
        f"size: {atlas_size[0]}, {atlas_size[1]}",
        "format: RGBA8888",
        "filter: Linear, Linear",
        "repeat: none",
        "pma: false",
    ]
    for r_name, (rx, ry, rw, rh) in regions.items():
        atlas_lines.extend([
            r_name,
            "  rotate: false",
            f"  bounds: {rx}, {ry}, {rw}, {rh}",
            f"  offsets: 0, 0, {rw}, {rh}",
        ])
    atlas_path = rig_d / f"{aid}.atlas"
    atlas_path.write_text("\n".join(atlas_lines) + "\n", encoding="utf-8")

    # Spine 3.8 skeleton JSON (compatible with Rigby2D 0.5.1 readSkeletonJson & convertMotionPlanToRigbyTracks)
    bones = [
        {"name": "root", "x": 0, "y": 0},
        {"name": "pelvis", "parent": "root", "x": 0, "y": 92, "length": 18, "rotation": 90},
        {"name": "torso", "parent": "pelvis", "x": 14, "y": 0, "length": 68, "rotation": 0},
        {"name": "cloak", "parent": "torso", "x": 58, "y": 8, "length": 88, "rotation": 176},
        {"name": "head", "parent": "torso", "x": 68, "y": 0, "length": 44, "rotation": 0},
        {"name": "upper_arm_l", "parent": "torso", "x": 58, "y": -10, "length": 38, "rotation": -162},
        {"name": "lower_arm_l", "parent": "upper_arm_l", "x": 38, "y": 0, "length": 34, "rotation": 22},
        {"name": "hand_l", "parent": "lower_arm_l", "x": 34, "y": 0, "length": 14, "rotation": 0},
        {"name": "upper_arm_r", "parent": "torso", "x": 58, "y": 10, "length": 38, "rotation": -172},
        {"name": "lower_arm_r", "parent": "upper_arm_r", "x": 38, "y": 0, "length": 34, "rotation": 18},
        {"name": "hand_r", "parent": "lower_arm_r", "x": 34, "y": 0, "length": 14, "rotation": 0},
        {"name": "upper_leg_l", "parent": "pelvis", "x": 0, "y": -6, "length": 44, "rotation": 175},
        {"name": "lower_leg_l", "parent": "upper_leg_l", "x": 44, "y": 0, "length": 42, "rotation": -8},
        {"name": "foot_l", "parent": "lower_leg_l", "x": 42, "y": 0, "length": 20, "rotation": 88},
        {"name": "upper_leg_r", "parent": "pelvis", "x": 0, "y": 6, "length": 44, "rotation": 184},
        {"name": "lower_leg_r", "parent": "upper_leg_r", "x": 44, "y": 0, "length": 42, "rotation": -8},
        {"name": "foot_r", "parent": "lower_leg_r", "x": 42, "y": 0, "length": 20, "rotation": 88},
        {"name": "ik_foot_l_target", "parent": "root", "x": 10, "y": 6},
        {"name": "ik_foot_r_target", "parent": "root", "x": -8, "y": 6},
        {"name": "ik_hand_l_target", "parent": "root", "x": 28, "y": 98},
        {"name": "ik_hand_r_target", "parent": "root", "x": 24, "y": 94},
    ]
    slots = [
        {"name": "cloak_back", "bone": "cloak", "attachment": "cloak_back"},
        {"name": "upper_arm_l", "bone": "upper_arm_l", "attachment": "upper_arm_l"},
        {"name": "lower_arm_l", "bone": "lower_arm_l", "attachment": "lower_arm_l"},
        {"name": "hand_l", "bone": "hand_l", "attachment": "hand_l"},
        {"name": "upper_leg_l", "bone": "upper_leg_l", "attachment": "upper_leg_l"},
        {"name": "lower_leg_l", "bone": "lower_leg_l", "attachment": "lower_leg_l"},
        {"name": "sandal_l", "bone": "foot_l", "attachment": "sandal_l"},
        {"name": "torso_tunic", "bone": "torso", "attachment": "torso_tunic"},
        {"name": "upper_leg_r", "bone": "upper_leg_r", "attachment": "upper_leg_r"},
        {"name": "lower_leg_r", "bone": "lower_leg_r", "attachment": "lower_leg_r"},
        {"name": "sandal_r", "bone": "foot_r", "attachment": "sandal_r"},
        {"name": "head", "bone": "head", "attachment": "head_neutral_attentive"},
        {"name": "upper_arm_r", "bone": "upper_arm_r", "attachment": "upper_arm_r"},
        {"name": "lower_arm_r", "bone": "lower_arm_r", "attachment": "lower_arm_r"},
        {"name": "hand_r", "bone": "hand_r", "attachment": "hand_r"},
    ]
    head_skin_attachments = {
        f"head_{expr}": {"x": 26, "y": -2, "rotation": -90, "width": 78, "height": 82}
        for expr in REQUIRED_EXPRESSIONS
    }
    head_skin_attachments["head"] = {"x": 26, "y": -2, "rotation": -90, "width": 78, "height": 82}

    skins = {
        "default": {
            "cloak_back": {"cloak_back": {"x": 44, "y": 0, "rotation": 90, "width": 84, "height": 124}},
            "torso_tunic": {"torso_tunic": {"x": 34, "y": 0, "rotation": -90, "width": 88, "height": 116}},
            "head": head_skin_attachments,
            "upper_arm_l": {"upper_arm_l": {"x": 19, "y": 0, "rotation": 90, "width": 34, "height": 58}},
            "lower_arm_l": {"lower_arm_l": {"x": 17, "y": 0, "rotation": 90, "width": 30, "height": 54}},
            "hand_l": {"hand_l": {"x": 7, "y": 0, "rotation": 90, "width": 26, "height": 26}},
            "upper_arm_r": {"upper_arm_r": {"x": 19, "y": 0, "rotation": 90, "width": 34, "height": 58}},
            "lower_arm_r": {"lower_arm_r": {"x": 17, "y": 0, "rotation": 90, "width": 30, "height": 54}},
            "hand_r": {
                "hand_r": {"x": 7, "y": 0, "rotation": 90, "width": 26, "height": 26},
                "hand_r_grip": {"x": 7, "y": 0, "rotation": 90, "width": 26, "height": 26},
            },
            "upper_leg_l": {"upper_leg_l": {"x": 22, "y": 0, "rotation": 90, "width": 40, "height": 68}},
            "lower_leg_l": {"lower_leg_l": {"x": 21, "y": 0, "rotation": 90, "width": 34, "height": 64}},
            "sandal_l": {"sandal_l": {"x": 10, "y": -2, "rotation": 0, "width": 48, "height": 26}},
            "upper_leg_r": {"upper_leg_r": {"x": 22, "y": 0, "rotation": 90, "width": 40, "height": 68}},
            "lower_leg_r": {"lower_leg_r": {"x": 21, "y": 0, "rotation": 90, "width": 34, "height": 64}},
            "sandal_r": {"sandal_r": {"x": 10, "y": -2, "rotation": 0, "width": 48, "height": 26}},
        }
    }
    ik = [
        {"name": "ik_leg_l", "order": 0, "bones": ["upper_leg_l", "lower_leg_l"], "target": "ik_foot_l_target", "bendPositive": False, "mix": 1.0},
        {"name": "ik_leg_r", "order": 1, "bones": ["upper_leg_r", "lower_leg_r"], "target": "ik_foot_r_target", "bendPositive": False, "mix": 1.0},
        {"name": "ik_arm_l", "order": 2, "bones": ["upper_arm_l", "lower_arm_l"], "target": "ik_hand_l_target", "bendPositive": True, "mix": 1.0},
        {"name": "ik_arm_r", "order": 3, "bones": ["upper_arm_r", "lower_arm_r"], "target": "ik_hand_r_target", "bendPositive": True, "mix": 1.0},
    ]
    animations = {
        "idle": {
            "bones": {
                "pelvis": {"translate": [{"time": 0, "x": 0, "y": 0}, {"time": 0.6, "x": 0, "y": -2.0}, {"time": 1.2, "x": 0, "y": 0}]},
                "torso": {"rotate": [{"time": 0, "angle": 0}, {"time": 0.6, "angle": -1.8}, {"time": 1.2, "angle": 0}]},
                "cloak": {"rotate": [{"time": 0, "angle": 0}, {"time": 0.6, "angle": 4.2}, {"time": 1.2, "angle": 0}]},
            }
        },
        "catch_scroll": {
            "bones": {
                "pelvis": {"translate": [{"time": 0, "x": 0, "y": 0}, {"time": 0.3, "x": 4, "y": -10}, {"time": 0.7, "x": 10, "y": 8}, {"time": 1.2, "x": 4, "y": -3}]},
                "torso": {"rotate": [{"time": 0, "angle": 0}, {"time": 0.3, "angle": -14}, {"time": 0.7, "angle": -8}, {"time": 1.2, "angle": -2}]},
                "ik_hand_r_target": {"translate": [{"time": 0, "x": 0, "y": 0}, {"time": 0.35, "x": 28, "y": 38}, {"time": 0.7, "x": 36, "y": 46}, {"time": 1.2, "x": 18, "y": 24}]},
                "cloak": {"rotate": [{"time": 0, "angle": 0}, {"time": 0.5, "angle": 18}, {"time": 1.2, "angle": 4}]},
            },
            "slots": {
                "head": {"attachment": [{"time": 0, "name": "head_determined_focus"}, {"time": 0.35, "name": "head_strained_exertion"}, {"time": 0.75, "name": "head_joyful_laugh"}]},
                "hand_r": {"attachment": [{"time": 0, "name": "hand_r"}, {"time": 0.45, "name": "hand_r_grip"}]},
            },
        },
    }
    skel_json = {
        "skeleton": {"hash": f"kh01_{aid}_v1", "spine": "3.8.99", "x": -64, "y": 0, "width": 128, "height": 225},
        "bones": bones,
        "slots": slots,
        "ik": ik,
        "skins": skins,
        "animations": animations,
    }
    skel_path = rig_d / f"{aid}.json"
    skel_path.write_text(json.dumps(skel_json, indent=2), encoding="utf-8")

    rig_manifest = {
        "schema_version": "kh01.rig_manifest.v1",
        "character_id": aid,
        "name": spec["name"],
        "niche": spec["niche"],
        "style_id": spec["style_id"],
        "spine_format_version": "3.8.99",
        "height_units": 210.0,
        "setup_targets": {
            "ik_foot_l_target": {"x": 10.0, "y": 6.0},
            "ik_foot_r_target": {"x": -8.0, "y": 6.0},
            "ik_hand_l_target": {"x": 28.0, "y": 98.0},
            "ik_hand_r_target": {"x": 24.0, "y": 94.0},
        },
        "bones": [b["name"] for b in bones],
        "slots": [s["name"] for s in slots],
        "ik_constraints": [c["name"] for c in ik],
        "supported_views": list(REQUIRED_VIEWS),
        "view_art_mapping": {vw: character_asset["view_assets"][vw]["path"] for vw in REQUIRED_VIEWS},
        "expression_attachments": {expr: f"head_{expr}" for expr in REQUIRED_EXPRESSIONS},
        "hand_attachments": {"open": "hand_r", "locked_grip": "hand_r_grip"},
        "viseme_mapping": {
            "closed_rest": "head_neutral_attentive",
            "open_ah": "head_wide_shock",
            "teeth_grit": "head_strained_exertion",
            "wide_laugh": "head_joyful_laugh",
        },
        "files": {
            "skeleton_json": {
                "path": str(skel_path.relative_to(ROOT_DIR).as_posix() if skel_path.is_relative_to(ROOT_DIR) else skel_path),
                "sha256": _sha256_file(skel_path),
            },
            "atlas": {
                "path": str(atlas_path.relative_to(ROOT_DIR).as_posix() if atlas_path.is_relative_to(ROOT_DIR) else atlas_path),
                "sha256": _sha256_file(atlas_path),
            },
            "texture_png": {
                "path": str(png_path.relative_to(ROOT_DIR).as_posix() if png_path.is_relative_to(ROOT_DIR) else png_path),
                "sha256": _sha256_file(png_path),
                "dimensions": list(atlas_size),
            },
        },
        "rigby_demo_assets_copied": False,
        "reference_frames_reused": 0,
    }
    mf_path = rig_d / f"{aid}_rig_manifest.json"
    mf_path.write_text(json.dumps(rig_manifest, indent=2), encoding="utf-8")
    rig_manifest["manifest_path"] = str(mf_path.relative_to(ROOT_DIR).as_posix() if mf_path.is_relative_to(ROOT_DIR) else mf_path)
    return rig_manifest


def validate_character_consistency(
    actor: Dict[str, Any],
    shots: Sequence[Dict[str, Any]],
    frames: Optional[Sequence[Path | str]] = None,
) -> Dict[str, Any]:
    """
    Validate character identity, clothing material/color continuity, head-to-body ratio,
    supported view coverage, and non-teleporting held props across shots and optional decoded PNGs.
    """
    spec = actor.get("spec") or actor
    aid = str(spec.get("actor_id") or actor.get("actor_id") or "")
    errors: List[str] = []
    warnings: List[str] = []

    if not aid:
        return {"valid": False, "status": "FAIL", "errors": ["Missing actor_id in character spec"]}

    views = set(actor.get("views") or spec.get("supported_views") or [])
    if not {"front", "three_quarter", "profile"}.issubset(views):
        errors.append(f"Character '{aid}' missing required views (front/three_quarter/profile): {sorted(views)}")

    exprs = set(actor.get("expressions") or spec.get("supported_expressions") or [])
    if len(exprs) < 6:
        errors.append(f"Character '{aid}' has fewer than 6 distinct expressions ({len(exprs)})")

    expected_outfit = str((spec.get("wardrobe") or {}).get("outfit_id") or "")
    expected_primary_hex = str((spec.get("wardrobe") or {}).get("primary_hex") or "").lower()
    expected_ratio = float((spec.get("proportions") or {}).get("head_to_height_ratio") or 0.215)

    prev_x: Optional[float] = None
    for s in shots or []:
        sid = str(s.get("id") or s.get("shot_id") or "S01")
        args = s.get("args") or {}
        change_event = s.get("outfit_change_reason") or (s.get("art_direction") or {}).get("outfit_change_reason")
        for p in args.get("people") or []:
            if not isinstance(p, dict) or str(p.get("id") or "") != aid:
                continue
            p_outfit = str(p.get("outfitId") or expected_outfit)
            if expected_outfit and p_outfit != expected_outfit and not change_event:
                errors.append(f"Shot {sid}: actor '{aid}' unmotivated costume change ('{expected_outfit}' -> '{p_outfit}')")
                expected_outfit = p_outfit
            elif change_event and p_outfit != expected_outfit:
                expected_outfit = p_outfit

            p_col = str(p.get("primaryColor") or expected_primary_hex).lower()
            if expected_primary_hex and p_col != expected_primary_hex and not change_event:
                errors.append(f"Shot {sid}: actor '{aid}' garment color changed mid-film ({expected_primary_hex} -> {p_col})")

            p_ratio = float(p.get("headToHeightRatio") or expected_ratio)
            if abs(p_ratio - expected_ratio) > 0.035:
                errors.append(f"Shot {sid}: actor '{aid}' head/body ratio drifted ({p_ratio:.3f} vs {expected_ratio:.3f})")

            cur_x = float(p.get("x", 0.5))
            if prev_x is not None and abs(cur_x - prev_x) > 0.68 and not s.get("intentional_cut_reason"):
                warnings.append(f"Shot {sid}: large spatial jump for '{aid}' ({prev_x:.2f} -> {cur_x:.2f}) without cut reason")
            prev_x = cur_x

    # Optional decoded pixel garment-hue presence check across supplied rendered frames
    frame_color_checks: List[Dict[str, Any]] = []
    if frames and expected_primary_hex.startswith("#") and len(expected_primary_hex) == 7:
        tr_r, tr_g, tr_b, _ = _hex_rgba(expected_primary_hex)
        for fp_raw in frames:
            fp = Path(fp_raw)
            if not fp.is_file():
                continue
            with Image.open(fp) as im:
                arr = np.asarray(im.convert("RGB"), dtype=np.float32)
            dist = np.sqrt((arr[:, :, 0] - tr_r) ** 2 + (arr[:, :, 1] - tr_g) ** 2 + (arr[:, :, 2] - tr_b) ** 2)
            match_ratio = float(np.mean(dist < 42.0))
            frame_color_checks.append({
                "frame": fp.name,
                "garment_color_pixel_ratio": round(match_ratio, 5),
                "detected": match_ratio >= 0.0015,
            })

    return {
        "valid": len(errors) == 0,
        "status": "PASS" if len(errors) == 0 else "FAIL",
        "actor_id": aid,
        "checked_shots": len(shots or []),
        "frame_color_checks": frame_color_checks,
        "errors": errors,
        "warnings": warnings,
    }
