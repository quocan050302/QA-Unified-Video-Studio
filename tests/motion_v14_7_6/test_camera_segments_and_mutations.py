"""Phase E & Section 10 tests: script-driven multi-angle camera segments, internal cut QA, and 10 mandatory mutations."""

from __future__ import annotations

from pathlib import Path

from tools.action_capabilities import get_pack_capabilities
from tools.cinematic_camera import (
    CameraSegment,
    compile_camera_segments_to_renderer,
    plan_multi_angle_action,
    validate_camera_segments,
)
from tools.motion_performance import (
    build_shared_motion_timeline,
    extract_semantic_motion_intents,
    plan_actor_motion_phases,
)
from tools.temporal_visual_qa import (
    audit_internal_camera_cuts,
    run_v14_7_6_mandatory_mutations,
)


def test_plan_and_validate_multi_angle_camera_segments() -> None:
    events = [
        {"id": "S01", "start": 0.0, "end": 3.0, "dur": 3.0, "line": "The harbor light went dark."},
        {"id": "S02", "start": 3.0, "end": 5.2, "dur": 2.2, "line": "A merchant ship rolled toward the rocks."},
        {"id": "S03", "start": 5.2, "end": 8.8, "dur": 3.6, "line": "Aelia grabbed the last burning lantern."},
        {
            "id": "S06",
            "start": 8.8,
            "end": 13.3,
            "dur": 4.5,
            "line": "Together, Aelia steadies the lantern and Felix hauls the rope.",
        },
    ]
    cast = {
        "aelia": {"preset": "peasant", "role": "lamp_keeper", "x": 0.35, "y": 0.80, "facing": 1},
        "felix": {"preset": "artisan", "role": "rope_worker", "x": 0.58, "y": 0.80, "facing": 1},
    }
    ws = {
        "actors": {"aelia": {"x": 0.35, "y": 0.80}, "felix": {"x": 0.58, "y": 0.80}},
        "objects": {"lantern": {"x": 0.42, "y": 0.68}, "rope": {"x": 0.64, "y": 0.66}},
    }
    intents = extract_semantic_motion_intents(
        "\n".join(e["line"] for e in events),
        script_events=events,
        cast_bible=cast,
        world_state=ws,
        pack="squire",
        genre="harbor",
    )
    tracks = plan_actor_motion_phases(
        intents,
        get_pack_capabilities("squire", "harbor"),
        shot_timing=events,
        cast_bible=cast,
        world_state=ws,
    )
    plan = build_shared_motion_timeline([], tracks, ws, intents=intents, pack="squire", genre="harbor")

    segs_s01 = plan_multi_angle_action(events[0], plan, ws)
    segs_s02 = plan_multi_angle_action(events[1], plan, ws)
    segs_s03 = plan_multi_angle_action(events[2], plan, ws)
    segs_s06 = plan_multi_angle_action(events[3], plan, ws)

    assert len(segs_s01) == 2  # close flame -> wide dark harbor
    assert len(segs_s02) == 1  # <3.0s simple beat -> 1 angle, not forced
    assert len(segs_s03) == 2  # medium reaction -> hand/lantern grip insert
    assert len(segs_s06) == 3  # wide cooperative -> close rope grip -> low tower angle

    for ev, segs in zip(events, [segs_s01, segs_s02, segs_s03, segs_s06]):
        ok, errs = validate_camera_segments(segs, ev, plan)
        assert ok is True, errs
        compiled = compile_camera_segments_to_renderer(segs)
        assert len(compiled["cameraSegments"]) == len(segs)
        assert "cameraRig" in compiled and "move" in compiled


def test_validate_camera_segments_rejects_fake_crop_reverse_and_axis_break() -> None:
    shot = {"id": "S03", "start": 0.0, "end": 3.5, "dur": 3.5}
    bad_segs = [
        CameraSegment(
            segment_id="S03_seg01",
            shot_id="S03",
            segment_index=0,
            local_start=0.0,
            local_end=1.6,
            scale="medium",
            viewpoint="profile_left",
            projection_mode="continuous_2d_canvas",
            axis="left_to_right",
        ),
        CameraSegment(
            segment_id="S03_seg02",
            shot_id="S03",
            segment_index=1,
            local_start=1.6,
            local_end=3.5,
            scale="close",
            viewpoint="over_shoulder_right",
            projection_mode="crop_zoom",
            axis="right_to_left",
            resets_action_time=True,
        ),
    ]
    ok, errs = validate_camera_segments(bad_segs, shot)
    assert ok is False
    joined = " | ".join(errs)
    assert "crop_zoom" in joined
    assert "180-degree axis" in joined
    assert "resets action time" in joined


def test_zero_cut_samples_fails_closed(tmp_path: Path) -> None:
    proj = tmp_path / "single_shot_no_cuts"
    (proj / "story").mkdir(parents=True)
    (proj / "story" / "shots.json").write_text(
        '{"duration": 2.0, "shots": [{"id": "S01", "start": 0.0, "end": 2.0, "dur": 2.0}]}',
        encoding="utf-8",
    )
    dummy_mp4 = tmp_path / "dummy.mp4"
    dummy_mp4.write_bytes(b"not_empty")
    res = audit_internal_camera_cuts(proj, dummy_mp4)
    assert res["status"] == "FAIL"
    assert res["full_coverage"] is False


def test_all_ten_v14_7_6_mandatory_mutations_killed(tmp_path: Path) -> None:
    rep = run_v14_7_6_mandatory_mutations(work_dir=tmp_path / "mut_work")
    assert rep["baseline_passed"] is True, rep
    assert rep["total_mutations"] == 10
    assert rep["killed_mutations"] == 10, rep
    assert rep["status"] == "PASS"
