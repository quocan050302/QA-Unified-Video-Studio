#!/usr/bin/env python3
"""Generate 100% original layered Roman civilian skeletal rig assets for V14.7.6 Rigby2D pilot.

Creates:
- integrations/rigby2d/assets/roman_harbor_worker.png (512x512 RGBA sprite atlas, 15 body-part regions)
- integrations/rigby2d/assets/roman_harbor_worker.atlas (Rigby2D / Spine text atlas)
- integrations/rigby2d/assets/roman_harbor_worker.json (Spine 3.8 / Rigby2D skeleton + 4 2-bone IK constraints + base animations)
- integrations/rigby2d/assets/roman_harbor_worker_manifest.json (rig manifest & SHA-256 provenance)
- integrations/rigby2d/SOURCE_PROVENANCE.json (complete runtime + original-asset hash manifest)

Zero external images, zero Rigby2D demo mascots (NILA/Rigbytron), zero prior FL-01 preview stills.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw

RIG_DIR = Path(__file__).resolve().parent
ASSETS_DIR = RIG_DIR / "assets"
VENDOR_DIR = RIG_DIR / "vendor"

INK = (26, 20, 18, 255)
SKIN = (218, 168, 132, 255)
SKIN_SHADOW = (188, 136, 102, 255)
HAIR = (56, 38, 28, 255)
TUNIC_MAIN = (176, 82, 54, 255)
TUNIC_DARK = (134, 56, 36, 255)
TUNIC_TRIM = (218, 186, 122, 255)
CLOAK = (66, 84, 98, 255)
CLOAK_DARK = (46, 60, 72, 255)
BELT = (88, 54, 32, 255)
SANDAL = (102, 64, 38, 255)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _draw_capsule(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    fill: Tuple[int, int, int, int],
    outline: Tuple[int, int, int, int] = INK,
    width: int = 3,
    radius: int = 12,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build_original_atlas_image() -> Tuple[Image.Image, Dict[str, Tuple[int, int, int, int]]]:
    """Draw 15 original Roman civilian body-part sprites onto a clean 512x512 RGBA sheet."""
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    regions: Dict[str, Tuple[int, int, int, int]] = {
        "torso_tunic": (8, 8, 92, 128),
        "cloak_back": (108, 8, 88, 132),
        "head": (204, 8, 72, 78),
        "upper_arm_r": (286, 8, 36, 62),
        "lower_arm_r": (330, 8, 32, 58),
        "hand_r": (370, 8, 28, 28),
        "upper_arm_l": (286, 80, 36, 62),
        "lower_arm_l": (330, 80, 32, 58),
        "hand_l": (370, 80, 28, 28),
        "upper_leg_r": (8, 152, 42, 72),
        "lower_leg_r": (58, 152, 36, 68),
        "sandal_r": (102, 152, 52, 28),
        "upper_leg_l": (164, 152, 42, 72),
        "lower_leg_l": (214, 152, 36, 68),
        "sandal_l": (258, 152, 52, 28),
    }

    # 1. Torso tunic (Roman harbor worker wool tunic + rope belt + shoulder hem)
    x, y, w, h = regions["torso_tunic"]
    d.polygon(
        [(x + 14, y + 8), (x + w - 14, y + 8), (x + w - 6, y + h - 8), (x + 6, y + h - 8)],
        fill=TUNIC_MAIN,
        outline=INK,
    )
    d.line([(x + 14, y + 8), (x + w - 14, y + 8), (x + w - 6, y + h - 8), (x + 6, y + h - 8), (x + 14, y + 8)], fill=INK, width=3)
    # Tunic folds & trim
    d.line([(x + 30, y + 24), (x + 26, y + h - 14)], fill=TUNIC_DARK, width=3)
    d.line([(x + 58, y + 22), (x + 62, y + h - 14)], fill=TUNIC_DARK, width=3)
    d.rectangle([x + 9, y + h - 18, x + w - 9, y + h - 11], fill=TUNIC_TRIM)
    # Rope/leather belt
    d.rounded_rectangle([x + 10, y + 72, x + w - 10, y + 84], radius=4, fill=BELT, outline=INK, width=2)
    d.ellipse([x + w // 2 - 6, y + 71, x + w // 2 + 6, y + 85], fill=TUNIC_TRIM, outline=INK, width=2)

    # 2. Weather cloak back
    x, y, w, h = regions["cloak_back"]
    d.polygon(
        [(x + 18, y + 6), (x + w - 18, y + 6), (x + w - 4, y + h - 6), (x + 8, y + h - 10)],
        fill=CLOAK,
        outline=INK,
    )
    d.line([(x + 18, y + 6), (x + w - 18, y + 6), (x + w - 4, y + h - 6), (x + 8, y + h - 10), (x + 18, y + 6)], fill=INK, width=3)
    d.line([(x + 34, y + 18), (x + 24, y + h - 16)], fill=CLOAK_DARK, width=3)
    d.line([(x + 56, y + 18), (x + 66, y + h - 14)], fill=CLOAK_DARK, width=3)

    # 3. Head (expressive Roman civilian profile-three-quarter facing right)
    x, y, w, h = regions["head"]
    # Neck
    _draw_capsule(d, (x + 24, y + 52, x + 46, y + 74), fill=SKIN_SHADOW, width=3, radius=6)
    # Cranium
    d.ellipse([x + 10, y + 10, x + 60, y + 62], fill=SKIN, outline=INK, width=3)
    # Nose facing +X (right)
    d.polygon([(x + 56, y + 29), (x + 66, y + 38), (x + 56, y + 42)], fill=SKIN, outline=INK)
    d.line([(x + 56, y + 29), (x + 66, y + 38), (x + 56, y + 42)], fill=INK, width=3)
    # Short curly Roman hair cap + headband
    d.pieslice([x + 8, y + 6, x + 60, y + 52], start=165, end=355, fill=HAIR, outline=INK, width=3)
    d.line([(x + 13, y + 24), (x + 56, y + 22)], fill=TUNIC_TRIM, width=3)
    # Eye + brow + focused mouth
    d.ellipse([x + 44, y + 30, x + 51, y + 37], fill=INK)
    d.ellipse([x + 46, y + 31, x + 48, y + 33], fill=(255, 255, 255, 255))
    d.line([(x + 41, y + 26), (x + 53, y + 27)], fill=HAIR, width=3)
    d.line([(x + 45, y + 49), (x + 55, y + 48)], fill=INK, width=2)

    # 4. Arms & hands (right = foreground brighter, left = far-side slightly shaded)
    for side, skin_col, tunic_col in [
        ("r", SKIN, TUNIC_MAIN),
        ("l", SKIN_SHADOW, TUNIC_DARK),
    ]:
        x, y, w, h = regions[f"upper_arm_{side}"]
        _draw_capsule(d, (x + 6, y + 6, x + w - 6, y + h - 6), fill=skin_col, width=3, radius=10)
        _draw_capsule(d, (x + 4, y + 4, x + w - 4, y + 28), fill=tunic_col, width=3, radius=8)

        x, y, w, h = regions[f"lower_arm_{side}"]
        _draw_capsule(d, (x + 5, y + 5, x + w - 5, y + h - 5), fill=skin_col, width=3, radius=9)
        d.rectangle([x + 6, y + h - 16, x + w - 6, y + h - 9], fill=BELT, outline=INK, width=2)

        x, y, w, h = regions[f"hand_{side}"]
        d.ellipse([x + 3, y + 3, x + w - 3, y + h - 3], fill=skin_col, outline=INK, width=3)
        d.arc([x + 7, y + 7, x + w - 5, y + h - 5], start=20, end=190, fill=INK, width=2)

    # 5. Legs & Roman sandals (caligae / harbor leather straps)
    for side, skin_col, tunic_col in [
        ("r", SKIN, TUNIC_MAIN),
        ("l", SKIN_SHADOW, TUNIC_DARK),
    ]:
        x, y, w, h = regions[f"upper_leg_{side}"]
        _draw_capsule(d, (x + 6, y + 5, x + w - 6, y + h - 5), fill=skin_col, width=3, radius=11)
        _draw_capsule(d, (x + 4, y + 4, x + w - 4, y + 30), fill=tunic_col, width=3, radius=9)

        x, y, w, h = regions[f"lower_leg_{side}"]
        _draw_capsule(d, (x + 5, y + 5, x + w - 5, y + h - 5), fill=skin_col, width=3, radius=9)
        # Crossed sandal ankle straps
        d.line([(x + 7, y + h - 22), (x + w - 7, y + h - 10)], fill=SANDAL, width=3)
        d.line([(x + w - 7, y + h - 22), (x + 7, y + h - 10)], fill=SANDAL, width=3)

        x, y, w, h = regions[f"sandal_{side}"]
        d.polygon(
            [(x + 6, y + 6), (x + 32, y + 8), (x + w - 4, y + h - 6), (x + 4, y + h - 4)],
            fill=SANDAL,
            outline=INK,
        )
        d.line([(x + 6, y + 6), (x + 32, y + 8), (x + w - 4, y + h - 6), (x + 4, y + h - 4), (x + 6, y + 6)], fill=INK, width=3)
        d.line([(x + 4, y + h - 5), (x + w - 4, y + h - 5)], fill=INK, width=4)

    return img, regions


def build_atlas_text(page_name: str, size: Tuple[int, int], regions: Dict[str, Tuple[int, int, int, int]]) -> str:
    lines: List[str] = [
        page_name,
        f"size: {size[0]}, {size[1]}",
        "format: RGBA8888",
        "filter: Linear, Linear",
        "repeat: none",
        "pma: false",
    ]
    for name, (x, y, w, h) in regions.items():
        lines.extend(
            [
                name,
                "  rotate: false",
                f"  bounds: {x}, {y}, {w}, {h}",
                f"  offsets: 0, 0, {w}, {h}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_skeleton_json(regions: Dict[str, Tuple[int, int, int, int]]) -> dict:
    """Build Spine 3.8 / Rigby2D skeleton JSON with Y-up world coordinates (feet at y=0, head top ~y=220)."""
    bones = [
        {"name": "root", "x": 0, "y": 0},
        {"name": "pelvis", "parent": "root", "x": 0, "y": 92, "length": 18, "rotation": 90},
        {"name": "torso", "parent": "pelvis", "x": 14, "y": 0, "length": 68, "rotation": 0},
        {"name": "cloak", "parent": "torso", "x": 58, "y": 8, "length": 88, "rotation": 176},
        {"name": "head", "parent": "torso", "x": 68, "y": 0, "length": 44, "rotation": 0},
        # Arms (parent torso has world rotation +90 deg; local rotation -180 => world -90 straight down)
        {"name": "upper_arm_l", "parent": "torso", "x": 58, "y": -10, "length": 42, "rotation": -172},
        {"name": "lower_arm_l", "parent": "upper_arm_l", "x": 42, "y": 0, "length": 38, "rotation": 14},
        {"name": "hand_l", "parent": "lower_arm_l", "x": 38, "y": 0, "length": 14, "rotation": 0},
        {"name": "upper_arm_r", "parent": "torso", "x": 58, "y": 10, "length": 42, "rotation": -184},
        {"name": "lower_arm_r", "parent": "upper_arm_r", "x": 42, "y": 0, "length": 38, "rotation": 18},
        {"name": "hand_r", "parent": "lower_arm_r", "x": 38, "y": 0, "length": 14, "rotation": 0},
        # Legs (parent pelvis has world rotation +90 deg; local rotation -180 => world -90 straight down)
        {"name": "upper_leg_l", "parent": "pelvis", "x": 0, "y": -8, "length": 44, "rotation": -176},
        {"name": "lower_leg_l", "parent": "upper_leg_l", "x": 44, "y": 0, "length": 42, "rotation": -6},
        {"name": "foot_l", "parent": "lower_leg_l", "x": 42, "y": 0, "length": 24, "rotation": 92},
        {"name": "upper_leg_r", "parent": "pelvis", "x": 0, "y": 8, "length": 44, "rotation": -182},
        {"name": "lower_leg_r", "parent": "upper_leg_r", "x": 44, "y": 0, "length": 42, "rotation": -4},
        {"name": "foot_r", "parent": "lower_leg_r", "x": 42, "y": 0, "length": 24, "rotation": 96},
        # World-space IK targets parented to root
        {"name": "ik_foot_l_target", "parent": "root", "x": 10, "y": 6},
        {"name": "ik_foot_r_target", "parent": "root", "x": -8, "y": 6},
        {"name": "ik_hand_l_target", "parent": "root", "x": 28, "y": 98},
        {"name": "ik_hand_r_target", "parent": "root", "x": 24, "y": 94},
    ]

    # Draw order from back (far side + cloak) to front (near side arm/hand)
    slot_defs = [
        ("cloak_back", "cloak"),
        ("upper_arm_l", "upper_arm_l"),
        ("lower_arm_l", "lower_arm_l"),
        ("hand_l", "hand_l"),
        ("upper_leg_l", "upper_leg_l"),
        ("lower_leg_l", "lower_leg_l"),
        ("sandal_l", "foot_l"),
        ("upper_leg_r", "upper_leg_r"),
        ("lower_leg_r", "lower_leg_r"),
        ("sandal_r", "foot_r"),
        ("torso_tunic", "torso"),
        ("head", "head"),
        ("upper_arm_r", "upper_arm_r"),
        ("lower_arm_r", "lower_arm_r"),
        ("hand_r", "hand_r"),
    ]
    slots = [{"name": s_name, "bone": b_name, "attachment": s_name} for s_name, b_name in slot_defs]

    # Note on Rigby2D / Spine 2-bone IK bendPositive:
    # Legs: knee bends forward (+X in world, so bendPositive=False for hip->ankle downward vector)
    # Arms: elbow bends backward (-X in world, so bendPositive=True for shoulder->wrist downward/forward vector)
    ik = [
        {
            "name": "ik_leg_l",
            "order": 0,
            "bones": ["upper_leg_l", "lower_leg_l"],
            "target": "ik_foot_l_target",
            "bendPositive": False,
            "mix": 1.0,
        },
        {
            "name": "ik_leg_r",
            "order": 1,
            "bones": ["upper_leg_r", "lower_leg_r"],
            "target": "ik_foot_r_target",
            "bendPositive": False,
            "mix": 1.0,
        },
        {
            "name": "ik_arm_l",
            "order": 2,
            "bones": ["upper_arm_l", "lower_arm_l"],
            "target": "ik_hand_l_target",
            "bendPositive": True,
            "mix": 1.0,
        },
        {
            "name": "ik_arm_r",
            "order": 3,
            "bones": ["upper_arm_r", "lower_arm_r"],
            "target": "ik_hand_r_target",
            "bendPositive": True,
            "mix": 1.0,
        },
    ]

    def _att(name: str, ax: float, ay: float, rot: float) -> dict:
        _, _, w, h = regions[name]
        return {"x": ax, "y": ay, "rotation": rot, "width": w, "height": h}

    # Attachment offsets align each upright atlas sprite cleanly along its bone:
    # - For torso/head (bone world rot = +90 deg UP): local +X is UP, local +Y is LEFT -> rot = -90 makes sprite upright!
    # - For upper/lower limbs (bone world rot ~ -90 deg DOWN): local +X is DOWN, local +Y is RIGHT -> rot = +90 makes sprite upright!
    # - For feet (bone world rot ~ 0 deg RIGHT): local +X is RIGHT, local +Y is UP -> rot = 0 makes sandal horizontal!
    default_atts = {
        "cloak_back": {"cloak_back": _att("cloak_back", 46, -6, 94)},
        "torso_tunic": {"torso_tunic": _att("torso_tunic", 24, 0, -90)},
        "head": {"head": _att("head", 28, -3, -90)},
        "upper_arm_l": {"upper_arm_l": _att("upper_arm_l", 20, 0, 90)},
        "lower_arm_l": {"lower_arm_l": _att("lower_arm_l", 18, 0, 90)},
        "hand_l": {"hand_l": _att("hand_l", 6, 0, 90)},
        "upper_arm_r": {"upper_arm_r": _att("upper_arm_r", 20, 0, 90)},
        "lower_arm_r": {"lower_arm_r": _att("lower_arm_r", 18, 0, 90)},
        "hand_r": {"hand_r": _att("hand_r", 6, 0, 90)},
        "upper_leg_l": {"upper_leg_l": _att("upper_leg_l", 20, 0, 90)},
        "lower_leg_l": {"lower_leg_l": _att("lower_leg_l", 20, 0, 90)},
        "sandal_l": {"sandal_l": _att("sandal_l", 12, 4, 0)},
        "upper_leg_r": {"upper_leg_r": _att("upper_leg_r", 20, 0, 90)},
        "lower_leg_r": {"lower_leg_r": _att("lower_leg_r", 20, 0, 90)},
        "sandal_r": {"sandal_r": _att("sandal_r", 12, 4, 0)},
    }

    animations = {
        "idle": {
            "bones": {
                "pelvis": {
                    "translate": [
                        {"time": 0.0, "x": 0.0, "y": 0.0},
                        {"time": 1.0, "x": 0.0, "y": -2.0},
                        {"time": 2.0, "x": 0.0, "y": 0.0},
                    ]
                },
                "torso": {
                    "rotate": [
                        {"time": 0.0, "angle": 0.0},
                        {"time": 1.0, "angle": -2.2},
                        {"time": 2.0, "angle": 0.0},
                    ]
                },
                "head": {
                    "rotate": [
                        {"time": 0.0, "angle": 0.0},
                        {"time": 1.0, "angle": 2.5},
                        {"time": 2.0, "angle": 0.0},
                    ]
                },
            }
        },
        "walk": {
            "bones": {
                "pelvis": {
                    "translate": [
                        {"time": 0.0, "x": 0.0, "y": -2.0},
                        {"time": 0.25, "x": 0.0, "y": 2.5},
                        {"time": 0.5, "x": 0.0, "y": -2.0},
                        {"time": 0.75, "x": 0.0, "y": 2.5},
                        {"time": 1.0, "x": 0.0, "y": -2.0},
                    ]
                },
                "ik_foot_r_target": {
                    "translate": [
                        {"time": 0.0, "x": 28.0, "y": 0.0},
                        {"time": 0.5, "x": -20.0, "y": 0.0},
                        {"time": 0.75, "x": 4.0, "y": 16.0},
                        {"time": 1.0, "x": 28.0, "y": 0.0},
                    ]
                },
                "ik_foot_l_target": {
                    "translate": [
                        {"time": 0.0, "x": -24.0, "y": 0.0},
                        {"time": 0.25, "x": 2.0, "y": 16.0},
                        {"time": 0.5, "x": 24.0, "y": 0.0},
                        {"time": 1.0, "x": -24.0, "y": 0.0},
                    ]
                },
            }
        },
        "haul_rope": {
            "bones": {
                "pelvis": {
                    "translate": [
                        {"time": 0.0, "x": 0.0, "y": 0.0},
                        {"time": 0.4, "x": 4.0, "y": 3.0},
                        {"time": 1.0, "x": -8.0, "y": -7.0},
                        {"time": 1.5, "x": -4.0, "y": -3.0},
                    ]
                },
                "torso": {
                    "rotate": [
                        {"time": 0.0, "angle": -4.0},
                        {"time": 0.4, "angle": -14.0},
                        {"time": 1.0, "angle": 12.0},
                        {"time": 1.5, "angle": 4.0},
                    ]
                },
                "ik_hand_r_target": {
                    "translate": [
                        {"time": 0.0, "x": 14.0, "y": 34.0},
                        {"time": 0.4, "x": 26.0, "y": 64.0},
                        {"time": 1.0, "x": 8.0, "y": 8.0},
                        {"time": 1.5, "x": 14.0, "y": 24.0},
                    ]
                },
                "ik_hand_l_target": {
                    "translate": [
                        {"time": 0.0, "x": 18.0, "y": 46.0},
                        {"time": 0.4, "x": 30.0, "y": 78.0},
                        {"time": 1.0, "x": 12.0, "y": 22.0},
                        {"time": 1.5, "x": 18.0, "y": 36.0},
                    ]
                },
            }
        },
        "hold_lantern": {
            "bones": {
                "torso": {
                    "rotate": [
                        {"time": 0.0, "angle": -3.0},
                        {"time": 0.8, "angle": -6.0},
                        {"time": 1.6, "angle": -3.0},
                    ]
                },
                "ik_hand_r_target": {
                    "translate": [
                        {"time": 0.0, "x": 32.0, "y": 54.0},
                        {"time": 0.8, "x": 34.0, "y": 60.0},
                        {"time": 1.6, "x": 32.0, "y": 54.0},
                    ]
                },
                "ik_hand_l_target": {
                    "translate": [
                        {"time": 0.0, "x": 20.0, "y": 30.0},
                        {"time": 0.8, "x": 22.0, "y": 34.0},
                        {"time": 1.6, "x": 20.0, "y": 30.0},
                    ]
                },
            }
        },
    }

    return {
        "skeleton": {
            "spine": "3.8.99",
            "x": -64,
            "y": 0,
            "width": 128,
            "height": 228,
            "fps": 24,
            "images": "./",
        },
        "bones": bones,
        "slots": slots,
        "ik": ik,
        "skins": [{"name": "default", "attachments": default_atts}],
        "animations": animations,
    }


def generate_rig_assets() -> dict:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    img, regions = build_original_atlas_image()
    png_path = ASSETS_DIR / "roman_harbor_worker.png"
    atlas_path = ASSETS_DIR / "roman_harbor_worker.atlas"
    skel_path = ASSETS_DIR / "roman_harbor_worker.json"
    manifest_path = ASSETS_DIR / "roman_harbor_worker_manifest.json"
    provenance_path = RIG_DIR / "SOURCE_PROVENANCE.json"

    img.save(png_path, format="PNG", optimize=False)
    atlas_path.write_text(build_atlas_text("roman_harbor_worker.png", img.size, regions), encoding="utf-8")
    skel = build_skeleton_json(regions)
    skel_path.write_text(json.dumps(skel, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "14.7.6",
        "character_id": "roman_harbor_worker",
        "origin": "100% newly authored procedural PIL sprite layers + Spine 3.8 / Rigby2D JSON rig for V14.7.6",
        "demo_assets_copied": False,
        "prior_preview_assets_reused": False,
        "height_units": 210.0,
        "setup_targets": {
            "ik_foot_l_target": {"x": 10.0, "y": 6.0},
            "ik_foot_r_target": {"x": -8.0, "y": 6.0},
            "ik_hand_l_target": {"x": 28.0, "y": 98.0},
            "ik_hand_r_target": {"x": 24.0, "y": 94.0},
        },
        "bone_names": [b["name"] for b in skel["bones"]],
        "slot_names": [s["name"] for s in skel["slots"]],
        "ik_constraints": [c["name"] for c in skel["ik"]],
        "base_animations": sorted(skel["animations"].keys()),
        "files": {
            "texture_png": {
                "path": "integrations/rigby2d/assets/roman_harbor_worker.png",
                "sha256": _sha256(png_path),
                "width": img.size[0],
                "height": img.size[1],
            },
            "atlas": {
                "path": "integrations/rigby2d/assets/roman_harbor_worker.atlas",
                "sha256": _sha256(atlas_path),
            },
            "skeleton_json": {
                "path": "integrations/rigby2d/assets/roman_harbor_worker.json",
                "sha256": _sha256(skel_path),
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    vendor_files = {}
    for sub in sorted(VENDOR_DIR.rglob("*.js")):
        rel = sub.relative_to(RIG_DIR).as_posix()
        vendor_files[rel] = _sha256(sub)

    provenance = {
        "schema_version": "14.7.6",
        "upstream_repository": "https://github.com/jaisurya-dev-art/rigby2d",
        "upstream_branch": "develop",
        "upstream_commit_sha": "130562a94e76a19986aa8b737f998a89c1270bb8",
        "upstream_package_version": "0.5.1",
        "runtime_license": "MIT OR Apache-2.0",
        "license_files": [
            "integrations/rigby2d/LICENSE-MIT",
            "integrations/rigby2d/LICENSE-APACHE",
        ],
        "proprietary_demo_mascots_excluded": ["NILA", "Rigbytron", "examples/*"],
        "original_character_rig_manifest": "integrations/rigby2d/assets/roman_harbor_worker_manifest.json",
        "vendored_runtime_sha256": vendor_files,
        "original_rig_assets_sha256": {
            k: v["sha256"] for k, v in manifest["files"].items()
        },
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = generate_rig_assets()
    print(json.dumps({"status": "OK", "character_id": m["character_id"], "files": m["files"]}, indent=2))
