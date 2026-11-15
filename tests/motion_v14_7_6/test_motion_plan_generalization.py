"""tests/motion_v14_7_6/test_motion_plan_generalization.py — Phase A MotionPlan Generalization & Validator Tests.

Verifies `tools/motion_performance.py`, `tools/action_capabilities.py`,
`tools/narrative_action.py`, and `tools/character_acting.py` across:
1. Three unseen non-military scripts with distinct verbs, props, and cast IDs:
   (a) Citizen slips and steadies a basket
   (b) Merchant lifts a heavy amphora with another person
   (c) Child walks toward lantern then ducks from wind
2. Idle/speech-only vs physical contact phase distinction
3. Truthful `OFFLINE_ONLY` routing label and safe `unsupported_action` fallback (no military bleed)
4. Squire & DEM pack capability resolution and manual-lock preservation
5. All `validate_motion_plan` fail-closed negative cases
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from tools.action_capabilities import get_pack_capabilities, resolve_motion_intent_capabilities
from tools.character_acting import (
    compile_actor_performance_to_rig,
    plan_actor_performance,
    validate_actor_performance,
)
from tools.motion_performance import (
    MotionPlan,
    build_shared_motion_timeline,
    compile_motion_plan_to_legacy_shot_args,
    extract_semantic_motion_intents,
    plan_actor_motion_phases,
    validate_motion_plan,
)
from tools.narrative_action import (
    ActionContext,
    WorldTimeline,
    compile_action_choreography_to_shots,
    parse_action_intents,
    plan_action_beats,
    validate_action_causality,
)


def _run_full_motion_pipeline(
    script_text: str,
    cast_bible: Dict[str, Any],
    world_state: Dict[str, Any],
    *,
    pack: str = "squire",
    genre: str = "civic",
) -> MotionPlan:
    intents = extract_semantic_motion_intents(
        script_text=script_text,
        script_events=None,
        cast_bible=cast_bible,
        world_state=world_state,
        pack=pack,
        genre=genre,
    )
    caps = get_pack_capabilities(pack, genre)
    tracks = plan_actor_motion_phases(
        intents=intents,
        action_capabilities=caps,
        cast_bible=cast_bible,
        world_state=world_state,
    )
    plan = build_shared_motion_timeline(
        scene_objectives=None,
        motion_tracks=tracks,
        world_timeline=world_state,
        intents=intents,
        project_id="test_generalization",
        pack=pack,
        genre=genre,
    )
    return plan


def test_unseen_script_a_citizen_slips_and_steadies_basket() -> None:
    script = "A citizen slips on wet stone and steadies a woven basket."
    cast = {"citizen": {"role": "citizen", "preset": "senator", "x": 0.34, "y": 0.84}}
    world = {"objects": {"basket": {"kind": "basket", "x": 0.44, "y": 0.76}}}

    plan = _run_full_motion_pipeline(script, cast, world)
    val = validate_motion_plan(plan)

    assert val["valid"] is True, f"Validation failed: {val['errors']}"
    assert plan.routing_mode == "OFFLINE_ONLY"
    assert plan.provider_trace_id is None
    assert "citizen" in plan.actor_ids
    assert "basket" in plan.object_ids
    assert not any("roman" in a or "opposing" in a for a in plan.actor_ids)

    intent_types = [it.motion_type for it in plan.intents]
    assert "SLIP" in intent_types
    assert "STEADY_PROP" in intent_types

    citizen_track = next(tr for tr in plan.tracks if tr.actor_id == "citizen")
    phase_names = [ph.phase_name for ph in citizen_track.phases]
    assert "ANTICIPATE" in phase_names
    assert "REACT" in phase_names  # slip reaction
    assert "REACH" in phase_names
    assert "CONTACT" in phase_names  # steady basket
    assert "SETTLE" in phase_names
    assert any(c.object_id == "basket" for c in citizen_track.contacts)


def test_unseen_script_b_merchant_lifts_amphora_with_another_person() -> None:
    script = "A merchant lifts a heavy amphora together with another person."
    cast = {
        "merchant": {"role": "merchant", "preset": "senator", "x": 0.42, "y": 0.84},
        "dock_helper": {"role": "helper", "preset": "peasant", "x": 0.58, "y": 0.84},
    }
    world = {"objects": {"amphora": {"kind": "amphora", "x": 0.50, "y": 0.80}}}

    plan = _run_full_motion_pipeline(script, cast, world)
    val = validate_motion_plan(plan)

    assert val["valid"] is True, f"Validation failed: {val['errors']}"
    assert len(plan.tracks) == 2
    actor_ids = {tr.actor_id for tr in plan.tracks}
    assert actor_ids == {"merchant", "dock_helper"}

    # Verify synchronized shared lift with slight realistic offset and distinct handles
    t_lead = next(tr for tr in plan.tracks if tr.actor_id == "merchant")
    t_co = next(tr for tr in plan.tracks if tr.actor_id == "dock_helper")
    assert t_lead.contacts and t_co.contacts
    assert t_lead.contacts[0].object_id == "amphora"
    assert t_co.contacts[0].object_id == "amphora"
    assert t_lead.contacts[0].exclusive is False
    assert t_co.contacts[0].exclusive is False
    assert t_lead.contacts[0].anchor_local[0] != t_co.contacts[0].anchor_local[0]
    assert t_co.contacts[0].start_sec > t_lead.contacts[0].start_sec  # non-robotic human reaction offset

    # Verify amphora world Y actually moved upward in post-state
    final_amphora_y = plan.world_states[-1].objects["amphora"]["y"]
    assert final_amphora_y < 0.80


def test_unseen_script_c_child_walks_toward_lantern_then_ducks_from_wind() -> None:
    script = "A child walks toward a hanging lantern, then ducks from a sudden gust of wind."
    cast = {"child": {"role": "child", "preset": "peasant", "x": 0.26, "y": 0.84, "height_norm": 0.20}}
    world = {"objects": {"lantern": {"kind": "lantern", "x": 0.58, "y": 0.68}}}

    plan = _run_full_motion_pipeline(script, cast, world)
    val = validate_motion_plan(plan)

    assert val["valid"] is True, f"Validation failed: {val['errors']}"
    intent_types = [it.motion_type for it in plan.intents]
    assert intent_types == ["WALK", "DUCK"]

    child_track = plan.tracks[0]
    assert child_track.actor_id == "child"
    assert child_track.world_end[0] > child_track.world_start[0]  # walked closer to lantern
    phase_names = [ph.phase_name for ph in child_track.phases]
    assert "APPROACH" in phase_names
    assert "REACT" in phase_names  # ducking crouch
    assert any(ph.knee_flex >= 0.25 for ph in child_track.phases)


def test_idle_speech_distinction_and_unsupported_action_safe_fallback() -> None:
    idle_plan = _run_full_motion_pipeline(
        "The watchman whispered softly in the calm evening.",
        {"watchman": {"role": "citizen", "preset": "peasant", "x": 0.45, "y": 0.84}},
        {},
    )
    assert idle_plan.is_valid is True
    assert idle_plan.intents[0].is_idle_or_speech_only is True
    assert len(idle_plan.tracks[0].contacts) == 0
    assert "CONTACT" not in [p.phase_name for p in idle_plan.tracks[0].phases]

    unsup_intents = extract_semantic_motion_intents(
        "A citizen performs a triple backflip across the square.",
        cast_bible={"citizen": {"role": "citizen", "preset": "senator", "x": 0.4, "y": 0.84}},
    )
    assert unsup_intents[0].unsupported_action is True
    assert unsup_intents[0].motion_type == "UNSUPPORTED_ACTION"
    assert unsup_intents[0].fallback_motion_type == "OBSERVE"
    assert "backflip" in (unsup_intents[0].unsupported_evidence or "")

    cap_check = resolve_motion_intent_capabilities(unsup_intents, pack="squire", genre="civic")
    assert cap_check["valid"] is True
    assert cap_check["unsupported"][0]["status"] == "UNSUPPORTED_WITH_SAFE_FALLBACK"


def test_narrative_action_and_character_acting_shared_plan_and_manual_locks() -> None:
    script = "A merchant lifts a heavy amphora together with another person."
    cast = {
        "merchant": {"role": "merchant", "preset": "senator", "x": 0.42, "y": 0.84},
        "dock_helper": {"role": "helper", "preset": "peasant", "x": 0.58, "y": 0.84},
    }
    world = {"objects": {"amphora": {"kind": "amphora", "x": 0.50, "y": 0.80}}}
    plan = _run_full_motion_pipeline(script, cast, world)

    shots = [
        {"id": "S01", "start": 0.0, "end": 3.54, "dur": 3.54, "tpl": "scene", "args": {"bg": "town"}},
        {"id": "S02", "start": 3.54, "end": 6.0, "dur": 2.46, "tpl": "scene", "manual": True, "args": {"bg": "locked"}},
    ]
    manual_before = copy.deepcopy(shots[1])

    ctx = ActionContext(project_path=".", project_id="test_shared", pack="squire", genre="civic", shots=shots)
    ev_nodes = parse_action_intents(ctx, motion_plan=plan)
    choreo = plan_action_beats(WorldTimeline(), ev_nodes, shots, pack="squire", genre="civic", motion_plan=plan)
    caus = validate_action_causality(choreo, motion_plan=plan)
    assert caus["valid"] is True

    compiled_shots, mod_count = compile_action_choreography_to_shots(shots, choreo, motion_plan=plan)
    assert mod_count == 1
    assert compiled_shots[1] == manual_before  # manual lock 100% byte-identical
    assert "motionPlan" in compiled_shots[0]["args"]
    assert len(compiled_shots[0]["args"]["motionTracks"]) == 2

    perfs = plan_actor_performance([], pack="squire", genre="civic", motion_plan=plan)
    perf_val = validate_actor_performance(perfs, motion_plan=plan)
    assert perf_val["valid"] is True
    rig = compile_actor_performance_to_rig(perfs["S01"][0], pack="squire")
    assert "motionTrack" in rig

    # DEM pack compatibility
    dem_plan = _run_full_motion_pipeline(
        "The student walks to the desk.",
        {"hero": {"role": "student", "preset": "hero", "x": 0.32, "y": 0.82}},
        {},
        pack="dem",
        genre="selfimprove",
    )
    assert dem_plan.is_valid is True

    # Null plan leaves legacy shots untouched
    null_res = compile_motion_plan_to_legacy_shot_args(None, shots=shots)
    assert null_res["shots"] == shots


def test_validate_motion_plan_rejects_all_mandatory_defect_classes() -> None:
    script = "A citizen slips on wet stone and steadies a woven basket."
    cast = {"citizen": {"role": "citizen", "preset": "senator", "x": 0.34, "y": 0.84}}
    world = {"objects": {"basket": {"kind": "basket", "x": 0.44, "y": 0.76}}}
    good = _run_full_motion_pipeline(script, cast, world)
    assert validate_motion_plan(good)["valid"] is True

    # 1. All-null tracks
    p_null = good.model_copy(deep=True)
    p_null.tracks = []
    assert validate_motion_plan(p_null)["valid"] is False

    # 2. Missing physical target object
    p_missing_obj = good.model_copy(deep=True)
    p_missing_obj.tracks[0].contacts[0].object_id = "nonexistent_prop"
    assert validate_motion_plan(p_missing_obj)["valid"] is False

    # 3. Overlapping exclusive constraints
    p_excl = good.model_copy(deep=True)
    c_dup = p_excl.tracks[0].contacts[0].model_copy(deep=True)
    c_dup.actor_id = "intruder"
    c_dup.exclusive = True
    p_excl.tracks[0].contacts[0].exclusive = True
    t2 = p_excl.tracks[0].model_copy(deep=True)
    t2.track_id = "S01_intruder"
    t2.actor_id = "intruder"
    t2.contacts = [c_dup]
    p_excl.tracks.append(t2)
    assert validate_motion_plan(p_excl)["valid"] is False

    # 4. Foot penetrating ground
    p_ground = good.model_copy(deep=True)
    p_ground.tracks[0].phases[1].world_end = (0.38, 0.92)  # > ground_y 0.84
    assert validate_motion_plan(p_ground)["valid"] is False

    # 5. Event outside shot bounds
    p_oob = good.model_copy(deep=True)
    p_oob.tracks[0].phases[-1].end_sec = p_oob.tracks[0].end_sec + 0.5
    assert validate_motion_plan(p_oob)["valid"] is False

    # 6. Intra-track actor teleport / discontinuous position
    p_tele = good.model_copy(deep=True)
    p_tele.tracks[0].phases[2].world_start = (0.85, 0.84)
    assert validate_motion_plan(p_tele)["valid"] is False

    # 7. Missing mandatory CONTACT phase on physical contact action
    p_nocon = good.model_copy(deep=True)
    p_nocon.tracks[0].phases = [ph for ph in p_nocon.tracks[0].phases if ph.phase_name != "CONTACT"]
    assert validate_motion_plan(p_nocon)["valid"] is False

    # 8. Unsupported action with missing fallback
    p_unsup = good.model_copy(deep=True)
    p_unsup.intents[0].unsupported_action = True
    p_unsup.intents[0].fallback_motion_type = None
    assert validate_motion_plan(p_unsup)["valid"] is False
