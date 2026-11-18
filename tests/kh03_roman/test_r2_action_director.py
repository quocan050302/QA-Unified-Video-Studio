"""Unit & adversarial regression tests for KH-03.0.R2 Generalized Action Director & Perceptual Shot QA."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pytest
from PIL import Image, ImageDraw

from tools.kh03_action_registry import (
    REGISTRY_VERSION,
    UnsupportedRomanActionError,
    action_registry_digest,
    build_roman_action_registry,
    resolve_roman_action,
    validate_action_bindings,
)
from tools.kh03_perceptual_qa import (
    audit_cinematic_camera,
    audit_motion_continuity,
    build_perceptual_review_packet,
    compute_visual_signatures,
    measure_shot_novelty,
    sample_rendered_frames,
)
from tools.kh03_script_beat_director import (
    V2_EDITORIAL_MODE,
    compile_v2_editorial_plan,
    parse_js_renderer_handlers,
)
from tools.kh03_r2_project_builder import (
    FORUM_COURTYARD_HOLDOUT_SCRIPT,
    RIVER_HARBOR_HOLDOUT_SCRIPT,
    THE_CART_THAT_WOULD_NOT_STOP_SCRIPT,
)


def _encode_png_sequence_to_mp4(frames: List[Image.Image], out_mp4: Path, fps: int = 24) -> None:
    tmp_dir = out_mp4.parent / f"frames_{out_mp4.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for idx, im in enumerate(frames):
        im.save(tmp_dir / f"{idx:04d}.png")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
            "-i", str(tmp_dir / "%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
            str(out_mp4),
        ],
        check=True,
    )


def test_registry_29_actions_and_js_parity():
    reg = build_roman_action_registry()
    js_handlers = parse_js_renderer_handlers()
    assert len(reg) == 29
    assert len(js_handlers) >= 29
    for aid, spec in reg.items():
        assert spec.renderer_action_id in js_handlers, f"Missing JS handler for {aid}"
    d1 = action_registry_digest(reg)
    d2 = action_registry_digest(build_roman_action_registry())
    assert d1 == d2
    assert REGISTRY_VERSION == "kh03.r2.action_registry.v1"


@pytest.mark.parametrize(
    "phrase,world_state,expected_code",
    [
        ("A white horse galloped over the cobbles.", {}, "UNSUPPORTED_ACTION"),
        ("A bronze dragon flew past the flying aqueduct.", {}, "UNSUPPORTED_ACTION"),
        ("A catapult launched a soldier across the river.", {}, "UNSUPPORTED_ACTION"),
        ("The senator never grabbed the spear on the bench.", {}, "NEGATED_ACTION"),
        ("Apprentice Titus did not run toward the gate.", {}, "NEGATED_ACTION"),
        ("He pushed him near the marble steps.", {}, "AMBIGUOUS_ACTION"),
        ("The heavy city gate reopened slowly.", {"gate_closed": True}, "STATE_CONFLICT"),
        ("Centurion Varro kept walking with a loaf.", {"loaf_on_helmet": False}, "STATE_CONFLICT"),
    ],
)
def test_fail_closed_action_resolution(phrase: str, world_state: Dict[str, Any], expected_code: str):
    entities = [
        {"actor_id": "apprentice_titus", "archetype": "rookie_hastatus"},
        {"actor_id": "senator_cassius", "archetype": "instructor_princeps"},
        {"actor_id": "centurion_varro", "archetype": "centurion_crest"},
    ]
    inv = {
        "props": ["market_cart", "brake_peg", "hemp_rope", "stone_bollard", "bakery_oven", "roman_loaf", "city_gate"],
        "locations": ["roman_market_hill", "city_gate_approach"],
        "default_location": "roman_market_hill",
    }
    with pytest.raises(UnsupportedRomanActionError) as exc_info:
        resolve_roman_action(
            {"beat_id": "BT01", "line_id": "L01", "source_text": phrase},
            entities,
            inv,
            style_contract={"style_id": "roman_squire_master.v1"},
            world_state=world_state,
        )
    assert exc_info.value.reason_code == expected_code


def test_missing_asset_and_unsafe_override_fail_closed():
    entities = [{"actor_id": "apprentice_titus", "archetype": "rookie_hastatus"}]
    incomplete_inv = {"props": ["market_cart"], "locations": ["roman_market_hill"], "default_location": "roman_market_hill"}
    with pytest.raises(UnsupportedRomanActionError) as exc_info:
        resolve_roman_action(
            {"beat_id": "BT02", "line_id": "L01", "source_text": "One brake peg cracked under the cart."},
            entities,
            incomplete_inv,
            style_contract={"style_id": "roman_squire_master.v1"},
        )
    assert exc_info.value.reason_code == "MISSING_ASSET"
    assert "brake_peg" in exc_info.value.missing_props

    with pytest.raises(UnsupportedRomanActionError) as ov_exc:
        resolve_roman_action(
            {"beat_id": "BT03", "line_id": "L01", "source_text": "Titus waited."},
            entities,
            incomplete_inv,
            style_contract={"style_id": "roman_squire_master.v1"},
            manual_override={"action_id": "actor.nonexistent", "author_reason": ""},
        )
    assert ov_exc.value.reason_code == "UNSAFE_OVERRIDE"


def test_three_corpora_compile_without_forced_shot_count():
    res_a = compile_v2_editorial_plan(THE_CART_THAT_WOULD_NOT_STOP_SCRIPT, total_duration_sec=30.0)
    res_b = compile_v2_editorial_plan(RIVER_HARBOR_HOLDOUT_SCRIPT, total_duration_sec=6.5)
    res_c = compile_v2_editorial_plan(FORUM_COURTYARD_HOLDOUT_SCRIPT, total_duration_sec=7.0)

    for res in (res_a, res_b, res_c):
        assert res["validation"]["valid"], res["validation"]["errors"]
        assert res["shot_plan"]["editorial_mode"] == V2_EDITORIAL_MODE
        assert res["shot_plan"]["render_mode"] == "canvas2d_only"
        assert res["shot_plan"]["style_profile"] == "roman_squire_master.v1"

    assert res_b["validation"]["shots_count"] in (3, 4, 5)
    assert res_c["validation"]["shots_count"] in (4, 5, 6)
    assert res_a["validation"]["shots_count"] not in (res_b["validation"]["shots_count"], res_c["validation"]["shots_count"])
    assert res_a["validation"]["shots_count"] != 15 or res_b["validation"]["shots_count"] == 4
    assert res_a["shot_to_line_map"]["summary"]["one_to_many_count"] >= 2
    assert res_a["shot_to_line_map"]["summary"]["many_to_one_count"] >= 1


def test_v2_validation_rejects_unregistered_js_handler():
    bad_plan = {
        "editorial_mode": V2_EDITORIAL_MODE,
        "render_mode": "canvas2d_only",
        "style_profile": "roman_squire_master.v1",
        "fps": 24,
        "total_frames": 48,
        "shots": [
            {
                "id": "SH01",
                "action_id": "actor.sprint_chase",
                "renderer_action_id": "fake_unregistered_handler",
                "location_id": "roman_market_hill",
            }
        ],
    }
    res = validate_action_bindings(bad_plan, renderer_registry=parse_js_renderer_handlers())
    assert not res["valid"]
    assert res["errors"][0]["error_code"] == "UNSUPPORTED_ACTION"


def test_perceptual_qa_catches_zoom_spam_duplicates_and_subtitle_only_motion(tmp_path: Path):
    w, h, fps = 360, 640, 24

    # 1. Negative control: frozen character card under pure 1.0->1.15 camera zoom + flashing caption bottom band
    frames_zoom: List[Image.Image] = []
    base = Image.new("RGB", (w, h), (160, 130, 95))
    dr = ImageDraw.Draw(base)
    dr.rectangle([120, 140, 240, 340], fill=(201, 71, 58), outline=(57, 42, 33), width=4)
    dr.ellipse([135, 95, 225, 185], fill=(244, 237, 225), outline=(57, 42, 33), width=4)

    for i in range(60):  # 2.5s
        z = 1.0 + 0.14 * (i / 59.0)
        cw, ch = int(w / z), int(h / z)
        left, top = (w - cw) // 2, (h - ch) // 2
        zoomed = base.crop((left, top, left + cw, top + ch)).resize((w, h), Image.Resampling.BILINEAR)
        # Flash large subtitles inside subtitle exclusion band (y >= 0.615*h -> y >= 394)
        z_dr = ImageDraw.Draw(zoomed)
        if (i // 4) % 2 == 0:
            z_dr.rectangle([40, int(h * 0.65), w - 40, int(h * 0.78)], fill=(255, 255, 255))
        frames_zoom.append(zoomed)

    mp4_zoom = tmp_path / "neg_zoom_subtitle.mp4"
    _encode_png_sequence_to_mp4(frames_zoom, mp4_zoom, fps=fps)
    plan_zoom = {
        "fps": fps,
        "duration_sec": 2.5,
        "total_frames": 60,
        "shots": [
            {
                "id": "SH01", "start": 0.0, "end": 1.25, "frame_start": 0, "frame_end": 29, "frame_count": 30,
                "action_id": "actor.sprint_chase", "sub_action": "actor_sprint_chase",
                "location_id": "roman_market_hill", "framing_scale": "low_angle_chase",
                "expected_actor_displacement_u": 0.0, "expected_prop_displacement_u": 0.0,
                "camera_intent": {"zoom_delta": 0.14},
            },
            {
                "id": "SH02", "start": 1.25, "end": 2.5, "frame_start": 30, "frame_end": 59, "frame_count": 30,
                "action_id": "prop.helmet_impact_settle", "sub_action": "prop_helmet_impact_settle",
                "location_id": "roman_market_hill", "framing_scale": "low_angle_chase",
                "expected_actor_displacement_u": 0.0, "expected_prop_displacement_u": 0.0,
                "camera_intent": {"zoom_delta": 0.14},
            },
        ],
    }
    pkt_neg = build_perceptual_review_packet(mp4_zoom, plan_zoom, tmp_path / "qa_neg")
    # Either low_motion, suspicious_cuts, or zoom_spam MUST trigger (subtitles alone never pass!)
    assert (
        pkt_neg["status"] == "FAIL"
        or len(pkt_neg["novelty"]["duplicate_nonadjacent_pairs"]) > 0
        or len(pkt_neg["novelty"]["unannotated_low_motion_shots"]) > 0
        or len(pkt_neg["novelty"]["frozen_actor_zoom_spam_shots"]) > 0
        or len(pkt_neg["continuity"]["suspicious_cuts"]) > 0
    )

    # 2. Negative control: duplicate non-adjacent shots SH01 == SH03
    frames_dup: List[Image.Image] = []
    img_a = base.copy()
    img_b = Image.new("RGB", (w, h), (70, 125, 165))
    ImageDraw.Draw(img_b).ellipse([80, 160, 280, 320], fill=(231, 176, 74), outline=(57, 42, 33), width=4)
    for i in range(72):  # 3 x 1.0s
        if i < 24 or i >= 48:
            frames_dup.append(img_a.copy())
        else:
            frames_dup.append(img_b.copy())
    mp4_dup = tmp_path / "neg_dup.mp4"
    _encode_png_sequence_to_mp4(frames_dup, mp4_dup, fps=fps)
    plan_dup = {
        "fps": fps,
        "duration_sec": 3.0,
        "total_frames": 72,
        "shots": [
            {"id": "SH01", "start": 0.0, "end": 1.0, "frame_start": 0, "frame_end": 23, "frame_count": 24, "action_id": "actor.walk_stride", "sub_action": "actor_walk_stride", "framing_scale": "medium_full_tracking"},
            {"id": "SH02", "start": 1.0, "end": 2.0, "frame_start": 24, "frame_end": 47, "frame_count": 24, "action_id": "prop.cart_roll_slope", "sub_action": "prop_cart_roll_slope", "framing_scale": "low_angle_chase"},
            {"id": "SH03", "start": 2.0, "end": 3.0, "frame_start": 48, "frame_end": 71, "frame_count": 24, "action_id": "actor.walk_stride", "sub_action": "actor_walk_stride", "framing_scale": "medium_full_tracking"},
        ],
    }
    pkt_dup = build_perceptual_review_packet(mp4_dup, plan_dup, tmp_path / "qa_dup")
    assert pkt_dup["status"] == "FAIL"
    assert len(pkt_dup["novelty"]["duplicate_nonadjacent_pairs"]) >= 1

    # 3. Positive control: 3 genuinely varied animated shots pass cleanly
    frames_pos: List[Image.Image] = []
    bg_cols = [(160, 185, 215), (215, 165, 115), (95, 145, 115)]
    for i in range(72):
        s_idx = min(2, i // 24)
        im = Image.new("RGB", (w, h), bg_cols[s_idx])
        p_dr = ImageDraw.Draw(im)
        cx = 90 + ((i % 24) * 7) if s_idx == 0 else (260 - (i % 24) * 6 if s_idx == 1 else 180)
        cy = 180 + (0 if s_idx != 2 else (i % 24) * 4)
        p_dr.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], fill=(201, 71, 58), outline=(57, 42, 33), width=4)
        frames_pos.append(im)
    mp4_pos = tmp_path / "pos_varied.mp4"
    _encode_png_sequence_to_mp4(frames_pos, mp4_pos, fps=fps)
    pkt_pos = build_perceptual_review_packet(mp4_pos, plan_dup, tmp_path / "qa_pos")
    assert pkt_pos["status"] == "PASS", json.dumps(pkt_pos, indent=2)
