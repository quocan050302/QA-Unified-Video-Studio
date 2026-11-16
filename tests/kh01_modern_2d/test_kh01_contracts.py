"""tests/kh01_modern_2d/test_kh01_contracts.py — Unit & Contract Tests for KH-01 Modern Expressive 2D."""

from __future__ import annotations

from pathlib import Path
import pytest

from tools.character_acting import ActorPerformanceBeat, compile_actor_performance_to_rig
from tools.character_design import (
    REQUIRED_EXPRESSIONS,
    REQUIRED_VIEWS,
    build_character_model_sheet,
    derive_character_specs,
    export_character_rig_manifest,
    generate_character_design,
    validate_character_consistency,
)
from tools.cinematic_camera import CameraSegment, link_camera_to_asset_views
from tools.environment_factory import (
    build_environment_assets,
    build_scene_asset_manifest,
    derive_environment_specs,
    validate_environment_continuity,
)
from tools.produce_kh01_original_roman_30s import run_urgent_scroll_wording_and_event_variation_test
from tools.temporal_visual_qa import audit_foot_plant
from tools.motion_performance import ActorMotionTrack, MotionPhase, MotionPlan
from tools.visual_storytelling import build_story_context, infer_niche_from_script, infer_scene_objectives
from tools.visual_style_director import (
    build_shot_art_direction,
    load_style_profile,
    resolve_visual_style,
    validate_style_contract,
)
from tools.visual_style_qa import run_kh01_visual_style_mutations


def test_style_profile_immutable_and_digest_verified() -> None:
    prof = load_style_profile("modern_expressive_2d.v1")
    assert prof.style_id == "modern_expressive_2d.v1"
    assert prof.style_lock_digest == prof.computed_lock_digest
    assert prof.fx_discipline["scene_chromatic_aberration_allowed"] is False
    assert prof.fx_discipline["scene_halftone_overlay_allowed"] is False
    assert prof.reference_availability == "STYLE_REFERENCE_UNAVAILABLE"


def test_legacy_visual_storytelling_defaults_preserved_and_niche_opt_in() -> None:
    shots = [{"id": "S01", "start": 0.0, "end": 3.0, "dur": 3.0, "line": "Soldiers hold the line."}]
    legacy_ctx = build_story_context(shots)
    assert legacy_ctx.genre == "roman"
    assert legacy_ctx.setting["environment"] == "field"
    assert legacy_ctx.niche is None
    assert "tactics" in legacy_ctx.intended_viewer_takeaway.lower()

    sci_shots = [{"id": "S01", "start": 0.0, "end": 3.0, "dur": 3.0, "line": "Inside the cleanroom lab, Maya tests the optical spectrometer."}]
    inferred = infer_niche_from_script(sci_shots[0]["line"])
    assert inferred == "modern_science"
    sci_ctx = build_story_context(sci_shots, genre="modern_science", niche=inferred, style_id="modern_expressive_2d.v1")
    assert sci_ctx.niche == "modern_science"
    assert all("scutum" not in f.lower() and "manipular" not in f.lower() for f in sci_ctx.historical_facts)


def test_multi_niche_character_and_environment_factories_produce_distinct_designs(tmp_path: Path) -> None:
    niches = ["roman_forum", "modern_science", "everyday_business", "holdout_astronomy_museum"]
    outfits = set()
    envs = set()
    ratios = set()
    for n in niches:
        style = resolve_visual_style(f"Test script for {n}", niche=n)
        specs = derive_character_specs(
            [{"actor_id": f"lead_{n}", "name": f"Lead {n}"}, {"actor_id": f"sup_{n}", "name": f"Sup {n}"}],
            niche=n,
            style_instance=style,
        )
        for sp in specs:
            outfits.add(sp["wardrobe"]["outfit_id"])
            ratios.add(sp["proportions"]["head_to_height_ratio"])
        env = derive_environment_specs(f"Scene in {n}", niche=n)
        envs.add(env["environment_id"])

    assert len(envs) == 4
    assert len(outfits) >= 7
    assert len(ratios) >= 3  # Non-homogeneous archetypes across cast!

    # Generate full layered character + model sheet + Rigby2D rig in isolated tmp_path
    roman_style = resolve_visual_style("Lucius runs through the forum.", niche="roman_forum")
    luc_spec = derive_character_specs([{"actor_id": "lucius", "name": "Lucius"}], "roman_forum", style_instance=roman_style)[0]
    asset = generate_character_design(luc_spec, roman_style, seed=42, output_dir=tmp_path / "lucius")
    assert set(asset["views"]) == set(REQUIRED_VIEWS)
    assert set(asset["expressions"]) == set(REQUIRED_EXPRESSIONS)

    sheet = build_character_model_sheet(asset, tmp_path / "sheet.png")
    assert sheet["unique_view_hashes"] == 3
    assert sheet["unique_expression_hashes"] == 6
    assert sheet["editorial_status"] == "HUMAN_REVIEW_PENDING"

    rig = export_character_rig_manifest(asset, tmp_path / "rig")
    assert rig["files"]["texture_png"]["dimensions"] == [1024, 1024]
    assert len(rig["expression_attachments"]) == 6

    env_spec = derive_environment_specs("Roman forum", niche="roman_forum")
    env_asset = build_environment_assets(env_spec, output_dir=tmp_path / "env")
    manifest = build_scene_asset_manifest(tmp_path, [asset], [rig], [env_asset])
    assert manifest["reference_frames_reused"] == 0
    assert manifest["prior_preview_derived_visual_inputs"] == 0


def test_wardrobe_continuity_and_camera_view_linkage_contracts() -> None:
    style = resolve_visual_style("Lucius runs.", niche="roman_forum")
    spec = derive_character_specs([{"actor_id": "lucius", "name": "Lucius"}], "roman_forum", style_instance=style)[0]

    bad_shots = [
        {"id": "S01", "args": {"people": [{"id": "lucius", "outfitId": spec["wardrobe"]["outfit_id"]}]}},
        {"id": "S02", "args": {"people": [{"id": "lucius", "outfitId": "unexplained_space_suit"}]}},
    ]
    res_bad = validate_character_consistency(spec, bad_shots)
    assert res_bad["valid"] is False

    # Fake reverse angle via crop_zoom of front portrait must be rejected by link_camera_to_asset_views
    fake_reverse_seg = CameraSegment(
        segment_id="S01_seg01",
        shot_id="S01",
        segment_index=0,
        local_start=0.0,
        local_end=2.0,
        global_start=0.0,
        global_end=2.0,
        scale="medium",
        viewpoint="over_shoulder_left",
        projection_mode="crop_zoom",
        focus_actor_ids=["lucius"],
        adds_information_reason="fake_reverse_crop_test",
    )
    link_bad = link_camera_to_asset_views([fake_reverse_seg], {"lucius": {"views": list(REQUIRED_VIEWS), "has_hand_insert": True}})
    assert link_bad["valid"] is False
    assert any("crop_zoom" in e for e in link_bad["errors"])


def test_fail_closed_foot_plant_and_unverified_pixel_confidence() -> None:
    # Sliding root during planted stance MUST fail audit_foot_plant AND missing MP4 must mark pixel_qa_status NOT_VERIFIED
    bad_phase = MotionPhase(
        phase_name="EXERT",
        start_sec=0.0,
        end_sec=2.0,
        actor_ids=["a1"],
        motion_type="BRACE_OBJECT",
        world_start=(0.30, 0.84),
        world_end=(0.55, 0.84),
        foot_planted_left=True,
        foot_planted_right=True,
    )
    tr = ActorMotionTrack(
        track_id="S01_a1",
        shot_id="S01",
        actor_id="a1",
        start_sec=0.0,
        end_sec=2.0,
        world_start=(0.30, 0.84),
        world_end=(0.55, 0.84),
        phases=[bad_phase],
    )
    mp = MotionPlan(project_id="test_fail_closed", tracks=[tr])
    rep = audit_foot_plant(mp, mp4_path=None)
    assert rep["status"] == "FAIL"
    assert rep["pixel_qa_status"] == "NOT_VERIFIED"

    # Good stationary planted track WITHOUT mp4 must report pixel_qa_status == NOT_VERIFIED and FAIL if require_pixel_verification=True
    good_phase = bad_phase.model_copy(update={"world_end": (0.30, 0.84)})
    good_mp = MotionPlan(project_id="test_pix_req", tracks=[tr.model_copy(update={"world_end": (0.30, 0.84), "phases": [good_phase]})])
    rep_strict = audit_foot_plant(good_mp, mp4_path=None, require_pixel_verification=True)
    assert rep_strict["pixel_qa_status"] == "NOT_VERIFIED"
    assert rep_strict["status"] == "FAIL"


def test_character_acting_additive_style_binding_preserves_legacy_keys() -> None:
    style = resolve_visual_style("Lucius reacts in shock.", niche="roman_forum")
    beat = ActorPerformanceBeat(
        shot_id="S01",
        actor_id="lucius",
        action="REACT",
        posture="guard_ready",
        arm_gesture="reach",
        face_expression="shock",
    )
    legacy_out = compile_actor_performance_to_rig(beat, pack="squire")
    styled_out = compile_actor_performance_to_rig(beat, pack="squire", style_instance=style)
    for k, v in legacy_out.items():
        assert styled_out[k] == v
    assert styled_out["styleAssetBinding"]["expression_id"] == "wide_shock"


def test_urgent_scroll_script_and_event_responsiveness() -> None:
    res = run_urgent_scroll_wording_and_event_variation_test()
    assert res["status"] == "PASS"
    assert res["script_responsive_verified"] is True


def test_all_seven_kh01_visual_style_mutations_killed() -> None:
    mut = run_kh01_visual_style_mutations()
    assert mut["status"] == "PASS"
    assert mut["killed_mutations"] == mut["total_mutations"] == 7
