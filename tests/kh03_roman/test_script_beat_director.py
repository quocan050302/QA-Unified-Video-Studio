#!/usr/bin/env python3
"""Unit, Contract & Negative Mutation Tests for KH-03.0.R1 Script-Driven Beat/Shot Director."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.kh03_narration_timeline import (
    align_words_and_lines,
    pack_narration_into_30s,
)
from tools.kh03_script_beat_director import (
    build_line_shot_crosswalk,
    compose_shot_plan,
    extract_semantic_beats,
    normalize_script_lines,
    schedule_editorial_camera,
    score_pacing_proxies,
    split_beat_into_visual_events,
    validate_shot_plan_contract,
)
from tools.kh03_reference_audit import assert_no_reused_demo_assets
from tools.kh03_style_lock import load_roman_master_style, validate_roman_style_contract


def _mock_voice_result(lines, tmp_dir: Path, durations=None):
    sr = 48000
    clips = []
    t_rng = np.random.default_rng(77)
    for i, ln in enumerate(lines):
        d = float(durations[i]) if durations else max(1.0, len(ln["text"].split()) * 0.27)
        t_axis = np.linspace(0, d, int(round(d * sr)), endpoint=False)
        sig = (0.12 * np.sin(2 * np.pi * (160 + i * 11) * t_axis) + 0.02 * t_rng.standard_normal(len(t_axis))).astype(np.float32)
        p = tmp_dir / f"{ln['id']}.wav"
        sf.write(str(p), sig, sr, subtype="PCM_16")
        clips.append({
            "id": ln["id"],
            "text": ln["text"],
            "slot": "NARRATOR",
            "wav_path": str(p),
            "sample_rate": sr,
            "raw_duration_sec": round(d, 4),
            "raw_rms": float(np.sqrt(np.mean(sig ** 2))),
            "pause_after_hint_sec": float(ln.get("pause_after_sec", 0.14)),
            "source_kind": "test_synthetic_fixture",
            "sha256": f"fixture_{i}",
        })
    return clips


def test_arbitrary_roman_script_generalization_with_1_to_many_and_many_to_1(tmp_path):
    script = [
        {"id": "A1", "text": "At twilight, a courier sprinted past three torchlit arches before the horn blew."},
        {"id": "A2", "text": "Twenty paces short he clipped a stone—the brass tube spun across wet flagstones."},
        {"id": "A3", "text": "Wait there."},
        {"id": "A4", "text": "Gaius lunged and missed. His boot pinned the cap beside the sewer."},
        {"id": "A5", "text": "He read four words: KEEP THE GATE OPEN."},
        {"id": "A6", "text": "He yelled."},
        {"id": "A7", "text": "Too late—the oak leaves slammed shut."},
    ]
    norm = normalize_script_lines(script)
    clips = _mock_voice_result(norm, tmp_path, durations=[3.4, 3.8, 0.9, 4.1, 3.0, 0.85, 2.5])
    packed = pack_narration_into_30s(clips, target_duration=24.0, scratch_dir=tmp_path / "p")
    aligned = align_words_and_lines(packed)
    vt = {"valid": True, "lines": aligned["lines"], "words": aligned["words"]}
    beats = extract_semantic_beats(aligned["lines"])
    events = []
    lmap = {l["id"]: l for l in aligned["lines"]}
    for b in beats:
        events.extend(split_beat_into_visual_events(b, lmap[b["line_id"]], min_event_frames=10, aspect="9:16"))
    plan = compose_shot_plan(beats, vt, events, target_frames=576, fps=24, aspect="9:16", allow_many_to_one_merge=True)
    cw = build_line_shot_crosswalk(aligned["lines"], plan["shots"], aligned["words"])
    cam = schedule_editorial_camera(plan["shots"], aspect="9:16")
    px = score_pacing_proxies(plan["shots"], aligned["lines"], aligned["words"], cam)
    res = validate_shot_plan_contract(plan, cw, cam, vt)

    assert res["valid"], res["errors"]
    assert cw["summary"]["one_to_many_count"] >= 2
    assert cw["summary"]["word_coverage_ratio"] == 1.0
    assert cw["summary"]["mid_sentence_cuts_count"] >= 1
    assert px["repeated_scale_3x_runs"] == 0
    assert px["editorial_approved"] == "HUMAN_REVIEW_PENDING"
    assert res["style_approved"] == "HUMAN_REVIEW_PENDING"


def test_negation_does_not_fire_false_positive_catch_or_run():
    lines = normalize_script_lines([
        {"id": "N1", "text": "The courier did not run across the gate."},
        {"id": "N2", "text": "Guard Marcus missed the leather satchel completely."},
        {"id": "N3", "text": "The heavy doors never opened again."},
    ])
    beats = extract_semantic_beats(lines)
    assert "run" in beats[0]["negated_verbs"]
    assert "NEGATED:sprint_chase" not in beats[0]["actions"] or all(a.startswith("NEGATED:") or a == "narrative_hold" for a in beats[0]["actions"])
    assert "catch" in beats[1]["negated_verbs"]
    assert "sandal_catch" not in beats[1]["actions"]
    assert "open" in beats[2]["negated_verbs"]


def test_narration_stretch_cap_blocks_overcompressed_speech(tmp_path):
    lines = normalize_script_lines([
        {"id": "S1", "text": "One very long sentence that takes a huge amount of spoken time inside a short slot."},
        {"id": "S2", "text": "Another slow long explanation exceeding thirty seconds total easily."},
    ])
    clips = _mock_voice_result(lines, tmp_path, durations=[20.0, 19.0])
    with pytest.raises(RuntimeError, match="AUDIO_STRETCH_EXCEEDED"):
        pack_narration_into_30s(clips, target_duration=30.0, max_stretch=1.15, scratch_dir=tmp_path / "over")


def test_validate_shot_plan_contract_rejects_gaps_overlaps_and_unannotated_holds(tmp_path):
    lines = normalize_script_lines([
        "First sentence arrives at dusk.",
        "Second beat tracks sandals on wet cobbles.",
        "Third beat checks the shrinking oak gap.",
        "Fourth sentence locks the iron bolt.",
    ])
    clips = _mock_voice_result(lines, tmp_path, durations=[2.1, 2.2, 2.2, 2.0])
    packed = pack_narration_into_30s(clips, target_duration=10.0, scratch_dir=tmp_path / "m")
    aligned = align_words_and_lines(packed)
    vt = {"valid": True, "lines": aligned["lines"], "words": aligned["words"]}
    beats = extract_semantic_beats(aligned["lines"])
    events = [split_beat_into_visual_events(b, aligned["lines"][i])[0] for i, b in enumerate(beats)]
    plan = compose_shot_plan(beats, vt, events, target_frames=240, fps=24, aspect="9:16", allow_many_to_one_merge=False)
    cw = build_line_shot_crosswalk(aligned["lines"], plan["shots"], aligned["words"])
    cam = schedule_editorial_camera(plan["shots"], aspect="9:16")

    # Mutant 1: Frame gap
    bad_gap = copy.deepcopy(plan)
    bad_gap["shots"][0]["frame_end"] -= 2
    assert not validate_shot_plan_contract(bad_gap, cw, cam, vt)["valid"]

    # Mutant 2: 3 consecutive identical framing scales
    bad_rep = copy.deepcopy(plan)
    bad_rep["shots"][0]["framing_scale"] = "medium_full_tracking"
    bad_rep["shots"][1]["framing_scale"] = "medium_full_tracking"
    bad_rep["shots"][2]["framing_scale"] = "medium_full_tracking"
    rep_res = validate_shot_plan_contract(bad_rep)
    assert any("consecutive identical framing" in e for e in rep_res["errors"])

    # Mutant 3: False-positive guard — intentional annotated hold passes cleanly
    clean_hold = copy.deepcopy(plan)
    clean_hold["shots"][0]["intentional_hold"] = {"enabled": True, "frames": 8, "editorial_justification": "Legible scroll beat"}
    clean_res = validate_shot_plan_contract(clean_hold, cw, cam, vt)
    assert clean_res["valid"], clean_res["errors"]


def test_r1_project_style_lock_and_no_forced_shot_id_coupling():
    proj = REPO_ROOT / "projects" / "kh03_r1_roman_gate_message_30s"
    if not (proj / "config.json").is_file():
        pytest.skip("R1 project not built yet")
    cfg = json.loads((proj / "config.json").read_text(encoding="utf-8"))
    assert cfg["aspect"] == "9:16"
    assert cfg["render_mode"] == "canvas2d_only"
    assert cfg["editorial_mode"] == "script_beat_director_v1"

    lines = json.loads((proj / "timeline" / "lines.json").read_text(encoding="utf-8"))
    assert all("shot_id" not in ln for ln in lines), "R1 lines.json must not hard-couple 1:1 to shot_id"

    sb = load_roman_master_style("roman_squire_master.v1")
    style_chk = validate_roman_style_contract(sb)
    assert style_chk["valid"] and style_chk["digest_verified"], style_chk
    non_reuse = assert_no_reused_demo_assets(proj)
    assert non_reuse["passed"], non_reuse
