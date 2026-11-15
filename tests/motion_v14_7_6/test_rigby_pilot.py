"""Real runtime tests for V14.7.6 Phase C — Rigby2D Pilot."""

from __future__ import annotations

from pathlib import Path

from integrations.rigby2d.pilot import (
    MANIFEST_PATH,
    PROVENANCE_PATH,
    build_rigby_vs_canvas_motion_plan,
    compare_rigby_vs_canvas,
    convert_motion_plan_to_rigby_tracks,
    inspect_rigby_runtime_capabilities,
    load_rigby_character_manifest,
    verify_rigby_browser_compositing,
)


def test_rigby_runtime_capabilities_and_fail_closed(tmp_path: Path) -> None:
    caps = inspect_rigby_runtime_capabilities()
    assert caps["status"] == "RUNTIME_VERIFIED", caps
    assert caps["version"] == "0.5.1"
    assert caps["commit_sha"] == "130562a94e76a19986aa8b737f998a89c1270bb8"
    assert caps["demo_assets_copied"] is False
    assert caps["webgl_renderer_exported"] is True
    assert caps["bone_count"] >= 18
    assert caps["slot_count"] == 15
    assert caps["ik_constraint_count"] == 4
    assert caps["emitted_attachments"] == 15
    assert caps["emitted_triangles"] >= 30
    assert MANIFEST_PATH.exists() and PROVENANCE_PATH.exists()

    # Fail-closed check when runtime asset is missing (no mock PASS)
    missing = inspect_rigby_runtime_capabilities(skeleton_path=tmp_path / "nonexistent.json")
    assert missing["status"] == "RIGBY_PILOT_BLOCKED"


def test_convert_motion_plan_to_rigby_tracks_loads_cleanly() -> None:
    plan = build_rigby_vs_canvas_motion_plan()
    manifest = load_rigby_character_manifest()
    compiled = convert_motion_plan_to_rigby_tracks(plan, manifest, fps=24)
    assert compiled["rigby_skeleton_verified"] is True
    assert compiled["track_count"] >= 2
    for anim_entry in compiled["tracks"].values():
        assert anim_entry["animation_name"] in compiled["loaded_animation_names"]
        bones = anim_entry["spine_animation"]["bones"]
        assert len(bones["ik_foot_l_target"]["translate"]) >= 20
        assert len(bones["ik_hand_r_target"]["translate"]) >= 20


def test_rigby_browser_webgl_to_canvas_compositing_and_determinism() -> None:
    res = verify_rigby_browser_compositing()
    assert res["status"] == "PASS", res
    assert res["deterministic_order_invariant"] is True
    assert res["distinct_animated_frames"] is True
    assert res["alpha_and_upright_valid"] is True


def test_compare_rigby_vs_canvas_8s_render(tmp_path: Path) -> None:
    cmp_res = compare_rigby_vs_canvas(tmp_path / "rigby_cmp", scale=0.25)
    assert cmp_res["pilot_status"] == "PILOT_WORKING", cmp_res
    assert cmp_res["distinct_backend_outputs"] is True
    assert cmp_res["rigby2d"]["frames"] == 192
    assert cmp_res["canvas"]["frames"] == 192
    assert cmp_res["rigby2d"]["sha256"] != cmp_res["canvas"]["sha256"]
