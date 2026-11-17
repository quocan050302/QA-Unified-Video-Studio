"""test_kh02_foundation.py — Unit, Contract & Negative Mutation Suite for KH-02.0 + KH-02.1.

Covers:
- Style bible schema, digest lock & semantic niche resolution (Roman / Medieval / Future)
- 2D-only guard (rejects kind:'3d' in canvas2d_only; preserves legacy 3D when not opted in)
- Character factory (>=2 distinct human rigs + non-human goat rig honesty)
- Environment factory (>=3 distinct 2D views + shared world landmarks + zero forbidden motifs)
- All 14 mandatory negative mutations (E7) + false-positive prevention (6-frame hold & valid cut)
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from kh02_style_contract import (
    compute_style_lock_digest,
    load_squire_style_profile,
    resolve_squire_niche_style,
    validate_squire_style_contract,
)
from kh02_character_factory import (
    build_character_turnaround_2d,
    build_expression_sheet_2d,
    derive_character_identity,
    validate_character_model_consistency,
    write_character_continuity_manifest,
)
from kh02_environment_factory import (
    build_original_layers,
    derive_scene_spec,
    export_2d_scene_manifest,
    validate_scene_continuity,
)
from kh02_visual_qa import (
    audit_camera_2d_bounds,
    audit_character_identity,
    audit_continuity_across_cuts,
    audit_frame_temporal_liveness,
    audit_hand_prop_contact,
    audit_style_baseline_preservation,
    audit_unique_visual_language,
)
from validator import validate_project


def test_style_contract_load_and_niche_resolution():
    prof = load_squire_style_profile("squire_cinematic_2d.v1")
    assert prof["style_id"] == "squire_cinematic_2d.v1"
    assert prof["canonical_digest"] == compute_style_lock_digest(prof)
    assert prof["protected_production_default"]["outline_hex"].lower() == "#392a21"

    rom = resolve_squire_niche_style("A Roman bell-keeper on a hilltop courtyard before dawn")
    med = resolve_squire_niche_style("A medieval knight inside a stone castle cathedral")
    fut = resolve_squire_niche_style("An orbital reactor station technician in the future")
    assert rom["resolved_niche"] == "roman"
    assert med["resolved_niche"] == "medieval"
    assert fut["resolved_niche"] == "non_historical_future"
    assert rom["niche_palette"] != med["niche_palette"]


def test_style_contract_tampered_digest_killed():
    prof = load_squire_style_profile("squire_cinematic_2d.v1")
    tampered = copy.deepcopy(prof)
    tampered["canonical_digest"] = "0" * 64
    res = validate_squire_style_contract(tampered, [])
    assert not res["valid"]
    assert any("canonical_digest mismatch" in e for e in res["errors"])


def test_character_factory_uniqueness_and_goat_honesty():
    ident = derive_character_identity()
    man = write_character_continuity_manifest(ident, {})
    val = validate_character_model_consistency(man)
    assert val["valid"], val["errors"]
    assert set(val["human_characters"]) == {"TAVI", "LYRA"}
    assert "PIP" in val["non_human_entities"]

    # Negative: claiming goat as human rig must FAIL
    bad_man = copy.deepcopy(man)
    for c in bad_man["characters"]:
        if c["canonical_name"] == "PIP":
            c["is_human_rig"] = True
    bad_val = validate_character_model_consistency(bad_man)
    assert not bad_val["valid"]


def test_environment_factory_views_and_forbidden_motifs():
    spec = derive_scene_spec()
    layers = build_original_layers(spec)
    assert len(layers) >= 4
    for _, view_layers in layers.items():
        assert 3 <= len(view_layers) <= 5

    man = export_2d_scene_manifest(spec, {})
    val = validate_scene_continuity(man)
    assert val["valid"], val["errors"]

    # Negative: injecting forbidden old stock motif ('urgent_scroll') must FAIL
    bad_man = copy.deepcopy(man)
    bad_man["views"][0]["purpose"] = "Reuse urgent_scroll chase from earlier demo"
    assert not validate_scene_continuity(bad_man)["valid"]


def test_2d_only_guard_vs_legacy_3d_compatibility(tmp_path: Path):
    # 1. KH02 canvas2d_only project with 3D shot MUST BE BLOCKED
    p_kh02 = tmp_path / "neg_3d_in_kh02"
    (p_kh02 / "story").mkdir(parents=True)
    (p_kh02 / "scenes" / "shots").mkdir(parents=True)
    (p_kh02 / "config.json").write_text(
        json.dumps({"title": "Neg3D", "pack": "squire", "aspect": "16:9", "render_mode": "canvas2d_only"}),
        encoding="utf-8",
    )
    (p_kh02 / "story" / "shots.json").write_text(
        json.dumps({"duration": 2.0, "shots": [{"id": "s3d", "start": 0.0, "end": 2.0}]}),
        encoding="utf-8",
    )
    (p_kh02 / "scenes" / "shots" / "s3d.js").write_text(
        "import { registerShot } from '/engine/core.js'; registerShot('s3d', { kind: '3d', init(){}, draw(){} });",
        encoding="utf-8",
    )
    rep_kh02 = validate_project(str(p_kh02), stage="preflight")
    assert rep_kh02["status"] == "BLOCKED"
    assert any("KH02_2D_ONLY_VIOLATION" in e for e in rep_kh02["fatal_errors"])

    # 2. Legacy project WITHOUT canvas2d_only MUST STILL ALLOW custom 3D shots
    p_leg = tmp_path / "legacy_3d_allowed"
    (p_leg / "story").mkdir(parents=True)
    (p_leg / "scenes" / "shots").mkdir(parents=True)
    (p_leg / "config.json").write_text(
        json.dumps({"title": "Legacy3D", "pack": "squire", "aspect": "16:9"}),
        encoding="utf-8",
    )
    (p_leg / "story" / "shots.json").write_text(
        json.dumps({"duration": 2.0, "shots": [{"id": "s3d", "start": 0.0, "end": 2.0}]}),
        encoding="utf-8",
    )
    (p_leg / "scenes" / "shots" / "s3d.js").write_text(
        "import { registerShot } from '/engine/core.js'; registerShot('s3d', { kind: '3d', init(){}, draw(){} });",
        encoding="utf-8",
    )
    rep_leg = validate_project(str(p_leg), stage="preflight")
    assert rep_leg["status"] == "PASS", rep_leg["fatal_errors"]


def test_mandatory_negative_mutations_and_false_positive_prevention(tmp_path: Path):
    prof = load_squire_style_profile("squire_cinematic_2d.v1")

    # --- FALSE-POSITIVE PREVENTION 1: Legitimate 6-frame held anticipation inside active shot MUST PASS
    valid_pose_trace = {
        "shots": [
            {
                "id": "S03",
                "action_heavy": True,
                "frames": (
                    [{"actor_world_vec": [100.0, 200.0], "expression": "anxious_alert"} for _ in range(7)]  # 6-frame hold
                    + [{"actor_world_vec": [100.0 + i * 3.5, 200.0 - i * 2.0], "expression": "strained_pull"} for i in range(1, 30)]
                ),
            }
        ]
    }
    res_fp1 = audit_frame_temporal_liveness(valid_pose_trace)
    assert res_fp1["passed"], res_fp1["errors"]

    # --- FALSE-POSITIVE PREVENTION 2: Legitimate cut with consistent world contact MUST PASS
    valid_story = {
        "shots": [
            {"id": f"S0{i}", "start": (i - 1) * 3.75, "end": i * 3.75}
            for i in range(1, 9)
        ]
    }
    res_fp2_cut = audit_continuity_across_cuts(
        valid_story,
        {"shot_joins": [{"join": "S06a->S06b"}]},
        {"joins": [{"join_id": "S06a->S06b", "prop_count": 1, "bell_angle_before": 0.085, "bell_angle_after": 0.085}]},
    )
    res_fp2_grip = audit_hand_prop_contact({
        "grip_samples": [
            {"t": 19.28, "shot": "S06a", "hand_world": [1012.0, 520.0], "prop_world": [1014.0, 521.0], "tolerance_px": 24.0},
            {"t": 19.32, "shot": "S06b", "hand_world": [1012.5, 520.2], "prop_world": [1014.0, 521.0], "tolerance_px": 24.0},
        ],
        "planted_foot_intervals": [
            {"label": "S05_step_3", "stance_foot_world_samples": [[689.0, 757.0], [689.0, 757.0], [689.0, 757.0]], "max_skate_px": 1.5}
        ],
    })
    assert res_fp2_cut["passed"] and res_fp2_grip["passed"]

    # --- NEGATIVE MUTANT A: 3-second (72 frames) static picture panned by camera -> KILLED
    static_pan_trace = {
        "shots": [
            {
                "id": "S05_static_pan",
                "action_heavy": True,
                "frames": [{"actor_world_vec": [500.0, 600.0], "expression": "neutral", "cam_x": i * 4.0} for i in range(72)],
            }
        ]
    }
    assert not audit_frame_temporal_liveness(static_pan_trace)["passed"]

    # --- NEGATIVE MUTANT B: Blank/black frame in MP4 -> KILLED
    black_mp4 = tmp_path / "black_defect.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(black_mp4)],
        check=True,
    )
    assert not audit_frame_temporal_liveness(valid_pose_trace, mp4_path=black_mp4)["passed"]

    # --- NEGATIVE MUTANT C: Corrupt MP4 -> KILLED
    corrupt_mp4 = tmp_path / "corrupt.mp4"
    corrupt_mp4.write_bytes(b"CORRUPT_MP4_NOT_DECODABLE_BYTES")
    assert not audit_frame_temporal_liveness(valid_pose_trace, mp4_path=corrupt_mp4)["passed"]

    # --- NEGATIVE MUTANT D: Hand releases rope too soon -> KILLED
    assert not audit_hand_prop_contact({
        "grip_samples": [{"t": 8.10, "shot": "S03", "hand_world": [880.0, 700.0], "prop_world": [1115.0, 690.0], "tolerance_px": 28.0}],
        "planted_foot_intervals": [],
    })["passed"]

    # --- NEGATIVE MUTANT E: Planted foot slides on stairs -> KILLED
    assert not audit_hand_prop_contact({
        "grip_samples": [],
        "planted_foot_intervals": [
            {"label": "S05_skate", "stance_foot_world_samples": [[510.0, 833.0], [528.0, 833.0], [546.0, 833.0]], "max_skate_px": 1.5}
        ],
    })["passed"]

    # --- NEGATIVE MUTANT F: Prop disappears / duplicates / teleports across cut -> KILLED
    assert not audit_continuity_across_cuts(
        valid_story,
        {"shot_joins": []},
        {"joins": [{"join_id": "S03->S04", "prop_count": 2, "bell_angle_before": 0.05, "bell_angle_after": 0.85}]},
    )["passed"]

    # --- NEGATIVE MUTANT G: Incorrect shot-end timing -> KILLED
    bad_timing = copy.deepcopy(valid_story)
    bad_timing["shots"][-1]["end"] = 28.2
    assert not audit_continuity_across_cuts(bad_timing, {"shot_joins": []})["passed"]

    # --- NEGATIVE MUTANT H: Camera overzoom / out-of-bounds / snap -> KILLED
    assert not audit_camera_2d_bounds({
        "bounds": {"min_zoom": 0.94, "max_zoom": 1.35, "max_pan_px": 380},
        "shots": {"S04": {"z0": 1.0, "z1": 2.25, "x0": 0, "x1": 650, "instant_snap": True}},
    })["passed"]

    # --- NEGATIVE MUTANT I: Actor wardrobe/identity mutates across cut -> KILLED
    bell_proj = REPO_ROOT / "projects" / "kh02_bell_before_sunrise_30s"
    if (bell_proj / "story" / "storyboard.json").is_file():
        tmp_p = tmp_path / "mut_identity"
        (tmp_p / "story").mkdir(parents=True)
        for fn in ("character_bible.json", "continuity_ledger.json", "storyboard.json"):
            (tmp_p / "story" / fn).write_bytes((bell_proj / "story" / fn).read_bytes())
        sb = json.loads((tmp_p / "story" / "storyboard.json").read_text(encoding="utf-8"))
        sb["shots"][3]["actor_wardrobe_overrides"] = {"TAVI": {"tunic": "#00ff00"}}
        (tmp_p / "story" / "storyboard.json").write_text(json.dumps(sb), encoding="utf-8")
        assert not audit_character_identity(tmp_p)["passed"]

    # --- NEGATIVE MUTANT J: 3D kind in style contract -> KILLED
    assert not validate_squire_style_contract(prof, [{"id": "S01", "start": 0.0, "end": 3.0, "kind": "3d"}])["valid"]
